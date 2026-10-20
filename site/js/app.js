import { barChart, blockLabel, heatmap, lineChart, slotLabel, table } from "./charts.js";
import { card, download, h, markdown, tile } from "./dom.js";
import * as f from "./format.js";

// ------------------------------------------------------------------ state
const store = {
  get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
};
const state = { tier: store.get("dhruva.tier", "free"), range: store.get("dhruva.range", "30") };
const isPro = () => state.tier === "pro";

const COLORS = { dam: "var(--s1)", rtm: "var(--s2)", gdam: "var(--s3)", hpdam: "var(--s4)" };
const SHORT = { dam: "DAM", rtm: "RTM", gdam: "G-DAM", hpdam: "HP-DAM" };

const cache = new Map();
function load(name) {
  if (!cache.has(name)) {
    cache.set(name, fetch(`data/${name}`).then((r) => {
      if (!r.ok) throw new Error(`${name}: HTTP ${r.status}`);
      return name.endsWith(".md") ? r.text() : r.json();
    }).catch((e) => { cache.delete(name); throw e; }));
  }
  return cache.get(name);
}

// ------------------------------------------------------------------ helpers
const hours = (i) => (i % 12 === 0 ? `${String(i / 4).padStart(2, "0")}:00` : null);
const lastIdx = (arr) => { for (let i = arr.length - 1; i >= 0; i--) if (arr[i] != null) return i; return -1; };
const mean = (a) => { const v = a.filter((x) => x != null && isFinite(x)); return v.length ? v.reduce((s, x) => s + x, 0) / v.length : null; };
const vwap = (p, v) => { let n = 0, d = 0; p.forEach((x, i) => { if (x != null && v[i] > 0) { n += x * v[i]; d += v[i]; } }); return d ? n / d : null; };

function rangeDays() {
  if (!isPro()) return 30;
  return state.range === "all" ? Infinity : +state.range;
}
function sliceLast(obj, keys, n) {
  const len = obj[keys[0]].length;
  const s = Number.isFinite(n) ? Math.max(0, len - n) : 0;
  const out = {};
  for (const k of keys) out[k] = obj[k].slice(s);
  return out;
}

function rangeControl(onChange) {
  const opts = [["30", "30 days"], ["90", "90 days"], ["365", "1 year"], ["all", "All (from Apr 2024)"]];
  const seg = h("div", { class: "seg", role: "group", "aria-label": "Time range" });
  for (const [v, label] of opts) {
    const locked = !isPro() && v !== "30";
    const b = h("button", {
      "aria-pressed": String((isPro() ? state.range : "30") === v), title: locked ? "Pro: full history" : null,
      onclick: () => {
        if (locked) { setTier("pro", true); return; }
        state.range = v; store.set("dhruva.range", v); onChange();
      },
    }, label, locked ? h("span", { class: "pro-badge" }, "PRO") : null);
    seg.append(b);
  }
  return h("label", {}, "Range", seg);
}

function lockCard(title, what) {
  return h("div", { class: "lock" }, h("b", {}, title), h("p", {}, what),
    h("button", { class: "btn small", onclick: () => setTier("pro", true) }, "Preview Pro"));
}

function tableToggle(c, build) {
  let shown = null;
  const b = h("button", {
    class: "iconbtn", "aria-expanded": "false", onclick: () => {
      if (shown) { shown.remove(); shown = null; b.setAttribute("aria-expanded", "false"); b.textContent = "Table"; return; }
      shown = h("div", { style: { marginTop: "10px", maxHeight: "360px", overflow: "auto" } }, build());
      c.append(shown);
      b.setAttribute("aria-expanded", "true");
      b.textContent = "Hide table";
    },
  }, "Table");
  c.actions.append(b);
}

function csvButton(c, filename, rowsFn) {
  const b = h("button", {
    class: "iconbtn", title: isPro() ? "Download CSV" : "Pro: data downloads",
    onclick: () => (isPro() ? download(filename, rowsFn()) : setTier("pro", true)),
  }, "CSV", isPro() ? null : h("span", { class: "pro-badge" }, "PRO"));
  c.actions.append(b);
}

function pageHead(title, blurb, ...extra) {
  return h("div", { class: "page-head" }, h("div", {}, h("h1", {}, title), blurb ? h("p", {}, blurb) : null), ...extra);
}

function dhruvaHead(title, blurb, ...extra) {
  return h("div", {},
    h("div", { class: "dhruva-banner" }, h("span", { class: "dhruva-chip" }, "Dhruva research"),
      h("span", {}, "Modelled by Dhruva from public exchange data. These are not exchange-published prices. "),
      h("a", { href: "#methodology" }, "Methodology")),
    pageHead(title, blurb, ...extra));
}

const mount = (el, fn, ...args) => { const host = h("div"); el.append(host); fn(host, ...args); return host; };

// ------------------------------------------------------------------ pages

async function overview(root) {
  const [spot, fut, ref] = await Promise.all([load("spot.json"), load("futures.json"), load("reference.json")]);
  root.append(pageHead("Every Indian power price, one screen",
    "Exchange and published data only: IEX day-ahead, real-time, green and high-price markets by 15-minute block, bid-area prices, NSE futures, term-ahead auctions, RECs, tender awards and open-access landed cost."));

  const dam = spot.dam.daily;
  const i = lastIdx(dam.vwap);
  const prev7 = mean(dam.vwap.slice(Math.max(0, i - 7), i));
  const grid = h("div", { class: "grid" });
  root.append(grid);

  const hero = h("div", { class: "card tile hero c4" },
    h("div", { class: "label" }, `DAM volume-weighted price · delivery ${f.dLong(dam.dates[i])}`),
    h("div", { class: "value" }, f.kwh(dam.vwap[i]), h("small", {}, "/kWh")),
    f.delta(f.pct(dam.vwap[i], dam.vwap[i - 1]), "vs previous day"), h("br"),
    f.delta(f.pct(dam.vwap[i], prev7), "vs 7-day average"),
    h("div", { class: "note" }, `Block average ${f.kwh(dam.avg[i])} · evening peak ${f.kwh(dam.evening_peak[i])} · solar hours ${f.kwh(dam.solar[i])} · ${dam.cap_blocks[i]} blocks at the ₹10 cap`));
  grid.append(hero);

  const side = h("div", { class: "c8 side-grid" });
  grid.append(side);
  const addTile = (el) => { side.append(el); return el; };
  const rtm = spot.rtm.daily, j = lastIdx(rtm.vwap);
  const fullRtm = rtm.blocks[j] >= 96 ? j : j - 1;
  addTile(tile(`RTM · ${f.dShort(rtm.dates[fullRtm])}`, f.kwh(rtm.vwap[fullRtm]), "/kWh",
    f.delta(f.pct(rtm.vwap[fullRtm], rtm.vwap[fullRtm - 1]), "d/d")));
  const g = spot.gdam.daily, k = lastIdx(g.vwap);
  addTile(tile(`G-DAM · ${f.dShort(g.dates[k])}`, f.kwh(g.vwap[k]), "/kWh", f.delta(f.pct(g.vwap[k], g.vwap[k - 1]), "d/d")));
  const hp = spot.hpdam.daily, hi = hp.dates.length - 1;
  addTile(tile(`HP-DAM · ${f.dShort(hp.dates[hi])}`, f.int(hp.volume_mwh[hi] ?? 0), "MWh cleared", null,
    hp.vwap[hi] != null ? `at ${f.kwh(hp.vwap[hi])}/kWh` : "Nothing cleared above the cap"));
  const front = fut.contracts.find((c) => c.last || c.prev_close);
  const frontPx = front ? (front.last || front.prev_close) : null;
  addTile(tile(`NSE future · ${front ? f.monthLong(front.delivery_month) : ""}`, frontPx ? f.mwh(frontPx) : "–", "/MWh",
    front ? f.delta(front.change_pct, "today") : null, front ? `OI ${f.int(front.open_interest)} lots · snapshot ${f.dShort(fut.latest_snapshot)}` : "No snapshot yet"));
  const tam = fut.tam.find((r) => r.instrument.startsWith("MTH-BAS"));
  addTile(tile(`TAM monthly base · ${tam ? tam.delivery_month : ""}`, tam ? f.mwh(tam.price_rs_mwh) : "–", "/MWh", null,
    tam ? `auction ${f.dShort(tam.auction_date)} · ${f.fixed(tam.volume_mu, 1)} MU` : null));
  const rec = ref.rec[ref.rec.length - 1];
  addTile(tile(`REC · session ${rec ? f.dShort(rec.session_date) : ""}`, rec ? `₹${rec.price_rs_per_rec}` : "–", "/REC", null,
    rec ? `${f.int(rec.cleared_volume)} cleared` : null));

  // Latest delivery day that RTM has completed, so all three markets are comparable.
  const days = spot.rtm.recent.dates;
  let di = days.length - 1;
  while (di > 0 && spot.rtm.recent.mcp[di].filter((v) => v != null).length < 96) di--;
  const day = days[di];
  const series = ["dam", "rtm", "gdam"].map((m) => {
    const r = spot[m].recent, ix = r.dates.indexOf(day);
    return { name: spot[m].label, short: SHORT[m], color: COLORS[m], values: ix < 0 ? [] : r.mcp[ix] };
  });
  const c1 = card(`Block prices · ${f.dLong(day)}`, "₹/kWh by 15-minute block");
  mount(c1, (el) => lineChart(el, { x: [...Array(96).keys()], series, yFmt: f.kwhAxis, tipFmt: (v) => f.kwh(v), xFmt: hours,
    titleFmt: (i) => blockLabel(i), height: 280, label: "Block prices by market" }));
  tableToggle(c1, () => table(["Block", ...series.map((s) => s.short)], [...Array(96).keys()].map((b) =>
    [blockLabel(b), ...series.map((s) => f.kwh(s.values[b]))]), [1, 2, 3]));
  grid.append(h("div", { class: "c8" }, c1));

  const ds = sliceLast(spot.dam.daily, ["dates"], 30).dates;
  const dser = ["dam", "rtm", "gdam"].map((m) => {
    const dd = spot[m].daily, idx = new Map(dd.dates.map((x, ii) => [x, ii]));
    return { name: spot[m].label, short: SHORT[m], color: COLORS[m], values: ds.map((x) => (idx.has(x) && dd.blocks[idx.get(x)] >= 96 ? dd.vwap[idx.get(x)] : null)) };
  });
  const c2 = card("Daily volume-weighted price", "last 30 delivery days");
  mount(c2, (el) => lineChart(el, { x: ds, series: dser, yFmt: f.kwhAxis, tipFmt: (v) => f.kwh(v), xFmt: (i) => f.dShort(ds[i]),
    titleFmt: (i) => f.dLong(ds[i]), height: 280 }));
  tableToggle(c2, () => table(["Date", ...dser.map((s) => s.short)], ds.map((x, ii) => [x, ...dser.map((s) => f.kwh(s.values[ii]))]).reverse(), [1, 2, 3]));
  grid.append(h("div", { class: "c4" }, c2));

  const tc = card("Latest tender awards", "discovered tariffs");
  tc.classList.add("nowrap1");
  tc.append(table(["Date", "Authority", "Category", "Tariff"], ref.tenders.slice(0, 6).map((t) => [f.dShort(t.result_date), t.authority,
    h("span", { class: "tag" }, t.category),
    `${t.tariff_low === t.tariff_high ? f.fixed(t.tariff_low) : `${f.fixed(t.tariff_low)}–${f.fixed(t.tariff_high)}`} ${t.unit}`])),
  h("a", { href: "#tenders" }, "All tenders →"));
  grid.append(h("div", { class: "c6" }, tc));

  const cov = card("Coverage", "market data and where it comes from");
  const rows = [
    ["IEX DAM, RTM, G-DAM, HP-DAM", "15-min blocks, from Apr 2024", "live"],
    ["DAM bid-area prices (13 areas)", "15-min blocks", "live"],
    ["NSE electricity futures", "daily snapshot", "live"],
    ["MCX electricity futures", "manual CSV hook (MCX blocks data-centre IPs)", "manual"],
    ["IEX term-ahead monthly auctions", "each auction", "live"],
    ["IEX REC sessions", "each session", "live"],
    ["Tenders: BESS, FDRE, solar, wind", "curated, every row sourced", "manual"],
    ["Open-access landed cost (IEX calculator)", "39 discoms × category × voltage", "live"],
    ["DSM, SRAS and TRAS settlements (ERPC, WRPC, NERPC)", "weekly accounts, ~2 weeks lag", "live"],
    ["Grid frequency", "15-min block averages from RPC data", "live"],
    ["NRPC and SRPC accounts, Grid-India reports", "not publicly reachable", "planned"],
  ];
  cov.append(table(["Dataset", "Granularity", "Status"], rows.map(([a, b, s]) =>
    [a, b, h("span", { class: `status-dot${s === "live" ? "" : " warn"}` }, s)])),
  h("p", { class: "note" }, "Dhruva's own indices and models are kept separately, in the Dhruva section."));
  grid.append(h("div", { class: "c6" }, cov));
}

