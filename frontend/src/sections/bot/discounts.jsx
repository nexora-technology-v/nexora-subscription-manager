/**
 * ربات: کدهای تخفیف.
 *
 * برگه‌اش: docs/specs/2026-09-19-discount-and-trial-winback.md
 *
 * جدولِ `discounts`، اعتبارسنجِ `core.validate_discount` و ستون‌های
 * `orders.discount_code`/`discount_pct` از قبل وجود داشتند و
 * **هیچ‌جا صدا زده نمی‌شدند** — قابلیتی نیمه‌کاره که خودِ
 * `CLAUDE.md` هشدارش را داده بود. این صفحه همان را وصل می‌کند.
 *
 * دو ستونِ «چند بار» و «چقدر» عمداً جدایند: شمارنده می‌گوید چند
 * سفارش، و مبلغ می‌گوید چقدر از جیب رفته. اولی از خودِ کد می‌آید و
 * دومی از سفارش‌های تاییدشده — پس اگر روزی از هم دور افتادند،
 * دیده می‌شود.
 */
import React, { useState, useEffect } from "react";
import {
  AlertTriangle, Loader2, Percent, Plus, Power, Save, Tag, Trash2, UserMinus,
} from "lucide-react";

import { API_URL } from "../../lib/constants";
import { errText, faNum } from "../../lib/format";
import {
  ConfirmModal, EmptyState, Field, InfoBox, Modal, Msg, NumberStepper,
  PageSkeleton, SectionHead, Toggle,
} from "../../ui/index";
import { JalaliDate } from "../../ui/jalali";

async function call(path, password, opt = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    method: opt.method || "GET",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Password": password || "",
    },
    ...(opt.body ? { body: JSON.stringify(opt.body) } : {}),
  });
  const j = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(errText(j.detail, "درخواست ناموفق بود"));
  return j;
}

const EMPTY = {
  id: null, code: "", percent: 20, maxUses: 0, planId: null,
  expiresAt: "", active: true,
};

