import numpy as np
import pytest

from dhruva.analytics import indices


def test_vwap_ignores_missing_and_zero_volume():
    assert indices.vwap([100, 200, np.nan, 300], [1, 3, 5, 0]) == pytest.approx(175.0)


def test_day_stats_spread_and_cap_blocks():
    p = np.full(96, 3000.0)
    p[72:92] = 10000.0        # evening peak at the cap
    p[36:64] = 1000.0         # cheap solar
    s = indices.day_stats(p, np.ones(96))
    assert s["evening_peak"] == pytest.approx(10000.0)
    assert s["solar"] == pytest.approx(1000.0)
    assert s["spread"] == pytest.approx(9000.0)
    assert s["cap_blocks"] == 20
    assert s["volume_mwh"] == pytest.approx(24.0)


def test_monthly_index_resets_each_month_and_tracks_mtd():
    dates = ["2026-09-30", "2026-10-01", "2026-10-02"]
    prices = np.array([[1000.0] * 96, [2000.0] * 96, [4000.0] * 96])
    vols = np.array([[1.0] * 96, [1.0] * 96, [3.0] * 96])
    out = indices.monthly_index(dates, prices, vols)
    assert out["2026-09"]["vwap"] == pytest.approx(1000.0)
    assert out["2026-10"]["mtd"][0][1] == pytest.approx(2000.0)
    assert out["2026-10"]["vwap"] == pytest.approx(3500.0)
    assert out["2026-10"]["days"] == 2


def test_dsm_normal_rate_falls_back_to_dam_rtm_average():
    dam, rtm = np.array([4000.0, 6000.0]), np.array([2000.0, 3000.0])
    assert indices.dsm_normal_rate(dam, rtm).tolist() == [3000.0, 4500.0]
    asc = np.array([9000.0, np.nan])
    assert indices.dsm_normal_rate(dam, rtm, asc).tolist() == [5000.0, 4500.0]


def test_baseline_backtest_runs():
    rng = np.random.default_rng(0)
    mat = 4000 + rng.normal(0, 100, (30, 96))
    bt = indices.backtest_baseline(mat, lookback=7, window=10)
    assert bt["days"] == 10 and 0 < bt["mae"] < 300
