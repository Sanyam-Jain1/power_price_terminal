"""Fetch MSEDCL day schedules from the public (no-login) scheduling Web API advertised on the
dsm-scheduling.mahasldc.in login page. The API itself only serves current date, last 45 days, day-ahead."""
import sys, os, time, datetime, requests
raw = sys.argv[1]; acr = sys.argv[2]; d0 = datetime.date.fromisoformat(sys.argv[3]); d1 = datetime.date.fromisoformat(sys.argv[4])
out = os.path.join(raw, 'sched_api', acr); os.makedirs(out, exist_ok=True)
S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0 research-bot (public data)'
d = d0
while d <= d1:
    p = os.path.join(out, d.isoformat() + '.json')
    if not (os.path.exists(p) and os.path.getsize(p) > 1000):
        u = 'https://dsm-scheduling.mahasldc.in/WEBACCESS/getapidata'
        try:
            r = S.get(u, params={'ACR': acr, 'DATE': d.strftime('%d-%m-%Y')}, timeout=180)
            open(p, 'wb').write(r.content)
            print(d, r.status_code, len(r.content), r.content[:80] if len(r.content) < 1000 else '', flush=True)
        except Exception as e:
            print(d, 'ERR', e, flush=True)
        time.sleep(3)
    d += datetime.timedelta(1)
