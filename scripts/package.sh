#!/usr/bin/env bash
# Build the release download: one zip that runs on Mac, Windows and Linux with Node.js 22.16+ (not 23).
#
#   scripts/package.sh            -> dist/bible-reader-<version>.zip (+ .sha256)
#   scripts/package.sh --no-test  skip starting the packaged app and running the smoke test
#
# Uses the existing db/bible.db (build it with scripts/check.sh --full). The zip holds:
#   start.command / start.sh / start.cmd / start.mjs   launchers
#   app/          Next.js standalone server (no npm install needed; no native modules)
#   db/bible.db   the database
#   README.txt, NOTICE.txt, TEXTS.md, LICENSE (the code; the data licenses are in NOTICE.txt)
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
TEST=1
[[ "${1:-}" == "--no-test" ]] && TEST=0

[[ -f db/bible.db ]] || { echo "db/bible.db missing: run scripts/check.sh --full"; exit 1; }
[[ -d web/node_modules ]] || { echo "Missing web/node_modules: (cd web && npm install)"; exit 1; }
VERSION=$(node -p "require('./web/package.json').version")
NAME="bible-reader-$VERSION"
OUT="$ROOT/dist/$NAME"
rm -rf "$OUT" "$ROOT/dist/$NAME.zip" "$ROOT/dist/$NAME.zip.sha256"
mkdir -p "$OUT/db"

echo "==> Building the standalone server"
(cd web && NEXT_OUTPUT=standalone npx next build >"$ROOT/dist/build.log" 2>&1) \
  || { tail -40 "$ROOT/dist/build.log"; exit 1; }
cp -R web/.next/standalone "$OUT/app"
mkdir -p "$OUT/app/.next"
cp -R web/.next/static "$OUT/app/.next/static"
[[ -d web/public ]] && cp -R web/public "$OUT/app/public"
# guard against the database or dev caches being traced into the server bundle
find "$OUT/app" -name "*.db" -print -delete
rm -rf "$OUT/app/.next/cache"
# sharp is Next's optional image optimizer (unused here) with per-platform binaries: leave it out
rm -rf "$OUT/app/node_modules/sharp" "$OUT/app/node_modules/@img"
# the build records this machine's absolute paths in its config; make them relative
grep -rlF "$ROOT" "$OUT/app" | while read -r f; do
  sed -i.bak -e "s|$ROOT/web|.|g" -e "s|$ROOT|..|g" "$f" && rm "$f.bak"
done
if grep -rqF "$ROOT" "$OUT/app"; then echo "absolute build paths left in the bundle:"; grep -rlF "$ROOT" "$OUT/app"; exit 1; fi
if find "$OUT/app/node_modules" -name "*.node" | grep -q .; then
  echo "native modules in the bundle (the release must stay platform-independent):"
  find "$OUT/app/node_modules" -name "*.node"; exit 1
fi

echo "==> Copying the database"
cp db/bible.db "$OUT/db/bible.db"

echo "==> Launchers and notices"
cp release/start.mjs release/start.sh release/README.txt TEXTS.md LICENSE "$OUT/"
cp release/start.sh "$OUT/start.command"
# Windows batch files want CRLF line endings
sed 's/$/\r/' release/start.cmd >"$OUT/start.cmd"
chmod +x "$OUT/start.sh" "$OUT/start.command"
node --disable-warning=ExperimentalWarning -e '
const { DatabaseSync } = require("node:sqlite");
const db = new DatabaseSync(process.argv[1], { readOnly: true });
const rows = db.prepare("SELECT title, version, license, attribution FROM source ORDER BY id").all();
const lines = [
  "SOURCES AND LICENSES",
  "====================",
  "",
  "db/bible.db is built from the sources below. Because the Swete Septuagint data is",
  "CC BY-SA 4.0, the database as a whole is distributed under CC BY-SA 4.0",
  "(https://creativecommons.org/licenses/by-sa/4.0/) with these attributions.",
  "",
];
for (const r of rows) {
  lines.push(r.title, `  License: ${r.license}`, `  ${r.attribution}`);
  if (r.version) lines.push(`  Version: ${r.version}`);
  lines.push("");
}
lines.push(
  "Fonts: Noto Serif and Noto Serif Hebrew, SIL Open Font License 1.1 (bundled in app/).",
  "Software: this reader, MIT License (see LICENSE); Next.js and React, MIT License.",
);
console.log(lines.join("\n"));
' "$OUT/db/bible.db" >"$OUT/NOTICE.txt"

if [[ $TEST == 1 ]]; then
  echo "==> Testing the packaged app"
  PORT=${PACKAGE_PORT:-3124}
  (cd "$OUT" && node start.mjs --port "$PORT" --no-open >"$ROOT/dist/server.log" 2>&1) &
  SERVER=$!
  trap 'pkill -P $SERVER 2>/dev/null; kill $SERVER 2>/dev/null || true' EXIT
  for _ in $(seq 1 80); do
    curl -sf "http://localhost:$PORT/about" >/dev/null && break
    sleep 0.5
  done
  (cd web && BASE_URL="http://localhost:$PORT" node scripts/smoke.mjs) | tail -3
fi

echo "==> Zipping"
(cd "$ROOT/dist" && rm -f "$NAME.zip" && zip -qr -9 -y "$NAME.zip" "$NAME" \
  && shasum -a 256 "$NAME.zip" >"$NAME.zip.sha256")
du -sh "$OUT" "$ROOT/dist/$NAME.zip" | sed 's|'"$ROOT"'/||'
echo "Done: dist/$NAME.zip"
