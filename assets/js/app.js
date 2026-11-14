/* FL2 site runtime: shared chrome (header/footer), the table renderer, computed
 * stats for the dashboard, and the two special-case views (injury snapshot, depth).
 * No dependencies, no network calls: the site must work from a local clone.
 */
window.FL2 = window.FL2 || {};

(function () {
  var FL2 = window.FL2;
  var DATA = FL2.DATA = FL2.DATA || {};

  FL2.PAGES = [
    { id: "index", href: "index.html", t: "Dashboard", group: "start" },
    { id: "executive-summary", href: "executive-summary.html", t: "Executive summary", group: "start" },
    { id: "requirements", href: "requirements.html", t: "Requirements", group: "define" },
    { id: "questions", href: "questions.html", t: "Open questions", group: "define" },
    { id: "suggestions", href: "suggestions.html", t: "Suggestions", group: "define" },
    { id: "methodology", href: "methodology.html", t: "Line origination", group: "model" },
    { id: "leaderboard", href: "leaderboard.html", t: "Leaderboard", group: "model" },
    { id: "injuries", href: "injuries.html", t: "Injury tracking", group: "football" },
    { id: "availability", href: "availability.html", t: "Depth & backups", group: "football" },
    { id: "markets", href: "markets.html", t: "Markets & combos", group: "football" },
    { id: "data-catalog", href: "data-catalog.html", t: "Data catalogue", group: "trust" },
    { id: "verification", href: "verification.html", t: "Verification", group: "trust" },
    { id: "review", href: "review.html", t: "Flagged for review", group: "trust" },
    { id: "roadmap", href: "roadmap.html", t: "Roadmap", group: "trust" }
  ];

  var GROUPS = { start: "Overview", define: "Define", model: "Model", football: "Football data", trust: "Trust" };

  /* ------------------------------------------------------------------ chrome */
  FL2.renderChrome = function (activeId) {
    var head = document.getElementById("site-header");
    var foot = document.getElementById("site-footer");
    if (head) {
      var links = FL2.PAGES.map(function (p) {
        var cur = p.id === activeId ? ' aria-current="page"' : "";
        return '<a href="' + p.href + '"' + cur + ">" + p.t + "</a>";
      }).join("");
      head.innerHTML =
        '<div class="masthead-inner"><div class="brand"><span class="mark">FL2</span>' +
        '<span>NFL line origination</span><span class="sub">verified-data workspace</span></div>' +
        '<nav class="primary" aria-label="Sections">' + links + "</nav></div>";
      head.className = "masthead";
    }
    var page = (FL2.PAGES.filter(function (p) { return p.id === activeId; })[0]) || {};
    if (foot) {
      foot.innerHTML =
        '<div class="inner"><strong>FL2</strong> — requirements, verified data, methods and open ' +
        'questions for originating NFL lines. Every table row links to the source it was read from; ' +
        'a blank cell means "not confirmable from an official source", never a guess.<br>' +
        'Snapshot captured 2026-11-14 (UTC). Sources are external and open in a new tab; the retrieval ' +
        'path used by the build agent may differ from a direct browser visit (flag FL-018). ' +
        'Nothing here is betting advice or a solicitation — see <a href="markets.html">markets &amp; compliance</a>.<br>' +
        'Repo: <a href="https://github.com/sassnarep3-star/FL2" target="_blank" rel="noopener">sassnarep3-star/FL2</a> · ' +
        'Task board: <a href="COORDINATION.md">COORDINATION.md</a> · this page: ' + (page.t || "") + "</div>";
      foot.className = "site";
    }
  };

  /* ------------------------------------------------------------------- utils */
  var esc = function (s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  FL2.esc = esc;

  var TAG = {
    "done": "ok", "met": "ok", "pass": "ok", "verified": "ok", "direct": "ok", "double": "ok",
    "adopted-this-session": "ok", "adopted-as-guard": "ok", "single": "muted",
    "in progress": "warn", "partially-met": "warn", "unknown": "warn", "snippet": "warn",
    "needs review": "warn", "medium": "muted", "low": "muted", "planned": "warn",
    "questionable": "warn", "recommended": "info", "candidate": "info", "high": "bad",
    "critical": "bad", "blocked": "bad", "fail": "bad", "failed": "bad", "open": "warn",
    "blocker-for-model-trust": "bad", "out": "bad", "doubtful": "bad", "fp": "ok",
    "lp": "warn", "dnp": "bad", "official-league": "info", "official-club": "info",
    "official-regulator": "ok", "commercial-operator": "muted", "academic": "muted",
    "media-of-record": "muted", "secondary-aggregator": "bad", "self-recorded": "info",
    "defined": "muted", "T0": "muted", "T1": "info", "T2": "ok", "T3": "ok", "n/a": "muted",
    "yes": "ok", "no": "bad"
  };
  var badge = function (v) {
    var key = String(v).trim().toLowerCase();
    if (TAG.hasOwnProperty(key) && String(v).length < 30) {
      return '<span class="pill ' + TAG[key] + '">' + esc(v) + "</span>";
    }
    return null;
  };

  var cellHTML = function (v, col) {
    if (v === "" || v === null || v === undefined) return '<span class="blank">–</span>';
    var b = badge(v);
    if (b) return b;
    if (col && col.num && typeof v === "number") return esc(v.toLocaleString("en-US"));
    if (col && col.mono) return '<span class="mono">' + esc(v) + "</span>";
    return esc(v);
  };

  /* ------------------------------------------------------- generic renderer */
  function rowsAsObjects(ds) {
    var rows = ds.rows.map(function (r, i) {
      var o = { __i: i };
      ds.columns.forEach(function (c, j) { o[c.k] = Array.isArray(r) ? r[j] : r[c.k]; });
      return o;
    });
    if (ds.id === "suggestions") {
      // priority is derived, never typed: (Impact + Confidence) * 2 - Effort - Risk
      rows.forEach(function (r) {
        var i = Number(r.i), c = Number(r.c), e = Number(r.e), k = Number(r.r);
        if ([i, c, e, k].every(function (x) { return !isNaN(x); })) r.p = String((i + c) * 2 - e - k);
      });
    }
    return rows;
  }

  FL2.renderTable = function (ds, mount) {
    if (!ds) { mount.innerHTML = '<div class="banner bad">Dataset not loaded: <code>' +
      esc(mount.getAttribute("data-set")) + "</code></div>"; return; }
    var cols = ds.columns.slice();
    var srcDef = ds.source || null;
    if (srcDef && mount.getAttribute("data-nosrc") !== "1") {
      cols = cols.concat([{ k: "__src", t: "Source", synthetic: true }]);
    }
    var all = rowsAsObjects(ds);
    all.forEach(function (r) {
      if (srcDef) r.__src = '<a class="src" href="' + srcDef.url + '" target="_blank" rel="noopener">' +
        esc(srcDef.label) + "</a>";
    });

    var opts = { q: "", chips: {}, sortCol: null, sortDir: 1 };
    var chipCols = (mount.getAttribute("data-chips") || "").split(",").filter(Boolean);
    var searchable = mount.getAttribute("data-search") !== "0";

    var wrap = document.createElement("div");
    wrap.className = "tablewrap";

    // Provenance line: a table without per-row source links must say why, in the
    // table itself, rather than leaving a reader to guess whether links were lost.
    var NOTE = {
      brief: "Provenance: these are project requirements restated from the brief into testable form. No external " +
             "claim is made in this table, so there is no source link to give; every number such a claim would " +
             "need lives in a table that does carry one.",
      register: "Provenance: internal register. Rows reference the source, requirement, question or gate IDs they " +
                "derive from instead of repeating a URL in every cell; those IDs resolve on the pages they name.",
      computed: "Provenance: computed by <code>engine/</code> in this repo from stated inputs — labelled " +
                "“computed (ours)”, never an official or market figure. Reproduce with " +
                "<code>python3 -m engine.selftest</code>."
    };
    var noteKey = mount.getAttribute("data-source-note");
    if (!noteKey && mount.getAttribute("data-nosrc") === "1") noteKey = "register";
    if (noteKey) {
      var p = document.createElement("p");
      p.className = "note srcnote";
      p.innerHTML = NOTE[noteKey] || ("Provenance: " + esc(noteKey));
      mount.appendChild(p);
    }
    mount.appendChild(wrap);

    var chipHTML = chipCols.map(function (key) {
      var col = ds.columns.filter(function (c) { return c.k === key; })[0];
      if (!col) return "";
      var vals = {};
      all.forEach(function (r) { var v = String(r[key] || "—"); vals[v] = (vals[v] || 0) + 1; });
      var list = Object.keys(vals).sort(function (a, b) { return vals[b] - vals[a]; }).slice(0, 10);
      return '<span class="chips" data-chipcol="' + key + '"><span class="note">' + esc(col.t) +
        ":</span> " + list.map(function (v) {
          return '<button class="chip" type="button" aria-pressed="false" data-v="' + esc(v) + '">' +
            esc(v) + " <span class='note'>(" + vals[v] + ")</span></button>";
        }).join("") + "</span>";
    }).join(" ");

    var head = '<div class="tabletools">' +
      (searchable ? '<input type="search" placeholder="Filter this table…" aria-label="Filter table">' : "") +
      chipHTML + '<span class="count"></span></div>';

    function draw() {
      var rows = all;
      if (opts.q) {
        var q = opts.q.toLowerCase();
        rows = rows.filter(function (r) {
          return ds.columns.some(function (c) { return String(r[c.k] === undefined ? "" : r[c.k]).toLowerCase().indexOf(q) >= 0; });
        });
      }
      Object.keys(opts.chips).forEach(function (k) {
        if (opts.chips[k]) rows = rows.filter(function (r) { return String(r[k] || "—") === opts.chips[k]; });
      });
      if (opts.sortCol !== null) {
        var sc = opts.sortCol;
        rows = rows.slice().sort(function (a, b) {
          var x = a[sc], y = b[sc];
          if (x === "" || x === null || x === undefined) return 1;
          if (y === "" || y === null || y === undefined) return -1;
          if (typeof x === "number" && typeof y === "number") return (x - y) * opts.sortDir;
          return String(x).localeCompare(String(y)) * opts.sortDir;
        });
      }
      var thead = "<tr>" + ds.columns.map(function (c) {
        return '<th data-col="' + c.k + '"' + (c.num ? ' class="num"' : "") + ">" + esc(c.t) +
          (opts.sortCol === c.k ? ' <span class="arrow">' + (opts.sortDir > 0 ? "▲" : "▼") + "</span>" : "") + "</th>";
      }).join("") + (srcDef ? '<th>Source</th>' : "") + "</tr>";
      var body = rows.map(function (r) {
        return "<tr>" + cols.map(function (c) {
          if (c.synthetic) return '<td class="src">' + r.__src + "</td>";
          var raw = r[c.k];
          var isBlank = raw === "" || raw === null || raw === undefined;
          return "<td" + (c.num ? ' class="num"' : "") + (isBlank ? ' data-blank="1"' : "") + ">" +
            cellHTML(raw, c) + "</td>";
        }).join("") + "</tr>";
      }).join("");
      wrap.innerHTML = head + (ds.caption ? "" : "") +
        '<table' + (ds.caption ? ' aria-describedby="cap-' + ds.id + '"' : "") + "><thead>" + thead +
        "</thead><tbody>" + (body || '<tr><td colspan="' + cols.length + '">no rows match</td></tr>') +
        "</tbody></table>" +
        '<p class="note" style="padding:8px 12px;margin:0">' + (ds.footer || "") + "</p>";
      var cnt = wrap.querySelector(".count");
      if (cnt) cnt.textContent = "showing " + rows.length + " of " + all.length + " rows";
      var inp = wrap.querySelector('input[type="search"]');
      if (inp) {
        inp.value = opts.q;
        inp.addEventListener("input", function () { opts.q = inp.value; draw(); });
      }
      wrap.querySelectorAll("thead th[data-col]").forEach(function (th) {
        th.addEventListener("click", function () {
          var k = th.getAttribute("data-col");
          if (opts.sortCol === k) opts.sortDir = -opts.sortDir; else { opts.sortCol = k; opts.sortDir = 1; }
          draw();
        });
      });
      wrap.querySelectorAll(".chip").forEach(function (btn) {
        btn.addEventListener("click", function () {
          var col = btn.parentNode.getAttribute("data-chipcol");
          var v = btn.getAttribute("data-v");
          var on = opts.chips[col] === v;
          opts.chips[col] = on ? null : v;
          if (on) delete opts.chips[col];
          wrap.querySelectorAll('[data-chipcol="' + col + '"] .chip').forEach(function (b2) {
            b2.setAttribute("aria-pressed", String(!on && b2.getAttribute("data-v") === v));
          });
          draw();
        });
      });
    }
    draw();
  };

  /* ------------------------------------------------- position-group analysis */
  var OFF = { QB: 1, RB: 1, WR: 1, TE: 1, FB: 1, C: 1, G: 1, T: 1, OT: 1, OG: 1, OL: 1 };
  var DEF = { DE: 1, DT: 1, DL: 1, LB: 1, OLB: 1, ILB: 1, MLB: 1, CB: 1, S: 1, SAF: 1, DB: 1, EDGE: 1, NG: 1 };
  var ST = { K: 1, P: 1, LS: 1 };
  FL2.groupOf = function (pos) {
    if (OFF[pos]) return "offence";
    if (DEF[pos]) return "defence";
    if (ST[pos]) return "special teams";
    return "unmapped";
  };
  var IRRELEVANT = /not injury related/i;

  FL2.injuryStats = function () {
    var d = DATA.injuriesW10;
    var s = { games: 0, rows: 0, out: 0, doubtful: 0, questionable: 0, nodesignation: 0,
      dnp: 0, lp: 0, fp: 0, nir: 0, teams: 0, clubs: {}, bygroup: { offence: 0, defence: 0, "special teams": 0, unmapped: 0 },
      bygroup_out: { offence: 0, defence: 0, "special teams": 0, unmapped: 0 } };
    (d ? d.games : []).forEach(function (g) {
      s.games += 1;
      [g.away, g.home].forEach(function (t) {
        if (!t) return;
        s.teams += 1;
        var c = s.clubs[t.abbr] = s.clubs[t.abbr] || { club: t.club, abbr: t.abbr, record: t.record, rows: 0, out: 0, off_out: 0, def_out: 0, qb_out: 0, ol_out: 0, back_out: 0, skill_out: 0 };
        (t.rows || []).forEach(function (r) {
          s.rows += 1; c.rows += 1;
          var status = r[4], prac = r[3], inj = r[2] || "", pos = r[1];
          if (status === "Out") { s.out += 1; c.out += 1; s.bygroup_out[FL2.groupOf(pos)] += 1; }
          if (status === "Doubtful") s.doubtful += 1;
          if (status === "Questionable") s.questionable += 1;
          if (!status) s.nodesignation += 1;
          if (prac === "DNP") s.dnp += 1; else if (prac === "LP") s.lp += 1; else if (prac === "FP") s.fp += 1;
          if (IRRELEVANT.test(inj)) s.nir += 1;
          s.bygroup[FL2.groupOf(pos)] += 1;
          if (status === "Out" || status === "Doubtful") {
            var grp = FL2.groupOf(pos);
            if (grp === "offence") c.off_out += 1; else if (grp === "defence") c.def_out += 1;
            if (pos === "QB") c.qb_out += 1;
            if (["C", "G", "T", "OT", "OG", "OL"].indexOf(pos) >= 0) c.ol_out += 1;
            if (["RB", "FB"].indexOf(pos) >= 0) c.back_out += 1;
            if (["WR", "TE"].indexOf(pos) >= 0) c.skill_out += 1;
          }
        });
      });
    });
    return s;
  };

  /* ----------------------------------------------- club availability summary */
  FL2.renderAvailabilitySummary = function (mount) {
    // engine status is read from the register the site publishes, never typed into a page
    var eng = { assertions: "—", failures: "—" };
    if (D.computedSelftest) {
      D.computedSelftest.rows.forEach(function (r) {
        if (r[0] === "Assertions passing") eng.assertions = r[1];
        if (r[0] === "Failures") eng.failures = r[1];
      });
    }
    out["engine.assertions"] = eng.assertions;
    out["engine.failures"] = eng.failures;
    var s = FL2.injuryStats();
    var clubs = Object.keys(s.clubs).map(function (k) { return s.clubs[k]; })
      .sort(function (a, b) { return (b.off_out + b.def_out) - (a.off_out + a.def_out) || a.club.localeCompare(b.club); });
    var cols = [["club", "Club"], ["record", "Record"], ["rows", "On report"], ["out", "Out"],
      ["off_out", "Off. Out/Doubtful"], ["def_out", "Def. Out/Doubtful"], ["qb_out", "QB"],
      ["ol_out", "OL"], ["back_out", "Backs"], ["skill_out", "WR/TE"]];
    var html = '<div class="tablewrap"><div class="tabletools"><span class="count">' +
      clubs.length + " clubs captured · counts are derived from the rows on the injuries page (" +
      s.rows + " rows), not new facts</span></div><table><thead><tr>" +
      cols.map(function (c) { return "<th" + (c[0] === "club" ? "" : ' class="num"') + ">" + c[1] + "</th>"; }).join("") +
      "<th>Source</th></tr></thead><tbody>" +
      clubs.map(function (cl) {
        return "<tr><td><strong>" + esc(cl.abbr) + "</strong> " + esc(cl.club) + "</td>" +
          '<td class="num">' + esc(cl.record || "") + "</td>" +
          '<td class="num">' + cl.rows + "</td>" +
          '<td class="num">' + (cl.out ? '<span class="pill bad">' + cl.out + "</span>" : "0") + "</td>" +
          '<td class="num">' + cl.off_out + '</td><td class="num">' + cl.def_out + "</td>" +
          '<td class="num">' + (cl.qb_out ? '<span class="pill bad">' + cl.qb_out + "</span>" : "0") + "</td>" +
          '<td class="num">' + cl.ol_out + "</td><td class='num'>" + cl.back_out + "</td>" +
          '<td class="num">' + cl.skill_out + "</td>" +
          '<td class="src"><a class="src" href="' + DATA.injuriesW10.source_url + '" target="_blank" rel="noopener">nfl.com/injuries</a></td></tr>';
      }).join("") + "</tbody></table></div>";
    mount.innerHTML = html;
  };

  /* -------------------------------------------------- injury snapshot renderer */
  FL2.renderInjuries = function (mount) {
    var d = DATA.injuriesW10;
    if (!d) { mount.innerHTML = '<div class="banner bad">injury dataset missing</div>'; return; }
    var s = FL2.injuryStats();
    var filter = { q: "", status: null, club: null };
    var wrap = document.createElement("div");
    wrap.className = "tablewrap";

    // Provenance line: a table without per-row source links must say why, in the
    // table itself, rather than leaving a reader to guess whether links were lost.
    var NOTE = {
      brief: "Provenance: these are project requirements restated from the brief into testable form. No external " +
             "claim is made in this table, so there is no source link to give; every number such a claim would " +
             "need lives in a table that does carry one.",
      register: "Provenance: internal register. Rows reference the source, requirement, question or gate IDs they " +
                "derive from instead of repeating a URL in every cell; those IDs resolve on the pages they name.",
      computed: "Provenance: computed by <code>engine/</code> in this repo from stated inputs — labelled " +
                "“computed (ours)”, never an official or market figure. Reproduce with " +
                "<code>python3 -m engine.selftest</code>."
    };
    var noteKey = mount.getAttribute("data-source-note");
    if (!noteKey && mount.getAttribute("data-nosrc") === "1") noteKey = "register";
    if (noteKey) {
      var p = document.createElement("p");
      p.className = "note srcnote";
      p.innerHTML = NOTE[noteKey] || ("Provenance: " + esc(noteKey));
      mount.appendChild(p);
    }
    mount.appendChild(wrap);

    function draw() {
      var body = "";
      var shown = 0;
      d.games.forEach(function (g) {
        var gblock = "";
        [g.away, g.home].forEach(function (t) {
          if (!t) return;
          if (filter.club && filter.club !== t.abbr) return;
          var rows = "";
          (t.rows || []).forEach(function (r) {
            if (filter.status && r[4] !== filter.status) return;
            if (filter.q) {
              var hay = (r[0] + " " + r[1] + " " + r[2] + " " + r[3] + " " + r[4]).toLowerCase();
              if (hay.indexOf(filter.q) < 0) return;
            }
            var xcheck = (t.abbr === "MIN" || t.abbr === "GB")
              ? ' · <a class="src" href="' + d.meta_gaps.cross_checked_against[0].url + '" target="_blank" rel="noopener">club cross-check</a>' : "";
            rows += "<tr><td>" + esc(r[0]) + "</td><td>" + badge(r[1] || "") + esc(r[1] || "") + "</td>" +
              "<td>" + (r[2] ? esc(r[2]) : '<span class="blank">–</span>') + "</td>" +
              "<td>" + (badge(r[3]) || esc(r[3])) + "</td>" +
              "<td>" + (r[4] ? badge(r[4]) || esc(r[4]) : '<span class="blank" title="no Friday designation on the official report">– (none listed)</span>') + "</td>" +
              '<td class="src"><a class="src" href="' + d.source_url + '" target="_blank" rel="noopener">nfl.com/injuries</a>' + xcheck + "</td></tr>";
            shown += 1;
          });
          if (!rows && (filter.q || filter.status)) return;
          var head = t.missing
            ? '<tr class="group"><td colspan="6">' + esc(t.club) + " (" + esc(t.abbr) + ") — <em>table not captured in this snapshot; see flag FL-005</em></td></tr>"
            : '<tr class="group"><td colspan="6">' + esc(t.club) + " · " + esc(t.record) +
              " · " + (t.truncated ? esc(t.truncated) : t.rows.length + " rows on the report") + "</td></tr>";
          gblock += head + rows;
        });
        if (gblock) {
          body += '<tr class="group"><td colspan="6" style="background:#e3e8ef">' + esc(g.game) + " · " +
            esc(g.date) + " " + esc(g.time_et) + " ET · " + esc(g.tv) +
            (g.note ? " · " + esc(g.note) : "") + (g.partial ? " · <em>partial capture</em>" : "") + "</td></tr>" + gblock;
        }
      });
      wrap.innerHTML = '<div class="tabletools"><input type="search" placeholder="Filter by player, position or injury…" aria-label="Filter injury rows">' +
        '<span class="chips"><span class="note">Game status:</span>' +
        ["Out", "Doubtful", "Questionable", ""].map(function (v) {
          return '<button class="chip" type="button" data-status="' + v + '" aria-pressed="' +
            (filter.status === (v || null)) + '">' + (v || "no designation") + "</button>";
        }).join("") + "</span>" +
        '<span class="chips"><span class="note">Club:</span>' +
        Object.keys(s.clubs).sort().map(function (k) {
          return '<button class="chip" type="button" data-club="' + k + '" aria-pressed="' + (filter.club === k) + '">' + k + "</button>";
        }).join("") + "</span>" +
        '<span class="count">showing ' + shown + " of " + s.rows + " captured rows</span></div>" +
        '<table><thead><tr><th>Player</th><th>Pos</th><th>Injury (as published)</th><th>Practice status</th><th>Game status</th><th>Source</th></tr></thead><tbody>' +
        (body || '<tr><td colspan="6">no rows match</td></tr>') + "</tbody></table>";
      var inp = wrap.querySelector("input");
      inp.addEventListener("input", function () { filter.q = inp.value.toLowerCase(); draw(); });
      wrap.querySelectorAll("[data-status]").forEach(function (b) {
        b.addEventListener("click", function () {
          var v = b.getAttribute("data-status");
          filter.status = (filter.status === (v || null)) ? null : (v || null);
          draw();
        });
      });
      wrap.querySelectorAll("[data-club]").forEach(function (b) {
        b.addEventListener("click", function () {
          var v = b.getAttribute("data-club");
          filter.club = filter.club === v ? null : v;
          draw();
        });
      });
    }
    draw();
  };

  /* ------------------------------------------------ depth / next man up table */
  FL2.renderNextManUp = function (mount) {
    var inj = DATA.injuriesW10, ros = DATA.rostersW10;
    if (!inj || !ros) { mount.innerHTML = '<div class="banner bad">datasets missing</div>'; return; }
    var byClub = {};
    ros.teams.forEach(function (t) {
      byClub[t.abbr] = {};
      t.players.forEach(function (p) {
        (byClub[t.abbr][p[2]] = byClub[t.abbr][p[2]] || []).push(p);
      });
    });
    var game = null;
    inj.games.forEach(function (g) { if (g.game === "MIN @ GB") game = g; });
    var rows = [];
    [game.away, game.home].forEach(function (t) {
      (t.rows || []).forEach(function (r) {
        if (r[4] !== "Out" && r[4] !== "Doubtful") return;
        var grp = FL2.groupOf(r[1]);
        var pool = (byClub[t.abbr] && byClub[t.abbr][r[1]]) ? byClub[t.abbr][r[1]].filter(function (p) { return p[0] !== r[0]; }) : null;
        var depth = pool ? pool.length : null;
        var nextName = pool && pool.length ? pool[0][0] : "";
        var nextExp = pool && pool.length ? pool[0][6] : "";
        rows.push({
          club: t.abbr, player: r[0], pos: r[1], grp: grp, status: r[4], inj: r[2] || "",
          depth: depth, next: nextName, nextExp: nextExp === "" ? "" : String(nextExp),
          gap: (depth === null) ? "" : (depth <= 1 ? "thin — projection invalid (SG-12 guard)" :
            (Number(nextExp) <= 3 ? "experience cliff: ≤3 yr next man up" : "covered by a veteran"))
        });
      });
    });
    var srcUrl = "https://www.nfl.com/injuries/";
    var rosUrl = { MIN: "https://www.nfl.com/teams/minnesota-vikings/roster", GB: "https://www.nfl.com/teams/green-bay-packers/roster" };
    var body = rows.map(function (r) {
      var next = r.next ? esc(r.next) + (r.nextExp !== "" ? ' <span class="note">(' + esc(r.nextExp) + " yr exp.)</span>" : ' <span class="note">(experience not captured)</span>')
        : '<span class="blank">unverified — position not in the captured roster excerpt</span>';
      return "<tr><td><strong>" + r.club + "</strong></td><td>" + esc(r.player) + "</td><td>" + esc(r.pos) +
        "</td><td>" + badge(r.status) + "</td><td>" + esc(r.grp) + "</td>" +
        "<td>" + (r.inj ? esc(r.inj) : '<span class="blank">–</span>') + "</td>" +
        '<td class="num">' + (r.depth === null ? '<span class="blank">n/a</span>' : r.depth) + "</td>" +
        "<td>" + next + "</td>" +
        "<td>" + (r.gap ? esc(r.gap) : '<span class="blank">not assessable</span>') + "</td>" +
        '<td class="src"><a class="src" href="' + srcUrl + '" target="_blank" rel="noopener">report</a> · ' +
        '<a class="src" href="' + rosUrl[r.club] + '" target="_blank" rel="noopener">roster</a></td></tr>';
    }).join("");
    mount.innerHTML = '<div class="tablewrap"><div class="tabletools"><span class="count">MIN @ GB, Week 10 — ' +
      rows.length + " absent starters · depth counts are only possible where the roster excerpt covers the position</span></div>" +
      '<table><thead><tr><th>Club</th><th>Absent starter</th><th>Pos</th><th>Status</th><th>Unit</th><th>Injury</th>' +
      '<th class="num">Same-pos players in captured roster excerpt</th><th>Next man up (from captured excerpt)</th>' +
      "<th>Deficiency read</th><th>Source</th></tr></thead><tbody>" + body + "</tbody></table>" +
      '<p class="note" style="padding:8px 12px;margin:0">“Next man up” here means the alphabetically-first other ' +
      "player at that position in the captured roster excerpt — it is <em>not</em> a depth-chart ordering, because no " +
      "official ordering source was found (Q-07, FL-013). This table demonstrates the pipeline and its limits, not a projection.</p></div>";
  };

  /* ------------------------------------------------- official roster excerpts */
  FL2.renderRosters = function (mount) {
    var d = DATA.rostersW10;
    if (!d) { mount.innerHTML = '<div class="banner bad">roster dataset missing</div>'; return; }
    var body = "";
    d.teams.forEach(function (t) {
      body += '<tr class="group"><td colspan="8">' + esc(t.club) + " · " + esc(t.standing_line) +
        " · " + esc(t.coverage) + ' · <a class="src" href="' + t.url +
        '" target="_blank" rel="noopener">official roster</a></td></tr>';
      t.players.forEach(function (p) {
        body += "<tr><td>" + esc(p[0]) + "</td>" +
          '<td class="num">' + (p[1] === "" ? '<span class="blank">–</span>' : p[1]) + "</td>" +
          "<td>" + esc(p[2]) + "</td><td>" + (badge(p[3]) || esc(p[3])) + "</td>" +
          '<td class="num">' + (p[4] === "" ? '<span class="blank">–</span>' : p[4]) + "</td>" +
          '<td class="num">' + (p[5] === "" ? '<span class="blank">–</span>' : p[5]) + "</td>" +
          '<td class="num">' + (p[6] === "" ? '<span class="blank">–</span>' : esc(p[6])) + "</td>" +
          "<td>" + (p[7] ? esc(p[7]) : '<span class="blank">–</span>') + "</td></tr>";
      });
      if (t.note) body += '<tr class="group"><td colspan="8" style="background:#fdf9ef;font-weight:400;text-transform:none;letter-spacing:0">' +
        esc(t.note) + "</td></tr>";
    });
    mount.innerHTML = '<div class="tablewrap"><div class="tabletools"><span class="count">' +
      d.teams.reduce(function (a, t) { return a + t.players.length; }, 0) +
      " players captured · columns exactly as published (height in, weight lb, years of experience)" +
      "</span></div><table><thead><tr><th>Player</th><th class='num'>#</th><th>Pos</th><th>Status</th>" +
      '<th class="num">Ht</th><th class="num">Wt</th><th class="num">Exp (yrs)</th><th>College</th></tr></thead>' +
      "<tbody>" + body + "</tbody></table></div>";
  };

  /* --------------------------------------------------------- leaderboard view */
  FL2.renderLeaderboard = function (mount) {
    var d = DATA.leaderboard;
    if (!d) { mount.innerHTML = '<div class="banner bad">leaderboard config missing</div>'; return; }
    var t = function (arr) { return arr.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join(""); };
    var wins = d.windows.map(function (w) {
      return "<tr><td><strong>" + esc(w.name) + "</strong></td><td>" + esc(w.rule) + "</td></tr>";
    }).join("");
    var tiers = d.reward_tiers.map(function (r) {
      return "<tr><td>" + (badge(r.tier.split(" ")[0]) || "") + " " + esc(r.tier) + "</td><td>" + esc(r.gate) +
        "</td><td>" + esc(r.reward) + '</td><td class="num">' + esc(r.max_alloc) + "</td></tr>";
    }).join("");
    var head = "<tr>" + d.standings_columns.map(function (c) { return "<th>" + esc(c) + "</th>"; }).join("") + "</tr>";
    var body = d.standings.map(function (r) {
      return "<tr>" + r.map(function (c) {
        return "<td" + (c === "—" ? ' class="blank"' : "") + ">" + (badge(c) || esc(c)) + "</td>";
      }).join("") + "</tr>";
    }).join("");
    mount.innerHTML =
      '<p class="note srcnote">Provenance: competition design from this repo (no external source is claimable for a ' +
      'rule we set). Scoring inputs — graded bets, closing prices, measured correlations — do not exist yet, so the ' +
      'standings below are intentionally empty rather than illustrative; see the flag register.</p>' +
      '<div class="card"><h3>Score</h3><p><code>' + esc(d.score_formula) + "</code></p>" +
      '<p class="note">Tie-breakers, in order: ' + d.tiebreakers.map(function (x) { return esc(x); }).join(" → ") + "</p></div>" +
      '<div class="tablewrap"><table><thead><tr><th>Window</th><th>Rule</th></tr></thead><tbody>' + wins + "</tbody></table></div>" +
      '<h3>Reward tiers</h3><div class="tablewrap"><table><thead><tr><th>Tier</th><th>Gate condition</th>' +
      '<th>Reward</th><th class="num">Max allocation</th></tr></thead><tbody>' + tiers + "</tbody></table></div>" +
      '<h3>Standings (current window)</h3><div class="tablewrap"><table><thead>' + head + "</thead><tbody>" + body +
      "</tbody></table><p class='note' style='padding:8px 12px;margin:0'>" + esc(d.standing_note) + "</p></div>" +
      '<h3>Penalties and clawbacks</h3><ul class="tight">' + t(d.penalties) + "</ul>" +
      '<div class="banner bad">' + esc(d.warning) + "</div>";
  };

  /* ------------------------------------------------------------------- stats */
  FL2.computeStats = function () {
    var out = {};
    var D = DATA;
    var count = function (k, key, want) {
      var ds = D[k]; if (!ds) return 0;
      var col = ds.columns.map(function (c) { return c.k; }).indexOf(key);
      if (col < 0) return 0;
      return ds.rows.filter(function (r) { return want(String(Array.isArray(r) ? r[col] : r[key])); }).length;
    };
    var n = function (k) { return D[k] ? D[k].rows.length : 0; };
    out["requirements.total"] = n("requirements");
    out["requirements.met"] = count("requirements", "st", function (v) { return v === "met"; });
    out["requirements.partial"] = count("requirements", "st", function (v) { return v === "partially-met"; });
    out["requirements.blocked"] = count("requirements", "st", function (v) { return v === "blocked"; });
    out["requirements.defined"] = count("requirements", "st", function (v) { return v === "defined"; });
    out["questions.total"] = n("questions");
    out["questions.critical"] = count("questions", "pri", function (v) { return v === "critical"; });
    out["suggestions.total"] = n("suggestions");
    out["suggestions.adopted"] = count("suggestions", "disp", function (v) { return v === "adopted-this-session"; });
    out["suggestions.recommended"] = count("suggestions", "disp", function (v) { return v === "recommended"; });
    out["sources.total"] = n("sources");
    out["sources.direct"] = count("sources", "ver", function (v) { return v.indexOf("direct") === 0; });
    out["sources.planned"] = count("sources", "ver", function (v) { return v.indexOf("planned") === 0; });
    out["sources.failed"] = count("sources", "ver", function (v) { return v.indexOf("failed") === 0; });
    out["verification.total"] = n("verification");
    out["verification.double"] = count("verification", "lvl", function (v) { return v === "double"; });
    out["flags.total"] = n("flags");
    out["flags.high"] = count("flags", "sev", function (v) { return v === "high" || v.indexOf("blocker") === 0; });
    out["signals.total"] = n("signals");
    out["signals.candidate"] = count("signals", "st", function (v) { return v.indexOf("candidate") === 0; });
    out["signals.blocked"] = count("signals", "st", function (v) { return v.indexOf("blocked") === 0; });
    out["gates.total"] = n("gates");
    out["corr.total"] = n("correlations");
    out["corr.measured"] = count("correlations", "rho", function (v) { return v !== "—" && v !== ""; });
    var s = FL2.injuryStats();
    out["injuries.rows"] = s.rows; out["injuries.games"] = s.games; out["injuries.teams"] = s.teams;
    out["injuries.out"] = s.out; out["injuries.doubtful"] = s.doubtful;
    out["injuries.questionable"] = s.questionable; out["injuries.nodet"] = s.nodesignation;
    out["injuries.dnp"] = s.dnp; out["injuries.nir"] = s.nir;
    out["injuries.clubs"] = Object.keys(s.clubs).length;
    out["injuries.undef_pos"] = s.bygroup.unmapped || 0;
    return out;
  };

  FL2.fillStats = function () {
    var st = FL2.computeStats();
    document.querySelectorAll("[data-stat]").forEach(function (el) {
      var k = el.getAttribute("data-stat");
      if (st.hasOwnProperty(k)) el.textContent = st[k];
      else { el.textContent = "n/a"; el.classList.add("blank"); }
    });
  };

  /* -------------------------------------------------------------------- init */
  FL2.init = function () {
    var page = document.body.getAttribute("data-page");
    FL2.renderChrome(page);
    var s = FL2.injuryStats();
    document.querySelectorAll(".table-mount").forEach(function (m) {
      var id = m.getAttribute("data-set");
      if (id === "injuries") { FL2.renderInjuries(m); return; }
      if (id === "availability-summary") { FL2.renderAvailabilitySummary(m); return; }
      if (id === "nextmanup") { FL2.renderNextManUp(m); return; }
      if (id === "rosters") { FL2.renderRosters(m); return; }
      if (id === "leaderboard") { FL2.renderLeaderboard(m); return; }
      var ds = DATA[id] || Object.keys(DATA).map(function (k) { return DATA[k]; }).filter(function (d) { return d && d.id === id; })[0];
      if (ds) FL2.renderTable(ds, m);
      else m.innerHTML = '<div class="banner bad">unknown dataset <code>' + esc(id) + "</code></div>";
    });
    document.querySelectorAll(".injury-banner").forEach(function (el) {
      var d = DATA.injuriesW10;
      if (!d) return;
      el.innerHTML = "Snapshot: <strong>" + s.rows + " rows</strong> across <strong>" + d.games.length +
        " game reports</strong> (" + Object.keys(s.clubs).length + " clubs), captured " + d.captured_utc +
        " UTC from <a href=\"" + d.source_url + '" target="_blank" rel="noopener">nfl.com/injuries</a>. ' +
        "Known gaps (FL-005): " + d.meta_gaps.not_captured.join("; ") + ".";
    });
    FL2.fillStats();
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", FL2.init);
  else FL2.init();
})();
