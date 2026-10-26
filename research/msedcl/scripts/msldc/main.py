import sys,re
h=open(sys.argv[1],encoding='utf-8',errors='replace').read()
a=h.find('<div class="content-area">')
if a<0: a=h.find('id="main-content"')
b=h.find('<!-- end::page-content-container -->')
s=h[a:b]
if len(sys.argv)>2 and sys.argv[2]=='scripts':
    for m in re.finditer(r'<script[^>]*>(.*?)</script>',h,re.S):
        t=m.group(1)
        if any(k in t for k in ('ajax','fetch','url','Url','URL')) and 'csrf' not in t[:300] and 'renderChart' not in t:
            print('---SCRIPT---');print(t)
else:
    print(s)
