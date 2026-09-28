'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Activity, ArrowRight, ArrowUpRight, Bell, BookOpen, CircleHelp, ClipboardList, Eye, EyeOff, HeartHandshake, Home, LogOut, MapPin, Menu, PlusSquare, Search, Settings, ShieldCheck, UserRound, X } from 'lucide-react';
import { api, Need, Organization, Resource, User } from '@/lib/api';
import { Language, languages, MessageKey, t } from '@/lib/i18n';
import { copy } from '@/lib/copy';
import { listCopy } from '@/lib/list-copy';
import { Intake } from '@/components/Intake';
import { Guide, ImpactSection, OrganizationSection, RequestDetail, RequestList, ResourceDirectory, TrustSection, VolunteerSection } from '@/components/Sections';
import { Operations } from '@/components/Operations';
import { HelpSupport, NotificationsSection, OrganizationDirectory, ProfileSettings, PublicExplorer, SearchSection } from '@/components/CitizenExtras';
import { ButterflyGarden } from '@/components/ButterflyGarden';
import { CivicArtwork } from '@/components/CivicArtwork';
import { AmbientMotion } from '@/components/AmbientMotion';
import { PublicHeader } from '@/components/PublicHeader';

type Section = 'overview' | 'newRequest' | 'myRequests' | 'resources' | 'trust' | 'operations' | 'assignments' | 'organization' | 'impact' | 'volunteer' | 'notifications' | 'explore' | 'search' | 'organizations' | 'settings' | 'help';
const navigation: { id: Section; label: MessageKey; icon: typeof Home }[] = [
  { id: 'overview', label: 'overview', icon: Home }, { id: 'newRequest', label: 'newRequest', icon: PlusSquare },
  { id: 'myRequests', label: 'myRequests', icon: ClipboardList }, { id: 'resources', label: 'resources', icon: BookOpen },
  { id: 'assignments', label: 'assignments', icon: HeartHandshake }, { id: 'organization', label: 'organization', icon: UserRound },
  { id: 'volunteer', label: 'profile', icon: HeartHandshake }, { id: 'operations', label: 'operations', icon: Activity },
  { id: 'impact', label: 'impact', icon: Activity }, { id: 'trust', label: 'trust', icon: ShieldCheck },
  { id: 'explore', label: 'explore', icon: MapPin }, { id: 'organizations', label: 'organizations', icon: HeartHandshake },
  { id: 'search', label: 'search', icon: Search }, { id: 'notifications', label: 'notifications', icon: Bell },
  { id: 'settings', label: 'settings', icon: Settings }, { id: 'help', label: 'help', icon: CircleHelp },
];

const authDescriptions: Record<Language, { login: string; register: string }> = {
  en: { login: 'Access your requests, updates, and verified outcomes.', register: 'Submit a request and follow every step from one place.' },
  hi: { login: 'अपने अनुरोध, अपडेट और सत्यापित परिणाम देखें।', register: 'अनुरोध भेजें और हर कदम की जानकारी एक ही जगह पाएं।' },
  ta: { login: 'உங்கள் கோரிக்கைகள், புதுப்பிப்புகள் மற்றும் உறுதிசெய்யப்பட்ட முடிவுகளைப் பாருங்கள்.', register: 'ஒரு கோரிக்கையைச் சமர்ப்பித்து ஒவ்வொரு நிலையையும் ஒரே இடத்தில் பாருங்கள்.' },
  ml: { login: 'നിങ്ങളുടെ അഭ്യർത്ഥനകളും അറിയിപ്പുകളും സ്ഥിരീകരിച്ച ഫലങ്ങളും കാണുക.', register: 'അഭ്യർത്ഥന നൽകി ഓരോ ഘട്ടവും ഒരിടത്ത് പിന്തുടരുക.' },
};

