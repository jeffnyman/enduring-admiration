"use client";

import { useState } from "react";
import type { CommentaryEntry, CommentaryGroup } from "@/lib/commentary";

export type CommentaryData = { label: string; groups: CommentaryGroup[] };

const LONG = 2400; // characters of HTML: longer entries start collapsed
const plain = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
const isHebrew = (s: string) => /[֐-׿]/.test(s);
// unfoldingWord note types (translationAcademy article names) in plain words
const NOTE_NAMES: Record<string, string> = {
  explicit: "implied meaning", metaphor: "metaphor", metonymy: "metonymy", idiom: "idiom", abstractnouns: "abstract nouns",
  activepassive: "active or passive", rquestion: "rhetorical question", synecdoche: "synecdoche", parallelism: "parallelism",
  personification: "personification", doublet: "doublet", simile: "simile", hyperbole: "exaggeration", irony: "irony",
  euphemism: "euphemism", ellipsis: "omitted words", possession: "possession", nominaladj: "adjective as noun",
  genericnoun: "generic noun", gendernotations: "gender", infostructure: "word order", quotesinquotes: "quotation",
  pronouns: "pronouns", quotations: "quotation", unknown: "unfamiliar thing", names: "names", symlanguage: "symbolic language",
  "connect-logic-result": "reason and result", "connect-words-phrases": "connecting words", background: "background",
  poetry: "poetry", hendiadys: "hendiadys", litotes: "understatement", merism: "merism", apostrophe: "apostrophe",
  "123person": "person", events: "order of events", imperative: "command", exclamations: "exclamation", you: "you",
  youdual: "you (two)", youformal: "you (formal)", exclusive: "exclusive we", inclusive: "inclusive we",
};
const NOTE_TYPE = (label: string | null) => {
  if (!label || label === "chapter-intro") return null;
  const k = label.replace(/^(figs|writing|grammar|translate|guidelines)-/, "");
  return NOTE_NAMES[k] ?? k.replace(/-/g, " ");
};

/** Highlight the words a language note is about, in the visible verse rows. */
function highlight(ids: number[], on: boolean) {
  for (const id of ids) {
    document.querySelectorAll<HTMLElement>(`[data-tok="${id}"]`).forEach((el) => el.classList.toggle("is-noted", on));
  }
}

function Body({ html }: { html: string }) {
  // safe HTML from the pipeline: a fixed set of tags, all text escaped, checked at build time
  return <div className="commentary-body" dangerouslySetInnerHTML={{ __html: html }} />;
}

export function CommentaryEntryView({ e, commentary }: { e: CommentaryEntry; commentary: string }) {
  const long = e.body.length > LONG;
  const words = e.words;
  const head = (
    <div className="mb-1 flex flex-wrap items-baseline gap-x-2 text-xs text-stone-500">
      <span className="font-semibold text-stone-700 dark:text-stone-300">{e.title ?? e.refLabel}</span>
      {e.title && <span>{e.refLabel}</span>}
      {e.kind !== "note" && <span className="rounded bg-stone-100 px-1 uppercase dark:bg-stone-800">{e.kind}</span>}
      {commentary === "uw" && NOTE_TYPE(e.label) && <span className="italic">{NOTE_TYPE(e.label)}</span>}
      {commentary === "catena" && e.label && <span className="italic">{e.label}</span>}
    </div>
  );
  const quote = e.quote && (
    <div className={`mb-1 ${isHebrew(e.quote) ? "scripture-he text-lg" : "scripture-grc"}`} dir={isHebrew(e.quote) ? "rtl" : "ltr"}>
      {e.quote}
      {e.quote && !words.length && <span className="ms-2 font-sans text-[0.65rem] text-stone-400" dir="ltr">(words not found in this text)</span>}
    </div>
  );
  return (
    <li
      className={`rounded border border-stone-200 p-3 text-sm dark:border-stone-800 ${words.length ? "cursor-default focus:outline focus:outline-sky-400" : ""}`}
      tabIndex={words.length ? 0 : undefined}
      data-entry={e.id}
      data-words={words.join(" ") || undefined}
      onMouseEnter={() => highlight(words, true)}
      onMouseLeave={() => highlight(words, false)}
      onFocus={() => highlight(words, true)}
      onBlur={() => highlight(words, false)}
    >
      {head}
      {quote}
      {long ? (
        <details>
          <summary className="cursor-pointer text-stone-600 dark:text-stone-400">
            {plain(e.body).slice(0, 220)}… <span className="text-amber-800 dark:text-amber-300">read more</span>
          </summary>
          <Body html={e.body} />
        </details>
      ) : (
        <Body html={e.body} />
      )}
    </li>
  );
}

function Group({ g }: { g: CommentaryGroup }) {
  const [all, setAll] = useState(false);
  const minor = g.entries.filter((e) => e.minor).length;
  const shown = all ? g.entries : g.entries.filter((e) => !e.minor);
  return (
    <div className="space-y-3">
      <details className="rounded bg-stone-50 p-2 text-xs text-stone-600 dark:bg-stone-800/50 dark:text-stone-400">
        <summary className="cursor-pointer">
          <span className="font-semibold text-stone-800 dark:text-stone-200">{g.title}</span>
          {g.author && <> · {g.author}</>} · {g.written}
          <div className="mt-0.5 italic">{g.tradition}</div>
        </summary>
        <p className="mt-2">{g.description}</p>
        <p className="mt-2 text-[0.65rem] text-stone-500">
          {g.license}. {g.attribution}
        </p>
      </details>
      <ul className="space-y-3">
        {shown.map((e) => (
          <CommentaryEntryView key={e.id} e={e} commentary={g.id} />
        ))}
      </ul>
      {minor > 0 && (
        <button onClick={() => setAll((a) => !a)} className="text-xs text-amber-800 underline dark:text-amber-300">
          {all ? "Hide the notes on translation technique" : `Show ${minor} more note${minor > 1 ? "s" : ""} on translation technique`}
        </button>
      )}
    </div>
  );
}

/** The commentaries on one verse: a tab per commentary. (Give it a key per verse so the tab resets.) */
export function CommentaryView({ data }: { data: CommentaryData }) {
  const [tab, setTab] = useState(data.groups[0]?.id);
  const g = data.groups.find((x) => x.id === tab) ?? data.groups[0];
  if (!g) return <p className="p-4 text-sm text-stone-500">No commentary on this verse.</p>;
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div role="tablist" aria-label="Commentaries" className="flex flex-wrap gap-1 border-b border-stone-200 px-4 py-2 dark:border-stone-800">
        {data.groups.map((x) => {
          const n = x.entries.filter((e) => !e.minor).length || x.entries.length;
          return (
            <button
              key={x.id}
              role="tab"
              aria-selected={x.id === g.id}
              onClick={() => setTab(x.id)}
              className={`rounded px-2 py-0.5 text-xs ${x.id === g.id ? "bg-stone-800 text-white dark:bg-stone-200 dark:text-stone-900" : "bg-stone-100 hover:bg-stone-200 dark:bg-stone-800 dark:hover:bg-stone-700"}`}
            >
              {x.shortTitle} <span className="opacity-60">{n}</span>
            </button>
          );
        })}
      </div>
      <div role="tabpanel" aria-label={g.title} className="flex-1 overflow-y-auto p-4">
        <Group key={g.id} g={g} />
      </div>
    </div>
  );
}
