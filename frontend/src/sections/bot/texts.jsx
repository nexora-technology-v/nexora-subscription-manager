/**
 * ربات: متن پیام‌ها و رفتار.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
import React, { useState, useEffect } from "react";
import {
  BellRing, Check, Circle, Loader2, Save,
} from "lucide-react";
import { API_URL } from "../../lib/constants";
import {
  Field, InfoBox, Msg, NumberInput, NumberStepper, PageSkeleton, SectionHead,
  Toggle,
} from "../../ui/index";

export const BOT_TEXTS = [
  { k: "welcome_text", label: "پیام خوش‌آمد",
    hint: "اگر خالی بماند، وضعیت زنده‌ی کاربر نمایش داده می‌شود",
    vars: ["{name}", "{brand}"],
    sample: "سلام {name} 👋\n\nبه {brand} خوش آمدید." },
  { k: "phone_prompt", label: "درخواست شماره",
    hint: "اختیاری بودن آن را حتماً بگویید", vars: [],
    sample: "📱 اگر شماره‌تان را ثبت کنید، سریع‌تر می‌توانیم کمکتان کنیم." },
  { k: "waiting_text", label: "بعد از ارسال رسید",
    hint: "", vars: ["{order_id}", "{support}"],
    sample: "✅ رسید شما دریافت شد\nکد پیگیری: {order_id}" },
  { k: "reject_text", label: "رد رسید",
    hint: "دلیل رد خودکار جایگزین می‌شود", vars: ["{order_id}", "{reason}", "{support}"],
    sample: "❌ رسید شما تایید نشد\n\nدلیل: {reason}" },
  { k: "delivered_text", label: "تحویل کانفیگ",
    hint: "", vars: ["{plan}", "{sub_url}", "{expires}"],
    sample: "🎉 اشتراک شما فعال شد!\n\n{sub_url}" },
  { k: "expiry_text", label: "یادآوری انقضا",
    hint: "", vars: ["{days}", "{plan}"],
    sample: "⏰ {days} روز تا پایان اشتراک شما باقی مانده." },
  { k: "help_text", label: "آموزش نصب",
    hint: "خالی بماند، متن سه‌قدمی پیش‌فرض نمایش داده می‌شود", vars: ["{brand}"],
    sample: "📚 آموزش نصب\n\nسه قدم، کمتر از دو دقیقه:" },
];

/**
 * تنظیم‌هایی که ربات می‌خواند ولی تا امروز هیچ فیلدی در پنل نداشتند.
 *
 * تست درزها (tools/test-seams.py) اینها را پیدا کرد: هر هشت کلید در
 * handlers.py خوانده می‌شد و چون پنل راهی برای نوشتنشان نداشت، همیشه
 * روی مقدار پیش‌فرض قفل بودند. بدترینش trial_enabled بود — «تست رایگان»
 * را به‌هیچ‌وجه نمی‌شد روشن کرد.
 */
export const BOT_BEHAVIOUR = [
  { k: "trial_enabled", type: "bool", def: false, label: "اشتراک تست رایگان",
    hint: "هر کاربر یک بار می‌تواند بگیرد" },
  { k: "ask_phone", type: "bool", def: true, label: "درخواست شماره تماس",
    hint: "همیشه اختیاری است؛ این فقط نمایش دکمه را کنترل می‌کند" },
  { k: "support_username", type: "text", label: "یوزرنیم پشتیبانی",
    ph: "@nexora_support",
    hint: "در پیام‌های خطا و رد رسید به مشتری نشان داده می‌شود" },
  { k: "order_ttl_minutes", type: "num", def: 30, min: 5, max: 1440,
    label: "مهلت پرداخت", unit: "دقیقه",
    hint: "بعد از این مدت سفارش پرداخت‌نشده منقضی می‌شود" },
  { k: "email_prefix", type: "text", label: "پیشوند شناسه کانفیگ",
    ph: "nexora",
    hint: "شناسه‌ی کلاینت در پنل این شکلی ساخته می‌شود: prefix_tgid_1" },
  { k: "sub_base_url", type: "text", label: "دامنه‌ی لینک اشتراک",
    ph: "https://sub.nexora.ir",
    hint: "خالی بماند، از تنظیمات خود پنل 3x-ui خوانده می‌شود" },
  { k: "miniapp_url", type: "text", label: "آدرس مینی‌اپ",
    ph: "خودکار — از دامنه‌ی لینک اشتراک",
    hint: "خالی بماند، خودش از دامنه‌ی لینک اشتراک ساخته می‌شود "
        + "(همان دامنه + ‎/app‎). فقط اگر مینی‌اپ را جای دیگری سرو "
        + "می‌کنید این را پر کنید — و حتماً https، چون تلگرام با "
        + "http پیام را اصلاً نمی‌فرستد." },
];

