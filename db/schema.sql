-- =====================================================================
-- bible.db schema  (v1)
--
-- Design principles
--   * Every edition (WEB, WLC, LXX, SBLGNT, ...) stores verses in its OWN
--     native numbering. Nothing is renumbered in place.
--   * A canonical verse grid (TVTMS "Standard" = NRSV-based English numbering) is the hub. verse_map
--     links each native verse to one or more canonical verses, so the UI
--     can show "Gen 1:1" in WEB beside the matching WLC and LXX verses even
--     when chapter/verse numbers differ (Joel 3/4, Mal 4, LXX Psalms, ...).
--   * Words (token) belong to a verse. A token can have several morphemes
--     (Hebrew prefixes/suffixes, Greek crasis), and each morpheme carries
--     lemma + Strong's + morphology code.
--   * Lexicon entries are joined by Strong's number OR lemma, so words
--     without a Strong's number (much of the LXX) can still be looked up.
--   * Every row of text traces back to a `source` row with its license.
-- =====================================================================

PRAGMA foreign_keys = ON;

CREATE TABLE schema_meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- Provenance and licensing
-- ---------------------------------------------------------------------
CREATE TABLE source (
  id           TEXT PRIMARY KEY,          -- 'ebible-eng-web', 'oshb-morphhb', ...
  title        TEXT NOT NULL,
  url          TEXT NOT NULL,
  version      TEXT,                      -- git commit / dated release
  license      TEXT NOT NULL,             -- 'Public Domain', 'CC-BY-4.0'
  attribution  TEXT NOT NULL,             -- text the app must display
  sha256       TEXT,                      -- of the downloaded file(s)
  retrieved_at TEXT NOT NULL              -- ISO-8601 UTC
);

-- ---------------------------------------------------------------------
-- Books and canons
-- ---------------------------------------------------------------------
CREATE TABLE book (
  id               TEXT PRIMARY KEY,      -- USFM code: GEN, TOB, JHN, ...
  ord              INTEGER NOT NULL UNIQUE,
  osis_id          TEXT UNIQUE,           -- Gen, Tob, John
  name             TEXT NOT NULL,
  section          TEXT NOT NULL CHECK (section IN ('OT','DC','NT')),
  -- 0 = not in canon, 1 = canonical, 2 = appendix / partial / some traditions
  canon_protestant INTEGER NOT NULL CHECK (canon_protestant IN (0,1,2)),
  canon_catholic   INTEGER NOT NULL CHECK (canon_catholic   IN (0,1,2)),
  canon_orthodox   INTEGER NOT NULL CHECK (canon_orthodox   IN (0,1,2)),
  canon_note       TEXT
);

-- Source-specific book abbreviations ('Gen' in OSIS, 'Jhn' in STEP, ...)
CREATE TABLE book_alias (
  scheme  TEXT NOT NULL,                  -- 'osis', 'step', 'ebible-file'
  alias   TEXT NOT NULL,
  book_id TEXT NOT NULL REFERENCES book(id),
  PRIMARY KEY (scheme, alias)
);

-- ---------------------------------------------------------------------
-- Editions and versification
-- ---------------------------------------------------------------------
CREATE TABLE versification_scheme (
  id          TEXT PRIMARY KEY,           -- 'eng' (canonical), 'heb', 'lxx'
  description TEXT NOT NULL
);

CREATE TABLE edition (
  id                TEXT PRIMARY KEY,     -- 'WEB', 'WLC', 'LXX-BRENTON', 'SBLGNT'
  name              TEXT NOT NULL,
  language          TEXT NOT NULL,        -- BCP-47: 'en', 'hbo', 'grc'
  direction         TEXT NOT NULL CHECK (direction IN ('ltr','rtl')),
  kind              TEXT NOT NULL CHECK (kind IN ('translation','original')),
  versification_id  TEXT NOT NULL REFERENCES versification_scheme(id),
  text_source_id    TEXT NOT NULL REFERENCES source(id),
  tagging_source_id TEXT REFERENCES source(id),   -- lemma/morph source, if different
  notes             TEXT
);

