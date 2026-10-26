"""Parse Annexure IV-B (FY 2026-27 monthly approved MU and variable cost by station) of MERC Order
Case 75 of 2025 dated 25.03.2026 from pdftotext -layout output.
Usage: parse_myt_monthly.py TXT OUT_CSV"""
import csv, re, sys
txt, out = sys.argv[1:3]
lines = open(txt, encoding="utf-8").read().splitlines()
start = next(i for i, l in enumerate(lines) if "B) For FY 2026-27" in l)
end = next((i for i in range(start + 1, len(lines)) if re.search(r"C\) FY 2027-28", lines[i])), len(lines))
months = ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12", "2027-01", "2027-02", "2027-03"]
NUM = r"-?[\d,]+(?:\.\d+)?"
rows, skipped, group, prevtext = [], [], "", ""
for l in lines[start:end]:
    s = l.strip()
    if not s or s.startswith("MERC Order") or "Particulars" in s or s.startswith("(") or "Energy" in s and "VC" in s:
        continue
    toks = s.split()
    nums = []
    while toks and re.fullmatch(NUM, toks[-1]) and len(nums) < 25:
        nums.insert(0, toks.pop())
    name = " ".join(toks)
    if not name and len(nums) in (24, 25):
        nxt = lines[lines.index(l) + 1].strip() if lines.index(l) + 1 < len(lines) else ""
        name = (prevtext + " " + nxt).strip()
        pending_skip = nxt
    if name and name == globals().get("pending_skip"):
        continue
    if len(nums) in (24, 25) and name:
        rate = float(nums[0]) if len(nums) == 25 else None
        vals = [float(x.replace(",", "")) for x in nums[-24:]]
        for i, m in enumerate(months):
            rows.append([m, name, "Must-run" if group.startswith("Must") else "Merit-order (MoD)", rate, vals[2 * i], vals[2 * i + 1]])
    elif not nums and name and len(name) < 60:
        if name.startswith(("Must Run", "Stations under MoD")):
            group = name
        prevtext = name
    else:
        skipped.append(s[:160])
with open(out, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["month", "source", "merc_group", "energy_charge_rs_per_kwh", "approved_mu", "approved_variable_cost_rs_cr"])
    w.writerows(rows)
print(len(rows) // 12, "sources;", "skipped lines:")
print("\n".join(skipped))
