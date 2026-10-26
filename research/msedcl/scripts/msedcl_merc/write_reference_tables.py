"""Write small reference CSVs transcribed from text-layer PDFs (values copied exactly as printed)."""
import csv, os, sys
d = sys.argv[1]
def w(name, header, rows):
    with open(os.path.join(d, name), "w", newline="") as fh:
        c = csv.writer(fh); c.writerow(header); c.writerows(rows)

O217 = "MERC MYT Order Case 217 of 2024 (28.03.2025)"; O26 = "MERC Order Case 75 of 2025 post-remand (25.03.2026)"
# MYT summary for 5th control period
w("merc_myt_control_period_summary.csv",
  ["metric", "unit", "FY2025-26", "FY2026-27", "FY2027-28", "FY2028-29", "FY2029-30", "source"],
  [["Total power purchase quantum - approved (MYT order)", "MU", 172700, 180111, 190659, 195504, 203301, O217 + " Table 249/250; " + O26 + " Table 9"],
   ["Total power purchase quantum - approved after review", "MU", 183934, 203628, 218144, 221982, 231379, O26 + " Table 4"],
   ["Total power purchase cost - approved after review", "Rs crore", 89894, 98025, 105091, 110309, 116705, O26 + " Table 4"],
   ["Average power purchase cost - approved after review", "Rs/kWh", 4.89, 4.81, 4.82, 4.97, 5.04, O26 + " Table 4"],
   ["Additional PP quantum vs MYT order (review)", "MU", 11234, 23517, 27485, 26216, 28078, O26 + " Table 3"],
   ["Additional PP cost vs MYT order (review)", "Rs crore", 4712, 9399, 10835, 9804, 9997, O26 + " Table 3"],
   ["Total energy availability & cost - MYT order (FY26-27 Table 259 total)", "Rs crore", "", 88626, "", "", "", O217 + " Table 259"],
   ["Fixed cost of power purchase (grid support charge basis)", "Rs crore", 21322, 21895, 22512, 26412, 31967, O26 + " Table 9"],
   ["Variable cost of power purchase (grid support charge basis)", "Rs crore", 68572, 76129, 82580, 83898, 84737, O26 + " Table 9"],
   ["Marginal variable cost", "Rs/kWh", 3.97, 4.23, 4.33, 4.29, 4.17, O26 + " Table 9"],
   ["Energy sales by MSEDCL incl DF (approved, MYT order)", "MU", 140358, 147085, 154218, 161873, 169973, O217 + " Table 248"],
   ["OA sales conventional (approved)", "MU", 4794, 5647, 6434, 7058, 7947, O217 + " Table 248"],
   ["OA sales non-conventional (approved)", "MU", 3907, 3676, 3556, 3430, 3522, O217 + " Table 248"],
   ["Total energy sales (approved, MYT order)", "MU", 149059, 156408, 164208, 172361, 181442, O217 + " Table 248"],
   ["Distribution loss (approved, excl EHV & OA)", "%", 17.0, 15.5, 14.0, "", "", O217 + " Table 249"],
   ["Surplus traded quantum (Commission projection)", "MU", 0, 2154, 7182, 5951, 7175, O217 + " Table 257"],
   ["Contracted capacity (Commission analysis)", "MW", 49302, 61454, 66376, 69830, 75276, O217 + " Table 234/240"],
   ["Firm capacity adj. for CC factor (Commission)", "MW", 32087, 36594, 36797, 39507, 47170, O217 + " Table 234"],
   ["RA requirement (Commission)", "MW", 26275, 27074, 27914, 28848, 29839, O217 + " Table 234"],
   ["RA surplus vs RA requirement (Commission)", "MW", 5812, 9520, 8883, 10659, 17331, O217 + " Table 234"],
   ["Forecasted peak demand (MSEDCL)", "MW", 25412, 27943, 30743, 31767, 32994, O217 + " Table 235"],
   ["Contracted capacity (MSEDCL submission)", "MW", 51882, 68257, 73961, 79910, 85345, O217 + " Table 234"],
   ["RA surplus vs RA requirement (MSEDCL submission)", "MW", 7735, 12521, 10907, 14880, 20769, O217 + " Table 234"]])

# cumulative contracted capacity by resource (Commission analysis, Table 240)
res = {"Thermal": [22551, 22551, 22551, 24151, 25123], "Nuclear": [1191]*5, "Large Hydro": [2825, 2934, 3247, 3351, 3351],
       "PSP-Storage": [250, 1000, 1000, 2750, 4824], "Wind": [3604]*5, "Solar": [15353, 24053, 25053, 25053, 27453],
       "Hybrid": [300, 1080, 4344, 4344, 4344], "FDRE": [0, 1468, 1468, 1468, 1468], "Bagasse+Biomass": [2911, 3256, 3601, 3601, 3601],
       "Small Hydro": [317]*5, "Total": [49302, 61454, 66376, 69830, 75276]}
