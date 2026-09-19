"""
منطق کسب‌وکار ربات: سیستم سکه، تخفیف، سفارش و رفرال.

این ماژول عمداً از تلگرام و دیتابیس مستقل نگه داشته شده تا
بشود مستقیم و بدون شبیه‌سازی تستش کرد.
"""

import json
import os
import random
from pathlib import Path
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════
#  سیستم سکه
# ═══════════════════════════════════════════════════════════

# پله‌های پیش‌فرض طبق ایده‌ی کاربر: هر ۲۰ سکه = ۱۰٪ تخفیف
DEFAULT_COIN_TIERS = [
    {"coins": 20,  "percent": 10},
    {"coins": 40,  "percent": 20},
    {"coins": 60,  "percent": 30},
    {"coins": 80,  "percent": 40},
    {"coins": 100, "percent": 50},
]

DEFAULT_COIN_SETTINGS = {
    "enabled": True,
    "tiers": DEFAULT_COIN_TIERS,
    "per_referral": 10,        # سکه به معرف، بعد از اولین خرید زیرمجموعه
    "welcome_bonus": 0,        # سکه به کاربر جدیدی که با لینک آمده
    "max_percent": 50,         # سقف تخفیف
    "expire_days": 0,          # 0 = بدون انقضا
}


def coin_settings(raw):
    """ادغام تنظیمات ذخیره‌شده با پیش‌فرض‌ها."""
    s = dict(DEFAULT_COIN_SETTINGS)
    if isinstance(raw, dict):
        for k, v in raw.items():
            if k in s and v is not None:
                s[k] = v
    tiers = s.get("tiers") or DEFAULT_COIN_TIERS
    # مرتب‌سازی صعودی تا محاسبه‌ی پله درست باشد
    s["tiers"] = sorted(
        [t for t in tiers if isinstance(t, dict) and t.get("coins") is not None],
        key=lambda t: int(t["coins"])
    )
    return s


def tier_for(coins, settings):
    """
    بالاترین پله‌ای که کاربر با این تعداد سکه به آن رسیده.
    اگر به هیچ پله‌ای نرسیده، None برمی‌گرداند.
    """
    s = coin_settings(settings)
    if not s["enabled"]:
        return None
    reached = None
    for t in s["tiers"]:
        if coins >= int(t["coins"]):
            reached = t
        else:
            break
    if not reached:
        return None
    pct = min(int(reached["percent"]), int(s["max_percent"]))
    return {"coins": int(reached["coins"]), "percent": pct}


def next_tier(coins, settings):
    """پله‌ی بعدی و تعداد سکه‌ی لازم تا رسیدن به آن."""
    s = coin_settings(settings)
    for t in s["tiers"]:
        if coins < int(t["coins"]):
            return {"coins": int(t["coins"]),
                    "percent": int(t["percent"]),
                    "need": int(t["coins"]) - coins}
    return None


def coin_progress(coins, settings):
    """خلاصه‌ی وضعیت سکه برای نمایش به کاربر."""
    cur = tier_for(coins, settings)
    nxt = next_tier(coins, settings)
    return {
        "coins": coins,
        "current_percent": cur["percent"] if cur else 0,
        "current_cost": cur["coins"] if cur else 0,
        "next": nxt,
    }


def apply_coins(price, coins, settings):
    """
    اعمال تخفیف سکه روی قیمت.

    منطق: کاربر بالاترین پله‌ی ممکن را استفاده می‌کند و فقط سکه‌های
    همان پله مصرف می‌شود — نه همه‌ی موجودی. این‌طور اگر ۱۲۰ سکه دارد،
    ۱۰۰ تا خرج می‌کند و ۲۰ تا برایش می‌ماند.
    """
    t = tier_for(coins, settings)
    if not t or price <= 0:
        return {"price": price, "discount": 0, "percent": 0, "coins_used": 0}

    discount = price * t["percent"] // 100
    return {
        "price": max(price - discount, 0),
        "discount": discount,
        "percent": t["percent"],
        "coins_used": t["coins"],
    }


# ═══════════════════════════════════════════════════════════
#  قیمت‌گذاری سفارش
# ═══════════════════════════════════════════════════════════