async function spotPage(root) {
  const spot = await load("spot.json");
  root.append(pageHead("Spot markets", "IEX clearing prices by 15-minute block. Prices are market clearing prices (MCP); G-DAM shows the unconstrained MCP. The DAM and RTM ceiling is ₹10/kWh."));
  let market = new URLSearchParams(location.hash.split("?")[1] || "").get("m") || "dam";
  const body = h("div");
  const mSel = h("select", { "aria-label": "Market", onchange: (e) => { market = e.target.value; render(); } },
    Object.keys(spot).map((m) => h("option", { value: m, selected: m === market || null }, spot[m].label)));
  const dSel = h("select", { "aria-label": "Delivery date" });
  root.append(h("div", { class: "controls" }, h("label", {}, "Market", mSel), h("label", {}, "Day", dSel), rangeControl(() => render())), body);

  async function render() {
    body.replaceChildren();
    const m = spot[market];
    let src = m.recent;
    if (isPro() && rangeDays() > 30) {
      body.append(h("p", { class: "muted small" }, "Loading full history…"));
      src = await load(`history/${market}.json`);
      body.replaceChildren();
    }
    const n = Math.min(rangeDays(), src.dates.length);
    const dates = src.dates.slice(-n), mcp = src.mcp.slice(-n), vol = src.vol.slice(-n);
    const prevDay = dSel.value;
    dSel.replaceChildren(...dates.slice().reverse().map((x) => h("option", { value: x }, f.dLong(x))));
    if (prevDay && dates.includes(prevDay)) dSel.value = prevDay;
    dSel.onchange = () => drawDay();
    const grid = h("div", { class: "grid" });
    body.append(grid);
    const tiles = h("div", { class: "c12 grid", style: { gap: "14px" } });
    const dayCard = card("Block prices", "");
    const volCard = card("Cleared volume", "MW by block");
    grid.append(tiles, h("div", { class: "c8" }, dayCard), h("div", { class: "c4" }, volCard));

    function drawDay() {
      const ix = dates.indexOf(dSel.value);
      const p = mcp[ix], v = vol[ix];
      const prev = ix > 0 ? mcp[ix - 1] : null;
      tiles.replaceChildren();
      const add = (t) => { t.classList.add("c3"); tiles.append(t); };
      const pv = prev ? vwap(prev, vol[ix - 1]) : null;
      add(tile("Volume-weighted price", f.kwh(vwap(p, v)), "/kWh", f.delta(f.pct(vwap(p, v), pv), "vs previous day")));
      add(tile("Block average", f.kwh(mean(p)), "/kWh", null, `min ${f.kwh(Math.min(...p.filter((x) => x != null)))} · max ${f.kwh(Math.max(...p.filter((x) => x != null)))}`));
      add(tile("Evening peak 18–23h", f.kwh(mean(p.slice(72, 92))), "/kWh", null, `solar 09–16h ${f.kwh(mean(p.slice(36, 64)))}`));
      add(tile("Cleared energy", f.int(v.reduce((s, x) => s + (x || 0), 0) / 4), "MWh", null,
        `${p.filter((x) => x >= 9999.5).length} blocks at the cap`));
      dayCard.querySelector(".sub").textContent = `${m.label} · ${f.dLong(dates[ix])}`;
      dayCard.querySelectorAll(".chart, .tablewrap").forEach((e) => e.remove());
      const series = [{ name: f.dShort(dates[ix]), color: COLORS[market], values: p }];
      if (prev) series.push({ name: `${f.dShort(dates[ix - 1])} (previous day)`, short: "prev", color: "var(--muted)", values: prev, width: 1.5 });
      mount(dayCard, (el) => lineChart(el, { x: [...Array(96).keys()], series, yFmt: f.kwhAxis, tipFmt: (x) => f.kwh(x),
        xFmt: hours, titleFmt: (i) => blockLabel(i), height: 280, refLines: [{ y: 10000, label: "₹10 cap" }] }));
      volCard.querySelectorAll(".chart").forEach((e) => e.remove());
      mount(volCard, (el) => barChart(el, { labels: [...Array(96).keys()], series: [{ name: "MW", color: COLORS[market], values: v }],
        yFmt: f.compact, tipFmt: (x) => `${f.int(x)} MW`, xFmt: hours, titleFmt: (i) => blockLabel(i), height: 280 }));
    }
    if (!dayCard.actions.childElementCount) {
      tableToggle(dayCard, () => { const ix = dates.indexOf(dSel.value); return table(["Block", "MCP ₹/MWh", "Volume MW"],
        mcp[ix].map((x, b) => [blockLabel(b), f.int(x), f.int(vol[ix][b])]), [1, 2]); });
      csvButton(dayCard, `dhruva_${market}_blocks.csv`, () => [["date", "block", "start", "mcp_rs_mwh", "volume_mw"],
        ...dates.flatMap((x, di) => mcp[di].map((p, b) => [x, b + 1, blockLabel(b).slice(0, 5), p, vol[di][b]]))]);
    }
    drawDay();

    const hc = card("Price heatmap", `${dates.length} days × 96 blocks · darker = higher price`);
    mount(hc, (el) => heatmap(el, { rows: dates.slice().reverse(), values: mcp.slice().reverse(), min: 0, max: 10000,
      fmt: (x) => f.kwh(x), rowFmt: (x) => f.dShort(x), unit: "/kWh", rowHeight: dates.length > 120 ? 4 : 10 }));
    grid.append(h("div", { class: "c12" }, hc));

    const dd = m.daily;
    const n2 = Math.min(rangeDays(), dd.dates.length);
    const sl = sliceLast(dd, ["dates", "vwap", "avg", "evening_peak", "solar", "min", "max", "cap_blocks", "volume_mwh"], n2);
    const tc = card("Daily summary", "₹/kWh");
    mount(tc, (el) => lineChart(el, { x: sl.dates, series: [
      { name: "Evening peak 18–23h", short: "Evening", color: "var(--s2)", values: sl.evening_peak },
      { name: "Volume-weighted", short: "VWAP", color: COLORS[market] === "var(--s2)" ? "var(--s1)" : COLORS[market], values: sl.vwap },
      { name: "Solar hours 09–16h", short: "Solar", color: "var(--s4)", values: sl.solar },
    ], yFmt: f.kwhAxis, tipFmt: (x) => f.kwh(x), xFmt: (i) => f.dShort(sl.dates[i]),
      titleFmt: (i) => f.dLong(sl.dates[i]), height: 260 }));
    tableToggle(tc, () => table(["Date", "VWAP", "Avg", "Evening", "Solar", "Min", "Max", "At cap", "MWh"],
      sl.dates.map((x, i) => [x, f.kwh(sl.vwap[i]), f.kwh(sl.avg[i]), f.kwh(sl.evening_peak[i]), f.kwh(sl.solar[i]),
        f.kwh(sl.min[i]), f.kwh(sl.max[i]), sl.cap_blocks[i], f.int(sl.volume_mwh[i])]).reverse(), [1, 2, 3, 4, 5, 6, 7, 8]));
    csvButton(tc, `dhruva_${market}_daily.csv`, () => [["date", "vwap", "avg", "evening_peak", "solar", "min", "max", "cap_blocks", "volume_mwh"],
      ...sl.dates.map((x, i) => [x, sl.vwap[i], sl.avg[i], sl.evening_peak[i], sl.solar[i], sl.min[i], sl.max[i], sl.cap_blocks[i], sl.volume_mwh[i]])]);
    grid.append(h("div", { class: "c12" }, tc));
    if (market === "gdam" && m.latest_mix) {
      const mc = card("G-DAM cleared mix", f.dLong(m.latest_mix.date));
      mount(mc, (el) => lineChart(el, { x: [...Array(96).keys()], series: [
        { name: "Solar (other RE)", short: "Solar", color: "var(--s4)", values: m.latest_mix.solar_mw },
        { name: "Wind", color: "var(--s1)", values: m.latest_mix.wind_mw },
        { name: "Hydro", color: "var(--s3)", values: m.latest_mix.hydro_mw },
      ], yFmt: f.compact, tipFmt: (x) => `${f.int(x)} MW`, xFmt: hours, titleFmt: blockLabel, height: 220 }));
      grid.append(h("div", { class: "c12" }, mc));
    }
  }
  render();
}

async function regionsPage(root) {
  const reg = await load("regions.json");
  root.append(pageHead("Regions", "DAM prices for IEX's 13 bid areas. When transmission corridors congest, India splits and areas clear at different prices. Since market coupling began in January 2026, that split is the regional signal."));
  const grid = h("div", { class: "grid" });
  root.append(grid);
  const n = reg.dates.length, last = n - 1;
  const areas = Object.keys(reg.areas);
  const lt = reg.latest || {};
  const rows = areas.map((a) => {
    const blocks = lt.blocks?.[a] || [];
    const avg = mean(blocks), mk = mean(lt.mkt || []);
    const d30 = mean(reg.areas[a].daily_avg.slice(-30)), m30 = mean(reg.mkt_daily_avg.slice(-30));
    return [h("b", {}, a), reg.areas[a].region, reg.areas[a].states, f.kwh(avg), f.mwh(avg != null && mk != null ? avg - mk : null),
      f.kwh(d30), f.mwh(d30 != null && m30 != null ? d30 - m30 : null)];
  });
  const tc = card("Bid areas", lt.date ? `delivery ${f.dLong(lt.date)}` : "");
  tc.append(table(["Area", "Region", "States", "Day avg ₹/kWh", "vs all-India ₹/MWh", "30-day avg", "30-day vs all-India"], rows, [3, 4, 5, 6]));
  grid.append(h("div", { class: "c7" }, tc));

  const span = Math.min(isPro() ? 365 : 30, n);
  const ds = reg.dates.slice(-span);
  const sc = card("Market splitting", `blocks per day where at least one area cleared differently · last ${span} days`);
  mount(sc, (el) => barChart(el, { labels: ds, series: [{ name: "Split blocks", color: "var(--s7)", values: reg.split_blocks.slice(-span) }],
    yFmt: (x) => String(x), tipFmt: (x, s, i) => `${x} of 96 blocks · max spread ${f.mwh(reg.max_spread.slice(-span)[i])}/MWh`,
    xFmt: (i) => f.dShort(ds[i]), titleFmt: (i) => f.dLong(ds[i]), height: 260 }));
  sc.append(h("p", { class: "note" }, `Split on ${reg.split_blocks.slice(-span).filter((x) => x > 0).length} of ${ds.length} days in this window.`));
  if (!isPro()) sc.append(h("p", { class: "note" }, "Free view shows 30 days. Pro shows a year."));
  grid.append(h("div", { class: "c5" }, sc));

  const sp = reg.latest_split || lt;
  // Show the cheapest and dearest areas on the split day, plus all-India.
  const avgs = areas.map((a) => [a, mean(sp.blocks?.[a] || [])]).sort((x, y) => x[1] - y[1]);
  const pick = [...new Set([avgs[0][0], avgs[avgs.length - 1][0]])];
  const lc = card("Area prices on the latest split day", sp.date ? f.dLong(sp.date) : "");
  mount(lc, (el) => lineChart(el, { x: [...Array(96).keys()], series: [
    ...pick.map((a, i) => ({ name: `${a} · ${reg.areas[a].region} (${i ? "highest" : "lowest"} day average)`, short: a, color: `var(--s${i + 1})`, values: sp.blocks[a] })),
    { name: "All-India MCP", short: "MCP", color: "var(--s3)", values: sp.mkt || [] }],
  yFmt: f.kwhAxis, tipFmt: (x) => f.kwh(x), xFmt: hours, titleFmt: blockLabel, height: 260 }));
  lc.append(h("p", { class: "note" }, "Where the lines separate, a transmission corridor was congested and that area cleared at its own price."));
  grid.append(h("div", { class: "c6" }, lc));

}

async function futuresPage(root) {
  const fut = await load("futures.json");
  root.append(pageHead("Futures and term-ahead",
    "NSE and MCX list monthly base-load electricity futures (50 MWh lots), cash-settled on the month's volume-weighted IEX DAM unconstrained MCP. IEX's term-ahead market auctions physical monthly contracts."));
  const grid = h("div", { class: "grid" });
  root.append(grid);
  const traded = fut.contracts.filter((c) => c.last || c.prev_close);
  const span = `c${12 / Math.max(1, Math.min(4, traded.length))}`;
  traded.slice(0, 4).forEach((c) => {
    const t = tile(`NSE ${f.monthLong(c.delivery_month)}`, f.mwh(c.last || c.prev_close), "/MWh", f.delta(c.change_pct, "today"),
      `expiry ${f.dShort(c.expiry)} · ${f.int(c.volume_lots)} lots · OI ${f.int(c.open_interest)}`);
    t.classList.add(span);
    grid.append(t);
  });

  const cc = card("Listed contracts", fut.latest_snapshot ? `NSE ELECMBL · ${f.dLong(fut.latest_snapshot)}` : "");
  cc.append(table(["Exchange", "Delivery", "Expiry", "Last ₹/MWh", "Prev close", "Chg %", "Lots", "OI"],
    fut.contracts.map((c) => [c.exchange, f.monthLong(c.delivery_month), f.dShort(c.expiry), f.int(c.last), f.int(c.prev_close), f.fixed(c.change_pct, 2), f.int(c.volume_lots), f.int(c.open_interest)]),
    [3, 4, 5, 6, 7]));
  cc.append(h("p", { class: "note" }, "MCX blocks automated access from data-centre IPs. Drop a CSV at data/manual/mcx_futures.csv (same columns) to include it."));
  grid.append(h("div", { class: "c6" }, cc));

  const pc = card("Futures price by snapshot", "₹/MWh, last or previous close");
  const months = [...new Set(fut.series.map((s) => s.month))].sort().slice(0, 4);
  const xs = [...new Set(fut.series.flatMap((s) => s.points.map((p) => p[0])))].sort();
  if (xs.length >= 2) {
    mount(pc, (el) => lineChart(el, { x: xs, series: months.map((m, i) => {
      const pts = new Map(fut.series.find((s) => s.month === m).points);
      return { name: `NSE ${f.monthLabel(m)}`, color: `var(--s${i + 1})`, values: xs.map((x) => pts.get(x) ?? null) };
    }), yFmt: f.compact, tipFmt: (v) => `${f.mwh(v)}/MWh`, zero: false, xFmt: (i) => f.dShort(xs[i]), titleFmt: (i) => f.dLong(xs[i]), height: 240 }));
  } else {
    pc.append(h("p", { class: "empty" }, `One snapshot so far (${f.dLong(xs[0])}). NSE publishes no history for these contracts, so the series grows by one point each trading day.`));
  }
  grid.append(h("div", { class: "c6" }, pc));

  const tc = card("Term-ahead market: monthly auctions", "IEX TAM, physical delivery");
  tc.append(table(["Auction", "Instrument", "Delivery", "Volume MU", "Price ₹/MWh"],
    fut.tam.slice(0, 12).map((r) => [f.dShort(r.auction_date), r.instrument, r.delivery_month, f.fixed(r.volume_mu, 2), f.int(r.price_rs_mwh)]), [3, 4]));
  tc.append(h("p", { class: "note" }, "TAM contracts are physical and often peak-shaped or round-the-clock. They are not directly comparable to cash-settled base-load futures."));
  grid.append(h("div", { class: "c12" }, tc));
}

