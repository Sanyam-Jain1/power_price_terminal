"""Block-level RPC parsers and reconciliation, on small workbooks built in each RPC's real layout."""
import io
import zipfile
from datetime import date

import openpyxl

from dhruva.sources import rpc_blocks as B
from dhruva.sources import tables as T


def xlsx(sheets: dict[str, list[tuple]]) -> bytes:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for r in rows:
            ws.append(list(r))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


ERPC_HDR = ("Date", "Time", "Block", "Freq (Hz)", "Actual (MWH)", "Schedule (MWH)", "SRAS (MWH)", "Deviation (MWH)",
            "Deviation (%)", "DSM Payable (Rs.)", "DSM Receivable (Rs.)", "Normal DSM Rate \nApplicable (p/KWH)")


def test_erpc_sheet_per_entity_and_rate_in_paise():
    data = xlsx({"BSPHCL": [("Detailed Deviation Report",), ("Station : BSPHCL",), (), ERPC_HDR,
                            ("2026-09-21", "00:15", 1, 49.99, -1827.9, -1822.2, 0, -5.7, 0.3, 59844.75, 0, 1000),
                            ("2026-09-21", "00:30", 2, 50.02, -1819.9, -1802.1, 0, -17.8, 1.0, 0, 1200.5, 1102.59)],
                 "Notes": [("nothing here",)]})
    res = B.erpc_dsm(data)
    assert res["status"] == "ok" and len(res["rows"]) == 2
    r = res["rows"][1]
    assert r[:3] == ("2026-09-21", 2, "BSPHCL")
    assert r[8] == 1200.5 and r[9] == 11025.9          # p/kWh x 10 = Rs/MWh
    assert res["freq"][("2026-09-21", 1)] == [49.99]
    assert "Notes" in res["message"]                    # skipped sheets are reported, not dropped silently


def test_wrpc_reads_constituent_csvs_and_nuclear_adjustment():
    hdr = ('Date,Time,Block,Freq(Hz),Constituents,"Actual (MWH)","Schedule (MWH)","SRAS (MWH)",Deviation(MWH),'
           '"Deviation (%)","DSM Payable (Rs.)","DSM Receivable (Rs.)","Normal Rate (p/Kwh)",'
           '"Adjusted DSM Payable On Account of Nuclear Stations","Adjusted DSM Receivable On Account of Nuclear Stations",\n')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("MP_State_DSM-2024_Data.csv", hdr + "2026-09-21,00:00,1,49.99,MP_State,130.5,122.5,0,8.0,6.5,84549.15,0,1000,35.92,515.64,\n")
        z.writestr("MP_State_schedule.csv", "date,time,block\n2026-09-21,00:00,1\n")
        z.writestr("old/JPL_DSM-2024_Data.csv", hdr)      # nested copy of an older week: ignored
    res = B.wrpc_dsm(buf.getvalue())
    assert len(res["rows"]) == 1
    r = res["rows"][0]
    assert r[2] == "MP_State" and r[7] == 84549.15 and r[10] == 35.92 and r[11] == 515.64
    rc = B.reconcile(res["rows"], [{"name": "MPSEB_Beneficiary", "payable_rs": 84585.07, "receivable_rs": 515.64}], tol_rs=1)
    assert rc["entities"]["MP_State"]["match"] == "amount" and rc["entities"]["MP_State"]["ties"]


NERPC_STATE_HDR = ("Time", "Block Number", "Frequency Code", "Frequency (Hz)", "Actual (MWH)", "Correction Factor(MWH)",
                   "Scheduled (MWH)", "Total Deviation (MWH)", "Normal Rate(Rs./MWH)", "Amount Recievable(Rs.)", "Amount Payable(Rs.)")
NERPC_IR_HDR = ("Time", "Frequency Code", "Frequency (Hz)", "Actual (MWH)", "Correction Factor(MWH)", "Scheduled (MWH)",
                "Total Deviation (MWH)", "Normal Rate(Rs./MWH)", "Amount Recievable(Rs.)", "Amount Payable(Rs.)")