function Auth({ language, mode, onAuthenticated }: { language: Language; mode: 'login' | 'register'; onAuthenticated: (user: User) => void }) {
  const tr = (key: MessageKey) => t(language, key);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const result = await api<{ user: User }>(`/auth/${mode === 'login' ? 'login' : 'register'}`, {
        method: 'POST',
        body: JSON.stringify(mode === 'login' ? { email, password } : { name, email, password }),
      });
      onAuthenticated(result.user);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return <main className="auth-page">
    <div className="auth-container">
      <div className="auth-visual" aria-hidden="true">
        <div className="auth-visual-orbit"><CivicArtwork compact /></div>
        <div className="auth-visual-copy"><span>SAHAYA NEXUS</span><strong>{tr('welcome')}</strong><p>{tr('subtitle')}</p></div>
        <div className="auth-visual-steps"><span><ShieldCheck size={17} /> {copy(language, 'humanVerification')}</span><span><HeartHandshake size={17} /> {copy(language, 'matchedAction')}</span></div>
      </div>
      <div className="auth-card">
        <div className="auth-card-top"><span className="small-label">{mode === 'login' ? tr('signIn') : tr('register')}</span><h1>{mode === 'login' ? tr('signInTitle') : tr('registerTitle')}</h1><p>{authDescriptions[language][mode]}</p></div>
        <form id="auth-form" className="auth-form" onSubmit={submit}>
          {mode === 'register' && <label htmlFor="auth-name">{tr('name')}<input id="auth-name" autoComplete="name" required minLength={2} value={name} onChange={event => setName(event.target.value)} /></label>}
          <label htmlFor="auth-email">{tr('email')}<input id="auth-email" type="email" autoComplete="email" required value={email} onChange={event => setEmail(event.target.value)} /></label>
          <div className="auth-field"><label htmlFor="auth-password">{tr('password')}</label><span className="auth-password-field"><input id="auth-password" type={showPassword ? 'text' : 'password'} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required minLength={mode === 'register' ? 10 : undefined} value={password} onChange={event => setPassword(event.target.value)} /><button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword} onClick={() => setShowPassword(value => !value)}>{showPassword ? <EyeOff size={19} /> : <Eye size={19} />}</button></span></div>
          {mode === 'register' && <small className="auth-password-hint">Use at least 10 characters.</small>}
          {error && <p className="error" role="alert">{error}</p>}
          <button className="button primary full auth-submit" disabled={busy}>{busy ? tr('loading') : mode === 'login' ? tr('signIn') : tr('register')} <ArrowRight size={18} /></button>
        </form>
        <p className="auth-switch">{mode === 'login' ? tr('needAccount') : tr('haveAccount')} <Link href={mode === 'login' ? '/signup' : '/login'}>{mode === 'login' ? tr('register') : tr('signIn')}</Link></p>
        <div className="auth-card-footer"><ShieldCheck size={16} /><span>{tr('privacyText')}</span></div>
      </div>
    </div>
  </main>;
}

function PublicNeedDraft({ language, signedIn }: { language: Language; signedIn: boolean }) {
  const router = useRouter();
  const [draft, setDraft] = useState('');
  useEffect(() => { setDraft(localStorage.getItem('sahaya_draft') || ''); }, []);
  function continueToAccount(event: React.FormEvent) {
    event.preventDefault();
    localStorage.setItem('sahaya_draft', draft.trim());
    router.push(signedIn ? '/app' : '/signup');
  }
  return <section id="request" className="public-draft-section">
    <div className="public-draft-inner">
      <div className="public-draft-copy"><span className="small-label">SAHAYA NEXUS / START HERE</span><h2>{t(language, 'newRequest')}</h2><p>{t(language, 'subtitle')}</p><span className="draft-reassurance"><ShieldCheck size={18} />{t(language, 'privacyText')}</span></div>
      <form className="public-draft-form" onSubmit={continueToAccount}>
        <label htmlFor="public-need-draft">{t(language, 'description')}</label>
        <textarea id="public-need-draft" minLength={10} maxLength={3000} required rows={4} value={draft} onChange={event => { setDraft(event.target.value); localStorage.setItem('sahaya_draft', event.target.value); }} placeholder={t(language, 'example')} />
        <button className="button primary">{t(language, 'getStarted')} <ArrowRight size={18} /></button>
      </form>
    </div>
  </section>;
}

