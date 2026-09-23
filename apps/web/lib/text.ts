/**
 * A source line without its bare web address. The page links the source once, by its title
 * (design review 02, finding 1), so the address itself only makes a phone scroll sideways.
 */
export function withoutUrl(text: string): string {
  return text.replace(/\s*https?:\/\/\S+/g, "").trim();
}
