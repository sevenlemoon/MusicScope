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

export default function Home() {
  const { t } = useI18n();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  useEffect(() => {
    void Promise.all([fetch(`${API_URL}/api/v1/profile`).then((response) => response.ok ? response.json() : null), fetch(`${API_URL}/api/v1/recommendations?exploration_level=50&limit=3`).then((response) => response.ok ? response.json() : null)]).then(([profileData, recommendationData]) => { setProfile(profileData?.long_term ?? null); setRecommendations(recommendationData?.recommendations ?? []); });
  }, []);
  return <PageFrame title={t("home.title")}><p className="intro home-subtitle">{t("home.subtitle")}</p><PlaylistImport /><section className="home-grid"><section className="panel"><h2>{t("home.profile")}</h2>{profile ? <><p className="profile-stat">{profile.summary.unique_tracks ?? 0} · {profile.summary.unique_artists ?? 0} {t("profile.artists")}</p><p className="muted">{t("profile.genres")}: {profile.genres.slice(0, 3).map((genre) => genre.name).join(" · ") || t("profile.none")}</p><Link className="text-link" href="/my-music">{t("home.open")}</Link></> : <p className="muted">{t("profile.noData")}</p>}</section><section className="panel"><h2>{t("home.forYou")}</h2>{recommendations.map((item) => <div className="preview-row" key={`${item.artist}-${item.title}`}><strong>{item.title}</strong><span>{item.artist}</span></div>)}<Link className="text-link" href="/for-you">{t("home.open")}</Link></section><section className="panel"><h2>{t("home.audio")}</h2><p className="muted">{t("home.audioDescription")}</p><Link className="text-link" href="/discover#audio">{t("home.open")}</Link></section></section><ConcertPanel compact /></PageFrame>;
}
