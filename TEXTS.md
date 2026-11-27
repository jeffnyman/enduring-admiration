# About the texts: what you are reading, and why

This guide is for readers who care about *which* Hebrew and Greek they are looking at: students, pastors, translators, and anyone who has wondered why two Bibles disagree about a verse number. It explains which editions this app uses, why we chose them, what each one is good and bad at, and where the app relies on machine work you should check against a printed edition before you build an argument on it.

The [README](README.md) has the short definitions. This page gives the reasons behind them. Figures quoted here come from the build's own verification report (`data/build_report.md`), which is regenerated every time the database is built.

## The ground rule: open texts only

Every word of Scripture in the app is parsed from a published, openly licensed file. Nothing is typed in by hand, and nothing comes from an AI model's memory. That rule settles most of the choices below, because many of the editions scholars use today are copyrighted and cannot be redistributed freely:

- **Hebrew:** *Biblia Hebraica Stuttgartensia* (BHS) and *Biblia Hebraica Quinta* (Deutsche Bibelgesellschaft). Their base text, the Leningrad Codex, is old enough to be free; their critical apparatus is not.
- **Septuagint:** Rahlfs–Hanhart (Deutsche Bibelgesellschaft) and the Göttingen *Septuaginta* volumes.
- **Greek New Testament:** Nestle–Aland 28 and UBS 5.
- **Lexicons:** BDAG, HALOT and the other standard modern dictionaries.

So the app uses the best editions that can be shared, and tells you what you give up by using them. The aim is for the text to travel freely; where a license asks for attribution or share-alike, the app keeps to it (see the **Sources** page).

## The Hebrew Old Testament

### The text: the Leningrad Codex (WLC)

The Hebrew column is the **Westminster Leningrad Codex**, version 4.20, from the Open Scriptures Hebrew Bible project. It is a careful digital transcription of the **Leningrad Codex** (about 1008 AD), the oldest complete manuscript of the Hebrew Bible. It is the same manuscript that BHS and BHQ print. It is a **Masoretic** text: the consonants are supplied with the vowel points, accents (cantillation marks) and marginal notes of the medieval Masoretes, the scribes who fixed how the text was to be read.

What this means for you:

- **This is one manuscript, not a reconstruction.** No editor has chosen readings from the Dead Sea Scrolls, the Samaritan Pentateuch or the ancient versions. Where scholars think the Hebrew has suffered in copying, you will see the Leningrad reading and no note about it. A printed BHS or BHQ apparatus is the place to check such passages.
- **Vowels and accents are part of the tradition, not the original autographs.** The consonantal text is far older than the pointing. When a word's parsing depends on its vowels, the app is following the Masoretic interpretation.
- **Ketiv and Qere are both kept.** Where the Masoretes wrote one form in the text (*ketiv*, "what is written") and directed that another be read (*qere*, "what is read"), the app stores both and shows both. Glosses and searches follow the Qere, as the reading tradition does.

### The word data: OSHB morphology

Every Hebrew word carries its lemma, Strong's number and parsing from the **Open Scriptures Hebrew Bible** (OSHB / MorphHB). This is human-curated work, not machine guesses, and it covers 100% of the words. OSHB splits each word into its parts (a prefix such as the conjunction or a preposition, the stem, a pronominal suffix), and the app keeps those parts separate, so clicking a word shows each piece with its own lexicon entry.

OSHB writes parsing as compact codes. The app decodes them into plain English with its own decoder, written against the OSHB specification, and the build checks that every code in the Bible decodes.

### The English glosses: STEPBible TAHOT

The gloss line under the Hebrew (the **Glosses** switch) comes from STEPBible's **Translators Amalgamated Hebrew OT** (TAHOT), produced by Tyndale House, Cambridge. These glosses are written *for the word in context*, not copied from a dictionary, so the same Hebrew word can carry different glosses in different verses. They were matched to the WLC words by comparing consonants; 99.95% of the Hebrew words (Ketiv forms excepted) get one.

A gloss is a translator's aid, not a definition. Use it to find your place in the sentence, then open the lexicon.

