/**
 * خطای خواندن باید دیده شود — نه «خالی است».
 *
 * چرا وجود دارد:
 *     بیست‌وشش جای پنل `fetch(...).then((r) => r.json())` داشتند و وضعیت
 *     را نمی‌سنجیدند، و چند جا خطا را کلاً می‌بلعیدند. نتیجه هر بار یک
 *     دروغِ آرام بود:
 *       - فایروال «ufw نصب نیست» می‌گفت و دستورِ نصب می‌داد، روی سروری
 *         که ufw داشت؛
 *       - کارتِ بازگردانی «هنوز نسخه‌ای نیست» می‌گفت؛
 *       - آی‌پی‌های بسته‌شده «۰» می‌گفت؛
 *       - فرمِ نگهداری با مقدارهای خالی باز می‌شد و «ذخیره» `{error: true}`
 *         را روی سرور می‌نوشت؛
 *       - کانفیگِ سرورِ خارج خالی بود و دکمه‌ی کپی داشت.
 *
 *     `test-ui-safety` شکلِ متنیِ این اشتباه را رد می‌کند. این فایل رفتار
 *     را می‌سنجد: هر صفحه را با پاسخِ ۵۰۰ برای مسیرِ خودش واقعاً mount
 *     می‌کند و می‌بیند دلیلِ سرور روی صفحه آمده یا نه.
 *
 * اجرا:  NODE_PATH=frontend/node_modules node tools/test-load-errors.cjs
 */
const path = require("path");
const fs = require("fs");

const ROOT = path.dirname(__dirname);
const G = "\x1b[38;5;42m", R = "\x1b[38;5;203m", D = "\x1b[38;5;245m", X = "\x1b[0m";
let ok = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) ok++; else fail++;
  console.log(`  ${cond ? G + "✓" : R + "✗"}${X} ${name}` + (detail ? ` ${D}— ${detail}${X}` : ""));
}

let JSDOM, esbuild;
try { ({ JSDOM } = require("jsdom")); } catch {
  console.log("jsdom پیدا نشد.  npm i jsdom  را در frontend اجرا کنید"); process.exit(1);
}
try { esbuild = require("esbuild"); } catch {
  console.log("esbuild پیدا نشد — همراه vite نصب می‌شود"); process.exit(1);
}

// ═══════════ محیط مرورگر ═══════════
const dom = new JSDOM("<!doctype html><html><body></body></html>",
                      { pretendToBeVisual: true, url: "https://panel.test/" });
for (const k of ["window", "document", "navigator", "HTMLElement", "Element", "Node", "localStorage"]) {
  global[k] = k === "window" ? dom.window : dom.window[k];
}
global.IS_REACT_ACT_ENVIRONMENT = true;
global.requestAnimationFrame = (cb) => setTimeout(() => cb(Date.now()), 16);
global.cancelAnimationFrame = (id) => clearTimeout(id);
dom.window.matchMedia = global.matchMedia = () => ({
  matches: false, addListener() {}, removeListener() {},
  addEventListener() {}, removeEventListener() {},
});

//: مسیری که باید بشکند؛ بقیه یک شیءِ خالیِ موفق می‌گیرند
let failRe = null, tag = "";
global.fetch = (url, opts) => {
  const u = String(url).split("?")[0];
  const get = !opts || !opts.method || opts.method === "GET";
  const bad = failRe && get && failRe.test(u);
  const body = bad ? { detail: tag } : {};
  return Promise.resolve({
    ok: !bad, status: bad ? 500 : 200,
    json: () => Promise.resolve(body),
    blob: () => Promise.resolve({}),
    headers: { get: () => null },
  });
};

