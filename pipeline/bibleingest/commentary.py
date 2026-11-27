"""Commentaries: parse four openly licensed sources into neutral entries.

Each parser yields Entry objects with references in the source's own (English, KJV-style)
numbering; build_bible.py resolves them to Standard verses and stores them. Bodies are converted
to a small, fixed set of HTML tags by this module (all text escaped), so the reader can show them
without trusting the source markup.

- Tyndale Open Study Notes (custom XML)               CC BY-SA 4.0
- unfoldingWord Translation Notes (TSV + Markdown)    CC BY-SA 4.0
- Catena Aurea, Newman's translation (OSIS, lemtom)   CC0 / public domain
- Keil & Delitzsch (CrossWire SWORD zCom4 module)     public domain (via Wikisource, CC BY-SA)
"""
from __future__ import annotations

import html
import io
import re
import struct
import xml.etree.ElementTree as ET
import zipfile
import zlib
from dataclasses import dataclass, field

from .books import BOOKS

# Shown to readers on the Sources and About-the-texts pages and in the study panel. The
# tradition lines are meant to help a student weigh what each voice brings.
COMMENTARIES = [
    dict(id="tyndale", source_id="tyndale-osn", title="Tyndale Open Study Notes", short_title="Tyndale",
         author="Tyndale House Publishers", written="2022",
         tradition="Evangelical Protestant study Bible",
         description="Modern study-Bible notes for general readers: historical background, meaning and theology, "
                     "with book introductions, theme articles and profiles of people. The phrases it quotes come "
                     "from the New Living Translation, so they won't always match the WEB's wording."),
    dict(id="uw", source_id="uw-tn", title="Translation Notes", short_title="Language notes", author=None,
         written="2026 (release v92)",
         tradition="Evangelical, written for Bible translators",
         description="Notes on the Hebrew and Greek words themselves: idioms, figures of speech, implied meaning "
                     "and grammar. Each note is linked to the words it explains. Many notes are about translation "
                     "technique (passive verbs, pronouns, word order); those are hidden unless you ask for them. "
                     "Its Greek follows a slightly different text from the SBLGNT, so a few notes can't point to "
                     "their words."),
    dict(id="catena", source_id="catena-lemtom", title="Catena Aurea", short_title="Catena (Fathers)",
         author="Thomas Aquinas (compiler); English translation under J. H. Newman", written="c. 1263; English 1841–45",
         tradition="The Church Fathers, as gathered by a medieval Catholic theologian: shared heritage of "
                   "Catholic, Orthodox and Protestant readers",
         description="A 'golden chain' of comments from the Church Fathers (Chrysostom, Augustine, Jerome, "
                     "Gregory and many others) on the four Gospels, passage by passage. Each comment names its "
                     "Father and work. Covers the Gospels only."),
    dict(id="kd", source_id="crosswire-kd", title="Biblical Commentary on the Old Testament", short_title="Keil & Delitzsch",
         author="C. F. Keil and F. Delitzsch", written="German 1860s–70s; English translation (T&T Clark)",
         tradition="Conservative German Lutheran scholarship of the 19th century",
         description="A detailed scholarly commentary on the Hebrew text of the whole Old Testament: grammar, "
                     "history and theology. It predates modern archaeology and discoveries such as the Ugaritic "
                     "texts and the Dead Sea Scrolls. In this digital edition its Hebrew is unpointed and has "
                     "transcription errors."),
]

# ------------------------------------------------------------------------------ references
# book abbreviations seen in the sources -> our ids (OSIS names come from BOOKS)
ALIASES = {
    "Pr": "PRO", "Pro": "PRO", "Hagg": "HAG", "Jon": "JON", "Jonah": "JON", "1Jn": "1JN", "2Jn": "2JN",
    "3Jn": "3JN", "1Thes": "1TH", "2Thes": "2TH", "1Th": "1TH", "1Ki": "1KI", "2Ki": "2KI", "1Sa": "1SA",
    "2Ch": "2CH", "Act": "ACT", "Amo": "AMO", "Cant": "SNG", "Son": "SNG", "Deu": "DEU", "Ecc": "ECC",
    "Exo": "EXO", "Eze": "EZK", "Is": "ISA", "Jam": "JAS", "Joe": "JOL", "Luc": "LUK", "Numb": "NUM",
    "Phi": "PHP", "Tit": "TIT", "Tobit": "TOB", "Wisdom": "WIS", "Zec": "ZEC", "Jos": "JOS",
}
BOOK_IDS = {b[1]: b[0] for b in BOOKS} | {b[0]: b[0] for b in BOOKS} | ALIASES

