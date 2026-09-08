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

const PROVIDER_LABELS: Record<string, { zh: string; en: string }> = {
  official_milet: { zh: "milet 官方网站", en: "Official milet site" },
  ticketmaster: { zh: "Ticketmaster", en: "Ticketmaster" },
  demo: { zh: "演示数据", en: "Demo data" },
};

export function concertProviderLabel(provider: string | undefined, language: "zh" | "en"): string {
  const value = provider?.trim();
  if (!value) return language === "zh" ? "来源未注明" : "Source not specified";
  return PROVIDER_LABELS[value.toLocaleLowerCase()]?.[language] ?? (language === "zh" ? `来源：${value}` : `Source: ${value}`);
}
