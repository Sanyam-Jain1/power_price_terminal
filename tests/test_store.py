from datetime import date

import numpy as np

from dhruva import store
from dhruva.weekly import last_complete_week_end


def test_block_roundtrip_merges_and_partitions_by_month(tmp_path):
    rows = [{"date": "2026-09-30", "block": b, "mcp": "100"} for b in range(1, 97)]
    rows += [{"date": "2026-10-01", "block": 1, "mcp": "200"}]
    store.write_blocks("dam", rows, ["mcp"], root=tmp_path)
    store.write_blocks("dam", [{"date": "2026-10-01", "block": 2, "mcp": ""}], ["mcp"], root=tmp_path)
    assert sorted(p.name for p in (tmp_path / "dam").iterdir()) == ["2026-09.csv", "2026-10.csv"]
    days, mat = store.block_matrix("dam", "mcp", date(2026, 9, 1), date(2026, 10, 31), root=tmp_path)
    assert days == ["2026-09-30", "2026-10-01"]
    assert mat[1, 0] == 200 and np.isnan(mat[1, 1])
    assert store.complete_days("dam", root=tmp_path) == {"2026-09-30"}
    assert store.latest_date("dam", root=tmp_path) == date(2026, 10, 1)


def test_upsert_table_replaces_by_key(tmp_path):
    f = ["k", "v"]
    store.upsert_table("t", [{"k": "a", "v": 1}, {"k": "b", "v": 2}], ["k"], f, root=tmp_path)
    store.upsert_table("t", [{"k": "a", "v": 3}], ["k"], f, root=tmp_path)
    assert store.read_table("t", root=tmp_path) == [{"k": "a", "v": "3"}, {"k": "b", "v": "2"}]


def test_last_complete_week_end():
    assert last_complete_week_end(date(2026, 10, 19)) == date(2026, 10, 18)   # Monday
    assert last_complete_week_end(date(2026, 10, 18)) == date(2026, 10, 11)   # Sunday: week not over
    assert last_complete_week_end(date(2026, 10, 22)) == date(2026, 10, 18)
