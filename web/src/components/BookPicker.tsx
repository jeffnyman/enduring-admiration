"use client";

import { useRouter } from "next/navigation";
import { useId, useSyncExternalStore } from "react";

export type PickerBook = {
  id: string;
  name: string;
  section: "OT" | "DC" | "NT";
  chapters: number;
  canon: { protestant: number; catholic: number; orthodox: number };
};

type Canon = "all" | "protestant" | "catholic" | "orthodox";
const CANON_LABEL: Record<Canon, string> = {
  all: "All books",
  protestant: "Protestant",
  catholic: "Catholic",
  orthodox: "Orthodox",
};
const SECTION_LABEL = { OT: "Old Testament", DC: "Deuterocanon / Apocrypha", NT: "New Testament" };

// The chosen canon lives in localStorage (an external store shared across tabs)
function subscribe(cb: () => void) {
  window.addEventListener("storage", cb);
  window.addEventListener("canon-change", cb);
  return () => {
    window.removeEventListener("storage", cb);
    window.removeEventListener("canon-change", cb);
  };
}
function readCanon(): Canon {
  const saved = window.localStorage.getItem("canon");
  return saved && saved in CANON_LABEL ? (saved as Canon) : "all";
}
function setCanon(c: Canon) {
  window.localStorage.setItem("canon", c);
  window.dispatchEvent(new Event("canon-change"));
}

export function BookPicker({ books, book, chapter }: { books: PickerBook[]; book: string; chapter: number }) {
  const router = useRouter();
  const canon = useSyncExternalStore(subscribe, readCanon, () => "all" as Canon);
  // Next keeps the previous page mounted (hidden) for instant back/forward, so ids must be unique
  const uid = useId();

  const visible = books.filter((b) => canon === "all" || b.canon[canon] > 0 || b.id === book);
  const current = books.find((b) => b.id === book);
  const go = (b: string, c: number) => router.push(`/read/${b}/${c}${window.location.search}`);

  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <label className="sr-only" htmlFor={`${uid}-book`}>Book</label>
      <select
        id={`${uid}-book`}
        value={book}
        onChange={(e) => go(e.target.value, 1)}
        className="rounded border border-stone-300 bg-white px-2 py-1 dark:border-stone-700 dark:bg-stone-900"
      >
        {(["OT", "DC", "NT"] as const).map((sec) => {
          const list = visible.filter((b) => b.section === sec);
          return list.length ? (
            <optgroup key={sec} label={SECTION_LABEL[sec]}>
              {list.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                  {canon !== "all" && b.canon[canon] === 2 ? " (appendix)" : ""}
                </option>
              ))}
            </optgroup>
          ) : null;
        })}
      </select>
      <label className="sr-only" htmlFor={`${uid}-chapter`}>Chapter</label>
      <select
        id={`${uid}-chapter`}
        value={chapter}
        onChange={(e) => go(book, Number(e.target.value))}
        className="rounded border border-stone-300 bg-white px-2 py-1 dark:border-stone-700 dark:bg-stone-900"
      >
        {Array.from({ length: current?.chapters ?? 1 }, (_, i) => i + 1).map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>
      <label className="sr-only" htmlFor={`${uid}-canon`}>Canon</label>
      <select
        id={`${uid}-canon`}
        value={canon}
        onChange={(e) => setCanon(e.target.value as Canon)}
        className="rounded border border-stone-300 bg-white px-2 py-1 text-stone-600 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-300"
        title="Which books to list"
      >
        {(Object.keys(CANON_LABEL) as Canon[]).map((c) => (
          <option key={c} value={c}>
            {CANON_LABEL[c]}
          </option>
        ))}
      </select>
    </div>
  );
}
