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

/** تازه‌ترین زمانِ تغییر در یک درخت. */
function newest(dir) {
  let t = 0;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    t = Math.max(t, e.isDirectory() ? newest(p) : fs.statSync(p).mtimeMs);
  }
  return t;
}

/*
 * کهنه بودن هم یعنی «باید دوباره ساخته شود».
 *
 * یک‌بار این تست در دروازه قرمز شد و در اجرای دستی سبز: `dist-test`
 * از قبل وجود داشت ولی کدِ تازه در آن نبود، پس تست کدِ قدیمی را
 * می‌سنجید. تستی که به یک فایلِ کهنه تکیه کند، هم دروغِ سبز می‌دهد
 * هم دروغِ قرمز.
 */
let stale = false;
try {
  stale = fs.existsSync(path.join(DIST, "index.html"))
    && newest(path.join(__dirname, "frontend", "src"))
       > fs.statSync(path.join(DIST, "index.html")).mtimeMs;
} catch { /* اگر نشد، بیلد می‌کنیم */ stale = true; }

if (stale || !fs.existsSync(path.join(DIST, "index.html"))) {
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
  // صفحه‌ی ورودِ نکسورا یک کفِ زمانیِ ۱٫۹ ثانیه‌ای دارد که با
  // `prefers-reduced-motion` برداشته می‌شود. این‌جا آن را روشن
  // می‌کنیم تا خودِ اپ رندر شود.
  //
  // چرا لازم شد: بدونش، `boot` متنِ *صفحه‌ی ورود* را می‌دید و چون
  // برچسبش «پنل نمایندگی» است، انتظارِ تست هم اتفاقی برآورده
  // می‌شد — یعنی سبز، بدون اینکه اپ اصلاً بالا آمده باشد.
  w.matchMedia = (q) => ({
    matches: /prefers-reduced-motion/.test(String(q || "")),
    addListener() {}, removeListener() {},
    addEventListener() {}, removeEventListener() {},
  });
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


/**
 * هر صفحه‌ی پنل باید *چیزی* رندر کند.
 *
 * چرا: پنل ۴۷ صفحه دارد و هیچ‌کدامشان جز داشبورد در هیچ تستی باز
 * نمی‌شدند. یک import جاافتاده یا یک پراپِ عوض‌شده، همان یک صفحه را
 * سفید می‌کند و تا وقتی کسی رویش کلیک نکند معلوم نمی‌شود — دقیقاً
 * همان شکلی که پنل نماینده یک‌بار کاملاً از کار افتاد.
 *
 * این‌جا قضاوتِ ظاهری نمی‌شود (jsdom چیدمان ندارد). فقط: باز شد؟
 * متنی تولید کرد؟ خطایی داد؟
 */
async function everyPage() {
  const errors = [];
  const dom = new JSDOM(html.replace(/<script[^>]*src="[^"]*"[^>]*><\/script>/g, ""), {
    url: "https://panel.example.com/", runScripts: "outside-only", pretendToBeVisual: true,
  });
  const w = dom.window;
  w.localStorage.setItem("nexora_subpage_admin_pw", "t");
  w.matchMedia = (q) => ({
    matches: /prefers-reduced-motion/.test(String(q || "")),
    addListener() {}, removeListener() {},
    addEventListener() {}, removeEventListener() {},
  });
  w.scrollTo = () => {};
  w.fetch = () => Promise.resolve({
    ok: true, status: 200,
    json: () => Promise.resolve({ ready: true, groups: [], orders: [], users: [],
                                  plans: [], daily: [], buyers: [], downloadApps: {},
                                  faq: {}, videos: [], resellers: [], links: {},
                                  advanced: {}, banners: {}, referral: {} }),
    text: () => Promise.resolve(""),
  });
  w.console.error = (...a) => { errors.push(a.map(String).join(" ")); };
  try { w.eval(js); } catch (e) { errors.push(String(e && e.message || e)); }
  await tick(150); await tick(150);

  const d = w.document;
  const WS = ["صفحه اشتراک", "حسابداری", "تانل", "نمایندگی", "فایروال", "ربات تلگرام"];
  // سرِ هر فضای کاری، تازه از DOM — بعد از هر رندر عوض می‌شوند
  const heads = () => [...d.querySelectorAll(".fx-side button")]
    .filter((b) => WS.some((t) => (b.textContent || "").trim().startsWith(t)));

  // آکاردئون *کلید* است: کلیک دوم می‌بنددش.
  //
  // نسخه‌ی اول همه‌ی سرها را یک‌بار می‌زد و بعد دوباره — یعنی
  // می‌بستشان — و بعد دنبال آیتم می‌گشت و پیدا نمی‌کرد. نتیجه:
  // هیچ صفحه‌ای باز نمی‌شد و تست *سبز* بود، چون فهرستِ خرابی‌ها
  // خالی می‌ماند. دقیقاً همان دروازه‌ای که به اتاق خالی نگاه می‌کند.
  async function openKey(k) {
    let btn = d.querySelector(`[data-navkey="${k}"]`);
    if (btn) { btn.click(); await tick(100); return true; }
    for (const h of heads()) {
      h.click(); await tick(50);
      btn = d.querySelector(`[data-navkey="${k}"]`);
      if (btn) { btn.click(); await tick(100); return true; }
      h.click(); await tick(20);          // بستن و رفتن سراغ بعدی
    }
    return false;
  }

  // همه‌ی کلیدها: هر فضای کاری را باز می‌کنیم و می‌بندیم
  const keys = new Set();
  for (const h of heads()) {
    h.click(); await tick(50);
    d.querySelectorAll("[data-navkey]").forEach((e) => keys.add(e.dataset.navkey));
    h.click(); await tick(20);
  }

  const broken = [];
  let opened = 0;
  for (const k of keys) {
    const before = errors.length;
    if (!(await openKey(k))) { broken.push(k + " (در منو پیدا نشد)"); continue; }
    opened++;
    const main = d.querySelector(".fx-main");
    const txt = ((main && main.textContent) || "").trim();
    const fresh = errors.slice(before).filter((e) =>
      !/not implemented|Not implemented|jsdom|act\(|Warning:/.test(e));
    // مرزِ خطا صفحه را سفید نمی‌کند — پیامِ خودش را نشان می‌دهد،
    // پس «خالی نبودن» کافی نیست
    const crashed = txt.includes("بقیه‌ی پنل سالم است") || txt.includes("دوباره تلاش");
    if (txt.length < 12 || fresh.length || crashed) {
      broken.push(k + (crashed ? " (کرش کرد)"
                     : fresh.length ? " (" + fresh[0].slice(0, 60) + ")" : " (خالی)"));
    }
  }

  // نگهبانِ خودِ تست: اگر ناگهان هیچ صفحه‌ای باز نشد، یعنی این تست
  // کور شده، نه اینکه پنل سالم است
  if (opened < 30) {
    fail++;
    console.log(`  ${R}✗${X} فقط ${opened} صفحه باز شد — این تست کور شده، نه پنل سالم`);
    return;
  }
  if (broken.length) {
    fail++;
    console.log(`  ${R}✗${X} ${broken.length} صفحه از ${keys.size} مشکل دارد`);
    broken.slice(0, 8).forEach((b) => console.log(`      ${D}▸ ${b}${X}`));
  } else {
    ok++;
    console.log(`  ${G}✓${X} هر ${opened} صفحه‌ی پنل باز می‌شود ${D}— بدون خطا، با محتوا${X}`);
  }
}


(async () => {
  // «NEXORA» در صفحه‌ی ورود هم هست؛ «رمز عبور» فقط در خودِ اپ.
  await boot("پنل مدیر روی /", "/", "رمز عبور");
  await boot("پنل نماینده روی /r/<نشانی>", "/r/hossein", "نشانی:");
  await boot("مینی‌اپ روی /app", "/app", "اشتراک‌ها");
  await everyPage();

  console.log("\n" + "─".repeat(52));
  if (fail) {
    console.log(`  ${R}${ok} پاس · ${fail} ناموفق${X}\n`);
    process.exit(1);
  }
  console.log(`  ${G}${ok} پاس — هر سه اپ باز می‌شوند${X}\n`);
})();
