"""Write the static site's JSON (site/data/*.json) from data/."""
from __future__ import annotations

import csv
import json
import shutil
import math
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from . import __version__, derive, grid, store
from .analytics import indices
from .analytics.bess import Spec, optimise_day
from .sources import rpc
from .config import (BESS_FEE_RS_PER_MWH, BESS_REGIONAL_SPEC, BESS_RTE, BESS_VARIANTS, BID_AREA_STATES,
                     BID_AREAS, DATA_DIR, HISTORY_START, MARKETS, NOTES_DIR, SITE_DATA_DIR)

RECENT_DAYS = 35
REGION_DAYS = 400
IST = timezone(timedelta(hours=5, minutes=30))


def _clean(x, nd: int | None = 0):
    if x is None:
        return None
    if isinstance(x, (float, np.floating)):
        if not math.isfinite(x):
            return None
        return round(float(x), nd) if nd is not None else float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


def _arr(a, nd: int = 0) -> list:
    return [_clean(float(v), nd) for v in np.asarray(a, dtype=float)]


def _write(name: str, obj, out: Path) -> int:
    path = out / name
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, separators=(",", ":"), allow_nan=False)
    path.write_text(text)
    return len(text)


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ spot

VOLUME_FIELD = "scheduled_mw"


def build_spot(end: date) -> tuple[dict, dict]:
    spot, history = {}, {}
    for m, meta in MARKETS.items():
        days, mcp = store.block_matrix(m, "mcp", HISTORY_START, end)
        _, vol = store.block_matrix(m, VOLUME_FIELD, HISTORY_START, end)
        cols: dict[str, list] = defaultdict(list)
        for i, d in enumerate(days):
            s = indices.day_stats(mcp[i], vol[i])
            cols["dates"].append(d)
            for k in ("avg", "vwap", "min", "max", "evening_peak", "solar", "spread"):
                cols[k].append(_clean(s.get(k)))
            cols["cap_blocks"].append(s.get("cap_blocks", 0))
            cols["blocks"].append(s.get("blocks", 0))
            cols["volume_mwh"].append(_clean(s.get("volume_mwh")))
        recent = slice(max(0, len(days) - RECENT_DAYS), len(days))
        entry = {
            "label": meta["label"], "daily": cols,
            "recent": {"dates": days[recent], "mcp": [_arr(r) for r in mcp[recent]],
                       "vol": [_arr(r) for r in vol[recent]]},
        }
        if m == "gdam" and days:
            mix = {}
            for f in ("solar_mw", "wind_mw", "hydro_mw"):
                _, mat = store.block_matrix(m, f, date.fromisoformat(days[-1]), date.fromisoformat(days[-1]))
                mix[f] = _arr(mat[-1], 1) if len(mat) else []
            entry["latest_mix"] = {"date": days[-1], **mix}
        spot[m] = entry
        history[m] = {"dates": days, "mcp": [_arr(r) for r in mcp], "vol": [_arr(r) for r in vol]}
    return spot, history


# ------------------------------------------------------------------ regions

