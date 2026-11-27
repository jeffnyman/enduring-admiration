#!/usr/bin/env python3
"""Sample ingest: Genesis 1, Tobit 1, John 1 -> db/sample.db, then verify.

  Genesis 1 : WEB + WLC Hebrew (MorphHB) + LXX Greek (Swete, tagged; Brenton, text only)
  Tobit 1   : WEB + LXX Greek (Swete, tagged; Brenton, text only)
  John 1    : WEB + SBLGNT Greek, tagged from STEP TAGNT

All text comes from downloaded files (cached in data/cache/). Nothing is
hard-coded: verification checks structure, counts, Unicode ranges and
cross-source agreement only.

Usage:  .venv/bin/python pipeline/sample_ingest.py
"""
import difflib
import html
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

from bibleingest import greek, lexicon, morphhb, oshb_morph, swete, tvtms, usfm
from bibleingest.books import BOOKS, ORD, canon_verse_id
from bibleingest.fetch import fetch, now, zip_member
from bibleingest.textnorm import norm_hebrew, script_of

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "sample.db"          # never overwrites the full build (db/bible.db)
SCHEMA = ROOT / "db" / "schema.sql"
PREVIEW = ROOT / "data" / "sample_preview.html"

MORPHHB_SHA = "db6c5c9b46b8f39346f10915ddb1a70dcd429901"
STRONGS_SHA = "0acd2f251c2d35ff8db2dece4e0593979d3ac223"
STEP_SHA = "5de0a47f35f0fc13dfe1430d104e5db8a4285f9c"
GH = "https://raw.githubusercontent.com"
STEP = f"{GH}/STEPBible/STEPBible-Data/{STEP_SHA}"
QF_SHA = "46258f8bde173998ef0633d79eff3067b9041575"
QF = f"{GH}/QuantForgeSoftware/lxx/{QF_SHA}/data"
HL = f"{GH}/openscriptures/HebrewLexicon/21c9add13bc727d3a951361778e97e3ff7afd1ce"
EP_SHA = "a31ff38c40a681ef1029dcc51eb7e7ee3f2ea409"
EP = f"{GH}/imbennyhim/Every-Promise-Thayers/{EP_SHA}"
TFLSJ = f"{STEP}/Lexicons/TFLSJ%20{{}}%20-%20Translators%20Formatted%20full%20LSJ%20Bible%20lexicon%20-%20STEPBible.org%20CC%20BY.txt"

