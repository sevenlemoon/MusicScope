export function formatConcertDate(value: string): string {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`));
}

export function formatConcertTime(value: string | null, timezone: string | null): string {
  if (!value) return "Exact time not announced";
  return timezone ? `${value} (${timezone})` : value;
}

export function shouldShowConcertLink(event: { is_demo: boolean; external_url?: string | null }): boolean {
  return !event.is_demo && Boolean(event.external_url) && !event.external_url!.includes("example.com");
}
