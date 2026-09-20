/**
 * کانال — نوشتن، قالب‌بندی، عکس، و زمان‌بندی.
 *
 * برگه: docs/specs/2026-09-19-channel.md
 *
 * چرا بخشِ جدا و نه یک صفحه‌ی دیگر زیرِ «ربات»: آن فهرست چهارده قلم
 * دارد و مالک از شلوغی‌اش گفته. کانال کارِ دیگری است — محتوا، نه
 * پیکربندی.
 *
 * و چرا اعتبارسنجِ HTML این‌جا نیست: تلگرام پیامِ با تگِ خراب را
 * اصلاً نمی‌فرستد، و `bot/fmt.py` از قبل این را می‌سنجد. نسخه‌ی
 * جاواسکریپتیِ دوم یعنی روزی یکی اصلاح می‌شود و دیگری نه —
 * پرتکرارترین باگِ این مخزن. پس پیش‌نمایش از بک‌اند می‌پرسد.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertTriangle, Bold, Calendar, Check, Code, Eraser, Eye, EyeOff, Image as ImageIcon,
  Italic, Link2, Loader2, Quote, Send, Strikethrough, Trash2, Underline,
} from "lucide-react";

import { API_URL } from "../lib/constants";
import { errText, faNum } from "../lib/format";
import {
  EmptyState, InfoBox, Msg, PageSkeleton, SectionHead,
} from "../ui/index";
import { JalaliDate } from "../ui/jalali.jsx";
import { shrinkImage } from "../lib/image.js";

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

/* ── قالب‌بندی ──
   هر دکمه انتخابِ کاربر را در تگ می‌پیچد. تگ‌ها همان‌هایی‌اند که
   `fmt.ALLOWED` می‌پذیرد؛ بیشتر از این، تلگرام رد می‌کند. */

const MARKS = [
  { k: "b", icon: Bold, label: "پررنگ" },
  { k: "i", icon: Italic, label: "کج" },
  { k: "u", icon: Underline, label: "زیرخط" },
  { k: "s", icon: Strikethrough, label: "خط‌خورده" },
  { k: "code", icon: Code, label: "کد" },
  { k: "tg-spoiler", icon: EyeOff, label: "اسپویلر" },
  { k: "blockquote", icon: Quote, label: "نقلِ‌قول" },
];

/**
 * پیش‌نمایشِ تقریبیِ تلگرام.
 *
 * «تقریبی» عمدی است و همین‌جا نوشته می‌شود تا کسی رویش حساب باز
 * نکند: تصمیمِ نهایی با `fmt.check` در بک‌اند است. این‌جا فقط
 * تگ‌های شناخته‌شده به عنصر تبدیل می‌شوند تا مالک شکلِ کار را
 * ببیند.
 */
function preview(html) {
  const esc = (x) => x.replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  let out = esc(String(html || ""));
  const rules = [
    [/&lt;b&gt;([\s\S]*?)&lt;\/b&gt;/g, "<b>$1</b>"],
    [/&lt;i&gt;([\s\S]*?)&lt;\/i&gt;/g, "<i>$1</i>"],
    [/&lt;u&gt;([\s\S]*?)&lt;\/u&gt;/g, "<u>$1</u>"],
    [/&lt;s&gt;([\s\S]*?)&lt;\/s&gt;/g, "<s>$1</s>"],
    [/&lt;code&gt;([\s\S]*?)&lt;\/code&gt;/g, '<code class="ch-code">$1</code>'],
    [/&lt;tg-spoiler&gt;([\s\S]*?)&lt;\/tg-spoiler&gt;/g,
      '<span class="ch-spoiler">$1</span>'],
    [/&lt;blockquote&gt;([\s\S]*?)&lt;\/blockquote&gt;/g,
      '<span class="ch-quote">$1</span>'],
    [/&lt;a href="([^"]+)"&gt;([\s\S]*?)&lt;\/a&gt;/g,
      '<span class="ch-link">$2</span>'],
  ];
  for (const [re, rep] of rules) out = out.replace(re, rep);
  return out.replace(/\n/g, "<br/>");
}

