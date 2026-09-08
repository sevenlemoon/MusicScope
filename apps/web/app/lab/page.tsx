"use client";

import AudioPanel from "../AudioPanel";
import PageFrame from "../PageFrame";
import { useI18n } from "../i18n";

export default function LabPage() {
  const { t } = useI18n();
  return <PageFrame title={t("nav.lab")}><section className="lab-intro"><p className="eyebrow">{t("lab.eyebrow")}</p><h2>{t("lab.title")}</h2><p className="muted">{t("lab.description")}</p></section><AudioPanel /></PageFrame>;
}
