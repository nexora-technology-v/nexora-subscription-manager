/**
 * هزینه‌ها و دفتر کل.
 *
 * «درآمد» بدون کم‌کردن هزینه‌ها عددی است که آدم را خوشحال و ورشکسته
 * می‌کند. سرور خارج، سرور ایران و خرید حجم پول واقعی‌اند و باید کنار
 * فروش دیده شوند.
 *
 * نکته‌ی مهم در طراحی: مبلغ تومانی در لحظه‌ی ثبت قفل می‌شود. اگر هر
 * بار با نرخ روز محاسبه کنیم، هزینه‌ی ماه پیش با تکان خوردن بازار
 * عوض می‌شود و هیچ گزارشی قابل اتکا نمی‌ماند.
 */
import React, { useState, useEffect, useCallback } from "react";
import {
  AlertTriangle, Clock, DollarSign, FileText, Loader2, Plus, RefreshCw, Server,
  Trash2, TrendingUp, Wallet,
} from "lucide-react";
import { API_URL } from "../lib/constants";
import { errText, faNum } from "../lib/format";
import { ConfirmModal, EmptyState, Field, InfoBox, Msg, NumberInput, PageSkeleton, SectionHead, StatTile } from "../ui/index";
import { JalaliDate } from "../ui/jalali";

const KIND_META = {
  server_abroad: { label: "سرور خارج", icon: Server, color: "var(--accent-2)" },
  server_iran: { label: "سرور ایران", icon: Server, color: "#34d399" },
  traffic: { label: "خرید حجم", icon: TrendingUp, color: "#fbbf24" },
  domain: { label: "دامنه و گواهی", icon: Wallet, color: "#a78bfa" },
  other: { label: "متفرقه", icon: DollarSign, color: "var(--muted)" },
};

const toman = (n) => `${faNum(Number(n || 0).toLocaleString("en-US")
  .replace(/,/g, "،"))} تومان`;

/** همان عدد، ولی برای رندر در JSX. */
const tomanNum = (n) => faNum(Number(n || 0).toLocaleString("en-US")
  .replace(/,/g, "،"));

/**
 * مبلغ با واحدش، جایی که ظرف فونت مونو دارد.
 *
 * رشته‌ی toman() واحد را به خودِ عدد می‌چسباند. آن رشته وقتی داخل
 * ظرفی با var(--mono) رندر شود، ارقام در JetBrains Mono می‌نشینند —
 * که همان چیزی است که برای هم‌ترازیِ ستون لازم است — ولی «تومان» در
 * آن فونت گلیف ندارد و به مونوی سیستم می‌افتد: اندازه‌گیری‌شده ۳۱٪
 * پهن‌تر از قلمِ خودِ پنل، درست وسط یک عدد.
 *
 * این‌جا عدد در مونو می‌ماند و واحد به قلم اصلی برمی‌گردد.
 */
const Toman = ({ n }) => (
  <>{tomanNum(n)}<span className="fx-fa-sub"> تومان</span></>
);

function useJson(path, password, deps = []) {
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [password, path, ...deps]);
  useEffect(() => { load(); }, [load]);
  return { d, busy, load, setD };
}