// ═══════════ ساخت ═══════════
const OUT = path.join(ROOT, "frontend", ".test-build");
fs.mkdirSync(OUT, { recursive: true });
const S = (f) => JSON.stringify(path.join(ROOT, "frontend", "src", "sections", f).split(path.sep).join("/"));
const entry = path.join(OUT, "load-errors-entry.jsx");
fs.writeFileSync(entry, [
  `export { BotStatsSection, BotReportSection } from ${S("bot/stats.jsx")};`,
  `export { ThemesSection } from ${S("bot/themes.jsx")};`,
  `export { BotAffiliates } from ${S("bot/affiliates.jsx")};`,
  `export { RollbackCard, UpdateCard, SystemSection } from ${S("system.jsx")};`,
  `export { UsageHistoryCard, TopClientsCard, MaintenanceCard } from ${S("monitoring.jsx")};`,
  `export { NodesMonitor } from ${S("nodes-monitor.jsx")};`,
  `export { TunnelOverview, NodeDiagnoseModal, TunnelMonitorModal, TunnelConfigModal } from ${S("tunnel.jsx")};`,
  `export { FirewallRules, FirewallBlocked } from ${S("firewall.jsx")};`,
  `export { BillingExpenses, BillingLedger } from ${S("expenses.jsx")};`,
  `export { BotOrdersSection } from ${S("bot/orders.jsx")};`,
  `export { BotUsersSection } from ${S("bot/users.jsx")};`,
  `export { BotPlansSection } from ${S("bot/plans.jsx")};`,
  `export { BotEventsSection } from ${S("bot/events.jsx")};`,
  `export { BotInboxSection } from ${S("bot/inbox.jsx")};`,
  `export { BotDiscountsSection } from ${S("bot/discounts.jsx")};`,
  `export { BotCoinsSection } from ${S("bot/coins.jsx")};`,
  `export { BotTextsSection } from ${S("bot/texts.jsx")};`,
  `export { BotSection } from ${S("bot/connection.jsx")};`,
  `export { ChannelSection } from ${S("channel.jsx")};`,
  `export { FirewallIntrusion } from ${S("intrusion.jsx")};`,
  `export { PortalAdmin, PortalAddon, ResellerInbounds } from ${S("portal-admin.jsx")};`,
  `export { BillingClients, BillingPayments, BillingDash, BillingSettings, BillingInvoice, BillingPeriod, BillingGroups } from ${S("billing.jsx")};`,
].join("\n"));
esbuild.buildSync({
  entryPoints: [entry], bundle: true, format: "cjs", platform: "node",
  outfile: path.join(OUT, "load-errors.cjs"), jsx: "automatic",
  external: ["react", "react-dom", "react-dom/client", "react-dom/server", "lucide-react"],
  logLevel: "silent",
  define: { "import.meta.env.VITE_API_URL": '"http://localhost:8100"' },
  loader: { ".js": "jsx" },
});
const React = require("react");
const { act } = React;
const ReactDOMClient = require("react-dom/client");
const C = require(path.join(OUT, "load-errors.cjs"));

const tick = () => act(async () => { await new Promise((r) => setTimeout(r, 30)); });

async function mountFailing(Comp, props, route, i) {
  failRe = new RegExp(route);
  tag = `FAKE-500-${i}`;
  const host = document.createElement("div");
  document.body.appendChild(host);
  const root = ReactDOMClient.createRoot(host);
  let err = null;
  const origErr = console.error;
  console.error = () => {};
  try {
    await act(async () => { root.render(React.createElement(Comp, props)); });
    for (let k = 0; k < 6; k++) await tick();
  } catch (e) { err = e; }
  const text = document.body.textContent || "";
  try { await act(async () => { root.unmount(); }); } catch { /* مهم نیست */ }
  console.error = origErr;
  host.remove();
  document.body.innerHTML = "";
  return { err, shown: text.includes(tag) };
}

