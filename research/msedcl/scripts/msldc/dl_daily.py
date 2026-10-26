import sys, json, datetime, os
sys.path.insert(0, os.path.dirname(__file__)); import sldc
raw = sys.argv[1]
recs = json.load(open(os.path.join(raw, 'listings/daily_2026.json')))
log = []
for r in sorted(recs, key=lambda r: (int(r['month']), int(r['day']))):
    d = datetime.date(int(r['year']), int(r['month']), int(r['day']))
    p = os.path.join(raw, 'daily_pdf', d.isoformat() + '.pdf')
    res = sldc.download(r['attachment_url'], p, delay=1.0)
    log.append(dict(date=d.isoformat(), url=r['attachment_url'], result=res))
# guess missing dates using the standard pattern (public static path)
have = {x['date'] for x in log}
d = datetime.date(2026, 4, 1)
while d <= datetime.date(2026, 10, 25):
    if d.isoformat() not in have:
        for suf in ('', '1', '_(1)'):
            u = 'https://mahasldc.in/assets/shared/reports/WEBSITE%02d%s%d%s.pdf' % (d.day, d.strftime('%b'), d.year, suf)
            res = sldc.download(u, os.path.join(raw, 'daily_pdf', d.isoformat() + '.pdf'), delay=1.0)
            log.append(dict(date=d.isoformat(), url=u, result=res, guessed=True))
            if isinstance(res, int) and res > 1000 or res == 'cached': break
    d += datetime.timedelta(1)
json.dump(log, open(os.path.join(raw, 'listings/daily_download_log.json'), 'w'), indent=1)
print('done', len(log))
