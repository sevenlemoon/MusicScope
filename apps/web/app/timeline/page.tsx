"use client";

import { useEffect, useState } from "react";
import PageFrame from "../PageFrame";
import { useI18n } from "../i18n";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Period = { id: string; start_at: string; label: string; change_score: number; is_demo?: boolean; evidence: { text: string }[] };

export default function TimelinePage() {
  const { t } = useI18n(); const [periods, setPeriods] = useState<Period[]>([]); const [message, setMessage] = useState("");
  const load = async () => { const response = await fetch(`${API_URL}/api/v1/timeline`); if (response.ok) setPeriods(await response.json()); };
  useEffect(() => { void load(); }, []);
  const recalculate = async () => { setMessage(t("timeline.recalculating")); const response = await fetch(`${API_URL}/api/v1/timeline/recalculate`, { method: "POST" }); if (response.ok) setPeriods(await response.json()); setMessage(t("timeline.updated")); };
  return <PageFrame title={t("nav.timeline")}><section className="panel timeline-panel"><div className="timeline-heading"><div><p className="muted">{t("timeline.description")}</p></div><button type="button" onClick={() => void recalculate}>{t("timeline.recalculate")}</button></div>{message && <p className="import-status">{message}</p>}{periods.length === 0 ? <p className="muted">{t("timeline.empty")}</p> : periods.map((period) => <article className="timeline-period" key={period.id}><div><p className="role">{new Date(period.start_at).getUTCFullYear()}</p>{period.is_demo && <small className="demo-note">{t("timeline.demo")}</small>}<h3>{period.label}</h3><p className="muted">{t("timeline.score", { score: period.change_score.toFixed(2) })}</p><ul>{period.evidence.map((evidence, index) => <li key={`${period.id}-${index}`}>{evidence.text}</li>)}</ul></div></article>)}</section></PageFrame>;
}
