"""
نوشتنِ پستِ کانال با هوش مصنوعی — اختیاری.

برگه: docs/specs/2026-09-19-channel.md (فاز ۳)

**این ستون نیست، چاشنی است.** بخشِ کانال بدونِ این کاملاً کار
می‌کند و اگر تنظیم نشده یا از کار افتاده باشد، همان‌جا گفته
می‌شود که چرا — نه اینکه دکمه بی‌صدا هیچ نکند.

چرا «ارائه‌دهنده‌محور» و نه یک سرویسِ مشخص:

  • سرویس‌های بی‌کلید رایگان‌اند ولی تضمینی ندارند و ممکن است
    فردا بسته شوند
  • لایه‌ی رایگانِ سرویس‌های بزرگ کلید می‌خواهد و از آی‌پیِ ایران
    معمولاً بسته است
  • و هر کلیدی که باشد، **در مخزنِ عمومی نمی‌نشیند** — تنظیمِ
    سرور است، نه کد

پس مالک آدرس و کلیدِ خودش را می‌گذارد. شکلِ درخواست همان
`/v1/chat/completions` است، چون تقریباً همه‌ی سرویس‌ها و
پروکسی‌ها همین را می‌پذیرند.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request

#: سقفِ انتظار. سرویسِ کند نباید صفحه‌ی پنل را قفل کند.
TIMEOUT = 45

#: تگ‌هایی که تلگرام می‌پذیرد — در دستور می‌آید تا مدل تگِ دیگری
#: نسازد. پستی که تگِ ناشناخته داشته باشد اصلاً فرستاده نمی‌شود.
ALLOWED_HINT = "<b> <i> <u> <s> <code> <a href> <blockquote> <tg-spoiler>"


def config(settings):
    """تنظیماتِ هوش مصنوعی، با پیش‌فرض‌های امن."""
    a = (settings or {}).get("ai") or {}
    return {
        "enabled": bool(a.get("enabled")),
        "base_url": str(a.get("base_url") or "").strip().rstrip("/"),
        "api_key": str(a.get("api_key") or "").strip(),
        "model": str(a.get("model") or "").strip(),
        "image_url": str(a.get("image_url") or "").strip(),
        "tone": str(a.get("tone") or "").strip(),
    }


def why_off(cfg):
    """
    چرا نمی‌شود استفاده کرد — یا None اگر می‌شود.

    پیامِ روشن به‌جای دکمه‌ای که کار نمی‌کند.
    """
    if not cfg["enabled"]:
        return "هوش مصنوعی خاموش است"
    if not cfg["base_url"]:
        return "آدرس سرویس وارد نشده"
    if not cfg["model"]:
        return "نامِ مدل وارد نشده"
    return None


def brand_brief(*, brand="", plans=(), apps=(), support="", tone=""):
    """
    بافتِ کسب‌وکار، که به هر درخواست اضافه می‌شود.

    بدونِ این، خروجی متنِ عمومیِ اینترنتی است — همان چیزی که
    مالک خودش هم می‌توانست از هر جایی کپی کند. با این، متن دربارهٔ
    *همین* کسب‌وکار است.
    """
    bits = []
    if brand:
        bits.append(f"نام برند: {brand}")
    rows = [f"{p.get('name')} ({int(p.get('price') or 0):,} تومان)"
            for p in plans if p.get("name")]
    if rows:
        bits.append("پلن‌ها: " + "، ".join(rows[:5]))
    names = [a.get("name") for a in apps if a.get("name")]
    if names:
        bits.append("اپلیکیشن‌های پیشنهادی: " + "، ".join(names[:5]))
    if support:
        bits.append(f"پشتیبانی: {support}")
    if tone:
        bits.append(f"لحن: {tone}")
    return "\n".join(bits)


def prompt(task, brief):
    """دستورِ کامل — سیستم و کاربر."""
    sysmsg = (
        "تو نویسنده‌ی کانالِ تلگرامِ یک سرویسِ فروشِ اشتراکِ اینترنت "
        "هستی. فارسیِ روان و کوتاه بنویس.\n\n"
        "قواعد:\n"
        f"• فقط این تگ‌های HTML مجازند: {ALLOWED_HINT}\n"
        "• مارک‌داون ننویس (نه ** و نه __)\n"
        "• هر تگی که باز می‌کنی حتماً ببند\n"
        "• حداکثر ۶۰۰ کاراکتر\n"
        "• قیمت و عدد را از خودت نساز؛ فقط آنچه در بافت آمده\n"
        "• وعده‌ی دروغ نده و ادعای دورزدنِ قانون نکن\n"
        "• فقط خودِ متنِ پست را بده، بدون توضیحِ اضافه"
    )
    user = (f"بافتِ کسب‌وکار:\n{brief}\n\n" if brief else "") + f"خواسته:\n{task}"
    return sysmsg, user


def clean(text):
    """
    خروجیِ مدل را قابلِ فرستادن می‌کند.

    مدل‌ها عادت دارند متن را در ```…``` بپیچند یا مارک‌داون بنویسند.
    اینها را تلگرام تگ نمی‌شناسد و پیام یا خام می‌رود یا اصلاً
    نمی‌رود.
    """
    t = str(text or "").strip()
    t = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", t).strip()
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t, flags=re.S)
    t = re.sub(r"(?<!\w)__(.+?)__(?!\w)", r"<u>\1</u>", t, flags=re.S)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>",
               t, flags=re.S)
    return t.strip()


def _post_json(url, payload, headers, timeout=TIMEOUT):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def human_error(e):
    """
    خطای سرویس به زبانی که مالک بتواند کاری با آن بکند.

    «HTTP Error 401» به کسی نمی‌گوید کلیدش غلط است.
    """
    if isinstance(e, urllib.error.HTTPError):
        c = e.code
        if c in (401, 403):
            return "کلید پذیرفته نشد — کلید یا دسترسیِ مدل را بررسی کنید"
        if c == 404:
            return "آدرس یا نامِ مدل پیدا نشد"
        if c == 429:
            return "سرویس موقتاً محدودتان کرده — کمی بعد دوباره"
        if c >= 500:
            return "سرویس الان خطا می‌دهد — کمی بعد دوباره"
        return f"سرویس پاسخِ {c} داد"
    if isinstance(e, urllib.error.URLError):
        return ("به سرویس نرسیدیم — آدرس، اینترنتِ سرور، یا فیلترشدنش "
                "را بررسی کنید")
    if isinstance(e, TimeoutError):
        return "سرویس دیر جواب داد"
    return str(e)[:160] or "درخواست ناموفق بود"


def write(cfg, task, brief=""):
    """
    متنِ پست. برمی‌گرداند (ok, متن یا دلیلِ خطا).
    """
    off = why_off(cfg)
    if off:
        return False, off
    if not str(task or "").strip():
        return False, "بگویید دربارهٔ چه بنویسد"

    sysmsg, user = prompt(task, brief)
    url = cfg["base_url"] + "/chat/completions"
    headers = {}
    if cfg["api_key"]:
        headers["Authorization"] = "Bearer " + cfg["api_key"]

    try:
        data = _post_json(url, {
            "model": cfg["model"],
            "messages": [{"role": "system", "content": sysmsg},
                         {"role": "user", "content": user}],
            "temperature": 0.7,
            "max_tokens": 700,
        }, headers)
    except Exception as e:                       # noqa: BLE001
        return False, human_error(e)

    try:
        txt = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        # پاسخی که شکلِ منتظره را ندارد — گفتنش بهتر از متنِ خالی
        return False, "پاسخِ سرویس شکلِ منتظره را نداشت"

    out = clean(txt)
    return (True, out) if out else (False, "سرویس متنِ خالی داد")


def image_url(cfg, subject):
    """
    نشانیِ تصویر، برای سرویس‌هایی که با یک URL کار می‌کنند.

    `{q}` جای موضوع را می‌گیرد. مثال:
        https://example.com/p/{q}?w=1024

    چرا این شکل و نه یک سرویسِ مشخص: سرویسِ بی‌کلید ممکن است فردا
    بسته شود. با قالبِ آدرس، مالک هر وقت خواست جایش را عوض می‌کند
    بدونِ اینکه ما نسخه بدهیم.
    """
    tpl = cfg.get("image_url") or ""
    if not tpl or "{q}" not in tpl:
        return None
    q = urllib.parse.quote(str(subject or "").strip()[:200], safe="")
    return tpl.replace("{q}", q)
