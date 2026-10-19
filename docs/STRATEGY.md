# Dhruva — strategy & build plan

## Name

**Dhruva** (ध्रुव) is the pole star: the one fixed point navigators steer by.
The company's goal is to be the fixed reference number for Indian power prices,
and the name says that. It is short, pronounceable in every Indian language and
in English, and has no conflict we could find in Indian power-market data.
_A formal trademark search (Class 9/35/36/42) is still required before launch._

Product naming follows the Modo "ME BESS" and Platts "3Pi" pattern:

| Name | What it is |
|---|---|
| **Dhruva Terminal** | the dashboard |
| **Dhruva BESS-IN index** | battery revenue benchmarks. Tickers: `DBX-2H` and `DBX-4H` (DAM, 1 cycle/day), plus RTM and 2-cycle variants |
| **Dhruva Base Index** (`DBI-M`) | month-to-date volume-weighted DAM UMCP, the futures settlement basis |
| **The Dhruva Weekly** | free Monday note |

## Positioning

> One screen for every Indian power price — and the battery revenue number
> lenders can write into a loan.

## Who pays, for what

| Buyer | Job to be done | Tier |
|---|---|---|
| Traders and discom desks | block-level prices across markets, MTD vs futures, alerts | Pro |
| BESS / RE developers | merchant revenue vs tender tariff, regional spreads, history | Pro / Enterprise |
| Lenders (REC Ltd, PFC, IREDA, banks) | an independent, auditable revenue benchmark for debt sizing | Enterprise (index licence) |
| Funds entering India | one place to learn the market, plus data downloads | Pro / Enterprise |
| Open-access C&I buyers | landed cost by state vs discom tariff | Free → Pro |

## Tiers

| | Free | Pro (per seat) | Enterprise / index licence |
|---|---|---|---|
| Today and the last 30 days, all markets | ✅ | ✅ | ✅ |
| Weekly note | ✅ | ✅ | ✅ |
| Dhruva BESS-IN headline (monthly) | ✅ | ✅ | ✅ |
| Full history (from Apr 2024) | – | ✅ | ✅ |
| CSV / API downloads | – | ✅ | ✅ |
| D+1 baseline forecast; later, ML forecasts | – | ✅ | ✅ |
| Price alerts (block/peak thresholds, futures basis) | – | ✅ (roadmap) | ✅ |
| Regional (bid-area) BESS indices, custom battery specs | – | – | ✅ |
| Right to reference DBX in contracts and loan agreements | – | – | ✅ |

Indian buyers pay little for data. The free tier is the marketing, and the
Pro price stays low (≈ ₹4–8k/seat/month). The money is in index licences and
in the credibility it lends the trading business.

## Audience engine (how Modo and Pexapark won)

1. **The Dhruva Weekly.** It is generated from the data each Monday
   (`python -m dhruva weekly`). An analyst then adds two paragraphs. Post it to
   LinkedIn and email.
2. **Monthly "Battery Report"**: DBX vs tender tariffs, and the regional spread
   table.
3. **Livestream at each futures expiry**: MTD index vs final settlement.
4. **Open methodology**: publish `METHODOLOGY.md`, version it, and keep a
   change log, the way Modo publishes its index versions.

## Path to a benchmark

1. **Now:** a simulated, perfect-foresight index from public prices, fully
   open-source and reproducible.
2. **6–12 months:** an uninterrupted daily series and a change log. Publish
   restatements openly.
3. **12–24 months:** align governance with the **IOSCO Principles for
   Financial Benchmarks**: an oversight committee, a methodology consultation
   process, and data-input controls. Add a measured index once operators share
   meter data.
4. **24+ months:** co-brand with a price reporting agency (the Platts–Pexapark
   model), or get named in a lender's model and a CERC/SERC submission.

## Build plan (this repo)

| Layer | Choice | Why |
|---|---|---|
| Ingestion | Python package `dhruva/`, stdlib HTTP, polite rate limit | runs anywhere, including GitHub Actions cron |
| Storage | month-partitioned CSV under `data/` | diff-able in git, auditable, trivial to load |
| Analytics | NumPy + SciPy HiGHS LP for battery dispatch | standard, exact, documented |
| Site | static HTML + vanilla JS + hand-built SVG charts | free hosting (GitHub Pages), no build step |
| Refresh | GitHub Actions daily at 14:00 IST (after DAM results) | zero infrastructure |

**Roadmap after v1:**

- Automate SRAS/TRAS from the RPC weekly accounts.
- MCX feed from an Indian IP.
- A real paywall (auth plus a signed API).
- Email alerts.
- An ML price forecast, published with its backtest.
- A PPA/tender percentile index on the LevelTen model.