-- Canonical verse grid (TVTMS Standard numbering). id = ord*1000000 + ch*1000 + v
-- (verse 0 = a Psalm title counted as its own unit in Standard numbering)
CREATE TABLE canon_verse (
  id      INTEGER PRIMARY KEY,
  book_id TEXT NOT NULL REFERENCES book(id),
  chapter INTEGER NOT NULL,
  verse   INTEGER NOT NULL,
  UNIQUE (book_id, chapter, verse)
);

-- A verse as it exists in one edition, in that edition's numbering.
CREATE TABLE verse (
  id             INTEGER PRIMARY KEY,
  edition_id     TEXT    NOT NULL REFERENCES edition(id),
  book_id        TEXT    NOT NULL REFERENCES book(id),
  chapter        INTEGER NOT NULL,
  verse          INTEGER NOT NULL,
  part           TEXT    NOT NULL DEFAULT '',  -- lettered part ('7a' -> verse 7, part 'a')
  verse_end      INTEGER,                      -- set when the source joins verses ('15-16')
  text           TEXT    NOT NULL,             -- display text exactly as in source (markup removed)
  text_search    TEXT    NOT NULL,             -- normalized (no points/accents, lowercase) for FTS
  rich_json      TEXT,                         -- [{"t":..},{"t":..,"wj":1},{"para":"q1"}]
  para_before    TEXT,                         -- paragraph/poetry style opening at this verse
  heading_before TEXT,                         -- section heading / psalm title preceding verse
  break_after    TEXT CHECK (break_after IN ('pe','samekh')),  -- MT open/closed paragraph
  source_ref     TEXT,                         -- source's own ref when stored differently ('2Esd 11:1')
  UNIQUE (edition_id, book_id, chapter, verse, part)
);
CREATE INDEX verse_by_ref ON verse (book_id, chapter, verse);

-- Native verse -> canonical verse(s), from STEP TVTMS rules evaluated per edition.
CREATE TABLE verse_map (
  verse_id       INTEGER NOT NULL REFERENCES verse(id) ON DELETE CASCADE,
  canon_verse_id INTEGER NOT NULL REFERENCES canon_verse(id),
  relation       TEXT NOT NULL CHECK (relation IN
                   ('identical','renumbered','partial','merged','split','assumed')),
  rule           TEXT,                          -- TVTMS tradition + action that produced this row
  note           TEXT,                          -- TVTMS versification note for the reader, if any
  PRIMARY KEY (verse_id, canon_verse_id)
);
CREATE INDEX verse_map_by_canon ON verse_map (canon_verse_id);

-- Reading layouts: a book presented in another tradition's order and numbering, built on
-- top of the canonical grid. Catholic and Orthodox Bibles read Daniel with the Prayer of
-- Azariah inside chapter 3 and Susanna/Bel as chapters 13-14, and Esther with its Greek
-- additions in place (A-F). Each layout lists canonical verses in reading order.
CREATE TABLE layout (
  book_id       TEXT PRIMARY KEY REFERENCES book(id),  -- book shown with this layout: DAG, ESG
  spine_edition TEXT NOT NULL REFERENCES edition(id),  -- edition whose order and numbering it follows
  replaces      TEXT NOT NULL,                         -- Standard books it presents as one: 'DAN,S3Y,SUS,BEL'
  description   TEXT NOT NULL
);

