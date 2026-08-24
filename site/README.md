# Olist OR Lab — Interactive MVP

This folder contains the interactive results website for the Olist forecast-driven inventory and fulfillment project.

Live site: [Olist OR Lab](https://olist-forecast-or-lab.peishanli1013.chatgpt.site)

## What the MVP shows

- observed demand concentration and historical route risk;
- comparison of last-week, four-week moving-average, and pooled Ridge forecasts;
- 13-week rolling policy results and regional fill rates;
- eleven solver-verified one-factor-at-a-time sensitivity scenarios.

The sensitivity controls select previously solved MILP scenarios. They do not interpolate or invent results for untested parameter combinations.

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
