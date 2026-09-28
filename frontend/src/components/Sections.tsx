'use client';

import { useEffect, useState } from 'react';
import { ArrowRight, CheckCircle2, CircleHelp, Clock3, FileText, HeartHandshake, LockKeyhole, MapPin } from 'lucide-react';
import { api, Need, Organization, Resource, User } from '@/lib/api';
import { Language, MessageKey, statusText, t } from '@/lib/i18n';
import { copy } from '@/lib/copy';
import { trustCopy } from '@/lib/trust-copy';
import { listCopy } from '@/lib/list-copy';
import { RequestMessages } from './RequestMessages';
import { CapacityHistory } from './CapacityHistory';
import { OrganizationInvitations, OrganizationMembers } from './OrganizationMembers';

export const categoryKey: Record<string, MessageKey> = { FOOD: 'food', BLOOD: 'blood', ACCESSIBILITY: 'accessibility', COMMUNITY: 'community', VOLUNTEER: 'volunteer', RESOURCE: 'resource', PUBLIC_SERVICE: 'publicService' };
export const categories = Object.keys(categoryKey);
type Opportunity = { id: string; category: string; urgency: string; quantity: number | null; unit: string | null; distance_km: number | null; approximate_latitude: number | null; approximate_longitude: number | null; interested: boolean; created_at: string };
type OrganizationPerformance = { organization_id: string; assignments: number; active: number; verified_outcomes: number; impact_units: Record<string, number> };
export function formatDate(value: string | null) { return value ? new Date(value).toLocaleString() : '—'; }
export function pretty(value: string) { return value.replaceAll('_', ' ').toLowerCase().replace(/^./, c => c.toUpperCase()); }

type Base = { language: Language };

export function Guide({ language, onTrust }: Base & { onTrust: () => void }) {
  const tr = (key: MessageKey) => t(language, key);
  return <aside className="guide"><h2>{tr('howWorks')}</h2><div className="steps">{(['step1', 'step2', 'step3', 'step4'] as const).map((key, index) => <div className="step" key={key}><span>{index + 1}</span><strong>{tr(key)}</strong></div>)}</div><div className="privacy-box"><LockKeyhole size={22} /><div><strong>{tr('privacy')}</strong><p>{tr('privacyText')}</p><button className="link-button" onClick={onTrust}>{tr('viewTrust')} <ArrowRight size={15} /></button></div></div></aside>;
}

export function RequestList({ language, requests, onSelect, emptyText }: Base & { requests: Need[]; onSelect: (request: Need) => void; emptyText?: string }) {
  const tr = (key: MessageKey) => t(language, key);
  if (!requests.length) return <div className="empty"><FileText size={48} strokeWidth={1.4} /><h2>{emptyText || tr('noRequests')}</h2><p>{tr('noRequestsText')}</p></div>;
  return <div className="request-list">{requests.map(request => <button className="request-row" key={request.id} onClick={() => onSelect(request)}><span className={`category-mark ${request.category.toLowerCase()}`}></span><span className="request-row-main"><strong>{tr(categoryKey[request.category] || 'publicService')}</strong><span>{request.description}</span><small><MapPin size={13} />{request.location_text} · {formatDate(request.created_at)}</small></span><span className="status-chip">{statusText(language, request.status)}</span><ArrowRight size={18} /></button>)}</div>;
}

