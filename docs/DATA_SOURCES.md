# Data sources

Every endpoint below was tested on 19 Oct 2026. Dates go to IEX as `dd-mm-yyyy`.
All requests are rate-limited to at most one every 0.4 s, and retried with
exponential backoff on 5xx and 429 responses.

| Dataset | Endpoint | Stored at | Cadence |
|---|---|---|---|
| DAM blocks | `GET https://www.iexindia.com/api/v1/dam/market-snapshot?interval=ONE_FOURTH_HOUR&fromDate=&toDate=` | `data/dam/YYYY-MM.csv` | daily; one month per call |
| RTM blocks | `…/api/v1/rtm/market-snapshot` (same params) | `data/rtm/` | daily (today is partial) |
| G-DAM blocks | `…/api/v1/gdam/market-snapshot`; price = `unconstrained_m_c_p`, with solar/wind/hydro volumes | `data/gdam/` | daily |
| HP-DAM blocks | `…/api/v1/hpdam/market-snapshot`; MCP is null when nothing clears | `data/hpdam/` | daily |
| DAM bid-area prices | `…/api/v1/dam/area-price?…&bidArea=N1,N2,…,A2` | `data/dam_area/` | daily |
| DAM unconstrained MCP/MCV | `https://iexrtmprice.com/view-dam-provisional-mcv-and-mcp-data/data/DAM_ddmmyyyy.csv` (from 1 Jan 2026) | `data/dam_umcp/` | daily |
| TAM monthly auctions | `https://www.iexindia.com/tam-monthly` (server-rendered HTML table, latest 10) | `data/tam_monthly.csv` (accumulates) | daily |
| REC sessions | `https://www.iexindia.com/market-data/REC-market-from-dec22?viewGraph=false&fromDate=1&toDate=12&instrumentType=BOTH&year=YYYY` | `data/rec_sessions.csv` | daily |
| NSE electricity futures | `https://www.nseindia.com/api/liveCommodity-derivatives?index=ELECMBL`, filtered to `contract=ELECMBL, instrumentType=FUTENR` | `data/futures.csv` (one snapshot per day) | daily |
| MCX electricity futures | Akamai blocks data-centre IPs. Put rows with the `futures.csv` columns in `data/manual/mcx_futures.csv` | manual | – |
| Open-access landed cost | `…/api/v1/calculator/{consumer-category,voltage,tod-months,tod-slots}` then `…/api/v1/calculator?state=&consumerCategory=&voltage=&todMonth=&todSlot=&iexPrice=` | `data/reference/open_access_landed_cost.csv` | monthly |
| Tenders | curated by hand; every row has a source URL | `data/reference/tenders.csv` | on each award |

## Storage format

Block files have one row per `(date, block)`. Block 1 is 00:00–00:15 IST.

```
date,block,purchase_bid_mw,sell_bid_mw,mcv_mw,scheduled_mw,mcp,congestion
2026-10-18,41,7098.00,2789.80,1611.70,1611.70,2150.56,NO
```

Prices are in ₹/MWh, as IEX publishes them, and volumes in MW for the block.
An empty `mcp` means nothing cleared; it is never zero-filled.

## Grid & balancing sources

These are checked on every daily run. Each source's status, last-checked time
and data-through date are written to `data/grid/sources.json` and shown on the
site's Source status page.

| Source | What Dhruva reads | Status (20 Oct 2026) |
|---|---|---|
| ERPC weekly accounts: links on `https://www.erpc.gov.in/` (signed, rotating) | "DSM, SRAS, TRAS and SCUC Settlement Account" PDF (₹ lakh) plus a block-wise Excel: one sheet per entity with frequency, schedule, actual, SRAS, deviation, payable, receivable and Normal Rate for every 15-minute block | ✅ parsed; every entity ties to the PDF |
| WRPC DSM accounts: `https://www.wrpc.gov.in/api/TopMenu/custom/342` | DSM PDF (₹) plus an all-member zip of per-constituent CSVs (the same block columns, plus the nuclear-station adjustment for states) | ⚠️ parsed. Every account row ties to the block data, but WRPC's printed totals differ from the sum of its rows, so the account is flagged "Totals don't tie" |
| WRPC SRAS/TRAS: `https://www.wrpc.gov.in/api/TopMenu/custom/348` | "TRAS SRAS & SCUC" weekly PDF. Single-entity revisions ("... of TPCL_Mundra ...") are used only when no full account is listed | ✅ parsed |
| NERPC: `https://nerpc.gov.in/?page_id=5872` | Provisional DSM and SRAS/TRAS statements (PDF), plus a data zip of DeviationDetails, SRAS (15- and 5-minute), TRAS and SCUC workbooks. Two-week statements are split into their weekly accounts | ✅ parsed; DSM, SRAS and TRAS all tie to the PDFs |
| NRPC: `https://nrpc.gov.in/` | its document API answers 401 without a login | ❌ flagged; no workaround attempted |
| SRPC: `https://srpc.kar.nic.in/` | TLS handshake reset from our network | ❌ flagged |
| Grid-India: `report.grid-india.in`, `grid-india.in` (frequency profile, AS dispatch) | connection refused by the gateway from this network; may need the host allow-listed | ❌ flagged |
| PXIL TRAS results | TLS reset from our network | ❌ flagged |
| IEX / HPX TRAS results | no public TRAS data on either site | ❌ flagged "Not published" |

**Storage.**

- One JSON file per RPC week: `data/grid/weeks/<rpc>_<week-start>.json`. It
  holds the document titles and URLs, the parse status of every table, and
  the rows.
- Block-level data, every entity and every 15-minute block (5-minute for
  NERPC SRAS), is stored as gzip CSV:
  `data/grid/blocks/{dsm,sras,sras_5min,tras,scuc}/<rpc>_<week-start>.csv.gz`.
  This is about 1 MB a week across the three RPCs. Each week's JSON records
  how the block data reconciles with the PDF (Methodology §5.1).
- The site's per-entity drill-down files (`site/data/grid/`) are rebuilt from
  those CSVs on every build and are not committed.
- The last 8 weeks per RPC are checked on each run. Older weeks stay in
  `data/` once fetched.
- Original downloads are cached in `data/grid/_raw/`, which is git-ignored.
- A week is parsed again only when a document's title changes (a revision)
  or the parser version changes.

**PDF parsing.**

- PDFs are converted with `pdftotext -layout` (poppler-utils). Table rows are
  read either by serial number or by column position.
- Every table is checked against its own TOTAL row before it is published
  (see Methodology §5).

## Known gaps

- **NRPC and SRPC accounts, and Grid-India.** Without these, DSM covers 3 of 5
  regions, frequency is 15-minute block averages rather than Grid-India's
  10-second profile, and there is no Grid-India AS dispatch report. See the
  table above.
- **TRAS clearing prices by block.** Available only where NERPC providers
  cleared. Exchange TRAS results are not public.
- **RTM bid-area prices.** `/api/v1/rtm/area-price` returns no rows.
- **PXIL and HPX.** Not ingested. Since DAM market coupling (Jan 2026) the DAM
  price is common across exchanges, but RTM and TAM are not coupled.
- **Licensing.** IEX and NSE data are public, but redistribution terms should
  be reviewed before any commercial launch. The Pro and Enterprise tiers
  should resell Dhruva's derived analytics, not the raw exchange feed.
