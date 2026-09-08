/* eslint-disable @next/next/no-img-element */

function hash(value: string): number {
  return [...value].reduce((total, character) => ((total << 5) - total + character.charCodeAt(0)) | 0, 0);
}

export default function TrackArtwork({ title, artist, artworkUrl, large = false }: { title: string; artist?: string | null; artworkUrl?: string | null; large?: boolean }) {
  if (artworkUrl) return <img className={`track-artwork ${large ? "artwork-large" : ""}`} src={artworkUrl} alt="" />;
  const seed = Math.abs(hash(`${title}:${artist ?? ""}`));
  const hue = 185 + seed % 90;
  return <div className={`track-artwork generated-artwork ${large ? "artwork-large" : ""}`} style={{ "--art-hue": hue } as React.CSSProperties} aria-label="MusicScope artwork placeholder"><span>{title.slice(0, 1).toUpperCase()}</span><i aria-hidden="true" /><small>MS/{String(seed % 1000).padStart(3, "0")}</small></div>;
}