SOURCES = {
    "ebible-eng-web": dict(
        title="World English Bible (with Deuterocanon), USFM",
        url="https://ebible.org/Scriptures/eng-web_usfm.zip", file="eng-web_usfm.zip",
        license="Public Domain", attribution="World English Bible, eBible.org (public domain)"),
    "ebible-grcbrent": dict(
        title="Brenton Greek Septuagint with Apocrypha, USFM",
        url="https://ebible.org/Scriptures/grcbrent_usfm.zip", file="grcbrent_usfm.zip",
        license="Public Domain", attribution="Septuagint Greek text, L.C.L. Brenton ed., via eBible.org"),
    "ebible-grcsbl": dict(
        title="SBL Greek New Testament, USFM",
        url="https://ebible.org/Scriptures/grcsbl_usfm.zip", file="grcsbl_usfm.zip",
        license="CC-BY-4.0",
        attribution="SBL Greek New Testament. Copyright © 2010 Society of Biblical Literature "
                    "and Logos Bible Software. CC BY 4.0."),
    "oshb-morphhb": dict(
        title="Open Scriptures Hebrew Bible (WLC 4.20 + morphology), Genesis",
        url=f"{GH}/openscriptures/morphhb/{MORPHHB_SHA}/wlc/Gen.xml", file="Gen.xml",
        version=MORPHHB_SHA, license="CC-BY-4.0 (morphology/lemmas); WLC text Public Domain",
        attribution="Open Scriptures Hebrew Bible Project (CC BY 4.0); Westminster Leningrad Codex (PD)"),
    "step-tagnt": dict(
        title="STEPBible TAGNT (Matthew-John)",
        url=f"{STEP}/Translators%20Amalgamated%20OT%2BNT/TAGNT%20Mat-Jhn%20-%20Translators%20Amalgamated%20Greek%20NT%20-%20STEPBible.org%20CC-BY.txt",
        file="TAGNT-Mat-Jhn.txt", version=STEP_SHA, license="CC-BY-4.0",
        attribution="Translators Amalgamated Greek NT, STEPBible.org / Tyndale House Cambridge (CC BY 4.0)"),
    "step-tvtms": dict(
        title="STEPBible TVTMS versification traditions and standardisation rules",
        url=f"{STEP}/Versification/TVTMS%20-%20Translators%20Versification%20Traditions%20with%20Methodology%20for%20Standardisation%20for%20Eng%2BHeb%2BLat%2BGrk%2BOthers%20-%20STEPBible.org%20CC%20BY.txt",
        file="TVTMS.txt", version=STEP_SHA, license="CC-BY-4.0",
        attribution="TVTMS, STEPBible.org / Tyndale House Cambridge (CC BY 4.0)"),
    "step-tegmc": dict(
        title="STEPBible TEGMC Greek morphology code expansions",
        url=f"{STEP}/Morphology%20codes/TEGMC%20-%20Translators%20Expansion%20of%20Greek%20Morphhology%20Codes%20-%20STEPBible.org%20CC%20BY.txt",
        file="TEGMC.txt", version=STEP_SHA, license="CC-BY-4.0",
        attribution="STEPBible.org / Tyndale House Cambridge (CC BY 4.0)"),
    "strongs-heb": dict(
        title="Strong's Hebrew Dictionary (OSIS XML)",
        url=f"{GH}/openscriptures/strongs/{STRONGS_SHA}/hebrew/StrongHebrewG.xml",
        file="StrongHebrewG.xml", version=STRONGS_SHA, license="Public Domain",
        attribution="James Strong, Hebrew and Chaldee Dictionary (1890); XML by D. Instone-Brewer / Open Scriptures"),
    "strongs-grk": dict(
        title="Strong's Greek Dictionary (XML 1.4)",
        url=f"{GH}/openscriptures/strongs/{STRONGS_SHA}/greek/StrongsGreekDictionaryXML_1.4/strongsgreek.xml",
        file="strongsgreek.xml", version=STRONGS_SHA, license="Public Domain",
        attribution="James Strong, Greek Dictionary (1890); XML by U. Sandborg-Petersen / Open Scriptures"),
    # Multi-file sources: data[sid] is then {key: bytes}
    "oshb-bdb": dict(
        title="Brown-Driver-Briggs Hebrew Lexicon (OpenScriptures HebrewLexicon)",
        files={"bdb": f"{HL}/BrownDriverBriggs.xml", "index": f"{HL}/LexicalIndex.xml"},
        version="21c9add13bc727d3a951361778e97e3ff7afd1ce",
        license="CC-BY-4.0 (markup/index); BDB text Public Domain",
        attribution="Brown, Driver & Briggs (1906), public domain; digitization and Lexical Index by the "
                    "Open Scriptures Hebrew Bible Project (CC BY 4.0). Work in progress: many entries are outlines."),
    "thayer-ep": dict(
        title="Thayer's Greek-English Lexicon of the NT (1889), Every-Promise edition",
        files={
               "01-G1-G224.md": f"{EP}/book/01-G1-G224.md",
               "02-G225-G499.md": f"{EP}/book/02-G225-G499.md",
               "03-G500-G745.md": f"{EP}/book/03-G500-G745.md",
               "04-G746-G986.md": f"{EP}/book/04-G746-G986.md",
               "05-G987-G1188.md": f"{EP}/book/05-G987-G1188.md",
               "06-G1189-G1383.md": f"{EP}/book/06-G1189-G1383.md",
               "07-G1384-G1514.md": f"{EP}/book/07-G1384-G1514.md",
               "08-G1515-G1706.md": f"{EP}/book/08-G1515-G1706.md",
               "09-G1707-G1908.md": f"{EP}/book/09-G1707-G1908.md",
               "10-G1909-G2097.md": f"{EP}/book/10-G1909-G2097.md",
               "11-G2098-G2288.md": f"{EP}/book/11-G2098-G2288.md",
               "12-G2289-G2482.md": f"{EP}/book/12-G2289-G2482.md",
               "13-G2483-G2670.md": f"{EP}/book/13-G2483-G2670.md",
               "14-G2671-G2918.md": f"{EP}/book/14-G2671-G2918.md",
               "15-G2919-G3096.md": f"{EP}/book/15-G2919-G3096.md",
               "16-G3097-G3367.md": f"{EP}/book/16-G3097-G3367.md",
               "17-G3368-G3597.md": f"{EP}/book/17-G3368-G3597.md",
               "18-G3598-G3766.md": f"{EP}/book/18-G3598-G3766.md",
               "19-G3767-G3937.md": f"{EP}/book/19-G3767-G3937.md",
               "20-G3938-G4121.md": f"{EP}/book/20-G3938-G4121.md",
               "21-G4122-G4313.md": f"{EP}/book/21-G4122-G4313.md",
               "22-G4314-G4533.md": f"{EP}/book/22-G4314-G4533.md",
               "23-G4534-G4782.md": f"{EP}/book/23-G4534-G4782.md",
               "24-G4783-G5045.md": f"{EP}/book/24-G4783-G5045.md",
               "25-G5046-G5277.md": f"{EP}/book/25-G5046-G5277.md",
               "26-G5278-G5524.md": f"{EP}/book/26-G5278-G5524.md",
               "27-G5525-G5624.md": f"{EP}/book/27-G5525-G5624.md",
           },
        version=EP_SHA, license="Public Domain (CC0 1.0 for the edition)",
        attribution="J. H. Thayer, Greek-English Lexicon of the New Testament (1889), public domain; "
                    "digital edition imbennyhim/Every-Promise-Thayers (CC0). May contain transcription artifacts."),
    "step-tflsj": dict(
        title="STEPBible TFLSJ: full Liddell-Scott-Jones for Bible Greek (NT + LXX)",
        files={"main": TFLSJ.format("%200-5624"), "extra": TFLSJ.format("extra")},
        version=STEP_SHA, license="CC-BY-4.0",
        attribution="Liddell-Scott-Jones Greek-English Lexicon via Perseus, formatted and corrected by "
                    "Tyndale House Cambridge / STEPBible.org (CC BY 4.0)"),
    "f1k-swete": dict(
        title="Swete, The Old Testament in Greek (1909), First1KGreek TEI transcription",
        files={"GEN": f"{QF}/swete-tei/tlg001__tlg0527.tlg001.opp-grc2.xml",
               "TOB": f"{QF}/swete-tei/tlg021__tlg0527.tlg021.1st1K-grc1.xml"},
        version=QF_SHA, license="CC-BY-SA-4.0",
        attribution="H. B. Swete, The Old Testament in Greek; transcription by the First1KGreek "
                    "Project (CC BY-SA 4.0). Artefacts cleaned by this pipeline."),
    "qf-lxx-morph": dict(
        title="QuantForgeSoftware/lxx Morpheus lemmas and morphology for Swete",
        files={"GEN": f"{QF}/morph-morpheus/001-Gen.txt", "TOB": f"{QF}/morph-morpheus/019-Tob.txt"},
        version=QF_SHA, license="CC-BY-SA-4.0",
        attribution="LXX morphology generated with Morpheus by QuantForgeSoftware/lxx (CC BY-SA 4.0); "
                    "machine-generated, not reviewed"),
}

SAMPLES = [("GEN", 1), ("TOB", 1), ("JHN", 1)]


# ---------------------------------------------------------------------------
def build_db(path=DB, label="sample"):
    path.parent.mkdir(exist_ok=True)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    con.execute("INSERT INTO schema_meta VALUES ('schema_version','1'), ('build',?)", (label,))
    con.executemany("INSERT INTO book VALUES (?,?,?,?,?,?,?,?,?)",
                    [(b[0], ORD[b[0]], b[1], b[2], b[3], b[4], b[5], b[6], b[7]) for b in BOOKS])
    con.executemany("INSERT INTO book_alias VALUES ('osis',?,?)", [(b[1], b[0]) for b in BOOKS])
    con.executemany("INSERT INTO versification_scheme VALUES (?,?)", [
        ("eng", "English (KJV/NRSV tradition); canonical grid = TVTMS Standard"),
        ("heb", "Masoretic (BHS/WLC) numbering"),
        ("lxx", "Septuagint numbering (Brenton / Rahlfs tradition)")])
    return con


EDITION_NOTES = {
    "LXX-SWETE": "Main text: Codex B where extant (Genesis: Codex A). Tobit = B text "
                 "(short recension). Lemma/morphology machine-generated (Morpheus).",
    "LXX-BRENTON": "Text only, no lemma/morphology; Vaticanus-based",
}


