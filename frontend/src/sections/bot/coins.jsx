/**
 * ربات: سکه و دعوت دوستان.
 *
 * ── چرا این فایل یک‌بار کامل بازنویسی شد ──
 *
 * این صفحه **هیچ‌وقت کار نمی‌کرد**، و بی‌صدا. مالک عدد می‌گذاشت،
 * «ذخیره شد» می‌دید، و ربات همان مقدارهای پیش‌فرض را می‌داد.
 *
 * دو اشتباه روی هم:
 *
 *   ۱. جای ذخیره. این‌جا `settings.coins_per_referral` نوشته
 *      می‌شد، ولی ربات `settings.coins.per_referral` را می‌خواند
 *      (`core.coin_settings(ctx.s.get("coins"))`). یعنی کلیدها
 *      کنارِ هم می‌نشستند و هیچ‌کدام دیگری را نمی‌دید.
 *
 *   ۲. نامِ فیلد. پله‌ها این‌جا `{coins, pct}` بودند و ربات
 *      `{coins, percent}` می‌خواهد. اندازه‌گیری‌شده: با `pct`،
 *      `core.tier_for` با KeyError می‌افتد.
 *
 * نتیجه‌ی اندازه‌گیری‌شده: مالک «۲۵ سکه به معرف» می‌گذاشت و ربات
 * ۱۰ تا می‌داد؛ پله‌ی «۳۰ سکه = ۱۵٪» می‌ساخت و مشتری ۰٪ تخفیف
 * می‌گرفت.
 *
 * حالا این صفحه دقیقاً همان شکلی را می‌نویسد که `bot/core.py`
 * می‌خواند، و تستِ درز برابریِ این دو را می‌سنجد — چون همین
 * «یک قاعده، دو جا» پرتکرارترین باگِ این مخزن است.
 */
import React, { useState, useMemo, useEffect } from "react";
import {
  Coins, Gift, Loader2, Plus as PlusIcon, Save, Trash2,
} from "lucide-react";
import { adminSrc } from "../../lib/botsrc";
import {
  Field, InfoBox, Msg, NumberInput, NumberStepper, PageSkeleton, SectionHead, Toggle,
} from "../../ui/index";
import { faNum } from "../../lib/format";

/** پیش‌فرض‌ها — عیناً `DEFAULT_COIN_SETTINGS` در `bot/core.py`. */
const DEFAULTS = {
  enabled: true,
  per_referral: 10,
  welcome_bonus: 0,
  max_percent: 50,
  expire_days: 0,
  tiers: [
    { coins: 20, percent: 10 }, { coins: 40, percent: 20 },
    { coins: 60, percent: 30 }, { coins: 80, percent: 40 },
    { coins: 100, percent: 50 },
  ],
};

