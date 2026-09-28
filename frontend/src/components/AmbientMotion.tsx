'use client';

import { useEffect } from 'react';

export function AmbientMotion() {
  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const nodes = document.querySelectorAll<HTMLElement>('[data-reveal]');
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    }, { threshold: 0.12 });
    nodes.forEach(node => observer.observe(node));

    let frame = 0;
    const update = () => {
      frame = 0;
      if (media.matches || document.documentElement.classList.contains('reduce-motion')) return;
      document.documentElement.style.setProperty('--parallax-shift', `${Math.min(window.scrollY * .14, 120)}px`);
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(update); };
    const pointer = (event: PointerEvent) => {
      if (media.matches || document.documentElement.classList.contains('reduce-motion')) return;
      document.documentElement.style.setProperty('--pointer-x', `${((event.clientX / window.innerWidth) - .5) * 16}px`);
      document.documentElement.style.setProperty('--pointer-y', `${((event.clientY / window.innerHeight) - .5) * 12}px`);
    };
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('pointermove', pointer, { passive: true });
    update();
    return () => { observer.disconnect(); window.removeEventListener('scroll', schedule); window.removeEventListener('pointermove', pointer); if (frame) cancelAnimationFrame(frame); };
  }, []);
  return null;
}
