"use client";

import { useState } from "react";

type Page = "overview" | "demand" | "forecast" | "optimization" | "sensitivity";
type LabMode = "verified" | "live";

type Scenario = {
  id: string;
  cost: number;
  fill: number;
  shortage: number;
  inventory: number;
  note: string;
};

type WhatIfInputs = {
  safety: number;
  lead: number;
  service: number;
  capacity: number;
  risk: number;
  shortageValue: number;
};

type MetricKey = "cost" | "fill" | "shortage" | "inventory";
type InputKey = keyof WhatIfInputs;
type InputControl = {
  key: InputKey;
  label: string;
  min: number;
  max: number;
  step: number;
  suffix: string;
  low?: { value: number; scenario: string };
  high?: { value: number; scenario: string };
};

const forecastRows = [
  { method: "Pooled Ridge", wape: 30.94, mae: 6.79, winners: 26, tone: "green" },
  { method: "4-week moving average", wape: 34.12, mae: 7.49, winners: 23, tone: "gold" },
  { method: "Last week", wape: 34.74, mae: 7.63, winners: 1, tone: "gray" },
];

const policyRows = [
  { id: "ridge", name: "Ridge + OR", cost: 996695.41, fill: 94.01, shortage: 855, inventory: 824, ordered: 13918, components: [650486, 202041, 14105, 4483, 92326, 33254] },
  { id: "moving", name: "Moving average + OR", cost: 1019523.25, fill: 94.26, shortage: 819, inventory: 1018, ordered: 14316, components: [669205, 202816, 14128, 4982, 83841, 44551] },
  { id: "last", name: "Last week + OR", cost: 1035993.17, fill: 93.31, shortage: 954, inventory: 1241, ordered: 14233, components: [663607, 201096, 13970, 4541, 102449, 50330] },
];

const regions = [
  { name: "Southeast", demand: 10043, fill: 95.89, shortage: 413 },
  { name: "South", demand: 1915, fill: 93.26, shortage: 129 },
  { name: "Central-West", demand: 818, fill: 92.3, shortage: 63 },
  { name: "Northeast", demand: 1248, fill: 86.22, shortage: 172 },
  { name: "North", demand: 243, fill: 67.9, shortage: 78 },
];

const demandRows = [
  { category: "bed_bath_table", region: "Southeast", demand: 8420, share: 11.8, cv: 0.53 },
  { category: "health_beauty", region: "Southeast", demand: 6468, share: 9.06, cv: 0.62 },
  { category: "sports_leisure", region: "Southeast", demand: 5824, share: 8.16, cv: 0.49 },
  { category: "furniture_decor", region: "Southeast", demand: 5675, share: 7.95, cv: 0.51 },
  { category: "computers_accessories", region: "Southeast", demand: 5305, share: 7.43, cv: 0.69 },
  { category: "housewares", region: "Southeast", demand: 5063, share: 7.09, cv: 0.57 },
];

const riskRows = [
  { route: "PR → Southeast", category: "bed_bath_table", n: 73, late: 22.91, seller: 35.1, freight: 23.85, risk: 3.59 },
  { route: "PR → South", category: "bed_bath_table", n: 35, late: 10.04, seller: 35.1, freight: 18.83, risk: 2.56 },
  { route: "PR → Northeast", category: "computers_accessories", n: 44, late: 16.44, seller: 17.73, freight: 42.92, risk: 2.2 },
  { route: "MG → Southeast", category: "telephony", n: 35, late: 15.69, seller: 17.18, freight: 15.1, risk: 2.11 },
  { route: "RJ → Northeast", category: "watches_gifts", n: 89, late: 16.39, seller: 15.88, freight: 23.63, risk: 2.11 },
];

