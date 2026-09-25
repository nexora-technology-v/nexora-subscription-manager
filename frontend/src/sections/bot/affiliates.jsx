/**
 * ربات: همکاران فروش.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
import React, { useState, useEffect } from "react";
import {
  AlertTriangle, Check, CheckCircle2, Coins, DollarSign, Eye, EyeOff, Key, Loader2, Plus as PlusIcon, Sliders, Trash2, Users, Wallet,
} from "lucide-react";
import { API_URL } from "../../lib/constants";
import { errText, faNum } from "../../lib/format";
import { ConfirmModal, EmptyState, Field, InfoBox, Modal, Msg, PageSkeleton, SectionHead, StatTile } from "../../ui/index";

export function BotAffiliates({ password }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [payFor, setPayFor] = useState(null);
  const [pwFor, setPwFor] = useState(null);
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

  /* پیش‌تر «همکار حذف شد» بی‌توجه به پاسخ نشان داده می‌شد، و روشن/خاموش
     پاسخ را نمی‌خواند — شکست‌ها شبیهِ موفقیت بودند. حذف هم بی‌پرسش بود. */
  const [delFor, setDelFor] = useState(null);
  const remove = async (a) => {
    setDelFor(null);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/affiliate/${a.id}`, {
        method: "DELETE", headers: { "X-Admin-Password": password } });
      const j = await res.json().catch(() => ({}));
      setMsg(res.ok ? { t: "ok", m: "همکار حذف شد — کاربرانش حفظ شدند" }
        : { t: "err", m: errText(j.detail, "حذف نشد") });
      if (res.ok) load();
    } catch { setMsg({ t: "err", m: "حذف نشد — اتصال برقرار نشد" }); }
  };

  const toggle = async (a) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/affiliate/${a.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ active: !a.active }),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) setMsg({ t: "err", m: errText(j.detail, "تغییرِ وضعیت ثبت نشد") });
      load();
    } catch { setMsg({ t: "err", m: "تغییرِ وضعیت ثبت نشد — اتصال برقرار نشد" }); }
  };

  if (loading) {
    return <PageSkeleton />;
  }

  if (!data?.ready) {
    return (
      <div className="fx-anim">
        <SectionHead title="همکاری در فروش" desc="" />
        <EmptyState icon={AlertTriangle} tone="var(--warn)"
          text="دیتابیس ربات در دسترس نیست"
          hint={data?.error || "همکاران فروش از همان دیتابیس خوانده می‌شوند؛ بقیه‌ی پنل سالم است."} />
      </div>
    );
  }

  const list = data.affiliates || [];
  // فقط همکارهای خودِ مالک — مالِ نماینده‌ها هزینه‌ی خودشان است (resellerOwed)
  const paidTotal = list.filter((a) => a.isOwn !== false).reduce((x, a) => x + (Number(a.payouts) || 0), 0);

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
        <>
        {/* «پرداخت‌شده» از `payouts` هر همکار جمع می‌شود. پیش‌تر از
            `totalPaid` خوانده می‌شد که بکند هرگز نفرستاد (فقط هارنسِ قدیم
            داشتش)، پس روی سرور همیشه صفر بود — حتی بعد از تسویه. */}
        <div className="fx-g3 grid grid-cols-3 gap-3">
          <StatTile label="بدهی به همکاران" icon={Wallet}
            tone={data.totalOwed > 0 ? "var(--warn)" : "var(--ok)"}
            value={faNum(data.totalOwed)} unit="تومان"
            color={data.totalOwed > 0 ? "var(--warn)" : "var(--ok)"}
            hint={data.totalOwed > 0 ? "هنوز پرداخت نشده" : "همه تسویه‌اند"} />
          <StatTile label="همکار فروش" icon={Users} tone="var(--accent-2)"
            value={faNum(list.length)}
            hint={`${faNum(list.filter((a) => (a.sales || a.orders || 0) > 0).length)} نفر فروش داشته‌اند`} />
          <StatTile label="پرداخت‌شده تا امروز" icon={Check} tone="var(--ok)"
            value={faNum(paidTotal)} unit="تومان" color="var(--ok)"
            hint={data.resellerOwed > 0
                  ? `${faNum(data.resellerOwed)} بدهیِ همکارهای نماینده‌ها`
                  : "پورسانتِ پرداخت‌شده"} />
        </div>

        {data.resellerOwed > 0 && <div className="fx-card p-5 mb-4">

          {/* بدهیِ همکارهای نماینده‌ها جداست و در این عدد نمی‌آید —
              هزینه‌ی همان نماینده است، نه شما. قبلاً با هم جمع
              می‌شدند و «مجموع بدهی» بزرگ‌تر از واقعیت بود. */}
          {data.resellerOwed > 0 && (
            <div className="flex justify-between items-baseline flex-wrap gap-2">
              <span className="text-[12.5px]" style={{ color: "var(--muted)" }}>
                بدهی همکاران نماینده‌ها <span style={{ opacity: .75 }}>
                  (هزینه‌ی خودشان، نه شما)</span>
              </span>
              <span className="text-[14px] font-bold"
                style={{ color: "var(--dim)", fontFamily: "var(--mono)" }}>
                {faNum(data.resellerOwed)} <span className="text-[12px] fx-fa-sub">تومان</span>
              </span>
            </div>
          )}
        </div>}
        </>
      )}

      {delFor && (
        <ConfirmModal title={`حذفِ «${delFor.name}»`} confirmLabel="حذف همکار"
          desc={`کد ${delFor.code} دیگر کار نمی‌کند و پورسانتِ خریدهای بعدیِ کاربرانش به کسی نمی‌رسد. کاربران و سابقه‌ی پرداخت‌ها حفظ می‌شوند.`}
          onCancel={() => setDelFor(null)} onConfirm={() => remove(delFor)} />
      )}

      {list.length === 0 ? (
        <EmptyState icon={Coins} text="هنوز همکاری اضافه نشده"
          hint="هر همکار یک لینک اختصاصی می‌گیرد. هر کسی با آن لینک وارد ربات شود، از تمام خریدهایش — نه فقط خرید اول — به آن همکار پورسانت می‌رسد." />
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
                    style={{ background: "var(--hair-2)", color: "var(--muted)" }}>
                    غیرفعال
                  </span>
                )}
              </div>
              {/* «بدون تلگرام» از خطِ ltr/مونو بیرون کشیده شد: در آن
                  جهت، فارسی جابه‌جا نمایش داده می‌شود و مونو هم گلیف
                  فارسی ندارد. کد و شناسه‌ی تلگرام — که لاتین‌اند — همان
                  ltr و مونو را نگه می‌دارند. */}
              <div className="text-[12px] mt-1.5"
                style={{ color: "var(--muted)", textAlign: "right" }}>
                <bdi style={{ fontFamily: "var(--mono)" }}>
                  aff_{a.code}{a.tg_id ? ` · ${a.tg_id}` : ""}
                </bdi>
                {!a.tg_id && " · بدون تلگرام"}
              </div>
              {a.note && (
                <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
                  {a.note}
                </div>
              )}
              {/* بدون این، همکارِ نماینده از همکارِ خودتان قابل
                  تشخیص نبود و «مانده»اش مثل بدهیِ خودتان خوانده
                  می‌شد. */}
              {a.isOwn === false && (
                <div className="text-[11.5px] mt-1.5 inline-block px-2 py-0.5
                                rounded-md"
                  style={{ color: "var(--dim)", background: "var(--surface-3)" }}>
                  همکارِ نماینده{a.tenantName ? ` · ${a.tenantName}` : ""}
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
              <button onClick={() => setDelFor(a)} className="fx-ico-btn fx-ico-danger" title="حذف" aria-label="حذف همکار">
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
            <div className="flex items-center gap-2">
              {/* رمزِ ورودِ همکار. بدون این، همکار برای دیدنِ طلبش
                  باید هر بار بپرسد — و پنلی که ساخته شده به آن
                  نمی‌رسد. */}
              <button onClick={() => setPwFor(a)}
                className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5"
                title="رمز ورود همکار به پنل خودش">
                <Key size={12} /> رمز ورود
              </button>
              {a.balance > 0 && (
                <button onClick={() => setPayFor(a)}
                  className="fx-btn px-3 py-2 text-[13px] flex items-center gap-1.5">
                  <DollarSign size={12} /> ثبت پرداخت
                </button>
              )}
            </div>
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

      {pwFor && (
        <AffiliatePasswordModal affiliate={pwFor} password={password}
          onClose={() => setPwFor(null)}
          onDone={(m) => { setPwFor(null); load(); setMsg({ t: "ok", m }); }} />
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
      else setErr(errText(d.detail, "ناموفق"));
    } catch { setErr("اتصال برقرار نشد"); }
    finally { setBusy(false); }
  };

  return (
    <Modal title={editing ? "ویرایش همکار" : "همکار جدید"} onClose={onClose} width="480px"
      footer={
        <button title="ثبت" onClick={submit} disabled={busy || !f.name.trim()}
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
                  border: `1px solid ${+f.percent === p ? "var(--accent-edge)" : "var(--border)"}`,
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
          style={{ background: "var(--danger-soft)", color: "var(--danger)" }}>{err}</div>
      )}
    </Modal>
  );
}

/** ثبت پرداخت به همکار */
export function AffiliatePayoutModal({ affiliate, password, onClose, onDone }) {
  const [amount, setAmount] = useState(String(affiliate.balance || ""));
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const [err, setErr] = useState(null);
  const submit = async () => {
    setBusy(true);
    try {
      // پرداخت پول است: شکستش پیش‌تر پنجره را می‌بست و مانده را دست‌نخورده می‌گذاشت
      const res = await fetch(`${API_URL}/api/admin/bot/affiliate/${affiliate.id}/payout`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ amount: +amount, note }),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) { setErr(errText(j.detail, "پرداخت ثبت نشد")); return; }
      onDone();
    } catch { setErr("پرداخت ثبت نشد — اتصال برقرار نشد"); }
    finally { setBusy(false); }
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
      {err && <Msg msg={{ t: "err", m: err }} />}
      <div className="p-3.5 rounded-xl mb-4" style={{ background: "var(--surface-3)" }}>
        <div className="flex justify-between text-[13px]">
          <span style={{ color: "var(--muted)" }}>مانده‌ی فعلی</span>
          <span style={{ color: "var(--warn)", fontFamily: "var(--mono)" }}>
            {faNum(affiliate.balance)}
            <span className="fx-fa-sub"> تومان</span>
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


/**
 * رمزِ ورودِ همکار به پنل خودش.
 *
 * خالی‌گذاشتن و زدنِ «برداشتن رمز» یعنی دسترسی بسته شود — و نشستِ
 * بازش هم همان لحظه باطل می‌شود، وگرنه تا ساعت‌ها هنوز می‌دید.
 */
function AffiliatePasswordModal({ affiliate, password, onClose, onDone }) {
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const send = async (value) => {
    setBusy(true); setErr("");
    try {
      const r = await fetch(
        `${API_URL}/api/admin/bot/affiliate/${affiliate.id}/password`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Admin-Password": password },
          body: JSON.stringify({ password: value }),
        });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(errText(j.detail, "ثبت نشد"));
      onDone(value ? "رمز همکار ثبت شد" : "دسترسی همکار بسته شد");
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  return (
    <Modal title={`رمز ورود — ${affiliate.name}`} onClose={onClose}>
      <p className="text-[12.5px] mb-3 leading-relaxed" style={{ color: "var(--muted)" }}>
        همکار با کد <b dir="ltr">{affiliate.code}</b> و این رمز وارد
        نشانی <b dir="ltr">/aff</b> می‌شود و فقط مشتری‌ها، پورسانت‌ها و
        مانده‌ی خودش را می‌بیند.
      </p>

      <Field label="رمز تازه" hint="حداقل ۶ کاراکتر.">
        <input className="fx-input" type="text" dir="ltr" value={pw}
          onChange={(e) => setPw(e.target.value)} placeholder="••••••" />
      </Field>

      {err && (
        <p className="text-[12.5px] mb-3 flex items-start gap-1.5"
          style={{ color: "var(--danger)" }}>
          <AlertTriangle size={13} className="shrink-0 mt-0.5" />{err}
        </p>
      )}

      <div className="flex gap-2">
        <button className="fx-btn flex-1 py-2.5 text-[13px]"
          disabled={busy || pw.length < 6} onClick={() => send(pw)}>
          ثبت رمز
        </button>
        <button className="fx-btn-g px-4 py-2.5 text-[13px]"
          disabled={busy} onClick={() => send("")}>
          برداشتن رمز
        </button>
      </div>
    </Modal>
  );
}
