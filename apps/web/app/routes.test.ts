import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("MusicScope information architecture", () => {
  it("has dedicated navigation routes and a concise home page", () => {
    expect(readFileSync("app/for-you/page.tsx", "utf8")).toContain("PageFrame");
    expect(readFileSync("app/my-music/page.tsx", "utf8")).toContain("visibleImportBatches");
    expect(readFileSync("app/discover/page.tsx", "utf8")).toContain("AudioPanel");
    expect(readFileSync("app/timeline/page.tsx", "utf8")).toContain("TimelinePage");
    const home = readFileSync("app/page.tsx", "utf8");
    expect(home).not.toContain("Resolved records");
    expect(home).not.toContain("Needs review");
  });
});
