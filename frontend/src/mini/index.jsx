/**
 * مینی‌اپ تلگرام — سمت مشتری.
 *
 * برگه‌اش: docs/specs/2026-09-16-miniapp.md
 *
 * چرا اپ سومِ جدا، مثل پنل نماینده:
 *
 *   این‌جا **مشتری** است، نه مدیر و نه نماینده. اگر داخل همان App
 *   می‌نشست، یک import اشتباه کافی بود تا چیزی از پنل مدیر برای
 *   مشتری رندر شود. این‌جا اصلاً به آن کد دسترسی ندارد.
 *
 * و یک قاعده که نباید شکسته شود: **هیچ پولی این‌جا حساب نمی‌شود.**
 * قیمت از API می‌آید و خرید از `/api/mini/buy` رد می‌شود، که خودش
 * `handlers.wallet_purchase` را صدا می‌زند — همان هسته‌ای که خرید از
 * داخل ربات هم از آن می‌گذرد. یک نسخه، دو در. حسابداریِ نماینده هم
 * اصلاً این‌جا نیست؛ قرارِ خودِ مالک.
 *
 * ── چیدمان ──
 *
 * سه صفحه با نوار پایین، نه تب‌های بالا: انگشتِ شست روی گوشی به
 * پایینِ صفحه می‌رسد، نه به بالایش. همان الگویی که مالک نمونه‌اش را
 * فرستاد و در هر اپِ موبایلی دیده‌ایم.
 */
import React, { useState, useEffect, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
import {
  AlertTriangle, ArrowLeft, Camera, Check, ChevronLeft, Clock, Copy,
  CreditCard, ExternalLink, Gift, Home, Image as ImageIcon, Layers, Link2,
  Loader2, MessageCircle, Package, Phone, QrCode, RefreshCw, Send, Shield,
  ShoppingBag, ShoppingCart, Trash2, User, Wallet, Zap,
} from "lucide-react";

import { API_URL } from "../lib/constants";
import { errText, faDate, faNum, toFaDigits as faDigits } from "../lib/format";
import { Avatar, EmptyState, Skeleton } from "../ui/index";

/* آیا این آدرس مینی‌اپ است؟ — نام باید در دامنه‌ی خودِ ماژول هم
   باشد، نه فقط عبور کند. */
import { isMini } from "../lib/route.js";
export { isMini };

/**
 * پلِ تلگرام.
 *
 * اگر مینی‌اپ بیرون از تلگرام باز شود (مثلاً خودِ مالک آدرس را در
 * مرورگر بزند) این شیء نیست. آن حالت باید پیام روشن بدهد، نه خطای
 * جاوااسکریپت روی صفحه‌ی سفید.
 */
const tg = () => (typeof window !== "undefined" ? window.Telegram?.WebApp : null);

/**
 * لرزشِ کوتاه — همان بازخوردی که بقیه‌ی اپ‌های تلگرام می‌دهند.
 *
 * روی دسکتاپ یا هر جایی که پشتیبانی نشود، بی‌صدا هیچ کاری نمی‌کند.
 * هیچ‌وقت نباید باعث خطا شود: این یک راحتی است، نه بخشی از کار.
 */
function buzz(kind = "light") {
  try {
    const h = tg()?.HapticFeedback;
    if (!h) return;
    if (kind === "ok") h.notificationOccurred?.("success");
    else if (kind === "err") h.notificationOccurred?.("error");
    else h.impactOccurred?.(kind);
  } catch { /* بی‌صدا — لرزش اختیاری است */ }
}

/**
 * هماهنگی با تلگرام — ولی فقط تا جایی که باید.
 *
 * تلگرام تصمیم می‌گیرد **روشن یا تیره**؛ رنگ را نکسورا تصمیم
 * می‌گیرد. قبلاً `--bg` و همه‌ی سطح‌ها مستقیم از `themeParams`
 * برداشته می‌شدند و نتیجه‌اش خاکستریِ خنثیِ خودِ تلگرام بود — یعنی
 * مینی‌اپ ما دقیقاً شبیه هر مینی‌اپ دیگری می‌شد و هیچ‌چیز از برند
 * در آن نمی‌ماند.
 *
 * این‌جا فقط یک صفت روی ریشه گذاشته می‌شود؛ خودِ رنگ‌ها در
 * `index.css` زیر `[data-mn-scheme="light"]` تعریف شده‌اند — رنگ
 * جای CSS است، نه داخل JSX.
 *
 * تنها چیزی که به تلگرام *داده* می‌شود رنگِ نوار بالا و پس‌زمینه‌ی
 * پنجره است، تا لبه‌ی اپ با محیطش یکی شود.
 */
/**
 * ناحیه‌ی امن — از خودِ تلگرام، نه از `env()`.
 *
 * `env(safe-area-inset-*)` را مرورگر از سیستم‌عامل می‌گیرد، ولی
 * داخل WebViewِ تلگرام معمولاً صفر برمی‌گردد — و مهم‌تر، اصلاً
 * چیزی از نوارِ خودِ تلگرام نمی‌داند. آن نوار روی محتوای ما
 * می‌نشیند و `env()` هرگز خبردار نمی‌شود.
 *
 * تلگرام دو چیز می‌دهد:
 *   safeAreaInset         ناچ و گوشه‌های دستگاه
 *   contentSafeAreaInset  نوار و دکمه‌های خودِ تلگرام
 *
 * جمعشان می‌شود فضایی که محتوای ما نباید زیرش برود. اگر هیچ‌کدام
 * نبود (نسخه‌ی قدیمی‌تر)، خاصیت برداشته می‌شود و CSS به `env()`
 * برمی‌گردد.
 */
function syncSafeArea() {
  const w = tg();
  const r = document.documentElement.style;
  const sa = w?.safeAreaInset || {};
  const csa = w?.contentSafeAreaInset || {};
  const put = (k, v) => {
    const n = Number(v) || 0;
    if (n > 0) r.setProperty(k, n + "px");
    else r.removeProperty(k);     // برگشت به env() در CSS
  };
  put("--mn-sa-top", (Number(sa.top) || 0) + (Number(csa.top) || 0));
  put("--mn-sa-bottom", (Number(sa.bottom) || 0) + (Number(csa.bottom) || 0));
  put("--mn-sa-start", Math.max(Number(sa.left) || 0, Number(csa.left) || 0));
  put("--mn-sa-end", Math.max(Number(sa.right) || 0, Number(csa.right) || 0));
}

function syncTheme() {
  const w = tg();
  const dark = (w?.colorScheme || "dark") === "dark";
  document.documentElement.dataset.mnScheme = dark ? "dark" : "light";
  try {
    const css = getComputedStyle(document.documentElement);
    const bg = css.getPropertyValue("--bg").trim() || "#070A12";
    w?.setHeaderColor?.(bg);
    w?.setBackgroundColor?.(bg);
  } catch { /* نسخه‌ی قدیمی‌تر این متدها را ندارد */ }
  return true;
}

async function api(path, opt = {}) {
  const init = tg()?.initData || "";
  const headers = { "X-Telegram-Init-Data": init };
  if (opt.body) headers["Content-Type"] = "application/json";
  const res = await fetch(`${API_URL}${path}`, {
    method: opt.method || "GET",
    headers,
    body: opt.body ? JSON.stringify(opt.body) : undefined,
  });
  const j = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(errText(j.detail, "درخواست ناموفق بود"));
  return j;
}

/**
 * حجم با واحدِ درست.
 *
 * چرا نه همیشه گیگابایت: اشتراکِ تستِ ۵۰ مگابایتی با گیگ می‌شود
 * «۰٫۰ گیگ» — که یعنی هیچ. مشتری باید عددِ خودش را ببیند.
 */
function vol(bytes) {
  const b = Number(bytes) || 0;
  if (!b) return { n: "۰", u: "مگابایت" };
  const mb = b / (1024 ** 2);
  if (mb < 1024) return { n: faNum(mb < 10 ? mb.toFixed(1) : Math.round(mb)), u: "مگابایت" };
  const gb = mb / 1024;
  return { n: faNum(gb < 10 ? gb.toFixed(1) : Math.round(gb)), u: "گیگابایت" };
}
const volText = (b) => { const v = vol(b); return `${v.n} ${v.u}`; };

/* ═══════════════ اجزای کوچک ═══════════════ */

function Bar({ pct }) {
  if (pct === null || pct === undefined) return null;
  const col = pct >= 90 ? "var(--danger)" : pct >= 75 ? "var(--warn)" : "var(--ok)";
  return (
    <div className="fx-usebar" title={`${faNum(pct)}٪ مصرف شده`}>
      <i style={{ width: `${Math.min(100, Math.max(2, pct))}%`, background: col }} />
    </div>
  );
}

function Tag({ tone, children }) {
  return <span className={`mn-tag ${tone || ""}`}>{children}</span>;
}

/** خطِ وضعیت: منقضی / تست / چند ماهه */
function SubTags({ s }) {
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      {s.months ? <Tag>{faNum(s.months)} ماهه</Tag> : null}
      {s.isTrial ? <Tag tone="warn">تست</Tag> : null}
      {s.active
        ? <Tag tone="ok"><i className="mn-dot" /> فعال</Tag>
        : <Tag tone="bad"><i className="mn-dot" /> منقضی</Tag>}
    </div>
  );
}

