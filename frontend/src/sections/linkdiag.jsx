/**
 * تانل: عیب‌یابیِ ارتباطِ ایران↔خارج، و حجمِ ترافیکِ هر سرور.
 *
 * برگه: docs/specs/2026-09-26-link-diagnosis-and-traffic.md
 *
 * هیچ حکمی این‌جا ساخته نمی‌شود: «اختلال از کدام سمت است» را
 * `linkcheck.diagnose` در بکند می‌گوید، و وضعیتِ هر سنجش هم از همان‌جا
 * می‌آید. اگر رابط آستانه‌ی خودش را داشت، نوارِ قرمز و حکمِ «سالم» کنارِ
 * هم می‌نشستند.
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle, ArrowDown, ArrowUp, CheckCircle2, HelpCircle, Loader2,
  RefreshCw, Server, Wrench, XCircle, Zap,
} from "lucide-react";
import { API_URL } from "../lib/constants";
import { errMsg, errText, faNum, fmtBytes, okJson } from "../lib/format";
import { usePolling } from "../lib/hooks";
import { EmptyState, InfoBox, LoadError, Msg, PageSkeleton, SectionHead, Segmented } from "../ui/index";
import { isoToJalaliLabel, isoToJalaliStamp } from "../ui/jalali";

const STATE_FA = { ok: "سالم", slow: "کند", lossy: "ناپایدار", down: "قطع", unknown: "بی‌داده" };

function useAdminJson(path, password, every) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API_URL}${path}`, { headers: { "X-Admin-Password": password } });
      setD(await okJson(r)); setErr("");
    } catch (e) { setErr(errMsg(e)); }
  }, [path, password]);
  useEffect(() => { load(); }, [load]);
  usePolling(load, every, [path, password]);
  return { d, err, load, setD };
}

/* نرخ: بایت بر ثانیه → «۱٫۲ MB/s» */
function rateOf(b) {
  const n = Number(b || 0);
  if (n >= 1048576) return `${(n / 1048576).toFixed(1)} MB/s`;
  if (n >= 1024) return `${Math.round(n / 1024)} KB/s`;
  return `${n} B/s`;
}

// ═══════════════════════════════════════════════════════════
//  عیب‌یابیِ ارتباط
// ═══════════════════════════════════════════════════════════

const VERDICT_ICON = { ok: CheckCircle2, warn: AlertTriangle, bad: XCircle, unknown: HelpCircle };

function Verdict({ v }) {
  const Icon = VERDICT_ICON[v.level] || HelpCircle;
  return (
    <div className={`ld-verdict l-${v.level}`} role={v.level === "bad" ? "alert" : undefined}>
      <Icon size={20} />
      <div className="min-w-0">
        <b>{v.title}</b>
        <p>{v.reason}</p>
        {v.fix && <p className="ld-fix"><Wrench size={12} /> {v.fix}</p>}
      </div>
    </div>
  );
}

/*
 * نوارِ ۲۴ ساعت: هر سنجش یک خانه، رنگش وضعیتِ همان سنجش. خواندنِ مقدار
 * با هاور (و لمس)؛ رنگ تنها نشانه نیست — برچسبِ وضعیت کنارِ ردیف هست.
 */
function Strip({ history, label }) {
  const [hi, setHi] = useState(null);
  const h = history || [];
  if (!h.length) return <div className="ld-strip empty"><span>هنوز سنجشی نیست</span></div>;
  const cur = hi != null ? h[hi] : null;
  const pick = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    // نوار راست‌به‌چپ نیست: زمان مثلِ هر محورِ زمانی از چپ به راست می‌رود
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - r.left;
    setHi(Math.max(0, Math.min(h.length - 1, Math.floor((x / r.width) * h.length))));
  };
  return (
    <div className="ld-strip-wrap">
      <div className="ld-strip" dir="ltr" role="img"
        aria-label={`${label}: ${faNum(h.length)} سنجش در ۲۴ ساعتِ اخیر، ${faNum(h.filter((x) => x.state === "down").length)} قطع`}
        onMouseMove={pick} onMouseLeave={() => setHi(null)} onTouchStart={pick} onTouchMove={pick}>
        {h.map((x, i) => <i key={i} className={`s-${x.state}${i === hi ? " on" : ""}`} />)}
      </div>
      <div className="ld-readout">
        {cur ? (
          <>
            <span>{isoToJalaliStamp(cur.at)}</span>
            <b className={`t-${cur.state}`}>{STATE_FA[cur.state]}</b>
            <span>پرت {faNum(cur.loss)}٪</span>
            {cur.avg != null && <span dir="ltr">{faNum(Math.round(cur.avg))} ms</span>}
          </>
        ) : (
          <span>{`${faNum(h.length)} سنجش · از ${isoToJalaliStamp(h[0].at)}`}</span>
        )}
      </div>
    </div>
  );
}

