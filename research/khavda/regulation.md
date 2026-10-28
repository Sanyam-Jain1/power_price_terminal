# Rules that set a wind or solar seller's money, as of 28 Oct 2026

Collected by a research agent on 28 Oct 2026. Each fact carries a flag:
- **[P]** primary document that was read, mostly cercind.gov.in PDFs;
- **[S]** secondary source (news or law-firm summary);
- **[D]** result worked out from WRPC block data (week 12–18 Oct 2026; scripts in `scripts/agent/`).

## 1. Deviation settlement (CERC DSM Regulations 2024)

### Instruments
- **Principal Regulations:** No. L-1/260/2021/CERC, 05.08.2024, in force 16.09.2024. [P] https://www.cercind.gov.in/regulations/192-Noti.pdf
- **First Amendment:** in force 23.12.2024. [P] https://cercind.gov.in/regulations/194.pdf
  - Available Capacity (AvC) is limited to the connectivity granted.
  - Adds a contract-rate limb for open-access sales.
- **Second Amendment:** in force 01.07.2025; thermal infirm power only. [P] https://cercind.gov.in/regulations/199.pdf
- **Third Amendment:** notified 25.08.2026, in force 31.08.2026. [P] https://cercind.gov.in/regulations/208-notification.pdf (statement of reasons: https://cercind.gov.in/regulations/208-third-amendment-for.pdf)
- **Order on the "X" trajectory:** Petition 9/SM/2025, 31.03.2026. [P] https://cercind.gov.in/2026/orders/9-SM-2025.pdf

### Definitions [P]
- **WS seller:** a wind, solar or hybrid station, with or without storage.
- **AvC:** turbines or inverters able to generate in the block, capped at connectivity.
- **Contract rate (Reg 3(1)(j)):**
  - with a tariff under Section 62, 63 or 86(1)(b): that tariff;
  - selling on a power exchange: "the price as discovered in the Power Exchange for the respective transaction";
  - open access or captive use: the block-wise weighted-average integrated day-ahead (I-DAM) price, where I-DAM = DAM + green DAM + high-price DAM;
  - several contracts: the weighted average of all of them.
- **Block-wise, not daily:** the Third Amendment kept the block-wise rate and rejected a proposed daily average.
- **Normal Rate (the highest of I-DAM, RTM, or ⅓ each of I-DAM, RTM and the ancillary service charge):** applies to buyers and general sellers, **not** to WS sellers.

### Measuring deviation (Reg 6(2)) [P]
- From 01.04.2026, deviation % = 100 × deviation ÷ [X% × AvC + (100−X)% × schedule].
- X is 100% in FY27, so the denominator is still AvC.
- The X trajectory below applies to single plants and to plants pooled by an aggregator (QCA).

| Period | Solar / hybrid | Wind |
|---|---|---|
| FY27 | 100% | 100% |
| FY28 | 90% | 95% |
| FY29 | 75% | 85% |
| FY30 | 55% | 65% |
| FY31 | 30% | 35% |
| From 01.04.2031 | 0% | 0% |

- Enforcement is subject to the writ petitions in the Delhi High Court: no coercive action while interim orders stand (para 86).

### Charges (Reg 8(4)) [P]
These charges are not linked to frequency.

| Band | Over-injection (seller receives) | Under-injection (seller pays) |
|---|---|---|
| Within band 1 | contract rate | contract rate |
| Within band 2 | 90% of contract rate | 110% of contract rate |
| Beyond band 2 | zero | 200% of contract rate |

| Seller | Band 1 / band 2, to 31.03.2026 | Band 1 / band 2, from 01.04.2026 |
|---|---|---|
| Solar or hybrid | ≤10% / 10–15% | ≤5% / 5–10% |
| Wind | ≤15% / 15–20% | ≤10% / 10–15% |

### Other provisions [P]
- **Storage at the same connection point (Reg 8(6)):** WS rules apply while wind or solar injects; standalone-storage rules apply otherwise. Each needs its own meter.
- **HP-DAM shortfall (Reg 8(13)):** a shortfall on power sold in the high-price day-ahead market is charged at that market's weighted average price.
- **New Reg 8(4A), effective 31.08.2026:** WS sellers are treated like general sellers if either
  - the project was bid on or after 01.01.2027, or
  - any other project has COD on or after 01.01.2029.
- **Proposals not adopted:** moving existing WS sellers to general-seller treatment from 2031, and zero pay for over-injection at ≥50.05 Hz. Neither is in the Third Amendment.
- **Courts:**
  - Delhi High Court interim order, 20.11.2024: no coercive action. [P, quoted in the X order]
  - Karnataka High Court, 27.04.2026: stayed Regs 6(2)(b) and 8(4) for its petitioners. [S] https://www.pv-magazine-india.com/2026/06/02/scheduling-discipline-at-a-judicial-crossroads-indias-evolving-deviation-settlement-mechanism/

