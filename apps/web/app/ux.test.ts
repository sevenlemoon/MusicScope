import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("V2 product UX structure", () => {
  it("uses the personal library without unavailable behavior metrics", () => {
    const source = readFileSync("app/my-music/page.tsx", "utf8");
    expect(source).toContain("/api/v1/library");
    expect(source).toContain('type Tab = "tracks" | "artists" | "genres"');
    expect(source).not.toContain("completion_rate");
    expect(source).not.toContain("profile.recentEmpty");
    expect(source).toContain("allArtists.length");
    expect(source).toContain("filteredArtists.slice(0, RESULT_LIMIT)");
    expect(source).toContain("allGenres.filter");
    expect(source).toContain("filteredGenres.map");
  });

  it("localizes structured recommendation evidence instead of raw backend text", () => {
    const source = readFileSync("app/for-you/page.tsx", "utf8");
    expect(source).toContain("localizeEvidence");
    expect(source).not.toContain("item.explanation_evidence[0]?.text");
    expect(source).toContain('submit("skip", "NOT_FOR_TODAY")');
    expect(source).toContain('submit("dislike", "DISLIKE_ARTIST")');
    expect(source).toContain('submit("dislike", "DISLIKE_STYLE")');
    expect(source).toContain('submit("dislike", "SIMPLY_DISLIKE")');
    expect(source).toContain('status === "submitting"');
    expect(source).toContain("feedback.recorded");
  });

  it("keeps the assisted playlist workflow visible", () => {
    const source = readFileSync("app/PlaylistImport.tsx", "utf8");
    expect(source).toContain("playlist.step1");
    expect(source).toContain("playlist.membershipNote");
    expect(source).toContain("ANALYZING LIBRARY");
    expect(source).toContain("await onImported?.()");
    expect(readFileSync("app/page.tsx", "utf8")).toContain("onImported={refreshLibrary}");
  });

  it("keeps concert suggestions empty until the user types", () => {
    const source = readFileSync("app/ConcertPanel.tsx", "utf8");
    expect(source).toContain(": []");
    expect(source).toContain("concertProviderLabel(event.provider, language)");
  });
});