export function RequestDetail({ language, request, user, onUpdated, onBack }: Base & { request: Need; user: User; onUpdated: (request: Need) => void; onBack: () => void }) {
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false); const [summary, setSummary] = useState(''); const [impactValue, setImpactValue] = useState(''); const [impactUnit, setImpactUnit] = useState(''); const [feedbackAnswer, setFeedbackAnswer] = useState<'YES' | 'NO' | 'PARTIALLY'>('YES'); const [feedbackComment, setFeedbackComment] = useState('');
  const tr = (key: MessageKey) => t(language, key);
  async function act(path: string, body?: object) { setError(''); setBusy(true); try { onUpdated(await api<Need>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined })); } catch (e) { setError((e as Error).message); } finally { setBusy(false); } }
  async function upload(file: File) { setError(''); setBusy(true); try { const form = new FormData(); form.set('file', file); const response = await fetch(`/api/v1/requests/${request.id}/evidence`, { method: 'POST', body: form }); const result = await response.json(); if (!response.ok) throw new Error(result.detail || 'Upload failed'); onUpdated(await api<Need>(`/requests/${request.id}`)); } catch (e) { setError((e as Error).message); } finally { setBusy(false); } }
  const isOwner = request.owner_id === user.id;
  const isResponder = request.assignment && !isOwner && user.role !== 'ADMIN' && user.role !== 'OPERATOR';
  return <section className="detail"><button className="text-button" onClick={onBack}>← {tr('back')}</button><div className="detail-heading"><div><span className="small-label">{tr(categoryKey[request.category] || 'publicService')}</span><h1>{request.description}</h1><p><MapPin size={16} /> {request.location_text} · {formatDate(request.created_at)}</p></div><span className="status-chip large">{statusText(language, request.status)}</span></div>
    {request.category === 'BLOOD' && <div className="safety-note">{tr('clinical')}</div>}
    <div className="detail-grid"><div className="panel"><h2>{tr('details')}</h2><dl className="facts"><div><dt>{tr('status')}</dt><dd>{statusText(language, request.status)}</dd></div><div><dt>{tr('verification')}</dt><dd>{statusText(language, request.verification)}</dd></div><div><dt>{tr('priority')}</dt><dd>{statusText(language, request.urgency)}{request.priority_reason && <small>{request.priority_reason}</small>}</dd></div><div><dt>{tr('locationPrivacy')}</dt><dd>{statusText(language, request.location_precision)}</dd></div>{request.latitude !== null && request.longitude !== null && <div><dt>{copy(language, 'coordinates')}</dt><dd>{request.latitude.toFixed(5)}, {request.longitude.toFixed(5)}</dd></div>}{request.quantity && <div><dt>{tr('quantity')}</dt><dd>{request.quantity} {request.unit}</dd></div>}{request.deadline && <div><dt>{tr('deadline')}</dt><dd>{formatDate(request.deadline)}</dd></div>}{Object.entries(request.details || {}).filter(([, value]) => value).map(([key, value]) => <div key={key}><dt>{pretty(key)}</dt><dd>{key.endsWith('time') || key.endsWith('until') ? formatDate(value) : String(value)}</dd></div>)}</dl>
      {request.assignment ? <div className="assignment-summary"><HeartHandshake size={20} /><div><strong>{tr('assignments')}</strong><p>{request.assignment.rationale}</p></div></div> : <p className="muted">{tr('noAssignment')}</p>}
      {request.outcome && <div className="outcome"><h3>{tr('outcome')}</h3><p>{request.outcome.summary}</p>{request.outcome.verified_at && <span className="verified"><CheckCircle2 size={16} /> {tr('verify')} · {formatDate(request.outcome.verified_at)}</span>}{request.outcome.impact_value !== null && <p>{request.outcome.impact_value} {request.outcome.impact_unit}</p>}</div>}
      <div className="evidence-section"><h3>{copy(language, 'evidence')}</h3>{request.evidence?.length ? <ul>{request.evidence.map(item => <li key={item.id}><a href={item.url}>{item.name}</a><small>{Math.ceil(item.size / 1024)} KB</small></li>)}</ul> : <p className="muted">{copy(language, 'noEvidence')}</p>}{!['CANCELLED', 'REJECTED', 'EXPIRED', 'DUPLICATE', 'IMPACT_RECORDED'].includes(request.status) && <label className="file-control">{copy(language, 'attachEvidence')}<input type="file" accept="image/jpeg,image/png" disabled={busy} onChange={e => { const file = e.target.files?.[0]; if (file) upload(file); e.target.value = ''; }} /></label>}</div>
      {isOwner && !['CANCELLED', 'REJECTED', 'EXPIRED', 'DUPLICATE', 'IMPACT_RECORDED', 'IN_PROGRESS', 'ACTION_COMPLETED', 'OUTCOME_VERIFIED'].includes(request.status) && <button className="button secondary" disabled={busy} onClick={() => act(`/requests/${request.id}/cancel`)}>{tr('cancel')}</button>}
      {isOwner && request.status === 'ACTION_COMPLETED' && <form className="form-stack" onSubmit={e => { e.preventDefault(); act(`/requests/${request.id}/feedback`, { answer: feedbackAnswer, comment: feedbackComment }); }}><h3>{copy(language, 'resolvedQuestion')}</h3><label>{copy(language, 'resolution')}<select value={feedbackAnswer} onChange={e => setFeedbackAnswer(e.target.value as 'YES' | 'NO' | 'PARTIALLY')}><option value="YES">{statusText(language, 'YES')}</option><option value="PARTIALLY">{statusText(language, 'PARTIALLY')}</option><option value="NO">{statusText(language, 'NO')}</option></select></label><label>{copy(language, 'comment')}<textarea value={feedbackComment} onChange={e => setFeedbackComment(e.target.value)} /></label><button className="button primary" disabled={busy}>{tr('confirmOutcome')}</button></form>}
      {request.feedback && <p className="muted">{copy(language, 'resolutionFeedback')}: {statusText(language, request.feedback.answer)}{request.feedback.comment ? ` · ${request.feedback.comment}` : ''}</p>}
      {isResponder && request.status === 'ASSIGNED' && request.assignment?.status === 'OFFERED' && <button className="button primary" disabled={busy} onClick={() => act(`/assignments/${request.id}/accept`)}>{copy(language, 'acceptAssignment')}</button>}
      {isResponder && request.status === 'ASSIGNED' && request.assignment?.status === 'ACCEPTED' && <button className="button primary" disabled={busy} onClick={() => act(`/assignments/${request.id}/start`)}>{copy(language, 'startResponse')}</button>}
      {isResponder && request.status === 'IN_PROGRESS' && request.assignment?.status === 'IN_PROGRESS' && <button className="button primary" disabled={busy} onClick={() => act(`/assignments/${request.id}/arrive`)}>{copy(language, 'markArrived')}</button>}
      {isResponder && request.status === 'IN_PROGRESS' && request.assignment?.status === 'ARRIVED' && <form className="form-stack" onSubmit={e => { e.preventDefault(); act(`/assignments/${request.id}/complete`, { summary, impact_value: impactValue ? Number(impactValue) : null, impact_unit: impactUnit || null }); }}><h3>{tr('complete')}</h3><label>{tr('outcome')}<textarea required minLength={10} value={summary} onChange={e => setSummary(e.target.value)} /></label><div className="form-grid"><label>{tr('impactValue')}<input type="number" min="0" value={impactValue} onChange={e => setImpactValue(e.target.value)} /></label><label>{tr('impactUnit')}<input value={impactUnit} onChange={e => setImpactUnit(e.target.value)} placeholder="meals, people, repairs" /></label></div><button className="button primary" disabled={busy}>{tr('complete')}</button></form>}
    </div><div className="panel"><h2>{tr('timeline')}</h2><ol className="timeline">{request.events.map(event => <li key={event.id}><span className="timeline-dot"></span><strong>{statusText(language, event.to_status)}</strong><small>{formatDate(event.created_at)}</small><p>{event.reason}</p></li>)}</ol></div></div><RequestMessages requestId={request.id} userId={user.id} language={language} />{error && <p className="error" role="alert">{error}</p>}</section>;
}

