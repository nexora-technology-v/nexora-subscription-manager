/**
 * استودیوی پوسته‌ی مینی‌اپ — مشترکِ پرتالِ نماینده و پنلِ مالک.
 *
 * تا ۱.۱۰۹ فقط در پرتال بود و مالک هیچ راهی برای شخصی‌سازیِ مینی‌اپِ
 * **خودش** نداشت. نسخه‌ی دوم ساخته نشد: همین کامپوننت، با `themeApi`ِ
 * دیگری که به مسیرهای مالک اشاره می‌کند.
 */
import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { createPortal } from "react-dom";
import {
  Activity, AlertTriangle, Bot, Camera, Check, Coins, Copy, CreditCard,
  Database, ExternalLink, Eye, FileText, Gift, Link2, Menu, MessageCircle, Moon, Play,
  Settings2, Sun,
  LayoutGrid, Loader2, Lock, LogOut, Package, Palette, Plus, Power, QrCode, RefreshCw, RotateCcw, Search,
  Sparkles,
  Trash2, Users, X, XCircle,
} from "lucide-react";

import { API_URL } from "../lib/constants";
import { errText, faDate, faNum, monoIf } from "../lib/format";
import { isoToJalaliLabel } from "../ui/jalali";
// usePager از کتابخانه‌ی مشترک می‌آید، نه کپیِ محلی: صفحه‌بندی یک
// قاعده است و دو پیاده‌سازی از یک قاعده دیر یا زود از هم جدا
// می‌شوند. این‌جا فقط همان چیزی گرفته می‌شود که ui/jalali هم هست —
// ابزار عمومی، نه کدِ پنل مدیر.
import { Avatar, EmptyState, MoneyInput, NumberInput, SkeletonCards, SkeletonTable,
         Toggle, usePager } from "../ui/index";
import { NexoraMark } from "../lib/mark.jsx";
// همان صفحه‌های پنلِ مالک، با داده‌ی خودِ نماینده — نه کپی.
// چرا: lib/botsrc.js. مرزِ واقعی بکند است (`portal_tenant`).
import { portalSrc } from "../lib/botsrc";
import { HomeDash } from "./dash.jsx";
import { MINI_PALETTES, MINI_SPLASHES, MINI_TEMPLATES, cleanSplash, themeVars } from "../lib/mini-themes.js";
import { LOGO_BGS, LOGO_SHAPES, ShopLogo, cleanLogoStyle } from "../lib/shoplogo.jsx";
import { BotUsersSection } from "../sections/bot/users";
import { BotInboxSection } from "../sections/bot/inbox";
import { BOT_BEHAVIOUR, BotTextsSection } from "../sections/bot/texts";
import { BotCoinsSection } from "../sections/bot/coins";
import { BotEventsSection } from "../sections/bot/events";

import { api } from "./api.js";

/**
 * قابِ هر پنجره‌ی پرتال — یا، با `inline`، یک صفحه‌ی داشبورد.
 *
 * چرا یکی: هشت پنجره هر کدام پرده‌ی خودش را داشت، با
 * `align-items: center`. پنجره‌ای که بلندتر از صفحه می‌شد، سرش
 * **بالای صفحه بریده می‌شد و با اسکرول هم برنمی‌گشت** — اندازه‌گیری‌شده
 * روی «ربات من»: ۱۴۱ پیکسل روی لپ‌تاپِ ۶۸۰ پیکسلی، یعنی عنوان و وضعیت
 * هیچ‌وقت دیده نمی‌شدند. `margin: auto` روی کارت، کوتاه را وسط می‌گذارد
 * و بلند را از بالا شروع می‌کند.
 *
 * و از راهِ پورتال روی `body`: داخلِ `.fx-anim` (صفحه‌های مالک که حالا
 * این‌جا سوارند) `transform` ماندگار هست و `fixed` در آن حبس می‌شود.
 */
export function Frame({ inline, onClose, width = 420, children }) {
  // صفحه، نه کارتِ شناور. قبلاً هر صفحه یک کارتِ ۶۴۰ پیکسلی وسطِ
  // ناحیه‌ی ۱۱۸۰ پیکسلی بود — نصفِ صفحه خالی، و روی گوشی کارت داخلِ
  // کارت. حالا خودِ صفحه شبکه است و عنوان را نوارِ بالا می‌گوید؛
  // عنوانِ خودِ پنجره (nx-box-head) در این حالت پنهان است.
  if (inline) {
    return <section className="nx-page">{children}</section>;
  }
  return createPortal(
    <div style={{
      position: "fixed", inset: 0, zIndex: 3000, display: "flex", padding: 16,
      background: "var(--scrim-3)", overflowY: "auto",
    }} onClick={onClose}>
      <div className="fx-card p-5" style={{ width, maxWidth: "100%", margin: "auto" }}
        onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
    </div>,
    document.body);
}

