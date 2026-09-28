import type { Language } from './i18n';

const labels: Record<Language, string> = {
  en: 'Closed request content retention (days; leave blank to disable)',
  hi: 'बंद अनुरोध की सामग्री रखने की अवधि (दिन; बंद रखने के लिए खाली छोड़ें)',
  ta: 'முடிக்கப்பட்ட கோரிக்கைத் தகவல் சேமிப்பு (நாட்கள்; முடக்க காலியாக விடவும்)',
  ml: 'പൂർത്തിയായ അഭ്യർത്ഥനയുടെ വിവരങ്ങൾ സൂക്ഷിക്കുന്ന കാലം (ദിവസം; ഒഴിവാക്കിയാൽ പ്രവർത്തിക്കില്ല)',
};

export function retentionCopy(language: Language): string { return labels[language]; }
