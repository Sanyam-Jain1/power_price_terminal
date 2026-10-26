"""MSEDCL daily procurement ledger, 11 Sep - 25 Oct 2026.

Volumes: MSEDCL's own day-ahead/real-time schedules by seller (MSLDC public Web API).
Prices: MERC-approved FY2026-27 energy charge for the month (variable cost only; fixed/capacity
charges are owed regardless of dispatch and are reported separately), actual IEX/PXIL/HPX block prices
for exchange buys, and nothing for swap returns (settled in energy, not money).
"""
import csv, re, sys, collections
from datetime import date
from pathlib import Path
import numpy as np
from dhruva import store
MH=Path(sys.argv[1]); OUT=MH/'ledger'
VC={}
for r in csv.DictReader(open(MH/'msedcl/merc_fy2026_27_approved_monthly_mu_vc_by_source.csv')):
    if r['energy_charge_rs_per_kwh']: VC[(r['month'],r['source'])]=float(r['energy_charge_rs_per_kwh'])
def merc(seller, stype, sub, fuel):
    s=seller.upper()
    rules=[(r'^BHUSAWAL_U3$','Bhusawal - 3'),(r'^BHUSAWAL_U[45]$','Bhusawal - 4 & 5'),(r'^BHUSAWAL_U6$','Bhusawal - 6'),
           (r'^CHANDRAPUR_U[3-7]$','Chandrapur - 3 to 7'),(r'^CHANDRAPUR_U[89]$','Chandrapur - 8 & 9'),
           (r'^KHAPERKHEDA_U[1-4]$','Khaparkheda - 1 to 4'),(r'^KHAPERKHEDA_U5$','Khaparkheda - 5'),
           (r'^KORADI_U6$','Koradi - 6'),(r'^KORADI_U(8|9|10)$','Koradi - 8 to 10'),(r'^NASHIK_U','Nashik- 3,4 & 5'),
           (r'^PARAS_U','Paras - 3 & 4'),(r'^PARLI_U[67]$','Parli - 6 & 7'),(r'^PARLI_U8$','Parli Replacement U 8'),
           (r'^URAN','GTPS Uran'),(r'KOYNA|GHATGHAR|^KDPH$|TILLARI|VAITARNA|BHIRA','Hydro'),
           (r'^KSTPS12$','KSTPS'),(r'^KSTPS7$','KSTPS III'),(r'^SIPAT1$','SIPAT TPS 1'),(r'^SIPAT2$','SIPAT TPS 2'),
           (r'^VSTPS1$','VSTP I'),(r'^VSTPS2$','VSTP II'),(r'^VSTPS3$','VSTP III'),(r'^VSTPS4$','VSTP IV'),(r'^VSTPS5$','VSTP V'),
           (r'^MOUDA1$','Mauda I'),(r'^MOUDA2$','Mauda II'),(r'^LARA$','Lara'),(r'^SOLAPUR$','NTPC Solapur'),(r'^KHSTPP_II$','KhSTPS-II'),
           (r'^GADARWARA$','Gadarwara'),(r'^KHARGONE$','Khargone'),(r'^KAPS$','KAPP'),(r'^KAPS_34$','KAPP 3 & 4'),
           (r'^TAPS_I$','TAPP 1 & 2'),(r'^TAPS_II$','TAPP 3 & 4'),(r'^SSP$','SSP'),(r'^PENCH$','Pench'),(r'^SUBANSIRI','Subhansari Hydro'),
           (r'^TPCL_MUNDRA$','CGPL'),(r'^GANDHAR','Gandhar'),(r'^KAWAS','Kawas'),(r'^APML_U','APML 1320 MW'),(r'^SWPGL','SWPGL 240 MW'),
           (r'^RIPL_U','RIPL 750 MW'),(r'^JSWEL','JSW'),(r'^GMR_WARORA$','GMR Energy'),(r'^MSEDCL_SHYDRO$','Renewable - Small Hydro'),
           (r'^MSEDCL_COGEN$','Renewable - Bagasse based Co-gen')]
    for pat,src in rules:
        if re.search(pat,s): return src
    if stype=='REMC': return 'Renewable - Solar intra' if fuel=='SOLAR' else 'Renewable - Wind'
    if sub=='GRTM_HPX': return 'Renewable - Solar inter' if fuel=='SOLAR' else 'Renewable - Hybrid Inter'
    if re.search(r'SSK|SSSK|SAIL|SPL|SAPL|SL_|SML|AIL|VNPL|IPL|AGRO|SRSL|SASPL|USTKW|USDPCL|RPSSKL|GKSEL|JSMPL|LMIL|QUINERGY|PATANGRAO|RENUKA|SMSMP',s): return 'Renewable - Bagasse based Co-gen'
    if stype in ('INTRASTATE STOA','INTRASTATE MTOA'): return 'Short term'
    return None