/**
 * یادآوری‌ها: روشن/خاموش، آستانه‌ها، و متنِ هشدارِ حجم.
 *
 * چرا این‌جا و نه یک صفحه‌ی جدا: فهرستِ کناریِ بخشِ ربات چهارده قلم
 * دارد و یکی بیشتر یعنی شلوغ‌تر. متنِ یادآوری هم از قبل همین‌جاست —
 * زمان‌بندی کنارِ متنی می‌نشیند که فرمانش را می‌دهد.
 *
 * چرا سه اسلاتِ ثابت: پرچمِ «فرستاده شد» سه ستونِ مشخص است
 * (notified_7d/3d/1d). فهرستِ آزاد یعنی ستونِ notified_14d هم لازم
 * است. سه اسلات که مالک عددشان را عوض می‌کند همان کار را بدونِ
 * مهاجرت می‌کند. صفر یعنی همان اسلات خاموش.
 */
function Reminders({ s, upS }) {
  const r = { enabled: true, days: [7, 3, 1], traffic_pct: 80,
              traffic_text: "", ...(s.reminders || {}) };
  const days = Array.isArray(r.days) ? r.days : [7, 3, 1];
  const up = (patch) => upS({ reminders: { ...r, days, ...patch } });
  const setDay = (i, v) => {
    const next = [days[0] ?? 0, days[1] ?? 0, days[2] ?? 0];
    next[i] = Number(v) || 0;
    up({ days: next });
  };

  const off = !r.enabled;

  return (
    <div className="fx-card p-4 mt-3">
      <div className="flex items-start justify-between gap-4 pb-3"
        style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="min-w-0 flex-1">
          <div className="text-[14px] font-semibold text-white flex items-center gap-2">
            <BellRing size={15} style={{ color: "var(--accent-2)" }} />
            یادآوری‌ها روشن باشند
          </div>
          <div className="text-[12px] mt-1 leading-relaxed"
            style={{ color: "var(--muted)" }}>
            هم یادآوری نزدیک‌شدن انقضا، هم هشدار پرشدن حجم. خاموش‌کردن
            یعنی مشتری اولین خبری که می‌گیرد قطع‌شدن است.
          </div>
        </div>
        <div className="shrink-0">
          <Toggle label="یادآوری‌ها" checked={!!r.enabled}
            onChange={() => up({ enabled: !r.enabled })} />
        </div>
      </div>

      <div style={{ opacity: off ? 0.45 : 1, pointerEvents: off ? "none" : "auto" }}>
        <div className="pt-3">
          <Field label="چند روز مانده یادآوری برود"
            hint="سه نوبت. صفر یعنی آن نوبت فرستاده نشود.">
            <div className="fx-g3 grid grid-cols-3 gap-3">
              {[0, 1, 2].map((i) => (
                <NumberStepper key={i} value={Number(days[i]) || 0}
                  onChange={(v) => setDay(i, v)} min={0} max={90} unit="روز" />
              ))}
            </div>
          </Field>
        </div>

        <Field label="هشدار حجم از چند درصد"
          hint="وقتی مصرف از این درصد رد شود، یک‌بار خبر می‌رود. صفر یعنی این هشدار خاموش.">
          <NumberStepper value={Number(r.traffic_pct) || 0}
            onChange={(v) => up({ traffic_pct: v })} min={0} max={100} unit="٪" />
        </Field>

        <Field label="متن هشدار حجم"
          hint="خالی بماند، متن پیش‌فرض می‌رود. جای‌گذارها: {used} {total} {left} {pct} {plan} {label}">
          <textarea className="fx-input" rows={3} value={r.traffic_text || ""}
            onChange={(e) => up({ traffic_text: e.target.value })}
            placeholder={"📊 {pct}٪ از حجم {label} مصرف شده.\nباقی‌مانده: {left} گیگ"}
            style={{ resize: "vertical", lineHeight: 1.9 }} />
        </Field>

        <InfoBox>
          عوض‌کردنِ عددِ یک نوبت، کسی را که <b>قبلاً همان نوبت را
          گرفته</b> دوباره خبر نمی‌کند. سرِ تمدید پرچم‌ها صفر می‌شوند و
          از آن به بعد عددِ تازه کار می‌کند.
        </InfoBox>
      </div>
    </div>
  );
}

