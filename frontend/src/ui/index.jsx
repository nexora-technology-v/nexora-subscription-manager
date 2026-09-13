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
        <input className="fx-stepper-val" type="number" value={value} onChange={(e) => onChange(clamp(Number(e.target.value) || min))} />
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
      <div className="min-w-0">
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
export function EmptyState({ icon: Icon, text, hint, action }) {
  return (
    <div className="fx-card py-12 px-5 text-center fx-fade" style={{ borderStyle: "dashed" }}>
      {/* آیکون اختیاری است: بدون این شرط، فراموش‌کردن آن یعنی
          «Element type is invalid» و سقوط همان بخش */}
      {Icon && <Icon size={24} className="mx-auto mb-3" style={{ color: "#2A3444" }} />}
      <p className="text-[13px]" style={{ color: "var(--dim)" }}>{text}</p>
      {hint && (
        <p className="text-[12px] mt-2 mx-auto leading-relaxed"
          style={{ color: "var(--muted)", maxWidth: "42ch" }}>{hint}</p>
      )}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
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
    <div className="rounded-2xl p-4 flex items-start gap-3 mt-4"
      style={{ background: t.bg, border: `1px solid ${t.bd}` }}>
      <t.Icon size={16} className="shrink-0 mt-0.5" style={{ color: t.c }} />
      <div className="text-[13px] leading-relaxed" style={{ color: "var(--dim)" }}>{children}</div>
    </div>
  );
}

