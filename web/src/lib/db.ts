import "server-only";
import Database from "better-sqlite3";
import path from "node:path";

// bible.db is built by pipeline/build_bible.py. It is read-only at runtime.
const DB_PATH = process.env.BIBLE_DB ?? path.join(process.cwd(), "..", "db", "bible.db");

const globalForDb = globalThis as unknown as { bibleDb?: Database.Database };

export function db(): Database.Database {
  if (!globalForDb.bibleDb) {
    const conn = new Database(DB_PATH, { readonly: true, fileMustExist: true });
    conn.pragma("query_only = ON");
    globalForDb.bibleDb = conn;
  }
  return globalForDb.bibleDb;
}