/* ═══════════════ صفحه‌ی خانه ═══════════════ */

function Balance({ me }) {
  const [copied, setCopied] = useState(false);
  const copyId = () => {
    try { navigator.clipboard?.writeText(String(me?.tgId || "")); } catch { /* بی‌صدا */ }
    setCopied(true); buzz("ok");
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div className="mn-card-bal">
      <div className="mn-bal-top">
        <span className="mn-bal-label">موجودی</span>
        <span className="mn-chip" aria-hidden="true" />
      </div>
      <div className="mn-bal-amount">
        <b>{faNum(me?.balance ?? 0)}</b>
        <span>تومان</span>
      </div>
      <div className="mn-bal-foot">
        {/* شناسه همان چیزی است که موقع پشتیبانی باید بگوید —
            پس باید بشود یک‌ضرب کپی‌اش کرد */}
        <button onClick={copyId} className="mn-bal-cell" title="کپی شناسه">
          <span>شناسه</span>
          {/* شناسه عدد نیست، شناسه است: `faNum` روی آن جداکننده‌ی
              هزارگان می‌گذارد و «۱٬۲۷۸٬۱۰۹٬۷۸۷» چیزی است که
              مشتری نمی‌تواند به پشتیبانی بگوید. */}
          {/* `dir="ltr"` فقط وقتی که واقعاً شناسه است — «کپی شد»
              فارسی است و داخل یک جعبه‌ی چپ‌به‌راست جابه‌جا می‌شود */}
          {copied
            ? <b>کپی شد</b>
            : <b dir="ltr">{me?.tgId ? faDigits(me.tgId) : "—"}</b>}
        </button>
        <div className="mn-bal-cell end">
          <span>صاحب حساب</span>
          <b>{me?.name || "—"}</b>
        </div>
      </div>
    </div>
  );
}

function SubRow({ s, onOpen }) {
  return (
    <button className="mn-row" onClick={() => { buzz("light"); onOpen(s); }}>
      <span className={`mn-row-ico ${s.active ? "ok" : "bad"}`}>
        <Layers size={16} />
      </span>
      <span className="mn-row-body">
        <span className="mn-row-title">{s.plan || s.email || "اشتراک"}</span>
        <span className="mn-row-sub">{s.email}</span>
        <SubTags s={s} />
        <span className="mn-row-vol">{volText(s.totalBytes)}</span>
      </span>
      <ChevronLeft size={16} className="mn-row-arrow" />
    </button>
  );
}

function HomeView({ me, subs, onOpen, onBuy, onAll }) {
  const recent = (subs || []).slice(0, 3);
  return (
    <>
      <Balance me={me} />

      <div className="mn-sec">
        <div className="mn-sec-head">
          <div>
            <h2>اشتراک‌های اخیر</h2>
            <p>برای جزئیات و مدیریت، روی هر مورد بزنید</p>
          </div>
          {/* «همه» یعنی فهرستِ اشتراک‌ها، نه صفحه‌ی خرید.
              تا امروز `onBuy` بود و کاربر را می‌برد جایی که نخواسته. */}
          {(subs || []).length > 3 && (
            <button className="mn-link" onClick={onAll}>
              همه <ChevronLeft size={13} />
            </button>
          )}
        </div>

        {recent.length === 0 ? (
          <EmptyState icon={Package} text="هنوز اشتراکی ندارید"
            hint="با اولین خرید، اشتراکتان همین‌جا با حجم و تاریخ انقضا نشان داده می‌شود."
            action={<button onClick={onBuy} className="fx-btn px-4 py-2 text-[13px]">
              دیدن پلن‌ها</button>} />
        ) : recent.map((s) => <SubRow key={s.id} s={s} onOpen={onOpen} />)}
      </div>
    </>
  );
}

/* ═══════════════ جزئیات یک اشتراک ═══════════════ */

function Cell({ label, value, unit, tone }) {
  return (
    <div className="mn-cell">
      <span className="mn-cell-label">{label}</span>
      <b className="mn-cell-value" style={tone ? { color: tone } : undefined}>
        {value}{unit && <em>{unit}</em>}
      </b>
    </div>
  );
}

function SubDetail({ s, onBack, onRenew }) {
  const [copied, setCopied] = useState("");
  const hit = (what, text) => {
    try { navigator.clipboard?.writeText(text || ""); } catch { /* بی‌صدا */ }
    setCopied(what); buzz("ok");
    setTimeout(() => setCopied(""), 1600);
  };
  const open = () => {
    buzz("light");
    const w = tg();
    if (s.subUrl && w?.openLink) w.openLink(s.subUrl);
    else if (s.subUrl) window.open(s.subUrl, "_blank", "noopener");
  };
  const used = vol(s.usedBytes);
  const total = vol(s.totalBytes);
  const remain = s.remainBytes === null || s.remainBytes === undefined
    ? null : vol(s.remainBytes);

  return (
    <>
      <button className="mn-back" onClick={() => { buzz("light"); onBack(); }}>
        <ArrowLeft size={14} className="scale-x-[-1]" /> بازگشت
      </button>

      <div className="mn-hero">
        <h2>{s.plan || s.email || "اشتراک"}</h2>
        <p dir="ltr">{s.email}</p>
        <SubTags s={s} />
        <div className="mt-3"><Bar pct={s.usagePct} /></div>
      </div>

      <div className="mn-cells">
        <Cell label="مصرف" value={used.n} unit={used.u} />
        <Cell label="کل حجم" value={s.totalBytes ? total.n : "نامحدود"}
          unit={s.totalBytes ? total.u : null} />
        <Cell label="باقی‌مانده" value={remain ? remain.n : "نامحدود"}
          unit={remain ? remain.u : null}
          tone={s.usagePct >= 90 ? "var(--danger)" : undefined} />
        <Cell label="انقضا" value={faDate(s.expiryJalali)}
          tone={s.daysLeft !== null && s.daysLeft <= 0 ? "var(--danger)"
            : s.daysLeft !== null && s.daysLeft <= 7 ? "var(--warn)" : undefined} />
      </div>

      {s.daysLeft !== null && s.daysLeft !== undefined && (
        <div className={`mn-note ${s.daysLeft <= 0 ? "bad" : s.daysLeft <= 7 ? "warn" : ""}`}>
          {s.daysLeft > 0
            ? <>‏{faNum(s.daysLeft)} روز تا پایان اشتراک باقی مانده.</>
            : <>این اشتراک منقضی شده — تا تمدید نشود وصل نمی‌شوید.</>}
        </div>
      )}

      {/* تمدید.

          تا امروز فقط یک جمله بود: «از ربات تمدید کنید» — یعنی
          کاربر باید خودش ربات را باز می‌کرد، منو را می‌گشت، و بین
          چند اشتراک همان یکی را پیدا می‌کرد. حالا دکمه مستقیم به
          همین اشتراک در ربات می‌رود. */}
      <button className="mn-renew" onClick={() => onRenew?.(s)}>
        <RefreshCw size={15} />
        {s.daysLeft !== null && s.daysLeft <= 0 ? "تمدید و فعال‌سازی" : "تمدید اشتراک"}
      </button>

      <div className="mn-acts">
        <button className="mn-act" onClick={() => hit("sub", s.subUrl)}>
          {copied === "sub"
            ? <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
                stroke="var(--ok)" strokeWidth="2.6" strokeLinecap="round"
                strokeLinejoin="round"><path className="fx-chk" d="m4 12 5.5 5.5L20 7" /></svg>
            : <Copy size={15} />}
          {copied === "sub" ? "کپی شد" : "کپی لینک"}
        </button>
        <button className="mn-act" onClick={open} disabled={!s.subUrl}>
          <ExternalLink size={15} /> باز کردن
        </button>
      </div>

      <div className="mn-hint">
        تعویض لینک و حذف اشتراک از منوی خودِ ربات انجام می‌شوند.
      </div>
    </>
  );
}

