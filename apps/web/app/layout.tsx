import type { Metadata, Viewport } from "next";
import Link from "next/link";
import "./globals.css";
import { hyperlegible, hyperlegibleMono } from "./fonts";
import { THEME_DARK, THEME_LIGHT } from "./theme";
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
  // Matches the page background in both schemes, so the phone chrome does not fight the page.
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: THEME_LIGHT },
    { media: "(prefers-color-scheme: dark)", color: THEME_DARK },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${hyperlegible.variable} ${hyperlegibleMono.variable}`}>
      <body>
        <a className="skip" href="#main">
          {t("nav.skip")}
        </a>
        <header className="site-header">
          <Link href="/" translate="no">
            {t("app.name")}
          </Link>
          <nav className="site-nav" aria-label={t("nav.label")}>
            <Link href="/about">{t("nav.about")}</Link>
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
