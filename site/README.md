# Olist OR Lab — Interactive MVP

This folder contains the interactive results website for the Olist forecast-driven inventory and fulfillment project.

Live site: [Olist OR Lab](https://olist-forecast-or-lab.peishanli1013.chatgpt.site)

## What the MVP shows

- observed demand concentration and historical route risk;
- comparison of last-week, four-week moving-average, and pooled Ridge forecasts;
- 13-week rolling policy results and regional fill rates;
- solver-verified one-factor-at-a-time sensitivity scenarios;
- a six-input Live What-if mode with instant cost, fill-rate, shortage, and inventory updates.
- an interactive response curve with selectable input and outcome metrics.

Verified Runs selects previously solved MILP scenarios. Live What-if uses piecewise-linear interpolation between those solved anchors and adds the one-factor effects for combined settings. The page labels these combined results as calibrated estimates and automatically switches back to solver-verified status when the inputs exactly match a stored solve.

For a research-grade upgrade, generate a larger offline scenario library from the Python pipeline and load those solver outputs into the website. A true on-demand version would additionally require a Python optimization service, job status API, and result cache; that service is not part of the current static Sites deployment.

## Run locally

Requires Node.js 22.13 or later.

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

## Verify

```bash
npm run lint
npm test
```

The main interface is implemented in `app/Dashboard.tsx`; design styles are in `app/globals.css`. The verified values shown in the MVP originate from the project outputs under `../outputs/tables/`.
