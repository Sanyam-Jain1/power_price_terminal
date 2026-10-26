"""Parse MSEDCL 'Power purchase through short-term tenders' FY summaries. Usage: parse_st.py OUT PDF..."""
import csv, datetime, re, subprocess, sys, os
out = sys.argv[1]; rows = []
for f in sys.argv[2:]:
    txt = subprocess.run(["pdftotext", "-layout", f, "-"], capture_output=True, text=True).stdout
    for line in txt.splitlines():
        m = re.match(r"^\s*([A-Z][a-z]{2}-\d{2})\s+(Upto\s+\d+|-)\s+([\d,.]+|-)\s+([\d.]+|-)\s*$", line)
        if m:
            ym = datetime.datetime.strptime(m.group(1), "%b-%y").strftime("%Y-%m")
            mw = re.sub(r"\D", "", m.group(2)) or ""
            mu = "" if m.group(3) == "-" else float(m.group(3).replace(",", ""))
            rt = "" if m.group(4) == "-" else float(m.group(4))
            rows.append([ym, mw, mu, rt, round(mu * rt / 10, 2) if mu != "" else "", os.path.basename(f)])
        t = re.match(r"^\s*Total\s+([\d,.]+)\s+([\d.]+)\s*$", line)
        if t:
            rows.append(["FY-total", "", float(t.group(1).replace(",", "")), float(t.group(2)), "", os.path.basename(f)])
with open(out, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["month", "max_contracted_mw_upto", "mu", "landed_rate_rs_per_kwh", "implied_cost_rs_cr", "doc"])
    w.writerows(rows)
print(len(rows))
