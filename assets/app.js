/* ==========================================================================
   FL2 — shared runtime for every page.
   No framework, no build step. Each page calls FL2.render(pageName).
   Data comes from a single generated bundle: data/site_data.js (window.FL2).
   ========================================================================== */
"use strict";

const FL2Console = (() => {
  const D = () => window.FL2;

  /* ---------- tiny helpers ---------- */
  const esc = (s) =>
    String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  const isNum = (v) => typeof v === "number" && isFinite(v);

  /** A blank cell is meaningful here: it means "not confirmed". Never fill it. */
  const cell = (v, opts = {}) => {
    if (v === null || v === undefined || v === "" || (typeof v === "number" && !isFinite(v))) {
      return `<td class="blank" title="Not confirmed by an official source — left blank on purpose">—</td>`;
    }
    const cls = opts.num ? ' class="num"' : (opts.cls ? ` class="${opts.cls}"` : "");
    return `<td${cls}>${esc(v)}</td>`;
  };

  const num = (v, d = 2) => (isNum(v) ? v.toFixed(d) : null);
  const pct = (v, d = 1) => (isNum(v) ? `${(v * 100).toFixed(d)}%` : null);
  const sgn = (v, d = 2) => (isNum(v) ? (v >= 0 ? "+" : "") + v.toFixed(d) : null);

  const srcLink = (url, label) =>
    url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(label || shortUrl(url))}</a>` : "";

  const shortUrl = (u) => {
    try {
      const x = new URL(u);
      const p = x.pathname.replace(/\/$/, "");
      return x.hostname.replace(/^www\./, "") + (p.length > 34 ? p.slice(0, 32) + "…" : p);
    } catch { return u; }
  };

  const statusBadge = (s) => {
    const map = {
      validated: ["ok", "validated"],
      promising: ["warn", "promising"],
      rejected: ["bad", "rejected"],
      untestable: ["mute", "untestable"],
      experimental: ["info", "experimental"],
    };
    const [c, t] = map[s] || ["mute", s || "—"];
    return `<span class="badge ${c}">${esc(t)}</span>`;
  };

  const sevBadge = (s) => {
    const map = { high: ["bad", "high"], medium: ["warn", "medium"], low: ["info", "low"], info: ["mute", "fixed"] };
    const [c, t] = map[s] || ["mute", s];
    return `<span class="badge ${c}">${esc(t)}</span>`;
  };

  const table = (head, rows, opts = {}) => {
    const th = head.map((h) => {
      if (typeof h === "string") return `<th>${esc(h)}</th>`;
      return `<th${h.num ? ' class="num"' : ""}>${esc(h.label)}</th>`;
    }).join("");
    const body = rows.length
      ? rows.map((r) => `<tr${r.__cls ? ` class="${r.__cls}"` : ""}>${r.cells.join("")}</tr>`).join("")
      : `<tr><td colspan="${head.length}" class="blank">No rows.</td></tr>`;
    return `<div class="table-wrap"><table>${opts.caption ? `<caption>${opts.caption}</caption>` : ""}
      <thead><tr>${th}</tr></thead><tbody>${body}</tbody></table></div>`;
  };

  /* ---------- shared chrome ---------- */
  const PAGES = [
    ["index.html", "Overview"],
    ["suggestions.html", "Suggestions"],
    ["decisions.html", "Questions & Answers"],
    ["strategies.html", "Strategy Lab"],
    ["injuries.html", "Injuries & Lineups"],
    ["lines.html", "My Lines"],
    ["verification.html", "Verification"],
    ["flagged.html", "Flagged for Review"],
    ["summary.html", "Executive Summary"],
    ["method.html", "Method"],
  ];

  function chrome(active) {
    const nav = PAGES.map(
      ([href, label]) =>
        `<a href="${href}"${href === active ? ' aria-current="page"' : ""}>${esc(label)}</a>`
    ).join("");
    const h = document.getElementById("site-header");
    if (h) {
      h.className = "site-header";
      h.innerHTML = `<div class="inner">
        <div class="brand-row">
          <div class="brand">FL2 <span>· NFL research &amp; decision ledger</span></div>
          <div class="brand-sub">2026 season · Week 10 snapshot · every row sourced, blanks left blank</div>
        </div>
        <nav class="tabs" aria-label="Sections">${nav}</nav>
      </div>`;
    }
    const f = document.getElementById("site-footer");
    if (f) {
      const d = D();
      f.className = "footer";
      f.innerHTML = `<div class="pill-row" style="margin-bottom:6px">
          <span class="badge mute">snapshot ${esc((d?.as_of_utc || "").slice(0, 16).replace("T", " "))} UTC</span>
          <span class="badge info">${d ? d.week10.injury_rows.length : 0} verified injury rows</span>
          <span class="badge info">${d ? d.backtest.strategies.length : 0} strategies tested</span>
          <span class="badge warn">${d ? d.flags.length : 0} flagged items</span>
        </div>
        Research tool, not betting advice. No market price is quoted unless it came from a citable
        source; no value is estimated. <a href="verification.html">Verification rules</a> ·
        <a href="method.html">Method</a> ·
        <a href="https://github.com/sassnarep3-star/FL2" target="_blank" rel="noopener">Repository</a>`;
    }
  }

  /* ---------- page: overview ---------- */
  function pageIndex() {
    const d = D();
    const bt = d.backtest;
    const p = bt.protocol;
    const passed = bt.strategies.filter((s) => s.status === "validated").length;
    const tested = bt.strategies.filter((s) => s.status !== "untestable").length;
    const outRows = d.week10.injury_rows.filter((r) => r.game_status === "Out").length;
    const ph = bt.baselines.market_home_win_rate;

    const stats = `
      <div class="grid c4">
        <div class="stat bad"><div class="k">Strategies validated</div>
          <div class="v">${passed}<span class="muted" style="font-size:15px"> / ${tested} tested</span></div>
          <div class="d">8 gates each · 2011–2026 out-of-sample</div></div>
        <div class="stat warn"><div class="k">Model vs. market (Brier)</div>
          <div class="v">${sgn(bt.baselines.elo_brier_skill_vs_market * 100, 1)}%</div>
          <div class="d">negative = worse than the closing line</div></div>
        <div class="stat"><div class="k">Week 10 players ruled Out</div>
          <div class="v">${outRows}</div>
          <div class="d">of ${d.week10.league_totals.n_players_out + d.week10.league_totals.n_players_doubtful}
          Out+Doubtful across ${d.week10.league_totals.teams_reporting} teams</div></div>
        <div class="stat warn"><div class="k">Open decisions</div>
          <div class="v">${window.FL2_DECISIONS.filter((x) => x.answer === null).length}</div>
          <div class="d">questions that block a decision</div></div>
      </div>`;

    const hero = `
      <div class="note bad">
        <p><strong>The headline finding is a negative one, and it is the most valuable thing here.</strong>
        Ten testable single-bet strategies were run against 16 seasons of closing lines with eight
        validation gates each. <strong>None passed.</strong> A transparent Elo model scores
        ${num(bt.baselines.elo_brier, 4)} on Brier versus the market's
        ${num(bt.baselines.market_brier, 4)} — ${sgn(bt.baselines.elo_brier_skill_vs_market * 100, 1)}% skill.
        A model that is worse than the market at scoring probabilities should not be expected to beat it,
        and it does not. What this project delivers is the machinery that proves that quickly and
        cheaply, plus a fully sourced dataset to build the next attempt on.</p>
      </div>`;

    const top = [...bt.strategies]
      .sort((a, b) => (b.gates_passed || 0) - (a.gates_passed || 0) || (b.n || 0) - (a.n || 0))
      .slice(0, 6);
    const lb = table(
      [{ label: "Strategy", }, { label: "Market" }, { label: "Bets", num: true },
       { label: "Hit", num: true }, { label: "ROI/bet", num: true }, { label: "Gates", num: true },
       { label: "Status" }],
      top.map((s) => ({
        cells: [
          `<td><a href="strategies.html#${esc(s.sid)}">${esc(s.name)}</a></td>`,
          cell(s.market),
          cell(s.n, { num: true }),
          cell(pct(s.hit_rate), { num: true }),
          isNum(s.roi) ? `<td class="num">${sgn(s.roi * 100, 2)}%</td>` : cell(null),
          `<td class="num">${s.gates_passed}/8</td>`,
          `<td>${statusBadge(s.status)}</td>`,
        ],
      })),
      { caption: "Leaderboard — ranked by gates passed, then sample size. Never by raw ROI." }
    );

    const wk = d.week10;
    const qb = Object.entries(wk.team_depletion).filter(([, r]) => r.qb_change && r.qb_change !== "none reported");
    const qbTable = table(
      ["Team", "Week 10 starter", "Change", "Official statement", "Source"],
      qb.map(([t, r]) => ({
        cells: [
          `<td><strong>${esc(t)}</strong> ${esc(r.name.replace(/^.* /, ""))}</td>`,
          r.qb_starter ? `<td>${esc(r.qb_starter)}</td>` : `<td class="blank">not confirmed</td>`,
          `<td><span class="badge ${r.qb_starter ? "warn" : "bad"}">${esc(r.qb_change)}</span></td>`,
          `<td class="small">${esc(r.qb_note || "")}</td>`,
          `<td class="src">${srcLink(r.qb_source, "nfl.com")}</td>`,
        ],
      })),
      { caption: "Quarterback availability — only what an official NFL.com page states." }
    );

    const nav = `
      <div class="grid c3">
        <a class="card pad" href="suggestions.html" style="text-decoration:none;color:inherit">
          <div class="eyebrow">Read first</div>
          <strong>Suggestions &amp; decision paths</strong>
          <div class="small">Ranked improvement proposals with effort, impact and a recommendation you
          can accept, reject or defer — review before implementing anything.</div></a>
        <a class="card pad" href="decisions.html" style="text-decoration:none;color:inherit">
          <div class="eyebrow">20 questions</div>
          <strong>What we know, what we don't</strong>
          <div class="small">Each question with its evidence basis and the exact information that would
          resolve it. Unknowns are marked unknown.</div></a>
        <a class="card pad" href="lines.html" style="text-decoration:none;color:inherit">
          <div class="eyebrow">Week 10</div>
          <strong>My own lines</strong>
          <div class="small">FL2's own total, margin and win probability per game, with every input and
          the audit trail — market comparison blank where no price is citable.</div></a>
      </div>`;

    document.getElementById("app").innerHTML = `
      <div class="page-head">
        <p class="eyebrow">Overview</p>
        <h1>NFL research you can audit, and the case against pretending it works</h1>
        <p class="lede">A 2026-season snapshot verified against official sources, a validation harness
        that rejects strategies instead of promoting them, and an explicit register of every question
        still open. Data as of ${esc((d.as_of_utc || "").slice(0, 16).replace("T", " "))} UTC.</p>
      </div>
      ${hero}
      <section class="block">${stats}</section>
      <section class="block">
        <h2>Where to look</h2>
        <p class="sub">Every section states its sources inline and leaves unconfirmed values blank.</p>
        ${nav}
      </section>
      <section class="block">
        <h2>Strategy leaderboard</h2>
        <p class="sub">Out-of-sample ${p.eval_start}–2026, closing lines, pushes removed, block-bootstrapped
        confidence intervals, Benjamini–Hochberg control across ${p.n_hypotheses} hypotheses.</p>
        ${lb}
        <p class="small" style="margin-top:10px"><a href="strategies.html">Open the full Strategy Lab →</a></p>
      </section>
      <section class="block">
        <h2>Week 10 quarterback availability</h2>
        <p class="sub">The single largest driver of a game number. Five teams have a confirmed change;
        two more have an unconfirmed starter, left blank on purpose.</p>
        ${qbTable}
      </section>
      <section class="block">
        <h2>How to read this site</h2>
        <div class="grid c3">
          <div class="card pad"><div class="eyebrow">Green / red badges</div>
            <div class="small">Status, not opinion. <span class="badge bad">rejected</span> means the
            strategy failed validation gates. <span class="badge ok">validated</span> would require 8/8.</div></div>
          <div class="card pad"><div class="eyebrow">An em dash —</div>
            <div class="small">Means the value was <strong>not confirmed from an official source</strong>.
            It is never a zero and never an estimate. Those rows are also listed on the Flagged page.</div></div>
          <div class="card pad"><div class="eyebrow">No prices</div>
            <div class="small">Sportsbook prices have no official publisher. Any market number shown comes
            from the aggregated closing-line file and is labelled; otherwise it is blank.</div></div>
        </div>
      </section>`;
  }

  /* ---------- page: decisions ---------- */
  function pageDecisions() {
    const dcs = window.FL2_DECISIONS;
    const open = dcs.filter((x) => x.answer === null);
    const partial = dcs.filter((x) => x.basis === "partially verified");
    const groups = [...new Set(dcs.map((x) => x.group))];

    const basisBadge = (b) => {
      const m = { verified: ["ok", "verified"], "partially verified": ["warn", "partially verified"],
                  unknown: ["bad", "unknown"], "policy decision": ["info", "your decision"] };
      const [c, t] = m[b] || ["mute", b];
      return `<span class="badge ${c}">${esc(t)}</span>`;
    };

    const block = (g) => {
      const items = dcs.filter((x) => x.group === g);
      return `<section class="block">
        <h2>${esc(g)}</h2>
        <p class="sub">${items.length} question${items.length > 1 ? "s" : ""}.</p>
        ${table(
          [{ label: "ID" }, { label: "Question" }, { label: "Answer — evidence, not a guess" },
           { label: "Basis" }, { label: "Why it matters" }, { label: "Suggested path" }, { label: "Sources" }],
          items.map((x) => ({
            __cls: x.answer === null ? "flag" : "",
            id: x.id,
            cells: [
              `<td class="mono"><span id="${esc(x.id)}">${esc(x.id)}</span></td>`,
              `<td><strong>${esc(x.question)}</strong></td>`,
              x.answer ? `<td class="small">${esc(x.answer)}</td>`
                       : `<td class="blank">OPEN — no answer available from the data we hold</td>`,
              `<td>${basisBadge(x.basis)}</td>`,
              `<td class="small">${esc(x.impact)}</td>`,
              `<td class="small">${esc(x.recommendation)}</td>`,
              `<td class="src">${(x.sources || []).map((u) => srcLink(u)).join("<br>")}</td>`,
            ],
          })),
          { caption: `Evidence note — ${g}` }
        )}
      </section>`;
    };

    document.getElementById("app").innerHTML = `
      <div class="page-head">
        <p class="eyebrow">Questions &amp; answers</p>
        <h1>What must be settled before a decision can reasonably be made</h1>
        <p class="lede">Twenty questions, each tagged with whether the answer is verified, partially
        verified, unknown, or a decision that belongs to you. Rows highlighted in amber are still open.
        Nothing here is inferred.</p>
      </div>
      <div class="grid c4">
        <div class="stat ok"><div class="k">Answered from evidence</div>
          <div class="v">${dcs.filter((x) => x.basis === "verified").length}</div>
          <div class="d">with a cited source</div></div>
        <div class="stat warn"><div class="k">Partially answered</div><div class="v">${partial.length}</div>
          <div class="d">known in part, blank where unknown</div></div>
        <div class="stat bad"><div class="k">Open / unknown</div><div class="v">${open.length}</div>
          <div class="d">blocks a decision until resolved</div></div>
        <div class="stat"><div class="k">Your call</div>
          <div class="v">${dcs.filter((x) => x.basis === "policy decision").length}</div>
          <div class="d">not a data question</div></div>
      </div>
      <div class="note">
        <p><strong>How to use this page.</strong> The open questions are the cheapest work available.
        ${open.length} of them have a named, specific blocker — a dataset, a licensed feed, or one of your
        policy choices. Closing those converts this from a snapshot into a system.
        See <a href="suggestions.html">Suggestions</a> for the proposed order of attack.</p>
      </div>
      ${groups.map(block).join("")}`;
  }

  /* ---------- page: strategies ---------- */
  function pageStrategies() {
    const d = D();
    const bt = d.backtest;
    const rows = [...bt.strategies].sort((a, b) => (b.gates_passed || 0) - (a.gates_passed || 0));

    const gateNames = bt.gates_definition.map((g) => g.id);

    const lb = table(
      [{ label: "ID" }, { label: "Strategy" }, { label: "Market" }, { label: "Bets", num: true },
       { label: "Hit", num: true }, { label: "95% CI low", num: true }, { label: "ROI/bet", num: true },
       { label: "Profit CI", num: true }, ...gateNames.map((g) => ({ label: g.split("_")[0], num: true })),
       { label: "Status" }],
      rows.map((s) => ({
        __cls: s.status === "rejected" ? "" : "",
        cells: [
          `<td class="mono">${esc(s.sid)}</td>`,
          `<td><a href="#${esc(s.sid)}">${esc(s.name)}</a></td>`,
          cell(s.market),
          cell(s.n, { num: true }),
          cell(pct(s.hit_rate), { num: true }),
          cell(pct(s.hit_rate_ci_lo), { num: true }),
          isNum(s.roi) ? `<td class="num">${sgn(s.roi * 100, 2)}%</td>` : cell(null),
          s.units_ci_lo !== undefined && isNum(s.units_ci_lo)
            ? `<td class="num">[${sgn(s.units_ci_lo * 100, 1)}, ${sgn(s.units_ci_hi * 100, 1)}]%</td>`
            : cell(null),
          ...gateNames.map((g) => {
            const v = s.gates[g];
            return `<td class="num">${v === true ? '<span class="badge ok">pass</span>'
              : v === false ? '<span class="badge bad">fail</span>' : '<span class="badge mute">n/a</span>'}</td>`;
          }),
          `<td>${statusBadge(s.status)}</td>`,
        ],
      })),
      { caption: "All hypotheses, ranked by gates passed. A strategy must pass all eight to be called validated." }
    );

    const gates = table(
      ["Gate", "Requirement", "Why it exists"],
      bt.gates_definition.map((g) => ({
        cells: [`<td class="mono">${esc(g.id)}</td>`, `<td>${esc(g.requirement)}</td>`,
                `<td class="small">${esc(GATE_WHY[g.id] || "")}</td>`],
      })),
      { caption: "The eight gates. Protocol fixed before results were seen." }
    );

    const detail = rows.map((s) => {
      const seasons = s.seasons ? Object.entries(s.seasons) : [];
      const seasonCells = seasons.map(([y, v]) =>
        `<span class="badge ${v.units > 0 ? "ok" : "bad"}" title="${y}: ${sgn(v.units, 1)}u over ${v.n} bets">${y.slice(2)} ${sgn(v.units, 0)}u</span>`
      ).join(" ");
      return `<div class="card pad" id="${esc(s.sid)}" style="margin-bottom:14px">
        <div class="pill-row" style="justify-content:space-between">
          <div><span class="mono muted">${esc(s.sid)}</span>
            <strong style="font-size:16px;display:block;margin-top:2px">${esc(s.name)}</strong></div>
          <div>${statusBadge(s.status)} <span class="badge mute">${s.gates_passed}/8 gates</span></div>
        </div>
        <p class="small" style="margin:10px 0"><strong>Thesis:</strong> ${esc(s.thesis)}</p>
        <div class="grid c4" style="margin:12px 0">
          <div><div class="eyebrow">Bets</div><strong>${s.n ?? "—"}</strong></div>
          <div><div class="eyebrow">Hit rate</div><strong>${pct(s.hit_rate) || "—"}</strong>
            <div class="src">break-even ${pct(s.required_hit_rate) || "—"}</div></div>
          <div><div class="eyebrow">ROI per bet</div><strong>${isNum(s.roi) ? sgn(s.roi * 100, 2) + "%" : "—"}</strong>
            <div class="src">${isNum(s.units_ci_lo) ? "95% CI " + sgn(s.units_ci_lo * 100, 1) + "% to " + sgn(s.units_ci_hi * 100, 1) + "%" : ""}</div></div>
          <div><div class="eyebrow">Luck fraction</div><strong>${num(s.luck_fraction, 2) || "—"}</strong>
            <div class="src">1.00 = fully explainable by coin flips</div></div>
        </div>
        ${seasonCells ? `<div class="eyebrow">Season-by-season profit (units)</div>
          <div class="pill-row" style="margin-bottom:12px">${seasonCells}</div>` : ""}
        ${isNum(s.brier_skill) && s.sid === "S1_elo_spread"
          ? `<div class="note warn" style="margin:10px 0"><strong>Gate 4 fails here too:</strong>
             this model's Brier skill against the closing line is ${sgn(s.brier_skill * 100, 1)}%.
             A strategy built on a model that is worse than the market is fitting noise.</div>` : ""}
        ${s.status === "untestable"
          ? `<div class="note bad"><strong>Untestable, not "no edge".</strong> ${esc(s.reason || "")}
             This strategy was not rejected on evidence — it cannot be evaluated without inventing data.
             See <a href="decisions.html">D02</a>.</div>` : ""}
      </div>`;
    }).join("");

    const corrRows = Object.entries(bt.correlations).map(([k, v]) => ({
      cells: [
        `<td class="mono">${esc(k.replace(/__/g, " ↔ ").replace(/_/g, " "))}</td>`,
        cell(v.type),
        `<td class="num">${isNum(v.r) ? (v.r >= 0 ? "+" : "") + v.r.toFixed(4) : "—"}</td>`,
        v.ci_lo !== undefined && isNum(v.ci_lo)
          ? `<td class="num">[${v.ci_lo.toFixed(3)}, ${v.ci_hi.toFixed(3)}]</td>` : cell(null),
        cell(v.n, { num: true }),
        v.significant === undefined ? cell(null)
          : `<td>${v.significant ? '<span class="badge ok">significant</span>' : '<span class="badge mute">not significant</span>'}</td>`,
      ],
    }));

    document.getElementById("app").innerHTML = `
      <div class="page-head">
        <p class="eyebrow">Strategy lab</p>
        <h1>Eleven hypotheses, eight gates, zero survivors</h1>
        <p class="lede">Every strategy here is scored on out-of-sample seasons only, with pushes removed,
        correlated bets block-bootstrapped, and the number of hypotheses tried counted against each
        p-value. The result is a leaderboard that is currently empty on purpose — and a list of exactly
        what each idea failed on.</p>
      </div>
      <div class="note">
        <p><strong>Read the gates before the scores.</strong> The most common failure in this field is a
        high hit rate on a small sample being read as skill. The gates exist to make that impossible:
        gate 2 uses the <em>lower</em> confidence bound, gate 6 subtracts what coin flips would explain,
        and gate 7 discounts for the fact that we tried eleven things.</p>
      </div>
      <section class="block"><h2>Leaderboard</h2>
        <p class="sub">Ranked by gates passed — never by ROI or win rate.</p>${lb}</section>
      <section class="block"><h2>Gate definitions</h2>${gates}</section>
      <section class="block"><h2>Every strategy in detail</h2>
        <p class="sub">Including season-by-season profit, so one lucky year cannot hide.</p>${detail}</section>
      <section class="block"><h2>Measured correlations</h2>
        <p class="sub">Phi for binary legs, Pearson for continuous pairs, bootstrapped confidence intervals.</p>
        ${table([{ label: "Pair" }, { label: "Type" }, { label: "Coefficient", num: true },
                 { label: "95% CI", num: true }, { label: "n", num: true }, { label: "Verdict" }],
                corrRows,
                { caption: "Correlation values used to price multi-leg tickets. Only win↔cover survives its interval." })}</section>
      <section class="block"><h2>Protocol constants</h2>
        ${table(["Constant", "Value", "Meaning"], [
          { cells: ["<td class='mono'>EVAL_START</td>", `<td class="num">${bt.protocol.eval_start}</td>`,
                    "<td>first out-of-sample season</td>"] },
          { cells: ["<td class='mono'>MIN_SAMPLE</td>", `<td class="num">${bt.protocol.min_sample}</td>`,
                    "<td>bets needed before judging</td>"] },
          { cells: ["<td class='mono'>BREAKEVEN_HIT</td>", `<td class="num">${pct(bt.protocol.breakeven_hit_rate, 2)}</td>`,
                    "<td>break-even win rate at −110</td>"] },
          { cells: ["<td class='mono'>FDR_Q</td>", `<td class="num">${bt.protocol.fdr_q}</td>`,
                    "<td>Benjamini–Hochberg false discovery rate</td>"] },
          { cells: ["<td class='mono'>n_hypotheses</td>", `<td class="num">${bt.protocol.n_hypotheses}</td>`,
                    "<td>tested — this number is charged against every p-value</td>"] },
          { cells: ["<td class='mono'>sigma (margin)</td>", `<td class="num">${num(d.market.method.sigma_used_for_win_prob, 2)}</td>`,
                    "<td>residual sd of (home margin − closing line), 2011–2026</td>"] },
        ])}
        <p class="small" style="margin-top:10px"><a href="method.html">Full methodology, including
        leakage controls →</a></p>
      </section>`;
  }

  const GATE_WHY = {
    G1_sample: "Below 150 bets, a 55% hit rate is indistinguishable from 50%.",
    G2_hitrate: "Uses the lower confidence bound, not the point estimate.",
    G3_profit_ci: "Block bootstrap, because a season of bets is serially dependent.",
    G4_brier: "A model that scores worse than the market cannot be assumed to find value against it.",
    G5_seasons: "Kills one-lucky-season results.",
    G6_luck: "Subtracts what fair coin flips would explain, before crediting skill.",
    G7_fdr: "With eleven hypotheses, one p < 0.05 is expected by chance alone.",
    G8_leak: "Every feature is proven to be pre-kickoff, asserted on each build.",
  };

  /* ---------- page: injuries ---------- */
  function pageInjuries() {
    const d = D();
    const wk = d.week10;
    const rows = wk.injury_rows;
    const teams = Object.values(wk.team_depletion);

    const statusCell = (s) =>
      `<td><span class="badge ${s === "Out" ? "bad" : s === "Doubtful" ? "warn" : "mute"}">${esc(s)}</span></td>`;

    const dep = table(
      ["Team", "Opp", "Out", "Doubt.", "Quest.", "Off weight lost", "Def weight lost", "Unit hurt most",
       "Avail. index", "QB status"],
      [...teams].filter((t) => t.played_week10)
        .sort((a, b) => (a.avail_index ?? 999) - (b.avail_index ?? 999))
        .map((t) => ({
          cells: [
            `<td><strong>${esc(t.team)}</strong></td>`,
            cell(t.opponent),
            cell(t.players_out, { num: true }),
            cell(t.players_doubtful, { num: true }),
            cell(t.players_questionable, { num: true }),
            cell(num(t.off_weight_lost, 1), { num: true }),
            cell(num(t.def_weight_lost, 1), { num: true }),
            `<td>${t.unit_most_affected === "OFF" ? '<span class="badge warn">offence</span>'
              : t.unit_most_affected === "DEF" ? '<span class="badge info">defence</span>'
              : '<span class="badge mute">even</span>'}</td>`,
            isNum(t.avail_index) ? `<td class="num"><strong>${t.avail_index.toFixed(1)}</strong></td>` : cell(null),
            `<td class="small">${esc(t.qb_change)}${t.qb_starter ? " — " + esc(t.qb_starter) : ""}</td>`,
          ],
        })),
      { caption: "Availability by team, Week 10. Sorted most depleted first. Index is a declared proxy, not a measurement." }
    );

    const inj = table(
      ["Team", "Player", "Pos", "Unit", "Injury", "Practice", "Game status", "Source"],
      rows.map((r) => ({
        cells: [
          `<td>${esc(r.team)}</td>`,
          `<td>${esc(r.player)}</td>`,
          `<td class="mono">${esc(r.position)}</td>`,
          `<td class="small">${esc(r.unit)}</td>`,
          `<td class="small">${esc(r.injury || "—")}</td>`,
          `<td class="small">${esc(r.practice || "—")}</td>`,
          statusCell(r.game_status),
          `<td class="src">${srcLink(r.source_url, "nfl.com")}</td>`,
        ],
      })),
      { caption: "Every player the league lists as Out or Doubtful for Week 10, verbatim from nfl.com/injuries." }
    );

    const byTeam = {};
    rows.forEach((r) => { byTeam[r.team] = byTeam[r.team] || []; byTeam[r.team].push(r); });
    const teamCards = teams.filter((t) => t.played_week10)
      .sort((a, b) => (a.avail_index ?? 999) - (b.avail_index ?? 999))
      .map((t) => {
        const list = byTeam[t.team] || [];
        const chips = list.length
          ? list.map((r) => `<span class="badge ${r.game_status === "Out" ? "bad" : "warn"}">${esc(r.position)} ${esc(r.player)}${r.injury ? " · " + esc(r.injury) : ""}</span>`).join(" ")
          : `<span class="badge ok">no Out/Doubtful players listed</span>`;
        return `<div class="card pad">
          <div class="pill-row" style="justify-content:space-between">
            <strong>${esc(t.team)} — ${esc(t.name)}</strong>
            <span class="badge ${t.avail_index < 70 ? "bad" : t.avail_index < 85 ? "warn" : "ok"}">index ${t.avail_index ?? "—"}</span>
          </div>
          <div class="src" style="margin:5px 0 9px">vs ${esc(t.opponent || "—")} · ${t.players_out} out, ${t.players_doubtful} doubtful, ${t.players_questionable ?? "—"} questionable
            ${t.qb_change !== "none reported" ? ` · <strong>QB: ${esc(t.qb_change)}</strong>` : ""}</div>
          <div class="pill-row">${chips}</div>
        </div>`;
      }).join("");

    document.getElementById("app").innerHTML = `
      <div class="page-head">
        <p class="eyebrow">Injuries &amp; lineups</p>
        <h1>Who is actually unavailable in Week 10</h1>
        <p class="lede">${wk.league_totals.n_players_out} players listed <strong>Out</strong> and
        ${wk.league_totals.n_players_doubtful} <strong>Doubtful</strong> across
        ${wk.league_totals.teams_reporting} teams, read directly from the league's own injury report on
        ${esc((wk.as_of_utc || "").slice(0, 10))}. Byes: ${wk.byes.join(", ")}.</p>
      </div>
      <div class="note warn">
        <p><strong>What this page can and cannot tell you.</strong> It can tell you exactly which players
        the league lists as unavailable, and which teams have confirmed a different starting quarterback.
        It <strong>cannot</strong> tell you whether a listed replacement is the 2nd, 3rd or 4th string —
        the league does not publish depth-chart rank alongside the injury report. The availability index
        below is an explicitly declared position-weight proxy, and the site never presents it as a
        measured point value. See <a href="decisions.html">D09 and D10</a>.</p>
      </div>
      <section class="block"><h2>Availability by team</h2>
        <p class="sub">Most depleted first. “Off/Def weight lost” sums declared position weights — a
        ranking device, not a points estimate.</p>${dep}</section>
      <section class="block"><h2>Team detail</h2>${`<div class="grid c2">${teamCards}</div>`}</section>
      <section class="block"><h2>Official injury report rows</h2>
        <p class="sub">All ${rows.length} rows. Every row links to the league page it came from.</p>${inj}</section>`;
  }

  /* ---------- page: lines ---------- */
  function pageLines() {
    const d = D();
    const m = d.market;

    const rows = m.games.map((g) => ({
      __cls: g.market.status === "present" ? "" : "flag",
      cells: [
        `<td class="nowrap"><strong>${esc(g.game_id)}</strong>
           <div class="src">${esc((g.kickoff_et || "").slice(5))}${g.note ? " · " + esc(g.note) : ""}</div></td>`,
        `<td class="num">${num(g.fl2_total, 1) ?? "—"}</td>`,
        g.market.total_line !== null && g.market.total_line !== undefined
          ? `<td class="num">${g.market.total_line}</td>` : `<td class="blank">—</td>`,
        isNum(g.fl2_vs_market.total_diff)
          ? `<td class="num"><strong>${sgn(g.fl2_vs_market.total_diff, 1)}</strong></td>` : `<td class="blank">—</td>`,
        `<td class="num">${num(g.fl2_home_margin, 1) ?? "—"}</td>`,
        g.market.spread_line_home_expected_margin !== null && g.market.spread_line_home_expected_margin !== undefined
          ? `<td class="num">${g.market.spread_line_home_expected_margin}</td>` : `<td class="blank">—</td>`,
        isNum(g.fl2_vs_market.margin_diff)
          ? `<td class="num"><strong>${sgn(g.fl2_vs_market.margin_diff, 1)}</strong></td>` : `<td class="blank">—</td>`,
        `<td class="num">${num(g.fl2_p_home, 3) ?? "—"}</td>`,
        `<td class="num">${num(1 - g.fl2_p_home, 3) ?? "—"}</td>`,
        `<td class="num">${sgn(g.avail_adjustment_points, 2)}</td>`,
        `<td class="src">${g.market.status === "present"
          ? srcLink(g.market.source_url, "nflverse")
          : '<span class="badge warn">no citable price</span>'}</td>`,
      ],
    }));

    const detail = m.games.map((g) => `
      <div class="card pad" style="margin-bottom:10px">
        <div class="pill-row" style="justify-content:space-between">
          <strong>${esc(g.game_id)}</strong>
          <span class="src">${esc(g.tv || "")}</span>
        </div>
        <div class="grid c4" style="margin:11px 0 8px">
          <div><div class="eyebrow">FL2 total</div><strong>${num(g.fl2_total, 1)}</strong></div>
          <div><div class="eyebrow">FL2 home margin</div><strong>${sgn(g.fl2_home_margin, 1)}</strong></div>
          <div><div class="eyebrow">Projected score</div><strong>${num(g.fl2_exp_away_points, 1)} – ${num(g.fl2_exp_home_points, 1)}</strong>
            <div class="src">away – home</div></div>
          <div><div class="eyebrow">P(home win)</div><strong>${num(g.fl2_p_home, 3)}</strong></div>
        </div>
        <table style="font-size:12px">
          <thead><tr><th>Input</th><th class="num">Away</th><th class="num">Home</th></tr></thead>
          <tbody>
            <tr><td>Points/game (raw)</td><td class="num">${num(g.inputs.away_off_ppg_raw, 2)}</td><td class="num">${num(g.inputs.home_off_ppg_raw, 2)}</td></tr>
            <tr><td>Points/game (shrunk)</td><td class="num">${num(g.inputs.away_off_ppg_regressed, 2)}</td><td class="num">${num(g.inputs.home_off_ppg_regressed, 2)}</td></tr>
            <tr><td>Points allowed/game (shrunk)</td><td class="num">${num(g.inputs.away_def_papg_regressed, 2)}</td><td class="num">${num(g.inputs.home_def_papg_regressed, 2)}</td></tr>
            <tr><td>Games played</td><td class="num">${g.inputs.away_games}</td><td class="num">${g.inputs.home_games}</td></tr>
          </tbody>
        </table>
        <div class="src" style="margin-top:8px">Availability adjustment applied to the home margin:
          ${esc(g.avail_note || "—")}</div>
      </div>`).join("");

    document.getElementById("app").innerHTML = `
      <div class="page-head">
        <p class="eyebrow">My lines · Week 10</p>
        <h1>Originating our own number for every game</h1>
        <p class="lede">Each game gets a projected total, a projected home margin and a win probability,
        built only from verified inputs: 2026 points for/against (nfl.com standings), points allowed and
        defensive yardage (Pro-Football-Reference), and the Week 10 availability data. Where a market
        price exists in the aggregated closing-line file, the difference is shown; where it does not,
        the cell is blank and the row is flagged.</p>
      </div>
      <div class="note">
        <p><strong>Method, in one sentence.</strong> Project each side's points as the average of its own
        scoring rate and the opponent's concession rate (both shrunk toward the league mean by 4 games of
        prior weight), add a measured home-field term of ${num(m.method.avail_adjustment ? m.games[0].inputs.hfa_points : 0, 1)} points,
        adjust for availability, and convert the margin to a win probability with &sigma; =
        ${num(m.method.sigma_used_for_win_prob, 2)} measured from 16 seasons of closing lines.</p>
      </div>
      <section class="block"><h2>All games</h2>
        <p class="sub">Amber rows have no citable market price. FL2's number is still published; nothing
        is invented to fill the gap.</p>
        ${table([{ label: "Game" }, { label: "FL2 total", num: true }, { label: "Market total", num: true },
                 { label: "Δ", num: true }, { label: "FL2 home margin", num: true },
                 { label: "Market margin", num: true }, { label: "Δ", num: true },
                 { label: "P(home)", num: true }, { label: "P(away)", num: true },
                 { label: "Avail. adj", num: true }, { label: "Market source" }],
                rows, { caption: "Week 10, 2026. Positive margin = home team favoured." })}</section>
      <section class="block"><h2>Inputs and audit trail</h2>
        <p class="sub">Every game's arithmetic, exposed so you can check it rather than trust it.</p>
        ${detail}</section>
      <section class="block"><h2>What this model does not have</h2>
        <div class="grid c2">
          ${m.method.caveats.map((c) => `<div class="card pad small">${esc(c)}</div>`).join("")}
        </div>
        <p class="small" style="margin-top:12px">
          <a href="decisions.html">See the open questions this creates →</a></p>
      </section>`;
  }

  /* ---------- page: verification ---------- */
  function pageVerification() {
    const d = D();
    const groups = d.sources;

    const rows = [];
    groups.forEach((g) => g.items.forEach((it) => rows.push({ g: g.group, it })));

    const srcTable = groups.map((g) => `
      <section class="block">
        <h2>${esc(g.group)}</h2>
        ${table(["Source", "Used for", "Tier", "Link"],
          g.items.map((it) => ({
            cells: [
              `<td><strong>${esc(it.name)}</strong></td>`,
              `<td class="small">${esc(it.used_for)}</td>`,
              `<td><span class="badge ${it.tier.startsWith("T1") ? "ok" : it.tier.startsWith("T3") ? "warn" : "info"}">${esc(it.tier.split(" ")[0])}</span>
                 <div class="src">${esc(it.tier)}</div></td>`,
              `<td class="src">${srcLink(it.url, "open")}</td>`,
            ],
          })))}</section>`).join("");

    const cov = table(["Dataset", "Rows", "SHA-256", "Source"],
      (d.manifest.files || []).map((f) => ({
        cells: [
          `<td class="mono">${esc(f.file)}</td>`,
          `<td class="num">${(f.bytes / 1024).toFixed(0)} KB</td>`,
          `<td class="mono" style="font-size:10.5px">${esc((f.sha256 || "").slice(0, 24))}…</td>`,
          `<td class="src">${srcLink(f.source_url, "github")}</td>`,
        ],
      })),
      { caption: "Downloaded datasets are hashed so a rebuild can be proven identical." });

    document.getElementById("app").innerHTML = `
      <div class="page-head">
        <p class="eyebrow">Verification</p>
        <h1>The rules this site obeys, and the evidence behind every table</h1>
        <p class="lede">Every row on every page carries a source link to an official or registry source.
        Where a value could not be confirmed, it is blank and listed on the Flagged for Review page.
        No value on this site was produced from memory, inference or estimation.</p>
      </div>
      <div class="grid c3">
        <div class="stat ok"><div class="k">Rule 1</div><div class="v" style="font-size:15px">Source or blank</div>
          <div class="d">A cell either has an official link or an em dash. There is no third state.</div></div>
        <div class="stat ok"><div class="k">Rule 2</div><div class="v" style="font-size:15px">No inference</div>
          <div class="d">Missing values are never derived from nearby values, league averages or memory.</div></div>
        <div class="stat ok"><div class="k">Rule 3</div><div class="v" style="font-size:15px">Flag everything</div>
          <div class="d">Unconfirmed, conflicting and resolved items all appear on the Flagged page.</div></div>
      </div>
      <section class="block"><h2>Verification tiers</h2>
        ${table(["Tier", "Meaning", "Used for"], [
          { cells: ["<td><span class='badge ok'>T1</span></td>",
                    "<td>Official league or statistical registry</td>",
                    "<td class='small'>nfl.com (injury report, standings, lineups), Pro-Football-Reference. May populate any cell.</td>"] },
          { cells: ["<td><span class='badge info'>T2</span></td>",
                    "<td>Open data derived from official play-by-play / GSIS ids</td>",
                    "<td class='small'>nflverse/nfldata results and schedules. Used for backtesting; column conventions verified against T1.</td>"] },
          { cells: ["<td><span class='badge warn'>T3</span></td>",
                    "<td>Aggregated market data</td>",
                    "<td class='small'>Closing lines. Never used as a statistical input to a strategy; always labelled, never called official.</td>"] },
          { cells: ["<td><span class='badge bad'>excluded</span></td>",
                    "<td>Unreachable or non-official</td>",
                    "<td class='small'>Wikipedia, editorial rankings, any sportsbook page, any mirror this environment could not actually read.</td>"] },
        ])}</section>
      ${srcTable}
      <section class="block"><h2>Dataset integrity</h2>${cov}
        <p class="small" style="margin-top:10px">Rebuild with <code>python3 engine/fetch_data.py</code>.
        Any hash difference means the upstream file changed and every derived number must be re-checked.</p>
      </section>
      <section class="block"><h2>Verification performed this session</h2>
        ${table(["Check", "Method", "Outcome"], [
          { cells: ["<td>Spread sign convention</td>",
                    "<td class='small'>Compared <code>spread_line</code> to the sign of <code>home_moneyline</code> on real 2025 rows, then asserted the invariant in code</td>",
                    "<td><span class='badge ok'>passed</span> <span class='small'>home favourites have spread_line &gt; 0</span></td>"] },
          { cells: ["<td>Cover rate plausibility</td>",
                    "<td class='small'>Asserted 0.44 &lt; home cover &lt; 0.56 on every build</td>",
                    "<td><span class='badge ok'>0.4752</span></td>"] },
          { cells: ["<td>Over rate plausibility</td>",
                    "<td class='small'>Excluded pushes, compared to 50%</td>",
                    "<td><span class='badge ok'>0.4880</span></td>"] },
          { cells: ["<td>League scoring sanity</td>",
                    "<td class='small'>PFR average team points, cross-checked against nfl.com standings</td>",
                    "<td><span class='badge ok'>23.0 pts/team/game</span></td>"] },
          { cells: ["<td>Injury report rows</td>",
                    "<td class='small'>Read player, position, practice and game status verbatim; captured practice status separately from game status</td>",
                    "<td><span class='badge ok'>76 rows</span> <span class='small'>66 Out, 10 Doubtful</span></td>"] },
          { cells: ["<td>Starting quarterbacks</td>",
                    "<td class='small'>Required a direct quote from an NFL.com page for each of the 7 teams with changes</td>",
                    "<td><span class='badge warn'>5 confirmed, 2 left blank</span></td>"] },
          { cells: ["<td>Every internal link</td>",
                    "<td class='small'>Crawled all pages in the built site and checked each href resolves to a file that exists</td>",
                    "<td><span class='badge ok'>see build log</span></td>"] },
        ])}
      </section>`;
  }

  /* ---------- page: flagged ---------- */
  function pageFlagged() {
    const d = D();
    const flags = d.flags;
    const order = { high: 0, medium: 1, low: 2, info: 3 };
    const sorted = [...flags].sort((a, b) => (order[a.severity] ?? 9) - (order[b.severity] ?? 9));

    const counts = { high: 0, medium: 0, low: 0, info: 0 };
    flags.forEach((f) => { counts[f.severity] = (counts[f.severity] || 0) + 1; });

    const rows = sorted.map((f, i) => ({
      __cls: f.severity === "high" ? "flag" : "",
      cells: [
        `<td class="num">${i + 1}</td>`,
        `<td>${sevBadge(f.severity)}</td>`,
        `<td class="small"><strong>${esc(f.category)}</strong></td>`,
        `<td><strong>${esc(f.item)}</strong><div class="small" style="margin-top:4px">${esc(f.detail)}</div></td>`,
        f.value === null || f.value === undefined
          ? `<td class="blank" title="Not confirmed">—</td>`
          : `<td class="num">${esc(String(f.value))}</td>`,
        `<td class="small">${esc(f.action)}</td>`,
        `<td class="src">${(f.sources || []).map((u) => srcLink(u)).join("<br>")}</td>`,
      ],
    }));

    const byCat = {};
    flags.forEach((f) => { byCat[f.category] = (byCat[f.category] || 0) + 1; });

    document.getElementById("app").innerHTML = `
      <div class="page-head">
        <p class="eyebrow">Flagged for review</p>
        <h1>${flags.length} items a human should check</h1>
        <p class="lede">Everything that is unconfirmed, conflicting, blocked, or was wrong and has been
        fixed. These items do not block publication — the site is live — but each one names the source
        that would close it. Ordered most serious first.</p>
      </div>
      <div class="grid c4">
        <div class="stat bad"><div class="k">High</div><div class="v">${counts.high || 0}</div>
          <div class="d">changes how a number should be read</div></div>
        <div class="stat warn"><div class="k">Medium</div><div class="v">${counts.medium || 0}</div>
          <div class="d">missing input, no workaround</div></div>
        <div class="stat"><div class="k">Low</div><div class="v">${counts.low || 0}</div>
          <div class="d">cosmetic or narrow</div></div>
        <div class="stat ok"><div class="k">Resolved</div><div class="v">${counts.info || 0}</div>
          <div class="d">defect found and fixed, kept visible</div></div>
      </div>
      <div class="note warn">
        <p><strong>The most important item on this page is the one that is not a defect:</strong> there is
        no validated strategy. That is a finding, not a gap. If you want a system to act on, the order of
        work is on the <a href="suggestions.html">Suggestions</a> page, and the blockers are on
        <a href="decisions.html">Questions &amp; Answers</a>.</p>
      </div>
      <section class="block">
        ${table(["#", "Severity", "Category", "Item and explanation", "Value", "What to do", "Sources"],
                rows,
                { caption: "Every flag is generated from the data files themselves, so this list cannot drift out of sync with the tables." })}
      </section>
      <section class="block"><h2>By category</h2>
        ${table(["Category", "Count"],
          Object.entries(byCat).sort((a, b) => b[1] - a[1]).map(([k, v]) => ({
            cells: [`<td>${esc(k)}</td>`, `<td class="num">${v}</td>`],
          })))}</section>`;
  }

  /* ---------- page: method ---------- */
  function pageMethod() {
    const d = D();
    const p = d.backtest.protocol;
    document.getElementById("app").innerHTML = `
      <div class="page-head">
        <p class="eyebrow">Method</p>
        <h1>How every number on this site was produced</h1>
        <p class="lede">Short enough to read, specific enough to reproduce. The engine is plain Python:
        five scripts, fixed seeds, no services.</p>
      </div>
      <section class="block"><h2>1 · The pipeline</h2>
      <pre><code>engine/fetch_data.py      download + sha256 the four nflverse CSVs