STATES={'APDCL','ASSAM_BEN','BSPHCL','CSEB_BENEFICIARY','HARYANA','JBVNL','ODISHA','PONDY','UPPCL','WBSEDCL','PSPCL','PUNJAB','DHARNI'}
def group(seller, stype, sub, fuel):
    s=seller.upper()
    if stype.startswith(('IEX','RTM','GDAM')) or s=='PXL_TD': return 'Exchange'
    if s in STATES: return 'Swap / banking with other states'
    if stype=='REMC' or sub=='GRTM_HPX' or fuel: return 'Renewable contracts'
    if stype=='CENTRE' and sub in ('ISGS','URS'): return 'Central stations (NTPC, NPCIL, CGPL...)'
    if stype=='CENTRE': return 'Inter-state IPPs (short/medium term)'
    if stype=='INTRASTATE LTA': return 'In-state IPPs, long term (Tiroda, SWPGL, Uran)'
    if stype in ('INTRASTATE MTOA','INTRASTATE STOA'): return 'In-state IPPs, medium/short term'
    if re.match(r'(BHUSAWAL|CHANDRAPUR|KHAPERKHEDA|KORADI|NASHIK|PARAS|PARLI)_',s): return 'MSPGCL thermal'
    if re.search(r'KOYNA|GHATGHAR|KDPH|TILLARI|VAITARNA|BHIRA',s): return 'Hydro'
    if s.startswith('URAN'): return 'MSPGCL gas (Uran)'
    if s.startswith(('RIPL','JSWEL')): return 'In-state IPPs, long term (RattanIndia, JSW)'
    return 'Small RE / co-gen / other'
# exchange: price each block
blk=collections.defaultdict(dict)
for r in csv.DictReader(open(MH/'msldc/sched_msedcl_summary_blocks_mw.csv')): blk[(r['date'],int(r['block_15min']))][r['series']]=float(r['mw'] or 0)
days,dp=store.block_matrix('dam','mcp',date(2026,9,11),date(2026,10,26)); _,rp=store.block_matrix('rtm','mcp',date(2026,9,11),date(2026,10,26)); _,gp=store.block_matrix('gdam','mcp',date(2026,9,11),date(2026,10,26))
di={d:i for i,d in enumerate(days)}
exch=collections.defaultdict(lambda:[0.0,0.0])   # (date, market) -> [MWh, Rs]
for (d,b),s in blk.items():
    i=di.get(d)
    if i is None: continue
    for mk,keys,px in (('DAM',('IEXTotal','PXITotal','HPXTotal'),dp),('RTM',('RTM_IEXTotal','RTM_PXITotal','RTM_HPXTotal'),rp),('G-DAM',('GDAM_IEXTotal','GDAM_PXITotal','GDAM_HPXTotal'),gp)):
        q=sum(s.get(k,0) for k in keys)/4; p=px[i][b-1]
        if q and np.isfinite(p): exch[(d,mk)][0]+=q; exch[(d,mk)][1]+=q*p
dc=collections.defaultdict(float)
for r in csv.DictReader(open(MH/'msldc/sched_msedcl_declared_capability_daily.csv')): dc[(r['date'],r['seller_acr'])]=float(r['dc_energy_mu'] or 0)
rows=[]
for r in csv.DictReader(open(MH/'msldc/sched_msedcl_by_source_daily_mu.csv')):
    if r['seller_acr']=='MSEDCL' or not (r['buyer_acr']=='MSEDCL' or r['buyer_parent']=='MSEDCL'): continue
    d=r['date']; sel=r['seller_acr']; st=r['schedule_type']; sub=r['sub_type']; fu=r['fuel']; mu=float(r['energy_mu'] or 0)
    g=group(sel,st,sub,fu); src=merc(sel,st,sub,fu) if g not in ('Exchange','Swap / banking with other states') else None
    vc=VC.get((d[:7],src)) if src else None
    assumed=''
    if vc is None and g=='Inter-state IPPs (short/medium term)' and sel.upper()!='KAMENG':
        vc=VC.get((d[:7],'Short term')); assumed='MERC approved short-term rate (assumed; deal prices not published)'
    rows.append(dict(date=d,seller=sel,group=g,contract=f"{st}{'/'+sub if sub else ''}{'/'+fu if fu else ''}",merc_source=src or '',mu=mu,
                     energy_charge_rs_kwh=vc,cost_rs_cr=None if vc is None else mu*vc/10,price_basis=assumed or ('MERC FY27 approved energy charge' if vc is not None else 'not priced')))
# replace exchange rows with block-priced figures
rows=[r for r in rows if r['group']!='Exchange']
for (d,mk),(q,rs) in exch.items():
    rows.append(dict(date=d,seller=f'Exchange {mk}',group='Exchange',contract=mk,merc_source='',mu=q/1e3,energy_charge_rs_kwh=rs/q/1e3 if q else None,cost_rs_cr=rs/1e7,price_basis='actual exchange clearing price by block'))
# selling side (swap deliveries / exchange sales)
sales=collections.defaultdict(float)
for r in csv.DictReader(open(MH/'msldc/sched_msedcl_by_source_daily_mu.csv')):
    if r['seller_acr']=='MSEDCL': sales[(r['date'],r['buyer_acr'],r['schedule_type'])]+=float(r['energy_mu'] or 0)
with open(OUT/'msedcl_ledger_daily_by_seller.csv','w') as fh:
    w=csv.DictWriter(fh,fieldnames=['date','seller','group','contract','merc_source','mu','energy_charge_rs_kwh','cost_rs_cr','price_basis','declared_capability_mu','undrawn_mu']); w.writeheader()
    for r in sorted(rows,key=lambda r:(r['date'],r['group'],r['seller'])):
        cap=dc.get((r['date'],r['seller']))
        r['declared_capability_mu']=None if cap is None else round(cap,4); r['undrawn_mu']=None if cap is None else round(cap-r['mu'],4)
        for k in ('mu','energy_charge_rs_kwh','cost_rs_cr'):
            if r[k] is not None: r[k]=round(r[k],4)
        w.writerow(r)
with open(OUT/'msedcl_sales_daily.csv','w') as fh:
    w=csv.writer(fh); w.writerow(['date','buyer','schedule_type','mu'])
    for (d,b,t),v in sorted(sales.items()): w.writerow([d,b,t,round(v,4)])
print('rows',len(rows))
