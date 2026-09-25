/**
 * ربات: سفارش‌ها و بررسی رسید.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import {
  AlertTriangle, CheckCircle2, Clock, CreditCard, Loader2, RefreshCw, Search, Wallet, X,
} from "lucide-react";
import { errText, faNum } from "../../lib/format";
import { API_URL } from "../../lib/constants";
import { Avatar, EmptyState, Field, Msg, PageSkeleton, SectionHead, StatTile, StatusPill, Tabs } from "../../ui/index";
import { isoToJalaliLabel, isoToJalaliStamp } from "../../ui/jalali";

export const REJECT_REASONS = [
  "مبلغ واریزی با مبلغ سفارش مطابقت ندارد.",
  "تصویر رسید خوانا نبود.",
  "این رسید قبلاً استفاده شده است.",
  "رسید معتبر تشخیص داده نشد.",
];

/* رسید با هدر، نه با رمز در آدرس.
   پیش‌تر `<img src=".../receipt/12?pw=رمز">` بود: رمزِ مدیر در لاگِ
   nginx، تاریخچه‌ی مرورگر و Referer می‌نشست — برای هر رسیدِ صفحه. حالا
   تصویر با fetch و هدر گرفته و از blob نشان داده می‌شود؛ بکند دیگر
   `?pw=` را نمی‌پذیرد. شکست هم دیده می‌شود، نه اینکه تصویر بی‌صدا
   پنهان شود. */
export function ReceiptImg({ id, password, style, alt = "رسید" }) {
  const [src, setSrc] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    let url = null;
    let alive = true;
    setSrc(null); setErr(null);
    fetch(`${API_URL}/api/admin/bot/receipt/${id}`, { headers: { "X-Admin-Password": password } })
      .then(async (r) => {
        if (!r.ok) {
          const j = await r.json().catch(() => ({}));
          throw new Error(errText(j.detail, "رسید باز نشد"));
        }
        return r.blob();
      })
      .then((b) => { if (!alive) return; url = URL.createObjectURL(b); setSrc(url); })
      .catch((e) => { if (alive) setErr(e.message || "رسید باز نشد"); });
    return () => { alive = false; if (url) URL.revokeObjectURL(url); };
  }, [id, password]);
  if (err) {
    return (
      <span className="grid place-items-center text-center text-[10.5px] p-1.5 leading-snug"
        style={{ ...style, color: "var(--danger)" }} title={err}>
        <AlertTriangle size={14} />{err}
      </span>
    );
  }
  if (!src) return <span className="fx-sk block" style={style} />;
  return <img src={src} alt={alt} style={style} />;
}

const KIND_LABEL = { new: "خرید", renew: "تمدید", topup: "شارژ کیف پول" };

