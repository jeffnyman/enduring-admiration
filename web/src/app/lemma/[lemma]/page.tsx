import { notFound } from "next/navigation";
import { Suspense } from "react";
import { Concordance } from "@/components/Concordance";
import { getLemma } from "@/lib/bible";

// Septuagint words with no Strong's or STEP extended number are looked up by lemma.
export default function Page(props: PageProps<"/lemma/[lemma]">) {
  return (
    <Suspense fallback={<p className="text-stone-400">Loading…</p>}>
      <Lemma params={props.params} />
    </Suspense>
  );
}

async function Lemma({ params }: { params: PageProps<"/lemma/[lemma]">["params"] }) {
  const { lemma } = await params;
  const data = getLemma(decodeURIComponent(lemma));
  if (!data.counts.length) notFound();
  return <Concordance title={data.id} hebrew={false} {...data} />;
}