w("merc_myt_contracted_capacity_by_resource.csv", ["resource", "FY2025-26", "FY2026-27", "FY2027-28", "FY2028-29", "FY2029-30", "unit", "source"],
  [[k] + v + ["MW", O217 + " Table 240 (Commission's analysis)"] for k, v in res.items()])

# RE contracted (MSEDCL website lists, as on 30.04.2025)
w("msedcl_re_contracts_apr2025.csv", ["category", "item", "contracted_mw", "commissioned_mw", "tariff_rs_per_kwh", "ppa_date", "location", "doc"],
  [["RE summary", "Wind", 3248, 2620, "", "", "", "Consolidated-Renewable-Energy-contracted-by-MSEDCL.pdf"],
   ["RE summary", "Bagasse co-generation", 2833, 2733, "", "", "", "Consolidated-Renewable-Energy-contracted-by-MSEDCL.pdf"],
   ["RE summary", "Biomass", 37, 37, "", "", "", "Consolidated-Renewable-Energy-contracted-by-MSEDCL.pdf"],
   ["RE summary", "Small Hydro", 307, 304.13, "", "", "", "Consolidated-Renewable-Energy-contracted-by-MSEDCL.pdf"],
   ["RE summary", "Solar (Centralised)", 14356, 3861, "", "", "", "Consolidated-Renewable-Energy-contracted-by-MSEDCL.pdf"],
   ["RE summary", "Solar (MSKVY)", 1531, 614, "", "", "", "Consolidated-Renewable-Energy-contracted-by-MSEDCL.pdf"],
   ["RE summary", "Solar (Kusum A)", 204, 4, "", "", "", "Consolidated-Renewable-Energy-contracted-by-MSEDCL.pdf"],
   ["RE summary", "Solar (Kusum C)", 108, 96, "", "", "", "Consolidated-Renewable-Energy-contracted-by-MSEDCL.pdf"],
   ["RE summary", "Solar (MSKVY 2.0)", 11668, 640, "", "", "", "Consolidated-Renewable-Energy-contracted-by-MSEDCL.pdf"],
   ["RE summary", "Solar (LIS)", 805, 0, "", "", "", "Consolidated-Renewable-Energy-contracted-by-MSEDCL.pdf"],
   ["RE summary", "Total Solar", 28672, 5215, "", "", "", "Consolidated-Renewable-Energy-contracted-by-MSEDCL.pdf"],
   ["RE summary", "Wind-Solar Hybrid", 4344, 300, "", "", "", "Consolidated-Renewable-Energy-contracted-by-MSEDCL.pdf"],
   ["RE summary", "RTC/Storage", 2218, 0, "", "", "", "Consolidated-Renewable-Energy-contracted-by-MSEDCL.pdf"],
   ["RE summary", "Municipal Solid Waste", 17, 4, "", "", "", "Consolidated-Renewable-Energy-contracted-by-MSEDCL.pdf"],
   ["RE summary", "TOTAL", 41676, 11213, "", "", "", "Consolidated-Renewable-Energy-contracted-by-MSEDCL.pdf"],
   ["RTC/Storage", "SJVN Ltd. (FDRE)", 1468, "", "4.45/4.46", "13.03.2024", "Inter-state", "h.-RTC-Storage.pdf"],
   ["RTC/Storage", "Pace Renewable Energies Pvt Ltd (storage)", 750, "", "Rs 2,19,001 per MW per month", "21.02.2025", "Intra-state", "h.-RTC-Storage.pdf"],
   ["Wind-Solar Hybrid", "T.P. Saurya Ltd (Solar 200 + Wind 100)", 300, 300, 2.56, "22.07.2022", "Maharashtra", "g.-Wind-Solar-Hybrid.pdf"],
   ["Wind-Solar Hybrid", "NTPC", 780, 0, "3.42-3.43", "30.06.2024", "Interstate", "g.-Wind-Solar-Hybrid.pdf"],
   ["Wind-Solar Hybrid", "JSW Renew Energy Six Ltd", 600, 0, 3.60, "16.10.2024", "Intrastate", "g.-Wind-Solar-Hybrid.pdf"],
   ["Wind-Solar Hybrid", "BN Peak Power-1 Pvt Ltd", 89, 0, 3.60, "25.10.2024", "Intrastate", "g.-Wind-Solar-Hybrid.pdf"],
   ["Wind-Solar Hybrid", "JSW Renew Energy Thirty Ltd", 600, 0, 3.60, "16.10.2024", "Intrastate", "g.-Wind-Solar-Hybrid.pdf"],
   ["Wind-Solar Hybrid", "Tata Power Renewable Energy Ltd", 400, 0, 3.60, "18.11.2024", "Intrastate", "g.-Wind-Solar-Hybrid.pdf"],
   ["Wind-Solar Hybrid", "Juniper Green Park Spark Pvt Ltd", 75, 0, 3.60, "18.11.2024", "Intrastate", "g.-Wind-Solar-Hybrid.pdf"],
   ["Wind-Solar Hybrid", "Juniper Green Eta Five Pvt Ltd", 75, "", 3.60, "18.11.2024", "Intrastate", "g.-Wind-Solar-Hybrid.pdf"],
   ["Wind-Solar Hybrid", "Juniper Green Energy Five Pvt Ltd", 75, 0, 3.60, "18.11.2024", "Intrastate", "g.-Wind-Solar-Hybrid.pdf"],
   ["Wind-Solar Hybrid", "AVAADA Green Sustainable Energy Pvt Ltd", 850, 0, 3.61, "26.11.2024", "Intrastate", "g.-Wind-Solar-Hybrid.pdf"],
   ["Wind-Solar Hybrid", "Avaada Energy Pvt Ltd", 500, 0, 3.60, "26.11.2024", "Intrastate", "g.-Wind-Solar-Hybrid.pdf"]])

