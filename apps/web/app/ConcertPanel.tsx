/* eslint-disable @next/next/no-img-element */
"use client";

import { useEffect, useMemo, useState } from "react";
import { concertProviderLabel, formatConcertDate, formatConcertTime, shouldShowConcertLink } from "./concerts";
import { SpotlightCard } from "./Kinetic";
import { useI18n } from "./i18n";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Concert = { id: string; artist: string; provider?: string; event_name?: string | null; date: string; time?: string | null; timezone?: string | null; venue?: string | null; city?: string | null; region?: string | null; country?: string | null; external_url?: string | null; image_url?: string | null; is_demo: boolean };
type ArtistOption = { id: string; name: string; track_count: number };
type SearchResult = { events: Concert[]; provider_status: string; stale: boolean };

export default function ConcertPanel() {
  const { language, t } = useI18n();
  const [artists, setArtists] = useState<ArtistOption[]>([]);
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const searchArtist = async (name: string) => {
    if (!name.trim()) return;
    setQuery(name); setLoading(true); setError(false); setResult(null);
    try {
      const response = await fetch(API_URL + "/api/v1/concerts/search?artist=" + encodeURIComponent(name.trim()));
      if (!response.ok) throw new Error("concert search failed");
      setResult(await response.json());
    } catch { setError(true); } finally { setLoading(false); }
  };

  useEffect(() => {
    void fetch(API_URL + "/api/v1/library/artists").then((response) => response.ok ? response.json() : []).then(setArtists).catch(() => setArtists([]));
    const initial = new URLSearchParams(window.location.search).get("artist");
    if (initial) void searchArtist(initial);
  }, []);
  const suggestions = useMemo(() => query.trim() ? artists.filter((artist) => artist.name.normalize("NFKC").toLocaleLowerCase().includes(query.normalize("NFKC").trim().toLocaleLowerCase())).slice(0, 6) : [], [artists, query]);

  return <section className="concert-experience"><div className="concert-search-shell"><label htmlFor="artist-search">{t("concert.search")}</label><div className="concert-search"><input id="artist-search" autoComplete="off" placeholder={t("v3.concertPlaceholder")} value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void searchArtist(query); }} /><button type="button" onClick={() => void searchArtist(query)} disabled={loading || !query.trim()}>{loading ? t("concert.searching") : t("concert.searchButton")} <span>↗</span></button></div><div className="artist-suggestions">{suggestions.map((artist) => <button type="button" key={artist.id} onClick={() => void searchArtist(artist.name)}><strong>{artist.name}</strong><span>{t("v3.trackCount", { count: artist.track_count })}</span></button>)}</div></div>
    {loading && <div className="loading-stage"><span>SEARCHING LIVE SOURCES</span><i /></div>}
    {error && <p className="empty-state">{t("concert.error")}</p>}
    {!loading && result?.provider_status === "provider_unavailable" && <p className="empty-state">{t("concert.providerUnavailable")}</p>}
    {!loading && result && result.provider_status !== "provider_unavailable" && result.events.length === 0 && <p className="empty-state">{t("v3.concertNone")}</p>}
    <div className="concert-grid">{result?.events.map((event) => <SpotlightCard className="concert-card" tilt key={event.id}>{event.image_url ? <img className="concert-image" src={event.image_url} alt="" /> : <div className="concert-image-placeholder" aria-hidden="true"><span>LIVE</span></div>}<div className="concert-date"><strong>{formatConcertDate(event.date)}</strong><span>{formatConcertTime(event.time ?? null, event.timezone ?? null)}</span></div><p className="recommendation-type">{event.artist}</p><h3>{event.event_name ?? t("concert.title")}</h3><p>{[event.venue, event.city, event.region, event.country].filter(Boolean).join(" · ") || t("concert.venueUnavailable")}</p><small>{concertProviderLabel(event.provider, language)}</small>{shouldShowConcertLink(event) && <a className="details-link" href={event.external_url!} target="_blank" rel="noreferrer">{t("concert.details")}</a>}</SpotlightCard>)}</div>
  </section>;
}
