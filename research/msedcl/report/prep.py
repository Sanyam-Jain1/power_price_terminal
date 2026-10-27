"""Build the report's datasets from research/msedcl (and Dhruva's IEX store)."""
import csv, gzip, sys, collections, json
from datetime import date
from pathlib import Path
import numpy as np
from dhruva import store
R=Path(sys.argv[1]); O=Path(sys.argv[2]); O.mkdir(parents=True, exist_ok=True)
def w(name, cols, rows):
    with open(O/f'{name}.csv','w',newline='') as fh:
        wr=csv.writer(fh); wr.writerow(cols)
        for r in rows: wr.writerow(['' if v is None else (round(v,3) if isinstance(v,float) else v) for v in r])
    print(name, len(rows))
MON={'2026-04':'Apr','2026-05':'May','2026-06':'Jun','2026-07':'Jul','2026-08':'Aug','2026-09':'Sep','2026-10':'Oct'}
# ---------- hourly SLDC series -> daily & monthly mix
H=collections.defaultdict(lambda: collections.defaultdict(float)); FMIN={}
for r in csv.DictReader(gzip.open(R/'msldc/hourly_load_mw.csv.gz','rt')):
    v=float(r['value'] or 0)
    if r['series']=='frequency_Hz':
        FMIN[r['date']]=min(FMIN.get(r['date'],99),v) if v>0 else FMIN.get(r['date'],99)
    else: H[r['date']][r['series']]+=v/1000     # MW for one hour -> MU
days=sorted(d for d in H if '2026-04-01'<=d<='2026-10-20')
mix_items=[('MSPGCL thermal','MSPGCL_thermal',1),('MSPGCL hydro','MSPGCL_hydro',1),('MSPGCL gas','MSPGCL_gas',1),('Private & captive plants in Maharashtra','CPP_IPP_thermal',1),
           ('Private & captive plants in Maharashtra','CPP_IPP_gas',1),('Wind','wind',1),('Solar','solar',1),('Central share & inter-state (net receipt)','CS_net_receipt_actual',1),
           ('Supplied to Mumbai utilities (net)','Mumbai_net_exchange',1),('Other licensees in the state','Other_discom_demand',-1)]
mm=collections.defaultdict(float); chk=[]
for d in days:
    s=H[d]; tot=0
    for lab,k,sg in mix_items: mm[(d[:7],lab)]+=sg*s[k]; tot+=sg*s[k]
    chk.append(abs(tot-s['MSEDCL_demand_met']))
print('identity max abs diff MU/day', round(max(chk),2))
order=[l for l,_,_ in mix_items]; order=list(dict.fromkeys(order))
w('monthly_mix',['month','month_label','source','mu','days'],[(m,MON[m],lab,mm[(m,lab)],sum(1 for d in days if d[:7]==m)) for m in MON for lab in order])
# daily table
mx={}
for r in csv.DictReader(open(R/'msldc/daily_max_demand_mw.csv')):
    if r['entity'].startswith('MSEDCL'): mx[r['date']]=float(r['max_demand_mw'])
out=collections.defaultdict(lambda: collections.defaultdict(float))
for r in csv.DictReader(open(R/'msldc/daily_outage_capacity_mw.csv')):
    if r['company']=='ALL': out[r['date']][r['category']]=float(r['capacity_mw'] or 0)
rows=[]
for d in days:
    s=H[d]; o=out[d]
    rows.append((d,s['MSEDCL_demand_met'],s['LS_planned'],s['LS_transmission_constraint'],mx.get(d),FMIN.get(d),
                 o['FORCED OUTAGE']+o['FORCED OUTAGE DUE TO NO PPA'],o['OUTAGE DUE TO FUEL SHORTAGE'],o['UNIT UNDER ZERO SCHEDULE / RSD'],o['PLANNED OUTAGE'],s['CS_net_receipt_actual'],s['CS_share_schedule']))
w('daily',['date','demand_met_mu','load_shed_shortfall_mu','load_shed_transmission_mu','peak_mw','min_freq_hz','forced_outage_mw','fuel_shortage_outage_mw','reserve_shutdown_mw','planned_outage_mw','interstate_actual_mu','interstate_schedule_mu'],rows)
# load-shedding events (shortfall), from the hourly planned series
ev=[]
HH=collections.defaultdict(dict)
for r in csv.DictReader(gzip.open(R/'msldc/hourly_load_mw.csv.gz','rt')):
    if r['series']=='LS_planned': HH[r['date']][int(r['hour_ending'])]=float(r['value'] or 0)
for d in days:
    hs=HH.get(d,{}); tot=sum(hs.values())/1000
    if tot>0:
        h=max(hs,key=hs.get); n=sum(1 for v in hs.values() if v>0)
        ev.append((d,tot,hs[h],f'{h-1:02d}:00–{h:02d}:00',n))
