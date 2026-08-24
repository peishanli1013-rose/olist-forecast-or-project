from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


LAGS = (1, 2, 4, 8)
MAX_LAG = max(LAGS)


@dataclass
class RidgeFit:
    coefficients: np.ndarray
    numeric_mean: np.ndarray
    numeric_scale: np.ndarray
    residual_scale: dict[tuple[str, str], float]
    global_residual_scale: float
    selected_alpha: float


class PooledRidgeForecaster:
    """Small dependency-free global Ridge model for related demand series."""

    def __init__(
        self,
        panel: pd.DataFrame,
        alpha: float = 25.0,
        alpha_grid: tuple[float, ...] | None = None,
        calibration_weeks: int = 8,
    ):
        self.panel = panel.copy()
        self.panel["week"] = pd.to_datetime(self.panel["week"])
        self.alpha = alpha
        self.alpha_grid = tuple(alpha_grid) if alpha_grid else (alpha,)
        self.calibration_weeks = calibration_weeks
        self.weeks = sorted(self.panel["week"].unique())
        self.categories = sorted(self.panel["category"].unique())
        self.regions = sorted(self.panel["region"].unique())
        self.pivot = (
            self.panel.pivot(index="week", columns=["category", "region"], values="demand")
            .sort_index()
            .fillna(0.0)
        )
        self.numeric_count = 9

    def _features(self, history: list[float], target_week: pd.Timestamp, category: str, region: str) -> np.ndarray:
        if len(history) < MAX_LAG:
            raise ValueError("At least eight historical weeks are required")
        lags = [history[-lag] for lag in LAGS]
        rolling = [float(np.mean(history[-4:])), float(np.mean(history[-8:]))]
        elapsed = (pd.Timestamp(target_week) - pd.Timestamp(self.weeks[0])).days / 7.0
        week_number = pd.Timestamp(target_week).isocalendar().week
        calendar = [elapsed / max(1.0, len(self.weeks)), np.sin(2 * np.pi * week_number / 52.0), np.cos(2 * np.pi * week_number / 52.0)]
        category_flags = [1.0 if category == value else 0.0 for value in self.categories]
        region_flags = [1.0 if region == value else 0.0 for value in self.regions]
        return np.asarray(lags + rolling + calendar + category_flags + region_flags, dtype=float)

    def _training_matrix(self, origin: pd.Timestamp):
        train_weeks = [pd.Timestamp(w) for w in self.pivot.index if pd.Timestamp(w) < pd.Timestamp(origin)]
        if len(train_weeks) <= MAX_LAG:
            raise ValueError(f"Insufficient training history before {origin}")
        X_rows: list[np.ndarray] = []
        y_rows: list[float] = []
        labels: list[tuple[str, str]] = []
        target_labels: list[pd.Timestamp] = []
        train_pivot = self.pivot.loc[train_weeks]
        for category, region in self.pivot.columns:
            values = train_pivot[(category, region)].astype(float).tolist()
            for pos in range(MAX_LAG, len(values)):
                X_rows.append(self._features(values[:pos], train_weeks[pos], category, region))
                y_rows.append(values[pos])
                labels.append((category, region))
                target_labels.append(pd.Timestamp(train_weeks[pos]))
        return np.vstack(X_rows), np.asarray(y_rows, dtype=float), labels, target_labels

    def _fit_coefficients(self, X: np.ndarray, y: np.ndarray, alpha: float):
        numeric_mean = X[:, : self.numeric_count].mean(axis=0)
        numeric_scale = X[:, : self.numeric_count].std(axis=0)
        numeric_scale[numeric_scale < 1e-8] = 1.0
        X_scaled = X.copy()
        X_scaled[:, : self.numeric_count] = (X_scaled[:, : self.numeric_count] - numeric_mean) / numeric_scale
        X_design = np.column_stack([np.ones(len(X_scaled)), X_scaled])
        penalty = np.eye(X_design.shape[1]) * alpha
        penalty[0, 0] = 0.0
        coefficients = np.linalg.solve(X_design.T @ X_design + penalty, X_design.T @ y)
        return coefficients, numeric_mean, numeric_scale

    def _matrix_predictions(
        self,
        X: np.ndarray,
        coefficients: np.ndarray,
        numeric_mean: np.ndarray,
        numeric_scale: np.ndarray,
    ) -> np.ndarray:
        X_scaled = X.copy()
        X_scaled[:, : self.numeric_count] = (X_scaled[:, : self.numeric_count] - numeric_mean) / numeric_scale
        return np.maximum(0.0, np.column_stack([np.ones(len(X_scaled)), X_scaled]) @ coefficients)

    def fit(self, origin: pd.Timestamp) -> RidgeFit:
        X, y, labels, target_labels = self._training_matrix(origin)
        unique_targets = sorted(set(target_labels))
        calibration_count = min(self.calibration_weeks, max(1, len(unique_targets) // 3))
        calibration_start = unique_targets[-calibration_count]
        calibration_mask = np.asarray([week >= calibration_start for week in target_labels])
        training_mask = ~calibration_mask
        if training_mask.sum() < X.shape[1] + 1:
            training_mask = np.ones(len(X), dtype=bool)
            calibration_mask = np.ones(len(X), dtype=bool)

        alpha_scores: list[tuple[float, float]] = []
        calibration_fits: dict[float, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        for alpha in self.alpha_grid:
            fit_values = self._fit_coefficients(X[training_mask], y[training_mask], alpha)
            calibration_fits[alpha] = fit_values
            predictions = self._matrix_predictions(X[calibration_mask], *fit_values)
            denominator = float(np.abs(y[calibration_mask]).sum())
            score = (
                float(np.abs(y[calibration_mask] - predictions).sum() / denominator)
                if denominator
                else float(np.abs(y[calibration_mask] - predictions).mean())
            )
            alpha_scores.append((score, alpha))
        selected_alpha = min(alpha_scores)[1]
        calibration_predictions = self._matrix_predictions(
            X[calibration_mask], *calibration_fits[selected_alpha]
        )
        calibration_residuals = y[calibration_mask] - calibration_predictions
        global_scale = float(np.sqrt(np.mean(np.square(calibration_residuals))))
        calibration_labels = [label for label, keep in zip(labels, calibration_mask) if keep]
        residual_frame = pd.DataFrame(calibration_labels, columns=["category", "region"])
        residual_frame["squared_error"] = np.square(calibration_residuals)
        grouped = residual_frame.groupby(["category", "region"])["squared_error"].mean().pow(0.5)
        scales = {key: max(1.0, float(value)) for key, value in grouped.items()}
        coefficients, numeric_mean, numeric_scale = self._fit_coefficients(X, y, selected_alpha)
        return RidgeFit(
            coefficients,
            numeric_mean,
            numeric_scale,
            scales,
            max(1.0, global_scale),
            selected_alpha,
        )

    def _ridge_forecast(self, origin: pd.Timestamp, horizon: int) -> pd.DataFrame:
        fit = self.fit(origin)
        rows = []
        history_pivot = self.pivot[self.pivot.index < pd.Timestamp(origin)]
        for category, region in self.pivot.columns:
            history = history_pivot[(category, region)].astype(float).tolist()
            for h in range(1, horizon + 1):
                target_week = pd.Timestamp(origin) + pd.Timedelta(weeks=h - 1)
                features = self._features(history, target_week, category, region)
                features[: self.numeric_count] = (features[: self.numeric_count] - fit.numeric_mean) / fit.numeric_scale
                prediction = float(np.dot(np.r_[1.0, features], fit.coefficients))
                prediction = max(0.0, prediction)
                history.append(prediction)
                rows.append(
                    {
                        "origin": pd.Timestamp(origin),
                        "target_week": target_week,
                        "horizon": h,
                        "category": category,
                        "region": region,
                        "forecast": prediction,
                        "error_scale": fit.residual_scale.get((category, region), fit.global_residual_scale),
                        "uncertainty_source": "chronological_holdout",
                        "selected_alpha": fit.selected_alpha,
                        "method": "ridge",
                    }
                )
        return pd.DataFrame(rows)

    def _baseline_scale(self, origin: pd.Timestamp, method: str) -> tuple[dict[tuple[str, str], float], float]:
        train = self.pivot[self.pivot.index < pd.Timestamp(origin)]
        rows = []
        for category, region in train.columns:
            values = train[(category, region)].astype(float).to_numpy()
            errors = []
            for pos in range(4, len(values)):
                prediction = values[pos - 1] if method == "last_week" else values[pos - 4 : pos].mean()
                errors.append(values[pos] - prediction)
            calibration_errors = errors[-self.calibration_weeks :]
            scale = float(np.sqrt(np.mean(np.square(calibration_errors)))) if calibration_errors else 1.0
            rows.append((category, region, max(1.0, scale)))
        scales = {(c, r): s for c, r, s in rows}
        global_scale = float(np.mean([s for _, _, s in rows])) if rows else 1.0
        return scales, max(1.0, global_scale)

    def _baseline_forecast(self, origin: pd.Timestamp, horizon: int, method: str) -> pd.DataFrame:
        scales, global_scale = self._baseline_scale(origin, method)
        history_pivot = self.pivot[self.pivot.index < pd.Timestamp(origin)]
        rows = []
        for category, region in self.pivot.columns:
            history = history_pivot[(category, region)].astype(float).tolist()
            for h in range(1, horizon + 1):
                target_week = pd.Timestamp(origin) + pd.Timedelta(weeks=h - 1)
                prediction = history[-1] if method == "last_week" else float(np.mean(history[-4:]))
                prediction = max(0.0, prediction)
                history.append(prediction)
                rows.append(
                    {
                        "origin": pd.Timestamp(origin),
                        "target_week": target_week,
                        "horizon": h,
                        "category": category,
                        "region": region,
                        "forecast": prediction,
                        "error_scale": scales.get((category, region), global_scale),
                        "uncertainty_source": "chronological_holdout",
                        "selected_alpha": np.nan,
                        "method": method,
                    }
                )
        return pd.DataFrame(rows)

    def forecast(self, origin: pd.Timestamp, horizon: int, method: str) -> pd.DataFrame:
        if method == "ridge":
            result = self._ridge_forecast(origin, horizon)
        elif method in {"last_week", "moving_average"}:
            result = self._baseline_forecast(origin, horizon, method)
        else:
            raise ValueError(f"Unknown forecast method: {method}")
        actual = self.panel.rename(columns={"week": "target_week", "demand": "actual"})[
            ["target_week", "category", "region", "actual"]
        ]
        return result.merge(actual, on=["target_week", "category", "region"], how="left")


def generate_backtest_forecasts(
    panel: pd.DataFrame,
    backtest_weeks: int,
    horizon: int,
    alpha: float,
    alpha_grid: tuple[float, ...] | None = None,
    calibration_weeks: int = 8,
) -> pd.DataFrame:
    forecaster = PooledRidgeForecaster(
        panel,
        alpha=alpha,
        alpha_grid=alpha_grid,
        calibration_weeks=calibration_weeks,
    )
    evaluation_weeks = sorted(pd.to_datetime(panel["week"].unique()))[-backtest_weeks:]
    frames = []
    for origin in evaluation_weeks:
        for method in ("last_week", "moving_average", "ridge"):
            frames.append(forecaster.forecast(pd.Timestamp(origin), horizon, method))
    return pd.concat(frames, ignore_index=True)


def forecast_metrics(forecasts: pd.DataFrame) -> pd.DataFrame:
    valid = forecasts.dropna(subset=["actual"]).copy()
    valid["absolute_error"] = (valid["actual"] - valid["forecast"]).abs()
    valid["signed_error"] = valid["forecast"] - valid["actual"]
    rows = []
    for (method, horizon), group in valid.groupby(["method", "horizon"]):
        denominator = group["actual"].abs().sum()
        rows.append(
            {
                "method": method,
                "horizon": int(horizon),
                "observations": int(len(group)),
                "MAE": float(group["absolute_error"].mean()),
                "WAPE": float(group["absolute_error"].sum() / denominator) if denominator else np.nan,
                "bias": float(group["signed_error"].mean()),
            }
        )
    return pd.DataFrame(rows).sort_values(["horizon", "WAPE"])