function Editor({ password, row, plans, onClose, onDone }) {
  const [f, setF] = useState({ ...EMPTY, ...(row || {}) });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const up = (patch) => setF((x) => ({ ...x, ...patch }));

  const save = async () => {
    setBusy(true); setErr("");
    try {
      await call("/api/admin/bot/discounts", password,
        { method: "POST", body: f });
      onDone();
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  return (
    <Modal title={f.id ? "ویرایش کد" : "کد تخفیف تازه"} onClose={onClose}
      width="480px"
      footer={
        <div className="flex items-center gap-2 justify-end">
          <button className="fx-btn-g px-4 py-2 text-[13px]" onClick={onClose}>
            انصراف
          </button>
          <button className="fx-btn px-4 py-2 text-[13px] flex items-center gap-1.5"
            onClick={save} disabled={busy || !f.code.trim()}>
            {busy ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            ذخیره
          </button>
        </div>
      }>
      {err && (
        <p className="text-[12.5px] mb-3 flex items-start gap-1.5"
          style={{ color: "var(--danger)" }}>
          <AlertTriangle size={13} className="shrink-0 mt-0.5" />{err}
        </p>
      )}

      <Field label="کد" hint="حروف انگلیسی، رقم، خط تیره — مشتری همین را تایپ می‌کند">
        {/* `dir="ltr"` چون کد انگلیسی است و در کادرِ راست‌به‌چپ
            جابه‌جا نوشته می‌شود. بزرگ‌کردن هم این‌جا انجام می‌شود تا
            مالک همان چیزی را ببیند که ذخیره می‌شود. */}
        <input className="fx-input" dir="ltr" value={f.code}
          placeholder="NOWRUZ"
          onChange={(e) => up({ code: e.target.value.toUpperCase() })} />
      </Field>

      <div className="fx-g3 grid grid-cols-2 gap-3">
        <Field label="درصد تخفیف" hint="از قیمت پلن کم می‌شود">
          <NumberStepper value={Number(f.percent) || 0}
            onChange={(v) => up({ percent: v })} min={1} max={100} unit="٪" />
        </Field>
        <Field label="سقف استفاده" hint="۰ یعنی نامحدود">
          <NumberStepper value={Number(f.maxUses) || 0}
            onChange={(v) => up({ maxUses: v })} min={0} max={10000} unit="بار" />
        </Field>
      </div>

      <Field label="فقط برای یک پلن"
        hint="خالی یعنی روی همه‌ی پلن‌ها کار می‌کند">
        <select className="fx-input" value={f.planId || ""}
          onChange={(e) => up({ planId: e.target.value || null })}>
          <option value="">همه‌ی پلن‌ها</option>
          {(plans || []).map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </Field>

      {/* تاریخ انتخابی، نه تایپی — قاعده‌ی مخزن: تبدیلِ ذهنیِ
          میلادی به شمسی یعنی خطا، و خطا این‌جا روی کدی می‌نشیند که
          زودتر یا دیرتر از انتظار منقضی می‌شود. */}
      <Field label="تاریخ انقضا" hint="خالی یعنی بدون انقضا">
        <JalaliDate value={f.expiresAt || ""}
          onChange={(v) => up({ expiresAt: v })} />
      </Field>
    </Modal>
  );
}

/**
 * پیگیریِ کسی که تست گرفته و نخریده.
 *
 * چرا این‌جا و نه یک صفحه‌ی جدا: این قابلیت *با* کد تخفیف کار
 * می‌کند — برای هر نفر یک کدِ یک‌بارمصرف ساخته می‌شود. جداکردنشان
 * یعنی مالک باید دو جا را با هم نگه دارد.
 */
function WinBack({ password }) {
  const [t, setT] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = async () => {
    try {
      const d = await call("/api/admin/bot/settings", password);
      setT({
        settings: (d.tenant?.settings && typeof d.tenant.settings === "object"
                   && !Array.isArray(d.tenant.settings)) ? d.tenant.settings : {},
      });
    } catch { setT({ settings: {} }); }
  };
  useEffect(() => { load(); }, [password]);
  useEffect(() => {
    if (msg) { const x = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(x); }
    return undefined;
  }, [msg]);

  const w = { enabled: false, percent: 30, after_hours: 24, valid_hours: 72,
              text: "", ...((t?.settings?.winback) || {}) };
  const up = (patch) => setT((x) => ({
    ...x,
    settings: { ...(x?.settings || {}), winback: { ...w, ...patch } },
  }));

  const save = async () => {
    setBusy(true);
    try {
      await call("/api/admin/bot/settings", password,
        { method: "PUT", body: { settings: t.settings } });
      setMsg({ t: "ok", m: "ذخیره شد" });
    } catch (e) { setMsg({ t: "err", m: e.message }); }
    finally { setBusy(false); }
  };

  if (!t) return null;

  return (
    <div className="fx-card p-5 mb-4">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="text-[14px] font-semibold text-white flex items-center gap-2">
          <UserMinus size={15} style={{ color: "var(--accent-2)" }} />
          پیگیریِ کسی که تست گرفته و نخریده
        </div>
        <div className="flex items-center gap-3">
          <Toggle checked={!!w.enabled} onChange={(v) => up({ enabled: v })}
            label="روشن" />
          <button onClick={save} disabled={busy}
            className="fx-btn px-3 py-2 text-[13px] flex items-center gap-1.5">
            {busy ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
            ذخیره
          </button>
        </div>
      </div>

      <Msg msg={msg} />

      <div className="fx-g3 grid grid-cols-3 gap-3">
        <Field label="درصد تخفیف" hint="روی کدی که برایش ساخته می‌شود">
          <NumberStepper value={Number(w.percent) || 0}
            onChange={(v) => up({ percent: v })} min={1} max={100} unit="٪" />
        </Field>
        <Field label="چند ساعت بعد" hint="از پایانِ تست">
          <NumberStepper value={Number(w.after_hours) || 0}
            onChange={(v) => up({ after_hours: v })} min={1} max={336} unit="ساعت" />
        </Field>
        <Field label="اعتبارِ کد" hint="بعدش خودبه‌خود منقضی می‌شود">
          <NumberStepper value={Number(w.valid_hours) || 0}
            onChange={(v) => up({ valid_hours: v })} min={1} max={720} unit="ساعت" />
        </Field>
      </div>

      <Field label="متن پیام"
        hint="خالی یعنی متنِ پیش‌فرض. می‌توانید {name}، {pct}، {code} و {hours} بگذارید.">
        <textarea className="fx-input" rows={4} value={w.text || ""}
          onChange={(e) => up({ text: e.target.value })}
          placeholder={"تستتان تمام شد 🙂\n\nاگر راضی بودید، این کد {pct}٪ تخفیف دارد:\n{code}"} />
      </Field>

      <InfoBox tone="info">
        هر نفر <b>یک‌بار</b> پیگیری می‌شود و کدش مخصوصِ خودش است — سقفِ
        یک استفاده. کسی که خرید کرده باشد اصلاً پیام نمی‌گیرد.
      </InfoBox>
    </div>
  );
}

/**
 * گزارشِ کدها.
 *
 * تا امروز تنها بازخوردِ مالک `used_count` بود: «چند بار». این
 * می‌گوید **چقدر** — و مهم‌تر، پیگیریِ تست جواب داد یا نه.
 *
 * هیچ عددی این‌جا حساب نمی‌شود؛ همه از `discount_report` می‌آید که
 * تفاوتِ `base_amount` و `amount` روی خودِ سفارش را می‌خواند.
 */
function Report({ r }) {
  if (!r) return null;
  const t = r.total || {};
  const w = r.winback || {};
  if (!t.orders && !w.sent) {
    return (
      <InfoBox>
        هنوز هیچ کدی استفاده نشده. وقتی اولین سفارش با کد تایید شود،
        این‌جا می‌بینید چقدر تخفیف داده‌اید و کدام کد فروش آورده.
      </InfoBox>
    );
  }
  return (
    <>
      <div className="dc-kpis">
        <div className="dc-kpi">
          <span>{faNum(t.orders || 0)}</span>
          <i>سفارش با کد</i>
        </div>
        <div className="dc-kpi">
          <span>{faNum(t.sales || 0)}</span>
          <i>فروش، تومان</i>
        </div>
        <div className="dc-kpi warn">
          <span>{faNum(t.given || 0)}</span>
          <i>تخفیف داده‌شده</i>
        </div>
        <div className="dc-kpi">
          <span>{faNum(t.codes || 0)}</span>
          <i>کدِ استفاده‌شده</i>
        </div>
      </div>

      {/* «فروش» عمداً نوشته شده، نه «درآمد»: سفارشی که از کیف پول
          پرداخت شده فروش هست ولی پولِ تازه‌ای با آن نرسیده — آن
          پول موقعِ شارژ رسیده. */}
      <div className="text-[11.5px] mt-2" style={{ color: "var(--muted)" }}>
        فروش، نه درآمد: خریدِ از کیف پول هم شمرده می‌شود چون پولش
        موقعِ شارژ رسیده. سفارش‌های پلنِ تست شمرده نمی‌شوند.
      </div>

      {(r.top || []).length > 0 && (
        <div className="dc-top mt-3">
          {(r.top || []).map((x) => (
            <div key={x.code} className="dc-top-row">
              <b className="fx-idnum" dir="ltr">{x.code}</b>
              <span>{faNum(x.orders)} سفارش</span>
              <span>فروش {faNum(x.sales)}</span>
              <span style={{ color: "var(--warn)" }}>
                تخفیف {faNum(x.given)}
              </span>
            </div>
          ))}
        </div>
      )}

      {w.sent > 0 && (
        <div className="dc-wb mt-3">
          <b>پیگیریِ تست:</b>{" "}
          برای <b>{faNum(w.sent)}</b> نفر کد رفت،{" "}
          <b>{faNum(w.used)}</b> نفر استفاده {w.used === 1 ? "کرد" : "کردند"}
          {w.sales > 0 && <> و <b>{faNum(w.sales)}</b> تومان فروش آورد</>}.
          {w.sent > 0 && w.used === 0 && (
            <> هنوز کسی برنگشته — شاید درصد یا متنش را عوض کنید.</>
          )}
        </div>
      )}
    </>
  );
}

export function BotDiscountsSection({ password }) {
  const [d, setD] = useState(null);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState(null);
  const [edit, setEdit] = useState(null);
  const [del, setDel] = useState(null);

  const load = async () => {
    try {
      setD(await call("/api/admin/bot/discounts", password));
    } catch (e) { setMsg({ t: "err", m: e.message }); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [password]);
  useEffect(() => {
    if (msg) { const x = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(x); }
    return undefined;
  }, [msg]);

  const toggle = async (row) => {
    try {
      await call("/api/admin/bot/discounts", password,
        { method: "POST", body: { ...row, active: !row.active } });
      load();
    } catch (e) { setMsg({ t: "err", m: e.message }); }
  };

  const remove = async () => {
    const row = del;
    setDel(null);
    try {
      await call(`/api/admin/bot/discounts/${row.id}`, password,
        { method: "DELETE" });
      setMsg({ t: "ok", m: `کد ${row.code} حذف شد` });
      load();
    } catch (e) { setMsg({ t: "err", m: e.message }); }
  };

  if (loading) return <PageSkeleton />;

  const rows = d?.discounts || [];

  return (
    <div className="fx-anim">
      <SectionHead title="کدهای تخفیف"
        desc="کد بسازید و به مشتری بدهید — موقع خرید، چه در ربات و چه در مینی‌اپ، واردش می‌کند."
        action={
          <button onClick={() => setEdit({ ...EMPTY })}
            className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
            <Plus size={14} /> کد تازه
          </button>
        } />

      <Msg msg={msg} />

      <div className="fx-card p-4 mb-4">
        <div className="text-[14px] font-semibold text-white mb-3">
          کدها چقدر کار کرده‌اند
        </div>
        <Report r={d?.report} />
      </div>

      <WinBack password={password} />

      {!rows.length ? (
        <EmptyState icon={Tag} text="هنوز کدی ساخته نشده"
          hint="کد تخفیف برای مناسبت‌ها، برای برگرداندن مشتریِ رفته، یا برای کسی که تست گرفته و نخریده."
          action={
            <button className="fx-btn px-4 py-2 text-[13px]"
              onClick={() => setEdit({ ...EMPTY })}>ساختن اولین کد</button>
          } />
      ) : (
        <div className="fx-card overflow-hidden">
          {rows.map((r, i) => {
            const full = r.maxUses > 0 && r.usedCount >= r.maxUses;
            return (
              <div key={r.id}
                className="flex items-center justify-between gap-3 p-4 flex-wrap"
                style={{ borderBottom: i < rows.length - 1 ? "1px solid var(--border)" : "none" }}>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <b className="text-[15px] fx-idnum" dir="ltr">{r.code}</b>
                    <span className="fx-pill" style={{
                      background: "var(--accent-soft)", color: "var(--accent-2)" }}>
                      {faNum(r.percent)}٪
                    </span>
                    {!r.active && (
                      <span className="fx-pill" style={{
                        background: "var(--hair-2)", color: "var(--muted)" }}>خاموش</span>
                    )}
                    {full && (
                      <span className="fx-pill" style={{
                        background: "var(--warn-soft)", color: "var(--warn)" }}>
                        ظرفیت تمام
                      </span>
                    )}
                    {r.planName && (
                      <span className="text-[12px]" style={{ color: "var(--muted)" }}>
                        فقط {r.planName}
                      </span>
                    )}
                  </div>
                  <div className="text-[12.5px] mt-1" style={{ color: "var(--muted)" }}>
                    {/* «چند بار» از شمارنده‌ی خودِ کد، «چقدر» از
                        سفارش‌های تاییدشده — دو منبع، عمداً. */}
                    {r.maxUses
                      ? <>{faNum(r.usedCount)} از {faNum(r.maxUses)} بار</>
                      : <>{faNum(r.usedCount)} بار استفاده شده</>}
                    {r.givenToman > 0 && (
                      <> · {faNum(r.givenToman)} تومان تخفیف داده</>
                    )}
                    {r.expiresAt && <> · تا {r.expiresAt.slice(0, 10)}</>}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button title={r.active ? "خاموش‌کردن" : "روشن‌کردن"}
                    onClick={() => toggle(r)} className="fx-ico-btn">
                    <Power size={13} />
                  </button>
                  <button title="ویرایش" onClick={() => setEdit(r)}
                    className="fx-ico-btn">
                    <Percent size={13} />
                  </button>
                  <button title="حذف" onClick={() => setDel(r)}
                    className="fx-ico-btn">
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {edit && (
        <Editor password={password} row={edit} plans={d?.plans}
          onClose={() => setEdit(null)}
          onDone={() => { setEdit(null); setMsg({ t: "ok", m: "ذخیره شد" }); load(); }} />
      )}

      {del && (
        <ConfirmModal title={`کد ${del.code} حذف شود؟`}
          desc="سفارش‌هایی که با این کد ساخته شده‌اند دست‌نخورده می‌مانند — کد و درصد روی خودِ سفارش ثبت شده، پس فاکتورهای قبلی عوض نمی‌شوند."
          onCancel={() => setDel(null)} onConfirm={remove} />
      )}
    </div>
  );
}
