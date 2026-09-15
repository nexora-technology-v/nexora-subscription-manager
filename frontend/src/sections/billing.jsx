/**
 * حسابداری و صورت‌حساب واسطه‌ها.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
import React, { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import {
  AlertTriangle, Check, CheckCircle2, ChevronLeft, Circle, Clock, Database, Download, FileText, Loader2, Plus as PlusIcon, RefreshCw, Save, Search, Send, ShieldCheck, Trash2, TrendingUp, Upload, Users, Wallet, X, XCircle,
} from "lucide-react";
import { JalaliDate, isoToJalaliLabel } from "../ui/jalali";
import { API_URL } from "../lib/constants";
import { errText, faNum } from "../lib/format";
import { Field, InfoBox, Modal, Msg, SectionHead, Toggle } from "../ui/index";

export function BillingPeriod({ password }) {
  const { data, loading: loadingGroups } = useBilling(password);
  const [sel, setSel] = useState("");
  const [inv, setInv] = useState(null);
  const [loading, setLoading] = useState(false);
  const [shift, setShift] = useState(0);
  const [custom, setCustom] = useState(false);
  const [range, setRange] = useState({ start: "", end: "" });

  const billed = data?.groups?.filter((g) => g.billed) || [];
  useEffect(() => { if (!sel && billed.length) setSel(billed[0].name); }, [data]);

  const load = async (offset = 0, manual = null) => {
    if (!sel) return;
    setLoading(true);
    try {
      let q = "";
      if (manual === "full") {
        q = "?full=1";
      } else if (manual && manual.start && manual.end) {
        q = `?start=${manual.start}&end=${manual.end}`;
      } else if (offset !== 0) {
        // دوره‌های قبل و بعد را با جابه‌جایی تاریخ می‌گیریم
        const g = billed.find((x) => x.name === sel);
        const days = g?.periodDays || 30;
        const base = inv?.period?.start
          ? new Date(inv.period.start) : new Date();
        const s = new Date(base);
        s.setDate(s.getDate() + offset * days);
        const e = new Date(s);
        e.setDate(e.getDate() + days);
        q = `?start=${s.toISOString().slice(0, 10)}&end=${e.toISOString().slice(0, 10)}`;
      }
      const d = await fetch(
        `${API_URL}/api/admin/billing/period/${encodeURIComponent(sel)}${q}`,
        { headers: { "X-Admin-Password": password } }).then((r) => r.json());
      setInv(d);
    } catch { setInv({ ready: false, error: "اتصال برقرار نشد" }); }
    finally { setLoading(false); }
  };

  useEffect(() => { setShift(0); load(0); }, [sel]);

  const move = (dir) => { setShift(shift + dir); load(dir); };

  // تا وقتی گروه‌ها نیامده‌اند، «خوانده نشد» نگوییم.
  //
  // data با null شروع می‌شود و !data?.ready همان لحظه‌ی اول درست است،
  // پس کارتِ «دیتابیس ۳x-ui خوانده نشد» یک لحظه ظاهر می‌شد و بعد
  // جایش را به داده می‌داد — یعنی هر بار ورود به این صفحه یک خطای
  // دروغین دیده می‌شد.
  if (loadingGroups) {
    return <div className="flex justify-center py-16">
      <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;
  }

  if (!data?.ready) {
    return (
      <div className="fx-anim">
        <SectionHead title="صورتحساب دوره" desc="" />
        <BillingUnavailable info={data} password={password} />
      </div>
    );
  }

  const t = inv?.totals;
  const p = inv?.period;

  return (
    <div className="fx-anim">
      <SectionHead title="صورتحساب دوره"
        desc="فقط کانفیگ‌ها و تمدیدهای همین دوره — نه کل بدهی از ابتدا." />

      {billed.length === 0 ? (
        <div className="fx-card p-10 text-center" style={{ borderStyle: "dashed" }}>
          <Users size={26} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
          <div className="text-[14px]" style={{ color: "var(--muted)" }}>
            ابتدا یک گروه را واسطه علامت بزنید
          </div>
        </div>
      ) : (
        <>
          <div className="fx-card p-5 mb-4">
            <div className="fx-g3 grid grid-cols-2 gap-3">
              <Field label="واسطه">
                <select className="fx-input" value={sel}
                  onChange={(e) => setSel(e.target.value)}>
                  {billed.map((g) => (
                    <option key={g.name} value={g.name}>{g.label}</option>
                  ))}
                </select>
              </Field>
              <Field label="دوره">
                {custom ? (
                  <div className="flex items-center gap-2">
                    <div className="flex-1 text-center py-2 rounded-xl text-[13px]"
                      style={{ background: "var(--surface-3)", color: "var(--dim)" }}>
                      {!p ? "بازه دلخواه"
                        : p.full ? `از ابتدا — ${p.startJalali} تا ${p.endJalali}`
                          : `${p.startJalali} تا ${p.endJalali}`}
                    </div>
                    <button onClick={() => { setCustom(false); setShift(0); load(0); }}
                      className="fx-ico-btn shrink-0" title="بازگشت به دوره‌ها">
                      <RefreshCw size={13} />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <button onClick={() => move(-1)} className="fx-ico-btn shrink-0">
                      <ChevronLeft size={14} />
                    </button>
                    <div className="flex-1 text-center py-2 rounded-xl text-[13px]"
                      style={{ background: "var(--surface-3)", color: "var(--dim)" }}>
                      {p ? `${p.startJalali} تا ${p.endJalali}` : "—"}
                    </div>
                    <button onClick={() => move(1)} className="fx-ico-btn shrink-0"
                      style={{ transform: "rotate(180deg)" }}>
                      <ChevronLeft size={14} />
                    </button>
                  </div>
                )}
              </Field>
            </div>

            {/* بازه‌ی دلخواه — وقتی می‌خواهید بازه‌ای غیر از دوره‌های
                خودکار را ببینید، مثلاً برای توافق خاص با یک واسطه */}
            <div className="mt-4 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
              <div className="flex justify-between items-center mb-3 flex-wrap gap-2">
                <span className="text-[13px]" style={{ color: "var(--dim)" }}>
                  بازه‌ی دلخواه
                </span>
                <div className="flex gap-1.5 flex-wrap">
                  {/* از ابتدا — دوره‌ی پیش‌فرض سی روز است، و برای
                      واسطه‌ای که دو سال با شما کار کرده یعنی
                      صورتحسابی که فقط کانفیگ‌های همین ماه را نشان
                      می‌دهد. این دکمه از تاریخ ساخت قدیمی‌ترین
                      کانفیگ همان گروه شروع می‌کند. */}
                  <button
                    onClick={() => { setCustom(true); load(0, "full"); }}
                    className="px-2.5 py-1 rounded-lg text-[12px] font-semibold"
                    style={{ background: "var(--accent)", color: "#fff",
                             border: "1px solid var(--accent)" }}>
                    از ابتدا تا امروز
                  </button>
                  {[["هفته گذشته", 7], ["دو هفته", 14],
                    ["ماه گذشته", 30], ["سه ماه", 90]].map(([l, n]) => (
                    <button key={n}
                      onClick={() => {
                        const e = new Date();
                        const s = new Date();
                        s.setDate(s.getDate() - n);
                        const r = { start: s.toISOString().slice(0, 10),
                                    end: e.toISOString().slice(0, 10) };
                        setRange(r); setCustom(true); load(0, r);
                      }}
                      className="px-2.5 py-1 rounded-lg text-[12px]"
                      style={{ background: "transparent",
                               border: "1px solid var(--border)",
                               color: "var(--muted)" }}>{l}</button>
                  ))}
                </div>
              </div>

              <div className="fx-g3 grid grid-cols-3 gap-2">
                {/* تقویم شمسی، انتخابی. تایپ‌کردن تاریخ میلادی از
                    کسی که همه‌ی کارش شمسی است، هم کند بود هم
                    اشتباه‌پذیر — و ارقام فارسی هم پذیرفته نمی‌شد. */}
                <JalaliDate value={range.start} placeholder="از تاریخ"
                  onChange={(v) => setRange({ ...range, start: v })} />
                <JalaliDate value={range.end} placeholder="تا تاریخ"
                  onChange={(v) => setRange({ ...range, end: v })} />
                <button
                  onClick={() => { setCustom(true); load(0, range); }}
                  disabled={!range.start || !range.end}
                  className="fx-btn py-2.5 text-[13px] flex items-center justify-center gap-1.5"
                  style={(!range.start || !range.end)
                    ? { opacity: .45, cursor: "not-allowed" } : {}}>
                  <FileText size={13} /> فاکتور
                </button>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="flex justify-center py-14">
              <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} />
            </div>
          ) : !inv?.ready ? (
            <div className="fx-card p-8 text-center" style={{ borderStyle: "dashed" }}>
              <div className="text-[13px]" style={{ color: "var(--muted)" }}>
                {inv?.error || "خطا در خواندن"}
              </div>
            </div>
          ) : (
            <>
              {/* خلاصه */}
              <div className="fx-card p-5 mb-4">
                <div className="flex justify-between items-baseline mb-4 flex-wrap gap-2">
                  <span className="text-[14px] font-semibold text-white">
                    بدهی این دوره
                  </span>
                  <span className="text-[24px] font-extrabold"
                    style={{ color: "var(--accent-2)",
                             fontFamily: "var(--mono)" }}>
                    {faNum(t.due)} <span className="text-[13px]">تومان</span>
                  </span>
                </div>

                {inv.perGb ? (
                  <div className="p-3 rounded-xl text-[13px]"
                    style={{ background: "var(--surface-3)", color: "var(--dim)" }}>
                    نرخ حجمی — بر اساس مصرف کل گروه
                  </div>
                ) : (
                  <div className="fx-g3 grid grid-cols-2 gap-3">
                    {[["کانفیگ جدید", t.newCount, t.newAmount, "var(--ok)"],
                      ["تمدید", t.renewalCount, t.renewalAmount, "var(--accent-2)"]
                    ].map(([l, n, amt, col], i) => (
                      <div key={i} className="p-3.5 rounded-xl"
                        style={{ background: "var(--surface-3)" }}>
                        <div className="flex justify-between items-baseline">
                          <span className="text-[13px]" style={{ color: "var(--muted)" }}>{l}</span>
                          <span className="text-[16px] font-bold" style={{ color: col,
                                fontFamily: "var(--mono)" }}>
                            {faNum(n)}
                          </span>
                        </div>
                        <div className="text-[13px] mt-1.5" style={{ color: "var(--dim)",
                             fontFamily: "var(--mono)" }}>
                          {faNum(amt)} تومان
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <div className="flex justify-between mt-4 pt-3 text-[13px]"
                  style={{ borderTop: "1px solid var(--border)" }}>
                  <span style={{ color: "var(--muted)" }}>پرداخت‌شده در این دوره</span>
                  <span style={{ color: "var(--ok)",
                                 fontFamily: "var(--mono)" }}>
                    {faNum(t.paid)}
                  </span>
                </div>
                <div className="flex justify-between mt-2 text-[14px] font-bold">
                  <span className="text-white">مانده</span>
                  <span style={{ color: t.balance > 0 ? "var(--warn)" : "var(--ok)",
                                 fontFamily: "var(--mono)" }}>
                    {faNum(t.balance)} تومان
                  </span>
                </div>

                {inv.settledUntil && (
                  <div className="text-[12px] mt-3" style={{ color: "var(--muted)" }}>
                    {faNum(inv.skippedSettled)} کانفیگ قبل از
                    {" "}{isoToJalaliLabel(inv.settledUntil)} تسویه‌شده
                    فرض شده و در محاسبه نیامده
                  </div>
                )}
              </div>

              {/* ریز */}
              {[["کانفیگ‌های جدید", inv.newConfigs, "var(--ok)"],
                ["تمدیدها", inv.renewals, "var(--accent-2)"]].map(([title, rows, col]) => (
                rows.length > 0 && (
                  <div key={title} className="fx-card p-5 mb-4">
                    <div className="text-[14px] font-semibold text-white mb-3">
                      {title} <span style={{ color: "var(--muted)" }}>({faNum(rows.length)})</span>
                    </div>
                    {rows.map((x, i) => (
                      <div key={i} className="flex justify-between items-center gap-3 py-2.5 flex-wrap"
                        style={{ borderBottom: i < rows.length - 1 ? "1px solid var(--border)" : "none" }}>
                        <div className="min-w-0">
                          <div className="text-[13px]" dir="ltr"
                            style={{ color: "var(--dim)", textAlign: "right",
                                     fontFamily: "var(--mono)" }}>
                            {x.email}
                          </div>
                          <div className="text-[12px] mt-0.5" style={{ color: "var(--muted)" }}>
                            {x.dateJalali || x.date} · {x.gbLabel}
                            {x.kind === "تخمینی" && (
                              <span style={{ color: "var(--warn)" }}> · تخمینی</span>
                            )}
                          </div>
                        </div>
                        <span className="text-[14px] font-bold shrink-0"
                          style={{ color: x.price === null ? "var(--warn)" : col,
                                   fontFamily: "var(--mono)" }}>
                          {x.price === null ? "بدون نرخ" : faNum(x.amount)}
                        </span>
                      </div>
                    ))}
                  </div>
                )
              ))}

              {t.estimated > 0 && (
                <InfoBox tone="warn">
                  {faNum(t.estimated)} تمدید تخمینی است — تاریخش از فاصله‌ی ایجاد تا
                  انقضا حدس زده شده، نه از ثبت واقعی. تمدیدهایی که از نکسورا انجام
                  شوند تاریخ قطعی دارند.
                </InfoBox>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

/* ── همه‌ی کاربران ── */

export const CLIENT_STATUS_COLOR = {
  "فعال": "var(--ok)",
  "رو به انقضا": "var(--warn)",
  "منقضی": "var(--danger)",
  "غیرفعال": "var(--muted)",
  "بدون انقضا": "#A78BFA",
  "شروع‌نشده": "#5AA9E6",
};

export function BillingClients({ password }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [group, setGroup] = useState("");
  const [status, setStatus] = useState("");
  const [renewed, setRenewed] = useState("");
  const [age, setAge] = useState("");
  const [priced, setPriced] = useState("");
  const [dates, setDates] = useState({ from: "", to: "" });
  const [sort, setSort] = useState("created");
  const [order, setOrder] = useState("desc");
  const [page, setPage] = useState(0);
  const [detail, setDetail] = useState(null);
  const PER = 60;

  const load = async () => {
    setLoading(true);
    try {
      const p = new URLSearchParams({
        q, group, status, renewed, age, priced, sort, order,
        created_from: dates.from, created_to: dates.to,
        limit: String(PER), offset: String(page * PER),
      });
      const d = await fetch(`${API_URL}/api/admin/billing/clients?${p}`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setData(d);
    } catch {
      setData({ ready: false, error: "اتصال به سرور برقرار نشد", clients: [] });
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); },
    [password, group, status, renewed, age, priced, dates, sort, order, page]);

  // جستجو با تاخیر — تا با هر حرف یک درخواست نرود
  useEffect(() => {
    const t = setTimeout(() => { setPage(0); load(); }, 400);
    return () => clearTimeout(t);
  }, [q]);

  const exportCsv = async () => {
    try {
      // همان فیلترهای صفحه — وگرنه باید در اکسل دوباره فیلتر کنید
      const p = new URLSearchParams({
        q, group, status, renewed, age, priced, sort, order,
        created_from: dates.from, created_to: dates.to,
      });
      const res = await fetch(`${API_URL}/api/admin/billing/clients/export?${p}`, {
        headers: { "X-Admin-Password": password } });
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `nexora-clients-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch { /* بی‌صدا */ }
  };

  const th = (key, label, w) => {
    const on = sort === key;
    return (
      <th key={key} onClick={() => {
        if (on) setOrder(order === "asc" ? "desc" : "asc");
        else { setSort(key); setOrder("desc"); }
        setPage(0);
      }}
        className="px-3 py-3 cursor-pointer select-none whitespace-nowrap text-[13px] transition-colors"
        style={{ width: w, color: on ? "var(--accent-2)" : "var(--muted)",
                 fontWeight: on ? 700 : 600 }}>
        <span className="inline-flex items-center gap-1">
          {label}
          <span style={{ opacity: on ? 1 : 0.25, fontSize: 9 }}>
            {on ? (order === "asc" ? "▲" : "▼") : "▼"}
          </span>
        </span>
      </th>
    );
  };

  if (loading && !data) {
    return <div className="flex justify-center py-16">
      <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;
  }

  if (!data?.ready) {
    return (
      <div className="fx-anim">
        <SectionHead title="همه کاربران" desc="" />
        <BillingUnavailable info={data} password={password} />
      </div>
    );
  }

  const s = data.stats;
  const pages = Math.ceil(data.total / PER);

  return (
    <div className="fx-anim">
      <SectionHead title="همه کاربران"
        desc="هر کانفیگ روی سرور — از هر گروه، و آن‌هایی که گروه ندارند."
        action={
          <div className="flex gap-2">
            <button onClick={exportCsv} className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
              <Download size={13} /> خروجی اکسل
            </button>
            <button onClick={load} className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
              <RefreshCw size={13} /> تازه‌سازی
            </button>
          </div>
        } />

      {/* آمار */}
      <div className="fx-g4 grid grid-cols-4 gap-3 mb-4">
        {[["کل کانفیگ", s.total, "var(--accent-2)", Users],
          ["تمدید شده", s.renewed, "var(--ok)", RefreshCw, `${s.renewalRate}٪ نرخ تمدید`],
          ["بدون تمدید", s.notRenewed, "var(--warn)", Clock, "فقط دوره اول"],
          ["مصرف کل", `${faNum(s.usedGB)}`, "#A78BFA", TrendingUp, "گیگابایت"]
        ].map(([l, v, col, I, sub], i) => (
          <div key={i} className="fx-card fx-card-i p-4">
            <div className="fx-ico mb-3" style={{ background: `color-mix(in srgb, ${col} 12%, transparent)` }}>
              <I size={15} style={{ color: col }} />
            </div>
            <div className="fx-stat-num text-[21px] font-extrabold text-white leading-none"
              style={{ fontFamily: "var(--mono)" }}>{faNum(v)}</div>
            <div className="text-[12px] mt-1.5" style={{ color: "var(--dim)" }}>{l}</div>
            {sub && <div className="text-[11.5px] mt-1" style={{ color: "var(--muted)" }}>{sub}</div>}
          </div>
        ))}
      </div>

      {/* وضعیت‌ها — کلیک برای فیلتر */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {[["فعال", s.active], ["رو به انقضا", s.expiringSoon],
          ["منقضی", s.expired], ["غیرفعال", s.disabled]].map(([label, n]) => {
          const on = status === label;
          const col = CLIENT_STATUS_COLOR[label];
          return (
            <button key={label}
              onClick={() => { setStatus(on ? "" : label); setPage(0); }}
              className="px-3 py-2 rounded-xl text-[13px] transition-all flex items-center gap-2"
              style={{
                background: on ? `color-mix(in srgb, ${col} 16%, transparent)` : "var(--surface-3)",
                border: `1px solid ${on ? col : "var(--border)"}`,
                color: on ? col : "var(--dim)",
              }}>
              <Circle size={7} fill={col} strokeWidth={0} />
              {label}
              <span style={{ fontFamily: "var(--mono)", opacity: .8 }}>
                {faNum(n)}
              </span>
            </button>
          );
        })}
        {s.noGroup > 0 && (
          <button onClick={() => { setGroup(group === "بدون گروه" ? "" : "بدون گروه"); setPage(0); }}
            className="px-3 py-2 rounded-xl text-[13px] flex items-center gap-2"
            style={{
              background: group === "بدون گروه" ? "rgba(255,255,255,.06)" : "var(--surface-3)",
              border: `1px solid ${group === "بدون گروه" ? "var(--border-2)" : "var(--border)"}`,
              color: "var(--muted)",
            }}>
            بدون گروه <span style={{ fontFamily: "var(--mono)" }}>{faNum(s.noGroup)}</span>
          </button>
        )}
      </div>

      {/* فیلترها */}
      <div className="fx-card p-4 mb-4">
        <div className="fx-g3 grid grid-cols-3 gap-3">
          <div className="fx-search">
            <Search size={14} style={{ color: "var(--muted)" }} />
            <input value={q} onChange={(e) => setQ(e.target.value)}
              placeholder="جستجو در ایمیل، گروه یا یادداشت..." />
          </div>
          <select className="fx-input" value={group}
            onChange={(e) => { setGroup(e.target.value); setPage(0); }}>
            <option value="">همه گروه‌ها</option>
            {data.groups.map((g) => <option key={g} value={g}>{g}</option>)}
          </select>
          <select className="fx-input" value={renewed}
            onChange={(e) => { setRenewed(e.target.value); setPage(0); }}>
            <option value="">تمدید: همه</option>
            <option value="yes">فقط تمدیدشده‌ها</option>
            <option value="no">فقط بدون تمدید</option>
          </select>
        </div>
        {/* فیلترهای حسابداری — سه چیزی که موقع فاکتور لازم می‌شوند */}
        <div className="mt-4 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
          <div className="flex gap-1.5 flex-wrap mb-3">
            {[["تازه (۳۰ روز)", "age", "new", s.newLast30],
              ["قدیمی‌تر", "age", "old", s.olderThan30],
              ["بدون نرخ", "priced", "no", s.unpriced]].map(([label, key, val, n]) => {
              const cur = key === "age" ? age : priced;
              const on = cur === val;
              const setter = key === "age" ? setAge : setPriced;
              const col = key === "priced" ? "var(--warn)" : "var(--accent-2)";
              return (
                <button key={label}
                  onClick={() => { setter(on ? "" : val); setPage(0); }}
                  className="px-3 py-1.5 rounded-lg text-[13px] flex items-center gap-1.5"
                  style={{
                    background: on ? `color-mix(in srgb, ${col} 14%, transparent)` : "transparent",
                    border: `1px solid ${on ? col : "var(--border)"}`,
                    color: on ? col : "var(--muted)",
                  }}>
                  {label}
                  {n !== undefined && (
                    <span style={{ fontFamily: "var(--mono)", opacity: .8 }}>
                      {faNum(n)}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[12px] shrink-0" style={{ color: "var(--muted)" }}>
              ساخته‌شده بین
            </span>
            {/* فیلتر هم باید شمسی باشد — کسی که در پنل فارسی کار
                می‌کند، بازه را شمسی در ذهن دارد نه میلادی */}
            <div style={{ width: 150 }}>
              <JalaliDate value={dates.from} placeholder="از تاریخ"
                onChange={(v) => { setDates({ ...dates, from: v }); setPage(0); }} />
            </div>
            <span className="text-[12px]" style={{ color: "var(--muted)" }}>تا</span>
            <div style={{ width: 150 }}>
              <JalaliDate value={dates.to} placeholder="تا تاریخ"
                onChange={(v) => { setDates({ ...dates, to: v }); setPage(0); }} />
            </div>

            {[["۷ روز", 7], ["۳۰ روز", 30]].map(([l, n]) => (
              <button key={n}
                onClick={() => {
                  const t = new Date();
                  const f = new Date();
                  f.setDate(f.getDate() - n);
                  setDates({ from: f.toISOString().slice(0, 10),
                             to: t.toISOString().slice(0, 10) });
                  setPage(0);
                }}
                className="px-2.5 py-1.5 rounded-lg text-[12px]"
                style={{ background: "transparent", border: "1px solid var(--border)",
                         color: "var(--muted)" }}>{l}</button>
            ))}
          </div>
        </div>

        {(q || group || status || renewed || age || priced || dates.from || dates.to) && (
          <button onClick={() => {
              setQ(""); setGroup(""); setStatus(""); setRenewed("");
              setAge(""); setPriced(""); setDates({ from: "", to: "" }); setPage(0);
            }}
            className="text-[13px] mt-3 flex items-center gap-1.5"
            style={{ color: "var(--accent-2)" }}>
            <X size={12} /> پاک کردن فیلترها ({faNum(data.total)} نتیجه)
          </button>
        )}
      </div>

      {/* جدول */}
      <div className="fx-card overflow-hidden" style={{ padding: 0 }}>
        <div style={{ overflowX: "auto" }}>
          <table className="w-full" style={{ borderCollapse: "collapse", minWidth: 1080 }}>
            <thead>
              <tr style={{ background: "var(--surface-3)", borderBottom: "1px solid var(--border-2)" }}>
                {th("email", "کاربر", "22%")}
                {th("group", "گروه", "13%")}
                <th className="px-3 py-3 text-[13px]" style={{ color: "var(--muted)", width: "11%" }}>وضعیت</th>
                {th("created", "ایجاد", "10%")}
                {th("expiry", "انقضا", "10%")}
                {th("remaining", "مانده", "8%")}
                {th("months", "ماه", "6%")}
                {th("renewals", "تمدید", "7%")}
                {th("used", "مصرف", "13%")}
                {th("amount", "مبلغ", "10%")}
              </tr>
            </thead>
            <tbody>
              {data.clients.map((c, i) => {
                const col = CLIENT_STATUS_COLOR[c.status] || "var(--muted)";
                const pctColor = c.usagePct === null ? "var(--muted)"
                  : c.usagePct >= 90 ? "var(--danger)"
                  : c.usagePct >= 70 ? "var(--warn)" : "var(--accent)";
                return (
                  <tr key={c.email} onClick={() => setDetail(c)}
                    className="cursor-pointer nx-row"
                    style={{
                      borderBottom: i < data.clients.length - 1 ? "1px solid var(--border)" : "none",
                      background: i % 2 ? "rgba(255,255,255,.015)" : "transparent",
                    }}>

                    {/* کاربر */}
                    <td className="px-3 py-3">
                      <div className="text-[14px] font-semibold" dir="ltr"
                        style={{ color: c.enable ? "var(--text)" : "var(--muted)",
                                 textAlign: "right",
                                 fontFamily: "var(--mono)" }}>
                        {c.email}
                      </div>
                      <div className="flex items-center gap-2 mt-1 flex-wrap">
                        <span className="text-[12px]" style={{ color: "var(--muted)" }}>
                          {c.gbLabel}
                        </span>
                        {c.limitIp > 0 && (
                          <span className="text-[12px] px-1.5 py-0.5 rounded"
                            style={{ background: "rgba(255,255,255,.05)", color: "var(--muted)" }}>
                            {faNum(c.limitIp)} دستگاه
                          </span>
                        )}
                        {c.resetCount > 0 && (
                          <span className="text-[12px] px-1.5 py-0.5 rounded"
                            style={{ background: "rgba(167,139,250,.14)", color: "#A78BFA" }}>
                            {faNum(c.resetCount)} ریست
                          </span>
                        )}
                        {c.tgId > 0 && (
                          <span className="text-[12px] px-1.5 py-0.5 rounded flex items-center gap-1"
                            style={{ background: "rgba(34,158,217,.14)", color: "#229ED9" }}>
                            <Send size={9} /> تلگرام
                          </span>
                        )}
                      </div>
                      {c.comment && (
                        <div className="text-[12px] mt-1.5 truncate" style={{ color: "var(--muted)", maxWidth: 240 }}>
                          {c.comment}
                        </div>
                      )}
                    </td>

                    {/* گروه */}
                    <td className="px-3 py-3">
                      <div className="text-[14px]" style={{ color: "var(--dim)" }}>
                        {c.groupLabel}
                      </div>
                      {c.billable && (
                        <span className="text-[11.5px] px-1.5 py-0.5 rounded mt-1 inline-block"
                          style={{ background: "var(--accent-soft)", color: "var(--accent-2)" }}>
                          واسطه
                        </span>
                      )}
                    </td>

                    {/* وضعیت */}
                    <td className="px-3 py-3">
                      <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-[13px]"
                        style={{ background: `color-mix(in srgb, ${col} 12%, transparent)`, color: col }}>
                        <Circle size={6} fill={col} strokeWidth={0} /> {c.status}
                      </span>
                    </td>

                    {/* ایجاد */}
                    <td className="px-3 py-3 text-center text-[13px]" dir="ltr"
                      style={{ color: "var(--dim)", fontFamily: "var(--mono)" }}>
                      {c.createdJalali || "—"}
                      {c.days && (
                        <div className="text-[12px] mt-0.5" style={{ color: "var(--muted)" }}>
                          {faNum(Math.round(c.days))} روز
                        </div>
                      )}
                    </td>

                    {/* انقضا */}
                    <td className="px-3 py-3 text-center text-[13px]" dir="ltr"
                      style={{ color: "var(--dim)", fontFamily: "var(--mono)" }}>
                      {c.expiryJalali || "—"}
                    </td>

                    {/* مانده */}
                    <td className="px-3 py-3 text-center">
                      {c.remainingDays === null ? (
                        <span style={{ color: "var(--muted)" }}>—</span>
                      ) : (
                        <div>
                          <div className="text-[16px] font-bold"
                            style={{
                              color: c.remainingDays < 0 ? "var(--danger)"
                                   : c.remainingDays <= 3 ? "var(--warn)" : "var(--text)",
                              fontFamily: "var(--mono)",
                            }}>
                            {faNum(Math.abs(Math.round(c.remainingDays)))}
                          </div>
                          <div className="text-[11.5px]" style={{ color: "var(--muted)" }}>
                            {c.remainingDays < 0 ? "روز گذشته" : "روز"}
                          </div>
                        </div>
                      )}
                    </td>

                    {/* ماه */}
                    <td className="px-3 py-3 text-center">
                      <div className="text-[16px] font-bold" style={{ color: "var(--text)",
                           fontFamily: "var(--mono)" }}>
                        {faNum(c.months)}
                      </div>
                    </td>

                    {/* تمدید */}
                    <td className="px-3 py-3 text-center">
                      {c.renewals ? (
                        <div>
                          <span className="px-2.5 py-1 rounded-lg text-[14px] font-bold inline-block"
                            style={{ background: "rgba(43,127,214,.18)", color: "var(--accent-2)",
                                     fontFamily: "var(--mono)" }}>
                            {faNum(c.renewals)}
                          </span>
                          {c.renewalKind === "تخمینی" && (
                            <div className="text-[11px] mt-1" style={{ color: "var(--warn)" }}>
                              تخمینی
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-[13px]" style={{ color: "var(--muted)" }}>بدون</span>
                      )}
                    </td>

                    {/* مصرف */}
                    <td className="px-3 py-3">
                      <div className="flex items-baseline gap-1.5 justify-center mb-1.5">
                        <span className="text-[14px] font-semibold"
                          style={{ color: "var(--text)", fontFamily: "var(--mono)" }}>
                          {faNum(c.usedGB)}
                        </span>
                        <span className="text-[12px]" style={{ color: "var(--muted)" }}>
                          / {c.gb === 0 ? "∞" : faNum(c.gb)} GB
                        </span>
                      </div>
                      <div style={{ height: 5, borderRadius: 99,
                                    background: "rgba(255,255,255,.06)", overflow: "hidden" }}>
                        <div style={{
                          width: c.usagePct === null ? "100%" : `${Math.min(100, c.usagePct)}%`,
                          height: "100%",
                          background: c.usagePct === null
                            ? "linear-gradient(90deg,#A78BFA33,#A78BFA66)" : pctColor,
                          transition: "width .4s ease",
                        }} />
                      </div>
                      <div className="text-[12px] mt-1 text-center" style={{ color: pctColor }}>
                        {c.usagePct === null ? "نامحدود" : `${faNum(c.usagePct)}٪`}
                      </div>
                    </td>

                    {/* مبلغ */}
                    <td className="px-3 py-3 text-center">
                      {c.amount ? (
                        <div>
                          <div className="text-[14px] font-bold" style={{ color: "var(--text)",
                               fontFamily: "var(--mono)" }}>
                            {faNum(c.amount)}
                          </div>
                          {c.months > 1 && c.price && (
                            <div className="text-[11.5px] mt-0.5" style={{ color: "var(--muted)" }}>
                              {faNum(c.months)}×{faNum(Math.round(c.price / 1000))}k
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-[13px]" style={{ color: "var(--muted)" }}>—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {data.clients.length === 0 && (
          <div className="py-16 text-center">
            <Users size={26} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
            <div className="text-[14px]" style={{ color: "var(--muted)" }}>
              کاربری با این فیلترها پیدا نشد
            </div>
          </div>
        )}
      </div>

      {/* صفحه‌بندی */}
      {pages > 1 && (
        <div className="flex items-center justify-between mt-4 flex-wrap gap-3">
          <span className="text-[13px]" style={{ color: "var(--muted)" }}>
            {faNum(page * PER + 1)} تا {faNum(Math.min((page + 1) * PER, data.total))} از {faNum(data.total)}
          </span>
          <div className="flex gap-2 items-center">
            <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
              className="fx-btn-g px-3 py-2 text-[13px]"
              style={page === 0 ? { opacity: .35, cursor: "not-allowed" } : {}}>قبلی</button>
            <span className="px-3 text-[13px]" style={{ color: "var(--dim)",
              fontFamily: "var(--mono)" }}>
              {faNum(page + 1)} / {faNum(pages)}
            </span>
            <button onClick={() => setPage(Math.min(pages - 1, page + 1))} disabled={page >= pages - 1}
              className="fx-btn-g px-3 py-2 text-[13px]"
              style={page >= pages - 1 ? { opacity: .35, cursor: "not-allowed" } : {}}>بعدی</button>
          </div>
        </div>
      )}

      {detail && <ClientDetailModal client={detail} onClose={() => setDetail(null)} />}
    </div>
  );
}

/** جزئیات کامل یک کاربر */
export function ClientDetailModal({ client: c, onClose }) {
  const col = CLIENT_STATUS_COLOR[c.status] || "var(--muted)";

  const Row = ({ label, value, mono, color }) => (
    <div className="flex justify-between items-start gap-3 py-2"
      style={{ borderBottom: "1px solid var(--border)" }}>
      <span className="text-[13px] shrink-0" style={{ color: "var(--muted)" }}>{label}</span>
      <span className="text-[13px] text-left" dir={mono ? "ltr" : "rtl"}
        style={{ color: color || "var(--dim)",
                 fontFamily: mono ? "var(--mono)" : "inherit" }}>
        {value}
      </span>
    </div>
  );

  return (
    <Modal title={c.email} onClose={onClose} width="480px">
      <div className="flex items-center gap-2 mb-4">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[13px]"
          style={{ background: `color-mix(in srgb, ${col} 14%, transparent)`, color: col }}>
          <Circle size={6} fill={col} strokeWidth={0} /> {c.status}
        </span>
        <span className="text-[13px] px-2.5 py-1 rounded-lg"
          style={{ background: "var(--surface-3)", color: "var(--dim)" }}>
          {c.groupLabel}
        </span>
      </div>

      <Row label="حجم پلن" value={c.gbLabel} />
      <Row label="مصرف" value={`${faNum(c.usedGB)} GB${c.usagePct !== null ? ` (${faNum(c.usagePct)}٪)` : ""}`} mono />
      <Row label="تاریخ ایجاد" value={c.createdJalali || "—"} mono />
      <Row label="تاریخ انقضا" value={c.expiryJalali || "—"} mono />
      <Row label="روز مانده"
        value={c.remainingDays === null ? "—" : faNum(Math.round(c.remainingDays))} mono
        color={c.remainingDays !== null && c.remainingDays < 0 ? "var(--danger)" : undefined} />
      <Row label="مدت اشتراک" value={c.days ? `${faNum(c.days)} روز` : "—"} mono />
      <Row label="تعداد ماه" value={faNum(c.months)} mono color="var(--text)" />
      <Row label="تعداد تمدید" value={c.renewals ? faNum(c.renewals) : "بدون تمدید"} mono
        color={c.renewals ? "var(--accent-2)" : undefined} />
      <Row label="نوع تشخیص"
        value={c.renewalKind + (c.drift ? ` (انحراف ${faNum(c.drift)} روز)` : "")}
        color={c.renewalKind === "تخمینی" ? "var(--warn)" : "var(--ok)"} />
      {c.loggedRenewals > 0 && (
        <Row label="تمدید ثبت‌شده در نکسورا" value={faNum(c.loggedRenewals)} mono color="var(--ok)" />
      )}
      <Row label="دستگاه همزمان" value={c.limitIp ? faNum(c.limitIp) : "نامحدود"} mono />
      {c.resetCount > 0 && <Row label="ریست ترافیک" value={faNum(c.resetCount)} mono />}
      {c.tgId > 0 && <Row label="آیدی تلگرام" value={c.tgId} mono />}
      {c.subId && <Row label="شناسه اشتراک" value={c.subId} mono />}
      {c.comment && <Row label="یادداشت" value={c.comment} />}

      {c.billable && (
        <div className="mt-4 p-3.5 rounded-xl"
          style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
          <div className="flex justify-between text-[13px]">
            <span style={{ color: "var(--muted)" }}>نرخ ماهانه</span>
            <span style={{ color: "var(--dim)", fontFamily: "var(--mono)" }}>
              {c.price ? faNum(c.price) : "تعریف نشده"}
            </span>
          </div>
          <div className="flex justify-between text-[14px] font-bold mt-2 pt-2"
            style={{ borderTop: "1px solid var(--border)" }}>
            <span className="text-white">مبلغ کل</span>
            <span style={{ color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
              {faNum(c.amount)} تومان
            </span>
          </div>
        </div>
      )}
    </Modal>
  );
}

/* ── تنظیمات و بک‌آپ حسابداری ── */

export function BillingSettings({ password }) {
  const [info, setInfo] = useState(null);
  const [cfg, setCfg] = useState(null);
  const [path, setPath] = useState("");
  const [busy, setBusy] = useState(null);
  const [msg, setMsg] = useState(null);
  const fileRef = React.useRef(null);

  const load = async () => {
    try {
      const [i, c2] = await Promise.all([
        fetch(`${API_URL}/api/admin/billing/xui-path`, { headers: { "X-Admin-Password": password } }).then(r => r.json()),
        fetch(`${API_URL}/api/admin/config`, { headers: { "X-Admin-Password": password } }).then(r => r.json()),
      ]);
      setInfo(i);
      setCfg(c2);
      setPath((c2.advanced?.xuiDbPath) || "");
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
  };
  useEffect(() => { load(); }, [password]);
  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 4500); return () => clearTimeout(t); } }, [msg]);

  const savePath = async (p) => {
    setBusy("path");
    try {
      const next = { ...cfg, advanced: { ...(cfg.advanced || {}), xuiDbPath: p } };
      const res = await fetch(`${API_URL}/api/admin/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify(next),
      });
      if (res.ok) { setMsg({ t: "ok", m: "مسیر ذخیره شد" }); load(); }
      else setMsg({ t: "err", m: "ذخیره ناموفق" });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(null); }
  };

  const backup = async () => {
    setBusy("backup");
    try {
      const d = await fetch(`${API_URL}/api/admin/billing/backup`, {
        headers: { "X-Admin-Password": password },
      }).then(r => r.json());
      const blob = new Blob([JSON.stringify(d, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `nexora-billing-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
      setMsg({ t: "ok", m: `دانلود شد — ${d.counts?.payments || 0} پرداخت، ${d.counts?.group_config || 0} گروه` });
    } catch { setMsg({ t: "err", m: "بک‌آپ ناموفق" }); }
    finally { setBusy(null); }
  };

  const restore = async (file) => {
    setBusy("restore");
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      const res = await fetch(`${API_URL}/api/admin/billing/restore`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ data: parsed.data || parsed }),
      });
      const d = await res.json();
      if (res.ok && d.warning) {
        setMsg({ t: "err", m: `بازیابی ناقص بود — ${d.warning}` });
      } else if (res.ok) {
        const n = Object.values(d.restored || {}).reduce((x, y) => x + y, 0);
        setMsg({ t: "ok", m: `بازیابی شد — ${n} ردیف` });
      }
      else setMsg({ t: "err", m: errText(d.detail, "بازیابی ناموفق") });
    } catch { setMsg({ t: "err", m: "فایل معتبر نبود" }); }
    finally { setBusy(null); if (fileRef.current) fileRef.current.value = ""; }
  };

  if (!info) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  return (
    <div className="fx-anim">
      <SectionHead title="تنظیمات و بک‌آپ"
        desc="مسیر دیتابیس ۳x-ui و پشتیبان‌گیری از نرخ‌ها و پرداخت‌ها." />

      {msg && <Msg msg={msg} />}

      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2">
          <Database size={15} style={{ color: "var(--accent-2)" }} /> مسیر دیتابیس ۳x-ui
        </div>
        <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
          حسابداری گروه‌ها و مصرف را از این فایل می‌خواند — فقط‌خواندنی، بدون هیچ تغییری در آن.
        </p>

        <div className="rounded-xl p-3 mb-4 flex items-start gap-2.5"
          style={{
            background: info.readable ? "rgba(52,211,153,.08)" : "rgba(251,191,36,.08)",
            border: `1px solid ${info.readable ? "rgba(52,211,153,.25)" : "rgba(251,191,36,.25)"}`,
          }}>
          {info.readable
            ? <CheckCircle2 size={15} style={{ color: "var(--ok)", flexShrink: 0, marginTop: 1 }} />
            : <AlertTriangle size={15} style={{ color: "var(--warn)", flexShrink: 0, marginTop: 1 }} />}
          <div className="min-w-0">
            <div className="text-[13px] font-semibold" style={{ color: info.readable ? "var(--ok)" : "var(--warn)" }}>
              {info.readable ? "خوانده می‌شود" : info.exists ? "پیدا شد ولی دسترسی خواندن نیست" : "پیدا نشد"}
            </div>
            <div className="text-[12px] mt-1 break-all" dir="ltr"
              style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
              {info.current}
            </div>
            {info.exists && !info.readable && (
              <div className="text-[12px] mt-2" style={{ color: "var(--warn)" }}>
                روی سرور اجرا کنید: <code dir="ltr" className="px-1.5 py-0.5 rounded"
                  style={{ background: "var(--surface-3)" }}>chmod +r {info.current}</code>
              </div>
            )}
          </div>
        </div>

        {info.found?.length > 0 && (
          <div className="mb-4">
            <div className="text-[13px] mb-2" style={{ color: "var(--muted)" }}>
              مسیرهای پیداشده روی این سرور:
            </div>
            {info.found.map((f) => (
              <button key={f.path} onClick={() => { setPath(f.path); savePath(f.path); }}
                className="w-full flex items-center justify-between gap-2 p-2.5 rounded-xl mb-1.5 text-right"
                style={{
                  background: f.path === info.current ? "var(--accent-soft)" : "var(--surface-3)",
                  border: `1px solid ${f.path === info.current ? "rgba(43,127,214,.4)" : "var(--border)"}`,
                }}>
                <span className="text-[13px] truncate" dir="ltr"
                  style={{ color: "var(--dim)", fontFamily: "var(--mono)" }}>{f.path}</span>
                <span className="text-[11.5px] shrink-0" style={{ color: "var(--muted)" }}>
                  {(f.size / 1024 / 1024).toFixed(1)} MB
                </span>
              </button>
            ))}
          </div>
        )}

        <Field label="مسیر دستی" hint="اگر ۳x-ui جای دیگری نصب است">
          <div className="flex gap-2">
            <input className="fx-input" dir="ltr" value={path}
              onChange={(e) => setPath(e.target.value)}
              placeholder="/etc/x-ui/x-ui.db"
              style={{ fontFamily: "var(--mono)" }} />
            <button onClick={() => savePath(path)} disabled={busy === "path"}
              className="fx-btn px-4 py-2.5 text-[13px] shrink-0 flex items-center gap-1.5">
              {busy === "path" ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
              ذخیره
            </button>
          </div>
        </Field>
      </div>

      <div className="fx-card p-5">
        <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2">
          <Database size={15} style={{ color: "var(--accent-2)" }} /> بک‌آپ حسابداری
        </div>
        <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
          نرخ‌ها، پرداخت‌ها و لاگ تمدید. داده‌ی ۳x-ui در بک‌آپ نیست — آن از خودش خوانده می‌شود.
        </p>

        <div className="fx-g3 grid grid-cols-2 gap-3">
          <button onClick={backup} disabled={busy === "backup"}
            className="fx-btn py-3 text-[14px] flex items-center justify-center gap-2">
            {busy === "backup" ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            دریافت بک‌آپ
          </button>
          <button onClick={() => fileRef.current?.click()} disabled={busy === "restore"}
            className="fx-btn-g py-3 text-[14px] flex items-center justify-center gap-2">
            {busy === "restore" ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
            بازیابی از فایل
          </button>
        </div>
        <input ref={fileRef} type="file" accept=".json" className="hidden"
          onChange={(e) => e.target.files?.[0] && restore(e.target.files[0])} />

        <InfoBox>
          قبل از بازیابی، یک نسخه‌ی امن از وضعیت فعلی گرفته می‌شود — اگر فایل اشتباه
          بود، داده‌ی فعلی از دست نرفته است.
        </InfoBox>
      </div>
    </div>
  );
}

/* ═══════════════════ حسابداری واسطه‌ها ═══════════════════ */

export const RATE_STEP = 10000;

export const RATE_QUICK = [90000, 120000, 150000, 190000, 250000];

/**
 * ردیف نرخ — حجم آزاد و قیمت با سه راه ورود.
 *
 * فیلدها فرورفته‌اند (پس‌زمینه‌ی تیره‌تر از کارت) تا با زبان بصری
 * بقیه‌ی پنل بخوانند و لکه‌ی روشن ایجاد نکنند.
 */
export function RateRow({ rate, onChange, onDelete }) {
  const unlimited = !rate.gb;
  const bump = (d) => onChange({ price: Math.max(0, (rate.price || 0) + d) });

  return (
    <div className="rounded-2xl p-3 mb-2.5"
      style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>

      <div className="flex items-end gap-2.5 mb-3">
        <div className="flex-1">
          <label className="text-[12px] block mb-1.5" style={{ color: "var(--muted)" }}>
            حجم ماهانه
          </label>
          <div className="flex gap-2">
            <button onClick={() => onChange({ gb: 0 })}
              className="px-3.5 py-2.5 rounded-[10px] text-[13px] font-semibold shrink-0"
              style={{
                background: unlimited ? "rgba(167,139,250,.14)" : "transparent",
                border: `1px solid ${unlimited ? "rgba(167,139,250,.4)" : "var(--border-2)"}`,
                color: unlimited ? "#A78BFA" : "var(--muted)",
              }}>
              نامحدود
            </button>

            <div className="flex-1 flex items-center gap-2 px-3 rounded-[10px]"
              style={{
                background: unlimited ? "transparent" : "rgba(0,0,0,.28)",
                border: "1px solid var(--border)",
                boxShadow: unlimited ? "none" : "0 2px 8px rgba(0,0,0,.35) inset",
                opacity: unlimited ? 0.42 : 1,
              }}>
              <input type="number" min="1" dir="ltr"
                value={unlimited ? "" : rate.gb}
                onFocus={() => unlimited && onChange({ gb: 30 })}
                onChange={(e) => onChange({ gb: Math.max(0, Number(e.target.value)) })}
                placeholder="مثلاً ۵۰"
                className="flex-1 bg-transparent border-0 outline-none py-2.5 text-[14px]"
                style={{ color: "var(--text)", fontFamily: "var(--mono)" }} />
              <span className="text-[12px] shrink-0" style={{ color: "var(--muted)" }}>گیگابایت</span>
            </div>
          </div>
        </div>

        <button onClick={onDelete} className="fx-ico-btn shrink-0" style={{ width: 36, height: 36 }}>
          <Trash2 size={13} />
        </button>
      </div>

      <div>
        <div className="flex justify-between items-center mb-2">
          <label className="text-[12px]" style={{ color: "var(--muted)" }}>قیمت ماهانه</label>
          <span className="text-[12px]" style={{ color: "var(--muted)" }}>
            {rate.price ? `${faNum(rate.price)} تومان` : "—"}
          </span>
        </div>

        <div className="flex items-center gap-0.5 rounded-xl p-1"
          style={{
            background: "rgba(0,0,0,.28)", border: "1px solid var(--border)",
            boxShadow: "0 2px 8px rgba(0,0,0,.35) inset",
          }}>
          <button onClick={() => bump(-RATE_STEP)} className="nx-step">−</button>
          <input type="number" dir="ltr" value={rate.price || ""}
            onChange={(e) => onChange({ price: Math.max(0, Number(e.target.value)) })}
            placeholder="0"
            className="flex-1 bg-transparent border-0 outline-none text-center py-2 text-[16px] font-bold"
            style={{ color: "var(--text)", fontFamily: "var(--mono)" }} />
          <button onClick={() => bump(RATE_STEP)} className="nx-step">+</button>
        </div>

        {/* نرخ هر کاربرِ اضافه — مخصوص همین پله.
            کانفیگ چهارکاربره همان نرخ تک‌کاربره را می‌گرفت، در حالی
            که سه کاربر بیشتر روی سرور می‌نشیند. */}
        <div className="mt-3 pt-3" style={{ borderTop: "1px solid var(--border)" }}>
          <div className="flex justify-between items-center mb-2">
            <label className="text-[12px]" style={{ color: "var(--muted)" }}>
              نرخ هر کاربر اضافه
            </label>
            <span className="text-[12px]" style={{ color: "var(--muted)" }}>
              {rate.perDevice ? `${faNum(rate.perDevice)} تومان` : "رایگان"}
            </span>
          </div>
          <input type="number" min="0" dir="ltr" value={rate.perDevice || ""}
            onChange={(e) => onChange({ perDevice: Math.max(0, Number(e.target.value)) })}
            placeholder="0"
            className="fx-input w-full text-center py-2 text-[15px] font-bold"
            style={{ fontFamily: "var(--mono)" }} />
          <p className="text-[12px] mt-2 leading-relaxed" style={{ color: "var(--muted)" }}>
            نرخ پایه شامل کاربر اول است. کانفیگ{" "}
            <b>{faNum(4)} کاربره</b> می‌شود{" "}
            <b style={{ color: "var(--accent-2)" }}>
              {faNum((rate.price || 0) + (rate.perDevice || 0) * 3)}
            </b>{" "}
            تومان در ماه
            {rate.perDevice ? (
              <> — {faNum(rate.price || 0)} + {faNum(3)}×{faNum(rate.perDevice)}</>
            ) : null}
            .
          </p>
        </div>

        <div className="flex gap-1.5 mt-2.5 flex-wrap">
          {RATE_QUICK.map((q) => {
            const on = rate.price === q;
            return (
              <button key={q} onClick={() => onChange({ price: q })}
                className="px-2.5 py-1 rounded-lg text-[12px]"
                style={{
                  background: on ? "rgba(43,127,214,.14)" : "transparent",
                  border: `1px solid ${on ? "rgba(43,127,214,.4)" : "var(--border)"}`,
                  color: on ? "var(--accent-2)" : "var(--muted)",
                  fontFamily: "var(--mono)",
                }}>{faNum(q / 1000)}k</button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export function useBilling(password) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/billing/groups`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setData(d);
    } catch {
      setData({ ready: false, error: "اتصال به سرور برقرار نشد", groups: [] });
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [password]);
  return { data, loading, reload: load };
}

export function BillingUnavailable({ info, password }) {
  const [diag, setDiag] = useState(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    try {
      const d = await fetch(`${API_URL}/api/admin/billing/diagnose`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setDiag(d);
    } catch {
      setDiag({ ok: false, steps: [{ title: "اتصال به سرور برقرار نشد", ok: false }] });
    } finally { setBusy(false); }
  };

  if (diag) {
    return (
      <div className="fx-card p-5">
        <div className="text-[14px] font-semibold text-white mb-4 flex items-center gap-2">
          <ShieldCheck size={15} style={{ color: "var(--accent-2)" }} /> تشخیص اتصال
        </div>
        {diag.steps.map((s, i) => (
          <div key={i} className="flex gap-3 py-2.5"
            style={{ borderBottom: i < diag.steps.length - 1 ? "1px solid var(--border)" : "none" }}>
            <div className="shrink-0 mt-0.5">
              {s.ok ? <CheckCircle2 size={15} style={{ color: "var(--ok)" }} />
                    : <XCircle size={15} style={{ color: "var(--danger)" }} />}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[13px] font-semibold"
                style={{ color: s.ok ? "var(--text)" : "var(--danger)" }}>{s.title}</div>
              {errText(s.detail) && (
                <div className="text-[12px] mt-1 break-all" dir="auto"
                  style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                  {errText(s.detail)}
                </div>
              )}
              {s.hint && (
                <div className="text-[13px] mt-2 px-2.5 py-1.5 rounded-lg break-all" dir="auto"
                  style={{ color: "var(--warn)", background: "rgba(251,191,36,.08)" }}>
                  {s.hint}
                </div>
              )}
            </div>
          </div>
        ))}
        <button onClick={() => setDiag(null)}
          className="fx-btn-g w-full py-2.5 text-[13px] mt-4">بازگشت</button>
      </div>
    );
  }

  return (
    <div className="fx-card p-8 text-center" style={{ borderStyle: "dashed" }}>
      <AlertTriangle size={24} style={{ color: "var(--warn)" }} className="mx-auto mb-3" />
      <div className="text-[14px] font-semibold text-white mb-2">
        دیتابیس ۳x-ui خوانده نشد
      </div>
      <p className="text-[13px] mb-4 max-w-sm mx-auto leading-relaxed" style={{ color: "var(--muted)" }}>
        {info?.error || "مسیر دیتابیس در دسترس نیست."}
      </p>
      {(info?.xuiPath || info?.dbPath) && (
        <code dir="ltr" className="text-[12px] px-3 py-1.5 rounded-lg inline-block"
          style={{ background: "var(--surface-3)", color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
          {info.xuiPath || info.dbPath}
        </code>
      )}
      <div className="mt-5 pt-4 max-w-sm mx-auto" style={{ borderTop: "1px solid var(--border)" }}>
        <p className="text-[13px] leading-relaxed mb-3" style={{ color: "var(--muted)" }}>
          روی سرور این را اجرا کنید تا مسیر خودکار پیدا و تنظیم شود:
        </p>
        <code dir="ltr" className="text-[13px] px-3 py-2 rounded-lg inline-block"
          style={{ background: "var(--surface-3)", color: "var(--ok)", fontFamily: "var(--mono)" }}>
          nexora fix-xui
        </code>
        <p className="text-[12px] leading-relaxed mt-3" style={{ color: "var(--muted)" }}>
          یا مسیر را دستی در بخش «تنظیمات و بک‌آپ» وارد کنید.
        </p>
        <button onClick={run} disabled={busy}
          className="fx-btn w-full py-2.5 text-[13px] mt-4 flex items-center justify-center gap-2">
          {busy ? <Loader2 size={14} className="animate-spin" /> : <ShieldCheck size={14} />}
          تشخیص دقیق مشکل
        </button>
      </div>
    </div>
  );
}

/**
 * وقتی گروهی تاریخ شروع ندارد، همه‌ی کانفیگ‌هایش «یک ماه» حساب
 * می‌شوند — و صورت‌حساب واسطه‌ای که دو سال کار کرده، غلط درمی‌آید.
 *
 * این بنر مشکل را در همان صفحه‌ای که دیده می‌شود توضیح می‌دهد و
 * یک‌جا حلش می‌کند، به‌جای اینکه مدیر مجبور باشد یازده بار وارد
 * تنظیمات هر گروه شود — کاری که عملاً هیچ‌کس نمی‌کند.
 */
function NeedStartBanner({ groups, password, onDone }) {
  const [date, setDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [open, setOpen] = useState(false);

  const apply = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/billing/bulk-start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Password": password,
        },
        body: JSON.stringify({ start: date, groups }),
      });
      const j = await res.json().catch(() => ({}));
      setMsg(res.ok ? { t: "ok", m: j.note || "انجام شد" }
        : { t: "err", m: errText(j.detail, "ناموفق") });
      if (res.ok) { setOpen(false); onDone && onDone(); }
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(false); }
  };

  return (
    <div className="fx-card p-5" style={{
      border: "1px solid var(--warn)", background: "rgba(251,191,36,.05)",
    }}>
      <div className="flex items-center gap-2 mb-2" style={{ color: "var(--warn)" }}>
        <AlertTriangle size={16} />
        <span className="text-[14px] font-semibold">
          {faNum(groups.length)} گروه تاریخ شروع ندارند
        </span>
      </div>
      <p className="text-[13px] leading-relaxed" style={{ color: "var(--dim)" }}>
        نسخه‌ی x-ui شما تاریخ ساخت کلاینت را نگه نمی‌دارد، پس پنل
        نمی‌داند این واسطه‌ها از کی کار می‌کنند و همه‌ی کانفیگ‌هایشان را
        <b> یک ماه </b> حساب می‌کند. اگر بگویید همکاری از چه تاریخی شروع
        شده، از همان روز محاسبه می‌شود.
      </p>
      <div className="flex gap-1.5 flex-wrap my-3">
        {groups.slice(0, 12).map((g) => (
          <span key={g} className="fx-pill" style={{
            background: "rgba(255,255,255,.05)", color: "var(--muted)",
          }}>{g}</span>
        ))}
      </div>

      <Msg msg={msg} />

      {!open ? (
        <button onClick={() => setOpen(true)}
          className="fx-btn px-4 py-2.5 text-[13px]">
          تعیین تاریخ شروع برای همه
        </button>
      ) : (
        <div className="flex gap-2 items-end flex-wrap">
          <div style={{ minWidth: 180 }}>
            <Field label="همکاری از چه تاریخی شروع شد؟"
              hint="تقویم شمسی — همین یک بار لازم است">
              <JalaliDate value={date} onChange={setDate}
                placeholder="انتخاب تاریخ شروع" />
            </Field>
          </div>
          <button onClick={apply} disabled={busy || !date}
            className="fx-btn px-4 py-2.5 text-[13px] flex items-center gap-1.5">
            {busy && <Loader2 size={13} className="animate-spin" />} اعمال
          </button>
          <button onClick={() => setOpen(false)}
            className="fx-btn-g px-4 py-2.5 text-[13px]">انصراف</button>
        </div>
      )}

      <p className="text-[12px] mt-3" style={{ color: "var(--muted)" }}>
        گروه‌هایی که از قبل تاریخ دارند دست‌نخورده می‌مانند. از امروز به
        بعد، پنل خودش تاریخ اولین دیدن هر کانفیگ تازه را ثبت می‌کند و
        این مشکل دیگر پیش نمی‌آید.
      </p>
    </div>
  );
}


export function BillingDash({ password }) {
  const { data, loading, reload } = useBilling(password);
  if (loading) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;
  if (!data?.ready) return (
    <div className="fx-anim">
      <SectionHead title="داشبورد حسابداری" desc="" />
      <BillingUnavailable info={data} password={password} />
    </div>
  );

  const billed = data.groups.filter((g) => g.billed);
  const due = billed.reduce((s, g) => s + g.amount, 0);
  const paid = billed.reduce((s, g) => s + g.paid, 0);
  const uncertain = billed.reduce((s, g) => s + (g.uncertain || 0), 0);

  return (
    <div className="fx-anim">
      <SectionHead title="داشبورد حسابداری"
        desc={`${faNum(data.totalClients)} کانفیگ در ${faNum(data.groups.length)} گروه`}
        action={
          <button onClick={reload} className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
            <RefreshCw size={13} /> تازه‌سازی
          </button>
        } />

      {(data.needStart || []).length > 0 && <NeedStartBanner
        groups={data.needStart} password={password} onDone={reload} />}

      <div className="grid gap-3 mb-6" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))" }}>
        {[["کل بدهی دوره", due, "var(--accent-2)"],
          ["دریافت‌شده", paid, "var(--ok)"],
          ["مانده", due - paid, due - paid > 0 ? "var(--warn)" : "var(--ok)"]].map(([l, v, col], i) => (
          <div key={i} className="fx-card p-4">
            <div className="fx-stat-num text-[21px] font-extrabold leading-none"
              style={{ color: col, fontFamily: "var(--mono)" }}>{faNum(v)}</div>
            <div className="text-[12px] mt-2" style={{ color: "var(--dim)" }}>{l} · تومان</div>
          </div>
        ))}
      </div>

      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-4">وضعیت هر واسطه</div>
        {billed.length === 0 ? (
          <div className="text-center py-8 text-[13px]" style={{ color: "var(--muted)" }}>
            هنوز گروهی به‌عنوان واسطه علامت نخورده — از بخش «واسطه‌ها و نرخ» شروع کنید
          </div>
        ) : billed.map((g, i) => {
          const rest = g.amount - g.paid;
          const pct = g.amount ? Math.min(100, Math.round(g.paid * 100 / g.amount)) : 0;
          return (
            <div key={g.name} className="py-3.5"
              style={{ borderBottom: i < billed.length - 1 ? "1px solid var(--border)" : "none" }}>
              <div className="flex justify-between items-start gap-3 mb-2.5 flex-wrap">
                <div>
                  <div className="text-[14px] font-semibold text-white">{g.label}</div>
                  <div className="text-[12px] mt-1" dir="ltr"
                    style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                    {g.name} · {g.configs} config · {g.months} months
                  </div>
                </div>
                <div className="text-left">
                  <div className="text-[14px] font-extrabold"
                    style={{ color: rest > 0 ? "var(--warn)" : "var(--ok)", fontFamily: "var(--mono)" }}>
                    {faNum(rest)}
                  </div>
                  <div className="text-[11.5px] mt-0.5" style={{ color: "var(--muted)" }}>
                    {rest > 0 ? "مانده" : "تسویه شده"}
                  </div>
                </div>
              </div>
              <div className="h-[5px] rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,.05)" }}>
                <div style={{
                  width: `${pct}%`, height: "100%", borderRadius: 99,
                  background: pct >= 100 ? "var(--ok)" : "linear-gradient(90deg,var(--accent),var(--accent-2))",
                  transition: "width .5s cubic-bezier(.22,1,.36,1)",
                }} />
              </div>
              {g.unpriced?.length > 0 && (
                <div className="text-[12px] mt-2" style={{ color: "var(--warn)" }}>
                  حجم بدون نرخ: {g.unpriced.map((v) => v ? `${faNum(v)}GB` : "نامحدود").join("، ")}
                </div>
              )}
              {/* دلیلش، نه فقط تعدادش.
                  «۷ کانفیگ بدون نرخ» مدیری را که نرخ تعریف کرده به
                  هیچ‌جا نمی‌برد جز این نتیجه که پنل خراب است. */}
              {Object.keys(g.unpricedWhy || {}).length > 0 && (
                <div className="text-[12px] mt-1.5 leading-relaxed"
                  style={{ color: "var(--warn)" }}>
                  {Object.entries(g.unpricedWhy).map(([why, n]) => (
                    <div key={why}>• {faNum(n)} کانفیگ: {why}</div>
                  ))}
                </div>
              )}
              {/* کانفیگ‌هایی که نرخ نگرفتند — با دلیل، تا معلوم باشد
                  چرا عدد صورت‌حساب از تعداد کانفیگ‌ها کمتر است */}
              {g.skipped > 0 && (
                <div className="text-[12px] mt-2" style={{ color: "var(--muted)" }}>
                  {faNum(g.skipped)} کانفیگ حساب نشد
                  {Object.keys(g.skippedWhy || {}).length > 0 && (
                    <span> — {Object.entries(g.skippedWhy)
                      .map(([w, n]) => `${faNum(n)} ${w}`).join("، ")}</span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {uncertain > 0 && (
        <InfoBox tone="warn">
          <b>{faNum(uncertain)} کانفیگ تمدید تخمینی دارند.</b> پنل ۳x-ui تاریخچه‌ی تمدید
          ندارد، پس تعداد ماه از فاصله‌ی «ایجاد تا انقضا» حساب می‌شود. اگر تمدید زودتر از
          موعد انجام شده باشد، عدد کمتر از واقعیت درمی‌آید.
          <br /><br />
          از امروز هر تمدیدی که از ربات یا پنل انجام شود ثبت می‌شود و تخمین جای خودش را
          به عدد قطعی می‌دهد.
        </InfoBox>
      )}
    </div>
  );
}

export function BillingGroups({ password }) {
  const { data, loading, reload } = useBilling(password);
  const [open, setOpen] = useState(null);
  const [draft, setDraft] = useState({});
  const [saving, setSaving] = useState(null);

  if (loading) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;
  if (!data?.ready) return (
    <div className="fx-anim">
      <SectionHead title="واسطه‌ها و نرخ" desc="" />
      <BillingUnavailable info={data} password={password} />
    </div>
  );

  const get = (g) => draft[g.name] || {
    label: g.label, billed: g.billed, rates: g.rates, perGb: g.perGb || 0,
    periodDays: g.periodDays || 30,
    periodStart: g.periodStart || "",
    settledUntil: g.settledUntil || "",
  };
  const set = (g, patch) => setDraft({ ...draft, [g.name]: { ...get(g), ...patch } });

  const save = async (g) => {
    setSaving(g.name);
    try {
      await fetch(`${API_URL}/api/admin/billing/group/${encodeURIComponent(g.name)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify(get(g)),
      });
      await reload();
      setDraft({ ...draft, [g.name]: undefined });
    } finally { setSaving(null); }
  };

  return (
    <div className="fx-anim">
      <SectionHead title="واسطه‌ها و نرخ"
        desc="گروه‌ها از ۳x-ui خوانده می‌شوند. برای هرکدام تعیین کنید واسطه است یا مشتری مستقیم." />

      {/* گروه‌هایی که هیچ درآمدی از آن‌ها شمرده نمی‌شود.
          بدون این، تنها نشانه‌اش این بود که عدد کل از انتظار کمتر
          است — و هیچ‌جا نمی‌گفت چرا یا کدام گروه. */}
      {(data.needsSetup || []).length > 0 && (
        <div className="fx-card p-5 mb-4"
          style={{ borderColor: "rgba(251,191,36,.3)" }}>
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle size={15} style={{ color: "var(--warn)" }} />
            <span className="text-[14px] font-semibold text-white">
              نیاز به تنظیم
            </span>
          </div>
          <p className="text-[13px] mb-3" style={{ color: "var(--muted)" }}>
            {faNum(data.needsSetupConfigs)} کانفیگ در{" "}
            {faNum(data.needsSetup.length)} گروه در صورتحساب حساب نمی‌شوند.
          </p>

          {data.needsSetup.map((n) => (
            <div key={n.key}
              className="flex items-center justify-between gap-3 py-2 flex-wrap"
              style={{ borderTop: "1px solid var(--border)" }}>
              <div className="min-w-0">
                <div className="text-[13px] text-white" dir="ltr"
                  style={{ fontFamily: "var(--mono)" }}>{n.key}</div>
                <div className="text-[12px] mt-0.5" style={{ color: "var(--warn)" }}>
                  {faNum(n.configs)} کانفیگ · {n.why}
                </div>
              </div>
              <button onClick={() => setOpen(n.key)}
                className="fx-btn-g px-3 py-2 text-[13px] shrink-0">
                تنظیم کن
              </button>
            </div>
          ))}
        </div>
      )}

      {data.groups.map((g) => {
        const d = get(g);
        const isOpen = open === g.name;
        const dirty = !!draft[g.name];
        return (
          <div key={g.name} className="fx-card mb-3 overflow-hidden" style={{ padding: 0 }}>
            <div onClick={() => setOpen(isOpen ? null : g.name)}
              className="p-4 cursor-pointer flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-3">
                <div className="fx-ico" style={{ background: d.billed ? "rgba(43,127,214,.12)" : "rgba(255,255,255,.04)" }}>
                  <Users size={16} style={{ color: d.billed ? "var(--accent-2)" : "var(--muted)" }} />
                </div>
                <div>
                  <div className="text-[14px] font-semibold text-white">{d.label || g.name}</div>
                  <div className="text-[12px] mt-1" dir="ltr"
                    style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                    {g.name} · {g.configs} configs · {g.usedGB}GB used
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {d.billed && g.amount > 0 && (
                  <span className="text-[13px] font-bold"
                    style={{ color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
                    {faNum(g.amount)}
                  </span>
                )}
                <div onClick={(e) => { e.stopPropagation(); set(g, { billed: !d.billed }); }}>
                  <Toggle checked={d.billed} onChange={() => {}} />
                </div>
              </div>
            </div>

            {isOpen && (
              <div className="px-4 pb-4" style={{ borderTop: "1px solid var(--border)" }}>
                {!d.billed ? (
                  <div className="py-6 text-center text-[13px]" style={{ color: "var(--muted)" }}>
                    مشتری مستقیم شماست — در صورتحساب واسطه‌ها نمی‌آید.
                  </div>
                ) : (
                  <>
                    <div className="pt-4">
                      <Field label="نام نمایشی">
                        <input className="fx-input" value={d.label || ""}
                          onChange={(e) => set(g, { label: e.target.value })}
                          placeholder={g.name} />
                      </Field>
                    </div>

                    {/* دو مدل قیمت‌گذاری — یا ماهانه بر اساس پلن، یا حجمی */}
                    <div className="flex gap-2 mb-4">
                      {[["پلنی", false], ["حجمی", true]].map(([label, isGb]) => {
                        const on = !!d.perGb === isGb;
                        return (
                          <button key={label}
                            onClick={() => set(g, { perGb: isGb ? (d.perGb || 3000) : 0 })}
                            className="flex-1 py-2.5 rounded-xl text-[13px] transition-all"
                            style={{
                              background: on ? "var(--accent-soft)" : "var(--surface-3)",
                              border: `1px solid ${on ? "rgba(43,127,214,.4)" : "var(--border)"}`,
                              color: on ? "var(--accent-2)" : "var(--muted)",
                            }}>
                            {label}
                          </button>
                        );
                      })}
                    </div>

                    {d.perGb ? (
                      <div className="mb-3">
                        <Field label="نرخ هر گیگابایت (تومان)"
                          hint="بر اساس مصرف واقعی حساب می‌شود، نه سقف پلن">
                          <div className="flex items-center gap-2">
                            <input className="fx-input" type="number" dir="ltr"
                              value={d.perGb || ""}
                              onChange={(e) => set(g, { perGb: Math.max(0, +e.target.value) })}
                              placeholder="3000"
                              style={{ fontFamily: "var(--mono)" }} />
                            <div className="flex gap-1.5 shrink-0">
                              {[2000, 3000, 5000].map((q) => (
                                <button key={q} onClick={() => set(g, { perGb: q })}
                                  className="px-2.5 py-2 rounded-lg text-[12px]"
                                  style={{
                                    background: d.perGb === q ? "var(--accent-soft)" : "transparent",
                                    border: `1px solid ${d.perGb === q ? "rgba(43,127,214,.4)" : "var(--border)"}`,
                                    color: d.perGb === q ? "var(--accent-2)" : "var(--muted)",
                                    fontFamily: "var(--mono)",
                                  }}>{faNum(q / 1000)}k</button>
                              ))}
                            </div>
                          </div>
                        </Field>
                        {g.usedGB > 0 && (
                          <div className="text-[13px] p-2.5 rounded-lg"
                            style={{ background: "var(--surface-3)", color: "var(--dim)" }}>
                            {faNum(g.usedGB)} GB × {faNum(d.perGb)} = {" "}
                            <b style={{ color: "var(--accent-2)" }}>
                              {faNum(Math.round(g.usedGB * d.perGb))} تومان
                            </b>
                          </div>
                        )}
                      </div>
                    ) : (
                    <>
                    <div className="flex justify-between items-center mb-3 mt-1 flex-wrap gap-2">
                      <span className="text-[13px]" style={{ color: "var(--dim)" }}>نرخ ماهانه بر اساس حجم</span>
                      <button onClick={() => set(g, { rates: [...(d.rates || []), { gb: 0, price: 190000, perDevice: 0 }] })}
                        className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
                        <PlusIcon size={12} /> افزودن نرخ
                      </button>
                    </div>

                    {(d.rates || []).length === 0 && (
                      <div className="rounded-xl p-4 text-center mb-3"
                        style={{ background: "rgba(251,191,36,.06)", border: "1px dashed rgba(251,191,36,.3)" }}>
                        <div className="text-[13px] mb-1" style={{ color: "var(--warn)" }}>هنوز نرخی تعریف نشده</div>
                        <div className="text-[12px]" style={{ color: "var(--muted)" }}>
                          بدون نرخ، این گروه صفر حساب می‌شود
                        </div>
                      </div>
                    )}

                    {(d.rates || []).map((r, i) => (
                      <RateRow key={i} rate={r}
                        onChange={(patch) => {
                          const l = [...d.rates]; l[i] = { ...l[i], ...patch };
                          set(g, { rates: l });
                        }}
                        onDelete={() => set(g, { rates: d.rates.filter((_, x) => x !== i) })} />
                    ))}

                    </>
                    )}

                    {/* دوره‌ی پرداخت — بدون این، معلوم نیست بابت چه بازه‌ای
                        پول می‌گیرید و پرداخت‌ها با هم قاطی می‌شوند */}
                    <div className="mt-4 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
                      <div className="text-[13px] mb-3" style={{ color: "var(--dim)" }}>
                        دوره‌ی پرداخت
                      </div>

                      <div className="flex gap-2 mb-3">
                        {[["هفتگی", 7], ["دوهفته", 14], ["ماهانه", 30]].map(([l, n]) => {
                          const on = (d.periodDays || 30) === n;
                          return (
                            <button key={n} onClick={() => set(g, { periodDays: n })}
                              className="flex-1 py-2 rounded-xl text-[13px]"
                              style={{
                                background: on ? "var(--accent-soft)" : "var(--surface-3)",
                                border: `1px solid ${on ? "rgba(43,127,214,.4)" : "var(--border)"}`,
                                color: on ? "var(--accent-2)" : "var(--muted)",
                              }}>{l}</button>
                          );
                        })}
                      </div>

                      <div className="fx-g3 grid grid-cols-2 gap-3">
                        <Field label="شروع همکاری"
                          hint="مبنای شمارش ماه‌ها — تقویم شمسی">
                          <JalaliDate value={d.periodStart || ""}
                            onChange={(v) => set(g, { periodStart: v })}
                            placeholder="انتخاب تاریخ شروع" />
                        </Field>
                        <Field label="تسویه‌شده تا"
                          hint="قبل از این تاریخ حساب نمی‌شود">
                          <JalaliDate value={d.settledUntil || ""}
                            onChange={(v) => set(g, { settledUntil: v })}
                            placeholder="هنوز تسویه‌ای نشده" />
                        </Field>
                      </div>
                    </div>

                    <div className="grid gap-2 mt-3 pt-3" style={{
                      gridTemplateColumns: "repeat(auto-fit,minmax(100px,1fr))",
                      borderTop: "1px solid var(--border)",
                    }}>
                      {[["کانفیگ", g.configs], ["فعال", g.active],
                        ["ماه", g.months], ["تمدید", g.renewals]].map(([k, v], i) => (
                        <div key={i} className="text-center">
                          <div className="text-[16px] font-bold text-white" style={{ fontFamily: "var(--mono)" }}>
                            {faNum(v)}
                          </div>
                          <div className="text-[11.5px] mt-1" style={{ color: "var(--muted)" }}>{k}</div>
                        </div>
                      ))}
                    </div>
                  </>
                )}

                {dirty && (
                  <button onClick={() => save(g)} disabled={saving === g.name}
                    className="fx-btn w-full mt-4 py-2.5 text-[14px] flex items-center justify-center gap-2">
                    {saving === g.name ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                    ذخیره
                  </button>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function BillingInvoice({ password }) {
  const { data, loading } = useBilling(password);
  const [sel, setSel] = useState("");
  const [inv, setInv] = useState(null);
  const [busy, setBusy] = useState(false);
  //: صورتحساب از چه تاریخی به بعد.
  //
  //  خالی یعنی «هرچه خودِ گروه می‌گوید» — تسویه‌شده تا، و بعد شروع
  //  همکاری. این فیلد برای وقتی است که مدیر می‌خواهد یک بار فاکتور
  //  را از تاریخ دیگری بگیرد بدون اینکه تنظیمات گروه را دست بزند.
  const [from, setFrom] = useState("");

  const billed = data?.groups?.filter((g) => g.billed) || [];
  const cur = billed.find((g) => g.name === sel);
  //  اگر مدیر تاریخی نزند، سرور همین را به کار می‌برد — پس همان را
  //  نشان می‌دهیم، تا فاکتورِ کوتاه غافلگیرکننده نباشد.
  const autoFrom = cur?.settledUntil || cur?.periodStart || "";
  const q = from ? `?start=${encodeURIComponent(from)}` : "";

  /**
   * دانلود صورتحساب PDF.
   *
   * چون endpoint هدر رمز می‌خواهد، نمی‌شود مستقیم لینک داد —
   * باید fetch کنیم و blob را دانلود کنیم.
   */
  const downloadPdf = async () => {
    if (!sel) return;
    setBusy(true);
    try {
      // بازه بیرون از قالب مسیر می‌چسبد، نه داخلش: تست درز مسیرها را
      // از روی همین قالب‌ها استخراج می‌کند و ${q} داخلش یک قطعه‌ی
      // جعلی می‌ساخت.
      const url =
        `${API_URL}/api/admin/billing/invoice/${encodeURIComponent(sel)}/pdf`;
      const res = await fetch(url + q,
        { headers: { "X-Admin-Password": password } });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        alert(errText(d.detail, "ساخت PDF ناموفق بود"));
        return;
      }
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `nexora-${sel}-${new Date().toISOString().slice(0, 10)}.pdf`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch {
      alert("اتصال به سرور برقرار نشد");
    } finally { setBusy(false); }
  };
  useEffect(() => { if (!sel && billed.length) setSel(billed[0].name); }, [data]);

  const gen = async () => {
    if (!sel) return;
    setBusy(true);
    try {
      const url =
        `${API_URL}/api/admin/billing/invoice/${encodeURIComponent(sel)}`;
      const d = await fetch(url + q, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setInv(d);
    } finally { setBusy(false); }
  };

  if (loading) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;
  if (!data?.ready) return (
    <div className="fx-anim"><SectionHead title="صورتحساب" desc="" /><BillingUnavailable info={data} password={password} /></div>
  );

  return (
    <div className="fx-anim">
      <SectionHead title="صورتحساب" desc="جزئیات کامل هر واسطه، آماده برای ارسال." />

      {billed.length === 0 ? (
        <div className="fx-card p-8 text-center" style={{ borderStyle: "dashed" }}>
          <FileText size={24} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
          <div className="text-[14px]" style={{ color: "var(--muted)" }}>
            ابتدا حداقل یک گروه را واسطه علامت بزنید
          </div>
        </div>
      ) : (
        <>
          <div className="fx-card p-5 mb-4">
            <Field label="واسطه">
              <select className="fx-input" value={sel} onChange={(e) => { setSel(e.target.value); setInv(null); }}>
                {billed.map((g) => <option key={g.name} value={g.name}>{g.label}</option>)}
              </select>
            </Field>

            <Field label="حساب کن از تاریخ">
              <JalaliDate value={from} placeholder="پیش‌فرضِ همین گروه"
                onChange={(v) => { setFrom(v || ""); setInv(null); }} />
            </Field>
            <div className="text-[12px] -mt-2 mb-3 leading-relaxed"
              style={{ color: "var(--muted)" }}>
              {from ? (
                <>
                  فقط کانفیگ‌ها و تمدیدهای بعد از{" "}
                  <span style={{ color: "var(--accent-2)" }}>
                    {isoToJalaliLabel(from)}
                  </span>{" "}
                  حساب می‌شوند.{" "}
                  <button onClick={() => { setFrom(""); setInv(null); }}
                    style={{ color: "var(--dim)", textDecoration: "underline" }}>
                    برگرد به پیش‌فرض
                  </button>
                </>
              ) : autoFrom ? (
                <>
                  خالی یعنی از{" "}
                  <span style={{ color: "var(--accent-2)" }}>
                    {isoToJalaliLabel(autoFrom)}
                  </span>{" "}
                  — {cur?.settledUntil ? "تسویه‌شده تا" : "شروع همکاری"}ی که
                  برای این گروه ثبت شده.
                </>
              ) : (
                <>
                  برای این گروه نه «تسویه‌شده تا» ثبت شده نه «شروع همکاری»،
                  پس کل عمر هر کانفیگ حساب می‌شود — یعنی تمدیدهای دوره‌های
                  تسویه‌شده هم دوباره می‌آیند.
                </>
              )}
            </div>

            <div className="fx-g3 grid grid-cols-2 gap-3">
              <button onClick={gen} disabled={busy}
                className="fx-btn py-2.5 text-[14px] flex items-center justify-center gap-2">
                {busy ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />}
                نمایش صورتحساب
              </button>
              <button onClick={downloadPdf} disabled={busy || !sel}
                className="fx-btn-g py-2.5 text-[14px] flex items-center justify-center gap-2">
                <Download size={14} /> دانلود PDF
              </button>
            </div>
          </div>

          {inv && (
            <div className="fx-card p-5">
              <div className="text-[14px] font-semibold text-white mb-1">{inv.label}</div>
              <div className="text-[12px] mb-4" style={{ color: "var(--muted)" }}>
                {inv.sinceJalali
                  ? `از ${inv.sinceJalali} تا امروز · ${inv.sinceWhy}`
                  : "از ابتدای همکاری تا امروز"}
              </div>

              {inv.totals?.before > 0 && (
                <InfoBox tone="info">
                  {faNum(inv.totals.before)} کانفیگ روی این فاکتور نیامد، چون
                  همه‌ی ماه‌هایشان ({faNum(inv.totals.beforeMonths)} ماه) پیش از
                  این تاریخ بوده و قبلاً حساب شده.
                </InfoBox>
              )}

              {inv.totals?.unused > 0 && (
                <InfoBox tone="info">
                  {faNum(inv.totals.unused)} کانفیگ حساب نشد —{" "}
                  {Object.keys(inv.totals.unusedWhy || {}).join("، ")}. همین
                  قاعده در داشبورد هم اعمال می‌شود، پس دو صفحه یک عدد
                  می‌دهند.
                </InfoBox>
              )}

              {inv.unpricedVolumes?.length > 0 && (
                <InfoBox tone="warn">
                  حجم‌های بدون نرخ کنار گذاشته شدند:{" "}
                  {inv.unpricedVolumes.map((v) => v ? `${faNum(v)}GB` : "نامحدود").join("، ")}
                  {(inv.unpricedWhy || []).map((why) => (
                    <div key={why} className="mt-1.5">— {why}</div>
                  ))}
                </InfoBox>
              )}

              <div className="rounded-xl p-4 mb-4" style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
                {[["کل مبلغ", inv.totalAmount, "var(--text)"],
                  ["پرداخت‌شده", inv.paid, "var(--ok)"],
                  ["مانده", inv.balance, inv.balance > 0 ? "var(--warn)" : "var(--ok)"]].map(([k, v, col], i) => (
                  <div key={i} className="flex justify-between py-1.5">
                    <span className="text-[13px]" style={{ color: i === 2 ? "var(--text)" : "var(--muted)" }}>{k}</span>
                    <span className="font-bold" style={{
                      color: col, fontSize: i === 2 ? 14 : 12,
                      fontFamily: "var(--mono)",
                    }}>{faNum(v)}</span>
                  </div>
                ))}
              </div>

              <div className="text-[13px] mb-2" style={{ color: "var(--dim)" }}>
                {faNum(inv.items.length)} کانفیگ
              </div>
              <div style={{ maxHeight: 320, overflowY: "auto" }}>
                {inv.items.map((it, i) => (
                  <div key={i} className="flex justify-between items-center py-2.5 gap-3"
                    style={{ borderBottom: i < inv.items.length - 1 ? "1px solid var(--border)" : "none" }}>
                    <div className="min-w-0">
                      <div className="text-[13px] truncate" dir="ltr"
                        style={{ color: "var(--text)", fontFamily: "var(--mono)" }}>
                        {it.email}
                      </div>
                      <div className="text-[11.5px] mt-1" style={{ color: "var(--muted)" }}>
                        {it.gb ? `${faNum(it.gb)}GB` : "نامحدود"} · {faNum(it.months)} ماه
                        {it.renewals > 0 && ` · ${faNum(it.renewals)} تمدید`}
                        {!it.certain && it.drift != null && ` · ±${it.drift} روز`}
                      </div>
                    </div>
                    <span className="text-[13px] font-semibold shrink-0"
                      style={{
                        color: it.lineTotal == null ? "var(--warn)" : "var(--dim)",
                        fontFamily: "var(--mono)",
                      }}>
                      {it.lineTotal == null ? "بدون نرخ" : faNum(it.lineTotal)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function BillingPayments({ password }) {
  const { data } = useBilling(password);
  const [list, setList] = useState([]);
  const [add, setAdd] = useState(false);
  const [form, setForm] = useState({ group: "", amount: "", date: "", note: "" });
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/billing/payments`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setList(d.payments || []);
    } catch { /* بی‌صدا */ }
  };
  useEffect(() => { load(); }, [password]);

  const billed = data?.groups?.filter((g) => g.billed) || [];

  const submit = async () => {
    if (!form.group || !form.amount) return;
    setBusy(true);
    try {
      await fetch(`${API_URL}/api/admin/billing/payment`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ ...form, amount: Number(form.amount) }),
      });
      setAdd(false);
      setForm({ group: "", amount: "", date: "", note: "" });
      load();
    } finally { setBusy(false); }
  };

  const del = async (id) => {
    await fetch(`${API_URL}/api/admin/billing/payment/${id}`, {
      method: "DELETE", headers: { "X-Admin-Password": password },
    });
    load();
  };

  return (
    <div className="fx-anim">
      <SectionHead title="پرداخت‌ها"
        desc="پرداخت‌های واسطه در ۳x-ui ثبت نمی‌شوند — هر دریافتی را اینجا بزنید تا مانده درست حساب شود."
        action={
          <button onClick={() => setAdd(true)} className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
            <PlusIcon size={14} /> ثبت پرداخت
          </button>
        } />

      {list.length === 0 ? (
        <div className="fx-card p-8 text-center" style={{ borderStyle: "dashed" }}>
          <Wallet size={24} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
          <div className="text-[14px]" style={{ color: "var(--muted)" }}>هنوز پرداختی ثبت نشده</div>
        </div>
      ) : (
        <div className="fx-card overflow-hidden" style={{ padding: 0 }}>
          {list.map((p, i) => {
            const g = data?.groups?.find((x) => x.name === p.group_name);
            return (
              <div key={p.id} className="p-4 flex justify-between items-center gap-3 flex-wrap"
                style={{ borderBottom: i < list.length - 1 ? "1px solid var(--border)" : "none" }}>
                <div>
                  <div className="text-[14px] font-semibold text-white">{g?.label || p.group_name}</div>
                  <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
                    {isoToJalaliLabel(p.paid_at || p.created_at?.slice(0, 10))}
                    {p.note && ` · ${p.note}`}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[14px] font-bold" style={{ color: "var(--ok)", fontFamily: "var(--mono)" }}>
                    +{faNum(p.amount)}
                  </span>
                  <button onClick={() => del(p.id)} className="fx-ico-btn" style={{ width: 28, height: 28 }}>
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {add && createPortal(
        <div className="nx-modal-wrap fx-fade" onClick={() => setAdd(false)}>
          <div className="fx-card fx-scale p-5" style={{ width: "min(400px,92vw)" }}
            onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <span className="text-[16px] font-bold text-white">ثبت پرداخت</span>
              <button onClick={() => setAdd(false)} className="fx-ico-btn" style={{ width: 28, height: 28 }}>
                <X size={14} />
              </button>
            </div>
            <Field label="واسطه">
              <select className="fx-input" value={form.group}
                onChange={(e) => setForm({ ...form, group: e.target.value })}>
                <option value="">انتخاب کنید</option>
                {billed.map((g) => <option key={g.name} value={g.name}>{g.label}</option>)}
              </select>
            </Field>
            <Field label="مبلغ (تومان)">
              <input className="fx-input" dir="ltr" type="number" value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
                style={{ fontFamily: "var(--mono)" }} />
            </Field>
            <Field label="تاریخ" hint="اختیاری">
              <input className="fx-input" value={form.date}
                onChange={(e) => setForm({ ...form, date: e.target.value })}
                placeholder="۱۴۰۵/۰۶/۲۵" />
            </Field>
            <Field label="توضیح" hint="اختیاری">
              <input className="fx-input" value={form.note}
                onChange={(e) => setForm({ ...form, note: e.target.value })} />
            </Field>
            <button onClick={submit} disabled={busy || !form.group || !form.amount}
              className="fx-btn w-full py-2.5 text-[14px] flex items-center justify-center gap-2 mt-2">
              {busy ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
              ثبت
            </button>
          </div>
        </div>, document.body)}
    </div>
  );
}
