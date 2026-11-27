"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import type { LexEntry, WordDetails } from "@/lib/bible";

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

export function WordDrawer({ children }: { children: React.ReactNode }) {
  const [word, setWord] = useState<WordDetails | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");
  const selected = useRef<HTMLElement | null>(null);

  const close = useCallback(() => {
    selected.current?.setAttribute("aria-pressed", "false");
    selected.current?.focus();
    selected.current = null;
    setWord(null);
    setState("idle");
  }, []);

  const open = useCallback(async (el: HTMLElement) => {
    selected.current?.setAttribute("aria-pressed", "false");
    selected.current = el;
    el.setAttribute("aria-pressed", "true");
    setState("loading");
    try {
      const res = await fetch(`/api/token/${el.dataset.tok}`);
      if (!res.ok) throw new Error(String(res.status));
      setWord((await res.json()) as WordDetails);
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
    const el = (e.target as HTMLElement).closest<HTMLElement>("[data-tok]");
    if (el) void open(el);
  };

  const showing = state !== "idle" || word;
  const machine = word?.edition.id === "LXX-SWETE" || word?.tagStatus === "inferred";

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
          aria-label="Word details"
          className="fixed inset-y-0 right-0 z-30 flex w-full max-w-md flex-col border-l border-stone-200 bg-white shadow-xl dark:border-stone-800 dark:bg-stone-900"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-start justify-between border-b border-stone-200 p-4 dark:border-stone-800">
            <div>
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
          {word && (
            <div className="flex-1 space-y-5 overflow-y-auto p-4">
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
