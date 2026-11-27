"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import {
  clearAnnotations,
  exportAnnotations,
  importAnnotations,
  setNote,
  toggleBookmark,
  useAnnotations,
} from "@/lib/annotations";

type Filter = "all" | "bookmarks" | "notes";

export function BookmarkList() {
  const items = useAnnotations();
  const [filter, setFilter] = useState<Filter>("all");
  const [message, setMessage] = useState("");
  const file = useRef<HTMLInputElement>(null);

  // Standard verse ids sort in Bible order (book order, chapter, verse)
  const rows = Object.entries(items)
    .filter(([, a]) => filter === "all" || (filter === "bookmarks" ? a.bookmarked : a.note.trim()))
    .sort(([a], [b]) => Number(a) - Number(b));

  const download = () => {
    const blob = new Blob([exportAnnotations()], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `bible-notes-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const upload = async (f: File) => {
    try {
      setMessage(`Imported ${importAnnotations(await f.text())} verses.`);
    } catch (e) {
      setMessage(`Could not import: ${(e as Error).message}`);
    }
  };

  const btn = "rounded border border-stone-300 px-2.5 py-1 hover:bg-stone-100 dark:border-stone-700 dark:hover:bg-stone-800";
  return (
    <div className="max-w-3xl">
      <div className="mb-4 flex flex-wrap items-center gap-2 text-sm">
        {(["all", "bookmarks", "notes"] as Filter[]).map((f) => (
          <button key={f} onClick={() => setFilter(f)} aria-pressed={filter === f}
            className={`${btn} ${filter === f ? "bg-stone-200 dark:bg-stone-800" : ""}`}>
            {f[0].toUpperCase() + f.slice(1)}
          </button>
        ))}
        <span className="mx-2 h-5 w-px bg-stone-300 dark:bg-stone-700" />
        <button onClick={download} className={btn} disabled={!Object.keys(items).length}>Export</button>
        <button onClick={() => file.current?.click()} className={btn}>Import</button>
        <input ref={file} type="file" accept="application/json" className="hidden" aria-label="Import file"
          onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
        {Object.keys(items).length > 0 && (
          <button
            onClick={() => window.confirm("Delete all bookmarks and notes in this browser?") && clearAnnotations()}
            className={`${btn} text-red-700 dark:text-red-400`}
          >
            Clear all
          </button>
        )}
      </div>
      {message && <p className="mb-3 text-sm text-stone-600" role="status">{message}</p>}
      {!rows.length && (
        <p className="text-stone-500">
          Nothing here yet. Use ☆ (bookmark) and ✎ (note) beside a verse number, or the keys b and e.
        </p>
      )}
      <ul className="space-y-3">
        {rows.map(([id, a]) => (
          <li key={id} className="border-b border-stone-200 pb-3 dark:border-stone-800">
            <div className="flex items-baseline gap-2">
              <Link href={a.href} className="font-semibold text-amber-800 hover:underline dark:text-amber-300">
                {a.ref}
              </Link>
              <button
                onClick={() => toggleBookmark({ id, ref: a.ref, href: a.href })}
                aria-pressed={a.bookmarked}
                aria-label={`Bookmark ${a.ref}`}
                className={a.bookmarked ? "text-amber-600" : "text-stone-400"}
              >
                {a.bookmarked ? "★" : "☆"}
              </button>
              <span className="ms-auto text-xs text-stone-400">{new Date(a.updated).toLocaleDateString()}</span>
            </div>
            {a.note && (
              <div className="mt-1 flex items-start gap-2">
                <p className="flex-1 whitespace-pre-line text-sm">{a.note}</p>
                <button onClick={() => setNote({ id, ref: a.ref, href: a.href }, "")} className="text-xs text-stone-400 hover:text-red-700">
                  delete note
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
      <p className="mt-6 text-xs text-stone-500">
        Bookmarks and notes are stored only in this browser. Export them to keep a copy or move them to another device.
      </p>
    </div>
  );
}
