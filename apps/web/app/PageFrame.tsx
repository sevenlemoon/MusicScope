"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useI18n } from "./i18n";

export default function PageFrame({ children, title, eyebrow }: { children: React.ReactNode; title: string; eyebrow?: string }) {
  const { language, setLanguage, t } = useI18n();
  const pathname = usePathname();
  const links = [["/", "nav.home"], ["/for-you", "nav.forYou"], ["/my-music", "nav.myMusic"], ["/timeline", "nav.timeline"], ["/lab", "nav.lab"]] as const;
  return <main className="shell wide-shell"><header className="app-header"><Link className="brand" href="/"><span className="brand-mark">M</span><span>MusicScope</span></Link><div className="language-switcher"><button type="button" className={language === "zh" ? "active-language" : ""} onClick={() => setLanguage("zh")}>中文</button><span>|</span><button type="button" className={language === "en" ? "active-language" : ""} onClick={() => setLanguage("en")}>EN</button></div></header><nav className="main-nav" aria-label={t("nav.primary")}>{links.map(([href, key]) => <Link className={(href === "/" ? pathname === "/" : pathname.startsWith(href)) ? "active-nav" : ""} href={href} key={href}>{t(key)}</Link>)}</nav>{pathname !== "/" && <header className="page-heading"><p className="eyebrow">{eyebrow ?? t("header.eyebrow")}</p><h1 className="page-title">{title}</h1></header>}{children}</main>;
}
