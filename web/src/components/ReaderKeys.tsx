"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const KEYS: [string, string][] = [
  ["j / k", "next / previous verse"],
  ["l / h  or  → / ←", "next / previous chapter"],
  ["g", "show or hide the gloss line"],
  ["b", "bookmark the current verse"],
  ["e", "write a note on the current verse"],
  ["x", "cross-references for the current verse"],
  ["c", "commentary on the current verse"],
  ["Esc", "close the panel"],
  ["?", "this list"],
];

/** Keyboard navigation for the reader. Shortcuts reuse the on-screen buttons. */
export function ReaderKeys({ prevHref, nextHref, glossHref }: { prevHref?: string; nextHref?: string; glossHref: string }) {
  const router = useRouter();
  const [help, setHelp] = useState(false);

  useEffect(() => {
    // only rows of the page being shown (Next keeps the previous page mounted but hidden)
    const rows = () => [...document.querySelectorAll<HTMLElement>(".verse-row")].filter((r) => r.offsetParent !== null);
    const current = () => rows().find((r) => r.classList.contains("is-current"));

    const select = (row: HTMLElement | undefined) => {
      if (!row) return;
      rows().forEach((r) => r.classList.remove("is-current"));
      row.classList.add("is-current");
      row.focus({ preventScroll: true });
      row.scrollIntoView({ block: "center", behavior: "smooth" });
      history.replaceState(null, "", `#${row.id}`);
    };

    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (e.metaKey || e.ctrlKey || e.altKey || t.closest("input, textarea, select, [contenteditable]")) return;
      const list = rows();
      const at = current() ?? list.find((r) => `#${r.id}` === location.hash);
      const i = at ? list.indexOf(at) : -1;
      const press = (sel: string) => at?.querySelector<HTMLElement>(sel)?.click();
      switch (e.key) {
        case "j":
          select(list[Math.min(i + 1, list.length - 1)]);
          break;
        case "k":
          select(list[Math.max(i - 1, 0)]);
          break;
        case "l":
        case "ArrowRight":
          if (nextHref) router.push(nextHref);
          break;
        case "h":
        case "ArrowLeft":
          if (prevHref) router.push(prevHref);
          break;
        case "g":
          router.push(glossHref);
          break;
        case "b":
          press('button[aria-label^="Bookmark"]');
          break;
        case "e":
          press("[data-note]");
          break;
        case "x":
          press("[data-xref]");
          break;
        case "c":
          press("[data-commentary]");
          break;
        case "?":
          setHelp((h) => !h);
          break;
        case "Escape":
          setHelp(false);
          return;
        default:
          return;
      }
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    document.documentElement.dataset.keys = "ready"; // lets tests know shortcuts are live
    return () => window.removeEventListener("keydown", onKey);
  }, [router, prevHref, nextHref, glossHref]);

  return (
    <>
      <button
        type="button"
        onClick={() => setHelp(true)}
        className="hidden text-xs text-stone-400 underline decoration-dotted hover:text-stone-600 md:inline"
      >
        Keyboard shortcuts (?)
      </button>
      {help && (
        <div
          role="dialog"
          aria-label="Keyboard shortcuts"
          className="fixed inset-0 z-40 flex items-center justify-center bg-black/30"
          onClick={() => setHelp(false)}
        >
          <div className="rounded-lg bg-white p-5 shadow-xl dark:bg-stone-900" onClick={(e) => e.stopPropagation()}>
            <h2 className="mb-3 font-semibold">Keyboard shortcuts</h2>
            <table className="text-sm">
              <tbody>
                {KEYS.map(([k, what]) => (
                  <tr key={k}>
                    <td className="pe-6 py-0.5 font-mono text-xs text-stone-600 dark:text-stone-300">{k}</td>
                    <td>{what}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}
