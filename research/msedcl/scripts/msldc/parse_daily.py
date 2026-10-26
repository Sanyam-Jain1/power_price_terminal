"""Parse MSLDC 'Daily system Report' PDFs (pdftotext -layout output) into tidy CSVs.

Usage: python3 -I parse_daily.py <daily_txt_dir> <out_dir>
Treats input as untrusted text; only regex parsing.
"""
import csv, datetime, glob, os, re, sys

NUM = r'-?\d+(?:\.\d+)?'
txt_dir, out_dir = sys.argv[1], sys.argv[2]
issues = []


def nums(s):
    return [float(x) for x in re.findall(r'(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])', s)]


# ---------------------------------------------------------------- Statement I
LEFT_ITEMS = [  # (regex on left part, section, item)
    (r'^\s*1\) Thermal', 'MSPGCL', 'Thermal'),
    (r'^\s*2\) Hydro\s', 'MSPGCL', 'Hydro'),
    (r'^\s*3\) Gas\s', 'MSPGCL', 'Gas'),
    (r'^\s*Total MSPGCL', 'MSPGCL', 'Total MSPGCL'),
    (r'^\s*B\) 1\) APML', 'IPP', 'APML (Adani Power Maharashtra, Tiroda)'),
    (r'^\s*2\) JSWEL', 'IPP', 'JSWEL (JSW Ratnagiri)'),
    (r'^\s*3\) VIPL', 'IPP', 'VIPL (Vidarbha Industries Power, Butibori)'),
    (r'^\s*4\) RPL\(AMT\)', 'IPP', 'RPL(AMT) (RattanIndia Amravati)'),
    (r'^\s*5\) SWPGPL', 'IPP', 'SWPGPL (Sai Wardha Power)'),
    (r'^\s*6\) Other IPP', 'IPP', 'Other IPP'),
    (r'^\s*7\) PGPL', 'IPP', 'PGPL (gas)'),
    (r'^\s*C\) 1\) TPCL Thermal', 'Mumbai_gen', 'TPCL Thermal'),
    (r'^\s*2\) TPCL Hydro', 'Mumbai_gen', 'TPCL Hydro'),
    (r'^\s*3\) TPCL Gas', 'Mumbai_gen', 'TPCL Gas'),
    (r'^\s*4\) AEML Thermal', 'Mumbai_gen', 'AEML Thermal'),
    (r'^\s*1\) Thermal', 'STATE', 'Thermal (A1+C1+C4+(B1-B6))'),
    (r'^\s*2\) Hydro\s+\(A2\+C2\)', 'STATE', 'Hydro (A2+C2)'),
    (r'^\s*3\) Gas\s+\(A3\+B7\+C3\)', 'STATE', 'Gas (A3+B7+C3)'),
    (r'^\s*4\) Wind', 'STATE', 'Wind'),
    (r'^\s*6\) SOLAR', 'STATE', 'Solar'),
    (r'^\s*TOTAL STATE', 'STATE', 'Total State generation'),
]
RIGHT_ITEMS = [
    (r'1\) Gujrat', 'InterState_actual', 'Gujarat'),
    (r'2\) Madhya Pradesh', 'InterState_actual', 'Madhya Pradesh'),
    (r'3\) Chattisgarh', 'InterState_actual', 'Chhattisgarh'),
    (r'4\) Maharashtra', 'InterState_actual', 'Maharashtra (ISTS points within MH)'),
    (r'5\) Goa \(Amona\)', 'InterState_actual', 'Goa (Amona)'),
    (r'Total(?! STATE)', 'InterState_actual', 'Total net interstate exchange'),
    (r'a\) Mumbai Schedule', 'Mumbai', 'Mumbai Schedule'),
    (r'b\) Mumbai Drawl', 'Mumbai', 'Mumbai Drawl'),
    (r'c\) MSEDCL Bilateral \*', 'Bilateral_info', 'MSEDCL Bilateral'),
    (r'Include PX', 'Bilateral_info', 'MSEDCL Bilateral - of which PX'),
    (r'd\) Mumbai Bilateral \*', 'Bilateral_info', 'Mumbai Bilateral'),
    (r'Include PX', 'Bilateral_info', 'Mumbai Bilateral - of which PX'),
    (r'Standby', 'Bilateral_info', 'Standby'),
    (r'1\) MSEDCL', 'Energy_catered', 'MSEDCL'),
    (r'2\) Mumbai Discoms', 'Energy_catered', 'Mumbai Discoms'),
    (r'3\) Other Discoms', 'Energy_catered', 'Other Discoms'),
    (r'TOTAL STATE', 'Energy_catered', 'Total State'),
]