### Aggregators (QCAs) [P] https://cercind.gov.in/Regulations/180-Regulations.pdf
- **Who may appoint one (IEGC 2023 Reg 45(11)):** stations at one ISTS substation, or at several ISTS substations in one state.
- **What it does:** the QCA schedules for its members and settles DSM.
- **If the QCA defaults:** members pay pro-rata to MW.
- **Pooled settlement:** the contract rate is the weighted average of members' rates, and AvC is the pool's total.
- **Effect:** a Grid-India simulation cited in the X order puts the penalty cut from pooling at about 30–65%.
- **Schedule revisions:** a WS seller in collective (exchange) trades cannot revise its schedule for forecast error (Reg 49(8)), so all of that error lands in DSM.

### What the WRPC columns mean [D]
| Column | Meaning |
|---|---|
| `Deviation (%)` | \|deviation\| ÷ `WS Seller Capacity` × 100. Matches every block, consistent with X = 100%. |
| `WS Seller Capacity (Mwh)` | AvC per block in MWh (MW × 0.25). |
| `Wt. Avg. Rate (p/Kwh)` | The contract rate WRPC applied to the seller in that block (weighted average across its sales). Payable and receivable reconcile to deviation × this rate × the band multiplier. |
| `RE Gen PPA Rate (p/Mwh)` | Declared PPA tariff. In practice it is ₹/MWh: 2620 means ₹2.62/kWh. |
| `Wt.Avg. ACP DAM Rate (p/Kwh)` | All-exchange I-DAM price. Used when the contract rate is zero, e.g. solar's night-time auxiliary drawal. |
| HP-DAM columns | Appear to be placeholders for Reg 8(13). |

### Which regime WRPC actually applies [D]
- **Older tiers:** about 30 WS entities, including Adani's Khavda QCAs, match the **2015-era tiers** in every block tested:
  - up to 15% of AvC at the contract rate;
  - 15–25% at 110% / 90%;
  - 25–35% at 120% / 80%;
  - beyond 35% at 130% / 70%.

  This is consistent with court protection keeping petitioners on the pre-2024 regime.
- **DSM-2024 FY27 bands:** only about 7 entities are on them (GSECL, GIPCL, CIL, SGEL, MRPL hybrid; AVGJC on the wind bands).
- **Unexplained:** Ayana HW, NVWEPL, Powerica, SVVPL and Torrent fit no tested model.
- **Caveat:** check the regime per entity against WRPC's notes before relying on it.

## 2. Curtailment

- **Grid security and transmission constraints (IEGC 2023 Reg 49(3)(a)):** temporary access (T-GNA) is cut before general access (GNA). [P]
  - Within T-GNA the order is bilateral, then day-ahead collective, then real-time collective.
  - Within each tier, non-RE is cut before wind, solar and hybrid, pro-rata.
  - A published incident report with reasons is due within 24 hours.
- **Evacuation bottleneck (Reg 49(3)(b)):** schedules are revised from the 7th or 8th block. [P]
- **Must-Run Rules 2021:** [S] https://www.legitquest.com/act/electricity-promotion-of-generation-of-electricity-from-must-run-power-plant-rules-2021/A676
  - Wind and solar may not be curtailed for commercial reasons.
  - Curtailed energy is compensated at the PPA rate, net of any exchange sales.
  - "Grid security" is undefined, and that is the main point of litigation.
- **Compensation clauses in PPAs:**
  - SECI and SJVN PPAs carry "Generation Compensation for off-take Constraints". [P] https://cercind.gov.in/2025/orders/404-AT-2024.pdf
  - FDRE and assured-peak PPAs require the seller to offer the power on the exchange first. [P] https://cercind.gov.in/2026/orders/31-AT-2026.pdf
  - Older templates compensate grid unavailability beyond 50 hours a year, or 175 in some templates. [S]
- **Pending compensation cases:** T-GNA curtailment petitions (846/MP/2025, 26/MP/2026, 35/MP/2026, 249/MP/2026) have no final award yet. [P] https://cercind.gov.in/2026/ROP/846-MP-2025_300726.pdf
- **Ministry of Power letter, 27.08.2026:** renewable power curtailed under T-GNA may charge a co-located battery and be sold to anyone, with no PPA change or procurer consent needed. [S] https://renewablewatch.in/2026/08/31/mop-allows-sale-of-curtailed-renewable-power-through-co-located-bess/
- **Scale of the problem:** about 4 GW of commissioned Rajasthan renewables face T-GNA curtailment in solar hours (CEA, 15.12.2025). [S]

## 3. Merchant sales, RECs and obligations

- **Who gets RECs (REC Regulations 2022, Reg 4(2)):** only plants with no Section 62/63 tariff, no sale for RPO, and no transmission-charge waiver. [P] https://cercind.gov.in/regulations/REC-Regulations-2022.pdf
  - Green-market sales, PPA power and ISTS-waiver plants earn no RECs.
