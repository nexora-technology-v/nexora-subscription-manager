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
  Activity, Loader2, RefreshCw, Server, ShieldCheck,
} from "lucide-react";
import { API_URL } from "../lib/constants";
import { faNum } from "../lib/format";
import { EmptyState, InfoBox, Msg, SectionHead } from "../ui/index";
import { MetricCard, PortsCard, ConnectionsCard } from "./monitoring";

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
        setMsg({ t: "err", m: j.detail || "درخواست ناموفق" });
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

      {!snap || !snap.ready ? (
        <EmptyState icon={Activity}
          text={(snap && snap.note)
            || "هنوز گزارشی از این سرور نرسیده — دکمه‌ی «گزارش تازه» را بزنید"} />
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
