# Research: what exists, what India lacks, what we can get

_Compiled 19 Oct 2026. Every figure below has a source link; anything we could
not verify is marked as such._

## 1. The global models

| Company | What they sell | How the number becomes a benchmark | What we copy |
|---|---|---|---|
| **Modo Energy** (London) | Per-seat subscriptions by region (GB, ERCOT, Germany, Australia…) plus add-ons. Raised $33M in Dec 2025 to push AI research tools. | The **ME BESS GB index**: revenue a representative battery fleet actually earned, built from public settlement data, calculated every half-hour, weighted by MW/MWh. Variants for 1h and 2h. Lenders write it into debt models. In Germany, where there is no asset-level data, Modo publishes a **simulated** index: a MILP dispatch model run against public prices. | A battery revenue index with a published methodology, duration variants, and a simulated approach (India has no public asset-level battery data, so we are in the "Germany" case). Free research to build an audience first. |
| **Pexapark** (Zurich) | Long-term PPA price data, valuation and advisory. | With S&P Global/Platts, the **3Pi** indices (from Feb 2023): daily evaluated PPA prices by country and technology, e.g. a German 10-year onshore wind pay-as-produced index. Third-party administration gives it benchmark credibility. | Daily, by-technology evaluated prices; partner with an established price-reporting agency once the series has a track record. |
| **LevelTen Energy** (Seattle) | PPA marketplace. | Quarterly **PPA Price Index**: P25 of live offers, by ISO and technology, with a developer survey. | Use tender results as India's "PPA offers" and publish percentiles each quarter. |
| **Grid Status** (US) | Free real-time ISO data plus paid API, alerts and Snowflake delivery ($8M seed, Aug 2024). | Not a benchmark. It wins by being the fastest, cleanest free view of raw market data. | The free tier must be the best free view of IEX anywhere. |
| **Aurora, Montel/EnAppSys, Wood Mackenzie** | Forecasts, fundamentals, advisory. | Long-run forecasts that banks commission. | The later-stage paid tier (forecasts), not where we start. |

