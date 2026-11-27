import "server-only";
import { db } from "@/lib/db";

// Commentaries (Tyndale Open Study Notes, unfoldingWord Translation Notes, Catena Aurea, Keil &
// Delitzsch). Entry bodies are safe HTML produced by the pipeline (a fixed set of tags, all text
// escaped; checked at build time), so they can be rendered as HTML.

export type CommentaryInfo = {
  id: string;
  title: string;
  shortTitle: string;
  author: string | null;
  written: string;
  tradition: string;
  description: string;
  license: string;
  attribution: string;
};

export type CommentaryEntry = {
  id: number;
  kind: "note" | "intro" | "article" | "profile";
  refLabel: string;
  title: string | null;
  label: string | null;
  quote: string | null;
  minor: boolean;
  body: string;
  /** token ids of the Hebrew/Greek words the note is about */
  words: number[];
};

export type CommentaryGroup = CommentaryInfo & { entries: CommentaryEntry[] };

const BOOK = 1_000_000;

export function getCommentaries(): CommentaryInfo[] {
  return db()
    .prepare(
      `SELECT c.id, c.title, c.short_title AS shortTitle, c.author, c.written, c.tradition, c.description,
              s.license, s.attribution
       FROM commentary c JOIN source s ON s.id = c.source_id ORDER BY c.sort`,
    )
    .all() as CommentaryInfo[];
}

type Row = Omit<CommentaryEntry, "minor" | "words"> & { commentaryId: string; minor: number; span: number };

function withWords(rows: Row[]): CommentaryEntry[] {
  const words = new Map<number, number[]>();
  const uw = rows.filter((r) => r.quote).map((r) => r.id);
  if (uw.length) {
    const stmt = db().prepare(`SELECT entry_id AS e, token_id AS t FROM commentary_word WHERE entry_id IN (${uw.map(() => "?").join(",")})`);
    for (const { e, t } of stmt.all(...uw) as { e: number; t: number }[]) (words.get(e) ?? words.set(e, []).get(e)!).push(t);
  }
  return rows.map((r) => ({
    id: r.id, kind: r.kind, refLabel: r.refLabel, title: r.title, label: r.label, quote: r.quote,
    minor: r.minor === 1, body: r.body, words: words.get(r.id) ?? [],
  }));
}

const KIND_ORDER = "CASE e.kind WHEN 'note' THEN 0 WHEN 'article' THEN 1 ELSE 2 END";

/** Everything the commentaries say about one Standard verse, grouped by commentary. */
export function getVerseCommentary(canonId: number): CommentaryGroup[] {
  const lo = Math.floor(canonId / BOOK) * BOOK;
  const rows = db()
    .prepare(
      `SELECT e.id, e.commentary_id AS commentaryId, e.kind, e.ref_label AS refLabel, e.title, e.label, e.quote,
              e.minor, e.body, MIN(r.end_canon - r.start_canon) AS span
       FROM commentary_ref r JOIN commentary_entry e ON e.id = r.entry_id
       WHERE r.start_canon BETWEEN @lo AND @v AND r.end_canon >= @v AND e.kind != 'intro'
       GROUP BY e.id
       ORDER BY ${KIND_ORDER}, span, e.sort`,
    )
    .all({ lo, v: canonId }) as Row[];
  const entries = withWords(rows);
  const byId = new Map(rows.map((r, i) => [r.id, { c: r.commentaryId, e: entries[i] }]));
  return getCommentaries()
    .map((c) => ({ ...c, entries: [...byId.values()].filter((x) => x.c === c.id).map((x) => x.e) }))
    .filter((g) => g.entries.length);
}

/** How many entries (not counting book introductions and translation-technique notes) cover each verse. */
export function countCommentary(canonIds: number[]): Map<number, number> {
  const counts = new Map<number, number>();
  const byBook = new Map<number, number[]>();
  for (const id of canonIds) (byBook.get(Math.floor(id / BOOK)) ?? byBook.set(Math.floor(id / BOOK), []).get(Math.floor(id / BOOK))!).push(id);
  const stmt = db().prepare(
    `SELECT r.start_canon AS a, r.end_canon AS b FROM commentary_ref r JOIN commentary_entry e ON e.id = r.entry_id
     WHERE r.start_canon BETWEEN @lo AND @hi AND r.end_canon >= @first AND e.kind != 'intro' AND e.minor = 0`,
  );
  for (const [book, ids] of byBook) {
    const first = Math.min(...ids), hi = Math.max(...ids);
    const spans = stmt.all({ lo: book * BOOK, hi, first }) as { a: number; b: number }[];
    for (const id of ids) counts.set(id, spans.filter((s) => s.a <= id && s.b >= id).length);
  }
  return counts;
}

/** unfoldingWord notes on a particular word. */
export function getWordNotes(tokenId: number): CommentaryEntry[] {
  const rows = db()
    .prepare(
      `SELECT e.id, e.commentary_id AS commentaryId, e.kind, e.ref_label AS refLabel, e.title, e.label, e.quote,
              e.minor, e.body, 0 AS span
       FROM commentary_word w JOIN commentary_entry e ON e.id = w.entry_id WHERE w.token_id = ? ORDER BY e.minor, e.sort`,
    )
    .all(tokenId) as Row[];
  return withWords(rows);
}

export type BookIntros = {
  intros: (CommentaryInfo & { entries: CommentaryEntry[] })[];
  /** Keil & Delitzsch keep their introduction with the comment on the book's first verse */
  kdIntroHref: string | null;
  articles: { id: number; kind: string; title: string; refLabel: string; href: string; commentary: string }[];
};

export function getBookIntros(book: string): BookIntros {
  const d = db();
  const rows = d
    .prepare(
      `SELECT e.id, e.commentary_id AS commentaryId, e.kind, e.ref_label AS refLabel, e.title, e.label, e.quote,
              e.minor, e.body, 0 AS span
       FROM commentary_entry e WHERE e.book_id = ? AND e.kind = 'intro' ORDER BY e.commentary_id, e.sort DESC`,
    )
    .all(book) as Row[];
  const entries = withWords(rows);
  const intros = getCommentaries()
    .map((c) => ({ ...c, entries: entries.filter((_, i) => rows[i].commentaryId === c.id) }))
    .filter((g) => g.entries.length);
  const kd = d
    .prepare(`SELECT 1 FROM commentary_entry WHERE book_id = ? AND commentary_id = 'kd' AND title IS NOT NULL LIMIT 1`)
    .get(book);
  const articles = (
    d
      .prepare(
        `SELECT e.id, e.kind, e.title, e.ref_label AS refLabel, c.short_title AS commentary, MIN(r.start_canon) AS start
         FROM commentary_entry e JOIN commentary c ON c.id = e.commentary_id JOIN commentary_ref r ON r.entry_id = e.id
         WHERE e.book_id = ? AND e.kind IN ('article', 'profile') GROUP BY e.id ORDER BY start`,
      )
      .all(book) as { id: number; kind: string; title: string; refLabel: string; commentary: string; start: number }[]
  ).map((a) => {
    const ch = Math.floor((a.start % BOOK) / 1000), v = a.start % 1000;
    return { ...a, href: `/read/${book}/${ch}#${book}-${ch}-${v}` };
  });
  return { intros, kdIntroHref: kd ? `/read/${book}/1#${book}-1-1` : null, articles };
}

export function hasBookIntro(book: string): boolean {
  return !!db().prepare("SELECT 1 FROM commentary_entry WHERE book_id = ? AND kind = 'intro' LIMIT 1").get(book);
}
