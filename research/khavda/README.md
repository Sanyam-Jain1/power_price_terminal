# One producer's view: Adani Green's Khavda park, Apr–Oct 2026

This is the mirror image of the MSEDCL study (`research/msedcl`): the market as a renewable generator sees it. It covers what the plant could have produced, what it was allowed to inject, who it sells to and at what price, what it pays or earns on deviations, and what it loses to curtailment.

**Why Khavda:**
- In Kutch, Gujarat. It is the world's largest renewable park: 10,752 MW operating at 30 Sep 2026, plus 6.6 GWh of batteries.
- Owned by Adani Green Energy (AGEL), a listed company that publishes quarterly results.
- WRPC publishes its 15-minute injection, schedule, settlement rate and deviation charges.

**How the data was gathered:**
- Collected 28 Oct 2026, from public sources only. Nothing was logged into.
- Every estimate is labelled as one.
- Grid-India and WRLDC sites cannot be reached from here, so buyer-level schedules (who received each block) are not available. Buyers come from company filings and CERC orders instead.

## Files

| File | What it holds |
|---|---|
| `data/wrpc_re_plants.csv` | Every wind, solar and hybrid seller in WRPC, 6 Apr–18 Oct 2026: capacity, output, capacity factor, night share, PPA rate, settlement rate, day-ahead capture price, deviation charges and deviation %. |
| `data/khavda_ps1_*`, `data/khavda_ps3_*` | The two Adani aggregator (QCA) entities at Khavda, by day, by month, and by month × hour. |
| `data/blocks_khavda_and_peers.csv.gz` | 15-minute rows for PS1, PS3 and three PPA solar or wind plants nearby, joined to IEX day-ahead, real-time, green day-ahead and high-price day-ahead prices. |
| `data/khavda_ps1_potential_blocks.csv.gz` | PS1's estimated potential output and curtailment per block. |
| `data/khavda_ps1_storage_options.csv` | Battery-behind-the-bottleneck model results. |
| `company.md` | AGEL disclosures: capacity, every buyer and tariff, grid access, results, curtailment, debt. Flagged and sourced. |
| `regulation.md` | Deviation, curtailment, REC, ISTS-waiver and PPA rules, plus 2025–26 auction tariffs. Flagged and sourced. |
| `scripts/` | `parse_all.py` (WRPC zips → blocks), `ledger.py`, `storage.py`, `prices.py`; `agent/` holds the regime-fit and capture-price checks. |

**Source of the block data:** the WRPC weekly "all-member block-wise data" zips, 28 weeks (6 Apr–18 Oct 2026). Each wind or solar seller's file carries:
- actual and scheduled MWh, deviation and its % of available capacity;
- deviation payable and receivable;
- the **rate WRPC used to settle the deviation**: the PPA tariff if one is declared, otherwise the weighted average of the seller's transactions in that block;
- available capacity.

## 1. What Khavda is, and who buys it

- **Capacity:**
  - 10,752 MW at 30 Sep 2026: AGEL's own 10,002 MW plus 750 MW for Ambuja Cements and Adani Ports.
  - Most of it is solar; about 1.4 GW is wind and about 1 GW hybrid.
  - Battery capacity went from 1.4 GWh (Mar) to 6.6 GWh (Sep).
- **How it appears in WRPC:**
  - **PS1 aggregator** (`AREH5L_KHAVDAPS1_QCA`): about 7.6 GW of available capacity. Members are about 13 Adani project companies plus the group-company plants.
  - **PS3 aggregator** (`AREH5L_KHAVDAPS3_QCA`): 2.2–4.0 GW.
- **Buyers by capacity** (AGEL asset annex, about 10 GW):

| Buyer | MW | Tariff ₹/kWh | Who ends up paying |
|---|---|---|---|
| SECI, manufacturing-linked tender, Packages II–IV | ~4,450 | 2.42 | Andhra Pradesh discoms, at ₹2.49 |
| SECI, Package I | ~800 | 2.54 | Odisha, Chhattisgarh, Tamil Nadu, J&K, BEST, Tripura |
| SECI hybrid | ~600 | 2.41 | – |
| Torrent | 150 | 2.22 | – |
| PTSL (Adani Energy Solutions subsidiary, a **related party**): solar / wind / hybrid | ~1,680 / ~1,050 / ~500, plus ~800 in process | 2.67–2.70 / 3.80–3.93 / 2.61–3.90 | Commercial and industrial customers of AESL |
| PTSL battery contract (15 years) | 3.5 GWh | 4.8 | – |
| MSEDCL, 5 GW contract (LoI 2024) | 0 operating yet | 2.70 | MSEDCL |

- **Sold on the market for now:** much of the SECI capacity is "infirm". Its PPA is signed, but supply starts only when grid access and transmission are in place.
  - Until then it is sold on the exchanges. AGEL's merchant price was **about ₹2.4/kWh in Q2 FY27**.
  - Portfolio-wide, 16.6% of H1 FY27 energy was infirm or merchant. Khavda is where that capacity sits.

