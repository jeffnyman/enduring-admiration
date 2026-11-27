import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { getStrongs } from "@/lib/bible";

const ED: Record<string, string> = {
  WLC: "Hebrew",
  "LXX-SWETE": "Septuagint",
  SBLGNT: "Greek NT",
};

export default function Page(props: PageProps<"/strongs/[id]">) {
  return (
    <Suspense fallback={<p className="text-stone-400">Loading…</p>}>
      <Strongs params={props.params} />
    </Suspense>
  );
}

async function Strongs({ params }: { params: PageProps<"/strongs/[id]">["params"] }) {
  const { id } = await params;
  const data = getStrongs(decodeURIComponent(id));
  if (!data) notFound();
  const hebrew = data.id.startsWith("H");
  const lemmaCls = hebrew ? "scripture-he text-2xl" : "scripture-grc text-xl";
  const byBook = new Map<string, typeof data.occurrences>();
  for (const o of data.occurrences) byBook.set(o.bookName, [...(byBook.get(o.bookName) ?? []), o]);
  const total = data.counts.reduce((a, c) => a + c.n, 0);

  return (
    <div className="max-w-4xl">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">{data.id}</h1>
      <p className="mb-6 text-sm text-stone-500">
        {total.toLocaleString()} occurrence{total === 1 ? "" : "s"}:{" "}
        {data.counts.map((c) => `${ED[c.editionId] ?? c.editionId} ${c.n.toLocaleString()}`).join(" · ")}
      </p>

      <div className="mb-8 space-y-3">
        {data.entries.map((e) => (
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
        {!data.entries.length && <p className="text-stone-500">No lexicon entry for this number.</p>}
      </div>

      <h2 className="mb-3 text-lg font-semibold">Occurrences</h2>
      {data.occurrences.length >= 2000 && <p className="mb-2 text-sm text-stone-500">Showing the first 2,000.</p>}
      <div className="space-y-4">
        {[...byBook.entries()].map(([bookName, occ]) => (
          <section key={bookName}>
            <h3 className="mb-1 text-sm font-semibold">
              {bookName} <span className="font-normal text-stone-500">({occ.length})</span>
            </h3>
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-sm">
              {occ.map((o, i) => (
                <Link
                  key={i}
                  href={o.href}
                  className="hover:underline"
                  title={`${ED[o.editionId] ?? o.editionId}: ${o.surface}`}
                >
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
