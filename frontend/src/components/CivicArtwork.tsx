export function CivicArtwork({ compact = false }: { compact?: boolean }) {
  return <svg className={compact ? 'civic-artwork compact' : 'civic-artwork'} viewBox="0 0 660 390" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="People connecting a request to trusted help">
    <defs>
      <linearGradient id="sahaya-route" x1="62" y1="218" x2="610" y2="104" gradientUnits="userSpaceOnUse"><stop stopColor="#F7B84C"/><stop offset=".52" stopColor="#F4DB83"/><stop offset="1" stopColor="#71D9C6"/></linearGradient>
      <linearGradient id="sahaya-card" x1="220" y1="75" x2="417" y2="295" gradientUnits="userSpaceOnUse"><stop stopColor="#FFFDF6"/><stop offset="1" stopColor="#DCEDE7"/></linearGradient>
      <filter id="sahaya-glow"><feGaussianBlur stdDeviation="12"/></filter>
    </defs>
    <circle cx="330" cy="196" r="165" stroke="#A1C8C2" strokeOpacity=".28" strokeDasharray="3 12"/>
    <circle cx="330" cy="196" r="116" stroke="#A1C8C2" strokeOpacity=".2"/>
    <path d="M32 289C126 298 127 104 243 151C342 191 340 323 453 249C529 199 541 130 628 103" stroke="#F9D261" strokeWidth="21" strokeOpacity=".35" filter="url(#sahaya-glow)"/>
    <path d="M32 289C126 298 127 104 243 151C342 191 340 323 453 249C529 199 541 130 628 103" stroke="url(#sahaya-route)" strokeWidth="4" strokeLinecap="round" strokeDasharray="1 0"/>
    <path d="M105 227l16-41h48l15 41v35h-79v-35Z" fill="#1E5958" stroke="#8ED9C8" strokeWidth="2"/>
    <path d="M99 186l46-37 47 37H99Z" fill="#F6B651"/>
    <rect x="133" y="224" width="24" height="38" rx="5" fill="#9CD9C7"/>
    <rect x="112" y="204" width="13" height="17" rx="3" fill="#F5EBD4"/>
    <rect x="164" y="204" width="13" height="17" rx="3" fill="#F5EBD4"/>
    <rect x="262" y="66" width="142" height="158" rx="25" fill="url(#sahaya-card)" stroke="#8BC6B7" strokeWidth="2"/>
    <rect x="283" y="92" width="61" height="10" rx="5" fill="#B2CFC6"/>
    <rect x="283" y="112" width="91" height="8" rx="4" fill="#C8DBD3"/>
    <path d="M332 170c-26-18-18-43-1-43 10 0 14 9 14 9s4-9 14-9c17 0 25 25-1 43l-13 9-13-9Z" fill="#EF8B7C"/>
    <circle cx="287" cy="243" r="28" fill="#F5B956"/>
    <path d="M261 276c3-21 17-31 27-31 11 0 23 10 26 31" fill="#69B8AC"/>
    <circle cx="287" cy="232" r="15" fill="#F8D5AD"/>
    <path d="M272 230c0-15 8-24 18-24 11 0 17 8 15 22-7-8-19-13-33 2Z" fill="#394C58"/>
    <circle cx="435" cy="232" r="26" fill="#A6DCCD"/>
    <path d="M409 272c2-20 15-31 27-31 13 0 26 11 28 31" fill="#F4B650"/>
    <circle cx="435" cy="225" r="15" fill="#C98968"/>
    <path d="M420 224c1-14 8-22 17-22 10 0 17 8 14 19-8-5-20-4-31 3Z" fill="#273D49"/>
    <path d="M313 270c25 5 51 5 74-2" stroke="#F5D9B3" strokeWidth="14" strokeLinecap="round"/>
    <path d="M318 260c16 11 29 12 42 8" stroke="#C58465" strokeWidth="7" strokeLinecap="round"/>
    <circle cx="52" cy="283" r="10" fill="#F5B956"/><circle cx="607" cy="117" r="11" fill="#8DDBC9"/>
    <path d="M558 70v18M549 79h18M77 102v14M70 109h14M534 314v14M527 321h14" stroke="#F8D577" strokeWidth="3" strokeLinecap="round"/>
    <path d="M533 177c9-16 22-21 36-17-1 17-13 29-32 30M547 177c-1 19-8 31-20 36" stroke="#76C5A1" strokeWidth="4" strokeLinecap="round"/>
    <path d="M220 79c-11-9-14-19-7-30 15 7 21 18 19 32" stroke="#A9D8AA" strokeWidth="4" strokeLinecap="round"/>
  </svg>;
}
