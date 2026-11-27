# Bible — side by side with Hebrew and Greek

A local-first Bible: the World English Bible beside the Hebrew (WLC), the Septuagint (Swete; Brenton as a cross-check) and the Greek New Testament (SBLGNT). Every Hebrew and Greek word opens its lemma, parsing and entries from Strong's, BDB, Thayer's and LSJ. All text comes from openly licensed source files; nothing is typed in by hand.

For why these Hebrew and Greek editions were chosen, what each is good and weak at, and how verse numbering is reconciled, see [About the texts](TEXTS.md).

## Reading and study

- **Side by side:** English (WEB) beside the Hebrew, the Septuagint and the Greek New Testament, aligned verse by verse; columns can be switched on and off.
- **Word study:** click any Hebrew or Greek word for its lemma, parsing in plain English, lexicon entries (Strong's, BDB, Thayer's, LSJ), Septuagint equivalents and all occurrences. The **Glosses** switch puts an English gloss under every word.
- **Commentaries:** the ¶ button beside a verse opens seven commentaries across about 1,800 years: the Church Fathers, the Catena Aurea, Matthew Henry, Adam Clarke, Keil & Delitzsch, Tyndale Open Study Notes, and unfoldingWord's Translation Notes (which are linked to the Hebrew and Greek words they discuss). Each book has an introduction page. [About the texts](TEXTS.md#the-commentaries) explains the traditions they come from.
- **Cross-references:** the ↗ button beside a verse number lists related verses with their text (OpenBible.info, CC BY, ranked by votes, plus the WEB's own notes).
- **Bookmarks and notes:** ☆ and ✎ beside a verse number. The downloaded reader saves them in a file on your computer, outside the app folder so upgrades keep them: `~/Library/Application Support/enduring-admiration/notes.json` on macOS, `%APPDATA%\enduring-admiration\notes.json` on Windows, `~/.local/share/enduring-admiration/notes.json` on Linux, or wherever `--notes FILE` (or `BIBLE_NOTES`) points. Without a notes file, for example on a hosted site, they stay in the browser. Notes made in the browser are copied into the file the first time it's available. The Bookmarks page shows where they are, and can export and import them as a file.
- **Keyboard:** `j`/`k` next/previous verse, `h`/`l` or ←/→ previous/next chapter, `g` glosses, `b` bookmark, `e` note, `x` cross-references, `c` commentary, `?` for the list.
- **Search:** English words or "phrases", Hebrew and Greek (vowels and accents optional), or a Strong's number such as H7225.
- **Canons:** the book picker lists the Protestant, Catholic or Orthodox canon; the latter two read Daniel and Esther with their Greek additions in place.

## Terms used here

**Texts (the columns in the reader)**

- **WEB — World English Bible.** A modern English translation in the public domain, made by volunteers as an update of the American Standard Version (1901). We use the edition from eBible.org that includes the deuterocanonical books.
- **WLC — Westminster Leningrad Codex.** The standard digital Hebrew Old Testament, transcribed from the Leningrad Codex (about 1008 AD), the oldest complete manuscript of the Hebrew Bible. It is the Masoretic Text, the traditional Jewish text with vowel points and cantillation marks.
- **OSHB / MorphHB — Open Scriptures Hebrew Bible.** A project that adds a dictionary form (lemma), Strong's number and grammatical parsing to every word of the WLC.
- **Septuagint (LXX).** The ancient Greek translation of the Hebrew Scriptures, made in the last centuries BC. It includes the deuterocanonical books, was the Bible of the early church, and is still the Old Testament of the Orthodox churches. Its chapters and verses are often numbered differently from the Hebrew.
- **Swete.** H. B. Swete's *The Old Testament in Greek according to the Septuagint* (Cambridge, 1887–1894). It prints one main manuscript, usually Codex Vaticanus (4th century), with another where Vaticanus is damaged (Codex Alexandrinus in most of Genesis). This is our main Septuagint column. The digital text is from the First1KGreek project. Its lemmas and parsing were machine-generated with Morpheus by the QuantForgeSoftware/lxx project. About 1,600 clear OCR errors in the transcription are corrected at build time (only one-letter errors confirmed by Brenton and by the same word elsewhere in Swete, never Vaticanus spellings); the word drawer shows the transcription's original form.
- **Brenton.** Sir Lancelot Brenton's 1844 edition of the Septuagint, Greek text largely following Codex Vaticanus. It has no word-level data here; we use it to cross-check Swete and as an optional column.
- **SBLGNT — SBL Greek New Testament.** A critical edition of the Greek New Testament published in 2010 by the Society of Biblical Literature, edited by Michael W. Holmes. We use the official source files (LogosBible/SBLGNT), including the textual apparatus.
- **TAGNT — Translators Amalgamated Greek New Testament.** STEPBible's word-by-word tagging of the Greek NT (lemma, Strong's number, parsing, English gloss), which we attach to the SBLGNT words.
- **TAHOT — Translators Amalgamated Hebrew Old Testament.** STEPBible's word-by-word tagging of the Hebrew Bible, the Hebrew counterpart of TAGNT. We use its in-context English glosses and transliterations for the gloss line and word drawer.
- **Theodotion / Old Greek.** Daniel survives in two Greek versions. The *Old Greek* is the original Septuagint translation; *Theodotion's* later version replaced it in church use. We use Theodotion for Daniel, Susanna and Bel; the Old Greek is available as an optional column on those books.
- **Deuterocanon / Apocrypha.** Books found in the Septuagint but not the Hebrew Bible, such as Tobit, Judith, the Maccabees and Sirach. Catholics and Orthodox count many of them as Scripture; Protestants generally do not. The book picker can filter by canon.

