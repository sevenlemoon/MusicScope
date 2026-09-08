"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ConcertPanel from "./ConcertPanel";
import PageFrame from "./PageFrame";
import PlaylistImport from "./PlaylistImport";
import { useI18n } from "./i18n";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Profile = { summary: { unique_artists?: number; unique_tracks?: number; completion_rate?: number; replays?: number }; artists: { name: string }[]; genres: { name: string }[] };
type Recommendation = { title: string; artist: string; role: string; explanation_evidence: { text: string }[] };
type LibraryTrack = { track_id: string; title: string; artist?: string | null };

export default function Home() {
  const { t } = useI18n();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [library, setLibrary] = useState<LibraryTrack[]>([]);
  useEffect(() => {
    void Promise.all([fetch(`${API_URL}/api/v1/profile`).then((response) => response.ok ? response.json() : null), fetch(`${API_URL}/api/v1/library`).then((response) => response.ok ? response.json() : []), fetch(`${API_URL}/api/v1/recommendations?exploration_level=50&limit=4`).then((response) => response.ok ? response.json() : null)]).then(([profileData, libraryData, recommendationData]) => { setProfile(profileData?.long_term ?? null); setLibrary(libraryData ?? []); setRecommendations(recommendationData?.recommendations ?? []); });
  }, []);
  return <PageFrame title={t("home.title")}><section className="home-hero"><p className="eyebrow">{t("home.heroKicker")}</p><p className="intro home-subtitle">{t("home.subtitle")}</p><PlaylistImport onImported={() => window.location.reload()} /></section>{library.length > 0 && <section className="home-overview"><div><p className="eyebrow">{t("home.libraryOverview")}</p><h2>{library.length} {t("profile.libraryTracks")}</h2></div><div><strong>{profile?.summary.unique_artists ?? 0}</strong><span>{t("profile.artists")}</span></div><div><strong>{profile?.artists.slice(0, 3).map((artist) => artist.name).join(" · ") || t("profile.none")}</strong><span>{t("profile.topArtists")}</span></div><Link className="text-link" href="/my-music">{t("home.open")}</Link></section>}<section className="home-grid"><section className="home-feature panel"><h2>{t("home.forYou")}</h2>{recommendations.length ? recommendations.map((item) => <div className="preview-row" key={`${item.artist}-${item.title}`}><strong>{item.title}</strong><span>{item.artist}</span></div>) : <p className="muted">{t("recommendation.noCandidates")}</p>}<Link className="text-link" href="/for-you">{t("home.open")}</Link></section><section className="panel"><h2>{t("home.concerts")}</h2><ConcertPanel compact /></section><section className="panel lab-card"><h2>{t("home.audio")}</h2><p className="muted">{t("home.audioDescription")}</p><Link className="text-link" href="/lab">{t("home.labCta")}</Link></section></section></PageFrame>;
}
