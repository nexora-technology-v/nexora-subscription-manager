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

/** آیا این آدرس مینی‌اپ است؟ */
export function isMini() {
  return /^\/app(\/|$)/.test(window.location.pathname || "");
}

/**
 * پلِ تلگرام.
 *
 * اگر مینی‌اپ بیرون از تلگرام باز شود (مثلاً خودِ مالک آدرس را در
 * مرورگر بزند) این شیء نیست. آن حالت باید پیام روشن بدهد، نه خطای
 * جاوااسکریپت روی صفحه‌ی سفید.
 */
const tg = () => (typeof window !== "undefined" ? window.Telegram?.WebApp : null);

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
    setTimeout(() => setCopied(false), 1600);
  };
  const urgent = s.daysLeft !== null && s.daysLeft <= 7;
  return (
    <div className="fx-card p-4 mb-3">
      <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
        <span className="text-[14px] font-semibold text-white">
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
          {copied ? <Check size={13} style={{ color: "var(--ok)" }} /> : <Copy size={13} />}
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
        <span className="text-[14px] font-semibold text-white">{p.name}</span>
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
    if (w) { w.ready(); w.expand(); }
    document.title = "اشتراک من";
    load();
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
      w.openTelegramLink(`https://t.me/${u}?start=plan_${p.id}`);
      w.close();
    } else {
      setErr("برای خرید به ربات برگردید و «خرید اشتراک» را بزنید");
    }
  };

  if (!tg()) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6" dir="rtl">
        <div className="fx-card p-6 text-center" style={{ maxWidth: 380 }}>
          <AlertTriangle size={26} style={{ color: "var(--warn)" }} className="mx-auto mb-3" />
          <div className="text-[14px] font-semibold text-white mb-2">
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
            <div className="text-[16px] font-bold text-white">
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
            <button key={k} onClick={() => setTab(k)}
              className="flex-1 py-2.5 rounded-[11px] text-[13px] flex items-center justify-center gap-1.5"
              style={tab === k
                ? { background: "var(--accent-2)", color: "#06090F", fontWeight: 600 }
                : { color: "var(--dim)", border: "1px solid var(--border-2)" }}>
              <Icon size={13} /> {label}
            </button>
          ))}
        </div>

        {busy && !subs && (
          <div className="flex justify-center py-14">
            <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} />
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
