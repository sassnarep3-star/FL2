/* FL2 site — data rendering. All table rows are rendered from verified JSON records
   and each row carries a link to the official source where the value was verified. */
(function () {
  "use strict";

  var DATA = {
    standings: "data/verified/standings-2026-reg.json",
    schedule: "data/verified/schedule-week10.json",
    injuries: "data/verified/injuries-week10.json",
    depth: "data/verified/depth-lions-2026.json"
  };

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function load(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status + " loading " + url);
      return r.json();
    });
  }

  function srcCell(url) {
    return '<td class="src"><a href="' + esc(url) + '" target="_blank" rel="noopener">Official source &#8599;</a></td>';
  }

  function onError(targetId, msg) {
    document.getElementById(targetId).innerHTML =
      '<div class="notice bad"><strong>Data unavailable.</strong> ' + esc(msg) +
      ' Tables are rendered from the verified JSON records under <code>data/verified/</code>; ' +
      'each row carries its official source link.</div>';
  }

  /* ---------- Standings ---------- */
  function renderStandings() {
    var box = document.getElementById("standings-table");
    if (!box) return;
    load(DATA.standings).then(function (d) {
      var keys = ["team", "conf", "div", "w", "l", "t", "pct", "pf", "pa", "net", "streak", "last5"];
      var numeric = { w: true, l: true, t: true, pct: true, pf: true, pa: true, net: true };

      function renderRows(rows) {
        var html = "";
        rows.forEach(function (t) {
          html += '<tr><td>' + esc(t.team) + '</td><td>' + esc(t.conf) + '</td><td>' + esc(t.div) + '</td>' +
            '<td class="num">' + esc(t.w) + '</td><td class="num">' + esc(t.l) + '</td>' +
            '<td class="num">' + esc(t.t) + '</td><td class="num">' + esc(t.pct) + '</td>' +
            '<td class="num">' + esc(t.pf) + '</td><td class="num">' + esc(t.pa) + '</td>' +
            '<td class="num">' + (t.net > 0 ? "+" : "") + esc(t.net) + '</td>' +
            '<td>' + esc(t.streak) + '</td><td>' + esc(t.last5) + '</td>' +
            srcCell(t.source) + '</tr>';
        });
        box.querySelector("tbody").innerHTML = html;
      }

      var current = d.teams.slice().sort(function (a, b) {
        return (b.w * 3 + b.t) - (a.w * 3 + a.t) || b.net - a.net;
      });

      var head = '<thead><tr>' +
        '<th class="sortable" data-k="team">Team</th><th>Conf</th><th>Div</th>' +
        '<th class="num sortable" data-k="w">W</th><th class="num sortable" data-k="l">L</th>' +
        '<th class="num sortable" data-k="t">T</th><th class="num sortable" data-k="pct">PCT</th>' +
        '<th class="num sortable" data-k="pf">PF</th><th class="num sortable" data-k="pa">PA</th>' +
        '<th class="num sortable" data-k="net">Net</th><th>Strk</th><th>L5</th>' +
        '<th>Source</th></tr></thead>';
      box.innerHTML = '<table class="data">' + head + '<tbody></tbody></table>';
      renderRows(current);

      box.querySelectorAll("th.sortable").forEach(function (th) {
        th.addEventListener("click", function () {
          var key = th.getAttribute("data-k");
          var asc = th.getAttribute("data-dir") !== "asc";
          box.querySelectorAll("th.sortable").forEach(function (h) { h.removeAttribute("data-dir"); });
          th.setAttribute("data-dir", asc ? "asc" : "desc");
          current.sort(function (a, b) {
            var va = a[key], vb = b[key];
            if (numeric[key]) { va = parseFloat(va); vb = parseFloat(vb); return asc ? va - vb : vb - va; }
            return asc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
          });
          renderRows(current);
        });
      });
    }).catch(function (e) { onError("standings-table", "Could not load standings JSON: " + e.message); });
  }

  /* ---------- Schedule ---------- */
  function renderSchedule() {
    var box = document.getElementById("schedule-table");
    if (!box) return;
    load(DATA.schedule).then(function (d) {
      var html = '<table class="data"><thead><tr>' +
        '<th>Date</th><th>Time (ET)</th><th>Slot</th><th>Away</th><th>Home</th>' +
        '<th>Network</th><th>Status</th><th>Source</th></tr></thead><tbody>';
      d.games.forEach(function (g) {
        html += '<tr><td>' + esc(g.date) + '</td><td>' + esc(g.time) + '</td><td>' + esc(g.slot) + '</td>' +
          '<td>' + esc(g.away) + '</td><td>' + esc(g.home) + '</td>' +
          '<td>' + esc(g.network) + '</td><td>' + esc(g.status) + '</td>' +
          srcCell(g.source) + '</tr>';
      });
      html += '</tbody></table>';
      html += '<h3>Week 10 bye teams</h3><table class="data"><thead><tr>' +
        '<th>Team</th><th>Record</th><th>Source</th></tr></thead><tbody>';
      d.bye_teams.forEach(function (t) {
        html += '<tr><td>' + esc(t.team) + '</td><td>' + esc(t.record) + '</td>' + srcCell(t.source) + '</tr>';
      });
      html += '</tbody></table>';
      box.innerHTML = html;
    }).catch(function (e) { onError("schedule-table", "Could not load schedule JSON: " + e.message); });
  }

  /* ---------- Injuries ---------- */
  function renderInjuries() {
    var box = document.getElementById("injuries-list");
    if (!box) return;
    load(DATA.injuries).then(function (d) {
      var teams = d.teams;
      var html = '<p class="muted">Verified from the official NFL.com injury report (Week 10, 2026 season). ' +
        'Blank injury cell = no injury listed on the official report. Bye teams (CHI, DEN, PHI, TB) have no Week 10 report.</p>';
      html += '<select class="filter" id="injury-filter"><option value="">All ' + teams.length + ' teams</option>';
      teams.forEach(function (t) {
        html += '<option value="' + esc(t.team) + '">' + esc(t.team) + ' (' + esc(t.record) + ')</option>';
      });
      html += '</select>';
      html += '<div id="injury-sections"></div>';
      box.innerHTML = html;

      var sections = document.getElementById("injury-sections");
      function paint() {
        var val = document.getElementById("injury-filter").value;
        var out = "";
        teams.forEach(function (t) {
          if (val && t.team !== val) return;
          out += '<h3>' + esc(t.team) + ' <span class="muted">(' + esc(t.record) + ')</span></h3>';
          out += '<table class="data"><thead><tr><th>Player</th><th>Pos</th><th>Injury</th>' +
            '<th>Practice status</th><th>Game status</th><th>Source</th></tr></thead><tbody>';
          t.rows.forEach(function (r) {
            var cls = r.gs === "Out" ? "out" : (r.gs === "Questionable" ? "q" : (r.gs === "Doubtful" ? "d" : ""));
            var gs = r.gs ? '<span class="status-' + cls + '">' + esc(r.gs) + '</span>' : '<span class="empty">&mdash;</span>';
            out += '<tr><td><a href="' + esc(r.u) + '" target="_blank" rel="noopener">' + esc(r.player) + '</a></td>' +
              '<td>' + esc(r.pos) + '</td>' +
              '<td>' + (r.inj ? esc(r.inj) : '<span class="empty">&mdash;</span>') + '</td>' +
              '<td>' + esc(r.prac) + '</td><td>' + gs + '</td>' + srcCell(d.source) + '</tr>';
          });
          out += '</tbody></table>';
        });
        sections.innerHTML = out || '<p class="empty">No rows match this filter.</p>';
      }
      document.getElementById("injury-filter").addEventListener("change", paint);
      paint();
    }).catch(function (e) { onError("injuries-list", "Could not load injury JSON: " + e.message); });
  }

  /* ---------- Depth chart (Lions example) ---------- */
  function renderDepth() {
    var box = document.getElementById("depth-tables");
    if (!box) return;
    load(DATA.depth).then(function (d) {
      function block(title, arr) {
        var h = '<h3>' + esc(title) + '</h3>';
        h += '<table class="data"><thead><tr><th>Position</th><th>1st string</th><th>2nd string</th>' +
          '<th>3rd string</th><th>4th string</th><th>Source</th></tr></thead><tbody>';
        arr.forEach(function (r) {
          var cells = r.strings.map(function (s) {
            return s ? esc(s) : '<span class="empty">&mdash;</span>';
          }).map(function (c) { return '<td>' + c + '</td>'; }).join("");
          h += '<tr><td>' + esc(r.position) + '</td>' + cells + srcCell(d.source) + '</tr>';
        });
        h += '</tbody></table>';
        return h;
      }
      box.innerHTML =
        block("Offense", d.offense) + block("Defense", d.defense) + block("Special teams", d.special_teams) +
        '<p class="muted">Roster cross-check: <a href="' + esc(d.roster_crosscheck) +
        '" target="_blank" rel="noopener">' + esc(d.roster_crosscheck) + '</a></p>';
    }).catch(function (e) { onError("depth-tables", "Could not load depth chart JSON: " + e.message); });
  }

  /* ---------- Dashboard snapshot (index) ---------- */
  function renderSnapshot() {
    var box = document.getElementById("snapshot");
    if (!box) return;
    Promise.all([load(DATA.standings), load(DATA.schedule), load(DATA.injuries)])
      .then(function (res) {
        var st = res[0], sc = res[1], inj = res[2];
        var injCount = inj.teams.reduce(function (n, t) { return n + t.rows.length; }, 0);
        var outCount = inj.teams.reduce(function (n, t) {
          return n + t.rows.filter(function (r) { return r.gs === "Out"; }).length; }, 0);
        var qCount = inj.teams.reduce(function (n, t) {
          return n + t.rows.filter(function (r) { return r.gs === "Questionable" || r.gs === "Doubtful"; }).length; }, 0);
        var top = st.teams.slice().sort(function (a, b) { return (b.w - a.w) || (b.net - a.net); })[0];
        box.innerHTML =
          '<div class="cards">' +
          '<div class="card"><div class="num">' + st.teams.length + '</div><div class="lbl">Teams in verified 2026 standings <a href="standings.html">&#8599;</a></div></div>' +
          '<div class="card"><div class="num">' + sc.games.length + '</div><div class="lbl">Week 10 games verified <a href="schedule.html">&#8599;</a></div></div>' +
          '<div class="card"><div class="num">' + injCount + '</div><div class="lbl">Injury-report entries verified (Week 10) <a href="injuries.html">&#8599;</a></div></div>' +
          '<div class="card"><div class="num">' + outCount + ' / ' + qCount + '</div><div class="lbl">Players Out / Questionable-Doubtful (Week 10) <a href="injuries.html">&#8599;</a></div></div>' +
          '<div class="card"><div class="num">' + esc(top.team) + '</div><div class="lbl">Top record: ' + esc(top.w + "-" + top.l + "-" + top.t) + ' (' + esc(top.pct) + ') <a href="standings.html">&#8599;</a></div></div>' +
          '</div>';
      })
      .catch(function (e) { box.innerHTML = '<div class="notice bad">Snapshot unavailable: ' + esc(e.message) + '</div>'; });
  }

  /* ---------- nav highlight ---------- */
  function highlightNav() {
    var path = location.pathname.split("/").pop() || "index.html";
    document.querySelectorAll("nav.mainnav a").forEach(function (a) {
      var href = a.getAttribute("href");
      if (href === path) a.classList.add("active");
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    highlightNav();
    renderStandings();
    renderSchedule();
    renderInjuries();
    renderDepth();
    renderSnapshot();
  });
})();