async function recPage(root) {
  const ref = await load("reference.json");
  root.append(pageHead("Renewable Energy Certificates", "IEX REC sessions, held twice a month. Since the Dec 2022 rules, RECs trade as a single instrument with technology multipliers."));
  const rec = ref.rec;
  if (!rec.length) { root.append(h("p", { class: "empty" }, "No REC sessions ingested yet.")); return; }
  const sl = isPro() ? rec : rec.slice(-12);
  const grid = h("div", { class: "grid" });
  root.append(grid);
  const lastR = rec[rec.length - 1], prevR = rec[rec.length - 2];
  [tile(`Latest clearing price · ${f.dShort(lastR.session_date)}`, `₹${lastR.price_rs_per_rec}`, "/REC", f.delta(f.pct(lastR.price_rs_per_rec, prevR.price_rs_per_rec), "vs previous session")),
    tile("Cleared volume", f.int(lastR.cleared_volume), "RECs", null, `${f.int(lastR.buy_bids)} buy vs ${f.int(lastR.sell_bids)} sell bids`),
    tile("Buy/sell ratio", f.fixed(lastR.buy_bids / lastR.sell_bids, 2), "×", null, "Above 1 means demand exceeded supply"),
    tile("Participants", f.int(lastR.participants), "", null, "")].forEach((t) => { t.classList.add("c3"); grid.append(t); });
  const c = card("Clearing price by session", "₹/REC");
  mount(c, (el) => barChart(el, { labels: sl.map((r) => r.session_date), series: [{ name: "Price", color: "var(--s3)", values: sl.map((r) => r.price_rs_per_rec) }],
    yFmt: (x) => `₹${x}`, tipFmt: (v, s, i) => `₹${v}/REC · ${f.int(sl[i].cleared_volume)} cleared`, zero: true,
    xFmt: (i) => f.dShort(sl[i].session_date), titleFmt: (i) => f.dLong(sl[i].session_date), height: 260 }));
  tableToggle(c, () => table(["Session", "Price ₹/REC", "Cleared", "Buy bids", "Sell bids", "Participants"],
    rec.slice().reverse().map((r) => [r.session_date, r.price_rs_per_rec, f.int(r.cleared_volume), f.int(r.buy_bids), f.int(r.sell_bids), r.participants]), [1, 2, 3, 4, 5]));
  csvButton(c, "dhruva_rec_sessions.csv", () => [["session_date", "price_rs_per_rec", "cleared_volume", "buy_bids", "sell_bids", "participants"],
    ...rec.map((r) => [r.session_date, r.price_rs_per_rec, r.cleared_volume, r.buy_bids, r.sell_bids, r.participants])]);
  if (!isPro()) c.append(h("p", { class: "note" }, "Free view: last 12 sessions. Pro: from Jan 2024."));
  grid.append(h("div", { class: "c12" }, c));
}

async function tendersPage(root) {
  const ref = await load("reference.json");
  root.append(pageHead("Tender results", "Discovered tariffs from central and state auctions for standalone batteries, firm and dispatchable RE (FDRE), solar, solar-plus-storage and wind. Every row links to its source."));
  const cats = ["All", ...new Set(ref.tenders.map((t) => t.category))];
  let cat = "All";
  const body = h("div");
  root.append(h("div", { class: "controls" }, h("label", {}, "Category",
    h("select", { onchange: (e) => { cat = e.target.value; render(); } }, cats.map((c) => h("option", { value: c }, c))))), body);
  function render() {
    body.replaceChildren();
    const rows = ref.tenders.filter((t) => cat === "All" || t.category === cat);
    const grid = h("div", { class: "grid" });
    body.append(grid);
    if (cat === "All" || cat === "BESS") {
      const b = ref.tenders.filter((t) => t.category === "BESS").sort((x, y) => x.result_date.localeCompare(y.result_date));
      const dur = (t) => Math.round(t.energy_mwh / t.capacity_mw);
      const c = card("Standalone battery tenders", "lowest discovered tariff · ₹ lakh/MW/month");
      mount(c, (el) => barChart(el, { labels: b.map((t) => `${t.authority} ${dur(t)}h · ${f.dShort(t.result_date)}`),
        series: [{ name: "Discovered tariff", color: "var(--s1)", colors: b.map((t) => (dur(t) >= 4 ? "var(--s7)" : "var(--s1)")), values: b.map((t) => t.tariff_low) }],
        yFmt: (x) => f.fixed(x, 1), tipFmt: (v, s, i) => `₹${f.fixed(v)} L/MW/mo · ${dur(b[i])}h · ${b[i].title}`,
        titleFmt: (i) => b[i].authority, height: 240, capLabels: true, capFmt: (v) => f.fixed(v) }));
      c.append(h("div", { class: "legend", style: { marginTop: "6px" } },
        h("span", { class: "key" }, h("span", { class: "rect", style: { background: "var(--s1)" } }), "2-hour"),
        h("span", { class: "key" }, h("span", { class: "rect", style: { background: "var(--s7)" } }), "4-hour")));
      grid.append(h("div", { class: "c12" }, c));
    }
    const tc = card("Results", `${rows.length} awards`);
    tc.classList.add("nowrap1");
    tc.append(table(["Date", "Authority", "Category", "Project", "Capacity", "Tariff", "Winners", "Source"],
      rows.map((t) => [t.result_date, t.authority, h("span", { class: "tag" }, t.category), t.title,
        `${f.int(t.capacity_mw)} MW${t.energy_mwh ? ` / ${f.int(t.energy_mwh)} MWh` : ""}`,
        `${t.tariff_low === t.tariff_high ? f.fixed(t.tariff_low) : `${f.fixed(t.tariff_low)}–${f.fixed(t.tariff_high)}`} ${t.unit}`,
        t.winners || "–", h("a", { href: t.source, target: "_blank", rel: "noopener" }, "source")]), []));
    tc.append(h("p", { class: "note" }, "Curated from IEEFA/JMK Research, Mercom, pv magazine India, SolarQuarter and Renewable Watch. CERC adoption orders are marked in the project column."));
    grid.append(h("div", { class: "c12" }, tc));
  }
  render();
}

async function openAccessPage(root) {
  const ref = await load("reference.json");
  const L = ref.landed;
  root.append(pageHead("Open-access landed cost",
    "What an industrial or commercial buyer pays to bring exchange power to their meter, by discom, compared with the discom's own tariff. Charges and losses come from IEX's landed-cost calculator."));
  const cats = [...new Set(L.rows.map((r) => r.category))].sort();
  const volts = [...new Set(L.rows.map((r) => r.voltage_kv))].sort((a, b) => a - b);
  let cat = cats.includes("Industrial General") ? "Industrial General" : cats[0];
  let volt = volts.includes(33) ? 33 : volts[0];
  let price = L.reference_price_rs_kwh || 4.5;
  const body = h("div");
  const priceIn = h("input", { type: "number", step: "0.05", min: "0", max: "20", value: price, style: { width: "90px" },
    oninput: (e) => { price = +e.target.value || 0; render(); } });
  root.append(h("div", { class: "controls" },
    h("label", {}, "Consumer category", h("select", { onchange: (e) => { cat = e.target.value; render(); } }, cats.map((c) => h("option", { value: c, selected: c === cat || null }, c)))),
    h("label", {}, "Voltage", h("select", { onchange: (e) => { volt = +e.target.value; render(); } }, volts.map((v) => h("option", { value: v, selected: v === volt || null }, `${v} kV`)))),
    h("label", {}, "Exchange price ₹/kWh", priceIn),
    h("span", { class: "muted small" }, `Default: ${L.reference_note}. Calculator data fetched ${L.fetched || "–"}.`)), body);
  function render() {
    body.replaceChildren();
    const rows = L.rows.filter((r) => r.category === cat && r.voltage_kv === volt)
      .map((r) => ({ ...r, landed: r.intercept_rs_kwh + r.slope * price }))
      .map((r) => ({ ...r, saving: r.discom_tariff_rs_kwh - r.landed, breakeven: (r.discom_tariff_rs_kwh - r.intercept_rs_kwh) / r.slope }))
      .sort((a, b) => b.saving - a.saving);
    if (!rows.length) { body.append(h("p", { class: "empty" }, "No discoms publish this category at this voltage.")); return; }
    const c = card("Saving vs discom tariff", `₹/kWh at ₹${price.toFixed(2)} exchange price · positive = open access is cheaper`);
    mount(c, (el) => barChart(el, { labels: rows.map((r) => r.state), series: [{ name: "Saving", color: "var(--s1)",
      colors: rows.map((r) => (r.saving >= 0 ? "var(--s1)" : "var(--s8)")), values: rows.map((r) => r.saving) }],
    yFmt: (x) => `₹${x.toFixed(1)}`, tipFmt: (v, s, i) => `₹${v.toFixed(2)}/kWh saving · landed ₹${rows[i].landed.toFixed(2)} vs discom ₹${rows[i].discom_tariff_rs_kwh.toFixed(2)}`,
    xFmt: () => null, titleFmt: (i) => rows[i].state, height: 260 }));
    c.append(h("div", { class: "legend", style: { marginTop: "6px" } },
      h("span", { class: "key" }, h("span", { class: "rect", style: { background: "var(--s1)" } }), "open access cheaper"),
      h("span", { class: "key" }, h("span", { class: "rect", style: { background: "var(--s8)" } }), "discom cheaper")));
    body.append(c);
    const t = card("By discom", `${rows.length} discoms · ${cat} · ${volt} kV`);
    const cheaper = rows.filter((r) => r.saving > 0).length;
    c.append(h("p", { class: "note" }, `At ₹${price.toFixed(2)}/kWh, open access beats the discom in ${cheaper} of ${rows.length} discoms. `
      + "Round-the-clock exchange power includes the capped evening blocks; buyers who schedule into solar hours pay far less. The break-even column gives the exchange price below which open access wins."));
    t.append(table(["Discom", "Landed ₹/kWh", "Discom tariff", "Saving", "Break-even price", "CSS", "Add'l surcharge", "Wheeling", "STU", "ISTS", "Losses %"],
      rows.map((r) => [r.state, f.fixed(r.landed), f.fixed(r.discom_tariff_rs_kwh), f.fixed(r.saving), r.breakeven > 0 ? f.fixed(r.breakeven) : "never", f.fixed(r.css), f.fixed(r.additional_surcharge),
        f.fixed(r.wheeling_charge), f.fixed(r.stu_charge), f.fixed(r.ists_charge), f.fixed((r.ists_loss_pct || 0) + (r.stu_loss_pct || 0) + (r.wheeling_loss_pct || 0), 1)]),
      [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]));
    t.append(h("p", { class: "note" }, "Landed cost = fixed charges + exchange price grossed up for ISTS, STU and wheeling losses. It is fitted exactly from two calculator runs per discom (the calculation is linear in price). The discom tariff is energy + fuel/FSA + ToD charges for the RTC slot. Green-OA banking, demand charges and electricity duty are excluded."));
    t.style.marginTop = "14px";
    body.append(t);
  }
  render();
}

