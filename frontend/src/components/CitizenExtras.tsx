'use client';

import { useEffect, useState } from 'react';
import { Bell, CheckCircle2, CircleHelp, MapPin, Search, ShieldAlert, SlidersHorizontal } from 'lucide-react';
import { api, Need, Notification, Organization, User } from '@/lib/api';
import { Language, statusText, t } from '@/lib/i18n';
import { copy } from '@/lib/copy';
import { listCopy } from '@/lib/list-copy';
import { categoryKey, formatDate, pretty } from './Sections';

type Base = { language: Language };
type PublicIssue = { id: string; category: string; issue_type: string; status: string; urgency: string; latitude: number | null; longitude: number | null; created_at: string; data_label: string };
type PublicCell = { latitude: number; longitude: number; verified_outcomes: number };
type SearchResults = { requests: { id: string; category: string; status: string; description: string }[]; resources: { id: string; title: string; category: string; capacity: number }[]; organizations: { id: string; name: string; service_area: string }[]; volunteers: { id: string; name: string; verified: boolean }[] };

export function NotificationsSection({ language, onOpenRequest }: Base & { onOpenRequest: (request: Need) => void }) {
  const [rows, setRows] = useState<Notification[]>([]);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1); const [hasMore, setHasMore] = useState(false); const [loadingMore, setLoadingMore] = useState(false);
  useEffect(() => { api<Notification[]>('/notifications').then(items => { setRows(items); setHasMore(items.length === 50); }).catch(e => setError((e as Error).message)); }, []);
  async function loadMore() {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try { const next = page + 1; const added = await api<Notification[]>(`/notifications?page=${next}`); setRows(current => [...current, ...added]); setPage(next); setHasMore(added.length === 50); setError(''); }
    catch (e) { setError((e as Error).message); }
    finally { setLoadingMore(false); }
  }
  async function open(item: Notification) {
    try {
      if (!item.read_at) await api(`/notifications/${item.id}/read`, { method: 'POST' });
      setRows(current => current.map(row => row.id === item.id ? { ...row, read_at: new Date().toISOString() } : row));
      if (item.request_id) onOpenRequest(await api<Need>(`/requests/${item.request_id}`));
    } catch (e) { setError((e as Error).message); }
  }
  const noticeKey = (kind: string) => ({ REQUEST_STATUS: 'requestUpdate', ASSIGNMENT: 'assignmentNotice', ASSIGNMENT_PROGRESS: 'progressNotice', FOLLOW_UP: 'followUpNotice', DUPLICATE_CONFIRMATION: 'duplicateNotice' } as const)[kind as 'REQUEST_STATUS' | 'ASSIGNMENT' | 'ASSIGNMENT_PROGRESS' | 'FOLLOW_UP' | 'DUPLICATE_CONFIRMATION'] || 'requestUpdate';
  return <section>
    <div className="section-heading"><div><h1>{copy(language, 'notificationsTitle')}</h1><p>{copy(language, 'notificationsLead')}</p></div><Bell size={24} /></div>
    {rows.length ? <div className="request-list">{rows.map(item => <button className="request-row" key={item.id} onClick={() => open(item)}><Bell size={19} /><span className="request-row-main"><strong>{copy(language, 'notificationsTitle')}{!item.read_at && <span className="status-chip">{copy(language, 'newNotice')}</span>}</strong><span>{copy(language, noticeKey(item.kind))}</span><small>{formatDate(item.created_at)}</small></span></button>)}</div> : <div className="empty compact"><Bell size={40} /><h2>{copy(language, 'noNotifications')}</h2></div>}
    {hasMore && <button className="button secondary inline list-more" disabled={loadingMore} onClick={loadMore}>{listCopy(language)}</button>}
    {error && <p className="error" role="alert">{error}</p>}
  </section>;
}

