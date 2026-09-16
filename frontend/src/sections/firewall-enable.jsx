/**
 * روشن‌کردن فایروال، بدون ریسک قفل‌شدن.
 *
 * چرا این‌طور ساخته شده:
 *     روشن‌کردن ufw روی سروری که فقط از راه دور در دسترس است، یک
 *     شرط‌بندی است: اگر قاعده‌ای جا افتاده باشد، همان لحظه ارتباطت
 *     قطع می‌شود و راهی برای برگشتن نداری مگر کنسول ارائه‌دهنده.
 *
 *     به همین دلیل بیشتر آدم‌ها فایروال را اصلاً روشن نمی‌کنند و
 *     سرورشان باز می‌ماند — که بدترین حالت ممکن است.
 *
 *     این صفحه شرط‌بندی را حذف می‌کند: اول نشان می‌دهد دقیقاً چه
 *     چیزی قطع خواهد شد، و بعد با یک ساعت‌شمار بازگشت روشن می‌کند.
 *     اگر تایید نکنید — چون قطع شده‌اید — سرور خودش برمی‌گردد.
 */
import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  AlertTriangle, CheckCircle2, Clock, Loader2, Power, ShieldCheck,
} from "lucide-react";
import { API_URL } from "../lib/constants";
import { errText, faNum } from "../lib/format";
import { EmptyState, InfoBox, Msg, PageSkeleton, SectionHead } from "../ui/index";

