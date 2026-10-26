"""Parse monthly 'System Performance Report' PDFs (daily table) and monthly 'Generation report' PDFs.
Usage: python3 -I parse_monthly.py <docs_dir> <out_dir>"""
import csv, glob, os, re, subprocess, sys, datetime
docs, out = sys.argv[1], sys.argv[2]
NUM = r'-?\d+(?:\.\d+)?'
COLS = ['MSEDCL_max_demand_MW', 'MSEDCL_LS_at_max_MW', 'MSEDCL_min_demand_MW', 'MSEDCL_LS_at_min_MW',
        'Mumbai_max_demand_MW', 'Mumbai_min_demand_MW',
        'State_max_demand_MW', 'State_LS_at_max_MW', 'State_min_demand_MW', 'State_LS_at_min_MW',
        'MSPGCL_thermal_MU', 'MSPGCL_hydro_MU', 'MSPGCL_gas_MU', 'Wind_MU', 'Solar_MU',
        'Central_sector_incl_UI_MU', 'UI_deviation_MU', 'TPCL_exchange_MU',
        'MSEDCL_requirement_MU', 'Mumbai_requirement_MU', 'Other_discom_requirement_MU', 'State_requirement_MU',
        'Load_shedding_MU', 'Avg_frequency_Hz', 'Koyna_water_TMC']
issues = []


def text(p):
    return subprocess.run(['pdftotext', '-layout', p, '-'], capture_output=True, text=True).stdout


rows = []
for p in sorted(glob.glob(os.path.join(docs, 'monthly', '*System_Performance*.pdf'))):
    t = text(p)
    n = 0
    for l in t.split('\n'):
        m = re.match(r'^\s*(\d{2}/\d{2}/\d{4})\s+(.*)$', l)
        if not m:
            continue
        v = re.findall(NUM, m.group(2))
        d = datetime.datetime.strptime(m.group(1), '%d/%m/%Y').date().isoformat()
        if len(v) != len(COLS):
            issues.append(f'{os.path.basename(p)} {d}: {len(v)} values'); continue
        for c, x in zip(COLS, v):
            rows.append((d, c, float(x), os.path.basename(p)))
        n += 1
    print(os.path.basename(p), n, 'days')
with open(os.path.join(out, 'monthly_perf_daily_summary.csv'), 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['date', 'metric', 'value', 'source_file']); w.writerows(rows)
print('perf rows', len(rows))

# --------- Monthly generation report: station/unit monthly MU, max MW, auxiliary consumption MU
gen = []
for p in sorted(glob.glob(os.path.join(docs, 'monthly', '*Generation_report*.pdf'))):
    month = os.path.basename(p)[:7]
    t = subprocess.run(['pdftotext', '-layout', '-f', '1', '-l', '1', p, '-'], capture_output=True, text=True).stdout
    lines = t.split('\n')
    # split two column blocks at the first letter appearing at col >= 60
    left, right = [], []
    for l in lines:
        mm = re.search(r'(?<=\s)[A-Za-z]', l[60:])
        sp = 60 + mm.start() if mm else len(l)
        left.append(l[:sp]); right.append(l[sp:])
    station = None
    for part in left + right:
        s = part.strip()
        if not s or 'Page' in s or 'MAHARASHTRA STATE' in s or 'Office of' in s or 'Thane-Belapur' in s or 'To :' in s:
            continue
        m = re.match(r'^(.*?[A-Za-z)\]].*?)\s+(' + NUM + r')(?:\s+(' + NUM + r'))?(?:\s+(' + NUM + r'))?\s*$', s)
        if m and not re.match(r'^(Power Station|Monthly Gen|\(Mus\)|consumption|Auxilary)', s):
            name = m.group(1).strip()
            if re.search(r'\s{3,}\d', name) or 'Central Sector' in name:
                issues.append(f'{month}: generation report p1 ambiguous row skipped: {s}'); continue
            vals = [float(x) if x is not None else '' for x in m.groups()[1:]]
            gen.append((month, station, name, *vals))
        elif not re.search(r'\d', s) and len(s) < 60 and not re.match(r'^(Power Station|Monthly|consumption|Auxilary|\(Mus\)|Max Gen)', s):
            station = s
with open(os.path.join(out, 'monthly_generation_report_raw.csv'), 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['month', 'station_header', 'unit_or_item', 'monthly_gen_mu', 'max_gen_mw', 'aux_consumption_mu'])
    w.writerows(gen)
print('gen rows', len(gen))
open(os.path.join(out, '_parse_issues_monthly.txt'), 'w').write('\n'.join(issues))
print('issues', issues[:10])

