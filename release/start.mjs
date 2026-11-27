// Starts the Bible reader from the release folder and opens it in the browser.
//
//   node start.mjs                 http://localhost:3000, opens the browser
//   node start.mjs --port 8080     another port
//   node start.mjs --no-open       don't open the browser
//
// The server listens on this computer only (127.0.0.1). Stop it with Ctrl+C.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const MIN = [22, 13];
const [major, minor] = process.versions.node.split(".").map(Number);
if (major < MIN[0] || (major === MIN[0] && minor < MIN[1])) {
  console.error(`This app needs Node.js ${MIN.join(".")} or newer (you have ${process.versions.node}).`);
  console.error("Download the LTS version from https://nodejs.org and run this again.");
  process.exit(1);
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
  env: { ...process.env, PORT: port, HOSTNAME: host, BIBLE_DB: dbPath, NODE_ENV: "production" },
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