## 2. What it generated (WRPC, 6 Apr–18 Oct 2026)

| | PS1 | PS3 |
|---|---|---|
| Output | 9,477 MU (48 MU/day) | 3,688 MU (19 MU/day) |
| Capacity factor on available capacity | 26.6% | 30.4% |
| Share of output at night (19:00–06:00) | 14% | 32% |
| Day-ahead price weighted by its output ÷ time-average price | 0.62 | 0.84 |

- **Capture ratio:** PS1 earns 62% of the average day-ahead price because its output peaks at midday, when prices are ₹1.4–2.1/kWh. At 19:00–23:00 prices are ₹9–10.
- **Same pattern across WRPC** (24 Aug–18 Oct, all plants): solar captures about 50% of the average, hybrid 76%, wind 90%.

## 3. Curtailment: the dominant fact

- **Evidence of a ceiling:**
  - PS1's highest schedule of the day fell from about 5,800 MW in April to a near-flat **4,100–4,400 MW from June onward**.
  - Its available capacity stayed at 7.6–7.8 GW.
  - Nearby PPA solar plants (NTPC REL, GIPCL, SAEL at KPS2) run at about 90% of capacity at midday.
  - On clear days PS1's midday output is flat and tracks its schedule. That is the signature of a plant held back to what it can evacuate.
- **Why:**
  - WRLDC's grid access for the PS1 aggregator is only **3,367 MW (Apr–Jun) and 3,525 MW (from Jul)**, and 1,000 MW for PS3.
  - The 7 GW Phase III corridor that would give AGEL its full access slipped to **Jan–Mar 2027**.
  - WRPC bills the injection above grid access at the transmission rate. For PS1 that was 67 GWh (₹2.7 crore) in April.
- **Estimate** (`scripts/storage.py`):
  - Method: PS1's potential output is fitted each month as a × (solar factor of the KPS2 peers) + b × (wind factor of Kutch wind peers), on blocks where solar is below 45% of capacity, and applied to the midday blocks.

| Month | Potential GWh | Actual GWh | Curtailed GWh | Share |
|---|---|---|---|---|
| Apr (from 6th) | 1,840 | 1,365 | 444 | 24% |
| May | 2,382 | 1,712 | 630 | 26% |
| Jun | 2,137 | 1,633 | 470 | 22% |
| Jul | 1,779 | 1,404 | 314 | 18% |
| Aug | 1,672 | 1,362 | 241 | 14% |
| Sep | 1,594 | 1,251 | 293 | 18% |
| Oct (to 18th) | 924 | 751 | 149 | 16% |
| **Total** | **12,327** | **9,477** | **2,540** | **21%** |

- **What that lost energy is worth:** ₹561 crore at the day-ahead price of each block, or ₹615 crore at the ₹2.42 SECI tariff.
- **Cross-check against AGEL:**
  - Solar grid availability was **78.9%** in H1 FY27, i.e. 21% lost.
  - Management put the H1 FY27 EBITDA loss from curtailment at **about ₹724 crore**, portfolio-wide but mostly Khavda.
  - Management's other figure is smaller: Khavda's solar capacity factor loses 2.5–3 points (about 10%). The true figure is probably between 10% and 21%.
- **No compensation:** PPA compensation covers only power that was scheduled and then cut. Power that could never be scheduled because of the access limit is not paid.

## 4. What it earns per unit

- **WRPC's settlement rate for PS1:** averages ₹3.65/kWh over the period. It runs from ₹2.1 at midday to ₹10.6 at 22:00 (above the ₹10 day-ahead cap, so some sales are in the high-price day-ahead market).
- **That rate overstates AGEL's income.** It blends all the aggregator's transactions:
  - group-company captive power, which is settled at the integrated day-ahead price by rule;
  - exchange sales at the price actually cleared.
- **AGEL's own figures:** ₹3.22/kWh portfolio-wide in H1 FY27; merchant about ₹2.4.
- **Contract versus market across WRPC** (plants with more than 50 MU):

| | Median sale or settlement rate | Median revenue per MW per month | Median absolute deviation |
|---|---|---|---|
| PPA plants | ₹2.70/kWh | ₹5.2 lakh | 16% of schedule |
| Market or mixed plants | ₹5.23/kWh | ₹12.7 lakh | 24% |

- **Regret on long PPAs:** wind and hybrid tied up at ₹2.6–2.9 left ₹2–3/kWh on the table in 2026. At these night prices, merchant wind captured ₹5–6.
- **Merchant solar:** about ₹2.1–2.9/kWh at the day-ahead price, little better than a PPA.

## 5. Deviation: nearly free for renewable sellers

- **How settlement works:** WRPC settles a renewable seller's deviation at its own settlement rate, not at the Normal Rate (with frequency multipliers) that discoms and thermal plants pay.
  - Adani's aggregators, like about 30 other renewable entities, still match the **2015-era tiers** block by block, apparently under court protection. Up to 15% of available capacity settles at the seller's own rate, then 110% / 90%, and so on.
  - For a 7.6 GW pool, that first band is about 1,100 MW. All of PS1's night output (500–900 MW) sits inside it.
