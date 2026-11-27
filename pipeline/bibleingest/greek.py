"""Greek editions: plain USFM tokenization (Brenton LXX, SBLGNT) and
STEP TAGNT tagging aligned onto SBLGNT tokens."""
import difflib
from collections import defaultdict
import re

from .textnorm import SBL_SIGLA, norm_greek, split_punct

# 'Mat.15.6#01', optionally with another tradition's verse number in (…), {…} or […]:
# 'Mat.15.6{15.5}#01', 'Luk.6.18[6.17]#06'
TAGNT_REF = re.compile(r"^(\w+)\.(\d+)\.(\d+)(?:\([^)]*\)|\{[^}]*\}|\[[^\]]*\])?#(\d+)=(\S+)$")
VARIANT_RE = re.compile(r"(?P<form>[^\s;()]+) \([to]=[^)]*\)\s*(?P<gloss>[^;]*?)\s*-\s*"
                        r"(?P<code>[GH]\d+[A-Za-z]?)=(?P<morph>\S+) in: (?P<eds>[\w+]+)")
SPELLING_RE = re.compile(r"(?P<eds>[\w+]+): (?P<form>[^\s;]+)")


def tokenize(text: str):
    """Split verse text into tokens with leading/trailing punctuation."""
    tokens = []
    text = "".join(c for c in text if c not in SBL_SIGLA)
    for chunk in text.split():
        lead, word, trail = split_punct(chunk)
        if not word:                     # stray punctuation: attach to previous
            if tokens:
                tokens[-1]["trailing"] = tokens[-1]["trailing"].rstrip() + " " + chunk
            continue
        tokens.append({"surface": word, "surface_norm": norm_greek(word),
                       "leading": lead, "trailing": trail + " "})
    if tokens:
        tokens[-1]["trailing"] = tokens[-1]["trailing"].rstrip()
    return tokens


def _strongs(code: str):
    m = re.search(r"([GH])(\d+)([A-Za-z]?)$", code)
    if not m:
        return None, None
    return f"{m.group(1)}{int(m.group(2)):04d}", code


def parse_tagnt(text: str, step_book: str, chapter: int):
    """Rows for one chapter: dicts with verse, word, morphemes, gloss, ..."""
    return parse_tagnt_book(text, step_book).get(chapter, [])


def parse_tagnt_book(text: str, step_book: str) -> dict:
    """{chapter: [row, ...]} for one book of a TAGNT file."""
    chapters = {}
    for line in text.splitlines():
        if not line.startswith(step_book + "."):
            continue
        f = line.split("\t")
        m = TAGNT_REF.match(f[0])
        if not m or m.group(1) != step_book:
            continue
        rows = chapters.setdefault(int(m.group(2)), [])
        word = f[1].split(" (")[0].strip()
        translit = f[1][f[1].find("(") + 1:f[1].rfind(")")] if "(" in f[1] else None
        grammar = [g.split("«")[-1] for g in f[3].split(" + ")]
        lemmas = f[4].split(" + ")
        morphemes = []
        for i, g in enumerate(grammar):
            code, _, morph = g.partition("=")
            base, ext = _strongs(code)
            # crasis (κἀγώ = ἐγώ + καί) has one lemma field for two parts: leave the
            # per-part lemma empty; it is filled from the Strong's entry later.
            lem, _, gl = (lemmas[i] if len(lemmas) == len(grammar) else "").partition("=")
            morphemes.append({"position": i + 1, "role": "stem", "surface": word,
                              "lemma": lem or None, "strongs": base, "strongs_ext": ext,
                              "morph_code": morph or None, "gloss": gl or None})
        # SBL readings TAGNT records as variants of this word:
        #   meaning variant  "ὄχλους (t=ochlous) crowds - G3793=N-APM in: Tyn+SBL+…"  (own tags)
        #   spelling variant "SBL+WH+…: εἰσὶ ;"                                         (same tags)
        alts = []
        for vm in VARIANT_RE.finditer(f[6] if len(f) > 6 else ""):
            if "SBL" in vm["eds"].split("+"):
                base, ext = _strongs(vm["code"])
                alts.append({"norm": norm_greek(vm["form"]), "gloss": vm["gloss"].strip() or f[2],
                             "morphemes": [{"position": 1, "role": "stem", "surface": vm["form"], "lemma": None,
                                            "strongs": base, "strongs_ext": ext, "morph_code": vm["morph"],
                                            "gloss": vm["gloss"].strip() or None}]})
        for sm_ in SPELLING_RE.finditer(f[7] if len(f) > 7 else ""):
            if "SBL" in sm_["eds"].split("+"):
                alts.append({"norm": norm_greek(sm_["form"]), "gloss": f[2], "morphemes": morphemes})
        rows.append({"verse": int(m.group(3)), "ref": f[0].split("=")[0], "word": word,
                     "norm": norm_greek(word), "translit": translit, "gloss": f[2],
                     "grammar_raw": f[3], "lemma_raw": f[4], "editions": f[5],
                     "morphemes": morphemes, "alts": alts})
    return chapters