## The Septuagint

The Septuagint (LXX) is not one book with one text. It is a collection of translations made by different people, in different places, over two or three centuries before Christ, plus some books composed in Greek. Its manuscripts differ, its books are ordered differently from the Hebrew, and several of its books exist in two Greek forms. Any edition has to make choices, and it is worth knowing which ones yours made.

### Why Swete, and not Rahlfs or Göttingen

The two editions most scholars cite are **Rahlfs–Hanhart** (a one-volume *eclectic* text: the editor chooses the best reading from several manuscripts) and the **Göttingen Septuagint** (a multi-volume critical edition, still unfinished). Both are under copyright.

The main Greek column is therefore **H. B. Swete's** *The Old Testament in Greek according to the Septuagint* (Cambridge, 1887–1894). Swete's edition is **diplomatic**: rather than reconstruct an original, it prints the text of one great manuscript and records the others' differences in notes. Usually that manuscript is **Codex Vaticanus** (B, 4th century). Where Vaticanus is missing or damaged, Swete prints another uncial instead. In most of Genesis that is **Codex Alexandrinus** (A, 5th century). The digital Judges in this app is also Swete's Alexandrinus text (the file says so in its title).

The trade-off, honestly stated:

- **Gains.** You are reading what one real ancient manuscript says, including its spellings. Swete is also the historic standard of English-speaking scholarship, and its page and verse references appear in older commentaries.
- **Losses.** Vaticanus has its own errors and peculiarities, and Swete did not correct them in the text. Swete's notes (the variants from other manuscripts) are not in the digital text the app uses, so the app shows you the Vaticanus reading without telling you when other manuscripts differ.

The digital Swete comes from the **First1KGreek** project (Harvard/Leipzig), under CC BY-SA. That share-alike license is why a distributed copy of the app's database is also CC BY-SA.

### Brenton as a cross-check

Sir Lancelot **Brenton's** 1844 Septuagint is in the public domain and also largely follows Vaticanus. It has no word-level tagging here, but it earns its place in two ways. It is an optional column, and it serves as an independent witness for checking Swete. Two digitisations of nearly the same manuscript tradition ought to agree. When aligned on the same verse numbers, Swete and Brenton agree on about 89% of their words over 27,600 verses, and the build fails if the versification mapping ever makes them agree *less* than their native numbering did.

### Machine work in the Septuagint (please read)

Two parts of the Greek Old Testament data are made by machine, and you should treat them accordingly:

1. **Lemmas and parsing.** These came from **Morpheus**, the Perseus Project's automatic analyser of Greek forms, run over Swete by the QuantForgeSoftware/lxx project. The analyser looks at each word on its own, without context, so a form that could be two things (a noun or a verb, say) may be given the wrong one. About 98% of Swete's words have an analysis. Most come straight from Morpheus; a smaller share (about 23,500 words) were inferred from the same form elsewhere in Swete.
2. **OCR corrections.** The digital Swete was made by optical character recognition, and OCR makes errors. The build corrects them only when four things are all true:
   - Morpheus could not analyse the word;
   - Brenton's word at the same place differs by exactly one letter;
   - Brenton's form appears elsewhere in Swete at least twice as a real word;
   - the difference is not a known Vaticanus spelling habit.

   That last test matters. Vaticanus spells some words in ways a modern editor would "fix", and those spellings are real evidence, not errors. On this basis 1,636 words were corrected, and 248 candidates were left alone because they looked like Vaticanus spelling. Every corrected word keeps its original transcription, and the word drawer shows it.

The Septuagint gloss line is different from the Hebrew and New Testament ones. No in-context English glossing of the LXX exists under an open license, so the Greek OT glosses are short **dictionary** glosses from LSJ, shown in *italics* to mark the difference. They tell you what a word can mean, not what it means here.

### Books that exist in two Greek forms

