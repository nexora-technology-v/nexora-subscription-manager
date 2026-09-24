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
  AlertTriangle, Download, Lock, RefreshCw, ShieldAlert, ShieldCheck, Users,
} from "lucide-react";
import { API_URL } from "../lib/constants";
import { errText, esc0, faNum } from "../lib/format";
import { ConfirmModal, EmptyState, InfoBox, Msg, PageSkeleton, SectionHead, StatTile, usePager } from "../ui/index";
import { isoToJalaliStamp } from "../ui/jalali";

/* «چه کار کنم» گاهی دستور است و گاهی جمله‌ی فارسی. همه در جعبه‌ی کدِ
   چپ‌به‌راست می‌نشستند و جمله‌ی فارسی وارونه خوانده می‌شد («... نبندید
   /etc/ssh/sshd_config در»). جمله متن می‌ماند و فقط دستور کد می‌شود. */
const FA = /[\u0600-\u06FF]/;
function FixText({ text }) {
  const t = String(text || "");
  const i = t.lastIndexOf(": ");
  const cmd = !FA.test(t) ? t : (i > 0 && !FA.test(t.slice(i + 2)) ? t.slice(i + 2) : "");
  const prose = cmd === t ? "" : (cmd ? t.slice(0, i + 1) : t);
  return (
    <div className="mt-2">
      {prose && <div className="text-[12.5px] leading-relaxed" style={{ color: "var(--dim)" }}>{prose}</div>}
      {cmd && (
        <div className="rounded-lg p-2.5 mt-1.5" style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
          <code dir="ltr" className="text-[12px] block text-left" style={{
            fontFamily: "var(--mono)", color: "var(--accent-2)", whiteSpace: "pre-wrap", wordBreak: "break-all",
          }}>{cmd}</code>
        </div>
      )}
    </div>
  );
}

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
      const r = await fetch(
        `${API_URL}/api/admin/firewall/intrusion?hours=${hours}`,
        { headers: { "X-Admin-Password": password } },
      );
      const j = await r.json().catch(() => ({}));
      // پاسخِ خطا پیش‌تر به‌جای داده می‌نشست و صفحه «لاگ خوانده نشد»
      // می‌گفت — دلیلِ واقعی (رمز، ماژول) دیده نمی‌شد
      if (!r.ok) { setMsg({ t: "err", m: errText(j.detail, "خواندنِ تلاش‌ها ناموفق بود") }); setD((x) => x || {}); return; }
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

  // این محاسبه‌ها *قبل* از هر return شرطی می‌آیند، چون usePager هوک
  // است. اگر بعد از «if (!d) return» می‌نشست، رندر اولِ خالی هوک را
  // اجرا نمی‌کرد و رندر بعدی می‌کرد — و React با خطای #310 کل صفحه
  // را سیاه می‌کرد. قاعده‌ی هوک‌ها: همیشه همه، همیشه به یک ترتیب.
  const ssh = (d && d.ssh) || {};
  const list = ssh.attempts || [];
  const attackers = list.filter((a) => a.severity !== "noise" && !a.known);
  const customers = list.filter((a) => a.known);
  const noise = list.filter((a) => a.severity === "noise" && !a.known);
  const heavy = attackers.filter((a) => a.severity === "heavy");

  const shown = show === "attackers" ? attackers
    : show === "customers" ? customers
      : show === "noise" ? noise : list;

  // جدول تلاش‌های نفوذ روی سرور واقعی صدها ردیف دارد. قبلاً تا صد
  // ردیف یک‌جا چاپ می‌شد — یعنی صفحه‌ای که باید تا ته اسکرول شود، و
  // بقیه‌ی ردیف‌ها اصلاً دیده نمی‌شدند.
  const { shown: pageRows, pager } = usePager(shown, 15);

  if (!d) {
    return (
      <PageSkeleton />
    );
  }

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

  // «از قبل بسته» فقط میانِ مهاجم‌ها معنا دارد — مشتری و نویز را
  // نمی‌بندیم. پیش‌تر از a.tries و a.blocked خوانده می‌شد که بکند هرگز
  // نمی‌فرستاد (از داده‌ی ساختگیِ هارنس آمده بودند)، پس «جدی» و «از قبل
  // بسته» روی سرورِ واقعی همیشه صفر بودند.
  const blockedAtk = attackers.filter((a) => a.blocked);

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
              className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
              <RefreshCw size={14} className={busy ? "animate-spin" : ""} />
              تازه‌سازی
            </button>
          </div>
        )} />

      <Msg msg={msg} />

      {/* یک ردیفِ شاخص، نه دو: ردیفِ بالا «۶ مهاجم، ۰ جدی» می‌گفت و ردیفِ
          پایین «۲ مهاجم، جدی» — هر دو درباره‌ی یک داده. حالا یک تعریف:
          مهاجم = پیگیر و ناآشنا، همان که جدولِ زیر نشان می‌دهد. */}
      {ssh.available && (
        <div className="fx-g4 grid grid-cols-4 gap-3">
          <StatTile label="تلاشِ ناموفق" icon={AlertTriangle}
            tone={(ssh.total || 0) > 500 ? "var(--danger)" : (ssh.total || 0) > 50 ? "var(--warn)" : "var(--ok)"}
            value={faNum(ssh.total || 0)}
            hint={`از ${faNum(list.length)} آدرس در ${faNum(ssh.hours || hours)} ساعت`} />
          <StatTile label="مهاجم" icon={ShieldAlert}
            tone={attackers.length ? "var(--danger)" : "var(--ok)"}
            color={attackers.length ? "var(--danger)" : "var(--ok)"}
            value={faNum(attackers.length)}
            hint={heavy.length ? `${faNum(heavy.length)} حمله‌ی سنگین` : attackers.length ? "پیگیر و ناآشنا" : "هیچ‌کدام پیگیر نبوده‌اند"} />
          <StatTile label="احتمالاً مشتری" icon={Users}
            tone={customers.length ? "var(--warn)" : "var(--accent-2)"}
            value={faNum(customers.length)}
            hint={customers.length ? "بستنشان سرویس را قطع می‌کند" : "هیچ مشتری‌ای میانشان نیست"} />
          <StatTile label="مهاجمِ بسته‌شده" icon={Lock} tone="var(--accent-2)"
            value={`${faNum(blockedAtk.length)}/${faNum(attackers.length)}`}
            hint={d.blockedError ? d.blockedError
              : attackers.length - blockedAtk.length > 0
                ? `${faNum(attackers.length - blockedAtk.length)} مهاجم هنوز باز است` : "همه بسته شده‌اند"} />
        </div>
      )}

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
          {(d.advice || []).map((a, idx) => (
            <InfoBox key={idx} tone={a.level === "crit" ? "danger" : "warn"}>
              {a.title && <b>{a.title}: </b>}{a.text}
              {a.fix && <FixText text={a.fix} />}
              {a.danger && (
                <div className="mt-2 text-[12px] flex items-start gap-1.5" style={{ color: "var(--danger)" }}>
                  <AlertTriangle size={13} className="shrink-0 mt-0.5" /> {a.danger}
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
                  <span style={{ color: "var(--muted)" }}>{a.user} · {isoToJalaliStamp(a.at)}</span>
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
                    {pageRows.map((a) => (
                      <tr key={a.ip}>
                        <td dir="ltr" style={{ fontFamily: "var(--mono)" }}>
                          {a.ip}
                          {a.known && (
                            <span className="fx-pill fx-fa-sub mr-2" style={{
                              background: "var(--warn-soft)",
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
                          {isoToJalaliStamp(a.last)}
                        </td>
                        <td>
                          {a.blocked ? (
                            <span className="fx-pill" style={{ background: "var(--ok-soft)", color: "var(--ok)" }}>
                              <Lock size={11} /> بسته
                            </span>
                          ) : (
                            <button onClick={() => setConfirmBlock(a)}
                              className="fx-btn-g px-2.5 py-1 text-[12px]"
                              style={{ color: "var(--danger)" }}>
                              بستن
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {pager}
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
