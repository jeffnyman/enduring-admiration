"""STEP TVTMS (Translators Versification Traditions with Methodology for
Standardisation, CC BY 4.0): map each edition's native verse numbers to
TVTMS "Standard" (NRSV-based English) numbering.

Each Expanded-data row says: "if ALL these tests are true for this Bible,
SourceRef in this Bible = StandardRef". Tests look at the edition's whole
verse inventory (which verses exist, the last verse of a chapter, relative
verse lengths), so an Inventory must cover complete books, not just the
chapters being ingested.
"""
import re
from collections import defaultdict
from dataclasses import dataclass, field

from .books import ORD

REF = re.compile(r"(?:(?P<book>[1-4]?[A-Za-z][A-Za-z0-9]{1,2})\.)?(?:(?P<ch>[A-Za-z0-9]+):)?(?P<v>\d+|TextBeforeV1|Title)"
                 r"(?:(?:!|\.)(?P<sub>[a-z]\d?|\d+))?")
STEP_TO_USFM = {"Esg": "ESG", "Lje": "LJE"}          # everything else: upper-case == USFM
RELATION_RANK = {"identical": 0, "renumbered": 1, "partial": 2, "merged": 3}


def usfm_book(step: str):
    b = STEP_TO_USFM.get(step, step.upper())
    return b if b in ORD else None


@dataclass
class Ref:
    book: str
    ch: str
    v: int            # 0 = Psalm title
    sub: str = ""


def parse_ref(s: str, ctx: Ref | None = None) -> Ref | None:
    m = REF.fullmatch(s.strip())
    if not m:
        return None
    book = usfm_book(m["book"]) if m["book"] else (ctx.book if ctx else None)
    ch = m["ch"] or (ctx.ch if ctx else None)
    if not book or ch is None:
        return None
    v = 0 if m["v"] in ("TextBeforeV1", "Title") else int(m["v"])      # verse 0 = Psalm title
    return Ref(book, ch, v, m["sub"] or "")


def parse_ref_list(s: str, chapter_last=None) -> list[Ref]:
    """'Gen.5:32; 6:1' | 'Gen.2:25-3:1' | 'Gen.5:31-32' -> [Ref, ...]"""
    out, ctx = [], None
    for part in re.split(r"[;,]\s*", s.strip()):
        if not part:
            continue
        lo, _, hi = part.partition("-")
        a = parse_ref(lo, ctx)
        if not a:
            return []
        ctx = a
        if not hi:
            out.append(a)
            continue
        b = parse_ref(hi, a)
        if not b:
            return []
        if a.ch == b.ch:
            out += [Ref(a.book, a.ch, v) for v in range(a.v, b.v + 1)]
        else:                                    # cross-chapter range: needs chapter lengths
            last = chapter_last(a.book, a.ch) if chapter_last else None
            out += [Ref(a.book, a.ch, v) for v in range(a.v, (last or a.v) + 1)]
            out += [Ref(b.book, b.ch, v) for v in range(1, b.v + 1)]
        ctx = b
    return out


@dataclass
class Rule:
    source_type: str
    source: Ref
    standard: list
    action: str
    note: str
    tests: list = field(default_factory=list)
    line: int = 0


def parse_expanded(text: str, chapter_last=None) -> tuple[list[Rule], dict]:
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("#DataStart(Expanded)"))
    end = next(i for i, l in enumerate(lines) if l.startswith("#DataEnd(Expanded)"))
    rules, stats = [], defaultdict(int)
    for n in range(start + 1, end):
        f = lines[n].split("\t")
        if len(f) < 4 or not re.match(r"^[1-4]?[A-Z][a-z]{1,3}\.", f[1] or ""):
            continue
        stats["rows"] += 1
        src_list = parse_ref_list(f[1])
        if len(src_list) != 1:                  # summary row over a source range: per-verse rows follow
            stats["skipped: source range"] += 1
            continue
        std = parse_ref_list(f[2], chapter_last)
        if not std:
            stats["skipped: unmapped book or bad ref"] += 1
            continue
        note = re.sub(r"%", "", (f[6] if len(f) > 6 else "") or (f[5] if len(f) > 5 else "")).strip()
        tests = [t.strip() for t in (f[8] if len(f) > 8 else "").split("&") if t.strip()]
        rules.append(Rule(f[0].strip(), src_list[0], std, f[3].strip().rstrip("*").strip(),
                          note, tests, n + 1))
    stats["rules"] = len(rules)
    return rules, dict(stats)