export function PublicExplorer({ language }: Base) {
  useEffect(() => { document.documentElement.lang = language; }, [language]);
  const [issues, setIssues] = useState<PublicIssue[]>([]);
  const [issuePage, setIssuePage] = useState(1); const [moreIssues, setMoreIssues] = useState(false); const [loadingIssues, setLoadingIssues] = useState(false);
  const [cells, setCells] = useState<PublicCell[]>([]);
  const [category, setCategory] = useState('');
  const [mapsEnabled, setMapsEnabled] = useState(false);
  const [selectedCell, setSelectedCell] = useState<PublicCell | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    api<PublicIssue[]>(`/public/issues?page=1${category ? `&category=${category}` : ''}`).then(items => { if (active) { setIssues(items); setIssuePage(1); setMoreIssues(items.length === 30); } }).catch(e => { if (active) setError((e as Error).message); });
    return () => { active = false; };
  }, [category]);
  async function loadIssues() {
    if (loadingIssues || !moreIssues) return;
    setLoadingIssues(true);
    try { const next = issuePage + 1; const added = await api<PublicIssue[]>(`/public/issues?page=${next}${category ? `&category=${category}` : ''}`); setIssues(current => [...current, ...added]); setIssuePage(next); setMoreIssues(added.length === 30); setError(''); }
    catch (e) { setError((e as Error).message); }
    finally { setLoadingIssues(false); }
  }
  useEffect(() => { api<{ cells: PublicCell[] }>('/public/impact-map').then(result => setCells(result.cells)).catch(e => setError((e as Error).message)); }, []);
  useEffect(() => { api<{ feature_flags: { maps: boolean } }>('/config').then(result => setMapsEnabled(result.feature_flags.maps)).catch(() => {}); }, []);
  const point = selectedCell || cells[0];
  const mapUrl = mapsEnabled && point ? `https://www.openstreetmap.org/export/embed.html?bbox=${point.longitude - 0.15}%2C${point.latitude - 0.1}%2C${point.longitude + 0.15}%2C${point.latitude + 0.1}&layer=mapnik&marker=${point.latitude}%2C${point.longitude}` : '';
  return <section>
    <div className="section-heading"><div><h1>{copy(language, 'publicExplorerTitle')}</h1><p>{copy(language, 'publicExplorerLead')}</p></div><MapPin size={24} /></div>
    <div className="filter-row"><label>{t(language, 'category')}<select value={category} onChange={e => setCategory(e.target.value)}><option value="">{copy(language, 'all')}</option><option value="COMMUNITY">{t(language, 'community')}</option><option value="ACCESSIBILITY">{t(language, 'accessibility')}</option></select></label></div>
    <div className="two-column section-spaced"><div className="panel"><h2>{copy(language, 'verifiedPublicReports')}</h2>
      {issues.length ? issues.map(item => <div className="review-row" key={item.id}><div><strong>{pretty(item.issue_type)} · {t(language, categoryKey[item.category])}</strong><p>{statusText(language, item.status)} · {statusText(language, item.urgency)} · {formatDate(item.created_at)}</p><small>{item.latitude === null ? copy(language, 'locationWithheld') : `${copy(language, 'approximateArea')}: ${item.latitude.toFixed(1)}, ${item.longitude?.toFixed(1)}`}</small></div><span className="status-chip">REAL</span></div>) : <p className="muted">{copy(language, 'noPublicReports')}</p>}
      {moreIssues && <button className="button secondary inline list-more" disabled={loadingIssues} onClick={loadIssues}>{listCopy(language)}</button>}
    </div><div className="panel"><h2>{copy(language, 'publicImpactMap')}</h2><p className="muted">{copy(language, 'publicMapLead')}</p>
      {mapUrl ? <iframe className="public-map" title={copy(language, 'publicImpactMap')} loading="lazy" referrerPolicy="no-referrer" src={mapUrl} /> : <div className="map-empty"><MapPin size={32} /><p>{mapsEnabled ? copy(language, 'noMapCells') : copy(language, 'mapDisabled')}</p></div>}
      {cells.length > 0 && <div className="map-cell-list">{cells.map(cell => <button key={`${cell.latitude}:${cell.longitude}`} className="button secondary" onClick={() => setSelectedCell(cell)}>{cell.verified_outcomes} {copy(language, 'outcomes')} · {cell.latitude.toFixed(1)}, {cell.longitude.toFixed(1)}</button>)}</div>}
    </div></div>
    {error && <p className="error" role="alert">{error}</p>}
  </section>;
}

