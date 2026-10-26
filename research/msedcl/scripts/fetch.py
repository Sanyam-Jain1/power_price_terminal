import sys, zipfile, json
from pathlib import Path
from dhruva.sources import rpc
OUT=Path(sys.argv[1])
ws=[w for w in rpc.wrpc_weeks(60) if w.start.isoformat()>='2026-04-06']
meta=[]
for w in sorted(ws, key=lambda w:w.start):
    try:
        z=zipfile.ZipFile(rpc.download(w.docs['blocks_zip']['url']))
    except Exception as e:
        print('FAIL',w.start,e); meta.append({'week':w.start.isoformat(),'error':str(e)}); continue
    names=[n for n in z.namelist() if '/' not in n and (n.startswith('MSEB_State') or n.startswith('Datewise_') or n.startswith('MSEB'))]
    d=OUT/w.start.isoformat(); d.mkdir(parents=True, exist_ok=True)
    for n in names: (d/n).write_bytes(z.read(n))
    meta.append({'week':w.start.isoformat(),'to':w.end.isoformat(),'zip':w.docs['blocks_zip'],'dsm_pdf':w.docs.get('dsm_pdf'),'files':names})
    print(w.start, names)
(OUT/'weeks.json').write_text(json.dumps(meta,indent=1))
