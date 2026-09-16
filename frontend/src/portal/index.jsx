/**
 * پنل نماینده.
 *
 * چرا اپلیکیشن جداست و از App.jsx جدا افتاده:
 *
 * پنل مدیر همه‌چیز را می‌بیند و ۱۱۴ مسیر مدیریتی صدا می‌زند. اگر
 * پنل نماینده هم همان‌جا می‌نشست، یک import اشتباه یا یک شرطِ
 * جاافتاده کافی بود تا بخشی از پنل مدیر برای نماینده رندر شود.
 * این‌جا اصلاً به آن کد دسترسی ندارد — نه به مسیرهایش، نه به
 * کامپوننت‌هایش.
 */
import React, { useState, useEffect, useCallback } from "react";
import {
  AlertTriangle, Bot, Check, Clock, Copy, Database, FileText, Link2, LogOut,
  Loader2, Package, Plus, Power, QrCode, RefreshCw, Search, ShoppingCart,
  Trash2, TrendingUp, Users, Wallet, X, XCircle,
} from "lucide-react";

import { API_URL } from "../lib/constants";
import { errText, faNum, monoIf } from "../lib/format";
import { isoToJalaliLabel } from "../ui/jalali";
// usePager از کتابخانه‌ی مشترک می‌آید، نه کپیِ محلی: صفحه‌بندی یک
// قاعده است و دو پیاده‌سازی از یک قاعده دیر یا زود از هم جدا
// می‌شوند. این‌جا فقط همان چیزی گرفته می‌شود که ui/jalali هم هست —
// ابزار عمومی، نه کدِ پنل مدیر.
import { NumberInput, StatTile, usePager } from "../ui/index";

const TOKEN_KEY = "nexora_portal_token";

/* نشانی نماینده از آدرس صفحه: /r/<slug>

   import و بعد export، نه `export … from`.

   شکل دوم فقط نام را *عبور* می‌دهد و آن را وارد دامنه‌ی خودِ
   این ماژول نمی‌کند. کد همین فایل دو جا `portalSlug()` را صدا
   می‌زند، پس با آن شکل، پنل نماینده موقع رندر می‌افتاد —
   بیلد هم چیزی نمی‌گفت، چون خودِ نحو درست است. */
import { portalSlug } from "../lib/route.js";
export { portalSlug };

async function api(path, { token, method = "GET", body } = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-Portal-Token": token } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const j = await res.json().catch(() => ({}));
  // errText چون FastAPI برای خطای اعتبارسنجی آرایه‌ای از آبجکت
  // برمی‌گرداند و رندر مستقیمش صفحه را سفید می‌کند.
  if (!res.ok) throw new Error(errText(j.detail, "درخواست ناموفق بود"));
  return j;
}

// ═══════════════════════════════════════════════════════════

function Login({ slug, onIn }) {
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setErr("");
    try {
      const j = await api(`/api/portal/${encodeURIComponent(slug)}/login`,
        { method: "POST", body: { password: pw } });
      localStorage.setItem(TOKEN_KEY, j.token);
      onIn(j.token);
    } catch (e) {
      // پیام خودِ سرور را نشان می‌دهیم: می‌گوید چند تلاش مانده یا
      // چقدر باید صبر کرد. «رمز نادرست» در حالت قفل، بدترین چیزی
      // است که می‌شود گفت.
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4" dir="rtl"
      style={{ background: "radial-gradient(ellipse 60% 50% at 50% 0%, rgba(43,127,214,.15), transparent), var(--bg)" }}>
      <div className="w-full max-w-sm rounded-2xl p-7"
        style={{ background: "var(--surface)", border: "1px solid rgba(90,169,230,.25)" }}>
        <div className="flex flex-col items-center text-center mb-6">
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center font-bold text-[28px] mb-4"
            style={{ background: "linear-gradient(135deg,#2B7FD6,#8FC1EE)", color: "#06090F" }}>N</div>
          <span className="text-white font-bold text-[18px]">پنل نمایندگی</span>
          <span className="text-[13px] mt-1" style={{ color: "var(--muted)" }}>
            {slug ? `نشانی: ${slug}` : "نشانی نامشخص"}
          </span>
        </div>

        <label className="text-[12px] block mb-1.5" style={{ color: "var(--muted)" }}>
          رمز عبور
        </label>
        <input type="password" value={pw} autoFocus className="fx-input w-full"
          style={{ fontFamily: "var(--mono)" }}
          onChange={(e) => setPw(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()} />

        {err && (
          <p className="text-[13px] mt-3 flex items-start gap-1.5"
            style={{ color: "var(--danger)" }}>
            <AlertTriangle size={13} className="shrink-0 mt-0.5" />{err}
          </p>
        )}

        <button onClick={submit} disabled={busy || !pw}
          className="fx-btn w-full py-3 text-[14px] flex items-center justify-center gap-2 mt-4">
          {busy && <Loader2 size={14} className="animate-spin" />} ورود
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════

/**
 * کارت شاخصِ پنل نماینده.
 *
 * حالا همان `StatTile` مشترک است — قدِ یکسان، آیکونِ داخل مربع،
 * و تپش وقتی عدد عوض می‌شود. سیزده جای این صفحه صدایش می‌زنند و
 * هیچ‌کدام لازم نبود عوض شوند.
 *
 * `StatTile` از `ui/index` می‌آید که ابزارِ عمومی است، نه کدِ پنل
 * مدیر — همان مرزی که این فایل از اول داشته.
 */
function Stat({ icon, label, value, hint, color, spark, sparkColor }) {
  return (
    <StatTile icon={icon} label={label} value={value} hint={hint}
      color={color || "var(--text)"} tone={color || "var(--accent-2)"}
      spark={spark} sparkColor={sparkColor} />
  );
}

function RenewBox({ token, row, plans, onDone, onClose }) {
  const [months, setMonths] = useState(1);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  // قیمت را از همان نرخی می‌گیریم که مالک تعریف کرده. این فقط
  // نمایش است — سرور خودش دوباره حساب می‌کند و عددِ سرور ملاک است.
  const tier = (plans?.plans || []).find((p) => p.gb === row.gb)
    || (plans?.plans || []).find((p) => p.gb > row.gb)
    || (plans?.plans || [])[0];
  const extra = row.devices > 1 ? row.devices - 1 : 0;
  const each = tier ? tier.price + (tier.perDevice || 0) * extra : null;
  const total = each === null ? null : each * months;

  const go = async () => {
    setBusy(true);
    setErr("");
    try {
      const j = await api("/api/portal/renew", {
        token, method: "POST", body: { email: row.email, months },
      });
      onDone(`${row.email} برای ${faNum(months)} ماه تمدید شد`
        + (j.charged ? ` — ${faNum(j.charged)} تومان` : ""));
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 3000, display: "flex",
      alignItems: "center", justifyContent: "center", padding: 16,
      background: "rgba(0,0,0,.6)",
    }} onClick={onClose}>
      <div className="fx-card p-5" style={{ width: 360, maxWidth: "100%" }}
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <div className="text-[14px] font-semibold text-white">تمدید کانفیگ</div>
          <button onClick={onClose} className="fx-ico-btn"
            style={{ width: 28, height: 28 }} aria-label="بستن">
            <X size={13} />
          </button>
        </div>

        <div className="text-[13px] mb-3" dir="ltr"
          style={{ fontFamily: "var(--mono)", color: "var(--dim)" }}>
          {row.email}
        </div>

        <label className="text-[12px] block mb-1.5" style={{ color: "var(--muted)" }}>
          چند ماه
        </label>
        <div className="flex gap-1.5 flex-wrap mb-3">
          {[1, 2, 3, 6, 12].map((m) => (
            <button key={m} onClick={() => setMonths(m)}
              className="px-3 py-2 rounded-lg text-[13px]"
              style={{
                background: months === m ? "rgba(43,127,214,.18)" : "transparent",
                border: `1px solid ${months === m ? "rgba(43,127,214,.45)" : "var(--border)"}`,
                color: months === m ? "var(--accent-2)" : "var(--muted)",
              }}>
              {faNum(m)}
            </button>
          ))}
        </div>

        {total !== null && (
          <div className="rounded-xl p-3 mb-3 text-[13px]"
            style={{ background: "var(--surface-3)", color: "var(--dim)" }}>
            حدود <b style={{ color: "var(--accent-2)" }}>{faNum(total)}</b> تومان
            {extra > 0 && (
              <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
                شامل {faNum(extra)} کاربر اضافه
              </div>
            )}
          </div>
        )}

        {err && (
          <p className="text-[13px] mb-3 flex items-start gap-1.5"
            style={{ color: "var(--danger)" }}>
            <AlertTriangle size={13} className="shrink-0 mt-0.5" />{err}
          </p>
        )}

        <button onClick={go} disabled={busy}
          className="fx-btn w-full py-2.5 text-[13px] flex items-center justify-center gap-2">
          {busy && <Loader2 size={13} className="animate-spin" />} تمدید کن
        </button>
      </div>
    </div>
  );
}


/**
 * تأیید حذف.
 *
 * دو حالت کاملاً متفاوت است و کاربر باید *پیش* از زدن دکمه بداند
 * کدام‌یک را دارد انجام می‌دهد:
 *
 *   • کانفیگی که هنوز مصرف نشده — اعتبارش برمی‌گردد. همان حالتی که
 *     مشتری همان لحظه پشیمان می‌شود.
 *   • کانفیگی که مصرف داشته — دوره‌اش را کار کرده، پس بدهی‌اش می‌ماند
 *     و اعتباری برنمی‌گردد.
 *
 * نوشتنش این‌جا مهم است: بدون آن، نماینده فکر می‌کند حذف یعنی
 * پس‌گرفتن پول، و وقتی برنگشت حس می‌کند چیزی دزدیده شده.
 */
function DropBox({ token, config, onDone, onClose }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const fresh = !config.used || config.used <= 0;

  const go = async () => {
    setBusy(true); setErr("");
    try {
      const j = await api(`/api/portal/config/${encodeURIComponent(config.email)}`,
                          { token, method: "DELETE" });
      onDone(j);
      onClose();
    } catch (e) {
      setErr(e.message);
    } finally { setBusy(false); }
  };

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 3000, display: "flex",
      alignItems: "center", justifyContent: "center", padding: 16,
      background: "rgba(0,0,0,.6)", overflowY: "auto",
    }} onClick={onClose}>
      <div className="fx-card p-5" style={{ width: 380, maxWidth: "100%" }}
        onClick={(e) => e.stopPropagation()}>
        <div className="text-[14px] font-semibold text-white mb-2">
          حذف کانفیگ
        </div>
        <div dir="ltr" className="text-[13px] mb-3"
          style={{ fontFamily: "var(--mono)", color: "var(--dim)",
                   wordBreak: "break-all" }}>
          {config.email}
        </div>

        <div className="rounded-xl p-3 mb-3 text-[13px] leading-relaxed"
          style={{
            background: fresh ? "rgba(52,211,153,.08)" : "rgba(251,191,36,.08)",
            border: `1px solid ${fresh ? "rgba(52,211,153,.25)" : "rgba(251,191,36,.3)"}`,
            color: "var(--dim)",
          }}>
          {fresh ? (
            <>این کانفیگ هنوز هیچ مصرفی نداشته، پس <b style={{ color: "var(--ok)" }}>
            اعتبارش به شما برمی‌گردد</b>.</>
          ) : (
            <>این کانفیگ مصرف داشته، پس دوره‌اش را کار کرده و
            <b style={{ color: "var(--warn)" }}> اعتباری برنمی‌گردد</b>.
            اگر فقط می‌خواهید مشتری وصل نشود، به‌جای حذف «غیرفعال» را بزنید.</>
          )}
        </div>

        <div className="text-[12px] mb-4" style={{ color: "var(--muted)" }}>
          لینک اشتراک این مشتری از کار می‌افتد و برگشت‌پذیر نیست.
        </div>

        {err && (
          <div className="text-[13px] mb-3" style={{ color: "var(--danger)" }}>{err}</div>
        )}

        <div className="flex items-center gap-2">
          <button onClick={go} disabled={busy}
            className="fx-btn flex-1 py-2.5 text-[13px] flex items-center justify-center gap-1.5"
            style={{ background: "var(--danger)", borderColor: "var(--danger)" }}>
            {busy ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
            حذف کن
          </button>
          <button onClick={onClose} className="fx-btn-g px-4 py-2.5 text-[13px]">
            انصراف
          </button>
        </div>
      </div>
    </div>
  );
}


