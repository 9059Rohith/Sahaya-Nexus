'use client';

import { useEffect, useRef, useState, type CSSProperties } from 'react';

// The wing movement follows 9059Rohith/asd-new; flight paths are sized for each surface.
const BUTTERFLIES = [
  { id: 'coral', size: 116 }, { id: 'gold', size: 104 },
  { id: 'blue', size: 96 }, { id: 'lilac', size: 94 },
  { id: 'mint', size: 98 }, { id: 'rose', size: 108 },
];
const STARTS = [[8, 14], [65, 12], [22, 64], [68, 70], [7, 40], [58, 48]];
const AMBIENT_STARTS = [[3, 16], [80, 25], [23, 72], [66, 78]];
const AMBIENT_PATHS = [
  [[76, 22], [24, 77], [85, 54]],
  [[13, 64], [70, 11], [27, 75]],
  [[83, 34], [15, 8], [72, 71]],
  [[10, 24], [86, 79], [35, 17]],
];
type GardenVariant = 'hero' | 'ambient';
const between = (low: number, high: number) => low + Math.random() * (high - low);
const viewport = (value: number) => `${value.toFixed(1)}vw`;
const height = (value: number) => `${value.toFixed(1)}vh`;
const percent = (value: number) => `${value.toFixed(1)}%`;
const containerWidth = (value: number) => `${value.toFixed(1)}cqw`;
const containerHeight = (value: number) => `${value.toFixed(1)}cqh`;
const getRandomColor = () => `#${Array.from({ length: 6 }, () => '0123456789ABCDEF'[Math.floor(Math.random() * 16)]).join('')}`;
const AMBIENT_COLORS = ['#81a99c', '#e3b270', '#7bafbb', '#b19bbb', '#a9bb8c'];
const gardenColor = (variant: GardenVariant) => variant === 'ambient' ? AMBIENT_COLORS[Math.floor(Math.random() * AMBIENT_COLORS.length)] : getRandomColor();

type Flight = { id: string; color: string; style: CSSProperties };

function createFlights(variant: GardenVariant): Flight[] {
  const ambient = variant === 'ambient';
  return BUTTERFLIES.slice(0, 4).map((butterfly, index) => {
    const [baseX, baseY] = ambient ? AMBIENT_STARTS[index] : STARTS[index];
    const x = Math.max(2, Math.min(ambient ? 94 : 70, baseX + between(ambient ? -3 : -5, ambient ? 3 : 5)));
    const y = Math.max(6, Math.min(ambient ? 86 : 72, baseY + between(-7, 7)));
    const destinations = ambient
      ? AMBIENT_PATHS[index].map(([targetX, targetY]) => [
        Math.max(4, Math.min(89, targetX + between(-4, 4))),
        Math.max(5, Math.min(84, targetY + between(-5, 5))),
      ])
      : Array.from({ length: 3 }, () => [between(3, 70), between(4, 74)]);
    const xPosition = ambient ? viewport : percent;
    const yPosition = ambient ? height : percent;
    const xDistance = ambient ? viewport : containerWidth;
    const yDistance = ambient ? height : containerHeight;
    const flightTime = between(ambient ? 48 : 34, ambient ? 64 : 48);
    const ambientSize = [0.75, 0.62, 0.88, 0.68][index];
    const heroSize = [1.08, 0.94, 1.16, 0.96][index];
    return {
      id: butterfly.id,
      color: gardenColor(variant),
      style: {
        '--start-x': xPosition(x), '--start-y': yPosition(y),
        '--dx-1': xDistance(destinations[0][0] - x), '--dy-1': yDistance(destinations[0][1] - y),
        '--dx-2': xDistance(destinations[1][0] - x), '--dy-2': yDistance(destinations[1][1] - y),
        '--dx-3': xDistance(destinations[2][0] - x), '--dy-3': yDistance(destinations[2][1] - y),
        '--flight-time': `${flightTime.toFixed(1)}s`,
        '--flight-delay': `${between(-flightTime, 0).toFixed(1)}s`,
        '--wing-time': `${between(1.55, 1.95).toFixed(2)}s`,
        '--butterfly-size': `${Math.round(butterfly.size * (ambient ? ambientSize : heroSize))}px`,
      } as CSSProperties,
    };
  });
}

