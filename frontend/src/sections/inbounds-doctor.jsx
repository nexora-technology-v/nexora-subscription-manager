/**
 * تانل: اینباندهای 3x-ui — پیشنهادها، و اینکه کدام اینباند مشکل دارد.
 *
 * برگه: docs/specs/2026-09-26-live-tunnel-and-inbound-doctor.md
 *
 * همه‌ی یافته‌ها و پیشنهادها از بکند (`inbounddoc`) می‌آیند؛ این‌جا فقط
 * نمایش. پنل در 3x-ui چیزی را عوض نمی‌کند — مالک اعمال می‌کند.
 *
 * چیدمان عمداً کم‌شلوغ است: بالا «پیشنهادِ ما»، پایین هر اینباند یک خط
 * (نام، وضعیت، مهم‌ترین مورد)، و جزئیات فقط با کلیک. نسخه‌ی اول همه‌ی
 * یافته‌های همه‌ی اینباندها را هم‌زمان باز نشان می‌داد و مالک گفت ادمین
 * گیج می‌شود.
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle, ArrowDown, ArrowUp, Check, CheckCircle2, ChevronDown, Copy, Info,
  Loader2, RefreshCw, Sparkles, Wrench, XCircle,
} from "lucide-react";
import { API_URL } from "../lib/constants";
import { errMsg, faNum, fmtBytes, okJson } from "../lib/format";
import { usePolling } from "../lib/hooks";
import { EmptyState, LoadError, PageSkeleton, SectionHead } from "../ui/index";

const LEVEL = {
  bad: { fa: "مشکل دارد", Icon: XCircle },
  warn: { fa: "هشدار", Icon: AlertTriangle },
  tip: { fa: "پیشنهاد", Icon: Info },
  ok: { fa: "سالم", Icon: CheckCircle2 },
};

function rateOf(b) {
  const n = Number(b || 0);
  if (n >= 1048576) return `${(n / 1048576).toFixed(1)} MB/s`;
  if (n >= 1024) return `${Math.round(n / 1024)} KB/s`;
  return `${n} B/s`;
}

function CopyBtn({ text }) {
  const [done, setDone] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      setTimeout(() => setDone(false), 1500);
    } catch { /* کلیپ‌بورد در دسترس نیست (http بی‌امن) — متن قابلِ انتخاب هست */ }
  };
  return (
    <button type="button" onClick={copy} className="ib-copy" aria-label={`کپیِ ${text}`}>
      {done ? <Check size={12} /> : <Copy size={12} />}
    </button>
  );
}

// ─────────────── پیشنهادها ───────────────

function Rec({ r }) {
  return (
    <section className="fx-card p-4 ib-rec">
      <header><Sparkles size={15} /> <b>{r.title}</b></header>
      <p className="ib-rec-why">{r.why}</p>
      {r.domains && (
        <div className="ib-domains">
          {r.domains.map((d, i) => (
            <div key={d.host} className={i === 0 ? "best" : ""}>
              <bdi dir="ltr">{d.host}</bdi>
              <span dir="ltr">{d.ms != null ? `${Math.round(d.ms)} ms` : ""}</span>
              {i === 0 && <em>سریع‌ترین</em>}
              <CopyBtn text={d.host} />
            </div>
          ))}
        </div>
      )}
      {r.settings && (r.have ? (
        <p className="ib-have"><CheckCircle2 size={13} /> اینباندِ «{r.have}» همین است — کاری لازم نیست.</p>
      ) : (
        <>
          <dl className="ib-settings">
            {r.settings.map(([k, v]) => (
              <div key={k}><dt>{k}</dt><dd>{v}</dd></div>
            ))}
          </dl>
          {r.new && (
            <p className="ib-rec-note">اینباندِ تازه یعنی لینکِ تازه — فقط برای مشتری‌هایی که به آن منتقل می‌کنید.</p>
          )}
        </>
      ))}
    </section>
  );
}

// ─────────────── فهرستِ اینباندها ───────────────

function Finding({ f }) {
  const L = LEVEL[f.level] || LEVEL.tip;
  return (
    <div className={`ib-find l-${f.level}`}>
      <L.Icon size={15} />
      <div className="min-w-0">
        <b>{f.title}</b>
        <p>{f.why}</p>
        <p className="ib-fix"><Wrench size={11} /> <span>{f.fix}</span></p>
        {f.sub && <span className="ib-sub">لینکِ اشتراکِ مشتری‌ها عوض می‌شود</span>}
      </div>
    </div>
  );
}

