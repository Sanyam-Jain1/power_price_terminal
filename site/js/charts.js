// Small SVG/canvas chart kit: line, bar (grouped, +/-), heatmap. No dependencies.
// Marks: 2px lines, 4px rounded bar ends, hairline solid grid, crosshair tooltips.

const NS = "http://www.w3.org/2000/svg";
const M = { top: 12, right: 16, bottom: 26, left: 48 };

function svgEl(tag, attrs = {}, style = {}) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  Object.assign(e.style, style);
  return e;
}

export function niceTicks(lo, hi, n = 5) {
  if (!isFinite(lo) || !isFinite(hi)) return [0, 1];
  if (lo === hi) { hi = lo + 1; }
  const span = hi - lo;
  const step0 = span / n;
  const mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => span / s <= n) || 10 * mag;
  const t0 = Math.floor(lo / step) * step;
  const out = [];
  for (let t = t0; t <= hi + step * 0.001; t += step) out.push(+t.toFixed(10));
  if (out[out.length - 1] < hi) out.push(out[out.length - 1] + step);
  return out;
}

function observe(el, draw) {
  let w = 0;
  const ro = new ResizeObserver(() => {
    const nw = Math.round(el.clientWidth);
    if (nw && nw !== w) { w = nw; draw(nw); }
  });
  ro.observe(el);
  return () => ro.disconnect();
}

function legend(series, kind = "line") {
  const div = document.createElement("div");
  div.className = "legend";
  for (const s of series) {
    const k = document.createElement("span");
    k.className = "key";
    const sw = document.createElement("span");
    sw.className = kind;
    sw.style.background = s.color;
    const t = document.createElement("span");
    t.textContent = s.name;
    k.append(sw, t);
    div.append(k);
  }
  return div;
}

function bandLegend(el, opts) {
  const labelled = (opts.bands || []).filter((b) => b.label);
  if (!labelled.length) return;
  const div = document.createElement("div");
  div.className = "legend";
  div.style.marginTop = "6px";
  for (const b of labelled) {
    const k = document.createElement("span");
    k.className = "key";
    const sw = document.createElement("span");
    sw.className = "rect";
    sw.style.background = "var(--ink-3)";
    sw.style.opacity = "0.35";
    const t = document.createElement("span");
    t.textContent = b.label;
    k.append(sw, t);
    div.append(k);
  }
  el.append(div);
}

function tooltipEl(host) {
  const tt = document.createElement("div");
  tt.className = "tooltip";
  tt.hidden = true;
  host.append(tt);
  return tt;
}

function fillTooltip(tt, title, rows) {
  tt.replaceChildren();
  const h = document.createElement("div");
  h.className = "tt-title";
  h.textContent = title;
  tt.append(h);
  for (const r of rows) {
    const row = document.createElement("div");
    row.className = "row";
    const k = document.createElement("span");
    k.className = "k";
    k.style.background = r.color;
    const b = document.createElement("b");
    b.textContent = r.value;
    const n = document.createElement("span");
    n.textContent = r.name;
    row.append(k, b, n);
    tt.append(row);
  }
}

function placeTooltip(tt, host, px, py) {
  tt.hidden = false;
  const w = tt.offsetWidth, hw = host.clientWidth;
  let x = px + 14;
  if (x + w > hw) x = px - w - 14;
  tt.style.left = `${Math.max(0, x)}px`;
  tt.style.top = `${Math.max(0, py - 10)}px`;
}

function yAxis(svg, ticks, y, x0, x1, fmt) {
  const g = svgEl("g", { class: "tick" });
  for (const t of ticks) {
    const yy = Math.round(y(t)) + 0.5;
    g.append(svgEl("line", { x1: x0, x2: x1, y1: yy, y2: yy, class: t === 0 ? "baseline" : "gridline" }));
    const tx = svgEl("text", { x: x0 - 6, y: yy + 3.5, "text-anchor": "end" });
    tx.textContent = fmt(t);
    g.append(tx);
  }
  svg.append(g);
}

function xLabels(svg, n, x, fmt, yPos, minGap = 52) {
  // Every index the formatter labels is a candidate; keep those at least minGap px apart.
  const g = svgEl("g", { class: "tick" });
  let last = -Infinity;
  for (let i = 0; i < n; i++) {
    const s = fmt(i);
    if (s == null || x(i) - last < minGap) continue;
    last = x(i);
    const tx = svgEl("text", { x: x(i), y: yPos, "text-anchor": "middle" });
    tx.textContent = s;
    g.append(tx);
  }
  svg.append(g);
}

