"use client";

import Link from "next/link";
import { useI18n } from "./i18n";

export default function PageFrame({ children, title, eyebrow }: { children: React.ReactNode; title: string; eyebrow?: string }) {
  const { language, setLanguage, t } = useI18n();
  return <main className="shell wide-shell"><header className="app-header"><div><p className="eyebrow">{eyebrow ?? t("header.eyebrow")}</p><h1 className="page-title">{title}</h1></div><div className="language-switcher"><button type="button" className={language === "zh" ? "active-language" : ""} onClick={() => setLanguage("zh")}>中文</button><span>|</span><button type="button" className={language === "en" ? "active-language" : ""} onClick={() => setLanguage("en")}>EN</button></div></header><nav className="main-nav" aria-label="Primary navigation"><Link href="/for-you">{t("nav.forYou")}</Link><Link href="/my-music">{t("nav.myMusic")}</Link><Link href="/discover">{t("nav.discover")}</Link><Link href="/timeline">{t("nav.timeline")}</Link></nav>{children}</main>;
}
