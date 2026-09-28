'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import type { Language } from '@/lib/i18n';

type RecordItem = { id: string; previous_capacity: number | null; capacity: number; previous_workload: number | null; workload: number; previous_available: boolean | null; available: boolean; reason: string; created_at: string };
const labels = {
  en: { title: 'Capacity history', refresh: 'Refresh history', capacity: 'Capacity', workload: 'Workload', available: 'Available', paused: 'Paused', empty: 'No changes recorded.' },
  hi: { title: 'क्षमता का इतिहास', refresh: 'इतिहास ताज़ा करें', capacity: 'क्षमता', workload: 'कार्यभार', available: 'उपलब्ध', paused: 'रोका गया', empty: 'कोई बदलाव दर्ज नहीं।' },
  ta: { title: 'திறன் வரலாறு', refresh: 'வரலாற்றைப் புதுப்பி', capacity: 'திறன்', workload: 'பணிச்சுமை', available: 'கிடைக்கும்', paused: 'நிறுத்தப்பட்டது', empty: 'மாற்றங்கள் பதிவாகவில்லை.' },
  ml: { title: 'ശേഷിയുടെ ചരിത്രം', refresh: 'ചരിത്രം പുതുക്കുക', capacity: 'ശേഷി', workload: 'ജോലിഭാരം', available: 'ലഭ്യം', paused: 'നിർത്തി', empty: 'മാറ്റങ്ങളൊന്നും രേഖപ്പെടുത്തിയിട്ടില്ല.' },
} as const;

export function CapacityHistory({ resourceId, language }: { resourceId: string; language: Language }) {
  const [open, setOpen] = useState(false);
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [error, setError] = useState('');
  const words = labels[language];
  async function load() {
    setError('');
    try { setRecords(await api<RecordItem[]>(`/resources/${resourceId}/capacity-history`)); setOpen(true); }
    catch (e) { setError((e as Error).message); }
  }
  return <div className="capacity-history"><button type="button" className="text-button" onClick={open ? () => setOpen(false) : load}>{words.title}</button>
    {open && <div><button type="button" className="text-button" onClick={load}>{words.refresh}</button>{records.length ? <ol>{records.map(row => <li key={row.id}><time dateTime={row.created_at}>{new Date(row.created_at).toLocaleString()}</time><span>{row.reason}</span><span>{words.capacity}: {row.previous_capacity ?? '—'} → {row.capacity}</span><span>{words.workload}: {row.previous_workload ?? '—'} → {row.workload}</span><span>{row.available ? words.available : words.paused}</span></li>)}</ol> : <p>{words.empty}</p>}</div>}
    {error && <p className="error" role="alert">{error}</p>}
  </div>;
}