function extent(series, opts) {
  let lo = Infinity, hi = -Infinity;
  for (const s of series) for (const v of s.values) if (v != null && isFinite(v)) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
  for (const r of opts.refLines || []) { lo = Math.min(lo, r.y); hi = Math.max(hi, r.y); }
  for (const b of opts.bands || []) { lo = Math.min(lo, b.y0); hi = Math.max(hi, b.y1); }
  if (opts.zero !== false) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
  if (opts.yMin != null) lo = opts.yMin;
  if (opts.yMax != null) hi = opts.yMax;
  if (!isFinite(lo)) { lo = 0; hi = 1; }
  return [lo, hi];
}

function refs(svg, opts, y, x0, x1) {
  for (const b of opts.bands || []) {
    // The band's label lives in the legend row under the chart (bars would cover it here).
    svg.append(svgEl("rect", { x: x0, width: x1 - x0, y: y(b.y1), height: Math.max(1, y(b.y0) - y(b.y1)) },
      { fill: "var(--ink-3)", opacity: 0.16, stroke: "none" }));
  }
  for (const r of opts.refLines || []) {
    const yy = Math.round(y(r.y)) + 0.5;
    svg.append(svgEl("line", { x1: x0, x2: x1, y1: yy, y2: yy }, { stroke: "var(--ink-3)", strokeWidth: 1 }));
    if (r.label) {
      const t = svgEl("text", { x: x0 + 4, y: yy - 4, class: "reflabel" });
      t.textContent = r.label;
      svg.append(t);
    }
  }
}

