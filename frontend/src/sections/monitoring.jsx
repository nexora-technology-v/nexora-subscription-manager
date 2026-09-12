/**
 * مانیتورینگ سرور.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
import React, { useState, useEffect } from "react";
import {
  Activity, AlertTriangle, CheckCircle2, ChevronDown, HelpCircle, Loader2, Network, Package, RefreshCw, Save, Search, Server, ShieldCheck, TrendingUp, Users, XCircle, Zap,
} from "lucide-react";
import { API_URL } from "../lib/constants";
import { errText, esc0, faNum, fmtSize, fmtUptime, toFaDigits } from "../lib/format";
import { usePolling } from "../lib/hooks";
import {
  ConfirmModal, CountChip, EmptyState, Field, InfoBox, LongList, Msg, SectionHead, Segmented, Toggle,
} from "../ui/index";

export const LEVEL_STYLE = {
  ok: { c: "var(--ok)", bg: "rgba(52,211,153,.10)", bd: "rgba(52,211,153,.30)",
        label: "سالم", Icon: CheckCircle2 },
  warn: { c: "var(--warn)", bg: "rgba(251,191,36,.10)", bd: "rgba(251,191,36,.30)",
          label: "هشدار", Icon: AlertTriangle },
  crit: { c: "var(--danger)", bg: "rgba(248,113,113,.10)", bd: "rgba(248,113,113,.32)",
          label: "بحرانی", Icon: XCircle },
};

// بخش‌های سبک هر چند ثانیه تازه می‌شوند؛ سنگین‌ها (apt و journal)
// فقط با درخواست، چون هرکدام چند ثانیه طول می‌کشند.
export const LIGHT = "cpu,memory,disk,network,xray,services,ports,processes,connections";

export const HEAVY = "packages,security";

export function Gauge({ pct, color }) {
  const v = Math.max(0, Math.min(100, Number(pct) || 0));
  return (
    <div style={{ height: 6, borderRadius: 99, background: "rgba(255,255,255,.06)", overflow: "hidden" }}>
      <div style={{ width: `${v}%`, height: "100%", background: color, borderRadius: 99,
                    transition: "width .4s ease" }} />
    </div>
  );
}

export function MetricCard({ m }) {
  const [open, setOpen] = useState(false);
  const s = LEVEL_STYLE[m.level] || LEVEL_STYLE.ok;
  const val = m.value === null || m.value === undefined
    ? "—"
    : (typeof m.value === "number" ? faNum(m.value) : m.value);

  return (
    <div className="fx-card p-4" style={{ borderColor: m.level === "ok" ? "var(--border)" : s.bd }}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="text-[13px]" style={{ color: "var(--dim)" }}>{m.title}</span>
        <s.Icon size={14} style={{ color: s.c, flexShrink: 0 }} />
      </div>

      <div className="flex items-baseline gap-1.5 mb-2">
        <span className="text-[24px] font-bold" style={{ color: s.c, fontFamily: "var(--mono)" }}>
          {val}
        </span>
        {m.unit && <span className="text-[13px]" style={{ color: "var(--muted)" }}>{m.unit}</span>}
      </div>

      {m.pct !== null && m.pct !== undefined && <Gauge pct={m.pct} color={s.c} />}

      {errText(m.detail) && (
        <div className="text-[12px] mt-2 leading-relaxed" style={{ color: "var(--muted)" }}>
          {errText(m.detail)}
        </div>
      )}

      {(m.why || m.hint) && (
        <>
          <button onClick={() => setOpen(!open)}
            className="text-[12px] mt-2.5 flex items-center gap-1"
            style={{ color: "var(--accent-2)" }}>
            <HelpCircle size={11} /> {open ? "بستن" : "چرا مهم است؟"}
          </button>
          {open && (
            <div className="mt-2 rounded-xl p-3 text-[12px] leading-relaxed"
              style={{ background: "rgba(255,255,255,.02)", color: "var(--dim)" }}>
              {m.why}
              {m.hint && (
                <div className="mt-2 pt-2" style={{ borderTop: "1px solid var(--border)" }}>
                  <span style={{ color: "var(--muted)" }}>چه کار کنم: </span>
                  <span dir="auto" style={{ fontFamily: "var(--mono)", color: "var(--accent-2)" }}>
                    {m.hint}
                  </span>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export const RISK_META = {
  high: { c: "var(--danger)", t: "بالا", bg: "rgba(248,113,113,.10)" },
  medium: { c: "var(--warn)", t: "متوسط", bg: "rgba(251,191,36,.10)" },
  low: { c: "var(--ok)", t: "پایین", bg: "rgba(52,211,153,.10)" },
};

/**
 * پورت‌های باز.
 *
 * قبلاً همه‌ی پورت‌ها یکجا چاپ می‌شدند و روی سرور واقعی این فهرست
 * ده‌ها ردیف می‌شد — باید تا ته صفحه اسکرول می‌کردید تا بقیه‌ی
 * مانیتورینگ را ببینید. حالا پیش‌فرض فقط چیزی را نشان می‌دهد که
 * باید به آن رسیدگی کنید؛ بقیه پشت یک دکمه است.
 */
