"""
پیشنهادِ پستِ کانال، از روی رویدادهای واقعیِ پنل.

برگه: docs/specs/2026-09-19-channel.md (فاز ۲)

چرا این‌جا و نه در بک‌اند: این‌ها توابعِ خالص‌اند — ردیف می‌گیرند و
پیشنهاد می‌دهند. بدونِ FastAPI و بدونِ دیتابیس تست می‌شوند، مثلِ
`core`.

**قاعده‌ی اول: هیچ پیشنهادی از هوا ساخته نمی‌شود.** هر کدام یک
رویدادِ واقعی پشتش دارد و `why` همان رویداد را با عدد می‌گوید. اگر
رویدادی نباشد، پیشنهادی هم نیست — فهرستِ خالی از پیشنهادِ الکی
بهتر است. کانالی که هر روز پستِ توخالی دارد، از کانالِ ساکت بدتر
است.

**قاعده‌ی دوم: چیزی که قبلاً اعلام شده، دوباره پیشنهاد نمی‌شود.**
سنجش با متنِ پست‌های رفته است، نه با پرچمِ جدا — پرچم از واقعیت
جدا می‌افتد، متنِ پست نه.
"""
from datetime import datetime, timedelta


def _dt(v):
    """رشته‌ی زمانِ دیتابیس → datetime. نامعتبر → None."""
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("T", " ").strip()[:19])
    except (ValueError, TypeError):
        return None


def _said(sent_bodies, needle):
    """آیا در پست‌های رفته حرفی از این زده شده؟"""
    n = str(needle or "").strip().lower()
    if not n:
        return False
    return any(n in str(b or "").lower() for b in sent_bodies)


def _fa(n):
    """عدد فارسی — بی‌وابستگی به core، چون این ماژول خالص می‌ماند."""
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _money(n):
    return _fa(f"{int(n):,}".replace(",", "،"))