/* ═══════════════ خرید ═══════════════ */

function PlanCard({ p, onBuy }) {
  return (
    <div className="mn-plan">
      <span className="mn-plan-strip" aria-hidden="true"><Shield size={15} /></span>
      <div className="mn-plan-body">
        <div className="mn-plan-title">
          {p.gb === 0 ? "نامحدود" : `${faNum(p.gb)} گیگابایت`}
          {" / "}{faNum(p.days)} روز
          {p.isTrial && <Tag tone="ok">رایگان</Tag>}
        </div>
        {p.desc && <div className="mn-plan-desc">{p.desc}</div>}
        <div className="mn-plan-meta">
          {p.devices > 0 ? `${faNum(p.devices)} دستگاه` : "بدون سقف دستگاه"}
        </div>
        <div className="mn-plan-price">
          {p.price ? faNum(p.price) : "۰"}<em>تومان</em>
        </div>
      </div>
      <button className="mn-plan-btn" onClick={() => onBuy(p)}>خرید</button>
    </div>
  );
}

function BuyView({ plans, onBuy }) {
  // گروه‌بندی بر اساس مدت — فهرستِ بلندِ بی‌سر، چیزی به کسی
  // نمی‌گوید؛ «۱ ماهه» و «۳ ماهه» تصمیم را ساده می‌کنند
  const groups = {};
  (plans || []).forEach((p) => {
    const m = Math.max(1, Math.round((Number(p.days) || 30) / 30));
    (groups[m] = groups[m] || []).push(p);
  });
  const keys = Object.keys(groups).map(Number).sort((a, b) => a - b);

  if (!keys.length) {
    return <EmptyState icon={ShoppingCart} text="فعلاً پلنی برای فروش نیست"
      hint="به‌زودی پلن‌ها اضافه می‌شوند. از پشتیبانی هم می‌توانید بپرسید." />;
  }

  return (
    <>
      <div className="mn-sec-head mb-1">
        <div>
          <h2>خرید سرویس</h2>
          <p>پلن مناسب خودتان را انتخاب کنید</p>
        </div>
      </div>
      {keys.map((m) => (
        <div key={m} className="mn-group">
          <div className="mn-group-head">
            <Zap size={14} /> {faNum(m)} ماهه
            <span>{faNum(groups[m].length)} گزینه</span>
          </div>
          {groups[m].map((p) => <PlanCard key={p.id} p={p} onBuy={onBuy} />)}
        </div>
      ))}
    </>
  );
}

/**
 * سفارش‌هایی که هنوز تکلیفشان روشن نیست.
 *
 * چرا لازم است: مشتری رسید می‌فرستد و بعد… هیچ. بدون این، تنها راهِ
 * فهمیدنِ اینکه رسیدش رسیده یا نه، پرسیدن از پشتیبانی است — همان
 * مسیرِ خرابِ بی‌صدا، این بار روی پول.
 */
function PendingOrders({ orders }) {
  const open = (orders || []).filter(
    (o) => o.status === "pending" || o.status === "awaiting");
  if (!open.length) return null;

  return (
    <div className="mn-pend">
      {open.map((o) => (
        <div key={o.id} className="mn-pend-row">
          <span className={`mn-pend-ico ${o.status}`}>
            {o.status === "awaiting" ? <Clock size={15} /> : <CreditCard size={15} />}
          </span>
          <span className="mn-pend-body">
            <b>{o.plan || "سفارش"}</b>
            <span>
              {o.status === "awaiting"
                ? "رسید فرستاده شده — در انتظار تایید"
                : "منتظر رسید شماست"}
            </span>
          </span>
          <span className="mn-pend-amt">{faNum(o.amount)}</span>
        </div>
      ))}
    </div>
  );
}

/* ═══════════════ تنظیمات و پروفایل ═══════════════ */

/**
 * پروفایلِ خودِ مشتری.
 *
 * چرا لازم است: `first_name` از تلگرام می‌آید و ممکن است «😎» باشد
 * یا اصلاً نباشد، و شماره را ربات فقط وقتی دارد که کاربر دکمه‌اش را
 * زده باشد. بدون این دو، پشتیبانی نمی‌داند با که حرف می‌زند — و
 * خودِ مشتری هم در فهرستِ سفارش‌ها «بدون نام» است.
 */
function SettingsView({ me, onSave, onAvatar, onDropAvatar, onTopUp,
                        support, channel }) {
  const [name, setName] = useState(me?.name || "");
  const [phone, setPhone] = useState(me?.phone || "");
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const fileRef = useRef(null);

  useEffect(() => {
    setName(me?.name || "");
    setPhone(me?.phone || "");
  }, [me?.name, me?.phone]);

  const dirty = (name || "") !== (me?.name || "")
             || (phone || "") !== (me?.phone || "");

  const save = async () => {
    setBusy("save"); setErr(""); setMsg("");
    try {
      await onSave({ name: name.trim(), phone: phone.trim() });
      buzz("ok");
      setMsg("ذخیره شد");
      setTimeout(() => setMsg(""), 2200);
    } catch (e) { buzz("err"); setErr(e.message); } finally { setBusy(""); }
  };

  const pick = async (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    setErr("");
    if (f.size > 512 * 1024) { setErr("حجم عکس بیشتر از ۵۱۲ کیلوبایت است"); return; }
    setBusy("photo");
    try {
      const data = await new Promise((res, rej) => {
        const r = new FileReader();
        r.onload = () => res(String(r.result || ""));
        r.onerror = () => rej(new Error("فایل خوانده نشد"));
        r.readAsDataURL(f);
      });
      await onAvatar(data);
      buzz("ok");
    } catch (e2) { buzz("err"); setErr(e2.message); } finally { setBusy(""); }
  };

  return (
    <>
      <div className="mn-sec-head mb-1">
        <div>
          <h2>تنظیمات</h2>
          <p>مشخصاتتان را کامل کنید تا پشتیبانی سریع‌تر کمکتان کند</p>
        </div>
      </div>

      {/* ── عکس ── */}
      <div className="mn-prof">
        <button className="mn-prof-pic" onClick={() => fileRef.current?.click()}
          disabled={busy === "photo"} title="تغییر عکس">
          <Avatar name={me?.name} id={me?.tgId} size={74} src={me?.avatar} ring />
          <span className="mn-prof-cam">
            {busy === "photo" ? <Loader2 size={13} className="animate-spin" />
                              : <Camera size={13} />}
          </span>
        </button>
        <div className="mn-prof-side">
          <b>{me?.name || "بدون نام"}</b>
          <span dir="ltr">{me?.tgId ? faDigits(me.tgId) : "—"}</span>
          {me?.avatar && (
            <button className="mn-prof-drop" onClick={onDropAvatar}>
              <Trash2 size={12} /> برداشتن عکس
            </button>
          )}
        </div>
        <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp"
          onChange={pick} className="hidden" />
      </div>

      {/* ── مشخصات ── */}
      <div className="mn-field">
        <label htmlFor="mn-name"><User size={13} /> نام و نام خانوادگی</label>
        <input id="mn-name" value={name} maxLength={60}
          onChange={(e) => setName(e.target.value)}
          placeholder="مثلاً مریم کاظمی" />
      </div>

      <div className="mn-field">
        <label htmlFor="mn-phone"><Phone size={13} /> شماره تماس</label>
        <input id="mn-phone" value={phone} dir="ltr" inputMode="tel" maxLength={24}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="09121234567" />
        <small>فقط برای پشتیبانی استفاده می‌شود.</small>
      </div>

      {err && (
        <div className="mn-pay-err"><AlertTriangle size={14} /><span>{err}</span></div>
      )}

      <button className="mn-pay-btn" onClick={save} disabled={!dirty || busy === "save"}>
        {busy === "save" ? <Loader2 size={15} className="animate-spin" /> : <Check size={15} />}
        {/* «ذخیره شد» فقط *بعد از* ذخیره‌کردن. نسخه‌ی اول وقتی چیزی
            عوض نشده بود هم همین را می‌گفت — یعنی همان لحظه‌ی اول
            به کاربر می‌گفت کاری کرده که نکرده. */}
        {msg || "ذخیره"}
      </button>

      {/* ── حساب ── */}
      <div className="mn-sec-head mt-5 mb-1">
        <div><h2>حساب</h2></div>
      </div>
      <div className="mn-rows">
        <div className="mn-row-kv">
          <span>کیف پول</span>
          <b>{faNum(me?.balance ?? 0)} تومان</b>
        </div>
        <div className="mn-row-kv">
          <span>سکه</span>
          <b>{faNum(me?.coins ?? 0)}</b>
        </div>
        <button className="mn-row-kv act" onClick={onTopUp}>
          <span>شارژ کیف پول</span>
          <b><ChevronLeft size={15} /></b>
        </button>
      </div>

      {/* ── ارتباط ── */}
      {(support || channel) && (
        <>
          <div className="mn-sec-head mt-5 mb-1">
            <div><h2>ارتباط با ما</h2></div>
          </div>
          <div className="mn-links">
            {channel && (
              <a className="mn-link-chip" target="_blank" rel="noreferrer"
                href={`https://t.me/${String(channel).replace(/^@/, "")}`}>
                <Link2 size={14} /> کانال ما
              </a>
            )}
            {support && (
              <a className="mn-link-chip" target="_blank" rel="noreferrer"
                href={`https://t.me/${String(support).replace(/^@/, "")}`}>
                <ExternalLink size={14} /> پشتیبانی در تلگرام
              </a>
            )}
          </div>
        </>
      )}
    </>
  );
}

