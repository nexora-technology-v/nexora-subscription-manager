/**
 * تانل: تحلیلِ اینباندهای 3x-ui — چرا این اینباند ترافیک نمی‌گیرد یا کند است.
 *
 * برگه: docs/specs/2026-09-26-live-tunnel-and-inbound-doctor.md
 *
 * همه‌ی یافته‌ها از بکند (`inbounddoc.analyze`) می‌آیند؛ این‌جا فقط نمایش.
 * پنل در 3x-ui چیزی را عوض نمی‌کند — هر یافته می‌گوید مالک کجا چه کند، و
 * اینکه لینکِ اشتراکِ مشتری‌ها عوض می‌شود یا نه.
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle, ArrowDown, ArrowUp, CheckCircle2, Info, Link2, Loader2, RefreshCw,
  Wrench, XCircle,
} from "lucide-react";
import { API_URL } from "../lib/constants";
import { errMsg, faNum, fmtBytes, okJson } from "../lib/format";
import { usePolling } from "../lib/hooks";
import { EmptyState, InfoBox, LoadError, PageSkeleton, SectionHead } from "../ui/index";

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

function Finding({ f }) {
  const L = LEVEL[f.level] || LEVEL.tip;
  return (
    <div className={`ib-find l-${f.level}`}>
      <L.Icon size={15} />
      <div className="min-w-0">
        <b>{f.title}</b>
        <p>{f.why}</p>
        <p className="ib-fix"><Wrench size={11} /> {f.fix}</p>
        {f.sub && (
          <span className="ib-sub" title="اعمالِ این پیشنهاد لینکِ اشتراکِ مشتری‌ها را عوض می‌کند">
            <Link2 size={11} /> لینکِ اشتراک عوض می‌شود — مشتری‌ها باید اشتراک را به‌روز کنند
          </span>
        )}
      </div>
    </div>
  );
}

function InboundCard({ i }) {
  const L = LEVEL[i.level] || LEVEL.ok;
  const c = i.conns;
  return (
    <section className={`fx-card p-5 ib-card l-${i.level}`}>
      <header className="ib-head">
        <L.Icon size={16} />
        <b>{i.remark}</b>
        <span className="ib-tags" dir="ltr">
          <span>{i.protocol}</span><span>{i.network}</span>
          {i.security !== "none" && <span>{i.security}</span>}
          <span>:{i.port}</span>
        </span>
      </header>
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
        <div>
          <span>کلاینت</span>
          <b>{faNum(i.active)} فعال از {faNum(i.clients)}</b>
        </div>
        <div>
          <span>مصرفِ کل</span>
          <b dir="ltr">{fmtBytes(i.up + i.down)}</b>
        </div>
      </div>
      {i.findings.length ? (
        <div className="ib-finds">{i.findings.map((f) => <Finding key={f.id} f={f} />)}</div>
      ) : (
        <p className="ib-ok"><CheckCircle2 size={13} /> هیچ مشکلی در تنظیمات یا اندازه‌گیری پیدا نشد.</p>
      )}
    </section>
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
  // مصرفِ لحظه‌ای از تفاضل با بارِ قبلی حساب می‌شود؛ 3x-ui هر ده ثانیه
  // آمار را در دیتابیسش می‌نویسد، پس تندتر از پنج ثانیه فایده ندارد
  usePolling(() => load(false), 5000, [password]);

  const recheck = async () => { setBusy(true); try { await load(true); } finally { setBusy(false); } };
  const head = (
    <SectionHead title="اینباندها"
      desc="هر اینباندِ 3x-ui: آیا واقعاً ترافیک می‌گیرد، از تانل می‌آید یا مستقیم، و چه چیزی در تنظیماتش مانع است."
      action={
        <button type="button" onClick={recheck} disabled={busy}
          className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5"
          title="dest Reality هر ده دقیقه یک‌بار سنجیده می‌شود؛ این همین حالا دوباره می‌سنجد">
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
      {!d.listenKnown && (
        <p className="ld-err mb-3">فهرستِ پورت‌های باز خوانده نشد (ss در دسترس نیست)؛ «کسی گوش نمی‌دهد» سنجیده نمی‌شود.</p>
      )}
      {!rows.length ? (
        <EmptyState icon={Info} text="هیچ اینباندی در 3x-ui نیست" />
      ) : (
        <>
          <InfoBox>
            {bad
              ? `${faNum(bad)} اینباند مشکلی دارد که جلوی ترافیک را می‌گیرد — بالای فهرست‌اند.`
              : "هیچ اینباندی مشکلِ قطع‌کننده ندارد."}
            {" "}پنل در 3x-ui چیزی را عوض نمی‌کند؛ پیشنهادها را خودتان اعمال کنید. هر جا لینکِ اشتراک عوض می‌شود، صریح گفته شده.
          </InfoBox>
          <div className="ib-grid">{rows.map((i) => <InboundCard key={i.id} i={i} />)}</div>
        </>
      )}
    </div>
  );
}
