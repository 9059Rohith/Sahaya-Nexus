import type { Language } from './i18n';

const labels: Record<Language, { loadMore: string }> = {
  en: { loadMore: 'Load more' },
  hi: { loadMore: 'और दिखाएँ' },
  ta: { loadMore: 'மேலும் காட்டு' },
  ml: { loadMore: 'കൂടുതൽ കാണിക്കുക' },
};

export function listCopy(language: Language): string { return labels[language].loadMore; }
