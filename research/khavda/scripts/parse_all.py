"""Parse every entity's block file from the WRPC weekly zips, keeping all columns."""
import glob, io, sys, zipfile
import pandas as pd

src, out = sys.argv[1], sys.argv[2]
COLS = {"Date": "date", "Block": "block", "Freq(Hz)": "freq", "Constituents": "entity",
        "Actual (MWH)": "actual_mwh", "Schedule (MWH)": "schedule_mwh", "SRAS (MWH)": "sras_mwh",
        "Deviation(MWH)": "deviation_mwh", "Deviation (%)": "deviation_pct",
        "DSM Payable (Rs.)": "payable_rs", "DSM Receivable (Rs.)": "receivable_rs",
        "Normal Rate (p/Kwh)": "normal_rate_p", "RE Gen PPA Rate (p/Mwh)": "ppa_rate_p",
        "Wt.Avg. ACP DAM Rate (p/Kwh)": "dam_acp_p", "Wt. Avg. Rate (p/Kwh)": "wt_avg_rate_p",
        "HPDAM Ref. Rate (p/Kwh)": "hpdam_ref_p", "HPDAM Normal Rate (p/Kwh)": "hpdam_nr_p",
        "WS Seller Capacity (Mwh)": "ws_capacity"}
frames = []
for f in sorted(glob.glob(f"{src}/*.zip")):
    z = zipfile.ZipFile(f)
    for n in z.namelist():
        if not n.endswith("_DSM-2024_Data.csv"):
            continue
        d = pd.read_csv(io.BytesIO(z.read(n)))
        d = d[[c for c in d.columns if c in COLS]].rename(columns=COLS)
        if "ws_capacity" not in d:          # thermal/state files carry no RE columns
            continue
        d["week"] = f.split("/")[-1][:10]
        frames.append(d)
d = pd.concat(frames, ignore_index=True)
d["date"] = pd.to_datetime(d["date"], dayfirst=False, errors="coerce").dt.date
d = d.dropna(subset=["date"])
d = d.drop_duplicates(["date", "block", "entity"], keep="last")
d.to_csv(out, index=False, compression="gzip")
print(d.shape, d.entity.nunique(), d.date.min(), d.date.max())