# --------------------------------------------------------------------------- inventory
class Inventory:
    """What an edition contains: verses with word counts, lettered parts
    ('7a' = subverse 1 of 7), joined ranges ('15-16'), and Psalm titles."""

    def __init__(self):
        self.verses = defaultdict(dict)          # (book, ch) -> {v: words}
        self.parts = defaultdict(list)           # (book, ch, v) -> ['', 'a', 'b', ...]
        self.ends = {}                           # (book, ch, v, part) -> last verse of a range
        self.titles = set()
        self.alias = {}                          # rule book -> stored book (Greek Daniel: DAN -> DAG)

    def view(self, alias: dict):
        """Same data, but lookups for alias keys read another stored book."""
        v = Inventory.__new__(Inventory)
        v.verses, v.parts, v.ends, v.titles, v.alias = self.verses, self.parts, self.ends, self.titles, alias
        return v

    def _b(self, book):
        return self.alias.get(book, book)

    def add(self, book, ch, v, words, part="", end=None):
        key = (book, str(ch))
        self.verses[key][int(v)] = self.verses[key].get(int(v), 0) + words
        self.parts[(book, str(ch), int(v))].append(part)
        if end:
            self.ends[(book, str(ch), int(v), part)] = end

    def entries(self, book):
        """(ch, v, part) in document order."""
        book = self._b(book)
        for (b, ch), vs in list(self.verses.items()):
            if b == book:
                for v in sorted(vs):
                    for part in self.parts[(b, ch, v)]:
                        yield ch, v, part

    def words(self, r: Ref):
        b = self._b(r.book)
        if r.v == 0:
            return 1 if (b, r.ch) in self.titles else None
        return self.verses.get((b, r.ch), {}).get(r.v)

    def exists(self, r: Ref) -> bool:
        if not self.words(r):
            return False
        if r.sub in ("", "0"):
            return True
        parts = self.parts.get((self._b(r.book), r.ch, r.v), [])
        if r.sub.isdigit():                      # '.2' = at least 3 parts (part 0 = base text)
            return len(parts) > int(r.sub)
        return r.sub in parts

    def last(self, book, ch):
        vs = self.verses.get((self._b(book), str(ch)))
        return max(vs) if vs else None

    def part_list(self, book, ch, v):
        return self.parts.get((self._b(book), ch, v), [])

    def end_of(self, book, ch, v, part):
        return self.ends.get((self._b(book), ch, v, part))

    def has_book(self, book):
        return any(b == book for b, _ in self.verses)


OPS = re.compile(r"\s*(=|<|>)\s*")


def _side(expr: str, ctx: Ref | None, inv: Inventory):
    """'Mal.3:22+Mal.3:24' or 'Mal.3:23*2' -> total words (None if a verse is missing)."""
    total, first = 0, None
    for term in expr.split("+"):
        ref_s, _, mult = term.strip().partition("*")
        r = parse_ref(ref_s, ctx or first)
        if r is None:
            raise ValueError(term)
        first = first or r
        w = inv.words(Ref(r.book, r.ch, r.v))
        if w is None:
            return None, first
        total += w * int(mult or 1)
    return total, first


def evaluate(test: str, inv: Inventory):
    """True / False, or None if the test cannot be parsed. A book the edition lacks
    simply has no verses (Exist=False, NotExist=True)."""
    parts = OPS.split(test.strip(), maxsplit=1)
    if len(parts) != 3:
        return None
    left, op, right = parts
    try:
        if op == "=":
            a = parse_ref(left)
            if a is None:
                return None
            kind = right.strip()
            if kind == "Exist":
                return inv.exists(a)
            if kind == "NotExist":
                return not inv.exists(a)
            if kind == "Last":
                return inv.last(a.book, a.ch) == a.v
            return None
        wa, a = _side(left, None, inv)
        wb, _ = _side(right, a, inv)
    except ValueError:
        return None
    if wa is None or wb is None:
        return False
    return wa < wb if op == "<" else wa > wb


def relation_for(rule: Rule, std: Ref) -> str:
    if len(rule.standard) > 1 or rule.action == "Concatenation":
        return "merged"
    if rule.source.sub or std.sub or rule.action.startswith(("Divided", "Merged", "CopiedFrom")):
        return "partial"
    if (std.book, std.ch, std.v) == (rule.source.book, rule.source.ch, rule.source.v):
        return "identical"
    return "renumbered"


