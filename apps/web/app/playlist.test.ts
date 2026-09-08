import { describe, expect, it } from "vitest";
import { detectPlaylistLink, parsePlaylistText } from "./playlist";

describe("playlist URL detection", () => {
  it("detects a NetEase playlist and preserves its ID", () => {
    expect(detectPlaylistLink("https://music.163.com/m/playlist?id=5036528042&creatorId=3346225720")).toEqual({ provider: "netease", playlistId: "5036528042", valid: true });
  });

  it("rejects unsupported or malformed links", () => {
    expect(detectPlaylistLink("https://example.com/playlist?id=12").valid).toBe(false);
    expect(detectPlaylistLink("not a URL").valid).toBe(false);
  });

  it("parses dash variants, blank lines, multiple artists, and large input", () => {
    const value = ["Can We Kiss Forever? - Kina / Adriana Proenza", "Monody (Radio Edit) – TheFatRat / Laura Brehm", "Need You Right Now — HEDEGAARD / Hayley Warner", "malformed", ...Array.from({ length: 2997 }, (_, index) => `Track ${index} - Artist ${index}`), ""].join("\n");
    const result = parsePlaylistText(value);
    expect(result.rows[0].artists).toEqual(["Kina", "Adriana Proenza"]);
    expect(result.summary.totalLines).toBe(3001);
    expect(result.summary.validTracks).toBe(3000);
    expect(result.summary.invalidLines).toBe(1);
  });
});
