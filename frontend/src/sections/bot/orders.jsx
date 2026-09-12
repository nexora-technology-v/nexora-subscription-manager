/**
 * ربات: سفارش‌ها و بررسی رسید.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import {
  AlertTriangle, CheckCircle2, CreditCard, Loader2, RefreshCw, Search, X,
} from "lucide-react";
import { errText } from "../../lib/format";
import { API_URL } from "../../lib/constants";
import { Field, Msg, SectionHead, StatusPill, Tabs } from "../../ui/index";

export const REJECT_REASONS = [
  "مبلغ واریزی با مبلغ سفارش مطابقت ندارد.",
  "تصویر رسید خوانا نبود.",
  "این رسید قبلاً استفاده شده است.",
  "رسید معتبر تشخیص داده نشد.",
];

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
      const d = await fetch(`${API_URL}/api/admin/bot/orders?status=${f}`, { headers: { "X-Admin-Password": password } }).then(r => r.json());
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
      const d = await res.json();
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
      const d = await res.json();
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
      <Tabs items={FILTERS.map(f => ({ key: f.k, label: f.l }))} active={filter} onChange={setFilter} />

      {loading ? (
        <div className="flex justify-center py-14"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>
      ) : orders.length === 0 ? (
        <div className="fx-card p-10 text-center" style={{ borderStyle: "dashed" }}>
          <CreditCard size={26} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
          <div className="text-[14px]" style={{ color: "var(--muted)" }}>
            {filter === "awaiting" ? "رسیدی در انتظار تایید نیست" : "موردی یافت نشد"}
          </div>
        </div>
      ) : orders.map((o) => (
        <div key={o.id} className="fx-card p-4 mb-3">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            {o.receipt_type === "photo" && (
              <button onClick={() => setZoom(o.id)}
                className="shrink-0 rounded-xl overflow-hidden relative"
                style={{ width: 84, height: 108, border: "1px solid var(--border-2)", background: "var(--surface-3)" }}
                title="بزرگ‌نمایی">
                <img src={`${API_URL}/api/admin/bot/receipt/${o.id}?pw=${encodeURIComponent(password)}`}
                  alt="رسید" loading="lazy"
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                  onError={(e) => { e.currentTarget.style.display = "none"; }} />
                <span className="absolute bottom-1 left-1 right-1 py-0.5 rounded text-[10.5px] flex items-center justify-center gap-1"
                  style={{ background: "rgba(0,0,0,.68)", color: "#fff" }}>
                  <Search size={9} /> بزرگ‌نمایی
                </span>
              </button>
            )}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-[14px] font-semibold text-white">{o.first_name || "بدون نام"}</span>
                {o.username && <span className="text-[13px]" dir="ltr" style={{ color: "var(--muted)" }}>@{o.username}</span>}
                <StatusPill s={o.status} />
              </div>
              <div className="text-[13px] leading-relaxed" style={{ color: "var(--dim)" }}>
                مبلغ: <b style={{ color: "var(--text)" }}>{Number(o.amount || 0).toLocaleString("fa-IR")}</b> تومان
                {o.coins_used > 0 && <> · {o.coins_used} سکه ({o.discount_pct}٪ تخفیف)</>}
              </div>

              {o.receipt_type === "text" && o.receipt_text && (
                <div className="mt-2.5 rounded-xl p-3 text-[13px] leading-relaxed whitespace-pre-wrap"
                  dir="auto" style={{
                    background: "var(--surface-3)", border: "1px solid var(--border)",
                    color: "var(--dim)", fontFamily: "var(--mono)",
                    maxHeight: 130, overflowY: "auto",
                  }}>
                  {o.receipt_text}
                </div>
              )}
              <div className="text-[12px] mt-1.5" style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                #{o.id} · {o.created_at?.slice(0, 16)}
              </div>
            </div>

            {(o.status === "awaiting" || o.status === "review") && (
              <div className="flex gap-2 shrink-0">
                <button onClick={() => act(o.id, "approve")} disabled={busy === o.id}
                  className="px-3.5 py-2.5 rounded-[10px] text-[13px] font-semibold flex items-center gap-1.5"
                  style={{ background: "rgba(52,211,153,.14)", color: "var(--ok)", border: "1px solid rgba(52,211,153,.3)" }}>
                  {busy === o.id ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />} تایید
                </button>
                <button onClick={() => { setRejecting(o); setReason(""); }} disabled={busy === o.id}
                  className="fx-btn-g px-3.5 py-2.5 text-[13px]" style={{ color: "var(--danger)" }}>
                  رد با دلیل
                </button>
              </div>
            )}
          </div>
        </div>
      ))}

      {zoom && createPortal(
        <div onClick={() => setZoom(null)}
          className="fixed inset-0 z-[110] flex items-center justify-center p-6"
          style={{ background: "rgba(3,6,12,.93)", cursor: "zoom-out" }}>
          <img src={`${API_URL}/api/admin/bot/receipt/${zoom}?pw=${encodeURIComponent(password)}`} alt="رسید"
            style={{ maxWidth: "92vw", maxHeight: "88vh", borderRadius: 14, objectFit: "contain" }}
            onClick={(e) => e.stopPropagation()} />
          <button onClick={() => setZoom(null)}
            className="absolute top-5 left-5 fx-ico-btn" style={{ width: 38, height: 38 }}>
            <X size={18} />
          </button>
        </div>, document.body)}

      {rejecting && createPortal(
        <div className="nx-modal-wrap fx-fade"
          style={{ background: "rgba(3,6,12,.82)", backdropFilter: "blur(6px)" }}
          onClick={() => setRejecting(null)}>
          <div className="w-full max-w-md rounded-2xl fx-scale nx-modal flex flex-col"
            onClick={(e) => e.stopPropagation()}
            style={{ background: "var(--surface)", border: "1px solid rgba(248,113,113,.3)" }}>

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
                      ? { background: "rgba(248,113,113,.12)", border: "1px solid rgba(248,113,113,.35)", color: "var(--text)" }
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