function InboundRow({ i }) {
  const [open, setOpen] = useState(false);
  const L = LEVEL[i.level] || LEVEL.ok;
  const top = i.findings[0];
  const c = i.conns;
  return (
    <div className={`ib-row l-${i.level} ${open ? "open" : ""}`}>
      <button type="button" className="ib-row-head" onClick={() => setOpen((x) => !x)} aria-expanded={open}>
        <L.Icon size={16} />
        <span className="ib-row-name">
          <b>{i.remark}</b>
          <small dir="ltr">{i.protocol} · {i.network}{i.security !== "none" ? ` · ${i.security}` : ""} · :{i.port}</small>
        </span>
        <span className="ib-row-top">{top ? top.title : "سالم"}</span>
        <span className="ib-row-rate">
          {i.rate ? <bdi dir="ltr">{rateOf((i.rate.rx || 0) + (i.rate.tx || 0))}</bdi> : "—"}
        </span>
        <ChevronDown size={15} className="ib-chev" />
      </button>
      {open && (
        <div className="ib-row-body">
          <div className="ib-stats">
            <div>
              <span>همین حالا</span>
              {i.rate ? (
                <b>
                  <span title="آپلودِ مشتری‌ها"><ArrowUp size={11} /> <bdi dir="ltr">{rateOf(i.rate.rx)}</bdi></span>
                  <span title="دانلودِ مشتری‌ها"><ArrowDown size={11} /> <bdi dir="ltr">{rateOf(i.rate.tx)}</bdi></span>
                </b>
              ) : <small>در حال اندازه‌گیری…</small>}
            </div>
            <div>
              <span>اتصال‌ها</span>
              {c ? <b>{faNum(c.tunnel)} از تانل · {faNum(c.direct)} مستقیم</b> : <small>—</small>}
            </div>
            <div><span>کلاینت</span><b>{faNum(i.active)} فعال از {faNum(i.clients)}</b></div>
            <div><span>مصرفِ کل</span><b dir="ltr">{fmtBytes(i.up + i.down)}</b></div>
          </div>
          {i.findings.length
            ? <div className="ib-finds">{i.findings.map((f) => <Finding key={f.id} f={f} />)}</div>
            : <p className="ib-ok"><CheckCircle2 size={13} /> مشکلی در تنظیمات یا اندازه‌گیری پیدا نشد.</p>}
        </div>
      )}
    </div>
  );
}

export function InboundsDoctor({ password }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async (fresh = false) => {
    try {
      const r = await fetch(`${API_URL}/api/admin/inbounds/doctor` + (fresh ? "?fresh=1" : ""),
        { headers: { "X-Admin-Password": password } });
      setD(await okJson(r)); setErr("");
    } catch (e) { setErr(errMsg(e)); }
  }, [password]);
  useEffect(() => { load(); }, [load]);
  // مصرفِ لحظه‌ای از تفاضل با بارِ قبلی؛ 3x-ui هر ده ثانیه آمار را می‌نویسد
  usePolling(() => load(false), 5000, [password]);

  const recheck = async () => { setBusy(true); try { await load(true); } finally { setBusy(false); } };
  const head = (
    <SectionHead title="اینباندها"
      desc="پیشنهادهای ما برای همین سرور، و اینکه کدام اینباند مشکل دارد."
      action={
        <button type="button" onClick={recheck} disabled={busy}
          className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5"
          title="دامنه‌ها و dest Reality دوباره از همین سرور سنجیده می‌شوند">
          {busy ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />} سنجشِ دوباره
        </button>} />
  );
  if (!d && !err) return <PageSkeleton />;
  if (!d) return <div className="fx-anim">{head}<LoadError what="اینباندها" err={err} onRetry={() => load(true)} /></div>;

  const order = { bad: 0, warn: 1, tip: 2, ok: 3 };
  const rows = [...(d.inbounds || [])].sort((a, b) => (order[a.level] ?? 9) - (order[b.level] ?? 9));
  const bad = rows.filter((r) => r.level === "bad").length;
  return (
    <div className="fx-anim">
      {head}
      {err && <p className="ld-err mb-3">آخرین تازه‌سازی ناموفق بود: {err}</p>}

      {(d.recommend || []).length > 0 && (
        <>
          <h3 className="ib-h">پیشنهادِ ما برای همین سرور</h3>
          <div className="ib-recs">{d.recommend.map((r) => <Rec key={r.id} r={r} />)}</div>
        </>
      )}

      <h3 className="ib-h">
        اینباندهای شما
        <span className={bad ? "t-bad" : "t-ok"}>
          {bad ? `${faNum(bad)} مورد مشکل دارد` : "مشکلِ قطع‌کننده‌ای نیست"}
        </span>
      </h3>
      {!d.listenKnown && (
        <p className="ld-err mb-3">فهرستِ پورت‌های باز خوانده نشد (ss در دسترس نیست)؛ «کسی گوش نمی‌دهد» سنجیده نمی‌شود.</p>
      )}
      {!rows.length ? (
        <EmptyState icon={Info} text="هیچ اینباندی در 3x-ui نیست" />
      ) : (
        <div className="ib-list">{rows.map((i) => <InboundRow key={i.id} i={i} />)}</div>
      )}
      <p className="ib-foot">پنل در 3x-ui چیزی را عوض نمی‌کند؛ پیشنهادها را خودتان در 3x-ui اعمال کنید.</p>
    </div>
  );
}