- **The numbers for PS1:**
  - Net deviation charge: **+₹153 crore received**. It over-injected 733 GWh and under-injected 373 GWh, mostly at night and paid at its own night rate.
  - Of that ₹153 crore, ₹155 crore is simply energy priced at its own rate. The **real penalty is ₹2.3 crore over 9.5 TWh, i.e. ₹0.002/kWh**.
- **Across WRPC:** the real penalty for renewable sellers is ₹0.002–0.13/kWh. For comparison, MSEDCL paid about ₹24/kWh on deviation in the evening blocks with the biggest gaps.
- **Who carries the cost of renewable shortfalls:**
  - A PPA wind plant that falls short at 19:00 pays its ₹2.6 tariff for energy the grid replaces at the Normal Rate (₹10+).
  - Summing (Normal Rate − settlement rate) × under-injection, less the same for over-injection, gives about **₹263 crore in 196 days** across WRPC renewable sellers.
  - Largest single items: Manikaran's Bhuj wind aggregator, ₹80 crore; Bhuj-2, ₹35 crore. PS1 is near zero because its night rate is close to the Normal Rate.
- **Coming changes:**
  - The FY28–FY31 trajectory moves the measurement base from available capacity to schedule.
  - New projects (bid from 2027, or COD from 2029) will be settled like general sellers.
  - Existing plants keep the cheap regime for now.

## 6. The opportunity: storage behind the bottleneck

- **The setup:** the evacuation ceiling binds only at midday. In the evening PS1 injects 800–1,000 MW under a ceiling of about 4,200 MW, so the line is mostly empty when prices are at the ₹10 cap.
- **The model:** a battery soaks up curtailed midday energy (topped up from the grid in the cheapest blocks), then sells into the day's highest-priced blocks within the spare room. One cycle a day, 88% round trip, ₹300/MWh wear.

| Battery | Margin over 196 days | Per year | ₹ lakh/MW/month |
|---|---|---|---|
| 500 MW × 2 h | ₹159 crore | ₹297 crore | 4.9 |
| 1 GW × 2 h | ₹318 crore | ₹593 crore | 4.9 |
| 1 GW × 4 h | ₹625 crore | ₹1,163 crore | 9.7 |
| 2 GW × 4 h | ₹1,237 crore | ₹2,303 crore | 9.6 |
| 3 GW × 4 h | ₹1,825 crore | ₹3,398 crore | 9.4 |

- **Against recent auctions:** standalone battery tariffs are ₹1.8–2.4 lakh/MW/month for 2 hours and ₹3.2–4.4 for 4 hours. Behind a curtailed park, a battery earns roughly 2–3× its contracted tariff.
- **What has changed:** a Ministry of Power letter (27 Aug 2026) lets curtailed renewable power charge a co-located battery and be sold to anyone without amending the PPA.
- **AGEL is already doing this** (6.6 GWh by Sep 2026).
  - It sells 3.5 GWh of battery output to its own group company PTSL at a fixed ₹4.8/kWh for 15 years, while evening exchange prices sit at ₹9–10.
  - The difference goes to Adani Energy Solutions, not to AGEL's minority shareholders.
- **Caveats:**
  - Evening prices hold only while the day-ahead market stays rationed at the cap. About 21.7 GW of unmet bids is the median, so a few GW more does not move it.
  - Curtailment ends when Phase III arrives in 2027. After that the battery charges from the grid at ₹1.5–2 instead of for free, and the margin falls by about ₹0.3/kWh.
  - The potential-output fit is linear and uses peers 20–40 km away.

## 7. Seen from both sides

| | Discom (MSEDCL) | Producer (Khavda) |
|---|---|---|
| Scarce at | the evening (17:00–23:00) | the midday wire |
| Deviation cost | Normal Rate × frequency multipliers; about ₹24/kWh in big-gap evening blocks | own rate; real penalty about ₹0.002/kWh |
| Day-ahead price | rationed at ₹10 in the evening, filling 1.4% of its bids | sells at ₹1.4–2 at midday, curtailed 21% |
| What would fix it | evening capacity: batteries at about ₹6.5/kWh delivered | storage behind the meter; the 2027 transmission corridor |

A battery at Khavda that charges from spilled midday solar and sells into the rationed evening market solves both columns at once. That is the single largest structural opportunity in either study.

## Gaps

- **Buyers by block:** who received each block (exchange buyers, SECI's end discoms). WRLDC's schedule portal is unreachable from here.
- **Khavda-only accounts:** AGEL reports generation, revenue and curtailment for the whole portfolio only.
- **Infirm versus PPA by project company**, and the date each PPA starts.
- **WRPC's settlement rate** is a proxy for sale price, not booked revenue.
- **Settlement regime:** which regime applies to each renewable entity, and why, is inferred from fits.
