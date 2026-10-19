from datetime import date

import pytest

from dhruva.sources import iex, nse


@pytest.mark.parametrize("period,block", [
    ("00:00 - 00:15", 1), ("10:00-10:15", 41), ("23:45 - 24:00", 96), ("13:30", 55),
])
def test_block_of(period, block):
    assert iex.block_of(period) == block


def test_normalise_dam_and_gdam():
    dam = iex.normalise_snapshot("dam", {
        "date": "18-10-2026", "period": "10:00 - 10:15", "purchase_bid": "7098.00", "sell_bid": "2789.80",
        "mcv": "1611.7", "final_scheduled_volume": "1611.7", "mcp": None, "congestion": "NO"})
    assert dam["date"] == "2026-10-18" and dam["block"] == 41 and dam["mcp"] == ""
    g = iex.normalise_snapshot("gdam", {
        "date": "18-10-2026", "period": "10:00 - 10:15", "purchase_bid": 7098, "total_sell_bid": 2789.8,
        "total_unconstrained_m_c_v": 1611.7, "total_cleared_volume": 1611.7, "unconstrained_m_c_p": 2150.56,
        "other_re_cleared_volume": 1524.9, "wind_cleared_volume": 3.3, "hydro_cleared_volume": 0})
    assert g["mcp"] == "2150.56" and g["solar_mw"] == "1524.90" and g["sell_bid_mw"] == "2789.80"


def test_parse_umcp_csv():
    text = "Period,MCP-Price,MCP-Buy Quantity,,\n00:00 - 00:15,10000,2357.9,,\n00:15 - 00:30,9999.5,2391.1,,\n"
    rows = iex.parse_umcp_csv(date(2026, 10, 20), text)
    assert [r["block"] for r in rows] == [1, 2]
    assert rows[1]["umcp"] == "9999.50" and rows[0]["umcv_mw"] == "2357.90"


REC_HTML = """<table><tr><th>Year</th><th>Month</th><th>Type</th><th>Buy Bids (REC)</th><th>Sell Bids (REC)</th>
<th>Cleared Volume (REC)</th><th>Cleared Price(Rs/REC)</th><th>No. Of Participants</th></tr>
<tr><td rowspan="4">2026</td><td>January14-01-2026</td><td>REC</td><td>1636444</td><td>2827114</td><td>1467294</td><td>339</td><td>76</td></tr>
<tr><td>January14-01-2026</td><td>Non-Solar*</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>
<tr><td>January28-01-2026</td><td>REC</td><td>1041168</td><td>2652662</td><td>923968</td><td>333</td><td>109</td></tr>
</table>"""


def test_parse_rec_handles_rowspans_and_blank_rows():
    rows = iex.parse_rec(REC_HTML)
    assert [(r["session_date"], r["price_rs_per_rec"]) for r in rows] == [("2026-01-14", "339"), ("2026-01-28", "333")]


TAM_HTML = """<table><tr><th>Auction Date</th><th>Instrument Name</th><th>Buy Bid Count</th><th>Sell Bid Count</th>
<th>Buy Bids (in MUs)</th><th>Sell Bids (in MUs)</th><th>Trade Volume (in MUs)</th><th>Price Discovered (in Rs/MWh)</th>
<th>Delivery Month</th><th>Auction Details</th></tr>
<tr><td>17-10-2026</td><td>MTH-BAS-NOV</td><td>1</td><td>4</td><td>15.12</td><td>15.12</td><td>15.12</td><td>9500</td><td>NOV-2026</td><td></td></tr>
</table>"""


def test_parse_tam_monthly():
    rows = iex.parse_tam_monthly(TAM_HTML)
    assert rows == [{"auction_date": "2026-10-17", "instrument": "MTH-BAS-NOV", "buy_bids_mu": "15.12",
                     "sell_bids_mu": "15.12", "volume_mu": "15.12", "price_rs_mwh": "9500",
                     "delivery_month": "NOV-2026"}]


def test_nse_parse_keeps_only_electricity_futures():
    payload = {"data": [
        {"contract": "NATURALGAS", "instrumentType": "OPTFUT", "expiryDate": "21-Oct-2026"},
        {"identifier": "FUTENRELECMBL30-10-2026XX0.0000", "instrumentType": "FUTENR", "contract": "ELECMBL",
         "expiryDate": "30-Oct-2026", "lastPrice": 4767, "highPrice": 4809, "openPrice": 4656, "lowPrice": 4621,
         "pChange": 2.406, "numberOfContractsTraded": 2025, "totalTurnover": 481257450, "openInterest": 362,
         "prevClose": 4655},
    ]}
    rows = nse.parse(payload, date(2026, 10, 19))
    assert len(rows) == 1
    assert rows[0]["delivery_month"] == "2026-10" and rows[0]["last"] == 4767