Ref = tuple[str, int, int, int, int]  # book, chapter, verse, end chapter, end verse


def osis_ref(s: str) -> Ref | None:
    """'Gen.1.1', 'Gen.1.1-2.3', 'Gen.1.1-3', 'Matt.1.3-Matt.1.5', 'John.1.1!a' -> Ref."""
    s = re.sub(r"![a-z]+", "", s.strip())
    a, _, b = s.partition("-")
    pa = a.split(".")
    if len(pa) != 3 or pa[0] not in BOOK_IDS or not (pa[1].isdigit() and pa[2].isdigit()):
        return None
    book, c1, v1 = BOOK_IDS[pa[0]], int(pa[1]), int(pa[2])
    c2, v2 = c1, v1
    if b:
        pb = b.split(".")
        if len(pb) == 3 and pb[0] in BOOK_IDS:
            pb = pb[1:]                                   # 'Matt.1.5'
        nums = [int(x) for x in pb if x.isdigit()]
        if len(pb) == 1 and nums:
            v2 = nums[0]                                  # '1.1-3'
        elif len(pb) == 2 and len(nums) == 2:
            c2, v2 = nums                                 # '1.1-2.3'
        else:
            return None
    if (c2, v2) < (c1, v1):
        c2, v2 = c1, v1                                   # truncated ranges in the source: keep the start
    return book, c1, v1, c2, v2


def read_href(r: Ref) -> str:
    book, c, v = r[0], r[1], r[2]
    return f"/read/{book}/{c}#{book}-{c}-{v}"


# ------------------------------------------------------------------------------ safe HTML
def esc(s: str) -> str:
    return html.escape(s, quote=False)


def link(text_html: str, ref: Ref | None, stats=None) -> str:
    if not ref:
        if stats is not None:
            stats["links unresolved (text kept)"] += 1
        return text_html
    return f'<a href="{html.escape(read_href(ref))}">{text_html}</a>'


ALLOWED_TAGS = {"p", "strong", "em", "sup", "sub", "h4", "ul", "li", "a", "span", "br"}
_TAG = re.compile(r"</?([a-z0-9]+)([^>]*)>")


def check_html(s: str) -> list[str]:
    """Problems in generated HTML (used by the build's verification)."""
    bad = []
    for m in _TAG.finditer(s):
        tag, attrs = m[1], m[2].strip().rstrip("/").strip()
        if tag not in ALLOWED_TAGS:
            bad.append(f"tag {tag}")
        elif attrs and not re.fullmatch(r'(href="/read/[A-Z0-9]+/\d+#[A-Z0-9]+-\d+-\d+"|class="(sc|note|heb)")', attrs):
            bad.append(f"attr {tag} {attrs[:40]}")
    return bad