Sources: [Modo methodology (GB)](https://modoenergy.com/methodology/gb) ·
[Modo benchmark docs](https://benchmarkdocs.modoenergy.com) ·
[ME BESS index release](https://modoenergy.com/research/me-bess-gb-index-battery-energy-storage-product-release-december-2024/) ·
[Modo DE simulated benchmark](https://modoenergy.com/benchmarking/methodology/germany) ·
[Modo raise, ESS News](https://www.ess-news.com/2025/12/03/modo-energy-raises-33m-and-sets-out-ai-ambitions/) ·
[S&P–Pexapark 3Pi](https://press.spglobal.com/2022-06-30-S-P-Global-Commodity-Insights-Joins-with-Pexapark-to-Create-New-Benchmark-for-Renewable-Energy-Pricing) ·
[Platts 3Pi launch note](https://www.spglobal.com/energy/en/pricing-benchmarks/our-methodology/subscriber-notes/022123-platts-launches-new-power-purchase-agreement-indexes-3pi) ·
[LevelTen PPA index](https://www.leveltenenergy.com/post/2023-q3-ppa-price-index) ·
[Grid Status funding](https://nacleanenergy.com/alternative-energies/grid-status-raises-8m-to-democratize-access-to-real-time-grid-data-to-meet-demands-of-rapidly-changing-energy-grid)

**Lesson:** the benchmark comes from three things together: a free audience, a
methodology anyone can audit, and years of history published without gaps. The
data is a commodity. The methodology and the track record are the product.

## 2. India's market, as of Oct 2026

- **Spot exchanges.** IEX holds about 85% of spot volume. DAM, RTM and G-DAM
  clear in **96 × 15-minute blocks**. HP-DAM covers high-cost generators above
  the cap. The DAM/RTM price cap is **₹10/kWh** (₹10,000/MWh); IEX's own block
  data shows overnight blocks clearing at exactly 10,000 through Oct 2026.
  DAM market coupling, ordered by CERC on 23 Jul 2025, started in Jan 2026.
  ([Business Standard](https://www.business-standard.com/markets/news/market-coupling-poses-threat-to-iex-says-nuvama-assigns-reduce-tag-125110300095_1.html),
  [Powerpeak Digest](https://powerpeakdigest.com/cerc-clears-market-coupling-for-day-ahead-power-but-design-raises-concerns/))
- **Price levels.** In May 2026 DAM averaged ₹4.88/kWh, RTM ₹4.16 and G-DAM
  ₹3.60. In Feb 2026 DAM averaged ₹3.58.
  ([Mercom](https://mercomindia.com/iex-electricity-volume-rises-19-yoy-to-12983-mu-in-may),
  [Bajaj Broking](https://www.bajajbroking.in/share-market-news/iex-feb-26-highest-daily-average-electricity-volume-touches-448-mu))
  The **simple average of blocks is very different from the volume-weighted
  average**. On 1 Sep 2026, for example, the simple average was ₹5,960/MWh and
  the weighted average ₹4,349/MWh, because cheap solar blocks clear large
  volumes. Any "index" has to say which average it uses.
- **Futures.** MCX (from 10 Jul 2025) and NSE (from 14 Jul 2025) list monthly
  base-load futures with a 50 MWh lot, cash-settled. Settlement is the
  **volume-weighted average DAM UMCP** of the expiry month. NSE's specification
  references PXIL's DAM-UMCP; with coupling, the discovered price is common
  across exchanges.
  ([NSE contract spec](https://www.nseindia.com/products-services/commodity-derivatives-contract-specifications-electricity-futures),
  [Upstox expiry notice](https://upstox.com/announcements/updates/mandatory-square-off-electricity-futures-expiry-august-2026/),
  [Zerodha FAQ](https://support.zerodha.com/category/trading-and-markets/trading-faqs/f-otrading/articles/electricity-futures))
- **DSM / ancillary.** The CERC DSM Regulations 2024 apply from 16 Sep 2024,
  amended 23 Dec 2024 and 1 Jul 2025. The **Normal Rate** for each block is an
  equal-thirds blend of the weighted DAM ACP, the weighted RTM ACP and the
  Ancillary Service Charge. It falls back to 50/50 DAM/RTM when no ancillary
  service is dispatched in that block. SRAS/TRAS are settled weekly through RPC
  accounts (PDFs).
  ([Powerline on the draft](https://powerline.net.in/2024/07/02/key-amendments-highlights-of-the-draft-dsm-regulations-2024/),
  [ERPC weekly accounts](https://erpc.gov.in/wp-content/uploads/2025/09/DSM-SRAS-TRAS-and-SCUC-Accounts-for-the-period-from-01.09.2025-to-07.09.2025..pdf))
- **RECs.** Twice-monthly sessions on IEX, about ₹333–400/REC in 2026. Sell
  bids fell 77.8% YoY in July 2026, which lifted prices.
  ([Mercom](https://www.mercomindia.com/iexs-electricity-trading-volume-rises-in-july))
- **Storage and firm-RE tenders (Aug 2026, IEEFA/JMK).**
  - GUVNL 450 MW/900 MWh: ₹2.32 lakh/MW/month. Its Feb 2026 335 MW tender with
    VGF cleared at ₹2.10.
  - WBSEDCL 500 MW/2,000 MWh: ₹4.35–4.39. Its Jan 2026 tender cleared at ₹3.47.
  - SECI 1,500 MW/6,000 MWh assured peak: ₹5.99/kWh.
  - SECI 1,000 MW RTC-thermal-mimic: ₹5.25–5.26/kWh.
  - Solar is around ₹2.57/kWh, solar+BESS ₹2.86–3.13, and the SECI wind tranche
    of Jul 2026 cleared at ₹3.78–4.32.
  ([IEEFA/JMK ESS tracker Sep 2026](https://ieefa.org/sites/default/files/2026-09/ESSjmk-0926.pdf),
  [pv magazine](https://www.pv-magazine-india.com/2026/08/11/guvnl-discovers-inr-2-32-lakh-mw-month-tariff-in-450-mw-900-mwh-bess-tender/),
  [Renewable Watch](https://renewablewatch.in/2026/07/16/seci-announces-winners-of-2-gw-wind-auction/))
- **Open access.** The cross-subsidy surcharge plus the additional surcharge is
  typically ₹1.5–2.0/kWh in the large OA states (CRISIL). Every 10 paise of
  surcharge costs a developer about 150 bps of return.
  ([Indian Chemical News / CRISIL](https://www.indianchemicalnews.com/energy/lite/draft-open-access-norms-can-be-a-tailwind-for-new-renewable-projects-crisil-10428))

## 3. Who serves India today, and the gap

- **IEX** publishes raw data on its own site, one market per page, with no
  cross-market view, no index and no battery analytics.
- **IIT Kanpur Energy Analytics Lab**, funded by IEX CSR, offers academic
  dashboards.
- **GNA Energy** launched an AI forecasting platform (GNAI) in 2026.
- **Trade press** (Mercom, JMK/IEEFA, Powerline) produces monthly PDFs and
  articles.
- **No one publishes:**
  1. a single cross-market view of DAM, RTM, G-DAM, HP-DAM, TAM, futures, DSM,
     REC, tenders and open access together;
  2. a **battery revenue index** that can be compared with tender tariffs in
     the same unit (₹ lakh/MW/month);
  3. a clean **month-to-date settlement index** next to the futures curve.

That gap is the wedge.

## 4. Data we verified we can get (and what we can't)

Every row was tested from this environment on 19 Oct 2026. The details are in
[`DATA_SOURCES.md`](DATA_SOURCES.md).

| Dataset | Source | Status |
|---|---|---|
| DAM, RTM, G-DAM, HP-DAM: 15-min price and volume | IEX public JSON (`/api/v1/{dam,rtm,gdam,hpdam}/market-snapshot`) | ✅ live, history to at least Apr 2024 |
| DAM prices for 13 bid areas (regions) | IEX `/api/v1/dam/area-price` | ✅ live |
| DAM unconstrained MCP (the futures settlement basis) | `iexrtmprice.com` daily CSV | ✅ from Jan 2026 |
| TAM monthly auctions | IEX `/tam-monthly` (HTML) | ✅ latest auctions |
| REC sessions | IEX REC page (HTML, by year) | ✅ |
| NSE electricity futures | NSE `liveCommodity-derivatives` JSON | ✅ live snapshot; history builds daily |
| MCX electricity futures | MCX site | ❌ blocks cloud IPs; a manual CSV hook is provided |
| Open-access landed cost by state | IEX landed-cost calculator API | ✅ about 45 discoms, by category and voltage |
| SRAS/TRAS clearing | Grid-India / RPC weekly PDFs | ⚠️ not automated yet (roadmap). The DSM Normal Rate is computed from DAM and RTM |
| Tender results | Curated from IEEFA/JMK, Mercom, pv magazine, SECI | ✅ manual, each row sourced |
