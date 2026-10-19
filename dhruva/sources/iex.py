"""Indian Energy Exchange adapters.

All of these read IEX's public market-data website / the JSON API that backs
it. Dates go to IEX as dd-mm-yyyy and come back the same way; we store ISO.
"""
from __future__ import annotations

import csv
import io
import logging
import re
from datetime import date, datetime, timedelta, timezone

from .. import http
from ..config import BID_AREAS, IEX_API, IEX_UMCP_CSV, IEX_WEB
from ..store import month_end, month_starts
from .html import tables

log = logging.getLogger(__name__)

BLOCK_FIELDS = ["purchase_bid_mw", "sell_bid_mw", "mcv_mw", "scheduled_mw", "mcp", "congestion"]
GDAM_EXTRA = ["solar_mw", "wind_mw", "hydro_mw"]
AREA_FIELDS = list(BID_AREAS)
UMCP_FIELDS = ["umcp", "umcv_mw"]


def _ddmmyyyy(d: date) -> str:
    return d.strftime("%d-%m-%Y")


def _iso(ddmmyyyy: str) -> str:
    return datetime.strptime(ddmmyyyy.strip(), "%d-%m-%Y").date().isoformat()


def block_of(period: str) -> int:
    """'00:00 - 00:15', '10:00-10:15' or '23:45' -> 1..96 (block containing start)."""
    start = period.split("-")[0].strip()
    hh, mm = (int(x) for x in start.split(":"))
    return hh * 4 + mm // 15 + 1


def _f(v) -> str:
    if v is None or v == "" or v == "-":
        return ""
    return f"{float(v):.2f}"


def _chunks(start: date, end: date):
    """Calendar-month windows (the API happily returns a month per call)."""
    for m in month_starts(start, end):
        yield max(m, start), min(month_end(m), end)


def normalise_snapshot(market: str, rec: dict) -> dict:
    row = {"date": _iso(rec["date"]), "block": block_of(rec["period"]),
           "congestion": rec.get("congestion", "")}
    if market == "gdam":
        row.update(
            purchase_bid_mw=_f(rec.get("purchase_bid")),
            sell_bid_mw=_f(rec.get("total_sell_bid")),
            mcv_mw=_f(rec.get("total_unconstrained_m_c_v")),
            scheduled_mw=_f(rec.get("total_cleared_volume")),
            mcp=_f(rec.get("unconstrained_m_c_p")),
            # IEX reports solar under "other RE"; DRE is distributed RE.
            solar_mw=_f(rec.get("other_re_cleared_volume")),
            wind_mw=_f(rec.get("wind_cleared_volume")),
            hydro_mw=_f(rec.get("hydro_cleared_volume")),
        )
    else:
        row.update(
            purchase_bid_mw=_f(rec.get("purchase_bid")),
            sell_bid_mw=_f(rec.get("sell_bid")),
            mcv_mw=_f(rec.get("mcv")),
            scheduled_mw=_f(rec.get("final_scheduled_volume")),
            mcp=_f(rec.get("mcp")),
        )
    return row


def fetch_market(market: str, endpoint: str, start: date, end: date) -> list[dict]:
    rows: list[dict] = []
    for a, b in _chunks(start, end):
        payload = http.get_json(f"{IEX_API}/{endpoint}", {
            "interval": "ONE_FOURTH_HOUR", "fromDate": _ddmmyyyy(a), "toDate": _ddmmyyyy(b)})
        data = payload.get("data") or []
        rows.extend(normalise_snapshot(market, r) for r in data)
        log.info("iex %s %s..%s: %d blocks", market, a, b, len(data))
    return rows


def fetch_area_prices(start: date, end: date) -> list[dict]:
    rows: list[dict] = []
    areas = ",".join(BID_AREAS)
    for a, b in _chunks(start, end):
        payload = http.get_json(f"{IEX_API}/dam/area-price", {
            "interval": "ONE_FOURTH_HOUR", "fromDate": _ddmmyyyy(a), "toDate": _ddmmyyyy(b),
            "bidArea": areas})
        for r in payload.get("data") or []:
            row = {"date": _iso(r["date"]), "block": block_of(r["timeperiod"])}
            for area in BID_AREAS:
                row[area] = _f(r.get(area.lower()))
            rows.append(row)
        log.info("iex area prices %s..%s", a, b)
    return rows