- **Daniel.** The original Septuagint translation of Daniel (the *Old Greek*) was replaced in the church's Bibles by a later version associated with **Theodotion**. Nearly every Greek manuscript of Daniel has Theodotion; Swete knew the Old Greek from a single manuscript (Codex Chisianus). The app follows church use and reads Theodotion for Daniel, Susanna and Bel. The Old Greek is available as an optional column on those books, covering 487 of their 531 verses.
- **Esther.** Greek Esther is longer than the Hebrew by six large passages, the **Additions A–F** (Mordecai's dream, two royal letters, the prayers of Mordecai and Esther, and others). They are not translations of anything in the Hebrew. The app keeps them distinct from the Hebrew Esther so that the Hebrew and Greek of the shared verses line up.
- **Ezra–Nehemiah and 1 Esdras.** The Septuagint has two books about the return from exile. *Esdras B* (2 Esdras in Greek numbering) is a translation of Hebrew Ezra and Nehemiah as one book; the app splits it at the Nehemiah boundary so each lines up with its Hebrew. *Esdras A* (1 Esdras) is a different, freer retelling and stands as its own book. (Confusingly, the "2 Esdras" of English Apocrypha, a Latin apocalypse also called 4 Ezra, is a third book again. It survives in Latin, not Greek, so only the WEB has it here.)

### Other places the Greek and Hebrew differ

- **Jeremiah** is about one-eighth shorter in Greek, and the oracles against the nations sit in the middle of the book rather than at the end. So Greek Jeremiah 26 is Hebrew and English Jeremiah 46, for example. The versification mapping (below) lines the two up, so the column beside Hebrew Jeremiah 46 shows the matching Greek.
- **The Psalms** are numbered differently for most of the Psalter, because the Greek joins and divides some psalms differently from the Hebrew (Greek 9 is Hebrew 9–10; Greek Psalm 22 is the Hebrew and English 23). The Greek also has a **Psalm 151**, which the app includes.
- **Samuel and Kings** are *1–4 Kingdoms* in Greek, and **Chronicles** is *Paraleipomena* ("things left out"). The app uses the familiar English names.
- **The Prayer of Manasseh** appears in Swete among the **Odes**, the collection of biblical songs printed after the Psalms. The app takes it from there, after checking it against Brenton's text of the Prayer.
- The **Psalms of Solomon** are in Swete but not in the canon of any tradition this app covers, so they are left out.

## The Greek New Testament

### The text: SBLGNT

The New Testament column is the **SBL Greek New Testament** (2010), edited by Michael W. Holmes and published by the Society of Biblical Literature and Logos Bible Software. It is an **eclectic critical text**: like Nestle–Aland, it chooses readings from the manuscripts and earlier editions instead of printing one manuscript. It differs from NA28 in a few hundred places, most of them small. Unlike NA28 it may be freely shared with attribution (CC BY).

The app takes the text from the **official SBLGNT source files**, with their apparatus. The SBLGNT apparatus compares its text with four other editions:

- Westcott–Hort;
- Tregelles;
- the Greek text behind the NIV;
- Robinson–Pierpont, a Byzantine text close to the Majority Text.

It is not a full manuscript apparatus like NA28's, but it shows you where the major printed editions part ways. That is often exactly where the interesting textual questions are.

(An early version of this app used a third-party copy of the SBLGNT that turned out to be corrupted in places, which is why we went back to the official files. If you ever see a difference between this app and a printed SBLGNT, please treat it as a bug.)

The New Testament is not the **Textus Receptus**, the Greek behind the King James Version. Where the KJV has a verse or phrase that the critical texts omit, the SBLGNT apparatus usually notes it under Robinson–Pierpont. The WEB's English, which follows the Majority Text in the New Testament, will often still have it.

### The word data: STEPBible TAGNT

Lemmas, Strong's numbers, parsing and in-context English glosses come from STEPBible's **Translators Amalgamated Greek NT** (TAGNT), from Tyndale House. TAGNT tags the words of several editions at once and marks which edition has which reading, so it can be matched to the SBLGNT word by word.

The match covers 99.98% of the words. The 34 untagged words are places where the SBLGNT has a reading that none of the editions TAGNT tags shares. They are real, if rare, editorial choices by the SBL editor, not errors (Mark 1:41, where the SBLGNT reads ὀργισθεὶς, is the best known). The build report lists them all.

## The English: the World English Bible

The **WEB** is a public-domain modern English translation, a volunteer revision of the American Standard Version (1901). It was chosen because it is free, complete, and includes the deuterocanonical books, among them Greek Daniel and Greek Esther as whole books.

Keep in mind that the WEB is a *translation with its own base texts*. In the Old Testament it translates the Hebrew, so when you read it beside the Septuagint you are comparing Greek against an English rendering of the Hebrew. That is useful, because differences between them often show you where the Greek translators read or understood the Hebrew differently. It also means the English will not "match" the Greek column, and it shouldn't.

## The lexicons

The lexicons in the app are the great public-domain dictionaries of the nineteenth and early twentieth centuries. They are still valuable, and they are also old. Here is what each is good for, and where it shows its age.

- **Strong's** (1890). James Strong numbered every Hebrew and Greek word in the King James Bible. The numbers are an excellent **index**: almost every Bible tool uses them, and they let you jump from a word to all its occurrences. The definitions are short and were written to explain the KJV's choices. Use them as signposts, not as the last word. Strong's numbers are also coarse: one number can cover words a modern lexicon would separate, and where OSHB gives a finer number (an extended Strong's such as H1254a), the app uses it.
- **BDB** — Brown, Driver and Briggs, *A Hebrew and English Lexicon of the Old Testament* (1906). For a century the standard Hebrew dictionary, and its organisation by root still repays study. It predates the discovery of **Ugaritic** (1929) and of the Dead Sea Scrolls, which changed our understanding of many rare words, so modern lexicons (HALOT, DCH) sometimes disagree with it. The open digital BDB is still being transcribed: many entries are complete, but many are so far only an outline of the senses.
- **Thayer's** — J. H. Thayer, *A Greek-English Lexicon of the New Testament* (1889). Thorough, and still useful for its references. It was written just before the great papyrus finds from Egypt, which showed that much New Testament vocabulary once thought special ("biblical Greek") was ordinary everyday Greek. BDAG, the modern standard, draws heavily on that evidence.
- **LSJ** — Liddell, Scott and Jones, *A Greek-English Lexicon*, the standard dictionary of ancient Greek as a whole. It covers the Septuagint's vocabulary, which New Testament lexicons don't. Its emphasis is classical Greek, so its first sense for a word may be the Athenian one, not the sense a Jewish translator in Alexandria had in mind. Here it supplies the Septuagint glosses and a second opinion on New Testament words.

