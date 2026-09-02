import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import en from './locale/en.json';
import hi from './locale/hi.json';

i18n
  .use(LanguageDetector) // Remembers user choice in localStorage
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      hi: { translation: hi }
    },
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false // React already protects against XSS
    }
  });

export default i18n;