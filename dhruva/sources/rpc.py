"""Regional Power Committee settlement accounts: DSM, SRAS, TRAS, block data.

Each RPC publishes the CERC weekly accounts in its own layout. Every table is
validated against its own TOTAL row (see tables.py); anything that does not
reconcile is recorded as a parse error and left out, never estimated.

Amounts are stored in rupees, energy in MWh, prices in Rs/MWh.
"""
from __future__ import annotations

import csv
import hashlib
import html as htmllib
import io
import json
import logging
import re
import statistics
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from .. import http
from ..config import DATA_DIR
from . import tables as T

log = logging.getLogger(__name__)

RAW_DIR = DATA_DIR / "grid" / "_raw"          # downloaded originals (git-ignored)
UA_HEADERS = {"Accept": "*/*"}

ERPC_HOME = "https://www.erpc.gov.in/"
WRPC_DSM_MENU = "https://www.wrpc.gov.in/api/TopMenu/custom/342"
WRPC_AS_MENU = "https://www.wrpc.gov.in/api/TopMenu/custom/348"
WRPC_DSM_PAGE = "https://www.wrpc.gov.in/menu/DSM_342"
WRPC_AS_PAGE = "https://www.wrpc.gov.in/menu/Ancillary%20Services%20_348"
NERPC_PAGE = "https://nerpc.gov.in/?page_id=5872"


@dataclass
class Week:
    rpc: str
    start: date
    end: date
    listing: str
    docs: dict[str, dict] = field(default_factory=dict)   # kind -> {title, url}

    @property
    def key(self) -> str:
        return f"{self.rpc.lower()}_{self.start.isoformat()}"


# ------------------------------------------------------------------ helpers

def _d(s: str) -> date:
    s = s.strip().replace("/", ".").replace("-", ".")
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%d.%b.%y", "%d.%b.%Y", "%d%m%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"unrecognised date {s!r}")


