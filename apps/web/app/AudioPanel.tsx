"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import { decodeStemBuffers, SynchronizedStemPlayer, StemName } from "./audio-player";
import { useI18n } from "./i18n";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Job = { id: string; asset_id: string; status: string; error_message?: string | null };
type Manifest = { duration_seconds: number; sample_rate: number; channels: number; stems: Record<StemName, { url: string }> };

export default function AudioPanel() {
  const { t } = useI18n();
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [message, setMessage] = useState(t("audio.chooseMessage"));
  const [vocalGain, setVocalGain] = useState(1);
  const [instrumentalGain, setInstrumentalGain] = useState(1);
  const [playing, setPlaying] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const playerRef = useRef<SynchronizedStemPlayer | null>(null);
  const contextRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    if (!job || job.status === "COMPLETED" || job.status === "FAILED") return;
    const timer = window.setInterval(async () => {
      const response = await fetch(`${API_URL}/api/v1/separation-jobs/${job.id}`);
      if (!response.ok) return;
      const nextJob: Job = await response.json();
      setJob(nextJob);
      if (nextJob.status === "COMPLETED") {
        const manifestResponse = await fetch(`${API_URL}/api/v1/separation-jobs/${nextJob.id}/manifest`);
        if (manifestResponse.ok) {
          setManifest(await manifestResponse.json());
          setMessage(t("audio.complete"));
        }
      }
      if (nextJob.status === "FAILED") setMessage(nextJob.error_message ?? t("audio.failed"));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [job, t]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (playerRef.current?.isPlaying) setCurrentTime(playerRef.current.currentTime);
    }, 200);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => () => {
    playerRef.current?.destroy();
    void contextRef.current?.close();
  }, []);

  const uploadAndSeparate = async () => {
    if (!file) return;
    try {
      setManifest(null);
      setLoaded(false);
      setPlaying(false);
      setMessage(t("audio.uploading"));
      const body = new FormData();
      body.append("file", file);
      const uploadResponse = await fetch(`${API_URL}/api/v1/audio-assets`, { method: "POST", body });
      if (!uploadResponse.ok) {
        setMessage((await uploadResponse.json()).detail ?? t("status.error"));
        return;
      }
      const asset = await uploadResponse.json();
      setMessage(t("audio.normalized"));
      const separationResponse = await fetch(`${API_URL}/api/v1/audio-assets/${asset.id}/separate`, { method: "POST" });
      if (!separationResponse.ok) {
        setMessage((await separationResponse.json()).detail ?? t("status.error"));
        return;
      }
      const nextJob: Job = await separationResponse.json();
      setJob(nextJob);
      if (nextJob.status === "COMPLETED") {
        const manifestResponse = await fetch(`${API_URL}/api/v1/separation-jobs/${nextJob.id}/manifest`);
        setManifest(await manifestResponse.json());
        setMessage(t("audio.cached"));
      } else {
        setMessage(nextJob.status === "PROCESSING" ? t("audio.processing") : t("audio.queued"));
      }
    } catch {
      setMessage(t("audio.unavailable"));
    }
  };

  const preparePlayer = async () => {
    if (!manifest) return;
    const context = contextRef.current ?? new AudioContext();
    contextRef.current = context;
    const player = playerRef.current ?? new SynchronizedStemPlayer(context);
    playerRef.current = player;
    try {
      if (!loaded) {
        setMessage(t("audio.loading"));
        const buffers = await decodeStemBuffers(context, { vocals: `${API_URL}${manifest.stems.vocals.url}`, instrumental: `${API_URL}${manifest.stems.instrumental.url}` });
        player.setBuffers(buffers);
        player.setGain("vocals", vocalGain);
        player.setGain("instrumental", instrumentalGain);
        setLoaded(true);
      }
      await player.play();
      setPlaying(true);
      setMessage(t("audio.playing"));
    } catch {
      setLoaded(false);
      setPlaying(false);
      setMessage(t("audio.loadError"));
    }
  };

  const pause = () => {
    playerRef.current?.pause();
    setCurrentTime(playerRef.current?.currentTime ?? 0);
    setPlaying(false);
  };

  const setGain = (stem: StemName, value: number) => {
    if (stem === "vocals") setVocalGain(value);
    else setInstrumentalGain(value);
    playerRef.current?.setGain(stem, value);
  };

  const seek = (event: ChangeEvent<HTMLInputElement>) => {
    const value = Number(event.target.value);
    playerRef.current?.seek(value);
    setCurrentTime(value);
  };

  return <section className="audio-panel spotlight-surface">
    <div className="audio-heading"><div><p className="eyebrow">{t("audio.eyebrow")}</p><h2>{t("audio.title")}</h2><p className="muted">{t("audio.description")}</p></div></div>
    <div className="audio-upload-row"><label className="upload-button">{t("audio.choose")}<input type="file" accept=".wav,.mp3,.m4a,.aac,.flac,audio/*" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label><span className="muted">{file?.name ?? t("audio.formats")}</span><button type="button" onClick={() => void uploadAndSeparate()} disabled={!file || (job?.status === "PENDING" || job?.status === "PROCESSING")}>{t("audio.separate")}</button></div>
    {job && <p className="audio-status"><strong>{t(`status.${job.status.toLowerCase()}`)}</strong> · {message}</p>}
    {!job && <p className="muted">{message}</p>}
    {job?.status === "FAILED" && <button type="button" onClick={() => void uploadAndSeparate()}>{t("audio.retry")}</button>}
    {manifest && <div className="stem-player">
      <div className="stem-meta"><span>{loaded ? t("audio.loaded") : t("audio.ready")}</span><span>{manifest.sample_rate} Hz · {manifest.channels} channels · {manifest.duration_seconds.toFixed(1)} s</span></div>
      <div className="transport"><button type="button" onClick={() => playing ? pause() : void preparePlayer()}>{playing ? t("audio.pause") : t("audio.play")}</button><input aria-label={t("audio.seek")} type="range" min="0" max={manifest.duration_seconds} step="0.01" value={Math.min(currentTime, manifest.duration_seconds)} onChange={seek} /><span>{formatTime(currentTime)} / {formatTime(manifest.duration_seconds)}</span></div>
      <StemControl label={t("audio.vocals")} value={vocalGain} onChange={(value) => setGain("vocals", value)} />
      <StemControl label={t("audio.instrumental")} value={instrumentalGain} onChange={(value) => setGain("instrumental", value)} />
    </div>}
  </section>;
}

function StemControl({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return <label className="stem-control"><span>{label}</span><input aria-label={`${label} volume`} type="range" min="0" max="1" step="0.01" value={value} onChange={(event) => onChange(Number(event.target.value))} /><span>{Math.round(value * 100)}%</span></label>;
}

function formatTime(value: number): string {
  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}
