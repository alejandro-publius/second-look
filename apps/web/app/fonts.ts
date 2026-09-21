// Self hosted through next/font/local from the installed packages, so no request leaves our origin
// and the strict connect-src policy stays as it is. Atkinson Hyperlegible Next was drawn for low
// vision readers, which is the reason it is here and not a taste call.
import localFont from "next/font/local";

export const hyperlegible = localFont({
  src: [
    {
      path: "../node_modules/@fontsource-variable/atkinson-hyperlegible-next/files/atkinson-hyperlegible-next-latin-wght-normal.woff2",
      style: "normal",
    },
  ],
  weight: "200 800",
  display: "swap",
  variable: "--font-hyperlegible",
  fallback: ["system-ui", "sans-serif"],
  preload: true,
});

// The mono cut is allowed only inside the View as FHIR sheet.
export const hyperlegibleMono = localFont({
  src: [
    {
      path: "../node_modules/@fontsource/atkinson-hyperlegible-mono/files/atkinson-hyperlegible-mono-latin-400-normal.woff2",
      style: "normal",
      weight: "400",
    },
  ],
  display: "swap",
  variable: "--font-hyperlegible-mono",
  fallback: ["ui-monospace", "monospace"],
  preload: false,
});