function Butterfly({ butterfly, wingSource, variant }: { butterfly: Flight; wingSource: string; variant: GardenVariant }) {
  const [color, setColor] = useState(butterfly.color);
  const wing = `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(wingSource.replace('#1cb1f2', color))}`;
  return <span className={`app-butterfly app-butterfly-${butterfly.id}`} style={butterfly.style} onAnimationIteration={event => {
    if (event.target === event.currentTarget && event.animationName === 'app-butterfly-flight') setColor(gardenColor(variant));
  }}>
    <span className="moth-wings">
      <span className="moth-wing-panel moth-wing-panel-left"><span className="moth-wing moth-wing-left" style={{ backgroundImage: `url("${wing}")` }} /></span>
      <span className="moth-wing-panel moth-wing-panel-right"><span className="moth-wing moth-wing-right" style={{ backgroundImage: `url("${wing}")` }} /></span>
      <span className="moth-body" />
    </span>
  </span>;
}

export function ButterflyGarden({ variant = 'hero' }: { variant?: GardenVariant }) {
  const gardenRef = useRef<HTMLDivElement>(null);
  const [flights, setFlights] = useState<Flight[]>([]);
  const [wingSource, setWingSource] = useState('');
  const [visible, setVisible] = useState(true);
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    setFlights(createFlights(variant));
    fetch('/moth-wing.svg').then(response => response.text()).then(setWingSource).catch(() => {});
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => {
      setVisible(!document.hidden);
      setReduced(media.matches || document.documentElement.classList.contains('reduce-motion'));
    };
    const respondToPointer = (event: PointerEvent) => {
      if (document.hidden || media.matches || document.documentElement.classList.contains('reduce-motion')) return;
      const butterflies = gardenRef.current?.querySelectorAll<HTMLElement>('.app-butterfly');
      if (!butterflies?.length) return;

      let nearest: HTMLElement | null = null;
      let nearestDistance = 145;
      butterflies.forEach(butterfly => {
        const rect = butterfly.getBoundingClientRect();
        if (!rect.width || !rect.height) return;
        const distance = Math.hypot(event.clientX - (rect.left + rect.width / 2), event.clientY - (rect.top + rect.height / 2));
        if (distance < nearestDistance) {
          nearest = butterfly;
          nearestDistance = distance;
        }
      });
      if (!nearest) return;

      const butterfly = nearest as HTMLElement;
      const wings = butterfly.querySelector<HTMLElement>('.moth-wings');
      if (!wings) return;
      const rect = butterfly.getBoundingClientRect();
      const direction = Math.sign(rect.left + rect.width / 2 - event.clientX) || 1;
      wings.getAnimations().forEach(animation => animation.cancel());
      butterfly.dataset.fluttering = 'true';
      const flutter = wings.animate([
        { transform: 'translate3d(0, 0, 0) rotate(0deg)', offset: 0 },
        { transform: `translate3d(${direction * 10}px, -9px, 0) rotate(${direction * 3}deg)`, offset: 0.3 },
        { transform: `translate3d(${direction * 20}px, -18px, 0) rotate(${direction * 5}deg)`, offset: 0.55 },
        { transform: 'translate3d(0, 0, 0) rotate(0deg)', offset: 1 },
      ], { duration: 1350, easing: 'ease-in-out' });
      flutter.onfinish = () => { delete butterfly.dataset.fluttering; };
      flutter.oncancel = () => { delete butterfly.dataset.fluttering; };
    };
    update();
    document.addEventListener('visibilitychange', update);
    media.addEventListener('change', update);
    window.addEventListener('pointerdown', respondToPointer);
    return () => {
      document.removeEventListener('visibilitychange', update);
      media.removeEventListener('change', update);
      window.removeEventListener('pointerdown', respondToPointer);
    };
  }, [variant]);

  return <div ref={gardenRef} className={`app-butterfly-garden ${variant}`} aria-hidden="true" data-playing={!reduced && visible}>
    {wingSource && flights.map(butterfly => <Butterfly butterfly={butterfly} wingSource={wingSource} variant={variant} key={butterfly.id} />)}
  </div>;
}
