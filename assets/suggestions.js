/* ==========================================================================
   FL2 — Suggestions page.
   The user asked for a dedicated section where proposals can be reviewed and
   the best path chosen before any change is implemented. So each suggestion is
   a decision with real options, a recommendation grounded in evidence from this
   repo, and a reviewer control (accept / reject / defer) that persists locally.
   ========================================================================== */
"use strict";

const SUGGESTIONS = [
  {
    id: "S-01",
    title: "Get the player-level feed before writing another strategy",
    area: "Data",
    effort: "2–4 hours + an environment with unrestricted HTTPS",
    impact: "Very high",
    confidence: "high",
    unlocks: ["D02", "player props", "snap counts", "depth charts", "target share"],
    problem: "Five of the eleven ideas we would most like to test — every player-prop combo — are not testable at all, because nflverse publishes player_stats and snap_counts only as GitHub release assets, which redirect to a host this build environment cannot reach. Nothing was substituted, so those combos sit at 'unverified'.",
    recommendation:
      "Do this first. It is the only item that turns a whole category from 'unverifiable' into 'measurable', and every other data suggestion depends on it.",
    options: [
      { id: "a", label: "Re-run the engine where release assets are reachable", note: "Cheapest. engine/fetch_data.py already exists; it only needs a network without the allow-list.", rec: true },
      { id: "b", label: "Buy a licensed data feed (Sportradar, etc.)", note: "Costs money but adds official per-player and official odds endpoints, closing D03 as well." },
      { id: "c", label: "Drop player props from scope permanently", note: "Honest and cheap. Keeps the site strictly team-level, which is where all verified data currently lives." },
      { id: "d", label: "Scrape box scores page by page", note: "Not recommended: manual, unauditable, and would breach the 'no hallucination' rule the moment one row is mistyped." },
    ],
    evidence: [
      { label: "nflverse release assets (unreachable)", url: "https://github.com/nflverse/nflverse-data/releases" },
      { label: "Decision D02", url: "decisions.html#D02" },
      { label: "Flagged: release assets unreachable", url: "flagged.html" },
    ],
  },
  {
    id: "S-02",
    title: "Build a weekly line-snapshot archive starting now",
    area: "Data",
    effort: "1 hour to instrument, then automatic",
    impact: "Very high",
    confidence: "high",
    unlocks: ["D10", "the entire injury-angle programme", "the line-move strategy (S11)"],
    problem: "We can measure what our own number says. We cannot measure what the market did when news broke, because we hold only a closing line. That makes 'does injury news move the line, and is the move too small or too large?' untestable — and it is the single most important question for an injury-focused model. S11 could not be tested at all for the same reason: opening lines exist for 2021 only.",
    recommendation:
      "Instrument a scraper now and let it accumulate. This is the only suggestion whose value comes purely from starting early — every week of delay is a week of data you can never recover. Store timestamp, game, book, line and the injury report as-of that moment.",
    options: [
      { id: "a", label: "Weekly job capturing open + midday + close, with timestamps", note: "Recommended. Even a single book at three times a week is enough to measure drift.", rec: true },
      { id: "b", label: "Snapshot only once, at a fixed time each week", note: "Cheap, but cannot distinguish 'the line moved' from 'the line was always there'." },
      { id: "c", label: "Wait for a vendor that sells historical line movement", note: "Defers the question and rents the answer. Worth pricing before writing your own." },
    ],
    evidence: [
      { label: "initial_lines.csv (2021 only)", url: "https://github.com/nflverse/nfldata/blob/master/data/initial_lines.csv" },
      { label: "Decision D10", url: "decisions.html" },
      { label: "S11 deemed untestable", url: "strategies.html#S11_line_move_fade" },
    ],
  },
  {
    id: "S-03",
    title: "Add a quarterback-quality term — the one model upgrade with a clear payoff",
    area: "Model",
    effort: "4–6 hours",
    impact: "High",
    confidence: "medium",
    unlocks: ["D05", "a fairer test of S1"],
    problem: "Our model is 8.1% worse than the closing line on Brier score. It has no idea who is playing quarterback. That is a structural omission, not a tuning problem: a team-level points-per-game average cannot distinguish a starter from a backup, which is exactly the situation facing five teams this week (ARI, CLE, MIA, MIN, SEA).",
    recommendation:
      "Add a per-QB adjustment derived from that quarterback's own starts, shrunk heavily toward the team rate. Then re-run the same eleven strategies unchanged. If the gates still fail, the negative result becomes much stronger evidence, because the most obvious objection has been removed.",
    options: [
      { id: "a", label: "Per-QB points-above-replacement, shrunk", note: "Recommended. Most defensible: it uses only starts, not reputation.", rec: true },
      { id: "b", label: "Use a published QBR/EPA feed", note: "Faster, but introduces a third-party metric you then have to verify — and its methodology is not auditable from here." },
      { id: "c", label: "Leave the model as-is and stop claiming it is close", note: "Accept that the negative result stands. Cheapest, and honest." },
    ],
    evidence: [
      { label: "Model vs market Brier", url: "strategies.html" },
      { label: "Decision D05", url: "decisions.html" },
      { label: "Five QB changes this week", url: "injuries.html" },
    ],
  },
  {
    id: "S-04",
    title: "Replace the availability index with a measured effect, or label it louder",
    area: "Model",
    effort: "1 hour (relabel) or 1–2 days (measure)",
    impact: "High",
    confidence: "high",
    unlocks: ["D09", "trust in the lines page"],
    problem: "The depletion index multiplies position weights (QB = 5.0, CB = 2.4, …) by four, subtracts from 100, and converts a 100-point gap into 3 points of margin. Every one of those constants is arbitrary. It is declared as arbitrary on the page, but a number that looks like a measurement tends to be read as one.",
    recommendation:
      "Either measure it or shrink it. Measuring needs the historical injury feed plus historical lines — blocked on S-01/S-02. Until then, reduce the margin adjustment to near zero and present the index purely as a descriptive ordering. A model should not silently carry a parameter nobody can defend.",
    options: [
      { id: "a", label: "Regress historical margin residuals on availability once data exists", note: "The real fix. Blocked on S-01 and S-02.", rec: true },
      { id: "b", label: "Set the margin adjustment to 0 and keep the index descriptive only", note: "Immediate, honest, loses nothing we can actually justify." },
      { id: "c", label: "Leave as-is", note: "Defensible only because the constant is declared — but it is still a guess inside a projection." },
    ],
    evidence: [
      { label: "Availability method", url: "lines.html" },
      { label: "Decision D09", url: "decisions.html" },
      { label: "Flagged: depth chart not verified", url: "flagged.html" },
    ],
  },
  {
    id: "S-05",
    title: "Make the leaderboard reward forward performance, not backtests",
    area: "Competition",
    effort: "1 day",
    impact: "High",
    confidence: "medium",
    unlocks: ["D12", "D13", "a competition that cannot be won by luck"],
    problem: "The brief asks for a leaderboard competition with rewards for top strategies. A leaderboard scored on backtest ROI selects for luck by construction — our own S10 demonstrates it: 55.1% over 156 bets and +7.4% ROI, which fails four gates. If that had been the scoring rule, S10 would be top of the table.",
    recommendation:
      "Score on gates passed, then on the lower confidence bound of forward ROI, with a minimum forward sample before a strategy is ranked at all. Keep backtest numbers visible but never ranked. This is a policy decision only you can make — it is suggested, not applied.",
    options: [
      { id: "a", label: "Forward-only scoring with a minimum sample gate", note: "Recommended. Only rule that cannot be gamed by re-running variants.", rec: true },
      { id: "b", label: "Blend: 50% backtest gates, 50% forward record", note: "Rewards effort early, still resistant to luck once samples grow." },
      { id: "c", label: "Raw ROI leaderboard", note: "Simple and motivating, but it will crown noise. Expect the top of the table to be small-sample." },
    ],
    evidence: [
      { label: "S10 — a 55% hit rate that is noise", url: "strategies.html" },
      { label: "Decision D12", url: "decisions.html" },
      { label: "Gate definitions", url: "method.html" },
    ],
  },
  {
    id: "S-06",
    title: "Pick a fixed hypothesis budget per cycle and publish it",
    area: "Competition",
    effort: "30 minutes",
    impact: "Medium",
    confidence: "high",
    unlocks: ["D14"],
    problem: "Every additional hypothesis lowers the bar for a false discovery. With eleven tried, the Benjamini–Hochberg threshold is about p ≈ 0.009. Adding ideas without counting them makes the whole leaderboard less meaningful, not more.",
    recommendation:
      "Cap tests per cycle (say 5), register them before running, and print the count beside every p-value on the site. This is already implemented in the data — it just needs to become a rule.",
    options: [
      { id: "a", label: "Fixed budget of 5 per cycle, pre-registered", note: "Recommended. Forces prioritisation.", rec: true },
      { id: "b", label: "Unlimited testing with a rising FDR penalty", note: "More permissive; still honest as long as the count is published." },
      { id: "c", label: "No cap", note: "Guarantees eventual false positives. Not recommended." },
    ],
    evidence: [
      { label: "Multiple-testing section", url: "method.html" },
      { label: "Decision D14", url: "decisions.html" },
    ],
  },
  {
    id: "S-07",
    title: "Separate 'could not test' from 'tested and failed' throughout the UI",
    area: "Presentation",
    effort: "2 hours",
    impact: "Medium",
    confidence: "high",
    unlocks: ["clearer reading of every negative result"],
    problem: "Both states currently appear as a red-ish outcome, which conflates two very different things. S11 was never run — we lack the data. S1 ran on 2,086 bets and failed. Treating them alike invites either false confidence ('everything fails') or false hope ('maybe the untested one works').",
    recommendation:
      "Give untestable its own grey state, its own wording, and a link to the specific blocker. This is largely done on the Strategy Lab; the request is to make it a standing rule so future additions do not blur it again.",
    options: [
      { id: "a", label: "Three-state model: validated / failed / untested", note: "Recommended. Already implemented; formalise it.", rec: true },
      { id: "b", label: "Hide untestable strategies entirely", note: "Cleaner table, but hides the most actionable information — what to go and get." },
    ],
    evidence: [
      { label: "Strategy Lab statuses", url: "strategies.html" },
      { label: "Decision D06", url: "decisions.html" },
    ],
  },
  {
    id: "S-08",
    title: "Automate the weekly refresh and fail the build when it goes stale",
    area: "Operations",
    effort: "3–4 hours",
    impact: "Medium",
    confidence: "high",
    unlocks: ["D15"],
    problem: "This snapshot is accurate as of 2026-11-14 and will be wrong within hours. An injury table that looks authoritative but is two days old is worse than no table, because a reader will act on it.",
    recommendation:
      "Schedule the pipeline weekly (and on game days), stamp every data file with an as_of time, and make the site refuse to render a table whose timestamp is more than 24 hours old without an explicit stale badge.",
    options: [
      { id: "a", label: "GitHub Actions on a schedule + stale badge", note: "Recommended. Free, visible, and the badge makes failure obvious.", rec: true },
      { id: "b", label: "Manual refresh each week", note: "Fine while a human is watching; silently wrong the first week they are not." },
      { id: "c", label: "Drop the live-dataset framing", note: "Present it as a dated research snapshot only. Cheapest and fully honest." },
    ],
    evidence: [
      { label: "Decision D15", url: "decisions.html" },
      { label: "Decision D16 (Pages races)", url: "decisions.html" },
    ],
  },
  {
    id: "S-09",
    title: "Close the two blank starting-quarterback cells before trusting those games",
    area: "Data",
    effort: "15 minutes",
    impact: "Medium",
    confidence: "high",
    unlocks: ["D11", "D19"],
    problem: "Baltimore and the LA Chargers both have an unresolved quarterback situation in the data. Lamar Jackson is confirmed out for 6–10 weeks, but no reviewed page names his replacement; for the Chargers the only official line is that Justin Herbert avoided a fracture. Those are the two largest unknowns on the Lines page, and quarterback is the biggest single input to a game number.",
    recommendation:
      "Confirm both from the teams' own official sites, then update data/week10_lineups.json. This is the cheapest item on the page and removes two high-severity flags.",
    options: [
      { id: "a", label: "Check ravens.com and chargers.com directly", note: "Recommended. Official team sites are a T2 source and are not in the sandbox allow-list, so a human must do this.", rec: true },
      { id: "b", label: "Wait for the league's inactive list 90 minutes before kickoff", note: "Definitive, but too late for any pre-game analysis." },
      { id: "c", label: "Leave blank", note: "Acceptable — blank is honest. The row stays flagged." },
    ],
    evidence: [
      { label: "QB availability table", url: "injuries.html" },
      { label: "Official Friday roundup", url: "https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-friday-nov-13" },
    ],
  },
  {
    id: "S-10",
    title: "Publish the negative result prominently — it is the asset",
    area: "Presentation",
    effort: "Already done; keep it",
    impact: "High",
    confidence: "high",
    unlocks: [],
    problem: "There is a temptation, once a site exists, to fill it with picks. This site's most defensible content is that eleven ideas were tested properly and none survived. That is what saves money. It is also the only claim here that a reader can independently reproduce in an afternoon.",
    recommendation:
      "Keep the empty leaderboard. If a strategy is ever added that passes eight gates on out-of-sample data, that becomes news. Until then, the honest headline is the one at the top of the Overview.",
    options: [
      { id: "a", label: "Keep the empty leaderboard and lead with the negative result", note: "Recommended.", rec: true },
      { id: "b", label: "Add 'best available' picks even though they failed", note: "Would make the site look more useful and be actively misleading." },
    ],
    evidence: [
      { label: "Decision D20", url: "decisions.html" },
      { label: "Validation results", url: "strategies.html" },
    ],
  },
];