def build_regions(end: date) -> dict:
    start = max(HISTORY_START, end - timedelta(days=REGION_DAYS))
    mkt_days, mkt = store.block_matrix("dam", "mcp", start, end)
    mkt_idx = {d: i for i, d in enumerate(mkt_days)}
    areas = {}
    dates = None
    stack = []
    for a in BID_AREAS:
        days, mat = store.block_matrix("dam_area", a, start, end)
        dates = dates or days
        stack.append(mat)
        areas[a] = {"region": BID_AREAS[a], "states": BID_AREA_STATES[a],
                    "daily_avg": [_clean(indices._nanmean(r)) for r in mat]}
    out = {"areas": areas, "dates": dates or []}
    if dates:
        cube = np.stack(stack)                        # areas x days x 96
        spread = np.nanmax(cube, axis=0) - np.nanmin(cube, axis=0)
        out["max_spread"] = [_clean(float(np.nanmax(s))) if np.isfinite(s).any() else None for s in spread]
        out["split_blocks"] = [int(np.sum(s > 0.5)) for s in spread]
        def day_blocks(k: int) -> dict:
            day = {"date": dates[k], "blocks": {a: _arr(cube[j, k]) for j, a in enumerate(BID_AREAS)}}
            if dates[k] in mkt_idx:
                day["mkt"] = _arr(mkt[mkt_idx[dates[k]]])
            return day
        last = len(dates) - 1
        out["latest"] = day_blocks(last)
        split_days = [k for k in range(len(dates)) if out["split_blocks"][k] > 0]
        if split_days:
            out["latest_split"] = day_blocks(split_days[-1])
        out["mkt_daily_avg"] = [_clean(indices._nanmean(mkt[mkt_idx[d]])) if d in mkt_idx else None for d in dates]
    # Regional battery index, monthly Rs lakh/MW/month.
    reg = defaultdict(lambda: defaultdict(float))
    ndays = defaultdict(lambda: defaultdict(int))
    for r in store.read_table(derive.REGIONAL_TABLE):
        v = _num(r["revenue_rs_per_mw"])
        if v is not None:
            reg[r["area"]][r["date"][:7]] += v
            ndays[r["area"]][r["date"][:7]] += 1
    months = sorted({m for a in reg for m in reg[a]})
    out["bess_monthly"] = {"months": months, "spec": BESS_REGIONAL_SPEC,
                           "areas": {a: [_clean(reg[a].get(m, float("nan")) / 1e5, 3) for m in months] for a in BID_AREAS},
                           "days": {a: [ndays[a].get(m, 0) for m in months] for a in BID_AREAS}}
    return out


# ------------------------------------------------------------------ futures & index

def build_futures(end: date) -> dict:
    dam_days, dam_p = store.block_matrix("dam", "mcp", HISTORY_START, end)
    _, dam_v = store.block_matrix("dam", "mcv_mw", HISTORY_START, end)
    u_days, u_p = store.block_matrix("dam_umcp", "umcp", HISTORY_START, end)
    _, u_v = store.block_matrix("dam_umcp", "umcv_mw", HISTORY_START, end)
    u_idx = {d: i for i, d in enumerate(u_days)}
    # Prefer UMCP (the settlement basis); fall back to cleared MCP/MCV before UMCP history.
    P, V = [], []
    umcp_days: dict[str, int] = defaultdict(int)
    for i, d in enumerate(dam_days):
        j = u_idx.get(d)
        if j is not None and np.isfinite(u_p[j]).all() and np.isfinite(u_v[j]).all():
            P.append(u_p[j]); V.append(u_v[j]); umcp_days[d[:7]] += 1
        else:
            P.append(dam_p[i]); V.append(dam_v[i])
    monthly = indices.monthly_index(dam_days, np.array(P), np.array(V)) if dam_days else {}
    dbi = []
    for ym, rec in sorted(monthly.items()):
        y, m = int(ym[:4]), int(ym[5:])
        dim = (store.month_end(date(y, m, 1))).day
        u = umcp_days.get(ym, 0)
        basis = "UMCP" if u == rec["days"] else ("MCP" if u == 0 else f"UMCP {u}/{rec['days']} days")
        dbi.append({"month": ym, "vwap": _clean(rec.get("vwap")), "days": rec["days"], "days_in_month": dim,
                    "umcp_days": u, "basis": basis, "mtd": [[d, _clean(v)] for d, v in rec["mtd"]]})
    fut = store.read_table("futures")
    manual = DATA_DIR / "manual" / "mcx_futures.csv"
    if manual.exists():
        with manual.open(newline="") as fh:
            fut += list(csv.DictReader(fh))
    series = defaultdict(list)
    for r in sorted(fut, key=lambda r: r["snapshot_date"]):
        px = _num(r.get("last")) or _num(r.get("prev_close"))
        if px:
            series[(r["exchange"], r["delivery_month"])].append([r["snapshot_date"], px])
    latest_snap = max((r["snapshot_date"] for r in fut), default=None)
    latest = [{k: (_num(v) if k in ("last", "prev_close", "open", "high", "low", "change_pct", "volume_lots",
                                      "turnover_rs", "open_interest") else v) for k, v in r.items()}
              for r in fut if r["snapshot_date"] == latest_snap]
    tam = sorted(store.read_table("tam_monthly"), key=lambda r: r["auction_date"], reverse=True)
    return {
        "dbi": dbi, "latest_snapshot": latest_snap, "contracts": sorted(latest, key=lambda r: r["expiry"]),
        "series": [{"exchange": e, "month": m, "points": pts} for (e, m), pts in sorted(series.items())],
        "tam": [{**r, "price_rs_mwh": _num(r["price_rs_mwh"]), "volume_mu": _num(r["volume_mu"])} for r in tam],
    }


