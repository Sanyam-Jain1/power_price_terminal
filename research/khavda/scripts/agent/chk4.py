import zipfile,csv,io,sys,glob
def tiers(dev,avc,R,bands,mu,mo):
    a=abs(dev); prev=0; s=0
    m = mu if dev<0 else mo
    for b,k in zip(bands+[1e9],m):
        lim=b*avc if b<1e8 else 1e18
        seg=max(0,min(a,lim)-prev); s+=seg*k*R; prev=max(prev,min(a,lim))
    return s if dev<0 else -s
models={
 'DSM24_new_S(5/10)':([0.05,0.10],[1,1.1,2.0],[1,0.9,0]),
 'DSM24_new_W(10/15)':([0.10,0.15],[1,1.1,2.0],[1,0.9,0]),
 'DSM24_old_S(10/15)':([0.10,0.15],[1,1.1,2.0],[1,0.9,0]),
 'DSM24_old_W(15/20)':([0.15,0.20],[1,1.1,2.0],[1,0.9,0]),
 'FS2015(15/25/35)':([0.15,0.25,0.35],[1,1.1,1.2,1.3],[1,0.9,0.8,0.7]),
}
for zf in sys.argv[1:]:
  z=zipfile.ZipFile(zf)
  for n in sorted(z.namelist()):
    if not n.endswith('_DSM-2024_Data.csv') or '/' in n: continue
    rd=list(csv.DictReader(io.StringIO(z.read(n).decode('utf-8','replace'))))
    if not rd or 'WS Seller Capacity (Mwh)' not in rd[0]: continue
    rows=[]
    for r in rd:
        try:
            dev=float(r['Deviation(MWH)']); avc=float(r['WS Seller Capacity (Mwh)']); R=float(r['Wt. Avg. Rate (p/Kwh)'])*10
            net=float(r['DSM Payable (Rs.)'])-float(r['DSM Receivable (Rs.)'])
        except: continue
        if avc>0 and R>0 and abs(dev)/avc>=0.10: rows.append((dev,avc,R,net))
    if len(rows)<10: continue
    res={k:sum(abs(tiers(d,a,R,*v)-net)<=max(1,0.001*abs(net)) for d,a,R,net in rows) for k,v in models.items()}
    best=max(res,key=res.get)
    print(f"{n[:-18]:32s} n={len(rows):4d} best={best} {res[best]}  all={res}")
