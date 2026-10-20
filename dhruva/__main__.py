"""Command line: python -m dhruva {ingest,derive,build,weekly,daily}."""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date

from .config import HISTORY_START


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="dhruva", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ing = sub.add_parser("ingest", help="fetch new data from all sources")
    ing.add_argument("--from", dest="start", type=date.fromisoformat, default=HISTORY_START)
    ing.add_argument("--only", choices=["spot", "areas", "umcp", "tam", "rec", "futures", "grid", "landed_cost"])
    ing.add_argument("--no-landed", action="store_true", help="skip the monthly landed-cost refresh")
    sub.add_parser("derive", help="compute Dhruva indices (incremental)")
    sub.add_parser("build", help="write site/data/*.json")
    wk = sub.add_parser("weekly", help="draft The Dhruva Weekly for the latest complete week")
    wk.add_argument("--week-ending", type=date.fromisoformat)
    sub.add_parser("daily", help="ingest + derive + build + weekly (the cron job)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    from . import build, derive, ingest, weekly

    if args.cmd == "ingest":
        if args.only:
            fn = {"spot": lambda: ingest.ingest_spot(args.start), "areas": lambda: ingest.ingest_areas(args.start),
                  "umcp": ingest.ingest_umcp, "tam": ingest.ingest_tam,
                  "rec": lambda: ingest.ingest_rec(list(range(args.start.year, date.today().year + 1))),
                  "futures": ingest.ingest_futures, "grid": ingest.ingest_grid,
                  "landed_cost": lambda: ingest.ingest_landed_cost(force=True)}[args.only]
            print(json.dumps({args.only: fn()}, default=str))
        else:
            print(json.dumps(ingest.run_all(args.start, landed=not args.no_landed), default=str))
    elif args.cmd == "derive":
        print(json.dumps(derive.run(), default=str))
    elif args.cmd == "build":
        print(json.dumps(build.run(), default=str))
    elif args.cmd == "weekly":
        print(weekly.write(args.week_ending))
    elif args.cmd == "daily":
        print(json.dumps(ingest.run_all(), default=str))
        print(json.dumps(derive.run(), default=str))
        print(weekly.write())
        print(json.dumps(build.run(), default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