export function PortsCard({ ports }) {
  const [all, setAll] = useState(false);
  // فیلتر: روی سرور واقعی ده‌ها پورت هست و بدون فیلتر، پیداکردن
  // «آن یکی که یادم نیست چیست» یعنی چشم‌چرخاندن در کل فهرست
  const [risk, setRisk] = useState("all");
  const [scope, setScope] = useState("all");
  const [q, setQ] = useState("");
  if (!ports.length) return null;

  const high = ports.filter((p) => p.risk === "high");
  const med = ports.filter((p) => p.risk === "medium");
  const low = ports.filter((p) => p.risk !== "high" && p.risk !== "medium");

  const filtering = risk !== "all" || scope !== "all" || q.trim();
  const match = (p) => {
    if (risk === "high" && p.risk !== "high") return false;
    if (risk === "medium" && p.risk !== "medium") return false;
    if (risk === "low" && (p.risk === "high" || p.risk === "medium")) return false;
    if (scope === "public" && !p.public) return false;
    if (scope === "local" && p.public) return false;
    if (q.trim()) {
      const s = q.trim().toLowerCase();
      if (!`${p.port} ${p.proto} ${p.process} ${p.known}`.toLowerCase().includes(s))
        return false;
    }
    return true;
  };

  const risky = [...high, ...med];
  // با فیلتر فعال، همه‌ی نتایج نشان داده می‌شوند؛ بدون فیلتر، همان
  // رفتار قبلی: فقط چیزی که باید به آن رسیدگی شود
  const shown = filtering
    ? [...risky, ...low].filter(match)
    : (all ? [...risky, ...low] : risky.slice(0, 6));
  const hidden = filtering ? 0 : ports.length - shown.length;

  return (
    <div className="fx-card p-5 mb-4">
      <div className="flex items-center justify-between gap-3 mb-2 flex-wrap">
        <div className="text-[14px] font-semibold text-white flex items-center gap-2">
          <ShieldCheck size={15} style={{ color: "var(--accent-2)" }} /> پورت‌های باز
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <CountChip label="پرخطر" n={high.length} color="var(--danger)" />
          <CountChip label="متوسط" n={med.length} color="var(--warn)" />
          <CountChip label="عادی" n={low.length} color="var(--ok)" />
        </div>
      </div>

      <div className="flex items-center gap-2 flex-wrap mb-3">
        <Segmented value={risk} onChange={setRisk} items={[
          ["all", "همه"], ["high", "پرخطر"], ["medium", "متوسط"], ["low", "عادی"],
        ]} />
        <Segmented value={scope} onChange={setScope} items={[
          ["all", "هر دسترسی"], ["public", "اینترنت"], ["local", "فقط داخلی"],
        ]} />
        <div className="fx-search" style={{ width: 168 }}>
          <Search size={14} style={{ color: "var(--muted)" }} />
          <input value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="پورت یا پردازه..." />
        </div>
        {filtering && (
          <button onClick={() => { setRisk("all"); setScope("all"); setQ(""); }}
            className="fx-btn-g px-3 py-2 text-[13px]">پاک‌کردن فیلتر</button>
        )}
      </div>

      <p className="text-[13px] mb-3" style={{ color: "var(--muted)" }}>
        {risky.length === 0
          ? "هیچ پورت ناشناخته‌ای رو به اینترنت باز نیست — وضعیت تمیز است."
          : "هر پورتِ رو به اینترنت یک در است. این‌ها را بشناسید یا ببندید."}
      </p>

      {shown.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table className="fx-table">
            <thead>
              <tr><th>پورت</th><th>پروتکل</th><th>پردازه</th><th>دسترسی</th><th>ریسک</th></tr>
            </thead>
            <tbody>
              {shown.map((p, i) => {
                const r = RISK_META[p.risk] || RISK_META.low;
                return (
                  <tr key={`${p.port}-${p.proto}-${i}`}>
                    <td style={{ fontFamily: "var(--mono)", fontWeight: 600 }}>{p.port}</td>
                    <td style={{ color: "var(--muted)" }}>{p.proto}</td>
                    <td dir="ltr" style={{ color: "var(--dim)" }}>{p.process || "—"}</td>
                    <td style={{ color: p.public ? "var(--warn)" : "var(--muted)" }}>
                      {p.public ? "اینترنت" : "فقط داخلی"}
                    </td>
                    <td>
                      <span className="fx-pill" style={{ background: r.bg, color: r.c }}>
                        {r.t}{p.known ? ` · ${p.known}` : ""}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {(hidden > 0 || all) && (
        <button onClick={() => setAll(!all)}
          className="fx-btn-g w-full mt-3 py-2.5 text-[13px] flex items-center justify-center gap-1.5">
          {all
            ? <>کمتر <ChevronDown size={14} style={{ transform: "rotate(180deg)" }} /></>
            : <>نمایش همه‌ی {faNum(ports.length)} پورت <ChevronDown size={14} /></>}
        </button>
      )}
    </div>
  );
}

/**
 * اتصال‌های فعال.
 *
 * پورت باز می‌گوید چه دری باز است؛ این می‌گوید الان چه کسی از آن در
 * تو آمده. وقتی سرور کند می‌شود، اولین سؤال همین است: سهم هر IP چقدر
 * است و کدامشان غیرعادی است.
 */
export function ConnectionsCard({ conn, onBlock }) {
  if (!conn || !conn.total) {
    return (
      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2">
          <Activity size={15} style={{ color: "var(--accent-2)" }} /> اتصال‌های فعال
        </div>
        <p className="text-[13px]" style={{ color: "var(--muted)" }}>
          {conn ? "الان هیچ اتصال برقراری نیست." : "این بخش روی این سرور در دسترس نیست."}
        </p>
      </div>
    );
  }

  const max = conn.byIp[0]?.count || 1;

  return (
    <div className="fx-card p-5 mb-4" style={{ overflow: "hidden" }}>
      <div className="flex items-center justify-between gap-3 mb-2 flex-wrap">
        <div className="text-[14px] font-semibold text-white flex items-center gap-2">
          <Activity size={15} style={{ color: "var(--accent-2)" }} /> اتصال‌های فعال
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <CountChip label="اتصال" n={conn.total} color="var(--accent-2)" />
          <CountChip label="آی‌پی یکتا" n={conn.uniqueIps} color="var(--ok)" />
          {conn.tunnelConns > 0 && (
            <CountChip label="از تانل" n={conn.tunnelConns} color="var(--purple)" />
          )}
        </div>
      </div>

      {/* تانل‌ها جدا و *قبل* از هشدارها.
          سرور ایرانِ خودتان ذاتاً صدها اتصال دارد؛ اگر کنار بقیه
          بنشیند مدام شبیه سوءاستفاده به نظر می‌رسد. این‌جا صریح
          می‌گوید کدام‌ها زیرساخت خودتان‌اند. */}
      {conn.tunnels?.length > 0 && (
        <div className="rounded-xl p-3.5 mb-3"
          style={{ background: "rgba(167,139,250,.07)",
                   border: "1px solid rgba(167,139,250,.22)" }}>
          <div className="text-[13px] font-semibold mb-1.5" style={{ color: "var(--purple)" }}>
            {faNum(conn.tunnels.length)} اتصال از تانل‌های خودتان
          </div>
          {conn.tunnels.map((t) => (
            <div key={t.ip} className="text-[13px] mb-1"
              style={{ color: "var(--dim)", wordBreak: "break-all" }}>
              <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>{t.ip}</span>
              {" — "}{esc0(t.name)}{" · "}<b>{faNum(t.count)}</b> اتصال
              {" "}<span style={{ color: "var(--muted)" }}>({faNum(t.pct)}٪)</span>
            </div>
          ))}
          <div className="text-[12px] mt-2 leading-relaxed" style={{ color: "var(--muted)" }}>
            این‌ها ترافیک مشتری‌های شما هستند که از سرور ایران رد می‌شوند —
            طبیعی است و در هشدارهای «مصرف غیرعادی» حساب نمی‌شوند.
          </div>
        </div>
      )}

      {conn.heavy?.length > 0 && (
        <div className="rounded-xl p-3.5 mb-3"
          style={{ background: "rgba(251,191,36,.07)", border: "1px solid rgba(251,191,36,.22)" }}>
          <div className="text-[13px] font-semibold mb-1.5" style={{ color: "var(--warn)" }}>
            {faNum(conn.heavy.length)} آی‌پی سهم غیرعادی دارد
          </div>
          {conn.heavy.map((h) => (
            <div key={h.ip}
              className="flex items-center justify-between gap-3 py-2 flex-wrap">
              <div className="text-[13px] min-w-0"
                style={{ color: "var(--dim)", wordBreak: "break-all" }}>
                <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>{h.ip}</span>
                {" — "}<b>{faNum(h.count)}</b> اتصال ({faNum(h.pct)}٪ کل)
              </div>
              <button onClick={() => onBlock && onBlock(h)}
                className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
                <XCircle size={13} /> بستن این آی‌پی
              </button>
            </div>
          ))}
          <div className="text-[12px] mt-2 leading-relaxed" style={{ color: "var(--muted)" }}>
            معمولاً یعنی یک اشتراک بین چند نفر پخش شده یا کسی دارد سرور را اسکن می‌کند.
            اگر مشتری خودتان است، محدودیت <b>IP هم‌زمان</b> آن پلن را کم کنید؛
            اگر ناشناس است، ببندیدش.
          </div>
        </div>
      )}

      <div className="mb-1 text-[13px]" style={{ color: "var(--muted)" }}>
        پرمصرف‌ترین آی‌پی‌ها
      </div>
      <LongList items={conn.byIp} initial={8} label="آی‌پی" searchable
        match={(x, q) => String(x.ip).includes(q)}>
        {(x) => (
        <div key={x.ip} className="flex items-center gap-3 py-1.5">
          {/* آدرس IPv6 سه برابر IPv4 است و با عرض ثابت از کادر
              می‌زد بیرون. کوتاه می‌شود و کاملش در tooltip می‌ماند. */}
          <span dir="ltr" className="text-[13px] shrink-0" title={x.ip}
            style={{ fontFamily: "var(--mono)", color: "var(--dim)",
                     maxWidth: 150, overflow: "hidden",
                     textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {x.ip}
          </span>
          <div className="flex-1 rounded-full overflow-hidden" style={{ height: 7, background: "var(--surface-3)" }}>
            <div style={{
              width: `${Math.max(4, (x.count / max) * 100)}%`, height: "100%",
              background: x.pct >= 15 ? "var(--warn)" : "var(--accent-2)",
            }} />
          </div>
          <span className="text-[13px] shrink-0" style={{ fontFamily: "var(--mono)", color: "var(--dim)", width: 58, textAlign: "left" }}>
            {faNum(x.count)}
          </span>
        </div>
        )}
      </LongList>

      {conn.byPort?.length > 0 && (
        <div className="mt-4 pt-3.5" style={{ borderTop: "1px solid var(--border)" }}>
          <div className="text-[13px] mb-2" style={{ color: "var(--muted)" }}>
            پرترافیک‌ترین پورت‌ها
          </div>
          <div className="flex gap-1.5 flex-wrap">
            {conn.byPort.map((p) => (
              <span key={p.port} className="fx-pill"
                style={{ background: "var(--surface-3)", color: "var(--dim)" }}>
                <span style={{ fontFamily: "var(--mono)" }}>{p.port}</span>
                {" · "}{faNum(p.count)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * نمودار تاریخچه‌ی مصرف.
 *
 * SVG خام و بدون کتابخانه — یک نمودار ساده ارزش ۱۲۰ کیلوبایت وابستگی
 * را ندارد. رنگ تنها حامل معنا نیست: هر سری برچسب و عدد جداگانه دارد،
 * چون قواعد دسترسی‌پذیری می‌گویند نباید فقط با رنگ تفکیک شود.
 */
export function UsageChart({ series, color, label, unit, height = 74 }) {
  const [hover, setHover] = useState(null);
  const raw = series.filter((v) => typeof v === "number");
  if (raw.length < 2) {
    return (
      <div className="text-[13px] py-6 text-center" style={{ color: "var(--muted)" }}>
        هنوز داده‌ی کافی جمع نشده — هر ۵ دقیقه یک نمونه ذخیره می‌شود.
      </div>
    );
  }

  // ۲۸۸ نقطه در چند صد پیکسل فقط دندانه‌ی بی‌معنا می‌سازد. میانگین
  // هر دسته را می‌گیریم تا روند دیده شود، نه نویز.
  const CAP = 64;
  const pts = raw.length <= CAP ? raw : (() => {
    const size = Math.ceil(raw.length / CAP);
    const out = [];
    for (let i = 0; i < raw.length; i += size) {
      const chunk = raw.slice(i, i + size);
      out.push(chunk.reduce((a, b) => a + b, 0) / chunk.length);
    }
    return out;
  })();

  const max = Math.max(...pts, 1);
  // کف نمودار صفر است تا نسبت‌ها صادقانه دیده شوند، ولی برچسب
  // «کمینه» باید کمینه‌ی واقعی داده باشد نه صفرِ کف
  const dataMin = Math.min(...raw);
  const min = 0;
  const span = max - min || 1;
  const W = 100;
  const xy = (v, i) => [
    (i / (pts.length - 1)) * W,
    height - ((v - min) / span) * (height - 8) - 4,
  ];
  const line = pts.map((v, i) => xy(v, i).join(",")).join(" ");
  const area = `0,${height} ${line} ${W},${height}`;
  const cur = hover !== null ? pts[hover] : pts[pts.length - 1];

  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5">
        <span className="text-[13px]" style={{ color: "var(--muted)" }}>{label}</span>
        <span className="text-[16px] font-bold" style={{ color, fontFamily: "var(--mono)" }}>
          {faNum(Math.round(cur))}
          <span className="text-[12px] font-normal mr-1" style={{ color: "var(--muted)" }}>{unit}</span>
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${height}`} preserveAspectRatio="none"
        style={{ width: "100%", height, display: "block" }}
        role="img" aria-label={`${label}: بیشینه ${Math.round(max)} ${unit}`}
        onMouseLeave={() => setHover(null)}
        onMouseMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          const p = (e.clientX - r.left) / r.width;
          setHover(Math.min(pts.length - 1, Math.max(0, Math.round(p * (pts.length - 1)))));
        }}>
        <polygon points={area} fill={color} opacity="0.13" />
        <polyline points={line} fill="none" stroke={color} strokeWidth="1.4"
          vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
        {hover !== null && (
          <circle cx={xy(pts[hover], hover)[0]} cy={xy(pts[hover], hover)[1]}
            r="2.5" fill={color} vectorEffect="non-scaling-stroke" />
        )}
      </svg>
      <div className="flex justify-between text-[12px] mt-1" style={{ color: "var(--muted)" }}>
        <span>کمینه {faNum(Math.round(dataMin))}</span>
        <span>بیشینه {faNum(Math.round(Math.max(...raw)))}</span>
      </div>
    </div>
  );
}

/** نوار ۲۴ ساعته — کدام ساعت شبانه‌روز شلوغ است و کدام خلوت. */
export function HourStrip({ hourly, quietest, busiest }) {
  if (!hourly?.length) return null;
  const max = Math.max(...hourly.map((h) => h.conn), 1);
  const byHour = Object.fromEntries(hourly.map((h) => [h.hour, h]));

  return (
    <div>
      <div className="flex items-end gap-[2px]" style={{ height: 52 }}>
        {Array.from({ length: 24 }, (_, h) => {
          const d = byHour[h];
          const v = d ? d.conn : 0;
          const isQuiet = h === quietest;
          const isBusy = h === busiest;
          return (
            <div key={h} className="flex-1 rounded-t-[3px]" title={
              d ? `ساعت ${h} — میانگین ${Math.round(v)} اتصال` : `ساعت ${h} — داده‌ای نیست`}
              style={{
                height: `${Math.max(3, (v / max) * 100)}%`,
                background: isBusy ? "var(--danger)"
                  : isQuiet ? "var(--ok)"
                    : d ? "var(--accent-2)" : "var(--surface-3)",
                opacity: d ? (isBusy || isQuiet ? 1 : 0.55) : 0.35,
              }} />
          );
        })}
      </div>
      <div className="flex justify-between text-[12px] mt-1.5" style={{ color: "var(--muted)" }}>
        <span>۰۰</span><span>۰۶</span><span>۱۲</span><span>۱۸</span><span>۲۳</span>
      </div>
    </div>
  );
}

export function UsageHistoryCard({ password }) {
  const [d, setD] = useState(null);

  useEffect(() => {
    let alive = true;
    fetch(`${API_URL}/api/admin/usage-history?hours=24`, {
      headers: { "X-Admin-Password": password },
    }).then((r) => r.json()).then((j) => alive && setD(j)).catch(() => alive && setD({}));
    return () => { alive = false; };
  }, [password]);

  if (!d) return null;
  const s = d.samples || [];

  return (
    <div className="fx-card p-5 mb-4">
      <div className="flex items-center justify-between gap-3 mb-1 flex-wrap">
        <div className="text-[14px] font-semibold text-white flex items-center gap-2">
          <TrendingUp size={15} style={{ color: "var(--accent-2)" }} /> تاریخچه‌ی مصرف
        </div>
        <span className="text-[13px]" style={{ color: "var(--muted)" }}>
          {faNum(d.count || 0)} نمونه از ۲۴ ساعت گذشته
        </span>
      </div>
      <p className="text-[13px] mb-4" style={{ color: "var(--muted)" }}>
        هر ۵ دقیقه یک نمونه. تا وقتی چند ساعت جمع نشود، الگو معنا ندارد.
      </p>

      {s.length >= 2 ? (
        <>
          <div className="fx-g3 grid grid-cols-2 gap-5 mb-5">
            <UsageChart series={s.map((x) => x.conn)} color="var(--accent-2)"
              label="اتصال‌های هم‌زمان" unit="اتصال" />
            <UsageChart series={s.map((x) => x.cpu)} color="var(--warn)"
              label="پردازنده" unit="٪" />
          </div>

          <div className="pt-4" style={{ borderTop: "1px solid var(--border)" }}>
            <div className="text-[13px] mb-2" style={{ color: "var(--muted)" }}>
              میانگین هر ساعت شبانه‌روز
            </div>
            <HourStrip hourly={d.hourly} quietest={d.quietestHour} busiest={d.busiestHour} />

            {d.quietestHour !== null && d.quietestHour !== undefined && (
              <div className="flex gap-3 flex-wrap mt-3 text-[13px]">
                <span style={{ color: "var(--ok)" }}>
                  ● خلوت‌ترین ساعت: <b>{faNum(d.quietestHour)}</b>
                </span>
                <span style={{ color: "var(--danger)" }}>
                  ● شلوغ‌ترین ساعت: <b>{faNum(d.busiestHour)}</b>
                </span>
              </div>
            )}
            {d.quietestHour !== null && d.quietestHour !== undefined && (
              <InfoBox>
                بر اساس همین داده، ساعت <b>{faNum(d.quietestHour)}</b> کم‌مصرف‌ترین
                زمان سرور شماست — اگر «تازه‌سازی خودکار سرویس» را روشن کردید،
                همین ساعت را بگذارید تا کسی قطعی را حس نکند.
              </InfoBox>
            )}
          </div>
        </>
      ) : (
        <div className="text-[13px] py-6 text-center" style={{ color: "var(--muted)" }}>
          هنوز نمونه‌ای ذخیره نشده. چند ساعت بعد از به‌روزرسانی دوباره سر بزنید.
        </div>
      )}
    </div>
  );
}

/** پرمصرف‌ترین مشتری‌ها — بر اساس ترافیک واقعی پنل، نه شمارش اتصال. */
export function TopClientsCard({ password }) {
  const [d, setD] = useState(null);
  const [all, setAll] = useState(false);

  useEffect(() => {
    let alive = true;
    fetch(`${API_URL}/api/admin/top-clients?limit=25`, {
      headers: { "X-Admin-Password": password },
    }).then((r) => r.json()).then((j) => alive && setD(j)).catch(() => alive && setD({ ready: false }));
    return () => { alive = false; };
  }, [password]);

  if (!d) return null;

  if (!d.ready) {
    return (
      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-1 flex items-center gap-2">
          <Users size={15} style={{ color: "var(--accent-2)" }} /> پرمصرف‌ترین مشتری‌ها
        </div>
        <p className="text-[13px]" style={{ color: "var(--muted)" }}>
          {d.error || "دیتابیس پنل در دسترس نیست."}
        </p>
      </div>
    );
  }

  const list = all ? d.clients : (d.clients || []).slice(0, 6);
  const max = d.clients?.[0]?.usedGB || 1;

  return (
    <div className="fx-card p-5 mb-4">
      <div className="flex items-center justify-between gap-3 mb-1 flex-wrap">
        <div className="text-[14px] font-semibold text-white flex items-center gap-2">
          <Users size={15} style={{ color: "var(--accent-2)" }} /> پرمصرف‌ترین مشتری‌ها
        </div>
        <span className="text-[13px]" style={{ color: "var(--muted)" }}>
          {faNum(d.totalClients || 0)} کانفیگ · {faNum(d.totalUsedGB || 0)} گیگ کل
        </span>
      </div>
      <p className="text-[13px] mb-3" style={{ color: "var(--muted)" }}>
        بر اساس ترافیک واقعی پنل — این می‌گوید کدام <b>مشتری</b> بار می‌آورد،
        نه فقط کدام آی‌پی.
      </p>

      {!list.length ? (
        <EmptyState icon={Users} text="هنوز مصرفی ثبت نشده"
          hint="کانفیگ‌ها ساخته شده‌اند ولی هنوز ترافیکی از آن‌ها عبور نکرده." />
      ) : list.map((c) => (
        <div key={c.email} className="py-2">
          <div className="flex items-baseline justify-between gap-2 mb-1 flex-wrap">
            <span dir="ltr" className="text-[13px] truncate"
              style={{ fontFamily: "var(--mono)", color: "var(--dim)", maxWidth: "60%" }}>
              {c.email}
            </span>
            <span className="text-[13px]" style={{ color: "var(--dim)" }}>
              <b style={{ fontFamily: "var(--mono)" }}>{faNum(c.usedGB)}</b> گیگ
              {c.quotaGB ? <span style={{ color: "var(--muted)" }}> از {faNum(c.quotaGB)}</span> : null}
              <span style={{ color: "var(--muted)" }}> · {faNum(c.pctOfAll)}٪ کل</span>
            </span>
          </div>
          <div className="rounded-full overflow-hidden" style={{ height: 7, background: "var(--surface-3)" }}>
            <div style={{
              width: `${Math.max(3, (c.usedGB / max) * 100)}%`, height: "100%",
              background: !c.enable ? "var(--muted)"
                : (c.pctOfQuota !== null && c.pctOfQuota >= 90) ? "var(--danger)"
                  : c.pctOfAll >= 20 ? "var(--warn)" : "var(--accent-2)",
            }} />
          </div>
          {(!c.enable || (c.pctOfQuota !== null && c.pctOfQuota >= 90)) && (
            <div className="text-[12px] mt-1" style={{ color: !c.enable ? "var(--muted)" : "var(--danger)" }}>
              {!c.enable ? "غیرفعال" : `${faNum(c.pctOfQuota)}٪ از حجمش مصرف شده — نزدیک تمام‌شدن`}
            </div>
          )}
        </div>
      ))}

      {(d.clients || []).length > 6 && (
        <button onClick={() => setAll(!all)}
          className="fx-btn-g w-full mt-3 py-2.5 text-[13px] flex items-center justify-center gap-1.5">
          {all ? "کمتر" : `نمایش همه‌ی ${faNum(d.clients.length)} مشتری`}
          <ChevronDown size={14} style={all ? { transform: "rotate(180deg)" } : undefined} />
        </button>
      )}
    </div>
  );
}

export const WEEKDAYS = [["دوشنبه", 0], ["سه‌شنبه", 1], ["چهارشنبه", 2],
                  ["پنجشنبه", 3], ["جمعه", 4], ["شنبه", 5], ["یکشنبه", 6]];

/**
 * نگهداری خودکار.
 *
 * ری‌استارت Xray حدود یک ثانیه قطعی دارد؛ ریبوت سرور یک تا دو دقیقه.
 * برای همین ریبوت پشت یک تایید جداگانه است — یک تیک اشتباهی نباید
 * بتواند سرور فروش را وسط شب بخواباند.
 */
export function MaintenanceCard({ password }) {
  const [m, setM] = useState(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);
  const [confirmReboot, setConfirmReboot] = useState(false);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/maintenance`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setM(d);
    } catch { setM({ error: true }); }
  };
  useEffect(() => { load(); }, [password]);
  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(t); } }, [msg]);

  if (!m) return null;

  const up = (patch) => setM({ ...m, ...patch });

  const save = async (extra = {}) => {
    setSaving(true);
    try {
      const body = { ...m, ...extra };
      const res = await fetch(`${API_URL}/api/admin/maintenance`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify(body),
      });
      const j = await res.json().catch(() => ({}));
      if (res.ok) { setM(j); setMsg({ t: "ok", m: "زمان‌بندی ذخیره شد" }); await load(); }
      else setMsg({ t: "err", m: errText(j.detail, "ذخیره ناموفق") });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setSaving(false); }
  };

  const runNow = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/maintenance/run-now`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ action: "xray" }),
      });
      const j = await res.json().catch(() => ({}));
      setMsg({ t: j.ok ? "ok" : "err", m: j.note || errText(j.detail, "انجام شد") });
      await load();
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setSaving(false); }
  };

  const isReboot = m.action === "reboot";

  return (
    <div className="fx-card p-5 mb-4">
      <div className="flex items-center justify-between gap-3 mb-1 flex-wrap">
        <div className="text-[14px] font-semibold text-white flex items-center gap-2">
          <RefreshCw size={15} style={{ color: "var(--accent-2)" }} /> تازه‌سازی خودکار سرویس
        </div>
        <Toggle checked={!!m.enabled} onChange={(v) => up({ enabled: v })}
          label={m.enabled ? "روشن" : "خاموش"} />
      </div>

      {/* توضیح باید به سؤال واقعی مدیر جواب بدهد — «این به چه دردم
          می‌خورد؟» — نه اینکه فقط بگوید چه کاری انجام می‌دهد. */}
      <p className="text-[13px] mb-3 leading-relaxed" style={{ color: "var(--dim)" }}>
        Xray هرچه بیشتر کار کند، حافظه‌ی بیشتری نگه می‌دارد و نشست‌های
        قطع‌شده در آن جمع می‌شوند. بعد از چند هفته، همین باعث می‌شود
        اتصال‌ها کند و بی‌دلیل قطع شوند.
      </p>
      <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
        یک ری‌استارت کوتاه در ساعتی که کسی آنلاین نیست، این را پاک
        می‌کند. <b>اگر سرورتان مشکلی ندارد، لازم نیست روشنش کنید.</b>
      </p>

      <Msg msg={msg} />

      <div className="fx-g3 grid grid-cols-2 gap-2.5 mb-3">
        {[["ری‌استارت Xray", "xray", "حدود ۱ ثانیه قطعی", "var(--ok)"],
          ["ریبوت کامل سرور", "reboot", "۱ تا ۲ دقیقه قطعی", "var(--warn)"]].map(
          ([label, val, note, col]) => {
            const on = m.action === val;
            return (
              <button key={val} onClick={() => up({ action: val })}
                className="p-3.5 rounded-xl text-right transition-all"
                style={{
                  background: on ? "var(--accent-soft)" : "var(--surface-3)",
                  border: `1px solid ${on ? "var(--accent-2)" : "var(--border)"}`,
                }}>
                <div className="text-[13px] font-bold mb-1"
                  style={{ color: on ? "var(--accent-2)" : "var(--dim)" }}>{label}</div>
                <div className="text-[12px]" style={{ color: col }}>{note}</div>
              </button>
            );
          })}
      </div>

      <div className="fx-g3 grid grid-cols-2 gap-3 mb-3">
        <Field label="ساعت" hint="به وقت سرور">
          <input className="fx-input" dir="ltr" type="number" min="0" max="23"
            value={m.hour ?? 5} onChange={(e) => up({ hour: Number(e.target.value) })}
            style={{ fontFamily: "var(--mono)" }} />
        </Field>
        <Field label="دقیقه">
          <input className="fx-input" dir="ltr" type="number" min="0" max="59"
            value={m.minute ?? 0} onChange={(e) => up({ minute: Number(e.target.value) })}
            style={{ fontFamily: "var(--mono)" }} />
        </Field>
      </div>

      <div className="mb-3">
        <label className="text-[12px] mb-1.5 block" style={{ color: "var(--muted)" }}>
          روزها — چیزی انتخاب نکنید یعنی هر روز
        </label>
        <div className="flex gap-1.5 flex-wrap">
          {WEEKDAYS.map(([label, d]) => {
            const on = (m.days || []).includes(d);
            return (
              <button key={d}
                onClick={() => up({ days: on ? m.days.filter((x) => x !== d)
                                              : [...(m.days || []), d] })}
                className="px-3 py-2 rounded-lg text-[13px]"
                style={{
                  background: on ? "var(--accent-soft)" : "var(--surface-3)",
                  border: `1px solid ${on ? "var(--accent-2)" : "var(--border)"}`,
                  color: on ? "var(--accent-2)" : "var(--muted)",
                }}>{label}</button>
            );
          })}
        </div>
      </div>

      <label className="flex items-center gap-2 text-[13px] cursor-pointer mb-3"
        style={{ color: "var(--dim)" }}>
        <input type="checkbox" checked={!!m.skipIfBusy}
          onChange={(e) => up({ skipIfBusy: e.target.checked })}
          style={{ accentColor: "var(--accent)" }} />
        اگر بیش از {faNum(m.busyThreshold || 20)} اتصال فعال بود، آن شب رد شود
      </label>

      {isReboot && (
        <InfoBox tone="warn">
          ریبوت کامل یعنی <b>همه‌ی مشتری‌ها یک تا دو دقیقه قطع می‌شوند</b>.
          برای نشتی حافظه معمولاً ری‌استارت Xray کافی است.
          <label className="flex items-center gap-2 mt-2.5 cursor-pointer">
            <input type="checkbox" checked={confirmReboot}
              onChange={(e) => setConfirmReboot(e.target.checked)}
              style={{ accentColor: "var(--warn)" }} />
            می‌دانم و ریبوت خودکار را می‌خواهم
          </label>
        </InfoBox>
      )}

      <div className="flex items-center gap-2 mt-4 flex-wrap">
        <button onClick={() => save({ confirmedReboot: isReboot ? confirmReboot : m.confirmedReboot })}
          disabled={saving || (m.enabled && isReboot && !confirmReboot)}
          className="fx-btn px-4 py-2.5 text-[13px] flex items-center gap-1.5">
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} ذخیره
        </button>
        <button onClick={runNow} disabled={saving}
          className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
          <Zap size={13} /> همین حالا Xray را تازه کن
        </button>
      </div>

      <div className="mt-3.5 pt-3 text-[13px] leading-relaxed"
        style={{ borderTop: "1px solid var(--border)", color: "var(--muted)" }}>
        {m.enabled && m.nextRun
          ? <>اجرای بعدی: <b style={{ color: "var(--dim)" }}>{m.nextRun.replace("T", " ساعت ")}</b></>
          : "زمان‌بندی خاموش است."}
        {m.lastResult && <div className="mt-1">آخرین بار: {m.lastResult}</div>}
        {typeof m.activeConnections === "number" && (
          <div className="mt-1">الان {faNum(m.activeConnections)} اتصال فعال است.</div>
        )}
      </div>
    </div>
  );
}

export function MonitorSection({ password }) {
  const [d, setD] = useState(null);
  const [heavy, setHeavy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [heavyBusy, setHeavyBusy] = useState(false);
  const [live, setLive] = useState(true);
  const [err, setErr] = useState("");
  // بستن آی‌پی یک عمل برگشت‌پذیر ولی مؤثر است — بدون تایید صریح
  // انجام نمی‌شود، چون ممکن است همان آی‌پی مشتری واقعی باشد
  const [blockTarget, setBlockTarget] = useState(null);
  const [blockMsg, setBlockMsg] = useState(null);

  useEffect(() => {
    if (blockMsg) { const t = setTimeout(() => setBlockMsg(null), 5000); return () => clearTimeout(t); }
  }, [blockMsg]);

  const doBlock = async (ip) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/firewall/block-ip`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ ip, comment: "اتصال غیرعادی — از مانیتورینگ" }),
      });
      const j = await res.json().catch(() => ({}));
      setBlockMsg(res.ok
        ? { t: "ok", m: `${ip} بسته شد` }
        : { t: "err", m: errText(j.detail, "بستن ناموفق بود") });
    } catch {
      setBlockMsg({ t: "err", m: "اتصال برقرار نشد" });
    }
  };

  const get = async (sections) => {
    const r = await fetch(`${API_URL}/api/admin/monitor?sections=${sections}`,
      { headers: { "X-Admin-Password": password } });
    const j = await r.json();
    if (!r.ok) throw new Error(errText(j.detail, "خطای سرور"));
    return j;
  };

  const load = async () => {
    try { setD(await get(LIGHT)); setErr(""); }
    catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const loadHeavy = async () => {
    setHeavyBusy(true);
    try { setHeavy(await get(HEAVY)); }
    catch { /* بی‌صدا */ }
    finally { setHeavyBusy(false); }
  };

  useEffect(() => { load(); }, [password]);
  usePolling(load, live ? 8000 : 0, [password]);

  if (loading) {
    return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;
  }

  const sec = d?.sections || {};
  const metrics = [...(d?.metrics || []), ...(heavy?.metrics || [])];
  const worst = heavy && heavy.level === "crit" ? "crit"
    : (d?.level === "crit" ? "crit"
      : (d?.level === "warn" || heavy?.level === "warn" ? "warn" : "ok"));
  const s = LEVEL_STYLE[worst] || LEVEL_STYLE.ok;
  const problems = metrics.filter((m) => m.level !== "ok");

  return (
    <div className="fx-anim">
      <SectionHead title="مانیتورینگ سرور"
        desc="وضعیت زنده‌ی سروری که پنل رویش نصب است — با توضیح اینکه هر عدد از کجا به بعد خطرناک می‌شود."
        action={
          <div className="flex items-center gap-2">
            <button onClick={() => setLive(!live)}
              className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full"
                style={{ background: live ? "var(--ok)" : "var(--muted)" }} />
              {live ? "زنده" : "متوقف"}
            </button>
            <button onClick={load} className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
              <RefreshCw size={13} /> تازه‌سازی
            </button>
          </div>
        } />

      {err && <InfoBox tone="warn">{err}</InfoBox>}

      {/* حکم کلی */}
      <div className="fx-card p-5 mb-4" style={{ background: s.bg, borderColor: s.bd }}>
        <div className="flex items-start gap-3 flex-wrap">
          <s.Icon size={22} style={{ color: s.c, flexShrink: 0 }} className="mt-0.5" />
          <div className="min-w-0 flex-1">
            <div className="text-[16px] font-bold" style={{ color: s.c }}>
              {worst === "ok" ? "سرور سالم است" : (d?.headline || s.label)}
            </div>
            <div className="text-[13px] mt-1" style={{ color: "var(--dim)" }}>
              {problems.length === 0
                ? "هیچ موردی نیاز به رسیدگی ندارد."
                : problems.map((p) => p.title).join(" · ")}
            </div>
            <div className="text-[12px] mt-2.5 flex items-center gap-3 flex-wrap"
              style={{ color: "var(--muted)" }}>
              <span>{d?.host?.hostname || "—"}</span>
              <span style={{ opacity: 0.4 }}>•</span>
              <span>روشن از {fmtUptime(d?.host?.uptime)}</span>
              <span style={{ opacity: 0.4 }}>•</span>
              <span>{faNum(d?.host?.cores || 0)} هسته</span>
              <span style={{ opacity: 0.4 }}>•</span>
              <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>{d?.host?.kernel}</span>
              <span style={{ opacity: 0.4 }}>•</span>
              {/* faNum روی ساعت «ناعدد» می‌داد — رشته‌ی زمان عدد نیست */}
              <span>آخرین بررسی {toFaDigits(d?.at?.slice(11) || "—")}</span>
            </div>
          </div>
        </div>
      </div>

      {/* سنجه‌ها */}
      <div className="fx-g4 grid grid-cols-3 gap-3 mb-4">
        {(d?.metrics || []).map((m) => <MetricCard key={m.key} m={m} />)}
      </div>

      {/* شبکه */}
      {sec.network && sec.network[0]?.extra?.interfaces?.length > 0 && (
        <div className="fx-card p-5 mb-4">
          <div className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
            <Network size={15} style={{ color: "var(--accent-2)" }} /> کارت‌های شبکه
          </div>
          {sec.network[0].extra.interfaces.map((i) => (
            <div key={i.name} className="flex items-center justify-between gap-3 py-2 flex-wrap"
              style={{ borderBottom: "1px solid var(--border)" }}>
              <span className="text-[13px] font-semibold text-white" dir="ltr">{i.name}</span>
              <div className="flex items-center gap-4 text-[13px]">
                <span style={{ color: "var(--ok)" }}>↓ {fmtSize(i.rx)}/s</span>
                <span style={{ color: "var(--accent-2)" }}>↑ {fmtSize(i.tx)}/s</span>
                <span style={{ color: "var(--muted)" }}>
                  کل: {fmtSize(i.rxTotal)} / {fmtSize(i.txTotal)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="fx-g3 grid grid-cols-2 gap-3 mb-4">
        {/* سرویس‌ها */}
        {sec.services?.length > 0 && (
          <div className="fx-card p-5">
            <div className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
              <Server size={15} style={{ color: "var(--accent-2)" }} /> سرویس‌ها
            </div>
            {/* یک سرور معمولی ده‌ها سرویس دارد. نشان‌دادن همه‌شان یعنی
                کارت به اندازه‌ی کل صفحه بلند شود و آن دو سرویسی که
                واقعاً خرابند زیر بقیه گم شوند. */}
            <LongList items={sec.services} initial={8} label="سرویس" searchable
              empty="سرویسی پیدا نشد"
              match={(sv, q) => (sv.name || "").toLowerCase().includes(q)}>
              {(sv) => {
                const bad = sv.level !== "ok";
                return (
                  <div key={sv.name} className="flex items-center justify-between gap-2 py-2"
                    style={{ borderBottom: "1px solid var(--border)" }}>
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="w-1.5 h-1.5 rounded-full shrink-0"
                        style={{ background: bad ? "var(--danger)" : (sv.flapping ? "var(--warn)" : "var(--ok)") }} />
                      <span className="text-[13px] truncate" dir="ltr"
                        style={{ color: bad ? "var(--danger)" : "var(--text)" }}>{sv.name}</span>
                      {sv.flapping && (
                        <span className="fx-pill" style={{ background: "rgba(251,191,36,.12)", color: "var(--warn)" }}>
                          ناپایدار
                        </span>
                      )}
                    </div>
                    <span className="text-[12px] shrink-0" style={{ color: "var(--muted)" }}>
                      {sv.active === "active" ? fmtSize(sv.memory) : sv.active}
                    </span>
                  </div>
                );
              }}
            </LongList>
          </div>
        )}

        {/* سنگین‌ترین پردازه‌ها */}
        {sec.processes?.length > 0 && (
          <div className="fx-card p-5">
            <div className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
              <Activity size={15} style={{ color: "var(--accent-2)" }} /> سنگین‌ترین پردازه‌ها
            </div>
            <LongList items={sec.processes} initial={8} label="پردازه" searchable
              empty="پردازه‌ای پیدا نشد"
              match={(p, q) => (p.name || "").toLowerCase().includes(q)}>
              {(p) => (
                <div key={p.pid} className="flex items-center justify-between gap-2 py-2"
                  style={{ borderBottom: "1px solid var(--border)" }}>
                  <span className="text-[13px] truncate" dir="ltr">{p.name}</span>
                  <div className="flex items-center gap-3 text-[12px] shrink-0"
                    style={{ fontFamily: "var(--mono)" }}>
                    <span style={{ color: p.cpu > 50 ? "var(--warn)" : "var(--muted)" }}>
                      {faNum(p.cpu)}٪ CPU
                    </span>
                    <span style={{ color: "var(--muted)" }}>{faNum(p.mem)}٪ RAM</span>
                  </div>
                </div>
              )}
            </LongList>
          </div>
        )}
      </div>

      {/* تاریخچه‌ی مصرف */}
      <UsageHistoryCard password={password} />

      {/* پرمصرف‌ترین مشتری‌ها */}
      <TopClientsCard password={password} />

      {/* اتصال‌های فعال */}
      <Msg msg={blockMsg} />
      <ConnectionsCard conn={sec.connections}
        onBlock={(h) => setBlockTarget(h)} />

      {blockTarget && (
        <ConfirmModal
          title={`بستن ${blockTarget.ip}؟`}
          desc={`این آی‌پی ${faNum(blockTarget.count)} اتصال دارد (${faNum(blockTarget.pct)}٪ کل). `
                + "با بستنش، اگر مشتری خودتان باشد سرویسش قطع می‌شود. "
                + "هر وقت خواستید از صفحه‌ی فایروال بازش کنید."}
          confirmLabel="ببند"
          onCancel={() => setBlockTarget(null)}
          onConfirm={() => { doBlock(blockTarget.ip); setBlockTarget(null); }} />
      )}

      {/* پورت‌های باز */}
      <PortsCard ports={sec.ports || []} />

      {/* نگهداری خودکار */}
      <MaintenanceCard password={password} />

      {/* بخش سنگین */}
      <div className="fx-card p-5">
        <div className="flex items-center justify-between gap-3 mb-1 flex-wrap">
          <div className="text-[14px] font-semibold text-white flex items-center gap-2">
            <Package size={15} style={{ color: "var(--accent-2)" }} /> بسته‌ها و امنیت
          </div>
          <button onClick={loadHeavy} disabled={heavyBusy}
            className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
            {heavyBusy ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
            {heavy ? "بررسی دوباره" : "بررسی کن"}
          </button>
        </div>
        <p className="text-[13px] mb-3" style={{ color: "var(--muted)" }}>
          چند ثانیه طول می‌کشد، پس خودکار تازه نمی‌شود.
        </p>
        {heavy ? (
          <div className="fx-g3 grid grid-cols-2 gap-3">
            {heavy.metrics.map((m) => <MetricCard key={m.key} m={m} />)}
          </div>
        ) : (
          <EmptyState icon={ShieldCheck} text="برای دیدن به‌روزرسانی‌های در انتظار و وضعیت امنیتی، «بررسی کن» را بزنید" />
        )}
      </div>
    </div>
  );
}
