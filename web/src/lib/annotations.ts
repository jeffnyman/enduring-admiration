"use client";

// Bookmarks and notes, keyed by Standard verse id, so a note follows the verse whichever edition
// or layout shows it.
//
// Two places they can live:
// - "file": the reader runs locally and the server has a notes file (BIBLE_NOTES, set by the
//   release launcher). The file is the source of truth; localStorage is a mirror for instant
//   first paint and to tell other tabs about changes.
// - "browser": no notes file (e.g. a hosted site): localStorage only, as before.
//
// Moving from browser to file: notes made in browser mode are merged into the file once (newer
// edit wins), then the mirror is marked as synced so a stale browser copy can't resurrect
// verses deleted elsewhere.
import { useSyncExternalStore } from "react";

export type Annotation = {
  /** readable reference, e.g. "Genesis 1:3" */
  ref: string;
  /** reader URL with the verse anchor */
  href: string;
  bookmarked: boolean;
  note: string;
  updated: string;
};

export type AnnotationMap = Record<string, Annotation>;

export type NotesStatus =
  | { mode: "loading" }
  | { mode: "browser" }
  | { mode: "file"; path: string; error?: string };

const KEY = "bible.annotations.v1";
const API = "/api/annotations";
const EMPTY: AnnotationMap = {};
const SAVE_DELAY = 400; // ms: batch keystrokes in a note into one save

type Mirror = { version: 1; items: AnnotationMap; synced?: boolean };

let items: AnnotationMap = EMPTY;
let status: NotesStatus = { mode: "loading" };
let started = false;
const listeners = new Set<() => void>();
const pending = new Map<string, ReturnType<typeof setTimeout>>();
// verses edited while a load from the notes file is in flight: its answer may predate them
const editedDuringLoad = new Set<string>();
let loading = false;

const emit = () => listeners.forEach((l) => l());

function readMirror(): Mirror {
  try {
    const raw = window.localStorage.getItem(KEY);
    const m = raw ? (JSON.parse(raw) as Partial<Mirror>) : null;
    return { version: 1, items: m?.items ?? {}, synced: m?.synced };
  } catch {
    return { version: 1, items: {} };
  }
}

function writeMirror(next: AnnotationMap, synced: boolean) {
  window.localStorage.setItem(KEY, JSON.stringify({ version: 1, items: next, ...(synced && { synced }) }));
}

function setItems(next: AnnotationMap) {
  items = next;
  emit();
}

function setStatus(next: NotesStatus) {
  status = next;
  emit();
}

async function call(body: unknown, keepalive = false): Promise<AnnotationMap> {
  const res = await fetch(API, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    keepalive,
  });
  const data = (await res.json().catch(() => ({}))) as { items?: AnnotationMap; error?: string };
  if (!res.ok || !data.items) throw new Error(data.error ?? `HTTP ${res.status}`);
  return data.items;
}

function failed(e: unknown) {
  // keep the change in the browser; the next load merges it into the file (newer wins)
  writeMirror(items, false);
  if (status.mode === "file") {
    setStatus({ ...status, error: `Couldn't save to the notes file (${(e as Error).message}). Your change is kept in this browser for now.` });
  }
}

/** Load from the server's notes file, if there is one. Edits made while it loads win over its
 *  answer and are then saved, so a quick bookmark right after the page opens isn't lost. */
async function load() {
  loading = true;
  editedDuringLoad.clear();
  try {
    await loadOnce();
  } finally {
    loading = false;
    editedDuringLoad.clear();
  }
}

