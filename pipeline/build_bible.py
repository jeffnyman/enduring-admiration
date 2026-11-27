#!/usr/bin/env python3
"""Full-Bible build -> db/bible.db, then a verification report.

Editions
  WEB          World English Bible, all 81 books (Protestant, Catholic, Orthodox canons)
  WLC          Hebrew OT (MorphHB), 39 books, lemma + morphology
  LXX-SWETE    Septuagint (Swete) text + Morpheus lemma/morphology (Daniel, Susanna, Bel:
               Theodotion; 2 Esdras split into Ezra/Nehemiah; Odes 12 = Prayer of Manasseh)
  LXX-BRENTON  Septuagint (Brenton), text only, used as a cross-check for Swete
  SBLGNT       Greek NT + STEP TAGNT lemma/morphology

Every verse is mapped to TVTMS Standard numbering (see bibleingest/tvtms.py) plus
verified overrides (versification_overrides.tsv). Nothing is hard-coded Scripture:
checks use counts, Unicode ranges, cross-edition agreement and documented
versification facts (e.g. Hebrew Gen 32:1 = English 31:55).

Usage:  .venv/bin/python pipeline/build_bible.py      (writes data/build_report.md too)
"""
import bisect
import difflib
import io
import json
import re
import sqlite3
import sys
import time
import unicodedata as ud
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import sample_ingest as S
from bibleingest import greek, morphhb, oshb_morph, sblgnt, swete, tahot, tvtms, usfm
from bibleingest.books import BOOKS, ORD
from bibleingest.textnorm import norm_greek, norm_hebrew, script_of

ROOT = S.ROOT
DB = ROOT / "db" / "bible.db"
REPORT = ROOT / "data" / "build_report.md"
HERE = Path(__file__).resolve().parent
OSIS_TO_USFM = {b[1]: b[0] for b in BOOKS}
NT = [b[0] for b in BOOKS if b[3] == "NT"]


def step_abbr(code):                      # MAT -> Mat, 1CO -> 1Co (STEP/TAGNT book names)
    return code[:2] + code[2:].lower() if code[0].isdigit() else code[0] + code[1:].lower()


# ----------------------------------------------------------------------------- sources
MORPHHB_BOOKS = ("Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr 2Chr Ezra Neh Esth "
                 "Job Ps Prov Eccl Song Isa Jer Lam Ezek Dan Hos Joel Amos Obad Jonah Mic Nah Hab "
                 "Zeph Hag Zech Mal").split()
SWETE_FILES = [l.strip() for l in (HERE / "swete_tei_files.txt").read_text().splitlines()
               if l.strip() and not l.startswith("#")]
# QuantForge books.tsv: code, abbreviation, tlg id   (abbr -> how we store it)
SWETE_BOOKS = [
    (1, "Gen", "tlg001", "GEN"), (2, "Exod", "tlg002", "EXO"), (3, "Lev", "tlg003", "LEV"),
    (4, "Num", "tlg004", "NUM"), (5, "Deut", "tlg005", "DEU"), (6, "Josh", "tlg006", "JOS"),
    (7, "Judg", "tlg008", "JDG"), (8, "Ruth", "tlg010", "RUT"), (9, "1Kgdms", "tlg011", "1SA"),
    (10, "2Kgdms", "tlg012", "2SA"), (11, "3Kgdms", "tlg013", "1KI"), (12, "4Kgdms", "tlg014", "2KI"),
    (13, "1Chr", "tlg015", "1CH"), (14, "2Chr", "tlg016", "2CH"), (15, "1Esd", "tlg017", "1ES"),
    (16, "2Esd", "tlg018", "EZR+NEH"), (17, "Esth", "tlg019", "ESG"), (18, "Jdt", "tlg020", "JDT"),
    (19, "Tob", "tlg021", "TOB"), (20, "1Macc", "tlg023", "1MA"), (21, "2Macc", "tlg024", "2MA"),
    (22, "3Macc", "tlg025", "3MA"), (23, "4Macc", "tlg026", "4MA"), (24, "Ps", "tlg027", "PSA+PS2"),
    (25, "Odes", "tlg028", "ODES>MAN"), (26, "Prov", "tlg029", "PRO"), (27, "Song", "tlg031", "SNG"),
    (28, "Job", "tlg032", "JOB"), (29, "Wis", "tlg033", "WIS"), (30, "Sir", "tlg034", "SIR"),
    (31, "PssSol", "tlg035", None), (32, "Hos", "tlg036", "HOS"), (33, "Amos", "tlg037", "AMO"),
    (34, "Mic", "tlg038", "MIC"), (35, "Joel", "tlg039", "JOL"), (36, "Obad", "tlg040", "OBA"),
    (37, "Jonah", "tlg041", "JON"), (38, "Nah", "tlg042", "NAM"), (39, "Hab", "tlg043", "HAB"),
    (40, "Zeph", "tlg044", "ZEP"), (41, "Hag", "tlg045", "HAG"), (42, "Zech", "tlg046", "ZEC"),
    (43, "Mal", "tlg047", "MAL"), (44, "Isa", "tlg048", "ISA"), (45, "Jer", "tlg049", "JER"),
    (46, "Bar", "tlg050", "BAR"), (47, "Lam", "tlg051", "LAM"), (48, "EpJer", "tlg052", "LJE"),
    (49, "Ezek", "tlg053", "EZK"), (50, "Sus", "tlg054", None), (51, "SusTh", "tlg055", "SUS"),
    (52, "Dan", "tlg056", None), (53, "DanTh", "tlg057", "DAG"), (54, "Bel", "tlg058", None),
    (55, "BelTh", "tlg059", "BEL"),
]
SKIPPED_SWETE = {"PssSol": "Psalms of Solomon: not canonical in any tradition covered"}
# The Old Greek (pre-Theodotion) Daniel, Susanna and Bel: a separate optional edition
OLD_GREEK = {"Dan": "DAG", "Sus": "SUS", "Bel": "BEL"}
SBLGNT_SHA = "d7f35adca9ec410e1d1499c63b4dd989d76c8d4d"
CATENA_SHA = "aebb0f6b2b313fd3732dab9b7f28714fbe967f40"
SBLGNT_BOOKS = ("Matt Mark Luke John Acts Rom 1Cor 2Cor Gal Eph Phil Col 1Thess 2Thess 1Tim 2Tim Titus Phlm "
                "Heb Jas 1Pet 2Pet 1John 2John 3John Jude Rev").split()


def sources():
    src = dict(S.SOURCES)
    src["oshb-morphhb"] = dict(src["oshb-morphhb"], title="Open Scriptures Hebrew Bible (WLC 4.20 + morphology)",
                               files={b: f"{S.GH}/openscriptures/morphhb/{S.MORPHHB_SHA}/wlc/{b}.xml"
                                      for b in MORPHHB_BOOKS})
    src["oshb-morphhb"].pop("url"), src["oshb-morphhb"].pop("file")
    tag = f"{S.STEP}/Translators%20Amalgamated%20OT%2BNT/TAGNT%20{{}}%20-%20Translators%20Amalgamated%20Greek%20NT%20-%20STEPBible.org%20CC-BY.txt"
    src["step-tagnt"] = dict(src["step-tagnt"], title="STEPBible TAGNT (Matthew-Revelation)",
                             files={"Mat-Jhn": tag.format("Mat-Jhn"), "Act-Rev": tag.format("Act-Rev")})
    src["step-tagnt"].pop("url"), src["step-tagnt"].pop("file")
    tah = f"{S.STEP}/Translators%20Amalgamated%20OT%2BNT/TAHOT%20{{}}%20-%20Translators%20Amalgamated%20Hebrew%20OT%20-%20STEPBible.org%20CC%20BY.txt"
    src["step-tahot"] = dict(
        title="STEPBible TAHOT (Translators Amalgamated Hebrew OT): in-context glosses",
        files={k: tah.format(k) for k in ("Gen-Deu", "Jos-Est", "Job-Sng", "Isa-Mal")},
        version=S.STEP_SHA, license="CC-BY-4.0",
        attribution="Translators Amalgamated Hebrew OT, STEPBible.org / Tyndale House Cambridge (CC BY 4.0)")
    by_tlg = {f.split("__")[0]: f for f in SWETE_FILES}
    wanted = lambda abbr, tgt: tgt or abbr in OLD_GREEK
    src["f1k-swete"] = dict(src["f1k-swete"], files={
        abbr: f"{S.QF}/swete-tei/{by_tlg[tlg]}" for _, abbr, tlg, tgt in SWETE_BOOKS if wanted(abbr, tgt)})
    src["qf-lxx-morph"] = dict(src["qf-lxx-morph"], files={
        abbr: f"{S.QF}/morph-morpheus/{code:03d}-{abbr}.txt" for code, abbr, _, tgt in SWETE_BOOKS if wanted(abbr, tgt)})
    src["openbible-xref"] = dict(
        title="OpenBible.info cross references", url="https://a.openbible.info/data/cross-references.zip",
        file="cross-references.zip", version=None, license="CC-BY",
        attribution="Cross references from OpenBible.info (CC BY), ranked by user votes")
    # the official SBLGNT (eBible's USFM conversion broke words around footnotes)
    sbl = f"{S.GH}/LogosBible/SBLGNT/{SBLGNT_SHA}/data"
    src.pop("ebible-grcsbl")
    src["sblgnt"] = dict(
        title="SBL Greek New Testament (official source files, with apparatus)",
        files={**{b: f"{sbl}/sblgnt/xml/{b}.xml" for b in SBLGNT_BOOKS},
               **{f"{b}.app": f"{sbl}/sblgntapp/xml/{b}.xml" for b in SBLGNT_BOOKS}},
        version=SBLGNT_SHA, license="CC-BY-4.0",
        attribution="SBL Greek New Testament. Copyright © 2010 Society of Biblical Literature and Logos "
                    "Bible Software. CC BY 4.0.")
    # commentaries (see bibleingest/commentary.py)
    src["tyndale-osn"] = dict(
        title="Tyndale Open Study Notes (release 1.25)",
        url="https://tyndaleopenresources.com/wp-content/themes/tyndale-openresources/files/tyndale_open-studynotes.zip",
        file="tyndale_open-studynotes.zip", version="1.25", license="CC-BY-SA-4.0",
        attribution="Adapted from Tyndale Open Study Notes. The original work by Tyndale House Publishers is "
                    "available for free at http://www.tyndaleopenresources.com. Changes: references converted to "
                    "this reader's verse numbering and links; markup simplified. Copyright (C) 2022 Tyndale House "
                    "Publishers, CC BY-SA 4.0.")
    src["uw-tn"] = dict(
        title="Translation Notes (unfoldingWord en_tn, release v92)",
        url="https://git.door43.org/unfoldingWord/en_tn/archive/v92.zip", file="en_tn-v92.zip", version="v92",
        license="CC-BY-SA-4.0",
        attribution="The original work by unfoldingWord is available from https://www.unfoldingword.org/utn "
                    "(CC BY-SA 4.0). Changes: notes linked to the words of this reader's Hebrew (WLC) and Greek "
                    "(SBLGNT) texts and to its verse numbering; Markdown converted; links to translationAcademy "
                    "articles removed; notes on translation technique marked so they can be hidden.")
    src["catena-lemtom"] = dict(
        title="Catena Aurea (Newman translation), OSIS edition by Tom Lemmens",
        url=f"{S.GH}/lemtom/catena/{CATENA_SHA}/catena.xml", file="catena.xml", version=CATENA_SHA,
        license="Public Domain (CC0 1.0 for the edition)",
        attribution="Thomas Aquinas, Catena Aurea, translated under J. H. Newman (1841–45), public domain; OSIS "
                    "edition by Tom Lemmens, github.com/lemtom/catena (CC0 1.0).")
    src["crosswire-kd"] = dict(
        title="Keil & Delitzsch, Biblical Commentary on the Old Testament (CrossWire SWORD module KD 2.0)",
        url="https://www.crosswire.org/ftpmirror/pub/sword/packages/rawzip/KD.zip", file="KD.zip", version="2.0",
        license="Public Domain (transcription from Wikisource, CC BY-SA 4.0)",
        attribution="C. F. Keil and F. Delitzsch, Biblical Commentary on the Old Testament (T&T Clark), public "
                    "domain; transcription from Wikisource (CC BY-SA 4.0) as packaged in the CrossWire SWORD "
                    "module KD. Its Hebrew is unpointed and has transcription errors.")
    src["ebible-kjv"] = dict(
        title="King James Version, USFM (used only for the KJV verse counts that index the K&D module)",
        url="https://ebible.org/Scriptures/eng-kjv2006_usfm.zip", file="eng-kjv2006_usfm.zip", version=None,
        license="Public Domain", attribution="King James Version, eBible.org (public domain)")
    return src


