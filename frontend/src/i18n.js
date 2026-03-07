import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import HttpBackend from 'i18next-http-backend';

i18n
  .use(HttpBackend)
  .use(initReactI18next)
  .init({
    // Load locale files from /static/locales/ so the SPA shares translations
    // with the existing static pages. The backend also serves these files.
    backend: {
      loadPath: '/static/locales/{{lng}}.json',
    },
    lng: localStorage.getItem('pref_lang') || navigator.language?.split('-')[0] || 'en',
    fallbackLng: 'en',
    supportedLngs: ['en', 'es', 'fr'],
    interpolation: {
      escapeValue: false, // React already escapes values
    },
  });

export default i18n;