export function SearchSection({ language, onOpenRequest }: Base & { onOpenRequest: (request: Need) => void }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResults | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    try { setResults(await api<SearchResults>(`/search?q=${encodeURIComponent(query)}`)); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function open(id: string) { try { onOpenRequest(await api<Need>(`/requests/${id}`)); } catch (e) { setError((e as Error).message); } }
  return <section>
    <div className="section-heading"><div><h1>{t(language, 'search')}</h1><p>{copy(language, 'searchLead')}</p></div><Search size={24} /></div>
    <form className="search-form" onSubmit={submit}><label className="sr-only" htmlFor="search-all">{copy(language, 'searchRecords')}</label><input id="search-all" minLength={2} maxLength={100} required value={query} onChange={e => setQuery(e.target.value)} placeholder={copy(language, 'searchPlaceholder')} /><button className="button primary" disabled={busy}>{busy ? copy(language, 'searching') : t(language, 'search')}</button></form>
    {results && <div className="search-groups">
      {results.requests.length > 0 && <div className="panel"><h2>{copy(language, 'requests')}</h2>{results.requests.map(row => <button className="review-row as-button" key={row.id} onClick={() => open(row.id)}><strong>{t(language, categoryKey[row.category])} · {statusText(language, row.status)}</strong><span>{row.description}</span></button>)}</div>}
      {results.resources.length > 0 && <div className="panel"><h2>{t(language, 'resources')}</h2>{results.resources.map(row => <p key={row.id}>{row.title} · {t(language, categoryKey[row.category])} · {t(language, 'capacity')} {row.capacity}</p>)}</div>}
      {results.organizations.length > 0 && <div className="panel"><h2>{t(language, 'organizations')}</h2>{results.organizations.map(row => <p key={row.id}>{row.name}{row.service_area ? ` · ${row.service_area}` : ''}</p>)}</div>}
      {results.volunteers.length > 0 && <div className="panel"><h2>{copy(language, 'volunteers')}</h2>{results.volunteers.map(row => <p key={row.id}>{row.name} · {statusText(language, row.verified ? 'VERIFIED' : 'UNDER_REVIEW')}</p>)}</div>}
      {Object.values(results).every(group => group.length === 0) && <div className="empty compact"><Search size={36} /><h2>{copy(language, 'noResults')}</h2></div>}
    </div>}
    {error && <p className="error" role="alert">{error}</p>}
  </section>;
}

export function OrganizationDirectory({ language }: Base) {
  const [rows, setRows] = useState<Organization[]>([]);
  const [saved, setSaved] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1); const [hasMore, setHasMore] = useState(false); const [loadingMore, setLoadingMore] = useState(false);
  useEffect(() => { Promise.all([api<Organization[]>('/organizations?limit=30'), api<Organization[]>('/organizations/saved')]).then(([all, own]) => { setRows(all); setHasMore(all.length === 30); setSaved(own.map(item => item.id)); }).catch(e => setError((e as Error).message)); }, []);
  async function loadMore() {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try { const next = page + 1; const added = await api<Organization[]>(`/organizations?page=${next}&limit=30`); setRows(current => [...current, ...added]); setPage(next); setHasMore(added.length === 30); setError(''); }
    catch (e) { setError((e as Error).message); }
    finally { setLoadingMore(false); }
  }
  async function toggle(id: string) {
    const isSaved = saved.includes(id);
    try { await api(`/organizations/${id}/save`, { method: isSaved ? 'DELETE' : 'POST' }); setSaved(current => isSaved ? current.filter(item => item !== id) : [...current, id]); }
    catch (e) { setError((e as Error).message); }
  }
  return <section><div className="section-heading"><div><h1>{copy(language, 'verifiedOrganizations')}</h1><p>{copy(language, 'endorsement')}</p></div><CheckCircle2 size={24} /></div>{rows.length ? <div className="resource-grid">{rows.map(row => <article className="resource-card" key={row.id}><span className="small-label">{statusText(language, 'VERIFIED')}</span><h2>{row.name}</h2><p>{row.description}</p><p>{row.service_area}</p><button className="button secondary" onClick={() => toggle(row.id)}>{saved.includes(row.id) ? copy(language, 'removeSaved') : copy(language, 'saveOrganization')}</button></article>)}</div> : <div className="empty compact"><CircleHelp size={40} /><h2>{copy(language, 'noVerifiedOrganizations')}</h2></div>}{hasMore && <button className="button secondary inline list-more" disabled={loadingMore} onClick={loadMore}>{listCopy(language)}</button>}{error && <p className="error" role="alert">{error}</p>}</section>;
}

