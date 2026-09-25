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
 *
 * مهم‌ترین چیزِ این صفحه «لینکِ دعوت» است، نه عددها: همکار برای
 * پخش‌کردنِ همین لینک این‌جاست. پیش‌تر فقط «کد» نشان داده می‌شد و
 * نه همکار می‌دانست چه بفرستد، نه مالک — لینک فقط داخلِ خودِ ربات
 * دیده می‌شد.
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle, Check, Coins, Copy, Link2, LogOut, RefreshCw, Send, Share2,
  TrendingUp, Users, Wallet,
} from "lucide-react";

import { API_URL } from "../lib/constants";
import { errMsg, errText, faNum } from "../lib/format";
import { Avatar, LongList, Skeleton, StatTile } from "../ui/index";
import { isoToJalaliLabel } from "../ui/jalali";

const KEY = "nexora_aff_token";

async function call(path, token, opt = {}) {
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: opt.method || "GET",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "X-Aff-Token": token } : {}),
      },
      ...(opt.body ? { body: JSON.stringify(opt.body) } : {}),
    });
  } catch (e) {
    // «Failed to fetch»ِ انگلیسیِ مرورگر پیش‌تر همین‌طور روی صفحه می‌آمد
    throw new Error(errMsg(e));
  }
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
      try { localStorage.setItem(KEY, j.token); } catch { /* حالتِ خصوصیِ مرورگر — بی‌یادآوری هم کار می‌کند */ }
      onIn(j.token);
    } catch (e2) { setErr(e2.message); } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen grid place-items-center p-5" style={{ background: "var(--bg)" }} dir="rtl">
      <form onSubmit={go} className="fx-card p-6 w-full" style={{ maxWidth: 380 }}>
        <div className="text-center mb-5">
          <div className="fx-aff-badge"><Coins size={20} /></div>
          <h1 className="text-[17px] font-bold text-white mt-3">پنل همکار فروش</h1>
          <p className="text-[12.5px] mt-1.5 leading-relaxed" style={{ color: "var(--muted)" }}>
            کد همکاری و رمزی را که مدیرِ فروشگاه برایتان فرستاده وارد کنید.
            این‌جا لینکِ دعوتِ خودتان، مشتری‌ها و پورسانتتان را می‌بینید.
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

/** لینکِ دعوت — کپی، و فرستادن از خودِ تلگرام. */
function RefCard({ d }) {
  const [copied, setCopied] = useState("");
  const copy = async (text, what) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(what);
      setTimeout(() => setCopied(""), 1800);
    } catch {
      // کلیپ‌بوردِ بسته (http یا مرورگرِ قدیمی): متن را انتخاب‌پذیر نگه داشته‌ایم
      setCopied("fail");
    }
  };
  const pitch = `با این لینک وارد ربات شوید و اشتراک بگیرید:\n${d.refLink}`;
  const share = d.refLink
    ? `https://t.me/share/url?url=${encodeURIComponent(d.refLink)}&text=${encodeURIComponent("با این لینک وارد ربات شوید و اشتراک بگیرید")}`
    : "";

  return (
    <div className="fx-card p-5 aff-ref">
      <div className="text-[14px] font-semibold text-white flex items-center gap-2">
        <Link2 size={15} style={{ color: "var(--accent-2)" }} /> لینکِ دعوتِ شما
      </div>

      {d.refLink ? (
        <>
          <p className="text-[13px] leading-relaxed mb-3" style={{ color: "var(--dim)" }}>
            همین لینک را برای مشتری‌ها بفرستید. هر کس با آن وارد ربات شود برای همیشه
            مشتریِ شما ثبت می‌شود و از <b>هر خریدش</b> — نه فقط خریدِ اول —
            {" "}<b style={{ color: "var(--warn)" }}>{faNum(d.percent)}٪</b> به شما می‌رسد.
          </p>
          <div className="aff-link" dir="ltr">
            <span className="aff-link-text" title={d.refLink}>{d.refLink}</span>
          </div>
          <div className="flex gap-2 mt-3 flex-wrap">
            <button type="button" className="fx-btn px-4 py-2.5 text-[13.5px] flex items-center gap-1.5"
              onClick={() => copy(d.refLink, "link")}>
              {copied === "link" ? <><Check size={14} /> کپی شد</> : <><Copy size={14} /> کپیِ لینک</>}
            </button>
            <a className="fx-btn-g px-4 py-2.5 text-[13.5px] flex items-center gap-1.5"
              href={share} target="_blank" rel="noreferrer">
              <Send size={14} /> فرستادن در تلگرام
            </a>
            <button type="button" className="fx-btn-g px-4 py-2.5 text-[13.5px] flex items-center gap-1.5"
              onClick={() => copy(pitch, "pitch")}>
              {copied === "pitch" ? <><Check size={14} /> کپی شد</> : <><Share2 size={14} /> کپیِ لینک با متن</>}
            </button>
          </div>
          {copied === "fail" && (
            <p className="text-[12px] mt-2" style={{ color: "var(--warn)" }}>
              مرورگر اجازه‌ی کپی نداد — لینک را از کادرِ بالا انتخاب و کپی کنید.
            </p>
          )}
        </>
      ) : (
        <p className="text-[13px] leading-relaxed" style={{ color: "var(--warn)" }}>
          لینک هنوز ساخته نشده، چون نامِ کاربریِ ربات معلوم نیست. تا مدیر آن را درست کند،
          کدِ خودتان <b dir="ltr" className="fx-idnum">{d.code}</b> را بدهید تا مشتری در ربات
          وارد کند.
        </p>
      )}
    </div>
  );
}

