// Browser smoke test for the reader. Checks structure and behaviour only (no Scripture text).
//
//   BASE_URL=http://localhost:3000 node scripts/smoke.mjs
//
// Uses an installed Chrome (or CHROME_PATH); falls back to a Playwright-managed Chromium
// (`npx playwright-core install chromium`).
import { existsSync } from "node:fs";
import { chromium } from "playwright-core";

const BASE = process.env.BASE_URL ?? "http://localhost:3000";
const CANDIDATES = [
  process.env.CHROME_PATH,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
].filter(Boolean);

function browserPath() {
  const found = CANDIDATES.find((p) => existsSync(p));
  if (found) return found;
  try {
    const managed = chromium.executablePath();
    if (existsSync(managed)) return managed;
  } catch {
    // not installed
  }
  throw new Error("No Chrome found: install Chrome, set CHROME_PATH, or run `npx playwright-core install chromium`");
}

let failures = 0;
function check(ok, msg) {
  console.log(`  [${ok ? "PASS" : "FAIL"}] ${msg}`);
  if (!ok) failures++;
}

const browser = await chromium.launch({ executablePath: browserPath() });
const errors = [];
const watch = (page) => {
  page.on("pageerror", (e) => errors.push(`${page.url()}: ${e}`));
  page.on("console", (m) => m.type() === "error" && errors.push(`${page.url()}: ${m.text()}`));
};