const pw = { password: "x" };
const noop = () => {};
const tunnel = { id: 1, name: "t1" };
const CASES = [
  ["قیفِ تبدیل", C.BotStatsSection, pw, "/bot/funnel$"],
  ["گزارشِ فروش", C.BotReportSection, pw, "/bot/users/report$"],
  ["قالب‌ها", C.ThemesSection, { ...pw, config: {}, setConfig: noop }, "/api/admin/themes$"],
  ["همکاری در فروش", C.BotAffiliates, pw, "/bot/affiliates$"],
  ["بازگردانی — نه «نسخه‌ای نیست»", C.RollbackCard, pw, "/api/admin/snapshots$"],
  ["بررسیِ نسخه — نه «تنظیم نشده»", C.UpdateCard, pw, "/api/admin/check-update$"],
  ["وضعیتِ سیستم", C.SystemSection, pw, "/api/admin/system$"],
  ["تاریخچه‌ی مصرف", C.UsageHistoryCard, pw, "/api/admin/usage-history$"],
  ["پرمصرف‌ترین مشتری‌ها", C.TopClientsCard, pw, "/api/admin/top-clients$"],
  ["نگهداری — نه فرمِ خالی", C.MaintenanceCard, pw, "/api/admin/maintenance$"],
  ["سرورهای دیگر — نه «سروری نیست»", C.NodesMonitor, pw, "/api/admin/tunnel/overview$"],
  ["داشبوردِ تانل", C.TunnelOverview, pw, "/api/admin/tunnel/overview$"],
  ["چرا نود آفلاین است", C.NodeDiagnoseModal, { ...pw, nodeId: 1, onClose: noop }, "/tunnel/node/1/check$"],
  ["کیفیتِ تانل", C.TunnelMonitorModal, { ...pw, tunnel, onClose: noop }, "/tunnel/1/metrics$"],
  ["کانفیگِ خارج — نه جعبه‌ی خالی با دکمه‌ی کپی", C.TunnelConfigModal, { ...pw, tunnel, onClose: noop }, "/tunnel/1/config$"],
  ["واسطه‌ها و نرخ", C.BillingGroups, pw, "/billing/groups$"],
  ["قواعدِ فایروال — نه «ufw نصب نیست»", C.FirewallRules, pw, "/api/admin/firewall$"],
  ["آی‌پی‌های بسته‌شده — نه «۰»", C.FirewallBlocked, pw, "/api/admin/firewall/blocked$"],
  ["نرخِ ارز در هزینه‌ها", C.BillingExpenses, pw, "/billing/fx$"],
  ["فهرستِ هزینه‌ها", C.BillingExpenses, pw, "/billing/expenses$"],
  ["دفترِ کل", C.BillingLedger, pw, "/billing/ledger$"],
  ["همه‌ی کاربرانِ حسابداری", C.BillingClients, pw, "/billing/clients$"],
  ["پرداخت‌ها", C.BillingPayments, pw, "/billing/payments$"],
  ["داشبوردِ حسابداری", C.BillingDash, pw, "/billing/groups$"],
  ["تنظیماتِ حسابداری", C.BillingSettings, pw, "/billing/xui-path$"],
  ["صورتحساب — فهرستِ واسطه‌ها", C.BillingInvoice, pw, "/billing/groups$"],
  ["صورتحسابِ دوره — فهرستِ واسطه‌ها", C.BillingPeriod, pw, "/billing/groups$"],
  ["سفارش‌های ربات", C.BotOrdersSection, pw, "/bot/orders$"],
  ["کاربرانِ ربات", C.BotUsersSection, pw, "/bot/users$"],
  ["پلن‌های ربات", C.BotPlansSection, pw, "/bot/plans$"],
  ["رویدادهای ربات", C.BotEventsSection, pw, "/bot/events$"],
  ["پیام‌ها", C.BotInboxSection, pw, "/bot/inbox$"],
  ["کدهای تخفیف", C.BotDiscountsSection, pw, "/bot/discounts$"],
  ["سکه و دعوت", C.BotCoinsSection, pw, "/bot/settings$"],
  ["متن‌ها و یادآوری‌ها", C.BotTextsSection, pw, "/bot/settings$"],
  ["اتصال و تنظیماتِ ربات", C.BotSection, pw, "/bot/status$"],
  ["کانال", C.ChannelSection, pw, "/api/admin/channel$"],
  ["تلاش برای نفوذ", C.FirewallIntrusion, pw, "/firewall/intrusion$"],
  ["نماینده‌ها و دسترسی", C.PortalAdmin, pw, "/tenant/portal-list$"],
  ["اینباندِ نماینده‌ها", C.ResellerInbounds, pw, "/tenant/portal-list$"],
  ["افزونه‌ی پرتال", C.PortalAddon, pw, "/api/admin/portal-addon$"],
  // خواندنِ تنظیماتِ ربات که شکست بخورد، ذخیره‌ی بعدی (PUTِ جایگزین‌کننده)
  // همه‌چیز را پاک می‌کرد — خطا باید دیده شود، نه فرمی با پیش‌فرض‌ها
  ["پیگیریِ تست — نه فرمِ پیش‌فرض", C.BotDiscountsSection, pw, "/bot/settings$"],
  ["پاسخ‌های آماده — نه ذخیره‌ی خالی", C.BotInboxSection, pw, "/bot/settings$"],
  ["آدرسِ کانال — نه ذخیره‌ی خالی", C.ChannelSection, pw, "/bot/settings$"],
];

(async () => {
  console.log(`\n${D}── خطای خواندن روی صفحه دیده می‌شود (${CASES.length} صفحه) ──${X}`);
  for (let i = 0; i < CASES.length; i++) {
    const [name, Comp, props, route] = CASES[i];
    if (typeof Comp !== "function") { check(name, false, "کامپوننت export نشده"); continue; }
    const r = await mountFailing(Comp, props, route, i);
    check(name, !r.err && r.shown,
          r.err ? `کرش: ${String(r.err.message).slice(0, 80)}` : r.shown ? "" : `دلیلِ سرور روی صفحه نیامد (${route})`);
  }
  // نشانه‌ی اینکه آزمون کور نیست: بدونِ شکستن، همان برچسب نباید دیده شود
  const blind = await mountFailing(C.FirewallBlocked, pw, "^$never", 999);
  check("آزمون کور نیست — بدونِ خطا، برچسب دیده نمی‌شود", !blind.shown);

  // پوشه‌ی ساخت در .gitignore نیست؛ اگر بماند، release-check درختِ کثیف می‌بیند
  fs.rmSync(entry, { force: true });
  fs.rmSync(path.join(OUT, "load-errors.cjs"), { force: true });
  try { fs.rmdirSync(OUT); } catch { /* test-components هم از همین پوشه استفاده می‌کند */ }
  console.log(`\n  ${fail ? R : G}${ok} پاس · ${fail} ناموفق${X}\n`);
  process.exit(fail ? 1 : 0);
})();