**Word study**

- **Lemma.** The dictionary form of a word: λόγος is the lemma of λόγου and λόγους.
- **Parsing / morphology.** A word's grammatical form, such as "verb, perfect, 3rd person singular". Each source writes these as short codes, which the app spells out.
- **Strong's numbers.** From James Strong's *Exhaustive Concordance* (1890), which numbered every Hebrew (H) and Greek (G) word in the King James Bible, e.g. H7225, G3056. Many tools use them as a shared key.
- **BDB.** The Brown–Driver–Briggs *Hebrew and English Lexicon* (1906), the classic Hebrew dictionary. The digital version here is still in progress; many entries are outlines.
- **Thayer's.** J. H. Thayer's *Greek-English Lexicon of the New Testament* (1889).
- **LSJ.** The Liddell–Scott–Jones *Greek–English Lexicon*, the standard dictionary of ancient Greek. It covers the Septuagint vocabulary that New Testament lexicons don't.
- **Gloss line.** The "Glosses" switch in the reader puts a short English gloss under each Hebrew and Greek word. Hebrew (TAHOT) and New Testament (TAGNT) glosses fit the word's context; Septuagint glosses, shown in italics, are dictionary glosses from LSJ, because no in-context source exists.
- **Septuagint equivalents.** For a Hebrew word, the Greek words the Septuagint most often uses for it (and for a Greek word, the Hebrew words it usually renders), with how often each Greek word appears in the New Testament. They are measured from verses where both words occur in the aligned Hebrew and Greek texts (a Dice score), so they are statistical, not a word-by-word alignment.
- **Ketiv / Qere.** In some places the Hebrew text is written one way (*ketiv*, "what is written") but traditionally read another (*qere*, "what is read"). The reader shows both.
- **Morpheus.** A program from the Perseus Project that analyzes Greek word forms automatically.

**Commentaries**

- **Tyndale Open Study Notes.** Study-Bible notes, book introductions, theme articles and profiles from Tyndale House Publishers (2022, CC BY-SA 4.0). Modern evangelical.
- **Translation Notes.** unfoldingWord's notes on the Hebrew and Greek for Bible translators (CC BY-SA 4.0). Each note quotes the original words it explains, and the reader links it to them.
- **The Church Fathers.** About 21,700 excerpts from 73 Fathers (Chrysostom, Augustine, Basil and others) in Schaff's public-domain *Ante-Nicene* and *Nicene and Post-Nicene Fathers*. They come from the HistoricalChristianFaith Commentaries-Database, keeping only excerpts whose words match Schaff's text (`pipeline/curate_fathers.py`).
- **Matthew Henry.** *Commentary on the Whole Bible* (1706–21), the classic devotional commentary (public domain, CrossWire module).
- **Adam Clarke.** *Commentary and Critical Notes* (1810–26), a Methodist scholar's verse-by-verse commentary (public domain, CrossWire module).
- **Catena Aurea.** Thomas Aquinas's chain of comments from the Church Fathers on the four Gospels, in the English translation made under J. H. Newman (1841–45; public domain).
- **Keil & Delitzsch.** C. F. Keil and F. Delitzsch's 19th-century commentary on the Hebrew text of the Old Testament (public domain; transcription from Wikisource via CrossWire).

**Verse numbering**

- **Versification.** How a Bible divides text into chapters and verses. Hebrew, Greek, Latin and English Bibles differ in places (e.g. Hebrew Malachi 3:19 is English Malachi 4:1, and Greek Psalm 22 is Hebrew and English Psalm 23).
- **Standard numbering.** The common grid the reader aligns everything on: English numbering as in the NRSV, with Psalm titles as verse 0 ("title").
- **TVTMS.** STEPBible's *Translators Versification Traditions with Methodology for Standardisation*: a public dataset of rules for converting each tradition's numbering to Standard numbering. We apply it to every edition, plus a few documented fixes in `pipeline/versification_overrides.tsv`.

