// The colour values that cannot read a CSS variable: the <meta name="theme-color"> tag, the web
// app manifest, and the share card SVG, which is served as an image and so has no stylesheet.
// Every value here mirrors styles/tokens.css and scripts/design-check.mjs fails if one drifts.
export const THEME_LIGHT = "#f4f6f5";
export const THEME_DARK = "#0f1715";
export const PRINT_INK = "#000000";
export const PRINT_PAPER = "#ffffff";
export const CARD_SURFACE = "#ffffff";
export const CARD_INK = "#14211e";
export const CARD_INK_SOFT = "#4b5b57";
export const CARD_FLAG = "#f26b1d";
export const CARD_LINE = "#7e8b87";

// The card is drawn at poster size, so the gauge gets poster numbers on the same 4px grid.
export const CARD_FONT = "Atkinson Hyperlegible Next, system-ui, sans-serif";
