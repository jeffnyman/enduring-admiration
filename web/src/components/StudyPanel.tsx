"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { setNote, useAnnotations } from "@/lib/annotations";
import type { CrossRef, LexEntry, WordDetails } from "@/lib/bible";

const LEX_NOTE: Record<string, string> = {
  bdb: "Brown-Driver-Briggs",
  thayer: "Thayer",
  lsj: "Liddell-Scott-Jones",
  "strongs-heb": "Strong's",
  "strongs-grk": "Strong's",
};

function Entry({ e }: { e: LexEntry }) {
  const long = e.definition && e.definition !== e.shortDef;
  return (
    <div className="rounded border border-stone-200 p-3 dark:border-stone-800">
      <div className="mb-1 flex items-baseline justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-stone-500">
          {LEX_NOTE[e.lexiconId] ?? e.lexiconName}
        </span>
        <span className="text-[0.65rem] text-stone-400">
          {e.entryKey}
          {e.status === "base" ? " · outline entry (digitization in progress)" : ""}
        </span>
      </div>
      <div className="mb-1">
        <span className={/[֐-׿]/.test(e.lemma) ? "scripture-he text-xl" : "scripture-grc"} dir="auto">
          {e.lemma}
        </span>
        {e.translit && <span className="ms-2 italic text-stone-600 dark:text-stone-400">{e.translit}</span>}
        {e.pronunciation && <span className="ms-2 text-xs text-stone-500">({e.pronunciation})</span>}
        {e.partOfSpeech && <span className="ms-2 text-xs text-stone-500">{e.partOfSpeech}</span>}
      </div>
      {e.shortDef && <p className="text-sm">{e.shortDef}</p>}
      {e.derivation && e.derivation !== e.shortDef && <p className="mt-1 text-xs text-stone-500">{e.derivation}</p>}
      {e.kjvUsage && <p className="mt-1 text-xs text-stone-500">KJV: {e.kjvUsage}</p>}
      {long && (
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer text-xs text-amber-800 dark:text-amber-300">Full entry</summary>
          <div className="mt-1 max-h-96 overflow-y-auto whitespace-pre-line text-[0.85rem] leading-relaxed">
            {e.definition}
          </div>
        </details>
      )}
    </div>
  );
}

type XrefData = { label: string; total: number; refs: CrossRef[] };
type NoteTarget = { id: string; ref: string; href: string };

function NoteEditor({ target }: { target: NoteTarget }) {
  const note = useAnnotations()[target.id]?.note ?? "";
  return (
    <div className="space-y-2">
      <label htmlFor="note-text" className="text-xs text-stone-500">
        Saved in this browser as you type. Export from Bookmarks to keep a copy.
      </label>
      <textarea
        id="note-text"
        autoFocus
        value={note}
        onChange={(e) => setNote(target, e.target.value)}
        rows={8}
        className="w-full rounded border border-stone-300 bg-white p-2 font-sans text-sm dark:border-stone-700 dark:bg-stone-950"
      />
      {note && (
        <button onClick={() => setNote(target, "")} className="text-xs text-red-700 underline dark:text-red-400">
          Delete note
        </button>
      )}
    </div>
  );
}

/**
 * Side panel for the reader (a bottom sheet on phones). One delegated listener opens it for
 * a word ([data-tok]), a verse's cross-references ([data-xref]) or a verse note ([data-note]).
 */
