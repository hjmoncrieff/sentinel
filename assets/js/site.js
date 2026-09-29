/*
 * Shared public-site configuration, consent, and analytics for every page
 * (dashboard, 404, privacy, terms, thank-you). Load before page scripts.
 *
 * Analytics stays OFF until `analytics.code` is set. When it is set, nothing
 * loads until the visitor accepts in the consent banner; the choice is kept in
 * localStorage under CONSENT_KEY and can be reset from the privacy page.
 */
(function () {
  'use strict';

  var SITE = window.SENTINEL_SITE = {
    name: 'SENTINEL',
    url: 'https://hjmoncrieff.github.io/sentinel/',
    repoUrl: 'https://github.com/hjmoncrieff/sentinel',
    issuesUrl: 'https://github.com/hjmoncrieff/sentinel/issues',
    formEndpoint: 'https://formspree.io/f/xkopdkwd',
    analytics: {
      // Privacy-friendly, cookieless GoatCounter. Set `code` to the GoatCounter
      // site code (e.g. 'sentinel' for https://sentinel.goatcounter.com) to enable.
      provider: 'goatcounter',
      code: ''
    }
  };

  var CONSENT_KEY = 'sentinel-analytics-consent';

  function readConsent() {
    try { return window.localStorage.getItem(CONSENT_KEY); } catch (e) { return null; }
  }

  function writeConsent(value) {
    try { window.localStorage.setItem(CONSENT_KEY, value); } catch (e) { /* storage blocked: ask again next visit */ }
  }

  function analyticsEnabled() {
    return !!(SITE.analytics && SITE.analytics.provider === 'goatcounter' && SITE.analytics.code);
  }

  function loadAnalytics() {
    if (!analyticsEnabled() || document.querySelector('script[data-goatcounter]')) return;
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://gc.zgo.at/count.js';
    s.setAttribute('data-goatcounter', 'https://' + SITE.analytics.code + '.goatcounter.com/count');
    document.head.appendChild(s);
  }

  function showBanner() {
    if (document.getElementById('consent-banner')) return;
    var bar = document.createElement('div');
    bar.id = 'consent-banner';
    bar.className = 'consent-banner';
    bar.setAttribute('role', 'region');
    bar.setAttribute('aria-label', 'Analytics consent');
    bar.innerHTML =
      '<p class="consent-copy">SENTINEL can count anonymous page views to see which views are used. ' +
      // Every page sits at the site root (404.html uses <base>), so this resolves everywhere.
      'No cookies and no personal profiles. <a href="privacy.html">Privacy policy</a></p>' +
      '<div class="consent-actions">' +
      '<button type="button" class="consent-btn consent-decline">Decline</button>' +
      '<button type="button" class="consent-btn consent-accept">Allow</button>' +
      '</div>';
    bar.querySelector('.consent-accept').addEventListener('click', function () {
      writeConsent('granted');
      bar.remove();
      loadAnalytics();
    });
    bar.querySelector('.consent-decline').addEventListener('click', function () {
      writeConsent('denied');
      bar.remove();
    });
    document.body.appendChild(bar);
  }

  SITE.resetConsent = function () {
    try { window.localStorage.removeItem(CONSENT_KEY); } catch (e) { /* ignore */ }
    if (analyticsEnabled()) showBanner();
  };
  SITE.analyticsEnabled = analyticsEnabled;
  SITE.consentState = readConsent;

  function init() {
    if (!analyticsEnabled()) return;
    var consent = readConsent();
    if (consent === 'granted') loadAnalytics();
    else if (consent !== 'denied') showBanner();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
