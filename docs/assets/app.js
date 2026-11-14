// Shared helpers for the static site. No build step, no external libraries.
async function getJSON(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(path + " returned " + r.status);
  return r.json();
}
function esc(s) {
  return String(s === undefined || s === null ? "" : s).replace(/[&<>"']/g, c =>
    ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
}
function srcLink(url, text) {
  if (!url) return '<span class="unverified">UNVERIFIED - no source</span>';
  return '<a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(text || "Source") + "</a>";
}
function statusTag(s) {
  if (!s) return "";
  const cls = s.toLowerCase();
  return '<span class="tag ' + esc(cls) + '">' + esc(s) + "</span>";
}
function emptyBox(el, msg) {
  el.innerHTML = '<div class="notice">' + esc(msg) + "</div>";
}

// Generic filterable, sortable table.
// opts: { el, rows, columns:[{key,label,render?,num?,sort?}], filters:[{key,label,all?}], search:true, countLabel }
function renderTable(opts) {
  const el = opts.el;
  const rows = opts.rows || [];
  let sortKey = null, sortDir = 1;
  const state = {};
  let html = '<div class="toolbar">';
  if (opts.search !== false) html += '<input type="search" placeholder="Search..." data-role="search" aria-label="Search">';
  (opts.filters || []).forEach((f, i) => {
    const vals = [...new Set(rows.map(r => r[f.key] || "").filter(v => v !== ""))].sort();
    html += '<select data-role="filter" data-i="' + i + '" aria-label="' + esc(f.label) + '"><option value="">' + esc(f.label) + ": all</option>";
    vals.forEach(v => { html += '<option value="' + esc(v) + '">' + esc(v) + "</option>"; });
    html += "</select>";
  });
  html += '<span class="count" data-role="count"></span></div>';
  html += '<div class="table-wrap"><table><thead><tr>';
  opts.columns.forEach((c, i) => {
    html += '<th data-col="' + i + '">' + esc(c.label) + ' <span class="arr"></span></th>';
  });
  html += '</tr></thead><tbody data-role="body"></tbody></table></div>';
  el.innerHTML = html;

  const body = el.querySelector('[data-role="body"]');
  const count = el.querySelector('[data-role="count"]');
  const search = el.querySelector('[data-role="search"]');
  const filterEls = el.querySelectorAll('[data-role="filter"]');

  function visible() {
    const q = search ? search.value.trim().toLowerCase() : "";
    return rows.filter(r => {
      for (const f of opts.filters || []) {
        const v = el.querySelector('[data-role="filter"][data-i="' + (opts.filters.indexOf(f)) + '"]').value;
        if (v && String(r[f.key] || "") !== v) return false;
      }
      if (q && !JSON.stringify(r).toLowerCase().includes(q)) return false;
      return true;
    });
  }
  function draw() {
    let list = visible();
    if (sortKey !== null) {
      const col = opts.columns[sortKey];
      list = list.slice().sort((a, b) => {
        const x = col.sort ? col.sort(a) : a[col.key];
        const y = col.sort ? col.sort(b) : b[col.key];
        if (typeof x === "number" && typeof y === "number") return (x - y) * sortDir;
        return String(x ?? "").localeCompare(String(y ?? ""), "en", {numeric: true}) * sortDir;
      });
    }
    body.innerHTML = list.map(r => "<tr>" + opts.columns.map(c => {
      const v = c.render ? c.render(r) : esc(r[c.key]);
      return '<td class="' + (c.num ? "num" : "") + '">' + v + "</td>";
    }).join("") + "</tr>").join("");
    count.textContent = list.length + " of " + rows.length + " " + (opts.countLabel || "rows");
    el.querySelectorAll("th .arr").forEach((a, i) => {
      a.textContent = i === sortKey ? (sortDir === 1 ? "▲" : "▼") : "";
    });
    if (!list.length) body.innerHTML = '<tr><td colspan="' + opts.columns.length + '">No rows match these filters.</td></tr>';
  }
  if (search) search.addEventListener("input", draw);
  filterEls.forEach(f => f.addEventListener("change", draw));
  el.querySelectorAll("th").forEach(th => th.addEventListener("click", () => {
    const i = Number(th.dataset.col);
    if (sortKey === i) sortDir = -sortDir; else { sortKey = i; sortDir = 1; }
    draw();
  }));
  draw();
}

// Highlight the active menu item.
document.addEventListener("DOMContentLoaded", () => {
  const here = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll("nav.menu a").forEach(a => {
    if (a.getAttribute("href") === here) a.classList.add("active");
  });
});
