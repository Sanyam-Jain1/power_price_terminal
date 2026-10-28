"""Block ledger for WRPC wind/solar sellers, priced at the rate WRPC uses to settle their deviations.

Inputs: re_blocks.csv.gz (parse_all.py) and the IEX prices in the Dhruva store.
Contract rate per block: the PPA rate when WRPC lists one (Rs/MWh), else WRPC's weighted average
sale rate (p/kWh x 10). Revenue = scheduled MWh x contract rate; DSM net = receivable - payable.
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import prices

src, out = sys.argv[1], sys.argv[2]
d = pd.read_csv(src, low_memory=False)
d = d[d.ws_capacity.fillna(0) > 0]                      # drop infirm (pre-COD) and battery test entities
p = prices.load()
d = d.merge(p, on=["date", "block"], how="left")
d["rate_rs_mwh"] = np.where(d.ppa_rate_p > 0, d.ppa_rate_p, np.where(d.wt_avg_rate_p > 0, d.wt_avg_rate_p * 10, np.nan))
d["rate_basis"] = np.where(d.ppa_rate_p > 0, "ppa", np.where(d.wt_avg_rate_p > 0, "weighted_sale_rate", "none"))
d["revenue_rs"] = d.schedule_mwh * d.rate_rs_mwh
d["dsm_net_rs"] = d.receivable_rs - d.payable_rs
d["capacity_mw"] = d.ws_capacity * 4
d["hour"] = (d.block - 1) // 4
KEEP = ["AREH5L_KHAVDAPS1_QCA", "AREH5L_KHAVDAPS3_QCA", "NTPCREL_PSS2_KPS2_S", "GIPCL_PSS1_KPS2_S", "MANIKARAN_BHUJ1_QCA"]
d[d.entity.isin(KEEP)].to_csv(f"{out}/blocks_khavda_and_peers.csv.gz", index=False, compression="gzip")

def summarise(g):
    act, sch = g.actual_mwh.sum(), g.schedule_mwh.sum()
    priced = g[g.rate_rs_mwh.notna()]
    days = g.date.nunique()
    cap = g.capacity_mw.median()
    return pd.Series({
        "first_day": g.date.min(), "last_day": g.date.max(), "days": days,
        "capacity_mw": cap, "actual_mu": act / 1e3, "schedule_mu": sch / 1e3,
        "cuf_pct": act / (cap * 24 * days) * 100,
        "night_share_pct": g.loc[(g.hour < 6) | (g.hour >= 19), "actual_mwh"].sum() / act * 100 if act else np.nan,
        "ppa_rate_rs_kwh": g.loc[g.ppa_rate_p > 0, "ppa_rate_p"].median() / 1e3 if (g.ppa_rate_p > 0).any() else np.nan,
        "priced_share_pct": priced.schedule_mwh.sum() / sch * 100 if sch else np.nan,
        "sale_rate_rs_kwh": priced.revenue_rs.sum() / priced.schedule_mwh.sum() / 1e3 if priced.schedule_mwh.sum() else np.nan,
        "dam_capture_rs_kwh": (g.actual_mwh * g.dam_mcp).sum() / act / 1e3 if act else np.nan,
        "dam_time_avg_rs_kwh": g.dam_mcp.mean() / 1e3,
        "revenue_cr": priced.revenue_rs.sum() / 1e7,
        "dsm_net_cr": g.dsm_net_rs.sum() / 1e7,
        "dsm_rs_per_kwh": g.dsm_net_rs.sum() / act / 1e3 if act else np.nan,
        "abs_deviation_pct": g.deviation_mwh.abs().sum() / sch * 100 if sch else np.nan,
        "over_injection_mu": g.deviation_mwh.clip(lower=0).sum() / 1e3,
        "under_injection_mu": -g.deviation_mwh.clip(upper=0).sum() / 1e3,
    })

plants = d.groupby("entity").apply(summarise, include_groups=False)
plants["dam_capture_ratio"] = plants.dam_capture_rs_kwh / plants.dam_time_avg_rs_kwh
plants.round(4).to_csv(f"{out}/wrpc_re_plants.csv")

d["month"] = d.date.str[:7]
for e, tag in [("AREH5L_KHAVDAPS1_QCA", "ps1"), ("AREH5L_KHAVDAPS3_QCA", "ps3")]:
    x = d[d.entity == e]
    x.groupby(x.date.rename("day")).apply(summarise, include_groups=False).round(4).to_csv(f"{out}/khavda_{tag}_daily.csv")
    x.groupby("month").apply(summarise, include_groups=False).round(4).to_csv(f"{out}/khavda_{tag}_monthly.csv")
    h = x.groupby(["month", "hour"]).agg(
        actual_mw=("actual_mwh", lambda s: s.mean() * 4), schedule_mw=("schedule_mwh", lambda s: s.mean() * 4),
        sale_rate_rs_kwh=("rate_rs_mwh", lambda s: s.mean() / 1e3), dam_rs_kwh=("dam_mcp", lambda s: s.mean() / 1e3),
        rtm_rs_kwh=("rtm_mcp", lambda s: s.mean() / 1e3), gdam_rs_kwh=("gdam_mcp", lambda s: s.mean() / 1e3),
        dsm_net_rs_lakh=("dsm_net_rs", lambda s: s.sum() / 1e5), abs_dev_mw=("deviation_mwh", lambda s: s.abs().mean() * 4))
    h.round(3).to_csv(f"{out}/khavda_{tag}_hourly_by_month.csv")
print(plants.loc[["AREH5L_KHAVDAPS1_QCA", "AREH5L_KHAVDAPS3_QCA"]].T)