/* ═══════════════ صندوق پیام ═══════════════ */

/**
 * گفتگو با پشتیبانی — و خبرهای خودکار.
 *
 * تاییدِ رسید، ردش با متنِ دلیل، و حرف‌زدن با پشتیبانی همه در یک
 * صندوق‌اند. سه جای جدا یعنی سه نشان و سه صدا و سه جا برای از هم
 * پاشیدن.
 */
function InboxView({ msgs, busy, onSend, support, channel }) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [err, setErr] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    // تازه‌ترین پیام باید دیده شود، نه اینکه کاربر اسکرول کند
    endRef.current?.scrollIntoView({ block: "end" });
  }, [msgs]);

  /* وقتی کیبورد باز می‌شود، جعبه‌ی نوشتن را در دید نگه دار.
     روی گوشی، بازشدنِ کیبورد جعبه را زیر خودش می‌برد و کاربر
     چیزی را که می‌نویسد نمی‌بیند. هر مرورگری این را جور دیگری
     مدیریت می‌کند، ولی `scrollIntoView` روی همه یکسان است. */
  const boxRef = useRef(null);
  useEffect(() => {
    const el = boxRef.current;
    if (!el) return undefined;
    const de = document.documentElement;

    /* کیبورد را از روی *فوکوس* می‌شناسیم، نه از اختلافِ ارتفاع.
     *
     * نسخه‌ی قبلی `innerHeight - visualViewport.height` را می‌سنجید.
     * آن روی بعضی مرورگرها کار می‌کند، ولی داخل WebViewِ اندروید
     * خودِ لایه‌ی چیدمان هم کوچک می‌شود — یعنی اختلاف تقریباً صفر
     * می‌ماند و نوارِ تب هیچ‌وقت کنار نمی‌رفت. دقیقاً همان چیزی که
     * مالک دید: «منو می‌آید بالای کیبورد و هیچی دیده نمی‌شود».
     *
     * فوکوس روی جعبه‌ی نوشتن یعنی کیبورد باز است. این هیچ ریاضی‌ای
     * ندارد و روی هر WebViewی یکسان است.
     */
    const on = () => {
      de.dataset.mnTyping = "1";
      // فقط روی لمسی: روی دسکتاپ کیبوردی بالا نمی‌آید و این اسکرول
      // فقط صفحه را بی‌دلیل می‌پراند — که خودِ مالک هم دید
      if (matchMedia("(pointer: coarse)").matches) {
        setTimeout(() => el.scrollIntoView({ block: "end", behavior: "smooth" }), 140);
      }
    };
    const off = () => { delete de.dataset.mnTyping; };

    el.addEventListener("focus", on);
    el.addEventListener("blur", off);
    const vv = window.visualViewport;
    const onResize = () => { if (document.activeElement === el) on(); };
    vv?.addEventListener("resize", onResize);
    return () => {
      el.removeEventListener("focus", on);
      el.removeEventListener("blur", off);
      vv?.removeEventListener("resize", onResize);
      delete de.dataset.mnTyping;
    };
  }, []);

  const send = async () => {
    const body = text.trim();
    if (!body || sending) return;
    setSending(true); setErr("");
    try {
      await onSend(body);
      setText("");
    } catch (e) {
      // متن در کادر می‌ماند — کاربر دوباره تایپ نکند
      setErr(e.message);
    } finally { setSending(false); }
  };

  return (
    <div className="mn-chat">
      {(support || channel) && (
        <div className="mn-links">
          {channel && (
            <a className="mn-link-chip" href={`https://t.me/${String(channel).replace(/^@/, "")}`}
              target="_blank" rel="noreferrer">
              <Link2 size={14} /> کانال ما
            </a>
          )}
          {support && (
            <a className="mn-link-chip" href={`https://t.me/${String(support).replace(/^@/, "")}`}
              target="_blank" rel="noreferrer">
              <ExternalLink size={14} /> پشتیبانی در تلگرام
            </a>
          )}
        </div>
      )}

      <div className="mn-chat-log">
        {busy && !msgs ? (
          <div aria-busy="true">
            <Skeleton h={54} className="mb-2" />
            <Skeleton h={38} className="mb-2" />
          </div>
        ) : !(msgs || []).length ? (
          <EmptyState icon={MessageCircle} text="هنوز پیامی نیست"
            hint="هر سوالی دارید همین‌جا بنویسید — خبرِ تایید یا ردِ رسیدتان هم این‌جا می‌آید." />
        ) : (msgs || []).map((m) => (
          <div key={m.id}
            className={`mn-msg ${m.from === "user" ? "me" : m.from === "system" ? "sys" : "them"}`
              + `${m.pending ? " pending" : ""}${m.failed ? " failed" : ""}`}>
            {m.from === "system" && <Shield size={13} className="mn-msg-ico" />}
            <span className="mn-msg-body">{m.body}</span>
            <span className="mn-msg-at">
              {m.at ? faDigits(String(m.at).slice(11, 16)) : ""}
              {m.pending && " · در حال رفتن"}
              {m.failed && " · نرفت"}
            </span>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {err && (
        <div className="mn-pay-err"><AlertTriangle size={14} /><span>{err}</span></div>
      )}

      <div className="mn-chat-bar">
        <textarea ref={boxRef} rows={1} dir="auto" value={text} placeholder="پیامتان را بنویسید…"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
          }} />
        <button onClick={send} disabled={sending || !text.trim()}
          aria-label="فرستادن">
          {sending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
        </button>
      </div>
    </div>
  );
}

/* ═══════════════ برگه‌ی پرداخت ═══════════════ */

/**
 * تاییدِ خرید، به شکلِ برگه‌ای که از پایین می‌آید.
 *
 * چرا برگه و نه صفحه‌ی تازه: خرید یک تصمیمِ کوتاه است و کاربر باید
 * همان لحظه ببیند چقدر دارد و بعدش چقدر می‌ماند. رفتن به صفحه‌ی
 * دیگر، این مقایسه را از جلوی چشمش برمی‌دارد.
 */
function PaySheet({ pay, me, onClose, onConfirm, onTopUp,
                   onCard, onReceipt, onTopupStart }) {
  const fileRef = useRef(null);
  const [amt, setAmt] = useState(0);
  if (!pay) return null;
  const isTopup = !!pay.topup;
  const p = pay.plan;
  const bal = Number(me?.balance || 0);
  const price = isTopup ? 0 : Number(p?.price || 0);
  const after = bal - price;
  const short = price - bal;
  const busy = pay.state === "busy";
  const enough = after >= 0;

  const pickFile = async (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    if (f.size > 3 * 1024 * 1024) { onReceipt({ err: "تصویر بیشتر از ۳ مگابایت است" }); return; }
    const data = await new Promise((res, rej) => {
      const r = new FileReader();
      r.onload = () => res(String(r.result || ""));
      r.onerror = () => rej(new Error("فایل خوانده نشد"));
      r.readAsDataURL(f);
    }).catch(() => null);
    if (data) onReceipt({ data });
  };

  const head = (
    <div className="mn-sheet-head">
      <b>{isTopup
        ? (pay.step === "card" ? "واریز کارت‌به‌کارت" : "شارژ کیف پول")
        : (pay.step === "card" ? "واریز کارت‌به‌کارت" : "تایید خرید")}</b>
      <span>{isTopup
        ? `موجودی فعلی: ${faNum(bal)} تومان`
        : `${p.gb === 0 ? "نامحدود" : `${faNum(p.gb)} گیگابایت`} / ${faNum(p.days)} روز`}</span>
    </div>
  );

  let body;

  /* انتخابِ مبلغِ شارژ.
     مبلغ‌های آماده همان‌هایی‌اند که ربات نشان می‌دهد، به‌علاوه‌ی
     مبلغِ دلخواه — چون کسی که دقیقاً ۲۳۰ هزار کم دارد نباید مجبور
     شود ۵۰۰ بریزد. */
  if (isTopup && pay.step === "amount") {
    const PRESETS = [100000, 200000, 500000, 1000000];
    const chosen = Number(amt || 0);
    const okAmount = chosen >= 10000 && chosen <= 50000000;
    body = (
      <>
        <div className="mn-amt-grid">
          {PRESETS.map((v) => (
            <button key={v} className={`mn-amt ${chosen === v ? "on" : ""}`}
              onClick={() => { buzz("light"); setAmt(v); }}>
              {faNum(v)}
              <em>تومان</em>
            </button>
          ))}
        </div>

        <div className="mn-field mt-1">
          <label htmlFor="mn-amt">مبلغ دلخواه</label>
          <input id="mn-amt" inputMode="numeric" dir="ltr"
            value={chosen ? String(chosen) : ""}
            onChange={(e) => setAmt(Number(String(e.target.value).replace(/\D/g, "")) || 0)}
            placeholder="250000" />
          <small>از ۱۰ هزار تا ۵۰ میلیون تومان.</small>
        </div>

        {pay.state === "err" && (
          <div className="mn-pay-err"><AlertTriangle size={14} /><span>{pay.why}</span></div>
        )}

        <button className="mn-pay-btn" disabled={!okAmount || busy}
          onClick={() => onTopupStart?.(chosen)}>
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Wallet size={15} />}
          ادامه
        </button>
      </>
    );
  } else if (pay.state === "done") {
    body = (
      <div className="mn-pay-done">
        <span className="mn-pay-tick"><Check size={26} /></span>
        <b>اشتراک ساخته شد</b>
        <span>{p.gb === 0 ? "نامحدود" : `${faNum(p.gb)} گیگابایت`}
          {" · "}{faNum(p.days)} روز</span>
        <div className="mn-pay-left">
          مانده‌ی کیف پول: <b>{faNum(pay.left ?? after)}</b> تومان
        </div>
        <button className="mn-pay-btn" onClick={onClose}>دیدن اشتراک‌ها</button>
      </div>
    );
  } else if (pay.state === "sent") {
    // رسید رفت — ولی هنوز تایید نشده. این تفاوت باید روشن باشد،
    // وگرنه مشتری فکر می‌کند اشتراکش آماده است و نیست.
    body = (
      <div className="mn-pay-done">
        <span className="mn-pay-tick wait"><Clock size={24} /></span>
        <b>رسید شما ثبت شد</b>
        <span>به‌محض تایید، اشتراک ساخته می‌شود و همین‌جا می‌بینیدش.
          معمولاً چند دقیقه طول می‌کشد.</span>
        <button className="mn-pay-btn" onClick={onClose}>باشه</button>
      </div>
    );
  } else if (pay.step === "card") {
    const c = pay.card || {};
    body = (
      <>
        {head}
        <div className="mn-pay-rows">
          {/* برای شارژ، مبلغ از خودِ سفارش می‌آید — `price`
              مالِ پلن است و در شارژ صفر می‌ماند. */}
          <div><span>مبلغ</span><b>{faNum(isTopup ? pay.amount : price)} تومان</b></div>
          {c.holder && <div><span>به نام</span><b>{c.holder}</b></div>}
          {c.bank && <div><span>بانک</span><b>{c.bank}</b></div>}
        </div>

        <button className="mn-card-no" onClick={() => onCard.copy(c.number)}
          title="کپی شماره کارت">
          {/* شماره‌ی کارت عدد نیست، شماره است: `faNum` جداکننده‌ی
              هزارگان می‌گذارد و «۶٬۰۳۷٬۹۹۱٬…» چیزی است که هیچ‌کس
              نمی‌تواند در اپ بانک وارد کند. همان اشتباهی که یک‌بار
              سرِ شناسه‌ی تلگرام رخ داد. */}
          <span dir="ltr">{faDigits(String(c.number || "").replace(/\D/g, "")
            .replace(/(\d{4})(?=\d)/g, "$1 "))}</span>
          {pay.copied ? <Check size={15} /> : <Copy size={15} />}
        </button>

        <div className="mn-pay-note">
          مبلغ را واریز کنید، بعد <b>عکس رسید</b> یا <b>متن پیامک بانک</b> را
          بفرستید.
        </div>

        {pay.state === "err" && (
          <div className="mn-pay-err"><AlertTriangle size={14} />
            <span>{pay.why}</span></div>
        )}

        <textarea className="mn-receipt-text" rows={2} dir="auto"
          placeholder="یا متن پیامک بانک را این‌جا بچسبانید…"
          value={pay.text || ""}
          onChange={(e) => onCard.setText(e.target.value)} />

        <div className="mn-pay-two">
          <button className="mn-pay-btn" disabled={busy}
            onClick={() => fileRef.current?.click()}>
            {busy ? <Loader2 size={15} className="animate-spin" />
                  : <ImageIcon size={15} />}
            عکس رسید
          </button>
          <button className="mn-pay-btn ghost" disabled={busy || !(pay.text || "").trim()}
            onClick={() => onReceipt({ text: pay.text })}>
            فرستادن متن
          </button>
        </div>
        <input ref={fileRef} type="file" accept="image/*" className="hidden"
          onChange={pickFile} />

        <button className="mn-pay-cancel" onClick={onClose} disabled={busy}>
          انصراف
        </button>
      </>
    );
  } else {
    body = (
      <>
        {head}
        <div className="mn-pay-rows">
          <div><span>مبلغ</span><b>{faNum(price)} تومان</b></div>
          <div><span>موجودی کیف پول</span><b>{faNum(bal)} تومان</b></div>
          <div className={enough ? "ok" : "bad"}>
            <span>{enough ? "بعد از خرید" : "کسری"}</span>
            <b>{faNum(Math.abs(after))} تومان</b>
          </div>
        </div>

        {pay.state === "err" && (
          <div className="mn-pay-err"><AlertTriangle size={14} />
            <span>{pay.why}</span></div>
        )}

        {/* کیف پول وقتی پول هست، وگرنه کارت. هر دو همیشه در دسترس‌اند
            — مشتری‌ای که ترجیح می‌دهد کارت‌به‌کارت کند نباید مجبور
            شود اول کیف پولش را شارژ کند. */}
        {enough && (
          <button className="mn-pay-btn" onClick={onConfirm} disabled={busy}>
            {busy ? <Loader2 size={15} className="animate-spin" />
                  : <Wallet size={15} />}
            {busy ? "در حال پرداخت…" : "پرداخت از کیف پول"}
          </button>
        )}

        <button className={`mn-pay-btn ${enough ? "ghost" : ""}`}
          onClick={onCard.start} disabled={busy}>
          <CreditCard size={15} /> کارت‌به‌کارت
        </button>

        {!enough && (
          <>
            <div className="mn-pay-note">
              برای پرداخت از کیف پول {faNum(short)} تومان کم دارید.
            </div>
            <button className="mn-pay-btn ghost" onClick={onTopUp} disabled={busy}>
              <Wallet size={15} /> شارژ کیف پول در ربات
            </button>
          </>
        )}

        <button className="mn-pay-cancel" onClick={onClose} disabled={busy}>
          انصراف
        </button>
      </>
    );
  }

  return createPortal(
    <div className="mn-sheet-wrap" role="dialog" aria-modal="true">
      <div className="mn-sheet-bg" onClick={busy ? undefined : onClose} />
      <div className="mn-sheet">
        <span className="mn-sheet-grip" aria-hidden="true" />
        {body}
      </div>
    </div>,
    document.body);
}

