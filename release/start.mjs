// Starts the Bible reader from the release folder and opens it in the browser.
//
//   node start.mjs                 http://localhost:3000, opens the browser
//   node start.mjs --port 8080     another port
//   node start.mjs --no-open       don't open the browser
//   node start.mjs --notes FILE    keep bookmarks and notes in FILE
//
// Bookmarks and notes are saved in a per-user folder (outside this folder, so they survive
// upgrades): ~/Library/Application Support/enduring-admiration on macOS, %APPDATA%\enduring-admiration
// on Windows, $XDG_DATA_HOME (or ~/.local/share)/enduring-admiration on Linux.
//
// The server listens on this computer only (127.0.0.1). Stop it with Ctrl+C.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

// Search needs SQLite's full-text index (FTS5), which Node's built-in SQLite has from 22.16 and
// 24.0 on (Node 23 never had it).
const NEED = "Node.js 22.16 or newer (but not Node 23)";
const tooOld = () => {
  console.error(`This app needs ${NEED}. You have ${process.versions.node}.`);
  console.error("Download the LTS version from https://nodejs.org and run this again.");
  process.exit(1);
};
const [major, minor] = process.versions.node.split(".").map(Number);
if (major < 22 || (major === 22 && minor < 16)) tooOld();
try {
  const { DatabaseSync } = await import("node:sqlite");
  const probe = new DatabaseSync(":memory:");
  if (!probe.prepare("SELECT 1 FROM pragma_compile_options WHERE compile_options = 'ENABLE_FTS5'").get()) tooOld();
  probe.close();
} catch {
  tooOld();
}

const args = process.argv.slice(2);
const flag = (name) => args.includes(name);
const option = (name, fallback) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};
const port = option("--port", process.env.PORT ?? "3000");
const host = "127.0.0.1";
const url = `http://localhost:${port}`;

function defaultNotes() {
  const home = os.homedir();
  const dir =
    process.platform === "darwin" ? path.join(home, "Library", "Application Support")
    : process.platform === "win32" ? (process.env.APPDATA ?? path.join(home, "AppData", "Roaming"))
    : (process.env.XDG_DATA_HOME ?? path.join(home, ".local", "share"));
  return path.join(dir, "enduring-admiration", "notes.json");
}
const notes = path.resolve(option("--notes", process.env.BIBLE_NOTES ?? defaultNotes()));

const here = path.dirname(fileURLToPath(import.meta.url));
const server = path.join(here, "app", "server.js");
const dbPath = path.join(here, "db", "bible.db");
for (const [file, what] of [[server, "app/server.js"], [dbPath, "db/bible.db"]]) {
  if (!existsSync(file)) {
    console.error(`Missing ${what}. Unpack the whole download and run start again from its folder.`);
    process.exit(1);
  }
}

const child = spawn(process.execPath, ["--disable-warning=ExperimentalWarning", server], {
  cwd: path.join(here, "app"),
  env: { ...process.env, PORT: port, HOSTNAME: host, BIBLE_DB: dbPath, BIBLE_NOTES: notes, NODE_ENV: "production" },
  stdio: ["ignore", "ignore", "inherit"],
});
child.on("exit", (code) => process.exit(code ?? 0));
for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => child.kill(sig));

const up = () =>
  new Promise((resolve) => {
    http.get(`http://${host}:${port}/about`, (res) => resolve(res.statusCode === 200)).on("error", () => resolve(false));
  });

const openBrowser = () => {
  const [cmd, cmdArgs] =
    process.platform === "darwin" ? ["open", [url]]
    : process.platform === "win32" ? ["cmd", ["/c", "start", "", url]]
    : ["xdg-open", [url]];
  spawn(cmd, cmdArgs, { stdio: "ignore", detached: true }).on("error", () => {}).unref();
};

for (let i = 0; i < 120; i++) {
  if (await up()) {
    console.log(`The Bible reader is running at ${url}`);
    console.log(`Bookmarks and notes are saved in ${notes}`);
    console.log("Keep this window open while you read. Press Ctrl+C to stop.");
    if (!flag("--no-open")) openBrowser();
    break;
  }
  if (i === 119) {
    console.error(`The server did not start. Is something else using port ${port}? Try: node start.mjs --port 3001`);
    child.kill();
    process.exit(1);
  }
  await new Promise((r) => setTimeout(r, 250));
}