/** فرم ثبت هزینه، با تبدیل زنده‌ی ارز پیش از ثبت. */
function ExpenseForm({ password, onDone, setMsg }) {
  const [f, setF] = useState({
    kind: "server_abroad", label: "", amount: "", currency: "EUR",
    recurring: "monthly", gb: "", spentAt: new Date().toISOString().slice(0, 10),
    note: "", rate: "",
  });
  const [fx, setFx] = useState(null);
  const [busy, setBusy] = useState(false);

  // نرخ را فقط وقتی می‌گیریم که ارز غیرتومانی انتخاب شده باشد
  useEffect(() => {
    if (f.currency === "IRT") { setFx(null); return; }
    let alive = true;
    fetch(`${API_URL}/api/admin/billing/fx?currency=${f.currency}`, {
      headers: { "X-Admin-Password": password },
    }).then((r) => r.json()).then((j) => { if (alive) setFx(j); })
      .catch(() => { if (alive) setFx({ ok: false }); });
    return () => { alive = false; };
  }, [f.currency, password]);

  const rate = Number(f.rate) || (fx && fx.ok ? fx.toman : null);
  const preview = rate && f.amount ? Math.round(Number(f.amount) * rate) : null;

  const submit = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/billing/expenses`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Password": password,
        },
        body: JSON.stringify({
          ...f,
          amount: Number(f.amount),
          rate: f.rate ? Number(f.rate) : undefined,
          gb: f.kind === "traffic" && f.gb ? Number(f.gb) : undefined,
        }),
      });
      const j = await res.json().catch(() => ({}));
      if (res.ok) {
        // هشدار نرخ کهنه باید دیده شود. هزینه ثبت شده، ولی با نرخی که
        // لحظه‌ی خرید نبوده — و کل دلیل ذخیره‌ی مبلغ تومانی همین بود.
        setMsg(j.warning
          ? { t: "warn", m: j.warning, keep: true }
          : { t: "ok", m: j.note || "ثبت شد" });
        setF({ ...f, label: "", amount: "", gb: "", note: "" });
        onDone();
      } else setMsg({ t: "err", m: errText(j.detail, "ثبت ناموفق") });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(false); }
  };

  return (
    <div className="fx-card p-5 mb-4">
      <div className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
        <Plus size={15} style={{ color: "var(--accent-2)" }} /> ثبت هزینه‌ی جدید
      </div>

      <div className="fx-g4 grid grid-cols-4 gap-3">
        <Field label="دسته">
          <select className="fx-input" value={f.kind}
            onChange={(e) => setF({ ...f, kind: e.target.value })}>
            {Object.entries(KIND_META).map(([k, m]) => (
              <option key={k} value={k}>{m.label}</option>
            ))}
          </select>
        </Field>
        <Field label="عنوان" hint="مثلاً: هتزنر CX22">
          <input className="fx-input" value={f.label}
            onChange={(e) => setF({ ...f, label: e.target.value })} />
        </Field>
        <Field label="مبلغ">
          <NumberInput decimal className="fx-input"
            value={f.amount} style={{ fontFamily: "var(--mono)" }}
            onChange={(e) => setF({ ...f, amount: e.target.value })}  />
        </Field>
        <Field label="ارز">
          <select className="fx-input" value={f.currency}
            onChange={(e) => setF({ ...f, currency: e.target.value })}>
            <option value="EUR">یورو</option>
            <option value="USD">دلار</option>
            <option value="IRT">تومان</option>
          </select>
        </Field>
      </div>

      <div className="fx-g4 grid grid-cols-4 gap-3 mt-1">
        <Field label="تکرار">
          <select className="fx-input" value={f.recurring}
            onChange={(e) => setF({ ...f, recurring: e.target.value })}>
            <option value="once">یک‌بار</option>
            <option value="monthly">ماهانه</option>
            <option value="yearly">سالانه</option>
          </select>
        </Field>
        <Field label="تاریخ">
          <JalaliDate value={f.spentAt}
            onChange={(v) => setF({ ...f, spentAt: v })} />
        </Field>
        {f.kind === "traffic" ? (
          <Field label="حجم (گیگابایت)">
            <NumberInput className="fx-input" value={f.gb}
              style={{ fontFamily: "var(--mono)" }}
              onChange={(e) => setF({ ...f, gb: e.target.value })}  />
          </Field>
        ) : (
          <Field label="توضیح" hint="اختیاری">
            <input className="fx-input" value={f.note}
              onChange={(e) => setF({ ...f, note: e.target.value })} />
          </Field>
        )}
        {f.currency !== "IRT" && (
          <Field label="نرخ دستی" hint="خالی = نرخ روز بازار">
            <NumberInput className="fx-input" value={f.rate}
              placeholder={fx && fx.ok ? String(fx.toman) : "—"}
              style={{ fontFamily: "var(--mono)" }}
              onChange={(e) => setF({ ...f, rate: e.target.value })}  />
          </Field>
        )}
      </div>

      {f.currency !== "IRT" && (
        <div className="mt-2 text-[12px] flex items-center gap-2 flex-wrap"
          style={{ color: "var(--muted)" }}>
          {!fx ? "در حال گرفتن نرخ…"
            : fx.ok ? (
              <>
                <span>نرخ {f.currency}: <Toman n={fx.toman} /></span>
                {fx.at && <span>· {fx.at}</span>}
                {fx.stale && (
                  <span style={{ color: "var(--warn)" }}>
                    · نرخ کهنه ({faNum(fx.ageMinutes || 0)} دقیقه پیش)
                  </span>
                )}
              </>
            ) : (
              <span style={{ color: "var(--warn)" }}>
                نرخ خوانده نشد — نرخ را دستی وارد کنید
              </span>
            )}
          {preview !== null && (
            <span style={{ color: "var(--accent-2)" }}>
              ← معادل <Toman n={preview} />
            </span>
          )}
        </div>
      )}

      <button onClick={submit} disabled={busy || !f.label || !f.amount}
        className="fx-btn px-4 py-2.5 text-[13px] flex items-center gap-1.5 mt-3">
        {busy ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
        ثبت هزینه
      </button>
    </div>
  );
}

export function BillingExpenses({ password }) {
  const [months, setMonths] = useState(12);
  const { d, busy, load } = useJson(
    `/api/admin/billing/expenses?months=${months}`, password, [months]);
  const [msg, setMsg] = useState(null);
  const [del, setDel] = useState(null);

  useEffect(() => {
    if (msg) {
      if (msg.keep) return;          // هشدار نرخ می‌ماند تا خوانده شود
      const t = setTimeout(() => setMsg(null), 4000);
      return () => clearTimeout(t);
    }
  }, [msg]);

  const remove = async (id) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/billing/expenses/${id}`, {
        method: "DELETE", headers: { "X-Admin-Password": password },
      });
      setMsg(res.ok ? { t: "ok", m: "حذف شد" } : { t: "err", m: "حذف ناموفق" });
      if (res.ok) load();
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setDel(null); }
  };

  if (!d) {
    return (
      <PageSkeleton />
    );
  }

  return (
    <div className="fx-anim">
      <SectionHead title="هزینه‌ها"
        desc="سرور، حجم و دامنه پول واقعی‌اند. تا این‌ها ثبت نشوند، عدد سود فقط یک آرزوست."
        action={(
          <div className="flex items-center gap-2">
            <select className="fx-input" value={months} style={{ width: 130 }}
              onChange={(e) => setMonths(Number(e.target.value))}>
              <option value={3}>۳ ماه اخیر</option>
              <option value={12}>یک سال اخیر</option>
              <option value={120}>همه</option>
            </select>
            <button onClick={load} disabled={busy}
              className="fx-btn-ghost px-3 py-2 text-[13px] flex items-center gap-1.5">
              <RefreshCw size={14} className={busy ? "animate-spin" : ""} />
              تازه‌سازی
            </button>
          </div>
        )} />

      <Msg msg={msg} />

      <div className="fx-g3 grid grid-cols-3 gap-3">
        <StatTile label="هزینه‌ی این بازه" icon={Wallet} tone="var(--danger)"
          value={faNum(d.total || 0)} unit="تومان" color="var(--danger)"
          hint={d.count ? `${faNum(d.count)} قلم هزینه` : "چیزی ثبت نشده"} />
        <StatTile label="هزینه‌ی ثابت ماهانه" icon={RefreshCw} tone="var(--warn)"
          value={faNum(d.monthlyRecurring || 0)} unit="تومان" color="var(--warn)"
          hint={d.monthlyFromYearly > 0
                ? `شامل ${faNum(d.monthlyFromYearly)} از هزینه‌های سالانه`
                : "این مبلغ را هر ماه باید دربیاورید"} />
        <StatTile label="حجم خریداری‌شده" icon={TrendingUp} tone="var(--accent-2)"
          value={faNum(d.trafficGB || 0)} unit="گیگ" color="var(--accent-2)"
          hint={d.trafficCost ? `${faNum(d.trafficCost)} تومان` : "ترافیک خریداری‌شده"} />
      </div>

      <div className="fx-card p-4 mb-4">
        <div className="text-[13px] mb-3" style={{ color: "var(--dim)" }}>
          تفکیک بر اساس دسته
        </div>
        {Object.entries(d.byKind || {}).map(([k, v]) => {
          const m = KIND_META[k] || KIND_META.other;
          const pct = d.total ? Math.round((v * 100) / d.total) : 0;
          return (
            <div key={k} className="flex items-center gap-3 py-2">
              <m.icon size={15} style={{ color: m.color, flexShrink: 0 }} />
              <span className="text-[13px]" style={{ width: 120 }}>{m.label}</span>
              <div className="flex-1 h-2 rounded-full"
                style={{ background: "var(--surface-3)" }}>
                <div className="h-2 rounded-full"
                  style={{ width: `${pct}%`, background: m.color }} />
              </div>
              <span className="text-[13px]" style={{
                fontFamily: "var(--mono)", color: "var(--dim)", width: 130,
                textAlign: "left",
              }}><Toman n={v} /></span>
            </div>
          );
        })}
      </div>

      <ExpenseForm password={password} onDone={load} setMsg={setMsg} />

      <div className="fx-card p-5">
        <div className="text-[14px] font-semibold text-white mb-3">
          هزینه‌های ثبت‌شده
          <span className="text-[13px] font-normal mr-2"
            style={{ color: "var(--muted)" }}>
            ({faNum((d.expenses || []).length)})
          </span>
        </div>

        {!(d.expenses || []).length ? (
          <EmptyState icon={Wallet} text="هنوز هزینه‌ای ثبت نشده" />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="fx-table">
              <thead>
                <tr>
                  <th>تاریخ</th><th>دسته</th><th>عنوان</th>
                  <th>مبلغ</th><th>معادل تومان</th><th>تکرار</th><th></th>
                </tr>
              </thead>
              <tbody>
                {(d.expenses || []).map((e) => {
                  const m = KIND_META[e.kind] || KIND_META.other;
                  return (
                    <tr key={e.id}>
                      <td dir="ltr" style={{
                        fontFamily: "var(--mono)", color: "var(--muted)",
                        fontSize: 12,
                      }}>{e.spent_at}</td>
                      <td style={{ color: m.color }}>{m.label}</td>
                      <td>
                        {e.label}
                        {e.gb ? (
                          <span className="fx-pill mr-2" style={{
                            background: "var(--surface-3)", color: "var(--muted)",
                          }}>{faNum(e.gb)} گیگ</span>
                        ) : null}
                      </td>
                      <td dir="ltr" style={{ fontFamily: "var(--mono)" }}>
                        {e.amount} {e.currency}
                        {e.fx_rate && e.currency !== "IRT" ? (
                          <div className="fx-fa-sub" style={{ fontSize: 11, color: "var(--muted)" }}>
                            نرخ {faNum(e.fx_rate)}
                            {e.fx_source === "manual" ? " (دستی)" : ""}
                          </div>
                        ) : null}
                      </td>
                      <td style={{ fontFamily: "var(--mono)" }}>
                        <Toman n={e.amount_irt} />
                      </td>
                      <td style={{ color: "var(--muted)", fontSize: 12 }}>
                        {e.recurring === "monthly" ? "ماهانه"
                          : e.recurring === "yearly" ? "سالانه" : "یک‌بار"}
                      </td>
                      <td>
                        <button title="حذف این هزینه" onClick={() => setDel(e)}
                          className="fx-btn-ghost px-2 py-1"
                          style={{ color: "var(--danger)" }}>
                          <Trash2 size={13} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {del && (
        <ConfirmModal title="حذف هزینه"
          desc={`«${del.label}» به مبلغ ${toman(del.amount_irt)} حذف می‌شود.`}
          confirmLabel="حذف کن"
          onConfirm={() => remove(del.id)}
          onCancel={() => setDel(null)} />
      )}
    </div>
  );
}

/**
 * دفتر کل — از روز اول تا امروز.
 *
 * مدیر یک سؤال دارد: «در مجموع چقدر جلو هستم و چه کسی به من بدهکار
 * است؟» این صفحه فقط همان را جواب می‌دهد.
 */
export function BillingLedger({ password }) {
  const { d, busy, load } = useJson("/api/admin/billing/ledger", password);

  if (!d) {
    return (
      <PageSkeleton />
    );
  }

  if (d.error) {
    return (
      <div className="fx-anim">
        <SectionHead title="دفتر کل" desc="جمع‌بندی همه‌چیز از روز اول." />
        <InfoBox tone="warn">{d.error}</InfoBox>
      </div>
    );
  }

  const profit = d.profit || 0;

  return (
    <div className="fx-anim">
      <SectionHead title="دفتر کل"
        desc={d.since ? `همه‌ی اعداد از ${d.since} تا امروز` : "جمع‌بندی از روز اول"}
        action={(
          <button onClick={load} disabled={busy}
            className="fx-btn-ghost px-3 py-2 text-[13px] flex items-center gap-1.5">
            <RefreshCw size={14} className={busy ? "animate-spin" : ""} />
            تازه‌سازی
          </button>
        )} />

      <div className="fx-g4 grid grid-cols-4 gap-3">
        <StatTile label="صورت‌حساب‌شده" icon={FileText} tone="var(--accent-2)"
          value={faNum(d.billed || 0)} unit="تومان" color="var(--accent-2)"
          hint="از روز اول تا امروز" />
        <StatTile label="دریافت‌شده" icon={Wallet} tone="var(--ok)"
          value={faNum(d.paid || 0)} unit="تومان" color="var(--ok)"
          hint={d.billed ? `${faNum(Math.round((d.paid || 0) * 100 / d.billed))}٪ از کل` : "از واسطه‌ها"} />
        <StatTile label="طلب شما" icon={Clock}
          tone={(d.outstanding || 0) > 0 ? "var(--warn)" : "var(--ok)"}
          value={faNum(d.outstanding || 0)} unit="تومان"
          color={(d.outstanding || 0) > 0 ? "var(--warn)" : "var(--ok)"}
          hint={(d.outstanding || 0) > 0 ? "هنوز نرسیده" : "همه تسویه‌اند"} />
        <StatTile label="هزینه" icon={TrendingUp} tone="var(--danger)"
          value={faNum(d.spent || 0)} unit="تومان" color="var(--danger)"
          hint="سرور، حجم، دامنه" />
      </div>

      {/* چهار کارت بالا با هم جمع نمی‌خورند وقتی دوره‌ای تسویه شده
          باشد: «صورت‌حساب‌شده» کلِ تاریخ است و «طلب شما» فقط امروز.
          بدون این یک خط، صفحه شبیه خرابی به نظر می‌رسد. */}
      {d.botReceived > 0 && (
        <div className="fx-card p-4 mb-4 flex items-baseline justify-between
                        gap-3 flex-wrap">
          <div>
            <div className="text-[13px]" style={{ color: "var(--dim)" }}>
              فروش مستقیم ربات
            </div>
            <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
              فقط پرداخت‌های کارتی — خریدی که از کیف پول انجام شده پول
              تازه نیست و دوباره شمرده نمی‌شود
            </div>
          </div>
          <div className="text-[19px] font-bold"
            style={{ color: "#34d399", fontFamily: "var(--mono)" }}>
            <Toman n={d.botReceived} />
          </div>
        </div>
      )}

      {(d.affiliatePaid > 0 || d.affiliateOwed > 0) && (
        <div className="fx-card p-4 mb-4 flex items-baseline justify-between
                        gap-3 flex-wrap">
          <div>
            <div className="text-[13px]" style={{ color: "var(--dim)" }}>
              پورسانت معرف‌ها
            </div>
            <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
              {d.affiliateOwed > 0
                ? `${toman(d.affiliateOwed)} هنوز پرداخت نشده — از سود کم نشده`
                : "همه پرداخت شده"}
            </div>
          </div>
          <div className="text-[19px] font-bold"
            style={{ color: "var(--danger)", fontFamily: "var(--mono)" }}>
            −<Toman n={d.affiliatePaid} />
          </div>
        </div>
      )}

      {d.settledGap > 0 && (
        <div className="text-[12px] mb-4 leading-relaxed"
          style={{ color: "var(--muted)" }}>
          {/* toman() خودش واحد را می‌چسباند — «تومان»ِ دوم اینجا اضافه بود */}
          <Toman n={d.settledGap} /> از صورت‌حساب‌شده در دوره‌هایی است که
          تسویه‌شده علامت خورده‌اند، پس در «طلب شما» نمی‌آید.
        </div>
      )}

      <div className="fx-card p-5 mb-4">
        <div className="flex items-baseline justify-between gap-3 flex-wrap">
          <div>
            <div className="text-[13px]" style={{ color: "var(--dim)" }}>
              سود واقعی تا امروز
            </div>
            <div className="text-[28px] font-bold" style={{
              color: profit >= 0 ? "#34d399" : "var(--danger)",
              fontFamily: "var(--mono)",
            }}><Toman n={profit} /></div>
            {/* عددِ بی‌توضیح، مدیر را وامی‌دارد حدس بزند از کجا آمده.
                وقتی ربات هم فروش دارد، سود از دو جا می‌آید. */}
            <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
              {d.botReceived > 0 ? (
                <>
                  (<Toman n={d.paid} /> از واسطه‌ها + <Toman n={d.botReceived} /> از ربات)
                  {" "}منهای <Toman n={d.spent} /> هزینه
                </>
              ) : "دریافتی منهای هزینه — نه آنچه طلب دارید"}
            </div>
          </div>
          <div style={{ textAlign: "left" }}>
            <div className="text-[13px]" style={{ color: "var(--dim)" }}>
              اگر همه تسویه کنند
            </div>
            <div className="text-[19px] font-bold" style={{
              color: "var(--accent-2)", fontFamily: "var(--mono)",
            }}><Toman n={d.profitIfAllPaid} /></div>
          </div>
        </div>
      </div>

      {(d.owing || []).length > 0 && (
        <div className="fx-card p-5 mb-4">
          <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2">
            <AlertTriangle size={15} style={{ color: "var(--warn)" }} />
            بدهکاران
          </div>
          <p className="text-[12px] mb-3" style={{ color: "var(--muted)" }}>
            پرداختی هر واسطه را در صفحه‌ی «پرداخت‌ها» ثبت کنید تا مانده‌اش
            به‌روز شود.
          </p>
          <div style={{ overflowX: "auto" }}>
            <table className="fx-table">
              <thead>
                <tr>
                  <th>واسطه</th><th>کانفیگ</th><th>صورت‌حساب</th>
                  <th>پرداختی</th><th>مانده</th>
                </tr>
              </thead>
              <tbody>
                {(d.owing || []).map((g) => (
                  <tr key={g.key}>
                    <td>
                      {g.label}
                      {g.unpriced > 0 && (
                        <span className="fx-pill mr-2" style={{
                          background: "rgba(251,191,36,.14)", color: "var(--warn)",
                        }}>{faNum(g.unpriced)} بدون نرخ</span>
                      )}
                    </td>
                    <td style={{ fontFamily: "var(--mono)" }}>{faNum(g.configs)}</td>
                    <td style={{ fontFamily: "var(--mono)" }}><Toman n={g.due} /></td>
                    <td style={{ fontFamily: "var(--mono)", color: "#34d399" }}>
                      <Toman n={g.paid} />
                    </td>
                    <td style={{ fontFamily: "var(--mono)", color: "var(--warn)" }}>
                      <Toman n={g.balance} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {(d.credit || []).length > 0 && (
        <div className="fx-card p-5">
          <div className="text-[14px] font-semibold text-white mb-1">
            پیش‌پرداخت‌ها
          </div>
          <p className="text-[12px] mb-3" style={{ color: "var(--muted)" }}>
            این واسطه‌ها بیشتر از صورت‌حسابشان پرداخت کرده‌اند — یعنی
            اعتبار دارند.
          </p>
          {(d.credit || []).map((g) => (
            <div key={g.key}
              className="flex items-center justify-between py-2 text-[13px]"
              style={{ borderBottom: "1px solid var(--border)" }}>
              <span>{g.label}</span>
              <span style={{ fontFamily: "var(--mono)", color: "#34d399" }}>
                <Toman n={Math.abs(g.balance)} />
                <span className="fx-fa-sub"> اعتبار</span>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
