#!/usr/bin/env python3
"""Evaluate the Swete LXX + Morpheus dataset (QuantForgeSoftware/lxx, CC BY-SA 4.0)
for Genesis 1 and Tobit 1 before deciding whether to ingest it.

Compares it against: the WEB verse grid and the Brenton tokens already in
db/bible.db, its own TEI source text, and the Strong's Greek lemma list.
Prints a report; it does not modify bible.db.

Usage: .venv/bin/python pipeline/eval_swete.py   (run sample_ingest.py first)
"""
import difflib
import re
import sqlite3
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from bibleingest.fetch import fetch
from bibleingest.textnorm import norm_greek, script_of

ROOT = Path(__file__).resolve().parents[1]
SHA = "46258f8bde173998ef0633d79eff3067b9041575"
BASE = f"https://raw.githubusercontent.com/QuantForgeSoftware/lxx/{SHA}/data"
BOOKS = {"GEN": ("001-Gen.txt", "tlg001__tlg0527.tlg001.opp-grc2.xml"),
         "TOB": ("019-Tob.txt", "tlg021__tlg0527.tlg021.1st1K-grc1.xml")}
TEI = "{http://www.tei-c.org/ns/1.0}"

POS = set("A- C- D- I- N- NP P- RA RD RI RP RR V- X-".split())
PARSE = [set("123-"), set("PIFAXY-"), set("AMP-"), set("IDSONP-"), set("NGDAV-"),
         set("SPD-"), set("MFN-"), set("CS-")]


def morph_rows(text, chapter):
    out = []
    for line in text.splitlines():
        f = line.split(" ")
        if len(f) != 9 or int(f[0][3:6]) != chapter:
            continue
        out.append(dict(verse=int(f[0][6:9]), pos=f[1], parse=f[2], text=f[3], word=f[4],
                        norm=f[5], lemma=f[6], src=f[8]))
    return out


def tei_verses(xml, chapter):
    """Main text per verse, notes (apparatus, margin sigla) removed."""
    root = ET.fromstring(xml)
    for ch in root.iter(TEI + "div"):
        if ch.get("subtype") == "chapter" and ch.get("n") == str(chapter):
            res = {}
            for v in ch.iter(TEI + "div"):
                if v.get("subtype") != "verse":
                    continue
                parts = []

                def walk(el):
                    if el.tag == TEI + "note":
                        return
                    parts.append(el.text or "")
                    for c in el:
                        walk(c)
                        parts.append(c.tail or "")
                walk(v)
                res[int(v.get("n"))] = " ".join("".join(parts).split())
            return res
    return {}


def valid_parse(pos, code):
    return pos in POS and len(code) == 8 and all(c in PARSE[i] for i, c in enumerate(code))


