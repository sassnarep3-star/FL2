/* Progressive enhancement only. The pages are complete without this file: it adds a filter
   box and click-to-sort to each table so a 74-row register and a 1,088-row line table are
   actually readable. No data is fetched, no number is computed here, and nothing is hidden by
   default - a filter only ever removes rows the reader asked to remove. */
(function () {
  "use strict";

  function cells(table) {
    return Array.prototype.slice.call(table.tBodies[0] ? table.tBodies[0].rows : []);
  }

  function addFilter(table, index) {
    if (!table.tBodies[0] || cells(table).length < 8) return;
    var input = document.createElement("input");
    input.type = "search";
    input.className = "tablefilter";
    input.placeholder = "filter " + cells(table).length + " rows - team, market, id, status\u2026";
    input.setAttribute("aria-label", "Filter table " + (index + 1));
    var count = document.createElement("span");
    count.className = "filtercount";
    input.addEventListener("input", function () {
      var q = input.value.trim().toLowerCase();
      var shown = 0;
      cells(table).forEach(function (tr) {
        var hit = !q || tr.textContent.toLowerCase().indexOf(q) !== -1;
        tr.hidden = !hit;
        if (hit) shown++;
      });
      count.textContent = q ? shown + " of " + cells(table).length + " rows shown" : "";
    });
    table.parentNode.insertBefore(input, table);
    table.parentNode.insertBefore(count, table.nextSibling);
  }

  function addSort(table) {
    if (!table.tHead || !table.tBodies[0]) return;
    Array.prototype.forEach.call(table.tHead.rows[0].cells, function (th, i) {
      th.scope = "col";
      th.title = "Sort by " + th.textContent.trim();
      th.addEventListener("click", function () {
        var rows = cells(table);
        var dir = th.getAttribute("data-dir") === "asc" ? -1 : 1;
        Array.prototype.forEach.call(table.tHead.rows[0].cells, function (o) {
          o.removeAttribute("data-active");
        });
        th.setAttribute("data-active", dir === 1 ? "asc" : "desc");
        th.setAttribute("data-dir", dir === 1 ? "asc" : "desc");
        rows.sort(function (a, b) {
          var x = a.cells[i] ? a.cells[i].textContent.trim() : "";
          var y = b.cells[i] ? b.cells[i].textContent.trim() : "";
          var nx = parseFloat(x.replace(/[^0-9.\-+eE]/g, ""));
          var ny = parseFloat(y.replace(/[^0-9.\-+eE]/g, ""));
          var numeric = !isNaN(nx) && !isNaN(ny) && /[-+0-9.]/.test(x) && /[-+0-9.]/.test(y);
          if (numeric) return (nx - ny) * dir;
          if (x === "\u2014") return 1;
          if (y === "\u2014") return -1;
          return x.localeCompare(y) * dir;
        });
        var body = table.tBodies[0];
        rows.forEach(function (tr) { body.appendChild(tr); });
      });
    });
  }

  function init() {
    var tables = Array.prototype.slice.call(document.querySelectorAll("table.grid"));
    tables.forEach(function (t, i) { addFilter(t, i); addSort(t); });
    var n = document.createElement("p");
    n.className = "fine";
    n.textContent = tables.length + " tables on this page: click a column header to sort, use the "
      + "filter box to narrow. Sorting and filtering never change a value.";
    if (document.body.lastElementChild && document.body.lastElementChild.tagName === "FOOTER") {
      document.body.insertBefore(n, document.body.lastElementChild);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