w('load_shedding_events',['date','mu','peak_mw','peak_hour','hours_with_cuts'],ev)
# ---------- ledger (45 days)
L=list(csv.DictReader(open(R/'ledger/msedcl_ledger_daily_by_seller.csv')))
ld=sorted({r['date'] for r in L}); n=len(ld)
g=collections.defaultdict(lambda:[0.0,0.0,0.0,0.0,set()])
s=collections.defaultdict(lambda:[0.0,0.0,0.0,0.0,0.0,'','','',''])
for r in L:
    mu=float(r['mu']); c=float(r['cost_rs_cr']) if r['cost_rs_cr'] else None
    a=g[r['group']]; a[0]+=mu
    if c is not None: a[1]+=c; a[2]+=mu
    a[4].add(r['price_basis'])
    if r['undrawn_mu']: a[3]+=max(float(r['undrawn_mu']),0)
    b=s[r['seller']]; b[0]+=mu
    if c is not None: b[1]+=c; b[2]+=mu
    if r['declared_capability_mu']: b[3]+=float(r['declared_capability_mu']); b[4]+=max(float(r['undrawn_mu'] or 0),0)
    b[5]=r['group']; b[6]=r['contract'] if not b[6] else b[6]; b[7]=r['merc_source']; b[8]=r['price_basis']
T=sum(a[0] for a in g.values())
w('ledger_groups',['group','mu_total','mu_per_day','share','priced_mu','cost_rs_cr','avg_rs_kwh','undrawn_capacity_mu_per_day','price_basis'],
  [(k,a[0],a[0]/n,a[0]/T,a[2],a[1] if a[2] else None,a[1]/a[2]*10 if a[2] else None,a[3]/n,'; '.join(sorted(x for x in a[4] if x))) for k,a in sorted(g.items(),key=lambda x:-x[1][0])])
w('ledger_sellers',['seller','group','contract','merc_source','mu_total','mu_per_day','avg_rs_kwh','cost_rs_cr','price_basis','declared_capability_mu','undrawn_mu'],
  [(k,b[5],b[6],b[7],b[0],b[0]/n,b[1]/b[2]*10 if b[2] else None,b[1] if b[2] else None,b[8],b[3] or None,b[4] if b[3] else None) for k,b in sorted(s.items(),key=lambda x:-x[1][0]) if b[0]>0.05])
# swaps
sw=collections.defaultdict(lambda:[0.0,0.0])
for r in L:
    if r['group']=='Swap / banking with other states': sw[r['seller']][0]+=float(r['mu'])
for r in csv.DictReader(open(R/'ledger/msedcl_sales_daily.csv')): sw[r['buyer']][1]+=float(r['mu'])
w('swaps',['partner','received_mu','delivered_mu'],[(k,v[0],v[1]) for k,v in sorted(sw.items(),key=lambda x:-(x[1][0]+x[1][1]))])
# ---------- hourly stack (45 days) with DAM price by hour
B=collections.defaultdict(lambda: collections.defaultdict(float)); N=collections.Counter()
for r in csv.DictReader(gzip.open(R/'msldc/sched_msedcl_summary_blocks_mw.csv.gz','rt')):
    h=(int(r['block_15min'])-1)//4; B[h][r['series']]+=float(r['mw'] or 0)
    if r['series']=='Demand': N[h]+=1