# DAS snapshot 24.10.2026 16:00
DS = "https://www.mahadiscom.in/DAS_LS/DAS_and_LS.pdf (24.10.2026 16:00, created 25.10.2026)"
das = [("System","MSEDCL demand incl OA",27655,""),("System","Availability",27655,""),("System","Shortfall (load shedding)",0,""),
 ("IPP","APML Tiroda",3085,2508),("IPP","RattanIndia Power Ltd",1200,1304),("IPP","EMCO*",200,193),("IPP","TPCL Mundra (CGPL)*",760,635),
 ("IPP","JSWEL",300,316),("IPP","Sai Wardha (U-3 forced outage)",240,186),("IPP","IPP Total",5785,5142),
 ("MSPGCL","Bhusawal Unit 3",210,153),("MSPGCL","Bhusawal Unit 4&5",1000,871),("MSPGCL","Bhusawal Unit 6",630,545),
 ("MSPGCL","Chandrapur Unit 3 to 7 (U-7 forced outage)",1920,1048),("MSPGCL","Chandrapur Unit 8&9",1000,858),
 ("MSPGCL","Khaparkheda Unit 1 to 4",840,480),("MSPGCL","Khaparkheda Unit 5",500,173),("MSPGCL","Koradi Unit 6 (forced outage)",210,0),
 ("MSPGCL","Koradi Unit 8 to 10",1980,1350),("MSPGCL","Nasik (U-5 forced outage)",630,332),("MSPGCL","Paras (U-3 forced outage)",500,210),
 ("MSPGCL","Parli Unit 6&7",500,403),("MSPGCL","Parli Unit 8",250,180),("MSPGCL","Case-IV bidding (IEPL)",180,0),
 ("MSPGCL","Uran Gas (A0 forced outage)",672,270),("MSPGCL","MSPGCL Total",10842,6872),
 ("NTPC","Mouda I&II (Stg-II U4 planned outage)",890,589),("NTPC","Korba",742,707),("NTPC","Kahalgaon",139,90),("NTPC","VSTPS I-V",1470,1348),
 ("NTPC","Sipat I&II",822,783),("NTPC","Kawas GPS (RSD)",200,0),("NTPC","Gandhar GPS (RSD/gas shortage)",196,0),("NTPC","Solapur",625,595),
 ("NTPC","Gadarwara-I",105,96),("NTPC","Lara",274,258),("NTPC","Khargone-I",95,87),("NTPC","NTPC Total*",5558,4554),
 ("NPCIL","Kakrapar",142,128),("NPCIL","Kakrapar 3&4",426,368),("NPCIL","Tarapur 1&2",160,144),("NPCIL","Tarapur 3&4",412,300),("NPCIL","NPCIL Total*",1140,940),
 ("Hydro","Koyna",1920,134),("Hydro","Ghatghar (U-1 forced outage)",250,0),("Hydro","Small Hydro",500,75),("Hydro","Sardar Sarovar",440,39),
 ("Hydro","Bhira",80,40),("Hydro","Tillari",66,0),("Hydro","Vaitarna",60,0),("Hydro","KDPH",36,0),("Hydro","Pench",54,39),("Hydro","Hydro Total",3406,327),
 ("Solar","Solar (Intra)",3300,2505),("Solar","Solar (Inter)",1825,1063),("Wind","Wind (Intra)",2880,317),("Wind","Wind (Inter)",133,24),
 ("Cogen","Cogen",2370,244),("Market","Short Term Purchase (contracted cell shows #REF!)","",289),("Market","Power Exchange","",2919),
 ("Market","URS","",0),("Market","Banking",0,96),("Other","Others (OA consumer, OD/UD)","",2364),("Total","Total",33044,27655),
 ("Market","Purchased from market via e-DEEP portal (PFC)","",289),("Market","Purchased via exchange","",2919),("Market","Total market purchase","",3208)]
