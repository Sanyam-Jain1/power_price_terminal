import sys, os, json
sys.path.insert(0, os.path.dirname(__file__)); import sldc
raw = sys.argv[1]
def L(t): return json.load(open(os.path.join(raw, 'listings', t + '.json')))
jobs = []
for r in L('system-operations-weekly-reports'):
    if r['year'] == '2026' and int(r['month']) >= 4: jobs.append(('weekly', r['attachment_url']))
for r in L('system-operations-monthly-report'):
    if r['year'] == '2026' and int(r['month']) >= 3: jobs.append(('monthly/%s-%02d_%s' % (r['year'], int(r['month']), r['type'].replace(' ', '_')), r['attachment_url']))
for r in L('marketing-operations-dsm-bills-and-reports'):
    if 'FY2026-27' in r['attachment_url'] or 'No_52_FY2025' in r['attachment_url']: jobs.append(('dsm_bills', r['attachment_url']))
for t in ('net-deviation-and-ancillary-services-statement', 'dsm-pool-account', 'details-of-rsdzero-schedule'):
    for r in L(t): jobs.append((t, r['attachment_url']))
for r in L('scheduling-monthly-mod-stack-annexue1'):
    if r['year'] == '2026' and int(r['month']) >= 4: jobs.append(('mod_stack', r['attachment_url']))
for u in ['https://mahasldc.in/assets/public-ui/files/Maharashtra_State_Aggregated_Shortfall_Study_Report_2026-31.pdf',
          'https://mahasldc.in/assets/public-ui/files/Maharashtra_State_Aggregated_Shortfall_Study_Report_2025-30.pdf',
          'https://mahasldc.in/assets/public-ui/files/Annual_Report.pdf',
          'https://mahasldc.in/assets/public/scada/DSM.pdf', 'https://mahasldc.in/assets/public/scada/report2.jpg',
          'https://mahasldc.in/assets/public/scada/mvrreport3.jpg', 'https://mahasldc.in/assets/public/scada/mvrreport5.jpg',
          'https://mahasldc.in/assets/public/scada/mvrreport7.jpg', 'https://mahasldc.in/assets/public/scada/mvrreport8.jpg',
          'https://mahasldc.in/assets/public/scada/mvrreport9.jpg']:
    jobs.append(('misc', u))
for folder, u in jobs:
    d = os.path.join(raw, 'docs', os.path.dirname(folder) if '/' in folder else folder); os.makedirs(d, exist_ok=True)
    name = (os.path.basename(folder) + '__' if '/' in folder else '') + u.split('/')[-1]
    print(folder, name, sldc.download(u, os.path.join(d, name), delay=1.0), flush=True)