a,b=date.fromisoformat(ld[0]),date.fromisoformat(ld[-1])
ds,dp=store.block_matrix('dam','mcp',a,date.fromordinal(b.toordinal()+1))
hp=[[] for _ in range(24)]
for i in range(len(ds)):
    for j in range(96):
        if np.isfinite(dp[i][j]): hp[j//4].append(dp[i][j])
cols=['hour','central_mw','instate_generation_mw','long_term_ipp_mw','medium_term_mw','short_term_mw','renewables_mw','exchange_dam_mw','exchange_rtm_mw','exchange_gdam_mw','scheduled_demand_mw','forecast_demand_mw','unscheduled_gap_mw','dam_avg_price_rs_mwh','dam_cap_share']
keys=['CentreTotal','IntraStateGenerationTotal','IntraStateLTOATotal','IntraStateMTOATotal','IntraStateSTOATotal','REMCTotal']
rows=[]
for h in range(24):
    k=N[h]; v=[B[h][x]/k for x in keys]
    dam=(B[h]['IEXTotal']+B[h]['PXITotal']+B[h]['HPXTotal'])/k; rtm=(B[h]['RTM_IEXTotal']+B[h]['RTM_PXITotal']+B[h]['RTM_HPXTotal'])/k; gd=(B[h]['GDAM_IEXTotal']+B[h]['GDAM_PXITotal']+B[h]['GDAM_HPXTotal'])/k
    dem=B[h]['Demand']/k; fc=B[h]['ForecastedDemand']/k
    rows.append((f'{h:02d}:00',*v,dam,rtm,gd,dem,fc,fc-dem,float(np.mean(hp[h])),float(np.mean(np.array(hp[h])>=9999.5))))
w('hourly_stack',cols,rows)
# ---------- exchange daily (block-priced)
ex=collections.defaultdict(lambda: collections.defaultdict(float))
for r in L:
    if r['group']=='Exchange':
        ex[r['date']][r['contract']]+=float(r['mu']); ex[r['date']]['rs']+=float(r['cost_rs_cr'])
w('exchange_daily',['date','dam_mu','rtm_mu','gdam_mu','total_mu','spend_rs_cr','avg_rs_kwh'],
  [(d,e['DAM'],e['RTM'],e['G-DAM'],e['DAM']+e['RTM']+e['G-DAM'],e['rs'],e['rs']/(e['DAM']+e['RTM']+e['G-DAM'])*10 if (e['DAM']+e['RTM']+e['G-DAM']) else None) for d,e in sorted(ex.items())])
# exchange history from MSEDCL disclosures
w('exchange_history',['month','mu','avg_rs_kwh','cost_rs_cr','max_daily_rate','min_daily_rate'],
  [(r['month'],float(r['mu_total_printed']),float(r['avg_rate_printed_rs_kwh']),float(r['implied_cost_rs_cr']),float(r['max_daily_rate'] or 0),float(r['min_daily_rate'] or 0)) for r in csv.DictReader(open(R/'msedcl_merc/msedcl_exchange_purchase_monthly.csv'))])
# ---------- merit order: approved energy charge vs what was scheduled
ap=collections.defaultdict(dict)
for r in csv.DictReader(open(R/'msedcl_merc/merc_fy2026_27_approved_monthly_mu_vc_by_source.csv')):
    if r['month'] in ('2026-09','2026-10'): ap[r['source']][r['month']]=(float(r['energy_charge_rs_per_kwh']) if r['energy_charge_rs_per_kwh'] else None, float(r['approved_mu'] or 0), r['merc_group'])
sch=collections.defaultdict(float)
for r in L:
    if r['merc_source']: sch[r['merc_source']]+=float(r['mu'])
rows=[]
for src,m in ap.items():
    vc,mu,grp=m.get('2026-09',(None,0,''))
    apd=(m.get('2026-09',(0,0,''))[1]/30+m.get('2026-10',(0,0,''))[1]/31)/2
    if vc is None or src in ('Total Solar','Short term'): continue
    rows.append((src,grp,vc,apd,sch.get(src,0)/n, (sch.get(src,0)/n)/apd if apd else None))
rows.sort(key=lambda r:r[2])
w('merit_order',['source','merc_group','energy_charge_rs_kwh','approved_mu_per_day','scheduled_mu_per_day','scheduled_vs_approved'],rows)
# ---------- central stations by month (WRPC)
cs=collections.defaultdict(float)
for r in csv.DictReader(open(R/'wrpc/mh_isgs_daily.csv')):
    if r['beneficiary']=='MSEB_Beneficiary' and r['date']>='2026-04-06': cs[(r['date'][:7],r['source'])]+=float(r['scheduled_mwh'])/1000
st=sorted({k[1] for k in cs}, key=lambda x:-sum(v for (m,s2),v in cs.items() if s2==x))
w('central_monthly',['month','month_label','station','mu'],[(m,MON[m],x,cs.get((m,x),0.0)) for m in MON for x in st if sum(v for (mm2,s2),v in cs.items() if s2==x)>1])
# ---------- DSM monthly, state level (WRPC blocks)
D=collections.defaultdict(lambda: collections.defaultdict(float))
for r in csv.DictReader(gzip.open(R/'wrpc/mh_blocks.csv.gz','rt')):
    m=r['date'][:7]; x=D[m]; dev=float(r['deviation_mwh'])
    x['blocks']+=1; x['over']+=max(dev,0); x['under']+=max(-dev,0); x['pay']+=float(r['dsm_payable_rs']); x['rec']+=float(r['dsm_receivable_rs'])
    p=float(r['dam_rs_mwh']) if r['dam_rs_mwh'] not in ('','None','nan') else np.nan
    if p>=9999.5: x['capb']+=1; x['over_cap']+=max(dev,0); x['pay_cap']+=float(r['dsm_payable_rs'])
w('dsm_monthly',['month','month_label','days','overdrawal_gwh','underdrawal_gwh','payable_rs_cr','receivable_rs_cr','net_payable_rs_cr','dam_capped_share','overdrawal_in_capped_blocks_gwh','payable_in_capped_blocks_rs_cr','payable_per_kwh_in_capped_blocks'],
  [(m,MON[m],x['blocks']/96,x['over']/1e3,x['under']/1e3,x['pay']/1e7,x['rec']/1e7,(x['pay']-x['rec'])/1e7,x['capb']/x['blocks'],x['over_cap']/1e3,x['pay_cap']/1e7,x['pay_cap']/x['over_cap']/1e3 if x['over_cap'] else None) for m,x in sorted(D.items())])
# ---------- last year's actuals by category
w('fy26_by_category',['month','category','mu','rs_cr','rs_kwh'],[(r['month'],r['category'],float(r['mu_actual'] or 0),float(r['rs_cr_actual'] or 0),float(r['rs_per_kwh_actual']) if r['rs_per_kwh_actual'] else None) for r in csv.DictReader(open(R/'msedcl_merc/msedcl_monthly_pp_by_category.csv'))])
# ---------- contracted capacity
w('contracted_capacity',['resource','mw_fy2026_27','mw_fy2027_28'],[(r['resource'],float(r['FY2026-27']),float(r['FY2027-28'])) for r in csv.DictReader(open(R/'msedcl_merc/merc_myt_contracted_capacity_by_resource.csv'))])
w('approved_plan',['metric','unit','fy2025_26','fy2026_27'],[(r['metric'],r['unit'],r['FY2025-26'],r['FY2026-27']) for r in csv.DictReader(open(R/'msedcl_merc/merc_myt_control_period_summary.csv'))])
# ---------- headline figures
ls_tot=sum(e[1] for e in ev); ls_max=max(ev,key=lambda e:e[2])
dm=[r for r in csv.DictReader(open(O/'dsm_monthly.csv'))]
G={r['group']:r for r in csv.DictReader(open(O/'ledger_groups.csv'))}
k=[('demand','MSEDCL energy supplied, average per day',float(np.mean([H[d]['MSEDCL_demand_met'] for d in days])),'MU/day','1 Apr – 20 Oct 2026'),
   ('peak','MSEDCL peak demand',max(mx.values()),'MW',max(mx,key=mx.get)),
   ('load_shed','Load shed for supply shortfall',ls_tot,'MU','1 Apr – 20 Oct 2026'),
   ('load_shed_days','Days with shortfall load shedding',float(len(ev)),'days','1 Apr – 20 Oct 2026'),
   ('load_shed_max','Largest single cut',ls_max[2],'MW',ls_max[0]),
   ('ledger_mu','Energy scheduled, average per day',sum(float(r['mu_total']) for r in G.values())/n,'MU/day',f'{ld[0]} – {ld[-1]}'),
   ('ledger_cost','Energy-charge cost of scheduled power',sum(float(r['cost_rs_cr'] or 0) for r in G.values()),'Rs crore',f'{ld[0]} – {ld[-1]}'),
   ('ledger_avg','Average energy charge',sum(float(r['cost_rs_cr'] or 0) for r in G.values())/sum(float(r['priced_mu']) for r in G.values())*10,'Rs/kWh',f'{ld[0]} – {ld[-1]}'),
   ('exch_mu','Bought on power exchanges',float(G['Exchange']['mu_total']),'MU',f'{ld[0]} – {ld[-1]}'),
   ('exch_cost','Spent on power exchanges',float(G['Exchange']['cost_rs_cr']),'Rs crore',f'{ld[0]} – {ld[-1]}'),
   ('exch_avg','Average exchange price paid',float(G['Exchange']['avg_rs_kwh']),'Rs/kWh',f'{ld[0]} – {ld[-1]}'),
   ('dsm_sep','State DSM net payable, September',float([r for r in dm if r['month']=='2026-09'][0]['net_payable_rs_cr']),'Rs crore','Sep 2026, Maharashtra at the inter-state boundary'),
   ('dsm_oct','State DSM net payable, 1–11 October',float([r for r in dm if r['month']=='2026-10'][0]['net_payable_rs_cr']),'Rs crore','1–11 Oct 2026'),
   ('days_n','Days in the seller-level ledger',float(n),'days',f'{ld[0]} – {ld[-1]}'),
   ('evening_gap','Average unscheduled demand, 18:00–20:00',float(np.mean([r[13] for r in rows] and [0])) if False else None,'MW','')]
hs=list(csv.DictReader(open(O/'hourly_stack.csv')))
k[-1]=('evening_gap','Average demand left unscheduled, 18:00–20:00',float(np.mean([float(x['unscheduled_gap_mw']) for x in hs if x['hour'] in ('18:00','19:00')])),'MW',f'{ld[0]} – {ld[-1]}')
w('headline',['metric','label','value','unit','window'],k)
