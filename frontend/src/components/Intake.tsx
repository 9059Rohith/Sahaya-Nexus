'use client';

import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, MapPin, Mic, ShieldCheck, Square } from 'lucide-react';
import { api, ApiError, Need } from '@/lib/api';
import { Language, MessageKey, statusText, t } from '@/lib/i18n';
import { copy } from '@/lib/copy';
import { offlineCopy } from '@/lib/offline-copy';

const categories = [
  ['FOOD', 'food'], ['BLOOD', 'blood'], ['ACCESSIBILITY', 'accessibility'], ['COMMUNITY', 'community'],
  ['VOLUNTEER', 'volunteer'], ['RESOURCE', 'resource'], ['PUBLIC_SERVICE', 'publicService'],
] as const;

type Interpretation = { category: string; description: string; quantity: number | null; unit: string | null; urgency: string; confidence: number; safety_flags: string[]; missing_fields: string[]; provider: string };
type QueuedSubmission = { payload: Record<string, unknown>; sameIssueId: string; savedAt: string };
type Props = { language: Language; userId: string; onCreated: (request: Need) => void; initialText?: string };

export function Intake({ language, userId, onCreated, initialText = '' }: Props) {
  const [text, setText] = useState(initialText);
  const [stage, setStage] = useState<'entry' | 'review'>('entry');
  const [interpretation, setInterpretation] = useState<Interpretation | null>(null);
  const [category, setCategory] = useState('PUBLIC_SERVICE');
  const [location, setLocation] = useState('');
  const [latitude, setLatitude] = useState<number | undefined>();
  const [longitude, setLongitude] = useState<number | undefined>();
  const [precision, setPrecision] = useState('APPROXIMATE');
  const [publicIssue, setPublicIssue] = useState(false);
  const [quantity, setQuantity] = useState('');
  const [unit, setUnit] = useState('');
  const [safeUntil, setSafeUntil] = useState('');
  const [foodType, setFoodType] = useState('');
  const [preparedTime, setPreparedTime] = useState('');
  const [pickupWindow, setPickupWindow] = useState('');
  const [packaging, setPackaging] = useState('');
  const [dietaryNotes, setDietaryNotes] = useState('');
  const [facility, setFacility] = useState('');
  const [barrierType, setBarrierType] = useState('');
  const [affectedUsers, setAffectedUsers] = useState('');
  const [severity, setSeverity] = useState('');
  const [issueType, setIssueType] = useState('');
  const [deadline, setDeadline] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [duplicates, setDuplicates] = useState<number | null>(null);
  const [duplicateOptions, setDuplicateOptions] = useState<{ id: string; issue_type: string; status: string; created_at: string }[]>([]);
  const [confirmSameId, setConfirmSameId] = useState('');
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [recording, setRecording] = useState(false);
  const [pending, setPending] = useState<QueuedSubmission | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const tr = (key: MessageKey) => t(language, key);
  const queueKey = `sahaya_pending_${userId}`;

  useEffect(() => {
    try {
      const saved = localStorage.getItem(queueKey);
      if (saved) {
        const parsed = JSON.parse(saved) as QueuedSubmission;
        if (parsed?.payload?.client_submission_id && parsed.payload.description) setPending(parsed);
      }
    } catch { /* Keep the form available when old device data is unreadable. */ }
  }, [queueKey]);

  useEffect(() => {
    const draft = localStorage.getItem('sahaya_draft');
    if (draft && !initialText) setText(draft);
  }, [initialText]);
  useEffect(() => { if (text) localStorage.setItem('sahaya_draft', text); }, [text]);
  useEffect(() => {
    api<{ feature_flags: { voice: boolean } }>('/config').then(result => setVoiceEnabled(result.feature_flags.voice)).catch(() => {});
    return () => { if (recorder.current?.state === 'recording') recorder.current.stop(); stream.current?.getTracks().forEach(track => track.stop()); };
  }, []);

  async function toggleRecording() {
    if (recording) { recorder.current?.stop(); setRecording(false); return; }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') { setError(copy(language, 'voiceUnavailable')); return; }
    const mime = ['audio/webm', 'audio/ogg'].find(value => MediaRecorder.isTypeSupported(value));
    if (!mime) { setError(copy(language, 'voiceUnavailable')); return; }
    try {
      setError('');
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.current = media;
      const current = new MediaRecorder(media, { mimeType: mime });
      const chunks: BlobPart[] = [];
      current.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
      current.onstop = async () => {
        media.getTracks().forEach(track => track.stop());
        setBusy(true);
        try {
          const audio = new Blob(chunks, { type: mime });
          const form = new FormData(); form.set('file', audio, 'request-audio.webm');
          const response = await fetch('/api/v1/speech/transcribe', { method: 'POST', body: form });
          const result = await response.json();
          if (!response.ok) throw new Error(copy(language, 'transcriptionUnavailable'));
          setText(result.text);
        } catch (err) { setError((err as Error).message); }
        finally { setBusy(false); }
      };
      recorder.current = current; current.start(); setRecording(true);
    } catch { setError(copy(language, 'voiceUnavailable')); }
  }

  async function understand() {
    setError('');
    setBusy(true);
    try {
      const result = await api<Interpretation>('/requests/interpret', { method: 'POST', body: JSON.stringify({ text }) });
      setInterpretation(result);
      setCategory(result.category);
      setQuantity(result.quantity?.toString() || '');
      setUnit(result.unit || '');
      setStage('review');
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  async function sendRequest(payload: Record<string, unknown>, sameIssueId: string) {
    let request = await api<Need>('/requests', { method: 'POST', body: JSON.stringify(payload) });
    localStorage.removeItem(queueKey);
    setPending(null);
    if (sameIssueId && payload.category === 'COMMUNITY') {
      try { request = await api<Need>(`/requests/${request.id}/duplicates/${sameIssueId}/confirm`, { method: 'POST' }); }
      catch (e) { setError((e as Error).message); }
    }
    localStorage.removeItem('sahaya_draft');
    setText('');
    onCreated(request);
  }

  async function sendPending() {
    if (!pending || busy) return;
    setBusy(true); setError('');
    try { await sendRequest(pending.payload, pending.sameIssueId); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  function discardPending() {
    localStorage.removeItem(queueKey);
    setPending(null);
    setError('');
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (pending) { setError(offlineCopy(language, 'pending')); return; }
    setError('');
    setBusy(true);
    const payload: Record<string, unknown> = {
      client_submission_id: crypto.randomUUID(),
      category, description: text, location_text: location, latitude, longitude, location_precision: precision,
      visibility_scope: publicIssue && ['COMMUNITY', 'ACCESSIBILITY'].includes(category) ? 'PUBLIC' : 'PRIVATE',
      quantity: quantity ? Number(quantity) : null, unit: unit || null, deadline: deadline ? new Date(deadline).toISOString() : null,
      details: {
        ...(category === 'FOOD' ? { safe_until: safeUntil ? new Date(safeUntil).toISOString() : '', food_type: foodType, prepared_time: preparedTime ? new Date(preparedTime).toISOString() : '', pickup_window: pickupWindow, packaging, dietary_notes: dietaryNotes } : {}),
        ...(category === 'BLOOD' ? { facility_name: facility } : {}),
        ...(category === 'ACCESSIBILITY' ? { barrier_type: barrierType, affected_users: affectedUsers, severity } : {}),
        ...(category === 'COMMUNITY' ? { issue_type: issueType } : {}),
      },
    };
    try { await sendRequest(payload, confirmSameId); }
    catch (e) {
      if (!navigator.onLine || e instanceof TypeError || (e instanceof ApiError && [502, 503, 504].includes(e.status))) {
        try {
          const saved = { payload, sameIssueId: confirmSameId, savedAt: new Date().toISOString() };
          localStorage.setItem(queueKey, JSON.stringify(saved));
          setPending(saved);
          setError(offlineCopy(language, 'saved'));
        } catch { setError(offlineCopy(language, 'unavailable')); }
      } else setError((e as Error).message);
    }
    finally { setBusy(false); }
  }

  function locate() {
    if (!navigator.geolocation) { setError('Geolocation is unavailable in this browser. Enter your area manually.'); return; }
    navigator.geolocation.getCurrentPosition(({ coords }) => {
      setLatitude(coords.latitude); setLongitude(coords.longitude);
      if (!location) setLocation(`${coords.latitude.toFixed(4)}, ${coords.longitude.toFixed(4)}`);
    }, () => setError('Location permission was not granted. Enter your area manually.'), { enableHighAccuracy: false, timeout: 10000 });
  }

  async function checkDuplicates() {
    setError('');
    try { const result = await api<{ count: number; matches: { id: string; issue_type: string; status: string; created_at: string }[] }>('/requests/duplicates', { method: 'POST', body: JSON.stringify({ category, description: text, location_text: location, latitude, longitude }) }); setDuplicates(result.count); setDuplicateOptions(result.matches); setConfirmSameId(''); }
    catch (e) { setError((e as Error).message); }
  }

  return <section className="intake" aria-labelledby="intake-heading">
    {pending && <div className="offline-queue" role="status"><h2>{offlineCopy(language, 'title')}</h2><p>{offlineCopy(language, 'notice')}</p><blockquote>{String(pending.payload.description)}</blockquote><p>{String(pending.payload.location_text)}</p><div className="intake-actions"><button type="button" className="button primary" disabled={busy} onClick={sendPending}>{offlineCopy(language, 'send')}</button><button type="button" className="button secondary" disabled={busy} onClick={discardPending}>{offlineCopy(language, 'discard')}</button></div></div>}
    {stage === 'entry' ? <>
      <h1 id="intake-heading">{tr('howHelp')}</h1>
      <p className="lead">{tr('describe')}</p>
      <label className="sr-only" htmlFor="need-text">{tr('description')}</label>
      <textarea id="need-text" className="need-input" rows={5} maxLength={3000} minLength={10} value={text} onChange={e => setText(e.target.value)} placeholder={tr('example')} />
      <div className="intake-actions"><span className="character-count">{text.length}/3000</span>{voiceEnabled && <button type="button" className="button secondary" disabled={busy} onClick={toggleRecording}>{recording ? <><Square size={17} /> {copy(language, 'stopRecording')}</> : <><Mic size={17} /> {copy(language, 'recordVoice')}</>}</button>}<button className="button primary" disabled={busy || text.trim().length < 10} onClick={understand}>{busy ? tr('loading') : tr('continue')} <ArrowRight size={18} /></button></div>
    </> : <>
      <button className="text-button" onClick={() => setStage('entry')}><ArrowLeft size={17} /> {tr('back')}</button>
      <h1 id="intake-heading">{tr('interpretation')}</h1>
      <p className="lead">{tr('reviewHint')}</p>
      {interpretation && <div className="interpret-note"><ShieldCheck size={20} /><div><strong>{interpretation.provider === 'rule_based' ? copy(language, 'localRules') : interpretation.provider}</strong><p>{interpretation.confidence < 0.5 ? tr('lowConfidence') : `${copy(language, 'suggestedCategory')}: ${tr(categories.find(([value]) => value === interpretation.category)?.[1] || 'publicService')}. ${copy(language, 'confidence')} ${Math.round(interpretation.confidence * 100)}%.`}</p></div></div>}
      <form onSubmit={submit} className="form-stack">
        <label>{tr('description')}<textarea required minLength={12} maxLength={3000} rows={4} value={text} onChange={e => setText(e.target.value)} /></label>
        <div className="form-grid"><label>{tr('category')}<select value={category} onChange={e => setCategory(e.target.value)}>{categories.map(([value, key]) => <option value={value} key={value}>{tr(key)}</option>)}</select></label><label>{tr('location')}<input required minLength={3} value={location} onChange={e => setLocation(e.target.value)} placeholder={copy(language, 'areaPlaceholder')} /></label></div>
        <button type="button" className="button secondary inline" onClick={locate}><MapPin size={17} /> {tr('useLocation')}</button>
        <div className="form-grid"><label>{tr('latitude')}<input type="number" step="any" min="-90" max="90" value={latitude ?? ''} onChange={e => setLatitude(e.target.value ? Number(e.target.value) : undefined)} /></label><label>{tr('longitude')}<input type="number" step="any" min="-180" max="180" value={longitude ?? ''} onChange={e => setLongitude(e.target.value ? Number(e.target.value) : undefined)} /></label></div>
        <label>{tr('locationPrivacy')}<select value={precision} onChange={e => setPrecision(e.target.value)}><option value="PRIVATE">{statusText(language, 'PRIVATE')}</option><option value="APPROXIMATE">{statusText(language, 'APPROXIMATE')}</option><option value="EXACT">{statusText(language, 'EXACT')}</option></select></label>
        {['COMMUNITY', 'ACCESSIBILITY'].includes(category) && <label className="checkbox"><input type="checkbox" checked={publicIssue} onChange={e => setPublicIssue(e.target.checked)} />{copy(language, 'publicOptIn')}</label>}
        {category === 'COMMUNITY' && <div className="duplicate-check"><button type="button" className="button secondary inline" disabled={location.length < 3 || text.length < 12} onClick={checkDuplicates}>{copy(language, 'checkSimilar')}</button>{duplicates !== null && <p role="status">{duplicates === 0 ? copy(language, 'noSimilar') : `${duplicates} ${copy(language, 'similarFound')}`}</p>}{duplicateOptions.length > 0 && <fieldset><legend>{copy(language, 'sameIssue')}</legend><label className="checkbox"><input type="radio" name="duplicate" checked={confirmSameId === ''} onChange={() => setConfirmSameId('')} />{copy(language, 'separateReport')}</label>{duplicateOptions.map(item => <label className="checkbox" key={item.id}><input type="radio" name="duplicate" checked={confirmSameId === item.id} onChange={() => setConfirmSameId(item.id)} />{copy(language, 'confirmSameIssue')}: {item.issue_type} · {statusText(language, item.status)}</label>)}</fieldset>}</div>}
        {(category === 'FOOD' || quantity) && <div className="form-grid"><label>{tr('quantity')}<input type="number" min="1" required={category === 'FOOD'} value={quantity} onChange={e => setQuantity(e.target.value)} /></label><label>{tr('unit')}<input value={unit} maxLength={48} onChange={e => setUnit(e.target.value)} placeholder="meals, packets, people" /></label></div>}
        {category === 'FOOD' && <label>{tr('safeUntil')}<input required type="datetime-local" value={safeUntil} onChange={e => setSafeUntil(e.target.value)} /></label>}
        {category === 'FOOD' && <><div className="form-grid"><label>{copy(language, 'foodType')}<input value={foodType} maxLength={120} onChange={e => setFoodType(e.target.value)} /></label><label>{copy(language, 'preparedTime')}<input type="datetime-local" value={preparedTime} onChange={e => setPreparedTime(e.target.value)} /></label></div><div className="form-grid"><label>{copy(language, 'pickupWindow')}<input value={pickupWindow} maxLength={120} onChange={e => setPickupWindow(e.target.value)} /></label><label>{copy(language, 'packaging')}<input value={packaging} maxLength={120} onChange={e => setPackaging(e.target.value)} /></label></div><label>{copy(language, 'dietaryNotes')}<input value={dietaryNotes} maxLength={300} onChange={e => setDietaryNotes(e.target.value)} /></label></>}
        {category === 'BLOOD' && <><div className="safety-note">{tr('clinical')}</div><label>{tr('facility')}<input required value={facility} onChange={e => setFacility(e.target.value)} /></label></>}
        {category === 'ACCESSIBILITY' && <><div className="form-grid"><label>{copy(language, 'barrierType')}<select value={barrierType} onChange={e => setBarrierType(e.target.value)}><option value="">{copy(language, 'choose')}</option>{['ramp', 'pathway', 'entrance', 'transport', 'other'].map(item => <option value={item} key={item}>{item}</option>)}</select></label><label>{copy(language, 'severity')}<select value={severity} onChange={e => setSeverity(e.target.value)}><option value="">{copy(language, 'choose')}</option><option value="LOW">{statusText(language, 'LOW')}</option><option value="MEDIUM">{statusText(language, 'MEDIUM')}</option><option value="HIGH">{statusText(language, 'HIGH')}</option></select></label></div><label>{copy(language, 'peopleAffected')}<input value={affectedUsers} maxLength={120} onChange={e => setAffectedUsers(e.target.value)} /></label></>}
        {category === 'COMMUNITY' && <label>{copy(language, 'issueType')}<select value={issueType} onChange={e => setIssueType(e.target.value)}><option value="">{copy(language, 'choose')}</option>{['garbage', 'streetlight', 'pothole', 'drainage'].map(item => <option value={item} key={item}>{item}</option>)}</select></label>}
        <label>{tr('deadline')}<input type="datetime-local" value={deadline} onChange={e => setDeadline(e.target.value)} /></label>
        <div className="form-footer"><button className="button primary" disabled={busy || Boolean(pending)}>{busy ? tr('loading') : tr('submit')} <ArrowRight size={18} /></button></div>
      </form>
    </>}
    {error && <p role="alert" className="error">{error}</p>}
  </section>;
}
