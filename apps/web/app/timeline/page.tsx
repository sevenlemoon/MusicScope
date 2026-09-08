"use client";

import { useEffect, useState } from "react";
import PageFrame from "../PageFrame";
import { useI18n } from "../i18n";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Evidence = { signal: string; text: string; name?: string; delta?: number; value?: number; current?: number; previous?: number };
type Period = { id: string; start_at: string; label: string; change_score: number; is_demo?: boolean; evidence: Evidence[] };

export default function TimelinePage() {
  const { t } = useI18n(); const [periods, setPeriods] = useState<Period[]>([]); const [message, setMessage] = useState(""); const [loading, setLoading] = useState(true); const [error, setError] = useState(false);
  const load = async () => { setLoading(true); const response = await fetch(`${API_URL}/api/v1/timeline`); if (response.ok) setPeriods(await response.json()); else setError(true); setLoading(false); };
  useEffect(() => { void load(); }, []);
  const recalculate = async () => { setMessage(t("timeline.recalculating")); const response = await fetch(`${API_URL}/api/v1/timeline/recalculate`, { method: "POST" }); if (response.ok) setPeriods(await response.json()); setMessage(t("timeline.updated")); };
  return <PageFrame title={t("nav.timeline")}><section className="panel timeline-panel"><div className="timeline-heading"><div><p className="muted">{t("timeline.description")}</p></div><button type="button" onClick={() => void recalculate}>{t("timeline.recalculate")}</button></div>{message && <p className="import-status">{message}</p>}{loading && <p className="empty-state">{t("status.loading")}</p>}{error && <p className="empty-state">{t("status.error")}</p>}{!loading && !error && periods.length === 0 ? <div className="empty-state timeline-empty"><h2>{t("timeline.emptyHistory")}</h2><p>{t("timeline.importHint")}</p></div> : periods.map((period) => <article className="timeline-period" key={period.id}><div><p className="role-badge">{new Date(period.start_at).getUTCFullYear()}</p>{period.is_demo && <small className="demo-note">{t("timeline.demo")}</small>}<h3>{period.label}</h3><p className="muted">{t("timeline.score", { score: period.change_score.toFixed(2) })}</p><ul>{period.evidence.map((evidence, index) => <li key={`${period.id}-${index}`}>{localizeEvidence(evidence, t)}</li>)}</ul></div></article>)}</section></PageFrame>;
}

function localizeEvidence(evidence: Evidence, t: (key: string, values?: Record<string, string | number>) => string): string {
  const percent = `${evidence.delta && evidence.delta >= 0 ? "+" : ""}${Math.round((evidence.delta ?? 0) * 100)}`;
  if (evidence.signal === "genre_share") return `${evidence.name ?? "Genre"} ${percent}%`;
  if (evidence.signal === "new_artists") return t("timeline.evidenceNewArtists", { count: evidence.value ?? 0 });
  if (evidence.signal === "completion") return t("timeline.evidenceCompletion", { delta: percent });
  if (evidence.signal === "skip_rate") return t("timeline.evidenceSkip", { delta: percent });
  if (evidence.signal === "listening_frequency") return t("timeline.evidenceFrequency", { previous: evidence.previous ?? "", current: evidence.current ?? "" });
  return evidence.text;
}
