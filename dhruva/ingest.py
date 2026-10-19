"""Incremental ingestion: fetch only what is missing (plus a short revision window)."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from . import store
from .config import HISTORY_START, MARKETS
from .sources import iex, nse

log = logging.getLogger(__name__)

REVISION_DAYS = 2   # always refetch the most recent days (RTM is intraday; IEX revises)
UMCP_START = date(2026, 1, 1)   # earliest date the UMCP CSVs exist


def _missing_months(dataset: str, start: date, end: date) -> list[tuple[date, date]]:
    have = store.complete_days(dataset)
    recent = end - timedelta(days=REVISION_DAYS)
    missing = [d for d in store.daterange(start, end) if d.isoformat() not in have or d >= recent]
    spans: dict[str, list[date]] = {}
    for d in missing:
        spans.setdefault(store.month_key(d), []).append(d)
    return [(min(v), max(v)) for _, v in sorted(spans.items())]


def ingest_spot(start: date = HISTORY_START, end: date | None = None) -> dict[str, int]:
    tomorrow = iex.tomorrow_ist()
    counts = {}
    for market, meta in MARKETS.items():
        last = end or (tomorrow if market != "rtm" else tomorrow - timedelta(days=1))
        fields = iex.BLOCK_FIELDS + (iex.GDAM_EXTRA if market == "gdam" else [])
        n = 0
        for a, b in _missing_months(market, start, last):
            rows = iex.fetch_market(market, meta["endpoint"], a, b)
            n += len(rows)
            store.write_blocks(market, rows, fields)
        counts[market] = n
    return counts


def ingest_areas(start: date = HISTORY_START, end: date | None = None) -> int:
    n = 0
    for a, b in _missing_months("dam_area", start, end or iex.tomorrow_ist()):
        rows = iex.fetch_area_prices(a, b)
        n += len(rows)
        store.write_blocks("dam_area", rows, iex.AREA_FIELDS)
    return n


def ingest_umcp(start: date = UMCP_START, end: date | None = None) -> int:
    end = end or iex.tomorrow_ist()
    have = store.complete_days("dam_umcp")
    recent = end - timedelta(days=REVISION_DAYS)
    n = 0
    for d in store.daterange(max(start, UMCP_START), end):
        if d.isoformat() in have and d < recent:
            continue
        rows = iex.fetch_umcp(d)
        if rows:
            store.write_blocks("dam_umcp", rows, iex.UMCP_FIELDS)
            n += len(rows)
    return n


def ingest_tam() -> int:
    rows = iex.fetch_tam_monthly()
    return store.upsert_table("tam_monthly", rows, ["auction_date", "instrument", "delivery_month"],
                              iex.TAM_FIELDS)


def ingest_rec(years: list[int] | None = None) -> int:
    today = date.today()
    years = years or [today.year]
    rows = [r for y in years for r in iex.fetch_rec(y)]
    return store.upsert_table("rec_sessions", rows, ["session_date", "type"], iex.REC_FIELDS)


def ingest_futures(snapshot: date | None = None) -> int:
    rows = nse.fetch(snapshot or (iex.tomorrow_ist() - timedelta(days=1)))
    return store.upsert_table("futures", rows, ["snapshot_date", "exchange", "expiry"], nse.FUTURES_FIELDS)


def ingest_landed_cost(max_age_days: int = 30, force: bool = False) -> int:
    existing = store.read_table("reference/open_access_landed_cost")
    if existing and not force:
        age = (date.today() - date.fromisoformat(existing[0]["fetched"])).days
        if age < max_age_days:
            log.info("landed cost is %d days old; skipping", age)
            return 0
    rows = iex.fetch_landed_cost()
    today = date.today().isoformat()
    for r in rows:
        r["fetched"] = today
    path = "reference/open_access_landed_cost"
    if rows:
        # Replace wholesale so discontinued discoms drop out.
        (store.DATA_DIR / f"{path}.csv").unlink(missing_ok=True)
        store.upsert_table(path, rows, ["state", "category", "voltage_kv"], iex.LANDED_FIELDS)
    return len(rows)


def run_all(backfill_from: date = HISTORY_START, landed: bool = True) -> dict:
    """Daily job. Each source is independent; one failing never blocks the rest."""
    results: dict[str, object] = {}
    steps = [
        ("spot", lambda: ingest_spot(backfill_from)),
        ("areas", lambda: ingest_areas(backfill_from)),
        ("umcp", ingest_umcp),
        ("tam", ingest_tam),
        ("rec", lambda: ingest_rec(list(range(backfill_from.year, date.today().year + 1)))),
        ("futures", ingest_futures),
    ]
    if landed:
        steps.append(("landed_cost", ingest_landed_cost))
    for name, fn in steps:
        try:
            results[name] = fn()
        except Exception as exc:  # noqa: BLE001 - report and continue
            log.exception("ingest %s failed", name)
            results[name] = f"FAILED: {exc}"
    return results
