import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("V2 product UX structure", () => {
  it("uses the personal library endpoint for My Music", () => {
    const source = readFileSync("app/my-music/page.tsx", "utf8");
    expect(source).toContain("/api/v1/library");
    expect(source).toContain("profile.recentEmpty");
  });

  it("localizes structured recommendation evidence instead of raw backend text", () => {
    const source = readFileSync("app/for-you/page.tsx", "utf8");
    expect(source).toContain("localizeEvidence");
    expect(source).not.toContain("item.explanation_evidence[0]?.text");
  });

  it("keeps the assisted playlist workflow visible", () => {
    const source = readFileSync("app/PlaylistImport.tsx", "utf8");
    expect(source).toContain("playlist.step1");
    expect(source).toContain("playlist.membershipNote");
  });
});
