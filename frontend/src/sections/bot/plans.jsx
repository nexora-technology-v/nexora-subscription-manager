/**
 * ربات: پلن‌های فروش.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
import React, { useState, useEffect } from "react";
import {
  ChevronDown, Gift, Loader2, Package, Plus as PlusIcon, Save, Trash2, TrendingUp, Wallet,
} from "lucide-react";
import { errText, faNum } from "../../lib/format";
import { API_URL } from "../../lib/constants";
import { EmptyState, Field, Msg, MoneyInput, NumberInput, PageSkeleton, SectionHead, StatTile, Toggle } from "../../ui/index";

/* ستونِ is_active در دیتابیس ۰/۱ است، نه true/false. سنجیدنش با «نابرابر با
   false» برای ۰ هم «روشن» می‌داد: پلنِ خاموش در پنل روشن دیده می‌شد، کاشیِ بالا
   «۱ پلن خاموش» می‌گفت و کلیدِ همان پلن روشن بود. */
export const isOn = (v) => v !== false && v !== 0 && v !== "0" && v != null;

export function BotPlansSection({ password }) {
  const [plans, setPlans] = useState([]);
  const [saved, setSaved] = useState("[]");
  const [open, setOpen] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = async () => {
    try {
      const r = await fetch(`${API_URL}/api/admin/bot/plans`, { headers: { "X-Admin-Password": password } });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) { setMsg({ t: "err", m: errText(d.detail, "خواندنِ پلن‌ها ناموفق بود") }); return; }
      const list = (d.plans || []).map((x) => ({ ...x, is_active: isOn(x.is_active), is_trial: !!x.is_trial }));
      setPlans(list);
      setSaved(JSON.stringify(list));
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [password]);
  useEffect(() => { if (msg) { const x = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(x); } }, [msg]);

  // از همان فهرستی که در دست است
  const paid = plans.filter((p) => !p.is_trial && Number(p.price) > 0);
  const activeCount = plans.filter((p) => isOn(p.is_active)).length;
  // پیش‌تر هیچ نشانی از تغییرِ ذخیره‌نشده نبود؛ رفتن به صفحه‌ی دیگر قیمتِ
  // تازه را بی‌صدا دور می‌ریخت
  const dirty = JSON.stringify(plans) !== saved;
  const trialCount = plans.filter((p) => p.is_trial).length;
  const minPrice = paid.length ? Math.min(...paid.map((p) => Number(p.price) || 0)) : 0;
  const maxPrice = paid.length ? Math.max(...paid.map((p) => Number(p.price) || 0)) : 0;

  const up = (i, patch) => { const l = [...plans]; l[i] = { ...l[i], ...patch }; setPlans(l); };
  const add = () => {
    setPlans([...plans, { name: "پلن جدید", gb: 30, days: 30, ip_limit: 1, price: 150000, is_active: true, is_trial: false }]);
    setOpen(plans.length);
  };

  const save = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/plans`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ plans }),
      });
      const d = await res.json().catch(() => ({}));
      if (res.ok) { setMsg({ t: "ok", m: `${faNum(d.count)} پلن ذخیره شد` }); setOpen(null); load(); }
      else setMsg({ t: "err", m: errText(d.detail, "ذخیره ناموفق") });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setSaving(false); }
  };

  if (loading) return <PageSkeleton />;

  return (
    <div className="fx-anim">
      <SectionHead title="پلن‌های فروش"
        desc="پلن‌هایی که مشتری در ربات می‌بیند. حجم صفر یعنی نامحدود."
        action={
          <div className="flex gap-2">
            <button onClick={add} className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5"><PlusIcon size={13} /> پلن جدید</button>
            <button onClick={save} disabled={saving || !dirty} className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              {dirty ? "ذخیره‌ی تغییرات" : "ذخیره‌شده"}
            </button>
          </div>
        } />

      <Msg msg={msg} />

      {/* خلاصه‌ی همین فهرست — بدون درخواست تازه.
          «چند پلن فعال است» و «ارزان‌ترین و گران‌ترین کدام‌اند»
          سؤال‌هایی بودند که باید با شمردنِ کارت‌ها جواب می‌گرفتند. */}
      {plans.length > 0 && (
        <div className="fx-g3 grid grid-cols-3 gap-3">
          <StatTile label="پلن فعال" icon={Package} tone="var(--accent-2)"
            value={faNum(activeCount)}
            hint={plans.length - activeCount > 0
                  ? `${faNum(plans.length - activeCount)} پلن خاموش`
                  : "همه‌ی پلن‌ها روشن‌اند"} />
          <StatTile label="ارزان‌ترین" icon={Wallet} tone="var(--ok)"
            value={faNum(minPrice)} unit="تومان" color="var(--ok)"
            hint={trialCount ? `${faNum(trialCount)} پلن تست رایگان` : "بدون پلن تست"} />
          <StatTile label="گران‌ترین" icon={TrendingUp} tone="var(--purple)"
            value={faNum(maxPrice)} unit="تومان" color="var(--purple)"
            hint="سقف فروش شما" />
        </div>
      )}

      {plans.length === 0 && (
        <EmptyState icon={Package} text="هنوز پلنی تعریف نشده"
          hint="بدون پلن، مشتری نمی‌تواند خرید کند" />
      )}

      {/* فهرستِ فشرده؛ ویرایشگر فقط برای پلنی که باز شده. پیش‌تر هر پلن یک
          فرمِ ۳۴۰ پیکسلیِ همیشه‌باز بود — پنج پلن، ۱۷۰۰ پیکسل فرم برای دیدنِ
          پنج قیمت. */}
      {plans.length > 0 && (
        <div className="fx-card overflow-hidden" style={{ padding: 0 }}>
          {plans.map((p, i) => {
            const on = isOn(p.is_active);
            const isOpen = open === i;
            return (
              <div key={p.id || `new-${i}`} className={`fx-plan ${isOpen ? "open" : ""} ${on ? "" : "off"}`}>
                <div className="fx-plan-row">
                  <button className="flex items-center gap-3 min-w-0 flex-1 text-right"
                    onClick={() => setOpen(isOpen ? null : i)} aria-expanded={isOpen}>
                    <span className="fx-ico shrink-0" style={{ background: p.is_trial ? "var(--ok-soft)" : "var(--accent-soft)" }}>
                      {p.is_trial ? <Gift size={15} style={{ color: "var(--ok)" }} /> : <Package size={15} style={{ color: "var(--accent-2)" }} />}
                    </span>
                    <span className="min-w-0">
                      <span className="flex items-center gap-2 flex-wrap">
                        <span className="text-[14px] font-semibold text-white truncate">{p.name || "بدون نام"}</span>
                        {!!p.is_trial && <span className="fx-pill" style={{ background: "var(--ok-soft)", color: "var(--ok)" }}>تست رایگان</span>}
                        {!on && <span className="fx-pill" style={{ background: "var(--hair-2)", color: "var(--muted)" }}>خاموش</span>}
                      </span>
                      <span className="block text-[12px] mt-0.5 fx-clamp2" style={{ color: "var(--muted)" }}>
                        {Number(p.gb) ? `${faNum(p.gb)} گیگ` : "نامحدود"} · {Number(p.days) ? `${faNum(p.days)} روز` : "بی‌انقضا"} · {faNum(p.ip_limit || 1)} کاربره
                        {p.description ? ` · ${p.description}` : ""}
                      </span>
                    </span>
                  </button>
                  <span className="text-[14px] font-bold shrink-0" style={{ color: Number(p.price) ? "var(--text)" : "var(--ok)", fontFamily: "var(--num)" }}>
                    {Number(p.price) ? <>{faNum(p.price)} <span className="fx-fa-sub text-[11px]" style={{ color: "var(--muted)" }}>تومان</span></> : "رایگان"}
                  </span>
                  <Toggle checked={on} onChange={() => up(i, { is_active: !on })} label="فعال" />
                  <button title={isOpen ? "بستن" : "ویرایش"} aria-label={isOpen ? "بستن" : "ویرایش"}
                    onClick={() => setOpen(isOpen ? null : i)} className="fx-ico-btn" style={{ width: 32, height: 32 }}>
                    <ChevronDown size={14} style={{ transform: isOpen ? "rotate(180deg)" : "none", transition: "transform .2s" }} />
                  </button>
                </div>

                {isOpen && (
                  <div className="fx-plan-edit">
                    <div className="fx-g3 grid grid-cols-2 gap-3">
                      <Field label="نام پلن">
                        <input className="fx-input" value={p.name || ""} onChange={(e) => up(i, { name: e.target.value })} />
                      </Field>
                      <Field label="قیمت (تومان)">
                        <MoneyInput className="fx-input" value={p.price ?? 0}
                          onChange={(e) => up(i, { price: Number(e.target.value) })}
                          style={{ fontFamily: "var(--mono)" }} />
                      </Field>
                    </div>
                    <div className="fx-g3 grid grid-cols-3 gap-3">
                      <Field label="حجم (GB)" hint="۰ = نامحدود">
                        <NumberInput className="fx-input" value={p.gb ?? 0}
                          onChange={(e) => up(i, { gb: Number(e.target.value) })} />
                      </Field>
                      <Field label="مدت (روز)" hint="۰ = بدون انقضا">
                        <NumberInput className="fx-input" value={p.days ?? 0}
                          onChange={(e) => up(i, { days: Number(e.target.value) })} />
                      </Field>
                      <Field label="کاربر همزمان">
                        <NumberInput className="fx-input" value={p.ip_limit ?? 1}
                          onChange={(e) => up(i, { ip_limit: Number(e.target.value) })} />
                      </Field>
                    </div>
                    <Field label="توضیح کوتاه (اختیاری)">
                      <input className="fx-input" value={p.description || ""}
                        onChange={(e) => up(i, { description: e.target.value })} placeholder="مناسب استفاده روزمره" />
                    </Field>
                    <div className="flex items-center justify-between gap-3 flex-wrap">
                      <label className="flex items-center gap-2 text-[13px] cursor-pointer" style={{ color: "var(--dim)" }}>
                        <input type="checkbox" checked={!!p.is_trial} onChange={(e) => up(i, { is_trial: e.target.checked })}
                          style={{ accentColor: "var(--accent)" }} />
                        این پلن، تست رایگان است (هر کاربر فقط یک‌بار)
                      </label>
                      <button onClick={() => { setPlans(plans.filter((_, x) => x !== i)); setOpen(null); }}
                        className="fx-btn-g fx-ico-danger px-3 py-2 text-[12.5px] flex items-center gap-1.5">
                        <Trash2 size={13} /> حذف (با ذخیره نهایی می‌شود)
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
