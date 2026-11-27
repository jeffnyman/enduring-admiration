import type { EditionVerse, Token } from "@/lib/bible";

type Run = { t?: string; wj?: number; para?: string };

function EnglishText({ v }: { v: EditionVerse }) {
  let runs: Run[] = [];
  try {
    runs = v.richJson ? (JSON.parse(v.richJson) as Run[]) : [];
  } catch {
    runs = [];
  }
  if (!runs.length) return <>{v.text}</>;
  return (
    <>
      {runs.map((r, i) =>
        r.para ? (
          r.para.startsWith("q") ? <br key={i} /> : <span key={i}> </span>
        ) : (
          <span key={i} className={r.wj ? "wj" : undefined}>
            {r.t}
          </span>
        ),
      )}
    </>
  );
}

const cleanGloss = (g: string) => g.replace(/[\s,.;:·]+$/, "").trim();

function TokenSpan({ t, showGloss }: { t: Token; showGloss: boolean }) {
  const variantTitle = t.variant === "ketiv" ? "Ketiv (as written)" : t.variant === "qere" ? "Qere (as read)" : undefined;
  const cls = [
    t.tagged ? "tok" : "tok tok-untagged",
    t.variant === "ketiv" ? "opacity-60" : "",
    t.variant === "qere" ? "text-[0.8em] text-amber-800 dark:text-amber-300" : "",
  ].join(" ");
  const inner = t.tagged ? (
    <span className={cls} data-tok={t.id} role="button" tabIndex={0} title={variantTitle} aria-pressed="false">
      {t.surface}
    </span>
  ) : (
    <span className={cls} title={variantTitle}>{t.surface}</span>
  );
  const word = t.variant === "qere" ? <>[{inner}]</> : inner;
  return (
    <>
      {t.leading}
      {showGloss && t.gloss ? (
        <>
          <ruby className="gl">
            {word}
            {/* keep joined punctuation (maqaf, sof pasuq, commas) with its word */}
            {/\s/.test(t.trailing) ? null : t.trailing}
            <rt className={t.glossKind === "lexical" ? "gl-lex" : undefined}>{cleanGloss(t.gloss)}</rt>
          </ruby>
          {/\s/.test(t.trailing) ? t.trailing : null}
        </>
      ) : (
        <>
          {word}
          {t.trailing}
        </>
      )}
    </>
  );
}

type Expect = { book: string; chapter: number; label: string };

function nativeLabel(v: EditionVerse, canonBook: string, canonChapter: number, canonVerse: number, expect?: Expect) {
  if (v.sourceRef) return v.sourceRef;
  if (v.bookId === canonBook && v.chapter === canonChapter && v.verse === canonVerse && !v.part) return null;
  // in a layout, an edition that numbers the verse like the layout needs no label
  if (expect && v.bookId === expect.book && v.chapter === expect.chapter && `${v.verse}${v.part}` === expect.label) return null;
  return `${v.bookId === canonBook ? "" : v.bookId + " "}${v.chapter}:${v.verse}${v.part}`;
}

export function VerseCell({
  editionId,
  verses,
  canonBook,
  canonChapter,
  canonVerse,
  lang,
  dir,
  title,
  hideHeading = false,
  preferBook,
  expect,
  glosses = false,
}: {
  editionId: string;
  verses: EditionVerse[] | undefined;
  canonBook: string;
  canonChapter: number;
  canonVerse: number;
  lang: string;
  dir: "ltr" | "rtl";
  /** heading to show in place of text (WEB Psalm title on the Standard "title" row) */
  title?: string | null;
  hideHeading?: boolean;
  /** English: show the WEB verse from this book first (Greek Daniel/Esther in their layouts) */
  preferBook?: string;
  expect?: Expect;
  /** show the gloss line under Hebrew and Greek words */
  glosses?: boolean;
}) {
  const cls = lang === "hbo" ? "scripture-he" : lang === "grc" ? "scripture-grc" : "scripture-en";
  if (!verses?.length) {
    return title ? (
      <div lang={lang} className={`${cls} italic text-stone-600 dark:text-stone-400`}>{title}</div>
    ) : (
      <div className="text-stone-300 dark:text-stone-700" aria-hidden>—</div>
    );
  }

  // English: the WEB verse from the preferred book first (the canonical book, or in a layout the
  // Greek-text translation), others after
  // The WEB translates Daniel and Esther twice (from the Hebrew and from the Greek); show the one
  // that matches this view, or every candidate if neither matches
  const first = preferBook ?? canonBook;
  const preferred = verses.filter((v) => v.bookId === first);
  const ordered = editionId === "WEB" && preferred.length ? preferred : verses;

  return (
    <div lang={lang} dir={dir} className={`${cls}${glosses ? " with-gloss" : ""}`}>
      {ordered.map((v, i) => {
        const label = nativeLabel(v, canonBook, canonChapter, canonVerse, expect);
        const loose = v.relation === "partial" || v.relation === "merged";
        const secondary = editionId === "WEB" && i > 0;
        return (
          <div key={`${v.verseId}-${i}`} className={secondary ? "mt-1 text-[0.9em] text-stone-500" : undefined}>
            {(label || loose) && (
              <span
                dir="ltr"
                className="me-1 align-super font-sans text-[0.65rem] text-stone-500"
                title={[v.relation !== "identical" ? `Mapping: ${v.relation}` : "", v.rule ?? "", v.note ?? ""]
                  .filter(Boolean)
                  .join(" · ")}
              >
                {label}
                {loose ? " ≈" : ""}
              </span>
            )}
            {editionId === "WEB" && v.heading && !hideHeading && !v.continued && (
              <div className="mb-0.5 text-[0.9em] italic text-stone-600 dark:text-stone-400">{v.heading}</div>
            )}
            {secondary && (
              <span className="me-1 font-sans text-[0.7rem]">
                ({{ DAG: "Greek Daniel", ESG: "Greek Esther", DAN: "Hebrew-text Daniel", EST: "Hebrew-text Esther" }[v.bookId] ?? v.bookId})
              </span>
            )}
            {v.continued ? (
              <span className="font-sans text-xs italic text-stone-400">(text shown with the verse above)</span>
            ) : v.tokens.length ? (
              v.tokens.map((t) => <TokenSpan key={t.id} t={t} showGloss={glosses} />)
            ) : editionId === "WEB" ? (
              <EnglishText v={v} />
            ) : (
              v.text
            )}
            {v.notes.length > 0 && !v.continued && (
              <sup className="ms-0.5 cursor-help font-sans text-[0.65rem] text-amber-700" title={v.notes.join("\n\n")}>
                †
              </sup>
            )}
          </div>
        );
      })}
    </div>
  );
}
