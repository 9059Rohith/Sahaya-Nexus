'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Language } from '@/lib/i18n';

type Message = { id: string; sender_id: string; sender_name: string; body: string; created_at: string };
type Labels = { title: string; lead: string; empty: string; write: string; send: string; older: string; refresh: string };

const labels: Record<Language, Labels> = {
  en: { title: 'Request conversation', lead: 'Only the requester, assigned responder and authorized staff can read these messages.', empty: 'No messages yet.', write: 'Write a message', send: 'Send message', older: 'Load older messages', refresh: 'Refresh messages' },
  hi: { title: 'अनुरोध वार्तालाप', lead: 'केवल अनुरोधकर्ता, सौंपे गए सहयोगी और अधिकृत कर्मचारी ये संदेश पढ़ सकते हैं।', empty: 'अभी कोई संदेश नहीं।', write: 'संदेश लिखें', send: 'संदेश भेजें', older: 'पुराने संदेश दिखाएँ', refresh: 'संदेश ताज़ा करें' },
  ta: { title: 'கோரிக்கை உரையாடல்', lead: 'கோரிக்கை அளித்தவர், ஒதுக்கப்பட்ட உதவியாளர் மற்றும் அங்கீகரிக்கப்பட்ட ஊழியர்கள் மட்டுமே இவற்றைப் படிக்க முடியும்.', empty: 'இன்னும் செய்திகள் இல்லை.', write: 'செய்தி எழுதுங்கள்', send: 'செய்தி அனுப்பு', older: 'பழைய செய்திகளை ஏற்று', refresh: 'செய்திகளைப் புதுப்பி' },
  ml: { title: 'അഭ്യർത്ഥന സംഭാഷണം', lead: 'അഭ്യർത്ഥകൻ, നിയോഗിച്ച സഹായി, അംഗീകൃത ജീവനക്കാർ എന്നിവർക്ക് മാത്രമേ ഈ സന്ദേശങ്ങൾ വായിക്കാൻ കഴിയൂ.', empty: 'ഇതുവരെ സന്ദേശങ്ങളില്ല.', write: 'സന്ദേശം എഴുതുക', send: 'സന്ദേശം അയയ്ക്കുക', older: 'പഴയ സന്ദേശങ്ങൾ കാണുക', refresh: 'സന്ദേശങ്ങൾ പുതുക്കുക' },
};

export function RequestMessages({ requestId, userId, language }: { requestId: string; userId: string; language: Language }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState('');
  const [page, setPage] = useState(1);
  const [hasOlder, setHasOlder] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const words = labels[language];

  useEffect(() => {
    let current = true;
    api<Message[]>(`/requests/${requestId}/messages`).then(rows => {
      if (current) { setMessages(rows); setHasOlder(rows.length === 50); setPage(1); }
    }).catch(e => { if (current) setError((e as Error).message); });
    return () => { current = false; };
  }, [requestId]);

  async function refresh() {
    setError('');
    try { const rows = await api<Message[]>(`/requests/${requestId}/messages`); setMessages(rows); setPage(1); setHasOlder(rows.length === 50); }
    catch (e) { setError((e as Error).message); }
  }

  async function older() {
    setError('');
    try {
      const rows = await api<Message[]>(`/requests/${requestId}/messages?page=${page + 1}`);
      setMessages(current => [...rows, ...current]);
      setPage(page + 1);
      setHasOlder(rows.length === 50);
    } catch (e) { setError((e as Error).message); }
  }

  async function send(event: React.FormEvent) {
    event.preventDefault();
    setError(''); setBusy(true);
    try {
      const sent = await api<Message>(`/requests/${requestId}/messages`, { method: 'POST', body: JSON.stringify({ body: draft }) });
      setMessages(current => [...current, sent]); setDraft('');
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  return <section className="panel request-messages" aria-label={words.title}>
    <div className="section-heading"><div><h2>{words.title}</h2><p>{words.lead}</p></div><button type="button" className="button secondary inline" onClick={refresh}>{words.refresh}</button></div>
    {hasOlder && <button type="button" className="text-button" onClick={older}>{words.older}</button>}
    {messages.length ? <ol className="message-list" aria-live="polite">{messages.map(item => <li key={item.id} className={item.sender_id === userId ? 'own-message' : ''}><strong>{item.sender_name}</strong><time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString()}</time><p>{item.body}</p></li>)}</ol> : <p className="muted">{words.empty}</p>}
    <form className="form-stack" onSubmit={send}><label>{words.write}<textarea required maxLength={2000} value={draft} onChange={event => setDraft(event.target.value)} /></label><button className="button primary inline" disabled={busy || !draft.trim()}>{words.send}</button></form>
    {error && <p role="alert" className="error">{error}</p>}
  </section>;
}
