"""
نرخ ارز — برای هزینه‌هایی که به یورو یا دلار پرداخت می‌شوند.

چرا وجود دارد:
    سرور خارج به یورو حساب می‌شود ولی فروش به تومان است. بدون نرخ،
    مدیر نمی‌داند هزینه‌ی واقعی‌اش چقدر بوده و سود را اشتباه حساب
    می‌کند — همیشه به نفع خودش، که بدترین حالت است.

دو قاعده‌ی مهم:
    ۱. نرخ *لحظه‌ی خرید* روی همان هزینه ذخیره می‌شود و دیگر عوض
       نمی‌شود. اگر هر بار با نرخ روز محاسبه کنیم، هزینه‌ی ماه پیش
       با تکان خوردن بازار تغییر می‌کند و حسابداری بی‌معنا می‌شود.
    ۲. نرخ دستی همیشه بر نرخ آنلاین مقدم است. کسی که خودش ارز خریده
       نرخ واقعی‌اش را می‌داند؛ ما حدس می‌زنیم.

واحدها:
    tgju قیمت‌ها را به **ریال** می‌دهد. کل برنامه به **تومان** کار
    می‌کند. تبدیل در همین ماژول انجام می‌شود تا هیچ‌جای دیگری لازم
    نباشد کسی یادش بماند.
"""

import json
import time
import urllib.request

#: منابع نرخ. هر کدام یک آدرس و راه استخراج دارد.
SOURCES = {
    "tgju": {
        "label": "بازار آزاد (tgju.org)",
        "url": "https://call3.tgju.org/ajax.json",
        "note": "نرخ لحظه‌ای بازار آزاد ایران",
    },
}

#: کلید هر ارز در خروجی tgju
_TGJU_KEYS = {"EUR": "price_eur", "USD": "price_dollar_rl", "GBP": "price_gbp"}

#: نرخ بیش از این مدت کهنه حساب می‌شود (ثانیه)
TTL = 900

_cache = {}


def _num(raw):
    """«۲,۷۴۶,۱۰۰» یا «2,746,100» را به عدد تبدیل می‌کند."""
    if raw is None:
        return None
    s = str(raw).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    s = "".join(ch for ch in s if ch.isdigit() or ch == ".")
    try:
        return float(s) if s else None
    except ValueError:
        return None


def _fetch_tgju(timeout=12):
    req = urllib.request.Request(
        SOURCES["tgju"]["url"],
        headers={"User-Agent": "Mozilla/5.0 (nexora)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def live(currency="EUR", timeout=12):
    """
    نرخ زنده به تومان.

    خروجی همیشه یک دیکشنری است، حتی وقتی شکست بخورد — صفحه‌ی
    حسابداری نباید به‌خاطر در دسترس نبودن یک سایت خالی شود.
    """
    cur = (currency or "EUR").upper()
    now = time.time()

    hit = _cache.get(cur)
    if hit and now - hit["at"] <= TTL:
        return dict(hit["data"], cached=True)

    key = _TGJU_KEYS.get(cur)
    if not key:
        return {"ok": False, "currency": cur, "toman": None,
                "error": f"ارز {cur} پشتیبانی نمی‌شود"}

    try:
        data = _fetch_tgju(timeout=timeout)
        row = (data.get("current") or data).get(key) or {}
        rial = _num(row.get("p"))
        if not rial:
            raise ValueError("قیمت در پاسخ نبود")

        out = {
            "ok": True,
            "currency": cur,
            # tgju ریال می‌دهد؛ برنامه تومان کار می‌کند
            "toman": int(round(rial / 10)),
            "rial": int(rial),
            "at": row.get("ts") or "",
            "source": "tgju",
            "sourceLabel": SOURCES["tgju"]["label"],
            "cached": False,
        }
        _cache[cur] = {"at": now, "data": out}
        return out

    except Exception as e:
        # آخرین نرخ موفق، حتی اگر کهنه باشد، از هیچ بهتر است —
        # ولی صریح می‌گوییم که کهنه است تا کسی رویش حساب باز نکند.
        if hit:
            stale = dict(hit["data"])
            stale.update(cached=True, stale=True,
                         ageMinutes=int((now - hit["at"]) / 60),
                         error=str(e))
            return stale
        return {"ok": False, "currency": cur, "toman": None,
                "error": f"نرخ خوانده نشد: {e}",
                "hint": "نرخ را دستی وارد کنید"}


def to_toman(amount, currency, manual_rate=None):
    """
    مبلغ را به تومان برمی‌گرداند، همراه با نرخی که استفاده شده.

    manual_rate اگر داده شود همیشه برنده است.
    """
    cur = (currency or "IRT").upper()
    try:
        amt = float(amount or 0)
    except (TypeError, ValueError):
        amt = 0.0

    if cur in ("IRT", "TOMAN", "تومان"):
        return {"toman": int(round(amt)), "rate": 1, "source": "toman"}

    if manual_rate:
        try:
            r = int(manual_rate)
            if r > 0:
                return {"toman": int(round(amt * r)), "rate": r,
                        "source": "manual"}
        except (TypeError, ValueError):
            pass

    rate = live(cur)
    if rate.get("ok") and rate.get("toman"):
        return {"toman": int(round(amt * rate["toman"])),
                "rate": rate["toman"],
                "source": rate.get("source", "live"),
                "stale": rate.get("stale", False)}

    return {"toman": None, "rate": None, "source": None,
            "error": rate.get("error") or "نرخ در دسترس نیست"}
