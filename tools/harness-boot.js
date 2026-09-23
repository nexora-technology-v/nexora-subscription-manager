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

  /* کدام اپ؟  harness.html?as=portal  یا  ?as=mini
   *
   * هر سه اپ از روی `location.pathname` انتخاب می‌شوند و سرورِ
   * پیش‌نمایش فایلی روی `/r/<نشانی>` ندارد. پس مسیر را همین‌جا —
   * *پیش از* اجرای باندل — عوض می‌کنیم. `main.jsx` بعد از این
   * اسکریپت اجرا می‌شود و همان مسیرِ تازه را می‌بیند.
   */
  /* پرچم‌های هارنس **پیش از** `replaceState` خوانده می‌شوند.
     آن یک خط نشانی را عوض می‌کند و `location.search` را خالی
     می‌گذارد، پس هر چیزی که دیرتر بخواندش هیچ‌وقت نمی‌بیندش. */
  var Q0 = new URLSearchParams(location.search);
  var NEW_RESELLER = Q0.get("plans") === "0";
  // ?accent=off بدونِ رنگ، ?accent=RRGGBB هر رنگی — تا بشود دید پالت
  // با رنگ‌های سخت (زردِ روشن، بنفشِ تیره) هم خوانا می‌ماند
  var MINI_ACCENT = Q0.get("accent") === "off" ? ""
    : /^[0-9a-fA-F]{6}$/.test(Q0.get("accent") || "") ? "#" + Q0.get("accent")
    : "#7c5cff";

  try {
    var qs = Q0;
    var as = qs.get("as");
    if (as === "portal") history.replaceState({}, "", "/r/hossein");
    else if (as === "mini") history.replaceState({}, "", "/app");
    else if (as === "aff") history.replaceState({}, "", "/aff");

    /* پوسته‌ی تلگرام:  ?scheme=dark  یا  ?scheme=light
     *
     * بیرون از تلگرام، خودِ telegram-web-app.js همیشه «روشن»
     * می‌گوید. پس پوسته‌ی تیره — که بیشترِ کاربرهای واقعی رویش
     * هستند — هیچ‌وقت دیده نمی‌شد. */
    /* ناحیه‌ی امن:  ?insets=47,34  →  بالا ۴۷، پایین ۳۴
     *
     * بیرون از تلگرام هر دو صفرند، پس محتوایی که زیرِ ناچ یا نوارِ
     * تلگرام می‌رود هیچ‌وقت دیده نمی‌شود — و این دقیقاً همان چیزی
     * است که روی گوشیِ واقعیِ مشتری خراب است. */
    var ins = qs.get("insets");
    var scOrIns = qs.get("scheme") || ins;

    var sc = qs.get("scheme");
    if (scOrIns && window.Telegram && window.Telegram.WebApp) {
      /* `colorScheme` روی شیءِ SDK قابلِ بازتعریف نیست، پس
         defineProperty بی‌صدا شکست می‌خورد. به‌جایش یک پوشش
         می‌گذاریم که همه چیز را به اصلی می‌دهد جز همین یک خاصیت. */
      var real = window.Telegram.WebApp;
      var parts = (ins || "").split(",");
      var saTop = parseInt(parts[0], 10) || 0;
      var saBot = parseInt(parts[1], 10) || 0;
      window.Telegram = { WebApp: new Proxy(real, {
        get: function (t, k) {
          if (sc && k === "colorScheme") return sc;
          if (ins && k === "safeAreaInset") {
            return { top: saTop, bottom: saBot, left: 0, right: 0 };
          }
          if (ins && k === "contentSafeAreaInset") {
            return { top: 0, bottom: 0, left: 0, right: 0 };
          }
          var v = t[k];
          return typeof v === "function" ? v.bind(t) : v;
        },
      }) };
      if (sc && window.Telegram.WebApp.colorScheme !== sc) {
        // مسیرِ خرابِ بی‌صدا ممنوع — اگر نگرفت، باید بدانیم
        console.error("[harness] scheme=" + sc + " اعمال نشد");
      }
    }
  } catch (e) { /* بی‌صدا */ }

  // قالب‌ها و پالت‌ها — همان شکلی که `/api/admin/themes` می‌دهد
  var THEMES = {
    currentTemplate: "classic",
    currentPalette: "ocean",
    templates: [
      { id: "classic", name: "کلاسیک" },
      { id: "analytics", name: "آماری" },
      { id: "wallet", name: "کیف پول" },
      { id: "console", name: "کنسول" },
    ],
    palettes: [
      { id: "ocean", name: "اقیانوس", vars: { accent: "#2B7FD6" } },
      { id: "violet", name: "بنفش", vars: { accent: "#7C5CFF" } },
      { id: "mint", name: "نعنایی", vars: { accent: "#00B894" } },
      { id: "gold", name: "طلایی", vars: { accent: "#F0A500" } },
    ],
    customPalettes: [],
  };

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
        usedGB: 1041.2, bankedGB: 462.6,
        amount: 12400000, paid: 9000000, uncertain: 2, unpriced: [], unpricedWhy: {},
        skipped: 3, skippedWhy: { "هرگز روشن نشد": 3 } },
      { name: "goroh-b", label: "مهدی", billed: true, configs: 61, months: 66,
        usedGB: 73.5, bankedGB: 0,
        amount: 7900000, paid: 7900000, uncertain: 0, unpriced: [], unpricedWhy: {}, skipped: 0 },
      { name: "goroh-c", label: "سارا", billed: true, configs: 34, months: 35,
        usedGB: 1541.6, bankedGB: 1017.5,
        amount: 4000000, paid: 1200000, uncertain: 1, unpriced: [200],
        unpricedWhy: { "نرخ ۲۰۰ گیگ تعریف نشده": 4 }, skipped: 1, skippedWhy: {} },
      { name: "بدون گروه", label: "بدون گروه", billed: false, configs: 12, months: 12,
        usedGB: 62.3, bankedGB: 0,
        amount: 0, paid: 0, uncertain: 0, unpriced: [], unpricedWhy: {}, skipped: 0 },
    ],
    needStart: [],
  };

  var mk = function (n, f) { var a = [], i; for (i = 0; i < n; i++) a.push(f(i)); return a; };
  var NAMES = ["علی رضایی", "مریم کاظمی", "حسین نوری", "زهرا مرادی", "امیر صادقی",
               "سارا احمدی", "رضا جعفری"];

  var ORDERS = { ready: true, total: 12, orders: mk(12, function (i) {
    // بکند `u.first_name` و `u.username` را join می‌کند (نه `name`).
    // با اسمِ اشتباه، هر ردیف «بدون نام» می‌شد — یعنی هارنس حالتی را
    // نشان می‌داد که پنلِ واقعی هیچ‌وقت ندارد.
    return { id: 900 + i, user_id: i + 1, first_name: NAMES[i % 7],
             username: "user" + i, tg_id: 5000 + i,
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


  var INBOUNDS = {
    ready: true, mode: "all", selected: [7, 9], default: 7,
    inbounds: mk(5, function (i) {
      return { id: 5 + i * 2, remark: ["Reality-443", "VLESS-2053", "VMess-8443",
                                       "Trojan-2083", "Shadowsocks-8080"][i],
               protocol: ["vless", "vless", "vmess", "trojan", "ss"][i],
               port: [443, 2053, 8443, 2083, 8080][i],
               enable: i !== 3, clients: 120 - i * 18 };
    }),
  };


  /* ── پنل نماینده ──
     مسیرش /r/<نشانی> است و توکنش از localStorage می‌آید، پس
     همین‌جا یکی می‌گذاریم تا صفحه‌ی ورود رد شود و خودِ پنل
     دیده شود. */
  try { localStorage.setItem("nexora_portal_token", "harness-token"); } catch (e) { /* بی‌صدا */ }

  var FAKE_LOGO = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCI+PHJlY3Qgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0IiByeD0iMTQiIGZpbGw9IiNGNTlFMEIiLz48dGV4dCB4PSIzMiIgeT0iNDIiIGZvbnQtc2l6ZT0iMzAiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXdlaWdodD0iODAwIiBmaWxsPSIjMDYwOTBGIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5IPC90ZXh0Pjwvc3ZnPg==";

  // آمادگیِ فروشِ ربات. نماینده‌ی جاافتاده کارت دارد و وصل است؛
  // نماینده‌ی تازه (`?plans=0`) هیچ‌کدام — همان حالتی که ربات
  // نمی‌فروشد و تا امروز در هارنس هیچ‌وقت دیده نمی‌شد.
  var P_CARDS = NEW_RESELLER ? [] : [
    { number: "6037991122223333", holder: "حسین دهلگی", bank: "ملی", active: true },
    { number: "6219861044445555", holder: "حسین دهلگی", bank: "سامان", active: false },
  ];
  var P_LINKED = !NEW_RESELLER;
  function pReady() {
    return { ownerLinked: P_LINKED, hasGroup: true,
             activeCards: P_CARDS.filter(function (c) { return c.active; }).length };
  }

  var P_NAMES = ["نیما احمدی", "سارا موسوی", "رضا کریمی", "لیلا نوری", "پویا صادقی",
                 "مهسا رحیمی", "کاوه جعفری"];
  var P_USERS = { users: [], total: 62, counts: {
    all: 62, active: 38, expired: 11, never: 13, buyers: 41, withPhone: 29,
    noPhone: 33, withBalance: 6, withCoins: 17, referred: 9, blocked: 1 } };
  for (var pu = 0; pu < 14; pu++) {
    P_USERS.users.push({
      id: 500 + pu, tg_id: 7100 + pu, first_name: P_NAMES[pu % 7],
      username: pu % 3 ? "p_user" + pu : "", phone: pu % 2 ? "0935100" + (2000 + pu) : "",
      balance: (pu % 4) * 30000, coins: pu * 2, is_blocked: pu === 5 ? 1 : 0,
      created_at: "2026-09-" + (10 + (pu % 9)) + " 10:00",
      ordersCount: pu % 4, spent: (pu % 4) * 150000, subsCount: pu % 3, activeSubs: pu % 2,
    });
  }
  var P_SUB = { user: { id: 501, tg_id: 7101, first_name: "سارا موسوی", username: "p_user1",
                        phone: "09351002001", balance: 30000, coins: 2, created_at: "2026-09-11 10:00" },
                subscriptions: [{ id: 91, plan_name: "ماهانه ۵۰", client_email: "hossein_7101_1",
                                  gb: 50, is_active: 1, expires_at: "2026-10-11 10:00",
                                  created_at: "2026-09-11 10:00" }],
                orders: [{ id: 3301, plan_name: "ماهانه ۵۰", amount: 150000, status: "approved",
                           created_at: "2026-09-11 10:00", paid_from: "card" }],
                coinHistory: [], live: {}, liveAvailable: false };
  var P_INBOX = { unread: 1, threads: [
    { userId: 501, tgId: 7101, name: "سارا موسوی", username: "p_user1", avatar: "",
      unread: 1, lastBody: "کانفیگ روی آیفون وصل نمی‌شه", lastAt: "2026-09-23 09:12" },
    { userId: 503, tgId: 7103, name: "لیلا نوری", username: "",
      unread: 0, lastBody: "ممنون، درست شد 🙏", lastAt: "2026-09-22 21:40" },
  ] };
  var P_THREAD = { messages: [
    { id: 1, from: "user", body: "سلام، کانفیگ روی آیفون وصل نمی‌شه", orderId: null, at: "2026-09-23 09:10", read: true },
    { id: 2, from: "system", body: "سفارش #3301 تایید شد و اشتراکتان فعال است.", orderId: 3301, at: "2026-09-23 09:11", read: true },
    // عکس بعداً وصل می‌شود: FAKE_SHOT پایین‌تر تعریف شده
    { id: 3, from: "user", body: "این پیام خطاست", photo: "", orderId: null, at: "2026-09-23 09:12", read: false },
  ] };
  var P_SETTINGS = { settings: {
    brand: "وی‌پی‌ان حسین", support_username: "hsupport",
    welcome_text: "سلام {name} 👋 به {brand} خوش آمدید.",
    trial_enabled: !NEW_RESELLER, ask_phone: true, order_ttl_minutes: 45,
    reminders: { enabled: true, days: [5, 2, 1], traffic_pct: 85, traffic_text: "" },
    coins: { enabled: true, per_referral: 12, welcome_bonus: 3, max_percent: 40,
             expire_days: 0, tiers: [{ coins: 20, percent: 10 }, { coins: 50, percent: 25 }] },
    force_channel_on: false, force_channel: "",
  }, trialCap: { gb: 1, days: 1, ip_limit: 1 }, trialWhy: "" };

  var P_ME = { ok: true, id: 2, name: "حسین", slug: "hossein", version: "1.87.0",
               credit: 1200000, discount: 0, hasBot: true,
               botUsername: "hossein_vpn_bot", logo: FAKE_LOGO };

  var P_SUMMARY = { group: "goroh-a", label: "حسین", configs: 96, months: 104,
                    renewals: 19, usedGB: 812.4, due: 12400000, paid: 9000000,
                    balance: 3400000, credit: 1200000, prepaid: true };

  var P_CONFIGS = { total: 14, configs: mk(14, function (i) {
    var used = [12, 47, 2, 31, 8, 44, 19, 3, 27, 36, 15, 40, 6, 22][i];
    var gb = [50, 50, 100, 50, 30, 50, 100, 50, 30, 50, 100, 50, 30, 50][i];
    // نماینده می‌تواند برای مشتری‌اش اسم بگذارد و آن اسم خودِ email
    // می‌شود — پس داده‌ی ساختگی هم باید هر دو شکل را داشته باشد،
    // وگرنه هیچ‌وقت نمی‌بینیم فارسی چطور درمی‌آید.
    var NAMED = { 1: "رضا مرادی", 4: "سمانه احمدی", 9: "خانم رستمی",
                  11: "Ali Karimi" };
    return { email: NAMED[i] || ("nexora_" + (8800 + i * 7) + "_1"), gb: gb,
             gbLabel: gb + " گیگ", used: used * 1024 * 1024 * 1024, usedGB: used,
             usagePct: Math.round(used * 100 / gb), devices: 1 + (i % 3),
             createdJalali: "۱۴۰۴/۰۵/" + (10 + (i % 18)),
             createdGregorian: "2026-08-" + (10 + (i % 18)),
             expiryJalali: "۱۴۰۴/۰۷/" + (5 + (i % 20)),
             expiryGregorian: "2026-10-" + (5 + (i % 20)),
             daysLeft: [26, 3, 30, 12, 19, 44, -2, 8, 30, 1, 22, 15, 9, 33][i],
             active: i !== 6, subId: "sub" + i,
             subUrl: "https://sub.example.com/sub" + i, group: "goroh-a" };
  }) };

  // پلن‌های ربات نماینده + سیاست حجم. حالت «پله‌ای» گذاشته شده تا
  // در هارنس دیده شود که فیلدِ حجم بسته می‌شود.
  var P_BOT_PLANS = {
    ready: true, hasBot: true, trialCap: { gb: 1, days: 1, ip_limit: 1 },
    gbMode: "tiers", gbAllowed: [30, 50, 100, 200],
    perGb: 0, gbCost: { "30": 90000, "50": 140000, "100": 250000, "200": 460000 },
    plans: [
      { id: 1, name: "یک‌ماهه", description: "مناسب شروع", gb: 50, days: 30,
        ip_limit: 1, price: 180000, is_active: 1, is_trial: 0, sort_order: 0 },
      { id: 2, name: "سه‌ماهه", description: "پرفروش", gb: 100, days: 90,
        ip_limit: 2, price: 230000, is_active: 1, is_trial: 0, sort_order: 1 },
    ],
  };

  // پوسته‌ی شخصی — عمداً **قفل** شروع می‌شود، چون صفحه‌ی قفل همان
  // چیزی است که بیشترِ نماینده‌ها می‌بینند و اگر باز باشد هیچ‌وقت
  // دیده نمی‌شود.
  // ?addon=1 یعنی پوسته‌ی شخصی فعال است — تا حالتِ قفل‌باز هم دیده شود
  var P_THEME = { accent: "", brand: "حسین VPN", logo: "",
                  tpl: "aurora", palette: "ocean",
                  logoStyle: { shape: "rounded", bg: "none", pad: 0 },
                  open: Q0.get("addon") === "1", until: Q0.get("addon") === "1" ? "2026-10-23" : "",
                  price: 250000, days: 30, credit: 1800000, postpaid: false };

  var P_STATS = { total: 96, active: 84, inactive: 12, expired: 5,
                  expiringSoon: 7, neverExpires: 2, nearQuota: 6, overQuota: 2,
                  unlimitedQuota: 3, usedGB: 812.4, quotaGB: 4200, usagePct: 19.3,
                  thisMonth: { new: 11, renewals: 19 },
                  series: { new:   [0,1,0,2,1,0,3,1,2,0,1,4,2,3],
                            renew: [1,0,2,1,3,2,0,1,4,2,1,0,3,2] },
                  needsAttention: 14,
                  sales: { hasBot: true, orders: 23, sold: 5600000, received: 4350000,
                           monthOrders: 9, monthSold: 2150000, pending: 2 } };

  var P_PLANS = { credit: 1200000, prepaid: true, perGb: 0,
                  plans: [{ gb: 30, label: "۳۰ گیگ", price: 70000, perDevice: 15000 },
                          { gb: 50, label: "۵۰ گیگ", price: 100000, perDevice: 20000 },
                          { gb: 100, label: "۱۰۰ گیگ", price: 180000, perDevice: 30000 },
                          { gb: 200, label: "۲۰۰ گیگ", price: 320000, perDevice: 40000 }] };

  // شکلِ ردیف **دقیقاً** همانی است که بکند می‌دهد: `customer` و
  // `planName`، نه `name` و `plan`. نسخه‌ی قبلی نام‌های دیگری
  // می‌فرستاد و هر ردیف «#۷۰۰ · » خالی نشان می‌داد — دادهٔ ساختگی
  // که شکلش با واقعیت فرق دارد، باگِ تقلبی می‌سازد و باگِ واقعی
  // را می‌پوشاند.
  var P_ORDER_ROWS = mk(6, function (i) {
    return { id: 700 + i, customer: NAMES[i % 7], tgId: 9000 + i,
             planName: ["یک‌ماهه", "سه‌ماهه"][i % 2],
             gb: [50, 100][i % 2],
             amount: [120000, 280000][i % 2],
             kind: ["new", "renew", "topup"][i % 3],
             paidFrom: i % 2 ? "wallet" : "card",
             hasReceipt: i % 2 === 0,
             receiptText: i % 4 === 0 ? "کارت به کارت ۱۲۰ هزار، ساعت ۱۴:۳۰" : "",
             note: "",
             status: ["awaiting", "approved", "rejected"][i % 3],
             createdAt: "۱۴۰۵/۰۶/۰" + ((i % 9) + 1) };
  });

  // و فیلترِ برگه‌ها واقعاً اعمال شود، وگرنه سفارشِ تاییدشده در
  // برگه‌ی «در انتظار» می‌نشیند و چون دکمه‌ای ندارد شبیهِ «کار
  // نمی‌کند» به نظر می‌رسد.
  function portalOrders(u) {
    var st = (String(u).match(/status=(\w+)/) || [])[1] || "open";
    var want = { open: ["pending", "awaiting", "review"],
                 approved: ["approved"], rejected: ["rejected"] }[st]
               || ["pending", "awaiting", "review"];
    var rows = P_ORDER_ROWS.filter(function (o) {
      return want.indexOf(o.status) >= 0;
    });
    return { ready: true, orders: rows, total: rows.length, truncated: false };
  }


  /* ── مینی‌اپ مشتری ── */
  // رنگِ فروشگاه — نماینده‌ای که پوسته‌ی شخصی گرفته. خالی یعنی
  // پوسته‌ی پیش‌فرض، و آن حالت هم باید دیده شود: `?accent=` در
  // نشانیِ هارنس خاموشش می‌کند.
  // ?brand= — فروشگاهِ یک نماینده. بدونش همه‌ی آزمون‌های اسپلش و
  // سربرگ «نکسورا» می‌دیدند، یعنی همان نامی که مشتریِ نماینده هرگز
  // نباید ببیند؛ نامِ فارسی/لاتینِ مخلوط هم فقط این‌طور دیده می‌شود.
  var M_ME = { name: "مریم کاظمی", brand: Q0.get("brand") || "نکسورا", balance: 240000, coins: 36,
               accent: MINI_ACCENT,
               // ?tpl=mono|bold|neon و ?shape=circle — قالب و قابِ لوگو
               theme: { tpl: Q0.get("tpl") || "aurora",
                        palette: MINI_ACCENT ? (Q0.get("pal") || "custom") : "",
                        accent: MINI_ACCENT,
                        logoStyle: { shape: Q0.get("shape") || "rounded", bg: "none", pad: 0 } },
               logo: Q0.get("logo") === "off" ? "" : FAKE_LOGO,
               support: "nexora_support", channel: "nexora_vpn",
               phone: "", avatar: "",
               refCode: "NX7K2M", refCount: 3,
               tgId: 1278109787, username: "maryam_k",
               botUsername: "nexora_vpn_bot" };
  /* پاداش‌ها. عددها واقع‌نما: ۳۶ سکه یعنی پله‌ی ۲۰ باز شده و
     پله‌ی ۴۰ نزدیک است — همان حالتی که نوارِ پیشرفت را معنادار
     می‌کند. با صفر، کارت شاخه‌ی «هنوز چیزی ندارید» را می‌گرفت و
     سالم به نظر می‌رسید. */
  var M_REWARDS = {
    enabled: true, coins: 36, percent: 10, cost: 20,
    next: { coins: 40, percent: 20, need: 4 },
    maxPercent: 50,
    tiers: [{ coins: 20, percent: 10 }, { coins: 40, percent: 20 },
            { coins: 60, percent: 30 }, { coins: 80, percent: 40 },
            { coins: 100, percent: 50 }],
    perReferral: 10, welcomeBonus: 3, expireDays: 0,
    refCode: "NX7K2M", refCount: 3, botUsername: "nexora_vpn_bot",
    link: "https://t.me/nexora_vpn_bot?start=NX7K2M"
  };
  /* کدهای تخفیف. با فهرستِ خالی، صفحه شاخه‌ی «هنوز کدی ساخته
     نشده» را می‌گیرد و هیچ‌وقت ردیفِ واقعی دیده نمی‌شود. */
  var EVENT_KINDS = {
  provision_failed: { label: "ساختِ کانفیگ ناموفق", level: "error", alert: true },
  deliver_failed: { label: "کانفیگ ساخته شد ولی به مشتری نرسید", level: "error", alert: true },
  order_deliver_failed: { label: "تحویلِ سفارشِ تاییدشده ناموفق", level: "error", alert: true },
  renew_failed: { label: "تمدید خودکار ناموفق", level: "error", alert: true },
  usage_failed: { label: "خواندنِ مصرف از پنل ناموفق", level: "error", alert: false },
  channel_failed: { label: "ارسالِ پستِ کانال ناموفق", level: "error", alert: false },
  provision: { label: "کانفیگ ساخته شد", level: "ok", alert: false },
  signup: { label: "کاربر تازه", level: "info", alert: false },
};

var EVENTS = [
  { id: 214, kind: "provision_failed", level: "error",
    text: "ساختِ کانفیگ ناموفق — سفارش #1842 · خطای پنل: 3x-ui پاسخ نداد (timeout بعد از ۳۰ ثانیه)",
    at: "1405/07/01 14:22", userId: 88, name: "مریم کاظمی", username: "maryamk", tgId: 184923771 },
  { id: 213, kind: "signup", level: "info", text: "کاربر تازه",
    at: "1405/07/01 14:19", userId: 141, name: "امیرحسین", username: "", tgId: 622019384 },
  { id: 212, kind: "provision", level: "ok",
    text: "کانفیگ ساخته شد — سفارش #1841 · اشتراک #903",
    at: "1405/07/01 13:58", userId: 77, name: "سعید رحمانی", username: "saeedr", tgId: 99201773 },
  { id: 211, kind: "renew_failed", level: "error",
    text: "تمدید خودکار ناموفق — اشتراک #812 · موجودی کیف پول کافی نبود و کسر برگشت خورد",
    at: "1405/07/01 12:04", userId: 52, name: "نگار", username: "", tgId: 510228841 },
  { id: 210, kind: "channel_failed", level: "error",
    text: "ارسالِ پستِ کانال ناموفق — پست #37 · ربات در کانال ادمین نیست",
    at: "1405/07/01 11:40", userId: null, name: "", username: "", tgId: null },
  { id: 209, kind: "deliver_failed", level: "error",
    text: "کانفیگ ساخته شد ولی به مشتری نرسید — سفارش #1836 · Forbidden: bot was blocked by the user",
    at: "1405/06/31 22:15", userId: 61, name: "حسین نجی", username: "hnaji", tgId: 771993022 },
  { id: 208, kind: "usage_failed", level: "error",
    text: "خواندنِ مصرف از پنل ناموفق · نام کاربری یا رمز پنل پذیرفته نشد",
    at: "1405/06/31 20:00", userId: null, name: "", username: "", tgId: null },
  { id: 207, kind: "provision", level: "ok",
    text: "کانفیگ ساخته شد — سفارش #1835 · اشتراک #901",
    at: "1405/06/31 19:31", userId: 34, name: "زهرا م.", username: "zahra_m", tgId: 402118837 },
];

var D_CODES = { ready: true,
    /* گزارش با عددِ واقع‌نما، نه صفر: با صفر، صفحه شاخه‌ی «هنوز
       استفاده نشده» را می‌گیرد و خودِ گزارش هیچ‌وقت دیده نمی‌شود. */
    report: {
      total: { orders: 270, sales: 47250000, given: 4890000, codes: 4 },
      top: [
        { code: "WELCOME10", orders: 212, sales: 38160000, given: 2544000,
          lastAt: "2026-09-19 21:40" },
        { code: "NOWRUZ", orders: 37, sales: 6660000, given: 1110000,
          lastAt: "2026-09-18 11:02" },
        { code: "OLDSALE", orders: 20, sales: 2400000, given: 1200000,
          lastAt: "2026-08-30 09:15" },
        { code: "BACKE2FD35", orders: 1, sales: 30000, given: 36000,
          lastAt: "2026-09-17 19:05" },
      ],
      winback: { sent: 14, used: 1, orders: 1, sales: 30000, given: 36000 },
    },
    plans: [{ id: 1, name: "یک‌ماهه" }, { id: 2, name: "سه‌ماهه" }],
    discounts: [
      { id: 1, code: "NOWRUZ", percent: 25, maxUses: 100, usedCount: 37,
        planId: null, planName: null, expiresAt: "1405-01-15",
        active: true, paidOrders: 37, givenToman: 1110000 },
      { id: 2, code: "WELCOME10", percent: 10, maxUses: 0, usedCount: 212,
        planId: null, planName: null, expiresAt: null,
        active: true, paidOrders: 212, givenToman: 2544000 },
      { id: 3, code: "TRIAL-A7K2", percent: 30, maxUses: 1, usedCount: 1,
        planId: 1, planName: "یک‌ماهه", expiresAt: "1404-07-02",
        active: true, paidOrders: 1, givenToman: 36000 },
      { id: 4, code: "OLDSALE", percent: 50, maxUses: 20, usedCount: 20,
        planId: null, planName: null, expiresAt: null,
        active: false, paidOrders: 20, givenToman: 1200000 },
    ] };

  var GB = 1024 * 1024 * 1024;
  var M_SUBS = { subs: mk(3, function (i) {
    var tot = [50 * GB, 100 * GB, 50 * 1024 * 1024][i];
    var use = [32 * GB, 8 * GB, 61.2 * 1024 * 1024][i];
    return { id: i + 1, plan: ["پلن یک‌ماهه", "پلن سه‌ماهه", "اشتراک تست"][i],
             email: "nexora_1278109787_" + (9605 + i),
             gb: [50, 100, 0][i], usedGB: [32, 8, 0.06][i],
             usagePct: [64, 8, 100][i],
             totalBytes: tot, usedBytes: use,
             remainBytes: Math.max(0, tot - use),
             months: [1, 3, 2][i], isTrial: i === 2,
             active: i !== 2,
             expiryJalali: ["۱۴۰۴/۰۷/۱۲", "۱۴۰۴/۰۹/۰۳", "۱۴۰۵/۰۶/۲۶"][i],
             daysLeft: [26, 78, -3][i],
             subUrl: "https://sub.example.com/s" + i };
  }) };
  var M_PLANS = { plans: mk(3, function (i) {
    return { id: i + 1, name: ["یک‌ماهه", "سه‌ماهه", "شش‌ماهه"][i],
             desc: ["مناسب شروع", "پرفروش‌ترین", "به‌صرفه‌ترین"][i],
             gb: [50, 100, 200][i], days: [30, 90, 180][i],
             devices: [1, 2, 3][i], price: [120000, 280000, 480000][i],
             isTrial: false };
  }) };

  // خریدِ ساختگی — موجودی را واقعاً کم می‌کند و یک اشتراک اضافه
  // می‌کند، وگرنه نمی‌شود دید بعد از خرید چه اتفاقی می‌افتد.
  // کم‌آوردنِ موجودی هم باید قابلِ دیدن باشد، پس پلن گران‌تر از
  // موجودی عمداً رد می‌شود.
  function miniBuy(body) {
    var pid = (body || {}).planId;
    var pl = null;
    M_PLANS.plans.forEach(function (x) { if (x.id === pid) pl = x; });
    if (!pl) { var e = new Error("این پلن دیگر در دسترس نیست"); e.status = 404; throw e; }
    if (M_ME.balance < pl.price) {
      var e2 = new Error("موجودی کافی نیست — "
        + (pl.price - M_ME.balance).toLocaleString("fa-IR") + " تومان کم دارید");
      e2.status = 402; throw e2;
    }
    M_ME.balance -= pl.price;
    M_SUBS.subs.unshift({
      id: 900 + M_SUBS.subs.length, plan: pl.name,
      email: "nexora_1278109787_" + (9700 + M_SUBS.subs.length),
      active: true, isTrial: false, months: Math.round(pl.days / 30),
      gb: pl.gb, usedGB: 0, usagePct: 0, daysLeft: pl.days,
      usedBytes: 0, totalBytes: pl.gb * 1024 * 1024 * 1024,
      remainBytes: pl.gb * 1024 * 1024 * 1024,
      expiryJalali: "۱۴۰۵/۰۸/۱۲",
      subUrl: "https://sub.example.com/new" });
    return { ok: true, spent: pl.price, left: M_ME.balance, plan: pl.name };
  }

  // با آرایه‌ی خالی، کارتِ «سفارشِ در انتظار» هیچ‌وقت دیده نمی‌شد و
  // شاخه‌ی سالمِ «چیزی نیست» رندر می‌شد — همان دامی که CLAUDE.md
  // درباره‌اش هشدار می‌دهد. نامِ بلند عمدی است: کوتاه‌ترین نام
  // سرریزِ ردیف را پنهان می‌کند.
  var M_ORDERS = { orders: [
    { id: 4098, status: "awaiting", amount: 280000,
      plan: "پلن سه‌ماهه ۱۰۰ گیگ — نامحدود کاربر", paidFrom: "card",
      createdAt: "۱۴۰۵/۰۶/۲۷", expiresAt: "", note: "" },
    { id: 4097, status: "pending", amount: 95000,
      plan: "پلن یک‌ماهه", paidFrom: "card",
      createdAt: "۱۴۰۵/۰۶/۲۷", expiresAt: "", note: "" },
  ] };
  var _oid = 4100;

  // سفارشِ کارتی — و رسیدش. بدون این‌ها، مسیر کارت‌به‌کارت در هارنس
  // دیده نمی‌شود و هیچ‌وقت معلوم نمی‌شود چه شکلی است.
  function miniOrder(body) {
    var pid = (body || {}).planId, pl = null;
    M_PLANS.plans.forEach(function (x) { if (x.id === pid) pl = x; });
    if (!pl) { var e = new Error("این پلن دیگر در دسترس نیست"); e.status = 404; throw e; }
    _oid += 1;
    M_ORDERS.orders.unshift({ id: _oid, status: "pending", amount: pl.price,
                              plan: pl.name, paidFrom: "card",
                              createdAt: "۱۴۰۵/۰۶/۲۷", expiresAt: "", note: "" });
    return { ok: true, orderId: _oid, amount: pl.price, expiresAt: "",
             plan: pl.name,
             card: { number: "6037991234567890", holder: "حسین رضایی",
                     bank: "بانک ملی" } };
  }

  function miniReceipt(u, body) {
    var id = parseInt((u.match(/order\/(\d+)\/receipt/) || [])[1], 10);
    var o = null;
    M_ORDERS.orders.forEach(function (x) { if (x.id === id) o = x; });
    if (!o) { var e = new Error("سفارش پیدا نشد"); e.status = 404; throw e; }
    if (!(body || {}).data && !((body || {}).text || "").trim()) {
      var e2 = new Error("عکس رسید یا متن پیامک بانک را بفرستید");
      e2.status = 400; throw e2;
    }
    o.status = "awaiting";
    return { ok: true, status: "awaiting" };
  }

  // صندوق پیام — با یک خبرِ سیستمی و یک گفتگوی واقعی، وگرنه
  // هیچ‌وقت معلوم نمی‌شود سه نوع پیام کنار هم چه شکلی‌اند.
  /* عکسِ ساختگیِ یک اسکرین‌شاتِ خطا — با آرایه‌ی بدونِ عکس،
     حبابِ تصویر هیچ‌وقت رندر نمی‌شد و سالم به نظر می‌رسید */
  var FAKE_SHOT = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzNjAgNjQwIj48cmVjdCB3aWR0aD0iMzYwIiBoZWlnaHQ9IjY0MCIgZmlsbD0iIzBGMTcyQSIvPjxyZWN0IHg9IjI0IiB5PSIxODAiIHdpZHRoPSIzMTIiIGhlaWdodD0iMTIwIiByeD0iMTIiIGZpbGw9IiM3RjFEMUQiLz48dGV4dCB4PSIxODAiIHk9IjIzMCIgZm9udC1zaXplPSIyMCIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZpbGw9IiNGQ0E1QTUiIHRleHQtYW5jaG9yPSJtaWRkbGUiPkNvbm5lY3Rpb24gZmFpbGVkPC90ZXh0Pjx0ZXh0IHg9IjE4MCIgeT0iMjYyIiBmb250LXNpemU9IjE1IiBmb250LWZhbWlseT0ic2Fucy1zZXJpZiIgZmlsbD0iI0ZFQ0FDQSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+dGltZW91dCBhZnRlciAzMHM8L3RleHQ+PC9zdmc+";

  var M_INBOX = { unread: 1, messages: [
    { id: 1, from: "user", body: "سلام، رسید رو فرستادم ولی هنوز تایید نشده",
      orderId: 4101, at: "2026-09-17 11:02:00", read: true },
    { id: 2, from: "admin", body: "سلام. الان بررسی می‌کنم، چند دقیقه صبر کنید.",
      orderId: null, at: "2026-09-17 11:04:00", read: true },
    { id: 3, from: "system",
      body: "رسید سفارش #4101 تایید نشد.\n\nدلیل: مبلغ واریزی با مبلغ سفارش نمی‌خواند — ۱۲۰٬۰۰۰ تومان لازم بود.",
      orderId: 4101, at: "2026-09-17 11:09:00", read: false },
    { id: 4, from: "user", body: "این خطا رو می‌گیرم", photo: FAKE_SHOT,
      orderId: null, at: "2026-09-17 11:15:00", read: true },
    { id: 5, from: "admin", body: "", photo: FAKE_SHOT,
      orderId: null, at: "2026-09-17 11:18:00", read: true },
  ] };

  var M_PING = { unread: 1, openOrders: 1, subs: 3 };

  function inboxSend(body) {
    var t = ((body || {}).body || "").trim();
    // پیامی که فقط عکس است هم معتبر است — همان قاعده‌ی سرور
    if (!t && !(body || {}).photo) {
      var e = new Error("پیام خالی است"); e.status = 400; throw e;
    }
    M_INBOX.messages.push({ id: M_INBOX.messages.length + 1, from: "user",
                            body: t, photo: (body || {}).photo || "", orderId: null,
                            at: new Date().toISOString().slice(0, 16).replace("T", " "),
                            read: true });
    return { ok: true };
  }

  var A_INBOX = { unread: 2, threads: [
    { userId: 1, tgId: 6001, name: "مریم کاظمی", username: "maryam", avatar: "",
      unread: 2, lastBody: "ممنون، دوباره واریز کردم", lastAt: "2026-09-17 11:20" },
    { userId: 2, tgId: 6002, name: "علی رضایی", username: "ali",
      unread: 0, lastBody: "مرسی درست شد", lastAt: "2026-09-16 19:02" },
  ] };
  var A_THREAD = { messages: [
    { id: 1, from: "user", body: "سلام، رسید رو فرستادم", orderId: 4101, at: "2026-09-17 11:02", read: true },
    { id: 2, from: "admin", body: "بررسی می‌کنم، چند دقیقه صبر کنید.", orderId: null, at: "2026-09-17 11:04", read: true },
    { id: 3, from: "system", body: "رسید سفارش #4101 تایید نشد.\n\nدلیل: مبلغ واریزی نمی‌خواند.", orderId: 4101, at: "2026-09-17 11:09", read: false },
    { id: 4, from: "user", body: "ممنون، دوباره واریز کردم", orderId: null, at: "2026-09-17 11:20", read: false },
    { id: 5, from: "user", body: "این خطا رو می‌گیرم", photo: FAKE_SHOT, orderId: null, at: "2026-09-17 11:22", read: false },
    { id: 6, from: "admin", body: "", photo: FAKE_SHOT, orderId: null, at: "2026-09-17 11:25", read: true },
  ] };

  // پروفایلِ ساختگی — تا بشود دید ذخیره و عکس واقعاً چه می‌کنند
  function miniProfile(body) {
    var b = body || {};
    if (b.name) M_ME.name = b.name;
    if (b.phone) M_ME.phone = b.phone;
    return { ok: true, name: M_ME.name, phone: M_ME.phone || "" };
  }

  // `method` هم لازم است: مسیرهایی که هم GET دارند و هم POST و
  // هم DELETE (مثل کدهای تخفیف) بدونش نمی‌توانند فرق بگذارند.
  function byPath(u, body, method) {
    if (u.indexOf("/aff/login") >= 0) {
      var ac = String((body || {}).code || "").toUpperCase();
      if (ac !== "AFF1") { var ae2 = new Error("کد یا رمز نادرست است"); ae2.status = 401; throw ae2; }
      return { token: "afftoken", name: "رضا مرادی", code: "AFF1", percent: 10 };
    }
    if (u.indexOf("/aff/logout") >= 0) return { ok: true };
    if (u.indexOf("/aff/summary") >= 0) {
      return {
        name: "رضا مرادی", code: "AFF1", percent: 10,
        earned: 480000, paid: 300000, balance: 180000,
        users: [
          { id: 1, first_name: "مریم کاظمی", username: "maryam", tg_id: 6001,
            created_at: "2026-08-02", orders: 3, spent: 900000 },
          { id: 2, first_name: "علی رضایی", username: "ali", tg_id: 6002,
            created_at: "2026-08-19", orders: 1, spent: 150000 },
        ],
        commissions: [
          { id: 3, order_id: 4101, order_amount: 480000, percent: 10,
            commission: 48000, status: "pending", created_at: "2026-09-14",
            first_name: "مریم کاظمی" },
          { id: 2, order_id: 4088, order_amount: 300000, percent: 10,
            commission: 30000, status: "paid", created_at: "2026-08-19",
            first_name: "علی رضایی" },
        ],
        payouts: [
          { id: 1, amount: 300000, note: "کارت‌به‌کارت", paid_at: "2026-09-01" },
        ],
      };
    }
    if (u.indexOf("/mini/topup/options") >= 0) {
      return { min: 10000, max: 50000000,
               presets: [100000, 200000, 500000, 1000000],
               balance: M_ME.balance };
    }
    if (u.indexOf("/mini/topup") >= 0) {
      var amt = Number((body || {}).amount || 0);
      if (!(amt >= 10000 && amt <= 50000000)) {
        var te = new Error("مبلغ باید بین ۱۰ هزار تا ۵۰ میلیون تومان باشد");
        te.status = 400; throw te;
      }
      return { orderId: 5200, amount: amt,
               card: { number: "6037991234567890", holder: "علی رضایی" },
               ttlMinutes: 60 };
    }
    if (u.indexOf("/mini/profile/avatar") >= 0) {
      // DELETE و POST هر دو به همین می‌رسند؛ بدنه فرق را می‌گوید
      if (body && body.data) { M_ME.avatar = body.data; return { ok: true, avatar: M_ME.avatar }; }
      M_ME.avatar = ""; return { ok: true, avatar: "" };
    }
    if (u.indexOf("/mini/profile") >= 0) return miniProfile(body);
    /* پرونده‌ی کاربر.
       بدون این مقک، پرونده با «بدون نام» و صفر باز می‌شد — یعنی
       هارنس حالتی را نشان می‌داد که پنلِ واقعی تقریباً هیچ‌وقت
       ندارد، و خوانایی‌اش اصلاً سنجیده نمی‌شد. */
    if (u.indexOf("/admin/bot/subscriber/") >= 0) {
      var stg = u.split("/subscriber/")[1].split("?")[0];
      var idx = (parseInt(stg, 10) || 6000) % 7;
      return {
        user: { id: idx + 1, tg_id: parseInt(stg, 10) || 6001,
                first_name: NAMES[idx], username: "user" + idx,
                phone: "0912000" + (1000 + idx),
                balance: 240000, coins: 12, is_blocked: 0,
                created_at: "2026-08-02", ordersCount: 3, spent: 690000 },
        subscriptions: [
          { id: 1, email: "nexora_" + stg + "_1", plan_name: "سه‌ماهه ۱۰۰ گیگ",
            gb: 100, usedGB: 41.3, usagePct: 41, status: "active",
            expiryJalali: "1405/09/14", daysLeft: 58, limitIp: 2 },
          { id: 2, email: "nexora_" + stg + "_2", plan_name: "یک‌ماهه",
            gb: 30, usedGB: 30, usagePct: 100, status: "expired",
            expiryJalali: "1405/06/01", daysLeft: -12, limitIp: 1 },
        ],
        orders: [
          { id: 4101, plan_name: "سه‌ماهه ۱۰۰ گیگ", amount: 480000,
            status: "approved", paid_from: "card", created_at: "2026-09-14 10:22" },
          { id: 4088, plan_name: "یک‌ماهه", amount: 120000,
            status: "approved", paid_from: "wallet", created_at: "2026-08-02 18:40" },
          { id: 4075, plan_name: "یک‌ماهه", amount: 120000,
            status: "rejected", paid_from: "card", created_at: "2026-07-29 12:05" },
        ],
        coinHistory: [
          { at: "2026-09-14", delta: 8, why: "خرید" },
          { at: "2026-08-02", delta: 4, why: "دعوت دوست" },
        ],
        live: { up: 4123456789, down: 38123456789, total: 107374182400,
                expiryTime: 1789000000000 },
        liveAvailable: true,
      };
    }
    if (u.indexOf("/admin/billing/overview") >= 0) {
      return { ready: true, groups: BILLING.groups.map(function (g) {
        return { name: g.name, label: g.label, billed: g.billed,
                 due: g.amount, paid: g.paid,
                 balance: g.amount - g.paid, configs: g.configs };
      }) };
    }
    if (u.indexOf("/admin/config/history") >= 0) return {
      current: 7,
      versions: [
        { version: 6, at: "2026-09-17 11:20", size: 3090 },
        { version: 5, at: "2026-09-17 09:02", size: 3044 },
        { version: 4, at: "2026-09-16 18:41", size: 2987 },
      ],
    };
    if (u.indexOf("/admin/config/rollback/") >= 0) return { ok: true, version: 8, config: CONFIG };
    if (u.indexOf("/admin/bot/alerts") >= 0) return {
      receipts: 3, messages: 2, ready: true, oldestMin: 214,
      items: [
        { kind: "receipt", id: 4101, userId: 1, name: "مریم کاظمی", amount: 250000,
          plan: "سه ماهه ۱۰۰ گیگ", at: "2026-09-17 08:02", waitedMin: 214, hasPhoto: true },
        { kind: "message", id: 1, userId: 1, name: "مریم کاظمی", count: 2,
          body: "ممنون، دوباره واریز کردم", at: "2026-09-17 09:40", waitedMin: 96 },
        { kind: "receipt", id: 4103, userId: 2, name: "علی رضایی", amount: 120000,
          plan: "یک ماهه", at: "2026-09-17 10:55", waitedMin: 41, hasPhoto: false },
        { kind: "receipt", id: 4104, userId: 3, name: "سارا نیک‌پور", amount: 480000,
          plan: "شش ماهه", at: "2026-09-17 11:30", waitedMin: 6, hasPhoto: true },
      ],
    };
    if (u.indexOf("/admin/channel/suggestions") >= 0) {
      /* هر سه شکل باید دیده شود: فرصت، فوریت، و خرابی. با فهرستِ
         خالی صفحه شاخه‌ی «چیزی نیست» را می‌گیرد و سالم به نظر
         می‌رسد. */
      return { suggestions: [
        { id: "failed", kind: "fix", title: "پستِ نافرجام را ببینید",
          why: "۱ پست فرستاده نشده", body: "" },
        { id: "disc:OFF30", kind: "draft", title: "اعلامِ کدِ OFF30",
          why: "کدِ OFF30 ساخته شده و هیچ‌وقت در کانال اعلام نشده",
          body: "🎟 <b>کدِ تخفیف</b>\n\nکدِ <code>OFF30</code> را موقعِ خرید بزنید و <b>۳۰٪</b> کمتر بپردازید." },
        { id: "expiry:2026-09-20", kind: "draft", title: "یادآوریِ تمدید",
          why: "۲۳ اشتراک در هفت روزِ آینده تمام می‌شود",
          body: "⏰ <b>اشتراکتان دارد تمام می‌شود؟</b>\n\nتمدید یک دکمه است." },
        { id: "quiet:2026-W38", kind: "draft", title: "یک پستِ آموزشی بگذارید",
          why: "۹ روز است پستی نگذاشته‌اید",
          body: "📚 <b>نصب در سه قدم</b>" },
      ] };
    }
    if (u.indexOf("/admin/channel/dismiss") >= 0) return { ok: true };
    if (u.indexOf("/admin/channel/ai-image") >= 0) {
      return { ok: true, photo: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==" };
    }
    if (u.indexOf("/admin/channel/ai") >= 0) {
      if (method === "POST") {
        return { ok: true, text: "🎉 <b>تخفیفِ آخر هفته</b>\n\nتا یکشنبه با کدِ <code>OFF30</code> سی درصد کمتر بپردازید." };
      }
      return { ready: true, why: "", hasKey: true, model: "demo-1",
               baseUrl: "https://api.example.test/v1",
               imageUrl: "https://img.example.test/p/{q}", tone: "صمیمی و کوتاه",
               enabled: true };
    }
    if (u.indexOf("/admin/channel/check") >= 0) {
      /* همان قاعده‌ای که بک‌اند دارد، فقط برای دیدنِ صفحه:
         تگِ بازمانده و سقفِ کپشن. */
      var cb = String((body || {}).body || "");
      var probs = [];
      var opens = (cb.match(/<(b|i|u|s|code|blockquote|tg-spoiler)>/g) || []).length;
      var closes = (cb.match(/<\/(b|i|u|s|code|blockquote|tg-spoiler)>/g) || []).length;
      if (opens > closes) probs.push("تگی بسته نشده");
      var lim = (body || {}).photo ? 1024 : 4096;
      if (cb.length > lim) probs.push("متن " + cb.length + " کاراکتر است؛ سقف " + lim);
      return { ok: !probs.length, problems: probs, limit: lim };
    }
    if (u.indexOf("/admin/channel/post") >= 0) {
      if (method === "DELETE") return { ok: true };
      return { ok: true, post: { id: 99, status: (body || {}).at ? "queued" : "sent" } };
    }
    if (u.indexOf("/admin/channel") >= 0) {
      return {
        target: "@nexora_vpn",
        limits: { text: 4096, caption: 1024 },
        posts: [
          { id: 3, body: "📦 <b>پلن‌های نکسورا</b>\n\n• استاندارد — ۲۵۰,۰۰۰ تومان",
            status: "sent", photo: null, sent_at: "2026-09-18 10:02",
            message_id: 812 },
          { id: 2, body: "⏰ <b>اشتراکتان دارد تمام می‌شود؟</b> تمدید یک دکمه است.",
            status: "queued", photo: "x.jpg", scheduled_at: "2026-09-21 10:00" },
          { id: 1, body: "🔌 وصل نمی‌شوید؟ یک سرورِ دیگر را امتحان کنید.",
            status: "failed", photo: null, created_at: "2026-09-17 21:40",
            error: "ربات در کانال نیست — اول اضافه‌اش کنید و ادمینش کنید" },
        ],
      };
    }
    if (u.indexOf("/admin/bot/inbox/send") >= 0) {
      /* پیام واقعاً اضافه شود.
         با `{ok:true}` خالی، حبابِ خوش‌بینانه بعد از خواندنِ دوباره
         ناپدید می‌شد و هارنس حالتی را نشان می‌داد که سرورِ واقعی
         ندارد — یعنی باگی که نیست. */
      var ab = ((body || {}).body || "").trim();
      if (!ab) { var ae = new Error("پیام خالی است"); ae.status = 400; throw ae; }
      A_THREAD.messages.push({ id: A_THREAD.messages.length + 1, from: "admin",
                               body: ab, orderId: null,
                               at: new Date().toISOString().slice(0, 16).replace("T", " "),
                               read: false });
      return { ok: true };
    }
    if (u.indexOf("/admin/bot/inbox") >= 0) {
      return u.indexOf("user_id=") >= 0 ? A_THREAD : A_INBOX;
    }
    if (u.indexOf("/mini/inbox/send") >= 0) return inboxSend(body);
    if (u.indexOf("/mini/inbox/read") >= 0) { M_INBOX.unread = 0; M_PING.unread = 0; return { ok: true }; }
    if (u.indexOf("/mini/inbox") >= 0) return M_INBOX;
    if (u.indexOf("/mini/ping") >= 0) return M_PING;
    if (u.indexOf("/receipt") >= 0) return miniReceipt(u, body);
    if (u.indexOf("/mini/orders") >= 0) return M_ORDERS;
    if (u.indexOf("/mini/order") >= 0) return miniOrder(body);
    if (u.indexOf("/mini/buy") >= 0) return miniBuy(body);
    if (u.indexOf("/admin/bot/events") >= 0) {
      var onlyErr = u.indexOf("errors=1") >= 0;
      var pg = 1;
      var mPg = u.match(/page=(\d+)/);
      if (mPg) pg = parseInt(mPg[1], 10) || 1;
      var rows = onlyErr
        ? EVENTS.filter(function (e) { return e.level === "error"; })
        : EVENTS;
      return {
        ready: true,
        total: onlyErr ? 41 : 214,
        page: pg,
        per: 30,
        events: rows,
        kinds: EVENT_KINDS,
      };
    }
    if (u.indexOf("/admin/bot/discounts") >= 0) {
      if (method === "DELETE") return { ok: true };
      if (method === "POST") return { ok: true, code: (body || {}).code };
      return D_CODES;
    }
    if (u.indexOf("/mini/discount") >= 0) {
      var dc = String((body || {}).code || "").toUpperCase();
      if (dc !== "NOWRUZ") {
        var de = new Error("کد تخفیف پیدا نشد"); de.status = 400; throw de;
      }
      return { ok: true, percent: 25, price: 90000, off: 30000, base: 120000 };
    }
    if (u.indexOf("/mini/rewards") >= 0) return M_REWARDS;
    if (u.indexOf("/mini/me") >= 0) return M_ME;
    if (u.indexOf("/mini/subs") >= 0) return M_SUBS;
    if (u.indexOf("/mini/plans") >= 0) return M_PLANS;
    if (u.indexOf("/portal/theme/buy") >= 0) {
      P_THEME.open = true;
      P_THEME.until = "1405-08-22T12:00:00";
      return { ok: true, until: P_THEME.until, paid: P_THEME.price };
    }
    if (u.indexOf("/portal/brand") >= 0) {
      P_THEME.brand = (body || {}).brand || P_THEME.brand;
      return { ok: true };
    }
    if (u.indexOf("/portal/logo") >= 0) {
      P_THEME.logo = method === "DELETE" ? "" : FAKE_LOGO;
      return { ok: true };
    }
    if (u.indexOf("/portal/theme") >= 0) {
      if (method === "POST") {
        if (!P_THEME.open) { var te = new Error("پوسته‌ی شخصی برای شما فعال نیست — اول تهیه‌اش کنید"); te.status = 402; throw te; }
        var tb = body || {};
        if ("accent" in tb) P_THEME.accent = tb.accent || "";
        if (tb.tpl) P_THEME.tpl = tb.tpl;
        if (tb.palette) P_THEME.palette = tb.palette;
        if (tb.logo_style) P_THEME.logoStyle = tb.logo_style;
        return { ok: true };
      }
      return P_THEME;
    }
    if (u.indexOf("/portal/plan-cost") >= 0) {
      // همان شکلی که بکند می‌دهد: کف از نرخ پایه × ماه + کاربر اضافه
      return { rows: ((body || {}).rows || []).map(function (r) {
        var gb = Number(r.gb) || 0, days = Number(r.days) || 0;
        var ips = Number(r.ip_limit) || 0;
        var base = gb === 0 ? 200000 : gb * 2000;
        var months = Math.max(1, Math.round((days || 30) / 30));
        var per = 15000, extra = Math.max(0, ips - 1);
        return { ready: true, cost: (base + per * extra) * months,
                 base: base, perDevice: per, extraDevices: extra,
                 months: months, estimated: !days };
      }) };
    }
    if (u.indexOf("/portal/me") >= 0) return Object.assign({}, P_ME, pReady());
    if (u.indexOf("/portal/users") >= 0) {
      var pq = (u.match(/[?&]q=([^&]*)/) || [])[1];
      pq = pq ? decodeURIComponent(pq) : "";
      var pl = P_USERS.users.filter(function (x) {
        return !pq || (x.first_name + " " + x.username + " " + x.tg_id).indexOf(pq) >= 0;
      });
      return { users: pl, total: pq ? pl.length : P_USERS.total, dbReady: true,
               counts: P_USERS.counts };
    }
    if (u.indexOf("/portal/subscriber/") >= 0) return P_SUB;
    if (u.indexOf("/portal/message/") >= 0) return { ok: true };
    if (u.indexOf("/portal/inbox/send") >= 0) {
      var pb = ((body || {}).body || "").trim();
      if (!pb && !(body || {}).photo) { var pe = new Error("پیام خالی است"); pe.status = 400; throw pe; }
      P_THREAD.messages.push({ id: P_THREAD.messages.length + 1, from: "admin", body: pb,
                               photo: (body || {}).photo || "", orderId: null,
                               at: new Date().toISOString().slice(0, 16).replace("T", " "),
                               read: false });
      return { ok: true };
    }
    if (u.indexOf("/portal/inbox") >= 0) {
      if (NEW_RESELLER) return u.indexOf("user_id=") >= 0 ? { messages: [] } : { threads: [], unread: 0 };
      if (!P_THREAD.messages[2].photo) P_THREAD.messages[2].photo = FAKE_SHOT;
      return u.indexOf("user_id=") >= 0 ? P_THREAD : P_INBOX;
    }
    if (u.indexOf("/portal/funnel") >= 0) {
      if (NEW_RESELLER) return { ready: true, started: 0, steps: [], segments: {} };
      return { ready: true, started: 62, steps: [
        { label: "ربات را باز کردند", n: 62, pct: 100 },
        { label: "شماره ثبت کردند", n: 29, pct: 46.8 },
        { label: "سفارش ثبت کردند", n: 47, pct: 75.8 },
        { label: "خرید موفق", n: 41, pct: 66.1 }],
        segments: { paid: 41, trialOnly: 8, trial: 19, idle: 13 } };
    }
    if (u.indexOf("/portal/events") >= 0) {
      return { ready: true, total: 3, page: 1, per: 30, kinds: EVENT_KINDS,
               events: EVENTS.slice(0, 3) };
    }
    if (u.indexOf("/portal/bot-settings") >= 0) {
      if (method === "PUT") {
        var ps = (body || {}).settings || {};
        if (ps.order_ttl_minutes !== undefined
            && (ps.order_ttl_minutes < 5 || ps.order_ttl_minutes > 1440)) {
          var pe2 = new Error("«مهلت پرداخت» باید بین 5 و 1440 باشد"); pe2.status = 400; throw pe2;
        }
        Object.keys(ps).forEach(function (k) { P_SETTINGS.settings[k] = ps[k]; });
        return { ok: true, saved: Object.keys(ps) };
      }
      return P_SETTINGS;
    }
    if (u.indexOf("/portal/cards") >= 0) {
      if (method === "PUT") {
        P_CARDS = ((body || {}).cards || []).filter(function (c) { return c && c.number; });
        return { ok: true, count: P_CARDS.length,
                 active: P_CARDS.filter(function (c) { return c.active; }).length };
      }
      return { cards: P_CARDS };
    }
    if (u.indexOf("/portal/bot/link") >= 0) {
      if (method === "DELETE") { P_LINKED = false; return { ok: true }; }
      return { ok: true, minutes: 30,
               url: "https://t.me/hossein_vpn_bot?start=own_Hx7Kq2mZpL9wR4tY" };
    }
    if (u.indexOf("/portal/summary") >= 0) return P_SUMMARY;
    if (u.indexOf("/portal/configs") >= 0) return P_CONFIGS;
    if (u.indexOf("/portal/stats") >= 0) return P_STATS;
    if (u.indexOf("/portal/bot-plans") >= 0) {
      // نماینده‌ی تازه — همان حالتی که تا امروز بن‌بست بود و در
      // هارنس هیچ‌وقت دیده نمی‌شد، چون داده‌ی ساختگی همیشه دو پلن
      // داشت.
      if (NEW_RESELLER) return Object.assign({}, P_BOT_PLANS, { plans: [] });
      return P_BOT_PLANS;
    }
    if (u.indexOf("/portal/plans") >= 0) return P_PLANS;
    if (u.indexOf("/portal/orders") >= 0) return portalOrders(u);
    if (u.indexOf("/portal/bot") >= 0) {
      return Object.assign({ hasBot: true, username: "hossein_vpn_bot",
                             brand: "وی‌پی‌ان حسین", supportUsername: "hsupport",
                             channelUsername: "" }, pReady());
    }
    if (u.indexOf("/bot/inbounds") >= 0) return INBOUNDS;
    if (u.indexOf("/tenant/portal-list") >= 0) return PORTAL_LIST;
    if (u.indexOf("/billing/clients") >= 0) return CLIENTS;
    if (u.indexOf("/billing/invoice") >= 0) return INVOICE;
    if (u.indexOf("/firewall/intrusion") >= 0) return INTRUSION;
    if (u.indexOf("/firewall") >= 0) return FIREWALL;
    if (u.indexOf("/tunnel/overview") >= 0 || u.indexOf("/tunnel") >= 0) return TUNNEL;
    if (u.indexOf("/affiliates") >= 0) return AFFILIATES;
    if (u.indexOf("/monitor") >= 0 || u.indexOf("/nodes") >= 0) return MONITOR;
    if (u.indexOf("/admin/themes") >= 0) {
      if (method === "POST") {
        THEMES.currentTemplate = (body || {}).template || THEMES.currentTemplate;
        THEMES.currentPalette = (body || {}).palette || THEMES.currentPalette;
        return { ok: true, template: THEMES.currentTemplate,
                 palette: THEMES.currentPalette };
      }
      return THEMES;
    }
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
    var body = null;
    try { body = opt && opt.body ? JSON.parse(opt.body) : null; } catch (e) { body = null; }

    // مسیرهای خطا هم باید دیده شوند. تا وقتی هارنس همیشه ۲۰۰
    // برمی‌گرداند، «موجودی کافی نیست» هیچ‌وقت روی صفحه نمی‌آید و
    // کسی نمی‌فهمد آن حالت چه شکلی است.
    var data, status = 200;
    try {
      data = byPath(u, body, String((opt && opt.method) || "GET").toUpperCase());
    } catch (e) {
      status = e.status || 500;
      data = { detail: e.message || "خطا" };
    }
    /* هدرها هم باید باشند. بدون اینها، کدی که یک هدرِ اختیاری
       می‌خواند روی هارنس خطا می‌داد و هارنس حالتی را نشان می‌داد
       که سرورِ واقعی هیچ‌وقت ندارد. */
    var HDR = { "x-config-version": "7" };
    return Promise.resolve({
      ok: status < 400, status: status,
      headers: { get: function (k) { return HDR[String(k).toLowerCase()] || null; } },
      json: function () { return Promise.resolve(data); },
      text: function () { return Promise.resolve(""); },
    });
  };
})();