# ------------------------------------------------------------------ DSM

def official_blocks() -> dict[str, dict]:
    """Per date: frequency and the published Normal Rate from RPC block-wise files.

    RPCs publish area-specific rates; where they differ the most common value
    across RPCs is used (WRPC breaks ties, as the largest bid area).
    """
    per_date: dict[str, dict] = {}
    order = {"WRPC": 0, "ERPC": 1, "NERPC": 2}
    for w in sorted(grid.load_weeks(), key=lambda w: order.get(w["rpc"], 9)):
        blk = w.get("blocks") or {}
        if blk.get("status") != "ok":
            continue
        for k, d in enumerate(blk["dates"]):
            e = per_date.setdefault(d, {"nr": [], "freq": [], "sources": []})
            e["nr"].append(blk["normal_rate_rs_mwh"][k])
            e["freq"].append(blk["frequency_hz"][k])
            e["sources"].append({"rpc": w["rpc"], "title": next(iter(w["documents"].values()))["title"],
                                 "url": (w["documents"].get("blocks_xlsx") or w["documents"].get("blocks_zip")
                                         or w["documents"].get("data_zip") or {}).get("url")})
    out = {}
    for d, e in per_date.items():
        nr, fr = [], []
        for b in range(96):
            vals = [row[b] for row in e["nr"] if row[b] is not None]
            nr.append(Counter(vals).most_common(1)[0][0] if vals else None)
            fs = [row[b] for row in e["freq"] if row[b] is not None]
            fr.append(float(np.median(fs)) if fs else None)
        out[d] = {"nr": nr, "freq": fr, "sources": e["sources"]}
    return out


def build_dsm(end: date) -> dict:
    """Normal Rate per the notified CERC DSM Regulations 2024, with the ASC where it can be recovered."""
    mats = {}
    for m in ("dam", "gdam", "hpdam", "rtm"):
        days, p = store.block_matrix(m, "mcp", HISTORY_START, end)
        _, v = store.block_matrix(m, "scheduled_mw", HISTORY_START, end)
        mats[m] = ({d: i for i, d in enumerate(days)}, p, v)
    official = official_blocks()
    cols = defaultdict(list)
    latest = latest_official = None
    nonbind = matched = binding = 0
    asc_all = []
    for d, i in sorted(mats["dam"][0].items()):
        j = mats["rtm"][0].get(d)
        if j is None or not np.isfinite(mats["rtm"][1][j]).all():
            continue
        segs = [(mats[m][1][mats[m][0][d]], mats[m][2][mats[m][0][d]]) for m in ("dam", "gdam", "hpdam") if d in mats[m][0]]
        idam = indices.integrated_dam([p for p, _ in segs], [v for _, v in segs])
        rtm = mats["rtm"][1][j]
        off = official.get(d)
        off_nr = np.array([np.nan if x is None else x for x in off["nr"]]) if off else None
        asc = indices.implied_asc(off_nr, idam, rtm) if off else None
        nr = indices.dsm_normal_rate(idam, rtm, asc)
        cols["dates"].append(d)
        cols["avg"].append(_clean(float(np.nanmean(nr))))
        cols["max"].append(_clean(float(np.nanmax(nr))))
        cols["min"].append(_clean(float(np.nanmin(nr))))
        cols["asc_status"].append("published" if off else "pending")
        cols["official_avg"].append(_clean(float(np.nanmean(off_nr))) if off else None)
        if off:
            nb = ~np.isfinite(asc) & np.isfinite(off_nr)
            nonbind += int(nb.sum())
            matched += int((np.abs(np.fmax(idam, rtm) - off_nr)[nb] <= 1.0).sum())
            binding += int(np.isfinite(asc).sum())
            asc_all.extend(asc[np.isfinite(asc)].tolist())
            latest_official = (d, idam, rtm, nr, off_nr, asc, off["sources"])
        latest = (d, idam, rtm, nr)
    out = {
        "daily": cols,
        "method": ("Normal Rate = highest of (i) the integrated day-ahead ACP (DAM, G-DAM, HP-DAM volume-weighted), "
                   "(ii) the RTM ACP and (iii) (I-DAM + RTM + Ancillary Service Charge) / 3, per the notified CERC DSM "
                   "Regulations 2024. The ASC is recovered from the Normal Rate the RPCs publish in their block-wise DSM "
                   "data: where that rate sits above both market prices, ASC = 3 × NR − I-DAM − RTM. Days after the latest "
                   "published RPC week show a lower bound (market terms only) until the ASC is published."),
        "validation": {"non_binding_blocks": nonbind, "matched_within_1_rs_mwh": matched,
                       "match_share": round(matched / nonbind, 4) if nonbind else None,
                       "asc_binding_blocks": binding,
                       "asc_median_rs_mwh": _clean(float(np.median(asc_all))) if asc_all else None},
    }
    if latest:
        d, idam, rtm, nr = latest
        out["latest"] = {"date": d, "idam": _arr(idam), "rtm": _arr(rtm), "nr": _arr(nr),
                         "asc_status": "published" if d in official else "pending"}
    if latest_official:
        d, idam, rtm, nr, off_nr, asc, src = latest_official
        out["latest_official"] = {"date": d, "idam": _arr(idam), "rtm": _arr(rtm), "nr": _arr(nr),
                                  "official": _arr(off_nr), "asc": _arr(asc), "sources": src}
    return out


