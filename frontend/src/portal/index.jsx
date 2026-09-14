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
  AlertTriangle, Bot, Check, Copy, Database, Link2, LogOut, Loader2, Package,
  Plus, Power, RefreshCw, Search, Trash2, Users, Wallet, X,
} from "lucide-react";

import { API_URL } from "../lib/constants";
import { errText, faNum } from "../lib/format";
import { isoToJalaliLabel } from "../ui/jalali";

const TOKEN_KEY = "nexora_portal_token";

/** نشانی نماینده از آدرس صفحه: /r/<slug> */
export function portalSlug() {
  const m = /^\/r\/([A-Za-z0-9_-]+)/.exec(window.location.pathname || "");
  return m ? m[1] : "";
}

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

function Stat({ icon: Icon, label, value, hint, color }) {
  return (
    <div className="fx-card p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon size={14} style={{ color: color || "var(--accent-2)" }} />
        <span className="text-[12px]" style={{ color: "var(--muted)" }}>{label}</span>
      </div>
      <div className="text-[20px] font-bold" style={{ color: color || "var(--text)" }}>
        {value}
      </div>
      {hint && (
        <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>{hint}</div>
      )}
    </div>
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


function NewBox({ token, plans, onDone, onClose }) {
  const tiers = plans?.plans || [];
  const [gb, setGb] = useState(tiers[0] ? tiers[0].gb : 0);
  const [months, setMonths] = useState(1);
  const [devices, setDevices] = useState(1);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [made, setMade] = useState(null);

  const tier = tiers.find((x) => x.gb === gb);
  const extra = devices > 1 ? devices - 1 : 0;
  const total = tier
    ? (tier.price + (tier.perDevice || 0) * extra) * months : null;

  const go = async () => {
    setBusy(true);
    setErr("");
    try {
      const j = await api("/api/portal/config", {
        token, method: "POST", body: { gb, months, devices },
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

            <label className="text-[12px] block mb-1.5" style={{ color: "var(--muted)" }}>
              تعداد کاربر هم‌زمان
            </label>
            <input type="number" min="1" max="20" dir="ltr" value={devices}
              onChange={(e) => setDevices(Math.max(1, Math.min(20, Number(e.target.value) || 1)))}
              className="fx-input w-full text-center mb-3"
              style={{ fontFamily: "var(--mono)" }} />

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
                      <input type="number" dir="ltr" min="0" value={r[k] ?? 0}
                        onChange={(e) => patch(i, { [k]: Number(e.target.value) || 0 })}
                        className="fx-input text-[13px] text-center"
                        style={{ fontFamily: "var(--mono)" }} />
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


function Dashboard({ token, onOut }) {
  const [me, setMe] = useState(null);
  const [sum, setSum] = useState(null);
  const [list, setList] = useState(null);
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [plans, setPlans] = useState(null);
  const [renew, setRenew] = useState(null);
  const [making, setMaking] = useState(false);
  const [botOpen, setBotOpen] = useState(false);
  const [plansOpen, setPlansOpen] = useState(false);
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

  const rows = (list?.configs || []).filter(
    (c) => !q || String(c.email).toLowerCase().includes(q.toLowerCase()));

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
          <div className="flex items-center gap-2">
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

        {sum && (
          <div className="fx-g4 grid grid-cols-4 gap-3 mb-4">
            <Stat icon={Users} label="کانفیگ‌ها" value={faNum(sum.configs)}
              hint={list ? `${faNum(list.active)} فعال` : ""} />
            <Stat icon={RefreshCw} label="تمدیدها" value={faNum(sum.renewals)}
              hint={`${faNum(sum.months)} ماه در مجموع`} />
            <Stat icon={Database} label="مصرف" value={`${faNum(sum.usedGB)} GB`} />
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

          {!list ? (
            <p className="text-[13px] py-6 text-center" style={{ color: "var(--muted)" }}>
              {busy ? "در حال بارگذاری…" : "چیزی برای نمایش نیست"}
            </p>
          ) : !rows.length ? (
            <p className="text-[13px] py-6 text-center" style={{ color: "var(--muted)" }}>
              {q ? "با این جست‌وجو چیزی پیدا نشد" : "هنوز کانفیگی ندارید"}
            </p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table className="fx-table">
                <thead>
                  <tr>
                    <th>نام کاربر</th><th>حجم</th><th>مصرف</th>
                    <th>دستگاه</th><th>انقضا</th><th>وضعیت</th><th></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((c) => (
                    <tr key={c.email}>
                      <td dir="ltr" style={{ fontFamily: "var(--mono)" }}>{c.email}</td>
                      <td>{c.gb === 0 ? "∞" : `${faNum(c.gb)} GB`}</td>
                      <td>
                        {faNum(c.usedGB)} GB
                        {c.usagePct !== null && (
                          <span className="text-[12px]"
                            style={{ color: c.usagePct >= 90 ? "var(--warn)" : "var(--muted)" }}>
                            {" "}({faNum(c.usagePct)}٪)
                          </span>
                        )}
                      </td>
                      <td>{c.devices ? faNum(c.devices) : "∞"}</td>
                      <td>
                        {c.expiryJalali || "—"}
                        {c.daysLeft !== null && c.daysLeft <= 7 && (
                          <span className="text-[12px]" style={{ color: "var(--warn)" }}>
                            {" "}{c.daysLeft < 0 ? "منقضی" : `${faNum(c.daysLeft)} روز`}
                          </span>
                        )}
                      </td>
                      <td>
                        {c.active ? (
                          <span style={{ color: "var(--ok)" }}>
                            <Check size={12} className="inline" /> فعال
                          </span>
                        ) : (
                          <span style={{ color: "var(--muted)" }}>غیرفعال</span>
                        )}
                      </td>
                      <td>
                        <div className="flex items-center gap-1.5 justify-end">
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
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {renew && (
        <RenewBox token={token} row={renew} plans={plans}
          onClose={() => setRenew(null)}
          onDone={(m) => { setRenew(null); setNote(m); setErr(""); load(); }} />
      )}

      {making && (
        <NewBox token={token} plans={plans}
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
    </div>
  );
}

// ═══════════════════════════════════════════════════════════

export default function Portal() {
  const slug = portalSlug();
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || "");

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
