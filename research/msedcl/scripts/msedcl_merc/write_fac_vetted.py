"""Values transcribed by eye from scanned MERC FAC prior-approval letters (no text layer).
Columns: month, source, basis(approved|actual), mu, vc_rs_kwh, vc_rs_cr, fc_rs_cr, fc_rs_kwh, appc_rs_kwh"""
import csv, sys
out = sys.argv[1]
A = "MSEDCL-FAC-Approval-April-2025-1.pdf"; Mf = "MSEDCL-FAC-Approval-May-2025-1.pdf"; J = "MSEDCL-FAC-Approval-June-2025.pdf"
rows = [
 # April 2025
 ("2025-04","MSPGCL - Thermal/Gas","approved",4473.98,3.76,1682.23,761.20,1.70,5.46,A),
 ("2025-04","MSPGCL - Thermal/Gas","actual",4914.55,4.10,2015.50,894.48,1.82,5.92,A),
 ("2025-04","NTPC (all stations)","approved",2118.33,2.05,433.60,449.71,2.12,4.17,A),
 ("2025-04","NTPC (all stations)","actual",3311.65,2.88,952.43,456.29,1.38,4.25,A),
 ("2025-04","IPP - JSW","approved",None,None,None,16.05,None,None,A),
 ("2025-04","IPP - JSW","actual",181.82,3.70,67.29,15.48,0.85,4.55,A),
 ("2025-04","IPP - Mundra UMPP (CGPL)","approved",423.94,4.77,202.10,40.23,0.95,5.72,A),
 ("2025-04","IPP - Mundra UMPP (CGPL)","actual",418.15,5.63,235.56,40.58,0.97,6.60,A),
 ("2025-04","IPP - Adani Power (APML, all)","approved",1221.59,4.29,524.31,196.34,1.61,5.90,A),
 ("2025-04","IPP - Adani Power (APML, all)","actual",1882.00,4.43,834.11,194.73,1.03,5.47,A),
 ("2025-04","IPP - Emco (GMR Warora)","approved",112.61,2.77,31.23,14.61,1.30,4.07,A),
 ("2025-04","IPP - Emco (GMR Warora)","actual",139.63,2.11,29.46,14.43,1.03,3.14,A),
 ("2025-04","IPP - RattanIndia","approved",675.65,3.26,220.56,57.71,0.85,4.12,A),
 ("2025-04","IPP - RattanIndia","actual",859.34,2.47,212.01,56.55,0.66,3.13,A),
 ("2025-04","IPP - Sai Wardha","approved",127.18,3.33,42.32,20.04,1.58,4.90,A),
 ("2025-04","IPP - Sai Wardha","actual",169.69,2.92,49.48,19.48,1.15,4.06,A),
 ("2025-04","IPP - Total (1-6)","approved",2560.96,3.98,1020.52,344.98,1.35,5.33,A),
 ("2025-04","IPP - Total (1-6)","actual",3650.64,3.91,1427.92,341.25,0.93,4.85,A),
 # May 2025
 ("2025-05","MSPGCL - Thermal/Gas","approved",4438.86,3.72,1652.79,761.20,1.71,5.44,Mf),
 ("2025-05","MSPGCL - Thermal/Gas","actual",4582.12,3.96,1814.87,934.54,2.04,6.00,Mf),
 ("2025-05","NTPC (all stations)","approved",2127.07,1.97,419.94,449.71,2.11,4.09,Mf),
 ("2025-05","NTPC (all stations)","actual",3153.18,2.49,785.27,476.21,1.51,4.00,Mf),
 ("2025-05","IPP - JSW","approved",None,None,None,16.05,None,None,Mf),
 ("2025-05","IPP - JSW","actual",139.22,3.77,52.43,16.02,1.15,4.92,Mf),
 ("2025-05","IPP - Mundra UMPP (CGPL)","approved",None,None,None,40.23,None,None,Mf),
 ("2025-05","IPP - Mundra UMPP (CGPL)","actual",445.95,3.67,163.84,42.67,0.96,4.63,Mf),
 ("2025-05","IPP - Adani Power (APML, all)","approved",780.51,3.88,302.65,196.34,2.52,6.39,Mf),
 ("2025-05","IPP - Adani Power (APML, all)","actual",1647.42,3.84,632.29,201.22,1.22,5.06,Mf),
 ("2025-05","IPP - Emco (GMR Warora)","approved",116.36,2.77,32.27,14.61,1.26,4.03,Mf),
 ("2025-05","IPP - Emco (GMR Warora)","actual",127.99,2.11,26.98,14.93,1.17,3.27,Mf),
 ("2025-05","IPP - RattanIndia","approved",698.17,3.26,227.91,57.71,0.83,4.09,Mf),
 ("2025-05","IPP - RattanIndia","actual",820.57,2.46,201.58,58.43,0.71,3.17,Mf),
 ("2025-05","IPP - Sai Wardha","approved",131.42,3.33,43.73,20.04,1.53,4.85,Mf),
 ("2025-05","IPP - Sai Wardha","actual",160.80,2.55,40.99,20.13,1.25,3.80,Mf),
 ("2025-05","IPP - Total (1-6)","approved",1726.46,3.51,606.57,344.98,2.00,5.51,Mf),
 ("2025-05","IPP - Total (1-6)","actual",3341.96,3.35,1118.13,353.40,1.06,4.40,Mf),
 # June 2025
 ("2025-06","MSPGCL - Thermal/Gas","approved",4473.98,3.76,1682.23,761.20,1.70,5.46,J),
 ("2025-06","MSPGCL - Thermal/Gas","actual",3893.07,4.03,1569.42,870.28,2.24,6.27,J),
 ("2025-06","NTPC (all stations)","approved",2117.63,2.05,433.28,449.71,2.12,4.17,J),
 ("2025-06","NTPC (all stations)","actual",2816.18,2.38,669.33,472.08,1.68,4.05,J),
 ("2025-06","IPP - JSW","approved",None,None,None,16.05,None,None,J),
 ("2025-06","IPP - JSW","actual",172.53,3.58,61.76,15.53,0.90,4.48,J),
 ("2025-06","IPP - Mundra UMPP (CGPL)","approved",None,None,None,40.23,None,None,J),
 ("2025-06","IPP - Mundra UMPP (CGPL)","actual",425.74,3.55,151.34,39.61,0.93,4.49,J),
 ("2025-06","IPP - Adani Power (APML, all)","approved",755.33,3.88,292.89,196.34,2.60,6.48,J),
 ("2025-06","IPP - Adani Power (APML, all)","actual",1726.58,2.43,420.14,194.73,1.13,3.56,J),
 ("2025-06","IPP - Emco (GMR Warora)","approved",112.61,2.77,31.23,14.61,1.30,4.07,J),
 ("2025-06","IPP - Emco (GMR Warora)","actual",128.60,2.12,27.23,14.46,1.12,3.24,J),
 ("2025-06","IPP - RattanIndia","approved",675.65,3.26,220.56,57.71,0.85,4.12,J),
 ("2025-06","IPP - RattanIndia","actual",758.41,2.44,185.13,56.55,0.75,3.19,J),
 ("2025-06","IPP - Sai Wardha","approved",127.18,3.33,42.32,20.04,1.58,4.90,J),
 ("2025-06","IPP - Sai Wardha","actual",154.21,2.54,39.17,19.48,1.26,3.80,J),
 ("2025-06","IPP - Total (1-6)","approved",1670.77,3.51,587.00,344.98,2.06,5.58,J),
 ("2025-06","IPP - Total (1-6)","actual",3366.06,2.63,884.77,340.35,1.01,3.64,J),
]
# June 2025 group summary (MU and total PP cost only; page 8 of 21)
summ = [("MSPGCL - Thermal",3893.07,2439.70),("MSPGCL - Hydro",154.52,57.72),("NTPC",2816.18,1141.41),
        ("IPP - JSW",172.53,77.29),("IPP - Mundra UMPP (CGPL)",425.74,190.95),("IPP - Adani Power (APML, all)",1726.58,614.87),
        ("IPP - Emco (GMR Warora)",128.60,41.69),("IPP - RattanIndia",758.41,241.68),("IPP - Sai Wardha",154.21,58.64),
        ("IPP - Total (1-6)",3366.06,1225.12),("RE - Non-Solar",901.84,440.06),("RE - Solar",831.14,293.77),
        ("RE - Total incl REC",1732.98,733.83),("Must Run - KAPP, TAPP, Dodson etc",535.45,194.81),
        ("Short Term",179.59,57.56),("Sale of Power (shown positive in table; is a sale)",58.06,46.40),("DSM",-43.80,8.99),
        ("Transmission, SLDC, STU charges",None,960.67),("Total",12575.99,6773.42)]
with open(out, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["month","source","basis","mu","variable_rs_per_kwh","variable_rs_cr","fixed_rs_cr","fixed_rs_per_kwh","total_rs_cr","avg_rs_per_kwh","table","doc"])
    for m,s,b,mu,vck,vc,fc,fck,appc,doc in rows:
        tot = round(vc+fc,2) if (vc is not None and fc is not None) else ""
        w.writerow([m,s,b,mu,vck,vc,fc,fck,tot,appc,"FC/VC comparison tables (MSPGCL p10-11, NTPC p12-13, IPP p14)",doc])
    for s,mu,cost in summ:
        w.writerow(["2025-06",s,"actual (FAC-vetted)",mu,"","","","",cost, round(cost*10/mu,2) if mu else "","Summary table p8 of 21",J])
print(len(rows)+len(summ))