def map_edition(rules: list[Rule], inv: Inventory, book: str, prefer: tuple):
    """-> {(ch, v, part): [(std_ref, relation, rule_label, note)]}, report dict.

    `prefer` lists SourceType substrings in priority order, used only to break
    ties when rules from different traditions all pass their tests."""
    report = defaultdict(int)
    report["traditions"] = defaultdict(int)
    candidates = defaultdict(list)
    for r in rules:
        if r.source.book != book or r.action == "IfEmpty verse":
            continue
        results = [evaluate(t, inv) for t in r.tests]
        if None in results:
            report["rules with unevaluable tests"] += 1
            continue
        if all(results):
            parts = inv.part_list(book, r.source.ch, r.source.v)
            # a summary 'Concatenation' row (whole verse -> several Standard verses) is for Bibles
            # that don't divide the verse; when this edition has the lettered parts, the per-part
            # rows apply instead
            if r.action == "Concatenation" and not r.source.sub and len(parts) > 1:
                report["concatenation rows skipped (edition has parts)"] += 1
                continue
            # a rule about subverse '!a' applies to part 'a' if the edition has that part,
            # otherwise it describes part of the undivided verse
            has_part = r.source.sub and r.source.sub in parts
            candidates[(r.source.ch, r.source.v, r.source.sub if has_part else "")].append(r)

    mapping, conflicts = {}, []
    for ch, v, part in inv.entries(book):
        cands = candidates.get((ch, v, part), [])
        if not cands:
            if part:                              # lettered part with no rule: part of its base verse
                base = mapping.get((ch, v, ""), [(Ref(book, ch, v), "identical", "", None)])
                rows = [(r, "partial", "no TVTMS rule for part; mapped to base verse", None) for r, *_ in base]
            else:
                end = inv.end_of(book, ch, v, part)
                rows = ([(Ref(book, ch, x), "merged", "source joins verses (range)", None) for x in range(v, end + 1)]
                        if end else [(Ref(book, ch, v), "identical", "TVTMS: no rule (keep)", None)])
            mapping[(ch, v, part)] = rows
            for _, rel, _, _ in rows:
                report[rel] += 1
            continue
        by_type = defaultdict(list)
        for r in cands:
            by_type[r.source_type].append(r)
        if len(by_type) > 1:
            targets = {t: frozenset((s.ch, s.v) for r in rs for s in r.standard) for t, rs in by_type.items()}
            if len(set(targets.values())) > 1:
                conflicts.append((ch, v, part, sorted(by_type)))
            pick = next((t for p in prefer for t in by_type if p in t), sorted(by_type)[0])
            cands = by_type[pick]
        rows = {}
        for r in cands:
            report["traditions"][r.source_type] += 1
            for s in r.standard:
                key = (s.book, s.ch, s.v)
                rel = relation_for(r, s)
                if key not in rows or RELATION_RANK[rel] > RELATION_RANK[rows[key][1]]:
                    rows[key] = (Ref(s.book, s.ch, s.v), rel, f"TVTMS {r.source_type}: {r.action}", r.note or None)
        mapping[(ch, v, part)] = list(rows.values())
        for _, rel, _, _ in rows.values():
            report[rel] += 1
    # a separately printed title (verse 0) with no rule of its own belongs to the Standard
    # chapter its verse 1 maps to
    for (ch, v, part), rows in mapping.items():
        if v == 0 and rows and rows[0][2] == "TVTMS: no rule (keep)":
            first = mapping.get((ch, 1, ""))
            if first and str(first[0][0].ch) != str(ch):
                mapping[(ch, v, part)] = [(Ref(first[0][0].book, first[0][0].ch, 0), "renumbered",
                                           "title follows its psalm's Standard chapter", None)]
    report["conflicts"] = conflicts
    report["traditions"] = dict(report["traditions"])
    return mapping, dict(report)


def load_overrides(path, mapping_by_edition, report):
    """Apply edition-specific corrections TVTMS does not cover.
    TSV: edition, book, source, standard, reason. Source 'ch:v[part]' or a range
    'ch:v1-v2[part]'; standard 'ch:v' or 'ch:v1-v2' (same length), or 'BOOK ch:v' for
    a different standard book."""
    applied = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        ed, book, src, std, reason = line.split("\t")
        m = re.fullmatch(r"(\w+):(\d+)(?:-(\d+))?([a-z]?)", src)
        n = re.fullmatch(r"(?:([1-4A-Z]{3}) )?(\d+):(\d+)(?:-(\d+))?", std)
        if not m or not n:
            report.setdefault("override_misses", []).append(line)
            continue
        s_ch, s_lo, s_hi, part = m[1], int(m[2]), int(m[3] or m[2]), m[4]
        t_book, t_ch, t_lo = n[1] or book, n[2], int(n[3])
        if n[4] and int(n[4]) - t_lo != s_hi - s_lo:
            report.setdefault("override_misses", []).append(line + "  (range lengths differ)")
            continue
        if (ed, book) not in mapping_by_edition:
            continue                              # book not part of this build
        for i, v in enumerate(range(s_lo, s_hi + 1)):
            key = (s_ch, v, part)
            if key not in mapping_by_edition[(ed, book)]:
                report.setdefault("override_misses", []).append(f"{line}  (no verse {s_ch}:{v}{part})")
                continue
            mapping_by_edition[(ed, book)][key] = [(Ref(t_book, t_ch, t_lo + i), "renumbered",
                                                    "override: " + reason, None)]
            applied.append((ed, book, f"{s_ch}:{v}{part}", f"{t_book} {t_ch}:{t_lo + i}"))
    report["overrides_applied"] = applied
