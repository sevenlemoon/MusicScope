"use client";

import { useEffect, useMemo, useState } from "react";
import PageFrame from "../PageFrame";
import { useI18n } from "../i18n";
import { visibleImportBatches } from "../import-batches";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Batch = { id: string; status: string; total_records: number; resolved_records: number; ambiguous_records: number; unresolved_records: number };
type Track = { id: string; title: string };
type RecordItem = { id: string; artist: string; title: string; resolution_status: string; canonical_title?: string };
type Profile = { summary: { unique_artists?: number; unique_tracks?: number; completion_rate?: number; replays?: number }; artists: { name: string }[]; genres: { name: string }[] };

export default function MyMusicPage() {
  const { t } = useI18n(); const [profile, setProfile] = useState<{ long_term: Profile | null; short_term: Profile | null }>({ long_term: null, short_term: null }); const [batches, setBatches] = useState<Batch[]>([]); const [review, setReview] = useState<RecordItem[]>([]); const [tracks, setTracks] = useState<Track[]>([]); const [showAll, setShowAll] = useState(false); const [showTracks, setShowTracks] = useState(false);
  const refresh = async () => { const [profileResponse, batchesResponse, reviewResponse, tracksResponse] = await Promise.all([fetch(`${API_URL}/api/v1/profile`), fetch(`${API_URL}/api/v1/imports`), fetch(`${API_URL}/api/v1/records/review`), fetch(`${API_URL}/api/v1/tracks`)]); const profileData = await profileResponse.json(); setProfile({ long_term: profileData.long_term, short_term: profileData.short_term }); setBatches(await batchesResponse.json()); setReview(await reviewResponse.json()); setTracks(await tracksResponse.json()); };
  useEffect(() => { void refresh(); }, []);
  const visible = useMemo(() => visibleImportBatches(batches, showAll), [batches, showAll]);
  const correct = async (id: string, action: "assign" | "exclude", trackId?: string) => { await fetch(`${API_URL}/api/v1/records/${id}/correction`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, track_id: trackId }) }); await refresh(); };
  return <PageFrame title={t("nav.myMusic")}><div className="panel-grid"><div className="panel profile-panel"><h2>{t("profile.title")}</h2><div className="profile-columns"><ProfileColumn title={t("profile.longTerm")} profile={profile.long_term} t={t} /><ProfileColumn title={t("profile.recent")} profile={profile.short_term} t={t} /></div></div><section className="panel"><h2>{t("review.resolved")}</h2><div className="track-list">{tracks.slice(0, showTracks ? tracks.length : 50).map((track) => <div className="batch" key={track.id}><strong>{track.title}</strong></div>)}</div>{tracks.length > 50 && <button type="button" className="secondary-button" onClick={() => setShowTracks((value) => !value)}>{showTracks ? t("import.showLess") : t("import.showAll")}</button>}</section><section className="panel"><h2>{t("import.batches")}</h2>{visible.map((batch) => <div className="batch" key={batch.id}><strong>{t(`status.${batch.status}`)}</strong><span>{batch.total_records ? t("import.records", { count: batch.total_records }) : t("import.empty")}</span><small>{batch.resolved_records} {t("import.resolved")} · {batch.ambiguous_records} {t("import.ambiguous")} · {batch.unresolved_records} {t("import.unresolved")}</small></div>)}{batches.length > 5 && <button type="button" className="secondary-button" onClick={() => setShowAll((value) => !value)}>{showAll ? t("import.showLess") : t("import.showAll")}</button>}</section><section className="panel"><h2>{t("review.title")}</h2>{review.length === 0 ? <p className="muted">{t("review.none")}</p> : review.map((record) => <div className="review-row" key={record.id}><div><strong>{record.title}</strong><span>{record.artist}</span></div><select defaultValue="" onChange={(event) => event.target.value && void correct(record.id, "assign", event.target.value)}><option value="">{t("review.assign")}</option>{tracks.map((track) => <option key={track.id} value={track.id}>{track.title}</option>)}</select><button type="button" onClick={() => void correct(record.id, "exclude")}>{t("review.exclude")}</button></div>)}</section></div></PageFrame>;
}

function ProfileColumn({ title, profile, t }: { title: string; profile: Profile | null; t: (key: string, values?: Record<string, string | number>) => string }) {
  if (!profile) return <div><h3>{title}</h3><p className="muted">{t("profile.noData")}</p></div>;
  return <div><h3>{title}</h3><p className="muted">{t("profile.tracks", { count: profile.summary.unique_tracks ?? 0 })} · {t("profile.completion", { percent: Math.round((profile.summary.completion_rate ?? 0) * 100) })}</p><strong>{t("profile.genres")}</strong><p>{profile.genres.slice(0, 5).map((genre) => genre.name).join(" · ") || t("profile.none")}</p><strong>{t("profile.artists")}</strong><p>{profile.artists.slice(0, 5).map((artist) => artist.name).join(" · ") || t("profile.none")}</p></div>;
}
