// Number and date formatting (Indian conventions).

export const kwh = (rsPerMwh, nd = 2) =>
  rsPerMwh == null || !isFinite(rsPerMwh) ? "–" : `₹${(rsPerMwh / 1000).toFixed(nd)}`;
export const kwhAxis = (rsPerMwh) => `₹${(rsPerMwh / 1000).toFixed(rsPerMwh % 1000 === 0 ? 0 : 1)}`;
export const mwh = (v) => (v == null || !isFinite(v) ? "–" : `${v < 0 ? "−" : ""}₹${Math.abs(Math.round(v)).toLocaleString("en-IN")}`);
export const int = (v) => (v == null || !isFinite(v) ? "–" : Math.round(v).toLocaleString("en-IN"));
export const fixed = (v, nd = 2) => (v == null || !isFinite(v) ? "–" : Number(v).toFixed(nd));
export const lakh = (v, nd = 2) => (v == null || !isFinite(v) ? "–" : `₹${Number(v).toFixed(nd)} L`);

export function compact(v) {
  if (v == null || !isFinite(v)) return "–";
  const a = Math.abs(v);
  if (a >= 1e7) return `${(v / 1e7).toFixed(1)} Cr`;
  if (a >= 1e5) return `${(v / 1e5).toFixed(1)} L`;
  if (a >= 1e3) return `${(v / 1e3).toFixed(a >= 1e4 ? 0 : 1)}K`;
  return String(Math.round(v));
}

const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
export const d = (iso) => (iso ? new Date(`${iso}T00:00:00`) : null);
export const dShort = (iso) => { const x = d(iso); return x ? `${x.getDate()} ${MON[x.getMonth()]}` : "–"; };
export const dLong = (iso) => { const x = d(iso); return x ? `${DOW[x.getDay()]} ${x.getDate()} ${MON[x.getMonth()]} ${x.getFullYear()}` : "–"; };
export const monthLabel = (ym) => `${MON[+ym.slice(5, 7) - 1]} ${ym.slice(2, 4)}`;
export const monthLong = (ym) => `${MON[+ym.slice(5, 7) - 1]} ${ym.slice(0, 4)}`;

export function pct(a, b) {
  if (a == null || b == null || !isFinite(a) || !isFinite(b) || b === 0) return null;
  return (a / b - 1) * 100;
}

/** Delta element: signed, coloured by direction x whether up is good. */
export function delta(change, label, upIsGood = null, unit = "%") {
  const span = document.createElement("span");
  span.className = "delta";
  if (change == null || !isFinite(change)) { span.textContent = label ? `– ${label}` : "–"; return span; }
  const b = document.createElement("span");
  const sign = change > 0 ? "▲" : change < 0 ? "▼" : "■";
  b.textContent = `${sign} ${Math.abs(change).toFixed(1)}${unit}`;
  if (upIsGood !== null && change !== 0) b.className = (change > 0) === upIsGood ? "up" : "down";
  span.append(b, document.createTextNode(` ${label}`));
  return span;
}
