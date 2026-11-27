#!/usr/bin/env python3
"""Compare two independent Thayer digitizations entry by entry (read-only report).

  EP = imbennyhim/Every-Promise-Thayers (CC0; normalized refs like 'Rev 9:11')
  NM = nigelmsipa/thayers-greek-lexicon-dataset (CC0 per README; refs like 'Rev. ix. 11')

Agreement between two independent digitizations is evidence of fidelity;
disagreement locates errors in one or the other.
Usage: .venv/bin/python pipeline/eval_thayer.py
"""
import difflib
import json
import re
from collections import Counter
from pathlib import Path

from bibleingest.textnorm import norm_greek

CACHE = Path(__file__).resolve().parents[1] / "data" / "cache"
ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


def roman(s):
    s, total = s.lower(), 0
    for i, ch in enumerate(s):
        v = ROMAN[ch]
        total += -v if i + 1 < len(s) and ROMAN[s[i + 1]] > v else v
    return total


# Book abbreviations as they appear in each source -> common key
BOOKS = """Gen Gn|Exod Ex Exo|Lev|Num Nu|Deut Dt Deu|Josh Jos|Judg Jdg|Ruth Rut|1 Sam 1Sa|2 Sam 2Sa|1 K 1 Kgs 1Ki|2 K 2 Kgs 2Ki|
1 Chr 1Ch|2 Chr 2Ch|Ezra Ezr|Neh|Esth Est|Job|Ps Psa|Prov Pro|Eccl Eccles Ecc|Cant Song Sol|Is Isa|Jer|Lam|Ezek Eze|Dan|Hos|Joel Joe|
Amos Amo|Obad Oba|Jon|Mic|Nah|Hab|Zeph Zep|Hag|Zech Zec|Mal|Mt Matt Mat|Mk Mark Mar|Lk Luke Luk|Jn John Joh|Acts Act|Ro Rom|
1 Co 1Co 1 Cor|2 Co 2Co 2 Cor|Gal|Eph|Phil Php|Col|1 Th 1Th 1 Thess|2 Th 2Th 2 Thess|1 Tim 1Ti|2 Tim 2Ti|Tit|Philem Phm|Heb|
Jas|1 Pet 1Pe|2 Pet 2Pe|1 Jn 1 Jo 1Jo|2 Jn 2 Jo 2Jo|3 Jn 3 Jo 3Jo|Jude Jud|Rev"""
ALIAS = {}
for i, grp in enumerate(BOOKS.replace("\n", "").split("|")):
    for a in grp.split(" ") if " " not in grp.replace(" ", "", 0) else []:
        pass
    # tokens may contain a leading number ('1 Sam'), so split on known patterns
    for a in re.findall(r"[1-3] [A-Z][a-z]+|[1-3][A-Z][a-z]+|[A-Z][a-z]+", grp):
        ALIAS[a.replace(" ", "")] = i


def refs_ep(text):
    out = set()
    for b, c, v in re.findall(r"\b([1-3]?\s?[A-Z][a-z]{1,4})\.? (\d+):(\d+)", text):
        k = ALIAS.get(b.replace(" ", ""))
        if k is not None:
            out.add((k, int(c), int(v)))
    return out


def refs_nm(text):
    out = set()
    # 'Rev. ix. 11'  (book may be omitted in lists like 'xxi. 6' -> keep last book)
    last = None
    for m in re.finditer(r"(?:\b([1-3]?\s?[A-Z][a-z]{1,6})\.\s)?\b([ivxlc]+)\.\s(\d+)", text):
        b, c, v = m.groups()
        if b:
            last = ALIAS.get(b.replace(" ", ""))
        if last is not None:
            out.add((last, roman(c), int(v)))
    return out


def load_ep():
    out = {}
    for f in sorted((CACHE / "thayer-ep").glob("*-G*.md")):
        for blk in f.read_text(encoding="utf-8").split("\n---\n"):
            m = re.search(r"`Strong's G(\d+)`\n\n(.*)", blk, re.S)
            if m:
                out[f"G{int(m[1]):04d}"] = m[2].strip()
    return out