def parse_statement1(lines, date):
    out = []
    li = ri = 0
    for ln in lines:
        if 'Statement II' in ln or 'DETAILS OF MAHARASHTRA STATE PEAK' in ln:
            break
        # find right label
        right = None
        if ri < len(RIGHT_ITEMS):
            pat = RIGHT_ITEMS[ri][0]
            # right block begins after column ~60
            m = None
            for mm in re.finditer(pat, ln):
                if mm.start() >= 55:
                    m = mm; break
            if m:
                right = ln[m.start():]
                ln_left = ln[:m.start()]
            else:
                ln_left = ln
        else:
            ln_left = ln
        if right is not None:
            rn = nums(right[len(re.match(RIGHT_ITEMS[ri][0], right).group(0)):])
            sec, item = RIGHT_ITEMS[ri][1:]
            if rn:
                out.append((date, 'exchange_or_catered', sec, item, rn[0], rn[1] if len(rn) > 1 else ''))
            else:
                issues.append(f'{date}: Statement I right item {item} has no numbers')
            ri += 1
        if li < len(LEFT_ITEMS) and re.match(LEFT_ITEMS[li][0], ln_left):
            lab = re.match(LEFT_ITEMS[li][0], ln_left).group(0)
            rest = ln_left[len(lab):]
            rest = re.sub(r'\(A\d.*?\)', '', rest)
            ln_nums = nums(rest)
            sec, item = LEFT_ITEMS[li][1:]
            if ln_nums:
                out.append((date, 'generation', sec, item, ln_nums[0], ln_nums[1] if len(ln_nums) > 1 else ''))
            else:
                issues.append(f'{date}: Statement I left item {item} has no numbers')
            li += 1
        elif li < len(LEFT_ITEMS) and LEFT_ITEMS[li][2].startswith('Thermal (A1') and re.match(r'^\s*1\) Thermal', ln_left):
            pass
    if li != len(LEFT_ITEMS) or ri != len(RIGHT_ITEMS):
        issues.append(f'{date}: Statement I matched {li}/{len(LEFT_ITEMS)} left, {ri}/{len(RIGHT_ITEMS)} right items')
    return out


# ---------------------------------------------------------------- Statement II
ST2_ROWS = ['MSPGCL Thermal', 'MSPGCL Hydro', 'MSPGCL Gas', 'MSPGCL Total Generation', 'Central Sector Receipt',
            'WIND', 'CPP / IPP Thermal', 'CPP / IPP Gas', 'SOLAR', 'Exchange with Mumbai', 'MSEDCL DEMAND MET',
            'Load Shedding', 'MSEDCL DEMAND', 'TPCL GENERATION', 'AEML GENERATION', 'MUMBAI DEMAND',
            'OTHER DISCOM DEMAND', 'STATE DEMAND MET', 'STATE DEMAND', 'Frequency (Hz)']
SNAPS = ['morning_peak', 'day_peak', 'evening_peak', 'night_minimum']


def parse_statement2(lines, date):
    out, hours = [], [None] * 4
    s = next(i for i, l in enumerate(lines) if 'DETAILS OF MAHARASHTRA STATE PEAK' in l)
    h1, h2 = lines[s + 1], lines[s + 2]
    m1 = re.search(r'Day Peak at\s*(\d+)?', h1)
    m2 = re.search(r'^\s*(\d+)?\s*Hrs\s+(\d+)?\s*Hrs\s+(\d+)?\s*Hrs\s+at\s*(\d+)\s*Hrs', h2)
    # typical: h1 '... B. Day Peak at 16 C. Evening Peak at ...'; h2 '10 Hrs  Hrs  19 Hrs  at 24 Hrs'
    if m2:
        a, b2, c, d = m2.groups()
        b = m1.group(1) if m1 and m1.group(1) else b2
        hours = [int(x) if x else None for x in (a, b, c, d)]
        if b2 and m1 and m1.group(1):
            issues.append(f'{date}: ambiguous Statement II header hours')
    else:
        issues.append(f'{date}: could not parse Statement II header hours: {h1.strip()} | {h2.strip()}')
    for l in lines[s + 3:s + 40]:
        for r in ST2_ROWS:
            if re.match(r'^\s*' + re.escape(r) + r'\s+' + NUM, l):
                v = nums(l[l.index(r) + len(r):])
                if len(v) == 4:
                    for k in range(4):
                        out.append((date, SNAPS[k], hours[k], r, v[k]))
                else:
                    issues.append(f'{date}: Statement II row {r} has {len(v)} values')
                break
    # frequency particulars
    fq = None
    for i, l in enumerate(lines):
        if 'FREQUENCY PARTICULARS' in l:
            t = lines[i + 2]
            m = re.search(r'(' + NUM + r')\s*Hz at\s*([\d.:]+)\s*Hrs\s+(' + NUM + r')\s*Hz at\s*([\d.:]+)\s*Hrs\s+(' + NUM + r')\s+(' + NUM + r')?\s*%', t)
            if m:
                fq = (date, float(m.group(1)), m.group(2).replace('.', ':'), float(m.group(3)), m.group(4).replace('.', ':'), float(m.group(5)), float(m.group(6)) if m.group(6) else '')
            else:
                issues.append(f'{date}: frequency particulars unparsed: {t.strip()}')
            break
    return out, hours, fq


