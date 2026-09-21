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
  width: number;
  height: number;
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
  warmup: { id: string; photo_id: string }[];
  glossary: GlossaryTerm[];
  regions: Record<string, Region>;
  lessons: Record<string, Lesson>;
  locale: Record<string, string>;
  photos: Record<string, Photo>;
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