# ------------------------------------------------------------------ grid & balancing

EXCLUDE_FROM_PAYERS = ("Inter-regional", "Cross-border")


def build_grid(end: date) -> dict:
    weeks = grid.load_weeks()
    sources = grid.load_sources()
    official = official_blocks()
    # Frequency (15-minute block averages from RPC DSM data).
    freq_days = []
    for d in sorted(official):
        f = np.array([np.nan if x is None else x for x in official[d]["freq"]])
        ok = np.isfinite(f)
        if ok.sum() < 90:
            continue
        band = (f >= 49.90) & (f <= 50.05)
        freq_days.append({"date": d, "min": _clean(float(np.nanmin(f)), 3), "max": _clean(float(np.nanmax(f)), 3),
                          "mean": _clean(float(np.nanmean(f)), 3), "in_band_pct": _clean(float(band[ok].mean() * 100), 1),
                          "below_49_90_pct": _clean(float((f[ok] < 49.90).mean() * 100), 1),
                          "above_50_05_pct": _clean(float((f[ok] > 50.05).mean() * 100), 1),
                          "sources": official[d]["sources"]})
    frequency = {"days": freq_days}
    if freq_days:
        last = freq_days[-1]["date"]
        frequency["latest"] = {"date": last, "blocks": [_clean(x, 3) if x is not None else None for x in official[last]["freq"]]}

    latest_by_rpc: dict[str, dict] = {}
    for w in weeks:
        cur = latest_by_rpc.get(w["rpc"])
        if cur is None or w["period"]["from"] > cur["period"]["from"]:
            latest_by_rpc[w["rpc"]] = w

    def doc_list(w):
        return [{"kind": k, **v} for k, v in w.get("documents", {}).items()]

    dsm, payers, ancillary = [], [], []
    for name, w in sorted(latest_by_rpc.items()):
        sec = w.get("dsm") or {}
        entities = []
        for r in sec.get("rows", []) if sec.get("status") in ("ok", "source_mismatch", "unvalidated") else []:
            pay, rec = r.get("payable_rs") or 0, r.get("receivable_rs") or 0
            ent = {"name": r["name"], "category": r.get("category"), "group": rpc.group_of(r.get("category")),
                   "payable_rs": _clean(pay), "receivable_rs": _clean(rec), "net_rs": _clean(pay - rec),
                   "deviation_mwh": _clean(r.get("deviation_mwh"), 1), "scheduled_mwh": _clean(r.get("scheduled_mwh"), 1),
                   "actual_mwh": _clean(r.get("actual_mwh"), 1)}
            entities.append(ent)
            if ent["group"] not in EXCLUDE_FROM_PAYERS:
                payers.append({**ent, "rpc": name, "period": w["period"]})
        groups = defaultdict(lambda: {"payable_rs": 0.0, "receivable_rs": 0.0, "abs_deviation_mwh": 0.0, "entities": 0})
        for e in entities:
            g = groups[e["group"]]
            g["payable_rs"] += e["payable_rs"] or 0
            g["receivable_rs"] += e["receivable_rs"] or 0
            g["abs_deviation_mwh"] += abs(e["deviation_mwh"] or 0)
            g["entities"] += 1
        dsm.append({"rpc": name, "region": w["region"], "period": w["period"], "status": sec.get("status", "missing"),
                    "message": sec.get("message", ""), "documents": doc_list(w), "fetched": w.get("fetched"),
                    "entities": entities, "groups": {k: {kk: _clean(vv) for kk, vv in v.items()} for k, v in groups.items()}})
        anc = {"rpc": name, "region": w["region"], "period": w["period"], "documents": doc_list(w)}
        for key in ("sras", "tras_market", "tras_shortfall"):
            t = w.get(key) or {"status": "missing", "message": "not published in this RPC's files", "rows": []}
            anc[key] = {"status": t.get("status"), "message": t.get("message", ""),
                        "rows": t.get("rows", []) if t.get("status") != "parse_error" else [], "total": t.get("total")}
        if w.get("tras_prices"):
            anc["tras_prices"] = w["tras_prices"]
        ancillary.append(anc)
    payers.sort(key=lambda e: e["net_rs"] or 0, reverse=True)
    history = []
    for w in sorted(weeks, key=lambda w: (w["rpc"], w["period"]["from"])):
        sec = w.get("dsm") or {}
        rows = sec.get("rows", []) if sec.get("status") in ("ok", "source_mismatch", "unvalidated") else []
        tot = lambda key, f: _clean(((w.get(key) or {}).get("total") or {}).get(f))  # noqa: E731
        history.append({"rpc": w["rpc"], "period": w["period"], "dsm_status": sec.get("status"),
                        "payable_rs": _clean(sum(r.get("payable_rs") or 0 for r in rows)) if rows else None,
                        "receivable_rs": _clean(sum(r.get("receivable_rs") or 0 for r in rows)) if rows else None,
                        "sras_total_rs": tot("sras", "total_rs"), "sras_up_mwh": tot("sras", "up_mwh"),
                        "tras_shortfall_net_rs": tot("tras_shortfall", "net_rs"), "tras_market_net_rs": tot("tras_market", "net_rs")})
    return {"sources": sources, "frequency": frequency, "dsm": dsm, "top_payers": payers[:10],
            "ancillary": ancillary, "history": history}


