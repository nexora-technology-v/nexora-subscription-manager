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
 * قیمت از API می‌آید، خرید در خودِ ربات انجام می‌شود. مالک صریح گفت
 * حسابداری از این بحث جداست.
 */
import React, { useState, useEffect, useCallback } from "react";
import {
  AlertTriangle, ArrowLeft, Check, Copy, Gift, Link2, Loader2, Package,
  RefreshCw, ShoppingCart, Wallet,
} from "lucide-react";

import { API_URL } from "../lib/constants";
import { errText, faNum } from "../lib/format";
import { Skeleton } from "../ui/index";

/** آیا این آدرس مینی‌اپ است؟ */
export { isMini } from "../lib/route.js";

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
 * رنگ‌ها را از خودِ تلگرام می‌گیرد.
 *
 * چرا: مینی‌اپ تنها جایی است که **مشتری نهایی** می‌بیند، و کنار
 * بقیه‌ی اپ‌های تلگرام قضاوت می‌شود. تا امروز همیشه سرمه‌ایِ نکسورا
 * بود — روی تلگرامِ روشن، مثل صفحه‌ی وبی که تصادفاً آن‌جا باز شده.
 *
 * `themeParams` همان متغیرهایی را می‌دهد که خودِ تلگرام به پوسته‌اش
 * می‌دهد. روی همان `--bg` و `--surface` و … می‌نشینند، پس هیچ
 * کامپوننتی لازم نیست عوض شود.
 *
 * اگر تلگرام چیزی نداد (نسخه‌ی قدیمی)، هیچ‌کدام نوشته نمی‌شوند و
 * پالتِ خودِ نکسورا سر جایش می‌ماند.
 */
function syncTheme() {
  const w = tg();
  const p = w?.themeParams;
  if (!p || !p.bg_color) return false;
  const dark = (w.colorScheme || "dark") === "dark";
  const r = document.documentElement.style;
  const set = (k, v) => v && r.setProperty(k, v);

  set("--bg", p.secondary_bg_color || p.bg_color);
  set("--surface", p.bg_color);
  set("--surface-2", p.secondary_bg_color || p.bg_color);
  set("--surface-3", p.secondary_bg_color || p.bg_color);
  set("--text", p.text_color);
  set("--dim", p.hint_color || p.subtitle_text_color);
  set("--muted", p.hint_color || p.subtitle_text_color);
  set("--accent", p.button_color || p.link_color);
  set("--accent-2", p.link_color || p.button_color);
  // مرزها در پوسته‌ی روشن باید تیره باشند، نه سفیدِ کم‌رنگ — وگرنه
  // روی زمینه‌ی روشن اصلاً دیده نمی‌شوند و کارت‌ها در هم می‌روند
  set("--border", dark ? "rgba(255,255,255,.10)" : "rgba(0,0,0,.10)");
  set("--border-2", dark ? "rgba(255,255,255,.16)" : "rgba(0,0,0,.16)");
  set("--accent-soft", dark ? "rgba(255,255,255,.06)" : "rgba(0,0,0,.04)");

  // نوار بالای تلگرام هم هم‌رنگ شود، وگرنه یک خطِ رنگِ غریبه بالای
  // صفحه می‌ماند
  try {
    w.setHeaderColor?.(p.secondary_bg_color || p.bg_color);
    w.setBackgroundColor?.(p.secondary_bg_color || p.bg_color);
  } catch { /* نسخه‌ی قدیمی‌تر این متدها را ندارد */ }
  return true;
}

async function api(path) {
  const init = tg()?.initData || "";
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "X-Telegram-Init-Data": init },
  });
  const j = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(errText(j.detail, "درخواست ناموفق بود"));
  return j;
}

/* ── نوار مصرف — همان چیزی که در پنل نماینده جواب داد ── */
function UseBar({ pct }) {
  if (pct === null || pct === undefined) return null;
  const col = pct >= 90 ? "var(--danger)" : pct >= 75 ? "var(--warn)" : "var(--ok)";
  return (
    <div className="fx-usebar" title={`${faNum(pct)}٪ مصرف شده`}>
      <i style={{ width: `${Math.min(100, Math.max(2, pct))}%`, background: col }} />
    </div>
  );
}

