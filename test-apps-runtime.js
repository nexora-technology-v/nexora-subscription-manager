#!/usr/bin/env node
/**
 * هر سه اپ باید واقعاً بالا بیایند — نه فقط پنل مدیر.
 *
 * چرا این فایل هست: `test-panel-runtime.js` فقط پنل مدیر را اجرا
 * می‌کرد. پنل نماینده و مینی‌اپ هیچ‌وقت در هیچ تستی *اجرا* نمی‌شدند،
 * فقط متنشان خوانده می‌شد.
 *
 * و دقیقاً همان‌جا شکست: در `portal/index.jsx` نوشته شده بود
 *
 *     export { portalSlug } from "../lib/route.js";
 *
 * که نام را فقط *عبور* می‌دهد و وارد دامنه‌ی خودِ ماژول نمی‌کند. کد
 * همان فایل دو جا `portalSlug()` را صدا می‌زند، پس پنل نماینده اصلاً
 * باز نمی‌شد. بیلد سبز بود (نحو درست است)، تست‌های متنی سبز بودند،
 * و هیچ‌کس نفهمید تا وقتی مالک خواست بازش کند.
 *
 * اجرا:  node test-apps-runtime.js
 */

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

function jsdomPath() {
  for (const c of ["jsdom", path.join(__dirname, "frontend", "node_modules", "jsdom"),
                   path.join(__dirname, "node_modules", "jsdom")]) {
    try { return require(c); } catch { /* بعدی */ }
  }
  console.error("jsdom پیدا نشد");
  process.exit(2);
}
const { JSDOM } = jsdomPath();

const DIST = path.join(__dirname, "frontend", "dist-test");
if (!fs.existsSync(path.join(DIST, "index.html"))) {
  console.log("  ساختِ نسخه‌ی تک‌فایلی برای تست…");
  const r = spawnSync("npx", ["vite", "build"], {
    cwd: path.join(__dirname, "frontend"),
    env: { ...process.env, NEXORA_SINGLE_BUNDLE: "1" },
    shell: true, encoding: "utf8",
  });
  if (r.status !== 0) {
    console.error("❌ ساختِ نسخه‌ی تست ناموفق بود");
    console.error((r.stderr || r.stdout || "").slice(-400));
    process.exit(1);
  }
}

const assets = path.join(DIST, "assets");
const jsFile = fs.readdirSync(assets).find((f) => f.endsWith(".js"));
const js = fs.readFileSync(path.join(assets, jsFile), "utf8");
const html = fs.readFileSync(path.join(DIST, "index.html"), "utf8");

const G = "\x1b[38;5;42m", R = "\x1b[38;5;203m", D = "\x1b[38;5;245m", X = "\x1b[0m";
let ok = 0, fail = 0;

const tick = (ms) => new Promise((r) => setTimeout(r, ms));

/** یک اپ را روی یک مسیر بالا می‌آورد و می‌گوید چه رندر شد.
 *
 * async است چون اپ‌ها با `lazy` می‌آیند: بلافاصله بعد از eval هنوز
 * فقط Suspense رندر شده و ریشه خالی است. بدون این صبر، هر سه اپ
 * «صفحه‌ی سفید» گزارش می‌شدند — یعنی تست همیشه قرمز، که از تست
 * همیشه‌سبز هم بی‌فایده‌تر است. */
async function boot(label, pathname, expect) {
  const errors = [];
  const dom = new JSDOM(html.replace(/<script[^>]*src="[^"]*"[^>]*><\/script>/g, ""), {
    url: "https://panel.example.com" + pathname,
    runScripts: "outside-only",
    pretendToBeVisual: true,
  });
  const w = dom.window;

  // تلگرام و شبکه را جعل می‌کنیم: این تست درباره‌ی *بالا آمدن* است،
  // نه درباره‌ی داده
  w.Telegram = { WebApp: {
    initData: "", ready() {}, expand() {}, onEvent() {}, offEvent() {},
    themeParams: {}, colorScheme: "dark",
  } };
  w.fetch = () => new Promise(() => {});          // هیچ‌وقت جواب نمی‌دهد
  w.matchMedia = w.matchMedia || (() => ({ matches: false, addListener() {}, removeListener() {} }));
  w.scrollTo = () => {};
  w.addEventListener("error", (e) => errors.push(String(e.error || e.message)));
  const origErr = w.console.error;
  w.console.error = (...a) => { errors.push(a.map(String).join(" ")); origErr(...a); };

  try {
    w.eval(js);
  } catch (e) {
    errors.push(String(e && e.message ? e.message : e));
  }

  // به تکه‌ی lazy و اولین رندر فرصت بده
  await tick(60);
  await tick(60);

  const root = w.document.getElementById("root");
  const text = (root && root.textContent || "").trim();
  const realErrors = errors.filter((e) =>
    !/not implemented|Not implemented|jsdom|act\(/.test(e));

  const good = text.length > 0 && realErrors.length === 0;
  if (good) {
    ok++;
    console.log(`  ${G}✓${X} ${label} ${D}— ${text.slice(0, 46).replace(/\s+/g, " ")}${X}`);
  } else {
    fail++;
    console.log(`  ${R}✗${X} ${label}`);
    if (realErrors.length) console.log(`      ${D}${realErrors[0].slice(0, 150)}${X}`);
    else console.log(`      ${D}هیچ چیزی رندر نشد — صفحه‌ی سفید${X}`);
  }
  if (expect && good && !text.includes(expect)) {
    fail++;
    console.log(`  ${R}✗${X} ${label}: «${expect}» در خروجی نبود`);
  }
}

console.log("\n" + "═".repeat(52));
console.log("  هر سه اپ باید بالا بیایند");
console.log("═".repeat(52) + "\n");

(async () => {
  await boot("پنل مدیر روی /", "/");
  await boot("پنل نماینده روی /r/<نشانی>", "/r/hossein", "پنل نمایندگی");
  await boot("مینی‌اپ روی /app", "/app");

  console.log("\n" + "─".repeat(52));
  if (fail) {
    console.log(`  ${R}${ok} پاس · ${fail} ناموفق${X}\n`);
    process.exit(1);
  }
  console.log(`  ${G}${ok} پاس — هر سه اپ باز می‌شوند${X}\n`);
})();
