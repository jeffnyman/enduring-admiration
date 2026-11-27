Act as a senior full-stack engineer. I am building a local-first web Bible application using 100% public-domain Scripture datasets. I have both Node.js and Python 3 installed on my machine.

Architecture & Stack:

• Data Pipeline (Python): Write Python ingestion scripts to parse standard open-source biblical formats (USFM / OSIS XML / TSV) and build a clean, indexed SQLite database (bible.db).
• Web App (Node.js): Build a fast, clean Next.js (App Router) + TypeScript + Tailwind CSS frontend that reads directly from bible.db (using better-sqlite3 or Prisma).

Core Features & Public-Domain Data Sources:

1. English Text: World English Bible (WEB) with Deuterocanon/Apocrypha (covering Protestant, Catholic, and Orthodox canons) from eBible.org (eng-web_usfm.zip or OSIS).
2. Original Languages (Side-by-Side / Interlinear):
	• Old Testament: OpenScriptures Hebrew Bible (MorphHB / Westminster Leningrad Codex)
	• Apocrypha / Deuterocanon: Public-domain Greek Septuagint (LXX via OpenScriptures / STEP Bible / Rahlfs)
	• New Testament: Public-domain Greek New Testament (OpenGNT or SBLGNT with morphology)
3. Interactive Lexicon: Clicking any Hebrew or Greek word opens a side drawer showing the lemma, transliteration, Strong’s number, morphological parsing code (decoded into plain English), and definition from public-domain Strong’s / Thayer’s / BDB dictionaries.
4. Navigation & Search: Book/chapter/verse selector supporting deuterocanonical books, plus full-text English search (using SQLite FTS5) and Strong’s number lookup.

Strict Rules:

• Zero Hardcoded Scripture: Never generate Bible verses from your training data. All text must come from parsed open-source files.
• Typography & Versification: Enforce dir="rtl" and proper Unicode font stacks (e.g., SBL Hebrew / Noto Serif Hebrew & Galatia SIL / Noto Serif) for pointed Hebrew and polytonic Greek. Account for versification differences between the Septuagint (LXX) and English/Masoretic numbering.

Step 1 — Do Not Build the Whole App Yet:

1. Give me the exact terminal commands to initialize the project folder (bible-app) with Next.js and a Python virtual environment (venv).

2. Design the SQLite schema (schema.sql) that cleanly links English verses, word-level Hebrew/Greek tokens, and Strong’s lexicon entries across all canons.

3. Give me a Python test script that downloads/parses just Genesis 1 (Hebrew + WEB), Tobit 1 (LXX Greek + WEB), and John 1 (NT Greek + WEB) into bible.db so we can verify encoding and alignment before ingesting the entire Bible.
