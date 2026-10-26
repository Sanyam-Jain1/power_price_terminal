import csv, sys, collections, os
d = sys.argv[1]
R = lambda n: list(csv.DictReader(open(os.path.join(d, n))))
s2 = R('daily_peak_snapshots_mw.csv'); hr = R('hourly_load_mw.csv'); s1 = R('daily_energy_balance_mu.csv'); a1 = R('daily_unit_generation.csv')
H = {(r['date'], int(r['hour_ending']), r['series']): float(r['value']) for r in hr}
mp = {'MSEDCL DEMAND MET': 'MSEDCL_demand_met', 'STATE DEMAND': 'State_demand', 'Central Sector Receipt': 'CS_net_receipt_actual', 'SOLAR': 'solar', 'WIND': 'wind'}
bad = collections.Counter(); nohour = set(); tot = 0
for r in s2:
    if r['item'] in mp:
        if not r['hour']: nohour.add(r['date']); continue
        tot += 1
        v = H.get((r['date'], int(r['hour']), mp[r['item']]))
        if v is None or abs(v - float(r['value'])) > 5: bad[(r['date'], r['snapshot'])] += 1
print('statement II hours missing for', len(nohour), sorted(nohour)[:5])
print('statement II vs hourly mismatches', len(bad), 'of', tot, list(bad.items())[:8])
# hours distribution
c = collections.Counter((r['snapshot'], r['hour']) for r in s2 if r['item'] == 'MSEDCL DEMAND MET'); print(sorted(c.items()))
# Statement I identities
S = collections.defaultdict(dict)
for r in s1: S[r['date']][(r['section'], r['item'])] = float(r['daily_mu'])
e = 0
for dt, x in S.items():
    a = x[('MSPGCL', 'Thermal')] + x[('MSPGCL', 'Hydro')] + x[('MSPGCL', 'Gas')] - x[('MSPGCL', 'Total MSPGCL')]
    b = x[('Energy_catered', 'MSEDCL')] + x[('Energy_catered', 'Mumbai Discoms')] + x[('Energy_catered', 'Other Discoms')] - x[('Energy_catered', 'Total State')]
    c2 = sum(v for (sec, it), v in x.items() if sec == 'InterState_actual' and not it.startswith('Total')) - x[('InterState_actual', 'Total net interstate exchange')]
    # hourly MSEDCL demand met sum vs MU
    hsum = sum(H.get((dt, h, 'MSEDCL_demand_met'), 0) for h in range(1, 25)) / 1000
    dd = hsum - x[('Energy_catered', 'MSEDCL')]
    if max(abs(a), abs(b), abs(c2)) > 0.05 or abs(dd) > 15:
        e += 1; print('identity', dt, round(a, 3), round(b, 3), round(c2, 3), 'hourlysum-MU', round(dd, 2))
print('identity failures', e, 'of', len(S))
# Annexure-1 station totals
st = collections.defaultdict(lambda: [0, None])
for r in a1:
    k = (r['date'], r['station'])
    if r['unit'] == 'Total': st[k][1] = float(r['daily_mu'])
    else: st[k][0] += float(r['daily_mu'])
badst = [(k, round(v[0], 2), v[1]) for k, v in st.items() if v[1] is not None and v[0] > 0 and abs(v[0] - v[1]) > 0.06]
print('annex1 station total mismatches', len(badst), badst[:15])
print(collections.Counter(r['station'] for r in a1).most_common(60))
