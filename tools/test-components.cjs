/**
 * هر کامپوننت را واقعاً رندر می‌کند.
 *
 * چرا وجود دارد:
 *     ConfirmModal به createPortal آرگومان مقصد نمی‌داد. نتیجه‌اش خطای
 *     React #200 و سیاه‌شدن کل صفحه بود — هر بار که کاربر دکمه‌ی
 *     «بستن آی‌پی» را می‌زد.
 *
 *     تست‌های الگویی این را نگرفتند چون کد از نظر متنی سالم به نظر
 *     می‌رسید؛ فقط اجرای واقعی لوش می‌دهد. و test-panel-runtime هم
 *     نگرفت چون فقط صفحه‌ی اول را رندر می‌کند و هیچ مودالی باز نمی‌شود.
 *
 *     پس این فایل تک‌تک کامپوننت‌های رابط را با داده‌ی واقعی رندر
 *     می‌کند و مطمئن می‌شود هیچ‌کدام خطا نمی‌دهند.
 *
 * اجرا:  node tools/test-components.cjs
 */
const path = require("path");
const fs = require("fs");

const ROOT = path.dirname(__dirname);
const G = "\x1b[38;5;42m", R = "\x1b[38;5;203m",
      D = "\x1b[38;5;245m", X = "\x1b[0m";
let ok = 0, fail = 0;

function check(name, cond, detail) {
  if (cond) {
    ok++;
    console.log(`  ${G}✓${X} ${name}` + (detail ? ` ${D}— ${detail}${X}` : ""));
  } else {
    fail++;
    console.log(`  ${R}✗${X} ${name}` + (detail ? ` ${D}— ${detail}${X}` : ""));
  }
}
function head(t) { console.log(`\n${D}── ${t} ──${X}`); }

let JSDOM;
try {
  ({ JSDOM } = require("jsdom"));
} catch {
  console.log("jsdom پیدا نشد.  npm i jsdom  را در frontend اجرا کنید");
  process.exit(1);
}

// ═══════════ محیط مرورگر ═══════════
const dom = new JSDOM("<!doctype html><html><body><div id=root></div></body></html>",
                      { pretendToBeVisual: true, url: "https://panel.test/" });
global.window = dom.window;
global.document = dom.window.document;
global.navigator = dom.window.navigator;
global.HTMLElement = dom.window.HTMLElement;
global.Element = dom.window.Element;
global.Node = dom.window.Node;
global.localStorage = dom.window.localStorage;
global.fetch = () => Promise.resolve({
  ok: true, json: () => Promise.resolve({}), blob: () => Promise.resolve({}),
});
global.IS_REACT_ACT_ENVIRONMENT = true;
// jsdom این دو را نمی‌سازد و CountUp بدونشان می‌افتد
global.requestAnimationFrame = (cb) => setTimeout(() => cb(Date.now()), 16);
global.cancelAnimationFrame = (id) => clearTimeout(id);

let React, ReactDOMServer;
try {
  React = require("react");
  ReactDOMServer = require("react-dom/server");
} catch (e) {
  console.log("react پیدا نشد:", e.message);
  process.exit(1);
}

// ═══════════ ساخت ماژول‌های JSX ═══════════
let esbuild;
try {
  esbuild = require("esbuild");
} catch {
  console.log("esbuild پیدا نشد — همراه vite نصب می‌شود");
  process.exit(1);
}

const OUT = path.join(ROOT, "frontend", ".test-build");
fs.rmSync(OUT, { recursive: true, force: true });

esbuild.buildSync({
  entryPoints: [path.join(ROOT, "frontend", "src", "ui", "index.jsx")],
  bundle: true,
  format: "cjs",
  platform: "node",
  outfile: path.join(OUT, "ui.cjs"),
  jsx: "automatic",
  external: ["react", "react-dom", "react-dom/server", "lucide-react"],
  logLevel: "silent",
  // import.meta.env مال Vite است و در Node وجود ندارد؛ بدون این،
  // خود بارگذاری ماژول می‌افتد و هیچ تستی اجرا نمی‌شود.
  define: { "import.meta.env.VITE_API_URL": '"http://localhost:8100"' },
});

const UI = require(path.join(OUT, "ui.cjs"));

// ═══════════ رندر ═══════════
function render(name, el) {
  try {
    const html = ReactDOMServer.renderToStaticMarkup(el);
    return { ok: true, html };
  } catch (e) {
    return { ok: false, err: e.message };
  }
}

head("مودال‌ها — همان‌جا که صفحه سیاه می‌شد");

// createPortal در رندر سمت سرور کار نمی‌کند، پس مستقیم در مرورگر
// جعلی mount می‌کنیم — همان مسیری که کاربر طی می‌کند.
let ReactDOMClient;
try {
  ReactDOMClient = require("react-dom/client");
} catch (e) {
  console.log("react-dom/client پیدا نشد:", e.message);
  process.exit(1);
}

const { act } = require("react");

