/**
 * مانیتورینگ سرورهای دیگر — بدون نصب پنل روی آن‌ها.
 *
 * سرور ایران، سرور دوم خارج، هر سروری که agent رویش نصب است: همان
 * صفحه‌ی مانیتورینگی که برای سرور پنل می‌بینید، این‌جا برای آن‌ها هم
 * هست. agent همان ماژول monitor.py پنل را دانلود و اجرا می‌کند، پس
 * اعداد و آستانه‌ها دقیقاً یکی‌اند.
 *
 * نکته‌ی رفتاری: درخواست در صف می‌نشیند و agent در چک‌این بعدی‌اش
 * برش می‌دارد. پس بعد از زدن دکمه چند ثانیه طول می‌کشد؛ صفحه
 * خودش چند بار سر می‌زند تا نتیجه برسد و این را صریح می‌گوید.
 */
import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Activity, AlertTriangle, CheckCircle2, Loader2, RefreshCw, Search, Server, ShieldCheck, Stethoscope,
} from "lucide-react";
import { API_URL } from "../lib/constants";
import { errText, faNum } from "../lib/format";
import { EmptyState, InfoBox, Msg, SectionHead } from "../ui/index";
import { MetricCard, PortsCard, ConnectionsCard } from "./monitoring";

/**
 * چرا از این سرور گزارشی نمی‌آید.
 *
 * چرا وجود دارد:
 *     دو بار برای همین مشکل حدس زدم و هر دو بار اشتباه بود، چون
 *     هیچ‌جا دیده نمی‌شد کار کجا می‌ایستد. صف کار چهار مرحله دارد و
 *     هر کدام می‌تواند جای گیرکردن باشد — بدون دیدنشان، رفع مشکل
 *     یعنی تیر در تاریکی.
 */