async function bessPage(root) {
  const bess = await load("bess.json");
  const I = bess.indices;
  const [ref, reg] = await Promise.all([load("reference.json"), load("regions.json")]);
  root.append(dhruvaHead("Battery revenue index (DBX)",
    `What a 1 MW battery would have earned from exchange arbitrage. Perfect-foresight daily optimisation on IEX 15-minute prices, ${(I["DBX-2H"].rte * 100).toFixed(0)}% round-trip efficiency, ₹${I["DBX-2H"].fee}/MWh exchange fee per side. Methodology v${bess.method_version}.`));
  const grid = h("div", { class: "grid" });
  root.append(grid);
  const two = I["DBX-2H"], lastM = two.monthly[two.monthly.length - 1];
  grid.append(h("div", { class: "card tile hero c4" },
    h("div", { class: "label" }, `DBX-2H · ${f.monthLong(lastM.month)} run-rate (${lastM.days}/${lastM.days_in_month} days)`),
    h("div", { class: "value" }, f.fixed(lastM.run_rate), h("small", {}, "₹ lakh/MW/month")),
    h("div", { class: "note" }, `Month to date ₹${f.fixed(lastM.lakh)} lakh/MW · trailing 12-month average ₹${f.fixed(two.trailing_365_lakh_per_mw_month)} lakh/MW/month`)));
  const t = card("Index family", "trailing 12-month average, ₹ lakh/MW/month");
  t.append(table(["Ticker", "Market", "Duration", "Cycles/day", "Latest month run-rate", "Trailing 12m"],
    Object.entries(I).map(([k, v]) => [h("b", {}, k), v.market.toUpperCase(), `${v.duration_h}h`, v.cycles, f.fixed(v.monthly.at(-1)?.run_rate), f.fixed(v.trailing_365_lakh_per_mw_month)]),
    [3, 4, 5]));
  grid.append(h("div", { class: "c8" }, t));

  for (const [name, band] of [["DBX-2H", { y0: 2.10, y1: 2.32, label: "2026 GUVNL 2h tenders ₹2.10–2.32" }], ["DBX-4H", { y0: 3.47, y1: 4.39, label: "2026 WBSEDCL 4h tenders ₹3.47–4.39" }]]) {
    const ms = I[name].monthly.slice(isPro() ? 0 : -6);
    const c = card(`${name} by month`, "₹ lakh/MW/month · latest month at run-rate");
    mount(c, (el) => barChart(el, { labels: ms.map((m) => m.month), series: [{ name, color: name === "DBX-2H" ? "var(--s1)" : "var(--s7)",
      values: ms.map((m) => (m.days < m.days_in_month ? m.run_rate : m.lakh)) }], bands: [band],
    yFmt: (x) => f.fixed(x, 1), tipFmt: (v, s, i) => `₹${f.fixed(v)} L/MW/mo${ms[i].days < ms[i].days_in_month ? ` (run-rate, ${ms[i].days} days)` : ""}`,
    xFmt: (i) => f.monthLabel(ms[i].month), titleFmt: (i) => f.monthLong(ms[i].month), height: 250, capLabels: ms.length <= 12, capFmt: (v) => f.fixed(v, 1) }));
    tableToggle(c, () => table(["Month", "₹ lakh/MW", "Days", "Run-rate"], I[name].monthly.slice().reverse().map((m) => [f.monthLong(m.month), f.fixed(m.lakh), `${m.days}/${m.days_in_month}`, f.fixed(m.run_rate)]), [1, 3]));
    csvButton(c, `dhruva_${name}_daily.csv`, () => [["date", "revenue_rs_per_mw", "cycles", "avg_buy_rs_mwh", "avg_sell_rs_mwh"],
      ...I[name].daily.dates.map((x, i) => [x, I[name].daily.revenue[i], I[name].daily.cycles[i], I[name].daily.avg_buy[i], I[name].daily.avg_sell[i]])]);
    if (!isPro()) c.append(h("p", { class: "note" }, "Free view: last 6 months. Pro: from April 2024, plus daily downloads."));
    grid.append(h("div", { class: "c6" }, c));
  }

  const dd = two.daily, n = Math.min(rangeDays(), dd.dates.length);
  const sl = sliceLast(dd, ["dates", "revenue"], n);
  const four = I["DBX-4H"].daily, fourIdx = new Map(four.dates.map((x, i) => [x, i]));
  const rtm = I["DBX-RTM-2H"].daily, rtmIdx = new Map(rtm.dates.map((x, i) => [x, i]));
  const c = card("Daily revenue", `₹/MW/day · last ${sl.dates.length} days`);
  mount(c, (el) => lineChart(el, { x: sl.dates, series: [
    { name: "DBX-4H", color: "var(--s7)", values: sl.dates.map((x) => four.revenue[fourIdx.get(x)] ?? null) },
    { name: "DBX-2H", color: "var(--s1)", values: sl.revenue },
    { name: "DBX-RTM-2H", short: "RTM-2H", color: "var(--s2)", values: sl.dates.map((x) => rtm.revenue[rtmIdx.get(x)] ?? null) },
  ], yFmt: f.compact, tipFmt: (v) => `₹${f.int(v)}`, xFmt: (i) => f.dShort(sl.dates[i]),
    titleFmt: (i) => f.dLong(sl.dates[i]), height: 260 }));
  root.append(h("div", { class: "controls", style: { marginTop: "14px" } }, rangeControl(() => route())));
  root.append(c);

  const dp = bess.dispatch["DBX-2H"];
  if (dp) {
    const g2 = h("div", { class: "grid", style: { marginTop: "14px" } });
    root.append(g2);
    const p = card(`What DBX-2H did · ${f.dLong(dp.date)}`, `DAM price, ₹/kWh · earned ₹${f.int(dp.revenue)}/MW`);
    mount(p, (el) => lineChart(el, { x: [...Array(96).keys()], series: [{ name: "DAM price", color: "var(--s1)", values: dp.price }],
      yFmt: f.kwhAxis, tipFmt: (x) => f.kwh(x), xFmt: hours, titleFmt: blockLabel, height: 200 }));
    const s = card("Charge and discharge", "MW · discharge positive, charge negative");
    mount(s, (el) => barChart(el, { labels: [...Array(96).keys()], series: [{ name: "MW", color: "var(--s1)",
      colors: dp.discharge.map((dch) => (dch > 0 ? "var(--s1)" : "var(--s2)")), values: dp.discharge.map((dch, i) => dch - dp.charge[i]) }],
    yFmt: (x) => x.toFixed(1), tipFmt: (v) => (v > 0 ? `discharge ${v.toFixed(2)} MW` : v < 0 ? `charge ${(-v).toFixed(2)} MW` : "idle"),
    xFmt: hours, titleFmt: blockLabel, height: 200 }));
    s.append(h("div", { class: "legend", style: { marginTop: "6px" } },
      h("span", { class: "key" }, h("span", { class: "rect", style: { background: "var(--s1)" } }), "discharge (sell)"),
      h("span", { class: "key" }, h("span", { class: "rect", style: { background: "var(--s2)" } }), "charge (buy)")));
    g2.append(h("div", { class: "c6" }, p), h("div", { class: "c6" }, s));
  }

  const g3 = h("div", { class: "grid", style: { marginTop: "14px" } });
  root.append(g3);
  const b = ref.tenders.filter((t) => t.category === "BESS").sort((x, y) => x.result_date.localeCompare(y.result_date));
  const dur = (t) => Math.round(t.energy_mwh / t.capacity_mw);
  const twoT = I["DBX-2H"].trailing_365_lakh_per_mw_month, fourT = I["DBX-4H"].trailing_365_lakh_per_mw_month;
  const tc = card("Tender tariffs vs the DBX ceiling", "₹ lakh/MW/month");
  mount(tc, (el) => barChart(el, { labels: b.map((t) => `${t.authority} ${dur(t)}h · ${f.dShort(t.result_date)}`),
    series: [{ name: "Discovered tariff", color: "var(--s1)", colors: b.map((t) => (dur(t) >= 4 ? "var(--s7)" : "var(--s1)")), values: b.map((t) => t.tariff_low) }],
    refLines: [{ y: twoT, label: `DBX-2H trailing 12m ${f.fixed(twoT)}` }, { y: fourT, label: `DBX-4H trailing 12m ${f.fixed(fourT)}` }],
    yFmt: (x) => f.fixed(x, 1), tipFmt: (v, s, i) => `₹${f.fixed(v)} L/MW/mo · ${dur(b[i])}h · ${b[i].title}`,
    titleFmt: (i) => b[i].authority, height: 260, capLabels: true, capFmt: (v) => f.fixed(v) }));
  tc.append(h("div", { class: "legend", style: { marginTop: "6px" } },
    h("span", { class: "key" }, h("span", { class: "rect", style: { background: "var(--s1)" } }), "2-hour tender (compare with DBX-2H)"),
    h("span", { class: "key" }, h("span", { class: "rect", style: { background: "var(--s7)" } }), "4-hour tender (compare with DBX-4H)")),
  h("p", { class: "note" }, "Bars are actual discovered tariffs (see Tenders). Lines are Dhruva's modelled merchant ceiling. A tender tariff is a contracted capacity payment; where it sits below the ceiling, the buyer keeps the arbitrage value."));
  g3.append(h("div", { class: "c12" }, tc));

  const areas = Object.keys(reg.areas);
  const bc = card("Regional battery index", "DBX-2H spec on each bid area's DAM price · ₹ lakh/MW/month");
  if (isPro()) {
    const bm = reg.bess_monthly;
    bc.append(table(["Area", "Region", ...bm.months.slice(-6).map(f.monthLabel)],
      areas.map((a) => [a, reg.areas[a].region, ...bm.areas[a].slice(-6).map((v) => f.fixed(v))]), [2, 3, 4, 5, 6, 7]));
    bc.append(h("p", { class: "note" }, "The latest month is month-to-date. Areas only diverge when the grid splits."));
  } else bc.append(lockCard("Enterprise: regional battery indices", "Battery revenue by bid area, for siting and for lenders' location-specific models."));
  g3.append(h("div", { class: "c12" }, bc));
}

// ------------------------------------------------------------------ grid & balancing (published data)
const STATUS = {
  ok: ["Parsed", ""], partial: ["Partly parsed", "warn"], source_mismatch: ["Totals don't tie", "warn"],
  unvalidated: ["No total to check", "warn"], parse_error: ["Could not parse", "bad"], unreachable: ["Unreachable", "bad"],
  blocked: ["Login required", "bad"], not_published: ["Not published", "muted"], missing: ["Not in files", "muted"], check: ["Responding", "warn"],
};
const statusChip = (st) => { const [label, cls] = STATUS[st] || [st || "unknown", "muted"]; return h("span", { class: `status-dot ${cls}` }, label); };
const docLink = (d) => h("a", { href: d.url, target: "_blank", rel: "noopener" }, d.title || d.kind);
const lakhCr = (rs) => (rs == null ? "–" : `${rs < 0 ? "−" : ""}${Math.abs(rs) >= 1e7 ? `₹${f.fixed(Math.abs(rs) / 1e7, 2)} Cr` : `₹${f.fixed(Math.abs(rs) / 1e5, 2)} L`}`);
const periodLabel = (p) => `${f.dShort(p.from)} – ${f.dLong(p.to)}`;

function sourcesCard(G, ids, title = "Sources for this page") {
  const rows = G.sources.sources.filter((x) => ids.includes(x.id) || ids.includes(x.kind));
  const c = card(title, G.sources.generated ? `checked ${G.sources.generated.replace("T", " ")} IST` : "");
  c.classList.add("wide");
  c.append(table(["Source", "Status", "Data through", "Last checked", "Notes"], rows.map((x) => [
    h("a", { href: x.url, target: "_blank", rel: "noopener" }, x.name), statusChip(x.status), x.data_through ? f.dLong(x.data_through) : "–",
    (x.last_checked || "").replace("T", " "), x.message || (x.documents ? h("span", {}, ...Object.values(x.documents).flatMap((d, i) => [i ? " · " : "", docLink(d)])) : "")])));
  return c;
}

function gridHead(title, blurb) {
  return h("div", {}, h("div", { class: "dhruva-banner" }, h("span", { class: "dhruva-chip pub" }, "Published data"),
    h("span", {}, "Figures as published by the Regional Power Committees, parsed and checked against each table's own totals. "), h("a", { href: "#grid-sources" }, "Source status")),
  pageHead(title, blurb));
}

async function gridFrequencyPage(root) {
  const G = await load("grid.json");
  root.append(gridHead("Grid frequency", "All-India frequency in 15-minute blocks, as recorded in the RPCs' block-wise DSM data. The IEGC operating band is 49.90–50.05 Hz."));
  const F = G.frequency;
  if (!F.days.length) { root.append(h("p", { class: "empty" }, "No block-wise frequency data parsed yet."), sourcesCard(G, ["rpc", "GRID_INDIA_FREQ"])); return; }
  const lt = F.days[F.days.length - 1];
  const grid = h("div", { class: "grid" });
  root.append(grid);
  [tile(`Lowest block · ${f.dShort(lt.date)}`, f.fixed(lt.min, 2), "Hz"), tile("Highest block", f.fixed(lt.max, 2), "Hz"),
    tile("Blocks within 49.90–50.05 Hz", f.fixed(lt.in_band_pct, 1), "%", null, `${f.fixed(lt.below_49_90_pct, 1)}% below · ${f.fixed(lt.above_50_05_pct, 1)}% above`),
    tile("Daily mean", f.fixed(lt.mean, 3), "Hz")].forEach((t) => { t.classList.add("c3"); grid.append(t); });
  const c = card("Frequency by block", "Hz, 15-minute average");
  let day = F.latest.date;
  const fsel = h("select", { onchange: (e) => { day = e.target.value; drawDay(); } },
    F.days.slice().reverse().map((x) => h("option", { value: x.date }, f.dLong(x.date))));
  const fhost = h("div");
  const fnote = h("p", { class: "note" });
  c.append(h("div", { class: "controls" }, h("label", {}, "Day", fsel)), fhost, fnote);
  tableToggle(c, () => table(["Block", "Hz"], F.blocks[day].map((x, b) => [blockLabel(b), f.fixed(x, 3)]), [1]));
  function drawDay() {
    const dd = F.days.find((x) => x.date === day);
    lineChart(fhost, { x: [...Array(96).keys()], series: [{ name: "Frequency", color: "var(--s1)", values: F.blocks[day] }],
      refLines: [{ y: 50.05, label: "50.05 Hz" }, { y: 49.9, label: "49.90 Hz" }], zero: false,
      yMin: Math.min(49.85, dd.min - 0.02), yMax: Math.max(50.1, dd.max + 0.02),
      yFmt: (x) => x.toFixed(2), tipFmt: (x) => `${x.toFixed(3)} Hz`, xFmt: hours, titleFmt: blockLabel, height: 280 });
    fnote.replaceChildren(`${f.dLong(day)}: ${f.fixed(dd.in_band_pct, 1)}% of blocks in band, low ${f.fixed(dd.min, 2)} Hz, high ${f.fixed(dd.max, 2)} Hz. Source: `,
      ...dd.sources.flatMap((x, i) => [i ? ", " : "", h("a", { href: x.url, target: "_blank", rel: "noopener" }, `${x.rpc} block-wise DSM data`)]),
      ". These are 15-minute block averages, the finest resolution the RPCs publish, so they understate true minima and maxima. Grid-India's 10-second frequency profile is not reachable from Dhruva's servers; see Source status.");
  }
  drawDay();
  grid.append(h("div", { class: "c8" }, c));
  const d = card("Daily summary", `${F.days.length} days with published data`);
  d.append(h("div", { style: { maxHeight: "330px", overflowY: "auto" } },
    table(["Day", "Min Hz", "Max Hz", "Mean", "In band %"], F.days.slice().reverse().map((x) => [f.dShort(x.date), f.fixed(x.min, 2), f.fixed(x.max, 2), f.fixed(x.mean, 3), f.fixed(x.in_band_pct, 1)]), [1, 2, 3, 4])));
  grid.append(h("div", { class: "c4" }, d));
  const b = card("Share of blocks within 49.90–50.05 Hz", "% of 96 blocks per day");
  mount(b, (el) => barChart(el, { labels: F.days.map((x) => x.date), series: [{ name: "In band", color: "var(--s3)", values: F.days.map((x) => x.in_band_pct) }],
    yMax: 100, yFmt: (x) => `${x}%`, tipFmt: (x, s2, i) => `${f.fixed(x, 1)}% in band · min ${f.fixed(F.days[i].min, 2)} Hz · max ${f.fixed(F.days[i].max, 2)} Hz`,
    xFmt: (i) => f.dShort(F.days[i].date), titleFmt: (i) => f.dLong(F.days[i].date), height: 220 }));
  grid.append(h("div", { class: "c12" }, b));
  const hm = card("Every block, every day", `${F.days.length} days × 96 blocks · Hz, centred on 50.00`);
  const fdays = F.days.map((x) => x.date);
  mount(hm, (el) => heatmap(el, { rows: fdays, values: fdays.map((d) => F.blocks[d]), min: 49.85, max: 50.15, diverging: true, rowFmt: f.dShort,
    fmt: (v) => `${v.toFixed(2)} Hz`, tipFmt: (v) => `${v.toFixed(3)} Hz`, unit: "Frequency", blankText: "no data",
    blankLabel: "· blue: below 50 Hz (generation short) · red: above (surplus)", label: "frequency by block and day" }));
  grid.append(h("div", { class: "c12" }, hm));
  root.append(h("div", { style: { marginTop: "14px" } }, sourcesCard(G, ["rpc", "GRID_INDIA_FREQ"])));
}