NOTES = {
    "LXX-SWETE": S.EDITION_NOTES["LXX-SWETE"] + " Daniel/Susanna/Bel = Theodotion. 2 Esdras 1-10 stored "
                 "as Ezra, 11-23 as Nehemiah 1-13. Psalm 151 stored as PS2. Prayer of Manasseh = Odes 12. "
                 "Esther additions: Swete's own numbering (A = chapter 0). verse.source_ref keeps Swete's refs.",
    "LXX-BRENTON": S.EDITION_NOTES["LXX-BRENTON"] + " 2 Esdras split into Ezra/Nehemiah; Psalm 151 stored as PS2.",
    "SBLGNT": "Official SBLGNT source files with apparatus. Lemma/morph/Strong's aligned from STEP TAGNT, "
              "including the SBL readings TAGNT records as variants.",
}


# ----------------------------------------------------------------------------- book plans
def split_book(source_book, chapters: dict):
    """Yield (stored_book, stored_chapter, source_chapter_label, verses) for one source book."""
    for ch, verses in chapters.items():
        if source_book in ("EZR+NEH", "2Esd", "EZR23"):
            yield ("EZR", ch, ch, verses) if ch <= 10 else ("NEH", ch - 10, ch, verses)
        elif source_book in ("PSA+PS2",):
            yield ("PSA", ch, ch, verses) if ch <= 150 else ("PS2", ch - 150, ch, verses)
        elif source_book == "ODES>MAN":               # Swete Odes: only the Prayer of Manasseh
            if ch == SWETE_MANASSEH_ODE:
                yield ("MAN", 1, ch, verses)
        else:
            yield (source_book, ch, ch, verses)


# Swete's Odes are numbered differently from Rahlfs (Ode 4 is split into iva/ivb); the
# Prayer of Manasseh is Swete's Ode 8. Verified at build time against Brenton's MAN.
SWETE_MANASSEH_ODE = 8


def canon_book(book, ch, v):
    """Esther on the canonical grid: the shared text (1:1-10:3) under EST so Hebrew and
    Greek Esther align; every Greek addition (10:4-16:24, Standard/Vulgate numbering)
    under ESG. TVTMS writes the additions as either Est.11-16 or Esg.11-16."""
    if book in ("EST", "ESG"):
        return "ESG" if ch > 10 or (ch == 10 and v > 3) else "EST"
    return book


def align_by_text(words, report, target, ref, book, ref_book=None, select=lambda std: True, why=""):
    """Map each `target` verse of `book` to the Standard refs of the `ref` edition verse whose
    text matches it best (similarity >= 0.5). Used only where the two Greek editions divide
    verses differently and TVTMS's positional rules can't see it."""
    sim = lambda a, b: difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
    tgt = {k: ws for k, ws in words.items() if k[0] == target and k[1] == book}
    rf = {k: ws for k, ws in words.items() if k[0] == ref and k[1] == (ref_book or book)}
    rmap = S.MAPS[(ref, ref_book or book)]
    new = defaultdict(list)
    for k, ws in rf.items():
        stds = [r for r, *_ in rmap[k[2:]] if str(r.ch).isdigit() and select(r)]
        if not stds:
            continue
        best = max(tgt, key=lambda b: sim(ws, tgt[b]))
        if sim(ws, tgt[best]) >= 0.5:
            new[best].extend(stds)
    m = S.MAPS[(target, book)]
    for tk, stds in new.items():
        uniq = list({(r.book, r.ch, r.v): r for r in stds}.values())
        m[tk[2:]] = [(r, "merged" if len(uniq) > 1 else "renumbered", f"aligned to {ref} text ({why})", None)
                     for r in uniq]
    report.setdefault("text_aligned", {})[(target, book)] = len(new)


# Spelling differences that are real Vaticanus/Swete orthography, not OCR errors: ει/ι and ε/αι
# (itacism), ο/ω, unassimilated ν before labials/velars, aspirated/unaspirated stops (ἔφιδε/ἔπιδε,
# ἐφ’/ἐπ’), and movable ν.
_ORTHO = [("ει", "ι"), ("αι", "ε"), ("ω", "ο"), ("γκ", "νκ"), ("γγ", "νγ"), ("γχ", "νχ"), ("γξ", "νξ"),
          ("μπ", "νπ"), ("μβ", "νβ"), ("μφ", "νφ"), ("μψ", "νψ"), ("μμ", "νμ"), ("λλ", "νλ"),
          ("φ", "π"), ("θ", "τ"), ("χ", "κ")]


def _orthographic(a, b):
    for x, y in _ORTHO:
        if a.replace(x, y) == b.replace(x, y):
            return True
    return a + "ν" == b or b + "ν" == a


def _one_edit(a, b):
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    a, b = sorted((a, b), key=len)
    return any(b[:i] + b[i + 1:] == a for i in range(len(b)))


def correct_swete_ocr(units, report):
    """Correct clear OCR errors in the Swete transcription, conservatively. A word is corrected
    only when (1) Morpheus could not analyse it, (2) Brenton's aligned word differs by exactly one
    letter, (3) that form is attested elsewhere in Swete as an analysed word (2+ times), and
    (4) the difference is not a known Vaticanus spelling pattern. The OCR form is kept."""
    sim = lambda a, b: difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    analysed, surfaces, tags = Counter(), defaultdict(Counter), defaultdict(Counter)
    for (ed, book), items in units.items():
        if ed != "LXX-SWETE":
            continue
        for *_, (toks, _ref) in items:
            for t in toks:
                tag = t.get("tag")
                if tag and tag["src"] == "morpheus" and not tag["code"].startswith("NP"):
                    analysed[t["surface_norm"]] += 1
                    surfaces[t["surface_norm"]][t["surface"].lower()] += 1
                    tags[t["surface_norm"]][(tag["lemma"], tag["code"])] += 1
    brenton = defaultdict(list)
    for (ed, book), items in units.items():
        if ed == "LXX-BRENTON":
            for ch, v, part, (pv, toks) in items:
                for r, *_ in S.MAPS[(ed, book)].get((str(ch), v, part), []):
                    brenton[(r.book, str(r.ch), r.v)].extend(t["surface_norm"] for t in toks)
    fixed, skipped_ortho = [], 0
    for (ed, book), items in units.items():
        if ed != "LXX-SWETE":
            continue
        for ch, v, part, (toks, _ref) in items:
            ref_words = [w for r, *_ in S.MAPS[(ed, book)].get((str(ch), v, part), [])
                         for w in brenton.get((r.book, str(r.ch), r.v), [])]
            if not ref_words:
                continue
            norms = [t["surface_norm"] for t in toks]
            for op, i1, i2, j1, j2 in sim(norms, ref_words):
                if op != "replace" or i2 - i1 != j2 - j1:
                    continue
                for k in range(i2 - i1):
                    t, target = toks[i1 + k], ref_words[j1 + k]
                    tag = t.get("tag")
                    unanalysed = not tag or (tag["code"].startswith("NP") and t["surface"][:1].islower())
                    if not unanalysed or analysed[t["surface_norm"]] or analysed[target] < 2:
                        continue
                    if not _one_edit(t["surface_norm"], target):
                        continue
                    if _orthographic(t["surface_norm"], target):
                        skipped_ortho += 1
                        continue
                    new = surfaces[target].most_common(1)[0][0]
                    if t["surface"][:1].isupper():
                        new = new[:1].upper() + new[1:]
                    # keep a grave accent (mid-sentence oxytone) where the transcription had one
                    if "\u0300" in ud.normalize("NFD", t["surface"]):
                        nfd = ud.normalize("NFD", new)
                        k = nfd.rfind("\u0301")
                        if k >= 0:
                            new = ud.normalize("NFC", nfd[:k] + "\u0300" + nfd[k + 1:])
                    lemma, code = tags[target].most_common(1)[0][0]
                    fixed.append((book, ch, v, t["surface"], new))
                    t["ocr_original"], t["surface"], t["surface_norm"] = t["surface"], new, target
                    t["tag"], t["tag_status"] = {"lemma": lemma, "code": code, "src": "morpheus"}, "inferred"
    report["ocr_fixed"], report["ocr_skipped_orthographic"] = fixed, skipped_ortho


