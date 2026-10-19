"""Month-partitioned CSV storage under data/.

Block datasets live at data/<dataset>/<YYYY-MM>.csv with one row per
(date, block). Flat tables (REC sessions, futures snapshots...) live at
data/<name>.csv and are upserted by key.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

import numpy as np

from .config import BLOCKS_PER_DAY, DATA_DIR


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def month_starts(start: date, end: date) -> list[date]:
    out, cur = [], date(start.year, start.month, 1)
    while cur <= end:
        out.append(cur)
        cur = date(cur.year + (cur.month == 12), cur.month % 12 + 1, 1)
    return out


def month_end(d: date) -> date:
    nxt = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return nxt - timedelta(days=1)


def daterange(start: date, end: date) -> Iterable[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


# ---------------------------------------------------------------- block data

def block_file(dataset: str, ym: str, root: Path = DATA_DIR) -> Path:
    return root / dataset / f"{ym}.csv"


def write_blocks(dataset: str, rows: list[dict], fields: list[str], root: Path = DATA_DIR) -> int:
    """Merge rows (keyed by date+block) into their month files. Returns rows written."""
    by_month: dict[str, dict[tuple, dict]] = defaultdict(dict)
    for r in rows:
        by_month[r["date"][:7]][(r["date"], int(r["block"]))] = r
    n = 0
    for ym, new in by_month.items():
        path = block_file(dataset, ym, root)
        merged = {(r["date"], int(r["block"])): r for r in _read_csv(path)}
        merged.update(new)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["date", "block", *fields], extrasaction="ignore")
            w.writeheader()
            for key in sorted(merged):
                w.writerow(merged[key])
                n += 1
    return n


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def read_blocks(dataset: str, start: date, end: date, root: Path = DATA_DIR) -> list[dict]:
    out = []
    s, e = start.isoformat(), end.isoformat()
    for m in month_starts(start, end):
        for r in _read_csv(block_file(dataset, month_key(m), root)):
            if s <= r["date"] <= e:
                out.append(r)
    out.sort(key=lambda r: (r["date"], int(r["block"])))
    return out


def complete_days(dataset: str, root: Path = DATA_DIR) -> set[str]:
    """Dates that have all 96 blocks stored."""
    counts: dict[str, int] = defaultdict(int)
    folder = root / dataset
    if not folder.exists():
        return set()
    for path in folder.glob("*.csv"):
        for r in _read_csv(path):
            counts[r["date"]] += 1
    return {d for d, c in counts.items() if c >= BLOCKS_PER_DAY}


def _num(v: str | None) -> float:
    if v is None or v == "":
        return np.nan
    return float(v)


def block_matrix(dataset: str, field: str, start: date, end: date,
                 root: Path = DATA_DIR) -> tuple[list[str], np.ndarray]:
    """Return (dates, array[days, 96]) for one numeric field; NaN where missing.

    Only dates with at least one stored block are returned.
    """
    rows = read_blocks(dataset, start, end, root)
    days = sorted({r["date"] for r in rows})
    idx = {d: i for i, d in enumerate(days)}
    mat = np.full((len(days), BLOCKS_PER_DAY), np.nan)
    for r in rows:
        mat[idx[r["date"]], int(r["block"]) - 1] = _num(r.get(field))
    return days, mat


def latest_date(dataset: str, root: Path = DATA_DIR) -> date | None:
    folder = root / dataset
    files = sorted(folder.glob("*.csv")) if folder.exists() else []
    for path in reversed(files):
        rows = _read_csv(path)
        if rows:
            return date.fromisoformat(max(r["date"] for r in rows))
    return None


# ---------------------------------------------------------------- flat tables

def read_table(name: str, root: Path = DATA_DIR) -> list[dict]:
    return _read_csv(root / f"{name}.csv")


def upsert_table(name: str, rows: list[dict], key: list[str], fields: list[str],
                 root: Path = DATA_DIR) -> int:
    path = root / f"{name}.csv"
    merged = {tuple(r[k] for k in key): r for r in _read_csv(path)}
    for r in rows:
        merged[tuple(str(r[k]) for k in key)] = {f: r.get(f, "") for f in fields}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for k in sorted(merged):
            w.writerow(merged[k])
    return len(merged)
