"""Consolidate WRPC weekly files into Maharashtra block- and day-level procurement tables."""
import csv, gzip, sys
from collections import defaultdict
from datetime import date
from pathlib import Path
import numpy as np
from dhruva import store
RAW=Path(sys.argv[1]); OUT=Path(sys.argv[2]); OUT.mkdir(exist_ok=True)
f=lambda x: float(x) if x not in ('',None) else 0.0
state={}            # (date,block) -> dict
isgs=defaultdict(float)   # (date,block,entity,benf) -> MW
for wk in sorted(p for p in RAW.iterdir() if p.is_dir()):
    for r in csv.DictReader(open(wk/'MSEB_State_DSM-2024_Data.csv', encoding='utf-8', errors='replace')):
        k=(r['Date'],int(r['Block']))
        state[k]=dict(freq=f(r['Freq(Hz)']), actual_mwh=f(r['Actual (MWH)']), schedule_mwh=f(r['Schedule (MWH)']), dev_mwh=f(r['Deviation(MWH)']),
                      payable=f(r['DSM Payable (Rs.)'])+f(r.get('Adjusted DSM Payable On Account of Nuclear Stations')),
                      receivable=f(r['DSM Receivable (Rs.)'])+f(r.get('Adjusted DSM Receivable On Account of Nuclear Stations')),
                      nr=f(r['Normal Rate (p/Kwh)'])*10)
    for r in csv.DictReader(open(wk/'MSEB_State_schedule.csv', encoding='utf-8', errors='replace')):
        isgs[(r['date'],int(r['block']),r['entity'].strip(),r['benf'].strip())]+=f(r['sch_after_loss'])
dates=sorted({d for d,_ in state}); a,b=date.fromisoformat(dates[0]),date.fromisoformat(dates[-1])
px={}
for m in ('dam','rtm','gdam'):
    ds,p=store.block_matrix(m,'mcp',a,date.fromordinal(b.toordinal()+1)); _,v=store.block_matrix(m,'mcv_mw',a,date.fromordinal(b.toordinal()+1)); _,buy=store.block_matrix(m,'purchase_bid_mw',a,date.fromordinal(b.toordinal()+1))
    for i,d in enumerate(ds):
        for j in range(96): px[(m,d,j+1)]=(p[i][j],v[i][j],buy[i][j])
ib=defaultdict(float); ib_mseb=defaultdict(float)
for (d,blk,e,bf),mw in isgs.items():
    ib[(d,blk)]+=mw/4
    if bf=='MSEB_Beneficiary': ib_mseb[(d,blk)]+=mw/4
with gzip.open(OUT/'mh_blocks.csv.gz','wt') as fh:
    w=csv.writer(fh); w.writerow(['date','block','freq_hz','actual_drawal_mwh','schedule_mwh','isgs_all_mwh','isgs_msedcl_mwh','other_interstate_mwh','deviation_mwh','dsm_payable_rs','dsm_receivable_rs','normal_rate_rs_mwh','dam_rs_mwh','dam_cleared_mw','dam_buy_bids_mw','rtm_rs_mwh','gdam_rs_mwh'])
    for k in sorted(state):
        s=state[k]; d,blk=k
        dm=px.get(('dam',d,blk),(None,None,None)); rt=px.get(('rtm',d,blk),(None,None,None)); gd=px.get(('gdam',d,blk),(None,None,None))
        w.writerow([d,blk,s['freq'],round(s['actual_mwh'],3),round(s['schedule_mwh'],3),round(ib[k],3),round(ib_mseb[k],3),round(s['schedule_mwh']-ib[k],3),round(s['dev_mwh'],3),round(s['payable']),round(s['receivable']),s['nr'],dm[0],dm[1],dm[2],rt[0],gd[0]])
# daily ISGS by source and beneficiary
day=defaultdict(float)
for (d,blk,e,bf),mw in isgs.items(): day[(d,e,bf)]+=mw/4
with open(OUT/'mh_isgs_daily.csv','w') as fh:
    w=csv.writer(fh); w.writerow(['date','source','beneficiary','scheduled_mwh'])
    for (d,e,bf),v in sorted(day.items()):
        if abs(v)>0.01: w.writerow([d,e,bf,round(v,2)])
print('blocks',len(state),'days',len(dates),dates[0],dates[-1],'isgs rows',len(isgs))
