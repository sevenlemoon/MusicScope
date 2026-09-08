/* eslint-disable @next/next/no-img-element */
"use client";

import { useEffect, useState } from "react";
import { formatConcertDate, formatConcertTime, shouldShowConcertLink } from "./concerts";
import { useI18n } from "./i18n";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Concert = { id: string; artist: string; provider?: string; event_name?: string | null; date: string; time?: string | null; doors_time?: string | null; timezone?: string | null; venue?: string | null; city?: string | null; region?: string | null; country?: string | null; external_url?: string | null; image_url?: string | null; is_demo: boolean };
type ConcertResponse = { events: Concert[]; artists: { name: string; event_count: number; provider_status: string; source: string; stale: boolean }[] };

export default function ConcertPanel({ compact = false }: { compact?: boolean }) {
  const { language, t } = useI18n();
  const [data, setData] = useState<ConcertResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [artistQuery, setArtistQuery] = useState("");
  const [demoMode, setDemoMode] = useState(false);

  useEffect(() => {
    fetch(compact ? `${API_URL}/api/v1/concerts/search?artist=milet${demoMode ? "&demo=true" : ""}` : `${API_URL}/api/v1/concerts${demoMode ? "?demo=true" : ""}`)
      .then((response) => { if (!response.ok) throw new Error("concert lookup failed"); return response.json(); })
      .then((value) => compact ? setData({ events: value.events, artists: [{ ...value.artist, event_count: value.events.length, provider_status: value.provider_status, source: value.source, stale: value.stale }] }) : setData(value as ConcertResponse))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [compact, demoMode]);

  const search = async () => {
    if (!artistQuery.trim()) return;
    setLoading(true); setError(false);
    try {
      const response = await fetch(`${API_URL}/api/v1/concerts/search?artist=${encodeURIComponent(artistQuery)}${demoMode ? "&demo=true" : ""}`);
      if (!response.ok) throw new Error("concert search failed");
      const result = await response.json();
      setData({ events: result.events, artists: [{ ...result.artist, event_count: result.events.length, provider_status: result.provider_status, source: result.source, stale: result.stale }] });
    } catch { setError(true); }
    finally { setLoading(false); }
  };

  return <section id="discover" className="panel concert-panel">
    <div className="concert-heading"><div><p className="eyebrow">{t("concert.eyebrow")}</p><h2>{t("concert.title")}</h2><p className="muted">{t("concert.description")}</p></div></div>
    {!compact && <div className="concert-search"><input aria-label={t("concert.searchPlaceholder")} placeholder={t("concert.searchPlaceholder")} value={artistQuery} onChange={(event) => setArtistQuery(event.target.value)} /><button type="button" onClick={() => void search()} disabled={loading}>{loading ? t("concert.searching") : t("concert.searchButton")}</button></div>}
    {loading && <p className="muted">{t("concert.loading")}</p>}
    {error && <p className="muted">{t("concert.error")}</p>}
    {!loading && !error && data?.artists.some((artist) => artist.provider_status === "provider_unavailable") && <p className="muted">{t("concert.providerUnavailable")}</p>}
    {!loading && !error && data?.artists.some((artist) => artist.provider_status === "provider_unavailable") && !demoMode && <button type="button" className="secondary-button" onClick={() => setDemoMode(true)}>{t("concert.demo")}</button>}
    {demoMode && <p className="demo-note">{t("concert.demo")}</p>}
    {!loading && !error && data?.artists.some((artist) => artist.stale) && <p className="muted">{t("concert.stale")}</p>}
    {!loading && !error && data && data.events.length === 0 && <p className="muted">{t("concert.none")}</p>}
    <div className="concert-grid">{data?.events.map((event) => <article className="concert-card" key={event.id}>{event.image_url ? <img className="concert-image" src={event.image_url} alt="" /> : <div className="concert-image-placeholder" aria-hidden="true" />}<p className="role">{event.artist}</p><h3>{event.event_name ?? t("concert.title")}</h3><strong>{formatConcertDate(event.date)}</strong><p className="muted">{event.doors_time ? `${language === "zh" ? "开场" : "Doors"} ${event.doors_time} · ` : ""}{formatConcertTime(event.time ?? null, event.timezone ?? null)}</p><p>{[event.venue, event.city, event.region, event.country].filter(Boolean).join(" · ") || t("concert.venueUnavailable")}</p><small className="demo-note">{event.is_demo ? t("concert.demo") : event.provider === "official_milet" ? (language === "zh" ? "官方网站" : "Official site") : "Ticketmaster"}</small>{shouldShowConcertLink(event) && <a className="details-link" href={event.external_url!} target="_blank" rel="noreferrer">{t("concert.details")}</a>}</article>)}</div>
  </section>;
}