def load_sources(con, sources=None, notes=None, sblgnt_source="ebible-grcsbl"):
    sources, notes = sources or SOURCES, {**EDITION_NOTES, **(notes or {})}
    data = {}
    for sid, s in sources.items():
        if "files" in s:
            data[sid], shas = {}, []
            for key, url in s["files"].items():
                data[sid][key], sha = fetch(sid, url, url.rsplit("/", 1)[1])
                shas.append(f"{key}:{sha}")
            url, sha = " ".join(s["files"].values()), " ".join(shas)
        else:
            (data[sid], sha), url = fetch(sid, s["url"], s["file"]), s["url"]
        con.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?,?)",
                    (sid, s["title"], url, s.get("version"), s["license"],
                     s["attribution"], sha, now()))
    con.executemany("INSERT INTO morph_scheme VALUES (?,?,?)", [
        ("oshb", "OpenScriptures Hebrew morphology (language-prefixed segment codes)", "oshb-morphhb"),
        ("step-greek", "Robinson-style Greek codes with STEP extensions", "step-tegmc"),
        ("morphgnt", "MorphGNT-style 'POS PARSING' codes (LXX Morpheus output)", "qf-lxx-morph")])
    con.executemany("INSERT INTO edition VALUES (?,?,?,?,?,?,?,?,?)", [
        ("WEB", "World English Bible", "en", "ltr", "translation", "eng", "ebible-eng-web", None, None),
        ("WLC", "Westminster Leningrad Codex", "hbo", "rtl", "original", "heb", "oshb-morphhb",
         "oshb-morphhb", None),
        ("LXX-SWETE", "Septuagint (Swete)", "grc", "ltr", "original", "lxx", "f1k-swete",
         "qf-lxx-morph", notes["LXX-SWETE"]),
        ("LXX-BRENTON", "Septuagint (Brenton Greek text)", "grc", "ltr", "original", "lxx",
         "ebible-grcbrent", None, notes["LXX-BRENTON"]),
        ("SBLGNT", "SBL Greek New Testament", "grc", "ltr", "original", "eng", sblgnt_source,
         "step-tagnt", notes.get("SBLGNT", "Lemma/morph/Strong's aligned from TAGNT; eBible Strong's tags ignored"))])
    return data


def insert_verse(con, edition, book, ch, v, text, text_search, rich=None, para=None,
                 heading=None, break_after=None, part="", verse_end=None):
    cur = con.execute(
        "INSERT INTO verse (edition_id, book_id, chapter, verse, part, verse_end, text, text_search,"
        " rich_json, para_before, heading_before, break_after) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (edition, book, ch, v, part, verse_end, text, text_search,
         json.dumps(rich, ensure_ascii=False) if rich else None, para, heading, break_after))
    return cur.lastrowid


MAPS = {}   # (edition, book) -> {(ch_str, v, part): [(std Ref, relation, rule, note)]}
OVERRIDES = Path(__file__).resolve().parent / "versification_overrides.tsv"


def map_verse(con, verse_id, edition, book, ch, v, part=""):
    for std, relation, rule, note in MAPS[(edition, book)][(str(ch), v, part)]:
        cid = canon_verse_id(std.book, int(std.ch), std.v)
        con.execute("INSERT OR IGNORE INTO canon_verse VALUES (?,?,?,?)", (cid, std.book, int(std.ch), std.v))
        con.execute("INSERT INTO verse_map VALUES (?,?,?,?,?)", (verse_id, cid, relation, rule, note))


# ---------------------------------------------------------------------------
# Full-book verse inventories (TVTMS tests look beyond the sample chapters)
def inv_usfm(text, book, ordinal=False):
    inv = tvtms.Inventory()
    for ch, verses in usfm.parse_book(text).items():
        if ordinal:
            usfm.ordinal_parts(verses)
        for v in verses:
            inv.add(book, ch, v["verse"], len(v["text"].split()), v["part"], v["verse_end"])
            if v["verse"] == 1 and v.get("title_before"):
                inv.titles.add((book, str(ch)))
    return inv


def inv_morphhb(xml, book):
    import xml.etree.ElementTree as ET
    inv = tvtms.Inventory()
    for v in ET.fromstring(xml).iter(morphhb.Q + "verse"):
        _, ch, vn = v.get("osisID").split(".")
        inv.add(book, ch, vn, sum(1 for w in v if w.tag == morphhb.Q + "w"))
    return inv


def inv_swete(xml, book):
    inv = tvtms.Inventory()
    for ch, raw in swete.book_text(xml).items():
        if isinstance(ch, int):
            for (vn, part), toks in swete.clean_chapter(raw, Counter()).items():
                inv.add(book, ch, vn, len(toks), part)
    return inv


def build_maps(data, web, lxx, sbl, report):
    std_inv = {b: inv_usfm(web[b], b) for b, _ in SAMPLES}     # chapter lengths for ranges
    last = lambda b, ch: std_inv[b].last(b, ch) if b in std_inv else None
    rules, stats = tvtms.parse_expanded(data["step-tvtms"].decode("utf-8"), last)
    report["tvtms_stats"] = stats
    eng, heb, grk = ("Eng-KJV", "Eng-NRSV", "AllBibles"), ("Hebrew", "AllBibles"), ("Greek", "AllBibles")
    plan = [("WEB", b, std_inv[b], eng) for b, _ in SAMPLES]
    plan += [("WLC", "GEN", inv_morphhb(data["oshb-morphhb"].decode("utf-8"), "GEN"), heb)]
    plan += [("LXX-BRENTON", b, inv_usfm(lxx[b], b, ordinal=True), grk) for b in ("GEN", "TOB")]
    plan += [("LXX-SWETE", b, inv_swete(data["f1k-swete"][b].decode("utf-8"), b), grk) for b in ("GEN", "TOB")]
    report["lxx_words"] = {}
    for b in ("GEN", "TOB"):
        book = usfm.parse_book(lxx[b])
        for verses in book.values():
            usfm.ordinal_parts(verses)
        report["lxx_words"][("LXX-BRENTON", b)] = {
            (str(ch), v["verse"], v["part"]): [t["surface_norm"] for t in greek.tokenize(v["text"])]
            for ch, verses in book.items() for v in verses}
        x = data["f1k-swete"][b].decode("utf-8")
        report["lxx_words"][("LXX-SWETE", b)] = {
            (str(ch), vn, part): [t["surface_norm"] for t in toks]
            for ch, raw in swete.book_text(x).items() if isinstance(ch, int)
            for (vn, part), toks in swete.clean_chapter(raw, Counter()).items()}
    plan += [("SBLGNT", "JHN", inv_usfm(sbl, "JHN"), eng)]
    report["tvtms"] = {}
    for edition, book, inv, prefer in plan:
        MAPS[(edition, book)], rep = tvtms.map_edition(rules, inv, book, prefer)
        report["tvtms"][(edition, book)] = rep
    tvtms.load_overrides(OVERRIDES, MAPS, report)