function PathRow({ p, lossLabel = "پرت", extra }) {
  const l = p.latest;
  return (
    <div className="ld-path">
      <div className="ld-path-head">
        <span className="ld-path-name">{p.label}</span>
        <span className={`ld-chip t-${p.state}`}>{STATE_FA[p.state]}</span>
        {extra}
        {l && (
          <span className="ld-path-num">
            {lossLabel} <b>{faNum(l.loss)}٪</b>
            {l.avg != null && <> · <b dir="ltr">{faNum(Math.round(l.avg))} ms</b></>}
          </span>
        )}
      </div>
      <Strip history={p.history} label={p.label} />
      {p.targets?.length > 0 && (
        <div className="ld-targets">
          {p.targets.map((t, i) => {
            const m = t.tcp || t.icmp;
            return (
              <span key={i} dir="ltr" title={t.tcp ? "TCP" : "ICMP"}>
                {t.host}{t.port ? `:${t.port}` : ""} · {m ? `${m.loss}%` : "—"}
                {m?.avg != null ? ` · ${Math.round(m.avg)}ms` : ""}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}

/*
 * خودِ تانل، از کرنلِ سرورِ خارج: اتصال‌ها، RTT و ارسالِ دوباره روی همان
 * ترافیکِ واقعی — و نرخِ لحظه‌ای که هر سه ثانیه تازه می‌شود. «اتصالِ صفر»
 * یعنی تانل وصل نیست، هر چه مسیرها بگویند.
 */
function TunnelRow({ n, live }) {
  const t = n.tunnel || {};
  const now = live || t.now;
  const row = {
    label: "خودِ تانل (کرنل)", state: t.state || "unknown",
    latest: now ? { loss: now.retransPct || 0, avg: now.rtt } : null,
    history: t.history || [],
  };
  return (
    <PathRow p={row} lossLabel="ارسالِ دوباره" extra={now && (
      <span className="ld-live">
        {faNum(now.conns || 0)} اتصال
        {live?.rate && (
          <>
            {" · "}<span title="دریافت از ایران"><ArrowDown size={11} /> <bdi dir="ltr">{rateOf(live.rate.rx)}</bdi></span>
            {" "}<span title="ارسال به ایران"><ArrowUp size={11} /> <bdi dir="ltr">{rateOf(live.rate.tx)}</bdi></span>
          </>
        )}
      </span>
    )} />
  );
}

function NodeDiag({ n, live, password, onNote }) {
  const [busy, setBusy] = useState(false);
  const update = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API_URL}/api/admin/tunnel/node/${n.id}/update-agent`,
        { method: "POST", headers: { "X-Admin-Password": password } });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(errText(j.detail, "به‌روزرسانی در صف نرفت"));
      onNote({ t: "ok", m: `به‌روزرسانیِ ایجنتِ «${n.name}» در صف رفت — دقیقه‌ی بعد انجام می‌شود` });
    } catch (e) { onNote({ t: "err", m: e.message }); } finally { setBusy(false); }
  };
  const iranPaths = n.paths.filter((p) => p.side === "iran");
  const foreignPaths = n.paths.filter((p) => p.side === "foreign");
  return (
    <section className="fx-card p-5 mb-4 ld-node">
      <header className="ld-node-head">
        <Server size={16} />
        <b>{n.name}</b>
        {n.kind === "manual"
          ? <span className="ld-chip t-neutral">تانلِ دستی{n.engine ? ` · ${n.engine}` : ""}</span>
          : n.online != null && (
            <span className={`ld-chip ${n.online ? "t-ok" : "t-down"}`}>{n.online ? "آنلاین" : "آفلاین"}</span>)}
        <span className="ld-node-meta">
          {n.ip && <>سرورِ ایران: <span dir="ltr">{n.ip}</span></>}
          {n.tunnels > 0 && <> · {faNum(n.tunnels)} تانل</>}
          {n.peers?.length > 0 && <> · سرورِ خارج: <span dir="ltr">{n.peers.join("، ")}</span></>}
        </span>
      </header>

      {n.agentStale && n.hasAgent && (
        <div className="ld-stale">
          <AlertTriangle size={14} />
          <span>
            ایجنتِ این سرور نسخه‌ی {n.agentVersion || "نامشخص"} است و سنجشِ سمتِ ایران را نمی‌شناسد
            (نسخه‌ی {n.agentNeed} لازم است). تا به‌روز نشود، فقط مسیرهای سمتِ خارج دیده می‌شوند.
          </span>
          <button type="button" onClick={update} disabled={busy}
            className="fx-btn px-3 py-1.5 text-[12px] flex items-center gap-1.5 shrink-0">
            {busy ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
            به‌روزرسانیِ ایجنت
          </button>
        </div>
      )}
      {n.lastError && (
        <p className="ld-err">آخرین سنجشِ سمتِ ایران ناموفق بود: <span dir="ltr">{n.lastError}</span></p>
      )}

      <Verdict v={n.verdict} />
      <TunnelRow n={n} live={live} />

      <div className="ld-cols mt-2">
        <div>
          <div className="ld-col-head">
            از سرورِ ایران
            <span>{n.iranAt ? isoToJalaliStamp(n.iranAt) : "هنوز نسنجیده"}</span>
          </div>
          {n.hasAgent ? iranPaths.map((p) => <PathRow key={p.key} p={p} />) : (
            // بی ایجنت، سه ردیفِ «بی‌داده» چیزی نمی‌گفت؛ این می‌گوید چرا و چه کنید
            <div className="ld-noagent">
              <p>
                روی این سرورِ ایران ایجنت نصب نیست، پس سه مسیرِ سمتِ ایران (داخل، بین‌الملل،
                تا سرورِ خارج) سنجیده نمی‌شوند — و حکم نمی‌تواند «مسیر» را از «خودِ سرورِ ایران» جدا کند.
              </p>
              <a href="#/tun-nodes" className="fx-btn-g px-3 py-1.5 text-[12px] inline-flex items-center gap-1.5">
                <Server size={12} /> افزودنِ این سرور و نصبِ ایجنت
              </a>
            </div>
          )}
        </div>
        <div>
          <div className="ld-col-head">
            از سرورِ خارج
            <span>{n.foreignAt ? isoToJalaliStamp(n.foreignAt) : "هنوز نسنجیده"}</span>
          </div>
          {foreignPaths.map((p) => <PathRow key={p.key} p={p} />)}
        </div>
      </div>
    </section>
  );
}

export function LinkDiag({ password }) {
  // خودش تازه می‌شود: سنجش هر دقیقه در بکند، صفحه هر ده ثانیه؛ آمارِ
  // خودِ تانل هر سه ثانیه
  const { d, err, load, setD } = useAdminJson("/api/admin/link/diag", password, 10000);
  const { d: live } = useAdminJson("/api/admin/link/live", password, 3000);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState(null);

  const checkNow = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API_URL}/api/admin/link/check`,
        { method: "POST", headers: { "X-Admin-Password": password } });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(errText(j.detail, "سنجش انجام نشد"));
      setD(j);
      setNote({ t: "ok", m: "سمتِ خارج همین حالا سنجیده شد؛ سمتِ ایران (اگر ایجنت دارد) ظرفِ ۳۰ ثانیه می‌رسد" });
    } catch (e) { setNote({ t: "err", m: e.message }); } finally { setBusy(false); }
  };

  const head = (
    <SectionHead title="عیب‌یابیِ ارتباط"
      desc="اختلال از کدام سمت است؟ هر دقیقه خودکار سنجیده می‌شود و این صفحه خودش تازه می‌شود."
      action={
        <button type="button" onClick={checkNow} disabled={busy}
          className="fx-btn px-3.5 py-2.5 text-[13px] flex items-center gap-1.5">
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
          {busy ? "در حال سنجش…" : "همین حالا بسنج"}
        </button>} />
  );

  if (!d && !err) return <PageSkeleton />;
  if (!d) return <div className="fx-anim">{head}<LoadError what="عیب‌یابیِ ارتباط" err={err} onRetry={load} /></div>;

  const livePeers = live?.peers || {};
  return (
    <div className="fx-anim">
      {head}
      <Msg msg={note} onClose={() => setNote(null)} />
      {d.loopError && (
        <p className="ld-err mb-3">سنجشِ خودکار آخرین بار شکست خورد: <span dir="ltr">{d.loopError}</span></p>
      )}
      {!(d.nodes || []).length ? (
        <EmptyState icon={Server} text="هیچ تانلی روی این سرور دیده نمی‌شود"
          hint="نه تانلی در پنل ساخته شده، نه پردازه‌ی تانلی (backhaul، backpack، gost، rathole، …) روی این سرور اتصالِ برقراری دارد." />
      ) : (
        d.nodes.map((n) => <NodeDiag key={n.id} n={n} password={password} onNote={setNote}
          live={livePeers[n.ip] || null} />)
      )}
      <InfoBox>
        «خودِ تانل» از کرنلِ همین سرور خوانده می‌شود — RTT و ارسالِ دوباره روی همان ترافیکِ واقعیِ تانل، نه
        سنجشِ مصنوعی. ارسالِ دوباره‌ی بالا یعنی بسته‌ها بینِ دو سرور گم می‌شوند.
        مرجع‌های بین‌المللی سه شبکه‌ی جدا‌اند (1.1.1.1، 8.8.8.8، 9.9.9.9) تا خرابیِ یکی حکم را عوض نکند.
      </InfoBox>
    </div>
  );
}
// ═══════════════════════════════════════════════════════════
//  حجمِ ترافیک
// ═══════════════════════════════════════════════════════════

const ROLE_FA = { panel: "سرورِ پنل", iran: "ایران", foreign: "خارج" };

/*
 * یک سری: حجمِ کل در هر سطل. دریافت و ارسال در کاشی‌های بالا جدا
 * آمده‌اند؛ دو سری روی یک نمودارِ کوچک فقط خواندنِ «کِی شلوغ بود» را سخت
 * می‌کرد. خواندنِ مقدار با هاور.
 */
function Bars({ rows, labelOf }) {
  const [hi, setHi] = useState(null);
  const tot = rows.map((r) => (r.rx || 0) + (r.tx || 0));
  const max = Math.max(1, ...tot);
  const cur = hi != null ? rows[hi] : null;
  return (
    <div className="tr-chart">
      <div className="tr-readout">
        {cur ? (
          <>
            <span>{labelOf(cur)}</span>
            <b dir="ltr">{fmtBytes(tot[hi])}</b>
            <span title="دریافت"><ArrowDown size={11} /> <bdi dir="ltr">{fmtBytes(cur.rx)}</bdi></span>
            <span title="ارسال"><ArrowUp size={11} /> <bdi dir="ltr">{fmtBytes(cur.tx)}</bdi></span>
          </>
        ) : <span>بیشترین: <bdi dir="ltr">{fmtBytes(max === 1 ? 0 : max)}</bdi></span>}
      </div>
      <div className="tr-bars" dir="ltr" onMouseLeave={() => setHi(null)}
        role="img" aria-label={`نمودارِ حجم، ${faNum(rows.length)} بازه، بیشترین ${fmtBytes(max)}`}>
        {rows.map((r, i) => (
          <span key={i} className={i === hi ? "on" : ""}
            onMouseEnter={() => setHi(i)} onTouchStart={() => setHi(i)}>
            <i style={{ height: tot[i] ? `${Math.max(3, (tot[i] / max) * 100)}%` : 0 }} />
          </span>
        ))}
      </div>
      {rows.length > 0 && (
        <div className="tr-axis" dir="ltr">
          <span>{labelOf(rows[0])}</span>
          <span>{labelOf(rows[rows.length - 1])}</span>
        </div>
      )}
    </div>
  );
}

function Tot({ label, v }) {
  return (
    <div className="tr-tot">
      <span>{label}</span>
      {/* حجم لاتین است («94.3 GB»)؛ بی dir، واحد در متنِ راست‌به‌چپ جلوی عدد می‌افتاد */}
      <b dir="ltr">{fmtBytes((v?.rx || 0) + (v?.tx || 0))}</b>
      <small>
        <span title="دریافت"><ArrowDown size={11} /> <bdi dir="ltr">{fmtBytes(v?.rx)}</bdi></span>
        <span title="ارسال"><ArrowUp size={11} /> <bdi dir="ltr">{fmtBytes(v?.tx)}</bdi></span>
      </small>
    </div>
  );
}

function ServerTraffic({ s }) {
  const [view, setView] = useState("hours");
  const none = !s.lastSample;
  return (
    <section className="fx-card p-5 tr-server">
      <header className="ld-node-head">
        <Server size={16} />
        <b>{s.name}</b>
        <span className="ld-chip t-neutral">{ROLE_FA[s.role] || s.role}</span>
        <span className="ld-node-meta">
          {s.lastSample ? `آخرین سنجش ${isoToJalaliStamp(s.lastSample)}` : ""}
        </span>
      </header>
      {none ? (
        <p className="ld-err">
          {s.agentStale
            ? `ایجنتِ این سرور نسخه‌ی ${s.agentVersion || "نامشخص"} است؛ شمارشِ حجم از نسخه‌ی ${s.agentNeed}. از «عیب‌یابیِ ارتباط» به‌روزش کنید.`
            : "اولین سنجش ظرفِ پنج دقیقه می‌رسد؛ از آن به بعد شمرده می‌شود."}
        </p>
      ) : (
        <>
          <div className="tr-tots">
            <Tot label="امروز" v={s.today} />
            <Tot label="۷ روز" v={s.week} />
            <Tot label="۳۰ روز" v={s.month} />
          </div>
          <div className="flex justify-end mb-2">
            <Segmented value={view} onChange={setView}
              items={[["hours", "۲۴ ساعت"], ["days", "۳۰ روز"]]} />
          </div>
          {view === "hours"
            ? <Bars rows={s.hours || []} labelOf={(r) => `ساعتِ ${faNum(r.hour.slice(11, 13))}`} />
            : <Bars rows={s.days || []} labelOf={(r) => isoToJalaliLabel(r.day)} />}
        </>
      )}
    </section>
  );
}

/*
 * همین حالا: نرخِ کارتِ شبکه‌ی سرورِ پنل و هر تانل، هر سه ثانیه. این همان
 * جوابِ «داده‌ای رد و بدل می‌شود؟» است — تانلی که اتصال دارد ولی صفر بایت
 * بر ثانیه رد می‌کند، در حالی که مشتری‌ها وصل‌اند، خودش نشانه است.
 */
function LiveNow({ live }) {
  if (!live) return null;
  const peers = Object.entries(live.peers || {});
  return (
    <section className="fx-card p-4 mb-4 tr-live">
      <div className="tr-live-head">
        <span className="tr-dot" aria-hidden="true" /> همین حالا
        <small>هر سه ثانیه</small>
      </div>
      <div className="tr-live-rows">
        <div className="tr-live-row">
          <span>کارتِ شبکه‌ی سرورِ پنل</span>
          {live.net ? (
            <b>
              <span title="دریافت"><ArrowDown size={12} /> <bdi dir="ltr">{rateOf(live.net.rx)}</bdi></span>
              <span title="ارسال"><ArrowUp size={12} /> <bdi dir="ltr">{rateOf(live.net.tx)}</bdi></span>
            </b>
          ) : <small>در حال اندازه‌گیری…</small>}
        </div>
        {peers.map(([ip, g]) => (
          <div key={ip} className="tr-live-row">
            {/* نامِ لاتینِ موتور کنارِ عدد بی bdi جابه‌جا می‌شد */}
            <span>
              تانلِ <bdi dir="ltr">{ip}</bdi>
              {g.engine && <> · <bdi dir="ltr">{g.engine}</bdi></>}
              {" · "}{faNum(g.conns || 0)} اتصال
            </span>
            {g.rate ? (
              <b className={!g.conns ? "t-down" : ""}>
                <span title="از ایران"><ArrowDown size={12} /> <bdi dir="ltr">{rateOf(g.rate.rx)}</bdi></span>
                <span title="به ایران"><ArrowUp size={12} /> <bdi dir="ltr">{rateOf(g.rate.tx)}</bdi></span>
              </b>
            ) : <small>{g.conns ? "در حال اندازه‌گیری…" : "وصل نیست"}</small>}
          </div>
        ))}
      </div>
    </section>
  );
}

export function TrafficSection({ password }) {
  const { d, err, load } = useAdminJson("/api/admin/traffic", password, 30000);
  const { d: live } = useAdminJson("/api/admin/link/live", password, 3000);
  const head = (
    <SectionHead title="حجمِ ترافیک"
      desc="هر سرور امروز، این هفته و این ماه چقدر ترافیک رد کرده، و همین حالا با چه سرعتی — خودکار تازه می‌شود." />
  );
  if (!d && !err) return <PageSkeleton />;
  if (!d) return <div className="fx-anim">{head}<LoadError what="حجمِ ترافیک" err={err} onRetry={load} /></div>;
  return (
    <div className="fx-anim">
      {head}
      <LiveNow live={live} />
      <InfoBox>
        روی سرورِ ایران هر بایتِ مشتری دو بار از کارتِ شبکه رد می‌شود — یک‌بار از مشتری به سرور و یک‌بار
        از سرور به خارج. پس «دریافت» تقریباً برابرِ مصرفِ مشتری‌هاست و جمعِ دریافت و ارسال حدودِ دو برابرِ آن.
        دیتاسنترها معمولاً یکی از این دو (اغلب ارسال) یا جمعشان را حساب می‌کنند.
      </InfoBox>
      <div className="tr-grid">
        {(d.servers || []).map((s) => <ServerTraffic key={s.id} s={s} />)}
      </div>
    </div>
  );
}