# ---------------------------------------------------------------- Annexure-1
def parse_annex1(lines, date):
    out = []
    start = next(i for i, l in enumerate(lines) if 'Annexure-1' in l)
    hdr = next(i for i in range(start, start + 8) if lines[i].count('Generating unit') == 2)
    split = lines[hdr].index('Generating unit', lines[hdr].index('Generating unit') + 5)
    left, right = [], []
    i = hdr + 2
    while i < len(lines):
        l = lines[i]
        if 'Summary' in l or 'Infirm Power' in l or 'Annexure-2' in l:
            break
        if re.match(r'^\s+\d+ of \d+\s*$', l) or not l.strip() or 'Annexure-1' in l or 'Generating unit' in l or re.match(r'^\s+\(Mus\)', l) or 'Daily and Progressive' in l or re.match(r'^\s+Generation\s+Generation\s*$', l):
            i += 1; continue
        # choose split at whitespace nearest to header split column
        # right block = first word starting with a letter at/after col 40 (left block names start at col 0,
        # left block values are numeric); the header split column is only a fallback
        mm = re.search(r'(?<=\s)[A-Za-z]', l[40:])
        sp = 40 + mm.start() if mm else max(split, len(l))
        left.append(l[:sp]); right.append(l[sp:])
        i += 1
    station = None
    seen_tot = set()
    for part in left + right:
        p = part.strip()
        if not p:
            continue
        m = re.match(r'^(.*?\S)\s+(' + NUM + r')\s+(' + NUM + r')(?:\s+(' + NUM + r')\s+(' + NUM + r'))?\s*$', p)
        if m and not re.fullmatch(r'[\d.\s-]+', m.group(1)):
            name = m.group(1)
            vals = [float(x) if x is not None else '' for x in m.groups()[1:]]
            if name == 'Total':
                if (station, 'Total') in seen_tot:
                    continue  # duplicated Total line (wind/solar sections)
                seen_tot.add((station, 'Total'))
            out.append((date, station, name, *vals))
        elif re.search(r'\d+\.\d+', p) and not re.match(r'^[A-Za-z]', p):
            issues.append(f'{date}: Annexure-1 orphan numbers "{p}" (station {station})')
        else:
            station = p
    return out


# ---------------------------------------------------------------- Annexure-2 hourly
HCOLS = ['MSPGCL_thermal', 'MSPGCL_hydro', 'MSPGCL_gas', 'MSPGCL_total', 'wind', 'CPP_IPP_thermal', 'CPP_IPP_gas',
         'solar', 'CS_share_schedule', 'CS_net_receipt_actual', 'Mumbai_net_exchange', 'MSEDCL_demand_met',
         'LS_planned', 'LS_transmission_constraint', 'MSEDCL_demand_with_LS', 'Mumbai_demand',
         'Other_discom_demand', 'State_demand', 'frequency_Hz']


