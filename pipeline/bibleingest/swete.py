"""Swete LXX: text from the First1KGreek TEI (CC BY-SA 4.0), lemma/morphology
from QuantForgeSoftware/lxx Morpheus output (CC BY-SA 4.0), joined here.

Why not use the Morpheus files' text directly: they drop text that follows a
mid-verse <note> (about 6-9% of words), so the verse text is rebuilt from the
TEI and the tags are attached by sequence alignment.
"""
import difflib
import re
import unicodedata as ud
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

from .textnorm import norm_greek, split_punct

TEI = "{http://www.tei-c.org/ns/1.0}"
SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
# Latin capitals the transcription uses in place of Greek ones
LOOKALIKE = str.maketrans("ABEHIKMNOPTXYZ", "ΑΒΕΗΙΚΜΝΟΡΤΧΥΖ")

# Morpheus (classical) lemma -> Strong's (Koine) headword spelling
LEMMA_ALIASES = {"γίγνομαι": "γίνομαι", "γιγνώσκω": "γινώσκω"}


# --------------------------------------------------------------------------- text
def _walk(el, parts):
    if el.tag == TEI + "note":
        return                                   # apparatus + margin sigla
    if el.tag in (TEI + "l", TEI + "p") and parts:
        parts.append(" ")
    parts.append(el.text or "")
    for c in el:
        _walk(c, parts)
        parts.append(c.tail or "")


VERSE_N = re.compile(r"^(\d+)([a-z]?)(\d*)$")


def book_text(xml: str, log: Counter | None = None) -> dict:
    """{chapter_key: {(verse, part): text}} in document order. chapter_key is an int,
    or the TEI label for non-numeric chapters ('prologue', 'iva'). Verse 'n' values like
    '7a' become (7, 'a'); the transcription typo '1a1' (between 10a and 12a) becomes (11, 'a')."""
    root = ET.fromstring(xml)
    out = {}
    chapters = [d for d in root.iter(TEI + "div") if d.get("subtype") == "chapter"]
    if not chapters:                              # one-chapter book (Epistle of Jeremiah): verses only
        chapters = [d for d in root.iter(TEI + "div") if d.get("type") == "edition"]
        for d in chapters:
            d.set("n", "1")
    for ch in chapters:
        key = int(ch.get("n")) if ch.get("n", "").isdigit() else ch.get("n")
        verses = out.setdefault(key, {})
        # text before the first verse (Psalm superscriptions) -> verse 0; <head> is Swete's
        # chapter numeral, not text
        pre = []
        for c in ch:
            if c.tag == TEI + "div":
                break
            if c.tag not in (TEI + "head", TEI + "note"):
                _walk(c, pre)
                pre.append(" ")
        if "".join(pre).strip():
            verses[(0, "")] = "".join(pre)
        for v in ch.iter(TEI + "div"):
            if v.get("subtype") != "verse":
                continue
            m = VERSE_N.match(v.get("n", ""))
            if not m:
                if log is not None:
                    log["unparseable verse numbers skipped"] += 1
                continue
            vn, part = int(m[1] + m[3]), m[2]
            if m[3] and log is not None:
                log["verse-number typos repaired"] += 1
            parts = []
            _walk(v, parts)
            verses[(vn, part)] = "".join(parts)
    return out


def chapter_text(xml: str, chapter) -> dict:
    book = book_text(xml)
    if chapter not in book:
        raise ValueError(f"chapter {chapter} not in TEI")
    return book[chapter]


def clean_chapter(raw: dict, log: Counter):
    """Fix transcription artefacts. {(verse, part): text} -> {(verse, part): [token, ...]},
    keeping document order."""
    verses: dict = {}
    for (vnum, part) in raw:
        text = raw[(vnum, part)]
        # alternative numbering in parentheses: (⁶) (23) -> drop
        text, n = re.subn(r"\(\s*[0-9⁰¹²³⁴⁵⁶⁷⁸⁹]+\s*\)", " ", text)
        log["alt-numbering removed"] += n
        # words glued by punctuation ('πόλιν,καὶ', 'τέταρτος.²⁴Οζειὴλ'): split after the mark
        text, n = re.subn(r"(?<=[^\W\d_])([,.·;—])(?=[^\W\d_]|[⁰¹²³⁴⁵⁶⁷⁸⁹])", r"\1 ", text)
        log["glued words split"] += n
        # section / pilcrow / bullet marks, stray backslashes
        text, n = re.subn(r"[§¶•|*\\]", " ", text)
        log["section marks removed"] += n
        # editorial brackets (letters supplied where the manuscript is damaged)
        text, n = re.subn(r"[\[\]]", "", text)
        log["bracket marks removed"] += n
        # words hyphenated across a line break
        text, n = re.subn(r"(\w)-\s+(\w)", r"\1\2", text)
        log["hyphenation joined"] += n

        cur = (vnum, part)
        verses.setdefault(cur, [])
        for chunk in text.split():
            # bare superscript verse number = verse break missed in transcription
            m = re.match(r"^([⁰¹²³⁴⁵⁶⁷⁸⁹]+)(.*)$", chunk)
            if m:
                new = int(m.group(1).translate(SUP))
                if not part and new == cur[0] + 1 and (new, "") not in raw:
                    cur = (new, "")
                    verses.setdefault(cur, [])
                    log["missed verse breaks restored"] += 1
                else:
                    log["stray superscripts removed"] += 1
                chunk = m.group(2)
                if not chunk:
                    continue
            if re.fullmatch(r"[A-Za-z]{1,2}|[IVXLC]{2,}|ABBREV", chunk):
                log["latin sigla / roman numerals removed"] += 1   # margin sigla, chapter labels
                continue
            # apostrophe + l/1/i read for capital iota with breathing: '’lσραὴλ' -> 'Ἰσραὴλ'
            chunk, n = re.subn(r"^[’ʼ'][l1i](?=[^\W\d_])", "Ἰ", chunk)
            log["iota-with-breathing repaired"] += n
            # stray digits inside a word ('θρό9νου')
            chunk, n = re.subn(r"(?<=[^\W\d_])\d+(?=[^\W\d_])", "", chunk)
            log["digits inside words removed"] += n
            lead, word, trail = split_punct(chunk)
            if not word:
                if verses[cur]:
                    verses[cur][-1]["trailing"] += chunk
                continue
            if any(c.isascii() and c.isalpha() for c in word):
                fixed = word.translate(LOOKALIKE)
                if any(not c.isascii() for c in fixed):      # Greek word with a Latin 'o' inside
                    fixed = fixed.replace("o", "ο")
                if not any(c.isascii() and c.isalpha() for c in fixed):
                    log["latin lookalikes repaired"] += 1
                    word = fixed
            verses[cur].append({"surface": word, "surface_norm": norm_greek(word),
                                "leading": lead, "trailing": trail})
    for toks in verses.values():
        for t in toks[:-1]:
            t["trailing"] += " "
    return verses