function NewBox({ token, plans, slug, onDone, onClose }) {
  const tiers = plans?.plans || [];
  const [gb, setGb] = useState(tiers[0] ? tiers[0].gb : 0);
  const [days, setDays] = useState(30);
  const [onUse, setOnUse] = useState(false);
  const [devices, setDevices] = useState(1);
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [made, setMade] = useState(null);

  // همان گردکردنی که سرور برای صورتحساب به کار می‌برد: نیم‌ماه به
  // بالا. اگر این‌جا جور دیگری حساب می‌شد، عددی که به نماینده نشان
  // می‌دهیم با عددی که از اعتبارش کم می‌شود فرق می‌کرد.
  const billMonths = Math.max(1, Math.round(days / 30));
  const tier = tiers.find((x) => x.gb === gb);
  const extra = devices > 1 ? devices - 1 : 0;
  const total = tier
    ? (tier.price + (tier.perDevice || 0) * extra) * billMonths : null;

  const go = async () => {
    setBusy(true);
    setErr("");
    try {
      const j = await api("/api/portal/config", {
        token, method: "POST",
        body: { gb, days, devices, label, startOnFirstUse: onUse },
      });
      setMade(j);
      onDone();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 3000, display: "flex",
      alignItems: "center", justifyContent: "center", padding: 16,
      background: "rgba(0,0,0,.6)", overflowY: "auto",
    }} onClick={onClose}>
      <div className="fx-card p-5" style={{ width: 380, maxWidth: "100%" }}
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <div className="text-[14px] font-semibold text-white">کانفیگ تازه</div>
          <button onClick={onClose} className="fx-ico-btn"
            style={{ width: 28, height: 28 }} aria-label="بستن">
            <X size={13} />
          </button>
        </div>

        {made ? (
          <>
            <div className="rounded-xl p-3 mb-3"
              style={{ background: "rgba(52,211,153,.08)",
                       border: "1px solid rgba(52,211,153,.25)" }}>
              <div className="text-[13px] mb-2" style={{ color: "var(--ok)" }}>
                ساخته شد
              </div>
              <div dir="ltr" className="text-[13px]"
                style={{ fontFamily: "var(--mono)", color: "var(--dim)",
                         wordBreak: "break-all" }}>
                {made.email}
              </div>
            </div>

            {/* گروه ننشست — کانفیگ ساخته شده و پولش هم کم شده، ولی
                در فهرست نماینده و در صورتحساب پیدا نمی‌شود. بدون این
                پیام، نماینده فقط می‌دید که کانفیگش «گم شده». */}
            {made.groupWarning && (
              <div className="rounded-xl p-3 mb-3 text-[13px] leading-relaxed"
                style={{ background: "rgba(251,191,36,.08)",
                         border: "1px solid rgba(251,191,36,.3)",
                         color: "var(--warn)" }}>
                {made.groupWarning}
              </div>
            )}

            {made.startOnFirstUse && (
              <div className="rounded-xl p-3 mb-3 text-[13px] leading-relaxed"
                style={{ background: "var(--surface-3)", color: "var(--dim)" }}>
                شمارش از اولین اتصال شروع می‌شود — تا وقتی مشتری وصل
                نشده، «شروع‌نشده» می‌ماند و از {faNum(made.days)} روزش
                کم نمی‌شود.
              </div>
            )}

            {made.subUrl && (
              <div className="mb-3">
                <div className="text-[12px] mb-1.5" style={{ color: "var(--muted)" }}>
                  لینک اشتراک
                </div>
                <div className="flex items-center gap-1.5">
                  <div dir="ltr" className="fx-input text-[12px] flex-1"
                    style={{ fontFamily: "var(--mono)", overflow: "hidden",
                             textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {made.subUrl}
                  </div>
                  <button className="fx-ico-btn" style={{ width: 32, height: 32 }}
                    aria-label="کپی"
                    onClick={() => navigator.clipboard?.writeText(made.subUrl)}>
                    <Copy size={13} />
                  </button>
                </div>
              </div>
            )}
            <button onClick={onClose} className="fx-btn w-full py-2.5 text-[13px]">
              بستن
            </button>
          </>
        ) : (
          <>
            {/* نام مشتری.
                پیشوند را نماینده تعیین نمی‌کند — برندِ صفحه‌ی اشتراک از
                همان تکه خوانده می‌شود. ولی بخشِ دوم مالِ خودش است، تا
                بداند کدام کانفیگ مالِ کدام مشتری است. تا امروز هشت
                نویسه‌ی تصادفی بود و هیچ معنایی نداشت. */}
            <label className="text-[12px] block mb-1.5" style={{ color: "var(--muted)" }}>
              نام مشتری <span style={{ opacity: .6 }}>(اختیاری)</span>
            </label>
            <input className="fx-input w-full mb-1" dir="ltr" value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="hossein" maxLength={24} />
            <div className="text-[11.5px] mb-3 leading-relaxed"
              style={{ color: label && !/[A-Za-z0-9]/.test(label)
                ? "var(--warn)" : "var(--muted)" }}>
              {label && !/[A-Za-z0-9]/.test(label)
                ? "فقط حروف انگلیسی و عدد پذیرفته می‌شود — با این نام، شناسه‌ی تصادفی ساخته می‌شود"
                : <>شناسه‌ای که ساخته می‌شود: <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>
                    {slug}_{label.replace(/[^A-Za-z0-9-]+/g, "-").replace(/^-+|-+$/g, "").toLowerCase() || "……"}
                  </span></>}
            </div>

            <label className="text-[12px] block mb-1.5" style={{ color: "var(--muted)" }}>
              حجم
            </label>
            <div className="flex gap-1.5 flex-wrap mb-3">
              {tiers.map((x) => (
                <button key={x.gb} onClick={() => setGb(x.gb)}
                  className="px-3 py-2 rounded-lg text-[13px]"
                  style={{
                    background: gb === x.gb ? "rgba(43,127,214,.18)" : "transparent",
                    border: `1px solid ${gb === x.gb ? "rgba(43,127,214,.45)" : "var(--border)"}`,
                    color: gb === x.gb ? "var(--accent-2)" : "var(--muted)",
                  }}>
                  {x.label}
                </button>
              ))}
              {!tiers.length && (
                <span className="text-[13px]" style={{ color: "var(--warn)" }}>
                  هنوز نرخی برای شما تعریف نشده
                </span>
              )}
            </div>

            {/* روز، نه فقط ماه. دکمه‌های میان‌بر برای حالت‌های
                معمول می‌مانند، ولی عدد را هم می‌شود دستی زد —
                «۴۵ روز» یا «۱۰ روز» بین پله‌های ماه گیر نکند. */}
            <label className="text-[12px] block mb-1.5" style={{ color: "var(--muted)" }}>
              مدت اشتراک <span style={{ opacity: .6 }}>(روز)</span>
            </label>
            <div className="flex gap-1.5 flex-wrap mb-2">
              {[7, 30, 60, 90, 180, 365].map((d) => (
                <button key={d} onClick={() => setDays(d)}
                  className="px-3 py-2 rounded-lg text-[13px]"
                  style={{
                    background: days === d ? "rgba(43,127,214,.18)" : "transparent",
                    border: `1px solid ${days === d ? "rgba(43,127,214,.45)" : "var(--border)"}`,
                    color: days === d ? "var(--accent-2)" : "var(--muted)",
                  }}>
                  {faNum(d)}
                </button>
              ))}
            </div>
            <NumberInput min="1" max="366" value={days}
              onChange={(e) => setDays(Math.max(1, Math.min(366, Number(e.target.value) || 1)))}
              className="fx-input w-full text-center mb-1"
              style={{ fontFamily: "var(--mono)" }} />
            <div className="text-[11.5px] mb-3" style={{ color: "var(--muted)" }}>
              برای حساب‌کردن مبلغ، {faNum(days)} روز = {faNum(billMonths)} ماه
            </div>

            {/* شروع از اولین اتصال — همان چیزی که خود پنل ۳x-ui دارد */}
            <label className="flex items-start gap-2.5 mb-3 cursor-pointer">
              <input type="checkbox" checked={onUse}
                onChange={(e) => setOnUse(e.target.checked)}
                style={{ accentColor: "var(--accent)", marginTop: 3 }} />
              <span>
                <span className="text-[13px]" style={{ color: "var(--dim)" }}>
                  شمارش از اولین اتصال
                </span>
                <span className="block text-[11.5px] mt-0.5"
                  style={{ color: "var(--muted)" }}>
                  اگر مشتری چند روز دیرتر وصل شود، از سهمش کم نمی‌شود.
                  تا وصل نشده «شروع‌نشده» نشان داده می‌شود.
                </span>
              </span>
            </label>

            <label className="text-[12px] block mb-1.5" style={{ color: "var(--muted)" }}>
              تعداد کاربر هم‌زمان
            </label>
            <NumberInput min="1" max="20" value={devices}
              onChange={(e) => setDevices(Math.max(1, Math.min(20, Number(e.target.value) || 1)))}
              className="fx-input w-full text-center mb-3"
              style={{ fontFamily: "var(--mono)" }}  />

            {total !== null && (
              <div className="rounded-xl p-3 mb-3 text-[13px]"
                style={{ background: "var(--surface-3)", color: "var(--dim)" }}>
                حدود <b style={{ color: "var(--accent-2)" }}>{faNum(total)}</b> تومان
                {extra > 0 && (
                  <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
                    شامل {faNum(extra)} کاربر اضافه
                  </div>
                )}
              </div>
            )}

            {err && (
              <p className="text-[13px] mb-3 flex items-start gap-1.5"
                style={{ color: "var(--danger)" }}>
                <AlertTriangle size={13} className="shrink-0 mt-0.5" />{err}
              </p>
            )}

            <button onClick={go} disabled={busy || !tiers.length}
              className="fx-btn w-full py-2.5 text-[13px] flex items-center justify-center gap-2">
              {busy && <Loader2 size={13} className="animate-spin" />} بساز
            </button>
          </>
        )}
      </div>
    </div>
  );
}


function BotBox({ token, onClose, onNote }) {
  const [st, setSt] = useState(null);
  const [tok, setTok] = useState("");
  const [brand, setBrand] = useState("");
  const [support, setSupport] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    try {
      const j = await api("/api/portal/bot", { token });
      setSt(j);
      setBrand(j.brand || "");
      setSupport(j.supportUsername || "");
    } catch (e) {
      setErr(e.message);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setBusy(true);
    setErr("");
    try {
      const j = await api("/api/portal/bot", {
        token, method: "POST", body: { token: tok.trim() },
      });
      setTok("");
      onNote(`ربات @${j.username} وصل شد — ${j.note}`);
      load();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const saveBrand = async () => {
    setBusy(true);
    setErr("");
    try {
      await api("/api/portal/brand", {
        token, method: "POST",
        body: { brand, support_username: support },
      });
      onNote("برند ذخیره شد");
      load();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const drop = async () => {
    setBusy(true);
    try {
      await api("/api/portal/bot", { token, method: "DELETE" });
      onNote("ربات جدا شد");
      load();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 3000, display: "flex",
      alignItems: "center", justifyContent: "center", padding: 16,
      background: "rgba(0,0,0,.6)", overflowY: "auto",
    }} onClick={onClose}>
      <div className="fx-card p-5" style={{ width: 420, maxWidth: "100%" }}
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <div className="text-[14px] font-semibold text-white">ربات تلگرام شما</div>
          <button onClick={onClose} className="fx-ico-btn"
            style={{ width: 28, height: 28 }} aria-label="بستن">
            <X size={13} />
          </button>
        </div>

        {st?.hasBot ? (
          <div className="rounded-xl p-3 mb-4 flex items-center justify-between gap-2"
            style={{ background: "rgba(52,211,153,.08)",
                     border: "1px solid rgba(52,211,153,.25)" }}>
            <div>
              <div className="text-[13px]" style={{ color: "var(--ok)" }}>
                وصل است
              </div>
              <div dir="ltr" className="text-[13px] mt-0.5"
                style={{ fontFamily: "var(--mono)", color: "var(--dim)" }}>
                @{st.username}
              </div>
            </div>
            <button onClick={drop} disabled={busy} className="fx-ico-btn"
              style={{ width: 32, height: 32 }} aria-label="جداکردن ربات"
              title="جداکردن">
              <Trash2 size={13} />
            </button>
          </div>
        ) : (
          <p className="text-[13px] mb-4 leading-relaxed"
            style={{ color: "var(--muted)" }}>
            یک ربات از <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>@BotFather</span>
            {" "}بسازید و توکنش را این‌جا بگذارید. مشتری‌های شما با آن خرید
            می‌کنند و برند خودتان را می‌بینند.
          </p>
        )}

        <label className="text-[12px] block mb-1.5" style={{ color: "var(--muted)" }}>
          {st?.hasBot ? "جایگزینی توکن" : "توکن ربات"}
        </label>
        <input dir="ltr" value={tok} onChange={(e) => setTok(e.target.value)}
          placeholder="123456:ABC-DEF..."
          className="fx-input w-full mb-2 text-[13px]"
          style={{ fontFamily: "var(--mono)" }} />
        <button onClick={save} disabled={busy || !tok.trim()}
          className="fx-btn w-full py-2.5 text-[13px] flex items-center
                     justify-center gap-2 mb-4">
          {busy && <Loader2 size={13} className="animate-spin" />} ثبت توکن
        </button>

        <div className="pt-4" style={{ borderTop: "1px solid var(--border)" }}>
          <label className="text-[12px] block mb-1.5" style={{ color: "var(--muted)" }}>
            نام برند شما
          </label>
          <input value={brand} onChange={(e) => setBrand(e.target.value)}
            className="fx-input w-full mb-2 text-[13px]" />

          <label className="text-[12px] block mb-1.5" style={{ color: "var(--muted)" }}>
            یوزرنیم پشتیبانی
          </label>
          <input dir="ltr" value={support}
            onChange={(e) => setSupport(e.target.value.replace("@", ""))}
            placeholder="yoursupport"
            className="fx-input w-full mb-2 text-[13px]"
            style={{ fontFamily: "var(--mono)" }} />

          <button onClick={saveBrand} disabled={busy}
            className="fx-btn-g w-full py-2.5 text-[13px]">
            ذخیره‌ی برند
          </button>
        </div>

        {err && (
          <p className="text-[13px] mt-3 flex items-start gap-1.5"
            style={{ color: "var(--danger)" }}>
            <AlertTriangle size={13} className="shrink-0 mt-0.5" />{err}
          </p>
        )}
      </div>
    </div>
  );
}


function PlansBox({ token, onClose, onNote }) {
  const [rows, setRows] = useState(null);
  const [hasBot, setHasBot] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    try {
      const j = await api("/api/portal/bot-plans", { token });
      setRows(j.plans || []);
      setHasBot(!!j.hasBot);
    } catch (e) { setErr(e.message); }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const patch = (i, p) => setRows(rows.map((r, k) => (k === i ? { ...r, ...p } : r)));
  const add = () => setRows([...(rows || []), {
    name: "", gb: 50, days: 30, ip_limit: 2, price: 0, is_active: true,
  }]);
  const drop = (i) => setRows(rows.filter((_, k) => k !== i));

  const save = async () => {
    setBusy(true);
    setErr("");
    try {
      const j = await api("/api/portal/bot-plans", {
        token, method: "PUT", body: { plans: rows },
      });
      onNote(`${faNum(j.count)} پلن ذخیره شد`);
      load();
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 3000, display: "flex",
      alignItems: "flex-start", justifyContent: "center", padding: 16,
      background: "rgba(0,0,0,.6)", overflowY: "auto",
    }} onClick={onClose}>
      <div className="fx-card p-5" style={{ width: 620, maxWidth: "100%", marginTop: 24 }}
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-2">
          <div className="text-[14px] font-semibold text-white">
            پلن‌های ربات شما
          </div>
          <button onClick={onClose} className="fx-ico-btn"
            style={{ width: 28, height: 28 }} aria-label="بستن">
            <X size={13} />
          </button>
        </div>

        <p className="text-[12px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
          این قیمتی است که به مشتری خودتان می‌فروشید. آنچه بابت هر کانفیگ به
          ما می‌دهید جداست و از نرخ‌های گروه شما می‌آید.
        </p>

        {!hasBot && (
          <div className="rounded-xl p-3 mb-4 text-[12px]"
            style={{ background: "rgba(251,191,36,.07)",
                     border: "1px solid rgba(251,191,36,.22)",
                     color: "var(--warn)" }}>
            هنوز رباتی وصل نکرده‌اید — این پلن‌ها جایی نمایش داده نمی‌شوند.
          </div>
        )}

        {!rows ? (
          <p className="text-[13px] py-6 text-center" style={{ color: "var(--muted)" }}>
            در حال بارگذاری…
          </p>
        ) : (
          <>
            {rows.map((r, i) => (
              <div key={i} className="rounded-xl p-3 mb-2.5"
                style={{ background: "var(--surface-3)",
                         border: "1px solid var(--border)" }}>
                <div className="flex items-center gap-2 mb-2">
                  <input value={r.name} placeholder="نام پلن"
                    onChange={(e) => patch(i, { name: e.target.value })}
                    className="fx-input text-[13px] flex-1" />
                  <button onClick={() => patch(i, { is_active: !r.is_active })}
                    className="fx-ico-btn" style={{ width: 30, height: 30 }}
                    title={r.is_active ? "فعال" : "غیرفعال"}
                    aria-label={r.is_active ? "غیرفعال کن" : "فعال کن"}>
                    <Power size={12} style={{
                      color: r.is_active ? "var(--ok)" : "var(--muted)" }} />
                  </button>
                  <button onClick={() => drop(i)} className="fx-ico-btn"
                    style={{ width: 30, height: 30 }} aria-label="حذف پلن">
                    <Trash2 size={12} />
                  </button>
                </div>
                <div className="grid grid-cols-4 gap-2">
                  {[["gb", "حجم (GB)"], ["days", "روز"],
                    ["ip_limit", "کاربر"], ["price", "قیمت"]].map(([k, lbl]) => (
                    <div key={k}>
                      <label className="text-[11px] block mb-1"
                        style={{ color: "var(--muted)" }}>{lbl}</label>
                      <NumberInput min="0" value={r[k] ?? 0}
                        onChange={(e) => patch(i, { [k]: Number(e.target.value) || 0 })}
                        className="fx-input text-[13px] text-center"
                        style={{ fontFamily: "var(--mono)" }}  />
                    </div>
                  ))}
                </div>
                <div className="text-[11px] mt-1.5" style={{ color: "var(--muted)" }}>
                  حجم ۰ یعنی نامحدود · کاربر ۰ یعنی بدون محدودیت
                </div>
              </div>
            ))}

            <button onClick={add}
              className="fx-btn-g w-full py-2.5 text-[13px] flex items-center
                         justify-center gap-1.5 mb-3">
              <Plus size={13} /> پلن تازه
            </button>

            {err && (
              <p className="text-[13px] mb-3 flex items-start gap-1.5"
                style={{ color: "var(--danger)" }}>
                <AlertTriangle size={13} className="shrink-0 mt-0.5" />{err}
              </p>
            )}

            <button onClick={save} disabled={busy}
              className="fx-btn w-full py-2.5 text-[13px] flex items-center
                         justify-center gap-2">
              {busy && <Loader2 size={13} className="animate-spin" />} ذخیره
            </button>
          </>
        )}
      </div>
    </div>
  );
}


function OrdersBox({ token, onClose, onNote }) {
  const [rows, setRows] = useState(null);
  const [cut, setCut] = useState(false);
  const [tab, setTab] = useState("open");
  const [busy, setBusy] = useState(0);
  const [err, setErr] = useState("");
  const [shot, setShot] = useState(null);
  const [rejecting, setRejecting] = useState(null);
  const [reason, setReason] = useState("");

  const load = useCallback(async () => {
    try {
      const j = await api(`/api/portal/orders?status=${tab}`, { token });
      setCut(!!j.truncated);
      setRows(j.orders || []);
    } catch (e) { setErr(e.message); }
  }, [token, tab]);

  useEffect(() => { load(); }, [load]);

  // مسیرها صریح‌اند، نه ساخته‌شده از رشته.
  //
  // `/order/${id}/${what}` کار می‌کرد ولی تست درزها نمی‌توانست
  // بررسی کند مسیری که صدا می‌زنیم واقعاً وجود دارد — و آن تست
  // همان چیزی است که جلوی صداکردن مسیر ناموجود را می‌گیرد.
  const act = async (id, what, body) => {
    setBusy(id);
    setErr("");
    try {
      const path = what === "approve"
        ? `/api/portal/order/${id}/approve`
        : `/api/portal/order/${id}/reject`;
      await api(path, { token, method: "POST", body });
      onNote(what === "approve"
        ? `سفارش #${faNum(id)} تایید شد — کانفیگ برای مشتری رفت`
        : `سفارش #${faNum(id)} رد شد`);
      setRejecting(null);
      setReason("");
      load();
    } catch (e) { setErr(e.message); } finally { setBusy(0); }
  };

  // رسید را با توکن نشست می‌گیریم، نه با آدرس مستقیم: آن آدرس
  // توکن ربات را در خودش دارد.
  const openShot = async (id) => {
    try {
      const res = await fetch(`${API_URL}/api/portal/order/${id}/receipt`, {
        headers: { "X-Portal-Token": token },
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(errText(j.detail, "رسید باز نشد"));
      }
      setShot(URL.createObjectURL(await res.blob()));
    } catch (e) { setErr(e.message); }
  };

  // صفحه‌بندی شماره‌دار — فهرست سفارش‌ها با گذر زمان بی‌سقف
  // می‌شود و تا امروز همه‌اش یک‌جا ریخته می‌شد.
  const { shown: pageOrders, pager: ordersPager } = usePager(rows || [], 12);

  const TABS = [["open", "در انتظار"], ["approved", "تاییدشده"],
                ["rejected", "ردشده"]];

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 3000, display: "flex",
      alignItems: "flex-start", justifyContent: "center", padding: 16,
      background: "rgba(0,0,0,.6)", overflowY: "auto",
    }} onClick={onClose}>
      <div className="fx-card p-5" style={{ width: 640, maxWidth: "100%", marginTop: 24 }}
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <div className="text-[14px] font-semibold text-white">
            سفارش‌های مشتری‌های شما
          </div>
          <button onClick={onClose} className="fx-ico-btn"
            style={{ width: 28, height: 28 }} aria-label="بستن">
            <X size={13} />
          </button>
        </div>

        <div className="flex gap-1.5 mb-4">
          {TABS.map(([k, lbl]) => (
            <button key={k} onClick={() => { setTab(k); setRows(null); }}
              className="px-3 py-2 rounded-lg text-[13px]"
              style={{
                background: tab === k ? "rgba(43,127,214,.18)" : "transparent",
                border: `1px solid ${tab === k ? "rgba(43,127,214,.45)" : "var(--border)"}`,
                color: tab === k ? "var(--accent-2)" : "var(--muted)",
              }}>
              {lbl}
            </button>
          ))}
        </div>

        {err && (
          <p className="text-[13px] mb-3 flex items-start gap-1.5"
            style={{ color: "var(--danger)" }}>
            <AlertTriangle size={13} className="shrink-0 mt-0.5" />{err}
          </p>
        )}

        {!rows ? (
          <p className="text-[13px] py-6 text-center" style={{ color: "var(--muted)" }}>
            در حال بارگذاری…
          </p>
        ) : !rows.length ? (
          <p className="text-[13px] py-6 text-center" style={{ color: "var(--muted)" }}>
            {tab === "open" ? "سفارشی در انتظار نیست" : "چیزی این‌جا نیست"}
          </p>
        ) : pageOrders.map((o) => (
          <div key={o.id} className="rounded-xl p-3.5 mb-2.5"
            style={{ background: "var(--surface-3)",
                     border: "1px solid var(--border)" }}>
            <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
              <div>
                <span className="text-[13px] text-white font-semibold">
                  {o.customer}
                </span>
                <span className="text-[12px] mr-2" style={{ color: "var(--muted)" }}>
                  #{faNum(o.id)} · {o.planName}
                </span>
              </div>
              <span className="text-[14px] font-bold"
                style={{ color: "var(--accent-2)" }}>
                {faNum(o.amount)} تومان
              </span>
            </div>

            <div className="text-[12px] mb-2" style={{ color: "var(--muted)" }}>
              {o.kind === "renew" ? "تمدید" : o.kind === "topup" ? "شارژ کیف پول" : "خرید تازه"}
              {o.paidFrom === "wallet" ? " · از کیف پول" : " · کارت به کارت"}
              {o.gb !== null && o.gb !== undefined
                && ` · ${o.gb === 0 ? "نامحدود" : `${faNum(o.gb)} گیگ`}`}
            </div>

            {o.receiptText && (
              <div className="text-[12px] rounded-lg p-2 mb-2"
                style={{ background: "rgba(0,0,0,.2)", color: "var(--dim)" }}>
                {o.receiptText}
              </div>
            )}

            {o.note && (
              <div className="text-[12px] mb-2" style={{ color: "var(--muted)" }}>
                {o.note}
              </div>
            )}

            {rejecting === o.id ? (
              <div className="flex items-center gap-1.5 flex-wrap">
                <input value={reason} autoFocus
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="دلیل رد — مشتری همین را می‌بیند"
                  className="fx-input text-[13px] flex-1" style={{ minWidth: 200 }} />
                <button disabled={busy === o.id || !reason.trim()}
                  onClick={() => act(o.id, "reject", { reason })}
                  className="fx-btn px-3 py-2 text-[13px]">بفرست</button>
                <button onClick={() => { setRejecting(null); setReason(""); }}
                  className="fx-btn-g px-3 py-2 text-[13px]">انصراف</button>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 flex-wrap">
                {o.hasReceipt && (
                  <button onClick={() => openShot(o.id)}
                    className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1">
                    <FileText size={12} /> دیدن رسید
                  </button>
                )}
                {o.status !== "approved" && (
                  <>
                    <button disabled={busy === o.id}
                      onClick={() => act(o.id, "approve")}
                      className="fx-btn px-3 py-2 text-[13px] flex items-center gap-1">
                      {busy === o.id ? <Loader2 size={12} className="animate-spin" />
                        : <Check size={12} />} تایید و ساخت کانفیگ
                    </button>
                    {o.status !== "rejected" && (
                      <button onClick={() => setRejecting(o.id)}
                        className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1">
                        <XCircle size={12} /> رد
                      </button>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        ))}

        {ordersPager}

        {/* سقف خوردنِ بی‌صدا بدتر از نبودِ فهرست است: نماینده فکر
            می‌کند همین‌ها همه‌ی سفارش‌هایش است. */}
        {cut && (
          <p className="text-[12px] text-center pt-2"
            style={{ color: "var(--warn)" }}>
            فقط تازه‌ترین سفارش‌ها نشان داده می‌شود — قدیمی‌ترها در
            «گزارش فروش» پنل مدیر هست.
          </p>
        )}
      </div>

      {shot && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 3100, display: "flex",
          alignItems: "center", justifyContent: "center", padding: 16,
          background: "rgba(0,0,0,.85)",
        }} onClick={(e) => { e.stopPropagation(); setShot(null); }}>
          <img src={shot} alt="رسید پرداخت"
            style={{ maxWidth: "100%", maxHeight: "90vh", borderRadius: 12 }} />
        </div>
      )}
    </div>
  );
}


/**
 * مشخصات یک کاربر — و مهم‌تر از آن، چیزی که به مشتری تحویل می‌شود.
 *
 * سه تب، مثل خود پنل x-ui: اول چیزی که همین حالا لازم است (لینک و
 * کیوآر)، بعد مصرف، بعد مشخصات. ترتیبشان عمدی است — نماینده این
 * پنجره را برای تحویل باز می‌کند، نه برای تماشا.
 */
function ConfigBox({ token, row, onClose, onRenew, onToggle }) {
  const [tab, setTab] = useState("deliver");
  const [qr, setQr] = useState(null);
  const [qrBusy, setQrBusy] = useState(false);
  const [qrErr, setQrErr] = useState("");
  const [copied, setCopied] = useState("");

  const copy = (text, what) => {
    navigator.clipboard?.writeText(text);
    setCopied(what);
    setTimeout(() => setCopied(""), 1600);
  };

  // کیوآر از سمت سرور و محلی ساخته می‌شود: لینک اشتراک عملاً رمز
  // مشتری است و نباید به هیچ سرویس بیرونی برود.
  const showQr = async () => {
    if (qr) { setQr(null); return; }
    setQrBusy(true);
    setQrErr("");
    try {
      const res = await fetch(
        `${API_URL}/api/portal/config/${encodeURIComponent(row.email)}/qr`,
        { headers: { "X-Portal-Token": token } });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(errText(j.detail, "کیوآر ساخته نشد"));
      }
      setQr(URL.createObjectURL(await res.blob()));
    } catch (e) { setQrErr(e.message); } finally { setQrBusy(false); }
  };

  const pct = row.usagePct;
  const bar = pct === null || pct === undefined ? null : Math.min(100, pct);
  const barColor = bar === null ? "var(--accent-2)"
    : bar >= 90 ? "var(--danger)" : bar >= 80 ? "var(--warn)" : "var(--accent-2)";

  const expired = row.daysLeft !== null && row.daysLeft !== undefined
    && row.daysLeft < 0;

  const TABS = [["deliver", "تحویل به مشتری"], ["usage", "مصرف"],
                ["info", "مشخصات"]];

  const Rowline = ({ k, v, tone }) => (
    <div className="flex items-center justify-between py-2"
      style={{ borderBottom: "1px solid var(--border)" }}>
      <span className="text-[13px]" style={{ color: "var(--muted)" }}>{k}</span>
      <span className="text-[13px]" style={{ color: tone || "var(--dim)" }}>{v}</span>
    </div>
  );

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 3000, display: "flex",
      alignItems: "flex-start", justifyContent: "center", padding: 16,
      background: "rgba(0,0,0,.62)", overflowY: "auto",
    }} onClick={onClose}>
      <div className="fx-card" style={{
        width: 470, maxWidth: "100%", marginTop: 24, padding: 0,
        overflow: "hidden",
      }} onClick={(e) => e.stopPropagation()}>

        {/* سربرگ */}
        <div className="px-5 pt-4 pb-3">
          <div className="flex items-start justify-between gap-3 mb-2">
            <div className="min-w-0">
              <div dir="ltr" className="text-[15px] font-semibold text-white"
                style={{ fontFamily: "var(--mono)", wordBreak: "break-all" }}>
                {row.email}
              </div>
              <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                <span className="fx-pill" style={{
                  background: row.active ? "rgba(52,211,153,.14)" : "var(--surface-3)",
                  color: row.active ? "var(--ok)" : "var(--muted)",
                }}>
                  {row.active ? "فعال" : "غیرفعال"}
                </span>
                {expired && (
                  <span className="fx-pill" style={{
                    background: "rgba(248,113,113,.14)", color: "var(--danger)" }}>
                    منقضی شده
                  </span>
                )}
                {!expired && row.daysLeft !== null && row.daysLeft !== undefined
                  && row.daysLeft <= 7 && (
                  <span className="fx-pill" style={{
                    background: "rgba(251,191,36,.14)", color: "var(--warn)" }}>
                    {faNum(row.daysLeft)} روز مانده
                  </span>
                )}
              </div>
            </div>
            <button onClick={onClose} className="fx-ico-btn shrink-0"
              style={{ width: 28, height: 28 }} aria-label="بستن">
              <X size={13} />
            </button>
          </div>
        </div>

        {/* تب‌ها */}
        <div className="flex gap-0 px-5"
          style={{ borderBottom: "1px solid var(--border)" }}>
          {TABS.map(([k, lbl]) => (
            <button key={k} onClick={() => setTab(k)}
              className="px-3 py-2.5 text-[13px]"
              style={{
                color: tab === k ? "var(--accent-2)" : "var(--muted)",
                borderBottom: `2px solid ${tab === k ? "var(--accent-2)" : "transparent"}`,
                marginBottom: -1,
              }}>
              {lbl}
            </button>
          ))}
        </div>

        <div className="p-5">
          {tab === "deliver" && (
            <>
              {row.subUrl ? (
                <>
                  <label className="text-[12px] block mb-1.5"
                    style={{ color: "var(--muted)" }}>
                    لینک اشتراک
                  </label>
                  <div className="flex items-center gap-1.5 mb-2">
                    <div dir="ltr" className="fx-input text-[12px] flex-1"
                      style={{ fontFamily: "var(--mono)", overflow: "hidden",
                               textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {row.subUrl}
                    </div>
                    <button className="fx-ico-btn" style={{ width: 34, height: 34 }}
                      aria-label="کپی لینک" title="کپی"
                      onClick={() => copy(row.subUrl, "l")}>
                      {copied === "l"
                        ? <Check size={14} style={{ color: "var(--ok)" }} />
                        : <Copy size={14} />}
                    </button>
                  </div>

                  <button title="نمایش کد QR" onClick={showQr} disabled={qrBusy}
                    className="fx-btn-g w-full py-2.5 text-[13px] flex items-center
                               justify-center gap-1.5 mb-3">
                    {qrBusy ? <Loader2 size={13} className="animate-spin" />
                      : <QrCode size={13} />}
                    {qr ? "بستن کیوآر" : "نمایش کیوآر"}
                  </button>

                  {qr && (
                    <div className="flex justify-center p-4 rounded-xl mb-3"
                      style={{ background: "#fff" }}>
                      <img src={qr} alt="کیوآر لینک اشتراک"
                        style={{ width: 210, height: 210 }} />
                    </div>
                  )}
                  {qrErr && (
                    <div className="text-[12px] mb-3" style={{ color: "var(--warn)" }}>
                      {qrErr}
                    </div>
                  )}

                  <p className="text-[12px] leading-relaxed"
                    style={{ color: "var(--muted)" }}>
                    این لینک را به مشتری بدهید یا کیوآر را نشانش دهید. با همین
                    یک لینک همه‌ی کانفیگ‌هایش را می‌گیرد.
                  </p>
                </>
              ) : (
                <div className="rounded-xl p-3.5 text-[13px] leading-relaxed"
                  style={{ background: "rgba(251,191,36,.07)",
                           border: "1px solid rgba(251,191,36,.22)",
                           color: "var(--warn)" }}>
                  آدرس پایه‌ی اشتراک پیدا نشد. از پشتیبانی بخواهید سرویس
                  Subscription را در پنل روشن کند یا آدرس اشتراک را تنظیم کند.
                </div>
              )}
            </>
          )}

          {tab === "usage" && (
            <>
              <div className="flex items-baseline justify-between mb-2">
                <span className="text-[13px]" style={{ color: "var(--muted)" }}>
                  مصرف‌شده
                </span>
                <span className="text-[15px] font-bold" style={{ color: barColor }}>
                  {faNum(row.usedGB)} GB
                </span>
              </div>
              {bar !== null ? (
                <>
                  <div style={{ height: 8, borderRadius: 99,
                                background: "rgba(255,255,255,.06)",
                                overflow: "hidden" }}>
                    <div style={{ width: `${bar}%`, height: "100%",
                                  background: barColor }} />
                  </div>
                  <div className="flex justify-between mt-1.5 text-[12px]"
                    style={{ color: "var(--muted)" }}>
                    <span>{faNum(pct)}٪ مصرف شده</span>
                    <span>از {faNum(row.gb)} GB</span>
                  </div>
                </>
              ) : (
                <div className="text-[13px]" style={{ color: "var(--dim)" }}>
                  حجم نامحدود — سقفی برای مصرف نیست
                </div>
              )}

              <div className="mt-4">
                <Rowline k="سقف حجم"
                  v={row.gb === 0 ? "نامحدود" : `${faNum(row.gb)} GB`} />
                <Rowline k="باقی‌مانده"
                  v={row.gb === 0 ? "نامحدود"
                    : `${faNum(Math.max(0, row.gb - row.usedGB).toFixed(1))} GB`}
                  tone={bar !== null && bar >= 90 ? "var(--danger)" : undefined} />
                <Rowline k="کاربر هم‌زمان"
                  v={row.devices ? faNum(row.devices) : "نامحدود"} />
              </div>
            </>
          )}

          {tab === "info" && (
            <div>
              <Rowline k="تاریخ ساخت" v={row.createdJalali || "—"} />
              <Rowline k="تاریخ انقضا" v={row.expiryJalali || "بدون انقضا"} />
              <Rowline k="روز باقی‌مانده"
                v={row.daysLeft === null || row.daysLeft === undefined ? "—"
                  : expired ? "منقضی شده" : `${faNum(row.daysLeft)} روز`}
                tone={expired ? "var(--danger)"
                  : row.daysLeft <= 7 ? "var(--warn)" : undefined} />
              <Rowline k="وضعیت" v={row.active ? "فعال" : "غیرفعال"}
                tone={row.active ? "var(--ok)" : "var(--muted)"} />
              <Rowline k="شناسه‌ی اشتراک" v={row.subId || "—"} />
            </div>
          )}
        </div>

        {/* کارها */}
        <div className="px-5 pb-5 flex items-center gap-1.5">
          <button onClick={() => { onClose(); onRenew(row); }}
            className="fx-btn flex-1 py-2.5 text-[13px] flex items-center
                       justify-center gap-1.5">
            <RefreshCw size={13} /> تمدید
          </button>
          <button title="روشن یا خاموش کردن کانفیگ" onClick={() => { onToggle(row); onClose(); }}
            className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
            <Power size={13}
              style={{ color: row.active ? "var(--muted)" : "var(--ok)" }} />
            {row.active ? "غیرفعال" : "فعال"}
          </button>
        </div>
      </div>
    </div>
  );
}


function Dashboard({ token, onOut }) {
  const [me, setMe] = useState(null);
  const [sum, setSum] = useState(null);
  const [list, setList] = useState(null);
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("all");
  const [busy, setBusy] = useState(false);
  const [plans, setPlans] = useState(null);
  const [renew, setRenew] = useState(null);
  const [drop, setDrop] = useState(null);
  const [making, setMaking] = useState(false);
  const [botOpen, setBotOpen] = useState(false);
  const [plansOpen, setPlansOpen] = useState(false);
  const [ordersOpen, setOrdersOpen] = useState(false);
  const [detail, setDetail] = useState(null);
  const [stats, setStats] = useState(null);
  const [copied, setCopied] = useState("");
  const [note, setNote] = useState("");

  const load = useCallback(async () => {
    setBusy(true);
    setErr("");
    try {
      const [m, s, c, pl] = await Promise.all([
        api("/api/portal/me", { token }),
        api("/api/portal/summary", { token }).catch((e) => ({ _err: e.message })),
        api("/api/portal/configs", { token }).catch((e) => ({ _err: e.message })),
        api("/api/portal/plans", { token }).catch(() => null),
      ]);
      api("/api/portal/stats", { token }).then(setStats).catch(() => setStats(null));
      setMe(m);
      setPlans(pl && !pl._err ? pl : null);
      setSum(s && s._err ? null : s);
      setList(c && c._err ? null : c);
      if (c && c._err) setErr(c._err);
      else if (s && s._err) setErr(s._err);
    } catch (e) {
      // نشست که بسته شود، باید به صفحه‌ی ورود برگردیم — نه اینکه
      // یک صفحه‌ی خالی بماند.
      onOut();
    } finally {
      setBusy(false);
    }
  }, [token, onOut]);

  useEffect(() => { load(); }, [load]);

  const toggle = async (row) => {
    setNote("");
    try {
      await api("/api/portal/toggle", {
        token, method: "POST",
        body: { email: row.email, enable: !row.active },
      });
      setNote(`${row.email} ${row.active ? "غیرفعال" : "فعال"} شد`);
      load();
    } catch (e) {
      setErr(e.message);
    }
  };

  // فیلترِ وضعیت — همان دسته‌هایی که آمار بالا می‌شمارد. جست‌وجوی
  // نام به‌تنهایی کافی نبود: نماینده‌ای با صدها کانفیگ نمی‌تواند
  // «کدام‌ها رو به اتمام‌اند» را با تایپ‌کردن پیدا کند.
  const FILTERS = [
    ["all", "همه"],
    ["active", "فعال"],
    ["inactive", "غیرفعال"],
    ["soon", "رو به اتمام"],
    ["expired", "منقضی"],
    ["overq", "حجم تمام"],
    ["nearq", "بالای ۸۰٪"],
  ];

  const passes = (c) => {
    switch (filter) {
      case "active":   return !!c.active;
      case "inactive": return !c.active;
      case "soon":     return c.daysLeft !== null && c.daysLeft >= 0
                              && c.daysLeft <= 7;
      case "expired":  return c.daysLeft !== null && c.daysLeft < 0;
      case "overq":    return c.usagePct !== null && c.usagePct >= 100;
      case "nearq":    return c.usagePct !== null && c.usagePct >= 80
                              && c.usagePct < 100;
      default:         return true;
    }
  };

  const rows = (list?.configs || []).filter(
    (c) => (!q || String(c.email).toLowerCase().includes(q.toLowerCase()))
           && passes(c));

  // صفحه‌بندی شماره‌دار، نه «نمایش بیشتر» — همان قاعده‌ای که بقیه‌ی
  // پنل دارد. تا امروز این جدول همه‌ی ردیف‌ها را یک‌جا می‌ریخت.
  const { shown: pageRows, pager } = usePager(rows, 15);

  return (
    <div className="min-h-screen" dir="rtl" style={{ background: "var(--bg)" }}>
      <div className="max-w-6xl mx-auto px-4 py-6">

        <div className="flex items-center justify-between gap-3 mb-5 flex-wrap">
          <div>
            <div className="text-[18px] font-bold text-white">
              {me?.name || "پنل نمایندگی"}
            </div>
            {sum && (
              <div className="text-[13px]" style={{ color: "var(--muted)" }}>
                گروه {sum.label}
              </div>
            )}
          </div>
          {/* flex-wrap لازم است: پنج دکمه در یک خطِ نشکن، صفحه را روی
              موبایل ۴۶۳ پیکسل می‌کرد روی نمایشگر ۳۷۵ پیکسلی — یعنی نام
              نماینده بیرون از کادر و کارت‌ها نصفه. ردیفِ بیرونی
              flex-wrap داشت و همین ردیفِ داخلی نداشت. */}
          <div className="flex items-center gap-2 flex-wrap">
            <button onClick={() => setOrdersOpen(true)}
              className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
              <FileText size={13} /> سفارش‌ها
            </button>
            <button onClick={() => setPlansOpen(true)}
              className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
              <Package size={13} /> پلن‌های ربات
            </button>
            <button onClick={() => setBotOpen(true)}
              className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
              <Bot size={13} style={{ color: me?.hasBot ? "var(--ok)" : "var(--muted)" }} />
              ربات من
            </button>
            <button onClick={load} disabled={busy}
              className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
              {busy ? <Loader2 size={13} className="animate-spin" />
                : <RefreshCw size={13} />} تازه‌سازی
            </button>
            <button onClick={onOut}
              className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
              <LogOut size={13} /> خروج
            </button>
          </div>
        </div>

        {note && (
          <div className="fx-card p-4 mb-4 flex items-start gap-2"
            style={{ borderColor: "rgba(52,211,153,.3)" }}>
            <Check size={15} style={{ color: "var(--ok)" }}
              className="shrink-0 mt-0.5" />
            <span className="text-[13px]" style={{ color: "var(--dim)" }}>{note}</span>
          </div>
        )}

        {err && (
          <div className="fx-card p-4 mb-4 flex items-start gap-2"
            style={{ borderColor: "rgba(251,191,36,.3)" }}>
            <AlertTriangle size={15} style={{ color: "var(--warn)" }}
              className="shrink-0 mt-0.5" />
            <span className="text-[13px]" style={{ color: "var(--dim)" }}>{err}</span>
          </div>
        )}

        {/* آنچه همین حالا کاری می‌خواهد — نه شمارش خشک.
            «۹۴ کانفیگ» به نماینده نمی‌گوید کدام مشتری دارد از دست
            می‌رود؛ «۶ تا تا یک هفته دیگر تمام می‌شوند» می‌گوید. */}
        {stats && stats.needsAttention > 0 && (
          <div className="fx-card p-4 mb-4"
            style={{ borderColor: "rgba(251,191,36,.3)" }}>
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle size={14} style={{ color: "var(--warn)" }} />
              <span className="text-[13px] font-semibold text-white">
                نیاز به پیگیری
              </span>
            </div>
            <div className="flex gap-4 flex-wrap text-[13px]">
              {stats.expiringSoon > 0 && (
                <span style={{ color: "var(--warn)" }}>
                  {faNum(stats.expiringSoon)} تا یک هفته‌ی دیگر تمام می‌شود
                </span>
              )}
              {stats.expired > 0 && (
                <span style={{ color: "var(--danger)" }}>
                  {faNum(stats.expired)} منقضی شده
                </span>
              )}
              {stats.overQuota > 0 && (
                <span style={{ color: "var(--danger)" }}>
                  {faNum(stats.overQuota)} حجمش تمام شده
                </span>
              )}
              {stats.nearQuota > 0 && (
                <span style={{ color: "var(--warn)" }}>
                  {faNum(stats.nearQuota)} بالای ۸۰٪ مصرف
                </span>
              )}
            </div>
          </div>
        )}

        {stats && (
          <div className="fx-g4 grid grid-cols-4 gap-3 mb-3">
            <Stat icon={Users} label="کاربران فعال" value={faNum(stats.active)}
              color="var(--ok)"
              hint={stats.inactive ? `${faNum(stats.inactive)} غیرفعال` : ""} />
            <Stat icon={Clock} label="رو به اتمام"
              value={faNum(stats.expiringSoon)}
              color={stats.expiringSoon ? "var(--warn)" : undefined}
              hint="تا هفت روز دیگر" />
            <Stat icon={Database} label="مصرف"
              value={`${faNum(stats.usedGB)} GB`}
              hint={stats.usagePct !== null
                ? `${faNum(stats.usagePct)}٪ از ${faNum(stats.quotaGB)} GB` : ""} />
            <Stat icon={TrendingUp} label="این ماه"
              value={faNum(stats.thisMonth.new + stats.thisMonth.renewals)}
              color="var(--accent-2)"
              hint={`${faNum(stats.thisMonth.new)} تازه · `
                + `${faNum(stats.thisMonth.renewals)} تمدید`} />
          </div>
        )}

        {sum && (
          <div className="fx-g4 grid grid-cols-4 gap-3 mb-4">
            <Stat icon={Users} label="کل کانفیگ‌ها" value={faNum(sum.configs)}
              hint={stats ? `${faNum(stats.neverExpires)} بدون انقضا` : ""} />
            <Stat icon={RefreshCw} label="تمدیدها" value={faNum(sum.renewals)}
              hint={`${faNum(sum.months)} ماه در مجموع`} />
            <Stat icon={Package} label="نامحدود"
              value={stats ? faNum(stats.unlimitedQuota) : "—"}
              hint="بدون سقف حجم" />
            {sum.prepaid ? (
              <Stat icon={Wallet} label="اعتبار باقی‌مانده"
                value={`${faNum(sum.credit)} تومان`}
                color={sum.credit > 0 ? "var(--ok)" : "var(--danger)"}
                hint={sum.credit > 0 ? "" : "اعتبار تمام شده"} />
            ) : (
              <Stat icon={Wallet} label="مانده‌ی بدهی"
                value={`${faNum(sum.balance)} تومان`}
                color={sum.balance > 0 ? "var(--warn)" : "var(--ok)"}
                hint={`از ${faNum(sum.due)} تومان`} />
            )}
          </div>
        )}

        {/* فروشِ ربات خودش. تا امروز نماینده هیچ عددی از فروشش
            نمی‌دید، با اینکه ربات و سفارش و رسید داشت. */}
        {stats?.sales?.hasBot && (
          <div className="fx-g4 grid grid-cols-4 gap-3 mb-4">
            <Stat icon={ShoppingCart} label="فروش این ماه"
              value={`${faNum(stats.sales.monthSold)} تومان`}
              color="var(--accent-2)"
              hint={`${faNum(stats.sales.monthOrders)} سفارش`} />
            <Stat icon={TrendingUp} label="فروش کل"
              value={`${faNum(stats.sales.sold)} تومان`}
              hint={`${faNum(stats.sales.orders)} سفارش`} />
            <Stat icon={Wallet} label="دریافتی کارت‌به‌کارت"
              value={`${faNum(stats.sales.received)} تومان`}
              hint="خرید با کیف پول پول تازه نیست" />
            <Stat icon={FileText} label="در انتظار بررسی"
              value={faNum(stats.sales.pending)}
              color={stats.sales.pending ? "var(--warn)" : undefined}
              hint={stats.sales.pending ? "رسید منتظر شماست" : "چیزی نمانده"} />
          </div>
        )}

        {sum?.unpriced > 0 && (
          <div className="fx-card p-4 mb-4 text-[13px]" style={{ color: "var(--warn)" }}>
            {faNum(sum.unpriced)} کانفیگ هنوز نرخ ندارد و در مبلغ بالا حساب نشده.
          </div>
        )}

        <div className="fx-card p-5">
          <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="text-[14px] font-semibold text-white">
                کانفیگ‌های شما
              </span>
              <button onClick={() => setMaking(true)}
                className="fx-btn px-3 py-1.5 text-[12px] flex items-center gap-1">
                <Plus size={12} /> کانفیگ تازه
              </button>
            </div>
            <div className="relative">
              <Search size={13} className="absolute top-1/2 -translate-y-1/2 right-3"
                style={{ color: "var(--muted)" }} />
              <input value={q} onChange={(e) => setQ(e.target.value)}
                placeholder="جست‌وجوی نام کاربر"
                className="fx-input text-[13px]" style={{ paddingRight: 32, width: 220 }} />
            </div>
          </div>

          <div className="flex items-center gap-1.5 mb-4 flex-wrap">
            {FILTERS.map(([k, lbl]) => {
              const on = filter === k;
              return (
                <button key={k} onClick={() => setFilter(k)}
                  className="px-3 py-1.5 rounded-lg text-[12.5px]"
                  style={{
                    background: on ? "rgba(43,127,214,.18)" : "transparent",
                    border: `1px solid ${on ? "rgba(43,127,214,.45)"
                                            : "var(--border)"}`,
                    color: on ? "var(--accent-2)" : "var(--muted)",
                  }}>
                  {lbl}
                </button>
              );
            })}
            {(filter !== "all" || q) && (
              <span className="text-[12px] mr-1" style={{ color: "var(--muted)" }}>
                {faNum(rows.length)} از {faNum((list?.configs || []).length)}
              </span>
            )}
          </div>

          {!list ? (
            <p className="text-[13px] py-6 text-center" style={{ color: "var(--muted)" }}>
              {busy ? "در حال بارگذاری…" : "چیزی برای نمایش نیست"}
            </p>
          ) : !rows.length ? (
            <p className="text-[13px] py-6 text-center" style={{ color: "var(--muted)" }}>
              {q || filter !== "all"
                ? "با این فیلتر چیزی پیدا نشد" : "هنوز کانفیگی ندارید"}
            </p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table className="fx-table fx-table-cards">
                <thead>
                  <tr>
                    <th>نام کاربر</th><th>حجم</th><th>مصرف</th>
                    <th>دستگاه</th><th>انقضا</th><th>وضعیت</th><th></th>
                  </tr>
                </thead>
                <tbody>
                  {pageRows.map((c) => (
                    <tr key={c.email}>
                      {/* نامِ کانفیگ را خودِ نماینده می‌نویسد و می‌تواند
                          فارسی باشد؛ bdi جلوی جابه‌جا شدنش را می‌گیرد و
                          monoIf مونو را فقط به شناسه‌ی لاتین می‌دهد. */}
                      <td>
                        <button onClick={() => setDetail(c)}
                          style={{ color: "var(--accent-2)", textAlign: "left" }}
                          title="دیدن اطلاعات و لینک">
                          <bdi style={{ fontFamily: monoIf(c.email) }}>{c.email}</bdi>
                        </button>
                      </td>
                      <td data-label="حجم">{c.gb === 0 ? "∞" : `${faNum(c.gb)} GB`}</td>
                      <td data-label="مصرف">
                        {/* عدد و نوار با هم: عدد برای وقتی دقت لازم
                            است، نوار برای وقتی فقط باید نگاه کرد. */}
                        <div style={{ minWidth: 92 }}>
                          <div>
                            {faNum(c.usedGB)} GB
                            {c.usagePct !== null && (
                              <span className="text-[12px]"
                                style={{ color: c.usagePct >= 90 ? "var(--warn)" : "var(--muted)" }}>
                                {" "}({faNum(c.usagePct)}٪)
                              </span>
                            )}
                          </div>
                          {c.usagePct !== null && (
                            <div className="fx-usebar"
                              title={`${faNum(c.usagePct)}٪ مصرف شده`}>
                              <i style={{
                                width: `${Math.min(100, Math.max(2, c.usagePct))}%`,
                                background: c.usagePct >= 90 ? "var(--danger)"
                                  : c.usagePct >= 75 ? "var(--warn)" : "var(--ok)",
                              }} />
                            </div>
                          )}
                        </div>
                      </td>
                      <td data-label="دستگاه">{c.devices ? faNum(c.devices) : "∞"}</td>
                      <td data-label="انقضا">
                        <span>{c.expiryJalali || "—"}</span>
                        {c.daysLeft !== null && c.daysLeft <= 7 && (
                          <span className="fx-pill mr-2 text-[11.5px]"
                            style={{
                              background: c.daysLeft < 0 ? "rgba(248,113,113,.14)"
                                                         : "rgba(251,191,36,.14)",
                              color: c.daysLeft < 0 ? "var(--danger)" : "var(--warn)",
                            }}>
                            {c.daysLeft < 0 ? "منقضی"
                              : c.daysLeft === 0 ? "امروز"
                              : `${faNum(c.daysLeft)} روز`}
                          </span>
                        )}
                      </td>
                      <td data-label="وضعیت">
                        {c.active ? (
                          <span style={{ color: "var(--ok)" }}>
                            <Check size={12} className="inline" /> فعال
                          </span>
                        ) : (
                          <span style={{ color: "var(--muted)" }}>غیرفعال</span>
                        )}
                      </td>
                      <td>
                        <div className="flex items-center gap-1.5 justify-end flex-wrap">
                          {/* لینک اشتراک — نماینده فقط موقع ساخت یک بار
                              می‌دیدش و بعد راهی برای پیدا کردنش نداشت. */}
                          {c.subUrl && (
                            <button className="fx-ico-btn"
                              style={{ width: 28, height: 28 }}
                              aria-label={`کپی لینک ${c.email}`}
                              title="کپی لینک اشتراک"
                              onClick={() => {
                                navigator.clipboard?.writeText(c.subUrl);
                                setCopied(c.email);
                                setTimeout(() => setCopied(""), 1600);
                              }}>
                              {copied === c.email
                                ? <Check size={12} style={{ color: "var(--ok)" }} />
                                : <Link2 size={12} />}
                            </button>
                          )}
                          <button onClick={() => setRenew(c)}
                            className="fx-btn-g px-2.5 py-1.5 text-[12px]
                                       flex items-center gap-1">
                            <RefreshCw size={12} /> تمدید
                          </button>
                          <button onClick={() => toggle(c)}
                            className="fx-ico-btn" style={{ width: 28, height: 28 }}
                            aria-label={c.active ? "غیرفعال کن" : "فعال کن"}
                            title={c.active ? "غیرفعال کن" : "فعال کن"}>
                            <Power size={12}
                              style={{ color: c.active ? "var(--muted)" : "var(--ok)" }} />
                          </button>
                          <button onClick={() => setDrop(c)}
                            className="fx-ico-btn" style={{ width: 28, height: 28 }}
                            aria-label={`حذف ${c.email}`} title="حذف کانفیگ">
                            <Trash2 size={12} style={{ color: "var(--danger)" }} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {pager}
            </div>
          )}
        </div>
      </div>

      {renew && (
        <RenewBox token={token} row={renew} plans={plans}
          onClose={() => setRenew(null)}
          onDone={(m) => { setRenew(null); setNote(m); setErr(""); load(); }} />
      )}

      {drop && (
        <DropBox token={token} config={drop}
          onClose={() => setDrop(null)}
          onDone={(j) => { setNote(j.note || "کانفیگ حذف شد"); setErr(""); load(); }} />
      )}

      {making && (
        <NewBox token={token} plans={plans} slug={portalSlug()}
          onClose={() => { setMaking(false); load(); }}
          onDone={() => { setNote("کانفیگ تازه ساخته شد"); setErr(""); }} />
      )}

      {botOpen && (
        <BotBox token={token} onClose={() => { setBotOpen(false); load(); }}
          onNote={(m) => { setNote(m); setErr(""); }} />
      )}

      {plansOpen && (
        <PlansBox token={token} onClose={() => setPlansOpen(false)}
          onNote={(m) => { setNote(m); setErr(""); }} />
      )}

      {ordersOpen && (
        <OrdersBox token={token} onClose={() => { setOrdersOpen(false); load(); }}
          onNote={(m) => { setNote(m); setErr(""); }} />
      )}

      {detail && (
        <ConfigBox token={token} row={detail} onClose={() => setDetail(null)}
          onRenew={(r) => setRenew(r)} onToggle={toggle} />
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════

export default function Portal() {
  const slug = portalSlug();
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || "");

  // عنوان تبْ از index.html می‌آمد و برای نماینده هم «مدیریت صفحه
  // اشتراک» می‌نوشت — یعنی عنوانِ پنل مدیر، روی صفحه‌ای که اصلاً به
  // آن دسترسی ندارد.
  useEffect(() => { document.title = "پنل نمایندگی | Nexora"; }, []);

  const out = useCallback(() => {
    if (token) {
      api("/api/portal/logout", { token, method: "POST" }).catch(() => {});
    }
    localStorage.removeItem(TOKEN_KEY);
    setToken("");
  }, [token]);

  if (!token) return <Login slug={slug} onIn={setToken} />;
  return <Dashboard token={token} onOut={out} />;
}
