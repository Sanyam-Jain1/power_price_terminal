"""Parse OCR boxes of MSEDCL 'Monthly Power Purchase for <Mon-YY>' (standalone) scans
into a tidy CSV, and check component rows against the printed subtotals.

Usage: python3 -I parse_ppcost.py OCR_DIR OUT_CSV CHECK_TXT
"""
import csv
import glob
import json
import os
import re
import sys

ocr_dir, out_csv, check_txt = sys.argv[1:4]

NUM_RE = re.compile(r"^-?\(?[\d,]+\.\d{1,2}\)?$")
DASH = {"-", "—", "–", "_", "--"}

# section header label -> (category tag)
SECTION_MAP = [
    (r"^STATE ?SECTOR$", None),
    (r"^MSPGCL$", "MSPGCL"),
    (r"^DODSON$", "State-Other (Dodson)"),
    (r"^CENTRAL ?SECTOR$", None),
    (r"^NTPC$", "Central-NTPC"),
    (r"^NPCIL$", "Central-NPCIL"),
    (r"^Other'?s$", "Central-Others/Hydro/Interstate"),
    (r"^IPP$", "IPP"),
    (r"^Medium ?Term$", "Medium Term"),
    (r"^NON ?CONVENTIONAL", "RE (Non Conventional)"),
]


def num(t):
    t = t.replace(" ", "")
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    v = float(t.replace(",", ""))
    return -v if neg else v


def parse_page(path):
    boxes = json.load(open(path))
    # header positions
    hdr = [b for b in boxes if b["text"].strip().upper() in ("MYT", "ACTUAL") and b["y1"] < 650]
    hdr.sort(key=lambda b: b["x0"])
    src_hdr = [b for b in boxes if b["text"].strip().lower() == "source" and b["y1"] < 650]
    st_hdr = [b for b in boxes if "Generating" in b["text"] and b["y1"] < 650]
    if len(hdr) != 4 or not src_hdr or not st_hdr:
        raise RuntimeError(f"header not found in {path}: {[b['text'] for b in hdr]}")
    hgt = sorted(b["y1"] - b["y0"] for b in boxes)[len(boxes) // 2]
    tol = 0.45 * hgt
    col_centres = [(b["x0"] + b["x1"]) / 2 for b in hdr]
    # numeric cells are right aligned within columns; use the column boundaries midway
    edges = [(col_centres[i] + col_centres[i + 1]) / 2 for i in range(3)]
    src_x0 = src_hdr[0]["x0"] - 2.0 * hgt
    num_x0 = col_centres[0] - 3.5 * hgt
    hdr_y = max(b["y1"] for b in hdr) + 1.1 * hgt  # skip 'MUs / Rs. Crs' sub-header line
    body = [b for b in boxes if (b["y0"] + b["y1"]) / 2 > hdr_y]
    body.sort(key=lambda b: (b["y0"] + b["y1"]) / 2)
    rows, cur, cur_y = [], [], None
    for b in body:
        yc = (b["y0"] + b["y1"]) / 2
        if cur_y is not None and abs(yc - cur_y) > tol:
            rows.append(cur)
            cur = []
        if not cur:
            cur_y = yc
        cur.append(b)
    if cur:
        rows.append(cur)
    out = []
    for r in rows:
        r.sort(key=lambda b: b["x0"])
        label_parts, src_parts, vals = [], [], [None] * 4
        for b in r:
            xc = (b["x0"] + b["x1"]) / 2
            t = b["text"].strip()
            if re.match(r"^-?[\d,]+'\d{1,2}$", t):
                t = t.replace("'", ".")
            if b["x0"] >= num_x0 and (NUM_RE.match(t.replace(" ", "")) or t in DASH):
                idx = sum(xc > e for e in edges)
                vals[idx] = None if t in DASH else num(t)
            elif b["x0"] >= src_x0 and b["x0"] < num_x0:
                src_parts.append(t)
            elif b["x0"] > st_hdr[0]["x0"] - 3.0 * hgt and b["x0"] < src_x0:
                label_parts.append(t)
        label = " ".join(label_parts).strip()
        if not label and src_parts and any(v is not None for v in vals):
            label = " ".join(src_parts) + " [label from source col]"
        if not label and all(v is None for v in vals):
            continue
        out.append({"label": label, "source": " ".join(src_parts).replace("Transmis sion", "Transmission"),
                    "vals": vals, "y": (r[0]["y0"] + r[0]["y1"]) / 2})
    return out


def norm_label(s):
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"^APL ?(\d+) ?MW$", r"APL \1 MW", s)
    s = re.sub(r"^RIPL ?(\d+) ?MW$", r"RIPL \1 MW", s)
    s = re.sub(r"^Total(?=[A-Z])", "Total ", s)
    s = re.sub(r"^Total Other's$", "Total Others", s)
    s = re.sub(r"^Parli ?6 ?& ?7$", "Parli 6 & 7", s)
    s = re.sub(r"^Parli ?Replacement", "Parli Replacement", s)
    s = re.sub(r"^Bhusawal 4 ?& ?5$", "Bhusawal 4 & 5", s)
    s = re.sub(r"^Paras 3 ?& ?4$", "Paras 3 & 4", s)
    s = re.sub(r"^KAPS ?3 ?& ?4$", "KAPS 3&4", s)
    s = re.sub(r"^TAPS ?3 ?& ?4$", "TAPS 3&4", s)
    s = re.sub(r"^VSTP ?IV$", "VSTP IV", s)
    s = re.sub(r"^VSTP ?V$", "VSTP V", s)
    s = re.sub(r"^VSTP ?I$", "VSTP I", s)
    s = re.sub(r"^JSw$", "JSW", s)
    s = s.replace("NONCONVENTIONAL", "NON CONVENTIONAL").replace("Sub- total", "Sub - total")
    return s


