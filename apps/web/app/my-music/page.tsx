"use client";

import { useEffect, useMemo, useState } from "react";
import PageFrame from "../PageFrame";
import { useI18n } from "../i18n";
import { visibleImportBatches } from "../import-batches";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Batch = { id: string; status: string; total_records: number; resolved_records: number; ambiguous_records: number; unresolved_records: number };
type Track = { id: string; title: string; artist?: string | null; track_id?: string };
type RecordItem = { id: string; artist: string; title: string; resolution_status: string };
type Profile = { summary: { unique_artists?: number; unique_tracks?: number; completion_rate?: number; replays?: number; library_tracks?: number }; artists: { name: string }[]; genres: { name: string }[] };

export default function MyMusicPage() {
  const { t } = useI18n();
  const [profile, setProfile] = useState<{ long_term: Profile | null; short_term: Profile | null }>({ long_term: null, short_term: null });
  const [library, setLibrary] = useState<Track[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [review, setReview] = useState<RecordItem[]>([]);
  const [allTracks, setAllTracks] = useState<Track[]>([]);
  const [search, setSearch] = useState("");
  const [showAll, setShowAll] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const refresh = async () => {
    setLoading(true); setError(false);
    try {
      const [profileResponse, libraryResponse, batchesResponse, reviewResponse, tracksResponse] = await Promise.all([fetch(`${API_URL}/api/v1/profile`), fetch(`${API_URL}/api/v1/library`), fetch(`${API_URL}/api/v1/imports`), fetch(`${API_URL}/api/v1/records/review`), fetch(`${API_URL}/api/v1/tracks`)]);
      if (![profileResponse, libraryResponse, batchesResponse, reviewResponse, tracksResponse].every((response) => response.ok)) throw new Error("load failed");
      const profileData = await profileResponse.json();
      setProfile({ long_term: profileData.long_term, short_term: profileData.short_term });
      setLibrary(await libraryResponse.json()); setBatches(await batchesResponse.json()); setReview(await reviewResponse.json()); setAllTracks(await tracksResponse.json());
    } catch { setError(true); } finally { setLoading(false); }
  };
  useEffect(() => { void refresh(); }, []);
  const visible = useMemo(() => visibleImportBatches(batches, showAll), [batches, showAll]);
  const filteredLibrary = useMemo(() => library.filter((track) => `${track.title} ${track.artist ?? ""}`.toLowerCase().includes(search.toLowerCase())).slice(0, 60), [library, search]);
  const correct = async (id: string, action: "assign" | "exclude", trackId?: string) => { await fetch(`${API_URL}/api/v1/records/${id}/correction`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, track_id: trackId }) }); await refresh(); };
  return <PageFrame title={t("nav.myMusic")}><p className="page-lede">{t("profile.description", { days: 30 })}</p>{loading && <p className="empty-state">{t("status.loading")}</p>}{error && <p className="empty-state">{t("status.error")}</p>}{!loading && !error && <><section className="library-stats"><div><strong>{library.length}</strong><span>{t("profile.libraryTracks")}</span></div><div><strong>{profile.long_term?.summary.unique_artists ?? 0}</strong><span>{t("profile.artists")}</span></div><div><strong>{profile.long_term?.genres.slice(0, 3).map((genre) => genre.name).join(" · ") || t("profile.none")}</strong><span>{t("profile.genres")}</span></div></section>{library.length === 0 ? <section className="empty-state panel"><h2>{t("profile.libraryEmpty")}</h2><p>{t("home.libraryEmpty")}</p></section> : <section className="library-layout"><section className="library-main"><div className="section-heading"><div><p className="eyebrow">{t("home.libraryOverview")}</p><h2>{t("profile.tracks", { count: library.length })}</h2></div><input className="library-search" aria-label={t("profile.searchLibrary")} placeholder={t("profile.searchLibrary")} value={search} onChange={(event) => setSearch(event.target.value)} /></div><div className="track-library">{filteredLibrary.map((track) => <div className="library-track" key={track.track_id ?? track.id}><strong>{track.title}</strong><span>{track.artist ?? t("profile.none")}</span></div>)}</div>{library.length > 60 && <p className="muted">{t("profile.showingFirst", { count: 60 })}</p>}</section><aside className="library-side"><ProfileColumn title={t("profile.longTerm")} profile={profile.long_term} t={t} /><ProfileColumn title={t("profile.recent")} profile={profile.short_term} t={t} emptyText={t("profile.recentEmpty")} /></aside></section>}<details className="data-management"><summary><strong>{t("profile.dataManagement")}</strong><span>{t("profile.dataManagementHint")}</span></summary><section className="management-grid"><div><h3>{t("import.batches")}</h3>{visible.map((batch) => <div className="batch" key={batch.id}><strong>{t(`status.${batch.status}`)}</strong><span>{batch.total_records ? t("import.records", { count: batch.total_records }) : t("import.empty")}</span><small>{batch.resolved_records} {t("import.resolved")} · {batch.ambiguous_records} {t("import.ambiguous")} · {batch.unresolved_records} {t("import.unresolved")}</small></div>)}{batches.length > 5 && <button type="button" className="secondary-button" onClick={() => setShowAll((value) => !value)}>{showAll ? t("import.showLess") : t("import.showAll")}</button>}</div><div><h3>{t("review.title")}</h3>{review.length === 0 ? <p className="muted">{t("review.none")}</p> : review.map((record) => <div className="review-row" key={record.id}><div><strong>{record.title}</strong><span>{record.artist}</span></div><select defaultValue="" onChange={(event) => event.target.value && void correct(record.id, "assign", event.target.value)}><option value="">{t("review.assign")}</option>{allTracks.map((track) => <option key={track.id} value={track.id}>{track.title}</option>)}</select><button type="button" onClick={() => void correct(record.id, "exclude")}>{t("review.exclude")}</button></div>)}</div></section></details></>}</PageFrame>;
}

function ProfileColumn({ title, profile, t, emptyText }: { title: string; profile: Profile | null; t: (key: string, values?: Record<string, string | number>) => string; emptyText?: string }) {
  if (!profile || !Object.keys(profile.summary).length) return <div><h3>{title}</h3><p className="muted">{emptyText ?? t("profile.noData")}</p></div>;
  return <div><h3>{title}</h3><p className="muted">{t("profile.tracks", { count: profile.summary.unique_tracks ?? 0 })} · {t("profile.completion", { percent: Math.round((profile.summary.completion_rate ?? 0) * 100) })}</p><strong>{t("profile.topArtists")}</strong><p>{profile.artists.slice(0, 5).map((artist) => artist.name).join(" · ") || t("profile.none")}</p><strong>{t("profile.genres")}</strong><p>{profile.genres.slice(0, 5).map((genre) => genre.name).join(" · ") || t("profile.none")}</p></div>;
}
