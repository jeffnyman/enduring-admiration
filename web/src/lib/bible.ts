import "server-only";
import { db } from "./db";
import { normWord } from "./normalize";

// ---------------------------------------------------------------------------- types
export type Book = {
  id: string;
  name: string;
  section: "OT" | "DC" | "NT";
  ord: number;
  canon_protestant: number;
  canon_catholic: number;
  canon_orthodox: number;
  chapters: number;
  /** set for books read through a layout (Greek Daniel, Greek Esther) */
  layout: Layout | null;
};

export type Layout = { bookId: string; replaces: string[]; description: string };

export type Edition = {
  id: string;
  name: string;
  language: string;
  direction: "ltr" | "rtl";
  kind: string;
  notes: string | null;
};

export type Token = {
  id: number;
  position: number;
  surface: string;
  leading: string;
  trailing: string;
  variant: string;
  tagged: boolean;
  gloss: string | null;
  glossKind: "contextual" | "lexical" | null;
};

export type EditionVerse = {
  verseId: number;
  editionId: string;
  bookId: string;
  chapter: number;
  verse: number;
  part: string;
  text: string;
  richJson: string | null;
  sourceRef: string | null;
  heading: string | null;
  relation: string;
  rule: string | null;
  note: string | null;
  notes: string[];
  tokens: Token[];
  /** true when this source verse was already shown at an earlier canonical verse */
  continued: boolean;
};

export type CanonRow = {
  canonId: number;
  /** Standard reference of this row */
  canonBook: string;
  canonChapter: number;
  verse: number;
  /** label shown for the row: the Standard verse, or the layout's own ('24', 'A 1') */
  label: string;
  /** element id / URL fragment for the row, unique per page: GEN-1-1, ESG-1-A1 */
  anchor: string;
  /** number of cross-references from this verse */
  xrefs: number;
  editions: Record<string, EditionVerse[]>;
};

// ---------------------------------------------------------------------------- books
export function getLayouts(): Layout[] {
  return (
    db().prepare("SELECT book_id AS bookId, replaces, description FROM layout").all() as {
      bookId: string; replaces: string; description: string;
    }[]
  ).map((l) => ({ ...l, replaces: l.replaces.split(",") }));
}

/** Books that have Standard verses, plus books read through a layout (chapters from the layout). */
export function getBooks(): Book[] {
  const layouts = new Map(getLayouts().map((l) => [l.bookId, l]));
  const rows = db()
    .prepare(
      `SELECT b.id, b.name, b.section, b.ord, b.canon_protestant, b.canon_catholic, b.canon_orthodox,
              COALESCE((SELECT MAX(chapter) FROM layout_verse lv WHERE lv.book_id = b.id),
                       (SELECT MAX(chapter) FROM canon_verse cv WHERE cv.book_id = b.id)) AS chapters
       FROM book b
       WHERE EXISTS (SELECT 1 FROM canon_verse cv WHERE cv.book_id = b.id)
          OR EXISTS (SELECT 1 FROM layout l WHERE l.book_id = b.id)
       ORDER BY b.ord`,
    )
    .all() as Omit<Book, "layout">[];
  return rows.map((b) => ({ ...b, layout: layouts.get(b.id) ?? null }));
}

export function getBook(id: string): Book | undefined {
  return getBooks().find((b) => b.id === id);
}

export function getEditions(): Edition[] {
  return db().prepare("SELECT id, name, language, direction, kind, notes FROM edition").all() as Edition[];
}

/** Columns shown by default for a book. */
export function defaultColumns(book: Pick<Book, "section" | "layout">): string[] {
  const section = book.section;
  if (book.layout) return ["WEB", "WLC", "LXX-SWETE"];   // Greek Daniel / Esther: Hebrew is there too
  if (section === "NT") return ["WEB", "SBLGNT"];
  if (section === "DC") return ["WEB", "LXX-SWETE"];
  return ["WEB", "WLC", "LXX-SWETE"];
}

