// Optional UI smoke test: drives the real dashboard page in jsdom against a RUNNING server.
//   cd tests/ui_smoke && npm install && node ui_smoke.js http://127.0.0.1:8000
// It adds/edits/deletes test competitors through the UI and cleans up after itself. (jsdom is a simulated browser, not Chrome.)
const { JSDOM, VirtualConsole } = require('jsdom');
const BASE = (process.argv[2] || 'http://127.0.0.1:8000').replace(/\/$/, '');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failed = 0, passed = 0; const jsErrors = [];
const check = (name, ok, extra) => { if (ok) passed++; else failed++; console.log((ok ? 'PASS  ' : 'FAIL  ') + name + (extra ? '   <- ' + extra : '')); };
async function waitFor(fn, ms = 4000) { const t = Date.now(); while (Date.now() - t < ms) { try { const v = fn(); if (v) return v; } catch (e) { /* retry */ } await sleep(50); } return false; }
async function open(seedBackup) {
  const vc = new VirtualConsole(); vc.on('jsdomError', (e) => jsErrors.push(e.message)); vc.on('error', (m) => jsErrors.push(String(m)));
  const dom = await JSDOM.fromURL(BASE + '/', { runScripts: 'dangerously', resources: 'usable', pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) { w.fetch = (u, o) => fetch(new URL(u, BASE), o); w.confirm = () => true; if (seedBackup) w.localStorage.setItem('cbs.live.v1', JSON.stringify(seedBackup)); w.addEventListener('error', (e) => jsErrors.push(e.message)); } });
  return dom.window;
}
const api = async (m, p, b) => { const r = await fetch(BASE + '/api' + p, { method: m, headers: b ? { 'content-type': 'application/json' } : {}, body: b ? JSON.stringify(b) : undefined }); return r.json(); };
const txt = (w) => w.document.getElementById('view').textContent;
const click = (w, sel) => w.document.querySelector(sel).dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
const go = async (w, page) => { w.location.hash = '#/' + page; await waitFor(() => w.document.querySelector('nav button.active') && w.document.querySelector('nav button.active').dataset.page === page); await sleep(150); };

