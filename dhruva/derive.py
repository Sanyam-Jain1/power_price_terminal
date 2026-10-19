"""Compute the Dhruva BESS-IN index family incrementally into data/derived/."""
from __future__ import annotations

import logging
from datetime import date, timedelta

import numpy as np

from . import store
from .analytics.bess import Spec, optimise_day
from .config import BESS_REGIONAL_SPEC, BESS_VARIANTS, BID_AREAS, HISTORY_START

log = logging.getLogger(__name__)

METHOD_VERSION = "1.0"
REGIONAL_DAYS = 400

DAILY_TABLE = "derived/bess_daily"
DAILY_FIELDS = ["date", "index", "revenue_rs_per_mw", "cycles", "avg_buy", "avg_sell", "method_version"]
REGIONAL_TABLE = "derived/bess_regional_daily"
REGIONAL_FIELDS = ["date", "area", "revenue_rs_per_mw", "method_version"]


def spec_for(name: str) -> Spec:
    v = BESS_VARIANTS[name]
    return Spec(duration_h=v["duration_h"], cycles=v["cycles"])


def _done(table: str, key: str) -> set[tuple[str, str]]:
    return {(r["date"], r[key]) for r in store.read_table(table) if r.get("method_version") == METHOD_VERSION}


def _r(x: float, nd: int = 2) -> str:
    return "" if x is None or not np.isfinite(x) else f"{x:.{nd}f}"


def run(today: date | None = None) -> dict:
    end = (today or date.today()) + timedelta(days=1)
    done = _done(DAILY_TABLE, "index")
    new_rows, counts = [], {}
    matrices = {}
    for name, v in BESS_VARIANTS.items():
        if v["market"] not in matrices:
            matrices[v["market"]] = store.block_matrix(v["market"], "mcp", HISTORY_START, end)
        days, mat = matrices[v["market"]]
        spec = spec_for(name)
        n = 0
        for i, d in enumerate(days):
            if (d, name) in done:
                continue
            res = optimise_day(mat[i], spec)
            if res is None:
                continue
            new_rows.append({"date": d, "index": name, "revenue_rs_per_mw": _r(res.revenue),
                             "cycles": _r(res.cycles, 3), "avg_buy": _r(res.avg_buy),
                             "avg_sell": _r(res.avg_sell), "method_version": METHOD_VERSION})
            n += 1
        counts[name] = n
    if new_rows:
        store.upsert_table(DAILY_TABLE, new_rows, ["date", "index"], DAILY_FIELDS)

    # Regional: same spec against each bid area's DAM price.
    start = max(HISTORY_START, end - timedelta(days=REGIONAL_DAYS))
    done_r = _done(REGIONAL_TABLE, "area")
    spec = Spec(**BESS_REGIONAL_SPEC)
    reg_rows = []
    for area in BID_AREAS:
        days, mat = store.block_matrix("dam_area", area, start, end)
        cache: dict[bytes, float] = {}
        for i, d in enumerate(days):
            if (d, area) in done_r:
                continue
            key = mat[i].tobytes()
            if key not in cache:   # most days every area clears at one price
                res = optimise_day(mat[i], spec)
                cache[key] = res.revenue if res else float("nan")
            if np.isfinite(cache[key]):
                reg_rows.append({"date": d, "area": area, "revenue_rs_per_mw": _r(cache[key]),
                                 "method_version": METHOD_VERSION})
    if reg_rows:
        store.upsert_table(REGIONAL_TABLE, reg_rows, ["date", "area"], REGIONAL_FIELDS)
    counts["regional"] = len(reg_rows)
    return counts