/*
 * پوسته‌ی شخصیِ نماینده.
 *
 * برگه: docs/specs/2026-09-22-reseller-and-ui.md
 *
 * برند و لوگو از قبل بودند و جای دیگری تنظیم می‌شدند؛ این‌جا رنگ
 * اضافه شد و — مهم‌تر — **پیش‌نمایش**. بدون پیش‌نمایش، نماینده
 * رنگ را ذخیره می‌کرد و تنها راهِ دیدنِ نتیجه باز کردنِ مینی‌اپ
 * با یک حسابِ واقعیِ تلگرام بود؛ یعنی عملاً هیچ‌وقت.
 */

//: پیشنهادها. نماینده می‌تواند هر رنگی بدهد، ولی انتخاب از میان
//: چند رنگِ سنجیده‌شده سریع‌تر است و به رنگِ ناخوانا نمی‌رسد.
const ACCENTS = [
  "#2b7fd6", "#7c5cff", "#00b894", "#e17055",
  "#e84393", "#f0a500", "#0aa2c0", "#8d6e63",
];

/*
 * استودیوی پوسته‌ی مینی‌اپ — قالب × پالت × لوگو.
 *
 * برگه: docs/specs/2026-09-23-mini-theme-studio.md
 *
 * مالک: «پیش‌نمایش فقط یک سری جزئیات را عوض می‌کند». راست می‌گفت:
 * پیش‌نمایشِ قبلی ماکتی دست‌ساز بود و فقط رنگِ دکمه‌اش عوض می‌شد.
 * حالا **خودِ مینی‌اپ** در قابِ گوشی است (`/app?preview=1` با داده‌ی
 * نمونه) و هر انتخاب از راهِ `postMessage` همان لحظه به آن می‌رسد —
 * قالب، طیفِ رنگ، لوگو، نام، پلن‌های واقعیِ خودِ نماینده، و حتی صفحه‌ی
 * ورود. پس چیزی جز آنچه مشتری می‌بیند نمی‌تواند نشان بدهد.
 *
 * پیش‌نمایش آزاد است؛ **ذخیره** پشتِ اشتراکِ پوسته (تصمیمِ مالک)، و
 * قفل در بکند است.
 */

/**
 * شِمای هر قالب — ساختار را نشان می‌دهد، با رنگِ پالتِ انتخابی.
 *
 * رنگ‌ها از متغیرهای خودِ پالت می‌آیند (`themeVars` روی همین عنصر)،
 * نه مقدارِ خام در JSX؛ شکلِ هر قالب در index.css زیر `.st-thumb.t-*`.
 * نسخه‌ی قبلی چهار نوارِ خالی بود در قابی بلند — نماینده نمی‌فهمید
 * فرقِ «مینیمال» و «نئون» چیست. حالا هر شِما سربرگ، کارتِ موجودی،
 * دو ردیفِ پلن با دکمه و نوارِ زبانه دارد، همان چیزهایی که قالب
 * عوضشان می‌کند.
 */
function TemplateThumb({ id, vars }) {
  return (
    <div className={`st-thumb t-${id}`} style={vars || undefined} aria-hidden="true">
      <div className="st-thumb-top">
        <span className="lg" />
        <span className="tx"><i /><i /></span>
      </div>
      <div className="st-thumb-body">
        <div className="bal"><i /><b /><i /></div>
        {[0, 1].map((k) => (
          <div key={k} className="row">
            <span className="tx"><i /><i /></span>
            <span className="btn" />
          </div>
        ))}
      </div>
      <div className="st-thumb-tabs">
        {[0, 1, 2, 3].map((k) => <span key={k} className={k ? "" : "on"} />)}
      </div>
    </div>
  );
}

/**
 * برش و زومِ لوگو پیش از آپلود.
 *
 * عکسِ هر اندازه‌ای می‌آید و مربع ذخیره می‌شود؛ بدونِ این، لوگوی
 * مستطیلی در قابِ گرد نصفه می‌شد و نماینده نمی‌فهمید چرا. خروجی ۵۱۲
 * پیکسل PNG (برای شفافیت)؛ اگر از سقفِ ۵۱۲ کیلوبایت بیشتر شد، WebP.
 */