def insert_tokens(con, verse_id, tokens, scheme):
    for pos, t in enumerate(tokens, 1):
        cur = con.execute(
            "INSERT INTO token (verse_id, position, variant, variant_group, surface, surface_norm,"
            " leading, trailing, source_ref, lemma_raw, morph_raw, morph_scheme, gloss, translit,"
            " tag_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (verse_id, pos, t.get("variant", ""), t.get("variant_group"), t["surface"],
             t["surface_norm"], t.get("leading", ""), t.get("trailing", ""), t.get("source_ref"),
             t.get("lemma_raw"), t.get("morph_raw"), scheme if t.get("morphemes") else None,
             t.get("gloss"), t.get("translit"), t.get("tag_status", "none")))
        for m in t.get("morphemes", []):
            con.execute(
                "INSERT INTO morpheme (token_id, position, role, surface, lemma, strongs,"
                " strongs_ext, morph_code, gloss) VALUES (?,?,?,?,?,?,?,?,?)",
                (cur.lastrowid, m["position"], m["role"], m["surface"], m.get("lemma"),
                 m["strongs"], m["strongs_ext"], m["morph_code"], m.get("gloss")))


def verse_text(tokens, skip_variant="qere"):
    return "".join(t.get("leading", "") + t["surface"] + t["trailing"]
                   for t in tokens if t.get("variant") != skip_variant).strip()


# ---------------------------------------------------------------------------
def ingest(con, data):
    report = {"anomalies": [], "unaligned": []}
    web = {b: zip_member(data["ebible-eng-web"], f"{b}eng-web.usfm") for b, _ in SAMPLES}
    lxx = {b: zip_member(data["ebible-grcbrent"], f"{b}grcbrent.usfm") for b in ("GEN", "TOB")}
    sbl = zip_member(data["ebible-grcsbl"], "JHNgrcsbl.usfm")
    build_maps(data, web, lxx, sbl, report)

    # English
    for book, ch in SAMPLES:
        for v in usfm.parse_chapter(web[book], ch):
            vid = insert_verse(con, "WEB", book, ch, v["verse"], v["text"], v["text"],
                               v["runs"], v["para_before"], v["heading_before"],
                               part=v["part"], verse_end=v["verse_end"])
            map_verse(con, vid, "WEB", book, ch, v["verse"], v["part"])
            con.executemany("INSERT INTO verse_note (verse_id, kind, text) VALUES (?,?,?)",
                            [(vid, k, t) for k, t in v["notes"]])

    # Hebrew (MorphHB)
    for v in morphhb.parse_chapter(data["oshb-morphhb"].decode("utf-8"), "Gen", 1):
        toks = v["tokens"]
        vid = insert_verse(con, "WLC", "GEN", 1, v["verse"], verse_text(toks),
                           " ".join(t["surface_norm"] for t in toks), break_after=v["break_after"])
        map_verse(con, vid, "WLC", "GEN", 1, v["verse"])
        for t in toks:
            if t.get("anomaly"):
                report["anomalies"].append((f"Gen 1:{v['verse']}", t["source_ref"], t["anomaly"]))
        insert_tokens(con, vid, toks, "oshb")

    # Greek LXX (Brenton) - text only
    for book in ("GEN", "TOB"):
        for v in usfm.parse_chapter(lxx[book], 1):
            toks = greek.tokenize(v["text"])
            vid = insert_verse(con, "LXX-BRENTON", book, 1, v["verse"], verse_text(toks),
                               " ".join(t["surface_norm"] for t in toks), v["runs"], v["para_before"],
                               part=v["part"], verse_end=v["verse_end"])
            map_verse(con, vid, "LXX-BRENTON", book, 1, v["verse"], v["part"])
            insert_tokens(con, vid, toks, None)

    # Greek NT: SBLGNT text + TAGNT tags
    sbl_verses = []
    for v in usfm.parse_chapter(sbl, 1, note_kind_f="textcritical"):
        v["tokens"] = greek.tokenize(v["text"])
        sbl_verses.append(v)
    rows = greek.parse_tagnt(data["step-tagnt"].decode("utf-8"), "Jhn", 1)
    report["unaligned"] = greek.align(sbl_verses, rows)
    report["tagnt_rows"] = len(rows)
    report["tagnt_sbl_rows"] = sum("SBL" in r["editions"] for r in rows)
    for v in sbl_verses:
        toks = v["tokens"]
        vid = insert_verse(con, "SBLGNT", "JHN", 1, v["verse"], verse_text(toks),
                           " ".join(t["surface_norm"] for t in toks), v["runs"], v["para_before"],
                           part=v["part"], verse_end=v["verse_end"])
        map_verse(con, vid, "SBLGNT", "JHN", 1, v["verse"], v["part"])
        con.executemany("INSERT INTO verse_note (verse_id, kind, text) VALUES (?,?,?)",
                        [(vid, k, t) for k, t in v["notes"]])
        insert_tokens(con, vid, toks, "step-greek")

    # Morphology codes. Greek: STEP TEGMC. Hebrew: decoded to the OSHB spec for every
    # code present in the whole MorphHB book (not just the sample chapter).
    con.executemany("INSERT OR IGNORE INTO morph_code VALUES (?,?,?,?,?)",
                    [("step-greek", r["code"], r["summary"], r["detail"], r["fields"])
                     for r in lexicon.step_morph_codes(data["step-tegmc"].decode("utf-8"))])
    import re as _re
    all_codes = set()
    for m in _re.findall(r'morph="([^"]+)"', data["oshb-morphhb"].decode("utf-8")):
        all_codes.update(m[0] + seg for seg in m[1:].split("/"))
    report["oshb_codes"], report["oshb_unknown"] = len(all_codes), []
    for c in sorted(all_codes):
        try:
            con.execute("INSERT INTO morph_code VALUES ('oshb',?,?,NULL,NULL)", (c, oshb_morph.decode(c)))
        except oshb_morph.Unknown as e:
            report["oshb_unknown"].append(str(e))

    load_lexicons(con, data, report)

    # Fill missing dictionary lemmas (all Hebrew stems, Greek crasis parts) from Strong's
    fill_lemmas(con)
    _swete_sample(con, data, report)
    con.execute("INSERT INTO verse_fts(verse_fts) VALUES ('rebuild')")
    con.commit()
    return report


def fill_lemmas(con):
    con.execute("""UPDATE morpheme SET lemma = (SELECT le.lemma FROM lexicon_entry le
                   WHERE le.strongs = morpheme.strongs AND le.lexicon_id IN ('strongs-heb','strongs-grk'))
                   WHERE lemma IS NULL AND strongs IS NOT NULL""")