export function BotOrdersSection({ password }) {
  const [rejecting, setRejecting] = useState(null);
  const [reason, setReason] = useState("");
  const [orders, setOrders] = useState([]);
  const [filter, setFilter] = useState("awaiting");
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(null);
  const [zoom, setZoom] = useState(null);

  const load = async (f = filter) => {
    setLoading(true);
    try {
      const r = await fetch(`${API_URL}/api/admin/bot/orders?status=${f}`, { headers: { "X-Admin-Password": password } });
      const d = await r.json().catch(() => ({}));
      // خطا پیش‌تر به «رسیدی در انتظار تایید نیست» ختم می‌شد — صفِ
      // خالی و صفِ خوانده‌نشده یک شکل بودند
      if (!r.ok) { setMsg({ t: "err", m: errText(d.detail, "خواندنِ سفارش‌ها ناموفق بود") }); return; }
      if (d.error) setMsg({ t: "err", m: `خواندنِ سفارش‌ها ناقص ماند: ${d.error}` });
      else if (d.dbReady === false) setMsg({ t: "err", m: "دیتابیسِ ربات پیدا نشد — ربات نصب و اجرا شده؟" });
      setOrders(d.orders || []);
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(filter); }, [password, filter]);
  useEffect(() => { if (msg) { const x = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(x); } }, [msg]);

  const doReject = async () => {
    if (!reason.trim()) return;
    const id = rejecting.id;
    setRejecting(null);
    setBusy(id);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/orders/${id}/reject-with-reason`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ reason }),
      });
      const d = await res.json().catch(() => ({}));
      if (res.ok) {
        setMsg({ t: "ok", m: "سفارش رد شد — دلیل برای مشتری فرستاده می‌شود" });
        load(filter);
      } else setMsg({ t: "err", m: errText(d.detail, "عملیات ناموفق") });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(null); }
  };

  const act = async (id, action) => {
    setBusy(id);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/orders/${id}/${action}`, {
        method: "POST", headers: { "X-Admin-Password": password },
      });
      const d = await res.json().catch(() => ({}));
      if (res.ok) {
        setMsg({ t: "ok", m: action === "approve" ? "تایید شد — ربات کانفیگ را می‌سازد" : "سفارش رد شد" });
        load(filter);
      } else setMsg({ t: "err", m: errText(d.detail, "عملیات ناموفق") });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(null); }
  };

  const FILTERS = [
    { k: "awaiting", l: "در انتظار تایید" },
    { k: "approved", l: "تاییدشده" },
    { k: "rejected", l: "ردشده" },
    { k: "all", l: "همه" },
  ];

  // از همان آرایه‌ای که در دست است — نه یک درخواست تازه
  const sumAmount = orders.reduce((a, o) => a + (Number(o.amount) || 0), 0);
  const waiting = orders.filter((o) => (o.status || "") === "pending"
                                    || (o.status || "") === "awaiting").length;
  const newest = orders.reduce((m, o) =>
    (o.created_at && (!m || o.created_at > m)) ? o.created_at : m, "");

  return (
    <div className="fx-anim">
      <SectionHead title="سفارش‌ها و رسیدها"
        desc="رسیدهای پرداخت کارت‌به‌کارت. تایید هم از اینجا و هم از گروه تلگرام ممکن است."
        action={
          <button onClick={() => load(filter)} className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
            <RefreshCw size={13} /> تازه‌سازی
          </button>
        } />

      <Msg msg={msg} />

      {/* خلاصه‌ی همین فهرست، بالای خودش.
          قبلاً برای دانستنِ «چند تا در انتظار است و چقدر می‌شود»
          باید ردیف‌ها شمرده می‌شدند. این‌ها از همان داده‌ای
          می‌آیند که صفحه از قبل گرفته — هیچ درخواست تازه‌ای. */}
      {!loading && orders.length > 0 && (
        <div className="fx-g4 grid grid-cols-3 gap-3">
          <StatTile label="سفارش در این نما" icon={CreditCard} tone="var(--accent-2)"
            value={faNum(orders.length)}
            hint={FILTERS.find((f) => f.k === filter)?.l} />
          <StatTile label="ارزش کل" icon={Wallet} tone="var(--ok)"
            value={faNum(sumAmount)} unit="تومان" color="var(--ok)"
            hint={orders.length ? `میانگین ${faNum(Math.round(sumAmount / orders.length))}` : ""} />
          <StatTile label="تازه‌ترین" icon={Clock} tone="var(--warn)"
            value={newest ? isoToJalaliLabel(newest) : "—"}
            hint={waiting ? `${faNum(waiting)} مورد در انتظار تایید` : "چیزی معطل نمانده"} />
        </div>
      )}

      <Tabs items={FILTERS.map(f => ({ key: f.k, label: f.l }))} active={filter} onChange={setFilter} />

      {loading ? (
        <PageSkeleton />
      ) : orders.length === 0 ? (
        <EmptyState icon={CreditCard}
          text={filter === "awaiting" ? "رسیدی در انتظار تایید نیست" : "موردی یافت نشد"}
          hint={filter === "awaiting"
            ? "هر رسیدی که مشتری بفرستد همین‌جا می‌آید — و از گروه تلگرام هم می‌شود تاییدش کرد."
            : "فیلتر بالا را عوض کنید تا سفارش‌های دیگر را ببینید."} />
      ) : (
        /* شبکه، نه ستونِ تمام‌عرض: هر سفارش یک کارتِ ۱۱۴۰ پیکسلی بود با
           نام در یک لبه و دکمه‌ی تایید در لبه‌ی دیگر — چشم برای هر رسید
           عرضِ کلِ صفحه را طی می‌کرد. */
        <div className="fx-orders">{orders.map((o) => (
        <div key={o.id} className={`fx-card fx-order st-${o.status || "none"}`}>
          <div className="flex items-start justify-between gap-3">
            {o.receipt_type === "photo" && (
              <button onClick={() => setZoom(o.id)}
                className="shrink-0 rounded-xl overflow-hidden relative"
                style={{ width: 84, height: 108, border: "1px solid var(--border-2)", background: "var(--surface-3)" }}
                title="بزرگ‌نمایی">
                <ReceiptImg id={o.id} password={password}
                  style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                <span className="absolute bottom-1 left-1 right-1 py-0.5 rounded text-[10.5px] flex items-center justify-center gap-1"
                  style={{ background: "var(--scrim-3)", color: "#fff" }}>
                  <Search size={9} /> بزرگ‌نمایی
                </span>
              </button>
            )}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                <Avatar name={o.first_name || o.username} id={o.tg_id} size={26} />
                <span className="text-[14px] font-semibold text-white">{o.first_name || "بدون نام"}</span>
                {o.username && <span className="text-[13px]" dir="ltr" style={{ color: "var(--muted)" }}>@{o.username}</span>}
                <StatusPill s={o.status} />
              </div>
              <div className="flex items-center gap-1.5 flex-wrap mb-1">
                <span className="fx-pill" style={{ background: "var(--accent-soft)", color: "var(--accent-2)" }}>
                  {KIND_LABEL[o.kind] || "سفارش"}
                </span>
                {o.plan_name && <span className="text-[13px] font-semibold text-white">{o.plan_name}</span>}
                {o.paid_from === "wallet" && (
                  <span className="fx-pill" style={{ background: "var(--hair-2)", color: "var(--muted)" }}>از کیف پول</span>
                )}
              </div>
              <div className="text-[13px] leading-relaxed" style={{ color: "var(--dim)" }}>
                مبلغ: <b style={{ color: "var(--text)" }}>{faNum(Number(o.amount || 0))}</b> تومان
                {o.coins_used > 0 && <> · {faNum(o.coins_used)} سکه ({faNum(o.discount_pct || 0)}٪ تخفیف)</>}
              </div>

              {o.receipt_type === "text" && o.receipt_text && (
                <div className="mt-2.5 rounded-xl p-3 text-[13px] leading-relaxed whitespace-pre-wrap"
                  dir="auto" style={{
                    background: "var(--surface-3)", border: "1px solid var(--border)",
                    color: "var(--dim)",
                    maxHeight: 130, overflowY: "auto",
                  }}>
                  {o.receipt_text}
                </div>
              )}
              <div className="text-[12px] mt-1.5" style={{ color: "var(--muted)" }}>
                #{faNum(o.id)} · {isoToJalaliStamp(o.created_at)}
              </div>
            </div>

          </div>
            {(o.status === "awaiting" || o.status === "review") && (
              <div className="fx-order-act">
                <button onClick={() => act(o.id, "approve")} disabled={busy === o.id}
                  className="px-3.5 py-2.5 rounded-[10px] text-[13px] font-semibold flex items-center gap-1.5"
                  style={{ background: "var(--ok-soft)", color: "var(--ok)", border: "1px solid var(--ok-line)" }}>
                  {busy === o.id ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />} تایید
                </button>
                <button onClick={() => { setRejecting(o); setReason(""); }} disabled={busy === o.id}
                  className="fx-btn-g px-3.5 py-2.5 text-[13px]" style={{ color: "var(--danger)" }}>
                  رد با دلیل
                </button>
              </div>
            )}
        </div>
        ))}</div>
      )}

      {zoom && createPortal(
        <div onClick={() => setZoom(null)}
          className="fixed inset-0 z-[110] flex items-center justify-center p-6"
          style={{ background: "var(--veil)", cursor: "zoom-out" }}>
          <span onClick={(e) => e.stopPropagation()}>
            <ReceiptImg id={zoom} password={password}
              style={{ maxWidth: "92vw", maxHeight: "88vh", minWidth: 120, minHeight: 120, borderRadius: 14, objectFit: "contain" }} />
          </span>
          <button title="بستن" onClick={() => setZoom(null)}
            className="absolute top-5 left-5 fx-ico-btn" style={{ width: 38, height: 38 }}>
            <X size={18} />
          </button>
        </div>, document.body)}

      {rejecting && createPortal(
        <div className="nx-modal-wrap fx-fade"
          style={{ background: "var(--veil)", backdropFilter: "blur(6px)" }}
          onClick={() => setRejecting(null)}>
          <div className="w-full max-w-md rounded-2xl fx-scale nx-modal flex flex-col"
            onClick={(e) => e.stopPropagation()}
            style={{ background: "var(--surface)", border: "1px solid var(--danger-line)" }}>

            <div className="p-5 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
              <div className="flex items-center gap-2">
                <AlertTriangle size={16} style={{ color: "var(--danger)" }} />
                <span className="text-[16px] font-bold text-white">رد سفارش #{rejecting.id}</span>
              </div>
              <p className="text-[13px] mt-2 leading-relaxed" style={{ color: "var(--muted)" }}>
                دلیل برای مشتری فرستاده می‌شود و سکه‌های خرج‌شده خودکار برمی‌گردند.
              </p>
            </div>

            <div className="p-5 overflow-y-auto flex-1" style={{ minHeight: 0 }}>
              <div className="text-[13px] mb-2" style={{ color: "var(--dim)" }}>دلیل‌های آماده:</div>
              <div className="flex flex-col gap-2 mb-4">
                {REJECT_REASONS.map((r, ri) => (
                  <button key={ri} onClick={() => setReason(r)}
                    className="text-right p-2.5 rounded-xl text-[13px] transition-all"
                    style={reason === r
                      ? { background: "var(--danger-soft)", border: "1px solid var(--danger-line)", color: "var(--text)" }
                      : { background: "var(--surface-3)", border: "1px solid var(--border)", color: "var(--dim)" }}>
                    {r}
                  </button>
                ))}
              </div>

              <Field label="یا دلیل خودتان را بنویسید">
                <textarea className="fx-input" rows={3} value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="مثلاً: مبلغ واریزی ۵۰ هزار تومان کمتر است" />
              </Field>
            </div>

            <div className="p-5 shrink-0 flex gap-2" style={{ borderTop: "1px solid var(--border)" }}>
              <button onClick={() => setRejecting(null)} className="fx-btn-g flex-1 py-3 text-[14px]">
                انصراف
              </button>
              <button onClick={doReject} disabled={!reason.trim()}
                className="flex-1 py-3 rounded-[11px] text-[14px] font-bold"
                style={{ background: reason.trim() ? "var(--danger)" : "var(--surface-2)",
                         color: reason.trim() ? "#fff" : "var(--muted)" }}>
                رد کن و اطلاع بده
              </button>
            </div>
          </div>
        </div>, document.body)}
    </div>
  );
}
