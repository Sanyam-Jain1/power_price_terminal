"""Draft The Dhruva Weekly from the data: numbers first, an analyst adds colour."""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from . import derive, store
from .analytics import indices
from .config import NOTES_DIR


def _week(mkt: str, start: date, end: date, field: str = "mcp"):
    days, p = store.block_matrix(mkt, field, start, end)
    _, v = store.block_matrix(mkt, "scheduled_mw", start, end)
    return days, p, v


def _pct(a: float, b: float) -> str:
    if not (np.isfinite(a) and np.isfinite(b)) or b == 0:
        return "n/a"
    ch = (a / b - 1) * 100
    return f"{'+' if ch >= 0 else ''}{ch:.1f}%"


def _rs(x: float) -> str:
    return f"₹{x / 1000:.2f}/kWh" if np.isfinite(x) else "n/a"


def last_complete_week_end(today: date) -> date:
    """The Sunday that closes the most recent Monday-Sunday week fully in the past."""
    return today - timedelta(days=(today.weekday() + 1) % 7 or 7)


def draft(week_ending: date | None = None) -> tuple[date, str]:
    latest = store.latest_date("rtm") or date.today()
    end = week_ending or last_complete_week_end(latest + timedelta(days=1))
    start = end - timedelta(days=6)
    p_start, p_end = start - timedelta(days=7), start - timedelta(days=1)

    lines = [f"# The Dhruva Weekly — week ending {end:%d %b %Y}", "",
             f"_{start:%a %d %b} to {end:%a %d %b %Y}. Draft generated from IEX, NSE and Dhruva index data._", ""]

    rows = []
    stats = {}
    for mkt, label in (("dam", "DAM"), ("rtm", "RTM"), ("gdam", "G-DAM")):
        d, p, v = _week(mkt, start, end)
        _, pp, pv = _week(mkt, p_start, p_end)
        if not len(d):
            continue
        w = indices.vwap(p.ravel(), v.ravel())
        pw = indices.vwap(pp.ravel(), pv.ravel()) if len(pp) else float("nan")
        avg = float(np.nanmean(p))
        ev = float(np.nanmean(p[:, 72:92]))
        so = float(np.nanmean(p[:, 36:64]))
        cap = int(np.sum(p >= indices.PRICE_CAP - 0.5))
        stats[mkt] = dict(vwap=w, avg=avg, ev=ev, so=so, cap=cap, prev=pw)
        rows.append(f"| {label} | {_rs(w)} | {_pct(w, pw)} | {_rs(avg)} | {_rs(so)} | {_rs(ev)} | {cap} |")

    if "dam" in stats:
        s = stats["dam"]
        lines += ["## The number", "",
                  f"**DAM cleared at {_rs(s['vwap'])} volume-weighted ({_pct(s['vwap'], s['prev'])} w/w).** "
                  f"The simple block average was {_rs(s['avg'])}: cheap, high-volume solar blocks "
                  f"({_rs(s['so'])}) pull the weighted price well below the evening peak ({_rs(s['ev'])}). "
                  f"{s['cap']} of {7 * 96} DAM blocks cleared at the ₹10/kWh ceiling.", ""]
    if rows:
        lines += ["## Spot markets", "",
                  "| Market | VWAP | w/w | Block avg | Solar 09–16h | Evening 18–23h | Blocks at cap |",
                  "|---|---|---|---|---|---|---|", *rows, ""]

    # Battery index.
    bess = [r for r in store.read_table(derive.DAILY_TABLE) if start.isoformat() <= r["date"] <= end.isoformat()]
    if bess:
        lines += ["## Dhruva BESS-IN", ""]
        for name in ("DBX-2H", "DBX-4H", "DBX-RTM-2H"):
            vals = [float(r["revenue_rs_per_mw"]) for r in bess if r["index"] == name and r["revenue_rs_per_mw"]]
            if vals:
                lines.append(f"- **{name}** earned ₹{sum(vals):,.0f}/MW over the week "
                             f"(₹{np.mean(vals):,.0f}/MW/day, a run-rate of "
                             f"₹{np.mean(vals) * 365 / 12 / 1e5:.2f} lakh/MW/month).")
        lines += ["- For scale: Aug 2026 BESS tenders cleared at ₹2.32 (GUVNL, 2h) and ₹4.35–4.39 "
                  "(WBSEDCL, 4h) lakh/MW/month. The index is a perfect-foresight ceiling; see the methodology.", ""]

    # Futures.
    fut = store.read_table("futures")
    wk = sorted([r for r in fut if start.isoformat() <= r["snapshot_date"] <= end.isoformat()],
                key=lambda r: r["snapshot_date"])
    if wk:
        lines += ["## Futures", ""]
        for m in sorted({r["delivery_month"] for r in wk}):
            pts = [r for r in wk if r["delivery_month"] == m and (r["last"] or r["prev_close"])]
            if pts:
                px = float(pts[-1]["last"] or pts[-1]["prev_close"])
                lines.append(f"- NSE {m}: ₹{px:,.0f}/MWh at {pts[-1]['snapshot_date']}.")
        lines.append("")

    lines += _grid_lines(start, end)

    rec = [r for r in store.read_table("rec_sessions") if start.isoformat() <= r["session_date"] <= end.isoformat()]
    tenders = [r for r in store.read_table("reference/tenders") if start.isoformat() <= r["result_date"] <= end.isoformat()]
    if rec or tenders:
        lines += ["## Also this week", ""]
        lines += [f"- REC session {r['session_date']}: {int(r['cleared_volume']):,} RECs cleared at ₹{r['price_rs_per_rec']}."
                  for r in rec]
        lines += [f"- Tender: {r['authority']} {r['title']}: {r['tariff_low']}–{r['tariff_high']} {r['unit']}."
                  for r in tenders]
        lines.append("")
    lines += ["## Analyst view", "", "_Two paragraphs from the desk go here before publishing._", ""]
    return end, "\n".join(lines)