export function neighbours(bookId: string, chapter: number) {
  const books = getBooks();
  const i = books.findIndex((b) => b.id === bookId);
  const b = books[i];
  const prev =
    chapter > 1 ? { book: b.id, chapter: chapter - 1 } : i > 0 ? { book: books[i - 1].id, chapter: books[i - 1].chapters } : null;
  const next =
    chapter < b.chapters ? { book: b.id, chapter: chapter + 1 } : i < books.length - 1 ? { book: books[i + 1].id, chapter: 1 } : null;
  return { prev, next };
}

// ---------------------------------------------------------------------------- chapter
const anchorOf = (book: string, chapter: number, label: string) => `${book}-${chapter}-${label.replace(/\s+/g, "")}`;

export function getChapter(bookId: string, chapter: number, editions: string[]): CanonRow[] {
  const d = db();
  const isLayout = !!d.prepare("SELECT 1 FROM layout WHERE book_id = ?").get(bookId);
  const canon = (
    isLayout
      ? d
          .prepare(
            `SELECT cv.id, cv.book_id AS canonBook, cv.chapter AS canonChapter, cv.verse, lv.label
             FROM layout_verse lv JOIN canon_verse cv ON cv.id = lv.canon_verse_id
             WHERE lv.book_id = ? AND lv.chapter = ? ORDER BY lv.seq`,
          )
          .all(bookId, chapter)
      : d
          .prepare(
            `SELECT id, book_id AS canonBook, chapter AS canonChapter, verse, CAST(verse AS TEXT) AS label
             FROM canon_verse WHERE book_id = ? AND chapter = ? ORDER BY verse`,
          )
          .all(bookId, chapter)
  ) as { id: number; canonBook: string; canonChapter: number; verse: number; label: string }[];
  if (!canon.length) return [];
  const ids = canon.map((c) => c.id);
  const ph = (n: number) => Array(n).fill("?").join(",");

  const rows = d
    .prepare(
      `SELECT m.canon_verse_id AS canonId, m.relation, m.rule, m.note,
              v.id AS verseId, v.edition_id AS editionId, v.book_id AS bookId, v.chapter, v.verse, v.part,
              v.text, v.rich_json AS richJson, v.source_ref AS sourceRef, v.heading_before AS heading
       FROM verse_map m JOIN verse v ON v.id = m.verse_id
       WHERE m.canon_verse_id IN (${ph(ids.length)}) AND v.edition_id IN (${ph(editions.length)})
       ORDER BY m.canon_verse_id, v.edition_id, v.book_id, v.chapter, v.verse, v.part`,
    )
    .all(...ids, ...editions) as (Omit<EditionVerse, "tokens" | "notes" | "continued"> & { canonId: number })[];

  const verseIds = [...new Set(rows.map((r) => r.verseId))];
  const tokens = new Map<number, Token[]>();
  const notes = new Map<number, string[]>();
  if (verseIds.length) {
    for (const t of d
      .prepare(
        `SELECT id, verse_id AS verseId, position, surface, leading, trailing, variant,
                morph_scheme IS NOT NULL AS tagged, gloss, gloss_kind AS glossKind
         FROM token WHERE verse_id IN (${ph(verseIds.length)}) ORDER BY verse_id, position`,
      )
      .all(...verseIds) as (Omit<Token, "tagged"> & { verseId: number; tagged: number })[]) {
      const list = tokens.get(t.verseId) ?? [];
      list.push({ id: t.id, position: t.position, surface: t.surface, leading: t.leading, trailing: t.trailing,
                  variant: t.variant, tagged: !!t.tagged, gloss: t.gloss, glossKind: t.glossKind });
      tokens.set(t.verseId, list);
    }
    for (const n of d
      .prepare(`SELECT verse_id AS verseId, text FROM verse_note WHERE verse_id IN (${ph(verseIds.length)}) ORDER BY id`)
      .all(...verseIds) as { verseId: number; text: string }[]) {
      notes.set(n.verseId, [...(notes.get(n.verseId) ?? []), n.text]);
    }
  }

  const byCanon = new Map<number, Record<string, EditionVerse[]>>();
  for (const r of rows) {
    const rec = byCanon.get(r.canonId) ?? {};
    const ev: EditionVerse = {
      verseId: r.verseId, editionId: r.editionId, bookId: r.bookId, chapter: r.chapter, verse: r.verse,
      part: r.part, text: r.text, richJson: r.richJson, sourceRef: r.sourceRef, heading: r.heading,
      relation: r.relation,
      rule: r.rule, note: r.note,
      tokens: tokens.get(r.verseId) ?? [],
      notes: notes.get(r.verseId) ?? [],
      continued: false,
    };
    (rec[r.editionId] ??= []).push(ev);
    byCanon.set(r.canonId, rec);
  }
  // A source verse mapped to several rows is shown once, at the first row in reading order
  // (layout order can differ from Standard order: Esther's Addition A comes before 1:1)
  const seen = new Set<number>();
  for (const c of canon) {
    for (const list of Object.values(byCanon.get(c.id) ?? {})) {
      for (const ev of list) {
        ev.continued = seen.has(ev.verseId);
        seen.add(ev.verseId);
      }
    }
  }
  const xref = new Map(
    (
      d
        .prepare(`SELECT from_canon AS id, COUNT(*) AS n FROM cross_ref WHERE from_canon IN (${ph(ids.length)}) GROUP BY 1`)
        .all(...ids) as { id: number; n: number }[]
    ).map((r) => [r.id, r.n]),
  );
  return canon.map((c) => ({
    canonId: c.id,
    xrefs: xref.get(c.id) ?? 0,
    canonBook: c.canonBook,
    canonChapter: c.canonChapter,
    verse: c.verse,
    label: c.label,
    anchor: anchorOf(bookId, chapter, c.label),
    editions: byCanon.get(c.id) ?? {},
  }));
}