const scenarios: Record<string, Scenario> = {
  base: { id: "base", cost: 996695.41, fill: 94.01, shortage: 855, inventory: 824, note: "Base Ridge policy: 0.5× safety error, one-week lead time, 90% regional service target." },
  safety_0: { id: "safety_0", cost: 1164917.29, fill: 86.03, shortage: 1993, inventory: 541, note: "Removing the forecast-error buffer creates severe shortages and higher shortage penalties." },
  safety_1: { id: "safety_1", cost: 954750.82, fill: 98.82, shortage: 168, inventory: 1195, note: "A full error-scale buffer raises inventory but sharply reduces expensive shortages." },
  lead_time_2: { id: "lead_time_2", cost: 1091625.68, fill: 91.68, shortage: 1187, inventory: 708, note: "A two-week replenishment delay weakens responsiveness and raises shortage exposure." },
  service_85: { id: "service_85", cost: 974563.99, fill: 94.01, shortage: 855, inventory: 824, note: "The realized fill rate is unchanged; the lower target mainly reduces service-gap penalties." },
  service_95: { id: "service_95", cost: 1038865.07, fill: 94.01, shortage: 855, inventory: 824, note: "The higher target raises penalized service gaps but does not create additional physical inventory." },
  capacity_80: { id: "capacity_80", cost: 996695.41, fill: 94.01, shortage: 855, inventory: 824, note: "The solution is unchanged: handling capacity is not binding at 80% of the tested baseline." },
  capacity_120: { id: "capacity_120", cost: 996695.41, fill: 94.01, shortage: 855, inventory: 824, note: "Extra handling capacity has no value in this range because another constraint is limiting performance." },
  risk_0: { id: "risk_0", cost: 982120.52, fill: 94.04, shortage: 851, inventory: 824, note: "Removing risk prices lowers reported cost and shifts route choices slightly." },
  risk_2x: { id: "risk_2x", cost: 1011040.66, fill: 93.99, shortage: 857, inventory: 824, note: "Doubling delay-risk weights increases cost while service remains close to the base case." },
  shortage_low: { id: "shortage_low", cost: 958239.37, fill: 94.0, shortage: 856, inventory: 816, note: "A lower shortage valuation reduces reported cost and permits one additional unmet unit." },
  shortage_high: { id: "shortage_high", cost: 1060825.52, fill: 94.01, shortage: 855, inventory: 824, note: "Higher shortage penalties raise cost, while the physical solution is unchanged in this tested case." },
};

const scenarioGroups = [
  { id: "safety", label: "Safety buffer", options: [["safety_0", "0×"], ["base", "0.5×"], ["safety_1", "1.0×"]] },
  { id: "lead", label: "Lead time", options: [["base", "1 week"], ["lead_time_2", "2 weeks"]] },
  { id: "service", label: "Service target", options: [["service_85", "85%"], ["base", "90%"], ["service_95", "95%"]] },
  { id: "capacity", label: "Capacity", options: [["capacity_80", "80%"], ["base", "100%"], ["capacity_120", "120%"]] },
  { id: "risk", label: "Risk weights", options: [["risk_0", "0×"], ["base", "Base"], ["risk_2x", "2×"]] },
  { id: "shortage", label: "Shortage value", options: [["shortage_low", "Low"], ["base", "Base"], ["shortage_high", "High"]] },
] as const;

const baseInputs: WhatIfInputs = {
  safety: 0.5,
  lead: 1,
  service: 90,
  capacity: 100,
  risk: 1,
  shortageValue: 1.25,
};

const exactInputs: Record<string, WhatIfInputs> = {
  base: baseInputs,
  safety_0: { ...baseInputs, safety: 0 },
  safety_1: { ...baseInputs, safety: 1 },
  lead_time_2: { ...baseInputs, lead: 2 },
  service_85: { ...baseInputs, service: 85 },
  service_95: { ...baseInputs, service: 95 },
  capacity_80: { ...baseInputs, capacity: 80 },
  capacity_120: { ...baseInputs, capacity: 120 },
  risk_0: { ...baseInputs, risk: 0 },
  risk_2x: { ...baseInputs, risk: 2 },
  shortage_low: { ...baseInputs, shortageValue: 0.8 },
  shortage_high: { ...baseInputs, shortageValue: 2 },
};

