"""Value of a battery behind Khavda PS1's evacuation ceiling, one cycle a day.

Charging energy is the estimated curtailed output (potential minus actual), topped up from the grid at the
day-ahead price when curtailed energy runs short. Discharge goes to the day's highest-priced day-ahead blocks,
limited by the spare room under the day's highest schedule (the evacuation ceiling seen in the data).
"""
import sys
import numpy as np
import pandas as pd

src, out = sys.argv[1], sys.argv[2]
RTE, WEAR = 0.88, 300.0                     # round-trip efficiency; Rs/MWh throughput wear, as in the synergy model
d = pd.read_csv(src, low_memory=False)
d = d[d.ws_capacity.fillna(0) > 0]
d["cf"] = d.actual_mwh / d.ws_capacity
pv = d.pivot_table(index=["date", "block"], columns="entity", values="cf")
cap = d.pivot_table(index=["date", "block"], columns="entity", values="ws_capacity")
solar = pv[["NTPCREL_PSS2_KPS2_S", "GIPCL_PSS1_KPS2_S", "SAELP4_GSECLS_KPS2_S", "SAELP5_GSECLS_KPS2_S"]].mean(axis=1).clip(lower=0)
wind = pv[["MANIKARAN_BHUJ1_QCA", "NVWEPL_DAYAPAR_BHJ_W", "MANIKARAN_BHACHAU_QCA"]].mean(axis=1).clip(lower=0)
e = "AREH5L_KHAVDAPS1_QCA"
x = d[d.entity == e].set_index(["date", "block"])
df = pd.DataFrame({"mw": x.actual_mwh * 4, "sch_mw": x.schedule_mwh * 4, "s": solar, "w": wind}).dropna()
prices = pd.concat(pd.read_csv(f) for f in __import__("glob").glob("/home/user/power_price_terminal/data/dam/2026-*.csv"))
df = df.join(prices.set_index(["date", "block"]).mcp.rename("dam"))
df["month"] = df.index.get_level_values(0).str[:7]
parts = []
for m, g in df.groupby("month"):                     # fit potential = a*solar_cf + b*wind_cf on unconstrained blocks
    fit = g[g.s < 0.45]
    c, *_ = np.linalg.lstsq(np.c_[fit.s, fit.w], fit.mw, rcond=None)
    parts.append(g.assign(potential_mw=np.maximum(c[0] * g.s + c[1] * g.w, g.mw)))
df = pd.concat(parts)
df["curtailed_mw"] = np.where(df.s >= 0.45, df.potential_mw - df.mw, 0.0)
df[["mw", "sch_mw", "potential_mw", "curtailed_mw", "dam"]].round(2).to_csv(f"{out}/khavda_ps1_potential_blocks.csv.gz", compression="gzip")

rows = []
for p_mw, hours in [(500, 2), (1000, 2), (1000, 4), (2000, 2), (2000, 4), (3000, 4)]:
    e_mwh = p_mw * hours
    for day, g in df.groupby(level=0):
        g = g.droplevel(0)
        ceiling = g.sch_mw.max()
        free = np.minimum(g.curtailed_mw, p_mw) / 4                        # MWh per block it could soak up
        free_e = min(free.sum(), e_mwh)
        # top up from the grid in the cheapest blocks
        cheap = g.dam.sort_values()
        need, grid_cost, grid_e = e_mwh - free_e, 0.0, 0.0
        for b, pr in cheap.items():
            if need <= 0: break
            take = min(need, p_mw / 4 - free.get(b, 0))
            if take > 0:
                grid_cost += take * pr; grid_e += take; need -= take
        stored = (free_e + grid_e) * RTE
        room = np.minimum(p_mw, (ceiling - g.mw).clip(lower=0)) / 4        # MWh it can push out per block
        sale, left = 0.0, stored
        for b in g.dam.sort_values(ascending=False).index:
            if left <= 0: break
            q = min(left, room[b]); sale += q * g.dam[b]; left -= q
        rows.append({"power_mw": p_mw, "hours": hours, "date": day, "free_mwh": free_e, "grid_mwh": grid_e,
                     "sold_mwh": stored - left, "sale_rs": sale, "grid_cost_rs": grid_cost, "wear_rs": (stored - left) * WEAR})
r = pd.DataFrame(rows)
r["margin_rs"] = r.sale_rs - r.grid_cost_rs - r.wear_rs
s = r.groupby(["power_mw", "hours"]).agg(days=("date", "nunique"), free_gwh=("free_mwh", lambda v: v.sum() / 1e3),
        grid_gwh=("grid_mwh", lambda v: v.sum() / 1e3), sold_gwh=("sold_mwh", lambda v: v.sum() / 1e3),
        sale_cr=("sale_rs", lambda v: v.sum() / 1e7), grid_cost_cr=("grid_cost_rs", lambda v: v.sum() / 1e7),
        margin_cr=("margin_rs", lambda v: v.sum() / 1e7))
s["margin_cr_per_year"] = s.margin_cr / s.days * 365
s["margin_lakh_per_mw_month"] = s.margin_cr_per_year * 100 / s.index.get_level_values(0) / 12
s["sale_rs_kwh"] = s.sale_cr * 10 / s.sold_gwh
s.round(2).to_csv(f"{out}/khavda_ps1_storage_options.csv")
print(s.round(2).to_string())
print("curtailed GWh, est.:", round(df.curtailed_mw.sum() / 4 / 1e3, 1), "of potential", round(df.potential_mw.sum() / 4 / 1e3, 1))