(async () => {
  await api('POST', '/demo/reset');
  const dash = await api('GET', '/dashboard');
  const w = await open();
  const ok = await waitFor(() => w.document.querySelectorAll('.card.stat').length >= 6);
  check('dashboard renders its 6 statistic cards', !!ok);
  const t = txt(w);
  check('cards show real API numbers', t.includes(String(dash.articles.total)) && t.includes('Average detection delay') && t.includes('Failed checks') && t.includes('Within 5-minute target'));
  check('chart, latest articles and recent checks are shown', !!w.document.querySelector('svg[aria-label="Articles discovered per day"]') && w.document.querySelectorAll('.row[data-action="open-article"]').length >= 5 && t.includes('Recent checks'));
  check('demo banner is shown and can be dismissed', !!w.document.querySelector('.banner')); click(w, '[data-action="dismiss-banner"]'); check('banner dismissed', !w.document.querySelector('.banner'));

  await go(w, 'competitors');
  check('competitors page lists the 4 sample competitors with badges', w.document.querySelectorAll('tbody tr').length === 4 && w.document.querySelectorAll('.badge.b-info').length >= 4 && txt(w).includes('Globex Cloud'));
  check('statuses shown (online, offline, disabled)', ['online', 'offline', 'disabled'].every((s) => txt(w).includes(s)));

  // add: first an invalid URL (validation message), then a valid one
  click(w, '[data-action="add"]');
  check('add modal opens', !!w.document.getElementById('comp-form'));
  const form = w.document.getElementById('comp-form');
  form.querySelector('[name=name]').value = 'UI Test Rival'; form.querySelector('[name=website_url]').value = 'not-a-url';
  form.dispatchEvent(new w.Event('submit', { bubbles: true, cancelable: true }));
  const err = await waitFor(() => { const e = w.document.querySelector('[data-err="website_url"]'); return e && e.textContent; });
  check('invalid URL shows the validation message under the field', !!err && /http/.test(err), err);
  form.querySelector('[name=website_url]').value = 'https://ui-test-rival.example/blog';
  form.dispatchEvent(new w.Event('submit', { bubbles: true, cancelable: true }));
  const added = await waitFor(() => txt(w).includes('UI Test Rival'));
  check('new competitor appears in the table (live badge)', !!added && !!w.document.querySelector('.badge.b-ok'));
  check('competitor is backed up in the browser', (w.localStorage.getItem('cbs.live.v1') || '').includes('UI Test Rival'));
  const dup = await api('POST', '/competitors', { name: 'Dup', website_url: 'https://www.ui-test-rival.example/blog/' });
  check('duplicate website is refused by the API', dup.field === 'website_url');

  // edit, check (sample), disable, delete
  const rowOf = (name) => [...w.document.querySelectorAll('tbody tr')].find((r) => r.textContent.includes(name));
  rowOf('UI Test Rival').querySelector('[data-action="edit"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  const f2 = w.document.getElementById('comp-form'); f2.querySelector('[name=name]').value = 'UI Test Renamed';
  f2.dispatchEvent(new w.Event('submit', { bubbles: true, cancelable: true }));
  check('edit renames the competitor', !!(await waitFor(() => txt(w).includes('UI Test Renamed') && !txt(w).includes('UI Test Rival'))));
  rowOf('Acme Analytics').querySelector('[data-action="check-one"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  check('"Check" runs a monitoring check and shows a result toast', !!(await waitFor(() => w.document.querySelector('.toast') && /Acme Analytics/.test(w.document.querySelector('.toast').textContent))));
  await sleep(300);
  rowOf('UI Test Renamed').querySelector('[data-action="toggle"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  check('disable toggles status to disabled', !!(await waitFor(() => rowOf('UI Test Renamed') && rowOf('UI Test Renamed').textContent.includes('disabled'))));
  rowOf('UI Test Renamed').querySelector('[data-action="delete"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  check('delete removes it (and its backup)', !!(await waitFor(() => !txt(w).includes('UI Test Renamed'))) && !(w.localStorage.getItem('cbs.live.v1') || '').includes('Renamed'));

  // articles: list, search, detail
  await go(w, 'articles');
  const total = w.document.querySelectorAll('#article-list .row').length;
  check('articles page lists articles', total >= 5, total + ' rows');
  const q = w.document.getElementById('f-q'); q.value = 'api'; q.dispatchEvent(new w.Event('input', { bubbles: true }));
  const filtered = await waitFor(() => { const n = w.document.querySelectorAll('#article-list .row').length; return n > 0 && n < total ? n : false; });
  check('search narrows the list', !!filtered, filtered + ' rows for "api"');
  const sel = w.document.getElementById('f-status'); sel.value = 'baseline'; sel.dispatchEvent(new w.Event('change', { bubbles: true }));
  check('status filter shows only baseline articles', !!(await waitFor(() => { const rows = w.document.querySelectorAll('#article-list .row'); return rows.length && [...rows].every((r) => r.textContent.includes('baseline')); })));
  const sel2 = w.document.getElementById('f-status');   // the page was re-rendered by the previous filter: look the element up again
  sel2.value = 'new'; sel2.dispatchEvent(new w.Event('change', { bubbles: true }));
  await waitFor(() => { const rows = w.document.querySelectorAll('#article-list .row'); return rows.length && [...rows].every((r) => !r.textContent.includes('baseline')); });
  w.document.querySelector('#article-list .row').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  const modal = await waitFor(() => w.document.querySelector('.modal[aria-label="Article details"]'));
  check('article detail opens with delay, method and source', !!modal && /Detection delay/.test(modal.textContent) && /exactly/.test(modal.textContent) && /Source URL/.test(modal.textContent) && /Published/.test(modal.textContent), modal ? modal.textContent.replace(/\s+/g, ' ').slice(0, 330) : 'no modal opened');
  click(w, '.modal [data-action="close"]'); check('article detail closes', !w.document.querySelector('.modal'));

  // activity
  await go(w, 'activity');
  check('activity page lists checks including failures', w.document.querySelectorAll('tbody tr').length >= 10 && /failed/.test(txt(w)) && /success/.test(txt(w)));

  // check all (button on dashboard)
  await go(w, 'dashboard');
  click(w, '[data-action="check-all"]');
  check('"Check all" completes and reports', !!(await waitFor(() => [...w.document.querySelectorAll('.toast')].some((e) => /Checked \d+ competitor/.test(e.textContent)), 8000)));

  // restore after a "server restart": server is pristine again, the browser still has a backup
  await api('POST', '/demo/reset');
  const w2 = await open([{ name: 'Restored Rival', website_url: 'https://restored-rival.example/', feed_url: null, enabled: true }]);
  await waitFor(() => w2.document.querySelectorAll('.card.stat').length >= 6);
  const list = await api('GET', '/competitors');
  check('competitors backed up in the browser are restored after a server reset', list.some((c) => c.name === 'Restored Rival' && c.kind === 'live'));
  check('restore is announced to the user', [...w2.document.querySelectorAll('.toast')].some((e) => /Restored 1 competitor/.test(e.textContent)));
  const w3 = await open([{ name: 'Should Not Duplicate', website_url: 'https://dup-restore.example/', enabled: true }]);
  await waitFor(() => w3.document.querySelectorAll('.card.stat').length >= 6);
  check('a server that already has changes is not overwritten by a backup', !(await api('GET', '/competitors')).some((c) => c.name === 'Should Not Duplicate'));

  check('no JavaScript errors occurred', jsErrors.length === 0, jsErrors.slice(0, 3).join(' | '));
  await api('POST', '/demo/reset');
  console.log(`\nUI smoke: ${passed} passed, ${failed} failed`);
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.error('ui_smoke crashed:', e); process.exit(2); });