def lxx_strongs_finders(con):
    """(lemma -> Strong's base, lemma -> STEP extended number via LSJ)"""
    find_strongs = swete.strongs_lookup(con.execute(
        "SELECT strongs, lemma FROM lexicon_entry WHERE lexicon_id='strongs-grk'").fetchall())
    find_ext = swete.strongs_lookup(con.execute(
        """SELECT ls.strongs_ext, le.lemma FROM lexicon_entry le JOIN lexicon_strongs ls ON ls.entry_id=le.id
           WHERE le.lexicon_id='lsj' AND ls.strongs_ext IS NOT NULL""").fetchall())
    return find_strongs, find_ext


def lxx_morpheme(tag, surface, finders):
    find_strongs, find_ext = finders
    base = find_strongs(tag["lemma"])
    ext = None if base else find_ext(tag["lemma"])
    n = int(re.match(r"G(\d+)", ext)[1]) if ext else None
    if n and n <= 5624:
        base = f"G{n:04d}"                    # the LSJ number is a Strong's number
    return {"position": 1, "role": "stem", "surface": surface, "lemma": tag["lemma"],
            "strongs": base, "strongs_ext": ext, "morph_code": tag["code"], "gloss": None}


def load_lexicons(con, data, report):
    # Lexicons (whole lexicons, not just sample words)
    con.executemany("INSERT INTO lexicon VALUES (?,?,?,?)", [
        ("strongs-heb", "Strong's Hebrew Dictionary", "hbo", "strongs-heb"),
        ("strongs-grk", "Strong's Greek Dictionary", "grc", "strongs-grk"),
        ("bdb", "Brown-Driver-Briggs", "hbo", "oshb-bdb"),
        ("thayer", "Thayer's Greek-English Lexicon", "grc", "thayer-ep"),
        ("lsj", "Liddell-Scott-Jones (Bible Greek)", "grc", "step-tflsj")])
    cols = ("entry_key", "strongs", "lemma", "translit", "pronunciation", "part_of_speech",
            "short_def", "definition", "derivation", "kjv_usage")
    sources = {
        "strongs-heb": lexicon.strongs_hebrew(data["strongs-heb"].decode("utf-8")),
        "strongs-grk": lexicon.strongs_greek(data["strongs-grk"].decode("utf-8")),
        "bdb": lexicon.bdb(data["oshb-bdb"]["bdb"].decode("utf-8-sig"),
                           data["oshb-bdb"]["index"].decode("utf-8-sig")),
        "thayer": lexicon.thayer_ep(data["thayer-ep"][k].decode("utf-8") for k in sorted(data["thayer-ep"])),
        "lsj": (e for part in ("main", "extra") for e in lexicon.tflsj(data["step-tflsj"][part].decode("utf-8-sig"))),
    }
    report["lexicon_dupes"] = Counter()
    for lex, entries in sources.items():
        for e in entries:
            try:
                cur = con.execute(
                    f"INSERT INTO lexicon_entry (lexicon_id, {', '.join(cols)}, extra_json) "
                    f"VALUES (?,{','.join('?' * len(cols))},?)",
                    (lex, *(e[c] for c in cols), json.dumps(e["extra"], ensure_ascii=False) if e["extra"] else None))
            except sqlite3.IntegrityError:
                report["lexicon_dupes"][lex] += 1         # same entry_key twice in a source
                continue
            con.executemany("INSERT OR IGNORE INTO lexicon_strongs VALUES (?,?,?)",
                            [(cur.lastrowid, b, x) for b, x in e["links"]])




def _swete_sample(con, data, report):
    # Greek LXX (Swete): text rebuilt from TEI, tags attached from the Morpheus files
    finders = lxx_strongs_finders(con)
    report["swete_log"], codes = Counter(), set()
    for book in ("GEN", "TOB"):
        rows = list(swete.morph_rows(data["qf-lxx-morph"][book].decode("utf-8")))
        index = swete.book_index(rows)
        verses = swete.clean_chapter(
            swete.chapter_text(data["f1k-swete"][book].decode("utf-8"), 1), report["swete_log"])
        swete.attach(verses, [r for r in rows if r["chapter"] == 1], index, report["swete_log"])
        for (vnum, part), toks in verses.items():
            for t in toks:
                tag = t.get("tag")
                if tag:
                    codes.add(tag["code"])
                    t["lemma_raw"], t["morph_raw"] = tag["lemma"], tag["code"]
                    t["morphemes"] = [lxx_morpheme(tag, t["surface"], finders)]
            vid = insert_verse(con, "LXX-SWETE", book, 1, vnum, verse_text(toks),
                               " ".join(t["surface_norm"] for t in toks), part=part)
            map_verse(con, vid, "LXX-SWETE", book, 1, vnum, part)
            insert_tokens(con, vid, toks, "morphgnt")
    report["morphgnt_bad"] = []
    for c in sorted(codes):
        try:
            con.execute("INSERT INTO morph_code VALUES ('morphgnt',?,?,NULL,NULL)", (c, swete.decode(c)))
        except ValueError:
            report["morphgnt_bad"].append(c)