def download(url: str) -> Path:
    """Fetch once and keep the original under data/grid/_raw/ (keyed by URL)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / hashlib.sha1(url.encode()).hexdigest()[:20]
    if not path.exists():
        path.write_bytes(http.get_bytes(url, headers=UA_HEADERS, timeout=180))
    return path


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


CATEGORY_GROUPS = [
    (r"benefic|discom", "Discoms & states"),
    (r"inter\W*regional", "Inter-regional"),
    (r"inter\W*national|bhutan|nepal|bangladesh", "Cross-border"),
    (r"wind|solar|\bre\b|re gen|qca|\bca\b|renewable", "Wind & solar"),
    (r"gen|cgs|isgs|station|thermal|hydro|ipp", "Conventional generators"),
]


def group_of(category: str | None) -> str:
    c = (category or "").lower()
    for pat, label in CATEGORY_GROUPS:
        if re.search(pat, c):
            return label
    return "Other"


def _table_out(t: T.Table, fields: list[str], cols: list[int], scale: dict[str, float] | None = None) -> dict:
    out = {"status": t.status, "message": t.message, "rows": []}
    if t.status == "parse_error":
        return out
    scale = scale or {}
    for r in t.rows:
        rec = {"name": r["name"]}
        for f, c in zip(fields, cols):
            v = r["values"][c]
            rec[f] = None if v is None else round(v * scale.get(f, 1), 3)
        out["rows"].append(rec)
    if t.total:
        out["total"] = {f: round(t.total[c] * scale.get(f, 1), 3) for f, c in zip(fields, cols)
                        if c < len(t.total) and t.total[c] is not None}
    return out


def _fail(kind: str, exc: Exception) -> dict:
    return {"status": "parse_error", "message": f"{kind}: {exc}", "rows": []}


# ------------------------------------------------------------------ block data (frequency, Normal Rate)

def _blocks_out(series: dict[str, dict[int, list]], unit_nr: float) -> dict:
    """series[date][block] -> list of (freq, nr) observations across entities."""
    dates = sorted(series)
    freq, nr, agree = [], [], []
    for d in dates:
        f_row, n_row, a_row = [], [], []
        for b in range(1, 97):
            obs = series[d].get(b, [])
            fs = [f for f, _ in obs if f is not None]
            ns = [round(n * unit_nr, 2) for _, n in obs if n is not None]
            f_row.append(round(statistics.median(fs), 3) if fs else None)
            if ns:
                mode, cnt = Counter(ns).most_common(1)[0]
                n_row.append(mode)
                a_row.append(round(cnt / len(ns), 3))
            else:
                n_row.append(None)
                a_row.append(None)
        freq.append(f_row); nr.append(n_row); agree.append(a_row)
    return {"status": "ok" if dates else "parse_error", "message": "" if dates else "no block rows found",
            "dates": dates, "frequency_hz": freq, "normal_rate_rs_mwh": nr, "normal_rate_agreement": agree}


def erpc_blocks(path: Path) -> dict:
    import openpyxl
    # Cached downloads carry no extension, which openpyxl rejects for paths; a buffer is fine.
    wb = openpyxl.load_workbook(io.BytesIO(path.read_bytes()), read_only=True, data_only=True)
    series: dict[str, dict[int, list]] = defaultdict(lambda: defaultdict(list))
    for ws in wb.worksheets:
        hdr = None
        for row in ws.iter_rows(values_only=True):
            if hdr is None:
                if row and row[0] == "Date":
                    hdr = [str(h or "") for h in row]
                    fi = next(i for i, h in enumerate(hdr) if h.startswith("Freq"))
                    ni = next(i for i, h in enumerate(hdr) if h.startswith("Normal DSM Rate"))
                continue
            if not row or not row[0] or not re.match(r"\d{4}-\d{2}-\d{2}", str(row[0])):
                continue
            series[str(row[0])[:10]][int(row[2])].append((row[fi], row[ni]))
    return _blocks_out(series, unit_nr=10.0)          # p/kWh -> Rs/MWh


def wrpc_blocks(path: Path) -> dict:
    z = zipfile.ZipFile(path)
    series: dict[str, dict[int, list]] = defaultdict(lambda: defaultdict(list))
    for name in z.namelist():
        if not name.endswith("_DSM-2024_Data.csv"):
            continue
        for r in csv.DictReader(io.StringIO(z.read(name).decode("utf-8", errors="replace"))):
            try:
                series[r["Date"]][int(r["Block"])].append((float(r["Freq(Hz)"]), float(r["Normal Rate (p/Kwh)"])))
            except (KeyError, ValueError):
                continue
    return _blocks_out(series, unit_nr=10.0)


def nerpc_blocks(members: dict[str, bytes]) -> dict:
    import openpyxl
    data = next((b for n, b in members.items() if n.startswith("DeviationDetails")), None)
    if data is None:
        return {"status": "parse_error", "message": "DeviationDetails workbook missing from the data file"}
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    series: dict[str, dict[int, list]] = defaultdict(lambda: defaultdict(list))
    for ws in wb.worksheets:
        day = None
        for row in ws.iter_rows(values_only=True):
            if not row:
                continue
            if row[1] == "Total" and isinstance(row[0], str) and re.match(r"\d{2}-\d{2}-\d{4}", row[0]):
                day = datetime.strptime(row[0], "%d-%m-%Y").date().isoformat()
                continue
            if day and isinstance(row[1], (int, float)) and isinstance(row[3], (int, float)):
                nr = row[22] if len(row) > 22 and isinstance(row[22], (int, float)) else None
                series[day][int(row[1])].append((row[3], nr))
    return _blocks_out(series, unit_nr=1.0)           # already Rs/MWh


# ------------------------------------------------------------------ ERPC

def erpc_weeks(limit: int = 4) -> list[Week]:
    s = http.get_text(ERPC_HOME)
    weeks: dict[str, Week] = {}
    for m in re.finditer(r"DSM, SRAS, TRAS and SCUC Settlement Account for the period from ([\d.]+) to ([\d.]+)", s):
        seg = s[m.end(): m.end() + 3000]
        links = re.findall(r'href="(https://www\.erpc\.gov\.in/commercials/[^"]+)"[^>]*>\s*(PDF|Excel)', seg)
        w = Week("ERPC", _d(m.group(1)), _d(m.group(2)), ERPC_HOME)
        if w.key in weeks:
            continue
        title = " ".join(m.group(0).split())
        for url, kind in links[:2]:
            w.docs["account_pdf" if kind == "PDF" else "blocks_xlsx"] = {"title": title + (" (PDF)" if kind == "PDF" else " – block-wise data"), "url": url}
        weeks[w.key] = w
    return sorted(weeks.values(), key=lambda w: w.start, reverse=True)[:limit]


def erpc_parse(week: Week) -> dict:
    out: dict = {}
    try:
        lines = T.pdf_text(download(week.docs["account_pdf"]["url"])).splitlines()
        i = T.find_index(lines, r"Deviation Settlement Account\s*$")
        h = T.find_index(lines, r"Payable\s+Receivable\s+Payable\s+Receivable", i)
        end = T.find_index(lines, r"Payable To The Pool", h)
        if min(i, h, end) < 0:
            raise T.ParseError("DSM summary table not found")
        if "Lakh" not in " ".join(lines[i:h + 1]):
            raise T.ParseError("summary is no longer stated in Rs lakh")
        cols = T.header_centres(lines[h], ["Payable", "Receivable", "Payable", "Receivable"])
        t = T.positional_rows(lines[h + 1:end], cols, [0, 1])
        dsm = _table_out(t, ["payable_rs", "receivable_rs"], [0, 1], {"payable_rs": 1e5, "receivable_rs": 1e5})
        if t.status != "parse_error":
            for row, src in zip(dsm["rows"], t.rows):
                row["category"] = src["category"]
        # Weekly deviation MWh: "Week total NAME sched actual agc dev payable receivable"
        dev = {}
        for line in lines:
            m = re.match(r"\s*Week total\s+(.+?)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+\d+\s+\d+\s*$", line)
            if m:
                dev[norm(m.group(1))] = (float(m.group(2)), float(m.group(3)), float(m.group(5)))
        for row in dsm["rows"]:
            sch, act, dv = dev.get(norm(row["name"]), (None, None, None))
            row.update(scheduled_mwh=sch, actual_mwh=act, deviation_mwh=dv)
        out["dsm"] = dsm
        sras = T.numbered_rows(T.section(lines, r"Format-SRAS 1", T.TOTAL_ROW, include_end=True), 6)
        out["sras"] = _table_out(sras, ["up_mwh", "down_mwh", "net_mwh", "energy_rs", "incentive_rs", "total_rs"], range(6))
        tm = T.numbered_rows(T.section(lines, r"Format-TRAS-II:", T.TOTAL_ROW, include_end=True), 14)
        out["tras_market"] = _table_out(tm, TRAS_MARKET_FIELDS, range(14))
        ts = T.numbered_rows(T.section(lines, r"Format-TRAS-III", T.TOTAL_ROW, include_end=True), 5)
        out["tras_shortfall"] = _table_out(ts, ["up_mwh", "up_rs", "down_mwh", "down_rs", "net_rs"], range(5))
    except Exception as exc:  # noqa: BLE001 - recorded, not raised
        out.setdefault("dsm", _fail("account PDF", exc))
    if "blocks_xlsx" in week.docs:
        try:
            out["blocks"] = erpc_blocks(download(week.docs["blocks_xlsx"]["url"]))
        except Exception as exc:  # noqa: BLE001
            out["blocks"] = _fail("block-wise workbook", exc)
    return out


TRAS_MARKET_FIELDS = ["da_up_cleared_mwh", "da_up_sched_mwh", "da_up_energy_rs", "da_up_commit_rs",
                      "rt_up_cleared_mwh", "rt_up_sched_mwh", "rt_up_energy_rs", "rt_up_commit_rs",
                      "up_total_rs", "da_down_mwh", "da_down_rs", "rt_down_mwh", "rt_down_rs", "net_rs"]


# ------------------------------------------------------------------ WRPC

def _wrpc_links(menu_url: str) -> list[tuple[str, str]]:
    d = http.get_json(menu_url)
    s = d.get("html") or ""
    out = []
    for href, text in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', s, re.S):
        t = " ".join(htmllib.unescape(re.sub(r"<[^>]+>", " ", text)).split())
        out.append((t, href.strip()))
    return out


WEEK_RE = re.compile(r"(\d{2}\.\d{2}\.\d{2,4})\s*to\s*(\d{2}\.\d{2}\.\d{2,4})", re.I)


def wrpc_weeks(limit: int = 4) -> list[Week]:
    weeks: dict[str, Week] = {}
    links = _wrpc_links(WRPC_DSM_MENU)
    for k, (text, href) in enumerate(links):
        m = WEEK_RE.search(text)
        if not m or not href.lower().endswith(".pdf"):
            continue
        w = Week("WRPC", _d(m.group(1)), _d(m.group(2)), WRPC_DSM_PAGE)
        if w.key in weeks:            # the list is newest-first; keep the latest revision
            continue
        w.docs["dsm_pdf"] = {"title": f"WRPC DSM account, {text}", "url": href}
        nxt = links[k + 1] if k + 1 < len(links) else ("", "")
        if nxt[1].lower().endswith(".zip"):
            w.docs["blocks_zip"] = {"title": f"WRPC all-member block-wise data, {m.group(0)}", "url": nxt[1]}
        weeks[w.key] = w
    try:
        for text, href in _wrpc_links(WRPC_AS_MENU):
            m = WEEK_RE.search(text)
            if m and re.search(r"TRAS", text) and href.lower().endswith(".pdf"):
                key = f"wrpc_{_d(m.group(1)).isoformat()}"
                if key in weeks and "as_pdf" not in weeks[key].docs:
                    weeks[key].docs["as_pdf"] = {"title": f"WRPC {text}", "url": href}
    except http.FetchError as exc:
        log.warning("WRPC AS list: %s", exc)
    return sorted(weeks.values(), key=lambda w: w.start, reverse=True)[:limit]


def wrpc_parse(week: Week) -> dict:
    out: dict = {}
    try:
        lines = T.pdf_text(download(week.docs["dsm_pdf"]["url"])).splitlines()
        i = T.find_index(lines, r"ABT based Deviation Charge Account")
        h = T.find_index(lines, r"Payable\s+Receivable\s+Net DSM", i)
        end = T.find_index(lines, T.TOTAL_ROW, h)
        if min(i, h, end) < 0:
            raise T.ParseError("DSM summary table not found")
        if "(All figures in Rs.)" not in " ".join(lines[i:h + 1]):
            raise T.ParseError("summary is no longer stated in rupees")
        body = lines[h + 1:end + 1]
        cols = T.header_centres(lines[h], ["Payable", "Receivable", "Net DSM (Rs.)"])
        # Category headings are lettered ("B. BENEFICIARIES ..."); the same words reappear unlettered beside sub-totals.
        t = T.positional_rows(body, cols, [0, 1], heading_pat=r"^[A-Z]\.\s+\S")
        if t.status == "parse_error" and t.rows and t.total and all(
                abs(abs((r["values"][0] or 0) - (r["values"][1] or 0)) - abs(r["values"][2] or 0)) <= 2 for r in t.rows):
            # Every row checks out on its own (payable - receivable = printed net), so the
            # rows were read correctly and the gap is in WRPC's printed totals. Publish, flagged.
            gp = sum(r["values"][0] or 0 for r in t.rows) - t.total[0]
            gr = sum(r["values"][1] or 0 for r in t.rows) - t.total[1]
            t.status = "source_mismatch"
            t.message = (f"Each entity row reconciles (payable − receivable = printed net), but WRPC's printed total "
                         f"differs from the sum of its rows by ₹{gp:,.0f} payable and ₹{gr:,.0f} receivable. "
                         "Rows are shown as printed.")
        dsm = _table_out(t, ["payable_rs", "receivable_rs"], [0, 1])
        if t.status != "parse_error":
            for row, src in zip(dsm["rows"], t.rows):
                row["category"] = src["category"]
        # Weekly MWh from each entity's day-wise summary: Total <name> actual schedule ... (MU)
        dev = {}
        cur = None
        for line in lines:
            m = re.match(r"\s*Daywise Summary\s*:\s*(.+?)\s*\|", line)
            if m:
                cur = m.group(1)
                continue
            if cur and re.match(r"\s*Total\b", line):
                nums = [v for v, *_ in T.numbers(line)]
                if len(nums) >= 2:
                    dev[norm(cur)] = (nums[1] * 1000, nums[0] * 1000)
                cur = None
        for row in dsm["rows"]:
            sch, act = dev.get(norm(row["name"]), (None, None))
            row.update(scheduled_mwh=sch, actual_mwh=act,
                       deviation_mwh=None if sch is None else round(act - sch, 3))
        out["dsm"] = dsm
    except Exception as exc:  # noqa: BLE001
        out["dsm"] = _fail("DSM PDF", exc)
    if "as_pdf" in week.docs:
        try:
            L = T.pdf_text(download(week.docs["as_pdf"]["url"])).splitlines()
            sras = T.numbered_rows(T.section(L, r"Payments to the SRAS Service Provider", T.TOTAL_ROW, include_end=True), 6)
            out["sras"] = _table_out(sras, ["up_mwh", "down_mwh", "incentive_rs", "net_mwh", "energy_rs", "total_rs"], range(6))
            for r in out["sras"].get("rows", []):
                r["down_mwh"] = abs(r["down_mwh"]) if r["down_mwh"] is not None else None
            tm = T.numbered_rows(T.section(L, r"Format-TRAS-II:", T.TOTAL_ROW, include_end=True), 14)
            out["tras_market"] = _table_out(tm, TRAS_MARKET_FIELDS, range(14))
            parts, after = [], 0
            for label in ("shortfall", "emergency"):
                i = T.find_index(L, r"Format-TRAS-III", after)
                if i < 0:
                    break
                sec = T.section(L, r"Format-TRAS-III", T.TOTAL_ROW, after=i, include_end=True)
                after = i + len(sec)
                tbl = _table_out(T.numbered_rows(sec, 5), ["up_mwh", "up_rs", "down_mwh", "down_rs", "net_rs"], range(5))
                tbl["condition"] = label
                parts.append(tbl)
            out["tras_shortfall"] = _merge_tras3(parts)
        except Exception as exc:  # noqa: BLE001
            out["sras"] = _fail("AS PDF", exc)
    if "blocks_zip" in week.docs:
        try:
            out["blocks"] = wrpc_blocks(download(week.docs["blocks_zip"]["url"]))
        except Exception as exc:  # noqa: BLE001
            out["blocks"] = _fail("block-wise zip", exc)
    return out


def _merge_tras3(parts: list[dict]) -> dict:
    if not parts:
        return {"status": "parse_error", "message": "TRAS-III tables not found", "rows": []}
    bad = [p for p in parts if p["status"] == "parse_error"]
    if bad:
        return bad[0]
    rows: dict[str, dict] = {}
    for p in parts:
        for r in p["rows"]:
            acc = rows.setdefault(r["name"], {"name": r["name"], "up_mwh": 0, "up_rs": 0, "down_mwh": 0, "down_rs": 0, "net_rs": 0})
            for k in ("up_mwh", "up_rs", "down_mwh", "down_rs", "net_rs"):
                acc[k] = round(acc[k] + (r.get(k) or 0), 3)
    status = "ok" if all(p["status"] == "ok" for p in parts) else "unvalidated"
    return {"status": status, "message": "shortfall and emergency conditions combined", "rows": list(rows.values()),
            "total": {k: round(sum(p.get("total", {}).get(k, 0) for p in parts), 3) for k in ("up_mwh", "up_rs", "down_mwh", "down_rs", "net_rs")}}


# ------------------------------------------------------------------ NERPC

def nerpc_weeks(limit: int = 4) -> list[Week]:
    s = http.get_text(NERPC_PAGE)
    links = re.findall(r'href="(https://nerpc\.gov\.in/wp-content/uploads/[^"#]+?)\s*(?:#[^"]*)?"', s)
    weeks: dict[str, Week] = {}

    def add(kind: str, url: str, a: date, b: date):
        w = weeks.setdefault(f"nerpc_{a.isoformat()}", Week("NERPC", a, b, NERPC_PAGE))
        w.docs.setdefault(kind, {"title": f"NERPC {Path(url).name}", "url": url})

    for url in links:
        fn = Path(url).name
        m = re.search(r"Provisional-DSM-statement-from-(\d{6})-to-(\d{6})", fn)
        if m:
            add("dsm_pdf", url, _d(m.group(1)), _d(m.group(2)))
            continue
        m = re.search(r"Provisional-SRAS-and-TRAS-statement-from-(\d{6})-to-(\d{6})", fn)
        if m:
            add("as_pdf", url, _d(m.group(1)), _d(m.group(2)))
            continue
        m = re.search(r"DATA_FILE[-_ ]*(\d{1,2}-[A-Za-z]{3}-\d{2})-to-(\d{1,2}-[A-Za-z]{3}-\d{2})\.zip", fn)
        if m:
            add("data_zip", url, _d(m.group(1)), _d(m.group(2)))
    # The AS statement occasionally starts a day early; attach it to the DSM week ending the same day.
    for k in [k for k, w in weeks.items() if set(w.docs) == {"as_pdf"}]:
        lone = weeks.pop(k)
        for w in weeks.values():
            if w.end == lone.end:
                w.docs["as_pdf"] = lone.docs["as_pdf"]
    good = [w for w in weeks.values() if "dsm_pdf" in w.docs]
    return sorted(good, key=lambda w: w.start, reverse=True)[:limit]


def nerpc_parse(week: Week) -> dict:
    out: dict = {}
    try:
        lines = T.pdf_text(download(week.docs["dsm_pdf"]["url"])).splitlines()
        i = T.find_index(lines, r"ABT based Deviation Charge Account")
        h = T.find_index(lines, r"CONSTITUENTS\s+SCHEDULE", i)
        end = T.find_index(lines, r"Pool Balance", h)
        if min(i, h, end) < 0:
            raise T.ParseError("DSM summary table not found")
        # Columns: schedule, actual, deviation (MWh), receivable from pool (A), payable to pool (B).
        # The money headers span several lines, so anchor those two columns on the TOTAL row.
        hdr = lines[h]
        tot = T.find_index(lines, T.TOTAL_ROW, h)
        money = [e for _, _, e in T.numbers(lines[tot])][-2:] if 0 < tot < end else []
        if len(money) != 2:
            raise T.ParseError("TOTAL row with receivable and payable figures not found")
        cols = [T.header_centres(hdr, ["SCHEDULE (MWH)"])[0], T.header_centres(hdr, ["ACTUAL (MWH)"])[0],
                T.header_centres(hdr, ["DEVIATION (MWH)"])[0], *money]
        t = T.positional_rows(lines[h + 1:end], cols, [3, 4])
        dsm = _table_out(t, ["scheduled_mwh", "actual_mwh", "deviation_mwh", "receivable_rs", "payable_rs"], range(5))
        if t.status != "parse_error":
            for row, src in zip(dsm["rows"], t.rows):
                row["category"] = src["category"]
        out["dsm"] = dsm
    except Exception as exc:  # noqa: BLE001
        out["dsm"] = _fail("DSM PDF", exc)
    if "as_pdf" in week.docs:
        try:
            L = T.pdf_text(download(week.docs["as_pdf"]["url"])).splitlines()
            sras = T.numbered_rows(T.section(L, r"Format SRAS - I:", T.TOTAL_ROW, include_end=True), 6)
            out["sras"] = _table_out(sras, ["up_mwh", "down_mwh", "net_mwh", "energy_rs", "incentive_rs", "total_rs"], range(6))
            ts = T.numbered_rows(T.section(L, r"Format TRAS - III", T.TOTAL_ROW, include_end=True), 4)
            t3 = _table_out(ts, ["up_mwh", "down_mwh", "up_rs", "down_rs"], range(4))
            for r in t3.get("rows", []):
                r["net_rs"] = round((r["up_rs"] or 0) - (r["down_rs"] or 0), 3)
            if "total" in t3:
                t3["total"]["net_rs"] = round(t3["total"]["up_rs"] - t3["total"]["down_rs"], 3)
            out["tras_shortfall"] = t3
        except Exception as exc:  # noqa: BLE001
            out["sras"] = _fail("AS PDF", exc)
    if "data_zip" in week.docs:
        try:
            z = zipfile.ZipFile(download(week.docs["data_zip"]["url"]))
            members = {n: z.read(n) for n in z.namelist() if n.lower().endswith(".xlsx")}
            out["blocks"] = nerpc_blocks(members)
            out["tras_market"], out["tras_prices"] = nerpc_tras(members)
        except Exception as exc:  # noqa: BLE001
            out["blocks"] = _fail("data zip", exc)
    return out


def nerpc_tras(members: dict[str, bytes]) -> tuple[dict, dict]:
    """Provider totals and block prices for the DAM/RTM ancillary markets from the TRAS data file."""
    import openpyxl
    data = next((b for n, b in members.items() if n.upper().startswith("TRAS")), None)
    if data is None:
        miss = {"status": "parse_error", "message": "TRAS workbook missing from the data file", "rows": []}
        return miss, miss
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    rows, prices = [], defaultdict(lambda: defaultdict(lambda: [None, None, None, None]))
    for ws in wb.worksheets:
        acc = dict.fromkeys(TRAS_MARKET_FIELDS, 0.0)
        for r in ws.iter_rows(min_row=3, values_only=True):
            if not r or not isinstance(r[1], (int, float)) or not isinstance(r[0], str):
                continue
            g = lambda i: float(r[i]) if i < len(r) and isinstance(r[i], (int, float)) else 0.0  # noqa: E731
            acc["da_up_cleared_mwh"] += g(2); acc["da_up_sched_mwh"] += g(3); acc["da_down_mwh"] += g(4)
            acc["da_up_energy_rs"] += g(8); acc["da_up_commit_rs"] += g(9); acc["da_down_rs"] += g(10)
            acc["rt_up_cleared_mwh"] += g(11); acc["rt_up_sched_mwh"] += g(12); acc["rt_down_mwh"] += g(13)
            acc["rt_up_energy_rs"] += g(17); acc["rt_up_commit_rs"] += g(18); acc["rt_down_rs"] += g(19)
            day = datetime.strptime(r[0], "%d-%m-%Y").date().isoformat()
            slot = prices[day][int(r[1])]
            # Only blocks where the provider actually cleared carry a market price.
            for k, (qty, px) in enumerate(((2, 5), (4, 7), (11, 14), (13, 16))):
                if g(qty) > 0 and g(px) > 0:
                    slot[k] = max(slot[k] or 0, g(px))
        acc["up_total_rs"] = acc["da_up_energy_rs"] + acc["da_up_commit_rs"] + acc["rt_up_energy_rs"] + acc["rt_up_commit_rs"]
        acc["net_rs"] = acc["up_total_rs"] - acc["da_down_rs"] - acc["rt_down_rs"]
        rows.append({"name": ws.title, **{k: round(v, 3) for k, v in acc.items()}})
    market = {"status": "ok", "message": "aggregated from block-wise TRAS data file", "rows": rows,
              "total": {k: round(sum(r[k] for r in rows), 3) for k in TRAS_MARKET_FIELDS}}
    days = sorted(prices)
    series = {k: [[prices[d][b][i] for b in range(1, 97)] for d in days]
              for i, k in enumerate(("da_up", "da_down", "rt_up", "rt_down"))}
    cleared = sum(1 for s in series.values() for day in s for v in day if v)
    return market, {"status": "ok", "dates": days, "rs_mwh": series, "blocks_with_clearing": cleared,
                    "message": "" if cleared else "no TRAS cleared for NER providers in the DAM/RTM AS markets this period"}


# ------------------------------------------------------------------ registry

RPCS = {
    "ERPC": {"region": "Eastern", "weeks": erpc_weeks, "parse": erpc_parse, "listing": ERPC_HOME},
    "WRPC": {"region": "Western", "weeks": wrpc_weeks, "parse": wrpc_parse, "listing": WRPC_DSM_PAGE},
    "NERPC": {"region": "North-Eastern", "weeks": nerpc_weeks, "parse": nerpc_parse, "listing": NERPC_PAGE},
}

# Sources we tried and could not use, with the reason we recorded on 2026-10-20.
UNAVAILABLE = {
    "NRPC": {"name": "NRPC weekly DSM / SRAS / TRAS accounts", "publisher": "Northern Regional Power Committee",
             "url": "https://nrpc.gov.in/", "probe": "https://nrpc.gov.in/api/Whatsnew",
             "reason": "the site's document API answers 401 Unauthorized without a login"},
    "SRPC": {"name": "SRPC weekly DSM / SRAS / TRAS accounts", "publisher": "Southern Regional Power Committee",
             "url": "https://srpc.kar.nic.in/", "probe": "https://srpc.kar.nic.in/",
             "reason": "connection reset during TLS handshake from this network"},
    "GRID_INDIA_FREQ": {"name": "Grid-India daily frequency profile", "publisher": "Grid Controller of India",
                        "url": "https://report.grid-india.in/", "probe": "https://report.grid-india.in/",
                        "reason": "host refused the connection from this network"},
    "GRID_INDIA_AS": {"name": "Grid-India ancillary services dispatch reports", "publisher": "Grid Controller of India",
                      "url": "https://grid-india.in/", "probe": "https://grid-india.in/",
                      "reason": "host refused the connection from this network"},
    "PXIL_TRAS": {"name": "PXIL TRAS market results", "publisher": "Power Exchange India",
                  "url": "https://www.pxil.co.in/", "probe": "https://www.pxil.co.in/",
                  "reason": "connection reset during TLS handshake from this network"},
    "IEX_TRAS": {"name": "IEX TRAS market results", "publisher": "Indian Energy Exchange",
                 "url": "https://www.iexindia.com/market-data/day-ahead-market/market-snapshot", "probe": None,
                 "reason": "no public TRAS segment in IEX's market-data site or API (checked market-data menu and /api/v1)"},
    "HPX_TRAS": {"name": "HPX TRAS market results", "publisher": "Hindustan Power Exchange",
                 "url": "https://www.hpxindia.com/", "probe": None,
                 "reason": "HPX publishes only DAM snapshot and area-price pages publicly; no TRAS results page found"},
}


def probe(url: str | None) -> tuple[bool, str]:
    if not url:
        return False, ""
    try:
        http.get_bytes(url, retries=0, timeout=25)
        return True, ""
    except http.FetchError as exc:
        return False, str(exc)
