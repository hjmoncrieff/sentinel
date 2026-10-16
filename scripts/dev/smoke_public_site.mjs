#!/usr/bin/env node
// Smoke check for the public site in a real browser, with no dependencies beyond Node 22+ and a local
// Chrome. It builds the site as the deploy does (the production build at /sentinel/ plus the repo's
// static pages), serves it, and opens one page of each kind at desktop and phone width in light and
// dark. It fails on script errors, failed requests and pages wider than the screen.
//
//   node scripts/dev/smoke_public_site.mjs            # build, check, report
//   CHROME=/path/to/chrome node scripts/dev/smoke_public_site.mjs

import {spawn, execFileSync} from 'node:child_process';
import {createServer} from 'node:http';
import {cpSync, existsSync, mkdtempSync, readFileSync, rmSync, statSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..');
const CHROME = process.env.CHROME || ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/usr/bin/google-chrome', '/usr/bin/chromium'].find(existsSync);
if (!CHROME) { console.error('No Chrome found; set CHROME=/path/to/chrome.'); process.exit(2); }

const PAGES = ['', 'headlines/', 'feed/', 'countries/', 'countries/col/', 'countries/hti/', 'organized-crime/', 'us-security/', 'explore/', 'about/', 'privacy.html', '404.html'];
const VIEWS = [{name: 'desktop', width: 1360, height: 900, mobile: false}, {name: 'phone', width: 390, height: 844, mobile: true}];
const THEMES = ['light', 'dark'];

// Build into a temporary copy of the deployed layout.
const tmp = mkdtempSync(path.join(tmpdir(), 'sentinel-smoke-'));
const site = path.join(tmp, 'sentinel');
execFileSync(process.execPath, [path.join(ROOT, 'apps/public-site/build.mjs'), '--out', site, '--base', '/sentinel/', '--production'], {cwd: ROOT, stdio: 'ignore'});
for (const f of ['assets', 'robots.txt', 'sitemap.xml', 'site.webmanifest', '404.html', 'privacy.html', 'terms.html', 'thank-you.html']) cpSync(path.join(ROOT, f), path.join(site, f), {recursive: true});

const TYPES = {'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.webmanifest': 'application/manifest+json', '.txt': 'text/plain'};
const server = createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  let f = path.join(tmp, p);
  if (existsSync(f) && statSync(f).isDirectory()) f = path.join(f, 'index.html');
  if (!f.startsWith(tmp) || !existsSync(f)) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, {'content-type': TYPES[path.extname(f)] || 'application/octet-stream'});
  res.end(readFileSync(f));
}).listen(0, '127.0.0.1');
await new Promise(r => server.once('listening', r));
const base = `http://127.0.0.1:${server.address().port}/sentinel/`;

const port = 9400 + Math.floor(Math.random() * 400);
const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${path.join(tmp, 'chrome')}`, '--no-first-run', 'about:blank'], {stdio: 'ignore'});
const sleep = ms => new Promise(r => setTimeout(r, ms));
let target;
for (let i = 0; i < 60 && !target; i++) { try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(t => t.type === 'page'); } catch { await sleep(250); } }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
let seq = 0;
const pending = new Map(), problems = [];
let current = '';
ws.onmessage = m => {
  const d = JSON.parse(m.data);
  if (d.id && pending.has(d.id)) { pending.get(d.id)(d.result); pending.delete(d.id); return; }
  if (d.method === 'Runtime.exceptionThrown') problems.push(`${current}: script error: ${d.params.exceptionDetails.exception?.description?.split('\n')[0] || d.params.exceptionDetails.text}`);
  if (d.method === 'Runtime.consoleAPICalled' && d.params.type === 'error') problems.push(`${current}: console.error: ${d.params.args.map(a => a.value ?? a.description).join(' ')}`);
  if (d.method === 'Network.responseReceived' && d.params.response.status >= 400 && d.params.response.url.startsWith(base)) problems.push(`${current}: HTTP ${d.params.response.status} ${d.params.response.url.replace(base, '/')}`);
  if (d.method === 'Network.loadingFailed' && !d.params.canceled && d.params.type !== 'Ping') problems.push(`${current}: request failed (${d.params.errorText})`);
};
const send = (method, params = {}) => new Promise(r => { const id = ++seq; pending.set(id, r); ws.send(JSON.stringify({id, method, params})); });
const evaluate = async expr => (await send('Runtime.evaluate', {expression: expr, returnByValue: true, awaitPromise: true}))?.result?.value;
await send('Runtime.enable'); await send('Network.enable'); await send('Page.enable');

let checked = 0;
for (const view of VIEWS) for (const theme of THEMES) {
  await send('Emulation.setDeviceMetricsOverride', {width: view.width, height: view.height, deviceScaleFactor: 1, mobile: view.mobile});
  await send('Emulation.setTouchEmulationEnabled', {enabled: view.mobile});
  await send('Emulation.setEmulatedMedia', {features: [{name: 'prefers-color-scheme', value: theme}]});
  for (const page of PAGES) {
    current = `${page || '/'} [${view.name}, ${theme}]`;
    await send('Page.navigate', {url: base + page});
    await sleep(page === 'feed/' ? 2500 : 900);
    const wide = await evaluate(`(() => { const w = document.documentElement.clientWidth; const over = [...document.querySelectorAll('body *')].filter(el => { const r = el.getBoundingClientRect(); return r.width && r.right > w + 1 && getComputedStyle(el).position !== 'fixed' && !el.closest('.tbl-scroll, .plstrip, .act-chart, [style*="overflow"], pre'); }).slice(0, 3).map(el => el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\\s+/).join('.') : '')); return document.documentElement.scrollWidth > w + 1 ? 'page ' + document.documentElement.scrollWidth + 'px wide: ' + over.join(', ') : ''; })()`);
    if (wide) problems.push(`${current}: ${wide}`);
    checked++;
  }
}

ws.close(); chrome.kill(); server.close();
rmSync(tmp, {recursive: true, force: true});
const unique = [...new Set(problems)];
console.log(`${checked} page views checked (${PAGES.length} pages × ${VIEWS.length} widths × ${THEMES.length} themes).`);
if (unique.length) { console.log(unique.map(p => `  ✗ ${p}`).join('\n')); process.exit(1); }
console.log('  ✓ no script errors, failed requests or sideways overflow');