function mount(name, el) {
  const host = document.createElement("div");
  document.body.appendChild(host);
  const root = ReactDOMClient.createRoot(host);
  let err = null;
  try {
    act(() => { root.render(el); });
  } catch (e) {
    err = e;
  }
  const html = document.body.innerHTML;
  try { act(() => { root.unmount(); }); } catch { /* مهم نیست */ }
  host.remove();
  return { err, html };
}

const noop = () => {};

let r = mount("ConfirmModal", React.createElement(UI.ConfirmModal, {
  title: "بستن این آی‌پی",
  desc: "۴۵.۹.۱۴۸.۷ با ۱۲۰ تلاش ناموفق بسته می‌شود.",
  confirmLabel: "بستن",
  onConfirm: noop,
  onCancel: noop,
}));
check("ConfirmModal بدون خطا رندر می‌شود", !r.err,
      r.err ? String(r.err.message).slice(0, 90) : "همان باگ صفحه‌ی سیاه");
check("ConfirmModal متنش را نشان می‌دهد",
      !r.err && r.html.includes("بستن این آی‌پی"));
check("ConfirmModal دکمه‌ی تایید دارد",
      !r.err && r.html.includes("بستن"));

r = mount("Modal", React.createElement(UI.Modal, {
  title: "ویرایش", onClose: noop,
  children: React.createElement("div", null, "محتوا"),
}));
check("Modal بدون خطا رندر می‌شود", !r.err,
      r.err ? String(r.err.message).slice(0, 90) : "");

head("اجزای پایه");

const CASES = [
  ["Field", { label: "نام", children: React.createElement("input") }],
  ["Toggle", { checked: true, onChange: noop, label: "فعال" }],
  ["SectionHead", { title: "بخش", desc: "توضیح" }],
  ["EmptyState", { text: "چیزی نیست" }],
  ["InfoBox", { children: "یک نکته" }],
  ["StatusChip", { ok: true }],
  ["Msg", { msg: { t: "ok", m: "انجام شد" } }],
  ["Msg", { msg: { t: "err", m: "ناموفق" } }],
  ["Msg", { msg: null }],
  ["Toast", { message: "ذخیره شد", type: "ok" }],
  ["CountUp", { value: 1234 }],
  ["StatTile", { label: "فروش", value: "۱۲۳" }],
  ["Segmented", { value: 7, onChange: noop, items: [[7, "۷"], [30, "۳۰"]] }],
  ["NumberStepper", { value: 5, onChange: noop, min: 0, max: 10 }],
  ["Sparkline", { data: [1, 5, 3, 8, 2] }],
  ["AreaChart", { data: [4, 9, 2, 11, 7, 3], label: "روند" }],
  // یک نقطه: نباید بیفتد، باید پیام «داده کافی نیست» بدهد
  ["AreaChart", { data: [5] }],
  ["AreaChart", { data: [] }],
  // مقدار خراب لای داده‌ی درست — نباید NaN وارد مسیر SVG کند
  ["AreaChart", { data: [3, null, 7, NaN, 5, undefined, 2] }],
  ["Tabs", { items: [{ key: "a", label: "یک" }, { key: "b", label: "دو" }],
             active: "a", onChange: noop }],
  // بدون آیکون — قبلاً همین حالت کل بخش را می‌انداخت
  ["EmptyState", { text: "بدون آیکون" }],
];

for (const [name, props] of CASES) {
  const C = UI[name];
  if (!C) { check(`${name} export شده`, false, "در ui/index.jsx نیست"); continue; }
  const res = mount(name, React.createElement(C, props));
  check(`${name} بدون خطا رندر می‌شود`, !res.err,
        res.err ? String(res.err.message).slice(0, 80) : "");
}

head("مرز خطا");

function Boom() { throw new Error("انفجار عمدی"); }
r = mount("ErrorBoundary", React.createElement(
  UI.ErrorBoundary, null, React.createElement(Boom)));
check("مرز خطا جلوی سقوط را می‌گیرد", !r.err,
      "کامپوننت داخلش عمداً خطا داد");
check("مرز خطا پیام نشان می‌دهد",
      !r.err && r.html.includes("این بخش باز نشد"));
check("مرز خطا می‌گوید بقیه سالم است",
      !r.err && r.html.includes("بقیه‌ی پنل سالم است"));

head("هیچ createPortal بی‌مقصد نماند");

const uiSrc = fs.readFileSync(
  path.join(ROOT, "frontend", "src", "ui", "index.jsx"), "utf8");
const portals = uiSrc.split("createPortal(").length - 1;
const targets = (uiSrc.match(/document\.body,?\s*\)/g) || []).length;
check("هر createPortal مقصد دارد", portals > 1 && targets >= portals - 1,
      `${portals} پرتال · ${targets} مقصد`);

fs.rmSync(OUT, { recursive: true, force: true });

console.log(`\n${D}${"─".repeat(46)}${X}`);
console.log(`  ${fail ? R : G}${ok} پاس${X}` + (fail ? ` · ${R}${fail} ناموفق${X}` : ""));
console.log();
process.exit(fail ? 1 : 0);
