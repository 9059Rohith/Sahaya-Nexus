'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Language } from '@/lib/i18n';

type Invitation = { id: string; organization_name: string };
type Member = { id: string; user_id: string; name: string; email: string; status: string };
const labels = {
  en: { invitations: 'Organization invitations', join: 'Join organization', members: 'Team members', invite: 'Invite registered account', email: 'Account email', send: 'Send in-app invitation', remove: 'Remove', invited: 'Invited', active: 'Active', note: 'Invitations appear inside Sahaya for registered accounts. No external email is sent.' },
  hi: { invitations: 'संगठन निमंत्रण', join: 'संगठन से जुड़ें', members: 'टीम सदस्य', invite: 'पंजीकृत खाते को आमंत्रित करें', email: 'खाते का ईमेल', send: 'ऐप में निमंत्रण भेजें', remove: 'हटाएँ', invited: 'आमंत्रित', active: 'सक्रिय', note: 'पंजीकृत खाते को सहाय में निमंत्रण दिखता है। बाहरी ईमेल नहीं भेजा जाता।' },
  ta: { invitations: 'நிறுவன அழைப்புகள்', join: 'நிறுவனத்தில் சேரவும்', members: 'குழு உறுப்பினர்கள்', invite: 'பதிவு செய்த கணக்கை அழைக்கவும்', email: 'கணக்கு மின்னஞ்சல்', send: 'செயலியில் அழைப்பு அனுப்பு', remove: 'நீக்கு', invited: 'அழைக்கப்பட்டார்', active: 'செயலில்', note: 'பதிவு செய்த கணக்கில் சஹாயாவுக்குள் அழைப்பு தோன்றும். வெளி மின்னஞ்சல் அனுப்பப்படாது.' },
  ml: { invitations: 'സ്ഥാപന ക്ഷണങ്ങൾ', join: 'സ്ഥാപനത്തിൽ ചേരുക', members: 'സംഘാംഗങ്ങൾ', invite: 'രജിസ്റ്റർ ചെയ്ത അക്കൗണ്ടിനെ ക്ഷണിക്കുക', email: 'അക്കൗണ്ട് ഇമെയിൽ', send: 'ആപ്പിൽ ക്ഷണം അയയ്ക്കുക', remove: 'നീക്കുക', invited: 'ക്ഷണിച്ചു', active: 'സജീവം', note: 'രജിസ്റ്റർ ചെയ്ത അക്കൗണ്ടിൽ സഹായയ്ക്കുള്ളിൽ ക്ഷണം കാണും. പുറത്തേക്ക് ഇമെയിൽ അയയ്ക്കില്ല.' },
} as const;

export function OrganizationInvitations({ language, onAccepted }: { language: Language; onAccepted: () => void }) {
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [error, setError] = useState('');
  const words = labels[language];
  useEffect(() => { api<Invitation[]>('/organizations/invitations').then(setInvitations).catch(e => setError((e as Error).message)); }, []);
  async function accept(id: string) {
    try { await api(`/organizations/invitations/${id}/accept`, { method: 'POST' }); setInvitations(current => current.filter(item => item.id !== id)); onAccepted(); setError(''); }
    catch (e) { setError((e as Error).message); }
  }
  if (!invitations.length && !error) return null;
  return <div className="panel section-spaced"><h2>{words.invitations}</h2>{invitations.map(item => <div className="review-row" key={item.id}><strong>{item.organization_name}</strong><button className="button primary inline" onClick={() => accept(item.id)}>{words.join}</button></div>)}{error && <p className="error" role="alert">{error}</p>}</div>;
}

export function OrganizationMembers({ organizationId, language }: { organizationId: string; language: Language }) {
  const [members, setMembers] = useState<Member[]>([]);
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const words = labels[language];
  async function refresh() { setMembers(await api<Member[]>(`/organizations/${organizationId}/members`)); }
  useEffect(() => { let current = true; api<Member[]>(`/organizations/${organizationId}/members`).then(rows => { if (current) setMembers(rows); }).catch(e => { if (current) setError((e as Error).message); }); return () => { current = false; }; }, [organizationId]);
  async function invite(event: React.FormEvent) {
    event.preventDefault();
    try { await api(`/organizations/${organizationId}/members`, { method: 'POST', body: JSON.stringify({ email }) }); setEmail(''); await refresh(); setError(''); }
    catch (e) { setError((e as Error).message); }
  }
  async function remove(member: Member) {
    try { await api(`/organizations/${organizationId}/members/${member.user_id}`, { method: 'DELETE' }); await refresh(); setError(''); }
    catch (e) { setError((e as Error).message); }
  }
  return <div className="organization-members"><h3>{words.members}</h3><p className="muted">{words.note}</p><form className="form-stack" onSubmit={invite}><label>{words.email}<input type="email" required value={email} onChange={event => setEmail(event.target.value)} /></label><button className="button secondary inline">{words.send}</button></form>{members.map(member => <div className="review-row" key={member.id}><div><strong>{member.name}</strong><p>{member.email} · {member.status === 'ACTIVE' ? words.active : words.invited}</p></div><button className="text-button" onClick={() => remove(member)}>{words.remove}</button></div>)}{error && <p role="alert" className="error">{error}</p>}</div>;
}
