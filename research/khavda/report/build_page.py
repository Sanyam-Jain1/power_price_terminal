"""Expand {{metric|fmt}} marks in index.src.html into headline-dataset marks; write index.html."""
import re, sys, os
here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, "index.src.html")).read()
def mark(m):
    metric, fmt, *tag = m.group(1).split("|")
    t = tag[0] if tag else "b"
    return f'<{t} data-draw="v" data-source="headline" data-where="metric={metric}" data-field="value" data-fmt="{fmt}">—</{t}>'
out = re.sub(r"\{\{([^}]+)\}\}", mark, src)
open(os.path.join(here, "index.html"), "w").write(out)
used = sorted(set(re.findall(r'metric=([a-z0-9_]+)', out)))
print(len(out), "bytes;", len(used), "metrics:", " ".join(used))
