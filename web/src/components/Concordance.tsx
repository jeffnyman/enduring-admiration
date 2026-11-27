import Link from "next/link";
import type { Equivalent, LexEntry, StrongsOccurrence } from "@/lib/bible";

const ED: Record<string, string> = {
  WLC: "Hebrew",
  "LXX-SWETE": "Septuagint",
  SBLGNT: "Greek NT",
};

export function Equivalents({ items, hebrew }: { items: Equivalent[]; hebrew: boolean }) {
  if (!items.length) return null;
  return (
    <section className="mb-8">
      <h2 className="mb-1 text-lg font-semibold">
        {hebrew ? "In the Septuagint usually" : "In the Hebrew Bible this usually renders"}
      </h2>
      <p className="mb-3 text-xs text-stone-500">
        Measured from verses where both words occur in the aligned Hebrew and Septuagint texts. Statistical, not a
        word-by-word alignment.
      </p>
      <ul className="space-y-1.5">
        {items.map((e) => (
          <li key={e.key} className="flex flex-wrap items-baseline gap-x-2">
            <Link href={e.href} className={`${hebrew ? "scripture-grc" : "scripture-he text-xl"} hover:underline`} dir="auto">
              {e.lemma}
            </Link>
            <span className="text-xs text-stone-500">{e.key.replace(/^lemma:/, "")}</span>
            {e.gloss && <span className="text-sm">{e.gloss}</span>}
            <span className="text-xs text-stone-500">
              together in {e.both} of {e.fromVerses} verses
              {e.ntCount ? ` · New Testament ${e.ntCount.toLocaleString()}×` : ""}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function Concordance({
  title,
  hebrew,
  entries,
  counts,
  occurrences,
  equivalents,
}: {
  title: string;
  hebrew: boolean;
  entries: LexEntry[];
  counts: { editionId: string; n: number }[];
  occurrences: StrongsOccurrence[];
  equivalents: Equivalent[];
}) {
  const lemmaCls = hebrew ? "scripture-he text-2xl" : "scripture-grc text-xl";
  const byBook = new Map<string, StrongsOccurrence[]>();
  for (const o of occurrences) byBook.set(o.bookName, [...(byBook.get(o.bookName) ?? []), o]);
  const total = counts.reduce((a, c) => a + c.n, 0);

  return (
    <div className="max-w-4xl">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight" dir="auto">
        {title}
      </h1>
      <p className="mb-6 text-sm text-stone-500">
        {total.toLocaleString()} occurrence{total === 1 ? "" : "s"}:{" "}
        {counts.map((c) => `${ED[c.editionId] ?? c.editionId} ${c.n.toLocaleString()}`).join(" · ")}
      </p>

      <div className="mb-8 space-y-3">
        {entries.map((e) => (
          <div key={`${e.lexiconId}-${e.entryKey}`} className="rounded border border-stone-200 p-4 dark:border-stone-800">
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-stone-500">
              {e.lexiconName} · {e.entryKey}
              {e.status === "base" ? " · outline entry" : ""}
            </div>
            <div>
              <span className={lemmaCls} dir="auto">{e.lemma}</span>
              {e.translit && <span className="ms-2 italic">{e.translit}</span>}
              {e.partOfSpeech && <span className="ms-2 text-xs text-stone-500">{e.partOfSpeech}</span>}
            </div>
            {e.shortDef && <p className="mt-1">{e.shortDef}</p>}
            {e.kjvUsage && <p className="mt-1 text-sm text-stone-500">KJV: {e.kjvUsage}</p>}
            {e.definition && e.definition !== e.shortDef && (
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-amber-800 dark:text-amber-300">Full entry</summary>
                <div className="mt-1 max-h-[32rem] overflow-y-auto whitespace-pre-line text-sm leading-relaxed">{e.definition}</div>
              </details>
            )}
          </div>
        ))}
        {!entries.length && <p className="text-stone-500">No lexicon entry for this word.</p>}
      </div>

      <Equivalents items={equivalents} hebrew={hebrew} />

      <h2 className="mb-3 text-lg font-semibold">Occurrences</h2>
      {occurrences.length >= 2000 && <p className="mb-2 text-sm text-stone-500">Showing the first 2,000.</p>}
      <div className="space-y-4">
        {[...byBook.entries()].map(([bookName, occ]) => (
          <section key={bookName}>
            <h3 className="mb-1 text-sm font-semibold">
              {bookName} <span className="font-normal text-stone-500">({occ.length})</span>
            </h3>
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-sm">
              {occ.map((o, i) => (
                <Link key={i} href={o.href} className="hover:underline" title={`${ED[o.editionId] ?? o.editionId}: ${o.surface}`}>
                  <bdi>{o.canonChapter}:{o.canonVerse}</bdi>
                  <bdi className={`ms-1 ${hebrew ? "scripture-he text-base" : "scripture-grc text-sm"}`}>{o.surface}</bdi>
                  {o.editionId === "LXX-SWETE" && <sup className="ms-0.5 text-[0.6rem] text-stone-400">LXX</sup>}
                </Link>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
