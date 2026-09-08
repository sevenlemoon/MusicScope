"use client";

import Link from "next/link";
import { PointerEvent, ReactNode, useEffect, useRef } from "react";

function point(event: PointerEvent<HTMLElement>, tilt = false) {
  const node = event.currentTarget;
  const rect = node.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  node.style.setProperty("--mouse-x", `${x}px`);
  node.style.setProperty("--mouse-y", `${y}px`);
  if (tilt && window.matchMedia("(prefers-reduced-motion: no-preference)").matches) {
    const rx = ((y / rect.height) - 0.5) * -4;
    const ry = ((x / rect.width) - 0.5) * 4;
    node.style.setProperty("--tilt", `perspective(900px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-4px)`);
  }
}

export function SpotlightCard({ children, className = "", tilt = false }: { children: ReactNode; className?: string; tilt?: boolean }) {
  return <div className={`spotlight-surface ${className}`} onPointerMove={(event) => point(event, tilt)} onPointerLeave={(event) => event.currentTarget.style.removeProperty("--tilt")}>{children}</div>;
}

export function MagneticLink({ href, children, className = "" }: { href: string; children: ReactNode; className?: string }) {
  const ref = useRef<HTMLAnchorElement>(null);
  return <Link ref={ref} href={href} className={`magnetic-cta spotlight-surface ${className}`} onPointerMove={(event) => {
    point(event);
    const rect = event.currentTarget.getBoundingClientRect();
    event.currentTarget.style.setProperty("--magnet-x", `${((event.clientX - rect.left) / rect.width - 0.5) * 8}px`);
    event.currentTarget.style.setProperty("--magnet-y", `${((event.clientY - rect.top) / rect.height - 0.5) * 8}px`);
  }} onPointerLeave={(event) => { event.currentTarget.style.setProperty("--magnet-x", "0px"); event.currentTarget.style.setProperty("--magnet-y", "0px"); }}>{children}<span aria-hidden="true">↗</span></Link>;
}

export function Reveal({ children, className = "" }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(([entry]) => { if (entry.isIntersecting) { node.dataset.visible = "true"; observer.disconnect(); } }, { threshold: 0.12 });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return <div ref={ref} className={`reveal ${className}`}>{children}</div>;
}
