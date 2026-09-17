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
import React, { useState, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import {
  AlertTriangle, ArrowLeft, Check, ChevronLeft, Copy, ExternalLink, Gift,
  Home, Layers, Link2, Loader2, Package, QrCode, RefreshCw, Shield,
  ShoppingBag, ShoppingCart, Trash2, Wallet, Zap,
} from "lucide-react";

import { API_URL } from "../lib/constants";
import { errText, faNum, toFaDigits as faDigits } from "../lib/format";
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

function HomeView({ me, subs, onOpen, onBuy }) {
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
          {(subs || []).length > 3 && (
            <button className="mn-link" onClick={onBuy}>
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

function SubDetail({ s, onBack }) {
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
        <Cell label="انقضا" value={s.expiryJalali || "—"}
          tone={s.daysLeft !== null && s.daysLeft <= 0 ? "var(--danger)"
            : s.daysLeft !== null && s.daysLeft <= 7 ? "var(--warn)" : undefined} />
      </div>

      {s.daysLeft !== null && s.daysLeft !== undefined && (
        <div className="mn-note">
          {s.daysLeft > 0
            ? <>‏{faNum(s.daysLeft)} روز تا پایان اشتراک باقی مانده.</>
            : <>این اشتراک منقضی شده — برای اتصال دوباره، از ربات تمدید کنید.</>}
        </div>
      )}

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
        همه‌ی این کارها — تمدید، تعویض لینک و حذف — از خودِ ربات هم
        انجام می‌شوند. اگر این صفحه بالا نیامد، منوی ربات همیشه هست.
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

/* ═══════════════ برگه‌ی پرداخت ═══════════════ */

/**
 * تاییدِ خرید، به شکلِ برگه‌ای که از پایین می‌آید.
 *
 * چرا برگه و نه صفحه‌ی تازه: خرید یک تصمیمِ کوتاه است و کاربر باید
 * همان لحظه ببیند چقدر دارد و بعدش چقدر می‌ماند. رفتن به صفحه‌ی
 * دیگر، این مقایسه را از جلوی چشمش برمی‌دارد.
 */
function PaySheet({ pay, me, onClose, onConfirm, onTopUp }) {
  if (!pay) return null;
  const p = pay.plan;
  const bal = Number(me?.balance || 0);
  const price = Number(p?.price || 0);
  const after = bal - price;
  const short = price - bal;
  const busy = pay.state === "busy";

  return createPortal(
    <div className="mn-sheet-wrap" role="dialog" aria-modal="true">
      <div className="mn-sheet-bg" onClick={busy ? undefined : onClose} />
      <div className="mn-sheet">
        <span className="mn-sheet-grip" aria-hidden="true" />

        {pay.state === "done" ? (
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
        ) : (
          <>
            <div className="mn-sheet-head">
              <b>تایید خرید</b>
              <span>{p.gb === 0 ? "نامحدود" : `${faNum(p.gb)} گیگابایت`}
                {" / "}{faNum(p.days)} روز</span>
            </div>

            <div className="mn-pay-rows">
              <div><span>مبلغ</span><b>{faNum(price)} تومان</b></div>
              <div><span>موجودی کیف پول</span><b>{faNum(bal)} تومان</b></div>
              <div className={after < 0 ? "bad" : "ok"}>
                <span>{after < 0 ? "کسری" : "بعد از خرید"}</span>
                <b>{faNum(Math.abs(after))} تومان</b>
              </div>
            </div>

            {pay.state === "err" && (
              <div className="mn-pay-err"><AlertTriangle size={14} />
                <span>{pay.why}</span></div>
            )}

            {after < 0 ? (
              <>
                <div className="mn-pay-note">
                  {faNum(short)} تومان کم دارید. شارژ کیف پول فعلاً در خودِ
                  ربات انجام می‌شود.
                </div>
                <button className="mn-pay-btn" onClick={onTopUp}>
                  <Wallet size={15} /> شارژ کیف پول
                </button>
              </>
            ) : (
              <button className="mn-pay-btn" onClick={onConfirm} disabled={busy}>
                {busy ? <Loader2 size={15} className="animate-spin" />
                      : <Wallet size={15} />}
                {busy ? "در حال پرداخت…" : "پرداخت از کیف پول"}
              </button>
            )}

            <button className="mn-pay-cancel" onClick={onClose} disabled={busy}>
              انصراف
            </button>
          </>
        )}
      </div>
    </div>,
    document.body);
}

/* ═══════════════ اپ ═══════════════ */

const TABS = [
  { k: "home", l: "خانه", i: Home },
  { k: "buy", l: "خرید اشتراک", i: ShoppingBag },
  { k: "subs", l: "اشتراک‌ها", i: Layers },
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

  const load = useCallback(async () => {
    setBusy(true);
    setErr("");
    try {
      const [m, s, p] = await Promise.all([
        api("/api/mini/me"), api("/api/mini/subs"), api("/api/mini/plans"),
      ]);
      setMe(m); setSubs(s.subs || []); setPlans(p.plans || []);
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
      w.onEvent?.("themeChanged", syncTheme);
    }
    document.title = "اشتراک من";
    load();
    return () => { try { tg()?.offEvent?.("themeChanged", syncTheme); } catch { /* بی‌صدا */ } };
  }, [load]);

  // دکمه‌ی بازگشتِ خودِ تلگرام، وقتی داخل جزئیات هستیم — همان
  // چیزی که کاربر در هر مینی‌اپ دیگری انتظار دارد
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

  // شارژ کیف پول هنوز در ربات است — کارت‌به‌کارت و رسید آن‌جاست.
  const topUp = () => {
    const w = tg();
    const u = me?.botUsername;
    if (w && u) { buzz("ok"); w.openTelegramLink(`https://t.me/${u}?start=wallet`); }
    else setErr("برای شارژ کیف پول به ربات برگردید");
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
        <button className="mn-icon-btn" onClick={() => { buzz("light"); load(); }}
          disabled={busy} title="تازه‌سازی" aria-label="تازه‌سازی">
          <RefreshCw size={16} className={busy ? "animate-spin" : ""} />
        </button>
      </header>

      <main className="mn-body">
        {err && (
          <div className="mn-err">
            <b>{err}</b>
            <span>همه‌ی این کارها از خودِ ربات هم انجام می‌شوند — پیام را
              ببندید و از منوی ربات ادامه بدهید.</span>
          </div>
        )}

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
          <SubDetail s={detail} onBack={() => setDetail(null)} />
        ) : view === "buy" ? (
          <BuyView plans={plans} onBuy={buy} />
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
          <HomeView me={me} subs={subs} onOpen={setDetail}
            onBuy={() => setTab("buy")} />
        )}
      </main>

      {/* ── نوار پایین ──
          انگشتِ شست به پایینِ صفحه می‌رسد، نه به بالایش. */}
      <nav className="mn-tabs">
        {TABS.map((t) => (
          <button key={t.k} className={`mn-tab ${tab === t.k && !detail ? "on" : ""}`}
            onClick={() => { buzz("light"); setDetail(null); setTab(t.k); }}
            aria-current={tab === t.k && !detail ? "page" : undefined}>
            <t.i size={19} />
            <span>{t.l}</span>
          </button>
        ))}
      </nav>

      <PaySheet pay={pay} me={me}
        onConfirm={confirmPay}
        onTopUp={topUp}
        onClose={() => {
          // بعد از خریدِ موفق، جایی که کاربر می‌خواهد برود
          // «اشتراک‌ها»ست — نه همان فهرست پلن‌ها که تازه از آن خرید
          if (pay?.state === "done") setTab("subs");
          setPay(null);
        }} />
    </div>
  );
}
