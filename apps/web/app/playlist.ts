export type PlaylistProvider = "netease" | "unknown";
export type PlaylistTextSummary = { totalLines: number; validTracks: number; invalidLines: number; uniqueArtists: number };

export type PlaylistLinkInfo = {
  provider: PlaylistProvider;
  playlistId: string | null;
  valid: boolean;
};

export function detectPlaylistLink(value: string): PlaylistLinkInfo {
  try {
    const url = new URL(value.trim());
    const host = url.hostname.toLowerCase();
    const playlistId = url.searchParams.get("id");
    if ((host === "music.163.com" || host.endsWith(".music.163.com")) && playlistId) return { provider: "netease", playlistId, valid: true };
  } catch {
    // The UI reports invalid links without throwing.
  }
  return { provider: "unknown", playlistId: null, valid: false };
}

export function providerLabel(provider: PlaylistProvider): string {
  return provider === "netease" ? "NetEase Cloud Music" : "Unknown provider";
}

export function parsePlaylistText(value: string): { rows: { title: string; artist: string; artists: string[] }[]; invalid: string[]; summary: PlaylistTextSummary } {
  const rows: { title: string; artist: string; artists: string[] }[] = [];
  const invalid: string[] = [];
  for (const line of value.split(/\r?\n/)) {
    const original = line.trim();
    if (!original) continue;
    const match = original.match(/\s[-–—]\s/);
    if (!match || match.index === undefined) { invalid.push(original); continue; }
    const title = original.slice(0, match.index).trim(); const artist = original.slice(match.index + match[0].length).trim();
    if (!title || !artist) { invalid.push(original); continue; }
    rows.push({ title, artist, artists: artist.split(/\s*(?:\/|＆|&|、|，|,)\s*/).filter(Boolean) });
  }
  return { rows, invalid, summary: { totalLines: value.split(/\r?\n/).filter((line) => line.trim()).length, validTracks: rows.length, invalidLines: invalid.length, uniqueArtists: new Set(rows.map((row) => row.artist.toLowerCase())).size } };
}