export function Sparkline({ data, color }) {
  if (!data || data.length < 2) return <div style={{ height: 30 }} />;
  const max = Math.max(...data), min = Math.min(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * 100},${28 - ((v - min) / range) * 24}`).join(" ");
  return (
    <svg width="100%" height="30" viewBox="0 0 100 30" preserveAspectRatio="none" style={{ opacity: .85 }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export function ConfirmModal({ title, desc, onConfirm, onCancel, confirmLabel = "حذف کن" }) {
  useEffect(() => {
    const k = (e) => e.key === "Escape" && onCancel();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onCancel]);
  return createPortal(
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 fx-fade"
      style={{ background: "rgba(3,6,12,.78)", backdropFilter: "blur(6px)" }} onClick={onCancel}>
      <div className="w-full max-w-sm rounded-2xl p-5 fx-scale" onClick={(e) => e.stopPropagation()}
        style={{ background: "var(--surface)", border: "1px solid rgba(248,113,113,.3)" }}>
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

export function Toast({ message, type }) {
  return (
    <div className="fx-toast fixed bottom-[92px] lg:bottom-6 left-1/2 z-[80] px-4 py-3 rounded-xl text-[14px] font-medium flex items-center gap-2 shadow-2xl max-w-[90vw]"
      style={{
        background: type === "error" ? "#3F1414" : "var(--surface)",
        border: `1px solid ${type === "error" ? "var(--danger)" : "rgba(90,169,230,.4)"}`,
        color: type === "error" ? "#FCA5A5" : "var(--accent-2)",
      }}>
      {type === "error" ? <AlertTriangle size={15} /> : <CheckCircle2 size={15} />} {message}
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
export function Segmented({ value, onChange, items }) {
  return (
    <div className="flex items-center rounded-[10px] overflow-hidden"
      style={{ border: "1px solid var(--border-2)" }}>
      {items.map(([v, label], i) => {
        const on = value === v;
        return (
          <button key={v} onClick={() => onChange(v)}
            className="px-3 py-2 text-[13px] transition-colors"
            style={{
              background: on ? "var(--accent-soft)" : "transparent",
              color: on ? "var(--accent-2)" : "var(--muted)",
              fontWeight: on ? 600 : 400,
              borderRight: i ? "1px solid var(--border-2)" : "none",
            }}>{label}</button>
        );
      })}
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

export function StatTile({ label, value, unit, hint, color = "var(--text)" }) {
  return (
    <div className="fx-card p-4">
      <div className="text-[13px] mb-1.5" style={{ color: "var(--muted)" }}>{label}</div>
      <div className="flex items-baseline gap-1.5">
        <span className="text-[21px] font-bold" style={{ color, fontFamily: "var(--mono)" }}>
          {value}
        </span>
        {unit && <span className="text-[13px]" style={{ color: "var(--muted)" }}>{unit}</span>}
      </div>
      {hint && (
        <div className="text-[12px] mt-1.5 leading-relaxed" style={{ color: "var(--muted)" }}>
          {hint}
        </div>
      )}
    </div>
  );
}

export function Modal({ title, onClose, children, footer, width = "440px" }) {
  return createPortal(
    <div className="nx-modal-wrap fx-fade"
      style={{ background: "rgba(3,6,12,.82)", backdropFilter: "blur(6px)" }}
      onClick={onClose}>
      {/* سه بخش جدا: سر و ته ثابت، وسط اسکرول‌شونده.
          بدون این تقسیم، فرم‌های بلند از صفحه بیرون می‌زنند و
          دکمه‌ی پایین دیده نمی‌شود. */}
      <div className="rounded-2xl fx-scale nx-modal" onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border-2)",
          width: `min(${width}, 94vw)`,
          boxShadow: "0 1px 0 rgba(255,255,255,.08) inset, 0 24px 60px -18px rgba(0,0,0,.75)",
        }}>

        <div className="nx-modal-head flex justify-between items-center px-5 py-4"
          style={{ borderBottom: "1px solid var(--border)" }}>
          <span className="text-[16px] font-bold text-white">{title}</span>
          <button onClick={onClose} className="fx-ico-btn" style={{ width: 30, height: 30 }}>
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
 * نمودار سطحی با منحنی نرم.
 *
 * خط شکسته بین نقطه‌ها درست است ولی خشن به نظر می‌رسد و چشم را
 * روی نویز نگه می‌دارد. منحنی کاتمول-رام از همان نقطه‌ها رد می‌شود
 * — پس داده دستکاری نمی‌شود — ولی روند را نشان می‌دهد نه دندانه را.
 *
 * زیر منحنی با گرادیان پر می‌شود تا حجم دیده شود، و نشانگر مقدار
 * هر نقطه را می‌گوید.
 */
export function AreaChart({
  data, color = "var(--accent-2)", height = 90, label,
  format = (v) => String(v), fill = true,
}) {
  const [hover, setHover] = useState(null);
  const id = useRef(`ac${Math.random().toString(36).slice(2, 9)}`).current;

  const pts = (data || []).filter((v) => typeof v === "number" && isFinite(v));
  if (pts.length < 2) {
    return (
      <div className="text-[12px] py-6 text-center" style={{ color: "var(--muted)" }}>
        هنوز داده‌ی کافی نیست
      </div>
    );
  }

  const W = 100, H = 34;
  const max = Math.max(...pts, 1);
  // کف صفر است تا نسبت‌ها صادقانه دیده شوند
  const x = (i) => (i / (pts.length - 1)) * W;
  const y = (v) => H - (v / max) * (H - 2) - 1;

  // کاتمول-رام → بزیه: منحنی از خودِ نقطه‌ها رد می‌شود
  let d = `M ${x(0)},${y(pts[0])}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i === 0 ? 0 : i - 1];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2 < pts.length ? i + 2 : i + 1];
    const c1x = x(i) + (x(i + 1) - x(i === 0 ? 0 : i - 1)) / 6;
    const c1y = y(p1) + (y(p2) - y(p0)) / 6;
    const c2x = x(i + 1) - (x(i + 2 < pts.length ? i + 2 : i + 1) - x(i)) / 6;
    const c2y = y(p2) - (y(p3) - y(p1)) / 6;
    d += ` C ${c1x},${c1y} ${c2x},${c2y} ${x(i + 1)},${y(p2)}`;
  }
  const area = `${d} L ${W},${H} L 0,${H} Z`;

  const onMove = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    const rel = (e.clientX - r.left) / r.width;
    // چیدمان راست‌به‌چپ است ولی نمودار زمانی چپ‌به‌راست می‌ماند
    const i = Math.round(rel * (pts.length - 1));
    setHover(Math.max(0, Math.min(pts.length - 1, i)));
  };

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
        style={{ width: "100%", height, display: "block", cursor: "crosshair" }}
        onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.35" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {fill && <path d={area} fill={`url(#${id})`} />}
        <path d={d} fill="none" stroke={color} strokeWidth="1.6"
          strokeLinecap="round" strokeLinejoin="round"
          vectorEffect="non-scaling-stroke" />
        {hover !== null && (
          <>
            <line x1={x(hover)} y1="0" x2={x(hover)} y2={H}
              stroke={color} strokeWidth="0.6" strokeDasharray="2 2"
              opacity="0.5" vectorEffect="non-scaling-stroke" />
            <circle cx={x(hover)} cy={y(pts[hover])} r="2.2" fill={color}
              stroke="var(--surface)" strokeWidth="1"
              vectorEffect="non-scaling-stroke" />
          </>
        )}
      </svg>
      <div className="text-[12px] mt-1.5 h-[18px] flex justify-between"
        style={{ color: "var(--muted)" }}>
        <span>{label}</span>
        <span style={{ color: hover !== null ? color : "var(--muted)" }}>
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
  match, empty = "چیزی نیست", label = "مورد",
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

      {shown.map(children)}

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
