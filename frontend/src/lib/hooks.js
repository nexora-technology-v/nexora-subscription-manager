/**
 * هوک‌های مشترک.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
import React, { useEffect, useRef } from "react";

/**
 * پولینگ که وقتی تب دیده نمی‌شود متوقف می‌شود.
 *
 * قبلاً صفحه‌ی مانیتورینگ هر ۵ ثانیه سرور را صدا می‌زد — حتی وقتی
 * پنل ساعت‌ها در یک تب پس‌زمینه باز مانده بود. هر فراخوانی روی سرور
 * چند subprocess اجرا می‌کند (ss، systemctl، ps)، پس این یعنی بار
 * دائمی روی همان سروری که قرار است سبک بماند.
 *
 * ms=0 یعنی پولینگ خاموش.
 */
export function usePolling(fn, ms, deps = []) {
  const saved = useRef(fn);
  useEffect(() => { saved.current = fn; });

  useEffect(() => {
    if (!ms) return undefined;
    let timer = null;

    const tick = () => { if (!document.hidden) saved.current(); };
    const start = () => { if (!timer) timer = setInterval(tick, ms); };
    const stop = () => { if (timer) { clearInterval(timer); timer = null; } };

    const onVis = () => {
      if (document.hidden) { stop(); return; }
      // برگشت به تب: یک‌بار فوری تازه کن، بعد دوباره زمان‌بندی
      saved.current();
      start();
    };

    if (!document.hidden) start();
    document.addEventListener("visibilitychange", onVis);
    return () => { stop(); document.removeEventListener("visibilitychange", onVis); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ms, ...deps]);
}
