// Every string a person sees goes through here and comes from content/locales/en.json.
import { content } from "./content";

export function t(key: string, params?: Record<string, string | number>): string {
  const s = content.locale[key];
  if (s === undefined) return `[missing: ${key}]`;
  if (!params) return s;
  return s.replace(/\{(\w+)\}/g, (whole, name: string) => (name in params ? String(params[name]) : whole));
}

export function has(key: string): boolean {
  return key in content.locale;
}