export function StudyPanel({ children }: { children: React.ReactNode }) {
  const [word, setWord] = useState<WordDetails | null>(null);
  const [xref, setXref] = useState<XrefData | null>(null);
  const [note, setNoteTarget] = useState<NoteTarget | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");
  const selected = useRef<HTMLElement | null>(null);

  const close = useCallback(() => {
    selected.current?.setAttribute("aria-pressed", "false");
    selected.current?.focus();
    selected.current = null;
    setWord(null);
    setXref(null);
    setNoteTarget(null);
    setState("idle");
  }, []);

  const open = useCallback(async (el: HTMLElement) => {
    if (selected.current?.dataset.tok) selected.current.setAttribute("aria-pressed", "false");
    selected.current = el;
    setWord(null);
    setXref(null);
    setNoteTarget(null);
    if (el.dataset.note) {
      setNoteTarget({ id: el.dataset.note, ref: el.dataset.ref ?? "", href: el.dataset.href ?? "" });
      setState("idle");
      return;
    }
    if (el.dataset.tok) el.setAttribute("aria-pressed", "true");
    setState("loading");
    try {
      const res = await fetch(el.dataset.tok ? `/api/token/${el.dataset.tok}` : `/api/xrefs/${el.dataset.xref}`);
      if (!res.ok) throw new Error(String(res.status));
      if (el.dataset.tok) setWord((await res.json()) as WordDetails);
      else setXref((await res.json()) as XrefData);
      setState("idle");
    } catch {
      setState("error");
    }
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close]);

  const pick = (e: React.SyntheticEvent) => {
    const el = (e.target as HTMLElement).closest<HTMLElement>("[data-tok],[data-xref],[data-note]");
    if (el) void open(el);
  };

  const showing = state !== "idle" || word || xref || note;
  const title = word ? "Word details" : xref ? "Cross-references" : note ? "Note" : "Details";
  const machine = word?.edition.id.startsWith("LXX-SWETE") || word?.tagStatus === "inferred";

  return (
    <div
      onClick={pick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          if ((e.target as HTMLElement).dataset.tok) {
            e.preventDefault();
            pick(e);
          }
        }
      }}
    >
      {children}
      {showing && (
        <aside
          role="dialog"
          aria-label={title}
          className="fixed inset-x-0 bottom-0 z-30 flex max-h-[75vh] flex-col rounded-t-2xl border-t border-stone-200 bg-white shadow-2xl md:inset-x-auto md:inset-y-0 md:right-0 md:max-h-none md:w-full md:max-w-md md:rounded-none md:border-l md:border-t-0 md:shadow-xl dark:border-stone-800 dark:bg-stone-900"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="mx-auto mt-2 h-1 w-10 shrink-0 rounded-full bg-stone-300 md:hidden dark:bg-stone-700" aria-hidden />
          <div className="flex items-start justify-between border-b border-stone-200 p-4 dark:border-stone-800">
            <div>
              {xref && (
                <>
                  <div className="text-lg font-semibold">Cross-references</div>
                  <div className="text-xs text-stone-500">
                    {xref.label} · {xref.total.toLocaleString()} references
                    {xref.total > xref.refs.length ? `, top ${xref.refs.length} shown` : ""}
                  </div>
                </>
              )}
              {note && (
                <>
                  <div className="text-lg font-semibold">Note</div>
                  <div className="text-xs text-stone-500">{note.ref}</div>
                </>
              )}
              {word && (
                <>
                  <div
                    className={word.edition.language === "hbo" ? "scripture-he text-3xl" : "scripture-grc text-2xl"}
                    dir={word.edition.direction}
                    lang={word.edition.language}
                  >
                    {word.surface}
                  </div>
                  <div className="text-xs text-stone-500">
                    {word.ref} · {word.edition.name}
                    {word.variant && ` · ${word.variant === "ketiv" ? "Ketiv (written)" : "Qere (read)"}`}
                  </div>
                  {(word.translit || word.gloss) && (
                    <div className="mt-1 text-sm">
                      {word.translit && <span className="italic">{word.translit}</span>}
                      {word.gloss && <span className="ms-2">“{word.gloss}”</span>}
                    </div>
                  )}
                </>
              )}
              {state === "loading" && <div className="text-sm text-stone-500">Loading…</div>}
              {state === "error" && <div className="text-sm text-red-700">Could not load this word.</div>}
            </div>
            <button onClick={close} className="rounded px-2 py-1 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800" aria-label="Close">
              ✕
            </button>
          </div>
          {xref && (
            <ol className="flex-1 space-y-3 overflow-y-auto p-4">
              {xref.refs.map((r, i) => (
                <li key={i} className="text-sm">
                  <Link href={r.href} className="font-semibold text-amber-800 hover:underline dark:text-amber-300">
                    {r.label}
                  </Link>
                  <span className="ms-2 text-[0.65rem] text-stone-400">
                    {r.source === "web" ? "WEB note" : `${r.votes} votes`}
                  </span>
                  <p className="scripture-en text-[0.95rem] text-stone-700 dark:text-stone-300">{r.text}</p>
                </li>
              ))}
              <li className="pt-2 text-[0.65rem] text-stone-400">
                Cross-references from OpenBible.info (CC BY), ranked by votes, and the WEB&apos;s own notes.
              </li>
            </ol>
          )}
          {note && (
            <div className="flex-1 overflow-y-auto p-4">
              <NoteEditor target={note} />
            </div>
          )}
          {word && (
            <div className="flex-1 space-y-5 overflow-y-auto p-4">
              {word.ocrOriginal && (
                <p className="rounded bg-stone-100 p-2 text-xs text-stone-700 dark:bg-stone-800 dark:text-stone-300">
                  Corrected OCR error: the digital transcription of Swete reads{" "}
                  <span className="scripture-grc">{word.ocrOriginal}</span>. The correction is the form found in
                  Brenton and elsewhere in Swete.
                </p>
              )}
              {machine && (
                <p className="rounded bg-amber-50 p-2 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-200">
                  Septuagint lemma and parsing are machine-generated (Morpheus)
                  {word.tagStatus === "inferred" ? ", copied from the same form elsewhere in the book" : ""}. Check
                  doubtful forms.
                </p>
              )}
              {word.morphemes.map((m) => (
                <section key={m.id}>
                  <div className="mb-2 flex flex-wrap items-baseline gap-x-2">
                    {word.morphemes.length > 1 && (
                      <span className="rounded bg-stone-100 px-1.5 text-[0.65rem] uppercase text-stone-600 dark:bg-stone-800 dark:text-stone-300">
                        {m.role}
                      </span>
                    )}
                    {word.morphemes.length > 1 && (
                      <span className={word.edition.language === "hbo" ? "scripture-he text-lg" : "scripture-grc"} dir="auto">
                        {m.surface}
                      </span>
                    )}
                    {m.lemma && (
                      <span className="text-sm">
                        lemma <span dir="auto" className={word.edition.language === "hbo" ? "scripture-he" : "scripture-grc"}>{m.lemma}</span>
                      </span>
                    )}
                    {m.href && (
                      <Link href={m.href} className="text-sm text-amber-800 underline dark:text-amber-300" title="All occurrences">
                        {m.key?.startsWith("lemma:") ? "all occurrences" : (m.strongsExt ?? m.strongs)}
                      </Link>
                    )}
                    {m.gloss && <span className="text-sm text-stone-500">“{m.gloss}”</span>}
                  </div>
                  {m.morphCode && (
                    <p className="mb-2 text-sm">
                      <span className="font-mono text-xs text-stone-500">{m.morphCode}</span>{" "}
                      {m.morphSummary ?? <span className="text-stone-400">(no expansion)</span>}
                    </p>
                  )}
                  {m.equivalents.length > 0 && (
                    <div className="mb-2 rounded bg-sky-50 p-2 text-sm dark:bg-sky-950">
                      <div className="mb-1 text-xs font-semibold text-sky-900 dark:text-sky-200">
                        {word.edition.language === "hbo" ? "In the Septuagint usually" : "Usually renders (Hebrew)"}
                      </div>
                      <ul className="space-y-0.5">
                        {m.equivalents.slice(0, 3).map((q) => (
                          <li key={q.key} className="flex flex-wrap items-baseline gap-x-1.5">
                            <Link
                              href={q.href}
                              className={`${word.edition.language === "hbo" ? "scripture-grc" : "scripture-he text-lg"} hover:underline`}
                              dir="auto"
                            >
                              {q.lemma}
                            </Link>
                            {q.gloss && <span className="text-xs">{q.gloss}</span>}
                            <span className="text-[0.7rem] text-stone-500">
                              {q.both}/{q.fromVerses} verses{q.ntCount ? ` · NT ${q.ntCount}×` : ""}
                            </span>
                          </li>
                        ))}
                      </ul>
                      <div className="mt-1 text-[0.65rem] text-stone-500">Statistical: words found together in aligned verses.</div>
                    </div>
                  )}
                  <div className="space-y-2">
                    {m.entries.map((e) => (
                      <Entry key={`${e.lexiconId}-${e.entryKey}`} e={e} />
                    ))}
                    {!m.entries.length && m.role !== "suffix" && (
                      <p className="text-xs text-stone-400">No lexicon entry linked.</p>
                    )}
                  </div>
                </section>
              ))}
            </div>
          )}
        </aside>
      )}
    </div>
  );
}
