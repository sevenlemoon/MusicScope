"use client";

import { useEffect, useState } from "react";
import PageFrame from "../PageFrame";
import TrackArtwork from "../TrackArtwork";
import { SpotlightCard } from "../Kinetic";
import { useI18n } from "../i18n";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Evidence = { signal: string; value?: number; text?: string };
type Recommendation = { id: string; title: string; artist: string; role: string; artwork_url?: string | null; explanation_evidence: Evidence[] };
type FeedbackType = "like" | "skip" | "dislike";
type FeedbackReason = "NOT_FOR_TODAY" | "DISLIKE_ARTIST" | "DISLIKE_STYLE" | "SIMPLY_DISLIKE" | null;

export default function ForYouPage() {
  const { language, t } = useI18n();
  const [items, setItems] = useState<Recommendation[]>([]);
  const [exploration, setExploration] = useState(50);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  useEffect(() => {
    setLoading(true);
    setError(false);
    void fetch(API_URL + "/api/v1/recommendations?exploration_level=" + exploration + "&limit=12")
      .then((response) => { if (!response.ok) throw new Error("unavailable"); return response.json(); })
      .then((data) => setItems(data.recommendations ?? []))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [exploration]);
  const giveFeedback = async (id: string, eventType: FeedbackType, reason: FeedbackReason) => {
    const response = await fetch(API_URL + "/api/v1/recommendations/" + id + "/feedback", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ event_type: eventType, reason }) });
    if (!response.ok) throw new Error("feedback failed");
  };
  const hero = items[0];
  return <PageFrame title={t("nav.forYou")} eyebrow="DISCOVER / 01">
    <section className="recommendation-header"><div><p className="chapter-label">DISCOVER / 01</p><h1>{t("v3.discoverTitle")}</h1><p>{t("v3.discoverIntro")}</p></div><div className="exploration-control"><div><span>{t("recommendation.familiar")}</span><strong>{exploration}</strong><span>{t("recommendation.adventurous")}</span></div><input aria-label={t("recommendation.exploration")} type="range" min="0" max="100" value={exploration} onChange={(event) => setExploration(Number(event.target.value))} /><small>{t("v3.explorationHonest")}</small></div></section>
    {loading && <div className="loading-stage"><span>ANALYZING LIBRARY</span><i /></div>}
    {error && <p className="empty-state">{t("recommendation.unavailable")}</p>}
    {!loading && !error && !hero && <section className="empty-state"><h2>{t("recommendation.noCandidates")}</h2></section>}
    {hero && <SpotlightCard className="hero-recommendation" tilt><span className="editorial-number">01</span><div className="hero-art"><TrackArtwork title={hero.title} artist={hero.artist} artworkUrl={hero.artwork_url} large /></div><div className="hero-recommendation-copy"><p className="recommendation-type">{visibleRole(hero.role, t)}</p><h2>{hero.title}</h2><p className="artist-name">{hero.artist}</p><Why evidence={hero.explanation_evidence[0]} language={language} t={t} /><Feedback id={hero.id} giveFeedback={giveFeedback} t={t} /></div></SpotlightCard>}
    <section className="recommendation-grid">{items.slice(1).map((item, index) => <SpotlightCard className="recommendation-card" tilt key={item.id}><span className="card-number">{String(index + 2).padStart(2, "0")}</span><TrackArtwork title={item.title} artist={item.artist} artworkUrl={item.artwork_url} /><p className="recommendation-type">{visibleRole(item.role, t)}</p><h3>{item.title}</h3><p className="artist-name">{item.artist}</p><Why evidence={item.explanation_evidence[0]} language={language} t={t} /><Feedback id={item.id} giveFeedback={giveFeedback} t={t} /></SpotlightCard>)}</section>
  </PageFrame>;
}

function visibleRole(role: string, t: (key: string) => string): string {
  if (role === "PRECISE_MATCH") return t("v3.role.precise");
  if (role === "ADJACENT_EXPLORATION") return t("v3.role.similar");
  return t("v3.role.explore");
}

function Why({ evidence, language, t }: { evidence?: Evidence; language: "zh" | "en"; t: (key: string, values?: Record<string, string | number>) => string }) {
  return <div className="why-block"><strong>{t("recommendation.why")}</strong><p>{localizeEvidence(evidence, language, t)}</p></div>;
}

function Feedback({ id, giveFeedback, t }: { id: string; giveFeedback: (id: string, type: FeedbackType, reason: FeedbackReason) => Promise<void>; t: (key: string) => string }) {
  const [showReasons, setShowReasons] = useState(false);
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [lastSubmission, setLastSubmission] = useState<{ type: FeedbackType; reason: FeedbackReason } | null>(null);
  const submit = async (type: FeedbackType, reason: FeedbackReason) => {
    if (status === "submitting") return;
    setLastSubmission({ type, reason });
    setStatus("submitting");
    try {
      await giveFeedback(id, type, reason);
      setStatus("success");
      setShowReasons(false);
    } catch { setStatus("error"); }
  };
  const disabled = status === "submitting";
  return <div className="feedback-shell"><div className="feedback"><button type="button" disabled={disabled} onClick={() => void submit("like", null)}>{t("feedback.like")}</button><button type="button" disabled={disabled} onClick={() => void submit("skip", "NOT_FOR_TODAY")}>{t("feedback.skip")}</button><button type="button" disabled={disabled} aria-expanded={showReasons} onClick={() => setShowReasons((value) => !value)}>{t("feedback.dislike")}</button></div>
    {showReasons && <div className="feedback-reasons"><button type="button" disabled={disabled} onClick={() => void submit("dislike", "DISLIKE_ARTIST")}>{t("feedback.dislikeArtist")}</button><button type="button" disabled={disabled} onClick={() => void submit("dislike", "DISLIKE_STYLE")}>{t("feedback.dislikeStyle")}</button><button type="button" disabled={disabled} onClick={() => void submit("dislike", "SIMPLY_DISLIKE")}>{t("feedback.simplyDislike")}</button></div>}
    <div className={`feedback-status ${status}`} aria-live="polite">{status === "submitting" ? t("feedback.submitting") : status === "success" ? t("feedback.recorded") : status === "error" ? <><span>{t("feedback.error")}</span>{lastSubmission && <button type="button" onClick={() => void submit(lastSubmission.type, lastSubmission.reason)}>{t("feedback.retry")}</button>}</> : null}</div>
  </div>;
}

function localizeEvidence(evidence: Evidence | undefined, language: "zh" | "en", t: (key: string, values?: Record<string, string | number>) => string): string {
  if (!evidence) return t("evidence.balanced_match");
  if (evidence.signal === "long_term_genre") return t("evidence.long_term_genre", { value: language === "zh" ? "收藏流派" : "library genre" });
  const key = "evidence." + evidence.signal;
  const translated = t(key, { value: evidence.value ?? "" });
  return translated === key ? evidence.text ?? t("evidence.balanced_match") : translated;
}
