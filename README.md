# Dhruva — India power price terminal

**Every Indian power price on one screen, and the battery revenue number
lenders can write into a loan.**

Dhruva (ध्रुव, the pole star) tracks Indian power prices from public data.
Modo Energy (battery indices) and Pexapark / Platts 3Pi (PPA benchmarks) are
the models.

- **Spot.** IEX Day-Ahead, Real-Time, Green Day-Ahead and High-Price DAM, by
  15-minute block, from April 2024.
- **Regions.** DAM prices for all 13 IEX bid areas, and how often the grid
  splits.
- **Futures.** NSE electricity futures (MCX via a manual hook) against the
  **Dhruva Base Index (DBI-M)**, the month-to-date volume-weighted DAM UMCP
  these contracts settle on. Also IEX term-ahead monthly auctions.
- **Balancing.** The block-wise DSM Normal Rate, computed under the CERC DSM
  Regulations 2024.
- **RECs.** Every IEX session.
- **Tenders.** BESS, FDRE, solar, solar+storage and wind awards, each with its
  source.
- **Open access.** Landed cost against the discom tariff for about 39 discoms,
  by category and voltage.
- **Dhruva BESS-IN (DBX).** What a 2-hour and a 4-hour battery would have
  earned each day. It is stated in ₹ lakh/MW/month, the unit Indian BESS
  tenders use.
- **The Dhruva Weekly.** A Monday note drafted from the data.

## Run it

```bash
pip install -r requirements.txt
python -m dhruva -v daily          # ingest → derive indices → draft weekly → build site JSON
python -m http.server -d site 8000 # open http://localhost:8000
```

Individual steps:

```bash
python -m dhruva ingest [--from 2024-04-01] [--only spot|areas|umcp|tam|rec|futures|landed_cost]
python -m dhruva derive     # DBX family (incremental; only new days are solved)
python -m dhruva weekly     # notes/<week-ending>.md (never overwrites an edited note)
python -m dhruva build      # site/data/*.json
python -m pytest -q
```

A GitHub Actions workflow (`.github/workflows/daily.yml`) runs the whole
pipeline at 14:10 IST, after D+1 DAM results are out. It commits the new data
and deploys `site/` to GitHub Pages.

## Layout

```
dhruva/               Python package (stdlib HTTP + NumPy/SciPy)
  sources/iex.py      IEX JSON API, UMCP CSVs, TAM/REC HTML, landed-cost calculator
  sources/nse.py      NSE electricity futures snapshot
  analytics/bess.py   battery LP (HiGHS)
  analytics/indices.py  VWAP/MTD index, DSM Normal Rate, baseline forecast
  ingest.py derive.py build.py weekly.py
data/                 month-partitioned CSVs (raw exchange data + derived indices)
data/reference/       tenders.csv (curated), open_access_landed_cost.csv
site/                 static terminal (vanilla JS, hand-built SVG/canvas charts)
docs/                 RESEARCH, STRATEGY, METHODOLOGY, DATA_SOURCES
notes/                The Dhruva Weekly
```

## Plans

**Free:** every market, today and the last 30 days, plus the weekly note.

**Pro:** full history, CSV downloads, forecasts and alerts.

**Enterprise:** a licence to reference DBX and DBI-M in contracts and loans,
plus regional and custom battery indices.

The site has a *Pro preview* toggle. No payments are wired up yet. See
[`docs/STRATEGY.md`](docs/STRATEGY.md).

## Read next

- [`docs/RESEARCH.md`](docs/RESEARCH.md): the global models, the Indian market,
  the gap, and which data is actually reachable.
- [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md): exact definitions of DBI-M and
  DBX, exclusions, and the governance roadmap.
- [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md): every endpoint, its cadence,
  and the known gaps.

_Dhruva indices are simulated benchmarks computed from public exchange data.
They are not investment advice._
