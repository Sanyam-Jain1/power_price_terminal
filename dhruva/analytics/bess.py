"""Dhruva BESS-IN: perfect-foresight battery arbitrage on 15-minute prices.

For each delivery day we solve a linear programme (HiGHS via SciPy):

    max   sum_t  dt * [ (p_t - f) * d_t  -  (p_t + f) * c_t ]
    s.t.  s_t = s_{t-1} + dt * (eta_c * c_t - d_t / eta_d)        t = 1..T
          0 <= s_t <= E,   s_0 = s_T = 0
          0 <= c_t, d_t,   c_t + d_t <= P
          dt * sum_t d_t / eta_d <= cycles * E      (throughput limit)

c_t / d_t are grid-side charge / discharge power (MW), s_t stored energy (MWh),
p_t the block price (Rs/MWh), f the per-side exchange fee, P = 1 MW and
E = duration_h MWh. Losses are split symmetrically: eta_c = eta_d = sqrt(RTE).
Days are independent (empty at 00:00 and 24:00), which keeps each day's
number reproducible from that day's prices alone.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, hstack, identity, vstack

from ..config import BESS_FEE_RS_PER_MWH, BESS_RTE, BLOCK_HOURS


@dataclass(frozen=True)
class Spec:
    duration_h: float
    cycles: float = 1.0
    power_mw: float = 1.0
    rte: float = BESS_RTE
    fee: float = BESS_FEE_RS_PER_MWH


@dataclass
class DayResult:
    revenue: float          # Rs per MW of power capacity for the day
    charge: np.ndarray      # MW per block
    discharge: np.ndarray   # MW per block
    soc: np.ndarray         # MWh at end of each block
    cycles: float           # equivalent full cycles (discharged energy / E)
    avg_buy: float          # volume-weighted charge price, Rs/MWh
    avg_sell: float         # volume-weighted discharge price, Rs/MWh


_cache: dict[tuple, tuple] = {}


def _structure(T: int, spec: Spec):
    """Constraint matrices depend only on T and spec; build once."""
    key = (T, spec)
    if key in _cache:
        return _cache[key]
    dt = BLOCK_HOURS
    eta = np.sqrt(spec.rte)
    E, P = spec.duration_h * spec.power_mw, spec.power_mw
    I = identity(T, format="csr")
    # s_t - s_{t-1} - dt*eta*c_t + dt/eta*d_t = 0 ; variables x = [c, d, s]
    shift = csr_matrix((np.ones(T - 1), (np.arange(1, T), np.arange(T - 1))), shape=(T, T))
    A_eq = hstack([-dt * eta * I, (dt / eta) * I, I - shift], format="csr")
    end = csr_matrix(([1.0], ([0], [3 * T - 1])), shape=(1, 3 * T))
    A_eq = vstack([A_eq, end], format="csr")
    b_eq = np.zeros(T + 1)
    # c_t + d_t <= P ; throughput
    A_ub = vstack([
        hstack([I, I, csr_matrix((T, T))]),
        csr_matrix(np.concatenate([np.zeros(T), np.full(T, dt / eta), np.zeros(T)])[None, :]),
    ], format="csr")
    b_ub = np.concatenate([np.full(T, P), [spec.cycles * E]])
    bounds = [(0, P)] * (2 * T) + [(0, E)] * T
    _cache[key] = (A_eq, b_eq, A_ub, b_ub, bounds)
    return _cache[key]


def optimise_day(prices: np.ndarray, spec: Spec) -> DayResult | None:
    """Optimal schedule for one day of block prices; None if any price is missing."""
    p = np.asarray(prices, dtype=float)
    if p.size == 0 or np.isnan(p).any():
        return None
    T, dt = p.size, BLOCK_HOURS
    A_eq, b_eq, A_ub, b_ub, bounds = _structure(T, spec)
    cost = np.concatenate([dt * (p + spec.fee), -dt * (p - spec.fee), np.zeros(T)])
    res = linprog(cost, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if res.status != 0:
        raise RuntimeError(f"LP failed: {res.message}")
    c, d, s = res.x[:T], res.x[T:2 * T], res.x[2 * T:]
    c[c < 1e-9] = 0.0
    d[d < 1e-9] = 0.0
    e_out = d.sum() * dt
    E = spec.duration_h * spec.power_mw
    return DayResult(
        revenue=float(-res.fun) / spec.power_mw,
        charge=c, discharge=d, soc=s,
        cycles=float(e_out / np.sqrt(spec.rte) / E) if E else 0.0,
        avg_buy=float((c * p).sum() / c.sum()) if c.sum() > 0 else float("nan"),
        avg_sell=float((d * p).sum() / d.sum()) if d.sum() > 0 else float("nan"),
    )


def lakh_per_mw_month(daily_rs_per_mw: list[float]) -> float:
    """Sum of a month's daily revenues in Rs lakh per MW (the unit tenders use)."""
    return float(np.nansum(daily_rs_per_mw)) / 1e5
