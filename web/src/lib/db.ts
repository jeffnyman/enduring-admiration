import "server-only";
import { DatabaseSync } from "node:sqlite";
import path from "node:path";

// bible.db is built by pipeline/build_bible.py. It is read-only at runtime.
// node:sqlite is built into Node (22.13+), so the app has no native module to compile per platform.
const DB_PATH = process.env.BIBLE_DB ?? path.join(process.cwd(), "..", "db", "bible.db");

const globalForDb = globalThis as unknown as { bibleDb?: DatabaseSync };

export function db(): DatabaseSync {
  if (!globalForDb.bibleDb) {
    const conn = new DatabaseSync(DB_PATH, { readOnly: true });
    conn.exec("PRAGMA query_only = ON");
    globalForDb.bibleDb = conn;
  }
  return globalForDb.bibleDb;
}