def align(sbl_verses, tagnt_rows):
    """Attach TAGNT tags to SBLGNT tokens by (verse, normalized form) sequence
    alignment. Returns list of unaligned (verse, surface) for the report."""
    flat = [(v["verse"], t) for v in sbl_verses for t in v["tokens"]]
    a = [(vn, t["surface_norm"]) for vn, t in flat]
    b = [(r["verse"], r["norm"]) for r in tagnt_rows]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    used = set()
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "replace" and i2 - i1 == j2 - j1:
            # same number of words, same verses: spelling variants (movable nu, elision,
            # 'παρέλαβε' vs 'παρέλαβεν') pair up if the forms are close
            pairs = [(k, k) for k in range(i2 - i1)
                     if a[i1 + k][0] == b[j1 + k][0]
                     and difflib.SequenceMatcher(None, a[i1 + k][1], b[j1 + k][1]).ratio() >= 0.75]
        elif op == "equal":
            pairs = [(k, k) for k in range(i2 - i1)]
        else:
            continue
        for k, _ in pairs:
            used.add(j1 + k)
            tok, row = flat[i1 + k][1], tagnt_rows[j1 + k]
            tok.update({"source_ref": row["ref"], "lemma_raw": row["lemma_raw"],
                        "morph_raw": row["grammar_raw"], "gloss": row["gloss"],
                        "translit": row["translit"], "tag_status": "aligned",
                        "morphemes": [dict(m, surface=tok["surface"]) for m in row["morphemes"]],
                        "not_in_sbl": "SBL" not in row["editions"]})
    # Further passes, order-independent, for words the in-order alignment missed:
    #   B exact form in the same verse (word-order variants: SBLGNT transposes a phrase)
    #   C an SBL reading TAGNT records as a variant of a word in the same verse (own tags)
    #   D a close spelling in the same verse
    #   E exact form or SBL variant in a neighbouring verse (verse divisions that start differently)
    def tag(tok, row, alt=None):
        src = alt or row
        tok.update({"source_ref": row["ref"], "lemma_raw": row["lemma_raw"],
                    "morph_raw": row["grammar_raw"] if alt is None else None,
                    "gloss": src["gloss"], "translit": row["translit"] if alt is None else None,
                    "tag_status": "aligned",
                    "morphemes": [dict(m, surface=tok["surface"]) for m in src["morphemes"]],
                    "not_in_sbl": "SBL" not in row["editions"]})
    free = defaultdict(list)
    for j, row in enumerate(tagnt_rows):
        if j not in used:
            free[row["verse"]].append(j)
    ratio = lambda x, y: difflib.SequenceMatcher(None, x, y).ratio()

    def find(norm, verses, mode):
        for vv in verses:
            for j in free.get(vv, []):
                row = tagnt_rows[j]
                if mode == "exact" and row["norm"] == norm:
                    return vv, j, None
                if mode == "alt":
                    alt = next((a for a in row["alts"] if a["norm"] == norm), None)
                    if alt:
                        return vv, j, alt
        if mode == "fuzzy":
            cands = [(ratio(norm, tagnt_rows[j]["norm"]), vv, j) for vv in verses for j in free.get(vv, [])]
            best = max(cands, default=None)
            if best and best[0] >= 0.75:
                return best[1], best[2], None
        return None

    for scope, mode in (("same", "exact"), ("same", "alt"), ("same", "fuzzy"), ("near", "exact"), ("near", "alt")):
        for vn, tok in flat:
            if tok.get("tag_status") == "aligned":
                continue
            verses = [vn] if scope == "same" else [vn - 1, vn + 1]
            hit = find(tok["surface_norm"], verses, mode)
            if hit:
                vv, j, alt = hit
                tag(tok, tagnt_rows[j], alt)
                free[vv].remove(j)
    unaligned = [(vn, t["surface"]) for vn, t in flat if t.get("tag_status") != "aligned"]
    for _, t in flat:
        t.setdefault("tag_status", "unaligned")
    return unaligned
