// Shared page shell: head, header, navigation, footer.

import {esc, fmtDate} from '../lib/html.mjs';

// The live site and the preview share one menu; ctx.url() points each entry at the right site.
const NAV = [
  ['feed', 'Live feed', 'feed/'],
  ['countries', 'Countries', 'countries/'],
  ['explore', 'Explore', 'explore/'],
  ['oc', 'Organized crime', 'organized-crime/'],
  ['us', 'US security', 'us-security/'],
  ['about', 'About', 'about/'],
];


// Shared with the dashboard: an explicit choice is stored; without one the system setting applies.
const THEME_BOOT = `<script>try{var t=localStorage.getItem('sentinel-theme');if(t==='light'||t==='dark')document.documentElement.dataset.theme=t}catch(e){}</script>`;
const THEME_BUTTON = `<button class="theme-toggle" id="theme-toggle" type="button" aria-label="Switch to dark mode" title="Switch light / dark mode">
        <svg class="i-moon" viewBox="0 0 16 16" aria-hidden="true"><path d="M13.5 9.8A5.6 5.6 0 0 1 6.2 2.5a5.6 5.6 0 1 0 7.3 7.3Z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>
        <svg class="i-sun" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="3" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M8 1.5v1.6M8 12.9v1.6M1.5 8h1.6M12.9 8h1.6M3.4 3.4l1.1 1.1M11.5 11.5l1.1 1.1M3.4 12.6l1.1-1.1M11.5 4.5l1.1-1.1" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>
      </button>`;

export function layout(ctx, {title, description, nav = '', body, scripts = [], bodyClass = '', app = false}) {
  const {url, legacy, asof, live} = ctx;
  const navItems = NAV.map(([key, label, href]) => [key, label, url(href)]);
  const home = url('');
  const aboutHref = url('about/');
  const fullTitle = title ? `${title} · SENTINEL` : 'SENTINEL · Civil–military monitor for Latin America and the Caribbean';
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>${esc(fullTitle)}</title>
<meta name="description" content="${esc(description || 'SENTINEL tracks civil–military relations, political stability and security events across 25 countries in Latin America and the Caribbean.')}">
<meta name="color-scheme" content="light dark">
${live ? '' : '<meta name="robots" content="noindex, nofollow">\n'}${THEME_BOOT}
<link rel="icon" href="${legacy}assets/icons/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="${ctx.asset('styles/site.css')}">
</head>
<body class="${bodyClass}${app ? ' app' : ''}">
<a class="visually-hidden" href="#view">Skip to content</a>
${live ? '' : `<div class="preview-bar" role="note"><div class="wrap">Preview build of SENTINEL. <a href="${legacy}">Go to the live site</a></div></div>
`}<header class="site-head" id="site-head">
  <div class="wrap">
    <a class="wordmark" href="${home}"><span class="wm">SENTINEL<i>·</i></span><span class="tag">Civil–military monitor · Latin America &amp; the Caribbean</span></a>
    <nav class="site-nav" aria-label="Site">
      ${navItems.map(([key, label, href]) => `<a href="${href}"${nav === key ? ' aria-current="page"' : ''}>${label}</a>`).join('\n      ')}
      <a class="console-link nav-login" href="${legacy}apps/analyst-console/" title="Invite-only workspace for SENTINEL analysts">
        <svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="7" width="10" height="7" rx="1.2" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>
        Analyst login</a>
    </nav>
    <div class="head-right">
      <div class="fresh"><span class="pulse" aria-hidden="true"></span><span>Updated ${esc(fmtDate(asof))}</span></div>
      ${THEME_BUTTON}
    </div>
  </div>
</header>
<main id="view">${body}</main>
${app ? '' : `<footer class="site-foot" id="site-foot">
  <div class="wrap">
    <span>SENTINEL · Public event layer compiled from open-source reporting. Machine-coded records are labeled as such.</span>
    <span><a href="${aboutHref}">About and methodology</a> · <a href="${legacy}privacy.html">Privacy</a> · <a href="${legacy}terms.html">Terms</a> · <a href="https://github.com/hjmoncrieff/sentinel">Source</a></span>
  </div>
</footer>`}
${['theme.js', ...scripts].map(s => `<script type="module" src="${ctx.asset(`client/${s}`)}"></script>`).join('\n')}
</body>
</html>
`;
}