# --------------------------------------------------------------------------- tags
def morph_rows(text: str):
    """All rows of a QuantForge book file (space-separated, 9 columns)."""
    for line in text.splitlines():
        f = line.split(" ")
        if len(f) == 9:
            yield dict(chapter=int(f[0][3:6]), verse=int(f[0][6:9]), pos=f[1], parse=f[2],
                       word=f[4], lemma=f[6], src=f[8])


def _tag(row):
    return {"lemma": row["lemma"], "code": f"{row['pos']} {row['parse']}", "src": row["src"]}


def book_index(rows):
    """Context-free fallback: form -> most frequent analysis in the book
    (only if it accounts for >= 80% of that form's analyses)."""
    by_form = defaultdict(Counter)
    for r in rows:
        if r["src"] == "morpheus":
            by_form[norm_greek(r["word"])][(r["lemma"], r["pos"], r["parse"])] += 1
    best = {}
    for form, c in by_form.items():
        (lemma, pos, parse), n = c.most_common(1)[0]
        if n / sum(c.values()) >= 0.8:
            best[form] = {"lemma": lemma, "code": f"{pos} {parse}", "src": "morpheus"}
    return best


def attach(verses: dict[int, list], chapter_rows: list, index: dict, log: Counter):
    flat = [t for toks in verses.values() for t in toks]          # document order
    a = [t["surface_norm"] for t in flat]
    b = [norm_greek(r["word"]) for r in chapter_rows]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            row = chapter_rows[blk.b + k]
            tok = flat[blk.a + k]
            # Morpheus fallback ("proper noun"): keep it only for real names (Capitalised);
            # ALL-CAPS opening words and lowercase OCR failures go to the book index instead
            s = tok["surface"]
            if row["src"] == "morpheus-proper" and not (s[:1].isupper() and not s.isupper()):
                continue
            tok["tag"], tok["tag_status"] = _tag(row), "aligned"
    for t in flat:
        if "tag" not in t:
            hit = index.get(t["surface_norm"])
            s = t["surface"]
            if not hit and s[:1].isupper() and not s.isupper():
                # same fallback the Morpheus pipeline uses for unanalysable capitalised words
                hit = {"lemma": s, "code": "NP --------", "src": "morpheus-proper"}
            if hit:
                t["tag"], t["tag_status"] = hit, "inferred"
            else:
                t["tag_status"] = "unaligned"
        log[t["tag_status"]] += 1
    return flat


# --------------------------------------------------------------------------- morph codes
POS = {"A-": "Adjective", "C-": "Conjunction", "D-": "Adverb", "I-": "Interjection",
       "N-": "Noun", "NP": "Proper noun", "P-": "Preposition", "RA": "Definite article",
       "RD": "Demonstrative pronoun", "RI": "Interrogative/indefinite pronoun",
       "RP": "Personal pronoun", "RR": "Relative pronoun", "V-": "Verb", "X-": "Particle"}
F = [dict(zip("123", ("1st person", "2nd person", "3rd person"))),
     dict(P="present", I="imperfect", F="future", A="aorist", X="perfect", Y="pluperfect"),
     dict(A="active", M="middle", P="passive"),
     dict(I="indicative", D="imperative", S="subjunctive", O="optative", N="infinitive", P="participle"),
     dict(N="nominative", G="genitive", D="dative", A="accusative", V="vocative"),
     dict(S="singular", P="plural", D="dual"),
     dict(M="masculine", F="feminine", N="neuter"),
     dict(C="comparative", S="superlative")]


def decode(code: str) -> str:
    pos, parse = code.split(" ")
    if pos not in POS or len(parse) != 8:
        raise ValueError(code)
    if any(ch != "-" and ch not in F[i] for i, ch in enumerate(parse)):
        raise ValueError(code)
    order = [1, 2, 3, 0, 4, 5, 6, 7]           # tense voice mood person case number gender degree
    vals = [F[i][parse[i]] for i in order if parse[i] != "-"]
    return POS[pos] + (", " + " ".join(vals) if vals else "")


def strongs_lookup(entries):
    """lemma (exact NFC) -> Strong's number, only where unambiguous."""
    exact = defaultdict(set)
    for strongs, lemma in entries:
        exact[ud.normalize("NFC", lemma)].add(strongs)

    def find(lemma):
        lemma = ud.normalize("NFC", LEMMA_ALIASES.get(lemma, lemma))
        s = exact.get(lemma, set())
        return next(iter(s)) if len(s) == 1 else None
    return find
