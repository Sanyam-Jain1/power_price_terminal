import sys, json, os
sys.path.insert(0, os.path.dirname(__file__)); import sldc
raw = sys.argv[1]
for t in sys.argv[2:]:
    out = []; meta = None
    for y in ('2026', '2025'):
        p = 1
        while True:
            j = sldc.fetch_reports(t, y=y, per_page=100, page_no=p)
            if not j.get('success', True) or 'reports' not in j:
                meta = j; break
            out += j['reports']
            if not j.get('has_more'): break
            p += 1
    json.dump(out, open(os.path.join(raw, 'listings', t + '.json'), 'w'), indent=1)
    print(t, len(out), meta if meta else '')
