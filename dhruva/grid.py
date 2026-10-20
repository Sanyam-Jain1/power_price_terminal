"""Grid & balancing ingestion: RPC weekly accounts plus a status registry for every source.

Outputs (all JSON, under data/grid/):
  weeks/<rpc>_<week-start>.json   one parsed settlement week per RPC
  sources.json                    every source we use or tried: status, last checked, data through
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import http
from .config import DATA_DIR
from .sources import rpc

log = logging.getLogger(__name__)

GRID_DIR = DATA_DIR / "grid"
WEEKS_DIR = GRID_DIR / "weeks"
SOURCES_FILE = GRID_DIR / "sources.json"
PARSER_VERSION = "1.3"
IST = timezone(timedelta(hours=5, minutes=30))
SECTIONS = ("dsm", "sras", "tras_market", "tras_shortfall", "blocks", "tras_prices")


def _now() -> str:
    return datetime.now(IST).isoformat(timespec="minutes")


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str))


def _needs_parse(existing: dict | None, week: rpc.Week) -> bool:
    if not existing or existing.get("parser_version") != PARSER_VERSION:
        return True
    # Compare titles, not URLs: ERPC's links are signed tokens that change on every page load,
    # while a revised account always gets a new title or file name.
    old = {k: d["title"] for k, d in existing.get("documents", {}).items()}
    new = {k: d["title"] for k, d in week.docs.items()}
    return old != new


def _summarise(problems: list[tuple]) -> str:
    """One line per (section, status): the latest week's message and how many weeks share it."""
    by: dict[tuple, list] = {}
    for sec, st, start, msg in problems:
        by.setdefault((sec, st), []).append((start, msg))
    out = []
    for (sec, st), items in by.items():
        items.sort(reverse=True)
        label = {"dsm": "DSM account", "sras": "SRAS", "tras_market": "TRAS (AS markets)",
                 "tras_shortfall": "TRAS (shortfall)", "blocks": "block-wise data", "tras_prices": "TRAS prices"}.get(sec, sec)
        weeks = ", ".join(f"{d:%d %b}" for d, _ in items)
        out.append(f"{label} – {'totals do not tie' if st == 'source_mismatch' else 'could not parse'} "
                   f"(weeks of {weeks}). Latest: {items[0][1]}")
    return " ".join(out)


def ingest(limit_weeks: int = 4) -> dict:
    """Fetch and parse the latest weeks from every reachable RPC; record every source's status."""
    registry: list[dict] = []
    counts: dict[str, object] = {}
    for name, meta in rpc.RPCS.items():
        entry = {"id": name, "name": f"{name} weekly DSM, SRAS and TRAS accounts",
                 "publisher": f"{meta['region']} Regional Power Committee", "url": meta["listing"],
                 "last_checked": _now(), "kind": "rpc"}
        try:
            weeks = meta["weeks"](limit_weeks)
        except Exception as exc:  # noqa: BLE001 - one RPC failing never stops the others
            entry.update(status="unreachable", message=f"listing page failed: {exc}")
            registry.append(entry)
            counts[name] = "unreachable"
            continue
        if not weeks:
            entry.update(status="parse_error", message="no weekly accounts found on the listing page")
            registry.append(entry)
            continue
        parsed, problems = 0, []
        for w in weeks:
            path = WEEKS_DIR / f"{w.key}.json"
            existing = _read(path)
            if not _needs_parse(existing, w):
                rec = existing
            else:
                try:
                    sections = meta["parse"](w)
                except Exception as exc:  # noqa: BLE001
                    sections = {"dsm": {"status": "parse_error", "message": str(exc), "rows": []}}
                rec = {"rpc": name, "region": meta["region"], "period": {"from": w.start.isoformat(), "to": w.end.isoformat()},
                       "listing": w.listing, "documents": w.docs, "fetched": _now(), "parser_version": PARSER_VERSION,
                       **{k: v for k, v in sections.items() if k in SECTIONS}}
                _write(path, rec)
                parsed += 1
            for sec in SECTIONS:
                st = (rec.get(sec) or {}).get("status")
                if st in ("parse_error", "source_mismatch"):
                    problems.append((sec, st, w.start, rec[sec].get("message") or ""))
        latest = weeks[0]
        entry.update(status="ok" if not problems else "partial", data_through=latest.end.isoformat(),
                     latest_period={"from": latest.start.isoformat(), "to": latest.end.isoformat()},
                     documents=latest.docs, message=_summarise(problems))
        registry.append(entry)
        counts[name] = parsed
    for key, meta in rpc.UNAVAILABLE.items():
        ok, err = rpc.probe(meta["probe"])
        status = "check" if ok else ("blocked" if "401" in err or "403" in err else
                                     "not_published" if meta["probe"] is None else "unreachable")
        registry.append({"id": key, "kind": "external", "name": meta["name"], "publisher": meta["publisher"],
                         "url": meta["url"], "last_checked": _now(), "status": status,
                         "message": ("Responded this run; an adapter is not yet written." if ok else meta["reason"])})
    _write(SOURCES_FILE, {"generated": _now(), "sources": registry})
    return counts


def load_weeks() -> list[dict]:
    out = []
    for p in sorted(WEEKS_DIR.glob("*.json")):
        rec = _read(p)
        if rec:
            out.append(rec)
    return out


def load_sources() -> dict:
    return _read(SOURCES_FILE) or {"generated": None, "sources": []}


# Re-exported for the CLI's "--only grid".
FetchError = http.FetchError
