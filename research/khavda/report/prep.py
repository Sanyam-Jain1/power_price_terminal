"""Build the datasets behind the Khavda Producer Ledger report from research/khavda/data.

Usage: python3 -I prep.py <re_blocks.csv.gz from scripts/parse_all.py>
"""
import os
import sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "data")
PS1, PS3 = "AREH5L_KHAVDAPS1_QCA", "AREH5L_KHAVDAPS3_QCA"
WIN = "6 Apr – 18 Oct 2026"


def save(df, name):
    df.to_csv(os.path.join(OUT, name + ".csv"), index=False)


raw = pd.read_csv(sys.argv[1], low_memory=False)
raw = raw[raw.ws_capacity.fillna(0) > 0].copy()
raw["rate"] = np.where(raw.ppa_rate_p > 0, raw.ppa_rate_p, np.where(raw.wt_avg_rate_p > 0, raw.wt_avg_rate_p * 10, np.nan))
raw["dsm"] = raw.receivable_rs - raw.payable_rs
raw["at_rate"] = raw.deviation_mwh * raw.rate
raw["penalty"] = raw.dsm - raw.at_rate
raw["nr_gap"] = (-raw.deviation_mwh) * (raw.normal_rate_p * 10 - raw.rate)
priced = raw[raw.rate.notna()]

# ---- plants (every WRPC wind/solar seller over 50 MU)
plants = pd.read_csv(os.path.join(D, "wrpc_re_plants.csv"))
pen = priced.groupby("entity").agg(penalty=("penalty", "sum"), at_rate=("at_rate", "sum"), nr_gap=("nr_gap", "sum"), act=("actual_mwh", "sum")).reset_index()
plants = plants.merge(pen, on="entity", how="left")
plants = plants[(plants.actual_mu > 50) & (plants.capacity_mw > 20)].copy()
plants["basis"] = np.where(plants.ppa_rate_rs_kwh.notna(), "PPA", "Market or mixed")
plants["revenue_lakh_per_mw_month"] = plants.revenue_cr * 1e2 / plants.capacity_mw / (plants.days / 30.4)
plants["penalty_rs_kwh"] = -plants.penalty / plants.act / 1e3
plants["shortfall_cost_to_others_cr"] = plants.nr_gap / 1e7
plants["owner"] = np.where(plants.entity.str.startswith(("AREH5L", "AWEMP1", "AWEK3L")), "Adani Green", "Other")
plants = plants.rename(columns={"entity": "plant"})
keep = ["plant", "owner", "basis", "capacity_mw", "actual_mu", "cuf_pct", "night_share_pct", "ppa_rate_rs_kwh", "sale_rate_rs_kwh",
        "dam_capture_ratio", "revenue_lakh_per_mw_month", "dsm_net_cr", "penalty_rs_kwh", "shortfall_cost_to_others_cr", "abs_deviation_pct", "days"]
plants = plants[keep].sort_values("actual_mu", ascending=False)
plants["dam_capture_ratio"] = plants.dam_capture_ratio.round(3)
save(plants.round(3), "plants")
basis = plants.groupby("basis").agg(plants=("plant", "size"), sale_rate_rs_kwh=("sale_rate_rs_kwh", "median"),
        revenue_lakh_per_mw_month=("revenue_lakh_per_mw_month", "median"), abs_deviation_pct=("abs_deviation_pct", "median"),
        penalty_rs_kwh=("penalty_rs_kwh", "median"), capture=("dam_capture_ratio", "median")).reset_index()
save(basis.round(3), "by_basis")

# ---- PS1 / PS3 monthly
pot = pd.read_csv(os.path.join(D, "khavda_ps1_potential_blocks.csv.gz"))
pot["month"] = pot.date.str[:7]
pot["val"] = pot.curtailed_mw / 4 * pot.dam
pm = pot.groupby("month").agg(potential_gwh=("potential_mw", lambda s: s.sum() / 4e3), actual_gwh=("mw", lambda s: s.sum() / 4e3),
        curtailed_gwh=("curtailed_mw", lambda s: s.sum() / 4e3), curtailed_value_cr=("val", lambda s: s.sum() / 1e7),
        max_schedule_mw=("sch_mw", "max")).reset_index()