try {
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  watch(page);

  console.log("Reader");
  await page.goto(`${BASE}/read/GEN/1`);
  const rows = page.locator(".verse-row");
  check((await rows.count()) >= 20, `Genesis 1 renders verse rows (${await rows.count()})`);
  const he = page.locator('#GEN-1-1 [lang="hbo"]');
  check((await he.getAttribute("dir")) === "rtl", "Hebrew cell is right-to-left");
  check(/[א-ת]/.test(await he.innerText()), "Hebrew cell contains Hebrew letters");
  check(/[Ͱ-Ͽἀ-῿]/.test(await page.locator('#GEN-1-1 [lang="grc"]').innerText()), "Septuagint cell contains Greek");
  check((await page.locator("#GEN-1-1 [data-tok]").count()) > 5, "words are clickable");

  console.log("Word drawer");
  await he.locator("[data-tok]").nth(1).click();
  const drawer = page.locator('aside[role="dialog"]');
  await drawer.locator("section").first().waitFor({ timeout: 10000 });
  check(await drawer.isVisible(), "clicking a Hebrew word opens the drawer");
  check((await drawer.getByText("Brown-Driver-Briggs").count()) > 0, "drawer shows a BDB entry");
  check((await drawer.locator('a[href^="/strongs/H"]').count()) > 0, "drawer links to the Strong's page");
  check((await drawer.locator("p.text-sm").first().innerText()).length > 10, "parsing is spelled out");
  await page.keyboard.press("Escape");
  check(!(await drawer.isVisible().catch(() => false)), "Escape closes the drawer");

  await page.goto(`${BASE}/read/JHN/1`);
  await page.locator('#JHN-1-1 [lang="grc"] [data-tok]').first().click();
  await drawer.locator("section").first().waitFor({ timeout: 10000 });
  check((await drawer.getByText("Thayer").count()) > 0, "clicking a Greek NT word shows Thayer's");

  console.log("Navigation");
  await page.goto(`${BASE}/read/GEN/1`);
  await page.getByRole("link", { name: "Next chapter" }).click();
  await page.waitForURL(/\/read\/GEN\/2/);
  check(page.url().includes("/read/GEN/2"), "next-chapter link works");
  // the previous chapter stays mounted (hidden) after client navigation: ids must not collide
  const dupes = await page.evaluate(() => {
    const ids = [...document.querySelectorAll("[id]")].map((e) => e.id);
    return ids.filter((id, i) => ids.indexOf(id) !== i);
  });
  check(dupes.length === 0, `no duplicate element ids after navigation ${dupes.slice(0, 5).join(" ")}`);
  await page.getByRole("combobox", { name: "Book" }).selectOption("EXO");
  await page.waitForURL(/\/read\/EXO\/1/);
  check(page.url().includes("/read/EXO/1"), "book picker navigates");
  await page.goto(`${BASE}/read/PSA/23`);
  check((await page.locator(".verse-row").first().innerText()).toLowerCase().startsWith("title"), "Psalm title has its own row");
  await page.goto(`${BASE}/read/XYZ/1`);
  check((await page.getByText("could not be found").count()) > 0, "unknown book shows not-found page");

  console.log("Search");
  await page.goto(`${BASE}/search?q=beginning`);
  const hits = page.locator("ol li a");
  check((await hits.count()) > 0, `English search returns results (${await hits.count()})`);
  await hits.first().click();
  await page.waitForURL(/\/read\/.*#[A-Z0-9]{3}-\d+-\d+$/);
  const hash = new URL(page.url()).hash.slice(1);
  await page.locator(`[id="${hash}"]`).first().waitFor({ timeout: 10000 }); // chapter streams in after the URL changes
  const anchors = await page.locator(`[id="${hash}"]`).count();
  check(anchors === 1, `a result opens its verse in the reader (${hash}, ${anchors} anchor)`);
  const count = async (q) => {
    await page.goto(`${BASE}/search?q=${encodeURIComponent(q)}`);
    return page.locator("ol li").count();
  };
  const accented = await count("λόγος");
  check(accented > 0 && accented === (await count("λογος")), "Greek search ignores accents");
  await page.goto(`${BASE}/read/GEN/1`);
  await page.locator("#q").fill("H7225");
  await page.locator("#q").press("Enter");
  await page.waitForURL(/\/strongs\/H7225/);
  check((await page.locator('section a[href^="/read/"]').count()) > 0, "Strong's number search lists occurrences");

  console.log("Greek Daniel and Esther (Catholic/Orthodox order)");
  await page.goto(`${BASE}/read/GEN/1`);
  await page.getByRole("combobox", { name: "Canon" }).selectOption("catholic");
  const bookOptions = await page.getByRole("combobox", { name: "Book" }).locator("option").evaluateAll((os) => os.map((o) => o.value));
  check(bookOptions.includes("DAG") && bookOptions.includes("ESG"), "Catholic list offers Daniel and Esther with the additions");
  check(!["DAN", "S3Y", "SUS", "BEL", "EST"].some((b) => bookOptions.includes(b)), "the pieces they absorb are not listed separately");
  check(bookOptions.indexOf("DAG") < bookOptions.indexOf("HOS") && bookOptions.indexOf("ESG") < bookOptions.indexOf("JOB"),
    "Daniel and Esther sit in their Old Testament places");
  await page.getByRole("combobox", { name: "Canon" }).selectOption("all");

  await page.goto(`${BASE}/read/DAG/3`);
  const dag = await page.locator(".verse-row").evaluateAll((rs) => rs.map((r) => r.id));
  check(dag.length >= 97, `Greek Daniel 3 includes the Prayer of Azariah (${dag.length} verses)`);
  const heb = (id) => page.locator(`[id="${id}"] [lang="hbo"]`).innerText().catch(() => "");
  const grc = (id) => page.locator(`[id="${id}"] [lang="grc"]`).first().innerText().catch(() => "");
  check(!/[\u05D0-\u05EA]/.test(await heb("DAG-3-24")) && /[\u0370-\u03FF\u1F00-\u1FFF]/.test(await grc("DAG-3-24")),
    "Daniel 3:24 (Greek numbering) is Greek-only");
  check(/[\u05D0-\u05EA]/.test(await heb("DAG-3-91")), "Daniel 3:91 lines up with the Hebrew (Standard 3:24)");
  await page.goto(`${BASE}/read/DAG/13`);
  check((await page.locator(".verse-row").count()) === 64, "Daniel 13 is Susanna (64 verses)");

  await page.goto(`${BASE}/read/ESG/1`);
  check((await page.locator(".verse-row").first().getAttribute("id")) === "ESG-1-A1", "Esther opens with Addition A");
  check(!(await page.locator('[id="ESG-1-A1"] [lang="en"]').innerText()).includes("shown with the verse above"),
    "a verse spanning several rows is shown at the first row in reading order");
  await page.goto(`${BASE}/read/ESG/3`);
  const esg = await page.locator(".verse-row").evaluateAll((rs) => rs.map((r) => r.id));
  const at = (id) => esg.indexOf(id);
  check(at("ESG-3-13") >= 0 && at("ESG-3-B1") === at("ESG-3-13") + 1 && at("ESG-3-14") === at("ESG-3-B7") + 1,
    "Addition B sits between Esther 3:13 and 3:14");

  console.log("API");
  const status = async (p) => (await page.request.get(`${BASE}${p}`)).status();
  check((await status("/api/token/abc")) === 400, "bad token id -> 400");
  check((await status("/api/token/999999999")) === 404, "missing token -> 404");

  console.log("Mobile");
  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true });
  watch(mobile);
  await mobile.goto(`${BASE}/read/JHN/1`);
  const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  check(overflow <= 0, `no horizontal scrolling on a phone (${overflow}px)`);

  check(errors.length === 0, `no browser errors${errors.length ? ": " + errors.slice(0, 3).join(" | ") : ""}`);
} catch (e) {
  check(false, `smoke test crashed: ${e.message}`);
} finally {
  await browser.close();
}

console.log(failures ? `\nSMOKE: ${failures} FAILED` : "\nSMOKE: ALL PASSED");
process.exit(failures ? 1 : 0);
