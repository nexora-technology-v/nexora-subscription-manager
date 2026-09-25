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
  // پیش‌نمایشِ زنده‌ی صفحه‌ی اشتراک از هارنسِ خودِ آن صفحه (make-subpage-harness)
  window.NX_PREVIEW_URL = "/sub.html";
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

  // قالب‌ها و پالت‌ها — عیناً TEMPLATES و PALETTESِ بکند (app.py).
  // نسخه‌ی قبلی دست‌ساز بود: نامِ فارسی و توضیح نداشت و پالت‌هایش
  // («نعنایی») اصلاً در بکند نبودند.
  var THEMES = {
    currentTemplate: "classic",
    currentPalette: "ocean",
    templates: [
      {
        "id": "classic",
        "name": "Classic",
        "fa": "کلاسیک",
        "desc": "ظاهر پیش‌فرض — ساده و آشنا"
      },
      {
        "id": "analytics",
        "name": "Analytics",
        "fa": "تحلیلی",
        "desc": "کارت‌های آماری برجسته با حاشیه‌های رنگی"
      },
      {
        "id": "wallet",
        "name": "Wallet",
        "fa": "کیف پول",
        "desc": "کارت اصلی گرادینتی + دکمه‌های گرد"
      },
      {
        "id": "console",
        "name": "Console",
        "fa": "کنسول",
        "desc": "حس ترمینال — مونواسپیس و گوشه‌های تیز"
      }
    ],
    palettes: [
      {
        "id": "ocean",
        "name": "Ocean",
        "fa": "اقیانوس",
        "builtin": true,
        "vars": {
          "accent": "#2B7FD6",
          "accent2": "#5AA9E6",
          "bg": "#06090F",
          "surface": "#0D1420",
          "surfaceAlt": "#0A0E17",
          "border": "rgba(255,255,255,0.06)",
          "text": "#E8EEF7",
          "textMuted": "#5A6880"
        }
      },
      {
        "id": "violet",
        "name": "Violet",
        "fa": "بنفش",
        "builtin": true,
        "vars": {
          "accent": "#8B5CF6",
          "accent2": "#C084FC",
          "bg": "#0A0713",
          "surface": "#150F26",
          "surfaceAlt": "#0F0A1C",
          "border": "rgba(255,255,255,0.07)",
          "text": "#EDE9F7",
          "textMuted": "#6B6188"
        }
      },
      {
        "id": "ember",
        "name": "Ember",
        "fa": "آتشین",
        "builtin": true,
        "vars": {
          "accent": "#F97316",
          "accent2": "#FB923C",
          "bg": "#0C0906",
          "surface": "#181109",
          "surfaceAlt": "#120C07",
          "border": "rgba(255,255,255,0.07)",
          "text": "#FBEDE6",
          "textMuted": "#8F7365"
        }
      },
      {
        "id": "forest",
        "name": "Forest",
        "fa": "جنگل",
        "builtin": true,
        "vars": {
          "accent": "#10B981",
          "accent2": "#34D399",
          "bg": "#04100C",
          "surface": "#0A1D16",
          "surfaceAlt": "#071711",
          "border": "rgba(255,255,255,0.06)",
          "text": "#E4F7EF",
          "textMuted": "#5A806F"
        }
      },
      {
        "id": "rose",
        "name": "Rose",
        "fa": "رز",
        "builtin": true,
        "vars": {
          "accent": "#EC4899",
          "accent2": "#F472B6",
          "bg": "#0E060B",
          "surface": "#1B0D16",
          "surfaceAlt": "#150A11",
          "border": "rgba(255,255,255,0.07)",
          "text": "#FDF2FA",
          "textMuted": "#8B6F80"
        }
      },
      {
        "id": "gold",
        "name": "Gold",
        "fa": "طلایی",
        "builtin": true,
        "vars": {
          "accent": "#D4AF37",
          "accent2": "#E8C766",
          "bg": "#0C0A07",
          "surface": "#171310",
          "surfaceAlt": "#110E0B",
          "border": "rgba(212,175,55,0.16)",
          "text": "#F5EFE2",
          "textMuted": "#8F8371"
        }
      },
      {
        "id": "cyan",
        "name": "Cyan",
        "fa": "فیروزه‌ای",
        "builtin": true,
        "vars": {
          "accent": "#06B6D4",
          "accent2": "#22D3EE",
          "bg": "#04121A",
          "surface": "#0A2029",
          "surfaceAlt": "#071821",
          "border": "rgba(255,255,255,0.07)",
          "text": "#E0F5FA",
          "textMuted": "#6E96A3"
        }
      },
      {
        "id": "slate",
        "name": "Slate",
        "fa": "خاکستری",
        "builtin": true,
        "vars": {
          "accent": "#94A3B8",
          "accent2": "#CBD5E1",
          "bg": "#0B0C0F",
          "surface": "#14161B",
          "surfaceAlt": "#101216",
          "border": "rgba(255,255,255,0.09)",
          "text": "#F1F5F9",
          "textMuted": "#6B7480"
        }
      }
    ],
    customPalettes: [],
  };

  /* پیکربندیِ صفحه‌ی اشتراک = پیش‌فرضِ خودِ بکند (app.DEFAULT_CONFIG)
     + داده‌ی نمونه‌ی واقع‌نما روی آن.

     نسخه‌ی قبلی شیءِ دست‌سازی بود که `advanced`، `popup`، `banners`،
     `template` و `palette` را اصلاً نداشت و واسطه‌هایش `{name, slug}`
     بودند، نه `{domains, emailPrefix, overrides}` — پس صفحه‌های تنظیمات و
     واسطه‌ها در هارنس شاخه‌ای را نشان می‌دادند که روی سرور نیست.
     test-contract.py این شکل را با بکند می‌سنجد. */
  var CONFIG_DEFAULT = {
    "downloadApps": {
      "android": [
        {
          "id": "happ",
          "name": "Happ",
          "url": "https://github.com/Happ-proxy/happ-android/releases/download/3.26.3/Happ.apk",
          "recommended": true,
          "icon": "bolt",
          "scheme": "happ"
        },
        {
          "id": "v2rayng",
          "name": "v2rayNG",
          "url": "https://github.com/2dust/v2rayNG/releases/download/2.2.6/v2rayNG_2.2.6_arm64-v8a.apk",
          "recommended": false,
          "icon": "paper-plane",
          "scheme": "v2rayng"
        }
      ],
      "ios": [
        {
          "id": "happ",
          "name": "Happ",
          "url": "https://apps.apple.com/us/app/happ-proxy-utility/id6504287215",
          "recommended": true,
          "icon": "bolt",
          "scheme": "happ"
        },
        {
          "id": "v2box",
          "name": "V2Box",
          "url": "https://apps.apple.com/us/app/v2box-v2ray-client/id6446814690",
          "recommended": false,
          "icon": "shield-halved",
          "scheme": "v2box"
        }
      ],
      "desktop": [
        {
          "id": "happ",
          "name": "Happ (Windows)",
          "url": "https://github.com/Happ-proxy/happ-desktop/releases/download/3.3.6/setup-Happ.x64.exe",
          "recommended": true,
          "icon": "bolt",
          "scheme": "happ"
        },
        {
          "id": "v2rayn",
          "name": "v2rayN (Windows)",
          "url": "https://github.com/2dust/v2rayN/releases/download/7.24.1/v2rayN-windows-arm64.zip",
          "recommended": false,
          "icon": "box-open",
          "scheme": "none"
        }
      ]
    },
    "faq": {
      "fa": [
        {
          "q": "چرا نمی‌توانم وصل شوم؟",
          "a": "اول مطمئن شوید آخرین نسخه‌ی اپ پیشنهادی (Happ) را نصب کرده‌اید و کانفیگ را درست وارد کرده‌اید."
        },
        {
          "q": "چطور اشتراکم را تمدید کنم؟",
          "a": "روی دکمه‌ی «تمدید ساب» در داشبورد بزنید یا مستقیم به پشتیبانی پیام دهید."
        }
      ],
      "en": [
        {
          "q": "Why can't I connect?",
          "a": "Make sure you've installed the latest version of our recommended app (Happ)."
        }
      ],
      "tr": [],
      "ar": []
    },
    "banners": {
      "enabled": true,
      "lowQuotaDaysThreshold": 3,
      "lowQuotaPercentThreshold": 15,
      "disabledTitle": "",
      "disabledDesc": "",
      "disabledButtonText": "",
      "lowQuotaTitle": "",
      "lowQuotaDescDays": "",
      "lowQuotaDescVolume": "",
      "lowQuotaButtonText": "",
      "lowQuotaButtonUrl": ""
    },
    "referral": {
      "enabled": true
    },
    "links": {
      "supportUsername": "crm_nexoravpn",
      "channelUsername": "yanexoravpn"
    },
    "videoTutorialUrl": null,
    "videos": [],
    "advanced": {
      "brandName": "NEXORA",
      "pageTitle": "Nexora | مدیریت اشتراک",
      "accentColor": "#2B7FD6",
      "accentColor2": "#5AA9E6",
      "defaultLanguage": "fa",
      "defaultTheme": "dark",
      "showNotificationPopup": true,
      "notificationDelaySeconds": 10,
      "showBrandStrip": true,
      "showReferralCard": true,
      "showFaqSection": true,
      "customCss": "",
      "customFooterText": "",
      "allowThemeToggle": true,
      "allowLanguageToggle": true,
      "hideConfigsList": false
    },
    "popup": {
      "enabled": true,
      "delaySeconds": 10,
      "icon": "🔔",
      "title": "آیا مشکلی در اتصال کانفیگ دارید؟",
      "description": "پیشنهاد می‌کنیم از برنامه‌ی Happ استفاده کنید؛ در غیر این صورت به پشتیبانی پیام بدهید",
      "primaryButtonText": "پشتیبانی",
      "primaryButtonUrl": "",
      "dismissButtonText": "خیر",
      "autoCloseSeconds": 15
    },
    "bot": {
      "enabled": false,
      "token": "",
      "adminChatId": "",
      "welcomeMessage": "سلام! به ربات Nexora خوش آمدید 👋",
      "notifyOnPurchase": true,
      "notifyOnExpiry": true,
      "expiryReminderDays": 3
    },
    "resellers": [],
    "template": "classic",
    "palette": "ocean",
    "customPalettes": []
  };
  var deepMerge = function (base, over) {
    var out = JSON.parse(JSON.stringify(base)), k;
    for (k in over) {
      if (over[k] && typeof over[k] === "object" && !Array.isArray(over[k])
          && out[k] && typeof out[k] === "object" && !Array.isArray(out[k])) {
        out[k] = deepMerge(out[k], over[k]);
      } else { out[k] = over[k]; }
    }
    return out;
  };
  var CONFIG = deepMerge(CONFIG_DEFAULT, {
    links: { channelUsername: "nexora_vpn", supportUsername: "nexora_sup" },
    faq: {
      fa: [{ q: "چرا نمی‌توانم وصل شوم؟", a: "اول مطمئن شوید آخرین نسخه‌ی Happ را نصب کرده‌اید." },
           { q: "حجمم تمام شد، چه کنم؟", a: "از داخل ربات یا دکمه‌ی «تمدید ساب» تمدید کنید." },
           { q: "روی چند دستگاه می‌شود وصل شد؟", a: "به تعدادِ کاربرِ پلنتان." }],
      en: [{ q: "How do I connect?", a: "Install Happ and add the link." }], tr: [], ar: [],
    },
    videos: [{ id: "v1", title: "نصب روی اندروید", url: "https://t.me/nexora_vpn/41", platform: "android" },
             { id: "v2", title: "نصب روی آیفون", url: "https://t.me/nexora_vpn/42", platform: "ios" }],
    resellers: [
      { id: "r1", name: "حسین", enabled: true, domains: ["sub.hossein-vpn.ir"], emailPrefix: "hossein_",
        overrides: { advanced: { brandName: "حسین VPN", accentColor: "#E84393", accentColor2: "#F48FB1" },
                     links: { supportUsername: "hsupport", channelUsername: "hossein_vpn" } } },
      { id: "r2", name: "مهدی", enabled: true, domains: [], emailPrefix: "mahdi_",
        overrides: { advanced: { brandName: "MAHDI NET" } } },
      { id: "r3", name: "سارا", enabled: false, domains: ["sara-net.ir"], emailPrefix: "",
        overrides: {} },
    ],
    referral: { enabled: false },
  });

  var REPORT = {
    ready: true, days: 30,
    users: { users: 1284, newUsers: 96, blocked: 4, withPhone: 812 },
    orders: { approved: 61, rejected: 3, pending: 5, revenue: 18400000, avg: 301639 },
    subs: { total: 412, active: 355, expiringSoon: 18 },
    buyers: [
      { tg_id: 11, first_name: "مریم کاظمی", username: "maryam_k", phone: "989121110011", orders: 4, spent: 1240000, lastBuy: "2026-09-22 14:10:00" },
      { tg_id: 12, first_name: "حسین نوری", username: "", phone: "989351220012", orders: 3, spent: 940000, lastBuy: "2026-09-20 09:31:00" },
      { tg_id: 13, first_name: "سارا احمدی", username: "sara_a", phone: "", orders: 2, spent: 610000, lastBuy: "2026-09-18 21:05:00" },
      { tg_id: 14, first_name: "امیر صادقی", username: "amir_s", phone: "989191440014", orders: 2, spent: 480000, lastBuy: "2026-09-11 11:44:00" },
      { tg_id: 15, first_name: "رضا جعفری", username: "", phone: "", orders: 1, spent: 320000, lastBuy: "2026-09-02 17:20:00" },
    ],
    buyerCount: 24, conversion: 25,
    daily: (function () {
      var a = [], i;
      for (i = 0; i < 30; i++) {
        // صفرِ پیشوند — بکند «2026-08-01» می‌دهد؛ «2026-08-1» تبدیلِ شمسی را رد می‌کرد
        a.push({ day: "2026-08-" + String(i + 1).padStart(2, "0"),
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

  /* ربات — خروجیِ خودِ بکند روی فیکسچرِ test-contract با داده‌ی غنی‌تر
     (p_hbot). پیش‌تر شکل‌ها ساختگی بودند: سفارش «plan» داشت و
     plan_name نه، کاربران counts نداشتند، وضعیت «connected» می‌گفت. */
  var ORDERS = {
   "orders": [
    {
     "id": 3,
     "tenant_id": 1,
     "user_id": 3,
     "plan_id": 3,
     "kind": "new",
     "amount": 280000,
     "base_amount": 280000,
     "coins_used": 0,
     "discount_code": null,
     "discount_pct": 0,
     "paid_from": "card",
     "status": "awaiting",
     "receipt_type": "photo",
     "receipt_file": "AgACAgQAAxkBAAIB",
     "receipt_text": null,
     "card_used": null,
     "admin_note": null,
     "reviewed_by": null,
     "sub_id": null,
     "created_at": "2026-09-25 02:12:52",
     "expires_at": "2026-09-25T03:00:52",
     "reviewed_at": null,
     "renew_sub_id": null,
     "first_name": "مریم کاظمی",
     "username": null,
     "tg_id": 2000,
     "plan_name": "سه‌ماهه",
     "plan_is_trial": 0
    },
    {
     "id": 4,
     "tenant_id": 1,
     "user_id": 4,
     "plan_id": 1,
     "kind": "renew",
     "amount": 100000,
     "base_amount": 100000,
     "coins_used": 0,
     "discount_code": null,
     "discount_pct": 0,
     "paid_from": "card",
     "status": "awaiting",
     "receipt_type": "text",
     "receipt_file": null,
     "receipt_text": "واریز شد از کارت ملت\nپیگیری ۴۸۲۹۱۷\nساعت ۱۴:۰۲",
     "card_used": null,
     "admin_note": null,
     "reviewed_by": null,
     "sub_id": null,
     "created_at": "2026-09-25 01:18:52",
     "expires_at": "2026-09-25T03:00:52",
     "reviewed_at": null,
     "renew_sub_id": null,
     "first_name": "حسین نوری",
     "username": "user4",
     "tg_id": 2001,
     "plan_name": "یک‌ماهه",
     "plan_is_trial": 0
    },
    {
     "id": 5,
     "tenant_id": 1,
     "user_id": 6,
     "plan_id": 4,
     "kind": "new",
     "amount": 456000,
     "base_amount": 480000,
     "coins_used": 24,
     "discount_code": null,
     "discount_pct": 5,
     "paid_from": "card",
     "status": "awaiting",
     "receipt_type": "photo",
     "receipt_file": "AgACAgQAAxkBAAIB",
     "receipt_text": null,
     "card_used": null,
     "admin_note": null,
     "reviewed_by": null,
     "sub_id": null,
     "created_at": "2026-09-25 00:00:52",
     "expires_at": "2026-09-25T03:00:52",
     "reviewed_at": null,
     "renew_sub_id": null,
     "first_name": "امیر صادقی",
     "username": null,
     "tg_id": 2003,
     "plan_name": "شش‌ماهه",
     "plan_is_trial": 0
    },
    {
     "id": 1,
     "tenant_id": 1,
     "user_id": 1,
     "plan_id": 1,
     "kind": "new",
     "amount": 100000,
     "base_amount": 100000,
     "coins_used": 0,
     "discount_code": null,
     "discount_pct": 0,
     "paid_from": "card",
     "status": "approved",
     "receipt_type": null,
     "receipt_file": null,
     "receipt_text": null,
     "card_used": null,
     "admin_note": null,
     "reviewed_by": null,
     "sub_id": null,
     "created_at": "2026-09-24 23:00:50",
     "expires_at": "2026-09-25T03:00:50",
     "reviewed_at": null,
     "renew_sub_id": null,
     "first_name": "علی",
     "username": "ali",
     "tg_id": 1001,
     "plan_name": "یک‌ماهه",
     "plan_is_trial": 0
    },
    {
     "id": 2,
     "tenant_id": 1,
     "user_id": 1,
     "plan_id": 1,
     "kind": "new",
     "amount": 100000,
     "base_amount": 100000,
     "coins_used": 0,
     "discount_code": null,
     "discount_pct": 0,
     "paid_from": "card",
     "status": "awaiting",
     "receipt_type": null,
     "receipt_file": null,
     "receipt_text": null,
     "card_used": null,
     "admin_note": null,
     "reviewed_by": null,
     "sub_id": null,
     "created_at": "2026-09-24 23:00:50",
     "expires_at": "2026-09-25T03:00:50",
     "reviewed_at": null,
     "renew_sub_id": null,
     "first_name": "علی",
     "username": "ali",
     "tg_id": 1001,
     "plan_name": "یک‌ماهه",
     "plan_is_trial": 0
    },
    {
     "id": 6,
     "tenant_id": 1,
     "user_id": 7,
     "plan_id": null,
     "kind": "topup",
     "amount": 200000,
     "base_amount": 200000,
     "coins_used": 0,
     "discount_code": null,
     "discount_pct": 0,
     "paid_from": "card",
     "status": "review",
     "receipt_type": "photo",
     "receipt_file": "AgACAgQAAxkBAAIB",
     "receipt_text": null,
     "card_used": null,
     "admin_note": null,
     "reviewed_by": null,
     "sub_id": null,
     "created_at": "2026-09-24 21:30:52",
     "expires_at": "2026-09-25T03:00:53",
     "reviewed_at": null,
     "renew_sub_id": null,
     "first_name": "نگار احمدی",
     "username": "user7",
     "tg_id": 2004,
     "plan_name": null,
     "plan_is_trial": 0
    },
    {
     "id": 7,
     "tenant_id": 1,
     "user_id": 5,
     "plan_id": 3,
     "kind": "new",
     "amount": 280000,
     "base_amount": 280000,
     "coins_used": 0,
     "discount_code": null,
     "discount_pct": 0,
     "paid_from": "wallet",
     "status": "approved",
     "receipt_type": null,
     "receipt_file": null,
     "receipt_text": null,
     "card_used": null,
     "admin_note": null,
     "reviewed_by": null,
     "sub_id": null,
     "created_at": "2026-09-24 06:30:52",
     "expires_at": "2026-09-25T03:00:53",
     "reviewed_at": null,
     "renew_sub_id": null,
     "first_name": "زهرا مرادی",
     "username": "user5",
     "tg_id": 2002,
     "plan_name": "سه‌ماهه",
     "plan_is_trial": 0
    },
    {
     "id": 11,
     "tenant_id": 1,
     "user_id": 12,
     "plan_id": 4,
     "kind": "new",
     "amount": 480000,
     "base_amount": 480000,
     "coins_used": 0,
     "discount_code": null,
     "discount_pct": 0,
     "paid_from": "card",
     "status": "rejected",
     "receipt_type": "photo",
     "receipt_file": "AgACAgQAAxkBAAIB",
     "receipt_text": null,
     "card_used": null,
     "admin_note": "مبلغ واریزی با مبلغ سفارش مطابقت ندارد.",
     "reviewed_by": null,
     "sub_id": null,
     "created_at": "2026-09-24 00:30:52",
     "expires_at": "2026-09-25T03:00:53",
     "reviewed_at": null,
     "renew_sub_id": null,
     "first_name": "رضا قاسمی",
     "username": null,
     "tg_id": 2009,
     "plan_name": "شش‌ماهه",
     "plan_is_trial": 0
    },
    {
     "id": 8,
     "tenant_id": 1,
     "user_id": 8,
     "plan_id": 1,
     "kind": "new",
     "amount": 100000,
     "base_amount": 100000,
     "coins_used": 0,
     "discount_code": null,
     "discount_pct": 0,
     "paid_from": "card",
     "status": "approved",
     "receipt_type": "photo",
     "receipt_file": "AgACAgQAAxkBAAIB",
     "receipt_text": null,
     "card_used": null,
     "admin_note": null,
     "reviewed_by": null,
     "sub_id": null,
     "created_at": "2026-09-23 20:30:52",
     "expires_at": "2026-09-25T03:00:53",
     "reviewed_at": null,
     "renew_sub_id": null,
     "first_name": "پویا کریمی",
     "username": "user8",
     "tg_id": 2005,
     "plan_name": "یک‌ماهه",
     "plan_is_trial": 0
    },
    {
     "id": 9,
     "tenant_id": 1,
     "user_id": 9,
     "plan_id": 3,
     "kind": "renew",
     "amount": 266000,
     "base_amount": 280000,
     "coins_used": 14,
     "discount_code": null,
     "discount_pct": 5,
     "paid_from": "card",
     "status": "approved",
     "receipt_type": "photo",
     "receipt_file": "AgACAgQAAxkBAAIB",
     "receipt_text": null,
     "card_used": null,
     "admin_note": null,
     "reviewed_by": null,
     "sub_id": null,
     "created_at": "2026-09-22 22:30:52",
     "expires_at": "2026-09-25T03:00:53",
     "reviewed_at": null,
     "renew_sub_id": null,
     "first_name": "سارا رحیمی",
     "username": null,
     "tg_id": 2006,
     "plan_name": "سه‌ماهه",
     "plan_is_trial": 0
    },
    {
     "id": 10,
     "tenant_id": 1,
     "user_id": 11,
     "plan_id": 2,
     "kind": "new",
     "amount": 0,
     "base_amount": 0,
     "coins_used": 0,
     "discount_code": null,
     "discount_pct": 0,
     "paid_from": "card",
     "status": "approved",
     "receipt_type": null,
     "receipt_file": null,
     "receipt_text": null,
     "card_used": null,
     "admin_note": null,
     "reviewed_by": null,
     "sub_id": null,
     "created_at": "2026-09-22 04:30:52",
     "expires_at": "2026-09-25T03:00:53",
     "reviewed_at": null,
     "renew_sub_id": null,
     "first_name": "لیلا حسینی",
     "username": "user11",
     "tg_id": 2008,
     "plan_name": "تست رایگان",
     "plan_is_trial": 1
    },
    {
     "id": 12,
     "tenant_id": 1,
     "user_id": 10,
     "plan_id": 1,
     "kind": "new",
     "amount": 100000,
     "base_amount": 100000,
     "coins_used": 0,
     "discount_code": null,
     "discount_pct": 0,
     "paid_from": "card",
     "status": "rejected",
     "receipt_type": "text",
     "receipt_file": null,
     "receipt_text": "پرداخت کردم",
     "card_used": null,
     "admin_note": "رسید معتبر تشخیص داده نشد.",
     "reviewed_by": null,
     "sub_id": null,
     "created_at": "2026-09-21 18:30:52",
     "expires_at": "2026-09-25T03:00:53",
     "reviewed_at": null,
     "renew_sub_id": null,
     "first_name": "مهدی جعفری",
     "username": "user10",
     "tg_id": 2007,
     "plan_name": "یک‌ماهه",
     "plan_is_trial": 0
    }
   ],
   "dbReady": true
  };

  var USERS = {
   "users": [
    {
     "id": 1,
     "tenant_id": 1,
     "tg_id": 1001,
     "username": "ali",
     "first_name": "علی",
     "phone": "989120000001",
     "balance": 50000,
     "coins": 12,
     "ref_code": "HCHSGZ",
     "referred_by": null,
     "is_blocked": 0,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-09-24 23:00:50",
     "last_seen": "2026-09-24 23:00:50",
     "affiliate_id": 1,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 1,
     "spent": 100000,
     "subsCount": 1,
     "activeSubs": 1
    },
    {
     "id": 2,
     "tenant_id": 1,
     "tg_id": 1002,
     "username": null,
     "first_name": "رضا",
     "phone": null,
     "balance": 0,
     "coins": 0,
     "ref_code": "QX7P9S",
     "referred_by": 1,
     "is_blocked": 0,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-09-24 23:00:50",
     "last_seen": "2026-09-24 23:00:50",
     "affiliate_id": null,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 0,
     "spent": 0,
     "subsCount": 0,
     "activeSubs": 0
    },
    {
     "id": 18,
     "tenant_id": 1,
     "tg_id": 2015,
     "username": null,
     "first_name": "بهراد اکبری",
     "phone": "989123118785",
     "balance": 0,
     "coins": 25,
     "ref_code": "7CF2QE",
     "referred_by": null,
     "is_blocked": 0,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-09-10 02:30:52",
     "last_seen": "2026-09-24 23:00:52",
     "affiliate_id": null,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 0,
     "spent": 0,
     "subsCount": 0,
     "activeSubs": 0
    },
    {
     "id": 17,
     "tenant_id": 1,
     "tg_id": 2014,
     "username": "user17",
     "first_name": "الهام رستمی",
     "phone": "989123110866",
     "balance": 180000,
     "coins": 18,
     "ref_code": "THV6VX",
     "referred_by": null,
     "is_blocked": 0,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-09-07 02:30:52",
     "last_seen": "2026-09-24 23:00:52",
     "affiliate_id": null,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 0,
     "spent": 0,
     "subsCount": 0,
     "activeSubs": 0
    },
    {
     "id": 16,
     "tenant_id": 1,
     "tg_id": 2013,
     "username": "user16",
     "first_name": "کیان محمدی",
     "phone": "989123102947",
     "balance": 135000,
     "coins": 11,
     "ref_code": "59X36Y",
     "referred_by": null,
     "is_blocked": 1,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-09-04 02:30:52",
     "last_seen": "2026-09-24 23:00:52",
     "affiliate_id": null,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 0,
     "spent": 0,
     "subsCount": 0,
     "activeSubs": 0
    },
    {
     "id": 15,
     "tenant_id": 1,
     "tg_id": 2012,
     "username": null,
     "first_name": "نیلوفر شریفی",
     "phone": null,
     "balance": 90000,
     "coins": 4,
     "ref_code": "29AE4G",
     "referred_by": null,
     "is_blocked": 0,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-09-01 02:30:52",
     "last_seen": "2026-09-24 23:00:52",
     "affiliate_id": null,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 0,
     "spent": 0,
     "subsCount": 0,
     "activeSubs": 0
    },
    {
     "id": 14,
     "tenant_id": 1,
     "tg_id": 2011,
     "username": "user14",
     "first_name": "علیرضا یزدانی",
     "phone": "989123087109",
     "balance": 45000,
     "coins": 37,
     "ref_code": "LV8LMS",
     "referred_by": 1,
     "is_blocked": 0,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-08-29 02:30:52",
     "last_seen": "2026-09-24 23:00:52",
     "affiliate_id": null,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 0,
     "spent": 0,
     "subsCount": 0,
     "activeSubs": 0
    },
    {
     "id": 13,
     "tenant_id": 1,
     "tg_id": 2010,
     "username": "user13",
     "first_name": "فاطمه موسوی",
     "phone": "989123079190",
     "balance": 0,
     "coins": 30,
     "ref_code": "MXLW56",
     "referred_by": null,
     "is_blocked": 0,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-08-26 02:30:52",
     "last_seen": "2026-09-24 23:00:52",
     "affiliate_id": null,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 0,
     "spent": 0,
     "subsCount": 1,
     "activeSubs": 0
    },
    {
     "id": 12,
     "tenant_id": 1,
     "tg_id": 2009,
     "username": null,
     "first_name": "رضا قاسمی",
     "phone": "989123071271",
     "balance": 180000,
     "coins": 23,
     "ref_code": "T386Y4",
     "referred_by": null,
     "is_blocked": 0,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-08-23 02:30:52",
     "last_seen": "2026-09-24 23:00:52",
     "affiliate_id": null,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 0,
     "spent": 0,
     "subsCount": 1,
     "activeSubs": 1
    },
    {
     "id": 11,
     "tenant_id": 1,
     "tg_id": 2008,
     "username": "user11",
     "first_name": "لیلا حسینی",
     "phone": null,
     "balance": 135000,
     "coins": 16,
     "ref_code": "9CASB9",
     "referred_by": null,
     "is_blocked": 0,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-08-20 02:30:52",
     "last_seen": "2026-09-24 23:00:52",
     "affiliate_id": null,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 0,
     "spent": 0,
     "subsCount": 1,
     "activeSubs": 1
    },
    {
     "id": 10,
     "tenant_id": 1,
     "tg_id": 2007,
     "username": "user10",
     "first_name": "مهدی جعفری",
     "phone": "989123055433",
     "balance": 90000,
     "coins": 9,
     "ref_code": "GSWH6L",
     "referred_by": 1,
     "is_blocked": 0,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-08-17 02:30:52",
     "last_seen": "2026-09-24 23:00:52",
     "affiliate_id": null,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 0,
     "spent": 0,
     "subsCount": 1,
     "activeSubs": 0
    },
    {
     "id": 9,
     "tenant_id": 1,
     "tg_id": 2006,
     "username": null,
     "first_name": "سارا رحیمی",
     "phone": "989123047514",
     "balance": 45000,
     "coins": 2,
     "ref_code": "UKZC8H",
     "referred_by": null,
     "is_blocked": 0,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-08-14 02:30:52",
     "last_seen": "2026-09-24 23:00:52",
     "affiliate_id": 1,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 1,
     "spent": 266000,
     "subsCount": 1,
     "activeSubs": 1
    },
    {
     "id": 8,
     "tenant_id": 1,
     "tg_id": 2005,
     "username": "user8",
     "first_name": "پویا کریمی",
     "phone": "989123039595",
     "balance": 0,
     "coins": 35,
     "ref_code": "P4G8HJ",
     "referred_by": null,
     "is_blocked": 0,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-08-11 02:30:52",
     "last_seen": "2026-09-24 23:00:52",
     "affiliate_id": 3,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 1,
     "spent": 100000,
     "subsCount": 1,
     "activeSubs": 1
    },
    {
     "id": 7,
     "tenant_id": 1,
     "tg_id": 2004,
     "username": "user7",
     "first_name": "نگار احمدی",
     "phone": null,
     "balance": 180000,
     "coins": 28,
     "ref_code": "QT2URV",
     "referred_by": null,
     "is_blocked": 0,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-08-08 02:30:52",
     "last_seen": "2026-09-24 23:00:52",
     "affiliate_id": null,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 0,
     "spent": 0,
     "subsCount": 1,
     "activeSubs": 1
    },
    {
     "id": 6,
     "tenant_id": 1,
     "tg_id": 2003,
     "username": null,
     "first_name": "امیر صادقی",
     "phone": "989123023757",
     "balance": 135000,
     "coins": 21,
     "ref_code": "RKABZB",
     "referred_by": null,
     "is_blocked": 0,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-08-05 02:30:52",
     "last_seen": "2026-09-24 23:00:52",
     "affiliate_id": null,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 0,
     "spent": 0,
     "subsCount": 1,
     "activeSubs": 0
    },
    {
     "id": 5,
     "tenant_id": 1,
     "tg_id": 2002,
     "username": "user5",
     "first_name": "زهرا مرادی",
     "phone": "989123015838",
     "balance": 90000,
     "coins": 14,
     "ref_code": "6TXW2W",
     "referred_by": 1,
     "is_blocked": 0,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-08-02 02:30:52",
     "last_seen": "2026-09-24 23:00:52",
     "affiliate_id": 2,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 1,
     "spent": 280000,
     "subsCount": 1,
     "activeSubs": 1
    },
    {
     "id": 4,
     "tenant_id": 1,
     "tg_id": 2001,
     "username": "user4",
     "first_name": "حسین نوری",
     "phone": "989123007919",
     "balance": 45000,
     "coins": 7,
     "ref_code": "B3G599",
     "referred_by": null,
     "is_blocked": 0,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-07-30 02:30:52",
     "last_seen": "2026-09-24 23:00:52",
     "affiliate_id": null,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 0,
     "spent": 0,
     "subsCount": 1,
     "activeSubs": 1
    },
    {
     "id": 3,
     "tenant_id": 1,
     "tg_id": 2000,
     "username": null,
     "first_name": "مریم کاظمی",
     "phone": null,
     "balance": 0,
     "coins": 0,
     "ref_code": "UK9XDY",
     "referred_by": null,
     "is_blocked": 0,
     "trial_used": 0,
     "phone_asked": 0,
     "lang": "fa",
     "state": null,
     "state_data": "{}",
     "created_at": "2026-07-27 02:30:52",
     "last_seen": "2026-09-24 23:00:52",
     "affiliate_id": null,
     "trial_followup_at": null,
     "held_discount": null,
     "ordersCount": 0,
     "spent": 0,
     "subsCount": 1,
     "activeSubs": 1
    }
   ],
   "dbReady": true,
   "total": 18,
   "offset": 0,
   "limit": 50,
   "counts": {
    "all": 18,
    "active": 9,
    "expired": 3,
    "never": 6,
    "buyers": 4,
    "blocked": 1,
    "withPhone": 13,
    "noPhone": 5,
    "withBalance": 13,
    "withCoins": 16,
    "referred": 4
   }
  };

  var PLANS = {
   "plans": [
    {
     "id": 2,
     "tenant_id": 1,
     "name": "تست رایگان",
     "description": "یک روز · یک گیگ — برای امتحانِ سرعت",
     "gb": 1,
     "days": 1,
     "ip_limit": 1,
     "price": 0,
     "inbound_id": 1,
     "is_active": 1,
     "is_trial": 1,
     "sort_order": 1,
     "created_at": "2026-09-24 23:00:52",
     "inbound_ids": null,
     "cost": 0
    },
    {
     "id": 1,
     "tenant_id": 1,
     "name": "یک‌ماهه",
     "description": "۳۰ روز · ۳۰ گیگ · دو کاربره",
     "gb": 30,
     "days": 30,
     "ip_limit": 2,
     "price": 100000,
     "inbound_id": 1,
     "is_active": 1,
     "is_trial": 0,
     "sort_order": 2,
     "created_at": "2026-09-24 23:00:50",
     "inbound_ids": null,
     "cost": 0
    },
    {
     "id": 3,
     "tenant_id": 1,
     "name": "سه‌ماهه",
     "description": "۹۰ روز · ۱۰۰ گیگ · دو کاربره — پرفروش",
     "gb": 100,
     "days": 90,
     "ip_limit": 2,
     "price": 280000,
     "inbound_id": 1,
     "is_active": 1,
     "is_trial": 0,
     "sort_order": 3,
     "created_at": "2026-09-24 23:00:52",
     "inbound_ids": null,
     "cost": 0
    },
    {
     "id": 4,
     "tenant_id": 1,
     "name": "شش‌ماهه",
     "description": "۱۸۰ روز · ۲۰۰ گیگ · سه کاربره",
     "gb": 200,
     "days": 180,
     "ip_limit": 3,
     "price": 480000,
     "inbound_id": 1,
     "is_active": 1,
     "is_trial": 0,
     "sort_order": 4,
     "created_at": "2026-09-24 23:00:52",
     "inbound_ids": null,
     "cost": 0
    },
    {
     "id": 5,
     "tenant_id": 1,
     "name": "نامحدودِ خانواده",
     "description": "۳۰ روز · بی‌سقف · پنج کاربره",
     "gb": 0,
     "days": 30,
     "ip_limit": 5,
     "price": 390000,
     "inbound_id": 1,
     "is_active": 0,
     "is_trial": 0,
     "sort_order": 5,
     "created_at": "2026-09-24 23:00:52",
     "inbound_ids": null,
     "cost": 0
    }
   ],
   "ready": true
  };
  var BOT_SETTINGS = {
   "ready": true,
   "tenant": {
    "id": 1,
    "name": "Owner",
    "bot_token": "…",
    "bot_username": "",
    "owner_tg_id": 1,
    "parent_id": null,
    "is_active": 1,
    "credit": 0,
    "credit_discount": 0,
    "panel_url": "",
    "panel_user": "",
    "panel_pass": null,
    "panel_token": null,
    "default_inbound": "",
    "admin_group_id": "",
    "topics": {},
    "settings": {},
    "created_at": "2026-09-24 23:00:50",
    "inbound_mode": "all",
    "inbound_ids": null,
    "portal_slug": null,
    "portal_pass": null,
    "portal_enabled": 0,
    "portal_group": null,
    "bot_token_set": true,
    "panel_pass_set": false,
    "panel_token_set": false
   }
  };
  var BOT_STATUS = {
   "installed": true,
   "dbReady": true,
   "running": true,
   "stats": {
    "users": 18,
    "plans": 4,
    "pendingOrders": 5,
    "activeSubs": 9,
    "openTickets": 0,
    "tenants": 1
   },
   "totalSales": 746000,
   "totalReceived": 466000,
   "totalRevenue": 746000
  };


  /* فایروال و تشخیصِ نفوذ — خروجیِ خودِ بکند (firewall.py/intrusion.py)
     روی فیکسچرِ test-contract با خروجیِ دستورهای ساختگی. نسخه‌ی قبلی
     کلیدهایی داشت که در بکند نیستند (tries، from، backend) و همه‌ی
     زیرمسیرها همان FIREWALL را می‌گرفتند. */
  var FIREWALL = {
   "ready": true,
   "installed": true,
   "active": true,
   "rules": [
    {
     "num": 1,
     "target": "22/tcp",
     "port": 22,
     "proto": "tcp",
     "action": "LIMIT",
     "direction": "IN",
     "source": "Anywhere",
     "v6": false,
     "critical": true,
     "note": "SSH — راه ورود شما به سرور",
     "both": true
    },
    {
     "num": 2,
     "target": "443",
     "port": 443,
     "proto": "any",
     "action": "ALLOW",
     "direction": "IN",
     "source": "Anywhere",
     "v6": false,
     "critical": false,
     "note": "",
     "both": true
    },
    {
     "num": 3,
     "target": "2053/tcp",
     "port": 2053,
     "proto": "tcp",
     "action": "ALLOW",
     "direction": "IN",
     "source": "Anywhere",
     "v6": false,
     "critical": false,
     "note": "",
     "both": false
    },
    {
     "num": 4,
     "target": "3080/tcp",
     "port": 3080,
     "proto": "tcp",
     "action": "ALLOW",
     "direction": "IN",
     "source": "Anywhere",
     "v6": false,
     "critical": false,
     "note": "",
     "both": false
    },
    {
     "num": 5,
     "target": "8443",
     "port": 8443,
     "proto": "any",
     "action": "ALLOW",
     "direction": "IN",
     "source": "Anywhere",
     "v6": false,
     "critical": false,
     "note": "",
     "both": false
    },
    {
     "num": 6,
     "target": "Anywhere",
     "port": null,
     "proto": "",
     "action": "DENY",
     "direction": "IN",
     "source": "203.0.113.50",
     "v6": false,
     "critical": false,
     "note": "",
     "both": false
    },
    {
     "num": 7,
     "target": "Anywhere",
     "port": null,
     "proto": "",
     "action": "DENY",
     "direction": "IN",
     "source": "203.0.113.51",
     "v6": false,
     "critical": false,
     "note": "",
     "both": false
    }
   ],
   "ruleCount": 7,
   "sshProtected": true,
   "sshPorts": [
    22
   ],
   "defaultIncoming": "deny"
  };
  var FW_BLOCKED = {
   "blocked": [
    {
     "ip": "203.0.113.41",
     "via": "blackhole",
     "active": true,
     "how": "مسیر سیاه‌چاله‌ی کرنل — بدون فایروال کار می‌کند"
    },
    {
     "ip": "203.0.113.60",
     "via": "blackhole",
     "active": true,
     "how": "مسیر سیاه‌چاله‌ی کرنل — بدون فایروال کار می‌کند"
    },
    {
     "ip": "203.0.113.61",
     "via": "blackhole",
     "active": true,
     "how": "مسیر سیاه‌چاله‌ی کرنل — بدون فایروال کار می‌کند"
    },
    {
     "ip": "203.0.113.50",
     "via": "ufw",
     "active": true,
     "pending": false,
     "num": 6,
     "how": "قاعده‌ی فایروال"
    },
    {
     "ip": "203.0.113.51",
     "via": "ufw",
     "active": true,
     "pending": false,
     "num": 7,
     "how": "قاعده‌ی فایروال"
    }
   ],
   "firewallActive": true,
   "blackholeAvailable": true
  };
  var FW_SUGGEST = {
   "ready": true,
   "installed": true,
   "active": true,
   "keep": [],
   "close": [
    {
     "port": 6379,
     "proto": "tcp",
     "process": "redis-server",
     "action": "deny",
     "why": "رو به اینترنت باز است و به سرویس شما ربطی ندارد — پردازه: redis-server"
    },
    {
     "port": 9100,
     "proto": "tcp",
     "process": "node_exporter",
     "action": "deny",
     "why": "رو به اینترنت باز است و به سرویس شما ربطی ندارد — پردازه: node_exporter"
    }
   ],
   "unknown": [
    {
     "port": 5353,
     "proto": "udp",
     "process": "",
     "action": "deny",
     "why": "نام پردازه در دسترس نیست، پس نمی‌دانیم این پورت مال چیست. اگر تانل یا سرویسی دارید که روی این پورت کار می‌کند، نبندیدش. برای دیدن نامش روی سرور: ss -tulpn | grep 5353"
    }
   ],
   "already": [
    {
     "port": 22,
     "proto": "tcp",
     "process": "sshd",
     "action": "LIMIT",
     "why": "SSH"
    },
    {
     "port": 443,
     "proto": "tcp",
     "process": "xray",
     "action": "ALLOW",
     "why": "Xray"
    },
    {
     "port": 2053,
     "proto": "tcp",
     "process": "x-ui",
     "action": "ALLOW",
     "why": "پنل 3x-ui"
    },
    {
     "port": 3080,
     "proto": "tcp",
     "process": "backhaul",
     "action": "ALLOW",
     "why": "قاعده دارد"
    }
   ],
   "ephemeral": [
    {
     "port": 41877,
     "proto": "udp",
     "process": "xray"
    },
    {
     "port": 52011,
     "proto": "udp",
     "process": "xray"
    }
   ],
   "tunnelPorts": [
    3080
   ],
   "sshCovered": true
  };
  var FW_PREFLIGHT = {
   "ready": true,
   "active": true,
   "atRisk": [
    {
     "port": 6379,
     "proto": "tcp",
     "process": "redis-server",
     "why": "پردازه‌ی redis-server",
     "critical": false
    },
    {
     "port": 9100,
     "proto": "tcp",
     "process": "node_exporter",
     "why": "پردازه‌ی node_exporter",
     "critical": false
    },
    {
     "port": 5353,
     "proto": "udp",
     "process": "",
     "why": "",
     "critical": false
    }
   ],
   "covered": [
    {
     "port": 22,
     "proto": "tcp",
     "process": "sshd",
     "why": "SSH — راه ورود شما به سرور",
     "critical": true
    },
    {
     "port": 443,
     "proto": "tcp",
     "process": "xray",
     "why": "Xray",
     "critical": false
    },
    {
     "port": 2053,
     "proto": "tcp",
     "process": "x-ui",
     "why": "پنل 3x-ui",
     "critical": false
    },
    {
     "port": 3080,
     "proto": "tcp",
     "process": "backhaul",
     "why": "تانل backhaul — تمام مشتری‌های ایران از این رد می‌شوند",
     "critical": true
    }
   ],
   "blockers": [],
   "safe": true,
   "note": "3 سرویس قاعده ندارد و با روشن‌شدن قطع می‌شود"
  };
  var FW_ROLLBACK = {
   "armed": false,
   "confirmed": false
  };
  var INTRUSION = {
   "ssh": {
    "available": true,
    "hours": 24,
    "attempts": [
     {
      "ip": "203.0.113.40",
      "count": 38,
      "users": [
       "root"
      ],
      "top_user": "root",
      "first": "2026-09-24T03:07:01",
      "last": "2026-09-24T07:26:38",
      "known": false,
      "severity": "brute",
      "kind": "unknown",
      "why": "",
      "blocked": false
     },
     {
      "ip": "203.0.113.41",
      "count": 22,
      "users": [
       "admin"
      ],
      "top_user": "admin",
      "first": "2026-09-24T07:33:39",
      "last": "2026-09-24T10:00:00",
      "known": false,
      "severity": "brute",
      "kind": "unknown",
      "why": "",
      "blocked": true
     },
     {
      "ip": "203.0.113.42",
      "count": 9,
      "users": [
       "ubuntu"
      ],
      "top_user": "ubuntu",
      "first": "2026-09-24T10:07:01",
      "last": "2026-09-24T11:03:09",
      "known": false,
      "severity": "noise",
      "kind": "unknown",
      "why": "",
      "blocked": false
     },
     {
      "ip": "203.0.113.43",
      "count": 4,
      "users": [
       "root"
      ],
      "top_user": "root",
      "first": "2026-09-24T11:10:10",
      "last": "2026-09-24T11:31:13",
      "known": false,
      "severity": "noise",
      "kind": "unknown",
      "why": "",
      "blocked": false
     },
     {
      "ip": "198.51.100.30",
      "count": 3,
      "users": [
       "root"
      ],
      "top_user": "root",
      "first": "2026-09-24T11:38:14",
      "last": "2026-09-24T11:52:16",
      "known": true,
      "severity": "noise",
      "kind": "tunnel",
      "why": "سرِ دیگرِ تانلِ «ایران-۱»",
      "blocked": false
     },
     {
      "ip": "198.51.100.7",
      "count": 2,
      "users": [
       "root"
      ],
      "top_user": "root",
      "first": "2026-09-24T11:59:17",
      "last": "2026-09-24T12:06:18",
      "known": true,
      "severity": "noise",
      "kind": "customer",
      "why": "همین آدرس الان به ۲ کانفیگ وصل است: ali_1، sara_1",
      "blocked": false
     }
    ],
    "total": 78,
    "attackers": 2,
    "customers": [
     {
      "ip": "198.51.100.30",
      "count": 3,
      "users": [
       "root"
      ],
      "top_user": "root",
      "first": "2026-09-24T11:38:14",
      "last": "2026-09-24T11:52:16",
      "known": true,
      "severity": "noise",
      "kind": "tunnel",
      "why": "سرِ دیگرِ تانلِ «ایران-۱»",
      "blocked": false
     },
     {
      "ip": "198.51.100.7",
      "count": 2,
      "users": [
       "root"
      ],
      "top_user": "root",
      "first": "2026-09-24T11:59:17",
      "last": "2026-09-24T12:06:18",
      "known": true,
      "severity": "noise",
      "kind": "customer",
      "why": "همین آدرس الان به ۲ کانفیگ وصل است: ali_1، sara_1",
      "blocked": false
     }
    ],
    "accepted": [
     {
      "user": "root",
      "ip": "198.51.100.7",
      "at": "2026-09-24T12:00:01"
     }
    ]
   },
   "hardening": {
    "checks": [
     {
      "key": "root_login",
      "title": "ورود مستقیم با کاربر root",
      "ok": false,
      "value": "yes",
      "why": "بیشترِ بروت‌فورس‌ها فقط root را امتحان می‌کنند. بستن آن به‌تنهایی اغلب حجم تلاش‌ها را چند برابر کم می‌کند.",
      "fix": "sed -i 's/^#\\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config && systemctl reload ssh"
     },
     {
      "key": "password_auth",
      "title": "ورود با رمز عبور",
      "ok": false,
      "value": "yes",
      "why": "تا وقتی رمز قبول می‌شود، بروت‌فورس معنی دارد. با کلید SSH، حدس‌زدن رمز بی‌فایده می‌شود.",
      "fix": "اول کلید SSH خودتان را اضافه کنید، بعد: sed -i 's/^#\\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && systemctl reload ssh",
      "danger": "اگر کلید SSH نگذاشته باشید، بعد از این دیگر نمی‌توانید وارد سرور شوید."
     },
     {
      "key": "port",
      "title": "پورت SSH",
      "ok": false,
      "value": "22",
      "why": "عوض‌کردن پورت جلوی حمله‌ی هدفمند را نمی‌گیرد، ولی اسکنرهای خودکار که فقط ۲۲ را می‌زنند کنار می‌روند و لاگ تمیز می‌شود.",
      "fix": "در /etc/ssh/sshd_config پورت را عوض کنید، در فایروال باز کنید، و تا وقتی با پورت جدید وارد نشده‌اید نشست فعلی را نبندید."
     },
     {
      "key": "fail2ban",
      "title": "fail2ban",
      "ok": true,
      "value": "نصب است — 0 IP مسدود",
      "why": "IPهایی که پشت سر هم رمز اشتباه می‌زنند را خودکار و موقت می‌بندد. بهترین نسبت اثر به زحمت در این فهرست همین است.",
      "fix": "apt-get install -y fail2ban && systemctl enable --now fail2ban"
     }
    ],
    "score": 1,
    "total": 4
   },
   "advice": [
    {
     "level": "warn",
     "text": "بیشترِ بروت‌فورس‌ها فقط root را امتحان می‌کنند. بستن آن به‌تنهایی اغلب حجم تلاش‌ها را چند برابر کم می‌کند.",
     "fix": "sed -i 's/^#\\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config && systemctl reload ssh",
     "title": "ورود مستقیم با کاربر root",
     "danger": null,
     "action": null
    },
    {
     "level": "warn",
     "text": "تا وقتی رمز قبول می‌شود، بروت‌فورس معنی دارد. با کلید SSH، حدس‌زدن رمز بی‌فایده می‌شود.",
     "fix": "اول کلید SSH خودتان را اضافه کنید، بعد: sed -i 's/^#\\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && systemctl reload ssh",
     "title": "ورود با رمز عبور",
     "danger": "اگر کلید SSH نگذاشته باشید، بعد از این دیگر نمی‌توانید وارد سرور شوید.",
     "action": null
    },
    {
     "level": "warn",
     "text": "عوض‌کردن پورت جلوی حمله‌ی هدفمند را نمی‌گیرد، ولی اسکنرهای خودکار که فقط ۲۲ را می‌زنند کنار می‌روند و لاگ تمیز می‌شود.",
     "fix": "در /etc/ssh/sshd_config پورت را عوض کنید، در فایروال باز کنید، و تا وقتی با پورت جدید وارد نشده‌اید نشست فعلی را نبندید.",
     "title": "پورت SSH",
     "danger": null,
     "action": null
    }
   ],
   "checked_at": 1790278249,
   "lookupPending": 6,
   "vpnNote": "اگر کسی از VPN استفاده کند، آدرس واقعی‌اش از بیرون قابل کشف نیست — نه با این پنل و نه با هیچ ابزار دیگری. ولی سؤال واقعی شما این نیست؛ سؤال این است که «اگر این را ببندم، مشتری‌ام را بسته‌ام؟» و آن جواب دارد: همین آدرس را در فهرست آدرس‌هایی که کلاینت‌های خودتان با آن وصل می‌شوند می‌گردیم. اگر پیدا شود، پشت آن VPN یک مشتری نشسته."
  };

  var AFFILIATES = {
   "ready": true,
   "affiliates": [
    {
     "id": 3,
     "tenant_id": 1,
     "name": "کانال تکنو",
     "code": "TECH",
     "tg_id": 9015,
     "percent": 15.0,
     "active": 1,
     "note": null,
     "password": null,
     "created_at": "2026-09-24 23:00:53",
     "tenantName": "Owner",
     "isOwn": true,
     "users": 1,
     "orders": 1,
     "sales": 100000,
     "earned": 15000,
     "payouts": 0,
     "balance": 15000
    },
    {
     "id": 2,
     "tenant_id": 1,
     "name": "سارا رحیمی",
     "code": "SR12",
     "tg_id": 9012,
     "percent": 12.0,
     "active": 1,
     "note": null,
     "password": null,
     "created_at": "2026-09-24 23:00:53",
     "tenantName": "Owner",
     "isOwn": true,
     "users": 1,
     "orders": 1,
     "sales": 280000,
     "earned": 33600,
     "payouts": 0,
     "balance": 33600
    },
    {
     "id": 1,
     "tenant_id": 1,
     "name": "حسین نوری",
     "code": "HN10",
     "tg_id": 9010,
     "percent": 10.0,
     "active": 1,
     "note": null,
     "password": null,
     "created_at": "2026-09-24 23:00:53",
     "tenantName": "Owner",
     "isOwn": true,
     "users": 2,
     "orders": 2,
     "sales": 366000,
     "earned": 36600,
     "payouts": 28000,
     "balance": 8600
    }
   ],
   "totalOwed": 57200,
   "resellerOwed": 0
  };

  /* مانیتورینگِ سرور — عیناً خروجیِ monitor.snapshot() (test-contract می‌سنجد).
     با توابعِ خودِ monitor.py ساخته شده (tools/…/p_hmon)، چون روی
     ویندوز همه‌ی بخش‌های لینوکسی خالی‌اند. نسخه‌ی قبلی summary.nodes و
     ram داشت که در بکند نیست؛ صفحه در هارنس هیچ‌وقت شکلِ واقعی‌اش را نشان نداد. */
  var MONITOR = {
    "level": "crit",
    "summary": "۱ مشکل جدی و ۲ هشدار",
    "headline": "به‌روزرسانی در انتظار",
    "metrics": [
      {
        "key": "cpu",
        "title": "مصرف پردازنده",
        "value": 38.4,
        "unit": "٪",
        "level": "ok",
        "detail": "بار ۱ دقیقه: ۱.۵۴ روی ۴ هسته",
        "why": "بالای ۷۵٪ یعنی سرور دارد به سقف می‌رسد و تأخیر کاربران بالا می‌رود. بالای ۹۲٪ یعنی همین حالا کند شده.",
        "hint": "با «سنگین‌ترین پردازه‌ها» پایین ببینید چه چیزی مصرف می‌کند.",
        "pct": 38.4,
        "extra": {
          "cores": 4,
          "load": [
            1.54,
            1.42,
            1.28
          ]
        }
      },
      {
        "key": "memory",
        "title": "حافظه",
        "value": 61.2,
        "unit": "٪",
        "level": "ok",
        "detail": "۴.۹ GB از ۸.۰ GB — ۳.۱ GB آزاد",
        "why": "بالای ۸۵٪ یعنی فضای مانور کم شده. اگر پر شود، هسته پردازه‌ها را می‌کشد و Xray هم می‌تواند قربانی شود — یعنی قطعی سرویس.",
        "hint": "اگر همیشه بالاست، یا مصرف واقعی زیاد است یا نشتی حافظه دارید.",
        "pct": 61.2,
        "extra": {
          "total": 8589934592,
          "used": 5257039970,
          "available": 3332894622
        }
      },
      {
        "key": "disk:/",
        "title": "دیسک /",
        "value": 47.5,
        "unit": "٪",
        "level": "ok",
        "detail": "۳۸.۰ GB از ۸۰.۰ GB — ۴۲.۰ GB آزاد",
        "why": "دیسک پر یعنی لاگ نوشته نمی‌شود، دیتابیس ربات خطا می‌دهد و بک‌آپ ساخته نمی‌شود. زیر ۸٪ آزاد وارد منطقه‌ی خطر می‌شوید.",
        "hint": "بزرگ‌ترین مصرف‌کننده معمولاً لاگ‌هاست: journalctl --vacuum-size=200M",
        "pct": 47.5,
        "extra": {
          "mount": "/",
          "total": 85899345920,
          "used": 40802189312
        }
      },
      {
        "key": "throughput",
        "title": "ترافیک لحظه‌ای",
        "value": 312.6,
        "unit": "Mbps",
        "level": "ok",
        "detail": "دریافت ۲۳.۱ MB/s · ارسال ۱۴.۲ MB/s",
        "why": "این همان چیزی است که مشتری‌های شما دارند مصرف می‌کنند. اگر به سقف پورت سرور (معمولاً ۱ گیگابیت) نزدیک شود، سرعت همه افت می‌کند.",
        "hint": "اگر مدام نزدیک سقف است، یا کاربر را کم کنید یا پورت بالاتر بگیرید.",
        "pct": 31,
        "extra": {
          "rx": 24226500,
          "tx": 14848500,
          "interfaces": [
            {
              "name": "eth0",
              "rx": 24226500,
              "tx": 14848500,
              "rxTotal": 9812000000000,
              "txTotal": 6120000000000
            }
          ]
        }
      },
      {
        "key": "established",
        "title": "اتصال‌های برقرار",
        "value": 1284,
        "unit": "",
        "level": "ok",
        "detail": "۱۲۸۴ اتصال TCP/UDP",
        "why": "تقریباً برابر با تعداد نشست‌های فعال مشتری‌ها.",
        "hint": "",
        "pct": null,
        "extra": {}
      },
      {
        "key": "xray",
        "title": "سرویس Xray",
        "value": "روشن",
        "unit": "",
        "level": "ok",
        "detail": "وضعیت systemd: active",
        "why": "اگر Xray خاموش باشد هیچ کاربری وصل نمی‌شود، حتی اگر پنل و ربات سالم کار کنند.",
        "hint": "",
        "pct": null,
        "extra": {}
      },
      {
        "key": "xray_errors",
        "title": "خطاهای Xray (۳۰ دقیقه اخیر)",
        "value": 3,
        "unit": "",
        "level": "ok",
        "detail": "۳ خط هشدار یا خطا",
        "why": "چند خطای پراکنده طبیعی است. انبوه خطا یعنی یا کانفیگ مشکل دارد یا سرور خارج در دسترس نیست.",
        "hint": "برای دیدن: journalctl -u xray -p warning --since -30min",
        "pct": null,
        "extra": {
          "lines": [
            "Sep 24 20:11:02 xray[812]: [Warning] failed to handler mux client connection > context canceled"
          ]
        }
      },
      {
        "key": "updates",
        "title": "به‌روزرسانی در انتظار",
        "value": 14,
        "unit": "بسته",
        "level": "crit",
        "detail": "۱۴ بسته — ۲ مورد امنیتی",
        "why": "به‌روزرسانی امنیتی یعنی حفره‌ای عمومی شده که کد سوءاستفاده‌اش هم معمولاً منتشر است. روی سروری که پورت باز به اینترنت دارد، این فوری‌ترین ریسک است.",
        "hint": "apt update && apt upgrade",
        "pct": null,
        "extra": {
          "security": 2,
          "sample": [
            "openssl",
            "libssl3",
            "openssh-server",
            "curl"
          ]
        }
      },
      {
        "key": "ssh_failed",
        "title": "ورود ناموفق SSH (۲۴ ساعت)",
        "value": 412,
        "unit": "",
        "level": "warn",
        "detail": "۴۱۲ تلاش ناموفق از ۳۷ آدرس",
        "why": "روی هر سرور عمومی چند صد تلاش خودکار در روز عادی است. عدد خیلی بالا از یک IP یعنی هدف‌گیری مشخص.",
        "hint": "ورود با رمز را ببندید و فقط کلید بگذارید؛ یا fail2ban نصب کنید.",
        "pct": null,
        "extra": {
          "topIps": [
            {
              "ip": "203.0.113.11",
              "n": 96
            },
            {
              "ip": "203.0.113.34",
              "n": 71
            },
            {
              "ip": "203.0.113.172",
              "n": 40
            }
          ]
        }
      },
      {
        "key": "fail2ban",
        "title": "fail2ban",
        "value": "فعال",
        "unit": "",
        "level": "ok",
        "detail": "جیل‌ها: sshd",
        "why": "fail2ban آدرس‌هایی را که مکرر شکست می‌خورند خودکار می‌بندد.",
        "hint": "",
        "pct": null,
        "extra": {}
      },
      {
        "key": "firewall",
        "title": "فایروال",
        "value": "روشن",
        "unit": "",
        "level": "ok",
        "detail": "Status: active",
        "why": "فایروال خاموش یعنی هر پورتی که سهواً باز شود، مستقیم از اینترنت در دسترس است.",
        "hint": "",
        "pct": null,
        "extra": {}
      },
      {
        "key": "conn:192.0.2.9",
        "title": "اتصال زیاد از 192.0.2.9",
        "value": 214,
        "unit": "اتصال",
        "level": "warn",
        "detail": "۱۶.۷٪ از کل اتصال‌های سرور",
        "why": "یک IP با این سهم یعنی یا یک حساب بین چند نفر پخش شده یا کسی دارد سرور را اسکن می‌کند.",
        "hint": "ss -tunp | grep 192.0.2.9",
        "pct": null,
        "extra": {}
      }
    ],
    "sections": {
      "cpu": [
        {
          "key": "cpu",
          "title": "مصرف پردازنده",
          "value": 38.4,
          "unit": "٪",
          "level": "ok",
          "detail": "بار ۱ دقیقه: ۱.۵۴ روی ۴ هسته",
          "why": "بالای ۷۵٪ یعنی سرور دارد به سقف می‌رسد و تأخیر کاربران بالا می‌رود. بالای ۹۲٪ یعنی همین حالا کند شده.",
          "hint": "با «سنگین‌ترین پردازه‌ها» پایین ببینید چه چیزی مصرف می‌کند.",
          "pct": 38.4,
          "extra": {
            "cores": 4,
            "load": [
              1.54,
              1.42,
              1.28
            ]
          }
        }
      ],
      "memory": [
        {
          "key": "memory",
          "title": "حافظه",
          "value": 61.2,
          "unit": "٪",
          "level": "ok",
          "detail": "۴.۹ GB از ۸.۰ GB — ۳.۱ GB آزاد",
          "why": "بالای ۸۵٪ یعنی فضای مانور کم شده. اگر پر شود، هسته پردازه‌ها را می‌کشد و Xray هم می‌تواند قربانی شود — یعنی قطعی سرویس.",
          "hint": "اگر همیشه بالاست، یا مصرف واقعی زیاد است یا نشتی حافظه دارید.",
          "pct": 61.2,
          "extra": {
            "total": 8589934592,
            "used": 5257039970,
            "available": 3332894622
          }
        }
      ],
      "disk": [
        {
          "key": "disk:/",
          "title": "دیسک /",
          "value": 47.5,
          "unit": "٪",
          "level": "ok",
          "detail": "۳۸.۰ GB از ۸۰.۰ GB — ۴۲.۰ GB آزاد",
          "why": "دیسک پر یعنی لاگ نوشته نمی‌شود، دیتابیس ربات خطا می‌دهد و بک‌آپ ساخته نمی‌شود. زیر ۸٪ آزاد وارد منطقه‌ی خطر می‌شوید.",
          "hint": "بزرگ‌ترین مصرف‌کننده معمولاً لاگ‌هاست: journalctl --vacuum-size=200M",
          "pct": 47.5,
          "extra": {
            "mount": "/",
            "total": 85899345920,
            "used": 40802189312
          }
        }
      ],
      "network": [
        {
          "key": "throughput",
          "title": "ترافیک لحظه‌ای",
          "value": 312.6,
          "unit": "Mbps",
          "level": "ok",
          "detail": "دریافت ۲۳.۱ MB/s · ارسال ۱۴.۲ MB/s",
          "why": "این همان چیزی است که مشتری‌های شما دارند مصرف می‌کنند. اگر به سقف پورت سرور (معمولاً ۱ گیگابیت) نزدیک شود، سرعت همه افت می‌کند.",
          "hint": "اگر مدام نزدیک سقف است، یا کاربر را کم کنید یا پورت بالاتر بگیرید.",
          "pct": 31,
          "extra": {
            "rx": 24226500,
            "tx": 14848500,
            "interfaces": [
              {
                "name": "eth0",
                "rx": 24226500,
                "tx": 14848500,
                "rxTotal": 9812000000000,
                "txTotal": 6120000000000
              }
            ]
          }
        },
        {
          "key": "established",
          "title": "اتصال‌های برقرار",
          "value": 1284,
          "unit": "",
          "level": "ok",
          "detail": "۱۲۸۴ اتصال TCP/UDP",
          "why": "تقریباً برابر با تعداد نشست‌های فعال مشتری‌ها.",
          "hint": "",
          "pct": null,
          "extra": {}
        }
      ],
      "xray": [
        {
          "key": "xray",
          "title": "سرویس Xray",
          "value": "روشن",
          "unit": "",
          "level": "ok",
          "detail": "وضعیت systemd: active",
          "why": "اگر Xray خاموش باشد هیچ کاربری وصل نمی‌شود، حتی اگر پنل و ربات سالم کار کنند.",
          "hint": "",
          "pct": null,
          "extra": {}
        },
        {
          "key": "xray_errors",
          "title": "خطاهای Xray (۳۰ دقیقه اخیر)",
          "value": 3,
          "unit": "",
          "level": "ok",
          "detail": "۳ خط هشدار یا خطا",
          "why": "چند خطای پراکنده طبیعی است. انبوه خطا یعنی یا کانفیگ مشکل دارد یا سرور خارج در دسترس نیست.",
          "hint": "برای دیدن: journalctl -u xray -p warning --since -30min",
          "pct": null,
          "extra": {
            "lines": [
              "Sep 24 20:11:02 xray[812]: [Warning] failed to handler mux client connection > context canceled"
            ]
          }
        }
      ],
      "packages": [
        {
          "key": "updates",
          "title": "به‌روزرسانی در انتظار",
          "value": 14,
          "unit": "بسته",
          "level": "crit",
          "detail": "۱۴ بسته — ۲ مورد امنیتی",
          "why": "به‌روزرسانی امنیتی یعنی حفره‌ای عمومی شده که کد سوءاستفاده‌اش هم معمولاً منتشر است. روی سروری که پورت باز به اینترنت دارد، این فوری‌ترین ریسک است.",
          "hint": "apt update && apt upgrade",
          "pct": null,
          "extra": {
            "security": 2,
            "sample": [
              "openssl",
              "libssl3",
              "openssh-server",
              "curl"
            ]
          }
        }
      ],
      "security": [
        {
          "key": "ssh_failed",
          "title": "ورود ناموفق SSH (۲۴ ساعت)",
          "value": 412,
          "unit": "",
          "level": "warn",
          "detail": "۴۱۲ تلاش ناموفق از ۳۷ آدرس",
          "why": "روی هر سرور عمومی چند صد تلاش خودکار در روز عادی است. عدد خیلی بالا از یک IP یعنی هدف‌گیری مشخص.",
          "hint": "ورود با رمز را ببندید و فقط کلید بگذارید؛ یا fail2ban نصب کنید.",
          "pct": null,
          "extra": {
            "topIps": [
              {
                "ip": "203.0.113.11",
                "n": 96
              },
              {
                "ip": "203.0.113.34",
                "n": 71
              },
              {
                "ip": "203.0.113.172",
                "n": 40
              }
            ]
          }
        },
        {
          "key": "fail2ban",
          "title": "fail2ban",
          "value": "فعال",
          "unit": "",
          "level": "ok",
          "detail": "جیل‌ها: sshd",
          "why": "fail2ban آدرس‌هایی را که مکرر شکست می‌خورند خودکار می‌بندد.",
          "hint": "",
          "pct": null,
          "extra": {}
        },
        {
          "key": "firewall",
          "title": "فایروال",
          "value": "روشن",
          "unit": "",
          "level": "ok",
          "detail": "Status: active",
          "why": "فایروال خاموش یعنی هر پورتی که سهواً باز شود، مستقیم از اینترنت در دسترس است.",
          "hint": "",
          "pct": null,
          "extra": {}
        }
      ],
      "services": [
        {
          "name": "xray",
          "active": "active",
          "sub": "running",
          "pid": "812",
          "memory": 184000000,
          "restarts": 0,
          "level": "ok",
          "flapping": false
        },
        {
          "name": "x-ui",
          "active": "active",
          "sub": "running",
          "pid": "790",
          "memory": 96000000,
          "restarts": 0,
          "level": "ok",
          "flapping": false
        },
        {
          "name": "nginx",
          "active": "active",
          "sub": "running",
          "pid": "655",
          "memory": 22000000,
          "restarts": 0,
          "level": "ok",
          "flapping": false
        },
        {
          "name": "nexora-bot",
          "active": "active",
          "sub": "running",
          "pid": "1021",
          "memory": 71000000,
          "restarts": 0,
          "level": "ok",
          "flapping": false
        },
        {
          "name": "nexora-api",
          "active": "active",
          "sub": "running",
          "pid": "1003",
          "memory": 118000000,
          "restarts": 0,
          "level": "ok",
          "flapping": false
        },
        {
          "name": "fail2ban",
          "active": "active",
          "sub": "running",
          "pid": "702",
          "memory": 31000000,
          "restarts": 0,
          "level": "ok",
          "flapping": false
        },
        {
          "name": "ssh",
          "active": "active",
          "sub": "running",
          "pid": "640",
          "memory": 6000000,
          "restarts": 0,
          "level": "ok",
          "flapping": false
        }
      ],
      "ports": [
        {
          "port": 22,
          "proto": "tcp",
          "process": "sshd",
          "public": true,
          "bind": "0.0.0.0",
          "scope": "public",
          "known": "SSH",
          "risk": "low"
        },
        {
          "port": 443,
          "proto": "tcp",
          "process": "xray",
          "public": true,
          "bind": "0.0.0.0",
          "scope": "public",
          "known": "Xray",
          "risk": "low"
        },
        {
          "port": 2053,
          "proto": "tcp",
          "process": "x-ui",
          "public": true,
          "bind": "0.0.0.0",
          "scope": "public",
          "known": "پنل 3x-ui",
          "risk": "low"
        },
        {
          "port": 8000,
          "proto": "tcp",
          "process": "python3",
          "public": false,
          "bind": "127.0.0.1",
          "scope": "local",
          "known": "API نکسورا",
          "risk": "low"
        },
        {
          "port": 6379,
          "proto": "tcp",
          "process": "redis-server",
          "public": true,
          "bind": "0.0.0.0",
          "scope": "public",
          "known": "",
          "risk": "medium"
        }
      ],
      "processes": [
        {
          "pid": 812,
          "name": "xray",
          "cpu": 21.1,
          "mem": 2.2,
          "uptime": 1036800
        },
        {
          "pid": 1003,
          "name": "python3",
          "cpu": 3.1,
          "mem": 1.4,
          "uptime": 259200
        },
        {
          "pid": 790,
          "name": "x-ui",
          "cpu": 1.8,
          "mem": 1.1,
          "uptime": 1036800
        },
        {
          "pid": 655,
          "name": "nginx",
          "cpu": 0.6,
          "mem": 0.3,
          "uptime": 1036800
        },
        {
          "pid": 1021,
          "name": "python3",
          "cpu": 0.4,
          "mem": 0.9,
          "uptime": 259200
        }
      ],
      "connections": {
        "total": 1284,
        "uniqueIps": 311,
        "byIp": [
          {
            "ip": "203.0.113.4",
            "count": 402,
            "pct": 31.3,
            "tunnel": "ایران-۱"
          },
          {
            "ip": "192.0.2.77",
            "count": 48,
            "pct": 3.7,
            "tunnel": ""
          },
          {
            "ip": "192.0.2.110",
            "count": 31,
            "pct": 2.4,
            "tunnel": ""
          },
          {
            "ip": "192.0.2.9",
            "count": 214,
            "pct": 16.7,
            "tunnel": ""
          }
        ],
        "byPort": [
          {
            "port": 443,
            "count": 1102
          },
          {
            "port": 8443,
            "count": 141
          },
          {
            "port": 22,
            "count": 41
          }
        ],
        "heavy": [
          {
            "ip": "192.0.2.9",
            "count": 214,
            "pct": 16.7
          }
        ],
        "tunnels": [
          {
            "ip": "203.0.113.4",
            "name": "ایران-۱",
            "count": 402,
            "pct": 31.3
          }
        ],
        "tunnelConns": 402
      }
    },
    "counts": {
      "ok": 9,
      "warn": 2,
      "crit": 1
    },
    "host": {
      "uptime": 1054800,
      "cores": 4,
      "kernel": "5.15.0-119-generic",
      "hostname": "de-fra-1"
    },
    "at": "2026-09-24 20:31:12",
    "took": 1.12
  };
  /* مانیتورینگِ نودِ ۱ — همان شکل، با سرویسِ ناپایدار */
  var SYSMON1 = {
    "level": "warn",
    "summary": "۱ هشدار",
    "headline": "سرویس nexora-bot",
    "metrics": [
      {
        "key": "cpu",
        "title": "مصرف پردازنده",
        "value": 22.0,
        "unit": "٪",
        "level": "ok",
        "detail": "بار ۱ دقیقه: ۰.۸۸ روی ۴ هسته",
        "why": "بالای ۷۵٪ یعنی سرور دارد به سقف می‌رسد و تأخیر کاربران بالا می‌رود. بالای ۹۲٪ یعنی همین حالا کند شده.",
        "hint": "با «سنگین‌ترین پردازه‌ها» پایین ببینید چه چیزی مصرف می‌کند.",
        "pct": 22.0,
        "extra": {
          "cores": 4,
          "load": [
            0.88,
            0.81,
            0.73
          ]
        }
      },
      {
        "key": "memory",
        "title": "حافظه",
        "value": 44.0,
        "unit": "٪",
        "level": "ok",
        "detail": "۳.۵ GB از ۸.۰ GB — ۴.۵ GB آزاد",
        "why": "بالای ۸۵٪ یعنی فضای مانور کم شده. اگر پر شود، هسته پردازه‌ها را می‌کشد و Xray هم می‌تواند قربانی شود — یعنی قطعی سرویس.",
        "hint": "اگر همیشه بالاست، یا مصرف واقعی زیاد است یا نشتی حافظه دارید.",
        "pct": 44.0,
        "extra": {
          "total": 8589934592,
          "used": 3779571220,
          "available": 4810363372
        }
      },
      {
        "key": "disk:/",
        "title": "دیسک /",
        "value": 36.0,
        "unit": "٪",
        "level": "ok",
        "detail": "۲۸.۸ GB از ۸۰.۰ GB — ۵۱.۲ GB آزاد",
        "why": "دیسک پر یعنی لاگ نوشته نمی‌شود، دیتابیس ربات خطا می‌دهد و بک‌آپ ساخته نمی‌شود. زیر ۸٪ آزاد وارد منطقه‌ی خطر می‌شوید.",
        "hint": "بزرگ‌ترین مصرف‌کننده معمولاً لاگ‌هاست: journalctl --vacuum-size=200M",
        "pct": 36.0,
        "extra": {
          "mount": "/",
          "total": 85899345920,
          "used": 30923764531
        }
      },
      {
        "key": "throughput",
        "title": "ترافیک لحظه‌ای",
        "value": 188.2,
        "unit": "Mbps",
        "level": "ok",
        "detail": "دریافت ۱۳.۹ MB/s · ارسال ۸.۵ MB/s",
        "why": "این همان چیزی است که مشتری‌های شما دارند مصرف می‌کنند. اگر به سقف پورت سرور (معمولاً ۱ گیگابیت) نزدیک شود، سرعت همه افت می‌کند.",
        "hint": "اگر مدام نزدیک سقف است، یا کاربر را کم کنید یا پورت بالاتر بگیرید.",
        "pct": 19,
        "extra": {
          "rx": 14585500,
          "tx": 8939500,
          "interfaces": [
            {
              "name": "eth0",
              "rx": 14585500,
              "tx": 8939500,
              "rxTotal": 9812000000000,
              "txTotal": 6120000000000
            }
          ]
        }
      },
      {
        "key": "established",
        "title": "اتصال‌های برقرار",
        "value": 1284,
        "unit": "",
        "level": "ok",
        "detail": "۱۲۸۴ اتصال TCP/UDP",
        "why": "تقریباً برابر با تعداد نشست‌های فعال مشتری‌ها.",
        "hint": "",
        "pct": null,
        "extra": {}
      },
      {
        "key": "xray",
        "title": "سرویس Xray",
        "value": "روشن",
        "unit": "",
        "level": "ok",
        "detail": "وضعیت systemd: active",
        "why": "اگر Xray خاموش باشد هیچ کاربری وصل نمی‌شود، حتی اگر پنل و ربات سالم کار کنند.",
        "hint": "",
        "pct": null,
        "extra": {}
      },
      {
        "key": "xray_errors",
        "title": "خطاهای Xray (۳۰ دقیقه اخیر)",
        "value": 3,
        "unit": "",
        "level": "ok",
        "detail": "۳ خط هشدار یا خطا",
        "why": "چند خطای پراکنده طبیعی است. انبوه خطا یعنی یا کانفیگ مشکل دارد یا سرور خارج در دسترس نیست.",
        "hint": "برای دیدن: journalctl -u xray -p warning --since -30min",
        "pct": null,
        "extra": {
          "lines": [
            "Sep 24 20:11:02 xray[812]: [Warning] failed to handler mux client connection > context canceled"
          ]
        }
      },
      {
        "key": "updates",
        "title": "به‌روزرسانی در انتظار",
        "value": 3,
        "unit": "بسته",
        "level": "ok",
        "detail": "۳ بسته — ۰ مورد امنیتی",
        "why": "به‌روزرسانی امنیتی یعنی حفره‌ای عمومی شده که کد سوءاستفاده‌اش هم معمولاً منتشر است. روی سروری که پورت باز به اینترنت دارد، این فوری‌ترین ریسک است.",
        "hint": "apt update && apt upgrade",
        "pct": null,
        "extra": {
          "security": 0,
          "sample": [
            "openssl",
            "libssl3",
            "openssh-server",
            "curl"
          ]
        }
      },
      {
        "key": "ssh_failed",
        "title": "ورود ناموفق SSH (۲۴ ساعت)",
        "value": 96,
        "unit": "",
        "level": "ok",
        "detail": "۹۶ تلاش ناموفق از ۳۷ آدرس",
        "why": "روی هر سرور عمومی چند صد تلاش خودکار در روز عادی است. عدد خیلی بالا از یک IP یعنی هدف‌گیری مشخص.",
        "hint": "ورود با رمز را ببندید و فقط کلید بگذارید؛ یا fail2ban نصب کنید.",
        "pct": null,
        "extra": {
          "topIps": [
            {
              "ip": "203.0.113.11",
              "n": 96
            },
            {
              "ip": "203.0.113.34",
              "n": 71
            },
            {
              "ip": "203.0.113.172",
              "n": 40
            }
          ]
        }
      },
      {
        "key": "fail2ban",
        "title": "fail2ban",
        "value": "فعال",
        "unit": "",
        "level": "ok",
        "detail": "جیل‌ها: sshd",
        "why": "fail2ban آدرس‌هایی را که مکرر شکست می‌خورند خودکار می‌بندد.",
        "hint": "",
        "pct": null,
        "extra": {}
      },
      {
        "key": "firewall",
        "title": "فایروال",
        "value": "روشن",
        "unit": "",
        "level": "ok",
        "detail": "Status: active",
        "why": "فایروال خاموش یعنی هر پورتی که سهواً باز شود، مستقیم از اینترنت در دسترس است.",
        "hint": "",
        "pct": null,
        "extra": {}
      },
      {
        "key": "svc:nexora-bot",
        "title": "سرویس nexora-bot",
        "value": "ناپایدار",
        "unit": "",
        "level": "warn",
        "detail": "۶ بار ری‌استارت شده",
        "why": "سرویسی که مدام بالا و پایین می‌شود از خاموش بدتر است، چون در نگاه اول سالم به نظر می‌رسد.",
        "hint": "journalctl -u nexora-bot -n 50",
        "pct": null,
        "extra": {}
      }
    ],
    "sections": {
      "cpu": [
        {
          "key": "cpu",
          "title": "مصرف پردازنده",
          "value": 22.0,
          "unit": "٪",
          "level": "ok",
          "detail": "بار ۱ دقیقه: ۰.۸۸ روی ۴ هسته",
          "why": "بالای ۷۵٪ یعنی سرور دارد به سقف می‌رسد و تأخیر کاربران بالا می‌رود. بالای ۹۲٪ یعنی همین حالا کند شده.",
          "hint": "با «سنگین‌ترین پردازه‌ها» پایین ببینید چه چیزی مصرف می‌کند.",
          "pct": 22.0,
          "extra": {
            "cores": 4,
            "load": [
              0.88,
              0.81,
              0.73
            ]
          }
        }
      ],
      "memory": [
        {
          "key": "memory",
          "title": "حافظه",
          "value": 44.0,
          "unit": "٪",
          "level": "ok",
          "detail": "۳.۵ GB از ۸.۰ GB — ۴.۵ GB آزاد",
          "why": "بالای ۸۵٪ یعنی فضای مانور کم شده. اگر پر شود، هسته پردازه‌ها را می‌کشد و Xray هم می‌تواند قربانی شود — یعنی قطعی سرویس.",
          "hint": "اگر همیشه بالاست، یا مصرف واقعی زیاد است یا نشتی حافظه دارید.",
          "pct": 44.0,
          "extra": {
            "total": 8589934592,
            "used": 3779571220,
            "available": 4810363372
          }
        }
      ],
      "disk": [
        {
          "key": "disk:/",
          "title": "دیسک /",
          "value": 36.0,
          "unit": "٪",
          "level": "ok",
          "detail": "۲۸.۸ GB از ۸۰.۰ GB — ۵۱.۲ GB آزاد",
          "why": "دیسک پر یعنی لاگ نوشته نمی‌شود، دیتابیس ربات خطا می‌دهد و بک‌آپ ساخته نمی‌شود. زیر ۸٪ آزاد وارد منطقه‌ی خطر می‌شوید.",
          "hint": "بزرگ‌ترین مصرف‌کننده معمولاً لاگ‌هاست: journalctl --vacuum-size=200M",
          "pct": 36.0,
          "extra": {
            "mount": "/",
            "total": 85899345920,
            "used": 30923764531
          }
        }
      ],
      "network": [
        {
          "key": "throughput",
          "title": "ترافیک لحظه‌ای",
          "value": 188.2,
          "unit": "Mbps",
          "level": "ok",
          "detail": "دریافت ۱۳.۹ MB/s · ارسال ۸.۵ MB/s",
          "why": "این همان چیزی است که مشتری‌های شما دارند مصرف می‌کنند. اگر به سقف پورت سرور (معمولاً ۱ گیگابیت) نزدیک شود، سرعت همه افت می‌کند.",
          "hint": "اگر مدام نزدیک سقف است، یا کاربر را کم کنید یا پورت بالاتر بگیرید.",
          "pct": 19,
          "extra": {
            "rx": 14585500,
            "tx": 8939500,
            "interfaces": [
              {
                "name": "eth0",
                "rx": 14585500,
                "tx": 8939500,
                "rxTotal": 9812000000000,
                "txTotal": 6120000000000
              }
            ]
          }
        },
        {
          "key": "established",
          "title": "اتصال‌های برقرار",
          "value": 1284,
          "unit": "",
          "level": "ok",
          "detail": "۱۲۸۴ اتصال TCP/UDP",
          "why": "تقریباً برابر با تعداد نشست‌های فعال مشتری‌ها.",
          "hint": "",
          "pct": null,
          "extra": {}
        }
      ],
      "xray": [
        {
          "key": "xray",
          "title": "سرویس Xray",
          "value": "روشن",
          "unit": "",
          "level": "ok",
          "detail": "وضعیت systemd: active",
          "why": "اگر Xray خاموش باشد هیچ کاربری وصل نمی‌شود، حتی اگر پنل و ربات سالم کار کنند.",
          "hint": "",
          "pct": null,
          "extra": {}
        },
        {
          "key": "xray_errors",
          "title": "خطاهای Xray (۳۰ دقیقه اخیر)",
          "value": 3,
          "unit": "",
          "level": "ok",
          "detail": "۳ خط هشدار یا خطا",
          "why": "چند خطای پراکنده طبیعی است. انبوه خطا یعنی یا کانفیگ مشکل دارد یا سرور خارج در دسترس نیست.",
          "hint": "برای دیدن: journalctl -u xray -p warning --since -30min",
          "pct": null,
          "extra": {
            "lines": [
              "Sep 24 20:11:02 xray[812]: [Warning] failed to handler mux client connection > context canceled"
            ]
          }
        }
      ],
      "packages": [
        {
          "key": "updates",
          "title": "به‌روزرسانی در انتظار",
          "value": 3,
          "unit": "بسته",
          "level": "ok",
          "detail": "۳ بسته — ۰ مورد امنیتی",
          "why": "به‌روزرسانی امنیتی یعنی حفره‌ای عمومی شده که کد سوءاستفاده‌اش هم معمولاً منتشر است. روی سروری که پورت باز به اینترنت دارد، این فوری‌ترین ریسک است.",
          "hint": "apt update && apt upgrade",
          "pct": null,
          "extra": {
            "security": 0,
            "sample": [
              "openssl",
              "libssl3",
              "openssh-server",
              "curl"
            ]
          }
        }
      ],
      "security": [
        {
          "key": "ssh_failed",
          "title": "ورود ناموفق SSH (۲۴ ساعت)",
          "value": 96,
          "unit": "",
          "level": "ok",
          "detail": "۹۶ تلاش ناموفق از ۳۷ آدرس",
          "why": "روی هر سرور عمومی چند صد تلاش خودکار در روز عادی است. عدد خیلی بالا از یک IP یعنی هدف‌گیری مشخص.",
          "hint": "ورود با رمز را ببندید و فقط کلید بگذارید؛ یا fail2ban نصب کنید.",
          "pct": null,
          "extra": {
            "topIps": [
              {
                "ip": "203.0.113.11",
                "n": 96
              },
              {
                "ip": "203.0.113.34",
                "n": 71
              },
              {
                "ip": "203.0.113.172",
                "n": 40
              }
            ]
          }
        },
        {
          "key": "fail2ban",
          "title": "fail2ban",
          "value": "فعال",
          "unit": "",
          "level": "ok",
          "detail": "جیل‌ها: sshd",
          "why": "fail2ban آدرس‌هایی را که مکرر شکست می‌خورند خودکار می‌بندد.",
          "hint": "",
          "pct": null,
          "extra": {}
        },
        {
          "key": "firewall",
          "title": "فایروال",
          "value": "روشن",
          "unit": "",
          "level": "ok",
          "detail": "Status: active",
          "why": "فایروال خاموش یعنی هر پورتی که سهواً باز شود، مستقیم از اینترنت در دسترس است.",
          "hint": "",
          "pct": null,
          "extra": {}
        }
      ],
      "services": [
        {
          "name": "xray",
          "active": "active",
          "sub": "running",
          "pid": "812",
          "memory": 184000000,
          "restarts": 0,
          "level": "ok",
          "flapping": false
        },
        {
          "name": "x-ui",
          "active": "active",
          "sub": "running",
          "pid": "790",
          "memory": 96000000,
          "restarts": 0,
          "level": "ok",
          "flapping": false
        },
        {
          "name": "nginx",
          "active": "active",
          "sub": "running",
          "pid": "655",
          "memory": 22000000,
          "restarts": 0,
          "level": "ok",
          "flapping": false
        },
        {
          "name": "nexora-bot",
          "active": "active",
          "sub": "running",
          "pid": "1021",
          "memory": 71000000,
          "restarts": 6,
          "level": "ok",
          "flapping": true
        },
        {
          "name": "nexora-api",
          "active": "active",
          "sub": "running",
          "pid": "1003",
          "memory": 118000000,
          "restarts": 0,
          "level": "ok",
          "flapping": false
        },
        {
          "name": "fail2ban",
          "active": "active",
          "sub": "running",
          "pid": "702",
          "memory": 31000000,
          "restarts": 0,
          "level": "ok",
          "flapping": false
        },
        {
          "name": "ssh",
          "active": "active",
          "sub": "running",
          "pid": "640",
          "memory": 6000000,
          "restarts": 0,
          "level": "ok",
          "flapping": false
        }
      ],
      "ports": [
        {
          "port": 22,
          "proto": "tcp",
          "process": "sshd",
          "public": true,
          "bind": "0.0.0.0",
          "scope": "public",
          "known": "SSH",
          "risk": "low"
        },
        {
          "port": 443,
          "proto": "tcp",
          "process": "xray",
          "public": true,
          "bind": "0.0.0.0",
          "scope": "public",
          "known": "Xray",
          "risk": "low"
        },
        {
          "port": 2053,
          "proto": "tcp",
          "process": "x-ui",
          "public": true,
          "bind": "0.0.0.0",
          "scope": "public",
          "known": "پنل 3x-ui",
          "risk": "low"
        },
        {
          "port": 8000,
          "proto": "tcp",
          "process": "python3",
          "public": false,
          "bind": "127.0.0.1",
          "scope": "local",
          "known": "API نکسورا",
          "risk": "low"
        },
        {
          "port": 6379,
          "proto": "tcp",
          "process": "redis-server",
          "public": true,
          "bind": "0.0.0.0",
          "scope": "public",
          "known": "",
          "risk": "medium"
        }
      ],
      "processes": [
        {
          "pid": 812,
          "name": "xray",
          "cpu": 12.1,
          "mem": 2.2,
          "uptime": 1036800
        },
        {
          "pid": 1003,
          "name": "python3",
          "cpu": 3.1,
          "mem": 1.4,
          "uptime": 259200
        },
        {
          "pid": 790,
          "name": "x-ui",
          "cpu": 1.8,
          "mem": 1.1,
          "uptime": 1036800
        },
        {
          "pid": 655,
          "name": "nginx",
          "cpu": 0.6,
          "mem": 0.3,
          "uptime": 1036800
        },
        {
          "pid": 1021,
          "name": "python3",
          "cpu": 0.4,
          "mem": 0.9,
          "uptime": 259200
        }
      ],
      "connections": {
        "total": 1284,
        "uniqueIps": 311,
        "byIp": [
          {
            "ip": "203.0.113.4",
            "count": 402,
            "pct": 31.3,
            "tunnel": "ایران-۱"
          },
          {
            "ip": "192.0.2.77",
            "count": 48,
            "pct": 3.7,
            "tunnel": ""
          },
          {
            "ip": "192.0.2.110",
            "count": 31,
            "pct": 2.4,
            "tunnel": ""
          }
        ],
        "byPort": [
          {
            "port": 443,
            "count": 1102
          },
          {
            "port": 8443,
            "count": 141
          },
          {
            "port": 22,
            "count": 41
          }
        ],
        "heavy": [],
        "tunnels": [
          {
            "ip": "203.0.113.4",
            "name": "ایران-۱",
            "count": 402,
            "pct": 31.3
          }
        ],
        "tunnelConns": 402
      }
    },
    "counts": {
      "ok": 11,
      "warn": 1,
      "crit": 0
    },
    "host": {
      "uptime": 1054800,
      "cores": 4,
      "kernel": "5.15.0-119-generic",
      "hostname": "ir-thr-1"
    },
    "at": "2026-09-24 20:31:12",
    "took": 1.12
  };
  /* تاریخچه‌ی ۲۴ ساعته — هر ۵ دقیقه، مثلِ حلقه‌ی بکند */
  var USAGE = {
    "samples": [
    {"t": "2026-09-23T20:00", "cpu": 19.0, "mem": 54.1, "conn": 447, "ips": 109},
    {"t": "2026-09-23T20:05", "cpu": 24.7, "mem": 53.9, "conn": 474, "ips": 115},
    {"t": "2026-09-23T20:10", "cpu": 23.3, "mem": 53.8, "conn": 441, "ips": 107},
    {"t": "2026-09-23T20:15", "cpu": 22.0, "mem": 53.7, "conn": 468, "ips": 114},
    {"t": "2026-09-23T20:20", "cpu": 20.6, "mem": 53.6, "conn": 435, "ips": 106},
    {"t": "2026-09-23T20:25", "cpu": 19.3, "mem": 53.5, "conn": 403, "ips": 98},
    {"t": "2026-09-23T20:30", "cpu": 18.0, "mem": 53.4, "conn": 431, "ips": 105},
    {"t": "2026-09-23T20:35", "cpu": 16.6, "mem": 53.4, "conn": 399, "ips": 97},
    {"t": "2026-09-23T20:40", "cpu": 22.3, "mem": 53.3, "conn": 428, "ips": 104},
    {"t": "2026-09-23T20:45", "cpu": 21.0, "mem": 53.2, "conn": 396, "ips": 96},
    {"t": "2026-09-23T20:50", "cpu": 19.8, "mem": 53.1, "conn": 365, "ips": 89},
    {"t": "2026-09-23T20:55", "cpu": 18.5, "mem": 53.0, "conn": 394, "ips": 96},
    {"t": "2026-09-23T21:00", "cpu": 17.2, "mem": 52.9, "conn": 364, "ips": 88},
    {"t": "2026-09-23T21:05", "cpu": 16.0, "mem": 52.9, "conn": 334, "ips": 81},
    {"t": "2026-09-23T21:10", "cpu": 14.7, "mem": 52.8, "conn": 364, "ips": 88},
    {"t": "2026-09-23T21:15", "cpu": 20.5, "mem": 52.7, "conn": 334, "ips": 81},
    {"t": "2026-09-23T21:20", "cpu": 19.2, "mem": 52.7, "conn": 365, "ips": 89},
    {"t": "2026-09-23T21:25", "cpu": 18.0, "mem": 52.6, "conn": 336, "ips": 81},
    {"t": "2026-09-23T21:30", "cpu": 16.8, "mem": 52.5, "conn": 307, "ips": 74},
    {"t": "2026-09-23T21:35", "cpu": 15.6, "mem": 52.5, "conn": 338, "ips": 82},
    {"t": "2026-09-23T21:40", "cpu": 14.4, "mem": 52.4, "conn": 310, "ips": 75},
    {"t": "2026-09-23T21:45", "cpu": 13.3, "mem": 52.4, "conn": 342, "ips": 83},
    {"t": "2026-09-23T21:50", "cpu": 19.1, "mem": 52.3, "conn": 315, "ips": 76},
    {"t": "2026-09-23T21:55", "cpu": 18.0, "mem": 52.3, "conn": 287, "ips": 70},
    {"t": "2026-09-23T22:00", "cpu": 16.8, "mem": 52.2, "conn": 321, "ips": 78},
    {"t": "2026-09-23T22:05", "cpu": 15.7, "mem": 52.2, "conn": 294, "ips": 71},
    {"t": "2026-09-23T22:10", "cpu": 14.6, "mem": 52.2, "conn": 268, "ips": 65},
    {"t": "2026-09-23T22:15", "cpu": 13.5, "mem": 52.1, "conn": 301, "ips": 73},
    {"t": "2026-09-23T22:20", "cpu": 12.4, "mem": 52.1, "conn": 276, "ips": 67},
    {"t": "2026-09-23T22:25", "cpu": 18.3, "mem": 52.1, "conn": 310, "ips": 75},
    {"t": "2026-09-23T22:30", "cpu": 17.2, "mem": 52.1, "conn": 285, "ips": 69},
    {"t": "2026-09-23T22:35", "cpu": 16.1, "mem": 52.0, "conn": 261, "ips": 63},
    {"t": "2026-09-23T22:40", "cpu": 15.1, "mem": 52.0, "conn": 296, "ips": 72},
    {"t": "2026-09-23T22:45", "cpu": 14.1, "mem": 52.0, "conn": 272, "ips": 66},
    {"t": "2026-09-23T22:50", "cpu": 13.0, "mem": 52.0, "conn": 308, "ips": 75},
    {"t": "2026-09-23T22:55", "cpu": 12.0, "mem": 52.0, "conn": 285, "ips": 69},
    {"t": "2026-09-23T23:00", "cpu": 18.0, "mem": 52.0, "conn": 262, "ips": 63},
    {"t": "2026-09-23T23:05", "cpu": 17.0, "mem": 52.0, "conn": 299, "ips": 72},
    {"t": "2026-09-23T23:10", "cpu": 16.0, "mem": 52.0, "conn": 276, "ips": 67},
    {"t": "2026-09-23T23:15", "cpu": 15.1, "mem": 52.0, "conn": 254, "ips": 61},
    {"t": "2026-09-23T23:20", "cpu": 14.1, "mem": 52.0, "conn": 292, "ips": 71},
    {"t": "2026-09-23T23:25", "cpu": 13.1, "mem": 52.0, "conn": 271, "ips": 66},
    {"t": "2026-09-23T23:30", "cpu": 12.2, "mem": 52.1, "conn": 309, "ips": 75},
    {"t": "2026-09-23T23:35", "cpu": 18.3, "mem": 52.1, "conn": 288, "ips": 70},
    {"t": "2026-09-23T23:40", "cpu": 17.4, "mem": 52.1, "conn": 268, "ips": 65},
    {"t": "2026-09-23T23:45", "cpu": 16.5, "mem": 52.1, "conn": 307, "ips": 74},
    {"t": "2026-09-23T23:50", "cpu": 15.6, "mem": 52.2, "conn": 288, "ips": 70},
    {"t": "2026-09-23T23:55", "cpu": 14.7, "mem": 52.2, "conn": 328, "ips": 80},
    {"t": "2026-09-24T00:00", "cpu": 13.8, "mem": 52.2, "conn": 309, "ips": 75},
    {"t": "2026-09-24T00:05", "cpu": 13.0, "mem": 52.3, "conn": 289, "ips": 70},
    {"t": "2026-09-24T00:10", "cpu": 19.1, "mem": 52.3, "conn": 331, "ips": 80},
    {"t": "2026-09-24T00:15", "cpu": 18.3, "mem": 52.4, "conn": 312, "ips": 76},
    {"t": "2026-09-24T00:20", "cpu": 17.4, "mem": 52.4, "conn": 294, "ips": 71},
    {"t": "2026-09-24T00:25", "cpu": 16.6, "mem": 52.5, "conn": 336, "ips": 81},
    {"t": "2026-09-24T00:30", "cpu": 15.8, "mem": 52.5, "conn": 319, "ips": 77},
    {"t": "2026-09-24T00:35", "cpu": 15.0, "mem": 52.6, "conn": 362, "ips": 88},
    {"t": "2026-09-24T00:40", "cpu": 14.2, "mem": 52.7, "conn": 345, "ips": 84},
    {"t": "2026-09-24T00:45", "cpu": 20.5, "mem": 52.7, "conn": 328, "ips": 80},
    {"t": "2026-09-24T00:50", "cpu": 19.7, "mem": 52.8, "conn": 372, "ips": 90},
    {"t": "2026-09-24T00:55", "cpu": 19.0, "mem": 52.9, "conn": 356, "ips": 86},
    {"t": "2026-09-24T01:00", "cpu": 18.2, "mem": 52.9, "conn": 340, "ips": 82},
    {"t": "2026-09-24T01:05", "cpu": 17.5, "mem": 53.0, "conn": 384, "ips": 93},
    {"t": "2026-09-24T01:10", "cpu": 16.8, "mem": 53.1, "conn": 369, "ips": 90},
    {"t": "2026-09-24T01:15", "cpu": 16.0, "mem": 53.2, "conn": 414, "ips": 100},
    {"t": "2026-09-24T01:20", "cpu": 22.3, "mem": 53.3, "conn": 400, "ips": 97},
    {"t": "2026-09-24T01:25", "cpu": 21.6, "mem": 53.4, "conn": 385, "ips": 93},
    {"t": "2026-09-24T01:30", "cpu": 21.0, "mem": 53.4, "conn": 431, "ips": 105},
    {"t": "2026-09-24T01:35", "cpu": 20.3, "mem": 53.5, "conn": 417, "ips": 101},
    {"t": "2026-09-24T01:40", "cpu": 19.6, "mem": 53.6, "conn": 463, "ips": 112},
    {"t": "2026-09-24T01:45", "cpu": 19.0, "mem": 53.7, "conn": 450, "ips": 109},
    {"t": "2026-09-24T01:50", "cpu": 18.3, "mem": 53.8, "conn": 437, "ips": 106},
    {"t": "2026-09-24T01:55", "cpu": 24.7, "mem": 53.9, "conn": 484, "ips": 118},
    {"t": "2026-09-24T02:00", "cpu": 24.0, "mem": 54.1, "conn": 471, "ips": 114},
    {"t": "2026-09-24T02:05", "cpu": 23.4, "mem": 54.2, "conn": 459, "ips": 111},
    {"t": "2026-09-24T02:10", "cpu": 22.8, "mem": 54.3, "conn": 506, "ips": 123},
    {"t": "2026-09-24T02:15", "cpu": 22.2, "mem": 54.4, "conn": 494, "ips": 120},
    {"t": "2026-09-24T02:20", "cpu": 21.6, "mem": 54.5, "conn": 543, "ips": 132},
    {"t": "2026-09-24T02:25", "cpu": 21.0, "mem": 54.6, "conn": 531, "ips": 129},
    {"t": "2026-09-24T02:30", "cpu": 27.4, "mem": 54.7, "conn": 520, "ips": 126},
    {"t": "2026-09-24T02:35", "cpu": 26.8, "mem": 54.9, "conn": 568, "ips": 138},
    {"t": "2026-09-24T02:40", "cpu": 26.2, "mem": 55.0, "conn": 557, "ips": 135},
    {"t": "2026-09-24T02:45", "cpu": 25.7, "mem": 55.1, "conn": 606, "ips": 147},
    {"t": "2026-09-24T02:50", "cpu": 25.1, "mem": 55.2, "conn": 596, "ips": 145},
    {"t": "2026-09-24T02:55", "cpu": 24.5, "mem": 55.4, "conn": 585, "ips": 142},
    {"t": "2026-09-24T03:00", "cpu": 24.0, "mem": 55.5, "conn": 635, "ips": 154},
    {"t": "2026-09-24T03:05", "cpu": 30.5, "mem": 55.6, "conn": 625, "ips": 152},
    {"t": "2026-09-24T03:10", "cpu": 29.9, "mem": 55.8, "conn": 615, "ips": 150},
    {"t": "2026-09-24T03:15", "cpu": 29.4, "mem": 55.9, "conn": 665, "ips": 162},
    {"t": "2026-09-24T03:20", "cpu": 28.9, "mem": 56.0, "conn": 655, "ips": 159},
    {"t": "2026-09-24T03:25", "cpu": 28.3, "mem": 56.2, "conn": 706, "ips": 172},
    {"t": "2026-09-24T03:30", "cpu": 27.8, "mem": 56.3, "conn": 696, "ips": 169},
    {"t": "2026-09-24T03:35", "cpu": 27.3, "mem": 56.5, "conn": 687, "ips": 167},
    {"t": "2026-09-24T03:40", "cpu": 33.8, "mem": 56.6, "conn": 738, "ips": 180},
    {"t": "2026-09-24T03:45", "cpu": 33.3, "mem": 56.7, "conn": 729, "ips": 177},
    {"t": "2026-09-24T03:50", "cpu": 32.8, "mem": 56.9, "conn": 780, "ips": 190},
    {"t": "2026-09-24T03:55", "cpu": 32.3, "mem": 57.0, "conn": 771, "ips": 188},
    {"t": "2026-09-24T04:00", "cpu": 31.8, "mem": 57.2, "conn": 762, "ips": 185},
    {"t": "2026-09-24T04:05", "cpu": 31.3, "mem": 57.3, "conn": 813, "ips": 198},
    {"t": "2026-09-24T04:10", "cpu": 30.8, "mem": 57.5, "conn": 804, "ips": 196},
    {"t": "2026-09-24T04:15", "cpu": 37.3, "mem": 57.6, "conn": 796, "ips": 194},
    {"t": "2026-09-24T04:20", "cpu": 36.8, "mem": 57.8, "conn": 847, "ips": 206},
    {"t": "2026-09-24T04:25", "cpu": 36.3, "mem": 57.9, "conn": 839, "ips": 204},
    {"t": "2026-09-24T04:30", "cpu": 35.9, "mem": 58.1, "conn": 890, "ips": 217},
    {"t": "2026-09-24T04:35", "cpu": 35.4, "mem": 58.2, "conn": 882, "ips": 215},
    {"t": "2026-09-24T04:40", "cpu": 34.9, "mem": 58.4, "conn": 874, "ips": 213},
    {"t": "2026-09-24T04:45", "cpu": 34.4, "mem": 58.5, "conn": 925, "ips": 225},
    {"t": "2026-09-24T04:50", "cpu": 41.0, "mem": 58.7, "conn": 917, "ips": 223},
    {"t": "2026-09-24T04:55", "cpu": 40.5, "mem": 58.8, "conn": 969, "ips": 236},
    {"t": "2026-09-24T05:00", "cpu": 40.0, "mem": 59.0, "conn": 961, "ips": 234},
    {"t": "2026-09-24T05:05", "cpu": 39.5, "mem": 59.2, "conn": 952, "ips": 232},
    {"t": "2026-09-24T05:10", "cpu": 39.0, "mem": 59.3, "conn": 1004, "ips": 244},
    {"t": "2026-09-24T05:15", "cpu": 38.6, "mem": 59.5, "conn": 996, "ips": 242},
    {"t": "2026-09-24T05:20", "cpu": 38.1, "mem": 59.6, "conn": 987, "ips": 240},
    {"t": "2026-09-24T05:25", "cpu": 44.6, "mem": 59.8, "conn": 1039, "ips": 253},
    {"t": "2026-09-24T05:30", "cpu": 44.1, "mem": 59.9, "conn": 1031, "ips": 251},
    {"t": "2026-09-24T05:35", "cpu": 43.7, "mem": 60.1, "conn": 1082, "ips": 263},
    {"t": "2026-09-24T05:40", "cpu": 43.2, "mem": 60.2, "conn": 1074, "ips": 261},
    {"t": "2026-09-24T05:45", "cpu": 42.7, "mem": 60.4, "conn": 1065, "ips": 259},
    {"t": "2026-09-24T05:50", "cpu": 42.2, "mem": 60.5, "conn": 1117, "ips": 272},
    {"t": "2026-09-24T05:55", "cpu": 41.7, "mem": 60.7, "conn": 1108, "ips": 270},
    {"t": "2026-09-24T06:00", "cpu": 48.2, "mem": 60.8, "conn": 1099, "ips": 268},
    {"t": "2026-09-24T06:05", "cpu": 47.7, "mem": 61.0, "conn": 1150, "ips": 280},
    {"t": "2026-09-24T06:10", "cpu": 47.2, "mem": 61.1, "conn": 1141, "ips": 278},
    {"t": "2026-09-24T06:15", "cpu": 46.7, "mem": 61.3, "conn": 1192, "ips": 290},
    {"t": "2026-09-24T06:20", "cpu": 46.2, "mem": 61.4, "conn": 1183, "ips": 288},
    {"t": "2026-09-24T06:25", "cpu": 45.7, "mem": 61.5, "conn": 1174, "ips": 286},
    {"t": "2026-09-24T06:30", "cpu": 45.2, "mem": 61.7, "conn": 1225, "ips": 298},
    {"t": "2026-09-24T06:35", "cpu": 51.7, "mem": 61.8, "conn": 1215, "ips": 296},
    {"t": "2026-09-24T06:40", "cpu": 51.1, "mem": 62.0, "conn": 1266, "ips": 308},
    {"t": "2026-09-24T06:45", "cpu": 50.6, "mem": 62.1, "conn": 1256, "ips": 306},
    {"t": "2026-09-24T06:50", "cpu": 50.1, "mem": 62.2, "conn": 1246, "ips": 303},
    {"t": "2026-09-24T06:55", "cpu": 49.5, "mem": 62.4, "conn": 1296, "ips": 316},
    {"t": "2026-09-24T07:00", "cpu": 49.0, "mem": 62.5, "conn": 1286, "ips": 313},
    {"t": "2026-09-24T07:05", "cpu": 48.5, "mem": 62.6, "conn": 1276, "ips": 311},
    {"t": "2026-09-24T07:10", "cpu": 54.9, "mem": 62.8, "conn": 1325, "ips": 323},
    {"t": "2026-09-24T07:15", "cpu": 54.3, "mem": 62.9, "conn": 1315, "ips": 320},
    {"t": "2026-09-24T07:20", "cpu": 53.8, "mem": 63.0, "conn": 1364, "ips": 332},
    {"t": "2026-09-24T07:25", "cpu": 53.2, "mem": 63.1, "conn": 1353, "ips": 330},
    {"t": "2026-09-24T07:30", "cpu": 52.6, "mem": 63.3, "conn": 1341, "ips": 327},
    {"t": "2026-09-24T07:35", "cpu": 52.0, "mem": 63.4, "conn": 1390, "ips": 339},
    {"t": "2026-09-24T07:40", "cpu": 51.4, "mem": 63.5, "conn": 1378, "ips": 336},
    {"t": "2026-09-24T07:45", "cpu": 57.8, "mem": 63.6, "conn": 1427, "ips": 348},
    {"t": "2026-09-24T07:50", "cpu": 57.2, "mem": 63.7, "conn": 1415, "ips": 345},
    {"t": "2026-09-24T07:55", "cpu": 56.6, "mem": 63.8, "conn": 1402, "ips": 341},
    {"t": "2026-09-24T08:00", "cpu": 56.0, "mem": 63.9, "conn": 1450, "ips": 353},
    {"t": "2026-09-24T08:05", "cpu": 55.3, "mem": 64.1, "conn": 1437, "ips": 350},
    {"t": "2026-09-24T08:10", "cpu": 54.7, "mem": 64.2, "conn": 1424, "ips": 347},
    {"t": "2026-09-24T08:15", "cpu": 54.0, "mem": 64.3, "conn": 1471, "ips": 358},
    {"t": "2026-09-24T08:20", "cpu": 60.4, "mem": 64.4, "conn": 1458, "ips": 355},
    {"t": "2026-09-24T08:25", "cpu": 59.7, "mem": 64.5, "conn": 1504, "ips": 366},
    {"t": "2026-09-24T08:30", "cpu": 59.0, "mem": 64.6, "conn": 1490, "ips": 363},
    {"t": "2026-09-24T08:35", "cpu": 58.4, "mem": 64.6, "conn": 1476, "ips": 360},
    {"t": "2026-09-24T08:40", "cpu": 57.7, "mem": 64.7, "conn": 1521, "ips": 370},
    {"t": "2026-09-24T08:45", "cpu": 57.0, "mem": 64.8, "conn": 1507, "ips": 367},
    {"t": "2026-09-24T08:50", "cpu": 56.2, "mem": 64.9, "conn": 1552, "ips": 378},
    {"t": "2026-09-24T08:55", "cpu": 62.5, "mem": 65.0, "conn": 1537, "ips": 374},
    {"t": "2026-09-24T09:00", "cpu": 61.8, "mem": 65.1, "conn": 1521, "ips": 370},
    {"t": "2026-09-24T09:05", "cpu": 61.0, "mem": 65.1, "conn": 1565, "ips": 381},
    {"t": "2026-09-24T09:10", "cpu": 60.3, "mem": 65.2, "conn": 1549, "ips": 377},
    {"t": "2026-09-24T09:15", "cpu": 59.5, "mem": 65.3, "conn": 1533, "ips": 373},
    {"t": "2026-09-24T09:20", "cpu": 58.8, "mem": 65.3, "conn": 1576, "ips": 384},
    {"t": "2026-09-24T09:25", "cpu": 58.0, "mem": 65.4, "conn": 1559, "ips": 380},
    {"t": "2026-09-24T09:30", "cpu": 64.2, "mem": 65.5, "conn": 1602, "ips": 390},
    {"t": "2026-09-24T09:35", "cpu": 63.4, "mem": 65.5, "conn": 1585, "ips": 386},
    {"t": "2026-09-24T09:40", "cpu": 62.6, "mem": 65.6, "conn": 1567, "ips": 382},
    {"t": "2026-09-24T09:45", "cpu": 61.7, "mem": 65.6, "conn": 1609, "ips": 392},
    {"t": "2026-09-24T09:50", "cpu": 60.9, "mem": 65.7, "conn": 1590, "ips": 387},
    {"t": "2026-09-24T09:55", "cpu": 60.0, "mem": 65.7, "conn": 1632, "ips": 398},
    {"t": "2026-09-24T10:00", "cpu": 59.2, "mem": 65.8, "conn": 1612, "ips": 393},
    {"t": "2026-09-24T10:05", "cpu": 65.3, "mem": 65.8, "conn": 1593, "ips": 388},
    {"t": "2026-09-24T10:10", "cpu": 64.4, "mem": 65.8, "conn": 1633, "ips": 398},
    {"t": "2026-09-24T10:15", "cpu": 63.5, "mem": 65.9, "conn": 1614, "ips": 393},
    {"t": "2026-09-24T10:20", "cpu": 62.6, "mem": 65.9, "conn": 1593, "ips": 388},
    {"t": "2026-09-24T10:25", "cpu": 61.7, "mem": 65.9, "conn": 1633, "ips": 398},
    {"t": "2026-09-24T10:30", "cpu": 60.8, "mem": 65.9, "conn": 1612, "ips": 393},
    {"t": "2026-09-24T10:35", "cpu": 59.9, "mem": 66.0, "conn": 1650, "ips": 402},
    {"t": "2026-09-24T10:40", "cpu": 65.9, "mem": 66.0, "conn": 1629, "ips": 397},
    {"t": "2026-09-24T10:45", "cpu": 64.9, "mem": 66.0, "conn": 1607, "ips": 391},
    {"t": "2026-09-24T10:50", "cpu": 64.0, "mem": 66.0, "conn": 1645, "ips": 401},
    {"t": "2026-09-24T10:55", "cpu": 63.0, "mem": 66.0, "conn": 1622, "ips": 395},
    {"t": "2026-09-24T11:00", "cpu": 62.0, "mem": 66.0, "conn": 1600, "ips": 390},
    {"t": "2026-09-24T11:05", "cpu": 61.0, "mem": 66.0, "conn": 1636, "ips": 399},
    {"t": "2026-09-24T11:10", "cpu": 60.0, "mem": 66.0, "conn": 1613, "ips": 393},
    {"t": "2026-09-24T11:15", "cpu": 65.9, "mem": 66.0, "conn": 1649, "ips": 402},
    {"t": "2026-09-24T11:20", "cpu": 64.9, "mem": 66.0, "conn": 1625, "ips": 396},
    {"t": "2026-09-24T11:25", "cpu": 63.9, "mem": 66.0, "conn": 1600, "ips": 390},
    {"t": "2026-09-24T11:30", "cpu": 62.8, "mem": 65.9, "conn": 1636, "ips": 399},
    {"t": "2026-09-24T11:35", "cpu": 61.7, "mem": 65.9, "conn": 1611, "ips": 392},
    {"t": "2026-09-24T11:40", "cpu": 60.6, "mem": 65.9, "conn": 1645, "ips": 401},
    {"t": "2026-09-24T11:45", "cpu": 59.5, "mem": 65.9, "conn": 1620, "ips": 395},
    {"t": "2026-09-24T11:50", "cpu": 65.4, "mem": 65.8, "conn": 1593, "ips": 388},
    {"t": "2026-09-24T11:55", "cpu": 64.3, "mem": 65.8, "conn": 1627, "ips": 396},
    {"t": "2026-09-24T12:00", "cpu": 63.2, "mem": 65.8, "conn": 1600, "ips": 390},
    {"t": "2026-09-24T12:05", "cpu": 62.0, "mem": 65.7, "conn": 1574, "ips": 383},
    {"t": "2026-09-24T12:10", "cpu": 60.9, "mem": 65.7, "conn": 1606, "ips": 391},
    {"t": "2026-09-24T12:15", "cpu": 59.7, "mem": 65.6, "conn": 1579, "ips": 385},
    {"t": "2026-09-24T12:20", "cpu": 58.6, "mem": 65.6, "conn": 1611, "ips": 392},
    {"t": "2026-09-24T12:25", "cpu": 64.4, "mem": 65.5, "conn": 1583, "ips": 386},
    {"t": "2026-09-24T12:30", "cpu": 63.2, "mem": 65.5, "conn": 1554, "ips": 379},
    {"t": "2026-09-24T12:35", "cpu": 62.0, "mem": 65.4, "conn": 1585, "ips": 386},
    {"t": "2026-09-24T12:40", "cpu": 60.8, "mem": 65.3, "conn": 1556, "ips": 379},
    {"t": "2026-09-24T12:45", "cpu": 59.5, "mem": 65.3, "conn": 1587, "ips": 387},
    {"t": "2026-09-24T12:50", "cpu": 58.3, "mem": 65.2, "conn": 1557, "ips": 379},
    {"t": "2026-09-24T12:55", "cpu": 57.0, "mem": 65.1, "conn": 1527, "ips": 372},
    {"t": "2026-09-24T13:00", "cpu": 62.8, "mem": 65.1, "conn": 1557, "ips": 379},
    {"t": "2026-09-24T13:05", "cpu": 61.5, "mem": 65.0, "conn": 1527, "ips": 372},
    {"t": "2026-09-24T13:10", "cpu": 60.2, "mem": 64.9, "conn": 1496, "ips": 364},
    {"t": "2026-09-24T13:15", "cpu": 59.0, "mem": 64.8, "conn": 1525, "ips": 371},
    {"t": "2026-09-24T13:20", "cpu": 57.7, "mem": 64.7, "conn": 1493, "ips": 364},
    {"t": "2026-09-24T13:25", "cpu": 56.4, "mem": 64.6, "conn": 1522, "ips": 371},
    {"t": "2026-09-24T13:30", "cpu": 55.0, "mem": 64.6, "conn": 1490, "ips": 363},
    {"t": "2026-09-24T13:35", "cpu": 60.7, "mem": 64.5, "conn": 1458, "ips": 355},
    {"t": "2026-09-24T13:40", "cpu": 59.4, "mem": 64.4, "conn": 1486, "ips": 362},
    {"t": "2026-09-24T13:45", "cpu": 58.0, "mem": 64.3, "conn": 1453, "ips": 354},
    {"t": "2026-09-24T13:50", "cpu": 56.7, "mem": 64.2, "conn": 1480, "ips": 360},
    {"t": "2026-09-24T13:55", "cpu": 55.3, "mem": 64.1, "conn": 1447, "ips": 352},
    {"t": "2026-09-24T14:00", "cpu": 54.0, "mem": 63.9, "conn": 1414, "ips": 344},
    {"t": "2026-09-24T14:05", "cpu": 52.6, "mem": 63.8, "conn": 1440, "ips": 351},
    {"t": "2026-09-24T14:10", "cpu": 58.2, "mem": 63.7, "conn": 1407, "ips": 343},
    {"t": "2026-09-24T14:15", "cpu": 56.8, "mem": 63.6, "conn": 1373, "ips": 334},
    {"t": "2026-09-24T14:20", "cpu": 55.4, "mem": 63.5, "conn": 1398, "ips": 340},
    {"t": "2026-09-24T14:25", "cpu": 54.0, "mem": 63.4, "conn": 1364, "ips": 332},
    {"t": "2026-09-24T14:30", "cpu": 52.6, "mem": 63.3, "conn": 1389, "ips": 338},
    {"t": "2026-09-24T14:35", "cpu": 51.2, "mem": 63.1, "conn": 1355, "ips": 330},
    {"t": "2026-09-24T14:40", "cpu": 49.8, "mem": 63.0, "conn": 1320, "ips": 321},
    {"t": "2026-09-24T14:45", "cpu": 55.3, "mem": 62.9, "conn": 1345, "ips": 328},
    {"t": "2026-09-24T14:50", "cpu": 53.9, "mem": 62.8, "conn": 1309, "ips": 319},
    {"t": "2026-09-24T14:55", "cpu": 52.5, "mem": 62.6, "conn": 1334, "ips": 325},
    {"t": "2026-09-24T15:00", "cpu": 51.0, "mem": 62.5, "conn": 1298, "ips": 316},
    {"t": "2026-09-24T15:05", "cpu": 49.5, "mem": 62.4, "conn": 1262, "ips": 307},
    {"t": "2026-09-24T15:10", "cpu": 48.1, "mem": 62.2, "conn": 1286, "ips": 313},
    {"t": "2026-09-24T15:15", "cpu": 46.6, "mem": 62.1, "conn": 1250, "ips": 304},
    {"t": "2026-09-24T15:20", "cpu": 52.1, "mem": 62.0, "conn": 1214, "ips": 296},
    {"t": "2026-09-24T15:25", "cpu": 50.7, "mem": 61.8, "conn": 1237, "ips": 301},
    {"t": "2026-09-24T15:30", "cpu": 49.2, "mem": 61.7, "conn": 1201, "ips": 292},
    {"t": "2026-09-24T15:35", "cpu": 47.7, "mem": 61.5, "conn": 1224, "ips": 298},
    {"t": "2026-09-24T15:40", "cpu": 46.2, "mem": 61.4, "conn": 1187, "ips": 289},
    {"t": "2026-09-24T15:45", "cpu": 44.7, "mem": 61.3, "conn": 1150, "ips": 280},
    {"t": "2026-09-24T15:50", "cpu": 43.2, "mem": 61.1, "conn": 1173, "ips": 286},
    {"t": "2026-09-24T15:55", "cpu": 48.7, "mem": 61.0, "conn": 1136, "ips": 277},
    {"t": "2026-09-24T16:00", "cpu": 47.2, "mem": 60.8, "conn": 1099, "ips": 268},
    {"t": "2026-09-24T16:05", "cpu": 45.7, "mem": 60.7, "conn": 1122, "ips": 273},
    {"t": "2026-09-24T16:10", "cpu": 44.2, "mem": 60.5, "conn": 1085, "ips": 264},
    {"t": "2026-09-24T16:15", "cpu": 42.7, "mem": 60.4, "conn": 1107, "ips": 270},
    {"t": "2026-09-24T16:20", "cpu": 41.2, "mem": 60.2, "conn": 1070, "ips": 260},
    {"t": "2026-09-24T16:25", "cpu": 39.7, "mem": 60.1, "conn": 1032, "ips": 251},
    {"t": "2026-09-24T16:30", "cpu": 45.1, "mem": 59.9, "conn": 1055, "ips": 257},
    {"t": "2026-09-24T16:35", "cpu": 43.6, "mem": 59.8, "conn": 1017, "ips": 248},
    {"t": "2026-09-24T16:40", "cpu": 42.1, "mem": 59.6, "conn": 1039, "ips": 253},
    {"t": "2026-09-24T16:45", "cpu": 40.6, "mem": 59.5, "conn": 1002, "ips": 244},
    {"t": "2026-09-24T16:50", "cpu": 39.0, "mem": 59.3, "conn": 964, "ips": 235},
    {"t": "2026-09-24T16:55", "cpu": 37.5, "mem": 59.2, "conn": 986, "ips": 240},
    {"t": "2026-09-24T17:00", "cpu": 36.0, "mem": 59.0, "conn": 949, "ips": 231},
    {"t": "2026-09-24T17:05", "cpu": 41.5, "mem": 58.8, "conn": 911, "ips": 222},
    {"t": "2026-09-24T17:10", "cpu": 40.0, "mem": 58.7, "conn": 933, "ips": 227},
    {"t": "2026-09-24T17:15", "cpu": 38.4, "mem": 58.5, "conn": 895, "ips": 218},
    {"t": "2026-09-24T17:20", "cpu": 36.9, "mem": 58.4, "conn": 918, "ips": 223},
    {"t": "2026-09-24T17:25", "cpu": 35.4, "mem": 58.2, "conn": 880, "ips": 214},
    {"t": "2026-09-24T17:30", "cpu": 33.9, "mem": 58.1, "conn": 842, "ips": 205},
    {"t": "2026-09-24T17:35", "cpu": 32.3, "mem": 57.9, "conn": 865, "ips": 210},
    {"t": "2026-09-24T17:40", "cpu": 37.8, "mem": 57.8, "conn": 827, "ips": 201},
    {"t": "2026-09-24T17:45", "cpu": 36.3, "mem": 57.6, "conn": 850, "ips": 207},
    {"t": "2026-09-24T17:50", "cpu": 34.8, "mem": 57.5, "conn": 812, "ips": 198},
    {"t": "2026-09-24T17:55", "cpu": 33.3, "mem": 57.3, "conn": 775, "ips": 189},
    {"t": "2026-09-24T18:00", "cpu": 31.8, "mem": 57.2, "conn": 798, "ips": 194},
    {"t": "2026-09-24T18:05", "cpu": 30.3, "mem": 57.0, "conn": 761, "ips": 185},
    {"t": "2026-09-24T18:10", "cpu": 28.8, "mem": 56.9, "conn": 724, "ips": 176},
    {"t": "2026-09-24T18:15", "cpu": 34.3, "mem": 56.7, "conn": 747, "ips": 182},
    {"t": "2026-09-24T18:20", "cpu": 32.8, "mem": 56.6, "conn": 710, "ips": 173},
    {"t": "2026-09-24T18:25", "cpu": 31.3, "mem": 56.5, "conn": 733, "ips": 178},
    {"t": "2026-09-24T18:30", "cpu": 29.8, "mem": 56.3, "conn": 696, "ips": 169},
    {"t": "2026-09-24T18:35", "cpu": 28.3, "mem": 56.2, "conn": 660, "ips": 160},
    {"t": "2026-09-24T18:40", "cpu": 26.9, "mem": 56.0, "conn": 683, "ips": 166},
    {"t": "2026-09-24T18:45", "cpu": 25.4, "mem": 55.9, "conn": 647, "ips": 157},
    {"t": "2026-09-24T18:50", "cpu": 30.9, "mem": 55.8, "conn": 671, "ips": 163},
    {"t": "2026-09-24T18:55", "cpu": 29.5, "mem": 55.6, "conn": 635, "ips": 154},
    {"t": "2026-09-24T19:00", "cpu": 28.0, "mem": 55.5, "conn": 599, "ips": 146},
    {"t": "2026-09-24T19:05", "cpu": 26.5, "mem": 55.4, "conn": 623, "ips": 151},
    {"t": "2026-09-24T19:10", "cpu": 25.1, "mem": 55.2, "conn": 588, "ips": 143},
    {"t": "2026-09-24T19:15", "cpu": 23.7, "mem": 55.1, "conn": 552, "ips": 134},
    {"t": "2026-09-24T19:20", "cpu": 22.2, "mem": 55.0, "conn": 577, "ips": 140},
    {"t": "2026-09-24T19:25", "cpu": 27.8, "mem": 54.9, "conn": 542, "ips": 132},
    {"t": "2026-09-24T19:30", "cpu": 26.4, "mem": 54.7, "conn": 568, "ips": 138},
    {"t": "2026-09-24T19:35", "cpu": 25.0, "mem": 54.6, "conn": 533, "ips": 130},
    {"t": "2026-09-24T19:40", "cpu": 23.6, "mem": 54.5, "conn": 499, "ips": 121},
    {"t": "2026-09-24T19:45", "cpu": 22.2, "mem": 54.4, "conn": 524, "ips": 127},
    {"t": "2026-09-24T19:50", "cpu": 20.8, "mem": 54.3, "conn": 490, "ips": 119},
    {"t": "2026-09-24T19:55", "cpu": 19.4, "mem": 54.2, "conn": 517, "ips": 126}
    ],
    "hourly": [
    {"hour": 0, "conn": 329.4, "cpu": 16.9},
    {"hour": 1, "conn": 414.5, "cpu": 19.6},
    {"hour": 2, "conn": 536.3, "cpu": 24.2},
    {"hour": 3, "conn": 691.8, "cpu": 29.9},
    {"hour": 4, "conn": 859.8, "cpu": 35.5},
    {"hour": 5, "conn": 1034.7, "cpu": 41.4},
    {"hour": 6, "conn": 1203.6, "cpu": 48.3},
    {"hour": 7, "conn": 1356.0, "cpu": 53.4},
    {"hour": 8, "conn": 1485.6, "cpu": 57.6},
    {"hour": 9, "conn": 1574.0, "cpu": 61.0},
    {"hour": 10, "conn": 1620.2, "cpu": 62.9},
    {"hour": 11, "conn": 1621.2, "cpu": 62.7},
    {"hour": 12, "conn": 1576.6, "cpu": 60.8},
    {"hour": 13, "conn": 1494.5, "cpu": 58.6},
    {"hour": 14, "conn": 1370.7, "cpu": 53.9},
    {"hour": 15, "conn": 1218.2, "cpu": 48.1},
    {"hour": 16, "conn": 1048.2, "cpu": 42.4},
    {"hour": 17, "conn": 871.4, "cpu": 36.4},
    {"hour": 18, "conn": 705.4, "cpu": 30.0},
    {"hour": 19, "conn": 551.0, "cpu": 24.2},
    {"hour": 20, "conn": 423.4, "cpu": 20.4},
    {"hour": 21, "conn": 333.0, "cpu": 16.9},
    {"hour": 22, "conn": 289.8, "cpu": 14.9},
    {"hour": 23, "conn": 286.8, "cpu": 15.7}
    ],
    "count": 288,
    "quietestHour": 23,
    "busiestHour": 11,
    "maxSamples": 576
  };
  /* پرمصرف‌ترین مشتری‌ها — شکلِ /api/admin/top-clients */
  var TOPCLIENTS = {
    "ready": true,
    "clients": [
      {
        "email": "ali_rezaei",
        "group": "de-1",
        "usedBytes": 94489280512,
        "usedGB": 88,
        "quotaGB": 100.0,
        "pctOfQuota": 88.0,
        "enable": true,
        "expiryTime": 1790000000000,
        "pctOfAll": 25.9
      },
      {
        "email": "sara.m",
        "group": "de-1",
        "usedBytes": 65498251264,
        "usedGB": 61,
        "quotaGB": 100.0,
        "pctOfQuota": 61.0,
        "enable": true,
        "expiryTime": 1790000000000,
        "pctOfAll": 18.0
      },
      {
        "email": "office_2",
        "group": "nl-1",
        "usedBytes": 57982058496,
        "usedGB": 54,
        "quotaGB": 0.0,
        "pctOfQuota": null,
        "enable": true,
        "expiryTime": 0,
        "pctOfAll": 15.9
      },
      {
        "email": "mehdi_k",
        "group": "de-1",
        "usedBytes": 44023414784,
        "usedGB": 41,
        "quotaGB": 50.0,
        "pctOfQuota": 82.0,
        "enable": true,
        "expiryTime": 1790000000000,
        "pctOfAll": 12.1
      },
      {
        "email": "reza99",
        "group": "fi-1",
        "usedBytes": 35433480192,
        "usedGB": 33,
        "quotaGB": 50.0,
        "pctOfQuota": 66.0,
        "enable": true,
        "expiryTime": 1790000000000,
        "pctOfAll": 9.7
      },
      {
        "email": "nazanin",
        "group": "nl-1",
        "usedBytes": 23622320128,
        "usedGB": 22,
        "quotaGB": 30.0,
        "pctOfQuota": 73.3,
        "enable": true,
        "expiryTime": 1790000000000,
        "pctOfAll": 6.5
      },
      {
        "email": "amir_t",
        "group": "de-1",
        "usedBytes": 19327352832,
        "usedGB": 18,
        "quotaGB": 50.0,
        "pctOfQuota": 36.0,
        "enable": true,
        "expiryTime": 1790000000000,
        "pctOfAll": 5.3
      },
      {
        "email": "hosein.b",
        "group": "fi-1",
        "usedBytes": 12884901888,
        "usedGB": 12,
        "quotaGB": 20.0,
        "pctOfQuota": 60.0,
        "enable": true,
        "expiryTime": 1790000000000,
        "pctOfAll": 3.5
      },
      {
        "email": "parisa",
        "group": "de-1",
        "usedBytes": 10200547328,
        "usedGB": 9.5,
        "quotaGB": 30.0,
        "pctOfQuota": 31.7,
        "enable": true,
        "expiryTime": 1790000000000,
        "pctOfAll": 2.8
      },
      {
        "email": "test_trial",
        "group": "de-1",
        "usedBytes": 858993459,
        "usedGB": 0.8,
        "quotaGB": 1.0,
        "pctOfQuota": 80.0,
        "enable": true,
        "expiryTime": 1790000000000,
        "pctOfAll": 0.2
      }
    ],
    "totalClients": 146,
    "totalUsedGB": 551.7
  };
  /* سنجشِ تانلِ ۱ — خروجیِ خودِ tunnels.get_metrics، با یک جهشِ تأخیر و پرت */
  var TMETRICS = {
   "samples": [
    {
     "id": 1,
     "tunnel_id": 1,
     "tcp_avg": 59.5,
     "tcp_min": 51.0,
     "tcp_max": 79.0,
     "jitter": 2.2,
     "loss": 0.0,
     "icmp_avg": 54.0,
     "http_avg": 100.0,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 58.0, \"min\": 51.0, \"max\": 76.0, \"jitter\": 2.0, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 61.0, \"min\": 53.0, \"max\": 79.0, \"jitter\": 2.4, \"loss\": 0}}, \"icmp\": {\"avg\": 54.0}, \"http\": {\"avg\": 100.0}}",
     "created_at": "2026-09-24 14:00:00"
    },
    {
     "id": 2,
     "tunnel_id": 1,
     "tcp_avg": 69.3,
     "tcp_min": 60.8,
     "tcp_max": 88.8,
     "jitter": 2.9,
     "loss": 0.0,
     "icmp_avg": 63.8,
     "http_avg": 109.8,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 67.8, \"min\": 60.8, \"max\": 85.8, \"jitter\": 2.7, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 70.8, \"min\": 62.8, \"max\": 88.8, \"jitter\": 3.0, \"loss\": 0}}, \"icmp\": {\"avg\": 63.8}, \"http\": {\"avg\": 109.8}}",
     "created_at": "2026-09-24 14:10:00"
    },
    {
     "id": 3,
     "tunnel_id": 1,
     "tcp_avg": 70.0,
     "tcp_min": 61.5,
     "tcp_max": 89.5,
     "jitter": 3.5,
     "loss": 0.0,
     "icmp_avg": 64.5,
     "http_avg": 110.5,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 68.5, \"min\": 61.5, \"max\": 86.5, \"jitter\": 3.4, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 71.5, \"min\": 63.5, \"max\": 89.5, \"jitter\": 3.6, \"loss\": 0}}, \"icmp\": {\"avg\": 64.5}, \"http\": {\"avg\": 110.5}}",
     "created_at": "2026-09-24 14:20:00"
    },
    {
     "id": 4,
     "tunnel_id": 1,
     "tcp_avg": 70.4,
     "tcp_min": 61.9,
     "tcp_max": 89.9,
     "jitter": 3.2,
     "loss": 0.0,
     "icmp_avg": 64.9,
     "http_avg": 110.9,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 68.9, \"min\": 61.9, \"max\": 86.9, \"jitter\": 4.1, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 71.9, \"min\": 63.9, \"max\": 89.9, \"jitter\": 2.4, \"loss\": 0}}, \"icmp\": {\"avg\": 64.9}, \"http\": {\"avg\": 110.9}}",
     "created_at": "2026-09-24 14:30:00"
    },
    {
     "id": 5,
     "tunnel_id": 1,
     "tcp_avg": 70.5,
     "tcp_min": 62.0,
     "tcp_max": 90.0,
     "jitter": 2.5,
     "loss": 0.0,
     "icmp_avg": 65.0,
     "http_avg": 111.0,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 69.0, \"min\": 62.0, \"max\": 87.0, \"jitter\": 2.0, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 72.0, \"min\": 64.0, \"max\": 90.0, \"jitter\": 3.0, \"loss\": 0}}, \"icmp\": {\"avg\": 65.0}, \"http\": {\"avg\": 111.0}}",
     "created_at": "2026-09-24 14:40:00"
    },
    {
     "id": 6,
     "tunnel_id": 1,
     "tcp_avg": 79.3,
     "tcp_min": 70.8,
     "tcp_max": 98.8,
     "jitter": 3.2,
     "loss": 0.0,
     "icmp_avg": 73.8,
     "http_avg": 119.8,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 77.8, \"min\": 70.8, \"max\": 95.8, \"jitter\": 2.7, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 80.8, \"min\": 72.8, \"max\": 98.8, \"jitter\": 3.6, \"loss\": 0}}, \"icmp\": {\"avg\": 73.8}, \"http\": {\"avg\": 119.8}}",
     "created_at": "2026-09-24 14:50:00"
    },
    {
     "id": 7,
     "tunnel_id": 1,
     "tcp_avg": 78.5,
     "tcp_min": 70.0,
     "tcp_max": 98.0,
     "jitter": 2.9,
     "loss": 0.0,
     "icmp_avg": 73.0,
     "http_avg": 119.0,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 77.0, \"min\": 70.0, \"max\": 95.0, \"jitter\": 3.4, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 80.0, \"min\": 72.0, \"max\": 98.0, \"jitter\": 2.4, \"loss\": 0}}, \"icmp\": {\"avg\": 73.0}, \"http\": {\"avg\": 119.0}}",
     "created_at": "2026-09-24 15:00:00"
    },
    {
     "id": 8,
     "tunnel_id": 1,
     "tcp_avg": 77.3,
     "tcp_min": 68.8,
     "tcp_max": 96.8,
     "jitter": 3.5,
     "loss": 0.0,
     "icmp_avg": 71.8,
     "http_avg": 117.8,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 75.8, \"min\": 68.8, \"max\": 93.8, \"jitter\": 4.1, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 78.8, \"min\": 70.8, \"max\": 96.8, \"jitter\": 3.0, \"loss\": 0}}, \"icmp\": {\"avg\": 71.8}, \"http\": {\"avg\": 117.8}}",
     "created_at": "2026-09-24 15:10:00"
    },
    {
     "id": 9,
     "tunnel_id": 1,
     "tcp_avg": 75.5,
     "tcp_min": 67.0,
     "tcp_max": 95.0,
     "jitter": 2.8,
     "loss": 0.0,
     "icmp_avg": 70.0,
     "http_avg": 116.0,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 74.0, \"min\": 67.0, \"max\": 92.0, \"jitter\": 2.0, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 77.0, \"min\": 69.0, \"max\": 95.0, \"jitter\": 3.6, \"loss\": 0}}, \"icmp\": {\"avg\": 70.0}, \"http\": {\"avg\": 116.0}}",
     "created_at": "2026-09-24 15:20:00"
    },
    {
     "id": 10,
     "tunnel_id": 1,
     "tcp_avg": 73.1,
     "tcp_min": 64.6,
     "tcp_max": 92.6,
     "jitter": 2.5,
     "loss": 0.0,
     "icmp_avg": 67.6,
     "http_avg": 113.6,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 71.6, \"min\": 64.6, \"max\": 89.6, \"jitter\": 2.7, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 74.6, \"min\": 66.6, \"max\": 92.6, \"jitter\": 2.4, \"loss\": 0}}, \"icmp\": {\"avg\": 67.6}, \"http\": {\"avg\": 113.6}}",
     "created_at": "2026-09-24 15:30:00"
    },
    {
     "id": 11,
     "tunnel_id": 1,
     "tcp_avg": 79.2,
     "tcp_min": 70.7,
     "tcp_max": 98.7,
     "jitter": 3.2,
     "loss": 0.0,
     "icmp_avg": 73.7,
     "http_avg": 119.7,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 77.7, \"min\": 70.7, \"max\": 95.7, \"jitter\": 3.4, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 80.7, \"min\": 72.7, \"max\": 98.7, \"jitter\": 3.0, \"loss\": 0}}, \"icmp\": {\"avg\": 73.7}, \"http\": {\"avg\": 119.7}}",
     "created_at": "2026-09-24 15:40:00"
    },
    {
     "id": 12,
     "tunnel_id": 1,
     "tcp_avg": 75.8,
     "tcp_min": 67.3,
     "tcp_max": 95.3,
     "jitter": 3.8,
     "loss": 0.0,
     "icmp_avg": 70.3,
     "http_avg": 116.3,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 74.3, \"min\": 67.3, \"max\": 92.3, \"jitter\": 4.1, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 77.3, \"min\": 69.3, \"max\": 95.3, \"jitter\": 3.6, \"loss\": 0}}, \"icmp\": {\"avg\": 70.3}, \"http\": {\"avg\": 116.3}}",
     "created_at": "2026-09-24 15:50:00"
    },
    {
     "id": 13,
     "tunnel_id": 1,
     "tcp_avg": 72.0,
     "tcp_min": 63.5,
     "tcp_max": 91.5,
     "jitter": 2.2,
     "loss": 0.0,
     "icmp_avg": 66.5,
     "http_avg": 112.5,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 70.5, \"min\": 63.5, \"max\": 88.5, \"jitter\": 2.0, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 73.5, \"min\": 65.5, \"max\": 91.5, \"jitter\": 2.4, \"loss\": 0}}, \"icmp\": {\"avg\": 66.5}, \"http\": {\"avg\": 112.5}}",
     "created_at": "2026-09-24 16:00:00"
    },
    {
     "id": 14,
     "tunnel_id": 1,
     "tcp_avg": 67.7,
     "tcp_min": 59.2,
     "tcp_max": 87.2,
     "jitter": 2.9,
     "loss": 0.0,
     "icmp_avg": 62.2,
     "http_avg": 108.2,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 66.2, \"min\": 59.2, \"max\": 84.2, \"jitter\": 2.7, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 69.2, \"min\": 61.2, \"max\": 87.2, \"jitter\": 3.0, \"loss\": 0}}, \"icmp\": {\"avg\": 62.2}, \"http\": {\"avg\": 108.2}}",
     "created_at": "2026-09-24 16:10:00"
    },
    {
     "id": 15,
     "tunnel_id": 1,
     "tcp_avg": 72.2,
     "tcp_min": 63.7,
     "tcp_max": 91.7,
     "jitter": 3.5,
     "loss": 0.0,
     "icmp_avg": 66.7,
     "http_avg": 112.7,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 70.7, \"min\": 63.7, \"max\": 88.7, \"jitter\": 3.4, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 73.7, \"min\": 65.7, \"max\": 91.7, \"jitter\": 3.6, \"loss\": 0}}, \"icmp\": {\"avg\": 66.7}, \"http\": {\"avg\": 112.7}}",
     "created_at": "2026-09-24 16:20:00"
    },
    {
     "id": 16,
     "tunnel_id": 1,
     "tcp_avg": 67.5,
     "tcp_min": 59.0,
     "tcp_max": 87.0,
     "jitter": 3.2,
     "loss": 0.0,
     "icmp_avg": 62.0,
     "http_avg": 108.0,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 66.0, \"min\": 59.0, \"max\": 84.0, \"jitter\": 4.1, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 69.0, \"min\": 61.0, \"max\": 87.0, \"jitter\": 2.4, \"loss\": 0}}, \"icmp\": {\"avg\": 62.0}, \"http\": {\"avg\": 108.0}}",
     "created_at": "2026-09-24 16:30:00"
    },
    {
     "id": 17,
     "tunnel_id": 1,
     "tcp_avg": 62.7,
     "tcp_min": 54.2,
     "tcp_max": 82.2,
     "jitter": 2.5,
     "loss": 0.0,
     "icmp_avg": 57.2,
     "http_avg": 103.2,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 61.2, \"min\": 54.2, \"max\": 79.2, \"jitter\": 2.0, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 64.2, \"min\": 56.2, \"max\": 82.2, \"jitter\": 3.0, \"loss\": 0}}, \"icmp\": {\"avg\": 57.2}, \"http\": {\"avg\": 103.2}}",
     "created_at": "2026-09-24 16:40:00"
    },
    {
     "id": 18,
     "tunnel_id": 1,
     "tcp_avg": 57.9,
     "tcp_min": 49.4,
     "tcp_max": 77.4,
     "jitter": 3.2,
     "loss": 0.0,
     "icmp_avg": 52.4,
     "http_avg": 98.4,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 56.4, \"min\": 49.4, \"max\": 74.4, \"jitter\": 2.7, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 59.4, \"min\": 51.4, \"max\": 77.4, \"jitter\": 3.6, \"loss\": 0}}, \"icmp\": {\"avg\": 52.4}, \"http\": {\"avg\": 98.4}}",
     "created_at": "2026-09-24 16:50:00"
    },
    {
     "id": 19,
     "tunnel_id": 1,
     "tcp_avg": 53.3,
     "tcp_min": 44.8,
     "tcp_max": 72.8,
     "jitter": 2.9,
     "loss": 0.0,
     "icmp_avg": 47.8,
     "http_avg": 93.8,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 51.8, \"min\": 44.8, \"max\": 69.8, \"jitter\": 3.4, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 54.8, \"min\": 46.8, \"max\": 72.8, \"jitter\": 2.4, \"loss\": 0}}, \"icmp\": {\"avg\": 47.8}, \"http\": {\"avg\": 93.8}}",
     "created_at": "2026-09-24 17:00:00"
    },
    {
     "id": 20,
     "tunnel_id": 1,
     "tcp_avg": 57.9,
     "tcp_min": 49.4,
     "tcp_max": 77.4,
     "jitter": 3.5,
     "loss": 0.0,
     "icmp_avg": 52.4,
     "http_avg": 98.4,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 56.4, \"min\": 49.4, \"max\": 74.4, \"jitter\": 4.1, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 59.4, \"min\": 51.4, \"max\": 77.4, \"jitter\": 3.0, \"loss\": 0}}, \"icmp\": {\"avg\": 52.4}, \"http\": {\"avg\": 98.4}}",
     "created_at": "2026-09-24 17:10:00"
    },
    {
     "id": 21,
     "tunnel_id": 1,
     "tcp_avg": 53.9,
     "tcp_min": 45.4,
     "tcp_max": 73.4,
     "jitter": 2.8,
     "loss": 0.0,
     "icmp_avg": 48.4,
     "http_avg": 94.4,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 52.4, \"min\": 45.4, \"max\": 70.4, \"jitter\": 2.0, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 55.4, \"min\": 47.4, \"max\": 73.4, \"jitter\": 3.6, \"loss\": 0}}, \"icmp\": {\"avg\": 48.4}, \"http\": {\"avg\": 94.4}}",
     "created_at": "2026-09-24 17:20:00"
    },
    {
     "id": 22,
     "tunnel_id": 1,
     "tcp_avg": 240.3,
     "tcp_min": 41.8,
     "tcp_max": 259.8,
     "jitter": 2.5,
     "loss": 0.0,
     "icmp_avg": 44.8,
     "http_avg": 90.8,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 238.8, \"min\": 41.8, \"max\": 256.8, \"jitter\": 2.7, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 241.8, \"min\": 43.8, \"max\": 259.8, \"jitter\": 2.4, \"loss\": 0}}, \"icmp\": {\"avg\": 44.8}, \"http\": {\"avg\": 90.8}}",
     "created_at": "2026-09-24 17:30:00"
    },
    {
     "id": 23,
     "tunnel_id": 1,
     "tcp_avg": 237.2,
     "tcp_min": 38.7,
     "tcp_max": 256.7,
     "jitter": 3.2,
     "loss": 6.0,
     "icmp_avg": 41.7,
     "http_avg": 87.7,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 235.7, \"min\": 38.7, \"max\": 253.7, \"jitter\": 3.4, \"loss\": 12}, \"8443\": {\"ok\": true, \"avg\": 238.7, \"min\": 40.7, \"max\": 256.7, \"jitter\": 3.0, \"loss\": 0}}, \"icmp\": {\"avg\": 41.7}, \"http\": {\"avg\": 87.7}}",
     "created_at": "2026-09-24 17:40:00"
    },
    {
     "id": 24,
     "tunnel_id": 1,
     "tcp_avg": 53.6,
     "tcp_min": 45.1,
     "tcp_max": 73.1,
     "jitter": 3.8,
     "loss": 0.0,
     "icmp_avg": 48.1,
     "http_avg": 94.1,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 52.1, \"min\": 45.1, \"max\": 70.1, \"jitter\": 4.1, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 55.1, \"min\": 47.1, \"max\": 73.1, \"jitter\": 3.6, \"loss\": 0}}, \"icmp\": {\"avg\": 48.1}, \"http\": {\"avg\": 94.1}}",
     "created_at": "2026-09-24 17:50:00"
    },
    {
     "id": 25,
     "tunnel_id": 1,
     "tcp_avg": 51.6,
     "tcp_min": 43.1,
     "tcp_max": 71.1,
     "jitter": 2.2,
     "loss": 0.0,
     "icmp_avg": 46.1,
     "http_avg": 92.1,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 50.1, \"min\": 43.1, \"max\": 68.1, \"jitter\": 2.0, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 53.1, \"min\": 45.1, \"max\": 71.1, \"jitter\": 2.4, \"loss\": 0}}, \"icmp\": {\"avg\": 46.1}, \"http\": {\"avg\": 92.1}}",
     "created_at": "2026-09-24 18:00:00"
    },
    {
     "id": 26,
     "tunnel_id": 1,
     "tcp_avg": 50.1,
     "tcp_min": 41.6,
     "tcp_max": 69.6,
     "jitter": 2.9,
     "loss": 0.0,
     "icmp_avg": 44.6,
     "http_avg": 90.6,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 48.6, \"min\": 41.6, \"max\": 66.6, \"jitter\": 2.7, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 51.6, \"min\": 43.6, \"max\": 69.6, \"jitter\": 3.0, \"loss\": 0}}, \"icmp\": {\"avg\": 44.6}, \"http\": {\"avg\": 90.6}}",
     "created_at": "2026-09-24 18:10:00"
    },
    {
     "id": 27,
     "tunnel_id": 1,
     "tcp_avg": 49.1,
     "tcp_min": 40.6,
     "tcp_max": 68.6,
     "jitter": 3.5,
     "loss": 0.0,
     "icmp_avg": 43.6,
     "http_avg": 89.6,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 47.6, \"min\": 40.6, \"max\": 65.6, \"jitter\": 3.4, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 50.6, \"min\": 42.6, \"max\": 68.6, \"jitter\": 3.6, \"loss\": 0}}, \"icmp\": {\"avg\": 43.6}, \"http\": {\"avg\": 89.6}}",
     "created_at": "2026-09-24 18:20:00"
    },
    {
     "id": 28,
     "tunnel_id": 1,
     "tcp_avg": 48.7,
     "tcp_min": 40.2,
     "tcp_max": 68.2,
     "jitter": 3.2,
     "loss": 0.0,
     "icmp_avg": 43.2,
     "http_avg": 89.2,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 47.2, \"min\": 40.2, \"max\": 65.2, \"jitter\": 4.1, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 50.2, \"min\": 42.2, \"max\": 68.2, \"jitter\": 2.4, \"loss\": 0}}, \"icmp\": {\"avg\": 43.2}, \"http\": {\"avg\": 89.2}}",
     "created_at": "2026-09-24 18:30:00"
    },
    {
     "id": 29,
     "tunnel_id": 1,
     "tcp_avg": 57.7,
     "tcp_min": 49.2,
     "tcp_max": 77.2,
     "jitter": 2.5,
     "loss": 0.0,
     "icmp_avg": 52.2,
     "http_avg": 98.2,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 56.2, \"min\": 49.2, \"max\": 74.2, \"jitter\": 2.0, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 59.2, \"min\": 51.2, \"max\": 77.2, \"jitter\": 3.0, \"loss\": 0}}, \"icmp\": {\"avg\": 52.2}, \"http\": {\"avg\": 98.2}}",
     "created_at": "2026-09-24 18:40:00"
    },
    {
     "id": 30,
     "tunnel_id": 1,
     "tcp_avg": 58.0,
     "tcp_min": 49.5,
     "tcp_max": 77.5,
     "jitter": 3.2,
     "loss": 0.0,
     "icmp_avg": 52.5,
     "http_avg": 98.5,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 56.5, \"min\": 49.5, \"max\": 74.5, \"jitter\": 2.7, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 59.5, \"min\": 51.5, \"max\": 77.5, \"jitter\": 3.6, \"loss\": 0}}, \"icmp\": {\"avg\": 52.5}, \"http\": {\"avg\": 98.5}}",
     "created_at": "2026-09-24 18:50:00"
    },
    {
     "id": 31,
     "tunnel_id": 1,
     "tcp_avg": 58.6,
     "tcp_min": 50.1,
     "tcp_max": 78.1,
     "jitter": 2.9,
     "loss": 0.0,
     "icmp_avg": 53.1,
     "http_avg": 99.1,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 57.1, \"min\": 50.1, \"max\": 75.1, \"jitter\": 3.4, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 60.1, \"min\": 52.1, \"max\": 78.1, \"jitter\": 2.4, \"loss\": 0}}, \"icmp\": {\"avg\": 53.1}, \"http\": {\"avg\": 99.1}}",
     "created_at": "2026-09-24 19:00:00"
    },
    {
     "id": 32,
     "tunnel_id": 1,
     "tcp_avg": 59.3,
     "tcp_min": 50.8,
     "tcp_max": 78.8,
     "jitter": 3.5,
     "loss": 0.0,
     "icmp_avg": 53.8,
     "http_avg": 99.8,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 57.8, \"min\": 50.8, \"max\": 75.8, \"jitter\": 4.1, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 60.8, \"min\": 52.8, \"max\": 78.8, \"jitter\": 3.0, \"loss\": 0}}, \"icmp\": {\"avg\": 53.8}, \"http\": {\"avg\": 99.8}}",
     "created_at": "2026-09-24 19:10:00"
    },
    {
     "id": 33,
     "tunnel_id": 1,
     "tcp_avg": 69.1,
     "tcp_min": 60.6,
     "tcp_max": 88.6,
     "jitter": 2.8,
     "loss": 0.0,
     "icmp_avg": 63.6,
     "http_avg": 109.6,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 67.6, \"min\": 60.6, \"max\": 85.6, \"jitter\": 2.0, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 70.6, \"min\": 62.6, \"max\": 88.6, \"jitter\": 3.6, \"loss\": 0}}, \"icmp\": {\"avg\": 63.6}, \"http\": {\"avg\": 109.6}}",
     "created_at": "2026-09-24 19:20:00"
    },
    {
     "id": 34,
     "tunnel_id": 1,
     "tcp_avg": 69.9,
     "tcp_min": 61.4,
     "tcp_max": 89.4,
     "jitter": 2.5,
     "loss": 0.0,
     "icmp_avg": 64.4,
     "http_avg": 110.4,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 68.4, \"min\": 61.4, \"max\": 86.4, \"jitter\": 2.7, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 71.4, \"min\": 63.4, \"max\": 89.4, \"jitter\": 2.4, \"loss\": 0}}, \"icmp\": {\"avg\": 64.4}, \"http\": {\"avg\": 110.4}}",
     "created_at": "2026-09-24 19:30:00"
    },
    {
     "id": 35,
     "tunnel_id": 1,
     "tcp_avg": 70.4,
     "tcp_min": 61.9,
     "tcp_max": 89.9,
     "jitter": 3.2,
     "loss": 0.0,
     "icmp_avg": 64.9,
     "http_avg": 110.9,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 68.9, \"min\": 61.9, \"max\": 86.9, \"jitter\": 3.4, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 71.9, \"min\": 63.9, \"max\": 89.9, \"jitter\": 3.0, \"loss\": 0}}, \"icmp\": {\"avg\": 64.9}, \"http\": {\"avg\": 110.9}}",
     "created_at": "2026-09-24 19:40:00"
    },
    {
     "id": 36,
     "tunnel_id": 1,
     "tcp_avg": 70.7,
     "tcp_min": 62.2,
     "tcp_max": 90.2,
     "jitter": 3.8,
     "loss": 0.0,
     "icmp_avg": 65.2,
     "http_avg": 111.2,
     "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 69.2, \"min\": 62.2, \"max\": 87.2, \"jitter\": 4.1, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 72.2, \"min\": 64.2, \"max\": 90.2, \"jitter\": 3.6, \"loss\": 0}}, \"icmp\": {\"avg\": 65.2}, \"http\": {\"avg\": 111.2}}",
     "created_at": "2026-09-24 19:50:00",
     "detail": {
      "tcp": {
       "443": {
        "ok": true,
        "avg": 69.2,
        "min": 62.2,
        "max": 87.2,
        "jitter": 4.1,
        "loss": 0
       },
       "8443": {
        "ok": true,
        "avg": 72.2,
        "min": 64.2,
        "max": 90.2,
        "jitter": 3.6,
        "loss": 0
       }
      },
      "icmp": {
       "avg": 65.2
      },
      "http": {
       "avg": 111.2
      }
     }
    }
   ],
   "summary": {
    "count": 36,
    "latest": 70.7,
    "best": 48.7,
    "worst": 240.3,
    "average": 74.7,
    "lossAvg": 0.2,
    "since": "2026-09-24 14:00:00",
    "quality": "خوب"
   },
   "latest": {
    "id": 36,
    "tunnel_id": 1,
    "tcp_avg": 70.7,
    "tcp_min": 62.2,
    "tcp_max": 90.2,
    "jitter": 3.8,
    "loss": 0.0,
    "icmp_avg": 65.2,
    "http_avg": 111.2,
    "raw": "{\"tcp\": {\"443\": {\"ok\": true, \"avg\": 69.2, \"min\": 62.2, \"max\": 87.2, \"jitter\": 4.1, \"loss\": 0}, \"8443\": {\"ok\": true, \"avg\": 72.2, \"min\": 64.2, \"max\": 90.2, \"jitter\": 3.6, \"loss\": 0}}, \"icmp\": {\"avg\": 65.2}, \"http\": {\"avg\": 111.2}}",
    "created_at": "2026-09-24 19:50:00",
    "detail": {
     "tcp": {
      "443": {
       "ok": true,
       "avg": 69.2,
       "min": 62.2,
       "max": 87.2,
       "jitter": 4.1,
       "loss": 0
      },
      "8443": {
       "ok": true,
       "avg": 72.2,
       "min": 64.2,
       "max": 90.2,
       "jitter": 3.6,
       "loss": 0
      }
     },
     "icmp": {
      "avg": 65.2
     },
     "http": {
      "avg": 111.2
     }
    }
   }
  };
  /* سلامتِ همه‌ی سرورها — یکی هشدار، یکی بحرانی، یکی بی‌گزارش */
  var HEALTH_ALL = {
   "ready": true,
   "level": "crit",
   "servers": [
    {
     "level": "warn",
     "summary": "۲ هشدار",
     "checks": [
      {
       "key": "disk",
       "title": "فضای دیسک",
       "level": "ok",
       "detail": "47٪ پر · 42.0 GB آزاد",
       "hint": ""
      },
      {
       "key": "memory",
       "title": "حافظه",
       "level": "ok",
       "detail": "61٪ مصرف · 3.1 GB آزاد",
       "hint": ""
      },
      {
       "key": "load",
       "title": "بار پردازنده",
       "level": "ok",
       "detail": "1.52 روی 4 هسته",
       "hint": ""
      },
      {
       "key": "uptime",
       "title": "مدت روشن بودن",
       "level": "ok",
       "detail": "12 روز",
       "hint": ""
      },
      {
       "key": "dns",
       "title": "DNS",
       "level": "ok",
       "detail": "10 ms",
       "hint": ""
      },
      {
       "key": "ipv6",
       "title": "IPv6",
       "level": "warn",
       "detail": "آدرس IPv6 ندارد",
       "hint": "اگر لازم نیست، نادیده بگیرید"
      },
      {
       "key": "cert",
       "title": "گواهی SSL",
       "level": "warn",
       "detail": "۱۱ روز تا انقضا",
       "hint": "certbot renew --dry-run را امتحان کنید"
      },
      {
       "key": "ports",
       "title": "پورت‌های سرویس",
       "level": "ok",
       "detail": "443، 2053، 8443 باز",
       "hint": ""
      }
     ],
     "counts": {
      "ok": 6,
      "warn": 2,
      "crit": 0
     },
     "at": "2026-09-24 20:31:40",
     "server": "سرور پنل",
     "nodeId": null
    },
    {
     "level": "crit",
     "summary": "۱ مشکل جدی",
     "checks": [
      {
       "key": "disk",
       "title": "فضای دیسک",
       "level": "crit",
       "detail": "94٪ پر · 1.9 GB آزاد",
       "hint": "لاگ‌ها را پاک کنید: journalctl --vacuum-size=200M و بزرگ‌ترین پوشه‌ها را با du -sh /* ببینید"
      },
      {
       "key": "memory",
       "title": "حافظه",
       "level": "ok",
       "detail": "44٪ مصرف",
       "hint": ""
      },
      {
       "key": "load",
       "title": "بار پردازنده",
       "level": "ok",
       "detail": "0.61 روی 2 هسته",
       "hint": ""
      },
      {
       "key": "dns",
       "title": "DNS",
       "level": "ok",
       "detail": "22 ms",
       "hint": ""
      }
     ],
     "counts": {
      "ok": 3,
      "warn": 0,
      "crit": 1
     },
     "at": "2026-09-24 20:29:02",
     "server": "ایران-۱",
     "nodeId": 1
    },
    {
     "server": "آلمان-۱",
     "nodeId": 2,
     "level": "unknown",
     "summary": "هنوز گزارشی نرسیده",
     "checks": []
    }
   ],
   "at": "2026-09-24 20:31:40"
  };

  /* تانل — عیناً شکلِ /api/admin/tunnel/overview (test-contract می‌سنجد).
     نسخه‌ی قبلی نام‌های ساده‌شده داشت (cpu، host، label) که در بکند
     نیستند؛ صفحه‌ها در هارنس شاخه‌هایی را نشان می‌دادند که روی سرور نیست.
     موتورها از خودِ بکند. یک سرورِ آفلاین و یک تانلِ خطادار هم هست تا
     آن حالت‌ها دیده شوند. */
  /* کارهای تانل — دو کارِ قدیمی تا فهرستِ «کارهای اخیر» خالی نباشد */
  var TJOBS = [
    { id: 90, tunnel: 1, action: "apply", status: "done", created_at: "2026-09-24 08:11:40", done_at: "2026-09-24 08:12:03", result: "service started" },
    { id: 91, tunnel: 2, action: "apply", status: "failed", created_at: "2026-09-24 08:11:40", done_at: "2026-09-24 08:12:10", result: "Job for nexora-tunnel-2.service failed because the control process exited with error code." },
  ];

  var TUNNEL = {
    "ready": true,
    "stats": {
      "nodes": 3,
      "online": 2,
      "tunnels": 2,
      "running": 1
    },
    "nodes": [
      {
        "id": 1,
        "name": "ایران-۱",
        "token": "nxa_Ab3dE1…",
        "role": "iran",
        "public_ip": "203.0.113.4",
        "note": "",
        "last_seen": "2026-09-24T20:30:40",
        "agent_version": "1.4.0",
        "os_info": "Ubuntu 22.04",
        "cpu_percent": 23.5,
        "mem_percent": 41.2,
        "disk_percent": 37.0,
        "uptime_sec": 1036800,
        "health_at": null,
        "sysmon_at": null,
        "enabled": 1,
        "created_at": "2026-08-02 10:00:00",
        "tunnel_count": 2,
        "running_count": 1,
        "online": true
      },
      {
        "id": 2,
        "name": "آلمان-۱",
        "token": "nxa_Ab3dE2…",
        "role": "foreign",
        "public_ip": "198.51.100.20",
        "note": "",
        "last_seen": "2026-09-24T20:30:40",
        "agent_version": "1.4.0",
        "os_info": "Debian 12",
        "cpu_percent": 11.0,
        "mem_percent": 28.4,
        "disk_percent": 22.0,
        "uptime_sec": 2592000,
        "health_at": null,
        "sysmon_at": null,
        "enabled": 1,
        "created_at": "2026-08-02 10:00:00",
        "tunnel_count": 0,
        "running_count": 0,
        "online": true
      },
      {
        "id": 3,
        "name": "فنلاند-۱",
        "token": "nxa_Ab3dE3…",
        "role": "foreign",
        "public_ip": "198.51.100.9",
        "note": "",
        "last_seen": "2026-09-23T04:11:02",
        "agent_version": "1.4.0",
        "os_info": "Ubuntu 22.04",
        "cpu_percent": null,
        "mem_percent": null,
        "disk_percent": null,
        "uptime_sec": null,
        "health_at": null,
        "sysmon_at": null,
        "enabled": 1,
        "created_at": "2026-08-02 10:00:00",
        "tunnel_count": 0,
        "running_count": 0,
        "online": false
      }
    ],
    "tunnels": [
      {
        "id": 1,
        "name": "تانل آلمان",
        "engine": "backhaul",
        "transport": "tcpmux",
        "node_id": 1,
        "foreign_node": 2,
        "remote_host": "198.51.100.20",
        "bridge_port": 3081,
        "ports": [
          {
            "local": 443,
            "remote": 443
          },
          {
            "local": 8443,
            "remote": 8443
          }
        ],
        "secret": "••••••",
        "options": {},
        "enabled": 1,
        "status": "running",
        "last_error": null,
        "last_check": "2026-09-24T20:30:40",
        "created_at": "2026-08-02 10:00:00",
        "updated_at": "2026-09-20 18:00:00",
        "node_name": "ایران-۱",
        "node_seen": "2026-09-24T20:30:40",
        "node_ip": "203.0.113.4",
        "engineName": "Backhaul",
        "nodeOnline": true
      },
      {
        "id": 2,
        "name": "تانل فنلاند",
        "engine": "rathole",
        "transport": "tcp",
        "node_id": 1,
        "foreign_node": 3,
        "remote_host": "198.51.100.9",
        "bridge_port": 3082,
        "ports": [
          {
            "local": 2053,
            "remote": 2053
          }
        ],
        "secret": "••••••",
        "options": {},
        "enabled": 1,
        "status": "failed",
        "last_error": "اتصال به سرورِ خارج برقرار نشد — سرورِ فنلاند آفلاین است",
        "last_check": "2026-09-24T20:30:40",
        "created_at": "2026-08-02 10:00:00",
        "updated_at": "2026-09-20 18:00:00",
        "node_name": "ایران-۱",
        "node_seen": "2026-09-24T20:30:40",
        "node_ip": "203.0.113.4",
        "engineName": "Rathole",
        "nodeOnline": true
      }
    ],
    "events": [
      {
        "id": 4,
        "node_id": 1,
        "tunnel_id": 2,
        "level": "error",
        "message": "تانل فنلاند قطع شد — تلاشِ دوباره",
        "created_at": "2026-09-24 03:00:00",
        "node_name": "ایران-۱",
        "tunnel_name": "تانل فنلاند"
      },
      {
        "id": 3,
        "node_id": 1,
        "tunnel_id": 1,
        "level": "warn",
        "message": "تأخیرِ تانل آلمان بالای ۳۰۰ میلی‌ثانیه",
        "created_at": "2026-09-24 01:00:00",
        "node_name": "ایران-۱",
        "tunnel_name": "تانل آلمان"
      },
      {
        "id": 2,
        "node_id": 2,
        "tunnel_id": null,
        "level": "info",
        "message": "سرورِ آلمان-۱ آنلاین شد",
        "created_at": "2026-09-23 22:10:00",
        "node_name": "آلمان-۱",
        "tunnel_name": null
      },
      {
        "id": 1,
        "node_id": 1,
        "tunnel_id": 1,
        "level": "info",
        "message": "تانل آلمان دوباره وصل شد",
        "created_at": "2026-09-23 20:00:00",
        "node_name": "ایران-۱",
        "tunnel_name": "تانل آلمان"
      }
    ],
    "engines": [
      {
        "key": "backhaul",
        "name": "Backhaul",
        "desc": "سریع و پایدار برای شرایط ایران — پیشنهاد اول",
        "repo": "Musixal/Backhaul",
        "binaries": [
          "backhaul"
        ],
        "config": "toml",
        "transports": [
          "tcp",
          "tcpmux",
          "ws",
          "wss",
          "wsmux",
          "wssmux",
          "utcpmux",
          "uwsmux"
        ],
        "default_transport": "tcpmux",
        "recommended": true
      },
      {
        "key": "rathole",
        "name": "Rathole",
        "desc": "سبک و کم‌مصرف، نوشته‌شده با Rust",
        "repo": "rapiz1/rathole",
        "binaries": [
          "rathole"
        ],
        "config": "toml",
        "transports": [
          "tcp",
          "tls",
          "noise",
          "websocket"
        ],
        "default_transport": "tcp",
        "recommended": false
      },
      {
        "key": "gost",
        "name": "GOST",
        "desc": "انعطاف‌پذیر با پروتکل‌های متنوع",
        "repo": "go-gost/gost",
        "binaries": [
          "gost"
        ],
        "config": "yaml",
        "transports": [
          "tcp",
          "ws",
          "wss",
          "mws",
          "mwss",
          "grpc",
          "quic"
        ],
        "default_transport": "mws",
        "recommended": false
      },
      {
        "key": "frp",
        "name": "FRP",
        "desc": "پرکاربرد و باثبات، با پنل وضعیت داخلی",
        "repo": "fatedier/frp",
        "binaries": [
          "frps",
          "frpc"
        ],
        "config": "toml",
        "transports": [
          "tcp",
          "kcp",
          "quic",
          "websocket"
        ],
        "default_transport": "tcp",
        "recommended": false
      },
      {
        "key": "chisel",
        "name": "Chisel",
        "desc": "روی HTTP سوار می‌شود — وقتی بقیه بسته می‌شوند جواب می‌دهد",
        "repo": "jpillora/chisel",
        "binaries": [
          "chisel"
        ],
        "config": "args",
        "transports": [
          "http",
          "https"
        ],
        "default_transport": "http",
        "recommended": true
      }
    ]
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
    // شکلِ tenant_portal_list؛ بی‌hasPass همه «رمز ندارد» دیده می‌شدند
    ready: true, groupsError: null,
    groups: ["goroh-a", "goroh-b", "goroh-c"],
    tenants: mk(4, function (i) {
      return { id: i + 2, name: ["حسین", "مهدی", "سارا", "امیر"][i],
               portalSlug: ["hossein", "mehdi", "sara", "amir"][i],
               portalGroup: i === 3 ? "" : ["goroh-a", "goroh-b", "goroh-c"][i],
               portalEnabled: i !== 2,
               hasPass: i !== 3, active: true, logo: "",
               credit: [1200000, 4500000, -1, 0][i] };
    }),
  };


  var INBOUNDS = {
    // شکلِ bot_inbounds در بکند؛ `clients` اختراعِ هارنس بود و `tenant` نبود
    ready: true, mode: "all", selected: [7, 9], default: 7, tenant: null,
    inbounds: mk(5, function (i) {
      return { id: 5 + i * 2, remark: ["Reality-443", "VLESS-2053", "VMess-8443",
                                       "Trojan-2083", "Shadowsocks-8080"][i],
               protocol: ["vless", "vless", "vmess", "trojan", "ss"][i],
               port: [443, 2053, 8443, 2083, 8080][i],
               enable: i !== 3 };
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
   "provision_failed": {
    "label": "ساختِ کانفیگ ناموفق",
    "level": "error",
    "alert": true
   },
   "deliver_failed": {
    "label": "کانفیگ ساخته شد ولی به مشتری نرسید",
    "level": "error",
    "alert": true
   },
   "order_deliver_failed": {
    "label": "تحویلِ سفارشِ تاییدشده ناموفق",
    "level": "error",
    "alert": true
   },
   "renew_failed": {
    "label": "تمدید خودکار ناموفق",
    "level": "error",
    "alert": true
   },
   "usage_failed": {
    "label": "خواندنِ مصرف از پنل ناموفق",
    "level": "error",
    "alert": false
   },
   "reminder_failed": {
    "label": "ارسالِ یادآوریِ انقضا ناموفق",
    "level": "error",
    "alert": false
   },
   "traffic_warn_failed": {
    "label": "ارسالِ هشدارِ حجم ناموفق",
    "level": "error",
    "alert": false
   },
   "channel_failed": {
    "label": "ارسالِ پستِ کانال ناموفق",
    "level": "error",
    "alert": false
   },
   "winback_failed": {
    "label": "پیگیریِ تست ناموفق",
    "level": "error",
    "alert": false
   },
   "report_failed": {
    "label": "گزارشِ روزانه ناموفق",
    "level": "error",
    "alert": false
   },
   "token_invalid": {
    "label": "توکنِ ربات نامعتبر شد — ربات غیرفعال شد",
    "level": "error",
    "alert": false
   },
   "scheduler_failed": {
    "label": "خطا در زمان‌بند",
    "level": "error",
    "alert": false
   },
   "provision": {
    "label": "کانفیگ ساخته شد",
    "level": "ok",
    "alert": false
   },
   "signup": {
    "label": "کاربر تازه",
    "level": "info",
    "alert": false
   },
   "owner_linked": {
    "label": "صاحبِ فروشگاه به ربات وصل شد",
    "level": "info",
    "alert": false
   }
  };

var EVENTS = [
  { id: 214, kind: "provision_failed", level: "error",
    text: "ساختِ کانفیگ ناموفق — سفارش #1842 · خطای پنل: 3x-ui پاسخ نداد (timeout بعد از ۳۰ ثانیه)",
    at: "2026-09-23 14:22:00", userId: 88, name: "مریم کاظمی", username: "maryamk", tgId: 184923771 },
  { id: 213, kind: "signup", level: "info", text: "کاربر تازه",
    at: "2026-09-23 14:19:00", userId: 141, name: "امیرحسین", username: "", tgId: 622019384 },
  { id: 212, kind: "provision", level: "ok",
    text: "کانفیگ ساخته شد — سفارش #1841 · اشتراک #903",
    at: "2026-09-23 13:58:00", userId: 77, name: "سعید رحمانی", username: "saeedr", tgId: 99201773 },
  { id: 211, kind: "renew_failed", level: "error",
    text: "تمدید خودکار ناموفق — اشتراک #812 · موجودی کیف پول کافی نبود و کسر برگشت خورد",
    at: "2026-09-23 12:04:00", userId: 52, name: "نگار", username: "", tgId: 510228841 },
  { id: 210, kind: "channel_failed", level: "error",
    text: "ارسالِ پستِ کانال ناموفق — پست #37 · ربات در کانال ادمین نیست",
    at: "2026-09-23 11:40:00", userId: null, name: "", username: "", tgId: null },
  { id: 209, kind: "deliver_failed", level: "error",
    text: "کانفیگ ساخته شد ولی به مشتری نرسید — سفارش #1836 · Forbidden: bot was blocked by the user",
    at: "2026-09-22 22:15:00", userId: 61, name: "حسین نجی", username: "hnaji", tgId: 771993022 },
  { id: 208, kind: "usage_failed", level: "error",
    text: "خواندنِ مصرف از پنل ناموفق · نام کاربری یا رمز پنل پذیرفته نشد",
    at: "2026-09-22 20:00:00", userId: null, name: "", username: "", tgId: null },
  { id: 207, kind: "provision", level: "ok",
    text: "کانفیگ ساخته شد — سفارش #1835 · اشتراک #901",
    at: "2026-09-22 19:31:00", userId: 34, name: "زهرا م.", username: "zahra_m", tgId: 402118837 },
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
        planId: null, planName: null, expiresAt: "2026-04-04",
        active: true, paidOrders: 37, givenToman: 1110000 },
      { id: 2, code: "WELCOME10", percent: 10, maxUses: 0, usedCount: 212,
        planId: null, planName: null, expiresAt: null,
        active: true, paidOrders: 212, givenToman: 2544000 },
      { id: 3, code: "TRIAL-A7K2", percent: 30, maxUses: 1, usedCount: 1,
        planId: 1, planName: "یک‌ماهه", expiresAt: "2025-09-24",
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
  /* رسیدِ بانکیِ ساختگی — برای کارتِ سفارش (FAKE_SHOT اسکرین‌شاتِ خطاست) */
  var FAKE_RECEIPT = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzMDAgNDIwIj48cmVjdCB3aWR0aD0iMzAwIiBoZWlnaHQ9IjQyMCIgZmlsbD0iI0Y4RkFGQyIvPjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iNjQiIGZpbGw9IiMwRTc0OTAiLz48dGV4dCB4PSIxNTAiIHk9IjQwIiBmb250LXNpemU9IjE4IiBmb250LWZhbWlseT0iVGFob21hLHNhbnMtc2VyaWYiIGZpbGw9IiNmZmYiIHRleHQtYW5jaG9yPSJtaWRkbGUiPtix2LPbjNivINin2YbYqtmC2KfZhCDZiNis2Yc8L3RleHQ+PGNpcmNsZSBjeD0iMTUwIiBjeT0iMTE4IiByPSIyNiIgZmlsbD0iIzEwQjk4MSIvPjxwYXRoIGQ9Ik0xMzcgMTE4bDkgOSAxNy0xOCIgc3Ryb2tlPSIjZmZmIiBzdHJva2Utd2lkdGg9IjUiIGZpbGw9Im5vbmUiLz48dGV4dCB4PSIxNTAiIHk9IjE3OCIgZm9udC1zaXplPSIxNSIgZm9udC1mYW1pbHk9IlRhaG9tYSxzYW5zLXNlcmlmIiBmaWxsPSIjMEYxNzJBIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj7Yp9mG2KrZgtin2YQg2YXZiNmB2YI8L3RleHQ+PHRleHQgeD0iMTUwIiB5PSIyMTgiIGZvbnQtc2l6ZT0iMjIiIGZvbnQtd2VpZ2h0PSI3MDAiIGZvbnQtZmFtaWx5PSJUYWhvbWEsc2Fucy1zZXJpZiIgZmlsbD0iIzBGMTcyQSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+27LbuNuw2azbsNuw27Ag2KrZiNmF2KfZhjwvdGV4dD48ZyBmb250LXNpemU9IjEzIiBmb250LWZhbWlseT0iVGFob21hLHNhbnMtc2VyaWYiIGZpbGw9IiM0NzU1NjkiPjx0ZXh0IHg9IjI3MCIgeT0iMjcwIiB0ZXh0LWFuY2hvcj0iZW5kIj7YqNmHINqp2KfYsdiqOiDbttuw27PbtyAqKioqICoqKiog27Tbtdux27I8L3RleHQ+PHRleHQgeD0iMjcwIiB5PSIzMDAiIHRleHQtYW5jaG9yPSJlbmQiPti02YXYp9ix2Ycg2b7bjNqv24zYsduMOiDbtNu427Lbudux27c8L3RleHQ+PHRleHQgeD0iMjcwIiB5PSIzMzAiIHRleHQtYW5jaG9yPSJlbmQiPtux27TbsNu1L9uw27cv27DbsyDigJQg27HbtDrbsNuyPC90ZXh0PjwvZz48L3N2Zz4=";
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
    // رسیدِ پنلِ مدیر پایین‌تر است؛ این فقط مالِ مینی‌اپ
    if (u.indexOf("/receipt") >= 0 && u.indexOf("/admin/bot/receipt/") < 0) return miniReceipt(u, body);
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
      P_THEME.until = "2026-11-12T12:00:00";   // همان ISOِ میلادیِ بکند
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
    /* فایروال — هر زیرمسیر شکلِ خودش را دارد؛ پیش‌تر `indexOf("/firewall")`
       همه را می‌گرفت و «پیشنهاد»، «بسته‌شده‌ها» و «بازگشتِ خودکار» همان
       فهرستِ قواعد را می‌دیدند */
    if (u.indexOf("/firewall/intrusion") >= 0) return INTRUSION;
    if (u.indexOf("/firewall/blocked") >= 0) return FW_BLOCKED;
    if (u.indexOf("/firewall/suggest") >= 0) return FW_SUGGEST;
    if (u.indexOf("/firewall/preflight") >= 0) return FW_PREFLIGHT;
    if (u.indexOf("/firewall/rollback-state") >= 0) return FW_ROLLBACK;
    if (u.indexOf("/firewall/blackhole/verify") >= 0) {
      var vip = decodeURIComponent((/[?&]ip=([^&]*)/.exec(u) || [])[1] || "");
      var isb = FW_BLOCKED.blocked.some(function (b) { return b.ip === vip; });
      return { ip: vip, blocked: isb, why: isb ? "کرنل تأیید می‌کند: مسیر این آدرس سیاه‌چاله است"
                                              : "کرنل مسیر عادی برایش دارد — بسته نیست" };
    }
    if (u.indexOf("/firewall/blackhole/bulk") >= 0) {
      var ips = String((body || {}).ips || "").split(/[\n,]/).map(function (x) { return x.trim(); })
        .filter(function (x) { return x && x.charAt(0) !== "#"; });
      var un = !!(body || {}).unblock;
      ips.forEach(function (ip) {
        FW_BLOCKED.blocked = FW_BLOCKED.blocked.filter(function (b) { return b.ip !== ip; });
        if (!un) FW_BLOCKED.blocked.unshift({ ip: ip, via: "blackhole", active: true, how: "مسیر سیاه‌چاله‌ی کرنل — بدون فایروال کار می‌کند" });
      });
      return { ok: true, total: ips.length, done: ips.length, failed: 0,
               results: ips.map(function (ip) { return { ip: ip, ok: true, note: un ? "باز شد" : "بسته شد" }; }),
               note: ips.length + " از " + ips.length + " آدرس " + (un ? "باز شد" : "بسته شد") };
    }
    if (u.indexOf("/firewall/blackhole") >= 0 && method === "POST") {
      var bip = String((body || {}).ip || "").trim();
      FW_BLOCKED.blocked = FW_BLOCKED.blocked.filter(function (b) { return b.ip !== bip; });
      if (!(body || {}).unblock) FW_BLOCKED.blocked.unshift({ ip: bip, via: "blackhole", active: true, how: "مسیر سیاه‌چاله‌ی کرنل — بدون فایروال کار می‌کند" });
      return { ok: true, note: (body || {}).unblock ? bip + " باز شد" : bip + " بسته شد" };
    }
    if (u.indexOf("/firewall/block-attackers") >= 0) {
      var bl = ((body || {}).ips || []).map(function (ip) { return { ip: ip, note: "بسته شد" }; });
      return { ok: true, note: bl.length + " آی‌پی بسته شد", blocked: bl, skipped: [], failed: [] };
    }
    if (u.indexOf("/firewall") >= 0 && method !== "GET") {
      return Object.assign({ ok: true, note: "انجام شد", results: [] }, FIREWALL);
    }
    if (u.indexOf("/firewall") >= 0) return FIREWALL;
    /* زیرمسیرهای تانل — پیش‌تر یک `indexOf("/tunnel")` همه را می‌گرفت و
       کلِ overview را برمی‌گرداند؛ پس نمودارِ سنجش، کانفیگ، تشخیص و
       مانیتورینگِ نود در هارنس هیچ‌وقت داده‌ی خودشان را نداشتند. شکل‌ها
       عیناً از بکند (test-contract با شناسه‌ی واقعیِ فیکسچر می‌سنجد). */
    if (u.indexOf("/tunnel/node/") >= 0) {
      var nm = u.match(/\/tunnel\/node\/(\d+)/), nid = nm ? +nm[1] : 0;
      var nd = TUNNEL.nodes.filter(function (n) { return n.id === nid; })[0] || TUNNEL.nodes[0];
      if (u.indexOf("/sysmon") >= 0) {
        if (method === "POST") return { ok: true, jobId: 91, note: "درخواست ثبت شد — نتیجه تا چند ثانیه‌ی دیگر می‌رسد" };
        // نودِ ۲ هنوز گزارشی نفرستاده، نودِ ۳ ایجنتِ قدیمی دارد — هر سه حالت دیده شوند
        if (nid === 1) return { ready: true, at: SYSMON1.at, kind: "sysmon", data: SYSMON1, staleAgent: null, lastError: null };
        if (nid === 3) return { ready: false, note: "ایجنت این سرور نسخه‌ی 1.4.0 است و دستور مانیتورینگ را نمی‌شناسد — باید به‌روز شود",
                                staleAgent: "1.4.0", lastError: null };
        return { ready: false, note: "هنوز گزارشی از این سرور نرسیده است", staleAgent: null, lastError: null };
      }
      if (u.indexOf("/check") >= 0) {
        return { ok: nd.online, node: nd.name, online: nd.online, neverSeen: false,
                 steps: [
                   { title: "نود در پنل ثبت است", ok: true, detail: nd.name, hint: "" },
                   { title: "آخرین تماس", ok: true, detail: nd.last_seen, hint: "" },
                   { title: "زنده است", ok: nd.online, detail: nd.online ? "کمتر از ۹۰ ثانیه پیش" : "بیش از یک روز پیش",
                     hint: nd.online ? "" : "روی سرور: systemctl status nexora-agent" },
                   { title: "دستور نصب", ok: true, detail: "از دکمه‌ی «توکن جدید» دوباره بگیرید اگر لازم شد", hint: "" } ],
                 commands: [
                   { label: "وضعیت agent", cmd: "systemctl status nexora-agent" },
                   { label: "لاگ زنده", cmd: "journalctl -u nexora-agent -n 40 --no-pager" },
                   { label: "تست دسترسی به پنل", cmd: "curl -sI https://YOUR-PANEL/api/health" },
                   { label: "ری‌استارت", cmd: "systemctl restart nexora-agent" } ] };
      }
      if (u.indexOf("/diagnose") >= 0) {
        var fresh = nid === 1;
        return { node: { id: nd.id, name: nd.name, host: nd.public_ip, version: nd.agent_version,
                         lastSeen: nd.last_seen, ageSeconds: nd.online ? 12 : 58000 },
                 steps: [
                   { step: "چک‌این ایجنت", ok: nd.online, note: nd.online ? "12 ثانیه پیش" : "بیش از ۱۶ ساعت پیش" },
                   { step: "نسخه‌ی ایجنت", ok: fresh, note: fresh ? "نسخه‌ی " + nd.agent_version : "نسخه‌ی 1.4.0 دستور مانیتورینگ را نمی‌شناسد",
                     fix: fresh ? undefined : "دکمه‌ی «به‌روزرسانی ایجنت» را بزنید" },
                   { step: "درخواست مانیتورینگ", ok: fresh, note: fresh ? "آخرین درخواست ۲ دقیقه پیش انجام شد" : "هیچ درخواستی برای این نود ثبت نشده" },
                   { step: "گزارش ذخیره‌شده", ok: fresh, note: fresh ? "گزارش ۲ دقیقه پیش" : "هیچ گزارشی ذخیره نشده" } ],
                 healthy: fresh,
                 jobs: [{ id: 97, action: "sysmon", status: fresh ? "done" : "queued", created_at: "2026-09-24 20:29:40",
                          taken_at: fresh ? "2026-09-24 20:29:52" : null, done_at: fresh ? "2026-09-24 20:29:55" : null,
                          result: fresh ? "ok" : null }] };
      }
      if (u.indexOf("/update-agent") >= 0) return { ok: true, queued: true };
      if (u.indexOf("/rotate") >= 0) return { ok: true, token: "nxa_Zr8…" };
      return { ok: true };
    }
    var tm = u.match(/\/tunnel\/(\d+)\/(metrics|config|monitor|deploy|action|jobs)/);
    if (tm) {
      /* کارهای تانل — دستورِ «لاگ»/«وضعیت» یک کار می‌سازد که با پرسشِ
         دوم «انجام شد» می‌شود، تا در هارنس هم انتظار و هم نتیجه دیده شوند */
      if (tm[2] === "jobs") {
        TJOBS.forEach(function (j) { if (j.status === "queued") { j.status = "taken"; } else if (j.status === "taken") { j.status = "done"; j.done_at = "2026-09-24 20:33:10"; } });
        return { jobs: TJOBS.filter(function (j) { return j.tunnel === +tm[1]; }).slice().reverse()
          .map(function (j) { return { id: j.id, node_id: 1, action: j.action, status: j.status,
                                       result: j.status === "done" ? j.result : null,
                                       created_at: j.created_at, done_at: j.done_at || null }; }) };
      }
      if (tm[2] === "action" && method === "POST") {
        var what = u.split("/action/")[1];
        TJOBS.push({ id: TJOBS.length + 100, tunnel: +tm[1], action: what, status: "queued",
                     created_at: "2026-09-24 20:32:40",
                     result: what === "status"
                       ? JSON.stringify({ running: +tm[1] === 1, state: +tm[1] === 1 ? "active" : "failed",
                                          sub: +tm[1] === 1 ? "running" : "failed", restarts: +tm[1] === 1 ? "0" : "7",
                                          since: "Wed 2026-09-24 08:12:03 UTC" })
                       : "2026-09-24T20:31:02+0000 ir-thr-1 backhaul[4121]: [INFO] client connected to 198.51.100.20:3081\n"
                         + "2026-09-24T20:31:02+0000 ir-thr-1 backhaul[4121]: [INFO] tcpmux session established (8 streams)\n"
                         + "2026-09-24T20:32:11+0000 ir-thr-1 backhaul[4121]: [WARN] keepalive timeout, reconnecting\n"
                         + "2026-09-24T20:32:12+0000 ir-thr-1 backhaul[4121]: [INFO] client connected to 198.51.100.20:3081" });
        return { ok: true, queued: what };
      }
      if (tm[2] === "metrics") return +tm[1] === 1 ? TMETRICS : { samples: [], summary: null };
      if (tm[2] === "config") {
        return { config: "[client]\nremote_addr = \"198.51.100.20:3081\"\ntoken = \"••••••••\"\ntransport = \"tcpmux\"\n"
                         + "keepalive_period = 75\nnodelay = true\nlog_level = \"info\"\nmux_version = 1\n",
                 engine: "backhaul", side: "foreign", filename: "tunnel-" + tm[1] + ".toml" };
      }
      if (tm[2] === "monitor") return { ok: true, queued: true, ports: [443, 8443] };
      return { ok: true, queued: true };
    }
    if (u.indexOf("/tunnel/overview") >= 0 || u.indexOf("/tunnel") >= 0) return TUNNEL;
    if (u.indexOf("/admin/health/all") >= 0) return HEALTH_ALL;
    if (u.indexOf("/admin/health/check") >= 0) return { ok: true, queued: true };
    if (u.indexOf("/admin/usage-history") >= 0) return USAGE;
    if (u.indexOf("/admin/top-clients") >= 0) return TOPCLIENTS;
    if (u.indexOf("/affiliates") >= 0) return AFFILIATES;
    if (u.indexOf("/admin/monitor") >= 0) {
      /* مثلِ بکند: `sections=` فقط همان بخش‌ها را برمی‌گرداند. بی‌این، بخشِ
         «بسته‌ها و امنیت» (که فقط با درخواست پر می‌شود) در هارنس همیشه خالی
         و سنجه‌هایش هم‌زمان در شبکه‌ی بالا پُر بودند — حالتی که روی سرور نیست */
      var sm = /[?&]sections=([^&]*)/.exec(u);
      if (!sm || !sm[1]) return MONITOR;
      var want = decodeURIComponent(sm[1]).split(",");
      var secs = {}, keys = {};
      want.forEach(function (k) {
        if (MONITOR.sections[k] === undefined) return;
        secs[k] = MONITOR.sections[k];
        (Array.isArray(secs[k]) ? secs[k] : []).forEach(function (m) { if (m && m.key) keys[m.key] = 1; });
      });
      var mets = MONITOR.metrics.filter(function (m) {
        return keys[m.key] || (m.key.indexOf("conn:") === 0 && want.indexOf("connections") >= 0)
          || (m.key.indexOf("svc:") === 0 && want.indexOf("services") >= 0);
      });
      return Object.assign({}, MONITOR, { sections: secs, metrics: mets });
    }
    if (u.indexOf("/admin/themes") >= 0) {
      if (method === "POST") {
        THEMES.currentTemplate = (body || {}).template || THEMES.currentTemplate;
        THEMES.currentPalette = (body || {}).palette || THEMES.currentPalette;
        return { ok: true, template: THEMES.currentTemplate,
                 palette: THEMES.currentPalette };
      }
      return THEMES;
    }
    /* صفحه‌ی «به‌روزرسانی» — تا این‌جا هیچ‌کدام ساختگی نبودند و همه
       {ready:true} می‌گرفتند، پس آن صفحه در هارنس همیشه خالی بود. شکل‌ها
       عیناً از بکند (test-contract می‌سنجد)؛ حالتِ «تنظیم‌شده، نسخه‌ی
       تازه هست» تا شاخه‌ی اصلیِ صفحه دیده شود. */
    if (u.indexOf("/admin/system") >= 0) {
      return { build: { built: true, stale: false, builtAt: "2026-09-24T18:42:10", note: null },
               version: "1.93.0",
               template: { path: "/opt/nexora-panel/sub-page-index.html", exists: true, size: 381204,
                           apiUrl: "https://panel.example.com" },
               counts: { apps: 6, faq: 3, videos: 2, resellers: 3 },
               configPath: "/opt/nexora-panel/data/config.json", configExists: true };
    }
    if (u.indexOf("/admin/check-update") >= 0) {
      return { currentVersion: "1.93.0", latestVersion: "1.94.0", updateAvailable: true, configured: true,
               releaseNotes: "### Fixed\n- ظاهرِ فروشگاه از اولین فریم\n- سقفِ زمانیِ درخواست‌های مینی‌اپ",
               publishedAt: "2026-09-24T12:00:00Z", repo: "nexora-technology-v/nexora-subscription-manager" };
    }
    if (u.indexOf("/admin/snapshots") >= 0) {
      return { snapshots: [
        { id: "snap-1.92.0", version: "1.92.0", createdAt: "2026-09-24T13:57:20", sizeMb: 18.4, hasSettings: true, hasBot: true },
        { id: "snap-1.91.0", version: "1.91.0", createdAt: "2026-09-23T18:16:42", sizeMb: 17.9, hasSettings: true, hasBot: true },
      ] };
    }
    if (u.indexOf("/admin/update-log") >= 0) {
      return { exists: true, lines: ["[18:42:01] دریافتِ نسخه‌ی 1.93.0", "[18:42:09] ساختِ پنل", "[18:42:31] راه‌اندازیِ دوباره — تمام"] };
    }
    if (u.indexOf("/admin/github") >= 0) {
      return { repo: "nexora-technology-v/nexora-subscription-manager", configured: true };
    }
    if (u.indexOf("/admin/maintenance") >= 0) {
      return { enabled: true, action: "xray", hour: 5, minute: 0, days: [5], skipIfBusy: true, busyThreshold: 20,
               confirmedReboot: false, lastRun: "2026-09-19T05:00:04", lastResult: "انجام شد — Xray ری‌استارت شد",
               nextRun: "2026-09-26T05:00:00", activeConnections: 37 };
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
    // بکند با ?status= فیلتر می‌کند؛ بدونِ این، زبانه‌ی «در انتظار» سفارشِ
    // تاییدشده و ردشده هم نشان می‌داد و شبیهِ باگِ پنل بود
    if (u.indexOf("/bot/receipt/") >= 0) {
      // تصویرِ رسید — رابط حالا با fetch و blob می‌گیردش (رمز در آدرس نیست)
      return { __blob: FAKE_RECEIPT };
    }
    if (u.indexOf("/bot/orders") >= 0) {
      var st = (/[?&]status=([a-z_]+)/.exec(u) || [])[1] || "awaiting";
      var rows = st === "all" ? ORDERS.orders : ORDERS.orders.filter(function (o) {
        return o.status === st || (st === "awaiting" && o.status === "review"); });
      return { orders: rows, dbReady: true };
    }
    if (u.indexOf("/bot/plans") >= 0) return PLANS;
    /* کاربران — فیلتر، جستجو و صفحه مثلِ `_users_page` بکند؛ بدونِ این هر
       فیلتر همان فهرست را نشان می‌داد و شبیهِ باگِ پنل بود */
    if (u.indexOf("/bot/users") >= 0) {
      var uq = decodeURIComponent((/[?&]q=([^&]*)/.exec(u) || [])[1] || "").trim();
      var uf = (/[?&]filter=([a-zA-Z]+)/.exec(u) || [])[1] || "all";
      var uo = +((/[?&]offset=(\d+)/.exec(u) || [])[1] || 0);
      var ul = +((/[?&]limit=(\d+)/.exec(u) || [])[1] || 50);
      var F = {
        all: function () { return true; },
        active: function (x) { return x.activeSubs > 0; },
        expired: function (x) { return x.subsCount > 0 && !x.activeSubs; },
        never: function (x) { return !x.ordersCount; },
        buyers: function (x) { return x.ordersCount > 0; },
        withPhone: function (x) { return !!x.phone; },
        noPhone: function (x) { return !x.phone; },
        withBalance: function (x) { return x.balance > 0; },
        withCoins: function (x) { return x.coins > 0; },
        referred: function (x) { return !!x.referred_by; },
        blocked: function (x) { return !!x.is_blocked; },
      };
      var ur = USERS.users.filter(F[uf] || F.all).filter(function (x) {
        return !uq || [x.first_name, x.username, x.phone, String(x.tg_id)].join(" ").indexOf(uq) >= 0;
      });
      return Object.assign({}, USERS, { users: ur.slice(uo, uo + ul), total: ur.length });
    }
    // همان شکلِ `_funnel` — شکلِ کهنه‌ی {seen, bought} صفحه‌ی «آمار و قیف»
    // را با «NaN٪» و قیفِ خالی نشان می‌داد و هیچ‌کس نمی‌فهمید هارنس است
    if (u.indexOf("/bot/funnel") >= 0) {
      return { ready: true, started: 640, steps: [
        { label: "ربات را باز کردند", n: 640, pct: 100 },
        { label: "شماره ثبت کردند", n: 402, pct: 62.8 },
        { label: "سفارش ثبت کردند", n: 188, pct: 29.4 },
        { label: "خرید موفق", n: 131, pct: 20.5 }],
        segments: { paid: 131, trialOnly: 96, trial: 210, idle: 413 } };
    }
    if (u.indexOf("/bot/status") >= 0) return BOT_STATUS;
    if (u.indexOf("/bot/settings") >= 0) {
      if (method !== "GET") return { ok: true };
      return BOT_SETTINGS;
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
    var resp = {
      ok: status < 400, status: status,
      headers: { get: function (k) { return HDR[String(k).toLowerCase()] || null; } },
      json: function () { return Promise.resolve(data); },
      blob: function () {
        var src = (data && data.__blob) || "";
        var m = /^data:([^;]+);base64,(.*)$/.exec(src);
        if (!m) return Promise.resolve(new Blob([JSON.stringify(data)], { type: "application/json" }));
        var bin = atob(m[2]), arr = new Uint8Array(bin.length);
        for (var i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
        return Promise.resolve(new Blob([arr], { type: m[1] }));
      },
      text: function () { return Promise.resolve(""); },
    };
    /* ?lat=2500 — تأخیرِ شبکه، به میلی‌ثانیه.
       پاسخِ فوری هر مشکلی را پنهان می‌کند که فقط وقتی دیده می‌شود که
       سرور دیر جواب بدهد: مینی‌اپ با رنگِ پیش‌فرض بالا می‌آمد و بعد به
       پوسته‌ی فروشگاه می‌پرید، و در هارنس هیچ‌وقت دیده نمی‌شد. */
    var lat = parseInt(Q0.get("lat") || "0", 10) || 0;
    return lat > 0
      ? new Promise(function (res) { setTimeout(function () { res(resp); }, lat); })
      : Promise.resolve(resp);
  };
})();
