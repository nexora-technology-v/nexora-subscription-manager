/**
 * اجزای پایه‌ی رابط — هیچ منطق دامنه‌ای این‌جا نیست.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
import React, { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import {
  AlertTriangle, CheckCircle2, ChevronLeft, ChevronRight, Info, Loader2, Minus, Plus, Search, X,
} from "lucide-react";
import { API_URL } from "../lib/constants";
import { faNum, errText } from "../lib/format";

/**
 * ارقام فارسی و عربی و جداکننده‌ها را به عددِ خامِ لاتین تبدیل می‌کند.
 *
 * چرا لازم است: ورودیِ نوع «number» هر چیزی جز رقم لاتین را
 * **بی‌صدا دور می‌ریزد**. اندازه‌گیری‌شده در همین پنل:
 *
 *     تایپ «۱۲۳»    →  value === ""
 *     تایپ «۱۲٬۳۴۵» →  value === ""
 *     تایپ «1,234»  →  value === ""
 *
 * یعنی کاربر فارسی رقم می‌زند و هیچ چیزی در فیلد ظاهر نمی‌شود. نه
 * خطایی، نه پیامی — فقط کار نمی‌کند.
 */
const _AR_FA_DIGIT = /[۰-۹٠-٩]/g;
export const toAsciiDigits = (s) =>
  String(s ?? "").replace(_AR_FA_DIGIT, (d) => {
    const c = d.charCodeAt(0);
    return String(c >= 0x06F0 ? c - 0x06F0 : c - 0x0660);
  });

export function normalizeNumeric(raw, { decimal = false } = {}) {
  // جداکننده‌ی هزارگان (فارسی و لاتین) و فاصله حذف می‌شوند،
  // ممیز فارسی «٫» به نقطه تبدیل می‌شود
  let s = toAsciiDigits(raw)
    .replace(/[٬,،\s]/g, "")
    .replace(/٫/g, ".");
  const neg = s.trim().startsWith("-");
  s = s.replace(/[^0-9.]/g, "");
  if (!decimal) {
    s = s.replace(/\./g, "");
  } else {
    const i = s.indexOf(".");
    if (i >= 0) s = s.slice(0, i + 1) + s.slice(i + 1).replace(/\./g, "");
  }
  return (neg ? "-" : "") + s;
}

/**
 * فیلد عددی — به‌جای `type="number"`.
 *
 * `type="text"` با `inputMode` عددی: صفحه‌کلید عددی روی موبایل باز
 * می‌شود، ولی مرورگر دیگر چیزی را دور نمی‌ریزد. نرمال‌سازی همین‌جا
 * انجام می‌شود، پس `e.target.value` که به دستِ onChange می‌رسد
 * **دقیقاً همان رشته‌ی لاتینی است که قبلاً می‌رسید** — قرارداد با
 * بکند عوض نمی‌شود، فقط دیگر خالی نمی‌ماند.
 *
 * فلش‌های بالا/پایین هم می‌روند، که در چیدمان راست‌به‌چپ جای درستی
 * نداشتند.
 */
export function NumberInput({ value, onChange, decimal = false,
                              className = "fx-input", ...rest }) {
  return (
    <input
      {...rest}
      type="text"
      inputMode={decimal ? "decimal" : "numeric"}
      dir="ltr"
      className={className}
      value={value ?? ""}
      onChange={(e) => {
        // مقدار را روی خودِ فیلد می‌نشانیم تا هم کاربر نتیجه را
        // ببیند و هم onChangeهای موجود بدون تغییر کار کنند
        e.target.value = normalizeNumeric(e.target.value, { decimal });
        onChange(e);
      }}
    />
  );
}

export function Field({ label, hint, children }) {
  return (
    <div className="mb-3">
      <label className="text-[13px] mb-1.5 block" style={{ color: "var(--muted)" }}>{label}</label>
      {children}
      {hint && <p className="text-[12px] mt-1.5 leading-relaxed" style={{ color: "#475569" }}>{hint}</p>}
    </div>
  );
}

export function Toggle({ checked, onChange, label }) {
  return (
    <button onClick={onChange} role="switch" aria-checked={checked} aria-label={label}
      className="w-12 h-[26px] rounded-full transition-all relative shrink-0"
      style={{ background: checked ? "var(--accent)" : "rgba(255,255,255,0.1)" }}>
      <span className="absolute top-[3px] w-5 h-5 rounded-full bg-white transition-all duration-200"
        style={{ [checked ? "right" : "left"]: "3px" }} />
    </button>
  );
}

export function NumberStepper({ value, onChange, min = 0, max = 100, unit }) {
  const clamp = (v) => Math.min(max, Math.max(min, v));
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div>
      <div className="fx-stepper">
        <button className="fx-stepper-btn" onClick={() => onChange(clamp(value - 1))} disabled={value <= min} aria-label="کم کردن"><Minus size={16} /></button>
        <NumberInput className="fx-stepper-val" value={value} onChange={(e) => onChange(clamp(Number(e.target.value) || min))}  />
        {unit && <span className="fx-stepper-unit">{unit}</span>}
        <button className="fx-stepper-btn" onClick={() => onChange(clamp(value + 1))} disabled={value >= max} aria-label="زیاد کردن"><Plus size={16} /></button>
      </div>
      <input className="fx-range" type="range" min={min} max={max} value={value} onChange={(e) => onChange(Number(e.target.value))}
        style={{ background: `linear-gradient(to left, var(--accent) 0%, var(--accent) ${pct}%, rgba(255,255,255,.08) ${pct}%)` }} />
    </div>
  );
}

/**
 * شمارش عدد تا مقدار نهایی.
 *
 * اگر کاربر انیمیشن را در سیستم‌عاملش خاموش کرده باشد، عدد
 * مستقیم نشان داده می‌شود — این یک قابلیت دسترسی‌پذیری است.
 */
