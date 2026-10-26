"""Parse MSEDCL 'Final PPA list for July 2025' (conventional PPAs) into CSV.
Usage: parse_ppa_list.py PDF OUT_CSV"""
import csv, re, subprocess, sys
pdf, out = sys.argv[1:3]
txt = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout
section = ""
rows = []
DATE = r"(?:\d{1,2}\.\d{1,2}\.\d{3,4}|\d{4}|U#\d: [\d.]+|-|_|…)"
for line in txt.splitlines():
    s = line.strip()
    if "MSPGCL (Mahagenco)" in s: section = "MSPGCL"
    elif "CENTRAL SECTOR" in s: section = "Central sector (MSEDCL share)"
    elif "Future Contracted" in s: section = "Future contracted (not yet commissioned)"
    elif "other Hydro Stations" in s: section = "Other hydro"
    elif "IPP and UMPP" in s: section = "IPP/UMPP"
    m = re.match(r"^(\d{1,2})\s+(.+?)\s{2,}(\d{2,5})\s+(?:(\d{2,5})\s+)?(Thermal|Gas|Hydro|Nuclear|Small Hydro|PSS Hydro)?\s*(.*)$", s)
    if not m or not section:
        continue
    sr, name, cap1, cap2, gtype, rest = m.groups()
    nums = re.findall(r"(?<![\d.])(NA|\d+\.\d{3}|\d\.\d{2})(?![\d.])", rest)
    dates = re.findall(r"\d{1,2}\.\d{1,2}\.\d{3,4}", rest)
    fc = vc = tot = ""
    if len(nums) >= 3:
        fc, vc, tot = nums[-3:]
    elif len(nums) == 2:
        vc, tot = nums
    elif len(nums) == 1 and section == "Other hydro":
        tot = nums[0]
    if section == "Future contracted (not yet commissioned)":
        rows.append([section, name, cap2 or "", gtype or "", "", "", "", "", "", f"total station capacity {cap1} MW; {rest}".strip()])
        continue
    rows.append([section, name, cap1, gtype or "", dates[0] if dates else "", dates[1] if len(dates) > 1 else "",
                 fc, vc, tot, rest if not nums else ""])
# Fix-ups for rows whose layout wraps (values transcribed from the same PDF text)
fixed = []
for r in rows:
    sec, name = r[0], r[1]
    if sec == "Future contracted (not yet commissioned)":
        continue
    if sec == "MSPGCL" and r[3] in ("Hydro", "Small Hydro", "PSS Hydro"):
        r[5], r[4] = r[4], ""
        r[9] = {"Koyna Stage-I & II": "Koyna I-IV + KDPH: fixed Rs 238.4 Cr/yr, VC 0.760 Rs/kWh (combined)",
                "Koyna Stage-III": "Koyna I-IV + KDPH: fixed Rs 238.4 Cr/yr, VC 0.760 Rs/kWh (combined)",
                "Koyna Stage-IV": "Koyna I-IV + KDPH: fixed Rs 238.4 Cr/yr, VC 0.760 Rs/kWh (combined)",
                "KDPH": "Koyna I-IV + KDPH: fixed Rs 238.4 Cr/yr, VC 0.760 Rs/kWh (combined)",
                "BHIRA Unit-1 & 02": "fixed Rs 7.51 Cr/yr; VC 1.080 Rs/kWh",
                "TILLARI Unit-1": "fixed Rs 13.13 Cr/yr; VC 1.250 Rs/kWh",
                "Ghatghar PSS Unit-1 & 2": "Rs 19.98 Cr per month",
                "VAITARNA Unit-1": "Rs 2.82 Cr per month"}.get(name, "")
        if name.startswith("BHIRA"): r[7] = "1.080"
        if name.startswith("TILLARI"): r[7] = "1.250"
        if name.startswith(("Koyna", "KDPH")): r[7] = "0.760"
    if name in ("KAWAS GPS", "Gandar GPS"):
        r[5], r[4] = r[4], ("01.11.1993 / 01.11.1995" if name == "KAWAS GPS" else "01.01.2009 / 20.03.2010 (as printed)")
    if name == "KAWAS GPS":
        r[6:10] = ["0.868", "", "", "VC by fuel Rs/kWh: APM 0.00, C-GAS 9.499, Liquid 23.026, RLNG 9.775 (total: 0.8684/10.3674/23.8944/10.6434)"]
    if name == "Gandar GPS":
        r[6:10] = ["1.032", "", "", "VC by fuel Rs/kWh: APM 0.00, C-GAS 9.432, RLNG 9.709 (total: 1.0319/10.4639/10.7409)"]
    if name in ("Khargone", "Lara"):
        r[5], r[4] = r[4], ("U#1 1.02.2020, U#2 4.04.2020" if name == "Khargone" else "U#1 1.10.2019, U#2 7.11.2020")
    if name == "Dodson II":
        r[9] = "MERC Case 105 of 2009: fixed charges Rs 2.038 Cr/month for FY 2025-26"
    if sec == "IPP/UMPP":
        r[3] = "Thermal"
    fixed.append(r)
fut = "Future contracted (not yet commissioned)"
fixed += [[fut, "NTPC Lara Stage 02, Units 1&2 (2x800 MW)", "228", "Thermal", "Expected FY 2023-24 (as printed)", "16.12.2010", "", "", "", "total capacity 1600 MW"],
          [fut, "Subansiri Hydro Electric Project", "183", "Hydro", "Expected FY 2023-24 (as printed)", "10.02.2012", "", "", "", "total capacity 2000 MW"],
          [fut, "M/s Adani Power Ltd.", "1600", "Thermal", "Expected FY 2029-30", "", "", "", "", "total capacity 1600 MW"],
          [fut, "M/s JSW Hydro Electric Project (PSP)", "1500", "Hydro", "Expected FY 2028-29", "", "", "", "", "total capacity 1500 MW"],
          [fut, "M/s Torrent Hydro Electric Project (PSP)", "1500", "Hydro", "Expected FY 2028-29", "", "", "", "", "total capacity 1500 MW"]]
rows = fixed
with open(out, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["section", "generator", "contracted_mw", "type", "date_commissioning", "date_ppa",
                "normative_capacity_charge_rs_kwh", "variable_charge_rs_kwh", "total_rs_kwh", "remark_raw"])
    w.writerows(rows)
for r in rows: print(r[:9])