const CHOICE_KEY = "fl2.suggestion-choices.v1";

function loadChoices() {
  try { return JSON.parse(localStorage.getItem(CHOICE_KEY) || "{}"); } catch { return {}; }
}
function saveChoices(o) {
  try { localStorage.setItem(CHOICE_KEY, JSON.stringify(o)); } catch { /* storage blocked: fine */ }
}

function pageSuggestions() {
  const choices = loadChoices();
  const areas = [...new Set(SUGGESTIONS.map((s) => s.area))];

  const chip = (s) => {
    const c = choices[s.id];
    if (!c) return `<span class="badge mute">undecided</span>`;
    const map = { accept: ["ok", "accepted"], reject: ["bad", "rejected"], defer: ["warn", "deferred"] };
    const [cls, label] = map[c.choice] || ["mute", c.choice];
    return `<span class="badge ${cls}">${label}${c.option ? " · " + FL2UI.esc(c.option) : ""}</span>`;
  };

  const card = (s, i) => {
    const c = choices[s.id] || {};
    const opts = s.options
      .map((o) => {
        const checked = c.option === o.id ? " checked" : "";
        return `<label style="display:flex;gap:8px;align-items:flex-start;margin:6px 0;font-size:13px;cursor:pointer">
          <input type="radio" name="opt-${s.id}" value="${o.id}"${checked}
            onchange="pickOption('${s.id}','${o.id}')" style="margin-top:3px">
          <span><strong>${FL2UI.esc(o.label)}</strong>${o.rec ? ' <span class="badge ok">recommended</span>' : ""}
            <div class="small muted">${FL2UI.esc(o.note)}</div></span>
        </label>`;
      })
      .join("");

    return `<div class="sug ${c.choice ? "chosen-" + c.choice : ""}" id="${s.id}">
      <div class="card pad" style="border:0;box-shadow:none;padding:0;background:transparent">
        <div class="pill-row" style="justify-content:space-between;align-items:flex-start">
          <div>
            <div class="eyebrow">${FL2UI.esc(s.id)} · ${FL2UI.esc(s.area)}</div>
            <h3>${i + 1}. ${FL2UI.esc(s.title)}</h3>
          </div>
          <div>${chip(s)}</div>
        </div>
        <div class="why"><strong>Problem.</strong> ${FL2UI.esc(s.problem)}</div>
        <div class="why"><strong>Recommendation.</strong> ${FL2UI.esc(s.recommendation)}</div>
        <div class="eyebrow" style="margin-top:12px">Choose a path</div>
        ${opts}
        <div class="meta">
          <span><b>Effort</b> ${FL2UI.esc(s.effort)}</span>
          <span><b>Impact</b> ${FL2UI.esc(s.impact)}</span>
          <span><b>Confidence</b> ${FL2UI.esc(s.confidence)}</span>
          ${s.unlocks.length ? `<span><b>Unlocks</b> ${s.unlocks.map((u) => FL2UI.esc(u)).join(", ")}</span>` : ""}
        </div>
        <div class="src" style="margin-top:8px">Evidence: ${s.evidence.map((e) => FL2UI.srcLink(e.url, e.label)).join(" · ")}</div>
        <div class="controls">
          <button onclick="setChoice('${s.id}','accept')">Accept</button>
          <button onclick="setChoice('${s.id}','defer')">Defer</button>
          <button onclick="setChoice('${s.id}','reject')">Reject</button>
          <button onclick="clearChoice('${s.id}')">Clear</button>
          <span class="src" id="saved-${s.id}"></span>
        </div>
      </div>
    </div>`;
  };

  const decisions = Object.keys(choices).length;
  const accepted = Object.values(choices).filter((c) => c.choice === "accept").length;
  const deferred = Object.values(choices).filter((c) => c.choice === "defer").length;
  const rejected = Object.values(choices).filter((c) => c.choice === "reject").length;

  document.getElementById("app").innerHTML = `
    <div class="page-head">
      <p class="eyebrow">Suggestions · decide before building</p>
      <h1>Ten proposals, each with the path we would take and the paths we would not</h1>
      <p class="lede">This page exists so a change can be reviewed and a route chosen before anything
      is implemented. Every proposal names the concrete problem, the evidence, the effort, and what it
      unlocks. Recommendations are argued from results in this repository — they are not preferences.
      Your selections are stored in this browser only; nothing is sent anywhere.</p>
    </div>

    <div class="grid c4">
      <div class="stat"><div class="k">Proposals</div><div class="v">${SUGGESTIONS.length}</div>
        <div class="d">across ${areas.length} areas</div></div>
      <div class="stat ok"><div class="k">Accepted</div><div class="v" id="cnt-accept">${accepted}</div>
        <div class="d">chosen for implementation</div></div>
      <div class="stat warn"><div class="k">Deferred</div><div class="v" id="cnt-defer">${deferred}</div>
        <div class="d">parked deliberately</div></div>
      <div class="stat bad"><div class="k">Rejected</div><div class="v" id="cnt-reject">${rejected}</div>
        <div class="d">decided against</div></div>
    </div>

    <div class="note">
      <p><strong>Suggested reading order.</strong> S-01 unlocks the most. S-02 is the only one that loses
      value every week it is not started. S-09 is the cheapest and can be closed in fifteen minutes.
      S-05 and S-06 are policy calls that only the owner can make — they are proposed, not applied.</p>
      <p class="small" style="margin-bottom:0">Nothing on this page has been implemented on your behalf.
      The site reflects the current state, not these proposals.</p>
    </div>

    <section class="block">
      <h2>Ranked by value per unit of effort</h2>
      <p class="sub">Ordering is a judgement, argued in each card. Filter by area below.</p>
      <div class="pill-row" style="margin-bottom:14px">
        <button onclick="filterArea('all')" style="font:inherit;font-size:12.5px;padding:5px 11px;border-radius:20px;border:1px solid var(--line);background:#fff;cursor:pointer">All</button>
        ${areas.map((a) => `<button onclick="filterArea('${a}')" style="font:inherit;font-size:12.5px;padding:5px 11px;border-radius:20px;border:1px solid var(--line);background:#fff;cursor:pointer">${FL2UI.esc(a)}</button>`).join("")}
      </div>
      <div id="sug-list">${SUGGESTIONS.map(card).join("")}</div>
    </section>

    <section class="block">
      <h2>How a proposal gets adopted</h2>
      ${FL2UI.table(["Step", "What happens", "Where it is recorded"], [
        { cells: ["<td>1</td>", "<td>Read the problem statement and the evidence links — not the recommendation first.</td>", "<td class='small'>this page</td>"] },
        { cells: ["<td>2</td>", "<td>Choose an option, or reject the proposal outright. Acceptance is a decision about direction, not a commitment to a date.</td>", "<td class='small'>the controls on each card</td>"] },
        { cells: ["<td>3</td>", "<td>An accepted option becomes a task with an owner and a file scope.</td>",
                  "<td class='small'><a href='https://github.com/sassnarep3-star/FL2/blob/main/COORDINATION.md' target='_blank' rel='noopener'>COORDINATION.md</a></td>"] },
        { cells: ["<td>4</td>", "<td>The change is implemented, verified against a source, and any new unknowns are added to the flagged list.</td>",
                  "<td class='small'><a href='flagged.html'>Flagged for Review</a></td>"] },
        { cells: ["<td>5</td>", "<td>Only then does the site change.</td>", "<td class='small'>this site</td>"] },
      ])}
    </section>`;
}

/* ---------- interaction ---------- */
function setChoice(id, choice) {
  const c = loadChoices();
  c[id] = c[id] || {};
  c[id].choice = choice;
  saveChoices(c);
  rerender(id);
}
function pickOption(id, option) {
  const c = loadChoices();
  c[id] = c[id] || {};
  c[id].option = option;
  saveChoices(c);
  rerender(id);
}
function clearChoice(id) {
  const c = loadChoices();
  delete c[id];
  saveChoices(c);
  rerender(id);
}
function rerender(id) {
  pageSuggestions();
  document.querySelectorAll(".controls .src").forEach((e) => (e.textContent = e.textContent));
  const el = document.getElementById(id);
  if (el && typeof el.scrollIntoView === "function") el.scrollIntoView({ block: "nearest" });
}
function filterArea(area) {
  document.querySelectorAll("#sug-list .sug").forEach((el, i) => {
    const s = SUGGESTIONS[i];
    el.style.display = area === "all" || s.area === area ? "" : "none";
  });
}

window.pageSuggestions = pageSuggestions;
