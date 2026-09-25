/**
 * تانل‌ها و نودها.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
import React, { useState, useEffect, useRef } from "react";
import {
  Activity, AlertTriangle, Check, CheckCircle2, Circle, Clock, Copy, FileText, Loader2, Network, Plus as PlusIcon, RefreshCw, Server, ShieldCheck, Trash2, UploadCloud, X, XCircle,
} from "lucide-react";
import { API_URL } from "../lib/constants";
import { errText, faNum } from "../lib/format";
import { usePolling } from "../lib/hooks";
import { ConfirmModal, EmptyState, Field, InfoBox, Modal, Msg, PageSkeleton, Pager, SectionHead, Segmented, StatTile, UsageBar, usageColor } from "../ui/index";
import { isoToJalaliLabel, isoToJalaliStamp } from "../ui/jalali";

export const ENGINE_COLOR = {
  backhaul: "#34D399",
  rathole: "#5AA9E6",
  gost: "#A78BFA",
  frp: "#FBBF24",
};

export const TUN_STATUS = {
  running:   { label: "در حال کار", color: "var(--ok)" },
  deploying: { label: "در حال اعمال", color: "var(--warn)" },
  stopped:   { label: "متوقف", color: "var(--muted)" },
  failed:    { label: "خطا", color: "var(--danger)" },
  pending:   { label: "اعمال نشده", color: "var(--muted)" },
  // «error» را بکند نمی‌نویسد (status_from_result فقط failed می‌گوید)،
  // ولی داده‌ی کهنه نباید «اعمال نشده» دیده شود
  error:     { label: "خطا", color: "var(--danger)" },
};

export function useTunnel(password) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/tunnel/overview`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setData(d);
    } catch {
      setData({ ready: false, error: "اتصال برقرار نشد", nodes: [], tunnels: [] });
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [password]);
  // نودها هر ۲۰ ثانیه ping می‌زنند — ولی وقتی تب مخفی است بی‌فایده
  usePolling(load, 20000, [password]);

  return { data, loading, reload: load };
}

/* ── داشبورد تانل ── */
export function TunnelOverview({ password }) {
  const { data, loading, reload } = useTunnel(password);

  if (loading) return <PageSkeleton />;

  if (!data?.ready) {
    return (
      <div className="fx-anim">
        <SectionHead title="داشبورد تانل" desc="" />
        <EmptyState icon={AlertTriangle} tone="var(--warn)"
          text="ماژول تانل در دسترس نیست"
          hint={data?.error || "تا وقتی این ماژول بالا نیاید، سرور و تانلی خوانده نمی‌شود."} />
      </div>
    );
  }

  // پاسخ ممکن است شکل دیگری داشته باشد (خطا، نسخه‌ی قدیمی، مستاجری
  // که این بخش را ندارد). آن‌وقت صفحه باید حالت خالی نشان بدهد، نه
  // اینکه کل بخش بیفتد.
  const s = data.stats || {};
  const nodes = data.nodes || [];
  const tuns = data.tunnels || [];
  const offline = nodes.filter((n) => !n.online);
  const broken = tuns.filter((t) => t.status === "failed" || t.status === "error");
  const issues = offline.length + broken.length;

  return (
    <div className="fx-anim">
      <SectionHead title="داشبورد تانل"
        desc="سرورهای متصل و تانل‌های فعال."
        action={<button onClick={reload} className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
          <RefreshCw size={13} /> تازه‌سازی</button>} />

      {/* سه عدد، نه چهار: «سرورها ۳» و «آنلاین ۲» یک خبر بودند در دو
          کارت. نسبت همان را در یکی می‌گوید، و جای چهارم به چیزی رسید
          که واقعاً کاری می‌خواهد — تعدادِ مشکل‌ها. */}
      <div className="fx-g3 fx-kpi3 grid grid-cols-3 gap-3">
        <StatTile label="سرورِ آنلاین" icon={Server}
          tone={offline.length ? "var(--warn)" : "var(--ok)"}
          value={`${faNum(s.online || 0)}/${faNum(s.nodes || 0)}`}
          hint={!s.nodes ? "هنوز سروری اضافه نشده"
                : offline.length ? `${faNum(offline.length)} سرور جواب نمی‌دهد` : "همه در دسترس‌اند"} />
        <StatTile label="تانلِ در حال کار" icon={Network}
          tone={s.tunnels && s.running === s.tunnels ? "var(--ok)" : "var(--purple)"}
          value={`${faNum(s.running || 0)}/${faNum(s.tunnels || 0)}`}
          hint={!s.tunnels ? "هنوز تانلی ساخته نشده"
                : broken.length ? `${faNum(broken.length)} تانل خطا دارد`
                : s.tunnels - (s.running || 0) > 0 ? `${faNum(s.tunnels - (s.running || 0))} تانل روشن نیست`
                : "همه روشن‌اند"} />
        <StatTile label="نیاز به توجه" icon={issues ? AlertTriangle : CheckCircle2}
          tone={issues ? "var(--danger)" : "var(--ok)"}
          color={issues ? "var(--danger)" : "var(--ok)"}
          value={faNum(issues)}
          hint={issues ? "پایین‌تر فهرست شده‌اند" : "همه چیز سالم است"} />
      </div>

      {issues > 0 && (
        <div className="fx-card p-5 mb-4 fx-attn">
          <div className="text-[14px] font-semibold text-white mb-1">نیاز به توجه</div>
          <div className="fx-rowlist">
            {broken.map((t) => (
              <div key={"t" + t.id} className="flex items-start gap-3">
                <XCircle size={15} className="shrink-0 mt-0.5" style={{ color: "var(--danger)" }} />
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] font-semibold text-white">تانل «{t.name}» خطا دارد</div>
                  <div className="text-[12px] mt-0.5 break-words" style={{ color: "var(--dim)" }}>
                    {t.last_error || "پیامی از سرور نرسید — «لاگ» را در صفحه‌ی تانل‌ها ببینید."}
                  </div>
                </div>
              </div>
            ))}
            {offline.map((n) => (
              <div key={"n" + n.id} className="flex items-start gap-3">
                <AlertTriangle size={15} className="shrink-0 mt-0.5" style={{ color: "var(--warn)" }} />
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] font-semibold text-white">سرورِ «{n.name}» جواب نمی‌دهد</div>
                  <div className="text-[12px] mt-0.5" style={{ color: "var(--dim)" }}>
                    {n.last_seen ? `آخرین تماس: ${isoToJalaliStamp(n.last_seen)}` : "هنوز هیچ تماسی نگرفته — دستور نصب اجرا شده؟"}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {nodes.length === 0 ? (
        <EmptyState icon={Server} text="هنوز سروری اضافه نشده"
          hint="از بخش «سرورها» یک سرور ایران اضافه کنید. یک دستور نصب می‌گیرید که روی آن سرور اجرا می‌کنید — بدون نیاز به باز کردن پورت یا دادن رمز." />
      ) : (
        /* کنارِ هم روی صفحه‌ی پهن: دو فهرستِ کوتاه زیرِ هم، نیمی از
           صفحه را خالی می‌گذاشتند */
        <div className="fx-split">
          <div className="fx-card p-5">
            <div className="text-[14px] font-semibold text-white mb-2">سرورها</div>
            <div className="fx-rowlist">
              {nodes.map((n) => (
                <div key={n.id} className="flex items-center gap-3">
                  <span className={`fx-live-dot ${n.online ? "on" : ""}`} />
                  <div className="min-w-0 flex-1">
                    <div className="text-[13.5px] font-semibold text-white truncate">{n.name}</div>
                    <div className="text-[12px] mt-0.5 truncate" style={{ color: "var(--muted)" }}>
                      {n.os_info || "—"}{n.public_ip ? ` · ${n.public_ip}` : ""}
                    </div>
                  </div>
                  {n.online && n.cpu_percent != null && (
                    <div className="fx-hide-m flex flex-col gap-1 w-[92px] shrink-0">
                      <UsageBar label="CPU" pct={n.cpu_percent} />
                      <UsageBar label="RAM" pct={n.mem_percent} />
                    </div>
                  )}
                  <span className="text-[12.5px] shrink-0 w-[58px] text-left"
                    style={{ color: n.online ? "var(--ok)" : "var(--muted)", fontFamily: "var(--mono)" }}>
                    {faNum(n.running_count)}/{faNum(n.tunnel_count)}
                    <span className="fx-fa-sub"> تانل</span>
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="fx-card p-5">
            <div className="text-[14px] font-semibold text-white mb-2">تانل‌ها</div>
            {tuns.length === 0 ? (
              <div className="text-[13px] py-6 text-center" style={{ color: "var(--muted)" }}>
                هنوز تانلی ساخته نشده — از «تانل‌ها» بسازید.
              </div>
            ) : (
              <div className="fx-rowlist">
                {tuns.slice(0, 6).map((t) => {
                  const st = TUN_STATUS[t.status] || TUN_STATUS.pending;
                  const ec = ENGINE_COLOR[t.engine] || "var(--accent-2)";
                  return (
                    <div key={t.id} className="flex items-center gap-2.5">
                      <div className="min-w-0 flex-1">
                        <div className="text-[13.5px] font-semibold text-white truncate">{t.name}</div>
                        <div className="text-[12px] mt-0.5 truncate" style={{ color: "var(--muted)" }}>
                          {t.node_name} · {faNum((t.ports || []).length)} پورت
                        </div>
                      </div>
                      <span className="fx-pill shrink-0"
                        style={{ background: `color-mix(in srgb, ${ec} 14%, transparent)`, color: ec }}>
                        {t.engineName}
                      </span>
                      <span className="fx-pill shrink-0"
                        style={{ background: `color-mix(in srgb, ${st.color} 14%, transparent)`, color: st.color }}>
                        {st.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── سرورها ── */
export function TunnelNodes({ password }) {
  const { data, loading, reload } = useTunnel(password);
  const [diag, setDiag] = useState(null);
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState(null);
  const [msg, setMsg] = useState(null);

  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(t); } }, [msg]);

  const add = async () => {
    if (!name.trim()) return;
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/tunnel/node`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ name, note }),
      });
      const d = await res.json();
      if (res.ok) {
        setCreated(d);
        setAdding(false);
        setName(""); setNote("");
        reload();
      } else setMsg({ t: "err", m: errText(d.detail, "افزودن ناموفق") });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(false); }
  };

  /* هر دو با یک کلیک و بی‌پاسخ بودند. «توکن جدید» توکنِ قبلی را همان
     لحظه باطل می‌کند — یعنی سرور تا اجرای دوباره‌ی دستورِ نصب قطع است؛
     و حذف، تانل‌های آن سرور را هم پاک می‌کند. هیچ‌کدام نباید با یک
     کلیکِ اشتباه بیفتد، و شکستشان نباید بی‌صدا بماند. */
  const [ask, setAsk] = useState(null);     // {kind: "del"|"rot", n}
  const remove = async (n) => {
    setAsk(null);
    const res = await fetch(`${API_URL}/api/admin/tunnel/node/${n.id}`, {
      method: "DELETE", headers: { "X-Admin-Password": password } });
    const d = await res.json().catch(() => ({}));
    setMsg(res.ok
      ? { t: "ok", m: `«${n.name}» حذف شد` + (d.tunnels ? ` — با ${faNum(d.tunnels)} تانل` : "") }
      : { t: "err", m: errText(d.detail, "حذف ناموفق بود") });
    reload();
  };

  const rotate = async (n) => {
    setAsk(null);
    const res = await fetch(`${API_URL}/api/admin/tunnel/node/${n.id}/rotate`, {
      method: "POST", headers: { "X-Admin-Password": password } });
    const d = await res.json().catch(() => ({}));
    if (res.ok) setCreated({ id: n.id, token: d.token, rotated: true });
    else setMsg({ t: "err", m: errText(d.detail, "ساختِ توکنِ تازه ناموفق بود") });
  };

  if (loading) return <PageSkeleton />;

  return (
    <div className="fx-anim">
      <SectionHead title="سرورها"
        desc="سرورهایی که agent روی آن‌ها نصب است."
        action={<button onClick={() => setAdding(true)} className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
          <PlusIcon size={14} /> افزودن سرور</button>} />

      {msg && <Msg msg={msg} />}

      {(!data?.nodes || (data.nodes || []).length === 0) ? (
        <EmptyState icon={Server} text="هنوز سروری اضافه نشده" />
      ) : (
      /* کارت‌های وضعیتِ کوتاه، پس کنار هم — نه یک ستون از
         نوارهای ۹۷۶ پیکسلی */
      <div className="fx-g3 grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(300px,1fr))" }}>
      {(data.nodes || []).map((n) => (
        <div key={n.id} className="fx-card p-5">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-3 min-w-0">
              <div className="fx-ico" style={{
                background: n.online ? "var(--ok-soft)" : "var(--hair-1)",
                width: 38, height: 38,
              }}>
                <Server size={17} style={{ color: n.online ? "var(--ok)" : "var(--muted)" }} />
              </div>
              <div className="min-w-0">
                <div className="text-[14px] font-bold text-white flex items-center gap-2">
                  {n.name}
                  <span className="text-[12px] px-2 py-0.5 rounded-full"
                    style={{
                      background: n.online ? "var(--ok-soft)" : "var(--hair-2)",
                      color: n.online ? "var(--ok)" : "var(--muted)",
                    }}>
                    {n.online ? "آنلاین" : "آفلاین"}
                  </span>
                </div>
                <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
                  {n.os_info || "هنوز خبری نداده"}
                  {n.public_ip && ` · ${n.public_ip}`}
                  {n.agent_version && ` · agent ${n.agent_version}`}
                </div>
              </div>
            </div>
            <div className="flex gap-2 shrink-0">
              {!n.online && (
                <button onClick={() => setDiag(n.id)}
                  className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
                  <ShieldCheck size={12} /> چرا آفلاین؟
                </button>
              )}
              <button onClick={() => setAsk({ kind: "rot", n })} className="fx-ico-btn"
                title="توکن جدید" aria-label="توکن جدید">
                <RefreshCw size={13} />
              </button>
              <button onClick={() => setAsk({ kind: "del", n })} className="fx-ico-btn fx-ico-danger"
                title="حذف سرور" aria-label="حذف سرور">
                <Trash2 size={13} />
              </button>
            </div>
          </div>

          {n.online && (n.cpu_percent != null || n.mem_percent != null) && (
            <div className="fx-g3 grid grid-cols-3 gap-3 mt-4">
              {[["پردازنده", n.cpu_percent], ["حافظه", n.mem_percent],
                ["دیسک", n.disk_percent]].map(([l, v], i) => (
                <div key={i} className="p-3 rounded-xl" style={{ background: "var(--surface-3)" }}>
                  <div className="flex justify-between items-baseline mb-2">
                    <span className="text-[12px]" style={{ color: "var(--muted)" }}>{l}</span>
                    <span className="text-[13px] font-bold" style={{
                      color: v == null ? "var(--muted)" : usageColor(v),
                      fontFamily: "var(--mono)",
                    }}>{v == null ? "—" : `${faNum(Math.round(v))}٪`}</span>
                  </div>
                  <div style={{ height: 4, borderRadius: 99, background: "var(--hair-2)", overflow: "hidden" }}>
                    <div style={{
                      width: `${Math.min(100, v || 0)}%`, height: "100%",
                      background: usageColor(v),
                    }} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {!n.online && (
            <div className="text-[12.5px] mt-4 px-3 py-2.5 rounded-xl flex items-center gap-2"
              style={{ background: "var(--warn-wash)", color: "var(--warn)" }}>
              <Clock size={13} className="shrink-0" />
              {n.last_seen ? `آخرین تماس: ${isoToJalaliStamp(n.last_seen)}` : "هنوز هیچ تماسی نگرفته — دستور نصب اجرا شده؟"}
            </div>
          )}

          <div className="flex items-center justify-between mt-4 pt-3 flex-wrap gap-2"
            style={{ borderTop: "1px solid var(--border)" }}>
            <span className="text-[13px]" style={{ color: "var(--muted)" }}>
              {faNum(n.running_count)} از {faNum(n.tunnel_count)} تانل در حال کار
            </span>
            <span className="text-[12px]" dir="ltr"
              style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
              {n.token}
            </span>
          </div>
        </div>
      ))}
      </div>
      )}

      {adding && (
        <Modal title="افزودن سرور" onClose={() => setAdding(false)}>
          <Field label="نام سرور" hint="مثلاً: تهران — پارس‌پک">
            <input className="fx-input" value={name} onChange={(e) => setName(e.target.value)}
              placeholder="سرور ایران" />
          </Field>
          <Field label="یادداشت (اختیاری)">
            <input className="fx-input" value={note} onChange={(e) => setNote(e.target.value)}
              placeholder="مشخصات یا محل سرور" />
          </Field>
          <InfoBox>
            بعد از ساخت، یک دستور نصب می‌گیرید که روی سرور اجرا می‌کنید.
            سرور شما هیچ پورتی باز نمی‌کند و رمزی جایی ذخیره نمی‌شود.
          </InfoBox>
          <button onClick={add} disabled={busy || !name.trim()}
            className="fx-btn w-full py-3 text-[14px] flex items-center justify-center gap-2 mt-4">
            {busy ? <Loader2 size={14} className="animate-spin" /> : <PlusIcon size={14} />}
            ساخت و دریافت دستور نصب
          </button>
        </Modal>
      )}

      {created && <AgentInstallModal data={created} onClose={() => setCreated(null)} />}
      {diag && <NodeDiagnoseModal nodeId={diag} password={password}
        onClose={() => setDiag(null)} />}
      {ask && ask.kind === "del" && (
        <ConfirmModal title={`حذفِ «${ask.n.name}»`} confirmLabel="حذف سرور"
          desc={(ask.n.tunnel_count
            ? `${faNum(ask.n.tunnel_count)} تانلِ این سرور هم از پنل پاک می‌شود؛ سرویس‌هایشان روی خودِ سرور می‌مانند تا دستی برشان دارید. `
            : "") + "agent دیگر به پنل وصل نمی‌شود."}
          onCancel={() => setAsk(null)} onConfirm={() => remove(ask.n)} />
      )}
      {ask && ask.kind === "rot" && (
        <ConfirmModal title={`توکنِ تازه برای «${ask.n.name}»`} confirmLabel="توکن تازه بساز"
          desc="توکنِ فعلی همین حالا باطل می‌شود و این سرور تا اجرای دوباره‌ی دستورِ نصب قطع می‌ماند. فقط اگر توکن لو رفته ادامه دهید."
          onCancel={() => setAsk(null)} onConfirm={() => rotate(ask.n)} />
      )}
    </div>
  );
}

/** چرا نود آفلاین است */
export function NodeDiagnoseModal({ nodeId, password, onClose }) {
  const [d, setD] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/api/admin/tunnel/node/${nodeId}/check`, {
      headers: { "X-Admin-Password": password },
    }).then((r) => r.json()).then(setD).catch(() => setD({ steps: [] }));
  }, [nodeId]);

  const copy = (t) => navigator.clipboard?.writeText(t);

  return (
    <Modal title="چرا نود آفلاین است" onClose={onClose} width="520px">
      {!d ? (
        <PageSkeleton />
      ) : (
        <>
          {d.steps?.map((s, i) => (
            <div key={i} className="flex gap-3 py-2.5"
              style={{ borderBottom: "1px solid var(--border)" }}>
              <div className="shrink-0 mt-0.5">
                {s.ok ? <CheckCircle2 size={15} style={{ color: "var(--ok)" }} />
                      : <XCircle size={15} style={{ color: "var(--danger)" }} />}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-semibold"
                  style={{ color: s.ok ? "var(--text)" : "var(--danger)" }}>{s.title}</div>
                {errText(s.detail) && (
                  <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
                    {errText(s.detail)}
                  </div>
                )}
                {s.hint && (
                  <div className="text-[13px] mt-2 px-2.5 py-1.5 rounded-lg leading-relaxed"
                    style={{ color: "var(--warn)", background: "var(--warn-wash)" }}>
                    {s.hint}
                  </div>
                )}
              </div>
            </div>
          ))}

          <div className="mt-4">
            <div className="text-[13px] font-semibold text-white mb-2.5">
              روی سرور ایران اجرا کنید
            </div>
            {d.commands?.map((cm, i) => (
              <div key={i} className="mb-2">
                <div className="text-[12px] mb-1" style={{ color: "var(--muted)" }}>
                  {cm.label}
                </div>
                <div onClick={() => copy(cm.cmd)}
                  className="rounded-lg px-3 py-2 cursor-pointer" dir="ltr"
                  style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
                  <code className="text-[13px]"
                    style={{ color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
                    {cm.cmd}
                  </code>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </Modal>
  );
}

/** دستور نصب agent */
export function AgentInstallModal({ data, onClose }) {
  const [copied, setCopied] = useState(false);
  const panel = typeof window !== "undefined" ? window.location.origin : "";
  const cmd = `curl -fsSL "${panel}/api/agent/install.sh?token=${data.token}&panel=${panel}" | sudo bash`;

  const copy = () => {
    navigator.clipboard?.writeText(cmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Modal title={data.rotated ? "توکن جدید" : "نصب روی سرور"} onClose={onClose} width="560px">
      <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
        {data.rotated
          ? "توکن قبلی باطل شد. agent را با این دستور دوباره نصب کنید."
          : "این دستور را روی سرور ایران اجرا کنید. کمتر از یک دقیقه طول می‌کشد."}
      </p>

      <div className="rounded-xl p-3.5 mb-3" dir="ltr"
        style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
        <code className="text-[13px] break-all block leading-relaxed"
          style={{ color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
          {cmd}
        </code>
      </div>

      <button title="کپی" onClick={copy}
        className="fx-btn w-full py-2.5 text-[14px] flex items-center justify-center gap-2">
        {copied ? <><Check size={14} /> کپی شد</> : <><Copy size={14} /> کپی دستور</>}
      </button>

      <InfoBox tone="warn">
        این دستور فقط یک‌بار نمایش داده می‌شود. توکن داخلش کلید دسترسی
        agent است — جایی که دیگران ببینند نگذارید.
      </InfoBox>
    </Modal>
  );
}

/* ── فهرست تانل‌ها ── */
export function TunnelList({ password }) {
  const { data, loading, reload } = useTunnel(password);
  const [adding, setAdding] = useState(false);
  const [cfgFor, setCfgFor] = useState(null);
  const [monFor, setMonFor] = useState(null);
  const [jobFor, setJobFor] = useState(null);
  const [delFor, setDelFor] = useState(null);
  const [msg, setMsg] = useState(null);

  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(t); } }, [msg]);

  const act = async (id, what) => {
    const url = what === "deploy"
      ? `${API_URL}/api/admin/tunnel/${id}/deploy`
      : `${API_URL}/api/admin/tunnel/${id}/action/${what}`;
    const res = await fetch(url, { method: "POST", headers: { "X-Admin-Password": password } });
    const d = await res.json().catch(() => ({}));
    setMsg(!res.ok ? { t: "err", m: errText(d.detail, "ناموفق") }
      : d.foreignError ? { t: "err", m: `سمت ایران در صف است؛ سمت خارج نه — ${d.foreignError}` }
      : { t: "ok", m: what === "deploy" ? "در صف اعمال قرار گرفت" : "دستور فرستاده شد" });
    reload();
  };

  /* حذف با یک کلیک و بی‌پاسخ بود: دکمه‌ی سطل کنارِ «کانفیگ» می‌نشست،
     تانل را بی‌پرسش پاک می‌کرد، و اگر بکند خطا می‌داد صفحه فقط تازه
     می‌شد و تانل سرِ جایش می‌ماند — بی‌هیچ توضیحی. */
  const remove = async (t) => {
    setDelFor(null);
    const res = await fetch(`${API_URL}/api/admin/tunnel/${t.id}`, {
      method: "DELETE", headers: { "X-Admin-Password": password } });
    const d = await res.json().catch(() => ({}));
    setMsg(res.ok ? { t: "ok", m: `«${t.name}» حذف شد` } : { t: "err", m: errText(d.detail, "حذف ناموفق بود") });
    reload();
  };

  if (loading) return <PageSkeleton />;

  const hasNodes = data?.nodes?.length > 0;

  return (
    <div className="fx-anim">
      <SectionHead title="تانل‌ها"
        desc="اتصال بین سرور ایران و سرور خارج."
        action={hasNodes && (
          <button onClick={() => setAdding(true)} className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5">
            <PlusIcon size={14} /> تانل جدید
          </button>
        )} />

      {msg && <Msg msg={msg} />}

      {!hasNodes ? (
        <EmptyState icon={Server} text="اول از بخش «سرورها» یک سرور اضافه کنید" />
      ) : (data.tunnels || []).length === 0 ? (
        <EmptyState icon={Network} text="هنوز تانلی ساخته نشده" />
      ) : (data.tunnels || []).map((t) => {
        const st = TUN_STATUS[t.status] || TUN_STATUS.pending;
        const ec = ENGINE_COLOR[t.engine] || "var(--accent-2)";
        return (
          <div key={t.id} className="fx-card fx-tun p-4 mb-3" style={{ "--tun-tone": st.color }}>
            {/* سر و پورت‌ها و وضعیت در یک ردیف: پیش‌تر سه ردیفِ جدا با
                فاصله‌ی ۱۶ پیکسلی بودند و هر کارت ۱۹۰ پیکسل می‌شد، که
                نیمش خالی بود */}
            <div className="flex items-center gap-3 flex-wrap">
              <span className="fx-live-dot" style={{ background: st.color,
                boxShadow: `0 0 0 3px color-mix(in srgb, ${st.color} 18%, transparent)` }} />
              <div className="min-w-0 flex-1">
                <div className="text-[14px] font-bold text-white flex items-center gap-2 flex-wrap">
                  {t.name}
                  <span className="fx-pill" style={{ background: `color-mix(in srgb, ${ec} 14%, transparent)`, color: ec }}>
                    {t.engineName} · {t.transport}
                  </span>
                  <span className="fx-pill" style={{ background: `color-mix(in srgb, ${st.color} 14%, transparent)`, color: st.color }}>
                    {st.label}
                  </span>
                </div>
                <div className="text-[12px] mt-1 flex items-center gap-2 flex-wrap" style={{ color: "var(--muted)" }}>
                  <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>{t.node_name} → {t.remote_host}:{t.bridge_port}</span>
                  <span className="flex gap-1 flex-wrap">
                    {(t.ports || []).map((p, i) => (
                      <span key={i} className="fx-port" dir="ltr">
                        {p.local === p.remote ? p.local : `${p.local}→${p.remote}`}
                      </span>
                    ))}
                  </span>
                  {t.last_check && (
                    <span className="flex items-center gap-1" title="آخرین تغییرِ وضعیت">
                      <Clock size={11} />{isoToJalaliStamp(t.last_check)}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {t.last_error && (
              <div className="text-[12px] px-3 py-2 rounded-lg mt-3 break-words"
                style={{ background: "var(--danger-wash)", color: "var(--danger)" }}>
                {t.last_error.slice(0, 240)}
              </div>
            )}
            {!t.nodeOnline && (
              <div className="text-[12px] mt-3" style={{ color: "var(--warn)" }}>
                سرور آفلاین است — دستورها وقتی وصل شود اجرا می‌شوند
              </div>
            )}

            <div className="flex gap-1.5 flex-wrap items-center mt-3 pt-3" style={{ borderTop: "1px solid var(--border)" }}>
              <button onClick={() => act(t.id, "deploy")} disabled={!t.nodeOnline}
                className="fx-btn px-3 py-1.5 text-[12.5px] flex items-center gap-1.5"
                style={!t.nodeOnline ? { opacity: .4, cursor: "not-allowed" } : {}}>
                <UploadCloud size={12} /> اعمال
              </button>
              {["restart", "stop"].map((w) => (
                <button key={w} onClick={() => act(t.id, w)} disabled={!t.nodeOnline}
                  className="fx-btn-g px-3 py-1.5 text-[12.5px]"
                  style={!t.nodeOnline ? { opacity: .4, cursor: "not-allowed" } : {}}>
                  {{ restart: "ری‌استارت", stop: "توقف" }[w]}
                </button>
              ))}
              {/* لاگ و وضعیت جواب می‌خواهند، نه فقط «فرستاده شد» — پنجره
                  تا رسیدنِ پاسخِ ایجنت صبر می‌کند و نشانش می‌دهد */}
              <button onClick={() => setJobFor({ t, kind: "status" })} disabled={!t.nodeOnline}
                className="fx-btn-g px-3 py-1.5 text-[12.5px] flex items-center gap-1.5"
                style={!t.nodeOnline ? { opacity: .4, cursor: "not-allowed" } : {}}>
                <CheckCircle2 size={12} /> وضعیت
              </button>
              <button onClick={() => setJobFor({ t, kind: "logs" })} disabled={!t.nodeOnline}
                className="fx-btn-g px-3 py-1.5 text-[12.5px] flex items-center gap-1.5"
                style={!t.nodeOnline ? { opacity: .4, cursor: "not-allowed" } : {}}>
                <FileText size={12} /> لاگ
              </button>
              <button onClick={() => setMonFor(t)}
                className="fx-btn-g px-3 py-1.5 text-[12.5px] flex items-center gap-1.5">
                <Activity size={12} /> کیفیت
              </button>
              <button onClick={() => setCfgFor(t)} className="fx-btn-g px-3 py-1.5 text-[12.5px] flex items-center gap-1.5">
                <Copy size={12} /> کانفیگ خارج
              </button>
              <button title="حذف این تانل" aria-label="حذف این تانل" onClick={() => setDelFor(t)}
                className="fx-ico-btn fx-ico-danger mr-auto" style={{ width: 32, height: 32 }}>
                <Trash2 size={13} />
              </button>
            </div>
          </div>
        );
      })}

      {adding && (
        <TunnelForm password={password} nodes={data.nodes || []} engines={data.engines || []}
          onClose={() => setAdding(false)}
          onDone={() => { setAdding(false); reload(); setMsg({ t: "ok", m: "تانل ساخته شد" }); }} />
      )}

      {cfgFor && <TunnelConfigModal tunnel={cfgFor} password={password}
        onClose={() => setCfgFor(null)} />}
      {monFor && <TunnelMonitorModal tunnel={monFor} password={password}
        onClose={() => setMonFor(null)} />}
      {jobFor && <TunnelJobModal tunnel={jobFor.t} kind={jobFor.kind} password={password}
        onDone={reload} onClose={() => setJobFor(null)} />}
      {delFor && <ConfirmModal title={`حذفِ «${delFor.name}»`}
        desc="سرویسِ تانل روی سرور هم برداشته می‌شود و اتصال‌های فعالِ روی این پورت‌ها قطع می‌شوند."
        confirmLabel="حذف تانل" onCancel={() => setDelFor(null)} onConfirm={() => remove(delFor)} />}
    </div>
  );
}

/* systemd تاریخ را «Wed 2026-09-24 08:12:03 UTC» می‌دهد — میلادی و خام */
function sinceStamp(v) {
  const m = /(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})/.exec(String(v || ""));
  return m ? `${isoToJalaliStamp(`${m[1]}T${m[2]}`)}${/UTC/.test(v) ? " (UTC)" : ""}` : String(v || "—");
}

const JOB_LABEL = { apply: "اعمال", install: "نصب موتور", start: "روشن", stop: "توقف", restart: "ری‌استارت",
                    status: "وضعیت", logs: "لاگ", monitor: "سنجش", remove: "حذف" };
const JOB_STATE = {
  queued: { l: "در صف", c: "var(--muted)" }, taken: { l: "در حال اجرا", c: "var(--warn)" },
  done: { l: "انجام شد", c: "var(--ok)" }, failed: { l: "ناموفق", c: "var(--danger)" },
};

/* ── پاسخِ ایجنت برای لاگ و وضعیت ──
   ایجنت هر ۳۰ ثانیه سر می‌زند؛ پس پاسخ فوری نیست. پنجره کار را در صف
   می‌گذارد، هر ۲.۵ ثانیه می‌پرسد، و تا ۹۰ ثانیه صبر می‌کند — بعد صریح
   می‌گوید چرا چیزی نیامده، نه اینکه خالی بماند. */
function TunnelJobModal({ tunnel, kind, password, onClose, onDone }) {
  const [jobs, setJobs] = useState(null);
  const [err, setErr] = useState(null);
  const [phase, setPhase] = useState("send");      // send | wait | done | timeout
  const since = useRef(null);

  useEffect(() => {
    let alive = true;
    let timer;
    const t0 = Date.now();
    const H = { "X-Admin-Password": password };
    const load = async () => {
      const r = await fetch(`${API_URL}/api/admin/tunnel/${tunnel.id}/jobs?limit=8`, { headers: H });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(errText(d.detail, "خواندنِ کارها ناموفق بود"));
      return d.jobs || [];
    };
    (async () => {
      try {
        const before = await load();
        since.current = before.length ? before[0].id : 0;
        if (alive) setJobs(before);
        const r = await fetch(`${API_URL}/api/admin/tunnel/${tunnel.id}/action/${kind}`,
          { method: "POST", headers: H });
        const d = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(errText(d.detail, "فرستادنِ دستور ناموفق بود"));
        if (alive) setPhase("wait");
        const tick = async () => {
          if (!alive) return;
          try {
            const js = await load();
            if (!alive) return;
            setJobs(js);
            const mine = js.find((j) => j.id > since.current && j.action === kind);
            if (mine && (mine.status === "done" || mine.status === "failed")) {
              setPhase("done");
              if (onDone) onDone();
              return;
            }
            if (Date.now() - t0 > 90000) { setPhase("timeout"); return; }
          } catch (e) { setErr(e.message); return; }
          timer = setTimeout(tick, 2500);
        };
        tick();
      } catch (e) { if (alive) setErr(e.message); }
    })();
    return () => { alive = false; clearTimeout(timer); };
  }, []);

  const mine = since.current == null ? null
    : (jobs || []).find((j) => j.id > since.current && j.action === kind);
  let parsed = null;
  if (mine && kind === "status" && mine.status === "done") {
    try { parsed = JSON.parse(mine.result || "{}"); } catch (e) { parsed = null; }
  }
  const others = (jobs || []).filter((j) => !mine || j.id !== mine.id);

  return (
    <Modal title={`${kind === "logs" ? "لاگِ" : "وضعیتِ"} «${tunnel.name}»`} onClose={onClose} width="620px">
      {err ? <Msg msg={{ t: "err", m: err }} />
        : phase === "timeout" ? (
          <InfoBox tone="warn">
            ایجنتِ «{tunnel.node_name}» در ۹۰ ثانیه جواب نداد. کار در صف مانده و با چک‌اینِ بعدی
            اجرا می‌شود — اگر سرور در «سرورها» آفلاین است، اول آن را درست کنید.
          </InfoBox>
        ) : !mine || mine.status === "queued" || mine.status === "taken" ? (
          <div className="flex items-center gap-2.5 text-[13px] py-3" style={{ color: "var(--muted)" }}>
            <Loader2 size={15} className="animate-spin" />
            {phase === "send" ? "در حالِ فرستادن…"
              : mine && mine.status === "taken" ? "ایجنت برداشت؛ منتظرِ نتیجه…"
              : "در صف — ایجنت هر ۳۰ ثانیه سر می‌زند"}
          </div>
        ) : mine.status === "failed" ? (
          <pre className="fx-pre fx-pre-err">{mine.result || "بدون پیام"}</pre>
        ) : parsed ? (
          <div className="fx-rowlist text-[13px]">
            <div className="flex justify-between"><span style={{ color: "var(--muted)" }}>سرویس</span>
              <span style={{ color: parsed.running ? "var(--ok)" : "var(--danger)" }}>
                {parsed.running ? "در حال اجرا" : "خاموش"}</span></div>
            <div className="flex justify-between"><span style={{ color: "var(--muted)" }}>systemd</span>
              <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>{parsed.state} / {parsed.sub || "—"}</span></div>
            <div className="flex justify-between"><span style={{ color: "var(--muted)" }}>ری‌استارت‌ها</span>
              <span style={{ color: Number(parsed.restarts) > 3 ? "var(--warn)" : "var(--text)" }}>{faNum(parsed.restarts || 0)}</span></div>
            {parsed.since && <div className="flex justify-between"><span style={{ color: "var(--muted)" }}>آخرین شروع</span>
              <span>{sinceStamp(parsed.since)}</span></div>}
          </div>
        ) : (
          <pre className="fx-pre">{mine.result || "خروجی خالی بود"}</pre>
        )}

      {others.length > 0 && (
        <div className="mt-4">
          <div className="text-[12px] font-semibold mb-1.5" style={{ color: "var(--muted)" }}>کارهای اخیرِ این تانل</div>
          <div className="fx-rowlist">
            {others.slice(0, 6).map((j) => {
              const st = JOB_STATE[j.status] || JOB_STATE.queued;
              return (
                <div key={j.id} className="flex items-center gap-2 text-[12.5px]">
                  <span className="text-white">{JOB_LABEL[j.action] || j.action}</span>
                  <span className="fx-pill" style={{ background: `color-mix(in srgb, ${st.c} 14%, transparent)`, color: st.c }}>{st.l}</span>
                  <span className="mr-auto" style={{ color: "var(--muted)" }}>{isoToJalaliStamp(j.done_at || j.created_at)}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </Modal>
  );
}

/** ساخت تانل */
export function TunnelForm({ password, nodes, engines, onClose, onDone }) {
  const [f, setF] = useState({
    name: "", engine: "backhaul", transport: "tcpmux",
    node_id: nodes[0]?.id || "", remote_host: "", bridge_port: 3080,
  });
  const [ports, setPorts] = useState([{ local: 443, remote: 443 }]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const eng = engines.find((e) => e.key === f.engine);

  const submit = async () => {
    setBusy(true); setErr("");
    try {
      const res = await fetch(`${API_URL}/api/admin/tunnel`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ ...f, ports }),
      });
      const d = await res.json();
      if (res.ok) onDone();
      else setErr(errText(d.detail, "ساخت ناموفق"));
    } catch { setErr("اتصال برقرار نشد"); }
    finally { setBusy(false); }
  };

  return (
    <Modal title="تانل جدید" onClose={onClose} width="560px"
      footer={
        <button onClick={submit} disabled={busy || !f.name.trim() || !f.remote_host.trim()}
          className="fx-btn w-full py-3 text-[14px] flex items-center justify-center gap-2">
          {busy ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
          ساخت تانل
        </button>
      }>
      {/* راهنمای کامل — چون بدون این، معلوم نیست چه چیزی کجا می‌رود */}
      <div className="rounded-xl p-4 mb-4"
        style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>

        {/* dir="ltr" عمدی است: فلش‌ها به راست می‌روند، پس ترتیبِ
            مرحله‌ها هم باید از چپ شروع شود. ولی مونو از روی کلِ خط
            برداشته شد و فقط روی خودِ فلش‌ها ماند — JetBrains Mono
            گلیف فارسی ندارد و این سه برچسب را به مونوی سیستم
            می‌انداخت، بسیار پهن‌تر از بقیه‌ی راهنما. */}
        <div className="flex items-center gap-2 mb-3 text-[13px] flex-wrap fx-ltr-ok" dir="ltr">
          <span style={{ color: "var(--muted)" }}>مشتری</span>
          <span style={{ color: "var(--accent-2)", fontFamily: "var(--mono)" }}>──►</span>
          <span style={{ color: "var(--ok)", fontWeight: 700 }}>سرور ایران</span>
          <span style={{ color: "var(--accent-2)", fontFamily: "var(--mono)" }}>──►</span>
          <span style={{ color: "var(--dim)" }}>سرور خارج</span>
        </div>

        <div className="text-[13px] leading-relaxed mb-3" style={{ color: "var(--muted)" }}>
          مشتری به <b style={{ color: "var(--ok)" }}>سرور ایران</b> وصل می‌شود.
          سرور ایران ترافیک را از تانل به سرور خارج می‌فرستد.
        </div>

        <div className="text-[13px] font-semibold mb-2" style={{ color: "var(--dim)" }}>
          سه مرحله:
        </div>
        {[
          ["این فرم را پر کنید", "پورت‌هایی که مشتری به آن‌ها وصل می‌شود"],
          ["دکمه‌ی «اعمال» را بزنید", "agent روی سرور ایران خودش نصب و راه‌اندازی می‌کند"],
          ["کانفیگ سرور خارج را کپی کنید",
           "چون آنجا agent نصب نیست، این یک مرحله دستی است"],
        ].map(([t, d], i) => (
          <div key={i} className="flex gap-2.5 mb-2">
            <span className="shrink-0 flex items-center justify-center text-[12px] font-bold"
              style={{
                width: 18, height: 18, borderRadius: "50%",
                background: "var(--accent-soft)", color: "var(--accent-2)",
              }}>{faNum(i + 1)}</span>
            <div className="min-w-0">
              <div className="text-[13px]" style={{ color: "var(--dim)" }}>{t}</div>
              <div className="text-[12px] mt-0.5" style={{ color: "var(--muted)" }}>{d}</div>
            </div>
          </div>
        ))}
      </div>

      <Field label="نام">
        <input className="fx-input" value={f.name}
          onChange={(e) => setF({ ...f, name: e.target.value })}
          placeholder="تانل اصلی" />
      </Field>

      <Field label="موتور">
        <div className="fx-g4 grid grid-cols-2 gap-2">
          {engines.map((e) => {
            const on = f.engine === e.key;
            const col = ENGINE_COLOR[e.key];
            return (
              <button key={e.key}
                onClick={() => setF({ ...f, engine: e.key, transport: e.default_transport })}
                className="p-3 rounded-xl text-right"
                style={{
                  background: on ? `color-mix(in srgb, ${col} 12%, transparent)` : "var(--surface-3)",
                  border: `1px solid ${on ? col : "var(--border)"}`,
                }}>
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-bold" style={{ color: on ? col : "var(--dim)" }}>
                    {e.name}
                  </span>
                  {e.recommended && (
                    <span className="text-[11px] px-1.5 py-0.5 rounded"
                      style={{ background: "var(--ok-soft)", color: "var(--ok)" }}>
                      پیشنهادی
                    </span>
                  )}
                </div>
                <div className="text-[12px] mt-1 leading-relaxed" style={{ color: "var(--muted)" }}>
                  {e.desc}
                </div>
              </button>
            );
          })}
        </div>
      </Field>

      <div className="fx-g3 grid grid-cols-2 gap-3">
        <Field label="سرور ایران" hint="پورت‌ها اینجا باز می‌شوند">
          <select className="fx-input" value={f.node_id}
            onChange={(e) => setF({ ...f, node_id: e.target.value })}>
            {nodes.map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
          </select>
        </Field>
        <Field label="سرور خارج"
          hint="اگر agent دارد، پنل خودش راه‌اندازی می‌کند">
          <select className="fx-input" value={f.foreign_node || ""}
            onChange={(e) => setF({ ...f, foreign_node: e.target.value })}>
            <option value="">دستی — کانفیگ را کپی می‌کنم</option>
            {nodes.filter((n) => String(n.id) !== String(f.node_id))
              .map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
          </select>
        </Field>
      </div>

      <div className="fx-g3 grid grid-cols-2 gap-3">
        <Field label="پروتکل انتقال">
          <select className="fx-input" value={f.transport}
            onChange={(e) => setF({ ...f, transport: e.target.value })}>
            {(eng?.transports || []).map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </Field>
      </div>

      <div className="fx-g3 grid grid-cols-2 gap-3">
        <Field label="آی‌پی عمومی سرور ایران"
          hint="همان سروری که بالا انتخاب کردید — سرور خارج به این آدرس وصل می‌شود">
          <input className="fx-input" dir="ltr" value={f.remote_host}
            onChange={(e) => setF({ ...f, remote_host: e.target.value })}
            placeholder="1.2.3.4" style={{ fontFamily: "var(--mono)" }} />
        </Field>
        <Field label="پورت ارتباط" hint="پورتی که دو سرور از آن حرف می‌زنند">
          <input className="fx-input" type="text" inputMode="numeric" dir="ltr"
            value={f.bridge_port}
            onChange={(e) => setF({ ...f,
              bridge_port: e.target.value.replace(/[^0-9]/g, "").slice(0, 5) })}
            placeholder="3080"
            style={{ fontFamily: "var(--mono)" }} />
        </Field>
      </div>

      <Field label="پورت‌ها" hint="پورت‌هایی که مشتری به آن‌ها وصل می‌شود">
        {/* هر پورت یک قوطی باریک — عدد چهار رقمی به عرض بیشتری نیاز ندارد،
            و کنار هم بودنشان دیدن کل فهرست را آسان می‌کند */}
        <div className="flex gap-2 flex-wrap mb-2.5">
          {ports.map((p, i) => (
            <div key={i} className="flex items-center rounded-xl overflow-hidden"
              style={{ background: "var(--surface-3)", border: "1px solid var(--border-2)" }}>
              {/* type=text نه number — چون فلش‌های بالا/پایین برای عددی
                  که مستقیم تایپ می‌شود فقط مزاحمند */}
              <input type="text" inputMode="numeric" dir="ltr"
                value={p.local || ""}
                onChange={(e) => {
                  const digits = e.target.value.replace(/[^0-9]/g, "").slice(0, 5);
                  const v = digits ? parseInt(digits, 10) : 0;
                  const l = [...ports];
                  l[i] = { local: v, remote: v };
                  setPorts(l);
                }}
                placeholder="443"
                style={{
                  width: 68, background: "transparent", border: "none", outline: "none",
                  color: "var(--text)", fontSize: 12.5, padding: "8px 10px",
                  textAlign: "center", fontFamily: "var(--mono)",
                }} />
              <button title="حذف این پورت" onClick={() => setPorts(ports.filter((_, x) => x !== i))}
                className="flex items-center justify-center transition-colors"
                style={{
                  width: 28, height: 34, border: "none", cursor: "pointer",
                  background: "var(--hair-1)", color: "var(--muted)",
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = "var(--danger)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = "var(--muted)"; }}>
                <X size={12} />
              </button>
            </div>
          ))}

          <button onClick={() => setPorts([...ports, { local: 0, remote: 0 }])}
            className="flex items-center gap-1.5 px-3 rounded-xl text-[13px] transition-all"
            style={{
              height: 34, background: "transparent",
              border: "1px dashed var(--border-2)", color: "var(--muted)", cursor: "pointer",
            }}>
            <PlusIcon size={12} /> افزودن
          </button>
        </div>

        {/* میان‌برهای پورت‌های رایج */}
        <div className="flex gap-1.5 flex-wrap">
          {[443, 8443, 2053, 2087, 80].map((q) => {
            const has = ports.some((p) => p.local === q);
            return (
              <button key={q}
                onClick={() => setPorts(has
                  ? ports.filter((p) => p.local !== q)
                  : [...ports, { local: q, remote: q }])}
                className="px-2.5 py-1 rounded-lg text-[12px] transition-all"
                style={{
                  background: has ? "var(--accent-soft)" : "transparent",
                  border: `1px solid ${has ? "var(--accent-edge)" : "var(--border)"}`,
                  color: has ? "var(--accent-2)" : "var(--muted)",
                  fontFamily: "var(--mono)",
                  cursor: "pointer",
                }}>
                {q}
              </button>
            );
          })}
        </div>
      </Field>

      {err && <div className="text-[13px] p-3 rounded-xl mt-3"
        style={{ background: "var(--danger-soft)", color: "var(--danger)" }}>{err}</div>}

    </Modal>
  );
}


/* ── کیفیت تانل ── */

/* همان مرزهای backend/tunnels.py (LATENCY_STEPS) — test-nodes برابری را
   می‌سنجد. رنگِ هر میله از همان برچسبی می‌آید که خلاصه می‌گوید. */
export const LATENCY_STEPS = [60, 150, 300];
export function latencyColor(ms) {
  const v = Number(ms) || 0;
  const q = v > LATENCY_STEPS[2] ? "ضعیف" : v > LATENCY_STEPS[1] ? "متوسط"
          : v > LATENCY_STEPS[0] ? "خوب" : "عالی";
  return QUALITY_COLOR[q];
}

export const QUALITY_COLOR = {
  "عالی": "var(--ok)",
  "خوب": "#5AA9E6",
  "متوسط": "var(--warn)",
  "ضعیف": "var(--danger)",
  "قطع": "var(--danger)",
  "نامشخص": "var(--muted)",
};

export function TunnelMonitorModal({ tunnel, password, onClose }) {
  const [m, setM] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/tunnel/${tunnel.id}/metrics`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setM(d);
      return d;
    } catch {
      setM({ samples: [], summary: null });
      return null;
    }
  };

  useEffect(() => { load(); }, [tunnel.id]);

  const measure = async () => {
    setBusy(true);
    const before = m?.samples?.length || 0;
    setErr(null);
    try {
      const res = await fetch(`${API_URL}/api/admin/tunnel/${tunnel.id}/monitor`, {
        method: "POST",
        headers: { "X-Admin-Password": password },
      });
      // درخواستِ ردشده پیش‌تر ۴۸ ثانیه بی‌هدف منتظرِ نتیجه می‌ماند
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        setErr(errText(j.detail, "سنجش در صف قرار نگرفت"));
        return;
      }
      // agent تا ۳۰ ثانیه بعد سر می‌زند، پس چند بار نتیجه را چک می‌کنیم
      for (let i = 0; i < 12; i++) {
        await new Promise((r) => setTimeout(r, 4000));
        const d = await load();
        if ((d?.samples?.length || 0) > before) break;
      }
    } finally {
      setBusy(false);
    }
  };

  const s = m?.summary;
  const detail = m?.latest?.detail || {};
  const samples = m?.samples || [];
  const qc = QUALITY_COLOR[s?.quality] || "var(--muted)";

  const Bar = ({ label, value, unit = "ms", max = 200, color }) => (
    <div className="mb-3">
      <div className="flex justify-between text-[13px] mb-1.5">
        <span style={{ color: "var(--muted)" }}>{label}</span>
        <span style={{ color: color || "var(--dim)",
                       fontFamily: "var(--mono)" }}>
          {value === null || value === undefined ? "—" : `${faNum(value)} ${unit}`}
        </span>
      </div>
      <div style={{ height: 5, borderRadius: 99,
                    background: "var(--hair-2)", overflow: "hidden" }}>
        <div style={{
          width: `${Math.min(100, ((value || 0) / max) * 100)}%`,
          height: "100%", background: color || "var(--accent)",
          transition: "width .4s ease",
        }} />
      </div>
    </div>
  );

  return (
    <Modal title={`کیفیت — ${tunnel.name}`} onClose={onClose} width="540px">
      {err && <Msg msg={{ t: "err", m: err }} />}
      {!m ? (
        <PageSkeleton />
      ) : (
        <>
          {s ? (
            <>
              <div className="rounded-2xl p-4 mb-4 text-center"
                style={{
                  background: `color-mix(in srgb, ${qc} 10%, transparent)`,
                  border: `1px solid color-mix(in srgb, ${qc} 28%, transparent)`,
                }}>
                <div className="text-[28px] font-extrabold"
                  style={{ color: qc, fontFamily: "var(--mono)" }}>
                  {faNum(s.latest)} <span className="text-[16px]">ms</span>
                </div>
                <div className="text-[13px] mt-1" style={{ color: qc }}>{s.quality}</div>
                <div className="text-[12px] mt-2" style={{ color: "var(--muted)" }}>
                  از {faNum(s.count)} سنجش · بهترین {faNum(s.best)} · بدترین {faNum(s.worst)}
                </div>
              </div>

              {samples.length > 1 && (
                <div className="mb-4">
                  <div className="text-[13px] mb-2" style={{ color: "var(--muted)" }}>روند</div>
                  <div className="flex items-end gap-1" style={{ height: 48 }}>
                    {samples.slice(-30).map((x, i) => {
                      const v = x.tcp_avg || 0;
                      const mx = Math.max(...samples.map((y) => y.tcp_avg || 0), 1);
                      const col = latencyColor(v);
                      return (
                        <div key={i} title={`${v} ms`} style={{
                          flex: 1, height: `${Math.max(8, (v / mx) * 100)}%`,
                          background: col, borderRadius: "2px 2px 0 0", opacity: 0.85,
                        }} />
                      );
                    })}
                  </div>
                </div>
              )}

              <Bar label="تاخیر TCP — همان چیزی که ترافیک واقعی حس می‌کند"
                value={s.latest} max={200}
                color={latencyColor(s.latest)} />

              {detail.icmp?.ok && (
                <Bar label="پینگ ICMP" value={detail.icmp.avg} max={200} color="#A78BFA" />
              )}
              {detail.http?.ok && (
                <Bar label="پاسخ HTTP — کل مسیر تا سرویس"
                  value={detail.http.avg} max={600} color="#5AA9E6" />
              )}

              <div className="fx-g3 grid grid-cols-3 gap-3 mt-4">
                {[["نوسان", m.latest?.jitter, "ms"],
                  ["اتلاف بسته", s.lossAvg, "٪"],
                  ["میانگین", s.average, "ms"]].map(([l, v, u], i) => (
                  <div key={i} className="p-3 rounded-xl text-center"
                    style={{ background: "var(--surface-3)" }}>
                    <div className="text-[16px] font-bold"
                      style={{ color: "var(--text)",
                               fontFamily: "var(--mono)" }}>
                      {v === null || v === undefined ? "—" : faNum(v)}
                    </div>
                    <div className="text-[11.5px] mt-1" style={{ color: "var(--muted)" }}>
                      {l} {u && `(${u})`}
                    </div>
                  </div>
                ))}
              </div>

              <InfoBox>
                تاخیر TCP از پینگ معمولی معنادارتر است، چون همان کاری را می‌کند که
                ترافیک واقعی می‌کند. اگر ICMP خوب باشد ولی TCP بالا، مشکل از خود
                تانل است نه مسیر شبکه.
              </InfoBox>
            </>
          ) : (
            <div className="text-center py-8">
              <Activity size={26} style={{ color: "var(--muted)" }} className="mx-auto mb-3" />
              <div className="text-[14px]" style={{ color: "var(--muted)" }}>
                هنوز سنجشی انجام نشده
              </div>
            </div>
          )}

          <button title="اندازه‌گیری" onClick={measure} disabled={busy || !tunnel.nodeOnline}
            className="fx-btn w-full py-3 text-[14px] flex items-center justify-center gap-2 mt-4"
            style={!tunnel.nodeOnline ? { opacity: 0.4, cursor: "not-allowed" } : {}}>
            {busy
              ? <><Loader2 size={14} className="animate-spin" /> در حال سنجش…</>
              : <><Activity size={14} /> سنجش جدید</>}
          </button>

          {!tunnel.nodeOnline && (
            <div className="text-[12px] mt-2 text-center" style={{ color: "var(--warn)" }}>
              سرور آفلاین است — دستور وقتی وصل شود اجرا می‌شود
            </div>
          )}
        </>
      )}
    </Modal>
  );
}

/** کانفیگ سمت خارج */
export function TunnelConfigModal({ tunnel, password, onClose }) {
  const [cfg, setCfg] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/api/admin/tunnel/${tunnel.id}/config?side=foreign`, {
      headers: { "X-Admin-Password": password },
    }).then((r) => r.json()).then(setCfg).catch(() => setCfg({ config: "" }));
  }, [tunnel.id]);

  const copy = () => {
    navigator.clipboard?.writeText(cfg?.config || "");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Modal title="کانفیگ سرور خارج" onClose={onClose} width="600px">
      <p className="text-[13px] mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
        این فایل را روی سرور خارج بگذارید. چون آنجا agent نصب نیست،
        این یک مرحله دستی است.
      </p>

      {!cfg ? (
        <PageSkeleton />
      ) : (
        <>
          <div className="rounded-xl p-3.5 mb-3 overflow-auto" dir="ltr"
            style={{ background: "var(--surface-3)", border: "1px solid var(--border)", maxHeight: 300 }}>
            <pre className="text-[13px] leading-relaxed whitespace-pre-wrap"
              style={{ color: "var(--dim)", fontFamily: "var(--mono)" }}>
              {cfg.config}
            </pre>
          </div>
          <div className="text-[12px] mb-3" dir="ltr"
            style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
            {cfg.filename}
          </div>
          <button title="کپی" onClick={copy}
            className="fx-btn w-full py-2.5 text-[14px] flex items-center justify-center gap-2">
            {copied ? <><Check size={14} /> کپی شد</> : <><Copy size={14} /> کپی کانفیگ</>}
          </button>
        </>
      )}
    </Modal>
  );
}


/* ── سلامت سرورها ── */

export const HEALTH_COLOR = {
  ok: "var(--ok)", warn: "var(--warn)",
  crit: "var(--danger)", unknown: "var(--muted)",
};

export const HEALTH_LABEL = {
  ok: "سالم", warn: "هشدار", crit: "مشکل جدی", unknown: "نامشخص",
};

export function SystemHealth({ password }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const later = useRef(null);

  /* خطا پیش‌تر بی‌صدا «نامشخص» می‌شد: پاسخِ ۴۰۱/۵۰۰ همان‌طور به‌جای
     داده نشسته و صفحه فقط برچسبِ خاکستری نشان می‌داد. */
  const load = async () => {
    try {
      const r = await fetch(`${API_URL}/api/admin/health/all`, {
        headers: { "X-Admin-Password": password },
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) {
        setMsg({ t: "err", m: errText(d.detail, "خواندنِ سلامتِ سرورها ناموفق بود") });
        return;
      }
      setData(d);
    } catch {
      setMsg({ t: "err", m: "اتصال به پنل برقرار نشد" });
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); return () => clearTimeout(later.current); }, [password]);
  usePolling(load, 60000, [password]);

  /* سرورِ پنل همان لحظه بررسی می‌شود، ولی نودها از راهِ ایجنت — که هر
     ۳۰ ثانیه سر می‌زند. پیش‌تر بعد از ۳ ثانیه یک‌بار بار می‌کرد و
     گزارشِ قدیمی را مثلِ نتیجه‌ی تازه نشان می‌داد. */
  const recheck = async () => {
    setBusy(true);
    let sent = 0;
    let failed = 0;
    try {
      for (const sv of data?.servers || []) {
        if (!sv.nodeId) continue;
        const r = await fetch(`${API_URL}/api/admin/health/check/${sv.nodeId}`, {
          method: "POST", headers: { "X-Admin-Password": password } }).catch(() => null);
        if (r && r.ok) sent += 1; else failed += 1;
      }
      await load();
      setMsg(failed ? { t: "err", m: `درخواست برای ${faNum(failed)} سرور فرستاده نشد` }
        : sent ? { t: "ok", m: `سرورِ پنل بررسی شد؛ گزارشِ ${faNum(sent)} سرورِ دیگر تا نیم دقیقه‌ی دیگر می‌رسد` }
        : { t: "ok", m: "سرورِ پنل دوباره بررسی شد" });
      clearTimeout(later.current);
      if (sent) later.current = setTimeout(load, 35000);
    } finally { setBusy(false); }
  };

  if (loading) return <PageSkeleton />;

  const servers = data?.servers || [];
  const worst = HEALTH_COLOR[data?.level] || "var(--muted)";
  const tally = { crit: 0, warn: 0, ok: 0, unknown: 0 };
  servers.forEach((sv) => { tally[sv.level in tally ? sv.level : "unknown"] += 1; });

  return (
    <div className="fx-anim">
      <SectionHead title="سلامت سرورها"
        desc="هر ۵ دقیقه خودکار بررسی می‌شود و اگر مشکلی پیدا شود، در تلگرام خبر می‌دهد."
        action={
          <button onClick={recheck} disabled={busy || !data}
            className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
            {busy ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
            بررسی دوباره
          </button>
        } />

      {msg && <Msg msg={msg} />}

      {data && (
        /* یک نوار، نه کارتِ ۸۰ پیکسلی برای یک کلمه: وضعیتِ کل، شمارِ
           هر سطح، و زمانِ بررسی — همه در یک خط */
        <div className="fx-health-bar mb-4" style={{ "--hb": worst }}>
          <span className="fx-live-dot on" style={{ background: worst, boxShadow: `0 0 0 3px color-mix(in srgb, ${worst} 22%, transparent)` }} />
          <span className="text-[15px] font-bold" style={{ color: worst }}>
            {HEALTH_LABEL[data.level] || "نامشخص"}
          </span>
          <span className="flex gap-1.5 flex-wrap">
            {["crit", "warn", "ok", "unknown"].filter((k) => tally[k]).map((k) => (
              <span key={k} className="fx-pill" style={{
                background: `color-mix(in srgb, ${HEALTH_COLOR[k]} 14%, transparent)`, color: HEALTH_COLOR[k] }}>
                {faNum(tally[k])} {k === "unknown" ? "بی‌گزارش" : HEALTH_LABEL[k]}
              </span>
            ))}
          </span>
          <span className="text-[12px] mr-auto flex items-center gap-1" style={{ color: "var(--muted)" }}>
            <Clock size={12} /> {data.at ? isoToJalaliStamp(data.at.replace(" ", "T")) : "—"}
          </span>
        </div>
      )}

      {servers.map((sv, i) => {
        const col = HEALTH_COLOR[sv.level] || "var(--muted)";
        const problems = (sv.checks || []).filter((c) => c.level !== "ok");
        const fine = (sv.checks || []).filter((c) => c.level === "ok");
        const none = (sv.checks || []).length === 0;
        return (
          <div key={i} className={`fx-card mb-3 ${none ? "px-5 py-3.5" : "p-5"}`}>
            <div className={`flex items-center gap-2.5 flex-wrap ${none ? "" : "mb-3"}`}>
              <Circle size={8} fill={col} strokeWidth={0} />
              <span className="text-[14px] font-bold text-white">{sv.server}</span>
              {sv.nodeId == null && <span className="fx-pill">همین سرور</span>}
              <span className="text-[12.5px]" style={{ color: col }}>{sv.summary}</span>
              {sv.at && (
                <span className="text-[12px] mr-auto" style={{ color: "var(--muted)" }}>
                  {isoToJalaliStamp(String(sv.at).replace(" ", "T"))}
                </span>
              )}
            </div>

            {problems.map((c, j) => (
              <div key={j} className="px-3.5 py-3 rounded-xl mb-2"
                style={{
                  background: c.level === "crit" ? "var(--danger-wash)" : "var(--warn-wash)",
                  border: `1px solid ${c.level === "crit" ? "var(--danger-fill)" : "var(--warn-fill)"}`,
                }}>
                <div className="flex justify-between items-baseline gap-3 flex-wrap">
                  <span className="text-[13.5px] font-semibold"
                    style={{ color: HEALTH_COLOR[c.level] }}>{c.title}</span>
                  <span className="text-[12.5px]" style={{ color: "var(--dim)" }}>
                    {errText(c.detail)}
                  </span>
                </div>
                {c.hint && (
                  <div className="text-[12.5px] mt-1.5 leading-relaxed" dir="auto"
                    style={{ color: "var(--muted)" }}>{c.hint}</div>
                )}
              </div>
            ))}

            {fine.length > 0 && (
              <div className="flex gap-1.5 flex-wrap mt-2">
                {fine.map((c, j) => (
                  <span key={j} className="text-[12px] px-2 py-1 rounded-lg"
                    style={{ background: "var(--surface-3)", color: "var(--muted)" }}
                    title={errText(c.detail)}>
                    ✓ {c.title}
                  </span>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── سلامت سرورها پایان ── */

/* ── رویدادها ── */
const EV_COLOR = { error: "var(--danger)", warn: "var(--warn)", info: "var(--muted)" };
const EV_PER = 15;

export function TunnelEvents({ password }) {
  const { data, loading } = useTunnel(password);
  const [lvl, setLvl] = useState("all");
  const [page, setPage] = useState(1);

  if (loading) return <PageSkeleton />;

  const all = data?.events || [];
  const count = (k) => all.filter((e) => e.level === k).length;
  const events = lvl === "all" ? all : all.filter((e) => e.level === lvl);
  const pages = Math.max(1, Math.ceil(events.length / EV_PER));
  const pg = Math.min(page, pages);
  const shown = events.slice((pg - 1) * EV_PER, pg * EV_PER);

  /* گروه‌بندی با روز: هر ردیف تاریخِ کامل را تکرار می‌کرد و چشم باید
     ده بار «۲ مهر ۱۴۰۵» را می‌خواند تا بفهمد کدام ماجرا مالِ امروز است. */
  const groups = [];
  shown.forEach((e) => {
    const day = isoToJalaliLabel(String(e.created_at || "").slice(0, 10));
    const g = groups[groups.length - 1];
    if (g && g.day === day) g.items.push(e); else groups.push({ day, items: [e] });
  });

  return (
    <div className="fx-anim">
      <SectionHead title="رویدادها" desc="آنچه روی سرورها و تانل‌ها اتفاق افتاده — ۴۰ رویدادِ آخر."
        action={all.length > 0 && (
          <Segmented value={lvl} onChange={(v) => { setLvl(v); setPage(1); }}
            items={[["all", `همه ${faNum(all.length)}`], ["error", `خطا ${faNum(count("error"))}`],
                    ["warn", `هشدار ${faNum(count("warn"))}`], ["info", `اطلاع ${faNum(count("info"))}`]]} />
        )} />

      {all.length === 0 ? (
        <EmptyState icon={Clock} text="هنوز رویدادی ثبت نشده" />
      ) : events.length === 0 ? (
        <EmptyState icon={CheckCircle2} tone="var(--ok)" text="در این سطح رویدادی نیست" />
      ) : (
        <>
          {groups.map((g) => (
            <div key={g.day} className="mb-3">
              <div className="fx-ev-day">{g.day}</div>
              <div className="fx-card" style={{ padding: "0 16px" }}>
                <div className="fx-rowlist fx-rowlist-pad">
                  {g.items.map((e) => (
                    <div key={e.id} className="flex items-center gap-3 flex-wrap">
                      <span className="fx-live-dot" style={{ background: EV_COLOR[e.level] || "var(--muted)" }} />
                      <span className="text-[13px] min-w-0 flex-1" style={{
                        color: e.level === "info" ? "var(--dim)" : "var(--text)" }}>{e.message}</span>
                      <span className="flex items-center gap-1.5 shrink-0 text-[11.5px]" style={{ color: "var(--muted)" }}>
                        {e.tunnel_name && <span className="fx-pill">{e.tunnel_name}</span>}
                        {e.node_name && <span className="fx-pill">{e.node_name}</span>}
                        <span style={{ fontFamily: "var(--mono)" }}>
                          {isoToJalaliStamp(e.created_at).split("، ")[1] || ""}
                        </span>
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
          <Pager page={pg} pages={pages} total={events.length} perPage={EV_PER} onPage={setPage} />
        </>
      )}
    </div>
  );
}


/* ── صورتحساب دوره ── */
