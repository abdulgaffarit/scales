#!/usr/bin/env node
/* Search correctness tests, run by build.py after the site is generated.
 * Usage: node tests/search.test.js [output-dir]
 * Checks the real search code (assets/search.js) against the real index and pages:
 *   - required queries resolve to the right page, and a state alone resolves to none;
 *   - every result exists and is indexable (never a noindex page);
 *   - every occupation title, alone and with every state, finds its own page first. */
'use strict';
const fs = require('fs');
const path = require('path');
require(path.join(__dirname, '..', 'assets', 'search.js'));
const S = globalThis.USSearch;

const out = path.resolve(process.argv[2] || path.join(__dirname, '..', 'output'));
const idx = S.prep(JSON.parse(fs.readFileSync(path.join(out, 'search-index.json'), 'utf8')));

const robotsCache = new Map();
function destProblem(url) {
  if (robotsCache.has(url)) return robotsCache.get(url);
  const file = path.join(out, url, 'index.html');
  let problem = null;
  if (!fs.existsSync(file)) problem = 'missing page ' + url;
  else {
    const m = fs.readFileSync(file, 'utf8').match(/<meta name="robots" content="([^"]*)"/);
    if (!m || /noindex/.test(m[1])) problem = 'noindex destination ' + url;
  }
  robotsCache.set(url, problem);
  return problem;
}

const cases = [
  // [query, intent, first result / Enter destination (null = must have none)]
  ['nurse', 'occupation', '/salary/registered-nurses/'],
  ['registered nurse', 'occupation', '/salary/registered-nurses/'],
  ['texas', 'state', null],
  ['nurse texas', 'occupation+state', '/salary/registered-nurses/texas/'],
  ['texas nurse', 'occupation+state', '/salary/registered-nurses/texas/'],
  ['nurse TX', 'occupation+state', '/salary/registered-nurses/texas/'],
  ['california nurse', 'occupation+state', '/salary/registered-nurses/california/'],
  ['teacher texas', 'occupation+state', '/salary/elementary-school-teachers/texas/'],
  ['engineer california', 'occupation+state', '/salary/civil-engineers/california/'],
  ['registered nurses in texas', 'occupation+state', '/salary/registered-nurses/texas/'],
  ['new york', 'state', null],
  ['west virginia', 'state', null],
  ['virginia', 'state', null],
  ['nurse kansas', 'occupation+state', '/salary/registered-nurses/kansas/'],
  ['arkansas nurse', 'occupation+state', '/salary/registered-nurses/arkansas/'],
  ['software developer', 'occupation', '/salary/software-developers/'],
  ['actor', 'none', null],          // BLS publishes hourly wages only: noindex page, not searchable
  ['xyzzy', 'none', null],
];

const failures = [];
const fail = (q, msg) => failures.push(`"${q}": ${msg}`);

for (const [q, mode, first] of cases) {
  const r = S.search(idx, q, 8);
  const items = r.groups.flatMap(g => g.items);
  const enter = S.enterTarget(r);
  if (r.mode !== mode) fail(q, `intent ${r.mode}, expected ${mode}`);
  if (enter !== first) fail(q, `Enter opens ${enter}, expected ${first}`);
  if (first && (!items[0] || items[0].url !== first)) fail(q, `first result ${items[0] && items[0].url}`);
  if (mode === 'state') {
    if (items.length < 5) fail(q, 'state query lists too few occupations');
    if (items.some(i => !i.url.endsWith('/' + r.state.slug + '/'))) fail(q, 'state query lists a page outside the state');
  }
  for (const i of items) { const p = destProblem(i.url); if (p) fail(q, p); }
}

// Exhaustive: each occupation alone and with each state resolves its own page first,
// and every listed result is an existing, indexable page.
let total = 0;
for (const j of idx.jobs) {
  for (const s of [null, ...idx.states]) {
    total++;
    const q = s ? `${j.title} ${s.name}` : j.title;
    const r = S.search(idx, q, 8);
    const items = r.groups.flatMap(g => g.items);
    const want = s && j.missing.indexOf(s.i) < 0 ? `/salary/${j.slug}/${s.slug}/` : `/salary/${j.slug}/`;
    if (!items[0] || items[0].url !== want || S.enterTarget(r) !== want) fail(q, `resolves to ${items[0] && items[0].url}, expected ${want}`);
    for (const i of items) { const p = destProblem(i.url); if (p) fail(q, p); }
    if (failures.length > 50) break;
  }
}

// Each state on its own: state context only, nothing preselected.
for (const s of idx.states) {
  const r = S.search(idx, s.name, 8);
  if (r.mode !== 'state' || r.state.slug !== s.slug || S.enterTarget(r) !== null) fail(s.name, 'not treated as state context');
}

if (failures.length) {
  console.error(failures.slice(0, 50).join('\n'));
  console.error(`❌ Search tests: ${failures.length} failure(s)`);
  process.exit(1);
}
console.log(`✅ Search tests: ${cases.length} named queries, ${total.toLocaleString('en-US')} occupation/state queries, ` +
  `${idx.states.length} state-only queries, ${robotsCache.size.toLocaleString('en-US')} destinations indexable`);