/** سه قدم — چون «کد» و «لینک» برای همکارِ تازه یعنی هیچ. */
function HowItWorks({ percent }) {
  const steps = [
    ["۱", "لینک را بفرستید", "در کانال، گروه یا پیوی — هر جا مشتری دارید."],
    ["۲", "مشتری ربات را باز می‌کند", "با اولین «استارت» از لینکِ شما، به نامِ شما ثبت می‌شود."],
    ["۳", `از هر خرید ${faNum(percent)}٪`, "پورسانت همین‌جا ثبت می‌شود و مدیر تسویه می‌کند."],
  ];
  return (
    <div className="aff-steps">
      {steps.map(([n, t, h]) => (
        <div key={n} className="aff-step">
          <span className="aff-step-n">{n}</span>
          <div className="min-w-0">
            <b className="block text-[13.5px] text-white">{t}</b>
            <span className="block text-[12px] mt-0.5 leading-relaxed" style={{ color: "var(--muted)" }}>{h}</span>
          </div>
        </div>
      ))}
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
        try { localStorage.removeItem(KEY); } catch { /* حالتِ خصوصیِ مرورگر */ }
        setToken(""); setD(null);
      }
    } finally { setBusy(false); }
  }, []);

  useEffect(() => { load(token); }, [token, load]);

  const out = async () => {
    // خروج در سرور بهترین‌تلاش است؛ توکنِ محلی به‌هرحال پاک می‌شود
    try { await call("/api/aff/logout", token, { method: "POST" }); } catch { /* نشست در سرور خودش منقضی می‌شود */ }
    try { localStorage.removeItem(KEY); } catch { /* حالتِ خصوصیِ مرورگر */ }
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
            onClick={() => load(token)} disabled={busy} aria-label="تازه‌سازی">
            <RefreshCw size={13} className={busy ? "animate-spin" : ""} />
            <span className="aff-hide-sm">تازه‌سازی</span>
          </button>
          <button className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5"
            onClick={out} aria-label="خروج">
            <LogOut size={13} /> <span className="aff-hide-sm">خروج</span>
          </button>
        </div>
      </header>

      <main className="aff-main">
        {err && (
          <p className="text-[13px] mb-4 flex items-start gap-1.5"
            style={{ color: "var(--danger)" }}>
            <AlertTriangle size={13} className="shrink-0 mt-0.5" />{err}
          </p>
        )}

        {!d ? (
          <div className="grid gap-3">
            <Skeleton h={150} />
            <div className="fx-g3 grid grid-cols-3 gap-3">
              {[0, 1, 2].map((i) => <Skeleton key={i} h={96} />)}
            </div>
          </div>
        ) : (
          <>
            <RefCard d={d} />
            <HowItWorks percent={d.percent} />

            <div className="fx-g3 grid grid-cols-3 gap-3 mb-4">
              <StatTile label="کل پورسانت" icon={TrendingUp} tone="var(--accent-2)"
                value={faNum(d.earned)} unit="تومان"
                hint={`${faNum(d.commissions.length)} خرید`} />
              <StatTile label="دریافت‌شده" icon={Wallet} tone="var(--ok)"
                value={faNum(d.paid)} unit="تومان" color="var(--ok)"
                hint={`${faNum(d.payouts.length)} پرداخت`} />
              <StatTile label="مانده‌ی شما" icon={Coins}
                tone={d.balance > 0 ? "var(--warn)" : "var(--muted)"}
                value={faNum(d.balance)} unit="تومان"
                color={d.balance > 0 ? "var(--warn)" : undefined}
                hint={d.balance > 0 ? "هنوز تسویه نشده" : "همه تسویه شده"} />
            </div>

            <div className="aff-cols">
              <div className="fx-card p-5">
                <div className="text-[14px] font-semibold text-white flex items-center gap-2">
                  <Users size={15} /> مشتری‌های شما
                  <span className="mr-auto text-[12px] font-normal" style={{ color: "var(--muted)" }}>
                    {faNum(d.users.length)} نفر
                  </span>
                </div>
                <LongList items={d.users} initial={6} label="مشتری"
                  empty="هنوز کسی با لینکِ شما وارد نشده — لینک را بالا کپی کنید و بفرستید.">
                  {(u) => (
                    <div key={u.id} className="aff-row">
                      <span className="flex items-center gap-2 min-w-0">
                        <Avatar name={u.first_name || u.username} id={u.tg_id} size={28} />
                        <span className="min-w-0">
                          <b className="block truncate text-[13px]">{u.first_name || "بدون نام"}</b>
                          {u.username && (
                            <i className="not-italic block text-[11.5px] truncate" dir="ltr"
                              style={{ color: "var(--muted)" }}>@{u.username}</i>
                          )}
                        </span>
                      </span>
                      <span className="text-[12px] shrink-0 text-left" style={{ color: "var(--dim)" }}>
                        {faNum(u.orders)} خرید
                        <span className="block" style={{ color: "var(--muted)" }}>{faNum(u.spent)} تومان</span>
                      </span>
                    </div>
                  )}
                </LongList>
              </div>

              <div className="fx-card p-5">
                <div className="text-[14px] font-semibold text-white flex items-center gap-2">
                  <Wallet size={15} /> پرداخت‌های دریافتی
                </div>
                <LongList items={d.payouts} initial={6} label="پرداخت"
                  empty="هنوز پرداختی ثبت نشده. هر وقت مدیر تسویه کند، این‌جا می‌آید.">
                  {(p) => (
                    <div key={p.id} className="aff-row">
                      <b className="text-[13px]">{faNum(p.amount)} تومان</b>
                      <span className="text-[12px] text-left" style={{ color: "var(--muted)" }}>
                        {isoToJalaliLabel(p.paid_at)}{p.note ? ` · ${p.note}` : ""}
                      </span>
                    </div>
                  )}
                </LongList>
              </div>
            </div>

            <div className="fx-card p-5 mt-4">
              <div className="text-[14px] font-semibold text-white flex items-center gap-2">
                <Coins size={15} /> پورسانت‌ها
              </div>
              <p className="text-[12px] mb-2" style={{ color: "var(--muted)" }}>
                «تسویه‌شده» یعنی مبلغش در پرداخت‌های بالا آمده.
              </p>
              <LongList items={d.commissions} initial={8} label="پورسانت"
                empty="هنوز پورسانتی ثبت نشده — با اولین خریدِ یکی از مشتری‌هایتان این‌جا می‌آید.">
                {(c) => (
                  <div key={c.id} className="aff-row">
                    <span className="min-w-0">
                      <b className="text-[13px]">{faNum(c.commission)} تومان</b>
                      <span className="block text-[11.5px] truncate" style={{ color: "var(--muted)" }}>
                        از خریدِ {faNum(c.order_amount)} تومانیِ {c.first_name || "—"}
                      </span>
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
                )}
              </LongList>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
