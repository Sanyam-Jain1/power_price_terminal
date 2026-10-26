"""Category x month summary from the tidy monthly power purchase CSV."""
import csv, sys
from collections import defaultdict
src, out = sys.argv[1:3]
rows = [r for r in csv.DictReader(open(src)) if r["is_total_row"] == "0"]
agg = defaultdict(lambda: [0.0, 0.0])
months = sorted({r["month"] for r in rows})
for r in rows:
    k = (r["month"], r["category"])
    agg[k][0] += float(r["mu_actual"] or 0)
    agg[k][1] += float(r["rs_cr_actual"] or 0)
cats = sorted({k[1] for k in agg})
with open(out, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["month", "category", "mu_actual", "rs_cr_actual", "rs_per_kwh_actual"])
    for m in months:
        tm = tc = 0.0
        for c in cats:
            mu, rs = agg.get((m, c), [0.0, 0.0])
            if (m, c) not in agg:
                continue
            w.writerow([m, c, round(mu, 2), round(rs, 2), round(rs * 10 / mu, 3) if abs(mu) > 0.5 else ""])
            if c != "Transmission & Other charges":
                tm += mu; tc += rs
        w.writerow([m, "ALL POWER PURCHASE excl. transmission (sum of components)", round(tm, 2), round(tc, 2), round(tc * 10 / tm, 3)])
