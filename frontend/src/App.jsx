import React, { useState, useEffect, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
import {
  Activity, AlertTriangle, Apple, ArrowUpRight, Bell, Bot, Check, CheckCircle2, ChevronLeft,
  ChevronDown, Circle, Clock, Coins, Copy, CreditCard, Database, DollarSign, Download, ExternalLink, Eye, Gift, Github, Globe,
  HardDrive, HelpCircle, History, Info, Key, Layers, LayoutGrid, Link2, Loader2, LogOut, Menu, Network, UploadCloud, EyeOff,
  MessageCircle, MessageSquare, Minus, Monitor, Package, Palette, PlayCircle, Plus, Power,
  Radio, RefreshCw, Save, Search, Send, Server, Settings, ShieldCheck, Sliders, Smartphone,
  Star, Terminal, Trash2, TrendingUp, FileText, Wallet, Type, Upload, UserPlus, Users, Video, X, XCircle, Zap,
  Palette as PaletteIcon, Plus as PlusIcon, Sparkles,
} from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8100";

const OS_TABS = [
  { key: "android", label: "اندروید", icon: Smartphone },
  { key: "ios", label: "آیفون / آیپد", icon: Apple },
  { key: "desktop", label: "ویندوز", icon: Monitor },
];
const LANG_TABS = [
  { key: "fa", label: "فارسی" }, { key: "en", label: "English" },
  { key: "tr", label: "Türkçe" }, { key: "ar", label: "العربية" },
];
const SCHEME_OPTIONS = [
  { value: "happ", label: "Happ", icon: Zap },
  { value: "v2rayng", label: "v2rayNG", icon: Send },
  { value: "v2box", label: "V2Box", icon: ShieldCheck },
  { value: "none", label: "بدون افزودن یک‌کلیک", icon: Package },
];
const SCHEME_ICON = Object.fromEntries(SCHEME_OPTIONS.map((s) => [s.value, s.icon]));

// ═══ دو حالت کاری پنل ═══
// کاربر با یک سوییچ بین «مدیریت صفحه اشتراک» و «مدیریت ربات» جابه‌جا می‌شود.
// این کار منو را کوتاه و متمرکز نگه می‌دارد.
const WORKSPACES = {
  sub: {
    key: "sub",
    label: "صفحه اشتراک",
    shortLabel: "ساب",
    icon: Layers,
    groups: [
      {
        title: "مدیریت",
        items: [
          { key: "overview", label: "داشبورد", icon: LayoutGrid },
          { key: "preview", label: "پیش‌نمایش زنده", icon: Eye },
          { key: "resellers", label: "واسطه‌ها", icon: Users },
        ],
      },
      {
        title: "محتوای صفحه",
        items: [
          { key: "apps", label: "اپلیکیشن‌ها", icon: Smartphone },
          { key: "faq", label: "سوالات متداول", icon: HelpCircle },
          { key: "videos", label: "ویدیوهای آموزشی", icon: Video },
          { key: "links", label: "لینک‌ها", icon: Link2 },
        ],
      },
      {
        title: "ظاهر و رفتار",
        items: [
          { key: "banners", label: "بنرهای هشدار", icon: Bell },
          { key: "popup", label: "پاپ‌آپ راهنما", icon: MessageSquare },
          { key: "referral", label: "رفرال", icon: Gift },
          { key: "themes", label: "قالب‌ها", icon: Layers },
          { key: "settings", label: "تنظیمات ظاهری", icon: Sliders },
        ],
      },
      {
        title: "سیستم",
        items: [
          { key: "system", label: "به‌روزرسانی", icon: Server },
        ],
      },
    ],
  },
  billing: {
    key: "billing",
    label: "حسابداری",
    shortLabel: "حساب",
    icon: Wallet,
    groups: [
      {
        title: "مدیریت مالی",
        items: [
          { key: "bill-dash", label: "داشبورد", icon: TrendingUp },
          { key: "bill-groups", label: "واسطه‌ها و نرخ", icon: Users },
          { key: "bill-invoice", label: "صورتحساب", icon: FileText },
          { key: "bill-pay", label: "پرداخت‌ها", icon: Wallet },
          { key: "bill-period", label: "صورتحساب دوره", icon: Clock },
          { key: "bill-clients", label: "همه کاربران", icon: Users },
          { key: "bill-settings", label: "تنظیمات و بک‌آپ", icon: Sliders },
        ],
      },
    ],
  },
  tunnel: {
    key: "tunnel",
    label: "تانل",
    shortLabel: "تانل",
    icon: Network,
    groups: [
      {
        title: "زیرساخت",
        items: [
          { key: "tun-overview", label: "داشبورد", icon: LayoutGrid },
          { key: "tun-nodes", label: "سرورها", icon: Server },
          { key: "tun-list", label: "تانل‌ها", icon: Network },
          { key: "monitor", label: "مانیتورینگ سرور", icon: Activity },
          { key: "tun-health", label: "سلامت سرورها", icon: ShieldCheck },
          { key: "tun-events", label: "رویدادها", icon: Clock },
        ],
      },
    ],
  },
  firewall: {
    key: "firewall",
    label: "فایروال",
    shortLabel: "فایروال",
    icon: ShieldCheck,
    groups: [
      {
        title: "امنیت سرور",
        items: [
          { key: "fw-rules", label: "قواعد فایروال", icon: ShieldCheck },
          { key: "fw-blocked", label: "آی‌پی‌های بسته‌شده", icon: XCircle },
        ],
      },
    ],
  },
  bot: {
    key: "bot",
    label: "ربات تلگرام",
    shortLabel: "ربات",
    icon: Bot,
    groups: [
      {
        title: "پیکربندی ربات",
        items: [
          { key: "bot", label: "اتصال و تنظیمات", icon: Key },
          { key: "bot-inbounds", label: "اینباندها", icon: Network },
          { key: "bot-plans", label: "پلن‌ها و قیمت", icon: Package },
          { key: "bot-orders", label: "سفارش‌ها و رسیدها", icon: CreditCard },
          { key: "bot-users", label: "کاربران ربات", icon: Users },
          { key: "bot-report", label: "گزارش فروش", icon: FileText },
          { key: "bot-coins", label: "سکه و دعوت", icon: Gift },
          { key: "bot-affiliates", label: "همکاری در فروش", icon: Coins },
          { key: "bot-texts", label: "متن‌ها", icon: MessageCircle },
          { key: "bot-preview", label: "پیش‌نمایش ربات", icon: Eye },
          { key: "bot-stats", label: "آمار و قیف", icon: TrendingUp },
          { key: "bot-backup", label: "بک‌آپ ربات", icon: Database },
        ],
      },
      {
        title: "سیستم",
        items: [
          { key: "system", label: "به‌روزرسانی", icon: Server },
        ],
      },
    ],
  },
};

const ALL_NAV = Object.values(WORKSPACES).flatMap((w) => w.groups.flatMap((g) => g.items));

/* ===================== اجزای پایه ===================== */

function Field({ label, hint, children }) {
  return (
    <div className="mb-3">
      <label className="text-[13px] mb-1.5 block" style={{ color: "var(--muted)" }}>{label}</label>
      {children}
      {hint && <p className="text-[12px] mt-1.5 leading-relaxed" style={{ color: "#475569" }}>{hint}</p>}
    </div>
  );
}

function Toggle({ checked, onChange, label }) {
  return (
    <button onClick={onChange} role="switch" aria-checked={checked} aria-label={label}
      className="w-12 h-[26px] rounded-full transition-all relative shrink-0"
      style={{ background: checked ? "var(--accent)" : "rgba(255,255,255,0.1)" }}>
      <span className="absolute top-[3px] w-5 h-5 rounded-full bg-white transition-all duration-200"
        style={{ [checked ? "right" : "left"]: "3px" }} />
    </button>
  );
}

function NumberStepper({ value, onChange, min = 0, max = 100, unit }) {
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
function CountUp({ value, duration = 850 }) {
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

function SectionHead({ title, desc, action }) {
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

function Tabs({ items, active, onChange, counts }) {
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
function EmptyState({ icon: Icon, text, hint, action }) {
  return (
    <div className="fx-card py-12 px-5 text-center fx-fade" style={{ borderStyle: "dashed" }}>
      <Icon size={24} className="mx-auto mb-3" style={{ color: "#2A3444" }} />
      <p className="text-[13px]" style={{ color: "var(--dim)" }}>{text}</p>
      {hint && (
        <p className="text-[12px] mt-2 mx-auto leading-relaxed"
          style={{ color: "var(--muted)", maxWidth: "42ch" }}>{hint}</p>
      )}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}

function StatusChip({ dirty }) {
  return dirty ? (
    <span className="fx-status fx-status-dirty">
      <span className="w-1.5 h-1.5 rounded-full fx-pulse" style={{ background: "var(--warn)" }} /> ذخیره نشده
    </span>
  ) : (
    <span className="fx-status fx-status-saved"><CheckCircle2 size={12} /> ذخیره شده</span>
  );
}

function InfoBox({ children, tone = "info" }) {
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

function Sparkline({ data, color }) {
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

function ConfirmModal({ title, desc, onConfirm, onCancel, confirmLabel = "حذف کن" }) {
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
    </div>
  );
}

function Toast({ message, type }) {
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

function LoginScreen({ onLogin }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const submit = async () => {
    setLoading(true); setError("");
    try {
      const res = await fetch(`${API_URL}/api/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password }) });
      if (!res.ok) throw new Error();
      onLogin(password);
    } catch { setError("رمز عبور نادرست است یا سرور در دسترس نیست."); }
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

/* ===================== داشبورد ===================== */

function OverviewSection({ config, stats, navigate, dirty }) {
  const appsCount = stats?.appsCount ?? OS_TABS.reduce((s, t) => s + (config.downloadApps?.[t.key]?.length || 0), 0);
  const faqCount = stats?.faqCount ?? LANG_TABS.reduce((s, t) => s + (config.faq?.[t.key]?.length || 0), 0);
  const videosCount = stats?.videosCount ?? (config.videos?.length || 0);
  const activeCount = stats?.activeFeaturesCount ?? 0;

  const cards = [
    { key: "apps", label: "اپلیکیشن‌های فعال", value: appsCount, icon: Smartphone, color: "var(--accent-2)", bg: "rgba(43,127,214,.12)", spark: [2, 3, 3, 4, 5, 5, appsCount || 1], sub: "روی ۳ پلتفرم" },
    { key: "faq", label: "سوالات متداول", value: faqCount, icon: HelpCircle, color: "var(--purple)", bg: "rgba(167,139,250,.12)", spark: [1, 2, 3, 4, 4, 5, faqCount || 1], sub: "در ۴ زبان" },
    { key: "videos", label: "ویدیوهای آموزشی", value: videosCount, icon: Video, color: "var(--ok)", bg: "rgba(52,211,153,.12)", spark: [0, 0, 1, 1, 2, 2, videosCount || 1], sub: videosCount ? "قابل نمایش" : "هنوز اضافه نشده" },
    { key: "resellers", label: "واسطه‌های فعال", value: (config.resellers || []).filter(r => r.enabled !== false).length, icon: Users, color: "var(--warn)", bg: "rgba(251,191,36,.12)", spark: [0, 0, 1, 1, 1, 2, (config.resellers || []).length || 1], sub: "برند اختصاصی" },
  ];

  const features = [
    { l: "بنرهای هشدار", on: config.banners?.enabled, k: "banners" },
    { l: "کارت رفرال", on: config.referral?.enabled, k: "referral" },
    { l: "سوالات متداول", on: config.advanced?.showFaqSection !== false, k: "settings" },
    { l: "پاپ‌آپ راهنما", on: config.advanced?.showNotificationPopup !== false, k: "settings" },
  ];

  const quickLinks = [
    { l: "مشاهده پیش‌نمایش زنده", i: Eye, k: "preview" },
    { l: "افزودن ویدیوی آموزشی", i: Video, k: "videos" },
    { l: "ویرایش سوالات متداول", i: HelpCircle, k: "faq" },
    { l: "تنظیمات پیشرفته", i: Settings, k: "settings" },
  ];

  const allApps = OS_TABS.flatMap((t) =>
    (config.downloadApps?.[t.key] || []).map((a) => ({ ...a, platform: t.label }))
  );

  return (
    <div className="fx-anim">
      <div className="fx-g4 grid grid-cols-4 gap-4 mb-5">
        {cards.map((c) => (
          <button key={c.key} onClick={() => navigate(c.key)} className="fx-card fx-card-i p-5 text-right">
            <div className="flex items-start justify-between mb-4">
              <div className="fx-ico" style={{ background: c.bg }}><c.icon size={17} style={{ color: c.color }} /></div>
              <ChevronLeft size={15} style={{ color: "#2A3444" }} />
            </div>
            <div className="flex items-end justify-between gap-2 mb-1">
              <span className="fx-stat-num text-white"><CountUp value={c.value} /></span>
            </div>
            <div className="text-[13px] mb-1" style={{ color: "var(--dim)" }}>{c.label}</div>
            <div className="text-[12px] mb-3" style={{ color: "var(--muted)" }}>{c.sub}</div>
            <Sparkline data={c.spark} color={c.color} />
          </button>
        ))}
      </div>

      <div className="fx-g2 grid gap-4">
        <div className="fx-card overflow-hidden">
          <div className="flex items-center justify-between p-5 pb-4 gap-3 flex-wrap">
            <div>
              <h2 className="text-[16px] font-bold text-white">اپلیکیشن‌های پیکربندی‌شده</h2>
              <p className="text-[13px] mt-1" style={{ color: "var(--muted)" }}>لیست اپ‌های موجود در صفحه اشتراک</p>
            </div>
            <button onClick={() => navigate("apps")} className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
              مدیریت <ChevronLeft size={13} />
            </button>
          </div>
          <div style={{ overflowX: "auto" }}>
            {allApps.length === 0 ? (
              <div className="py-12 text-center text-[13px]" style={{ color: "var(--muted)" }}>هنوز اپی اضافه نشده</div>
            ) : (
              <table className="fx-table">
                <thead>
                  <tr>
                    <th>نام اپ</th>
                    <th>پلتفرم</th>
                    <th className="fx-hide-m">دیپ‌لینک</th>
                    <th>وضعیت</th>
                  </tr>
                </thead>
                <tbody>
                  {allApps.map((a, i) => {
                    const Icon = SCHEME_ICON[a.scheme] || Package;
                    return (
                      <tr key={i}>
                        <td>
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                              style={{ background: a.recommended ? "linear-gradient(135deg,#2B7FD6,#8FC1EE)" : "rgba(255,255,255,.05)" }}>
                              <Icon size={14} color={a.recommended ? "#06090F" : "#5A6880"} />
                            </div>
                            <span className="font-semibold text-white">{a.name}</span>
                          </div>
                        </td>
                        <td style={{ color: "var(--dim)" }}>{a.platform}</td>
                        <td className="fx-hide-m" dir="ltr" style={{ color: "var(--muted)", fontFamily: "var(--mono)", fontSize: 11 }}>
                          {a.scheme === "none" ? "—" : `${a.scheme}://`}
                        </td>
                        <td>
                          {a.recommended ? (
                            <span className="fx-pill" style={{ background: "rgba(43,127,214,.14)", color: "var(--accent-2)" }}>
                              <Star size={9} fill="var(--accent-2)" /> پیشنهادی
                            </span>
                          ) : (
                            <span className="fx-pill" style={{ background: "rgba(255,255,255,.04)", color: "var(--muted)" }}>عادی</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <div className="fx-card p-5" style={{ background: "linear-gradient(150deg,rgba(43,127,214,.14),var(--surface))", borderColor: "rgba(90,169,230,.25)" }}>
            <div className="flex items-start justify-between gap-2 mb-3">
              <div className="fx-ico" style={{ background: "rgba(43,127,214,.16)" }}><Activity size={17} style={{ color: "var(--accent-2)" }} /></div>
              <StatusChip dirty={dirty} />
            </div>
            <h3 className="text-[14px] font-bold text-white mb-1.5">وضعیت صفحه اشتراک</h3>
            <p className="text-[13px] leading-relaxed mb-4" style={{ color: "var(--dim)" }}>قابلیت‌هایی که الان به مشتریان نمایش داده می‌شوند.</p>
            <div className="flex flex-col gap-2.5">
              {features.map((x, i) => (
                <button key={i} onClick={() => navigate(x.k)} className="flex items-center justify-between w-full">
                  <span className="text-[13px]" style={{ color: "var(--dim)" }}>{x.l}</span>
                  <span className="fx-pill" style={{ background: x.on ? "rgba(52,211,153,.12)" : "rgba(255,255,255,.04)", color: x.on ? "var(--ok)" : "var(--muted)" }}>
                    {x.on ? "فعال" : "خاموش"}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className="fx-card p-5">
            <h3 className="text-[14px] font-bold text-white mb-3.5">دسترسی سریع</h3>
            <div className="flex flex-col gap-2">
              {quickLinks.map((x, i) => (
                <button key={i} onClick={() => navigate(x.k)} className="fx-btn-g flex items-center justify-between px-3 py-2.5 text-[13px] w-full">
                  <span className="flex items-center gap-2"><x.i size={14} /> {x.l}</span>
                  <ArrowUpRight size={13} />
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ===================== اپلیکیشن‌ها ===================== */

function PhonePreview({ config, os }) {
  const list = config.downloadApps?.[os] || [];
  const rec = list.find((a) => a.recommended);
  const others = list.filter((a) => !a.recommended);
  const osLabel = OS_TABS.find((t) => t.key === os)?.label;

  return (
    <div className="fx-hide-m">
      <div className="sticky top-24">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-1.5 text-[13px]" style={{ color: "var(--muted)" }}><Eye size={13} /> پیش‌نمایش زنده</div>
          <span className="text-[12px] px-2 py-0.5 rounded-full" style={{ background: "rgba(43,127,214,.12)", color: "var(--accent-2)" }}>{osLabel}</span>
        </div>
        <div className="mx-auto rounded-[2.2rem] p-2.5" style={{ width: 250, background: "linear-gradient(160deg,#1a2130,#0a0e17)", border: "1px solid rgba(255,255,255,.12)", boxShadow: "0 24px 70px rgba(0,0,0,.55)" }}>
          <div className="flex items-center justify-center mb-1.5"><div className="w-14 h-1 rounded-full" style={{ background: "rgba(255,255,255,.15)" }} /></div>
          <div className="rounded-[1.7rem] overflow-hidden" style={{ background: "var(--bg)", minHeight: 380 }}>
            <div className="flex items-center justify-between px-4 pt-3 pb-1 text-[10px]" style={{ color: "var(--muted)" }}>
              <span style={{ fontFamily: "var(--mono)" }}>۱۰:۳۰</span>
              <div className="flex items-center gap-1"><span className="w-1 h-1 rounded-full" style={{ background: "var(--ok)" }} /><span>Nexora</span></div>
            </div>
            <div className="px-3.5 pb-4">
              <div className="text-[12px] font-bold text-white text-center my-3">دانلود برنامه ها</div>
              <div className="rounded-lg px-2.5 py-2 mb-3 flex items-start gap-1.5" style={{ background: "rgba(43,127,214,.1)", border: "1px solid rgba(43,127,214,.3)" }}>
                <Star size={9} className="shrink-0 mt-0.5" style={{ color: "var(--accent-2)" }} fill="var(--accent-2)" />
                <div className="text-[10.5px] leading-relaxed" style={{ color: "var(--accent-2)" }}>پیشنهاد ما: <b>{rec?.name || "—"}</b></div>
              </div>
              {[rec, ...others].filter(Boolean).map((app, i) => {
                const Icon = SCHEME_ICON[app.scheme] || Package;
                return (
                  <div key={i} className="rounded-xl p-3 mb-2 relative" style={{ background: "var(--surface)", border: app.recommended ? "1px solid rgba(90,169,230,.45)" : "1px solid var(--border)" }}>
                    {app.recommended && <div className="absolute -top-2 right-3 text-[9px] px-2 py-0.5 rounded-full" style={{ background: "linear-gradient(135deg,#2B7FD6,#5AA9E6)", color: "#06090F", fontWeight: 700 }}>پیشنهادی</div>}
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="min-w-0">
                        <div className="text-[12px] font-bold text-white truncate">{app.name}</div>
                        <div className="text-[10px]" style={{ color: "var(--muted)" }}>کلاینت رسمی</div>
                      </div>
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: app.recommended ? "linear-gradient(135deg,#2B7FD6,#8FC1EE)" : "rgba(255,255,255,.05)" }}>
                        <Icon size={14} color={app.recommended ? "#06090F" : "#5A6880"} />
                      </div>
                    </div>
                    <div className="flex flex-col gap-1">
                      {app.scheme !== "none" && <div className="text-[10px] text-center py-1.5 rounded-lg font-bold" style={{ background: "linear-gradient(135deg,#2B7FD6,#5AA9E6)", color: "#06090F" }}>افزودن با یک کلیک</div>}
                      <div className="text-[9.5px] text-center py-1 rounded-lg" style={{ border: "1px solid var(--border-2)", color: "var(--muted)" }}>دانلود اپ</div>
                    </div>
                  </div>
                );
              })}
              {list.length === 0 && <div className="text-[11px] text-center py-12" style={{ color: "#2A3444" }}>هیچ اپی اضافه نشده</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function AppsSection({ config, setConfig, requestDelete }) {
  const [osTab, setOsTab] = useState("android");
  const list = config.downloadApps?.[osTab] || [];
  const counts = Object.fromEntries(OS_TABS.map((t) => [t.key, config.downloadApps?.[t.key]?.length || 0]));

  const updateApp = (i, patch) => {
    const l = [...list]; l[i] = { ...l[i], ...patch };
    setConfig({ ...config, downloadApps: { ...(config.downloadApps || {}), [osTab]: l } });
  };
  const setRec = (i) => {
    const l = list.map((a, j) => ({ ...a, recommended: j === i }));
    setConfig({ ...config, downloadApps: { ...(config.downloadApps || {}), [osTab]: l } });
  };
  const addApp = () => setConfig({ ...config, downloadApps: { ...(config.downloadApps || {}), [osTab]: [...list, { id: `app-${Date.now()}`, name: "اپ جدید", url: "", recommended: list.length === 0, scheme: "none" }] } });

  return (
    <div className="fx-g2 grid gap-6 fx-anim" style={{ gridTemplateColumns: "1fr 280px" }}>
      <div className="min-w-0">
        <SectionHead title="اپلیکیشن‌های دانلود" desc="برای هر پلتفرم، اپ‌های قابل‌دانلود و اپ پیشنهادی را مدیریت کنید." />
        <Tabs items={OS_TABS} active={osTab} onChange={setOsTab} counts={counts} />
        <div className="flex flex-col gap-3">
          {list.length === 0 && <EmptyState icon={Smartphone} text="هنوز اپی برای این پلتفرم اضافه نشده"
            hint="مشتری در صفحه‌ی اشتراک هیچ دکمه‌ی نصبی نمی‌بیند تا اینجا حداقل یک اپ اضافه کنید." />}
          {list.map((app, i) => {
            const Icon = SCHEME_ICON[app.scheme] || Package;
            return (
              <div key={app.id || i} className={`fx-card p-4 ${app.recommended ? "fx-card-hl" : ""}`}>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="fx-ico" style={{ background: app.recommended ? "linear-gradient(135deg,#2B7FD6,#8FC1EE)" : "rgba(255,255,255,.05)" }}>
                      <Icon size={16} color={app.recommended ? "#06090F" : "#5A6880"} />
                    </div>
                    <button onClick={() => setRec(i)} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-[10px] text-[13px] font-semibold transition-all"
                      style={app.recommended ? { color: "#06090F", background: "linear-gradient(135deg,#2B7FD6,#5AA9E6)" } : { color: "var(--muted)", background: "rgba(255,255,255,.05)" }}>
                      <Star size={11} fill={app.recommended ? "#06090F" : "none"} /> {app.recommended ? "پیشنهادی" : "انتخاب به‌عنوان پیشنهادی"}
                    </button>
                  </div>
                  <button onClick={() => requestDelete({ type: "app", os: osTab, idx: i, name: app.name })} className="fx-ico-btn shrink-0"><Trash2 size={15} /></button>
                </div>
                <div className="fx-g3 grid grid-cols-2 gap-3">
                  <Field label="نام اپ"><input className="fx-input" value={app.name} onChange={(e) => updateApp(i, { name: e.target.value })} /></Field>
                  <Field label="نوع افزودن یک‌کلیک">
                    <select className="fx-input" value={app.scheme} onChange={(e) => updateApp(i, { scheme: e.target.value })}>
                      {SCHEME_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                    </select>
                  </Field>
                </div>
                <Field label="لینک دانلود"><input className="fx-input" dir="ltr" value={app.url} onChange={(e) => updateApp(i, { url: e.target.value })} placeholder="https://..." /></Field>
              </div>
            );
          })}
          <button onClick={addApp} className="fx-btn-dash flex items-center justify-center gap-2 py-3.5 text-[14px]">
            <Plus size={15} /> افزودن اپ جدید به {OS_TABS.find((t) => t.key === osTab)?.label}
          </button>
        </div>
      </div>
      <PhonePreview config={config} os={osTab} />
    </div>
  );
}

/* ===================== ویدیوها ===================== */

function VideosSection({ config, setConfig, requestDelete }) {
  const videos = config.videos || [];
  const update = (i, patch) => { const l = [...videos]; l[i] = { ...l[i], ...patch }; setConfig({ ...config, videos: l }); };
  const add = () => setConfig({ ...config, videos: [...videos, { id: `vid-${Date.now()}`, title: "آموزش جدید", telegramUrl: "", platform: "all" }] });

  const incomplete = videos.filter((v) => !v.telegramUrl || !v.telegramUrl.trim()).length;

  return (
    <div className="fx-anim">
      <SectionHead title="ویدیوهای آموزشی" desc="ویدیوها را در کانال تلگرام خود آپلود کنید و فقط لینک پیام را اینجا بگذارید — هیچ حجمی از سرور مصرف نمی‌شود." />

      {incomplete > 0 && (
        <div className="mb-4">
          <InfoBox tone="warn">
            <b>{incomplete} ویدیو بدون لینک است</b> و در صفحه‌ی مشتری نمایش داده نمی‌شود.
            برای هر ویدیو حتماً لینک تلگرام را وارد کنید.
          </InfoBox>
        </div>
      )}

      <div className="mb-4">
        <InfoBox>
          <b>چطور لینک بگیرم؟</b> ویدیو را در کانال تلگرام‌تان بفرستید، روی پیام لمس طولانی کنید و «Copy Link» را بزنید. لینکی شبیه <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>t.me/yanexoravpn/42</span> می‌گیرید.
          <br /><span style={{ color: "var(--warn)" }}>توجه:</span> لینک Saved Messages شخصی برای مشتری‌ها باز نمی‌شود — حتماً از کانال عمومی استفاده کنید.
        </InfoBox>
      </div>
      <div className="flex flex-col gap-3">
        {videos.length === 0 && <EmptyState icon={Video} text="هنوز ویدیویی اضافه نشده"
          hint="ویدیوی آموزش نصب، بیشترین سؤال پشتیبانی را کم می‌کند." />}
        {videos.map((v, i) => (
          <div key={v.id || i} className="fx-card p-4">
            <div className="flex items-center justify-between gap-2 mb-3">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="fx-ico" style={{ background: "rgba(43,127,214,.12)" }}><PlayCircle size={16} style={{ color: "var(--accent-2)" }} /></div>
                <span className="text-[14px] font-semibold text-white truncate">{v.title || "بدون عنوان"}</span>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                {v.telegramUrl && <a href={v.telegramUrl} target="_blank" rel="noreferrer" className="fx-ico-btn" style={{ color: "var(--accent-2)" }}><ExternalLink size={14} /></a>}
                <button onClick={() => requestDelete({ type: "video", idx: i, name: v.title })} className="fx-ico-btn"><Trash2 size={15} /></button>
              </div>
            </div>
            <div className="fx-g3 grid grid-cols-2 gap-3">
              <Field label="عنوان ویدیو"><input className="fx-input" value={v.title} onChange={(e) => update(i, { title: e.target.value })} placeholder="آموزش نصب Happ در اندروید" /></Field>
              <Field label="مربوط به پلتفرم">
                <select className="fx-input" value={v.platform} onChange={(e) => update(i, { platform: e.target.value })}>
                  <option value="all">همه پلتفرم‌ها</option>
                  {OS_TABS.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
                </select>
              </Field>
            </div>
            <Field label="لینک پیام تلگرام" hint="مثال: https://t.me/yanexoravpn/42">
              <input className="fx-input" dir="ltr" value={v.telegramUrl} onChange={(e) => update(i, { telegramUrl: e.target.value })} placeholder="https://t.me/..." />
            </Field>
          </div>
        ))}
        <button onClick={add} className="fx-btn-dash flex items-center justify-center gap-2 py-3.5 text-[14px]"><Plus size={15} /> افزودن ویدیوی آموزشی</button>
      </div>
    </div>
  );
}

/* ===================== FAQ ===================== */

function FaqSection({ config, setConfig, requestDelete }) {
  const [lang, setLang] = useState("fa");
  const list = config.faq?.[lang] || [];
  const counts = Object.fromEntries(LANG_TABS.map((t) => [t.key, config.faq?.[t.key]?.length || 0]));
  const update = (i, patch) => { const l = [...list]; l[i] = { ...l[i], ...patch }; setConfig({ ...config, faq: { ...(config.faq || {}), [lang]: l } }); };
  const add = () => setConfig({ ...config, faq: { ...(config.faq || {}), [lang]: [...list, { q: "", a: "" }] } });

  return (
    <div className="fx-anim">
      <SectionHead title="سوالات متداول" desc="این سوال‌ها به‌صورت آکاردئون در پایین صفحه‌ی اشتراک نمایش داده می‌شوند." />
      <Tabs items={LANG_TABS} active={lang} onChange={setLang} counts={counts} />
      <div className="flex flex-col gap-3">
        {list.length === 0 && <EmptyState icon={HelpCircle} text="هنوز سوالی برای این زبان اضافه نشده"
          hint="سوال‌های متداول در همان صفحه جواب می‌دهند و بار پشتیبانی را کم می‌کنند." />}
        {list.map((item, i) => (
          <div key={i} className="fx-card p-4">
            <div className="flex items-start justify-between mb-2.5">
              <span className="fx-pill" style={{ background: "rgba(255,255,255,.04)", color: "var(--muted)" }}>سوال {i + 1}</span>
              <button onClick={() => requestDelete({ type: "faq", lang, idx: i, name: item.q || "این سوال" })} className="fx-ico-btn"><Trash2 size={14} /></button>
            </div>
            <Field label="متن سوال"><input className="fx-input" value={item.q} onChange={(e) => update(i, { q: e.target.value })} /></Field>
            <Field label="متن پاسخ"><textarea className="fx-input" value={item.a} onChange={(e) => update(i, { a: e.target.value })} rows={2} /></Field>
          </div>
        ))}
        <button onClick={add} className="fx-btn-dash flex items-center justify-center gap-2 py-3.5 text-[14px]"><Plus size={15} /> افزودن سوال جدید</button>
      </div>
    </div>
  );
}

/* ===================== بنرها ===================== */

function BannersSection({ config, setConfig }) {
  const b = config.banners || {};
  const update = (patch) => setConfig({ ...config, banners: { ...b, ...patch } });
  const [tab, setTab] = useState("thresholds");

  const TABS_B = [
    { key: "thresholds", label: "آستانه‌ها", icon: Sliders },
    { key: "disabled", label: "متن بنر قطعی", icon: AlertTriangle },
    { key: "lowquota", label: "متن بنر اتمام", icon: Clock },
  ];

  return (
    <div className="fx-anim">
      <SectionHead title="بنرهای هشدار" desc="بنرهایی که بالای داشبورد صفحه‌ی اشتراک، بسته به شرایط، خودکار ظاهر می‌شوند." />

      <div className="fx-card p-5 mb-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="fx-ico" style={{ background: "rgba(43,127,214,.12)" }}><Bell size={16} style={{ color: "var(--accent-2)" }} /></div>
            <div className="min-w-0">
              <div className="text-[14px] font-semibold text-white">فعال‌سازی کلی بنرها</div>
              <div className="text-[13px] mt-0.5" style={{ color: "var(--muted)" }}>اگر خاموش کنید، هیچ بنری نمایش داده نمی‌شود</div>
            </div>
          </div>
          <Toggle checked={b.enabled !== false} onChange={() => update({ enabled: !(b.enabled !== false) })} label="بنرها" />
        </div>
      </div>

      <div style={{ opacity: b.enabled !== false ? 1 : 0.45, pointerEvents: b.enabled !== false ? "auto" : "none" }}>
        <Tabs items={TABS_B} active={tab} onChange={setTab} />

        {tab === "thresholds" && (
          <div className="fx-g3 grid grid-cols-2 gap-4 fx-fade">
            <div className="fx-card p-5">
              <div className="flex items-center gap-2 mb-4"><Clock size={14} style={{ color: "var(--warn)" }} /><span className="text-[14px] font-semibold text-white">هشدار پایان زمان</span></div>
              <NumberStepper value={b.lowQuotaDaysThreshold ?? 3} onChange={(v) => update({ lowQuotaDaysThreshold: v })} min={1} max={30} unit="روز" />
              <p className="text-[12px] mt-3 leading-relaxed" style={{ color: "#475569" }}>
                از <b style={{ color: "var(--warn)" }}>{b.lowQuotaDaysThreshold ?? 3} روز</b> مانده به انقضا، بنر نمایش داده می‌شود.
              </p>
            </div>
            <div className="fx-card p-5">
              <div className="flex items-center gap-2 mb-4"><Package size={14} style={{ color: "var(--warn)" }} /><span className="text-[14px] font-semibold text-white">هشدار پایان حجم</span></div>
              <NumberStepper value={b.lowQuotaPercentThreshold ?? 15} onChange={(v) => update({ lowQuotaPercentThreshold: v })} min={1} max={50} unit="درصد" />
              <p className="text-[12px] mt-3 leading-relaxed" style={{ color: "#475569" }}>
                وقتی کمتر از <b style={{ color: "var(--warn)" }}>{b.lowQuotaPercentThreshold ?? 15}٪</b> حجم باقی باشد، بنر ظاهر می‌شود.
              </p>
            </div>
          </div>
        )}

        {tab === "disabled" && (
          <div className="fx-g2 grid gap-5 fx-fade" style={{ gridTemplateColumns: "1fr 280px" }}>
            <div className="fx-card p-5">
              <div className="text-[14px] font-semibold text-white mb-1">بنر «کانفیگ غیرفعال است»</div>
              <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
                وقتی کانفیگ مشتری غیرفعال شده باشد (مثلاً به‌خاطر تخطی از محدودیت IP) این بنر نمایش داده می‌شود.
              </p>
              <Field label="عنوان" hint="خالی بگذارید تا متن پیش‌فرض استفاده شود">
                <input className="fx-input" value={b.disabledTitle || ""} onChange={(e) => update({ disabledTitle: e.target.value })} placeholder="این کانفیگ غیرفعال است" />
              </Field>
              <Field label="متن توضیحات">
                <textarea className="fx-input" rows={3} value={b.disabledDesc || ""} onChange={(e) => update({ disabledDesc: e.target.value })}
                  placeholder="این اتفاق معمولاً به‌خاطر استفاده‌ی هم‌زمان از چند دستگاه می‌افتد..." />
              </Field>
              <Field label="متن دکمه">
                <input className="fx-input" value={b.disabledButtonText || ""} onChange={(e) => update({ disabledButtonText: e.target.value })} placeholder="تماس با پشتیبانی" />
              </Field>
            </div>
            <div className="fx-hide-m">
              <div className="sticky top-24">
                <div className="flex items-center gap-1.5 text-[13px] mb-3" style={{ color: "var(--muted)" }}><Eye size={13} /> پیش‌نمایش</div>
                <div className="rounded-2xl p-4" style={{ background: "rgba(248,113,113,.08)", border: "1px solid rgba(248,113,113,.3)" }}>
                  <div className="flex items-start gap-2.5">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: "rgba(248,113,113,.18)" }}>
                      <AlertTriangle size={14} style={{ color: "var(--danger)" }} />
                    </div>
                    <div className="min-w-0">
                      <div className="text-[13px] font-bold text-white mb-1">{b.disabledTitle || "این کانفیگ غیرفعال است"}</div>
                      <div className="text-[12px] leading-relaxed mb-2.5" style={{ color: "var(--dim)" }}>
                        {b.disabledDesc || "این اتفاق معمولاً به‌خاطر استفاده‌ی هم‌زمان از چند دستگاه می‌افتد."}
                      </div>
                      <div className="inline-block text-[12px] font-bold px-2.5 py-1.5 rounded-lg" style={{ background: "var(--danger)", color: "#1a0505" }}>
                        {b.disabledButtonText || "تماس با پشتیبانی"}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {tab === "lowquota" && (
          <div className="fx-g2 grid gap-5 fx-fade" style={{ gridTemplateColumns: "1fr 280px" }}>
            <div className="fx-card p-5">
              <div className="text-[14px] font-semibold text-white mb-1">بنر «اشتراک رو به اتمام»</div>
              <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
                وقتی حجم یا زمان اشتراک مشتری به آستانه‌ی تعیین‌شده برسد، این بنر نمایش داده می‌شود.
              </p>
              <Field label="عنوان">
                <input className="fx-input" value={b.lowQuotaTitle || ""} onChange={(e) => update({ lowQuotaTitle: e.target.value })} placeholder="اشتراک شما رو به اتمام است" />
              </Field>
              <Field label="متن هشدار پایان زمان" hint="از {days} برای نمایش تعداد روز باقی‌مانده استفاده کنید">
                <textarea className="fx-input" rows={2} value={b.lowQuotaDescDays || ""} onChange={(e) => update({ lowQuotaDescDays: e.target.value })}
                  placeholder="فقط {days} روز از اشتراک شما باقی مانده. همین حالا تمدید کنید." />
              </Field>
              <Field label="متن هشدار پایان حجم">
                <textarea className="fx-input" rows={2} value={b.lowQuotaDescVolume || ""} onChange={(e) => update({ lowQuotaDescVolume: e.target.value })}
                  placeholder="حجم اشتراک شما رو به اتمام است. همین حالا تمدید کنید." />
              </Field>
              <div className="fx-g3 grid grid-cols-2 gap-3">
                <Field label="متن دکمه">
                  <input className="fx-input" value={b.lowQuotaButtonText || ""} onChange={(e) => update({ lowQuotaButtonText: e.target.value })} placeholder="تمدید اشتراک" />
                </Field>
                <Field label="لینک دکمه" hint="خالی = لینک پشتیبانی">
                  <input className="fx-input" dir="ltr" value={b.lowQuotaButtonUrl || ""} onChange={(e) => update({ lowQuotaButtonUrl: e.target.value })} placeholder="https://t.me/..." />
                </Field>
              </div>
            </div>
            <div className="fx-hide-m">
              <div className="sticky top-24">
                <div className="flex items-center gap-1.5 text-[13px] mb-3" style={{ color: "var(--muted)" }}><Eye size={13} /> پیش‌نمایش</div>
                <div className="rounded-2xl p-4" style={{ background: "rgba(251,191,36,.08)", border: "1px solid rgba(251,191,36,.3)" }}>
                  <div className="flex items-start gap-2.5">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: "rgba(251,191,36,.18)" }}>
                      <Clock size={14} style={{ color: "var(--warn)" }} />
                    </div>
                    <div className="min-w-0">
                      <div className="text-[13px] font-bold text-white mb-1">{b.lowQuotaTitle || "اشتراک شما رو به اتمام است"}</div>
                      <div className="text-[12px] leading-relaxed mb-2.5" style={{ color: "var(--dim)" }}>
                        {(b.lowQuotaDescDays || "فقط {days} روز از اشتراک شما باقی مانده.").replace("{days}", String(b.lowQuotaDaysThreshold ?? 3))}
                      </div>
                      <div className="inline-block text-[12px] font-bold px-2.5 py-1.5 rounded-lg" style={{ background: "var(--warn)", color: "#2a1c02" }}>
                        {b.lowQuotaButtonText || "تمدید اشتراک"}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ===================== رفرال ===================== */

function ReferralSection({ config, setConfig }) {
  const r = config.referral || { enabled: true };
  return (
    <div className="fx-anim">
      <SectionHead title="سیستم رفرال" desc="کارت معرفی به دوستان که در داشبورد صفحه‌ی اشتراک نمایش داده می‌شود." />
      <div className="fx-card p-5 mb-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="fx-ico" style={{ background: "rgba(43,127,214,.12)" }}><Gift size={16} style={{ color: "var(--accent-2)" }} /></div>
            <div className="min-w-0">
              <div className="text-[14px] font-semibold text-white">نمایش کارت رفرال</div>
              <div className="text-[13px] mt-0.5" style={{ color: "var(--muted)" }}>اگر خاموش کنید، کارت معرفی نمایش داده نمی‌شود</div>
            </div>
          </div>
          <Toggle checked={r.enabled} onChange={() => setConfig({ ...config, referral: { ...r, enabled: !r.enabled } })} label="رفرال" />
        </div>
      </div>
      <InfoBox tone="warn">
        فعلاً این کارت فقط یک لینک پیام آماده به پشتیبانی است، بدون ردیابی خودکار پاداش. برای پاداش‌دهی خودکار، باید منطق جداگانه‌ای در ربات تلگرام پیاده‌سازی شود.
      </InfoBox>
    </div>
  );
}

/* ===================== لینک‌ها ===================== */

function LinksSection({ config, setConfig }) {
  const l = config.links;
  const update = (patch) => setConfig({ ...config, links: { ...l, ...patch } });
  return (
    <div className="fx-anim">
      <SectionHead title="لینک‌های ارتباطی" desc="آدرس‌های پشتیبانی و کانال که در سراسر صفحه‌ی اشتراک استفاده می‌شوند." />
      <div className="fx-card p-5">
        <div className="text-[14px] font-semibold text-white mb-4 flex items-center gap-2"><MessageCircle size={15} style={{ color: "var(--accent-2)" }} /> پشتیبانی و کانال</div>
        <div className="fx-g3 grid grid-cols-2 gap-4">
          <Field label="یوزرنیم تلگرام پشتیبانی" hint="بدون @ وارد کنید">
            <input className="fx-input" dir="ltr" value={l.supportUsername} onChange={(e) => update({ supportUsername: e.target.value })} placeholder="crm_nexoravpn" />
          </Field>
          <Field label="یوزرنیم کانال" hint="بدون @ وارد کنید">
            <input className="fx-input" dir="ltr" value={l.channelUsername} onChange={(e) => update({ channelUsername: e.target.value })} placeholder="yanexoravpn" />
          </Field>
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          <a href={`https://t.me/${l.supportUsername}`} target="_blank" rel="noreferrer" className="text-[13px] px-3 py-1.5 rounded-lg flex items-center gap-1.5" style={{ background: "rgba(43,127,214,.1)", color: "var(--accent-2)" }}>
            <ExternalLink size={11} /> تست لینک پشتیبانی
          </a>
          <a href={`https://t.me/${l.channelUsername}`} target="_blank" rel="noreferrer" className="text-[13px] px-3 py-1.5 rounded-lg flex items-center gap-1.5" style={{ background: "rgba(43,127,214,.1)", color: "var(--accent-2)" }}>
            <ExternalLink size={11} /> تست لینک کانال
          </a>
        </div>
      </div>
    </div>
  );
}

/* ===================== تنظیمات ===================== */

function SettingsSection({ config, setConfig, password, onPasswordChanged, onRestored, wsMode, setWsMode }) {
  const a = config.advanced || {};
  const update = (patch) => setConfig({ ...config, advanced: { ...a, ...patch } });
  const vis = [
    { key: "showBrandStrip", label: "نوار برند بالای صفحه", desc: "لوگو و نام برند" },
    { key: "showReferralCard", label: "کارت رفرال", desc: "معرفی به دوستان در داشبورد" },
    { key: "showFaqSection", label: "بخش سوالات متداول", desc: "آکاردئون سوالات در پایین صفحه" },
    { key: "showNotificationPopup", label: "پاپ‌آپ راهنما", desc: "تنظیمات کامل در بخش «پاپ‌آپ راهنما»" },
    { key: "allowThemeToggle", label: "دکمه تغییر تم", desc: "اجازه‌ی سوییچ بین حالت تیره و روشن" },
    { key: "allowLanguageToggle", label: "دکمه تغییر زبان", desc: "اجازه‌ی انتخاب زبان توسط مشتری" },
  ];

  return (
    <div className="fx-anim">
      <SectionHead title="تنظیمات پیشرفته" desc="کنترل کامل روی ظاهر، رفتار و جزئیات صفحه‌ی اشتراک." />

      {/* حالت سوییچ فضای کاری — سلیقه‌ای، فقط روی همین مرورگر */}
      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2">
          <LayoutGrid size={15} style={{ color: "var(--accent-2)" }} /> نمایش فضاهای کاری
        </div>
        <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
          چطور بین صفحه اشتراک، حسابداری و ربات جابه‌جا شوید. فقط روی همین مرورگر ذخیره می‌شود.
        </p>

        <div className="fx-g3 grid grid-cols-3 gap-3">
          {Object.entries(WS_MODES).map(([k, m]) => {
            const on = wsMode === k;
            return (
              <button key={k} onClick={() => setWsMode(k)}
                className="p-3.5 rounded-2xl text-right"
                style={{
                  background: on ? "var(--accent-soft)" : "var(--surface-3)",
                  border: `1px solid ${on ? "rgba(43,127,214,.45)" : "var(--border)"}`,
                  transition: "transform .28s cubic-bezier(.22,1,.36,1), box-shadow .28s, background .2s, border-color .2s",
                  transform: on ? "translateY(-2px)" : "none",
                  boxShadow: on
                    ? "0 1px 0 rgba(255,255,255,.1) inset, 0 14px 30px -14px rgba(43,127,214,.55)"
                    : "0 1px 0 rgba(255,255,255,.04) inset",
                }}>
                <WsModePreview mode={k} active={on} />
                <div className="flex items-center gap-1.5 mt-3">
                  {on && <Check size={12} style={{ color: "var(--accent-2)", flexShrink: 0 }} />}
                  <span className="text-[13px] font-bold"
                    style={{ color: on ? "var(--text)" : "var(--dim)" }}>{m.label}</span>
                </div>
                <div className="text-[12px] mt-1.5 leading-relaxed" style={{ color: "var(--muted)" }}>
                  {m.desc}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-4 flex items-center gap-2"><Type size={15} style={{ color: "var(--accent-2)" }} /> هویت برند</div>
        <div className="fx-g3 grid grid-cols-2 gap-4">
          <Field label="نام برند"><input className="fx-input" value={a.brandName || ""} onChange={(e) => update({ brandName: e.target.value })} placeholder="NEXORA" /></Field>
          <Field label="عنوان صفحه (تب مرورگر)"><input className="fx-input" value={a.pageTitle || ""} onChange={(e) => update({ pageTitle: e.target.value })} /></Field>
        </div>
      </div>

      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-4 flex items-center gap-2"><Palette size={15} style={{ color: "var(--accent-2)" }} /> رنگ‌بندی</div>
        <div className="fx-g3 grid grid-cols-2 gap-4">
          <Field label="رنگ اصلی برند">
            <div className="flex items-center gap-2">
              <input type="color" value={a.accentColor || "#2B7FD6"} onChange={(e) => update({ accentColor: e.target.value })}
                className="w-11 h-11 rounded-xl cursor-pointer shrink-0" style={{ background: "transparent", border: "1px solid var(--border-2)" }} />
              <input className="fx-input" dir="ltr" value={a.accentColor || ""} onChange={(e) => update({ accentColor: e.target.value })} />
            </div>
          </Field>
          <Field label="رنگ ثانویه (گرادینت)">
            <div className="flex items-center gap-2">
              <input type="color" value={a.accentColor2 || "#5AA9E6"} onChange={(e) => update({ accentColor2: e.target.value })}
                className="w-11 h-11 rounded-xl cursor-pointer shrink-0" style={{ background: "transparent", border: "1px solid var(--border-2)" }} />
              <input className="fx-input" dir="ltr" value={a.accentColor2 || ""} onChange={(e) => update({ accentColor2: e.target.value })} />
            </div>
          </Field>
        </div>
        <div className="mt-2 rounded-xl p-3 text-center" style={{ background: `linear-gradient(135deg, ${a.accentColor || "#2B7FD6"}, ${a.accentColor2 || "#5AA9E6"})` }}>
          <span className="text-[13px] font-bold" style={{ color: "#06090F" }}>پیش‌نمایش گرادینت برند</span>
        </div>
      </div>

      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-4 flex items-center gap-2"><Globe size={15} style={{ color: "var(--accent-2)" }} /> پیش‌فرض‌های صفحه</div>
        <div className="fx-g3 grid grid-cols-2 gap-4">
          <Field label="زبان پیش‌فرض">
            <select className="fx-input" value={a.defaultLanguage || "fa"} onChange={(e) => update({ defaultLanguage: e.target.value })}>
              {LANG_TABS.map((l) => <option key={l.key} value={l.key}>{l.label}</option>)}
            </select>
          </Field>
          <Field label="تم پیش‌فرض">
            <select className="fx-input" value={a.defaultTheme || "dark"} onChange={(e) => update({ defaultTheme: e.target.value })}>
              <option value="dark">تیره</option><option value="light">روشن</option>
            </select>
          </Field>
        </div>
        <Field label="تاخیر نمایش پاپ‌آپ راهنما">
          <NumberStepper value={a.notificationDelaySeconds ?? 10} onChange={(v) => update({ notificationDelaySeconds: v })} min={0} max={60} unit="ثانیه" />
        </Field>
      </div>

      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2"><Eye size={15} style={{ color: "var(--accent-2)" }} /> نمایش بخش‌ها</div>
        <p className="text-[13px] mb-4" style={{ color: "var(--muted)" }}>هر بخشی را که نمی‌خواهید در صفحه‌ی مشتری دیده شود، خاموش کنید.</p>
        <div className="flex flex-col">
          {vis.map((v, i) => (
            <div key={v.key} className="flex items-center justify-between gap-3 py-3" style={{ borderBottom: i < vis.length - 1 ? "1px solid var(--border)" : "none" }}>
              <div className="min-w-0">
                <div className="text-[14px] text-white">{v.label}</div>
                <div className="text-[12px] mt-0.5" style={{ color: "var(--muted)" }}>{v.desc}</div>
              </div>
              <Toggle checked={a[v.key] !== false} onChange={() => update({ [v.key]: !(a[v.key] !== false) })} label={v.label} />
            </div>
          ))}
        </div>
      </div>

      <BackupCard password={password} onRestored={onRestored} />

      <ChangePasswordCard password={password} onPasswordChanged={onPasswordChanged} />

      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2"><ShieldCheck size={15} style={{ color: "var(--accent-2)" }} /> امنیت و حریم خصوصی</div>
        <p className="text-[13px] mb-4" style={{ color: "var(--muted)" }}>کنترل چیزی که مشتری می‌تواند ببیند یا کپی کند.</p>
        <div className="flex items-center justify-between gap-3 py-3">
          <div className="min-w-0">
            <div className="text-[14px] text-white">مخفی‌کردن لیست کانفیگ‌ها</div>
            <div className="text-[12px] mt-0.5 leading-relaxed" style={{ color: "var(--muted)" }}>
              دکمه‌ی «کپی کانفیگ» حذف می‌شود تا مشتری نتواند کانفیگ خام را کپی و با دیگران به اشتراک بگذارد. لینک اشتراک همچنان کار می‌کند.
            </div>
          </div>
          <Toggle checked={a.hideConfigsList === true} onChange={() => update({ hideConfigsList: !a.hideConfigsList })} label="مخفی‌کردن کانفیگ‌ها" />
        </div>
      </div>

      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-4 flex items-center gap-2"><Sliders size={15} style={{ color: "var(--accent-2)" }} /> سفارشی‌سازی پیشرفته</div>
        <Field label="متن پاورقی سفارشی" hint="اگر خالی بگذارید، چیزی نمایش داده نمی‌شود.">
          <input className="fx-input" value={a.customFooterText || ""} onChange={(e) => update({ customFooterText: e.target.value })} placeholder="پشتیبانی ۲۴ ساعته" />
        </Field>
        <Field label="CSS سفارشی" hint="برای کاربران حرفه‌ای — مستقیم به صفحه‌ی اشتراک تزریق می‌شود.">
          <textarea className="fx-input" dir="ltr" rows={4} value={a.customCss || ""} onChange={(e) => update({ customCss: e.target.value })}
            placeholder=".my-class { color: red; }" style={{ fontFamily: "var(--mono)", fontSize: 11.5 }} />
        </Field>
      </div>

      <InfoBox tone="warn">تنظیمات این بخش مستقیم روی ظاهر صفحه‌ی همه‌ی مشتری‌ها اثر می‌گذارد. بعد از تغییر، حتماً یک‌بار خودتان صفحه‌ی اشتراک را باز کنید.</InfoBox>
    </div>
  );
}

/* ===================== مدیریت واسطه‌ها (White-Label) ===================== */

function ResellersSection({ config, setConfig, requestDelete, password }) {
  const resellers = config.resellers || [];
  const [expanded, setExpanded] = useState(null);
  const [tplOptions, setTplOptions] = useState([]);
  const [palOptions, setPalOptions] = useState([]);

  // ساختارها و پالت‌ها برای انتخاب قالب اختصاصی هر واسطه
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/admin/themes`, { headers: { "X-Admin-Password": password } });
        if (res.ok) {
          const d = await res.json();
          setTplOptions(d.templates || []);
          setPalOptions([...(d.palettes || []), ...(d.customPalettes || [])]);
        }
      } catch { /* بی‌صدا */ }
    })();
  }, [password]);

  const update = (i, patch) => {
    const l = [...resellers]; l[i] = { ...l[i], ...patch };
    setConfig({ ...config, resellers: l });
  };
  const updateOverride = (i, path, value) => {
    const l = [...resellers];
    const ov = { ...(l[i].overrides || {}) };
    ov[path[0]] = { ...(ov[path[0]] || {}), [path[1]]: value };
    l[i] = { ...l[i], overrides: ov };
    setConfig({ ...config, resellers: l });
  };
  const add = () => {
    const id = `reseller-${Date.now()}`;
    setConfig({
      ...config,
      resellers: [...resellers, {
        id, name: "واسطه جدید", enabled: true, emailPrefix: "", domains: [],
        overrides: {
          links: { supportUsername: "", channelUsername: "" },
          advanced: { brandName: "", pageTitle: "", accentColor: "#2B7FD6", accentColor2: "#5AA9E6" },
        },
      }],
    });
    setExpanded(resellers.length);
  };

  return (
    <div className="fx-anim">
      <SectionHead
        title="واسطه‌ها (فروش با برند اختصاصی)"
        desc="برای هر واسطه، برند و لینک‌های اختصاصی تعریف کنید — روی همین سرور، بدون نیاز به سرور یا پنل جدید."
      />

      <div className="mb-4">
        <InfoBox>
          <b>چطور کار می‌کند؟</b> صفحه‌ی اشتراک تشخیص می‌دهد مشتری متعلق به کدام واسطه است و برند همان واسطه را نمایش می‌دهد.
          هر چیزی که برای واسطه تعریف نکنید (مثل اپ‌های دانلود، سوالات متداول، بنرها) خودکار از تنظیمات اصلی شما به ارث می‌رسد.
          <br /><br />
          <b>دو روش تشخیص:</b>
          <br />
          ۱. <b>پیشوند ایمیل</b> — کافی است در پنل 3x-ui، ایمیل مشتریان آن واسطه را با پیشوند بسازید (مثلاً <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>macan_ali@nexora</span>)
          <br />
          ۲. <b>دامنه اختصاصی</b> — واسطه یک دامنه می‌خرد و به IP همین سرور اشاره می‌دهد (کاملاً white-label)
        </InfoBox>
      </div>

      <div className="flex flex-col gap-3">
        {resellers.length === 0 && <EmptyState icon={Users} text="هنوز واسطه‌ای اضافه نشده"
          hint="واسطه یعنی کسی که با برند خودش می‌فروشد و شما فقط صورتحسابش را می‌گیرید." />}

        {resellers.map((r, i) => {
          const isOpen = expanded === i;
          const ov = r.overrides || {};
          const advOv = ov.advanced || {};
          const linksOv = ov.links || {};
          return (
            <div key={r.id || i} className={`fx-card ${r.enabled === false ? "" : ""}`} style={{ opacity: r.enabled === false ? 0.6 : 1 }}>
              {/* سربرگ */}
              <div className="flex items-center justify-between gap-2 p-4">
                <button onClick={() => setExpanded(isOpen ? null : i)} className="flex items-center gap-3 min-w-0 flex-1 text-right">
                  <div className="fx-ico" style={{ background: `linear-gradient(135deg, ${advOv.accentColor || "#2B7FD6"}, ${advOv.accentColor2 || "#5AA9E6"})` }}>
                    <span className="font-bold text-[16px]" style={{ color: "#06090F" }}>
                      {(advOv.brandName || r.name || "?").trim().charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div className="min-w-0">
                    <div className="text-[14px] font-semibold text-white truncate">{r.name || "بدون نام"}</div>
                    <div className="text-[12px] mt-0.5 truncate" style={{ color: "var(--muted)" }}>
                      {r.emailPrefix ? `پیشوند: ${r.emailPrefix}_` : ""}
                      {r.emailPrefix && r.domains?.length ? " · " : ""}
                      {r.domains?.length ? r.domains.join(", ") : ""}
                      {!r.emailPrefix && !r.domains?.length ? "هنوز تنظیم نشده" : ""}
                    </div>
                  </div>
                </button>
                <div className="flex items-center gap-2 shrink-0">
                  <Toggle checked={r.enabled !== false} onChange={() => update(i, { enabled: !(r.enabled !== false) })} label="فعال" />
                  <button onClick={() => requestDelete({ type: "reseller", idx: i, name: r.name })} className="fx-ico-btn"><Trash2 size={15} /></button>
                </div>
              </div>

              {/* بدنه */}
              {isOpen && (
                <div className="px-4 pb-4 fx-fade" style={{ borderTop: "1px solid var(--border)" }}>
                  <div className="pt-4">
                    <Field label="نام واسطه (فقط برای خودتان، به مشتری نمایش داده نمی‌شود)">
                      <input className="fx-input" value={r.name} onChange={(e) => update(i, { name: e.target.value })} placeholder="مثلاً: ماکان" />
                    </Field>

                    <div className="text-[13px] font-semibold text-white mt-4 mb-2.5 flex items-center gap-2">
                      <Search size={13} style={{ color: "var(--accent-2)" }} /> روش تشخیص مشتریان این واسطه
                    </div>

                    <div className="fx-g3 grid grid-cols-2 gap-3">
                      <Field label="پیشوند ایمیل" hint={r.emailPrefix ? `ایمیل مشتریان باید این‌طور باشد: ${r.emailPrefix}_نام@دامنه` : "مثلاً: macan"}>
                        <input className="fx-input" dir="ltr" value={r.emailPrefix || ""} onChange={(e) => update(i, { emailPrefix: e.target.value.trim() })} placeholder="macan" />
                      </Field>
                      <Field label="دامنه‌های اختصاصی" hint="با کاما جدا کنید. باید به IP همین سرور اشاره کنند.">
                        <input className="fx-input" dir="ltr" value={(r.domains || []).join(", ")}
                          onChange={(e) => update(i, { domains: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
                          placeholder="macanvpn.ir" />
                      </Field>
                    </div>

                    <div className="text-[13px] font-semibold text-white mt-4 mb-2.5 flex items-center gap-2">
                      <Palette size={13} style={{ color: "var(--accent-2)" }} /> برند اختصاصی واسطه
                    </div>

                    <div className="fx-g3 grid grid-cols-2 gap-3">
                      <Field label="نام برند"><input className="fx-input" value={advOv.brandName || ""} onChange={(e) => updateOverride(i, ["advanced", "brandName"], e.target.value)} placeholder="MACAN" /></Field>
                      <Field label="عنوان صفحه"><input className="fx-input" value={advOv.pageTitle || ""} onChange={(e) => updateOverride(i, ["advanced", "pageTitle"], e.target.value)} placeholder="ماکان | اشتراک" /></Field>
                    </div>

                    <div className="fx-g3 grid grid-cols-2 gap-3">
                      <Field label="یوزرنیم پشتیبانی واسطه" hint="بدون @">
                        <input className="fx-input" dir="ltr" value={linksOv.supportUsername || ""} onChange={(e) => updateOverride(i, ["links", "supportUsername"], e.target.value)} placeholder="macan_support" />
                      </Field>
                      <Field label="یوزرنیم کانال واسطه" hint="بدون @">
                        <input className="fx-input" dir="ltr" value={linksOv.channelUsername || ""} onChange={(e) => updateOverride(i, ["links", "channelUsername"], e.target.value)} placeholder="macanvpn" />
                      </Field>
                    </div>

                    <div className="fx-g3 grid grid-cols-2 gap-3">
                      <Field label="رنگ اصلی">
                        <div className="flex items-center gap-2">
                          <input type="color" value={advOv.accentColor || "#2B7FD6"} onChange={(e) => updateOverride(i, ["advanced", "accentColor"], e.target.value)}
                            className="w-11 h-11 rounded-xl cursor-pointer shrink-0" style={{ background: "transparent", border: "1px solid var(--border-2)" }} />
                          <input className="fx-input" dir="ltr" value={advOv.accentColor || ""} onChange={(e) => updateOverride(i, ["advanced", "accentColor"], e.target.value)} />
                        </div>
                      </Field>
                      <Field label="رنگ ثانویه">
                        <div className="flex items-center gap-2">
                          <input type="color" value={advOv.accentColor2 || "#5AA9E6"} onChange={(e) => updateOverride(i, ["advanced", "accentColor2"], e.target.value)}
                            className="w-11 h-11 rounded-xl cursor-pointer shrink-0" style={{ background: "transparent", border: "1px solid var(--border-2)" }} />
                          <input className="fx-input" dir="ltr" value={advOv.accentColor2 || ""} onChange={(e) => updateOverride(i, ["advanced", "accentColor2"], e.target.value)} />
                        </div>
                      </Field>
                    </div>

                    <Field label="متن پاورقی اختصاصی (اختیاری)">
                      <input className="fx-input" value={advOv.customFooterText || ""} onChange={(e) => updateOverride(i, ["advanced", "customFooterText"], e.target.value)} placeholder="پشتیبانی ۲۴ ساعته ماکان" />
                    </Field>

                    <div className="text-[13px] font-semibold text-white mt-4 mb-2.5 flex items-center gap-2">
                      <Layers size={13} style={{ color: "var(--accent-2)" }} /> قالب اختصاصی
                    </div>
                    <div className="fx-g3 grid grid-cols-2 gap-3">
                      <Field label="ساختار" hint="خالی = ساختار اصلی شما">
                        <select className="fx-input" value={r.overrides?.template || ""}
                          onChange={(e) => {
                            const l = [...resellers];
                            const ov = { ...(l[i].overrides || {}) };
                            if (e.target.value) ov.template = e.target.value; else delete ov.template;
                            l[i] = { ...l[i], overrides: ov };
                            setConfig({ ...config, resellers: l });
                          }}>
                          <option value="">— همان ساختار اصلی —</option>
                          {tplOptions.map((t) => <option key={t.id} value={t.id}>{t.name} · {t.fa}</option>)}
                        </select>
                      </Field>

                      <Field label="طیف رنگی" hint="خالی = پالت اصلی شما">
                        <select className="fx-input" value={r.overrides?.palette || ""}
                          onChange={(e) => {
                            const l = [...resellers];
                            const ov = { ...(l[i].overrides || {}) };
                            if (e.target.value) ov.palette = e.target.value; else delete ov.palette;
                            l[i] = { ...l[i], overrides: ov };
                            setConfig({ ...config, resellers: l });
                          }}>
                          <option value="">— همان پالت اصلی —</option>
                          {palOptions.map((p) => <option key={p.id} value={p.id}>{p.name} · {p.fa}</option>)}
                        </select>
                      </Field>
                    </div>

                    {(r.overrides?.template || r.overrides?.palette) && (() => {
                      const pv = palOptions.find((p) => p.id === (r.overrides?.palette))?.vars;
                      const tid = r.overrides?.template || config.template || "classic";
                      return (
                        <div className="flex items-center gap-3 rounded-xl p-3 mt-1"
                          style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
                          <div style={{ width: 96, flexShrink: 0 }}>
                            <TemplateThumb id={tid} vars={pv || {}} active />
                          </div>
                          <div className="text-[13px] leading-relaxed" style={{ color: "var(--muted)" }}>
                            ترکیب این واسطه:{" "}
                            <b style={{ color: "var(--text)" }}>
                              {tplOptions.find((t) => t.id === tid)?.name || tid}
                            </b>
                            {" × "}
                            <b style={{ color: pv?.accent2 || "var(--accent-2)" }}>
                              {palOptions.find((p) => p.id === r.overrides?.palette)?.name || "پالت اصلی"}
                            </b>
                          </div>
                        </div>
                      );
                    })()}

                    {/* تست زنده */}
                    {(r.emailPrefix || r.domains?.length > 0) && (
                      <div className="mt-3 rounded-xl p-3" style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
                        <div className="text-[13px] mb-2" style={{ color: "var(--muted)" }}>تست تشخیص این واسطه:</div>
                        <div className="flex flex-wrap gap-2">
                          {r.emailPrefix && (
                            <a href={`${API_URL}/api/public/config?email=${r.emailPrefix}_test@nexora`} target="_blank" rel="noreferrer"
                              className="text-[12px] px-2.5 py-1.5 rounded-lg flex items-center gap-1.5" style={{ background: "rgba(43,127,214,.1)", color: "var(--accent-2)" }}>
                              <ExternalLink size={10} /> تست با ایمیل
                            </a>
                          )}
                          {r.domains?.[0] && (
                            <a href={`${API_URL}/api/public/config?host=${r.domains[0]}`} target="_blank" rel="noreferrer"
                              className="text-[12px] px-2.5 py-1.5 rounded-lg flex items-center gap-1.5" style={{ background: "rgba(43,127,214,.1)", color: "var(--accent-2)" }}>
                              <ExternalLink size={10} /> تست با دامنه
                            </a>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}

        <button onClick={add} className="fx-btn-dash flex items-center justify-center gap-2 py-3.5 text-[14px]">
          <UserPlus size={15} /> افزودن واسطه جدید
        </button>
      </div>

      <div className="mt-4">
        <InfoBox tone="warn">
          <b>نکته‌ی مهم امنیتی:</b> لیست واسطه‌ها هرگز در پاسخ عمومی API فرستاده نمی‌شود — مشتری هیچ راهی برای دیدن این‌که چند واسطه دارید یا مشخصاتشان چیست ندارد.
        </InfoBox>
      </div>
    </div>
  );
}

/* ===================== پشتیبان‌گیری و بازیابی ===================== */

function BackupCard({ password, onRestored }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const exportConfig = async () => {
    setBusy(true); setMsg(null);
    try {
      const res = await fetch(`${API_URL}/api/admin/export`, { headers: { "X-Admin-Password": password } });
      if (!res.ok) throw new Error();
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `nexora-backup-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setMsg({ type: "ok", text: "فایل پشتیبان دانلود شد" });
    } catch {
      setMsg({ type: "error", text: "دریافت پشتیبان ناموفق بود" });
    } finally { setBusy(false); }
  };

  const importConfig = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!confirm("تنظیمات فعلی با محتوای این فایل جایگزین می‌شود. مطمئن هستید؟")) {
      e.target.value = ""; return;
    }
    setBusy(true); setMsg(null);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      const res = await fetch(`${API_URL}/api/admin/import`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify(parsed),
      });
      const data = await res.json();
      if (res.ok) {
        setMsg({ type: "ok", text: "تنظیمات بازیابی شد" });
        onRestored();
      } else {
        setMsg({ type: "error", text: data.detail || "بازیابی ناموفق بود" });
      }
    } catch {
      setMsg({ type: "error", text: "فایل معتبر نیست" });
    } finally { setBusy(false); e.target.value = ""; }
  };

  return (
    <div className="fx-card p-5 mb-4">
      <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2">
        <Download size={15} style={{ color: "var(--accent-2)" }} /> پشتیبان‌گیری و بازیابی
      </div>
      <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
        قبل از هر تغییر بزرگ، یک نسخه پشتیبان بگیرید. هنگام بازیابی، از نسخه‌ی فعلی خودکار یک کپی روی سرور نگه داشته می‌شود.
      </p>

      {msg && (
        <div className="rounded-xl p-3 mb-3 flex items-center gap-2 text-[13px]"
          style={{
            background: msg.type === "error" ? "rgba(248,113,113,.1)" : "rgba(52,211,153,.1)",
            border: `1px solid ${msg.type === "error" ? "rgba(248,113,113,.3)" : "rgba(52,211,153,.3)"}`,
            color: msg.type === "error" ? "var(--danger)" : "var(--ok)",
          }}>
          {msg.type === "error" ? <AlertTriangle size={14} /> : <CheckCircle2 size={14} />} {msg.text}
        </div>
      )}

      <div className="fx-g3 grid grid-cols-2 gap-3">
        <button onClick={exportConfig} disabled={busy} className="fx-btn-g flex items-center justify-center gap-2 py-3 text-[13px]">
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />} دریافت پشتیبان
        </button>
        <label className="fx-btn-g flex items-center justify-center gap-2 py-3 text-[13px] cursor-pointer">
          <Upload size={14} /> بازیابی از فایل
          <input type="file" accept="application/json" onChange={importConfig} className="hidden" disabled={busy} />
        </label>
      </div>
    </div>
  );
}

/* ===================== تغییر رمز عبور ===================== */

function ChangePasswordCard({ password, onPasswordChanged }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const strength = (() => {
    if (!next) return { level: 0, label: "", color: "var(--muted)" };
    let s = 0;
    if (next.length >= 8) s++;
    if (next.length >= 12) s++;
    if (/[A-Z]/.test(next) && /[a-z]/.test(next)) s++;
    if (/\d/.test(next)) s++;
    if (/[^A-Za-z0-9]/.test(next)) s++;
    const map = [
      { label: "خیلی ضعیف", color: "var(--danger)" },
      { label: "ضعیف", color: "var(--danger)" },
      { label: "متوسط", color: "var(--warn)" },
      { label: "خوب", color: "#84CC16" },
      { label: "قوی", color: "var(--ok)" },
      { label: "خیلی قوی", color: "var(--ok)" },
    ];
    return { level: s, ...map[s] };
  })();

  const submit = async () => {
    setMsg(null);
    if (next !== confirm) { setMsg({ type: "error", text: "رمز جدید و تکرار آن یکسان نیستند" }); return; }
    if (next.length < 8) { setMsg({ type: "error", text: "رمز جدید باید حداقل ۸ کاراکتر باشد" }); return; }

    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/change-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ currentPassword: current, newPassword: next }),
      });
      const data = await res.json();
      if (res.ok) {
        setMsg({ type: "ok", text: "رمز عبور با موفقیت تغییر کرد" });
        setCurrent(""); setNext(""); setConfirm("");
        onPasswordChanged(next);
      } else {
        setMsg({ type: "error", text: data.detail || "تغییر رمز ناموفق بود" });
      }
    } catch {
      setMsg({ type: "error", text: "اتصال به سرور برقرار نشد" });
    } finally { setBusy(false); }
  };

  return (
    <div className="fx-card p-5 mb-4">
      <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2">
        <Key size={15} style={{ color: "var(--accent-2)" }} /> تغییر رمز عبور
      </div>
      <p className="text-[13px] mb-4" style={{ color: "var(--muted)" }}>
        رمز جدید بلافاصله فعال می‌شود و در فایل امن روی سرور ذخیره می‌گردد.
      </p>

      <Field label="رمز عبور فعلی">
        <input className="fx-input" type={show ? "text" : "password"} value={current}
          onChange={(e) => setCurrent(e.target.value)} dir="ltr"
          style={{ fontFamily: "var(--mono)" }} />
      </Field>

      <Field label="رمز عبور جدید" hint="حداقل ۸ کاراکتر — ترکیب حروف بزرگ/کوچک، عدد و علامت امن‌تر است">
        <input className="fx-input" type={show ? "text" : "password"} value={next}
          onChange={(e) => setNext(e.target.value)} dir="ltr"
          style={{ fontFamily: "var(--mono)" }} />
      </Field>

      {next && (
        <div className="mb-3 -mt-1">
          <div className="flex items-center gap-1.5 mb-1.5">
            {[0, 1, 2, 3, 4].map((i) => (
              <div key={i} className="h-1 flex-1 rounded-full transition-all"
                style={{ background: i < strength.level ? strength.color : "rgba(255,255,255,.07)" }} />
            ))}
          </div>
          <span className="text-[12px]" style={{ color: strength.color }}>قدرت رمز: {strength.label}</span>
        </div>
      )}

      <Field label="تکرار رمز جدید">
        <input className="fx-input" type={show ? "text" : "password"} value={confirm}
          onChange={(e) => setConfirm(e.target.value)} dir="ltr"
          style={{ fontFamily: "var(--mono)",
                   borderColor: confirm && next !== confirm ? "var(--danger)" : undefined }} />
      </Field>

      <label className="flex items-center gap-2 text-[13px] mb-4 cursor-pointer" style={{ color: "var(--dim)" }}>
        <input type="checkbox" checked={show} onChange={(e) => setShow(e.target.checked)}
          style={{ accentColor: "var(--accent)" }} />
        نمایش رمزها
      </label>

      {msg && (
        <div className="rounded-xl p-3 mb-3 flex items-center gap-2 text-[13px]"
          style={{
            background: msg.type === "error" ? "rgba(248,113,113,.1)" : "rgba(52,211,153,.1)",
            border: `1px solid ${msg.type === "error" ? "rgba(248,113,113,.3)" : "rgba(52,211,153,.3)"}`,
            color: msg.type === "error" ? "var(--danger)" : "var(--ok)",
          }}>
          {msg.type === "error" ? <AlertTriangle size={14} /> : <CheckCircle2 size={14} />} {msg.text}
        </div>
      )}

      <button onClick={submit} disabled={busy || !current || !next || !confirm}
        className="fx-btn w-full py-3 text-[14px] flex items-center justify-center gap-2">
        {busy ? <Loader2 size={15} className="animate-spin" /> : <Key size={15} />}
        {busy ? "در حال تغییر..." : "تغییر رمز عبور"}
      </button>
    </div>
  );
}

/* ===================== پاپ‌آپ راهنما ===================== */

function PopupSection({ config, setConfig }) {
  const p = config.popup || {};
  const update = (patch) => setConfig({ ...config, popup: { ...p, ...patch } });
  const EMOJIS = ["🔔", "💡", "⚠️", "🚀", "❓", "📱", "🎁", "⚡"];

  return (
    <div className="fx-g2 grid gap-6 fx-anim" style={{ gridTemplateColumns: "1fr 300px" }}>
      <div className="min-w-0">
        <SectionHead title="پاپ‌آپ راهنما" desc="پیامی که چند ثانیه بعد از باز شدن صفحه‌ی اشتراک به مشتری نمایش داده می‌شود." />

        <div className="fx-card p-5 mb-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="fx-ico" style={{ background: "rgba(43,127,214,.12)" }}><MessageSquare size={16} style={{ color: "var(--accent-2)" }} /></div>
              <div className="min-w-0">
                <div className="text-[14px] font-semibold text-white">نمایش پاپ‌آپ</div>
                <div className="text-[13px] mt-0.5" style={{ color: "var(--muted)" }}>اگر خاموش کنید، هیچ پاپ‌آپی نمایش داده نمی‌شود</div>
              </div>
            </div>
            <Toggle checked={p.enabled !== false} onChange={() => update({ enabled: !(p.enabled !== false) })} label="پاپ‌آپ" />
          </div>
        </div>

        <div style={{ opacity: p.enabled !== false ? 1 : 0.45, pointerEvents: p.enabled !== false ? "auto" : "none" }}>
          <div className="fx-card p-5 mb-4">
            <div className="text-[14px] font-semibold text-white mb-4">محتوای پیام</div>

            <Field label="آیکون">
              <div className="flex items-center gap-2 flex-wrap">
                {EMOJIS.map((e) => (
                  <button key={e} onClick={() => update({ icon: e })}
                    className="w-11 h-11 rounded-xl text-[21px] transition-all"
                    style={p.icon === e
                      ? { background: "var(--accent-soft)", border: "1px solid var(--accent)" }
                      : { background: "var(--surface-3)", border: "1px solid var(--border-2)" }}>
                    {e}
                  </button>
                ))}
                <input className="fx-input" style={{ width: 80, textAlign: "center", fontSize: 17 }}
                  value={p.icon || ""} onChange={(e) => update({ icon: e.target.value })} maxLength={4} />
              </div>
            </Field>

            <Field label="عنوان پیام">
              <input className="fx-input" value={p.title || ""} onChange={(e) => update({ title: e.target.value })}
                placeholder="آیا مشکلی در اتصال کانفیگ دارید؟" />
            </Field>

            <Field label="متن توضیحات">
              <textarea className="fx-input" rows={2} value={p.description || ""} onChange={(e) => update({ description: e.target.value })}
                placeholder="پیشنهاد می‌کنیم از برنامه‌ی Happ استفاده کنید..." />
            </Field>
          </div>

          <div className="fx-card p-5 mb-4">
            <div className="text-[14px] font-semibold text-white mb-4">دکمه‌ها</div>
            <div className="fx-g3 grid grid-cols-2 gap-3">
              <Field label="متن دکمه‌ی اصلی">
                <input className="fx-input" value={p.primaryButtonText || ""} onChange={(e) => update({ primaryButtonText: e.target.value })} placeholder="پشتیبانی" />
              </Field>
              <Field label="متن دکمه‌ی رد کردن">
                <input className="fx-input" value={p.dismissButtonText || ""} onChange={(e) => update({ dismissButtonText: e.target.value })} placeholder="خیر" />
              </Field>
            </div>
            <Field label="لینک دکمه‌ی اصلی" hint="اگر خالی بگذارید، خودکار به لینک پشتیبانی شما (یا واسطه) وصل می‌شود.">
              <input className="fx-input" dir="ltr" value={p.primaryButtonUrl || ""} onChange={(e) => update({ primaryButtonUrl: e.target.value })} placeholder="https://t.me/..." />
            </Field>
          </div>

          <div className="fx-card p-5">
            <div className="text-[14px] font-semibold text-white mb-4">زمان‌بندی</div>
            <div className="fx-g3 grid grid-cols-2 gap-4">
              <Field label="تاخیر تا نمایش" hint="چند ثانیه بعد از باز شدن صفحه ظاهر شود">
                <NumberStepper value={p.delaySeconds ?? 10} onChange={(v) => update({ delaySeconds: v })} min={0} max={60} unit="ثانیه" />
              </Field>
              <Field label="بسته شدن خودکار" hint="بعد از چند ثانیه خودش بسته شود">
                <NumberStepper value={p.autoCloseSeconds ?? 15} onChange={(v) => update({ autoCloseSeconds: v })} min={3} max={60} unit="ثانیه" />
              </Field>
            </div>
          </div>
        </div>
      </div>

      {/* پیش‌نمایش زنده پاپ‌آپ */}
      <div className="fx-hide-m">
        <div className="sticky top-24">
          <div className="flex items-center gap-1.5 text-[13px] mb-3" style={{ color: "var(--muted)" }}>
            <Eye size={13} /> پیش‌نمایش
          </div>
          <div className="rounded-2xl p-5" style={{ background: "var(--surface-3)", border: "1px solid var(--border-2)" }}>
            <div className="rounded-2xl p-5 text-center" style={{ background: "var(--surface)", border: "1px solid rgba(90,169,230,.3)", boxShadow: "0 8px 32px rgba(0,0,0,.4)" }}>
              <div className="text-[32px] mb-2">{p.icon || "🔔"}</div>
              <div className="text-[14px] font-bold text-white mb-2 leading-relaxed">{p.title || "آیا مشکلی در اتصال دارید؟"}</div>
              <div className="text-[13px] leading-relaxed mb-3" style={{ color: "var(--dim)" }}>{p.description || "متن توضیحات اینجا نمایش داده می‌شود"}</div>
              <div className="h-1 rounded-full mb-4 overflow-hidden" style={{ background: "rgba(255,255,255,.06)" }}>
                <div className="h-full rounded-full" style={{ width: "65%", background: "var(--accent-2)" }} />
              </div>
              <div className="flex gap-2">
                <div className="flex-1 py-2 rounded-lg text-[13px]" style={{ border: "1px solid var(--border-2)", color: "var(--muted)" }}>
                  {p.dismissButtonText || "خیر"}
                </div>
                <div className="flex-1 py-2 rounded-lg text-[13px] font-bold" style={{ background: "linear-gradient(135deg,var(--accent),var(--accent-2))", color: "#06090F" }}>
                  {p.primaryButtonText || "پشتیبانی"}
                </div>
              </div>
            </div>
          </div>
          <p className="text-[12px] mt-3 text-center leading-relaxed" style={{ color: "var(--muted)" }}>
            بعد از {p.delaySeconds ?? 10} ثانیه ظاهر و بعد از {p.autoCloseSeconds ?? 15} ثانیه بسته می‌شود
          </p>
        </div>
      </div>
    </div>
  );
}

/* ===================== مدیریت ربات تلگرام ===================== */

function useBotApi(password) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState(null);

  const call = async (path, opts = {}) => {
    const res = await fetch(`${API_URL}${path}`, {
      ...opts,
      headers: { "Content-Type": "application/json", "X-Admin-Password": password, ...(opts.headers || {}) },
    });
    const d = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(d.detail || "خطای سرور");
    return d;
  };

  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(t); } }, [msg]);

  return { data, setData, loading, setLoading, msg, setMsg, call };
}

function BotStatusBar({ status, password, onChange, dirty, onApplied }) {
  const [busy, setBusy] = useState(null);
  const [err, setErr] = useState("");
  const [applied, setApplied] = useState(false);
  useEffect(() => { if (applied) { const t = setTimeout(() => setApplied(false), 3000); return () => clearTimeout(t); } }, [applied]);
  if (!status) return null;

  const ready = status.dbReady;
  const running = !!status.running;

  const act = async (action) => {
    setBusy(action); setErr("");
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/service/${action}`, {
        method: "POST", headers: { "X-Admin-Password": password },
      });
      const d = await res.json().catch(() => ({}));
      if (!res.ok) setErr(d.detail || "اجرای دستور ناموفق بود");
      onChange?.();
    } catch { setErr("اتصال به سرور برقرار نشد"); }
    finally { setBusy(null); }
  };

  const applyNow = async () => {
    setBusy("apply"); setErr("");
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/reload`, {
        method: "POST", headers: { "X-Admin-Password": password },
      });
      const d = await res.json().catch(() => ({}));
      if (res.ok) { setApplied(true); onApplied?.(); }
      else setErr(d.detail || "اعمال ناموفق بود");
    } catch { setErr("اتصال به سرور برقرار نشد"); }
    finally { setBusy(null); }
  };

  const tone = running ? "var(--ok)" : ready ? "var(--warn)" : "var(--muted)";

  return (
    <div className="fx-card p-4 mb-4" style={{ borderColor: `${running ? "rgba(52,211,153,.3)" : "rgba(251,191,36,.28)"}` }}>
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="fx-ico" style={{ background: running ? "rgba(52,211,153,.12)" : "rgba(251,191,36,.12)" }}>
            <Bot size={16} style={{ color: tone }} />
          </div>
          <div>
            <div className="text-[14px] font-semibold text-white flex items-center gap-2">
              {running ? "ربات در حال اجراست" : ready ? "ربات متوقف است" : "ربات راه‌اندازی نشده"}
              <Circle size={7} fill={tone} strokeWidth={0} />
            </div>
            <div className="text-[13px] mt-0.5" style={{ color: "var(--muted)" }}>
              {ready
                ? `${status.stats?.users ?? 0} کاربر · ${status.stats?.plans ?? 0} پلن فعال · ${status.stats?.pendingOrders ?? 0} رسید در انتظار`
                : (status.message || "توکن را وارد و ذخیره کنید")}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {ready && status.totalRevenue > 0 && (
            <span className="fx-pill" style={{ background: "rgba(52,211,153,.1)", color: "var(--ok)" }}>
              {Number(status.totalRevenue).toLocaleString("fa-IR")} تومان
            </span>
          )}
          {running ? (
            <>
              <button onClick={() => act("restart")} disabled={!!busy}
                className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
                {busy === "restart" ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
                ری‌استارت
              </button>
              <button onClick={() => act("stop")} disabled={!!busy}
                className="px-3.5 py-2.5 rounded-[10px] text-[13px] font-semibold flex items-center gap-1.5"
                style={{ background: "rgba(248,113,113,.12)", border: "1px solid rgba(248,113,113,.3)", color: "var(--danger)" }}>
                {busy === "stop" ? <Loader2 size={13} className="animate-spin" /> : <Power size={13} />}
                خاموش
              </button>
            </>
          ) : (
            <button onClick={() => act("start")} disabled={!!busy}
              className="fx-btn px-4 py-2.5 text-[13px] flex items-center gap-1.5">
              {busy === "start" ? <Loader2 size={13} className="animate-spin" /> : <Power size={13} />}
              روشن کردن ربات
            </button>
          )}
        </div>
      </div>

      {running && dirty && (
        <div className="mt-3 rounded-xl p-3 flex items-center justify-between gap-3 flex-wrap"
          style={{ background: "rgba(251,191,36,.08)", border: "1px solid rgba(251,191,36,.28)" }}>
          <div className="flex items-start gap-2.5">
            <RefreshCw size={15} style={{ color: "var(--warn)", flexShrink: 0, marginTop: 1 }} />
            <div>
              <div className="text-[13px] font-semibold" style={{ color: "var(--text)" }}>
                تغییرات ذخیره‌نشده دارید
              </div>
              <div className="text-[12px] mt-1 leading-relaxed" style={{ color: "var(--muted)" }}>
                قیمت‌ها و متن‌ها به‌محض ذخیره اعمال می‌شوند. اگر توکن یا اتصال پنل را
                عوض کرده‌اید، این دکمه را بزنید.
              </div>
            </div>
          </div>
          <button onClick={applyNow} disabled={!!busy}
            className="fx-btn px-4 py-2.5 text-[13px] flex items-center gap-1.5 shrink-0">
            {busy === "apply" ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
            اعمال در ربات
          </button>
        </div>
      )}

      {applied && (
        <div className="mt-3 rounded-xl p-2.5 text-[13px] flex items-center gap-2"
          style={{ background: "rgba(52,211,153,.1)", border: "1px solid rgba(52,211,153,.25)", color: "var(--ok)" }}>
          <CheckCircle2 size={13} /> اعمال شد — ربات ظرف ۳۰ ثانیه همگام می‌شود
        </div>
      )}

      {err && (
        <div className="mt-3 rounded-xl p-2.5 text-[13px] flex items-center gap-2"
          style={{ background: "rgba(248,113,113,.1)", border: "1px solid rgba(248,113,113,.25)", color: "var(--danger)" }}>
          <AlertTriangle size={13} /> {err}
        </div>
      )}
    </div>
  );
}

function Msg({ msg }) {
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

/* ===================== ربات: اتصال و تنظیمات ===================== */

function ConnectionTest({ password, tenant }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  const runTrace = async () => {
    setBusy(true);
    setResult(null);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/xui-trace`, {
        method: "POST",
        headers: { "X-Admin-Password": password },
      });
      const d = await res.json();
      setResult(d);
    } catch {
      setResult({ ok: false, steps: [
        { title: "اتصال به سرور", ok: false, detail: "برقرار نشد" }] });
    } finally { setBusy(false); }
  };

  const run = async () => {
    setBusy(true);
    setResult(null);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/test-connection`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({
          panel_url: tenant.panel_url,
          panel_user: tenant.panel_user,
          panel_pass: tenant.panel_pass,
          panel_token: tenant.panel_token,
          default_inbound: tenant.default_inbound,
        }),
      });
      const d = await res.json().catch(() => ({}));
      if (!res.ok) {
        setResult({ ok: false, steps: [{ key: "e", title: "تست انجام نشد",
                    ok: false, detail: d.detail || "خطای سرور", hint: "" }] });
      } else {
        setResult(d);
      }
    } catch {
      setResult({ ok: false, steps: [{ key: "e", title: "اتصال به سرور برقرار نشد",
                  ok: false, detail: "", hint: "پنل در حال اجراست؟" }] });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fx-card p-5 mb-4">
      <div className="flex items-start justify-between gap-3 flex-wrap mb-1">
        <div>
          <div className="text-[14px] font-semibold text-white flex items-center gap-2">
            <ShieldCheck size={15} style={{ color: "var(--accent-2)" }} /> تست اتصال
          </div>
          <p className="text-[13px] mt-1.5 leading-relaxed max-w-md" style={{ color: "var(--muted)" }}>
            یک کانفیگ آزمایشی می‌سازد و بلافاصله پاک می‌کند — تا مطمئن شوید
            ربات واقعاً می‌تواند برای مشتری کانفیگ بسازد، نه فقط وصل شود.
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          <button onClick={run} disabled={busy || !tenant.panel_url}
            className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5"
            style={!tenant.panel_url ? { opacity: 0.45, cursor: "not-allowed" } : {}}>
            {busy ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
            {busy ? "در حال بررسی..." : "اجرای تست"}
          </button>
          <button onClick={runTrace} disabled={busy || !tenant.panel_url}
            className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5"
            style={!tenant.panel_url ? { opacity: 0.45, cursor: "not-allowed" } : {}}>
            <HelpCircle size={13} /> تشخیص عمیق
          </button>
        </div>
      </div>

      {!tenant.panel_url && (
        <p className="text-[13px] mt-3" style={{ color: "var(--warn)" }}>
          ابتدا آدرس پنل را وارد و ذخیره کنید.
        </p>
      )}

      {result && (
        <div className="mt-4">
          <div className="rounded-xl p-3 mb-3 flex items-center gap-2.5 text-[14px] font-semibold"
            style={{
              background: result.ok ? "rgba(52,211,153,.1)" : "rgba(248,113,113,.1)",
              border: `1px solid ${result.ok ? "rgba(52,211,153,.3)" : "rgba(248,113,113,.3)"}`,
              color: result.ok ? "var(--ok)" : "var(--danger)",
            }}>
            {result.ok ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
            {result.ok ? "همه‌چیز آماده است — ربات می‌تواند کانفیگ بسازد"
                       : "یک مرحله ناموفق بود"}
          </div>

          {(result.steps || []).map((s, i) => (
            <div key={i} className="flex gap-3 py-2.5"
              style={{ borderBottom: i < result.steps.length - 1 ? "1px solid var(--border)" : "none" }}>
              <div className="shrink-0 mt-0.5">
                {s.ok ? <CheckCircle2 size={15} style={{ color: "var(--ok)" }} />
                      : <XCircle size={15} style={{ color: "var(--danger)" }} />}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-semibold"
                  style={{ color: s.ok ? "var(--text)" : "var(--danger)" }}>{s.title}</div>
                {s.detail && (
                  <div className="text-[13px] mt-1 leading-relaxed break-words" style={{ color: "var(--muted)" }}>
                    {s.detail}
                  </div>
                )}
                {s.hint && (
                  <div className="text-[13px] mt-1.5 leading-relaxed" style={{ color: "var(--warn)" }}>
                    {s.hint}
                  </div>
                )}
              </div>
            </div>
          ))}

          {result.inbounds?.length > 0 && (
            <div className="mt-4">
              <div className="text-[13px] mb-2" style={{ color: "var(--muted)" }}>
                inboundهای موجود — شماره‌ی مورد نظر را در تنظیمات بگذارید:
              </div>
              <div className="flex flex-wrap gap-2">
                {result.inbounds.map((ib) => (
                  <span key={ib.id} className="fx-pill"
                    style={{ background: "var(--surface-3)", color: "var(--dim)",
                             border: "1px solid var(--border-2)" }}>
                    <b style={{ fontFamily: "var(--mono)" }}>#{ib.id}</b>
                    {" "}{ib.remark || ib.protocol}
                    {ib.port ? ` · ${ib.port}` : ""}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function BotSection({ password, dirty }) {
  const [t, setT] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);
  const [showTok, setShowTok] = useState(false);
  const [authMode, setAuthMode] = useState("token");

  const load = async () => {
    try {
      const [s, st] = await Promise.all([
        fetch(`${API_URL}/api/admin/bot/settings`, { headers: { "X-Admin-Password": password } }).then(r => r.json()),
        fetch(`${API_URL}/api/admin/bot/status`, { headers: { "X-Admin-Password": password } }).then(r => r.json()),
      ]);
      setStatus(st);
      // بک‌اند ممکن است tenant را null بدهد یا فیلدهایش ناقص باشند.
      // اینجا یک شکل کامل می‌سازیم تا هیچ‌جای رابط روی null نخورد.
      // اگر ماژول ربات در دسترس نیست، حالت خطا نشان می‌دهیم
      if (!s.ready && !s.tenant) {
        setT(null);
        if (s.error) setMsg({ t: "err", m: s.error });
        return;
      }

      const raw = s.tenant || {};
      const tn = {
        name: "Nexora",
        bot_username: "", owner_tg_id: "", panel_url: "", panel_user: "",
        default_inbound: "", admin_group_id: "",
        ...raw,
        settings: (raw.settings && typeof raw.settings === "object" && !Array.isArray(raw.settings))
          ? raw.settings : {},
        topics: (raw.topics && typeof raw.topics === "object" && !Array.isArray(raw.topics))
          ? raw.topics : {},
      };
      setT(tn);
      // اگر قبلاً با یوزر/رمز تنظیم شده بود، همان حالت را نشان بده
      if (tn.panel_user && !tn.panel_token_set) setAuthMode("login");
      if (s.error) setMsg({ t: "err", m: s.error });
    } catch { setMsg({ t: "err", m: "اتصال به سرور برقرار نشد" }); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [password]);
  useEffect(() => { if (msg) { const x = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(x); } }, [msg]);

  const up = (patch) => setT({ ...t, ...patch });
  const upS = (patch) => setT({ ...t, settings: { ...(t.settings || {}), ...patch } });

  const save = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify(t),
      });
      const d = await res.json();
      if (res.ok) { setMsg({ t: "ok", m: "تنظیمات ربات ذخیره شد" }); load(); }
      else setMsg({ t: "err", m: d.detail || "ذخیره ناموفق بود" });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setSaving(false); }
  };

  if (loading) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  // اگر به هر دلیلی tenant ساخته نشد، به‌جای صفحه‌ی سفید یک پیام
  // با راه‌حل نشان می‌دهیم.
  if (!t) {
    return (
      <div className="fx-anim">
        <SectionHead title="اتصال و تنظیمات ربات" desc="" />
        <div className="fx-card p-8 text-center" style={{ borderStyle: "dashed" }}>
          <AlertTriangle size={24} style={{ color: "var(--warn)" }} className="mx-auto mb-3" />
          <div className="text-[14px] font-semibold text-white mb-2">
            تنظیمات ربات خوانده نشد
          </div>
          <p className="text-[13px] mb-5 max-w-sm mx-auto leading-relaxed" style={{ color: "var(--muted)" }}>
            {msg?.m || "ماژول ربات ممکن است نصب نشده باشد."}
          </p>
          <button onClick={() => { setLoading(true); load(); }}
            className="fx-btn px-5 py-2.5 text-[14px] inline-flex items-center gap-2">
            <RefreshCw size={14} /> تلاش دوباره
          </button>
          <div className="text-[13px] mt-5 pt-4" style={{ color: "var(--muted)", borderTop: "1px solid var(--border)" }}>
            اگر ادامه داشت، روی سرور اجرا کنید:{" "}
            <code dir="ltr" className="px-2 py-1 rounded-md"
              style={{ background: "var(--surface-3)", color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
              nexora doctor
            </code>
          </div>
        </div>
      </div>
    );
  }

  const s = (t.settings && typeof t.settings === "object" && !Array.isArray(t.settings))
    ? t.settings : {};
  const cards = Array.isArray(s.cards) ? s.cards : [];

  return (
    <div className="fx-anim">
      <SectionHead title="اتصال و تنظیمات ربات"
        desc="توکن ربات، اتصال به پنل 3x-ui، گروه مدیریت و شماره کارت‌ها."
        action={
          <button onClick={save} disabled={saving} className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} ذخیره
          </button>
        } />

      <BotStatusBar status={status} password={password} onChange={load} dirty={dirty} />
      <Msg msg={msg} />

      {/* توکن ربات */}
      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2">
          <Bot size={15} style={{ color: "var(--accent-2)" }} /> ربات تلگرام
        </div>
        <p className="text-[13px] mb-4" style={{ color: "var(--muted)" }}>
          توکن را از <span dir="ltr">@BotFather</span> بگیرید.
        </p>

        <div className="fx-g3 grid grid-cols-2 gap-3">
          <Field label="نام کسب‌وکار">
            <input className="fx-input" value={t.name || ""} onChange={(e) => up({ name: e.target.value })} placeholder="Nexora" />
          </Field>
          <Field label="یوزرنیم ربات" hint="بدون @">
            <input className="fx-input" dir="ltr" value={t.bot_username || ""} onChange={(e) => up({ bot_username: e.target.value })} placeholder="NexoraVpnBot" />
          </Field>
        </div>

        <Field label="توکن ربات" hint={t.bot_token_set ? "توکن ذخیره شده — برای تغییر، مقدار جدید وارد کنید" : "الزامی"}>
          <div className="flex gap-2">
            <input className="fx-input" dir="ltr" type={showTok ? "text" : "password"}
              value={t.bot_token || ""} onChange={(e) => up({ bot_token: e.target.value })}
              placeholder="123456:AAE..." style={{ fontFamily: "var(--mono)" }} />
            <button onClick={() => setShowTok(!showTok)} className="fx-btn-g px-3 shrink-0">
              <Eye size={14} />
            </button>
          </div>
        </Field>

        <Field label="آیدی عددی ادمین اصلی" hint="از @userinfobot بگیرید">
          <input className="fx-input" dir="ltr" value={t.owner_tg_id || ""}
            onChange={(e) => up({ owner_tg_id: e.target.value })} placeholder="123456789"
            style={{ fontFamily: "var(--mono)" }} />
        </Field>
      </div>

      {/* اتصال به پنل */}
      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2">
          <Server size={15} style={{ color: "var(--accent-2)" }} /> اتصال به پنل 3x-ui
        </div>
        <p className="text-[13px] mb-4" style={{ color: "var(--muted)" }}>
          ربات از این اتصال برای ساخت خودکار کانفیگ استفاده می‌کند.
        </p>

        <Field label="آدرس پنل" hint="با پورت و مسیر، مثلاً https://panel.site.com:2053/abc">
          <input className="fx-input" dir="ltr" value={t.panel_url || ""}
            onChange={(e) => up({ panel_url: e.target.value })} placeholder="https://panel.example.com:2053/path" />
        </Field>

        <div className="flex gap-2 mb-4">
          {[["token", "توکن API", ShieldCheck, "امن‌تر"], ["login", "نام کاربری و رمز", Key, ""]].map(([k, l, Ico, tag]) => (
            <button key={k} onClick={() => setAuthMode(k)}
              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-[13px] font-semibold transition-all"
              style={authMode === k
                ? { background: "linear-gradient(135deg,var(--accent),var(--accent-2))", color: "#06090F" }
                : { background: "var(--surface-3)", border: "1px solid var(--border-2)", color: "var(--muted)" }}>
              <Ico size={14} /> {l}
              {tag && authMode === k && (
                <span className="text-[11px] px-1.5 py-0.5 rounded-full"
                  style={{ background: "rgba(0,0,0,.18)" }}>{tag}</span>
              )}
            </button>
          ))}
        </div>

        {authMode === "token" ? (
          <>
            <Field label="توکن API پنل" hint={t.panel_token_set ? "ذخیره شده — برای تغییر مقدار جدید وارد کنید" : "از پنل: Settings → Security → API Token"}>
              <input className="fx-input" dir="ltr" type="password" value={t.panel_token || ""}
                onChange={(e) => up({ panel_token: e.target.value })}
                placeholder="توکن را از پنل 3x-ui کپی کنید"
                style={{ fontFamily: "var(--mono)" }} />
            </Field>
            <InfoBox>
              <b>چرا توکن بهتر است؟</b> رمز پنل دسترسی کامل می‌دهد و اگر لو برود
              باید کل رمز را عوض کنید. توکن را می‌توانید هر لحظه از پنل باطل کنید
              بدون این‌که چیز دیگری تغییر کند.
            </InfoBox>
          </>
        ) : (
          <div className="fx-g3 grid grid-cols-2 gap-3">
            <Field label="نام کاربری پنل">
              <input className="fx-input" dir="ltr" value={t.panel_user || ""} onChange={(e) => up({ panel_user: e.target.value })} />
            </Field>
            <Field label="رمز پنل" hint={t.panel_pass_set ? "ذخیره شده" : ""}>
              <input className="fx-input" dir="ltr" type="password" value={t.panel_pass || ""}
                onChange={(e) => up({ panel_pass: e.target.value })} />
            </Field>
          </div>
        )}

        <Field label="شناسه inbound پیش‌فرض" hint="عدد inbound که کانفیگ‌ها در آن ساخته شوند">
          <input className="fx-input" dir="ltr" value={t.default_inbound || ""}
            onChange={(e) => up({ default_inbound: e.target.value })} placeholder="1"
            style={{ fontFamily: "var(--mono)" }} />
        </Field>
      </div>

      <ConnectionTest password={password} tenant={t} />

      {/* گروه مدیریت */}
      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2">
          <Users size={15} style={{ color: "var(--accent-2)" }} /> گروه مدیریت
        </div>
        <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
          یک سوپرگروه خصوصی بسازید، تاپیک‌ها را فعال کنید، ربات را ادمین کنید و آیدی گروه را اینجا بگذارید.
          ربات خودش تاپیک‌های لازم را می‌سازد.
        </p>
        <Field label="آیدی گروه" hint="معمولاً با -100 شروع می‌شود">
          <input className="fx-input" dir="ltr" value={t.admin_group_id || ""}
            onChange={(e) => up({ admin_group_id: e.target.value })} placeholder="-1001234567890"
            style={{ fontFamily: "var(--mono)" }} />
        </Field>
      </div>

      {/* کارت‌های بانکی */}
      <div className="fx-card p-5 mb-4">
        <div className="flex items-center justify-between gap-3 mb-1">
          <div className="text-[14px] font-semibold text-white flex items-center gap-2">
            <CreditCard size={15} style={{ color: "var(--accent-2)" }} /> شماره کارت‌ها
          </div>
          <button onClick={() => upS({ cards: [...cards, { number: "", holder: "", bank: "", active: true }] })}
            className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
            <PlusIcon size={13} /> افزودن کارت
          </button>
        </div>
        <p className="text-[13px] mb-4" style={{ color: "var(--muted)" }}>
          اگر چند کارت فعال باشد، ربات به‌صورت چرخشی از آن‌ها استفاده می‌کند.
        </p>

        {cards.length === 0 && (
          <div className="text-center py-6 text-[13px]" style={{ color: "var(--muted)" }}>
            هنوز کارتی اضافه نشده — بدون کارت، پرداخت کار نمی‌کند
          </div>
        )}

        {cards.map((cd, i) => (
          <div key={i} className="fx-card p-4 mb-3" style={{ background: "var(--surface-3)" }}>
            <div className="flex items-center justify-between gap-2 mb-3">
              <Toggle checked={cd.active !== false}
                onChange={() => { const l = [...cards]; l[i] = { ...cd, active: !(cd.active !== false) }; upS({ cards: l }); }}
                label="فعال" />
              <button onClick={() => upS({ cards: cards.filter((_, x) => x !== i) })}
                className="fx-ico-btn" style={{ width: 28, height: 28 }}><Trash2 size={13} /></button>
            </div>
            <Field label="شماره کارت">
              <input className="fx-input" dir="ltr" value={cd.number || ""}
                onChange={(e) => { const l = [...cards]; l[i] = { ...cd, number: e.target.value }; upS({ cards: l }); }}
                placeholder="6037997512345678" style={{ fontFamily: "var(--mono)" }} />
            </Field>
            <div className="fx-g3 grid grid-cols-2 gap-3">
              <Field label="به نام">
                <input className="fx-input" value={cd.holder || ""}
                  onChange={(e) => { const l = [...cards]; l[i] = { ...cd, holder: e.target.value }; upS({ cards: l }); }}
                  placeholder="علی محمدی" />
              </Field>
              <Field label="بانک">
                <input className="fx-input" value={cd.bank || ""}
                  onChange={(e) => { const l = [...cards]; l[i] = { ...cd, bank: e.target.value }; upS({ cards: l }); }}
                  placeholder="ملی" />
              </Field>
            </div>
          </div>
        ))}
      </div>

      {/* عضویت اجباری کانال */}
      <div className="fx-card p-5 mb-4">
        <div className="flex items-center justify-between gap-3 mb-1">
          <div className="text-[14px] font-semibold text-white flex items-center gap-2">
            <Radio size={15} style={{ color: "var(--accent-2)" }} /> عضویت اجباری کانال
          </div>
          <Toggle checked={!!s.force_channel_on}
            onChange={() => upS({ force_channel_on: !s.force_channel_on })} label="فعال" />
        </div>
        <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
          اگر فعال باشد، کاربر تا در کانال عضو نشود نمی‌تواند پلن‌ها را ببیند یا تست رایگان بگیرد.
        </p>

        <div style={{ opacity: s.force_channel_on ? 1 : 0.45, pointerEvents: s.force_channel_on ? "auto" : "none" }}>
          <Field label="یوزرنیم یا لینک کانال" hint="مثلاً @yanexoravpn یا https://t.me/yanexoravpn">
            <input className="fx-input" dir="ltr" value={s.force_channel || ""}
              onChange={(e) => upS({ force_channel: e.target.value })} placeholder="@yanexoravpn" />
          </Field>

          <InfoBox tone="warn">
            <b>مهم:</b> ربات باید در کانال <b>ادمین</b> باشد، وگرنه نمی‌تواند عضویت را بررسی کند.
            اگر ربات ادمین نباشد، سیستم سخت‌گیری نمی‌کند و اجازه‌ی خرید می‌دهد —
            چون قفل‌شدن کل فروش بدتر از رد نشدن یک نفر است.
          </InfoBox>
        </div>
      </div>

      {/* راه‌اندازی */}
      <InfoBox>
        بعد از ذخیره، روی سرور این دستور را بزنید تا ربات روشن شود:
        <br />
        <code dir="ltr" className="inline-block mt-2 px-3 py-1.5 rounded-lg text-[13px]"
          style={{ background: "var(--surface-3)", color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
          nexora bot enable
        </code>
      </InfoBox>
    </div>
  );
}

/* ===================== قالب‌ها (ساختار × رنگ) ===================== */

// نمایش کوچک ساختار هر Template
function TemplateThumb({ id, vars, active }) {
  const v = vars || {};
  const A = active ? (v.accent || "#2B7FD6") : "#3A4453";
  const A2 = active ? (v.accent2 || "#5AA9E6") : "#2A3444";
  const bg = active ? (v.bg || "#06090F") : "#0A0E17";
  const card = active ? `${A}12` : "#141A25";
  const bar = (w, h = 3, c = "#2A3444") => ({ width: w, height: h, borderRadius: 2, background: c });

  return (
    <div style={{ background: bg, borderRadius: 10, padding: 9, height: 68, overflow: "hidden" }}>
      {id === "classic" && (
        <>
          <div style={{ background: card, borderRadius: 6, padding: 6, marginBottom: 5, display: "flex", alignItems: "center", gap: 7 }}>
            <div style={{ width: 20, height: 20, borderRadius: "50%", border: `2.5px solid ${A}`, borderRightColor: "transparent", flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
              <div style={{ ...bar("72%"), marginBottom: 3 }} />
              <div style={bar("46%")} />
            </div>
          </div>
          <div style={{ display: "flex", gap: 3.5 }}>
            {[0, 1, 2].map((i) => <div key={i} style={{ flex: 1, height: 9, borderRadius: 3, background: i === 0 ? A : "#1E2531" }} />)}
          </div>
        </>
      )}
      {id === "analytics" && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 3.5, marginBottom: 4 }}>
            {[0, 1, 2, 3].map((i) => (
              <div key={i} style={{ background: card, borderRadius: 4, padding: 3.5 }}>
                <div style={{ ...bar(9, 3, i < 2 ? A : A2), marginBottom: 2.5 }} />
                <div style={bar("62%", 2.5)} />
              </div>
            ))}
          </div>
          <div style={{ background: card, borderRadius: 4, padding: 4, display: "flex", alignItems: "flex-end", gap: 2, height: 20 }}>
            {[6, 11, 8, 14, 10, 6, 12].map((h, i) => (
              <div key={i} style={{ flex: 1, height: h, borderRadius: 1, background: i === 6 ? A : `${A}55` }} />
            ))}
          </div>
        </>
      )}
      {id === "wallet" && (
        <>
          <div style={{ height: 30, borderRadius: 8, marginBottom: 6, padding: 7, background: `linear-gradient(135deg,${A},${A2})`, position: "relative", overflow: "hidden" }}>
            <div style={{ position: "absolute", top: -10, left: -10, width: 34, height: 34, borderRadius: "50%", background: "rgba(255,255,255,.16)" }} />
            <div style={{ ...bar(26, 6, bg), opacity: .82, marginBottom: 4 }} />
            <div style={{ ...bar(16, 3, bg), opacity: .5 }} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-around" }}>
            {[0, 1, 2, 3].map((i) => (
              <div key={i} style={{ width: 12, height: 12, borderRadius: "50%", background: i === 0 ? A : "#1E2531" }} />
            ))}
          </div>
        </>
      )}
      {id === "console" && (
        <>
          <div style={{ background: card, borderRadius: 4, padding: 6, marginBottom: 5 }}>
            <div style={{ display: "flex", gap: 2.5, marginBottom: 5 }}>
              {["#FF5F57", "#FEBC2E", "#28C840"].map((cc, i) => (
                <div key={i} style={{ width: 4, height: 4, borderRadius: "50%", background: cc, opacity: active ? .85 : .35 }} />
              ))}
            </div>
            {[0, 1].map((i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                <div style={bar(20, 2.5)} />
                <div style={bar(12, 2.5, i === 1 ? A : "#2A3444")} />
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 1.5 }}>
            {Array.from({ length: 16 }).map((_, i) => (
              <div key={i} style={{ flex: 1, height: 7, borderRadius: 1, background: i < 9 ? A : `${A}2E` }} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

/**
 * سربرگ یک گام.
 *
 * بیرون از کامپوننت تعریف شده — اگر داخل بدنه باشد، در هر رندر
 * دوباره ساخته می‌شود و React کل زیردرختش را دور می‌ریزد. نتیجه:
 * پرش بصری و از بین رفتن انیمیشن ورود.
 */
function ThemeStep({ n, title, desc, accent, bg }) {
  return (
    <div className="flex items-center gap-3 mb-5">
      <div className="w-7 h-7 rounded-full flex items-center justify-center text-[13px] font-bold shrink-0"
        style={{
          background: accent || "var(--accent)",
          color: bg || "#06090F",
          boxShadow: `0 1px 0 rgba(255,255,255,.3) inset, 0 4px 10px -3px ${accent || "var(--accent)"}`,
        }}>{n}</div>
      <div>
        <div className="text-[14px] font-bold text-white leading-tight">{title}</div>
        {desc && <div className="text-[13px] mt-1" style={{ color: "var(--muted)" }}>{desc}</div>}
      </div>
    </div>
  );
}

function ThemesSection({ config, setConfig, password }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [msg, setMsg] = useState(null);
  const [confirmDel, setConfirmDel] = useState(null);

  const load = async () => {
    try {
      const res = await fetch(`${API_URL}/api/admin/themes`, { headers: { "X-Admin-Password": password } });
      if (res.ok) setData(await res.json());
    } catch { /* بی‌صدا */ }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [password]);
  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(t); } }, [msg]);

  if (loading) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  const templates = data?.templates || [];
  const palettes = [...(data?.palettes || []), ...(data?.customPalettes || [])];
  const curTpl = config.template || "classic";
  const curPal = config.palette || "ocean";
  const activePal = palettes.find((p) => p.id === curPal) || palettes[0];
  const V = activePal?.vars || {};

  const removePalette = async (id) => {
    setConfirmDel(null);
    try {
      const res = await fetch(`${API_URL}/api/admin/palettes/${id}`, {
        method: "DELETE", headers: { "X-Admin-Password": password },
      });
      if (res.ok) { setMsg({ t: "ok", m: "پالت حذف شد" }); load(); }
      else setMsg({ t: "err", m: "حذف ناموفق بود" });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
  };

  return (
    <div className="fx-anim">
      <SectionHead title="قالب صفحه اشتراک"
        desc={`ساختار و رنگ جدا هستند — ${templates.length} ساختار × ${palettes.length} پالت = ${templates.length * palettes.length} ترکیب`}
        action={
          <button onClick={() => setAddOpen(true)} className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-2">
            <PlusIcon size={14} /> پالت سفارشی
          </button>
        } />

      {msg && (
        <div className="rounded-xl p-3 mb-5 flex items-center gap-2 text-[13px]"
          style={{
            background: msg.t === "err" ? "rgba(248,113,113,.1)" : "rgba(52,211,153,.1)",
            border: `1px solid ${msg.t === "err" ? "rgba(248,113,113,.3)" : "rgba(52,211,153,.3)"}`,
            color: msg.t === "err" ? "var(--danger)" : "var(--ok)",
          }}>
          {msg.t === "err" ? <AlertTriangle size={14} /> : <CheckCircle2 size={14} />} {msg.m}
        </div>
      )}

      {/* گام ۱ — ساختار */}
      <ThemeStep n="۱" title="ساختار قالب" desc="سبک بصری کارت‌ها و اجزای صفحه" accent={V.accent} bg={V.bg} />
      <div className="grid gap-3 mb-8" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(190px,1fr))" }}>
        {templates.map((t) => {
          const on = curTpl === t.id;
          return (
            <button key={t.id} onClick={() => setConfig({ ...config, template: t.id })}
              className="fx-card p-4 text-right"
              style={{
                transition: "transform .28s cubic-bezier(.22,1,.36,1), box-shadow .28s ease, border-color .2s ease, background .2s ease",
                ...(on ? {
                  borderColor: `${V.accent}88`,
                  background: `${V.accent}0D`,
                  transform: "translateY(-3px)",
                  boxShadow: `0 1px 0 rgba(255,255,255,.1) inset, 0 0 0 1px ${V.accent}44, 0 18px 36px -14px ${V.accent}55`,
                } : {}),
              }}>
              <div className="mb-4"><TemplateThumb id={t.id} vars={V} active={on} /></div>
              <div className="flex items-center gap-2 mb-2">
                {on && (
                  <div style={{
                    width: 16, height: 16, borderRadius: "50%", flexShrink: 0,
                    background: V.accent, display: "flex", alignItems: "center", justifyContent: "center",
                  }}>
                    <Check size={10} style={{ color: V.bg || "#06090F" }} />
                  </div>
                )}
                <span className="text-[14px] font-bold text-white" style={{ fontFamily: "var(--mono)" }}>{t.name}</span>
                <span className="text-[12px]" style={{ color: "var(--muted)" }}>· {t.fa}</span>
              </div>
              <div className="text-[12px] mt-1 leading-relaxed" style={{ color: "var(--muted)" }}>{t.desc}</div>
            </button>
          );
        })}
      </div>

      {/* گام ۲ — پالت */}
      <ThemeStep n="۲" title="طیف رنگی" desc="رنگ‌بندی که روی ساختار انتخابی اعمال می‌شود" accent={V.accent} bg={V.bg} />
      <div className="grid gap-3 mb-8" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(120px,1fr))" }}>
        {palettes.map((p) => {
          const on = curPal === p.id;
          const pv = p.vars || {};
          return (
            <div key={p.id} className="fx-card p-3 relative"
              style={{
                transition: "transform .28s cubic-bezier(.22,1,.36,1), box-shadow .28s ease, border-color .2s ease",
                ...(on ? {
                  borderColor: `${pv.accent}99`,
                  transform: "translateY(-2px)",
                  boxShadow: `0 1px 0 rgba(255,255,255,.1) inset, 0 0 0 1px ${pv.accent}44, 0 16px 32px -14px ${pv.accent}66`,
                } : {}),
              }}>
              <button onClick={() => setConfig({ ...config, palette: p.id })} className="w-full text-right">
                <div className="rounded-xl mb-3 relative overflow-hidden" style={{
                  height: 44,
                  background: `linear-gradient(135deg,${pv.accent},${pv.accent2})`,
                  boxShadow: `0 1px 0 rgba(255,255,255,.25) inset, 0 4px 10px -3px ${pv.accent}77`,
                }}>
                  <div style={{ position: "absolute", inset: 0, background: `linear-gradient(90deg, transparent 48%, ${pv.bg}E6)` }} />
                  {on && (
                    <div style={{
                      position: "absolute", top: 7, right: 7,
                      width: 20, height: 20, borderRadius: "50%",
                      background: pv.bg, display: "flex", alignItems: "center", justifyContent: "center",
                    }}>
                      <Check size={12} style={{ color: pv.accent }} />
                    </div>
                  )}
                </div>
                <div className="text-[13px] font-bold text-white" style={{ fontFamily: "var(--mono)" }}>{p.name}</div>
                <div className="text-[11.5px] mt-0.5" style={{ color: "var(--muted)" }}>{p.fa}</div>
              </button>
              {p.builtin === false && (
                <button onClick={() => setConfirmDel(p)} className="fx-ico-btn absolute" style={{ width: 24, height: 24, top: 6, left: 6 }}>
                  <Trash2 size={11} />
                </button>
              )}
            </div>
          );
        })}
      </div>

      <InfoBox>
        ترکیب فعلی: <b>{templates.find((t) => t.id === curTpl)?.name}</b> × <b>{activePal?.name}</b>
        <br />
        بعد از انتخاب، دکمه‌ی <b>«ذخیره تغییرات»</b> را بزنید، سپس در بخش
        <b> «پیش‌نمایش زنده»</b> نتیجه را ببینید. برای هر واسطه هم می‌توانید ترکیب جداگانه تعیین کنید.
      </InfoBox>

      {addOpen && <AddPaletteModal password={password} onClose={() => setAddOpen(false)}
        onAdded={(m) => { setMsg(m); load(); setAddOpen(false); }} />}

      {confirmDel && (
        <ConfirmModal title="حذف پالت؟"
          desc={`پالت «${confirmDel.name}» حذف می‌شود. اگر جایی استفاده شده باشد، به پالت پیش‌فرض برمی‌گردد.`}
          onConfirm={() => removePalette(confirmDel.id)} onCancel={() => setConfirmDel(null)} />
      )}
    </div>
  );
}

function AddPaletteModal({ password, onClose, onAdded }) {
  const [name, setName] = useState("");
  const [fa, setFa] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [vars, setVars] = useState({
    accent: "#2B7FD6", accent2: "#5AA9E6", bg: "#06090F",
    surface: "#0D1420", surfaceAlt: "#0A0E17",
    border: "rgba(255,255,255,0.06)", text: "#E8EEF7", textMuted: "#5A6880",
  });
  const [preview, setPreview] = useState("classic");

  const setVar = (k, v) => setVars({ ...vars, [k]: v });

  const submit = async () => {
    setErr("");
    if (!name.trim()) { setErr("نام پالت را وارد کنید"); return; }
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/palettes`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ name, fa: fa || name, vars }),
      });
      const d = await res.json();
      if (res.ok) onAdded({ t: "ok", m: `پالت «${name}» اضافه شد` });
      else setErr(d.detail || "افزودن ناموفق بود");
    } catch { setErr("اتصال به سرور برقرار نشد"); }
    finally { setBusy(false); }
  };

  const COLORS = [
    ["accent", "رنگ اصلی"], ["accent2", "رنگ ثانویه"],
    ["bg", "پس‌زمینه"], ["surface", "کارت‌ها"], ["text", "متن"],
  ];

  return createPortal(
    <div className="nx-modal-wrap fx-fade"
      style={{ background: "rgba(3,6,12,.82)", backdropFilter: "blur(6px)" }} onClick={onClose}>
      <div className="max-w-2xl rounded-2xl fx-scale nx-modal" onClick={(e) => e.stopPropagation()}
        style={{ background: "var(--surface)", border: "1px solid rgba(90,169,230,.3)" }}>

        <div className="nx-modal-head p-5" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <PaletteIcon size={17} style={{ color: "var(--accent-2)" }} />
              <span className="text-[16px] font-bold text-white">پالت رنگی سفارشی</span>
            </div>
            <button onClick={onClose} className="fx-ico-btn"><X size={16} /></button>
          </div>
        </div>

        <div className="nx-modal-body p-5">
          <div className="fx-g3 grid grid-cols-2 gap-3">
            <Field label="نام پالت (انگلیسی)">
              <input className="fx-input" dir="ltr" value={name} onChange={(e) => setName(e.target.value)} placeholder="Sunset" />
            </Field>
            <Field label="نام فارسی">
              <input className="fx-input" value={fa} onChange={(e) => setFa(e.target.value)} placeholder="غروب" />
            </Field>
          </div>

          <div className="text-[13px] font-semibold text-white mt-4 mb-2.5">رنگ‌ها</div>
          <div className="fx-g3 grid grid-cols-2 gap-3">
            {COLORS.map(([k, l]) => (
              <Field key={k} label={l}>
                <div className="flex items-center gap-2">
                  <input type="color" value={vars[k]} onChange={(e) => setVar(k, e.target.value)}
                    className="w-10 h-10 rounded-lg cursor-pointer shrink-0"
                    style={{ background: "transparent", border: "1px solid var(--border-2)" }} />
                  <input className="fx-input" dir="ltr" value={vars[k]} onChange={(e) => setVar(k, e.target.value)} />
                </div>
              </Field>
            ))}
          </div>

          <div className="text-[13px] font-semibold text-white mt-4 mb-2.5">پیش‌نمایش روی ساختارها</div>
          <div className="grid gap-2.5" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(120px,1fr))" }}>
            {["classic", "analytics", "wallet", "console"].map((id) => (
              <button key={id} onClick={() => setPreview(id)} className="text-right p-2 rounded-xl transition-all"
                style={preview === id
                  ? { background: `${vars.accent}16`, border: `1px solid ${vars.accent}77` }
                  : { background: "var(--surface-3)", border: "1px solid var(--border-2)" }}>
                <TemplateThumb id={id} vars={vars} active={preview === id} />
                <div className="text-[12px] mt-1.5 font-semibold" style={{ color: preview === id ? vars.accent2 : "var(--muted)", fontFamily: "var(--mono)" }}>
                  {id}
                </div>
              </button>
            ))}
          </div>

          {err && (
            <div className="rounded-xl p-3 mt-4 flex items-center gap-2 text-[13px]"
              style={{ background: "rgba(248,113,113,.1)", border: "1px solid rgba(248,113,113,.3)", color: "var(--danger)" }}>
              <AlertTriangle size={14} /> {err}
            </div>
          )}
        </div>

        <div className="nx-modal-foot p-5 flex gap-2" style={{ borderTop: "1px solid var(--border)" }}>
          <button onClick={onClose} className="fx-btn-g flex-1 py-3 text-[14px]">انصراف</button>
          <button onClick={submit} disabled={busy} className="fx-btn flex-1 py-3 text-[14px] flex items-center justify-center gap-2">
            {busy ? <Loader2 size={14} className="animate-spin" /> : <PlusIcon size={14} />} افزودن پالت
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}

/* ===================== ربات: پلن‌ها ===================== */

function BotPlansSection({ password }) {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/bot/plans`, { headers: { "X-Admin-Password": password } }).then(r => r.json());
      setPlans(d.plans || []);
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [password]);
  useEffect(() => { if (msg) { const x = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(x); } }, [msg]);

  const up = (i, patch) => { const l = [...plans]; l[i] = { ...l[i], ...patch }; setPlans(l); };
  const add = () => setPlans([...plans, { name: "پلن جدید", gb: 30, days: 30, ip_limit: 1, price: 150000, is_active: true }]);

  const save = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/plans`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ plans }),
      });
      const d = await res.json();
      if (res.ok) { setMsg({ t: "ok", m: `${d.count} پلن ذخیره شد` }); load(); }
      else setMsg({ t: "err", m: d.detail || "ذخیره ناموفق" });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setSaving(false); }
  };

  if (loading) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  return (
    <div className="fx-anim">
      <SectionHead title="پلن‌های فروش"
        desc="پلن‌هایی که مشتری در ربات می‌بیند. حجم صفر یعنی نامحدود."
        action={
          <div className="flex gap-2">
            <button onClick={add} className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5"><PlusIcon size={13} /> پلن جدید</button>
            <button onClick={save} disabled={saving} className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} ذخیره
            </button>
          </div>
        } />

      <Msg msg={msg} />

      {plans.length === 0 && (
        <div className="fx-card p-10 text-center" style={{ borderStyle: "dashed" }}>
          <Package size={26} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
          <div className="text-[14px] text-white mb-1">هنوز پلنی تعریف نشده</div>
          <div className="text-[13px]" style={{ color: "var(--muted)" }}>
            بدون پلن، مشتری نمی‌تواند خرید کند
          </div>
        </div>
      )}

      {plans.map((p, i) => (
        <div key={i} className="fx-card p-5 mb-3">
          <div className="flex items-center justify-between gap-2 mb-4">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="fx-ico" style={{ background: p.is_trial ? "rgba(52,211,153,.12)" : "rgba(43,127,214,.12)" }}>
                {p.is_trial ? <Gift size={15} style={{ color: "var(--ok)" }} /> : <Package size={15} style={{ color: "var(--accent-2)" }} />}
              </div>
              <span className="text-[14px] font-semibold text-white truncate">{p.name || "بدون نام"}</span>
            </div>
            <div className="flex items-center gap-2">
              <Toggle checked={p.is_active !== false} onChange={() => up(i, { is_active: !(p.is_active !== false) })} label="فعال" />
              <button onClick={() => setPlans(plans.filter((_, x) => x !== i))} className="fx-ico-btn" style={{ width: 28, height: 28 }}>
                <Trash2 size={13} />
              </button>
            </div>
          </div>

          <div className="fx-g3 grid grid-cols-2 gap-3">
            <Field label="نام پلن">
              <input className="fx-input" value={p.name || ""} onChange={(e) => up(i, { name: e.target.value })} />
            </Field>
            <Field label="قیمت (تومان)">
              <input className="fx-input" dir="ltr" type="number" value={p.price ?? 0}
                onChange={(e) => up(i, { price: Number(e.target.value) })}
                style={{ fontFamily: "var(--mono)" }} />
            </Field>
          </div>

          <div className="fx-g3 grid grid-cols-3 gap-3">
            <Field label="حجم (GB)" hint="۰ = نامحدود">
              <input className="fx-input" dir="ltr" type="number" value={p.gb ?? 0}
                onChange={(e) => up(i, { gb: Number(e.target.value) })} />
            </Field>
            <Field label="مدت (روز)" hint="۰ = بدون انقضا">
              <input className="fx-input" dir="ltr" type="number" value={p.days ?? 0}
                onChange={(e) => up(i, { days: Number(e.target.value) })} />
            </Field>
            <Field label="کاربر همزمان">
              <input className="fx-input" dir="ltr" type="number" value={p.ip_limit ?? 1}
                onChange={(e) => up(i, { ip_limit: Number(e.target.value) })} />
            </Field>
          </div>

          <Field label="توضیح کوتاه (اختیاری)">
            <input className="fx-input" value={p.description || ""}
              onChange={(e) => up(i, { description: e.target.value })} placeholder="مناسب استفاده روزمره" />
          </Field>

          <label className="flex items-center gap-2 text-[13px] cursor-pointer" style={{ color: "var(--dim)" }}>
            <input type="checkbox" checked={!!p.is_trial} onChange={(e) => up(i, { is_trial: e.target.checked })}
              style={{ accentColor: "var(--accent)" }} />
            این پلن، تست رایگان است (هر کاربر فقط یک‌بار)
          </label>
        </div>
      ))}
    </div>
  );
}

/* ===================== ربات: سفارش‌ها ===================== */

const REJECT_REASONS = [
  "مبلغ واریزی با مبلغ سفارش مطابقت ندارد.",
  "تصویر رسید خوانا نبود.",
  "این رسید قبلاً استفاده شده است.",
  "رسید معتبر تشخیص داده نشد.",
];

function BotOrdersSection({ password }) {
  const [rejecting, setRejecting] = useState(null);
  const [reason, setReason] = useState("");
  const [orders, setOrders] = useState([]);
  const [filter, setFilter] = useState("awaiting");
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(null);
  const [zoom, setZoom] = useState(null);

  const load = async (f = filter) => {
    setLoading(true);
    try {
      const d = await fetch(`${API_URL}/api/admin/bot/orders?status=${f}`, { headers: { "X-Admin-Password": password } }).then(r => r.json());
      setOrders(d.orders || []);
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(filter); }, [password, filter]);
  useEffect(() => { if (msg) { const x = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(x); } }, [msg]);

  const doReject = async () => {
    if (!reason.trim()) return;
    const id = rejecting.id;
    setRejecting(null);
    setBusy(id);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/orders/${id}/reject-with-reason`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ reason }),
      });
      const d = await res.json();
      if (res.ok) {
        setMsg({ t: "ok", m: "سفارش رد شد — دلیل برای مشتری فرستاده می‌شود" });
        load(filter);
      } else setMsg({ t: "err", m: d.detail || "عملیات ناموفق" });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(null); }
  };

  const act = async (id, action) => {
    setBusy(id);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/orders/${id}/${action}`, {
        method: "POST", headers: { "X-Admin-Password": password },
      });
      const d = await res.json();
      if (res.ok) {
        setMsg({ t: "ok", m: action === "approve" ? "تایید شد — ربات کانفیگ را می‌سازد" : "سفارش رد شد" });
        load(filter);
      } else setMsg({ t: "err", m: d.detail || "عملیات ناموفق" });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(null); }
  };

  const FILTERS = [
    { k: "awaiting", l: "در انتظار تایید" },
    { k: "approved", l: "تاییدشده" },
    { k: "rejected", l: "ردشده" },
    { k: "all", l: "همه" },
  ];

  return (
    <div className="fx-anim">
      <SectionHead title="سفارش‌ها و رسیدها"
        desc="رسیدهای پرداخت کارت‌به‌کارت. تایید هم از اینجا و هم از گروه تلگرام ممکن است."
        action={
          <button onClick={() => load(filter)} className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
            <RefreshCw size={13} /> تازه‌سازی
          </button>
        } />

      <Msg msg={msg} />
      <Tabs items={FILTERS.map(f => ({ key: f.k, label: f.l }))} active={filter} onChange={setFilter} />

      {loading ? (
        <div className="flex justify-center py-14"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>
      ) : orders.length === 0 ? (
        <div className="fx-card p-10 text-center" style={{ borderStyle: "dashed" }}>
          <CreditCard size={26} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
          <div className="text-[14px]" style={{ color: "var(--muted)" }}>
            {filter === "awaiting" ? "رسیدی در انتظار تایید نیست" : "موردی یافت نشد"}
          </div>
        </div>
      ) : orders.map((o) => (
        <div key={o.id} className="fx-card p-4 mb-3">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            {o.receipt_type === "photo" && (
              <button onClick={() => setZoom(o.id)}
                className="shrink-0 rounded-xl overflow-hidden relative"
                style={{ width: 84, height: 108, border: "1px solid var(--border-2)", background: "var(--surface-3)" }}
                title="بزرگ‌نمایی">
                <img src={`${API_URL}/api/admin/bot/receipt/${o.id}?pw=${encodeURIComponent(password)}`}
                  alt="رسید" loading="lazy"
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                  onError={(e) => { e.currentTarget.style.display = "none"; }} />
                <span className="absolute bottom-1 left-1 right-1 py-0.5 rounded text-[10.5px] flex items-center justify-center gap-1"
                  style={{ background: "rgba(0,0,0,.68)", color: "#fff" }}>
                  <Search size={9} /> بزرگ‌نمایی
                </span>
              </button>
            )}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-[14px] font-semibold text-white">{o.first_name || "بدون نام"}</span>
                {o.username && <span className="text-[13px]" dir="ltr" style={{ color: "var(--muted)" }}>@{o.username}</span>}
                <StatusPill s={o.status} />
              </div>
              <div className="text-[13px] leading-relaxed" style={{ color: "var(--dim)" }}>
                مبلغ: <b style={{ color: "var(--text)" }}>{Number(o.amount || 0).toLocaleString("fa-IR")}</b> تومان
                {o.coins_used > 0 && <> · {o.coins_used} سکه ({o.discount_pct}٪ تخفیف)</>}
              </div>

              {o.receipt_type === "text" && o.receipt_text && (
                <div className="mt-2.5 rounded-xl p-3 text-[13px] leading-relaxed whitespace-pre-wrap"
                  dir="auto" style={{
                    background: "var(--surface-3)", border: "1px solid var(--border)",
                    color: "var(--dim)", fontFamily: "var(--mono)",
                    maxHeight: 130, overflowY: "auto",
                  }}>
                  {o.receipt_text}
                </div>
              )}
              <div className="text-[12px] mt-1.5" style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                #{o.id} · {o.created_at?.slice(0, 16)}
              </div>
            </div>

            {(o.status === "awaiting" || o.status === "review") && (
              <div className="flex gap-2 shrink-0">
                <button onClick={() => act(o.id, "approve")} disabled={busy === o.id}
                  className="px-3.5 py-2.5 rounded-[10px] text-[13px] font-semibold flex items-center gap-1.5"
                  style={{ background: "rgba(52,211,153,.14)", color: "var(--ok)", border: "1px solid rgba(52,211,153,.3)" }}>
                  {busy === o.id ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />} تایید
                </button>
                <button onClick={() => { setRejecting(o); setReason(""); }} disabled={busy === o.id}
                  className="fx-btn-g px-3.5 py-2.5 text-[13px]" style={{ color: "var(--danger)" }}>
                  رد با دلیل
                </button>
              </div>
            )}
          </div>
        </div>
      ))}

      {zoom && createPortal(
        <div onClick={() => setZoom(null)}
          className="fixed inset-0 z-[110] flex items-center justify-center p-6"
          style={{ background: "rgba(3,6,12,.93)", cursor: "zoom-out" }}>
          <img src={`${API_URL}/api/admin/bot/receipt/${zoom}?pw=${encodeURIComponent(password)}`} alt="رسید"
            style={{ maxWidth: "92vw", maxHeight: "88vh", borderRadius: 14, objectFit: "contain" }}
            onClick={(e) => e.stopPropagation()} />
          <button onClick={() => setZoom(null)}
            className="absolute top-5 left-5 fx-ico-btn" style={{ width: 38, height: 38 }}>
            <X size={18} />
          </button>
        </div>, document.body)}

      {rejecting && createPortal(
        <div className="nx-modal-wrap fx-fade"
          style={{ background: "rgba(3,6,12,.82)", backdropFilter: "blur(6px)" }}
          onClick={() => setRejecting(null)}>
          <div className="w-full max-w-md rounded-2xl fx-scale nx-modal flex flex-col"
            onClick={(e) => e.stopPropagation()}
            style={{ background: "var(--surface)", border: "1px solid rgba(248,113,113,.3)" }}>

            <div className="p-5 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
              <div className="flex items-center gap-2">
                <AlertTriangle size={16} style={{ color: "var(--danger)" }} />
                <span className="text-[16px] font-bold text-white">رد سفارش #{rejecting.id}</span>
              </div>
              <p className="text-[13px] mt-2 leading-relaxed" style={{ color: "var(--muted)" }}>
                دلیل برای مشتری فرستاده می‌شود و سکه‌های خرج‌شده خودکار برمی‌گردند.
              </p>
            </div>

            <div className="p-5 overflow-y-auto flex-1" style={{ minHeight: 0 }}>
              <div className="text-[13px] mb-2" style={{ color: "var(--dim)" }}>دلیل‌های آماده:</div>
              <div className="flex flex-col gap-2 mb-4">
                {REJECT_REASONS.map((r, ri) => (
                  <button key={ri} onClick={() => setReason(r)}
                    className="text-right p-2.5 rounded-xl text-[13px] transition-all"
                    style={reason === r
                      ? { background: "rgba(248,113,113,.12)", border: "1px solid rgba(248,113,113,.35)", color: "var(--text)" }
                      : { background: "var(--surface-3)", border: "1px solid var(--border)", color: "var(--dim)" }}>
                    {r}
                  </button>
                ))}
              </div>

              <Field label="یا دلیل خودتان را بنویسید">
                <textarea className="fx-input" rows={3} value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="مثلاً: مبلغ واریزی ۵۰ هزار تومان کمتر است" />
              </Field>
            </div>

            <div className="p-5 shrink-0 flex gap-2" style={{ borderTop: "1px solid var(--border)" }}>
              <button onClick={() => setRejecting(null)} className="fx-btn-g flex-1 py-3 text-[14px]">
                انصراف
              </button>
              <button onClick={doReject} disabled={!reason.trim()}
                className="flex-1 py-3 rounded-[11px] text-[14px] font-bold"
                style={{ background: reason.trim() ? "var(--danger)" : "var(--surface-2)",
                         color: reason.trim() ? "#fff" : "var(--muted)" }}>
                رد کن و اطلاع بده
              </button>
            </div>
          </div>
        </div>, document.body)}
    </div>
  );
}

function StatusPill({ s }) {
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

/* ===================== ربات: کاربران ===================== */

// فیلترهای بخش کاربران — کلیدها باید عیناً با _USER_FILTERS در
// backend/app.py بخوانند.
const USER_FILTERS = [
  { key: "all", label: "همه" },
  { key: "active", label: "اشتراک فعال" },
  { key: "expired", label: "منقضی‌شده" },
  { key: "never", label: "بدون خرید" },
  { key: "buyers", label: "خریدار" },
  { key: "withPhone", label: "شماره دارد" },
  { key: "noPhone", label: "بدون شماره" },
  { key: "withBalance", label: "کیف پول دار" },
  { key: "withCoins", label: "سکه دار" },
  { key: "referred", label: "با دعوت" },
  { key: "blocked", label: "مسدود" },
];

const USER_SORTS = [
  { key: "new", label: "تازه‌ترین" },
  { key: "old", label: "قدیمی‌ترین" },
  { key: "spent", label: "بیشترین خرید" },
  { key: "balance", label: "بیشترین موجودی" },
  { key: "coins", label: "بیشترین سکه" },
  { key: "lastSeen", label: "آخرین فعالیت" },
];

const PAGE = 40;

function BotUsersSection({ password }) {
  const [d, setD] = useState({ users: [], total: 0, counts: {} });
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("new");
  const [offset, setOffset] = useState(0);
  const [detail, setDetail] = useState(null);
  const [msgTo, setMsgTo] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async (opts = {}) => {
    const query = opts.q !== undefined ? opts.q : q;
    const f = opts.filter || filter;
    const s = opts.sort || sort;
    const off = opts.offset !== undefined ? opts.offset : offset;
    setLoading(true);
    try {
      const p = new URLSearchParams({
        q: query, filter: f, sort: s, offset: off, limit: PAGE,
      });
      const r = await fetch(`${API_URL}/api/admin/bot/users?${p}`,
        { headers: { "X-Admin-Password": password } }).then((x) => x.json());
      setD({ users: r.users || [], total: r.total || 0, counts: r.counts || {} });
    } catch { /* بی‌صدا */ }
    finally { setLoading(false); }
  };
  useEffect(() => { load({ offset: 0 }); }, [password]);

  // جستجوی زنده — بدون این، ادمین باید هر بار Enter بزند
  useEffect(() => {
    const t = setTimeout(() => { setOffset(0); load({ q, offset: 0 }); }, 350);
    return () => clearTimeout(t);
  }, [q]);

  const pick = (key) => { setFilter(key); setOffset(0); load({ filter: key, offset: 0 }); };
  const pickSort = (key) => { setSort(key); setOffset(0); load({ sort: key, offset: 0 }); };
  const go = (off) => { setOffset(off); load({ offset: off }); };

  const users = d.users;
  const pages = Math.ceil(d.total / PAGE) || 1;
  const page = Math.floor(offset / PAGE) + 1;

  return (
    <div className="fx-anim">
      <SectionHead title="کاربران ربات"
        desc="هر کسی که با ربات تعامل داشته — با سابقه‌ی خرید، شماره تماس و امکان پیام مستقیم."
        action={
          <button onClick={() => load()} disabled={loading}
            className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
            <RefreshCw size={13} /> بازخوانی
          </button>
        } />

      <div className="fx-card p-4 mb-4">
        <div className="fx-search mb-3" style={{ width: "auto" }}>
          <Search size={14} style={{ color: "var(--muted)" }} />
          <input placeholder="نام، یوزرنیم، آیدی عددی یا شماره تماس..." value={q}
            onChange={(e) => setQ(e.target.value)} />
          {q && (
            <button onClick={() => setQ("")} className="shrink-0">
              <X size={13} style={{ color: "var(--muted)" }} />
            </button>
          )}
        </div>

        <div className="flex flex-wrap gap-1.5 mb-3">
          {USER_FILTERS.map((f) => {
            const on = filter === f.key;
            const n = d.counts[f.key];
            return (
              <button key={f.key} onClick={() => pick(f.key)}
                className="px-2.5 py-1.5 rounded-[9px] text-[13px] transition-all"
                style={on
                  ? { background: "var(--accent-2)", color: "#06090F", fontWeight: 600 }
                  : { color: "var(--dim)", border: "1px solid var(--border-2)" }}>
                {f.label}
                {n !== undefined && (
                  <span className="mr-1" style={{ opacity: 0.65 }}>({faNum(n)})</span>
                )}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[12px]" style={{ color: "var(--muted)" }}>مرتب‌سازی:</span>
          {USER_SORTS.map((s) => (
            <button key={s.key} onClick={() => pickSort(s.key)}
              className="px-2 py-1 rounded-[8px] text-[13px] transition-all"
              style={sort === s.key
                ? { background: "var(--accent-soft)", color: "var(--accent-2)" }
                : { color: "var(--muted)" }}>
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-14"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>
      ) : users.length === 0 ? (
        <EmptyState icon={Users} text={q ? `چیزی برای «${q}» پیدا نشد` : "در این دسته کاربری نیست"} />
      ) : (
        <>
          <div className="fx-card overflow-hidden mb-3">
            {users.map((u, i) => (
              <div key={u.id}
                className="flex items-center justify-between gap-3 p-4 flex-wrap transition-colors hover:bg-white/[.02]"
                style={{ borderBottom: i < users.length - 1 ? "1px solid var(--border)" : "none" }}>
                <button onClick={() => setDetail(u.tg_id)}
                  className="min-w-0 flex-1 text-right">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[14px] font-semibold text-white">
                      {u.first_name || "بدون نام"}
                    </span>
                    {u.username && (
                      <span className="text-[13px]" dir="ltr" style={{ color: "var(--muted)" }}>
                        @{u.username}
                      </span>
                    )}
                    {u.activeSubs > 0 && (
                      <span className="fx-pill" style={{ background: "rgba(52,211,153,.12)", color: "var(--ok)" }}>
                        فعال
                      </span>
                    )}
                    {u.is_blocked === 1 && (
                      <span className="fx-pill" style={{ background: "rgba(248,113,113,.12)", color: "var(--danger)" }}>
                        مسدود
                      </span>
                    )}
                  </div>
                  <div className="text-[12px] mt-1 flex items-center gap-2 flex-wrap"
                    style={{ color: "var(--muted)" }}>
                    <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>{u.tg_id}</span>
                    {u.phone && (
                      <>
                        <span style={{ opacity: 0.4 }}>•</span>
                        <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>{u.phone}</span>
                      </>
                    )}
                    {u.ordersCount > 0 && (
                      <>
                        <span style={{ opacity: 0.4 }}>•</span>
                        <span>{faNum(u.ordersCount)} خرید · {faNum(u.spent)} تومان</span>
                      </>
                    )}
                  </div>
                </button>
                <div className="flex items-center gap-3 text-[13px] shrink-0">
                  {!!u.coins && <span style={{ color: "var(--warn)" }}>{faNum(u.coins)} سکه</span>}
                  {!!u.balance && <span style={{ color: "var(--ok)" }}>{faNum(u.balance)}</span>}
                  <button onClick={() => setMsgTo(u)} className="fx-ico-btn"
                    title="پیام به این کاربر" style={{ width: 30, height: 30 }}>
                    <Send size={13} />
                  </button>
                  <button onClick={() => setDetail(u.tg_id)} className="fx-ico-btn"
                    title="پرونده‌ی کاربر" style={{ width: 30, height: 30 }}>
                    <ChevronLeft size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between gap-3 flex-wrap">
            <span className="text-[13px]" style={{ color: "var(--muted)" }}>
              {faNum(offset + 1)}–{faNum(Math.min(offset + PAGE, d.total))} از {faNum(d.total)}
            </span>
            {pages > 1 && (
              <div className="flex items-center gap-2">
                <button onClick={() => go(Math.max(0, offset - PAGE))} disabled={offset === 0}
                  className="fx-btn-g px-3 py-2 text-[13px]">قبلی</button>
                <span className="text-[13px]" style={{ color: "var(--dim)" }}>
                  {faNum(page)} از {faNum(pages)}
                </span>
                <button onClick={() => go(offset + PAGE)} disabled={offset + PAGE >= d.total}
                  className="fx-btn-g px-3 py-2 text-[13px]">بعدی</button>
              </div>
            )}
          </div>
        </>
      )}

      {detail && (
        <SubscriberModal tgId={detail} password={password} onClose={() => setDetail(null)}
          onMessage={(u) => { setDetail(null); setMsgTo(u); }} />
      )}
      {msgTo && (
        <MessageUserModal user={msgTo} password={password} onClose={() => setMsgTo(null)} />
      )}
    </div>
  );
}

function MessageUserModal({ user, password, onClose }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const name = user.first_name || user.tg_id;

  const send = async () => {
    if (!text.trim()) return;
    setBusy(true); setMsg(null);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/message/${user.tg_id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ text }),
      });
      const j = await res.json().catch(() => ({}));
      if (res.ok) {
        setMsg({ t: "ok", m: "پیام فرستاده شد" });
        setText("");
        setTimeout(onClose, 1200);
      } else {
        setMsg({ t: "err", m: j.detail || "ارسال ناموفق بود" });
      }
    } catch {
      setMsg({ t: "err", m: "اتصال برقرار نشد" });
    } finally { setBusy(false); }
  };

  return (
    <Modal title={`پیام به ${name}`} onClose={onClose} width="480px"
      footer={
        <div className="flex items-center justify-between gap-3 w-full">
          <span className="text-[12px]" style={{ color: "var(--muted)" }}>
            از طرف ربات، با عنوان «پیام از پشتیبانی» فرستاده می‌شود
          </span>
          <button onClick={send} disabled={busy || !text.trim()}
            className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5 shrink-0">
            {busy ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />} ارسال
          </button>
        </div>
      }>
      <Msg msg={msg} />
      <textarea className="fx-input" rows={6} value={text} autoFocus
        onChange={(e) => setText(e.target.value)}
        placeholder="سلام! درباره‌ی سفارشتان تماس می‌گیرم…"
        style={{ resize: "vertical", lineHeight: 1.8 }} />
      <div className="text-[12px] mt-2 flex items-center justify-between"
        style={{ color: "var(--muted)" }}>
        <span>{faNum(text.length)} از ۳۵۰۰ کاراکتر</span>
        {user.username && <span dir="ltr">@{user.username}</span>}
      </div>
      <InfoBox>
        اگر کاربر ربات را بلاک کرده باشد، پیام نمی‌رسد و همین‌جا به شما گفته می‌شود.
      </InfoBox>
    </Modal>
  );
}

/* ===================== بازگشت به نسخه قبلی ===================== */

function RollbackCard({ password }) {
  const [snaps, setSnaps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [confirm, setConfirm] = useState(null);
  const [keepSettings, setKeepSettings] = useState(true);
  const [msg, setMsg] = useState(null);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/snapshots`, {
        headers: { "X-Admin-Password": password } }).then((r) => r.json());
      setSnaps(d.snapshots || []);
    } catch { /* بی‌صدا */ }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [password]);
  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 5000); return () => clearTimeout(t); } }, [msg]);

  const run = async () => {
    const id = confirm.id;
    setConfirm(null);
    try {
      const res = await fetch(`${API_URL}/api/admin/rollback`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ id, keepSettings }),
      });
      const d = await res.json();
      if (res.ok) {
        setMsg({ t: "ok", m: "بازگشت شروع شد — صفحه تا لحظاتی دیگر بارگذاری می‌شود" });
        setTimeout(() => window.location.reload(), 45000);
      } else setMsg({ t: "err", m: d.detail || "بازگشت ناموفق" });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
  };

  if (loading) return null;

  return (
    <div className="fx-card p-5 mb-4">
      <div className="flex items-center gap-2 mb-1">
        <History size={15} style={{ color: "var(--warn)" }} />
        <span className="text-[14px] font-semibold text-white">بازگشت به نسخه قبلی</span>
      </div>
      <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
        قبل از هر به‌روزرسانی یک نسخه‌ی کامل ذخیره می‌شود و پنج نسخه‌ی آخر نگه داشته می‌شوند.
        وضعیت فعلی هم قبل از بازگشت ذخیره می‌شود، پس همیشه می‌توانید دوباره جلو بروید.
      </p>

      <Msg msg={msg} />

      {snaps.length === 0 ? (
        <div className="text-center py-6 text-[13px]" style={{ color: "var(--muted)" }}>
          هنوز نسخه‌ی ذخیره‌شده‌ای نیست — با اولین به‌روزرسانی ساخته می‌شود
        </div>
      ) : (
        <>
          <label className="flex items-center gap-2 text-[13px] mb-3 cursor-pointer" style={{ color: "var(--dim)" }}>
            <input type="checkbox" checked={keepSettings} onChange={(e) => setKeepSettings(e.target.checked)}
              style={{ accentColor: "var(--accent)" }} />
            تنظیمات فعلی حفظ شود (توصیه می‌شود)
          </label>

          <div className="mt-4">
          {snaps.map((s) => (
            <div key={s.id} className="flex items-center justify-between gap-3 p-3.5 rounded-xl mb-3 flex-wrap"
              style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[14px] font-semibold text-white">نسخه {s.version}</span>
                  {s.hasBot && <span className="fx-pill" style={{ background: "rgba(43,127,214,.12)", color: "var(--accent-2)" }}>شامل ربات</span>}
                </div>
                <div className="text-[12px] mt-1" style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                  {s.createdAt?.replace("T", " ").slice(0, 16)} · {s.sizeMb} MB
                </div>
              </div>
              <button onClick={() => setConfirm(s)}
                className="fx-btn-g px-3.5 py-2.5 text-[13px] shrink-0" style={{ color: "var(--warn)" }}>
                بازگشت به این نسخه
              </button>
            </div>
          ))}
          </div>
        </>
      )}

      {confirm && (
        <ConfirmModal
          title={`بازگشت به نسخه ${confirm.version}؟`}
          desc={`پنل به وضعیت ${confirm.createdAt?.slice(0, 10)} برمی‌گردد و حدود یک دقیقه در دسترس نخواهد بود.${keepSettings ? " تنظیمات فعلی حفظ می‌شود." : " تنظیمات هم به همان نسخه برمی‌گردد."}`}
          confirmLabel="بله، برگرد"
          onConfirm={run}
          onCancel={() => setConfirm(null)} />
      )}
    </div>
  );
}

/* ===================== ربات: متن‌ها ===================== */

const BOT_TEXTS = [
  { k: "welcome_text", label: "پیام خوش‌آمد",
    hint: "اگر خالی بماند، وضعیت زنده‌ی کاربر نمایش داده می‌شود",
    vars: ["{name}", "{brand}"],
    sample: "سلام {name} 👋\n\nبه {brand} خوش آمدید." },
  { k: "phone_prompt", label: "درخواست شماره",
    hint: "اختیاری بودن آن را حتماً بگویید", vars: [],
    sample: "📱 اگر شماره‌تان را ثبت کنید، سریع‌تر می‌توانیم کمکتان کنیم." },
  { k: "waiting_text", label: "بعد از ارسال رسید",
    hint: "", vars: ["{order_id}", "{support}"],
    sample: "✅ رسید شما دریافت شد\nکد پیگیری: {order_id}" },
  { k: "reject_text", label: "رد رسید",
    hint: "دلیل رد خودکار جایگزین می‌شود", vars: ["{order_id}", "{reason}", "{support}"],
    sample: "❌ رسید شما تایید نشد\n\nدلیل: {reason}" },
  { k: "delivered_text", label: "تحویل کانفیگ",
    hint: "", vars: ["{plan}", "{sub_url}", "{expires}"],
    sample: "🎉 اشتراک شما فعال شد!\n\n{sub_url}" },
  { k: "expiry_text", label: "یادآوری انقضا",
    hint: "", vars: ["{days}", "{plan}"],
    sample: "⏰ {days} روز تا پایان اشتراک شما باقی مانده." },
];

function BotTextsSection({ password }) {
  const [t, setT] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/bot/settings`, {
        headers: { "X-Admin-Password": password } }).then((r) => r.json());
      setT({
        settings: {}, topics: {},
        ...(d.tenant || {}),
        settings: (d.tenant?.settings && typeof d.tenant.settings === "object"
                   && !Array.isArray(d.tenant.settings)) ? d.tenant.settings : {},
      });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [password]);
  useEffect(() => { if (msg) { const x = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(x); } }, [msg]);

  const s = t?.settings || {};
  const upS = (patch) => setT({ ...t, settings: { ...s, ...patch } });

  const save = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ settings: t.settings }),
      });
      setMsg(res.ok ? { t: "ok", m: "متن‌ها ذخیره شد — ربات فوری اعمال می‌کند" }
                    : { t: "err", m: "ذخیره ناموفق" });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setSaving(false); }
  };

  if (loading) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  return (
    <div className="fx-anim">
      <SectionHead title="متن‌های ربات"
        desc="هر پیامی که ربات می‌فرستد قابل ویرایش است. خالی بگذارید تا متن پیش‌فرض استفاده شود."
        action={
          <button onClick={save} disabled={saving} className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} ذخیره
          </button>
        } />

      <Msg msg={msg} />

      <InfoBox>
        تغییرات <b>بدون ری‌استارت ربات</b> اعمال می‌شوند — ربات هر بار تنظیمات را تازه می‌خواند.
      </InfoBox>

      {BOT_TEXTS.map((f) => (
        <div key={f.k} className="fx-card p-4 mt-3">
          <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
            <span className="text-[14px] font-semibold text-white">{f.label}</span>
            {f.vars.length > 0 && (
              <div className="flex gap-1.5 flex-wrap">
                {f.vars.map((v) => (
                  <code key={v} className="text-[11.5px] px-2 py-1 rounded-md"
                    style={{ background: "rgba(43,127,214,.14)", color: "var(--accent-2)",
                             fontFamily: "var(--mono)" }}>{v}</code>
                ))}
              </div>
            )}
          </div>
          <textarea className="fx-input" rows={3} value={s[f.k] || ""}
            onChange={(e) => upS({ [f.k]: e.target.value })}
            placeholder={f.sample} style={{ resize: "vertical", lineHeight: 1.9 }} />
          {f.hint && <div className="text-[12px] mt-1.5" style={{ color: "var(--muted)" }}>{f.hint}</div>}
        </div>
      ))}
    </div>
  );
}

/* ===================== ربات: پیش‌نمایش ===================== */

const PREVIEW_FLOWS = {
  welcome: {
    label: "خوش‌آمد",
    msgs: [
      { me: true, t: "/start" },
      { t: "سلام علی 👋\n\n📦 <b>استاندارد</b>\n   ✅ <b>۱۷ روز</b> باقی مانده\n\n💎 ۴۵ سکه <i>(۲۰٪ تخفیف)</i>   ·   👛 ۱۲۰,۰۰۰",
        kb: [["🛒 خرید اشتراک", "♻️ تمدید"], ["📊 وضعیت من", "💎 سکه و دعوت"], ["👛 کیف پول", "🎓 آموزش"], ["🎧 پشتیبانی"]] },
    ],
  },
  phone: {
    label: "شماره تماس",
    msgs: [
      { t: "📱 <b>شماره تماس</b>\n\nاگر شماره‌تان را ثبت کنید، در صورت بروز مشکل سریع‌تر می‌توانیم کمکتان کنیم.\n\n<i>اختیاری است — بدون آن هم می‌توانید خرید کنید.</i>",
        contact: true, kb: [["📱 ارسال شماره من"], ["فعلاً نه"]] },
    ],
  },
  buy: {
    label: "خرید با سکه",
    msgs: [
      { me: true, t: "🥈 استاندارد · ۶۰GB" },
      { t: "<b>پلن استاندارد</b> 🥈\n\n📦 حجم: ۶۰ گیگابایت\n⏱ مدت: ۳۰ روز\n👥 کاربر همزمان: ۲\n\n💵 قیمت: ۲۵۰,۰۰۰ تومان\n\n💎 <b>سکه‌های تو: ۴۵</b>\nمی‌توانی ۴۰ سکه خرج کنی ← <b>۲۰٪ تخفیف</b>\n\n💰 قیمت نهایی: <b>۲۰۰,۰۰۰</b>",
        kb: [["✅ خرید با ۲۰٪ تخفیف"], ["💵 خرید بدون تخفیف"], ["‹ بازگشت"]] },
    ],
  },
  wait: {
    label: "انتظار تایید",
    msgs: [
      { me: true, img: true, t: "[عکس رسید]" },
      { t: "✅ <b>رسید شما دریافت شد</b>\n━━━━━━━━━━━━━━━━━━━\n\n🔢 کد پیگیری: <code>#4821</code>\n⏳ در انتظار بررسی\n\nمعمولاً کمتر از ۱۵ دقیقه طول می‌کشد.\nبه محض تایید، کانفیگتان همین‌جا ارسال می‌شود.",
        kb: [["📊 وضعیت سفارش"], ["🎧 پشتیبانی"], ["‹ منوی اصلی"]] },
    ],
  },
  reject: {
    label: "رد رسید",
    msgs: [
      { t: "❌ <b>رسید شما تایید نشد</b>\n━━━━━━━━━━━━━━━━━━━\n\n🔢 کد پیگیری: <code>#4821</code>\n\n<b>دلیل:</b>\nمبلغ واریزی با مبلغ سفارش مطابقت ندارد.\n\n💎 ۴۰ سکه‌ی شما برگردانده شد.\n\nمی‌توانید رسید درست را دوباره بفرستید.",
        kb: [["🔄 ارسال مجدد رسید"], ["🎧 پشتیبانی"], ["‹ منوی اصلی"]] },
    ],
  },
  trial: {
    label: "تست رایگان",
    msgs: [
      { me: true, t: "🎁 تست رایگان" },
      { t: "🎁 <b>اشتراک تست رایگان</b>\n\n📦 حجم: <b>۱ گیگابایت</b>\n⏱ مدت: <b>۲۴ ساعت</b>\n\n<i>هر کاربر فقط یک‌بار می‌تواند دریافت کند.</i>",
        kb: [["✅ فعال‌سازی تست"], ["‹ بازگشت"]] },
    ],
  },
  admin: {
    label: "پنل مدیریت",
    msgs: [
      { me: true, t: "⚙️ پنل مدیریت" },
      { t: "⚙️ <b>پنل مدیریت</b> · نکسورا\n━━━━━━━━━━━━━━━━━━━\n\n👥 کاربران   <b>۴۸۲</b>\n📦 اشتراک فعال   <b>۱۹۷</b>\n💳 رسید در انتظار   <b>۳</b>\n🎫 تیکت باز   <b>۲</b>\n\n💰 فروش کل   <b>۴۸,۵۰۰,۰۰۰</b>",
        kb: [["💳 رسیدها (۳)"], ["👥 کاربران", "📦 پلن‌ها"], ["📊 آمار", "📢 پیام همگانی"], ["‹ بازگشت"]] },
    ],
  },
};

function BotPreviewSection() {
  const [flow, setFlow] = useState("welcome");
  const f = PREVIEW_FLOWS[flow];

  const md = (t) => {
    const parts = t.split(/(<b>[^<]*<\/b>|<code>[^<]*<\/code>|<i>[^<]*<\/i>)/g);
    return parts.map((p, i) => {
      if (p.startsWith("<b>")) return <b key={i} style={{ color: "#fff" }}>{p.slice(3, -4)}</b>;
      if (p.startsWith("<i>")) return <i key={i} style={{ opacity: .72 }}>{p.slice(3, -4)}</i>;
      if (p.startsWith("<code>")) return <code key={i} style={{
        background: "rgba(255,255,255,.09)", padding: "1px 5px", borderRadius: 4,
        fontFamily: "var(--mono)", fontSize: 9.5, color: "#8FC1EE" }}>{p.slice(6, -7)}</code>;
      return p;
    });
  };

  return (
    <div className="fx-anim">
      <SectionHead title="پیش‌نمایش ربات"
        desc="آنچه مشتری در تلگرام می‌بیند. روی هر مرحله بزنید." />

      <div className="fx-g2 grid gap-6" style={{ gridTemplateColumns: "1fr 300px" }}>
        <div className="min-w-0">
          <div className="flex flex-col gap-2">
            {Object.entries(PREVIEW_FLOWS).map(([k, v]) => {
              const on = flow === k;
              return (
                <button key={k} onClick={() => setFlow(k)}
                  className="flex items-center gap-3 px-4 py-3 rounded-xl text-right transition-all"
                  style={on
                    ? { background: "rgba(43,127,214,.14)", border: "1px solid rgba(43,127,214,.45)" }
                    : { background: "var(--surface)", border: "1px solid var(--border)" }}>
                  {on ? <Check size={14} style={{ color: "var(--accent-2)" }} />
                      : <Circle size={7} fill="var(--muted)" strokeWidth={0} />}
                  <span className="text-[14px] font-semibold"
                    style={{ color: on ? "var(--text)" : "var(--dim)" }}>{v.label}</span>
                </button>
              );
            })}
          </div>

          <InfoBox>
            متن‌ها را در بخش <b>«متن‌ها»</b> می‌توانید تغییر دهید.
            پیش‌نمایش، حالت پیش‌فرض را نشان می‌دهد.
          </InfoBox>
        </div>

        <div className="fx-hide-m">
          <div className="sticky top-24">
            <div style={{
              borderRadius: 28, padding: 9,
              background: "linear-gradient(160deg,#232B3C,#0C1119)",
              border: "1px solid rgba(255,255,255,.13)",
              boxShadow: "0 20px 52px rgba(0,0,0,.5)",
            }}>
              <div className="flex justify-center mb-1.5">
                <div style={{ width: 46, height: 4, borderRadius: 99, background: "rgba(255,255,255,.18)" }} />
              </div>
              <div style={{
                background: "#0E1621", borderRadius: 21, padding: "12px 10px",
                height: 420, overflowY: "auto", direction: "rtl",
              }}>
                <div className="flex items-center gap-2 pb-2.5 mb-3"
                  style={{ borderBottom: "1px solid rgba(255,255,255,.07)" }}>
                  <div style={{
                    width: 26, height: 26, borderRadius: "50%",
                    background: "linear-gradient(135deg,var(--accent),var(--accent-2))",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 12, fontWeight: 800, color: "#06090F",
                  }}>N</div>
                  <div>
                    <div className="text-[13px] font-bold" style={{ color: "#fff" }}>ربات نکسورا</div>
                    <div className="text-[10.5px]" style={{ color: "#6B8299" }}>آنلاین</div>
                  </div>
                </div>

                {f.msgs.map((m, i) => (
                  <div key={i} className="mb-2.5 flex" style={{ justifyContent: m.me ? "flex-start" : "flex-end" }}>
                    <div style={{ maxWidth: "89%" }}>
                      <div style={{
                        background: m.me ? "#2B5278" : "#182533",
                        borderRadius: m.me ? "12px 12px 12px 4px" : "12px 12px 4px 12px",
                        padding: "8px 10px", fontSize: 10, lineHeight: 1.9,
                        color: "#E8EEF7", whiteSpace: "pre-wrap",
                      }}>
                        {m.img && (
                          <div style={{
                            height: 50, borderRadius: 7, marginBottom: 5,
                            background: "linear-gradient(135deg,#2A3A4A,#1A2530)",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: 8.5, color: "#6B8299",
                          }}>🧾 رسید</div>
                        )}
                        {md(m.t)}
                      </div>
                      {m.kb && (
                        <div className="mt-1.5 flex flex-col gap-1">
                          {m.kb.map((row, ri) => (
                            <div key={ri} className="flex gap-1">
                              {row.map((b, bi) => (
                                <div key={bi} style={{
                                  flex: 1, borderRadius: 8, padding: "7px 5px",
                                  fontSize: 8.8, textAlign: "center", fontWeight: 600,
                                  background: m.contact && ri === 0 ? "#2F5C42" : "#1F2C3A",
                                  border: `1px solid ${m.contact && ri === 0 ? "rgba(110,231,183,.35)" : "rgba(90,169,230,.22)"}`,
                                  color: m.contact && ri === 0 ? "#6EE7B7" : "#8FC1EE",
                                }}>{b}</div>
                              ))}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ===================== ربات: آمار و قیف ===================== */

function BotStatsSection({ password }) {
  const [d, setD] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API_URL}/api/admin/bot/funnel`, {
        headers: { "X-Admin-Password": password } }).then((x) => x.json());
      setD(r);
    } catch { /* بی‌صدا */ }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [password]);

  if (loading) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  if (!d?.ready) {
    return (
      <div className="fx-anim">
        <SectionHead title="آمار و قیف تبدیل" desc="وقتی ربات راه بیفتد، آمار اینجا نمایش داده می‌شود." />
        <div className="fx-card p-10 text-center" style={{ borderStyle: "dashed" }}>
          <TrendingUp size={26} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
          <div className="text-[14px]" style={{ color: "var(--muted)" }}>هنوز داده‌ای نیست</div>
        </div>
      </div>
    );
  }

  const seg = d.segments || {};
  const cards = [
    ["استارت‌زده", d.started, "کل کسانی که ربات را باز کردند", "var(--accent-2)"],
    ["خرید کرده", seg.paid, d.started ? `${Math.round(seg.paid * 100 / d.started)}٪ نرخ تبدیل` : "", "var(--ok)"],
    ["فقط تست گرفته", seg.trialOnly, "هدف خوبی برای پیگیری", "var(--warn)"],
    ["بدون هیچ اقدام", seg.idle, "نه خرید، نه تست", "var(--muted)"],
  ];

  return (
    <div className="fx-anim">
      <SectionHead title="آمار و قیف تبدیل"
        desc="از باز کردن ربات تا خرید — کجا مشتری را از دست می‌دهید."
        action={
          <button onClick={load} className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
            <RefreshCw size={13} /> تازه‌سازی
          </button>
        } />

      <div className="fx-g4 grid grid-cols-4 gap-4 mb-5">
        {cards.map(([l, v, sub, c], i) => (
          <div key={i} className="fx-card p-5">
            <div className="fx-stat-num" style={{ color: c }}><CountUp value={v ?? 0} /></div>
            <div className="text-[13px] mt-2" style={{ color: "var(--dim)" }}>{l}</div>
            {sub && <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>{sub}</div>}
          </div>
        ))}
      </div>

      <div className="fx-card p-5">
        <div className="text-[14px] font-semibold text-white mb-4">قیف تبدیل</div>
        {(d.steps || []).map((s, i) => {
          const colors = ["var(--accent-2)", "var(--purple)", "var(--warn)", "var(--ok)"];
          const c = colors[i] || "var(--accent-2)";
          return (
            <div key={i} className="mb-3">
              <div className="flex justify-between mb-1.5">
                <span className="text-[13px]" style={{ color: "var(--dim)" }}>{s.label}</span>
                <span className="text-[13px] font-bold" style={{ color: c, fontFamily: "var(--mono)" }}>
                  {s.n} <span style={{ color: "var(--muted)", fontSize: 10 }}>({s.pct}٪)</span>
                </span>
              </div>
              <div className="h-[7px] rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,.05)" }}>
                <div style={{ width: `${s.pct}%`, height: "100%", borderRadius: 99, background: c, opacity: .85 }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ===================== ربات: بک‌آپ ===================== */

function BotBackupSection({ password }) {
  const [busy, setBusy] = useState(null);
  const [msg, setMsg] = useState(null);
  const [confirm, setConfirm] = useState(null);
  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 5000); return () => clearTimeout(t); } }, [msg]);

  const download = async () => {
    setBusy("dl");
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/backup`, {
        headers: { "X-Admin-Password": password } });
      const d = await res.json();
      if (!res.ok) { setMsg({ t: "err", m: d.detail || "دریافت ناموفق" }); return; }

      const blob = new Blob([JSON.stringify(d, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `nexora-bot-backup-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
      const total = Object.values(d.counts || {}).reduce((x, y) => x + y, 0);
      setMsg({ t: "ok", m: `بک‌آپ دانلود شد — ${total} رکورد` });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(null); }
  };

  const pickFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const r = new FileReader();
    r.onload = () => {
      try {
        const parsed = JSON.parse(r.result);
        if (!parsed.data) { setMsg({ t: "err", m: "این فایل بک‌آپ ربات نیست" }); return; }
        setConfirm(parsed);
      } catch { setMsg({ t: "err", m: "فایل خراب است" }); }
    };
    r.readAsText(f);
    e.target.value = "";
  };

  const restore = async () => {
    const payload = confirm;
    setConfirm(null); setBusy("up");
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/restore`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ data: payload.data }),
      });
      const d = await res.json();
      if (res.ok) {
        const total = Object.values(d.restored || {}).reduce((x, y) => x + y, 0);
        setMsg({ t: "ok", m: `${total} رکورد بازیابی شد` });
      } else setMsg({ t: "err", m: d.detail || "بازیابی ناموفق" });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(null); }
  };

  return (
    <div className="fx-anim">
      <SectionHead title="بک‌آپ و بازیابی ربات"
        desc="کاربران، سفارش‌ها، اشتراک‌ها، سکه‌ها و تنظیمات ربات." />
      <Msg msg={msg} />

      <div className="fx-g2 grid grid-cols-2 gap-4 mb-4">
        <button onClick={download} disabled={!!busy} className="fx-card p-6 text-center">
          <div className="fx-ico mx-auto mb-3" style={{ width: 44, height: 44, background: "rgba(43,127,214,.12)" }}>
            {busy === "dl" ? <Loader2 size={20} className="animate-spin" style={{ color: "var(--accent-2)" }} />
                           : <Download size={20} style={{ color: "var(--accent-2)" }} />}
          </div>
          <div className="text-[14px] font-semibold text-white mb-1">دریافت بک‌آپ</div>
          <div className="text-[13px]" style={{ color: "var(--muted)" }}>یک فایل JSON دانلود می‌شود</div>
        </button>

        <label className="fx-card p-6 text-center cursor-pointer">
          <div className="fx-ico mx-auto mb-3" style={{ width: 44, height: 44, background: "rgba(251,191,36,.12)" }}>
            {busy === "up" ? <Loader2 size={20} className="animate-spin" style={{ color: "var(--warn)" }} />
                           : <Upload size={20} style={{ color: "var(--warn)" }} />}
          </div>
          <div className="text-[14px] font-semibold text-white mb-1">بازیابی از فایل</div>
          <div className="text-[13px]" style={{ color: "var(--muted)" }}>فایل بک‌آپ را انتخاب کنید</div>
          <input type="file" accept=".json" onChange={pickFile} className="hidden" disabled={!!busy} />
        </label>
      </div>

      <InfoBox tone="warn">
        بازیابی، <b>همه‌ی داده‌های فعلی ربات را جایگزین می‌کند</b>.
        قبل از آن یک نسخه‌ی امن از وضعیت فعلی کنار دیتابیس ذخیره می‌شود،
        پس اگر اشتباه شد چیزی از دست نمی‌رود.
      </InfoBox>

      {confirm && (
        <ConfirmModal
          title="بازیابی بک‌آپ؟"
          desc={`این فایل شامل ${Object.entries(confirm.counts || {}).map(([k, v]) => `${v} ${k}`).join(" · ")} است. همه‌ی داده‌های فعلی ربات جایگزین می‌شوند.`}
          confirmLabel="بازیابی کن"
          onConfirm={restore}
          onCancel={() => setConfirm(null)} />
      )}
    </div>
  );
}

/* ===================== ربات: پرونده مشتری ===================== */

const fmtBytes = (n) => {
  const b = Number(n || 0);
  if (b <= 0) return "۰";
  const gb = b / 1073741824;
  if (gb >= 1) return `${gb.toFixed(1)} GB`;
  return `${(b / 1048576).toFixed(0)} MB`;
};

const fmtDate = (ms) => {
  if (!ms) return "بدون انقضا";
  try {
    return new Date(Number(ms)).toLocaleDateString("fa-IR");
  } catch { return "—"; }
};

const daysLeft = (ms) => {
  if (!ms) return null;
  const d = Math.ceil((Number(ms) - Date.now()) / 86400000);
  return d;
};

function SubscriberModal({ tgId, password, onClose, onMessage }) {
  const [d, setD] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/admin/bot/subscriber/${tgId}`, {
          headers: { "X-Admin-Password": password },
        });
        const body = await res.json();
        if (res.ok) setD(body);
        else setErr(body.detail || "دریافت اطلاعات ناموفق بود");
      } catch { setErr("اتصال به سرور برقرار نشد"); }
      finally { setLoading(false); }
    })();
  }, [tgId, password]);

  const u = d?.user || {};
  const subs = d?.subscriptions || [];
  const live = d?.live || {};

  return createPortal(
    <div className="nx-modal-wrap fx-fade"
      style={{ background: "rgba(3,6,12,.84)", backdropFilter: "blur(6px)" }}
      onClick={onClose}>
      <div className="w-full max-w-2xl rounded-2xl fx-scale nx-modal flex flex-col"
        onClick={(e) => e.stopPropagation()}
        style={{ background: "var(--surface)", border: "1px solid rgba(90,169,230,.3)" }}>

        <div className="p-5 shrink-0 flex items-start justify-between gap-3"
          style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[16px] font-bold text-white">
                {u.first_name || "بدون نام"}
              </span>
              {u.username && (
                <span className="text-[13px]" dir="ltr" style={{ color: "var(--muted)" }}>
                  @{u.username}
                </span>
              )}
              {u.is_blocked === 1 && (
                <span className="fx-pill" style={{ background: "rgba(248,113,113,.12)", color: "var(--danger)" }}>
                  مسدود
                </span>
              )}
            </div>
            <div className="text-[12px] mt-1.5" dir="ltr"
              style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
              {u.tg_id}{u.phone ? ` · ${u.phone}` : ""}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {onMessage && u.tg_id && (
              <button onClick={() => onMessage(u)}
                className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
                <Send size={13} /> پیام
              </button>
            )}
            <button onClick={onClose} className="fx-ico-btn"><X size={16} /></button>
          </div>
        </div>

        <div className="p-5 overflow-y-auto flex-1" style={{ minHeight: 0 }}>
          {loading && (
            <div className="flex justify-center py-14">
              <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} />
            </div>
          )}

          {err && (
            <div className="rounded-xl p-3 flex items-center gap-2 text-[13px]"
              style={{ background: "rgba(248,113,113,.1)", border: "1px solid rgba(248,113,113,.3)", color: "var(--danger)" }}>
              <AlertTriangle size={14} /> {err}
            </div>
          )}

          {d && (
            <>
              {/* خلاصه */}
              <div className="fx-g3 grid grid-cols-3 gap-3 mb-5">
                {[
                  ["سکه", u.coins || 0, "var(--warn)"],
                  ["کیف پول", Number(u.balance || 0).toLocaleString("fa-IR"), "var(--ok)"],
                  ["خرید موفق", (d.orders || []).filter((o) => o.status === "approved").length, "var(--accent-2)"],
                ].map(([l, v, c2], i) => (
                  <div key={i} className="rounded-xl p-3 text-center"
                    style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
                    <div className="text-[18px] font-bold" style={{ color: c2, fontFamily: "var(--mono)" }}>{v}</div>
                    <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>{l}</div>
                  </div>
                ))}
              </div>

              {/* اشتراک‌ها */}
              <div className="text-[14px] font-semibold text-white mb-3">
                اشتراک‌ها
                {!d.liveAvailable && subs.length > 0 && (
                  <span className="text-[12px] font-normal mr-2" style={{ color: "var(--warn)" }}>
                    · داده زنده در دسترس نیست
                  </span>
                )}
              </div>

              {subs.length === 0 && (
                <div className="text-center py-6 text-[13px]" style={{ color: "var(--muted)" }}>
                  اشتراکی ندارد
                </div>
              )}

              {subs.map((s) => {
                const lv = live[s.client_email];
                const used = lv ? (lv.up || 0) + (lv.down || 0) : 0;
                const total = lv?.total || 0;
                const pct = total > 0 ? Math.min(100, Math.round(used * 100 / total)) : 0;
                const dl = lv?.expiryTime ? daysLeft(lv.expiryTime) : null;
                const near = dl !== null && dl <= 3;

                return (
                  <div key={s.id} className="fx-card p-4 mb-3" style={{ background: "var(--surface-3)" }}>
                    <div className="flex items-center justify-between gap-2 mb-3 flex-wrap">
                      <div className="flex items-center gap-2">
                        <Package size={14} style={{ color: "var(--accent-2)" }} />
                        <span className="text-[14px] font-semibold text-white">
                          {s.plan_name || "اشتراک"}
                        </span>
                      </div>
                      <span className="fx-pill" style={{
                        background: s.is_active ? "rgba(52,211,153,.12)" : "rgba(255,255,255,.05)",
                        color: s.is_active ? "var(--ok)" : "var(--muted)",
                      }}>
                        {s.is_active ? "فعال" : "غیرفعال"}
                      </span>
                    </div>

                    <div className="text-[12px] mb-3" dir="ltr"
                      style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                      {s.client_email}
                    </div>

                    {lv ? (
                      <>
                        <div className="flex justify-between mb-2">
                          <span className="text-[13px]" style={{ color: "var(--dim)" }}>مصرف حجم</span>
                          <span className="text-[13px] font-bold"
                            style={{ color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
                            {fmtBytes(used)} {total > 0 ? `/ ${fmtBytes(total)}` : "· نامحدود"}
                          </span>
                        </div>

                        {total > 0 && (
                          <div className="h-[8px] rounded-full overflow-hidden mb-3"
                            style={{ background: "rgba(43,127,214,.12)" }}>
                            <div style={{
                              width: `${pct}%`, height: "100%", borderRadius: 99,
                              background: pct >= 85
                                ? "linear-gradient(90deg,var(--danger),#FCA5A5)"
                                : "linear-gradient(90deg,var(--accent),var(--accent-2))",
                            }} />
                          </div>
                        )}

                        <div className="grid grid-cols-3 gap-2 mb-3">
                          {[
                            ["دانلود", fmtBytes(lv.down), "var(--ok)"],
                            ["آپلود", fmtBytes(lv.up), "var(--warn)"],
                            ["باقی", total > 0 ? fmtBytes(Math.max(0, total - used)) : "∞", "var(--accent-2)"],
                          ].map(([l, v, c2], i) => (
                            <div key={i} className="text-center">
                              <div className="text-[11.5px]" style={{ color: "var(--muted)" }}>{l}</div>
                              <div className="text-[13px] font-bold mt-0.5"
                                style={{ color: c2, fontFamily: "var(--mono)" }}>{v}</div>
                            </div>
                          ))}
                        </div>

                        <div className="flex justify-between text-[13px] pt-2"
                          style={{ borderTop: "1px solid var(--border)" }}>
                          <span style={{ color: "var(--muted)" }}>انقضا</span>
                          <span style={{ color: near ? "var(--warn)" : "var(--dim)" }}>
                            {fmtDate(lv.expiryTime)}
                            {dl !== null && (dl > 0 ? ` · ${dl} روز مانده` : " · منقضی شده")}
                          </span>
                        </div>
                      </>
                    ) : (
                      <div className="text-[13px] py-2" style={{ color: "var(--muted)" }}>
                        داده‌ی زنده از 3x-ui دریافت نشد — اتصال پنل را بررسی کنید
                      </div>
                    )}
                  </div>
                );
              })}

              {/* آخرین سفارش‌ها */}
              {(d.orders || []).length > 0 && (
                <>
                  <div className="text-[14px] font-semibold text-white mt-5 mb-3">آخرین سفارش‌ها</div>
                  {d.orders.slice(0, 6).map((o) => (
                    <div key={o.id} className="flex items-center justify-between gap-2 py-2.5"
                      style={{ borderBottom: "1px solid var(--border)" }}>
                      <div className="min-w-0">
                        <div className="text-[13px]" style={{ color: "var(--dim)" }}>
                          {o.plan_name || "—"}
                        </div>
                        <div className="text-[12px] mt-0.5"
                          style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                          #{o.id} · {String(o.created_at || "").slice(0, 10)}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-[13px]" style={{ color: "var(--dim)" }}>
                          {Number(o.amount || 0).toLocaleString("fa-IR")}
                        </span>
                        <StatusPill s={o.status} />
                      </div>
                    </div>
                  ))}
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}

/* ===================== ربات: سکه و دعوت ===================== */

function BotCoinsSection({ password }) {
  const [t, setT] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/bot/settings`, { headers: { "X-Admin-Password": password } }).then(r => r.json());
      setT({
        settings: {}, topics: {},
        ...(d.tenant || {}),
        settings: (d.tenant?.settings && typeof d.tenant.settings === "object"
                   && !Array.isArray(d.tenant.settings)) ? d.tenant.settings : {},
      });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [password]);
  useEffect(() => { if (msg) { const x = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(x); } }, [msg]);

  const s = t?.settings || {};
  const tiers = s.coin_tiers || [
    { coins: 20, pct: 10 }, { coins: 40, pct: 20 }, { coins: 60, pct: 30 },
    { coins: 80, pct: 40 }, { coins: 100, pct: 50 },
  ];
  const upS = (patch) => setT({ ...t, settings: { ...s, ...patch } });

  const save = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ settings: t.settings }),
      });
      if (res.ok) setMsg({ t: "ok", m: "تنظیمات سکه ذخیره شد" });
      else setMsg({ t: "err", m: "ذخیره ناموفق" });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setSaving(false); }
  };

  if (loading) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  return (
    <div className="fx-anim">
      <SectionHead title="سکه و دعوت"
        desc="کاربران با دعوت دوستان سکه می‌گیرند و با نگه‌داشتن سکه، تخفیف بزرگ‌تری باز می‌کنند."
        action={
          <button onClick={save} disabled={saving} className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} ذخیره
          </button>
        } />

      <Msg msg={msg} />

      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-4 flex items-center gap-2">
          <Gift size={15} style={{ color: "var(--warn)" }} /> قوانین دریافت سکه
        </div>

        <div className="fx-g3 grid grid-cols-2 gap-3">
          <Field label="سکه برای معرف" hint="وقتی دعوت‌شده اولین خریدش را کند">
            <NumberStepper value={s.coins_per_referral ?? 5} onChange={(v) => upS({ coins_per_referral: v })} min={0} max={50} unit="سکه" />
          </Field>
          <Field label="سکه برای دعوت‌شده" hint="۰ یعنی چیزی نمی‌گیرد">
            <NumberStepper value={s.coins_for_invitee ?? 2} onChange={(v) => upS({ coins_for_invitee: v })} min={0} max={50} unit="سکه" />
          </Field>
        </div>

        <Field label="حداقل مبلغ خرید برای احتساب" hint="خریدهای کمتر از این، سکه نمی‌دهند">
          <input className="fx-input" dir="ltr" type="number" value={s.min_purchase_for_coin ?? 0}
            onChange={(e) => upS({ min_purchase_for_coin: Number(e.target.value) })}
            style={{ fontFamily: "var(--mono)" }} />
        </Field>

        <InfoBox tone="warn">
          سکه فقط بعد از <b>خرید واقعی</b> دعوت‌شده داده می‌شود، نه با ثبت‌نام ساده.
          این جلوی سوءاستفاده با اکانت‌های جعلی را می‌گیرد.
        </InfoBox>
      </div>

      <div className="fx-card p-5">
        <div className="flex items-center justify-between gap-3 mb-1">
          <div className="text-[14px] font-semibold text-white flex items-center gap-2">
            <Coins size={15} style={{ color: "var(--warn)" }} /> نردبان تخفیف
          </div>
          <button onClick={() => upS({ coin_tiers: [...tiers, { coins: 120, pct: 55 }] })}
            className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
            <PlusIcon size={13} /> افزودن پله
          </button>
        </div>
        <p className="text-[13px] mb-4" style={{ color: "var(--muted)" }}>
          هرچه سکه بیشتری نگه دارد، تخفیف بزرگ‌تری می‌گیرد.
        </p>

        {tiers.map((tr, i) => (
          <div key={i} className="flex items-center gap-3 mb-2.5">
            <Coins size={14} style={{ color: "var(--warn)", flexShrink: 0 }} />
            <div className="flex-1 fx-g3 grid grid-cols-2 gap-3">
              <div>
                <label className="text-[12px] mb-1 block" style={{ color: "var(--muted)" }}>سکه لازم</label>
                <input className="fx-input" dir="ltr" type="number" value={tr.coins}
                  onChange={(e) => { const l = [...tiers]; l[i] = { ...tr, coins: Number(e.target.value) }; upS({ coin_tiers: l }); }}
                  style={{ fontFamily: "var(--mono)" }} />
              </div>
              <div>
                <label className="text-[12px] mb-1 block" style={{ color: "var(--muted)" }}>درصد تخفیف</label>
                <input className="fx-input" dir="ltr" type="number" value={tr.pct}
                  onChange={(e) => { const l = [...tiers]; l[i] = { ...tr, pct: Number(e.target.value) }; upS({ coin_tiers: l }); }}
                  style={{ fontFamily: "var(--mono)" }} />
              </div>
            </div>
            <button onClick={() => upS({ coin_tiers: tiers.filter((_, x) => x !== i) })}
              className="fx-ico-btn shrink-0" style={{ width: 28, height: 28 }}><Trash2 size={13} /></button>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ===================== ربات: اینباندها ===================== */

// سه حالت انتخاب اینباند. متن‌ها عمداً توضیحی‌اند تا مدیر
// بدون خواندن مستندات بفهمد هرکدام چه اثری روی کانفیگ مشتری دارد.
const INBOUND_MODES = [
  {
    key: "all",
    title: "همه‌ی اینباندهای فعال",
    desc: "کانفیگ روی هر اینباند فعال ساخته می‌شود. اگر یکی از سرورها بیفتد، بقیه کار می‌کنند.",
    tag: "پیشنهادی",
  },
  {
    key: "default",
    title: "فقط اینباند پیش‌فرض",
    desc: "همان اینباندی که در «اتصال و تنظیمات» به‌عنوان پیش‌فرض ثبت شده.",
  },
  {
    key: "custom",
    title: "انتخاب دستی",
    desc: "خودت مشخص کن کانفیگ روی کدام اینباندها ساخته شود.",
  },
];

function InboundRow({ inb, checked, onToggle }) {
  return (
    <label className="flex items-center gap-3 p-3 rounded-xl mb-2 cursor-pointer transition-all"
      style={{
        background: checked ? "var(--accent-soft)" : "var(--surface-3)",
        border: `1px solid ${checked ? "var(--accent-2)" : "var(--border)"}`,
      }}>
      <input type="checkbox" checked={checked} onChange={() => onToggle(inb.id)}
        style={{ accentColor: "var(--accent)", flexShrink: 0 }} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[14px] font-semibold text-white truncate">{inb.remark}</span>
          {!inb.enable && (
            <span className="text-[11px] px-1.5 py-0.5 rounded"
              style={{ background: "rgba(248,113,113,.14)", color: "var(--danger)" }}>
              غیرفعال
            </span>
          )}
        </div>
        <div className="text-[12px] mt-1 flex items-center gap-2" style={{ color: "var(--muted)" }}>
          <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>
            {inb.protocol || "—"}:{inb.port ?? "—"}
          </span>
          <span style={{ opacity: 0.4 }}>•</span>
          <span>شناسه {faNum(inb.id)}</span>
        </div>
      </div>
    </label>
  );
}

function BotInboundsSection({ password }) {
  const [d, setD] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);
  const [mode, setMode] = useState("all");
  const [sel, setSel] = useState([]);

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API_URL}/api/admin/bot/inbounds`, {
        headers: { "X-Admin-Password": password },
      }).then((x) => x.json());
      setD(r);
      setMode(r.mode || "all");
      setSel(Array.isArray(r.selected) ? r.selected : []);
    } catch {
      setD({ ready: false, error: "اتصال به سرور برقرار نشد", inbounds: [] });
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [password]);
  useEffect(() => { if (msg) { const x = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(x); } }, [msg]);

  const inbounds = d?.inbounds || [];
  const toggle = (id) => setSel((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const same = (a, b) =>
    JSON.stringify([...(a || [])].sort((x, y) => x - y)) ===
    JSON.stringify([...(b || [])].sort((x, y) => x - y));
  const dirty = !!d?.ready && (mode !== (d.mode || "all") || !same(sel, d.selected));
  // بک‌اند در حالت custom با لیست خالی ۴۰۰ می‌دهد؛ جلوترش را همین‌جا می‌گیریم.
  const blocked = mode === "custom" && sel.length === 0;

  const defInb = inbounds.find((i) => String(i.id) === String(d?.default));
  const active = inbounds.filter((i) => i.enable);

  const save = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/inbounds`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ mode, ids: sel }),
      });
      const j = await res.json().catch(() => ({}));
      if (res.ok) {
        setD({ ...d, mode: j.mode ?? mode, selected: j.ids ?? sel });
        setSel(j.ids ?? sel);
        setMsg({ t: "ok", m: "تنظیم اینباندها ذخیره شد" });
      } else {
        setMsg({ t: "err", m: j.detail || "ذخیره ناموفق بود" });
      }
    } catch {
      setMsg({ t: "err", m: "اتصال برقرار نشد" });
    } finally { setSaving(false); }
  };

  if (loading) {
    return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;
  }

  return (
    <div className="fx-anim">
      <SectionHead title="اینباندها"
        desc="مشخص کن کانفیگ هر مشتری روی کدام اینباندهای پنل ساخته شود — با نام، نه با شماره."
        action={
          <div className="flex items-center gap-2">
            {dirty && <StatusChip dirty />}
            <button onClick={load} disabled={saving}
              className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
              <RefreshCw size={13} /> بازخوانی
            </button>
            <button onClick={save} disabled={saving || !d?.ready || blocked || !dirty}
              className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} ذخیره
            </button>
          </div>
        } />

      <Msg msg={msg} />

      {!d?.ready ? (
        <div className="fx-card p-5">
          <div className="text-[14px] font-semibold text-white mb-2 flex items-center gap-2">
            <AlertTriangle size={15} style={{ color: "var(--warn)" }} /> اینباندها خوانده نشد
          </div>
          <p className="text-[13px] leading-relaxed" style={{ color: "var(--dim)" }}>
            {d?.error || "اتصال پنل تنظیم نشده است."}
          </p>
          <InfoBox tone="warn">
            برای خواندن اینباندها، اول باید آدرس و رمز پنل در بخش <b>«اتصال و تنظیمات»</b> ثبت
            و تست شده باشد. بعد از آن این صفحه را دوباره باز کن.
          </InfoBox>
        </div>
      ) : (
        <>
          <div className="fx-card p-5 mb-4">
            <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2">
              <Network size={15} style={{ color: "var(--accent-2)" }} /> کانفیگ روی کدام اینباندها ساخته شود؟
            </div>
            <p className="text-[13px] mb-4" style={{ color: "var(--muted)" }}>
              پنل الان <b style={{ color: "var(--dim)" }}>{faNum(inbounds.length)}</b> اینباند دارد که{" "}
              <b style={{ color: "var(--dim)" }}>{faNum(active.length)}</b> تای آن فعال است.
            </p>

            <div className="fx-g3 grid grid-cols-3 gap-2.5">
              {INBOUND_MODES.map((m) => {
                const on = mode === m.key;
                return (
                  <button key={m.key} onClick={() => setMode(m.key)}
                    className="p-3.5 rounded-xl text-right transition-all"
                    style={{
                      background: on ? "var(--accent-soft)" : "var(--surface-3)",
                      border: `1px solid ${on ? "var(--accent-2)" : "var(--border)"}`,
                    }}>
                    <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                      <span className="shrink-0 flex items-center justify-center"
                        style={{
                          width: 15, height: 15, borderRadius: "50%",
                          border: `1.5px solid ${on ? "var(--accent-2)" : "var(--border-2)"}`,
                        }}>
                        {on && <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--accent-2)" }} />}
                      </span>
                      <span className="text-[13px] font-bold" style={{ color: on ? "var(--accent-2)" : "var(--dim)" }}>
                        {m.title}
                      </span>
                      {m.tag && (
                        <span className="text-[11px] px-1.5 py-0.5 rounded"
                          style={{ background: "rgba(52,211,153,.14)", color: "var(--ok)" }}>
                          {m.tag}
                        </span>
                      )}
                    </div>
                    <div className="text-[12px] leading-relaxed" style={{ color: "var(--muted)" }}>
                      {m.desc}
                    </div>
                  </button>
                );
              })}
            </div>

            {mode === "default" && (
              <InfoBox>
                {defInb ? (
                  <>اینباند پیش‌فرض الان <b>{defInb.remark}</b> است (
                    <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>
                      {defInb.protocol}:{defInb.port}
                    </span>). تغییرش در «اتصال و تنظیمات» انجام می‌شود.</>
                ) : (
                  <>هنوز اینباند پیش‌فرضی ثبت نشده. تا وقتی ثبت نشود ربات به اولین اینباند فعال وصل می‌شود —
                    بهتر است در «اتصال و تنظیمات» یکی را مشخص کنی.</>
                )}
              </InfoBox>
            )}
          </div>

          {mode === "custom" ? (
            <div className="fx-card p-5">
              <div className="flex items-center justify-between gap-3 mb-1 flex-wrap">
                <div className="text-[14px] font-semibold text-white flex items-center gap-2">
                  <Layers size={15} style={{ color: "var(--accent-2)" }} /> اینباندهای انتخاب‌شده
                  <span className="text-[13px] font-normal" style={{ color: "var(--muted)" }}>
                    ({faNum(sel.length)} از {faNum(inbounds.length)})
                  </span>
                </div>
                <button
                  onClick={() => setSel(sel.length === active.length ? [] : active.map((i) => i.id))}
                  className="fx-btn-g px-3 py-2 text-[13px]">
                  {sel.length === active.length ? "هیچ‌کدام" : "همه‌ی فعال‌ها"}
                </button>
              </div>
              <p className="text-[13px] mb-4" style={{ color: "var(--muted)" }}>
                اینباند غیرفعال هم قابل انتخاب است، ولی تا وقتی در پنل روشن نشود کانفیگی رویش ساخته نمی‌شود.
              </p>

              {inbounds.length === 0 ? (
                <EmptyState icon={Network} text="پنل هیچ اینباندی ندارد"
                  hint="تا وقتی در 3x-ui حداقل یک اینباند نسازید، ربات نمی‌تواند کانفیگ بسازد." />
              ) : (
                inbounds.map((i) => (
                  <InboundRow key={i.id} inb={i} checked={sel.includes(i.id)} onToggle={toggle} />
                ))
              )}

              {blocked && (
                <InfoBox tone="warn">
                  در حالت انتخاب دستی باید <b>حداقل یک اینباند</b> تیک بخورد، وگرنه ربات نمی‌تواند کانفیگ بسازد.
                </InfoBox>
              )}
            </div>
          ) : inbounds.length > 0 ? (
            <div className="fx-card p-5">
              <div className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
                <Layers size={15} style={{ color: "var(--muted)" }} /> اینباندهای پنل
              </div>
              {inbounds.map((i) => {
                const used = mode === "all" ? i.enable : String(i.id) === String(d?.default);
                return (
                  <div key={i.id} className="flex items-center gap-3 p-3 rounded-xl mb-2"
                    style={{ background: "var(--surface-3)", border: "1px solid var(--border)", opacity: used ? 1 : 0.45 }}>
                    {used
                      ? <CheckCircle2 size={15} style={{ color: "var(--ok)", flexShrink: 0 }} />
                      : <Circle size={15} style={{ color: "var(--muted)", flexShrink: 0 }} />}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[14px] font-semibold text-white truncate">{i.remark}</span>
                        {!i.enable && (
                          <span className="text-[11px] px-1.5 py-0.5 rounded"
                            style={{ background: "rgba(248,113,113,.14)", color: "var(--danger)" }}>
                            غیرفعال
                          </span>
                        )}
                      </div>
                      <div className="text-[12px] mt-1 flex items-center gap-2" style={{ color: "var(--muted)" }}>
                        <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>
                          {i.protocol || "—"}:{i.port ?? "—"}
                        </span>
                        <span style={{ opacity: 0.4 }}>•</span>
                        <span>شناسه {faNum(i.id)}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <EmptyState icon={Network} text="پنل هیچ اینباندی ندارد"
                  hint="تا وقتی در 3x-ui حداقل یک اینباند نسازید، ربات نمی‌تواند کانفیگ بسازد." />
          )}
        </>
      )}
    </div>
  );
}

/* ===================== مانیتورینگ سرور ===================== */

const LEVEL_STYLE = {
  ok: { c: "var(--ok)", bg: "rgba(52,211,153,.10)", bd: "rgba(52,211,153,.30)",
        label: "سالم", Icon: CheckCircle2 },
  warn: { c: "var(--warn)", bg: "rgba(251,191,36,.10)", bd: "rgba(251,191,36,.30)",
          label: "هشدار", Icon: AlertTriangle },
  crit: { c: "var(--danger)", bg: "rgba(248,113,113,.10)", bd: "rgba(248,113,113,.32)",
          label: "بحرانی", Icon: XCircle },
};

// بخش‌های سبک هر چند ثانیه تازه می‌شوند؛ سنگین‌ها (apt و journal)
// فقط با درخواست، چون هرکدام چند ثانیه طول می‌کشند.
const LIGHT = "cpu,memory,disk,network,xray,services,ports,processes,connections";
const HEAVY = "packages,security";

// faNum یک عدد می‌خواهد؛ برای رشته‌هایی مثل «13:45:22» یا نسخه‌ی
// کرنل باید رقم‌به‌رقم تبدیل کرد، وگرنه NaN می‌شود.
const toFaDigits = (s) =>
  String(s ?? "").replace(/[0-9]/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[d]);

function fmtUptime(s) {
  if (!s) return "—";
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600);
  if (d) return `${faNum(d)} روز و ${faNum(h)} ساعت`;
  const m = Math.floor((s % 3600) / 60);
  return h ? `${faNum(h)} ساعت و ${faNum(m)} دقیقه` : `${faNum(m)} دقیقه`;
}

function fmtSize(n) {
  if (n === null || n === undefined) return "—";
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0, v = Number(n);
  while (Math.abs(v) >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return `${faNum(v.toFixed(i ? 1 : 0))} ${u[i]}`;
}

function Gauge({ pct, color }) {
  const v = Math.max(0, Math.min(100, Number(pct) || 0));
  return (
    <div style={{ height: 6, borderRadius: 99, background: "rgba(255,255,255,.06)", overflow: "hidden" }}>
      <div style={{ width: `${v}%`, height: "100%", background: color, borderRadius: 99,
                    transition: "width .4s ease" }} />
    </div>
  );
}

function MetricCard({ m }) {
  const [open, setOpen] = useState(false);
  const s = LEVEL_STYLE[m.level] || LEVEL_STYLE.ok;
  const val = m.value === null || m.value === undefined
    ? "—"
    : (typeof m.value === "number" ? faNum(m.value) : m.value);

  return (
    <div className="fx-card p-4" style={{ borderColor: m.level === "ok" ? "var(--border)" : s.bd }}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="text-[13px]" style={{ color: "var(--dim)" }}>{m.title}</span>
        <s.Icon size={14} style={{ color: s.c, flexShrink: 0 }} />
      </div>

      <div className="flex items-baseline gap-1.5 mb-2">
        <span className="text-[24px] font-bold" style={{ color: s.c, fontFamily: "var(--mono)" }}>
          {val}
        </span>
        {m.unit && <span className="text-[13px]" style={{ color: "var(--muted)" }}>{m.unit}</span>}
      </div>

      {m.pct !== null && m.pct !== undefined && <Gauge pct={m.pct} color={s.c} />}

      {m.detail && (
        <div className="text-[12px] mt-2 leading-relaxed" style={{ color: "var(--muted)" }}>
          {m.detail}
        </div>
      )}

      {(m.why || m.hint) && (
        <>
          <button onClick={() => setOpen(!open)}
            className="text-[12px] mt-2.5 flex items-center gap-1"
            style={{ color: "var(--accent-2)" }}>
            <HelpCircle size={11} /> {open ? "بستن" : "چرا مهم است؟"}
          </button>
          {open && (
            <div className="mt-2 rounded-xl p-3 text-[12px] leading-relaxed"
              style={{ background: "rgba(255,255,255,.02)", color: "var(--dim)" }}>
              {m.why}
              {m.hint && (
                <div className="mt-2 pt-2" style={{ borderTop: "1px solid var(--border)" }}>
                  <span style={{ color: "var(--muted)" }}>چه کار کنم: </span>
                  <span dir="auto" style={{ fontFamily: "var(--mono)", color: "var(--accent-2)" }}>
                    {m.hint}
                  </span>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

const RISK_META = {
  high: { c: "var(--danger)", t: "بالا", bg: "rgba(248,113,113,.10)" },
  medium: { c: "var(--warn)", t: "متوسط", bg: "rgba(251,191,36,.10)" },
  low: { c: "var(--ok)", t: "پایین", bg: "rgba(52,211,153,.10)" },
};

/**
 * پولینگ که وقتی تب دیده نمی‌شود متوقف می‌شود.
 *
 * قبلاً صفحه‌ی مانیتورینگ هر ۵ ثانیه سرور را صدا می‌زد — حتی وقتی
 * پنل ساعت‌ها در یک تب پس‌زمینه باز مانده بود. هر فراخوانی روی سرور
 * چند subprocess اجرا می‌کند (ss، systemctl، ps)، پس این یعنی بار
 * دائمی روی همان سروری که قرار است سبک بماند.
 *
 * ms=0 یعنی پولینگ خاموش.
 */
function usePolling(fn, ms, deps = []) {
  const saved = useRef(fn);
  useEffect(() => { saved.current = fn; });

  useEffect(() => {
    if (!ms) return undefined;
    let timer = null;

    const tick = () => { if (!document.hidden) saved.current(); };
    const start = () => { if (!timer) timer = setInterval(tick, ms); };
    const stop = () => { if (timer) { clearInterval(timer); timer = null; } };

    const onVis = () => {
      if (document.hidden) { stop(); return; }
      // برگشت به تب: یک‌بار فوری تازه کن، بعد دوباره زمان‌بندی
      saved.current();
      start();
    };

    if (!document.hidden) start();
    document.addEventListener("visibilitychange", onVis);
    return () => { stop(); document.removeEventListener("visibilitychange", onVis); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ms, ...deps]);
}

/** گروه دکمه‌ی انتخاب — برای فیلترهایی که گزینه‌هایشان کم و ثابت‌اند. */
function Segmented({ value, onChange, items }) {
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

function CountChip({ label, n, color }) {
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
 * پورت‌های باز.
 *
 * قبلاً همه‌ی پورت‌ها یکجا چاپ می‌شدند و روی سرور واقعی این فهرست
 * ده‌ها ردیف می‌شد — باید تا ته صفحه اسکرول می‌کردید تا بقیه‌ی
 * مانیتورینگ را ببینید. حالا پیش‌فرض فقط چیزی را نشان می‌دهد که
 * باید به آن رسیدگی کنید؛ بقیه پشت یک دکمه است.
 */
function PortsCard({ ports }) {
  const [all, setAll] = useState(false);
  // فیلتر: روی سرور واقعی ده‌ها پورت هست و بدون فیلتر، پیداکردن
  // «آن یکی که یادم نیست چیست» یعنی چشم‌چرخاندن در کل فهرست
  const [risk, setRisk] = useState("all");
  const [scope, setScope] = useState("all");
  const [q, setQ] = useState("");
  if (!ports.length) return null;

  const high = ports.filter((p) => p.risk === "high");
  const med = ports.filter((p) => p.risk === "medium");
  const low = ports.filter((p) => p.risk !== "high" && p.risk !== "medium");

  const filtering = risk !== "all" || scope !== "all" || q.trim();
  const match = (p) => {
    if (risk === "high" && p.risk !== "high") return false;
    if (risk === "medium" && p.risk !== "medium") return false;
    if (risk === "low" && (p.risk === "high" || p.risk === "medium")) return false;
    if (scope === "public" && !p.public) return false;
    if (scope === "local" && p.public) return false;
    if (q.trim()) {
      const s = q.trim().toLowerCase();
      if (!`${p.port} ${p.proto} ${p.process} ${p.known}`.toLowerCase().includes(s))
        return false;
    }
    return true;
  };

  const risky = [...high, ...med];
  // با فیلتر فعال، همه‌ی نتایج نشان داده می‌شوند؛ بدون فیلتر، همان
  // رفتار قبلی: فقط چیزی که باید به آن رسیدگی شود
  const shown = filtering
    ? [...risky, ...low].filter(match)
    : (all ? [...risky, ...low] : risky.slice(0, 6));
  const hidden = filtering ? 0 : ports.length - shown.length;

  return (
    <div className="fx-card p-5 mb-4">
      <div className="flex items-center justify-between gap-3 mb-2 flex-wrap">
        <div className="text-[14px] font-semibold text-white flex items-center gap-2">
          <ShieldCheck size={15} style={{ color: "var(--accent-2)" }} /> پورت‌های باز
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <CountChip label="پرخطر" n={high.length} color="var(--danger)" />
          <CountChip label="متوسط" n={med.length} color="var(--warn)" />
          <CountChip label="عادی" n={low.length} color="var(--ok)" />
        </div>
      </div>

      <div className="flex items-center gap-2 flex-wrap mb-3">
        <Segmented value={risk} onChange={setRisk} items={[
          ["all", "همه"], ["high", "پرخطر"], ["medium", "متوسط"], ["low", "عادی"],
        ]} />
        <Segmented value={scope} onChange={setScope} items={[
          ["all", "هر دسترسی"], ["public", "اینترنت"], ["local", "فقط داخلی"],
        ]} />
        <div className="fx-search" style={{ width: 168 }}>
          <Search size={14} style={{ color: "var(--muted)" }} />
          <input value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="پورت یا پردازه..." />
        </div>
        {filtering && (
          <button onClick={() => { setRisk("all"); setScope("all"); setQ(""); }}
            className="fx-btn-g px-3 py-2 text-[13px]">پاک‌کردن فیلتر</button>
        )}
      </div>

      <p className="text-[13px] mb-3" style={{ color: "var(--muted)" }}>
        {risky.length === 0
          ? "هیچ پورت ناشناخته‌ای رو به اینترنت باز نیست — وضعیت تمیز است."
          : "هر پورتِ رو به اینترنت یک در است. این‌ها را بشناسید یا ببندید."}
      </p>

      {shown.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table className="fx-table">
            <thead>
              <tr><th>پورت</th><th>پروتکل</th><th>پردازه</th><th>دسترسی</th><th>ریسک</th></tr>
            </thead>
            <tbody>
              {shown.map((p, i) => {
                const r = RISK_META[p.risk] || RISK_META.low;
                return (
                  <tr key={`${p.port}-${p.proto}-${i}`}>
                    <td style={{ fontFamily: "var(--mono)", fontWeight: 600 }}>{p.port}</td>
                    <td style={{ color: "var(--muted)" }}>{p.proto}</td>
                    <td dir="ltr" style={{ color: "var(--dim)" }}>{p.process || "—"}</td>
                    <td style={{ color: p.public ? "var(--warn)" : "var(--muted)" }}>
                      {p.public ? "اینترنت" : "فقط داخلی"}
                    </td>
                    <td>
                      <span className="fx-pill" style={{ background: r.bg, color: r.c }}>
                        {r.t}{p.known ? ` · ${p.known}` : ""}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {(hidden > 0 || all) && (
        <button onClick={() => setAll(!all)}
          className="fx-btn-g w-full mt-3 py-2.5 text-[13px] flex items-center justify-center gap-1.5">
          {all
            ? <>کمتر <ChevronDown size={14} style={{ transform: "rotate(180deg)" }} /></>
            : <>نمایش همه‌ی {faNum(ports.length)} پورت <ChevronDown size={14} /></>}
        </button>
      )}
    </div>
  );
}

/**
 * اتصال‌های فعال.
 *
 * پورت باز می‌گوید چه دری باز است؛ این می‌گوید الان چه کسی از آن در
 * تو آمده. وقتی سرور کند می‌شود، اولین سؤال همین است: سهم هر IP چقدر
 * است و کدامشان غیرعادی است.
 */
function ConnectionsCard({ conn, onBlock }) {
  const [all, setAll] = useState(false);
  if (!conn || !conn.total) {
    return (
      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2">
          <Activity size={15} style={{ color: "var(--accent-2)" }} /> اتصال‌های فعال
        </div>
        <p className="text-[13px]" style={{ color: "var(--muted)" }}>
          {conn ? "الان هیچ اتصال برقراری نیست." : "این بخش روی این سرور در دسترس نیست."}
        </p>
      </div>
    );
  }

  const ips = all ? conn.byIp : conn.byIp.slice(0, 5);
  const max = conn.byIp[0]?.count || 1;

  return (
    <div className="fx-card p-5 mb-4">
      <div className="flex items-center justify-between gap-3 mb-2 flex-wrap">
        <div className="text-[14px] font-semibold text-white flex items-center gap-2">
          <Activity size={15} style={{ color: "var(--accent-2)" }} /> اتصال‌های فعال
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <CountChip label="اتصال" n={conn.total} color="var(--accent-2)" />
          <CountChip label="آی‌پی یکتا" n={conn.uniqueIps} color="var(--ok)" />
        </div>
      </div>

      {conn.heavy?.length > 0 && (
        <div className="rounded-xl p-3.5 mb-3"
          style={{ background: "rgba(251,191,36,.07)", border: "1px solid rgba(251,191,36,.22)" }}>
          <div className="text-[13px] font-semibold mb-1.5" style={{ color: "var(--warn)" }}>
            {faNum(conn.heavy.length)} آی‌پی سهم غیرعادی دارد
          </div>
          {conn.heavy.map((h) => (
            <div key={h.ip}
              className="flex items-center justify-between gap-3 py-2 flex-wrap">
              <div className="text-[13px]" style={{ color: "var(--dim)" }}>
                <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>{h.ip}</span>
                {" — "}<b>{faNum(h.count)}</b> اتصال ({faNum(h.pct)}٪ کل)
              </div>
              <button onClick={() => onBlock && onBlock(h)}
                className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
                <XCircle size={13} /> بستن این آی‌پی
              </button>
            </div>
          ))}
          <div className="text-[12px] mt-2 leading-relaxed" style={{ color: "var(--muted)" }}>
            معمولاً یعنی یک اشتراک بین چند نفر پخش شده یا کسی دارد سرور را اسکن می‌کند.
            اگر مشتری خودتان است، محدودیت <b>IP هم‌زمان</b> آن پلن را کم کنید؛
            اگر ناشناس است، ببندیدش.
          </div>
        </div>
      )}

      <div className="mb-1 text-[13px]" style={{ color: "var(--muted)" }}>
        پرمصرف‌ترین آی‌پی‌ها
      </div>
      {ips.map((x) => (
        <div key={x.ip} className="flex items-center gap-3 py-1.5">
          <span dir="ltr" className="text-[13px] shrink-0"
            style={{ fontFamily: "var(--mono)", color: "var(--dim)", width: 130 }}>
            {x.ip}
          </span>
          <div className="flex-1 rounded-full overflow-hidden" style={{ height: 7, background: "var(--surface-3)" }}>
            <div style={{
              width: `${Math.max(4, (x.count / max) * 100)}%`, height: "100%",
              background: x.pct >= 15 ? "var(--warn)" : "var(--accent-2)",
            }} />
          </div>
          <span className="text-[13px] shrink-0" style={{ fontFamily: "var(--mono)", color: "var(--dim)", width: 58, textAlign: "left" }}>
            {faNum(x.count)}
          </span>
        </div>
      ))}

      {conn.byIp.length > 5 && (
        <button onClick={() => setAll(!all)}
          className="fx-btn-g w-full mt-2.5 py-2.5 text-[13px] flex items-center justify-center gap-1.5">
          {all ? "کمتر" : `نمایش همه‌ی ${faNum(conn.byIp.length)} آی‌پی`}
          <ChevronDown size={14} style={all ? { transform: "rotate(180deg)" } : undefined} />
        </button>
      )}

      {conn.byPort?.length > 0 && (
        <div className="mt-4 pt-3.5" style={{ borderTop: "1px solid var(--border)" }}>
          <div className="text-[13px] mb-2" style={{ color: "var(--muted)" }}>
            پرترافیک‌ترین پورت‌ها
          </div>
          <div className="flex gap-1.5 flex-wrap">
            {conn.byPort.map((p) => (
              <span key={p.port} className="fx-pill"
                style={{ background: "var(--surface-3)", color: "var(--dim)" }}>
                <span style={{ fontFamily: "var(--mono)" }}>{p.port}</span>
                {" · "}{faNum(p.count)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * نمودار تاریخچه‌ی مصرف.
 *
 * SVG خام و بدون کتابخانه — یک نمودار ساده ارزش ۱۲۰ کیلوبایت وابستگی
 * را ندارد. رنگ تنها حامل معنا نیست: هر سری برچسب و عدد جداگانه دارد،
 * چون قواعد دسترسی‌پذیری می‌گویند نباید فقط با رنگ تفکیک شود.
 */
function UsageChart({ series, color, label, unit, height = 74 }) {
  const [hover, setHover] = useState(null);
  const raw = series.filter((v) => typeof v === "number");
  if (raw.length < 2) {
    return (
      <div className="text-[13px] py-6 text-center" style={{ color: "var(--muted)" }}>
        هنوز داده‌ی کافی جمع نشده — هر ۵ دقیقه یک نمونه ذخیره می‌شود.
      </div>
    );
  }

  // ۲۸۸ نقطه در چند صد پیکسل فقط دندانه‌ی بی‌معنا می‌سازد. میانگین
  // هر دسته را می‌گیریم تا روند دیده شود، نه نویز.
  const CAP = 64;
  const pts = raw.length <= CAP ? raw : (() => {
    const size = Math.ceil(raw.length / CAP);
    const out = [];
    for (let i = 0; i < raw.length; i += size) {
      const chunk = raw.slice(i, i + size);
      out.push(chunk.reduce((a, b) => a + b, 0) / chunk.length);
    }
    return out;
  })();

  const max = Math.max(...pts, 1);
  // کف نمودار صفر است تا نسبت‌ها صادقانه دیده شوند، ولی برچسب
  // «کمینه» باید کمینه‌ی واقعی داده باشد نه صفرِ کف
  const dataMin = Math.min(...raw);
  const min = 0;
  const span = max - min || 1;
  const W = 100;
  const xy = (v, i) => [
    (i / (pts.length - 1)) * W,
    height - ((v - min) / span) * (height - 8) - 4,
  ];
  const line = pts.map((v, i) => xy(v, i).join(",")).join(" ");
  const area = `0,${height} ${line} ${W},${height}`;
  const cur = hover !== null ? pts[hover] : pts[pts.length - 1];

  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5">
        <span className="text-[13px]" style={{ color: "var(--muted)" }}>{label}</span>
        <span className="text-[16px] font-bold" style={{ color, fontFamily: "var(--mono)" }}>
          {faNum(Math.round(cur))}
          <span className="text-[12px] font-normal mr-1" style={{ color: "var(--muted)" }}>{unit}</span>
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${height}`} preserveAspectRatio="none"
        style={{ width: "100%", height, display: "block" }}
        role="img" aria-label={`${label}: بیشینه ${Math.round(max)} ${unit}`}
        onMouseLeave={() => setHover(null)}
        onMouseMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          const p = (e.clientX - r.left) / r.width;
          setHover(Math.min(pts.length - 1, Math.max(0, Math.round(p * (pts.length - 1)))));
        }}>
        <polygon points={area} fill={color} opacity="0.13" />
        <polyline points={line} fill="none" stroke={color} strokeWidth="1.4"
          vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
        {hover !== null && (
          <circle cx={xy(pts[hover], hover)[0]} cy={xy(pts[hover], hover)[1]}
            r="2.5" fill={color} vectorEffect="non-scaling-stroke" />
        )}
      </svg>
      <div className="flex justify-between text-[12px] mt-1" style={{ color: "var(--muted)" }}>
        <span>کمینه {faNum(Math.round(dataMin))}</span>
        <span>بیشینه {faNum(Math.round(Math.max(...raw)))}</span>
      </div>
    </div>
  );
}

/** نوار ۲۴ ساعته — کدام ساعت شبانه‌روز شلوغ است و کدام خلوت. */
function HourStrip({ hourly, quietest, busiest }) {
  if (!hourly?.length) return null;
  const max = Math.max(...hourly.map((h) => h.conn), 1);
  const byHour = Object.fromEntries(hourly.map((h) => [h.hour, h]));

  return (
    <div>
      <div className="flex items-end gap-[2px]" style={{ height: 52 }}>
        {Array.from({ length: 24 }, (_, h) => {
          const d = byHour[h];
          const v = d ? d.conn : 0;
          const isQuiet = h === quietest;
          const isBusy = h === busiest;
          return (
            <div key={h} className="flex-1 rounded-t-[3px]" title={
              d ? `ساعت ${h} — میانگین ${Math.round(v)} اتصال` : `ساعت ${h} — داده‌ای نیست`}
              style={{
                height: `${Math.max(3, (v / max) * 100)}%`,
                background: isBusy ? "var(--danger)"
                  : isQuiet ? "var(--ok)"
                    : d ? "var(--accent-2)" : "var(--surface-3)",
                opacity: d ? (isBusy || isQuiet ? 1 : 0.55) : 0.35,
              }} />
          );
        })}
      </div>
      <div className="flex justify-between text-[12px] mt-1.5" style={{ color: "var(--muted)" }}>
        <span>۰۰</span><span>۰۶</span><span>۱۲</span><span>۱۸</span><span>۲۳</span>
      </div>
    </div>
  );
}

function UsageHistoryCard({ password }) {
  const [d, setD] = useState(null);

  useEffect(() => {
    let alive = true;
    fetch(`${API_URL}/api/admin/usage-history?hours=24`, {
      headers: { "X-Admin-Password": password },
    }).then((r) => r.json()).then((j) => alive && setD(j)).catch(() => alive && setD({}));
    return () => { alive = false; };
  }, [password]);

  if (!d) return null;
  const s = d.samples || [];

  return (
    <div className="fx-card p-5 mb-4">
      <div className="flex items-center justify-between gap-3 mb-1 flex-wrap">
        <div className="text-[14px] font-semibold text-white flex items-center gap-2">
          <TrendingUp size={15} style={{ color: "var(--accent-2)" }} /> تاریخچه‌ی مصرف
        </div>
        <span className="text-[13px]" style={{ color: "var(--muted)" }}>
          {faNum(d.count || 0)} نمونه از ۲۴ ساعت گذشته
        </span>
      </div>
      <p className="text-[13px] mb-4" style={{ color: "var(--muted)" }}>
        هر ۵ دقیقه یک نمونه. تا وقتی چند ساعت جمع نشود، الگو معنا ندارد.
      </p>

      {s.length >= 2 ? (
        <>
          <div className="fx-g3 grid grid-cols-2 gap-5 mb-5">
            <UsageChart series={s.map((x) => x.conn)} color="var(--accent-2)"
              label="اتصال‌های هم‌زمان" unit="اتصال" />
            <UsageChart series={s.map((x) => x.cpu)} color="var(--warn)"
              label="پردازنده" unit="٪" />
          </div>

          <div className="pt-4" style={{ borderTop: "1px solid var(--border)" }}>
            <div className="text-[13px] mb-2" style={{ color: "var(--muted)" }}>
              میانگین هر ساعت شبانه‌روز
            </div>
            <HourStrip hourly={d.hourly} quietest={d.quietestHour} busiest={d.busiestHour} />

            {d.quietestHour !== null && d.quietestHour !== undefined && (
              <div className="flex gap-3 flex-wrap mt-3 text-[13px]">
                <span style={{ color: "var(--ok)" }}>
                  ● خلوت‌ترین ساعت: <b>{faNum(d.quietestHour)}</b>
                </span>
                <span style={{ color: "var(--danger)" }}>
                  ● شلوغ‌ترین ساعت: <b>{faNum(d.busiestHour)}</b>
                </span>
              </div>
            )}
            {d.quietestHour !== null && d.quietestHour !== undefined && (
              <InfoBox>
                بر اساس همین داده، ساعت <b>{faNum(d.quietestHour)}</b> کم‌مصرف‌ترین
                زمان سرور شماست — اگر نگهداری خودکار را روشن کردید، همان را انتخاب کنید.
              </InfoBox>
            )}
          </div>
        </>
      ) : (
        <div className="text-[13px] py-6 text-center" style={{ color: "var(--muted)" }}>
          هنوز نمونه‌ای ذخیره نشده. چند ساعت بعد از به‌روزرسانی دوباره سر بزنید.
        </div>
      )}
    </div>
  );
}

/** پرمصرف‌ترین مشتری‌ها — بر اساس ترافیک واقعی پنل، نه شمارش اتصال. */
function TopClientsCard({ password }) {
  const [d, setD] = useState(null);
  const [all, setAll] = useState(false);

  useEffect(() => {
    let alive = true;
    fetch(`${API_URL}/api/admin/top-clients?limit=25`, {
      headers: { "X-Admin-Password": password },
    }).then((r) => r.json()).then((j) => alive && setD(j)).catch(() => alive && setD({ ready: false }));
    return () => { alive = false; };
  }, [password]);

  if (!d) return null;

  if (!d.ready) {
    return (
      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2">
          <Users size={15} style={{ color: "var(--accent-2)" }} /> پرمصرف‌ترین مشتری‌ها
        </div>
        <p className="text-[13px]" style={{ color: "var(--muted)" }}>
          {d.error || "دیتابیس پنل در دسترس نیست."}
        </p>
      </div>
    );
  }

  const list = all ? d.clients : (d.clients || []).slice(0, 6);
  const max = d.clients?.[0]?.usedGB || 1;

  return (
    <div className="fx-card p-5 mb-4">
      <div className="flex items-center justify-between gap-3 mb-1 flex-wrap">
        <div className="text-[14px] font-semibold text-white flex items-center gap-2">
          <Users size={15} style={{ color: "var(--accent-2)" }} /> پرمصرف‌ترین مشتری‌ها
        </div>
        <span className="text-[13px]" style={{ color: "var(--muted)" }}>
          {faNum(d.totalClients || 0)} کانفیگ · {faNum(d.totalUsedGB || 0)} گیگ کل
        </span>
      </div>
      <p className="text-[13px] mb-3" style={{ color: "var(--muted)" }}>
        بر اساس ترافیک واقعی پنل — این می‌گوید کدام <b>مشتری</b> بار می‌آورد،
        نه فقط کدام آی‌پی.
      </p>

      {!list.length ? (
        <EmptyState icon={Users} text="هنوز مصرفی ثبت نشده"
          hint="کانفیگ‌ها ساخته شده‌اند ولی هنوز ترافیکی از آن‌ها عبور نکرده." />
      ) : list.map((c) => (
        <div key={c.email} className="py-2">
          <div className="flex items-baseline justify-between gap-2 mb-1 flex-wrap">
            <span dir="ltr" className="text-[13px] truncate"
              style={{ fontFamily: "var(--mono)", color: "var(--dim)", maxWidth: "60%" }}>
              {c.email}
            </span>
            <span className="text-[13px]" style={{ color: "var(--dim)" }}>
              <b style={{ fontFamily: "var(--mono)" }}>{faNum(c.usedGB)}</b> گیگ
              {c.quotaGB ? <span style={{ color: "var(--muted)" }}> از {faNum(c.quotaGB)}</span> : null}
              <span style={{ color: "var(--muted)" }}> · {faNum(c.pctOfAll)}٪ کل</span>
            </span>
          </div>
          <div className="rounded-full overflow-hidden" style={{ height: 7, background: "var(--surface-3)" }}>
            <div style={{
              width: `${Math.max(3, (c.usedGB / max) * 100)}%`, height: "100%",
              background: !c.enable ? "var(--muted)"
                : (c.pctOfQuota !== null && c.pctOfQuota >= 90) ? "var(--danger)"
                  : c.pctOfAll >= 20 ? "var(--warn)" : "var(--accent-2)",
            }} />
          </div>
          {(!c.enable || (c.pctOfQuota !== null && c.pctOfQuota >= 90)) && (
            <div className="text-[12px] mt-1" style={{ color: !c.enable ? "var(--muted)" : "var(--danger)" }}>
              {!c.enable ? "غیرفعال" : `${faNum(c.pctOfQuota)}٪ از حجمش مصرف شده — نزدیک تمام‌شدن`}
            </div>
          )}
        </div>
      ))}

      {(d.clients || []).length > 6 && (
        <button onClick={() => setAll(!all)}
          className="fx-btn-g w-full mt-3 py-2.5 text-[13px] flex items-center justify-center gap-1.5">
          {all ? "کمتر" : `نمایش همه‌ی ${faNum(d.clients.length)} مشتری`}
          <ChevronDown size={14} style={all ? { transform: "rotate(180deg)" } : undefined} />
        </button>
      )}
    </div>
  );
}

const WEEKDAYS = [["دوشنبه", 0], ["سه‌شنبه", 1], ["چهارشنبه", 2],
                  ["پنجشنبه", 3], ["جمعه", 4], ["شنبه", 5], ["یکشنبه", 6]];

/**
 * نگهداری خودکار.
 *
 * ری‌استارت Xray حدود یک ثانیه قطعی دارد؛ ریبوت سرور یک تا دو دقیقه.
 * برای همین ریبوت پشت یک تایید جداگانه است — یک تیک اشتباهی نباید
 * بتواند سرور فروش را وسط شب بخواباند.
 */
function MaintenanceCard({ password }) {
  const [m, setM] = useState(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);
  const [confirmReboot, setConfirmReboot] = useState(false);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/maintenance`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setM(d);
    } catch { setM({ error: true }); }
  };
  useEffect(() => { load(); }, [password]);
  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(t); } }, [msg]);

  if (!m) return null;

  const up = (patch) => setM({ ...m, ...patch });

  const save = async (extra = {}) => {
    setSaving(true);
    try {
      const body = { ...m, ...extra };
      const res = await fetch(`${API_URL}/api/admin/maintenance`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify(body),
      });
      const j = await res.json().catch(() => ({}));
      if (res.ok) { setM(j); setMsg({ t: "ok", m: "زمان‌بندی ذخیره شد" }); await load(); }
      else setMsg({ t: "err", m: j.detail || "ذخیره ناموفق" });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setSaving(false); }
  };

  const runNow = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/maintenance/run-now`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ action: "xray" }),
      });
      const j = await res.json().catch(() => ({}));
      setMsg({ t: j.ok ? "ok" : "err", m: j.note || j.detail || "انجام شد" });
      await load();
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setSaving(false); }
  };

  const isReboot = m.action === "reboot";

  return (
    <div className="fx-card p-5 mb-4">
      <div className="flex items-center justify-between gap-3 mb-1 flex-wrap">
        <div className="text-[14px] font-semibold text-white flex items-center gap-2">
          <RefreshCw size={15} style={{ color: "var(--accent-2)" }} /> نگهداری خودکار
        </div>
        <Toggle checked={!!m.enabled} onChange={(v) => up({ enabled: v })}
          label={m.enabled ? "روشن" : "خاموش"} />
      </div>
      <p className="text-[13px] mb-4" style={{ color: "var(--muted)" }}>
        در ساعت کم‌مصرف، سرویس را تازه می‌کند تا نشتی حافظه و نشست‌های
        مرده جمع نشوند.
      </p>

      <Msg msg={msg} />

      <div className="fx-g3 grid grid-cols-2 gap-2.5 mb-3">
        {[["ری‌استارت Xray", "xray", "حدود ۱ ثانیه قطعی", "var(--ok)"],
          ["ریبوت کامل سرور", "reboot", "۱ تا ۲ دقیقه قطعی", "var(--warn)"]].map(
          ([label, val, note, col]) => {
            const on = m.action === val;
            return (
              <button key={val} onClick={() => up({ action: val })}
                className="p-3.5 rounded-xl text-right transition-all"
                style={{
                  background: on ? "var(--accent-soft)" : "var(--surface-3)",
                  border: `1px solid ${on ? "var(--accent-2)" : "var(--border)"}`,
                }}>
                <div className="text-[13px] font-bold mb-1"
                  style={{ color: on ? "var(--accent-2)" : "var(--dim)" }}>{label}</div>
                <div className="text-[12px]" style={{ color: col }}>{note}</div>
              </button>
            );
          })}
      </div>

      <div className="fx-g3 grid grid-cols-2 gap-3 mb-3">
        <Field label="ساعت" hint="به وقت سرور">
          <input className="fx-input" dir="ltr" type="number" min="0" max="23"
            value={m.hour ?? 5} onChange={(e) => up({ hour: Number(e.target.value) })}
            style={{ fontFamily: "var(--mono)" }} />
        </Field>
        <Field label="دقیقه">
          <input className="fx-input" dir="ltr" type="number" min="0" max="59"
            value={m.minute ?? 0} onChange={(e) => up({ minute: Number(e.target.value) })}
            style={{ fontFamily: "var(--mono)" }} />
        </Field>
      </div>

      <div className="mb-3">
        <label className="text-[12px] mb-1.5 block" style={{ color: "var(--muted)" }}>
          روزها — چیزی انتخاب نکنید یعنی هر روز
        </label>
        <div className="flex gap-1.5 flex-wrap">
          {WEEKDAYS.map(([label, d]) => {
            const on = (m.days || []).includes(d);
            return (
              <button key={d}
                onClick={() => up({ days: on ? m.days.filter((x) => x !== d)
                                              : [...(m.days || []), d] })}
                className="px-3 py-2 rounded-lg text-[13px]"
                style={{
                  background: on ? "var(--accent-soft)" : "var(--surface-3)",
                  border: `1px solid ${on ? "var(--accent-2)" : "var(--border)"}`,
                  color: on ? "var(--accent-2)" : "var(--muted)",
                }}>{label}</button>
            );
          })}
        </div>
      </div>

      <label className="flex items-center gap-2 text-[13px] cursor-pointer mb-3"
        style={{ color: "var(--dim)" }}>
        <input type="checkbox" checked={!!m.skipIfBusy}
          onChange={(e) => up({ skipIfBusy: e.target.checked })}
          style={{ accentColor: "var(--accent)" }} />
        اگر بیش از {faNum(m.busyThreshold || 20)} اتصال فعال بود، آن شب رد شود
      </label>

      {isReboot && (
        <InfoBox tone="warn">
          ریبوت کامل یعنی <b>همه‌ی مشتری‌ها یک تا دو دقیقه قطع می‌شوند</b>.
          برای نشتی حافظه معمولاً ری‌استارت Xray کافی است.
          <label className="flex items-center gap-2 mt-2.5 cursor-pointer">
            <input type="checkbox" checked={confirmReboot}
              onChange={(e) => setConfirmReboot(e.target.checked)}
              style={{ accentColor: "var(--warn)" }} />
            می‌دانم و ریبوت خودکار را می‌خواهم
          </label>
        </InfoBox>
      )}

      <div className="flex items-center gap-2 mt-4 flex-wrap">
        <button onClick={() => save({ confirmedReboot: isReboot ? confirmReboot : m.confirmedReboot })}
          disabled={saving || (m.enabled && isReboot && !confirmReboot)}
          className="fx-btn px-4 py-2.5 text-[13px] flex items-center gap-1.5">
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} ذخیره
        </button>
        <button onClick={runNow} disabled={saving}
          className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
          <Zap size={13} /> همین حالا Xray را تازه کن
        </button>
      </div>

      <div className="mt-3.5 pt-3 text-[13px] leading-relaxed"
        style={{ borderTop: "1px solid var(--border)", color: "var(--muted)" }}>
        {m.enabled && m.nextRun
          ? <>اجرای بعدی: <b style={{ color: "var(--dim)" }}>{m.nextRun.replace("T", " ساعت ")}</b></>
          : "زمان‌بندی خاموش است."}
        {m.lastResult && <div className="mt-1">آخرین بار: {m.lastResult}</div>}
        {typeof m.activeConnections === "number" && (
          <div className="mt-1">الان {faNum(m.activeConnections)} اتصال فعال است.</div>
        )}
      </div>
    </div>
  );
}

/* ===================== فایروال ===================== */

const FW_ACTIONS = [
  ["allow", "اجازه", "var(--ok)"],
  ["deny", "مسدود", "var(--danger)"],
  ["limit", "محدود", "var(--warn)"],
];

function useFirewall(password) {
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API_URL}/api/admin/firewall`, {
        headers: { "X-Admin-Password": password },
      }).then((x) => x.json());
      setD(r);
    } catch { setD({ ready: false, error: "اتصال به سرور برقرار نشد", rules: [] }); }
  }, [password]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 5000); return () => clearTimeout(t); } }, [msg]);

  const call = async (path, opts = {}) => {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}${path}`, {
        ...opts,
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Password": password, ...(opts.headers || {}),
        },
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) { setMsg({ t: "err", m: j.detail || "عملیات ناموفق" }); return null; }
      setMsg({ t: "ok", m: j.note || "انجام شد" });
      if (j.rules) setD(j); else await load();
      return j;
    } catch {
      setMsg({ t: "err", m: "اتصال برقرار نشد" });
      return null;
    } finally { setBusy(false); }
  };

  return { d, busy, msg, setMsg, load, call };
}

function FirewallRules({ password }) {
  const { d, busy, msg, call } = useFirewall(password);
  const [form, setForm] = useState({ port: "", proto: "tcp", action: "allow", comment: "" });
  const [confirmSsh, setConfirmSsh] = useState(false);
  const [q, setQ] = useState("");
  const [confirmDel, setConfirmDel] = useState(null);

  if (!d) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  if (!d.installed) {
    return (
      <div className="fx-anim">
        <SectionHead title="فایروال" desc="کنترل اینکه چه کسی از بیرون به سرور دسترسی دارد." />
        <div className="fx-card p-5">
          <div className="text-[14px] font-semibold text-white mb-2 flex items-center gap-2">
            <AlertTriangle size={15} style={{ color: "var(--warn)" }} /> ufw نصب نیست
          </div>
          <p className="text-[13px] leading-relaxed" style={{ color: "var(--dim)" }}>
            این صفحه با <b>ufw</b> کار می‌کند که روی اوبونتو و دبیان استاندارد است.
            روی سرور اجرا کنید و صفحه را تازه کنید:
          </p>
          <div className="mt-3 rounded-xl p-3.5" style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
            <code dir="ltr" className="text-[13px]" style={{ fontFamily: "var(--mono)", color: "var(--accent-2)" }}>
              apt update &amp;&amp; apt install -y ufw
            </code>
          </div>
          <InfoBox tone="warn">
            بعد از نصب، <b>قبل از روشن‌کردن فایروال</b> حتماً قاعده‌ی SSH را اضافه کنید،
            وگرنه دسترسی خودتان به سرور قطع می‌شود.
          </InfoBox>
        </div>
      </div>
    );
  }

  const rules = (d.rules || []).filter((r) => {
    if (!q.trim()) return true;
    const s = q.trim().toLowerCase();
    return `${r.target} ${r.source} ${r.action}`.toLowerCase().includes(s);
  });

  const add = () => {
    if (!form.port) return;
    call("/api/admin/firewall/rule", {
      method: "POST", body: JSON.stringify(form),
    }).then((j) => { if (j) setForm({ ...form, port: "", comment: "" }); });
  };

  return (
    <div className="fx-anim">
      <SectionHead title="قواعد فایروال"
        desc="هر قاعده یک در است که باز یا بسته می‌گذارید. چیزی که لازم ندارید را ببندید."
        action={
          <div className="flex items-center gap-2">
            <span className="fx-pill" style={{
              background: d.active ? "rgba(52,211,153,.14)" : "rgba(248,113,113,.14)",
              color: d.active ? "var(--ok)" : "var(--danger)",
            }}>
              {d.active ? "روشن" : "خاموش"}
            </span>
            <button
              onClick={() => call("/api/admin/firewall/toggle", {
                method: "POST",
                body: JSON.stringify({ enable: !d.active, confirmSsh }),
              })}
              disabled={busy}
              className={d.active ? "fx-btn-g px-4 py-2.5 text-[13px]" : "fx-btn px-4 py-2.5 text-[13px]"}>
              {busy ? <Loader2 size={14} className="animate-spin" /> : (d.active ? "خاموش کن" : "روشن کن")}
            </button>
          </div>
        } />

      <Msg msg={msg} />

      {!d.active && (
        <div className="fx-card p-5 mb-4" style={{ borderColor: "rgba(251,191,36,.3)" }}>
          <div className="text-[14px] font-semibold mb-2 flex items-center gap-2" style={{ color: "var(--warn)" }}>
            <AlertTriangle size={15} /> فایروال خاموش است
          </div>
          <p className="text-[13px] leading-relaxed" style={{ color: "var(--dim)" }}>
            یعنی همه‌ی پورت‌های باز سرور از تمام اینترنت در دسترس‌اند.
          </p>
          {!d.sshProtected && (
            <>
              <InfoBox tone="warn">
                <b>هیچ قاعده‌ای پورت ۲۲ (SSH) را باز نگذاشته.</b> اگر همین حالا
                فایروال را روشن کنید، دسترسی خودتان به سرور قطع می‌شود و فقط از
                کنسول ارائه‌دهنده می‌توانید برگردید. اول قاعده‌ی SSH را اضافه کنید.
              </InfoBox>
              <label className="flex items-center gap-2 text-[13px] cursor-pointer mt-3" style={{ color: "var(--dim)" }}>
                <input type="checkbox" checked={confirmSsh}
                  onChange={(e) => setConfirmSsh(e.target.checked)}
                  style={{ accentColor: "var(--warn)" }} />
                می‌دانم و با همین وضع روشن کن
              </label>
            </>
          )}
        </div>
      )}

      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
          <Plus size={15} style={{ color: "var(--accent-2)" }} /> قاعده‌ی جدید
        </div>
        <div className="fx-g4 grid grid-cols-4 gap-3">
          <Field label="پورت">
            <input className="fx-input" dir="ltr" type="number" min="1" max="65535"
              value={form.port} placeholder="۴۴۳"
              onChange={(e) => setForm({ ...form, port: e.target.value })}
              style={{ fontFamily: "var(--mono)" }} />
          </Field>
          <Field label="پروتکل">
            <select className="fx-input" value={form.proto}
              onChange={(e) => setForm({ ...form, proto: e.target.value })}>
              <option value="tcp">TCP</option>
              <option value="udp">UDP</option>
              <option value="any">هر دو</option>
            </select>
          </Field>
          <Field label="عمل">
            <select className="fx-input" value={form.action}
              onChange={(e) => setForm({ ...form, action: e.target.value })}>
              {FW_ACTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </Field>
          <Field label="توضیح" hint="اختیاری">
            <input className="fx-input" value={form.comment} placeholder="پنل"
              onChange={(e) => setForm({ ...form, comment: e.target.value })} />
          </Field>
        </div>
        <button onClick={add} disabled={busy || !form.port}
          className="fx-btn px-4 py-2.5 text-[13px] flex items-center gap-1.5 mt-3">
          <Plus size={14} /> افزودن قاعده
        </button>
      </div>

      <div className="fx-card p-5">
        <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
          <div className="text-[14px] font-semibold text-white flex items-center gap-2">
            <ShieldCheck size={15} style={{ color: "var(--accent-2)" }} /> قواعد فعلی
            <span className="text-[13px] font-normal" style={{ color: "var(--muted)" }}>
              ({faNum(rules.length)})
            </span>
          </div>
          <div className="fx-search" style={{ width: 200 }}>
            <Search size={14} style={{ color: "var(--muted)" }} />
            <input value={q} onChange={(e) => setQ(e.target.value)}
              placeholder="جستجو در قواعد..." />
          </div>
        </div>

        {!rules.length ? (
          <EmptyState icon={ShieldCheck} text={q ? "چیزی پیدا نشد" : "هنوز قاعده‌ای ثبت نشده"} />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="fx-table">
              <thead>
                <tr><th>#</th><th>مقصد</th><th>عمل</th><th>مبدأ</th><th></th></tr>
              </thead>
              <tbody>
                {rules.map((r) => {
                  const meta = FW_ACTIONS.find(([v]) => v === r.action.toLowerCase());
                  return (
                    <tr key={r.num}>
                      <td style={{ fontFamily: "var(--mono)", color: "var(--muted)" }}>{faNum(r.num)}</td>
                      <td dir="ltr" style={{ fontFamily: "var(--mono)" }}>
                        {r.target}
                        {r.critical && (
                          <span className="fx-pill mr-2" style={{ background: "rgba(251,191,36,.14)", color: "var(--warn)" }}>
                            حیاتی
                          </span>
                        )}
                      </td>
                      <td style={{ color: meta ? meta[2] : "var(--dim)" }}>
                        {meta ? meta[1] : r.action}
                      </td>
                      <td dir="ltr" style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                        {r.source}
                      </td>
                      <td>
                        <button onClick={() => setConfirmDel(r)} disabled={busy}
                          className="fx-ico-btn" aria-label={`حذف قاعده ${r.num}`}
                          style={{ width: 30, height: 30 }}>
                          <Trash2 size={13} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {r_note(d)}
      </div>

      {confirmDel && (
        <ConfirmModal
          title={`حذف قاعده #${faNum(confirmDel.num)}؟`}
          desc={confirmDel.critical
            ? `${confirmDel.note} — حذفش می‌تواند دسترسی شما به سرور را قطع کند.`
            : `قاعده‌ی ${confirmDel.target} (${confirmDel.action}) حذف می‌شود.`}
          confirmLabel="حذف کن"
          onCancel={() => setConfirmDel(null)}
          onConfirm={() => {
            call(`/api/admin/firewall/rule/${confirmDel.num}?confirm=1`,
                 { method: "DELETE" });
            setConfirmDel(null);
          }} />
      )}
    </div>
  );
}

/** یادداشت پایین جدول قواعد — وضعیت پیش‌فرض ورودی. */
function r_note(d) {
  if (!d?.defaultIncoming || d.defaultIncoming === "?") return null;
  const deny = d.defaultIncoming === "deny";
  return (
    <div className="text-[13px] mt-3 pt-3 leading-relaxed"
      style={{ borderTop: "1px solid var(--border)", color: "var(--muted)" }}>
      سیاست پیش‌فرض ورودی: <b style={{ color: deny ? "var(--ok)" : "var(--warn)" }}>
        {deny ? "مسدود" : "باز"}
      </b>
      {deny
        ? " — یعنی هرچه در فهرست بالا نیست، بسته است. این حالت درست است."
        : " — یعنی هر پورتی که قاعده‌ی مسدود ندارد، باز است."}
    </div>
  );
}

function FirewallBlocked({ password }) {
  const { d, busy, msg, call } = useFirewall(password);
  const [ip, setIp] = useState("");

  if (!d) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  const blocked = (d.rules || []).filter(
    (r) => r.action === "DENY" && r.source && r.source !== "Anywhere");

  return (
    <div className="fx-anim">
      <SectionHead title="آی‌پی‌های بسته‌شده"
        desc="آی‌پی‌هایی که کامل از سرور کنار گذاشته شده‌اند." />

      <Msg msg={msg} />

      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
          <XCircle size={15} style={{ color: "var(--danger)" }} /> بستن یک آی‌پی
        </div>
        <div className="flex gap-2 flex-wrap items-end">
          <div className="flex-1" style={{ minWidth: 200 }}>
            <Field label="آدرس آی‌پی" hint="مثلاً ۹۱٫۹۹٫۱۲٫۴ یا یک رنج مثل 91.99.12.0/24">
              <input className="fx-input" dir="ltr" value={ip}
                onChange={(e) => setIp(e.target.value)} placeholder="91.99.12.4"
                style={{ fontFamily: "var(--mono)" }} />
            </Field>
          </div>
          <button
            onClick={() => call("/api/admin/firewall/block-ip", {
              method: "POST", body: JSON.stringify({ ip }),
            }).then((j) => { if (j) setIp(""); })}
            disabled={busy || !ip.trim()}
            className="fx-btn px-4 py-2.5 text-[13px] flex items-center gap-1.5">
            <XCircle size={14} /> ببند
          </button>
        </div>
        {!d.active && (
          <InfoBox tone="warn">
            فایروال خاموش است، پس این قاعده‌ها فعلاً اثری ندارند. از صفحه‌ی
            «قواعد فایروال» روشنش کنید.
          </InfoBox>
        )}
      </div>

      <div className="fx-card p-5">
        <div className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
          <XCircle size={15} style={{ color: "var(--muted)" }} /> فهرست بسته‌شده‌ها
          <span className="text-[13px] font-normal" style={{ color: "var(--muted)" }}>
            ({faNum(blocked.length)})
          </span>
        </div>
        {!blocked.length ? (
          <EmptyState icon={ShieldCheck} text="هیچ آی‌پی‌ای بسته نشده" />
        ) : blocked.map((r) => (
          <div key={r.num} className="flex items-center justify-between gap-3 p-3 rounded-xl mb-2"
            style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
            <span dir="ltr" className="text-[13px]" style={{ fontFamily: "var(--mono)", color: "var(--dim)" }}>
              {r.source}
            </span>
            <button
              onClick={() => call("/api/admin/firewall/block-ip", {
                method: "POST",
                body: JSON.stringify({ ip: r.source, unblock: true }),
              })}
              disabled={busy}
              className="fx-btn-g px-3 py-2 text-[13px]">
              باز کن
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ===================== گزارش فروش ربات ===================== */

const REPORT_RANGES = [[7, "۷ روز"], [30, "۳۰ روز"], [90, "۹۰ روز"], [365, "یک سال"]];

function StatTile({ label, value, unit, hint, color = "var(--text)" }) {
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

/**
 * گزارش فروش ربات.
 *
 * حسابداری می‌گوید از هر واسطه چقدر طلب دارید؛ این می‌گوید فروش
 * مستقیم ربات در یک دوره چه شکلی بوده — چند نفر آمدند، چند درصدشان
 * خریدند، و چه کسانی بیشترین سهم را داشتند.
 */
function BotReportSection({ password }) {
  const [days, setDays] = useState(30);
  const [d, setD] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    fetch(`${API_URL}/api/admin/bot/users/report?days=${days}`, {
      headers: { "X-Admin-Password": password },
    }).then((r) => r.json())
      .then((j) => { if (alive) { setD(j); setLoading(false); } })
      .catch(() => { if (alive) { setD({ ready: false }); setLoading(false); } });
    return () => { alive = false; };
  }, [password, days]);

  const download = () => {
    const a = document.createElement("a");
    a.href = `${API_URL}/api/admin/bot/users/export`;
    a.click();
  };

  if (loading) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  if (!d?.ready) {
    return (
      <div className="fx-anim">
        <SectionHead title="گزارش فروش" desc="خلاصه‌ی عملکرد ربات در یک بازه." />
        <div className="fx-card p-5">
          <p className="text-[13px]" style={{ color: "var(--dim)" }}>
            {d?.error || "دیتابیس ربات در دسترس نیست."}
          </p>
        </div>
      </div>
    );
  }

  const o = d.orders || {};
  const u = d.users || {};
  const s = d.subs || {};
  const maxDay = Math.max(...(d.daily || []).map((x) => x.sum), 1);

  return (
    <div className="fx-anim">
      <SectionHead title="گزارش فروش"
        desc="عملکرد ربات در بازه‌ی انتخابی — چند نفر آمدند، چند نفر خریدند، چقدر فروش رفت."
        action={
          <div className="flex items-center gap-2 flex-wrap">
            <Segmented value={days} onChange={setDays}
              items={REPORT_RANGES.map(([v, l]) => [v, l])} />
            <button onClick={download}
              className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
              <Download size={13} /> خروجی اکسل
            </button>
          </div>
        } />

      <div className="fx-g4 grid grid-cols-4 gap-3 mb-4">
        <StatTile label="فروش دوره" value={faNum(o.revenue || 0)} unit="تومان"
          color="var(--ok)"
          hint={o.approved ? `${faNum(o.approved)} سفارش · میانگین ${faNum(o.avg)}` : "سفارشی نبوده"} />
        <StatTile label="کاربر جدید" value={faNum(u.newUsers || 0)} unit="نفر"
          hint={`از ${faNum(u.users || 0)} کاربر کل`} />
        <StatTile label="خریدار" value={faNum(d.buyerCount || 0)} unit="نفر"
          color="var(--accent-2)"
          hint={d.conversion !== null && d.conversion !== undefined
            ? `نرخ تبدیل ${faNum(d.conversion)}٪ از کاربران جدید`
            : "کاربر جدیدی نبوده"} />
        <StatTile label="اشتراک فعال" value={faNum(s.active || 0)}
          color={s.expiringSoon ? "var(--warn)" : "var(--text)"}
          hint={s.expiringSoon
            ? `${faNum(s.expiringSoon)} تا کمتر از ۳ روز اعتبار دارد`
            : `از ${faNum(s.total || 0)} اشتراک کل`} />
      </div>

      {(o.pending > 0 || o.rejected > 0) && (
        <div className="fx-card p-5 mb-4">
          <div className="flex gap-4 flex-wrap text-[13px]">
            {o.pending > 0 && (
              <span style={{ color: "var(--warn)" }}>
                ⏳ <b>{faNum(o.pending)}</b> رسید منتظر بررسی شماست
              </span>
            )}
            {o.rejected > 0 && (
              <span style={{ color: "var(--muted)" }}>
                {faNum(o.rejected)} سفارش در این دوره رد شده
              </span>
            )}
          </div>
        </div>
      )}

      {(d.daily || []).length > 1 && (
        <div className="fx-card p-5 mb-4">
          <div className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
            <TrendingUp size={15} style={{ color: "var(--accent-2)" }} /> فروش روزانه
          </div>
          <div className="flex items-end gap-[3px]" style={{ height: 90 }}>
            {d.daily.map((x) => (
              <div key={x.day} className="flex-1 rounded-t-[3px]"
                title={`${x.day} — ${faNum(x.sum)} تومان از ${faNum(x.n)} سفارش`}
                style={{
                  height: `${Math.max(4, (x.sum / maxDay) * 100)}%`,
                  background: "var(--accent-2)", opacity: 0.75,
                }} />
            ))}
          </div>
          <div className="flex justify-between text-[12px] mt-2" style={{ color: "var(--muted)" }}>
            <span>{d.daily[0].day}</span>
            <span>بیشترین روز: {faNum(maxDay)} تومان</span>
            <span>{d.daily[d.daily.length - 1].day}</span>
          </div>
        </div>
      )}

      <div className="fx-card p-5">
        <div className="flex items-center justify-between gap-3 mb-1 flex-wrap">
          <div className="text-[14px] font-semibold text-white flex items-center gap-2">
            <Users size={15} style={{ color: "var(--accent-2)" }} /> بهترین خریداران
          </div>
          <span className="text-[13px]" style={{ color: "var(--muted)" }}>
            {faNum(u.withPhone || 0)} کاربر شماره تماس داده‌اند
          </span>
        </div>
        <p className="text-[13px] mb-3" style={{ color: "var(--muted)" }}>
          مرتب بر اساس مجموع خرید در همین دوره.
        </p>

        {!(d.buyers || []).length ? (
          <EmptyState icon={Users} text="در این بازه خریدی ثبت نشده" />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="fx-table">
              <thead>
                <tr><th>کاربر</th><th>شماره تماس</th><th>سفارش</th>
                  <th>مجموع خرید</th><th>آخرین خرید</th></tr>
              </thead>
              <tbody>
                {d.buyers.map((b) => (
                  <tr key={b.tg_id}>
                    <td>
                      {esc0(b.first_name) || "—"}
                      {b.username && (
                        <span dir="ltr" className="mr-2" style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                          @{b.username}
                        </span>
                      )}
                    </td>
                    <td dir="ltr" style={{ fontFamily: "var(--mono)", color: b.phone ? "var(--dim)" : "var(--muted)" }}>
                      {b.phone || "—"}
                    </td>
                    <td style={{ fontFamily: "var(--mono)" }}>{faNum(b.orders)}</td>
                    <td style={{ fontFamily: "var(--mono)", color: "var(--ok)" }}>
                      {faNum(b.spent)}
                    </td>
                    <td style={{ color: "var(--muted)" }}>{String(b.lastBuy || "").slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

/** نام کاربر ممکن است HTML داشته باشد — React خودش امن می‌کند، این فقط تمیزکاری است. */
const esc0 = (s) => (s == null ? "" : String(s));

function MonitorSection({ password }) {
  const [d, setD] = useState(null);
  const [heavy, setHeavy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [heavyBusy, setHeavyBusy] = useState(false);
  const [live, setLive] = useState(true);
  const [err, setErr] = useState("");
  // بستن آی‌پی یک عمل برگشت‌پذیر ولی مؤثر است — بدون تایید صریح
  // انجام نمی‌شود، چون ممکن است همان آی‌پی مشتری واقعی باشد
  const [blockTarget, setBlockTarget] = useState(null);
  const [blockMsg, setBlockMsg] = useState(null);

  useEffect(() => {
    if (blockMsg) { const t = setTimeout(() => setBlockMsg(null), 5000); return () => clearTimeout(t); }
  }, [blockMsg]);

  const doBlock = async (ip) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/firewall/block-ip`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ ip, comment: "اتصال غیرعادی — از مانیتورینگ" }),
      });
      const j = await res.json().catch(() => ({}));
      setBlockMsg(res.ok
        ? { t: "ok", m: `${ip} بسته شد` }
        : { t: "err", m: j.detail || "بستن ناموفق بود" });
    } catch {
      setBlockMsg({ t: "err", m: "اتصال برقرار نشد" });
    }
  };

  const get = async (sections) => {
    const r = await fetch(`${API_URL}/api/admin/monitor?sections=${sections}`,
      { headers: { "X-Admin-Password": password } });
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail || "خطای سرور");
    return j;
  };

  const load = async () => {
    try { setD(await get(LIGHT)); setErr(""); }
    catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const loadHeavy = async () => {
    setHeavyBusy(true);
    try { setHeavy(await get(HEAVY)); }
    catch { /* بی‌صدا */ }
    finally { setHeavyBusy(false); }
  };

  useEffect(() => { load(); }, [password]);
  usePolling(load, live ? 8000 : 0, [password]);

  if (loading) {
    return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;
  }

  const sec = d?.sections || {};
  const metrics = [...(d?.metrics || []), ...(heavy?.metrics || [])];
  const worst = heavy && heavy.level === "crit" ? "crit"
    : (d?.level === "crit" ? "crit"
      : (d?.level === "warn" || heavy?.level === "warn" ? "warn" : "ok"));
  const s = LEVEL_STYLE[worst] || LEVEL_STYLE.ok;
  const problems = metrics.filter((m) => m.level !== "ok");

  return (
    <div className="fx-anim">
      <SectionHead title="مانیتورینگ سرور"
        desc="وضعیت زنده‌ی سروری که پنل رویش نصب است — با توضیح اینکه هر عدد از کجا به بعد خطرناک می‌شود."
        action={
          <div className="flex items-center gap-2">
            <button onClick={() => setLive(!live)}
              className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full"
                style={{ background: live ? "var(--ok)" : "var(--muted)" }} />
              {live ? "زنده" : "متوقف"}
            </button>
            <button onClick={load} className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
              <RefreshCw size={13} /> تازه‌سازی
            </button>
          </div>
        } />

      {err && <InfoBox tone="warn">{err}</InfoBox>}

      {/* حکم کلی */}
      <div className="fx-card p-5 mb-4" style={{ background: s.bg, borderColor: s.bd }}>
        <div className="flex items-start gap-3 flex-wrap">
          <s.Icon size={22} style={{ color: s.c, flexShrink: 0 }} className="mt-0.5" />
          <div className="min-w-0 flex-1">
            <div className="text-[16px] font-bold" style={{ color: s.c }}>
              {worst === "ok" ? "سرور سالم است" : (d?.headline || s.label)}
            </div>
            <div className="text-[13px] mt-1" style={{ color: "var(--dim)" }}>
              {problems.length === 0
                ? "هیچ موردی نیاز به رسیدگی ندارد."
                : problems.map((p) => p.title).join(" · ")}
            </div>
            <div className="text-[12px] mt-2.5 flex items-center gap-3 flex-wrap"
              style={{ color: "var(--muted)" }}>
              <span>{d?.host?.hostname || "—"}</span>
              <span style={{ opacity: 0.4 }}>•</span>
              <span>روشن از {fmtUptime(d?.host?.uptime)}</span>
              <span style={{ opacity: 0.4 }}>•</span>
              <span>{faNum(d?.host?.cores || 0)} هسته</span>
              <span style={{ opacity: 0.4 }}>•</span>
              <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>{d?.host?.kernel}</span>
              <span style={{ opacity: 0.4 }}>•</span>
              {/* faNum روی ساعت «ناعدد» می‌داد — رشته‌ی زمان عدد نیست */}
              <span>آخرین بررسی {toFaDigits(d?.at?.slice(11) || "—")}</span>
            </div>
          </div>
        </div>
      </div>

      {/* سنجه‌ها */}
      <div className="fx-g4 grid grid-cols-3 gap-3 mb-4">
        {(d?.metrics || []).map((m) => <MetricCard key={m.key} m={m} />)}
      </div>

      {/* شبکه */}
      {sec.network && sec.network[0]?.extra?.interfaces?.length > 0 && (
        <div className="fx-card p-5 mb-4">
          <div className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
            <Network size={15} style={{ color: "var(--accent-2)" }} /> کارت‌های شبکه
          </div>
          {sec.network[0].extra.interfaces.map((i) => (
            <div key={i.name} className="flex items-center justify-between gap-3 py-2 flex-wrap"
              style={{ borderBottom: "1px solid var(--border)" }}>
              <span className="text-[13px] font-semibold text-white" dir="ltr">{i.name}</span>
              <div className="flex items-center gap-4 text-[13px]">
                <span style={{ color: "var(--ok)" }}>↓ {fmtSize(i.rx)}/s</span>
                <span style={{ color: "var(--accent-2)" }}>↑ {fmtSize(i.tx)}/s</span>
                <span style={{ color: "var(--muted)" }}>
                  کل: {fmtSize(i.rxTotal)} / {fmtSize(i.txTotal)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="fx-g3 grid grid-cols-2 gap-3 mb-4">
        {/* سرویس‌ها */}
        {sec.services?.length > 0 && (
          <div className="fx-card p-5">
            <div className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
              <Server size={15} style={{ color: "var(--accent-2)" }} /> سرویس‌ها
            </div>
            {sec.services.map((sv) => {
              const bad = sv.level !== "ok";
              return (
                <div key={sv.name} className="flex items-center justify-between gap-2 py-2"
                  style={{ borderBottom: "1px solid var(--border)" }}>
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="w-1.5 h-1.5 rounded-full shrink-0"
                      style={{ background: bad ? "var(--danger)" : (sv.flapping ? "var(--warn)" : "var(--ok)") }} />
                    <span className="text-[13px] truncate" dir="ltr"
                      style={{ color: bad ? "var(--danger)" : "var(--text)" }}>{sv.name}</span>
                    {sv.flapping && (
                      <span className="fx-pill" style={{ background: "rgba(251,191,36,.12)", color: "var(--warn)" }}>
                        ناپایدار
                      </span>
                    )}
                  </div>
                  <span className="text-[12px] shrink-0" style={{ color: "var(--muted)" }}>
                    {sv.active === "active" ? fmtSize(sv.memory) : sv.active}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {/* سنگین‌ترین پردازه‌ها */}
        {sec.processes?.length > 0 && (
          <div className="fx-card p-5">
            <div className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
              <Activity size={15} style={{ color: "var(--accent-2)" }} /> سنگین‌ترین پردازه‌ها
            </div>
            {sec.processes.map((p) => (
              <div key={p.pid} className="flex items-center justify-between gap-2 py-2"
                style={{ borderBottom: "1px solid var(--border)" }}>
                <span className="text-[13px] truncate" dir="ltr">{p.name}</span>
                <div className="flex items-center gap-3 text-[12px] shrink-0"
                  style={{ fontFamily: "var(--mono)" }}>
                  <span style={{ color: p.cpu > 50 ? "var(--warn)" : "var(--muted)" }}>
                    {faNum(p.cpu)}٪ CPU
                  </span>
                  <span style={{ color: "var(--muted)" }}>{faNum(p.mem)}٪ RAM</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* تاریخچه‌ی مصرف */}
      <UsageHistoryCard password={password} />

      {/* پرمصرف‌ترین مشتری‌ها */}
      <TopClientsCard password={password} />

      {/* اتصال‌های فعال */}
      <Msg msg={blockMsg} />
      <ConnectionsCard conn={sec.connections}
        onBlock={(h) => setBlockTarget(h)} />

      {blockTarget && (
        <ConfirmModal
          title={`بستن ${blockTarget.ip}؟`}
          desc={`این آی‌پی ${faNum(blockTarget.count)} اتصال دارد (${faNum(blockTarget.pct)}٪ کل). `
                + "با بستنش، اگر مشتری خودتان باشد سرویسش قطع می‌شود. "
                + "هر وقت خواستید از صفحه‌ی فایروال بازش کنید."}
          confirmLabel="ببند"
          onCancel={() => setBlockTarget(null)}
          onConfirm={() => { doBlock(blockTarget.ip); setBlockTarget(null); }} />
      )}

      {/* پورت‌های باز */}
      <PortsCard ports={sec.ports || []} />

      {/* نگهداری خودکار */}
      <MaintenanceCard password={password} />

      {/* بخش سنگین */}
      <div className="fx-card p-5">
        <div className="flex items-center justify-between gap-3 mb-1 flex-wrap">
          <div className="text-[14px] font-semibold text-white flex items-center gap-2">
            <Package size={15} style={{ color: "var(--accent-2)" }} /> بسته‌ها و امنیت
          </div>
          <button onClick={loadHeavy} disabled={heavyBusy}
            className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
            {heavyBusy ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
            {heavy ? "بررسی دوباره" : "بررسی کن"}
          </button>
        </div>
        <p className="text-[13px] mb-3" style={{ color: "var(--muted)" }}>
          چند ثانیه طول می‌کشد، پس خودکار تازه نمی‌شود.
        </p>
        {heavy ? (
          <div className="fx-g3 grid grid-cols-2 gap-3">
            {heavy.metrics.map((m) => <MetricCard key={m.key} m={m} />)}
          </div>
        ) : (
          <EmptyState icon={ShieldCheck} text="برای دیدن به‌روزرسانی‌های در انتظار و وضعیت امنیتی، «بررسی کن» را بزنید" />
        )}
      </div>
    </div>
  );
}

/* ===================== صفحه «به‌زودی» ===================== */

function ComingSoon({ title, desc, features }) {
  return (
    <div className="fx-anim">
      <SectionHead title={title} desc={desc} />
      <div className="fx-card p-8 text-center" style={{ borderStyle: "dashed" }}>
        <div className="fx-ico mx-auto mb-4" style={{ width: 52, height: 52, background: "rgba(251,191,36,.1)" }}>
          <Bot size={24} style={{ color: "var(--warn)" }} />
        </div>
        <div className="text-[16px] font-bold text-white mb-2">در حال توسعه</div>
        <p className="text-[13px] mb-6 max-w-md mx-auto leading-relaxed" style={{ color: "var(--muted)" }}>
          این بخش هنوز فعال نیست. تنظیماتی که در بخش «اتصال و تنظیمات» ذخیره می‌کنید،
          به‌محض آماده شدن ربات خودکار استفاده می‌شوند.
        </p>
        {features && (
          <div className="max-w-sm mx-auto text-right">
            <div className="text-[13px] mb-2.5" style={{ color: "var(--dim)" }}>قابلیت‌های برنامه‌ریزی‌شده:</div>
            {features.map((f, i) => (
              <div key={i} className="flex items-center gap-2 py-1.5">
                <Circle size={5} fill="var(--muted)" strokeWidth={0} />
                <span className="text-[13px]" style={{ color: "var(--muted)" }}>{f}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * مودال ساده — از React Portal روی body.
 *
 * داخل main که overflow دارد کار نمی‌کند و بریده می‌شود؛ این را
 * قبلاً یک‌بار یاد گرفتیم.
 */
/** مینیاتور کوچک هر حالت — تا بدون امتحان کردن بفهمید چه شکلی است. */
function WsModePreview({ mode, active }) {
  const line = (w, on) => (
    <div style={{
      height: 4, width: w, borderRadius: 2,
      background: on ? "var(--accent)" : "rgba(255,255,255,.13)",
    }} />
  );

  return (
    <div className="rounded-xl p-2.5 flex gap-1.5"
      style={{
        height: 58,
        background: active ? "rgba(0,0,0,.28)" : "rgba(0,0,0,.2)",
        boxShadow: "0 2px 8px rgba(0,0,0,.35) inset",
      }}>
      {mode === "rail" && (
        <div className="flex flex-col gap-1 shrink-0">
          {[0, 1, 2].map((i) => (
            <div key={i} style={{
              width: 8, height: 8, borderRadius: 3,
              background: i === 1 ? "var(--accent)" : "rgba(255,255,255,.13)",
            }} />
          ))}
        </div>
      )}

      <div className="flex-1 flex flex-col gap-1.5 min-w-0">
        {mode === "dropdown" && (
          <>
            <div className="rounded-md flex items-center px-1.5"
              style={{ height: 13, background: "rgba(255,255,255,.09)" }}>
              {line(18, true)}
            </div>
            <div className="flex flex-col gap-1 pr-1">
              {line(26, false)}{line(20, false)}{line(23, false)}
            </div>
          </>
        )}

        {mode === "accordion" && (
          <>
            {line(24, true)}
            <div className="flex flex-col gap-1 pr-2"
              style={{ borderRight: "1px solid rgba(43,127,214,.3)" }}>
              {line(18, false)}{line(15, false)}
            </div>
            {line(22, false)}
          </>
        )}

        {mode === "rail" && (
          <div className="flex flex-col gap-1.5 pt-0.5">
            {line(26, false)}{line(20, false)}{line(23, false)}
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════ سوییچ فضای کاری ═══════════════════ */

const WS_MODES = {
  accordion: { label: "تاشو", desc: "هر سه دیده می‌شوند، منوی فضای فعلی باز است" },
  dropdown:  { label: "کشویی", desc: "فضای فعلی بزرگ، بقیه با یک کلیک" },
  rail:      { label: "نوار آیکون", desc: "ستون باریک با آیکون و راهنمای شناور" },
};

const WS_COLOR = {
  sub: "var(--accent-2)",
  billing: "#D4AF37",
  tunnel: "#34D399",
  bot: "#A78BFA",
};

/**
 * جابه‌جایی بین فضاهای کاری.
 *
 * سه حالت دارد چون سلیقه‌ها فرق می‌کند و این پنل قرار است فروخته شود.
 * حالت از تنظیمات می‌آید و در localStorage می‌ماند.
 */
function WorkspaceSwitch({ mode, workspace, onSwitch, active, setActive }) {
  const [open, setOpen] = useState(false);
  const [hover, setHover] = useState(null);
  const spaces = Object.values(WORKSPACES);
  const cur = WORKSPACES[workspace];

  /* ── تاشو ── */
  if (mode === "accordion") {
    return (
      <div className="mb-2">
        {spaces.map((w) => {
          const on = workspace === w.key;
          const col = WS_COLOR[w.key] || "var(--accent-2)";
          return (
            <div key={w.key} className="mb-1">
              <button onClick={() => onSwitch(w.key)}
                className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-right transition-all"
                style={{
                  background: on ? `color-mix(in srgb, ${col} 10%, transparent)` : "transparent",
                  border: `1px solid ${on ? `color-mix(in srgb, ${col} 22%, transparent)` : "transparent"}`,
                }}>
                <w.icon size={15} style={{ color: on ? col : "var(--muted)", flexShrink: 0 }} />
                <span className="flex-1 text-[13px] truncate"
                  style={{ color: on ? "var(--text)" : "var(--dim)", fontWeight: on ? 700 : 500 }}>
                  {w.label}
                </span>
                <ChevronDown size={12} style={{
                  color: "var(--muted)", flexShrink: 0,
                  transform: on ? "rotate(180deg)" : "none",
                  transition: "transform .25s cubic-bezier(.22,1,.36,1)",
                }} />
              </button>

              {on && (
                <div className="mt-1 pr-2.5 mr-4"
                  style={{ borderRight: `1px solid color-mix(in srgb, ${col} 22%, transparent)` }}>
                  {w.groups.flatMap((g) => g.items).map((it) => {
                    const sel = active === it.key;
                    return (
                      <button key={it.key} onClick={() => setActive(it.key)}
                        className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg mb-0.5 text-right transition-colors"
                        style={{
                          background: sel ? "rgba(255,255,255,.04)" : "transparent",
                          color: sel ? "var(--text)" : "var(--muted)",
                          fontWeight: sel ? 600 : 400,
                        }}>
                        <it.icon size={12} style={{ flexShrink: 0 }} />
                        <span className="text-[13px] truncate">{it.label}</span>
                        {it.badge && (
                          <span className="text-[10.5px] px-1.5 py-0.5 rounded-full shrink-0"
                            style={{ background: "rgba(255,255,255,.06)", color: "var(--muted)" }}>
                            {it.badge}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  /* ── نوار آیکون ── */
  if (mode === "rail") {
    return (
      <div className="flex gap-1.5 mb-4 px-1">
        {spaces.map((w) => {
          const on = workspace === w.key;
          const col = WS_COLOR[w.key] || "var(--accent-2)";
          return (
            <div key={w.key} className="relative flex-1"
              onMouseEnter={() => setHover(w.key)} onMouseLeave={() => setHover(null)}>
              <button onClick={() => onSwitch(w.key)}
                className="w-full flex items-center justify-center rounded-xl transition-all"
                style={{
                  height: 42,
                  background: on ? `color-mix(in srgb, ${col} 14%, transparent)` : "transparent",
                  border: `1px solid ${on ? `color-mix(in srgb, ${col} 28%, transparent)` : "var(--border)"}`,
                  boxShadow: on
                    ? `0 1px 0 rgba(255,255,255,.08) inset, 0 6px 14px -6px color-mix(in srgb, ${col} 55%, transparent)`
                    : "none",
                }}>
                <w.icon size={17} style={{ color: on ? col : "var(--muted)" }} />
              </button>

              {hover === w.key && (
                <div className="absolute z-30 whitespace-nowrap rounded-xl px-3 py-2 fx-fade"
                  style={{
                    top: "calc(100% + 7px)", right: 0,
                    background: "var(--surface-2)", border: "1px solid var(--border-2)",
                    boxShadow: "0 12px 28px -8px rgba(0,0,0,.7)",
                  }}>
                  <div className="text-[13px] font-bold text-white">{w.label}</div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  /* ── کشویی (پیش‌فرض) ── */
  const col = WS_COLOR[workspace] || "var(--accent-2)";
  return (
    <div className="relative mb-4">
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-right"
        style={{
          background: "var(--surface-2)", border: "1px solid var(--border-2)",
          boxShadow: "0 1px 0 rgba(255,255,255,.05) inset",
        }}>
        <div className="rounded-[10px] flex items-center justify-center shrink-0"
          style={{
            width: 30, height: 30,
            background: `color-mix(in srgb, ${col} 14%, transparent)`,
            boxShadow: "0 1px 0 rgba(255,255,255,.1) inset",
          }}>
          <cur.icon size={15} style={{ color: col }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-bold text-white truncate">{cur.label}</div>
          <div className="text-[11px] mt-0.5" style={{ color: "var(--muted)" }}>فضای کاری</div>
        </div>
        <ChevronDown size={14} style={{
          color: "var(--muted)", flexShrink: 0,
          transform: open ? "rotate(180deg)" : "none", transition: "transform .22s",
        }} />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute z-20 left-0 right-0 rounded-2xl p-1.5 fx-scale"
            style={{
              top: "calc(100% + 6px)",
              background: "var(--surface)", border: "1px solid var(--border-2)",
              boxShadow: "0 18px 40px -12px rgba(0,0,0,.75)",
            }}>
            {spaces.map((w) => {
              const on = workspace === w.key;
              const c2 = WS_COLOR[w.key] || "var(--accent-2)";
              return (
                <button key={w.key}
                  onClick={() => { onSwitch(w.key); setOpen(false); }}
                  className="w-full flex items-center gap-2.5 px-2.5 py-2.5 rounded-xl text-right transition-colors"
                  style={{ background: on ? `color-mix(in srgb, ${c2} 12%, transparent)` : "transparent" }}>
                  <w.icon size={14} style={{ color: on ? c2 : "var(--muted)", flexShrink: 0 }} />
                  <span className="flex-1 text-[13px] truncate"
                    style={{ color: on ? "var(--text)" : "var(--dim)", fontWeight: on ? 700 : 500 }}>
                    {w.label}
                  </span>
                  {on && <Check size={12} style={{ color: c2, flexShrink: 0 }} />}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

function Modal({ title, onClose, children, footer, width = "440px" }) {
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

function BotAffiliates({ password }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [payFor, setPayFor] = useState(null);
  const [edit, setEdit] = useState(null);
  const [msg, setMsg] = useState(null);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/bot/affiliates`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setData(d);
    } catch {
      setData({ ready: false, error: "اتصال برقرار نشد", affiliates: [] });
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [password]);
  useEffect(() => {
    if (msg) { const t = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(t); }
  }, [msg]);

  const remove = async (id) => {
    await fetch(`${API_URL}/api/admin/bot/affiliate/${id}`, {
      method: "DELETE", headers: { "X-Admin-Password": password } });
    setMsg({ t: "ok", m: "همکار حذف شد — کاربرانش حفظ شدند" });
    load();
  };

  const toggle = async (a) => {
    await fetch(`${API_URL}/api/admin/bot/affiliate/${a.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-Admin-Password": password },
      body: JSON.stringify({ active: !a.active }),
    });
    load();
  };

  if (loading) {
    return <div className="flex justify-center py-16">
      <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;
  }

  if (!data?.ready) {
    return (
      <div className="fx-anim">
        <SectionHead title="همکاری در فروش" desc="" />
        <div className="fx-card p-8 text-center" style={{ borderStyle: "dashed" }}>
          <AlertTriangle size={24} style={{ color: "var(--warn)" }} className="mx-auto mb-3" />
          <div className="text-[14px]" style={{ color: "var(--muted)" }}>
            {data?.error || "دیتابیس ربات در دسترس نیست"}
          </div>
        </div>
      </div>
    );
  }

  const list = data.affiliates || [];

  return (
    <div className="fx-anim">
      <SectionHead title="همکاری در فروش"
        desc="کسانی که برای شما می‌فروشند و درصد می‌گیرند."
        action={
          <button onClick={() => setAdding(true)}
            className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
            <PlusIcon size={14} /> همکار جدید
          </button>
        } />

      {msg && <Msg msg={msg} />}

      {list.length > 0 && (
        <div className="fx-card p-5 mb-4">
          <div className="flex justify-between items-baseline flex-wrap gap-2">
            <span className="text-[14px]" style={{ color: "var(--dim)" }}>
              مجموع بدهی به همکاران
            </span>
            <span className="text-[21px] font-extrabold"
              style={{ color: data.totalOwed > 0 ? "var(--warn)" : "var(--ok)",
                       fontFamily: "var(--mono)" }}>
              {faNum(data.totalOwed)} <span className="text-[13px]">تومان</span>
            </span>
          </div>
        </div>
      )}

      {list.length === 0 ? (
        <div className="fx-card p-10 text-center" style={{ borderStyle: "dashed" }}>
          <Coins size={26} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
          <div className="text-[14px] font-semibold text-white mb-2">
            هنوز همکاری اضافه نشده
          </div>
          <p className="text-[13px] max-w-md mx-auto leading-relaxed"
            style={{ color: "var(--muted)" }}>
            هر همکار یک لینک اختصاصی می‌گیرد. هر کسی با آن لینک وارد ربات شود،
            از تمام خریدهایش — نه فقط خرید اول — به آن همکار پورسانت می‌رسد.
          </p>
        </div>
      ) : list.map((a) => (
        <div key={a.id} className="fx-card p-5 mb-3">
          <div className="flex items-start justify-between gap-3 flex-wrap mb-4">
            <div className="min-w-0">
              <div className="text-[14px] font-bold text-white flex items-center gap-2 flex-wrap">
                {a.name}
                <span className="text-[12px] px-2 py-0.5 rounded-lg"
                  style={{ background: "var(--accent-soft)", color: "var(--accent-2)",
                           fontFamily: "var(--mono)" }}>
                  {faNum(a.percent)}٪
                </span>
                {!a.active && (
                  <span className="text-[12px] px-2 py-0.5 rounded-lg"
                    style={{ background: "rgba(255,255,255,.05)", color: "var(--muted)" }}>
                    غیرفعال
                  </span>
                )}
              </div>
              <div className="text-[12px] mt-1.5" dir="ltr"
                style={{ color: "var(--muted)", fontFamily: "var(--mono)",
                         textAlign: "right" }}>
                aff_{a.code}
                {a.tg_id ? ` · ${a.tg_id}` : " · بدون تلگرام"}
              </div>
              {a.note && (
                <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
                  {a.note}
                </div>
              )}
            </div>
            <div className="flex gap-2 shrink-0">
              <button onClick={() => setEdit(a)} className="fx-ico-btn" title="ویرایش">
                <Sliders size={13} />
              </button>
              <button onClick={() => toggle(a)} className="fx-ico-btn"
                title={a.active ? "غیرفعال کردن" : "فعال کردن"}>
                {a.active ? <Eye size={13} /> : <EyeOff size={13} />}
              </button>
              <button onClick={() => remove(a.id)} className="fx-ico-btn" title="حذف">
                <Trash2 size={13} />
              </button>
            </div>
          </div>

          <div className="fx-g4 grid grid-cols-4 gap-3">
            {[["کاربر", a.users, "var(--dim)"],
              ["خرید", a.orders, "var(--dim)"],
              ["فروش", a.sales, "var(--accent-2)"],
              ["پورسانت", a.earned, "var(--ok)"]].map(([l, v, col], i) => (
              <div key={i} className="p-3 rounded-xl text-center"
                style={{ background: "var(--surface-3)" }}>
                <div className="text-[16px] font-bold" style={{ color: col,
                     fontFamily: "var(--mono)" }}>
                  {faNum(v)}
                </div>
                <div className="text-[11.5px] mt-1" style={{ color: "var(--muted)" }}>{l}</div>
              </div>
            ))}
          </div>

          <div className="flex justify-between items-center mt-4 pt-3 flex-wrap gap-3"
            style={{ borderTop: "1px solid var(--border)" }}>
            <div className="text-[13px]" style={{ color: "var(--muted)" }}>
              پرداخت‌شده {faNum(a.payouts)} · {" "}
              <b style={{ color: a.balance > 0 ? "var(--warn)" : "var(--ok)" }}>
                مانده {faNum(a.balance)}
              </b>
            </div>
            {a.balance > 0 && (
              <button onClick={() => setPayFor(a)}
                className="fx-btn px-3 py-2 text-[13px] flex items-center gap-1.5">
                <DollarSign size={12} /> ثبت پرداخت
              </button>
            )}
          </div>
        </div>
      ))}

      {(adding || edit) && (
        <AffiliateForm password={password} affiliate={edit}
          onClose={() => { setAdding(false); setEdit(null); }}
          onDone={(m) => { setAdding(false); setEdit(null); load(); setMsg({ t: "ok", m }); }} />
      )}

      {payFor && (
        <AffiliatePayoutModal affiliate={payFor} password={password}
          onClose={() => setPayFor(null)}
          onDone={() => { setPayFor(null); load(); setMsg({ t: "ok", m: "پرداخت ثبت شد" }); }} />
      )}
    </div>
  );
}

/** افزودن یا ویرایش همکار */
function AffiliateForm({ password, affiliate, onClose, onDone }) {
  const editing = !!affiliate;
  const [f, setF] = useState({
    name: affiliate?.name || "",
    percent: affiliate?.percent || 10,
    code: affiliate?.code || "",
    tg_id: affiliate?.tg_id || "",
    note: affiliate?.note || "",
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async () => {
    setBusy(true); setErr("");
    try {
      const url = editing
        ? `${API_URL}/api/admin/bot/affiliate/${affiliate.id}`
        : `${API_URL}/api/admin/bot/affiliate`;
      const res = await fetch(url, {
        method: editing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify(f),
      });
      const d = await res.json();
      if (res.ok) onDone(editing ? "ذخیره شد" : `همکار اضافه شد — کد ${d.code}`);
      else setErr(d.detail || "ناموفق");
    } catch { setErr("اتصال برقرار نشد"); }
    finally { setBusy(false); }
  };

  return (
    <Modal title={editing ? "ویرایش همکار" : "همکار جدید"} onClose={onClose} width="480px"
      footer={
        <button onClick={submit} disabled={busy || !f.name.trim()}
          className="fx-btn w-full py-3 text-[14px] flex items-center justify-center gap-2"
          style={!f.name.trim() ? { opacity: .45, cursor: "not-allowed" } : {}}>
          {busy ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
          {editing ? "ذخیره" : "افزودن"}
        </button>
      }>
      <Field label="نام همکار">
        <input className="fx-input" value={f.name}
          onChange={(e) => setF({ ...f, name: e.target.value })}
          placeholder="نام یا عنوان" />
      </Field>

      <Field label="درصد پورسانت" hint="از هر خریدی که مشتریانش می‌کنند">
        <div className="flex items-center gap-2">
          <input className="fx-input" type="text" inputMode="decimal" dir="ltr"
            value={f.percent}
            onChange={(e) => setF({ ...f,
              percent: e.target.value.replace(/[^0-9.]/g, "").slice(0, 5) })}
            style={{ fontFamily: "var(--mono)" }} />
          <div className="flex gap-1.5 shrink-0">
            {[5, 10, 15, 20].map((p) => (
              <button key={p} onClick={() => setF({ ...f, percent: p })}
                className="px-2.5 py-2 rounded-lg text-[12px]"
                style={{
                  background: +f.percent === p ? "var(--accent-soft)" : "transparent",
                  border: `1px solid ${+f.percent === p ? "rgba(43,127,214,.4)" : "var(--border)"}`,
                  color: +f.percent === p ? "var(--accent-2)" : "var(--muted)",
                  fontFamily: "var(--mono)",
                }}>{faNum(p)}٪</button>
            ))}
          </div>
        </div>
      </Field>

      <Field label="آیدی عددی تلگرام (اختیاری)"
        hint="اگر بدهید، پنل همکاری در ربات برایش باز می‌شود و از هر فروش خبردار می‌شود">
        <input className="fx-input" type="text" inputMode="numeric" dir="ltr"
          value={f.tg_id}
          onChange={(e) => setF({ ...f, tg_id: e.target.value.replace(/[^0-9]/g, "") })}
          placeholder="123456789"
          style={{ fontFamily: "var(--mono)" }} />
      </Field>

      {!editing && (
        <Field label="کد لینک (اختیاری)" hint="خالی بگذارید تا خودکار ساخته شود">
          <input className="fx-input" dir="ltr" value={f.code}
            onChange={(e) => setF({ ...f, code: e.target.value.replace(/[^A-Za-z0-9]/g, "") })}
            placeholder="yaser"
            style={{ fontFamily: "var(--mono)" }} />
        </Field>
      )}

      <Field label="یادداشت (اختیاری)">
        <input className="fx-input" value={f.note}
          onChange={(e) => setF({ ...f, note: e.target.value })}
          placeholder="توافق یا شماره تماس" />
      </Field>

      {err && (
        <div className="text-[13px] p-3 rounded-xl mt-3"
          style={{ background: "rgba(248,113,113,.1)", color: "var(--danger)" }}>{err}</div>
      )}
    </Modal>
  );
}

/** ثبت پرداخت به همکار */
function AffiliatePayoutModal({ affiliate, password, onClose, onDone }) {
  const [amount, setAmount] = useState(String(affiliate.balance || ""));
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      await fetch(`${API_URL}/api/admin/bot/affiliate/${affiliate.id}/payout`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ amount: +amount, note }),
      });
      onDone();
    } finally { setBusy(false); }
  };

  return (
    <Modal title={`پرداخت به ${affiliate.name}`} onClose={onClose} width="420px"
      footer={
        <button onClick={submit} disabled={busy || !(+amount > 0)}
          className="fx-btn w-full py-3 text-[14px] flex items-center justify-center gap-2"
          style={!(+amount > 0) ? { opacity: .45, cursor: "not-allowed" } : {}}>
          {busy ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
          ثبت پرداخت
        </button>
      }>
      <div className="p-3.5 rounded-xl mb-4" style={{ background: "var(--surface-3)" }}>
        <div className="flex justify-between text-[13px]">
          <span style={{ color: "var(--muted)" }}>مانده‌ی فعلی</span>
          <span style={{ color: "var(--warn)", fontFamily: "var(--mono)" }}>
            {faNum(affiliate.balance)} تومان
          </span>
        </div>
      </div>

      <Field label="مبلغ پرداختی (تومان)">
        <input className="fx-input" type="text" inputMode="numeric" dir="ltr"
          value={amount}
          onChange={(e) => setAmount(e.target.value.replace(/[^0-9]/g, ""))}
          style={{ fontFamily: "var(--mono)" }} />
      </Field>

      <Field label="یادداشت (اختیاری)">
        <input className="fx-input" value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="شماره کارت یا تاریخ واریز" />
      </Field>

      <InfoBox>
        پرداخت بیرون از ربات انجام می‌شود؛ این فقط ثبت می‌کند تا مانده درست بماند.
        پورسانت‌های قدیمی‌تر تا سقف این مبلغ، پرداخت‌شده علامت می‌خورند.
      </InfoBox>
    </Modal>
  );
}

/* ═══════════════════ تانل ═══════════════════ */

const ENGINE_COLOR = {
  backhaul: "#34D399",
  rathole: "#5AA9E6",
  gost: "#A78BFA",
  frp: "#FBBF24",
};

const TUN_STATUS = {
  running:   { label: "در حال کار", color: "var(--ok)" },
  deploying: { label: "در حال اعمال", color: "var(--warn)" },
  stopped:   { label: "متوقف", color: "var(--muted)" },
  failed:    { label: "خطا", color: "var(--danger)" },
  pending:   { label: "اعمال نشده", color: "var(--muted)" },
};

function useTunnel(password) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/tunnel/overview`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setData(d);
    } catch {
      setData({ ready: false, error: "اتصال برقرار نشد", nodes: [], tunnels: [] });
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [password]);
  // نودها هر ۲۰ ثانیه ping می‌زنند — ولی وقتی تب مخفی است بی‌فایده
  usePolling(load, 20000, [password]);

  return { data, loading, reload: load };
}

/* ── داشبورد تانل ── */
function TunnelOverview({ password }) {
  const { data, loading, reload } = useTunnel(password);

  if (loading) return <div className="flex justify-center py-16">
    <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  if (!data?.ready) {
    return (
      <div className="fx-anim">
        <SectionHead title="داشبورد تانل" desc="" />
        <div className="fx-card p-8 text-center" style={{ borderStyle: "dashed" }}>
          <AlertTriangle size={24} style={{ color: "var(--warn)" }} className="mx-auto mb-3" />
          <div className="text-[14px]" style={{ color: "var(--muted)" }}>
            {data?.error || "ماژول تانل در دسترس نیست"}
          </div>
        </div>
      </div>
    );
  }

  const s = data.stats;

  return (
    <div className="fx-anim">
      <SectionHead title="داشبورد تانل"
        desc="سرورهای متصل و تانل‌های فعال."
        action={<button onClick={reload} className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
          <RefreshCw size={13} /> تازه‌سازی</button>} />

      <div className="fx-g4 grid grid-cols-4 gap-3 mb-5">
        {[["سرورها", s.nodes, "var(--accent-2)", Server],
          ["آنلاین", s.online, "var(--ok)", Activity],
          ["تانل‌ها", s.tunnels, "#A78BFA", Network],
          ["در حال کار", s.running, "var(--ok)", CheckCircle2]].map(([l, v, col, I], i) => (
          <div key={i} className="fx-card fx-card-i p-4">
            <div className="fx-ico mb-3" style={{ background: `color-mix(in srgb, ${col} 12%, transparent)` }}>
              <I size={15} style={{ color: col }} />
            </div>
            <div className="fx-stat-num text-[21px] font-extrabold text-white leading-none"
              style={{ fontFamily: "var(--mono)" }}>{faNum(v)}</div>
            <div className="text-[12px] mt-1.5" style={{ color: "var(--dim)" }}>{l}</div>
          </div>
        ))}
      </div>

      {data.nodes.length === 0 ? (
        <div className="fx-card p-10 text-center" style={{ borderStyle: "dashed" }}>
          <Server size={26} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
          <div className="text-[14px] font-semibold text-white mb-2">هنوز سروری اضافه نشده</div>
          <p className="text-[13px] max-w-sm mx-auto leading-relaxed" style={{ color: "var(--muted)" }}>
            از بخش «سرورها» یک سرور ایران اضافه کنید. یک دستور نصب می‌گیرید
            که روی آن سرور اجرا می‌کنید — بدون نیاز به باز کردن پورت یا دادن رمز.
          </p>
        </div>
      ) : (
        <>
          <div className="fx-card p-5 mb-4">
            <div className="text-[14px] font-semibold text-white mb-4">سرورها</div>
            {data.nodes.map((n, i, arr) => (
              <div key={n.id} className="flex items-center justify-between gap-3 py-3 flex-wrap"
                style={{ borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                <div className="flex items-center gap-3 min-w-0">
                  <div style={{
                    width: 8, height: 8, borderRadius: "50%",
                    background: n.online ? "var(--ok)" : "var(--muted)",
                    boxShadow: n.online ? "0 0 8px var(--ok)" : "none",
                    flexShrink: 0,
                  }} />
                  <div className="min-w-0">
                    <div className="text-[14px] font-semibold text-white">{n.name}</div>
                    <div className="text-[12px] mt-0.5" style={{ color: "var(--muted)" }}>
                      {n.os_info || "—"}{n.public_ip ? ` · ${n.public_ip}` : ""}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4 shrink-0 text-[13px]"
                  style={{ color: "var(--dim)", fontFamily: "var(--mono)" }}>
                  {n.cpu_percent != null && <span>CPU {faNum(n.cpu_percent)}٪</span>}
                  {n.mem_percent != null && <span>RAM {faNum(n.mem_percent)}٪</span>}
                  <span style={{ color: n.online ? "var(--ok)" : "var(--muted)" }}>
                    {n.running_count}/{n.tunnel_count} تانل
                  </span>
                </div>
              </div>
            ))}
          </div>

          {data.tunnels.length > 0 && (
            <div className="fx-card p-5">
              <div className="text-[14px] font-semibold text-white mb-4">تانل‌های اخیر</div>
              {data.tunnels.slice(0, 6).map((t, i, arr) => {
                const st = TUN_STATUS[t.status] || TUN_STATUS.pending;
                const ec = ENGINE_COLOR[t.engine] || "var(--accent-2)";
                return (
                  <div key={t.id} className="flex items-center justify-between gap-3 py-3 flex-wrap"
                    style={{ borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                    <div className="min-w-0">
                      <div className="text-[14px] font-semibold text-white">{t.name}</div>
                      <div className="text-[12px] mt-0.5" style={{ color: "var(--muted)" }}>
                        {t.node_name} · {t.ports.length} پورت
                      </div>
                    </div>
                    <div className="flex items-center gap-2.5 shrink-0">
                      <span className="text-[12px] px-2 py-1 rounded-lg"
                        style={{ background: `color-mix(in srgb, ${ec} 14%, transparent)`, color: ec }}>
                        {t.engineName}
                      </span>
                      <span className="text-[13px]" style={{ color: st.color }}>{st.label}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ── سرورها ── */
function TunnelNodes({ password }) {
  const { data, loading, reload } = useTunnel(password);
  const [diag, setDiag] = useState(null);
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState(null);
  const [msg, setMsg] = useState(null);

  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(t); } }, [msg]);

  const add = async () => {
    if (!name.trim()) return;
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/tunnel/node`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ name, note }),
      });
      const d = await res.json();
      if (res.ok) {
        setCreated(d);
        setAdding(false);
        setName(""); setNote("");
        reload();
      } else setMsg({ t: "err", m: d.detail || "افزودن ناموفق" });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(false); }
  };

  const remove = async (id) => {
    await fetch(`${API_URL}/api/admin/tunnel/node/${id}`, {
      method: "DELETE", headers: { "X-Admin-Password": password } });
    reload();
  };

  const rotate = async (id) => {
    const res = await fetch(`${API_URL}/api/admin/tunnel/node/${id}/rotate`, {
      method: "POST", headers: { "X-Admin-Password": password } });
    const d = await res.json();
    if (res.ok) setCreated({ id, token: d.token, rotated: true });
  };

  if (loading) return <div className="flex justify-center py-16">
    <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  return (
    <div className="fx-anim">
      <SectionHead title="سرورها"
        desc="سرورهایی که agent روی آن‌ها نصب است."
        action={<button onClick={() => setAdding(true)} className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
          <PlusIcon size={14} /> افزودن سرور</button>} />

      {msg && <Msg msg={msg} />}

      {(!data?.nodes || data.nodes.length === 0) ? (
        <div className="fx-card p-10 text-center" style={{ borderStyle: "dashed" }}>
          <Server size={26} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
          <div className="text-[14px]" style={{ color: "var(--muted)" }}>هنوز سروری اضافه نشده</div>
        </div>
      ) : data.nodes.map((n) => (
        <div key={n.id} className="fx-card p-5 mb-3">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-3 min-w-0">
              <div className="fx-ico" style={{
                background: n.online ? "rgba(52,211,153,.12)" : "rgba(255,255,255,.04)",
                width: 38, height: 38,
              }}>
                <Server size={17} style={{ color: n.online ? "var(--ok)" : "var(--muted)" }} />
              </div>
              <div className="min-w-0">
                <div className="text-[14px] font-bold text-white flex items-center gap-2">
                  {n.name}
                  <span className="text-[12px] px-2 py-0.5 rounded-full"
                    style={{
                      background: n.online ? "rgba(52,211,153,.14)" : "rgba(255,255,255,.05)",
                      color: n.online ? "var(--ok)" : "var(--muted)",
                    }}>
                    {n.online ? "آنلاین" : "آفلاین"}
                  </span>
                </div>
                <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
                  {n.os_info || "هنوز خبری نداده"}
                  {n.public_ip && ` · ${n.public_ip}`}
                  {n.agent_version && ` · agent ${n.agent_version}`}
                </div>
              </div>
            </div>
            <div className="flex gap-2 shrink-0">
              {!n.online && (
                <button onClick={() => setDiag(n.id)}
                  className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
                  <ShieldCheck size={12} /> چرا آفلاین؟
                </button>
              )}
              <button onClick={() => rotate(n.id)} className="fx-ico-btn" title="توکن جدید">
                <RefreshCw size={13} />
              </button>
              <button onClick={() => remove(n.id)} className="fx-ico-btn" title="حذف">
                <Trash2 size={13} />
              </button>
            </div>
          </div>

          {n.online && (n.cpu_percent != null || n.mem_percent != null) && (
            <div className="fx-g3 grid grid-cols-3 gap-3 mt-4">
              {[["پردازنده", n.cpu_percent], ["حافظه", n.mem_percent],
                ["دیسک", n.disk_percent]].map(([l, v], i) => (
                <div key={i} className="p-3 rounded-xl" style={{ background: "var(--surface-3)" }}>
                  <div className="flex justify-between items-baseline mb-2">
                    <span className="text-[12px]" style={{ color: "var(--muted)" }}>{l}</span>
                    <span className="text-[13px] font-bold" style={{
                      color: v == null ? "var(--muted)"
                           : v > 85 ? "var(--danger)" : v > 65 ? "var(--warn)" : "var(--dim)",
                      fontFamily: "var(--mono)",
                    }}>{v == null ? "—" : `${faNum(v)}٪`}</span>
                  </div>
                  <div style={{ height: 4, borderRadius: 99, background: "rgba(255,255,255,.06)", overflow: "hidden" }}>
                    <div style={{
                      width: `${Math.min(100, v || 0)}%`, height: "100%",
                      background: (v || 0) > 85 ? "var(--danger)" : (v || 0) > 65 ? "var(--warn)" : "var(--accent)",
                    }} />
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-center justify-between mt-4 pt-3 flex-wrap gap-2"
            style={{ borderTop: "1px solid var(--border)" }}>
            <span className="text-[13px]" style={{ color: "var(--muted)" }}>
              {faNum(n.running_count)} از {faNum(n.tunnel_count)} تانل در حال کار
            </span>
            <span className="text-[12px]" dir="ltr"
              style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
              {n.token}
            </span>
          </div>
        </div>
      ))}

      {adding && (
        <Modal title="افزودن سرور" onClose={() => setAdding(false)}>
          <Field label="نام سرور" hint="مثلاً: تهران — پارس‌پک">
            <input className="fx-input" value={name} onChange={(e) => setName(e.target.value)}
              placeholder="سرور ایران" />
          </Field>
          <Field label="یادداشت (اختیاری)">
            <input className="fx-input" value={note} onChange={(e) => setNote(e.target.value)}
              placeholder="مشخصات یا محل سرور" />
          </Field>
          <InfoBox>
            بعد از ساخت، یک دستور نصب می‌گیرید که روی سرور اجرا می‌کنید.
            سرور شما هیچ پورتی باز نمی‌کند و رمزی جایی ذخیره نمی‌شود.
          </InfoBox>
          <button onClick={add} disabled={busy || !name.trim()}
            className="fx-btn w-full py-3 text-[14px] flex items-center justify-center gap-2 mt-4">
            {busy ? <Loader2 size={14} className="animate-spin" /> : <PlusIcon size={14} />}
            ساخت و دریافت دستور نصب
          </button>
        </Modal>
      )}

      {created && <AgentInstallModal data={created} onClose={() => setCreated(null)} />}
      {diag && <NodeDiagnoseModal nodeId={diag} password={password}
        onClose={() => setDiag(null)} />}
    </div>
  );
}

/** چرا نود آفلاین است */
function NodeDiagnoseModal({ nodeId, password, onClose }) {
  const [d, setD] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/api/admin/tunnel/node/${nodeId}/check`, {
      headers: { "X-Admin-Password": password },
    }).then((r) => r.json()).then(setD).catch(() => setD({ steps: [] }));
  }, [nodeId]);

  const copy = (t) => navigator.clipboard?.writeText(t);

  return (
    <Modal title="چرا نود آفلاین است" onClose={onClose} width="520px">
      {!d ? (
        <div className="flex justify-center py-8">
          <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>
      ) : (
        <>
          {d.steps?.map((s, i) => (
            <div key={i} className="flex gap-3 py-2.5"
              style={{ borderBottom: "1px solid var(--border)" }}>
              <div className="shrink-0 mt-0.5">
                {s.ok ? <CheckCircle2 size={15} style={{ color: "var(--ok)" }} />
                      : <XCircle size={15} style={{ color: "var(--danger)" }} />}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-semibold"
                  style={{ color: s.ok ? "var(--text)" : "var(--danger)" }}>{s.title}</div>
                {s.detail && (
                  <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
                    {s.detail}
                  </div>
                )}
                {s.hint && (
                  <div className="text-[13px] mt-2 px-2.5 py-1.5 rounded-lg leading-relaxed"
                    style={{ color: "var(--warn)", background: "rgba(251,191,36,.08)" }}>
                    {s.hint}
                  </div>
                )}
              </div>
            </div>
          ))}

          <div className="mt-4">
            <div className="text-[13px] font-semibold text-white mb-2.5">
              روی سرور ایران اجرا کنید
            </div>
            {d.commands?.map((cm, i) => (
              <div key={i} className="mb-2">
                <div className="text-[12px] mb-1" style={{ color: "var(--muted)" }}>
                  {cm.label}
                </div>
                <div onClick={() => copy(cm.cmd)}
                  className="rounded-lg px-3 py-2 cursor-pointer" dir="ltr"
                  style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
                  <code className="text-[13px]"
                    style={{ color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
                    {cm.cmd}
                  </code>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </Modal>
  );
}

/** دستور نصب agent */
function AgentInstallModal({ data, onClose }) {
  const [copied, setCopied] = useState(false);
  const panel = typeof window !== "undefined" ? window.location.origin : "";
  const cmd = `curl -fsSL "${panel}/api/agent/install.sh?token=${data.token}&panel=${panel}" | sudo bash`;

  const copy = () => {
    navigator.clipboard?.writeText(cmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Modal title={data.rotated ? "توکن جدید" : "نصب روی سرور"} onClose={onClose} width="560px">
      <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
        {data.rotated
          ? "توکن قبلی باطل شد. agent را با این دستور دوباره نصب کنید."
          : "این دستور را روی سرور ایران اجرا کنید. کمتر از یک دقیقه طول می‌کشد."}
      </p>

      <div className="rounded-xl p-3.5 mb-3" dir="ltr"
        style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
        <code className="text-[13px] break-all block leading-relaxed"
          style={{ color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
          {cmd}
        </code>
      </div>

      <button onClick={copy}
        className="fx-btn w-full py-2.5 text-[14px] flex items-center justify-center gap-2">
        {copied ? <><Check size={14} /> کپی شد</> : <><Copy size={14} /> کپی دستور</>}
      </button>

      <InfoBox tone="warn">
        این دستور فقط یک‌بار نمایش داده می‌شود. توکن داخلش کلید دسترسی
        agent است — جایی که دیگران ببینند نگذارید.
      </InfoBox>
    </Modal>
  );
}

/* ── فهرست تانل‌ها ── */
function TunnelList({ password }) {
  const { data, loading, reload } = useTunnel(password);
  const [adding, setAdding] = useState(false);
  const [cfgFor, setCfgFor] = useState(null);
  const [monFor, setMonFor] = useState(null);
  const [msg, setMsg] = useState(null);

  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(t); } }, [msg]);

  const act = async (id, what) => {
    const url = what === "deploy"
      ? `${API_URL}/api/admin/tunnel/${id}/deploy`
      : `${API_URL}/api/admin/tunnel/${id}/action/${what}`;
    const res = await fetch(url, { method: "POST", headers: { "X-Admin-Password": password } });
    const d = await res.json().catch(() => ({}));
    setMsg(res.ok
      ? { t: "ok", m: what === "deploy" ? "در صف اعمال قرار گرفت" : "دستور فرستاده شد" }
      : { t: "err", m: d.detail || "ناموفق" });
    reload();
  };

  const remove = async (id) => {
    await fetch(`${API_URL}/api/admin/tunnel/${id}`, {
      method: "DELETE", headers: { "X-Admin-Password": password } });
    reload();
  };

  if (loading) return <div className="flex justify-center py-16">
    <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  const hasNodes = data?.nodes?.length > 0;

  return (
    <div className="fx-anim">
      <SectionHead title="تانل‌ها"
        desc="اتصال بین سرور ایران و سرور خارج."
        action={hasNodes && (
          <button onClick={() => setAdding(true)} className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
            <PlusIcon size={14} /> تانل جدید
          </button>
        )} />

      {msg && <Msg msg={msg} />}

      {!hasNodes ? (
        <div className="fx-card p-10 text-center" style={{ borderStyle: "dashed" }}>
          <Server size={26} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
          <div className="text-[14px]" style={{ color: "var(--muted)" }}>
            اول از بخش «سرورها» یک سرور اضافه کنید
          </div>
        </div>
      ) : data.tunnels.length === 0 ? (
        <div className="fx-card p-10 text-center" style={{ borderStyle: "dashed" }}>
          <Network size={26} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
          <div className="text-[14px]" style={{ color: "var(--muted)" }}>هنوز تانلی ساخته نشده</div>
        </div>
      ) : data.tunnels.map((t) => {
        const st = TUN_STATUS[t.status] || TUN_STATUS.pending;
        const ec = ENGINE_COLOR[t.engine] || "var(--accent-2)";
        return (
          <div key={t.id} className="fx-card p-5 mb-3">
            <div className="flex items-start justify-between gap-3 flex-wrap mb-4">
              <div className="min-w-0">
                <div className="text-[14px] font-bold text-white flex items-center gap-2 flex-wrap">
                  {t.name}
                  <span className="text-[12px] px-2 py-0.5 rounded-lg"
                    style={{ background: `color-mix(in srgb, ${ec} 14%, transparent)`, color: ec }}>
                    {t.engineName} · {t.transport}
                  </span>
                </div>
                <div className="text-[12px] mt-1.5" dir="ltr"
                  style={{ color: "var(--muted)", fontFamily: "var(--mono)", textAlign: "right" }}>
                  {t.node_name} ← {t.remote_host}:{t.bridge_port}
                </div>
              </div>
              <span className="text-[13px] px-2.5 py-1 rounded-lg shrink-0"
                style={{ background: `color-mix(in srgb, ${st.color} 12%, transparent)`, color: st.color }}>
                {st.label}
              </span>
            </div>

            <div className="flex gap-1.5 flex-wrap mb-4">
              {t.ports.map((p, i) => (
                <span key={i} className="text-[12px] px-2 py-1 rounded-lg" dir="ltr"
                  style={{ background: "var(--surface-3)", color: "var(--dim)",
                           fontFamily: "var(--mono)" }}>
                  {p.local === p.remote ? p.local : `${p.local}→${p.remote}`}
                </span>
              ))}
            </div>

            {t.last_error && (
              <div className="text-[12px] p-2.5 rounded-lg mb-3"
                style={{ background: "rgba(248,113,113,.08)", color: "var(--danger)" }}>
                {t.last_error.slice(0, 160)}
              </div>
            )}

            <div className="flex gap-2 flex-wrap pt-3" style={{ borderTop: "1px solid var(--border)" }}>
              <button onClick={() => act(t.id, "deploy")} disabled={!t.nodeOnline}
                className="fx-btn px-3 py-2 text-[13px] flex items-center gap-1.5"
                style={!t.nodeOnline ? { opacity: .4, cursor: "not-allowed" } : {}}>
                <UploadCloud size={12} /> اعمال
              </button>
              {["restart", "stop", "logs"].map((w) => (
                <button key={w} onClick={() => act(t.id, w)} disabled={!t.nodeOnline}
                  className="fx-btn-g px-3 py-2 text-[13px]"
                  style={!t.nodeOnline ? { opacity: .4, cursor: "not-allowed" } : {}}>
                  {{ restart: "ری‌استارت", stop: "توقف", logs: "لاگ" }[w]}
                </button>
              ))}
              <button onClick={() => setMonFor(t)}
                className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
                <Activity size={12} /> کیفیت
              </button>
              <button onClick={() => setCfgFor(t)} className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
                <FileText size={12} /> کانفیگ سرور خارج
              </button>
              <button onClick={() => remove(t.id)} className="fx-ico-btn mr-auto" style={{ width: 30, height: 30 }}>
                <Trash2 size={12} />
              </button>
            </div>

            {!t.nodeOnline && (
              <div className="text-[12px] mt-3" style={{ color: "var(--warn)" }}>
                سرور آفلاین است — دستورها وقتی وصل شود اجرا می‌شوند
              </div>
            )}
          </div>
        );
      })}

      {adding && (
        <TunnelForm password={password} nodes={data.nodes} engines={data.engines}
          onClose={() => setAdding(false)}
          onDone={() => { setAdding(false); reload(); setMsg({ t: "ok", m: "تانل ساخته شد" }); }} />
      )}

      {cfgFor && <TunnelConfigModal tunnel={cfgFor} password={password}
        onClose={() => setCfgFor(null)} />}
      {monFor && <TunnelMonitorModal tunnel={monFor} password={password}
        onClose={() => setMonFor(null)} />}
    </div>
  );
}

/** ساخت تانل */
function TunnelForm({ password, nodes, engines, onClose, onDone }) {
  const [f, setF] = useState({
    name: "", engine: "backhaul", transport: "tcpmux",
    node_id: nodes[0]?.id || "", remote_host: "", bridge_port: 3080,
  });
  const [ports, setPorts] = useState([{ local: 443, remote: 443 }]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const eng = engines.find((e) => e.key === f.engine);

  const submit = async () => {
    setBusy(true); setErr("");
    try {
      const res = await fetch(`${API_URL}/api/admin/tunnel`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ ...f, ports }),
      });
      const d = await res.json();
      if (res.ok) onDone();
      else setErr(d.detail || "ساخت ناموفق");
    } catch { setErr("اتصال برقرار نشد"); }
    finally { setBusy(false); }
  };

  return (
    <Modal title="تانل جدید" onClose={onClose} width="560px"
      footer={
        <button onClick={submit} disabled={busy || !f.name.trim() || !f.remote_host.trim()}
          className="fx-btn w-full py-3 text-[14px] flex items-center justify-center gap-2">
          {busy ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
          ساخت تانل
        </button>
      }>
      {/* راهنمای کامل — چون بدون این، معلوم نیست چه چیزی کجا می‌رود */}
      <div className="rounded-xl p-4 mb-4"
        style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>

        <div className="flex items-center gap-2 mb-3 text-[13px] flex-wrap" dir="ltr"
          style={{ fontFamily: "var(--mono)" }}>
          <span style={{ color: "var(--muted)" }}>مشتری</span>
          <span style={{ color: "var(--accent-2)" }}>──►</span>
          <span style={{ color: "var(--ok)", fontWeight: 700 }}>سرور ایران</span>
          <span style={{ color: "var(--accent-2)" }}>──►</span>
          <span style={{ color: "var(--dim)" }}>سرور خارج</span>
        </div>

        <div className="text-[13px] leading-relaxed mb-3" style={{ color: "var(--muted)" }}>
          مشتری به <b style={{ color: "var(--ok)" }}>سرور ایران</b> وصل می‌شود.
          سرور ایران ترافیک را از تانل به سرور خارج می‌فرستد.
        </div>

        <div className="text-[13px] font-semibold mb-2" style={{ color: "var(--dim)" }}>
          سه مرحله:
        </div>
        {[
          ["این فرم را پر کنید", "پورت‌هایی که مشتری به آن‌ها وصل می‌شود"],
          ["دکمه‌ی «اعمال» را بزنید", "agent روی سرور ایران خودش نصب و راه‌اندازی می‌کند"],
          ["کانفیگ سرور خارج را کپی کنید",
           "چون آنجا agent نصب نیست، این یک مرحله دستی است"],
        ].map(([t, d], i) => (
          <div key={i} className="flex gap-2.5 mb-2">
            <span className="shrink-0 flex items-center justify-center text-[12px] font-bold"
              style={{
                width: 18, height: 18, borderRadius: "50%",
                background: "var(--accent-soft)", color: "var(--accent-2)",
              }}>{faNum(i + 1)}</span>
            <div className="min-w-0">
              <div className="text-[13px]" style={{ color: "var(--dim)" }}>{t}</div>
              <div className="text-[12px] mt-0.5" style={{ color: "var(--muted)" }}>{d}</div>
            </div>
          </div>
        ))}
      </div>

      <Field label="نام">
        <input className="fx-input" value={f.name}
          onChange={(e) => setF({ ...f, name: e.target.value })}
          placeholder="تانل اصلی" />
      </Field>

      <Field label="موتور">
        <div className="fx-g4 grid grid-cols-2 gap-2">
          {engines.map((e) => {
            const on = f.engine === e.key;
            const col = ENGINE_COLOR[e.key];
            return (
              <button key={e.key}
                onClick={() => setF({ ...f, engine: e.key, transport: e.default_transport })}
                className="p-3 rounded-xl text-right"
                style={{
                  background: on ? `color-mix(in srgb, ${col} 12%, transparent)` : "var(--surface-3)",
                  border: `1px solid ${on ? col : "var(--border)"}`,
                }}>
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-bold" style={{ color: on ? col : "var(--dim)" }}>
                    {e.name}
                  </span>
                  {e.recommended && (
                    <span className="text-[11px] px-1.5 py-0.5 rounded"
                      style={{ background: "rgba(52,211,153,.14)", color: "var(--ok)" }}>
                      پیشنهادی
                    </span>
                  )}
                </div>
                <div className="text-[12px] mt-1 leading-relaxed" style={{ color: "var(--muted)" }}>
                  {e.desc}
                </div>
              </button>
            );
          })}
        </div>
      </Field>

      <div className="fx-g3 grid grid-cols-2 gap-3">
        <Field label="سرور ایران" hint="پورت‌ها اینجا باز می‌شوند">
          <select className="fx-input" value={f.node_id}
            onChange={(e) => setF({ ...f, node_id: e.target.value })}>
            {nodes.map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
          </select>
        </Field>
        <Field label="سرور خارج"
          hint="اگر agent دارد، پنل خودش راه‌اندازی می‌کند">
          <select className="fx-input" value={f.foreign_node || ""}
            onChange={(e) => setF({ ...f, foreign_node: e.target.value })}>
            <option value="">دستی — کانفیگ را کپی می‌کنم</option>
            {nodes.filter((n) => String(n.id) !== String(f.node_id))
              .map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
          </select>
        </Field>
      </div>

      <div className="fx-g3 grid grid-cols-2 gap-3">
        <Field label="پروتکل انتقال">
          <select className="fx-input" value={f.transport}
            onChange={(e) => setF({ ...f, transport: e.target.value })}>
            {(eng?.transports || []).map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </Field>
      </div>

      <div className="fx-g3 grid grid-cols-2 gap-3">
        <Field label="آی‌پی عمومی سرور ایران"
          hint="همان سروری که بالا انتخاب کردید — سرور خارج به این آدرس وصل می‌شود">
          <input className="fx-input" dir="ltr" value={f.remote_host}
            onChange={(e) => setF({ ...f, remote_host: e.target.value })}
            placeholder="1.2.3.4" style={{ fontFamily: "var(--mono)" }} />
        </Field>
        <Field label="پورت ارتباط" hint="پورتی که دو سرور از آن حرف می‌زنند">
          <input className="fx-input" type="text" inputMode="numeric" dir="ltr"
            value={f.bridge_port}
            onChange={(e) => setF({ ...f,
              bridge_port: e.target.value.replace(/[^0-9]/g, "").slice(0, 5) })}
            placeholder="3080"
            style={{ fontFamily: "var(--mono)" }} />
        </Field>
      </div>

      <Field label="پورت‌ها" hint="پورت‌هایی که مشتری به آن‌ها وصل می‌شود">
        {/* هر پورت یک قوطی باریک — عدد چهار رقمی به عرض بیشتری نیاز ندارد،
            و کنار هم بودنشان دیدن کل فهرست را آسان می‌کند */}
        <div className="flex gap-2 flex-wrap mb-2.5">
          {ports.map((p, i) => (
            <div key={i} className="flex items-center rounded-xl overflow-hidden"
              style={{ background: "var(--surface-3)", border: "1px solid var(--border-2)" }}>
              {/* type=text نه number — چون فلش‌های بالا/پایین برای عددی
                  که مستقیم تایپ می‌شود فقط مزاحمند */}
              <input type="text" inputMode="numeric" dir="ltr"
                value={p.local || ""}
                onChange={(e) => {
                  const digits = e.target.value.replace(/[^0-9]/g, "").slice(0, 5);
                  const v = digits ? parseInt(digits, 10) : 0;
                  const l = [...ports];
                  l[i] = { local: v, remote: v };
                  setPorts(l);
                }}
                placeholder="443"
                style={{
                  width: 68, background: "transparent", border: "none", outline: "none",
                  color: "var(--text)", fontSize: 12.5, padding: "8px 10px",
                  textAlign: "center", fontFamily: "var(--mono)",
                }} />
              <button onClick={() => setPorts(ports.filter((_, x) => x !== i))}
                className="flex items-center justify-center transition-colors"
                style={{
                  width: 28, height: 34, border: "none", cursor: "pointer",
                  background: "rgba(255,255,255,.03)", color: "var(--muted)",
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = "var(--danger)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = "var(--muted)"; }}>
                <X size={12} />
              </button>
            </div>
          ))}

          <button onClick={() => setPorts([...ports, { local: 0, remote: 0 }])}
            className="flex items-center gap-1.5 px-3 rounded-xl text-[13px] transition-all"
            style={{
              height: 34, background: "transparent",
              border: "1px dashed var(--border-2)", color: "var(--muted)", cursor: "pointer",
            }}>
            <PlusIcon size={12} /> افزودن
          </button>
        </div>

        {/* میان‌برهای پورت‌های رایج */}
        <div className="flex gap-1.5 flex-wrap">
          {[443, 8443, 2053, 2087, 80].map((q) => {
            const has = ports.some((p) => p.local === q);
            return (
              <button key={q}
                onClick={() => setPorts(has
                  ? ports.filter((p) => p.local !== q)
                  : [...ports, { local: q, remote: q }])}
                className="px-2.5 py-1 rounded-lg text-[12px] transition-all"
                style={{
                  background: has ? "var(--accent-soft)" : "transparent",
                  border: `1px solid ${has ? "rgba(43,127,214,.4)" : "var(--border)"}`,
                  color: has ? "var(--accent-2)" : "var(--muted)",
                  fontFamily: "var(--mono)",
                  cursor: "pointer",
                }}>
                {q}
              </button>
            );
          })}
        </div>
      </Field>

      {err && <div className="text-[13px] p-3 rounded-xl mt-3"
        style={{ background: "rgba(248,113,113,.1)", color: "var(--danger)" }}>{err}</div>}

    </Modal>
  );
}


/* ── کیفیت تانل ── */

const QUALITY_COLOR = {
  "عالی": "var(--ok)",
  "خوب": "#5AA9E6",
  "متوسط": "var(--warn)",
  "ضعیف": "var(--danger)",
  "نامشخص": "var(--muted)",
};

function TunnelMonitorModal({ tunnel, password, onClose }) {
  const [m, setM] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/tunnel/${tunnel.id}/metrics`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setM(d);
      return d;
    } catch {
      setM({ samples: [], summary: null });
      return null;
    }
  };

  useEffect(() => { load(); }, [tunnel.id]);

  const measure = async () => {
    setBusy(true);
    const before = m?.samples?.length || 0;
    try {
      await fetch(`${API_URL}/api/admin/tunnel/${tunnel.id}/monitor`, {
        method: "POST",
        headers: { "X-Admin-Password": password },
      });
      // agent تا ۳۰ ثانیه بعد سر می‌زند، پس چند بار نتیجه را چک می‌کنیم
      for (let i = 0; i < 12; i++) {
        await new Promise((r) => setTimeout(r, 4000));
        const d = await load();
        if ((d?.samples?.length || 0) > before) break;
      }
    } finally {
      setBusy(false);
    }
  };

  const s = m?.summary;
  const detail = m?.latest?.detail || {};
  const samples = m?.samples || [];
  const qc = QUALITY_COLOR[s?.quality] || "var(--muted)";

  const Bar = ({ label, value, unit = "ms", max = 200, color }) => (
    <div className="mb-3">
      <div className="flex justify-between text-[13px] mb-1.5">
        <span style={{ color: "var(--muted)" }}>{label}</span>
        <span style={{ color: color || "var(--dim)",
                       fontFamily: "var(--mono)" }}>
          {value === null || value === undefined ? "—" : `${faNum(value)} ${unit}`}
        </span>
      </div>
      <div style={{ height: 5, borderRadius: 99,
                    background: "rgba(255,255,255,.06)", overflow: "hidden" }}>
        <div style={{
          width: `${Math.min(100, ((value || 0) / max) * 100)}%`,
          height: "100%", background: color || "var(--accent)",
          transition: "width .4s ease",
        }} />
      </div>
    </div>
  );

  return (
    <Modal title={`کیفیت — ${tunnel.name}`} onClose={onClose} width="540px">
      {!m ? (
        <div className="flex justify-center py-8">
          <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} />
        </div>
      ) : (
        <>
          {s ? (
            <>
              <div className="rounded-2xl p-4 mb-4 text-center"
                style={{
                  background: `color-mix(in srgb, ${qc} 10%, transparent)`,
                  border: `1px solid color-mix(in srgb, ${qc} 28%, transparent)`,
                }}>
                <div className="text-[28px] font-extrabold"
                  style={{ color: qc, fontFamily: "var(--mono)" }}>
                  {faNum(s.latest)} <span className="text-[16px]">ms</span>
                </div>
                <div className="text-[13px] mt-1" style={{ color: qc }}>{s.quality}</div>
                <div className="text-[12px] mt-2" style={{ color: "var(--muted)" }}>
                  از {faNum(s.count)} سنجش · بهترین {faNum(s.best)} · بدترین {faNum(s.worst)}
                </div>
              </div>

              {samples.length > 1 && (
                <div className="mb-4">
                  <div className="text-[13px] mb-2" style={{ color: "var(--muted)" }}>روند</div>
                  <div className="flex items-end gap-1" style={{ height: 48 }}>
                    {samples.slice(-30).map((x, i) => {
                      const v = x.tcp_avg || 0;
                      const mx = Math.max(...samples.map((y) => y.tcp_avg || 0), 1);
                      const col = v > 150 ? "var(--danger)"
                                : v > 60 ? "var(--warn)" : "var(--accent)";
                      return (
                        <div key={i} title={`${v} ms`} style={{
                          flex: 1, height: `${Math.max(8, (v / mx) * 100)}%`,
                          background: col, borderRadius: "2px 2px 0 0", opacity: 0.85,
                        }} />
                      );
                    })}
                  </div>
                </div>
              )}

              <Bar label="تاخیر TCP — همان چیزی که ترافیک واقعی حس می‌کند"
                value={s.latest} max={200}
                color={s.latest > 150 ? "var(--danger)"
                     : s.latest > 60 ? "var(--warn)" : "var(--ok)"} />

              {detail.icmp?.ok && (
                <Bar label="پینگ ICMP" value={detail.icmp.avg} max={200} color="#A78BFA" />
              )}
              {detail.http?.ok && (
                <Bar label="پاسخ HTTP — کل مسیر تا سرویس"
                  value={detail.http.avg} max={600} color="#5AA9E6" />
              )}

              <div className="fx-g3 grid grid-cols-3 gap-3 mt-4">
                {[["نوسان", m.latest?.jitter, "ms"],
                  ["اتلاف بسته", s.lossAvg, "٪"],
                  ["میانگین", s.average, "ms"]].map(([l, v, u], i) => (
                  <div key={i} className="p-3 rounded-xl text-center"
                    style={{ background: "var(--surface-3)" }}>
                    <div className="text-[16px] font-bold"
                      style={{ color: "var(--text)",
                               fontFamily: "var(--mono)" }}>
                      {v === null || v === undefined ? "—" : faNum(v)}
                    </div>
                    <div className="text-[11.5px] mt-1" style={{ color: "var(--muted)" }}>
                      {l} {u && `(${u})`}
                    </div>
                  </div>
                ))}
              </div>

              <InfoBox>
                تاخیر TCP از پینگ معمولی معنادارتر است، چون همان کاری را می‌کند که
                ترافیک واقعی می‌کند. اگر ICMP خوب باشد ولی TCP بالا، مشکل از خود
                تانل است نه مسیر شبکه.
              </InfoBox>
            </>
          ) : (
            <div className="text-center py-8">
              <Activity size={26} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
              <div className="text-[14px]" style={{ color: "var(--muted)" }}>
                هنوز سنجشی انجام نشده
              </div>
            </div>
          )}

          <button onClick={measure} disabled={busy || !tunnel.nodeOnline}
            className="fx-btn w-full py-3 text-[14px] flex items-center justify-center gap-2 mt-4"
            style={!tunnel.nodeOnline ? { opacity: 0.4, cursor: "not-allowed" } : {}}>
            {busy
              ? <><Loader2 size={14} className="animate-spin" /> در حال سنجش…</>
              : <><Activity size={14} /> سنجش جدید</>}
          </button>

          {!tunnel.nodeOnline && (
            <div className="text-[12px] mt-2 text-center" style={{ color: "var(--warn)" }}>
              سرور آفلاین است — دستور وقتی وصل شود اجرا می‌شود
            </div>
          )}
        </>
      )}
    </Modal>
  );
}

/** کانفیگ سمت خارج */
function TunnelConfigModal({ tunnel, password, onClose }) {
  const [cfg, setCfg] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/api/admin/tunnel/${tunnel.id}/config?side=foreign`, {
      headers: { "X-Admin-Password": password },
    }).then((r) => r.json()).then(setCfg).catch(() => setCfg({ config: "" }));
  }, [tunnel.id]);

  const copy = () => {
    navigator.clipboard?.writeText(cfg?.config || "");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Modal title="کانفیگ سرور خارج" onClose={onClose} width="600px">
      <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
        این فایل را روی سرور خارج بگذارید. چون آنجا agent نصب نیست،
        این یک مرحله دستی است.
      </p>

      {!cfg ? (
        <div className="flex justify-center py-8">
          <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>
      ) : (
        <>
          <div className="rounded-xl p-3.5 mb-3 overflow-auto" dir="ltr"
            style={{ background: "var(--surface-3)", border: "1px solid var(--border)", maxHeight: 300 }}>
            <pre className="text-[13px] leading-relaxed whitespace-pre-wrap"
              style={{ color: "var(--dim)", fontFamily: "var(--mono)" }}>
              {cfg.config}
            </pre>
          </div>
          <div className="text-[12px] mb-3" dir="ltr"
            style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
            {cfg.filename}
          </div>
          <button onClick={copy}
            className="fx-btn w-full py-2.5 text-[14px] flex items-center justify-center gap-2">
            {copied ? <><Check size={14} /> کپی شد</> : <><Copy size={14} /> کپی کانفیگ</>}
          </button>
        </>
      )}
    </Modal>
  );
}


/* ── سلامت سرورها ── */

const HEALTH_COLOR = {
  ok: "var(--ok)", warn: "var(--warn)",
  crit: "var(--danger)", unknown: "var(--muted)",
};
const HEALTH_LABEL = {
  ok: "سالم", warn: "هشدار", crit: "مشکل جدی", unknown: "نامشخص",
};

function SystemHealth({ password }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/health/all`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setData(d);
    } catch {
      setData({ ready: false, servers: [] });
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [password]);
  usePolling(load, 60000, [password]);

  const recheck = async () => {
    setBusy(true);
    try {
      for (const s of data?.servers || []) {
        if (s.nodeId) {
          await fetch(`${API_URL}/api/admin/health/check/${s.nodeId}`, {
            method: "POST", headers: { "X-Admin-Password": password } });
        }
      }
      await new Promise((r) => setTimeout(r, 3000));
      await load();
    } finally { setBusy(false); }
  };

  if (loading) return <div className="flex justify-center py-16">
    <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  const servers = data?.servers || [];
  const worst = HEALTH_COLOR[data?.level] || "var(--muted)";

  return (
    <div className="fx-anim">
      <SectionHead title="سلامت سرورها"
        desc="هر ۵ دقیقه خودکار بررسی می‌شود و اگر مشکلی پیدا شود، در تلگرام خبر می‌دهد."
        action={
          <button onClick={recheck} disabled={busy}
            className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
            {busy ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
            بررسی دوباره
          </button>
        } />

      <div className="fx-card p-5 mb-4" style={{
        borderColor: data?.level === "crit" ? "rgba(248,113,113,.4)"
                   : data?.level === "warn" ? "rgba(251,191,36,.35)" : undefined }}>
        <div className="flex items-center gap-3">
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: worst,
                        boxShadow: `0 0 10px ${worst}`, flexShrink: 0 }} />
          <div className="min-w-0">
            <div className="text-[16px] font-bold" style={{ color: worst }}>
              {HEALTH_LABEL[data?.level] || "نامشخص"}
            </div>
            <div className="text-[13px] mt-0.5" style={{ color: "var(--muted)" }}>
              {faNum(servers.length)} سرور · آخرین بررسی {data?.at?.slice(11, 16) || "—"}
            </div>
          </div>
        </div>
      </div>

      {servers.map((s, i) => {
        const col = HEALTH_COLOR[s.level] || "var(--muted)";
        const problems = (s.checks || []).filter((c) => c.level !== "ok");
        const fine = (s.checks || []).filter((c) => c.level === "ok");
        return (
          <div key={i} className="fx-card p-5 mb-3">
            <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
              <div className="flex items-center gap-2.5 min-w-0">
                <Circle size={8} fill={col} strokeWidth={0} />
                <span className="text-[14px] font-bold text-white">{s.server}</span>
              </div>
              <span className="text-[13px]" style={{ color: col }}>{s.summary}</span>
            </div>

            {problems.map((c, j) => (
              <div key={j} className="p-3.5 rounded-xl mb-2"
                style={{
                  background: c.level === "crit"
                    ? "rgba(248,113,113,.07)" : "rgba(251,191,36,.07)",
                  border: `1px solid ${c.level === "crit"
                    ? "rgba(248,113,113,.2)" : "rgba(251,191,36,.2)"}`,
                }}>
                <div className="flex justify-between items-baseline gap-3 flex-wrap">
                  <span className="text-[14px] font-semibold"
                    style={{ color: HEALTH_COLOR[c.level] }}>{c.title}</span>
                  <span className="text-[13px]" style={{ color: "var(--dim)" }}>
                    {c.detail}
                  </span>
                </div>
                {c.hint && (
                  <div className="text-[13px] mt-2 leading-relaxed"
                    style={{ color: "var(--muted)" }}>{c.hint}</div>
                )}
              </div>
            ))}

            {fine.length > 0 && (
              <div className="flex gap-1.5 flex-wrap mt-3">
                {fine.map((c, j) => (
                  <span key={j} className="text-[12px] px-2 py-1 rounded-lg"
                    style={{ background: "var(--surface-3)", color: "var(--muted)" }}
                    title={c.detail}>
                    ✓ {c.title}
                  </span>
                ))}
              </div>
            )}

            {(s.checks || []).length === 0 && (
              <div className="text-[13px]" style={{ color: "var(--muted)" }}>
                {s.summary || "گزارشی نرسیده"}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── سلامت سرورها پایان ── */

/* ── رویدادها ── */
function TunnelEvents({ password }) {
  const { data, loading } = useTunnel(password);

  if (loading) return <div className="flex justify-center py-16">
    <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  const events = data?.events || [];
  const color = { error: "var(--danger)", warn: "var(--warn)", info: "var(--muted)" };

  return (
    <div className="fx-anim">
      <SectionHead title="رویدادها" desc="آنچه روی سرورها اتفاق افتاده." />

      {events.length === 0 ? (
        <div className="fx-card p-10 text-center" style={{ borderStyle: "dashed" }}>
          <Clock size={26} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
          <div className="text-[14px]" style={{ color: "var(--muted)" }}>هنوز رویدادی ثبت نشده</div>
        </div>
      ) : (
        <div className="fx-card overflow-hidden" style={{ padding: 0 }}>
          {events.map((e, i) => (
            <div key={e.id} className="flex items-start gap-3 p-4"
              style={{ borderBottom: i < events.length - 1 ? "1px solid var(--border)" : "none" }}>
              <Circle size={7} fill={color[e.level] || "var(--muted)"} strokeWidth={0}
                style={{ marginTop: 5, flexShrink: 0 }} />
              <div className="min-w-0 flex-1">
                <div className="text-[13px]" style={{ color: "var(--dim)" }}>{e.message}</div>
                <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
                  {e.node_name && `${e.node_name} · `}
                  {e.created_at?.replace("T", " ").slice(0, 16)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


/* ── صورتحساب دوره ── */

function BillingPeriod({ password }) {
  const { data } = useBilling(password);
  const [sel, setSel] = useState("");
  const [inv, setInv] = useState(null);
  const [loading, setLoading] = useState(false);
  const [shift, setShift] = useState(0);
  const [custom, setCustom] = useState(false);
  const [range, setRange] = useState({ start: "", end: "" });

  const billed = data?.groups?.filter((g) => g.billed) || [];
  useEffect(() => { if (!sel && billed.length) setSel(billed[0].name); }, [data]);

  const load = async (offset = 0, manual = null) => {
    if (!sel) return;
    setLoading(true);
    try {
      let q = "";
      if (manual && manual.start && manual.end) {
        q = `?start=${manual.start}&end=${manual.end}`;
      } else if (offset !== 0) {
        // دوره‌های قبل و بعد را با جابه‌جایی تاریخ می‌گیریم
        const g = billed.find((x) => x.name === sel);
        const days = g?.periodDays || 30;
        const base = inv?.period?.start
          ? new Date(inv.period.start) : new Date();
        const s = new Date(base);
        s.setDate(s.getDate() + offset * days);
        const e = new Date(s);
        e.setDate(e.getDate() + days);
        q = `?start=${s.toISOString().slice(0, 10)}&end=${e.toISOString().slice(0, 10)}`;
      }
      const d = await fetch(
        `${API_URL}/api/admin/billing/period/${encodeURIComponent(sel)}${q}`,
        { headers: { "X-Admin-Password": password } }).then((r) => r.json());
      setInv(d);
    } catch { setInv({ ready: false, error: "اتصال برقرار نشد" }); }
    finally { setLoading(false); }
  };

  useEffect(() => { setShift(0); load(0); }, [sel]);

  const move = (dir) => { setShift(shift + dir); load(dir); };

  if (!data?.ready) {
    return (
      <div className="fx-anim">
        <SectionHead title="صورتحساب دوره" desc="" />
        <BillingUnavailable info={data} password={password} />
      </div>
    );
  }

  const t = inv?.totals;
  const p = inv?.period;

  return (
    <div className="fx-anim">
      <SectionHead title="صورتحساب دوره"
        desc="فقط کانفیگ‌ها و تمدیدهای همین دوره — نه کل بدهی از ابتدا." />

      {billed.length === 0 ? (
        <div className="fx-card p-10 text-center" style={{ borderStyle: "dashed" }}>
          <Users size={26} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
          <div className="text-[14px]" style={{ color: "var(--muted)" }}>
            ابتدا یک گروه را واسطه علامت بزنید
          </div>
        </div>
      ) : (
        <>
          <div className="fx-card p-5 mb-4">
            <div className="fx-g3 grid grid-cols-2 gap-3">
              <Field label="واسطه">
                <select className="fx-input" value={sel}
                  onChange={(e) => setSel(e.target.value)}>
                  {billed.map((g) => (
                    <option key={g.name} value={g.name}>{g.label}</option>
                  ))}
                </select>
              </Field>
              <Field label="دوره">
                {custom ? (
                  <div className="flex items-center gap-2">
                    <div className="flex-1 text-center py-2 rounded-xl text-[13px]"
                      style={{ background: "var(--surface-3)", color: "var(--dim)" }}>
                      {p ? `${p.startJalali} تا ${p.endJalali}` : "بازه دلخواه"}
                    </div>
                    <button onClick={() => { setCustom(false); setShift(0); load(0); }}
                      className="fx-ico-btn shrink-0" title="بازگشت به دوره‌ها">
                      <RefreshCw size={13} />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <button onClick={() => move(-1)} className="fx-ico-btn shrink-0">
                      <ChevronLeft size={14} />
                    </button>
                    <div className="flex-1 text-center py-2 rounded-xl text-[13px]"
                      style={{ background: "var(--surface-3)", color: "var(--dim)" }}>
                      {p ? `${p.startJalali} تا ${p.endJalali}` : "—"}
                    </div>
                    <button onClick={() => move(1)} className="fx-ico-btn shrink-0"
                      style={{ transform: "rotate(180deg)" }}>
                      <ChevronLeft size={14} />
                    </button>
                  </div>
                )}
              </Field>
            </div>

            {/* بازه‌ی دلخواه — وقتی می‌خواهید بازه‌ای غیر از دوره‌های
                خودکار را ببینید، مثلاً برای توافق خاص با یک واسطه */}
            <div className="mt-4 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
              <div className="flex justify-between items-center mb-3 flex-wrap gap-2">
                <span className="text-[13px]" style={{ color: "var(--dim)" }}>
                  بازه‌ی دلخواه
                </span>
                <div className="flex gap-1.5 flex-wrap">
                  {[["هفته گذشته", 7], ["دو هفته", 14],
                    ["ماه گذشته", 30], ["سه ماه", 90]].map(([l, n]) => (
                    <button key={n}
                      onClick={() => {
                        const e = new Date();
                        const s = new Date();
                        s.setDate(s.getDate() - n);
                        const r = { start: s.toISOString().slice(0, 10),
                                    end: e.toISOString().slice(0, 10) };
                        setRange(r); setCustom(true); load(0, r);
                      }}
                      className="px-2.5 py-1 rounded-lg text-[12px]"
                      style={{ background: "transparent",
                               border: "1px solid var(--border)",
                               color: "var(--muted)" }}>{l}</button>
                  ))}
                </div>
              </div>

              <div className="fx-g3 grid grid-cols-3 gap-2">
                <input className="fx-input" dir="ltr" value={range.start}
                  onChange={(e) => setRange({ ...range, start: e.target.value })}
                  placeholder="از  2026-08-01"
                  style={{ fontFamily: "var(--mono)" }} />
                <input className="fx-input" dir="ltr" value={range.end}
                  onChange={(e) => setRange({ ...range, end: e.target.value })}
                  placeholder="تا  2026-08-15"
                  style={{ fontFamily: "var(--mono)" }} />
                <button
                  onClick={() => { setCustom(true); load(0, range); }}
                  disabled={!range.start || !range.end}
                  className="fx-btn py-2.5 text-[13px] flex items-center justify-center gap-1.5"
                  style={(!range.start || !range.end)
                    ? { opacity: .45, cursor: "not-allowed" } : {}}>
                  <FileText size={13} /> فاکتور
                </button>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="flex justify-center py-14">
              <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} />
            </div>
          ) : !inv?.ready ? (
            <div className="fx-card p-8 text-center" style={{ borderStyle: "dashed" }}>
              <div className="text-[13px]" style={{ color: "var(--muted)" }}>
                {inv?.error || "خطا در خواندن"}
              </div>
            </div>
          ) : (
            <>
              {/* خلاصه */}
              <div className="fx-card p-5 mb-4">
                <div className="flex justify-between items-baseline mb-4 flex-wrap gap-2">
                  <span className="text-[14px] font-semibold text-white">
                    بدهی این دوره
                  </span>
                  <span className="text-[24px] font-extrabold"
                    style={{ color: "var(--accent-2)",
                             fontFamily: "var(--mono)" }}>
                    {faNum(t.due)} <span className="text-[13px]">تومان</span>
                  </span>
                </div>

                {inv.perGb ? (
                  <div className="p-3 rounded-xl text-[13px]"
                    style={{ background: "var(--surface-3)", color: "var(--dim)" }}>
                    نرخ حجمی — بر اساس مصرف کل گروه
                  </div>
                ) : (
                  <div className="fx-g3 grid grid-cols-2 gap-3">
                    {[["کانفیگ جدید", t.newCount, t.newAmount, "var(--ok)"],
                      ["تمدید", t.renewalCount, t.renewalAmount, "var(--accent-2)"]
                    ].map(([l, n, amt, col], i) => (
                      <div key={i} className="p-3.5 rounded-xl"
                        style={{ background: "var(--surface-3)" }}>
                        <div className="flex justify-between items-baseline">
                          <span className="text-[13px]" style={{ color: "var(--muted)" }}>{l}</span>
                          <span className="text-[16px] font-bold" style={{ color: col,
                                fontFamily: "var(--mono)" }}>
                            {faNum(n)}
                          </span>
                        </div>
                        <div className="text-[13px] mt-1.5" style={{ color: "var(--dim)",
                             fontFamily: "var(--mono)" }}>
                          {faNum(amt)} تومان
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <div className="flex justify-between mt-4 pt-3 text-[13px]"
                  style={{ borderTop: "1px solid var(--border)" }}>
                  <span style={{ color: "var(--muted)" }}>پرداخت‌شده در این دوره</span>
                  <span style={{ color: "var(--ok)",
                                 fontFamily: "var(--mono)" }}>
                    {faNum(t.paid)}
                  </span>
                </div>
                <div className="flex justify-between mt-2 text-[14px] font-bold">
                  <span className="text-white">مانده</span>
                  <span style={{ color: t.balance > 0 ? "var(--warn)" : "var(--ok)",
                                 fontFamily: "var(--mono)" }}>
                    {faNum(t.balance)} تومان
                  </span>
                </div>

                {inv.settledUntil && (
                  <div className="text-[12px] mt-3" style={{ color: "var(--muted)" }}>
                    {faNum(inv.skippedSettled)} کانفیگ قبل از {inv.settledUntil} تسویه‌شده
                    فرض شده و در محاسبه نیامده
                  </div>
                )}
              </div>

              {/* ریز */}
              {[["کانفیگ‌های جدید", inv.newConfigs, "var(--ok)"],
                ["تمدیدها", inv.renewals, "var(--accent-2)"]].map(([title, rows, col]) => (
                rows.length > 0 && (
                  <div key={title} className="fx-card p-5 mb-4">
                    <div className="text-[14px] font-semibold text-white mb-3">
                      {title} <span style={{ color: "var(--muted)" }}>({faNum(rows.length)})</span>
                    </div>
                    {rows.map((x, i) => (
                      <div key={i} className="flex justify-between items-center gap-3 py-2.5 flex-wrap"
                        style={{ borderBottom: i < rows.length - 1 ? "1px solid var(--border)" : "none" }}>
                        <div className="min-w-0">
                          <div className="text-[13px]" dir="ltr"
                            style={{ color: "var(--dim)", textAlign: "right",
                                     fontFamily: "var(--mono)" }}>
                            {x.email}
                          </div>
                          <div className="text-[12px] mt-0.5" style={{ color: "var(--muted)" }}>
                            {x.dateJalali || x.date} · {x.gbLabel}
                            {x.kind === "تخمینی" && (
                              <span style={{ color: "var(--warn)" }}> · تخمینی</span>
                            )}
                          </div>
                        </div>
                        <span className="text-[14px] font-bold shrink-0"
                          style={{ color: x.price === null ? "var(--warn)" : col,
                                   fontFamily: "var(--mono)" }}>
                          {x.price === null ? "بدون نرخ" : faNum(x.amount)}
                        </span>
                      </div>
                    ))}
                  </div>
                )
              ))}

              {t.estimated > 0 && (
                <InfoBox tone="warn">
                  {faNum(t.estimated)} تمدید تخمینی است — تاریخش از فاصله‌ی ایجاد تا
                  انقضا حدس زده شده، نه از ثبت واقعی. تمدیدهایی که از نکسورا انجام
                  شوند تاریخ قطعی دارند.
                </InfoBox>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

/* ── همه‌ی کاربران ── */

const CLIENT_STATUS_COLOR = {
  "فعال": "var(--ok)",
  "رو به انقضا": "var(--warn)",
  "منقضی": "var(--danger)",
  "غیرفعال": "var(--muted)",
  "بدون انقضا": "#A78BFA",
  "شروع‌نشده": "#5AA9E6",
};

function BillingClients({ password }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [group, setGroup] = useState("");
  const [status, setStatus] = useState("");
  const [renewed, setRenewed] = useState("");
  const [age, setAge] = useState("");
  const [priced, setPriced] = useState("");
  const [dates, setDates] = useState({ from: "", to: "" });
  const [sort, setSort] = useState("created");
  const [order, setOrder] = useState("desc");
  const [page, setPage] = useState(0);
  const [detail, setDetail] = useState(null);
  const PER = 60;

  const load = async () => {
    setLoading(true);
    try {
      const p = new URLSearchParams({
        q, group, status, renewed, age, priced, sort, order,
        created_from: dates.from, created_to: dates.to,
        limit: String(PER), offset: String(page * PER),
      });
      const d = await fetch(`${API_URL}/api/admin/billing/clients?${p}`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setData(d);
    } catch {
      setData({ ready: false, error: "اتصال به سرور برقرار نشد", clients: [] });
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); },
    [password, group, status, renewed, age, priced, dates, sort, order, page]);

  // جستجو با تاخیر — تا با هر حرف یک درخواست نرود
  useEffect(() => {
    const t = setTimeout(() => { setPage(0); load(); }, 400);
    return () => clearTimeout(t);
  }, [q]);

  const exportCsv = async () => {
    try {
      // همان فیلترهای صفحه — وگرنه باید در اکسل دوباره فیلتر کنید
      const p = new URLSearchParams({
        q, group, status, renewed, age, priced, sort, order,
        created_from: dates.from, created_to: dates.to,
      });
      const res = await fetch(`${API_URL}/api/admin/billing/clients/export?${p}`, {
        headers: { "X-Admin-Password": password } });
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `nexora-clients-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch { /* بی‌صدا */ }
  };

  const th = (key, label, w) => {
    const on = sort === key;
    return (
      <th key={key} onClick={() => {
        if (on) setOrder(order === "asc" ? "desc" : "asc");
        else { setSort(key); setOrder("desc"); }
        setPage(0);
      }}
        className="px-3 py-3 cursor-pointer select-none whitespace-nowrap text-[13px] transition-colors"
        style={{ width: w, color: on ? "var(--accent-2)" : "var(--muted)",
                 fontWeight: on ? 700 : 600 }}>
        <span className="inline-flex items-center gap-1">
          {label}
          <span style={{ opacity: on ? 1 : 0.25, fontSize: 9 }}>
            {on ? (order === "asc" ? "▲" : "▼") : "▼"}
          </span>
        </span>
      </th>
    );
  };

  if (loading && !data) {
    return <div className="flex justify-center py-16">
      <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;
  }

  if (!data?.ready) {
    return (
      <div className="fx-anim">
        <SectionHead title="همه کاربران" desc="" />
        <BillingUnavailable info={data} password={password} />
      </div>
    );
  }

  const s = data.stats;
  const pages = Math.ceil(data.total / PER);

  return (
    <div className="fx-anim">
      <SectionHead title="همه کاربران"
        desc="هر کانفیگ روی سرور — از هر گروه، و آن‌هایی که گروه ندارند."
        action={
          <div className="flex gap-2">
            <button onClick={exportCsv} className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
              <Download size={13} /> خروجی اکسل
            </button>
            <button onClick={load} className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
              <RefreshCw size={13} /> تازه‌سازی
            </button>
          </div>
        } />

      {/* آمار */}
      <div className="fx-g4 grid grid-cols-4 gap-3 mb-4">
        {[["کل کانفیگ", s.total, "var(--accent-2)", Users],
          ["تمدید شده", s.renewed, "var(--ok)", RefreshCw, `${s.renewalRate}٪ نرخ تمدید`],
          ["بدون تمدید", s.notRenewed, "var(--warn)", Clock, "فقط دوره اول"],
          ["مصرف کل", `${faNum(s.usedGB)}`, "#A78BFA", TrendingUp, "گیگابایت"]
        ].map(([l, v, col, I, sub], i) => (
          <div key={i} className="fx-card fx-card-i p-4">
            <div className="fx-ico mb-3" style={{ background: `color-mix(in srgb, ${col} 12%, transparent)` }}>
              <I size={15} style={{ color: col }} />
            </div>
            <div className="fx-stat-num text-[21px] font-extrabold text-white leading-none"
              style={{ fontFamily: "var(--mono)" }}>{faNum(v)}</div>
            <div className="text-[12px] mt-1.5" style={{ color: "var(--dim)" }}>{l}</div>
            {sub && <div className="text-[11.5px] mt-1" style={{ color: "var(--muted)" }}>{sub}</div>}
          </div>
        ))}
      </div>

      {/* وضعیت‌ها — کلیک برای فیلتر */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {[["فعال", s.active], ["رو به انقضا", s.expiringSoon],
          ["منقضی", s.expired], ["غیرفعال", s.disabled]].map(([label, n]) => {
          const on = status === label;
          const col = CLIENT_STATUS_COLOR[label];
          return (
            <button key={label}
              onClick={() => { setStatus(on ? "" : label); setPage(0); }}
              className="px-3 py-2 rounded-xl text-[13px] transition-all flex items-center gap-2"
              style={{
                background: on ? `color-mix(in srgb, ${col} 16%, transparent)` : "var(--surface-3)",
                border: `1px solid ${on ? col : "var(--border)"}`,
                color: on ? col : "var(--dim)",
              }}>
              <Circle size={7} fill={col} strokeWidth={0} />
              {label}
              <span style={{ fontFamily: "var(--mono)", opacity: .8 }}>
                {faNum(n)}
              </span>
            </button>
          );
        })}
        {s.noGroup > 0 && (
          <button onClick={() => { setGroup(group === "بدون گروه" ? "" : "بدون گروه"); setPage(0); }}
            className="px-3 py-2 rounded-xl text-[13px] flex items-center gap-2"
            style={{
              background: group === "بدون گروه" ? "rgba(255,255,255,.06)" : "var(--surface-3)",
              border: `1px solid ${group === "بدون گروه" ? "var(--border-2)" : "var(--border)"}`,
              color: "var(--muted)",
            }}>
            بدون گروه <span style={{ fontFamily: "var(--mono)" }}>{faNum(s.noGroup)}</span>
          </button>
        )}
      </div>

      {/* فیلترها */}
      <div className="fx-card p-4 mb-4">
        <div className="fx-g3 grid grid-cols-3 gap-3">
          <div className="fx-search">
            <Search size={14} style={{ color: "var(--muted)" }} />
            <input value={q} onChange={(e) => setQ(e.target.value)}
              placeholder="جستجو در ایمیل، گروه یا یادداشت..." />
          </div>
          <select className="fx-input" value={group}
            onChange={(e) => { setGroup(e.target.value); setPage(0); }}>
            <option value="">همه گروه‌ها</option>
            {data.groups.map((g) => <option key={g} value={g}>{g}</option>)}
          </select>
          <select className="fx-input" value={renewed}
            onChange={(e) => { setRenewed(e.target.value); setPage(0); }}>
            <option value="">تمدید: همه</option>
            <option value="yes">فقط تمدیدشده‌ها</option>
            <option value="no">فقط بدون تمدید</option>
          </select>
        </div>
        {/* فیلترهای حسابداری — سه چیزی که موقع فاکتور لازم می‌شوند */}
        <div className="mt-4 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
          <div className="flex gap-1.5 flex-wrap mb-3">
            {[["تازه (۳۰ روز)", "age", "new", s.newLast30],
              ["قدیمی‌تر", "age", "old", s.olderThan30],
              ["بدون نرخ", "priced", "no", s.unpriced]].map(([label, key, val, n]) => {
              const cur = key === "age" ? age : priced;
              const on = cur === val;
              const setter = key === "age" ? setAge : setPriced;
              const col = key === "priced" ? "var(--warn)" : "var(--accent-2)";
              return (
                <button key={label}
                  onClick={() => { setter(on ? "" : val); setPage(0); }}
                  className="px-3 py-1.5 rounded-lg text-[13px] flex items-center gap-1.5"
                  style={{
                    background: on ? `color-mix(in srgb, ${col} 14%, transparent)` : "transparent",
                    border: `1px solid ${on ? col : "var(--border)"}`,
                    color: on ? col : "var(--muted)",
                  }}>
                  {label}
                  {n !== undefined && (
                    <span style={{ fontFamily: "var(--mono)", opacity: .8 }}>
                      {faNum(n)}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[12px] shrink-0" style={{ color: "var(--muted)" }}>
              ساخته‌شده بین
            </span>
            <input className="fx-input" dir="ltr" value={dates.from}
              onChange={(e) => { setDates({ ...dates, from: e.target.value }); setPage(0); }}
              placeholder="2026-08-01"
              style={{ width: 130, fontFamily: "var(--mono)",
                       fontSize: 11.5, padding: "7px 10px" }} />
            <span className="text-[12px]" style={{ color: "var(--muted)" }}>تا</span>
            <input className="fx-input" dir="ltr" value={dates.to}
              onChange={(e) => { setDates({ ...dates, to: e.target.value }); setPage(0); }}
              placeholder="2026-08-31"
              style={{ width: 130, fontFamily: "var(--mono)",
                       fontSize: 11.5, padding: "7px 10px" }} />

            {[["۷ روز", 7], ["۳۰ روز", 30]].map(([l, n]) => (
              <button key={n}
                onClick={() => {
                  const t = new Date();
                  const f = new Date();
                  f.setDate(f.getDate() - n);
                  setDates({ from: f.toISOString().slice(0, 10),
                             to: t.toISOString().slice(0, 10) });
                  setPage(0);
                }}
                className="px-2.5 py-1.5 rounded-lg text-[12px]"
                style={{ background: "transparent", border: "1px solid var(--border)",
                         color: "var(--muted)" }}>{l}</button>
            ))}
          </div>
        </div>

        {(q || group || status || renewed || age || priced || dates.from || dates.to) && (
          <button onClick={() => {
              setQ(""); setGroup(""); setStatus(""); setRenewed("");
              setAge(""); setPriced(""); setDates({ from: "", to: "" }); setPage(0);
            }}
            className="text-[13px] mt-3 flex items-center gap-1.5"
            style={{ color: "var(--accent-2)" }}>
            <X size={12} /> پاک کردن فیلترها ({faNum(data.total)} نتیجه)
          </button>
        )}
      </div>

      {/* جدول */}
      <div className="fx-card overflow-hidden" style={{ padding: 0 }}>
        <div style={{ overflowX: "auto" }}>
          <table className="w-full" style={{ borderCollapse: "collapse", minWidth: 1080 }}>
            <thead>
              <tr style={{ background: "var(--surface-3)", borderBottom: "1px solid var(--border-2)" }}>
                {th("email", "کاربر", "22%")}
                {th("group", "گروه", "13%")}
                <th className="px-3 py-3 text-[13px]" style={{ color: "var(--muted)", width: "11%" }}>وضعیت</th>
                {th("created", "ایجاد", "10%")}
                {th("expiry", "انقضا", "10%")}
                {th("remaining", "مانده", "8%")}
                {th("months", "ماه", "6%")}
                {th("renewals", "تمدید", "7%")}
                {th("used", "مصرف", "13%")}
                {th("amount", "مبلغ", "10%")}
              </tr>
            </thead>
            <tbody>
              {data.clients.map((c, i) => {
                const col = CLIENT_STATUS_COLOR[c.status] || "var(--muted)";
                const pctColor = c.usagePct === null ? "var(--muted)"
                  : c.usagePct >= 90 ? "var(--danger)"
                  : c.usagePct >= 70 ? "var(--warn)" : "var(--accent)";
                return (
                  <tr key={c.email} onClick={() => setDetail(c)}
                    className="cursor-pointer nx-row"
                    style={{
                      borderBottom: i < data.clients.length - 1 ? "1px solid var(--border)" : "none",
                      background: i % 2 ? "rgba(255,255,255,.015)" : "transparent",
                    }}>

                    {/* کاربر */}
                    <td className="px-3 py-3">
                      <div className="text-[14px] font-semibold" dir="ltr"
                        style={{ color: c.enable ? "var(--text)" : "var(--muted)",
                                 textAlign: "right",
                                 fontFamily: "var(--mono)" }}>
                        {c.email}
                      </div>
                      <div className="flex items-center gap-2 mt-1 flex-wrap">
                        <span className="text-[12px]" style={{ color: "var(--muted)" }}>
                          {c.gbLabel}
                        </span>
                        {c.limitIp > 0 && (
                          <span className="text-[12px] px-1.5 py-0.5 rounded"
                            style={{ background: "rgba(255,255,255,.05)", color: "var(--muted)" }}>
                            {faNum(c.limitIp)} دستگاه
                          </span>
                        )}
                        {c.resetCount > 0 && (
                          <span className="text-[12px] px-1.5 py-0.5 rounded"
                            style={{ background: "rgba(167,139,250,.14)", color: "#A78BFA" }}>
                            {faNum(c.resetCount)} ریست
                          </span>
                        )}
                        {c.tgId > 0 && (
                          <span className="text-[12px] px-1.5 py-0.5 rounded flex items-center gap-1"
                            style={{ background: "rgba(34,158,217,.14)", color: "#229ED9" }}>
                            <Send size={9} /> تلگرام
                          </span>
                        )}
                      </div>
                      {c.comment && (
                        <div className="text-[12px] mt-1.5 truncate" style={{ color: "var(--muted)", maxWidth: 240 }}>
                          {c.comment}
                        </div>
                      )}
                    </td>

                    {/* گروه */}
                    <td className="px-3 py-3">
                      <div className="text-[14px]" style={{ color: "var(--dim)" }}>
                        {c.groupLabel}
                      </div>
                      {c.billable && (
                        <span className="text-[11.5px] px-1.5 py-0.5 rounded mt-1 inline-block"
                          style={{ background: "var(--accent-soft)", color: "var(--accent-2)" }}>
                          واسطه
                        </span>
                      )}
                    </td>

                    {/* وضعیت */}
                    <td className="px-3 py-3">
                      <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-[13px]"
                        style={{ background: `color-mix(in srgb, ${col} 12%, transparent)`, color: col }}>
                        <Circle size={6} fill={col} strokeWidth={0} /> {c.status}
                      </span>
                    </td>

                    {/* ایجاد */}
                    <td className="px-3 py-3 text-center text-[13px]" dir="ltr"
                      style={{ color: "var(--dim)", fontFamily: "var(--mono)" }}>
                      {c.createdJalali || "—"}
                      {c.days && (
                        <div className="text-[12px] mt-0.5" style={{ color: "var(--muted)" }}>
                          {faNum(Math.round(c.days))} روز
                        </div>
                      )}
                    </td>

                    {/* انقضا */}
                    <td className="px-3 py-3 text-center text-[13px]" dir="ltr"
                      style={{ color: "var(--dim)", fontFamily: "var(--mono)" }}>
                      {c.expiryJalali || "—"}
                    </td>

                    {/* مانده */}
                    <td className="px-3 py-3 text-center">
                      {c.remainingDays === null ? (
                        <span style={{ color: "var(--muted)" }}>—</span>
                      ) : (
                        <div>
                          <div className="text-[16px] font-bold"
                            style={{
                              color: c.remainingDays < 0 ? "var(--danger)"
                                   : c.remainingDays <= 3 ? "var(--warn)" : "var(--text)",
                              fontFamily: "var(--mono)",
                            }}>
                            {faNum(Math.abs(Math.round(c.remainingDays)))}
                          </div>
                          <div className="text-[11.5px]" style={{ color: "var(--muted)" }}>
                            {c.remainingDays < 0 ? "روز گذشته" : "روز"}
                          </div>
                        </div>
                      )}
                    </td>

                    {/* ماه */}
                    <td className="px-3 py-3 text-center">
                      <div className="text-[16px] font-bold" style={{ color: "var(--text)",
                           fontFamily: "var(--mono)" }}>
                        {faNum(c.months)}
                      </div>
                    </td>

                    {/* تمدید */}
                    <td className="px-3 py-3 text-center">
                      {c.renewals ? (
                        <div>
                          <span className="px-2.5 py-1 rounded-lg text-[14px] font-bold inline-block"
                            style={{ background: "rgba(43,127,214,.18)", color: "var(--accent-2)",
                                     fontFamily: "var(--mono)" }}>
                            {faNum(c.renewals)}
                          </span>
                          {c.renewalKind === "تخمینی" && (
                            <div className="text-[11px] mt-1" style={{ color: "var(--warn)" }}>
                              تخمینی
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-[13px]" style={{ color: "var(--muted)" }}>بدون</span>
                      )}
                    </td>

                    {/* مصرف */}
                    <td className="px-3 py-3">
                      <div className="flex items-baseline gap-1.5 justify-center mb-1.5">
                        <span className="text-[14px] font-semibold"
                          style={{ color: "var(--text)", fontFamily: "var(--mono)" }}>
                          {faNum(c.usedGB)}
                        </span>
                        <span className="text-[12px]" style={{ color: "var(--muted)" }}>
                          / {c.gb === 0 ? "∞" : faNum(c.gb)} GB
                        </span>
                      </div>
                      <div style={{ height: 5, borderRadius: 99,
                                    background: "rgba(255,255,255,.06)", overflow: "hidden" }}>
                        <div style={{
                          width: c.usagePct === null ? "100%" : `${Math.min(100, c.usagePct)}%`,
                          height: "100%",
                          background: c.usagePct === null
                            ? "linear-gradient(90deg,#A78BFA33,#A78BFA66)" : pctColor,
                          transition: "width .4s ease",
                        }} />
                      </div>
                      <div className="text-[12px] mt-1 text-center" style={{ color: pctColor }}>
                        {c.usagePct === null ? "نامحدود" : `${faNum(c.usagePct)}٪`}
                      </div>
                    </td>

                    {/* مبلغ */}
                    <td className="px-3 py-3 text-center">
                      {c.amount ? (
                        <div>
                          <div className="text-[14px] font-bold" style={{ color: "var(--text)",
                               fontFamily: "var(--mono)" }}>
                            {faNum(c.amount)}
                          </div>
                          {c.months > 1 && c.price && (
                            <div className="text-[11.5px] mt-0.5" style={{ color: "var(--muted)" }}>
                              {faNum(c.months)}×{faNum(Math.round(c.price / 1000))}k
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-[13px]" style={{ color: "var(--muted)" }}>—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {data.clients.length === 0 && (
          <div className="py-16 text-center">
            <Users size={26} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
            <div className="text-[14px]" style={{ color: "var(--muted)" }}>
              کاربری با این فیلترها پیدا نشد
            </div>
          </div>
        )}
      </div>

      {/* صفحه‌بندی */}
      {pages > 1 && (
        <div className="flex items-center justify-between mt-4 flex-wrap gap-3">
          <span className="text-[13px]" style={{ color: "var(--muted)" }}>
            {faNum(page * PER + 1)} تا {faNum(Math.min((page + 1) * PER, data.total))} از {faNum(data.total)}
          </span>
          <div className="flex gap-2 items-center">
            <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
              className="fx-btn-g px-3 py-2 text-[13px]"
              style={page === 0 ? { opacity: .35, cursor: "not-allowed" } : {}}>قبلی</button>
            <span className="px-3 text-[13px]" style={{ color: "var(--dim)",
              fontFamily: "var(--mono)" }}>
              {faNum(page + 1)} / {faNum(pages)}
            </span>
            <button onClick={() => setPage(Math.min(pages - 1, page + 1))} disabled={page >= pages - 1}
              className="fx-btn-g px-3 py-2 text-[13px]"
              style={page >= pages - 1 ? { opacity: .35, cursor: "not-allowed" } : {}}>بعدی</button>
          </div>
        </div>
      )}

      {detail && <ClientDetailModal client={detail} onClose={() => setDetail(null)} />}
    </div>
  );
}

/** جزئیات کامل یک کاربر */
function ClientDetailModal({ client: c, onClose }) {
  const col = CLIENT_STATUS_COLOR[c.status] || "var(--muted)";

  const Row = ({ label, value, mono, color }) => (
    <div className="flex justify-between items-start gap-3 py-2"
      style={{ borderBottom: "1px solid var(--border)" }}>
      <span className="text-[13px] shrink-0" style={{ color: "var(--muted)" }}>{label}</span>
      <span className="text-[13px] text-left" dir={mono ? "ltr" : "rtl"}
        style={{ color: color || "var(--dim)",
                 fontFamily: mono ? "var(--mono)" : "inherit" }}>
        {value}
      </span>
    </div>
  );

  return (
    <Modal title={c.email} onClose={onClose} width="480px">
      <div className="flex items-center gap-2 mb-4">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[13px]"
          style={{ background: `color-mix(in srgb, ${col} 14%, transparent)`, color: col }}>
          <Circle size={6} fill={col} strokeWidth={0} /> {c.status}
        </span>
        <span className="text-[13px] px-2.5 py-1 rounded-lg"
          style={{ background: "var(--surface-3)", color: "var(--dim)" }}>
          {c.groupLabel}
        </span>
      </div>

      <Row label="حجم پلن" value={c.gbLabel} />
      <Row label="مصرف" value={`${faNum(c.usedGB)} GB${c.usagePct !== null ? ` (${faNum(c.usagePct)}٪)` : ""}`} mono />
      <Row label="تاریخ ایجاد" value={c.createdJalali || "—"} mono />
      <Row label="تاریخ انقضا" value={c.expiryJalali || "—"} mono />
      <Row label="روز مانده"
        value={c.remainingDays === null ? "—" : faNum(Math.round(c.remainingDays))} mono
        color={c.remainingDays !== null && c.remainingDays < 0 ? "var(--danger)" : undefined} />
      <Row label="مدت اشتراک" value={c.days ? `${faNum(c.days)} روز` : "—"} mono />
      <Row label="تعداد ماه" value={faNum(c.months)} mono color="var(--text)" />
      <Row label="تعداد تمدید" value={c.renewals ? faNum(c.renewals) : "بدون تمدید"} mono
        color={c.renewals ? "var(--accent-2)" : undefined} />
      <Row label="نوع تشخیص"
        value={c.renewalKind + (c.drift ? ` (انحراف ${faNum(c.drift)} روز)` : "")}
        color={c.renewalKind === "تخمینی" ? "var(--warn)" : "var(--ok)"} />
      {c.loggedRenewals > 0 && (
        <Row label="تمدید ثبت‌شده در نکسورا" value={faNum(c.loggedRenewals)} mono color="var(--ok)" />
      )}
      <Row label="دستگاه همزمان" value={c.limitIp ? faNum(c.limitIp) : "نامحدود"} mono />
      {c.resetCount > 0 && <Row label="ریست ترافیک" value={faNum(c.resetCount)} mono />}
      {c.tgId > 0 && <Row label="آیدی تلگرام" value={c.tgId} mono />}
      {c.subId && <Row label="شناسه اشتراک" value={c.subId} mono />}
      {c.comment && <Row label="یادداشت" value={c.comment} />}

      {c.billable && (
        <div className="mt-4 p-3.5 rounded-xl"
          style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
          <div className="flex justify-between text-[13px]">
            <span style={{ color: "var(--muted)" }}>نرخ ماهانه</span>
            <span style={{ color: "var(--dim)", fontFamily: "var(--mono)" }}>
              {c.price ? faNum(c.price) : "تعریف نشده"}
            </span>
          </div>
          <div className="flex justify-between text-[14px] font-bold mt-2 pt-2"
            style={{ borderTop: "1px solid var(--border)" }}>
            <span className="text-white">مبلغ کل</span>
            <span style={{ color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
              {faNum(c.amount)} تومان
            </span>
          </div>
        </div>
      )}
    </Modal>
  );
}

/* ── تنظیمات و بک‌آپ حسابداری ── */

function BillingSettings({ password }) {
  const [info, setInfo] = useState(null);
  const [cfg, setCfg] = useState(null);
  const [path, setPath] = useState("");
  const [busy, setBusy] = useState(null);
  const [msg, setMsg] = useState(null);
  const fileRef = React.useRef(null);

  const load = async () => {
    try {
      const [i, c2] = await Promise.all([
        fetch(`${API_URL}/api/admin/billing/xui-path`, { headers: { "X-Admin-Password": password } }).then(r => r.json()),
        fetch(`${API_URL}/api/admin/config`, { headers: { "X-Admin-Password": password } }).then(r => r.json()),
      ]);
      setInfo(i);
      setCfg(c2);
      setPath((c2.advanced?.xuiDbPath) || "");
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
  };
  useEffect(() => { load(); }, [password]);
  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 4500); return () => clearTimeout(t); } }, [msg]);

  const savePath = async (p) => {
    setBusy("path");
    try {
      const next = { ...cfg, advanced: { ...(cfg.advanced || {}), xuiDbPath: p } };
      const res = await fetch(`${API_URL}/api/admin/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify(next),
      });
      if (res.ok) { setMsg({ t: "ok", m: "مسیر ذخیره شد" }); load(); }
      else setMsg({ t: "err", m: "ذخیره ناموفق" });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(null); }
  };

  const backup = async () => {
    setBusy("backup");
    try {
      const d = await fetch(`${API_URL}/api/admin/billing/backup`, {
        headers: { "X-Admin-Password": password },
      }).then(r => r.json());
      const blob = new Blob([JSON.stringify(d, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `nexora-billing-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
      setMsg({ t: "ok", m: `دانلود شد — ${d.counts?.payments || 0} پرداخت، ${d.counts?.group_config || 0} گروه` });
    } catch { setMsg({ t: "err", m: "بک‌آپ ناموفق" }); }
    finally { setBusy(null); }
  };

  const restore = async (file) => {
    setBusy("restore");
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      const res = await fetch(`${API_URL}/api/admin/billing/restore`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ data: parsed.data || parsed }),
      });
      const d = await res.json();
      if (res.ok) setMsg({ t: "ok", m: `بازیابی شد — ${d.restored?.payments || 0} پرداخت` });
      else setMsg({ t: "err", m: d.detail || "بازیابی ناموفق" });
    } catch { setMsg({ t: "err", m: "فایل معتبر نبود" }); }
    finally { setBusy(null); if (fileRef.current) fileRef.current.value = ""; }
  };

  if (!info) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  return (
    <div className="fx-anim">
      <SectionHead title="تنظیمات و بک‌آپ"
        desc="مسیر دیتابیس ۳x-ui و پشتیبان‌گیری از نرخ‌ها و پرداخت‌ها." />

      {msg && <Msg msg={msg} />}

      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2">
          <Database size={15} style={{ color: "var(--accent-2)" }} /> مسیر دیتابیس ۳x-ui
        </div>
        <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
          حسابداری گروه‌ها و مصرف را از این فایل می‌خواند — فقط‌خواندنی، بدون هیچ تغییری در آن.
        </p>

        <div className="rounded-xl p-3 mb-4 flex items-start gap-2.5"
          style={{
            background: info.readable ? "rgba(52,211,153,.08)" : "rgba(251,191,36,.08)",
            border: `1px solid ${info.readable ? "rgba(52,211,153,.25)" : "rgba(251,191,36,.25)"}`,
          }}>
          {info.readable
            ? <CheckCircle2 size={15} style={{ color: "var(--ok)", flexShrink: 0, marginTop: 1 }} />
            : <AlertTriangle size={15} style={{ color: "var(--warn)", flexShrink: 0, marginTop: 1 }} />}
          <div className="min-w-0">
            <div className="text-[13px] font-semibold" style={{ color: info.readable ? "var(--ok)" : "var(--warn)" }}>
              {info.readable ? "خوانده می‌شود" : info.exists ? "پیدا شد ولی دسترسی خواندن نیست" : "پیدا نشد"}
            </div>
            <div className="text-[12px] mt-1 break-all" dir="ltr"
              style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
              {info.current}
            </div>
            {info.exists && !info.readable && (
              <div className="text-[12px] mt-2" style={{ color: "var(--warn)" }}>
                روی سرور اجرا کنید: <code dir="ltr" className="px-1.5 py-0.5 rounded"
                  style={{ background: "var(--surface-3)" }}>chmod +r {info.current}</code>
              </div>
            )}
          </div>
        </div>

        {info.found?.length > 0 && (
          <div className="mb-4">
            <div className="text-[13px] mb-2" style={{ color: "var(--muted)" }}>
              مسیرهای پیداشده روی این سرور:
            </div>
            {info.found.map((f) => (
              <button key={f.path} onClick={() => { setPath(f.path); savePath(f.path); }}
                className="w-full flex items-center justify-between gap-2 p-2.5 rounded-xl mb-1.5 text-right"
                style={{
                  background: f.path === info.current ? "var(--accent-soft)" : "var(--surface-3)",
                  border: `1px solid ${f.path === info.current ? "rgba(43,127,214,.4)" : "var(--border)"}`,
                }}>
                <span className="text-[13px] truncate" dir="ltr"
                  style={{ color: "var(--dim)", fontFamily: "var(--mono)" }}>{f.path}</span>
                <span className="text-[11.5px] shrink-0" style={{ color: "var(--muted)" }}>
                  {(f.size / 1024 / 1024).toFixed(1)} MB
                </span>
              </button>
            ))}
          </div>
        )}

        <Field label="مسیر دستی" hint="اگر ۳x-ui جای دیگری نصب است">
          <div className="flex gap-2">
            <input className="fx-input" dir="ltr" value={path}
              onChange={(e) => setPath(e.target.value)}
              placeholder="/etc/x-ui/x-ui.db"
              style={{ fontFamily: "var(--mono)" }} />
            <button onClick={() => savePath(path)} disabled={busy === "path"}
              className="fx-btn px-4 py-2.5 text-[13px] shrink-0 flex items-center gap-1.5">
              {busy === "path" ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
              ذخیره
            </button>
          </div>
        </Field>
      </div>

      <div className="fx-card p-5">
        <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2">
          <Database size={15} style={{ color: "var(--accent-2)" }} /> بک‌آپ حسابداری
        </div>
        <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
          نرخ‌ها، پرداخت‌ها و لاگ تمدید. داده‌ی ۳x-ui در بک‌آپ نیست — آن از خودش خوانده می‌شود.
        </p>

        <div className="fx-g3 grid grid-cols-2 gap-3">
          <button onClick={backup} disabled={busy === "backup"}
            className="fx-btn py-3 text-[14px] flex items-center justify-center gap-2">
            {busy === "backup" ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            دریافت بک‌آپ
          </button>
          <button onClick={() => fileRef.current?.click()} disabled={busy === "restore"}
            className="fx-btn-g py-3 text-[14px] flex items-center justify-center gap-2">
            {busy === "restore" ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
            بازیابی از فایل
          </button>
        </div>
        <input ref={fileRef} type="file" accept=".json" className="hidden"
          onChange={(e) => e.target.files?.[0] && restore(e.target.files[0])} />

        <InfoBox>
          قبل از بازیابی، یک نسخه‌ی امن از وضعیت فعلی گرفته می‌شود — اگر فایل اشتباه
          بود، داده‌ی فعلی از دست نرفته است.
        </InfoBox>
      </div>
    </div>
  );
}

/* ═══════════════════ حسابداری واسطه‌ها ═══════════════════ */

const faNum = (n) => Number(n || 0).toLocaleString("fa-IR");
const RATE_STEP = 10000;
const RATE_QUICK = [90000, 120000, 150000, 190000, 250000];

/**
 * ردیف نرخ — حجم آزاد و قیمت با سه راه ورود.
 *
 * فیلدها فرورفته‌اند (پس‌زمینه‌ی تیره‌تر از کارت) تا با زبان بصری
 * بقیه‌ی پنل بخوانند و لکه‌ی روشن ایجاد نکنند.
 */
function RateRow({ rate, onChange, onDelete }) {
  const unlimited = !rate.gb;
  const bump = (d) => onChange({ price: Math.max(0, (rate.price || 0) + d) });

  return (
    <div className="rounded-2xl p-3 mb-2.5"
      style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>

      <div className="flex items-end gap-2.5 mb-3">
        <div className="flex-1">
          <label className="text-[12px] block mb-1.5" style={{ color: "var(--muted)" }}>
            حجم ماهانه
          </label>
          <div className="flex gap-2">
            <button onClick={() => onChange({ gb: 0 })}
              className="px-3.5 py-2.5 rounded-[10px] text-[13px] font-semibold shrink-0"
              style={{
                background: unlimited ? "rgba(167,139,250,.14)" : "transparent",
                border: `1px solid ${unlimited ? "rgba(167,139,250,.4)" : "var(--border-2)"}`,
                color: unlimited ? "#A78BFA" : "var(--muted)",
              }}>
              نامحدود
            </button>

            <div className="flex-1 flex items-center gap-2 px-3 rounded-[10px]"
              style={{
                background: unlimited ? "transparent" : "rgba(0,0,0,.28)",
                border: "1px solid var(--border)",
                boxShadow: unlimited ? "none" : "0 2px 8px rgba(0,0,0,.35) inset",
                opacity: unlimited ? 0.42 : 1,
              }}>
              <input type="number" min="1" dir="ltr"
                value={unlimited ? "" : rate.gb}
                onFocus={() => unlimited && onChange({ gb: 30 })}
                onChange={(e) => onChange({ gb: Math.max(0, Number(e.target.value)) })}
                placeholder="مثلاً ۵۰"
                className="flex-1 bg-transparent border-0 outline-none py-2.5 text-[14px]"
                style={{ color: "var(--text)", fontFamily: "var(--mono)" }} />
              <span className="text-[12px] shrink-0" style={{ color: "var(--muted)" }}>گیگابایت</span>
            </div>
          </div>
        </div>

        <button onClick={onDelete} className="fx-ico-btn shrink-0" style={{ width: 36, height: 36 }}>
          <Trash2 size={13} />
        </button>
      </div>

      <div>
        <div className="flex justify-between items-center mb-2">
          <label className="text-[12px]" style={{ color: "var(--muted)" }}>قیمت ماهانه</label>
          <span className="text-[12px]" style={{ color: "var(--muted)" }}>
            {rate.price ? `${faNum(rate.price)} تومان` : "—"}
          </span>
        </div>

        <div className="flex items-center gap-0.5 rounded-xl p-1"
          style={{
            background: "rgba(0,0,0,.28)", border: "1px solid var(--border)",
            boxShadow: "0 2px 8px rgba(0,0,0,.35) inset",
          }}>
          <button onClick={() => bump(-RATE_STEP)} className="nx-step">−</button>
          <input type="number" dir="ltr" value={rate.price || ""}
            onChange={(e) => onChange({ price: Math.max(0, Number(e.target.value)) })}
            placeholder="0"
            className="flex-1 bg-transparent border-0 outline-none text-center py-2 text-[16px] font-bold"
            style={{ color: "var(--text)", fontFamily: "var(--mono)" }} />
          <button onClick={() => bump(RATE_STEP)} className="nx-step">+</button>
        </div>

        <div className="flex gap-1.5 mt-2.5 flex-wrap">
          {RATE_QUICK.map((q) => {
            const on = rate.price === q;
            return (
              <button key={q} onClick={() => onChange({ price: q })}
                className="px-2.5 py-1 rounded-lg text-[12px]"
                style={{
                  background: on ? "rgba(43,127,214,.14)" : "transparent",
                  border: `1px solid ${on ? "rgba(43,127,214,.4)" : "var(--border)"}`,
                  color: on ? "var(--accent-2)" : "var(--muted)",
                  fontFamily: "var(--mono)",
                }}>{faNum(q / 1000)}k</button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function useBilling(password) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/billing/groups`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setData(d);
    } catch {
      setData({ ready: false, error: "اتصال به سرور برقرار نشد", groups: [] });
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [password]);
  return { data, loading, reload: load };
}

function BillingUnavailable({ info, password }) {
  const [diag, setDiag] = useState(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    try {
      const d = await fetch(`${API_URL}/api/admin/billing/diagnose`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setDiag(d);
    } catch {
      setDiag({ ok: false, steps: [{ title: "اتصال به سرور برقرار نشد", ok: false }] });
    } finally { setBusy(false); }
  };

  if (diag) {
    return (
      <div className="fx-card p-5">
        <div className="text-[14px] font-semibold text-white mb-4 flex items-center gap-2">
          <ShieldCheck size={15} style={{ color: "var(--accent-2)" }} /> تشخیص اتصال
        </div>
        {diag.steps.map((s, i) => (
          <div key={i} className="flex gap-3 py-2.5"
            style={{ borderBottom: i < diag.steps.length - 1 ? "1px solid var(--border)" : "none" }}>
            <div className="shrink-0 mt-0.5">
              {s.ok ? <CheckCircle2 size={15} style={{ color: "var(--ok)" }} />
                    : <XCircle size={15} style={{ color: "var(--danger)" }} />}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[13px] font-semibold"
                style={{ color: s.ok ? "var(--text)" : "var(--danger)" }}>{s.title}</div>
              {s.detail && (
                <div className="text-[12px] mt-1 break-all" dir="auto"
                  style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                  {s.detail}
                </div>
              )}
              {s.hint && (
                <div className="text-[13px] mt-2 px-2.5 py-1.5 rounded-lg break-all" dir="auto"
                  style={{ color: "var(--warn)", background: "rgba(251,191,36,.08)" }}>
                  {s.hint}
                </div>
              )}
            </div>
          </div>
        ))}
        <button onClick={() => setDiag(null)}
          className="fx-btn-g w-full py-2.5 text-[13px] mt-4">بازگشت</button>
      </div>
    );
  }

  return (
    <div className="fx-card p-8 text-center" style={{ borderStyle: "dashed" }}>
      <AlertTriangle size={24} style={{ color: "var(--warn)" }} className="mx-auto mb-3" />
      <div className="text-[14px] font-semibold text-white mb-2">
        دیتابیس ۳x-ui خوانده نشد
      </div>
      <p className="text-[13px] mb-4 max-w-sm mx-auto leading-relaxed" style={{ color: "var(--muted)" }}>
        {info?.error || "مسیر دیتابیس در دسترس نیست."}
      </p>
      {(info?.xuiPath || info?.dbPath) && (
        <code dir="ltr" className="text-[12px] px-3 py-1.5 rounded-lg inline-block"
          style={{ background: "var(--surface-3)", color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
          {info.xuiPath || info.dbPath}
        </code>
      )}
      <div className="mt-5 pt-4 max-w-sm mx-auto" style={{ borderTop: "1px solid var(--border)" }}>
        <p className="text-[13px] leading-relaxed mb-3" style={{ color: "var(--muted)" }}>
          روی سرور این را اجرا کنید تا مسیر خودکار پیدا و تنظیم شود:
        </p>
        <code dir="ltr" className="text-[13px] px-3 py-2 rounded-lg inline-block"
          style={{ background: "var(--surface-3)", color: "var(--ok)", fontFamily: "var(--mono)" }}>
          nexora fix-xui
        </code>
        <p className="text-[12px] leading-relaxed mt-3" style={{ color: "var(--muted)" }}>
          یا مسیر را دستی در بخش «تنظیمات و بک‌آپ» وارد کنید.
        </p>
        <button onClick={run} disabled={busy}
          className="fx-btn w-full py-2.5 text-[13px] mt-4 flex items-center justify-center gap-2">
          {busy ? <Loader2 size={14} className="animate-spin" /> : <ShieldCheck size={14} />}
          تشخیص دقیق مشکل
        </button>
      </div>
    </div>
  );
}

function BillingDash({ password }) {
  const { data, loading, reload } = useBilling(password);
  if (loading) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;
  if (!data?.ready) return (
    <div className="fx-anim">
      <SectionHead title="داشبورد حسابداری" desc="" />
      <BillingUnavailable info={data} password={password} />
    </div>
  );

  const billed = data.groups.filter((g) => g.billed);
  const due = billed.reduce((s, g) => s + g.amount, 0);
  const paid = billed.reduce((s, g) => s + g.paid, 0);
  const uncertain = billed.reduce((s, g) => s + (g.uncertain || 0), 0);

  return (
    <div className="fx-anim">
      <SectionHead title="داشبورد حسابداری"
        desc={`${data.totalClients} کانفیگ در ${data.groups.length} گروه`}
        action={
          <button onClick={reload} className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
            <RefreshCw size={13} /> تازه‌سازی
          </button>
        } />

      <div className="grid gap-3 mb-6" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))" }}>
        {[["کل بدهی دوره", due, "var(--accent-2)"],
          ["دریافت‌شده", paid, "var(--ok)"],
          ["مانده", due - paid, due - paid > 0 ? "var(--warn)" : "var(--ok)"]].map(([l, v, col], i) => (
          <div key={i} className="fx-card p-4">
            <div className="fx-stat-num text-[21px] font-extrabold leading-none"
              style={{ color: col, fontFamily: "var(--mono)" }}>{faNum(v)}</div>
            <div className="text-[12px] mt-2" style={{ color: "var(--dim)" }}>{l} · تومان</div>
          </div>
        ))}
      </div>

      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-4">وضعیت هر واسطه</div>
        {billed.length === 0 ? (
          <div className="text-center py-8 text-[13px]" style={{ color: "var(--muted)" }}>
            هنوز گروهی به‌عنوان واسطه علامت نخورده — از بخش «واسطه‌ها و نرخ» شروع کنید
          </div>
        ) : billed.map((g, i) => {
          const rest = g.amount - g.paid;
          const pct = g.amount ? Math.min(100, Math.round(g.paid * 100 / g.amount)) : 0;
          return (
            <div key={g.name} className="py-3.5"
              style={{ borderBottom: i < billed.length - 1 ? "1px solid var(--border)" : "none" }}>
              <div className="flex justify-between items-start gap-3 mb-2.5 flex-wrap">
                <div>
                  <div className="text-[14px] font-semibold text-white">{g.label}</div>
                  <div className="text-[12px] mt-1" dir="ltr"
                    style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                    {g.name} · {g.configs} config · {g.months} months
                  </div>
                </div>
                <div className="text-left">
                  <div className="text-[14px] font-extrabold"
                    style={{ color: rest > 0 ? "var(--warn)" : "var(--ok)", fontFamily: "var(--mono)" }}>
                    {faNum(rest)}
                  </div>
                  <div className="text-[11.5px] mt-0.5" style={{ color: "var(--muted)" }}>
                    {rest > 0 ? "مانده" : "تسویه شده"}
                  </div>
                </div>
              </div>
              <div className="h-[5px] rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,.05)" }}>
                <div style={{
                  width: `${pct}%`, height: "100%", borderRadius: 99,
                  background: pct >= 100 ? "var(--ok)" : "linear-gradient(90deg,var(--accent),var(--accent-2))",
                  transition: "width .5s cubic-bezier(.22,1,.36,1)",
                }} />
              </div>
              {g.unpriced?.length > 0 && (
                <div className="text-[12px] mt-2" style={{ color: "var(--warn)" }}>
                  حجم بدون نرخ: {g.unpriced.map((v) => v ? `${faNum(v)}GB` : "نامحدود").join("، ")}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {uncertain > 0 && (
        <InfoBox tone="warn">
          <b>{faNum(uncertain)} کانفیگ تمدید تخمینی دارند.</b> پنل ۳x-ui تاریخچه‌ی تمدید
          ندارد، پس تعداد ماه از فاصله‌ی «ایجاد تا انقضا» حساب می‌شود. اگر تمدید زودتر از
          موعد انجام شده باشد، عدد کمتر از واقعیت درمی‌آید.
          <br /><br />
          از امروز هر تمدیدی که از ربات یا پنل انجام شود ثبت می‌شود و تخمین جای خودش را
          به عدد قطعی می‌دهد.
        </InfoBox>
      )}
    </div>
  );
}

function BillingGroups({ password }) {
  const { data, loading, reload } = useBilling(password);
  const [open, setOpen] = useState(null);
  const [draft, setDraft] = useState({});
  const [saving, setSaving] = useState(null);

  if (loading) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;
  if (!data?.ready) return (
    <div className="fx-anim">
      <SectionHead title="واسطه‌ها و نرخ" desc="" />
      <BillingUnavailable info={data} password={password} />
    </div>
  );

  const get = (g) => draft[g.name] || {
    label: g.label, billed: g.billed, rates: g.rates, perGb: g.perGb || 0,
    periodDays: g.periodDays || 30,
    periodStart: g.periodStart || "",
    settledUntil: g.settledUntil || "",
  };
  const set = (g, patch) => setDraft({ ...draft, [g.name]: { ...get(g), ...patch } });

  const save = async (g) => {
    setSaving(g.name);
    try {
      await fetch(`${API_URL}/api/admin/billing/group/${encodeURIComponent(g.name)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify(get(g)),
      });
      await reload();
      setDraft({ ...draft, [g.name]: undefined });
    } finally { setSaving(null); }
  };

  return (
    <div className="fx-anim">
      <SectionHead title="واسطه‌ها و نرخ"
        desc="گروه‌ها از ۳x-ui خوانده می‌شوند. برای هرکدام تعیین کنید واسطه است یا مشتری مستقیم." />

      {data.groups.map((g) => {
        const d = get(g);
        const isOpen = open === g.name;
        const dirty = !!draft[g.name];
        return (
          <div key={g.name} className="fx-card mb-3 overflow-hidden" style={{ padding: 0 }}>
            <div onClick={() => setOpen(isOpen ? null : g.name)}
              className="p-4 cursor-pointer flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-3">
                <div className="fx-ico" style={{ background: d.billed ? "rgba(43,127,214,.12)" : "rgba(255,255,255,.04)" }}>
                  <Users size={16} style={{ color: d.billed ? "var(--accent-2)" : "var(--muted)" }} />
                </div>
                <div>
                  <div className="text-[14px] font-semibold text-white">{d.label || g.name}</div>
                  <div className="text-[12px] mt-1" dir="ltr"
                    style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                    {g.name} · {g.configs} configs · {g.usedGB}GB used
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {d.billed && g.amount > 0 && (
                  <span className="text-[13px] font-bold"
                    style={{ color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
                    {faNum(g.amount)}
                  </span>
                )}
                <div onClick={(e) => { e.stopPropagation(); set(g, { billed: !d.billed }); }}>
                  <Toggle checked={d.billed} onChange={() => {}} />
                </div>
              </div>
            </div>

            {isOpen && (
              <div className="px-4 pb-4" style={{ borderTop: "1px solid var(--border)" }}>
                {!d.billed ? (
                  <div className="py-6 text-center text-[13px]" style={{ color: "var(--muted)" }}>
                    مشتری مستقیم شماست — در صورتحساب واسطه‌ها نمی‌آید.
                  </div>
                ) : (
                  <>
                    <div className="pt-4">
                      <Field label="نام نمایشی">
                        <input className="fx-input" value={d.label || ""}
                          onChange={(e) => set(g, { label: e.target.value })}
                          placeholder={g.name} />
                      </Field>
                    </div>

                    {/* دو مدل قیمت‌گذاری — یا ماهانه بر اساس پلن، یا حجمی */}
                    <div className="flex gap-2 mb-4">
                      {[["پلنی", false], ["حجمی", true]].map(([label, isGb]) => {
                        const on = !!d.perGb === isGb;
                        return (
                          <button key={label}
                            onClick={() => set(g, { perGb: isGb ? (d.perGb || 3000) : 0 })}
                            className="flex-1 py-2.5 rounded-xl text-[13px] transition-all"
                            style={{
                              background: on ? "var(--accent-soft)" : "var(--surface-3)",
                              border: `1px solid ${on ? "rgba(43,127,214,.4)" : "var(--border)"}`,
                              color: on ? "var(--accent-2)" : "var(--muted)",
                            }}>
                            {label}
                          </button>
                        );
                      })}
                    </div>

                    {d.perGb ? (
                      <div className="mb-3">
                        <Field label="نرخ هر گیگابایت (تومان)"
                          hint="بر اساس مصرف واقعی حساب می‌شود، نه سقف پلن">
                          <div className="flex items-center gap-2">
                            <input className="fx-input" type="number" dir="ltr"
                              value={d.perGb || ""}
                              onChange={(e) => set(g, { perGb: Math.max(0, +e.target.value) })}
                              placeholder="3000"
                              style={{ fontFamily: "var(--mono)" }} />
                            <div className="flex gap-1.5 shrink-0">
                              {[2000, 3000, 5000].map((q) => (
                                <button key={q} onClick={() => set(g, { perGb: q })}
                                  className="px-2.5 py-2 rounded-lg text-[12px]"
                                  style={{
                                    background: d.perGb === q ? "var(--accent-soft)" : "transparent",
                                    border: `1px solid ${d.perGb === q ? "rgba(43,127,214,.4)" : "var(--border)"}`,
                                    color: d.perGb === q ? "var(--accent-2)" : "var(--muted)",
                                    fontFamily: "var(--mono)",
                                  }}>{faNum(q / 1000)}k</button>
                              ))}
                            </div>
                          </div>
                        </Field>
                        {g.usedGB > 0 && (
                          <div className="text-[13px] p-2.5 rounded-lg"
                            style={{ background: "var(--surface-3)", color: "var(--dim)" }}>
                            {faNum(g.usedGB)} GB × {faNum(d.perGb)} = {" "}
                            <b style={{ color: "var(--accent-2)" }}>
                              {faNum(Math.round(g.usedGB * d.perGb))} تومان
                            </b>
                          </div>
                        )}
                      </div>
                    ) : (
                    <>
                    <div className="flex justify-between items-center mb-3 mt-1 flex-wrap gap-2">
                      <span className="text-[13px]" style={{ color: "var(--dim)" }}>نرخ ماهانه بر اساس حجم</span>
                      <button onClick={() => set(g, { rates: [...(d.rates || []), { gb: 0, price: 190000 }] })}
                        className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
                        <PlusIcon size={12} /> افزودن نرخ
                      </button>
                    </div>

                    {(d.rates || []).length === 0 && (
                      <div className="rounded-xl p-4 text-center mb-3"
                        style={{ background: "rgba(251,191,36,.06)", border: "1px dashed rgba(251,191,36,.3)" }}>
                        <div className="text-[13px] mb-1" style={{ color: "var(--warn)" }}>هنوز نرخی تعریف نشده</div>
                        <div className="text-[12px]" style={{ color: "var(--muted)" }}>
                          بدون نرخ، این گروه صفر حساب می‌شود
                        </div>
                      </div>
                    )}

                    {(d.rates || []).map((r, i) => (
                      <RateRow key={i} rate={r}
                        onChange={(patch) => {
                          const l = [...d.rates]; l[i] = { ...l[i], ...patch };
                          set(g, { rates: l });
                        }}
                        onDelete={() => set(g, { rates: d.rates.filter((_, x) => x !== i) })} />
                    ))}

                    </>
                    )}

                    {/* دوره‌ی پرداخت — بدون این، معلوم نیست بابت چه بازه‌ای
                        پول می‌گیرید و پرداخت‌ها با هم قاطی می‌شوند */}
                    <div className="mt-4 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
                      <div className="text-[13px] mb-3" style={{ color: "var(--dim)" }}>
                        دوره‌ی پرداخت
                      </div>

                      <div className="flex gap-2 mb-3">
                        {[["هفتگی", 7], ["دوهفته", 14], ["ماهانه", 30]].map(([l, n]) => {
                          const on = (d.periodDays || 30) === n;
                          return (
                            <button key={n} onClick={() => set(g, { periodDays: n })}
                              className="flex-1 py-2 rounded-xl text-[13px]"
                              style={{
                                background: on ? "var(--accent-soft)" : "var(--surface-3)",
                                border: `1px solid ${on ? "rgba(43,127,214,.4)" : "var(--border)"}`,
                                color: on ? "var(--accent-2)" : "var(--muted)",
                              }}>{l}</button>
                          );
                        })}
                      </div>

                      <div className="fx-g3 grid grid-cols-2 gap-3">
                        <Field label="شروع دوره‌ها" hint="مبنای شمارش">
                          <input className="fx-input" dir="ltr" value={d.periodStart || ""}
                            onChange={(e) => set(g, { periodStart: e.target.value })}
                            placeholder="2026-08-01"
                            style={{ fontFamily: "var(--mono)" }} />
                        </Field>
                        <Field label="تسویه‌شده تا" hint="قبل از این تاریخ حساب نمی‌شود">
                          <input className="fx-input" dir="ltr" value={d.settledUntil || ""}
                            onChange={(e) => set(g, { settledUntil: e.target.value })}
                            placeholder="2026-08-01"
                            style={{ fontFamily: "var(--mono)" }} />
                        </Field>
                      </div>
                    </div>

                    <div className="grid gap-2 mt-3 pt-3" style={{
                      gridTemplateColumns: "repeat(auto-fit,minmax(100px,1fr))",
                      borderTop: "1px solid var(--border)",
                    }}>
                      {[["کانفیگ", g.configs], ["فعال", g.active],
                        ["ماه", g.months], ["تمدید", g.renewals]].map(([k, v], i) => (
                        <div key={i} className="text-center">
                          <div className="text-[16px] font-bold text-white" style={{ fontFamily: "var(--mono)" }}>
                            {faNum(v)}
                          </div>
                          <div className="text-[11.5px] mt-1" style={{ color: "var(--muted)" }}>{k}</div>
                        </div>
                      ))}
                    </div>
                  </>
                )}

                {dirty && (
                  <button onClick={() => save(g)} disabled={saving === g.name}
                    className="fx-btn w-full mt-4 py-2.5 text-[14px] flex items-center justify-center gap-2">
                    {saving === g.name ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                    ذخیره
                  </button>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function BillingInvoice({ password }) {
  const { data, loading } = useBilling(password);
  const [sel, setSel] = useState("");
  const [inv, setInv] = useState(null);
  const [busy, setBusy] = useState(false);

  const billed = data?.groups?.filter((g) => g.billed) || [];

  /**
   * دانلود صورتحساب PDF.
   *
   * چون endpoint هدر رمز می‌خواهد، نمی‌شود مستقیم لینک داد —
   * باید fetch کنیم و blob را دانلود کنیم.
   */
  const downloadPdf = async () => {
    if (!sel) return;
    setBusy(true);
    try {
      const res = await fetch(
        `${API_URL}/api/admin/billing/invoice/${encodeURIComponent(sel)}/pdf`,
        { headers: { "X-Admin-Password": password } });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        alert(d.detail || "ساخت PDF ناموفق بود");
        return;
      }
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `nexora-${sel}-${new Date().toISOString().slice(0, 10)}.pdf`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch {
      alert("اتصال به سرور برقرار نشد");
    } finally { setBusy(false); }
  };
  useEffect(() => { if (!sel && billed.length) setSel(billed[0].name); }, [data]);

  const gen = async () => {
    if (!sel) return;
    setBusy(true);
    try {
      const d = await fetch(`${API_URL}/api/admin/billing/invoice/${encodeURIComponent(sel)}`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setInv(d);
    } finally { setBusy(false); }
  };

  if (loading) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;
  if (!data?.ready) return (
    <div className="fx-anim"><SectionHead title="صورتحساب" desc="" /><BillingUnavailable info={data} password={password} /></div>
  );

  return (
    <div className="fx-anim">
      <SectionHead title="صورتحساب" desc="جزئیات کامل هر واسطه، آماده برای ارسال." />

      {billed.length === 0 ? (
        <div className="fx-card p-8 text-center" style={{ borderStyle: "dashed" }}>
          <FileText size={24} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
          <div className="text-[14px]" style={{ color: "var(--muted)" }}>
            ابتدا حداقل یک گروه را واسطه علامت بزنید
          </div>
        </div>
      ) : (
        <>
          <div className="fx-card p-5 mb-4">
            <Field label="واسطه">
              <select className="fx-input" value={sel} onChange={(e) => { setSel(e.target.value); setInv(null); }}>
                {billed.map((g) => <option key={g.name} value={g.name}>{g.label}</option>)}
              </select>
            </Field>
            <div className="fx-g3 grid grid-cols-2 gap-3">
              <button onClick={gen} disabled={busy}
                className="fx-btn py-2.5 text-[14px] flex items-center justify-center gap-2">
                {busy ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />}
                نمایش صورتحساب
              </button>
              <button onClick={downloadPdf} disabled={busy || !sel}
                className="fx-btn-g py-2.5 text-[14px] flex items-center justify-center gap-2">
                <Download size={14} /> دانلود PDF
              </button>
            </div>
          </div>

          {inv && (
            <div className="fx-card p-5">
              <div className="text-[14px] font-semibold text-white mb-4">{inv.label}</div>

              {inv.unpricedVolumes?.length > 0 && (
                <InfoBox tone="warn">
                  حجم‌های بدون نرخ کنار گذاشته شدند:{" "}
                  {inv.unpricedVolumes.map((v) => v ? `${faNum(v)}GB` : "نامحدود").join("، ")}
                </InfoBox>
              )}

              <div className="rounded-xl p-4 mb-4" style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
                {[["کل مبلغ", inv.totalAmount, "var(--text)"],
                  ["پرداخت‌شده", inv.paid, "var(--ok)"],
                  ["مانده", inv.balance, inv.balance > 0 ? "var(--warn)" : "var(--ok)"]].map(([k, v, col], i) => (
                  <div key={i} className="flex justify-between py-1.5">
                    <span className="text-[13px]" style={{ color: i === 2 ? "var(--text)" : "var(--muted)" }}>{k}</span>
                    <span className="font-bold" style={{
                      color: col, fontSize: i === 2 ? 14 : 12,
                      fontFamily: "var(--mono)",
                    }}>{faNum(v)}</span>
                  </div>
                ))}
              </div>

              <div className="text-[13px] mb-2" style={{ color: "var(--dim)" }}>
                {faNum(inv.items.length)} کانفیگ
              </div>
              <div style={{ maxHeight: 320, overflowY: "auto" }}>
                {inv.items.map((it, i) => (
                  <div key={i} className="flex justify-between items-center py-2.5 gap-3"
                    style={{ borderBottom: i < inv.items.length - 1 ? "1px solid var(--border)" : "none" }}>
                    <div className="min-w-0">
                      <div className="text-[13px] truncate" dir="ltr"
                        style={{ color: "var(--text)", fontFamily: "var(--mono)" }}>
                        {it.email}
                      </div>
                      <div className="text-[11.5px] mt-1" style={{ color: "var(--muted)" }}>
                        {it.gb ? `${faNum(it.gb)}GB` : "نامحدود"} · {faNum(it.months)} ماه
                        {it.renewals > 0 && ` · ${faNum(it.renewals)} تمدید`}
                        {!it.certain && it.drift != null && ` · ±${it.drift} روز`}
                      </div>
                    </div>
                    <span className="text-[13px] font-semibold shrink-0"
                      style={{
                        color: it.lineTotal == null ? "var(--warn)" : "var(--dim)",
                        fontFamily: "var(--mono)",
                      }}>
                      {it.lineTotal == null ? "بدون نرخ" : faNum(it.lineTotal)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function BillingPayments({ password }) {
  const { data } = useBilling(password);
  const [list, setList] = useState([]);
  const [add, setAdd] = useState(false);
  const [form, setForm] = useState({ group: "", amount: "", date: "", note: "" });
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/billing/payments`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setList(d.payments || []);
    } catch { /* بی‌صدا */ }
  };
  useEffect(() => { load(); }, [password]);

  const billed = data?.groups?.filter((g) => g.billed) || [];

  const submit = async () => {
    if (!form.group || !form.amount) return;
    setBusy(true);
    try {
      await fetch(`${API_URL}/api/admin/billing/payment`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ ...form, amount: Number(form.amount) }),
      });
      setAdd(false);
      setForm({ group: "", amount: "", date: "", note: "" });
      load();
    } finally { setBusy(false); }
  };

  const del = async (id) => {
    await fetch(`${API_URL}/api/admin/billing/payment/${id}`, {
      method: "DELETE", headers: { "X-Admin-Password": password },
    });
    load();
  };

  return (
    <div className="fx-anim">
      <SectionHead title="پرداخت‌ها"
        desc="پرداخت‌های واسطه در ۳x-ui ثبت نمی‌شوند — هر دریافتی را اینجا بزنید تا مانده درست حساب شود."
        action={
          <button onClick={() => setAdd(true)} className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
            <PlusIcon size={14} /> ثبت پرداخت
          </button>
        } />

      {list.length === 0 ? (
        <div className="fx-card p-8 text-center" style={{ borderStyle: "dashed" }}>
          <Wallet size={24} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
          <div className="text-[14px]" style={{ color: "var(--muted)" }}>هنوز پرداختی ثبت نشده</div>
        </div>
      ) : (
        <div className="fx-card overflow-hidden" style={{ padding: 0 }}>
          {list.map((p, i) => {
            const g = data?.groups?.find((x) => x.name === p.group_name);
            return (
              <div key={p.id} className="p-4 flex justify-between items-center gap-3 flex-wrap"
                style={{ borderBottom: i < list.length - 1 ? "1px solid var(--border)" : "none" }}>
                <div>
                  <div className="text-[14px] font-semibold text-white">{g?.label || p.group_name}</div>
                  <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
                    {p.paid_at || p.created_at?.slice(0, 10)}{p.note && ` · ${p.note}`}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[14px] font-bold" style={{ color: "var(--ok)", fontFamily: "var(--mono)" }}>
                    +{faNum(p.amount)}
                  </span>
                  <button onClick={() => del(p.id)} className="fx-ico-btn" style={{ width: 28, height: 28 }}>
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {add && createPortal(
        <div className="nx-modal-wrap fx-fade" onClick={() => setAdd(false)}>
          <div className="fx-card fx-scale p-5" style={{ width: "min(400px,92vw)" }}
            onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <span className="text-[16px] font-bold text-white">ثبت پرداخت</span>
              <button onClick={() => setAdd(false)} className="fx-ico-btn" style={{ width: 28, height: 28 }}>
                <X size={14} />
              </button>
            </div>
            <Field label="واسطه">
              <select className="fx-input" value={form.group}
                onChange={(e) => setForm({ ...form, group: e.target.value })}>
                <option value="">انتخاب کنید</option>
                {billed.map((g) => <option key={g.name} value={g.name}>{g.label}</option>)}
              </select>
            </Field>
            <Field label="مبلغ (تومان)">
              <input className="fx-input" dir="ltr" type="number" value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
                style={{ fontFamily: "var(--mono)" }} />
            </Field>
            <Field label="تاریخ" hint="اختیاری">
              <input className="fx-input" value={form.date}
                onChange={(e) => setForm({ ...form, date: e.target.value })}
                placeholder="۱۴۰۵/۰۶/۲۵" />
            </Field>
            <Field label="توضیح" hint="اختیاری">
              <input className="fx-input" value={form.note}
                onChange={(e) => setForm({ ...form, note: e.target.value })} />
            </Field>
            <button onClick={submit} disabled={busy || !form.group || !form.amount}
              className="fx-btn w-full py-2.5 text-[14px] flex items-center justify-center gap-2 mt-2">
              {busy ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
              ثبت
            </button>
          </div>
        </div>, document.body)}
    </div>
  );
}


/* ===================== اتصال گیت‌هاب ===================== */

function GithubCard({ password }) {
  const [repo, setRepo] = useState("");
  const [saved, setSaved] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/github`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setRepo(d.repo || "");
      setSaved(d.repo || "");
    } catch { /* بی‌صدا */ }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [password]);
  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 5000); return () => clearTimeout(t); } }, [msg]);

  const save = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/github`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ repo }),
      });
      const d = await res.json().catch(() => ({}));
      if (res.ok) {
        setSaved(d.repo || "");
        setRepo(d.repo || "");
        setMsg({ t: "ok", m: d.latestTag
          ? `متصل شد — آخرین نسخه: ${d.latestTag}`
          : "ذخیره شد" });
      } else {
        setMsg({ t: "err", m: d.detail || "ذخیره ناموفق بود" });
      }
    } catch { setMsg({ t: "err", m: "اتصال به سرور برقرار نشد" }); }
    finally { setBusy(false); }
  };

  if (loading) return null;

  const dirty = repo.trim() !== saved;

  return (
    <div className="fx-card p-5 mb-4">
      <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2">
        <Github size={15} style={{ color: "var(--accent-2)" }} /> مخزن به‌روزرسانی
      </div>
      <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
        وقتی مخزن را وصل کنید، پنل نسخه‌های جدید را از Releases گیت‌هاب می‌گیرد
        و به‌روزرسانی از همین‌جا انجام می‌شود.
      </p>

      <Field label="آدرس مخزن" hint="مثلاً username/nexora — یا لینک کامل گیت‌هاب">
        <div className="flex gap-2">
          <input className="fx-input" dir="ltr" value={repo}
            onChange={(e) => setRepo(e.target.value)}
            placeholder="username/nexora"
            onKeyDown={(e) => e.key === "Enter" && dirty && save()}
            style={{ fontFamily: "var(--mono)" }} />
          <button onClick={save} disabled={busy || !dirty}
            className="fx-btn px-4 py-2.5 text-[14px] shrink-0 flex items-center gap-1.5"
            style={!dirty ? { opacity: 0.45, cursor: "not-allowed" } : {}}>
            {busy ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
            {busy ? "بررسی..." : "اتصال"}
          </button>
        </div>
      </Field>

      {msg && (
        <div className="rounded-xl p-3 mb-3 flex items-start gap-2 text-[13px] leading-relaxed"
          style={{
            background: msg.t === "err" ? "rgba(248,113,113,.1)" : "rgba(52,211,153,.1)",
            border: `1px solid ${msg.t === "err" ? "rgba(248,113,113,.3)" : "rgba(52,211,153,.3)"}`,
            color: msg.t === "err" ? "var(--danger)" : "var(--ok)",
          }}>
          {msg.t === "err" ? <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                           : <CheckCircle2 size={14} className="shrink-0 mt-0.5" />}
          <span>{msg.m}</span>
        </div>
      )}

      {saved ? (
        <div className="flex items-center gap-2 text-[13px]" style={{ color: "var(--ok)" }}>
          <CheckCircle2 size={13} />
          متصل به{" "}
          <a href={`https://github.com/${saved}`} target="_blank" rel="noreferrer"
            dir="ltr" className="underline"
            style={{ color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
            {saved}
          </a>
        </div>
      ) : (
        <InfoBox>
          <b>قبل از اتصال:</b> مخزن باید عمومی باشد و حداقل یک Release داشته باشد.
          پنل هنگام اتصال این را بررسی می‌کند.
        </InfoBox>
      )}
    </div>
  );
}

/* ===================== کارت به‌روزرسانی ===================== */

function UpdateCard({ password }) {
  const [info, setInfo] = useState(null);
  const [checking, setChecking] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [stuck, setStuck] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const finishRef = React.useRef(null);
  const [log, setLog] = useState([]);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const check = async () => {
    setChecking(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/check-update`, { headers: { "X-Admin-Password": password } });
      if (res.ok) setInfo(await res.json());
    } catch { /* بی‌صدا */ }
    finally { setChecking(false); }
  };

  useEffect(() => { check(); }, [password]);

  // در حین به‌روزرسانی، لاگ را دنبال می‌کنیم.
  // نکته‌ی مهم: سرویس وسط کار ری‌استارت می‌شود، پس درخواست‌ها موقتاً شکست
  // می‌خورند. برای همین چند محافظ لازم است تا صفحه گیر نکند:
  //   ۱. سقف زمانی کلی (۶ دقیقه) — بعد از آن به‌هرحال رفرش می‌کنیم
  //   ۲. تشخیص بازگشت سرویس: اگر بعد از قطعی دوباره سالم شد، یعنی تمام شده
  //   ۳. رفرش خودکار در هر حالت پایان
  useEffect(() => {
    if (!updating) return;

    let elapsed = 0;
    let sawDowntime = false;
    let quiet = 0;          // چند بار پشت سر هم لاگ بدون تغییر ماند
    let lastLen = 0;
    let done = false;

    const finish = (delay = 2200) => {
      if (done) return;
      done = true;
      clearInterval(timer);
      setUpdating(false);
      setTimeout(() => window.location.reload(), delay);
    };
    finishRef.current = finish;

    const timer = setInterval(async () => {
      elapsed += 2000;
      setElapsedSec(Math.floor(elapsed / 1000));

      // سقف کلی — ۴ دقیقه کافی است؛ بیشتر یعنی چیزی خراب شده
      if (elapsed > 240000) {
        setLog((l) => [...l, "— زمان انتظار تمام شد —"]);
        setStuck(true);
        clearInterval(timer);
        return;
      }

      try {
        const ctrl = new AbortController();
        const to = setTimeout(() => ctrl.abort(), 4000);
        const res = await fetch(`${API_URL}/api/admin/update-log?_t=${Date.now()}`, {
          headers: { "X-Admin-Password": password },
          cache: "no-store",
          signal: ctrl.signal,
        });
        clearTimeout(to);

        if (res.ok) {
          const d = await res.json();
          const lines = d.lines || [];
          if (lines.length) setLog(lines);

          if (d.finished || d.failed) { finish(); return; }

          // سرویس برگشته بعد از قطعی → کار تمام است
          if (sawDowntime) {
            setLog((l) => [...l, "— سرویس بازگشت —"]);
            finish(1500);
            return;
          }

          // لاگ بی‌حرکت: اگر ۳۰ ثانیه هیچ خط تازه‌ای نیامد و سرویس هم
          // سالم است، یعنی یا تمام شده یا گیر کرده. به کاربر اختیار می‌دهیم
          // به‌جای اینکه بی‌صدا منتظر بماند.
          if (lines.length === lastLen) {
            quiet += 1;
            if (quiet >= 15) {
              setStuck(true);
              clearInterval(timer);
              return;
            }
          } else {
            quiet = 0;
            lastLen = lines.length;
          }
        }
      } catch {
        // سرویس در حال ری‌استارت — طبیعی است
        sawDowntime = true;
        quiet = 0;
      }
    }, 2000);

    return () => clearInterval(timer);
  }, [updating, password]);

  const startUpdate = async () => {
    setConfirmOpen(false);
    setStuck(false);
    setElapsedSec(0);
    setUpdating(true);
    setLog(["در حال شروع به‌روزرسانی..."]);
    try {
      await fetch(`${API_URL}/api/admin/run-update`, {
        method: "POST",
        headers: { "X-Admin-Password": password },
      });
    } catch { /* سرویس ری‌استارت می‌شود، خطا طبیعی است */ }
  };

  const hasUpdate = info?.updateAvailable;

  return (
    <>
      <div className="fx-card p-5 mb-4" style={hasUpdate ? { borderColor: "rgba(52,211,153,.4)", boxShadow: "0 0 24px rgba(52,211,153,.08)" } : {}}>
        <div className="flex items-start justify-between gap-3 flex-wrap mb-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="fx-ico" style={{ background: hasUpdate ? "rgba(52,211,153,.12)" : "rgba(43,127,214,.12)" }}>
              <RefreshCw size={16} className={checking ? "animate-spin" : ""}
                style={{ color: hasUpdate ? "var(--ok)" : "var(--accent-2)" }} />
            </div>
            <div className="min-w-0">
              <div className="text-[14px] font-semibold text-white">به‌روزرسانی</div>
              <div className="text-[13px] mt-0.5" style={{ color: "var(--muted)" }}>
                {checking ? "در حال بررسی..." :
                 !info?.configured ? "به‌روزرسانی خودکار تنظیم نشده" :
                 info?.error ? "ارتباط با گیت‌هاب برقرار نشد" :
                 hasUpdate ? `نسخه ${info.latestVersion} در دسترس است` :
                 "شما آخرین نسخه را دارید"}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="fx-pill" style={{ background: "rgba(255,255,255,.05)", color: "var(--muted)" }}>
              نسخه فعلی: {info?.currentVersion || "?"}
            </span>
            {!updating && (
              <button onClick={check} className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
                <RefreshCw size={12} /> بررسی مجدد
              </button>
            )}
          </div>
        </div>

        {/* در حال به‌روزرسانی */}
        {updating && (
          <div className="rounded-xl p-4"
            style={{ background: "var(--surface-3)", border: `1px solid ${stuck ? "rgba(251,191,36,.35)" : "rgba(90,169,230,.3)"}` }}>
            <div className="flex items-center justify-between gap-2 mb-3 flex-wrap">
              <div className="flex items-center gap-2">
                {stuck
                  ? <AlertTriangle size={14} style={{ color: "var(--warn)" }} />
                  : <Loader2 size={14} className="animate-spin" style={{ color: "var(--accent-2)" }} />}
                <span className="text-[13px] font-semibold"
                  style={{ color: stuck ? "var(--warn)" : "var(--accent-2)" }}>
                  {stuck ? "پاسخی از سرور نمی‌آید" : "در حال به‌روزرسانی — صفحه را نبندید"}
                </span>
              </div>
              <span className="text-[13px]" style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                {Math.floor(elapsedSec / 60)}:{String(elapsedSec % 60).padStart(2, "0")}
              </span>
            </div>

            {stuck && (
              <div className="rounded-xl p-3 mb-3 text-[13px] leading-relaxed"
                style={{ background: "rgba(251,191,36,.08)", border: "1px solid rgba(251,191,36,.25)", color: "var(--dim)" }}>
                لاگی دریافت نمی‌شود. معمولاً یعنی به‌روزرسانی تمام شده و سرویس ری‌استارت شده،
                ولی گاهی هم یعنی چیزی خطا داده. یکی از گزینه‌های زیر را انتخاب کنید.
              </div>
            )}

            {stuck && (
              <div className="flex gap-2 mb-3 flex-wrap">
                <button onClick={() => window.location.reload()}
                  className="fx-btn px-4 py-2.5 text-[13px] flex items-center gap-1.5">
                  <RefreshCw size={13} /> بارگذاری مجدد پنل
                </button>
                <button onClick={() => { setStuck(false); setUpdating(false); }}
                  className="fx-btn-g px-4 py-2.5 text-[13px]">
                  بستن و ادامه کار
                </button>
              </div>
            )}
            <div className="rounded-lg p-3 max-h-52 overflow-y-auto" dir="ltr"
              style={{ background: "#05070C", border: "1px solid var(--border)" }}>
              {log.length === 0 ? (
                <div className="text-[13px]" style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                  waiting for output...
                </div>
              ) : log.map((l, i) => (
                <div key={i} className="text-[13px] leading-relaxed"
                  style={{ color: l.includes("✓") ? "var(--ok)" : l.includes("✗") ? "var(--danger)" : "var(--dim)",
                           fontFamily: "var(--mono)" }}>
                  {l}
                </div>
              ))}
            </div>
            <p className="text-[12px] mt-3" style={{ color: "var(--muted)" }}>
              بعد از اتمام، صفحه خودکار بارگذاری مجدد می‌شود.
            </p>
          </div>
        )}

        {/* نسخه جدید موجود است */}
        {!updating && hasUpdate && (
          <>
            <div className="rounded-xl p-4 mb-3" style={{ background: "rgba(52,211,153,.06)", border: "1px solid rgba(52,211,153,.25)" }}>
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 size={14} style={{ color: "var(--ok)" }} />
                <span className="text-[14px] font-semibold" style={{ color: "var(--ok)" }}>
                  نسخه {info.latestVersion} منتشر شده
                </span>
              </div>
              {info.releaseNotes && (
                <div className="text-[13px] leading-relaxed max-h-32 overflow-y-auto mt-2 whitespace-pre-line"
                  style={{ color: "var(--dim)" }}>
                  {info.releaseNotes}
                </div>
              )}
            </div>

            <button onClick={() => setConfirmOpen(true)}
              className="fx-btn w-full py-3 text-[14px] flex items-center justify-center gap-2">
              <Download size={15} /> به‌روزرسانی به نسخه {info.latestVersion}
            </button>

            <p className="text-[12px] mt-2.5 text-center" style={{ color: "var(--muted)" }}>
              تنظیمات، رمز عبور و واسطه‌های شما حفظ می‌شوند
            </p>
          </>
        )}

        {/* آخرین نسخه */}
        {!updating && !hasUpdate && info?.configured && !info?.error && (
          <div className="rounded-xl p-4 flex items-center gap-2.5" style={{ background: "rgba(52,211,153,.06)", border: "1px solid rgba(52,211,153,.2)" }}>
            <CheckCircle2 size={15} style={{ color: "var(--ok)" }} />
            <span className="text-[13px]" style={{ color: "var(--dim)" }}>
              شما آخرین نسخه ({info.currentVersion}) را دارید
            </span>
          </div>
        )}

        {/* تنظیم نشده */}
        {!updating && !info?.configured && !checking && (
          <div className="rounded-xl p-4" style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
            <p className="text-[13px] mb-2.5" style={{ color: "var(--dim)" }}>
              برای فعال‌سازی به‌روزرسانی خودکار، این دستور را روی سرور اجرا کنید:
            </p>
            <code dir="ltr" className="block px-3 py-2.5 rounded-lg text-[13px]"
              style={{ background: "#05070C", border: "1px solid var(--border-2)", color: "var(--accent-2)",
                       fontFamily: "var(--mono)", wordBreak: "break-all" }}>
              echo 'GITHUB_REPO="nexoratech-v/nexora-subscription-manager"' &gt; /opt/nexora-panel/.github
            </code>
            <p className="text-[12px] mt-2" style={{ color: "var(--muted)" }}>
              سپس <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>nexora restart</span> را بزنید.
            </p>
          </div>
        )}

        {/* خطای اتصال */}
        {!updating && info?.error && (
          <div className="rounded-xl p-4" style={{ background: "rgba(251,191,36,.06)", border: "1px solid rgba(251,191,36,.25)" }}>
            <div className="flex items-start gap-2.5">
              <AlertTriangle size={15} className="shrink-0 mt-0.5" style={{ color: "var(--warn)" }} />
              <div>
                <div className="text-[13px] mb-1" style={{ color: "var(--warn)" }}>ارتباط با گیت‌هاب برقرار نشد</div>
                <div className="text-[12px]" style={{ color: "var(--muted)" }}>
                  ممکن است سرور به گیت‌هاب دسترسی نداشته باشد. می‌توانید از ترمینال به‌روزرسانی کنید:
                  <span dir="ltr" style={{ fontFamily: "var(--mono)" }}> nexora update</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {confirmOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 fx-fade"
          style={{ background: "rgba(3,6,12,.78)", backdropFilter: "blur(6px)" }} onClick={() => setConfirmOpen(false)}>
          <div className="w-full max-w-sm rounded-2xl p-5 fx-scale" onClick={(e) => e.stopPropagation()}
            style={{ background: "var(--surface)", border: "1px solid rgba(90,169,230,.35)" }}>
            <div className="flex items-center gap-2 mb-2.5" style={{ color: "var(--accent-2)" }}>
              <Download size={18} />
              <span className="text-[16px] font-semibold">به‌روزرسانی به {info?.latestVersion}؟</span>
            </div>
            <p className="text-[13px] mb-3 leading-relaxed" style={{ color: "var(--muted)" }}>
              سرویس برای چند دقیقه ری‌استارت می‌شود. صفحه‌ی اشتراک مشتریان در این مدت
              با تنظیمات فعلی به کار خود ادامه می‌دهد.
            </p>
            <div className="rounded-lg p-3 mb-4" style={{ background: "rgba(52,211,153,.07)", border: "1px solid rgba(52,211,153,.2)" }}>
              <div className="text-[13px] leading-relaxed" style={{ color: "var(--dim)" }}>
                قبل از شروع، یک بک‌آپ خودکار از تنظیمات گرفته می‌شود.
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setConfirmOpen(false)} className="fx-btn-g flex-1 py-2.5 text-[14px]">انصراف</button>
              <button onClick={startUpdate} className="fx-btn flex-1 py-2.5 text-[14px]">شروع به‌روزرسانی</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ===================== سیستم و به‌روزرسانی ===================== */

function SystemSection({ password }) {
  const [sys, setSys] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/admin/system`, { headers: { "X-Admin-Password": password } });
        if (res.ok) setSys(await res.json());
      } catch { /* بی‌صدا */ }
      finally { setLoading(false); }
    })();
  }, [password]);

  const CMD = ({ children }) => (
    <code dir="ltr" className="block px-3 py-2.5 rounded-lg text-[13px] my-1.5"
      style={{ background: "var(--surface-3)", border: "1px solid var(--border-2)",
               color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
      {children}
    </code>
  );

  if (loading) {
    return <div className="flex items-center justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;
  }

  return (
    <div className="fx-anim">
      <SectionHead title="سیستم و به‌روزرسانی" desc="وضعیت نصب، نسخه‌ی فعلی و راهنمای به‌روزرسانی." />

      {/* وضعیت */}
      <div className="fx-g4 grid grid-cols-4 gap-3 mb-4">
        <div className="fx-card p-4">
          <div className="fx-ico mb-3" style={{ background: "rgba(43,127,214,.12)" }}>
            <Server size={16} style={{ color: "var(--accent-2)" }} />
          </div>
          <div className="text-[18px] font-bold text-white" style={{ fontFamily: "var(--mono)" }}>
            {sys?.version || "?"}
          </div>
          <div className="text-[13px] mt-1" style={{ color: "var(--dim)" }}>نسخه فعلی</div>
        </div>

        <div className="fx-card p-4">
          <div className="fx-ico mb-3" style={{ background: sys?.template?.exists ? "rgba(52,211,153,.12)" : "rgba(248,113,113,.12)" }}>
            <HardDrive size={16} style={{ color: sys?.template?.exists ? "var(--ok)" : "var(--danger)" }} />
          </div>
          <div className="text-[16px] font-bold" style={{ color: sys?.template?.exists ? "var(--ok)" : "var(--danger)" }}>
            {sys?.template?.exists ? "نصب شده" : "پیدا نشد"}
          </div>
          <div className="text-[13px] mt-1" style={{ color: "var(--dim)" }}>قالب صفحه اشتراک</div>
          {sys?.template?.size > 0 && (
            <div className="text-[12px] mt-0.5" style={{ color: "var(--muted)" }}>
              {(sys.template.size / 1024).toFixed(0)} KB
            </div>
          )}
        </div>

        <div className="fx-card p-4">
          <div className="fx-ico mb-3" style={{ background: "rgba(167,139,250,.12)" }}>
            <Smartphone size={16} style={{ color: "var(--purple)" }} />
          </div>
          <div className="text-[18px] font-bold text-white" style={{ fontFamily: "var(--mono)" }}>
            {sys?.counts?.apps ?? 0}
          </div>
          <div className="text-[13px] mt-1" style={{ color: "var(--dim)" }}>اپلیکیشن</div>
        </div>

        <div className="fx-card p-4">
          <div className="fx-ico mb-3" style={{ background: "rgba(251,191,36,.12)" }}>
            <Users size={16} style={{ color: "var(--warn)" }} />
          </div>
          <div className="text-[18px] font-bold text-white" style={{ fontFamily: "var(--mono)" }}>
            {sys?.counts?.resellers ?? 0}
          </div>
          <div className="text-[13px] mt-1" style={{ color: "var(--dim)" }}>واسطه</div>
        </div>
      </div>

      {/* هشدار آدرس API */}
      {sys?.template?.apiUrl?.includes("localhost") && (
        <div className="mb-4">
          <InfoBox tone="warn">
            <b>هشدار:</b> آدرس API داخل قالب روی <span dir="ltr">localhost</span> است.
            مرورگر مشتری نمی‌تواند به آن وصل شود و تنظیمات پنل اعمال نخواهد شد.
            <br />با دستور <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>nexora update</span> یا اجرای مجدد نصب، آن را به دامنه‌ی واقعی تغییر دهید.
          </InfoBox>
        </div>
      )}

      {/* مسیرها */}
      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-4 flex items-center gap-2">
          <HardDrive size={15} style={{ color: "var(--accent-2)" }} /> مسیرهای نصب
        </div>
        <div className="flex flex-col gap-2.5">
          {[
            { l: "قالب صفحه اشتراک", v: sys?.template?.path },
            { l: "فایل تنظیمات", v: sys?.configPath },
            { l: "آدرس API در قالب", v: sys?.template?.apiUrl },
          ].map((row, i) => (
            <div key={i} className="flex items-center justify-between gap-3 py-2" style={{ borderBottom: i < 2 ? "1px solid var(--border)" : "none" }}>
              <span className="text-[13px] shrink-0" style={{ color: "var(--dim)" }}>{row.l}</span>
              <span dir="ltr" className="text-[13px] truncate" style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                {row.v || "—"}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* به‌روزرسانی */}
      {sys?.build?.stale && (
        <div className="fx-card p-4 mb-4 flex items-start gap-3"
          style={{ background: "rgba(251,191,36,.08)", borderColor: "rgba(251,191,36,.35)" }}>
          <AlertTriangle size={17} style={{ color: "var(--warn)", flexShrink: 0, marginTop: 2 }} />
          <div className="flex-1">
            <div className="text-[14px] font-semibold text-white mb-1">
              پنل با کد فعلی ساخته نشده
            </div>
            <div className="text-[13px] leading-relaxed" style={{ color: "var(--dim)" }}>
              کد به‌روز است ولی صفحه‌ای که می‌بینید از بیلد قبلی است — به همین دلیل
              قابلیت‌های جدید ظاهر نمی‌شوند. معمولاً یعنی بیلد در آخرین به‌روزرسانی
              شکست خورده است.
              <br />
              <code dir="ltr" className="inline-block mt-2 px-3 py-1.5 rounded-lg text-[13px]"
                style={{ background: "var(--surface-3)", color: "var(--warn)", fontFamily: "var(--mono)" }}>
                nexora rebuild
              </code>
            </div>
          </div>
        </div>
      )}

      <GithubCard password={password} />
      <UpdateCard password={password} />
      <RollbackCard password={password} />

      {/* دستورات */}
      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-4 flex items-center gap-2">
          <Terminal size={15} style={{ color: "var(--accent-2)" }} /> دستورات مدیریتی
        </div>
        {[
          { c: "nexora status", d: "وضعیت کامل سرویس‌ها" },
          { c: "nexora logs", d: "لاگ زنده (خروج با Ctrl+C)" },
          { c: "nexora restart", d: "ری‌استارت بک‌اند" },
          { c: "nexora rebuild", d: "ساخت مجدد پنل (رفع مشکل ظاهری)" },
          { c: "nexora backup", d: "بک‌آپ فوری از تنظیمات" },
          { c: "nexora snapshots", d: "لیست نسخه‌های ذخیره‌شده" },
          { c: "nexora rollback", d: "بازگشت به نسخه قبل" },
          { c: "nexora diagnose", d: "عیب‌یابی نمایش قالب" },
        ].map((x, i, arr) => (
          <div key={i} className="flex items-center justify-between gap-3 py-2" style={{ borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
            <code dir="ltr" className="text-[13px]" style={{ color: "var(--accent-2)", fontFamily: "var(--mono)" }}>{x.c}</code>
            <span className="text-[13px]" style={{ color: "var(--muted)" }}>{x.d}</span>
          </div>
        ))}
      </div>

      <InfoBox>
        قبل از هر به‌روزرسانی، یک بک‌آپ دستی هم بگیرید: <b>تنظیمات → پشتیبان‌گیری → دریافت پشتیبان</b>
      </InfoBox>
    </div>
  );
}

/* ===================== پیش‌نمایش زنده صفحه اشتراک ===================== */

function LivePreview({ dirty, onSave, saving }) {
  const [key, setKey] = useState(0);
  const [device, setDevice] = useState("mobile");
  const [loading, setLoading] = useState(true);
  const [zoom, setZoom] = useState(100);

  const DEVICES = {
    mobile: { w: 390, label: "موبایل", icon: Smartphone, sub: "iPhone 14 Pro" },
    tablet: { w: 768, label: "تبلت", icon: Monitor, sub: "iPad" },
    desktop: { w: 1200, label: "دسکتاپ", icon: Monitor, sub: "لپ‌تاپ" },
  };
  const d = DEVICES[device];
  const scale = zoom / 100;

  const refresh = () => { setLoading(true); setKey((k) => k + 1); };

  return (
    <div className="fx-anim">
      <SectionHead
        title="پیش‌نمایش زنده"
        desc="دقیقاً همان چیزی که مشتری می‌بیند — با تنظیمات ذخیره‌شده‌ی شما و داده‌ی نمونه."
      />

      {dirty && (
        <div className="mb-4">
          <div className="rounded-2xl p-4 flex items-start gap-3 flex-wrap" style={{ background: "rgba(251,191,36,.07)", border: "1px solid rgba(251,191,36,.28)" }}>
            <AlertTriangle size={16} className="shrink-0 mt-0.5" style={{ color: "var(--warn)" }} />
            <div className="flex-1 min-w-[200px]">
              <div className="text-[14px] font-semibold mb-1" style={{ color: "var(--warn)" }}>تغییرات ذخیره‌نشده دارید</div>
              <p className="text-[13px] leading-relaxed" style={{ color: "var(--dim)" }}>
                پیش‌نمایش، آخرین نسخه‌ی <b>ذخیره‌شده</b> را نشان می‌دهد. برای دیدن تغییرات جدید، اول ذخیره کنید.
              </p>
            </div>
            <button onClick={async () => { await onSave(); setTimeout(refresh, 300); }} disabled={saving}
              className="fx-btn px-3.5 py-2 text-[13px] flex items-center gap-1.5 shrink-0">
              {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
              ذخیره و به‌روزرسانی
            </button>
          </div>
        </div>
      )}

      {/* نوار ابزار */}
      <div className="fx-card p-3 mb-4 flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1 p-1 rounded-[11px]" style={{ background: "var(--surface-3)", border: "1px solid var(--border-2)" }}>
            {Object.entries(DEVICES).map(([k, v]) => (
              <button key={k} onClick={() => setDevice(k)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-[9px] text-[13px] font-medium transition-all"
                style={device === k ? { background: "var(--accent-2)", color: "#06090F" } : { color: "var(--muted)" }}>
                <v.icon size={12} /> {v.label}
              </button>
            ))}
          </div>
          <span className="text-[12px] px-2.5 py-1.5 rounded-lg" style={{ background: "var(--surface-3)", color: "var(--muted)", fontFamily: "var(--mono)" }}>
            {d.w}px · {d.sub}
          </span>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1 px-1 py-1 rounded-[11px]" style={{ background: "var(--surface-3)", border: "1px solid var(--border-2)" }}>
            <button onClick={() => setZoom((z) => Math.max(50, z - 10))} className="fx-ico-btn" style={{ width: 28, height: 28 }} aria-label="کوچک‌نمایی"><Minus size={13} /></button>
            <span className="text-[13px] w-11 text-center" style={{ color: "var(--dim)", fontFamily: "var(--mono)" }}>{zoom}%</span>
            <button onClick={() => setZoom((z) => Math.min(150, z + 10))} className="fx-ico-btn" style={{ width: 28, height: 28 }} aria-label="بزرگ‌نمایی"><Plus size={13} /></button>
          </div>
          <a href={`${API_URL}/api/preview`} target="_blank" rel="noreferrer" className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
            <ExternalLink size={13} /> <span className="fx-hide-m">تب جدید</span>
          </a>
          <button onClick={refresh} className="fx-btn px-3.5 py-2 text-[13px] flex items-center gap-1.5">
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} /> به‌روزرسانی
          </button>
        </div>
      </div>

      {/* ناحیه پیش‌نمایش با اسکرول */}
      <div className="fx-card overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2.5" style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-3)" }}>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#FF5F57" }} />
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#FEBC2E" }} />
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#28C840" }} />
          </div>
          <div className="text-[12px] px-3 py-1 rounded-md flex-1 mx-3 text-center truncate" dir="ltr"
            style={{ background: "var(--surface)", color: "var(--muted)", fontFamily: "var(--mono)" }}>
            {API_URL}/api/preview
          </div>
          <div className="w-14 fx-hide-m" />
        </div>

        <div className="nx-preview-scroll" style={{ background: "#05070C" }}>
          <div className="flex justify-center p-6" style={{ minWidth: device === "desktop" ? d.w * scale + 48 : "auto" }}>
            <div className="relative" style={{ width: d.w * scale, transition: "width .25s ease" }}>
              {loading && (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 rounded-[18px] z-10" style={{ background: "var(--surface-3)" }}>
                  <Loader2 size={22} className="animate-spin" style={{ color: "var(--accent-2)" }} />
                  <span className="text-[13px]" style={{ color: "var(--muted)" }}>در حال بارگذاری...</span>
                </div>
              )}
              <iframe
                key={key}
                src={`${API_URL}/api/preview?t=${key}`}
                onLoad={() => setLoading(false)}
                title="پیش‌نمایش صفحه اشتراک"
                style={{
                  width: d.w,
                  height: 760,
                  border: "1px solid var(--border-2)",
                  borderRadius: 18,
                  background: "var(--bg)",
                  display: "block",
                  transform: `scale(${scale})`,
                  transformOrigin: "top center",
                  transition: "transform .25s ease",
                }}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4">
        <InfoBox>
          داده‌های نمایش‌داده‌شده (حجم، تاریخ انقضا، کانفیگ‌ها) <b>نمونه</b> هستند و در سرور واقعی با اطلاعات هر مشتری جایگزین می‌شوند — ولی تمام تنظیماتی که در این پنل ذخیره کرده‌اید (اپ‌ها، رنگ‌ها، بنرها، متن‌ها) دقیقاً همان‌طور که اینجا می‌بینید اعمال می‌شوند.
        </InfoBox>
      </div>
    </div>
  );
}

/* ===================== اپ اصلی ===================== */

export default function App() {
  const [password, setPassword] = useState(() => localStorage.getItem("nexora_subpage_admin_pw") || "");
  const [authed, setAuthed] = useState(false);
  const [config, setConfigRaw] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [active, setActive] = useState("overview");
  const [workspace, setWorkspace] = useState(() => {
    const w = localStorage.getItem("nexora_workspace");
    return WORKSPACES[w] ? w : "sub";
  });

  // حالت نمایش سوییچ فضای کاری — سلیقه‌ای است، پس در مرورگر می‌ماند
  const [wsMode, setWsMode] = useState(() => {
    try {
      const m = localStorage.getItem("nexora-ws-mode");
      return WS_MODES[m] ? m : "accordion";
    } catch {
      return "accordion";
    }
  });

  useEffect(() => {
    try { localStorage.setItem("nexora-ws-mode", wsMode); } catch { /* بی‌صدا */ }
  }, [wsMode]);
  const [confirmTarget, setConfirmTarget] = useState(null);
  const [toast, setToast] = useState(null);
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  // نسخه‌ی آخرین حالت ذخیره‌شده — مرجع برای لغو تغییرات
  const [savedConfig, setSavedConfig] = useState(null);

  const setConfig = (next) => { setConfigRaw(next); setDirty(true); };

  // بازگرداندن همه‌ی تغییرات ذخیره‌نشده به آخرین حالت ذخیره‌شده
  const discardChanges = () => {
    if (!savedConfig) return;
    setConfigRaw(JSON.parse(JSON.stringify(savedConfig)));
    setDirty(false);
    setToast({ message: "تغییرات لغو شد", type: "ok" });
  };

  const fetchAll = useCallback(async (pw) => {
    setLoading(true);
    try {
      const [cRes, sRes] = await Promise.all([
        fetch(`${API_URL}/api/admin/config`, { headers: { "X-Admin-Password": pw } }),
        fetch(`${API_URL}/api/admin/stats`, { headers: { "X-Admin-Password": pw } }),
      ]);
      if (!cRes.ok) throw new Error();
      const loaded = await cRes.json();
      setConfigRaw(loaded);
      setSavedConfig(JSON.parse(JSON.stringify(loaded)));
      if (sRes.ok) setStats(await sRes.json());
      setAuthed(true);
    } catch { setAuthed(false); localStorage.removeItem("nexora_subpage_admin_pw"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { if (password) fetchAll(password); else setLoading(false); }, [password, fetchAll]);
  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(null), 3000); return () => clearTimeout(t); } }, [toast]);
  useEffect(() => {
    const h = (e) => { if (dirty) { e.preventDefault(); e.returnValue = ""; } };
    window.addEventListener("beforeunload", h);
    return () => window.removeEventListener("beforeunload", h);
  }, [dirty]);
  // هنگام باز بودن کشو: بستن با Escape.
  // نکته: اسکرول body را قفل نمی‌کنیم چون خود سایدبار اسکرول داخلی دارد
  // و قفل‌کردن body در بعضی مرورگرهای موبایل باعث گیرکردن کل صفحه می‌شود.
  useEffect(() => {
    if (!open) return;
    const k = (e) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [open]);

  const navigate = (k) => { setActive(k); setOpen(false); };

  // اگر صفحه‌ی فعال در حالت کاری جاری وجود نداشت (مثلاً بعد از رفرش)،
  // خودکار به اولین صفحه‌ی همان حالت می‌رویم تا صفحه‌ی خالی نبینیم.
  useEffect(() => {
    const keys = WORKSPACES[workspace].groups.flatMap((g) => g.items).map((i) => i.key);
    if (!keys.includes(active)) {
      const first = WORKSPACES[workspace].groups.flatMap((g) => g.items).find((i) => !i.badge);
      if (first) setActive(first.key);
    }
  }, [workspace, active]);

  // تعویض حالت کاری — به اولین آیتم فعال همان حالت می‌رود
  const switchWorkspace = (wsKey) => {
    setWorkspace(wsKey);
    localStorage.setItem("nexora_workspace", wsKey);
    const first = WORKSPACES[wsKey].groups
      .flatMap((g) => g.items)
      .find((i) => !i.badge);
    if (first) setActive(first.key);
    setOpen(false);
  };
  const login = (pw) => { localStorage.setItem("nexora_subpage_admin_pw", pw); setPassword(pw); };
  const logout = () => { localStorage.removeItem("nexora_subpage_admin_pw"); setPassword(""); setAuthed(false); };

  // بعد از تغییر موفق رمز، رمز جدید را جایگزین می‌کنیم تا کاربر
  // بدون نیاز به ورود مجدد بتواند به کارش ادامه دهد.
  const handlePasswordChanged = (newPw) => {
    localStorage.setItem("nexora_subpage_admin_pw", newPw);
    setPassword(newPw);
    setToast({ message: "رمز عبور تغییر کرد — نیازی به ورود مجدد نیست", type: "ok" });
  };

  const save = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify(config),
      });
      if (res.ok) {
        setDirty(false);
        setSavedConfig(JSON.parse(JSON.stringify(config)));
        setToast({ message: "تغییرات با موفقیت ذخیره شد", type: "ok" });
        const sRes = await fetch(`${API_URL}/api/admin/stats`, { headers: { "X-Admin-Password": password } });
        if (sRes.ok) setStats(await sRes.json());
      } else setToast({ message: "ذخیره‌سازی ناموفق بود", type: "error" });
    } catch { setToast({ message: "اتصال به سرور برقرار نشد", type: "error" }); }
    finally { setSaving(false); }
  };

  const confirmDelete = () => {
    const t = confirmTarget;
    if (t.type === "app") setConfig({ ...config, downloadApps: { ...(config.downloadApps || {}), [t.os]: (config.downloadApps?.[t.os] || []).filter((_, i) => i !== t.idx) } });
    else if (t.type === "faq") setConfig({ ...config, faq: { ...config.faq, [t.lang]: (config.faq?.[t.lang] || []).filter((_, i) => i !== t.idx) } });
    else if (t.type === "video") setConfig({ ...config, videos: config.videos.filter((_, i) => i !== t.idx) });
    else if (t.type === "reseller") setConfig({ ...config, resellers: config.resellers.filter((_, i) => i !== t.idx) });
    setConfirmTarget(null);
  };

  if (!password || !authed) {
    if (loading && password) return <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg)" }}><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;
    return <LoginScreen onLogin={login} />;
  }
  if (loading || !config) return <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg)" }}><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  const currentNav = ALL_NAV.find((n) => n.key === active);
  const filteredNav = (items) => search ? items.filter((n) => n.label.includes(search)) : items;

  return (
    <div className="min-h-screen w-full flex" style={{ background: "var(--bg)" }} dir="rtl">
      {open && <div className="fx-backdrop fx-fade" onClick={() => setOpen(false)} />}

      <aside className={`fx-side ${open ? "open" : ""}`}>
        <div className="flex items-center justify-between gap-2 px-2 mb-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center font-bold text-[18px] shrink-0"
              style={{ background: "linear-gradient(135deg,#2B7FD6,#8FC1EE)", color: "#06090F" }}>N</div>
            <div className="min-w-0">
              <div className="text-[16px] font-bold text-white leading-none">NEXORA</div>
              <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>پنل مدیریت</div>
            </div>
          </div>
          <button className="lg:hidden shrink-0" onClick={() => setOpen(false)} style={{ color: "var(--dim)" }}><X size={18} /></button>
        </div>

        <WorkspaceSwitch mode={wsMode} workspace={workspace} onSwitch={switchWorkspace}
          active={active} setActive={setActive} />

        {/* در حالت تاشو، منو داخل خود آکاردئون است — اینجا تکرارش نمی‌کنیم */}
        {wsMode !== "accordion" && WORKSPACES[workspace].groups.map((group) => {
          const items = filteredNav(group.items);
          if (items.length === 0) return null;
          return (
            <div key={group.title}>
              <div className="fx-side-label">{group.title}</div>
              <nav className="flex flex-col gap-1">
                {items.map((n) => (
                  <button key={n.key} className={`fx-nav-item ${active === n.key ? "on" : ""}`}
                    onClick={() => navigate(n.key)} disabled={!!n.badge}
                    style={n.badge ? { opacity: 0.55, cursor: "not-allowed" } : {}}>
                    <n.icon size={16} />
                    <span className="flex-1 text-right">{n.label}</span>
                    {n.badge && (
                      <span className="text-[11px] px-1.5 py-0.5 rounded-full shrink-0"
                        style={{ background: "rgba(251,191,36,.15)", color: "var(--warn)" }}>
                        {n.badge}
                      </span>
                    )}
                  </button>
                ))}
              </nav>
            </div>
          );
        })}

        <div className="mt-6 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
          <div className="fx-card p-3 mb-3" style={{ background: "var(--surface-2)" }}>
            <div className="flex items-center gap-2 mb-1.5">
              <Circle size={7} fill="var(--ok)" strokeWidth={0} />
              <span className="text-[13px] font-semibold" style={{ color: "var(--ok)" }}>سرویس فعال</span>
            </div>
            <div className="text-[12px]" style={{ color: "var(--muted)" }} dir="ltr">t.me/{config.links?.channelUsername}</div>
          </div>
          <button onClick={logout} className="fx-nav-item"><LogOut size={15} /> خروج</button>
        </div>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="fx-topbar">
          <div className="flex items-center gap-3 min-w-0">
            <button className="fx-burger" onClick={() => setOpen(true)} aria-label="منو"><Menu size={19} /></button>
            <div className="min-w-0">
              <h1 className="text-[18px] font-bold text-white truncate">{currentNav?.label}</h1>
              <p className="text-[13px] mt-0.5 fx-hide-m" style={{ color: "var(--muted)" }}>مدیریت صفحه اشتراک مشتریان</p>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            <div className="fx-search">
              <Search size={14} style={{ color: "var(--muted)" }} />
              <input placeholder="جستجو در بخش‌ها..." value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
            <div className="fx-hide-m"><StatusChip dirty={dirty} /></div>
            {dirty && (
              <button onClick={discardChanges} title="بازگرداندن به آخرین حالت ذخیره‌شده"
                className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5 shrink-0">
                <RefreshCw size={13} className="scale-x-[-1]" />
                <span className="fx-hide-m">لغو تغییرات</span>
              </button>
            )}
            <button onClick={save} disabled={saving || !dirty} className="fx-desktop-save fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5 shrink-0">
              {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
              <span className="fx-hide-m">{saving ? "در حال ذخیره..." : "ذخیره تغییرات"}</span>
            </button>
          </div>
        </header>

        <main className="fx-main flex-1 p-7 overflow-y-auto w-full mx-auto">
          {active === "overview" && <OverviewSection config={config} stats={stats} navigate={navigate} dirty={dirty} />}
          {active === "preview" && <LivePreview dirty={dirty} onSave={save} saving={saving} />}
          {active === "apps" && <AppsSection config={config} setConfig={setConfig} requestDelete={setConfirmTarget} />}
          {active === "videos" && <VideosSection config={config} setConfig={setConfig} requestDelete={setConfirmTarget} />}
          {active === "faq" && <FaqSection config={config} setConfig={setConfig} requestDelete={setConfirmTarget} />}
          {active === "resellers" && <ResellersSection config={config} setConfig={setConfig} requestDelete={setConfirmTarget} password={password} />}
          {active === "bot" && <BotSection password={password} dirty={dirty} />}
          {active === "bot-inbounds" && <BotInboundsSection password={password} />}
          {active === "bot-plans" && <BotPlansSection password={password} />}
          {active === "bot-orders" && <BotOrdersSection password={password} />}
          {active === "bot-users" && <BotUsersSection password={password} />}
          {active === "bot-report" && <BotReportSection password={password} />}
          {active === "bot-coins" && <BotCoinsSection password={password} />}
          {active === "bot-affiliates" && <BotAffiliates password={password} />}
          {active === "bill-dash" && <BillingDash password={password} />}
          {active === "bill-groups" && <BillingGroups password={password} />}
          {active === "bill-invoice" && <BillingInvoice password={password} />}
          {active === "bill-pay" && <BillingPayments password={password} />}
          {active === "bill-period" && <BillingPeriod password={password} />}
          {active === "bill-clients" && <BillingClients password={password} />}
          {active === "tun-overview" && <TunnelOverview password={password} />}
          {active === "tun-nodes" && <TunnelNodes password={password} />}
          {active === "tun-list" && <TunnelList password={password} />}
          {active === "monitor" && <MonitorSection password={password} />}
          {active === "fw-rules" && <FirewallRules password={password} />}
          {active === "fw-blocked" && <FirewallBlocked password={password} />}
          {active === "tun-health" && <SystemHealth password={password} />}
          {active === "tun-events" && <TunnelEvents password={password} />}
          {active === "bill-settings" && <BillingSettings password={password} />}
          {active === "bot-texts" && <BotTextsSection password={password} />}
          {active === "bot-preview" && <BotPreviewSection />}
          {active === "bot-stats" && <BotStatsSection password={password} />}
          {active === "bot-backup" && <BotBackupSection password={password} />}
          {active === "popup" && <PopupSection config={config} setConfig={setConfig} />}
          {active === "banners" && <BannersSection config={config} setConfig={setConfig} />}
          {active === "referral" && <ReferralSection config={config} setConfig={setConfig} />}
          {active === "links" && <LinksSection config={config} setConfig={setConfig} />}
          {active === "settings" && <SettingsSection config={config} setConfig={setConfig} password={password} wsMode={wsMode} setWsMode={setWsMode} onPasswordChanged={handlePasswordChanged} onRestored={() => fetchAll(password)} />}
          {active === "themes" && <ThemesSection config={config} setConfig={setConfig} password={password} />}
          {active === "system" && <SystemSection password={password} />}
        </main>
      </div>

      <div className="fx-mobile-save">
        <div className="shrink-0"><StatusChip dirty={dirty} /></div>
        <button onClick={save} disabled={saving || !dirty} className="fx-btn flex-1 flex items-center justify-center gap-2 py-3 text-[14px]">
          {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
          {saving ? "در حال ذخیره..." : "ذخیره تغییرات"}
        </button>
      </div>

      {confirmTarget && (
        <ConfirmModal title="حذف این مورد؟"
          desc={`آیا مطمئن هستید می‌خواهید «${confirmTarget.name}» را حذف کنید؟ این عمل بعد از ذخیره‌ی تغییرات، از صفحه‌ی اشتراک هم حذف می‌شود.`}
          onConfirm={confirmDelete} onCancel={() => setConfirmTarget(null)} />
      )}
      {toast && <Toast message={toast.message} type={toast.type} />}
    </div>
  );
}
