import type { MetadataRoute } from "next";

// A static export writes this file at build time.
export const dynamic = "force-static";
import { THEME_LIGHT } from "./theme";
import { t } from "@/lib/t";

// Served at /manifest.webmanifest. Strings come from the locale like everything else.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: t("app.name"),
    short_name: t("app.name"),
    description: t("app.one_sentence"),
    start_url: "/?src=other",
    scope: "/",
    display: "standalone",
    // Android trusts these for the splash screen and the title bar, so they mirror --bg.
    background_color: THEME_LIGHT,
    theme_color: THEME_LIGHT,
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