function LogoCropper({ file, shape, onCancel, onDone }) {
  const VIEW = 260;
  const [img, setImg] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [off, setOff] = useState({ x: 0, y: 0 });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const drag = useRef(null);

  useEffect(() => {
    const url = URL.createObjectURL(file);
    const im = new Image();
    im.onload = () => setImg(im);
    im.onerror = () => setErr("این فایل تصویر نیست یا خراب است");
    im.src = url;
    return () => URL.revokeObjectURL(url);
  }, [file]);

  // اندازه‌ی «پوشاندن»: کوچک‌ترین ضلع قاب را پر می‌کند
  const base = img ? VIEW / Math.min(img.width, img.height) : 1;
  const w = img ? img.width * base * zoom : 0;
  const h = img ? img.height * base * zoom : 0;
  const clamp = (o) => ({
    x: Math.min(0, Math.max(VIEW - w, o.x)),
    y: Math.min(0, Math.max(VIEW - h, o.y)),
  });
  useEffect(() => {
    if (img) setOff((o) => clamp(o.x === 0 && o.y === 0 ? { x: (VIEW - w) / 2, y: (VIEW - h) / 2 } : o));
  }, [img, zoom]);   // eslint-disable-line react-hooks/exhaustive-deps

  const down = (e) => { drag.current = { x: e.clientX - off.x, y: e.clientY - off.y }; e.currentTarget.setPointerCapture?.(e.pointerId); };
  const move = (e) => { if (drag.current) setOff(clamp({ x: e.clientX - drag.current.x, y: e.clientY - drag.current.y })); };
  const up = () => { drag.current = null; };

  const save = async () => {
    if (!img) return;
    setBusy(true); setErr("");
    try {
      const OUT = 512, k = OUT / VIEW;
      const cv = document.createElement("canvas");
      cv.width = OUT; cv.height = OUT;
      const g = cv.getContext("2d");
      g.imageSmoothingQuality = "high";
      g.drawImage(img, off.x * k, off.y * k, w * k, h * k);
      let data = cv.toDataURL("image/png");
      if (data.length * 0.75 > 480 * 1024) data = cv.toDataURL("image/webp", 0.92);
      if (data.length * 0.75 > 500 * 1024) data = cv.toDataURL("image/jpeg", 0.9);
      await onDone(data);
    } catch (e) { setErr(e.message || "ذخیره نشد"); }
    finally { setBusy(false); }
  };

  const round = shape === "circle" ? "50%" : shape === "square" ? "10%" : "28%";
  return (
    <Frame onClose={onCancel} width={340}>
      <div className="text-[14px] font-semibold text-white mb-3">برش و اندازه‌ی لوگو</div>
      <div onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}
        style={{ width: VIEW, height: VIEW, margin: "0 auto", position: "relative",
                 overflow: "hidden", borderRadius: 14, cursor: "grab", touchAction: "none",
                 background: "var(--surface-3)" }}>
        {img && (
          <img src={img.src} alt="" draggable={false}
            style={{ position: "absolute", left: off.x, top: off.y, width: w, height: h,
                     maxWidth: "none", userSelect: "none", pointerEvents: "none" }} />
        )}
        {/* قابِ همان شکلی که انتخاب شده — بیرونش تیره است */}
        <div style={{ position: "absolute", inset: 14, borderRadius: round,
                      boxShadow: "0 0 0 999px var(--scrim-3)",
                      border: "2px solid var(--hair-4)", pointerEvents: "none" }} />
      </div>
      <label className="flex items-center gap-3 mt-4 text-[12px]" style={{ color: "var(--muted)" }}>
        بزرگ‌نمایی
        <input type="range" min="1" max="4" step="0.01" value={zoom}
          onChange={(e) => setZoom(Number(e.target.value))} className="flex-1" />
      </label>
      <p className="text-[11.5px] mt-2" style={{ color: "var(--muted)" }}>
        بکشید تا جابه‌جا شود.
      </p>
      {err && <p className="text-[12.5px] mt-2" style={{ color: "var(--danger)" }}>{err}</p>}
      <div className="flex gap-2 mt-4">
        <button onClick={onCancel} className="fx-btn-g flex-1 py-2 text-[13px]">انصراف</button>
        <button onClick={save} disabled={!img || busy}
          className="fx-btn flex-1 py-2 text-[13px] flex items-center justify-center gap-1.5">
          {busy && <Loader2 size={13} className="animate-spin" />} ذخیره‌ی لوگو
        </button>
      </div>
    </Frame>
  );
}

/** دکمه‌های کنارِ هم برای انتخابِ یکی از چند گزینه. */
/** یک مرحله از استودیو — شماره، عنوان، و آنچه همین حالا انتخاب شده. */
function Step({ n, title, hint, aside, children }) {
  return (
    <section className="nx-tile st-step">
      <header className="st-step-head">
        <span className="st-step-n">{faNum(n)}</span>
        <div className="min-w-0 flex-1">
          <h3>{title}</h3>
          {hint && <p>{hint}</p>}
        </div>
        {aside}
      </header>
      {children}
    </section>
  );
}

/** دکمه‌ی انتخاب با نشانِ تیک — یک شکل برای قالب، پالت، قاب و زمینه. */
/*
 * نمونه‌ی کوچکِ هر سبکِ صفحه‌ی ورود — با همان کلاس‌های اسپلشِ واقعی
 * (`nx-sp-*`)، تا نمونه و خودِ صفحه دو طراحیِ جدا نباشند.
 */
