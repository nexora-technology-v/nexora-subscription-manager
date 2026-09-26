/**
 * پنل نمایندگی — سمت مدیر.
 *
 * این‌جا نشانی و رمز هر نماینده ساخته می‌شود و لینکش تحویل داده
 * می‌شود. تا وقتی این صفحه نبود، تنها راهش خط فرمان بود.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertTriangle, Camera, Check, ChevronDown, Copy, History, Key, Link2, Loader2, Network,
  Plus, Power, RefreshCw, Users, Wallet, X,
} from "lucide-react";

import { API_URL } from "../lib/constants";
import { errMsg, errText, faNum, okJson } from "../lib/format";
import { Avatar, ConfirmModal, EmptyState, Field, InfoBox, LoadError, Msg, MoneyInput, NumberInput, SectionHead, StatTile, Toggle } from "../ui/index";
import { BotInboundsSection } from "./bot/inbounds";
import { isoToJalaliLabel, isoToJalaliStamp } from "../ui/jalali";


/** همان الگوی بقیه‌ی بخش‌ها: بخوان، نگه دار، دوباره بخوان. */
function useJson(path, password) {
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    setBusy(true);
    try {
      const j = await fetch(`${API_URL}${path}`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => okJson(r));
      setD(j);
    } catch (e) { setD({ ready: false, error: errMsg(e) }); }
    finally { setBusy(false); }
  }, [password, path]);
  useEffect(() => { load(); }, [load]);
  return { d, busy, load };
}

function randomPass() {
  const a = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  return Array.from(crypto.getRandomValues(new Uint32Array(16)))
    .map((n) => a[n % a.length]).join("");
}

/**
 * لوگوی یک نماینده، از سمت مالک.
 *
 * همان قاعده‌ی پنل نماینده، فقط با احراز هویتِ مدیر. مالک لازم است
 * بتواند خودش هم بگذارد: نماینده‌ای که هنوز وارد پنلش نشده، مشتری
 * دارد.
 */