def load_nm():
    out = {}
    for line in (CACHE / "thayer-nm" / "thayer_lexicon.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e.get("strongs"):
            k = f"G{int(e['strongs'][1:]):04d}"
            out[k] = (e.get("lemma") or "") + " " + (e.get("grammar") or "") + " " + (e.get("text") or "")
    return out


def main():
    ep, nm = load_ep(), load_nm()
    both = sorted(set(ep) & set(nm))
    print(f"entries: EP {len(ep)}  NM {len(nm)}  both {len(both)}  EP-only {len(set(ep) - set(nm))}  NM-only {len(set(nm) - set(ep))}")
    sims, ref_stats, examples = [], Counter(), []
    for k in both:
        ga = [norm_greek(w) for w in ep[k].split() if norm_greek(w)]
        gb = [norm_greek(w) for w in nm[k].split() if norm_greek(w)]
        sims.append(difflib.SequenceMatcher(None, ga, gb, autojunk=False).ratio())
        ra, rb = refs_ep(ep[k]), refs_nm(nm[k])
        ref_stats["EP refs"] += len(ra)
        ref_stats["NM refs"] += len(rb)
        ref_stats["shared"] += len(ra & rb)
        if ra and rb:
            # EP refs that NM lacks but NM has same book+verse with another chapter: likely EP chapter error
            for (b, c, v) in ra - rb:
                alt = [x for x in rb - ra if x[0] == b and x[2] == v]
                if alt:
                    ref_stats["EP chapter differs from NM"] += 1
                    if len(examples) < 8:
                        examples.append((k, f"EP {b}:{c}:{v}", f"NM {alt[0]}"))
    sims.sort()
    print(f"Greek-word agreement per entry: median {sims[len(sims) // 2]:.2f}, "
          f"<0.5 in {sum(s < 0.5 for s in sims)} entries")
    print(f"references: {dict(ref_stats)}")
    print(f"  share of EP refs confirmed by NM: {ref_stats['shared'] / ref_stats['EP refs']:.1%}")
    print(f"  examples where only the chapter differs: {examples}")
    for k in ("G0003", "G3056"):
        print(f"  {k}: EP refs {sorted(refs_ep(ep[k]))[:6]}  NM refs {sorted(refs_nm(nm[k]))[:6]}")


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Independent check: does the cited NT verse contain the headword (by Strong's)?
NT = "Mat Mrk Luk Jhn Act Rom 1Co 2Co Gal Eph Php Col 1Th 2Th 1Ti 2Ti Tit Phm Heb Jas 1Pe 2Pe 1Jn 2Jn 3Jn Jud Rev".split()


def nt_strongs_by_verse():
    idx = {}
    for f in ("TAGNT-Mat-Jhn.txt", "TAGNT-Act-Rev.txt"):
        for line in (CACHE / "step-tagnt" / f).read_text(encoding="utf-8").splitlines():
            m = re.match(r"^(\w+)\.(\d+)\.(\d+)(?:\([^)]*\))?#\d+=", line)
            if m and m[1] in NT:
                key = (39 + NT.index(m[1]), int(m[2]), int(m[3]))
                for s in re.findall(r"G(\d{4})", line.split("\t")[3]):
                    idx.setdefault(key, set()).add(f"G{s}")
    return idx


def verify_refs():
    ep, nm = load_ep(), load_nm()
    idx = nt_strongs_by_verse()
    for name, src, fn in (("EP", ep, refs_ep), ("NM", nm, refs_nm)):
        for subset in ("all", "both"):
            keys = sorted(set(ep) & set(nm)) if subset == "both" else sorted(src)
            hit = tot = 0
            for k in keys:
                for r in fn(src[k]):
                    if r[0] >= 39 and r in idx:          # NT refs that exist as verses
                        tot += 1
                        hit += k in idx[r]
            print(f"  {name} ({subset} entries): NT refs whose verse contains the headword: {hit}/{tot} = {hit / tot:.1%}")
    # EP vs NM disagreements on chapter: who is right?
    wins = Counter()
    for k in sorted(set(ep) & set(nm)):
        ra, rb = refs_ep(ep[k]), refs_nm(nm[k])
        for (b, c, v) in ra - rb:
            for alt in [x for x in rb - ra if x[0] == b and x[2] == v and b >= 39]:
                a_ok, b_ok = k in idx.get((b, c, v), ()), k in idx.get(alt, ())
                wins["EP right" if a_ok and not b_ok else "NM right" if b_ok and not a_ok
                     else "both" if a_ok else "neither"] += 1
    print(f"  chapter disagreements adjudicated by TAGNT: {dict(wins)}")


if __name__ == "__main__":
    print("\nReference check against TAGNT:")
    verify_refs()