pm["curtailed_share"] = pm.curtailed_gwh / pm.potential_gwh
mon = pd.read_csv(os.path.join(D, "khavda_ps1_monthly.csv"))
mon3 = pd.read_csv(os.path.join(D, "khavda_ps3_monthly.csv"))
m = pm.merge(mon[["month", "days", "capacity_mw", "cuf_pct", "sale_rate_rs_kwh", "dam_capture_rs_kwh", "dam_time_avg_rs_kwh", "revenue_cr", "dsm_net_cr", "abs_deviation_pct"]], on="month")
m = m.merge(mon3[["month", "actual_mu", "capacity_mw", "sale_rate_rs_kwh", "dsm_net_cr"]].rename(columns={"actual_mu": "ps3_actual_gwh", "capacity_mw": "ps3_capacity_mw", "sale_rate_rs_kwh": "ps3_sale_rate_rs_kwh", "dsm_net_cr": "ps3_dsm_net_cr"}), on="month")
gna = {"2026-04": 3367, "2026-05": 3367, "2026-06": 3367, "2026-07": 3525, "2026-08": 3525, "2026-09": 3525, "2026-10": 3525}
m["ps1_gna_mw"] = m.month.map(gna)
m["label"] = pd.to_datetime(m.month + "-01").dt.strftime("%b")
save(m.round(3), "monthly")

# ---- daily, PS1
day = pd.read_csv(os.path.join(D, "khavda_ps1_daily.csv")).rename(columns={"day": "date"})
pdy = pot.groupby("date").agg(potential_gwh=("potential_mw", lambda s: s.sum() / 4e3), curtailed_gwh=("curtailed_mw", lambda s: s.sum() / 4e3),
        max_schedule_mw=("sch_mw", "max"), max_output_mw=("mw", "max")).reset_index()
day = day[["date", "capacity_mw", "actual_mu", "schedule_mu", "sale_rate_rs_kwh", "dam_time_avg_rs_kwh", "dsm_net_cr", "abs_deviation_pct"]].merge(pdy, on="date")
save(day.round(3), "daily")

# ---- hour of day, PS1, whole window
b = raw[raw.entity == PS1].copy()
b["hour"] = (b.block - 1) // 4
b = b.merge(pot[["date", "block", "potential_mw", "dam"]], on=["date", "block"], how="left")
h = b.groupby("hour").agg(actual_mw=("actual_mwh", lambda s: s.mean() * 4), schedule_mw=("schedule_mwh", lambda s: s.mean() * 4),
        potential_mw=("potential_mw", "mean"), settlement_rate_rs_kwh=("rate", lambda s: s.mean() / 1e3), dam_rs_kwh=("dam", lambda s: s.mean() / 1e3),
        dsm_net_cr=("dsm", lambda s: s.sum() / 1e7), dsm_at_own_rate_cr=("at_rate", lambda s: s.sum() / 1e7), penalty_cr=("penalty", lambda s: s.sum() / 1e7),
        over_mw=("deviation_mwh", lambda s: s.clip(lower=0).mean() * 4), under_mw=("deviation_mwh", lambda s: -s.clip(upper=0).mean() * 4)).reset_index()
h["label"] = h.hour.map(lambda x: f"{x:02d}:00")
save(h.round(3), "hourly")

# ---- one clear day, every block
SAMPLE = "2026-10-10"
sd = pot[pot.date == SAMPLE][["block", "mw", "sch_mw", "potential_mw", "dam"]].copy()
sd["time"] = sd.block.map(lambda k: f"{(k - 1) // 4:02d}:{(k - 1) % 4 * 15:02d}")
sd["dam_rs_kwh"] = sd.dam / 1e3
sd["date"] = SAMPLE
save(sd.drop(columns="dam").round(2), "sample_day")

