#!/usr/bin/env bash
# One command to verify the project.
#
#   scripts/check.sh          sample pipeline test + web typecheck/lint/build + browser smoke test
#   scripts/check.sh --full   also rebuilds db/bible.db and runs its 49 checks first (~2 min)
#
# The smoke test runs against db/bible.db, so build it once with --full (or
# .venv/bin/python pipeline/build_bible.py) before the quick mode.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
PY="$ROOT/.venv/bin/python"
PORT=${CHECK_PORT:-3123}
LOGS=$(mktemp -d)
FULL=0
[[ "${1:-}" == "--full" ]] && FULL=1

step() { printf '\n==> %s\n' "$*"; }
run() {  # run quietly, show the log tail on failure
  local name=$1; shift
  if ! "$@" >"$LOGS/$name.log" 2>&1; then
    echo "FAILED: $name (log: $LOGS/$name.log)"; tail -40 "$LOGS/$name.log"; exit 1
  fi
}

[[ -x "$PY" ]] || { echo "Missing .venv: python3 -m venv .venv"; exit 1; }
[[ -d web/node_modules ]] || { echo "Missing web/node_modules: (cd web && npm install)"; exit 1; }

step "Pipeline: sample test (db/sample.db)"
run sample "$PY" pipeline/sample_ingest.py
grep -E '\[FAIL\]|RESULT' "$LOGS/sample.log"

if [[ $FULL == 1 ]]; then
  step "Pipeline: full build + checks (db/bible.db)"
  run full "$PY" pipeline/build_bible.py
  grep -E 'FAIL|RESULT' "$LOGS/full.log"
fi
[[ -f db/bible.db ]] || { echo "db/bible.db missing: run scripts/check.sh --full"; exit 1; }

step "Web: typecheck, lint, production build"
(cd web && run typecheck npm run typecheck && echo "typecheck ok")
(cd web && run lint npm run lint && echo "lint ok")
(cd web && run build npx next build && echo "build ok")

step "Web: browser smoke test (port $PORT)"
(cd web && BIBLE_DB="$ROOT/db/bible.db" npx next start -p "$PORT" >"$LOGS/server.log" 2>&1) &
SERVER=$!
trap 'pkill -P $SERVER 2>/dev/null; kill $SERVER 2>/dev/null || true' EXIT
for _ in $(seq 1 60); do
  curl -sf "http://localhost:$PORT/about" >/dev/null && break
  sleep 0.5
done
curl -sf "http://localhost:$PORT/about" >/dev/null || { echo "server did not start"; tail -20 "$LOGS/server.log"; exit 1; }
(cd web && BASE_URL="http://localhost:$PORT" node scripts/smoke.mjs)

printf '\nAll checks passed.\n'
