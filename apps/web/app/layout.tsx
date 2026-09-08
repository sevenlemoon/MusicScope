import type { Metadata } from "next";
import "./globals.css";
import { LanguageProvider } from "./i18n";

export const metadata: Metadata = {
  title: "MusicScope",
  description: "Personal music intelligence workspace",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body><LanguageProvider>{children}</LanguageProvider></body>
    </html>
  );
}