- **REC First Amendment 2026:** adds the consumption obligation (RCO) and virtual PPAs; RECs under a virtual PPA cannot be resold. [P] https://cercind.gov.in/regulations/207-Noti.pdf
- **REC prices on IEX, 2026:** ₹395 (24 Jun), then ₹380, 376, 370, 350, 345, 343, and ₹338 (14 Oct). Source: `data/rec_sessions.csv`.
- **Renewable consumption obligation:** rises from 29.91% (FY25) to 43.33% (FY30). [S]
- **Price capture, 24 Aug–18 Oct 2026 [D], all-India IEX prices:**

| | Day-ahead ₹/MWh | Green day-ahead | Real-time | Day-ahead capture |
|---|---|---|---|---|
| Time-weighted average | 7,269 | 7,305 | 6,698 | |
| Solar | 3,621 | 3,542 | 3,321 | about 50% |
| Wind | 6,524 | 6,695 | 5,832 | about 90% |
| Hybrid | 5,544 | 5,641 | 4,966 | about 76% |

## 4. ISTS charge waiver and connectivity

- **Waiver ladder for wind, solar and hybrid by COD** (Sharing Regulations, Fourth Amendment, Reg 13(2)(a)). [P] https://cercind.gov.in/regulations/200.pdf

| COD | Waiver | Period |
|---|---|---|
| By 30.06.2025 | 100% | 25 years |
| 1.7.2025 – 30.6.2026 | 75% | 25 years |
| 1.7.2026 – 30.6.2027 | 50% | 25 years |
| 1.7.2027 – 30.6.2028 | 25% | 25 years |
| After that | 0% | |

- **Batteries:** 100% for 12 years if co-located and charged from renewables, with COD by 30.06.2028.
- **Projects delayed by missing transmission:** may keep 100% under Reg 13(2)(h), through the extension committee. [P] https://cercind.gov.in/regulations/300725.pdf, https://cercind.gov.in/regulations/Addendum-14012026.pdf
- **Who benefits:** the waiver reduces the *buyer's* ISTS charge, so for a merchant seller it shows up in the price buyers will pay.
- **Shared connectivity (GNA Third Amendment, 31.08.2025):** adds solar-hour and non-solar-hour access, so two plants can share one connection by time of day. [P] https://cercind.gov.in/regulations/201.pdf

## 5. Standard SECI and SJVN PPA terms

- **Tariff:** single, fixed for 25 years, at the delivery point. [P]
- **Generator bears:** transmission charges, losses and DSM up to the delivery point.
- **Payment security:** LPS Rules 2022 plus a payment security fund (2 paise/kWh). [P]
- **Trading margin:** SECI/SJVN charge discoms ₹0.07/kWh, capped at ₹0.02 if the generator gets no escrow or revolving LC. [P] 404/AT/2024
- **Shortfall:** below minimum CUF, the generator pays 1.5 × tariff on units not supplied. [P for FDRE, S for solar]
- **Default damages:** 24 months. [P]
- **Late Payment Surcharge Rules 2022:** [S]
  - the surcharge starts at the base rate (SBI one-year MCLR + 5%), rises 0.5 point a month, and is capped at base + 3;
  - payments go first to the surcharge, then to the oldest bill.

## 6. Discovered tariffs, 2025–26

| Product | Result |
|---|---|
| Plain solar | SJVN, Aug 2024: ₹2.52 [P]; SECI Tranche XVI: ₹2.48 [S] |
| Wind | SJVN, Mar 2026: ₹3.64–3.65; SECI, Jul 2026: ₹3.78–3.85 [S] |
| Hybrid | SJVN: ₹3.19; NHPC: ₹3.41; NTPC: ₹3.38–3.44 [S] |
| Solar + battery | SECI 2 GW + 4 GWh, Oct 2025: ₹2.86–2.87; SECI, Jan 2026: ₹3.12–3.13 [S] |
| Firm and dispatchable (FDRE) | NHPC, Jul 2025: ₹3.13 [S]; SECI FDRE-VI: ₹8.50 [P] |
| Assured peak | SJVN 1.5 GW × 4 h: ₹6.74 [P]; SECI 1.5 GW / 6 GWh, Aug 2026: ₹5.99–6.00 [S] |
| Standalone battery (₹ lakh/MW/month) | 2-hour: 1.48 (2025 low), 1.78–2.35 (2025–26 range); 4-hour: 3.15 (TNGECL), 4.35–4.39 (WBSEDCL, Aug 2026) [S] https://ieefa.org/sites/default/files/2026-09/ESSjmk-0926.pdf |

## Gaps

- **Which regime applies to whom:** no WRPC note explains which entities are settled under the old tiers.
- **Aggregation procedure:** the final NLDC procedure was not found; grid-india.in is unreachable.
- **Primary texts not read:** the LPS Rules and Must-Run Rules gazette texts, and the full current SECI generation-compensation clause.
- **Curtailment compensation:** no 2026 award has been found.
- **Market changes:** the status of market coupling is unverified.