const inputControls: readonly InputControl[] = [
  { key: "safety", label: "Safety buffer", min: 0, max: 1, step: 0.05, suffix: "×", low: { value: 0, scenario: "safety_0" }, high: { value: 1, scenario: "safety_1" } },
  { key: "lead", label: "Effective lead time", min: 1, max: 2, step: 0.1, suffix: " weeks", high: { value: 2, scenario: "lead_time_2" } },
  { key: "service", label: "Regional service target", min: 85, max: 95, step: 1, suffix: "%", low: { value: 85, scenario: "service_85" }, high: { value: 95, scenario: "service_95" } },
  { key: "capacity", label: "Weight capacity", min: 80, max: 120, step: 5, suffix: "%", low: { value: 80, scenario: "capacity_80" }, high: { value: 120, scenario: "capacity_120" } },
  { key: "risk", label: "Route-risk weight", min: 0, max: 2, step: 0.1, suffix: "×", low: { value: 0, scenario: "risk_0" }, high: { value: 2, scenario: "risk_2x" } },
  { key: "shortageValue", label: "Shortage value", min: 0.8, max: 2, step: 0.05, suffix: "×", low: { value: 0.8, scenario: "shortage_low" }, high: { value: 2, scenario: "shortage_high" } },
];

const money = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const signed = (value: number, digits = 1) => `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;
const closeEnough = (a: number, b: number) => Math.abs(a - b) < 0.0001;

function exactScenarioFor(inputs: WhatIfInputs) {
  const keys = Object.keys(baseInputs) as (keyof WhatIfInputs)[];
  return Object.entries(exactInputs).find(([, values]) => keys.every((key) => closeEnough(inputs[key], values[key])))?.[0] ?? null;
}

function estimateScenario(inputs: WhatIfInputs): Scenario {
  const result: Scenario = { ...scenarios.base, id: "live_estimate", note: "Instant additive response-surface estimate calibrated to the eleven one-factor MILP runs." };
  const metrics: MetricKey[] = ["cost", "fill", "shortage", "inventory"];

  for (const control of inputControls) {
    const value = inputs[control.key];
    const baseValue = baseInputs[control.key];
    const anchor = value < baseValue ? control.low : control.high;
    if (!anchor || closeEnough(value, baseValue)) continue;
    const ratio = (value - baseValue) / (anchor.value - baseValue);
    for (const metric of metrics) {
      result[metric] += ratio * (scenarios[anchor.scenario][metric] - scenarios.base[metric]);
    }
  }

  result.cost = Math.max(0, result.cost);
  result.fill = Math.min(100, Math.max(0, result.fill));
  result.shortage = Math.max(0, Math.round(result.shortage));
  result.inventory = Math.max(0, Math.round(result.inventory));
  return result;
}

function PageTitle({ kicker, title, copy }: { kicker: string; title: string; copy: string }) {
  return <header className="sectionHeader"><span>{kicker}</span><h1>{title}</h1><p>{copy}</p></header>;
}

function Metric({ label, value, detail, accent = false }: { label: string; value: string; detail: string; accent?: boolean }) {
  return <article className={`metricCard ${accent ? "accent" : ""}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>;
}