# ---------------------------------------------------------------------------
def verify(con, report):
    ok = True
    q = lambda sql, *a: con.execute(sql, a).fetchall()

    def check(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")

    print("\n== 1. Verse counts and canonical alignment")
    for book, ch in SAMPLES:
        counts = dict(q("SELECT edition_id, COUNT(*) FROM verse WHERE book_id=? AND chapter=? "
                        "GROUP BY edition_id", book, ch))
        print(f"  {book} {ch}: {counts}")
        web = {r[0] for r in q("""SELECT vm.canon_verse_id FROM verse v JOIN verse_map vm ON vm.verse_id=v.id
                                  WHERE v.edition_id='WEB' AND v.book_id=? AND v.chapter=?""", book, ch)}
        for ed in counts:
            if ed == "WEB":
                continue
            other = {r[0] for r in q("""SELECT vm.canon_verse_id FROM verse v JOIN verse_map vm
                     ON vm.verse_id=v.id WHERE v.edition_id=? AND v.book_id=? AND v.chapter=?""", ed, book, ch)}
            check(other == web, f"{book} {ch}: {ed} verse set matches WEB "
                  f"(missing {sorted(c % 1000 for c in web - other)}, extra {sorted(c % 1000 for c in other - web)})")
        empty = q("SELECT edition_id, verse FROM verse WHERE book_id=? AND chapter=? AND length(text)=0", book, ch)
        check(not empty, f"{book} {ch}: no empty verses {empty or ''}")

    print("\n== 2. Encoding")
    leftovers = q("SELECT edition_id, book_id, verse FROM verse WHERE text LIKE '%\\%' "
                  "OR text LIKE '%|strong=%' OR text LIKE '%  %'")
    check(not leftovers, f"no USFM markup or double spaces left in verse text {leftovers[:5]}")
    heb = [r[0] for r in q("SELECT t.surface FROM token t JOIN verse v ON v.id=t.verse_id WHERE v.edition_id='WLC'")]
    heb_scripts = Counter(script_of(c) for w in heb for c in w)
    print(f"  Hebrew token character classes: {dict(heb_scripts)}")
    check(set(heb_scripts) <= {"hebrew"}, "Hebrew tokens use only the Hebrew block (no presentation forms, no Latin)")
    check(all(norm_hebrew(w) for w in heb), "every Hebrew token has consonants")
    import unicodedata as ud
    nfc_diff = sum(ud.normalize("NFC", w) != w for w in heb)
    print(f"  (info) {nfc_diff}/{len(heb)} Hebrew tokens would be altered by NFC - stored as source, unnormalized")
    for ed in ("LXX-BRENTON", "LXX-SWETE", "SBLGNT"):
        words = q("SELECT t.surface, v.book_id, v.verse FROM token t JOIN verse v ON v.id=t.verse_id "
                  "WHERE v.edition_id=?", ed)
        bad = [(w, b, vn) for w, b, vn in words
               if any(script_of(c) not in ("greek", "combining", "elision") for c in w)]
        sc = Counter(script_of(c) for w, _, _ in words for c in w)
        print(f"  {ed} token character classes: {dict(sc)}")
        check(not bad, f"{ed}: Greek tokens contain only Greek letters/diacritics/elision "
              f"({len(bad)} bad{': ' + str(bad[:8]) if bad else ''})")

    print("\n== 3. Hebrew morphology")
    check(not report["anomalies"], f"MorphHB segment/lemma/morph counts agree ({report['anomalies'][:5]})")
    n_m, n_dec = q("""SELECT COUNT(*), SUM(mc.code IS NOT NULL) FROM morpheme m JOIN token t ON t.id=m.token_id
                      LEFT JOIN morph_code mc ON mc.scheme_id='oshb' AND mc.code=m.morph_code
                      JOIN verse v ON v.id=t.verse_id WHERE v.edition_id='WLC'""")[0]
    check(n_m and n_dec == n_m, f"Hebrew morph codes decoded (Gen 1): {n_dec}/{n_m}")
    check(not report["oshb_unknown"], f"OSHB decoder handles all {report['oshb_codes']} distinct codes "
          f"in all of Genesis {report['oshb_unknown'][:10]}")
    n_s, n_lex = q("""SELECT COUNT(*), SUM(le.id IS NOT NULL) FROM morpheme m JOIN token t ON t.id=m.token_id
                      JOIN verse v ON v.id=t.verse_id LEFT JOIN lexicon_entry le
                      ON le.lexicon_id='strongs-heb' AND le.strongs=m.strongs
                      WHERE v.edition_id='WLC' AND m.role='stem'""")[0]
    check(n_lex == n_s, f"Hebrew stems resolving to a Strong's entry: {n_lex}/{n_s}")

    print("\n== 4. Greek NT tagging (SBLGNT <- TAGNT)")
    total = q("SELECT COUNT(*) FROM token t JOIN verse v ON v.id=t.verse_id WHERE v.edition_id='SBLGNT'")[0][0]
    un = report["unaligned"]
    print(f"  SBLGNT tokens {total}; TAGNT rows {report['tagnt_rows']} (SBL-marked {report['tagnt_sbl_rows']})")
    check(len(un) / total < 0.01, f"aligned {total - len(un)}/{total}; unaligned: {un}")
    n_m, n_dec = q("""SELECT COUNT(*), SUM(mc.code IS NOT NULL) FROM morpheme m JOIN token t ON t.id=m.token_id
                      LEFT JOIN morph_code mc ON mc.scheme_id='step-greek' AND mc.code=m.morph_code""")[0]
    missing = q("""SELECT DISTINCT m.morph_code FROM morpheme m JOIN token t ON t.id=m.token_id
                   LEFT JOIN morph_code mc ON mc.scheme_id='step-greek' AND mc.code=m.morph_code
                   WHERE t.morph_scheme='step-greek' AND mc.code IS NULL""")
    n_m = q("SELECT COUNT(*) FROM morpheme m JOIN token t ON t.id=m.token_id WHERE t.morph_scheme='step-greek'")[0][0]
    check(not missing, f"Greek morph codes decoded: {n_m - 0 if not missing else '?'}/{n_m}; undecoded {[r[0] for r in missing]}")
    n_s, n_lex = q("""SELECT COUNT(*), SUM(le.id IS NOT NULL) FROM morpheme m JOIN token t ON t.id=m.token_id
                      LEFT JOIN lexicon_entry le ON le.lexicon_id='strongs-grk' AND le.strongs=m.strongs
                      WHERE t.morph_scheme='step-greek'""")[0]
    print(f"  Greek morphemes resolving to Strong's entry: {n_lex}/{n_s} "
          f"(STEP numbers above G5624 are extensions with no Strong's entry)")

    print("\n== 5. Septuagint (Swete text + Morpheus tags)")
    log = report["swete_log"]
    print(f"  cleanup: { {k: v for k, v in log.items() if k not in ('aligned', 'inferred', 'unaligned')} }")
    total = log["aligned"] + log["inferred"] + log["unaligned"]
    tagged = log["aligned"] + log["inferred"]
    check(tagged / total >= 0.97, f"tokens tagged {tagged}/{total} ({tagged / total:.1%}): "
          f"aligned {log['aligned']}, inferred from same form elsewhere in book {log['inferred']}, "
          f"untagged {log['unaligned']}")
    untagged = q("""SELECT v.book_id, v.verse, t.surface FROM token t JOIN verse v ON v.id=t.verse_id
                    WHERE v.edition_id='LXX-SWETE' AND t.tag_status='unaligned'""")
    print(f"  untagged words: {untagged}")
    check(not report["morphgnt_bad"], f"all LXX parsing codes decode {report['morphgnt_bad']}")
    n_s, n_lex = q("""SELECT COUNT(*), SUM(m.strongs IS NOT NULL) FROM morpheme m JOIN token t ON t.id=m.token_id
                      JOIN verse v ON v.id=t.verse_id WHERE v.edition_id='LXX-SWETE'
                      AND m.morph_code NOT LIKE 'NP %'""")[0]
    print(f"  (info) non-name LXX lemmas linked to a Strong's entry: {n_lex}/{n_s} ({n_lex / n_s:.0%}); "
          f"the rest need lemma lookup (LSJ) on full ingest")
    for book in ("GEN", "TOB"):
        sw, br = (q("SELECT COUNT(*) FROM token t JOIN verse v ON v.id=t.verse_id WHERE v.edition_id=? "
                    "AND v.book_id=?", ed, book)[0][0] for ed in ("LXX-SWETE", "LXX-BRENTON"))
        check(abs(sw - br) / br < 0.10, f"{book} 1 word count Swete {sw} vs Brenton {br} (within 10%: no text lost)")

    print("\n== 6. Versification (TVTMS)")
    print(f"  rules parsed: {report['tvtms_stats']}")
    for (ed, book), rep in report["tvtms"].items():
        rels = {k: rep.get(k, 0) for k in ("identical", "renumbered", "partial", "merged")}
        print(f"  {ed:<11} {book}: {rels}  traditions matched: {rep['traditions'] or '-'}"
              f"{'  unevaluable rules: ' + str(rep['rules with unevaluable tests']) if rep.get('rules with unevaluable tests') else ''}")
        check(not rep["conflicts"], f"{ed} {book}: no conflicting traditions {rep['conflicts'][:5]}")
    unmapped = q("SELECT COUNT(*) FROM verse v WHERE NOT EXISTS (SELECT 1 FROM verse_map m WHERE m.verse_id=v.id)")[0][0]
    check(unmapped == 0, f"every ingested verse has a canonical mapping ({unmapped} unmapped)")
    # Known answers (well-documented MT/English differences elsewhere in Genesis,
    # exercising rules against the full-book inventory)
    wlc = MAPS[("WLC", "GEN")]
    got = lambda ch, v: [(r.ch, r.v, rel) for r, rel, _, _ in wlc.get((ch, v, ""), [])]
    check(got("32", 1) == [("31", 55, "renumbered")], f"WLC Gen 32:1 -> Std 31:55 (got {got('32', 1)})")
    check(got("32", 33) == [("32", 32, "renumbered")], f"WLC Gen 32:33 -> Std 32:32 (got {got('32', 33)})")
    check(("31", 55, "") not in wlc, "WLC Gen has no 31:55 of its own")
    check(not report.get("override_misses"), f"all overrides matched a verse {report.get('override_misses', '')}")

    # Empirical check: Swete and Brenton print (mostly) the same Greek text, so after
    # mapping, verses sharing a Standard ref should agree far better than by native number.
    sim = lambda a, b: difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
    for book in ("TOB", "GEN"):
        sw, br = report["lxx_words"][("LXX-SWETE", book)], report["lxx_words"][("LXX-BRENTON", book)]
        def by_std(words, m):
            out = {}
            for k, ws in words.items():
                for r, *_ in m[k]:
                    out.setdefault((r.ch, r.v), []).extend(ws)
            return out
        cs, cb = by_std(sw, MAPS[("LXX-SWETE", book)]), by_std(br, MAPS[("LXX-BRENTON", book)])
        keys = set(cs) & set(cb)
        mapped = sum(sim(cs[k], cb[k]) for k in keys) / len(keys)
        nat_keys = set(sw) & set(br)
        native = sum(sim(sw[k], br[k]) for k in nat_keys) / len(nat_keys)
        low = sorted((round(sim(cs[k], cb[k]), 2), f"{k[0]}:{k[1]}") for k in keys if sim(cs[k], cb[k]) < 0.5)
        check(mapped >= native, f"{book}: Swete~Brenton agreement by Standard ref {mapped:.3f} "
              f"(by native number {native:.3f}); still <0.5: {len(low)} {low[:8]}")
    for ed, book, src, std in report["overrides_applied"]:
        ch, v = std.split(" ")[-1].split(":")
        m = re.fullmatch(r"(\d+):(\d+)([a-z]?)", src)
        a = report["lxx_words"][(ed, book)][(m[1], int(m[2]), m[3])]
        b = report["lxx_words"][("LXX-SWETE", book)].get((ch, int(v), ""), [])
        check(sim(a, b) >= 0.6, f"override {ed} {book} {src} -> {std}: text matches Swete {std} ({sim(a, b):.2f})")
    web_moved = [(k, v) for (ed, b), m in MAPS.items() if ed == "WEB" for k, v in m.items()
                 if any(rel != "identical" for _, rel, _, _ in v)]
    print(f"  (info) WEB verses not identical to Standard in sample books: {len(web_moved)} {web_moved[:3]}")

    print("\n== 7. Lexicons")
    counts = dict(q("SELECT lexicon_id, COUNT(*) FROM lexicon_entry GROUP BY 1"))
    print(f"  entries: {counts}; duplicate keys skipped: {dict(report['lexicon_dupes'])}")
    check(all(counts.get(k, 0) > 1000 for k in ("strongs-heb", "strongs-grk", "bdb", "thayer", "lsj")),
          "all five lexicons loaded")
    empty = dict(q("SELECT lexicon_id, COUNT(*) FROM lexicon_entry WHERE coalesce(definition, short_def, '') = '' GROUP BY 1"))
    print(f"  (info) entries with no definition text: {empty}")

    def coverage(edition, lex, where="1=1"):
        return q(f"""SELECT COUNT(DISTINCT m.id),
                            COUNT(DISTINCT CASE WHEN ml.entry_id IS NOT NULL THEN m.id END)
                     FROM morpheme m JOIN token t ON t.id=m.token_id JOIN verse v ON v.id=t.verse_id
                     LEFT JOIN morpheme_lexicon ml ON ml.morpheme_id=m.id AND ml.lexicon_id=?
                     WHERE v.edition_id=? AND {where}""", lex, edition)[0]
    for ed, lex, where, need in (("WLC", "bdb", "m.role='stem'", 0.98),
                                 ("WLC", "bdb", "m.role='prefix'", 0.98),
                                 ("SBLGNT", "thayer", "1=1", 0.98),
                                 ("SBLGNT", "lsj", "1=1", 0.98),
                                 ("LXX-SWETE", "lsj", "m.morph_code NOT LIKE 'NP %'", 0.90)):
        tot, hit = coverage(ed, lex, where)
        check(hit / tot >= need, f"{ed} words with a {lex} entry: {hit}/{tot} ({hit / tot:.1%})")
    multi = q("""SELECT m.strongs_ext, COUNT(DISTINCT ml.entry_id) n FROM morpheme m
                 JOIN morpheme_lexicon ml ON ml.morpheme_id=m.id AND ml.lexicon_id='bdb'
                 JOIN token t ON t.id=m.token_id JOIN verse v ON v.id=t.verse_id
                 WHERE v.edition_id='WLC' GROUP BY m.strongs_ext HAVING n > 1""")
    print(f"  (info) Hebrew lemmas linking to more than one BDB entry (homographs/cross-refs): {multi[:8]}")
    exact = q("""SELECT ml.match, COUNT(*) FROM morpheme_lexicon ml JOIN morpheme m ON m.id=ml.morpheme_id
                 JOIN token t ON t.id=m.token_id JOIN verse v ON v.id=t.verse_id
                 WHERE v.edition_id='WLC' AND ml.lexicon_id='bdb' GROUP BY 1""")
    print(f"  (info) WLC->BDB link types: {dict(exact)}")
    status = q("""SELECT json_extract(le.extra_json,'$.status'), COUNT(DISTINCT le.id) FROM morpheme_lexicon ml
                  JOIN lexicon_entry le ON le.id=ml.entry_id JOIN morpheme m ON m.id=ml.morpheme_id
                  JOIN token t ON t.id=m.token_id JOIN verse v ON v.id=t.verse_id
                  WHERE v.edition_id='WLC' AND ml.lexicon_id='bdb' GROUP BY 1""")
    print(f"  (info) BDB entries used by Gen 1, by digitization status: {dict(status)}")
    tot, hit = q("""SELECT COUNT(DISTINCT m.id), COUNT(DISTINCT CASE WHEN ml.entry_id IS NOT NULL THEN m.id END)
                    FROM morpheme m JOIN token t ON t.id=m.token_id JOIN verse v ON v.id=t.verse_id
                    LEFT JOIN morpheme_lexicon ml ON ml.morpheme_id=m.id
                    WHERE v.edition_id='LXX-SWETE' AND m.morph_code NOT LIKE 'NP %'""")[0]
    print(f"  (info) LXX non-name words with any lexicon entry: {hit}/{tot} ({hit / tot:.1%}); "
          f"Strong's alone was 92%")

    print("\n== 8. Search")
    hits = q("""SELECT v.book_id, COUNT(*) FROM verse_fts f JOIN verse v ON v.id=f.rowid
                WHERE verse_fts MATCH 'beginning' AND v.edition_id='WEB' GROUP BY v.book_id""")
    check(len(hits) >= 2, f"FTS5 English 'beginning' hits by book: {hits}")
    for s in ("H7225", "G3056"):
        n = q("SELECT COUNT(*) FROM strongs_occurrence WHERE strongs=?", s)[0][0]
        check(n > 0, f"Strong's lookup {s}: {n} occurrence(s)")

    return ok


# ---------------------------------------------------------------------------
def preview(con):
    """HTML page to eyeball RTL + fonts in a browser (all text from the DB)."""
    rows = con.execute("""SELECT cv.book_id, cv.chapter, cv.verse, pv.edition_id, pv.direction,
                                 pv.language, pv.text
                          FROM canon_verse cv JOIN parallel_verse pv ON pv.canon_verse_id = cv.id
                          WHERE cv.verse <= 3 ORDER BY cv.id, pv.edition_id DESC""").fetchall()
    out, cur = [], None
    for b, c, v, ed, d, lang, text in rows:
        if (b, c, v) != cur:
            out.append(f"<h3>{b} {c}:{v}</h3>")
            cur = (b, c, v)
        out.append(f'<p class="{lang}" dir="{d}" lang="{lang}"><small>{ed}</small> {html.escape(text)}</p>')
    PREVIEW.write_text(f"""<!doctype html><meta charset="utf-8"><title>bible.db sample preview</title>
<style>body{{font-family:system-ui;max-width:56rem;margin:2rem auto;line-height:1.6}}
.hbo{{font-family:"SBL Hebrew","Noto Serif Hebrew","Ezra SIL",serif;font-size:1.6rem}}
.grc{{font-family:"Galatia SIL","SBL Greek","Noto Serif",serif;font-size:1.25rem}}
small{{font:12px system-ui;color:#888;margin:0 .5rem}}</style>
<h1>Sample preview (first 3 verses of each chapter, from bible.db)</h1>{''.join(out)}""",
                       encoding="utf-8")


def show_word(con, edition, book, verse, position):
    r = con.execute("""SELECT t.surface, t.translit, t.gloss, m.role, m.surface, m.lemma, m.strongs,
                              m.morph_code, mc.summary, m.id, m.strongs_ext
                       FROM token t JOIN verse v ON v.id=t.verse_id
                       JOIN morpheme m ON m.token_id=t.id
                       LEFT JOIN morph_code mc ON mc.scheme_id=t.morph_scheme AND mc.code=m.morph_code
                       WHERE v.edition_id=? AND v.book_id=? AND v.chapter=1 AND v.verse=? AND t.position=?
                       ORDER BY m.position""", (edition, book, verse, position)).fetchall()
    print(f"\n  {edition} {book} 1:{verse} word {position}: {r[0][0]}  translit={r[0][1]} gloss={r[0][2]}")
    for x in r:
        print(f"    {x[3]:<7} {x[4]:<10} lemma={x[5]} {x[6] or ''}{' / ' + x[10] if x[10] else ''} {x[7]} -> {x[8]}")
        for lex, match, sd in con.execute(
                """SELECT ml.lexicon_id, ml.match, le.short_def FROM morpheme_lexicon ml
                   JOIN lexicon_entry le ON le.id=ml.entry_id WHERE ml.morpheme_id=?
                   ORDER BY ml.lexicon_id""", (x[9],)):
            print(f"            {lex:<11} ({match}) {(sd or '').replace(chr(10), ' ')[:95]}")


def main():
    print("Building", DB.relative_to(ROOT))
    con = build_db()
    data = load_sources(con)
    report = ingest(con, data)
    ok = verify(con, report)
    preview(con)
    print("\n== 9. Samples (read back from bible.db)")
    for b in ("GEN", "TOB", "JHN"):
        for ed, text in con.execute("""SELECT edition_id, text FROM verse WHERE book_id=? AND verse=1
                                       ORDER BY edition_id DESC""", (b,)):
            print(f"  {b} 1:1 [{ed}] {text[:140]}")
    show_word(con, "WLC", "GEN", 1, 1)
    show_word(con, "LXX-SWETE", "GEN", 1, 2)
    show_word(con, "LXX-SWETE", "TOB", 2, 1)
    show_word(con, "WLC", "GEN", 1, 2)
    lxx_ext = con.execute("""SELECT v.book_id, v.verse, t.position FROM morpheme m JOIN token t ON t.id=m.token_id
                             JOIN verse v ON v.id=t.verse_id WHERE v.edition_id='LXX-SWETE'
                             AND m.strongs IS NULL AND m.strongs_ext IS NOT NULL LIMIT 1""").fetchone()
    if lxx_ext:
        show_word(con, "LXX-SWETE", *lxx_ext)
    show_word(con, "SBLGNT", "JHN", 1, 5)
    show_word(con, "SBLGNT", "JHN", 31, 1)
    print(f"\nPreview for RTL/font check: {PREVIEW}")
    print("\nRESULT:", "ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