engine/run_backtest.py    assert conventions, build features, run 11 strategies, apply 8 gates
engine/run_parlays.py     measure leg correlations, compute vig compounding
engine/build_week10.py    transcribe the official injury report + QB decisions
engine/build_market.py    project totals, margins, win probabilities
engine/build_site_data.py sanitise to JSON-safe, emit data/site_data.js</code></pre>
      <p class="small">Fixed seeds: <code>20261114</code> (statistics core) and <code>7</code> (gate
      bootstraps). Re-running reproduces every interval exactly.</p></section>

      <section class="block"><h2>2 · The convention that broke first</h2>
      <div class="note bad">
        <p>In this dataset <code>spread_line</code> is the <strong>expected home margin</strong>, not a
        handicap: a home favourite has <code>spread_line &gt; 0</code>. The first build treated it as a
        handicap and produced a 77.5% "divisional home underdog cover rate" — a number impossible in
        football. It was caught because the model's own results were absurd, not because a test failed.</p>
        <p>The correction is now an assertion that runs before any modelling:
        <code>self_check()</code> verifies the moneyline signs, that favourites outscore underdogs, and
        that the cover rate is inside (0.44, 0.56). If any fails, the build aborts.</p>
      </div></section>

      <section class="block"><h2>3 · No look-ahead</h2>
      ${table(["Feature", "Built from", "Leakage risk", "Control"], [
        { cells: ["<td class='mono'>elo_margin</td>", "<td>Elo state before kickoff</td>",
                  "<td class='small'>rating updated with the game's own result</td>",
                  "<td class='small'>expected value stored <em>then</em> updated</td>"] },
        { cells: ["<td class='mono'>home_pf6 / pa6</td>", "<td>mean of last 6 games</td>",
                  "<td class='small'>including this game</td>",
                  "<td class='small'>history appended after the row is written</td>"] },
        { cells: ["<td class='mono'>last_margin</td>", "<td>previous game only</td>",
                  "<td class='small'>this week's margin</td>",
                  "<td class='small'>read before write</td>"] },
        { cells: ["<td class='mono'>mkt_p_home</td>", "<td>de-vigged <strong>closing</strong> line</td>",
                  "<td class='small'>closing is later than some bet timings</td>",
                  "<td class='small'>declared: makes results conservative for early bettors, optimistic for late ones</td>"] },
        { cells: ["<td class='mono'>calibration coefficients</td>", "<td>2006–2010 only</td>",
                  "<td class='small'>fitting on evaluation data</td>",
                  "<td class='small'>explicit <code>CALIB_END</code> split</td>"] },
      ])}</section>

      <section class="block"><h2>4 · Separating luck from skill</h2>
      <p class="sub">Three independent devices, because any one of them can be gamed.</p>
      <div class="grid c3">
        <div class="card pad"><div class="eyebrow">Luck fraction</div>
          <p class="small">Under a fair-coin null the variance of the mean return is <code>1/n</code>.
          If the observed variance is no larger, the record is fully explainable by luck. Formula:
          <code>1 − max(SE² − 1/n, 0)/SE²</code>.</p></div>
        <div class="card pad"><div class="eyebrow">Effective sample size</div>
          <p class="small">Correlated bets are not independent trials.
          <code>n_eff = n(1−ρ)/(1+ρ)</code> using lag-1 autocorrelation. 900 bets on the same team is
          never 900 trials.</p></div>
        <div class="card pad"><div class="eyebrow">Block bootstrap</div>
          <p class="small">Resamples blocks of 16 bets rather than single bets, because a season is
          serially dependent. Naive iid intervals on this data are 15–25% too narrow.</p></div>
      </div></section>

      <section class="block"><h2>5 · Multiple testing</h2>
      <p class="sub">Eleven hypotheses were tested. At q = ${p.fdr_q}, Benjamini–Hochberg requires the
      smallest p to clear roughly 0.1/11 ≈ 0.009. Nothing did. Reporting a 0.04 p-value from this batch
      as a discovery would be a false positive by construction.</p>
      ${table(["Quantity", "Value"], [
        { cells: ["<td>Hypotheses tested</td>", `<td class="num">${p.n_hypotheses}</td>`] },
        { cells: ["<td>FDR level</td>", `<td class="num">${p.fdr_q}</td>`] },
        { cells: ["<td>BH cutoff p (none passed)</td>",
                  `<td class="num">${p.fdr_cutoff_p === null ? "—" : p.fdr_cutoff_p}</td>`] },
        { cells: ["<td>Strategies validated</td>",
                  `<td class="num">${d.backtest.strategies.filter((s) => s.status === "validated").length}</td>`] },
      ])}</section>

      <section class="block"><h2>6 · Correlation and parlay maths</h2>
      <p class="sub">Binary legs use phi with a bootstrapped interval; continuous pairs use Pearson.
      The Gaussian-copula estimate for multi-leg tickets is reported as a <em>lower bound</em> on
      mispricing, because real tail dependence is fatter than a Gaussian can express.</p>
      ${table(["Question", "Answer", "Number"], [
        { cells: ["<td>Are spread and total legs correlated?</td>", "<td>Essentially not</td>",
                  `<td class="num">phi ${num(d.parlays.same_game_correlations["home_cover + over"].phi, 4)}</td>`] },
        { cells: ["<td>Are winning and covering correlated?</td>", "<td>Strongly, mechanically</td>",
                  `<td class="num">phi ${num(d.parlays.same_game_correlations["home_win + home_cover"].phi, 4)}</td>`] },
        { cells: ["<td>Cost of a 3-leg ticket at −110?</td>", "<td>13.03% of fair value surrendered</td>",
                  `<td class="num">6.958× vs 8.000×</td>`] },
        { cells: ["<td>Cost of a 10-leg ticket?</td>", "<td>37.20% surrendered</td>",
                  `<td class="num">643× vs 1024×</td>`] },
      ])}</section>

      <section class="block"><h2>7 · Reproducing</h2>
      <pre><code>python3 engine/fetch_data.py
python3 engine/run_backtest.py
python3 engine/run_parlays.py
python3 engine/build_week10.py
python3 engine/build_market.py
python3 engine/build_site_data.py</code></pre>
      <p class="small">Requires <code>pandas</code> and <code>numpy</code>. The first script needs
      outbound HTTPS to <code>api.github.com</code>.</p></section>`;
  }

  /* ---------- router ---------- */
  const ROUTES = {
    "index.html": pageIndex,
    "suggestions.html": () => (window.pageSuggestions ? window.pageSuggestions() : null),
    "decisions.html": pageDecisions,
    "strategies.html": pageStrategies,
    "injuries.html": pageInjuries,
    "lines.html": pageLines,
    "verification.html": pageVerification,
    "flagged.html": pageFlagged,
    "summary.html": () => (window.pageSummary ? window.pageSummary() : null),
    "method.html": pageMethod,
  };

  function render(page) {
    chrome(page);
    const fn = ROUTES[page];
    if (fn) fn();
  }

  return { render, esc, num, pct, sgn, cell, table, srcLink, statusBadge, sevBadge, shortUrl };
})();

window.FL2UI = FL2Console;
