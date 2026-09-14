/**
 * پنل نمایندگی — سمت مدیر.
 *
 * این‌جا نشانی و رمز هر نماینده ساخته می‌شود و لینکش تحویل داده
 * می‌شود. تا وقتی این صفحه نبود، تنها راهش خط فرمان بود.
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle, Check, Copy, History, Key, Link2, Loader2, Plus, Power,
  RefreshCw, Users, Wallet,
} from "lucide-react";

import { API_URL } from "../lib/constants";
import { errText, faNum } from "../lib/format";
import { EmptyState, Field, InfoBox, Msg, SectionHead } from "../ui/index";


/** همان الگوی بقیه‌ی بخش‌ها: بخوان، نگه دار، دوباره بخوان. */
function useJson(path, password) {
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    setBusy(true);
    try {
      const j = await fetch(`${API_URL}${path}`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setD(j);
    } catch { setD({ ready: false, error: "اتصال برقرار نشد" }); }
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

function Row({ t, groups, password, onSaved, setMsg }) {
  const [slug, setSlug] = useState(t.portalSlug || "");
  const [group, setGroup] = useState(t.portalGroup || "");
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState("");
  const [topup, setTopup] = useState("");
  const [log, setLog] = useState(null);

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
      const j = await fetch(
        `${API_URL}/api/admin/tenant/${t.id}/credit-log`,
        { headers: { "X-Admin-Password": password } }).then((r) => r.json());
      setLog(j.rows || []);
    } catch {
      setMsg({ t: "err", m: "تاریخچه خوانده نشد" });
    }
  };

  return (
    <div className="fx-card p-5 mb-3">
      <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-[14px] font-semibold text-white">{t.name}</span>
          <span className="fx-pill" style={{
            background: on ? "rgba(52,211,153,.14)" : "var(--surface-3)",
            color: on ? "var(--ok)" : "var(--muted)",
          }}>
            {on ? "پنل باز" : "پنل بسته"}
          </span>
        </div>
        <button disabled={busy}
          onClick={() => save({ enabled: !on },
            on ? "پنل بسته شد — نشست‌های بازش همان لحظه افتادند"
               : "پنل باز شد")}
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
          onClick={() => { const p = randomPass(); setPw(p); save({ password: p },
            "رمز تازه ساخته شد — همین حالا کپی کنید"); }}
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
            <div dir="ltr" className="fx-input text-[13px] flex-1"
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
          <input type="number" dir="ltr" value={topup}
            onChange={(e) => setTopup(e.target.value)}
            placeholder="مبلغ شارژ"
            className="fx-input text-[13px]"
            style={{ width: 150, fontFamily: "var(--mono)" }} />
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
                  {String(r.created_at || "").slice(0, 16)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* چه چیزی مانده تا این نماینده بتواند وارد شود.
          بدون این، تنها بازخوردی که مدیر می‌گرفت «رمز نادرست است»
          روی صفحه‌ی ورود بود — که هیچ ربطی به رمز نداشت. */}
      {(!t.portalGroup || !t.hasPass || !on) && (
        <div className="rounded-xl p-3 mt-3 text-[12px] leading-relaxed"
          style={{ background: "rgba(251,191,36,.07)",
                   border: "1px solid rgba(251,191,36,.22)",
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
    </div>
  );
}

export function PortalAdmin({ password }) {
  const [msg, setMsg] = useState(null);
  const { d: data, busy: loading, load: reload } =
    useJson("/api/admin/tenant/portal-list", password);

  return (
    <>
      <SectionHead icon={Link2} title="پنل نمایندگی"
        desc="به هر نماینده یک لینک و رمز بدهید تا لازم نباشد پنل x-ui خودتان را در اختیارش بگذارید." />

      <Msg msg={msg} onClose={() => setMsg(null)} />

      <InfoBox>
        نماینده از لینک خودش فقط کانفیگ‌های گروه خودش را می‌بیند و می‌تواند
        بسازد و تمدید کند. نه کانفیگ نماینده‌های دیگر، نه مشتری‌های مستقیم
        شما، نه رمز پنل x-ui.
      </InfoBox>

      <div className="flex justify-end mb-3">
        <button onClick={reload} disabled={loading}
          className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
          {loading ? <Loader2 size={13} className="animate-spin" />
            : <RefreshCw size={13} />} تازه‌سازی
        </button>
      </div>

      {!data ? (
        <EmptyState icon={Users} text={loading ? "در حال بارگذاری…"
          : "فهرست نماینده‌ها خوانده نشد"} />
      ) : !(data.tenants || []).length ? (
        <EmptyState icon={Users}
          text="هنوز نماینده‌ای تعریف نشده — از بخش ربات، مستاجر بسازید" />
      ) : (
        (data.tenants || []).map((t) => (
          <Row key={t.id} t={t} groups={data.groups} password={password}
            onSaved={reload} setMsg={setMsg} />
        ))
      )}
    </>
  );
}