def suggest(*, now=None, plans=(), discounts=(), expiring=0, posts=(),
            trial_enabled=False, brand="", dismissed=()):
    """
    فهرستِ پیشنهادها، مهم‌ترین اول.

    ورودی‌ها همه ردیفِ ساده‌اند تا تست بتواند بسازدشان:

        plans      پلن‌های فعالِ غیرِتست: id, name, price, created_at
        discounts  کدهای فعال: code, percent, created_at, expires_at
        expiring   چند اشتراک در هفت روزِ آینده تمام می‌شود
        posts      پست‌های کانال: body, status, sent_at
        dismissed  شناسه‌هایی که مالک کنار گذاشته

    هر پیشنهاد: {id, why, title, body}
    """
    now = now or datetime.now()
    sent = [p.get("body") for p in posts if (p.get("status") == "sent")]
    sent_at = sorted((_dt(p.get("sent_at")) for p in posts
                      if p.get("status") == "sent" and p.get("sent_at")),
                     reverse=True)
    out = []

    def add(sid, why, title, body, kind="draft"):
        """
        `kind` مهم است: «draft» متن دارد و در کادر می‌نشیند، ولی
        «fix» فقط اشاره است. بدونِ این تفکیک، کلیک روی اشاره کادر
        را با متنِ خالی پر می‌کرد و به نظر می‌رسید دکمه کار نکرده.
        """
        if sid in set(dismissed):
            return
        out.append({"id": sid, "why": why, "title": title,
                    "body": body, "kind": kind})

    # ── پستی که نرفته ──
    #
    # اول از همه، چون تنها چیزی در این فهرست است که *خراب* است، نه
    # فرصت. پستی که نرفته و کسی نبیندش، همان مسیرِ خرابِ بی‌صداست.
    failed = [p for p in posts if p.get("status") == "failed"]
    if failed:
        add("failed", f"{_fa(len(failed))} پست فرستاده نشده",
            "پستِ نافرجام را ببینید", "", kind="fix")

    # ── کدِ تخفیفی که اعلام نشده ──
    #
    # پرتکرارترین فرصتِ ازدست‌رفته: مالک کد می‌سازد و هیچ‌کس خبر
    # ندارد. ظرفیتِ تمام‌شده و منقضی کنار گذاشته می‌شوند — کدی که
    # کار نمی‌کند، اعلامش بدتر از نگفتن است.
    for d in discounts:
        code = str(d.get("code") or "").strip()
        if not code or not d.get("is_active", 1):
            continue
        exp = _dt(d.get("expires_at"))
        if exp and exp < now:
            continue
        mx = int(d.get("max_uses") or 0)
        if mx and int(d.get("used_count") or 0) >= mx:
            continue
        if _said(sent, code):
            continue
        pct = int(d.get("percent") or 0)
        when = ""
        if exp:
            hrs = max(0, int((exp - now).total_seconds() // 3600))
            when = (f"\n\n<b>فقط تا {_fa(hrs)} ساعت آینده.</b>" if hrs < 72
                    else "")
        add(f"disc:{code.upper()}",
            f"کدِ {code} ساخته شده و هیچ‌وقت در کانال اعلام نشده",
            f"اعلامِ کدِ {code}",
            f"🎟 <b>کدِ تخفیف</b>\n\n"
            f"کدِ <code>{code}</code> را موقعِ خرید بزنید و "
            f"<b>{_fa(pct)}٪</b> کمتر بپردازید.{when}")

    # ── پلنِ تازه ──
    for p in plans:
        made = _dt(p.get("created_at"))
        if not made or (now - made) > timedelta(days=21):
            continue
        name = str(p.get("name") or "").strip()
        if not name or _said(sent, name):
            continue
        add(f"plan:{p.get('id')}",
            f"پلنِ «{name}» {_fa((now - made).days)} روز پیش اضافه شد "
            "و هنوز معرفی نشده",
            f"معرفیِ پلنِ {name}",
            f"📦 <b>پلنِ تازه: {name}</b>\n\n"
            f"💰 {_money(p.get('price') or 0)} تومان\n\n"
            "برای خرید، ربات را باز کنید 👇")

    # ── موجِ انقضا ──
    #
    # این تنها پیشنهادی است که مستقیم به درآمد وصل است: کسی که
    # اشتراکش دارد تمام می‌شود، با یک یادآوری تمدید می‌کند.
    if expiring >= 3:
        add(f"expiry:{now.strftime('%Y-%m-%d')}",
            f"{_fa(expiring)} اشتراک در هفت روزِ آینده تمام می‌شود",
            "یادآوریِ تمدید",
            "⏰ <b>اشتراکتان دارد تمام می‌شود؟</b>\n\n"
            "تمدید یک دکمه است و کانفیگِ فعلی‌تان <b>همان می‌ماند</b> — "
            "لازم نیست چیزی را دوباره اضافه کنید.\n\n"
            "<blockquote>قبل از تمام‌شدن تمدید کنید تا اتصالتان "
            "قطع نشود.</blockquote>")

    # ── تستِ رایگان که کسی از آن خبر ندارد ──
    if trial_enabled and not _said(sent, "تست رایگان"):
        add("trial",
            "تستِ رایگان روشن است ولی در کانال معرفی نشده",
            "معرفیِ تستِ رایگان",
            "🎁 <b>اول امتحان کنید، بعد بخرید</b>\n\n"
            f"{('در ' + brand + ' ') if brand else ''}می‌توانید یک‌بار "
            "اشتراکِ تست بگیرید و خودتان سرعت و کیفیت را ببینید.\n\n"
            "ربات را باز کنید و «تست رایگان» را بزنید.")

    # ── مدتی است چیزی نگذاشته‌اید ──
    #
    # شناسه هفتگی است: کنارگذاشتنش این هفته را ساکت می‌کند، نه
    # برای همیشه.
    last = sent_at[0] if sent_at else None
    quiet = (now - last).days if last else None
    if quiet is None or quiet >= 7:
        wk = now.strftime("%Y-W%W")
        why = ("هنوز هیچ پستی در کانال نگذاشته‌اید" if quiet is None
               else f"{_fa(quiet)} روز است پستی نگذاشته‌اید")
        add(f"quiet:{wk}", why, "یک پستِ آموزشی بگذارید",
            "📚 <b>نصب در سه قدم</b>\n\n"
            "<b>۱.</b> لینکِ اشتراکتان را کپی کنید\n"
            "<b>۲.</b> برنامه را نصب کنید\n"
            "<b>۳.</b> «افزودن از کلیپ‌بورد» را بزنید\n\n"
            "<blockquote>کمتر از دو دقیقه طول می‌کشد.</blockquote>")

    return out
