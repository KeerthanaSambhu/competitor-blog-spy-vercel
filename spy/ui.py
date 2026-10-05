"""The whole dashboard (HTML + CSS + JavaScript) as one embedded page. Embedding it in Python means there are no static files to
bundle, so the deployed function is self-contained and the page cannot be missing on Vercel."""

FAVICON_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#4f46e5"/>'
               '<circle cx="29" cy="29" r="12" fill="none" stroke="#fff" stroke-width="5"/><path d="M38 38l12 12" stroke="#fff" stroke-width="6" stroke-linecap="round"/></svg>')

INDEX_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Competitor Blog Spy</title>
<meta name="description" content="Monitor competitor blogs and measure how fast new articles are detected.">
<link rel="icon" href="/favicon.ico" type="image/svg+xml">
<style>
:root{--bg:#f5f6fa;--card:#fff;--ink:#111827;--muted:#6b7280;--line:#e5e7eb;--brand:#4f46e5;--brand2:#4338ca;--ok:#047857;--okbg:#d1fae5;--bad:#b91c1c;--badbg:#fee2e2;--warn:#b45309;--warnbg:#fef3c7;--gray:#374151;--graybg:#e5e7eb;--info:#1d4ed8;--infobg:#dbeafe;--shadow:0 1px 2px rgba(16,24,40,.06),0 1px 3px rgba(16,24,40,.08)}
@media (prefers-color-scheme:dark){:root{--bg:#0f1220;--card:#181c2e;--ink:#e8eaf3;--muted:#9aa3b8;--line:#2a3050;--brand:#818cf8;--brand2:#a5b4fc;--ok:#6ee7b7;--okbg:#064e3b;--bad:#fca5a5;--badbg:#7f1d1d;--warn:#fcd34d;--warnbg:#78350f;--gray:#cbd5e1;--graybg:#2a3050;--info:#93c5fd;--infobg:#1e3a8a;--shadow:none}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--brand);text-decoration:none}a:hover{text-decoration:underline}
header{position:sticky;top:0;z-index:20;background:var(--card);border-bottom:1px solid var(--line)}
.bar{max-width:1180px;margin:0 auto;padding:10px 16px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:17px;color:var(--ink)}
.logo{width:30px;height:30px;border-radius:8px;background:var(--brand);display:grid;place-items:center}
.pill{font-size:11px;font-weight:600;padding:2px 8px;border-radius:999px;background:var(--warnbg);color:var(--warn)}
nav{display:flex;gap:4px;margin-left:auto;overflow-x:auto}
nav button{border:0;background:none;color:var(--muted);font:inherit;font-weight:600;padding:8px 12px;border-radius:8px;cursor:pointer;white-space:nowrap}
nav button:hover{background:var(--graybg)}nav button.active{color:var(--brand);background:var(--infobg)}
main{max-width:1180px;margin:0 auto;padding:18px 16px 60px}
h1{font-size:22px;margin:0}h2{font-size:16px;margin:0 0 10px}
.head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:16px}
.sub{color:var(--muted);font-size:13px}
.btn{border:1px solid var(--line);background:var(--card);color:var(--ink);font:inherit;font-weight:600;padding:8px 14px;border-radius:9px;cursor:pointer;box-shadow:var(--shadow)}
.btn:hover{border-color:var(--brand)}.btn:disabled{opacity:.55;cursor:not-allowed}
.btn.primary{background:var(--brand);border-color:var(--brand);color:#fff}.btn.primary:hover{background:var(--brand2)}
.btn.danger{color:var(--bad)}.btn.small{padding:4px 10px;font-size:13px;box-shadow:none}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-bottom:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;box-shadow:var(--shadow)}
.stat .label{font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.stat .value{font-size:26px;font-weight:700;margin:2px 0}.stat .note{font-size:12.5px;color:var(--muted)}
.grid2{display:grid;grid-template-columns:3fr 2fr;gap:12px;margin-bottom:16px}
@media (max-width:820px){.grid2{grid-template-columns:1fr}}
.badge{display:inline-block;font-size:11.5px;font-weight:700;padding:2px 8px;border-radius:999px;white-space:nowrap}
.b-ok{background:var(--okbg);color:var(--ok)}.b-bad{background:var(--badbg);color:var(--bad)}.b-warn{background:var(--warnbg);color:var(--warn)}.b-gray{background:var(--graybg);color:var(--gray)}.b-info{background:var(--infobg);color:var(--info)}
.tablewrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:10px;border-bottom:1px solid var(--line);vertical-align:middle}tr:last-child td{border-bottom:0}
td.actions{white-space:nowrap;text-align:right}td.actions .btn{margin-left:4px}
.clip{max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:inline-block;vertical-align:bottom}
.list .row{display:flex;gap:12px;justify-content:space-between;align-items:flex-start;padding:11px 0;border-bottom:1px solid var(--line);cursor:pointer}
.list .row:last-child{border-bottom:0}.list .row:hover .t{color:var(--brand)}
.row .t{font-weight:600}.row .meta{font-size:12.5px;color:var(--muted);margin-top:2px}.row .right{text-align:right;white-space:nowrap}
.bars{display:flex;flex-direction:column;gap:8px}
.bar-row{display:grid;grid-template-columns:130px 1fr 28px;gap:8px;align-items:center;font-size:13px}
.bar-row .track{background:var(--graybg);border-radius:6px;height:12px;overflow:hidden}.bar-row .fill{background:var(--brand);height:100%;border-radius:6px}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
input,select,textarea{font:inherit;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:9px;padding:8px 10px;min-width:0}
input:focus,select:focus,.btn:focus-visible,nav button:focus-visible{outline:2px solid var(--brand);outline-offset:1px}
.filters input{flex:1;min-width:180px}
.empty{text-align:center;color:var(--muted);padding:28px 10px}
.banner{background:var(--warnbg);color:var(--warn);border-radius:10px;padding:10px 14px;margin-bottom:16px;display:flex;gap:12px;justify-content:space-between;align-items:flex-start;font-size:13.5px}
.banner button{background:none;border:0;color:inherit;font-size:20px;line-height:1;cursor:pointer}
.error{background:var(--badbg);color:var(--bad);padding:12px 14px;border-radius:10px;margin-bottom:12px}
.modal-bg{position:fixed;inset:0;background:rgba(15,18,32,.55);display:grid;place-items:center;padding:16px;z-index:50;overflow:auto}
.modal{background:var(--card);border-radius:14px;max-width:620px;width:100%;padding:20px;box-shadow:0 20px 50px rgba(0,0,0,.3);max-height:92vh;overflow:auto}
.modal h2{font-size:18px}.field{margin-bottom:12px}.field label{display:block;font-weight:600;font-size:13px;margin-bottom:4px}.field input{width:100%}
.field .err{color:var(--bad);font-size:12.5px;margin-top:3px}.field .hint{color:var(--muted);font-size:12.5px;margin-top:3px}
.modal .foot{display:flex;gap:8px;justify-content:flex-end;margin-top:14px}
dl.kv{display:grid;grid-template-columns:150px 1fr;gap:6px 12px;margin:12px 0;font-size:14px}dl.kv dt{color:var(--muted)}dl.kv dd{margin:0;word-break:break-word}
#toast{position:fixed;left:50%;bottom:20px;transform:translateX(-50%);display:flex;flex-direction:column;gap:8px;z-index:60;width:min(92vw,460px)}
.toast{background:#111827;color:#fff;padding:10px 14px;border-radius:10px;box-shadow:0 6px 20px rgba(0,0,0,.3);font-size:14px}.toast.bad{background:#991b1b}.toast.ok{background:#065f46}
footer{max-width:1180px;margin:0 auto;padding:0 16px 30px;color:var(--muted);font-size:12.5px}
.loading{color:var(--muted);padding:40px;text-align:center}
.switch{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--muted)}
svg text{fill:var(--muted);font-size:10px}
@media (max-width:640px){.hide-sm{display:none}.bar{gap:8px}nav{margin-left:0;width:100%}.clip{max-width:150px}dl.kv{grid-template-columns:1fr}}
</style>
</head>
<body>
<header><div class="bar">
  <a class="brand" href="#/dashboard" aria-label="Competitor Blog Spy home"><span class="logo"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l6 6"/></svg></span>Competitor Blog Spy <span class="pill">Demo</span></a>
  <nav aria-label="Main">
    <button data-action="nav" data-page="dashboard">Dashboard</button>
    <button data-action="nav" data-page="competitors">Competitors</button>
    <button data-action="nav" data-page="articles">Articles</button>
    <button data-action="nav" data-page="activity">Activity</button>
  </nav>
</div></header>
<main>
  <div id="banner"></div>
  <div id="view" aria-live="polite"><div class="loading">Loading…</div></div>
</main>
<footer>
  <div>Demo mode: data is kept in server memory, so it can reset when the serverless instance restarts. Competitors you add are backed up in this browser and restored automatically. Sample competitors are simulated; yours are checked live.</div>
  <div style="margin-top:6px"><a href="/docs">API documentation</a> · <a href="/api/health">Health</a> · <a href="#" data-action="reset-demo">Reset demo data</a></div>
</footer>
<div id="modal-root"></div>
<div id="toast" role="status"></div>
<noscript><div style="padding:20px;text-align:center">This dashboard needs JavaScript.</div></noscript>
<script>
(function () {
'use strict';
const $ = (s, r) => (r || document).querySelector(s);
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const BACKUP_KEY = 'cbs.live.v1', AUTO_KEY = 'cbs.auto', BANNER_KEY = 'cbs.banner';
const S = {page: 'dashboard', dash: null, competitors: [], articles: [], total: 0, checks: [], filters: {competitor_id: '', q: '', status: ''}, limit: 30, error: null, busy: {}};

async function api(method, path, body) {
  const res = await fetch('/api' + path, {method, headers: body ? {'Content-Type': 'application/json'} : {}, body: body ? JSON.stringify(body) : undefined});
  let data = null;
  try { data = await res.json(); } catch (e) { data = null; }
  if (!res.ok) { const err = new Error((data && data.detail) || ('Request failed (' + res.status + ')')); err.field = data && data.field; throw err; }
  return data;
}
function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage may be unavailable (private mode) */ } }

// ---------------------------------------------------------------- formatting
function date(iso) { return iso ? new Date(iso) : null; }
function abs(iso) { const d = date(iso); return d ? d.toLocaleString() : '—'; }
function ago(iso) {
  const d = date(iso); if (!d) return 'never';
  const s = Math.max(0, Math.round((Date.now() - d.getTime()) / 1000));
  if (s < 45) return 'just now'; if (s < 3600) return Math.round(s / 60) + ' min ago';
  if (s < 86400) return Math.round(s / 3600) + ' h ago'; return Math.round(s / 86400) + ' d ago';
}
function human(sec) {
  if (sec == null) return '—';
  if (sec < 60) return sec.toFixed(1) + ' s';
  if (sec < 3600) return Math.floor(sec / 60) + ' min ' + Math.round(sec % 60) + ' s';
  return Math.floor(sec / 3600) + ' h ' + Math.round((sec % 3600) / 60) + ' min';
}
function delayBadge(sec) {
  if (sec == null) return '<span class="badge b-gray" title="The source gave no publication time, so no delay can be calculated">n/a</span>';
  return '<span class="badge ' + (sec <= 300 ? 'b-ok' : 'b-warn') + '" title="' + esc(sec) + ' seconds exactly' + (sec > 300 ? ' - over the 5 minute target' : '') + '">' + esc(human(sec)) + '</span>';
}
function statusBadge(s) { const m = {online: 'b-ok', offline: 'b-bad', disabled: 'b-gray', unchecked: 'b-warn'}; return '<span class="badge ' + (m[s] || 'b-gray') + '">' + esc(s) + '</span>'; }
function kindBadge(k) { return k === 'sample' ? '<span class="badge b-info" title="Simulated: checks of sample competitors are generated locally">sample</span>' : '<span class="badge b-ok" title="Checked live over the internet">live</span>'; }
function toast(msg, kind) {
  const el = document.createElement('div'); el.className = 'toast ' + (kind || ''); el.textContent = msg; $('#toast').appendChild(el);
  setTimeout(() => el.remove(), kind === 'bad' ? 7000 : 4000);
}

// ---------------------------------------------------------------- data
async function refresh() {
  const q = new URLSearchParams({limit: S.limit}); const f = S.filters;
  if (f.competitor_id) q.set('competitor_id', f.competitor_id); if (f.q) q.set('q', f.q); if (f.status) q.set('status', f.status);
  try {
    const [dash, comps, arts, checks] = await Promise.all([api('GET', '/dashboard'), api('GET', '/competitors'), api('GET', '/articles?' + q), api('GET', '/checks?limit=50')]);
    S.dash = dash; S.competitors = comps; S.articles = arts.items; S.total = arts.total; S.checks = checks; S.error = null;
  } catch (e) { S.error = e.message; }
  render();
}
function backupLive() {
  const live = S.competitors.filter((c) => c.kind === 'live').map((c) => ({name: c.name, website_url: c.website_url, feed_url: c.feed_url, enabled: c.enabled}));
  lsSet(BACKUP_KEY, JSON.stringify(live));
}
async function restoreIfNeeded() {
  let backup = []; try { backup = JSON.parse(lsGet(BACKUP_KEY) || '[]'); } catch (e) { backup = []; }
  if (!backup.length) return;
  try {
    const st = await api('GET', '/state');
    if (!st.pristine) return;
    const r = await api('POST', '/state/restore', {competitors: backup});
    if (r.restored) toast('Restored ' + r.restored + ' competitor(s) from this browser after a server restart. Run a check to refill their articles.', 'ok');
  } catch (e) { /* nothing to restore, or the server already has data */ }
}

// ---------------------------------------------------------------- pages
function statCard(label, value, note) { return '<div class="card stat"><div class="label">' + esc(label) + '</div><div class="value">' + value + '</div><div class="note">' + note + '</div></div>'; }
function dayChart(days) {
  const max = Math.max(1, ...days.map((d) => d.count)), W = 560, H = 150, bw = W / days.length;
  const bars = days.map((d, i) => { const h = Math.round((d.count / max) * (H - 30)); const x = i * bw + 4;
    return '<g><title>' + esc(d.date) + ': ' + d.count + ' article(s)</title><rect x="' + x + '" y="' + (H - 18 - h) + '" width="' + (bw - 8) + '" height="' + h + '" rx="3" fill="var(--brand)" opacity="' + (d.count ? 1 : .25) + '"/>' +
      (d.count ? '<text x="' + (x + (bw - 8) / 2) + '" y="' + (H - 22 - h) + '" text-anchor="middle">' + d.count + '</text>' : '') +
      '<text x="' + (x + (bw - 8) / 2) + '" y="' + (H - 4) + '" text-anchor="middle">' + esc(d.date.slice(5)) + '</text></g>'; }).join('');
  return '<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" role="img" aria-label="Articles discovered per day">' + bars + '</svg>';
}
function articleRow(a) {
  return '<div class="row" data-action="open-article" data-id="' + a.id + '" tabindex="0"><div><div class="t">' + esc(a.title) + '</div><div class="meta">' + esc(a.competitor_name || '') + ' · discovered ' + esc(ago(a.discovered_at)) +
    ' · ' + esc(a.method) + '</div></div><div class="right">' + delayBadge(a.detection_delay_seconds) + '<div style="margin-top:4px">' + (a.status === 'new' ? '<span class="badge b-info">new</span>' : '<span class="badge b-gray">baseline</span>') + '</div></div></div>';
}
function dashboardPage() {
  const d = S.dash; if (!d) return '<div class="loading">Loading…</div>';
  const c = d.competitors, a = d.articles, t = d.detection_delay, k = d.checks, bs = c.by_status;
  const cards = [
    statCard('Competitors', c.total, (bs.online || 0) + ' online · ' + (bs.offline || 0) + ' offline · ' + (bs.disabled || 0) + ' disabled'),
    statCard('Articles discovered', a.total, a.new + ' detected as new · ' + a.baseline + ' baseline'),
    statCard('Average detection delay', esc(human(t.average_seconds)), 'fastest ' + esc(human(t.fastest_seconds)) + ' · slowest ' + esc(human(t.slowest_seconds))),
    statCard('Within 5-minute target', t.measured ? Math.round(100 * t.within_target / t.measured) + '%' : '—', t.within_target + ' of ' + t.measured + ' measured articles'),
    statCard('Failed checks', k.failed, k.total ? 'of ' + k.total + ' checks · ' + k.success_rate + '% succeeded' : 'no checks yet'),
    statCard('Discovered in 24 h', a.last_24h, 'articles across all competitors')];
  const byComp = a.by_competitor.length ? '<div class="bars">' + a.by_competitor.map((x) => '<div class="bar-row"><span class="clip" style="max-width:130px" title="' + esc(x.name) + '">' + esc(x.name) + '</span><div class="track"><div class="fill" style="width:' + Math.round(100 * x.count / a.by_competitor[0].count) + '%"></div></div><b>' + x.count + '</b></div>').join('') + '</div>' : '<div class="empty">No articles yet</div>';
  const checksHtml = d.recent_checks.length ? d.recent_checks.map((x) => '<div class="row" style="cursor:default"><div><div class="t">' + esc(x.competitor_name) + '</div><div class="meta">' + esc(ago(x.started_at)) + ' · ' + esc(x.method || '—') + ' · ' + x.items_found + ' items · ' + x.new_articles + ' new' + (x.error ? ' · ' + esc(x.error) : '') + '</div></div><div class="right"><span class="badge ' + (x.status === 'success' ? 'b-ok' : 'b-bad') + '">' + esc(x.status) + '</span></div></div>').join('') : '<div class="empty">No checks yet</div>';
  return '<div class="head"><div><h1>Dashboard</h1><div class="sub">Competitor blog monitoring at a glance</div></div><div><label class="switch"><input type="checkbox" id="auto" ' + (lsGet(AUTO_KEY) === '1' ? 'checked' : '') + '> auto-check every 5 min while this page is open</label> <button class="btn primary" data-action="check-all"' + (S.busy.all ? ' disabled' : '') + '>' + (S.busy.all ? 'Checking…' : 'Check all competitors') + '</button></div></div>' +
    '<div class="cards">' + cards.join('') + '</div>' +
    '<div class="grid2"><div class="card"><h2>Articles discovered per day</h2>' + dayChart(a.per_day) + '</div><div class="card"><h2>Articles by competitor</h2>' + byComp + '</div></div>' +
    '<div class="grid2"><div class="card list"><h2>Latest detected articles</h2>' + (d.latest_articles.length ? d.latest_articles.map(articleRow).join('') : '<div class="empty">No articles yet - add a competitor and run a check</div>') + '</div><div class="card list"><h2>Recent checks</h2>' + checksHtml + '</div></div>';
}
function competitorsPage() {
  const rows = S.competitors.map((c) => '<tr><td><b>' + esc(c.name) + '</b> ' + kindBadge(c.kind) + '</td><td><a class="clip" href="' + esc(c.website_url) + '" target="_blank" rel="noopener noreferrer">' + esc(c.website_url) + '</a></td><td class="hide-sm">' + esc(c.strategy || '—') + '</td><td>' + statusBadge(c.status) +
    (c.last_error ? '<div class="sub clip" style="max-width:200px" title="' + esc(c.last_error) + '">' + esc(c.last_error) + '</div>' : '') + '</td><td class="hide-sm" title="' + esc(abs(c.last_checked_at)) + '">' + esc(ago(c.last_checked_at)) + '</td><td class="hide-sm">' + c.article_count + '</td><td class="actions">' +
    '<button class="btn small" data-action="check-one" data-id="' + c.id + '"' + (!c.enabled || S.busy[c.id] ? ' disabled' : '') + '>' + (S.busy[c.id] ? 'Checking…' : 'Check') + '</button><button class="btn small" data-action="edit" data-id="' + c.id + '">Edit</button>' +
    '<button class="btn small" data-action="toggle" data-id="' + c.id + '">' + (c.enabled ? 'Disable' : 'Enable') + '</button><button class="btn small danger" data-action="delete" data-id="' + c.id + '">Delete</button></td></tr>').join('');
  return '<div class="head"><div><h1>Competitors</h1><div class="sub">Add a blog or website; the app finds its feed or article links automatically. ' + S.competitors.length + ' monitored.</div></div><button class="btn primary" data-action="add">+ Add competitor</button></div>' +
    '<div class="card tablewrap">' + (S.competitors.length ? '<table><thead><tr><th>Name</th><th>Website</th><th class="hide-sm">Strategy</th><th>Status</th><th class="hide-sm">Last checked</th><th class="hide-sm">Articles</th><th></th></tr></thead><tbody>' + rows + '</tbody></table>' : '<div class="empty">No competitors yet. Click “Add competitor”.</div>') + '</div>';
}
function articleList() {
  const more = S.articles.length < S.total ? '<div style="text-align:center;margin-top:10px"><button class="btn" data-action="more-articles">Show more (' + (S.total - S.articles.length) + ' left)</button></div>' : '';
  return (S.articles.length ? S.articles.map(articleRow).join('') : '<div class="empty">No articles match.</div>') + more;
}
function articlesPage() {
  const opts = '<option value="">All competitors</option>' + S.competitors.map((c) => '<option value="' + c.id + '"' + (String(c.id) === String(S.filters.competitor_id) ? ' selected' : '') + '>' + esc(c.name) + '</option>').join('');
  const st = ['', 'new', 'baseline'].map((v) => '<option value="' + v + '"' + (S.filters.status === v ? ' selected' : '') + '>' + (v ? (v === 'new' ? 'Detected as new' : 'Baseline (existing)') : 'All statuses') + '</option>').join('');
  return '<div class="head"><div><h1>Articles</h1><div class="sub"><span id="art-count">' + S.total + '</span> article(s) discovered</div></div></div>' +
    '<div class="filters"><select id="f-comp" aria-label="Competitor">' + opts + '</select><select id="f-status" aria-label="Status">' + st + '</select><input id="f-q" type="search" placeholder="Search titles, summaries, tags…" value="' + esc(S.filters.q) + '" aria-label="Search"></div>' +
    '<div class="card list" id="article-list">' + articleList() + '</div>';
}
function activityPage() {
  const rows = S.checks.map((x) => '<tr><td title="' + esc(abs(x.started_at)) + '">' + esc(ago(x.started_at)) + '</td><td>' + esc(x.competitor_name) + '</td><td><span class="badge ' + (x.status === 'success' ? 'b-ok' : 'b-bad') + '">' + esc(x.status) + '</span></td><td class="hide-sm">' + esc(x.method || '—') + '</td><td class="hide-sm">' + x.items_found + '</td><td>' + x.new_articles + '</td><td class="hide-sm">' + x.duration_ms + ' ms</td><td>' + esc(x.error || '') + '</td></tr>').join('');
  return '<div class="head"><div><h1>Activity</h1><div class="sub">Every monitoring check, including failures</div></div></div><div class="card tablewrap">' +
    (S.checks.length ? '<table><thead><tr><th>When</th><th>Competitor</th><th>Result</th><th class="hide-sm">Method</th><th class="hide-sm">Items</th><th>New</th><th class="hide-sm">Duration</th><th>Error</th></tr></thead><tbody>' + rows + '</tbody></table>' : '<div class="empty">No checks recorded yet.</div>') + '</div>';
}
const PAGES = {dashboard: dashboardPage, competitors: competitorsPage, articles: articlesPage, activity: activityPage};
function render() {
  document.querySelectorAll('nav button').forEach((b) => b.classList.toggle('active', b.dataset.page === S.page));
  $('#banner').innerHTML = (S.error ? '<div class="error">Cannot reach the API: ' + esc(S.error) + ' <button class="btn small" data-action="retry">Retry</button></div>' : '') +
    (lsGet(BANNER_KEY) === '1' ? '' : '<div class="banner"><div><b>Demo mode.</b> Sample competitors are simulated and clearly labelled; any competitor you add is checked <b>live</b> (RSS/Atom feed or page links). Data lives in server memory and may reset when the instance restarts.</div><button data-action="dismiss-banner" aria-label="Dismiss">×</button></div>');
  $('#view').innerHTML = PAGES[S.page]();
}
function route() { const p = (location.hash.replace(/^#\/?/, '') || 'dashboard'); S.page = PAGES[p] ? p : 'dashboard'; render(); }

// ---------------------------------------------------------------- modals
function closeModal() { $('#modal-root').innerHTML = ''; }
function openCompetitorModal(c) {
  const edit = !!c;
  $('#modal-root').innerHTML = '<div class="modal-bg" data-action="close-bg"><div class="modal" role="dialog" aria-modal="true" aria-label="' + (edit ? 'Edit' : 'Add') + ' competitor"><h2>' + (edit ? 'Edit competitor' : 'Add competitor') + '</h2><form id="comp-form" novalidate>' +
    '<div class="field"><label for="f-name">Name</label><input id="f-name" name="name" maxlength="80" required value="' + esc(c ? c.name : '') + '" placeholder="Acme Corp"><div class="err" data-err="name"></div></div>' +
    '<div class="field"><label for="f-site">Website or blog URL</label><input id="f-site" name="website_url" type="url" required value="' + esc(c ? c.website_url : '') + '" placeholder="https://example.com/blog"><div class="err" data-err="website_url"></div></div>' +
    '<div class="field"><label for="f-feed">Feed URL <span class="sub">(optional)</span></label><input id="f-feed" name="feed_url" type="url" value="' + esc(c && c.feed_url ? c.feed_url : '') + '" placeholder="https://example.com/feed.xml"><div class="hint">Leave empty: the feed is discovered automatically; if there is none, article links on the page are used.</div><div class="err" data-err="feed_url"></div></div>' +
    '<div class="field"><label><input type="checkbox" name="enabled" ' + (!c || c.enabled ? 'checked' : '') + ' style="width:auto"> Monitoring enabled</label></div><div class="err" data-err="_form"></div>' +
    '<div class="foot"><button type="button" class="btn" data-action="close">Cancel</button><button type="submit" class="btn primary" id="save-btn">' + (edit ? 'Save changes' : 'Add competitor') + '</button></div></form></div></div>';
  $('#comp-form').dataset.id = edit ? c.id : '';
  setTimeout(() => { const el = $('#f-name'); if (el) el.focus(); }, 0);
}
function openArticle(id) {
  api('GET', '/articles/' + id).then((a) => {
    const dl = [['Competitor', esc(a.competitor_name || '') + ' ' + (a.competitor_kind ? kindBadge(a.competitor_kind) : '')], ['Status', a.status === 'new' ? 'Detected as new after monitoring began' : 'Baseline - already existed at the first check (no delay is calculated)'],
      ['Published', esc(abs(a.published_at)) + (a.published_at ? ' <span class="sub">(source time)</span>' : '')], ['First discovered', esc(abs(a.discovered_at))],
      ['Detection delay', delayBadge(a.detection_delay_seconds) + (a.detection_delay_seconds != null ? ' <span class="sub">' + esc(a.detection_delay_seconds) + ' seconds exactly (discovery − publication)</span>' : '')],
      ['Detection method', esc(a.method)], ['Author', esc(a.author || '—')], ['Tags', a.tags.length ? a.tags.map((t) => '<span class="badge b-gray">' + esc(t) + '</span>').join(' ') : '—'],
      ['Source URL', '<a href="' + esc(a.url) + '" target="_blank" rel="noopener noreferrer">' + esc(a.url) + '</a>']];
    $('#modal-root').innerHTML = '<div class="modal-bg" data-action="close-bg"><div class="modal" role="dialog" aria-modal="true" aria-label="Article details"><h2>' + esc(a.title) + '</h2>' + (a.summary ? '<p class="sub" style="font-size:14px">' + esc(a.summary) + '</p>' : '') +
      '<dl class="kv">' + dl.map((r) => '<dt>' + r[0] + '</dt><dd>' + r[1] + '</dd>').join('') + '</dl><div class="foot"><a class="btn primary" href="' + esc(a.url) + '" target="_blank" rel="noopener noreferrer" style="text-decoration:none">Open original</a><button class="btn" data-action="close">Close</button></div></div></div>';
  }).catch((e) => toast(e.message, 'bad'));
}

// ---------------------------------------------------------------- actions
async function checkOne(id) {
  S.busy[id] = true; render();
  try {
    const r = await api('POST', '/competitors/' + id + '/check'); const k = r.check;
    if (k.status === 'success') toast(r.competitor.name + ': ' + k.items_found + ' item(s) found via ' + k.method + ', ' + k.new_articles + ' new', 'ok'); else toast(r.competitor.name + ' failed: ' + k.error, 'bad');
  } catch (e) { toast(e.message, 'bad'); }
  delete S.busy[id]; await refresh();
}
async function checkAll(quiet) {
  if (S.busy.all) return; S.busy.all = true; render();
  try {
    const r = await api('POST', '/check-all');
    if (!quiet || r.new_articles || r.failed) toast('Checked ' + r.checked + ' competitor(s): ' + r.new_articles + ' new article(s)' + (r.failed ? ', ' + r.failed + ' failed' : ''), r.failed ? 'bad' : 'ok');
  } catch (e) { toast(e.message, 'bad'); }
  delete S.busy.all; await refresh();
}
async function saveCompetitor(form) {
  const id = form.dataset.id, f = new FormData(form);
  const body = {name: f.get('name') || '', website_url: f.get('website_url') || '', feed_url: f.get('feed_url') || null, enabled: f.get('enabled') === 'on'};
  form.querySelectorAll('[data-err]').forEach((e) => { e.textContent = ''; });
  const btn = $('#save-btn'); btn.disabled = true;
  try {
    await (id ? api('PUT', '/competitors/' + id, body) : api('POST', '/competitors', body));
    closeModal(); toast(id ? 'Competitor updated' : 'Competitor added - press Check to run its first check', 'ok'); await refresh(); backupLive();
  } catch (e) {
    const slot = form.querySelector('[data-err="' + (e.field || '_form') + '"]') || form.querySelector('[data-err="_form"]'); slot.textContent = e.message; btn.disabled = false;
  }
}
const ACTIONS = {
  nav: (b) => { location.hash = '#/' + b.dataset.page; },
  retry: () => refresh(), 'dismiss-banner': () => { lsSet(BANNER_KEY, '1'); render(); },
  add: () => openCompetitorModal(null), edit: (b) => openCompetitorModal(S.competitors.find((c) => String(c.id) === b.dataset.id)),
  'check-one': (b) => checkOne(b.dataset.id), 'check-all': () => checkAll(false),
  toggle: async (b) => { const c = S.competitors.find((x) => String(x.id) === b.dataset.id); try { await api('PUT', '/competitors/' + c.id, {name: c.name, website_url: c.website_url, feed_url: c.feed_url, enabled: !c.enabled}); await refresh(); backupLive(); } catch (e) { toast(e.message, 'bad'); } },
  delete: async (b) => { const c = S.competitors.find((x) => String(x.id) === b.dataset.id); if (!window.confirm('Delete "' + c.name + '" and its articles?')) return; try { await api('DELETE', '/competitors/' + c.id); toast('Deleted', 'ok'); await refresh(); backupLive(); } catch (e) { toast(e.message, 'bad'); } },
  'open-article': (b) => openArticle(b.dataset.id), close: closeModal,
  'close-bg': (b, e) => { if (e.target === b) closeModal(); },
  'more-articles': () => { S.limit += 30; refresh(); },
  'reset-demo': async () => { if (!window.confirm('Reset to the sample data? Competitors you added will be removed.')) return; try { await api('POST', '/demo/reset'); lsSet(BACKUP_KEY, '[]'); toast('Demo data reset', 'ok'); await refresh(); } catch (e) { toast(e.message, 'bad'); } }
};
document.addEventListener('click', (e) => { const b = e.target.closest('[data-action]'); if (!b) return; if (b.tagName === 'A' && b.dataset.action === 'reset-demo') e.preventDefault(); const fn = ACTIONS[b.dataset.action]; if (fn) fn(b, e); });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); if ((e.key === 'Enter') && e.target.matches && e.target.matches('.row[data-action]')) openArticle(e.target.dataset.id); });
document.addEventListener('submit', (e) => { if (e.target.id === 'comp-form') { e.preventDefault(); saveCompetitor(e.target); } });
let timer = null, autoTimer = null;
document.addEventListener('input', (e) => { if (e.target.id === 'f-q') { clearTimeout(timer); timer = setTimeout(() => { S.filters.q = e.target.value.trim(); S.limit = 30; refresh().then(() => { const el = $('#f-q'); if (el) { el.focus(); el.setSelectionRange(el.value.length, el.value.length); } }); }, 250); } });
document.addEventListener('change', (e) => {
  if (e.target.id === 'f-comp') { S.filters.competitor_id = e.target.value; S.limit = 30; refresh(); }
  if (e.target.id === 'f-status') { S.filters.status = e.target.value; S.limit = 30; refresh(); }
  if (e.target.id === 'auto') { lsSet(AUTO_KEY, e.target.checked ? '1' : '0'); setAuto(); if (e.target.checked) toast('Auto-check on: every 5 minutes while this page stays open', 'ok'); }
});
function setAuto() { clearInterval(autoTimer); if (lsGet(AUTO_KEY) === '1') autoTimer = setInterval(() => checkAll(true), 300000); }
window.addEventListener('hashchange', route);
(async function init() { await restoreIfNeeded(); route(); await refresh(); backupLive(); setAuto(); })();
})();
</script>
</body>
</html>
'''
