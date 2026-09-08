"use client";

import ConcertPanel from "../ConcertPanel";
import PageFrame from "../PageFrame";
import { useI18n } from "../i18n";

export default function ConcertsPage() {
  const { t } = useI18n();
  return <PageFrame title={t("nav.concerts")} eyebrow="LIVE / 02"><section className="concert-hero"><p className="chapter-label">LIVE / 02</p><p className="hero-english">WHO DO YOU<br /><em>WANT TO SEE?</em></p><h1>{t("v3.concertTitle")}</h1><p>{t("v3.concertIntro")}</p></section><ConcertPanel /></PageFrame>;
}
