"""Grid & balancing ingestion: RPC weekly accounts plus a status registry for every source.

Outputs, under data/grid/:
  weeks/<rpc>_<week-start>.json        one parsed settlement week per RPC (JSON), including a
                                       "block_data" summary: what the block files hold and how
                                       they reconcile with the weekly account
  blocks/<dataset>/<rpc>_<start>.csv.gz  every entity, every 15-minute block (5-minute for
                                       NERPC SRAS), as published; gzip CSV because a week is
                                       ~100k rows
  sources.json                         every source we use or tried: status, last checked, data through
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import http
from .config import DATA_DIR
from .sources import rpc
from .sources import rpc_blocks as B

log = logging.getLogger(__name__)

GRID_DIR = DATA_DIR / "grid"
WEEKS_DIR = GRID_DIR / "weeks"
SOURCES_FILE = GRID_DIR / "sources.json"
BLOCKS_DIR = GRID_DIR / "blocks"
PARSER_VERSION = "2.3"
IST = timezone(timedelta(hours=5, minutes=30))
SECTIONS = ("dsm", "sras", "tras_market", "tras_shortfall", "blocks", "tras_prices", "block_data")
DATASETS = {"dsm": B.DSM_COLUMNS, "sras": B.SRAS_COLUMNS, "sras_5min": B.SRAS5_COLUMNS,
            "tras": B.TRAS_COLUMNS, "scuc": B.SCUC_COLUMNS}


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


def block_path(dataset: str, key: str) -> Path:
    return BLOCKS_DIR / dataset / f"{key}.csv.gz"


def _write_rows(path: Path, columns, rows) -> None:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(columns)
    for r in sorted(rows, key=lambda r: (r[2], r[0], r[1])):
        w.writerow(["" if v is None else (round(v, 4) if isinstance(v, float) else v) for v in r])
    path.parent.mkdir(parents=True, exist_ok=True)
    # mtime=0 keeps the bytes identical when the data is, so unchanged weeks never show up in git.
    with open(path, "wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
        gz.write(buf.getvalue().encode())


def read_rows(dataset: str, key: str) -> list[dict]:
    path = block_path(dataset, key)
    if not path.exists():
        return []
    with gzip.open(path, "rt") as fh:
        return list(csv.DictReader(fh))


def _sum(rows, i) -> float:
    return sum(r[i] or 0 for r in rows)


def _check_total(label: str, got: float, want: float | None, tol: float = 1000.0) -> dict:
    ok = want is not None and abs(got - want) <= max(tol, abs(want) * 0.002)
    return {"check": label, "summed": round(got, 2), "printed": want, "ok": ok if want is not None else None}


def _block_data(key: str, data: dict, sections: dict) -> dict:
    """Write each block dataset and reconcile it with the weekly account it underlies."""
    out = {}
    for name, res in data.items():
        cols = DATASETS[name]
        if res.get("status") != "ok":
            out[name] = {"status": "parse_error", "message": res.get("message", "")}
            continue
        rows = res["rows"]
        _write_rows(block_path(name, key), cols, rows)
        ent_i = 2
        rec = {"status": "ok", "message": res.get("message", ""), "file": str(block_path(name, key).relative_to(DATA_DIR.parent)),
               "rows": len(rows), "entities": len({r[ent_i] for r in rows}), "dates": sorted({r[0] for r in rows}),
               "checks": []}
        if name == "dsm":
            pdf = (sections.get("dsm") or {})
            if pdf.get("status") in ("ok", "source_mismatch", "unvalidated") and pdf.get("rows"):
                rc = B.reconcile(rows, pdf["rows"])
                rec["reconciliation"] = rc["summary"]
                if (pdf["status"] == "source_mismatch" and not rc["summary"]["differs"]
                        and not rc["summary"]["pdf_rows_without_block_data"]):
                    pdf["message"] += (f" Every one of the {rc['summary']['ties']} rows also ties to the RPC's block-wise data, "
                                       "so the gap is in the printed total, not in the rows.")
                rec["entity_map"] = rc["entities"]
                if rc["summary"]["differs"] or rc["summary"]["pdf_rows_without_block_data"]:
                    rec["status"] = "partial"
                    rec["message"] = (f"{rc['summary']['differs']} entities' block sums differ from the weekly account; "
                                      f"{len(rc['summary']['pdf_rows_without_block_data'])} account rows have no block data.")
            else:
                rec.update(status="unvalidated", message="weekly account not parsed, so block sums could not be checked")
            bad = [c for c in res.get("day_checks", []) if not c["ok"]]
            if res.get("day_checks"):
                rec["day_checks"] = {"checked": len(res["day_checks"]), "failed": len(bad), "examples": bad[:5]}
                if bad:
                    rec["status"] = "partial"
                    rec["message"] = (rec["message"] + f" {len(bad)} entity-days differ from the file's own daily totals.").strip()
        elif name in ("sras", "sras_5min"):
            t = (sections.get("sras") or {}).get("total") or {}
            if name == "sras":
                rec["checks"] = [_check_total("SRAS up MWh vs weekly account", _sum(rows, 3), t.get("up_mwh"), 1.0),
                                 _check_total("SRAS down MWh vs weekly account", _sum(rows, 4), t.get("down_mwh"), 1.0),
                                 _check_total("SRAS energy Rs vs weekly account", _sum(rows, 6), t.get("energy_rs"))]
            else:
                rec["checks"] = [_check_total("SRAS incentive Rs vs weekly account", _sum(rows, 6), t.get("incentive_rs"))]
        elif name == "tras":
            t = (sections.get("tras_shortfall") or {}).get("total") or {}
            rec["checks"] = [_check_total("Shortfall + emergency TRAS-Up MWh vs weekly account", _sum(rows, 15) + _sum(rows, 18), t.get("up_mwh"), 1.0)]
        failed = [c for c in rec["checks"] if c["ok"] is False]
        if failed:
            rec["status"] = "partial"
            rec["message"] = (rec["message"] + " " + "; ".join(f"{c['check']}: {c['summed']:,} summed vs {c['printed']:,} printed" for c in failed)).strip()
        out[name] = rec
    return out


def _summarise(problems: list[tuple]) -> str:
    """One line per (section, status): the latest week's message and how many weeks share it."""
    by: dict[tuple, list] = {}
    for sec, st, start, msg in problems:
        by.setdefault((sec, st), []).append((start, msg))
    out = []
    for (sec, st), items in by.items():
        items.sort(reverse=True)
        label = {"dsm": "DSM account", "sras": "SRAS", "tras_market": "TRAS (AS markets)",
                 "tras_shortfall": "TRAS (shortfall)", "blocks": "block-wise data", "tras_prices": "TRAS prices",
                 "block:dsm": "block-level DSM", "block:sras": "15-min SRAS", "block:sras_5min": "5-min SRAS",
                 "block:tras": "block-level TRAS", "block:scuc": "block-level SCUC"}.get(sec, sec)
        weeks = ", ".join(f"{d:%d %b}" for d, _ in items)
        verdict = {"source_mismatch": "totals do not tie", "partial": "only partly reconciles"}.get(st, "could not parse")
        out.append(f"{label} – {verdict} "
                   f"(weeks of {weeks}). Latest: {items[0][1]}")
    return " ".join(out)


def ingest(limit_weeks: int = 8) -> dict:
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
                raw = sections.pop("_block_data", None)
                if raw:
                    try:
                        sections["block_data"] = _block_data(w.key, raw, sections)
                    except Exception as exc:  # noqa: BLE001
                        sections["block_data"] = {"dsm": {"status": "parse_error", "message": f"block data: {exc}"}}
                rec = {"rpc": name, "region": meta["region"], "period": {"from": w.start.isoformat(), "to": w.end.isoformat()},
                       "listing": w.listing, "documents": w.docs, "fetched": _now(), "parser_version": PARSER_VERSION,
                       **{k: v for k, v in sections.items() if k in SECTIONS}}
                _write(path, rec)
                parsed += 1
            for sec in SECTIONS:
                if sec == "block_data":
                    for ds, b in (rec.get(sec) or {}).items():
                        if b.get("status") in ("parse_error", "partial"):
                            problems.append((f"block:{ds}", b["status"], w.start, b.get("message") or ""))
                    continue
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