/* ── قالب‌های آماده ──
   با دادهٔ خودِ پنل پر می‌شوند، نه متنِ عمومی. کادرِ خالی است که
   فلج می‌کند، نه کمبودِ ایده. */
function templates(cfg) {
  const brand = cfg.brand || "سرویس ما";
  const plans = (cfg.plans || []).slice(0, 4);
  const apps = (cfg.apps || []).filter((a) => a.name).slice(0, 4);
  const sup = cfg.support_username || "";

  const priceList = plans.length
    ? plans.map((p) => `• <b>${p.name}</b> — ${faNum(p.price)} تومان`).join("\n")
    : "• پلن‌هایتان را در بخش «پلن‌ها و قیمت» تعریف کنید";

  const appList = apps.length
    ? apps.map((a) => `• ${a.name}`).join("\n")
    : "• اپلیکیشن‌ها را در تنظیمات ربات اضافه کنید";

  return [
    { t: "معرفی پلن‌ها",
      b: `📦 <b>پلن‌های ${brand}</b>\n\n${priceList}\n\n`
       + "برای خرید، ربات را باز کنید 👇" },
    { t: "آموزش نصب",
      b: `📚 <b>نصب در سه قدم</b>\n\n<b>۱.</b> لینکِ اشتراکتان را کپی کنید\n`
       + `<b>۲.</b> یکی از این برنامه‌ها را نصب کنید:\n${appList}\n`
       + "<b>۳.</b> در برنامه «افزودن از کلیپ‌بورد» را بزنید\n\n"
       + "<blockquote>کمتر از دو دقیقه طول می‌کشد.</blockquote>" },
    { t: "تمدید",
      b: "⏰ <b>اشتراکتان دارد تمام می‌شود؟</b>\n\n"
       + "تمدید یک دکمه است و کانفیگِ فعلی‌تان <b>همان می‌ماند</b> — "
       + "لازم نیست چیزی را دوباره اضافه کنید." },
    { t: "اگر وصل نشد",
      b: "🔌 <b>وصل نمی‌شوید؟</b>\n\n"
       + "<b>۱.</b> یک سرورِ دیگر را از داخلِ برنامه امتحان کنید\n"
       + "<b>۲.</b> برنامه را کامل ببندید و دوباره باز کنید\n"
       + "<b>۳.</b> حجم و تاریخِ اشتراکتان را در ربات ببینید\n\n"
       + (sup ? `باز هم نشد؟ ${sup}` : "باز هم نشد؟ به پشتیبانی بگویید.") },
    { t: "قطعی موقت",
      b: "⚠️ <b>اختلالِ موقت</b>\n\n"
       + "چند دقیقه اختلالِ شبکه داشتیم و در حالِ رفعش هستیم.\n\n"
       + "<blockquote>اگر وصل نمی‌شوید، یک سرورِ دیگر را امتحان کنید.</blockquote>" },
    { t: "خبرِ تخفیف",
      b: "🎟 <b>کدِ تخفیف</b>\n\n"
       + "کدِ <code>CODE</code> را موقعِ خرید بزنید.\n\n"
       + "<b>فقط تا پایانِ هفته.</b>" },
  ];
}

