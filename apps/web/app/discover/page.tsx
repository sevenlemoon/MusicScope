"use client";

import AudioPanel from "../AudioPanel";
import ConcertPanel from "../ConcertPanel";
import PageFrame from "../PageFrame";
import { useI18n } from "../i18n";

export default function DiscoverPage() {
  const { t } = useI18n();
  return <PageFrame title={t("nav.discover")}><ConcertPanel /><section id="audio"><AudioPanel /></section></PageFrame>;
}
