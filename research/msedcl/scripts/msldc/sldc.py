"""Small polite client for mahasldc.in public listing API (POST report/fetchReports)."""
import re, time, json, requests, os
S = requests.Session()
S.headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) research-bot (public data)'
CSRF = None
def page(url):
    global CSRF
    r = S.get(url, timeout=60); r.raise_for_status()
    m = re.search(r"window\.csrfHash\s*=\s*'([0-9a-f]+)'", r.text)
    if m: CSRF = m.group(1)
    time.sleep(0.7)
    return r.text
def fetch_reports(t, y='', m='', d='', w='', s='', page_no=1, per_page=50, endpoint='fetchReports'):
    global CSRF
    if CSRF is None: page('https://mahasldc.in/reports/'+t)
    data = dict(t=t, m=m, y=y, w=w, d=d, s=s, lang='en', page=page_no, per_page=per_page, csrf_token=CSRF)
    r = S.post('https://mahasldc.in/report/'+endpoint, data=data, headers={'X-Requested-With':'XMLHttpRequest','Referer':'https://mahasldc.in/reports/'+t}, timeout=60)
    time.sleep(0.7)
    try: j = r.json()
    except Exception: return {'_status': r.status_code, '_text': r.text[:500]}
    if j.get('csrfHash'): CSRF = j['csrfHash']
    return j
def download(url, path, delay=1.0):
    if os.path.exists(path) and os.path.getsize(path) > 0: return 'cached'
    r = S.get(url, timeout=120)
    time.sleep(delay)
    if r.status_code != 200: return r.status_code
    open(path, 'wb').write(r.content); return len(r.content)
