import type { MetadataRoute } from "next";
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
    background_color: "#fbfaf6",
    theme_color: "#1f3a2e",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
