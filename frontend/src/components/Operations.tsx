'use client';

import { useEffect, useState } from 'react';
import { ArrowRight, CheckCircle2, CircleAlert, MapPin, ShieldCheck } from 'lucide-react';
import { api, Candidate, Need } from '@/lib/api';
import { Language, MessageKey, statusText, t } from '@/lib/i18n';
import { operationsCopy } from '@/lib/operations-copy';
import { listCopy } from '@/lib/list-copy';
import { retentionCopy } from '@/lib/retention-copy';
import { categoryKey, formatDate, pretty } from './Sections';

const stages = ['SUBMITTED', 'UNDERSTANDING', 'VALIDATION', 'VERIFICATION', 'PRIORITIZATION', 'MATCHING', 'ASSIGNED', 'IN_PROGRESS', 'ACTION_COMPLETED', 'OUTCOME_VERIFIED', 'IMPACT_RECORDED'];
type OrgReview = { id: string; name: string; description: string; status: string };
type VolunteerReview = { id: string; name: string; email: string; verified: boolean; available: boolean; categories: string[] };
type Audit = { id: string; action: string; actor_id: string; entity_type: string; entity_id: string; created_at: string };
type Analytics = { period_days: number; requests: number; resolution_rate: number; mean_hours_to_verification: number | null; mean_hours_to_assignment: number | null; mean_hours_to_action: number | null; assignments: number; category_distribution: Record<string, number>; requests_by_day: Record<string, number> };
type Abuse = { id: string; request_id: string | null; category: string; reason: string; status: string; created_at: string };
type Escalation = { request_id: string; category: string; age_hours: number; threshold_hours: number; reason: string; previous_actions: { status: string; reason: string; created_at: string }[]; next_action: string; follow_up_id: string | null };
type Policy = { feature_flags: Record<string, boolean>; pilot_enabled: boolean; pilot_categories: string[]; pilot_service_areas: string[]; priority_high_hours: number; priority_critical_hours: number; verification_evidence_categories: string[]; service_radius_km: number; escalation_hours: number; retention_days: number | null };