function NodeDiagnose({ nodeId, password, onFix }) {
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);

  const run = useCallback(async () => {
    if (!nodeId) return;
    setBusy(true);
    try {
      const j = await fetch(
        `${API_URL}/api/admin/tunnel/node/${nodeId}/diagnose`,
        { headers: { "X-Admin-Password": password } },
      ).then((r) => r.json());
      setD(j);
    } catch { setD({ steps: [], error: "اتصال برقرار نشد" }); }
    finally { setBusy(false); }
  }, [nodeId, password]);

  useEffect(() => { if (open) run(); }, [open, run]);

  return (
    <div className="fx-card p-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="text-[14px] font-semibold text-white flex items-center gap-2">
          <Stethoscope size={15} style={{ color: "var(--accent-2)" }} />
          چرا گزارشی نمی‌آید؟
        </div>
        <button title="جستجو" onClick={() => setOpen(!open)} disabled={busy || !nodeId}
          className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
          {busy ? <Loader2 size={13} className="animate-spin" />
            : <Search size={13} />}
          {open ? "بستن" : "بررسی کن"}
        </button>
      </div>
      <p className="text-[13px] mt-1" style={{ color: "var(--muted)" }}>
        هر چهار مرحله‌ی مسیر را نشان می‌دهد و می‌گوید کجا ایستاده.
      </p>

      {open && d && (
        <div className="mt-3">
          {d.error && <InfoBox tone="warn">{d.error}</InfoBox>}

          {(d.steps || []).map((s, i) => (
            <div key={i} className="flex items-start gap-3 p-3 rounded-xl mb-2"
              style={{
                background: s.ok ? "rgba(52,211,153,.06)" : "rgba(251,191,36,.06)",
                border: `1px solid ${s.ok ? "rgba(52,211,153,.22)"
                  : "rgba(251,191,36,.28)"}`,
              }}>
              {s.ok
                ? <CheckCircle2 size={16} className="shrink-0 mt-0.5"
                    style={{ color: "var(--ok)" }} />
                : <AlertTriangle size={16} className="shrink-0 mt-0.5"
                    style={{ color: "var(--warn)" }} />}
              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-semibold"
                  style={{ color: s.ok ? "var(--ok)" : "var(--warn)" }}>
                  {s.step}
                </div>
                <div className="text-[12px] mt-1 leading-relaxed"
                  style={{ color: "var(--dim)", wordBreak: "break-word" }}>
                  {s.note}
                </div>
                {s.fix && (
                  <div className="text-[12px] mt-1.5" style={{ color: "var(--accent-2)" }}>
                    راه‌حل: {s.fix}
                  </div>
                )}
              </div>
            </div>
          ))}

          {d.healthy && (
            <InfoBox tone="ok">
              هر چهار مرحله سالم است — گزارش باید بیاید.
            </InfoBox>
          )}

          {(d.jobs || []).length > 0 && (
            <details className="mt-3">
              <summary className="text-[13px] cursor-pointer"
                style={{ color: "var(--muted)" }}>
                آخرین کارها ({faNum(d.jobs.length)})
              </summary>
              <div className="mt-2" style={{ overflowX: "auto" }}>
                <table className="fx-table" style={{ minWidth: 520 }}>
                  <thead>
                    <tr>
                      <th>#</th><th>دستور</th><th>وضعیت</th>
                      <th>ثبت</th><th>نتیجه</th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.jobs.map((j) => (
                      <tr key={j.id}>
                        <td style={{ fontFamily: "var(--mono)" }}>{j.id}</td>
                        <td dir="ltr">{j.action}</td>
                        <td style={{
                          color: j.status === "done" ? "var(--ok)"
                            : j.status === "failed" ? "var(--danger)"
                              : "var(--warn)",
                        }}>{j.status}</td>
                        <td className="text-[12px]" dir="ltr">
                          {String(j.created_at || "").slice(5, 16)}
                        </td>
                        <td className="text-[12px]" style={{
                          maxWidth: 240, overflow: "hidden",
                          textOverflow: "ellipsis", whiteSpace: "nowrap",
                          color: "var(--muted)",
                        }} title={j.result || ""}>{j.result || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          )}

          <div className="flex gap-2 mt-3 flex-wrap">
            <button onClick={run} disabled={busy}
              className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
              <RefreshCw size={13} className={busy ? "animate-spin" : ""} />
              دوباره بررسی کن
            </button>
            {onFix && !d.healthy && (
              <button onClick={onFix} disabled={busy}
                className="fx-btn px-3 py-2 text-[13px]">
                به‌روزرسانی ایجنت
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}


export function NodesMonitor({ password }) {
  const [nodes, setNodes] = useState(null);
  const [sel, setSel] = useState(null);
  const [snap, setSnap] = useState(null);
  const [busy, setBusy] = useState(false);
  const [waiting, setWaiting] = useState(false);
  const [msg, setMsg] = useState(null);
  const timer = useRef(null);

  useEffect(() => {
    fetch(`${API_URL}/api/admin/tunnel/overview`, {
      headers: { "X-Admin-Password": password },
    }).then((r) => r.json())
      .then((j) => {
        const list = j.nodes || [];
        setNodes(Array.isArray(list) ? list : []);
        if (Array.isArray(list) && list.length) setSel(list[0].id);
      })
      .catch(() => setNodes([]));
  }, [password]);

  const read = useCallback(async (nodeId) => {
    if (!nodeId) return null;
    try {
      const j = await fetch(
        `${API_URL}/api/admin/tunnel/node/${nodeId}/sysmon`,
        { headers: { "X-Admin-Password": password } },
      ).then((r) => r.json());
      setSnap(j);
      return j;
    } catch {
      setSnap({ ready: false, note: "اتصال برقرار نشد" });
      return null;
    }
  }, [password]);

  useEffect(() => {
    setSnap(null);
    if (sel) read(sel);
    return () => { if (timer.current) clearTimeout(timer.current); };
  }, [sel, read]);

  /**
   * درخواست گزارش تازه و انتظار برای رسیدنش.
   *
   * زمان رسیدن به بازه‌ی چک‌این agent بستگی دارد، پس تا ۳۰ ثانیه
   * هر ۳ ثانیه سر می‌زنیم و بعد دست می‌کشیم — حلقه‌ی بی‌پایان
   * فقط سرور را بی‌دلیل مشغول می‌کند.
   */
  const request = async (kind = "sysmon") => {
    if (!sel) return;
    setBusy(true);
    setWaiting(true);
    const before = snap && snap.at;
    try {
      const res = await fetch(
        `${API_URL}/api/admin/tunnel/node/${sel}/sysmon?kind=${kind}`,
        { method: "POST", headers: { "X-Admin-Password": password } },
      );
      const j = await res.json().catch(() => ({}));
      if (!res.ok) {
        setMsg({ t: "err", m: errText(j.detail, "درخواست ناموفق") });
        setWaiting(false);
        return;
      }
      setMsg({ t: "ok", m: j.note || "درخواست ثبت شد" });

      let tries = 0;
      const poll = async () => {
        tries += 1;
        const got = await read(sel);
        if (got && got.ready && got.at !== before) {
          setWaiting(false);
          return;
        }
        if (tries >= 10) {
          setWaiting(false);
          setMsg({
            t: "err",
            m: "سرور هنوز جواب نداده — ممکن است agent خاموش باشد یا "
               + "بازه‌ی چک‌این آن طولانی باشد",
          });
          return;
        }
        timer.current = setTimeout(poll, 3000);
      };
      timer.current = setTimeout(poll, 3000);
    } catch {
      setMsg({ t: "err", m: "اتصال برقرار نشد" });
      setWaiting(false);
    } finally { setBusy(false); }
  };

  /** ایجنت قدیمی را از همین‌جا به‌روز می‌کند — بدون SSH زدن. */
  const updateAgent = async () => {
    if (!sel) return;
    setBusy(true);
    try {
      const res = await fetch(
        `${API_URL}/api/admin/tunnel/node/${sel}/update-agent`,
        { method: "POST", headers: { "X-Admin-Password": password } },
      );
      const j = await res.json().catch(() => ({}));
      setMsg(res.ok ? { t: "ok", m: j.note || "در صف قرار گرفت" }
        : { t: "err", m: errText(j.detail, "ناموفق") });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(false); }
  };

  useEffect(() => {
    if (msg) {
      const t = setTimeout(() => setMsg(null), 6000);
      return () => clearTimeout(t);
    }
  }, [msg]);

  if (nodes === null) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} />
      </div>
    );
  }

  if (!nodes.length) {
    return (
      <div className="fx-anim">
        <SectionHead title="مانیتورینگ سرورهای دیگر"
          desc="سرور ایران و هر سرور دیگری که agent رویش نصب است." />
        <InfoBox tone="warn">
          هنوز سروری اضافه نشده. از صفحه‌ی <b>تانل ← سرورها</b> یک سرور
          بسازید و دستور نصب agent را روی آن اجرا کنید. بعد از آن، همین
          صفحه وضعیت کاملش را نشان می‌دهد — بدون اینکه لازم باشد پنل را
          روی آن سرور هم نصب کنید.
        </InfoBox>
      </div>
    );
  }

  const d = (snap && snap.ready && snap.kind === "sysmon" && snap.data) || null;
  const fw = (snap && snap.ready && snap.kind === "firewall" && snap.data) || null;
  // snapshot بخش‌ها را زیر sections می‌گذارد و سنجه‌ها را جدا
  const sec = (d && d.sections) || {};
  const node = nodes.find((n) => n.id === sel);

  return (
    <div className="fx-anim">
      <SectionHead title="مانیتورینگ سرورهای دیگر"
        desc="همان اعداد و همان آستانه‌های سرور پنل — چون agent همان ماژول را اجرا می‌کند."
        action={(
          <div className="flex items-center gap-2 flex-wrap">
            <select className="fx-input" value={sel || ""} style={{ width: 180 }}
              onChange={(e) => setSel(Number(e.target.value))}>
              {nodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.name}{n.role ? ` — ${n.role}` : ""}
                </option>
              ))}
            </select>
            <button onClick={() => request("sysmon")} disabled={busy || waiting}
              className="fx-btn px-3 py-2 text-[13px] flex items-center gap-1.5">
              <RefreshCw size={14}
                className={busy || waiting ? "animate-spin" : ""} />
              گزارش تازه
            </button>
            <button onClick={() => request("firewall")} disabled={busy || waiting}
              className="fx-btn-ghost px-3 py-2 text-[13px] flex items-center gap-1.5">
              <ShieldCheck size={14} /> فایروال
            </button>
          </div>
        )} />

      <Msg msg={msg} />

      {waiting && (
        <InfoBox>
          درخواست فرستاده شد. agent در چک‌این بعدی‌اش آن را برمی‌دارد —
          معمولاً کمتر از نیم دقیقه. صفحه خودش به‌روز می‌شود.
        </InfoBox>
      )}

      {node && (
        <div className="fx-card p-4 mb-4 flex items-center gap-4 flex-wrap">
          <Server size={18} style={{ color: "var(--accent-2)" }} />
          <div>
            <div className="text-[14px] font-semibold text-white">{node.name}</div>
            <div className="text-[12px]" style={{ color: "var(--muted)" }}>
              {node.host || "—"}{node.role ? ` · ${node.role}` : ""}
            </div>
          </div>
          {snap && snap.at && (
            <div className="text-[12px]" style={{ color: "var(--muted)" }}>
              آخرین گزارش: {snap.at}
            </div>
          )}
        </div>
      )}

      {snap && snap.staleAgent && (
        <InfoBox tone="warn">
          <b>ایجنت این سرور قدیمی است</b> (نسخه‌ی {snap.staleAgent}). دستور
          مانیتورینگ از نسخه‌ی ۱.۴.۰ اضافه شده، پس تا به‌روز نشود گزارشی
          نمی‌آید — حتی اگر سرور بدون مشکل وصل باشد.
          <div className="mt-2">
            <button onClick={updateAgent} disabled={busy}
              className="fx-btn px-3 py-2 text-[13px] flex items-center gap-1.5">
              <RefreshCw size={13} className={busy ? "animate-spin" : ""} />
              به‌روزرسانی ایجنت
            </button>
          </div>
        </InfoBox>
      )}

      {snap && snap.lastError && !snap.staleAgent && (
        <InfoBox tone="warn">
          <b>آخرین تلاش ناموفق بود:</b>
          <div dir="ltr" className="mt-1 text-[12px]"
            style={{ fontFamily: "var(--mono)" }}>{snap.lastError}</div>
        </InfoBox>
      )}

      {!snap || !snap.ready ? (
        <>
          <EmptyState icon={Activity}
            text={(snap && snap.note)
              || "هنوز گزارشی از این سرور نرسیده — دکمه‌ی «گزارش تازه» را بزنید"} />
          {/* وقتی گزارش نمی‌آید، اولین سؤال «چرا» است — نه اینکه
              دوباره همان دکمه را بزنیم. */}
          <NodeDiagnose nodeId={sel} password={password} onFix={updateAgent} />
        </>
      ) : d ? (
        <>
          {(d.metrics || []).length > 0 && (
            <div className="fx-g4 grid grid-cols-4 gap-3 mb-4">
              {(d.metrics || []).map((m) => (
                <MetricCard key={m.key} m={m} />
              ))}
            </div>
          )}
          {sec.ports && <PortsCard ports={sec.ports} />}
          {sec.connections && <ConnectionsCard conn={sec.connections} />}
        </>
      ) : fw ? (
        <div className="fx-card p-5">
          <div className="text-[14px] font-semibold text-white mb-3">
            فایروال این سرور
          </div>
          {!fw.installed ? (
            <InfoBox tone="warn">
              ufw روی این سرور نصب نیست.
            </InfoBox>
          ) : (
            <>
              <div className="mb-3 text-[13px]">
                وضعیت:{" "}
                <span style={{ color: fw.active ? "var(--ok)" : "var(--danger)" }}>
                  {fw.active ? "روشن" : "خاموش"}
                </span>
                <span style={{ color: "var(--muted)" }}>
                  {" "}· {faNum((fw.rules || []).length)} قاعده
                </span>
              </div>
              <div style={{ overflowX: "auto" }}>
                <table className="fx-table">
                  <thead>
                    <tr><th>#</th><th>مقصد</th><th>عمل</th><th>مبدأ</th></tr>
                  </thead>
                  <tbody>
                    {(fw.rules || []).slice(0, 60).map((r) => (
                      <tr key={r.num}>
                        <td style={{
                          fontFamily: "var(--mono)", color: "var(--muted)",
                        }}>{faNum(r.num)}</td>
                        <td dir="ltr" style={{ fontFamily: "var(--mono)" }}>
                          {r.target}
                        </td>
                        <td>{r.action}</td>
                        <td dir="ltr" style={{ color: "var(--muted)" }}>
                          {r.source}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      ) : (
        <EmptyState icon={Activity} text="گزارش قابل خواندن نبود" />
      )}
    </div>
  );
}
