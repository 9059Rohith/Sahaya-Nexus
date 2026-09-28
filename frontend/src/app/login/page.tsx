import type { Metadata } from 'next';
import SahayaApp from '@/components/SahayaApp';

export const metadata: Metadata = { title: 'Sign in | Sahaya Nexus' };

export default function LoginPage() {
  return <SahayaApp view="login" />;
}
