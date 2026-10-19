"""NSE monthly electricity futures (ELECMBL) live snapshot.

NSE serves no history for these contracts on its public API, so the daily job
appends one snapshot per trading day; the series grows from first run.
"""
from __future__ import annotations

from datetime import date, datetime

from .. import http
from ..config import NSE_COMMODITY_API, NSE_HOME

FUTURES_FIELDS = ["snapshot_date", "exchange", "contract", "expiry", "delivery_month",
                  "last", "prev_close", "open", "high", "low", "change_pct",
                  "volume_lots", "turnover_rs", "open_interest"]


def parse(payload: dict, snapshot: date) -> list[dict]:
    out = []
    for r in payload.get("data") or []:
        if r.get("contract") != "ELECMBL" or r.get("instrumentType") != "FUTENR":
            continue
        expiry = datetime.strptime(r["expiryDate"], "%d-%b-%Y").date()
        out.append({
            "snapshot_date": snapshot.isoformat(), "exchange": "NSE", "contract": "ELECMBL",
            "expiry": expiry.isoformat(), "delivery_month": f"{expiry.year:04d}-{expiry.month:02d}",
            "last": r.get("lastPrice") or "", "prev_close": r.get("prevClose") or "",
            "open": r.get("openPrice") or "", "high": r.get("highPrice") or "",
            "low": r.get("lowPrice") or "", "change_pct": round(r.get("pChange") or 0, 3),
            "volume_lots": r.get("numberOfContractsTraded") or 0,
            "turnover_rs": r.get("totalTurnover") or 0, "open_interest": r.get("openInterest") or 0,
        })
    return out


def fetch(snapshot: date) -> list[dict]:
    http.warm(NSE_HOME)
    payload = http.get_json(NSE_COMMODITY_API, {"index": "ELECMBL"},
                            headers={"Referer": "https://www.nseindia.com/market-data/commodity-derivatives"})
    return parse(payload, snapshot)
