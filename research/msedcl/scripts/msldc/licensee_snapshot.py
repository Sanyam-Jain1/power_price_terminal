"""Licensee schedule snapshot for one day from the scheduling Web API (other ACRs only allow yesterday/today).
Usage: python3 -I licensee_snapshot.py <probe_dir> <msedcl_json> <out_csv>"""
import csv, glob, json, os, sys
rows = []
files = sorted(glob.glob(os.path.join(sys.argv[1], '*_2026-10-25.json'))) + [sys.argv[2]]
for f in files:
    try: j = json.load(open(f))
    except Exception: continue
    if not j.get('scheduleSummaryList'): continue
    s = j['scheduleSummaryList'][0]
    if not any(isinstance(v, str) and ',' in v for v in s.values()): continue
    for k, v in s.items():
        if isinstance(v, str) and ',' in v:
            x = [float(a) for a in v.split(',')]
            rows.append((j['Date'][:10], s['acronym'], k, round(sum(x) / 4000, 4), round(max(x), 2), j.get('fullschdRevisionNo'), j.get('schedulePublishedTime')))
with open(sys.argv[3], 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['date', 'licensee_acr', 'series', 'energy_mu', 'max_block_mw', 'revision_no', 'published_time']); w.writerows(rows)
print(len(rows))
