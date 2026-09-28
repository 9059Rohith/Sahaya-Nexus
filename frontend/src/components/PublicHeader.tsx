'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowUpRight, HeartHandshake, Menu, X } from 'lucide-react';
import { Language, languages, t } from '@/lib/i18n';

type Props = {
  language: Language;
  onLanguageChange: (language: Language) => void;
  signedIn: boolean;
  page: 'home' | 'login' | 'signup';
};
const workspaceLabel: Record<Language, string> = { en: 'Workspace', hi: 'कार्यस्थल', ta: 'பணியிடம்', ml: 'പ്രവർത്തന ഇടം' };

export function PublicHeader({ language, onLanguageChange, signedIn, page }: Props) {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return <header className="site-header">
    <div className="site-header-inner">
      <Link href="/" className="site-brand" onClick={close} aria-label="Sahaya Nexus home">
        <span className="site-brand-icon"><HeartHandshake size={23} strokeWidth={2.1} /></span>
        <span>Sahaya<span className="brand-dot">.</span><small>NEXUS</small></span>
      </Link>
      <nav id="public-navigation" className={`site-nav ${open ? 'open' : ''}`} aria-label="Public navigation">
        <Link href="/" onClick={close} aria-current={page === 'home' ? 'page' : undefined}>{t(language, 'overview')}</Link>
        <Link href="/#how-it-works" onClick={close}>{t(language, 'howWorks')}</Link>
        <Link href="/#causes" onClick={close}>{t(language, 'categories')}</Link>
        <Link href="/#impact" onClick={close}>{t(language, 'impact')}</Link>
        <Link href="/#trust" onClick={close}>{t(language, 'trust')}</Link>
        <div className="site-nav-auth">{signedIn ? <Link href="/app" onClick={close}>{workspaceLabel[language]} <ArrowUpRight size={16} /></Link> : <><Link href="/login" onClick={close}>{t(language, 'signIn')}</Link><Link href="/signup" onClick={close}>{t(language, 'register')} <ArrowUpRight size={16} /></Link></>}</div>
      </nav>
      <div className="site-header-actions">
        <label className="sr-only" htmlFor="public-language">{t(language, 'language')}</label>
        <select id="public-language" value={language} onChange={event => onLanguageChange(event.target.value as Language)}>{languages.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select>
        {signedIn ? <Link className="site-header-cta" href="/app">{workspaceLabel[language]} <ArrowUpRight size={16} /></Link> : <>
          <Link className={`site-login ${page === 'login' ? 'active' : ''}`} href="/login">{t(language, 'signIn')}</Link>
          <Link className={`site-header-cta ${page === 'signup' ? 'active' : ''}`} href="/signup">{t(language, 'register')} <ArrowUpRight size={16} /></Link>
        </>}
      </div>
      <button className="site-menu-toggle" type="button" aria-label={open ? 'Close navigation' : 'Open navigation'} aria-controls="public-navigation" aria-expanded={open} onClick={() => setOpen(value => !value)}>{open ? <X size={24} /> : <Menu size={24} />}</button>
    </div>
  </header>;
}