def test_nerpc_day_totals_are_checked_and_interregional_blocks_come_from_time():
    assam = [("Detailed Deviation Report",), ("Station :ASSAM",),
             ("28-09-2026", "Total", None, None, 20, 0, 18, 2, None, 100, 50),
             NERPC_STATE_HDR,
             ("00:00", 1, "47", 49.97, 10, 0, 9, 1, 6000.3, 100, 0),
             ("00:15", 2, "45", 49.95, 10, 0, 9, 1, 5499.1, 0, 50),
             ("29-09-2026", "Total", None, None, 10, 0, 9, 1, None, 0, 999),   # printed total disagrees
             NERPC_STATE_HDR,
             ("00:00", 1, "47", 49.97, 10, 0, 9, 1, 6000.3, 0, 40)]
    er = [("Station :ER",), ("28-09-2026", "Total", None, 3, 0, -6, 9, None, 10, 0),
          NERPC_IR_HDR, ("00:00", "47", 49.97, 1, 0, -2, 3, 6000.3, 5, 0), ("00:15", "45", 49.95, 2, 0, -4, 6, 5499.1, 5, 0)]
    res = B.nerpc_dsm({"DeviationDetails_x.xlsx": xlsx({"ASSAM": assam, "ER": er})})
    checks = {(c["entity"], c["date"]): c["ok"] for c in res["day_checks"]}
    assert checks == {("ASSAM", "2026-09-28"): True, ("ASSAM", "2026-09-29"): False, ("ER", "2026-09-28"): True}
    assert {r[1] for r in res["rows"] if r[2] == "ER"} == {1, 2}
    wk = B.within(res, date(2026, 9, 29), date(2026, 10, 5))
    assert {r[0] for r in wk["rows"]} == {"2026-09-29"} and len(wk["day_checks"]) == 1


def test_reconcile_names_amounts_net_and_unmatched():
    rows = [("d", 1, "FSTPP I & II", None, None, None, 1, 100.0, 40.0, None, None, None),
            ("d", 1, "FSTPP-III", None, None, None, 1, 10.0, 0.0, None, None, None),
            ("d", 1, "North Karanpura STPS", None, None, None, 1, 7.0, 3.0, None, None, None),
            ("d", 1, "ASSAM", None, None, None, 1, 500.0, 200.0, None, None, None),
            ("d", 1, "TAPS-I", None, None, None, 1, 9.0, 9.0, None, None, None)]
    pdf = [{"name": "FSTPP - I & II", "payable_rs": 100, "receivable_rs": 40},
           {"name": "FSTPP-III", "payable_rs": 10, "receivable_rs": 0},
           {"name": "NKSTPP", "payable_rs": 7, "receivable_rs": 3},
           {"name": "ASSAM", "payable_rs": 300, "receivable_rs": 0}]          # printed as a net figure
    rc = B.reconcile(rows, pdf, tol_rs=0.5)
    e = rc["entities"]
    assert e["FSTPP I & II"]["pdf_name"] == "FSTPP - I & II"            # '&' must not collapse onto 'III'
    assert e["FSTPP-III"]["pdf_name"] == "FSTPP-III"
    assert e["North Karanpura STPS"]["match"] == "amount"
    assert e["ASSAM"]["ties"] and e["ASSAM"]["basis"] == "net"
    assert e["TAPS-I"]["match"] == "unmatched" and e["TAPS-I"]["ties"] is None
    assert rc["summary"] == {"entities": 5, "ties": 4, "differs": 0, "unmatched": 1, "pdf_rows_without_block_data": []}


def test_subtotal_with_wrapped_label_is_not_an_entity():
    lines = ["                                    Payable        Receivable      Net DSM (Rs.)",
             "105    ARE35L_PSS10_KPS3_BI      14,32,118         14,48,942          16,824",
             "           WIND & SOLAR",
             "  -    (INFIRM) GENERATORS       71,99,944        57,99,276         14,00,668",
             "              Subtotal",
             "  -             Total            14,32,118        14,48,942          16,824"]
    cols = T.header_centres(lines[0], ["Payable", "Receivable", "Net DSM (Rs.)"])
    t = T.positional_rows(lines[1:], cols, [0, 1])
    assert [r["name"] for r in t.rows] == ["ARE35L_PSS10_KPS3_BI"] and t.status == "ok"
