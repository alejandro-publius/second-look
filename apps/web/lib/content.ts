// Typed access to the content built by scripts/build-content.mjs. The JSON never carries gold labels
// for test items or photos; the server scores.
import raw from "@/generated/content.json";

export type FeatureId = "artificial_bank" | "dug_out_channel" | "invasive_plant" | "pipe_running";

export interface Feature {
  id: FeatureId;
  name: string;
  plain: string;
  question: string;
  wording_source: string;
  wording_status: string;
  app_item: string | null;
  verified_against_app: boolean;
  glossary_term: string;
}

export interface FormOption {
  id: string;
  label: string;
  value: string;
}

export interface FormItem {
  id: string;
  section: string;
  type: "choice" | "multi" | "yesno" | "number" | "pick_region_list" | "sliders";
  text: string;
  options?: FormOption[];
  unit?: string;
  sliders?: string[];
  allow_not_applicable?: boolean;
  depends_on?: { item: string; value: string };
  region_list?: string;
  note?: string;
  feature: FeatureId | null;
  verified_against_app: boolean;
  rating_check?: boolean;
}

export interface FormSection {
  id: string;
  title: string;
}

export interface TestItem {
  id: string;
  feature: FeatureId;
  photo_id: string;
}

export interface Photo {
  id: string;
  file: string;
  url: string;
  role: string;
  feature: string | null;
  placeholder: boolean;
  alt: string;
  /** CC BY and CC BY-SA ask us to name the author wherever the photo appears. See /credits. */
  author: string;
  license: string;
  source_url: string;
  width: number;
  height: number;
  /** Smaller AVIF and WebP copies, best first, when scripts/derive_photos.py made some. */
  sources?: PhotoSource[];
  /** The sizes attribute that goes with sources. */
  sizes?: string;
}

export interface PhotoSource {
  type: string;
  srcset: string;
}

export interface Mark {
  x: number;
  y: number;
  label: string;
}

export interface ContrastPair {
  assume_photo_id: string;
  actual_photo_id: string;
  assume_caption: string;
  actual_caption: string;
  /** Marks sit on the actual photo. Fractions of width and height, 0,0 top left. */
  marks?: Mark[];
}

export interface Lesson {
  feature: FeatureId;
  approved: boolean;
  rule_of_thumb: string;
  source: string;
  contrast_pairs: ContrastPair[];
  practice_marks?: Mark[];
  practice: {
    photo_id: string;
    gold: "present" | "absent";
    feedback_correct: string;
    feedback_wrong: string;
  };
}

export interface GlossaryTerm {
  term: string;
  plain: string;
}

export interface Region {
  region: string;
  name: string;
  approved: boolean;
  invasive_plants: { common_name: string; latin_name: string; source: string }[];
}

export interface Content {
  content_hash: string;
  consent_version: string;
  features: Feature[];
  form: { version: number; sections: FormSection[]; items: FormItem[] };
  test_items: TestItem[];
  warmup: WarmupItem[];
  glossary: GlossaryTerm[];
  regions: Record<string, Region>;
  lessons: Record<string, Lesson>;
  locale: Record<string, string>;
  photos: Record<string, Photo>;
  walks: Walk[];
  footage_credits: FootageCredit[];
  video_credits: VideoCredits;
  inat_checks: InatChecks;
}

/** A video walk (Update 14 3.7), from content/walks.yaml via scripts/build_walks.py. */
export interface Walk {
  id: string;
  title: string;
  author: string;
  license: string;
  source_url: string;
  country: string;
  creek_name: string;
  spot_name: string;
  clip: { file: string; start_s: number; seconds: number };
  poster_photo_id: string;
  /** The one question a gated flag made eligible at build time, or null. */
  question: { feature: FeatureId; note: string } | null;
  checker_run: "real" | "synthetic";
  checker_dropped: number;
}

export interface FootageCredit {
  id: string;
  title: string;
  author: string;
  license: string;
  source_url: string;
  country: string;
}

