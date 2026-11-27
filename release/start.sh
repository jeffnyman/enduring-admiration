#!/bin/sh
# Mac and Linux: start the Bible reader. Needs Node.js 22.13 or newer (https://nodejs.org).
cd "$(dirname "$0")" || exit 1
if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is not installed. Download the LTS version from https://nodejs.org and run this again."
  exit 1
fi
exec node start.mjs "$@"