CREATE TABLE layout_verse (
  book_id        TEXT    NOT NULL REFERENCES layout(book_id),
  chapter        INTEGER NOT NULL,                     -- chapter in this layout
  seq            INTEGER NOT NULL,                     -- reading order within the book
  canon_verse_id INTEGER NOT NULL REFERENCES canon_verse(id),
  label          TEXT    NOT NULL,                     -- verse label in this layout: '24', 'A 1'
  PRIMARY KEY (book_id, seq),
  UNIQUE (book_id, canon_verse_id)
);
CREATE INDEX layout_verse_chapter ON layout_verse (book_id, chapter, seq);
CREATE INDEX layout_verse_canon   ON layout_verse (canon_verse_id);

-- Cross-references between Standard verses. OpenBible.info (CC BY, ranked by user votes; only
-- references with votes >= 0) and the WEB's own cross-reference notes (incl. the deuterocanon).
CREATE TABLE cross_ref (
  from_canon INTEGER NOT NULL REFERENCES canon_verse(id),
  to_start   INTEGER NOT NULL REFERENCES canon_verse(id),
  to_end     INTEGER NOT NULL REFERENCES canon_verse(id),   -- = to_start for a single verse
  votes      INTEGER,                                       -- OpenBible votes; NULL for WEB notes
  source     TEXT    NOT NULL CHECK (source IN ('openbible','web')),
  PRIMARY KEY (from_canon, to_start, to_end, source)
);
CREATE INDEX cross_ref_from ON cross_ref (from_canon, votes DESC);

CREATE TABLE verse_note (
  id       INTEGER PRIMARY KEY,
  verse_id INTEGER NOT NULL REFERENCES verse(id) ON DELETE CASCADE,
  kind     TEXT NOT NULL CHECK (kind IN ('footnote','crossref','textcritical')),
  text     TEXT NOT NULL
);
CREATE INDEX verse_note_by_verse ON verse_note (verse_id);

-- ---------------------------------------------------------------------
-- Word-level original-language data
-- ---------------------------------------------------------------------
CREATE TABLE morph_scheme (
  id          TEXT PRIMARY KEY,           -- 'oshb', 'step-greek'
  description TEXT NOT NULL,
  source_id   TEXT REFERENCES source(id)
);

-- Morphology code -> plain English (from STEP TEHMC / TEGMC).
CREATE TABLE morph_code (
  scheme_id TEXT NOT NULL REFERENCES morph_scheme(id),
  code      TEXT NOT NULL,                -- single segment: 'HVqp3ms', 'N-NSM'
  summary   TEXT NOT NULL,                -- 'Verb Qal Perfect Third Singular Masculine'
  detail    TEXT,                         -- longer explanation
  fields    TEXT,                         -- 'Function=Verb; Stem=Qal; ...'
  PRIMARY KEY (scheme_id, code)
);

CREATE TABLE token (
  id           INTEGER PRIMARY KEY,
  verse_id     INTEGER NOT NULL REFERENCES verse(id) ON DELETE CASCADE,
  position     INTEGER NOT NULL,          -- 1-based order within verse (ketiv AND qere each get one)
  variant      TEXT NOT NULL DEFAULT '' CHECK (variant IN ('','ketiv','qere')),
  variant_group INTEGER,                  -- ketiv and its qere word(s) share this number
  surface      TEXT NOT NULL,             -- exact source form (segment dividers removed)
  surface_norm TEXT NOT NULL,             -- stripped of points/accents, lowercase
  leading      TEXT NOT NULL DEFAULT '',  -- punctuation before the word: '(', '“'
  trailing     TEXT NOT NULL DEFAULT '',  -- what follows: ' ', '־', '׃', ', '
  source_ref   TEXT,                      -- MorphHB word id / TAGNT 'Jhn.1.1#01'
  lemma_raw    TEXT,                      -- as given: 'b/7225'
  morph_raw    TEXT,                      -- as given: 'HR/Ncfsa'
  morph_scheme TEXT REFERENCES morph_scheme(id),
  gloss        TEXT,                      -- short English gloss for the gloss line
  gloss_kind   TEXT CHECK (gloss_kind IN ('contextual','lexical')),  -- in context (TAGNT/TAHOT) or dictionary (LSJ)
  translit     TEXT,
  ocr_original TEXT,                      -- the transcription's form, when an OCR error was corrected
  -- native: tags came with the text; aligned: matched word-for-word from a tagging source;
  -- inferred: copied from the same form elsewhere in the book (no context; lower confidence)
  tag_status   TEXT NOT NULL DEFAULT 'none'
               CHECK (tag_status IN ('native','aligned','inferred','unaligned','none')),
  UNIQUE (verse_id, position)
);
CREATE INDEX token_norm ON token (surface_norm);

