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
import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { createPortal } from "react-dom";
import {
  Activity, AlertTriangle, Bot, Camera, Check, Coins, Copy, CreditCard,
  Database, ExternalLink, Eye, FileText, Gift, Link2, Menu, MessageCircle, Moon, Play,
  Settings2, Sun,
  LayoutGrid, Loader2, LogOut, Package, Palette, Plus, Power, QrCode, RefreshCw, RotateCcw, Search,
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
import { MINI_PALETTES, MINI_TEMPLATES, themeVars } from "../lib/mini-themes.js";
import { LOGO_BGS, LOGO_SHAPES, ShopLogo, cleanLogoStyle } from "../lib/shoplogo.jsx";
import { BotUsersSection } from "../sections/bot/users";
import { BotInboxSection } from "../sections/bot/inbox";
import { BOT_BEHAVIOUR, BotTextsSection } from "../sections/bot/texts";
import { BotCoinsSection } from "../sections/bot/coins";
import { BotEventsSection } from "../sections/bot/events";

import { api } from "./api.js";
import { Frame, ThemeBox } from "./studio.jsx";
import { StoreBar } from "./store.jsx";
const TOKEN_KEY = "nexora_portal_token";

/* نشانی نماینده از آدرس صفحه: /r/<slug>

   import و بعد export، نه `export … from`.

   شکل دوم فقط نام را *عبور* می‌دهد و آن را وارد دامنه‌ی خودِ
   این ماژول نمی‌کند. کد همین فایل دو جا `portalSlug()` را صدا
   می‌زند، پس با آن شکل، پنل نماینده موقع رندر می‌افتاد —
   بیلد هم چیزی نمی‌گفت، چون خودِ نحو درست است. */
import { portalSlug } from "../lib/route.js";
export { portalSlug };

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
      style={{ background: "radial-gradient(ellipse 60% 50% at 50% 0%, var(--accent-soft), transparent), var(--bg)" }}>
      <div className="w-full max-w-sm rounded-2xl p-7"
        style={{ background: "var(--surface)", border: "1px solid var(--accent-halo)" }}>
        <div className="flex flex-col items-center text-center mb-6">
          <NexoraMark size={76} animate className="mb-3" />
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

function RenewBox({ inline, token, row, plans, onDone, onClose }) {
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
    <Frame inline={inline} onClose={onClose} width={360}>
        <div className="nx-box-head flex items-center justify-between mb-3">
          <div className="text-[14px] font-semibold text-white">تمدید کانفیگ</div>
          {!inline && (
            <button onClick={onClose} className="fx-ico-btn"
              style={{ width: 28, height: 28 }} aria-label="بستن">
              <X size={13} />
            </button>
          )}
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
                background: months === m ? "var(--accent-fill)" : "transparent",
                border: `1px solid ${months === m ? "var(--accent-edge)" : "var(--border)"}`,
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
    </Frame>
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
function DropBox({ inline, token, config, onDone, onClose }) {
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
    <Frame inline={inline} onClose={onClose} width={380}>
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
            background: fresh ? "var(--ok-wash)" : "var(--warn-wash)",
            border: `1px solid ${fresh ? "var(--ok-fill)" : "var(--warn-line)"}`,
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
    </Frame>
  );
}


function NewBox({ inline, token, plans, slug, onDone, onClose }) {
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
    <Frame inline={inline} onClose={onClose} width={380}>
        <div className="nx-box-head flex items-center justify-between mb-3">
          <div className="text-[14px] font-semibold text-white">کانفیگ تازه</div>
          {!inline && (
            <button onClick={onClose} className="fx-ico-btn"
              style={{ width: 28, height: 28 }} aria-label="بستن">
              <X size={13} />
            </button>
          )}
        </div>

        {made ? (
          <>
            <div className="rounded-xl p-3 mb-3"
              style={{ background: "var(--ok-wash)",
                       border: "1px solid var(--ok-fill)" }}>
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
                style={{ background: "var(--warn-wash)",
                         border: "1px solid var(--warn-line)",
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
                    background: gb === x.gb ? "var(--accent-fill)" : "transparent",
                    border: `1px solid ${gb === x.gb ? "var(--accent-edge)" : "var(--border)"}`,
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
                    background: days === d ? "var(--accent-fill)" : "transparent",
                    border: `1px solid ${days === d ? "var(--accent-edge)" : "var(--border)"}`,
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
    </Frame>
  );
}


/**
 * رباتِ نماینده چه چیزی کم دارد تا واقعاً بفروشد؟
 *
 * چرا یک تابع: هم بنرِ داشبورد این را می‌پرسد هم پنجره‌ی «ربات من».
 * اگر هر کدام فهرستِ خودش را داشت، روزی یکی قلمِ تازه را نداشت و
 * بنر می‌گفت «همه چیز آماده است» در حالی که ربات نمی‌فروخت.
 *
 * هر قلم می‌گوید **چه کسی** باید درستش کند. گروه دستِ مالک است؛ اگر
 * همان‌جا نگوییم، نماینده دنبالِ دکمه‌ای می‌گردد که وجود ندارد.
 */
export function saleGaps(st) {
  if (!st || !st.hasBot) return [];
  const out = [];
  if (!st.hasGroup) {
    out.push({ key: "group", who: "owner",
      title: "گروهِ شما هنوز تعیین نشده",
      why: "ربات تا آن موقع هیچ کانفیگی نمی‌سازد — به مدیر بگویید." });
  }
  if (!st.activeCards) {
    out.push({ key: "cards", who: "you",
      title: "شماره کارتی ثبت نشده",
      why: "مشتری نمی‌تواند پرداخت کند و کیف پول هم شارژ نمی‌شود." });
  }
  if (!st.ownerLinked) {
    out.push({ key: "link", who: "you",
      title: "رسیدها به شما نمی‌رسند",
      why: "یک‌بار خودتان را به ربات وصل کنید تا رسیدِ هر خرید با دکمه‌ی تایید برایتان بیاید." });
  }
  return out;
}

const CARD_BLANK = { number: "", holder: "", bank: "", active: true };

/** شماره کارت چهاررقم‌چهاررقم، فقط برای نمایش — ذخیره بی‌خط است */
function cardShown(v) {
  const d = String(v || "").replace(/[^0-9۰-۹]/g, "").slice(0, 16);
  return d.replace(/(.{4})(?=.)/g, "$1 ");
}

/**
 * کارت‌هایی که مشتری به آن‌ها واریز می‌کند.
 *
 * تا امروز نماینده هیچ راهی برای ثبتشان نداشت و ربات برای هر خرید
 * «هنوز شماره کارتی ثبت نشده» می‌گفت.
 */
function CardsEditor({ token, onSaved }) {
  const [rows, setRows] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");

  useEffect(() => {
    api("/api/portal/cards", { token })
      .then((j) => setRows(j.cards || []))
      .catch((e) => { setRows([]); setErr(e.message); });
  }, [token]);

  const up = (i, patch) => {
    setOk("");
    setRows((l) => l.map((c, x) => (x === i ? { ...c, ...patch } : c)));
  };

  const save = async () => {
    setBusy(true); setErr(""); setOk("");
    try {
      const j = await api("/api/portal/cards", {
        token, method: "PUT", body: { cards: rows },
      });
      setOk(`${faNum(j.active)} کارتِ فعال ذخیره شد`);
      onSaved && onSaved();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (rows === null) {
    return <div className="text-[13px] py-3" style={{ color: "var(--muted)" }}>
      <Loader2 size={13} className="inline animate-spin" /> در حال خواندن…</div>;
  }

  return (
    <div>
      {!rows.length && (
        <p className="text-[13px] mb-2 leading-relaxed" style={{ color: "var(--muted)" }}>
          هنوز کارتی ندارید. اگر چند کارت بگذارید، هر خرید تصادفی یکی را
          می‌گیرد تا واریزها روی یک حساب جمع نشوند.
        </p>
      )}
      {rows.map((c, i) => (
        <div key={i} className="rounded-xl p-3 mb-2"
          style={{ border: "1px solid var(--border)",
                   opacity: c.active ? 1 : 0.6 }}>
          {/* کلید و حذف در ردیفِ خودشان: کنارِ شماره که بودند، روی
              گوشی ۲۳ پیکسل از شانزده رقم را می‌بریدند. */}
          <div className="flex items-center justify-between gap-2 mb-2">
            <span className="text-[12px]" style={{ color: "var(--muted)" }}>
              کارت {faNum(i + 1)} · {c.active ? "فعال" : "غیرفعال"}
            </span>
            <div className="flex items-center gap-2">
              <Toggle checked={!!c.active} label="فعال"
                onChange={() => up(i, { active: !c.active })} />
              <button onClick={() => setRows((l) => l.filter((_, x) => x !== i))}
                className="fx-ico-btn" style={{ width: 30, height: 30 }}
                aria-label="حذف این کارت" title="حذف">
                <Trash2 size={12} />
              </button>
            </div>
          </div>
          <input dir="ltr" inputMode="numeric" value={cardShown(c.number)}
            onChange={(e) => up(i, { number: e.target.value.replace(/\s/g, "") })}
            placeholder="6037 9911 2222 3333"
            className="fx-input w-full text-[13px] mb-2"
            style={{ fontFamily: "var(--mono)" }}
            aria-label="شماره کارت" />
          <div className="grid grid-cols-2 gap-2">
            <input value={c.holder} onChange={(e) => up(i, { holder: e.target.value })}
              placeholder="نام صاحب کارت" className="fx-input text-[13px] min-w-0" />
            <input value={c.bank} onChange={(e) => up(i, { bank: e.target.value })}
              placeholder="بانک" className="fx-input text-[13px] min-w-0" />
          </div>
        </div>
      ))}
      <div className="flex gap-2">
        <button onClick={() => { setOk(""); setRows((l) => [...l, { ...CARD_BLANK }]); }}
          disabled={rows.length >= 10}
          className="fx-btn-g flex-1 py-2 text-[13px] flex items-center justify-center gap-1.5">
          <Plus size={13} /> کارتِ تازه
        </button>
        <button onClick={save} disabled={busy}
          className="fx-btn flex-1 py-2 text-[13px] flex items-center justify-center gap-1.5">
          {busy && <Loader2 size={13} className="animate-spin" />} ذخیره‌ی کارت‌ها
        </button>
      </div>
      {ok && <p className="text-[13px] mt-2" style={{ color: "var(--ok)" }}>{ok}</p>}
      {err && (
        <p className="text-[13px] mt-2 flex items-start gap-1.5" style={{ color: "var(--danger)" }}>
          <AlertTriangle size={13} className="shrink-0 mt-0.5" />{err}
        </p>
      )}
    </div>
  );
}

/**
 * وصل‌شدنِ نماینده به رباتش — تا رسیدها به او برسند.
 *
 * لینک یک‌بارمصرف است و نیم ساعت کار می‌کند. عمداً در تبِ تازه باز
 * می‌شود و خودِ لینک هم نشان داده می‌شود: روی دسکتاپ ممکن است
 * تلگرامِ وب باز نباشد و نماینده بخواهد لینک را روی گوشی باز کند.
 */
function OwnerLink({ token, linked, onChange }) {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const make = async () => {
    setBusy(true); setErr("");
    try {
      const j = await api("/api/portal/bot/link", { token, method: "POST" });
      setUrl(j.url);
      try { window.open(j.url, "_blank", "noopener"); } catch { /* نشانش می‌دهیم */ }
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const unlink = async () => {
    setBusy(true); setErr("");
    try {
      await api("/api/portal/bot/link", { token, method: "DELETE" });
      setUrl("");
      onChange && onChange();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (linked) {
    return (
      <div className="flex items-center justify-between gap-2">
        <span className="text-[13px]" style={{ color: "var(--ok)" }}>
          <Check size={13} className="inline" /> رسیدها به تلگرامِ شما می‌آیند
        </span>
        <button onClick={unlink} disabled={busy}
          className="fx-btn-g px-3 py-1.5 text-[12px]">جداشدن</button>
      </div>
    );
  }

  return (
    <div>
      <button onClick={make} disabled={busy}
        className="fx-btn w-full py-2.5 text-[13px] flex items-center justify-center gap-2">
        {busy ? <Loader2 size={13} className="animate-spin" /> : <ExternalLink size={13} />}
        وصلِ من به ربات
      </button>
      {url && (
        <div className="mt-2 text-[12px] leading-relaxed" style={{ color: "var(--muted)" }}>
          در تلگرام «Start» را بزنید. اگر باز نشد، این لینک را روی گوشی باز کنید
          (نیم ساعت و یک‌بار کار می‌کند):
          <div dir="ltr" className="mt-1 break-all select-all"
            style={{ fontFamily: "var(--mono)", color: "var(--dim)" }}>{url}</div>
          <button onClick={onChange} className="fx-btn-g w-full py-1.5 mt-2 text-[12px]">
            Start را زدم — دوباره بررسی کن
          </button>
        </div>
      )}
      {err && (
        <p className="text-[13px] mt-2 flex items-start gap-1.5" style={{ color: "var(--danger)" }}>
          <AlertTriangle size={13} className="shrink-0 mt-0.5" />{err}
        </p>
      )}
    </div>
  );
}

function BotBox({ inline, token, onClose, onNote }) {
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

  // چک‌لیستِ آمادگی — موارد درست هم دیده می‌شوند، نه فقط کمبودها:
  // «سه از چهار آماده است» از «یک مشکل» روشن‌تر می‌گوید کجای کارید.
  const gaps = saleGaps(st);
  const gapOf = (k) => gaps.find((g) => g.key === k);
  const checks = st?.hasBot ? [
    { k: "bot", ok: true, t: "ربات وصل است" },
    { k: "group", ok: !gapOf("group"), t: gapOf("group")?.title || "گروهِ فروش تعیین شده",
      why: gapOf("group")?.why, owner: true },
    { k: "cards", ok: !gapOf("cards"), t: gapOf("cards")?.title || `${faNum(st.activeCards)} کارتِ فعال`,
      why: gapOf("cards")?.why },
    { k: "link", ok: !gapOf("link"), t: gapOf("link")?.title || "رسیدها به تلگرامِ شما می‌آیند",
      why: gapOf("link")?.why },
  ] : [];

  return (
    <Frame inline={inline} onClose={onClose} width={420}>
      <div className="bb-grid">
        <div className="bb-col">
          <section className="nx-tile">
            <header className="pd-head">
              <div>
                <h3>ربات تلگرامِ شما</h3>
                <p>{st?.hasBot ? "مشتری‌ها از این ربات می‌خرند و برندِ شما را می‌بینند"
                  : "یک ربات از @BotFather بسازید و توکنش را این‌جا بگذارید"}</p>
              </div>
              <span className={`bb-pill ${st?.hasBot ? "t-ok" : "t-muted"}`}>
                {st?.hasBot ? "وصل" : "وصل نیست"}
              </span>
            </header>
            {st?.hasBot && (
              <div className="bb-bot">
                <Bot size={16} />
                <span dir="ltr">@{st.username}</span>
                <button onClick={drop} disabled={busy} className="fx-ico-btn"
                  style={{ width: 30, height: 30 }} aria-label="جداکردن ربات" title="جداکردن">
                  <Trash2 size={13} />
                </button>
              </div>
            )}
            <label className="bb-label">{st?.hasBot ? "جایگزینی توکن" : "توکن ربات"}</label>
            <div className="bb-row">
              <input dir="ltr" value={tok} onChange={(e) => setTok(e.target.value)}
                placeholder="123456:ABC-DEF..." className="fx-input text-[13px]"
                style={{ fontFamily: "var(--mono)" }} />
              <button onClick={save} disabled={busy || !tok.trim()}
                className="fx-btn px-4 text-[13px] flex items-center gap-1.5 shrink-0">
                {busy && <Loader2 size={13} className="animate-spin" />} ثبت
              </button>
            </div>
          </section>

          {st?.hasBot && (
            <section className="nx-tile">
              <header className="pd-head">
                <div>
                  <h3>آمادگیِ فروش</h3>
                  <p>{gaps.length ? `${faNum(checks.length - gaps.length)} از ${faNum(checks.length)} آماده است`
                    : "ربات آماده‌ی فروش است"}</p>
                </div>
              </header>
              <ul className="bb-checks">
                {checks.map((c) => (
                  <li key={c.k} className={c.ok ? "t-ok" : "t-warn"}>
                    <span className="ico">{c.ok ? <Check size={13} /> : <AlertTriangle size={13} />}</span>
                    <div>
                      <b>{c.t}{!c.ok && c.owner && <em> · کارِ مدیر</em>}</b>
                      {!c.ok && c.why && <span>{c.why}</span>}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {st?.hasBot && (
            <section className="nx-tile">
              <header className="pd-head">
                <div>
                  <h3>رسیدها و هشدارها</h3>
                  <p>رسیدِ هر خرید با دکمه‌ی تایید به تلگرامِ خودتان می‌آید</p>
                </div>
              </header>
              <OwnerLink token={token} linked={!!st.ownerLinked} onChange={load} />
            </section>
          )}
        </div>

        <div className="bb-col">
          {st?.hasBot && (
            <section className="nx-tile">
              <header className="pd-head">
                <div>
                  <h3>کارت‌های واریز</h3>
                  <p>مشتری به یکی از کارت‌های فعال واریز می‌کند — اگر چندتا باشد، تصادفی</p>
                </div>
                <CreditCard size={16} className="pd-head-ico" />
              </header>
              <CardsEditor token={token} onSaved={load} />
            </section>
          )}

          <section className="nx-tile">
            <header className="pd-head">
              <div>
                <h3>برند و پشتیبانی</h3>
                <p>نامی که مشتری در ربات و مینی‌اپ می‌بیند</p>
              </div>
            </header>
            <div className="bb-two">
              <div>
                <label className="bb-label">نامِ فروشگاه</label>
                <input value={brand} onChange={(e) => setBrand(e.target.value)}
                  className="fx-input w-full text-[13px]" />
              </div>
              <div>
                <label className="bb-label">یوزرنیمِ پشتیبانی</label>
                <input dir="ltr" value={support}
                  onChange={(e) => setSupport(e.target.value.replace("@", ""))}
                  placeholder="yoursupport" className="fx-input w-full text-[13px]"
                  style={{ fontFamily: "var(--mono)" }} />
              </div>
            </div>
            <button onClick={saveBrand} disabled={busy}
              className="fx-btn-g px-4 py-2.5 text-[13px] mt-3">ذخیره‌ی برند</button>
          </section>
        </div>
      </div>

      {err && (
        <p className="text-[13px] mt-3 flex items-start gap-1.5" style={{ color: "var(--danger)" }}>
          <AlertTriangle size={13} className="shrink-0 mt-0.5" />{err}
        </p>
      )}
    </Frame>
  );
}

/**
 * کف، قیمت، و سودِ یک پلن.
 *
 * `cost` از `/api/portal/plan-cost` می‌آید و **این‌جا هیچ ضربی
 * انجام نمی‌شود** — فقط تفریقِ سود، که خودِ همان دو عددِ آمده است.
 * قاعده‌ی مخزن: هیچ صفحه‌ای پول را خودش حساب نمی‌کند.
 *
 * چرا سه عدد و نه یکی: «برای شما ۲۰۰٬۰۰۰ تومان» به نماینده
 * نمی‌گفت چقدر سود می‌کند، فقط می‌گفت زیر کف نیست. و کفِ قبلی
 * `days` و `ip_limit` را نادیده می‌گرفت.
 */
function PlanFloor({ row, cost }) {
  if (!cost) {
    return (
      <div className="text-[11px] mt-1" style={{ color: "var(--muted)" }}>
        در حال حساب‌کردن کف…
      </div>
    );
  }

  if (!cost.ready) {
    // صفر نشان نمی‌دهیم: صفر یعنی «رایگان»، و این یعنی «نمی‌دانیم»
    return (
      <div className="rounded-lg px-2.5 py-2 mt-1.5 text-[11px] leading-relaxed"
        style={{ background: "var(--warn-wash)",
                 border: "1px solid var(--warn-fill)", color: "var(--warn)" }}>
        کفِ قیمت معلوم نیست — {cost.why || "نرخی برای این حجم ثبت نشده"}.
        {" "}تا ثبت نشود نمی‌توانید بدانید سود می‌کنید یا نه.
      </div>
    );
  }

  const price = Number(row.price) || 0;
  const floor = Number(cost.cost) || 0;
  const profit = price - floor;
  const loss = price > 0 && profit < 0;
  const flat = price > 0 && profit === 0;

  const tone = loss ? "var(--danger)" : flat ? "var(--warn)" : "var(--ok)";
  const wash = loss ? "var(--danger-wash)"
             : flat ? "var(--warn-wash)" : "var(--ok-wash)";
  const line = loss ? "var(--danger-line)"
             : flat ? "var(--warn-line)" : "var(--ok-line)";

  return (
    <div className="rounded-lg px-2.5 py-2 mt-1.5"
      style={{ background: wash, border: `1px solid ${line}` }}>
      <div className="flex items-center gap-3 flex-wrap text-[11.5px]">
        <span style={{ color: "var(--muted)" }}>
          کفِ شما <b style={{ color: "var(--dim)" }}>{faNum(floor)}</b> تومان
        </span>
        <span style={{ color: "var(--muted)" }}>
          قیمتِ شما <b style={{ color: "var(--dim)" }}>{faNum(price)}</b>
        </span>
        <span style={{ color: tone, fontWeight: 700 }}>
          {price === 0 ? "قیمت نگذاشته‌اید"
            : loss ? `${faNum(Math.abs(profit))} تومان ضرر`
            : flat ? "بدون سود"
            : `${faNum(profit)} تومان سود`}
        </span>
      </div>

      {/* چرا این‌قدر: نماینده باید بتواند عدد را بشکند، وگرنه
          «کف» یک ادعای بی‌پشتوانه است. */}
      <div className="text-[10.5px] mt-1" style={{ color: "var(--muted)" }}>
        {faNum(cost.base)} تومان پایه
        {cost.extraDevices > 0 && (
          <> {" + "}{faNum(cost.extraDevices)} کاربر اضافه ×{" "}
            {faNum(cost.perDevice)}</>
        )}
        {" × "}{faNum(cost.months)} ماه
        {cost.estimated && (
          <span style={{ color: "var(--warn)" }}>
            {" — "}پلن بی‌انقضاست؛ یک ماه تخمین زده شد
          </span>
        )}
      </div>
    </div>
  );
}



function PlansBox({ inline, token, onClose, onNote }) {
  const [rows, setRows] = useState(null);
  const [hasBot, setHasBot] = useState(false);
  const [policy, setPolicy] = useState(
    { mode: "open", allowed: [], perGb: 0, cost: {} });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  //: کفِ هر ردیف — از بکند می‌آید، این‌جا حساب نمی‌شود.
  const [cost, setCost] = useState([]);
  //: سقفِ تستِ رایگان = تستِ خودِ مالک. null یعنی تست ممکن نیست.
  const [trialCap, setTrialCap] = useState(null);

  const load = useCallback(async () => {
    try {
      const j = await api("/api/portal/bot-plans", { token });
      setRows(j.plans || []);
      setHasBot(!!j.hasBot);
      setTrialCap(j.trialCap || null);
      setPolicy({ mode: j.gbMode || "open", allowed: j.gbAllowed || [],
                  perGb: j.perGb || 0, cost: j.gbCost || {} });
    } catch (e) { setErr(e.message); }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  /*
   * کف را **بکند** حساب می‌کند، نه این‌جا.
   *
   * تا امروز این صفحه `cost[gb]` را نشان می‌داد — یعنی فقط حجم.
   * صورتحساب از `_line_amount` می‌آید که
   * `(نرخ پایه + نرخ کاربر اضافه) × ماه` است، پس یک پلنِ ۹۰ روزه‌ی
   * چهارکاربره کفش تقریباً یک‌سوم نشان داده می‌شد. نماینده «بالای
   * کف» می‌فروخت و ضرر می‌کرد، و فقط آخر ماه می‌فهمید.
   *
   * تاخیر دارد چون در حالِ تایپ صدا زده می‌شود.
   */
  const key = JSON.stringify((rows || []).map(
    (r) => [Number(r.gb) || 0, Number(r.days) || 0, Number(r.ip_limit) || 0]));

  useEffect(() => {
    if (!rows || !rows.length) { setCost([]); return undefined; }
    let alive = true;
    const id = setTimeout(async () => {
      try {
        const j = await api("/api/portal/plan-cost", {
          token, method: "POST",
          body: { rows: rows.map((r) => ({ gb: r.gb, days: r.days,
                                           ip_limit: r.ip_limit })) },
        });
        if (alive) setCost(j.rows || []);
      } catch {
        // نبودِ کف نباید ویرایشگر را از کار بیندازد؛ فقط نشان
        // داده نمی‌شود
        if (alive) setCost([]);
      }
    }, 350);
    return () => { alive = false; clearTimeout(id); };
  }, [key, token]);   // eslint-disable-line react-hooks/exhaustive-deps

  const patch = (i, p) => setRows(rows.map((r, k) => (k === i ? { ...r, ...p } : r)));
  // پلنِ تازه با اولین پله‌ی مجاز شروع می‌شود، نه با ۵۰ ثابت — وگرنه
  // نماینده‌ای که پله‌ی ۵۰ ندارد، هر بار یک ردیفِ نامعتبر می‌گیرد.
  const add = () => setRows([...(rows || []), {
    name: "",
    gb: policy.mode === "tiers" && policy.allowed.length
      ? policy.allowed[0] : 50,
    days: 30, ip_limit: 2, price: 0, is_active: true,
  }]);
  const drop = (i) => setRows(rows.filter((_, k) => k !== i));
  // تستِ رایگان با اندازه‌ی تستِ مالک شروع می‌شود — بزرگ‌ترین چیزی که
  // مجاز است. بزرگ‌ترش را بکند رد می‌کند و می‌گوید چرا.
  const hasTrial = (rows || []).some((r) => r.is_trial);
  const addTrial = () => setRows([...(rows || []), {
    name: "تست رایگان", gb: trialCap?.gb || 1, days: trialCap?.days || 1,
    ip_limit: trialCap?.ip_limit || 1, price: 0, is_active: true, is_trial: true,
  }]);

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
    <Frame inline={inline} onClose={onClose} width={620}>
        <div className="nx-box-head flex items-center justify-between mb-2">
          <div className="text-[14px] font-semibold text-white">
            پلن‌های ربات شما
          </div>
          {!inline && (
            <button onClick={onClose} className="fx-ico-btn"
              style={{ width: 28, height: 28 }} aria-label="بستن">
              <X size={13} />
            </button>
          )}
        </div>

        <p className="text-[12px] mb-3 leading-relaxed" style={{ color: "var(--muted)" }}>
          این قیمتی است که به مشتری خودتان می‌فروشید. آنچه بابت هر کانفیگ به
          ما می‌دهید جداست و از نرخ‌های گروه شما می‌آید.
        </p>

        {/* چرا فیلدِ حجم بسته است — یا چرا نیست. سکوت این‌جا یعنی
            نماینده فکر کند سیستم خراب است. */}
        <div className="rounded-xl p-3 mb-4 text-[12px] leading-relaxed"
          style={{
            background: policy.mode === "open" ? "var(--warn-wash)" : "var(--accent-wash)",
            border: `1px solid ${policy.mode === "open" ? "var(--warn-fill)" : "var(--accent-fill)"}`,
            color: policy.mode === "open" ? "var(--warn)" : "var(--dim)",
          }}>
          {policy.mode === "tiers" && (
            <>حجم‌های مجاز شما: <b>{policy.allowed
              .map((g) => (g === 0 ? "نامحدود" : faNum(g))).join("، ")}</b>
              {" — "}همان پله‌هایی که برایتان نرخ تعریف شده.</>
          )}
          {policy.mode === "volume" && (
            <>نرخ شما حجمی است: هر گیگابایت <b>{faNum(policy.perGb)}</b> تومان.
              {" "}پس هر حجمی می‌توانید تعریف کنید.</>
          )}
          {policy.mode === "open" && (
            <>هنوز نرخی برای گروه شما ثبت نشده، پس فعلاً حجم آزاد است.
              {" "}تا ثبت نشود، صورتحسابتان صفر حساب می‌شود — از پشتیبانی
              بخواهید نرخ را وارد کند.</>
          )}
        </div>

        {!hasBot && (
          <div className="rounded-xl p-3 mb-4 text-[12px]"
            style={{ background: "var(--warn-wash)",
                     border: "1px solid var(--warn-fill)",
                     color: "var(--warn)" }}>
            هنوز رباتی وصل نکرده‌اید — این پلن‌ها جایی نمایش داده نمی‌شوند.
          </div>
        )}

        {/* خطای خواندن داخلِ شاخه‌ی «ردیف‌ها رسیدند» بود؛ خواندنِ ناموفق
            هرگز به آن‌جا نمی‌رسید و اسکلت برای همیشه می‌ماند */}
        {!rows && err ? (
          <div className="text-[13px] py-3 flex items-start gap-1.5" style={{ color: "var(--danger)" }}>
            <AlertTriangle size={13} className="shrink-0 mt-0.5" />
            <span>پلن‌ها خوانده نشد: {err}{" "}
              <button type="button" className="underline" onClick={() => { setErr(""); load(); }}>دوباره</button>
            </span>
          </div>
        ) : !rows ? (
          <SkeletonCards n={3} />
        ) : (
          <>
            {/* حالتِ خالی **بن‌بست نیست**.
                تا امروز این شاخه `<>`ای را که دکمه‌های «پلن تازه» و
                «ذخیره» در آن بودند اصلاً رندر نمی‌کرد، پس هر
                نماینده‌ی تازه ویرایشگر را باز می‌کرد و هیچ راهی
                برای ساختنِ اولین پلن نداشت. */}
            {!rows.length && (
              <EmptyState icon={Package} text="هنوز پلنی تعریف نکرده‌اید"
                hint="پلن همان چیزی است که مشتری در ربات شما می‌بیند — حجم، مدت و قیمت."
                action={
                  <button onClick={add}
                    className="fx-btn px-4 py-2.5 text-[13px] flex items-center gap-1.5">
                    <Plus size={13} /> ساختِ اولین پلن
                  </button>
                } />
            )}

            {rows.length > 0 && <div className="pd-cards mb-3">{rows.map((r, i) => (
              <div key={i} className={`nx-tile${r.is_trial ? " pl-trial" : ""}`}>
                <div className="flex items-center gap-2 mb-2">
                  {!!r.is_trial && (
                    <span className="fx-pill text-[11.5px] shrink-0"
                      style={{ background: "var(--ok-soft)", color: "var(--ok)" }}>
                      <Gift size={11} className="inline" /> تست رایگان
                    </span>
                  )}
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
                  {/* حجم از پله‌های مالک می‌آید، نه دلخواه.
                      در حالت حجمی پله معنا ندارد و آزاد می‌ماند. */}
                  <div>
                    <label className="text-[11px] block mb-1"
                      style={{ color: "var(--muted)" }}>حجم (GB)</label>
                    {/* select بدون مونو: گزینه‌ها «نامحدود» و «خارج از
                        نرخ» هم دارند و JetBrains Mono حرف فارسی ندارد،
                        پس فقط به فونتِ دیگری می‌افتد. */}
                    {policy.mode === "tiers" && !r.is_trial ? (
                      <select value={r.gb ?? 0}
                        onChange={(e) => patch(i, { gb: Number(e.target.value) || 0 })}
                        className="fx-input text-[13px] text-center w-full">
                        {!policy.allowed.includes(Number(r.gb) || 0) && (
                          <option value={r.gb ?? 0}>
                            {faNum(r.gb ?? 0)} (خارج از نرخ)
                          </option>
                        )}
                        {policy.allowed.map((g) => (
                          <option key={g} value={g}>
                            {g === 0 ? "نامحدود" : faNum(g)}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <NumberInput min="0" value={r.gb ?? 0}
                        onChange={(e) => patch(i, { gb: Number(e.target.value) || 0 })}
                        className="fx-input text-[13px] text-center"
                        style={{ fontFamily: "var(--mono)" }} />
                    )}
                  </div>
                  {[["days", "روز"], ["ip_limit", "کاربر"],
                    ["price", "قیمت"]].map(([k, lbl]) => (
                    <div key={k}>
                      <label className="text-[11px] block mb-1"
                        style={{ color: "var(--muted)" }}>{lbl}</label>
                      {/* فقط «قیمت» جداکننده می‌گیرد. روز و تعداد
                          کاربر هیچ‌وقت سه‌رقمی نمی‌شوند و جداکننده
                          رویشان فقط شلوغی است. */}
                      {k === "price" && r.is_trial ? (
                        <input disabled value="رایگان"
                          className="fx-input text-[13px] text-center"
                          style={{ color: "var(--ok)" }} />
                      ) : k === "price" ? (
                        <MoneyInput min="0" value={r[k] ?? 0}
                          onChange={(e) => patch(i, { [k]: Number(e.target.value) || 0 })}
                          className="fx-input text-[13px] text-center" />
                      ) : (
                        <NumberInput min="0" value={r[k] ?? 0}
                          onChange={(e) => patch(i, { [k]: Number(e.target.value) || 0 })}
                          className="fx-input text-[13px] text-center"
                          style={{ fontFamily: "var(--mono)" }} />
                      )}
                    </div>
                  ))}
                </div>
                <div className="text-[11px] mt-1.5"
                  style={{ color: "var(--muted)" }}>
                  حجم ۰ یعنی نامحدود · کاربر ۰ یعنی بدون محدودیت
                </div>

                {/* کف، قیمت، و سود — سه عددِ جدا.
                    «برای شما X تومان» به‌تنهایی کافی نبود: نماینده
                    باید ببیند چقدر سود می‌کند، نه فقط اینکه زیر کف
                    نیست. */}
                {r.is_trial ? (
                  <div className="text-[12px] mt-2 leading-relaxed"
                    style={{ color: "var(--dim)" }}>
                    رایگان برای مشتری و برای شما — هزینه‌اش با مدیر است. حداکثر{" "}
                    <b>{trialCap?.gb ? `${faNum(trialCap.gb)} گیگ` : "حجمِ نامحدود"}</b>
                    {" · "}<b>{trialCap?.days ? `${faNum(trialCap.days)} روز` : "بی‌انقضا"}</b>
                    {" · "}<b>{trialCap?.ip_limit ? `${faNum(trialCap.ip_limit)} کاربر` : "کاربرِ نامحدود"}</b>
                    . هر مشتری یک بار. دکمه‌اش در ربات وقتی می‌آید که
                    «اشتراک تست رایگان» را در تنظیماتِ ربات روشن کنید.
                  </div>
                ) : (
                  <PlanFloor row={r} cost={cost[i]} />
                )}
              </div>
            ))}
              <button onClick={add} className="pd-add">
                <Plus size={18} /> پلن تازه
              </button>
            </div>}

            {/* تستِ رایگان: یکی، و فقط وقتی مالک تستی دارد. نبودنش گفته
                می‌شود — دکمه‌ای که کار نمی‌کند از نبودنش بدتر است. */}
            {rows.length > 0 && !hasTrial && (
              trialCap ? (
                <button onClick={addTrial}
                  className="fx-btn-g w-full py-2 text-[12.5px] flex items-center
                             justify-center gap-1.5 mb-2">
                  <Gift size={13} /> افزودنِ تستِ رایگان
                </button>
              ) : (
                <p className="text-[12px] mb-2 text-center" style={{ color: "var(--muted)" }}>
                  تستِ رایگان فعلاً ممکن نیست — مدیر هنوز تستی تعریف نکرده.
                </p>
              )
            )}

            {err && (
              <p className="text-[13px] mb-3 flex items-start gap-1.5"
                style={{ color: "var(--danger)" }}>
                <AlertTriangle size={13} className="shrink-0 mt-0.5" />{err}
              </p>
            )}

            {rows.length > 0 && (
              <button onClick={save} disabled={busy}
                className="fx-btn w-full py-2.5 text-[13px] flex items-center
                           justify-center gap-2">
                {busy && <Loader2 size={13} className="animate-spin" />} ذخیره
              </button>
            )}
          </>
        )}
    </Frame>
  );
}


function OrdersBox({ inline, token, onClose, onNote }) {
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
    <>
    <Frame inline={inline} onClose={onClose} width={640}>
        <div className="nx-box-head flex items-center justify-between mb-3">
          <div className="text-[14px] font-semibold text-white">
            سفارش‌های مشتری‌های شما
          </div>
          {!inline && (
            <button onClick={onClose} className="fx-ico-btn"
              style={{ width: 28, height: 28 }} aria-label="بستن">
              <X size={13} />
            </button>
          )}
        </div>

        <div className="flex gap-1.5 mb-4">
          {TABS.map(([k, lbl]) => (
            <button key={k} onClick={() => { setTab(k); setRows(null); }}
              className="px-3 py-2 rounded-lg text-[13px]"
              style={{
                background: tab === k ? "var(--accent-fill)" : "transparent",
                border: `1px solid ${tab === k ? "var(--accent-edge)" : "var(--border)"}`,
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
          <SkeletonCards n={3} />
        ) : !rows.length ? (
          <EmptyState icon={FileText}
            text={tab === "open" ? "سفارشی در انتظار نیست" : "چیزی این‌جا نیست"}
            hint={tab === "open"
              ? "هر رسیدی که مشتری در ربات شما بفرستد، همین‌جا برای تایید می‌آید."
              : "سفارش‌های بسته‌شده این‌جا بایگانی می‌شوند."} />
        ) : (<div className="pd-cards">{pageOrders.map((o) => (
          <div key={o.id} className={`nx-tile od-tile od-${o.status}`}>
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
                style={{ background: "var(--scrim-1)", color: "var(--dim)" }}>
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
        ))}</div>)}

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
    </Frame>

      {shot && createPortal(
        <div style={{
          position: "fixed", inset: 0, zIndex: 3100, display: "flex",
          alignItems: "center", justifyContent: "center", padding: 16,
          background: "var(--scrim-4)",
        }} onClick={(e) => { e.stopPropagation(); setShot(null); }}>
          <img src={shot} alt="رسید پرداخت"
            style={{ maxWidth: "100%", maxHeight: "90vh", borderRadius: 12 }} />
        </div>, document.body)}
    </>
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
      background: "var(--scrim-3)", overflowY: "auto",
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
                  background: row.active ? "var(--ok-soft)" : "var(--surface-3)",
                  color: row.active ? "var(--ok)" : "var(--muted)",
                }}>
                  {row.active ? "فعال" : "غیرفعال"}
                </span>
                {expired && (
                  <span className="fx-pill" style={{
                    background: "var(--danger-soft)", color: "var(--danger)" }}>
                    منقضی شده
                  </span>
                )}
                {!expired && row.daysLeft !== null && row.daysLeft !== undefined
                  && row.daysLeft <= 7 && (
                  <span className="fx-pill" style={{
                    background: "var(--warn-soft)", color: "var(--warn)" }}>
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
                  style={{ background: "var(--warn-wash)",
                           border: "1px solid var(--warn-fill)",
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
                                background: "var(--hair-2)",
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
              <Rowline k="تاریخ ساخت" v={faDate(row.createdJalali)} />
              <Rowline k="تاریخ انقضا" v={faDate(row.expiryJalali, "بدون انقضا")} />
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


/**
 * لوگوی خودِ نماینده.
 *
 * چرا این‌جا و نه در تنظیمات: این تنها جایی است که نماینده *می‌بیند*
 * لوگویش کجا می‌نشیند. تنظیماتی که اثرش جای دیگری است، پر نمی‌شود.
 *
 * فایل با base64 می‌رود، نه multipart — سرور `python-multipart`
 * ندارد و افزودنش به هر سروری که آپدیت می‌شود، ریسکِ بی‌دلیل است.
 */
function LogoPick({ token, logo, name, onDone }) {
  const ref = useRef(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const pick = async (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";                 // همان فایل دوباره هم انتخاب شود
    if (!f) return;
    setErr("");
    if (f.size > 512 * 1024) {
      setErr("حجم فایل بیشتر از ۵۱۲ کیلوبایت است");
      return;
    }
    setBusy(true);
    try {
      const data = await new Promise((res, rej) => {
        const r = new FileReader();
        r.onload = () => res(String(r.result || ""));
        r.onerror = () => rej(new Error("فایل خوانده نشد"));
        r.readAsDataURL(f);
      });
      await api("/api/portal/logo", { token, method: "POST", body: { data } });
      onDone();
    } catch (e2) {
      setErr(e2.message);
    } finally { setBusy(false); }
  };

  const drop = async () => {
    setBusy(true);
    setErr("");
    try {
      await api("/api/portal/logo", { token, method: "DELETE" });
      onDone();
    } catch (e2) { setErr(e2.message); } finally { setBusy(false); }
  };

  return (
    <div className="relative group">
      <button onClick={() => ref.current?.click()} disabled={busy}
        title="تغییر لوگو" className="block rounded-2xl"
        style={{ lineHeight: 0 }}>
        {logo
          ? <img src={logo} alt={name || ""} className="nx-logo"
              style={{ width: 42, height: 42 }} />
          : <Avatar name={name} id={name} size={42} ring />}
        <span className="fx-logo-edit">
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Camera size={13} />}
        </span>
      </button>
      <input ref={ref} type="file" accept="image/png,image/jpeg,image/webp"
        onChange={pick} className="hidden" />
      {logo && !busy && (
        <button onClick={drop} className="fx-logo-drop" title="برداشتن لوگو">
          <X size={11} />
        </button>
      )}
      {err && (
        <div className="absolute top-full mt-1 text-[11px] whitespace-nowrap z-10"
          style={{ color: "var(--danger)" }}>{err}</div>
      )}
    </div>
  );
}


/*
 * منوی نماینده — مثلِ پنلِ مالک، با بخش‌هایی که مالک برایش خواست.
 *
 * برگه: docs/specs/2026-09-23-reseller-dashboard.md
 */
const PORTAL_GROUPS = ["فروشگاه", "ربات", "ظاهر"];
const PORTAL_NAV = [
  { key: "home", label: "داشبورد", icon: LayoutGrid, group: "فروشگاه" },
  { key: "configs", label: "کانفیگ‌ها", icon: Database, group: "فروشگاه" },
  { key: "orders", label: "سفارش‌ها", icon: FileText, group: "فروشگاه" },
  { key: "users", label: "مشتری‌ها", icon: Users, group: "فروشگاه" },
  { key: "chat", label: "چت با مشتری", icon: MessageCircle, group: "فروشگاه" },
  { key: "plans", label: "پلن‌ها", icon: Package, group: "ربات" },
  { key: "bot", label: "ربات و پرداخت", icon: Bot, group: "ربات" },
  { key: "texts", label: "متن‌ها و تنظیمات", icon: Settings2, group: "ربات" },
  { key: "coins", label: "سکه و دعوت", icon: Coins, group: "ربات" },
  { key: "events", label: "رویدادها", icon: Activity, group: "ربات" },
  { key: "theme", label: "پوسته‌ی مینی‌اپ", icon: Palette, group: "ظاهر" },
];

/*
 * رفتارِ ربات برای نماینده — زیرمجموعه‌ی همان فهرستِ مالک.
 *
 * پیشوندِ شناسه، آدرسِ مینی‌اپ و پایه‌ی لینک مالِ مالک‌اند: پیشوند
 * برندِ صفحه‌ی اشتراک را تعیین می‌کند و آدرس برای همه یکی است.
 * یوزرنیمِ پشتیبانی در «ربات و پرداخت» است. بکند هم فقط همین‌ها را
 * می‌پذیرد (`PORTAL_SETTING_KEYS`) — این فهرست فقط رابط است.
 */
const PORTAL_BEHAVIOUR = BOT_BEHAVIOUR
  .filter((f) => ["trial_enabled", "ask_phone", "order_ttl_minutes"].includes(f.k))
  .map((f) => (f.k === "trial_enabled"
    ? { ...f, hint: "هر مشتری یک بار. پلنِ تست را در «پلن‌ها» بسازید — حداکثر به اندازه‌ی تستِ مدیر." }
    : f));

/**
 * قفلِ کانال — مشتری تا عضوِ کانالِ نماینده نشود، پلن نمی‌بیند.
 *
 * ربات باید در آن کانال مدیر باشد؛ وگرنه عضویت را نمی‌تواند بپرسد.
 */
function ChannelLock({ src }) {
  const [st, setSt] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [loadErr, setLoadErr] = useState("");
  // پیش‌تر خطا `setSt({})` بود: فرم با «خاموش» و کانالِ خالی نشان داده
  // می‌شد و «ذخیره» همان را می‌نوشت — قفلِ واقعیِ کانالِ نماینده بی‌صدا
  // خاموش می‌شد. حالا فرم فقط با داده‌ی خوانده‌شده نشان داده می‌شود.
  useEffect(() => {
    src.settings().then((j) => { setSt(j); setLoadErr(""); })
      .catch((e) => setLoadErr(e.message || "خواندن ناموفق بود"));
  }, [src]);
  if (loadErr && !st) {
    return (
      <div className="fx-card p-4 mt-4 text-[13px]" style={{ color: "var(--danger)" }}>
        تنظیمِ عضویتِ اجباری در کانال خوانده نشد: {loadErr}
      </div>
    );
  }
  if (!st) return null;
  const save = async () => {
    setBusy(true); setMsg(null);
    try {
      await src.saveSettings({ force_channel_on: !!st.force_channel_on,
                               force_channel: st.force_channel || "" });
      setMsg({ ok: true, m: "قفلِ کانال ذخیره شد" });
    } catch (e) { setMsg({ ok: false, m: e.message }); }
    finally { setBusy(false); }
  };
  return (
    <div className="fx-card p-4 mt-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-[14px] font-semibold text-white">عضویتِ اجباری در کانال</div>
          <div className="text-[12px] mt-1 leading-relaxed" style={{ color: "var(--muted)" }}>
            مشتری پیش از دیدنِ پلن‌ها باید عضوِ کانالتان باشد. رباتتان باید در
            آن کانال مدیر باشد.
          </div>
        </div>
        <Toggle label="عضویتِ اجباری" checked={!!st.force_channel_on}
          onChange={() => setSt({ ...st, force_channel_on: !st.force_channel_on })} />
      </div>
      <div className="flex gap-2 mt-3" style={{ opacity: st.force_channel_on ? 1 : 0.45 }}>
        <input dir="ltr" className="fx-input flex-1 min-w-0" placeholder="@yourchannel"
          value={st.force_channel || ""} disabled={!st.force_channel_on}
          onChange={(e) => setSt({ ...st, force_channel: e.target.value })}
          style={{ fontFamily: "var(--mono)" }} />
        <button onClick={save} disabled={busy} className="fx-btn px-4 text-[13px] shrink-0">
          {busy ? <Loader2 size={13} className="animate-spin" /> : "ذخیره"}
        </button>
      </div>
      {msg && (
        <p className="text-[12.5px] mt-2" style={{ color: msg.ok ? "var(--ok)" : "var(--danger)" }}>
          {msg.m}
        </p>
      )}
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
  // صفحه‌ی باز — در آدرس (#) می‌ماند تا تازه‌سازی و «برگشت» جای کاربر
  // را گم نکند
  const [page, setPage] = useState(() => {
    const h = String(window.location.hash || "").replace("#", "");
    return PORTAL_NAV.some((n) => n.key === h) ? h : "home";
  });
  const [side, setSide] = useState(false);
  const S = useMemo(() => portalSrc(token), [token]);
  const go = (k) => {
    setPage(k); setSide(false);
    try { window.history.replaceState(null, "", `#${k}`); } catch { /* تزئین */ }
  };
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
        api("/api/portal/plans", { token }).catch((e) => ({ _err: e.message })),
      ]);
      // آمار جدا می‌آید تا صفحه منتظرش نماند؛ ولی شکستش بی‌صدا نیست:
      // پیش‌تر کارت‌های فروش بی‌هیچ توضیحی از داشبورد غیب می‌شدند
      api("/api/portal/stats", { token }).then(setStats).catch((e) => {
        setStats(null);
        setErr((prev) => prev || `آمارِ فروش خوانده نشد: ${e.message}`);
      });
      setMe(m);
      setPlans(pl && !pl._err ? pl : null);
      setSum(s && s._err ? null : s);
      setList(c && c._err ? null : c);
      if (c && c._err) setErr(c._err);
      else if (s && s._err) setErr(s._err);
      // بی‌نرخ، «کانفیگ تازه» هیچ پله‌ای ندارد و تمدید قیمت نشان نمی‌دهد
      else if (pl && pl._err) setErr(`نرخ‌ها خوانده نشد: ${pl._err}`);
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

  const cur = PORTAL_NAV.find((n) => n.key === page) || PORTAL_NAV[0];
  const gaps = saleGaps(me);
  const pageNote = (m) => { setNote(m); setErr(""); };

  return (
    <div className="min-h-screen w-full flex fx-shell" dir="rtl">
      <div className="fx-amb" aria-hidden="true"><i /></div>
      {side && <div className="fx-backdrop fx-fade" onClick={() => setSide(false)} />}

      {/* منوی کناری — همان کلاس‌های پنلِ مالک، پس روی گوشی همان کشوی
          کناری است و روی دسکتاپ ثابت. */}
      <aside className={`fx-side ${side ? "open" : ""}`} style={{ zIndex: 60 }}>
        <div className="flex items-center gap-2.5 px-2 mb-2 min-w-0">
          <LogoPick token={token} logo={me?.logo} name={me?.name} onDone={load} />
          <div className="min-w-0 flex-1">
            <div className="text-[15px] font-bold text-white truncate">
              {me?.name || "پنل نمایندگی"}
            </div>
            <div className="text-[12px] truncate" style={{ color: "var(--muted)" }}
              dir={me?.botUsername ? "ltr" : "rtl"}>
              {me?.botUsername ? `@${me.botUsername}` : (sum ? `گروه ${sum.label}` : "")}
            </div>
          </div>
          <button className="lg:hidden shrink-0 fx-drawer-x" onClick={() => setSide(false)}
            aria-label="بستن منو"><X size={18} /></button>
        </div>

        {PORTAL_GROUPS.map((g) => (
          <div key={g}>
            <div className="fx-side-label">{g}</div>
            <nav className="flex flex-col gap-1">
              {PORTAL_NAV.filter((n) => n.group === g).map((n) => (
                <button key={n.key} data-navkey={n.key}
                  className={`fx-nav-item ${page === n.key ? "on" : ""}`}
                  onClick={() => go(n.key)}>
                  <n.icon size={16} />
                  <span className="flex-1 text-right">{n.label}</span>
                  {/* کاری که همین حالا منتظرِ اوست */}
                  {n.key === "orders" && stats?.sales?.pending > 0 && (
                    <span className="fx-pill text-[11px]"
                      style={{ background: "var(--warn-soft)", color: "var(--warn)" }}>
                      {faNum(stats.sales.pending)}
                    </span>
                  )}
                  {n.key === "bot" && gaps.length > 0 && (
                    <AlertTriangle size={13} style={{ color: "var(--warn)" }} />
                  )}
                </button>
              ))}
            </nav>
          </div>
        ))}

        <div className="mt-auto pt-4" style={{ borderTop: "1px solid var(--border)" }}>
          <button onClick={onOut} className="fx-nav-item"><LogOut size={15} /> خروج</button>
          {/* «هنوز نمی‌بینمش» معمولاً یعنی سرور به‌روز نشده — و تا
              امروز هیچ راهی برای فهمیدنش نبود. */}
          {me?.version && (
            <div className="text-[11.5px] px-3 mt-2" style={{ color: "var(--muted)" }}>
              نسخه‌ی <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>{me.version}</span>
            </div>
          )}
        </div>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="fx-topbar">
          <div className="flex items-center gap-3 min-w-0">
            <button className="fx-burger" onClick={() => setSide(true)} aria-label="منو">
              <Menu size={19} />
            </button>
            <h1 className="text-[18px] font-bold text-white truncate">{cur.label}</h1>
          </div>
          {/* فقط برای داده‌ی همین دو صفحه؛ صفحه‌های دیگر دکمه‌ی خودشان را
              دارند و دو «تازه‌سازی» کنارِ هم نمی‌گوید کدام چه می‌کند. */}
          {(page === "home" || page === "configs") && (
            <button onClick={load} disabled={busy}
              className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5 shrink-0">
              {busy ? <Loader2 size={13} className="animate-spin" />
                : <RefreshCw size={13} />} تازه‌سازی
            </button>
          )}
        </header>

        <main className="fx-main flex-1 p-7 w-full mx-auto" style={{ maxWidth: 1440 }}>
        {/* رباتی که وصل است ولی نمی‌فروشد. بدون این، نماینده فقط
            وقتی می‌فهمید که مشتری شکایت می‌کرد. */}
        {gaps.length > 0 && page !== "bot" && (
          <div className="fx-card p-4 mb-4 flex items-start gap-3 flex-wrap"
            style={{ borderColor: "var(--warn-line)" }}>
            <AlertTriangle size={16} className="shrink-0 mt-0.5"
              style={{ color: "var(--warn)" }} />
            <div className="flex-1 min-w-0">
              <div className="text-[13px] font-medium" style={{ color: "var(--warn)" }}>
                ربات شما هنوز نمی‌تواند بفروشد
              </div>
              <ul className="text-[13px] mt-1 leading-relaxed" style={{ color: "var(--dim)" }}>
                {gaps.map((g) => (
                  <li key={g.key}>• {g.title}{g.who === "owner" && " (کارِ مدیر)"}</li>
                ))}
              </ul>
            </div>
            <button onClick={() => go("bot")}
              className="fx-btn-g px-3 py-2 text-[13px] shrink-0">
              درست‌کردن
            </button>
          </div>
        )}

        {note && (
          <div className="fx-card p-4 mb-4 flex items-start gap-2"
            style={{ borderColor: "var(--ok-line)" }}>
            <Check size={15} style={{ color: "var(--ok)" }}
              className="shrink-0 mt-0.5" />
            <span className="text-[13px]" style={{ color: "var(--dim)" }}>{note}</span>
          </div>
        )}

        {err && (
          <div className="fx-card p-4 mb-4 flex items-start gap-2"
            style={{ borderColor: "var(--warn-line)" }}>
            <AlertTriangle size={15} style={{ color: "var(--warn)" }}
              className="shrink-0 mt-0.5" />
            <span className="text-[13px]" style={{ color: "var(--dim)" }}>{err}</span>
          </div>
        )}

        <StoreBar token={token} page={page} onNote={pageNote} />

        {page === "home" && (
          <HomeDash stats={stats} sum={sum} go={go} src={S} busy={busy} />
        )}

        {page === "configs" && (
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
                    background: on ? "var(--accent-fill)" : "transparent",
                    border: `1px solid ${on ? "var(--accent-edge)"
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
            <SkeletonTable rows={6} cols={7} />
          ) : !rows.length ? (
            q || filter !== "all" ? (
              <EmptyState icon={Search} text="با این فیلتر چیزی پیدا نشد"
                hint="فیلتر را «همه» کنید یا بخشی از نام کاربر را بنویسید."
                action={<button className="fx-btn-g px-4 py-2 text-[13px]"
                  onClick={() => { setQ(""); setFilter("all"); }}>
                  برداشتن فیلتر</button>} />
            ) : (
              <EmptyState icon={Users} text="هنوز کانفیگی ندارید"
                hint="با «کانفیگ تازه» اولین مشتری‌تان را بسازید — نامش را خودتان انتخاب می‌کنید."
                action={<button className="fx-btn px-4 py-2 text-[13px]"
                  onClick={() => setMaking(true)}>کانفیگ تازه</button>} />
            )
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
                          className="inline-flex items-center gap-2"
                          style={{ color: "var(--accent-2)", textAlign: "left" }}
                          title="دیدن اطلاعات و لینک">
                          {/* چهره‌ی مشتری — فهرستِ صد ردیفِ هم‌شکل با
                              شناسه‌های شبیه‌به‌هم، با رنگ قابل‌مرور
                              می‌شود. رنگ از خودِ شناسه می‌آید، پس
                              همیشه همان است. */}
                          <Avatar name={c.email} id={c.email} size={26} />
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
                        <span>{faDate(c.expiryJalali)}</span>
                        {c.daysLeft !== null && c.daysLeft <= 7 && (
                          <span className="fx-pill mr-2 text-[11.5px]"
                            style={{
                              background: c.daysLeft < 0 ? "var(--danger-soft)"
                                                         : "var(--warn-soft)",
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
        )}

        {page === "orders" && <OrdersBox inline token={token} onNote={pageNote} />}
        {page === "users" && <BotUsersSection src={S} />}
        {page === "chat" && (
          <BotInboxSection src={S}
            note={me?.hasBot ? "پاسخ شما در مینی‌اپِ مشتری و با یک خبر در رباتِ خودتان می‌رسد."
                             : "تا رباتتان وصل نشود، پاسخ فقط در مینی‌اپ دیده می‌شود."} />
        )}
        {page === "plans" && <PlansBox inline token={token} onNote={pageNote} />}
        {page === "bot" && (
          <BotBox inline token={token} onNote={pageNote} onClose={load} />
        )}
        {page === "texts" && (
          <>
            <BotTextsSection src={S} behaviour={PORTAL_BEHAVIOUR} showAdmins={false} />
            <ChannelLock src={S} />
          </>
        )}
        {page === "coins" && <BotCoinsSection src={S} />}
        {page === "theme" && <ThemeBox inline token={token} onNote={pageNote} />}
        {page === "events" && <BotEventsSection src={S} />}
        </main>
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
