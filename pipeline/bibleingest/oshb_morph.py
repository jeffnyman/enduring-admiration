"""Decoder for OpenScriptures Hebrew Bible morphology codes.

Spec: https://hb.openscriptures.org/parsing/HebrewMorphologyCodes.html (CC BY 4.0)
Codes are single segments with the language letter prefixed: 'HVqp3ms', 'HNcfsa'.
(STEP's TEHMC uses a different letter dialect, so it is NOT used for OSHB codes.)
"""

STEMS = {
    "H": dict(q="Qal", N="Niphal", p="Piel", P="Pual", h="Hiphil", H="Hophal", t="Hithpael",
              o="Polel", O="Polal", r="Hithpolel", m="Poel", M="Poal", k="Palel", K="Pulal",
              Q="Qal passive", l="Pilpel", L="Polpal", f="Hithpalpel", D="Nithpael", j="Pealal",
              i="Pilel", u="Hothpaal", c="Tiphil", v="Hishtaphel", w="Nithpalel", y="Nithpoel",
              z="Hithpoel"),
    "A": dict(q="Peal", Q="Peil", u="Hithpeel", p="Pael", P="Ithpaal", M="Hithpaal", a="Aphel",
              h="Haphel", s="Saphel", e="Shaphel", H="Hophal", i="Ithpeel", t="Hishtaphel",
              v="Ishtaphel", w="Hithaphel", o="Polel", z="Ithpoel", r="Hithpolel", f="Hithpalpel",
              b="Hephal", c="Tiphel", m="Poel", l="Palpel", L="Ithpalpel", O="Ithpolel",
              G="Ittaphal"),
}
CONJ = dict(p="Perfect (qatal)", q="Sequential perfect (weqatal)", i="Imperfect (yiqtol)",
            w="Sequential imperfect (wayyiqtol)", h="Cohortative", j="Jussive", v="Imperative",
            r="Participle active", s="Participle passive", a="Infinitive absolute",
            c="Infinitive construct")
TYPES = {
    "A": dict(a="Adjective", c="Cardinal number", g="Gentilic adjective", o="Ordinal number"),
    "N": dict(c="Common noun", g="Gentilic noun", p="Proper name"),
    "P": dict(d="Demonstrative pronoun", f="Indefinite pronoun", i="Interrogative pronoun",
              p="Personal pronoun", r="Relative pronoun"),
    "R": dict(d="with definite article"),
    "S": dict(d="Directional he", h="Paragogic he", n="Paragogic nun", p="Pronominal suffix"),
    "T": dict(a="Affirmation particle", d="Definite article", e="Exhortation particle",
              i="Interrogative particle", j="Interjection", m="Demonstrative particle",
              n="Negative particle", o="Direct object marker", r="Relative particle"),
}
POS = dict(A="Adjective", C="Conjunction", D="Adverb", N="Noun", P="Pronoun", R="Preposition",
           S="Suffix", T="Particle", V="Verb")
PERSON = {"1": "1st person", "2": "2nd person", "3": "3rd person"}
GENDER = dict(b="both genders", c="common", f="feminine", m="masculine")
NUMBER = dict(d="dual", p="plural", s="singular")
STATE = dict(a="absolute", c="construct", d="determined")
LANG = dict(H="Hebrew", A="Aramaic")


class Unknown(ValueError):
    pass


def _take(table, ch, what):
    if ch == "x":
        return None
    if ch not in table:
        raise Unknown(f"unknown {what} {ch!r}")
    return table[ch]


def decode(code: str) -> str:
    """'HVqp3ms' -> 'Hebrew Verb, Qal, Perfect (qatal), 3rd person masculine singular'"""
    if len(code) < 2 or code[0] not in LANG:
        raise Unknown(f"bad code {code!r}")
    lang, pos, rest = code[0], code[1], list(code[2:])
    if pos not in POS:
        raise Unknown(f"unknown part of speech {pos!r}")
    head, feats = [], []

    def nxt():
        return rest.pop(0) if rest else None

    if pos == "V":
        head = [f"Verb, {_take(STEMS[lang], nxt(), 'stem')}"]
        conj = nxt()
        head.append(_take(CONJ, conj, "conjugation"))
        if conj in ("r", "s"):            # participle: gender number state
            order = [(GENDER, "gender"), (NUMBER, "number"), (STATE, "state")]
        elif conj in ("a", "c"):          # infinitive: nothing (state allowed)
            order = [(STATE, "state")]
        else:
            order = [(PERSON, "person"), (GENDER, "gender"), (NUMBER, "number")]
    elif pos in ("A", "N"):
        t = nxt()
        head = [_take(TYPES[pos], t, "type")]
        # proper names carry only gender ('l' location, 't' title, per OSHB data)
        if pos == "N" and t == "p":
            g = nxt()
            if g is not None:
                feats.append({"m": "masculine", "f": "feminine", "l": "location",
                              "t": "title"}.get(g) or _take(GENDER, g, "gender"))
            order = []
        else:
            order = [(GENDER, "gender"), (NUMBER, "number"), (STATE, "state")]
    elif pos in ("P", "S"):
        head = [_take(TYPES[pos], nxt(), "type")]
        order = [(PERSON, "person"), (GENDER, "gender"), (NUMBER, "number")]
    elif pos in ("R", "T"):
        t = nxt()
        head = [POS[pos] if t is None else
                (f"Preposition {TYPES['R'][t]}" if pos == "R" and t in TYPES["R"]
                 else _take(TYPES[pos], t, "type"))]
        order = []
    else:                                  # C, D
        head, order = [POS[pos]], []

    for table, what in order:
        ch = nxt()
        if ch is None:
            break
        v = _take(table, ch, what)
        if v:
            feats.append(v)
    if rest:
        raise Unknown(f"trailing characters {''.join(rest)!r} in {code!r}")
    text = f"{LANG[lang]} " + ", ".join(h for h in head if h)
    return text + (", " + " ".join(feats) if feats else "")
