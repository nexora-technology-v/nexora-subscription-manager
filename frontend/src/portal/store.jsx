/**
 * اشتراکِ ربات و مینی‌اپِ نماینده — نوارِ وضعیت در پرتال.
 *
 * برگه: docs/specs/2026-09-26-reseller-store-subscription.md
 *
 * بی اشتراک، ربات و مینی‌اپِ نماینده نمی‌فروشند و مشتری‌ها «فروش موقتاً
 * متوقف است» می‌بینند. اگر نماینده این را فقط از زبانِ مشتری بشنود،
 * دیر فهمیده؛ پس وقتی بسته است یا نزدیکِ تمام‌شدن، روی **همه‌ی** صفحه‌ها
 * دیده می‌شود، و وقتی همه‌چیز خوب است فقط در داشبورد.
 *
 * قیمتِ صفر یعنی مالک این را پولی نکرده — هیچ نواری نشان داده نمی‌شود.
 */
import React, { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Loader2, RefreshCw, Store } from "lucide-react";
import { faNum } from "../lib/format";
import { isoToJalaliLabel } from "../ui/jalali";
import { api } from "./api.js";

// چند روز مانده به پایان، هشدار روی همه‌ی صفحه‌ها
const WARN_DAYS = 5;

export function StoreBar({ token, page, onNote }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try { setD(await api("/api/portal/store", { token })); setErr(""); }
    catch (e) { setErr(e.message); }
  }, [token]);
  useEffect(() => { load(); }, [load]);

  const buy = async () => {
    setBusy(true); setErr("");
    try {
      const j = await api("/api/portal/store/buy", { token, method: "POST" });
      onNote?.(`اشتراکِ فروشگاه تمدید شد — ${faNum(j.paid)} تومان از اعتبارتان کم شد`);
      await load();
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  // نیامدنِ وضعیت بی‌صدا نیست — ولی فقط در داشبورد، تا هر صفحه یک خطا نداشته باشد
  if (!d) {
    return err && page === "home" ? (
      <div className="px-store t-warn">
        <AlertTriangle size={15} />
        <span className="px-store-body">وضعیتِ اشتراکِ فروشگاه خوانده نشد: {err}</span>
        <button type="button" className="fx-btn-g px-3 py-1.5 text-[12px]" onClick={load}>دوباره</button>
      </div>
    ) : null;
  }
  if (!(d.price > 0)) return null;

  const left = d.until ? Math.ceil((Date.parse(d.until) - Date.now()) / 864e5) : null;
  const soon = d.open && left !== null && left <= WARN_DAYS;
  if (d.open && !soon && page !== "home") return null;

  const tone = !d.open ? "t-danger" : soon ? "t-warn" : "t-ok";
  const Icon = !d.open ? AlertTriangle : soon ? AlertTriangle : CheckCircle2;
  return (
    <div className={`px-store ${tone}`} role={d.open ? undefined : "alert"}>
      <Icon size={16} />
      <div className="px-store-body">
        <b>
          {!d.open ? "ربات و مینی‌اپِ شما الان نمی‌فروشند"
            : soon ? `اشتراکِ فروشگاه ${faNum(Math.max(0, left))} روز دیگر تمام می‌شود`
              : "اشتراکِ فروشگاه فعال است"}
        </b>
        <span>
          {!d.open
            ? "مشتری‌ها «فروش موقتاً متوقف است» می‌بینند — کانفیگ‌های فعلی‌شان کار می‌کند."
            : `تا ${isoToJalaliLabel(d.until)}${soon ? " — بعد از آن خرید و تمدیدِ مشتری‌ها می‌ایستد." : ""}`}
          {" "}
          <span className="px-store-fine">
            {d.postpaid ? "مبلغ به صورتحسابِ این دوره اضافه می‌شود."
              : `از اعتبارتان کم می‌شود — موجودی: ${faNum(d.credit)} تومان.`}
          </span>
        </span>
        {err && <span className="px-store-err">{err}</span>}
      </div>
      <button type="button" onClick={buy} disabled={busy}
        className={`${d.open && !soon ? "fx-btn-g" : "fx-btn"} px-3.5 py-2 text-[12.5px] flex items-center gap-1.5 shrink-0`}>
        {busy ? <Loader2 size={13} className="animate-spin" />
          : d.open ? <RefreshCw size={13} /> : <Store size={13} />}
        {d.open ? "تمدید" : "فعال‌سازی"} · {faNum(d.price)} تومان / {faNum(d.days)} روز
      </button>
    </div>
  );
}
