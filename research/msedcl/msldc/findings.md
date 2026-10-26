# MSLDC — how MSEDCL met its demand, 21 Apr – 25 Oct 2026 (collected 26 Oct 2026)

Public pages only; nothing logged into; no missing values filled. CSVs are long format with a `date` (or `month`) column; units in file/column names.

## How the site works
- Report listings: `/reports/<slug>` calls `POST https://mahasldc.in/report/fetchReports` (form: t=slug, y, m, w, d, s, lang, page, per_page, csrf_token from `window.csrfHash`; needs session cookie). Returns JSON with `attachment_url` under `/assets/shared/reports/`. Client: `scripts/sldc.py`.
- SCADA pages (`report2`, `mvrreport3/5/7/8/9`) are live JPG snapshots with no history; `mvrreport2/4/6` are login-only (not accessed).
- Scheduling portal (`dsm-scheduling.mahasldc.in`) is login-only, but its public login page advertises `/WEBACCESS/getapidata?ACR=..&DATE=dd-mm-yyyy`, which needs no login. MSEDCL: last 45 days + day-ahead; other licensees: today/yesterday/day-ahead only.
- Unreachable: `old.mahasldc.in`, `mspc.co.in/fbsm-bills`.

## 1. Daily system report (slug `system-operations-daily-reports`) — 201 PDFs, 1 Apr–20 Oct
Missing: 28 Sep and 2 Oct (not listed), 21–25 Oct (not yet published).
- `daily_energy_balance_mu.csv` (Statement I, MU): MSPGCL, IPPs (APML, JSWEL, VIPL, RattanIndia Amravati, SWPGPL, Other IPP, PGPL), Mumbai generators, state totals by fuel; interstate exchange by neighbour; Mumbai schedule/drawal; MSEDCL and Mumbai bilateral (exchange part shown separately, information only); energy catered to MSEDCL, Mumbai, other discoms, state.
- `daily_peak_snapshots_mw.csv` (Statement II): ~20 items at morning peak, day peak, evening peak, night minimum.
- `hourly_load_mw.csv` (Annexure-2): 24 hourly values × 19 series (MSPGCL thermal/hydro/gas/total, wind, IPP/captive, solar, CS_share_schedule, CS_net_receipt_actual, Mumbai net exchange, MSEDCL demand met, planned and transmission-constraint load shedding, MSEDCL demand incl. LS, Mumbai, other discoms, state, frequency).
- `daily_max_demand_mw.csv`, `daily_frequency.csv`, `daily_unit_generation.csv` (Annexure-1: every unit, daily MU, MTD, max/min MW), `daily_outage_capacity_mw.csv` (Statement VI).
- Checks passed on all days: energy catered sums; MSPGCL total = parts; interstate parts = total; station totals = unit sums; hourly MSEDCL demand sums to daily energy.
- Identity: MSEDCL demand met = MSPGCL + wind + IPP/captive + solar + interstate net receipt + Mumbai exchange (negative = to Mumbai) − other discoms. Interstate schedule/actual are STATE-level.
- Issues: 1 Apr Statement II disagrees with its hourly table; Statement II vs hourly differ by 2–6 MW (rounding); some MTD values blank (layout); no bagasse/captive/small-hydro lines; "Other(Mus)" not broken down.

## 2. Monthly System Performance Report — `monthly_perf_daily_summary.csv` (1 Mar–30 Sep, covers 28 Sep)
Max/min demand with LS (MSEDCL, Mumbai, state), MSPGCL thermal/hydro/gas, wind, solar, central sector incl. and excl. deviation, Tata exchange, requirements, load shedding MU, avg frequency, Koyna water (TMC). LS MU matches hourly sums except 10 Apr, 26 Apr, 13 Jul; 13–15 Jul requirement exceeds energy catered by ~3.4 MU (kept as published).

## 3. Monthly Generation Report (Mar–Sep)
- `monthly_energy_balance_mu.csv`: 35 items — generation by fuel; interstate by neighbour; requirement; bilateral purchases by MSEDCL+other discoms (interstate import/export, "PX/IEX/REMC/Standby/RTM", intra-state); same for Mumbai incl. standby from MSEDCL; auxiliary.
- `monthly_unit_generation_mu.csv`: monthly MU, max MW, aux by unit (ambiguous merged-cell rows dropped; see logs/).

## 4. MSEDCL schedules (Web API), 11 Sep – 25 Oct
- `sched_msedcl_summary_blocks_mw.csv` (96 blocks × 26 series: centre total, intra-state LT/MT/ST and generation, RE via REMC, exchange DAM, green DAM, RTM, standby, forecast demand, target injection, surplus/shortfall); `sched_msedcl_summary_daily.csv`; `sched_msedcl_by_source_daily_mu.csv` (by seller, schedule type, sub-type, fuel); `sched_msedcl_declared_capability_daily.csv`; `sched_licensee_snapshot_2026-10-25.csv`; `sched_msedcl_revision_meta.csv`.
- Days to 18 Oct appear finalised; 19–25 Oct and 24 Sep may still be revised. "CENTRE / GRTM_HPX" (~15 MU/day solar+wind) does not match `GRTM_HPXTotal` (0); kept as published.

## 5. Intra-state DSM / FBSM
Only FY27 week 25 (14–20 Sep) available (weeks 26–28 404; 1–24 unlisted). Files: `dsm_weekly_entity_charges_rs.csv`, `dsm_daily_entity_deviation.csv`, `dsm_daily_state_periphery.csv`. MSEDCL week 25: scheduled 3,574.3 MU, drew 3,501.6 MU, net receivable Rs 9.15 crore. Net deviation statements exist only for Jul–Dec 2025; DSM pool account only FY26 (downloaded, not parsed).

## 6. Resource adequacy
Month-ahead RA and forecast-error listings empty. 2026-31 and 2025-30 studies are scanned images (no OCR). Read by eye (2026-31): contracted capacity 58,532 MW FY27 vs 34,482 MW capacity-credit availability (72,383 vs 41,216 MW FY28). Annex-3 shortfall Excel not published.

## 7. Downloaded, not tabulated
Weekly reports to 2 Aug (duplicate daily data); MOD rate stacks Apr–Oct; zero-schedule report; approved outages; UFR reports. September System Overview (narrative): load curtailment on 17 days (29 events, 43.4 MU); MSEDCL short of resources in 64% of evening blocks (avg 554 MW, max 1,645 MW); 4,074 MW thermal unavailable outside solar hours; 6.04 MU solar curtailed.

## Key numbers (21 Apr – 20 Oct)
MSEDCL 538 MU/day (Apr 588, May 576, Jun 545, Jul 478, Aug 503, Sep 541, Oct 587); Mumbai 79.9; other discoms 14.2; state 632. Peaks: MSEDCL 28,221 MW (10 Oct), state 33,051 MW (17 Oct). Mix of MSEDCL demand: interstate net 39.5%, MSPGCL thermal 29.2%, IPP/captive 27.2%, wind 6.5%, solar 5.6%, MSPGCL hydro 3.1%, Uran gas 1.1%, net to Mumbai −9.5%. Load shedding ~112 MU planned + 7.4 MU transmission (Apr 0.5, May 23.4, Jun 28.1, Jul 7.4, Aug 0.4, Sep 43.6, Oct 1–20 15.8). Min frequency 49.33 Hz (6 Oct).
