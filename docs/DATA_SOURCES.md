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

## Known gaps

- **SRAS/TRAS clearing prices.** These are published weekly by the RPCs as PDFs
  (e.g. ERPC "DSM, SRAS, TRAS and SCUC Accounts"). A PDF parser is on the
  roadmap.
- **RTM bid-area prices.** `/api/v1/rtm/area-price` returns no rows.
- **PXIL and HPX.** Not ingested. Since DAM market coupling (Jan 2026) the DAM
  price is common across exchanges, but RTM and TAM are not coupled.
- **Licensing.** IEX and NSE data are public, but redistribution terms should
  be reviewed before any commercial launch. The Pro and Enterprise tiers
  should resell Dhruva's derived analytics, not the raw exchange feed.
