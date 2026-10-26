"""Parse MSLDC weekly intra-state DSM settlement invoice PDFs.
Usage: python3 -I parse_dsm.py <dsm_pdf_dir> <out_dir>"""
import csv, glob, os, re, subprocess, sys, datetime
src, out = sys.argv[1], sys.argv[2]
INT = r'\(?-?\d+\)?'
issues = []
wk_rows, day_rows, per_rows = [], [], []


def val(x):
    x = x.strip()
    neg = x.startswith('(') and x.endswith(')')
    v = int(x.strip('()'))
    return -v if neg else v


for p in sorted(glob.glob(os.path.join(src, '*.pdf'))):
    fn = os.path.basename(p)
    t = subprocess.run(['pdftotext', '-layout', p, '-'], capture_output=True, text=True).stdout
    m = re.search(r'WEEK FROM (\d{2}-[A-Z]{3}-\d{4}) TO (\d{2}-[A-Z]{3}-\d{4})', t)
    if not m:
        issues.append(f'{fn}: no week period'); continue
    w0 = datetime.datetime.strptime(m.group(1).title(), '%d-%b-%Y').date().isoformat()
    w1 = datetime.datetime.strptime(m.group(2).title(), '%d-%b-%Y').date().isoformat()
    lines = t.split('\n')
    sec = None; entity = None; role = None
    for l in lines:
        if 'Details of DSM Charges for the State Entities' in l:
            sec = 'entities'; continue
        if 'DETAILS OF DSM CHARGES AT STATE PERIPHERY' in l:
            sec = 'periphery'; continue
        if 'DETAILS OF DSM CHARGES OF BUYERS' in l:
            sec = 'buyers_daily'; entity = None; continue
        if 'DETAILS OF WEEKLY DSM CHARGES OF SELLERS' in l:
            sec = 'sellers_weekly'; continue
        if 'DETAILS OF DSM CHARGES OF SELLERS' in l:
            sec = 'sellers_daily'; entity = None; continue
        if sec == 'entities':
            if l.strip() == 'Buyers': role = 'buyer'
            if l.strip() == 'Sellers': role = 'seller'
            mm = re.match(r'^\s*(\d+)\s+(.+?)\s+(' + INT + r')\s+(' + INT + r')\s+(' + INT + r')\s+(' + INT + r')\s+(' + INT + r')\s+(' + INT + r')\s+(' + INT + r')\s+(' + INT + r')\s+(' + INT + r')\s*$', l)
            if mm:
                g = mm.groups()
                wk_rows.append((fn, w0, w1, role, g[1].strip(), *[val(x) for x in g[2:]]))
        if sec == 'periphery':
            mm = re.match(r'^\s*\d+\s+(\d{2}-[A-Z]{3}-\d{4})\s+((?:' + INT + r'\s+){8}' + INT + r')\s*$', l)
            if mm:
                d = datetime.datetime.strptime(mm.group(1).title(), '%d-%b-%Y').date().isoformat()
                per_rows.append((fn, d, *[val(x) for x in mm.group(2).split()]))
        if sec == 'buyers_daily':
            mm = re.match(r'^\s*\d+\s+(.+?)\s+(\d{2}-[A-Z]{3}-\d{4})\s+((?:' + INT + r'\s+){7}' + INT + r')\s*$', l)
            if mm:
                nm = mm.group(1).strip()
                if nm != '-':
                    entity = nm
                d = datetime.datetime.strptime(mm.group(2).title(), '%d-%b-%Y').date().isoformat()
                v = [val(x) for x in mm.group(3).split()]
                day_rows.append((fn, 'buyer' if sec == 'buyers_daily' else 'seller', entity, d, *v))
    print(fn, w0, w1, 'entities', len(wk_rows), 'daily', len(day_rows), 'periphery', len(per_rows))


def w(name, header, rows):
    with open(os.path.join(out, name), 'w', newline='') as fh:
        c = csv.writer(fh); c.writerow(header); c.writerows(rows)
    print(name, len(rows))


w('dsm_weekly_entity_charges_rs.csv', ['source_file', 'week_start', 'week_end', 'role', 'entity', 'dsm_payable_a_rs', 'dsm_receivable_b_rs',
                                        'addl_dsm_payable_d_rs', 'sign_violation_e_rs', 'total_f_rs', 'arrear_g_rs', 'arrear_lps_h_rs',
                                        'current_lps_i_rs', 'net_payable_j_rs'], wk_rows)
w('dsm_daily_entity_deviation.csv', ['source_file', 'role', 'entity', 'date', 'schedule_kwh', 'actual_kwh', 'deviation_kwh',
                                     'dsm_payable_rs', 'dsm_receivable_rs', 'addl_dsm_payable_rs', 'sign_violation_rs', 'net_payable_rs'], day_rows)
w('dsm_daily_state_periphery.csv', ['source_file', 'date', 'schedule_kwh', 'actual_drawl_kwh', 'deviation_kwh', 'dsm_payable_a_rs',
                                    'dsm_receivable_b_rs', 'capping_c_rs', 'addl_d_rs', 'sign_violation_e_rs', 'net_f_rs'], per_rows)
open(os.path.join(out, '_parse_issues_dsm.txt'), 'w').write('\n'.join(issues))
print('issues', len(issues), issues[:5])