/* `src` خالی یعنی پنلِ مالک؛ پرتالِ نماینده `portalSrc` می‌دهد. */
export function BotCoinsSection({ password, src }) {
  const S = useMemo(() => src || adminSrc(password), [src, password]);
  const [t, setT] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = async () => {
    try {
      setT({ settings: await S.settings() });
    } catch (e) { setMsg({ t: "err", m: e.message || "اتصال برقرار نشد" }); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [S]);
  useEffect(() => { if (msg) { const x = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(x); } }, [msg]);

  // همه چیز زیر کلیدِ `coins` — همان‌جایی که ربات نگاه می‌کند
  const raw = t?.settings?.coins;
  const c = { ...DEFAULTS, ...(raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {}) };
  const tiers = Array.isArray(c.tiers) && c.tiers.length ? c.tiers : DEFAULTS.tiers;

  const up = (patch) => setT({
    ...t,
    settings: { ...(t?.settings || {}), coins: { ...c, ...patch } },
  });
  const upTiers = (list) => up({
    // مرتب‌سازی صعودی، چون `tier_for` روی اولین پله‌ای که نرسیده
    // `break` می‌زند: پله‌ی نامرتب یعنی پله‌های بعدش دیده نمی‌شوند
    tiers: [...list].sort((a, b) => (Number(a.coins) || 0) - (Number(b.coins) || 0)),
  });

  const save = async () => {
    setSaving(true);
    try {
      await S.saveSettings({ ...(t.settings || {}), coins: c });
      setMsg({ t: "ok", m: "تنظیمات سکه ذخیره شد" });
    } catch (e) { setMsg({ t: "err", m: e.message || "ذخیره ناموفق" }); }
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
        <div className="flex items-center justify-between gap-3 mb-4">
          <div className="text-[14px] font-semibold text-white flex items-center gap-2">
            <Gift size={15} style={{ color: "var(--warn)" }} /> قوانین دریافت سکه
          </div>
          <Toggle checked={c.enabled !== false}
            onChange={(v) => up({ enabled: v })} label="سکه فعال است" />
        </div>

        <div className="fx-g3 grid grid-cols-2 gap-3">
          <Field label="سکه برای معرف" hint="وقتی دعوت‌شده اولین خریدش را کند">
            <NumberStepper value={Number(c.per_referral) || 0}
              onChange={(v) => up({ per_referral: v })} min={0} max={100} unit="سکه" />
          </Field>
          <Field label="سکه برای دعوت‌شده" hint="۰ یعنی چیزی نمی‌گیرد">
            <NumberStepper value={Number(c.welcome_bonus) || 0}
              onChange={(v) => up({ welcome_bonus: v })} min={0} max={100} unit="سکه" />
          </Field>
        </div>

        <div className="fx-g3 grid grid-cols-2 gap-3">
          <Field label="سقف تخفیف"
            hint="حتی اگر پله‌ای بیشتر از این بنویسد، بیشتر از این کم نمی‌شود">
            <NumberStepper value={Number(c.max_percent) || 0}
              onChange={(v) => up({ max_percent: v })} min={0} max={100} unit="٪" />
          </Field>
          <Field label="انقضای سکه" hint="۰ یعنی سکه‌ها هیچ‌وقت منقضی نمی‌شوند">
            <NumberStepper value={Number(c.expire_days) || 0}
              onChange={(v) => up({ expire_days: v })} min={0} max={365} unit="روز" />
          </Field>
        </div>

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
          <button onClick={() => upTiers([...tiers,
            { coins: (Number(tiers[tiers.length - 1]?.coins) || 0) + 20, percent: 55 }])}
            className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
            <PlusIcon size={13} /> افزودن پله
          </button>
        </div>
        <p className="text-[13px] mb-4" style={{ color: "var(--muted)" }}>
          هرچه سکه بیشتری نگه دارد، تخفیف بزرگ‌تری می‌گیرد. فقط سکه‌های
          همان پله خرج می‌شوند، نه همه‌ی موجودی.
        </p>

        {tiers.map((tr, i) => {
          // سقف روی خودِ ردیف دیده شود، نه بعداً سرِ خرید
          const capped = (Number(tr.percent) || 0) > (Number(c.max_percent) || 0);
          return (
            <div key={i} className="flex items-center gap-3 mb-2.5">
              <Coins size={14} style={{ color: "var(--warn)", flexShrink: 0 }} />
              <div className="flex-1 fx-g3 grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[12px] mb-1 block" style={{ color: "var(--muted)" }}>سکه لازم</label>
                  <NumberInput className="fx-input" value={tr.coins}
                    onChange={(e) => { const l = [...tiers]; l[i] = { ...tr, coins: Number(e.target.value) }; upTiers(l); }}
                    style={{ fontFamily: "var(--num)" }} />
                </div>
                <div>
                  <label className="text-[12px] mb-1 block" style={{ color: "var(--muted)" }}>درصد تخفیف</label>
                  <NumberInput className="fx-input" value={tr.percent}
                    onChange={(e) => { const l = [...tiers]; l[i] = { ...tr, percent: Number(e.target.value) }; upTiers(l); }}
                    style={{ fontFamily: "var(--num)" }} />
                  {capped && (
                    <span className="text-[11.5px] mt-1 block" style={{ color: "var(--warn)" }}>
                      سقف {faNum(c.max_percent)}٪ است — بیشتر از آن اعمال نمی‌شود
                    </span>
                  )}
                </div>
              </div>
              <button title="حذف این پله" onClick={() => upTiers(tiers.filter((_, x) => x !== i))}
                className="fx-ico-btn shrink-0" style={{ width: 28, height: 28 }}><Trash2 size={13} /></button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
