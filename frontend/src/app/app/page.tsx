import type { Metadata } from 'next';
import SahayaApp from '@/components/SahayaApp';

export const metadata: Metadata = { title: 'Your workspace | Sahaya Nexus' };

export default function WorkspacePage() {
  return <SahayaApp view="app" />;
}