/**
 * Reader URL for a Standard verse. Verses of a book that only exists as a layout (Greek
 * Esther's additions, ESG) live on the layout's pages; everything else on its Standard page.
 */
export function verseHref(canonId: number, book: string, chapter: number, verse: number): string {
  const lv = db()
    .prepare(
      `SELECT lv.book_id AS book, lv.chapter, lv.label FROM layout_verse lv
       WHERE lv.canon_verse_id = ? AND lv.book_id = ?`,
    )
    .get(canonId, book) as { book: string; chapter: number; label: string } | undefined;
  if (lv) return `/read/${lv.book}/${lv.chapter}#${anchorOf(lv.book, lv.chapter, lv.label)}`;
  return `/read/${book}/${chapter}#${anchorOf(book, chapter, String(verse))}`;
}

// ---------------------------------------------------------------------------- word details
export type LexEntry = {
  lexiconId: string;
  lexiconName: string;
  match: string;
  entryKey: string;
  lemma: string;
  translit: string | null;
  pronunciation: string | null;
  partOfSpeech: string | null;
  shortDef: string | null;
  definition: string | null;
  derivation: string | null;
  kjvUsage: string | null;
  status: string | null;
};

export type Morpheme = {
  id: number;
  position: number;
  role: string;
  surface: string;
  lemma: string | null;
  strongs: string | null;
  strongsExt: string | null;
  morphCode: string | null;
  morphSummary: string | null;
  gloss: string | null;
  entries: LexEntry[];
  /** key for concordance and equivalents: Strong's, else STEP extended number, else lemma:<lemma> */
  key: string | null;
  href: string | null;
  equivalents: Equivalent[];
};

export type Equivalent = {
  key: string;
  href: string;
  lemma: string;
  gloss: string | null;
  both: number;
  fromVerses: number;
  /** New Testament occurrences of a Greek equivalent */
  ntCount: number | null;
};

export type WordDetails = {
  tokenId: number;
  surface: string;
  translit: string | null;
  gloss: string | null;
  tagStatus: string;
  variant: string;
  /** the transcription's form when an OCR error was corrected (Swete) */
  ocrOriginal: string | null;
  edition: Edition;
  ref: string;
  morphemes: Morpheme[];
};

