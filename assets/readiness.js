/* FL2 readiness register: data comes only from the checked-in JSON file.
 * All user-facing values are inserted with textContent; links are restricted to
 * HTTPS hosts validated again by scripts/check_readiness.py. */
(() => {
  "use strict";

  const DATA_URL = "data/decision-readiness.json";
  const REVIEW_URL = "readiness-review.html";
  const ALLOWED_HOSTS = new Set([
    "nfl.com", "www.nfl.com", "operations.nfl.com", "static.www.nfl.com",
    "weather.gov", "www.weather.gov", "api.weather.gov",
    "patriots.com", "www.patriots.com", "detroitlions.com", "www.detroitlions.com",
    "packers.com", "www.packers.com", "chiefs.com", "www.chiefs.com",
    "49ers.com", "www.49ers.com"
  ]);

  const byId = (id) => document.getElementById(id);
  const text = (tag, value, className) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = value == null ? "" : String(value);
    return node;
  };

  function safeExternalLink(url, label) {
    let parsed;
    try {
      parsed = new URL(url);
    } catch (_) {
      return null;
    }
    if (parsed.protocol !== "https:" || !ALLOWED_HOSTS.has(parsed.hostname.toLowerCase())) {
      return null;
    }
    const link = document.createElement("a");
    link.href = parsed.href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = label;
    return link;
  }

  function stateLabel(state) {
    const labels = {
      "official-direct-unarchived": "Official page · direct fact · not archived",
      "official-pathway-unarchived": "Official source path/example · not archived",
      "club-unofficial-historical": "Club-published · explicitly unofficial · historical",
      "stale-or-conflicted": "Stale, conflicting, or not point-in-time verified",
      "repository-only": "Repository evidence only",
      "no-official-source": "No applicable official NFL source"
    };
    return labels[state] || "Source state unresolved";
  }

  function stateDescription(state) {
    const labels = {
      "official-direct-unarchived": "Direct official evidence supports the named fact only. The page response is not archived or hashed.",
      "official-pathway-unarchived": "The official page is a route or limited example; it does not prove local coverage or model validity. No page hash is stored.",
      "club-unofficial-historical": "The linked club page is identified as unofficial in the local record. It is not NFL-issued depth or actual-game starter evidence.",
      "stale-or-conflicted": "A local claim, source vintage, count, or method needs reconciliation. Do not treat the value as current availability.",
      "repository-only": "The finding concerns code, process, or local artifacts; project paths are the evidence, not an NFL source.",
      "no-official-source": "No applicable official NFL source can substantiate this research/policy gate. The source cell is intentionally blank."
    };
    return labels[state] || "The source/evidence state needs review.";
  }

  function appendSourceCell(cell, row, payload) {
    const sourceIds = Array.isArray(row.source_ids) ? row.source_ids : [];
    if (!sourceIds.length) {
      const blankLabel = row.evidence_state === "repository-only"
        ? "— Repository evidence only"
        : "— No applicable official source verified";
      cell.append(text("span", blankLabel, "blank"));
    } else {
      sourceIds.forEach((sourceId) => {
        const source = payload.sources[sourceId];
        if (!source) return;
        const wrap = document.createElement("div");
        wrap.className = "readiness-source-item";
        const link = safeExternalLink(source.url, source.label);
        if (link) {
          wrap.append(link);
        } else {
          wrap.append(text("span", "Invalid source URL blocked", "readiness-error-text"));
        }
        const date = source.checked_date_utc
          ? `Checked ${source.checked_date_utc}`
          : source.repository_recorded_date_utc
            ? `Recorded locally ${source.repository_recorded_date_utc}; not rechecked`
            : "Check date not recorded";
        wrap.append(text("small", date, "readiness-source-date"));
        const details = document.createElement("details");
        details.className = "readiness-source-details";
        details.append(text("summary", "Source scope / limitation"));
        details.append(text("p", source.verification));
        wrap.append(details);
        cell.append(wrap);
      });
    }

    if (row.flagged) {
      const review = document.createElement("a");
      review.className = "review-link";
      review.href = `${REVIEW_URL}#${encodeURIComponent(row.id)}`;
      review.textContent = "Flagged for Review ↗";
      cell.append(review);
    }
  }

  function projectEvidence(cell, refs) {
    refs.forEach((ref) => {
      const link = document.createElement("a");
      link.className = "project-ref";
      link.href = ref;
      const code = text("code", ref);
      link.append(code);
      cell.append(link, document.createElement("br"));
    });
  }

  function makeRequirementRow(row, payload) {
    const tr = document.createElement("tr");
    tr.dataset.status = row.status;
    tr.dataset.category = row.category;
    tr.dataset.flagged = row.flagged ? "true" : "false";
    tr.id = row.id;

    const idCell = document.createElement("td");
    idCell.className = "req-id";
    idCell.append(text("strong", row.id), text("span", row.category));
    tr.append(idCell);

    const detailCell = document.createElement("td");
    detailCell.className = "req-detail";
    detailCell.append(text("strong", row.requirement), text("small", row.finding));
    tr.append(detailCell);

    const statusCell = document.createElement("td");
    statusCell.append(text("span", row.status, `readiness-status status-${row.status}`));
    tr.append(statusCell);

    tr.append(text("td", row.gate));

    const clearanceCell = document.createElement("td");
    clearanceCell.className = "clearance";
    clearanceCell.append(text("strong", row.clearance_metric));
    tr.append(clearanceCell);

    const projectCell = document.createElement("td");
    projectCell.className = "project-evidence";
    projectEvidence(projectCell, row.project_refs);
    tr.append(projectCell);

    const evidenceCell = document.createElement("td");
    evidenceCell.className = "evidence-state-cell";
    evidenceCell.append(
      text("span", stateLabel(row.evidence_state), `evidence-state state-${row.evidence_state}`),
      text("small", row.evidence_note)
    );
    tr.append(evidenceCell);

    const sourcesCell = document.createElement("td");
    sourcesCell.className = "official-source";
    appendSourceCell(sourcesCell, row, payload);
    tr.append(sourcesCell);
    return tr;
  }

  function setKpis(rows) {
    const counts = {
      total: rows.length,
      implemented: rows.filter((row) => row.status === "implemented").length,
      partial: rows.filter((row) => row.status === "partial").length,
      open: rows.filter((row) => ["blocked", "needs-review", "proposed"].includes(row.status)).length
    };
    Object.entries(counts).forEach(([key, value]) => {
      const target = document.querySelector(`[data-kpi="${key}"]`);
      if (target) target.textContent = String(value);
    });
  }

  function populateCategoryFilter(rows, select) {
    if (!select) return;
    const categories = [...new Set(rows.map((row) => row.category))].sort((a, b) => a.localeCompare(b));
    categories.forEach((category) => {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      select.append(option);
    });
  }

  function initLanding(payload) {
    const tbody = byId("readiness-rows");
    const rows = payload.requirements;
    if (!tbody) return;
    rows.forEach((row) => tbody.append(makeRequirementRow(row, payload)));
    setKpis(rows);
    populateCategoryFilter(rows, byId("readiness-category-filter"));

    const search = byId("readiness-search");
    const status = byId("readiness-status-filter");
    const category = byId("readiness-category-filter");
    const flaggedOnly = byId("readiness-flagged-only");
    const count = byId("readiness-count");
    const empty = byId("readiness-empty");
    const table = byId("decision-readiness-table");

    function update() {
      const query = (search?.value || "").trim().toLocaleLowerCase();
      const statusValue = status?.value || "";
      const categoryValue = category?.value || "";
      const flaggedValue = Boolean(flaggedOnly?.checked);
      let visible = 0;
      [...tbody.rows].forEach((tr) => {
        const matches = (!query || tr.textContent.toLocaleLowerCase().includes(query))
          && (!statusValue || tr.dataset.status === statusValue)
          && (!categoryValue || tr.dataset.category === categoryValue)
          && (!flaggedValue || tr.dataset.flagged === "true");
        tr.hidden = !matches;
        if (matches) visible += 1;
      });
      if (count) count.textContent = `Showing ${visible} of ${rows.length} requirements`;
      if (empty) empty.hidden = visible !== 0;
      if (table) table.setAttribute("aria-rowcount", String(visible + 1));
    }

    [search, status, category, flaggedOnly].filter(Boolean).forEach((control) => {
      control.addEventListener(control.tagName === "INPUT" ? "input" : "change", update);
    });
    byId("readiness-clear")?.addEventListener("click", () => {
      if (search) search.value = "";
      if (status) status.value = "";
      if (category) category.value = "";
      if (flaggedOnly) flaggedOnly.checked = false;
      update();
      search?.focus();
    });
    const loading = byId("readiness-load-state");
    if (loading) loading.hidden = true;
    if (table) table.setAttribute("aria-busy", "false");
    update();
  }

  function makeReviewCard(row, payload) {
    const article = document.createElement("article");
    article.className = "readiness-flag";
    article.id = row.id;
    article.dataset.flagId = row.flag_id;
    article.dataset.status = row.status;

    const top = document.createElement("div");
    top.className = "readiness-flag-top";
    top.append(
      text("code", row.flag_id),
      text("span", row.status, `readiness-status status-${row.status}`),
      text("span", row.category, "readiness-category")
    );
    article.append(top);
    article.append(text("h2", `${row.id} · ${row.requirement}`));
    article.append(text("p", `Current evidence: ${row.finding}`));
    article.append(text("p", `Blocking gate: ${row.gate}`));
    article.append(text("p", `Clearance measure: ${row.clearance_metric}`));
    article.append(text("p", `Evidence/source state: ${stateLabel(row.evidence_state)}. ${row.evidence_note}`, "source-explainer"));

    const official = text("div", "", "review-links");
    official.append(text("strong", "Official source / review:"), document.createElement("br"));
    appendSourceCell(official, row, payload);
    article.append(official);

    const project = text("div", "", "review-links");
    project.append(text("strong", "Repository evidence:"), document.createElement("br"));
    projectEvidence(project, row.project_refs);
    article.append(project);
    return article;
  }

  function initReview(payload) {
    const list = byId("readiness-review-list");
    if (!list) return;
    const rows = payload.requirements.filter((row) => row.flagged);
    rows.forEach((row) => list.append(makeReviewCard(row, payload)));
    const search = byId("readiness-review-search");
    const status = byId("readiness-review-status");
    const count = byId("readiness-review-count");
    const empty = byId("readiness-review-empty");

    function update() {
      const query = (search?.value || "").trim().toLocaleLowerCase();
      const statusValue = status?.value || "";
      let visible = 0;
      [...list.children].forEach((article) => {
        const matches = (!query || article.textContent.toLocaleLowerCase().includes(query))
          && (!statusValue || article.dataset.status === statusValue);
        article.hidden = !matches;
        if (matches) visible += 1;
      });
      if (count) count.textContent = `Showing ${visible} of ${rows.length} flagged requirements`;
      if (empty) empty.hidden = visible !== 0;
    }

    [search, status].filter(Boolean).forEach((control) => {
      control.addEventListener(control.tagName === "INPUT" ? "input" : "change", update);
    });
    byId("readiness-review-clear")?.addEventListener("click", () => {
      if (search) search.value = "";
      if (status) status.value = "";
      update();
      search?.focus();
    });
    const loading = byId("readiness-review-load-state");
    if (loading) loading.hidden = true;
    update();
    if (window.location.hash) {
      const targetId = decodeURIComponent(window.location.hash.slice(1));
      requestAnimationFrame(() => byId(targetId)?.scrollIntoView({ block: "start" }));
    }
  }

  async function start() {
    const pageType = document.body.dataset.readinessPage;
    if (!pageType) return;
    const loadingId = pageType === "review" ? "readiness-review-load-state" : "readiness-load-state";
    const errorId = pageType === "review" ? "readiness-review-error" : "readiness-error";
    try {
      const response = await fetch(DATA_URL, { cache: "no-store", credentials: "same-origin" });
      if (!response.ok) throw new Error(`Register request failed (${response.status})`);
      const payload = await response.json();
      if (!Array.isArray(payload.requirements) || payload.requirements.length !== payload.meta.requirement_count) {
        throw new Error("Register structure/count mismatch");
      }
      if (pageType === "review") initReview(payload);
      else initLanding(payload);
    } catch (error) {
      const loading = byId(loadingId);
      if (loading) loading.hidden = true;
      const message = byId(errorId);
      if (message) {
        message.hidden = false;
        message.textContent = `The register could not be loaded (${error.message}). Open the raw JSON or Flagged for Review page below; no values have been filled in.`;
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
