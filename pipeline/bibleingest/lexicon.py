"""Strong's Hebrew & Greek dictionaries (OpenScriptures XML, public domain)
and STEP morphology-code expansions (TEHMC / TEGMC, CC BY 4.0)."""
import re
import xml.etree.ElementTree as ET

OSIS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"


def _render(el, lang="H") -> str:
    """Flatten mixed content; inline <w>/<strongsref>/<greek> become readable text."""
    parts = [el.text or ""]
    for ch in el:
        tag = ch.tag.replace(OSIS, "")
        if tag == "w":
            lem, src = ch.get("lemma"), ch.get("src")
            parts.append(f"{lem or ''}{f' ({lang}{src})' if src else ''}{ch.text or ''}")
        elif tag == "strongsref":
            parts.append(("H" if ch.get("language") == "HEBREW" else "G") + ch.get("strongs").lstrip("0"))
        elif tag == "greek":
            parts.append(ch.get("unicode") or "")
        else:
            parts.append(_render(ch, lang))
        parts.append(ch.tail or "")
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def strongs_hebrew(xml_text: str):
    root = ET.fromstring(xml_text)
    for div in root.iter(OSIS + "div"):
        if div.get("type") != "entry":
            continue
        w = div.find(OSIS + "w")
        if w is None or not w.get("ID"):
            continue
        n = int(w.get("ID")[1:])
        notes = {n_.get("type"): _render(n_) for n_ in div.findall(OSIS + "note")}
        items = [_render(i) for i in div.iter(OSIS + "item")]
        yield {"entry_key": f"H{n:04d}", "links": [(f"H{n:04d}", None)], "extra": None,
               "strongs": f"H{n:04d}", "lemma": w.get("lemma") or (w.text or ""),
               "translit": w.get("xlit"), "pronunciation": w.get("POS"),
               "part_of_speech": w.get("morph"), "short_def": notes.get("explanation"),
               "definition": "\n".join(items) or None, "derivation": notes.get("exegesis"),
               "kjv_usage": notes.get("translation")}


def strongs_greek(xml_text: str):
    root = ET.fromstring(xml_text)
    for e in root.iter("entry"):
        n = int(e.get("strongs"))
        g = e.find("greek")
        pron = e.find("pronunciation")
        get = lambda t: _render(e.find(t), "G") if e.find(t) is not None else None
        kjv = get("kjv_def")
        yield {"entry_key": f"G{n:04d}", "links": [(f"G{n:04d}", None)], "extra": None,
               "strongs": f"G{n:04d}", "lemma": g.get("unicode") if g is not None else "",
               "translit": g.get("translit") if g is not None else None,
               "pronunciation": pron.get("strongs") if pron is not None else None,
               # some entries carry the definition only in <strongs_derivation>
               "part_of_speech": None, "short_def": get("strongs_def") or get("strongs_derivation"),
               "definition": None,
               "derivation": get("strongs_derivation"),
               "kjv_usage": kjv.lstrip(":-").strip() if kjv else None}


def step_morph_codes(text: str):
    """Records separated by '$' lines: 'CODE\\tfields' / '\\tsummary' / '\\tdetail'."""
    blocks = text.split("\n$")
    for blk in blocks[1:]:
        lines = [l for l in blk.strip("\n").split("\n") if l.strip()]
        if not lines or "\t" not in lines[0]:
            continue
        code, _, fields = lines[0].partition("\t")
        code = code.strip().strip('"')
        if not code or " " in code:
            continue
        clean = lambda s: s.strip().strip('"').strip()
        yield {"code": code, "fields": clean(fields),
               "summary": clean(lines[1]) if len(lines) > 1 else clean(fields),
               "detail": clean(lines[2]) if len(lines) > 2 else None}


# --------------------------------------------------------------------------- BDB
OSHB = "{http://openscriptures.github.com/morphhb/namespace}"


def _bdb_text(el) -> str:
    """Flatten a BDB entry: senses on new lines, cross-references kept, status/page dropped."""
    out = []

    def walk(e):
        tag = e.tag.replace(OSHB, "")
        if tag in ("status", "page"):
            out.append(e.tail or "")
            return
        if tag == "sense":
            out.append(f"\n{e.get('n')}. " if e.get("n") else "\n")
        elif tag == "stem":
            out.append("\n")
        if tag == "w" and e.get("src") and not (e.text or "").strip():
            out.append(f"[{e.get('src')}]")
        out.append(e.text or "")
        for c in e:
            walk(c)
        out.append(e.tail or "")

    out.append(el.text or "")
    for c in el:
        walk(c)
    text = "".join(out)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*", "\n", text).strip()