export function Operations({ language, queue, role, onRefresh, hasMore, loadingMore, onLoadMore }: { language: Language; queue: Need[]; role: string; onRefresh: () => void; hasMore: boolean; loadingMore: boolean; onLoadMore: () => void }) {
  const tr = (key: MessageKey) => t(language, key);
  const oc = (key: Parameters<typeof operationsCopy>[1]) => operationsCopy(language, key);
  const weightLabels: Record<string, string> = { category_match: tr('category'), distance: oc('distance'), availability: tr('availability'), reliability: oc('reliability'), urgency_fit: oc('urgencyFit'), capacity_fit: tr('capacity'), response_time: oc('responseTime') };
  const [selected, setSelected] = useState<Need | null>(null);
  const [reason, setReason] = useState('');
  const [priorityChoice, setPriorityChoice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [matches, setMatches] = useState<Candidate[]>([]);
  const [organizations, setOrganizations] = useState<OrgReview[]>([]);
  const [volunteers, setVolunteers] = useState<VolunteerReview[]>([]);
  const [audit, setAudit] = useState<Audit[]>([]);
  const [weights, setWeights] = useState<Record<string, number> | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [analyticsDays, setAnalyticsDays] = useState(30);
  const [health, setHealth] = useState<Record<string, string> | null>(null);
  const [abuse, setAbuse] = useState<Abuse[]>([]);
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [mapsEnabled, setMapsEnabled] = useState(false);

  useEffect(() => {
    api<OrgReview[]>('/admin/organizations').then(setOrganizations).catch(() => {});
    api<VolunteerReview[]>('/admin/volunteers').then(setVolunteers).catch(() => {});
    api<Audit[]>('/admin/audit').then(setAudit).catch(() => {});
    api<{ weights: Record<string, number> }>('/admin/matching-settings').then(result => setWeights(result.weights)).catch(() => {});
    api<Record<string, string>>('/admin/health').then(setHealth).catch(() => {});
    api<Abuse[]>('/admin/reports/abuse').then(setAbuse).catch(() => {});
    api<{ feature_flags: { maps: boolean } }>('/config').then(result => setMapsEnabled(result.feature_flags.maps)).catch(() => {});
    api<Escalation[]>('/admin/escalations').then(setEscalations).catch(() => {});
    if (role === 'ADMIN') api<Policy>('/admin/config').then(setPolicy).catch(() => {});
  }, [queue, role]);
  useEffect(() => { api<Analytics>(`/admin/analytics?days=${analyticsDays}`).then(setAnalytics).catch(() => setAnalytics(null)); }, [analyticsDays, queue]);
  useEffect(() => {
    if (!selected) return;
    const fresh = queue.find(item => item.id === selected.id);
    if (fresh && fresh !== selected) setSelected(fresh);
  }, [queue, selected]);
  useEffect(() => {
    if (selected?.status === 'MATCHING') api<Candidate[]>(`/matching/${selected.id}`).then(setMatches).catch(() => setMatches([]));
    else setMatches([]);
  }, [selected?.id, selected?.status]);

  async function action(path: string, body?: object) {
    setBusy(true); setError('');
    try {
      const result = await api<Need>(path, { method: 'POST', body: JSON.stringify(body || {}) });
      setSelected(result); onRefresh();
      if (result.status === 'MATCHING') setMatches(await api<Candidate[]>(`/matching/${result.id}`));
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function review(type: 'organizations' | 'volunteers', id: string, decision: 'VERIFIED' | 'REJECTED') {
    setBusy(true); setError('');
    try { await api(`/admin/${type}/${id}/verify`, { method: 'POST', body: JSON.stringify({ decision, reason }) }); onRefresh(); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function saveWeights(event: React.FormEvent) { event.preventDefault(); if (!weights) return; setBusy(true); setError(''); try { const result = await api<{ weights: Record<string, number> }>('/admin/matching-settings', { method: 'POST', body: JSON.stringify(weights) }); setWeights(result.weights); } catch (e) { setError((e as Error).message); } finally { setBusy(false); } }
  async function savePolicy(event: React.FormEvent) { event.preventDefault(); if (!policy) return; setBusy(true); setError(''); try { setPolicy(await api<Policy>('/admin/config', { method: 'PUT', body: JSON.stringify(policy) })); } catch (e) { setError((e as Error).message); } finally { setBusy(false); } }
  async function resolveAbuse(item: Abuse, status: 'ACTIONED' | 'DISMISSED') { setBusy(true); setError(''); try { await api(`/admin/reports/abuse/${item.id}/resolve`, { method: 'POST', body: JSON.stringify({ status, resolution: reason }) }); setAbuse(await api<Abuse[]>('/admin/reports/abuse')); } catch (e) { setError((e as Error).message); } finally { setBusy(false); } }
  const next = selected ? stages[stages.indexOf(selected.status) + 1] : undefined;
  const locationReady = selected && selected.latitude !== null && selected.longitude !== null;
  const approxLat = locationReady ? Math.round(selected.latitude! * 20) / 20 : 0;
  const approxLon = locationReady ? Math.round(selected.longitude! * 20) / 20 : 0;
  const mapUrl = mapsEnabled && locationReady ? `https://www.openstreetmap.org/export/embed.html?bbox=${approxLon - 0.05}%2C${approxLat - 0.035}%2C${approxLon + 0.05}%2C${approxLat + 0.035}&layer=mapnik&marker=${approxLat}%2C${approxLon}` : '';

  return <section className="operations"><div className="section-heading"><div><h1>{tr('operations')}</h1><p>{tr('realData')}</p></div><span className="queue-count">{queue.length} {tr('queue').toLowerCase()}</span></div><div className="command-grid">
    <div className="queue-panel"><h2>{tr('queue')}</h2>{queue.length ? queue.map(item => <button key={item.id} onClick={() => setSelected(item)} className={`queue-item ${selected?.id === item.id ? 'selected' : ''}`}><span className={`urgency-dot ${item.urgency.toLowerCase()}`}></span><span><strong>{tr(categoryKey[item.category] || 'publicService')}</strong><small>{item.description}</small><em>{statusText(language, item.status)} · {formatDate(item.created_at)}</em></span></button>) : <p className="muted">{tr('noQueue')}</p>}{hasMore && <button className="button secondary inline list-more" disabled={loadingMore} onClick={onLoadMore}>{listCopy(language)}</button>}</div>
    <div className="map-panel"><div className="map-header"><MapPin size={18} /><strong>{oc('approximateMap')}</strong><span>{selected?.location_text || tr('selectRequest')}</span></div>{mapUrl ? <iframe title={oc('approximateMap')} src={mapUrl} loading="lazy" referrerPolicy="no-referrer" /> : <div className="map-empty"><MapPin size={36} /><p>{selected ? oc('noCoordinates') : tr('selectRequest')}</p></div>}</div>
    <div className="inspection-panel"><h2>{tr('details')}</h2>{selected ? <><span className="small-label">{tr(categoryKey[selected.category] || 'publicService')}</span><p className="inspection-description">{selected.description}</p><dl className="facts"><div><dt>{tr('status')}</dt><dd>{statusText(language, selected.status)}</dd></div><div><dt>{tr('verification')}</dt><dd>{statusText(language, selected.verification)}</dd></div><div><dt>{tr('priority')}</dt><dd>{statusText(language, selected.urgency)}<small>{selected.priority_reason}</small></dd></div><div><dt>{tr('location')}</dt><dd>{selected.location_text}</dd></div></dl><label className="form-label">{tr('reason')}<textarea minLength={8} value={reason} onChange={e => setReason(e.target.value)} /></label>
      {selected.status === 'VERIFICATION' ? <div className="action-row"><button className="button primary" disabled={busy || reason.length < 8 || selected.verification === 'VERIFIED'} onClick={() => action(`/admin/requests/${selected.id}/verify`, { decision: 'VERIFIED', reason })}><ShieldCheck size={17} />{tr('verify')}</button><button className="button danger" disabled={busy || reason.length < 8} onClick={() => action(`/admin/requests/${selected.id}/verify`, { decision: 'REJECTED', reason })}>{tr('reject')}</button></div> : null}
      {next && !['ASSIGNED', 'IN_PROGRESS', 'ACTION_COMPLETED', 'OUTCOME_VERIFIED', 'IMPACT_RECORDED'].includes(next) && <button className="button primary full" disabled={busy || reason.length < 8 || (next === 'PRIORITIZATION' && selected.verification !== 'VERIFIED')} onClick={() => action(`/admin/requests/${selected.id}/transition`, { to_status: next, reason })}>{tr('nextStage')} <ArrowRight size={17} /></button>}
      {selected.status === 'MATCHING' && <div className="candidates"><h3>{tr('candidates')}</h3>{matches.length ? matches.map(match => <div className="candidate" key={match.id}><div><strong>{match.name}</strong><span>{match.organization || pretty(match.type)} · {match.score}/100 {match.interested && `· ${oc('expressedAvailability')}`}</span><small>{match.why.join(' · ')}</small></div><button className="button secondary" disabled={busy || reason.length < 8} onClick={() => action(`/admin/requests/${selected.id}/assign`, { resource_id: match.type === 'resource' ? match.id : null, volunteer_id: match.type === 'volunteer' ? match.id : null, reason })}>{tr('assign')}</button></div>) : <p className="muted">{tr('noCandidates')}</p>}</div>}
      {selected.status === 'OUTCOME_VERIFIED' && <button className="button primary full" disabled={busy} onClick={() => action(`/admin/requests/${selected.id}/record-impact`)}>{tr('recordImpact')}</button>}
      {selected.status === 'ESCALATED' && <button className="button primary full" disabled={busy || reason.length < 8 || Boolean(selected.details.follow_up_id)} onClick={() => action(`/admin/requests/${selected.id}/follow-up`, { reason })}>{oc('followUp')}</button>}
      {['PRIORITIZATION', 'MATCHING', 'ASSIGNED', 'IN_PROGRESS'].includes(selected.status) && <div className="priority-override"><label className="form-label">{oc('priorityOverride')}<select value={priorityChoice || selected.urgency} onChange={e => setPriorityChoice(e.target.value)}>{['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(value => <option value={value} key={value}>{statusText(language, value)}</option>)}</select></label><button className="button secondary" disabled={busy || reason.length < 8} onClick={() => action(`/admin/requests/${selected.id}/priority`, { urgency: priorityChoice || selected.urgency, reason })}>{oc('savePriority')}</button></div>}
    </> : <p className="muted">{tr('selectRequest')}</p>}</div>
  </div>
  <div className="review-columns"><div className="panel"><h2>{tr('pendingOrganizations')}</h2>{organizations.filter(o => o.status === 'UNDER_REVIEW').length ? organizations.filter(o => o.status === 'UNDER_REVIEW').map(o => <div className="review-row" key={o.id}><div><strong>{o.name}</strong><p>{o.description}</p></div><div><button className="button secondary" disabled={busy || reason.length < 8} onClick={() => review('organizations', o.id, 'VERIFIED')}><CheckCircle2 size={16} />{tr('verify')}</button><button className="text-button" disabled={busy || reason.length < 8} onClick={() => review('organizations', o.id, 'REJECTED')}>{tr('reject')}</button></div></div>) : <p className="muted">{tr('noOrganizations')}</p>}</div><div className="panel"><h2>{tr('pendingVolunteers')}</h2>{volunteers.filter(v => !v.verified).length ? volunteers.filter(v => !v.verified).map(v => <div className="review-row" key={v.id}><div><strong>{v.name}</strong><p>{v.email}</p></div><button className="button secondary" disabled={busy || reason.length < 8} onClick={() => review('volunteers', v.id, 'VERIFIED')}><CheckCircle2 size={16} />{tr('verify')}</button></div>) : <p className="muted">{tr('noVolunteers')}</p>}</div></div>
  <div className="panel audit-panel"><h2>{oc('auditTrail')}</h2>{audit.length ? <div className="audit-list">{audit.slice(0, 12).map(entry => <div key={entry.id}><strong>{pretty(entry.action.replaceAll('.', ' '))}</strong><span>{entry.entity_type} · {entry.entity_id.slice(0, 8)}</span><small>{formatDate(entry.created_at)}</small></div>)}</div> : <p className="muted">{oc('noAudit')}</p>}</div>
  <div className="panel section-spaced"><h2>{oc('escalations')}</h2>{escalations.length ? escalations.map(item => <div className="review-row" key={item.request_id}><div><strong>{tr(categoryKey[item.category] || 'publicService')} · {item.age_hours} {oc('hoursOld')}</strong><p>{item.reason}</p><small>{oc('threshold')} {item.threshold_hours} h · {item.previous_actions.length} {oc('recordedActions')} · {item.next_action}</small></div><button className="button secondary" onClick={() => { const found = queue.find(row => row.id === item.request_id); if (found) setSelected(found); }}>{oc('review')}</button></div>) : <p className="muted">{oc('noEscalations')}</p>}</div>
  <div className="two-column section-spaced"><div className="panel"><div className="section-heading"><div><h2>{oc('analytics')}</h2><p>{oc('realPeriod')}</p></div><label>{oc('period')}<select value={analyticsDays} onChange={e => setAnalyticsDays(Number(e.target.value))}>{[7, 30, 90, 365].map(days => <option value={days} key={days}>{days} {oc('days')}</option>)}</select></label></div>{analytics && <><div className="metric-grid"><div><strong>{analytics.requests}</strong><span>{tr('myRequests')}</span></div><div><strong>{Math.round(analytics.resolution_rate * 100)}%</strong><span>{oc('resolutionRate')}</span></div><div><strong>{analytics.assignments}</strong><span>{tr('assignments')}</span></div></div><dl className="facts"><div><dt>{oc('meanVerification')}</dt><dd>{analytics.mean_hours_to_verification ?? '—'} h</dd></div><div><dt>{oc('meanAssignment')}</dt><dd>{analytics.mean_hours_to_assignment ?? '—'} h</dd></div><div><dt>{oc('meanAction')}</dt><dd>{analytics.mean_hours_to_action ?? '—'} h</dd></div></dl><h3>{oc('categoryDistribution')}</h3>{Object.entries(analytics.category_distribution).length ? Object.entries(analytics.category_distribution).map(([key, count]) => <p key={key}>{tr(categoryKey[key] || 'publicService')}: {count}</p>) : <p className="muted">{oc('noPeriodRequests')}</p>}</>}</div><div className="panel"><h2>{oc('systemHealth')}</h2>{health ? <dl className="facts">{Object.entries(health).map(([key, value]) => <div key={key}><dt>{pretty(key)}</dt><dd>{pretty(value)}</dd></div>)}</dl> : <p className="muted">{oc('healthUnavailable')}</p>}</div></div>
  <div className="panel section-spaced"><h2>{oc('safetyReports')}</h2>{abuse.filter(item => item.status === 'OPEN').length ? abuse.filter(item => item.status === 'OPEN').map(item => <div className="review-row" key={item.id}><div><strong>{pretty(item.category)}</strong><p>{item.reason}</p><small>{formatDate(item.created_at)}</small></div><div className="action-row"><button className="button secondary" disabled={busy || reason.length < 8} onClick={() => resolveAbuse(item, 'ACTIONED')}>{oc('actioned')}</button><button className="text-button" disabled={busy || reason.length < 8} onClick={() => resolveAbuse(item, 'DISMISSED')}>{oc('dismiss')}</button></div></div>) : <p className="muted">{oc('noSafety')}</p>}</div>
  {role === 'ADMIN' && weights && <form className="panel weight-panel" onSubmit={saveWeights}><div><h2>{oc('matchingWeights')}</h2><p>{oc('weightsHint')}</p></div><div className="weight-grid">{Object.entries(weights).map(([key, value]) => <label key={key}>{weightLabels[key] || key}<input type="number" min="0" max="1" step="0.01" value={value} onChange={e => setWeights({ ...weights, [key]: Number(e.target.value) })} /></label>)}</div><button className="button secondary" disabled={busy}>{oc('saveWeights')}</button></form>}
  {role === 'ADMIN' && policy && <form className="panel form-stack section-spaced" onSubmit={savePolicy}><h2>{oc('platformPolicy')}</h2><p>{oc('policyHint')}</p><fieldset><legend>{oc('featureFlags')}</legend><div className="checkbox-grid">{Object.entries(policy.feature_flags).map(([key, value]) => <label className="checkbox" key={key}><input type="checkbox" checked={value} onChange={e => setPolicy({ ...policy, feature_flags: { ...policy.feature_flags, [key]: e.target.checked } })} />{pretty(key)}</label>)}</div></fieldset><label className="checkbox"><input type="checkbox" checked={policy.pilot_enabled} onChange={e => setPolicy({ ...policy, pilot_enabled: e.target.checked })} />{oc('pilotLimit')}</label><div className="form-grid"><label>{oc('pilotAreas')}<input value={policy.pilot_service_areas.join(', ')} onChange={e => setPolicy({ ...policy, pilot_service_areas: e.target.value.split(',').map(x => x.trim()).filter(Boolean) })} /></label><label>{oc('pilotCategories')}<input value={policy.pilot_categories.join(', ')} onChange={e => setPolicy({ ...policy, pilot_categories: e.target.value.split(',').map(x => x.trim().toUpperCase()).filter(Boolean) })} /></label></div><div className="form-grid"><label>{oc('highHours')}<input type="number" min="1" max="168" value={policy.priority_high_hours} onChange={e => setPolicy({ ...policy, priority_high_hours: Number(e.target.value) })} /></label><label>{oc('criticalHours')}<input type="number" min="1" max="48" value={policy.priority_critical_hours} onChange={e => setPolicy({ ...policy, priority_critical_hours: Number(e.target.value) })} /></label></div><div className="form-grid"><label>{oc('defaultRadius')}<input type="number" min="1" max="500" value={policy.service_radius_km} onChange={e => setPolicy({ ...policy, service_radius_km: Number(e.target.value) })} /></label><label>{oc('escalationThreshold')}<input type="number" min="1" max="720" value={policy.escalation_hours} onChange={e => setPolicy({ ...policy, escalation_hours: Number(e.target.value) })} /></label></div><label>{oc('evidenceCategories')}<input value={policy.verification_evidence_categories.join(', ')} onChange={e => setPolicy({ ...policy, verification_evidence_categories: e.target.value.split(',').map(x => x.trim().toUpperCase()).filter(Boolean) })} /></label><label>{retentionCopy(language)}<input type="number" min="30" max="3650" value={policy.retention_days ?? ''} onChange={e => setPolicy({ ...policy, retention_days: e.target.value ? Number(e.target.value) : null })} /></label><button className="button primary inline" disabled={busy}>{oc('savePolicy')}</button></form>}
  {error && <p className="error" role="alert"><CircleAlert size={17} />{error}</p>}
  </section>;
}