/** Line chart with crosshair tooltip, legend for >=2 series, sparing end labels. */
export function lineChart(el, opts) {
  const { x, series, height = 260 } = opts;
  const yFmt = opts.yFmt || ((v) => String(v));
  const tipFmt = opts.tipFmt || yFmt;
  const xFmt = opts.xFmt || ((i) => x[i]);
  const titleFmt = opts.titleFmt || ((i) => x[i]);
  el.replaceChildren();
  el.classList.add("chart");
  if (series.length >= 2) el.append(legend(series));
  const host = document.createElement("div");
  host.style.position = "relative";
  el.append(host);
  const tt = tooltipEl(host);
  const endLabels = opts.endLabels !== false && series.length <= 4 && series.length >= 2;
  const right = endLabels ? 70 : M.right;

  const draw = (W) => {
    host.querySelector("svg")?.remove();
    const svg = svgEl("svg", { width: W, height, role: "img", "aria-label": opts.label || "line chart" });
    host.prepend(svg);
    const x0 = M.left, x1 = W - right, y0 = height - M.bottom, y1 = M.top;
    const [lo, hi] = extent(series, opts);
    const ticks = niceTicks(lo, hi, opts.ticks || 5);
    const tlo = ticks[0], thi = ticks[ticks.length - 1];
    const y = (v) => y0 - ((v - tlo) / (thi - tlo || 1)) * (y0 - y1);
    const n = x.length;
    const xs = (i) => x0 + (n <= 1 ? 0 : (i / (n - 1)) * (x1 - x0));
    refs(svg, opts, y, x0, x1);
    yAxis(svg, ticks, y, x0, x1, yFmt);
    xLabels(svg, n, xs, xFmt, height - 8);
    for (const s of series) {
      let d = "", pen = false;
      s.values.forEach((v, i) => {
        if (v == null || !isFinite(v)) { pen = false; return; }
        d += `${pen ? "L" : "M"}${xs(i).toFixed(1)},${y(v).toFixed(1)}`;
        pen = true;
      });
      if (s.area) {
        const pts = s.values.map((v, i) => [i, v]).filter(([, v]) => v != null);
        if (pts.length) {
          const a = `M${xs(pts[0][0])},${y(Math.max(tlo, 0))}` + pts.map(([i, v]) => `L${xs(i)},${y(v)}`).join("") +
            `L${xs(pts[pts.length - 1][0])},${y(Math.max(tlo, 0))}Z`;
          svg.append(svgEl("path", { d: a }, { fill: s.color, opacity: 0.1, stroke: "none" }));
        }
      }
      svg.append(svgEl("path", { d, fill: "none" }, {
        stroke: s.color, strokeWidth: s.width || 2, strokeLinejoin: "round", strokeLinecap: "round",
        strokeDasharray: s.dash ? "4 4" : "none",
      }));
    }
    if (endLabels) {
      const labs = series.map((s) => {
        let i = s.values.length - 1;
        while (i >= 0 && (s.values[i] == null || !isFinite(s.values[i]))) i--;
        return i < 0 ? null : { s, i, y: y(s.values[i]) };
      }).filter(Boolean).sort((a, b) => a.y - b.y);
      let last = -Infinity;
      for (const l of labs) {
        const ly = Math.max(l.y, last + 13);
        last = ly;
        if (Math.abs(ly - l.y) > 2) {
          svg.append(svgEl("line", { x1: xs(l.i) + 4, x2: x1 + 6, y1: l.y, y2: ly }, { stroke: "var(--axis)", strokeWidth: 1 }));
        }
        const t = svgEl("text", { x: x1 + 8, y: ly + 4, class: "endlabel" });
        t.textContent = l.s.short || l.s.name;
        svg.append(t);
        svg.append(svgEl("circle", { cx: xs(l.i), cy: l.y, r: 4 }, { fill: l.s.color, stroke: "var(--surface-1)", strokeWidth: 2 }));
      }
    }
    const cross = svgEl("line", { y1: y1, y2: y0, class: "crosshair", visibility: "hidden" });
    svg.append(cross);
    const dots = series.map((s) => {
      const c = svgEl("circle", { r: 4, visibility: "hidden" }, { fill: s.color, stroke: "var(--surface-1)", strokeWidth: 2 });
      svg.append(c);
      return c;
    });
    const overlay = svgEl("rect", { x: x0, y: y1, width: Math.max(1, x1 - x0), height: y0 - y1, fill: "transparent" });
    svg.append(overlay);
    let cur = -1;
    const show = (i) => {
      if (i < 0 || i >= n) return;
      cur = i;
      const cx = xs(i);
      cross.setAttribute("x1", cx); cross.setAttribute("x2", cx); cross.setAttribute("visibility", "visible");
      const rows = [];
      series.forEach((s, k) => {
        const v = s.values[i];
        if (v == null || !isFinite(v)) { dots[k].setAttribute("visibility", "hidden"); return; }
        dots[k].setAttribute("cx", cx); dots[k].setAttribute("cy", y(v)); dots[k].setAttribute("visibility", "visible");
        rows.push({ color: s.color, name: s.name, value: tipFmt(v, s) });
      });
      fillTooltip(tt, titleFmt(i), rows);
      placeTooltip(tt, host, cx, y1 + 8);
    };
    const hide = () => {
      cross.setAttribute("visibility", "hidden");
      dots.forEach((d) => d.setAttribute("visibility", "hidden"));
      tt.hidden = true;
    };
    overlay.addEventListener("pointermove", (ev) => {
      const r = svg.getBoundingClientRect();
      const px = ev.clientX - r.left;
      show(Math.round(((px - x0) / (x1 - x0 || 1)) * (n - 1)));
    });
    overlay.addEventListener("pointerleave", hide);
    el.onkeydown = (ev) => {
      if (ev.key === "ArrowRight") { show(Math.min(n - 1, cur + 1)); ev.preventDefault(); }
      if (ev.key === "ArrowLeft") { show(Math.max(0, cur < 0 ? n - 1 : cur - 1)); ev.preventDefault(); }
      if (ev.key === "Escape") hide();
    };
    el.onfocus = () => show(cur < 0 ? n - 1 : cur);
    el.onblur = hide;
  };
  el.tabIndex = 0;
  return observe(host, draw);
}

function barPath(x, w, yBase, yVal, r = 4) {
  const h = yBase - yVal;
  if (Math.abs(h) < 0.5) return `M${x},${yBase}h${w}`;
  const rr = Math.min(r, Math.abs(h), w / 2);
  if (h > 0) {   // positive bar, round the top
    return `M${x},${yBase}V${yVal + rr}Q${x},${yVal} ${x + rr},${yVal}H${x + w - rr}Q${x + w},${yVal} ${x + w},${yVal + rr}V${yBase}Z`;
  }
  return `M${x},${yBase}V${yVal - rr}Q${x},${yVal} ${x + rr},${yVal}H${x + w - rr}Q${x + w},${yVal} ${x + w},${yVal - rr}V${yBase}Z`;
}

