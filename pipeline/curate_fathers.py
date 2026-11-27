"""Choose which Church Fathers excerpts to use, and write pipeline/fathers_allowlist.tsv.

    .venv/bin/python pipeline/curate_fathers.py

The source, HistoricalChristianFaith/Commentaries-Database, files excerpts by verse but mixes
public-domain translations with AI translations, paraphrases from modern copyrighted anthologies
and modern authors, and its source links are not reliable evidence of where a text came from.
So an excerpt is kept only if its own words are found in Philip Schaff's public-domain
Ante-Nicene and Nicene and Post-Nicene Fathers (the 1880s-90s translations):

- the text is compared as word 6-grams with the 38 Schaff volumes (CCEL plain-text files, used
  here only for this comparison and never shipped);
- 6-grams that also occur in the King James Bible (with Apocrypha) are ignored, so quoted
  Scripture can't make an excerpt look like Schaff;
- at least 90% of the remaining words must be covered, and there must be at least 15 of them;
- dropped as well: the Catena Aurea (already in the reader from a better edition), the
  'Canonical Scriptures', 'Reformation & Modern' and 'Second Temple Judaism' categories, and
  excerpts with no source link or an anthology-style title in capitals (these are often lightly
  modernised).

The build (build_bible.py) then loads only the excerpts listed here, and checks that each one's
text is unchanged (by its hash). Re-run this after changing HCF_SHA.
"""
import hashlib
import html
import io
import re
import sys
import tarfile
import tomllib
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bibleingest.fetch import fetch  # noqa: E402

HCF_SHA = "1f737a48c07cdcb1c64c4dd9dbbc789c122476dc"
HCF_URL = f"https://codeload.github.com/HistoricalChristianFaith/Commentaries-Database/tar.gz/{HCF_SHA}"
SCHAFF = ([f"anf{i:02d}" for i in range(1, 11)] + [f"npnf1{i:02d}" for i in range(1, 15)]
          + [f"npnf2{i:02d}" for i in range(1, 15)])
SCHAFF_URL = "https://ccel.org/ccel/s/schaff/{0}/cache/{0}.txt"
KJVA_URL = "https://ebible.org/Scriptures/eng-kjv_usfm.zip"
OUT = HERE / "fathers_allowlist.tsv"
N, COVER, MIN_WORDS = 6, 0.90, 15
SKIP_CATEGORIES = {"Canonical Scriptures", "Reformation & Modern", "Second Temple Judaism"}


def words(text: str) -> list[str]:
    t = unicodedata.normalize("NFKD", html.unescape(text))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower().replace("-\n", "")
    return re.findall(r"[a-z]+", re.sub(r"\d+", " ", t))


def grams(w: list[str]) -> list[int]:
    return [hash(" ".join(w[i:i + N])) for i in range(len(w) - N + 1)]


def quote_hash(q: str) -> str:
    return hashlib.sha256(q.encode("utf-8")).hexdigest()[:16]


def hcf_entries(tar_bytes: bytes):
    """(father, file name, index in file, quote, url, title, category) for every excerpt."""
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tar:
        members = [m for m in tar.getmembers() if m.isfile() and m.name.endswith(".toml")]
        meta = {}
        for m in members:
            parts = m.name.split("/")
            if len(parts) == 3 and parts[2] == "metadata.toml":
                meta[parts[1]] = tomllib.loads(tar.extractfile(m).read().decode("utf-8"))
        for m in members:
            parts = m.name.split("/")
            if len(parts) != 3 or parts[2] == "metadata.toml":
                continue
            father, fname = parts[1], parts[2]
            try:
                data = tomllib.loads(tar.extractfile(m).read().decode("utf-8"))
            except (tomllib.TOMLDecodeError, UnicodeDecodeError):
                continue
            cat = meta.get(father, {}).get("father_category", "")
            for i, c in enumerate(data.get("commentary", [])):
                yield father, fname, i, c.get("quote", ""), c.get("source_url", ""), c.get("source_title", ""), cat


def main():
    print("Loading King James Bible (with Apocrypha) to recognise quoted Scripture")
    kjv_zip, _ = fetch("ebible-kjva", KJVA_URL, "eng-kjv_usfm.zip")
    scripture = set()
    with zipfile.ZipFile(io.BytesIO(kjv_zip)) as z:
        for name in z.namelist():
            if name.endswith(".usfm"):
                text = re.sub(r"\\[a-z0-9]+\*?|\|[^\\]*", " ", z.read(name).decode("utf-8-sig"))
                for line in text.splitlines():
                    scripture.update(grams(words(line)))
    print(f"Indexing {len(SCHAFF)} Schaff volumes")
    schaff = set()
    for vol in SCHAFF:
        data, _ = fetch("ccel-schaff", SCHAFF_URL.format(vol), f"{vol}.txt")
        text = re.sub(r"Image of page \S+", " ", data.decode("utf-8", "replace"))
        schaff.update(grams(words(text)))
    print("Reading the Commentaries-Database")
    tar_bytes, sha = fetch("hcf-commentaries", HCF_URL, f"Commentaries-Database-{HCF_SHA}.tar.gz")
    stats, kept = Counter(), []
    for father, fname, i, quote, url, title, cat in hcf_entries(tar_bytes):
        stats["excerpts"] += 1
        why = None
        if cat in SKIP_CATEGORIES:
            why = f"category {cat}"
        elif "catena aurea" in title.lower():
            why = "Catena Aurea (already in the reader)"
        elif not url or (sum(c.isupper() for c in title) > 0.6 * sum(c.isalpha() for c in title) > 0):
            why = "no source link or anthology-style title"
        else:
            w = words(quote)
            g = grams(w)
            in_scripture = [False] * len(w)
            covered = [False] * len(w)
            for k, h in enumerate(g):
                if h in scripture:
                    for j in range(k, k + N):
                        in_scripture[j] = True
                elif h in schaff:
                    for j in range(k, k + N):
                        covered[j] = True
            own = [j for j in range(len(w)) if not in_scripture[j]]
            if len(own) < MIN_WORDS:
                why = "too short to verify"
            elif sum(covered[j] for j in own) < COVER * len(own):
                why = "not found in Schaff"
        if why:
            stats[f"dropped: {why}"] += 1
            continue
        kept.append((father, fname, i, quote_hash(quote)))
        stats["kept"] += 1
    kept.sort()
    fathers = len({k[0] for k in kept})
    with OUT.open("w", encoding="utf-8") as f:
        f.write(f"# Church Fathers excerpts kept from HistoricalChristianFaith/Commentaries-Database@{HCF_SHA}\n")
        f.write("# Made by pipeline/curate_fathers.py: each excerpt's words were found in Schaff's ANF/NPNF\n")
        f.write(f"# (public domain). {len(kept)} excerpts from {fathers} Fathers. Columns: father, file, index\n")
        f.write("# of the [[commentary]] entry in that file, sha256 of its quote (first 16 hex digits).\n")
        for row in kept:
            f.write("\t".join(map(str, row)) + "\n")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    print(f"Wrote {OUT.relative_to(HERE.parent)} ({len(kept)} excerpts, {fathers} Fathers)")


if __name__ == "__main__":
    main()
