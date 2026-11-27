BIBLE READER: side by side with Hebrew and Greek
================================================

The World English Bible beside the Hebrew (Westminster Leningrad Codex), the Septuagint
(Swete, with Brenton) and the Greek New Testament (SBLGNT), with a lexicon for every
Hebrew and Greek word. It runs entirely on your computer: nothing is sent anywhere,
and it works without an internet connection.

WHAT YOU NEED

  Node.js 22.16 or newer (Node 23 won't work). If you don't have it, install the
  "LTS" version from https://nodejs.org (it is free). Nothing else needs installing.

START IT

  Mac:      double-click "start.command"
            (the first time, macOS may refuse to open a downloaded script: right-click it,
            choose Open, then Open again)
            or in Terminal:  ./start.sh
  Windows:  double-click "start.cmd"
  Linux:    ./start.sh

  Your browser opens the reader at http://localhost:3000. Keep the window that opened
  running while you read; close it (or press Ctrl+C) to stop.

  Another port:          ./start.sh --port 8080      (Windows: start.cmd --port 8080)
  Don't open a browser:  ./start.sh --no-open
  Another notes file:    ./start.sh --notes /path/to/notes.json

YOUR BOOKMARKS AND NOTES

  They are saved in a file on your computer, outside this folder, so they stay when
  you upgrade to a newer download and any browser you use sees the same ones:

    Mac:      ~/Library/Application Support/enduring-admiration/notes.json
    Windows:  %APPDATA%\enduring-admiration\notes.json
    Linux:    ~/.local/share/enduring-admiration/notes.json

  The previous version is kept beside it as notes.json.bak. To use another file:
  ./start.sh --notes /path/to/notes.json   (Windows: start.cmd --notes C:\path\notes.json)

  Notes you made with version 0.1.0 or 0.1.1 (saved in the browser) are copied into the
  file the first time you open the reader in that browser. The Bookmarks page can also
  export them to a file and import them again.

WHAT'S IN THIS FOLDER

  app/            the reader (a Next.js server)
  db/bible.db     all the texts, words and lexicons (SQLite)
  NOTICE.txt      sources and licenses
  TEXTS.md        about the texts: which editions, and why
  LICENSE         the software license (MIT)

LICENSE

  The software is under the MIT License (see LICENSE). The texts are public domain
  or CC BY / CC BY-SA. Because the Swete Septuagint data is CC BY-SA 4.0, db/bible.db
  is distributed under CC BY-SA 4.0 with the attributions in NOTICE.txt. You are free
  to copy and share this download.