def parse_annex2(lines, date):
    out = []
    s = next(i for i, l in enumerate(lines) if 'Annexure-2' in l)
    got = set()
    for l in lines[s:s + 120]:
        if l.strip().startswith('MUs') or 'NOTE : ALL VALUES' in l:
            break
        m = re.match(r'^\s*(\d{1,2})\s+(' + NUM + r'(?:\s+' + NUM + r')+)\s*$', l)
        if m:
            h = int(m.group(1)); v = nums(m.group(2))
            if 1 <= h <= 24 and len(v) == len(HCOLS) and h not in got:
                got.add(h)
                for c, x in zip(HCOLS, v):
                    out.append((date, h, c, x))
            elif 1 <= h <= 24:
                issues.append(f'{date}: hourly row {h} has {len(v)} values (expected {len(HCOLS)})')
    if len(got) != 24:
        issues.append(f'{date}: hourly table has {len(got)} hours')
    # maximum demand scenario
    md = []
    for i, l in enumerate(lines):
        if 'Maximum Demand scenario' in l:
            blk = [x for x in lines[i + 1:i + 12] if x.strip()]
            vals = [x for x in blk if 'MW' in x and 'LS' not in x]
            hrs = [x for x in blk if 'Hrs' in x]
            ls = [x for x in blk if 'Includes LS' in x]
            if vals and hrs:
                mw = [int(x) for x in re.findall(r'(\d+)\s*MW', vals[0])]
                hh = [x for x in re.findall(r'([\d.:]+)\s*Hrs', hrs[0])]
                lsv = re.findall(r'Includes LS\s*-\s*(\d+)\s*MW', ls[0]) if ls else []
                ents = ['State', 'MSEDCL (non-coincident)', 'Mumbai (non-coincident)']
                for k, e in enumerate(ents):
                    if k < len(mw):
                        md.append((date, e, mw[k], hh[k] if k < len(hh) else '', lsv[k] if k < len(lsv) else ''))
                if len(mw) != 3 or len(hh) != 3:
                    issues.append(f'{date}: max demand block parsed {len(mw)} MW / {len(hh)} hours')
            break
    return out, md


# ---------------------------------------------------------------- Statement VI outage totals
CATS = ['PLANNED OUTAGE', 'FORCED OUTAGE DUE TO NO PPA', 'FORCED OUTAGE', 'OUTAGE DUE TO FUEL SHORTAGE',
        'UNIT UNDER ZERO SCHEDULE / RSD', 'UNIT OUT ON TOLLING']


def parse_outages(lines, date):
    out = []; cat = None
    for l in lines:
        st = l.strip()
        if 'Statement-VII' in l:
            break
        for c in CATS:
            if st.startswith(c) and not st.startswith('Total'):
                cat = c; break
        m = re.match(r'^\s*Total Capacity (.+?)\s+(\d+)\s*$', l)
        if m and cat:
            who = m.group(1).strip()
            if any(c.startswith(who) or who.startswith(c[:12]) for c in CATS):
                out.append((date, cat, 'ALL', int(m.group(2))))
            else:
                out.append((date, cat, who, int(m.group(2))))
    return out


def main():
    os.makedirs(out_dir, exist_ok=True)
    S1, S2, FQ, A1, A2, MD, OU, HRS = [], [], [], [], [], [], [], []
    for f in sorted(glob.glob(os.path.join(txt_dir, '*.txt'))):
        date = os.path.basename(f)[:-4]
        lines = open(f, encoding='utf-8', errors='replace').read().split('\n')
        S1 += parse_statement1(lines, date)
        s2, hours, fq = parse_statement2(lines, date)
        S2 += s2; HRS.append((date, hours))
        if fq: FQ.append(fq)
        A1 += parse_annex1(lines, date)
        a2, md = parse_annex2(lines, date)
        A2 += a2; MD += md
        OU += parse_outages(lines, date)

    def w(name, header, rows):
        with open(os.path.join(out_dir, name), 'w', newline='') as fh:
            cw = csv.writer(fh); cw.writerow(header); cw.writerows(rows)
        print(name, len(rows))
    w('daily_energy_balance_mu.csv', ['date', 'block', 'section', 'item', 'daily_mu', 'month_to_date_mu'], S1)
    w('daily_peak_snapshots_mw.csv', ['date', 'snapshot', 'hour', 'item', 'value'], S2)
    w('daily_frequency.csv', ['date', 'max_hz', 'max_time', 'min_hz', 'min_time', 'avg_hz', 'pct_time_below_49_4'], FQ)
    w('daily_unit_generation.csv', ['date', 'station', 'unit', 'daily_mu', 'month_to_date_mu', 'max_mw', 'min_mw'], A1)
    w('hourly_load_mw.csv', ['date', 'hour_ending', 'series', 'value'], A2)
    w('daily_max_demand_mw.csv', ['date', 'entity', 'max_demand_mw', 'at_hrs', 'includes_load_shedding_mw'], MD)
    w('daily_outage_capacity_mw.csv', ['date', 'category', 'company', 'capacity_mw'], OU)
    with open(os.path.join(out_dir, '_parse_issues_daily.txt'), 'w') as fh:
        fh.write('\n'.join(issues))
    print('issues', len(issues))


main()