export function getWord(tokenId: number): WordDetails | null {
  const d = db();
  const t = d
    .prepare(
      `SELECT t.id, t.surface, t.translit, t.gloss, t.tag_status AS tagStatus, t.variant, t.morph_scheme AS scheme,
              t.ocr_original AS ocrOriginal,
              v.edition_id AS editionId, b.name AS bookName, v.chapter, v.verse, v.part, v.source_ref AS sourceRef
       FROM token t JOIN verse v ON v.id = t.verse_id JOIN book b ON b.id = v.book_id WHERE t.id = ?`,
    )
    .get(tokenId) as
    | { id: number; surface: string; translit: string | null; gloss: string | null; tagStatus: string; variant: string;
        ocrOriginal: string | null;
        scheme: string | null; editionId: string; bookName: string; chapter: number; verse: number; part: string;
        sourceRef: string | null }
    | undefined;
  if (!t) return null;
  const edition = getEditions().find((e) => e.id === t.editionId)!;
  const morphemes = d
    .prepare(
      `SELECT m.id, m.position, m.role, m.surface, m.lemma, m.strongs, m.strongs_ext AS strongsExt,
              m.morph_code AS morphCode, mc.summary AS morphSummary, m.gloss
       FROM morpheme m LEFT JOIN morph_code mc ON mc.scheme_id = ? AND mc.code = m.morph_code
       WHERE m.token_id = ? ORDER BY m.position`,
    )
    .all(t.scheme, tokenId) as unknown as Omit<Morpheme, "entries">[];
  const entryStmt = d.prepare(
    `SELECT ml.lexicon_id AS lexiconId, l.name AS lexiconName, ml.match, le.entry_key AS entryKey, le.lemma,
            le.translit, le.pronunciation, le.part_of_speech AS partOfSpeech, le.short_def AS shortDef,
            le.definition, le.derivation, le.kjv_usage AS kjvUsage,
            json_extract(le.extra_json, '$.status') AS status
     FROM morpheme_lexicon ml JOIN lexicon_entry le ON le.id = ml.entry_id JOIN lexicon l ON l.id = ml.lexicon_id
     WHERE ml.morpheme_id = ?
     ORDER BY CASE ml.lexicon_id WHEN 'bdb' THEN 1 WHEN 'thayer' THEN 2 WHEN 'lsj' THEN 3 ELSE 4 END, le.id`,
  );
  const isGreek = edition.language === "grc";
  return {
    tokenId: t.id,
    surface: t.surface,
    translit: t.translit,
    gloss: t.gloss,
    tagStatus: t.tagStatus,
    variant: t.variant,
    ocrOriginal: t.ocrOriginal,
    edition,
    ref: `${t.bookName} ${t.chapter}:${t.verse}${t.part}${t.sourceRef ? ` (${t.sourceRef})` : ""}`,
    morphemes: morphemes.map((m) => {
      const key = m.role === "prefix" ? null : wordKey(m.strongs, m.strongsExt, isGreek ? m.lemma : null);
      return {
        ...m,
        entries: entryStmt.all(m.id) as LexEntry[],
        key,
        href: key ? keyHref(key) : null,
        equivalents: key ? getEquivalents(key, isGreek ? "grk>heb" : "heb>grk", 4) : [],
      };
    }),
  };
}

// ---------------------------------------------------------------------------- cross-references
export type CrossRef = { href: string; label: string; text: string; votes: number | null; source: string };

/** Readable reference for a Standard verse (or range), e.g. "Romans 1:19-20". */
function refLabel(startId: number, endId: number): string {
  const d = db();
  const a = d.prepare(
    "SELECT b.name, cv.chapter, cv.verse FROM canon_verse cv JOIN book b ON b.id = cv.book_id WHERE cv.id = ?",
  );
  const s = a.get(startId) as { name: string; chapter: number; verse: number };
  if (startId === endId) return `${s.name} ${s.chapter}:${s.verse}`;
  const e = a.get(endId) as { name: string; chapter: number; verse: number };
  return e.chapter === s.chapter
    ? `${s.name} ${s.chapter}:${s.verse}-${e.verse}`
    : `${s.name} ${s.chapter}:${s.verse}-${e.chapter}:${e.verse}`;
}