## Septuagint equivalents

When you open a Hebrew word, the app shows which Greek words the Septuagint most often uses for it; when you open a Greek word, which Hebrew words it usually renders. This is one of the oldest and most fruitful ways of studying biblical vocabulary. The New Testament writers' Bible was largely the Greek one, so knowing that a Greek word habitually stands for a particular Hebrew one can show the Old Testament freight a New Testament word carries.

These equivalents are **statistical**. They are not a word-by-word alignment made by a scholar. For each Hebrew–Greek pair, the build counts how often the two appear in the same verse of the aligned Hebrew and Greek texts, relative to how often each appears at all (a *Dice score*). Over about 22,000 aligned verses this works well for common words. The build checks, for example, that the strongest equivalents for the Hebrew words for God, the LORD and earth are the expected Greek words, and that *davar* ("word, matter") is rendered chiefly by *logos* and *rhēma*. It is weaker for rare words, and it can be thrown off by words that merely keep each other company, such as the article. Treat the list as a lead to follow up, not as evidence in itself. A tool such as Hatch–Redpath's *Concordance to the Septuagint* is the proper check.

## Verse numbers

### Why they differ

Chapter divisions were added in the 13th century and verse numbers in the 16th, long after the texts were written, and different traditions drew the lines in different places. The Hebrew Bible, the Septuagint, the Latin Vulgate and English Bibles each have their own numbering, and they disagree in hundreds of places. A few common examples:

