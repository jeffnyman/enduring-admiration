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

function TokenSpan({ t }: { t: Token }) {
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
  return (
    <>
      {t.leading}
      {t.variant === "qere" ? <>[{inner}]</> : inner}
      {t.trailing}
    </>
  );
}

function nativeLabel(v: EditionVerse, canonBook: string, canonChapter: number, canonVerse: number) {
  if (v.sourceRef) return v.sourceRef;
  if (v.bookId === canonBook && v.chapter === canonChapter && v.verse === canonVerse && !v.part) return null;
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
}) {
  const cls = lang === "hbo" ? "scripture-he" : lang === "grc" ? "scripture-grc" : "scripture-en";
  if (!verses?.length) {
    return title ? (
      <div lang={lang} className={`${cls} italic text-stone-600 dark:text-stone-400`}>{title}</div>
    ) : (
      <div className="text-stone-300 dark:text-stone-700" aria-hidden>—</div>
    );
  }

  // English: the WEB verse from the canonical book first (e.g. Hebrew-text Daniel), others after
  const ordered =
    editionId === "WEB"
      ? [...verses].sort((a, b) => Number(b.bookId === canonBook) - Number(a.bookId === canonBook))
      : verses;

  return (
    <div lang={lang} dir={dir} className={cls}>
      {ordered.map((v, i) => {
        const label = nativeLabel(v, canonBook, canonChapter, canonVerse);
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
            {secondary && <span className="me-1 font-sans text-[0.7rem]">({v.bookId === "DAG" ? "Greek Daniel" : v.bookId === "ESG" ? "Greek Esther" : v.bookId})</span>}
            {v.continued ? (
              <span className="font-sans text-xs italic text-stone-400">(text shown with the verse above)</span>
            ) : v.tokens.length ? (
              v.tokens.map((t) => <TokenSpan key={t.id} t={t} />)
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