def bdb(bdb_xml: str, index_xml: str):
    """Yield BDB entries with their Strong's links (from LexicalIndex xrefs)."""
    links = {}
    for e in ET.fromstring(index_xml).iter(OSHB + "entry"):
        for x in e.iter(OSHB + "xref"):
            st = x.get("strong")
            if not (x.get("bdb") and st):
                continue
            if st.isalpha():                     # MorphHB prefix codes: b c d i k l m s
                links.setdefault(x.get("bdb"), set()).add((f"H{st}", f"H{st}"))
                continue
            n = int(re.match(r"\d+", st)[0])
            links.setdefault(x.get("bdb"), set()).add((f"H{n:04d}", f"H{n:04d}{x.get('aug') or ''}"))
    for e in ET.fromstring(bdb_xml).iter(OSHB + "entry"):
        words = [w.text for w in e.findall(OSHB + "w") if w.text]
        defs = [d.text for d in e.iter(OSHB + "def") if d.text]
        pos = e.find(OSHB + "pos")
        status = e.find(OSHB + "status")
        lk = sorted(links.get(e.get("id"), ()))
        yield {"entry_key": e.get("id"), "strongs": lk[0][0] if lk else None,
               "lemma": words[0] if words else "", "translit": None, "pronunciation": None,
               "part_of_speech": pos.text if pos is not None else None,
               "short_def": ", ".join(dict.fromkeys(defs[:4])) or None,
               "definition": _bdb_text(e), "derivation": None, "kjv_usage": None,
               "extra": {"status": status.text if status is not None else None,
                         "mod": e.get("mod"), "type": e.get("type")},
               "links": lk}


# --------------------------------------------------------------------------- Thayer
def thayer_ep(md_files):
    """Every-Promise Thayer markdown: '### lemma — translit' / '`Strong's G123`' / body."""
    for text in md_files:
        for blk in text.split("\n---\n"):
            m = re.search(r"###\s*(.+?)(?:\s+—\s+(.+?))?\n`Strong's G(\d+)`\n\n(.*)", blk, re.S)
            if not m:
                continue
            lemma, translit, n, body = m[1].strip(), (m[2] or "").strip() or None, int(m[3]), m[4].strip()
            first = re.split(r"\n\s*\n", body)[0]
            yield {"entry_key": f"G{n:04d}", "strongs": f"G{n:04d}", "lemma": lemma,
                   "translit": translit, "pronunciation": None, "part_of_speech": None,
                   "short_def": (first[:240] + "…") if len(first) > 240 else first,
                   "definition": re.sub(r"\n{3,}", "\n\n", body), "derivation": None,
                   "kjv_usage": None, "extra": None, "links": [(f"G{n:04d}", None)]}


# --------------------------------------------------------------------------- LSJ
def _html_to_text(h: str) -> str:
    h = re.sub(r"<a [^>]*>(.*?)</a>", r"\1", h, flags=re.S)       # drop tooltip links, keep label
    h = re.sub(r"<br\s*/?>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    import html as _h
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*", "\n", _h.unescape(h))).strip()


def tflsj(text: str):
    """STEP TFLSJ rows: eStrong, 'dStrong =', uStrong, Greek, translit, morph, gloss, LSJ (HTML)."""
    for line in text.splitlines():
        f = line.split("\t")
        if len(f) < 8 or not re.match(r"^G\d+$", f[0]):
            continue
        estrong, dstrong = f[0], f[1].split(" =")[0].strip()
        n = int(estrong[1:])
        base = f"G{n:04d}" if n <= 5624 else None
        links = {(base or f"G{n:04d}", dstrong or None)}
        # entry_key = disambiguated number: G0001G (alpha) and G0001H (ah!) share eStrong G0001
        yield {"entry_key": dstrong or estrong, "strongs": base, "lemma": f[3].split(",")[0].strip(),
               "translit": f[4] or None, "pronunciation": None, "part_of_speech": f[5] or None,
               "short_def": f[6] or None, "definition": _html_to_text(f[7]), "derivation": None,
               "kjv_usage": None, "extra": {"step_morph": f[5], "ustrong": f[2]} if f[2] else None,
               "links": sorted(links)}
