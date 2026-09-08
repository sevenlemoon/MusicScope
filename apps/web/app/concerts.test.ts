import { describe, expect, it } from "vitest";
import { formatConcertDate, formatConcertTime, shouldShowConcertLink } from "./concerts";

describe("concert display helpers", () => {
  it("formats dates and preserves unknown event time", () => {
    expect(formatConcertDate("2027-03-18")).toContain("Mar");
    expect(formatConcertTime(null, "Asia/Shanghai")).toBe("Exact time not announced");
  });

  it("includes timezone when exact time is available", () => {
    expect(formatConcertTime("20:00", "Asia/Shanghai")).toBe("20:00 (Asia/Shanghai)");
  });

  it("only exposes legitimate links for live events", () => {
    expect(shouldShowConcertLink({ is_demo: true, external_url: "https://example.com/demo" })).toBe(false);
    expect(shouldShowConcertLink({ is_demo: false, external_url: "https://example.com/demo" })).toBe(false);
    expect(shouldShowConcertLink({ is_demo: false, external_url: "https://www.milet.jp/" })).toBe(true);
  });
});