export function BotTextsSection({ password }) {
  const [t, setT] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/bot/settings`, {
        headers: { "X-Admin-Password": password } }).then((r) => r.json());
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
  const upS = (patch) => setT({ ...t, settings: { ...s, ...patch } });

  const save = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ settings: t.settings }),
      });
      setMsg(res.ok ? { t: "ok", m: "متن‌ها ذخیره شد — ربات فوری اعمال می‌کند" }
                    : { t: "err", m: "ذخیره ناموفق" });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setSaving(false); }
  };

  if (loading) return <PageSkeleton />;

  return (
    <div className="fx-anim">
      <SectionHead title="متن‌های ربات"
        desc="هر پیامی که ربات می‌فرستد قابل ویرایش است. خالی بگذارید تا متن پیش‌فرض استفاده شود."
        action={
          <button onClick={save} disabled={saving} className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} ذخیره
          </button>
        } />

      <Msg msg={msg} />

      <InfoBox>
        تغییرات <b>بدون ری‌استارت ربات</b> اعمال می‌شوند — ربات هر بار تنظیمات را تازه می‌خواند.
      </InfoBox>

      {/* دو ستون، نه یک ستونِ ۹۷۰ پیکسلی.
          هر کارت یک textarea سه‌خطی است؛ با تمام‌عرض بودنشان صفحه
          ۲۳۲۴ پیکسل بلند می‌شد و هر کارت پر از فضای خالی بود.
          روی موبایل خودش یک‌ستونه می‌شود. */}
      <div className="fx-g2-even grid gap-3 mt-3">
      {BOT_TEXTS.map((f) => (
        <div key={f.k} className="fx-card p-4">
          <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
            <span className="text-[14px] font-semibold text-white">{f.label}</span>
            {f.vars.length > 0 && (
              <div className="flex gap-1.5 flex-wrap">
                {f.vars.map((v) => (
                  <code key={v} className="text-[11.5px] px-2 py-1 rounded-md"
                    style={{ background: "var(--accent-soft)", color: "var(--accent-2)",
                             fontFamily: "var(--mono)" }}>{v}</code>
                ))}
              </div>
            )}
          </div>
          <textarea className="fx-input" rows={3} value={s[f.k] || ""}
            onChange={(e) => upS({ [f.k]: e.target.value })}
            placeholder={f.sample} style={{ resize: "vertical", lineHeight: 1.9 }} />
          {f.hint && <div className="text-[12px] mt-1.5" style={{ color: "var(--muted)" }}>{f.hint}</div>}
        </div>
      ))}
      </div>

      <SectionHead title="یادآوری‌ها"
        desc="چه وقت به مشتری خبر بدهیم که اشتراکش دارد تمام می‌شود — یا حجمش." />

      <Reminders s={s} upS={upS} />

      <SectionHead title="رفتار ربات"
        desc="تنظیم‌هایی که ربات موقع کار می‌خواند — بدون اینها روی مقدار پیش‌فرض می‌ماند." />

      <div className="fx-card p-4 mt-3">
        {BOT_BEHAVIOUR.map((f) => (
          <div key={f.k}
            className="flex items-start justify-between gap-4 py-3"
            style={{ borderBottom: "1px solid var(--border)" }}>
            <div className="min-w-0 flex-1">
              <div className="text-[14px] font-semibold text-white">{f.label}</div>
              <div className="text-[12px] mt-1 leading-relaxed"
                style={{ color: "var(--muted)" }}>{f.hint}</div>
            </div>
            <div className="shrink-0" style={{ width: f.type === "bool" ? "auto" : 200 }}>
              {f.type === "bool" && (
                <Toggle label={f.label}
                  checked={s[f.k] === undefined ? f.def : !!s[f.k]}
                  onChange={() => upS({ [f.k]: !(s[f.k] === undefined ? f.def : !!s[f.k]) })} />
              )}
              {f.type === "num" && (
                <div className="flex items-center gap-2">
                  <NumberInput className="fx-input" min={f.min} max={f.max}
                    value={s[f.k] ?? f.def}
                    onChange={(e) => upS({ [f.k]: Number(e.target.value) || f.def })}
                    style={{ textAlign: "center" }}  />
                  <span className="text-[12px] shrink-0"
                    style={{ color: "var(--muted)" }}>{f.unit}</span>
                </div>
              )}
              {f.type === "text" && (
                <input className="fx-input" value={s[f.k] || ""} placeholder={f.ph}
                  onChange={(e) => upS({ [f.k]: e.target.value })}
                  style={{ fontFamily: "var(--mono)", direction: "ltr", textAlign: "left" }} />
              )}
            </div>
          </div>
        ))}

        {/* مدیرها آیدی عددی‌اند، پس هر خط یک عدد — نه CSV که با فاصله خراب شود */}
        <div className="pt-3">
          <Field label="مدیرهای ربات"
            hint="هر خط یک آیدی عددی تلگرام. اینها دسترسی پنل مدیریت داخل ربات را دارند.">
            <textarea className="fx-input" rows={3}
              value={(s.admins || []).join("\n")}
              onChange={(e) => upS({
                admins: e.target.value.split("\n")
                  .map((x) => parseInt(x.trim(), 10))
                  .filter((x) => Number.isFinite(x)),
              })}
              placeholder={"123456789\n987654321"}
              style={{ fontFamily: "var(--mono)", direction: "ltr",
                       textAlign: "left", resize: "vertical" }} />
          </Field>
        </div>
      </div>
    </div>
  );
}

export const PREVIEW_FLOWS = {
  welcome: {
    label: "خوش‌آمد",
    msgs: [
      { me: true, t: "/start" },
      { t: "سلام علی 👋\n\n📦 <b>استاندارد</b>\n   ✅ <b>۱۷ روز</b> باقی مانده\n\n💎 ۴۵ سکه <i>(۲۰٪ تخفیف)</i>   ·   👛 ۱۲۰,۰۰۰",
        kb: [["🛒 خرید اشتراک", "♻️ تمدید"], ["📊 وضعیت من", "💎 سکه و دعوت"], ["👛 کیف پول", "🎓 آموزش"], ["🎧 پشتیبانی"]] },
    ],
  },
  phone: {
    label: "شماره تماس",
    msgs: [
      { t: "📱 <b>شماره تماس</b>\n\nاگر شماره‌تان را ثبت کنید، در صورت بروز مشکل سریع‌تر می‌توانیم کمکتان کنیم.\n\n<i>اختیاری است — بدون آن هم می‌توانید خرید کنید.</i>",
        contact: true, kb: [["📱 ارسال شماره من"], ["فعلاً نه"]] },
    ],
  },
  buy: {
    label: "خرید با سکه",
    msgs: [
      { me: true, t: "🥈 استاندارد · ۶۰GB" },
      { t: "<b>پلن استاندارد</b> 🥈\n\n📦 حجم: ۶۰ گیگابایت\n⏱ مدت: ۳۰ روز\n👥 کاربر همزمان: ۲\n\n💵 قیمت: ۲۵۰,۰۰۰ تومان\n\n💎 <b>سکه‌های تو: ۴۵</b>\nمی‌توانی ۴۰ سکه خرج کنی ← <b>۲۰٪ تخفیف</b>\n\n💰 قیمت نهایی: <b>۲۰۰,۰۰۰</b>",
        kb: [["✅ خرید با ۲۰٪ تخفیف"], ["💵 خرید بدون تخفیف"], ["‹ بازگشت"]] },
    ],
  },
  wait: {
    label: "انتظار تایید",
    msgs: [
      { me: true, img: true, t: "[عکس رسید]" },
      { t: "✅ <b>رسید شما دریافت شد</b>\n━━━━━━━━━━━━━━━━━━━\n\n🔢 کد پیگیری: <code>#4821</code>\n⏳ در انتظار بررسی\n\nمعمولاً کمتر از ۱۵ دقیقه طول می‌کشد.\nبه محض تایید، کانفیگتان همین‌جا ارسال می‌شود.",
        kb: [["📊 وضعیت سفارش"], ["🎧 پشتیبانی"], ["‹ منوی اصلی"]] },
    ],
  },
  reject: {
    label: "رد رسید",
    msgs: [
      { t: "❌ <b>رسید شما تایید نشد</b>\n━━━━━━━━━━━━━━━━━━━\n\n🔢 کد پیگیری: <code>#4821</code>\n\n<b>دلیل:</b>\nمبلغ واریزی با مبلغ سفارش مطابقت ندارد.\n\n💎 ۴۰ سکه‌ی شما برگردانده شد.\n\nمی‌توانید رسید درست را دوباره بفرستید.",
        kb: [["🔄 ارسال مجدد رسید"], ["🎧 پشتیبانی"], ["‹ منوی اصلی"]] },
    ],
  },
  trial: {
    label: "تست رایگان",
    msgs: [
      { me: true, t: "🎁 تست رایگان" },
      { t: "🎁 <b>اشتراک تست رایگان</b>\n\n📦 حجم: <b>۱ گیگابایت</b>\n⏱ مدت: <b>۲۴ ساعت</b>\n\n<i>هر کاربر فقط یک‌بار می‌تواند دریافت کند.</i>",
        kb: [["✅ فعال‌سازی تست"], ["‹ بازگشت"]] },
    ],
  },
  admin: {
    label: "پنل مدیریت",
    msgs: [
      { me: true, t: "⚙️ پنل مدیریت" },
      { t: "⚙️ <b>پنل مدیریت</b> · نکسورا\n━━━━━━━━━━━━━━━━━━━\n\n👥 کاربران   <b>۴۸۲</b>\n📦 اشتراک فعال   <b>۱۹۷</b>\n💳 رسید در انتظار   <b>۳</b>\n🎫 تیکت باز   <b>۲</b>\n\n💰 فروش کل   <b>۴۸,۵۰۰,۰۰۰</b>",
        kb: [["💳 رسیدها (۳)"], ["👥 کاربران", "📦 پلن‌ها"], ["📊 آمار", "📢 پیام همگانی"], ["‹ بازگشت"]] },
    ],
  },
};

export function BotPreviewSection() {
  const [flow, setFlow] = useState("welcome");
  const f = PREVIEW_FLOWS[flow];

  const md = (t) => {
    const parts = t.split(/(<b>[^<]*<\/b>|<code>[^<]*<\/code>|<i>[^<]*<\/i>)/g);
    return parts.map((p, i) => {
      if (p.startsWith("<b>")) return <b key={i} style={{ color: "#fff" }}>{p.slice(3, -4)}</b>;
      if (p.startsWith("<i>")) return <i key={i} style={{ opacity: .72 }}>{p.slice(3, -4)}</i>;
      if (p.startsWith("<code>")) return <code key={i} style={{
        background: "var(--hair-2)", padding: "1px 5px", borderRadius: 4,
        fontFamily: "var(--mono)", fontSize: 9.5, color: "#8FC1EE" }}>{p.slice(6, -7)}</code>;
      return p;
    });
  };

  return (
    <div className="fx-anim">
      <SectionHead title="پیش‌نمایش ربات"
        desc="آنچه مشتری در تلگرام می‌بیند. روی هر مرحله بزنید." />

      <div className="fx-g2 grid gap-6" style={{ gridTemplateColumns: "1fr 300px" }}>
        <div className="min-w-0">
          <div className="flex flex-col gap-2">
            {Object.entries(PREVIEW_FLOWS).map(([k, v]) => {
              const on = flow === k;
              return (
                <button title="انتخاب این مسیر" key={k} onClick={() => setFlow(k)}
                  className="flex items-center gap-3 px-4 py-3 rounded-xl text-right transition-all"
                  style={on
                    ? { background: "var(--accent-soft)", border: "1px solid var(--accent-edge)" }
                    : { background: "var(--surface)", border: "1px solid var(--border)" }}>
                  {on ? <Check size={14} style={{ color: "var(--accent-2)" }} />
                      : <Circle size={7} fill="var(--muted)" strokeWidth={0} />}
                  <span className="text-[14px] font-semibold"
                    style={{ color: on ? "var(--text)" : "var(--dim)" }}>{v.label}</span>
                </button>
              );
            })}
          </div>

          <InfoBox>
            متن‌ها را در بخش <b>«متن‌ها»</b> می‌توانید تغییر دهید.
            پیش‌نمایش، حالت پیش‌فرض را نشان می‌دهد.
          </InfoBox>
        </div>

        <div className="fx-hide-m">
          <div className="sticky top-24">
            <div style={{
              borderRadius: 28, padding: 9,
              background: "linear-gradient(160deg,#232B3C,#0C1119)",
              border: "1px solid var(--hair-3)",
              boxShadow: "0 20px 52px var(--scrim-2)",
            }}>
              <div className="flex justify-center mb-1.5">
                <div style={{ width: 46, height: 4, borderRadius: 99, background: "var(--hair-4)" }} />
              </div>
              <div style={{
                background: "#0E1621", borderRadius: 21, padding: "12px 10px",
                height: 420, overflowY: "auto", direction: "rtl",
              }}>
                <div className="flex items-center gap-2 pb-2.5 mb-3"
                  style={{ borderBottom: "1px solid var(--hair-2)" }}>
                  <div style={{
                    width: 26, height: 26, borderRadius: "50%",
                    background: "linear-gradient(135deg,var(--accent),var(--accent-2))",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 12, fontWeight: 800, color: "#06090F",
                  }}>N</div>
                  <div>
                    <div className="text-[13px] font-bold" style={{ color: "#fff" }}>ربات نکسورا</div>
                    <div className="text-[10.5px]" style={{ color: "#6B8299" }}>آنلاین</div>
                  </div>
                </div>

                {f.msgs.map((m, i) => (
                  <div key={i} className="mb-2.5 flex" style={{ justifyContent: m.me ? "flex-start" : "flex-end" }}>
                    <div style={{ maxWidth: "89%" }}>
                      <div style={{
                        background: m.me ? "#2B5278" : "#182533",
                        borderRadius: m.me ? "12px 12px 12px 4px" : "12px 12px 4px 12px",
                        padding: "8px 10px", fontSize: 10, lineHeight: 1.9,
                        color: "#E8EEF7", whiteSpace: "pre-wrap",
                      }}>
                        {m.img && (
                          <div style={{
                            height: 50, borderRadius: 7, marginBottom: 5,
                            background: "linear-gradient(135deg,#2A3A4A,#1A2530)",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: 8.5, color: "#6B8299",
                          }}>🧾 رسید</div>
                        )}
                        {md(m.t)}
                      </div>
                      {m.kb && (
                        <div className="mt-1.5 flex flex-col gap-1">
                          {m.kb.map((row, ri) => (
                            <div key={ri} className="flex gap-1">
                              {row.map((b, bi) => (
                                <div key={bi} style={{
                                  flex: 1, borderRadius: 8, padding: "7px 5px",
                                  fontSize: 8.8, textAlign: "center", fontWeight: 600,
                                  background: m.contact && ri === 0 ? "#2F5C42" : "#1F2C3A",
                                  border: `1px solid ${m.contact && ri === 0 ? "var(--ok-line)" : "var(--accent-halo)"}`,
                                  color: m.contact && ri === 0 ? "#6EE7B7" : "#8FC1EE",
                                }}>{b}</div>
                              ))}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