// Net DSM colours: red = pays the pool, blue = receives from it (same poles as the diverging heatmap).
const PAYS = "var(--div-p2)", RECEIVES = "var(--div-n2)";
const signColor = (v) => (v >= 0 ? PAYS : RECEIVES);
const dayOpts = (dates, all = "Whole week") => [h("option", { value: "all" }, all), ...dates.map((d) => h("option", { value: d }, f.dLong(d)))];
const flat = (m) => m.flat();
// x-axis labels for a run of 15-minute blocks over one or more days.
const blockAxis = (dates) => (dates.length === 1 ? hours : (i) => (i % 96 === 0 ? f.dShort(dates[i / 96]) : null));
const blockTitle = (dates, per = 96, lab = blockLabel) => (i) => `${dates.length > 1 ? `${f.dShort(dates[Math.floor(i / per)])} · ` : ""}${lab(i % per)}`;

function reconBanner(W, settled) {
  const rc = W.reconciliation;
  const parts = [];
  if (rc) {
    parts.push(`${rc.ties} of ${rc.ties + rc.differs} entities in the weekly account tie to the rupee with the sum of their 15-minute blocks (payable and receivable).`);
    if (rc.unmatched) parts.push(`${rc.unmatched} further series in the block files have no row of their own in the weekly account (plants settled through an aggregator or QCA, infirm units, nuclear stations apportioned to states); they are shown, marked "Not settled separately", and left out of pool totals.`);
    if (rc.pdf_rows_without_block_data?.length) parts.push(`Account rows with no block data: ${rc.pdf_rows_without_block_data.join(", ")}.`);
  } else parts.push(W.message || "Block data could not be reconciled with the weekly account.");
  if (W.day_checks) parts.push(`${W.day_checks.checked - W.day_checks.failed} of ${W.day_checks.checked} entity-days also match the file's own daily totals.`);
  if (W.dsm_status === "source_mismatch") parts.push(`Note: ${W.dsm_message}`);
  return h("div", { class: `dhruva-banner ${W.status === "ok" ? "" : "warn"}` }, statusChip(W.status), h("span", {}, parts.join(" ")));
}

async function gridDsmPage(root) {
  const [G, GD] = await Promise.all([load("grid.json"), load("grid_daily.json")]);
  root.append(gridHead("Deviations (DSM)", "How far each entity strayed from schedule and what it paid into, or received from, the regional Deviation & Ancillary Service Pool, day by day and in every 15-minute block. Block data comes from each RPC's block-wise settlement files and is reconciled with its weekly account before it is shown."));
  const RS = GD.rpcs.filter((r) => r.dates.length);
  if (!RS.length) { root.append(h("p", { class: "empty" }, "No block-wise DSM data parsed yet."), sourcesCard(G, ["rpc"])); return; }
  const top = card("Biggest DSM payers", "net payable to the pool, latest week of each RPC · excludes inter-regional and cross-border lines");
  top.append(table(["Entity", "RPC · week", "Group", "Deviation MWh", "Payable", "Receivable", "Net payable"],
    G.top_payers.map((e) => [h("b", {}, e.name), `${e.rpc} · ${periodLabel(e.period)}`, e.group, f.int(e.deviation_mwh), lakhCr(e.payable_rs), lakhCr(e.receivable_rs), lakhCr(e.net_rs)]), [3, 4, 5, 6]));
  top.append(h("p", { class: "note" }, "Ranked across the three RPCs whose accounts are parsed (ERPC, WRPC, NERPC); NRPC and SRPC are missing (see Source status). Pick a region below for the day-by-day and block-by-block view."));
  root.append(h("div", { class: "grid" }, h("div", { class: "c12" }, top)));

  const st = { rpc: RS[0].rpc, week: null, day: "all", entity: null, group: "All", q: "" };
  const rsel = h("select", { onchange: (e) => { st.rpc = e.target.value; st.week = null; st.day = "all"; st.entity = null; draw(); } },
    RS.map((r) => h("option", { value: r.rpc }, `${r.rpc} · ${r.region}`)));
  const wsel = h("select", { onchange: (e) => { st.week = e.target.value; st.day = "all"; draw(); } });
  const dsel = h("select", { onchange: (e) => { st.day = e.target.value; draw(); } });
  root.append(h("div", { class: "controls", style: { marginTop: "14px" } }, h("label", {}, "Region", rsel), h("label", {}, "Week", wsel), h("label", {}, "Day", dsel)));
  const body = h("div");
  root.append(body);

  async function draw() {
    const R = RS.find((r) => r.rpc === st.rpc);
    const weeks = R.weeks.filter((w) => w.status !== "missing" && w.status !== "parse_error").slice().reverse();
    if (!st.week || !weeks.some((w) => w.key === st.week)) st.week = weeks[0].key;
    wsel.replaceChildren(...weeks.map((w) => h("option", { value: w.key, selected: w.key === st.week }, periodLabel(w.period))));
    const W = weeks.find((w) => w.key === st.week);
    const idx = await load(`grid/blocks/${W.key}/index.json`);
    dsel.replaceChildren(...dayOpts(idx.dates));
    dsel.value = st.day;
    const dates = st.day === "all" ? idx.dates : [st.day];
    const scope = st.day === "all" ? periodLabel(W.period) : f.dLong(st.day);
    const di = Object.fromEntries(R.dates.map((d, i) => [d, i]));
    const sumOver = (arr) => dates.reduce((a, d) => a + (arr[di[d]] || 0), 0);
    body.replaceChildren();
    const g = h("div", { class: "grid" });
    body.append(g);
    g.append(h("div", { class: "c12" }, reconBanner(W)));
    const pay = sumOver(R.pool.payable_rs), rec = sumOver(R.pool.receivable_rs);
    const settled = idx.entities.filter((e) => e.settled).length;
    [tile("Charges payable to pool", lakhCr(pay), "", null, scope), tile("Charges receivable from pool", lakhCr(rec), ""),
      tile("Pool balance", lakhCr(pay - rec), "", null, "payable − receivable, settled entities"),
      tile("Gross |deviation|", f.int(sumOver(R.pool.abs_deviation_mwh)), "MWh", null, `${settled} settled entities · ${R.region} region`)].forEach((t) => { t.classList.add("c3"); g.append(t); });

    const pc = card("Pool flows by day", `${R.rpc} · every day with published block data · ₹ crore`);
    mount(pc, (el) => barChart(el, { labels: R.dates, series: [
      { name: "Payable to pool", color: PAYS, values: R.pool.payable_rs.map((x) => (x == null ? null : x / 1e7)) },
      { name: "Receivable from pool", color: RECEIVES, values: R.pool.receivable_rs.map((x) => (x == null ? null : x / 1e7)) }],
    yFmt: (x) => f.fixed(x, 0), tipFmt: (x) => `₹${f.fixed(x, 2)} Cr`, xFmt: (i) => f.dShort(R.dates[i]), titleFmt: (i) => f.dLong(R.dates[i]), height: 220 }));
    tableToggle(pc, () => table(["Day", "Payable", "Receivable", "Balance", "|Deviation| MWh"], R.dates.map((d, i) => [f.dLong(d), lakhCr(R.pool.payable_rs[i]), lakhCr(R.pool.receivable_rs[i]), lakhCr(R.pool.payable_rs[i] - R.pool.receivable_rs[i]), f.int(R.pool.abs_deviation_mwh[i])]), [1, 2, 3, 4]));
    g.append(h("div", { class: "c12" }, pc));

    const hc = card("Pool net by block", `${R.rpc} · ${periodLabel(W.period)} · payable − receivable per 15-minute block, ₹ lakh`);
    const net = idx.pool.payable.map((row, i) => row.map((p, b) => (p - idx.pool.receivable[i][b]) / 1e5));
    const absv = net.flat().map(Math.abs).sort((a, b2) => a - b2);
    const M = Math.max(1, absv[Math.floor(absv.length * 0.98)] || 1);
    mount(hc, (el) => heatmap(el, { rows: idx.dates, values: net, min: -M, max: M, diverging: true, rowFmt: f.dShort, rowHeight: 16,
      fmt: (v) => `${v < 0 ? "−" : "+"}${f.fixed(Math.abs(v), 0)} L`, tipFmt: (v) => lakhCr(v * 1e5), unit: "Net to pool",
      blankLabel: "· red: entities pay the pool on balance · blue: the pool pays out", label: "DSM pool net by block" }));
    g.append(h("div", { class: "c12" }, hc));

    // Entities: daily nets, a check mark, and a drill-down per entity.
    const ents = R.entities.filter((e) => idx.entities.some((x) => x.block_name === e.block_name));
    const groups = ["All", ...new Set(ents.map((e) => e.group))];
    const tc = card("Entities", `${R.rpc} · ${scope} · net DSM (₹ lakh, + pays the pool) · pick one for its 15-minute blocks`);
    const gsel = h("select", { onchange: (e) => { st.group = e.target.value; fill(); } }, groups.map((x) => h("option", { value: x, selected: x === st.group }, x)));
    const search = h("input", { type: "search", placeholder: "Find entity", value: st.q, oninput: (e) => { st.q = e.target.value; fill(); } });
    const tbl = h("div", { style: { maxHeight: "460px", overflow: "auto" } });
    const check = (e) => (e.settled ? h("span", { class: "status-dot", title: e.match === "amount" ? "matched to its account row by amount" : "matched by name" }, e.ties ? "Ties" : "Differs")
      : h("span", { class: "status-dot muted", title: "No separate row in the weekly account" }, "Not settled separately"));
    const fill = () => {
      const rows = ents.filter((e) => (st.group === "All" || e.group === st.group) && (!st.q || `${e.name} ${e.block_name}`.toLowerCase().includes(st.q.toLowerCase())))
        .map((e) => ({ e, tot: dates.reduce((a, d) => a + (e.net_rs[di[d]] || 0), 0), dev: dates.reduce((a, d) => a + (e.abs_deviation_mwh[di[d]] || 0), 0) }))
        .sort((a, b2) => b2.tot - a.tot);
      const dayCols = dates.length > 1 ? dates.map((d) => f.dShort(d)) : [];
      tbl.replaceChildren(table(["Entity", "Group", ...dayCols, dates.length > 1 ? "Week net" : "Net", "|Deviation| MWh", "Check"],
        rows.map(({ e, tot, dev }) => [
          h("button", { class: "linkbtn", onclick: () => { st.entity = e.block_name; drill(); dc.scrollIntoView({ behavior: "smooth", block: "start" }); } }, e.name),
          e.group, ...(dates.length > 1 ? dates.map((d) => (e.net_rs[di[d]] == null ? "–" : f.fixed(e.net_rs[di[d]] / 1e5, 1))) : []),
          lakhCr(tot), f.int(dev), check(e)]),
        [...dayCols.map((_, i) => i + 2), dayCols.length + 2, dayCols.length + 3]));
    };
    fill();
    tc.append(h("div", { class: "controls" }, h("label", {}, "Group", gsel), h("label", {}, "Search", search)), tbl,
      h("p", { class: "note" }, "Names are as printed in the weekly account; where the block files use a different name it is matched by amount and shown on the entity page. Sources: ",
        ...W.documents.flatMap((d, i) => [i ? " · " : "", docLink(d)])));
    csvButton(tc, `dhruva_dsm_daily_${R.rpc}_${W.period.from}.csv`, () => [["entity", "name_in_block_file", "group", "settled", "date", "payable_rs", "receivable_rs", "net_rs", "abs_deviation_mwh"],
      ...ents.flatMap((e) => idx.dates.map((d) => [e.name, e.block_name, e.group, e.settled, d, e.payable_rs[di[d]], e.receivable_rs[di[d]], e.net_rs[di[d]], e.abs_deviation_mwh[di[d]]]))]);
    g.append(h("div", { class: "c12" }, tc));

    const dc = card("Entity detail", "pick an entity in the table above");
    g.append(h("div", { class: "c12" }, dc));
    async function drill() {
      const meta = idx.entities.find((x) => x.block_name === st.entity) || idx.entities.find((x) => x.settled);
      if (!meta) return;
      st.entity = meta.block_name;
      const E = await load(`grid/blocks/${W.key}/${meta.slug}.json`);
      const ix = dates.map((d) => E.dates.indexOf(d));
      const pick = (m) => (m ? ix.flatMap((i) => (i < 0 ? Array(96).fill(null) : m[i])) : null);
      const sch = pick(E.schedule_mwh), act = pick(E.actual_mwh), dev = pick(E.deviation_mwh);
      const recb = pick(E.receivable_rs);
      const netb = pick(E.payable_rs).map((p, i) => (p == null ? null : p - (recb[i] || 0)));
      const sras = pick(E.sras_mwh), nr = pick(E.normal_rate_rs_mwh);
      const x = [...Array(sch.length).keys()];
      const xFmt = blockAxis(dates), titleFmt = blockTitle(dates);
      dc.querySelector("h2").textContent = `${E.name}${E.block_name !== E.name ? ` (${E.block_name} in the block files)` : ""}`;
      dc.querySelector(".sub").textContent = `${R.rpc} · ${scope} · 15-minute blocks`;
      dc.querySelectorAll(":scope > :not(.card-head)").forEach((n) => n.remove());
      dc.actions.replaceChildren();
      const tot = netb.reduce((a, v) => a + (v || 0), 0);
      const dg = h("div", { class: "grid" });
      [tile("Net DSM", lakhCr(tot), "", null, tot >= 0 ? "pays the pool" : "receives from the pool"),
        tile("Gross |deviation|", f.int(dev.reduce((a, v) => a + Math.abs(v || 0), 0)), "MWh"),
        tile("Scheduled", f.int(sch.reduce((a, v) => a + (v || 0), 0)), "MWh", null, R.rpc === "ERPC" ? "ERPC states drawal as negative" : "as scheduled by the RLDC"),
        tile("Account check", meta.settled ? (meta.ties ? "Ties" : "Differs") : "Not settled separately", "", null,
          meta.settled ? `week's block sums vs the weekly account (matched by ${meta.match})` : "no separate row in the weekly account")].forEach((t) => { t.classList.add("c3"); dg.append(t); });
      dc.append(dg);
      const c1 = h("div", { style: { marginTop: "12px" } });
      dc.append(h("h3", { class: "minihead" }, "Schedule and actual, MWh per block"), c1);
      lineChart(c1, { x, series: [{ name: "Schedule", color: "var(--s1)", values: sch, dash: true }, { name: "Actual", color: "var(--s2)", values: act }],
        yFmt: f.compact, tipFmt: (v) => `${f.fixed(v, 2)} MWh`, xFmt, titleFmt, height: 240 });
      const c2 = h("div");
      dc.append(h("h3", { class: "minihead" }, "Deviation, MWh per block (actual − schedule)"), c2);
      const c3 = h("div");
      dc.append(h("h3", { class: "minihead" }, "Net DSM charge, ₹ per block (+ pays the pool)"), c3);
      if (dates.length === 1) {
        barChart(c2, { labels: x, series: [{ name: "Deviation", color: "var(--s7)", colors: dev.map((v) => (v >= 0 ? "var(--s7)" : "var(--s4)")), values: dev }],
          yFmt: f.compact, tipFmt: (v) => `${f.fixed(v, 2)} MWh`, xFmt, titleFmt, height: 200 });
        barChart(c3, { labels: x, series: [{ name: "Net ₹", color: PAYS, colors: netb.map(signColor), values: netb }],
          yFmt: f.compact, tipFmt: (v, s2, i) => `₹${f.int(v)}${nr && nr[i] != null ? ` · Normal Rate ₹${f.int(nr[i])}/MWh` : ""}`, xFmt, titleFmt, height: 200 });
      } else {
        lineChart(c2, { x, series: [{ name: "Deviation", color: "var(--s7)", values: dev, area: true }], yFmt: f.compact, tipFmt: (v) => `${f.fixed(v, 2)} MWh`, xFmt, titleFmt, height: 200 });
        lineChart(c3, { x, series: [{ name: "Net ₹", color: PAYS, values: netb, area: true }], yFmt: f.compact,
          tipFmt: (v) => `₹${f.int(v)}`, xFmt, titleFmt, height: 200 });
      }
      if (sras && sras.some((v) => v)) {
        const c4 = h("div");
        dc.append(h("h3", { class: "minihead" }, "SRAS (AGC) energy, MWh per block (+ up)"), c4);
        lineChart(c4, { x, series: [{ name: "SRAS", color: "var(--s3)", values: sras }], yFmt: f.compact, tipFmt: (v) => `${f.fixed(v, 3)} MWh`, xFmt, titleFmt, height: 160 });
      }
      dc.append(h("p", { class: "note" }, "As published in the RPC's block-wise file: ", docLink(W.documents.find((d) => /block|data_zip/.test(d.kind)) || W.documents[0]),
        ". Deviation sign follows the RPC (actual − schedule; ERPC states drawal as negative). Charges are the block's payable or receivable at the Normal Rate and any volume-limit multipliers the RPC applied."));
      const rows = () => x.map((i) => [dates[Math.floor(i / 96)], (i % 96) + 1, sch[i], act[i], dev[i], netb[i], sras?.[i] ?? null, nr?.[i] ?? null]);
      tableToggle(dc, () => table(["Day", "Block", "Schedule MWh", "Actual MWh", "Deviation MWh", "Net ₹", "SRAS MWh", "Normal Rate ₹/MWh"],
        rows().map((r) => [f.dShort(r[0]), blockLabel(r[1] - 1), f.fixed(r[2], 2), f.fixed(r[3], 2), f.fixed(r[4], 2), f.int(r[5]), r[6] == null ? "–" : f.fixed(r[6], 3), f.int(r[7])]), [2, 3, 4, 5, 6, 7]));
      csvButton(dc, `dhruva_dsm_blocks_${R.rpc}_${meta.slug}_${dates[0]}.csv`, () => [["date", "block", "schedule_mwh", "actual_mwh", "deviation_mwh", "net_rs", "sras_mwh", "normal_rate_rs_mwh"], ...rows()]);
    }
    if (st.entity) drill();
  }
  draw();
  root.append(h("div", { style: { marginTop: "14px" } }, sourcesCard(G, ["rpc", "NRPC", "SRPC"])));
}