month_files = {}
for p in sorted(glob.glob(os.path.join(ocr_dir, "*.json"))):
    base = os.path.basename(p)[:-5]  # e.g. FEB-26-000
    mon = base[:6]
    month_files.setdefault(mon, []).append(p)

# Cells the OCR missed/misread; values read visually from the page images (documented in findings.md)
# keys: (month, label) -> {index: value}; index 0=MU MYT, 1=MU actual, 2=Rs cr MYT, 3=Rs cr actual
OVERRIDES = {("2025-05", "Gadarwara"): {0: 69.01}, ("2025-09", "Solar"): {2: 659.53}}
for _m in ("2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10"):
    OVERRIDES[(_m, "SLDC")] = {2: 2.22, 3: 2.22}

CANON = {}
for _c in ["Bhusawal 3", "Bhusawal 4 & 5", "Bhusawal 6", "Khaparkheda 1 to 4", "Khaparkheda 5", "Nashik 3 to 5",
           "Chandrapur 3 to 7", "Chandrapur 8 & 9", "Paras 3 & 4", "Parli 6 & 7", "Parli Replacement U 8", "Koradi 6",
           "Koradi 8 to 10", "Uran", "MSPGCL True Up", "MSPGCL - IEPL", "MSPGCL - Dhariwal", "Dodson II",
           "KSTPS", "KSTPS III", "VSTP I", "VSTP II", "VSTP III", "VSTP IV", "VSTP V", "SIPAT TPS 1", "SIPAT TPS 2",
           "KhSTPS-II", "Mauda I", "Mauda II", "NTPC Solapur", "Lara", "Gadarwara", "Khargone", "Kawas", "Gandhar",
           "KAPS 1&2", "KAPS 3&4", "TAPS 1&2", "TAPS 3&4", "RGPPL", "SSP", "Pench", "Subhansari Hydro",
           "NTPC NVVN Coal", "MPEB", "JSW", "TPCL", "APL 125 MW", "APL 1320 MW", "APL 1200 MW", "APL 440 MW", "GMR",
           "RIPL 450 MW", "RIPL 750 MW", "SWPGPL", "PTSL", "JPL - Tamnar", "JPL - Shirpur", "MPL", "Hydro (NCE)",
           "Wind", "Bagasse", "Biomass", "MSW", "PHSP", "Hybrid", "Solar", "REC", "Short Term", "DSM", "CTUIL",
           "MSETCL", "SLDC", "STU Fee", "Others", "Total Medium Term"]:
    CANON[re.sub(r"[^a-z0-9&]", "", _c.lower())] = _c
