// Python's round(x, n), which rounds an exact tie to the even digit, where Math.round and
// toFixed round it up. Ties are rare in coordinates but real: round(0.125, 2) is 0.12 in Python
// and toFixed gives 0.13. A stored coordinate that differs in its last digit would make the
// TypeScript record differ from the Python one, so the rounding is matched here and checked by
// the golden vectors in golden/helpers.json.

export function pyRound(x: number, digits: number): number {
  if (!Number.isFinite(x)) return x;
  const sign = x < 0 ? -1 : 1;
  const magnitude = Math.abs(x);
  // Enough digits to see whether the exact binary value is a tie. A tie is a dyadic fraction
  // whose decimal expansion stops, so it shows as 5 followed by zeros; a near miss such as
  // 2.675, which is really 2.67499999999999982..., shows its 4 well inside thirty digits.
  // toFixed is exact, so no rounding of the tail can turn a near miss into a tie.
  const extra = 30;
  const long = magnitude.toFixed(digits + extra);
  const [whole, fraction = ""] = long.split(".");
  const kept = fraction.slice(0, digits);
  const rest = fraction.slice(digits);
  const tie = rest === "5" + "0".repeat(extra - 1);
  let result: number;
  if (!tie) {
    result = Number(magnitude.toFixed(digits));
  } else {
    // Half to even on the last kept digit.
    const keptDigits = whole + kept;
    const last = Number(keptDigits[keptDigits.length - 1]);
    let asInteger = BigInt(keptDigits);
    if (last % 2 === 1) asInteger += 1n;
    const text = asInteger.toString().padStart(digits + 1, "0");
    const cut = text.length - digits;
    result = Number(digits === 0 ? text : `${text.slice(0, cut)}.${text.slice(cut)}`);
  }
  return sign * result === 0 ? 0 : sign * result;
}
