/**
 * چه کسی دارد به سرور در می‌زند — و کدامشان مشتری خودتان است.
 *
 * مهم‌ترین تصمیم این صفحه یک چیز است: مدیر نباید تصادفی آی‌پی مشتری
 * خودش را ببندد. یک مشتری که رمز SSH را اشتباه می‌زند، در لاگ دقیقاً
 * شبیه مهاجم است؛ تنها تفاوتش این است که همین حالا به سرویس وصل است.
 * پس آن‌ها جدا، با رنگ متفاوت و هشدار صریح نشان داده می‌شوند و در
 * مسدودسازی دسته‌ای هم پیش‌فرض کنار گذاشته می‌شوند.
 */
import React, { useState, useEffect, useCallback } from "react";
import {
  AlertTriangle, Download, Loader2, RefreshCw, ShieldCheck,
} from "lucide-react";
import { API_URL } from "../lib/constants";
import { errText, esc0, faNum } from "../lib/format";
import {
  ConfirmModal, EmptyState, InfoBox, Msg, SectionHead,
} from "../ui/index";
import { MetricCard } from "./monitoring";

export function FirewallIntrusion({ password }) {
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [hours, setHours] = useState(24);
  const [show, setShow] = useState("attackers");
  const [confirmBlock, setConfirmBlock] = useState(null);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const j = await fetch(
        `${API_URL}/api/admin/firewall/intrusion?hours=${hours}`,
        { headers: { "X-Admin-Password": password } },
      ).then((r) => r.json());
      setD(j);
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(false); }
  }, [password, hours]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (msg) {
      const t = setTimeout(() => setMsg(null), 5000);
    
  /**
   * فهرست آدرس‌های مهاجم را به فایل می‌دهد.
   *
   * قالبش همان است که بخش «بستن دسته‌ای» می‌خواند، پس بدون هیچ
   * ویرایشی مستقیم وارد می‌شود.
   *
   * onlyUnknown: تانل‌ها و آدرس‌هایی که مشتری‌های خودتان با آن‌ها
   * وصل می‌شوند کنار گذاشته می‌شوند — بستن آن‌ها یعنی قطع‌کردن
   * مشتری خودتان.
   */
  const exportIps = (onlyUnknown) => {
    const rows = (d.ssh?.attempts || []).filter(
      (a) => (onlyUnknown ? !a.known : true) && a.ip);
    if (!rows.length) {
      setMsg({ t: "err", m: "آدرسی برای خروجی نیست" });
      return;
    }
    const lines = [
      "# آدرس‌های مهاجم — از صفحه‌ی تلاش برای نفوذ",
      `# ${new Date().toISOString().slice(0, 16).replace("T", " ")}`,
      `# ${rows.length} آدرس`
        + (onlyUnknown ? " (تانل‌ها و مشتری‌ها کنار گذاشته شدند)" : ""),
      "",
      ...rows.map((a) => a.ip),
    ];
    const blob = new Blob([lines.join("\n") + "\n"], { type: "text/plain" });
    const el = document.createElement("a");
    el.href = URL.createObjectURL(blob);
    el.download = onlyUnknown
      ? "nexora-attackers-unknown.txt" : "nexora-attackers.txt";
    el.click();
    URL.revokeObjectURL(el.href);
    setMsg({ t: "ok", m: `${rows.length} آدرس در فایل ذخیره شد` });
  };

  return () => clearTimeout(t);
    }
  }, [msg]);

  if (!d) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} />
      </div>
    );
  }

  const ssh = d.ssh || {};
  const list = ssh.attempts || [];
  const attackers = list.filter((a) => a.severity !== "noise" && !a.known);
  const customers = list.filter((a) => a.known);
  const noise = list.filter((a) => a.severity === "noise" && !a.known);
  const heavy = attackers.filter((a) => a.severity === "heavy");

  const shown = show === "attackers" ? attackers
    : show === "customers" ? customers
      : show === "noise" ? noise : list;

  const post = async (body, okMsg) => {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/firewall/block-attackers`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Password": password,
        },
        body: JSON.stringify(body),
      });
      const j = await res.json().catch(() => ({}));
      setMsg(res.ok ? { t: "ok", m: j.note || okMsg }
        : { t: "err", m: errText(j.detail, "ناموفق") });
      if (res.ok) await load();
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(false); setConfirmBlock(null); }
  };

  // مسدودسازی دسته‌ای عمداً includeConnected نمی‌فرستد: سرور خودش
  // آی‌پی‌های متصل را کنار می‌گذارد حتی اگر این‌جا اشتباهی بیایند.
  const blockHeavy = () => post(
    { ips: heavy.map((a) => a.ip), confirm: true },
    "آی‌پی‌های مهاجم بسته شدند",
  );

  // تک‌تک، با تصمیم صریح مدیر — این‌جا includeConnected می‌رود چون
  // مدیر روی همان سطر و با دیدن برچسب «وصل به سرویس» تایید کرده.
  const blockOne = (ip) => post(
    { ips: [ip], confirm: true, includeConnected: true }, "بسته شد",
  );

  const TABS = [
    ["attackers", "مهاجم", attackers.length, "var(--danger)"],
    ["customers", "احتمالاً مشتری", customers.length, "var(--warn)"],
    ["noise", "نویز", noise.length, "var(--muted)"],
  ];

  return (
    <div className="fx-anim">
      <SectionHead title="تلاش برای نفوذ"
        desc="هر سرور روی اینترنت شبانه‌روز اسکن می‌شود. مهم این است که بدانید کدام جدی است و کدام مشتری خودتان."
        action={(
          <div className="flex items-center gap-2">
            <select className="fx-input" value={hours} style={{ width: 130 }}
              onChange={(e) => setHours(Number(e.target.value))}>
              <option value={6}>۶ ساعت اخیر</option>
              <option value={24}>۲۴ ساعت اخیر</option>
              <option value={72}>۳ روز اخیر</option>
              <option value={168}>۷ روز اخیر</option>
            </select>
            <button onClick={load} disabled={busy}
              className="fx-btn-ghost px-3 py-2 text-[13px] flex items-center gap-1.5">
              <RefreshCw size={14} className={busy ? "animate-spin" : ""} />
              تازه‌سازی
            </button>
          </div>
        )} />

      <Msg msg={msg} />

      {(ssh.attempts || []).length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <button onClick={() => exportIps(false)}
            className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
            <Download size={13} /> خروجی همه‌ی مهاجم‌ها
          </button>
          <button onClick={() => exportIps(true)}
            className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
            <Download size={13} /> فقط ناشناس‌ها
          </button>
          <span className="text-[12px]" style={{ color: "var(--muted)" }}>
            فایل را در «آی‌پی‌های بسته‌شده» وارد کنید
          </span>
        </div>
      )}

      {d.vpnNote && (
        <InfoBox>
          <b>درباره‌ی آدرس واقعی:</b> {d.vpnNote}
          <div className="mt-2 text-[12px]" style={{ color: "var(--muted)" }}>
            ستون «صاحب آدرس» می‌گوید آدرس از یک دیتاسنتر آمده یا از یک
            اپراتور خانگی. دیتاسنتر یعنی سرور یا خروجی VPN — بستنش
            کم‌خطر است. اپراتور خانگی یعنی به‌احتمال زیاد یک آدم واقعی.
          </div>
        </InfoBox>
      )}

      {!ssh.available ? (
        <div className="fx-card p-5">
          <div className="text-[14px] font-semibold text-white mb-2 flex items-center gap-2">
            <AlertTriangle size={15} style={{ color: "var(--warn)" }} />
            لاگ SSH خوانده نشد
          </div>
          <p className="text-[13px] leading-relaxed" style={{ color: "var(--dim)" }}>
            {ssh.note || "دسترسی به لاگ احراز هویت وجود ندارد."}
            {" "}پنل باید با دسترسی کافی اجرا شود تا بتواند
            {" "}<code dir="ltr" style={{ fontFamily: "var(--mono)" }}>
              journalctl -u ssh
            </code>{" "}را بخواند.
          </p>
        </div>
      ) : (
        <>
          <div className="fx-g3 grid grid-cols-3 gap-3 mb-4">
            <MetricCard m={{
              key: "total", title: "کل تلاش ناموفق",
              value: faNum(ssh.total || 0),
              unit: `در ${faNum(ssh.hours || 24)} ساعت`,
              level: (ssh.total || 0) > 500 ? "crit"
                : (ssh.total || 0) > 50 ? "warn" : "ok",
              why: "تلاش ناموفق روی هر سرور عمومی عادی است. آنچه مهم است تمرکز آن روی چند آی‌پی مشخص است.",
            }} />
            <MetricCard m={{
              key: "attackers", title: "آی‌پی مهاجم",
              value: faNum(attackers.length), unit: "جدی",
              level: attackers.length ? "warn" : "ok",
              why: "آی‌پی‌هایی که بیش از ۱۰ بار رمز اشتباه زده‌اند و به سرویس شما وصل نیستند.",
            }} />
            <MetricCard m={{
              key: "customers", title: "احتمالاً مشتری",
              value: faNum(customers.length), unit: "به سرویس وصل‌اند",
              level: customers.length ? "warn" : "ok",
              why: "این آی‌پی‌ها هم تلاش ناموفق داشته‌اند و هم همین حالا به سرویس وصل‌اند — پس به‌احتمال زیاد مشتری خودتان‌اند.",
            }} />
          </div>

          {(d.advice || []).map((a, idx) => (
            <InfoBox key={idx} tone={a.level === "crit" ? "danger" : "warn"}>
              {a.title && <b>{a.title}: </b>}{a.text}
              {a.fix && (
                <div className="mt-2 rounded-lg p-2.5" style={{
                  background: "var(--surface-3)",
                  border: "1px solid var(--border)",
                }}>
                  <code dir="ltr" className="text-[12px]" style={{
                    fontFamily: "var(--mono)", color: "var(--accent-2)",
                    whiteSpace: "pre-wrap", wordBreak: "break-all",
                  }}>{a.fix}</code>
                </div>
              )}
              {a.danger && (
                <div className="mt-2 text-[12px]" style={{ color: "var(--danger)" }}>
                  ⚠️ {a.danger}
                </div>
              )}
            </InfoBox>
          ))}

          {(ssh.accepted || []).length > 0 && (
            <div className="fx-card p-5 mb-4">
              <div className="text-[14px] font-semibold text-white mb-2">
                ورودهای موفق اخیر
              </div>
              <p className="text-[12px] mb-3" style={{ color: "var(--muted)" }}>
                اگر آی‌پی‌ای این‌جا می‌بینید که خودتان نیستید، دیگر تلاش نیست —
                یعنی کسی وارد شده. فوراً رمز و کلیدها را عوض کنید.
              </p>
              {(ssh.accepted || []).map((a, k) => (
                <div key={k}
                  className="flex items-center justify-between py-2 text-[13px]"
                  style={{ borderBottom: "1px solid var(--border)" }}>
                  <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>{a.ip}</span>
                  <span style={{ color: "var(--muted)" }}>{a.user} · {a.at}</span>
                </div>
              ))}
            </div>
          )}

          <div className="fx-card p-5">
            <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
              <div className="flex items-center gap-2 flex-wrap">
                {TABS.map(([k, label, n, color]) => (
                  <button key={k} onClick={() => setShow(k)}
                    className="fx-pill px-3 py-1.5 text-[13px]"
                    style={{
                      background: show === k ? "var(--accent-soft)" : "var(--surface-3)",
                      border: `1px solid ${show === k ? "var(--accent-2)" : "var(--border)"}`,
                      color: show === k ? "var(--accent-2)" : color,
                    }}>
                    {label} ({faNum(n)})
                  </button>
                ))}
              </div>
              {show === "attackers" && heavy.length > 0 && (
                <button onClick={() => setConfirmBlock("heavy")} disabled={busy}
                  className="fx-btn px-3 py-2 text-[13px] flex items-center gap-1.5"
                  style={{ background: "var(--danger)" }}>
                  <ShieldCheck size={14} /> بستن {faNum(heavy.length)} حمله‌ی سنگین
                </button>
              )}
            </div>

            {show === "customers" && customers.length > 0 && (
              <InfoBox tone="warn">
                این آی‌پی‌ها همین حالا به سرویس شما وصل‌اند. به‌احتمال زیاد
                مشتری خودتان‌اند که رمز SSH را اشتباه می‌زند یا برنامه‌ای روی
                دستگاهش خراب است. <b>بستنشان یعنی از دست دادن مشتری.</b>
              </InfoBox>
            )}

            {!shown.length ? (
              <EmptyState icon={ShieldCheck} text="چیزی در این دسته نیست" />
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table className="fx-table">
                  <thead>
                    <tr>
                      <th>آی‌پی</th><th>صاحب آدرس</th><th>تلاش</th>
                      <th>کاربر هدف</th><th>آخرین بار</th><th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {shown.slice(0, 100).map((a) => (
                      <tr key={a.ip}>
                        <td dir="ltr" style={{ fontFamily: "var(--mono)" }}>
                          {a.ip}
                          {a.known && (
                            <span className="fx-pill mr-2" style={{
                              background: "rgba(251,191,36,.14)",
                              color: "var(--warn)",
                            }}>وصل به سرویس</span>
                          )}
                        </td>
                        <td style={{ fontSize: 12 }}>
                          {a.owner ? (
                            <span title={a.ownerWhy} style={{
                              color: a.ownerKind === "hosting" ? "var(--warn)"
                                : a.ownerKind === "isp" ? "var(--ok)"
                                  : "var(--muted)",
                            }}>{a.owner}</span>
                          ) : (
                            <span style={{ color: "var(--muted)" }}>—</span>
                          )}
                          {a.ownerKind === "hosting" && (
                            <div style={{ color: "var(--muted)", fontSize: 11 }}>
                              دیتاسنتر
                            </div>
                          )}
                          {a.ownerKind === "isp" && (
                            <div style={{ color: "var(--muted)", fontSize: 11 }}>
                              اپراتور خانگی
                            </div>
                          )}
                        </td>
                        <td style={{
                          color: a.severity === "heavy" ? "var(--danger)"
                            : a.severity === "brute" ? "var(--warn)" : "var(--muted)",
                          fontFamily: "var(--mono)",
                        }}>{faNum(a.count)}</td>
                        <td dir="ltr" style={{ color: "var(--muted)" }}>
                          {esc0(a.top_user)}
                        </td>
                        <td style={{ color: "var(--muted)", fontSize: 12 }}>
                          {a.last}
                        </td>
                        <td>
                          <button onClick={() => setConfirmBlock(a)}
                            className="fx-btn-ghost px-2 py-1 text-[12px]"
                            style={{ color: "var(--danger)" }}>
                            بستن
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {confirmBlock && (
        <ConfirmModal
          title={confirmBlock === "heavy" ? "بستن حمله‌های سنگین" : "بستن این آی‌پی"}
          desc={confirmBlock === "heavy"
            ? `${faNum(heavy.length)} آی‌پی که بیش از ۱۰۰ بار رمز اشتباه زده‌اند بسته می‌شوند. آی‌پی‌هایی که به سرویس وصل‌اند خودکار کنار گذاشته می‌شوند.`
            : confirmBlock.known
              ? `${confirmBlock.ip} همین حالا به سرویس شما وصل است — احتمالاً مشتری خودتان. با بستن آن، دسترسی‌اش به سرویس هم قطع می‌شود. مطمئنید؟`
              : `${confirmBlock.ip} با ${faNum(confirmBlock.count)} تلاش ناموفق بسته می‌شود.`}
          confirmLabel="بستن"
          onConfirm={() => (confirmBlock === "heavy"
            ? blockHeavy() : blockOne(confirmBlock.ip))}
          onCancel={() => setConfirmBlock(null)} />
      )}
    </div>
  );
}
