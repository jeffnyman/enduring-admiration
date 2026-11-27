import { notFound } from "next/navigation";
import { Suspense } from "react";
import { Concordance } from "@/components/Concordance";
import { getStrongs } from "@/lib/bible";

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
  if (!data || !data.counts.length) notFound();
  return <Concordance title={data.id} hebrew={data.id.startsWith("H")} {...data} />;
}
