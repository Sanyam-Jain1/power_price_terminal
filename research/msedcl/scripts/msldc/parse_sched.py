"""Parse MSEDCL day-schedule JSON from dsm-scheduling.mahasldc.in/WEBACCESS/getapidata.
Usage: python3 -I parse_sched.py <sched_dir> <out_dir> <last_date_inclusive>"""
import csv, glob, json, os, sys, collections
src, out, last = sys.argv[1], sys.argv[2], sys.argv[3]
SUMMARY = ['CentreTotal', 'IntraStateLTOATotal', 'IntraStateMTOATotal', 'IntraStateSTOATotal', 'IntraStateGenerationTotal',
           'REMCTotal', 'IEXTotal', 'PXITotal', 'HPXTotal', 'GDAM_IEXTotal', 'GDAM_PXITotal', 'GDAM_HPXTotal',
           'RTM_IEXTotal', 'RTM_PXITotal', 'RTM_HPXTotal', 'GRTM_IEXTotal', 'GRTM_PXITotal', 'GRTM_HPXTotal',
           'VSETotal', 'StanbyTotal', 'IntraDiscomTradeTotal', 'ForecastedDemand', 'Demand',
           'TargetInjScheduleExBus', 'TargetInjScheduleWithLoss', 'SurplusShortFall']
blocks, daily, bysrc, meta, dc = [], [], [], [], []
issues = []


def series(s):
    v = [float(x) for x in s.split(',')] if s else []
    return v


for f in sorted(glob.glob(os.path.join(src, '*.json'))):
    date = os.path.basename(f)[:10]
    if date > last:
        continue
    try:
        j = json.load(open(f))
    except Exception:
        issues.append(f'{date}: not JSON ({open(f, errors="replace").read(100)!r})'); continue
    meta.append((date, j.get('fullschdRevisionNo'), j.get('schedulePublishedTime'), j.get('scheduleRemarks'), len(j.get('fullschdList', []))))
    sm = j['scheduleSummaryList'][0]
    for k in SUMMARY:
        v = series(sm.get(k, ''))
        if len(v) != 96:
            issues.append(f'{date}: {k} has {len(v)} blocks'); continue
        for b, x in enumerate(v, 1):
            blocks.append((date, b, k, x))
        daily.append((date, k, round(sum(v) / 4000, 4), round(max(v), 2), round(min(v), 2)))
    agg = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for r in j['fullschdList']:
        v = series(r['ScheduleAmount'])
        if len(v) != 96:
            issues.append(f'{date}: schedule row {r.get("SellerAcr")} has {len(v)} blocks'); continue
        k = (r['BuyerAcr'], r.get('BuyerParentName') or '', r['SellerAcr'], r['ScheduleTypeName'], r.get('SubScheduleTypeName') or '',
             r.get('FuelTypeName') or '', r.get('TraderAcr') or '')
        a = agg[k]; a[0] += sum(v) / 4000; a[1] = max(a[1], max(v)); a[2] += 1
    for k, a in sorted(agg.items()):
        bysrc.append((date, *k, round(a[0], 4), round(a[1], 2), a[2]))
    for r in j.get('decList', []):
        v = series(r['DeclaredAmount'])
        if len(v) == 96:
            dc.append((date, r['SellerAcr'], round(sum(v) / 4000, 4), round(sum(v) / 96, 2), round(max(v), 2), r.get('RevisionNo'), (r.get('Comments') or '')[:60]))


def w(name, header, rows):
    with open(os.path.join(out, name), 'w', newline='') as fh:
        c = csv.writer(fh); c.writerow(header); c.writerows(rows)
    print(name, len(rows))


w('sched_msedcl_summary_blocks_mw.csv', ['date', 'block_15min', 'series', 'mw'], blocks)
w('sched_msedcl_summary_daily.csv', ['date', 'series', 'energy_mu', 'max_block_mw', 'min_block_mw'], daily)
w('sched_msedcl_by_source_daily_mu.csv', ['date', 'buyer_acr', 'buyer_parent', 'seller_acr', 'schedule_type', 'sub_type', 'fuel', 'trader',
                                          'energy_mu', 'max_block_mw', 'n_rows'], bysrc)
w('sched_msedcl_declared_capability_daily.csv', ['date', 'seller_acr', 'dc_energy_mu', 'dc_avg_mw', 'dc_max_mw', 'revision_no', 'comment'], dc)
w('sched_msedcl_revision_meta.csv', ['date', 'revision_no', 'published_time', 'remarks', 'n_schedule_rows'], meta)
open(os.path.join(out, '_parse_issues_sched.txt'), 'w').write('\n'.join(issues))
print('issues', len(issues), issues[:5])
