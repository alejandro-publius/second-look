/**
 * A source line without its bare web address. The page links the source once, by its title
 * (design review 02, finding 1), so the address itself only makes a phone scroll sideways.
 */
export function withoutUrl(text: string): string {
  return text.replace(/\s*https?:\/\/\S+/g, "").trim();
}

/**
 * Why a measure is listed, then its source: "Pipes and drain outlets. OneAquaHealth Policy Brief".
 * A reason can be a form question, which already ends in a question mark, so the full stop goes in
 * only when the reasons do not end a sentence already. The line never reads "barriers?. One..."
 * (CRITIC_03 E06).
 */
export function reasonsThenSource(reasons: string[], source: string): string {
  const because = reasons.join(", ").trim();
  const from = withoutUrl(source);
  if (!because) return from;
  return /[.?!]$/.test(because) ? `${because} ${from}` : `${because}. ${from}`;
}