function SubCard({ s }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard?.writeText(s.subUrl);
    setCopied(true);
    buzz("ok");
    setTimeout(() => setCopied(false), 1600);
  };
  const urgent = s.daysLeft !== null && s.daysLeft <= 7;
  return (
    <div className="fx-card p-4 mb-3">
      <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
        <span className="text-[14px] font-semibold" style={{ color: "var(--text)" }}>
          {s.plan || "اشتراک"}
        </span>
        <span className="fx-pill" style={{
          background: s.active ? "rgba(52,211,153,.14)" : "rgba(255,255,255,.05)",
          color: s.active ? "var(--ok)" : "var(--muted)",
        }}>
          {s.active ? "فعال" : "غیرفعال"}
        </span>
      </div>

      <div className="text-[13px] mb-1" style={{ color: "var(--dim)" }}>
        {faNum(s.usedGB)} از {s.gb === 0 ? "نامحدود" : `${faNum(s.gb)} گیگ`}
        {s.usagePct !== null && (
          <span className="text-[12px]" style={{ color: "var(--muted)" }}>
            {" "}({faNum(s.usagePct)}٪)
          </span>
        )}
      </div>
      <UseBar pct={s.usagePct} />

      <div className="text-[12px] mt-3 flex items-center gap-2 flex-wrap"
        style={{ color: "var(--muted)" }}>
        <span>انقضا: {s.expiryJalali || "—"}</span>
        {urgent && (
          <span className="fx-pill" style={{
            background: s.daysLeft <= 0 ? "rgba(248,113,113,.14)" : "rgba(251,191,36,.14)",
            color: s.daysLeft <= 0 ? "var(--danger)" : "var(--warn)",
          }}>
            {s.daysLeft <= 0 ? "منقضی" : `${faNum(s.daysLeft)} روز`}
          </span>
        )}
      </div>

      {s.subUrl && (
        <button onClick={copy}
          className="fx-btn-g w-full mt-3 py-2.5 text-[13px] flex items-center justify-center gap-1.5">
          {/* آیکون از کپی به تیک تبدیل می‌شود و تیک *کشیده* می‌شود:
              بازخوردی که بدون خواندنِ متن هم فهمیده می‌شود */}
          {copied ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--ok)"
              strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
              <path className="fx-chk" d="m4 12 5.5 5.5L20 7" />
            </svg>
          ) : <Copy size={13} />}
          {copied ? "کپی شد" : "کپی لینک اشتراک"}
        </button>
      )}
    </div>
  );
}

