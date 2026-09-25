/**
 * داشبوردِ نماینده — صفحه‌ی خانه.
 *
 * مالک: «فضای خالیِ به‌شدت زیاد، جذابیت ندارد، و نمودارِ خطی نگذار».
 * نسخه‌ی قبلی هشت کارتِ هم‌اندازه بود، دوتایش با خطِ کوچکِ روند، و یک
 * قیف که نوارهای باریکِ تمام‌عرض داشت. هر عدد جا می‌گرفت و هیچ‌کدام
 * چیزی نمی‌گفت.
 *
 * حالا هر بلوک یک سؤال را جواب می‌دهد و شکلش از همان سؤال می‌آید:
 *   · چقدر فروختم و چه چیزی منتظرِ من است؟ — چهار عددِ فشرده
 *   · مشتری‌هایم در چه حال‌اند؟ — یک نوارِ بخش‌بخش با راهنما
 *   · حجم چقدر مصرف شده؟ — حلقه
 *   · چند نفر از بازکردنِ ربات به خرید رسیدند؟ — قیفِ باریک‌شونده
 *   · امروز چه کنم؟ — فهرستِ کوتاه با دکمه
 *
 * هیچ عددی این‌جا حساب نمی‌شود؛ همه از `/api/portal/stats`، `summary`
 * و `funnel`. فقط تقسیمِ یک کل به بخش‌ها برای کشیدنِ نوار.
 */
import React, { useEffect, useState } from "react";
import {
  AlertTriangle, ArrowLeft, Check, Clock, FileText, Gauge, ShoppingCart,
  Users, Wallet,
} from "lucide-react";
import { faNum } from "../lib/format";

const pctOf = (n, total) => (total > 0 ? Math.round((n * 1000) / total) / 10 : 0);

function Kpi({ icon: Icon, label, value, unit, sub, tone = "accent", onClick }) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag className={`pd-kpi tone-${tone}`} onClick={onClick}>
      <span className="pd-kpi-ico"><Icon size={17} /></span>
      <span className="pd-kpi-label">{label}</span>
      <span className="pd-kpi-value">{value}{unit && <em>{unit}</em>}</span>
      {sub && <span className="pd-kpi-sub">{sub}</span>}
    </Tag>
  );
}