def price_order(plan_price, *, coins=0, coin_cfg=None, use_coins=False,
                discount_percent=0, reseller_discount=0):
    """
    محاسبه‌ی قیمت نهایی با همه‌ی تخفیف‌ها.

    ترتیب اعمال: اول کد تخفیف، بعد سکه، بعد تخفیف عمده‌ی واسطه.
    این ترتیب عمدی است تا تخفیف‌ها روی هم ضرب نشوند و قیمت منفی نشود.
    """
    base = int(plan_price)
    price = base
    # `code_percent` کنارِ مبلغش می‌آید تا صداکننده مجبور نشود از
    # روی دو عدد دوباره درصد را حساب کند — همان‌جا که گرد‌کردن
    # عددی می‌سازد که با آنچه به مشتری گفته‌ایم یکی نیست.
    breakdown = {"base": base, "code_discount": 0, "code_percent": 0,
                 "coin_discount": 0, "reseller_discount": 0,
                 "coins_used": 0, "coin_percent": 0}

    if discount_percent > 0:
        d = price * int(discount_percent) // 100
        breakdown["code_discount"] = d
        breakdown["code_percent"] = int(discount_percent)
        price -= d

    if use_coins and coins > 0:
        res = apply_coins(price, coins, coin_cfg)
        breakdown["coin_discount"] = res["discount"]
        breakdown["coins_used"] = res["coins_used"]
        breakdown["coin_percent"] = res["percent"]
        price = res["price"]

    if reseller_discount > 0:
        d = price * int(reseller_discount) // 100
        breakdown["reseller_discount"] = d
        price -= d

    breakdown["final"] = max(price, 0)
    return breakdown


# ═══════════════════════════════════════════════════════════
#  کد تخفیف
# ═══════════════════════════════════════════════════════════

def validate_discount(row, plan_id=None):
    """بررسی اعتبار کد تخفیف. (پیام خطا, درصد)"""
    if not row:
        return "کد تخفیف پیدا نشد", 0
    if not row.get("is_active"):
        return "این کد غیرفعال است", 0
    if row.get("max_uses") and row["used_count"] >= row["max_uses"]:
        return "ظرفیت این کد تمام شده", 0
    exp = row.get("expires_at")
    if exp:
        try:
            if datetime.fromisoformat(exp) < datetime.now():
                return "این کد منقضی شده", 0
        except ValueError:
            pass
    if row.get("plan_id") and plan_id and row["plan_id"] != plan_id:
        return "این کد برای این پلن نیست", 0
    return None, int(row["percent"])


# ═══════════════════════════════════════════════════════════
#  کارت بانکی
# ═══════════════════════════════════════════════════════════

def pick_card(cards):
    """
    انتخاب کارت برای پرداخت. اگر چند کارت باشد تصادفی انتخاب می‌شود
    تا تراکنش‌ها روی یک حساب متمرکز نشوند.
    """
    active = [c for c in (cards or []) if c.get("number") and c.get("active", True)]
    if not active:
        return None
    return random.choice(active)


def fmt_card(number):
    """نمایش شماره کارت به‌صورت چهار رقم چهار رقم."""
    digits = "".join(ch for ch in str(number) if ch.isdigit())
    return "-".join(digits[i:i + 4] for i in range(0, len(digits), 4)) or number


# ═══════════════════════════════════════════════════════════
#  کمکی‌های نمایش
# ═══════════════════════════════════════════════════════════

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(v):
    """
    فارسی‌کردن ارقام یک متن.

    فقط برای چیزهایی که کاربر *می‌خواند* — نه چیزهایی که کپی می‌کند.
    شماره‌ی کارت، لینک اشتراک، کد دعوت و شناسه‌ی سفارش عمداً لاتین
    می‌مانند، چون با رقم فارسی نه در تلگرام قابل جست‌وجو می‌شوند و نه
    در اپ‌ها و درگاه‌ها درست پیست می‌شوند.
    """
    return str(v).translate(_FA_DIGITS)


#: نام ماه‌های شمسی
_FA_MONTHS = ("فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
              "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند")


def fa_date(value, with_month_name=True):
    """
    تاریخ شمسی برای مشتری فارسی‌زبان.

    تا قبل از این، ربات تاریخ انقضا را میلادی نشان می‌داد — مشتری
    ایرانی «۲۰۲۷-۰۱-۱۵» را نمی‌خواند و نمی‌فهمد چند روز دیگر است.

    اگر jdatetime نصب نباشد یا ورودی خراب باشد، همان میلادیِ قبلی
    برمی‌گردد؛ نمایش تاریخ نباید بتواند پیام را از کار بیندازد.
    """
    if not value:
        return ""
    raw = str(value)[:10]
    try:
        y, m, d = (int(x) for x in raw.split("-"))
    except (ValueError, TypeError):
        return fa(raw)

    try:
        import jdatetime
        from datetime import date as _date
        j = jdatetime.date.fromgregorian(date=_date(y, m, d))
        if with_month_name:
            return f"{fa(j.day)} {_FA_MONTHS[j.month - 1]} {fa(j.year)}"
        return fa(f"{j.year}/{j.month:02d}/{j.day:02d}")
    except Exception:
        return fa(raw)


def fa_datetime(value):
    """
    تاریخ شمسی به‌همراه ساعت — برای سفارش‌ها و رویدادها.

    ساعت همان‌طور می‌ماند؛ فقط بخش تاریخ شمسی می‌شود.
    """
    if not value:
        return ""
    raw = str(value).replace("T", " ")
    date_part = raw[:10]
    time_part = raw[11:16].strip()
    d = fa_date(date_part, with_month_name=False)
    return f"{d} — {fa(time_part)}" if time_part else d


