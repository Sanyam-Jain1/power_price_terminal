"""Parse MSEDCL 'Power Purchase from Power Exchange for <month>' PDFs (text layer) into daily + monthly CSVs.
Usage: python3 -I parse_exchange.py EXCH_DIR DAILY_CSV MONTHLY_CSV"""
import csv, datetime, glob, os, re, subprocess, sys
d, daily_csv, mon_csv = sys.argv[1:4]
daily, monthly = [], []
for f in sorted(glob.glob(os.path.join(d, "*.pdf"))):
    txt = subprocess.run(["pdftotext", "-layout", f, "-"], capture_output=True, text=True).stdout
    title = next((l.strip() for l in txt.splitlines() if "Power Exchange" in l), "")
    days = []
    ldc = []
    for line in txt.splitlines():
        m = re.match(r"^\s*(\d{1,2}-[A-Za-z]{3}-\d{2})\s+(?:(Upto\s+\d+)\s+([\d.]+\s+to\s+[\d.]+)\s+)?(-?[\d,]+\.\d+)\s+(-?[\d.]+)\s*$", line)
        if m:
            dt = datetime.datetime.strptime(m.group(1), "%d-%b-%y").date()
            mu, rate = float(m.group(4).replace(",", "")), float(m.group(5))
            days.append(dt)
            daily.append([dt.isoformat(), mu, rate, m.group(2) or "", m.group(3) or "", os.path.basename(f)])
        l2 = re.match(r"^\s*(?:(Upto\s+\d+)\s+([\d.]+\s+to\s+[\d.]+)\s+)?([\d,]+\.\d+)\s+([\d.]+)\s*$", line)
        if not l2 and "Long" in line and not m:
            l2 = re.search(r"()()([\d,]+\.\d+)\s+([\d.]+)\s*$", line)
        if l2 and not m and "Total" not in line:
            ldc.append([float(l2.group(3).replace(",", "")), float(l2.group(4)), (l2.group(1) or "") + " " + (l2.group(2) or "")])
        t = re.match(r"^\s*Total\s+(-?[\d,]+\.\d+)\s+(-?[\d.]+)\s*$", line)
        if t:
            tot = (float(t.group(1).replace(",", "")), float(t.group(2)))
    ym = days[0].strftime("%Y-%m")
    sub = [r for r in daily if r[5] == os.path.basename(f)]
    smu = sum(r[1] for r in sub); wavg = sum(r[1] * r[2] for r in sub) / smu
    lmu = sum(x[0] for x in ldc); lrate = (sum(x[0] * x[1] for x in ldc) / lmu) if lmu else None
    for x in ldc:
        daily.append([ym + "-LDC", x[0], x[1], x[2].strip(), "long-duration contract (month block, as printed)", os.path.basename(f)])
    monthly.append([ym, tot[0], tot[1], round(tot[0] * tot[1] / 10, 2), len(sub), round(smu, 2), round(wavg, 3),
                    round(lmu, 2), round(lrate, 3) if lrate else "", round(smu + lmu - tot[0], 2),
                    max(r[2] for r in sub), min(r[2] for r in sub), max(r[1] for r in sub), title, os.path.basename(f)])
with open(daily_csv, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["date", "mu", "rate_rs_per_kwh", "mw_cap_text", "rate_range_text", "doc"])
    w.writerows(sorted(daily))
with open(mon_csv, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["month", "mu_total_printed", "avg_rate_printed_rs_kwh", "implied_cost_rs_cr", "n_days", "mu_sum_of_days",
                "daily_weighted_rate", "long_duration_contract_mu", "long_duration_contract_rate", "check_diff_mu", "max_daily_rate", "min_daily_rate", "max_daily_mu", "doc_title", "doc"])
    w.writerows(sorted(monthly))
for r in sorted(monthly): print(r[:13])
