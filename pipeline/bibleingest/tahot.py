"""STEP TAHOT (Translators Amalgamated Hebrew OT, CC BY 4.0): in-context English glosses
and transliterations for every Hebrew word, attached to the WLC words by consonant alignment.

Rows look like
  Gen.1.1#01=L   בְּ/רֵאשִׁ֖ית   be./re.Shit   in/ beginning   ...
  Gen.31.55(32.1)#01=L ...        (English 31:55 = Hebrew 32:1; we key by the Hebrew ref)
The gloss is split at the same '/' boundaries as the word's prefixes and suffixes.
"""
import difflib
import re
from collections import defaultdict

from .textnorm import norm_hebrew

REF = re.compile(r"^(\w+)\.(\d+)\.(\d+)(?:\((\d+)\.(\d+)\))?#(\d+)=(\S+)$")


def parse(text: str) -> dict:
    """{(step_book, hebrew_ch, hebrew_v): [row, ...]}"""
    out = defaultdict(list)
    for line in text.splitlines():
        f = line.split("\t")
        m = REF.match(f[0]) if f else None
        if not m or len(f) < 4:
            continue
        ch, v = (int(m[4]), int(m[5])) if m[4] else (int(m[2]), int(m[3]))
        # anything after a backslash is appended punctuation or a paragraph marker (\׃, \פ, \ס)
        word = f[1].split("\\")[0]
        out[(m[1], ch, v)].append({"type": m[7], "hebrew": word, "norm": norm_hebrew(word),
                                   "translit": f[2], "gloss": f[3]})
    return out


def _clean_gloss(g: str) -> str:
    return re.sub(r"\s+", " ", g.replace("/", " ")).strip()


def attach(verses: list, rows_by_verse: dict, step_book: str, ch: int, log) -> None:
    """Give each WLC token of one chapter its TAHOT gloss and transliteration."""
    for v in verses:
        rows = rows_by_verse.get((step_book, ch, v["verse"]), [])
        toks = v["tokens"]
        sm = difflib.SequenceMatcher(None, [t["surface_norm"] for t in toks], [r["norm"] for r in rows],
                                     autojunk=False)
        matched = set()
        for blk in sm.get_matching_blocks():
            for k in range(blk.size):
                t, r = toks[blk.a + k], rows[blk.b + k]
                matched.add(blk.a + k)
                t["gloss"], t["gloss_kind"] = _clean_gloss(r["gloss"]), "contextual"
                t["translit"] = r["translit"].replace(".", "").replace("/", "")
                segs = [s.strip() for s in r["gloss"].split("/")]
                if len(segs) == len(t.get("morphemes", [])):
                    for m, seg in zip(t["morphemes"], segs):
                        if seg:
                            m["gloss"] = seg
        log["tahot glossed"] += len(matched)
        log["tahot unmatched"] += len(toks) - len(matched)