function SplashThumb({ id, vars }) {
  return (
    <span className={`st-spl sp-${id}`} style={vars}>
      <span className="st-spl-mark">
        {id === "ring" && <span className="nx-sp-ring" />}
        {id === "pulse" && <span className="nx-sp-pulse"><i /><i /><i /></span>}
        <i className="st-spl-logo" />
      </span>
      {id !== "logo" && <b className="st-spl-name" />}
      {id === "bar" && <span className="st-spl-bar"><i /></span>}
      {id === "dots" && <span className="nx-sp-dots"><i /><i /><i /></span>}
    </span>
  );
}

function Pick({ on, onClick, label, children, className = "", ...rest }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className={`st-pick ${on ? "on" : ""} ${className}`} {...rest}>
      {on && <span className="st-tick"><Check size={11} /></span>}
      {children}
      {label && <span className="st-pick-lbl">{label}</span>}
    </button>
  );
}

/**
 * مسیرهای استودیو. پرتال پیش‌فرض است؛ پنلِ مالک `ownerThemeApi` را می‌دهد.
 * همه‌ی درخواست‌های استودیو از همین شیء می‌گذرند، پس دو استودیو نداریم.
 */
export function portalThemeApi(token) {
  return {
    owner: false,
    get: () => api("/api/portal/theme", { token }),
    plans: () => api("/api/portal/bot-plans", { token }),
    save: (body) => api("/api/portal/theme", { token, method: "POST", body }),
    brand: (body) => api("/api/portal/brand", { token, method: "POST", body }),
    logo: (data) => api("/api/portal/logo", { token, method: "POST", body: { data } }),
    clearLogo: () => api("/api/portal/logo", { token, method: "DELETE" }),
    buy: () => api("/api/portal/theme/buy", { token, method: "POST" }),
  };
}

export function ownerThemeApi(password) {
  const call = async (path, opt = {}) => {
    const res = await fetch(`${API_URL}${path}`, {
      method: opt.method || "GET",
      headers: { "Content-Type": "application/json", "X-Admin-Password": password },
      ...(opt.body ? { body: JSON.stringify(opt.body) } : {}),
    });
    const j = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(errText(j.detail, "درخواست ناموفق بود"));
    return j;
  };
  return {
    owner: true,
    get: () => call("/api/admin/bot/mini-theme"),
    // پلن‌های واقعیِ خودِ مالک در پیش‌نمایش
    plans: () => call("/api/admin/bot/plans"),
    save: (body) => call("/api/admin/bot/mini-theme", { method: "POST", body }),
    brand: (body) => call("/api/admin/bot/brand", { method: "POST", body }),
    logo: (data) => call("/api/admin/bot/logo", { method: "POST", body: { data } }),
    clearLogo: () => call("/api/admin/bot/logo", { method: "DELETE" }),
    buy: async () => { throw new Error("فروشگاهِ مالک قفل ندارد"); },
  };
}

