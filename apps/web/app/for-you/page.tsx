"use client";

import { useEffect, useState } from "react";
import PageFrame from "../PageFrame";
import { useI18n } from "../i18n";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Recommendation = { id: string; title: string; artist: string; role: string; explanation_evidence: { text: string }[] };
const roles = ["ALL", "PRECISE_MATCH", "ADJACENT_EXPLORATION", "CROSS_BOUNDARY_DISCOVERY", "BOLD_TRY"];

export default function ForYouPage() {
  const { t } = useI18n();
  const [items, setItems] = useState<Recommendation[]>([]); const [role, setRole] = useState("ALL"); const [exploration, setExploration] = useState(50);
  useEffect(() => { void fetch(`${API_URL}/api/v1/recommendations?exploration_level=${exploration}&limit=12`).then((response) => response.json()).then((data) => setItems(data.recommendations ?? [])); }, [exploration]);
  const filtered = role === "ALL" ? items : items.filter((item) => item.role === role);
  const giveFeedback = async (id: string, eventType: "like" | "skip" | "dislike") => { await fetch(`${API_URL}/api/v1/recommendations/${id}/feedback`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ event_type: eventType, reason: eventType === "skip" ? "NOT_FOR_TODAY" : null }) }); };
  return <PageFrame title={t("nav.forYou")}><section className="panel recommendation-page-heading"><p className="muted">{t("recommendation.description")}</p><label className="slider-label">{t("recommendation.exploration")} <strong>{exploration}</strong><input aria-label={t("recommendation.exploration")} type="range" min="0" max="100" value={exploration} onChange={(event) => setExploration(Number(event.target.value))} /></label></section><div className="discover-layout"><aside className="role-nav" aria-label="Recommendation roles">{roles.map((item) => <button type="button" className={role === item ? "selected-role" : ""} key={item} onClick={() => setRole(item)}>{item === "ALL" ? t("recommendation.title") : t(`role.${item}`)}</button>)}</aside><section className="recommendation-grid focused-recommendations">{filtered.map((item) => <article className="recommendation-card" key={item.id}><p className="role">{t(`role.${item.role}`)}</p><h3>{item.title}</h3><p className="muted">{item.artist}</p><p className="why"><strong>{t("recommendation.why")}</strong> {item.explanation_evidence[0]?.text}</p><div className="feedback"><button type="button" onClick={() => void giveFeedback(item.id, "like")}>{t("feedback.like")}</button><button type="button" onClick={() => void giveFeedback(item.id, "skip")}>{t("feedback.skip")}</button><button type="button" onClick={() => void giveFeedback(item.id, "dislike")}>{t("feedback.dislike")}</button></div></article>)}</section></div></PageFrame>;
}
