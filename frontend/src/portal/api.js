/**
 * درخواست به API پرتال با توکنِ نشستِ نماینده.
 *
 * از index.jsx جدا شد تا استودیوی پوسته (studio.jsx) — که حالا پنلِ
 * مالک هم از آن استفاده می‌کند — بی‌آنکه کلِ پرتال را بکشد، همین را
 * داشته باشد.
 */
import { API_URL } from "../lib/constants";
import { errText } from "../lib/format";
export async function api(path, { token, method = "GET", body } = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-Portal-Token": token } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const j = await res.json().catch(() => ({}));
  // errText چون FastAPI برای خطای اعتبارسنجی آرایه‌ای از آبجکت
  // برمی‌گرداند و رندر مستقیمش صفحه را سفید می‌کند.
  if (!res.ok) throw new Error(errText(j.detail, "درخواست ناموفق بود"));
  return j;
}

