// Mirrors pipeline/bibleingest/textnorm.py so user queries match verse.text_search.

const ELISION = new Set(["ʼ", "᾽", "’", "᾿", "'"]);

export function isHebrew(s: string) {
  return /[֐-׿]/.test(s);
}

export function isGreek(s: string) {
  return /[Ͱ-Ͽἀ-῿]/.test(s);
}

/** Hebrew: consonants only (points, accents and maqaf removed). */
export function normHebrew(s: string) {
  return Array.from(s).filter((c) => c >= "א" && c <= "ת").join("");
}

/** Greek: no diacritics, lowercase, final sigma folded, letters only. */
export function normGreek(s: string) {
  return Array.from(s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase().replace(/ς/g, "σ"))
    .filter((c) => /\p{L}/u.test(c) && !ELISION.has(c))
    .join("");
}

/** Normalize one search word the way the given script is indexed. */
export function normWord(w: string) {
  if (isHebrew(w)) return normHebrew(w);
  if (isGreek(w)) return normGreek(w);
  return w.toLowerCase().replace(/[^\p{L}\p{N}'’-]/gu, "");
}
