import numpy as np
import pytest

from dhruva.analytics.bess import Spec, lakh_per_mw_month, optimise_day


def test_two_price_day_matches_closed_form():
    p = np.r_[np.zeros(48), np.full(48, 10000.0)]
    spec = Spec(duration_h=2, cycles=1, rte=0.81, fee=20)   # eta = 0.9 each way
    res = optimise_day(p, spec)
    E, eta = 2.0, 0.9
    expected = E * eta * (10000 - 20) - 20 * E / eta
    assert res.revenue == pytest.approx(expected, rel=1e-6)
    assert res.cycles == pytest.approx(1.0, abs=1e-6)
    assert res.avg_buy == pytest.approx(0.0)
    assert res.avg_sell == pytest.approx(10000.0)


def test_flat_prices_do_not_trade():
    res = optimise_day(np.full(96, 5000.0), Spec(duration_h=4))
    assert res.revenue == pytest.approx(0.0, abs=1e-6)
    assert res.discharge.sum() == pytest.approx(0.0, abs=1e-9)


def test_constraints_hold_on_noisy_prices():
    rng = np.random.default_rng(7)
    p = 4000 + 3000 * np.sin(np.linspace(0, 4 * np.pi, 96)) + rng.normal(0, 500, 96)
    spec = Spec(duration_h=2, cycles=1)
    res = optimise_day(p, spec)
    assert res.revenue >= 0
    assert res.soc.min() >= -1e-7 and res.soc.max() <= 2 + 1e-7
    assert res.soc[-1] == pytest.approx(0, abs=1e-7)
    assert np.all(res.charge + res.discharge <= 1 + 1e-7)
    assert res.cycles <= 1 + 1e-6


def test_more_cycles_and_energy_never_earn_less():
    rng = np.random.default_rng(1)
    p = 3000 + 3000 * np.sin(np.linspace(0, 4 * np.pi, 96)) ** 2 + rng.normal(0, 300, 96)
    one = optimise_day(p, Spec(duration_h=2, cycles=1)).revenue
    two = optimise_day(p, Spec(duration_h=2, cycles=2)).revenue
    four_h = optimise_day(p, Spec(duration_h=4, cycles=1)).revenue
    assert two >= one - 1e-6
    assert four_h >= one - 1e-6


def test_missing_block_returns_none():
    p = np.full(96, 3000.0)
    p[10] = np.nan
    assert optimise_day(p, Spec(duration_h=2)) is None


def test_lakh_per_mw_month():
    assert lakh_per_mw_month([10000.0] * 30) == pytest.approx(3.0)
