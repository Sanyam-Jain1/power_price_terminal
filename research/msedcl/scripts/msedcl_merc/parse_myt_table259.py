"""Parse MERC MYT Order (Case 217 of 2024, 28.03.2025) Table 259: source-wise power purchase FY 2026-27
(MSEDCL petition vs approved). Usage: parse_myt_table259.py TXT OUT_CSV"""
import csv, re, sys
txt, out = sys.argv[1:3]
L = open(txt, encoding="utf-8").read().splitlines()
s = max(i for i, l in enumerate(L) if "Table 259: Power Purchase Quantum and Cost for FY 2026-27" in l)
e = next(i for i in range(s, len(L)) if "Table 260:" in L[i])
TOK = r"(?:-?[\d,]+(?:\.\d+)?|-)"
rows, section, carry = [], "Long Term Supply", ""
for l in L[s:e]:
    st = l.strip()
    if not st or st.startswith(("MERC Order", "MYT Order", "2024-25 and approval", "(MU)", "wise)", "Source of Power", "FY 2026-27", "Commission", "Table 259")):
        continue
    if st in ("Long Term Supply", "Medium Term Supply", "Short Term Supply"):
        section = st; continue
    toks = st.split(); nums = []
    while toks and re.fullmatch(TOK, toks[-1]) and len(nums) < 6:
        nums.insert(0, toks.pop())
    name = " ".join(toks)
    if len(nums) >= 3 and (name or carry):
        full = (carry + " " + name).strip(); carry = ""
        v = [None if x == "-" else float(x.replace(",", "")) for x in nums]
        if len(v) == 6:
            rec = v
        elif len(v) == 4 and name == "" :
            rec = [v[0], v[1], None, v[2], v[3], None]
        else:
            rec = [None] * (6 - len(v)) + v
        rows.append([section, full] + rec)
    elif not nums:
        carry = (carry + " " + st).strip()
    else:
        rows.append([section, ("UNPARSED " + carry + " " + st).strip()] + [None] * 6); carry = ""
# tidy-ups for rows the layout wraps (verified against the text of the table)
fix = {"Renewable - Solar inter (Loss": "Renewable - Solar (intra 3.04 + inter-loss-NA 3.87 + inter 2.67 Rs/kWh; one combined figure in order)",
       "Renewable - PHSP (JSW, Torrent, SSP PHSP &": "Renewable - PHSP (JSW, Torrent, SSP PHSP & Ghatghar)",
       "Ghatghar) KAPP": "KAPP", "Short     Term        (Power": "Short Term (Power Exchange)",
       "Exchange) Total Energy Availability": "Total Energy Availability", "Total": "Total Long Term (approved MU only)"}
clean = []
sec = "Long Term Supply"
for r in rows:
    if r[1].startswith("UNPARSED"):
        continue
    if r[1] == "Renewable - Solar inter (Loss":
        r[2:8] = [r[4], r[5], None, r[6], r[7], None]
    r[1] = fix.get(r[1], r[1])
    if r[1] in ("Medium Term Supply", "Short Term Supply"):
        sec = r[1]; continue
    r[0] = "Total" if r[1].startswith("Total") else sec
    clean.append(r)
rows = clean
with open(out, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["supply_type", "source", "petition_mu", "petition_rs_cr", "petition_rs_per_kwh",
                "approved_mu", "approved_rs_cr", "approved_rs_per_kwh"])
    w.writerows(rows)
for r in rows: print(r)
