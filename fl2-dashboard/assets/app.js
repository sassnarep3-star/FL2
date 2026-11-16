/* FL2 site — data rendering. All table rows are rendered from verified JSON records
   and each row carries a link to the official source where the value was verified. */
(function () {
  "use strict";

  var DATA = {
    standings: "data/verified/standings-2026-reg.json",
    schedule: "data/verified/schedule-week10.json",
    injuries: "data/official/injuries-w10-team-summary.json",
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

  /* ---------- Injuries (team-level; player rows are private, see Flagged F-T1) ---------- */
  function renderInjuries() {
    var box = document.getElementById("injuries-list");
    if (!box) return;
    load(DATA.injuries).then(function (d) {
      var clubs = d.clubs;
      var s = d.summary;
      var html = '<p class="muted">Counts computed from the official NFL.com injury report, captured ' + esc(d.captured) +
        ' (' + esc(s.rows) + ' listed players, ' + esc(s.clubs) + ' clubs, ' + esc(s.games) + ' games). ' +
        'A club with no designation shows 0. &ldquo;Differs from stored&rdquo; compares each club with the ' +
        'stored 2026-11-14 capture; it is a change or an error to review, not a verdict.</p>';
      html += '<table class="data"><thead><tr><th>Club</th><th>Record</th><th>Game (ET)</th>' +
        '<th class="num">Listed</th><th class="num">With designation</th><th class="num">Out</th>' +
        '<th class="num">Doubtful</th><th class="num">Questionable</th><th class="num">Did not practice</th>' +
        '<th class="num">Differs from stored</th><th>Source</th></tr></thead><tbody>';
      clubs.forEach(function (c) {
        var diff = c.players_differing_from_stored === null || c.players_differing_from_stored === undefined
          ? '<span class="empty">n/a</span>'
          : (c.players_differing_from_stored ? '<span class="status-q">' + esc(c.players_differing_from_stored) + ' player(s)</span>' : '0');
        html += '<tr><td>' + esc(c.club) + '</td><td>' + esc(c.record_on_report) + '</td>' +
          '<td>' + esc(c.kickoff_et) + ' vs ' + esc(c.opponent_abbr) + '<br><span class="muted">' + esc(c.network) + '</span></td>' +
          '<td class="num">' + esc(c.players_listed) + '</td>' +
          '<td class="num">' + esc(c.with_injury_designation) + '</td>' +
          '<td class="num">' + esc(c.out) + '</td>' +
          '<td class="num">' + esc(c.doubtful) + '</td>' +
          '<td class="num">' + esc(c.questionable) + '</td>' +
          '<td class="num">' + esc(c.did_not_participate) + '</td>' +
          '<td class="num">' + diff + '</td>' +
          srcCell(c.official_report_url) + '</tr>';
      });
      html += '</tbody></table>';
      box.innerHTML = html;
    }).catch(function (e) { onError("injuries-list", "Could not load injury summary JSON: " + e.message); });
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
        var top = st.teams.slice().sort(function (a, b) { return (b.w - a.w) || (b.net - a.net); })[0];
        box.innerHTML =
          '<div class="cards">' +
          '<div class="card"><div class="num">' + st.teams.length + '</div><div class="lbl">Teams in verified 2026 standings <a href="standings.html">&#8599;</a></div></div>' +
          '<div class="card"><div class="num">' + sc.games.length + '</div><div class="lbl">Week 10 games verified <a href="schedule.html">&#8599;</a></div></div>' +
          '<div class="card"><div class="num">' + inj.summary.rows + '</div><div class="lbl">Players on the official Week 10 injury report (captured ' + esc(inj.captured) + ') <a href="injuries.html">&#8599;</a></div></div>' +
          '<div class="card"><div class="num">' + inj.summary.game_status_out + ' / ' + (inj.summary.game_status_questionable + inj.summary.game_status_doubtful) + '</div><div class="lbl">Game status Out / Questionable-Doubtful <a href="injuries.html">&#8599;</a></div></div>' +
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
