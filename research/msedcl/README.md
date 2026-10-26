# MSEDCL procurement, April–October 2026

The goal is to see the market as one discom sees it: every unit it bought, from whom, when, at what price, and what it did when supply fell short. **MSEDCL** (Maharashtra State Electricity Distribution Co.) is India's largest discom, supplying about 85% of Maharashtra's energy. It was chosen because Maharashtra's load despatch centre, MSEDCL itself and the state regulator (MERC) publish data that can be reached from here; Gujarat's sites cannot.

Collected on 26 Oct 2026, from public sources only. Nothing was logged into, and no missing number has been filled in. Every assumption is labelled in the data.

## What is here

| Folder | Source | Coverage | What it holds |
|---|---|---|---|
| `msldc/` | Maharashtra State Load Despatch Centre (mahasldc.in): daily system reports, monthly reports, MSEDCL's scheduling feed | 1 Apr–20 Oct (daily reports); 11 Sep–25 Oct (schedules) | Demand, hourly load by source, unit-wise generation, outages, load shedding; MSEDCL's 15-minute schedules by seller and contract; declared capability by seller; one week of intra-state DSM. See `msldc/findings.md`. |
| `wrpc/` | Western Regional Power Committee weekly DSM files | 6 Apr–11 Oct (189 days) | Block-level Maharashtra drawal, schedule, deviation and DSM ₹, with IEX prices joined (`mh_blocks.csv.gz`); daily schedule from every central station by beneficiary (`mh_isgs_daily.csv`). These are state-level, not MSEDCL-only. |
| `msedcl_merc/` | MSEDCL website and MERC orders (several are scanned PDFs, read by OCR) | Monthly actuals to Feb 2026; FY2026-27 approved plan | Source-wise monthly purchases (MU, ₹ crore) Mar 2025–Feb 2026; daily exchange purchases to Mar 2026; the MERC-approved FY27 monthly volume and energy charge for 68 sources; the PPA list with capacity and fixed/variable charges; RE contracts; FY26 accounts. See `source_manifest.csv`. |
| `ledger/` | Built from the above (`scripts/build_ledger.py`) | 11 Sep–25 Oct (45 days) | **`msedcl_ledger_daily_by_seller.csv`:** one row per day per seller, giving MU, supply group, contract type, the MERC source it maps to, energy charge, cost, price basis, declared capability, undrawn capacity. `msedcl_sales_daily.csv`: what MSEDCL delivered to others (swap returns). |
| `news_and_regulatory.md` | Web research (each fact carries its source URL and is flagged primary, claim, secondary or snippet) | Mar–Oct 2026 | Timeline of load shedding, coal stocks, outages, Section 11 orders, new contracts (round-the-clock renewables, thermal, battery storage, farm-feeder solar), MERC orders. |
| `scripts/` | Collection and parsing code | | |

## How the ledger prices each unit

- **Contracted power:** the scheduled MU from MSEDCL's own schedules × the **MERC-approved FY2026-27 energy charge** for that source and month. This is the variable cost only. Capacity (fixed) charges are owed whether or not a plant is dispatched, so they do not drive day-to-day decisions; they appear in the PPA list and the annual plan.
- **Exchange purchases:** each 15-minute block's scheduled MW × that block's actual clearing price on IEX, PXIL or HPX.
- **Short-term inter-state purchases** (Jindal, Mahan, Vedanta, APL Raipur and others): deal prices are not published, so they are priced at MERC's approved short-term rate (₹5.50/kWh) and marked `price_basis = assumed`.
- **Swap or banking returns from other states** (UPPCL, JBVNL, APDCL, Haryana and others) are settled in energy, not money, and are left unpriced.
- **Not priced:** NEEPCO Kameng hydro, which is not in MERC's FY27 plan.

## Main numbers

- **Demand:** MSEDCL supplied about 538 MU/day, peaking at 28,221 MW on 10 Oct; Maharashtra as a whole peaked at 33,051 MW on 17 Oct.
- **Purchases, 11 Sep–25 Oct:** 25,176 MU scheduled (559 MU/day); 98% of it is priced; energy-charge cost ₹9,441 crore, an average of ₹3.82/kWh.

| Supply group, 11 Sep–25 Oct | MU/day | Share | Avg energy charge (₹/kWh) |
|---|---|---|---|
| MSPGCL thermal | 147 | 26% | 4.16 |
| Central stations | 136 | 24% | 3.14 |
| Renewable contracts | 68 | 12% | 3.25 |
| Tiroda, SWPGL and Uran on long-term contracts | 66 | 12% | 4.33 |
| RattanIndia and JSW on long-term contracts | 31 | 6% | 3.10 |
| Medium- and short-term in-state contracts | 30 | 5% | 5.32 |
| **Exchanges (day-ahead, green day-ahead, real-time)** | **27** | **5%** | **6.32, actual (₹763 crore in 45 days)** |
| Hydro (mostly Koyna) | 19 | 3% | 0 |
| Short-term inter-state purchases | 18 | 3% | 5.50, assumed |
| Swap returns from other states | 8 | 1% | not priced |

- **Load shedding for supply shortfall:** about 105 MU between 1 Apr and 20 Oct. The worst month was September (40.6 MU over 16 days); the highest single cut was 2,050 MW on 25 May.
- **The evening gap:** MSEDCL's own forecast of demand runs 470–570 MW above what it managed to schedule at 18:00–20:00.
- **Deviation charges:** Maharashtra's state-level DSM bill was about ₹204 crore net in September and ₹202 crore in 1–11 Oct, mostly in blocks where the day-ahead market was at its ₹10 cap.

## Gaps

- **No source-by-source actuals for April–October 2026 have been published.** MSEDCL's monthly power-purchase statements stop at Feb 2026, its exchange-purchase files at Mar 2026, and MERC's fuel-adjustment approvals at Jun 2025.
- **The ledger window is short.** MSEDCL's schedules can only be fetched 45 days back, so seller-level detail exists only for 11 Sep–25 Oct.
- **Interstate figures are state-level.** WRPC and SLDC interstate numbers cover all of Maharashtra, Mumbai's utilities included.
- **Intra-state DSM:** only one week (14–20 Sep) is published.
- **Not found:** prices of individual short-term deals and their e-DEEP results; swap terms; MSEDCL's dues on PRAAPTI (the government's generator-payments portal).
- **No OCR for the resource-adequacy studies.** They are scanned images and were read by eye only.
