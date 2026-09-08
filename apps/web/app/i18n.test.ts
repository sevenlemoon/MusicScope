import { describe, expect, it } from "vitest";
import { DEFAULT_LANGUAGE, translate } from "./i18n";

describe("MusicScope language support", () => {
  it("defaults to Chinese and translates representative navigation text", () => {
    expect(DEFAULT_LANGUAGE).toBe("zh");
    expect(translate(DEFAULT_LANGUAGE, "nav.forYou")).toBe("为你推荐");
    expect(translate(DEFAULT_LANGUAGE, "audio.vocals")).toBe("人声");
  });

  it("switches to English and back without changing data labels", () => {
    expect(translate("en", "nav.timeline")).toBe("Timeline");
    expect(translate("zh", "nav.timeline")).toBe("时间线");
    expect(translate("en", "import.summary", { total: 8, withRecords: 3, empty: 5 })).toContain("8 imports");
  });
});
