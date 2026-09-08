"use client";

import { useEffect, useState } from "react";
import PageFrame from "../PageFrame";
import { useI18n } from "../i18n";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Evidence = { signal: string; value?: number; text?: string };
type Recommendation = { id: string; title: string; artist: string; role: string; explanation_evidence: Evidence[] };
const roles = ["ALL", "PRECISE_MATCH", "ADJACENT_EXPLORATION", "CROSS_BOUNDARY_DISCOVERY", "BOLD_TRY"];

export default function ForYouPage() {
  const { language, t } = useI18n();
  const [items, setItems] = useState<Recommendation[]>([]);
  const [role, setRole] = useState("ALL");
  const [exploration, setExploration] = useState(50);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  useEffect(() => { setLoading(true); setError(false); void fetch(`${API_URL}/api/v1/recommendations?exploration_level=${exploration}&limit=12`).then((response) => { if (!response.ok) throw new Error("recommendations unavailable"); return response.json(); }).then((data) => setItems(data.recommendations ?? [])).catch(() => setError(true)).finally(() => setLoading(false)); }, [exploration]);
  const filtered = role === "ALL" ? items : items.filter((item) => item.role === role);
  const giveFeedback = async (id: string, eventType: "like" | "skip" | "dislike") => { await fetch(`${API_URL}/api/v1/recommendations/${id}/feedback`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ event_type: eventType, reason: eventType === "skip" ? "NOT_FOR_TODAY" : null }) }); };
  return <PageFrame title={t("nav.forYou")}><section className="recommendation-intro"><div><p className="page-lede">{t("recommendation.libraryBasis")}</p><p className="muted">{t("recommendation.description")}</p></div><div className="exploration-control"><div className="exploration-labels"><span>{t("recommendation.familiar")}</span><strong>{exploration}%</strong><span>{t("recommendation.adventurous")}</span></div><input aria-label={t("recommendation.exploration")} type="range" min="0" max="100" value={exploration} onChange={(event) => setExploration(Number(event.target.value))} /></div></section><div className="role-filter" aria-label={t("recommendation.title")}>{roles.map((item) => <button type="button" className={role === item ? "selected-role" : "secondary-button"} key={item} onClick={() => setRole(item)}>{item === "ALL" ? t("recommendation.title") : t(`role.${item}`)}</button>)}</div>{loading && <p className="empty-state">{t("status.loading")}</p>}{error && <p className="empty-state">{t("recommendation.unavailable")}</p>}{!loading && !error && filtered.length === 0 && <section className="empty-state panel"><h2>{t("recommendation.noCandidates")}</h2></section>}<section className="recommendation-grid focused-recommendations">{filtered.map((item) => <article className="recommendation-card" key={item.id}><p className="role-badge">{t(`role.${item.role}`)}</p><h3>{item.title}</h3><p className="muted">{item.artist}</p><p className="why"><strong>{t("recommendation.why")}</strong> {localizeEvidence(item.explanation_evidence[0], language, t)}</p><div className="feedback"><button type="button" onClick={() => void giveFeedback(item.id, "like")}>{t("feedback.like")}</button><button type="button" onClick={() => void giveFeedback(item.id, "skip")}>{t("feedback.skip")}</button><button type="button" onClick={() => void giveFeedback(item.id, "dislike")}>{t("feedback.dislike")}</button></div></article>)}</section></PageFrame>;
}

function localizeEvidence(evidence: Evidence | undefined, language: "zh" | "en", t: (key: string, values?: Record<string, string | number>) => string): string {
  if (!evidence) return t("evidence.balanced_match");
  if (evidence.signal === "long_term_genre") return t("evidence.long_term_genre", { value: language === "zh" ? "长期流派" : "a long-term genre" });
  const key = `evidence.${evidence.signal}`;
  const translated = t(key, { value: evidence.value ?? "" });
  return translated === key ? evidence.text ?? t("evidence.balanced_match") : translated;
}
