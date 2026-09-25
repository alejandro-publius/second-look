// A locale string may quote another string by its key, written as {time.test}. How long a thing
// takes is written once, under time., and every screen that quotes it reads it from there, so two
// screens can never give one thing two times (judge walk W09). A key with a dot in it is never a
// fill-in: t() fills only {name} with no dot.
//
// core/content_loader.py resolve_locale does the same in Python. Both refuse a key that is missing
// and a quoted string that quotes another in turn, so a reference is one step and always resolves.

export const LOCALE_REF = /\{([a-z_]+(?:\.[a-z0-9_]+)+)\}/g;

/** The problems with the references in a locale: each names the key and what is wrong. */
export function localeRefProblems(locale) {
  const problems = [];
  for (const [key, value] of Object.entries(locale)) {
    if (typeof value !== "string") continue;
    for (const [, ref] of value.matchAll(LOCALE_REF)) {
      const quoted = locale[ref];
      if (typeof quoted !== "string") problems.push(`${key} quotes ${ref}, which the locale does not have`);
      else if (new RegExp(LOCALE_REF.source).test(quoted)) problems.push(`${key} quotes ${ref}, which quotes another string in turn`);
    }
  }
  return problems;
}

/** The locale as a person reads it: every {a.b} replaced by the string it names. */
export function resolveLocale(locale) {
  const problems = localeRefProblems(locale);
  if (problems.length > 0) throw new Error(`locale references: ${problems.join("; ")}`);
  return Object.fromEntries(
    Object.entries(locale).map(([key, value]) => [key, typeof value === "string" ? value.replace(LOCALE_REF, (_whole, ref) => locale[ref]) : value]),
  );
}
