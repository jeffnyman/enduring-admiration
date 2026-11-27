import type { Metadata } from "next";
import Link from "next/link";
// Self-hosted OFL fonts (no network needed). Locally installed SBL Hebrew / Galatia SIL win if present.
import "@fontsource-variable/noto-serif";
import "@fontsource-variable/noto-serif-hebrew";
import "./globals.css";

export const metadata: Metadata = {
  title: "Bible — side by side with Hebrew and Greek",
  description: "World English Bible with the Hebrew, Septuagint and Greek New Testament, word by word.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-stone-50 text-stone-900 dark:bg-stone-950 dark:text-stone-100">
        <header className="sticky top-0 z-20 border-b border-stone-200 bg-stone-50/90 backdrop-blur dark:border-stone-800 dark:bg-stone-950/90">
          <nav className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2 text-sm">
            <Link href="/read/GEN/1" className="font-semibold tracking-tight">
              Bible
            </Link>
            <Link href="/read/GEN/1" className="hover:underline">Read</Link>
            <Link href="/search" className="hover:underline">Search</Link>
            <Link href="/about" className="hover:underline">Sources</Link>
            <form action="/search" className="w-full sm:ml-auto sm:w-auto">
              <label htmlFor="q" className="sr-only">Search</label>
              <input
                id="q"
                name="q"
                placeholder="Search, or H7225 / G3056"
                className="w-full rounded border sm:w-56 border-stone-300 bg-white px-2 py-1 dark:border-stone-700 dark:bg-stone-900"
              />
            </form>
          </nav>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">{children}</main>
        <footer className="border-t border-stone-200 px-4 py-3 text-center text-xs text-stone-500 dark:border-stone-800">
          Texts: World English Bible (public domain), Westminster Leningrad Codex with OpenScriptures morphology (CC BY),
          Swete Septuagint (CC BY-SA), SBL Greek NT (CC BY), STEPBible data (CC BY).{" "}
          <Link href="/about" className="underline">All sources and licenses</Link>
        </footer>
      </body>
    </html>
  );
}