# ------------------------------------------------------------------ BESS index

def build_bess(end: date) -> dict:
    rows = store.read_table(derive.DAILY_TABLE)
    by_idx = defaultdict(dict)
    for r in rows:
        by_idx[r["index"]][r["date"]] = r
    indices_out = {}
    for name, v in BESS_VARIANTS.items():
        recs = by_idx.get(name, {})
        dates = sorted(recs)
        rev = [_num(recs[d]["revenue_rs_per_mw"]) for d in dates]
        monthly = defaultdict(lambda: [0.0, 0])
        for d, x in zip(dates, rev):
            if x is not None:
                monthly[d[:7]][0] += x
                monthly[d[:7]][1] += 1
        months = []
        for ym, (tot, n) in sorted(monthly.items()):
            dim = store.month_end(date(int(ym[:4]), int(ym[5:]), 1)).day
            months.append({"month": ym, "lakh": round(tot / 1e5, 3), "days": n, "days_in_month": dim,
                           "run_rate": round(tot / n * dim / 1e5, 3) if n else None})
        last365 = [x for d, x in zip(dates, rev) if x is not None][-365:]
        indices_out[name] = {
            **v, "rte": BESS_RTE, "fee": BESS_FEE_RS_PER_MWH,
            "daily": {"dates": dates, "revenue": [_clean(x) for x in rev],
                      "cycles": [_clean(_num(recs[d]["cycles"]), 3) for d in dates],
                      "avg_buy": [_clean(_num(recs[d]["avg_buy"])) for d in dates],
                      "avg_sell": [_clean(_num(recs[d]["avg_sell"])) for d in dates]},
            "monthly": months,
            "trailing_365_lakh_per_mw_month": round(sum(last365) / len(last365) * 365 / 12 / 1e5, 3) if last365 else None,
        }
    # Dispatch for the latest delivery day, so people can see what the index did.
    dispatch = {}
    for name in ("DBX-2H", "DBX-4H"):
        v = BESS_VARIANTS[name]
        days, mat = store.block_matrix(v["market"], "mcp", end - timedelta(days=3), end)
        for i in range(len(days) - 1, -1, -1):
            res = optimise_day(mat[i], derive.spec_for(name))
            if res:
                dispatch[name] = {"date": days[i], "price": _arr(mat[i]), "charge": _arr(res.charge, 3),
                                  "discharge": _arr(res.discharge, 3), "soc": _arr(res.soc, 3),
                                  "revenue": _clean(res.revenue)}
                break
    return {"method_version": derive.METHOD_VERSION, "indices": indices_out, "dispatch": dispatch}