function HomeHero({ language, signedIn }: { language: Language; signedIn: boolean }) {
  const tr = (key: MessageKey) => t(language, key);
  return <section className="home-hero" aria-labelledby="home-hero-title">
    <div className="home-hero-inner">
      <div className="home-hero-copy">
        <span className="hero-eyebrow"><span /> SAHAYA NEXUS · OPEN PUBLIC NEED</span>
        <h1 id="home-hero-title">{tr('welcome')}</h1>
        <p>{tr('subtitle')} {tr('privacyText')}</p>
        <div className="home-hero-actions">
          <Link className="button primary" href={signedIn ? '/app' : '/signup'}>{tr('getStarted')} <ArrowUpRight size={18} /></Link>
          <Link className="button secondary" href="/#how-it-works">{tr('howWorks')} <ArrowRight size={18} /></Link>
        </div>
        <div className="home-hero-proof"><span><ShieldCheck size={18} />{copy(language, 'humanVerification')}</span><span><HeartHandshake size={18} />{copy(language, 'matchedAction')}</span><span><Activity size={18} />{copy(language, 'confirmedImpact')}</span></div>
      </div>
      <div className="home-hero-visual"><div className="home-hero-orbit"><CivicArtwork /></div><ButterflyGarden variant="hero" /><div className="home-visual-note"><span>01 / 03</span><strong>{tr('howWorks')}</strong><ArrowUpRight size={17} /></div></div>
    </div>
  </section>;
}

function PublicLanding({ language, signedIn }: { language: Language; signedIn: boolean }) {
  const tr = (key: MessageKey) => t(language, key);
  const [verifiedOutcomes, setVerifiedOutcomes] = useState<number | null>(null);
  const [verifiedOrganizations, setVerifiedOrganizations] = useState<Organization[] | null>(null);
  const [organizationsUnavailable, setOrganizationsUnavailable] = useState(false);
  const [publicIssues, setPublicIssues] = useState<number | null>(null);
  useEffect(() => {
    api<{ verified_outcomes: number }>('/impact').then(result => setVerifiedOutcomes(result.verified_outcomes)).catch(() => {});
    api<Organization[]>('/organizations').then(setVerifiedOrganizations).catch(() => setOrganizationsUnavailable(true));
    api<{ verified_public_issues: number }>('/public/summary').then(result => setPublicIssues(result.verified_public_issues)).catch(() => {});
  }, []);
  const categoryKeys: MessageKey[] = ['food', 'blood', 'accessibility', 'community', 'volunteer', 'resource', 'publicService'];
  return <><main id="main-content" className="public-landing"><AmbientMotion /><HomeHero language={language} signedIn={signedIn} />
    <section id="impact" className="public-section public-snapshot" aria-labelledby="snapshot-title" data-reveal>
      <div className="snapshot-copy"><span className="small-label">01 / THE MISSION</span><h2 id="snapshot-title">{tr('impact')}</h2><p>{tr('realData')}</p><div className="public-metrics">
        <div><strong>{verifiedOutcomes ?? '—'}</strong><span>{tr('verifiedOutcomes')}</span></div><div><strong>{verifiedOrganizations?.length ?? "—"}</strong><span>{tr('organizations')}</span></div><div><strong>{publicIssues ?? '—'}</strong><span>{tr('explore')}</span></div>
      </div></div>
    </section>
    <section id="how-it-works" className="public-section public-process" data-reveal><span className="small-label">02 / A CLEAR PATH TO HELP</span><h2>{tr('howWorks')}</h2><div className="public-steps">{(['step1', 'step2', 'step3', 'step4'] as MessageKey[]).map((key, index) => <div key={key}><b>{String(index + 1).padStart(2, '0')}</b><strong>{tr(key)}</strong><ArrowRight size={18} aria-hidden="true" /></div>)}</div></section>
    <section id="causes" className="public-section public-cause" data-reveal><div><span className="small-label">03 / WAYS TO SUPPORT</span><h2>{tr('categories')}</h2></div><div className="public-categories">{categoryKeys.map(key => <span key={key}>{tr(key)}</span>)}</div></section>
    <PublicNeedDraft language={language} signedIn={signedIn} />
    <section id="organizations" className="public-section public-partners" data-reveal><span className="small-label">04 / VERIFIED COMMUNITY</span><h2>{tr('organizations')}</h2>{verifiedOrganizations?.length ? <div className="public-orgs">{verifiedOrganizations.slice(0, 6).map(org => <article key={org.id}><strong>{org.name}</strong><p>{org.service_area || org.description}</p><small>{tr('verify')} · SAHAYA NEXUS</small></article>)}</div> : <div className="public-org-empty"><span className="empty-orbit" aria-hidden="true"><HeartHandshake size={30} /></span><p>{organizationsUnavailable ? tr('serviceUnavailable') : verifiedOrganizations === null ? tr('loading') : tr('noOrganizations')}</p></div>}</section>
    <section id="trust" className="public-section public-trust" data-reveal><span className="small-label">05 / BUILT FOR ACCOUNTABILITY</span><TrustSection language={language} headingLevel={2} variant="public" /><Link className="button primary inline" href={signedIn ? '/app' : '/signup'}>{tr('getStarted')} <ArrowRight size={18} /></Link></section>
  </main><footer className="public-footer"><span>SAHAYA NEXUS</span><span>{tr('realData')}</span><Link href={signedIn ? '/app' : '/signup'}>{tr('getStarted')} <ArrowUpRight size={15} /></Link></footer></>;
}

