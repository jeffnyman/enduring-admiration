"""OpenScriptures Hebrew Bible (MorphHB) OSIS parser.

<w lemma="b/7225" morph="HR/Ncfsa" id="01xeN">בְּ/רֵאשִׁ֖ית</w>
  - text and morph are split by '/' into the same number of segments
  - lemma lists prefixes + the main lemma; pronominal suffixes (morph 'S...')
    have no lemma entry
"""
import re
import xml.etree.ElementTree as ET

from .textnorm import norm_hebrew

NS = {"o": "http://www.bibletechnologies.net/2003/OSIS/namespace"}
Q = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"

PREFIX_GLOSS = {"b": "in, with, by", "c": "and", "d": "the", "i": "interrogative particle",
                "k": "like, as", "l": "to, for", "m": "from", "s": "which, that"}


def _strongs(lemma_part: str):
    m = re.fullmatch(r"(\d+)\s*([a-z])?\+?", lemma_part.strip())
    if not m:
        return None, None
    n, letter = int(m.group(1)), m.group(2)
    return f"H{n:04d}", f"H{n:04d}{letter or ''}"


def split_word(text: str, lemma: str, morph: str):
    """Return (morphemes, anomaly-or-None).

    Lemma parts go to the non-suffix codes in order (prefixes, then the stem). A code
    after the stem with no lemma left (Aramaic emphatic 'Td') is a suffix. Lemma parts
    left over after that belong to pronominal suffixes: MorphHB gives 'in them'
    (b/2004 + HR/Sp3fp) the pronoun's lemma."""
    lang, codes = morph[0], morph[1:].split("/")
    surfaces = text.split("/")
    lemmas = lemma.split("/") if lemma else []
    anomaly = None
    if len(surfaces) != len(codes):
        anomaly = f"{len(surfaces)} text segments vs {len(codes)} morph codes"
    out, li, seen_stem = [], 0, False
    for i, code in enumerate(codes):
        surf = surfaces[i] if i < len(surfaces) else ""
        m = {"position": i + 1, "surface": surf, "morph_code": lang + code,
             "lemma_part": None, "strongs": None, "strongs_ext": None, "gloss": None}
        lp = lemmas[li] if li < len(lemmas) else None
        if code.startswith("S") or (seen_stem and lp is None):
            m["role"] = "suffix"
        else:
            li += 1
            m["lemma_part"] = lp
            if lp and lp in PREFIX_GLOSS and not seen_stem:
                m["role"], m["gloss"] = "prefix", PREFIX_GLOSS[lp]
                m["strongs_ext"] = f"H{lp}"       # lexicon key for the prefix (BDB links these)
            else:
                m["role"], seen_stem = "stem", True
                m["strongs"], m["strongs_ext"] = _strongs(lp or "")
        out.append(m)
    for m in out:                                 # leftover lemma parts -> suffixes, in order
        if li >= len(lemmas):
            break
        if m["role"] == "suffix" and m["strongs"] is None and m["morph_code"][1:].startswith("S"):
            m["lemma_part"] = lemmas[li]
            m["strongs"], m["strongs_ext"] = _strongs(lemmas[li])
            li += 1
    if li != len(lemmas):
        anomaly = anomaly or f"{len(lemmas)} lemma parts, {li} used"
    return out, anomaly


def _token(w, variant="", group=None):
    raw = w.text or ""
    return {"surface": raw.replace("/", ""), "surface_norm": norm_hebrew(raw),
            "lemma_raw": w.get("lemma"), "morph_raw": w.get("morph"),
            "source_ref": w.get("id"), "variant": variant, "variant_group": group,
            "trailing": "", "leading": "", "_raw": raw}


def parse_chapter(xml_text: str, osis_book: str, chapter: int):
    return parse_book(xml_text).get(chapter, [])


def parse_book(xml_text: str) -> dict:
    """{chapter: [verse, ...]} for a whole MorphHB book file."""
    root = ET.fromstring(xml_text)
    chapters = {}
    for v in root.iter(Q + "verse"):
        vid = v.get("osisID", "")
        verses = chapters.setdefault(int(vid.split(".")[1]), [])
        tokens, break_after, group = [], None, 0
        for el in v:
            tag = el.tag.replace(Q, "")
            if tag == "w":
                variant = "ketiv" if el.get("type") == "x-ketiv" else ""
                if variant:
                    group += 1
                tokens.append(_token(el, variant, group if variant else None))
            elif tag == "seg" and tokens:
                t = el.get("type")
                if t == "x-maqqef":
                    tokens[-1]["trailing"] += el.text or "־"
                elif t == "x-sof-pasuq":
                    tokens[-1]["trailing"] += el.text or "׃"
                elif t == "x-paseq":
                    tokens[-1]["trailing"] += " " + (el.text or "׀")
                elif t == "x-pe":
                    break_after = "pe"
                elif t == "x-samekh":
                    break_after = "samekh"
            elif tag == "note" and el.get("type") == "variant":
                for w in el.iter(Q + "w"):
                    tokens.append(_token(w, "qere", group))
        for i, t in enumerate(tokens):
            if i < len(tokens) - 1 and not t["trailing"].endswith("־"):
                t["trailing"] += " "
            if t["morph_raw"]:
                t["morphemes"], t["anomaly"] = split_word(
                    t.pop("_raw"), t["lemma_raw"] or "", t["morph_raw"])
            t["tag_status"] = "native"
        verses.append({"verse": int(vid.split(".")[2]), "tokens": tokens,
                       "break_after": break_after})
    return chapters
