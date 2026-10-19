import { barChart, blockLabel, heatmap, lineChart, table } from "./charts.js";
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
    ["DSM and SRAS/TRAS settlement rates", "RPC weekly accounts", "planned"],
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
    [h("b", {}, "Indicative DSM Normal Rate"), "Block-wise rate per the CERC DSM Regulations 2024, from DAM and RTM prices (ancillary component pending)", h("a", { href: "#analytics" }, "Analytics")],
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
    "Calculations Dhruva runs on exchange prices: an indicative DSM Normal Rate under the CERC DSM Regulations 2024, and a D+1 baseline price forecast."));
  const grid = h("div", { class: "grid" });
  root.append(grid);
  const lt = dsm.latest;
  if (lt) {
    const c = card(`Indicative DSM Normal Rate · ${f.dLong(lt.date)}`, "₹/kWh by block");
    mount(c, (el) => lineChart(el, { x: [...Array(96).keys()], series: [
      { name: "Normal Rate (indicative)", short: "NR", color: "var(--s7)", values: lt.nr },
      { name: "DAM", color: COLORS.dam, values: lt.dam, width: 1.5 },
      { name: "RTM", color: COLORS.rtm, values: lt.rtm, width: 1.5 },
    ], yFmt: f.kwhAxis, tipFmt: (x) => f.kwh(x), xFmt: hours, titleFmt: blockLabel, height: 280 }));
    tableToggle(c, () => table(["Block", "NR", "DAM", "RTM"], lt.nr.map((x, b) => [blockLabel(b), f.kwh(x), f.kwh(lt.dam[b]), f.kwh(lt.rtm[b])]), [1, 2, 3]));
    grid.append(h("div", { class: "c8" }, c));
  }
  const s = card("How the rate is built", "");
  s.append(table(["Component", "Source", "Status"], [
    ["DAM ACP", "IEX, every block", h("span", { class: "status-dot" }, "live")],
    ["RTM ACP", "IEX, every block", h("span", { class: "status-dot" }, "live")],
    ["Ancillary Service Charge (SRAS/TRAS)", "RPC weekly DSM/SRAS/TRAS accounts", h("span", { class: "status-dot warn" }, "planned")],
  ]), h("p", { class: "note" }, "The regulation blends DAM, RTM and the Ancillary Service Charge in equal thirds, and falls back to 50:50 DAM/RTM when no ancillary service is dispatched. Until the ancillary charge is ingested, the fallback is applied to every block, using IEX prices only. Official settlement rates are published weekly by the RPCs."));
  grid.append(h("div", { class: "c4" }, s));

  const d = dsm.daily, n = Math.min(rangeDays(), d.dates.length);
  const sl = sliceLast(d, ["dates", "avg", "max", "min"], n);
  const c2 = card("Daily indicative Normal Rate", `average and range · last ${sl.dates.length} days`);
  mount(c2, (el) => lineChart(el, { x: sl.dates, series: [
    { name: "Max block", short: "Max", color: "var(--s2)", values: sl.max },
    { name: "Daily average", short: "Avg", color: "var(--s7)", values: sl.avg },
    { name: "Min block", short: "Min", color: "var(--s3)", values: sl.min },
  ], yFmt: f.kwhAxis, tipFmt: (x) => f.kwh(x), xFmt: (i) => f.dShort(sl.dates[i]),
    titleFmt: (i) => f.dLong(sl.dates[i]), height: 240 }));
  csvButton(c2, "dhruva_dsm_normal_rate_daily.csv", () => [["date", "avg", "max", "min"], ...sl.dates.map((x, i) => [x, sl.avg[i], sl.max[i], sl.min[i]])]);
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
  const alias = { balancing: "analytics" };
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
    if (g !== group) { group = g; out.push(h("span", { class: `navgroup${g === "Dhruva" ? " dhruva" : ""}`, "aria-hidden": "true" }, g)); }
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
