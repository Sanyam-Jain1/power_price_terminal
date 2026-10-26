"""Keep only unambiguous rows from the page-1 parse of the monthly Generation report.
Dropped: TATA block (aux-consumption cells span several rows), Pench(MS) (merged with requirement line),
IPP/CPP 'Total' (max-MW column misaligned), single-line Wind/Solar rows (header misattributed; also on page 2),
and the 'at InSTS' summary lines (duplicated on page 2).
Usage: python3 -I filter_monthly_units.py <in_csv> <out_csv>"""
import csv, sys
rows = list(csv.DictReader(open(sys.argv[1])))
keep, drop = [], 0
for r in rows:
    st, u = r['station_header'], r['unit_or_item']
    bad = (st in ('TATA', 'Pench(MS)', '', None) or u in ('Wind', 'Solar') or
           (st == 'IPP/CPP' and u == 'Total') or (st == 'AEML (R-INFRA)' and u not in ('Adani DTPS 1-2', 'Total')) or
           (st == 'PGPL' and u.startswith('Pench')))
    if bad: drop += 1; continue
    keep.append(r)
# Total rows: keep only if they equal the sum of the unit rows above them (else column misalignment)
import collections
sums = collections.defaultdict(float)
for r in keep:
    if r['unit_or_item'] != 'Total': sums[(r['month'], r['station_header'])] += float(r['monthly_gen_mu'] or 0)
seen = set(); k2 = []
for r in keep:
    if r['unit_or_item'] == 'Total':
        key = (r['month'], r['station_header'])
        if key in seen or abs(sums[key] - float(r['monthly_gen_mu'] or 0)) > 0.5:
            drop += 1; continue
        seen.add(key)
    k2.append(r)
keep = k2
with open(sys.argv[2], 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['month', 'station', 'unit', 'monthly_gen_mu', 'max_gen_mw', 'aux_consumption_mu'])
    w.writeheader()
    for r in keep:
        w.writerow(dict(month=r['month'], station=r['station_header'], unit=r['unit_or_item'], monthly_gen_mu=r['monthly_gen_mu'],
                        max_gen_mw=r['max_gen_mw'], aux_consumption_mu=r['aux_consumption_mu']))
print('kept', len(keep), 'dropped', drop)
