# Dhruva index methodology (v1.0)

_Effective 19 Oct 2026. Benchmark administrator: Dhruva. Changes are versioned
and logged at the end of this document._

Dhruva publishes two benchmark families:

1. **DBI-M**, the Dhruva Base Index (monthly): the reference number for Indian
   base-load power in a calendar month.
2. **DBX**, the Dhruva BESS-IN battery revenue index: what a reference battery
   would have earned from exchange arbitrage.

Both are computed only from public exchange data, with open-source code
(`dhruva/analytics/`), so anyone can reproduce every published value.

## 1. Dhruva Base Index (DBI-M)

**Definition.** The volume-weighted average of the IEX Day-Ahead Market
unconstrained market clearing price (UMCP) over every 15-minute block of a
calendar month. Each block is weighted by its unconstrained market cleared
volume (MCV).

```
DBI-M(month) = Σ_blocks UMCP_b × UMCV_b  /  Σ_blocks UMCV_b
```

- **Why this definition.** MCX and NSE monthly electricity futures are
  cash-settled on the month's volume-weighted DAM UMCP. DBI-M tracks that
  settlement basis every day, so it doubles as a month-to-date fair value for
  the expiring contract.
- **Month to date.** The same formula over the delivery days published so far.
  DAM results for D+1 are published around 13:00 IST, so the index includes
  tomorrow once it has cleared.
- **Fallback.** Before IEX began publishing daily UMCP files (January 2026),
  and on any day the file is missing, that day uses the cleared MCP × MCV.
  About a quarter of 2026 days have no file at the source. Each month is
  published with its UMCP coverage (`UMCP`, `UMCP n/N days` or `MCP`). In
  uncongested blocks the two prices are equal.
- **Simple vs weighted.** The simple block average is shown alongside it but
  is not the index. Cheap solar blocks clear far more volume than the evening
  peak, so the two can differ by more than ₹1/kWh.

## 2. Dhruva BESS-IN (DBX)

### 2.1 What it measures

The revenue a **1 MW** battery would have earned from **perfect-foresight
energy arbitrage** on IEX 15-minute prices, for each delivery day. It is a
**ceiling**: it assumes the operator knew every price in advance and always
cleared. Realised merchant revenue will be lower, because of forecast error,
bid non-clearance, availability and degradation management.

India has no public asset-level battery dispatch or settlement data, so a
measured index on the model of Modo's ME BESS GB is not yet possible. DBX
follows the simulated approach Modo uses for Germany.

### 2.2 Index family

| Ticker | Market | Duration | Max cycles/day | Role |
|---|---|---|---|---|
| **DBX-2H** | DAM | 2h (1 MW / 2 MWh) | 1 | headline |
| **DBX-4H** | DAM | 4h (1 MW / 4 MWh) | 1 | headline |
| DBX-2H-2C | DAM | 2h | 2 | sensitivity |
| DBX-RTM-2H | RTM | 2h | 1 | sensitivity |
| DBX-RTM-4H | RTM | 4h | 1 | sensitivity |
| DBX-2H-{area} | DAM bid-area price | 2h | 1 | regional (Enterprise) |

### 2.3 Optimisation

For each day independently, solve the linear programme:

```
maximise   Σ_t Δt · [ (p_t − f) · d_t  −  (p_t + f) · c_t ]
subject to s_t = s_{t−1} + Δt · (η · c_t − d_t / η)
           0 ≤ s_t ≤ E,          s_0 = s_T = 0
           0 ≤ c_t, d_t ;  c_t + d_t ≤ P
           Δt · Σ_t d_t / η ≤ N · E
```

| Symbol | Meaning | Value |
|---|---|---|
| `t` | 15-minute block, 1…96 | |
| `Δt` | block length | 0.25 h |
| `p_t` | MCP in block `t` (₹/MWh) | from IEX |
| `c_t`, `d_t` | grid-side charge / discharge power (MW) | |
| `s_t` | stored energy (MWh) | |
| `P` | power | 1 MW |
| `E` | energy | duration × 1 MW |
| `η` | one-way efficiency | √0.85 (85% round trip) |
| `f` | exchange transaction fee, each side | ₹20/MWh (CERC cap of 2 paise/kWh) |
| `N` | cycle limit | 1 (or 2) full cycles of storage throughput per day |

The LP is solved with HiGHS (SciPy `linprog`). Days are independent: the
battery starts and ends each day empty. Any day missing a block price is
skipped, never interpolated.

### 2.4 Outputs and units

- **Daily:** ₹ per MW of power capacity, plus cycles used and the
  volume-weighted buy and sell prices.
- **Monthly:** the sum of daily values in **₹ lakh/MW/month**. This is the unit
  Indian BESS tenders use (for example, GUVNL Aug 2026: ₹2.32 lakh/MW/month),
  so the merchant ceiling and the contracted tariff can be compared directly.
- **Run-rate** for a month in progress: mean daily value × days in the month.
- **Trailing 12-month:** mean daily value over the last 365 published days ×
  365 / 12.

### 2.5 Exclusions in v1.0

These are deliberate and will be revisited through consultation:

- Ancillary-service (SRAS/TRAS) revenue, and capacity or tender payments.
- Transmission charges and losses. ISTS waivers for storage vary by
  commissioning date.
- Degradation cost and availability derating.
- The DSM exposure of a real bidding strategy.
- Combined DAM + RTM optimisation. Each market is indexed separately.

## 3. Other published measures

- **DSM Normal Rate (indicative).** Per block, (DAM ACP + RTM ACP + ASC) / 3 as
  in the CERC DSM Regulations 2024. In v1.0 the Ancillary Service Charge is
  not ingested, so the regulation's 50:50 DAM/RTM fallback is applied to every
  block, using IEX prices. It is labelled indicative.
- **D+1 baseline forecast.** The per-block median of the last 7 delivered DAM
  days, published with its 60-day out-of-sample mean absolute error. It is a
  benchmark that better models have to beat.
- **Open-access landed cost.** Each discom × category × voltage combination is
  run through IEX's public landed-cost calculator at two exchange prices. The
  result is fitted exactly as `landed = a + b × price`.

## 4. Governance (roadmap toward IOSCO Principles)

| Stage | Commitment |
|---|---|
| v1 (now) | Open code, open data inputs, daily publication, versioned methodology, public change log |
| 6–12 months | Restatement policy: errors are corrected and logged, never silently revised. Data-input checks: block completeness, cap breaches, cross-checks of DAM against UMCP |
| 12–24 months | Oversight committee with external members (a lender, a developer, an academic). Consultation of at least 30 days before any methodology change |
| 24+ months | Third-party assurance. Co-administration with a price reporting agency |

## 5. Change log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-10-19 | First publication. DBX-2H/4H (DAM, 1 cycle), sensitivities, regional 2H. DBI-M on UMCP with an MCP fallback |