export default function SahayaApp({ view }: { view: 'home' | 'login' | 'signup' | 'app' }) {
  const router = useRouter();
  const [language, setLanguage] = useState<Language>('en');
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [section, setSection] = useState<Section>('overview');
  const [selected, setSelected] = useState<Need | null>(null);
  const [requests, setRequests] = useState<Need[]>([]);
  const [requestPage, setRequestPage] = useState(1);
  const [hasMoreRequests, setHasMoreRequests] = useState(false);
  const [assignments, setAssignments] = useState<Need[]>([]);
  const [queue, setQueue] = useState<Need[]>([]);
  const [queuePage, setQueuePage] = useState(1);
  const [hasMoreQueue, setHasMoreQueue] = useState(false);
  const [resources, setResources] = useState<Resource[]>([]);
  const [resourceCategory, setResourceCategory] = useState('ALL');
  const [resourcePage, setResourcePage] = useState(1);
  const [hasMoreResources, setHasMoreResources] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [impact, setImpact] = useState<{ verified_outcomes: number; by_category: Record<string, { verified_outcomes: number; units: Record<string, number> }>; source: string } | null>(null);
  const [error, setError] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);
  const tr = (key: MessageKey) => t(language, key);

  useEffect(() => {
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
    const saved = localStorage.getItem('sahaya_language') as Language | null;
    if (saved && languages.some(x => x.id === saved)) { setLanguage(saved); document.documentElement.lang = saved; }
    try {
      const preferences = JSON.parse(localStorage.getItem('sahaya_accessibility') || '{}');
      document.documentElement.classList.toggle('large-text', Boolean(preferences.largeText));
      document.documentElement.classList.toggle('high-contrast', Boolean(preferences.highContrast));
      document.documentElement.classList.toggle('reduce-motion', Boolean(preferences.reducedMotion));
    } catch { /* Invalid local preference is ignored. */ }
    api<User>('/auth/me').then(setUser).catch(() => {}).finally(() => setAuthLoading(false));
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (view === 'app' && !user) router.replace('/login');
    if ((view === 'login' || view === 'signup') && user) router.replace('/app');
  }, [authLoading, router, user, view]);

  const refresh = useCallback(async () => {
    if (!user || view !== 'app') return;
    try {
      const [mine, assigned, listed, orgs, totals] = await Promise.all([
        api<Need[]>('/requests?limit=20'), api<Need[]>('/assignments/mine'), api<Resource[]>(`/resources?limit=100${resourceCategory === 'ALL' ? '' : `&category=${resourceCategory}`}`),
        api<Organization[]>('/organizations/mine'), api<typeof impact>('/impact'),
      ]);
      setRequests(mine); setRequestPage(1); setHasMoreRequests(mine.length === 20); setAssignments(assigned); setResources(listed); setResourcePage(1); setHasMoreResources(listed.length === 100); setOrganizations(orgs); setImpact(totals);
      if (user.role === 'ADMIN' || user.role === 'OPERATOR') { const rows = await api<Need[]>('/admin/queue?limit=50'); setQueue(rows); setQueuePage(1); setHasMoreQueue(rows.length === 50); }
      setError('');
    } catch (e) { setError((e as Error).message); }
  }, [user, resourceCategory, view]);
  useEffect(() => { refresh(); }, [refresh]);

  async function loadMoreRequests() {
    setLoadingMore(true);
    try { const next = requestPage + 1; const rows = await api<Need[]>(`/requests?limit=20&page=${next}`); setRequests(current => [...current, ...rows.filter(row => !current.some(item => item.id === row.id))]); setRequestPage(next); setHasMoreRequests(rows.length === 20); }
    catch (e) { setError((e as Error).message); } finally { setLoadingMore(false); }
  }
  async function loadMoreResources() {
    setLoadingMore(true);
    try { const next = resourcePage + 1; const rows = await api<Resource[]>(`/resources?limit=100&page=${next}${resourceCategory === 'ALL' ? '' : `&category=${resourceCategory}`}`); setResources(current => [...current, ...rows.filter(row => !current.some(item => item.id === row.id))]); setResourcePage(next); setHasMoreResources(rows.length === 100); }
    catch (e) { setError((e as Error).message); } finally { setLoadingMore(false); }
  }
  async function loadMoreQueue() {
    setLoadingMore(true);
    try { const next = queuePage + 1; const rows = await api<Need[]>(`/admin/queue?limit=50&page=${next}`); setQueue(current => [...current, ...rows.filter(row => !current.some(item => item.id === row.id))]); setQueuePage(next); setHasMoreQueue(rows.length === 50); }
    catch (e) { setError((e as Error).message); } finally { setLoadingMore(false); }
  }

  function choose(sectionName: Section) { setSection(sectionName); setSelected(null); setMenuOpen(false); }
  function selectRequest(request: Need) { setSelected(request); setMenuOpen(false); }
  async function signOut() { await api('/auth/logout', { method: 'POST' }).catch(() => {}); setUser(null); setRequests([]); setAssignments([]); setQueue([]); setSelected(null); router.replace('/'); }
  function onCreated(request: Need) { setRequests(current => [request, ...current]); setSelected(request); setSection('myRequests'); refresh(); }
  function onUpdated(request: Need) { setSelected(request); refresh(); }
  function changeLanguage(value: Language) { setLanguage(value); localStorage.setItem('sahaya_language', value); document.documentElement.lang = value; }

  if (view === 'home') return <div className="public-page"><ButterflyGarden variant="ambient" /><PublicHeader language={language} onLanguageChange={changeLanguage} signedIn={Boolean(user)} page="home" /><PublicLanding language={language} signedIn={Boolean(user)} /></div>;
  if (view === 'login' || view === 'signup') return <div className="public-page"><ButterflyGarden variant="ambient" /><PublicHeader language={language} onLanguageChange={changeLanguage} signedIn={Boolean(user)} page={view} />{user ? <div className="loading-screen">{tr('loading')}</div> : <Auth language={language} mode={view === 'login' ? 'login' : 'register'} onAuthenticated={authenticated => { setUser(authenticated); router.push('/app'); }} />}</div>;
  if (authLoading || !user) return <div className="loading-screen">{tr('loading')}</div>;

  const nav = navigation.filter(item => {
    if (item.id === 'operations') return user.role === 'ADMIN' || user.role === 'OPERATOR';
    if (item.id === 'organization') return user.role === 'ORGANIZATION' || user.role === 'CITIZEN';
    if (item.id === 'volunteer') return user.role === 'VOLUNTEER' || user.role === 'CITIZEN';
    if (item.id === 'assignments') return user.role === 'VOLUNTEER' || user.role === 'ORGANIZATION';
    return true;
  });

  return <div className="app-shell"><ButterflyGarden variant="ambient" /><aside className={`sidebar ${menuOpen ? 'open' : ''}`}><div className="sidebar-top"><Link href="/" className="brand" aria-label="Sahaya Nexus home"><span className="site-brand-icon"><HeartHandshake size={22} /></span><span>SAHAYA<br />NEXUS</span></Link><button className="menu-close" onClick={() => setMenuOpen(false)} aria-label="Close menu"><X size={22} /></button></div><nav aria-label="Main navigation">{nav.map(item => { const Icon = item.icon; return <button key={item.id} className={`nav-item ${section === item.id && !selected ? 'active' : ''}`} onClick={() => choose(item.id)}><Icon size={20} strokeWidth={1.8} /><span>{tr(item.label)}</span></button>; })}</nav><div className="sidebar-footer"><p>Open Public Need<br />Verified Action<br />Measurable Impact</p><small>SAHAYA NEXUS</small></div></aside><div className="main-column"><header className="topbar"><button className="menu-open" aria-label="Open menu" onClick={() => setMenuOpen(true)}><Menu size={22} /></button><div className="topbar-intro"><strong>{selected ? tr('details') : tr(navigation.find(item => item.id === section)?.label ?? 'overview')}</strong><span>{tr('realData')}</span></div><div className="topbar-actions"><label className="sr-only" htmlFor="language">{tr('language')}</label><select id="language" value={language} onChange={e => changeLanguage(e.target.value as Language)}>{languages.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select><div className="user-badge"><span>{user.name.slice(0, 1).toUpperCase()}</span><div><strong>{user.name}</strong><small>{user.role.toLowerCase()}</small></div></div><button className="icon-button" aria-label={tr('signOut')} title={tr('signOut')} onClick={signOut}><LogOut size={19} /></button></div></header><main className="content">
    {error && <div className="error-banner" role="alert"><span>{tr('serviceUnavailable')}</span><button onClick={refresh}>{tr('retry')}</button></div>}
    {selected ? <RequestDetail language={language} request={selected} user={user} onUpdated={onUpdated} onBack={() => setSelected(null)} /> : <>
      {section === 'overview' && <div className="overview-grid"><div><Intake language={language} userId={user.id} onCreated={onCreated} /><div className="section-subhead"><h2>{tr('myRequests')}</h2><button className="link-button" onClick={() => choose('myRequests')}>{tr('myRequests')} <ArrowRight size={16} /></button></div><RequestList language={language} requests={requests.slice(0, 4)} onSelect={selectRequest} /></div><Guide language={language} onTrust={() => choose('trust')} /></div>}
      {section === 'newRequest' && <div className="narrow"><Intake language={language} userId={user.id} onCreated={onCreated} /></div>}
      {section === 'myRequests' && <section><div className="section-heading"><div><h1>{tr('requestsTitle')}</h1><p>{tr('realData')}</p></div><button className="button primary" onClick={() => choose('newRequest')}><PlusSquare size={17} />{tr('newRequest')}</button></div><RequestList language={language} requests={requests} onSelect={selectRequest} />{hasMoreRequests && <button className="button secondary inline list-more" disabled={loadingMore} onClick={loadMoreRequests}>{listCopy(language)}</button>}</section>}
      {section === 'resources' && <ResourceDirectory language={language} resources={resources} category={resourceCategory} onCategoryChange={value => { setResourceCategory(value); setResources([]); setHasMoreResources(false); }} hasMore={hasMoreResources} loadingMore={loadingMore} onLoadMore={loadMoreResources} />}
      {section === 'assignments' && <section><h1>{tr('assignments')}</h1><RequestList language={language} requests={assignments} onSelect={selectRequest} emptyText={tr('noData')} /></section>}
      {section === 'volunteer' && <VolunteerSection language={language} user={user} onUser={setUser} assignments={assignments} onSelect={selectRequest} />}
      {section === 'organization' && <OrganizationSection language={language} organizations={organizations} onRefresh={refresh} onUser={setUser} assignments={assignments} onSelect={selectRequest} />}
      {section === 'operations' && <Operations language={language} queue={queue} role={user.role} onRefresh={refresh} hasMore={hasMoreQueue} loadingMore={loadingMore} onLoadMore={loadMoreQueue} />}
      {section === 'impact' && <ImpactSection language={language} impact={impact} />}
      {section === 'trust' && <TrustSection language={language} />}
      {section === 'notifications' && <NotificationsSection language={language} onOpenRequest={selectRequest} />}
      {section === 'explore' && <PublicExplorer language={language} />}
      {section === 'organizations' && <OrganizationDirectory language={language} />}
      {section === 'search' && <SearchSection language={language} onOpenRequest={selectRequest} />}
      {section === 'settings' && <ProfileSettings language={language} user={user} onUser={setUser} onDeleted={signOut} />}
      {section === 'help' && <HelpSupport language={language} />}
    </>}
  </main><footer className="footer"><span>SAHAYA NEXUS · {tr('realData')}</span><span>{tr('privacy')}</span></footer></div>{menuOpen && <button className="sidebar-scrim" aria-label="Close menu" onClick={() => setMenuOpen(false)} />}</div>;
}