w("msedcl_daily_supply_snapshot_2026-10-24_1600.csv", ["group","station","contracted_mw","gross_generation_or_schedule_mw","doc"], [list(r)+[DS] for r in das])

# FY2025-26 audited accounts power purchase note (OCR text layer of scanned PDF; noisy - verify against PDF)
FS = "Standalone-MSEDCL-Fianacial-FY-2025-26_compressed-1ocr.pdf (OCR text layer)"
w("msedcl_fy2025_26_accounts_power_purchase.csv", ["item","unit","value","note","doc"],
  [["Long-term PP quantum","MU",155574.30,"Thermal 119813.79; Hydro 5067.71; RE 23021.72; Nuclear 6428.85; Others 1236.23",FS],
   ["Long-term fixed charges","Rs lakh",2111853.84,"Thermal 1983695.10",FS],
   ["Long-term energy charges","Rs lakh",5640764.52,"Thermal 4221290.75; Nuclear 290445.13",FS],
   ["Long-term total PP cost","Rs lakh",7752618.35,"",FS],
   ["Late payment surcharge paid (long-term)","Rs lakh",44346.65,"Thermal 43329.90; RE 1016.75",FS],
   ["Long-term PP cost incl LPS","Rs lakh",7801174.63,"",FS],
   ["Medium-term PP quantum","MU",3100.83,"thermal",FS],
   ["Medium-term fixed charges","Rs lakh",80325.33,"",FS],
   ["Medium-term energy charges","Rs lakh",86573.42,"",FS],
   ["Medium-term total","Rs lakh",166898.75,"LPS 13.12; rebate 1739.60",FS],
   ["Short-term bilateral quantum","MU",3690.73,"thermal 2919.65; RE 98.10; others 672.98",FS],
   ["Short-term bilateral cost","Rs lakh",159795.39,"",FS],
   ["Short-term exchange quantum","MU",6599.83,"OCR garbled row label; read as exchange",FS],
   ["Short-term exchange cost","Rs lakh",286868.27,"OCR garbled row label",FS],
   ["Short-term total cost","Rs lakh",446663.66,"",FS],
   ["Gross input energy FY2025-26","MU",168965.69,"FY2024-25: 167329.38",FS],
   ["Energy sold within periphery","MU",140248.21,"FY2024-25: 135573.12",FS],
   ["Distribution loss","MU",22385.82,"FY2024-25: 25407.95",FS],
   ["Billing efficiency","%",86.24,"FY2024-25: 84.22",FS],
   ["Total power purchase cost (net of rebate)","Rs lakh",8356964.61,"FY2024-25: 8722119.46",FS],
   ["CTU & RLDC charges","Rs lakh",361406.25,"",FS],
   ["STU & SLDC charges","Rs lakh",890959.15,"",FS],
   ["Total cost of power purchase & transmission","Rs lakh",9609330.01,"FY2024-25: 9886911.49",FS],
   ["Average power purchase cost (on gross input)","Rs/kWh",5.69,"",FS],
   ["Trade payables power purchase+transmission, closing 31.03.2026","Rs lakh",2117988.57,"opening 01.04.2025: 2676138.88",FS],
   ["Payable to MSPGCL (state own gen), closing 31.03.2026","Rs lakh",917567.96,"opening 1187644.38",FS],
   ["Payable to state IPPs, closing","Rs lakh",377016.26,"opening 555197.50",FS],
   ["Payable to CPSE within state, closing","Rs lakh",269870.49,"",FS],
   ["Payable to CPSE inter-state, closing","Rs lakh",274236.96,"",FS],
   ["Payable bilateral, closing","Rs lakh",57442.85,"",FS],
   ["Payable exchange, closing","Rs lakh",1024.95,"",FS],
   ["Payable state transmission co, closing","Rs lakh",135758.10,"",FS],
   ["Payable CPSE transmission, closing","Rs lakh",62737.00,"",FS],
   ["Delayed payment charges (income from consumers)","Rs lakh",27634.32,"previous year 31610.75",FS]])
print("ok")