def rule_book(book):
    """TVTMS keys Greek Daniel (with Prayer of Azariah, Susanna, Bel) under Dan."""
    return "DAN" if book == "DAG" else book


# ----------------------------------------------------------------------------- inserts
class Writer:
    """Bulk inserts with explicit ids (much faster than lastrowid round trips)."""

    def __init__(self, con):
        self.con = con
        self.tok_id = self.morph_id = 0
        self.toks, self.morphs = [], []

    def tokens(self, verse_id, tokens, scheme):
        for pos, t in enumerate(tokens, 1):
            self.tok_id += 1
            gloss_kind = t.get("gloss_kind") or ("contextual" if t.get("gloss") else None)
            self.toks.append((self.tok_id, verse_id, pos, t.get("variant", ""), t.get("variant_group"),
                              t["surface"], t["surface_norm"], t.get("leading", ""), t.get("trailing", ""),
                              t.get("source_ref"), t.get("lemma_raw"), t.get("morph_raw"),
                              scheme if t.get("morphemes") else None, t.get("gloss"), gloss_kind,
                              t.get("translit"), t.get("tag_status", "none"), t.get("ocr_original")))
            norm = norm_hebrew if scheme == "oshb" else norm_greek
            for m in t.get("morphemes", []):
                self.morph_id += 1
                self.morphs.append((self.morph_id, self.tok_id, m["position"], m["role"], m["surface"],
                                    norm(m["surface"]), m.get("lemma"), m["strongs"], m["strongs_ext"],
                                    m["morph_code"], m.get("gloss")))
        if len(self.toks) > 50000:
            self.flush()

    def flush(self):
        self.con.executemany("INSERT INTO token (id, verse_id, position, variant, variant_group, surface,"
                             " surface_norm, leading, trailing, source_ref, lemma_raw, morph_raw, morph_scheme,"
                             " gloss, gloss_kind, translit, tag_status, ocr_original)"
                             " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             self.toks)
        self.con.executemany("INSERT INTO morpheme (id, token_id, position, role, surface, surface_norm, lemma,"
                             " strongs, strongs_ext, morph_code, gloss) VALUES (?,?,?,?,?,?,?,?,?,?,?)", self.morphs)
        self.toks, self.morphs = [], []


def verse_row(con, edition, book, ch, v, text, search, *, part="", verse_end=None, rich=None, para=None,
              heading=None, break_after=None, source_ref=None):
    vid = S.insert_verse(con, edition, book, ch, v, text, search, rich, para, heading, break_after,
                         part, verse_end)
    if source_ref:
        con.execute("UPDATE verse SET source_ref=? WHERE id=?", (source_ref, vid))
    return vid


# ----------------------------------------------------------------------------- build
def build(report):
    t0 = time.time()
    con = S.build_db(DB, "full")
    con.commit()                                  # PRAGMAs below can't run inside a transaction
    con.execute("PRAGMA synchronous = OFF")
    con.execute("PRAGMA journal_mode = MEMORY")
    data = S.load_sources(con, sources(), NOTES, sblgnt_source="sblgnt")
    con.execute("INSERT INTO edition VALUES (?,?,?,?,?,?,?,?,?)", (
        "LXX-SWETE-OG", "Septuagint, Old Greek Daniel (Swete)", "grc", "ltr", "original", "lxx", "f1k-swete",
        "qf-lxx-morph", "The Old Greek translation of Daniel, Susanna and Bel, which churches replaced with "
        "Theodotion's version (the main Septuagint column). Swete prints both. Lemma/morphology machine-generated."))
    report["t_download"] = time.time() - t0

    # Lexicons first: LXX Strong's/LSJ lookups need them
    S.load_lexicons(con, data, report)
    finders = S.lxx_strongs_finders(con)
    # Septuagint gloss line: LSJ's short gloss (dictionary, not in context)
    lsj_by_key, lsj_by_lemma = {}, {}
    for ext, base, lemma, sd in con.execute(
            """SELECT ls.strongs_ext, ls.strongs, le.lemma, le.short_def FROM lexicon_strongs ls
               JOIN lexicon_entry le ON le.id = ls.entry_id WHERE le.lexicon_id = 'lsj' AND le.short_def IS NOT NULL"""):
        for k in (ext, base):
            if k:
                lsj_by_key.setdefault(k, sd)
        lsj_by_lemma.setdefault(lemma, sd)

    z = lambda sid: zipfile.ZipFile(io.BytesIO(data[sid]))
    web_z, br_z = z("ebible-eng-web"), z("ebible-grcbrent")

    def usfm_books(zf, skip=("FRT", "GLO", "INT", "BAK", "OTH", "XXA")):
        for n in sorted(zf.namelist()):
            if n.endswith(".usfm"):
                t = zf.read(n).decode("utf-8-sig")
                code = re.search(r"\\id\s+(\S+)", t)[1]
                if code not in skip:
                    yield code, t

    # --- collect every edition's verses: units[(edition, stored_book)] = [(ch, v, part, payload)]
    units = defaultdict(list)
    inv = defaultdict(tvtms.Inventory)                     # one per edition, all books
    words = {}                                             # LXX word lists for the cross-check

    def add(edition, book, ch, v, part, payload, nwords, verse_end=None, title=False):
        units[(edition, book)].append((ch, v, part, payload))
        inv[edition].add(book, ch, v, nwords, part, verse_end)
        if title and v == 1:
            inv[edition].titles.add((book, str(ch)))
        if book == "PS2" and edition.startswith("LXX"):
            # TVTMS recognises Greek Psalm numbering partly by "Psa.151:1=Exist"
            inv[edition].add("PSA", 151, v, nwords, part)

    for code, t in usfm_books(web_z):
        for ch, verses in usfm.parse_book(t).items():
            for v in verses:
                add("WEB", code, ch, v["verse"], v["part"], v, len(v["text"].split()), v["verse_end"],
                    v.get("title_before"))

    for code, t in usfm_books(br_z):
        src_book = {"EZR": "EZR+NEH", "PSA": "PSA+PS2"}.get(code, code)
        for book, ch, src_ch, verses in split_book(src_book, usfm.parse_book(t)):
            usfm.ordinal_parts(verses)
            for v in verses:
                toks = greek.tokenize(v["text"])
                moved = (book, ch) != (code, src_ch) or "brenton_part" in v
                v["source_ref"] = f"{code} {src_ch}:{v['verse']}{v.get('brenton_part', v['part'])}" if moved else None
                add("LXX-BRENTON", book, ch, v["verse"], v["part"], (v, toks), len(toks), v["verse_end"])
                words[("LXX-BRENTON", book, str(ch), v["verse"], v["part"])] = [x["surface_norm"] for x in toks]

    tahot_rows = {}
    for k in data["step-tahot"]:
        tahot_rows.update(tahot.parse(data["step-tahot"][k].decode("utf-8-sig")))
    report["tahot_log"] = Counter()
    for osis in MORPHHB_BOOKS:
        book = OSIS_TO_USFM[osis]
        for ch, verses in morphhb.parse_book(data["oshb-morphhb"][osis].decode("utf-8")).items():
            tahot.attach(verses, tahot_rows, step_abbr(book), ch, report["tahot_log"])
            for v in verses:
                add("WLC", book, ch, v["verse"], "", v, sum(1 for t in v["tokens"] if t["variant"] != "qere"))

    tagnt = {k: data["step-tagnt"][k].decode("utf-8-sig") for k in data["step-tagnt"]}
    for osis in SBLGNT_BOOKS:
        code = OSIS_TO_USFM[osis]
        rows_by_ch = greek.parse_tagnt_book(tagnt["Mat-Jhn" if ORD[code] <= ORD["JHN"] else "Act-Rev"],
                                            step_abbr(code))
        book = sblgnt.parse_book(data["sblgnt"][osis].decode("utf-8"), data["sblgnt"][f"{osis}.app"].decode("utf-8"))
        report["sbl_total"] = report.get("sbl_total", 0) + sum(len(v["tokens"]) for vs in book.values() for v in vs)
        for ch, verses in book.items():
            report.setdefault("sbl_unaligned", []).extend(
                (code, ch, vn, w) for vn, w in greek.align(verses, rows_by_ch.get(ch, [])))
            for v in verses:
                add("SBLGNT", code, ch, v["verse"], v["part"], v, len(v["tokens"]), v["verse_end"])

    report["swete_log"] = Counter()
    plan = [("LXX-SWETE", abbr, target) for _, abbr, _, target in SWETE_BOOKS if target]
    plan += [("LXX-SWETE-OG", abbr, target) for abbr, target in OLD_GREEK.items()]
    for edition, abbr, target in plan:
        tei = swete.book_text(data["f1k-swete"][abbr].decode("utf-8"), report["swete_log"])
        rows = list(swete.morph_rows(data["qf-lxx-morph"][abbr].decode("utf-8")))
        index = swete.book_index(rows)
        rows_by_ch = defaultdict(list)
        for r in rows:
            rows_by_ch[r["chapter"]].append(r)
        chapters = {}
        for ch, raw in tei.items():
            if ch == "prologue":
                key = 0                                   # Esther Addition A
            elif isinstance(ch, int):
                key = ch
            else:
                report["swete_log"][f"non-numeric chapter skipped ({abbr} {ch})"] += 1
                continue
            if (0, "") in raw and target != "PSA+PS2":
                report["swete_log"]["pre-verse text dropped (not a Psalm title)"] += 1
                raw = {k: t for k, t in raw.items() if k != (0, "")}
            verses = swete.clean_chapter(raw, report["swete_log"])
            swete.attach(verses, rows_by_ch.get(key, []), index, report["swete_log"])
            chapters[key] = verses
        for book, ch, src_ch, verses in split_book(target, chapters):
            for (vn, part), toks in verses.items():
                moved = book != target or ch != src_ch or src_ch == 0
                src_ref = f"{abbr} {'prologue' if src_ch == 0 else src_ch}:{vn}{part}" if moved else None
                add(edition, book, ch, vn, part, (toks, src_ref), len(toks))
                if vn == 0:                                   # Psalm title printed before verse 1
                    inv[edition].titles.add((book, str(ch)))
                if edition == "LXX-SWETE":
                    words[(edition, book, str(ch), vn, part)] = [x["surface_norm"] for x in toks]
    report["words"] = words
    report["t_parse"] = time.time() - t0

    # --- versification: TVTMS per edition/book, then verified overrides
    last = lambda b, ch: inv["WEB"].last(b, ch)
    rules, report["tvtms_stats"] = tvtms.parse_expanded(data["step-tvtms"].decode("utf-8"), last)
    prefer = {"WEB": ("Eng-KJV", "Eng-NRSV", "AllBibles"), "SBLGNT": ("Eng-KJV", "AllBibles"),
              "WLC": ("Hebrew", "AllBibles"), "LXX-SWETE": ("Greek", "AllBibles"),
              "LXX-BRENTON": ("Greek", "AllBibles"), "LXX-SWETE-OG": ("Greek", "AllBibles")}
    report["tvtms"] = {}
    for edition, book in units:
        rb = rule_book(book)
        view = inv[edition].view({rb: book} if rb != book else {})
        S.MAPS[(edition, book)], report["tvtms"][(edition, book)] = tvtms.map_edition(
            rules, view, rb, prefer[edition])
    tvtms.load_overrides(S.OVERRIDES, S.MAPS, report)
    # Esther Additions C-F: Brenton merges verses, so TVTMS's positional mapping drifts; Swete
    # numbers each addition verse explicitly (TVTMS A-F table overrides) -> align Brenton to Swete.
    align_by_text(words, report, "LXX-BRENTON", "LXX-SWETE", "ESG",
                  select=lambda r: canon_book(r.book, int(r.ch), r.v) == "ESG" and (int(r.ch), r.v) > (13, 7),
                  why="Brenton divides Esther Additions C-F differently")
    # Letter of Jeremiah: Brenton = Standard Baruch 6 verse for verse; Swete prints the title as a
    # heading and divides 1:43-50 differently -> align Swete to Brenton.
    align_by_text(words, report, "LXX-SWETE", "LXX-BRENTON", "LJE",
                  why="Swete divides the Letter of Jeremiah differently")
    correct_swete_ocr(units, report)
    report["t_versify"] = time.time() - t0

    # --- write verses, maps, tokens
    w = Writer(con)
    codes = set()
    report["letter_chapter_skips"] = Counter()

    def map_it(vid, edition, book, ch, v, part):
        for std, relation, rule, note in S.MAPS[(edition, book)][(str(ch), v, part)]:
            if not str(std.ch).isdigit():
                report["letter_chapter_skips"][(edition, book)] += 1
                continue
            cb = canon_book(std.book, int(std.ch), std.v)
            cid = S.canon_verse_id(cb, int(std.ch), std.v)
            con.execute("INSERT OR IGNORE INTO canon_verse VALUES (?,?,?,?)", (cid, cb, int(std.ch), std.v))
            con.execute("INSERT OR IGNORE INTO verse_map VALUES (?,?,?,?,?)", (vid, cid, relation, rule, note))

    for (edition, book), items in sorted(units.items(), key=lambda x: (ORD[x[0][1]], x[0][0])):
        for ch, v, part, payload in items:
            try:
                if edition == "WEB":
                    vid = verse_row(con, "WEB", book, ch, v, payload["text"], payload["text"], part=part,
                                    verse_end=payload["verse_end"], rich=payload["runs"],
                                    para=payload["para_before"], heading=payload["heading_before"])
                    con.executemany("INSERT INTO verse_note (verse_id, kind, text) VALUES (?,?,?)",
                                    [(vid, k, t) for k, t in payload["notes"]])
                elif edition == "LXX-BRENTON":
                    pv, toks = payload
                    vid = verse_row(con, edition, book, ch, v, S.verse_text(toks),
                                    " ".join(t["surface_norm"] for t in toks), part=part,
                                    verse_end=pv["verse_end"], source_ref=pv["source_ref"])
                elif edition == "WLC":
                    toks = payload["tokens"]
                    vid = verse_row(con, edition, book, ch, v, S.verse_text(toks),
                                    " ".join(t["surface_norm"] for t in toks), break_after=payload["break_after"])
                    w.tokens(vid, toks, "oshb")
                    for t in toks:
                        if t.get("anomaly"):
                            report.setdefault("morphhb_anomalies", []).append((book, ch, v, t["anomaly"]))
                elif edition == "SBLGNT":
                    toks = payload["tokens"]
                    vid = verse_row(con, edition, book, ch, v, S.verse_text(toks),
                                    " ".join(t["surface_norm"] for t in toks), part=part,
                                    verse_end=payload["verse_end"], rich=payload["runs"],
                                    para=payload["para_before"])
                    con.executemany("INSERT INTO verse_note (verse_id, kind, text) VALUES (?,?,?)",
                                    [(vid, k, t) for k, t in payload["notes"]])
                    w.tokens(vid, toks, "step-greek")
                else:                                       # LXX-SWETE, LXX-SWETE-OG
                    toks, src_ref = payload
                    for t in toks:
                        if t.get("tag"):
                            codes.add(t["tag"]["code"])
                            t["lemma_raw"], t["morph_raw"] = t["tag"]["lemma"], t["tag"]["code"]
                            t["morphemes"] = [S.lxx_morpheme(t["tag"], t["surface"], finders)]
                            m = t["morphemes"][0]
                            g = lsj_by_key.get(m["strongs_ext"]) or lsj_by_key.get(m["strongs"]) or lsj_by_lemma.get(m["lemma"])
                            if g:
                                t["gloss"], t["gloss_kind"] = g, "lexical"
                    vid = verse_row(con, edition, book, ch, v, S.verse_text(toks),
                                    " ".join(t["surface_norm"] for t in toks), part=part, source_ref=src_ref)
                    w.tokens(vid, toks, "morphgnt")
            except sqlite3.IntegrityError as e:
                report.setdefault("duplicate_verses", []).append((edition, book, ch, v, part, str(e)))
                continue
            map_it(vid, edition, book, ch, v, part)
    w.flush()
    report["t_write"] = time.time() - t0

    # --- morphology codes (Greek NT: TEGMC; Hebrew: OSHB decoder; LXX: MorphGNT-style decoder)
    from bibleingest import lexicon
    con.executemany("INSERT OR IGNORE INTO morph_code VALUES (?,?,?,?,?)",
                    [("step-greek", r["code"], r["summary"], r["detail"], r["fields"])
                     for r in lexicon.step_morph_codes(data["step-tegmc"].decode("utf-8"))])
    report["oshb_unknown"], report["morphgnt_bad"] = [], []
    for (c,) in con.execute("SELECT DISTINCT morph_code FROM morpheme m JOIN token t ON t.id=m.token_id "
                            "WHERE t.morph_scheme='oshb'").fetchall():
        try:
            con.execute("INSERT INTO morph_code VALUES ('oshb',?,?,NULL,NULL)", (c, oshb_morph.decode(c)))
        except oshb_morph.Unknown as e:
            report["oshb_unknown"].append(str(e))
    for c in sorted(codes):
        try:
            con.execute("INSERT INTO morph_code VALUES ('morphgnt',?,?,NULL,NULL)", (c, swete.decode(c)))
        except ValueError:
            report["morphgnt_bad"].append(c)

    build_layouts(con, report)
    load_cross_refs(con, data, report)
    S.fill_lemmas(con)
    build_lemma_links(con, report)
    load_commentaries(con, data, report)
    con.execute("INSERT INTO verse_fts(verse_fts) VALUES ('rebuild')")
    con.execute("INSERT INTO schema_meta VALUES ('built_at', datetime('now'))")
    con.commit()
    con.execute("ANALYZE")
    con.commit()
    con.execute("VACUUM")
    report["t_total"] = time.time() - t0
    return con


# ----------------------------------------------------------------------------- cross-references
def load_cross_refs(con, data, report):
    """OpenBible.info references (English numbering = Standard) plus the WEB's own \\x notes."""
    canon = {(b, c, v): cid for cid, b, c, v in con.execute("SELECT id, book_id, chapter, verse FROM canon_verse")}
    osis = {b[1]: b[0] for b in BOOKS}
    stats = Counter()

    def ref(o):                                          # 'Rom.1.19' -> canon id
        b, c, v = o.split(".")
        return canon.get((osis.get(b), int(c), int(v)))

    rows = []
    with zipfile.ZipFile(io.BytesIO(data["openbible-xref"])) as z:
        text = z.read("cross_references.txt").decode("utf-8")
    for line in text.splitlines()[1:]:
        f = line.split("\t")
        if len(f) < 3:
            continue
        votes = int(f[2])
        if votes < 0:
            stats["openbible voted down (skipped)"] += 1
            continue
        lo, _, hi = f[1].partition("-")
        a, x, y = ref(f[0]), ref(lo), ref(hi or lo)
        if a and x and y and y >= x:
            rows.append((a, x, y, votes, "openbible"))
            stats["openbible"] += 1
        else:
            stats["openbible unresolved"] += 1
    # WEB notes: 'Exodus 23:13; Psalms 16:4', 'Isaiah 66:2; 66:10,13', 'See Job 5:1'
    names = {b[2]: b[0] for b in BOOKS} | {"Wisdom": "WIS", "Song of Solomon": "SNG"}
    pat = re.compile(r"(?:See\s+)?(?:((?:[1-4] )?[A-Z][A-Za-z ]+?)\s+)?(\d+):([\d,\- ]+)")
    for cid, text in con.execute("""SELECT cv.id, n.text FROM verse_note n JOIN verse v ON v.id = n.verse_id
                                    JOIN verse_map m ON m.verse_id = v.id JOIN canon_verse cv ON cv.id = m.canon_verse_id
                                    WHERE n.kind = 'crossref' AND v.edition_id = 'WEB'"""):
        book = None
        for part in re.split(r";\s*", text):
            m = pat.search(part)
            if not m:
                stats["web unparsed"] += 1
                continue
            book = names.get(m[1].strip(), book) if m[1] else book
            for piece in m[3].replace(" ", "").split(","):
                if not piece:
                    continue
                lo, _, hi = piece.partition("-")
                x = canon.get((book, int(m[2]), int(lo)))
                y = canon.get((book, int(m[2]), int(hi or lo)))
                if book and x and y:
                    rows.append((cid, x, y, None, "web"))
                    stats["web"] += 1
                else:
                    stats["web unresolved"] += 1
    con.executemany("INSERT OR IGNORE INTO cross_ref VALUES (?,?,?,?,?)", rows)
    report["xref"] = dict(stats)


# ----------------------------------------------------------------------------- commentaries
def load_commentaries(con, data, report):
    """Tyndale, unfoldingWord, Catena Aurea and Keil & Delitzsch. Their references use English
    (KJV-style) numbering, which is Standard numbering in nearly every verse; a reference is
    clamped to the nearest Standard verses inside the book. unfoldingWord notes are then linked
    to the WLC / SBLGNT words they quote."""
    from bibleingest import commentary as C
    t0, stats = time.time(), Counter()
    entries = (C.tyndale(data["tyndale-osn"], stats) + C.unfoldingword(data["uw-tn"], stats)
               + C.catena(data["catena-lemtom"].decode("utf-8"), stats)
               + C.keil_delitzsch(data["crosswire-kd"], C.kjv_counts(data["ebible-kjv"]), stats))
    con.executemany("INSERT INTO commentary VALUES (:id,:source_id,:title,:short_title,:author,:written,"
                    ":tradition,:description,:sort)", [dict(c, sort=i) for i, c in enumerate(C.COMMENTARIES)])
    ids = defaultdict(list)
    for (cid,) in con.execute("SELECT id FROM canon_verse ORDER BY id"):
        ids[cid // 1_000_000].append(cid)
    name = {b[0]: b[2] for b in BOOKS}

    def resolve(r):
        """Standard (first, last) verse ids for a reference: the first Standard verse at or after its
        start (staying in the same chapter) and the last at or before its end."""
        book, c1, v1, c2, v2 = r
        have = ids.get(ORD[book], [])
        lo, hi = S.canon_verse_id(book, c1, v1), S.canon_verse_id(book, c2, v2)
        i = bisect.bisect_left(have, lo)
        if i == len(have) or (have[i] // 1000) % 1000 != c1:
            return None
        a = have[i]
        b = have[bisect.bisect_right(have, hi) - 1] if hi >= a else a
        return a, max(a, b)

    def label(r):
        book, c1, v1, c2, v2 = r
        start = f"{name[book]} {c1}:{v1}" if v1 else f"{name[book]} {c1} (title)"
        if (c1, v1) == (c2, v2):
            return start
        return f"{start}–{v2}" if c1 == c2 else f"{start}–{c2}:{v2}"

    rows, refs, keep = [], [], []
    for e in entries:
        spans = [s for s in (resolve(r) for r in e.refs) if s]
        if not spans:
            stats[f"{e.commentary}: reference not in Standard numbering (skipped)"] += 1
            continue
        eid = len(rows) + 1
        minor = int(bool(e.commentary == "uw" and e.label and C.UW_MECHANICS.match(e.label)))
        rows.append((eid, e.commentary, e.kind, e.refs[0][0], label(e.refs[0]), e.title, e.label, e.quote,
                     minor, e.body, e.sort))
        refs += [(a, b, eid) for a, b in spans]
        keep.append((eid, e, spans))
        stats[f"{e.commentary} {e.kind}"] += 1
    con.executemany("INSERT INTO commentary_entry VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.executemany("INSERT OR IGNORE INTO commentary_ref VALUES (?,?,?)", refs)

    # link unfoldingWord quotes to words: WLC for the OT, SBLGNT for the NT
    words = defaultdict(list)                                  # canon id -> [(token, norm, variant)]
    for edition in ("WLC", "SBLGNT"):
        for cid, tid, norm, variant in con.execute(
                """SELECT m.canon_verse_id, t.id, t.surface_norm, t.variant FROM verse v
                   JOIN verse_map m ON m.verse_id = v.id JOIN token t ON t.verse_id = v.id
                   WHERE v.edition_id = ? ORDER BY m.canon_verse_id, v.id, t.position""", (edition,)):
            words[cid].append((tid, norm, variant))
    links = []
    for eid, e, spans in keep:
        if e.commentary != "uw" or not e.quote or e.occurrence == 0:
            continue
        a, b = spans[0]
        seen, toks = set(), []
        for cid in range(a, b + 1):
            for w in words.get(cid, ()):
                if w[0] not in seen:
                    seen.add(w[0]); toks.append(w)
        if not toks:
            continue
        lang = "heb" if e.refs[0][0] not in NT else "grk"
        found, how = match_quote(e.quote, e.occurrence, toks, lang)
        stats[f"uw {lang} words: {how}"] += 1
        links += [(t, eid) for t in found]
    con.executemany("INSERT OR IGNORE INTO commentary_word VALUES (?,?)", links)
    report["commentary"] = dict(stats)
    report["t_commentary"] = time.time() - t0


def match_quote(quote, occurrence, toks, lang):
    """Token ids for an unfoldingWord quote ('w1 w2 & w3', '…' also separates parts) in a verse's
    tokens. Exact runs first, trying the Ketiv and the Qere reading of the Hebrew; otherwise the
    words that can be found one by one, in order (reported as partial)."""
    norm = norm_hebrew if lang == "heb" else norm_greek
    parts = [[w for w in (norm(x) for x in re.split(r"[\s\u05be]+", p)) if w]
             for p in re.split(r"\s*(?:&|…)\s*", quote)]
    parts = [p for p in parts if p]
    if not parts:
        return [], "no words"
    best = []
    for skip in ("qere", "ketiv"):
        stream = [t for t in toks if t[2] != skip]
        norms = [t[1] for t in stream]

        def runs(p, start=0):
            return [i for i in range(start, len(norms) - len(p) + 1) if norms[i:i + len(p)] == p]

        starts = runs(parts[0])
        chosen = starts if occurrence < 0 else starts[occurrence - 1:occurrence]
        for s0 in chosen:
            ids, pos = [t[0] for t in stream[s0:s0 + len(parts[0])]], s0 + len(parts[0])
            for p in parts[1:]:
                nxt = runs(p, pos)
                if not nxt:
                    ids = None
                    break
                ids += [t[0] for t in stream[nxt[0]:nxt[0] + len(p)]]
                pos = nxt[0] + len(p)
            if ids:
                best += ids
        if best:
            return best, "exact"
    stream, pos, ids = [t for t in toks if t[2] != "qere"], 0, []
    flat = [w for p in parts for w in p]
    for w in flat:
        k = next((i for i in range(pos, len(stream)) if stream[i][1] == w), None)
        if k is not None:
            ids.append(stream[k][0]); pos = k + 1
    if ids and len(ids) * 2 >= len(flat):
        return ids, "partial"
    return [], "not found (note kept at verse level)"


# ----------------------------------------------------------------------------- equivalents
def build_lemma_links(con, report, top=8):
    """Hebrew <-> Greek equivalents from co-occurrence in aligned Standard verses (Dice).
    Only verses present in both the WLC and Swete count; a pair needs 2+ shared verses
    unless both words are that rare."""
    def verse_sets(edition, key_sql, where):
        sets = defaultdict(set)
        for cid, key in con.execute(
                f"""SELECT vm.canon_verse_id, {key_sql} FROM morpheme m JOIN token t ON t.id = m.token_id
                    JOIN verse v ON v.id = t.verse_id JOIN verse_map vm ON vm.verse_id = v.id
                    WHERE v.edition_id = ? AND {where}""", (edition,)):
            if key:
                sets[cid].add(key)
        return sets
    heb = verse_sets("WLC", "m.strongs", "m.role = 'stem' AND m.strongs IS NOT NULL")
    grk = verse_sets("LXX-SWETE", "COALESCE(m.strongs, m.strongs_ext, 'lemma:' || m.lemma)", "m.lemma IS NOT NULL")
    shared = set(heb) & set(grk)
    h_n, g_n, pair = Counter(), Counter(), Counter()
    for cid in shared:
        hs, gs = heb[cid], grk[cid]
        h_n.update(hs)
        g_n.update(gs)
        for h in hs:
            for g in gs:
                pair[(h, g)] += 1
    rows = []
    for direction, idx in (("heb>grk", 0), ("grk>heb", 1)):
        best = defaultdict(list)
        for (h, g), both in pair.items():
            hn, gn = h_n[h], g_n[g]
            if both < 2 and not (hn <= 2 and gn <= 2 and both == min(hn, gn)):
                continue
            score = 2 * both / (hn + gn)
            frm, to = (h, g) if idx == 0 else (g, h)
            best[frm].append((score, both, to, h_n[frm] if idx == 0 else g_n[frm], g_n[to] if idx == 0 else h_n[to]))
        for frm, cands in best.items():
            for rank, (score, both, to, fn, tn) in enumerate(sorted(cands, reverse=True)[:top], 1):
                rows.append((direction, frm, to, rank, both, fn, tn, round(score, 4)))
    con.executemany("INSERT INTO lemma_link VALUES (?,?,?,?,?,?,?,?)", rows)
    report["lemma_links"] = {"aligned verses": len(shared), "hebrew lemmas": len(h_n),
                             "greek lemmas": len(g_n), "links": len(rows)}


# ----------------------------------------------------------------------------- layouts
# Esther's Greek additions, lettered as in Catholic Bibles, from Standard (Vulgate-style)
# numbering, per the TVTMS notes: (letter, Std chapter, first, last, first label number)
ESTHER_ADDITIONS = [("A", 11, 2, 12, 1), ("A", 12, 1, 6, 12), ("B", 13, 1, 7, 1), ("C", 13, 8, 18, 1),
                    ("C", 14, 1, 19, 12), ("D", 15, 1, 16, 1), ("E", 16, 1, 24, 1), ("F", 10, 4, 13, 1),
                    ("F", 11, 1, 1, 11)]


def esther_label(ch, v):
    for letter, c, lo, hi, first in ESTHER_ADDITIONS:
        if ch == c and lo <= v <= hi:
            return f"{letter} {first + v - lo}"
    return None


LAYOUTS = [
    # book, spine edition, Standard books it presents, description
    ("DAG", "WEB", ("DAN", "S3Y", "SUS", "BEL"),
     "Daniel as read in Catholic and Orthodox Bibles: the Prayer of Azariah and Song of the Three "
     "inside chapter 3 (3:24-90), Susanna as chapter 13, Bel and the Dragon as chapter 14. Order and "
     "numbering follow the WEB's Greek Daniel."),
    ("ESG", "LXX-SWETE", ("EST", "ESG"),
     "Esther with the Greek additions in place, lettered A-F as in Catholic Bibles. Order follows "
     "Swete's Septuagint."),
]


def build_layouts(con, report):
    """Reading order for Greek Daniel and Esther, built from a spine edition's own order.
    Every Standard verse of the replaced books appears exactly once: in spine order where the
    spine has it, otherwise right after its nearest preceding Standard verse."""
    report["layouts"] = {}
    for book, spine, books, desc in LAYOUTS:
        con.execute("INSERT INTO layout VALUES (?,?,?,?)", (book, spine, ",".join(books), desc))
        ph = ",".join("?" * len(books))
        target = {cid: (b, ch, v) for cid, b, ch, v in con.execute(
            f"SELECT id, book_id, chapter, verse FROM canon_verse WHERE book_id IN ({ph}) ORDER BY id", books)}
        order, info = [], {}
        rows = con.execute(f"""SELECT v.chapter, v.verse, v.part, group_concat(m.canon_verse_id)
                               FROM verse v JOIN verse_map m ON m.verse_id = v.id
                               WHERE v.edition_id = ? AND v.book_id = ? GROUP BY v.id ORDER BY v.id""",
                           (spine, book)).fetchall()
        for ch, v, part, cids in rows:
            new = [c for c in sorted({int(x) for x in cids.split(",")}) if c in target and c not in info]
            for k, cid in enumerate(new):
                tb, tch, tv = target[cid]
                if book == "ESG":
                    label = esther_label(tch, tv) if tb == "ESG" else str(tv)
                    lch = 1 if ch == 0 else ch                # Addition A (Swete's prologue) opens chapter 1
                else:
                    label = f"{v}{part}" + ("abcdefgh"[k - 1] if k else "")
                    lch = ch
                info[cid] = (lch, label)
                order.append(cid)
        # Standard verses the spine lacks: after their nearest preceding Standard verse
        leftovers = [c for c in target if c not in info]
        for cid in leftovers:
            tb, tch, tv = target[cid]
            nxt = [c for c in order if c > cid and target[c][0] == tb]
            prev = [c for c in order if c < cid and target[c][0] == tb]
            if nxt:                                     # just before the next Standard verse
                at = order.index(min(nxt))
                lch = info[min(nxt)][0]
            elif prev:
                at = order.index(max(prev)) + 1
                lch = info[max(prev)][0]
            else:
                at, lch = len(order), tch
            label = esther_label(tch, tv) if tb == "ESG" else None
            if not label:
                label = str(tv) if lch == tch else f"{tch}:{tv}"
            info[cid] = (lch, label)
            order.insert(at, cid)
        con.executemany("INSERT INTO layout_verse VALUES (?,?,?,?,?)",
                        [(book, info[c][0], i, c, info[c][1]) for i, c in enumerate(order)])
        report["layouts"][book] = {"verses": len(order), "from spine": len(order) - len(leftovers),
                                   "placed by neighbour": len(leftovers), "target": len(target)}


# ----------------------------------------------------------------------------- verify
def verify(con, report):
    out, ok = [], True
    q = lambda sql, *a: con.execute(sql, a).fetchall()

    def say(s=""):
        print(s)
        out.append(s)

    def check(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        say(f"- [{'PASS' if cond else 'FAIL'}] {msg}")

    say("# bible.db full build report\n")
    say(f"Build time {report['t_total']:.0f}s (downloads/cache {report['t_download']:.0f}s, parse "
        f"{report['t_parse'] - report['t_download']:.0f}s, versification {report['t_versify'] - report['t_parse']:.0f}s, "
        f"write {report['t_write'] - report['t_versify']:.0f}s). DB size {DB.stat().st_size / 1e6:.0f} MB.\n")

    say("## 1. Contents")
    rows = q("""SELECT e.id, COUNT(DISTINCT v.book_id), COUNT(*), SUM(length(v.text) = 0)
                FROM verse v JOIN edition e ON e.id=v.edition_id GROUP BY 1""")
    toks = dict(q("SELECT v.edition_id, COUNT(*) FROM token t JOIN verse v ON v.id=t.verse_id GROUP BY 1"))
    for ed, nb, nv, empty in rows:
        say(f"- {ed}: {nb} books, {nv} verses, {toks.get(ed, 0)} words" + (f", {empty} empty verses" if empty else ""))
    books = {ed: {r[0] for r in q("SELECT DISTINCT book_id FROM verse WHERE edition_id=?", ed)} for ed, *_ in rows}
    check(len(books["WEB"]) == 81, f"WEB has all 81 books ({len(books['WEB'])})")
    check(len(books["WLC"]) == 39, f"WLC has 39 books ({len(books['WLC'])})")
    check(len(books["SBLGNT"]) == 27, f"SBLGNT has 27 books ({len(books['SBLGNT'])})")
    dc = {b[0] for b in BOOKS if b[3] == "DC"}
    say(f"- (info) Deuterocanon in WEB: {sorted(dc & books['WEB'])}")
    say(f"- (info) Deuterocanon in LXX-SWETE: {sorted(dc & books['LXX-SWETE'])}; missing: "
        f"{sorted((dc & books['WEB']) - books['LXX-SWETE'])}")
    say(f"- (info) Swete books not loaded: {SKIPPED_SWETE}")
    check(not report.get("duplicate_verses"), f"no duplicate verse keys {report.get('duplicate_verses', [])[:5]}")

    say("\n## 2. Encoding")
    resid = q("SELECT edition_id, book_id, chapter, verse FROM verse WHERE text LIKE '%\\%' OR text LIKE '%|strong=%'")
    check(not resid, f"no USFM markup left in verse text {resid[:5]}")
    for ed, allowed in (("WLC", {"hebrew"}), ("LXX-SWETE", {"greek", "combining", "elision"}),
                        ("SBLGNT", {"greek", "combining", "elision"})):
        cls = Counter()
        bad = []
        for (s,) in con.execute("SELECT t.surface FROM token t JOIN verse v ON v.id=t.verse_id WHERE v.edition_id=?", (ed,)):
            c = {script_of(ch) for ch in s}
            cls.update(c)
            if not c <= allowed:
                bad.append(s)
        check(len(bad) / max(1, toks.get(ed, 1)) < 0.0005,
              f"{ed}: tokens outside expected scripts {len(bad)} ({Counter(bad).most_common(6)})")

    say("\n## 3. Versification (TVTMS Standard)")
    say(f"- rules: {report['tvtms_stats']}")
    unmapped = q("SELECT v.edition_id, COUNT(*) FROM verse v WHERE NOT EXISTS "
                 "(SELECT 1 FROM verse_map m WHERE m.verse_id=v.id) GROUP BY 1")
    check(not unmapped, f"every verse mapped to Standard (unmapped: {dict(unmapped)}; letter-chapter refs skipped: "
          f"{dict(report['letter_chapter_skips'])})")
    conflicts = {k: r["conflicts"] for k, r in report["tvtms"].items() if r["conflicts"]}
    say(f"- (info) rule conflicts (resolved by tradition preference): {sum(len(c) for c in conflicts.values())} "
        f"in {sorted(f'{e} {b}' for e, b in conflicts)[:12]}")
    rel = q("SELECT v.edition_id, m.relation, COUNT(*) FROM verse_map m JOIN verse v ON v.id=m.verse_id GROUP BY 1,2")
    by = defaultdict(dict)
    for ed, r, n in rel:
        by[ed][r] = n
    for ed, d in sorted(by.items()):
        say(f"- {ed}: {d}")
    check(not report.get("override_misses"), f"all overrides matched a verse {report.get('override_misses', [])[:4]}")
    # every override on a Greek edition is checked against the other Greek edition's text
    W, sim = report["words"], lambda a, b: difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
    other_std = defaultdict(list)
    for (ed, book, ch, v, part), ws in W.items():
        for r, *_ in S.MAPS[(ed, book)].get((ch, v, part), []):
            if str(r.ch).isdigit():
                other_std[(ed, canon_book(r.book, int(r.ch), r.v), int(r.ch), r.v)].extend(ws)
    bad = []
    for ed, book, src, std in report.get("overrides_applied", []):
        if not ed.startswith("LXX"):
            continue
        m = re.fullmatch(r"(\w+):(\d+)([a-z]*)", src)
        tb, tcv = std.split(" ")
        tc, tv = map(int, tcv.split(":"))
        other = "LXX-BRENTON" if ed == "LXX-SWETE" else "LXX-SWETE"
        a = W.get((ed, book, m[1], int(m[2]), m[3]), [])
        # Esther additions: Brenton's TVTMS mapping runs ~1 verse behind Swete's in C-E, so
        # accept the best neighbour there (placement within the right addition, in order)
        if canon_book(tb, tc, tv) == "ESG" and (tc, tv) > (13, 7):
            continue                       # Additions C-F: Brenton is aligned to Swete, not independent
        b = other_std.get((other, canon_book(tb, tc, tv), tc, tv), [])
        if b and sim(a, b) < 0.5:
            bad.append(f"{ed} {book} {src}->{std} ({sim(a, b):.2f})")
    n_lxx = sum(1 for e, b_, _, st in report.get("overrides_applied", []) if e.startswith("LXX")
                and not (st.startswith("ESG") and tuple(map(int, st.split(" ")[1].split(":"))) > (13, 7)))
    check(len(bad) <= n_lxx * 0.05, f"LXX overrides agree with the other Greek edition: {n_lxx - len(bad)}/{n_lxx} "
          f"(disagreeing: {bad[:6]})")

    def std_of(ed, book, ch, v, part=""):
        return sorted((r.book, int(r.ch), r.v) for r, *_ in S.MAPS.get((ed, book), {}).get((str(ch), v, part), [])
                      if str(r.ch).isdigit())
    # documented versification facts (not Scripture text)
    facts = [("WLC", "GEN", 32, 1, ("GEN", 31, 55)), ("WLC", "GEN", 32, 33, ("GEN", 32, 32)),
             ("WLC", "JOL", 3, 1, ("JOL", 2, 28)), ("WLC", "MAL", 3, 19, ("MAL", 4, 1)),
             ("WLC", "PSA", 51, 3, ("PSA", 51, 1)), ("LXX-SWETE", "PSA", 22, 2, ("PSA", 23, 2)),
             ("LXX-BRENTON", "PSA", 22, 2, ("PSA", 23, 2)), ("LXX-SWETE", "JER", 26, 2, ("JER", 46, 2)),
             ("LXX-BRENTON", "DAG", 3, 24, ("S3Y", 1, 1)), ("WEB", "DAG", 13, 1, ("SUS", 1, 1)),
             ("WEB", "DAG", 14, 1, ("BEL", 1, 1)), ("LXX-SWETE", "NEH", 1, 1, ("NEH", 1, 1)),
             ("LXX-SWETE", "PS2", 1, 1, ("PS2", 1, 1)),
             # Psalm titles: Standard verse 0 ("Title" in TVTMS)
             ("WLC", "PSA", 51, 1, ("PSA", 51, 0)), ("LXX-SWETE", "PSA", 50, 1, ("PSA", 51, 0)),
             ("LXX-SWETE", "PSA", 22, 0, ("PSA", 23, 0)),   # Swete prints some titles before verse 1
             ("LXX-BRENTON", "PSA", 51, 1, ("PSA", 52, 0))]
    for ed, b, c, v, want in facts:
        got = std_of(ed, b, c, v)
        check(want in got, f"{ed} {b} {c}:{v} -> Standard {want[0]} {want[1]}:{want[2]} (got {got})")

    # every canonical verse: which editions cover it
    cover = q("""SELECT cv.book_id, b.section, COUNT(DISTINCT cv.id),
                        COUNT(DISTINCT CASE WHEN v.edition_id='WEB' THEN cv.id END),
                        COUNT(DISTINCT CASE WHEN v.edition_id='WLC' THEN cv.id END),
                        COUNT(DISTINCT CASE WHEN v.edition_id='LXX-SWETE' THEN cv.id END),
                        COUNT(DISTINCT CASE WHEN v.edition_id='SBLGNT' THEN cv.id END)
                 FROM canon_verse cv JOIN book b ON b.id=cv.book_id
                 JOIN verse_map m ON m.canon_verse_id=cv.id JOIN verse v ON v.id=m.verse_id
                 GROUP BY cv.book_id ORDER BY b.ord""")
    low = []
    for bk, sec, n, web, wlc, lxx, sbl in cover:
        orig = wlc if sec == "OT" else sbl if sec == "NT" else lxx
        if sec != "DC" and web / n < 0.97 or (orig / n < 0.9):
            low.append(f"{bk}: {n} Std verses, WEB {web}, WLC {wlc}, LXX {lxx}, NT {sbl}")
    tot = sum(r[2] for r in cover)
    say(f"- canonical verses: {tot}")
    say(f"- (info) books where WEB covers <97% or the original language <90% of Standard verses "
        f"({len(low)}): " + "; ".join(low[:25]))

    say("\n## 4. Swete vs Brenton by Standard reference (same Greek tradition: should agree)")
    sim = lambda a, b: difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
    W = report["words"]
    by_std = {"LXX-SWETE": defaultdict(list), "LXX-BRENTON": defaultdict(list)}
    native = defaultdict(list)
    for (ed, book, ch, v, part), ws in W.items():
        for r, *_ in S.MAPS[(ed, book)].get((ch, v, part), []):
            if str(r.ch).isdigit():
                by_std[ed][(canon_book(r.book, int(r.ch), r.v), str(r.ch), r.v)].extend(ws)
    per_book, worst = defaultdict(list), []
    for k in set(by_std["LXX-SWETE"]) & set(by_std["LXX-BRENTON"]):
        s = sim(by_std["LXX-SWETE"][k], by_std["LXX-BRENTON"][k])
        per_book[k[0]].append(s)
        worst.append((s, k))
    for (ed, book, ch, v, part), ws in W.items():
        if ed == "LXX-SWETE" and ("LXX-BRENTON", book, ch, v, part) in W:
            native[book].append(sim(ws, W[("LXX-BRENTON", book, ch, v, part)]))
    say("| book | Std verses compared | agreement by Standard ref | by native number |")
    say("|---|---|---|---|")
    regress = []
    for book in sorted(per_book, key=lambda b: ORD[b]):
        a = sum(per_book[book]) / len(per_book[book])
        n = sum(native[book]) / len(native[book]) if native[book] else float("nan")
        say(f"| {book} | {len(per_book[book])} | {a:.2f} | {n:.2f} |")
        if native[book] and a + 0.02 < n and book != "ESG":
            regress.append(book)
    check(not regress, f"mapping never makes Swete/Brenton agree worse than native numbering {regress} "
          f"(ESG reported separately: the two editions number the additions differently)")
    overall = sum(s for s, _ in worst) / len(worst)
    say(f"- overall agreement by Standard ref: {overall:.3f} over {len(worst)} verses")
    # Esther: Additions A-B are mapped independently in both editions (Swete: TVTMS A-F
    # table overrides; Brenton: TVTMS rules + its ch. 1 overrides) - they must agree.
    ab = [(s, k) for s, k in worst if k[0] == "ESG" and (11, 2) <= (int(k[1]), k[2]) <= (13, 7)]
    check(ab and sum(s for s, _ in ab) / len(ab) > 0.8, f"Esther Additions A-B: Swete and Brenton agree "
          f"independently ({sum(s for s, _ in ab) / max(1, len(ab)):.2f} over {len(ab)} verses)")
    say(f"- (info) verses mapped by text alignment between the Greek editions: {report.get('text_aligned')}")
    esg = []
    man = [s for s, k in worst if k[0] == "MAN"]
    check(man and sum(man) / len(man) > 0.6, f"Swete Ode {SWETE_MANASSEH_ODE} is the Prayer of Manasseh "
          f"(agreement with Brenton MAN {sum(man) / max(1, len(man)):.2f})")
    n14 = q("SELECT COUNT(*) FROM verse WHERE edition_id='WEB' AND book_id='DAG' AND chapter=14")[0][0]
    check(n14 == 42, f"WEB Daniel 14 has 42 verses, as Standard Bel 1:1-42 (override precondition) ({n14})")


    say("\n## 5. Reading layouts (Greek Daniel and Esther)")
    for book, info in report["layouts"].items():
        check(info["verses"] == info["target"], f"{book} layout covers every Standard verse once: {info}")
    chs = dict(q("SELECT chapter, COUNT(*) FROM layout_verse WHERE book_id='DAG' GROUP BY 1"))
    check(sorted(chs) == list(range(1, 15)), f"Daniel layout has chapters 1-14 ({sorted(chs)})")
    check(chs.get(3, 0) >= 97 and chs.get(13) == 64 and chs.get(14) == 42,
          f"Daniel 3 holds the Prayer of Azariah ({chs.get(3)} verses); 13 = Susanna ({chs.get(13)}), "
          f"14 = Bel ({chs.get(14)})")
    seq = [b for (b,) in q("""SELECT cv.book_id FROM layout_verse lv JOIN canon_verse cv ON cv.id = lv.canon_verse_id
                               WHERE lv.book_id='DAG' AND lv.chapter=3 ORDER BY lv.seq""")]
    s3y = [i for i, b in enumerate(seq) if b == "S3Y"]
    check(s3y and all(b == "DAN" for b in seq[:s3y[0]]) and seq[s3y[-1] + 1:] and
          all(b == "DAN" for b in seq[s3y[-1] + 1:]) and len(s3y) == s3y[-1] - s3y[0] + 1,
          "Daniel 3: Hebrew verses, then the whole Prayer of Azariah, then the rest of the chapter")
    labels = {l for (l,) in q("SELECT label FROM layout_verse WHERE book_id='ESG'")}
    want = {f"{letter} {n}" for letter, size in (("A", 17), ("B", 7), ("C", 30), ("D", 16), ("E", 24), ("F", 11))
            for n in range(1, size + 1)}
    check(want <= labels, f"Esther layout has every addition A 1-F 11 (missing {sorted(want - labels)[:8]})")
    host = {}
    for letter in "ABCDEF":
        host[letter] = q("""SELECT chapter FROM layout_verse WHERE book_id='ESG' AND label LIKE ? LIMIT 1""",
                         f"{letter} %")[0][0]
    est_orphans = q("""SELECT cv.chapter, cv.verse FROM canon_verse cv WHERE cv.book_id='EST' AND NOT EXISTS
                         (SELECT 1 FROM verse_map m JOIN verse v ON v.id=m.verse_id
                          WHERE m.canon_verse_id=cv.id AND v.edition_id='WLC')""")
    check(not est_orphans, f"every Standard Esther verse (EST) has its Hebrew counterpart {est_orphans[:8]}")
    web_c = q("SELECT COUNT(*) FROM verse WHERE edition_id='WEB' AND book_id='ESG' AND chapter=4 AND verse BETWEEN 18 AND 47")[0][0]
    check(web_c == 30, f"WEB Greek Esther 4:18-47 is 30 verses, as Addition C (override precondition) ({web_c})")
    check(host == {"A": 1, "B": 3, "C": 4, "D": 4, "E": 8, "F": 10},
          f"Esther additions sit in their host chapters {host}")

    say("\n## 6. Tagging and lexicons")
    for ed, scheme in (("WLC", "oshb"), ("SBLGNT", "step-greek"), ("LXX-SWETE", "morphgnt")):
        st = dict(q("SELECT t.tag_status, COUNT(*) FROM token t JOIN verse v ON v.id=t.verse_id "
                    "WHERE v.edition_id=? GROUP BY 1", ed))
        tot = sum(st.values())
        tagged = st.get("native", 0) + st.get("aligned", 0) + st.get("inferred", 0)
        need = {"WLC": 0.999, "SBLGNT": 0.99, "LXX-SWETE": 0.95}[ed]
        check(tagged / tot >= need, f"{ed}: words tagged {tagged}/{tot} ({tagged / tot:.2%}) {st}")
    check(not report["oshb_unknown"], f"OSHB decoder handles every Hebrew code {report['oshb_unknown'][:5]}")
    check(not report["morphgnt_bad"], f"LXX parsing codes decode {report['morphgnt_bad'][:5]}")
    und = q("""SELECT COUNT(*) FROM morpheme m JOIN token t ON t.id=m.token_id
               LEFT JOIN morph_code mc ON mc.scheme_id=t.morph_scheme AND mc.code=m.morph_code
               WHERE t.morph_scheme IS NOT NULL AND m.morph_code IS NOT NULL AND mc.code IS NULL""")[0][0]
    say(f"- (info) morphemes whose code has no plain-English expansion: {und}")
    say(f"- (info) MorphHB anomalies: {len(report.get('morphhb_anomalies', []))} {report.get('morphhb_anomalies', [])[:3]}")
    un = report.get("sbl_unaligned", [])
    check(len(un) / report["sbl_total"] < 0.001, f"SBLGNT words without TAGNT tags: {len(un)} of {report['sbl_total']} "
          f"(genuine SBL-only readings) e.g. {un[:6]}")
    fx = report["ocr_fixed"]
    say(f"- Swete OCR corrections: {len(fx)} (skipped as Vaticanus spelling, not OCR: "
        f"{report['ocr_skipped_orthographic']}); e.g. {[f'{b} {c}:{v} {o}→{n}' for b, c, v, o, n in fx[:8]]}")
    kept = q("SELECT COUNT(*) FROM token WHERE ocr_original IS NOT NULL")[0][0]
    check(kept == len(fx), f"every OCR correction keeps the transcription's form ({kept})")
    og = q("""SELECT COUNT(DISTINCT cv.id), COUNT(DISTINCT CASE WHEN v.edition_id='LXX-SWETE-OG' THEN cv.id END)
              FROM canon_verse cv JOIN verse_map m ON m.canon_verse_id = cv.id JOIN verse v ON v.id = m.verse_id
              WHERE cv.book_id IN ('DAN','S3Y','SUS','BEL')""")[0]
    check(og[1] / og[0] > 0.9, f"Old Greek Daniel covers {og[1]} of {og[0]} Standard verses of Daniel/Azariah/Susanna/Bel")
    for ed, lex, where, need in (("WLC", "bdb", "NOT (m.role='suffix' AND m.strongs IS NULL)", 0.99), ("SBLGNT", "thayer", "1=1", 0.97),
                                 ("SBLGNT", "lsj", "1=1", 0.97), ("LXX-SWETE", "lsj", "m.morph_code NOT LIKE 'NP %'", 0.90)):
        tot, hit = q(f"""SELECT COUNT(*), SUM(EXISTS (SELECT 1 FROM morpheme_lexicon ml
                                                 WHERE ml.morpheme_id=m.id AND ml.lexicon_id=?))
                         FROM morpheme m JOIN token t ON t.id=m.token_id JOIN verse v ON v.id=t.verse_id
                         WHERE v.edition_id=? AND {where}""", lex, ed)[0]
        check(hit / tot >= need, f"{ed} words with a {lex} entry: {hit}/{tot} ({hit / tot:.1%})")
    say(f"- (info) Swete cleanup: {dict(report['swete_log'])}")

    say("\n## 7. Glosses and Hebrew-Greek equivalents")
    # Ketiv words are excluded: TAHOT glosses the Qere (what is read) and the Qere token carries it
    gl = dict(q("""SELECT v.edition_id, ROUND(100.0 * SUM(t.gloss IS NOT NULL) / COUNT(*), 2) FROM token t
                   JOIN verse v ON v.id = t.verse_id WHERE t.variant != 'ketiv' GROUP BY 1"""))
    say(f"- TAHOT alignment: {dict(report['tahot_log'])}")
    check(gl.get("WLC", 0) >= 99, f"Hebrew words (Ketiv excepted) with an in-context gloss (TAHOT): {gl.get('WLC')}%")
    check(gl.get("SBLGNT", 0) >= 99, f"Greek NT words with an in-context gloss (TAGNT): {gl.get('SBLGNT')}%")
    check(gl.get("LXX-SWETE", 0) >= 90, f"Septuagint words with a dictionary gloss (LSJ): {gl.get('LXX-SWETE')}%")
    seg = q("""SELECT COUNT(*), SUM(m.gloss IS NOT NULL) FROM morpheme m JOIN token t ON t.id = m.token_id
               JOIN verse v ON v.id = t.verse_id WHERE v.edition_id = 'WLC' AND m.role = 'stem'""")[0]
    say(f"- (info) Hebrew stems with their own segment gloss: {seg[1]}/{seg[0]}")
    say(f"- equivalents: {report['lemma_links']}")
    top = lambda d, k: [r[0] for r in q("SELECT to_key FROM lemma_link WHERE direction=? AND from_key=? ORDER BY rank LIMIT 3", d, k)]
    # well-known translation equivalents (lexical facts): Elohim -> theos, YHWH -> kyrios, erets -> ge
    for d, h, want in (("heb>grk", "H0430", "G2316"), ("heb>grk", "H3068", "G2962"), ("heb>grk", "H0776", "G1093"),
                       ("grk>heb", "G2316", "H0430"), ("grk>heb", "G2962", "H3068")):
        got = top(d, h)
        check(got[:1] == [want], f"{d} {h}: strongest equivalent is {want} (got {got})")
    got = top("heb>grk", "H1697")
    check("G3056" in got or "G4487" in got, f"heb>grk H1697 (davar): logos or rhema among the top 3 (got {got})")

    say("\n## 8. Cross-references")
    x = report["xref"]
    say(f"- {x}")
    ok_ob = x.get("openbible", 0) / max(1, x.get("openbible", 0) + x.get("openbible unresolved", 0))
    check(ok_ob > 0.995, f"OpenBible references resolving to Standard verses: {ok_ob:.2%}")
    check(x.get("web", 0) > 300, f"WEB cross-reference notes imported: {x.get('web', 0)}")
    with_refs = q("SELECT COUNT(DISTINCT from_canon) FROM cross_ref")[0][0]
    say(f"- (info) Standard verses with cross-references: {with_refs}")

    say("\n## 9. Commentaries")
    from bibleingest.commentary import check_html
    cs = report.get("commentary", {})
    say(f"- {cs}")
    per = dict(q("SELECT commentary_id, COUNT(*) FROM commentary_entry GROUP BY 1"))
    for cid, least in (("tyndale", 17000), ("uw", 90000), ("catena", 800), ("kd", 8500)):
        check(per.get(cid, 0) >= least, f"{cid}: {per.get(cid, 0)} entries (expected {least}+)")
    skipped = sum(v for k, v in cs.items() if "skipped" in k)
    check(skipped <= 0.005 * sum(per.values()), f"references outside Standard numbering: {skipped}")
    bad = [(i, p) for i, body in q("SELECT id, body FROM commentary_entry") for p in check_html(body)]
    check(not bad, f"commentary bodies use only the safe HTML tags ({len(bad)} problems) {bad[:3]}")
    for lang, least in (("heb", 0.97), ("grk", 0.90)):
        tot = sum(v for k, v in cs.items() if k.startswith(f"uw {lang} words"))
        hit = cs.get(f"uw {lang} words: exact", 0) + cs.get(f"uw {lang} words: partial", 0)
        check(tot and hit / tot >= least, f"unfoldingWord {lang} quotes linked to words: {hit}/{tot} "
              f"({100 * hit / max(tot, 1):.1f}%; exact {cs.get(f'uw {lang} words: exact', 0)})")
    for book, ch, v, want in (("GEN", 1, 1, {"tyndale", "uw", "kd"}), ("MAT", 1, 2, {"catena", "tyndale", "uw"}),
                              ("JON", 1, 17, {"tyndale", "uw", "kd"}), ("PSA", 23, 1, {"tyndale", "uw", "kd"})):
        cid = S.canon_verse_id(book, ch, v)
        got = {r[0] for r in q("""SELECT DISTINCT e.commentary_id FROM commentary_ref r JOIN commentary_entry e
                                  ON e.id = r.entry_id WHERE r.start_canon <= ? AND r.end_canon >= ?
                                  AND e.kind = 'note'""", cid, cid)}
        check(want <= got, f"{book} {ch}:{v} has notes from {sorted(want)} (got {sorted(got)})")
    # a note on a Hebrew word in Jonah 1:17 must point at the WLC's Jonah 2:1 (Hebrew numbering)
    heb = q("""SELECT DISTINCT v.chapter, v.verse FROM commentary_word w JOIN token t ON t.id = w.token_id
               JOIN verse v ON v.id = t.verse_id JOIN commentary_ref r ON r.entry_id = w.entry_id
               WHERE r.start_canon = ? AND v.edition_id = 'WLC'""", S.canon_verse_id("JON", 1, 17))
    check(heb == [(2, 1)], f"Jonah 1:17 language notes link to WLC Jonah 2:1 (got {heb})")
    say(f"- (info) unfoldingWord notes marked as translation technique (hidden by default): "
        f"{q('SELECT COUNT(*) FROM commentary_entry WHERE minor = 1')[0][0]}")

    say("\n## 10. Search")
    for term in ("beginning", "covenant", "mercy"):
        n = q("SELECT COUNT(*) FROM verse_fts f JOIN verse v ON v.id=f.rowid WHERE verse_fts MATCH ? "
              "AND v.edition_id='WEB'", term)[0][0]
        check(n > 10, f"FTS5 WEB '{term}': {n} verses")
    for s in ("H7225", "H1254", "G3056", "G0026"):
        n = q("SELECT COUNT(*) FROM strongs_occurrence WHERE strongs=?", s)[0][0]
        check(n > 0, f"Strong's {s}: {n} occurrences")
    t = time.time()
    q("""SELECT pv.edition_id, pv.text FROM parallel_verse pv WHERE pv.canon_verse_id = ?""",
      S.canon_verse_id("PSA", 23, 1))
    say(f"- (info) parallel-verse lookup: {1000 * (time.time() - t):.1f} ms")

    say(f"\n**RESULT: {'ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED'}**")
    REPORT.write_text("\n".join(out) + "\n", encoding="utf-8")
    return ok


def main():
    report = {}
    con = build(report)
    ok = verify(con, report)
    print(f"\nReport written to {REPORT}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