- **Reading layouts.** Catholic and Orthodox Bibles read Daniel with the Prayer of Azariah and the Song of the Three inside chapter 3 and Susanna and Bel as chapters 13–14, and Esther with its Greek additions in place (lettered A–F). Choosing the Catholic or Orthodox canon in the book picker shows Daniel and Esther this way; the Protestant canon shows them in Standard order. The layouts are built into `bible.db` from the WEB's Greek Daniel and Swete's Esther and checked at build time.

**File formats** (only relevant to the data pipeline): **USFM** (Bible text markup used by eBible.org), **OSIS** and **TEI** (XML formats for scripture and other texts), **SQLite FTS5** (the full-text search index inside `bible.db`).

## Download and run

The easiest way to read is the release download, `bible-reader-<version>.zip` (about 130 MB). Unzip it and double-click `start.command` (Mac) or `start.cmd` (Windows), or run `./start.sh` (Mac/Linux). The reader opens at http://localhost:3000. It needs only [Node.js](https://nodejs.org) 22.16 or newer (not Node 23, whose built-in SQLite lacks full-text search). There is no install step, nothing to compile, and nothing is sent over the network. The same zip runs on Mac, Windows and Linux. `README.txt` inside explains the details, `NOTICE.txt` lists every source and license, and `TEXTS.md` is included.

To make the zip from a built `db/bible.db`:

```bash
scripts/package.sh        # -> dist/bible-reader-<version>.zip and .sha256; tests the packaged app first
```

It builds the Next.js standalone server (`NEXT_OUTPUT=standalone`) and adds launchers (`release/`), notices and a slimmed copy of the database. `pipeline/slim_db.py` leaves out the raw source tags that only the build uses and stores three lookup tables more compactly. It verifies the copy before accepting it, with SQLite and FTS5 integrity checks and identical row counts. `db/bible.db` itself stays the full build. It then checks that no native modules or build-machine paths ended up in the bundle, starts the packaged app and runs the browser smoke test against it.

## Run it from source

```bash
# 1. Build the database (first run downloads ~150 source files into data/cache/, ~2 min)
python3 -m venv .venv
.venv/bin/python pipeline/build_bible.py        # -> db/bible.db + data/build_report.md

# 2. Start the reader
cd web
npm install
npm run build && npm start                      # http://localhost:3000
# or, while developing:  npm run dev
```

`BIBLE_DB=/path/to/bible.db` points the app at a database elsewhere. `pipeline/sample_ingest.py` is the small Genesis 1 / Tobit 1 / John 1 test build (writes `db/sample.db`).

## Check it

```bash
scripts/check.sh          # sample pipeline test, web typecheck/lint/build, browser smoke test
scripts/check.sh --full   # also rebuilds db/bible.db and runs its full verification first (~3 min)
```

On GitHub, the **CI** workflow runs `scripts/check.sh --full` on Linux for every push and pull request. It then packages the release zip and starts it on Linux, Windows and macOS, on Node 22.16 (the oldest supported) and the current LTS, and runs the smoke test against each. **Test release download** does the same for the zip attached to a published release, after checking its SHA-256.

The smoke test drives Chrome (or `CHROME_PATH`, or a Playwright-managed Chromium) through the reader: opening chapters, clicking Hebrew and Greek words, navigating, searching and the phone layout. It checks structure and behaviour only, never Scripture text. The quick mode needs an existing `db/bible.db`.

## Layout

| Path | What |
|---|---|
| `db/schema.sql` | SQLite schema (editions, verses, Standard-numbering map, words, morphemes, lexicons, FTS5) |
| `pipeline/build_bible.py` | Full build + verification report |
| `pipeline/bibleingest/` | Parsers: USFM, MorphHB, Swete TEI, TAGNT, lexicons, TVTMS versification |
| `pipeline/curate_fathers.py`, `pipeline/fathers_allowlist.tsv` | Chooses the Church Fathers excerpts (only those whose words match Schaff's translation); the build loads only the listed ones |
| `pipeline/slim_db.py` | Makes the smaller release copy of `bible.db` (checked before use) |
| `pipeline/versification_overrides.tsv` | Documented numbering fixes TVTMS doesn't cover (each checked at build time) |
| `web/` | Next.js reader (App Router, built-in node:sqlite, read-only) |
| `release/` | Launchers and README for the download; `scripts/package.sh` builds it |

## Licensing

The code (the pipeline, the reader and the scripts) is under the [MIT License](LICENSE).

The data is licensed separately. Texts are public domain or CC BY / CC BY-SA; see the app's **Sources** page or the `source` table. Because the Swete Septuagint data is CC BY-SA 4.0, a distributed `bible.db` is CC BY-SA 4.0 with the listed attributions. Bundled fonts (Noto Serif, Noto Serif Hebrew) are OFL; SBL Hebrew / Galatia SIL are used when installed locally.
