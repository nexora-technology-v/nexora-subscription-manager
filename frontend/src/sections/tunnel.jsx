/**
 * تانل‌ها و نودها.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
import React, { useState, useEffect } from "react";
import {
  Activity, AlertTriangle, Check, CheckCircle2, Circle, Clock, Copy, FileText, Loader2, Network, Plus as PlusIcon, RefreshCw, Server, ShieldCheck, Trash2, UploadCloud, X, XCircle,
} from "lucide-react";
import { API_URL } from "../lib/constants";
import { errText, faNum } from "../lib/format";
import { usePolling } from "../lib/hooks";
import { EmptyState, Field, InfoBox, Modal, Msg, PageSkeleton, SectionHead, StatTile } from "../ui/index";

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
        <div className="fx-card p-8 text-center" style={{ borderStyle: "dashed" }}>
          <AlertTriangle size={24} style={{ color: "var(--warn)" }} className="mx-auto mb-3" />
          <div className="text-[14px]" style={{ color: "var(--muted)" }}>
            {data?.error || "ماژول تانل در دسترس نیست"}
          </div>
        </div>
      </div>
    );
  }

  // پاسخ ممکن است شکل دیگری داشته باشد (خطا، نسخه‌ی قدیمی، مستاجری
  // که این بخش را ندارد). آن‌وقت صفحه باید حالت خالی نشان بدهد، نه
  // اینکه کل بخش بیفتد.
  const s = data.stats || {};

  return (
    <div className="fx-anim">
      <SectionHead title="داشبورد تانل"
        desc="سرورهای متصل و تانل‌های فعال."
        action={<button onClick={reload} className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
          <RefreshCw size={13} /> تازه‌سازی</button>} />

      {/* همان چهار عدد، ولی با زمینه: «۲ از ۳ آنلاین» چیزی می‌گوید
          که «۲» تنها نمی‌گوید. */}
      <div className="fx-g4 grid grid-cols-4 gap-3">
        <StatTile label="سرورها" icon={Server} tone="var(--accent-2)"
          value={faNum(s.nodes)}
          hint={s.nodes ? `${faNum(s.online || 0)} تا آنلاین` : "هنوز سروری اضافه نشده"} />
        <StatTile label="آنلاین" icon={Activity}
          tone={s.online === s.nodes && s.nodes ? "var(--ok)" : "var(--warn)"}
          value={faNum(s.online)}
          color={s.online === s.nodes && s.nodes ? "var(--ok)" : "var(--warn)"}
          hint={s.nodes - (s.online || 0) > 0
                ? `${faNum(s.nodes - s.online)} سرور جواب نمی‌دهد` : "همه در دسترس‌اند"} />
        <StatTile label="تانل‌ها" icon={Network} tone="var(--purple)"
          value={faNum(s.tunnels)}
          hint={s.tunnels ? `${faNum(s.running || 0)} تا در حال کار` : "هنوز تانلی ساخته نشده"} />
        <StatTile label="در حال کار" icon={CheckCircle2}
          tone={s.running === s.tunnels && s.tunnels ? "var(--ok)" : "var(--danger)"}
          value={faNum(s.running)}
          color={s.running === s.tunnels && s.tunnels ? "var(--ok)" : "var(--danger)"}
          hint={s.tunnels - (s.running || 0) > 0
                ? `${faNum(s.tunnels - s.running)} تانل خوابیده` : "هیچ تانلی نخوابیده"} />
      </div>

      {(data.nodes || []).length === 0 ? (
        <EmptyState icon={Server} text="هنوز سروری اضافه نشده"
          hint="از بخش «سرورها» یک سرور ایران اضافه کنید. یک دستور نصب می‌گیرید که روی آن سرور اجرا می‌کنید — بدون نیاز به باز کردن پورت یا دادن رمز." />
      ) : (
        <>
          <div className="fx-card p-5 mb-4">
            <div className="text-[14px] font-semibold text-white mb-4">سرورها</div>
            {(data.nodes || []).map((n, i, arr) => (
              <div key={n.id} className="flex items-center justify-between gap-3 py-3 flex-wrap"
                style={{ borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                <div className="flex items-center gap-3 min-w-0">
                  <div style={{
                    width: 8, height: 8, borderRadius: "50%",
                    background: n.online ? "var(--ok)" : "var(--muted)",
                    boxShadow: n.online ? "0 0 8px var(--ok)" : "none",
                    flexShrink: 0,
                  }} />
                  <div className="min-w-0">
                    <div className="text-[14px] font-semibold text-white">{n.name}</div>
                    <div className="text-[12px] mt-0.5" style={{ color: "var(--muted)" }}>
                      {n.os_info || "—"}{n.public_ip ? ` · ${n.public_ip}` : ""}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4 shrink-0 text-[13px]"
                  style={{ color: "var(--dim)", fontFamily: "var(--mono)" }}>
                  {n.cpu_percent != null && <span>CPU {faNum(n.cpu_percent)}٪</span>}
                  {n.mem_percent != null && <span>RAM {faNum(n.mem_percent)}٪</span>}
                  <span style={{ color: n.online ? "var(--ok)" : "var(--muted)" }}>
                    {n.running_count}/{n.tunnel_count}
                    <span className="fx-fa-sub"> تانل</span>
                  </span>
                </div>
              </div>
            ))}
          </div>

          {(data.tunnels || []).length > 0 && (
            <div className="fx-card p-5">
              <div className="text-[14px] font-semibold text-white mb-4">تانل‌های اخیر</div>
              {(data.tunnels || []).slice(0, 6).map((t, i, arr) => {
                const st = TUN_STATUS[t.status] || TUN_STATUS.pending;
                const ec = ENGINE_COLOR[t.engine] || "var(--accent-2)";
                return (
                  <div key={t.id} className="flex items-center justify-between gap-3 py-3 flex-wrap"
                    style={{ borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                    <div className="min-w-0">
                      <div className="text-[14px] font-semibold text-white">{t.name}</div>
                      <div className="text-[12px] mt-0.5" style={{ color: "var(--muted)" }}>
                        {t.node_name} · {(t.ports || []).length} پورت
                      </div>
                    </div>
                    <div className="flex items-center gap-2.5 shrink-0">
                      <span className="text-[12px] px-2 py-1 rounded-lg"
                        style={{ background: `color-mix(in srgb, ${ec} 14%, transparent)`, color: ec }}>
                        {t.engineName}
                      </span>
                      <span className="text-[13px]" style={{ color: st.color }}>{st.label}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
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

  const remove = async (id) => {
    await fetch(`${API_URL}/api/admin/tunnel/node/${id}`, {
      method: "DELETE", headers: { "X-Admin-Password": password } });
    reload();
  };

  const rotate = async (id) => {
    const res = await fetch(`${API_URL}/api/admin/tunnel/node/${id}/rotate`, {
      method: "POST", headers: { "X-Admin-Password": password } });
    const d = await res.json();
    if (res.ok) setCreated({ id, token: d.token, rotated: true });
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
                background: n.online ? "rgba(52,211,153,.12)" : "rgba(255,255,255,.04)",
                width: 38, height: 38,
              }}>
                <Server size={17} style={{ color: n.online ? "var(--ok)" : "var(--muted)" }} />
              </div>
              <div className="min-w-0">
                <div className="text-[14px] font-bold text-white flex items-center gap-2">
                  {n.name}
                  <span className="text-[12px] px-2 py-0.5 rounded-full"
                    style={{
                      background: n.online ? "rgba(52,211,153,.14)" : "rgba(255,255,255,.05)",
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
              <button onClick={() => rotate(n.id)} className="fx-ico-btn" title="توکن جدید">
                <RefreshCw size={13} />
              </button>
              <button onClick={() => remove(n.id)} className="fx-ico-btn" title="حذف">
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
                      color: v == null ? "var(--muted)"
                           : v > 85 ? "var(--danger)" : v > 65 ? "var(--warn)" : "var(--dim)",
                      fontFamily: "var(--mono)",
                    }}>{v == null ? "—" : `${faNum(v)}٪`}</span>
                  </div>
                  <div style={{ height: 4, borderRadius: 99, background: "rgba(255,255,255,.06)", overflow: "hidden" }}>
                    <div style={{
                      width: `${Math.min(100, v || 0)}%`, height: "100%",
                      background: (v || 0) > 85 ? "var(--danger)" : (v || 0) > 65 ? "var(--warn)" : "var(--accent)",
                    }} />
                  </div>
                </div>
              ))}
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
                    style={{ color: "var(--warn)", background: "rgba(251,191,36,.08)" }}>
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
  const [msg, setMsg] = useState(null);

  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 4000); return () => clearTimeout(t); } }, [msg]);

  const act = async (id, what) => {
    const url = what === "deploy"
      ? `${API_URL}/api/admin/tunnel/${id}/deploy`
      : `${API_URL}/api/admin/tunnel/${id}/action/${what}`;
    const res = await fetch(url, { method: "POST", headers: { "X-Admin-Password": password } });
    const d = await res.json().catch(() => ({}));
    setMsg(res.ok
      ? { t: "ok", m: what === "deploy" ? "در صف اعمال قرار گرفت" : "دستور فرستاده شد" }
      : { t: "err", m: errText(d.detail, "ناموفق") });
    reload();
  };

  const remove = async (id) => {
    await fetch(`${API_URL}/api/admin/tunnel/${id}`, {
      method: "DELETE", headers: { "X-Admin-Password": password } });
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
          <div key={t.id} className="fx-card p-5 mb-3">
            <div className="flex items-start justify-between gap-3 flex-wrap mb-4">
              <div className="min-w-0">
                <div className="text-[14px] font-bold text-white flex items-center gap-2 flex-wrap">
                  {t.name}
                  <span className="text-[12px] px-2 py-0.5 rounded-lg"
                    style={{ background: `color-mix(in srgb, ${ec} 14%, transparent)`, color: ec }}>
                    {t.engineName} · {t.transport}
                  </span>
                </div>
                <div className="text-[12px] mt-1.5" dir="ltr"
                  style={{ color: "var(--muted)", fontFamily: "var(--mono)", textAlign: "right" }}>
                  {t.node_name} ← {t.remote_host}:{t.bridge_port}
                </div>
              </div>
              <span className="text-[13px] px-2.5 py-1 rounded-lg shrink-0"
                style={{ background: `color-mix(in srgb, ${st.color} 12%, transparent)`, color: st.color }}>
                {st.label}
              </span>
            </div>

            <div className="flex gap-1.5 flex-wrap mb-4">
              {(t.ports || []).map((p, i) => (
                <span key={i} className="text-[12px] px-2 py-1 rounded-lg" dir="ltr"
                  style={{ background: "var(--surface-3)", color: "var(--dim)",
                           fontFamily: "var(--mono)" }}>
                  {p.local === p.remote ? p.local : `${p.local}→${p.remote}`}
                </span>
              ))}
            </div>

            {t.last_error && (
              <div className="text-[12px] p-2.5 rounded-lg mb-3"
                style={{ background: "rgba(248,113,113,.08)", color: "var(--danger)" }}>
                {t.last_error.slice(0, 160)}
              </div>
            )}

            <div className="flex gap-2 flex-wrap pt-3" style={{ borderTop: "1px solid var(--border)" }}>
              <button onClick={() => act(t.id, "deploy")} disabled={!t.nodeOnline}
                className="fx-btn px-3 py-2 text-[13px] flex items-center gap-1.5"
                style={!t.nodeOnline ? { opacity: .4, cursor: "not-allowed" } : {}}>
                <UploadCloud size={12} /> اعمال
              </button>
              {["restart", "stop", "logs"].map((w) => (
                <button key={w} onClick={() => act(t.id, w)} disabled={!t.nodeOnline}
                  className="fx-btn-g px-3 py-2 text-[13px]"
                  style={!t.nodeOnline ? { opacity: .4, cursor: "not-allowed" } : {}}>
                  {{ restart: "ری‌استارت", stop: "توقف", logs: "لاگ" }[w]}
                </button>
              ))}
              <button onClick={() => setMonFor(t)}
                className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
                <Activity size={12} /> کیفیت
              </button>
              <button onClick={() => setCfgFor(t)} className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
                <FileText size={12} /> کانفیگ سرور خارج
              </button>
              <button title="حذف این تانل" onClick={() => remove(t.id)} className="fx-ico-btn mr-auto" style={{ width: 30, height: 30 }}>
                <Trash2 size={12} />
              </button>
            </div>

            {!t.nodeOnline && (
              <div className="text-[12px] mt-3" style={{ color: "var(--warn)" }}>
                سرور آفلاین است — دستورها وقتی وصل شود اجرا می‌شوند
              </div>
            )}
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
    </div>
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
                      style={{ background: "rgba(52,211,153,.14)", color: "var(--ok)" }}>
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
                  background: "rgba(255,255,255,.03)", color: "var(--muted)",
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
                  border: `1px solid ${has ? "rgba(43,127,214,.4)" : "var(--border)"}`,
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
        style={{ background: "rgba(248,113,113,.1)", color: "var(--danger)" }}>{err}</div>}

    </Modal>
  );
}


/* ── کیفیت تانل ── */

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
    try {
      await fetch(`${API_URL}/api/admin/tunnel/${tunnel.id}/monitor`, {
        method: "POST",
        headers: { "X-Admin-Password": password },
      });
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
                    background: "rgba(255,255,255,.06)", overflow: "hidden" }}>
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
                      const col = v > 150 ? "var(--danger)"
                                : v > 60 ? "var(--warn)" : "var(--accent)";
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
                color={s.latest > 150 ? "var(--danger)"
                     : s.latest > 60 ? "var(--warn)" : "var(--ok)"} />

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

  const load = async () => {
    try {
      const d = await fetch(`${API_URL}/api/admin/health/all`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setData(d);
    } catch {
      setData({ ready: false, servers: [] });
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [password]);
  usePolling(load, 60000, [password]);

  const recheck = async () => {
    setBusy(true);
    try {
      for (const s of data?.servers || []) {
        if (s.nodeId) {
          await fetch(`${API_URL}/api/admin/health/check/${s.nodeId}`, {
            method: "POST", headers: { "X-Admin-Password": password } });
        }
      }
      await new Promise((r) => setTimeout(r, 3000));
      await load();
    } finally { setBusy(false); }
  };

  if (loading) return <PageSkeleton />;

  const servers = data?.servers || [];
  const worst = HEALTH_COLOR[data?.level] || "var(--muted)";

  return (
    <div className="fx-anim">
      <SectionHead title="سلامت سرورها"
        desc="هر ۵ دقیقه خودکار بررسی می‌شود و اگر مشکلی پیدا شود، در تلگرام خبر می‌دهد."
        action={
          <button onClick={recheck} disabled={busy}
            className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
            {busy ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
            بررسی دوباره
          </button>
        } />

      <div className="fx-card p-5 mb-4" style={{
        borderColor: data?.level === "crit" ? "rgba(248,113,113,.4)"
                   : data?.level === "warn" ? "rgba(251,191,36,.35)" : undefined }}>
        <div className="flex items-center gap-3">
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: worst,
                        boxShadow: `0 0 10px ${worst}`, flexShrink: 0 }} />
          <div className="min-w-0">
            <div className="text-[16px] font-bold" style={{ color: worst }}>
              {HEALTH_LABEL[data?.level] || "نامشخص"}
            </div>
            <div className="text-[13px] mt-0.5" style={{ color: "var(--muted)" }}>
              {faNum(servers.length)} سرور · آخرین بررسی {data?.at?.slice(11, 16) || "—"}
            </div>
          </div>
        </div>
      </div>

      {servers.map((s, i) => {
        const col = HEALTH_COLOR[s.level] || "var(--muted)";
        const problems = (s.checks || []).filter((c) => c.level !== "ok");
        const fine = (s.checks || []).filter((c) => c.level === "ok");
        return (
          <div key={i} className="fx-card p-5 mb-3">
            <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
              <div className="flex items-center gap-2.5 min-w-0">
                <Circle size={8} fill={col} strokeWidth={0} />
                <span className="text-[14px] font-bold text-white">{s.server}</span>
              </div>
              <span className="text-[13px]" style={{ color: col }}>{s.summary}</span>
            </div>

            {problems.map((c, j) => (
              <div key={j} className="p-3.5 rounded-xl mb-2"
                style={{
                  background: c.level === "crit"
                    ? "rgba(248,113,113,.07)" : "rgba(251,191,36,.07)",
                  border: `1px solid ${c.level === "crit"
                    ? "rgba(248,113,113,.2)" : "rgba(251,191,36,.2)"}`,
                }}>
                <div className="flex justify-between items-baseline gap-3 flex-wrap">
                  <span className="text-[14px] font-semibold"
                    style={{ color: HEALTH_COLOR[c.level] }}>{c.title}</span>
                  <span className="text-[13px]" style={{ color: "var(--dim)" }}>
                    {errText(c.detail)}
                  </span>
                </div>
                {c.hint && (
                  <div className="text-[13px] mt-2 leading-relaxed"
                    style={{ color: "var(--muted)" }}>{c.hint}</div>
                )}
              </div>
            ))}

            {fine.length > 0 && (
              <div className="flex gap-1.5 flex-wrap mt-3">
                {fine.map((c, j) => (
                  <span key={j} className="text-[12px] px-2 py-1 rounded-lg"
                    style={{ background: "var(--surface-3)", color: "var(--muted)" }}
                    title={errText(c.detail)}>
                    ✓ {c.title}
                  </span>
                ))}
              </div>
            )}

            {(s.checks || []).length === 0 && (
              <div className="text-[13px]" style={{ color: "var(--muted)" }}>
                {s.summary || "گزارشی نرسیده"}
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
export function TunnelEvents({ password }) {
  const { data, loading } = useTunnel(password);

  if (loading) return <PageSkeleton />;

  const events = data?.events || [];
  const color = { error: "var(--danger)", warn: "var(--warn)", info: "var(--muted)" };

  return (
    <div className="fx-anim">
      <SectionHead title="رویدادها" desc="آنچه روی سرورها اتفاق افتاده." />

      {events.length === 0 ? (
        <EmptyState icon={Clock} text="هنوز رویدادی ثبت نشده" />
      ) : (
        <div className="fx-card overflow-hidden" style={{ padding: 0 }}>
          {events.map((e, i) => (
            <div key={e.id} className="flex items-start gap-3 p-4"
              style={{ borderBottom: i < events.length - 1 ? "1px solid var(--border)" : "none" }}>
              <Circle size={7} fill={color[e.level] || "var(--muted)"} strokeWidth={0}
                style={{ marginTop: 5, flexShrink: 0 }} />
              <div className="min-w-0 flex-1">
                <div className="text-[13px]" style={{ color: "var(--dim)" }}>{e.message}</div>
                <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>
                  {e.node_name && `${e.node_name} · `}
                  {e.created_at?.replace("T", " ").slice(0, 16)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


/* ── صورتحساب دوره ── */