def parse_umcp_csv(day: date, text: str) -> list[dict]:
    rows = []
    for rec in csv.reader(io.StringIO(text)):
        if not rec or not re.match(r"^\d{2}:\d{2}", rec[0].strip()):
            continue
        rows.append({"date": day.isoformat(), "block": block_of(rec[0]),
                     "umcp": _f(rec[1]), "umcv_mw": _f(rec[2]) if len(rec) > 2 else ""})
    return rows


def fetch_umcp(day: date) -> list[dict]:
    """Unconstrained DAM MCP/MCV for one delivery day (the futures settlement basis)."""
    try:
        text = http.get_text(IEX_UMCP_CSV.format(ddmmyyyy=day.strftime("%d%m%Y")), retries=1)
    except http.FetchError:
        return []
    return parse_umcp_csv(day, text)


# ------------------------------------------------------------- term-ahead

TAM_FIELDS = ["auction_date", "instrument", "buy_bids_mu", "sell_bids_mu", "volume_mu",
              "price_rs_mwh", "delivery_month"]


def parse_tam_monthly(html: str) -> list[dict]:
    out = []
    for t in tables(html):
        if not t or "Instrument Name" not in t[0]:
            continue
        for r in t[1:]:
            if len(r) < 9 or not re.match(r"\d{2}-\d{2}-\d{4}", r[0]):
                continue
            out.append({
                "auction_date": _iso(r[0]), "instrument": r[1],
                "buy_bids_mu": r[4], "sell_bids_mu": r[5], "volume_mu": r[6],
                "price_rs_mwh": r[7], "delivery_month": r[8],
            })
    return out


def fetch_tam_monthly() -> list[dict]:
    return parse_tam_monthly(http.get_text(f"{IEX_WEB}/tam-monthly"))


# ------------------------------------------------------------- RECs

REC_FIELDS = ["session_date", "type", "buy_bids", "sell_bids", "cleared_volume",
              "price_rs_per_rec", "participants"]


def parse_rec(html: str) -> list[dict]:
    out = []
    for t in tables(html):
        if not t or "Cleared Price(Rs/REC)" not in " ".join(t[0]):
            continue
        for r in t[1:]:
            # Leading cells vary with rowspans: [year?] month+date, type, 5 numbers.
            idx = next((i for i, c in enumerate(r) if re.search(r"\d{2}-\d{2}-\d{4}$", c)), None)
            if idx is None or len(r) < idx + 7:
                continue
            nums = r[idx + 2: idx + 7]
            if any(n in ("-", "") for n in nums):
                continue
            out.append({
                "session_date": _iso(r[idx][-10:]),
                "type": r[idx + 1].rstrip("*"),
                "buy_bids": nums[0], "sell_bids": nums[1], "cleared_volume": nums[2],
                "price_rs_per_rec": nums[3], "participants": nums[4],
            })
    return out


def fetch_rec(year: int) -> list[dict]:
    html = http.get_text(f"{IEX_WEB}/market-data/REC-market-from-dec22", {
        "viewGraph": "false", "fromDate": 1, "toDate": 12, "instrumentType": "BOTH", "year": year})
    return parse_rec(html)


# ------------------------------------------------------------- landed cost

OA_PREFERRED_SLOT = "RTC (24 hrs)"
OA_VOLTAGES = (11, 33, 132)
OA_PROBE_PRICES = (2.0, 6.0)   # Rs/kWh; landed cost is linear in exchange price

FALLBACK_STATES = [
    "Andhra Pradesh (CPDCL)", "Assam", "Bihar", "Chhattisgarh", "Delhi (BRPL)", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka (BESCOM)", "Kerala",
    "Madhya Pradesh", "Maharashtra (MSEDCL)", "Odisha (TPCODL)", "Punjab", "Rajasthan",
    "Tamilnadu", "Telangana (SPDCL)", "Uttar Pradesh", "Uttarakhand", "West Bengal",
]