CANON.update({"spattps2": "SIPAT TPS 2", "khstpsi": "KhSTPS-II", "kstpsii": "KSTPS III", "jpltammar": "JPL - Tamnar",
              "saiwardha": "SWPGPL", "tatapower": "TPCL", "msw[labelfromsourcecol]": "MSW"})


def canon(lab, section):
    if lab.startswith("Hydro [label from source col]") or (lab == "Hydro" and section == "MSPGCL"):
        return "MSPGCL Hydro"
    k = re.sub(r"[^a-z0-9&\[\]]", "", lab.lower())
    return CANON.get(k, CANON.get(re.sub(r"[^a-z0-9&]", "", lab.lower()), lab))


MON = {m: i for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}
records, checks = [], []
for mon, files in sorted(month_files.items(), key=lambda kv: (int(kv[0][4:6]), MON[kv[0][:3]])):
    ym = f"20{mon[4:6]}-{MON[mon[:3]]:02d}"
    section, top = None, None
    comp_sum = {}
    for f in sorted(files):
        prev = None
        for row in parse_page(f):
            lab = norm_label(row["label"])
            vals = row["vals"]
            note = ""
            if not lab and prev == "Biomass" and any(v is not None for v in vals):
                lab, note = "MSW", "label OCR-missed; row position between Biomass and PHSP (MSW) verified visually"
            if lab and not lab.lower().startswith(("total", "sub", "(excl")):
                lab = canon(lab, section)
            if (ym, lab) in OVERRIDES:
                for i, v in OVERRIDES[(ym, lab)].items():
                    vals[i] = v
                note = "cell(s) %s read visually from scan (OCR missed/misread)" % sorted(OVERRIDES[(ym, lab)])
            if lab:
                prev = lab
            if not lab:
                checks.append(f"{ym}: unlabeled numeric row {vals} in {os.path.basename(f)}")
                continue
            matched = False
            for pat, cat in SECTION_MAP:
                if re.match(pat, lab, re.I) and all(v is None for v in vals) and not row["source"]:
                    if cat is not None:
                        section = cat
                    matched = True
                    break
            if matched:
                continue
            if all(v is None for v in vals) and not lab.lower().startswith("total power purchase"):
                checks.append(f"{ym}: row without values skipped: {lab!r} [{row['source']}]")
                continue
            is_total = bool(re.match(r"^(Total|Sub - total|Sub-total|\(excluding)", lab, re.I))
            if lab.lower().startswith("total power purchase"):
                # values sit on the '(excluding Transmission &' line in some scans
                is_total = True
            src = row["source"]
            cat = section
            if lab == "RGPPL":
                cat = "Central-RGPPL (gas)"
            if lab in ("Short Term",) or src == "Short Term":
                cat = "Short Term (bilateral/exchange)"
            elif lab == "DSM":
                cat = "DSM / Deviation"
            elif src in ("Transmission",) or lab in ("SLDC", "STU Fee") or (src == "Other" and section in ("Transmission", None)):
                cat = "Transmission & Other charges"
            if cat == "Transmission & Other charges":
                section = "Transmission & Other charges"
            if lab in ("CTUIL", "MSETCL"):
                section = "Transmission & Other charges"
                cat = section
            if section == "RE (Non Conventional)" and lab.startswith("Short Term"):
                section = None
            rec = {"month": ym, "row_label": lab, "category": "TOTAL" if is_total else cat,
                   "fuel_or_type": src, "is_total": int(is_total),
                   "mu_myt": vals[0], "mu_actual": vals[1], "rs_cr_myt": vals[2], "rs_cr_actual": vals[3],
                   "page_file": os.path.basename(f), "note": note}
            records.append(rec)