export function ChannelSection({ password }) {
  const [data, setData] = useState(null);
  const [cfg, setCfg] = useState({});
  const [text, setText] = useState("");
  const [photo, setPhoto] = useState("");
  const [when, setWhen] = useState("");
  const [time, setTime] = useState("10:00");
  const [busy, setBusy] = useState(false);
  const [shrinking, setShrinking] = useState(false);
  const [msg, setMsg] = useState(null);
  const [problems, setProblems] = useState([]);
  const [showPrev, setShowPrev] = useState(true);
  const [addr, setAddr] = useState("");
  const [savingAddr, setSavingAddr] = useState(false);

  const boxRef = useRef(null);
  const fileRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const [ch, st] = await Promise.all([
        call("/api/admin/channel", password),
        call("/api/admin/bot/settings", password),
      ]);
      setData(ch);
      const s = (st.tenant?.settings && typeof st.tenant.settings === "object"
                 && !Array.isArray(st.tenant.settings)) ? st.tenant.settings : {};
      let plans = [];
      try {
        const pj = await call("/api/admin/bot/plans", password);
        plans = (pj.plans || []).filter((p) => !p.is_trial);
      } catch { plans = []; }
      setCfg({ ...s, plans });
      setAddr(s.channel_id || "");
    } catch (e) {
      setMsg({ t: "err", m: e.message });
      setData({ posts: [], target: "", limits: { text: 4096, caption: 1024 } });
    }
  }, [password]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (msg) { const x = setTimeout(() => setMsg(null), 5000); return () => clearTimeout(x); }
    return undefined;
  }, [msg]);

  const cap = photo ? (data?.limits?.caption || 1024) : (data?.limits?.text || 4096);
  const over = text.length > cap;

  /* سنجش از بک‌اند، با کمی مکث تا هر کلید یک درخواست نسازد */
  useEffect(() => {
    if (!text.trim()) { setProblems([]); return undefined; }
    const x = setTimeout(async () => {
      try {
        const j = await call("/api/admin/channel/check", password,
                             { method: "POST", body: { body: text, photo: !!photo } });
        setProblems(j.problems || []);
      } catch { /* سنجش که نشد، ارسال خودش جلویش را می‌گیرد */ }
    }, 500);
    return () => clearTimeout(x);
  }, [text, photo, password]);

  /** انتخاب را در تگ می‌پیچد؛ اگر چیزی انتخاب نشده، تگِ خالی می‌گذارد. */
  const wrap = (tag) => {
    const el = boxRef.current;
    if (!el) return;
    const a = el.selectionStart ?? text.length;
    const b = el.selectionEnd ?? text.length;
    const mid = text.slice(a, b);
    const next = `${text.slice(0, a)}<${tag}>${mid}</${tag}>${text.slice(b)}`;
    setText(next);
    requestAnimationFrame(() => {
      el.focus();
      const p = a + tag.length + 2 + mid.length;
      el.setSelectionRange(p, p);
    });
  };

  const addLink = () => {
    const url = window.prompt("نشانی لینک:", "https://");
    if (!url) return;
    const el = boxRef.current;
    const a = el?.selectionStart ?? text.length;
    const b = el?.selectionEnd ?? text.length;
    const mid = text.slice(a, b) || "این‌جا";
    setText(`${text.slice(0, a)}<a href="${url}">${mid}</a>${text.slice(b)}`);
  };

  const pickPhoto = async (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    setShrinking(true);
    try {
      const out = await shrinkImage(f, 1600, 0.82);
      setPhoto(out.data);
    } catch (e2) { setMsg({ t: "err", m: e2.message || "عکس خوانده نشد" }); }
    finally { setShrinking(false); }
  };

  const submit = async (schedule) => {
    if (busy || !text.trim()) return;
    setBusy(true);
    try {
      const at = schedule ? `${when} ${time}:00` : "";
      const j = await call("/api/admin/channel/post", password, {
        method: "POST",
        body: { body: text, ...(photo ? { photo } : {}), ...(at ? { at } : {}) },
      });
      setText(""); setPhoto(""); setWhen("");
      setMsg({ t: "ok", m: j.queued ? "برای زمانِ انتخابی گذاشته شد" : "در کانال منتشر شد" });
      load();
    } catch (e) { setMsg({ t: "err", m: e.message }); }
    finally { setBusy(false); }
  };

  const saveAddr = async () => {
    setSavingAddr(true);
    try {
      await call("/api/admin/bot/settings", password, {
        method: "PUT",
        body: { settings: { ...cfg, plans: undefined, channel_id: addr.trim() } },
      });
      setMsg({ t: "ok", m: "آدرس کانال ذخیره شد" });
      load();
    } catch (e) { setMsg({ t: "err", m: e.message }); }
    finally { setSavingAddr(false); }
  };

  const remove = async (pid) => {
    try {
      await call(`/api/admin/channel/post/${pid}`, password, { method: "DELETE" });
      load();
    } catch (e) { setMsg({ t: "err", m: e.message }); }
  };

  if (!data) return <PageSkeleton />;

  const tpl = templates(cfg);

  return (
    <div className="fx-anim">
      <SectionHead title="کانال"
        desc="نوشتن، قالب‌بندی و زمان‌بندیِ پستِ کانال — بدون بیرون‌رفتن از پنل." />

      <Msg msg={msg} />

      {/* آدرسِ کانال همین‌جا، نه در صفحه‌ی دیگر: کسی که می‌خواهد
          کانالش را وصل کند، این صفحه را باز کرده. */}
      <div className="fx-card p-4 mt-3">
        <div className="ch-addr">
          <div className="min-w-0">
            <div className="text-[13.5px] font-semibold text-white">آدرس کانال</div>
            <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
              یوزرنیمِ کانال، یا شناسه‌ی عددی اگر خصوصی است. ربات باید
              <b> در کانال ادمین باشد</b> — بدونِ دسترسیِ ارسال، تلگرام پست را
              رد می‌کند.
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <input className="fx-input ch-addr-in" value={addr} dir="ltr"
              placeholder="@my_channel" onChange={(e) => setAddr(e.target.value)} />
            <button className="fx-btn-g px-3 py-2 text-[13px]"
              onClick={saveAddr} disabled={savingAddr}>
              {savingAddr ? <Loader2 size={13} className="animate-spin" /> : "ذخیره"}
            </button>
          </div>
        </div>
        {!data.target && (
          <div className="mt-3">
            <InfoBox tone="warn">
              تا آدرسِ کانال را نگذارید، هیچ پستی نمی‌رود.
            </InfoBox>
          </div>
        )}
      </div>

      {/* قالب‌ها بالای کادرند، نه پایینش: کادرِ خالی است که فلج
          می‌کند، پس اولین چیزی که چشم می‌بیند باید یک نقطه‌ی شروع
          باشد. */}
      <div className="fx-card p-4 mt-3">
        <div className="text-[13px] mb-2" style={{ color: "var(--muted)" }}>
          از یکی از این‌ها شروع کنید — با پلن‌ها و اپ‌های خودتان پر شده‌اند:
        </div>
        <div className="ch-tpl">
          {tpl.map((x) => (
            <button key={x.t} type="button" className="ch-tpl-chip"
              onClick={() => setText((p) => (p.trim() ? `${p}\n\n${x.b}` : x.b))}>
              {x.t}
            </button>
          ))}
        </div>
      </div>

      <div className="ch-wrap mt-3">
      <div className="ch-grid grid gap-3">
        <div className="fx-card p-4">
          <div className="ch-tools">
            {MARKS.map((m) => (
              <button key={m.k} type="button" className="ch-tool"
                title={m.label} aria-label={m.label} onClick={() => wrap(m.k)}>
                <m.icon size={14} />
              </button>
            ))}
            <button type="button" className="ch-tool" title="لینک"
              aria-label="لینک" onClick={addLink}><Link2 size={14} /></button>
            <span className="ch-tool-sep" />
            <button type="button" className="ch-tool" title="عکس"
              aria-label="عکس" disabled={shrinking}
              onClick={() => fileRef.current?.click()}>
              {shrinking ? <Loader2 size={14} className="animate-spin" />
                         : <ImageIcon size={14} />}
            </button>
            <input ref={fileRef} type="file" accept="image/*" className="hidden"
              onChange={pickPhoto} />
            <button type="button" className="ch-tool" title="پاک‌کردن"
              aria-label="پاک‌کردن" onClick={() => { setText(""); setPhoto(""); }}>
              <Eraser size={14} />
            </button>
            <span className="flex-1" />
            <button type="button" className="ch-tool"
              title={showPrev ? "بستنِ پیش‌نمایش" : "نمایشِ پیش‌نمایش"}
              aria-label="پیش‌نمایش" onClick={() => setShowPrev((v) => !v)}>
              <Eye size={14} />
            </button>
          </div>

          {photo && (
            <div className="ch-photo">
              <img src={photo} alt="" />
              <button type="button" onClick={() => setPhoto("")}
                aria-label="برداشتنِ عکس"><Trash2 size={13} /></button>
            </div>
          )}

          <textarea ref={boxRef} className="fx-input ch-box" rows={10} dir="auto"
            value={text} onChange={(e) => setText(e.target.value)}
            placeholder={"متنِ پست…\n\nدکمه‌های بالا انتخابتان را قالب‌بندی می‌کنند."} />

          {/* سقف با وجودِ عکس عوض می‌شود: متنی که بدونِ عکس می‌رفت،
              با عکس رد می‌شود. */}
          <div className="ch-count">
            <span style={{ color: over ? "var(--danger)" : "var(--muted)" }}>
              {faNum(text.length)} / {faNum(cap)}
              {photo ? " (چون عکس دارد)" : ""}
            </span>
          </div>

          {problems.length > 0 && (
            <div className="ch-bad">
              <AlertTriangle size={13} />
              <span>{problems.slice(0, 3).join(" · ")}</span>
            </div>
          )}

          <div className="ch-actions">
            <button className="fx-btn px-4 py-2.5 text-[13px] flex items-center gap-1.5"
              disabled={busy || !text.trim() || over || problems.length > 0}
              onClick={() => submit(false)}>
              {busy ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
              همین حالا بفرست
            </button>

            <div className="ch-when">
              <Calendar size={13} style={{ color: "var(--muted)" }} />
              <JalaliDate value={when} onChange={setWhen} />
              <input className="fx-input ch-time" value={time} dir="ltr"
                onChange={(e) => setTime(e.target.value)} placeholder="10:00" />
              <button className="fx-btn-g px-3 py-2 text-[13px]"
                disabled={busy || !when || !text.trim() || over || problems.length > 0}
                onClick={() => submit(true)}>
                بگذار برای این زمان
              </button>
            </div>
          </div>
        </div>

        {showPrev && (
          <div className="fx-card p-4">
            <div className="text-[13px] mb-2" style={{ color: "var(--muted)" }}>
              پیش‌نمایشِ تقریبی
            </div>
            <div className="ch-prev">
              {photo && <img src={photo} alt="" className="ch-prev-img" />}
              {text.trim()
                // متن از خودِ مالک می‌آید و پیش از نمایش escape شده؛
                // فقط تگ‌های شناخته‌شده دوباره باز می‌شوند.
                ? <div dangerouslySetInnerHTML={{ __html: preview(text) }} />
                : <span style={{ color: "var(--muted)" }}>چیزی نوشته نشده</span>}
            </div>
            <div className="text-[11.5px] mt-2" style={{ color: "var(--muted)" }}>
              شکلِ نهایی را تلگرام تعیین می‌کند؛ این‌جا فقط تقریبی است.
            </div>
          </div>
        )}
      </div>

      </div>

      <SectionHead title="پست‌ها" desc="آنچه رفته، آنچه در نوبت است، و آنچه نرفته." />

      {!(data.posts || []).length ? (
        <EmptyState text="هنوز پستی نیست"
          hint="از بالا یکی از قالب‌ها را بردارید و اولین پست را بگذارید." />
      ) : (
        <div className="fx-card p-0 mt-3">
          {(data.posts || []).map((p) => (
            <div key={p.id} className="ch-row">
              <div className="min-w-0 flex-1">
                <div className="ch-row-body">
                  {String(p.body || "").replace(/<[^>]+>/g, "").slice(0, 140) || "—"}
                </div>
                <div className="ch-row-meta">
                  {p.status === "sent" && (
                    <span className="ch-tag ok"><Check size={11} /> رفت</span>
                  )}
                  {p.status === "queued" && (
                    <span className="ch-tag wait">در نوبت</span>
                  )}
                  {p.status === "failed" && (
                    <span className="ch-tag bad">
                      <AlertTriangle size={11} /> نرفت
                    </span>
                  )}
                  {p.photo && <span className="ch-tag">عکس دارد</span>}
                  <span>{p.sent_at || p.scheduled_at || p.created_at || ""}</span>
                </div>
                {p.error && <div className="ch-row-err">{p.error}</div>}
              </div>
              {p.status !== "sent" && (
                <button className="fx-ico-btn shrink-0" onClick={() => remove(p.id)}
                  title="حذف" aria-label="حذفِ پست"><Trash2 size={14} /></button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