def toman(n):
    """قالب‌بندی مبلغ با جداکننده‌ی هزارگان."""
    try:
        return fa(f"{int(n):,}".replace(",", "،"))
    except (TypeError, ValueError):
        return str(n)


def fmt_gb(gb):
    return "نامحدود" if not gb else f"{fa(gb)} گیگابایت"


def fmt_days(days):
    if not days:
        return "بدون محدودیت زمانی"
    if days % 30 == 0:
        return f"{fa(days // 30)} ماهه"
    return f"{fa(days)} روزه"


def plan_line(p):
    """یک خط توصیف پلن برای دکمه."""
    parts = [fmt_gb(p["gb"]), fmt_days(p["days"])]
    return f"{p['name']} — {' · '.join(parts)} — {toman(p['price'])} تومان"


def mins_since(when):
    """چند دقیقه از یک زمانِ محلی گذشته. نامعتبر → None."""
    if not when:
        return None
    try:
        t = datetime.fromisoformat(str(when).replace("T", " ").strip())
    except (ValueError, TypeError):
        return None
    return max(0, int((datetime.now() - t).total_seconds() // 60))


def channel_photo_dir():
    """
    پوشه‌ی عکسِ پست‌های کانال.

    **یک تعریف، دو مصرف‌کننده:** بک‌اند این‌جا می‌نویسد و زمان‌بندِ
    ربات از همین‌جا می‌خواند. اگر هر کدام پیش‌فرضِ خودش را داشت،
    اولین باری که مسیرها از هم جدا می‌شدند عکس بی‌صدا حذف می‌شد و
    پست بدونِ عکس در کانال می‌نشست — و کسی هم خطایی نمی‌دید.

    کنارِ دیتابیسِ ربات می‌نشیند، چون آن تنها مسیری است که هر دو
    پردازه قطعاً بر سرش توافق دارند.
    """
    d = os.getenv("CHANNEL_DIR")
    if d:
        return Path(d)
    db = os.getenv("BOT_DB_PATH") or os.getenv("BOT_DB")
    base = Path(db).parent if db else Path(__file__).resolve().parent.parent / "data"
    return base / "channel"


def days_left(expires_at):
    if not expires_at:
        return None
    try:
        exp = datetime.fromisoformat(expires_at)
    except (ValueError, TypeError):
        return None
    delta = exp - datetime.now()
    return max(int(delta.total_seconds() // 86400), 0) if delta.total_seconds() > 0 else 0


def days_past(expires_at):
    """
    چند روز از انقضا گذشته. اگر هنوز منقضی نشده یا تاریخ ندارد: صفر.

    days_left عمداً هیچ‌وقت منفی نمی‌دهد — ده‌ها جا روی «صفر یعنی
    تمام شده» حساب باز کرده‌اند. ولی همین یعنی با آن نمی‌شود گفت
    *چند وقت* پیش تمام شده: صفحه‌ی «اشتراک‌های من» برای هر اشتراک
    منقضی می‌نوشت «۰ روز پیش منقضی شده»، چه دیروز تمام شده بود چه
    سه ماه پیش.
    """
    if not expires_at:
        return 0
    try:
        exp = datetime.fromisoformat(expires_at)
    except (ValueError, TypeError):
        return 0
    gone = (datetime.now() - exp).total_seconds()
    return int(gone // 86400) if gone > 0 else 0


def make_email(tenant_prefix, tg_id, seq=1):
    """
    ساخت شناسه‌ی کلاینت در 3x-ui.

    از الگوی prefix_tgid_seq استفاده می‌کنیم چون سیستم واسطه‌ی صفحه‌ی
    اشتراک با پیشوند ایمیل کار می‌کند — این‌طور خودکار برند درست را می‌بیند.
    """
    prefix = "".join(ch for ch in (tenant_prefix or "nx") if ch.isalnum()).lower()[:12]
    return f"{prefix}_{tg_id}_{seq}"


def normalize_phone(raw):
    """
    یکسان‌سازی شماره‌ی ایرانی به شکل 98XXXXXXXXXX.

    تلگرام گاهی با +، گاهی بدون، و گاهی با 0 ابتدایی می‌دهد.
    بدون یکسان‌سازی، یک نفر می‌تواند با چند شکل ثبت شود.
    """
    d = "".join(ch for ch in str(raw or "") if ch.isdigit())
    if d.startswith("0098"):
        d = d[2:]
    elif d.startswith("098"):
        d = d[1:]
    elif d.startswith("09"):
        d = "98" + d[1:]
    elif d.startswith("9") and len(d) == 10:
        d = "98" + d
    return d


def pretty_phone(p):
    """نمایش خوانا: 98912... → 0912 123 4567"""
    d = normalize_phone(p)
    if d.startswith("98") and len(d) == 12:
        n = "0" + d[2:]
        return f"{n[:4]} {n[4:7]} {n[7:]}"
    return d or "—"