export function ResourceDirectory({ language, resources, category, onCategoryChange, hasMore, loadingMore, onLoadMore }: Base & { resources: Resource[]; category: string; onCategoryChange: (category: string) => void; hasMore: boolean; loadingMore: boolean; onLoadMore: () => void }) {
  const tr = (key: MessageKey) => t(language, key);
  return <section><div className="section-heading"><div><h1>{tr('resourcesTitle')}</h1><p>{tr('realData')}</p></div><select aria-label={tr('category')} value={category} onChange={e => onCategoryChange(e.target.value)}><option value="ALL">{copy(language, 'all')}</option>{categories.map(c => <option value={c} key={c}>{tr(categoryKey[c])}</option>)}</select></div>{resources.length ? <div className="resource-grid">{resources.map(r => <article className="resource-card" key={r.id}><div className="resource-symbol"><HeartHandshake size={24} /></div><span className="small-label">{tr(categoryKey[r.category])}</span><h2>{r.title}</h2><p>{r.description}</p><dl><div><dt>{tr('organization')}</dt><dd>{r.organization_name}</dd></div><div><dt>{copy(language, 'remainingCapacity')}</dt><dd>{r.remaining_capacity} / {r.capacity}</dd></div>{r.expires_at && <div><dt>{copy(language, 'expires')}</dt><dd>{formatDate(r.expires_at)}</dd></div>}</dl></article>)}</div> : <div className="empty compact"><CircleHelp size={42} /><h2>{tr('noResources')}</h2></div>}{hasMore && <button className="button secondary inline list-more" disabled={loadingMore} onClick={onLoadMore}>{listCopy(language)}</button>}</section>;
}

