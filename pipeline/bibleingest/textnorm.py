"""Unicode helpers.

Stored display text is NEVER normalized: NFC can reorder Hebrew points and
turns Greek oxia into tonos. Only the *_norm / text_search columns are
normalized, for search and alignment.
"""
import unicodedata as ud

# Elision / apostrophe marks used by different Greek sources
ELISION = {"ʼ", "᾽", "’", "᾿", "'"}
# Text-critical sigla used in SBLGNT
SBL_SIGLA = set("⸀⸁⸂⸃⸄⸅")

HEB_LETTERS = (0x05D0, 0x05EA)
HEB_BLOCK = (0x0590, 0x05FF)
HEB_PRESENTATION = (0xFB1D, 0xFB4F)


def strip_marks(s: str) -> str:
    return "".join(c for c in ud.normalize("NFD", s) if not ud.combining(c))


def norm_greek(s: str) -> str:
    out = strip_marks(s).lower().replace("ς", "σ")
    return "".join(c for c in out if c.isalpha() and c not in ELISION and ud.category(c) != "Lm")


def norm_hebrew(s: str) -> str:
    return "".join(c for c in s if HEB_LETTERS[0] <= ord(c) <= HEB_LETTERS[1])


def is_word_char(c: str) -> bool:
    return c.isalpha() or ud.category(c) in ("Mn", "Mc", "Lm") or c in ELISION


def split_punct(chunk: str):
    """'“λόγος,' -> ('“', 'λόγος', ',')"""
    i, j = 0, len(chunk)
    while i < j and not is_word_char(chunk[i]):
        i += 1
    while j > i and not is_word_char(chunk[j - 1]):
        j -= 1
    return chunk[:i], chunk[i:j], chunk[j:]


def script_of(c: str) -> str:
    cp = ord(c)
    if HEB_PRESENTATION[0] <= cp <= HEB_PRESENTATION[1]:
        return "hebrew-presentation"
    if HEB_BLOCK[0] <= cp <= HEB_BLOCK[1]:
        return "hebrew"
    if 0x0370 <= cp <= 0x03FF or 0x1F00 <= cp <= 0x1FFF:
        return "greek"
    if ud.combining(c):
        return "combining"
    if c in ELISION:
        return "elision"
    if c.isascii() and c.isalpha():
        return "latin"
    return ud.category(c)