/** The open creek footage and photos in the video (UPDATE_22 6.6), from content/video_credits.yaml. */
export interface VideoCredits {
  /** The video's own licence, CC BY-SA 4.0 because several clips are CC BY-SA. */
  licence: string;
  licence_url: string;
  items: { title: string; author: string; license: string; license_url: string; source_url: string }[];
}

/**
 * What iNaturalist said about each of its photos we show, from results/inat_photos.json. Only these
 * three facts: never the species or the place, because a test photo's species is its answer.
 */
export interface InatChecks {
  checked_at: string;
  photos: Record<string, { found: boolean; research_grade: boolean; in_california: boolean }>;
}

export interface WarmupItem {
  id: string;
  photo_id: string;
  /** True on the creek in the more natural state. Exactly one of the pair carries it. */
  more_natural: boolean;
}

export const content = raw as unknown as Content;

export const FEATURE_IDS: FeatureId[] = ["artificial_bank", "dug_out_channel", "invasive_plant", "pipe_running"];

export function featureById(id: string): Feature | undefined {
  return content.features.find((f) => f.id === id);
}

export function photoById(id: string): Photo | undefined {
  return content.photos[id];
}

export function lessonFor(id: string): Lesson | undefined {
  return content.lessons[id];
}

export function testItemById(id: string): TestItem | undefined {
  return content.test_items.find((i) => i.id === id);
}

export function glossaryFor(term: string | null | undefined): string | undefined {
  if (!term) return undefined;
  const hit = content.glossary.find((g) => g.term.toLowerCase() === term.toLowerCase());
  return hit?.plain;
}

/** Every photo a visitor can see, in id order, for the credits page. */
// Every CC licence asks that the licence itself be named and linked wherever the photo appears.
// The manifest records the exact version, so the deed link follows from it with no guessing.
const LICENSE_URLS: Record<string, string> = {
  "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
  "CC-BY-2.0": "https://creativecommons.org/licenses/by/2.0/",
  "CC-BY-3.0": "https://creativecommons.org/licenses/by/3.0/",
  "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
  "own-CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
  "CC-BY-SA-2.0": "https://creativecommons.org/licenses/by-sa/2.0/",
  "CC-BY-SA-3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
  "CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
};

/** The creek in the more natural state, whichever side of the pair it was shown on. */
export function moreNatural(pair: WarmupItem[]): WarmupItem | undefined {
  return pair.find((w) => w.more_natural);
}

export function licenseUrl(license: string): string | undefined {
  return LICENSE_URLS[license];
}

/**
 * A licence as people write it, for display only: the manifest's CC-BY-SA-2.0 as CC BY-SA 2.0 and
 * public-domain as Public domain, the way the video's credits already write them, so /credits
 * names every licence one way (CRITIC_09 R05). The code itself still picks the deed link. A name
 * already in words, such as CC BY-SA 4.0, is kept as it is. CC0 has only ever had version 1.0, so
 * the video credits' plain CC0 is written CC0 1.0 like the photos' CC0-1.0.
 */
export function licenseName(license: string): string {
  if (license === "public-domain") return "Public domain";
  if (license === "CC0") return "CC0 1.0";
  if (license.startsWith("CC0-")) return `CC0 ${license.slice("CC0-".length)}`;
  const parts = license.replace(/^own-/, "").split("-");
  if (parts[0] === "CC" && parts.length >= 3) return `CC ${parts.slice(1, -1).join("-")} ${parts[parts.length - 1]}`;
  return license;
}

export function shownPhotos(): Photo[] {
  return Object.values(content.photos).sort((a, b) => a.id.localeCompare(b.id));
}

export function walkById(id: string): Walk | undefined {
  return (content.walks ?? []).find((w) => w.id === id);
}

/**
 * "Question n of total" for the form question at `index` of the questions on screen. A follow-up,
 * such as "Which ones?" after a yes on invasive plants, belongs to the question before it and
 * shares its number, so the total stays the same from the first question (REVIEW_03 R42).
 */
export function questionCount(shown: FormItem[], index: number): { n: number; total: number } {
  const main = (item: FormItem) => !item.depends_on;
  return {
    n: Math.max(1, shown.slice(0, index + 1).filter(main).length),
    total: content.form.items.filter(main).length,
  };
}
