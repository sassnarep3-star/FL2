"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM } = require("jsdom");

const root = path.resolve(__dirname, "..");
const payload = JSON.parse(fs.readFileSync(path.join(root, "data/decision-readiness.json"), "utf8"));
const expectedFlagged = payload.requirements.filter((row) => row.flagged);

function waitFor(predicate, description, timeoutMs = 5000) {
  return new Promise((resolve, reject) => {
    const started = Date.now();
    const timer = setInterval(() => {
      if (predicate()) {
        clearInterval(timer);
        resolve();
      } else if (Date.now() - started > timeoutMs) {
        clearInterval(timer);
        reject(new Error(`Timed out waiting for ${description}`));
      }
    }, 10);
  });
}

async function loadPage(filename) {
  const dom = await JSDOM.fromFile(path.join(root, filename), {
    runScripts: "dangerously",
    resources: "usable",
    pretendToBeVisual: true,
    beforeParse(window) {
      window.fetch = async () => ({
        ok: true,
        status: 200,
        json: async () => payload,
      });
    },
  });
  const pageType = filename === "readiness-review.html" ? "review" : "landing";
  const ready = pageType === "review"
    ? () => dom.window.document.querySelectorAll("#readiness-review-list article").length === expectedFlagged.length
    : () => dom.window.document.querySelectorAll("#readiness-rows tr").length === payload.requirements.length;
  await waitFor(ready, `${filename} to render register data`);
  return dom;
}

function visibleCount(nodes) {
  return [...nodes].filter((node) => !node.hidden).length;
}

function fire(window, element, eventName) {
  element.dispatchEvent(new window.Event(eventName, { bubbles: true }));
}

async function testLanding() {
  const dom = await loadPage("index.html");
  const { document } = dom.window;
  const rows = document.querySelectorAll("#readiness-rows tr");
  assert.equal(rows.length, 81, "landing page must render all 81 readiness rows");
  assert.equal(document.querySelector('#decision-readiness-table[aria-busy="false"]') !== null, true);
  assert.equal(document.querySelector('[data-kpi="total"]').textContent, "81");
  assert.equal(document.querySelector('[data-kpi="implemented"]').textContent, "4");
  assert.equal(document.querySelector('[data-kpi="partial"]').textContent, "49");
  assert.equal(document.querySelector('[data-kpi="open"]').textContent, "28");
  const category = document.getElementById("readiness-category-filter");
  assert.equal(category.options.length, 10, "nine categories plus the default option");
  category.value = "Availability & depth";
  fire(dom.window, category, "change");
  assert.equal(visibleCount(rows), payload.requirements.filter((row) => row.category === category.value).length, "category filter count");
  category.value = "";
  fire(dom.window, category, "change");
  assert.equal(visibleCount(rows), payload.requirements.length, "clearing category selection should restore all rows");

  const payloadSourceLinks = document.querySelectorAll("#readiness-rows a[href^='https://']");
  assert.ok(payloadSourceLinks.length > 0, "landing table should render scoped external source links");
  for (const link of payloadSourceLinks) {
    assert.equal(link.target, "_blank");
    assert.equal(link.rel, "noopener noreferrer");
  }
  assert.equal(document.querySelector("#REQ-003 .official-source a[href^='https://']"), null, "repository-only row must not imply official support");
  assert.match(document.querySelector("#REQ-001 .official-source").textContent, /No applicable official source/);
  assert.equal(document.querySelector("#REQ-048 .official-source a.review-link").getAttribute("href"), "readiness-review.html#REQ-048");

  const checkbox = document.getElementById("readiness-flagged-only");
  checkbox.checked = true;
  fire(dom.window, checkbox, "input");
  assert.equal(visibleCount(rows), expectedFlagged.length, "flagged-only filter count");

  const status = document.getElementById("readiness-status-filter");
  status.value = "blocked";
  fire(dom.window, status, "change");
  assert.equal(visibleCount(rows), payload.requirements.filter((row) => row.flagged && row.status === "blocked").length);

  const search = document.getElementById("readiness-search");
  search.value = "REQ-048";
  fire(dom.window, search, "input");
  assert.equal(visibleCount(rows), 0, "combined filters should still apply to search");
  assert.equal(document.getElementById("readiness-empty").hidden, false);

  document.getElementById("readiness-clear").click();
  assert.equal(visibleCount(rows), payload.requirements.length, "clear filters should restore the full landing register");
  assert.equal(document.getElementById("readiness-empty").hidden, true);
  assert.equal(document.getElementById("readiness-count").textContent, "Showing 81 of 81 requirements");
  dom.window.close();
  console.log(`Landing UI: rendered ${rows.length} rows; status, category, search, flagged-only and clear controls passed.`);
}

async function testReview() {
  const dom = await loadPage("readiness-review.html");
  const { document } = dom.window;
  const cards = document.querySelectorAll("#readiness-review-list article");
  assert.equal(cards.length, 78, "review page must render every flagged row and no unflagged rows");
  assert.equal(document.getElementById("REQ-048").dataset.flagId, "FR-REQ-048");
  assert.equal(document.querySelectorAll("#readiness-review-list article[data-flag-id]").length, expectedFlagged.length);

  const status = document.getElementById("readiness-review-status");
  status.value = "blocked";
  fire(dom.window, status, "change");
  assert.equal(visibleCount(cards), expectedFlagged.filter((row) => row.status === "blocked").length);

  status.value = "";
  fire(dom.window, status, "change");
  const search = document.getElementById("readiness-review-search");
  search.value = "REQ-048";
  fire(dom.window, search, "input");
  assert.equal(visibleCount(cards), 1, "review search should isolate the requested flagged row");
  assert.equal(document.getElementById("readiness-review-empty").hidden, true);

  search.value = "no-such-readiness-row";
  fire(dom.window, search, "input");
  assert.equal(visibleCount(cards), 0);
  assert.equal(document.getElementById("readiness-review-empty").hidden, false);
  document.getElementById("readiness-review-clear").click();
  assert.equal(visibleCount(cards), expectedFlagged.length, "clear filters should restore the review queue");
  assert.equal(document.getElementById("readiness-review-count").textContent, "Showing 78 of 78 flagged requirements");
  dom.window.close();
  console.log(`Review UI: rendered ${cards.length} flagged cards; status, search, empty state and clear controls passed.`);
}

(async () => {
  await testLanding();
  await testReview();
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
