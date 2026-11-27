"use client";

import { toggleBookmark, useAnnotations } from "@/lib/annotations";

type Props = { canonId: number; refLabel: string; href: string; xrefs: number; comments: number };

/** Bookmark, note, cross-reference and commentary buttons under a verse number. */
export function VerseTools({ canonId, refLabel, href, xrefs, comments }: Props) {
  const a = useAnnotations()[canonId];
  const target = { id: canonId, ref: refLabel, href };
  const btn = "rounded px-0.5 leading-none hover:bg-stone-200 dark:hover:bg-stone-800";
  return (
    <span className="mt-1 flex flex-col items-start gap-0.5 font-sans text-[0.7rem] text-stone-400">
      <button
        type="button"
        className={`${btn} ${a?.bookmarked ? "text-amber-600" : ""}`}
        aria-pressed={!!a?.bookmarked}
        aria-label={`Bookmark ${refLabel}`}
        title="Bookmark (b)"
        onClick={() => toggleBookmark(target)}
      >
        {a?.bookmarked ? "★" : "☆"}
      </button>
      <button
        type="button"
        className={`${btn} ${a?.note ? "text-sky-700 dark:text-sky-300" : ""}`}
        aria-label={`Note on ${refLabel}`}
        title="Note (e)"
        data-note={canonId}
        data-ref={refLabel}
        data-href={href}
      >
        ✎
      </button>
      {comments > 0 && (
        <button type="button" className={btn} aria-label={`Commentary on ${refLabel}`} title="Commentary (c)"
          data-commentary={canonId}>
          ¶
        </button>
      )}
      {xrefs > 0 && (
        <button type="button" className={btn} aria-label={`${xrefs} cross-references for ${refLabel}`} title="Cross-references (x)"
          data-xref={canonId}>
          ↗{xrefs > 99 ? "99+" : xrefs}
        </button>
      )}
    </span>
  );
}

/** The verse's note, shown under the verse across all columns. */
export function VerseNote({ canonId }: { canonId: number }) {
  const a = useAnnotations()[canonId];
  if (!a?.note?.trim()) return null;
  return (
    <div className="col-span-full whitespace-pre-line rounded bg-sky-50 px-3 py-1.5 font-sans text-sm text-sky-950 md:ms-[3rem] dark:bg-sky-950 dark:text-sky-100">
      {a.note}
    </div>
  );
}
