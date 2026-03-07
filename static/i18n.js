/**
 * Phase 8: Lightweight i18n module for the existing static HTML pages.
 *
 * Usage
 * -----
 *   // In HTML — mark translatable text:
 *   <h2 data-i18n="login">Login</h2>
 *   <input placeholder="Username" data-i18n-placeholder="username">
 *   <button aria-label="Close" data-i18n-aria-label="close">X</button>
 *
 *   // In JS — init once (reads pref_lang from localStorage → navigator.language → 'en'):
 *   await I18n.init();
 *
 *   // Translate a key programmatically (falls back to the key itself):
 *   const label = I18n.t('login');
 *
 *   // Re-apply translations after dynamic DOM changes:
 *   I18n.apply();
 *
 *   // Switch language at runtime:
 *   await I18n.setLocale('es');
 *
 * Locale files live in /static/locales/{locale}.json.
 * Supported locales: en, es, fr (add more by dropping a JSON file).
 */

const I18n = (() => {
  let _dict = {};
  let _locale = 'en';

  const SUPPORTED = new Set(['en', 'es', 'fr']);

  function _detectLocale() {
    // Priority: saved preference → browser language → fallback
    const saved = localStorage.getItem('pref_lang');
    if (saved && SUPPORTED.has(saved)) return saved;

    const browser = (navigator.language || 'en').split('-')[0].toLowerCase();
    return SUPPORTED.has(browser) ? browser : 'en';
  }

  async function _load(locale) {
    try {
      const res = await fetch(`/static/locales/${locale}.json`);
      if (res.ok) {
        _dict = await res.json();
        _locale = locale;
      } else {
        _dict = {};
      }
    } catch (_) {
      _dict = {};
    }
  }

  /** Return the translation for *key*, falling back to *fallback* or the key. */
  function t(key, fallback) {
    return _dict[key] || fallback || key;
  }

  /** Walk the DOM and replace content / attributes for all i18n-annotated elements. */
  function apply() {
    // Text content:  data-i18n="key"
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const val = t(el.dataset.i18n);
      if (el.childElementCount === 0) {
        el.textContent = val;
      } else {
        // Preserve child elements — only update the first text node
        for (const node of el.childNodes) {
          if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
            node.textContent = val;
            break;
          }
        }
      }
    });

    // Placeholder:  data-i18n-placeholder="key"
    document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      el.placeholder = t(el.dataset.i18nPlaceholder);
    });

    // aria-label:   data-i18n-aria-label="key"
    document.querySelectorAll('[data-i18n-aria-label]').forEach((el) => {
      el.setAttribute('aria-label', t(el.dataset.i18nAriaLabel));
    });

    // title attr:   data-i18n-title="key"
    document.querySelectorAll('[data-i18n-title]').forEach((el) => {
      el.setAttribute('title', t(el.dataset.i18nTitle));
    });

    // Update <html lang> so screen readers know the language
    document.documentElement.lang = _locale;
  }

  /** Initialise: detect locale, load translations, apply to DOM. */
  async function init() {
    const locale = _detectLocale();
    await _load(locale);
    apply();
  }

  /** Switch to a new locale, persist the preference, and re-apply to the DOM. */
  async function setLocale(locale) {
    if (!SUPPORTED.has(locale)) return;
    localStorage.setItem('pref_lang', locale);
    await _load(locale);
    apply();
  }

  return {
    init,
    apply,
    setLocale,
    t,
    get locale() {
      return _locale;
    },
  };
})();
