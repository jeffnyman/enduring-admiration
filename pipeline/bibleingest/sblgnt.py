"""Official SBL Greek New Testament (LogosBible/SBLGNT on GitHub, CC BY 4.0).

data/sblgnt/xml/<Book>.xml
  <p><verse-number id="Matthew 1:1">1:1</verse-number> <w>Βίβλος</w><suffix> </suffix> ...
  <prefix> holds text-critical sigla (⸀ ⸂ …) or opening punctuation before a word.
data/sblgntapp/xml/<Book>.xml
  <verse>Matthew 1:5</verse> <note>…apparatus entry…</note> …

eBible's USFM conversion of the same text broke some words around footnotes (Mat 7:4
"ἐκβάλω" became "ἐκ" + "άλω") and appended "‘p /’ ‘/book’" markers, so the source is used directly.
"""
import re
import xml.etree.ElementTree as ET

from .textnorm import SBL_SIGLA, norm_greek

REF = re.compile(r"(\d+):(\d+)$")


def _strip_sigla(s: str) -> str:
    return "".join(c for c in s if c not in SBL_SIGLA)


def parse_book(text_xml: str, app_xml: str | None = None) -> dict:
    """{chapter: [verse]} with the fields the build uses for USFM editions, plus tokens."""
    root = ET.fromstring(text_xml.lstrip("﻿"))
    chapters: dict = {}
    cur = None
    pending_prefix = ""
    for p in root.iter("p"):
        new_para = True
        for el in p:
            if el.tag == "verse-number":
                m = REF.search(el.get("id", ""))
                ch, vn = int(m[1]), int(m[2])
                cur = {"verse": vn, "part": "", "verse_end": None, "tokens": [], "notes": [],
                       "runs": [], "para_before": "p" if new_para else None, "heading_before": None}
                chapters.setdefault(ch, []).append(cur)
            elif el.tag == "prefix":
                pending_prefix += el.text or ""
            elif el.tag == "w" and cur is not None:
                if new_para and cur["tokens"]:
                    cur["runs"].append({"para": "p"})          # paragraph starts mid-verse
                word = _strip_sigla(el.text or "")
                cur["tokens"].append({"surface": word, "surface_norm": norm_greek(word),
                                      "leading": _strip_sigla(pending_prefix).strip(), "trailing": ""})
                pending_prefix = ""
            elif el.tag == "suffix" and cur is not None and cur["tokens"]:
                cur["tokens"][-1]["trailing"] += el.text or ""
            new_para = new_para and el.tag in ("verse-number", "prefix")
    for verses in chapters.values():
        for v in verses:
            toks = v["tokens"]
            for t in toks[:-1]:
                if not t["trailing"].endswith(" "):
                    t["trailing"] += " "
            if toks:
                toks[-1]["trailing"] = toks[-1]["trailing"].rstrip()
            v["text"] = re.sub(r"  +", " ", "".join(t["leading"] + t["surface"] + t["trailing"] for t in toks))
            v["runs"] = [{"t": v["text"]}]
    if app_xml:
        current = None
        for el in ET.fromstring(app_xml.lstrip("﻿")):
            if el.tag == "verse":
                m = REF.search(el.text or "")
                current = (int(m[1]), int(m[2])) if m else None
            elif el.tag == "note" and current:
                for v in chapters.get(current[0], []):
                    if v["verse"] == current[1]:
                        v["notes"].append(("textcritical", re.sub(r"\s+", " ", el.text or "").strip()))
    return chapters