export function getCrossRefs(canonId: number, limit = 60): { label: string; total: number; refs: CrossRef[] } {
  const d = db();
  const total = (d.prepare("SELECT COUNT(*) AS n FROM cross_ref WHERE from_canon = ?").get(canonId) as { n: number }).n;
  // the WEB's own notes first, then OpenBible by votes
  const rows = d
    .prepare(
      `SELECT to_start AS a, to_end AS b, votes, source FROM cross_ref WHERE from_canon = ?
       ORDER BY source = 'web' DESC, votes DESC, to_start LIMIT ?`,
    )
    .all(canonId, limit) as { a: number; b: number; votes: number | null; source: string }[];
  const loc = d.prepare("SELECT book_id AS book, chapter, verse FROM canon_verse WHERE id = ?");
  // English text of the range (first 3 verses), preferring the WEB verse from the canonical book
  const text = d.prepare(
    `SELECT v.text FROM verse_map m JOIN verse v ON v.id = m.verse_id JOIN canon_verse cv ON cv.id = m.canon_verse_id
     WHERE m.canon_verse_id BETWEEN ? AND ? AND v.edition_id = 'WEB'
     GROUP BY m.canon_verse_id ORDER BY m.canon_verse_id, v.book_id = cv.book_id DESC LIMIT 3`,
  );
  const self = loc.get(canonId) as { book: string; chapter: number; verse: number } | undefined;
  return {
    label: refLabel(canonId, canonId),
    total,
    refs: rows.map((r) => {
      const at = loc.get(r.a) as { book: string; chapter: number; verse: number };
      const parts = (text.all(r.a, r.b) as { text: string }[]).map((t) => t.text);
      return {
        href: verseHref(r.a, at.book, at.chapter, at.verse),
        label: refLabel(r.a, r.b),
        text: parts.join(" ") + (r.b - r.a > 2 && self ? " …" : ""),
        votes: r.votes,
        source: r.source,
      };
    }),
  };
}

// ---------------------------------------------------------------------------- lemma keys & equivalents
/** The key used by lemma_link and concordance pages. */
export function wordKey(strongs: string | null, ext: string | null, lemma: string | null): string | null {
  if (strongs) return strongs;
  if (ext && /^G\d+$/.test(ext)) return ext;
  return lemma ? `lemma:${lemma}` : null;
}

export function keyHref(key: string): string {
  return key.startsWith("lemma:") ? `/lemma/${encodeURIComponent(key.slice(6))}` : `/strongs/${key}`;
}

/** Headword and short gloss for a key, preferring LSJ/BDB glosses over Strong's. */
export function keyInfo(key: string): { lemma: string; gloss: string | null } {
  const d = db();
  const row = (
    key.startsWith("lemma:")
      ? d.prepare(
          `SELECT lemma, short_def AS gloss FROM lexicon_entry WHERE lemma = ?
           ORDER BY CASE lexicon_id WHEN 'lsj' THEN 0 ELSE 1 END LIMIT 1`,
        ).get(key.slice(6))
      : d.prepare(
          `SELECT le.lemma, le.short_def AS gloss FROM lexicon_strongs ls JOIN lexicon_entry le ON le.id = ls.entry_id
           WHERE ls.strongs = @k OR ls.strongs_ext = @k
           ORDER BY CASE le.lexicon_id WHEN 'lsj' THEN 0 WHEN 'bdb' THEN 0 WHEN 'strongs-grk' THEN 1
                    WHEN 'strongs-heb' THEN 1 ELSE 2 END, le.id LIMIT 1`,
        ).get({ k: key })
  ) as { lemma: string; gloss: string | null } | undefined;
  return row ?? { lemma: key.replace(/^lemma:/, ""), gloss: null };
}