export function FirewallEnable({ password, onChanged }) {
  const [pre, setPre] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [minutes, setMinutes] = useState(5);
  const [armedUntil, setArmedUntil] = useState(null);
  const [now, setNow] = useState(Date.now());
  const tick = useRef(null);

  const load = useCallback(async () => {
    try {
      const [j, rb] = await Promise.all([
        fetch(`${API_URL}/api/admin/firewall/preflight`, {
          headers: { "X-Admin-Password": password },
        }).then((r) => r.json()),
        // اگر صفحه رفرش شده باشد، ساعت‌شمار ممکن است هنوز فعال باشد.
        // بدون این، کاربر دکمه‌ی تایید را نمی‌بیند و فایروال بی‌دلیل
        // خاموش می‌شود.
        fetch(`${API_URL}/api/admin/firewall/rollback-state`, {
          headers: { "X-Admin-Password": password },
        }).then((r) => r.json()).catch(() => null),
      ]);
      setPre(j);
      if (rb && rb.armed) {
        setArmedUntil((prev) => prev || Date.now() + minutes * 60000);
      }
    } catch { setPre({ ready: false, error: "اتصال برقرار نشد" }); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [password]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (msg) { const t = setTimeout(() => setMsg(null), 8000); return () => clearTimeout(t); }
  }, [msg]);

  // شمارش معکوس فقط وقتی ساعت‌شمار فعال است
  useEffect(() => {
    if (!armedUntil) return undefined;
    tick.current = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(tick.current);
  }, [armedUntil]);

  const left = armedUntil ? Math.max(0, Math.ceil((armedUntil - now) / 1000)) : 0;

  const enable = async (force) => {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/firewall/safe-enable`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Password": password,
        },
        body: JSON.stringify({ confirm: true, rollbackMinutes: minutes, force }),
      });
      const j = await res.json().catch(() => ({}));
      if (res.ok) {
        setMsg({ t: "ok", m: j.note || "روشن شد" });
        setArmedUntil(Date.now() + minutes * 60000);
        onChanged && onChanged();
      } else {
        setMsg({ t: "err", m: errText(j.detail, "روشن نشد") });
      }
      await load();
    } catch {
      // قطع‌شدن ارتباط دقیقاً همان چیزی است که ساعت‌شمار برایش هست
      setMsg({ t: "err", m: "ارتباط قطع شد — اگر ساعت‌شمار گذاشته شده بود، "
                            + "فایروال خودش خاموش می‌شود. صبر کنید." });
      setArmedUntil(Date.now() + minutes * 60000);
    } finally { setBusy(false); }
  };

  const confirm = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/firewall/confirm-enabled`, {
        method: "POST", headers: { "X-Admin-Password": password },
      });
      const j = await res.json().catch(() => ({}));
      setMsg(res.ok ? { t: "ok", m: j.note || "تایید شد" }
        : { t: "err", m: errText(j.detail, "ناموفق") });
      if (res.ok) setArmedUntil(null);
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(false); }
  };

  if (!pre) {
    return (
      <PageSkeleton />
    );
  }

  if (!pre.ready) {
    return <EmptyState icon={ShieldCheck} text={pre.error || "در دسترس نیست"} />;
  }

  const risky = pre.atRisk || [];
  const blockers = pre.blockers || [];

  return (
    <div className="fx-anim">
      <SectionHead title="روشن‌کردن فایروال"
        desc="اول می‌بینید چه چیزی قطع می‌شود، بعد با تور نجات روشن می‌کنید." />

      <Msg msg={msg} />

      {/* ساعت‌شمار بازگشت */}
      {armedUntil && left > 0 && (
        <div className="fx-card p-5" style={{
          border: "1px solid var(--warn)",
          background: "var(--warn-wash)",
        }}>
          <div className="flex items-center gap-2 mb-2"
            style={{ color: "var(--warn)" }}>
            <Clock size={18} />
            <span className="text-[16px] font-semibold">
              {faNum(Math.floor(left / 60))}:{String(left % 60).padStart(2, "0")}
              {" "}تا بازگشت خودکار
            </span>
          </div>
          <p className="text-[13px] leading-relaxed mb-3"
            style={{ color: "var(--dim)" }}>
            فایروال روشن است. اگر همه‌چیز کار می‌کند، همین حالا تایید کنید.
            اگر تایید نکنید، سرور خودش فایروال را خاموش می‌کند و به حالت
            قبل برمی‌گردد — پس اگر ارتباطتان قطع شد، فقط صبر کنید.
          </p>
          <button onClick={confirm} disabled={busy}
            className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-2">
            <CheckCircle2 size={15} /> همه‌چیز کار می‌کند، نگهش دار
          </button>
        </div>
      )}

      {pre.active && !armedUntil && (
        <InfoBox tone="ok">
          فایروال روشن است و قاعده‌هایتان اعمال می‌شوند.
        </InfoBox>
      )}

      {/* چه چیزی قطع می‌شود */}
      {blockers.length > 0 && (
        <div className="fx-card p-5" style={{ border: "1px solid var(--danger)" }}>
          <div className="flex items-center gap-2 mb-2"
            style={{ color: "var(--danger)" }}>
            <AlertTriangle size={16} />
            <span className="text-[14px] font-semibold">
              این‌ها قطع می‌شوند و نباید بشوند
            </span>
          </div>
          {blockers.map((b) => (
            <div key={`${b.port}${b.proto}`} className="py-2"
              style={{ borderBottom: "1px solid var(--border)" }}>
              <div className="flex items-center gap-2 flex-wrap">
                <span style={{ fontFamily: "var(--mono)", fontWeight: 600 }}>
                  {b.port}
                </span>
                <span className="text-[12px]" style={{ color: "var(--muted)" }}>
                  {b.proto}
                </span>
                {b.process && (
                  <span dir="ltr" className="text-[12px]"
                    style={{ color: "var(--dim)" }}>{b.process}</span>
                )}
              </div>
              <div className="text-[12px] mt-1" style={{ color: "var(--danger)" }}>
                {b.why}
              </div>
            </div>
          ))}
          <p className="text-[13px] mt-3 leading-relaxed"
            style={{ color: "var(--dim)" }}>
            اول از صفحه‌ی «قواعد فایروال» برای این پورت‌ها قاعده‌ی
            <b> اجازه </b> بسازید، بعد برگردید. تا آن موقع روشن‌کردن
            مجاز نیست.
          </p>
        </div>
      )}

      {risky.length > blockers.length && (
        <div className="fx-card p-5">
          <div className="text-[14px] font-semibold text-white mb-1">
            بدون قاعده — با روشن‌شدن بسته می‌شوند
          </div>
          <p className="text-[12px] mb-3" style={{ color: "var(--muted)" }}>
            اگر لازمشان ندارید، همین درست است.
          </p>
          {risky.filter((r) => !r.critical).map((b) => (
            <div key={`${b.port}${b.proto}`}
              className="flex items-center gap-2 py-1.5 flex-wrap">
              <span style={{ fontFamily: "var(--mono)" }}>{b.port}</span>
              <span className="text-[12px]" style={{ color: "var(--muted)" }}>
                {b.proto}
              </span>
              {b.process && (
                <span dir="ltr" className="text-[12px]"
                  style={{ color: "var(--dim)" }}>{b.process}</span>
              )}
              {b.why && (
                <span className="text-[12px]" style={{ color: "var(--muted)" }}>
                  — {b.why}
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {(pre.covered || []).length > 0 && (
        <div className="fx-card p-5">
          <div className="flex items-center gap-2 text-[14px] font-semibold mb-2"
            style={{ color: "var(--ok)" }}>
            <ShieldCheck size={15} /> قاعده دارند و باز می‌مانند
            <span className="text-[12px] font-normal"
              style={{ color: "var(--muted)" }}>
              ({faNum(pre.covered.length)})
            </span>
          </div>
          <div className="flex gap-2 flex-wrap">
            {pre.covered.map((b) => (
              <span key={`${b.port}${b.proto}`} className="fx-pill"
                style={{ background: "var(--ok-soft)", color: "var(--ok)" }}>
                {b.port}/{b.proto}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* دکمه‌ی روشن‌کردن */}
      {!pre.active && !armedUntil && (
        <div className="fx-card p-5">
          <div className="text-[14px] font-semibold text-white mb-3">
            روشن‌کردن با بازگشت خودکار
          </div>

          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <span className="text-[13px]" style={{ color: "var(--muted)" }}>
              اگر تا این مدت تایید نکنم، خاموشش کن:
            </span>
            {[3, 5, 10, 15].map((m) => (
              <button key={m} onClick={() => setMinutes(m)}
                className="px-3 py-1.5 rounded-lg text-[13px]"
                style={{
                  background: minutes === m ? "var(--accent-soft)" : "var(--surface-3)",
                  border: `1px solid ${minutes === m ? "var(--accent-2)" : "var(--border)"}`,
                  color: minutes === m ? "var(--accent-2)" : "var(--dim)",
                }}>
                {faNum(m)} دقیقه
              </button>
            ))}
          </div>

          <InfoBox>
            بعد از روشن‌شدن، اگر صفحه از کار افتاد یا ارتباطتان قطع شد،
            <b> هیچ کاری نکنید</b> — سرور خودش ظرف {faNum(minutes)} دقیقه
            فایروال را خاموش می‌کند و همه‌چیز به حالت قبل برمی‌گردد.
          </InfoBox>

          <button onClick={() => enable(false)} disabled={busy || blockers.length > 0}
            className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-2 mt-3">
            {busy ? <Loader2 size={15} className="animate-spin" />
              : <Power size={15} />}
            روشن کن
          </button>

          {blockers.length > 0 && (
            <p className="text-[12px] mt-2" style={{ color: "var(--danger)" }}>
              تا وقتی سرویس‌های حیاتی بالا قاعده نداشته باشند، این دکمه
              غیرفعال است.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
