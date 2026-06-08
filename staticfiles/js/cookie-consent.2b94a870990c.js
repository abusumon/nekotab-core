/**
 * NekoTab Cookie Consent Module
 * Production-grade consent management with cookie + localStorage dual storage.
 *
 * - Checks consent during initial page load without template inline scripts
 * - Sets a persistent cookie (180 days) with Path=/, SameSite=Lax, Secure
 * - Falls back to localStorage for quick synchronous reads
 * - Prevents FOUC / layout shift: banner starts display:none, shown only if needed
 * - Works across all subpaths, reloads, and incognito sessions
 */
(function (root) {
  'use strict';

  var COOKIE_NAME  = 'nekotab_consent';
  var LS_KEY       = 'cookie_consent';      // backward-compatible with existing key
  var MAX_AGE_DAYS = 180;
  var EUROPE_COUNTRY_CODES = {
    AL: true, AD: true, AM: true, AT: true, AZ: true,
    BY: true, BE: true, BA: true, BG: true, HR: true,
    CY: true, CZ: true, DK: true, EE: true, FI: true,
    FR: true, GE: true, DE: true, GR: true, HU: true,
    IS: true, IE: true, IT: true, XK: true, LV: true,
    LI: true, LT: true, LU: true, MT: true, MD: true,
    MC: true, ME: true, NL: true, MK: true, NO: true,
    PL: true, PT: true, RO: true, RU: true, SM: true,
    RS: true, SK: true, SI: true, ES: true, SE: true,
    CH: true, TR: true, UA: true, GB: true, VA: true
  };

  // ── Helpers ──────────────────────────────────────────────────

  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(?:^|;\\s*)' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : null;
  }

  function setCookie(name, value, days) {
    var maxAge = days * 24 * 60 * 60;
    var parts  = [
      name + '=' + encodeURIComponent(value),
      'path=/',
      'max-age=' + maxAge,
      'samesite=lax'
    ];
    // Set Secure flag on HTTPS
    if (location.protocol === 'https:') {
      parts.push('secure');
    }
    document.cookie = parts.join('; ');
  }

  function removeCookie(name) {
    document.cookie = name + '=; path=/; max-age=0; samesite=lax';
  }

  function getRequestCountryCode() {
    var html = document.documentElement;
    if (!html) return '';

    var code = html.getAttribute('data-country-code') || '';
    code = String(code).trim().toUpperCase();

    return /^[A-Z]{2}$/.test(code) ? code : '';
  }

  function shouldShowBannerForCountry(countryCode) {
    return !!EUROPE_COUNTRY_CODES[countryCode];
  }

  // ── Read consent (cookie first, then localStorage fallback) ──

  function readConsent() {
    var fromCookie = getCookie(COOKIE_NAME);
    if (fromCookie) return fromCookie;

    // Backward compat: read from localStorage (old implementation)
    try {
      var fromLS = localStorage.getItem(LS_KEY);
      if (fromLS) {
        // Migrate to cookie so it persists properly
        persistConsent(fromLS);
        return fromLS;
      }
    } catch (e) { /* private browsing / storage disabled */ }

    return null;
  }

  // ── Write consent to both stores ──

  function persistConsent(value) {
    setCookie(COOKIE_NAME, value, MAX_AGE_DAYS);
    try { localStorage.setItem(LS_KEY, value); } catch (e) { /* ignore */ }
  }

  // ── Public API ───────────────────────────────────────────────

  var NekoConsent = {

    /**
     * Shows banner only if no consent recorded.
     */
    init: function () {
      var consent = readConsent();
      var banner  = document.getElementById('cookie-consent');
      if (!banner) return;

      if (consent) {
        // Consent already given — keep banner hidden, load GA4 if accepted
        banner.style.display = 'none';
        if (consent === 'all') this._loadGA4();
      } else {
        var countryCode = getRequestCountryCode();

        if (shouldShowBannerForCountry(countryCode)) {
          // Europe: require explicit consent choice.
          banner.style.display = 'block';
        } else {
          // Non-Europe (or missing country header): auto-accept analytics.
          persistConsent('all');
          banner.style.display = 'none';
          this._loadGA4();
        }
      }
    },

    /**
     * User clicks "Accept All" / "Accept Analytics"
     */
    acceptAll: function () {
      persistConsent('all');
      this._hideBanner();
      this._loadGA4();
    },

    /**
     * User clicks "Essential Only" / "No Thanks"
     */
    acceptEssential: function () {
      persistConsent('essential');
      this._hideBanner();
    },

    /**
     * Read current consent state
     */
    getConsent: function () {
      return readConsent();
    },

    // ── Internal ──

    _hideBanner: function () {
      var banner = document.getElementById('cookie-consent');
      if (banner) banner.style.display = 'none';
    },

    _loadGA4: function () {
      try {
        if (window.__ga4_loaded) return;
        window.__ga4_loaded = true;

        var s   = document.createElement('script');
        s.id    = 'ga4-script';
        s.async = true;
        s.src   = 'https://www.googletagmanager.com/gtag/js?id=G-7KH41L8LQL';
        document.head.appendChild(s);

        window.dataLayer = window.dataLayer || [];
        function gtag() { dataLayer.push(arguments); }
        window.gtag = gtag;
        gtag('js', new Date());
        gtag('config', 'G-7KH41L8LQL');
      } catch (e) {
        // Blocked by adblock/ETP — fail silently
      }
    }
  };

  // Expose globally
  root.NekoConsent = NekoConsent;

  // Also expose legacy functions for backward compatibility
  root.acceptAllCookies = function () { NekoConsent.acceptAll(); };
  root.acceptEssentialOnly = function () { NekoConsent.acceptEssential(); };

  // Initialize once DOM is ready so templates don't need inline init calls.
  var _initialized = false;
  function initOnce() {
    if (_initialized) return;
    _initialized = true;
    NekoConsent.init();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initOnce);
  } else {
    initOnce();
  }

})(window);