export default function Dashboard() {
  const [page, setPage] = useState<Page>("overview");
  const [labMode, setLabMode] = useState<LabMode>("verified");
  const [groupId, setGroupId] = useState("safety");
  const [scenarioId, setScenarioId] = useState("base");
  const [whatIfInputs, setWhatIfInputs] = useState<WhatIfInputs>({ ...baseInputs });
  const [copied, setCopied] = useState(false);
  const verifiedScenario = scenarios[scenarioId];
  const base = scenarios.base;
  const activeGroup = scenarioGroups.find((group) => group.id === groupId) ?? scenarioGroups[0];
  const exactLiveScenarioId = exactScenarioFor(whatIfInputs);
  const liveScenario = exactLiveScenarioId ? scenarios[exactLiveScenarioId] : estimateScenario(whatIfInputs);
  const result = labMode === "verified" ? verifiedScenario : liveScenario;
  const resultIsVerified = labMode === "verified" || Boolean(exactLiveScenarioId);

  const updateInput = (key: InputKey, value: number) => {
    setWhatIfInputs((current) => ({ ...current, [key]: value }));
  };

  const copySnapshot = async () => {
    const inputSummary = inputControls.map((control) => `${control.label}: ${whatIfInputs[control.key]}${control.suffix}`).join("; ");
    await navigator.clipboard.writeText(`Olist OR Lab what-if — ${inputSummary}. Cost R$${money.format(result.cost)}, fill ${result.fill.toFixed(2)}%, shortage ${money.format(result.shortage)}, ending inventory ${money.format(result.inventory)}. ${resultIsVerified ? "Solver-verified scenario." : "Calibrated preview; rerun the MILP before making a final claim."}`);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  const showPage = (next: Page) => {
    setPage(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <main className="appShell">
      <header className="appNav">
        <button className="brandButton" onClick={() => showPage("overview")} aria-label="Open overview">
          <span className="brandMark">O</span><span>Olist OR Lab<small>Decision intelligence</small></span>
        </button>
        <nav aria-label="Dashboard sections">
          {(["overview", "demand", "forecast", "optimization", "sensitivity"] as Page[]).map((item) => (
            <button key={item} className={page === item ? "active" : ""} onClick={() => showPage(item)}>{item}</button>
          ))}
        </nav>
        <div className="validated"><span /> 27 checks passed</div>
      </header>

      {page === "overview" && (
        <div className="pageWrap">
          <section className="hero">
            <div className="eyebrow">Forecast-driven operations research</div>
            <h1>From marketplace signals to inventory decisions.</h1>
            <p>Explore what the Olist data reveals, how three forecasts behave, and how those forecasts change simulated cost and regional service.</p>
            <div className="heroActions">
              <button className="primaryButton" onClick={() => showPage("sensitivity")}>Open sensitivity lab <b>→</b></button>
              <span>13-week rolling backtest · 50 demand series</span>
            </div>
          </section>

          <section className="metricGrid" aria-label="Key project metrics">
            <Metric label="Valid item lines" value="112,643" detail="Six joined Olist tables" />
            <Metric label="Ridge WAPE" value="30.94%" detail="Best aggregate forecast" />
            <Metric label="Simulated cost" value="R$996.7k" detail="Lowest base policy" accent />
            <Metric label="Fill rate" value="94.01%" detail="Ridge + OR policy" />
          </section>

          <section className="overviewGrid">
            <article className="darkPanel">
              <span className="panelKicker">Decision loop</span>
              <h2>Describe → forecast → plan → fulfill</h2>
              <div className="flowSteps">
                <div><b>01</b><span>Demand & risk</span></div><i>→</i>
                <div><b>02</b><span>4-week MILP</span></div><i>→</i>
                <div><b>03</b><span>Actual fulfillment</span></div>
              </div>
            </article>
            <article className="insightPanel">
              <span className="panelKicker">Most decision-relevant finding</span>
              <h2>One extra week of lead time costs more than R$94k.</h2>
              <p>In the verified two-week scenario, shortages rise by 332 units and fill rate falls by 2.33 points.</p>
              <button onClick={() => { setGroupId("lead"); setScenarioId("lead_time_2"); showPage("sensitivity"); }}>Inspect scenario →</button>
            </article>
          </section>

          <section className="splitSection">
            <div>
              <span className="panelKicker">Evidence, not just a solve</span>
              <h2>The dashboard connects three kinds of evidence.</h2>
            </div>
            <div className="evidenceList">
              <article><b>01</b><div><h3>Observed</h3><p>Demand, geography, price, freight, weight and delivery timestamps.</p></div></article>
              <article><b>02</b><div><h3>Derived</h3><p>Weekly demand, historical route risk, supply share and forecast uncertainty.</p></div></article>
              <article><b>03</b><div><h3>Scenario</h3><p>Proxy hubs, inventory, capacity, lead time and economic penalties.</p></div></article>
            </div>
          </section>
        </div>
      )}

      {page === "demand" && (
        <div className="pageWrap">
          <PageTitle kicker="Data exploration" title="Demand is concentrated—and risk is uneven." copy="The retained panel contains 50 category–region series. Southeast demand dominates, while historical late-delivery and seller risk vary materially by route." />
          <section className="twoCol">
            <article className="whitePanel chartPanel">
              <div className="panelHead"><div><span className="panelKicker">Top segments</span><h2>Total retained demand</h2></div><span className="unit">units</span></div>
              <div className="barList">
                {demandRows.map((row) => <div className="barRow" key={row.category}><div><b>{row.category.replaceAll("_", " ")}</b><small>{row.region} · CV {row.cv.toFixed(2)}</small></div><div className="barTrack"><span style={{ width: `${row.demand / 84.2}%` }} /></div><strong>{money.format(row.demand)}</strong></div>)}
              </div>
            </article>
            <article className="whitePanel concentrationPanel">
              <span className="panelKicker">Concentration</span>
              <div className="bigNumber">54.1%</div>
              <p>of retained demand is represented by the six largest category–region segments shown here.</p>
              <div className="miniMetric"><span>Largest single segment</span><strong>11.8%</strong></div>
              <div className="miniMetric"><span>Complete weeks</span><strong>86</strong></div>
              <div className="miniMetric"><span>Zero-inclusive panel rows</span><strong>4,300</strong></div>
            </article>
          </section>

          <section className="whitePanel tablePanel">
            <div className="panelHead"><div><span className="panelKicker">Historical fulfillment evidence</span><h2>Highest smoothed risk routes</h2></div><span className="badge">minimum n = 30</span></div>
            <div className="tableScroll"><table><thead><tr><th>Route</th><th>Category</th><th>n</th><th>Late probability</th><th>Seller risk</th><th>Median freight</th><th>Risk cost / unit</th></tr></thead><tbody>{riskRows.map((row) => <tr key={`${row.route}-${row.category}`}><td><b>{row.route}</b></td><td>{row.category.replaceAll("_", " ")}</td><td>{row.n}</td><td>{row.late.toFixed(1)}%</td><td>{row.seller.toFixed(1)}%</td><td>R${row.freight.toFixed(2)}</td><td><span className="riskPill">R${row.risk.toFixed(2)}</span></td></tr>)}</tbody></table></div>
          </section>
        </div>
      )}

      {page === "forecast" && (
        <div className="pageWrap">
          <PageTitle kicker="Chronological evaluation" title="Ridge wins overall—not everywhere." copy="All forecasts use expanding-window origins and an eight-week past-only holdout. Aggregate accuracy and segment-level winners tell complementary stories." />
          <section className="forecastGrid">
            {forecastRows.map((row, index) => <article className={`forecastCard ${index === 0 ? "winner" : ""}`} key={row.method}><div className="rank">0{index + 1}</div><span>{row.method}</span><strong>{row.wape.toFixed(2)}%</strong><small>one-week WAPE</small><div className="forecastMeta"><div><b>{row.mae.toFixed(2)}</b><span>MAE</span></div><div><b>{row.winners}</b><span>best segments</span></div></div>{index === 0 && <em>Best aggregate result</em>}</article>)}
          </section>
          <section className="twoCol forecastDetail">
            <article className="whitePanel chartPanel">
              <div className="panelHead"><div><span className="panelKicker">Accuracy gap</span><h2>One-week WAPE</h2></div><span className="unit">lower is better</span></div>
              <div className="verticalBars">{forecastRows.map((row) => <div key={row.method}><div className="vBar"><span className={row.tone} style={{ height: `${row.wape * 2.3}%` }}><b>{row.wape.toFixed(2)}%</b></span></div><small>{row.method}</small></div>)}</div>
            </article>
            <article className="whitePanel formulaPanel">
              <span className="panelKicker">Forecast → planning input</span>
              <h2>Uncertainty becomes a safety buffer.</h2>
              <div className="formula">D̃ = ⌈max(0, D̂ + ζs)⌉</div>
              <dl><div><dt>D̂</dt><dd>point forecast</dd></div><div><dt>s</dt><dd>past-only error scale</dd></div><div><dt>ζ</dt><dd>safety multiplier</dd></div></dl>
              <button className="textButton" onClick={() => { setGroupId("safety"); setScenarioId("base"); showPage("sensitivity"); }}>Test the safety multiplier →</button>
            </article>
          </section>
        </div>
      )}

      {page === "optimization" && (
        <div className="pageWrap">
          <PageTitle kicker="13-week rolling backtest" title="Forecasts change inventory decisions—not just errors." copy="Each policy uses the same six-hub network, actual demand, capacities and cost assumptions. Only the forecast input changes." />
          <section className="policyGrid">
            {policyRows.map((row, index) => <article className={`policyCard ${index === 0 ? "recommended" : ""}`} key={row.id}><div className="policyTop"><span>{row.name}</span>{index === 0 && <em>Lowest cost</em>}</div><strong>R${money.format(row.cost)}</strong><small>simulated total cost</small><div className="policyStats"><div><b>{row.fill.toFixed(2)}%</b><span>fill rate</span></div><div><b>{money.format(row.shortage)}</b><span>shortage</span></div><div><b>{money.format(row.inventory)}</b><span>end inventory</span></div></div></article>)}
          </section>
          <section className="twoCol">
            <article className="whitePanel chartPanel">
              <div className="panelHead"><div><span className="panelKicker">Cost composition</span><h2>Ridge + OR</h2></div><span className="unit">R$</span></div>
              <div className="componentList">{["Procurement", "Shipping", "Risk", "Holding", "Shortage", "Service gap"].map((label, index) => <div key={label}><span>{label}</span><div><i style={{ width: `${policyRows[0].components[index] / 6800}%` }} /></div><strong>{money.format(policyRows[0].components[index])}</strong></div>)}</div>
            </article>
            <article className="whitePanel chartPanel">
              <div className="panelHead"><div><span className="panelKicker">Equity lens</span><h2>Regional fill rate</h2></div><span className="unit">Ridge policy</span></div>
              <div className="regionList">{regions.map((row) => <div key={row.name}><div><b>{row.name}</b><small>{money.format(row.demand)} demand · {row.shortage} shortage</small></div><div className="regionTrack"><span className={row.fill < 90 ? "alert" : ""} style={{ width: `${row.fill}%` }} /></div><strong>{row.fill.toFixed(1)}%</strong></div>)}</div>
            </article>
          </section>
        </div>
      )}

      {page === "sensitivity" && (
        <div className="pageWrap sensitivityPage">
          <PageTitle kicker="Interactive sensitivity lab" title="Test one solved case—or combine assumptions instantly." copy="Verified Runs reproduces the eleven MILP outputs. Live What-if combines their measured one-factor effects into a transparent, instant planning preview." />
          <div className="labModeToggle" role="tablist" aria-label="Sensitivity analysis mode">
            <button role="tab" aria-selected={labMode === "verified"} className={labMode === "verified" ? "active" : ""} onClick={() => setLabMode("verified")}><span>01</span><b>Verified runs</b><small>Exact MILP outputs</small></button>
            <button role="tab" aria-selected={labMode === "live"} className={labMode === "live" ? "active" : ""} onClick={() => setLabMode("live")}><span>02</span><b>Live what-if</b><small>Six inputs · instant response</small></button>
          </div>
          <section className="labLayout">
            <aside className="controlPanel">
              {labMode === "verified" ? (
                <>
                  <div className="controlIntro"><span className="panelKicker">1 · Choose parameter</span><p>One-factor-at-a-time design</p></div>
                  <div className="groupButtons">{scenarioGroups.map((group) => <button key={group.id} className={groupId === group.id ? "active" : ""} onClick={() => { setGroupId(group.id); setScenarioId("base"); }}><span>{group.label}</span><b>→</b></button>)}</div>
                  <div className="valueControl"><span className="panelKicker">2 · Set tested value</span><div>{activeGroup.options.map(([id, label]) => <button key={`${groupId}-${id}`} className={scenarioId === id ? "active" : ""} onClick={() => setScenarioId(id)}>{label}</button>)}</div></div>
                </>
              ) : (
                <>
                  <div className="controlIntro"><span className="panelKicker">Live control panel</span><p>Move any slider; results update immediately.</p></div>
                  <div className="sliderList">
                    {inputControls.map((control) => (
                      <label key={control.key} className="sliderControl">
                        <span><b>{control.label}</b><output>{whatIfInputs[control.key].toFixed(control.step < 1 ? 2 : 0)}{control.suffix}</output></span>
                        <input aria-label={control.label} type="range" min={control.min} max={control.max} step={control.step} value={whatIfInputs[control.key]} onChange={(event) => updateInput(control.key, Number(event.target.value))} />
                        <small><i>{control.min}{control.suffix}</i><i>Base {baseInputs[control.key]}{control.suffix}</i><i>{control.max}{control.suffix}</i></small>
                      </label>
                    ))}
                  </div>
                  <div className="labActions"><button onClick={() => setWhatIfInputs({ ...baseInputs })}>Reset base</button><button onClick={copySnapshot}>{copied ? "Copied ✓" : "Copy snapshot"}</button></div>
                </>
              )}
              <div className={`verifiedNote ${resultIsVerified ? "" : "estimated"}`}><span>{resultIsVerified ? "✓" : "≈"}</span><p><b>{resultIsVerified ? "Solver-verified result" : "Calibrated instant estimate"}</b><br />{resultIsVerified ? "13 rolling weeks · integer flows · same actual demand" : "Additive interpolation · validate with MILP before final reporting"}</p></div>
            </aside>

            <div className="labResults">
              <div className="resultHeader"><div><span className="panelKicker">{labMode === "verified" ? "Selected scenario" : "Live operational preview"}</span><h2>{labMode === "verified" ? `${activeGroup.label}: ${activeGroup.options.find(([id]) => id === scenarioId)?.[1]}` : "Combined operating assumptions"}</h2></div><span className={`scenarioTag ${resultIsVerified ? "" : "estimated"}`}>{resultIsVerified ? (labMode === "verified" ? verifiedScenario.id : exactLiveScenarioId)?.replaceAll("_", " ") : "estimated combination"}</span></div>
              <div className="comparisonGrid">
                <Metric label="Total cost" value={`R$${money.format(result.cost)}`} detail={`${signed((result.cost / base.cost - 1) * 100)}% vs base`} accent={result.cost < base.cost} />
                <Metric label="Fill rate" value={`${result.fill.toFixed(2)}%`} detail={`${signed(result.fill - base.fill, 2)} points vs base`} />
                <Metric label="Shortage units" value={money.format(result.shortage)} detail={`${signed(result.shortage - base.shortage, 0)} units vs base`} />
                <Metric label="Ending inventory" value={money.format(result.inventory)} detail={`${signed(result.inventory - base.inventory, 0)} units vs base`} />
              </div>
              <article className="scenarioChart whitePanel">
                <div className="panelHead"><div><span className="panelKicker">Base vs selected</span><h2>Cost and service trade-off</h2></div></div>
                <div className="comparisonBars"><div><span>Base cost</span><div><i style={{ width: `${base.cost / Math.max(base.cost, result.cost) * 100}%` }} /></div><strong>R${money.format(base.cost)}</strong></div><div><span>Selected cost</span><div><i className="selected" style={{ width: `${result.cost / Math.max(base.cost, result.cost) * 100}%` }} /></div><strong>R${money.format(result.cost)}</strong></div><div className="fill"><span>Base service</span><div><i style={{ width: `${base.fill}%` }} /></div><strong>{base.fill.toFixed(2)}%</strong></div><div className="fill"><span>Selected service</span><div><i className="selected" style={{ width: `${result.fill}%` }} /></div><strong>{result.fill.toFixed(2)}%</strong></div></div>
              </article>
              <article className={`interpretation ${resultIsVerified ? "" : "estimated"}`}><span>{resultIsVerified ? "Interpretation" : "Model boundary"}</span><p>{result.note}</p></article>
              {labMode === "live" && <article className="calibrationNote"><b>How the instant preview works</b><p>Each slider is piecewise-linear between the base case and its solved low/high anchor. When several sliders move, their measured changes are added. An exact check mark appears whenever the inputs match one of the twelve stored solver results.</p></article>}
            </div>
          </section>
        </div>
      )}

      <footer><div><b>Olist OR Lab</b><span>Data-driven counterfactual experiment</span></div><p>Observed demand and risk · transparent planning assumptions · 27 automated checks</p><a href="https://github.com/peishanli1013-rose/olist-forecast-or-project" target="_blank" rel="noreferrer">View project on GitHub ↗</a></footer>
    </main>
  );
}
