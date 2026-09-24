/**
 * ربات: آمار، قیف و گزارش فروش.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
import React, { useState, useEffect } from "react";
import {
  FileText, Download, RefreshCw, TrendingUp, Users,
} from "lucide-react";
import { API_URL } from "../../lib/constants";
import { errText, esc0, faNum } from "../../lib/format";
import { AreaChart, Avatar, CountUp, EmptyState, PageSkeleton, SectionHead, Segmented, StatTile } from "../../ui/index";
import { isoToJalaliLabel } from "../../ui/jalali";

export function BotStatsSection({ password }) {
  const [d, setD] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API_URL}/api/admin/bot/funnel`, {
        headers: { "X-Admin-Password": password } }).then((x) => x.json());
      setD(r);
    } catch { /* بی‌صدا */ }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [password]);

  if (loading) return <PageSkeleton />;

  if (!d?.ready) {
    return (
      <div className="fx-anim">
        <SectionHead title="آمار و قیف تبدیل" desc="وقتی ربات راه بیفتد، آمار اینجا نمایش داده می‌شود." />
        <EmptyState icon={TrendingUp} text="هنوز داده‌ای نیست" />
      </div>
    );
  }

  const seg = d.segments || {};
  const cards = [
    ["استارت‌زده", d.started, "کل کسانی که ربات را باز کردند", "var(--accent-2)"],
    // بدونِ عدد، «NaN٪» روی صفحه می‌آمد — درصدی که حساب نشده، نوشته نمی‌شود
    ["خرید کرده", seg.paid, d.started && Number.isFinite(seg.paid)
      ? `${faNum(Math.round(seg.paid * 100 / d.started))}٪ نرخ تبدیل` : "", "var(--ok)"],
    ["فقط تست گرفته", seg.trialOnly, "هدف خوبی برای پیگیری", "var(--warn)"],
    ["بدون هیچ اقدام", seg.idle, "نه خرید، نه تست", "var(--muted)"],
  ];

  return (
    <div className="fx-anim">
      <SectionHead title="آمار و قیف تبدیل"
        desc="از باز کردن ربات تا خرید — کجا مشتری را از دست می‌دهید."
        action={
          <button onClick={load} className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
            <RefreshCw size={13} /> تازه‌سازی
          </button>
        } />

      <div className="fx-g4 grid grid-cols-4 gap-4 mb-5">
        {cards.map(([l, v, sub, c], i) => (
          <div key={i} className="fx-card p-5">
            <div className="fx-stat-num" style={{ color: c }}><CountUp value={v ?? 0} /></div>
            <div className="text-[13px] mt-2" style={{ color: "var(--dim)" }}>{l}</div>
            {sub && <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>{sub}</div>}
          </div>
        ))}
      </div>

      <div className="fx-card p-5">
        <div className="text-[14px] font-semibold text-white mb-1">قیف تبدیل</div>
        <p className="text-[12px] mb-4" style={{ color: "var(--muted)" }}>
          هر پله نسبت به کل بازدید. عدد قرمز بین دو پله یعنی چند درصد
          همان‌جا از دست می‌روند — همان‌جایی که باید درستش کرد.
        </p>
        {(d.steps || []).map((s, i, arr) => {
          const colors = ["var(--accent-2)", "var(--purple)", "var(--warn)", "var(--ok)"];
          const c = colors[i] || "var(--accent-2)";
          // ریزش نسبت به پله‌ی قبل، نه نسبت به کل
          const prev = i > 0 ? arr[i - 1] : null;
          const drop = prev && prev.n
            ? Math.round(((prev.n - s.n) * 100) / prev.n) : null;
          return (
            <div key={i}>
              {drop !== null && drop > 0 && (
                <div className="flex items-center gap-2 my-1.5 pr-1">
                  <span style={{ color: "var(--danger)", fontSize: 11 }}>
                    ↓ {faNum(drop)}٪ ریزش
                  </span>
                  <div className="flex-1 h-px" style={{
                    background: "linear-gradient(90deg, var(--danger), transparent)",
                    opacity: 0.35,
                  }} />
                </div>
              )}
              <div className="mb-1">
                <div className="flex justify-between mb-1.5">
                  <span className="text-[13px]" style={{ color: "var(--dim)" }}>
                    {s.label}
                  </span>
                  <span className="text-[13px] font-bold"
                    style={{ color: c, fontFamily: "var(--mono)" }}>
                    {faNum(s.n)}
                    <span style={{ color: "var(--muted)", fontSize: 10 }}>
                      {" "}({faNum(s.pct)}٪)
                    </span>
                  </span>
                </div>
                <div className="h-[9px] rounded-full overflow-hidden"
                  style={{ background: "var(--hair-2)" }}>
                  <div style={{
                    width: `${Math.max(s.pct, 1)}%`, height: "100%",
                    borderRadius: 99,
                    // آلفای هگز چسبیده به var(--…) رنگِ نامعتبر می‌سازد و مرورگر کلِ شیب را
                    // دور می‌ریزد — قیف روی سرورِ واقعی هم نوارِ خالی بود
                    background: `linear-gradient(90deg, ${c}, color-mix(in srgb, ${c} 60%, transparent))`,
                    // حرکت نرم موقع تغییر بازه — نه پرش ناگهانی
                    transition: "width .5s cubic-bezier(.4,0,.2,1)",
                  }} />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export const REPORT_RANGES = [[7, "۷ روز"], [30, "۳۰ روز"], [90, "۹۰ روز"], [365, "یک سال"]];

/**
 * گزارش فروش ربات.
 *
 * حسابداری می‌گوید از هر واسطه چقدر طلب دارید؛ این می‌گوید فروش
 * مستقیم ربات در یک دوره چه شکلی بوده — چند نفر آمدند، چند درصدشان
 * خریدند، و چه کسانی بیشترین سهم را داشتند.
 */
export function BotReportSection({ password }) {
  const [days, setDays] = useState(30);
  const [d, setD] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hover, setHover] = useState(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    fetch(`${API_URL}/api/admin/bot/users/report?days=${days}`, {
      headers: { "X-Admin-Password": password },
    }).then((r) => r.json())
      .then((j) => { if (alive) { setD(j); setLoading(false); } })
      .catch(() => { if (alive) { setD({ ready: false }); setLoading(false); } });
    return () => { alive = false; };
  }, [password, days]);

  const [busy, setBusy] = useState(false);

  /**
   * دانلود فایل از یک مسیر محافظت‌شده.
   *
   * نسخه‌ی قبلی آدرس را مستقیم در <a href> می‌گذاشت. مرورگر در آن
   * حالت هیچ هدری نمی‌فرستد، پس سرور ۴۰۱ می‌داد و کاربر یک فایل
   * خطا دانلود می‌کرد بدون اینکه بفهمد چرا. پس fetch می‌کنیم و
   * blob را دانلود می‌دهیم.
   */
  const grab = async (path, filename) => {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}${path}`, {
        headers: { "X-Admin-Password": password },
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        alert(errText(j.detail, "ساخت فایل ناموفق بود"));
        return;
      }
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch {
      alert("اتصال به سرور برقرار نشد");
    } finally { setBusy(false); }
  };

  const today = new Date().toISOString().slice(0, 10);
  const download = () => grab("/api/admin/bot/users/export",
                              `nexora-users-${today}.csv`);
  const downloadPdf = () => grab(
    `/api/admin/bot/users/report/pdf?days=${days}`,
    `nexora-bot-report-${days}d-${today}.pdf`);

  if (loading) return <PageSkeleton />;

  if (!d?.ready) {
    return (
      <div className="fx-anim">
        <SectionHead title="گزارش فروش" desc="خلاصه‌ی عملکرد ربات در یک بازه." />
        <div className="fx-card p-5">
          <p className="text-[13px]" style={{ color: "var(--dim)" }}>
            {d?.error || "دیتابیس ربات در دسترس نیست."}
          </p>
        </div>
      </div>
    );
  }

  const o = d.orders || {};
  const u = d.users || {};
  const s = d.subs || {};
  const maxDay = Math.max(...(d.daily || []).map((x) => x.sum), 1);
  // میانگین بدون روزهای صفر: روزهای بی‌فروش میانگین را مصنوعی
  // پایین می‌آورند و خط مرجع بی‌معنا می‌شود.
  const sold = (d.daily || []).filter((x) => x.sum > 0);
  const avgDay = sold.length
    ? sold.reduce((a, b) => a + b.sum, 0) / sold.length : 0;

  return (
    <div className="fx-anim">
      <SectionHead title="گزارش فروش"
        desc="عملکرد ربات در بازه‌ی انتخابی — چند نفر آمدند، چند نفر خریدند، چقدر فروش رفت."
        action={
          <div className="flex items-center gap-2 flex-wrap">
            <Segmented value={days} onChange={setDays}
              items={REPORT_RANGES.map(([v, l]) => [v, l])} />
            <button onClick={downloadPdf} disabled={busy}
              className="fx-btn px-3 py-2.5 text-[13px] flex items-center gap-1.5">
              <FileText size={13} /> گزارش PDF
            </button>
            <button onClick={download} disabled={busy}
              className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
              <Download size={13} /> خروجی اکسل
            </button>
          </div>
        } />

      <div className="fx-g4 grid grid-cols-4 gap-3 mb-4">
        <StatTile label="فروش دوره" value={faNum(o.revenue || 0)} unit="تومان"
          color="var(--ok)"
          hint={o.approved ? `${faNum(o.approved)} سفارش · میانگین ${faNum(o.avg)}` : "سفارشی نبوده"} />
        <StatTile label="کاربر جدید" value={faNum(u.newUsers || 0)} unit="نفر"
          hint={`از ${faNum(u.users || 0)} کاربر کل`} />
        <StatTile label="خریدار" value={faNum(d.buyerCount || 0)} unit="نفر"
          color="var(--accent-2)"
          hint={d.conversion !== null && d.conversion !== undefined
            ? `نرخ تبدیل ${faNum(d.conversion)}٪ از کاربران جدید`
            : "کاربر جدیدی نبوده"} />
        <StatTile label="اشتراک فعال" value={faNum(s.active || 0)}
          color={s.expiringSoon ? "var(--warn)" : "var(--text)"}
          hint={s.expiringSoon
            ? `${faNum(s.expiringSoon)} تا کمتر از ۳ روز اعتبار دارد`
            : `از ${faNum(s.total || 0)} اشتراک کل`} />
      </div>

      {(o.pending > 0 || o.rejected > 0) && (
        <div className="fx-card p-5 mb-4">
          <div className="flex gap-4 flex-wrap text-[13px]">
            {o.pending > 0 && (
              <span style={{ color: "var(--warn)" }}>
                ⏳ <b>{faNum(o.pending)}</b> رسید منتظر بررسی شماست
              </span>
            )}
            {o.rejected > 0 && (
              <span style={{ color: "var(--muted)" }}>
                {faNum(o.rejected)} سفارش در این دوره رد شده
              </span>
            )}
          </div>
        </div>
      )}

      {(d.daily || []).length > 1 && (
        <div className="fx-card p-5 mb-4">
          <div className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
            <TrendingUp size={15} style={{ color: "var(--accent-2)" }} /> فروش روزانه
          </div>
          <AreaChart
            data={d.daily.map((x) => x.sum)}
            color="var(--accent-2)"
            height={110}
            label={`${isoToJalaliLabel(d.daily[0].day)} تا ${isoToJalaliLabel(d.daily[d.daily.length - 1].day)}`}
            format={(v) => `${faNum(v)} تومان`} labels={d.daily.map((x) => x.day)} />
        </div>
      )}

      <div className="fx-card p-5">
        <div className="flex items-center justify-between gap-3 mb-1 flex-wrap">
          <div className="text-[14px] font-semibold text-white flex items-center gap-2">
            <Users size={15} style={{ color: "var(--accent-2)" }} /> بهترین خریداران
          </div>
          <span className="text-[13px]" style={{ color: "var(--muted)" }}>
            {faNum(u.withPhone || 0)} کاربر شماره تماس داده‌اند
          </span>
        </div>
        <p className="text-[13px] mb-3" style={{ color: "var(--muted)" }}>
          مرتب بر اساس مجموع خرید در همین دوره.
        </p>

        {!(d.buyers || []).length ? (
          <EmptyState icon={Users} text="در این بازه خریدی ثبت نشده" />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="fx-table">
              <thead>
                <tr><th>کاربر</th><th>شماره تماس</th><th>سفارش</th>
                  <th>مجموع خرید</th><th>آخرین خرید</th></tr>
              </thead>
              <tbody>
                {(d.buyers || []).map((b) => (
                  <tr key={b.tg_id}>
                    <td>
                      <span className="inline-flex items-center gap-2 align-middle">
                        <Avatar name={b.first_name || b.username} id={b.tg_id} size={24} />
                        <span>{esc0(b.first_name) || "—"}</span>
                      </span>
                      {b.username && (
                        <span dir="ltr" className="mr-2" style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                          @{b.username}
                        </span>
                      )}
                    </td>
                    <td dir="ltr" style={{ fontFamily: "var(--mono)", color: b.phone ? "var(--dim)" : "var(--muted)" }}>
                      {b.phone || "—"}
                    </td>
                    <td style={{ fontFamily: "var(--mono)" }}>{faNum(b.orders)}</td>
                    <td style={{ fontFamily: "var(--mono)", color: "var(--ok)" }}>
                      {faNum(b.spent)}
                    </td>
                    <td style={{ color: "var(--muted)" }}>{isoToJalaliLabel(b.lastBuy)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
