import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("MusicScope information architecture", () => {
  it("has the V3 primary destinations", () => {
    expect(readFileSync("app/for-you/page.tsx", "utf8")).toContain("PageFrame");
    expect(readFileSync("app/my-music/page.tsx", "utf8")).toContain("visibleImportBatches");
    expect(readFileSync("app/lab/page.tsx", "utf8")).toContain("AudioPanel");
    expect(readFileSync("app/PageFrame.tsx", "utf8")).toContain('["/lab", "nav.lab"]');
    expect(readFileSync("app/PageFrame.tsx", "utf8")).toContain('["/concerts", "nav.concerts"]');
    expect(readFileSync("app/PageFrame.tsx", "utf8")).not.toContain('["/timeline", "nav.timeline"]');
    expect(readFileSync("app/PageFrame.tsx", "utf8")).not.toContain('href="/discover"');
    expect(readFileSync("app/timeline/page.tsx", "utf8")).toContain('redirect("/my-music")');
    const home = readFileSync("app/page.tsx", "utf8");
    expect(home).not.toContain("Resolved records");
    expect(home).not.toContain("Needs review");
    expect(home).not.toContain("artist=milet");
  });

  it("keeps compatibility discover as a redirect", () => {
    expect(readFileSync("app/discover/page.tsx", "utf8")).toContain('redirect("/for-you")');
  });
});