# ------------------------------------------------------------------ forecast

def build_forecast(end: date) -> dict:
    days, mat = store.block_matrix("dam", "mcp", end - timedelta(days=120), end)
    if len(days) < 8:
        return {}
    target = date.fromisoformat(days[-1]) + timedelta(days=1)
    return {"target_date": target.isoformat(), "method": "per-block median of the last 7 delivered days",
            "forecast": _arr(indices.baseline_forecast(mat, 7)),
            "backtest": indices.backtest_baseline(mat, 7, 60),
            "last_actual": {"date": days[-1], "mcp": _arr(mat[-1])}}


# ------------------------------------------------------------------ reference tables

def build_reference(end: date) -> dict:
    tenders = []
    for r in store.read_table("reference/tenders"):
        tenders.append({**r, "capacity_mw": _num(r["capacity_mw"]), "energy_mwh": _num(r["energy_mwh"]),
                        "tariff_low": _num(r["tariff_low"]), "tariff_high": _num(r["tariff_high"])})
    tenders.sort(key=lambda r: r["result_date"], reverse=True)
    rec = sorted(({**r, **{k: _num(r[k]) for k in ("buy_bids", "sell_bids", "cleared_volume",
                                                  "price_rs_per_rec", "participants")}}
                  for r in store.read_table("rec_sessions")), key=lambda r: r["session_date"])
    landed = [{**r, **{k: _num(v) for k, v in r.items() if k not in ("state", "category", "tod_slot", "fetched")}}
              for r in store.read_table("reference/open_access_landed_cost")]
    days, p = store.block_matrix("dam", "mcp", end - timedelta(days=30), end)
    _, v = store.block_matrix("dam", "mcv_mw", end - timedelta(days=30), end)
    ref = indices.vwap(p.ravel(), v.ravel()) / 1000 if len(days) else None
    return {"tenders": tenders, "rec": rec,
            "landed": {"rows": landed, "reference_price_rs_kwh": _clean(ref, 2),
                       "reference_note": f"30-day DAM volume-weighted price to {days[-1] if days else '-'}",
                       "fetched": landed[0]["fetched"] if landed else None}}


# ------------------------------------------------------------------ weekly notes

def build_notes() -> dict:
    notes = sorted(NOTES_DIR.glob("*.md"), reverse=True) if NOTES_DIR.exists() else []
    return {"notes": [{"week_ending": p.stem, "markdown": p.read_text()} for p in notes[:12]]}


def run(out: Path = SITE_DATA_DIR) -> dict:
    latest = store.latest_date("dam") or date.today()
    end = latest + timedelta(days=1)
    spot, history = build_spot(end)
    sizes = {"spot.json": _write("spot.json", spot, out)}
    for m, h in history.items():
        sizes[f"history/{m}.json"] = _write(f"history/{m}.json", h, out)
    for name, fn in (("regions.json", build_regions), ("futures.json", build_futures), ("dsm.json", build_dsm),
                     ("bess.json", build_bess), ("forecast.json", build_forecast),
                     ("reference.json", build_reference), ("grid.json", build_grid)):
        sizes[name] = _write(name, fn(end), out)
    sizes["notes.json"] = _write("notes.json", build_notes(), out)
    shutil.copyfile(DATA_DIR.parent / "docs" / "METHODOLOGY.md", out / "methodology.md")
    meta = {
        "version": __version__, "method_version": derive.METHOD_VERSION,
        "generated_at": datetime.now(IST).isoformat(timespec="minutes"),
        "latest": {k: (store.latest_date(k).isoformat() if store.latest_date(k) else None)
                   for k in (*MARKETS, "dam_area", "dam_umcp")},
        "history_start": HISTORY_START.isoformat(),
        "free_days": 30,
    }
    sizes["meta.json"] = _write("meta.json", meta, out)
    return sizes