# --------- page 2 monthly balance (targeted labels, in order)
P2 = [('Total Thermal Generation', 'State generation', 'Thermal'), ('Total Hydro Generation', 'State generation', 'Hydro'),
      ('Total Gas Generation', 'State generation', 'Gas'), ('Total Solar Generation', 'State generation', 'Solar'),
      ('Total Wind Generation', 'State generation', 'Wind'), (r'Total State (?:\(InSTS\) )?Generation', 'State generation', 'Total'),
      ('GEB', 'Interstate exchange (actual)', 'Gujarat'), ('MPEB', 'Interstate exchange (actual)', 'Madhya Pradesh'),
      ('CHATTISGARH', 'Interstate exchange (actual)', 'Chhattisgarh'), ('GOA', 'Interstate exchange (actual)', 'Goa'),
      ('MAHARASHTRA NET', 'Interstate exchange (actual)', 'Maharashtra net (ISTS points in MH)'),
      ('Net Inter State Exchanges', 'Interstate exchange (actual)', 'Net total'),
      (r'Restricted Energy Requirement\(Gross\)', 'Requirement', 'Restricted energy requirement (gross)'),
      (r'Restricted Energy Requirement\(Ex-Bus\)', 'Requirement', 'Restricted energy requirement (ex-bus)'),
      ('IMPORT', 'Bilateral purchases - MSEDCL + other discoms', 'Interstate import'),
      ('EXPORT', 'Bilateral purchases - MSEDCL + other discoms', 'Interstate export'),
      (r'PX / IEX / REMC/STANDBY/RTM', 'Bilateral purchases - MSEDCL + other discoms', 'PX/IEX/REMC/Standby/RTM'),
      ('INTRA', 'Bilateral purchases - MSEDCL + other discoms', 'Intra-state'),
      (r'Total Bilateral Purchase by MSEDCL\+Other Discoms', 'Bilateral purchases - MSEDCL + other discoms', 'Total'),
      ('IMPORT', 'Bilateral purchases - Mumbai', 'Interstate import'), ('EXPORT', 'Bilateral purchases - Mumbai', 'Interstate export'),
      ('STANDBY FROM MSEDCL', 'Bilateral purchases - Mumbai', 'Standby from MSEDCL'),
      (r'PX / IEX / REMC/RTM', 'Bilateral purchases - Mumbai', 'PX/IEX/REMC/RTM'), ('INTRA', 'Bilateral purchases - Mumbai', 'Intra-state'),
      ('Total Bilateral Purchase by Mumbai', 'Bilateral purchases - Mumbai', 'Total'),
      ('Total Auxiliary Consumption', 'Auxiliary consumption', 'Total'), ('MSPGCL Total', 'Auxiliary consumption', 'MSPGCL total'),
      ('Thermal', 'Auxiliary consumption', 'MSPGCL thermal'), ('Hydro', 'Auxiliary consumption', 'MSPGCL hydro'), ('Gas', 'Auxiliary consumption', 'MSPGCL gas'),
      ('TPCL Total', 'Auxiliary consumption', 'TPCL total'), ('Thermal', 'Auxiliary consumption', 'TPCL thermal'),
      ('Hydro', 'Auxiliary consumption', 'TPCL hydro'), ('Gas', 'Auxiliary consumption', 'TPCL gas'), ('AEML Dahanu', 'Auxiliary consumption', 'AEML Dahanu')]
bal = []
for p in sorted(glob.glob(os.path.join(docs, 'monthly', '*Generation_report*.pdf'))):
    month = os.path.basename(p)[:7]
    t = subprocess.run(['pdftotext', '-layout', '-f', '2', '-l', '2', p, '-'], capture_output=True, text=True).stdout
    k = 0
    for l in t.split('\n'):
        if k >= len(P2): break
        lab, grp, item = P2[k]
        m = re.match(r'^\s*' + lab + r'\s+(' + NUM + r')\s*$', l)
        if m:
            bal.append((month, grp, item, float(m.group(1)))); k += 1
    if k != len(P2):
        issues.append(f'{month}: generation report p2 matched {k}/{len(P2)} labels (stopped at {P2[k][0] if k < len(P2) else ""})')
    print(month, 'p2 items', k)
with open(os.path.join(out, 'monthly_energy_balance_mu.csv'), 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['month', 'group', 'item', 'mu']); w.writerows(bal)
open(os.path.join(out, '_parse_issues_monthly.txt'), 'w').write('\n'.join(issues))
print(issues)