export function getEquivalents(key: string, direction: "heb>grk" | "grk>heb", limit = 6): Equivalent[] {
  const d = db();
  const rows = d
    .prepare(
      `SELECT to_key AS key, both_verses AS both, from_verses AS fromVerses FROM lemma_link
       WHERE direction = ? AND from_key = ? ORDER BY rank LIMIT ?`,
    )
    .all(direction, key, limit) as { key: string; both: number; fromVerses: number }[];
  const nt = d.prepare(
    `SELECT COUNT(*) AS n FROM morpheme m JOIN token t ON t.id = m.token_id JOIN verse v ON v.id = t.verse_id
     WHERE v.edition_id = 'SBLGNT' AND m.strongs = ?`,
  );
  return rows.map((r) => {
    const info = keyInfo(r.key);
    const gloss = info.gloss && info.gloss.length > 60 ? info.gloss.slice(0, 57) + "…" : info.gloss;
    return {
      ...r,
      href: keyHref(r.key),
      lemma: info.lemma,
      gloss,
      ntCount: direction === "heb>grk" && /^G\d+$/.test(r.key) ? (nt.get(r.key) as { n: number }).n : null,
    };
  });
}

/** Lemmas a Hebrew or Greek search word belongs to: whole-word or stem match (finds בראשית's ראשית). */
export function lemmaMatches(q: string) {
  const word = q.trim();
  if (!word || /\s/.test(word)) return [];
  const norm = normWord(word);
  if (!norm || !/[\u05D0-\u05EA\u0370-\u03FF\u1F00-\u1FFF]/.test(norm)) return [];
  const rows = db()
    .prepare(
      `SELECT m.strongs, m.strongs_ext AS ext, m.lemma, v.edition_id AS editionId, COUNT(*) AS n
       FROM morpheme m JOIN token t ON t.id = m.token_id JOIN verse v ON v.id = t.verse_id
       WHERE (t.surface_norm = @q OR m.surface_norm = @q) AND m.role != 'prefix'
       GROUP BY 1, 2, 3, 4 ORDER BY n DESC LIMIT 12`,
    )
    .all({ q: norm }) as { strongs: string | null; ext: string | null; lemma: string | null; editionId: string; n: number }[];
  const byKey = new Map<string, { key: string; href: string; lemma: string; gloss: string | null; matches: number; editions: string[] }>();
  for (const r of rows) {
    const key = wordKey(r.strongs, r.ext, r.lemma);
    if (!key) continue;
    const cur = byKey.get(key) ?? { key, href: keyHref(key), ...keyInfo(key), matches: 0, editions: [] };
    cur.matches += r.n;
    cur.editions.push(r.editionId);
    byKey.set(key, cur);
  }
  return [...byKey.values()];
}

// ---------------------------------------------------------------------------- search
export type SearchHit = {
  href: string;
  editionId: string;
  bookId: string;
  bookName: string;
  canonBook: string;
  canonChapter: number;
  canonVerse: number;
  ref: string;
  snippet: string;
};

/** Build a safe FTS5 query: every word quoted (implicit AND); "quoted phrases" kept. */
export function ftsQuery(q: string): string | null {
  const parts: string[] = [];
  const re = /"([^"]+)"|(\S+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(q))) {
    if (m[1]) {
      const words = m[1].split(/\s+/).map(normWord).filter(Boolean);
      if (words.length) parts.push(`"${words.join(" ")}"`);
    } else {
      const w = normWord(m[2]);
      if (w) parts.push(`"${w}"`);
    }
  }
  return parts.length ? parts.join(" ") : null;
}

