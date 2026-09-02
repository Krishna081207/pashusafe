import React from 'react';
import { useTranslation } from 'react-i18next';

export default function LanguageSelector() {
  const { i18n } = useTranslation();

  const handleLanguageChange = (e) => {
    i18n.changeLanguage(e.target.value);
  };

  return (
    <div className="language-selector">
      <select 
        value={i18n.language.startsWith('hi') ? 'hi' : 'en'} 
        onChange={handleLanguageChange}
        aria-label="Select Language"
      >
        <option value="en">English</option>
        <option value="hi">हिंदी (Hindi)</option>
      </select>
    </div>
  );
}