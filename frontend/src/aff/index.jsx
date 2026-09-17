/**
 * پنل همکار فروش — فقط خواندنی.
 *
 * برگه‌اش: docs/specs/2026-09-17-affiliate-portal.md
 *
 * همکار هیچ چیزی را عوض نمی‌کند: نه پرداخت ثبت می‌کند، نه درصد.
 * فقط می‌بیند چند مشتری آورده، چقدر درآورده و چقدر طلب دارد —
 * بدون اینکه هر بار از مالک بپرسد.
 *
 * و عددِ مانده از همان تابعی می‌آید که پنلِ مالک به کار می‌برد.
 * اگر این‌جا دوباره حساب می‌شد، روزی دو عدد می‌دادند و همان
 * می‌شد موضوعِ بحث.
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle, Coins, LogOut, RefreshCw, TrendingUp, Users, Wallet,
} from "lucide-react";

import { API_URL } from "../lib/constants";
import { errText, faDate, faNum, toFaDigits } from "../lib/format";
import { Avatar, EmptyState, SectionHead, Skeleton } from "../ui/index";
import { isoToJalaliLabel } from "../ui/jalali";

const KEY = "nexora_aff_token";

async function call(path, token, opt = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    method: opt.method || "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-Aff-Token": token } : {}),
    },
    ...(opt.body ? { body: JSON.stringify(opt.body) } : {}),
  });
  const j = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(errText(j.detail, "درخواست ناموفق بود"));
  return j;
}

function Login({ onIn }) {
  const [code, setCode] = useState("");
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const go = async (e) => {
    e?.preventDefault();
    if (!code.trim() || !pw || busy) return;
    setBusy(true); setErr("");
    try {
      const j = await call("/api/aff/login", null,
        { method: "POST", body: { code: code.trim(), password: pw } });
      try { localStorage.setItem(KEY, j.token); } catch { /* بی‌صدا */ }
      onIn(j.token);
    } catch (e2) { setErr(e2.message); } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen grid place-items-center p-5" style={{ background: "var(--bg)" }}>
      <form onSubmit={go} className="fx-card p-6 w-full" style={{ maxWidth: 380 }}>
        <div className="text-center mb-5">
          <div className="fx-aff-badge"><Coins size={20} /></div>
          <h1 className="text-[17px] font-bold text-white mt-3">پنل همکار فروش</h1>
          <p className="text-[12.5px] mt-1.5" style={{ color: "var(--muted)" }}>
            کد همکاری و رمزی که برایتان تعریف شده را وارد کنید
          </p>
        </div>

        <div className="mn-field">
          <label htmlFor="aff-code">کد همکاری</label>
          <input id="aff-code" dir="ltr" value={code} autoCapitalize="characters"
            onChange={(e) => setCode(e.target.value)} placeholder="AFF1" />
        </div>

        <div className="mn-field">
          <label htmlFor="aff-pw">رمز</label>
          <input id="aff-pw" type="password" value={pw}
            onChange={(e) => setPw(e.target.value)} placeholder="••••••" />
        </div>

        {err && (
          <p className="text-[12.5px] mb-3 flex items-start gap-1.5"
            style={{ color: "var(--danger)" }}>
            <AlertTriangle size={13} className="shrink-0 mt-0.5" />{err}
          </p>
        )}

        <button type="submit" className="fx-btn w-full py-2.5 text-[14px]"
          disabled={busy || !code.trim() || !pw}>
          {busy ? "در حال ورود…" : "ورود"}
        </button>
      </form>
    </div>
  );
}

function Money({ icon: Icon, label, value, tone }) {
  return (
    <div className="fx-card p-4">
      <div className="flex items-center justify-between mb-2.5">
        <span className="text-[12px]" style={{ color: "var(--muted)" }}>{label}</span>
        <Icon size={15} style={{ color: tone || "var(--muted)" }} />
      </div>
      <b className="fx-stat-num text-[21px]" style={{ color: tone || "var(--text)" }}>
        {faNum(value)}
      </b>
      <span className="text-[11.5px] mr-1.5" style={{ color: "var(--muted)" }}>تومان</span>
    </div>
  );
}

