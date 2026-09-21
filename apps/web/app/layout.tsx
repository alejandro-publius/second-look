import type { Metadata, Viewport } from "next";
import Link from "next/link";
import "./globals.css";
import { t } from "@/lib/t";
import { SwRegister } from "@/components/SwRegister";

export const metadata: Metadata = {
  title: t("app.name"),
  description: t("app.one_sentence"),
  manifest: "/manifest.webmanifest",
  appleWebApp: { capable: true, title: t("app.name"), statusBarStyle: "default" },
  icons: { icon: "/icons/icon-192.png", apple: "/icons/icon-192.png" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#1f3a2e",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a className="skip" href="#main">
          {t("nav.skip")}
        </a>
        <header className="site-header">
          <Link href="/">{t("app.name")}</Link>
          <nav className="site-nav" aria-label={t("nav.label")}>
            <Link href="/about">{t("nav.about")}</Link>
            <Link href="/privacy">{t("nav.privacy")}</Link>
          </nav>
        </header>
        <main id="main" tabIndex={-1}>
          {children}
        </main>
        <SwRegister />
      </body>
    </html>
  );
}