export function search(q: string, edition: string, limit = 200): { total: number; hits: SearchHit[] } {
  const fts = ftsQuery(q);
  if (!fts) return { total: 0, hits: [] };
  const d = db();
  const total = (
    d
      .prepare(
        `SELECT COUNT(*) AS n FROM verse_fts f JOIN verse v ON v.id = f.rowid
         WHERE verse_fts MATCH ? AND v.edition_id = ?`,
      )
      .get(fts, edition) as { n: number }
  ).n;
  const rows = d
    .prepare(
      `SELECT v.id, v.edition_id AS editionId, v.book_id AS bookId, b.name AS bookName, v.chapter, v.verse, v.part,
              v.text, snippet(verse_fts, 0, '\u0001', '\u0002', '…', 24) AS snip
       FROM verse_fts f JOIN verse v ON v.id = f.rowid JOIN book b ON b.id = v.book_id
       WHERE verse_fts MATCH ? AND v.edition_id = ?
       ORDER BY b.ord, v.chapter, v.verse LIMIT ?`,
    )
    .all(fts, edition, limit) as {
    id: number; editionId: string; bookId: string; bookName: string; chapter: number; verse: number; part: string;
    text: string; snip: string;
  }[];
  const canonStmt = d.prepare(
    `SELECT cv.id, cv.book_id AS book, cv.chapter, cv.verse FROM verse_map m JOIN canon_verse cv ON cv.id = m.canon_verse_id
     WHERE m.verse_id = ? ORDER BY cv.id LIMIT 1`,
  );
  const hits = rows.map((r) => {
    const c = canonStmt.get(r.id) as { id: number; book: string; chapter: number; verse: number };
    // English is indexed as-is, so the FTS snippet can be shown; original-language text is
    // indexed without diacritics, so show the verse itself.
    const snippet = r.editionId === "WEB" ? r.snip : r.text;
    return {
      href: verseHref(c.id, c.book, c.chapter, c.verse),
      editionId: r.editionId, bookId: r.bookId, bookName: r.bookName,
      canonBook: c.book, canonChapter: c.chapter, canonVerse: c.verse,
      ref: `${r.bookName} ${r.chapter}:${r.verse}${r.part}`, snippet,
    };
  });
  return { total, hits };
}

// ---------------------------------------------------------------------------- Strong's
export function normalizeStrongs(s: string): { base: string; ext: string } | null {
  const m = /^([HG])0*(\d{1,5})([a-zA-Z]?)$/.exec(s.trim());
  if (!m) return null;
  const n = m[2].padStart(4, "0");
  return { base: `${m[1].toUpperCase()}${n}`, ext: `${m[1].toUpperCase()}${n}${m[3]}` };
}

export type StrongsOccurrence = {
  href: string;
  canonId: number;
  editionId: string;
  canonBook: string;
  bookName: string;
  canonChapter: number;
  canonVerse: number;
  surface: string;
  lemma: string | null;
  strongsExt: string | null;
};

export function getStrongs(id: string) {
  const s = normalizeStrongs(id);
  if (!s) return null;
  const d = db();
  // a letter-suffixed number (H1254a) matches exactly; a plain one matches the Strong's number or a
  // STEP extended number stored only as strongs_ext (Septuagint-only words, G6000+)
  const hasExt = s.ext !== s.base;
  const entries = d
    .prepare(
      `SELECT DISTINCT le.lexicon_id AS lexiconId, l.name AS lexiconName, le.entry_key AS entryKey, le.lemma,
              le.translit, le.pronunciation, le.part_of_speech AS partOfSpeech, le.short_def AS shortDef,
              le.definition, le.derivation, le.kjv_usage AS kjvUsage,
              json_extract(le.extra_json, '$.status') AS status, 'strongs' AS match
       FROM lexicon_strongs ls JOIN lexicon_entry le ON le.id = ls.entry_id JOIN lexicon l ON l.id = le.lexicon_id
       WHERE ${hasExt ? "ls.strongs_ext = @k" : "(ls.strongs = @k OR ls.strongs_ext = @k)"}
       ORDER BY CASE le.lexicon_id WHEN 'strongs-heb' THEN 0 WHEN 'strongs-grk' THEN 0 WHEN 'bdb' THEN 1
                WHEN 'thayer' THEN 2 ELSE 3 END, le.id`,
    )
    .all({ k: hasExt ? s.ext : s.base }) as LexEntry[];
  const where = hasExt ? "m.strongs_ext = @k" : "(m.strongs = @k OR (m.strongs IS NULL AND m.strongs_ext = @k))";
  const counts = d
    .prepare(
      `SELECT v.edition_id AS editionId, COUNT(*) AS n FROM morpheme m JOIN token t ON t.id = m.token_id
       JOIN verse v ON v.id = t.verse_id WHERE ${where} GROUP BY 1`,
    )
    .all({ k: hasExt ? s.ext : s.base }) as { editionId: string; n: number }[];
  const occurrences = d
    .prepare(
      `SELECT cv.id AS canonId, v.edition_id AS editionId, cv.book_id AS canonBook, b.name AS bookName, cv.chapter AS canonChapter,
              cv.verse AS canonVerse, t.surface, m.lemma, m.strongs_ext AS strongsExt
       FROM morpheme m JOIN token t ON t.id = m.token_id JOIN verse v ON v.id = t.verse_id
       JOIN verse_map vm ON vm.verse_id = v.id JOIN canon_verse cv ON cv.id = vm.canon_verse_id
       JOIN book b ON b.id = cv.book_id
       WHERE ${where} GROUP BY t.id ORDER BY b.ord, cv.chapter, cv.verse, v.edition_id LIMIT 2000`,
    )
    .all({ k: hasExt ? s.ext : s.base }) as Omit<StrongsOccurrence, "href">[];
  const withHref = occurrences.map((o) => ({
    ...o, href: verseHref(o.canonId, o.canonBook, o.canonChapter, o.canonVerse),
  }));
  const key = hasExt ? s.ext : s.base;
  return {
    id: key, entries, counts, occurrences: withHref,
    equivalents: getEquivalents(s.base, key.startsWith("H") ? "heb>grk" : "grk>heb", 8),
  };
}

