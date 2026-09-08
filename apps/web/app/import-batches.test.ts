import { describe, expect, it } from "vitest";
import { visibleImportBatches } from "./import-batches";

describe("import batch presentation", () => {
  it("reduces empty completed batches while keeping useful records", () => {
    const batches = [
      ...Array.from({ length: 8 }, (_, index) => ({ id: `empty-${index}`, total_records: 0, status: "completed" })),
      { id: "useful", total_records: 4, status: "completed" },
    ];
    expect(visibleImportBatches(batches, false)).toHaveLength(1);
    expect(visibleImportBatches(batches, false)[0].id).toBe("useful");
  });

  it("restores access to all history", () => {
    const batches = Array.from({ length: 7 }, (_, index) => ({ id: String(index), total_records: 0, status: "completed" }));
    expect(visibleImportBatches(batches, true)).toHaveLength(7);
  });
});