export default function AffApp() {
  const [token, setToken] = useState(() => {
    try { return localStorage.getItem(KEY) || ""; } catch { return ""; }
  });
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (t) => {
    if (!t) return;
    setBusy(true); setErr("");
    try {
      setD(await call("/api/aff/summary", t));
    } catch (e) {
      setErr(e.message);
      // نشستِ تمام‌شده یعنی باید دوباره وارد شود، نه اینکه یک
      // صفحه‌ی خالی با پیامِ قرمز ببیند
      if (/نشست|بسته/.test(e.message)) {
        try { localStorage.removeItem(KEY); } catch { /* بی‌صدا */ }
        setToken(""); setD(null);
      }
    } finally { setBusy(false); }
  }, []);

  useEffect(() => { load(token); }, [token, load]);

  const out = async () => {
    try { await call("/api/aff/logout", token, { method: "POST" }); } catch { /* بی‌صدا */ }
    try { localStorage.removeItem(KEY); } catch { /* بی‌صدا */ }
    setToken(""); setD(null);
  };

  if (!token) return <Login onIn={setToken} />;

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }} dir="rtl">
      <header className="fx-topbar">
        <div className="flex items-center gap-3 min-w-0">
          <Avatar name={d?.name} id={d?.code} size={36} ring />
          <div className="min-w-0">
            <h1 className="text-[15px] font-bold text-white truncate">
              {d?.name || "همکار فروش"}
            </h1>
            <p className="text-[12px] mt-0.5" style={{ color: "var(--muted)" }}>
              کد <span dir="ltr" className="fx-idnum">{d?.code || "—"}</span>
              {d ? ` · ${faNum(d.percent)}٪ پورسانت` : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5"
            onClick={() => load(token)} disabled={busy}>
            <RefreshCw size={13} className={busy ? "animate-spin" : ""} /> تازه‌سازی
          </button>
          <button className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5"
            onClick={out}>
            <LogOut size={13} /> خروج
          </button>
        </div>
      </header>

      <main className="fx-main p-5">
        {err && (
          <p className="text-[13px] mb-4 flex items-start gap-1.5"
            style={{ color: "var(--danger)" }}>
            <AlertTriangle size={13} className="shrink-0 mt-0.5" />{err}
          </p>
        )}

        {!d ? (
          <div className="fx-g3 grid grid-cols-3 gap-3">
            {[0, 1, 2].map((i) => <Skeleton key={i} h={96} />)}
          </div>
        ) : (
          <>
            <div className="fx-g3 grid grid-cols-3 gap-3 mb-5">
              <Money icon={TrendingUp} label="کل پورسانت" value={d.earned} />
              <Money icon={Wallet} label="دریافت‌شده" value={d.paid} tone="var(--ok)" />
              <Money icon={Coins} label="مانده‌ی شما" value={d.balance}
                tone={d.balance > 0 ? "var(--warn)" : undefined} />
            </div>

            <SectionHead icon={Users} title="مشتری‌های شما"
              desc="کسانی که با کد شما وارد شده‌اند. هر خریدشان — نه فقط خرید اول — پورسانت دارد." />
            {!d.users.length ? (
              <EmptyState icon={Users} text="هنوز مشتری‌ای ثبت نشده"
                hint="هر کسی که با لینک یا کد شما وارد ربات شود، این‌جا می‌آید." />
            ) : (
              <div className="fx-rows mb-6">
                {d.users.map((u) => (
                  <div key={u.id} className="fx-row-kv">
                    <span className="flex items-center gap-2 min-w-0">
                      <Avatar name={u.first_name || u.username} id={u.tg_id} size={28} />
                      <b className="truncate">{u.first_name || "بدون نام"}</b>
                      {u.username && (
                        <i className="not-italic text-[12px]" dir="ltr"
                          style={{ color: "var(--muted)" }}>@{u.username}</i>
                      )}
                    </span>
                    <span className="text-[12.5px] shrink-0" style={{ color: "var(--dim)" }}>
                      {faNum(u.orders)} خرید · {faNum(u.spent)} تومان
                    </span>
                  </div>
                ))}
              </div>
            )}

            <SectionHead icon={Coins} title="پورسانت‌ها"
              desc="«تسویه‌شده» یعنی مبلغش در پرداخت‌های زیر آمده." />
            {!d.commissions.length ? (
              <EmptyState icon={Coins} text="هنوز پورسانتی ثبت نشده"
                hint="با اولین خریدِ یکی از مشتری‌هایتان، همین‌جا می‌آید." />
            ) : (
              <div className="fx-rows mb-6">
                {d.commissions.map((c) => (
                  <div key={c.id} className="fx-row-kv">
                    <span className="flex items-center gap-2 min-w-0">
                      <b>{faNum(c.commission)} تومان</b>
                      <i className="not-italic text-[12px]" style={{ color: "var(--muted)" }}>
                        از {faNum(c.order_amount)} · {c.first_name || "—"}
                      </i>
                    </span>
                    <span className="flex items-center gap-2 shrink-0 text-[12px]"
                      style={{ color: "var(--muted)" }}>
                      {isoToJalaliLabel(c.created_at)}
                      <span className="fx-pill" style={c.status === "paid"
                        ? { background: "var(--ok-soft)", color: "var(--ok)" }
                        : { background: "var(--warn-soft)", color: "var(--warn)" }}>
                        {c.status === "paid" ? "تسویه‌شده" : "در انتظار"}
                      </span>
                    </span>
                  </div>
                ))}
              </div>
            )}

            <SectionHead icon={Wallet} title="پرداخت‌های دریافتی"
              desc="آنچه مالک به شما پرداخت کرده و ثبت شده است." />
            {!d.payouts.length ? (
              <EmptyState icon={Wallet} text="هنوز پرداختی ثبت نشده" />
            ) : (
              <div className="fx-rows">
                {d.payouts.map((p) => (
                  <div key={p.id} className="fx-row-kv">
                    <b>{faNum(p.amount)} تومان</b>
                    <span className="text-[12px]" style={{ color: "var(--muted)" }}>
                      {isoToJalaliLabel(p.paid_at)}{p.note ? ` · ${p.note}` : ""}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
