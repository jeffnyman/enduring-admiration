import type { NextRequest } from "next/server";
import { cleanAnnotation, notesPath, readNotes, validId, writeNotes, type StoredMap } from "@/lib/notesFile";

// Bookmarks and notes file API. Only active when BIBLE_NOTES is set (the local release), and then
// only for this computer: the Host must be localhost (blocks DNS rebinding), a browser Origin
// must be this reader's own, and writes must be JSON (so another site can't post a plain form).

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]"]);
const MAX_BODY = 5_000_000;

function refuse(req: NextRequest): Response | null {
  const host = req.headers.get("host") ?? "";
  const hostname = host.startsWith("[") ? host.slice(0, host.indexOf("]") + 1) : host.split(":")[0];
  if (!LOCAL_HOSTS.has(hostname)) return Response.json({ error: "notes file is only served to this computer" }, { status: 403 });
  const origin = req.headers.get("origin");
  if (origin && origin !== `http://${host}`) return Response.json({ error: "cross-origin request" }, { status: 403 });
  return null;
}

export async function GET(req: NextRequest) {
  const file = notesPath();
  if (!file) return Response.json({ enabled: false });
  const denied = refuse(req);
  if (denied) return denied;
  try {
    return Response.json({ enabled: true, path: file, items: readNotes(file) });
  } catch (e) {
    return Response.json({ enabled: true, path: file, error: `Could not read the notes file: ${(e as Error).message}` }, { status: 500 });
  }
}

type Op =
  | { op: "set"; id: string; value: unknown }
  | { op: "merge"; items: Record<string, unknown>; prefer: "newer" | "incoming" }
  | { op: "clear" };

export async function POST(req: NextRequest) {
  const file = notesPath();
  if (!file) return Response.json({ error: "notes are kept in the browser" }, { status: 404 });
  const denied = refuse(req);
  if (denied) return denied;
  if (!req.headers.get("content-type")?.startsWith("application/json")) {
    return Response.json({ error: "expected JSON" }, { status: 415 });
  }
  const text = await req.text();
  if (text.length > MAX_BODY) return Response.json({ error: "too large" }, { status: 413 });
  let op: Op;
  try {
    op = JSON.parse(text) as Op;
  } catch {
    return Response.json({ error: "bad JSON" }, { status: 400 });
  }

  let items: StoredMap;
  try {
    items = readNotes(file);
  } catch (e) {
    // never overwrite a file we couldn't read
    return Response.json({ error: `Could not read the notes file: ${(e as Error).message}` }, { status: 500 });
  }
  if (op?.op === "set" && typeof op.id === "string" && validId(op.id)) {
    const a = op.value === null ? null : cleanAnnotation(op.value);
    if (op.value !== null && !a) return Response.json({ error: "bad annotation" }, { status: 400 });
    if (a && (a.bookmarked || a.note.trim())) items[op.id] = a;
    else delete items[op.id];
  } else if (op?.op === "merge" && op.items && typeof op.items === "object") {
    for (const [id, v] of Object.entries(op.items)) {
      const a = cleanAnnotation(v);
      if (!validId(id) || !a) continue;
      const cur = items[id];
      if (!cur || op.prefer === "incoming" || a.updated > cur.updated) items[id] = a;
    }
  } else if (op?.op === "clear") {
    items = {};
  } else {
    return Response.json({ error: "unknown operation" }, { status: 400 });
  }
  try {
    writeNotes(file, items);
  } catch (e) {
    return Response.json({ error: `Could not save the notes file: ${(e as Error).message}` }, { status: 500 });
  }
  return Response.json({ items });
}
