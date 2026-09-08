"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useI18n } from "./i18n";

export default function PageFrame({ children, title, eyebrow }: { children: React.ReactNode; title: string; eyebrow?: string }) {
  const { language, setLanguage, t } = useI18n();
  const pathname = usePathname();
  const links = [["/", "nav.home"], ["/for-you", "nav.forYou"], ["/my-music", "nav.myMusic"], ["/concerts", "nav.concerts"], ["/lab", "nav.lab"]] as const;
  return <main className="shell"><header className="app-header"><Link className="brand" href="/" aria-label="MusicScope home"><span className="brand-mark">M</span><span>MusicScope</span></Link><nav className="main-nav" aria-label={t("nav.primary")}>{links.map(([href, key], index) => <Link className={(href === "/" ? pathname === "/" : pathname.startsWith(href)) ? "active-nav" : ""} href={href} key={href}><small>0{index + 1}</small>{t(key)}</Link>)}</nav><div className="language-switcher"><button type="button" className={language === "zh" ? "active-language" : ""} onClick={() => setLanguage("zh")}>中文</button><span>/</span><button type="button" className={language === "en" ? "active-language" : ""} onClick={() => setLanguage("en")}>EN</button></div></header>{pathname !== "/" && <header className="page-heading"><p className="chapter-label">{eyebrow ?? t("header.eyebrow")}</p><h1>{title}</h1></header>}<div className="page-enter">{children}</div><footer className="site-footer"><span>MUSICSCOPE</span><small>PERSONAL MUSIC INTELLIGENCE / 2026</small></footer></main>;
}