/* ═══════════════ اپ ═══════════════ */

const TABS = [
  { k: "home", l: "خانه", i: Home },
  { k: "buy", l: "خرید", i: ShoppingBag },
  { k: "subs", l: "اشتراک", i: Layers },
  { k: "chat", l: "پیام‌ها", i: MessageCircle },
  { k: "me", l: "تنظیمات", i: User },
];

export default function Mini() {
  const [tab, setTab] = useState("home");
  const [me, setMe] = useState(null);
  const [subs, setSubs] = useState(null);
  const [plans, setPlans] = useState(null);
  const [detail, setDetail] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(true);
  const [pay, setPay] = useState(null);
  const [orders, setOrders] = useState([]);
  const [msgs, setMsgs] = useState(null);
  const [unread, setUnread] = useState(0);
  const [toast, setToast] = useState(null);

  const load = useCallback(async () => {
    setBusy(true);
    setErr("");
    try {
      const [m, s, p, o] = await Promise.all([
        api("/api/mini/me"), api("/api/mini/subs"), api("/api/mini/plans"),
        // سفارش‌های باز نباید کلِ صفحه را بیندازند اگر نیامدند
        api("/api/mini/orders").catch(() => ({ orders: [] })),
      ]);
      setMe(m); setSubs(s.subs || []); setPlans(p.plans || []);
      setOrders(o.orders || []);
      // صندوق جدا بارگذاری می‌شود: نیامدنش نباید بقیه را بیندازد
      api("/api/mini/inbox")
        .then((x) => { setMsgs(x.messages || []); setUnread(x.unread || 0); })
        .catch(() => { /* نشان عوض نمی‌شود، بقیه‌ی اپ کار می‌کند */ });
    } catch (e) {
      setErr(e.message);
    } finally { setBusy(false); }
  }, []);

  useEffect(() => {
    const w = tg();
    if (w) {
      w.ready();
      w.expand();
      syncTheme();
      syncSafeArea();
      w.onEvent?.("themeChanged", syncTheme);
      // ناحیه‌ی امن ثابت نیست: چرخاندنِ گوشی و بازشدنِ صفحه‌کلید
      // عوضش می‌کنند
      w.onEvent?.("safeAreaChanged", syncSafeArea);
      w.onEvent?.("contentSafeAreaChanged", syncSafeArea);
      w.onEvent?.("viewportChanged", syncSafeArea);
    }
    document.title = "اشتراک من";
    load();
    return () => {
      try {
        const x = tg();
        x?.offEvent?.("themeChanged", syncTheme);
        x?.offEvent?.("safeAreaChanged", syncSafeArea);
        x?.offEvent?.("contentSafeAreaChanged", syncSafeArea);
        x?.offEvent?.("viewportChanged", syncSafeArea);
      } catch { /* بی‌صدا */ }
    };
  }, [load]);

  // دکمه‌ی بازگشتِ خودِ تلگرام، وقتی داخل جزئیات هستیم — همان
  // چیزی که کاربر در هر مینی‌اپ دیگری انتظار دارد
  /* وقتی مشتری برمی‌گردد، تازه‌اش کن.
     *
     * رسید که فرستاده شد، مشتری می‌رود سراغ کار دیگری و بعد
     * برمی‌گردد ببیند تایید شده یا نه. بدون این، همان صفحه‌ی کهنه را
     * می‌بیند و فکر می‌کند هیچ اتفاقی نیفتاده — یعنی می‌رود از
     * پشتیبانی می‌پرسد.
     *
     * با فاصله‌ی کمینه، وگرنه هر بار جابه‌جا شدن بین تب‌های تلگرام
     * یک درخواست می‌زند. */
  const lastLoad = useRef(0);
  useEffect(() => {
    const onBack = () => {
      if (document.visibilityState !== "visible") return;
      const now = Date.now();
      if (now - lastLoad.current < 8000) return;
      lastLoad.current = now;
      load();
    };
    /* سه رویداد، نه یکی.
       داخل WebViewِ تلگرام برگشتن به مینی‌اپ همیشه
       `visibilitychange` نمی‌دهد — گاهی فقط `focus` می‌آید. و وقتی
       اینترنت قطع و وصل می‌شود هیچ‌کدام نمی‌آیند، پس کاربر با
       صفحه‌ی کهنه می‌ماند تا تیکِ بعدی. */
    document.addEventListener("visibilitychange", onBack);
    window.addEventListener("focus", onBack);
    window.addEventListener("online", onBack);
    return () => {
      document.removeEventListener("visibilitychange", onBack);
      window.removeEventListener("focus", onBack);
      window.removeEventListener("online", onBack);
    };
  }, [load]);

  /* کیبوردِ گوشی.
   *
   * جعبه‌ی نوشتن `position: sticky; bottom: 0` است، یعنی به پایینِ
   * *لایه‌ی چیدمان* می‌چسبد. ولی کیبورد لایه‌ی چیدمان را کوچک
   * نمی‌کند — فقط `visualViewport` را. نتیجه این بود که جعبه پشتِ
   * کیبورد می‌رفت و نوارِ تب هم رویش می‌نشست: کاربر تایپ می‌کرد و
   * چیزی که می‌نوشت را نمی‌دید.
   *
   * پس ارتفاعِ کیبورد را خودمان می‌سنجیم و به CSS می‌دهیم. وقتی
   * باز است نوارِ تب کنار می‌رود — همان کاری که خودِ تلگرام
   * می‌کند.
   */
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return undefined;
    const de = document.documentElement;
    /* بدون requestAnimationFrame.
       rAF در تبِ پنهان اصلاً اجرا نمی‌شود، پس اندازه‌ی کیبورد تا
       وقتی صفحه دوباره دیده نشود به‌روز نمی‌شد — و کارش هم آن‌قدر
       سبک است که به کوالسینگ نیاز ندارد. */
    const apply = () => {
      const kb = Math.max(0, window.innerHeight - vv.height - vv.offsetTop);
      de.style.setProperty("--mn-kb", `${Math.round(kb)}px`);
      // آستانه: چرخاندنِ گوشی و نوارِ آدرس هم چند ده پیکسل
      // جابه‌جا می‌کنند و آن‌ها کیبورد نیستند
      de.dataset.mnKb = kb > 120 ? "1" : "0";
    };
    apply();
    vv.addEventListener("resize", apply);
    vv.addEventListener("scroll", apply);
    return () => {
      vv.removeEventListener("resize", apply);
      vv.removeEventListener("scroll", apply);
      de.style.removeProperty("--mn-kb");
      delete de.dataset.mnKb;
    };
  }, []);

  /* هر بیست ثانیه فقط شمارنده‌ها.
   *
   * کاربر نباید مجبور باشد تازه‌سازی بزند تا بفهمد رسیدش تایید شده.
   * ولی گرفتنِ کلِ داده هر بیست ثانیه روی اینترنتِ موبایل گران است،
   * پس اول شمارنده — و فقط وقتی عددی عوض شد، داده.
   *
   * وقتی صفحه پنهان است هیچ درخواستی نمی‌رود: مینی‌اپِ بازِ فراموش‌شده
   * نباید تا ابد به سرور بزند.
   */
  const seen = useRef({ unread: -1, openOrders: -1, subs: -1 });
  useEffect(() => {
    let alive = true;
    const beat = async () => {
      if (!alive || document.visibilityState !== "visible") return;
      try {
        const p = await api("/api/mini/ping");
        if (!alive) return;
        setUnread(p.unread || 0);
        const was = seen.current;
        const changed = was.unread !== -1
          && (p.unread !== was.unread || p.openOrders !== was.openOrders
              || p.subs !== was.subs);
        seen.current = p;
        if (changed) {
          load();
          if (p.unread > was.unread) {
            // پیامِ تازه را یک‌بار جلوی چشم بیاور — نه هر بار
            try {
              const x = await api("/api/mini/inbox");
              if (!alive) return;
              setMsgs(x.messages || []);
              const last = (x.messages || []).filter((m) => m.from !== "user").pop();
              if (last) { buzz("ok"); setToast(last); }
            } catch { /* بی‌صدا */ }
          }
        }
      } catch { /* شبکه قطع بود — دفعه‌ی بعد */ }
    };
    /* داخل گفتگو تندتر.

       بیست ثانیه برای شمارنده‌ها خوب است، ولی وقتی کاربر *در حالِ
       چت‌کردن* است یعنی تا بیست ثانیه جوابِ پشتیبانی را نمی‌بیند —
       که در یک گفتگو خیلی طولانی است. بیرون از چت همان بیست
       می‌ماند تا روی اینترنت موبایل گران نشود. */
    /* سه ثانیه داخل گفتگو.
       شش ثانیه هم برای یک گفتگوی زنده زیاد بود — مالک جواب
       می‌داد و مشتری تا شش ثانیه بعد نمی‌دید. بیرون از چت همان
       بیست می‌ماند تا روی اینترنت موبایل گران نشود. */
    const id = setInterval(beat, tab === "chat" ? 3000 : 20000);
    beat();
    return () => { alive = false; clearInterval(id); };
  }, [load, tab]);

  const saveProfile = async (body) => {
    await api("/api/mini/profile", { method: "POST", body });
    const m = await api("/api/mini/me");
    setMe(m);
  };

  const setAvatar = async (data) => {
    await api("/api/mini/profile/avatar", { method: "POST", body: { data } });
    const m = await api("/api/mini/me");
    setMe(m);
  };

  const dropAvatar = async () => {
    try {
      await api("/api/mini/profile/avatar", { method: "DELETE" });
      const m = await api("/api/mini/me");
      buzz("light");
      setMe(m);
    } catch (e) { setErr(e.message); }
  };

  /**
   * فرستادنِ پیام — با حبابِ فوری.
   *
   * قبلاً تا *دو* رفت‌وبرگشت تمام نمی‌شد (POST، بعد خواندنِ دوباره)
   * هیچ چیزی روی صفحه نمی‌آمد. روی اینترنتِ موبایل یعنی یکی دو
   * ثانیه سکوت، و کاربر دوباره می‌زد.
   */
  const sendMsg = async (body) => {
    const temp = `tmp-${Date.now()}`;
    const now = new Date().toISOString().slice(0, 19).replace("T", " ");
    setMsgs((prev) => [...(prev || []),
      { id: temp, from: "user", body, at: now, pending: true }]);
    try {
      await api("/api/mini/inbox/send", { method: "POST", body: { body } });
      const x = await api("/api/mini/inbox");
      setMsgs(x.messages || []);
      setUnread(x.unread || 0);
    } catch (e) {
      // حبابِ نرفته نباید شبیه پیامِ رفته بماند
      setMsgs((prev) => (prev || []).map(
        (m) => (m.id === temp ? { ...m, pending: false, failed: true } : m)));
      throw e;
    }
  };

  // بازکردنِ تبِ پیام‌ها یعنی خوانده شد
  useEffect(() => {
    if (tab !== "chat") return;
    setUnread(0);
    setToast(null);
    api("/api/mini/inbox/read", { method: "POST" }).catch(() => { /* بی‌صدا */ });
    api("/api/mini/inbox")
      .then((x) => setMsgs(x.messages || []))
      .catch(() => { /* بی‌صدا */ });
  }, [tab]);

  useEffect(() => {
    const w = tg();
    const b = w?.BackButton;
    if (!b) return;
    const back = () => setDetail(null);
    if (detail) { b.show?.(); b.onClick?.(back); }
    else b.hide?.();
    return () => { try { b.offClick?.(back); } catch { /* بی‌صدا */ } };
  }, [detail]);

  // خرید همین‌جا انجام می‌شود، ولی هیچ محاسبه‌ای این‌جا نیست:
  // `/api/mini/buy` مستقیم `handlers.wallet_purchase` را صدا می‌زند
  // — همان هسته‌ای که خرید از داخل ربات هم از آن رد می‌شود. اگر
  // این‌جا دوباره نوشته می‌شد، می‌شد مسیر چهارمِ پول در این مخزن.
  const buy = (p) => { buzz("light"); setPay({ plan: p, state: "ask" }); };

  const confirmPay = async () => {
    if (!pay?.plan || pay.state === "busy") return;
    setPay((x) => ({ ...x, state: "busy" }));
    try {
      const r = await api("/api/mini/buy", {
        method: "POST", body: { planId: pay.plan.id },
      });
      buzz("ok");
      setPay({ plan: pay.plan, state: "done", left: r.left });
      // موجودی و فهرست اشتراک‌ها هر دو عوض شده‌اند
      await load();
    } catch (e) {
      buzz("err");
      setPay((x) => ({ ...x, state: "err", why: e.message }));
    }
  };

  /**
   * بازکردنِ ربات روی یک مقصدِ مشخص.
   *
   * چرا یک تابع: سه دکمه (شارژ، تمدید، پشتیبانی) همین کار را
   * می‌کردند و هر کدام جدا نوشته شده بودند. و مهم‌تر — همه‌شان وقتی
   * `botUsername` خالی بود بی‌صدا هیچ کاری نمی‌کردند.
   */
  const toBot = (payload, why) => {
    const u = (me?.botUsername || "").replace(/^@/, "");
    if (!u) { buzz("err"); setErr(why || "ربات این فروشگاه هنوز تنظیم نشده"); return; }
    const url = `https://t.me/${u}?start=${encodeURIComponent(payload)}`;
    const w = tg();
    buzz("ok");
    if (w?.openTelegramLink) w.openTelegramLink(url);
    else window.open(url, "_blank", "noopener");
  };

  // شارژ کیف پول هنوز در ربات است — رسیدِ شارژ آن‌جا ثبت می‌شود.
  /* شارژ کیف پول، داخل خودِ مینی‌اپ.
     تا امروز ربات را باز می‌کرد و کاربر باید آن‌جا مبلغ می‌زد و
     رسید می‌فرستاد — یعنی وسطِ خرید از اپ بیرون می‌افتاد. حالا
     همان برگه‌ی پرداخت، فقط با مبلغِ دلخواه به‌جای پلن. */
  const topUp = () => {
    buzz("light");
    setPay({ topup: true, state: "ask", step: "amount", amount: 0 });
  };

  const topup = {
    start: async (amount) => {
      setPay((x) => ({ ...x, state: "busy" }));
      try {
        const r = await api("/api/mini/topup", { method: "POST", body: { amount } });
        buzz("ok");
        setPay((x) => ({ ...x, state: "ask", step: "card", amount: r.amount,
                         orderId: r.orderId, card: r.card, text: "" }));
      } catch (e) {
        buzz("err");
        setPay((x) => ({ ...x, state: "err", why: e.message }));
      }
    },
  };

  // تمدید هم در ربات است، ولی مستقیم روی همین اشتراک باز می‌شود
  const renew = (s) => toBot(s?.id ? `renew_${s.id}` : "subs",
                             "برای تمدید به ربات برگردید");

  /* ── کارت‌به‌کارت ──
     سفارشِ `pending` ساخته می‌شود و شماره‌ی کارت می‌آید؛ تا رسید
     نیاید هیچ چیزی تایید نمی‌شود. همان مسیرِ کارتیِ ربات، فقط بدون
     رفتن به گفتگو. */
  const card = {
    start: async () => {
      if (!pay?.plan) return;
      setPay((x) => ({ ...x, state: "busy" }));
      try {
        const r = await api("/api/mini/order", {
          method: "POST", body: { planId: pay.plan.id },
        });
        buzz("ok");
        setPay((x) => ({ ...x, state: "ask", step: "card",
                         orderId: r.orderId, card: r.card, text: "" }));
      } catch (e) {
        buzz("err");
        setPay((x) => ({ ...x, state: "err", why: e.message }));
      }
    },
    copy: (n) => {
      try { navigator.clipboard?.writeText(String(n || "").replace(/\D/g, "")); }
      catch { /* بی‌صدا */ }
      buzz("ok");
      setPay((x) => ({ ...x, copied: true }));
      setTimeout(() => setPay((x) => (x ? { ...x, copied: false } : x)), 1600);
    },
    setText: (t) => setPay((x) => ({ ...x, text: t })),
  };

  const sendReceipt = async ({ data, text, err }) => {
    if (err) { buzz("err"); setPay((x) => ({ ...x, state: "err", why: err })); return; }
    if (!pay?.orderId) return;
    setPay((x) => ({ ...x, state: "busy" }));
    try {
      await api(`/api/mini/order/${pay.orderId}/receipt`, {
        method: "POST", body: data ? { data } : { text },
      });
      buzz("ok");
      setPay((x) => ({ ...x, state: "sent" }));
      // سفارش تازه در فهرست بیاید
      load();
    } catch (e) {
      buzz("err");
      setPay((x) => ({ ...x, state: "err", why: e.message }));
    }
  };

  if (!tg()) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6" dir="rtl">
        <div className="fx-card p-6 text-center" style={{ maxWidth: 380 }}>
          <AlertTriangle size={26} style={{ color: "var(--warn)" }} className="mx-auto mb-3" />
          <div className="text-[14px] font-semibold mb-2" style={{ color: "var(--text)" }}>
            این صفحه باید از داخل تلگرام باز شود
          </div>
          <p className="text-[13px] leading-relaxed" style={{ color: "var(--muted)" }}>
            در ربات روی دکمه‌ی مینی‌اپ بزنید. همه‌ی کارها از خودِ ربات هم
            انجام می‌شوند.
          </p>
        </div>
      </div>
    );
  }

  const view = detail ? "detail" : tab;

  return (
    <div className="mn-app" dir="rtl">
      {/* ── نوار برند ── */}
      <header className="mn-top">
        <div className="mn-brand">
          {/* لوگوی همین فروشگاه اگر آپلود شده، وگرنه چهره‌ی کاربر.
              مینی‌اپِ هر نماینده باید مالِ خودش به نظر برسد. */}
          {me?.logo
            ? <img src={me.logo} alt={me.brand || ""} className="mn-logo" />
            : <Avatar name={me?.name} id={me?.tgId} size={38} ring />}
          <div className="min-w-0">
            <b>{me?.brand || "اشتراک من"}</b>
            <span>{me?.name || "—"}</span>
          </div>
        </div>
        {/* دکمه‌ی «تازه‌سازی» برداشته شد.
            اپ خودش هر سه تا بیست ثانیه، و با برگشتن به آن، تازه
            می‌شود — پس دکمه‌اش فقط می‌گفت «شاید تازه نباشد». تنها
            نشانه‌ای که می‌ماند، چرخنده‌ی موقعِ بارگذاری است. */}
        {busy && <Loader2 size={16} className="animate-spin mn-head-busy" />}
      </header>

      <main className="mn-body">
        {err && (
          <div className="mn-err">
            <b>{err}</b>
            <span>همه‌ی این کارها از خودِ ربات هم انجام می‌شوند — پیام را
              ببندید و از منوی ربات ادامه بدهید.</span>
          </div>
        )}

        {/* هر بار که صفحه عوض شود، ورودش دوباره پخش می‌شود:
            `key` که عوض شود React درخت را از نو می‌سازد.

            تا امروز تب‌ها بی‌هیچ حرکتی جا عوض می‌کردند — پنل مدیر
            این را داشت و مینی‌اپ نداشت، و همان تفاوتِ کوچک است که
            یکی را «اپ» و دیگری را «صفحه‌ی وب» نشان می‌دهد. */}
        {/* تبِ گفتگو باید قدِ صفحه را پر کند، وگرنه جعبه‌ی نوشتن
            وسطِ صفحه می‌ماند و زیرش فضای مرده می‌افتد — اندازه‌گیری
            روی گوشیِ ۷۸۰ پیکسلی: ۱۸۶ پیکسل. */}
        <div key={view} className={`mn-view${view === "chat" ? " chat" : ""}`}>
        {busy && !subs ? (
          /* شکلِ همان چیزی که می‌آید — نه چرخنده. روی موبایل که
             صفحه کوتاه است، پریدنِ چیدمان بیشتر به چشم می‌آید. */
          <div aria-busy="true">
            <Skeleton h={150} className="mb-4" />
            {[0, 1].map((i) => (
              <div key={i} className="fx-card p-4 mb-3">
                <Skeleton w="52%" h={13} />
                <div className="mt-2.5"><Skeleton w="72%" h={10} /></div>
                <div className="mt-3"><Skeleton w="100%" h={6} /></div>
              </div>
            ))}
          </div>
        ) : view === "detail" ? (
          <SubDetail s={detail} onBack={() => setDetail(null)} onRenew={renew} />
        ) : view === "buy" ? (
          <BuyView plans={plans} onBuy={buy} />
        ) : view === "me" ? (
          <SettingsView me={me} onSave={saveProfile} onAvatar={setAvatar}
            onDropAvatar={dropAvatar} onTopUp={topUp}
            support={me?.support} channel={me?.channel} />
        ) : view === "chat" ? (
          <InboxView msgs={msgs} busy={busy} onSend={sendMsg}
            support={me?.support} channel={me?.channel} />
        ) : view === "subs" ? (
          (subs || []).length === 0 ? (
            <EmptyState icon={Package} text="هنوز اشتراکی ندارید"
              hint="با اولین خرید، اشتراکتان همین‌جا با حجم و تاریخ انقضا نشان داده می‌شود."
              action={<button onClick={() => setTab("buy")}
                className="fx-btn px-4 py-2 text-[13px]">دیدن پلن‌ها</button>} />
          ) : (subs || []).map((s) => (
            <SubRow key={s.id} s={s} onOpen={setDetail} />
          ))
        ) : (
          <>
            <PendingOrders orders={orders} />
            <HomeView me={me} subs={subs} onOpen={setDetail} onAll={() => setTab("subs")}
              onBuy={() => setTab("buy")} />
          </>
        )}
        </div>
      </main>

      {/* ── نوار پایین ──
          انگشتِ شست به پایینِ صفحه می‌رسد، نه به بالایش. */}
      <nav className="mn-tabs">
        {TABS.map((t) => (
          <button key={t.k} className={`mn-tab ${tab === t.k && !detail ? "on" : ""}`}
            onClick={() => { buzz("light"); setDetail(null); setTab(t.k); }}
            aria-current={tab === t.k && !detail ? "page" : undefined}>
            <span className="mn-tab-ico">
              <t.i size={19} />
              {t.k === "chat" && unread > 0 && (
                <i className="mn-badge">{unread > 9 ? "۹+" : faNum(unread)}</i>
              )}
            </span>
            <span>{t.l}</span>
          </button>
        ))}
      </nav>

      {/* پیامِ تازه یک‌بار جلوی چشم می‌آید.
          بدون این، مشتری باید حدس بزند که باید تبِ پیام‌ها را باز
          کند — و رسیدی که رد شده، دلیلش را هیچ‌وقت نمی‌بیند. */}
      {toast && (
        <button className="mn-toast" onClick={() => { setToast(null); setTab("chat"); }}>
          <span className="mn-toast-ico">
            {toast.from === "system" ? <Shield size={15} /> : <MessageCircle size={15} />}
          </span>
          <span className="mn-toast-body">
            <b>{toast.from === "system" ? "خبر تازه" : "پاسخ پشتیبانی"}</b>
            <span>{String(toast.body || "").slice(0, 90)}</span>
          </span>
          <ChevronLeft size={16} />
        </button>
      )}

      <PaySheet pay={pay} me={me}
        onConfirm={confirmPay}
        onTopUp={topUp}
        onTopupStart={topup.start}
        onCard={card}
        onReceipt={sendReceipt}
        onClose={() => {
          // بعد از خریدِ موفق، جایی که کاربر می‌خواهد برود
          // «اشتراک‌ها»ست — نه همان فهرست پلن‌ها که تازه از آن خرید
          // فقط خریدِ تمام‌شده اشتراک ساخته؛ رسیدِ فرستاده‌شده هنوز
          // منتظر تایید است و بردنِ کاربر به «اشتراک‌ها» یعنی نشان‌دادنِ
          // فهرستی که چیزی تازه در آن نیست.
          if (pay?.state === "done") setTab("subs");
          setPay(null);
        }} />
    </div>
  );
}