def main():
    con = sqlite3.connect(ROOT / "db" / "bible.db")
    q = lambda s, *a: con.execute(s, a).fetchall()
    strongs_lemmas = {norm_greek(r[0]) for r in q(
        "SELECT lemma FROM lexicon_entry WHERE lexicon_id='strongs-grk'")}

    for book, (mfile, tfile) in BOOKS.items():
        mtext = fetch("swete-lxx", f"{BASE}/morph-morpheus/{mfile}", mfile)[0].decode("utf-8")
        ttext = fetch("swete-lxx", f"{BASE}/swete-tei/{tfile}", tfile)[0].decode("utf-8")
        rows = morph_rows(mtext, 1)
        tei = tei_verses(ttext, 1)
        print(f"\n================ {book} 1  ({len(rows)} tokens)")

        # 1. verse grid
        sw = {r["verse"] for r in rows}
        web = {r[0] for r in q("SELECT verse FROM verse WHERE edition_id='WEB' AND book_id=? AND chapter=1", book)}
        print(f"[verses] Swete {len(sw)}  WEB {len(web)}  missing {sorted(web - sw)}  extra {sorted(sw - web)}"
              f"  | TEI verse divs {len(tei)} missing {sorted(web - set(tei))}")

        # 2. faithfulness to TEI source
        diffs = []
        for v in sorted(sw):
            a = [norm_greek(w) for w in tei.get(v, "").split()]
            a = [w for w in a if w]
            b = [r["norm"] for r in rows if r["verse"] == v]
            b = [norm_greek(w) for w in b if norm_greek(w)]
            if a != b:
                diffs.append((v, len(a), len(b)))
        print(f"[source] verses where tokens != TEI main text (notes removed): {len(diffs)} {diffs[:8]}")

        # 3. encoding of the display column
        latin = [(r["verse"], r["text"]) for r in rows if any(script_of(c) == "latin" for c in r["text"])]
        latin_w = [(r["verse"], r["word"]) for r in rows if any(script_of(c) == "latin" for c in r["word"])]
        junk = [(r["verse"], r["text"]) for r in rows if "U+" in r["text"]]
        print(f"[chars ] Latin letters in 'text' col: {len(latin)} {latin[:6]}")
        print(f"         Latin letters in repaired 'word' col: {len(latin_w)} {latin_w[:6]}; 'U+' artefacts: {junk[:4]}")
        caps = sum(1 for r in rows if r["word"].isupper() and len(r["word"]) > 1)
        print(f"         unaccented ALL-CAPS words (lost accents/breathings): {caps}")

        # 4. morphology
        src = Counter(r["src"] for r in rows)
        bad = [(r["verse"], r["word"], r["pos"], r["parse"]) for r in rows if not valid_parse(r["pos"], r["parse"])]
        fallback = [(r["verse"], r["word"]) for r in rows if r["src"] == "morpheus-proper"]
        fb_caps = [w for _, w in fallback if w.isupper()]
        fb_lower = [(v, w) for v, w in fallback if w[:1].islower()]
        print(f"[morph ] sources {dict(src)}; invalid parse codes: {len(bad)} {bad[:5]}")
        print(f"         proper-noun fallbacks: {len(fallback)} = {len(fb_caps)} ALL-CAPS, "
              f"{len(fb_lower)} lowercase {fb_lower[:8]}, rest capitalised names")
        print(f"         fallback words: {[w for _, w in fallback]}")
        real = [r for r in rows if r["src"] == "morpheus"]
        hit = sum(norm_greek(r["lemma"]) in strongs_lemmas for r in real)
        print(f"[lexicon] analysed lemmas matching a Strong's Greek lemma: {hit}/{len(real)}"
              f"  e.g. misses {sorted({r['lemma'] for r in real if norm_greek(r['lemma']) not in strongs_lemmas})[:12]}")

        # 5. agreement with Brenton (same Vaticanus tradition): OCR / textual noise
        print("[vs Brenton] per-verse word agreement (normalized):")
        scores = []
        for v in sorted(sw & web):
            br = [r[0] for r in q("""SELECT t.surface_norm FROM token t JOIN verse x ON x.id=t.verse_id
                       WHERE x.edition_id='LXX-BRENTON' AND x.book_id=? AND x.chapter=1 AND x.verse=? ORDER BY t.position""", book, v)]
            swv = [r["norm"] for r in rows if r["verse"] == v]
            swv = [norm_greek(w) for w in swv]
            sm = difflib.SequenceMatcher(None, br, swv, autojunk=False)
            changes = [(br[i1:i2], swv[j1:j2]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]
            scores.append((sm.ratio(), v, changes))
        avg = sum(s for s, _, _ in scores) / len(scores)
        print(f"         mean agreement {avg:.3f}; verses < 0.90: {[(v, round(s, 2)) for s, v, _ in scores if s < .9]}")
        for s, v, ch in sorted(scores)[:4]:
            print(f"         {book} 1:{v} ({s:.2f}) Brenton→Swete: {ch[:5]}")

        # 6. spot check
        print("[sample] first 2 verses, word | lemma | pos parse | source")
        for r in rows:
            if r["verse"] <= 2:
                print(f"         1:{r['verse']} {r['text']:<14} {r['lemma']:<14} {r['pos']} {r['parse']} {r['src']}")


if __name__ == "__main__":
    main()
