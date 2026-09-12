/**
 * کمکی‌های نمایش: رقم فارسی، حجم، تاریخ.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
export const fmtBytes = (n) => {
  const b = Number(n || 0);
  if (b <= 0) return "۰";
  const gb = b / 1073741824;
  if (gb >= 1) return `${gb.toFixed(1)} GB`;
  return `${(b / 1048576).toFixed(0)} MB`;
};

export const fmtDate = (ms) => {
  if (!ms) return "بدون انقضا";
  try {
    return new Date(Number(ms)).toLocaleDateString("fa-IR");
  } catch { return "—"; }
};

export const daysLeft = (ms) => {
  if (!ms) return null;
  const d = Math.ceil((Number(ms) - Date.now()) / 86400000);
  return d;
};

// faNum یک عدد می‌خواهد؛ برای رشته‌هایی مثل «13:45:22» یا نسخه‌ی
// کرنل باید رقم‌به‌رقم تبدیل کرد، وگرنه NaN می‌شود.
export const toFaDigits = (s) =>
  String(s ?? "").replace(/[0-9]/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[d]);

export function fmtUptime(s) {
  if (!s) return "—";
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600);
  if (d) return `${faNum(d)} روز و ${faNum(h)} ساعت`;
  const m = Math.floor((s % 3600) / 60);
  return h ? `${faNum(h)} ساعت و ${faNum(m)} دقیقه` : `${faNum(m)} دقیقه`;
}

export function fmtSize(n) {
  if (n === null || n === undefined) return "—";
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0, v = Number(n);
  while (Math.abs(v) >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return `${faNum(v.toFixed(i ? 1 : 0))} ${u[i]}`;
}

/** نام کاربر ممکن است HTML داشته باشد — React خودش امن می‌کند، این فقط تمیزکاری است. */
export const esc0 = (s) => (s == null ? "" : String(s));

export const faNum = (n) => Number(n || 0).toLocaleString("fa-IR");