async function loadOnce() {
  let data: { enabled?: boolean; path?: string; items?: AnnotationMap; error?: string };
  try {
    data = await (await fetch(API, { cache: "no-store" })).json();
  } catch {
    data = { enabled: false };
  }
  if (!data.enabled) {
    setStatus({ mode: "browser" });
    return;
  }
  const path = data.path ?? "";
  if (!data.items) {
    setStatus({ mode: "file", path, error: data.error ?? "Couldn't read the notes file." });
    return;
  }
  let next = data.items;
  const mirror = readMirror();
  if (!mirror.synced && Object.keys(mirror.items).length) {
    try {
      next = await call({ op: "merge", items: mirror.items, prefer: "newer" });
    } catch (e) {
      setStatus({ mode: "file", path, error: `Couldn't copy this browser's notes into the file (${(e as Error).message}).` });
      return;
    }
  }
  // keep what was edited meanwhile (and anything still waiting to be saved) over the file's answer
  const local = new Set([...editedDuringLoad, ...pending.keys()]);
  if (local.size) {
    next = { ...next };
    for (const id of local) {
      if (items[id]) next[id] = items[id];
      else delete next[id];
    }
  }
  writeMirror(next, true);
  setItems(next);
  setStatus({ mode: "file", path });
  for (const id of editedDuringLoad) if (!pending.has(id)) save(id);
}

function start() {
  if (started) return;
  started = true;
  items = readMirror().items;
  // other tabs write the mirror; pick their changes up
  window.addEventListener("storage", (e) => {
    if (e.key === KEY) setItems(readMirror().items);
  });
  // another browser may have changed the file meanwhile
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && status.mode === "file" && !pending.size) void load();
    if (document.visibilityState === "hidden") flush();
  });
  window.addEventListener("pagehide", flush);
  void load();
}

function subscribe(cb: () => void) {
  start();
  listeners.add(cb);
  return () => listeners.delete(cb);
}

export function useAnnotations(): AnnotationMap {
  return useSyncExternalStore(subscribe, () => items, () => EMPTY);
}

const loadingStatus: NotesStatus = { mode: "loading" };
export function useNotesStatus(): NotesStatus {
  return useSyncExternalStore(subscribe, () => status, () => loadingStatus);
}

function save(id: string, now = false) {
  const prev = pending.get(id);
  if (prev) clearTimeout(prev);
  const send = (keepalive: boolean) => {
    pending.delete(id);
    call({ op: "set", id, value: items[id] ?? null }, keepalive).then(() => {
      if (status.mode === "file" && status.error) setStatus({ mode: "file", path: status.path });
    }, failed);
  };
  if (now) send(true);
  else pending.set(id, setTimeout(() => send(false), SAVE_DELAY));
}

/** Send any batched saves right away (the page is closing or being hidden). */
function flush() {
  for (const id of [...pending.keys()]) save(id, true);
}

type Target = { id: number | string; ref: string; href: string };

function update(t: Target, change: Partial<Annotation>) {
  const id = String(t.id);
  const next = { ...items };
  const cur = next[id] ?? { ref: t.ref, href: t.href, bookmarked: false, note: "", updated: "" };
  const a = { ...cur, ref: t.ref, href: t.href, ...change, updated: new Date().toISOString() };
  if (!a.bookmarked && !a.note.trim()) delete next[id];
  else next[id] = a;
  writeMirror(next, status.mode === "file");
  setItems(next);
  if (loading) editedDuringLoad.add(id);
  if (status.mode === "file") save(id);
}

export function toggleBookmark(t: Target) {
  update(t, { bookmarked: !items[String(t.id)]?.bookmarked });
}

export function setNote(t: Target, note: string) {
  update(t, { note });
}

export function exportAnnotations(): string {
  return JSON.stringify({ version: 1, exported: new Date().toISOString(), items }, null, 2);
}

/** Merge an exported file into the current annotations (its entries win); returns how many verses it had. */
export async function importAnnotations(json: string): Promise<number> {
  const data = JSON.parse(json) as { items?: AnnotationMap };
  if (!data.items || typeof data.items !== "object") throw new Error("Not an annotations export");
  if (status.mode === "file") {
    const next = await call({ op: "merge", items: data.items, prefer: "incoming" });
    writeMirror(next, true);
    setItems(next);
  } else {
    const next = { ...items, ...data.items };
    writeMirror(next, false);
    setItems(next);
  }
  return Object.keys(data.items).length;
}

export async function clearAnnotations() {
  for (const t of pending.values()) clearTimeout(t);
  pending.clear();
  if (status.mode === "file") {
    const next = await call({ op: "clear" });
    writeMirror(next, true);
    setItems(next);
  } else {
    writeMirror({}, false);
    setItems({});
  }
}
