import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { BookPicker, type PickerBook } from "@/components/BookPicker";
import { VerseCell } from "@/components/VerseCell";
import { ReaderKeys } from "@/components/ReaderKeys";
import { StudyPanel } from "@/components/StudyPanel";
import { VerseNote, VerseTools } from "@/components/VerseTools";
import { defaultColumns, getBook, getBooks, getChapter, getEditions, neighbours } from "@/lib/bible";

const ALL_COLUMNS = ["WEB", "WLC", "LXX-SWETE", "LXX-SWETE-OG", "LXX-BRENTON", "SBLGNT"];
// the Old Greek column only exists for Daniel and its additions
const OLD_GREEK_BOOKS = ["DAN", "DAG", "S3Y", "SUS", "BEL"];
// Short names for a row's Standard reference when a layout renumbers it
const STD_ABBR: Record<string, string> = {
  DAN: "Dan", S3Y: "Pr Azar", SUS: "Sus", BEL: "Bel", EST: "Esth", ESG: "Add Esth",
};

const SHORT: Record<string, string> = {
  WEB: "English (WEB)",
  WLC: "Hebrew (WLC)",
  "LXX-SWETE": "Septuagint (Swete)",
  "LXX-SWETE-OG": "Old Greek Daniel",
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

  const available = ALL_COLUMNS.filter((c) => c !== "LXX-SWETE-OG" || OLD_GREEK_BOOKS.includes(bookId));
  const requested = typeof sp.cols === "string" ? sp.cols.split(",").filter((c) => available.includes(c)) : null;
  const columns = requested?.length ? requested : defaultColumns(book);
  const layout = book.layout;
  const title = layout ? book.name.replace(/\s*\(Greek\)\s*/, "") : book.name;
  const editions = Object.fromEntries(getEditions().map((e) => [e.id, e]));
  const rows = getChapter(bookId, chapter, columns);
  const { prev, next } = neighbours(bookId, chapter);
  // The WEB prints a Psalm title as a heading before verse 1; Standard numbering gives
  // titles their own row (verse 0), so show it there.
  const hasTitleRow = !layout && rows[0]?.verse === 0;
  const webTitle = hasTitleRow ? rows.find((r) => r.verse === 1)?.editions.WEB?.[0]?.heading ?? null : null;
  const glosses = sp.gloss === "1";
  const params_ = new URLSearchParams();
  if (requested) params_.set("cols", columns.join(","));
  if (glosses) params_.set("gloss", "1");
  const qs = params_.size ? `?${params_.toString().replace(/%2C/g, ",")}` : "";

  const allBooks = getBooks();
  const replacedBy = new Map<string, string>();
  for (const b of allBooks) for (const r of b.layout?.replaces ?? []) if (r !== b.id) replacedBy.set(r, b.id);
  const pickerBooks: PickerBook[] = allBooks.map((b) => {
    // in Catholic/Orthodox lists a layout book takes the place of the first book it replaces
    const first = b.layout ? allBooks.find((x) => x.id === b.layout!.replaces[0]) : undefined;
    return {
      id: b.id,
      name: b.name,
      section: b.section,
      chapters: b.chapters,
      canon: { protestant: b.canon_protestant, catholic: b.canon_catholic, orthodox: b.canon_orthodox },
      replacedBy: replacedBy.get(b.id),
      layout: first ? { name: b.name.replace(/\s*\(Greek\)\s*/, ""), section: first.section, ord: first.ord } : undefined,
      ord: b.ord,
    };
  });

  const href = (cols: string[] | null, gloss: boolean) => {
    const p = [cols?.length ? `cols=${cols.join(",")}` : "", gloss ? "gloss=1" : ""].filter(Boolean).join("&");
    return `/read/${bookId}/${chapter}${p ? `?${p}` : ""}`;
  };
  const toggle = (id: string) => {
    const set = columns.includes(id) ? columns.filter((c) => c !== id) : [...columns, id];
    return href(available.filter((c) => set.includes(c)), glosses);
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
            {title} {chapter}
          </h1>
          {next && (
            <Link href={`/read/${next.book}/${next.chapter}${qs}`} className="rounded px-2 py-1 hover:bg-stone-200 dark:hover:bg-stone-800" aria-label="Next chapter">
              →
            </Link>
          )}
        </div>
        <BookPicker books={pickerBooks} book={bookId} chapter={chapter} />
      </div>

      {layout && (
        <p className="mb-3 max-w-3xl text-sm text-stone-600 dark:text-stone-400">
          {layout.description} Small references under a verse number give the Standard (NRSV) numbering.
        </p>
      )}
      <div className="mb-4 flex flex-wrap gap-2 text-xs" aria-label="Columns">
        {available.map((id) => (
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
        <Link
          href={href(requested ? columns : null, !glosses)}
          className={`rounded-full border px-2.5 py-0.5 ${
            glosses
              ? "border-sky-700 bg-sky-100 text-sky-900 dark:bg-sky-900 dark:text-sky-100"
              : "border-stone-300 text-stone-500 dark:border-stone-700"
          }`}
          aria-pressed={glosses}
          title="English gloss under each Hebrew and Greek word (Septuagint glosses, in italics, are dictionary glosses)"
        >
          Glosses
        </Link>
        <span className="self-center text-stone-400">Click a Hebrew or Greek word for its lexicon entry.</span>
        <span className="self-center">
          <ReaderKeys
            prevHref={prev ? `/read/${prev.book}/${prev.chapter}${qs}` : undefined}
            nextHref={next ? `/read/${next.book}/${next.chapter}${qs}` : undefined}
            glossHref={href(requested ? columns : null, !glosses)}
          />
        </span>
      </div>

      <StudyPanel>
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
            id={r.anchor}
            tabIndex={-1}
            className="verse-row grid scroll-mt-20 gap-x-6 gap-y-1 border-b border-stone-100 py-3 md:grid-cols-[2.5rem_repeat(var(--cols),minmax(0,1fr))] dark:border-stone-900"
            style={{ "--cols": columns.length } as React.CSSProperties}
          >
            <div>
            <a href={`#${r.anchor}`} className="pt-1 font-sans text-xs text-stone-400 hover:text-stone-700">
              {!layout && r.verse === 0 ? "title" : r.label}
              {layout &&
                (![bookId, layout.replaces[0]].includes(r.canonBook) || r.canonChapter !== chapter || r.label !== String(r.verse)) && (
                <span className="block text-[0.6rem] leading-tight text-stone-400" title="Standard (NRSV) reference">
                  {STD_ABBR[r.canonBook] ?? r.canonBook} {r.canonChapter}:{r.verse}
                </span>
              )}
            </a>
            <VerseTools
              canonId={r.canonId}
              refLabel={`${title} ${chapter}:${!layout && r.verse === 0 ? "title" : r.label}`}
              href={`/read/${bookId}/${chapter}#${r.anchor}`}
              xrefs={r.xrefs}
            />
            </div>
            {columns.map((c) => (
              <div key={c}>
                <div className="mb-0.5 font-sans text-[0.65rem] uppercase text-stone-400 md:hidden">{SHORT[c]}</div>
                <VerseCell
                  editionId={c}
                  verses={r.editions[c]}
                  canonBook={r.canonBook}
                  canonChapter={r.canonChapter}
                  canonVerse={r.verse}
                  preferBook={layout ? bookId : r.canonBook}
                  expect={layout ? { book: bookId, chapter, label: r.label } : undefined}
                  glosses={glosses}
                  lang={editions[c]?.language ?? "en"}
                  dir={editions[c]?.direction ?? "ltr"}
                  title={c === "WEB" && r.verse === 0 ? webTitle : null}
                  hideHeading={c === "WEB" && r.verse === 1 && !!webTitle}
                />
              </div>
            ))}
            <VerseNote canonId={r.canonId} />
          </div>
        ))}
      </StudyPanel>

      <div className="mt-6 flex justify-between text-sm">
        {prev ? <Link href={`/read/${prev.book}/${prev.chapter}${qs}`} className="hover:underline">← Previous</Link> : <span />}
        {next ? <Link href={`/read/${next.book}/${next.chapter}${qs}`} className="hover:underline">Next →</Link> : <span />}
      </div>
    </div>
  );
}