async function gridAncillaryPage(root) {
  const G = await load("grid.json");
  root.append(gridHead("Ancillary services", "Secondary (SRAS) and tertiary (TRAS) reserve settlements by provider, from the RPC weekly accounts: energy deployed up and down, and what the pool paid or recovered."));
  const A = G.ancillary;
  if (!A.length) { root.append(h("p", { class: "empty" }, "No ancillary accounts parsed yet."), sourcesCard(G, ["rpc"])); return; }
  let which = A[0].rpc;
  const body = h("div");
  const sel = h("select", { onchange: (e) => { which = e.target.value; draw(); } }, A.map((x) => h("option", { value: x.rpc }, `${x.rpc} · ${periodLabel(x.period)}`)));
  root.append(h("div", { class: "controls" }, h("label", {}, "Regional account", sel)), body);
  const sum = (rows, k) => rows.reduce((a, r) => a + (r[k] || 0), 0);
  function sectionCard(title, sub, t, headers, row, numeric) {
    const c = card(title, sub);
    if (t.status && t.status !== "ok") c.append(h("div", { class: "dhruva-banner warn" }, statusChip(t.status), h("span", {}, t.message || "")));
    if (!t.rows.length) { c.append(h("p", { class: "empty" }, t.status === "missing" ? "Not published in this RPC's files." : "No rows.")); return c; }
    c.append(table(headers, t.rows.map(row), numeric));
    return c;
  }
  function draw() {
    body.replaceChildren();
    const R = A.find((x) => x.rpc === which);
    const g = h("div", { class: "grid" });
    body.append(g);
    const sr = R.sras.rows, tm = R.tras_market.rows, ts = R.tras_shortfall.rows;
    [tile("SRAS up / down", `${f.int(sum(sr, "up_mwh"))} / ${f.int(sum(sr, "down_mwh"))}`, "MWh", null, `${sr.length} providers`),
      tile("SRAS net to providers", lakhCr(sum(sr, "total_rs")), "", null, "energy + incentive; + paid by pool"),
      tile("TRAS DAM/RTM market", `${f.int(sum(tm, "da_up_sched_mwh") + sum(tm, "rt_up_sched_mwh"))} / ${f.int(sum(tm, "da_down_mwh") + sum(tm, "rt_down_mwh"))}`, "MWh", null, "up scheduled / down scheduled"),
      tile("TRAS shortfall & emergency", `${f.int(sum(ts, "up_mwh"))} / ${f.int(sum(ts, "down_mwh"))}`, "MWh", null, `net ${lakhCr(sum(ts, "net_rs"))} to providers`)].forEach((t) => { t.classList.add("c3"); g.append(t); });
    g.append(h("div", { class: "c12" }, sectionCard("SRAS (secondary reserve, AGC)", "by provider · + means paid by the pool to the provider",
      R.sras, ["Provider", "Up MWh", "Down MWh", "Net MWh", "Energy ₹", "Incentive ₹", "Total ₹"],
      (r) => [r.name, f.fixed(r.up_mwh, 1), f.fixed(r.down_mwh, 1), f.fixed(r.net_mwh, 1), f.int(r.energy_rs), f.int(r.incentive_rs), f.int(r.total_rs)], [1, 2, 3, 4, 5, 6])));
    g.append(h("div", { class: "c12" }, sectionCard("TRAS in the day-ahead and real-time AS markets", "by provider",
      R.tras_market, ["Provider", "DA up cleared", "DA up sched.", "RT up cleared", "RT up sched.", "Up charges ₹", "DA down MWh", "RT down MWh", "Net ₹"],
      (r) => [r.name, f.fixed(r.da_up_cleared_mwh, 1), f.fixed(r.da_up_sched_mwh, 1), f.fixed(r.rt_up_cleared_mwh, 1), f.fixed(r.rt_up_sched_mwh, 1), f.int(r.up_total_rs), f.fixed(r.da_down_mwh, 1), f.fixed(r.rt_down_mwh, 1), f.int(r.net_rs)], [1, 2, 3, 4, 5, 6, 7, 8])));
    g.append(h("div", { class: "c12" }, sectionCard("TRAS in shortfall and emergency conditions", "scheduled by the grid operator outside the markets",
      R.tras_shortfall, ["Provider", "Up MWh", "Up charges ₹", "Down MWh", "Down paid back ₹", "Net ₹"],
      (r) => [r.name, f.fixed(r.up_mwh, 1), f.int(r.up_rs), f.fixed(r.down_mwh, 1), f.int(r.down_rs), f.int(r.net_rs)], [1, 2, 3, 4, 5])));
    const P = R.tras_prices;
    const pc = card("TRAS clearing prices by block", P ? `${R.rpc} providers · ₹/MWh where a provider cleared` : "");
    if (!P) pc.append(h("p", { class: "empty" }, `${R.rpc} publishes TRAS only as weekly totals, so block prices are not available from its files. NERPC's block-wise TRAS file carries them.`));
    else if (!P.blocks_with_clearing) pc.append(h("p", { class: "empty" }, `${P.message}. Exchange TRAS results (IEX, PXIL, HPX) are not publicly available; see Source status.`));
    else {
      const k = P.dates.length - 1;
      mount(pc, (el) => lineChart(el, { x: [...Array(96).keys()], series: [
        { name: "DA TRAS-Up", color: "var(--s2)", values: P.rs_mwh.da_up[k] }, { name: "RT TRAS-Up", color: "var(--s7)", values: P.rs_mwh.rt_up[k] },
        { name: "DA TRAS-Down", color: "var(--s1)", values: P.rs_mwh.da_down[k] }, { name: "RT TRAS-Down", color: "var(--s3)", values: P.rs_mwh.rt_down[k] }],
      yFmt: f.compact, tipFmt: (x) => `₹${f.int(x)}/MWh`, xFmt: hours, titleFmt: blockLabel, height: 240 }));
    }
    g.append(h("div", { class: "c12" }, pc));
    g.append(h("p", { class: "note c12" }, "Documents: ", ...R.documents.flatMap((d, i) => [i ? " · " : "", docLink(d)])));
  }
  draw();
  root.append(h("div", { style: { marginTop: "14px" } }, await ancillaryBlocks()));
  root.append(h("div", { style: { marginTop: "14px" } }, sourcesCard(G, ["rpc", "GRID_INDIA_AS", "IEX_TRAS", "PXIL_TRAS", "HPX_TRAS", "NRPC", "SRPC"])));
}

