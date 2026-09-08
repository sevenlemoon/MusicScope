"use client";

import AudioPanel from "../AudioPanel";
import PageFrame from "../PageFrame";
import { useI18n } from "../i18n";

export default function LabPage() {
  const { t } = useI18n();
  return <PageFrame title={t("nav.lab")} eyebrow="STEMS / 04"><section className="stems-hero"><p className="chapter-label">STEMS / 04</p><p className="hero-english">BREAK<br />THE SOUND<br /><em>APART.</em></p><div><h1>{t("nav.lab")}</h1><p>{t("lab.description")}</p></div><div className="hero-waveform" aria-hidden="true">{Array.from({ length: 28 }, (_, index) => <i key={index} style={{ height: 18 + ((index * 17) % 62) }} />)}</div></section><AudioPanel /></PageFrame>;
}