export function VolunteerSection({ language, user, onUser, assignments, onSelect }: Base & { user: User; onUser: (user: User) => void; assignments: Need[]; onSelect: (request: Need) => void }) {
  const tr = (key: MessageKey) => t(language, key);
  const [categoriesValue, setCategoriesValue] = useState<string[]>(user.categories || []); const [skills, setSkills] = useState((user.skills || []).join(', ')); const [languagesValue, setLanguagesValue] = useState((user.languages || []).join(', ')); const [transport, setTransport] = useState(user.transport || ''); const [available, setAvailable] = useState(user.available); const [capacity, setCapacity] = useState(String(user.capacity || 1)); const [error, setError] = useState('');
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [opportunityPage, setOpportunityPage] = useState(1); const [moreOpportunities, setMoreOpportunities] = useState(false); const [loadingOpportunities, setLoadingOpportunities] = useState(false);
  const [taskCategory, setTaskCategory] = useState(''); const [taskUrgency, setTaskUrgency] = useState(''); const [maxDistance, setMaxDistance] = useState('');
  useEffect(() => {
    if (user.role !== 'VOLUNTEER' || !user.verified || !user.available) { setOpportunities([]); setMoreOpportunities(false); return; }
    const query = new URLSearchParams();
    if (taskCategory) query.set('category', taskCategory);
    if (taskUrgency) query.set('urgency', taskUrgency);
    if (maxDistance) query.set('max_distance_km', maxDistance);
    query.set('page', '1'); query.set('limit', '20');
    let active = true;
    api<Opportunity[]>(`/volunteers/opportunities?${query}`).then(rows => { if (active) { setOpportunities(rows); setOpportunityPage(1); setMoreOpportunities(rows.length === 20); } }).catch(e => { if (active) setError((e as Error).message); });
    return () => { active = false; };
  }, [user.role, user.verified, user.available, taskCategory, taskUrgency, maxDistance]);
  async function loadOpportunities() {
    if (loadingOpportunities || !moreOpportunities) return;
    setLoadingOpportunities(true);
    const query = new URLSearchParams({ page: String(opportunityPage + 1), limit: '20' });
    if (taskCategory) query.set('category', taskCategory);
    if (taskUrgency) query.set('urgency', taskUrgency);
    if (maxDistance) query.set('max_distance_km', maxDistance);
    try { const rows = await api<Opportunity[]>(`/volunteers/opportunities?${query}`); setOpportunities(current => [...current, ...rows]); setOpportunityPage(opportunityPage + 1); setMoreOpportunities(rows.length === 20); setError(''); }
    catch (e) { setError((e as Error).message); }
    finally { setLoadingOpportunities(false); }
  }
  async function apply() { try { onUser(await api<User>('/auth/volunteer/apply', { method: 'POST' })); } catch (e) { setError((e as Error).message); } }
  async function save(e: React.FormEvent) { e.preventDefault(); try { onUser(await api<User>('/auth/me', { method: 'PATCH', body: JSON.stringify({ categories: categoriesValue, skills: skills.split(',').map(x => x.trim()).filter(Boolean), languages: languagesValue.split(',').map(x => x.trim()).filter(Boolean), transport, available, capacity: Number(capacity) }) })); setError(''); } catch (err) { setError((err as Error).message); } }
  async function interest(item: Opportunity) { try { await api(`/volunteers/opportunities/${item.id}/interest`, { method: 'POST', body: '{}' }); setOpportunities(current => current.map(row => row.id === item.id ? { ...row, interested: true } : row)); setError(''); } catch (e) { setError((e as Error).message); } }
  return <section>
    <div className="section-heading"><div><h1>{tr('profile')}</h1><p>{user.role === 'VOLUNTEER' && !user.verified ? tr('underReview') : tr('subtitle')}</p></div></div>
    {user.role !== 'VOLUNTEER' ? <button className="button primary" onClick={apply}>{tr('applyVolunteer')}</button> : <>
      <form className="panel form-stack" onSubmit={save}>
        <label className="checkbox"><input type="checkbox" checked={available} onChange={e => setAvailable(e.target.checked)} />{tr('availability')}</label>
        <fieldset><legend>{tr('categories')}</legend><div className="checkbox-grid">{categories.map(c => <label className="checkbox" key={c}><input type="checkbox" checked={categoriesValue.includes(c)} onChange={e => setCategoriesValue(e.target.checked ? [...categoriesValue, c] : categoriesValue.filter(x => x !== c))} />{tr(categoryKey[c])}</label>)}</div></fieldset>
        <div className="form-grid"><label>{tr('skills')}<input value={skills} onChange={e => setSkills(e.target.value)} /></label><label>{tr('capacity')}<input type="number" min="1" required value={capacity} onChange={e => setCapacity(e.target.value)} /></label></div>
        <div className="form-grid"><label>{copy(language, 'languages')}<input value={languagesValue} onChange={e => setLanguagesValue(e.target.value)} /></label><label>{copy(language, 'transport')}<input value={transport} onChange={e => setTransport(e.target.value)} /></label></div>
        <button className="button primary inline">{tr('save')}</button>
      </form>
      {user.verified && <div className="panel section-spaced"><h2>{copy(language, 'availableTasks')}</h2><div className="form-grid"><label>{tr('category')}<select value={taskCategory} onChange={e => setTaskCategory(e.target.value)}><option value="">{copy(language, 'all')}</option>{categories.map(c => <option key={c} value={c}>{tr(categoryKey[c])}</option>)}</select></label><label>{tr('priority')}<select value={taskUrgency} onChange={e => setTaskUrgency(e.target.value)}><option value="">{copy(language, 'all')}</option>{['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(value => <option key={value} value={value}>{statusText(language, value)}</option>)}</select></label></div><label>{copy(language, 'maxDistance')}<input type="number" min="1" max="500" value={maxDistance} onChange={e => setMaxDistance(e.target.value)} /></label>{opportunities.length ? opportunities.map(item => <div className="review-row" key={item.id}><div><strong>{tr(categoryKey[item.category])} · {statusText(language, item.urgency)}</strong><p>{item.quantity ? `${item.quantity} ${item.unit || ''} · ` : ''}{item.distance_km !== null ? `${item.distance_km} km` : copy(language, 'approximateLocation')}</p><small>{formatDate(item.created_at)}</small></div><button className="button secondary" disabled={item.interested} onClick={() => interest(item)}>{item.interested ? copy(language, 'interestSent') : copy(language, 'expressInterest')}</button></div>) : <p className="muted">{copy(language, 'noOpportunities')}</p>}{moreOpportunities && <button className="button secondary inline list-more" disabled={loadingOpportunities} onClick={loadOpportunities}>{listCopy(language)}</button>}</div>}
      <div className="section-subhead"><h2>{tr('assignments')}</h2></div>
      <RequestList language={language} requests={assignments} onSelect={onSelect} emptyText={tr('noData')} />
    </>}
    {error && <p className="error" role="alert">{error}</p>}
  </section>;
}

export function OrganizationSection({ language, organizations, onRefresh, onUser, assignments, onSelect }: Base & { organizations: Organization[]; onRefresh: () => void; onUser: (user: User) => void; assignments: Need[]; onSelect: (request: Need) => void }) {
  const tr = (key: MessageKey) => t(language, key);
  const [name, setName] = useState(''); const [description, setDescription] = useState(''); const [serviceArea, setServiceArea] = useState(''); const [serviceCategories, setServiceCategories] = useState<string[]>([]); const [orgId, setOrgId] = useState(''); const [title, setTitle] = useState(''); const [category, setCategory] = useState('FOOD'); const [capacity, setCapacity] = useState('1'); const [workload, setWorkload] = useState('0'); const [availableFrom, setAvailableFrom] = useState(''); const [availableUntil, setAvailableUntil] = useState(''); const [expiresAt, setExpiresAt] = useState(''); const [radius, setRadius] = useState('25'); const [latitude, setLatitude] = useState(''); const [longitude, setLongitude] = useState(''); const [resourceDescription, setResourceDescription] = useState(''); const [error, setError] = useState(''); const [ownResources, setOwnResources] = useState<Resource[]>([]);
  const [performance, setPerformance] = useState<Record<string, OrganizationPerformance>>({});
  useEffect(() => { Promise.all(organizations.map(o => api<Resource[]>(`/organizations/${o.id}/resources`))).then(groups => setOwnResources(groups.flat())).catch(() => setOwnResources([])); }, [organizations]);
  useEffect(() => { Promise.all(organizations.map(o => api<OrganizationPerformance>(`/organizations/${o.id}/performance`))).then(rows => setPerformance(Object.fromEntries(rows.map(row => [row.organization_id, row])))).catch(() => setPerformance({})); }, [organizations]);
  async function createOrganization(e: React.FormEvent) { e.preventDefault(); try { await api('/organizations', { method: 'POST', body: JSON.stringify({ name, description, service_area: serviceArea, service_categories: serviceCategories }) }); setName(''); setDescription(''); setServiceArea(''); setServiceCategories([]); setError(''); onUser(await api<User>('/auth/me')); onRefresh(); } catch (err) { setError((err as Error).message); } }
  async function createResource(e: React.FormEvent) { e.preventDefault(); try { await api(`/organizations/${orgId}/resources`, { method: 'POST', body: JSON.stringify({ title, category, capacity: Number(capacity), current_workload: Number(workload), description: resourceDescription, available: true, available_from: availableFrom ? new Date(availableFrom).toISOString() : null, available_until: availableUntil ? new Date(availableUntil).toISOString() : null, expires_at: expiresAt ? new Date(expiresAt).toISOString() : null, service_radius_km: Number(radius), latitude: latitude ? Number(latitude) : null, longitude: longitude ? Number(longitude) : null }) }); setTitle(''); setResourceDescription(''); setError(''); onRefresh(); } catch (err) { setError((err as Error).message); } }
  async function toggleResource(resource: Resource) { try { await api(`/resources/${resource.id}`, { method: 'PATCH', body: JSON.stringify({ available: !resource.available }) }); const groups = await Promise.all(organizations.map(o => api<Resource[]>(`/organizations/${o.id}/resources`))); setOwnResources(groups.flat()); setError(''); onRefresh(); } catch (err) { setError((err as Error).message); } }
  return <section>
    <div className="section-heading"><div><h1>{tr('organization')}</h1><p>{tr('realData')}</p></div></div>
    <OrganizationInvitations language={language} onAccepted={onRefresh} />
    <div className="two-column">
      <form className="panel form-stack" onSubmit={createOrganization}>
        <h2>{tr('createOrganization')}</h2>
        <label>{tr('organizationName')}<input required minLength={3} value={name} onChange={e => setName(e.target.value)} /></label>
        <label>{tr('description')}<textarea value={description} onChange={e => setDescription(e.target.value)} /></label>
        <label>{copy(language, 'serviceArea')}<input value={serviceArea} onChange={e => setServiceArea(e.target.value)} maxLength={240} /></label>
        <fieldset><legend>{tr('categories')}</legend><div className="checkbox-grid">{categories.map(item => <label className="checkbox" key={item}><input type="checkbox" checked={serviceCategories.includes(item)} onChange={e => setServiceCategories(e.target.checked ? [...serviceCategories, item] : serviceCategories.filter(value => value !== item))} />{tr(categoryKey[item])}</label>)}</div></fieldset>
        <button className="button primary inline">{tr('createOrganization')}</button>
      </form>
      <div className="panel"><h2>{tr('organization')}</h2>{organizations.length ? organizations.map(o => <div className="org-row" key={o.id}><strong>{o.name}</strong><span className="status-chip">{statusText(language, o.status)}</span><p>{o.description}</p><small>{o.service_area}</small>{performance[o.id] && <p>{performance[o.id].assignments} {tr('assignments')} · {performance[o.id].active} {statusText(language, 'IN_PROGRESS')} · {performance[o.id].verified_outcomes} {tr('verifiedOutcomes')}{Object.entries(performance[o.id].impact_units).map(([unit, count]) => <span key={unit}> · {count} {unit}</span>)}</p>}{o.membership_role === 'OWNER' && <OrganizationMembers organizationId={o.id} language={language} />}</div>) : <p className="muted">{tr('noOrganizations')}</p>}</div>
    </div>
    {organizations.length > 0 && <form className="panel form-stack section-spaced" onSubmit={createResource}>
      <h2>{tr('createResource')}</h2>
      <div className="form-grid"><label>{tr('organization')}<select required value={orgId} onChange={e => setOrgId(e.target.value)}><option value="">{copy(language, 'selectOrganization')}</option>{organizations.map(o => <option value={o.id} key={o.id}>{o.name}</option>)}</select></label><label>{tr('category')}<select value={category} onChange={e => setCategory(e.target.value)}>{categories.map(c => <option key={c} value={c}>{tr(categoryKey[c])}</option>)}</select></label></div>
      <div className="form-grid"><label>{copy(language, 'resourceTitle')}<input required minLength={3} value={title} onChange={e => setTitle(e.target.value)} /></label><label>{tr('capacity')}<input type="number" required min="1" value={capacity} onChange={e => setCapacity(e.target.value)} /></label></div>
      <div className="form-grid"><label>{copy(language, 'currentWorkload')}<input type="number" min="0" value={workload} onChange={e => setWorkload(e.target.value)} /></label><label>{copy(language, 'serviceRadius')}<input type="number" min="1" max="500" value={radius} onChange={e => setRadius(e.target.value)} /></label></div>
      <div className="form-grid"><label>{copy(language, 'availableFrom')}<input type="datetime-local" value={availableFrom} onChange={e => setAvailableFrom(e.target.value)} /></label><label>{copy(language, 'availableUntil')}<input type="datetime-local" value={availableUntil} onChange={e => setAvailableUntil(e.target.value)} /></label></div>
      <div className="form-grid"><label>{copy(language, 'expires')}<input type="datetime-local" value={expiresAt} onChange={e => setExpiresAt(e.target.value)} /></label><label>{tr('description')}<textarea value={resourceDescription} onChange={e => setResourceDescription(e.target.value)} /></label></div>
      <div className="form-grid"><label>{tr('latitude')}<input type="number" step="any" min="-90" max="90" value={latitude} onChange={e => setLatitude(e.target.value)} /></label><label>{tr('longitude')}<input type="number" step="any" min="-180" max="180" value={longitude} onChange={e => setLongitude(e.target.value)} /></label></div>
      <button className="button primary inline">{tr('createResource')}</button>
    </form>}
    {ownResources.length > 0 && <div className="panel section-spaced"><h2>{copy(language, 'myResources')}</h2>{ownResources.map(r => <div key={r.id}><div className="review-row"><div><strong>{r.title}</strong><p>{tr(categoryKey[r.category])} · {copy(language, 'remainingCapacity')} {r.remaining_capacity} / {r.capacity} · {r.available ? tr('available') : copy(language, 'pause')}</p>{r.expires_at && <small>{copy(language, 'expires')} {formatDate(r.expires_at)}</small>}</div><button className="button secondary" onClick={() => toggleResource(r)}>{r.available ? copy(language, 'pause') : copy(language, 'resume')}</button></div><ResourceEditor language={language} resource={r} onUpdated={updated => { setOwnResources(current => current.map(item => item.id === updated.id ? updated : item)); onRefresh(); }} /><CapacityHistory resourceId={r.id} language={language} /></div>)}</div>}
    <div className="section-subhead"><h2>{tr('assignments')}</h2></div>
    <RequestList language={language} requests={assignments} onSelect={onSelect} emptyText={tr('noData')} />
    {error && <p className="error" role="alert">{error}</p>}
  </section>;
}

function localDateTime(value: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

function ResourceEditor({ language, resource, onUpdated }: Base & { resource: Resource; onUpdated: (resource: Resource) => void }) {
  const [capacity, setCapacity] = useState(String(resource.capacity));
  const [workload, setWorkload] = useState(String(resource.current_workload));
  const [radius, setRadius] = useState(String(resource.service_radius_km));
  const [from, setFrom] = useState(localDateTime(resource.available_from));
  const [until, setUntil] = useState(localDateTime(resource.available_until));
  const [expiry, setExpiry] = useState(localDateTime(resource.expires_at));
  const [error, setError] = useState('');
  async function save(event: React.FormEvent) {
    event.preventDefault();
    try {
      const result = await api<Resource>(`/resources/${resource.id}`, { method: 'PATCH', body: JSON.stringify({ capacity: Number(capacity), current_workload: Number(workload), service_radius_km: Number(radius), available_from: from ? new Date(from).toISOString() : null, available_until: until ? new Date(until).toISOString() : null, expires_at: expiry ? new Date(expiry).toISOString() : null }) });
      onUpdated(result); setError('');
    } catch (e) { setError((e as Error).message); }
  }
  return <form className="resource-editor form-stack" onSubmit={save}>
    <div className="form-grid"><label>{t(language, 'capacity')}<input type="number" min="1" required value={capacity} onChange={e => setCapacity(e.target.value)} /></label><label>{copy(language, 'currentWorkload')}<input type="number" min="0" required value={workload} onChange={e => setWorkload(e.target.value)} /></label></div>
    <div className="form-grid"><label>{copy(language, 'availableFrom')}<input type="datetime-local" value={from} onChange={e => setFrom(e.target.value)} /></label><label>{copy(language, 'availableUntil')}<input type="datetime-local" value={until} onChange={e => setUntil(e.target.value)} /></label></div>
    <div className="form-grid"><label>{copy(language, 'expires')}<input type="datetime-local" value={expiry} onChange={e => setExpiry(e.target.value)} /></label><label>{copy(language, 'serviceRadius')}<input type="number" min="1" max="500" value={radius} onChange={e => setRadius(e.target.value)} /></label></div>
    <button className="button secondary inline">{copy(language, 'saveCapacity')}</button>
    {error && <p className="error" role="alert">{error}</p>}
  </form>;
}

export function TrustSection({ language, headingLevel = 1, variant = 'workspace' }: Base & { headingLevel?: 1 | 2; variant?: 'workspace' | 'public' }) {
  const tr = (key: MessageKey) => t(language, key);
  const Heading = headingLevel === 1 ? 'h1' : 'h2';
  if (variant === 'public') {
    const safeguards = [
      { icon: CheckCircle2, title: copy(language, 'trustVerificationTitle'), body: copy(language, 'trustVerificationBody') },
      { icon: Clock3, title: copy(language, 'trustPriorityTitle'), body: copy(language, 'trustPriorityBody') },
      { icon: MapPin, title: copy(language, 'trustLocationTitle'), body: copy(language, 'trustLocationBody') },
      { icon: HeartHandshake, title: copy(language, 'trustImpactTitle'), body: copy(language, 'trustImpactBody') },
    ];
    const deeperChecks = [
      { title: trustCopy(language, 'aiTitle'), body: trustCopy(language, 'aiBody') },
      { title: trustCopy(language, 'sourceTitle'), body: trustCopy(language, 'sourceBody') },
      { title: trustCopy(language, 'safetyTitle'), body: trustCopy(language, 'safetyBody') },
      { title: trustCopy(language, 'auditTitle'), body: trustCopy(language, 'auditBody') },
    ];
    return <div className="trust-story">
      <div className="trust-story-head">
        <div className="trust-story-intro"><Heading>{tr('trustTitle')}</Heading><p>{tr('realData')}</p></div>
        <div className="trust-story-promise"><span className="trust-promise-icon"><LockKeyhole size={25} /></span><strong>{tr('privacy')}</strong><p>{tr('privacyText')}</p></div>
      </div>
      <div className="trust-path">{safeguards.map((item, index) => { const Icon = item.icon; return <article key={item.title} className="trust-path-step"><div className="trust-path-top"><span>{String(index + 1).padStart(2, '0')}</span><Icon size={23} strokeWidth={1.8} /></div><h3>{item.title}</h3><p>{item.body}</p></article>; })}</div>
      <div className="trust-deeper-checks">{deeperChecks.map(item => <details key={item.title}><summary>{item.title}<ArrowRight size={17} aria-hidden="true" /></summary><p>{item.body}</p></details>)}</div>
      <div className="safety-note trust-safety-note">{tr('clinical')}</div>
    </div>;
  }
  return <section className="trust-content"><Heading>{tr('trustTitle')}</Heading><p className="lead">{tr('realData')}</p><div className="trust-list"><article><ShieldIcon /><h2>{copy(language, 'trustVerificationTitle')}</h2><p>{copy(language, 'trustVerificationBody')}</p></article><article><Clock3 size={25} /><h2>{copy(language, 'trustPriorityTitle')}</h2><p>{copy(language, 'trustPriorityBody')}</p></article><article><MapPin size={25} /><h2>{copy(language, 'trustLocationTitle')}</h2><p>{copy(language, 'trustLocationBody')}</p></article><article><HeartHandshake size={25} /><h2>{copy(language, 'trustImpactTitle')}</h2><p>{copy(language, 'trustImpactBody')}</p></article><article><CircleHelp size={25} /><h2>{trustCopy(language, 'aiTitle')}</h2><p>{trustCopy(language, 'aiBody')}</p></article><article><FileText size={25} /><h2>{trustCopy(language, 'sourceTitle')}</h2><p>{trustCopy(language, 'sourceBody')}</p></article><article><LockKeyhole size={25} /><h2>{trustCopy(language, 'safetyTitle')}</h2><p>{trustCopy(language, 'safetyBody')}</p></article><article><CheckCircle2 size={25} /><h2>{trustCopy(language, 'auditTitle')}</h2><p>{trustCopy(language, 'auditBody')}</p></article></div><div className="safety-note">{tr('clinical')}</div></section>;
}

function ShieldIcon() { return <CheckCircle2 size={25} />; }

export function ImpactSection({ language, impact }: Base & { impact: { verified_outcomes: number; by_category: Record<string, { verified_outcomes: number; units: Record<string, number> }>; source: string } | null }) {
  const tr = (key: MessageKey) => t(language, key);
  return <section><h1>{tr('impact')}</h1><p className="lead">{tr('realData')}</p><div className="impact-total"><strong>{impact?.verified_outcomes ?? 0}</strong><span>{tr('verifiedOutcomes')}</span></div>{Object.entries(impact?.by_category || {}).length ? <div className="impact-list">{Object.entries(impact!.by_category).map(([key, value]) => <div key={key}><strong>{tr(categoryKey[key])}</strong><span>{value.verified_outcomes} {tr('verifiedOutcomes').toLowerCase()}</span>{Object.entries(value.units).map(([unit, count]) => <small key={unit}>{count} {unit}</small>)}</div>)}</div> : <div className="empty compact"><Clock3 size={42} /><h2>{tr('noData')}</h2><p>{tr('realData')}</p></div>}</section>;
}
