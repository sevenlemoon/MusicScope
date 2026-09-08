"use client";

import Link from "next/link";
import { ChangeEvent, useMemo, useState } from "react";
import { parsePlaylistText } from "./playlist";
import { useI18n } from "./i18n";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Stage = "ready" | "parse" | "resolve" | "refresh" | "done";

export default function PlaylistImport({ onImported }: { onImported?: () => Promise<void> | void }) {
  const { t } = useI18n();
  const [text, setText] = useState("");
  const [method, setMethod] = useState<"text" | "csv">("text");
  const [stage, setStage] = useState<Stage>("ready");
  const [message, setMessage] = useState(t("playlist.csvReady"));
  const checking = stage === "parse" || stage === "resolve" || stage === "refresh";
  const parsed = useMemo(() => parsePlaylistText(text), [text]);

  const importText = async () => {
    if (!parsed.rows.length) { setMessage(t("playlist.invalid")); return; }
    setStage("parse"); setMessage(t("playlist.stageParse"));
    await Promise.resolve();
    setStage("resolve"); setMessage(t("v3.importResolving", { count: parsed.rows.length }));
    try {
      const response = await fetch(API_URL + "/api/v1/imports/playlist-text", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
      const payload = await response.json();
      if (!response.ok) { setStage("ready"); setMessage(payload.detail ?? t("status.error")); return; }
      setStage("refresh"); setMessage(t("v3.importRefresh"));
      try { await onImported?.(); } catch {
        setStage("done");
        setMessage(t("v3.importCompleteRefreshFailed", { count: payload.total_records }));
        return;
      }
      setStage("done");
      setMessage(t("playlist.complete", { count: payload.total_records, unresolved: payload.unresolved_records + payload.ambiguous_records, artists: payload.unique_artists }));
    } catch { setStage("ready"); setMessage(t("status.error")); }
  };

  const importCsv = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setStage("resolve"); setMessage(t("v3.importResolving", { count: "CSV" }));
    const body = new FormData(); body.append("file", file);
    try {
      const response = await fetch(API_URL + "/api/v1/imports/csv", { method: "POST", body });
      const payload = await response.json();
      if (!response.ok) { setStage("ready"); setMessage(payload.detail ?? t("status.error")); return; }
      setStage("refresh"); setMessage(t("v3.importRefresh"));
      try { await onImported?.(); } catch {
        setStage("done");
        setMessage(t("v3.importCompleteRefreshFailed", { count: payload.total_records }));
        return;
      }
      setStage("done"); setMessage(t("status.imported", { count: payload.total_records }));
    } catch { setStage("ready"); setMessage(t("status.error")); }
  };

  return <section className="playlist-import"><div className="section-heading"><p className="eyebrow">IMPORT / LIBRARY</p><h2>{t("home.importTitle")}</h2><p className="muted">{t("home.importDescription")}</p></div>
    <ol className="import-steps"><li><strong>1</strong><span>{t("playlist.step1")}</span></li><li><strong>2</strong><span>{t("playlist.step2")}</span></li><li><strong>3</strong><span>{t("playlist.step3")}</span></li></ol>
    <div className="import-methods"><button type="button" className={method === "text" ? "selected-role" : "secondary-button"} onClick={() => setMethod("text")}>{t("playlist.textTab")}</button><button type="button" className={method === "csv" ? "selected-role" : "secondary-button"} onClick={() => setMethod("csv")}>{t("playlist.otherMethods")}</button></div>
    {method === "text" ? <><p className="muted playlist-help">{t("playlist.textHelp")}</p><a className="text-link" href="https://music.unmeta.cn/" target="_blank" rel="noreferrer">{t("playlist.openTool")}</a><textarea aria-label={t("playlist.textPlaceholder")} className="playlist-textarea" value={text} onChange={(event) => setText(event.target.value)} placeholder={t("playlist.textPlaceholder")} /><p className="muted">{t("playlist.summary", { total: parsed.summary.totalLines, valid: parsed.summary.validTracks, invalid: parsed.summary.invalidLines, artists: parsed.summary.uniqueArtists })}</p><button type="button" onClick={() => void importText()} disabled={checking || !parsed.rows.length}>{t("playlist.parse")}</button><p className="import-note">{t("playlist.membershipNote")}</p><p className="muted attribution">{t("playlist.attribution")}</p></> : <label className="secondary-upload">{t("playlist.csv")}<input type="file" accept=".csv,text/csv" onChange={importCsv} /></label>}
    {checking && <div className="loading-stage" aria-label={message}><span>{stage === "parse" ? "PARSING TEXT" : stage === "refresh" ? "REFRESHING LIBRARY" : "ANALYZING LIBRARY"}</span><i /></div>}<p className="import-status" role="status">{message}</p>{stage === "done" && <Link className="text-link" href="/my-music">{t("v3.importMusic")} ↗</Link>}
  </section>;
}
