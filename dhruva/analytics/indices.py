"""Price statistics, the month-to-date settlement index, DSM Normal Rate, baseline forecast."""
from __future__ import annotations

import numpy as np

from ..config import BLOCK_HOURS, EVENING_PEAK_BLOCKS, SOLAR_BLOCKS

PRICE_CAP = 10000.0  # Rs/MWh, DAM/RTM ceiling


def _nanmean(x) -> float:
    x = np.asarray(x, dtype=float)
    return float(np.nanmean(x)) if np.isfinite(x).any() else float("nan")


def vwap(prices, volumes) -> float:
    p, v = np.asarray(prices, float), np.asarray(volumes, float)
    ok = np.isfinite(p) & np.isfinite(v) & (v > 0)
    return float((p[ok] * v[ok]).sum() / v[ok].sum()) if ok.any() else float("nan")


def day_stats(prices, volumes=None) -> dict:
    """Summary of one day's 96 block prices (Rs/MWh)."""
    p = np.asarray(prices, dtype=float)
    if not np.isfinite(p).any():
        return {}
    ev = _nanmean(p[list(EVENING_PEAK_BLOCKS)])
    so = _nanmean(p[list(SOLAR_BLOCKS)])
    out = {
        "avg": _nanmean(p),
        "min": float(np.nanmin(p)),
        "max": float(np.nanmax(p)),
        "evening_peak": ev,
        "solar": so,
        "spread": ev - so,
        "cap_blocks": int(np.sum(p >= PRICE_CAP - 0.5)),
        "blocks": int(np.isfinite(p).sum()),
    }
    if volumes is not None:
        v = np.asarray(volumes, dtype=float)
        out["vwap"] = vwap(p, v)
        out["volume_mwh"] = float(np.nansum(v) * BLOCK_HOURS)
    return out


def monthly_index(dates: list[str], prices: np.ndarray, volumes: np.ndarray) -> dict[str, dict]:
    """Volume-weighted average price per calendar month, with running MTD values.

    Returns {YYYY-MM: {"vwap": .., "days": n, "mtd": [(date, vwap_to_date), ...]}}
    """
    out: dict[str, dict] = {}
    num = den = 0.0
    cur = None
    for i, d in enumerate(dates):
        ym = d[:7]
        if ym != cur:
            cur, num, den = ym, 0.0, 0.0
            out[ym] = {"mtd": [], "days": 0}
        p, v = prices[i], volumes[i]
        ok = np.isfinite(p) & np.isfinite(v) & (v > 0)
        if not ok.any():
            continue
        num += float((p[ok] * v[ok]).sum())
        den += float(v[ok].sum())
        out[ym]["days"] += 1
        out[ym]["mtd"].append((d, num / den))
        out[ym]["vwap"] = num / den
    return out


def dsm_normal_rate(dam: np.ndarray, rtm: np.ndarray, asc: np.ndarray | None = None) -> np.ndarray:
    """CERC DSM Regulations 2024 Normal Rate per block.

    Equal thirds of DAM ACP, RTM ACP and the Ancillary Service Charge; when no
    ancillary charge is available the rate is the 50:50 DAM/RTM average.
    """
    dam, rtm = np.asarray(dam, float), np.asarray(rtm, float)
    if asc is None:
        return np.round((dam + rtm) / 2, 2)
    asc = np.asarray(asc, float)
    with_asc = (dam + rtm + asc) / 3
    return np.round(np.where(np.isfinite(asc) & (asc > 0), with_asc, (dam + rtm) / 2), 2)


def baseline_forecast(history: np.ndarray, lookback: int = 7) -> np.ndarray:
    """D+1 block forecast: per-block median of the last `lookback` days."""
    h = np.asarray(history, float)[-lookback:]
    return np.nanmedian(h, axis=0)


def backtest_baseline(mat: np.ndarray, lookback: int = 7, window: int = 60) -> dict:
    """Out-of-sample errors of the baseline over the last `window` days."""
    errs, n = [], len(mat)
    for i in range(max(lookback, n - window), n):
        f = baseline_forecast(mat[:i], lookback)
        a = mat[i]
        ok = np.isfinite(f) & np.isfinite(a)
        if ok.any():
            errs.append(np.abs(f[ok] - a[ok]))
    if not errs:
        return {}
    e = np.concatenate(errs)
    return {"mae": float(e.mean()), "days": len(errs), "lookback": lookback}