# ---- headline figures
ps1 = plants.set_index("plant").loc[PS1]; ps3 = plants.set_index("plant").loc[PS3]
pp = pen.set_index("entity")
tot_pot, tot_cur = pot.potential_mw.sum() / 4e3, pot.curtailed_mw.sum() / 4e3
june_on = pot[pot.date >= "2026-06-01"].groupby("date").sch_mw.max()
ev = b[(b.hour >= 18) & (b.hour < 23)]
cap_ps1 = b.capacity_mw if "capacity_mw" in b else b.ws_capacity * 4
hl = [
    ("days", raw.date.nunique(), WIN),
    ("ps1_mu", ps1.actual_mu, WIN), ("ps1_mu_day", ps1.actual_mu / ps1.days, WIN),
    ("ps3_mu", ps3.actual_mu, WIN), ("ps3_mu_day", ps3.actual_mu / ps3.days, WIN),
    ("ps1_capacity", ps1.capacity_mw, "median available capacity"), ("ps3_capacity", ps3.capacity_mw, "median available capacity"),
    ("ps1_cuf", ps1.cuf_pct, WIN), ("ps3_cuf", ps3.cuf_pct, WIN),
    ("ps1_night", ps1.night_share_pct, "19:00–06:00"), ("ps3_night", ps3.night_share_pct, "19:00–06:00"),
    ("ps1_capture", ps1.dam_capture_ratio * 100, "output-weighted ÷ time-average day-ahead price"),
    ("ps3_capture", ps3.dam_capture_ratio * 100, "output-weighted ÷ time-average day-ahead price"),
    ("ps1_rate", ps1.sale_rate_rs_kwh, "WRPC settlement rate"), ("ps3_rate", ps3.sale_rate_rs_kwh, "WRPC settlement rate"),
    ("potential_gwh", tot_pot, "PS1, estimate"), ("curtailed_gwh", tot_cur, "PS1, estimate"), ("curtailed_pct", tot_cur / tot_pot * 100, "PS1, estimate"),
    ("curtailed_value_dam", pot.val.sum() / 1e7, "at each block's day-ahead price"), ("curtailed_value_seci", tot_cur * 2.42 / 10, "at the ₹2.42 SECI tariff"),
    ("ceiling_low", june_on.quantile(0.1), "PS1 highest daily schedule, Jun–Oct, 10th percentile"),
    ("ceiling_high", june_on.quantile(0.9), "PS1 highest daily schedule, Jun–Oct, 90th percentile"),
    ("april_peak_sched", pot[pot.date < "2026-05-01"].groupby("date").sch_mw.max().max(), "PS1 highest schedule in April"),
    ("ps1_dsm", ps1.dsm_net_cr, "net received"), ("ps3_dsm", ps3.dsm_net_cr, "net"),
    ("ps1_at_rate", pp.loc[PS1, "at_rate"] / 1e7, "deviation × own rate"), ("ps1_penalty", -pp.loc[PS1, "penalty"] / 1e7, "real penalty"),
    ("ps1_penalty_kwh", -pp.loc[PS1, "penalty"] / pp.loc[PS1, "act"] / 1e3, "₹/kWh of output"),
    ("ps1_over_gwh", b.deviation_mwh.clip(lower=0).sum() / 1e3, "over-injected"), ("ps1_under_gwh", -b.deviation_mwh.clip(upper=0).sum() / 1e3, "under-injected"),
    ("wrpc_cost_to_others", priced.nr_gap.sum() / 1e7, "all WRPC wind/solar sellers"),
    ("ps1_evening_mw", ev.actual_mwh.mean() * 4, "PS1 average output 18:00–23:00"),
    ("ps1_midday_dam", b[(b.hour >= 10) & (b.hour < 14)].dam.mean() / 1e3, "day-ahead 10:00–14:00"),
    ("ps1_evening_dam", ev.dam.mean() / 1e3, "day-ahead 18:00–23:00"),
    ("ps1_night_rate_max", h.settlement_rate_rs_kwh.max(), "highest hourly settlement rate"),
    ("band1_mw", ps1.capacity_mw * 0.15, "first deviation band of the 2015-era tiers, 15% of PS1 available capacity"),
    # assumptions of the estimates (scripts/storage.py)
    ("fit_threshold_pct", 45, "peer solar output below this share of capacity is treated as unconstrained"),
    ("plant_min_mu", 50, "plants below this output are left out of the comparison"),
    ("rte_pct", 88, "battery round-trip efficiency assumed"),
    ("wear_rs_mwh", 300, "battery wear cost assumed, per MWh discharged"),
    # facts from other studies and filings
    ("agel_merchant_rs_kwh", 2.4, "AGEL merchant price, Q2 FY27 call"),
    ("agel_h1_rs_kwh", 3.22, "AGEL revenue per kWh, H1 FY27"),
    ("agel_h1_curtail_cr", 724, "AGEL EBITDA lost to curtailment, H1 FY27"),
    ("agel_solar_grid_avail", 78.9, "AGEL solar grid availability, H1 FY27"),
    ("khavda_mw", 10752, "Khavda operating capacity, 30 Sep 2026"),
    ("khavda_bess_mwh", 6632, "Khavda battery capacity, 30 Sep 2026"),
    ("ps1_gna_mw", 3525, "PS1 grid access from Jul 2026, WRPC RTDA"),
    ("msedcl_evening_dsm", 24.25, "MSEDCL deviation price in big-gap evening blocks, research/msedcl"),
]
save(pd.DataFrame(hl, columns=["metric", "value", "window"]).round(3), "headline")
print("datasets written to", OUT)
