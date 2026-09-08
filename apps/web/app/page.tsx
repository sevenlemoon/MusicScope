"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PageFrame from "./PageFrame";
import PlaylistImport from "./PlaylistImport";
import { MagneticLink, Reveal, SpotlightCard } from "./Kinetic";
import { useI18n } from "./i18n";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type LibraryTrack = { track_id: string; artist_id?: string | null; genres?: string[] };

export default function Home() {
  const { t } = useI18n();
  const [library, setLibrary] = useState<LibraryTrack[]>([]);
  const visualRef = useRef<HTMLDivElement>(null);
  const refreshLibrary = useCallback(async () => {
    const response = await fetch(`${API_URL}/api/v1/library`);
    if (!response.ok) throw new Error("library refresh failed");
    setLibrary(await response.json());
  }, []);
  useEffect(() => { void refreshLibrary().catch(() => setLibrary([])); }, [refreshLibrary]);
  const stats = useMemo(() => ({ tracks: new Set(library.map((item) => item.track_id)).size, artists: new Set(library.map((item) => item.artist_id).filter(Boolean)).size, genres: new Set(library.flatMap((item) => item.genres ?? [])).size }), [library]);
  const moveVisual = (event: React.PointerEvent<HTMLElement>) => {
    if (!visualRef.current || !window.matchMedia("(prefers-reduced-motion: no-preference)").matches) return;
    visualRef.current.style.setProperty("--parallax-x", `${(event.clientX / window.innerWidth - 0.5) * 14}px`);
    visualRef.current.style.setProperty("--parallax-y", `${(event.clientY / window.innerHeight - 0.5) * 10}px`);
  };
  const features = [
    { number: "01", label: "DISCOVER", title: t("nav.forYou"), body: t("v3.featureDiscover"), href: "/for-you", className: "feature-discover" },
    { number: "02", label: "LIVE", title: t("nav.concerts"), body: t("v3.featureLive"), href: "/concerts", className: "feature-live" },
    { number: "03", label: "LIBRARY", title: t("nav.myMusic"), body: t("v3.featureLibrary"), href: "/my-music", className: "feature-library" },
    { number: "04", label: "STEMS", title: t("nav.lab"), body: t("v3.featureStems"), href: "/lab", className: "feature-stems" },
  ];
  return <PageFrame title={t("home.title")}><section className="v3-hero" onPointerMove={moveVisual}>
    <div className="hero-copy"><p className="chapter-label">MUSICSCOPE / PERSONAL MUSIC INTELLIGENCE</p><p className="hero-english">YOUR MUSIC,<br /><em>A WIDER WORLD.</em></p><h1>{t("v3.heroTitle")}</h1><p className="hero-lede">{t("v3.heroBody")}</p><MagneticLink href={stats.tracks ? "/for-you" : "#import"}>{t("v3.start")}</MagneticLink></div>
    <div className="hero-visual" ref={visualRef}><div className="vinyl-ring"><span>MS</span></div><div className="waveform">{Array.from({ length: 28 }, (_, index) => <i key={index} style={{ height: `${22 + ((index * 37) % 70)}%` }} />)}</div><b>03</b><small>SCOPE / SOUND / SELF</small></div>
    <div className="hero-stats" aria-label={t("v3.libraryStats")}><Stat value={stats.tracks} label="TRACKS" /><Stat value={stats.artists} label="ARTISTS" /><Stat value={stats.genres || "—"} label="GENRES" /></div>
  </section>
  <Reveal className="feature-chapter"><div className="section-index"><span>CORE / 04</span><h2>{t("v3.coreTitle")}</h2></div><div className="feature-grid">{features.map((feature) => <SpotlightCard key={feature.number} tilt className={`feature-entry ${feature.className}`}><span className="feature-number">{feature.number}</span><p>{feature.label}</p><h3>{feature.title}</h3><p className="muted">{feature.body}</p><MagneticLink href={feature.href}>{t("home.open")}</MagneticLink></SpotlightCard>)}</div></Reveal>
  <Reveal className="import-chapter" ><div id="import" className="section-index"><span>IMPORT / LIBRARY</span><h2>{t("v3.importTitle")}</h2><p>{t("v3.importIntro")}</p></div><PlaylistImport onImported={refreshLibrary} /></Reveal></PageFrame>;
}

function Stat({ value, label }: { value: number | string; label: string }) {
  return <div><strong>{value}</strong><span>{label}</span></div>;
}
