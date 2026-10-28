import glob, pandas as pd
def load(root="/home/user/power_price_terminal/data"):
    out = None
    for seg in ["dam", "rtm", "gdam", "hpdam"]:
        fs = [f for f in glob.glob(f"{root}/{seg}/2026-*.csv") if f[-11:-4] >= "2026-04"]
        if not fs: continue
        d = pd.concat(pd.read_csv(f) for f in fs)[["date", "block", "mcp", "mcv_mw"]]
        d = d.rename(columns={"mcp": f"{seg}_mcp", "mcv_mw": f"{seg}_mcv"})
        out = d if out is None else out.merge(d, on=["date", "block"], how="outer")
    return out
