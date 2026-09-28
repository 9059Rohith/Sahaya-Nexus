import type { Language } from './i18n';

const en = {
  aiTitle: 'AI suggestions are reviewable',
  aiBody: 'Local rules or an optional local model suggest a category and fields. You review and edit them before submission. Staff make verification and assignment decisions.',
  sourceTitle: 'Records come from people using Sahaya',
  sourceBody: 'Requests, resources and organizations are entered by real users. Public impact counts only requester-confirmed outcomes recorded by staff. Empty systems show zero.',
  safetyTitle: 'Safety concerns can be reported',
  safetyBody: 'Use Help and Safety to report spam, fraud, privacy or safety concerns. Staff review the report and record a resolution.',
  auditTitle: 'Decisions leave a history',
  auditBody: 'Request timelines show status changes and reasons. Staff actions such as verification, matching settings and policy changes are recorded in an audit trail.',
} as const;

type Key = keyof typeof en;
const translations: Record<Exclude<Language, 'en'>, Record<Key, string>> = {
  hi: {
    aiTitle: 'AI सुझाव की समीक्षा की जा सकती है', aiBody: 'स्थानीय नियम या वैकल्पिक स्थानीय मॉडल श्रेणी और जानकारी सुझाते हैं। भेजने से पहले आप उन्हें जांच और बदल सकते हैं। सत्यापन और कार्य सौंपने का निर्णय कर्मचारी लेते हैं।',
    sourceTitle: 'रिकॉर्ड सहाय उपयोगकर्ताओं से आते हैं', sourceBody: 'अनुरोध, संसाधन और संगठन वास्तविक उपयोगकर्ता दर्ज करते हैं। सार्वजनिक प्रभाव में केवल आवेदक द्वारा पुष्ट और कर्मचारियों द्वारा दर्ज परिणाम गिने जाते हैं। खाली प्रणाली में शून्य दिखता है।',
    safetyTitle: 'सुरक्षा चिंताएँ रिपोर्ट की जा सकती हैं', safetyBody: 'स्पैम, धोखाधड़ी, गोपनीयता या सुरक्षा चिंता बताने के लिए सहायता और सुरक्षा खोलें। कर्मचारी रिपोर्ट की समीक्षा कर समाधान दर्ज करते हैं।',
    auditTitle: 'निर्णयों का इतिहास रहता है', auditBody: 'अनुरोध की समयरेखा में स्थिति और कारण दिखते हैं। सत्यापन, मिलान सेटिंग और नीति बदलाव जैसी कर्मचारी कार्रवाइयाँ ऑडिट रिकॉर्ड में दर्ज होती हैं।',
  },
  ta: {
    aiTitle: 'AI பரிந்துரைகளை ஆய்வு செய்யலாம்', aiBody: 'உள்ளூர் விதிகள் அல்லது விருப்பமான உள்ளூர் மாதிரி வகையையும் விவரங்களையும் பரிந்துரைக்கும். சமர்ப்பிப்பதற்கு முன் அவற்றை நீங்கள் ஆய்வு செய்து மாற்றலாம். சரிபார்ப்பு மற்றும் ஒதுக்கீட்டை பணியாளர்கள் முடிவு செய்கிறார்கள்.',
    sourceTitle: 'பதிவுகள் சஹாயா பயனர்களிடமிருந்து வருகின்றன', sourceBody: 'கோரிக்கைகள், வளங்கள் மற்றும் அமைப்புகளை உண்மையான பயனர்கள் பதிவு செய்கிறார்கள். கோரியவர் உறுதிசெய்து பணியாளர்கள் பதிவு செய்த விளைவுகள் மட்டுமே பொது தாக்கத்தில் எண்ணப்படும். காலியான அமைப்பில் பூஜ்ஜியம் காட்டப்படும்.',
    safetyTitle: 'பாதுகாப்புக் கவலைகளை புகாரளிக்கலாம்', safetyBody: 'தேவையற்ற செய்திகள், மோசடி, தனியுரிமை அல்லது பாதுகாப்புக் கவலைகளை உதவி மற்றும் பாதுகாப்பில் தெரிவிக்கவும். பணியாளர்கள் ஆய்வு செய்து தீர்வைப் பதிவு செய்கிறார்கள்.',
    auditTitle: 'முடிவுகளின் வரலாறு உள்ளது', auditBody: 'கோரிக்கை காலவரிசையில் நிலை மாற்றங்களும் காரணங்களும் தெரியும். சரிபார்ப்பு, பொருத்த அமைப்புகள், கொள்கை மாற்றங்கள் ஆகியவை தணிக்கைப் பதிவில் சேமிக்கப்படும்.',
  },
  ml: {
    aiTitle: 'AI നിർദേശങ്ങൾ പരിശോധിക്കാം', aiBody: 'പ്രാദേശിക നിയമങ്ങളോ ഐച്ഛിക പ്രാദേശിക മാതൃകയോ വിഭാഗവും വിവരങ്ങളും നിർദേശിക്കും. സമർപ്പിക്കുന്നതിന് മുമ്പ് നിങ്ങൾക്ക് അവ പരിശോധിച്ച് തിരുത്താം. സ്ഥിരീകരണവും നിയോഗവും ജീവനക്കാർ തീരുമാനിക്കും.',
    sourceTitle: 'രേഖകൾ സഹായ ഉപയോഗിക്കുന്നവരിൽ നിന്ന്', sourceBody: 'അഭ്യർത്ഥനകളും വിഭവങ്ങളും സ്ഥാപനങ്ങളും യഥാർത്ഥ ഉപയോക്താക്കളാണ് നൽകുന്നത്. അപേക്ഷകൻ സ്ഥിരീകരിച്ച് ജീവനക്കാർ രേഖപ്പെടുത്തിയ ഫലങ്ങൾ മാത്രമേ പൊതു ഫലത്തിൽ എണ്ണൂ. ശൂന്യ സംവിധാനത്തിൽ പൂജ്യം കാണിക്കും.',
    safetyTitle: 'സുരക്ഷാ ആശങ്കകൾ റിപ്പോർട്ട് ചെയ്യാം', safetyBody: 'സ്പാം, തട്ടിപ്പ്, സ്വകാര്യത, സുരക്ഷ എന്നിവയെക്കുറിച്ചുള്ള ആശങ്കകൾ സഹായവും സുരക്ഷയും വഴി അറിയിക്കാം. ജീവനക്കാർ പരിശോധിച്ച് പരിഹാരം രേഖപ്പെടുത്തും.',
    auditTitle: 'തീരുമാനങ്ങളുടെ ചരിത്രം സൂക്ഷിക്കുന്നു', auditBody: 'അഭ്യർത്ഥന സമയരേഖയിൽ നില മാറ്റങ്ങളും കാരണങ്ങളും കാണാം. സ്ഥിരീകരണം, പൊരുത്ത ക്രമീകരണം, നയ മാറ്റം എന്നിവ ഓഡിറ്റ് രേഖയിൽ സൂക്ഷിക്കും.',
  },
};

export function trustCopy(language: Language, key: Key): string {
  return language === 'en' ? en[key] : translations[language][key];
}