CREATE TABLE morpheme (
  id          INTEGER PRIMARY KEY,
  token_id    INTEGER NOT NULL REFERENCES token(id) ON DELETE CASCADE,
  position    INTEGER NOT NULL,
  role        TEXT NOT NULL CHECK (role IN ('prefix','stem','suffix')),
  surface     TEXT NOT NULL,
  surface_norm TEXT,                      -- surface without points/accents: finds a stem inside prefixed words
  lemma       TEXT,                       -- dictionary form, when known
  strongs     TEXT,                       -- zero-padded base: 'H0430', 'G3056'
  strongs_ext TEXT,                       -- disambiguated: 'H1254a', 'G1492H'
  morph_code  TEXT,                       -- key into morph_code for token.morph_scheme
  gloss       TEXT,
  UNIQUE (token_id, position)
);
CREATE INDEX morpheme_strongs ON morpheme (strongs);
CREATE INDEX morpheme_lemma   ON morpheme (lemma);
CREATE INDEX morpheme_norm    ON morpheme (surface_norm);
CREATE INDEX morpheme_ext     ON morpheme (strongs_ext);

-- Hebrew <-> Greek equivalents, measured from the aligned Hebrew Bible and Septuagint: how often
-- a Hebrew lemma and a Greek lemma occur in the same Standard verse (Dice coefficient). Statistical,
-- not a word-by-word alignment. Keys: Strong's ('H1697', 'G3056'), else the STEP extended number,
-- else 'lemma:<Greek lemma>'.
CREATE TABLE lemma_link (
  direction   TEXT    NOT NULL CHECK (direction IN ('heb>grk','grk>heb')),
  from_key    TEXT    NOT NULL,
  to_key      TEXT    NOT NULL,
  rank        INTEGER NOT NULL,           -- 1 = strongest for from_key
  both_verses INTEGER NOT NULL,           -- verses where both occur
  from_verses INTEGER NOT NULL,           -- aligned verses containing from_key
  to_verses   INTEGER NOT NULL,
  score       REAL    NOT NULL,           -- Dice: 2*both / (from + to)
  PRIMARY KEY (direction, from_key, to_key)
);
CREATE INDEX lemma_link_rank ON lemma_link (direction, from_key, rank);

-- ---------------------------------------------------------------------
-- Lexicons
-- ---------------------------------------------------------------------
CREATE TABLE lexicon (
  id        TEXT PRIMARY KEY,             -- 'strongs-heb', 'strongs-grk', 'bdb', 'thayer', 'lsj'
  name      TEXT NOT NULL,
  language  TEXT NOT NULL,                -- 'hbo', 'grc'
  source_id TEXT NOT NULL REFERENCES source(id)
);

CREATE TABLE lexicon_entry (
  id             INTEGER PRIMARY KEY,
  lexicon_id     TEXT NOT NULL REFERENCES lexicon(id),
  entry_key      TEXT NOT NULL,           -- the lexicon's own id: 'H7225', BDB 't.ad.ag', 'G3056'
  strongs        TEXT,                    -- primary Strong's number for display, if any
  lemma          TEXT NOT NULL,
  translit       TEXT,
  pronunciation  TEXT,
  part_of_speech TEXT,
  short_def      TEXT,                    -- one-line gloss for the drawer header
  definition     TEXT,                    -- full entry, plain text (senses on new lines)
  derivation     TEXT,
  kjv_usage      TEXT,
  extra_json     TEXT,                    -- e.g. {"status": "base"} for work-in-progress BDB entries
  UNIQUE (lexicon_id, entry_key)
);
CREATE INDEX lexicon_entry_lemma ON lexicon_entry (lemma);
CREATE INDEX lexicon_entry_strongs ON lexicon_entry (strongs, lexicon_id);