export function ThemeBox({ inline, token, onClose, onNote, themeApi }) {
  const A = React.useMemo(() => themeApi || portalThemeApi(token), [themeApi, token]);
  const [d, setD] = useState(null);
  const [tpl, setTpl] = useState("aurora");
  const [palette, setPalette] = useState("ocean");
  const [accent, setAccent] = useState("");
  const [ls, setLs] = useState(cleanLogoStyle({}));
  const [sp, setSp] = useState("bar");
  const [brand, setBrand] = useState("");
  const [plans, setPlans] = useState([]);
  const [scheme, setScheme] = useState("dark");
  const [crop, setCrop] = useState(null);
  const [logoV, setLogoV] = useState(0);
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const logoRef = useRef(null);
  const frameRef = useRef(null);
  const sideRef = useRef(null);

  const fromSaved = (j) => {
    setTpl(j.tpl || "aurora");
    setPalette(j.palette || "ocean");
    setAccent(j.accent || "");
    setLs(cleanLogoStyle(j.logoStyle));
    setSp(cleanSplash(j.splash));
  };

  const load = useCallback(async () => {
    try {
      const j = await A.get();
      setD(j);
      fromSaved(j);
      setBrand(j.brand || "");
    } catch (e) { setErr(e.message); }
    // پلن‌های واقعیِ خودش در پیش‌نمایش — نبودشان نمونه را نشان می‌دهد
    A.plans().then((j) => setPlans(j.plans || []))
      .catch(() => setPlans([]));
  }, [A]);
  useEffect(() => { load(); }, [load]);

  const logo = d?.logo ? `${d.logo}?v=${logoV}` : "";
  const theme = { tpl, palette, accent: palette === "custom" ? accent : "", logoStyle: ls, splash: sp };
  // متغیرهای پالتِ انتخابی — هر پیش‌نمایشِ این صفحه با همین رنگ می‌شود،
  // نه با آبیِ خودِ پرتال
  const vars = themeVars(theme, "dark") || undefined;

  // هر تغییر همان لحظه به مینی‌اپِ داخلِ قاب می‌رسد
  const send = useCallback(() => {
    try {
      frameRef.current?.contentWindow?.postMessage({
        type: "nx-preview", theme, brand: brand || d?.brand || "", logo, plans, scheme,
      }, window.location.origin);
    } catch { /* قاب هنوز بالا نیامده */ }
  }, [JSON.stringify(theme), brand, logo, plans, scheme, d?.brand]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { send(); }, [send]);
  useEffect(() => {
    const onMsg = (e) => {
      if (e.origin === window.location.origin && e.data?.type === "nx-ready") send();
    };
    window.addEventListener("message", onMsg);
    return () => window.removeEventListener("message", onMsg);
  }, [send]);
  const replaySplash = () => {
    try { frameRef.current?.contentWindow?.postMessage({ type: "nx-splash" }, window.location.origin); }
    catch { /* */ }
  };

  const saved = d && tpl === (d.tpl || "aurora") && palette === (d.palette || "ocean")
    && (palette !== "custom" || accent === (d.accent || ""))
    && JSON.stringify(ls) === JSON.stringify(cleanLogoStyle(d.logoStyle))
    && sp === cleanSplash(d.splash);

  const save = async () => {
    setBusy("save"); setErr("");
    try {
      await A.save({
        tpl, ...(palette === "custom" ? { accent } : {}), palette, logo_style: ls, splash: sp });
      onNote("پوسته ذخیره شد — مینی‌اپِ مشتری‌هایتان همین را نشان می‌دهد");
      load();
    } catch (e) { setErr(e.message); } finally { setBusy(""); }
  };

  // نام از همان مسیری می‌رود که «ربات و پرداخت» استفاده می‌کند —
  // نه مسیرِ دوم.
  const saveBrand = async () => {
    setBusy("brand"); setErr("");
    try {
      await A.brand({ brand: brand.trim() });
      onNote("نام فروشگاه ذخیره شد");
      load();
    } catch (e) { setErr(e.message); } finally { setBusy(""); }
  };

  const [drag, setDrag] = useState(false);
  const pickLogo = (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    takeLogo(f);
  };
  // از دکمه یا از کشیدن‌ورها کردن روی پیش‌نمایش — یک سنجش برای هر دو
  const takeLogo = (f) => {
    if (!f) return;
    if (!/^image\//.test(f.type || "")) { setErr("فقط تصویر"); return; }
    if (f.size > 12 * 1024 * 1024) { setErr("تصویر بیشتر از ۱۲ مگابایت است"); return; }
    setErr(""); setCrop(f);
  };
  const uploadLogo = async (data) => {
    await A.logo(data);
    setCrop(null); setLogoV(Date.now());
    onNote("لوگو ذخیره شد");
    await load();
  };
  const dropLogo = async () => {
    setBusy("logo"); setErr("");
    try { await A.clearLogo(); await load(); }
    catch (e2) { setErr(e2.message); } finally { setBusy(""); }
  };

  const buy = async () => {
    setBusy("buy"); setErr("");
    try {
      const j = await A.buy();
      onNote(`فعال شد — ${faNum(j.paid)} تومان از اعتبارتان کم شد`);
      load();
    } catch (e) { setErr(e.message); } finally { setBusy(""); }
  };

  const open = !!d?.open;
  const tplOf = MINI_TEMPLATES.find((t) => t.id === tpl);
  const palName = palette === "custom" ? "رنگِ دلخواه"
    : (MINI_PALETTES.find((p) => p.id === palette)?.fa || "");
  // تاریخ شمسی — «فعال تا 22-10-2026» تنها تاریخِ میلادیِ پرتال بود
  const left = d?.until ? Math.max(0, Math.ceil((Date.parse(d.until) - Date.now()) / 864e5)) : null;
  const name = brand.trim() || d?.brand || "";

  return (
    <Frame inline={inline} onClose={onClose} width={900}>
      <div className="nx-box-head flex items-center justify-between mb-3">
        <div className="text-[14px] font-semibold text-white">پوسته‌ی مینی‌اپِ شما</div>
        {!inline && (
          <button onClick={onClose} className="fx-ico-btn" style={{ width: 28, height: 28 }}
            aria-label="بستن"><X size={13} /></button>
        )}
      </div>

      {/* همان اشتباهِ پلن‌ها: خطا فقط داخلِ شاخه‌ی «رسید» نشان داده می‌شد */}
      {!d && err ? (
        <div className="text-[13px] py-3 flex items-start gap-1.5" style={{ color: "var(--danger)" }}>
          <AlertTriangle size={13} className="shrink-0 mt-0.5" />
          <span>پوسته خوانده نشد: {err}{" "}
            <button type="button" className="underline" onClick={() => { setErr(""); load(); }}>دوباره</button>
          </span>
        </div>
      ) : !d ? <SkeletonCards n={2} /> : (
        <div className="st-wrap">
          <div className="st-main">
            {/* سربرگ — فروشگاه با همان رنگی که انتخاب شده، و وضعیتِ اشتراک */}
            <section className="st-hero" style={vars}>
              <div className="st-hero-id">
                <ShopLogo src={logo} name={name} style={ls} size={56} />
                <div className="min-w-0">
                  <h2>{name || "فروشگاهِ شما"}</h2>
                  <p>{tplOf?.fa} · {palName}</p>
                </div>
              </div>
              <div className="st-hero-state">
                {open ? (
                  <>
                    <span className="st-badge t-ok"><Check size={12} />
                      {A.owner ? "فروشگاهِ اصلی — همیشه فعال" : "پوسته‌ی شخصی فعال است"}</span>
                    {!A.owner && d.until && (
                      <span className="st-until">
                        {left !== null && <b>{faNum(left)} روز</b>} مانده · تا {isoToJalaliLabel(d.until)}
                      </span>
                    )}
                    {/* قیمتِ افزونه برای نماینده است؛ مالک چیزی برای تمدید ندارد */}
                    {!A.owner && d.price > 0 && (
                      <button onClick={buy} disabled={busy === "buy"} className="st-ghost">
                        {busy === "buy" ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
                        تمدید {faNum(d.days)} روزه
                      </button>
                    )}
                  </>
                ) : d.blocked ? (
                  // مدیر بسته — خرید بازش نمی‌کند (بکند ۴۰۳)، پس دکمه‌ای هم نیست
                  <>
                    <span className="st-badge t-warn"><Lock size={12} /> مدیر این قابلیت را برای شما بسته است</span>
                    <span className="st-until">
                      پیش‌نمایش آزاد است، ولی مشتری‌ها پوسته‌ی پیش‌فرض را می‌بینند. برای بازشدن با مدیر هماهنگ کنید.
                    </span>
                  </>
                ) : (
                  <>
                    <span className="st-badge t-accent"><Sparkles size={12} /> پیش‌نمایش آزاد است</span>
                    <span className="st-until">
                      همه را امتحان کنید؛ برای اینکه مشتری‌ها هم ببینند، فعالش کنید.
                    </span>
                    <button onClick={buy} disabled={busy === "buy"} className="st-cta">
                      {busy === "buy" ? <Loader2 size={13} className="animate-spin" /> : <Palette size={13} />}
                      {faNum(d.price)} تومان · {faNum(d.days)} روز
                    </button>
                    <span className="st-fine">
                      {d.postpaid ? "به صورتحسابِ این دوره‌تان اضافه می‌شود"
                        : `از اعتبارتان کم می‌شود — موجودی: ${faNum(d.credit)} تومان`}
                    </span>
                  </>
                )}
              </div>
            </section>

            <Step n={1} title="قالب" hint={tplOf?.desc}>
              <div className="st-tpls">
                {MINI_TEMPLATES.map((t) => (
                  <Pick key={t.id} on={tpl === t.id} onClick={() => setTpl(t.id)}
                    label={t.fa} data-tpl={t.id} title={t.desc}>
                    <TemplateThumb id={t.id} vars={vars} />
                  </Pick>
                ))}
              </div>
            </Step>

            <Step n={2} title="طیفِ رنگ" hint="زمینه، سطح‌ها و رنگ‌های اصلی با هم عوض می‌شوند">
              <div className="st-pals">
                {MINI_PALETTES.map((p) => (
                  <Pick key={p.id} on={palette === p.id} onClick={() => setPalette(p.id)}
                    label={p.fa} data-pal={p.id}>
                    {/* رنگ از متغیرهای خودِ همان پالت — مقدارِ خام در JSX نیست */}
                    <span className="st-pal" style={themeVars({ palette: p.id }, "dark") || undefined}>
                      <i className="band" /><i className="chip" />
                    </span>
                  </Pick>
                ))}
                <Pick on={palette === "custom"} label="دلخواه" data-pal="custom"
                  onClick={() => { setPalette("custom"); if (!accent) setAccent("#7c5cff"); }}>
                  <span className="st-pal st-pal-any"><Palette size={16} /></span>
                </Pick>
              </div>

              {palette === "custom" && (
                <div className="st-custom">
                  <label className="st-wheel" style={vars}>
                    <input type="color" value={accent || "#7c5cff"}
                      onChange={(e) => setAccent(e.target.value)} aria-label="رنگِ دلخواه" />
                  </label>
                  <div className="st-custom-body">
                    <div className="flex items-center gap-2 flex-wrap">
                      <input value={accent} dir="ltr" placeholder="#7c5cff" maxLength={7}
                        onChange={(e) => setAccent(e.target.value.trim())}
                        className="fx-input text-[13px]" style={{ fontFamily: "var(--mono)", width: 110 }} />
                      <div className="st-dots">
                        {ACCENTS.map((c) => (
                          <button key={c} type="button" onClick={() => setAccent(c)} aria-label={`رنگ ${c}`}
                            className={accent === c ? "on" : ""} style={{ background: c }} />
                        ))}
                      </div>
                    </div>
                    {/* آنچه از این یک رنگ ساخته می‌شود — تا بداند چرا زمینه عوض شد */}
                    <div className="st-derived" style={vars}>
                      <span><i className="a" />رنگِ اصلی</span>
                      <span><i className="c" />رنگِ دوم</span>
                      <span><i className="b" />زمینه</span>
                    </div>
                  </div>
                </div>
              )}
            </Step>

            <Step n={3} title="لوگو و نام"
              hint={d.logo ? "قاب و زمینه‌ی لوگو هم جزوِ پوسته‌اند"
                : "بدونِ لوگو، نشانی از حرفِ اولِ نامِ فروشگاه با رنگِ پالت ساخته می‌شود"}>
              <div className="st-logo">
                {/* همان صفحه‌ی ورودِ مشتری، کوچک: لوگو و نام روی زمینه‌ی پالت */}
                <div className={`st-stage sp-${sp} ${drag ? "drag" : ""}`} style={vars}
                  onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
                  onDragLeave={() => setDrag(false)}
                  onDrop={(e) => { e.preventDefault(); setDrag(false); takeLogo(e.dataTransfer?.files?.[0]); }}>
                  {/* با سبکِ صفحه‌ی ورودِ انتخابی (گامِ ۴) — پیش‌تر همیشه
                      «نوار» بود و انتخابِ حلقه این‌جا دیده نمی‌شد */}
                  <span className="nx-shop-mark">
                    {sp === "ring" && <span className="nx-sp-ring" />}
                    {sp === "pulse" && <span className="nx-sp-pulse"><i /><i /><i /></span>}
                    <ShopLogo src={logo} name={name} style={ls} size={sp === "logo" ? 96 : 76} />
                  </span>
                  {sp !== "logo" && <b>{name || "نام فروشگاه"}</b>}
                  {sp === "bar" && <span className="bar"><i /></span>}
                  {sp === "dots" && <span className="nx-sp-dots"><i /><i /><i /></span>}
                  {drag && <span className="st-drop"><Camera size={18} /> رها کنید</span>}
                </div>

                <div className="st-logo-ctl">
                  <input ref={logoRef} type="file" className="hidden"
                    accept="image/png,image/jpeg,image/webp" onChange={pickLogo} />
                  {/* پیش‌تر دکمه‌ی آپلود بی‌برچسب بالای ستون می‌نشست و از بقیه‌ی
                      ردیف‌ها جدا بود؛ حالا یک ردیف مثلِ «قاب» و «زمینه»، با
                      آنچه پذیرفته می‌شود — تا خطای «فقط تصویر» اولین راهنما نباشد */}
                  <div className="st-field">
                    <span>لوگو</span>
                    <div className="st-logo-src">
                      <button onClick={() => logoRef.current?.click()}
                        className="fx-btn px-3.5 py-2 text-[12.5px] flex items-center gap-1.5">
                        <Camera size={13} /> {d.logo ? "عوض‌کردن و برش" : "آپلودِ لوگو"}
                      </button>
                      {d.logo && (
                        <button onClick={dropLogo} disabled={busy === "logo"}
                          className="fx-btn-g px-3 py-2 text-[12.5px] flex items-center gap-1.5">
                          {busy === "logo" ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />} حذف
                        </button>
                      )}
                      <small>تصویرِ PNG یا JPG یا WebP تا ۱۲ مگابایت — بعد از انتخاب برشش می‌زنید. می‌توانید روی پیش‌نمایش هم رهایش کنید.</small>
                    </div>
                  </div>

                  <div className="st-field">
                    <span>قاب</span>
                    <div className="st-mini-picks">
                      {LOGO_SHAPES.map((o) => (
                        <Pick key={o.id} on={ls.shape === o.id} label={o.fa}
                          onClick={() => setLs({ ...ls, shape: o.id })}>
                          <i className={`st-shape s-${o.id}`} />
                        </Pick>
                      ))}
                    </div>
                  </div>
                  <div className="st-field">
                    <span>زمینه</span>
                    <div className="st-mini-picks" style={vars}>
                      {LOGO_BGS.map((o) => (
                        <Pick key={o.id} on={ls.bg === o.id} label={o.fa}
                          onClick={() => setLs({ ...ls, bg: o.id })}>
                          <i className={`st-bgsw b-${o.id}`} />
                        </Pick>
                      ))}
                    </div>
                  </div>
                  <div className="st-field">
                    <span>فاصله</span>
                    <div className="st-range">
                      <input type="range" min="0" max="24" value={ls.pad} aria-label="فاصله‌ی لوگو از قاب"
                        onChange={(e) => setLs({ ...ls, pad: Number(e.target.value) })} />
                      {/* صفرِ فارسی یک نقطه است — «۰» کنارِ لغزنده شبیهِ لکه بود */}
                      <b>{ls.pad ? faNum(ls.pad) : "بی‌فاصله"}</b>
                    </div>
                  </div>

                  <div className="st-field">
                    <span>نام</span>
                    <div className="flex items-center gap-2 min-w-0">
                      <input value={brand} maxLength={40} placeholder="مثلاً: حسین وی‌پی‌ان"
                        onChange={(e) => setBrand(e.target.value)}
                        className="fx-input text-[13px] flex-1 min-w-0" />
                      <button onClick={saveBrand}
                        disabled={busy === "brand" || !brand.trim() || brand.trim() === (d.brand || "")}
                        className="fx-btn-g px-3 py-2 text-[12.5px] shrink-0">
                        {busy === "brand" ? <Loader2 size={12} className="animate-spin" /> : "ذخیره‌ی نام"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </Step>

            <Step n={4} title="صفحه‌ی ورود"
              hint={MINI_SPLASHES.find((x) => x.id === sp)?.desc}>
              <div className="st-spls">
                {MINI_SPLASHES.map((x) => (
                  // انتخاب همان لحظه در گوشیِ کناری پخش می‌شود — نمونه‌ی
                  // کوچک حرکت را نشان می‌دهد، ولی حسِ واقعی فقط تمام‌صفحه است.
                  // مکث تا پوسته‌ی تازه اول به قاب برسد.
                  <Pick key={x.id} on={sp === x.id} label={x.fa} data-splash={x.id}
                    onClick={() => { setSp(x.id); setTimeout(replaySplash, 160); }}>
                    <SplashThumb id={x.id} vars={vars} />
                  </Pick>
                ))}
              </div>
            </Step>

            {err && (
              <p className="text-[12.5px] flex items-start gap-1.5" style={{ color: "var(--danger)" }}>
                <AlertTriangle size={13} className="shrink-0 mt-0.5" />{err}
              </p>
            )}

            {/* نوارِ ذخیره — همیشه در دسترس، و می‌گوید چیزی مانده یا نه */}
            <div className={`st-savebar ${saved ? "" : "dirty"}`}>
              <span className="st-save-state">
                <i />
                {/* روی گوشی جمله‌ی کامل چهار خط می‌شد و نصفِ صفحه را می‌گرفت */}
                <span className="long">{!open ? "پیش‌نمایش — برای ذخیره، پوسته‌ی شخصی را فعال کنید"
                  : saved ? "همه‌چیز ذخیره شده" : "تغییراتِ ذخیره‌نشده"}</span>
                <span className="short">{!open ? "فقط پیش‌نمایش" : saved ? "ذخیره شده" : "ذخیره‌نشده"}</span>
              </span>
              <button type="button" className="st-ghost st-peek"
                onClick={() => sideRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })}
                aria-label="پیش‌نمایش">
                <Eye size={12} /> <span className="st-hide-sm">پیش‌نمایش</span>
              </button>
              {open && !saved && (
                <button onClick={() => fromSaved(d)} aria-label="برگرداندن"
                  className="fx-btn-g px-3 py-2 text-[12.5px] flex items-center gap-1.5">
                  <RotateCcw size={12} /> <span className="st-hide-sm">برگرداندن</span>
                </button>
              )}
              {open ? (
                <button onClick={save} disabled={saved || busy === "save"}
                  className="fx-btn px-5 py-2 text-[13px] flex items-center gap-1.5">
                  {busy === "save" ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                  ذخیره‌ی پوسته
                </button>
              ) : (
                <button onClick={buy} disabled={busy === "buy"}
                  className="fx-btn px-4 py-2 text-[13px] flex items-center gap-1.5">
                  <Palette size={13} /> فعال‌سازی
                </button>
              )}
            </div>
          </div>

          {/* خودِ مینی‌اپ، در قابِ گوشی — نه ماکت */}
          <aside className="st-side" ref={sideRef}>
            <div className="st-live"><i /> پیش‌نمایشِ زنده</div>
            <div className="nx-phone">
              <iframe ref={frameRef} src="/app?preview=1" title="پیش‌نمایشِ مینی‌اپ"
                onLoad={send} />
            </div>
            <div className="st-phone-ctl">
              <button onClick={replaySplash} className="st-ghost">
                <Play size={12} /> صفحه‌ی ورود
              </button>
              <div className="st-seg" role="group" aria-label="پوسته‌ی تلگرام">
                <button className={scheme === "dark" ? "on" : ""} onClick={() => setScheme("dark")}>
                  <Moon size={12} /> تیره
                </button>
                <button className={scheme === "light" ? "on" : ""} onClick={() => setScheme("light")}>
                  <Sun size={12} /> روشن
                </button>
              </div>
            </div>
            <p className="st-fine text-center">داده‌ی نمونه، با پلن‌های خودتان</p>
          </aside>
        </div>
      )}

      {crop && (
        <LogoCropper file={crop} shape={ls.shape} onCancel={() => setCrop(null)} onDone={uploadLogo} />
      )}
    </Frame>
  );
}

