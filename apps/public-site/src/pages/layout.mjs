// Shared page shell: head, header, navigation, footer.

import {esc, fmtDate} from '../lib/html.mjs';

const NAV = [
  ['feed', 'Live feed', 'feed/'],
  ['countries', 'Countries', 'countries/'],
];

export function layout(ctx, {title, description, nav = '', body, scripts = [], bodyClass = '', app = false}) {
  const {url, legacy, asof} = ctx;
  const fullTitle = title ? `${title} · SENTINEL` : 'SENTINEL · Civil–military monitor for Latin America and the Caribbean';
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>${esc(fullTitle)}</title>
<meta name="description" content="${esc(description || 'SENTINEL tracks civil–military relations, political stability and security events across 25 countries in Latin America and the Caribbean.')}">
<meta name="color-scheme" content="light dark">
<meta name="robots" content="noindex, nofollow">
<link rel="icon" href="${legacy}assets/icons/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="${ctx.asset('styles/site.css')}">
</head>
<body class="${bodyClass}${app ? ' app' : ''}">
<a class="visually-hidden" href="#view">Skip to content</a>
<div class="preview-bar" role="note"><div class="wrap">Preview of the redesigned SENTINEL. <a href="${legacy}">Return to the current site</a></div></div>
<header class="site-head" id="site-head">
  <div class="wrap">
    <a class="wordmark" href="${url('')}"><span class="wm">SENTINEL<i>·</i></span><span class="tag">Civil–military monitor · Latin America &amp; the Caribbean</span></a>
    <nav class="site-nav" aria-label="Site">
      ${NAV.map(([key, label, href]) => `<a href="${url(href)}"${nav === key ? ' aria-current="page"' : ''}>${label}</a>`).join('\n      ')}
      <a href="${legacy}#transnational">Organized crime</a>
      <a href="${legacy}#us">US security</a>
      <a href="${legacy}#about">About</a>
      <a class="console-link nav-login" href="${legacy}apps/analyst-console/" title="Invite-only workspace for SENTINEL analysts">
        <svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="7" width="10" height="7" rx="1.2" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>
        Analyst login</a>
    </nav>
    <div class="head-right">
      <div class="fresh"><span class="pulse" aria-hidden="true"></span><span>Updated ${esc(fmtDate(asof))}</span></div>
    </div>
  </div>
</header>
<main id="view">${body}</main>
${app ? '' : `<footer class="site-foot" id="site-foot">
  <div class="wrap">
    <span>SENTINEL · Public event layer compiled from open-source reporting. Machine-coded records are labeled as such.</span>
    <span><a href="${legacy}#about">About</a> · <a href="${legacy}privacy.html">Privacy</a> · <a href="${legacy}terms.html">Terms</a> · <a href="https://github.com/hjmoncrieff/sentinel">Source</a></span>
  </div>
</footer>`}
${scripts.map(s => `<script type="module" src="${ctx.asset(`client/${s}`)}"></script>`).join('\n')}
</body>
</html>
`;
}