-- Which Strong's numbers an entry covers (many-to-many). strongs_ext is the
-- disambiguated form ('H1254a', 'G1492H') when the lexicon distinguishes them.
CREATE TABLE lexicon_strongs (
  entry_id    INTEGER NOT NULL REFERENCES lexicon_entry(id) ON DELETE CASCADE,
  strongs     TEXT NOT NULL,              -- zero-padded base: 'H1254'
  strongs_ext TEXT,
  PRIMARY KEY (entry_id, strongs, strongs_ext)
);
CREATE INDEX lexicon_strongs_base ON lexicon_strongs (strongs);
CREATE INDEX lexicon_strongs_ext  ON lexicon_strongs (strongs_ext);

-- ---------------------------------------------------------------------
-- Full-text search (all editions; filter by joining verse.edition_id)
-- ---------------------------------------------------------------------
CREATE VIRTUAL TABLE verse_fts USING fts5 (
  text_search,
  content = 'verse',
  content_rowid = 'id',
  tokenize = 'unicode61 remove_diacritics 2'
);

-- ---------------------------------------------------------------------
-- Convenience views for the app
-- ---------------------------------------------------------------------
-- All editions' verses for one canonical verse (side-by-side view).
CREATE VIEW parallel_verse AS
SELECT vm.canon_verse_id, vm.relation, e.id AS edition_id, e.language, e.direction,
       v.id AS verse_id, v.book_id, v.chapter, v.verse, v.part, v.text
FROM verse_map vm
JOIN verse   v ON v.id = vm.verse_id
JOIN edition e ON e.id = v.edition_id;

-- Lexicon entries for a morpheme, per lexicon: an exact extended-Strong's match wins;
-- otherwise the base Strong's number; otherwise (no Strong's at all) the lemma.
CREATE VIEW morpheme_lexicon AS
SELECT m.id AS morpheme_id, le.lexicon_id, le.id AS entry_id, 'exact' AS match
FROM morpheme m
JOIN lexicon_strongs ls ON ls.strongs_ext = m.strongs_ext
JOIN lexicon_entry le   ON le.id = ls.entry_id
UNION ALL
SELECT m.id, le.lexicon_id, le.id, 'base'
FROM morpheme m
JOIN lexicon_strongs ls ON ls.strongs = m.strongs
JOIN lexicon_entry le   ON le.id = ls.entry_id
WHERE NOT EXISTS (SELECT 1 FROM lexicon_strongs x JOIN lexicon_entry y ON y.id = x.entry_id
                  WHERE x.strongs_ext = m.strongs_ext AND y.lexicon_id = le.lexicon_id)
UNION ALL
SELECT m.id, le.lexicon_id, le.id, 'lemma'
FROM morpheme m
JOIN lexicon_entry le ON le.lemma = m.lemma
WHERE m.strongs IS NULL AND m.strongs_ext IS NULL;

-- Every occurrence of a Strong's number, with its canonical reference.
CREATE VIEW strongs_occurrence AS
SELECT m.strongs, m.strongs_ext, m.lemma, m.morph_code, t.surface, t.position,
       v.edition_id, v.book_id, v.chapter, v.verse, vm.canon_verse_id
FROM morpheme m
JOIN token t  ON t.id = m.token_id
JOIN verse v  ON v.id = t.verse_id
LEFT JOIN verse_map vm ON vm.verse_id = v.id
WHERE m.strongs IS NOT NULL;
