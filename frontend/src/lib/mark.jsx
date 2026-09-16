/**
 * نشانِ نکسورا و صفحه‌ی ورود.
 *
 * چرا این‌جا و نه در `ui/index.jsx`: صفحه‌ی ورود را `main.jsx` نشان
 * می‌دهد، یعنی *قبل* از رسیدنِ تکه‌ی اپ. اگر از کتابخانه‌ی UI بیاید،
 * کلِ آن کتابخانه (با همه‌ی آیکون‌هایش) داخل تکه‌ی ورودی می‌نشیند و
 * همان کاری را می‌کند که lazy برای جلوگیری‌اش گذاشته شده.
 *
 * پس این ماژول عمداً هیچ وابستگی‌ای جز خودِ React ندارد — مثل
 * `lib/route.js`.
 */
import React from "react";

/* شناسه‌ی یکتا برای گرادیان‌ها: اگر دو نشان هم‌زمان رندر شوند و هر دو
   یک id داشته باشند، مرورگر اولی را به هر دو می‌دهد و دومی رنگِ
   اشتباه می‌گیرد. */
let _seq = 0;

export function NexoraMark({ size = 96, animate = false, className = "" }) {
  const uid = React.useMemo(() => "nx" + (++_seq), []);
  const gN = uid + "n";
  const gR = uid + "r";

  return (
    <svg viewBox="0 0 120 120" width={size} height={size}
      className={`nx-mark ${animate ? "go" : ""} ${className}`}
      role="img" aria-label="نکسورا">
      <defs>
        {/* آبیِ برند → فیروزه‌ای، همان زاویه‌ی نشانِ نوار کناری */}
        <linearGradient id={gN} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#8FC1EE" />
          <stop offset="58%" stopColor="#2B7FD6" />
          <stop offset="100%" stopColor="#2DD4BF" />
        </linearGradient>
        {/* حلقه نقره‌ای است، نه آبی — در لوگو همین تضاد است که
            حجم می‌سازد */}
        <linearGradient id={gR} x1="0" y1="0" x2="1" y2="0.6">
          <stop offset="0%" stopColor="#EEF3F9" />
          <stop offset="45%" stopColor="#93A4B8" />
          <stop offset="100%" stopColor="#5AA9E6" />
        </linearGradient>
      </defs>

      {/* حلقه دو نیمه است تا مثل خودِ لوگو از پشتِ N رد شود و
          جلویش دربیاید — همین تقاطع است که به نشان حجم می‌دهد.
          دو نقطه‌ی انتها روی بیضیِ چرخیده‌ی (rx 50، ry 17، ‎-22°)
          حساب شده‌اند؛ اگر یکی را دست بزنی، حلقه باز می‌ماند. */}
      <path className="nx-ring back"
        d="M96.97 35.90 A50 17 -22 0 0 23.04 84.10"
        fill="none" stroke={`url(#${gR})`} strokeWidth="5"
        strokeLinecap="round" opacity=".5" />

      <path className="nx-n"
        d="M30 92 V28 H50 L74 70 V28 H90 V92 H70 L46 50 V92 Z"
        fill={`url(#${gN})`} />

      <path className="nx-ring front"
        d="M23.04 84.10 A50 17 -22 0 0 96.97 35.90"
        fill="none" stroke={`url(#${gR})`} strokeWidth="5"
        strokeLinecap="round" />
    </svg>
  );
}

/**
 * صفحه‌ی ورود — تا وقتی تکه‌ی اپ برسد.
 *
 * `label` زیرِ نام می‌آید و می‌گوید کدام‌یک از سه اپ دارد بالا
 * می‌آید؛ صفحه‌ی یکسان برای هر سه، به کاربر هیچ نمی‌گوید.
 */
export function Splash({ label = "" }) {
  return (
    <div className="nx-splash" dir="rtl">
      <NexoraMark size={104} animate />
      <div className="nx-word">NEXORA</div>
      {label ? <div className="nx-sub">{label}</div> : null}
      {/* نوارِ پیشرفت عمداً زمان‌بندی‌شده است، نه واقعی: پیشرفتِ
          دانلودِ یک تکه را نمی‌شود صادقانه اندازه گرفت. کارش فقط این
          است که بگوید «ایستاده نیست». */}
      <div className="nx-bar" aria-hidden="true"><i /></div>
    </div>
  );
}
