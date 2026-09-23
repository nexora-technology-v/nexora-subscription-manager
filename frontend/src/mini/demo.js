/**
 * داده‌ی نمونه برای پیش‌نمایشِ مینی‌اپ در پرتالِ نماینده.
 *
 * برگه: docs/specs/2026-09-23-mini-theme-studio.md
 *
 * پیش‌نمایش **خودِ مینی‌اپ** است در یک قاب — نه ماکتی که شبیهش باشد.
 * بیرون از تلگرام `initData` ندارد، پس هر درخواست این‌جا جواب می‌گیرد
 * و هیچ‌چیز به سرور نمی‌رود. کارهای نوشتنی (خرید، رسید، پیام) فقط یک
 * پیامِ «پیش‌نمایش است» می‌گیرند — وانمودِ موفقیت یعنی نماینده فکر کند
 * چیزی واقعاً انجام شد.
 *
 * داده واقع‌نماست، نه خالی: با آرایه‌ی خالی هر صفحه شاخه‌ی «هنوز چیزی
 * نیست» را می‌گیرد و قالب روی نیمی از اجزا هیچ‌وقت دیده نمی‌شود.
 */
const GB = 1024 * 1024 * 1024;

export function makeDemo() {
  return {
    brand: "", logo: "", theme: null,
    me: {
      name: "مشتریِ نمونه", balance: 240000, coins: 36, tgId: 1278109787,
      username: "sample_user", support: "", botUsername: "", trialUsed: false,
      logo: "", accent: "", avatar: "", phone: "", refCode: "NX7K2M", refCount: 3,
    },
    subs: { subs: [
      { id: 1, plan: "پلن یک‌ماهه", email: "shop_1278109787_1", gb: 50, usedGB: 32,
        usagePct: 64, totalBytes: 50 * GB, usedBytes: 32 * GB, remainBytes: 18 * GB,
        months: 1, isTrial: false, active: true, expiryJalali: "۱۴۰۵/۰۸/۱۲",
        daysLeft: 26, subUrl: "https://sub.example.com/s1" },
      { id: 2, plan: "پلن سه‌ماهه", email: "shop_1278109787_2", gb: 100, usedGB: 8,
        usagePct: 8, totalBytes: 100 * GB, usedBytes: 8 * GB, remainBytes: 92 * GB,
        months: 3, isTrial: false, active: true, expiryJalali: "۱۴۰۵/۱۰/۰۳",
        daysLeft: 78, subUrl: "https://sub.example.com/s2" },
    ] },
    plans: { plans: [
      { id: 1, name: "یک‌ماهه", desc: "مناسب شروع", gb: 50, days: 30, devices: 1, price: 120000, isTrial: false },
      { id: 2, name: "سه‌ماهه", desc: "پرفروش‌ترین", gb: 100, days: 90, devices: 2, price: 280000, isTrial: false },
      { id: 3, name: "شش‌ماهه", desc: "به‌صرفه‌ترین", gb: 200, days: 180, devices: 3, price: 480000, isTrial: false },
    ] },
    orders: { orders: [
      { id: 4098, status: "awaiting", amount: 280000, plan: "پلن سه‌ماهه",
        paidFrom: "card", createdAt: "۱۴۰۵/۰۷/۰۱", expiresAt: "", note: "" },
    ] },
    inbox: { unread: 1, messages: [
      { id: 1, from: "user", body: "سلام، کانفیگ روی آیفون وصل نمی‌شه", orderId: null,
        at: "2026-09-23 09:10", read: true },
      { id: 2, from: "system", body: "سفارش #4097 تایید شد و اشتراکتان فعال است.",
        orderId: 4097, at: "2026-09-23 09:11", read: true },
      { id: 3, from: "admin", body: "سلام 🙂 برنامه را یک‌بار ببندید و دوباره باز کنید.",
        orderId: null, at: "2026-09-23 09:14", read: false },
    ] },
    rewards: {
      enabled: true, coins: 36, percent: 10, cost: 20,
      next: { coins: 40, percent: 20, need: 4 }, maxPercent: 50,
      tiers: [{ coins: 20, percent: 10 }, { coins: 40, percent: 20 },
              { coins: 60, percent: 30 }, { coins: 80, percent: 40 }],
      perReferral: 10, welcomeBonus: 3, expireDays: 0,
      refCode: "NX7K2M", refCount: 3, botUsername: "", link: "",
    },
  };
}

/** پلن‌های واقعیِ نماینده (از پرتال) → شکلِ مینی‌اپ */
export function plansFromPortal(rows) {
  return (rows || []).filter((p) => p && p.name && (p.is_active ?? 1)).map((p, i) => ({
    id: p.id || i + 1, name: p.name, desc: p.description || "",
    gb: Number(p.gb) || 0, days: Number(p.days) || 0,
    devices: Number(p.ip_limit) || 0, price: Number(p.price) || 0,
    isTrial: !!p.is_trial,
  }));
}

const PREVIEW_ONLY = "این پیش‌نمایش است — در مینی‌اپِ واقعی انجام می‌شود";

/** جوابِ هر مسیر از داده‌ی نمونه. نوشتن‌ها خطای روشن می‌گیرند. */
export function demoApi(demo, path, opt = {}) {
  const p = String(path).split("?")[0];
  const write = (opt.method || "GET") !== "GET";
  const reply = (v) => Promise.resolve(JSON.parse(JSON.stringify(v)));
  if (p === "/api/mini/me") {
    return reply({ ...demo.me, brand: demo.brand, logo: demo.logo,
                   accent: demo.theme?.accent || "", theme: demo.theme });
  }
  if (p === "/api/mini/subs") return reply(demo.subs);
  if (p === "/api/mini/plans") return reply(demo.plans);
  if (p === "/api/mini/orders") return reply(demo.orders);
  if (p === "/api/mini/rewards") return reply(demo.rewards);
  if (p === "/api/mini/ping") return reply({ unread: demo.inbox.unread, openOrders: 1, subs: 2 });
  if (p === "/api/mini/inbox/read") return reply({ ok: true });
  if (p === "/api/mini/inbox" && !write) return reply(demo.inbox);
  return Promise.reject(new Error(PREVIEW_ONLY));
}
