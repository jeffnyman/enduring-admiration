"""Minimal USFM chapter parser (eBible.org flavour).

Returns verse records with plain text, rich runs (paragraphs, poetry,
words of Jesus), notes, and the paragraph/heading that opens each verse.
"""
import re
from collections import defaultdict

PARA = {"p", "m", "nb", "pi", "pi1", "pi2", "mi", "pc", "pm", "pmo", "pmc", "pmr", "b",
        "q", "q1", "q2", "q3", "q4", "qr", "qc", "qm", "qm1", "qm2", "li", "li1", "li2",
        "li3", "lim", "lim1", "lim2", "cls", "po"}
HEADING = {"s", "s1", "s2", "s3", "s4", "d", "ms", "ms1", "ms2", "mr", "sr", "r", "sp",
           "qa", "cl", "cd"}
MARKER = re.compile(r"\\(\+?)([a-z]+\d*)(?:(\*)|\s?)")  # opening markers eat one space
NOTE = re.compile(r"\\(f|fe|x)\s+(.*?)\\\1\*", re.S)
ATTRS = re.compile(r"\|[^\\|]*(?=\\\+?[a-z]+\d*\*)")


def _note_text(raw: str) -> str:
    raw = re.sub(r"^\S+\s*", "", raw.strip())            # caller (+, -, a)
    raw = re.sub(r"\\(fr|xo)\s+[^\\]*", "", raw)         # reference labels
    raw = re.sub(r"\\\+?[a-z]+\d*\*?\s?", "", raw)
    return re.sub(r"\s+", " ", raw).strip()


def _scan(seg: str):
    """Yield ('text', s) | ('para', style) | ('heading', text) | ('wj', bool)."""
    pos = 0
    for m in MARKER.finditer(seg):
        if m.start() < pos:
            continue
        if m.start() > pos:
            yield ("text", seg[pos:m.start()])
        plus, name, close = m.groups()
        pos = m.end()
        if name == "wj":
            yield ("wj", not close)
        elif name in PARA and not close:
            yield ("para", name)
        elif name in HEADING and not close:
            end = seg.find("\n", pos)
            end = len(seg) if end < 0 else end
            # \d = canonical Psalm title (TVTMS "TextBeforeV1"); others are editorial headings
            yield ("title" if name == "d" else "heading", ATTRS.sub("", seg[pos:end]).strip())
            pos = end
        # other character markers (w, add, nd, bk, ...): drop marker, keep content
    if pos < len(seg):
        yield ("text", seg[pos:])


def parse_book(usfm: str, note_kind_f: str = "footnote") -> dict:
    """{chapter: [verse, ...]} for a whole book (split once)."""
    parts = re.split(r"\\c\s+(\d+)\s*", usfm)
    return {int(parts[i]): _parse_block(parts[i + 1], note_kind_f) for i in range(1, len(parts), 2)}


def parse_chapter(usfm: str, chapter: int, note_kind_f: str = "footnote"):
    parts = re.split(r"\\c\s+(\d+)\s*", usfm)
    for i in range(1, len(parts), 2):
        if int(parts[i]) == chapter:
            return _parse_block(parts[i + 1], note_kind_f)
    raise ValueError(f"chapter {chapter} not found")


def _parse_block(block: str, note_kind_f: str):

    # verse markers: '7', '7a' (lettered part), '15-16' (range)
    pieces = re.split(r"\\v\s+(\d+)([a-z]?)(?:-(\d+)[a-z]?)?\s*", block)
    carry_para, carry_heading, carry_title = None, None, False
    for item in _scan(ATTRS.sub("", NOTE.sub("", pieces[0]))):
        if item[0] == "para":
            carry_para = item[1]
        elif item[0] in ("heading", "title"):
            carry_heading, carry_title = item[1], carry_title or item[0] == "title"

    verses, wj = [], False   # words-of-Jesus spans can cross verse boundaries
    for i in range(1, len(pieces), 4):
        vnum, part, vend, seg = int(pieces[i]), pieces[i + 1] or "", pieces[i + 2], pieces[i + 3]
        notes = [("crossref" if k == "x" else note_kind_f, _note_text(t))
                 for k, t in NOTE.findall(seg)]
        seg = ATTRS.sub("", NOTE.sub("", seg))
        items = list(_scan(seg))
        # paragraph/heading markers after the last text belong to the next verse
        tail = []
        while items and (items[-1][0] in ("para", "heading", "title") or
                         (items[-1][0] == "text" and not items[-1][1].strip())):
            tail.insert(0, items.pop())
        runs = []
        for kind, val in items:
            if kind == "wj":
                wj = val
            elif kind == "para":
                runs.append({"para": val})
            elif kind == "title":
                pass                                 # mid-verse title marker: ignore
            elif kind == "text":
                t = re.sub(r"\s+", " ", val)
                if runs and "t" in runs[-1] and bool(runs[-1].get("wj")) == wj:
                    runs[-1]["t"] += t
                else:
                    runs.append({"t": t, **({"wj": 1} if wj else {})})
        text = re.sub(r"\s+", " ", "".join(r.get("t", " ") for r in runs)).strip()
        verses.append({
            "verse": vnum, "part": part, "verse_end": int(vend) if vend else None,
            "text": text, "runs": runs, "notes": notes,
            "para_before": carry_para, "heading_before": carry_heading, "title_before": carry_title,
        })
        carry_para, carry_heading, carry_title = None, None, False
        for kind, val in tail:
            if kind == "para":
                carry_para = val
            elif kind in ("heading", "title"):
                carry_heading, carry_title = val, carry_title or kind == "title"
    return verses


LETTERS = [c for c in "abcdefghijklmnopqrstuvwxyz"] + ["a" + c for c in "abcdefghijklmnopqrstuvwxyz"]


def ordinal_parts(verses):
    """Brenton letters subverses skipping j and v (… 17i, 17k …); TVTMS letters them
    consecutively. Re-letter each verse's parts by position; keep Brenton's label."""
    seen = defaultdict(list)
    for v in verses:
        if v["part"]:
            seen[v["verse"]].append(v)
    for vn, parts in seen.items():
        for i, v in enumerate(parts):
            if v["part"] != LETTERS[i]:
                v["brenton_part"], v["part"] = v["part"], LETTERS[i]