/** Concordance for a Septuagint lemma that has no Strong's or extended number. */
export function getLemma(lemma: string) {
  const d = db();
  const entries = d
    .prepare(
      `SELECT le.lexicon_id AS lexiconId, l.name AS lexiconName, le.entry_key AS entryKey, le.lemma, le.translit,
              le.pronunciation, le.part_of_speech AS partOfSpeech, le.short_def AS shortDef, le.definition,
              le.derivation, le.kjv_usage AS kjvUsage, json_extract(le.extra_json, '$.status') AS status,
              'lemma' AS match
       FROM lexicon_entry le JOIN lexicon l ON l.id = le.lexicon_id WHERE le.lemma = ?`,
    )
    .all(lemma) as LexEntry[];
  const counts = d
    .prepare(
      `SELECT v.edition_id AS editionId, COUNT(*) AS n FROM morpheme m JOIN token t ON t.id = m.token_id
       JOIN verse v ON v.id = t.verse_id WHERE m.lemma = ? GROUP BY 1`,
    )
    .all(lemma) as { editionId: string; n: number }[];
  const occurrences = (
    d
      .prepare(
        `SELECT cv.id AS canonId, v.edition_id AS editionId, cv.book_id AS canonBook, b.name AS bookName,
                cv.chapter AS canonChapter, cv.verse AS canonVerse, t.surface, m.lemma, m.strongs_ext AS strongsExt
         FROM morpheme m JOIN token t ON t.id = m.token_id JOIN verse v ON v.id = t.verse_id
         JOIN verse_map vm ON vm.verse_id = v.id JOIN canon_verse cv ON cv.id = vm.canon_verse_id
         JOIN book b ON b.id = cv.book_id
         WHERE m.lemma = ? GROUP BY t.id ORDER BY b.ord, cv.chapter, cv.verse LIMIT 2000`,
      )
      .all(lemma) as Omit<StrongsOccurrence, "href">[]
  ).map((o) => ({ ...o, href: verseHref(o.canonId, o.canonBook, o.canonChapter, o.canonVerse) }));
  return { id: lemma, entries, counts, occurrences, equivalents: getEquivalents(`lemma:${lemma}`, "grk>heb", 8) };
}

// ---------------------------------------------------------------------------- sources
export function getSources() {
  return db()
    .prepare("SELECT id, title, url, version, license, attribution FROM source ORDER BY license, id")
    .all() as { id: string; title: string; url: string; version: string | null; license: string; attribution: string }[];
}
