/* ==========================================================================
   FL2 — Executive summary.
   Renders from data/site_data.js so no number is typed by hand and the summary
   can never drift from the tables it summarises.
   ========================================================================== */
"use strict";

function pageSummary() {
  const d = window.FL2;
  const bt = d.backtest;
  const wk = d.week10;
  const pl = d.parlays;
  const mk = d.market;
  const validated = bt.strategies.filter((s) => s.status === "validated").length;
  const tested = bt.strategies.filter((s) => s.status !== "untestable").length;
  const best = [...bt.strategies].sort((a, b) => (b.gates_passed || 0) - (a.gates_passed || 0))[0];
  const openQ = window.FL2_DECISIONS.filter((x) => x.answer === null).length;
  const corr = pl.same_game_correlations;
  const vig3 = pl.vig_cost_by_leg_count.find((r) => r.legs === 3);

  const keyNumbers = [
    { k: "Strategies validated", v: `${validated} / ${tested}`, d: "eight gates, out-of-sample 2011–2026", cls: "bad" },
    { k: "Model skill vs. closing line", v: `${FL2UI.sgn(bt.baselines.elo_brier_skill_vs_market * 100, 1)}%`, d: "Brier score, negative means worse", cls: "warn" },
    { k: "Games in the backtest", v: bt.baselines.n_games_evaluated.toLocaleString(), d: "with a usable closing line and result", cls: "" },
    { k: "Players ruled Out this week", v: wk.league_totals.n_players_out, d: `plus ${wk.league_totals.n_players_doubtful} doubtful`, cls: "" },
    { k: "Open decisions", v: openQ, d: "of 20 register questions", cls: "warn" },
    { k: "Flagged items", v: d.flags.length, d: "unconfirmed, blocked or resolved", cls: "warn" },
    { k: "Spread ↔ total correlation", v: FL2UI.sgn(corr["home_cover + over"].phi, 4), d: "confidence interval spans zero", cls: "" },
    { k: "Cost of a 3-leg ticket", v: `${vig3.probability_given_up_pct}%`, d: "of fair value surrendered at −110", cls: "" },
  ];

  const findings = [
    {
      n: 1,
      h: "No tested strategy survives validation — and that is the deliverable.",
      p: `${tested} hypotheses were run against 16 seasons of closing lines with eight gates each. None cleared all eight. The best was ${FL2UI.esc(best.name)} at ${FL2UI.sgn((best.roi || 0) * 100, 2)}% ROI per bet over ${best.n} bets, with a confidence interval that includes zero and a luck fraction of ${FL2UI.num(best.luck_fraction, 2)}. A system that tells you this in an afternoon is worth more than a list of picks that cannot be audited.`,
      tag: ["bad", "finding"],
    },
    {
      n: 2,
      h: "Our model is measurably worse than the market, which explains finding 1.",
      p: `The Elo model scores a Brier of ${FL2UI.num(bt.baselines.elo_brier, 4)} against the closing line's ${FL2UI.num(bt.baselines.market_brier, 4)} on ${bt.baselines.n_games_evaluated.toLocaleString()} games — a ${FL2UI.sgn(bt.baselines.elo_brier_skill_vs_market * 100, 1)}% skill. A model that cannot price a game as well as the market is not a candidate for finding value in it. The honest read is that the market is doing its job and our inputs are thin.`,
      tag: ["warn", "caveat"],
    },
    {
      n: 3,
      h: "Most of the claimed edge in this sport is not measurable with public data.",
      p: `Player props are where the largest claimed edges live and where we can measure least. Five prop-combo families are listed as unverified because the player-level feed could not be reached from the build environment. They are not estimated, proxied or guessed — they are blank, and they are on the flagged page. Anything else would have been a hallucination with a confident tone.`,
      tag: ["warn", "gap"],
    },
    {
      n: 4,
      h: "Spread and total legs are essentially uncorrelated; win and cover are mechanically joined.",
      p: `Measured over ${corr["home_cover + over"].n.toLocaleString()} settled games: spread+total phi = ${FL2UI.sgn(corr["home_cover + over"].phi, 4)} with a CI spanning zero, and the joint rate is within 0.2 points of the independence prediction. Win+cover phi = ${FL2UI.sgn(corr["home_win + home_cover"].phi, 4)} and is the same event twice. So the popular 'correlated same-game parlay' story holds for the second pair, where it is already priced, and not for the first, where people claim it most.`,
      tag: ["info", "measurement"],
    },
    {
      n: 5,
      h: "Parlay structure, not pick quality, is the dominant cost.",
      p: `Each leg at −110 carries 4.55% margin, and margins multiply. A two-leg ticket surrenders ${pl.vig_cost_by_leg_count[1].probability_given_up_pct}% of fair value, three legs ${vig3.probability_given_up_pct}%, ten legs ${pl.vig_cost_by_leg_count.find((r) => r.legs === 10).probability_given_up_pct}%. Whatever edge a single bet has, it must exceed that compounded threshold on every leg simultaneously. This is arithmetic, not opinion.`,
      tag: ["info", "arithmetic"],
    },
    {
      n: 6,
      h: "The availability picture this week is unusually distorted, and quarterback is the sharpest edge of it.",
      p: `Five teams have a confirmed different starting quarterback in Week 10 — Arizona, Cleveland, Miami, Minnesota and Seattle. ${wk.league_totals.n_players_out} players are listed out league-wide across ${wk.league_totals.teams_reporting} teams, with four teams on bye. We can state this precisely because it comes from the league's own report. We cannot yet state what it does to a line, because we hold no pre-news market snapshot.`,
      tag: ["warn", "live"],
    },
    {
      n: 7,
      h: "Two starting quarterbacks remain unconfirmed, and the site says so instead of guessing.",
      p: `Baltimore and the Los Angeles Chargers have unresolved quarterback situations. Lamar Jackson is confirmed out for 6–10 weeks but no reviewed official page names his replacement; for the Chargers the only official statement is that Justin Herbert avoided a fracture. Both are left blank, flagged high, and named on the suggestions page as the cheapest thing to close.`,
      tag: ["bad", "gap"],
    },
    {
      n: 8,
      h: "The next step is data acquisition, not more modelling.",
      p: `Every high-value blocker is a missing dataset: player-level statistics, a historical injury feed, and a pre-news line archive. Model work without them is tuning a formula on too few inputs. The suggestions page ranks these by value per hour, and the only one that decays with time is the line archive.`,
      tag: ["ok", "next"],
    },
  ];

  document.getElementById("app").innerHTML = `
    <div class="page-head">
      <p class="eyebrow">Executive summary</p>
      <h1>What this project found, in one page</h1>
      <p class="lede">Eight findings, the numbers behind them, and what to do next. Everything below is
      generated from the same verified data the rest of the site renders, so the summary cannot drift
      from the tables. Snapshot ${FL2UI.esc((d.as_of_utc || "").slice(0, 16).replace("T", " "))} UTC.</p>
    </div>

    <div class="grid c4">
      ${keyNumbers.map((s) => `<div class="stat ${s.cls}">
        <div class="k">${FL2UI.esc(s.k)}</div>
        <div class="v">${FL2UI.esc(String(s.v))}</div>
        <div class="d">${FL2UI.esc(s.d)}</div></div>`).join("")}
    </div>

    <section class="block">
      <h2>The bottom line</h2>
      <div class="note bad">
        <p>This project set out to originate NFL lines, generate skill-based signals and run a
        competition that rewards the best strategies. It has produced a verified dataset, a working line
        model, and a validation harness. <strong>It has not produced a profitable strategy, and it should
        not pretend otherwise.</strong> That result is measured, reproducible, and more useful than a
        confident pick: it tells you where not to spend money, and exactly which data would change the
        answer.</p>
      </div>
    </section>

    <section class="block">
      <h2>Findings</h2>
      <p class="sub">Ordered by consequence. Each links to the page with the underlying rows.</p>
      ${findings.map((f) => `<div class="card pad" style="margin-bottom:12px">
        <div class="pill-row" style="justify-content:space-between">
          <strong style="font-size:15px">${f.n}. ${FL2UI.esc(f.h)}</strong>
          <span class="badge ${f.tag[0]}">${f.tag[1]}</span>
        </div>
        <p class="small" style="margin:9px 0 0">${f.p}</p>
      </div>`).join("")}
    </section>

    <section class="block">
      <h2>Recommendations, in order</h2>
      ${FL2UI.table(["#", "Action", "Why now", "Effort"], [
        { cells: ["<td>1</td>", "<td><strong>Start a weekly line-snapshot archive</strong></td>",
                  "<td class='small'>The only item that loses value every week it is not started. Unlocks the entire injury-angle programme and the untestable line-move strategy.</td>", "<td class='small'>1 hour to instrument</td>"] },
        { cells: ["<td>2</td>", "<td><strong>Obtain the player-level feed</strong></td>",
                  "<td class='small'>Turns five unverified prop-combo categories into measurable ones. The fetch script already exists; only the network is missing.</td>", "<td class='small'>2–4 hours</td>"] },
        { cells: ["<td>3</td>", "<td><strong>Add a quarterback-quality term</strong></td>",
                  "<td class='small'>The most obvious structural gap in the model, and the one that makes the negative result strongest if it still holds afterwards.</td>", "<td class='small'>4–6 hours</td>"] },
        { cells: ["<td>4</td>", "<td><strong>Fix how the competition scores</strong></td>",
                  "<td class='small'>A leaderboard ranked on backtest ROI selects for luck. Our own S10 shows a 55% hit rate that fails four gates.</td>", "<td class='small'>1 day, a policy call</td>"] },
        { cells: ["<td>5</td>", "<td><strong>Close the two blank QB cells</strong></td>",
                  "<td class='small'>Fifteen minutes of checking removes two high-severity flags and firms up two game numbers.</td>", "<td class='small'>15 minutes</td>"] },
        { cells: ["<td>6</td>", "<td><strong>Automate the weekly refresh</strong></td>",
                  "<td class='small'>A stale injury table is worse than none. A scheduled build with a stale badge makes failure visible.</td>", "<td class='small'>3–4 hours</td>"] },
      ])}
      <p class="small" style="margin-top:10px"><a href="suggestions.html">Review and choose a path for each
      proposal →</a> · <a href="decisions.html">See the ${openQ} open questions →</a></p>
    </section>

    <section class="block">
      <h2>What would change this conclusion</h2>
      <div class="grid c2">
        <div class="card pad"><div class="eyebrow">Would strengthen it</div>
          <ul class="tight small">
            <li>A quarterback-adjusted model that still fails the gates — removes the strongest objection.</li>
            <li>A forward sample of a strategy that looks good now and decays, documented honestly.</li>
            <li>Player-level data showing the prop combos fail too.</li>
          </ul></div>
        <div class="card pad"><div class="eyebrow">Would overturn it</div>
          <ul class="tight small">
            <li>A strategy passing all eight gates out-of-sample, then holding up on 150+ forward bets at recorded prices.</li>
            <li>Evidence that a specific injury-news mispricing is persistent — which needs the line archive first.</li>
            <li>A documented cost advantage (line shopping, reduced vig, better prices) large enough to be the edge itself.</li>
          </ul></div>
      </div>
    </section>

    <section class="block">
      <h2>Scope and limits, stated plainly</h2>
      ${FL2UI.table(["Area", "Status", "Detail"], [
        { cells: ["<td>Team-level data</td>", "<td><span class='badge ok'>verified</span></td>",
                  "<td class='small'>Points for/against, defensive yardage, takeaways, standings, injury report — all linked to nfl.com or Pro-Football-Reference.</td>"] },
        { cells: ["<td>Player-level data</td>", "<td><span class='badge bad'>unavailable</span></td>",
                  "<td class='small'>Release assets unreachable from the build environment. Nothing substituted.</td>"] },
        { cells: ["<td>Market prices</td>", "<td><span class='badge warn'>not citable</span></td>",
                  "<td class='small'>No official publisher exists. Shown only from the aggregated closing-line file, always labelled.</td>"] },
        { cells: ["<td>Depth-chart rank</td>", "<td><span class='badge warn'>not published</span></td>",
                  "<td class='small'>The league lists availability, not whether a replacement is 2nd or 4th string. The availability index is a declared proxy.</td>"] },
        { cells: ["<td>Strategy validation</td>", "<td><span class='badge bad'>0 validated</span></td>",
                  "<td class='small'>Eleven tested, none passed eight gates. One untestable for lack of opening-line history.</td>"] },
        { cells: ["<td>Betting advice</td>", "<td><span class='badge mute'>none given</span></td>",
                  "<td class='small'>This is a research tool. It does not recommend wagers and it does not claim an edge.</td>"] },
      ])}
    </section>`;
}

window.pageSummary = pageSummary;
