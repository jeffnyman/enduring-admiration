import "server-only";
import fs from "node:fs";
import path from "node:path";

// Bookmarks and notes saved in a JSON file on this computer, when BIBLE_NOTES names one (the
// release launcher sets it to a per-user folder). Without it the reader keeps them in the
// browser only. Keyed by Standard verse id, like the browser store.

export type StoredAnnotation = { ref: string; href: string; bookmarked: boolean; note: string; updated: string };
export type StoredMap = Record<string, StoredAnnotation>;

export function notesPath(): string | null {
  const p = process.env.BIBLE_NOTES?.trim();
  return p ? path.resolve(p) : null;
}

/** A well-formed annotation, or null. Guards the file against malformed requests. */
export function cleanAnnotation(v: unknown): StoredAnnotation | null {
  if (!v || typeof v !== "object") return null;
  const a = v as Record<string, unknown>;
  const str = (x: unknown, max: number) => (typeof x === "string" && x.length <= max ? x : null);
  const ref = str(a.ref, 200), href = str(a.href, 500), note = str(a.note, 50_000), updated = str(a.updated, 40);
  if (ref === null || href === null || note === null || updated === null || typeof a.bookmarked !== "boolean") return null;
  if (!href.startsWith("/")) return null;
  return { ref, href, bookmarked: a.bookmarked, note, updated };
}

export const validId = (id: string) => /^\d{1,10}$/.test(id);

export function readNotes(file: string): StoredMap {
  let raw: string;
  try {
    raw = fs.readFileSync(file, "utf8");
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return {};
    throw e;
  }
  const data = JSON.parse(raw) as { items?: Record<string, unknown> };
  const items: StoredMap = {};
  for (const [id, v] of Object.entries(data.items ?? {})) {
    const a = cleanAnnotation(v);
    if (validId(id) && a) items[id] = a;
  }
  return items;
}

/** Write atomically (temp file + rename), keeping the previous version as <file>.bak. */
export function writeNotes(file: string, items: StoredMap) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify({ version: 1, saved: new Date().toISOString(), items }, null, 2));
  if (fs.existsSync(file)) fs.copyFileSync(file, `${file}.bak`);
  fs.renameSync(tmp, file);
}
