// Tiny DOM helpers. Strings always go in as text nodes, never as HTML.

export function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") e.className = v;
    else if (k === "style" && typeof v === "object") Object.assign(e.style, v);
    else if (k.startsWith("on") && typeof v === "function") e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat()) {
    if (c == null || c === false) continue;
    e.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return e;
}

export function card(title, sub, ...body) {
  const actions = h("div", { class: "actions" });
  const c = h("section", { class: "card" },
    h("div", { class: "card-head" }, h("h2", {}, title), h("span", { class: "sub" }, sub || ""), actions),
    ...body);
  c.actions = actions;
  return c;
}

export function tile(label, value, unit, deltaEl, extra) {
  return h("div", { class: "card tile" },
    h("div", { class: "label" }, label),
    h("div", { class: "value" }, value, unit ? h("small", {}, unit) : null),
    deltaEl || null, extra ? h("div", { class: "note" }, extra) : null);
}

export function download(filename, rows) {
  const esc = (v) => {
    const s = v == null ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const blob = new Blob([rows.map((r) => r.map(esc).join(",")).join("\n")], { type: "text/csv" });
  const a = h("a", { href: URL.createObjectURL(blob), download: filename });
  document.body.append(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 0);
}

/** Minimal Markdown for our own notes and methodology: headings, lists, tables, emphasis, links, code. */
export function markdown(md) {
  const root = h("div", { class: "prose" });
  const lines = md.replace(/\r/g, "").split("\n");
  let i = 0;
  const inline = (text) => {
    const frag = document.createDocumentFragment();
    const re = /(\*\*[^*]+\*\*|_[^_]+_|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
    let last = 0, m;
    while ((m = re.exec(text))) {
      if (m.index > last) frag.append(text.slice(last, m.index));
      const t = m[0];
      if (t.startsWith("**")) frag.append(h("strong", {}, t.slice(2, -2)));
      else if (t.startsWith("`")) frag.append(h("code", {}, t.slice(1, -1)));
      else if (t.startsWith("[")) {
        const mm = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(t);
        const href = /^(https?:|#|mailto:)/.test(mm[2]) ? mm[2] : "#";
        frag.append(h("a", { href, target: href.startsWith("http") ? "_blank" : null, rel: "noopener" }, mm[1]));
      } else frag.append(h("em", {}, t.slice(1, -1)));
      last = m.index + t.length;
    }
    if (last < text.length) frag.append(text.slice(last));
    return frag;
  };
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    const hm = /^(#{1,4})\s+(.*)$/.exec(line);
    if (hm) { root.append(h(`h${Math.min(4, hm[1].length)}`, {}, inline(hm[2]))); i++; continue; }
    if (line.startsWith("```")) {
      const buf = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) buf.push(lines[i++]);
      i++;
      root.append(h("pre", {}, h("code", {}, buf.join("\n"))));
      continue;
    }
    if (/^\s*\|/.test(line)) {
      const rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(lines[i++]);
      const cells = (r) => r.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      const head = cells(rows[0]);
      const body = rows.slice(2).map(cells);
      const t = h("table", {}, h("thead", {}, h("tr", {}, head.map((c) => h("th", {}, inline(c))))),
        h("tbody", {}, body.map((r) => h("tr", {}, r.map((c) => h("td", {}, inline(c)))))));
      root.append(h("div", { class: "tablewrap" }, t));
      continue;
    }
    if (/^\s*([-*]|\d+\.)\s+/.test(line)) {
      const ordered = /^\s*\d+\./.test(line);
      const list = h(ordered ? "ol" : "ul");
      while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) {
        let item = lines[i].replace(/^\s*([-*]|\d+\.)\s+/, "");
        i++;
        while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*([-*]|\d+\.)\s+/.test(lines[i])) item += ` ${lines[i++].trim()}`;
        list.append(h("li", {}, inline(item)));
      }
      root.append(list);
      continue;
    }
    if (line.startsWith(">")) {
      const buf = [];
      while (i < lines.length && lines[i].startsWith(">")) buf.push(lines[i++].replace(/^>\s?/, ""));
      root.append(h("blockquote", {}, inline(buf.join(" "))));
      continue;
    }
    const buf = [line];
    i++;
    while (i < lines.length && lines[i].trim() && !/^(#|```|\s*\||\s*([-*]|\d+\.)\s|>)/.test(lines[i])) buf.push(lines[i++]);
    root.append(h("p", {}, inline(buf.join(" "))));
  }
  return root;
}
