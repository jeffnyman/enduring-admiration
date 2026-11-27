import Link from "next/link";
import { redirect } from "next/navigation";
import { Suspense } from "react";
import { lemmaMatches, normalizeStrongs, search } from "@/lib/bible";
import { isGreek, isHebrew } from "@/lib/normalize";

const EDITIONS = [
  ["WEB", "English (WEB)"],
  ["WLC", "Hebrew (WLC)"],
  ["LXX-SWETE", "Septuagint (Swete)"],
  ["LXX-BRENTON", "Septuagint (Brenton)"],
  ["SBLGNT", "Greek NT (SBLGNT)"],
] as const;

export default function Page(props: PageProps<"/search">) {
  return (
    <div className="max-w-4xl">
      <h1 className="mb-4 text-2xl font-semibold tracking-tight">Search</h1>
      <Suspense fallback={<p className="text-stone-400">Searching…</p>}>
        <Results searchParams={props.searchParams} />
      </Suspense>
    </div>
  );
}

function Highlight({ s }: { s: string }) {
  // snippet() marks matches with \u0001 … \u0002
  return (
    <>
      {s.split(/(\u0001[^\u0002]*\u0002)/).map((part, i) =>
        part.startsWith("\u0001") ? (
          <mark key={i} className="rounded bg-amber-200 px-0.5 dark:bg-amber-800">
            {part.slice(1, -1)}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}

async function Results({ searchParams }: { searchParams: PageProps<"/search">["searchParams"] }) {
  const sp = await searchParams;
  const q = typeof sp.q === "string" ? sp.q.trim() : "";
  const strongs = normalizeStrongs(q);
  if (strongs) redirect(`/strongs/${q.trim().toUpperCase().replace(/^([HG])0*/, "$1")}`);

  // Default the edition from the script typed
  const guess = isHebrew(q) ? "WLC" : isGreek(q) ? "LXX-SWETE" : "WEB";
  const ed = typeof sp.ed === "string" && EDITIONS.some(([id]) => id === sp.ed) ? sp.ed : guess;
  const { total, hits } = q ? search(q, ed) : { total: 0, hits: [] };
  const lemmas = q ? lemmaMatches(q) : [];
  const rtl = ed === "WLC";

  return (
    <>
      <form action="/search" className="mb-6 flex flex-wrap gap-2">
        <input
          name="q"
          defaultValue={q}
          dir="auto"
          placeholder='Words, "a phrase", Hebrew or Greek (accents optional), or H7225'
          className="min-w-72 flex-1 rounded border border-stone-300 bg-white px-3 py-2 dark:border-stone-700 dark:bg-stone-900"
        />
        <select name="ed" defaultValue={ed} className="rounded border border-stone-300 bg-white px-2 dark:border-stone-700 dark:bg-stone-900">
          {EDITIONS.map(([id, label]) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
        <button className="rounded bg-stone-800 px-4 py-2 text-white dark:bg-stone-200 dark:text-stone-900">Search</button>
      </form>
      {lemmas.length > 0 && (
        <section className="mb-6 rounded border border-stone-200 p-4 dark:border-stone-800" aria-label="Dictionary words">
          <h2 className="mb-2 text-sm font-semibold">Dictionary words (all forms, including with prefixes)</h2>
          <ul className="space-y-1">
            {lemmas.map((l) => (
              <li key={l.key} className="flex flex-wrap items-baseline gap-x-2">
                <Link href={l.href} className={`${/^H/.test(l.key) ? "scripture-he text-xl" : "scripture-grc"} hover:underline`} dir="auto">
                  {l.lemma}
                </Link>
                <span className="text-xs text-stone-500">{l.key.replace(/^lemma:/, "")}</span>
                {l.gloss && <span className="text-sm">{l.gloss.length > 70 ? l.gloss.slice(0, 67) + "…" : l.gloss}</span>}
                <span className="text-xs text-stone-500">{l.matches.toLocaleString()} matching words</span>
              </li>
            ))}
          </ul>
        </section>
      )}
      {q && (
        <p className="mb-4 text-sm text-stone-500">
          {total.toLocaleString()} verse{total === 1 ? "" : "s"}
          {total > hits.length ? ` (showing the first ${hits.length})` : ""}. Hebrew and Greek are matched without
          vowels or accents. Verse matches use whole word forms; the dictionary words above also find prefixed forms.
        </p>
      )}
      <ol className="space-y-3">
        {hits.map((h, i) => (
          <li key={i} className="border-b border-stone-100 pb-3 dark:border-stone-900">
            <Link
              href={h.href}
              className="text-sm font-semibold text-amber-800 hover:underline dark:text-amber-300"
            >
              {h.ref}
            </Link>
            <p dir={rtl ? "rtl" : "ltr"} className={rtl ? "scripture-he text-xl" : ed === "WEB" ? "scripture-en" : "scripture-grc"}>
              <Highlight s={h.snippet} />
            </p>
          </li>
        ))}
      </ol>
    </>
  );
}
