import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { BookPicker, type PickerBook } from "@/components/BookPicker";
import { VerseCell } from "@/components/VerseCell";
import { WordDrawer } from "@/components/WordDrawer";
import { defaultColumns, getBook, getBooks, getChapter, getEditions, neighbours } from "@/lib/bible";

const ALL_COLUMNS = ["WEB", "WLC", "LXX-SWETE", "LXX-BRENTON", "SBLGNT"];
const SHORT: Record<string, string> = {
  WEB: "English (WEB)",
  WLC: "Hebrew (WLC)",
  "LXX-SWETE": "Septuagint (Swete)",
  "LXX-BRENTON": "Septuagint (Brenton)",
  SBLGNT: "Greek NT (SBLGNT)",
};

export default function Page(props: PageProps<"/read/[book]/[chapter]">) {
  return (
    <Suspense fallback={<div className="animate-pulse text-stone-400">Loading chapter…</div>}>
      <Chapter params={props.params} searchParams={props.searchParams} />
    </Suspense>
  );
}

async function Chapter({
  params,
  searchParams,
}: {
  params: PageProps<"/read/[book]/[chapter]">["params"];
  searchParams: PageProps<"/read/[book]/[chapter]">["searchParams"];
}) {
  const { book: rawBook, chapter: rawChapter } = await params;
  const sp = await searchParams;
  const bookId = rawBook.toUpperCase();
  const chapter = Number(rawChapter);
  const book = getBook(bookId);
  if (!book || !Number.isInteger(chapter) || chapter < 1 || chapter > book.chapters) notFound();

  const requested = typeof sp.cols === "string" ? sp.cols.split(",").filter((c) => ALL_COLUMNS.includes(c)) : null;
  const columns = requested?.length ? requested : defaultColumns(book.section);
  const editions = Object.fromEntries(getEditions().map((e) => [e.id, e]));
  const rows = getChapter(bookId, chapter, columns);
  const { prev, next } = neighbours(bookId, chapter);
  // The WEB prints a Psalm title as a heading before verse 1; Standard numbering gives
  // titles their own row (verse 0), so show it there.
  const hasTitleRow = rows[0]?.verse === 0;
  const webTitle = hasTitleRow ? rows.find((r) => r.verse === 1)?.editions.WEB?.[0]?.heading ?? null : null;
  const qs = requested ? `?cols=${columns.join(",")}` : "";

  const pickerBooks: PickerBook[] = getBooks().map((b) => ({
    id: b.id,
    name: b.name,
    section: b.section,
    chapters: b.chapters,
    canon: { protestant: b.canon_protestant, catholic: b.canon_catholic, orthodox: b.canon_orthodox },
  }));

  const toggle = (id: string) => {
    const set = columns.includes(id) ? columns.filter((c) => c !== id) : [...columns, id];
    const ordered = ALL_COLUMNS.filter((c) => set.includes(c));
    return ordered.length ? `/read/${bookId}/${chapter}?cols=${ordered.join(",")}` : `/read/${bookId}/${chapter}`;
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          {prev && (
            <Link href={`/read/${prev.book}/${prev.chapter}${qs}`} className="rounded px-2 py-1 hover:bg-stone-200 dark:hover:bg-stone-800" aria-label="Previous chapter">
              ←
            </Link>
          )}
          <h1 className="text-2xl font-semibold tracking-tight">
            {book.name} {chapter}
          </h1>
          {next && (
            <Link href={`/read/${next.book}/${next.chapter}${qs}`} className="rounded px-2 py-1 hover:bg-stone-200 dark:hover:bg-stone-800" aria-label="Next chapter">
              →
            </Link>
          )}
        </div>
        <BookPicker books={pickerBooks} book={bookId} chapter={chapter} />
      </div>

      <div className="mb-4 flex flex-wrap gap-2 text-xs" aria-label="Columns">
        {ALL_COLUMNS.map((id) => (
          <Link
            key={id}
            href={toggle(id)}
            className={`rounded-full border px-2.5 py-0.5 ${
              columns.includes(id)
                ? "border-amber-700 bg-amber-100 text-amber-900 dark:bg-amber-900 dark:text-amber-100"
                : "border-stone-300 text-stone-500 dark:border-stone-700"
            }`}
            aria-pressed={columns.includes(id)}
          >
            {SHORT[id]}
          </Link>
        ))}
        <span className="self-center text-stone-400">Click a Hebrew or Greek word for its lexicon entry.</span>
      </div>

      <WordDrawer>
        <div
          className="hidden gap-6 border-b border-stone-300 pb-2 text-xs font-semibold uppercase tracking-wide text-stone-500 md:grid md:grid-cols-[2.5rem_repeat(var(--cols),minmax(0,1fr))] dark:border-stone-700"
          style={{ "--cols": columns.length } as React.CSSProperties}
        >
          <span />
          {columns.map((c) => (
            <span key={c} dir={editions[c]?.direction} className={editions[c]?.direction === "rtl" ? "text-right" : ""}>
              {SHORT[c]}
            </span>
          ))}
        </div>
        {rows.map((r) => (
          <div
            key={r.canonId}
            id={`${bookId}-${chapter}-${r.verse}`}
            className="verse-row grid scroll-mt-20 gap-x-6 gap-y-1 border-b border-stone-100 py-3 md:grid-cols-[2.5rem_repeat(var(--cols),minmax(0,1fr))] dark:border-stone-900"
            style={{ "--cols": columns.length } as React.CSSProperties}
          >
            <a href={`#${bookId}-${chapter}-${r.verse}`} className="pt-1 font-sans text-xs text-stone-400 hover:text-stone-700">
              {r.verse === 0 ? "title" : r.verse}
            </a>
            {columns.map((c) => (
              <div key={c}>
                <div className="mb-0.5 font-sans text-[0.65rem] uppercase text-stone-400 md:hidden">{SHORT[c]}</div>
                <VerseCell
                  editionId={c}
                  verses={r.editions[c]}
                  canonBook={bookId}
                  canonChapter={chapter}
                  canonVerse={r.verse}
                  lang={editions[c]?.language ?? "en"}
                  dir={editions[c]?.direction ?? "ltr"}
                  title={c === "WEB" && r.verse === 0 ? webTitle : null}
                  hideHeading={c === "WEB" && r.verse === 1 && !!webTitle}
                />
              </div>
            ))}
          </div>
        ))}
      </WordDrawer>

      <div className="mt-6 flex justify-between text-sm">
        {prev ? <Link href={`/read/${prev.book}/${prev.chapter}${qs}`} className="hover:underline">← Previous</Link> : <span />}
        {next ? <Link href={`/read/${next.book}/${next.chapter}${qs}`} className="hover:underline">Next →</Link> : <span />}
      </div>
    </div>
  );
}