export function ProfileSettings({ language, user, onUser, onDeleted }: Base & { user: User; onUser: (user: User) => void; onDeleted: () => void }) {
  const [name, setName] = useState(user.name);
  const [largeText, setLargeText] = useState(false);
  const [highContrast, setHighContrast] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [message, setMessage] = useState('');
  const [deletionPassword, setDeletionPassword] = useState('');
  useEffect(() => {
    try {
      const settings = JSON.parse(localStorage.getItem('sahaya_accessibility') || '{}');
      setLargeText(Boolean(settings.largeText)); setHighContrast(Boolean(settings.highContrast)); setReducedMotion(Boolean(settings.reducedMotion));
    } catch { localStorage.removeItem('sahaya_accessibility'); }
  }, []);
  function updateAccessibility(values: { largeText: boolean; highContrast: boolean; reducedMotion: boolean }) {
    setLargeText(values.largeText); setHighContrast(values.highContrast); setReducedMotion(values.reducedMotion);
    localStorage.setItem('sahaya_accessibility', JSON.stringify(values));
    document.documentElement.classList.toggle('large-text', values.largeText);
    document.documentElement.classList.toggle('high-contrast', values.highContrast);
    document.documentElement.classList.toggle('reduce-motion', values.reducedMotion);
  }
  async function save(event: React.FormEvent) { event.preventDefault(); try { onUser(await api<User>('/auth/me', { method: 'PATCH', body: JSON.stringify({ name }) })); setMessage(copy(language, 'profileSaved')); } catch (e) { setMessage((e as Error).message); } }
  async function deleteAccount(event: React.FormEvent) { event.preventDefault(); try { await api('/auth/me', { method: 'DELETE', body: JSON.stringify({ password: deletionPassword }) }); localStorage.removeItem(`sahaya_pending_${user.id}`); localStorage.removeItem('sahaya_draft'); onDeleted(); } catch (e) { setMessage((e as Error).message); } }
  return <section>
    <div className="section-heading"><div><h1>{copy(language, 'profileAccessibility')}</h1><p>{copy(language, 'profileLead')}</p></div><SlidersHorizontal size={24} /></div>
    <div className="two-column">
      <form className="panel form-stack" onSubmit={save}><h2>{t(language, 'profile')}</h2><label>{t(language, 'name')}<input value={name} required minLength={2} onChange={e => setName(e.target.value)} /></label><label>{t(language, 'email')}<input value={user.email} disabled /></label><button className="button primary inline">{copy(language, 'saveProfile')}</button></form>
      <div className="panel form-stack"><h2>{copy(language, 'accessibilitySettings')}</h2><label className="checkbox"><input type="checkbox" checked={largeText} onChange={e => updateAccessibility({ largeText: e.target.checked, highContrast, reducedMotion })} />{copy(language, 'largeText')}</label><label className="checkbox"><input type="checkbox" checked={highContrast} onChange={e => updateAccessibility({ largeText, highContrast: e.target.checked, reducedMotion })} />{copy(language, 'highContrast')}</label><label className="checkbox"><input type="checkbox" checked={reducedMotion} onChange={e => updateAccessibility({ largeText, highContrast, reducedMotion: e.target.checked })} />{copy(language, 'reduceMotion')}</label><p className="muted">{copy(language, 'localPreferences')}</p></div>
    </div>
    {user.role !== 'ADMIN' && user.role !== 'OPERATOR' && <form className="panel form-stack section-spaced" onSubmit={deleteAccount}><h2>{copy(language, 'deleteAccount')}</h2><p>{copy(language, 'deleteLead')}</p><label>{copy(language, 'confirmPassword')}<input type="password" autoComplete="current-password" value={deletionPassword} onChange={e => setDeletionPassword(e.target.value)} required /></label><button className="button danger inline">{copy(language, 'anonymizeAccount')}</button></form>}
    {message && <p role="status">{message}</p>}
  </section>;
}

export function HelpSupport({ language, requestId }: Base & { requestId?: string }) {
  const [category, setCategory] = useState('OTHER');
  const [reason, setReason] = useState('');
  const [message, setMessage] = useState('');
  async function report(event: React.FormEvent) { event.preventDefault(); try { await api('/reports/abuse', { method: 'POST', body: JSON.stringify({ request_id: requestId || null, category, reason }) }); setReason(''); setMessage(copy(language, 'reportSent')); } catch (e) { setMessage((e as Error).message); } }
  return <section><div className="section-heading"><div><h1>{copy(language, 'helpSafety')}</h1><p>{copy(language, 'emergency')}</p></div><ShieldAlert size={24} /></div><div className="two-column"><div className="panel"><h2>{copy(language, 'howToGetHelp')}</h2><p>{copy(language, 'helpInstructions')}</p><p>{copy(language, 'clinicalHelp')}</p><p>{copy(language, 'escalationHelp')}</p></div><form className="panel form-stack" onSubmit={report}><h2>{copy(language, 'reportAbuse')}</h2><label>{copy(language, 'type')}<select value={category} onChange={e => setCategory(e.target.value)}><option value="OTHER">{copy(language, 'other')}</option><option value="SPAM">{copy(language, 'spam')}</option><option value="FRAUD">{copy(language, 'fraud')}</option><option value="SAFETY">{copy(language, 'safety')}</option><option value="PRIVACY">{copy(language, 'privacy')}</option></select></label><label>{copy(language, 'whatHappened')}<textarea required minLength={12} maxLength={2000} value={reason} onChange={e => setReason(e.target.value)} /></label><button className="button primary inline">{copy(language, 'sendReport')}</button></form></div>{message && <p role="status">{message}</p>}</section>;
}