def text_of(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


@dataclass
class Entry:
    commentary: str
    kind: str                      # note | intro | article | profile
    refs: list[Ref]
    body: str                      # safe HTML
    title: str | None = None
    label: str | None = None       # unfoldingWord support reference / Father / section
    quote: str | None = None       # original-language words the note is about (unfoldingWord)
    occurrence: int = 1
    sort: int = 0
    words: list[int] = field(default_factory=list)   # token ids, filled by the build


# ------------------------------------------------------------------------------ Tyndale
TYNDALE_FILES = {"StudyNotes.xml": "note", "ThemeNotes.xml": "article", "Profiles.xml": "profile",
                 "BookIntros.xml": "intro", "BookIntroSummaries.xml": "intro"}
_SC = {"era", "sc", "sn-ref-sc", "divine-name", "sn-excerpt-divine-name", "divine-name-ital", "sn-excerpt-sc"}
_EM = {"ital", "hebrew", "greek", "latin", "aramaic", "ital-bold", "sn-excerpt-roman"}
_STRONG = {"sn-excerpt", "bold", "sn-ref", "intro-h2"}


def _tyndale_inline(el, stats) -> str:
    out = [esc(el.text or "")]
    for ch in el:
        inner = _tyndale_inline(ch, stats)
        cls = ch.get("class", "")
        if ch.tag == "a":
            href = ch.get("href", "")
            out.append(link(inner, osis_ref(href.split("bref=", 1)[1]) if "bref=" in href else None, stats))
        elif ch.tag == "span" and cls in _SC:
            out.append(f'<span class="sc">{inner}</span>')
        elif ch.tag == "span" and cls in _EM:
            out.append(f"<em>{inner}</em>")
        elif ch.tag == "span" and cls in _STRONG:
            out.append(f"<strong>{inner}</strong>")
        elif ch.tag == "span" and cls == "sn-hebrew-chars":
            out.append(f'<span class="heb">{inner}</span>')
        elif ch.tag == "span" and cls in ("sup", "sub"):
            out.append(f"<{cls}>{inner}</{cls}>")
        else:
            out.append(inner)
        out.append(esc(ch.tail or ""))
    return "".join(out)


def _tyndale_body(body, stats) -> str:
    parts = []
    for p in body:
        cls = p.get("class", "")
        if cls.endswith("-title") and not cls.endswith("refs-title"):
            continue                                       # stored as the entry's title
        inner = _tyndale_inline(p, stats).strip()
        if not inner:
            continue
        if cls.endswith("-h1") or cls.endswith("refs-title") or cls == "intro-sidebar-h1":
            parts.append(f"<h4>{inner}</h4>")
        else:
            parts.append(f"<p>{inner}</p>")
    return "".join(parts)


def tyndale(zip_bytes: bytes, stats) -> list[Entry]:
    entries = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        names = {n.rsplit("/", 1)[-1]: n for n in z.namelist()}
        for fname, kind in TYNDALE_FILES.items():
            root = ET.fromstring(z.read(names[fname]))
            for i, item in enumerate(root.iter("item")):
                refs = [r for r in (osis_ref(x) for x in re.split(r"[;,\s]+", item.findtext("refs") or "") if x) if r]
                if not refs:
                    stats[f"tyndale {fname}: no usable reference"] += 1
                    continue
                k = "profile" if item.get("typename") == "Profile" else kind
                title = (item.findtext("title") or "").strip() or None
                if fname == "BookIntroSummaries.xml":
                    title = f"{title or ''} at a glance".strip()
                entries.append(Entry("tyndale", k, refs, _tyndale_body(item.find("body"), stats), title=title,
                                     label=item.get("name"), sort=i))
    return entries


# ------------------------------------------------------------------------------ OSIS fragments (Catena, K&D)
_OSIS_TOKEN = re.compile(r"<(/?)([A-Za-z]+)((?:\s+[A-Za-z:]+=\"[^\"]*\")*)\s*(/?)>|([^<]+)")


def osis_html(frag: str, stats) -> str:
    """OSIS markup -> safe HTML. Paragraph milestones and <p> become paragraphs; hi, title,
    reference, note, list/item are mapped; everything else keeps only its text."""
    out, stack, para_open = [], [], False

    def open_p():
        nonlocal para_open
        if not para_open:
            out.append("<p>")
            para_open = True

    def close_p():
        nonlocal para_open
        if para_open:
            out.append("</p>")
            para_open = False

    for m in _OSIS_TOKEN.finditer(frag):
        if m[5] is not None:
            text = html.unescape(m[5])
            if text.strip():
                open_p()
            out.append(esc(text))
            continue
        closing, tag, attrs, selfclose = m[1] == "/", m[2], m[3] or "", m[4] == "/"
        a = dict(re.findall(r'([A-Za-z:]+)="([^"]*)"', attrs))
        if tag in ("p", "lg", "l") or (tag == "div" and ("sID" in a or "eID" in a or selfclose)):
            close_p()
            continue
        if tag in ("chapter", "verse", "milestone", "lb", "div", "work", "osisText", "osis", "header"):
            continue
        if selfclose:
            continue
        if closing:
            want = stack.pop() if stack else None
            if want:
                out.append(want)
            continue
        if tag == "title":
            close_p()
            out.append("<h4>")
            stack.append("</h4>")
        elif tag == "hi":
            t = a.get("type", "")
            open_p()
            if t == "bold":
                out.append("<strong>"); stack.append("</strong>")
            elif t in ("super", "superscript"):
                out.append("<sup>"); stack.append("</sup>")
            elif t in ("small-caps", "smallCaps"):
                out.append('<span class="sc">'); stack.append("</span>")
            else:
                out.append("<em>"); stack.append("</em>")
        elif tag == "reference":
            open_p()
            r = osis_ref(a["osisRef"].split(" ")[0]) if a.get("osisRef") else None
            if r:
                out.append(f'<a href="{html.escape(read_href(r))}">'); stack.append("</a>")
            else:
                if a.get("osisRef"):
                    stats["links unresolved (text kept)"] += 1
                stack.append("")
        elif tag == "note":
            open_p()
            out.append('<span class="note">('); stack.append(")</span>")
        elif tag == "list":
            close_p()
            out.append("<ul>"); stack.append("</ul>")
        elif tag == "item":
            out.append("<li>"); stack.append("</li>")
        else:
            stack.append("")
    while stack:
        out.append(stack.pop())
    close_p()
    s = "".join(out)
    s = re.sub(r"<p>\s*</p>|<h4>\s*</h4>", "", s)
    return re.sub(r"[ \t\n]+", " ", s).strip()


def catena(xml_text: str, stats) -> list[Entry]:
    """Catena Aurea: one entry per annotated section (the Fathers' comments on a passage)."""
    entries = []
    starts = list(re.finditer(r'<div annotateRef="([^"]+)"[^>]*>', xml_text))
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(xml_text)
        chunk = xml_text[m.end():end]
        r = osis_ref(m[1].split(" ")[0])
        if not r:
            stats["catena: unresolved section"] += 1
            continue
        body = osis_html(chunk, stats)
        fathers = []
        for name in re.findall(r"<strong>([^<]{2,80}?):?</strong>", body):
            short = re.split(r"[,.(]", name)[0].strip()
            if short and short not in fathers:
                fathers.append(short)
        entries.append(Entry("catena", "note", [r], body, label=", ".join(fathers[:12]) or None, sort=i))
    return entries


# ------------------------------------------------------------------------------ Keil & Delitzsch (SWORD zCom4)
KJV_OT = ("GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER "
          "LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL").split()


def kjv_counts(kjv_zip: bytes) -> dict[str, list[int]]:
    """Verses per chapter in the KJV (eBible eng-kjv2006 USFM): the SWORD 'KJV' versification."""
    counts = {}
    with zipfile.ZipFile(io.BytesIO(kjv_zip)) as z:
        for b in KJV_OT:
            [name] = [n for n in z.namelist() if n.endswith(f"{b}eng-kjv2006.usfm")]
            ch, c = {}, 0
            for m in re.finditer(r"\\(c|v) (\d+)", z.read(name).decode("utf-8-sig")):
                if m[1] == "c":
                    c = int(m[2]); ch[c] = 0
                else:
                    ch[c] = max(ch[c], int(m[2]))
            counts[b] = [ch[i] for i in sorted(ch)]
    return counts


def keil_delitzsch(module_zip: bytes, counts: dict[str, list[int]], stats) -> list[Entry]:
    with zipfile.ZipFile(io.BytesIO(module_zip)) as z:
        part = lambda ext: z.read(next(n for n in z.namelist() if n.endswith(f"/ot.bz{ext}")))
        bzs, bzv, bzz = part("s"), part("v"), part("z")
    slots = 2 + sum(1 + sum(1 + n for n in c) for c in counts.values())
    if slots != len(bzv) // 12:
        raise RuntimeError(f"K&D index has {len(bzv) // 12} slots, KJV versification gives {slots}")
    blocks: dict[int, bytes] = {}

    def get(i):
        blk, off, size = struct.unpack("<III", bzv[i * 12:i * 12 + 12])
        if not size:
            return None, ""
        if blk not in blocks:
            o, s, _ = struct.unpack("<III", bzs[blk * 12:blk * 12 + 12])
            blocks[blk] = zlib.decompress(bzz[o:o + s])
        return (blk, off, size), blocks[blk][off:off + size].decode("utf-8")

    entries, i = [], 2
    for book in KJV_OT:
        i += 1                                             # book heading slot
        prev_key, cur = None, None
        for c, nv in enumerate(counts[book], 1):
            i += 1                                         # chapter heading slot
            for v in range(1, nv + 1):
                key, text = get(i)
                i += 1
                if key is None:
                    prev_key = None
                    continue
                if key == prev_key and cur is not None:    # a linked verse: same comment covers it
                    cur.refs[0] = (book, cur.refs[0][1], cur.refs[0][2], c, v)
                    continue
                prev_key = key
                body = osis_html(text, stats)
                if not text_of(body):
                    continue
                # the module keeps each book's introduction with the comment on its first verse
                title = ("Introduction to the book, with the comment on its opening verses"
                         if (c, v) == (1, 1) and len(body) > 15000 else None)
                cur = Entry("kd", "note", [(book, c, v, c, v)], body, title=title, sort=len(entries))
                entries.append(cur)
    return entries


# ------------------------------------------------------------------------------ unfoldingWord
# Notes about how to translate rather than what the text means: kept, but hidden by default.
UW_MECHANICS = re.compile(
    r"figs-(abstractnouns|activepassive|possession|nominaladj|genericnoun|gendernotations|infostructure|"
    r"quotesinquotes|go|you\w*|exclusive|inclusive|pastforfuture|events|declarative|imperative|123person)"
    r"|writing-(pronouns|quotations|participants|newevent|endofstory|background-hidden)"
    r"|grammar-|translate-(numbers|ordinal|fraction|bdistance|bmoney|bvolume|bweight|hebrewmonths|names|transliterate)")


def uw_markdown(md: str, stats) -> str:
    md = md.replace("\\n", "\n")
    md = re.sub(r"\(See:\s*\[\[rc://[^\]]+\]\][^)]*\)", "", md)
    md = re.sub(r"\[\[rc://[^\]]+\]\]", "", md)
    out, in_list = [], False

    def inline(s):
        s = esc(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
        s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)     # links to other notes: keep the words
        return s

    for line in md.split("\n"):
        line = line.rstrip()
        if not line.strip():
            continue
        if re.match(r"\s*[*-] ", line):
            if not in_list:
                out.append("<ul>"); in_list = True
            item = re.sub(r"^\s*[*-] ", "", line)
            out.append(f"<li>{inline(item)}</li>")
            continue
        if in_list:
            out.append("</ul>"); in_list = False
        h = re.match(r"(#{1,6})\s+(.*)", line)
        out.append(f"<h4>{inline(h[2])}</h4>" if h else f"<p>{inline(line)}</p>")
    if in_list:
        out.append("</ul>")
    return "".join(out)


def unfoldingword(zip_bytes: bytes, stats) -> list[Entry]:
    entries = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for name in sorted(n for n in z.namelist() if re.search(r"/tn_[0-9A-Z]{3}\.tsv$", n)):
            book = name.rsplit("_", 1)[1][:3]
            if book not in BOOK_IDS:
                stats[f"unfoldingWord: unknown book {book}"] += 1
                continue
            for i, line in enumerate(z.read(name).decode("utf-8-sig").splitlines()[1:]):
                f = line.split("\t")
                if len(f) < 7:
                    stats["unfoldingWord: short row"] += 1
                    continue
                ref, nid, _tags, support, quote, occ, note = f[:7]
                support = support.rsplit("/", 1)[-1] if support else None
                body = uw_markdown(note, stats)
                if not text_of(body):
                    continue
                ch, _, vs = ref.partition(":")
                if ch == "front":                          # book introduction
                    entries.append(Entry("uw", "intro", [(book, 1, 1, 1, 1)], body, title="Introduction",
                                         label=support, sort=i))
                    continue
                if not ch.isdigit():
                    stats["unfoldingWord: bad reference"] += 1
                    continue
                c = int(ch)
                if vs == "intro":                          # chapter introduction, shown at its first verse
                    entries.append(Entry("uw", "note", [(book, c, 1, c, 1)], body, title=f"Introduction to chapter {c}",
                                         label="chapter-intro", sort=i))
                    continue
                if vs == "front":
                    v1 = v2 = 0                            # psalm title
                else:
                    nums = [int(x) for x in re.split(r"[-,]", vs) if x.isdigit()]
                    if not nums:
                        stats["unfoldingWord: bad reference"] += 1
                        continue
                    v1, v2 = nums[0], nums[-1]
                quote = quote.replace("⁠", "").strip() or None
                entries.append(Entry("uw", "note", [(book, c, v1, c, v2)], body, label=support, quote=quote,
                                     occurrence=int(occ) if occ.lstrip("-").isdigit() else 1, sort=i))
    return entries
