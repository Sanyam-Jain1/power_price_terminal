import zipfile,csv,io,sys,glob,re,collections
D='/home/user/power_price_terminal/data/'
def load(mkt):
    p={}
    for f in glob.glob(D+mkt+'/2026-*.csv'):
        for r in csv.DictReader(open(f)):
            try: p[(r['date'],int(r['block']))]=float(r['mcp'])
            except: pass
    return p
mk={m:load(m) for m in ('dam','rtm','gdam')}
cls=lambda e: 'solar' if re.search(r'_S$|SOLAR|_RSP$',e,re.I) else ('wind' if re.search(r'_W$',e) else ('hybrid' if re.search(r'_H$|_HS$|_HW$',e) else None))
seen=set(); gen=collections.defaultdict(lambda: collections.defaultdict(float)); tot=collections.defaultdict(float)
for zf in sorted(glob.glob(sys.argv[1]+'/*.zip')):
    z=zipfile.ZipFile(zf)
    for n in z.namelist():
        if not n.endswith('_DSM-2024_Data.csv') or '/' in n: continue
        e=n[:-len('_DSM-2024_Data.csv')]; c=cls(e)
        if not c or 'QCA' in e or 'nfirm' in e: continue
        for r in csv.DictReader(io.StringIO(z.read(n).decode('utf-8','replace'))):
            k=(e,r['Date'],r['Block'])
            if k in seen: continue
            seen.add(k)
            a=max(0.0,float(r['Actual (MWH)'] or 0)); key=(r['Date'],int(r['Block']))
            if all(key in mk[m] for m in mk):
                tot[c]+=a
                for m in mk: gen[c][m]+=a*mk[m][key]
dates=sorted({k[1] for k in seen}); print('period',dates[0],dates[-1])
for m in mk:
    keys=[k for k in mk[m] if dates[0]<=k[0]<=dates[-1]]
    print(m,'time-avg Rs/MWh',round(sum(mk[m][k] for k in keys)/len(keys)))
for c in tot:
    print(c,'MWh',round(tot[c]),{m:round(gen[c][m]/tot[c]) for m in mk})
