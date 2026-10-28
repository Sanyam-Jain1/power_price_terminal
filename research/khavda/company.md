# Adani Green Energy (AGEL) and Khavda: public facts, as of 28 Oct 2026

Collected by a research agent on 28 Oct 2026, using public sources only.

**Flags:**
- **P**: primary source (company filing or deck, call transcript, annual report, regulator, RPC or CTU document, rating rationale).
- **C**: company press release.
- **S**: news or other secondary source.
- **D**: derived from P data.

**Main documents:**
- Investor decks: [Q2 FY27](https://www.adanigreenenergy.com/-/media/project/greenenergy/investor-downloads/result-presentation-dynamic/agel----earnings-presentation---q2fy27_vf.pdf), [Q1 FY27](https://www.adanigreenenergy.com/-/media/project/greenenergy/investor-downloads/result-presentation-dynamic/agel----earnings-presentation---q1fy27_vf.pdf), [Q4 FY26](https://www.adanigreenenergy.com/-/media/project/greenenergy/investor-downloads/result-presentation-dynamic/q4-fy26.pdf).
- Call transcripts: [Q2 FY27, 22 Oct 2026](https://www.adanigreenenergy.com/-/media/project/greenenergy/investor-downloads/results-conference-call-transcript/agelq2fy27earnings-call-transcriptoct-22-2026v1.pdf), [Q1 FY27](https://www.adanigreenenergy.com/-/media/project/greenenergy/investor-downloads/results-conference-call-transcript/agel_q1fy27_transcript_v1.pdf), [Q4 FY26](https://www.adanigreenenergy.com/-/media/project/greenenergy/investor-downloads/results-conference-call-transcript/adani-green_q4fy26_equity-call_transcript_apr-24-2026_vf.pdf).
- [FY26 annual report](https://www.adanigreenenergy.com/-/media/project/greenenergy/investor-downloads/annual-reports/fy26.pdf).
- [CARE rating rationale, 3 Sep 2026](https://www.careratings.com/upload/CompanyFiles/PR/202609120946_Adani_Green_Energy_Limited.pdf).
- WRPC monthly transmission deviation statements (RTA/RTDA). They are listed through a public JSON endpoint, `https://www.wrpc.gov.in/api/TopMenu/custom/354` (RTA) and `/356` (RTDA). Links to each month are at the end.

## 1. Capacity

| Date | Khavda MW (AGEL's own + group companies) | AGEL total MW | Khavda battery MWh | Source |
|---|---|---|---|---|
| 31 Dec 2025 | 7,722 (7,005 + 717) | 17,200 | – | C |
| 31 Mar 2026 | 9,413 (8,671 + 742) | 19,294 | 1,376 | Q4 FY26 deck p15 (P) |
| 26 May 2026 | about 9,900 | 19,786 | 3,366 | C |
| 30 Jun 2026 | 10,262 (9,520 + 742) | 20,142 | 3,551 | Q1 FY27 deck (P) |
| 30 Sep 2026 | **10,752 (10,002 + 750)** | **20,763** | **6,632** | Q2 FY27 deck p15 (P) |

- **Additions in FY26 at Khavda (AGEL's own):** 2,974 MW solar, 683 MW wind, 956 MW hybrid (C).
- **The site:** 538 km², with a target of 30 GW by 2029 (P).
- **Group-company capacity (750 MW):** built by AGEL for Ambuja Cements and Adani Ports. It sits inside the PS1 aggregator but outside AGEL's EBITDA (P).
- **Battery:**
  - Power rating about 1.1–1.2 GW by May 2026 (S). Systems are 2–3 hours (P).
  - Capex about ₹1.5 crore/MWh; EBITDA ₹25–30 lakh per MWh a year (P).
  - 3.5 GWh is contracted to PTSL for 15 years at about **₹4.8/kWh** (CARE, P).
  - Management cites ₹4–5/kWh of arbitrage, charging at about ₹2.5 (P).
- **Pumped hydro:** none linked to Khavda. The first project is Chitravathi, 500 MW in Andhra Pradesh (P).

### Who buys the Khavda capacity
Built from the Q2 FY27 asset annex, pp. 38–46 (P / D). The total comes to about 10,010 MW.

| Buyer and tariff | MW (approx.) | Main project companies |
|---|---|---|
| SECI ₹2.42 solar (manufacturing-linked tender, Packages II–IV, resold to Andhra Pradesh) | ~4,447 | AGE24AL, AGE24BL, AGE25AL, AGE25BL, AGE26BL, ARE56L, ARE57L, AGE25CL |
| SECI ₹2.54 solar (Package I) | ~800 | AGE26AL |
| SECI ₹2.41 hybrid | ~600 | AHEJ5L |
| Torrent ₹2.22 solar | 150 | ARE8L (Jun 2026) |
| PTSL solar ₹2.67–2.70 | ~1,678, plus ~400 in process | ARE56L, AGE24AL, AGE24L, AHEJ5L, ARE45L, AGE26BL, ASEJ6L |
| PTSL wind ₹3.80 | ~1,048, plus ~360 in process | ARE41L, AGE24L, AHEJ5L, AGE25CL, AGE26AL, AGE41L |
| PTSL hybrid ₹2.61–3.90 | ~500, plus 25 in process | ARE41L, AGE25BL, AGE26BL, ASEJ6PL, ARE3L |

- **PTSL** is Powerpulse Trading Solutions, a wholly owned subsidiary of Adani Energy Solutions (AESL), so it is a **related party**.
  - Its contracts are 25-year fixed (15 years for batteries), on SECI terms, with no termination for convenience.
  - AESL resells the power to commercial and industrial customers and carries the ISTS-waiver risk of about ₹0.50/kWh (P).
- **ARE3L:** 50 MW hybrid at ₹3.90 under a third-party PPA, matching the 61.4 MW supply to Google announced in 2024 (S).
- **SECI's resale:**
  - The ₹2.42 power goes to the Andhra Pradesh discoms at ₹2.49 (₹0.07 margin). The schedule is 3,000 MW from Oct 2024, 3,000 MW from Oct 2025 and 1,000 MW from Oct 2026.
  - APERC's approval is subject to High Court public-interest petitions (S).
  - The ₹2.54 power goes to Odisha 500, Chhattisgarh 300, Tamil Nadu 1,000, J&K 100, BEST 234 and Tripura 100 MW.
  - CERC orders: 286/AT/2021, 224/AT/2023 and [202/MP/2024](https://cercind.gov.in/2025/orders/202-MP-2024.pdf) (P).
- **MSEDCL contract:** 5,000 MW of Khavda solar at a flat ₹2.70 for 25 years (letter of intent, Sep 2024). None of it is operating yet.
  - The "1,600 MW" in the same deal is Adani Power thermal capacity (C/S).
- **Contract status at the start of FY27 (P):** of 19.3 GW, 9.7 GW was under PPAs, 5.3 GW was "infirm" (PPA signed, sold on the market until the PPA starts) and 4.2 GW was merchant.
  - CARE says the portfolio was 100% contracted by 30 Jun 2026 (P).

| Generation (MU) | 25-year PPAs | PTSL / private | Infirm / merchant |
|---|---|---|---|
| FY26 | 21,585 | 6,988 (sold as merchant) | 8,995 |
| H1 FY27 | 14,478 | 6,983 | 4,286 (16.6%) |
| Q2 FY27 (D) | 6,872 | 3,323 | 1,895 |

- **Related-party sales (FY26):** ₹4,626 crore to PTSL and ₹946 crore to Adani Electricity Mumbai, out of ₹11,602 crore of power revenue (P).

## 2. Grid access: the binding limit

| Item | MW | Effective | Source |
|---|---|---|---|
| CTU GNA, AREH4L at Khavda pooling station 1 (KPS-1) | 1,000 | 25 Feb 2024 | Aug-26 RTA (P) |
| CTU GNA, AGEL at KPS-1 | 1,000 + 1,000 + 1,050 | 08 Mar 2026 | same |
| CTU GNA, AGEL at KPS-3 | 1,050 | 08 Mar 2026 | same |
| WRLDC GNA, PS1 aggregator | 3,367 (Apr–Jun 2026); **3,525** (from Jul 2026) | – | RTDA (P) |
| WRLDC GNA, PS3 aggregator | 950 (Apr–Jun 2026); **1,000** (from Jul 2026) | – | RTDA (P) |

WRPC charges at the transmission rate for injection above GNA (P):

| Billing month | PS1, MWh (₹) | PS3, MWh (₹) |
|---|---|---|
| Apr-26 | 67,300 (₹2.67 crore) | 9,633 (₹38 lakh) |
| May-26 | 12,645 (₹55 lakh) | 3,249 (₹14 lakh) |
| Jun-26 | 17,273 (₹72 lakh) | 18,548 (₹78 lakh) |
| Jul-26 | 9,291 (₹38 lakh) | 1,757 (₹7 lakh) |
| Aug-26 | 1,258 (₹5 lakh) | 1,288 (₹6 lakh) |

- **Transmission:**
  - About 9 GW of Khavda transmission was active in Apr 2026 (P).
  - PGCIL: Phase II Part C (4.5 GW) commissioned 31 Jan 2026; Phase IV Part E4 (7 GW) commissioned 21 Jun 2026 (S).
  - **Phase III Part A (7 GW, AESL, Halvad):** slipped to **Jan–Mar 2027** over right-of-way problems. Management says it "gives us the full GNA capacity" (Q2 FY27 call, P).
  - Phase V Part C (±500 kV HVDC to South Olpad): scheduled COD Dec 2029 (S).
- **13 May 2026 outage:** a grid disturbance tripped the whole Khavda complex and **8,963 MW** was lost.
  - Short-circuit ratios: Khavda-I 2.58, Khavda-II 4.41, Khavda-III 4.65, all below the CEA minimum of 5 (S).
  - Sources: [PowerPeak](https://powerpeakdigest.com/khavda-blackout-probe-8963-mw-power-loss/), [Renewable Watch](https://renewablewatch.in/2026/08/18/lessons-from-khavda-recent-outage-underscores-the-need-for-grid-forming-inverters/).

## 3. Results

| | Q4 FY26 | FY26 | Q1 FY27 | Q2 FY27 | H1 FY27 |
|---|---|---|---|---|---|
| Power revenue (₹ crore) | 3,094 | 11,602 | 4,280 | 4,019 | 8,299 |
| Power EBITDA (₹ crore) | 2,944 | 10,865 | 4,122 | 3,835 | 7,957 (total 8,276) |
| Energy sold (MU) | ~9,931 | 37,567 | 13,657 | 12,090 | 25,747 |
| Revenue per kWh (D) | – | ₹3.09 | ₹3.13 | ₹3.32 | ₹3.22 |
| Solar CUF | – | 24.0% | 25.3% | ~20.5% (D) | 22.9% |
| Wind CUF | – | 26.6% | 44.4% | – | 42.9% |
| **Solar grid availability** | – | **86.9%** | **80.6%** | – | **78.9%** |

- **Realisation:**
  - Blended PPA tariff about ₹3.10 (P).
  - Merchant (infirm) price about **₹2.4/kWh in Q2 FY27**, against about ₹2.1 a year earlier (P).
  - CARE: merchant solar realised ₹2.3 and merchant wind ₹4.4 in FY26 (P).
- **Curtailment:**
  - FY26: about ₹500 crore of EBITDA, plus ₹800–1,000 crore from low merchant prices (P).
  - Q1 FY27: 5–7% of EBITDA (P).
  - **H1 FY27: about ₹724 crore**. Management said EBITDA "would have been close to ₹9,000 crore" (P / D).
  - Khavda solar CUF is above 27% before curtailment, which takes off 2.5–3 percentage points (P).
- **Compensation:** paid only for power that was *scheduled* and then backed down. Output that could not be scheduled because of evacuation limits is not paid (Q2 call, P).
- **Other income:** RECs and carbon credits ₹193 crore in FY26; late-payment interest ₹36 crore (P).
- **Debt at 30 Sep 2026:** net ₹1,02,973 crore; 5.6× run-rate EBITDA; average cost 8.9% (P).
- **Capex:** ₹30,365 crore in FY26; FY27 guidance ₹40,000–42,000 crore (P).
- **Ratings:** CARE AA/Stable, reaffirmed 3 Sep 2026 (P).
- **US cases:** the criminal case was **dismissed with prejudice on 10 Aug 2026**, and the SEC case was settled for US$18 million (S; confirmed by CARE, P).
- **Overdue receivables:** ₹113 crore, of which UPPCL owes ₹51 crore (P).

## Gaps

- **Khavda-only data:** generation, CUF, curtailment and realisation are reported only for the whole portfolio.
- **Capacity series:** no month-by-month series. BSE filings refused automated requests.
- **Infirm status:** which capacity is still infirm, and when each PPA starts.
- **Khavda curtailment orders:** no CERC or Grid-India order on Khavda curtailment was found.

## WRPC RTA/RTDA files (one per billing month)

| Billing month | File |
|---|---|
| Dec-25 | https://www.wrpc.gov.in/allfile/020220261256190551rta_rtda_feb26.pdf |
| Jan-26 | https://www.wrpc.gov.in/allfile/020320261208445961rta_rtda_March%2026.pdf |
| Feb-26 | https://www.wrpc.gov.in/allfile/310320262051472168rta_rtda_April%2026.pdf |
| Mar-26 | https://www.wrpc.gov.in/allfile/300420261803417332rta_rtda_May%2026%20final.pdf |
| Apr-26 | https://www.wrpc.gov.in/allfile/300520261821394414rta_rtda_June%2026%20final..pdf |
| May-26 | https://www.wrpc.gov.in/allfile/240720261704249807rta_rtda_July%2026%20final.pdf |
| Jun-26 | https://www.wrpc.gov.in/allfile/300720261026410639rta-rtda%20-august%202026.pdf |
| Jul-26 | https://www.wrpc.gov.in/allfile/310820261848225896RTA_RTDA%20for%20Sept%2026%20final.pdf |
| Aug-26 | https://www.wrpc.gov.in/allfile/290920261729169290RTA-RTDA%20OCT-26.pdf |
