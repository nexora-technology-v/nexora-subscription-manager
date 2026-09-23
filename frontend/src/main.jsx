import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";
import { isAff, isMini, portalSlug } from "./lib/route.js";
import { Splash } from "./lib/mark.jsx";
import "./index.css";
import { applyTheme, markScheme } from "./lib/mini-themes.js";

// آدرس تعیین می‌کند کدام اپ بالا بیاید.
//
// /r/<نشانی> پنل نماینده است و /app مینی‌اپ مشتری. هیچ‌کدام ربطی به
// پنل مدیر ندارند — نه کدشان، نه مسیرهایشان. این شرط تنها جایی است
// که این سه به هم می‌رسند، و عمداً همین‌قدر کوچک نگه داشته شده.
//
// و با lazy بارگذاری می‌شوند، نه با import مستقیم: وگرنه هر سه در
// یک فایل می‌نشینند و مشتریِ مینی‌اپ کلِ پنل مدیر را هم دانلود
// می‌کند. شرط از `lib/route.js` می‌آید که هیچ وابستگی‌ای ندارد، پس
// خودِ تصمیم چیزی را بار نمی‌کند.
const PICK = {
  mini: () => import("./mini/index.jsx"),
  portal: () => import("./portal/index.jsx"),
  aff: () => import("./aff/index.jsx"),
  admin: () => import("./App.jsx"),
};

const WHICH = isMini() ? "mini" : isAff() ? "aff"
  : portalSlug() ? "portal" : "admin";

// دانلود **همین حالا** شروع می‌شود، نه موقع رندر.
//
// `lazy()` تا اولین رندر چیزی را نمی‌آورد. با کفِ زمانیِ پایین، آن
// یعنی اول ۱٫۹ ثانیه صبر و *بعد* شروعِ دانلود — دو کار پشت سر هم به
// جای هم‌زمان. این‌طور هر دو با هم می‌دوند و کف واقعاً فقط کف است.
const CHUNK = PICK[WHICH]();
const Root = lazy(() => CHUNK);

// تا رسیدنِ تکه، صفحه نباید سفید بماند.
//
// `Splash` از `lib/mark.jsx` می‌آید که مثل `lib/route.js` هیچ
// وابستگی‌ای ندارد — اگر از کتابخانه‌ی UI می‌آمد، همه‌ی آیکون‌هایش
// هم داخل تکه‌ی ورودی می‌نشستند و lazy بی‌معنی می‌شد.
const BOOT_LABEL = { mini: "اشتراک من", portal: "پنل نمایندگی",
                     aff: "پنل همکار فروش", admin: "پنل مدیریت" }[WHICH];

/*
 * برندِ فروشگاه، از کشِ دفعه‌ی قبل.
 *
 * موقعِ اسپلش هنوز `/api/mini/me` نیامده، پس نمی‌دانیم مشتریِ کدام
 * فروشگاه است. دفعه‌ی قبل می‌دانستیم و نگهش داشتیم.
 *
 * و اگر هیچ‌وقت ندانستیم، نشانِ **خودمان** را نشان نمی‌دهیم —
 * مشتریِ نماینده نباید بفهمد پشتِ فروشگاه نکسوراست. یک نشانِ خنثی
 * می‌آید تا وقتی برند برسد.
 *
 * `localStorage` ممکن است در حالتِ ناشناس یا با کوکیِ بسته اصلاً
 * کار نکند، پس هر خواندنی داخلِ try است و نبودنش فقط یعنی اسپلشِ
 * خنثی.
 */
const SHOP_KEY = "nx_shop";

function cachedShop() {
  if (WHICH !== "mini") return null;
  // پیش‌نمایشِ پرتال فروشگاهِ نمونه است؛ کشِ مرورگرِ نماینده را نخواند
  try { if (new URLSearchParams(window.location.search).get("preview") === "1") return null; }
  catch { /* */ }
  try {
    const raw = window.localStorage.getItem(SHOP_KEY);
    const v = raw ? JSON.parse(raw) : null;
    return v && typeof v === "object" ? v : null;
  } catch { return null; }
}

const SHOP = cachedShop();

