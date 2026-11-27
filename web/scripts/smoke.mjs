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
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
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
/** Count matches once the first one has appeared: content streams in, and client-side state
 *  (such as bookmarks in localStorage) renders after hydration, so counting at once can race. */
async function present(locator, timeout = 10000) {
  await locator.first().waitFor({ timeout }).catch(() => {});
  return locator.count();
}
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
  check((await present(drawer.getByText("Brown-Driver-Briggs"))) > 0, "drawer shows a BDB entry");
  check((await present(drawer.locator('a[href^="/strongs/H"]'))) > 0, "drawer links to the Strong's page");
  check((await drawer.locator("p.text-sm").first().innerText()).length > 10, "parsing is spelled out");
  await page.keyboard.press("Escape");
  check(!(await drawer.isVisible().catch(() => false)), "Escape closes the drawer");

  await page.goto(`${BASE}/read/JHN/1`);
  await page.locator('#JHN-1-1 [lang="grc"] [data-tok]').first().click();
  await drawer.locator("section").first().waitFor({ timeout: 10000 });
  check((await present(drawer.getByText("Thayer"))) > 0, "clicking a Greek NT word shows Thayer's");

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
  // the not-found content streams in after the load event
  const notFound = await page.getByText("could not be found").first().waitFor({ timeout: 10000 }).then(() => true, () => false);
  check(notFound, "unknown book shows not-found page");

  console.log("Search");
  await page.goto(`${BASE}/search?q=beginning`);
  const hits = page.locator("ol li a");
  check((await present(hits)) > 0, `English search returns results (${await hits.count()})`);
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
  check((await present(page.locator('section a[href^="/read/"]'))) > 0, "Strong's number search lists occurrences");

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
  const ogChip = page.getByRole("link", { name: "Old Greek Daniel" });
  check((await present(ogChip)) === 1, "Daniel offers the Old Greek column");
  await ogChip.click();
  await page.waitForURL(/cols=.*LXX-SWETE-OG/);
  await page.locator('[id="DAG-3-1"]').waitFor();
  check((await page.locator('[id="DAG-3-1"] [lang="grc"]').count()) >= 2, "Old Greek shows beside Theodotion");
  await page.goto(`${BASE}/read/GEN/1`);
  check((await page.getByRole("link", { name: "Old Greek Daniel" }).count()) === 0, "other books don't offer it");
  await page.goto(`${BASE}/read/DAG/13`);
  check((await present(page.locator(".verse-row"))) === 64, "Daniel 13 is Susanna (64 verses)");

  await page.goto(`${BASE}/read/ESG/1`);
  check((await page.locator(".verse-row").first().getAttribute("id")) === "ESG-1-A1", "Esther opens with Addition A");
  check(!(await page.locator('[id="ESG-1-A1"] [lang="en"]').innerText()).includes("shown with the verse above"),
    "a verse spanning several rows is shown at the first row in reading order");
  await page.goto(`${BASE}/read/ESG/3`);
  const esg = await page.locator(".verse-row").evaluateAll((rs) => rs.map((r) => r.id));
  const at = (id) => esg.indexOf(id);
  check(at("ESG-3-13") >= 0 && at("ESG-3-B1") === at("ESG-3-13") + 1 && at("ESG-3-14") === at("ESG-3-B7") + 1,
    "Addition B sits between Esther 3:13 and 3:14");

  console.log("Word study");
  await page.goto(`${BASE}/read/GEN/1`);
  await page.getByRole("link", { name: "Glosses" }).click();
  await page.waitForURL(/gloss=1/);
  await page.locator('[id="GEN-1-1"] ruby').first().waitFor();
  check((await page.locator('[id="GEN-1-1"] [lang="hbo"] ruby rt').count()) > 3, "gloss line under Hebrew words");
  check((await page.locator('[id="GEN-1-1"] [lang="grc"] ruby rt.gl-lex').count()) > 3, "Septuagint glosses marked as dictionary glosses");
  // every glossed word stays on one line (no mid-word breaks)
  const split = await page.locator('[id="GEN-1-2"] ruby').evaluateAll((rs) => rs.filter((r) => r.getClientRects().length > 1).length);
  check(split === 0, `glossed words never break across lines (${split} split)`);
  await page.getByRole("link", { name: "Next chapter" }).click();
  await page.waitForURL(/\/read\/GEN\/2\?gloss=1/);
  check(page.url().includes("gloss=1"), "gloss setting survives chapter navigation");
  await page.goto(`${BASE}/read/JHN/1?gloss=1`);
  await page.locator('[id="JHN-1-1"] ruby').first().waitFor();
  check((await page.locator('[id="JHN-1-1"] [lang="grc"] ruby rt:not(.gl-lex)').count()) > 3, "in-context glosses under NT Greek");

  await page.goto(`${BASE}/read/GEN/1`);
  const firstHeb = page.locator('[id="GEN-1-1"] [lang="hbo"] [data-tok]').first();
  const prefixed = await firstHeb.innerText();
  await page.locator('[id="GEN-1-1"] [lang="hbo"] [data-tok]').nth(2).click();
  await drawer.locator("section").first().waitFor({ timeout: 10000 });
  check((await present(drawer.getByText("In the Septuagint usually"))) > 0, "Hebrew word shows its Septuagint equivalents");
  check((await present(drawer.locator('a[href^="/strongs/G"]'))) > 0, "equivalents link to Greek concordance pages");
  await page.keyboard.press("Escape");
  await page.locator('[id="GEN-1-1"] [lang="grc"] [data-tok]').nth(3).click();
  await drawer.locator("section").first().waitFor({ timeout: 10000 });
  const lxxLemma = (await drawer.locator("section span.scripture-grc").first().innerText()).trim();
  check((await present(drawer.getByText("Usually renders (Hebrew)"))) > 0, "Greek word shows its Hebrew equivalents");
  await page.keyboard.press("Escape");

  await page.goto(`${BASE}/search?q=${encodeURIComponent(prefixed)}`);
  check((await present(page.locator('section[aria-label="Dictionary words"] a[href^="/strongs/H"]'))) > 0,
    "searching a prefixed Hebrew word finds its dictionary word");
  await page.goto(`${BASE}/strongs/H0430`);
  check((await present(page.getByText("In the Septuagint usually"))) > 0, "concordance page lists Septuagint equivalents");
  const lemmaPage = await page.request.get(`${BASE}/lemma/${encodeURIComponent(lxxLemma)}`);
  check(lemmaPage.status() === 200 && (await lemmaPage.text()).includes("occurrence"), `lemma concordance page works (${lxxLemma})`);

  console.log("Cross-references");
  await page.goto(`${BASE}/read/GEN/1`);
  const xbtn = page.locator('[id="GEN-1-1"] [data-xref]');
  check((await present(xbtn)) === 1, "verse shows a cross-reference button");
  await xbtn.click();
  await drawer.locator("ol li a").first().waitFor({ timeout: 10000 });
  check((await drawer.locator('ol li a[href^="/read/"]').count()) > 3, "cross-references list linked verses with text");
  await drawer.locator("ol li a").first().click();
  await page.waitForURL(/\/read\/.*#[A-Z0-9]{3}-\d+-\d+$/);
  check(true, "a cross-reference opens its verse");

  console.log("Commentaries");
  await page.goto(`${BASE}/read/GEN/1`);
  await page.locator('[id="GEN-1-1"] [data-commentary]').click();
  const tabs = drawer.getByRole("tab");
  await tabs.first().waitFor({ timeout: 10000 });
  const tabNames = (await tabs.allInnerTexts()).join(" | ");
  check(["Tyndale", "Language notes", "Keil", "Matthew Henry", "Adam Clarke"].every((t) => tabNames.includes(t)),
    `Genesis 1:1 has Tyndale, language notes, Henry, Clarke and Keil & Delitzsch (${tabNames})`);
  check((await present(drawer.locator(".commentary-body p"))) > 0, "commentary text is shown");
  check((await drawer.locator(".commentary-body script, .commentary-body [onclick], .commentary-body iframe").count()) === 0,
    "commentary HTML has no scripts or handlers");
  await drawer.getByRole("tab", { name: /Language notes/ }).click();
  const noteWithWords = drawer.locator("[data-words]").first();
  await noteWithWords.hover();
  check((await present(page.locator('[id="GEN-1-1"] .is-noted'))) > 0, "hovering a language note highlights its Hebrew words");
  const technique = drawer.getByRole("button", { name: /translation technique/ });
  check((await present(technique)) === 1, "translation-technique notes are hidden behind a toggle");
  const before = await drawer.locator("[data-entry]").count();
  await technique.click();
  check((await drawer.locator("[data-entry]").count()) > before, "the toggle shows them");
  await page.goto(`${BASE}/read/MAT/1`);
  await page.locator('[id="MAT-1-2"] [data-commentary]').click();
  await drawer.getByRole("tab", { name: /Catena/ }).click();
  check((await present(drawer.locator(".commentary-body strong"))) > 0, "Matthew 1:2 has the Catena Aurea, naming its Fathers");
  await page.goto(`${BASE}/read/JHN/1`);
  await page.locator('[id="JHN-1-1"] [data-commentary]').click();
  await drawer.getByRole("tab", { name: /^Fathers/ }).click();
  check((await present(drawer.locator("[data-entry]"))) > 3, "John 1:1 has excerpts from the Church Fathers");
  check((await drawer.getByText("John Chrysostom").count()) + (await drawer.getByText("Augustine of Hippo").count()) > 0,
    "each excerpt names its Father");
  await page.goto(`${BASE}/read/GEN/1`);
  await page.locator('[id="GEN-1-1"] [data-tok]').first().click();
  check((await present(drawer.getByText("Language notes on this word"))) === 1, "a word's details include language notes on it");
  await page.goto(`${BASE}/intro/RUT`);
  check((await present(page.getByRole("heading", { name: "Tyndale Open Study Notes" }))) === 1, "Ruth's introduction page shows Tyndale's introduction");
  await page.goto(`${BASE}/about`);
  check((await present(page.locator("#commentaries li"))) >= 4, "Sources page describes the commentaries");

  console.log("Keyboard");
  await page.goto(`${BASE}/read/GEN/1`);
  await page.locator('html[data-keys="ready"]').waitFor({ state: "attached" });
  const currentId = () => page.locator(".verse-row.is-current").first().getAttribute("id");
  await page.keyboard.press("j");
  await page.keyboard.press("j");
  check((await currentId()) === "GEN-1-2", "j moves to the next verse");
  await page.keyboard.press("k");
  check((await currentId()) === "GEN-1-1", "k moves back");
  await page.keyboard.press("b");
  check((await page.locator('[id="GEN-1-1"] button[aria-label^="Bookmark"]').getAttribute("aria-pressed")) === "true",
    "b bookmarks the current verse");
  await page.keyboard.press("e");
  const textarea = page.locator("#note-text");
  await textarea.waitFor();
  await textarea.fill("smoke-test note");
  await page.keyboard.press("Escape");
  check((await present(page.locator('[id="GEN-1-1"]').getByText("smoke-test note"))) === 1, "e writes a note shown under the verse");
  await page.keyboard.press("x");
  await drawer.locator("ol li a").first().waitFor({ timeout: 10000 });
  check(await drawer.isVisible(), "x opens the verse's cross-references");
  await page.keyboard.press("Escape");
  await page.keyboard.press("c");
  check((await present(drawer.getByRole("tab"))) > 0, "c opens the verse's commentary");
  await page.keyboard.press("Escape");
  await page.keyboard.press("?");
  check(await page.getByRole("dialog", { name: "Keyboard shortcuts" }).isVisible(), "? lists the shortcuts");
  await page.keyboard.press("Escape");
  await page.keyboard.press("l");
  await page.waitForURL(/\/read\/GEN\/2/);
  await page.locator('[id="GEN-2-1"]').waitFor();          // chapter streams in after the URL changes
  await page.locator('html[data-keys="ready"]').waitFor({ state: "attached" });
  check(true, "l goes to the next chapter");
  await page.keyboard.press("g");
  await page.waitForURL(/gloss=1/);
  check(true, "g toggles the gloss line");

  console.log("Bookmarks and notes");
  await page.goto(`${BASE}/read/GEN/1`);
  const kept = await page.locator('[id="GEN-1-1"]').getByText("smoke-test note").waitFor({ timeout: 5000 })
    .then(() => true, () => false);
  check(kept, "notes survive a reload");
  await page.goto(`${BASE}/bookmarks`);
  check((await present(page.getByRole("link", { name: "Genesis 1:1" }))) === 1, "bookmarks page lists the verse");
  check((await present(page.getByText("smoke-test note"))) === 1, "bookmarks page shows the note");
  const notesApi = async () => (await page.request.get(`${BASE}/api/annotations`)).json();
  if (process.env.EXPECT_NOTES_FILE) {
    check((await present(page.locator('[data-notes-store="file"]'))) === 1, "bookmarks page says notes are saved in a file");
    const saved = await notesApi();
    check(saved.enabled && Object.values(saved.items ?? {}).some((a) => a.ref === "Genesis 1:1" && a.bookmarked && a.note === "smoke-test note"),
      "the notes file holds the bookmark and note");
    // a new browser profile has empty localStorage: what it shows can only come from the file
    const fresh = await browser.newContext({ viewport: { width: 1400, height: 1000 } });
    const other = await fresh.newPage();
    await other.goto(`${BASE}/bookmarks`);
    check((await present(other.getByText("smoke-test note"))) === 1, "another browser profile sees the same notes");
    await fresh.close();
    // Edits made while the notes are still loading must not be lost (a slow machine hit this):
    // a bookmark during the first load makes the reader merge this browser's copy into the file,
    // and an edit made while that merge is on its way must survive its (older) answer.
    const slow = await browser.newContext({ viewport: { width: 1400, height: 1000 } });
    const early = await slow.newPage();
    await early.goto(`${BASE}/bookmarks`);
    await early.locator('[data-notes-store="file"]').waitFor({ timeout: 10000 });
    await slow.route("**/api/annotations", async (route) => {
      const r = route.request();
      if (r.method() === "GET") await new Promise((res) => setTimeout(res, 1000));
      if (r.method() === "POST" && (r.postData() ?? "").includes('"merge"')) await new Promise((res) => setTimeout(res, 2500));
      await route.continue();
    });
    await early.goto(`${BASE}/read/GEN/1`);
    await early.locator('html[data-keys="ready"]').waitFor({ state: "attached" });
    await early.locator('[id="GEN-1-5"] button[aria-label^="Bookmark"]').click(); // while the file loads
    await early.waitForTimeout(1600);
    await early.locator('[id="GEN-1-6"] button[aria-label^="Bookmark"]').click(); // while the merge is on its way
    await early.waitForTimeout(4000);
    const afterLoad = Object.values((await notesApi()).items ?? {});
    check(["Genesis 1:5", "Genesis 1:6"].every((ref) => afterLoad.some((a) => a.ref === ref && a.bookmarked)),
      "bookmarks made while the notes are still loading are saved");
    check((await early.locator('[id="GEN-1-6"] button[aria-pressed="true"]').count()) === 1,
      "and still show as bookmarked once loading has finished");
    await slow.close();
    const post = (headers, body = "{}") => page.request.post(`${BASE}/api/annotations`, { headers, data: body });
    check((await post({ "content-type": "application/json", origin: "http://evil.example" })).status() === 403,
      "notes API refuses another site's request");
    check((await post({ "content-type": "text/plain" })).status() === 415, "notes API refuses a non-JSON write");
    check((await post({ "content-type": "application/json", host: "evil.example" })).status() === 403,
      "notes API refuses a non-local Host (DNS rebinding)");
  }
  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: "Clear all" }).click();
  check((await present(page.getByText("Nothing here yet"))) === 1, "clear all removes them");
  if (process.env.EXPECT_NOTES_FILE) {
    const cleared = await notesApi();
    check(cleared.enabled && Object.keys(cleared.items ?? { x: 1 }).length === 0, "clear all empties the notes file");
  }

  console.log("API");
  const status = async (p) => (await page.request.get(`${BASE}${p}`)).status();
  check((await status("/api/token/abc")) === 400, "bad token id -> 400");
  check((await status("/api/token/999999999")) === 404, "missing token -> 404");
  check((await status("/api/commentary/abc")) === 400, "bad commentary id -> 400");

  console.log("Mobile");
  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true });
  watch(mobile);
  await mobile.goto(`${BASE}/read/JHN/1`);
  const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  check(overflow <= 0, `no horizontal scrolling on a phone (${overflow}px)`);
  await mobile.locator('[id="JHN-1-1"] [lang="grc"] [data-tok]').first().click();
  const sheet = mobile.locator('aside[role="dialog"]');
  await sheet.locator("section").first().waitFor({ timeout: 10000 });
  const box = await sheet.boundingBox();
  check(!!box && box.width >= 380 && box.y > 844 * 0.2 && Math.abs(box.y + box.height - 844) < 2,
    "on a phone the panel is a bottom sheet");

  check(errors.length === 0, `no browser errors${errors.length ? ": " + errors.slice(0, 3).join(" | ") : ""}`);
} catch (e) {
  check(false, `smoke test crashed: ${e.message}`);
} finally {
  await browser.close();
}

console.log(failures ? `\nSMOKE: ${failures} FAILED` : "\nSMOKE: ALL PASSED");
process.exit(failures ? 1 : 0);