function TenantLogo({ tid, name, logo, password, onDone }) {
  const ref = useRef(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const send = async (body, method) => {
    setBusy(true); setErr("");
    try {
      const r = await fetch(`${API_URL}/api/admin/tenant/${tid}/logo`, {
        method,
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Password": password || "",
        },
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(errText(j.detail, "آپلود نشد"));
      onDone();
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  const pick = async (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    if (f.size > 512 * 1024) { setErr("بیشتر از ۵۱۲ کیلوبایت"); return; }
    const data = await new Promise((res, rej) => {
      const rd = new FileReader();
      rd.onload = () => res(String(rd.result || ""));
      rd.onerror = () => rej(new Error("فایل خوانده نشد"));
      rd.readAsDataURL(f);
    }).catch((e2) => { setErr(e2.message); return null; });
    if (data) send({ data }, "POST");
  };

  return (
    <div className="relative group shrink-0">
      <button onClick={() => ref.current?.click()} disabled={busy}
        title="تغییر لوگو" style={{ lineHeight: 0 }}>
        {logo
          ? <img src={logo} alt={name || ""} className="nx-logo"
              style={{ width: 30, height: 30 }} />
          : <Avatar name={name} id={tid ?? name} size={30} />}
        <span className="fx-logo-edit" style={{ width: 16, height: 16 }}>
          {busy ? <Loader2 size={9} className="animate-spin" /> : <Camera size={9} />}
        </span>
      </button>
      <input ref={ref} type="file" accept="image/png,image/jpeg,image/webp"
        onChange={pick} className="hidden" />
      {logo && !busy && (
        <button onClick={() => send(null, "DELETE")} className="fx-logo-drop"
          style={{ width: 15, height: 15 }} title="برداشتن لوگو">
          <X size={9} />
        </button>
      )}
      {err && (
        <div className="absolute top-full mt-1 text-[10.5px] whitespace-nowrap z-10"
          style={{ color: "var(--danger)" }}>{err}</div>
      )}
    </div>
  );
}


function Row({ t, groups, password, onSaved, setMsg }) {
  const [slug, setSlug] = useState(t.portalSlug || "");
  const [group, setGroup] = useState(t.portalGroup || "");
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState("");
  const [topup, setTopup] = useState("");
  const [log, setLog] = useState(null);
  const [open, setOpen] = useState(false);
  const [ask, setAsk] = useState(null);      // "pw" | "close"

  // credit منفی یعنی بدون سقف: آخر ماه صورتحساب می‌گیرد.
  const prepaid = t.credit !== null && Number(t.credit) >= 0;

  const link = slug ? `${window.location.origin}/r/${slug}` : "";

  const save = async (patch, what) => {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/tenant/${t.id}/portal`, {
        method: "POST",
        headers: { "Content-Type": "application/json",
                   "X-Admin-Password": password },
        body: JSON.stringify(patch),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(errText(j.detail, "ثبت نشد"));
      setMsg({ t: "ok", m: what + (j.opened ? " — پنلش هم باز شد" : "") });
      onSaved();
    } catch (e) {
      setMsg({ t: "err", m: e.message });
    } finally {
      setBusy(false);
    }
  };

  const copy = (text, label) => {
    navigator.clipboard?.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(""), 1600);
  };

  const on = !!t.portalEnabled;
  const newPass = () => {
    const p = randomPass();
    setPw(p);
    setOpen(true);
    save({ password: p }, "رمز تازه ساخته شد — همین حالا کپی کنید");
  };

  const setCredit = async (body, what) => {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/tenant/${t.id}/credit`, {
        method: "POST",
        headers: { "Content-Type": "application/json",
                   "X-Admin-Password": password },
        body: JSON.stringify(body),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(errText(j.detail, "ثبت نشد"));
      setTopup("");
      // شارژ در حسابداری هم به‌عنوان پرداخت ثبت می‌شود — مگر اینکه
      // نماینده هنوز گروهی نداشته باشد. آن حالت باید دیده شود،
      // وگرنه پولی که رسیده در «دریافت‌شده» و سود نمی‌آید و هیچ‌جا
      // هم نمی‌گوید چرا.
      if (j.recorded === false) {
        setMsg({ t: "err",
                 m: `${what} — ولی چون گروهی انتخاب نشده، در حسابداری `
                    + "ثبت نشد. گروه را تعیین کنید و پرداخت را دستی وارد کنید." });
        onSaved();
        return;
      }
      setMsg({ t: "ok", m: what });
      onSaved();
    } catch (e) {
      setMsg({ t: "err", m: e.message });
    } finally {
      setBusy(false);
    }
  };

  const showLog = async () => {
    if (log) { setLog(null); return; }
    try {
      const r = await fetch(
        `${API_URL}/api/admin/tenant/${t.id}/credit-log`,
        { headers: { "X-Admin-Password": password } });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { setMsg({ t: "err", m: errText(j.detail, "تاریخچه خوانده نشد") }); return; }
      setLog(j.rows || []);
    } catch {
      setMsg({ t: "err", m: "تاریخچه خوانده نشد" });
    }
  };

  // «آماده‌ی ورود» — همان سه شرطی که پایین فهرست می‌شوند. پیش‌تر نبودِ
  // نشانیِ لینک در شرطِ بیرونی نبود، پس نماینده‌ی بی‌نشانی هشدار نمی‌گرفت.
  const ready = !!(t.portalSlug && t.portalGroup && t.hasPass && on);

  /* ردیفِ فشرده، تنظیمات بازشونده. پیش‌تر هر نماینده یک کارتِ ۳۷۰ پیکسلیِ
     همیشه‌باز بود — چهار نماینده، ۱۵۰۰ پیکسل فرم برای دیدنِ چهار عدد اعتبار. */
  return (
    <div className={`fx-card fx-res mb-3 ${open ? "open" : ""}`}>
      <div className="fx-res-row">
        <TenantLogo tid={t.id} name={t.name} logo={t.logo}
          password={password} onDone={onSaved} />
        <button className="min-w-0 flex-1 text-right" onClick={() => setOpen(!open)} aria-expanded={open}>
          <span className="flex items-center gap-2 flex-wrap">
            <span className="text-[14px] font-semibold text-white">{t.name}</span>
            <span className="fx-pill" style={{
              background: on ? "var(--ok-soft)" : "var(--surface-3)",
              color: on ? "var(--ok)" : "var(--muted)" }}>{on ? "پنل باز" : "پنل بسته"}</span>
            {!ready && on && <span className="fx-pill" style={{ background: "var(--warn-soft)", color: "var(--warn)" }}>آماده‌ی ورود نیست</span>}
          </span>
          <span className="block text-[12px] mt-0.5 truncate" style={{ color: "var(--muted)" }}>
            {t.portalGroup ? <span dir="ltr">{t.portalGroup}</span> : "بدون گروه"}
            {t.portalSlug ? <> · <span dir="ltr">/r/{t.portalSlug}</span></> : ""}
          </span>
        </button>
        <span className="text-[13px] font-bold shrink-0 text-left" style={{
          color: prepaid ? (Number(t.credit) > 0 ? "var(--ok)" : "var(--danger)") : "var(--dim)",
          fontFamily: "var(--num)" }}>
          {prepaid ? <>{faNum(t.credit)} <span className="fx-fa-sub text-[11px]" style={{ color: "var(--muted)" }}>تومان</span></> : "بدون سقف"}
        </span>
        {link && (
          <button className="fx-ico-btn" style={{ width: 32, height: 32 }}
            title="کپی لینک پنل" aria-label="کپی لینک پنل" onClick={() => copy(link, "link")}>
            {copied === "link" ? <Check size={13} style={{ color: "var(--ok)" }} /> : <Copy size={13} />}
          </button>
        )}
        <button className="fx-ico-btn" style={{ width: 32, height: 32 }}
          title={open ? "بستن" : "تنظیمات"} aria-label={open ? "بستن" : "تنظیمات"} onClick={() => setOpen(!open)}>
          <ChevronDown size={14} style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform .2s" }} />
        </button>
      </div>

      {open && <div className="fx-res-body">
      <div className="flex items-center justify-end gap-3 mb-3 flex-wrap">
        {/* بستنِ پنل نشست‌های بازِ نماینده را همان لحظه می‌اندازد — با یک
            کلیکِ اشتباه نه */}
        <button title="باز یا بستن پنل نماینده" disabled={busy}
          onClick={() => (on ? setAsk("close") : save({ enabled: true }, "پنل باز شد"))}
          className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
          <Power size={13} style={{ color: on ? "var(--muted)" : "var(--ok)" }} />
          {on ? "بستن پنل" : "بازکردن پنل"}
        </button>
      </div>

      <div className="fx-g3 grid grid-cols-2 gap-3 mb-3">
        <Field label="نشانی لینک" hint="فقط حروف انگلیسی و عدد — در کل سیستم یکتاست">
          <input className="fx-input" dir="ltr" value={slug}
            placeholder="hossein"
            onChange={(e) => setSlug(e.target.value.replace(/[^A-Za-z0-9_-]/g, ""))} />
        </Field>
        <Field label="گروه x-ui این نماینده"
          hint="کلید همه‌ی محدودسازی‌ها — بدونش هیچ چیز نمی‌بیند">
          <select className="fx-input" value={group}
            onChange={(e) => setGroup(e.target.value)}>
            <option value="">— انتخاب کنید —</option>
            {/* گروهِ ثبت‌شده باید دیده شود، حتی اگر در فهرستِ x-ui
                نباشد. بدون این، select مقدارِ بی‌گزینه را نشان
                نمی‌داد و روی «انتخاب کنید» می‌افتاد — یعنی نماینده‌ای
                که گروه دارد «بدون گروه» به نظر می‌رسید. و چون فهرست
                از x-ui می‌آید، کافی بود پنل یک لحظه در دسترس نباشد تا
                *همه‌ی* نماینده‌ها همین‌طور دیده شوند. */}
            {group && !(groups || []).includes(group) && (
              <option value={group}>{group} — در x-ui پیدا نشد</option>
            )}
            {(groups || []).map((g) => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>
        </Field>
      </div>

      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <button disabled={busy || !slug || !group}
          onClick={() => save({ slug, group }, "نشانی و گروه ثبت شد")}
          className="fx-btn px-3 py-2 text-[13px] flex items-center gap-1.5">
          {busy ? <Loader2 size={13} className="animate-spin" />
            : <Check size={13} />} ثبت
        </button>
        <button disabled={busy}
          onClick={() => (t.hasPass ? setAsk("pw") : newPass())}
          className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
          <Key size={13} /> رمز تازه بساز
        </button>
      </div>

      {pw && (
        <InfoBox tone="warn">
          <div className="text-[13px] mb-2">
            رمز این نماینده — فقط همین یک بار نشان داده می‌شود:
          </div>
          <div className="flex items-center gap-1.5">
            <div dir="ltr" className="fx-input text-[13px] flex-1"
              style={{ fontFamily: "var(--mono)" }}>{pw}</div>
            <button className="fx-ico-btn" style={{ width: 32, height: 32 }}
              aria-label="کپی رمز" onClick={() => copy(pw, "pw")}>
              {copied === "pw" ? <Check size={13} style={{ color: "var(--ok)" }} />
                : <Copy size={13} />}
            </button>
          </div>
        </InfoBox>
      )}

      {link && (
        <div className="mt-3">
          <div className="text-[12px] mb-1.5" style={{ color: "var(--muted)" }}>
            لینکی که به نماینده می‌دهید
          </div>
          <div className="flex items-center gap-1.5">
            {/* روی موبایل لینک در کادر جا نمی‌شود و با ... بریده
                می‌شود؛ title کاری می‌کند که کاملش دست‌کم با نگه‌داشتن
                ماوس دیده شود. دکمه‌ی کپی هم کنارش هست. */}
            <div dir="ltr" title={link} className="fx-input text-[13px] flex-1"
              style={{ fontFamily: "var(--mono)", overflow: "hidden",
                       textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {link}
            </div>
            <button className="fx-ico-btn" style={{ width: 32, height: 32 }}
              aria-label="کپی لینک" onClick={() => copy(link, "link")}>
              {copied === "link" ? <Check size={13} style={{ color: "var(--ok)" }} />
                : <Copy size={13} />}
            </button>
          </div>
        </div>
      )}

      {/* ── اعتبار ── */}
      <div className="rounded-xl p-3.5 mt-3"
        style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
        <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
          <div className="flex items-center gap-2">
            <Wallet size={14} style={{ color: "var(--accent-2)" }} />
            <span className="text-[13px]" style={{ color: "var(--muted)" }}>
              {prepaid ? "اعتبار باقی‌مانده" : "بدون سقف"}
            </span>
            <span className="text-[14px] font-bold"
              style={{ color: prepaid
                ? (Number(t.credit) > 0 ? "var(--ok)" : "var(--danger)")
                : "var(--dim)" }}>
              {prepaid ? `${faNum(t.credit)} تومان` : "صورتحساب ماهانه"}
            </span>
          </div>
          <button onClick={showLog} className="fx-btn-g px-2.5 py-1.5 text-[12px]
                                               flex items-center gap-1">
            <History size={12} /> تاریخچه
          </button>
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          <MoneyInput value={topup}
            onChange={(e) => setTopup(e.target.value)}
            placeholder="100000"
            title="مبلغ شارژ به تومان — منفی یعنی برداشت"
            aria-label="مبلغ شارژ به تومان"
            className="fx-input text-[13px]"
            style={{ width: 150, fontFamily: "var(--mono)" }}  />
          <button disabled={busy || !topup}
            onClick={() => setCredit({ amount: Number(topup) },
              `اعتبار ${faNum(Math.abs(Number(topup)))} تومان `
              + (Number(topup) > 0 ? "شارژ شد" : "برداشت شد"))}
            className="fx-btn px-3 py-2 text-[13px] flex items-center gap-1">
            <Plus size={12} /> اعمال
          </button>
          {prepaid ? (
            <button disabled={busy}
              onClick={() => setCredit({ unlimited: true },
                "روی بدهکاری تنظیم شد — آخر ماه صورتحساب می‌گیرد")}
              className="fx-btn-g px-3 py-2 text-[13px]">
              بدون سقف کن
            </button>
          ) : (
            <span className="text-[12px]" style={{ color: "var(--muted)" }}>
              برای پیش‌پرداخت کردن، یک مبلغ مثبت وارد کنید
            </span>
          )}
        </div>

        {log && (
          <div className="mt-3 pt-3" style={{ borderTop: "1px solid var(--border)" }}>
            {!log.length ? (
              <div className="text-[12px]" style={{ color: "var(--muted)" }}>
                هنوز تغییری ثبت نشده
              </div>
            ) : log.map((r, i) => (
              <div key={i} className="flex items-center justify-between gap-2
                                      py-1.5 text-[12px]">
                <span style={{ color: r.amount >= 0 ? "var(--ok)" : "var(--dim)" }}>
                  {r.amount >= 0 ? "+" : "−"}{faNum(Math.abs(r.amount))}
                </span>
                <span style={{ color: "var(--muted)", flex: 1, textAlign: "right" }}>
                  {r.note}
                </span>
                <span dir="ltr" style={{ color: "var(--muted)",
                                         fontFamily: "var(--mono)" }}>
                  {isoToJalaliStamp(r.created_at)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* چه چیزی مانده تا این نماینده بتواند وارد شود.
          بدون این، تنها بازخوردی که مدیر می‌گرفت «رمز نادرست است»
          روی صفحه‌ی ورود بود — که هیچ ربطی به رمز نداشت. */}
      {!ready && (
        <div className="rounded-xl p-3 mt-3 text-[12px] leading-relaxed"
          style={{ background: "var(--warn-wash)",
                   border: "1px solid var(--warn-fill)",
                   color: "var(--warn)" }}>
          <div className="font-semibold mb-1">برای اینکه بتواند وارد شود:</div>
          {!t.portalSlug && <div>• نشانی لینک را بنویسید و ثبت کنید</div>}
          {!t.portalGroup && <div>• گروه x-ui را انتخاب کنید</div>}
          {!t.hasPass && <div>• یک رمز بسازید</div>}
          {t.portalSlug && t.portalGroup && t.hasPass && !on && (
            <div>• پنلش بسته است — دکمه‌ی «بازکردن پنل» را بزنید</div>
          )}
        </div>
      )}
      </div>}

      {ask === "pw" && (
        <ConfirmModal title={`رمزِ تازه برای «${t.name}»`} confirmLabel="رمز تازه بساز"
          desc="رمزِ فعلیِ نماینده همین حالا باطل می‌شود و تا رمزِ تازه را به او ندهید نمی‌تواند وارد شود."
          onCancel={() => setAsk(null)} onConfirm={() => { setAsk(null); newPass(); }} />
      )}
      {ask === "close" && (
        <ConfirmModal title={`بستنِ پنلِ «${t.name}»`} confirmLabel="ببند"
          desc="نشست‌های بازِ نماینده همان لحظه می‌افتند و تا دوباره باز نکنید نمی‌تواند وارد شود. ربات و مشتری‌هایش کار می‌کنند."
          onCancel={() => setAsk(null)}
          onConfirm={() => { setAsk(null); save({ enabled: false }, "پنل بسته شد — نشست‌های بازش همان لحظه افتادند"); }} />
      )}
    </div>
  );
}

/**
 * ساخت نماینده‌ی تازه.
 *
 * تا امروز این فرم نبود و صفحه می‌گفت «از بخش ربات، مستاجر بسازید» —
 * جایی که اصلاً وجود نداشت. یعنی عملاً فقط یک نماینده ممکن بود.
 */
function NewReseller({ password, groups, onDone, onCancel, setMsg }) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [group, setGroup] = useState("");
  const [pw, setPw] = useState(randomPass);
  const [prepaid, setPrepaid] = useState(false);
  const [busy, setBusy] = useState(false);

  // نشانی از نام حدس زده می‌شود تا مدیر دوباره تایپ نکند؛ ولی هر وقت
  // خودش چیزی نوشت، دیگر دست نمی‌خورد.
  const [slugTouched, setSlugTouched] = useState(false);
  const guess = (v) => v.trim().toLowerCase()
    .replace(/[^a-z0-9-_]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 32);

  const create = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/tenant`, {
        method: "POST",
        headers: { "Content-Type": "application/json",
                   "X-Admin-Password": password },
        body: JSON.stringify({
          name, slug: slugTouched ? slug : guess(name), group,
          password: pw, credit: prepaid ? 0 : -1,
        }),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(errText(j.detail, "ساخته نشد"));
      setMsg({ t: "ok", m: `نماینده «${name}» ساخته شد — ${j.next || ""}` });
      setName(""); setSlug(""); setGroup(""); setPw(randomPass());
      setSlugTouched(false);
      onDone();
    } catch (e) {
      setMsg({ t: "err", m: e.message });
    } finally { setBusy(false); }
  };

  const shownSlug = slugTouched ? slug : guess(name);
  const ready = name.trim() && shownSlug && pw.length >= 8;

  return (
    <div className="fx-card p-5 mb-4">
      <div className="text-[15px] font-bold text-white mb-4">نماینده‌ی جدید</div>

      <div className="grid gap-3" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <Field label="نام نماینده">
          <input value={name} onChange={(e) => setName(e.target.value)}
            className="fx-input w-full" placeholder="مثلاً علی" />
        </Field>

        <Field label="نشانی لینک">
          <input value={shownSlug} dir="ltr"
            onChange={(e) => { setSlugTouched(true); setSlug(e.target.value); }}
            className="fx-input w-full" placeholder="ali" />
        </Field>

        <Field label="گروه x-ui">
          <select value={group} onChange={(e) => setGroup(e.target.value)}
            className="fx-input w-full">
            <option value="">— بعداً انتخاب می‌کنم —</option>
            {(groups || []).map((g) => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>
        </Field>

        <Field label="رمز ورود">
          <div className="flex gap-2">
            <input value={pw} dir="ltr"
              onChange={(e) => setPw(e.target.value)}
              className="fx-input w-full" />
            <button onClick={() => setPw(randomPass())}
              className="fx-btn-g px-3 text-[13px]">تازه</button>
          </div>
        </Field>
      </div>

      <label className="flex items-center gap-2 mt-3 text-[13px]"
        style={{ color: "var(--dim)" }}>
        <input type="checkbox" checked={prepaid}
          onChange={(e) => setPrepaid(e.target.checked)} />
        پیش‌پرداخت — اعتبار می‌خرد و از آن کم می‌شود
        <span style={{ color: "var(--muted)" }}>
          (بدون این، آخر ماه صورتحساب می‌گیرد)
        </span>
      </label>

      <InfoBox>
        پنلش <b>بسته</b> ساخته می‌شود. تا گروه x-ui و رمزش ثبت نشده،
        بازکردنش فقط یک صفحه‌ی ورود می‌دهد که چیزی نشان نمی‌دهد.
      </InfoBox>

      <div className="flex gap-2 mt-4">
        <button onClick={create} disabled={busy || !ready}
          className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
          {busy ? <Loader2 size={13} className="animate-spin" />
            : <Check size={14} />} بساز
        </button>
        <button onClick={onCancel} disabled={busy}
          className="fx-btn-g px-4 py-2.5 text-[14px]">انصراف</button>
      </div>
    </div>
  );
}


/**
 * اینباندِ هر نماینده.
 *
 * قبلاً این تنظیم سراسری بود و — بدتر — نوشتنش `WHERE` نداشت: هر بار
 * که مالک اینباندهای خودش را ذخیره می‌کرد، همان تنظیم روی تک‌تک
 * نماینده‌ها می‌نشست.
 */
export function ResellerInbounds({ password }) {
  const [sel, setSel] = useState("");
  const { d: data, busy: loading, load: reload } =
    useJson("/api/admin/tenant/portal-list", password);

  const list = (data?.tenants || []);
  // صفحه تا انتخابِ دستی خالی بود؛ اولی خودش انتخاب می‌شود
  useEffect(() => {
    if (!sel && list.length) setSel(String(list[0].id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [list.length]);

  // بعد از هوک‌ها — بی‌این، خطا یک ردیفِ خالیِ «نماینده:» می‌ساخت
  if (data?.error) {
    return (
      <>
        <SectionHead icon={Network} title="اینباند نماینده‌ها" />
        <LoadError what="فهرستِ نماینده‌ها" err={data.error} onRetry={reload} />
      </>
    );
  }

  return (
    <>
      <SectionHead icon={Network} title="اینباند نماینده‌ها"
        desc="تعیین کنید کانفیگ‌های هر نماینده روی کدام اینباندها ساخته شود." />

      <InfoBox>
        فهرست اینباندها از پنل x-ui خودتان خوانده می‌شود — نماینده پنل
        جدا ندارد. چیزی که این‌جا فرق می‌کند فقط <b>انتخاب</b> است.
      </InfoBox>

      <div className="fx-card p-4 mb-4 flex items-center gap-3 flex-wrap">
        <span className="text-[13px]" style={{ color: "var(--dim)" }}>
          نماینده:
        </span>
        {/* قرص به‌جای منوی کشویی: با چند نماینده، همه یک‌جا دیده می‌شوند */}
        <div className="flex gap-1.5 flex-wrap flex-1" role="tablist" aria-label="نماینده">
          {list.map((t) => {
            const on = String(t.id) === String(sel);
            return (
              <button key={t.id} role="tab" aria-selected={on} onClick={() => setSel(String(t.id))}
                className="fx-pill px-3 py-1.5 text-[13px]" style={{
                  background: on ? "var(--accent-soft)" : "var(--surface-3)",
                  color: on ? "var(--accent-2)" : "var(--dim)",
                  border: `1px solid ${on ? "var(--accent-line)" : "var(--border)"}` }}>
                {t.name}
              </button>
            );
          })}
        </div>
        <button onClick={reload} disabled={loading}
          className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
          {loading ? <Loader2 size={13} className="animate-spin" />
            : <RefreshCw size={13} />} تازه‌سازی
        </button>
      </div>

      {!sel ? (
        <EmptyState icon={Users}
          text={list.length ? "یک نماینده را انتخاب کنید"
            : "هنوز نماینده‌ای ساخته نشده"} />
      ) : (
        <BotInboundsSection password={password} tenant={sel} />
      )}
    </>
  );
}


/**
 * قابلیت‌های نماینده‌ها — فروشگاه، پوسته، و تستِ رایگان — در یک کارت.
 *
 * برگه‌ها: docs/specs/2026-09-26-reseller-store-subscription.md،
 * docs/specs/2026-09-26-reseller-floor-trial-addons.md
 *
 * پیش‌تر هر قابلیت کارتِ خودش را داشت و فهرستِ نماینده‌ها دو بار زیرِ هم
 * می‌آمد، هر ردیف با دو دکمه — مالک: «شلوغ و نامنظم، و دکمه‌های باز و
 * بسته‌اش اصلاً کار نمی‌کند». کار نمی‌کردند چون با قیمتِ صفر فقط تاریخ
 * عوض می‌شد و تاریخ آن‌جا خوانده نمی‌شد. حالا «ببند» قفلِ دستی است
 * (`core.addon_open`) و هر خانه‌ی جدول فقط **یک** دکمه دارد.
 *
 * **قیمت را مالک تعیین می‌کند.** صفر یعنی رایگان برای همه — نه «خاموش».
 */
// مسیرها کامل و لفظی — test-seams صدازدن‌ها را از متن پیدا می‌کند
const ADDON_KINDS = {
  store: {
    get: "/api/admin/store-addon", grant: "/api/admin/store-addon/grant",
    title: "فروش از ربات و مینی‌اپ",
    desc: "بی این، ربات و مینی‌اپِ نماینده نمی‌فروشند. کانفیگ‌های فعلیِ مشتری‌ها دست نمی‌خورند.",
  },
  theme: {
    get: "/api/admin/portal-addon", grant: "/api/admin/portal-addon/grant",
    title: "پوسته‌ی شخصی",
    desc: "رنگ و لوگوی خودِ نماینده روی مینی‌اپِ مشتری‌هایش.",
  },
};

async function adminJson(path, password, body) {
  const r = await fetch(`${API_URL}${path}`, body === undefined
    ? { headers: { "X-Admin-Password": password } }
    : { method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(errText(j.detail, "انجام نشد"));
  return j;
}

/** قیمت و مدتِ یک قابلیت — یک کاشیِ کوچک. */
function PriceTile({ k, d, password, onSaved, setMsg }) {
  const K = ADDON_KINDS[k];
  const [price, setPrice] = useState("");
  const [days, setDays] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (d) { setPrice(String(d.price ?? 0)); setDays(String(d.days ?? 30)); }
  }, [d?.price, d?.days]);   // eslint-disable-line react-hooks/exhaustive-deps
  const dirty = d && (Number(price) !== Number(d.price) || Number(days) !== Number(d.days));
  const save = async () => {
    setBusy(true);
    try {
      await adminJson(K.get, password, { price: Number(price) || 0, days: Number(days) || 30 });
      setMsg({ t: "ok", m: `«${K.title}» ذخیره شد` });
      onSaved();
    } catch (e) { setMsg({ t: "err", m: e.message }); } finally { setBusy(false); }
  };
  const free = Number(price) === 0;
  return (
    <div className="rf-tile">
      <b>{K.title}</b>
      <p>{K.desc}</p>
      <div className="rf-fields">
        <label>
          <span>قیمت (تومان)</span>
          <MoneyInput value={price} onChange={(e) => setPrice(e.target.value)} />
        </label>
        <label>
          <span>مدت (روز)</span>
          <NumberInput value={days} onChange={(e) => setDays(e.target.value)} />
        </label>
      </div>
      <div className="rf-foot">
        <span className={free ? "t-ok" : ""}>
          {free ? "رایگان برای همه" : `${faNum(price)} تومان برای ${faNum(days)} روز، از اعتبارِ نماینده`}
        </span>
        {dirty && (
          <button onClick={save} disabled={busy} className="fx-btn px-3 py-1.5 text-[12px]">
            {busy ? <Loader2 size={12} className="animate-spin" /> : "ذخیره"}
          </button>
        )}
      </div>
    </div>
  );
}

/** تستِ رایگانِ نماینده‌ها — عددها را مالک می‌گذارد، نه نماینده. */
function TrialTile({ password, setMsg }) {
  const [d, setD] = useState(null);
  const [f, setF] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    try {
      const j = await adminJson("/api/admin/reseller-trial", password);
      setD(j); setF({ enabled: j.enabled, gb: j.gb, days: j.days, ip_limit: j.ip_limit });
    } catch (e) { setMsg({ t: "err", m: `تستِ نماینده‌ها خوانده نشد: ${e.message}` }); }
  }, [password]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [load]);
  if (!f) return <div className="rf-tile"><b>تستِ رایگان</b><p>در حال بارگذاری…</p></div>;
  const dirty = d && (f.enabled !== d.enabled || (f.enabled && (
    Number(f.gb) !== d.gb || Number(f.days) !== d.days || Number(f.ip_limit) !== d.ip_limit)))
    || (d && d.source !== "set" && f.enabled);
  const save = async () => {
    setBusy(true);
    try {
      const j = await adminJson("/api/admin/reseller-trial", password, {
        enabled: f.enabled, gb: Number(f.gb) || 0, days: Number(f.days) || 0,
        ip_limit: Number(f.ip_limit) || 0 });
      setMsg({ t: "ok", m: j.enabled
        ? `تستِ نماینده‌ها ذخیره شد${j.synced ? ` — روی ${faNum(j.synced)} فروشگاه نشست` : ""}`
        : "تستِ نماینده‌ها خاموش شد" });
      load();
    } catch (e) { setMsg({ t: "err", m: e.message }); } finally { setBusy(false); }
  };
  const put = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <div className="rf-tile">
      <div className="rf-tile-head">
        <b>تستِ رایگان</b>
        <Toggle checked={!!f.enabled} label="تستِ رایگانِ نماینده‌ها"
          onChange={() => setF({ ...f, enabled: !f.enabled })} />
      </div>
      <p>
        نماینده فقط روشن یا خاموشش می‌کند؛ حجم و مدت را شما تعیین می‌کنید. هزینه‌اش با شماست و
        در صورتحسابِ نماینده نمی‌آید.
      </p>
      {f.enabled ? (
        <div className="rf-fields rf-fields-3">
          <label><span>حجم (گیگ)</span><NumberInput value={f.gb} onChange={put("gb")} /></label>
          <label><span>مدت (روز)</span><NumberInput value={f.days} onChange={put("days")} /></label>
          <label><span>کاربر</span><NumberInput value={f.ip_limit} onChange={put("ip_limit")} /></label>
        </div>
      ) : null}
      <div className="rf-foot">
        <span className={f.enabled ? "t-ok" : ""}>
          {!f.enabled ? "خاموش — نماینده‌ها تست نمی‌دهند"
            : d.source === "own" ? "هنوز ذخیره نشده — فعلاً تستِ خودتان ملاک است"
              : `${faNum(d.resellersWithTrial)} فروشگاه تست دارد`}
        </span>
        {dirty && (
          <button onClick={save} disabled={busy} className="fx-btn px-3 py-1.5 text-[12px]">
            {busy ? <Loader2 size={12} className="animate-spin" /> : "ذخیره"}
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * «نامحدود» چند گیگ است — برای کفِ پلن‌های نامحدودِ نماینده‌های حجمی.
 * مالک: «نامحدودی که ما تعریف می‌کنیم ۲۰۰ گیگ است».
 */
function UnlimitedTile({ password, setMsg }) {
  const [d, setD] = useState(null);
  const [gb, setGb] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    try {
      const j = await adminJson("/api/admin/reseller-unlimited", password);
      setD(j); setGb(String(j.gb));
    } catch (e) { setMsg({ t: "err", m: `«نامحدود» خوانده نشد: ${e.message}` }); }
  }, [password]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [load]);
  const save = async () => {
    setBusy(true);
    try {
      const j = await adminJson("/api/admin/reseller-unlimited", password, { gb: Number(gb) || 0 });
      setMsg({ t: "ok", m: `نامحدود = ${faNum(j.gb)} گیگ${j.plansUpdated ? ` — کفِ ${faNum(j.plansUpdated)} پلن به‌روز شد` : ""}` });
      load();
    } catch (e) { setMsg({ t: "err", m: e.message }); } finally { setBusy(false); }
  };
  return (
    <div className="rf-tile">
      <b>نامحدود یعنی چند گیگ؟</b>
      <p>کفِ پلنِ «نامحدود» نماینده‌هایی که نرخشان حجمی است: این حجم × نرخِ هر گیگ.</p>
      <div className="rf-fields rf-fields-1">
        <label><span>حجم (گیگ)</span>
          <NumberInput value={gb} onChange={(e) => setGb(e.target.value)} /></label>
      </div>
      <div className="rf-foot">
        <span>{d ? `الان ${faNum(d.gb)} گیگ` : "…"}</span>
        {d && Number(gb) !== d.gb && (
          <button onClick={save} disabled={busy} className="fx-btn px-3 py-1.5 text-[12px]">
            {busy ? <Loader2 size={12} className="animate-spin" /> : "ذخیره"}
          </button>
        )}
      </div>
    </div>
  );
}

/** یک خانه‌ی جدول: وضعیت + یک دکمه. */
function AddonCell({ r, free, busy, onGrant }) {
  const label = r.blocked ? "بسته به‌دستِ شما"
    : r.open ? (free ? "باز" : r.until ? `تا ${isoToJalaliLabel(r.until)}` : "باز")
      : "تمام شده";
  const tone = r.open ? "t-ok" : r.blocked ? "t-danger" : "t-warn";
  return (
    <div className="rf-cell">
      <span className={`rf-chip ${tone}`}>{label}</span>
      <button onClick={() => onGrant(r.open ? 0 : 1)} disabled={busy}
        className="fx-btn-g rf-act"
        title={r.open ? "بستن برای این نماینده — حتی اگر رایگان باشد"
          : free ? "بازکردن" : "بازکردن به مدتِ همان روزهای بالا، بی‌پول"}>
        {busy ? <Loader2 size={12} className="animate-spin" /> : r.open ? "ببند" : "باز کن"}
      </button>
    </div>
  );
}

export function ResellerFeatures({ password }) {
  const [d, setD] = useState({ store: null, theme: null });
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    try {
      const [st, th] = await Promise.all([
        adminJson(ADDON_KINDS.store.get, password),
        adminJson(ADDON_KINDS.theme.get, password),
      ]);
      setD({ store: st, theme: th }); setErr("");
    } catch (e) { setErr(e.message); }
  }, [password]);
  useEffect(() => { load(); }, [load]);

  const grant = async (k, r, open) => {
    setBusy(`${k}${r.id}`);
    try {
      await adminJson(ADDON_KINDS[k].grant, password,
        { tenant: r.id, days: open ? (Number(d[k]?.days) || 30) : 0 });
      setMsg({ t: "ok", m: `«${ADDON_KINDS[k].title}» برای ${r.name || `#${r.id}`} ${open ? "باز" : "بسته"} شد` });
      await load();
    } catch (e) { setMsg({ t: "err", m: e.message }); } finally { setBusy(""); }
  };

  const rows = (d.store?.resellers || []).map((r) => ({
    ...r, theme: (d.theme?.resellers || []).find((x) => x.id === r.id) || null,
  }));

  return (
    <section className="fx-card p-4 mb-4 rf-card">
      <div className="text-[14px] font-semibold text-white mb-1">قابلیت‌های نماینده‌ها</div>
      <p className="text-[12px] leading-relaxed mb-3" style={{ color: "var(--muted)" }}>
        قیمت صفر یعنی رایگان برای همه. «ببند» برای یک نماینده حتی وقتی رایگان است هم می‌بندد.
      </p>
      <Msg msg={msg} onClose={() => setMsg(null)} />
      {err && !d.store ? (
        <LoadError what="قابلیت‌های نماینده‌ها" err={err} onRetry={load} />
      ) : (
        <>
          <div className="rf-tiles">
            <PriceTile k="store" d={d.store} password={password} onSaved={load} setMsg={setMsg} />
            <PriceTile k="theme" d={d.theme} password={password} onSaved={load} setMsg={setMsg} />
            <TrialTile password={password} setMsg={setMsg} />
            <UnlimitedTile password={password} setMsg={setMsg} />
          </div>
          {rows.length > 0 && (
            <div className="rf-table" role="table" aria-label="وضعیتِ قابلیت‌ها برای هر نماینده">
              <div className="rf-tr rf-th" role="row">
                <span role="columnheader">نماینده</span>
                <span role="columnheader">{ADDON_KINDS.store.title}</span>
                <span role="columnheader">{ADDON_KINDS.theme.title}</span>
              </div>
              {rows.map((r) => (
                <div key={r.id} className="rf-tr" role="row">
                  <span className="rf-name" role="cell">{r.name || `#${r.id}`}</span>
                  <span role="cell" data-label={ADDON_KINDS.store.title}>
                    <AddonCell r={r} free={!(d.store?.price > 0)} busy={busy === `store${r.id}`}
                      onGrant={(o) => grant("store", r, o)} />
                  </span>
                  <span role="cell" data-label={ADDON_KINDS.theme.title}>
                    {r.theme && (
                      <AddonCell r={r.theme} free={!(d.theme?.price > 0)} busy={busy === `theme${r.id}`}
                        onGrant={(o) => grant("theme", r.theme, o)} />
                    )}
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}


export function PortalAdmin({ password }) {
  const [msg, setMsg] = useState(null);
  const [adding, setAdding] = useState(false);
  const { d: data, busy: loading, load: reload } =
    useJson("/api/admin/tenant/portal-list", password);

  // از همان فهرستی که در دست است
  const tenantList = (data?.tenants || []);
  const openCount = tenantList.filter((t) => t.portalEnabled).length;
  const unlimitedCount = tenantList.filter((t) => Number(t.credit) < 0).length;
  const creditSum = tenantList.reduce(
    (a, t) => a + Math.max(0, Number(t.credit) || 0), 0);
  const noGroupCount = tenantList.filter((t) => !t.portalGroup).length;

  return (
    <>
      <SectionHead icon={Link2} title="پنل نمایندگی"
        desc="به هر نماینده یک لینک و رمز بدهید تا لازم نباشد پنل x-ui خودتان را در اختیارش بگذارید." />

      <Msg msg={msg} onClose={() => setMsg(null)} />

      {/* وضعیت نماینده‌ها در یک نگاه.
          «کدامشان پنلشان باز است» و «مجموع اعتبارِ دستشان چقدر است»
          سؤال‌هایی بودند که باید با باز کردنِ تک‌تک ردیف‌ها جواب
          می‌گرفتند. نماینده‌ی بی‌گروه هم باید دیده شود: کانفیگی که
          می‌سازد به هیچ صورتحسابی نمی‌چسبد. */}
      {tenantList.length > 0 && (
        <div className="fx-g3 grid grid-cols-3 gap-3">
          <StatTile label="نماینده" icon={Users} tone="var(--accent-2)"
            value={faNum(tenantList.length)}
            hint={`${faNum(openCount)} نفر پنلشان باز است`} />
          <StatTile label="مجموع اعتبار" icon={Wallet} tone="var(--ok)"
            value={faNum(creditSum)} unit="تومان" color="var(--ok)"
            hint={unlimitedCount
                  ? `${faNum(unlimitedCount)} نفر بدون سقف`
                  : "اعتبارِ پیش‌پرداختِ دستشان"} />
          <StatTile label="بدون گروه" icon={AlertTriangle}
            tone={noGroupCount ? "var(--warn)" : "var(--ok)"}
            value={faNum(noGroupCount)}
            color={noGroupCount ? "var(--warn)" : "var(--ok)"}
            hint={noGroupCount ? "کانفیگشان به صورتحساب نمی‌چسبد" : "همه گروه دارند"} />
        </div>
      )}

      <InfoBox>
        نماینده از لینک خودش فقط کانفیگ‌های گروه خودش را می‌بیند و می‌تواند
        بسازد و تمدید کند. نه کانفیگ نماینده‌های دیگر، نه مشتری‌های مستقیم
        شما، نه رمز پنل x-ui.
      </InfoBox>

      {/* بدون این، نخواندنِ فهرست گروه‌ها بی‌صدا می‌ماند و مدیر فقط
          یک منوی خالی می‌دید. */}
      {data?.groupsError && (
        <div className="fx-card p-4 mb-4 text-[13px]"
          style={{ borderColor: "var(--warn-line)", color: "var(--warn)" }}>
          فهرست گروه‌های x-ui خوانده نشد: {data.groupsError}
          <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
            گروهِ ثبت‌شده‌ی هر نماینده سر جایش است؛ فقط نمی‌توانید از
            فهرست انتخاب کنید تا اتصال پنل درست شود.
          </div>
        </div>
      )}

      <div className="flex justify-between items-center gap-2 mb-3 flex-wrap">
        <button title="افزودن" onClick={() => setAdding((v) => !v)}
          className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
          <Plus size={14} /> {adding ? "بستن فرم" : "نماینده‌ی جدید"}
        </button>
        <button onClick={reload} disabled={loading}
          className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
          {loading ? <Loader2 size={13} className="animate-spin" />
            : <RefreshCw size={13} />} تازه‌سازی
        </button>
      </div>

      {/* بیرون از ردیفِ دکمه‌ها، وگرنه فرم فقط یک ستون از عرض را
          می‌گیرد و کنارش یک ستونِ خالیِ بزرگ می‌ماند. */}
      {adding && (
        <NewReseller password={password} groups={data?.groups}
          onDone={() => { setAdding(false); reload(); }}
          onCancel={() => setAdding(false)} setMsg={setMsg} />
      )}

      {!data ? (
        <EmptyState icon={Users} text={loading ? "در حال بارگذاری…"
          : "فهرست نماینده‌ها خوانده نشد"} />
      ) : data.error ? (
        /* خطا — چه از fetch، چه `ready: false`ِ خودِ بکند — پیش‌تر به شاخه‌ی
           «هنوز نماینده‌ای ساخته نشده» می‌افتاد، چون `tenants` خالی بود */
        <LoadError what="فهرستِ نماینده‌ها" err={data.error} onRetry={reload} />
      ) : !(data.tenants || []).length ? (
        <EmptyState icon={Users}
          text="هنوز نماینده‌ای ساخته نشده — دکمه‌ی «نماینده‌ی جدید» بالا" />
      ) : (
        (data.tenants || []).map((t) => (
          <Row key={t.id} t={t} groups={data.groups} password={password}
            onSaved={reload} setMsg={setMsg} />
        ))
      )}

      {/* قیمت‌گذاری بعد از فهرست: کاری است که یک‌بار انجام می‌شود، و
          بالای صفحه فهرستِ نماینده‌ها — کارِ هرروزه — را زیرِ تا می‌برد */}
      <div className="mt-6" />
      <ResellerFeatures password={password} />
    </>
  );
}
