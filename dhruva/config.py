"""Static configuration: markets, bid areas, paths and the index parameters."""
from __future__ import annotations

from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SITE_DATA_DIR = ROOT / "site" / "data"
NOTES_DIR = ROOT / "notes"

# History starts at the beginning of FY2024-25.
HISTORY_START = date(2024, 4, 1)

IEX_API = "https://www.iexindia.com/api/v1"
IEX_WEB = "https://www.iexindia.com"
IEX_UMCP_CSV = "https://iexrtmprice.com/view-dam-provisional-mcv-and-mcp-data/data/DAM_{ddmmyyyy}.csv"
NSE_HOME = "https://www.nseindia.com/"
NSE_COMMODITY_API = "https://www.nseindia.com/api/liveCommodity-derivatives"

BLOCKS_PER_DAY = 96
BLOCK_HOURS = 0.25

# Spot segments published as 15-minute blocks by IEX.
MARKETS = {
    "dam": {"label": "Day-Ahead (DAM)", "endpoint": "dam/market-snapshot"},
    "rtm": {"label": "Real-Time (RTM)", "endpoint": "rtm/market-snapshot"},
    "gdam": {"label": "Green Day-Ahead (G-DAM)", "endpoint": "gdam/market-snapshot"},
    "hpdam": {"label": "High-Price DAM (HP-DAM)", "endpoint": "hpdam/market-snapshot"},
}

# IEX bid areas grouped into the five regional grids.
BID_AREAS = {
    "N1": "North", "N2": "North", "N3": "North",
    "E1": "East", "E2": "East",
    "W1": "West", "W2": "West", "W3": "West",
    "S1": "South", "S2": "South", "S3": "South",
    "A1": "North-East", "A2": "North-East",
}

# States in each bid area (as published by IEX).
BID_AREA_STATES = {
    "N1": "J&K, Himachal Pradesh, Chandigarh, Haryana",
    "N2": "Uttar Pradesh, Uttarakhand, Rajasthan, Delhi",
    "N3": "Punjab",
    "E1": "West Bengal, Sikkim, Bihar, Jharkhand",
    "E2": "Odisha",
    "W1": "Madhya Pradesh",
    "W2": "Maharashtra, Gujarat, Goa, Daman & Diu, DNH",
    "W3": "Chhattisgarh",
    "S1": "Andhra Pradesh, Telangana, Karnataka",
    "S2": "Tamil Nadu, Puducherry",
    "S3": "Kerala",
    "A1": "Tripura, Meghalaya, Manipur, Mizoram, Nagaland",
    "A2": "Assam, Arunachal Pradesh",
}

# Dhruva BESS-IN index family (see docs/METHODOLOGY.md).
BESS_RTE = 0.85                 # round-trip efficiency, AC-AC
BESS_FEE_RS_PER_MWH = 20.0      # exchange transaction fee per side (CERC cap: 2 paise/kWh)
BESS_VARIANTS = {
    "DBX-2H":     {"market": "dam", "duration_h": 2, "cycles": 1.0, "headline": True},
    "DBX-4H":     {"market": "dam", "duration_h": 4, "cycles": 1.0, "headline": True},
    "DBX-2H-2C":  {"market": "dam", "duration_h": 2, "cycles": 2.0, "headline": False},
    "DBX-RTM-2H": {"market": "rtm", "duration_h": 2, "cycles": 1.0, "headline": False},
    "DBX-RTM-4H": {"market": "rtm", "duration_h": 4, "cycles": 1.0, "headline": False},
}
# Regional variants are run for this spec against each bid area's DAM price.
BESS_REGIONAL_SPEC = {"duration_h": 2, "cycles": 1.0}

# Peak window used for summary statistics (evening peak, IST).
EVENING_PEAK_BLOCKS = range(72, 92)   # 18:00-23:00
SOLAR_BLOCKS = range(36, 64)          # 09:00-16:00