- **Psalm titles.** In Hebrew numbering a psalm's title ("A psalm of David…") is usually verse 1. In English Bibles it is unnumbered, so the English verse numbers run one behind the Hebrew in many psalms.
- **Malachi.** The English Malachi 4 is part of chapter 3 in Hebrew (English 4:1 is Hebrew 3:19).
- **Joel.** The English Joel 2:28–32 is chapter 3 in Hebrew, and English chapter 3 is Hebrew chapter 4.
- **Chapter starts.** Some chapters begin a verse earlier or later; Hebrew Genesis 32:1 is English Genesis 31:55, for example.

### How the app handles it

Each edition is stored with **its own native numbering**, exactly as printed, so a reference you look up in a printed WLC, Swete or Brenton matches what the app has for that edition. All editions are then mapped onto one shared grid, called **Standard numbering**: English numbering as in the NRSV, with psalm titles as "verse 0". The columns you read side by side line up on that grid, and the reader shows the native reference whenever it differs.

The mapping rules come from STEPBible's **TVTMS** (*Translators Versification Traditions with Methodology for Standardisation*), a public dataset compiled by Tyndale House that describes each tradition's numbering and how it converts to the standard grid. Where TVTMS does not cover a particular printed edition's quirks (Swete's numbering of the Esther additions, or the WEB's printing of Susanna and Bel as Daniel 13 and 14), the app adds a documented fix in `pipeline/versification_overrides.tsv`. The build tests each fix against the text of a second edition before trusting it. For two books where no fixed rule was right (Brenton's Esther additions and Swete's Letter of Jeremiah), the two Greek editions are aligned by comparing their text.

Some mappings are not one-to-one. One edition's verse may be **merged** into, or be only **part** of, another's, and the app records which. So when a Greek verse covers more or less than its English neighbour, that is the versification, not a mistake.

### Catholic and Orthodox order

Catholic and Orthodox Bibles read Daniel and Esther with their Greek material in place: the Prayer of Azariah and the Song of the Three inside Daniel 3, Susanna and Bel as chapters 13–14, and Esther's additions where they fall in the story, lettered A–F. Choosing the Catholic or Orthodox canon in the book picker shows those books in that order, while the Protestant setting shows the Hebrew order with the additions as separate books.

## A checklist before you rely on something

The app is meant for serious reading, and it tries hard to say where its data is weaker. In short:

| Data | Made by | Confidence |
|---|---|---|
| Hebrew text (WLC) | careful human transcription | high — but one manuscript, no apparatus |
| Hebrew parsing (OSHB) | human-curated | high |
| Greek NT text (SBLGNT) | critical edition, official files | high |
| Greek NT parsing (TAGNT) | human-curated, matched by the build | high |
| Septuagint text (Swete) | OCR of a diplomatic edition, 1,636 corrections by rule | good — check a printed edition for anything that matters |
| Septuagint parsing (Morpheus) | machine analysis without context | fair — verify forms that could be parsed two ways |
| Septuagint glosses (LSJ) | dictionary, not in context | a hint only |
| Hebrew–Greek equivalents | statistics over aligned verses | a lead to follow up |
| Cross-references (OpenBible.info) | crowd-sourced, ranked by votes | a starting point |
| Lexicons | public-domain classics, 1889–1940 | valuable, dated — compare with a modern lexicon |

## Further reading

If this page has whetted your appetite, these standard introductions explain the background in far more depth:

- Emanuel Tov, *Textual Criticism of the Hebrew Bible*: the manuscripts, the Masoretes and how the Hebrew text was transmitted.
- Karen H. Jobes and Moisés Silva, *Invitation to the Septuagint*: a readable introduction to the LXX, its editions and its use in New Testament study.
- Bruce M. Metzger and Bart D. Ehrman, *The Text of the New Testament*, and Metzger's *A Textual Commentary on the Greek New Testament*: how the New Testament text was copied and how editors choose between readings.
- H. B. Swete, *An Introduction to the Old Testament in Greek* (1900; public domain): Swete's own account of the Septuagint and its manuscripts, written as a companion to the edition used here.
