import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";
import { isMini, portalSlug } from "./lib/route.js";
import { Splash } from "./lib/mark.jsx";
import "./index.css";

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
  admin: () => import("./App.jsx"),
};

const WHICH = isMini() ? "mini" : portalSlug() ? "portal" : "admin";

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
                     admin: "پنل مدیریت" }[WHICH];

function Booting() {
  return <Splash label={BOOT_LABEL} />;
}

/**
 * صفحه‌ی ورود یک کفِ زمانی دارد.
 *
 * روی اتصال خوب، تکه‌ی اپ در حدود صدم‌ثانیه می‌رسد و نشان فقط یک بار
 * می‌پرد و می‌رود — که از نبودنش بدتر است. این کف باعث می‌شود حرکتِ
 * خودِ نشان (حلقه ۰٫۷۸ ثانیه، بعد نام) تا آخر دیده شود.
 *
 * کف است نه تأخیر: تکه از قبل دارد دانلود می‌شود، پس اگر دیرتر
 * برسد هیچ چیزی به زمانِ انتظار اضافه نشده.
 *
 * و اگر کاربر حرکت را خاموش کرده، کف هم برداشته می‌شود: کسی که
 * `prefers-reduced-motion` گذاشته، انیمیشنی نمی‌بیند که منتظرش
 * بماند.
 */
const SPLASH_MS = 1900;

function Gate({ children }) {
  const skip = typeof window !== "undefined"
    && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const [ready, setReady] = React.useState(!!skip);
  React.useEffect(() => {
    if (skip) return undefined;
    const t = setTimeout(() => setReady(true), SPLASH_MS);
    return () => clearTimeout(t);
  }, [skip]);
  return ready ? children : <Booting />;
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Suspense fallback={<Booting />}>
      <Gate><Root /></Gate>
    </Suspense>
  </React.StrictMode>
);