def _values(payload) -> list:
    data = payload.get("data") or {}
    return list(data.values()) if isinstance(data, dict) else list(data)


def oa_states() -> list[str]:
    """IEX lists the valid discoms in its validation error; use that list."""
    try:
        http.get_json(f"{IEX_API}/calculator/consumer-category", {"state": "?"}, retries=0)
    except http.FetchError as exc:
        cause = exc.__cause__
        body = cause.read().decode() if hasattr(cause, "read") else ""
        m = re.search(r"one of the following values: (.*?)\"", body)
        if m:
            return sorted(s.strip() for s in m.group(1).split(", ") if s.strip())
    return FALLBACK_STATES


def fetch_landed_cost(states: list[str] | None = None) -> list[dict]:
    """For each discom x category x voltage, fit landed = a + b * exchange price."""
    out = []
    for state in states or oa_states():
        try:
            cats = _values(http.get_json(f"{IEX_API}/calculator/consumer-category", {"state": state}))
        except http.FetchError as exc:
            log.warning("landed cost %s: %s", state, exc)
            continue
        for cat in cats:
            try:
                volts = _values(http.get_json(f"{IEX_API}/calculator/voltage",
                                              {"state": state, "consumerCategory": cat}))
            except http.FetchError:
                continue
            for v in [x for x in volts if int(x) in OA_VOLTAGES]:
                base = {"state": state, "consumerCategory": cat, "voltage": v}
                try:
                    months = _values(http.get_json(f"{IEX_API}/calculator/tod-months", base))
                    month = months[0] if months else "All Months"
                    slots = _values(http.get_json(f"{IEX_API}/calculator/tod-slots", {**base, "month": month}))
                    slot = OA_PREFERRED_SLOT if OA_PREFERRED_SLOT in slots else (slots[0] if slots else None)
                    if slot is None:
                        continue
                    res = [http.get_json(f"{IEX_API}/calculator", {
                        **base, "todMonth": month, "todSlot": slot, "iexPrice": p})["data"]
                        for p in OA_PROBE_PRICES]
                except (http.FetchError, KeyError, TypeError) as exc:
                    log.warning("landed cost %s/%s/%s: %s", state, cat, v, exc)
                    continue
                (p1, p2), (r1, r2) = OA_PROBE_PRICES, res
                slope = (r2["landCost"] - r1["landCost"]) / (p2 - p1)
                discom = sum(float(r1.get(k) or 0) for k in ("energyCharge", "fsaCharge", "todCharge", "fuelCharge"))
                out.append({
                    "state": state, "category": cat, "voltage_kv": int(v), "tod_slot": slot,
                    "intercept_rs_kwh": round(r1["landCost"] - slope * p1, 4),
                    "slope": round(slope, 4),
                    "ists_charge": r1.get("istsCharge"), "stu_charge": r1.get("stuCharge"),
                    "wheeling_charge": r1.get("wheelingCharge"),
                    "css": r1.get("crossSubsidyCharge"), "additional_surcharge": r1.get("additionalSurcharge"),
                    "other_charges": r1.get("otherCharges"),
                    "ists_loss_pct": r1.get("istsLoss"), "stu_loss_pct": r1.get("stuLoss"),
                    "wheeling_loss_pct": r1.get("wheelingLoss"),
                    "discom_tariff_rs_kwh": round(discom, 4),
                })
        log.info("landed cost %s: %d rows so far", state, len(out))
    return out


LANDED_FIELDS = ["state", "category", "voltage_kv", "tod_slot", "intercept_rs_kwh", "slope",
                 "ists_charge", "stu_charge", "wheeling_charge", "css", "additional_surcharge",
                 "other_charges", "ists_loss_pct", "stu_loss_pct", "wheeling_loss_pct",
                 "discom_tariff_rs_kwh", "fetched"]


def tomorrow_ist() -> date:
    """DAM for D+1 is published around 13:00 IST; asking for it early returns nothing."""
    now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    return now_ist.date() + timedelta(days=1)
