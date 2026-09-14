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
  AlertTriangle, Calendar, Check, Clock, Database, LogOut, Loader2,
  RefreshCw, Search, Users, Wallet,
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

function Dashboard({ token, onOut }) {
  const [me, setMe] = useState(null);
  const [sum, setSum] = useState(null);
  const [list, setList] = useState(null);
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    setErr("");
    try {
      const [m, s, c] = await Promise.all([
        api("/api/portal/me", { token }),
        api("/api/portal/summary", { token }).catch((e) => ({ _err: e.message })),
        api("/api/portal/configs", { token }).catch((e) => ({ _err: e.message })),
      ]);
      setMe(m);
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
            <div className="text-[14px] font-semibold text-white">کانفیگ‌های شما</div>
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
                    <th>دستگاه</th><th>انقضا</th><th>وضعیت</th>
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
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
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
