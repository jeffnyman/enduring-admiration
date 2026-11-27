"""Book catalogue for all supported canons.

Canon flags: 0 = absent, 1 = canonical, 2 = appendix / partial / only some
churches of that tradition. These are reference metadata, not Scripture;
review them before publishing the canon filter in the UI.
"""

# (usfm, osis, name, section, protestant, catholic, orthodox, note)
BOOKS = [
    ("GEN", "Gen", "Genesis", "OT", 1, 1, 1, None),
    ("EXO", "Exod", "Exodus", "OT", 1, 1, 1, None),
    ("LEV", "Lev", "Leviticus", "OT", 1, 1, 1, None),
    ("NUM", "Num", "Numbers", "OT", 1, 1, 1, None),
    ("DEU", "Deut", "Deuteronomy", "OT", 1, 1, 1, None),
    ("JOS", "Josh", "Joshua", "OT", 1, 1, 1, None),
    ("JDG", "Judg", "Judges", "OT", 1, 1, 1, None),
    ("RUT", "Ruth", "Ruth", "OT", 1, 1, 1, None),
    ("1SA", "1Sam", "1 Samuel", "OT", 1, 1, 1, None),
    ("2SA", "2Sam", "2 Samuel", "OT", 1, 1, 1, None),
    ("1KI", "1Kgs", "1 Kings", "OT", 1, 1, 1, None),
    ("2KI", "2Kgs", "2 Kings", "OT", 1, 1, 1, None),
    ("1CH", "1Chr", "1 Chronicles", "OT", 1, 1, 1, None),
    ("2CH", "2Chr", "2 Chronicles", "OT", 1, 1, 1, None),
    ("EZR", "Ezra", "Ezra", "OT", 1, 1, 1, None),
    ("NEH", "Neh", "Nehemiah", "OT", 1, 1, 1, None),
    ("EST", "Esth", "Esther", "OT", 1, 1, 1, "Hebrew Esther"),
    ("JOB", "Job", "Job", "OT", 1, 1, 1, None),
    ("PSA", "Ps", "Psalms", "OT", 1, 1, 1, None),
    ("PRO", "Prov", "Proverbs", "OT", 1, 1, 1, None),
    ("ECC", "Eccl", "Ecclesiastes", "OT", 1, 1, 1, None),
    ("SNG", "Song", "Song of Songs", "OT", 1, 1, 1, None),
    ("ISA", "Isa", "Isaiah", "OT", 1, 1, 1, None),
    ("JER", "Jer", "Jeremiah", "OT", 1, 1, 1, None),
    ("LAM", "Lam", "Lamentations", "OT", 1, 1, 1, None),
    ("EZK", "Ezek", "Ezekiel", "OT", 1, 1, 1, None),
    ("DAN", "Dan", "Daniel", "OT", 1, 1, 1, "Hebrew/Aramaic Daniel"),
    ("HOS", "Hos", "Hosea", "OT", 1, 1, 1, None),
    ("JOL", "Joel", "Joel", "OT", 1, 1, 1, None),
    ("AMO", "Amos", "Amos", "OT", 1, 1, 1, None),
    ("OBA", "Obad", "Obadiah", "OT", 1, 1, 1, None),
    ("JON", "Jonah", "Jonah", "OT", 1, 1, 1, None),
    ("MIC", "Mic", "Micah", "OT", 1, 1, 1, None),
    ("NAM", "Nah", "Nahum", "OT", 1, 1, 1, None),
    ("HAB", "Hab", "Habakkuk", "OT", 1, 1, 1, None),
    ("ZEP", "Zeph", "Zephaniah", "OT", 1, 1, 1, None),
    ("HAG", "Hag", "Haggai", "OT", 1, 1, 1, None),
    ("ZEC", "Zech", "Zechariah", "OT", 1, 1, 1, None),
    ("MAL", "Mal", "Malachi", "OT", 1, 1, 1, None),
    # Deuterocanon / Apocrypha
    ("TOB", "Tob", "Tobit", "DC", 0, 1, 1, None),
    ("JDT", "Jdt", "Judith", "DC", 0, 1, 1, None),
    ("ESG", "EsthGr", "Esther (Greek)", "DC", 0, 1, 1, "Esther with the Greek additions"),
    ("WIS", "Wis", "Wisdom of Solomon", "DC", 0, 1, 1, None),
    ("SIR", "Sir", "Sirach", "DC", 0, 1, 1, None),
    ("BAR", "Bar", "Baruch", "DC", 0, 1, 1, "Catholic Baruch 6 = Letter of Jeremiah"),
    ("LJE", "EpJer", "Letter of Jeremiah", "DC", 0, 1, 1, "Catholic: Baruch 6"),
    ("S3Y", "PrAzar", "Prayer of Azariah", "DC", 0, 1, 1, "Daniel 3 addition"),
    ("SUS", "Sus", "Susanna", "DC", 0, 1, 1, "Daniel 13 (Catholic)"),
    ("BEL", "Bel", "Bel and the Dragon", "DC", 0, 1, 1, "Daniel 14 (Catholic)"),
    ("DAG", "DanGr", "Daniel (Greek)", "DC", 0, 1, 1, "Daniel with the Greek additions"),
    ("1MA", "1Macc", "1 Maccabees", "DC", 0, 1, 1, None),
    ("2MA", "2Macc", "2 Maccabees", "DC", 0, 1, 1, None),
    ("3MA", "3Macc", "3 Maccabees", "DC", 0, 0, 1, None),
    ("4MA", "4Macc", "4 Maccabees", "DC", 0, 0, 2, "Appendix in Greek Bibles"),
    ("1ES", "1Esd", "1 Esdras", "DC", 0, 2, 1, "Vulgate appendix as 3 Esdras"),
    ("2ES", "2Esd", "2 Esdras", "DC", 0, 2, 2, "Latin only; Slavonic Bible; Vulgate appendix"),
    ("MAN", "PrMan", "Prayer of Manasseh", "DC", 0, 2, 1, "Vulgate appendix"),
    ("PS2", "AddPs", "Psalm 151", "DC", 0, 0, 1, None),
    # New Testament
    ("MAT", "Matt", "Matthew", "NT", 1, 1, 1, None),
    ("MRK", "Mark", "Mark", "NT", 1, 1, 1, None),
    ("LUK", "Luke", "Luke", "NT", 1, 1, 1, None),
    ("JHN", "John", "John", "NT", 1, 1, 1, None),
    ("ACT", "Acts", "Acts", "NT", 1, 1, 1, None),
    ("ROM", "Rom", "Romans", "NT", 1, 1, 1, None),
    ("1CO", "1Cor", "1 Corinthians", "NT", 1, 1, 1, None),
    ("2CO", "2Cor", "2 Corinthians", "NT", 1, 1, 1, None),
    ("GAL", "Gal", "Galatians", "NT", 1, 1, 1, None),
    ("EPH", "Eph", "Ephesians", "NT", 1, 1, 1, None),
    ("PHP", "Phil", "Philippians", "NT", 1, 1, 1, None),
    ("COL", "Col", "Colossians", "NT", 1, 1, 1, None),
    ("1TH", "1Thess", "1 Thessalonians", "NT", 1, 1, 1, None),
    ("2TH", "2Thess", "2 Thessalonians", "NT", 1, 1, 1, None),
    ("1TI", "1Tim", "1 Timothy", "NT", 1, 1, 1, None),
    ("2TI", "2Tim", "2 Timothy", "NT", 1, 1, 1, None),
    ("TIT", "Titus", "Titus", "NT", 1, 1, 1, None),
    ("PHM", "Phlm", "Philemon", "NT", 1, 1, 1, None),
    ("HEB", "Heb", "Hebrews", "NT", 1, 1, 1, None),
    ("JAS", "Jas", "James", "NT", 1, 1, 1, None),
    ("1PE", "1Pet", "1 Peter", "NT", 1, 1, 1, None),
    ("2PE", "2Pet", "2 Peter", "NT", 1, 1, 1, None),
    ("1JN", "1John", "1 John", "NT", 1, 1, 1, None),
    ("2JN", "2John", "2 John", "NT", 1, 1, 1, None),
    ("3JN", "3John", "3 John", "NT", 1, 1, 1, None),
    ("JUD", "Jude", "Jude", "NT", 1, 1, 1, None),
    ("REV", "Rev", "Revelation", "NT", 1, 1, 1, None),
]

ORD = {b[0]: i + 1 for i, b in enumerate(BOOKS)}

# STEP (TAGNT/TAHOT) abbreviations needed so far; extend on full ingest.
STEP_ALIASES = {"Gen": "GEN", "Jhn": "JHN", "Tob": "TOB"}


def canon_verse_id(book_id: str, chapter: int, verse: int) -> int:
    return ORD[book_id] * 1_000_000 + chapter * 1_000 + verse
