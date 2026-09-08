"use client";

import { ChangeEvent, useState } from "react";
import { detectPlaylistLink, parsePlaylistText, providerLabel } from "./playlist";
import { useI18n } from "./i18n";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function PlaylistImport({ onImported }: { onImported?: () => void }) {
  const { t } = useI18n();
  const [url, setUrl] = useState("https://music.163.com/m/playlist?id=5036528042&creatorId=3346225720");
  const [message, setMessage] = useState(t("playlist.csvReady"));
  const [checking, setChecking] = useState(false);
  const [text, setText] = useState("");
  const [method, setMethod] = useState<"text" | "csv">("text");
  const parsed = parsePlaylistText(text);

  const inspect = async () => {
    const info = detectPlaylistLink(url);
    if (!info.valid || !info.playlistId) { setMessage(t("playlist.invalid")); return; }
    setChecking(true);
    setMessage(t("playlist.checking"));
    try {
      const response = await fetch(`${API_URL}/api/v1/imports/playlist-url`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url }) });
      const payload = await response.json();
      if (!response.ok) setMessage(payload.detail ?? t("playlist.unsupported"));
      else setMessage(t("playlist.detected", { provider: providerLabel(info.provider), id: info.playlistId }));
    } catch { setMessage(t("playlist.unsupported")); }
    finally { setChecking(false); }
  };

  const importCsv = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setChecking(true);
    const body = new FormData(); body.append("file", file);
    try {
      const response = await fetch(`${API_URL}/api/v1/imports/csv`, { method: "POST", body });
      const payload = await response.json();
      setMessage(response.ok ? t("status.imported", { count: payload.total_records }) : payload.detail ?? t("status.error"));
      if (response.ok) onImported?.();
    } catch { setMessage(t("status.error")); }
    finally { setChecking(false); }
  };

  const importText = async () => {
    if (!parsed.rows.length) { setMessage(t("playlist.invalid")); return; }
    setChecking(true); setMessage(t("playlist.stageParse"));
    try {
      setMessage(t("playlist.stageResolve"));
      const response = await fetch(`${API_URL}/api/v1/imports/playlist-text`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
      const payload = await response.json();
      if (!response.ok) { setMessage(payload.detail ?? t("status.error")); return; }
      setMessage(t("playlist.complete", { count: payload.total_records, resolved: payload.resolved_records, unresolved: payload.unresolved_records + payload.ambiguous_records, artists: payload.unique_artists }));
      onImported?.();
    } catch { setMessage(t("status.error")); }
    finally { setChecking(false); }
  };

  return <section className="panel playlist-import"><h2>{t("home.importTitle")}</h2><p className="muted">{t("home.importDescription")}</p><div className="import-methods"><button type="button" className={method === "text" ? "selected-role" : "secondary-button"} onClick={() => setMethod("text")}>{t("playlist.textTab")}</button><button type="button" className={method === "csv" ? "selected-role" : "secondary-button"} onClick={() => setMethod("csv")}>{t("playlist.csv")}</button></div>{method === "text" ? <><div className="playlist-input-row"><input aria-label={t("playlist.placeholder")} value={url} onChange={(event) => setUrl(event.target.value)} placeholder={t("playlist.placeholder")} /><button type="button" onClick={() => void inspect()} disabled={checking}>{t("playlist.detect")}</button></div><p className="muted playlist-help">{t("playlist.textHelp")}</p><a className="text-link" href="https://music.unmeta.cn/" target="_blank" rel="noreferrer">{t("playlist.openTool")}</a><textarea aria-label={t("playlist.textPlaceholder")} className="playlist-textarea" value={text} onChange={(event) => setText(event.target.value)} placeholder={t("playlist.textPlaceholder")} /><p className="muted">{t("playlist.summary", { total: parsed.summary.totalLines, valid: parsed.summary.validTracks, invalid: parsed.summary.invalidLines, artists: parsed.summary.uniqueArtists })}</p><button type="button" onClick={() => void importText()} disabled={checking || !parsed.rows.length}>{t("playlist.parse")}</button><p className="muted attribution">{t("playlist.attribution")}</p></> : <label className="secondary-upload">{t("playlist.csv")}<input type="file" accept=".csv,text/csv" onChange={importCsv} /></label>}<p className="import-status" role="status">{message}</p></section>;
}