export function CountUp({ value, duration = 850 }) {
  const [n, setN] = useState(0);
  const target = Number(value) || 0;

  useEffect(() => {
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
    if (reduce || target === 0) { setN(target); return; }

    let raf, t0;
    const step = (t) => {
      if (!t0) t0 = t;
      const p = Math.min((t - t0) / duration, 1);
      setN(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return <>{n}</>;
}

export function SectionHead({ title, desc, action }) {
  return (
    <div className="flex items-start justify-between gap-3 mb-5 flex-wrap">
      <div className="min-w-0 fx-sec-head">
        <h2 className="text-[16px] font-bold text-white">{title}</h2>
        {desc && <p className="text-[13px] mt-1.5 leading-relaxed" style={{ color: "var(--muted)" }}>{desc}</p>}
      </div>
      {action}
    </div>
  );
}

export function Tabs({ items, active, onChange, counts }) {
  return (
    <div className="fx-tabs flex items-center gap-1.5 mb-5">
      {items.map((t) => {
        const on = active === t.key;
        return (
          <button key={t.key} onClick={() => onChange(t.key)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-[10px] text-[13px] font-medium transition-all"
            style={on ? { color: "#06090F", background: "var(--accent-2)" } : { color: "var(--dim)", border: "1px solid var(--border-2)" }}>
            {t.icon && <t.icon size={13} />} {t.label}
            {counts && <span className="opacity-60 text-[13px]">({counts[t.key] ?? 0})</span>}
          </button>
        );
      })}
    </div>
  );
}

/**
 * حالت خالی.
 *
 * صفحه‌ی خالی بدون راهنما، کاربر را سر دوراهی رها می‌کند. پس علاوه بر
 * متن، می‌شود یک قدم بعدی هم داد: `hint` توضیح می‌دهد چرا خالی است و
 * `action` کاری که باید کرد.
 */
export function EmptyState({ icon: Icon, text, hint, action, tone }) {
  return (
    <div className="fx-card fx-empty fx-fade">
      {/* آیکون داخل یک مربعِ ملایم، نه شناور روی زمینه.
          آیکونِ تنهای کم‌رنگ شبیه «چیزی بارگذاری نشد» بود؛ این
          می‌گوید این‌جا عمداً خالی است. */}
      <span className="fx-empty-ico" style={tone ? { color: tone } : undefined}>
        {/* آیکون اختیاری است: بدون این شرط، فراموش‌کردنش یعنی
            «Element type is invalid» و سقوط همان بخش */}
        {Icon ? <Icon size={22} /> : <Info size={22} />}
      </span>
      <b className="fx-empty-title">{text}</b>
      {hint && <p className="fx-empty-hint">{hint}</p>}
      {action && <div className="mt-4 flex justify-center flex-wrap gap-2">{action}</div>}
    </div>
  );
}

export function StatusChip({ dirty }) {
  return dirty ? (
    <span className="fx-status fx-status-dirty">
      <span className="w-1.5 h-1.5 rounded-full fx-pulse" style={{ background: "var(--warn)" }} /> ذخیره نشده
    </span>
  ) : (
    <span className="fx-status fx-status-saved"><CheckCircle2 size={12} /> ذخیره شده</span>
  );
}

export function InfoBox({ children, tone = "info" }) {
  const t = tone === "warn"
    ? { bg: "rgba(251,191,36,.06)", bd: "rgba(251,191,36,.25)", c: "var(--warn)", Icon: AlertTriangle }
    : { bg: "rgba(43,127,214,.06)", bd: "rgba(43,127,214,.2)", c: "var(--accent-2)", Icon: Info };
  return (
    <div className="rounded-2xl p-4 flex items-start gap-3 my-4 last:mb-0"
      style={{ background: t.bg, border: `1px solid ${t.bd}` }}>
      <t.Icon size={16} className="shrink-0 mt-0.5" style={{ color: t.c }} />
      <div className="text-[13px] leading-relaxed" style={{ color: "var(--dim)" }}>{children}</div>
    </div>
  );
}

/** منحنی نرم از روی نقطه‌ها — کاتمول-رام تبدیل‌شده به بزیه.
 *
 * یک‌جا نوشته شده چون سه نمودار از آن استفاده می‌کنند؛ سه کپی
 * یعنی سه منحنیِ کمی متفاوت در یک صفحه. */
export function smoothPath(pts, closeAt) {
  if (!pts || pts.length < 2) return "";
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i], p1 = pts[i];
    const p2 = pts[i + 1], p3 = pts[i + 2] || p2;
    d += ` C${p1[0] + (p2[0] - p0[0]) / 6},${p1[1] + (p2[1] - p0[1]) / 6}`
       + ` ${p2[0] - (p3[0] - p1[0]) / 6},${p2[1] - (p3[1] - p1[1]) / 6}`
       + ` ${p2[0]},${p2[1]}`;
  }
  if (closeAt !== undefined) {
    d += ` L${pts[pts.length - 1][0]},${closeAt} L${pts[0][0]},${closeAt} Z`;
  }
  return d;
}

export const reducedMotion = () =>
  (typeof document !== "undefined" && document.body.classList.contains("fx-calm")) ||
  (typeof window !== "undefined" &&
   !!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches);

/**
 * اسپارک‌لاین — خطِ ریزِ کنار عدد.
 *
 * زیرش با گرادیان پر می‌شود تا حجم دیده شود، و خط موقع ورود
 * *کشیده* می‌شود نه اینکه یکباره ظاهر شود: چشم مسیر را دنبال
 * می‌کند و جهتِ روند بدون خواندن عدد فهمیده می‌شود.
 */
export function Sparkline({ data, color = "var(--accent-2)", height = 32 }) {
  const id = useRef(`sp${Math.random().toString(36).slice(2, 9)}`).current;
  const ref = useRef(null);
  const ok = data && data.length >= 2;

  useEffect(() => {
    const ln = ref.current?.querySelector("path.ln");
    if (!ln || reducedMotion()) return;
    // getTotalLength در هر محیطی نیست (jsdom ندارد، و همین‌جا هم
    // تست گرفتش). بدون این محافظ، نبودنش کلِ بخش را می‌انداخت —
    // برای یک انیمیشنِ تزئینی. اگر نبود، خط بدون کشیده‌شدن رسم
    // می‌شود و هیچ چیز دیگری فرق نمی‌کند.
    let len;
    try { len = ln.getTotalLength?.(); } catch { return; }
    if (!len) return;
    ln.style.setProperty("--len", len);
    ln.classList.remove("fx-draw");
    void ln.getBoundingClientRect();
    ln.classList.add("fx-draw");
  }, [data]);

  if (!ok) return <div style={{ height }} />;

  const W = 108, H = 34, pad = 4;
  const mx = Math.max(...data), mn = Math.min(...data), rg = mx - mn || 1;
  const pts = data.map((v, i) => [
    (i / (data.length - 1)) * W,
    H - pad - ((v - mn) / rg) * (H - pad * 2),
  ]);

  return (
    <svg ref={ref} className="fx-spark" viewBox={`0 0 ${W} ${H}`}
      style={{ width: "100%", maxWidth: W, height }} aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity=".5" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={smoothPath(pts, H)} fill={`url(#${id})`} />
      <path className="ln" d={smoothPath(pts)} stroke={color} />
    </svg>
  );
}

/**
 * حبسِ تمرکز داخل یک لایه، و برگرداندنش سر جای اول.
 *
 * چرا لازم شد: مودال‌ها `role="dialog"` نداشتند و تمرکز داخلشان
 * حبس نمی‌شد — با Tab می‌شد به صفحه‌ی *زیر* مودال رفت و روی دکمه‌ای
 * زد که دیده نمی‌شود. برای کسی که با کیبورد کار می‌کند، مودال عملاً
 * یک تله بود.
 */
export function useFocusTrap(ref, onClose) {
  useEffect(() => {
    const prev = document.activeElement;
    const sel = 'button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])';
    const box = ref.current;
    const items = () => [...(box?.querySelectorAll(sel) || [])]
      .filter((el) => !el.disabled && el.offsetParent !== null);
    items()[0]?.focus();

    const onKey = (e) => {
      if (e.key === "Escape") { e.stopPropagation(); onClose?.(); return; }
      if (e.key !== "Tab") return;
      const f = items();
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      if (prev && prev.focus) prev.focus();
    };
  }, [ref, onClose]);
}

export function ConfirmModal({ title, desc, onConfirm, onCancel, confirmLabel = "حذف کن" }) {
  const box = useRef(null);
  useFocusTrap(box, onCancel);
  return createPortal(
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 fx-fade"
      style={{ background: "rgba(3,6,12,.78)", backdropFilter: "blur(6px)" }} onClick={onCancel}>
      <div ref={box} role="dialog" aria-modal="true" aria-label={title}
        className="w-full max-w-sm rounded-2xl p-5 fx-scale" onClick={(e) => e.stopPropagation()}
        style={{ background: "var(--surface)", border: "1px solid var(--danger-line)",
                 boxShadow: "var(--e-3)" }}>
        <div className="flex items-center gap-2 mb-2.5" style={{ color: "var(--danger)" }}>
          <AlertTriangle size={18} /><span className="text-[16px] font-semibold">{title}</span>
        </div>
        <p className="text-[13px] mb-5 leading-relaxed" style={{ color: "var(--muted)" }}>{desc}</p>
        <div className="flex gap-2">
          <button onClick={onCancel} className="fx-btn-g flex-1 py-2.5 text-[14px]">انصراف</button>
          <button onClick={onConfirm} className="flex-1 py-2.5 rounded-[11px] text-[14px] font-semibold text-white transition-all hover:brightness-110" style={{ background: "var(--danger)" }}>{confirmLabel}</button>
        </div>
      </div>
    </div>,
    // بدون این آرگومان، createPortal خطای «Target container is not a DOM
    // element» می‌دهد و React کل درخت را می‌اندازد — یعنی هر بار که این
    // مودال باز می‌شد، صفحه سیاه می‌شد. دقیقاً همان چیزی که موقع بستن
    // آی‌پی اتفاق می‌افتاد.
    document.body,
  );
}

/**
 * توست.
 *
 * `role="status"` دارد، پس صفحه‌خوان «ذخیره شد» را اعلام می‌کند.
 * بدون آن، کسی که صفحه را نمی‌بیند هیچ‌وقت نمی‌فهمید کارش انجام
 * شده — همان بازخوردی که برای بقیه بدیهی است.
 */
export function Toast({ message, type }) {
  return (
    <div role="status" aria-live="polite"
      className="fx-toast fixed bottom-[92px] lg:bottom-6 left-1/2 z-[80] px-4 py-3 rounded-xl text-[14px] font-medium flex items-center gap-2 max-w-[90vw]"
      style={{
        background: type === "error" ? "#3F1414" : "rgba(19,28,46,.92)",
        backdropFilter: "blur(20px)",
        border: `1px solid ${type === "error" ? "var(--danger)" : "var(--ok-line)"}`,
        color: type === "error" ? "#FCA5A5" : "var(--ok)",
        boxShadow: "var(--e-3)",
      }}>
      {type === "error" ? <AlertTriangle size={15} /> : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
          <path className="fx-chk" d="m4 12 5.5 5.5L20 7" />
        </svg>
      )} {message}
    </div>
  );
}

export function LoginScreen({ onLogin }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const submit = async () => {
    setLoading(true); setError("");
    try {
      const res = await fetch(`${API_URL}/api/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password }) });
      if (!res.ok) {
        // پیام خودِ سرور را نشان می‌دهیم.
        //
        // حالا که ورودِ ناموفق پشت‌سرهم موقتاً قفل می‌شود، «رمز عبور
        // نادرست است» دقیقاً اشتباه‌ترین چیزی است که می‌شود گفت —
        // مدیر را به تلاش دوباره می‌فرستد، درست وقتی که نباید. پیام
        // سرور می‌گوید چند تلاش مانده یا چقدر باید صبر کند.
        const j = await res.json().catch(() => ({}));
        throw new Error(errText(j.detail, ""));
      }
      onLogin(password);
    } catch (e) { setError(e.message || "رمز عبور نادرست است یا سرور در دسترس نیست."); }
    finally { setLoading(false); }
  };
  return (
    <div className="min-h-screen w-full flex items-center justify-center px-4"
      style={{ background: "radial-gradient(ellipse 60% 50% at 50% 0%, rgba(43,127,214,.15), transparent), var(--bg)" }} dir="rtl">
      <div className="w-full max-w-sm rounded-2xl p-7 fx-anim" style={{ background: "var(--surface)", border: "1px solid rgba(90,169,230,.25)", boxShadow: "0 0 80px rgba(43,127,214,.18)" }}>
        <div className="flex flex-col items-center text-center mb-7">
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center font-bold text-[28px] mb-4"
            style={{ background: "linear-gradient(135deg,#2B7FD6,#8FC1EE)", color: "#06090F" }}>N</div>
          <span className="text-white font-bold text-[18px]">NEXORA</span>
          <span className="text-[13px] mt-1" style={{ color: "var(--muted)" }}>پنل مدیریت صفحه اشتراک</span>
        </div>
        <Field label="رمز عبور مدیریت">
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} onKeyDown={(e) => e.key === "Enter" && submit()}
            autoFocus className="fx-input" style={{ fontFamily: "var(--mono)" }} />
        </Field>
        {error && <p className="text-[13px] mb-3 flex items-center gap-1.5" style={{ color: "var(--danger)" }}><AlertTriangle size={13} />{error}</p>}
        <button onClick={submit} disabled={loading} className="fx-btn w-full py-3 text-[14px] flex items-center justify-center gap-2 mt-2">
          {loading && <Loader2 size={14} className="animate-spin" />} ورود به پنل
        </button>
      </div>
    </div>
  );
}

export function Msg({ msg }) {
  if (!msg) return null;
  const err = msg.t === "err";
  return (
    <div className="rounded-xl p-3 mt-3 mb-4 flex items-center gap-2 text-[13px]"
      style={{
        background: err ? "rgba(248,113,113,.1)" : "rgba(52,211,153,.1)",
        border: `1px solid ${err ? "rgba(248,113,113,.3)" : "rgba(52,211,153,.3)"}`,
        color: err ? "var(--danger)" : "var(--ok)",
      }}>
      {err ? <AlertTriangle size={14} /> : <CheckCircle2 size={14} />} {msg.m}
    </div>
  );
}

export function StatusPill({ s }) {
  const map = {
    awaiting: ["در انتظار", "var(--warn)", "rgba(251,191,36,.12)"],
    review: ["بررسی", "var(--warn)", "rgba(251,191,36,.12)"],
    approved: ["تاییدشده", "var(--ok)", "rgba(52,211,153,.12)"],
    panel_approve: ["در صف ساخت", "var(--accent-2)", "rgba(43,127,214,.12)"],
    rejected: ["ردشده", "var(--danger)", "rgba(248,113,113,.12)"],
  };
  const [l, c, bg] = map[s] || [s, "var(--muted)", "rgba(255,255,255,.05)"];
  return <span className="fx-pill" style={{ background: bg, color: c }}>{l}</span>;
}

/** گروه دکمه‌ی انتخاب — برای فیلترهایی که گزینه‌هایشان کم و ثابت‌اند. */
/**
 * کلید چندحالته، با قرصی که زیر گزینه‌ها سُر می‌خورد.
 *
 * چرا سُر می‌خورد و ظاهر نمی‌شود: وقتی قرص از گزینه‌ی قبلی به
 * گزینه‌ی تازه حرکت می‌کند، چشم می‌فهمد *از کجا به کجا* رفت. رنگ
 * عوض‌شدنِ ناگهانی این را نمی‌گوید.
 *
 * `items` هر دو شکل را می‌پذیرد — `[[مقدار, برچسب]]` که همه‌ی
 * صداکننده‌های قبلی می‌فرستند، و `[{ v, l }]`. دو شکل بهتر از
 * دست‌زدن به ده صفحه است.
 */
export function Segmented({ value, onChange, items }) {
  const box = useRef(null);
  const [pill, setPill] = useState(null);
  const list = (items || []).map((it) =>
    Array.isArray(it) ? { v: it[0], l: it[1] } : it);

  useEffect(() => {
    const host = box.current;
    const el = host?.querySelector('[aria-pressed="true"]');
    if (!host || !el) { setPill(null); return; }
    // در RTL قرص به لبه‌ی راست چسبیده و با transform به چپ می‌آید؛
    // انیمیشن روی left/right یعنی محاسبه‌ی دوباره‌ی چیدمان
    setPill({ w: el.offsetWidth,
              d: host.offsetWidth - el.offsetLeft - el.offsetWidth - 3 });
  }, [value, items]);

  return (
    <div className="fx-seg" ref={box} role="group">
      <span className="fx-seg-pill" aria-hidden="true"
        style={{ width: pill?.w || 0, opacity: pill ? 1 : 0,
                 transform: `translateX(${-(pill?.d || 0)}px)` }} />
      {list.map((it) => (
        <button key={it.v} onClick={() => onChange(it.v)}
          aria-pressed={value === it.v}>{it.l}</button>
      ))}
    </div>
  );
}

export function CountChip({ label, n, color }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[13px]"
      style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
      <span style={{ width: 7, height: 7, borderRadius: "50%", background: color }} />
      <span style={{ color: "var(--dim)" }}>{label}</span>
      <b style={{ color, fontFamily: "var(--mono)" }}>{faNum(n)}</b>
    </span>
  );
}

/**
 * کارتِ شاخص.
 *
 * چیزی بیش از «آیکون + عدد + متن»: وقتی مقدارش عوض می‌شود کارت یک
 * تپشِ کوتاه می‌زند و عدد تا مقدار تازه می‌رود، پس تغییرِ داده دیده
 * می‌شود بدون اینکه کاربر مجبور باشد عدد قبلی را به خاطر بسپارد.
 *
 * `spark`، `trend` و `icon` همه اختیاری‌اند — صدها جای پنل همین
 * کامپوننت را با همان سه آرگومان قبلی صدا می‌زنند و باید دست‌نخورده
 * کار کنند.
 */
export function StatTile({
  label, value, unit, hint, color = "var(--text)",
  icon: Icon, spark, sparkColor, trend, tone, className = "",
}) {
  const box = useRef(null);
  const first = useRef(true);

  useEffect(() => {
    // بار اول تپش نمی‌زند: ورودِ صفحه خودش انیمیشن دارد و دو حرکت
    // هم‌زمان، شلوغ است
    if (first.current) { first.current = false; return; }
    const el = box.current;
    if (!el || reducedMotion()) return;
    el.classList.remove("fx-bump");
    void el.getBoundingClientRect();
    el.classList.add("fx-bump");
  }, [value]);

  return (
    <div className={`fx-card fx-kpi ${className}`}>
      <div className="flex items-center gap-2">
        {Icon && (
          <span className="w-7 h-7 rounded-[8px] grid place-items-center shrink-0"
            style={{ background: "rgba(255,255,255,.05)", color: tone || "var(--muted)" }}>
            <Icon size={14} />
          </span>
        )}
        <span className="fx-kpi-label">{label}</span>
        {trend && (
          <span className={`fx-badge ${trend.up ? "up" : "down"} mr-auto shrink-0`} dir="ltr">
            {trend.up ? "▲" : "▼"} {trend.text}
          </span>
        )}
      </div>

      {/* عدد و واحدش روی یک خط می‌مانند.
          بدون nowrap، «تومان» به خط بعد می‌افتاد و ارتفاع کارت‌ها با
          هم فرق می‌کرد — چهار کارتِ کنار هم که هرکدام یک قد دارند. */}
      <div ref={box} className="fx-kpi-val">
        <span style={{ color, fontFamily: "var(--mono)" }}>{value}</span>
        {unit && <span className="u fx-fa-sub">{unit}</span>}
      </div>

      {/* یک خط، و اگر بلندتر بود بریده می‌شود.
          متنِ چندخطی ارتفاع کارت را بالا می‌برد و ردیفِ شاخص‌ها را
          ناهموار می‌کند؛ عددِ اصلی همان بالاست و این فقط زمینه است. */}
      <div className="fx-kpi-foot">
        <span className="fx-kpi-note" title={typeof hint === "string" ? hint : undefined}>
          {hint || ""}
        </span>
        {spark && spark.length > 1 && (
          <span className="fx-kpi-spark">
            <Sparkline data={spark} color={sparkColor || color} height={30} />
          </span>
        )}
      </div>
    </div>
  );
}

/**
 * اسکلتون — جای چیزی که دارد می‌آید.
 *
 * چرخنده فقط می‌گوید «صبر کن» و وقتی داده رسید کل چیدمان می‌پرد.
 * این، شکلِ محتوا را از قبل نگه می‌دارد.
 */
export function Skeleton({ w = "100%", h = 14, className = "", style }) {
  return <div className={`fx-sk ${className}`} style={{ width: w, height: h, ...style }} />;
}

export function SkeletonCards({ n = 4, cols = "fx-g4" }) {
  return (
    <div className={`grid gap-3 ${cols}`}
      style={{ gridTemplateColumns: `repeat(${Math.min(n, 4)}, minmax(0,1fr))` }}>
      {Array.from({ length: n }, (_, i) => (
        <div key={i} className="fx-card p-4">
          <Skeleton w="52%" h={12} />
          <div className="mt-3"><Skeleton w="70%" h={22} /></div>
          <div className="mt-3"><Skeleton w="40%" h={10} /></div>
        </div>
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 6, cols = 4 }) {
  return (
    <div className="fx-card p-4">
      <div className="flex gap-3 pb-3 mb-1" style={{ borderBottom: "1px solid var(--border)" }}>
        {Array.from({ length: cols }, (_, i) => <Skeleton key={i} w={`${100 / cols - 4}%`} h={10} />)}
      </div>
      {Array.from({ length: rows }, (_, r) => (
        <div key={r} className="flex gap-3 py-3" style={{ borderBottom: "1px solid var(--border)" }}>
          {Array.from({ length: cols }, (_, c) => (
            <Skeleton key={c} w={`${100 / cols - 4}%`} h={13}
              style={{ opacity: 1 - r * 0.1 }} />
          ))}
        </div>
      ))}
    </div>
  );
}

/**
 * دونات — سهمِ هر دسته.
 *
 * بخش‌ها یکی‌یکی کشیده می‌شوند و با موس روی هرکدام، بقیه کم‌رنگ
 * می‌شوند: مقایسه‌ی یک سهم با کل، بدون خواندن عدد.
 */
export function Donut({ items, size = 124, center }) {
  const [hi, setHi] = useState(null);
  const [on, setOn] = useState(false);
  const R = 45, C = 2 * Math.PI * R;
  const tot = (items || []).reduce((s, x) => s + (x.v || 0), 0);

  useEffect(() => { const t = setTimeout(() => setOn(true), 30); return () => clearTimeout(t); }, []);
  if (!tot) return null;

  let off = 0;
  const segs = items.map((it, i) => {
    const len = (it.v / tot) * C;
    const seg = { ...it, len, off, i };
    off += len;
    return seg;
  });

  return (
    <div className="fx-donut-row">
      <svg className="fx-donut" viewBox="0 0 120 120" aria-hidden="true">
        <g transform="rotate(-90 60 60)">
          {segs.map((s) => (
            <circle key={s.i} cx="60" cy="60" r={R} stroke={s.c} strokeWidth="15"
              className={hi === null ? "" : hi === s.i ? "hi" : "dim"}
              strokeDasharray={(on || reducedMotion())
                ? `${Math.max(0, s.len - 2.5)} ${C - s.len + 2.5}` : `0 ${C}`}
              strokeDashoffset={-s.off}
              style={{ transition: `stroke-dasharray .8s var(--sp-soft) ${s.i * 90}ms,
                                    stroke-width var(--m-base) var(--sp-snappy),
                                    opacity var(--m-base) linear` }}
              onMouseEnter={() => setHi(s.i)} onMouseLeave={() => setHi(null)} />
          ))}
        </g>
        {center && (
          <text x="60" y="65" textAnchor="middle" fontSize="15" fontWeight="700"
            fill="var(--text)" fontFamily="var(--sans)">
            {hi === null ? center : items[hi].n}
          </text>
        )}
      </svg>
      <div className="legend flex flex-col gap-0.5">
        {segs.map((s) => (
          <button key={s.i} className="flex items-center gap-2 px-2 py-1.5 rounded-[9px] text-[12px] w-full text-right"
            style={{ color: hi === s.i ? "var(--text)" : "var(--dim)",
                     background: hi === s.i ? "rgba(255,255,255,.05)" : "transparent",
                     transition: "background var(--m-fast) linear, color var(--m-fast) linear" }}
            onMouseEnter={() => setHi(s.i)} onMouseLeave={() => setHi(null)}
            onFocus={() => setHi(s.i)} onBlur={() => setHi(null)}>
            <i className="w-2 h-2 rounded-[3px] shrink-0" style={{ background: s.c }} />
            <span className="truncate">{s.n}</span>
            <b className="mr-auto shrink-0" style={{ fontFamily: "var(--mono)" }}>
              {faNum(Math.round((s.v / tot) * 100))}٪
            </b>
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * میله‌های افقی — مقایسه‌ی چند چیزِ هم‌جنس.
 *
 * میله‌ها پلکانی پر می‌شوند تا ترتیبِ بزرگی دیده شود. مقیاس از
 * بزرگ‌ترین مقدار می‌آید، نه از جمع، وگرنه ردیف‌های کوچک نامرئی
 * می‌شوند.
 */
export function BarList({ items, color = "var(--accent)", format = (v) => faNum(v) }) {
  const mx = Math.max(...(items || []).map((x) => x.v || 0), 1);
  if (!items || !items.length) return null;
  return (
    <div className="flex flex-col gap-2.5">
      {items.map((it, i) => (
        <div key={it.n + i} className="grid items-center gap-2.5 text-[12px]"
          style={{ gridTemplateColumns: "minmax(64px,96px) 1fr auto" }}>
          <span className="truncate" style={{ color: "var(--dim)" }}>{it.n}</span>
          <span className="h-2 rounded-full overflow-hidden"
            style={{ background: "rgba(255,255,255,.06)" }}>
            <i className="fx-barfill block" style={{
              width: `${((it.v || 0) / mx) * 100}%`,
              background: it.c || color,
              animationDelay: `${i * 70}ms`,
              ...(reducedMotion() ? { transform: "scaleX(1)", animation: "none" } : {}),
            }} />
          </span>
          <b style={{ fontFamily: "var(--mono)", color: "var(--dim)" }} dir="ltr">
            {format(it.v)}
          </b>
        </div>
      ))}
    </div>
  );
}

export function Modal({ title, onClose, children, footer, width = "440px" }) {
  const box = useRef(null);
  useFocusTrap(box, onClose);
  return createPortal(
    <div className="nx-modal-wrap fx-fade"
      style={{ background: "rgba(3,6,12,.82)", backdropFilter: "blur(6px)" }}
      onClick={onClose}>
      {/* سه بخش جدا: سر و ته ثابت، وسط اسکرول‌شونده.
          بدون این تقسیم، فرم‌های بلند از صفحه بیرون می‌زنند و
          دکمه‌ی پایین دیده نمی‌شود. */}
      <div ref={box} role="dialog" aria-modal="true" aria-label={title}
        className="rounded-2xl fx-scale nx-modal" onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border-2)",
          width: `min(${width}, 94vw)`,
          boxShadow: "0 1px 0 rgba(255,255,255,.08) inset, 0 24px 60px -18px rgba(0,0,0,.75)",
        }}>

        <div className="nx-modal-head flex justify-between items-center px-5 py-4"
          style={{ borderBottom: "1px solid var(--border)" }}>
          <span className="text-[16px] font-bold text-white">{title}</span>
          <button title="بستن" onClick={onClose} className="fx-ico-btn" style={{ width: 30, height: 30 }}>
            <X size={15} />
          </button>
        </div>

        <div className="nx-modal-body px-5 py-4">
          {children}
        </div>

        {footer && (
          <div className="nx-modal-foot px-5 py-4"
            style={{ borderTop: "1px solid var(--border)" }}>
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body
  );
}


/* ── همکاری در فروش ── */

/**
 * مرز خطا — یک بخش خراب نباید کل پنل را سیاه کند.
 *
 * React وقتی یک کامپوننت خطا بدهد، به‌طور پیش‌فرض کل درخت را جدا
 * می‌کند و صفحه سفید/سیاه می‌شود. این دقیقاً همان چیزی بود که موقع
 * بستن آی‌پی اتفاق می‌افتاد: سرور خطای اعتبارسنجی می‌داد، detail
 * یک آرایه از آبجکت بود، React سعی می‌کرد رندرش کند و می‌افتاد.
 *
 * علت اصلی جداگانه رفع شده (errText)، ولی این لایه می‌ماند: هر
 * باگ ناشناخته‌ی بعدی هم باید فقط همان بخش را از کار بیندازد، نه
 * کل پنل را. کاربر دست‌کم منو را دارد و می‌تواند جای دیگری برود.
 */
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { err: null };
  }

  static getDerivedStateFromError(err) {
    return { err };
  }

  componentDidCatch(err, info) {
    // در کنسول می‌ماند تا اگر لازم شد بشود دنبالش را گرفت
    console.error("بخش پنل خطا داد:", err, info);
  }

  render() {
    if (!this.state.err) return this.props.children;
    return (
      <div className="fx-card p-6 fx-anim">
        <div className="text-[15px] font-semibold mb-2"
          style={{ color: "var(--danger)" }}>
          این بخش باز نشد
        </div>
        <p className="text-[13px] leading-relaxed mb-3"
          style={{ color: "var(--dim)" }}>
          بقیه‌ی پنل سالم است — از منو به بخش دیگری بروید. اگر این خطا
          تکرار شد، متن زیر را برای پشتیبانی بفرستید.
        </p>
        <pre dir="ltr" className="text-[12px] p-3 rounded-lg" style={{
          fontFamily: "var(--mono)", color: "var(--muted)",
          background: "var(--surface-3)", border: "1px solid var(--border)",
          whiteSpace: "pre-wrap", wordBreak: "break-word", maxHeight: 180,
          overflow: "auto",
        }}>{String(this.state.err && (this.state.err.stack
          || this.state.err.message || this.state.err))}</pre>
        <button onClick={() => this.setState({ err: null })}
          className="fx-btn px-4 py-2.5 text-[13px] mt-3">
          دوباره تلاش کن
        </button>
      </div>
    );
  }
}


/**
 * نمودار سطحی — یک یا دو سری روی یک محور.
 *
 * چرا دو سری روی *یک* نمودار و نه دو نمودار زیر هم: دو نمودارِ
 * جدا یعنی دو بار خواندنِ محور و دو بار پیداکردنِ همان روز. وقتی
 * روی هم بیفتند، «فروش بالا رفت ولی تعداد سفارش نه» در یک نگاه
 * دیده می‌شود. ارتفاع کارت هم نصف می‌شود — که همان فضای خالی بود.
 *
 * سری دوم مقیاسِ خودش را دارد: تومان و «تعداد» هیچ‌وقت روی یک
 * مقیاس معنا نمی‌دهند؛ با یک مقیاس، خطِ تعداد همیشه صاف کفِ نمودار
 * می‌چسبد.
 *
 * `data`/`color` مثل قبل کار می‌کنند — ده جای پنل همان‌طور صدایش
 * می‌زنند و نباید دست بخورند.
 */
export function AreaChart({
  data, color = "var(--accent-2)", height = 90, label,
  format = (v) => String(v), fill = true,
  data2, color2 = "var(--cy)", label2, format2,
}) {
  const [hover, setHover] = useState(null);
  const [tipX, setTipX] = useState(0);
  const tipRef = useRef(null);
  const id = useRef(`ac${Math.random().toString(36).slice(2, 9)}`).current;

  const clean = (a) => (a || []).filter((v) => typeof v === "number" && isFinite(v));
  const pts = clean(data);
  const pts2 = clean(data2);
  if (pts.length < 2) {
    return (
      <div className="text-[12px] py-6 text-center" style={{ color: "var(--muted)" }}>
        هنوز داده‌ی کافی نیست
      </div>
    );
  }

  const W = 100, H = 34, PB = 1;
  const max = Math.max(...pts, 1);
  const max2 = Math.max(...pts2, 1);
  const x = (i, n) => (i / ((n || pts.length) - 1)) * W;
  // کف صفر است تا نسبت‌ها صادقانه دیده شوند
  const y = (v) => H - (v / max) * (H - 2) - PB;
  const y2 = (v) => H - (v / max2) * (H - 2) - PB;

  const curve = (arr, fy) => {
    const n = arr.length;
    let d = `M ${x(0, n)},${fy(arr[0])}`;
    for (let i = 0; i < n - 1; i++) {
      const p0 = arr[i === 0 ? 0 : i - 1], p1 = arr[i];
      const p2 = arr[i + 1], p3 = arr[i + 2 < n ? i + 2 : i + 1];
      const c1x = x(i, n) + (x(i + 1, n) - x(i === 0 ? 0 : i - 1, n)) / 6;
      const c1y = fy(p1) + (fy(p2) - fy(p0)) / 6;
      const c2x = x(i + 1, n) - (x(i + 2 < n ? i + 2 : i + 1, n) - x(i, n)) / 6;
      const c2y = fy(p2) - (fy(p3) - fy(p1)) / 6;
      d += ` C ${c1x},${c1y} ${c2x},${c2y} ${x(i + 1, n)},${fy(p2)}`;
    }
    return d;
  };

  const d = curve(pts, y);
  const area = `${d} L ${W},${H} L 0,${H} Z`;
  const d2 = pts2.length >= 2 ? curve(pts2, y2) : null;

  const track = (clientX, el) => {
    const r = el.getBoundingClientRect();
    const rel = (clientX - r.left) / r.width;
    // چیدمان راست‌به‌چپ است ولی نمودار زمانی چپ‌به‌راست می‌ماند
    const i = Math.round(rel * (pts.length - 1));
    const idx = Math.max(0, Math.min(pts.length - 1, i));
    setHover(idx);
    // تولتیپ داخل نمودار می‌ماند.
    //
    // بدون این، در دو سرِ نمودار نصفش بیرون می‌زد و چون
    // translate(-50%) دارد، پهنای *کلِ صفحه* را زیاد می‌کرد —
    // اندازه‌گیری‌شده: کارت ۴۸۰ پیکسل، محتوا ۵۲۱. یعنی یک نوار
    // اسکرول افقی که هیچ‌کس دلیلش را پیدا نمی‌کرد.
    const half = ((tipRef.current && tipRef.current.offsetWidth) || 140) / 2 + 6;
    const px = (x(idx) / W) * r.width;
    setTipX(Math.max(half, Math.min(r.width - half, px)));
  };
  const onMove = (e) => track(e.clientX, e.currentTarget);
  const onTouch = (e) => track(e.touches[0].clientX, e.currentTarget);

  const hv = hover ?? 0;
  // نقطه‌ی متناظر در سری دوم — اگر طولشان یکی نبود، نسبتی
  const j = pts2.length
    ? Math.min(pts2.length - 1, Math.round((hv / (pts.length - 1)) * (pts2.length - 1)))
    : 0;

  return (
    <div className={`relative ${hover !== null ? "fx-hot" : ""}`}>
      {/* تولتیپ شیشه‌ای — روی نمودار، نه زیرش.
          ظرف dir نمی‌گیرد: متنِ فارسی داخلش راست‌چین می‌ماند و
          مختصاتِ SVG اصلاً به جهتِ نوشتار کاری ندارد. */}
      {/* پیش از اولین هاور وسط می‌ماند: با left:0 و translate(-50%)
          نصفش بیرونِ کارت بود و همان پهنای صفحه را زیاد می‌کرد. */}
      <div className="fx-tip" ref={tipRef}
        style={{ left: hover === null ? "50%" : tipX,
                 top: `${(y(pts[hv]) / H) * 100}%` }}>
        <div className="flex items-center gap-2 text-[12px]">
          <i className="w-2 h-2 rounded-[3px] shrink-0" style={{ background: color }} />
          <span style={{ color: "var(--muted)" }}>{label || "مقدار"}</span>
          <b className="mr-auto" style={{ color, fontFamily: "var(--mono)" }}>
            {hover !== null ? format(pts[hv]) : ""}
          </b>
        </div>
        {d2 && (
          <div className="flex items-center gap-2 text-[12px] mt-1">
            <i className="w-2 h-2 rounded-[3px] shrink-0" style={{ background: color2 }} />
            <span style={{ color: "var(--muted)" }}>{label2 || ""}</span>
            <b className="mr-auto" style={{ color: color2, fontFamily: "var(--mono)" }}>
              {hover !== null ? (format2 || format)(pts2[j]) : ""}
            </b>
          </div>
        )}
      </div>

      <svg className="fx-chart" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
        style={{ height, cursor: "crosshair" }}
        onMouseMove={onMove} onMouseLeave={() => setHover(null)}
        onTouchMove={onTouch} onTouchEnd={() => setHover(null)}>
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.38" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
          <clipPath id={`${id}c`}>
            <rect className={reducedMotion() ? "" : "fx-reveal"} x="0" y="0" width={W} height={H} />
          </clipPath>
        </defs>

        {/* خطوط راهنمای افقی — بدون آن‌ها منحنی در فضای خالی شناور است */}
        {[0.25, 0.5, 0.75].map((f) => (
          <line key={f} className="gl" x1="0" y1={H * f} x2={W} y2={H * f}
            vectorEffect="non-scaling-stroke" />
        ))}

        <g clipPath={`url(#${id}c)`}>
          {fill && <path d={area} fill={`url(#${id})`} />}
          <path d={d} fill="none" stroke={color} strokeWidth="1.8"
            strokeLinecap="round" strokeLinejoin="round"
            vectorEffect="non-scaling-stroke" />
          {d2 && (
            <path d={d2} fill="none" stroke={color2} strokeWidth="1.3"
              strokeDasharray="3 4" strokeLinecap="round" opacity=".62"
              vectorEffect="non-scaling-stroke" />
          )}
        </g>

        <line className="fx-guide" x1={x(hv)} y1="0" x2={x(hv)} y2={H}
          vectorEffect="non-scaling-stroke" />
        <circle className="fx-dot" cx={x(hv)} cy={y(pts[hv])} r="2.6" fill={color}
          stroke="var(--surface)" strokeWidth="1.2" vectorEffect="non-scaling-stroke" />
        {d2 && (
          <circle className="fx-dot" cx={x(hv)} cy={y2(pts2[j])} r="2.2" fill={color2}
            stroke="var(--surface)" strokeWidth="1.2" vectorEffect="non-scaling-stroke" />
        )}
      </svg>

      {/* افسانه، و بیشینه‌ی هر سری — تا وقتی موس روی نمودار نیست هم
          معلوم باشد این خط‌ها چه‌اند و سقفشان کجاست */}
      <div className="flex items-center gap-3 flex-wrap text-[11.5px] mt-2"
        style={{ color: "var(--muted)" }}>
        <span className="flex items-center gap-1.5">
          <i className="w-2 h-2 rounded-[3px]" style={{ background: color }} />
          {label}
        </span>
        {d2 && (
          <span className="flex items-center gap-1.5">
            <i className="w-2 h-2 rounded-[3px]" style={{ background: color2 }} />
            {label2}
          </span>
        )}
        <span className="mr-auto" style={{ color: hover !== null ? color : "var(--muted)" }}>
          {hover !== null ? format(pts[hover]) : `بیشینه ${format(max)}`}
        </span>
      </div>
    </div>
  );
}


/**
 * فهرستی که خودش کوتاه می‌ماند.
 *
 * چرا لازم است:
 *     صفحه‌ای که صد ردیف را پشت سر هم می‌ریزد، عملاً غیرقابل استفاده
 *     است: کاربر باید متری اسکرول کند تا به بخش بعدی برسد، و همان
 *     چند ردیفی که مهم‌اند زیر انبوه بقیه گم می‌شوند.
 *
 *     این کامپوننت چند ردیف اول را نشان می‌دهد، بقیه را پشت یک دکمه
 *     نگه می‌دارد، و اگر فهرست به‌قدری بلند باشد که ارزشش را داشته
 *     باشد یک جست‌وجو هم اضافه می‌کند.
 *
 * children یک تابع است که برای هر آیتم JSX برمی‌گرداند — این‌طور
 * ردیف‌ها همان شکلی می‌مانند که هر صفحه می‌خواهد.
 */
/**
 * شماره‌های صفحه با «…» وقتی زیادند.
 *
 * سی دکمه‌ی صفحه خودش یک مشکل اسکرول تازه است؛ اول، آخر، و چندتای
 * اطراف صفحه‌ی جاری کافی است.
 */
function pageNumbers(cur, total) {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  const out = [1];
  const from = Math.max(2, cur - 1);
  const to = Math.min(total - 1, cur + 1);
  if (from > 2) out.push("…");
  for (let i = from; i <= to; i++) out.push(i);
  if (to < total - 1) out.push("…");
  out.push(total);
  return out;
}


export function Pager({ page, pages, total, perPage, onPage }) {
  if (pages <= 1) return null;
  return (
    <div className="flex items-center justify-between gap-2 mt-3 flex-wrap">
      <span className="text-[12px]" style={{ color: "var(--muted)" }}>
        {faNum((page - 1) * perPage + 1)}–
        {faNum(Math.min(page * perPage, total))}
        {" از "}{faNum(total)}
      </span>
      <div className="flex items-center gap-1">
        <button onClick={() => onPage(page - 1)} disabled={page <= 1}
          className="fx-ico-btn" style={{ width: 28, height: 28 }}
          aria-label="صفحه‌ی قبل">
          <ChevronRight size={14} />
        </button>
        {pageNumbers(page, pages).map((n, idx) => (
          n === "…" ? (
            <span key={`g${idx}`} className="px-1 text-[12px]"
              style={{ color: "var(--muted)" }}>…</span>
          ) : (
            <button key={n} onClick={() => onPage(n)}
              className="rounded-lg text-[12px]"
              style={{
                minWidth: 28, height: 28,
                background: n === page ? "var(--accent)" : "var(--surface-3)",
                color: n === page ? "#fff" : "var(--dim)",
                border: `1px solid ${n === page ? "var(--accent)" : "var(--border)"}`,
              }}>{faNum(n)}</button>
          )
        ))}
        <button onClick={() => onPage(page + 1)} disabled={page >= pages}
          className="fx-ico-btn" style={{ width: 28, height: 28 }}
          aria-label="صفحه‌ی بعد">
          <ChevronLeft size={14} />
        </button>
      </div>
    </div>
  );
}


/**
 * صفحه‌بندی برای جایی که LongList نمی‌تواند برود.
 *
 * LongList محتوا را داخل یک div می‌گذارد، و div داخل <table> معتبر
 * نیست — مرورگر آن را بیرون جدول پرت می‌کند. جدول‌ها این هوک را
 * می‌گیرند: برش صفحه‌ی جاری، به‌علاوه‌ی همان کنترلی که بقیه‌ی پنل دارد.
 */
export function usePager(items, perPage = 10) {
  const [page, setPage] = useState(1);
  const all = Array.isArray(items) ? items : [];
  const total = all.length;
  const pages = Math.max(1, Math.ceil(total / perPage));
  const cur = Math.min(page, pages);

  // با عوض‌شدن داده (تعویض تب، فیلتر تازه) به صفحه‌ی اول برمی‌گردیم،
  // وگرنه کاربر روی صفحه‌ی خالیِ یک فهرست کوتاه‌تر می‌ماند
  useEffect(() => { setPage(1); }, [total]);

  return {
    shown: all.slice((cur - 1) * perPage, cur * perPage),
    pager: <Pager page={cur} pages={pages} total={total}
      perPage={perPage} onPage={setPage} />,
  };
}


export function LongList({
  items, children, initial = 8, searchable = false,
  match, empty = "چیزی نیست", label = "مورد", container,
}) {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");

  // با عوض‌شدن جست‌وجو باید به صفحه‌ی اول برگردیم، وگرنه کاربر روی
  // صفحه‌ی پنجمِ نتیجه‌ای می‌ماند که فقط دو صفحه دارد
  useEffect(() => { setPage(1); }, [q]);

  const all = Array.isArray(items) ? items : [];
  const filtered = (!searchable || !q.trim()) ? all : all.filter((it) => {
    if (match) return match(it, q.trim().toLowerCase());
    try {
      return JSON.stringify(it).toLowerCase().includes(q.trim().toLowerCase());
    } catch { return true; }
  });

  // صفحه‌بندی عددی، نه فقط «نمایش بیشتر».
  //
  // «نمایش بیشتر» فهرست را بلندتر می‌کند و صفحه را بزرگ‌تر — دقیقاً
  // همان چیزی که قرار بود حل شود. با صفحه‌بندی، ارتفاع صفحه ثابت
  // می‌ماند هر چقدر داده باشد.
  const perPage = initial;
  const pages = Math.max(1, Math.ceil(filtered.length / perPage));
  const cur = Math.min(page, pages);
  const shown = filtered.slice((cur - 1) * perPage, cur * perPage);

  if (!all.length) {
    return <div className="text-[13px] py-4 text-center"
      style={{ color: "var(--muted)" }}>{empty}</div>;
  }

  return (
    <div>
      {/* جست‌وجو فقط وقتی می‌آید که فهرست به‌قدری بلند باشد که
          پیداکردن یک ردیف در آن سخت شود */}
      {searchable && all.length > initial * 2 && (
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <div className="fx-search" style={{ width: 200 }}>
            <Search size={14} style={{ color: "var(--muted)" }} />
            <input value={q} onChange={(e) => setQ(e.target.value)}
              placeholder="جست‌وجو..." />
          </div>
          <span className="text-[12px]" style={{ color: "var(--muted)" }}>
            {q.trim()
              ? `${faNum(filtered.length)} از ${faNum(all.length)}`
              : `${faNum(all.length)} ${label}`}
          </span>
        </div>
      )}

      {/* ظرف اختیاری: ردیف‌های جدول باید داخل <tbody> بنشینند، نه
          داخل یک <div>. بدون این، هر فهرستِ جدولی مجبور بود
          صفحه‌بندی خودش را از نو بنویسد — و ننوشت. */}
      {container ? container(shown.map(children)) : shown.map(children)}

      {!filtered.length && (
        <div className="text-[13px] py-4 text-center"
          style={{ color: "var(--muted)" }}>
          با این جست‌وجو چیزی پیدا نشد
        </div>
      )}

      <Pager page={cur} pages={pages} total={filtered.length}
        perPage={perPage} onPage={setPage} />
    </div>
  );
}


/**
 * پالت فرمان — Ctrl+K.
 *
 * چرا این‌جا مهم است و در هر پنلی نه: نکسورا **۴۵ صفحه** دارد که
 * در پنج فضای کاری پخش شده‌اند. رسیدن به «تلاش‌های نفوذ» یعنی اول
 * فضای کاری را عوض کن، بعد گروه را پیدا کن، بعد آیتم را. جستجوی
 * بالای سایدبار فقط *همان* فضای کاری را فیلتر می‌کند.
 *
 * این‌جا همه‌ی صفحه‌ها در یک فهرست‌اند، با نام فضای کاری‌شان، و
 * انتخاب یک مورد هم فضای کاری را عوض می‌کند هم صفحه را. یعنی
 * چیزی که دو تصمیم و سه کلیک بود، یک تایپ می‌شود.
 *
 * صفحه‌هایی که badge دارند (هنوز نیامده‌اند) نمی‌آیند — دکمه‌ی
 * بی‌جواب از نبودِ دکمه بدتر است.
 */
export function CommandPalette({ open, onClose, workspaces, onPick, extra = [] }) {
  const [q, setQ] = useState("");
  const [idx, setIdx] = useState(0);
  const box = useRef(null);
  const listRef = useRef(null);

  const all = [];
  Object.values(workspaces || {}).forEach((ws) => {
    ws.groups.forEach((g) => g.items.forEach((it) => {
      if (it.badge) return;
      all.push({ kind: "page", ws: ws.key, key: it.key, label: it.label,
                 group: ws.label, icon: it.icon });
    }));
  });
  extra.forEach((x) => all.push({ kind: "act", ...x }));

  const hits = q
    ? all.filter((x) => x.label.includes(q) || (x.group || "").includes(q))
    : all;

  useEffect(() => { setIdx(0); }, [q]);
  useEffect(() => { if (open) { setQ(""); setIdx(0); } }, [open]);

  // پیمایش با کیبورد — کلِ کار باید بدون موس تمام شود
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape") { onClose(); return; }
      if (e.key === "ArrowDown") { e.preventDefault(); setIdx((i) => Math.min(hits.length - 1, i + 1)); }
      if (e.key === "ArrowUp") { e.preventDefault(); setIdx((i) => Math.max(0, i - 1)); }
      if (e.key === "Enter") {
        e.preventDefault();
        const h = hits[idx];
        if (h) { h.kind === "act" ? h.run() : onPick(h.ws, h.key); onClose(); }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, hits, idx, onPick, onClose]);

  useEffect(() => {
    listRef.current?.querySelector('[aria-selected="true"]')
      ?.scrollIntoView({ block: "nearest" });
  }, [idx]);

  if (!open) return null;

  let lastGroup = "";
  return createPortal(
    <div className="fx-pal-wrap fx-fade" onClick={onClose}>
      <div className="fx-pal" ref={box} role="dialog" aria-modal="true"
        aria-label="پالت فرمان" onClick={(e) => e.stopPropagation()}>
        <input autoFocus value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="بروید به، یا کاری انجام دهید…" aria-label="جستجوی فرمان" />
        <div className="fx-pal-list" ref={listRef} role="listbox">
          {hits.length === 0 && (
            <div className="py-7 text-center text-[13px]" style={{ color: "var(--muted)" }}>
              چیزی با «{q}» پیدا نشد
            </div>
          )}
          {hits.map((h, i) => {
            const head = h.group !== lastGroup ? (lastGroup = h.group) : null;
            return (
              <React.Fragment key={h.kind + (h.key || h.label) + i}>
                {head && <div className="fx-pal-grp">{head}</div>}
                <button className="fx-pal-it" role="option" aria-selected={i === idx}
                  onMouseEnter={() => setIdx(i)}
                  onClick={() => { h.kind === "act" ? h.run() : onPick(h.ws, h.key); onClose(); }}>
                  {h.icon && <h.icon size={15} />}
                  <span className="truncate">{h.label}</span>
                  <span className="mr-auto text-[10px] shrink-0"
                    style={{ color: "var(--muted)", fontFamily: "var(--mono)",
                             opacity: i === idx ? 1 : 0 }}>↵</span>
                </button>
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>,
    document.body,
  );
}

/**
 * نشانگرِ متحرکِ منو.
 *
 * چرا به‌جای رنگ‌کردنِ ساده‌ی آیتم فعال: وقتی نشانگر از آیتم قبلی
 * به آیتم تازه *سُر می‌خورد*، چشم مسیر را دنبال می‌کند و می‌فهمد
 * کجای فهرست است. ظاهرشدنِ ناگهانی این را نمی‌دهد — مخصوصاً در
 * منویی با ۴۵ آیتم که آدم جای خودش را گم می‌کند.
 *
 * والدش باید position: relative باشد و هر آیتم data-navkey داشته
 * باشد. اگر آیتم فعال در این ظرف نباشد (فضای کاری دیگری است)،
 * نشانگر محو می‌شود، نه اینکه روی آیتم اشتباه بنشیند.
 */
export function NavIndicator({ activeKey }) {
  const ref = useRef(null);
  const [box, setBox] = useState(null);

  useEffect(() => {
    let raf;
    const measure = () => {
      const host = ref.current?.parentElement;
      if (!host) return;
      const el = host.querySelector(`[data-navkey="${String(activeKey).replace(/"/g, "")}"]`);
      setBox(el ? { top: el.offsetTop, h: el.offsetHeight } : null);
    };
    measure();
    // یک فریم بعد هم: وقتی آکاردئون تازه باز شده، ارتفاع‌ها هنوز
    // صفرند و اندازه‌گیریِ اول روی صفر می‌نشیند
    raf = requestAnimationFrame(measure);
    window.addEventListener("resize", measure);
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", measure); };
  }, [activeKey]);

  return (
    <span ref={ref} className="fx-ind" aria-hidden="true"
      style={{ opacity: box ? 1 : 0, height: box?.h || 36,
               transform: `translateY(${box?.top || 0}px)` }} />
  );
}

/**
 * اسکلتونِ یک صفحه‌ی کامل.
 *
 * جایگزینِ چرخنده‌ی وسطِ صفحه — که ۳۸ جای این پنل یکسان تکرار شده
 * بود. تفاوتش این است که وقتی داده می‌رسد، چیدمان **نمی‌پرد**:
 * جای کارت‌ها و ردیف‌ها از قبل گرفته شده.
 *
 * شکلش تقریبی است، نه دقیق. هدف نگه‌داشتنِ فضا و ریتم است، نه
 * ساختنِ یک کپیِ بی‌نقص از هر صفحه — که خودش می‌شد یک قاعده‌ی دوم
 * که باید با هر تغییرِ صفحه هماهنگ بماند.
 */
export function PageSkeleton({ cards = 4, rows = 6 }) {
  return (
    <div className="fx-anim" aria-busy="true" aria-live="polite">
      <span className="sr-only">در حال بارگذاری…</span>
      {cards > 0 && (
        <div className="grid gap-3 fx-g4"
          style={{ gridTemplateColumns: `repeat(${cards}, minmax(0,1fr))` }}>
          {Array.from({ length: cards }, (_, i) => (
            <div key={i} className="fx-card p-4" style={{ animationDelay: `${i * 50}ms` }}>
              <Skeleton w="54%" h={11} />
              <div className="mt-3"><Skeleton w="72%" h={21} /></div>
              <div className="mt-3"><Skeleton w="42%" h={9} /></div>
            </div>
          ))}
        </div>
      )}
      {rows > 0 && <SkeletonTable rows={rows} cols={4} />}
    </div>
  );
}

/**
 * نشانِ کاربر — حرفِ اول روی یک زمینه‌ی رنگی.
 *
 * چرا رنگ از خودِ شناسه می‌آید و تصادفی نیست: در فهرستی از چند ده
 * نفر، چشم ردیف را از روی *رنگ* پیدا می‌کند نه از خواندنِ نام. اگر
 * رنگ هر بار عوض شود، این کمک از بین می‌رود. پس از یک هشِ ساده روی
 * شناسه می‌آید — همان کاربر، همیشه همان رنگ.
 *
 * `ring` برای جایی است که خودِ کاربر است (مثلاً بالای مینی‌اپ)، نه
 * یک ردیف در فهرست.
 */
const AVATAR_HUES = [
  ["#2B7FD6", "#5AA9E6"], ["#2DD4BF", "#14B8A6"], ["#A78BFA", "#8B5CF6"],
  ["#34D399", "#10B981"], ["#FBBF24", "#F59E0B"], ["#F87171", "#EF4444"],
  ["#60A5FA", "#3B82F6"], ["#F472B6", "#EC4899"],
];

export function Avatar({ name, id, size = 32, ring = false, className = "" }) {
  const label = String(name || "").trim();
  // حرفِ اول: اگر نام خالی بود، «؟» — نه یک مربعِ خالی که شبیه
  // خرابی به نظر برسد
  const ch = label ? [...label][0] : "؟";
  let h = 0;
  const key = String(id ?? label);
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  const [a, b] = AVATAR_HUES[h % AVATAR_HUES.length];

  return (
    <span className={`fx-avatar ${ring ? "ring" : ""} ${className}`}
      title={label || undefined} aria-hidden={label ? undefined : "true"}
      style={{
        width: size, height: size,
        fontSize: Math.max(11, Math.round(size * 0.42)),
        background: `linear-gradient(140deg, ${a}, ${b})`,
        ...(ring ? { "--ring": a } : {}),
      }}>
      {ch}
    </span>
  );
}