async function ancillaryBlocks() {
  const GD = await load("grid_daily.json");
  const RS = GD.rpcs.map((r) => ({ ...r, weeks: r.weeks.filter((w) => w.ancillary_file).reverse() })).filter((r) => r.weeks.length);
  const c = card("By provider, block by block", "deployed energy per 15-minute block, and per 5-minute slot where the RPC publishes it");
  if (!RS.length) { c.append(h("p", { class: "empty" }, "No block-wise ancillary data parsed yet.")); return c; }
  const st = { rpc: RS.find((r) => r.rpc === "NERPC")?.rpc || RS[0].rpc, week: null, prov: null, day: null };
  const rsel = h("select", { onchange: (e) => { st.rpc = e.target.value; st.week = st.prov = st.day = null; draw(); } }, RS.map((r) => h("option", { value: r.rpc, selected: r.rpc === st.rpc }, r.rpc)));
  const wsel = h("select", { onchange: (e) => { st.week = e.target.value; st.prov = st.day = null; draw(); } });
  const psel = h("select", { onchange: (e) => { st.prov = e.target.value; draw(); } });
  const dsel = h("select", { onchange: (e) => { st.day = e.target.value; draw(); } });
  const body = h("div");
  c.append(h("div", { class: "controls" }, h("label", {}, "Region", rsel), h("label", {}, "Week", wsel), h("label", {}, "Provider", psel), h("label", {}, "Day", dsel)), body);
  async function draw() {
    const R = RS.find((r) => r.rpc === st.rpc);
    if (!st.week) st.week = R.weeks[0].key;
    wsel.replaceChildren(...R.weeks.map((w) => h("option", { value: w.key, selected: w.key === st.week }, periodLabel(w.period))));
    const W = R.weeks.find((w) => w.key === st.week);
    const A = await load(W.ancillary_file);
    if (!A.providers.length) { body.replaceChildren(h("p", { class: "empty" }, "No provider data this week.")); return; }
    if (!st.prov || !A.providers.some((p) => p.name === st.prov)) st.prov = (A.providers.find((p) => p.sras_5min || p.sras) || A.providers[0]).name;
    psel.replaceChildren(...A.providers.map((p) => h("option", { value: p.name, selected: p.name === st.prov }, p.name)));
    if (!st.day || !A.dates.includes(st.day)) st.day = A.dates[A.dates.length - 1];
    dsel.replaceChildren(...dayOpts(A.dates, "Whole week").slice(1));
    dsel.value = st.day;
    const P = A.providers.find((p) => p.name === st.prov);
    const k = A.dates.indexOf(st.day);
    body.replaceChildren();
    const bad = Object.entries(A.checks).filter(([, v]) => v.status !== "ok");
    const okc = Object.values(A.checks).flatMap((v) => v.checks || []).filter((x) => x.ok);
    if (Object.keys(A.checks).length) body.append(h("div", { class: `dhruva-banner ${bad.length ? "warn" : ""}` }, statusChip(bad.length ? "partial" : "ok"),
      h("span", {}, okc.length ? `Block sums checked against the weekly AS account: ${okc.map((x) => x.check.replace(" vs weekly account", "")).join(", ")} agree. ` : "",
        bad.map(([ds, v]) => `${ds}: ${v.message || v.status}`).join(" "))));
    const sec = (title, el) => { body.append(h("h3", { class: "minihead" }, title), el); return el; };
    const line = (el, series, unit, nd = 2, per = 96, lab = blockLabel, empty = "Nothing deployed on this day.") => {
      const live = series.filter((x) => x.values && x.values.some((v) => v));
      if (!live.length) { el.replaceChildren(h("p", { class: "empty" }, empty)); return; }
      lineChart(el, { x: [...Array(per).keys()], series: live, yFmt: f.compact, tipFmt: (v) => `${f.fixed(v, nd)} ${unit}`,
        xFmt: per === 96 ? hours : (i) => (i % 36 === 0 ? `${String(i / 12).padStart(2, "0")}:00` : null), titleFmt: (i) => lab(i), height: 200 });
    };
    let any = false;
    if (P.sras_5min) {
      any = true;
      const inc = P.sras_5min.incentive_rs[k] || [];
      sec(`SRAS, every 5 minutes · ${f.dLong(st.day)} · MWh`, h("div"));
      line(body.lastChild, [{ name: "Up", color: "var(--s2)", values: P.sras_5min.up_mwh[k] }, { name: "Down", color: "var(--s1)", values: P.sras_5min.down_mwh[k] }], "MWh", 3, 288, slotLabel);
      body.append(h("p", { class: "note" }, `Mileage incentive for the day: ₹${f.int(inc.reduce((a, v) => a + (v || 0), 0))}. SRAS is dispatched by AGC and settled on 5-minute mileage.`));
    }
    if (P.sras) {
      any = true;
      sec(`SRAS, per 15-minute block · ${f.dLong(st.day)} · MWh`, h("div"));
      if (P.sras.net_mwh) line(body.lastChild, [{ name: "Net SRAS (+ up)", color: "var(--s3)", values: P.sras.net_mwh[k] }], "MWh", 3);
      else line(body.lastChild, [{ name: "Up", color: "var(--s2)", values: P.sras.up_mwh[k] }, { name: "Down", color: "var(--s1)", values: P.sras.down_mwh[k] }], "MWh", 3);
      body.append(h("p", { class: "note" }, P.sras.source + "."));
    }
    if (P.tras) {
      any = true;
      const T = P.tras;
      sec(`TRAS scheduled, per block · ${f.dLong(st.day)} · MWh`, h("div"));
      line(body.lastChild, [
        { name: "DA up", color: "var(--s1)", values: T.da_up_sched_mwh[k] }, { name: "RT up", color: "var(--s2)", values: T.rt_up_sched_mwh[k] },
        { name: "Shortfall up", color: "var(--s3)", values: T.sf_up_mwh[k] }, { name: "Emergency up", color: "var(--s4)", values: T.em_up_mwh[k] },
        { name: "DA down", color: "var(--s5)", values: T.da_down_mwh[k] }, { name: "RT down", color: "var(--s6)", values: T.rt_down_mwh[k] },
        { name: "Shortfall down", color: "var(--s7)", values: T.sf_down_mwh[k] }], "MWh", 2, 96, blockLabel, "No TRAS scheduled for this provider on this day.");
    }
    if (P.scuc) {
      any = true;
      sec(`SCUC (security-constrained unit commitment) · ${f.dLong(st.day)} · MWh`, h("div"));
      line(body.lastChild, [{ name: "Increment", color: "var(--s2)", values: P.scuc.increment_mwh[k] }, { name: "Decrement", color: "var(--s1)", values: P.scuc.decrement_mwh[k] }], "MWh", 2, 96, blockLabel, "No SCUC schedule changes for this generator on this day.");
    }
    if (!any) body.append(h("p", { class: "empty" }, "No block data for this provider."));
    body.append(h("p", { class: "note" }, "Documents: ", ...W.documents.flatMap((d, i) => [i ? " · " : "", docLink(d)]),
      R.rpc === "NERPC" ? "" : `. ${R.rpc} publishes SRAS and TRAS only as weekly PDF totals; the per-block SRAS here comes from the SRAS column of its DSM block files, and TRAS is not available per block.`));
  }
  draw();
  return c;
}

async function gridSourcesPage(root) {
  const G = await load("grid.json");
  root.append(gridHead("Source status", "Every public source behind the Grid & balancing pages, whether it could be read on the last run, and how far its data runs. Anything that failed to parse is shown here, never filled in."));
  root.append(sourcesCard(G, G.sources.sources.map((x) => x.id), "All sources"));
  const hc = card("Parsed weeks", "one row per RPC settlement week · totals as published");
  hc.append(table(["RPC", "Week", "DSM", "DSM payable", "DSM receivable", "SRAS total ₹", "TRAS shortfall net ₹", "TRAS market net ₹"],
    G.history.slice().reverse().map((x) => [x.rpc, periodLabel(x.period), statusChip(x.dsm_status), lakhCr(x.payable_rs), lakhCr(x.receivable_rs), lakhCr(x.sras_total_rs), lakhCr(x.tras_shortfall_net_rs), lakhCr(x.tras_market_net_rs)]), [3, 4, 5, 6, 7]));
  root.append(h("div", { style: { marginTop: "14px" } }, hc));
  const GD = await load("grid_daily.json");
  const rc = card("Block-level data and how it reconciles", "every RPC week · block files summed and checked against the weekly account");
  const n = (x) => (x == null ? "–" : f.int(x));
  rc.append(table(["RPC", "Week", "Status", "Entities in account", "Tie to the rupee", "Other series", "Entity-days vs file totals", "Ancillary block files", "Notes"],
    GD.rpcs.flatMap((r) => r.weeks.map((w) => ({ r, w }))).sort((a, b) => (b.w.period.from > a.w.period.from ? 1 : -1)).map(({ r, w }) => {
      const x = w.reconciliation;
      return [r.rpc, periodLabel(w.period), statusChip(w.status), x ? n(x.ties + x.differs) : "–", x ? n(x.ties) : "–", x ? n(x.unmatched) : "–",
        w.day_checks ? `${n(w.day_checks.checked - w.day_checks.failed)} / ${n(w.day_checks.checked)}` : "no daily totals in file",
        w.ancillary.length ? w.ancillary.join(", ") : "–", w.message || (w.file ? `stored as ${w.file}` : "")];
    }), [3, 4, 5]));
  rc.append(h("p", { class: "note" }, "Block data is published as each RPC's own files (ERPC: block-wise Excel; WRPC: per-constituent CSVs; NERPC: DeviationDetails, SRAS, TRAS and SCUC workbooks) and stored unchanged in data/grid/blocks/ as gzip CSV. \"Other series\" are in the block files but have no row of their own in the weekly account (QCA member plants, infirm units, nuclear stations apportioned to states) and are kept out of pool totals."));
  root.append(h("div", { style: { marginTop: "14px" } }, rc));
}

async function dhruvaHome(root) {
  const [bess, fut] = await Promise.all([load("bess.json"), load("futures.json")]);
  root.append(dhruvaHead("Dhruva indices and analytics",
    "Everything on these pages is Dhruva's own work: benchmarks and models built on top of the market data, with open code and a versioned methodology. The Markets pages show the source data alone."));
  const grid = h("div", { class: "grid" });
  root.append(grid);
  const add = (t) => { t.classList.add("c3"); grid.append(t); };
  for (const name of ["DBX-2H", "DBX-4H"]) {
    const ix = bess.indices[name], m = ix.monthly.at(-1);
    add(tile(`${name} · ${f.monthLong(m.month)} run-rate`, f.fixed(m.run_rate), "₹ lakh/MW/mo", null,
      `trailing 12 months ₹${f.fixed(ix.trailing_365_lakh_per_mw_month)} lakh/MW/mo`));
  }
  const cur = fut.dbi.at(-1), prev = fut.dbi.at(-2);
  add(tile(`DBI-M · ${f.monthLong(cur.month)} to date`, f.mwh(cur.vwap), "/MWh", null, `${cur.days}/${cur.days_in_month} days · ${cur.basis}`));
  add(tile(`DBI-M · ${f.monthLong(prev.month)}`, f.mwh(prev.vwap), "/MWh", null, `${prev.days} delivery days · ${prev.basis}`));
  const products = card("What Dhruva publishes", "");
  products.append(table(["Product", "What it is", "Page"], [
    [h("b", {}, "DBX battery index"), "Daily perfect-foresight arbitrage revenue for a 2h and 4h battery, in the unit tenders use (₹ lakh/MW/month)", h("a", { href: "#bess" }, "Battery index")],
    [h("b", {}, "DBI-M base index"), "Month-to-date volume-weighted DAM unconstrained price: the number NSE and MCX futures settle on, computed daily", h("a", { href: "#base-index" }, "Base index")],
    [h("b", {}, "DSM Normal Rate"), "Block-wise rate per the CERC DSM Regulations 2024: highest of DAM, RTM and (DAM + RTM + ancillary charge)/3, checked against the rate the RPCs publish", h("a", { href: "#analytics" }, "Analytics")],
    [h("b", {}, "D+1 baseline forecast"), "Per-block median of the last 7 days, published with its backtest error", h("a", { href: "#analytics" }, "Analytics")],
    [h("b", {}, "The Dhruva Weekly"), "Monday note drafted from the data, with an analyst view", h("a", { href: "#weekly" }, "Weekly")],
  ]));
  grid.append(h("div", { class: "c12" }, products));
}

