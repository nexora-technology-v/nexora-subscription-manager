/**
 * ربات: سکه و دعوت دوستان.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
import React, { useState, useEffect } from "react";
import {
  Coins, Gift, Loader2, Plus as PlusIcon, Save, Trash2,
} from "lucide-react";
import { API_URL } from "../../lib/constants";
import { Field, InfoBox, Msg, NumberInput, NumberStepper, PageSkeleton, SectionHead } from "../../ui/index";

export function BotCoinsSection({ password }) {
  const [t, setT] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/bot/settings`, { headers: { "X-Admin-Password": password } }).then(r => r.json());
      setT({
        settings: {}, topics: {},
        ...(d.tenant || {}),
        settings: (d.tenant?.settings && typeof d.tenant.settings === "object"
                   && !Array.isArray(d.tenant.settings)) ? d.tenant.settings : {},
      });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [password]);
  useEffect(() => { if (msg) { const x = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(x); } }, [msg]);

  const s = t?.settings || {};
  const tiers = s.coin_tiers || [
    { coins: 20, pct: 10 }, { coins: 40, pct: 20 }, { coins: 60, pct: 30 },
    { coins: 80, pct: 40 }, { coins: 100, pct: 50 },
  ];
  const upS = (patch) => setT({ ...t, settings: { ...s, ...patch } });

  const save = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ settings: t.settings }),
      });
      if (res.ok) setMsg({ t: "ok", m: "تنظیمات سکه ذخیره شد" });
      else setMsg({ t: "err", m: "ذخیره ناموفق" });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setSaving(false); }
  };

  if (loading) return <PageSkeleton />;

  return (
    <div className="fx-anim">
      <SectionHead title="سکه و دعوت"
        desc="کاربران با دعوت دوستان سکه می‌گیرند و با نگه‌داشتن سکه، تخفیف بزرگ‌تری باز می‌کنند."
        action={
          <button onClick={save} disabled={saving} className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} ذخیره
          </button>
        } />

      <Msg msg={msg} />

      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-4 flex items-center gap-2">
          <Gift size={15} style={{ color: "var(--warn)" }} /> قوانین دریافت سکه
        </div>

        <div className="fx-g3 grid grid-cols-2 gap-3">
          <Field label="سکه برای معرف" hint="وقتی دعوت‌شده اولین خریدش را کند">
            <NumberStepper value={s.coins_per_referral ?? 5} onChange={(v) => upS({ coins_per_referral: v })} min={0} max={50} unit="سکه" />
          </Field>
          <Field label="سکه برای دعوت‌شده" hint="۰ یعنی چیزی نمی‌گیرد">
            <NumberStepper value={s.coins_for_invitee ?? 2} onChange={(v) => upS({ coins_for_invitee: v })} min={0} max={50} unit="سکه" />
          </Field>
        </div>

        <Field label="حداقل مبلغ خرید برای احتساب" hint="خریدهای کمتر از این، سکه نمی‌دهند">
          <NumberInput className="fx-input" value={s.min_purchase_for_coin ?? 0}
            onChange={(e) => upS({ min_purchase_for_coin: Number(e.target.value) })}
            style={{ fontFamily: "var(--mono)" }}  />
        </Field>

        <InfoBox tone="warn">
          سکه فقط بعد از <b>خرید واقعی</b> دعوت‌شده داده می‌شود، نه با ثبت‌نام ساده.
          این جلوی سوءاستفاده با اکانت‌های جعلی را می‌گیرد.
        </InfoBox>
      </div>

      <div className="fx-card p-5">
        <div className="flex items-center justify-between gap-3 mb-1">
          <div className="text-[14px] font-semibold text-white flex items-center gap-2">
            <Coins size={15} style={{ color: "var(--warn)" }} /> نردبان تخفیف
          </div>
          <button onClick={() => upS({ coin_tiers: [...tiers, { coins: 120, pct: 55 }] })}
            className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
            <PlusIcon size={13} /> افزودن پله
          </button>
        </div>
        <p className="text-[13px] mb-4" style={{ color: "var(--muted)" }}>
          هرچه سکه بیشتری نگه دارد، تخفیف بزرگ‌تری می‌گیرد.
        </p>

        {tiers.map((tr, i) => (
          <div key={i} className="flex items-center gap-3 mb-2.5">
            <Coins size={14} style={{ color: "var(--warn)", flexShrink: 0 }} />
            <div className="flex-1 fx-g3 grid grid-cols-2 gap-3">
              <div>
                <label className="text-[12px] mb-1 block" style={{ color: "var(--muted)" }}>سکه لازم</label>
                <NumberInput className="fx-input" value={tr.coins}
                  onChange={(e) => { const l = [...tiers]; l[i] = { ...tr, coins: Number(e.target.value) }; upS({ coin_tiers: l }); }}
                  style={{ fontFamily: "var(--mono)" }}  />
              </div>
              <div>
                <label className="text-[12px] mb-1 block" style={{ color: "var(--muted)" }}>درصد تخفیف</label>
                <NumberInput className="fx-input" value={tr.pct}
                  onChange={(e) => { const l = [...tiers]; l[i] = { ...tr, pct: Number(e.target.value) }; upS({ coin_tiers: l }); }}
                  style={{ fontFamily: "var(--mono)" }}  />
              </div>
            </div>
            <button title="حذف این پله" onClick={() => upS({ coin_tiers: tiers.filter((_, x) => x !== i) })}
              className="fx-ico-btn shrink-0" style={{ width: 28, height: 28 }}><Trash2 size={13} /></button>
          </div>
        ))}
      </div>
    </div>
  );
}
