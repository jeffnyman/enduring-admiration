import { getEditions, getSources } from "@/lib/bible";

// Static: the database never changes at runtime, so this page is prerendered.
export default function About() {
  const sources = getSources();
  const editions = getEditions();
  return (
    <div className="max-w-4xl space-y-8">
      <section>
        <h1 className="mb-2 text-2xl font-semibold tracking-tight">Sources and licenses</h1>
        <p className="text-sm text-stone-600 dark:text-stone-400">
          Every word of Scripture here comes from the openly licensed files below; nothing is typed in by hand. Because the
          Septuagint (Swete) data is CC BY-SA, the database as a whole is distributed under CC BY-SA 4.0 with these
          attributions.
        </p>
      </section>
      <section>
        <h2 className="mb-2 text-lg font-semibold">Editions</h2>
        <ul className="space-y-2 text-sm">
          {editions.map((e) => (
            <li key={e.id}>
              <span className="font-semibold">{e.name}</span> <span className="text-stone-500">({e.id})</span>
              {e.notes && <p className="text-stone-600 dark:text-stone-400">{e.notes}</p>}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h2 className="mb-2 text-lg font-semibold">Data sources</h2>
        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase text-stone-500">
            <tr>
              <th className="py-1 pe-4">Source</th>
              <th className="py-1 pe-4">License</th>
              <th className="py-1">Attribution</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((s) => (
              <tr key={s.id} className="border-t border-stone-200 align-top dark:border-stone-800">
                <td className="py-2 pe-4">
                  {s.title}
                  {s.version && <div className="font-mono text-[0.65rem] text-stone-400">{s.version.slice(0, 12)}</div>}
                </td>
                <td className="py-2 pe-4 whitespace-nowrap">{s.license}</td>
                <td className="py-2">{s.attribution}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="text-sm text-stone-600 dark:text-stone-400">
        <h2 className="mb-2 text-lg font-semibold text-stone-900 dark:text-stone-100">Versification</h2>
        <p>
          Verses are aligned on the Standard (NRSV-based English) numbering using STEPBible&apos;s TVTMS rules, with a small
          number of documented corrections. Where an edition numbers a verse differently, its own reference appears in
          small type beside the text; “≈” marks verses that only partly correspond.
        </p>
      </section>
    </div>
  );
}
