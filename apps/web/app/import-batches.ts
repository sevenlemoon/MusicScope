export type ImportBatchSummary = { total_records: number; status: string };

export function visibleImportBatches<T extends ImportBatchSummary>(batches: T[], showAll: boolean, limit = 5): T[] {
  if (showAll) return batches;
  return batches.filter((batch) => batch.total_records > 0 || batch.status !== "completed").slice(0, limit);
}
