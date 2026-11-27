"use client";

// Bookmarks and notes, stored only in this browser (localStorage). Keyed by Standard verse id,
// so a note follows the verse whichever edition or layout shows it.
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

const KEY = "bible.annotations.v1";
const EVENT = "annotations-change";
const EMPTY: AnnotationMap = {};
let cache: { raw: string | null; value: AnnotationMap } = { raw: null, value: EMPTY };

function read(): AnnotationMap {
  const raw = window.localStorage.getItem(KEY);
  if (raw !== cache.raw) {
    try {
      const parsed = raw ? (JSON.parse(raw) as { items?: AnnotationMap }) : null;
      cache = { raw, value: parsed?.items ?? EMPTY };
    } catch {
      cache = { raw, value: EMPTY };
    }
  }
  return cache.value;
}

function write(items: AnnotationMap) {
  window.localStorage.setItem(KEY, JSON.stringify({ version: 1, items }));
  window.dispatchEvent(new Event(EVENT));
}

function subscribe(cb: () => void) {
  window.addEventListener("storage", cb);
  window.addEventListener(EVENT, cb);
  return () => {
    window.removeEventListener("storage", cb);
    window.removeEventListener(EVENT, cb);
  };
}

export function useAnnotations(): AnnotationMap {
  return useSyncExternalStore(subscribe, read, () => EMPTY);
}

type Target = { id: number | string; ref: string; href: string };

function update(t: Target, change: Partial<Annotation>) {
  const items = { ...read() };
  const cur = items[t.id] ?? { ref: t.ref, href: t.href, bookmarked: false, note: "", updated: "" };
  const next = { ...cur, ref: t.ref, href: t.href, ...change, updated: new Date().toISOString() };
  if (!next.bookmarked && !next.note.trim()) delete items[t.id];
  else items[t.id] = next;
  write(items);
}

export function toggleBookmark(t: Target) {
  update(t, { bookmarked: !read()[t.id]?.bookmarked });
}

export function setNote(t: Target, note: string) {
  update(t, { note });
}

export function exportAnnotations(): string {
  return JSON.stringify({ version: 1, exported: new Date().toISOString(), items: read() }, null, 2);
}

/** Merge an exported file into the current annotations; returns how many verses were imported. */
export function importAnnotations(json: string): number {
  const data = JSON.parse(json) as { items?: AnnotationMap };
  if (!data.items || typeof data.items !== "object") throw new Error("Not an annotations export");
  write({ ...read(), ...data.items });
  return Object.keys(data.items).length;
}

export function clearAnnotations() {
  write({});
}
