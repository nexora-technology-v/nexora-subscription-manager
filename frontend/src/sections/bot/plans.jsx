/**
 * ربات: پلن‌های فروش.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
import React, { useState, useEffect } from "react";
import {
  Gift, Loader2, Package, Plus as PlusIcon, Save, Trash2, TrendingUp, Wallet,
} from "lucide-react";
import { errText, faNum } from "../../lib/format";
import { API_URL } from "../../lib/constants";
import { EmptyState, Field, Msg, MoneyInput, NumberInput, PageSkeleton, SectionHead, StatTile, Toggle } from "../../ui/index";

export function BotPlansSection({ password }) {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/bot/plans`, { headers: { "X-Admin-Password": password } }).then(r => r.json());
      setPlans(d.plans || []);
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [password]);
  useEffect(() => { if (msg) { const x = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(x); } }, [msg]);

  // از همان فهرستی که در دست است
  const paid = plans.filter((p) => !p.is_trial && Number(p.price) > 0);
  const activeCount = plans.filter((p) => p.is_active).length;
  const trialCount = plans.filter((p) => p.is_trial).length;
  const minPrice = paid.length ? Math.min(...paid.map((p) => Number(p.price) || 0)) : 0;
  const maxPrice = paid.length ? Math.max(...paid.map((p) => Number(p.price) || 0)) : 0;

  const up = (i, patch) => { const l = [...plans]; l[i] = { ...l[i], ...patch }; setPlans(l); };
  const add = () => setPlans([...plans, { name: "پلن جدید", gb: 30, days: 30, ip_limit: 1, price: 150000, is_active: true }]);

  const save = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/plans`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ plans }),
      });
      const d = await res.json();
      if (res.ok) { setMsg({ t: "ok", m: `${d.count} پلن ذخیره شد` }); load(); }
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
            <button onClick={save} disabled={saving} className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} ذخیره
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

      {plans.map((p, i) => (
        <div key={i} className="fx-card p-5 mb-3">
          <div className="flex items-center justify-between gap-2 mb-4">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="fx-ico" style={{ background: p.is_trial ? "var(--ok-soft)" : "var(--accent-soft)" }}>
                {p.is_trial ? <Gift size={15} style={{ color: "var(--ok)" }} /> : <Package size={15} style={{ color: "var(--accent-2)" }} />}
              </div>
              <span className="text-[14px] font-semibold text-white truncate">{p.name || "بدون نام"}</span>
            </div>
            <div className="flex items-center gap-2">
              <Toggle checked={p.is_active !== false} onChange={() => up(i, { is_active: !(p.is_active !== false) })} label="فعال" />
              <button title="حذف این پلن" onClick={() => setPlans(plans.filter((_, x) => x !== i))} className="fx-ico-btn" style={{ width: 28, height: 28 }}>
                <Trash2 size={13} />
              </button>
            </div>
          </div>

          <div className="fx-g3 grid grid-cols-2 gap-3">
            <Field label="نام پلن">
              <input className="fx-input" value={p.name || ""} onChange={(e) => up(i, { name: e.target.value })} />
            </Field>
            <Field label="قیمت (تومان)">
              <MoneyInput className="fx-input" value={p.price ?? 0}
                onChange={(e) => up(i, { price: Number(e.target.value) })}
                style={{ fontFamily: "var(--mono)" }}  />
            </Field>
          </div>

          <div className="fx-g3 grid grid-cols-3 gap-3">
            <Field label="حجم (GB)" hint="۰ = نامحدود">
              <NumberInput className="fx-input" value={p.gb ?? 0}
                onChange={(e) => up(i, { gb: Number(e.target.value) })}  />
            </Field>
            <Field label="مدت (روز)" hint="۰ = بدون انقضا">
              <NumberInput className="fx-input" value={p.days ?? 0}
                onChange={(e) => up(i, { days: Number(e.target.value) })}  />
            </Field>
            <Field label="کاربر همزمان">
              <NumberInput className="fx-input" value={p.ip_limit ?? 1}
                onChange={(e) => up(i, { ip_limit: Number(e.target.value) })}  />
            </Field>
          </div>

          <Field label="توضیح کوتاه (اختیاری)">
            <input className="fx-input" value={p.description || ""}
              onChange={(e) => up(i, { description: e.target.value })} placeholder="مناسب استفاده روزمره" />
          </Field>

          <label className="flex items-center gap-2 text-[13px] cursor-pointer" style={{ color: "var(--dim)" }}>
            <input type="checkbox" checked={!!p.is_trial} onChange={(e) => up(i, { is_trial: e.target.checked })}
              style={{ accentColor: "var(--accent)" }} />
            این پلن، تست رایگان است (هر کاربر فقط یک‌بار)
          </label>
        </div>
      ))}
    </div>
  );
}
