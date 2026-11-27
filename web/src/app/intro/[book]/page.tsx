import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { getBook } from "@/lib/bible";
import { getBookIntros } from "@/lib/commentary";

export default function Page(props: PageProps<"/intro/[book]">) {
  return (
    <Suspense fallback={<p className="text-stone-400">Loading…</p>}>
      <Intro params={props.params} />
    </Suspense>
  );
}

async function Intro({ params }: { params: PageProps<"/intro/[book]">["params"] }) {
  const { book: id } = await params;
  const book = getBook(id.toUpperCase());
  if (!book) notFound();
  const { intros, kdIntroHref, articles } = getBookIntros(book.id);
  if (!intros.length && !kdIntroHref && !articles.length) notFound();
  return (
    <div className="max-w-3xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Introductions to {book.name}</h1>
        <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
          What each commentary says about the book as a whole. They come from different traditions; see{" "}
          <Link href="/about#commentaries" className="underline">the commentaries</Link> for who wrote each and why.{" "}
          <Link href={`/read/${book.id}/1`} className="text-amber-800 underline dark:text-amber-300">
            Read {book.name} 1 →
          </Link>
        </p>
      </div>
      {intros.map((g) => (
        <section key={g.id} aria-label={g.title}>
          <h2 className="text-lg font-semibold">{g.title}</h2>
          <p className="mb-3 text-xs italic text-stone-500">
            {g.tradition} · {g.written}
          </p>
          <div className="space-y-6">
            {g.entries.map((e) => (
              <article key={e.id}>
                {e.title && g.entries.length > 1 && <h3 className="mb-1 font-semibold">{e.title}</h3>}
                {/* safe HTML from the pipeline: a fixed set of tags, all text escaped, checked at build time */}
                <div className="commentary-body" dangerouslySetInnerHTML={{ __html: e.body }} />
              </article>
            ))}
          </div>
          <p className="mt-3 text-[0.65rem] text-stone-500">{g.attribution}</p>
        </section>
      ))}
      {kdIntroHref && (
        <section>
          <h2 className="text-lg font-semibold">Keil &amp; Delitzsch</h2>
          <p className="text-sm">
            Keil and Delitzsch&apos;s introduction to {book.name} is kept with their comment on the opening verses.{" "}
            <Link href={kdIntroHref} className="text-amber-800 underline dark:text-amber-300">
              Open {book.name} 1:1
            </Link>{" "}
            and choose ¶, then Keil &amp; Delitzsch.
          </p>
        </section>
      )}
      {articles.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold">Articles and profiles</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {articles.map((a) => (
              <li key={a.id}>
                <Link href={a.href} className="text-amber-800 hover:underline dark:text-amber-300">
                  {a.title}
                </Link>{" "}
                <span className="text-xs text-stone-500">
                  {a.kind} · {a.refLabel} · {a.commentary}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