async function baseIndexPage(root) {
  const fut = await load("futures.json");
  root.append(dhruvaHead("Base index (DBI-M)",
    "NSE and MCX monthly electricity futures settle on the month's volume-weighted IEX DAM unconstrained MCP. DBI-M computes that number to date, every day, so the expiring contract can be read against it."));
  const grid = h("div", { class: "grid" });
  root.append(grid);
  const cur = fut.dbi[fut.dbi.length - 1];
  const front = fut.contracts.find((c) => c.delivery_month === cur?.month);
  const frontPx = front ? (front.last || front.prev_close) : null;
  const add = (t) => { t.classList.add("c3"); grid.append(t); };
  add(tile(`DBI-M ${f.monthLong(cur.month)} · ${cur.days}/${cur.days_in_month} days`, f.mwh(cur.vwap), "/MWh", null, `basis: ${cur.basis === "UMCP" ? "IEX unconstrained MCP × MCV" : cur.basis === "MCP" ? "IEX MCP × MCV (no UMCP files)" : `${cur.basis}; MCP × MCV on days IEX's UMCP file is missing`}`));
  add(tile(`NSE ${f.monthLabel(cur.month)} future`, frontPx ? f.mwh(frontPx) : "–", "/MWh",
    front ? f.delta(front.change_pct, "today") : null, fut.latest_snapshot ? `exchange price · snapshot ${f.dShort(fut.latest_snapshot)}` : "no snapshot yet"));
  add(tile("Futures − index", frontPx ? f.mwh(frontPx - cur.vwap) : "–", "/MWh", null,
    "Futures above the index means the market expects the rest of the month to clear higher."));
  const prev = fut.dbi[fut.dbi.length - 2];
  add(tile(`DBI-M · ${prev ? f.monthLong(prev.month) : ""}`, prev ? f.mwh(prev.vwap) : "–", "/MWh", null, prev ? `${prev.days} delivery days · ${prev.basis}` : ""));

  const pc = card(`Month-to-date path · ${f.monthLong(cur.month)}`, "₹/MWh");
  const xs = cur.mtd.map((p) => p[0]);
  const series = [{ name: "DBI-M (month to date)", short: "DBI-M", color: "var(--s1)", values: cur.mtd.map((p) => p[1]) }];
  const fs = fut.series.find((s) => s.exchange === "NSE" && s.month === cur.month);
  if (fs) {
    const m = new Map(fs.points);
    series.push({ name: `NSE ${f.monthLabel(cur.month)} future (exchange)`, short: "NSE", color: "var(--s2)", values: xs.map((x) => m.get(x) ?? null) });
  }
  mount(pc, (el) => lineChart(el, { x: xs, series, yFmt: (v) => f.compact(v), tipFmt: (v) => `${f.mwh(v)}/MWh`, zero: false,
    xFmt: (i) => f.dShort(xs[i]), titleFmt: (i) => f.dLong(xs[i]), height: 260 }));
  pc.append(h("p", { class: "note" }, "The futures line starts from the first daily snapshot, because NSE publishes no history for these contracts."));
  grid.append(h("div", { class: "c7" }, pc));

  const hc = card("DBI-M by month", "₹/MWh");
  const months = fut.dbi.slice(isPro() ? 0 : -6);
  mount(hc, (el) => barChart(el, { labels: months.map((m) => m.month), series: [{ name: "DBI-M", color: "var(--s1)", values: months.map((m) => m.vwap) }],
    yFmt: f.compact, tipFmt: (v, s, i) => `${f.mwh(v)}/MWh · ${months[i].days} days · ${months[i].basis}`, xFmt: (i) => f.monthLabel(months[i].month),
    titleFmt: (i) => f.monthLong(months[i].month), height: 260, capLabels: months.length <= 12, capFmt: (v) => f.int(v) }));
  tableToggle(hc, () => table(["Month", "DBI-M ₹/MWh", "Days", "Basis"], fut.dbi.slice().reverse().map((m) => [f.monthLong(m.month), f.int(m.vwap), `${m.days}/${m.days_in_month}`, m.basis]), [1]));
  csvButton(hc, "dhruva_dbi_monthly.csv", () => [["month", "dbi_m_rs_mwh", "days", "basis"], ...fut.dbi.map((m) => [m.month, m.vwap, m.days, m.basis])]);
  if (!isPro()) hc.append(h("p", { class: "note" }, "Free view: last 6 months. Pro: from April 2024."));
  grid.append(h("div", { class: "c5" }, hc));
}

async function analyticsPage(root) {
  const [dsm, fc] = await Promise.all([load("dsm.json"), load("forecast.json")]);
  root.append(dhruvaHead("Analytics",
    "Calculations Dhruva runs on public data: the DSM Normal Rate under the CERC DSM Regulations 2024, using the ancillary charge where it can be recovered, and a D+1 baseline price forecast."));
  const grid = h("div", { class: "grid" });
  root.append(grid);
  const lo = dsm.latest_official;
  if (lo) {
    const c = card(`DSM Normal Rate · ${f.dLong(lo.date)}`, "₹/kWh by block · Dhruva's calculation against the rate the RPCs published");
    mount(c, (el) => lineChart(el, { x: [...Array(96).keys()], series: [
      { name: "Published Normal Rate (RPC)", short: "Published", color: "var(--s7)", values: lo.official, width: 3 },
      { name: "Dhruva: max(I-DAM, RTM, (I-DAM+RTM+ASC)/3)", short: "Dhruva", color: "var(--s1)", values: lo.nr, width: 1.5 },
      { name: "I-DAM ACP (IEX)", short: "I-DAM", color: "var(--s3)", values: lo.idam, width: 1.5 },
      { name: "RTM ACP (IEX)", short: "RTM", color: "var(--s2)", values: lo.rtm, width: 1.5 },
    ], yFmt: f.kwhAxis, tipFmt: (x) => f.kwh(x), xFmt: hours, titleFmt: blockLabel, height: 300 }));
    tableToggle(c, () => table(["Block", "Published", "Dhruva", "I-DAM", "RTM", "ASC"], lo.official.map((x, b) =>
      [blockLabel(b), f.kwh(x), f.kwh(lo.nr[b]), f.kwh(lo.idam[b]), f.kwh(lo.rtm[b]), lo.asc[b] == null ? "not binding" : f.kwh(lo.asc[b])]), [1, 2, 3, 4, 5]));
    c.append(h("p", { class: "note" }, "Published rate: ", ...lo.sources.flatMap((x, i) => [i ? ", " : "", h("a", { href: x.url, target: "_blank", rel: "noopener" }, `${x.rpc} block-wise DSM data`)]),
      ". Where the published rate sits above both market prices, the ancillary term set it and ASC = 3 × NR − I-DAM − RTM."));
    grid.append(h("div", { class: "c8" }, c));
  }
  const v = dsm.validation || {};
  const s = card("How the rate is built", "CERC DSM Regulations 2024, as notified");
  s.append(table(["Term", "Source", "Status"], [
    ["(i) I-DAM ACP: DAM, G-DAM, HP-DAM", "IEX, volume-weighted per block", h("span", { class: "status-dot" }, "live")],
    ["(ii) RTM ACP", "IEX, every block", h("span", { class: "status-dot" }, "live")],
    ["(iii) (I-DAM + RTM + ASC) / 3", "ASC recovered from RPC-published Normal Rate", h("span", { class: "status-dot" }, "weekly, ~2 weeks lag")],
  ]),
  h("p", { class: "note" }, "The rate is the highest of the three terms. There is no 50:50 fallback in the notified text; that was in the 2024 draft. The draft also proposed equal thirds alone."),
  h("p", { class: "note" }, v.non_binding_blocks
    ? `Check: in ${f.int(v.non_binding_blocks)} published blocks where the ancillary term did not bind, max(I-DAM, RTM) from IEX matched the published rate within ₹1/MWh in ${f.fixed(v.match_share * 100, 1)}% of blocks. Misses come from area-wise prices and PXIL/HPX volumes, which Dhruva does not have. The ASC set the rate in ${f.int(v.asc_binding_blocks)} blocks (median ASC ${f.kwh(v.asc_median_rs_mwh)}/kWh).`
    : "No RPC block-wise data ingested yet, so the ASC is unknown and only a lower bound is shown."));
  grid.append(h("div", { class: "c4" }, s));

  const d = dsm.daily, n = Math.min(rangeDays(), d.dates.length);
  const sl = sliceLast(d, ["dates", "avg", "max", "min", "official_avg", "asc_status"], n);
  const pend = sl.asc_status.filter((x) => x === "pending").length;
  const c2 = card("Daily Normal Rate", `average and range · last ${sl.dates.length} days${pend ? ` · ${pend} recent days are a lower bound (ASC not yet published)` : ""}`);
  mount(c2, (el) => lineChart(el, { x: sl.dates, series: [
    { name: "Max block", short: "Max", color: "var(--s2)", values: sl.max },
    { name: "Daily average (Dhruva)", short: "Avg", color: "var(--s7)", values: sl.avg },
    { name: "Daily average (published)", short: "Published", color: "var(--s1)", values: sl.official_avg, width: 1.5 },
    { name: "Min block", short: "Min", color: "var(--s3)", values: sl.min },
  ], yFmt: f.kwhAxis, tipFmt: (x) => f.kwh(x), xFmt: (i) => f.dShort(sl.dates[i]),
    titleFmt: (i) => `${f.dLong(sl.dates[i])}${sl.asc_status[i] === "pending" ? " · lower bound" : ""}`, height: 260 }));
  csvButton(c2, "dhruva_dsm_normal_rate_daily.csv", () => [["date", "avg", "max", "min", "published_avg", "asc_status"], ...sl.dates.map((x, i) => [x, sl.avg[i], sl.max[i], sl.min[i], sl.official_avg[i], sl.asc_status[i]])]);
  grid.append(h("div", { class: "c12" }, h("div", { class: "controls" }, rangeControl(() => route())), c2));

  const fcard = card(`D+1 baseline forecast · ${fc.target_date ? f.dLong(fc.target_date) : ""}`, fc.method || "");
  if (!isPro()) fcard.append(lockCard("Pro: forecasts", "A per-block D+1 DAM baseline with its published backtest; ML forecasts next."));
  else {
    mount(fcard, (el) => lineChart(el, { x: [...Array(96).keys()], series: [
      { name: "Baseline forecast", short: "Forecast", color: "var(--s7)", values: fc.forecast },
      { name: `Actual ${f.dShort(fc.last_actual.date)}`, short: "Last", color: "var(--muted)", values: fc.last_actual.mcp, width: 1.5 },
    ], yFmt: f.kwhAxis, tipFmt: (x) => f.kwh(x), xFmt: hours, titleFmt: blockLabel, height: 240 }));
    fcard.append(h("p", { class: "note" }, `Backtest over the last ${fc.backtest.days} days: mean absolute error ${f.kwh(fc.backtest.mae)}/kWh per block. A naive benchmark to beat, not a trading signal.`));
  }
  grid.append(h("div", { class: "c12" }, fcard));
}

async function weeklyPage(root) {
  const notes = await load("notes.json");
  root.append(dhruvaHead("The Dhruva Weekly", "A free Monday note on what moved Indian power prices. The numbers are generated from the data; the analyst view is written by hand."));
  if (!notes.notes.length) { root.append(h("p", { class: "empty" }, "No notes yet.")); return; }
  const sel = h("select", { onchange: () => show() }, notes.notes.map((n) => h("option", { value: n.week_ending }, `Week ending ${f.dLong(n.week_ending)}`)));
  const body = h("div", { class: "card" });
  root.append(h("div", { class: "controls" }, sel), body);
  const show = () => body.replaceChildren(markdown(notes.notes.find((n) => n.week_ending === sel.value).markdown));
  show();
}

async function methodologyPage(root) {
  const md = await load("methodology.md");
  root.append(dhruvaHead("Methodology", "How every Dhruva index and model is defined, what it excludes, and how it is governed."),
    h("div", { class: "card" }, markdown(md.split("\n").slice(1).join("\n"))));
}

function pricingPage(root) {
  root.append(pageHead("Plans", "The free view is the full market today. Pro adds history, downloads and forecasts. Enterprise licenses the index for contracts and lending."));
  const plan = (name, price, sub, items, cta, featured) => h("div", { class: `card plan${featured ? " featured" : ""}` },
    h("h2", {}, name), h("div", { class: "muted small" }, sub), h("div", { class: "price" }, price), h("ul", {}, items.map((i) => h("li", {}, i))), cta);
  root.append(h("div", { class: "pricing" },
    plan("Free", "₹0", "for everyone", ["Every market, today and last 30 days", "Tenders, RECs, open-access calculator", "Dhruva DBX and DBI-M headline values", "The Dhruva Weekly by email"],
      h("button", { class: "btn ghost", onclick: () => setTier("free", true) }, "Use free"), false),
    plan("Pro", "₹6,000", "per seat / month · billed annually", ["Full history from April 2024", "CSV downloads for every chart", "D+1 baseline forecast (ML forecasts next)", "Price and basis alerts (coming)", "Regional market-split history"],
      h("button", { class: "btn", onclick: () => setTier("pro", true) }, "Preview Pro"), true),
    plan("Enterprise", "Talk to us", "lenders, funds, developers", ["Licence to reference DBX and DBI-M in PPAs, loans and hedges", "Regional and custom-spec battery indices", "API and daily delivery", "Methodology consultation seat"],
      h("a", { class: "btn ghost", href: "#methodology" }, "Read the methodology"), false)));
  root.append(h("p", { class: "note" }, "This build has no payments. \"Preview Pro\" unlocks the Pro views in your browser so you can evaluate them."));
}

// ------------------------------------------------------------------ router
const ROUTES = [
  ["overview", "Overview", overview, "Markets"], ["spot", "Spot", spotPage, "Markets"], ["regions", "Regions", regionsPage, "Markets"],
  ["futures", "Futures", futuresPage, "Markets"], ["rec", "RECs", recPage, "Markets"], ["tenders", "Tenders", tendersPage, "Markets"],
  ["open-access", "Open access", openAccessPage, "Markets"],
  ["frequency", "Frequency", gridFrequencyPage, "Grid & balancing"], ["deviations", "Deviations (DSM)", gridDsmPage, "Grid & balancing"],
  ["ancillary", "Ancillary", gridAncillaryPage, "Grid & balancing"], ["grid-sources", "Source status", gridSourcesPage, "Grid & balancing"],
  ["dhruva", "Indices", dhruvaHome, "Dhruva"], ["bess", "Battery index", bessPage, "Dhruva"], ["base-index", "Base index", baseIndexPage, "Dhruva"],
  ["analytics", "Analytics", analyticsPage, "Dhruva"], ["weekly", "Weekly", weeklyPage, "Dhruva"],
  ["methodology", "Methodology", methodologyPage, "Dhruva"], ["pricing", "Plans", pricingPage, "Dhruva"],
];

function setTier(t, rerender) {
  state.tier = t;
  store.set("dhruva.tier", t);
  document.querySelectorAll("[data-tier]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.tier === t)));
  if (rerender) route();
}

let routing = 0;
async function route() {
  const id = (location.hash.replace(/^#\/?/, "").split(/[?/]/)[0]) || "overview";
  const alias = { balancing: "deviations", grid: "frequency" };
  const r = ROUTES.find((x) => x[0] === (alias[id] || id)) || ROUTES[0];
  document.querySelectorAll("nav.tabs a").forEach((a) => a.toggleAttribute("aria-current", a.dataset.id === r[0]));
  const active = document.querySelector("nav.tabs a[aria-current]");
  active?.setAttribute("aria-current", "page");
  active?.scrollIntoView({ block: "nearest", inline: "nearest" });
  const main = document.querySelector("main");
  const token = ++routing;
  const fresh = h("div");
  main.style.opacity = "0.6";
  try {
    await r[2](fresh);
    if (token !== routing) return;
    main.replaceChildren(fresh);
  } catch (e) {
    console.error(e);
    main.replaceChildren(h("p", { class: "empty" }, `Could not load this view: ${e.message}`));
  }
  main.style.opacity = "";
  document.title = `${r[1]} · Dhruva`;
}

async function init() {
  const nav = document.querySelector("nav.tabs");
  let group = null;
  nav.replaceChildren(...ROUTES.flatMap(([id, label, , g]) => {
    const out = [];
    if (g !== group) { group = g; out.push(h("span", { class: `navgroup${g === "Markets" ? "" : " sep"}${g === "Dhruva" ? " dhruva" : ""}`, "aria-hidden": "true" }, g)); }
    out.push(h("a", { href: `#${id}`, "data-id": id, class: g === "Dhruva" ? "dhruva" : null }, label));
    return out;
  }));
  document.querySelectorAll("[data-tier]").forEach((b) => b.addEventListener("click", () => setTier(b.dataset.tier, true)));
  setTier(state.tier, false);
  const themeBtn = document.getElementById("theme");
  const applyTheme = (t) => { if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme; };
  applyTheme(store.get("dhruva.theme", null));
  themeBtn.addEventListener("click", () => {
    const dark = document.documentElement.dataset.theme ? document.documentElement.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    const t = dark ? "light" : "dark";
    store.set("dhruva.theme", t);
    applyTheme(t);
    route();
  });
  try {
    const meta = await load("meta.json");
    document.getElementById("asof").textContent = `Data to ${f.dLong(meta.latest.dam)} · updated ${meta.generated_at.replace("T", " ").slice(0, 16)} IST`;
  } catch { /* shown per page */ }
  window.addEventListener("hashchange", route);
  route();
}
init();