/** مشتری‌ها در چه حال‌اند — یک کل، چهار بخش که جمعشان همان کل است. */
function StatusCard({ st, go }) {
  const total = Math.max(0, st.total || 0);
  const soon = Math.max(0, st.expiringSoon || 0);
  const expired = Math.max(0, st.expired || 0);
  const healthy = Math.max(0, (st.active || 0) - soon);
  const rest = Math.max(0, total - healthy - soon - expired);
  const parts = [
    { k: "ok", label: "فعال و سالم", n: healthy },
    { k: "warn", label: "تا ۷ روز تمام می‌شود", n: soon },
    { k: "danger", label: "منقضی", n: expired },
    { k: "muted", label: "خاموش", n: rest },
  ];
  return (
    <section className="pd-card pd-status">
      <header className="pd-head">
        <div>
          <h3>مشتری‌های شما</h3>
          <p><b>{faNum(st.active || 0)}</b> فعال از {faNum(total)} کانفیگ</p>
        </div>
        <button className="pd-link" onClick={() => go("configs")}>
          همه <ArrowLeft size={13} />
        </button>
      </header>
      <div className="pd-stack" role="img"
        aria-label={parts.map((p) => `${p.label}: ${p.n}`).join("، ")}>
        {parts.filter((p) => p.n > 0).map((p) => (
          <i key={p.k} className={`t-${p.k}`} style={{ flexGrow: p.n }} />
        ))}
        {!total && <i className="t-muted" style={{ flexGrow: 1 }} />}
      </div>
      <ul className="pd-legend">
        {parts.map((p) => (
          <li key={p.k}>
            <span className={`dot t-${p.k}`} />
            <span className="lbl">{p.label}</span>
            <b>{faNum(p.n)}</b>
            <em>{faNum(pctOf(p.n, total))}٪</em>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** حلقه‌ی مصرف — عدد وسطِ حلقه، هشدارها زیرش. */
function UsageRing({ st }) {
  const pct = st.usagePct === null || st.usagePct === undefined ? null
    : Math.min(100, Math.max(0, st.usagePct));
  const R = 46, C = 2 * Math.PI * R;
  const tone = pct === null ? "muted" : pct >= 90 ? "danger" : pct >= 75 ? "warn" : "accent";
  return (
    <section className="pd-card pd-usage">
      <header className="pd-head">
        <div>
          <h3>مصرفِ حجم</h3>
          <p>از کلِ سقفِ کانفیگ‌های حجم‌دار</p>
        </div>
        <Gauge size={16} className="pd-head-ico" />
      </header>
      <div className="pd-ring-row">
        <svg viewBox="0 0 120 120" className={`pd-ring t-${tone}`} aria-hidden="true">
          <circle cx="60" cy="60" r={R} className="trk" />
          <circle cx="60" cy="60" r={R} className="val"
            strokeDasharray={`${((pct || 0) / 100) * C} ${C}`} />
        </svg>
        <div className="pd-ring-center">
          <b>{pct === null ? "—" : `${faNum(Math.round(pct))}٪`}</b>
          <span>{faNum(st.usedGB || 0)} از {faNum(st.quotaGB || 0)} گیگ</span>
        </div>
      </div>
      <div className="pd-chips">
        <span className="t-danger">{faNum(st.overQuota || 0)} حجمِ تمام</span>
        <span className="t-warn">{faNum(st.nearQuota || 0)} بالای ۸۰٪</span>
        <span className="t-muted">{faNum(st.unlimitedQuota || 0)} نامحدود</span>
      </div>
    </section>
  );
}

/**
 * قیف — هر پله یک نوارِ افقی، طولش سهمِ آن پله از «ربات را باز کردند».
 *
 * چرا نه «درصد از پله‌ی قبلی» و نه شکلِ قیفِ باریک‌شونده: پله‌ها تو در
 * تو نیستند. ثبتِ شماره شرطِ سفارش نیست، پس در داده‌ی واقعی «سفارش
 * ثبت کردند» از «شماره ثبت کردند» بیشتر است. نسخه‌ی اولِ این کارت
 * «۱۶۲٪ از قبلی» نشان می‌داد و قیف وسطش پهن می‌شد. درصد را هم خودمان
 * حساب نمی‌کنیم — `pct` از خودِ `_funnel` می‌آید.
 */
function Funnel({ src }) {
  const [f, setF] = useState(null);
  useEffect(() => {
    let alive = true;
    src.funnel().then((j) => { if (alive) setF(j); })
      .catch((e) => { if (alive) setF({ error: e.message || "خوانده نشد" }); });
    return () => { alive = false; };
  }, [src]);
  // پیش‌تر خطا کارت را بی‌صدا حذف می‌کرد — همان شکلِ «هنوز کسی ربات را باز نکرده»
  if (f && f.error) {
    return (
      <section className="pd-card pd-funnel">
        <p style={{ color: "var(--danger)", fontSize: 13 }}>قیفِ فروش خوانده نشد: {f.error}</p>
      </section>
    );
  }
  if (!f || !f.ready || !f.started) return null;
  return (
    <section className="pd-card pd-funnel">
      <header className="pd-head">
        <div>
          <h3>از بازکردنِ ربات تا خرید</h3>
          <p>{faNum(f.segments?.trialOnly || 0)} نفر فقط تست گرفتند و هنوز نخریده‌اند</p>
        </div>
      </header>
      <ol>
        {f.steps.map((s, i) => (
          <li key={s.label} className={i === f.steps.length - 1 ? "last" : ""}>
            <div className="row">
              <span className="lbl">{s.label}</span>
              <b>{faNum(s.n)}</b>
              <em>{i ? `${faNum(s.pct)}٪` : ""}</em>
            </div>
            <div className="trk"><i style={{ width: `${Math.max(2, Math.min(100, s.pct || 0))}%` }} /></div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Today({ stats, sum, go }) {
  const todo = [];
  const pending = stats?.sales?.pending || 0;
  if (pending > 0) todo.push({ t: `${faNum(pending)} سفارش منتظرِ تایید`, tone: "warn", b: "سفارش‌ها", to: "orders" });
  if (stats?.expiringSoon > 0) todo.push({ t: `${faNum(stats.expiringSoon)} اشتراک تا یک هفته تمام می‌شود`, tone: "warn", b: "مشتری‌ها", to: "users" });
  if (stats?.expired > 0) todo.push({ t: `${faNum(stats.expired)} اشتراکِ منقضی`, tone: "danger", b: "کانفیگ‌ها", to: "configs" });
  if (stats?.overQuota > 0) todo.push({ t: `${faNum(stats.overQuota)} مشتری حجمش تمام شده`, tone: "danger", b: "کانفیگ‌ها", to: "configs" });
  if (sum?.unpriced > 0) todo.push({ t: `${faNum(sum.unpriced)} کانفیگ هنوز نرخ ندارد`, tone: "muted" });
  return (
    <section className="pd-card pd-today">
      <header className="pd-head"><div><h3>کارهای امروز</h3></div></header>
      {!todo.length ? (
        <div className="pd-done"><Check size={16} /> چیزی منتظرِ شما نیست</div>
      ) : (
        <ul>
          {todo.map((x, i) => (
            <li key={i} className={`t-${x.tone}`}>
              <span className="dot" />
              <span className="txt">{x.t}</span>
              {x.to && <button onClick={() => go(x.to)} aria-label={`رفتن به ${x.b}`}>{x.b} <ArrowLeft size={12} /></button>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/**
 * عددهای دومِ صفحه — فهرستِ فشرده، نه کاشی.
 * نسخه‌ی قبلی به هر کدامِ این‌ها یک کاشیِ ۱۴۲ پیکسلی می‌داد؛ دوازده
 * کاشیِ هم‌وزن یعنی چشم نمی‌داند از کجا شروع کند. این‌ها مهم‌اند ولی
 * سؤالِ اولِ روز نیستند.
 */
function Facts({ stats, sum }) {
  const sales = stats?.sales;
  const rows = [];
  if (sales?.hasBot) {
    rows.push(["فروشِ کل", `${faNum(sales.sold)} تومان`, `${faNum(sales.orders)} سفارش`]);
    // «فروش» با «درآمد» یکی نیست — خرید از کیف پول پولِ تازه نیاورده
    rows.push(["دریافتیِ کارت‌به‌کارت", `${faNum(sales.received)} تومان`, "بدونِ خرید از کیف پول"]);
  }
  if (sum) {
    rows.push(["کلِ کانفیگ‌ها", faNum(sum.configs),
      stats ? `${faNum(stats.neverExpires)} بدون انقضا` : ""]);
    rows.push(["تمدیدها", faNum(sum.renewals), `${faNum(sum.months)} ماه در مجموع`]);
  }
  if (stats) rows.push(["غیرفعال", faNum(stats.inactive || 0), "خاموش یا غیرفعال‌شده"]);
  if (!rows.length) return null;
  return (
    <section className="pd-card pd-facts">
      <header className="pd-head"><div><h3>در یک نگاه</h3></div></header>
      <dl>
        {rows.map(([k, v, h]) => (
          <div key={k}>
            <dt>{k}{h && <small>{h}</small>}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export function HomeDash({ stats, sum, go, src, busy }) {
  if (!stats && !sum) {
    return busy ? (
      <div className="pd-grid">
        {[0, 1, 2, 3].map((i) => <div key={i} className="pd-kpi pd-skel" />)}
      </div>
    ) : null;
  }
  const sales = stats?.sales;
  return (
    <div className="pd-home">
      <div className="pd-grid">
        {sales?.hasBot && (
          <Kpi icon={ShoppingCart} label="فروشِ این ماه" value={faNum(sales.monthSold)} unit="تومان"
            sub={`${faNum(sales.monthOrders)} سفارش · کل ${faNum(sales.sold)}`} tone="accent" />
        )}
        {stats && (
          <Kpi icon={Users} label="مشتریِ فعال" value={faNum(stats.active)}
            sub={`${faNum(stats.thisMonth?.new || 0)} تازه و ${faNum(stats.thisMonth?.renewals || 0)} تمدید در این ماه`}
            tone="ok" onClick={() => go("users")} />
        )}
        {sales?.hasBot && (
          <Kpi icon={FileText} label="رسیدِ منتظرِ شما" value={faNum(sales.pending)}
            sub={sales.pending ? "برای تایید بزنید" : "چیزی نمانده"}
            tone={sales.pending ? "warn" : "muted"} onClick={() => go("orders")} />
        )}
        {sum && (sum.prepaid ? (
          <Kpi icon={Wallet} label="اعتبارِ باقی‌مانده" value={faNum(sum.credit)} unit="تومان"
            sub={sum.credit > 0 ? "پیش‌پرداخت" : "اعتبار تمام شده"}
            tone={sum.credit > 0 ? "ok" : "danger"} />
        ) : (
          <Kpi icon={Wallet} label="مانده‌ی بدهیِ این دوره" value={faNum(sum.balance)} unit="تومان"
            sub={`از ${faNum(sum.due)} تومان`} tone={sum.balance > 0 ? "warn" : "ok"} />
        ))}
        {!sales?.hasBot && stats && (
          <Kpi icon={Clock} label="رو به اتمام" value={faNum(stats.expiringSoon)}
            sub="تا هفت روز دیگر" tone={stats.expiringSoon ? "warn" : "muted"} />
        )}
      </div>

      <div className="pd-split">
        <div className="pd-col">
          {stats && <StatusCard st={stats} go={go} />}
          <Funnel src={src} />
          <Facts stats={stats} sum={sum} />
        </div>
        <div className="pd-col">
          <Today stats={stats} sum={sum} go={go} />
          {stats && <UsageRing st={stats} />}
        </div>
      </div>

      {sum?.unpriced > 0 && (
        <p className="pd-note"><AlertTriangle size={13} /> {faNum(sum.unpriced)} کانفیگ هنوز نرخ ندارد
          و در مبلغِ بدهی حساب نشده.</p>
      )}
    </div>
  );
}