// پوسته‌ی فروشگاه (قالب + پالت) پیش از اولین رندر، تا صفحه‌ی ورود هم
// مالِ خودش باشد — قالبِ «پررنگ» اسپلشِ تمام‌رنگ دارد، «مینیمال» بی‌مدار.
// پوسته‌ی تلگرام این‌جا هنوز روی ریشه ننشسته، پس از خودِ SDK پرسیده
// می‌شود؛ مینی‌اپ بعداً با پوسته‌ی قطعی دوباره می‌سازدش.
const SHOP_THEME = SHOP
  ? (SHOP.theme || (SHOP.accent ? { palette: "custom", accent: SHOP.accent } : null))
  : null;
try {
  if (WHICH === "mini") {
    const scheme = markScheme(window.Telegram && window.Telegram.WebApp);
    if (SHOP_THEME) applyTheme(SHOP_THEME, scheme);
  }
} catch { /* رنگ تزئین است، نه شرطِ بالاآمدن */ }

// عنوانِ پنجره هم همین است — تلگرام آن را بالای مینی‌اپ نشان
// می‌دهد، و `index.html` یک عنوانِ مشترک برای هر چهار اپ دارد.
try {
  if (WHICH === "mini") {
    document.title = (SHOP && SHOP.brand) || "اشتراک من";
  }
} catch { /* عنوان تزئین است، نه شرطِ بالاآمدن */ }

/**
 * صفحه‌ی ورود، با وضعیتِ واقعی.
 *
 * `note` را از خودِ کار می‌گیرد، نه از یک تایمر: تا وقتی تکه نرسیده
 * «در حال بارگذاری» و اگر نرسید، «نیامد» با دکمه‌ی تلاش دوباره.
 * درصدِ ساختگی نشان نمی‌دهیم — دروغ است و کاربر هم می‌فهمد.
 */
function Booting({ phase, note, onRetry }) {
  return <Splash label={BOOT_LABEL} phase={phase} note={note}
    onRetry={onRetry}
    name={(SHOP && SHOP.brand) || ""}
    logo={(SHOP && SHOP.logo) || ""}
    logoStyle={SHOP_THEME && SHOP_THEME.logoStyle}
    neutral={WHICH === "mini"} />;
}

/**
 * از صفحه‌ی ورود به اپ — با یک خروجِ نرم.
 *
 * سه چیز باید هم‌زمان درست شوند:
 *
 *   ۱. تکه‌ی اپ برسد (کارِ واقعی)
 *   ۲. حرکتِ نشان تا آخر دیده شود (کفِ زمانی)
 *   ۳. قطعِ ناگهانی نباشد (خروجِ نرم)
 *
 * کف، *کف* است نه تأخیر: دانلود از پیش شروع شده و هم‌زمان می‌دود.
 * و اگر کاربر حرکت را خاموش کرده، هر دو برداشته می‌شوند — کسی که
 * `prefers-reduced-motion` گذاشته، انیمیشنی ندارد که منتظرش بماند.
 */
const SPLASH_MS = 1700;
const EXIT_MS = 380;

function Gate({ children }) {
  // پیش‌نمایشِ پرتال: هر بار که قاب بار می‌شود ۱٫۷ ثانیه صفحه‌ی ورودِ
  // بی‌نام نشان می‌داد، پیش از آنکه پوسته برسد. پخشش با دکمه است.
  const skip = typeof window !== "undefined"
    && (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
        || /[?&]preview=1\b/.test(window.location.search));

  const [phase, setPhase] = React.useState(skip ? "in" : "load");
  const [err, setErr] = React.useState("");

  // ۱. تکه واقعاً رسید؟
  React.useEffect(() => {
    let alive = true;
    CHUNK.then(() => { if (alive) setErr(""); })
         .catch(() => { if (alive) setErr("برنامه بارگذاری نشد."); });
    return () => { alive = false; };
  }, []);

  // ۲+۳. کف، بعد خروج
  React.useEffect(() => {
    if (skip || err) return undefined;
    const a = setTimeout(() => setPhase("done"), SPLASH_MS);
    const b = setTimeout(() => setPhase("in"), SPLASH_MS + EXIT_MS);
    return () => { clearTimeout(a); clearTimeout(b); };
  }, [skip, err]);

  if (err) {
    return <Booting phase="error" note={err}
      onRetry={() => window.location.reload()} />;
  }
  if (phase === "in") return children;
  return <Booting phase={phase} note="در حال آماده‌سازی…" />;
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Suspense fallback={<Booting />}>
      <Gate><Root /></Gate>
    </Suspense>
  </React.StrictMode>
);