def _grid_lines(start: date, end: date) -> list[str]:
    """Frequency and the biggest DSM payer from the latest RPC accounts on or before the week.

    RPC accounts arrive about two weeks late, so the note quotes the latest
    published week and says which one it is.
    """
    from . import grid
    from .sources.rpc import group_of
    weeks = [w for w in grid.load_weeks() if w["period"]["from"] <= end.isoformat()]
    if not weeks:
        return []
    days: dict[str, list[float]] = {}
    for w in weeks:
        b = w.get("blocks") or {}
        if b.get("status") in ("ok", "partial"):
            for d, f in zip(b["dates"], b["frequency_hz"]):
                if d <= end.isoformat():
                    days[d] = [x for x in f if x is not None]
    out = []
    recent = sorted(days)[-7:]
    if recent:
        allf = [x for d in recent for x in days[d]]
        inband = sum(49.90 <= x <= 50.05 for x in allf) / len(allf) * 100
        out.append(f"- **Frequency, {recent[0]} to {recent[-1]}** (latest published RPC data): {inband:.0f}% of 15-minute "
                   f"blocks within 49.90–50.05 Hz; lowest block {min(allf):.2f} Hz, highest {max(allf):.2f} Hz.")
    latest_to = max(w["period"]["to"] for w in weeks)
    payers = []
    for w in weeks:
        sec = w.get("dsm") or {}
        if w["period"]["to"] == latest_to and sec.get("status") in ("ok", "source_mismatch"):
            for r in sec["rows"]:
                if group_of(r.get("category")) not in ("Inter-regional", "Cross-border"):
                    payers.append(((r.get("payable_rs") or 0) - (r.get("receivable_rs") or 0), r["name"], w["rpc"]))
    if payers:
        net, name, rpc_name = max(payers)
        out.append(f"- **Biggest DSM payer, week to {latest_to}:** {name} ({rpc_name}), ₹{net / 1e7:.2f} crore net payable "
                   "to the deviation pool (ERPC, WRPC and NERPC accounts).")
    return ["## Grid & balancing", "", *out, ""] if out else []


def write(week_ending: date | None = None) -> str:
    end, md = draft(week_ending)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    path = NOTES_DIR / f"{end.isoformat()}.md"
    # Never overwrite a note an analyst has edited.
    if path.exists() and "_Two paragraphs from the desk go here" not in path.read_text():
        return f"kept edited {path.name}"
    path.write_text(md)
    return f"wrote {path.name}"
