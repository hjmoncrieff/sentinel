#!/usr/bin/env node
// Build the public site as static files.
//
//   node apps/public-site/build.mjs [--out dist/public-site] [--base /] [--legacy /] [--origin https://host]
//
// --base    URL prefix the built site is served under (for example /sentinel/next/).
// --legacy  URL prefix of the current dashboard, for sections not rebuilt yet.
// --origin  Scheme and host the site is served from; used in the citation on record pages.
//
// Reads public layers only (data/published/, data/cleaned/us_assistance.json, the codebook). Writes pre-rendered pages, the stylesheet, the browser
// modules and data/feed.json. No dependencies: Vite, when used, only bundles the output.

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadModel, feedPayload} from './src/lib/model.mjs';
import {renderFront} from './src/pages/front.mjs';
import {renderCountries, renderCountry} from './src/pages/countries.mjs';
import {renderFeed} from './src/pages/feed.mjs';
import {renderEvent, renderEventRedirect} from './src/pages/event.mjs';
import {renderAbout} from './src/pages/about.mjs';
import {renderOrganizedCrime, renderUsSecurity} from './src/pages/topics.mjs';

const siteRoot = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(siteRoot, '..', '..');
const arg = (name, fallback) => { const i = process.argv.indexOf(`--${name}`); return i > 0 ? process.argv[i + 1] : fallback; };
const withSlash = s => (s.endsWith('/') ? s : s + '/');
const out = path.resolve(repoRoot, arg('out', 'dist/public-site'));
const base = withSlash(arg('base', '/'));
const legacy = withSlash(arg('legacy', '/'));
const origin = arg('origin', 'https://hjmoncrieff.github.io').replace(/\/$/, '');

const model = loadModel(repoRoot, siteRoot);
// Asset URLs carry a content hash so a deploy never serves a stale stylesheet or script.
const assetVersion = (() => {
  const hash = crypto.createHash('sha1');
  const walk = dir => { for (const e of fs.readdirSync(dir, {withFileTypes: true}).sort((a, b) => a.name.localeCompare(b.name))) { const p = path.join(dir, e.name); if (e.isDirectory()) walk(p); else hash.update(fs.readFileSync(p)); } };
  walk(path.join(siteRoot, 'src'));
  return hash.digest('hex').slice(0, 8);
})();
const ctx = {
  url: p => base + p,
  asset: p => `${base}assets/${p}?v=${assetVersion}`,
  legacy,
  origin,
  asof: model.asof,
  formEndpoint: 'https://formspree.io/f/xkopdkwd',
};

const write = (rel, content) => {
  const file = path.join(out, rel);
  fs.mkdirSync(path.dirname(file), {recursive: true});
  fs.writeFileSync(file, content);
};
const copyDir = (from, to) => {
  for (const entry of fs.readdirSync(from, {withFileTypes: true})) {
    const src = path.join(from, entry.name), dst = path.join(to, entry.name);
    if (entry.isDirectory()) copyDir(src, dst);
    else { fs.mkdirSync(to, {recursive: true}); fs.copyFileSync(src, dst); }
  }
};

fs.rmSync(out, {recursive: true, force: true});
write('index.html', renderFront(model, ctx));
write('feed/index.html', renderFeed(model, ctx));
write('countries/index.html', renderCountries(model, ctx));
for (const c of model.countries) write(`countries/${c.iso3.toLowerCase()}/index.html`, renderCountry(c, model, ctx));
write('about/index.html', renderAbout(model, ctx));
write('organized-crime/index.html', renderOrganizedCrime(model, ctx));
write('us-security/index.html', renderUsSecurity(model, ctx));
for (const e of model.events) write(`events/${e.id}/index.html`, renderEvent(e, model, ctx));
for (const [old, target] of Object.entries(model.aliases)) write(`events/${old}/index.html`, renderEventRedirect(target, ctx));
write('data/feed.json', JSON.stringify(feedPayload(model)));
copyDir(path.join(siteRoot, 'src', 'styles'), path.join(out, 'assets', 'styles'));
copyDir(path.join(siteRoot, 'src', 'client'), path.join(out, 'assets', 'client'));
copyDir(path.join(siteRoot, 'src', 'lib'), path.join(out, 'assets', 'lib'));
// Build-only modules must not ship to the browser.
for (const f of ['model.mjs', 'geo.mjs']) fs.rmSync(path.join(out, 'assets', 'lib', f), {force: true});

const pages = 6 + model.countries.length + model.events.length;
const feedKb = Math.round(fs.statSync(path.join(out, 'data', 'feed.json')).size / 1024);
console.log(`Built ${pages} pages → ${path.relative(repoRoot, out)} (base ${base}); ${model.events.length} events to ${model.asof}; feed.json ${feedKb} KB`);
