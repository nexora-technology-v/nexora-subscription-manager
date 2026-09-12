/**
 * ربات: همکاران فروش.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
import React, { useState, useEffect } from "react";
import {
  AlertTriangle, CheckCircle2, Coins, DollarSign, Eye, EyeOff, Loader2, Plus as PlusIcon, Sliders, Trash2,
} from "lucide-react";
import { API_URL } from "../../lib/constants";
import { faNum } from "../../lib/format";
import { Field, InfoBox, Modal, Msg, SectionHead } from "../../ui/index";

export function BotAffiliates({ password }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [payFor, setPayFor] = useState(null);
  const [edit, setEdit] = useState(null);
  const [msg, setMsg] = useState(null);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/bot/affiliates`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setData(d);
    } catch {
      setData({ ready: false, error: "اتصال برقرار نشد", affiliates: [] });
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [password]);
  useEffect(() => {
    if (msg) { const t = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(t); }
  }, [msg]);

  const remove = async (id) => {
    await fetch(`${API_URL}/api/admin/bot/affiliate/${id}`, {
      method: "DELETE", headers: { "X-Admin-Password": password } });
    setMsg({ t: "ok", m: "همکار حذف شد — کاربرانش حفظ شدند" });
    load();
  };

  const toggle = async (a) => {
    await fetch(`${API_URL}/api/admin/bot/affiliate/${a.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-Admin-Password": password },
      body: JSON.stringify({ active: !a.active }),
    });
    load();
  };

  if (loading) {
    return <div className="flex justify-center py-16">
      <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;
  }

  if (!data?.ready) {
    return (
      <div className="fx-anim">
        <SectionHead title="همکاری در فروش" desc="" />
        <div className="fx-card p-8 text-center" style={{ borderStyle: "dashed" }}>
          <AlertTriangle size={24} style={{ color: "var(--warn)" }} className="mx-auto mb-3" />
          <div className="text-[14px]" style={{ color: "var(--muted)" }}>
            {data?.error || "دیتابیس ربات در دسترس نیست"}
          </div>
        </div>
      </div>
    );
  }

  const list = data.affiliates || [];

  return (
    <div className="fx-anim">
      <SectionHead title="همکاری در فروش"
        desc="کسانی که برای شما می‌فروشند و درصد می‌گیرند."
        action={
          <button onClick={() => setAdding(true)}
            className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
            <PlusIcon size={14} /> همکار جدید
          </button>
        } />

      {msg && <Msg msg={msg} />}

      {list.length > 0 && (
        <div className="fx-card p-5 mb-4">
          <div className="flex justify-between items-baseline flex-wrap gap-2">
            <span className="text-[14px]" style={{ color: "var(--dim)" }}>
              مجموع بدهی به همکاران
            </span>
            <span className="text-[21px] font-extrabold"
              style={{ color: data.totalOwed > 0 ? "var(--warn)" : "var(--ok)",
                       fontFamily: "var(--mono)" }}>
              {faNum(data.totalOwed)} <span className="text-[13px]">تومان</span>
            </span>
          </div>
        </div>
      )}

      {list.length === 0 ? (
        <div className="fx-card p-10 text-center" style={{ borderStyle: "dashed" }}>
          <Coins size={26} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
          <div className="text-[14px] font-semibold text-white mb-2">
            هنوز همکاری اضافه نشده
          </div>
          <p className="text-[13px] max-w-md mx-auto leading-relaxed"
            style={{ color: "var(--muted)" }}>
            هر همکار یک لینک اختصاصی می‌گیرد. هر کسی با آن لینک وارد ربات شود،
            از تمام خریدهایش — نه فقط خرید اول — به آن همکار پورسانت می‌رسد.
          </p>
        </div>
      ) : list.map((a) => (
        <div key={a.id} className="fx-card p-5 mb-3">
          <div className="flex items-start justify-between gap-3 flex-wrap mb-4">
            <div className="min-w-0">
              <div className="text-[14px] font-bold text-white flex items-center gap-2 flex-wrap">
                {a.name}
                <span className="text-[12px] px-2 py-0.5 rounded-lg"
                  style={{ background: "var(--accent-soft)", color: "var(--accent-2)",
                           fontFamily: "var(--mono)" }}>
                  {faNum(a.percent)}٪
                </span>
                {!a.active && (
                  <span className="text-[12px] px-2 py-0.5 rounded-lg"
                    style={{ background: "rgba(255,255,255,.05)", color: "var(--muted)" }}>
                    غیرفعال
                  </span>
                )}
              </div>
              <div className="text-[12px] mt-1.5" dir="ltr"
                style={{ color: "var(--muted)", fontFamily: "var(--mono)",
                         textAlign: "right" }}>
                aff_{a.code}
                {a.tg_id ? ` · ${a.tg_id}` : " · بدون تلگرام"}
              </div>
              {a.note && (
                <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
                  {a.note}
                </div>
              )}
            </div>
            <div className="flex gap-2 shrink-0">
              <button onClick={() => setEdit(a)} className="fx-ico-btn" title="ویرایش">
                <Sliders size={13} />
              </button>
              <button onClick={() => toggle(a)} className="fx-ico-btn"
                title={a.active ? "غیرفعال کردن" : "فعال کردن"}>
                {a.active ? <Eye size={13} /> : <EyeOff size={13} />}
              </button>
              <button onClick={() => remove(a.id)} className="fx-ico-btn" title="حذف">
                <Trash2 size={13} />
              </button>
            </div>
          </div>

          <div className="fx-g4 grid grid-cols-4 gap-3">
            {[["کاربر", a.users, "var(--dim)"],
              ["خرید", a.orders, "var(--dim)"],
              ["فروش", a.sales, "var(--accent-2)"],
              ["پورسانت", a.earned, "var(--ok)"]].map(([l, v, col], i) => (
              <div key={i} className="p-3 rounded-xl text-center"
                style={{ background: "var(--surface-3)" }}>
                <div className="text-[16px] font-bold" style={{ color: col,
                     fontFamily: "var(--mono)" }}>
                  {faNum(v)}
                </div>
                <div className="text-[11.5px] mt-1" style={{ color: "var(--muted)" }}>{l}</div>
              </div>
            ))}
          </div>

          <div className="flex justify-between items-center mt-4 pt-3 flex-wrap gap-3"
            style={{ borderTop: "1px solid var(--border)" }}>
            <div className="text-[13px]" style={{ color: "var(--muted)" }}>
              پرداخت‌شده {faNum(a.payouts)} · {" "}
              <b style={{ color: a.balance > 0 ? "var(--warn)" : "var(--ok)" }}>
                مانده {faNum(a.balance)}
              </b>
            </div>
            {a.balance > 0 && (
              <button onClick={() => setPayFor(a)}
                className="fx-btn px-3 py-2 text-[13px] flex items-center gap-1.5">
                <DollarSign size={12} /> ثبت پرداخت
              </button>
            )}
          </div>
        </div>
      ))}

      {(adding || edit) && (
        <AffiliateForm password={password} affiliate={edit}
          onClose={() => { setAdding(false); setEdit(null); }}
          onDone={(m) => { setAdding(false); setEdit(null); load(); setMsg({ t: "ok", m }); }} />
      )}

      {payFor && (
        <AffiliatePayoutModal affiliate={payFor} password={password}
          onClose={() => setPayFor(null)}
          onDone={() => { setPayFor(null); load(); setMsg({ t: "ok", m: "پرداخت ثبت شد" }); }} />
      )}
    </div>
  );
}

/** افزودن یا ویرایش همکار */
export function AffiliateForm({ password, affiliate, onClose, onDone }) {
  const editing = !!affiliate;
  const [f, setF] = useState({
    name: affiliate?.name || "",
    percent: affiliate?.percent || 10,
    code: affiliate?.code || "",
    tg_id: affiliate?.tg_id || "",
    note: affiliate?.note || "",
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async () => {
    setBusy(true); setErr("");
    try {
      const url = editing
        ? `${API_URL}/api/admin/bot/affiliate/${affiliate.id}`
        : `${API_URL}/api/admin/bot/affiliate`;
      const res = await fetch(url, {
        method: editing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify(f),
      });
      const d = await res.json();
      if (res.ok) onDone(editing ? "ذخیره شد" : `همکار اضافه شد — کد ${d.code}`);
      else setErr(d.detail || "ناموفق");
    } catch { setErr("اتصال برقرار نشد"); }
    finally { setBusy(false); }
  };

  return (
    <Modal title={editing ? "ویرایش همکار" : "همکار جدید"} onClose={onClose} width="480px"
      footer={
        <button onClick={submit} disabled={busy || !f.name.trim()}
          className="fx-btn w-full py-3 text-[14px] flex items-center justify-center gap-2"
          style={!f.name.trim() ? { opacity: .45, cursor: "not-allowed" } : {}}>
          {busy ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
          {editing ? "ذخیره" : "افزودن"}
        </button>
      }>
      <Field label="نام همکار">
        <input className="fx-input" value={f.name}
          onChange={(e) => setF({ ...f, name: e.target.value })}
          placeholder="نام یا عنوان" />
      </Field>

      <Field label="درصد پورسانت" hint="از هر خریدی که مشتریانش می‌کنند">
        <div className="flex items-center gap-2">
          <input className="fx-input" type="text" inputMode="decimal" dir="ltr"
            value={f.percent}
            onChange={(e) => setF({ ...f,
              percent: e.target.value.replace(/[^0-9.]/g, "").slice(0, 5) })}
            style={{ fontFamily: "var(--mono)" }} />
          <div className="flex gap-1.5 shrink-0">
            {[5, 10, 15, 20].map((p) => (
              <button key={p} onClick={() => setF({ ...f, percent: p })}
                className="px-2.5 py-2 rounded-lg text-[12px]"
                style={{
                  background: +f.percent === p ? "var(--accent-soft)" : "transparent",
                  border: `1px solid ${+f.percent === p ? "rgba(43,127,214,.4)" : "var(--border)"}`,
                  color: +f.percent === p ? "var(--accent-2)" : "var(--muted)",
                  fontFamily: "var(--mono)",
                }}>{faNum(p)}٪</button>
            ))}
          </div>
        </div>
      </Field>

      <Field label="آیدی عددی تلگرام (اختیاری)"
        hint="اگر بدهید، پنل همکاری در ربات برایش باز می‌شود و از هر فروش خبردار می‌شود">
        <input className="fx-input" type="text" inputMode="numeric" dir="ltr"
          value={f.tg_id}
          onChange={(e) => setF({ ...f, tg_id: e.target.value.replace(/[^0-9]/g, "") })}
          placeholder="123456789"
          style={{ fontFamily: "var(--mono)" }} />
      </Field>

      {!editing && (
        <Field label="کد لینک (اختیاری)" hint="خالی بگذارید تا خودکار ساخته شود">
          <input className="fx-input" dir="ltr" value={f.code}
            onChange={(e) => setF({ ...f, code: e.target.value.replace(/[^A-Za-z0-9]/g, "") })}
            placeholder="yaser"
            style={{ fontFamily: "var(--mono)" }} />
        </Field>
      )}

      <Field label="یادداشت (اختیاری)">
        <input className="fx-input" value={f.note}
          onChange={(e) => setF({ ...f, note: e.target.value })}
          placeholder="توافق یا شماره تماس" />
      </Field>

      {err && (
        <div className="text-[13px] p-3 rounded-xl mt-3"
          style={{ background: "rgba(248,113,113,.1)", color: "var(--danger)" }}>{err}</div>
      )}
    </Modal>
  );
}

/** ثبت پرداخت به همکار */
export function AffiliatePayoutModal({ affiliate, password, onClose, onDone }) {
  const [amount, setAmount] = useState(String(affiliate.balance || ""));
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      await fetch(`${API_URL}/api/admin/bot/affiliate/${affiliate.id}/payout`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ amount: +amount, note }),
      });
      onDone();
    } finally { setBusy(false); }
  };

  return (
    <Modal title={`پرداخت به ${affiliate.name}`} onClose={onClose} width="420px"
      footer={
        <button onClick={submit} disabled={busy || !(+amount > 0)}
          className="fx-btn w-full py-3 text-[14px] flex items-center justify-center gap-2"
          style={!(+amount > 0) ? { opacity: .45, cursor: "not-allowed" } : {}}>
          {busy ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
          ثبت پرداخت
        </button>
      }>
      <div className="p-3.5 rounded-xl mb-4" style={{ background: "var(--surface-3)" }}>
        <div className="flex justify-between text-[13px]">
          <span style={{ color: "var(--muted)" }}>مانده‌ی فعلی</span>
          <span style={{ color: "var(--warn)", fontFamily: "var(--mono)" }}>
            {faNum(affiliate.balance)} تومان
          </span>
        </div>
      </div>

      <Field label="مبلغ پرداختی (تومان)">
        <input className="fx-input" type="text" inputMode="numeric" dir="ltr"
          value={amount}
          onChange={(e) => setAmount(e.target.value.replace(/[^0-9]/g, ""))}
          style={{ fontFamily: "var(--mono)" }} />
      </Field>

      <Field label="یادداشت (اختیاری)">
        <input className="fx-input" value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="شماره کارت یا تاریخ واریز" />
      </Field>

      <InfoBox>
        پرداخت بیرون از ربات انجام می‌شود؛ این فقط ثبت می‌کند تا مانده درست بماند.
        پورسانت‌های قدیمی‌تر تا سقف این مبلغ، پرداخت‌شده علامت می‌خورند.
      </InfoBox>
    </Modal>
  );
}

/* ═══════════════════ تانل ═══════════════════ */