# tidy output
with open(out_csv, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["month", "source", "category", "fuel_type", "is_total_row", "mu_actual", "rs_cr_actual",
                "rs_per_kwh_actual", "mu_myt_approved", "rs_cr_myt_approved", "rs_per_kwh_myt",
                "fixed_rs_cr", "variable_rs_cr", "doc", "note"])
    for r in records:
        def rate(mu, rs):
            if mu and rs is not None and abs(mu) > 0.005:
                return round(rs * 10 / mu, 3)
            return None
        w.writerow([r["month"], r["row_label"], r["category"], r["fuel_or_type"], r["is_total"],
                    r["mu_actual"], r["rs_cr_actual"], rate(r["mu_actual"], r["rs_cr_actual"]),
                    r["mu_myt"], r["rs_cr_myt"], rate(r["mu_myt"], r["rs_cr_myt"]), "", "",
                    f"PP-COST-{r['page_file'][:6]}-STANDALONE-ENGLISH.pdf", r["note"]])

# consistency checks: section component sums vs 'Total <x>' rows
groups = {}
for r in records:
    groups.setdefault(r["month"], []).append(r)
for ym, rs in groups.items():
    acc = {}
    for r in rs:
        if not r["is_total"]:
            a = acc.setdefault(r["category"], [0.0, 0.0, 0.0, 0.0])
            for i, k in enumerate(["mu_myt", "mu_actual", "rs_cr_myt", "rs_cr_actual"]):
                a[i] += r[k] or 0.0
    tot_map = {"Total MSPGCL": ["MSPGCL"], "Total NTPC": ["Central-NTPC"], "Total NPCIL": ["Central-NPCIL"],
               "Total Others": ["Central-Others/Hydro/Interstate"], "Total Other's": ["Central-Others/Hydro/Interstate"], "Total IPP": ["IPP"],
               "Total Medium Term": ["Medium Term"], "Total Non Conventional": ["RE (Non Conventional)"],
               "Total Transmission": ["Transmission & Other charges"]}
    for r in rs:
        if r["row_label"] in tot_map:
            s = [0.0] * 4
            for c in tot_map[r["row_label"]]:
                s = [x + y for x, y in zip(s, acc.get(c, [0] * 4))]
            printed = [r["mu_myt"], r["mu_actual"], r["rs_cr_myt"], r["rs_cr_actual"]]
            # Total Transmission row has MU columns blank
            for i, nm in enumerate(["MU_MYT", "MU_ACT", "RS_MYT", "RS_ACT"]):
                if printed[i] is None:
                    continue
                if abs(printed[i] - s[i]) > 0.06:
                    checks.append(f"{ym} {r['row_label']} {nm}: printed {printed[i]} vs sum {round(s[i], 2)} (diff {round(printed[i] - s[i], 2)})")
    # grand total: Total Power Purchase vs sum of all non-total non-transmission components
    tpp = [r for r in rs if r["row_label"].lower().startswith(("total power purchase", "(excluding"))]
    allc = [0.0] * 4
    for c, a in acc.items():
        if c != "Transmission & Other charges":
            allc = [x + y for x, y in zip(allc, a)]
    for r in tpp:
        printed = [r["mu_myt"], r["mu_actual"], r["rs_cr_myt"], r["rs_cr_actual"]]
        if any(v is not None for v in printed):
            for i, nm in enumerate(["MU_MYT", "MU_ACT", "RS_MYT", "RS_ACT"]):
                if printed[i] is not None and abs(printed[i] - allc[i]) > 0.15:
                    checks.append(f"{ym} TOTAL POWER PURCHASE {nm}: printed {printed[i]} vs sum {round(allc[i], 2)} (diff {round(printed[i] - allc[i], 2)})")
    checks.append(f"{ym}: {sum(1 for r in rs if not r['is_total'])} component rows, {sum(1 for r in rs if r['is_total'])} total rows")

open(check_txt, "w").write("\n".join(checks) + "\n")
print("\n".join(checks))