function PlanCard({ p, onBuy }) {
  return (
    <div className="fx-card p-4 mb-3">
      <div className="flex items-center justify-between gap-2 mb-1 flex-wrap">
        <span className="text-[14px] font-semibold" style={{ color: "var(--text)" }}>{p.name}</span>
        {p.isTrial && (
          <span className="fx-pill" style={{
            background: "rgba(52,211,153,.14)", color: "var(--ok)" }}>رایگان</span>
        )}
      </div>
      {p.desc && (
        <div className="text-[12px] mb-2 leading-relaxed" style={{ color: "var(--muted)" }}>
          {p.desc}
        </div>
      )}
      <div className="flex items-center gap-3 text-[13px] mb-3 flex-wrap"
        style={{ color: "var(--dim)" }}>
        <span>{p.gb === 0 ? "نامحدود" : `${faNum(p.gb)} گیگ`}</span>
        <span style={{ opacity: .4 }}>•</span>
        <span>{faNum(p.days)} روز</span>
        {p.devices > 0 && (
          <>
            <span style={{ opacity: .4 }}>•</span>
            <span>{faNum(p.devices)} دستگاه</span>
          </>
        )}
      </div>
      <div className="flex items-center justify-between gap-2">
        <span className="text-[16px] font-extrabold"
          style={{ color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
          {p.price ? faNum(p.price) : "۰"}
          <span className="text-[12px] fx-fa-sub"> تومان</span>
        </span>
        <button onClick={() => onBuy(p)}
          className="fx-btn px-4 py-2 text-[13px] flex items-center gap-1.5">
          <ShoppingCart size={13} /> خرید
        </button>
      </div>
    </div>
  );
}

export default function Mini() {
  const [tab, setTab] = useState("subs");
  const [me, setMe] = useState(null);
  const [subs, setSubs] = useState(null);
  const [plans, setPlans] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(true);

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
      // کاربر می‌تواند وسط کار پوسته‌ی تلگرام را عوض کند
      w.onEvent?.("themeChanged", syncTheme);
    }
    document.title = "اشتراک من";
    load();
    return () => { try { tg()?.offEvent?.("themeChanged", syncTheme); } catch { /* بی‌صدا */ } };
  }, [load]);

  // خرید در خودِ ربات انجام می‌شود.
  //
  // مینی‌اپ فقط پلن را نشان می‌دهد و کاربر را به همان مسیری می‌برد
  // که از قبل کار می‌کند. اگر خرید این‌جا پیاده می‌شد، قیمت و
  // پورسانت و سکه در دو جا حساب می‌شدند — همان باگی که این مخزن
  // بارها دیده.
  const buy = (p) => {
    const w = tg();
    const u = me?.botUsername;
    if (w && u) {
      buzz("ok");
      w.openTelegramLink(`https://t.me/${u}?start=plan_${p.id}`);
      w.close();
    } else {
      buzz("err");
      setErr("برای خرید به ربات برگردید و «خرید اشتراک» را بزنید");
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

  return (
    <div className="min-h-screen" dir="rtl" style={{ background: "var(--bg)" }}>
      <div className="max-w-xl mx-auto px-4 py-5">

        <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
          <div>
            <div className="text-[16px] font-bold" style={{ color: "var(--text)" }}>
              {me?.brand || "اشتراک من"}
            </div>
            {me?.name && (
              <div className="text-[13px]" style={{ color: "var(--muted)" }}>
                {me.name}
              </div>
            )}
          </div>
          <button onClick={load} disabled={busy}
            className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
            {busy ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
            تازه‌سازی
          </button>
        </div>

        {me && (
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="fx-card p-3.5">
              <div className="text-[12px] mb-1 flex items-center gap-1.5"
                style={{ color: "var(--muted)" }}>
                <Wallet size={13} /> کیف پول
              </div>
              <div className="text-[17px] font-extrabold"
                style={{ color: "var(--ok)", fontFamily: "var(--mono)" }}>
                {faNum(me.balance)}
                <span className="text-[11.5px] fx-fa-sub"> تومان</span>
              </div>
            </div>
            <div className="fx-card p-3.5">
              <div className="text-[12px] mb-1 flex items-center gap-1.5"
                style={{ color: "var(--muted)" }}>
                <Gift size={13} /> سکه
              </div>
              <div className="text-[17px] font-extrabold"
                style={{ color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
                {faNum(me.coins)}
              </div>
            </div>
          </div>
        )}

        {/* خطا باید بگوید چه چیزی نشد، و راه ربات را هم نشان بدهد —
            وگرنه مشتری روی صفحه‌ی خالی می‌ماند و فکر می‌کند سرویس
            خراب است */}
        {err && (
          <div className="fx-card p-4 mb-4" style={{ borderColor: "rgba(248,113,113,.3)" }}>
            <div className="text-[13px] mb-2" style={{ color: "var(--danger)" }}>{err}</div>
            <div className="text-[12px]" style={{ color: "var(--muted)" }}>
              همه‌ی این کارها از خودِ ربات هم انجام می‌شوند — پیام را ببندید
              و از منوی ربات ادامه بدهید.
            </div>
          </div>
        )}

        <div className="flex items-center gap-1.5 mb-4">
          {[["subs", "اشتراک‌های من", Package],
            ["plans", "خرید اشتراک", ShoppingCart]].map(([k, label, Icon]) => (
            <button key={k} onClick={() => { setTab(k); buzz("light"); }}
              className="flex-1 py-2.5 rounded-[11px] text-[13px] flex items-center justify-center gap-1.5"
              style={tab === k
                ? { background: "var(--accent-2)", color: "#06090F", fontWeight: 600 }
                : { color: "var(--dim)", border: "1px solid var(--border-2)" }}>
              <Icon size={13} /> {label}
            </button>
          ))}
        </div>

        {busy && !subs && (
          /* شکلِ همان کارتی که می‌آید — نه چرخنده. روی موبایل که
             صفحه کوتاه است، پریدنِ چیدمان بیشتر به چشم می‌آید. */
          <div aria-busy="true">
            {[0, 1].map((i) => (
              <div key={i} className="fx-card p-4 mb-3">
                <div className="flex justify-between mb-3">
                  <Skeleton w="38%" h={13} /><Skeleton w="52px" h={18} />
                </div>
                <Skeleton w="62%" h={11} />
                <div className="mt-2.5"><Skeleton w="100%" h={6} /></div>
                <div className="mt-3"><Skeleton w="44%" h={10} /></div>
                <div className="mt-3"><Skeleton w="100%" h={36} /></div>
              </div>
            ))}
          </div>
        )}

        {tab === "subs" && subs && (
          subs.length === 0 ? (
            <div className="fx-card p-8 text-center" style={{ borderStyle: "dashed" }}>
              <Package size={24} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
              <div className="text-[13px] mb-3" style={{ color: "var(--muted)" }}>
                هنوز اشتراکی ندارید
              </div>
              <button onClick={() => setTab("plans")}
                className="fx-btn px-4 py-2 text-[13px]">دیدن پلن‌ها</button>
            </div>
          ) : subs.map((s) => <SubCard key={s.id} s={s} />)
        )}

        {tab === "plans" && plans && (
          plans.length === 0 ? (
            <div className="fx-card p-8 text-center" style={{ borderStyle: "dashed" }}>
              <div className="text-[13px]" style={{ color: "var(--muted)" }}>
                فعلاً پلنی برای فروش نیست
              </div>
            </div>
          ) : plans.map((p) => <PlanCard key={p.id} p={p} onBuy={buy} />)
        )}

        <div className="text-[11.5px] text-center mt-5 leading-relaxed"
          style={{ color: "var(--muted)" }}>
          <ArrowLeft size={11} className="inline" />{" "}
          همه‌ی این کارها از منوی خودِ ربات هم انجام می‌شوند
        </div>
      </div>
    </div>
  );
}
