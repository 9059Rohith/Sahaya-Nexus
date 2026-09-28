import type { Metadata } from 'next';
import SahayaApp from '@/components/SahayaApp';

export const metadata: Metadata = { title: 'Create account | Sahaya Nexus' };

export default function SignUpPage() {
  return <SahayaApp view="signup" />;
}
