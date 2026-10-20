"""Parsers for RPC settlement PDFs, tested on excerpts of the real accounts (week of 28 Sep 2026)."""
from pathlib import Path

import pytest

from dhruva.sources import rpc
from dhruva.sources import tables as T

FIX = Path(__file__).parent / "fixtures"


def lines(name: str) -> list[str]:
    return (FIX / name).read_text().splitlines()


def test_numbers_ignore_dates_and_read_indian_grouping():
    vals = [v for v, *_ in T.numbers("Week 28-09-2026 to 04/10/26  WR-ER  3,53,60,51,210  -1,205,491  12.5")]
    assert vals == [3536051210.0, -1205491.0, 12.5]


def test_erpc_sras_reconciles_with_total_row():
    t = T.numbered_rows(lines("erpc_sras.txt"), 6)
    assert t.status == "ok" and len(t.rows) == 20
    nk = next(r for r in t.rows if r["name"] == "NKSTPP")
    assert nk["values"] == [4875.13, 210.66, 4664.47, 10238512.0, 2542895.0, 12781407.0]


def test_wrapped_provider_names_are_rejoined():
    t = T.numbered_rows(lines("erpc_tras2.txt"), 14)
    assert t.status == "ok"
    names = [r["name"] for r in t.rows]
    assert "DSTPS I&II" in names and "MTPS 7&8" in names


def test_a_wrong_total_is_flagged_not_published():
    body = lines("erpc_sras.txt")
    tampered = [l.replace("12051008", "12051999") if l.strip().startswith("Total") else l for l in body]
    t = T.numbered_rows(tampered, 6)
    assert t.status == "parse_error" and "TOTAL says" in t.message


def test_erpc_dsm_summary_positional_columns_and_categories():
    L = lines("erpc_dsm_summary.txt")
    h = T.find_index(L, r"Payable\s+Receivable\s+Payable\s+Receivable")
    end = T.find_index(L, r"Payable To The Pool", h)
    cols = T.header_centres(L[h], ["Payable", "Receivable", "Payable", "Receivable"])
    t = T.positional_rows(L[h + 1:end], cols, [0, 1])
    assert t.status == "ok"
    gridco = next(r for r in t.rows if r["name"] == "GRIDCO")
    assert gridco["values"] == [441.30997, 916.80497, None, 475.495]          # final payable blank, receivable set
    assert rpc.group_of(gridco["category"]) == "Discoms & states"
    solar = next(r for r in t.rows if r["name"] == "TALCHER SOLAR")
    assert rpc.group_of(solar["category"]) == "Wind & solar"


def test_nerpc_dsm_summary_anchors_money_columns_on_total_row():
    L = lines("nerpc_dsm_summary.txt")
    h = T.find_index(L, r"CONSTITUENTS\s+SCHEDULE")
    end = T.find_index(L, r"Pool Balance", h)
    tot = T.find_index(L, T.TOTAL_ROW, h)
    money = [e for _, _, e in T.numbers(L[tot])][-2:]
    cols = [T.header_centres(L[h], [w])[0] for w in ("SCHEDULE (MWH)", "ACTUAL (MWH)", "DEVIATION (MWH)")] + money
    t = T.positional_rows(L[h + 1:end], cols, [3, 4])
    assert t.status == "ok"
    nr = next(r for r in t.rows if r["name"] == "NR")
    assert nr["values"][2] == pytest.approx(-87186.18) and nr["values"][4] == pytest.approx(795161805)
    assert rpc.group_of(nr["category"]) == "Inter-regional"
