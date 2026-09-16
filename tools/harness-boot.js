/**
 * داده‌ی ساختگی برای *نگاه‌کردن* به پنل.
 *
 * چرا لازم شد: تا امروز تنها راهِ دیدنِ پنل، بالاآوردنِ بکند و
 * دیتابیس و ربات بود. یعنی عملاً هیچ‌وقت به آن نگاه نمی‌شد و
 * ایرادهای چیدمانی — کارتی که سه خط می‌شود، افسانه‌ای که زیر
 * نمودار می‌افتد، نوار بالایی که با اسکرول می‌رود — فقط وقتی پیدا
 * می‌شدند که مالک بازش می‌کرد.
 *
 * این فایل `fetch` را می‌دزدد و به هر مسیر `/api/…` یک پاسخِ
 * واقع‌نما می‌دهد. هیچ‌جا سرو نمی‌شود؛ فقط `tools/make-harness.js`
 * آن را داخل `dist-test/harness.html` می‌گذارد.
 */
(function () {
  try {
    localStorage.setItem("nexora_subpage_admin_pw", "harness");
    localStorage.setItem("nexora_workspace", "sub");
  } catch (e) { /* بی‌صدا */ }

  var CONFIG = {
    brandName: "NEXORA",
    links: { channelUsername: "nexora_vpn", supportUsername: "nexora_sup" },
    downloadApps: {
      android: [{ name: "Happ", scheme: "happ", recommended: true },
                { name: "v2rayNG", scheme: "v2rayng" },
                { name: "NekoBox", scheme: "none" }],
      ios: [{ name: "Streisand", scheme: "none", recommended: true },
            { name: "V2Box", scheme: "v2box" }],
      desktop: [{ name: "Nekoray", scheme: "none" }, { name: "v2rayN", scheme: "none" }],
    },
    faq: {
      fa: [{ q: "چطور وصل شوم؟", a: "اپ را نصب کنید و لینک را وارد کنید." },
           { q: "حجمم تمام شد", a: "از ربات تمدید کنید." },
           { q: "روی چند دستگاه؟", a: "بسته به پلن شما." }],
      en: [{ q: "How do I connect?", a: "Install the app." }], tr: [], ar: [],
    },
    videos: [{ title: "نصب روی اندروید", url: "https://example.com/1" },
             { title: "نصب روی آیفون", url: "https://example.com/2" }],
    resellers: [{ name: "حسین", slug: "hossein", enabled: true },
                { name: "مهدی", slug: "mehdi", enabled: true },
                { name: "سارا", slug: "sara", enabled: false }],
    banners: { enabled: true }, referral: { enabled: false },
    advanced: { showFaqSection: true, showNotificationPopup: true, showBrandStrip: true },
    popup: {}, themes: {},
  };

  var REPORT = {
    ready: true, days: 30,
    users: { users: 1284, newUsers: 96, blocked: 4, withPhone: 812 },
    orders: { approved: 61, rejected: 3, pending: 5, revenue: 18400000, avg: 301639 },
    subs: { total: 412, active: 355, expiringSoon: 18 },
    buyers: [
      { tg_id: 11, first_name: "مریم کاظمی", orders: 4, spent: 1240000 },
      { tg_id: 12, first_name: "حسین نوری", orders: 3, spent: 940000 },
      { tg_id: 13, first_name: "سارا احمدی", orders: 2, spent: 610000 },
      { tg_id: 14, first_name: "امیر صادقی", orders: 2, spent: 480000 },
      { tg_id: 15, first_name: "رضا جعفری", orders: 1, spent: 320000 },
    ],
    buyerCount: 24, conversion: 25,
    daily: (function () {
      var a = [], i;
      for (i = 0; i < 30; i++) {
        a.push({ day: "2026-08-" + (i + 1),
                 n: 2 + Math.round(Math.sin(i / 4) * 2 + (i % 3)),
                 sum: 260000 + Math.round(Math.sin(i / 3.5) * 130000) + i * 13000 });
      }
      return a;
    })(),
  };

  var BILLING = {
    ready: true, totalClients: 412, periodStart: "1404-06-01",
    groups: [
      { name: "goroh-a", label: "حسین", billed: true, configs: 96, months: 104,
        amount: 12400000, paid: 9000000, uncertain: 2, unpriced: [], unpricedWhy: {},
        skipped: 3, skippedWhy: { "هرگز روشن نشد": 3 } },
      { name: "goroh-b", label: "مهدی", billed: true, configs: 61, months: 66,
        amount: 7900000, paid: 7900000, uncertain: 0, unpriced: [], unpricedWhy: {}, skipped: 0 },
      { name: "goroh-c", label: "سارا", billed: true, configs: 34, months: 35,
        amount: 4000000, paid: 1200000, uncertain: 1, unpriced: [200],
        unpricedWhy: { "نرخ ۲۰۰ گیگ تعریف نشده": 4 }, skipped: 1, skippedWhy: {} },
      { name: "بدون گروه", label: "بدون گروه", billed: false, configs: 12, months: 12,
        amount: 0, paid: 0, uncertain: 0, unpriced: [], unpricedWhy: {}, skipped: 0 },
    ],
    needStart: [],
  };

  var mk = function (n, f) { var a = [], i; for (i = 0; i < n; i++) a.push(f(i)); return a; };
  var NAMES = ["علی رضایی", "مریم کاظمی", "حسین نوری", "زهرا مرادی", "امیر صادقی",
               "سارا احمدی", "رضا جعفری"];

  var ORDERS = { ready: true, total: 12, orders: mk(12, function (i) {
    return { id: 900 + i, user_id: i + 1, name: NAMES[i % 7], tg_id: 5000 + i,
             plan: ["یک‌ماهه", "سه‌ماهه", "شش‌ماهه"][i % 3],
             amount: [120000, 280000, 480000][i % 3],
             status: ["approved", "pending", "rejected"][i % 3],
             paid_from: i % 2 ? "card" : "wallet",
             created_at: "2026-09-0" + ((i % 9) + 1) + " 12:30" };
  }) };

  var USERS = { ready: true, total: 1284, users: mk(14, function (i) {
    return { id: i + 1, tg_id: 6000 + i, first_name: NAMES[i % 7],
             username: "user" + i, phone: "0912000" + (1000 + i),
             balance: (i % 5) * 50000, coins: i * 3, is_blocked: i === 3 ? 1 : 0,
             created_at: "2026-08-0" + ((i % 9) + 1), subs: i % 4, spent: i * 90000 };
  }) };

  var PLANS = { ready: true, plans: mk(4, function (i) {
    return { id: i + 1, name: ["تست رایگان", "یک‌ماهه", "سه‌ماهه", "شش‌ماهه"][i],
             gb: [5, 50, 100, 200][i], days: [1, 30, 90, 180][i],
             price: [0, 120000, 280000, 480000][i], devices: [1, 1, 2, 3][i],
             is_active: 1, is_trial: i === 0 ? 1 : 0 };
  }) };


  var FIREWALL = {
    installed: true, active: true, backend: "ufw",
    rules: mk(9, function (i) {
      return { num: i + 1, port: [22, 80, 443, 8100, 2053, 8443, 9090, 3000, 5432][i],
               proto: i % 3 === 2 ? "udp" : "tcp",
               action: i > 5 ? "DENY" : "ALLOW",
               from: "Anywhere", comment: ["SSH", "HTTP", "HTTPS", "API", "x-ui",
                                           "sub", "metrics", "dev", "db"][i] };
    }),
  };

  var _ATT = mk(8, function (i) {
    return { ip: "203.0.113." + (10 + i), tries: 40 - i * 4,
             last: "2026-09-16 0" + (i % 9) + ":10", user: "root",
             known: i === 2, blocked: i < 2 };
  });
  var INTRUSION = { ready: true, hours: 24, ssh: { attempts: _ATT, total: 184 },
                    attempts: _ATT, blocked: 2, total: 184 };

  var AFFILIATES = {
    ready: true, totalOwed: 3400000, totalPaid: 12600000, resellerOwed: 900000,
    affiliates: mk(5, function (i) {
      return { id: i + 1, tg_id: 7000 + i, name: NAMES[i % 7], code: "AF" + (100 + i),
               pct: 10 + i, sales: 12 - i * 2, orders: 12 - i * 2,
               owed: [1400000, 900000, 600000, 300000, 200000][i],
               paid: i * 400000, is_active: 1 };
    }),
  };

  var MONITOR = {
    ready: true, summary: { nodes: 3, online: 3, cpu: 34, ram: 61, disk: 48 },
    nodes: mk(3, function (i) {
      return { id: i + 1, name: ["ایران-۱", "آلمان-۱", "فنلاند-۱"][i],
               online: true, cpu: [22, 44, 36][i], ram: [51, 68, 64][i],
               disk: [40, 55, 49][i], up: "۱۲ روز" };
    }),
  };

  var TUNNEL = {
    ready: true,
    nodes: mk(3, function (i) {
      return { id: i + 1, name: ["ایران-۱", "آلمان-۱", "فنلاند-۱"][i],
               host: "10.0.0." + (i + 1), online: true, role: i ? "خارج" : "ایران" };
    }),
    tunnels: mk(2, function (i) {
      return { id: i + 1, name: "تانل " + (i + 1), engine: "gost",
               status: "running", src: 1, dst: i + 2, port: 2000 + i };
    }),
    events: mk(4, function (i) {
      return { id: i, at: "2026-09-16 0" + i + ":00", kind: "info",
               text: "تانل " + (i % 2 + 1) + " دوباره وصل شد" };
    }),
    engines: [{ key: "gost", label: "GOST" }, { key: "frp", label: "FRP" }],
    stats: { nodes: 3, online: 3, tunnels: 2, running: 2 },
  };


  var CLIENTS = {
    ready: true, total: 42,
    groups: ["goroh-a", "goroh-b", "goroh-c", "بدون گروه"],
    stats: { total: 42, renewed: 28, notRenewed: 14, totalRenewals: 61,
             periodRenewals: 19, active: 33, expiringSoon: 5, expired: 3,
             disabled: 1, noGroup: 4, usedGB: 812.4, amount: 9400000,
             renewalRate: 66.7, newLast30: 9, olderThan30: 33, unpriced: 2 },
    clients: mk(14, function (i) {
      return { email: "nexora_" + (8800 + i * 7) + "_1",
               group: ["goroh-a", "goroh-b", "goroh-c", "بدون گروه"][i % 4],
               billable: i % 5 !== 0, gb: [50, 100, 30, 200][i % 4],
               usedBytes: (i + 1) * 3.2 * 1024 * 1024 * 1024,
               status: ["فعال", "رو به انقضا", "منقضی", "غیرفعال"][i % 4],
               renewals: i % 3, totalRenewals: i % 4,
               price: i % 7 === 0 ? null : 100000,
               amount: i % 7 === 0 ? 0 : 100000 * (1 + (i % 3)),
               created: "۱۴۰۴/۰۵/" + (10 + (i % 18)),
               createdGregorian: "2026-08-" + (10 + (i % 18)),
               expiry: "۱۴۰۴/۰۷/" + (5 + (i % 20)), daysLeft: 30 - i };
    }),
  };

  var INVOICE = {
    ready: true, group: "goroh-a", label: "حسین",
    period: { from: "۱۴۰۴/۰۶/۰۱", to: "۱۴۰۴/۰۶/۳۱" },
    totals: { due: 12400000, paid: 9000000, balance: 3400000,
              configs: 96, months: 104, before: 0, beforeMonths: 0,
              unused: 3, unusedWhy: { "هرگز روشن نشد": 3 } },
    due: 12400000, paid: 9000000, balance: 3400000,
    perGb: false, unpricedVolumes: [],
    totalAmount: 12400000,
    newConfigs: mk(3, function (i) {
      return { email: "nexora_99" + i + "_1", gb: 50, months: 1,
               devices: 1, price: 100000, amount: 100000 };
    }),
    renewals: mk(4, function (i) {
      return { email: "nexora_88" + i + "_1", gb: 100, months: 1 + (i % 2),
               devices: 2, price: 180000, amount: 180000 * (1 + (i % 2)) };
    }),
    items: mk(6, function (i) {
      return { email: "nexora_" + (8800 + i * 5) + "_1", gb: [50, 100, 30][i % 3],
               months: 1 + (i % 3), devices: 1 + (i % 2),
               price: [100000, 180000, 70000][i % 3],
               amount: [100000, 180000, 70000][i % 3] * (1 + (i % 3)),
               kind: i % 4 === 0 ? "ساخت" : "تمدید" };
    }),
    payments: mk(2, function (i) {
      return { id: i + 1, amount: [6000000, 3000000][i],
               at: "۱۴۰۴/۰۶/" + (10 + i * 8), note: "کارت به کارت" };
    }),
  };


  var PORTAL_LIST = {
    ready: true,
    groups: ["goroh-a", "goroh-b", "goroh-c"],
    tenants: mk(4, function (i) {
      return { id: i + 2, name: ["حسین", "مهدی", "سارا", "امیر"][i],
               portalSlug: ["hossein", "mehdi", "sara", "amir"][i],
               portalGroup: i === 3 ? "" : ["goroh-a", "goroh-b", "goroh-c"][i],
               portalEnabled: i !== 2,
               credit: [1200000, 4500000, -1, 0][i] };
    }),
  };

  function byPath(u) {
    if (u.indexOf("/tenant/portal-list") >= 0) return PORTAL_LIST;
    if (u.indexOf("/billing/clients") >= 0) return CLIENTS;
    if (u.indexOf("/billing/invoice") >= 0) return INVOICE;
    if (u.indexOf("/firewall/intrusion") >= 0) return INTRUSION;
    if (u.indexOf("/firewall") >= 0) return FIREWALL;
    if (u.indexOf("/tunnel/overview") >= 0 || u.indexOf("/tunnel") >= 0) return TUNNEL;
    if (u.indexOf("/affiliates") >= 0) return AFFILIATES;
    if (u.indexOf("/monitor") >= 0 || u.indexOf("/nodes") >= 0) return MONITOR;
    if (u.indexOf("/admin/config") >= 0) return CONFIG;
    if (u.indexOf("/admin/stats") >= 0) {
      return { appsCount: 7, faqCount: 4, videosCount: 2,
               appsPerPlatform: { android: 3, ios: 2, desktop: 2 },
               faqPerLanguage: { fa: 3, en: 1, tr: 0, ar: 0 },
               recommendedApps: { android: "Happ", ios: "Streisand", desktop: null },
               activeFeatures: { banners: true, referral: false, faqSection: true,
                                 notificationPopup: true, brandStrip: true },
               activeFeaturesCount: 4 };
    }
    if (u.indexOf("/bot/users/report") >= 0) return REPORT;
    if (u.indexOf("/billing/") >= 0) return BILLING;
    if (u.indexOf("/bot/orders") >= 0) return ORDERS;
    if (u.indexOf("/bot/plans") >= 0) return PLANS;
    if (u.indexOf("/bot/users") >= 0) return USERS;
    if (u.indexOf("/bot/funnel") >= 0) {
      return { ready: true, seen: 1284, started: 640, bought: 61, conversion: 4.8 };
    }
    if (u.indexOf("/bot/status") >= 0 || u.indexOf("/bot/connection") >= 0) {
      return { ready: true, connected: true, username: "nexora_bot", tenants: 3 };
    }
    return { ready: true };
  }

  var realFetch = window.fetch ? window.fetch.bind(window) : null;
  window.fetch = function (url, opt) {
    var u = String(url);
    if (u.indexOf("/api/") < 0 && realFetch) return realFetch(url, opt);
    return Promise.resolve({
      ok: true, status: 200,
      json: function () { return Promise.resolve(byPath(u)); },
      text: function () { return Promise.resolve(""); },
    });
  };
})();
