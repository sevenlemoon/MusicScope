"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import PageFrame from "../PageFrame";
import TrackArtwork from "../TrackArtwork";
import { useI18n } from "../i18n";
import { visibleImportBatches } from "../import-batches";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Batch = { id: string; status: string; total_records: number; resolved_records: number; ambiguous_records: number; unresolved_records: number };
type Track = { id: string; track_id?: string; title: string; artist_id?: string | null; artist?: string | null; album?: string | null; genres?: string[]; artwork_url?: string | null };
type RecordItem = { id: string; artist: string; title: string };
type Tab = "tracks" | "artists" | "genres";
const RESULT_LIMIT = 80;

function normalizeSearch(value: string): string {
  return value.normalize("NFKC").trim().toLocaleLowerCase();
}

export default function MyMusicPage() {
  const { t } = useI18n();
  const [library, setLibrary] = useState<Track[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [review, setReview] = useState<RecordItem[]>([]);
  const [allTracks, setAllTracks] = useState<Track[]>([]);
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState<Tab>("tracks");
  const [showAll, setShowAll] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const refresh = async () => {
    setLoading(true); setError(false);
    try {
      const responses = await Promise.all([fetch(`${API_URL}/api/v1/library`), fetch(`${API_URL}/api/v1/imports`), fetch(`${API_URL}/api/v1/records/review`), fetch(`${API_URL}/api/v1/tracks`)]);
      if (!responses.every((response) => response.ok)) throw new Error("load failed");
      const [libraryData, batchData, reviewData, trackData] = await Promise.all(responses.map((response) => response.json()));
      setLibrary(libraryData); setBatches(batchData); setReview(reviewData); setAllTracks(trackData);
    } catch { setError(true); } finally { setLoading(false); }
  };
  useEffect(() => { void refresh(); }, []);

  const normalizedSearch = normalizeSearch(search);
  const matchingTracks = useMemo(() => library.filter((item) => normalizeSearch(`${item.title} ${item.artist ?? ""} ${(item.genres ?? []).join(" ")}`).includes(normalizedSearch)), [library, normalizedSearch]);
  const visibleTracks = matchingTracks.slice(0, RESULT_LIMIT);
  const allArtists = useMemo(() => Object.values(library.reduce<Record<string, { id?: string | null; name: string; count: number }>>((result, item) => {
    const name = item.artist ?? t("profile.none");
    result[name] ??= { id: item.artist_id, name, count: 0 };
    result[name].count += 1;
    return result;
  }, {})).sort((a, b) => b.count - a.count), [library, t]);
  const filteredArtists = useMemo(() => allArtists.filter((item) => normalizeSearch(item.name).includes(normalizedSearch)), [allArtists, normalizedSearch]);
  const visibleArtists = filteredArtists.slice(0, RESULT_LIMIT);
  const allGenres = useMemo(() => Object.entries(library.flatMap((item) => item.genres ?? []).reduce<Record<string, number>>((result, genre) => {
    result[genre] = (result[genre] ?? 0) + 1;
    return result;
  }, {})).sort((a, b) => b[1] - a[1]), [library]);
  const filteredGenres = useMemo(() => allGenres.filter(([genre]) => normalizeSearch(genre).includes(normalizedSearch)), [allGenres, normalizedSearch]);
  const visible = useMemo(() => visibleImportBatches(batches, showAll), [batches, showAll]);
  const correct = async (id: string, action: "assign" | "exclude", trackId?: string) => {
    await fetch(`${API_URL}/api/v1/records/${id}/correction`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, track_id: trackId }) });
    await refresh();
  };

  return <PageFrame title={t("nav.myMusic")} eyebrow="LIBRARY / 03">
    <section className="library-hero"><div><p className="chapter-label">LIBRARY / 03</p><h1>{t("nav.myMusic")}</h1><p>{t("v3.libraryIntro")}</p></div><div className="library-stats"><Stat value={library.length} label="TRACKS" /><Stat value={allArtists.length} label="ARTISTS" /><Stat value={allGenres.length || "—"} label="GENRES" /></div></section>
    {loading && <p className="empty-state">{t("status.loading")}</p>}
    {error && <p className="empty-state">{t("status.error")}</p>}
    {!loading && !error && <><section className="library-browser"><div className="library-toolbar"><input className="library-search" aria-label={t("profile.searchLibrary")} placeholder={t("v3.librarySearch")} value={search} onChange={(event) => setSearch(event.target.value)} /><div className="library-tabs" role="tablist">{(["tracks", "artists", "genres"] as Tab[]).map((value) => <button type="button" role="tab" aria-selected={tab === value} className={tab === value ? "active-tab" : ""} key={value} onClick={() => setTab(value)}>{t(`v3.tab.${value}`)}</button>)}</div></div>
      {library.length === 0 ? <div className="empty-state"><h2>{t("profile.libraryEmpty")}</h2><Link href="/#import">{t("v3.importMusic")} ↗</Link></div> : tab === "tracks" ? <div className="track-list">{visibleTracks.map((track, index) => <article className="music-row" key={track.track_id ?? track.id}><span className="row-index">{String(index + 1).padStart(2, "0")}</span><TrackArtwork title={track.title} artist={track.artist} artworkUrl={track.artwork_url} /><div className="track-copy"><h3>{track.title}</h3><p>{track.artist ?? t("profile.none")}</p><small>{track.album ?? (track.genres?.length ? track.genres.join(" / ") : t("v3.metadataPending"))}</small></div>{track.artist && <Link className="row-action" href={`/concerts?artist=${encodeURIComponent(track.artist)}`}>{t("v3.findConcert")} ↗</Link>}</article>)}</div> : tab === "artists" ? <div className="artist-grid">{visibleArtists.map((artist) => <article key={artist.name}><span>{String(artist.count).padStart(2, "0")}</span><h3>{artist.name}</h3><p>{t("v3.trackCount", { count: artist.count })}</p><Link href={`/concerts?artist=${encodeURIComponent(artist.name)}`}>{t("v3.findConcert")} ↗</Link></article>)}</div> : allGenres.length === 0 ? <div className="empty-state"><h2>{t("v3.noGenres")}</h2><p>{t("v3.noGenresBody")}</p></div> : filteredGenres.length ? <div className="genre-grid">{filteredGenres.map(([genre, count]) => <article key={genre}><h3>{genre}</h3><strong>{count}</strong><span>TRACKS</span></article>)}</div> : <div className="empty-state"><h2>{t("v3.noGenreMatches")}</h2></div>}
      {tab === "tracks" && matchingTracks.length > RESULT_LIMIT && <p className="list-limit">{t("profile.showingFirstOf", { count: RESULT_LIMIT, total: matchingTracks.length })}</p>}
      {tab === "artists" && filteredArtists.length > RESULT_LIMIT && <p className="list-limit">{t("profile.showingFirstArtists", { count: RESULT_LIMIT, total: filteredArtists.length })}</p>}</section>
      <details className="data-management"><summary><strong>{t("profile.dataManagement")}</strong><span>{t("profile.dataManagementHint")}</span></summary><div className="management-grid"><section><h3>{t("import.batches")}</h3>{visible.map((batch) => <div className="batch" key={batch.id}><strong>{t(`status.${batch.status}`)}</strong><span>{batch.total_records ? t("import.records", { count: batch.total_records }) : t("import.empty")}</span><small>{batch.resolved_records} {t("import.resolved")} · {batch.ambiguous_records} {t("import.ambiguous")} · {batch.unresolved_records} {t("import.unresolved")}</small></div>)}{batches.length > 5 && <button type="button" className="secondary-button" onClick={() => setShowAll((value) => !value)}>{showAll ? t("import.showLess") : t("import.showAll")}</button>}</section><section><h3>{t("review.title")}</h3>{review.length === 0 ? <p className="muted">{t("review.none")}</p> : review.map((record) => <div className="review-row" key={record.id}><div><strong>{record.title}</strong><span>{record.artist}</span></div><select defaultValue="" onChange={(event) => event.target.value && void correct(record.id, "assign", event.target.value)}><option value="">{t("review.assign")}</option>{allTracks.map((track) => <option key={track.id} value={track.id}>{track.title}</option>)}</select><button type="button" onClick={() => void correct(record.id, "exclude")}>{t("review.exclude")}</button></div>)}</section></div></details></>}
  </PageFrame>;
}

function Stat({ value, label }: { value: number | string; label: string }) {
  return <div><strong>{value}</strong><span>{label}</span></div>;
}