/** Column chart: grouped series, negatives allowed, optional reference band/lines. */
export function barChart(el, opts) {
  const { labels, series, height = 240 } = opts;
  const yFmt = opts.yFmt || ((v) => String(v));
  const tipFmt = opts.tipFmt || yFmt;
  const xFmt = opts.xFmt || ((i) => labels[i]);
  el.replaceChildren();
  el.classList.add("chart");
  if (series.length >= 2) el.append(legend(series, "rect"));
  const host = document.createElement("div");
  host.style.position = "relative";
  el.append(host);
  const tt = tooltipEl(host);
  bandLegend(el, opts);
  const draw = (W) => {
    host.querySelector("svg")?.remove();
    const svg = svgEl("svg", { width: W, height, role: "img", "aria-label": opts.label || "bar chart" });
    host.prepend(svg);
    const x0 = M.left, x1 = W - M.right, y0 = height - M.bottom, y1 = M.top + (opts.capLabels ? 12 : 0);
    const [lo, hi] = extent(series, opts);
    const ticks = niceTicks(lo, hi, 5);
    const tlo = ticks[0], thi = ticks[ticks.length - 1];
    const y = (v) => y0 - ((v - tlo) / (thi - tlo || 1)) * (y0 - y1);
    const n = labels.length, band = (x1 - x0) / Math.max(1, n);
    const gap = 2, k = series.length;
    const bw = Math.max(1, Math.min(24, (band * 0.72 - gap * (k - 1)) / k));
    const groupW = bw * k + gap * (k - 1);
    refs(svg, opts, y, x0, x1);
    yAxis(svg, ticks, y, x0, x1, yFmt);
    xLabels(svg, n, (i) => x0 + band * (i + 0.5), xFmt, height - 8);
    const base = y(Math.max(tlo, Math.min(0, thi)));
    labels.forEach((_, i) => {
      const gx = x0 + band * (i + 0.5) - groupW / 2;
      series.forEach((s, j) => {
        const v = s.values[i];
        if (v == null || !isFinite(v)) return;
        const bx = gx + j * (bw + gap);
        const p = svgEl("path", { d: barPath(bx, bw, base, y(v)) }, { fill: s.colors?.[i] || s.color });
        svg.append(p);
        if (opts.capLabels && n <= 24 && j === k - 1 && k === 1) {
          const t = svgEl("text", { x: bx + bw / 2, y: (v >= 0 ? y(v) - 4 : y(v) + 12), "text-anchor": "middle", class: "endlabel" });
          t.textContent = opts.capFmt ? opts.capFmt(v) : yFmt(v);
          svg.append(t);
        }
      });
      const hit = svgEl("rect", { x: x0 + band * i, y: y1, width: band, height: y0 - y1, fill: "transparent" });
      hit.addEventListener("pointermove", () => {
        fillTooltip(tt, opts.titleFmt ? opts.titleFmt(i) : labels[i], series
          .filter((s) => s.values[i] != null)
          .map((s) => ({ color: s.colors?.[i] || s.color, name: s.name, value: tipFmt(s.values[i], s, i) })));
        placeTooltip(tt, host, x0 + band * (i + 0.5), y1 + 8);
        hit.setAttribute("fill", "var(--wash)");
      });
      hit.addEventListener("pointerleave", () => { tt.hidden = true; hit.setAttribute("fill", "transparent"); });
      svg.append(hit);
    });
    // Band edges sit above the bars so the reference range stays readable.
    for (const b of opts.bands || []) {
      for (const v of [b.y0, b.y1]) {
        const yy = Math.round(y(v)) + 0.5;
        svg.insertBefore(svgEl("line", { x1: x0, x2: x1, y1: yy, y2: yy }, { stroke: "var(--ink-2)", strokeWidth: 1, opacity: 0.7 }),
          svg.querySelector("rect[fill='transparent']"));
      }
    }
  };
  return observe(host, draw);
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** Days x 96-block price heatmap on canvas; one-hue sequential ramp. */
export function heatmap(el, opts) {
  const { rows, values, min = 0, max = 10000 } = opts;
  const fmt = opts.fmt || ((v) => String(v));
  el.replaceChildren();
  el.classList.add("chart");
  const host = document.createElement("div");
  host.style.position = "relative";
  el.append(host);
  const tt = tooltipEl(host);
  const scale = document.createElement("div");
  scale.className = "scale";
  el.append(scale);
  const ramp = ["--seq-0", "--seq-1", "--seq-2", "--seq-3", "--seq-4", "--seq-5", "--seq-6"].map(cssVar);
  const rgb = ramp.map((h) => [1, 3, 5].map((o) => parseInt(h.slice(o, o + 2), 16)));
  const colorAt = (v) => {
    const t = Math.max(0, Math.min(1, (v - min) / (max - min || 1))) * (rgb.length - 1);
    const a = Math.floor(t), b = Math.min(rgb.length - 1, a + 1), f = t - a;
    return `rgb(${rgb[a].map((c, i) => Math.round(c + (rgb[b][i] - c) * f)).join(",")})`;
  };
  const lo = document.createElement("span"); lo.textContent = fmt(min);
  const bar = document.createElement("span"); bar.className = "bar";
  bar.style.background = `linear-gradient(90deg, ${ramp.join(",")})`;
  const hiS = document.createElement("span"); hiS.textContent = fmt(max);
  const none = document.createElement("span"); none.textContent = "· blank = no trade";
  scale.append(lo, bar, hiS, none);
  const L = 74, T = 16;
  const draw = (W) => {
    host.querySelector("canvas")?.remove();
    const cols = 96;
    const cw = (W - L) / cols;
    const ch = Math.max(4, Math.min(14, opts.rowHeight || 10));
    const H = T + ch * rows.length + 2;
    const dpr = window.devicePixelRatio || 1;
    const c = document.createElement("canvas");
    c.className = "heat";
    c.width = Math.round(W * dpr); c.height = Math.round(H * dpr);
    c.style.height = `${H}px`;
    c.setAttribute("role", "img");
    c.setAttribute("aria-label", opts.label || "price heatmap");
    host.prepend(c);
    const g = c.getContext("2d");
    g.scale(dpr, dpr);
    g.font = `11px ${getComputedStyle(document.body).fontFamily}`;
    g.fillStyle = cssVar("--muted");
    g.textAlign = "center";
    for (let h = 0; h < 24; h += 3) g.fillText(`${String(h).padStart(2, "0")}:00`, L + h * 4 * cw + 2 * cw, 11);
    g.textAlign = "right";
    const every = Math.max(1, Math.ceil(12 / ch));
    rows.forEach((r, i) => {
      if (i % every === 0) g.fillText(opts.rowFmt ? opts.rowFmt(r) : r, L - 8, T + ch * i + ch - 1);
      const vals = values[i] || [];
      for (let j = 0; j < cols; j++) {
        const v = vals[j];
        if (v == null || !isFinite(v)) continue;
        g.fillStyle = colorAt(v);
        g.fillRect(L + j * cw, T + i * ch, Math.ceil(cw), ch - (ch > 6 ? 1 : 0));
      }
    });
    c.onpointermove = (ev) => {
      const r = c.getBoundingClientRect();
      const px = ev.clientX - r.left, py = ev.clientY - r.top;
      const j = Math.floor((px - L) / cw), i = Math.floor((py - T) / ch);
      if (i < 0 || i >= rows.length || j < 0 || j >= cols) { tt.hidden = true; return; }
      const v = values[i]?.[j];
      fillTooltip(tt, `${opts.rowFmt ? opts.rowFmt(rows[i]) : rows[i]} · ${blockLabel(j)}`,
        [{ color: v == null ? "transparent" : colorAt(v), name: opts.unit || "", value: v == null ? "no trade" : fmt(v) }]);
      placeTooltip(tt, host, px, py);
    };
    c.onpointerleave = () => { tt.hidden = true; };
  };
  return observe(host, draw);
}

export function blockLabel(j) {
  const m = j * 15;
  const e = m + 15;
  const f = (x) => `${String(Math.floor(x / 60)).padStart(2, "0")}:${String(x % 60).padStart(2, "0")}`;
  return `${f(m)}–${f(e)}`;
}

/** Render a plain table (the accessible twin of a chart). */
export function table(headers, rows, numeric = []) {
  const wrap = document.createElement("div");
  wrap.className = "tablewrap";
  const t = document.createElement("table");
  const thead = document.createElement("thead");
  const tr = document.createElement("tr");
  headers.forEach((h, i) => {
    const th = document.createElement("th");
    th.textContent = h;
    if (numeric.includes(i)) th.className = "n";
    tr.append(th);
  });
  thead.append(tr);
  const tb = document.createElement("tbody");
  for (const r of rows) {
    const row = document.createElement("tr");
    r.forEach((c, i) => {
      const td = document.createElement("td");
      if (c instanceof Node) td.append(c); else td.textContent = c == null ? "–" : String(c);
      if (numeric.includes(i)) td.className = "n";
      row.append(td);
    });
    tb.append(row);
  }
  t.append(thead, tb);
  wrap.append(t);
  return wrap;
}
