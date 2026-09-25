"""
جریان‌های کاربری ربات.

هر handler یک تابع ساده است که (ctx, update) می‌گیرد.
ctx شامل bot، db، tenant و settings است.
"""

import json
import os
import time
import logging
from datetime import datetime

from tg import (kb, esc, TelegramError, Bot, contact_kb, remove_kb,
                valid_button_url)
import core
import db as DB
import fmt as F          # واژگان قالب‌بندی تلگرام — F.b، F.code، F.quote و…
import events as EV   # نگاشتِ نوعِ رویداد → برچسب و هشدار
from xui import XUI, XUIError
import qr

log = logging.getLogger("nexora.bot")


# ═══════════════════════════════════════════════════════════
#  Context — هر مستاجر یک نمونه دارد
# ═══════════════════════════════════════════════════════════

class Ctx:
    """
    زمینه‌ی یک درخواست.

    نکته‌ی مهم درباره‌ی بازخوانی زنده: تنظیمات و اطلاعات مستاجر هر بار
    تازه خوانده می‌شوند، پس تغییرات پنل بدون ری‌استارت ربات اعمال می‌شوند.
    فقط اتصال 3x-ui کش می‌شود (چون لاگین هزینه دارد) و آن هم وقتی
    اطلاعات اتصال عوض شود، خودکار دور ریخته می‌شود.
    """

    #: چند ثانیه تنظیمات را کش کنیم.
    #
    # صفر یعنی رفتار قبلی: هر دسترسی یک اتصال SQLite جدید، یک کوئری
    # و یک json.loads. و `ctx.s` در handlers حدود ۳۱ جا صدا زده
    # می‌شود — یعنی یک پیام ساده‌ی کاربر ده‌ها بار دیسک را می‌خورد.
    # اندازه‌گیری‌شده: ۲ms هر بار روی SSD، ۶۲ms برای یک پیام؛ روی
    # دیسک اشتراکی سرور مجازی چند برابر.
    #
    # دو ثانیه به‌اندازه‌ی کافی کوتاه است که تغییر تنظیمات در پنل
    # عملاً فوری دیده شود، و به‌اندازه‌ی کافی بلند که در طول پردازش
    # یک پیام فقط یک بار خوانده شود.
    CACHE_TTL = float(os.getenv("BOT_CTX_CACHE", "2"))

    def __init__(self, bot, tenant):
        self.bot = bot
        self._tenant0 = tenant
        self.tid = tenant["id"]
        self.db = DB.TenantDB(tenant["id"])
        self._xui = None
        self._xui_sig = None
        self._t_cache = None
        self._t_at = 0.0
        self._s_cache = None
        self._s_at = 0.0
        self._in_cache = None
        self._in_at = 0.0

    def invalidate(self):
        """دور ریختن کش — بعد از هر تغییری که خودمان در تنظیمات دادیم."""
        self._t_cache = self._s_cache = None
        self._t_at = self._s_at = 0.0

    @property
    def tenant(self):
        """اطلاعات مستاجر، با کش کوتاه."""
        now = time.time()
        if self._t_cache is None or now - self._t_at > self.CACHE_TTL:
            self._t_cache = DB.get_tenant(self.tid) or self._tenant0
            self._t_at = now
        return self._t_cache

    @property
    def s(self):
        """تنظیمات مستاجر، با کش کوتاه."""
        now = time.time()
        if self._s_cache is None or now - self._s_at > self.CACHE_TTL:
            self._s_cache = DB.tenant_settings(self.tid)
            self._s_at = now
        return self._s_cache

    @property
    def xui(self):
        # نماینده پنلِ جدا ندارد — به پنلِ مالک وصل می‌شود و کانفیگ‌هایش
        # با گروهِ خودش جدا می‌شوند. دلیلِ کامل در `DB.panel_source`.
        t = DB.panel_source(self.tenant) or self.tenant
        # امضای اتصال — اگر عوض شود یعنی ادمین تنظیمات پنل را تغییر داده
        sig = (t.get("panel_url"), t.get("panel_user"),
               t.get("panel_pass"), t.get("panel_token"))
        if self._xui is None or self._xui_sig != sig:
            self._xui = XUI(*sig)
            self._xui_sig = sig
        return self._xui

    def brand(self):
        return self.s.get("brand") or self.tenant.get("name") or "VPN"

    #: نام اینباندها با کش بلندتر — روی پنل تقریباً هرگز عوض نمی‌شوند
    INBOUND_TTL = 300.0

    def inbound_names(self):
        """
        {شناسه‌ی اینباند: نام قابل‌خواندن} از پنل ۳x-ui.

        بدون این، مشتری‌ای که سه اشتراک روی سه سرور دارد سه بار
        «یک‌ماهه پرسرعت» می‌بیند و نمی‌فهمد کدام کدام است. نام اینباند
        (remark) همان چیزی است که خودِ مدیر روی سرور گذاشته — «آلمان»،
        «فنلاند» — و دقیقاً همان است که مشتری باید ببیند.

        اگر پنل در دسترس نباشد دیکشنری خالی برمی‌گردد؛ نام سرور یک
        زینت است و نبودش نباید پیام را از کار بیندازد.
        """
        now = time.time()
        if self._in_cache is not None and now - self._in_at <= self.INBOUND_TTL:
            return self._in_cache
        names = {}
        try:
            for ib in (self.xui.inbounds() or []):
                if not isinstance(ib, dict):
                    continue
                iid = ib.get("id")
                remark = (ib.get("remark") or "").strip()
                if iid is not None and remark:
                    names[int(iid)] = remark
        except Exception:
            log.debug("نام اینباندها خوانده نشد", exc_info=True)
        self._in_cache, self._in_at = names, now
        return names

    def sub_label(self, sub, with_plan=True, plan_name=None):
        """
        نام یکتا و خوانای یک اشتراک.

        ترتیب: نام پلنی که مشتری خریده، بعد شماره‌ی خودِ کانفیگ
        (nexora_555_2 → «کانفیگ ۲»).

        نام اینباند فقط وقتی می‌آید که تنها یک اینباند در کار نباشد.
        قبلاً برعکس بود — نام اینباند *به‌جای* شماره‌ی کانفیگ می‌نشست:

            یک‌ماهه · پنل جدید
            یک‌ماهه · پنل جدید
            یک‌ماهه · پنل جدید

        چون همه‌ی کانفیگ‌ها روی یک اینباند مشترک‌اند، هر سه اشتراکِ
        مشتری دقیقاً یک اسم می‌گرفتند و صفحه‌ی تمدید نمی‌گفت کدام را
        دارد تمدید می‌کند. آن اسم هم مال پنل بود، نه چیزی که مشتری
        خریده باشد.

        plan_name را وقتی می‌دهیم که ردیف اشتراک از یک SELECT خام آمده
        باشد و ستون plan_name نداشته باشد — وگرنه «اشتراک» می‌نویسد.
        """
        parts = []
        if with_plan:
            # نام ثبت‌شده‌ی خود اشتراک اول می‌آید — همان چیزی که
            # مشتری خریده. اگر پلن بعداً حذف شود، این می‌ماند.
            parts.append(str(sub.get("plan_name") or plan_name or "اشتراک"))

        # شناسه‌ی خودِ کانفیگ — این چیزی است که دو اشتراک را از هم
        # جدا می‌کند، چون روی یک اینباند هم یکتاست.
        email = str(sub.get("client_email") or "")
        tail = email.rsplit("_", 1)[-1] if "_" in email else ""
        if tail.isdigit():
            parts.append(f"کانفیگ {core.fa(tail)}")

        # نام سرور فقط وقتی اطلاعات اضافه می‌کند که بیش از یک اینباند
        # داشته باشیم؛ با یک اینباند، برای همه یکی است و فقط طولش
        # می‌کند.
        iid = sub.get("inbound_id")
        if iid is not None:
            try:
                names = self.inbound_names()
                if len(names) > 1 and names.get(int(iid)):
                    parts.append(names[int(iid)])
            except (TypeError, ValueError):
                pass

        return " · ".join(parts) if parts else "اشتراک"

    def is_admin(self, tg_id):
        """
        تشخیص ادمین.

        نکته: owner_tg_id از فرم پنل می‌آید و ممکن است رشته باشد،
        در حالی که تلگرام همیشه عدد می‌فرستد. پس هر دو را به عدد
        تبدیل می‌کنیم تا مقایسه درست انجام شود — این باگی بود که
        باعث می‌شد ادمین اصلاً شناخته نشود.
        """
        def as_int(v):
            try:
                return int(str(v).strip())
            except (TypeError, ValueError):
                return None

        me = as_int(tg_id)
        if me is None:
            return False

        t = DB.get_tenant(self.tid)
        if as_int(t.get("owner_tg_id")) == me:
            return True

        for a in (self.s.get("admins") or []):
            if as_int(a) == me:
                return True
        return False

    #: اعلان‌هایی که اگر گروه نباشد به پیویِ صاحبِ ربات می‌روند.
    #
    # فقط آن‌هایی که کسی منتظرِ جوابشان است: رسید (مشتری پول داده)،
    # هشدار (پولِ مشتری معلق مانده)، و پیامِ پشتیبانی. عضوِ تازه و
    # آمار نه — اینها در گروه خوب‌اند، در پیوی سیل.
    DM_TOPICS = ("receipts", "alerts", "tickets")

    def staff_chat(self, topic=None):
        """
        (chat_id, topic_id) برای اعلانِ مدیریتی.

        اول گروهِ مدیریت. اگر نیست و اعلان از آن‌هایی است که کسی
        منتظرش است، پیویِ صاحبِ ربات — که نماینده با یک دکمه در پرتال
        خودش را به آن وصل می‌کند (`own_` در `/start`).

        هر دو مسیر از همین‌جا رد می‌شوند؛ نسخه‌ی دومی از «کجا بفرستم»
        یعنی روزی یکی‌شان پیوی را فراموش می‌کند.
        """
        t = DB.get_tenant(self.tid) or {}
        gid = t.get("admin_group_id")
        if gid:
            try:
                topics = json.loads(t.get("topics") or "{}")
            except json.JSONDecodeError:
                topics = {}
            return gid, topics.get(topic)
        if topic in self.DM_TOPICS and t.get("owner_tg_id"):
            return t["owner_tg_id"], None
        return None, None

    def notify_group(self, text, keyboard=None, topic=None, photo=None):
        """
        ارسال به گروه مدیریت در تاپیک مشخص — یا پیویِ صاحبِ ربات.

        `photo` بایت‌های تصویر است و متن به زیرنویسش می‌رود. چرا
        این‌جا و نه یک تابع دوم: پیداکردنِ گروه و تاپیک همین‌جاست و
        نسخه‌ی دومی از آن یعنی روزی یکی‌شان تاپیک را فراموش می‌کند.
        """
        gid, tpid = self.staff_chat(topic)
        if not gid:
            return None
        try:
            if photo:
                return self.bot.send_photo_bytes(
                    gid, photo, filename="photo.jpg",
                    # زیرنویسِ تلگرام ۱۰۲۴ کاراکتر است، نه ۴۰۹۶.
                    # بلندتر که باشد، کلِ ارسال رد می‌شود — نه اینکه
                    # کوتاه شود.
                    caption=text[:1000], keyboard=keyboard,
                    topic_id=tpid)
            return self.bot.send(gid, text, keyboard=keyboard,
                                 topic_id=tpid)
        except TelegramError as e:
            log.warning("ارسال به گروه ناموفق: %s", e)
            return None


# ═══════════════════════════════════════════════════════════
#  رویدادها — یک درِ ورودی، نه دو
# ═══════════════════════════════════════════════════════════

def record(ctx, kind, user_id=None, data=None, who=None):
    """
    ثبتِ رویداد، و اگر پولِ مشتری معلق مانده، خبرکردنِ گروه.

    چرا یک تابع و نه دو خط در هر جای شکست:
        اگر «ثبت کن» و «گروه را خبر کن» جدا نوشته شوند، جای
        هفدهم یکی‌شان را فراموش می‌کند — و آن یکی همیشه همانی
        است که مالک لازمش دارد. این‌جا `EV.is_alert` تصمیم
        می‌گیرد، نه صداکننده.

    هیچ‌وقت خطا بالا نمی‌برد: از داخلِ `except` صدا زده می‌شود و
    یک خطای فرعی نباید جای خطای اصلی را بگیرد.
    """
    try:
        ctx.db.log(kind, user_id, data)
    except Exception:
        log.debug("ثبت رویداد ناموفق (%s)", kind, exc_info=True)

    if not EV.is_alert(kind):
        return
    try:
        ctx.notify_group(EV.alert_text(kind, data, who=esc(who) if who else None))
    except Exception:
        # گروه خبردار نشد؛ ولی ردیفِ جدول سرِ جایش است. دو مسیرِ
        # جدا، تا شکستِ یکی دیگری را نبرد.
        log.debug("هشدار گروه ناموفق (%s)", kind, exc_info=True)


# ═══════════════════════════════════════════════════════════
#  منوها
# ═══════════════════════════════════════════════════════════

def miniapp_url(ctx):
    """
    آدرس مینی‌اپ. برمی‌گرداند: رشته‌ی https یا "" .

    مقدارش را **خودِ پنل** می‌نویسد: اولین باری که مدیر پنل را روی
    https باز می‌کند، بک‌اند دامنه‌ی خودش را از هدر Host می‌بیند و
    `https://<همان دامنه>/app` را این‌جا ثبت می‌کند. مینی‌اپ از همان
    `frontend/dist` سرو می‌شود که پنل، و nginx هم `try_files` دارد،
    پس `/app` بدون هیچ تنظیم تازه‌ای بالا می‌آید.

    چرا خودکار: تنظیمی که باید آدم پرش کند، پر نمی‌شود — و آن‌وقت
    قابلیتی داریم که ساخته شده و هیچ‌کس نمی‌بیندش. همان چیزی که سر
    پنل نمایندگی افتاد (ساخته شد و هیچ دکمه‌ای به آن نمی‌رسید) و سر
    اینباند پیش‌فرض (تنظیم نبود و کلِ ساخت کانفیگ می‌خوابید).

    چرا از `sub_base_url` ساخته نمی‌شود: آن آدرسِ سرویسِ اشتراکِ
    x-ui است و معمولاً روی پورت دیگری می‌نشیند. حدس‌زدن از رویش
    آدرسی می‌سازد که صفحه‌ی سفید می‌دهد — بدتر از نبودنِ دکمه.

    تلگرام فقط https را می‌پذیرد و با http خودِ *پیام* را رد می‌کند —
    نه فقط دکمه را. پس هر چیزی که https نباشد این‌جا دور ریخته
    می‌شود، نه این‌که به تلگرام برسد و کل منو را از کار بیندازد.
    """
    url = str(ctx.s.get("miniapp_url") or "").strip()
    if not url.lower().startswith("https://"):
        return ""
    url = url.rstrip("/")
    # شناسه‌ی فروشگاه در آدرس — فقط کلیدِ کشِ ظاهر، نه احراز هویت (آن
    # از امضای initData است). همه‌ی فروشگاه‌ها یک /app دارند؛ بی این،
    # مینی‌اپ پیش از رسیدنِ پاسخ نمی‌دانست مالِ کیست: بارِ اول با رنگِ
    # پیش‌فرضِ نکسورا بالا می‌آمد و بعد به پوسته‌ی فروشگاه می‌پرید، و
    # مشتری‌ای که از دو ربات می‌خرید اسپلشِ فروشگاهِ دیگر را می‌دید.
    tid = getattr(ctx, "tid", None)
    if tid is not None and "shop=" not in url:
        url += ("&" if "?" in url else "?") + f"shop={int(tid)}"
    return url


def main_menu(ctx, user):
    # ترتیب بر اساس کاری که کاربر بیشتر می‌آید انجام دهد:
    # خرید، بعد دیدن وضعیت، بعد بقیه
    rows = [
        [("🛒 خرید اشتراک", "buy")],
        [("📊 اشتراک‌های من", "mysubs"), ("👛 کیف پول", "wallet")],
        [("🎁 دعوت دوستان", "ref"), ("🪙 سکه‌های من", "coins")],
        [("🧾 سفارش‌های من", "myorders")],
    ]
    # پنل همکار فقط به کسی نشان داده می‌شود که واقعاً همکار است
    try:
        if DB.affiliate_by_tg(ctx.tid, user["tg_id"]):
            rows.append([("💼 پنل همکاری در فروش", "affiliate")])
    except Exception:
        pass

    # مینی‌اپ.
    #
    # *اضافه* بر منو، نه جایگزینِ چیزی. مینی‌اپ از دامنه‌ی ما بارگذاری
    # می‌شود و مشتری‌های ما همان کسانی‌اند که اینترنتشان محدود است.
    # اگر آن صفحه بالا نیاید، تلگرام چیزی نمی‌گوید و کاربر صفحه‌ی سفید
    # می‌بیند — پس هر کاری که از مینی‌اپ می‌شود کرد، باید از همین منو
    # هم بشود.
    app_url = miniapp_url(ctx)
    if app_url:
        rows.insert(0, [("📱 اپلیکیشن", app_url, "web_app")])

    # دکمه فقط وقتی پلنِ تستی هست. «روشن» بدونِ پلن، دکمه‌ای می‌ساخت
    # که جوابش «فعلاً فعال نیست» بود — دکمه‌ی بی‌جواب از نبودنش بدتر است.
    if (ctx.s.get("trial_enabled") and not user.get("trial_used")
            and ctx.db.trial_plan()):
        rows.insert(1, [("🎉 دریافت اشتراک تست رایگان", "trial")])
    rows.append([("📚 آموزش نصب", "help"), ("💬 پشتیبانی", "support")])
    if ctx.is_admin(user["tg_id"]):
        rows.append([("⚙️ پنل مدیریت", "admin")])
    return kb(rows)


def back_kb(to="menu"):
    return kb([[("‹ بازگشت", to)]])


def welcome_text(ctx, user):
    """
    پیام خوش‌آمد با وضعیت زنده.

    به‌جای یک متن ثابت، وضعیت واقعی کاربر را نشان می‌دهد: اشتراک فعال،
    روزهای باقی‌مانده، سکه و کیف پول. این‌طور کاربر با یک نگاه می‌فهمد
    کجاست و چه کاری باید بکند.
    """
    name = esc(user.get("first_name") or "دوست عزیز")
    brand = esc(ctx.brand())

    custom = ctx.s.get("welcome_text")
    if custom:
        return custom.replace("{name}", name).replace("{brand}", brand)

    subs = ctx.db.user_subs(user["id"], active_only=True)
    coins = user.get("coins", 0)
    balance = user.get("balance", 0)

    lines = [f"سلام {name} 👋", f"به {brand} خوش آمدید.", ""]

    if subs:
        # چند اشتراک یعنی چند سرور. اگر فقط «۱۲ روز باقی مانده» بنویسیم،
        # مشتری نمی‌داند حرف از کدام است — پس همه را با نامشان می‌آوریم.
        shown = subs[:3]
        for s in shown:
            left = core.days_left(s.get("expires_at"))
            if left is None:
                status = "بدون محدودیت زمانی"
            elif left <= 0:
                status = f"{F.b('اعتبارش تمام شده')} — وقت تمدید است"
            elif left == 1:
                status = f"فقط {F.b('امروز')} اعتبار دارد"
            elif left <= 3:
                status = f"فقط {F.b(f'{core.fa(left)} روز')} باقی مانده"
            else:
                status = f"{F.b(f'{core.fa(left)} روز')} باقی مانده"

            dot = "🔴" if (left is not None and left <= 0) else (
                  "🟡" if (left is not None and left <= 3) else "🟢")
            lines.append(f"{dot} {F.b(ctx.sub_label(s))}")
            lines.append(f"⏳ {status}")
            lines.append("")

        if len(subs) > len(shown):
            lines.append(F.i(f"و {core.fa(len(subs) - len(shown))} اشتراک دیگر "
                             "در «اشتراک‌های من»"))
    else:
        lines += [
            "هنوز اشتراکی ندارید.",
            "با <b>خرید اشتراک</b> شروع کنید — کمتر از یک دقیقه طول می‌کشد.",
        ]

    wallet_line = []
    if balance:
        wallet_line.append(f"👛 کیف پول <b>{core.toman(balance)}</b> تومان")
    if coins:
        tier = core.tier_for(coins, ctx.s)
        if tier:
            wallet_line.append(
                f"🪙 <b>{core.fa(coins)}</b> سکه <i>({core.fa(tier['percent'])}٪ تخفیف آماده)</i>")
        else:
            wallet_line.append(f"🪙 <b>{core.fa(coins)}</b> سکه")
    if wallet_line:
        lines += ["", "  ·  ".join(wallet_line)]

    return "\n".join(lines).rstrip()


# ═══════════════════════════════════════════════════════════
#  /start و ثبت‌نام + رفرال
# ═══════════════════════════════════════════════════════════

#: پیلودهایی که مینی‌اپ در `?start=` می‌فرستد.
#
#  اینها «کد معرف» نیستند و نباید به‌عنوان کد معرف خوانده شوند.
#  کد معرف شش حرفِ بزرگ از همان الفباست، پس `WALLET` می‌تواند
#  روزی کدِ واقعیِ کسی باشد — و آن‌وقت هر کسی که از مینی‌اپ روی
#  «شارژ» بزند، بی‌صدا زیرمجموعه‌ی آن نفر می‌شود.
DEEP_WORDS = ("wallet", "buy", "subs", "support")


def _deep_link(ctx, user, chat_id, arg):
    """
    مقصدِ مستقیم از مینی‌اپ. True یعنی خودش جواب داد.

    چرا لازم شد: مینی‌اپ دکمه‌هایی داشت که به `?start=wallet`
    می‌رفتند، ولی `/start` این مقدار را فقط به‌عنوان کد معرف
    می‌خواند و چون کد معتبری نبود بی‌صدا دورش می‌ریخت. نتیجه این
    بود که دکمه «کار می‌کرد» — ربات باز می‌شد — ولی کاربر در منوی
    اصلی رها می‌شد و باید خودش دنبال کیف پول می‌گشت.
    """
    arg = (arg or "").strip()
    if not arg:
        return False
    if arg == "wallet":
        show_wallet(ctx, user, chat_id, None)
        return True
    if arg == "buy":
        show_plans(ctx, user, chat_id)
        return True
    if arg == "subs":
        show_subs(ctx, user, chat_id, None)
        return True
    if arg.startswith("renew_"):
        try:
            sid = int(arg[6:])
        except ValueError:
            return False
        # مالکیت را خودِ show_renew می‌سنجد (WHERE user_id=?)، پس
        # شناسه‌ی دست‌کاری‌شده به «این اشتراک پیدا نشد» می‌رسد
        show_renew(ctx, user, chat_id, None, sid)
        return True
    return False


#: لینکِ وصل‌شدن چقدر معتبر است
OWNER_CLAIM_MINUTES = 30


def claim_owner(ctx, msg, code):
    """
    صاحبِ فروشگاه خودش را به رباتش وصل می‌کند.

    چرا لازم شد: رسیدها و هشدارها به گروهِ مدیریت می‌رفتند و
    نماینده نه گروه داشت نه راهی برای تعریفش. `owner_tg_id` هم که
    راهِ دوم است از هیچ فرمی پر نمی‌شد. پس مشتریِ نماینده رسید
    می‌فرستاد و **هیچ‌کس** خبردار نمی‌شد.

    چرا لینک و نه «آیدیِ عددی‌تان را وارد کنید»: کسی آیدیِ عددیِ
    خودش را نمی‌داند، و عددِ اشتباه یعنی رسیدها به غریبه برسد.
    این‌جا خودِ تلگرام می‌گوید چه کسی دکمه را زده.

    کد یک‌بارمصرف و کوتاه‌عمر است — هرکس این لینک را داشته باشد
    می‌تواند سفارش‌های این فروشگاه را تایید کند.
    """
    import hmac as _hmac

    frm = msg.get("from") or {}
    chat_id = (msg.get("chat") or {}).get("id") or frm.get("id")

    # متنِ خامِ تنظیمات را نگه می‌داریم: ادعای پایین روی همین متن شرط
    # می‌گذارد.
    raw = (DB.get_tenant(ctx.tid) or {}).get("settings") or "{}"
    try:
        st = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        st = {}
    if not isinstance(st, dict):
        st = {}
    want = st.get("owner_claim") if isinstance(st.get("owner_claim"), dict) else {}
    good = bool(code) and bool(want.get("code")) and \
        _hmac.compare_digest(str(code), str(want.get("code")))

    fresh = False
    try:
        fresh = datetime.fromisoformat(str(want.get("until"))[:19]) > datetime.now()
    except (TypeError, ValueError):
        fresh = False

    if not (good and fresh):
        return ctx.bot.send(
            chat_id,
            "⚠️ این لینک دیگر معتبر نیست.\n\n"
            "از پنلِ خودتان دوباره «وصلِ من به ربات» را بزنید — لینک "
            f"فقط {core.fa(OWNER_CLAIM_MINUTES)} دقیقه و یک‌بار کار می‌کند.")

    # سوزاندنِ کد و وصل‌کردن **یک** نوشتنِ شرطی است، نه دو تا.
    #
    # نسخه‌ی اول اول کد را می‌سوزاند و بعد جدا وصل می‌کرد. دو Start
    # هم‌زمان هر دو کدِ زنده را خوانده بودند و هر دو رد می‌شدند — آخری
    # برنده، بی‌آنکه کسی بفهمد. حالا شرط روی همان متنی است که خواندیم:
    # فقط یکی می‌تواند آن را عوض کند.
    st.pop("owner_claim", None)
    with DB.conn() as c:
        cur = c.execute(
            "UPDATE tenants SET settings=?, owner_tg_id=? "
            "WHERE id=? AND settings=?",
            (json.dumps(st, ensure_ascii=False), int(frm["id"]), ctx.tid, raw))
        won = cur.rowcount == 1
    if not won:
        return ctx.bot.send(
            chat_id, "⚠️ این لینک همین حالا استفاده شد. اگر شما نبودید، از "
                     "پنلِ خودتان جدا شوید و لینکِ تازه بسازید.")
    ctx.invalidate()
    ctx.db.log("owner_linked", None, {"tg": frm.get("id")})
    log.info("صاحبِ فروشگاه %s به ربات وصل شد: %s", ctx.tid, frm.get("id"))

    return ctx.bot.send(
        chat_id,
        "✅ <b>وصل شدید</b>\n\n"
        "از این به بعد رسیدِ هر خرید با دکمه‌های تایید و رد همین‌جا "
        "می‌آید، و اگر ساختِ کانفیگی گیر کند همین‌جا خبردار می‌شوید.")


def cmd_start(ctx, msg, args=None):
    """
    نمایش منوی اصلی.

    ساختِ کاربر و کارهای ثبت‌نام (پاداش خوش‌آمد، اطلاع به معرف، خبر
    به گروه) این‌جا نیست — در _get_or_create است، چون کاربر همان‌جا
    ساخته می‌شود. یک نسخه‌ی تکراری از آن منطق قبلاً این‌جا بود که
    هیچ‌وقت اجرا نمی‌شد و فقط توهم کارکردن می‌داد.
    """
    tg = msg["from"]
    user = _get_or_create(ctx, tg, args)

    ctx.db.clear_state(tg["id"])

    # اگر از مینی‌اپ آمده و مقصد مشخصی خواسته، همان‌جا ببرش
    try:
        if _deep_link(ctx, user, tg["id"], args):
            return
    except Exception:
        # مقصد خراب بود؛ منوی اصلی بهتر از هیچ است — ولی بی‌صدا نه
        log.warning("دیپ‌لینک %r کار نکرد", args, exc_info=True)

    ctx.bot.send(tg["id"], welcome_text(ctx, user), keyboard=main_menu(ctx, user))


# ═══════════════════════════════════════════════════════════
#  خرید
# ═══════════════════════════════════════════════════════════

def show_plans(ctx, user, chat_id, message_id=None):
    # عضویت اجباری کانال — قبل از دیدن پلن‌ها
    if require_membership(ctx, chat_id, message_id, user):
        return

    plans = ctx.db.plans()
    if not plans:
        text = ("فعلاً پلنی برای فروش فعال نیست.\n\n"
                "به‌زودی برمی‌گردند — اگر عجله دارید به پشتیبانی پیام بدهید.")
        return _reply(ctx, chat_id, message_id, text, back_kb())

    rows = [[(core.plan_line(p), f"plan:{p['id']}")] for p in plans]
    rows.append([("‹ بازگشت", "menu")])

    prog = core.coin_progress(user["coins"], ctx.s.get("coins"))
    hint = ""
    if prog["current_percent"]:
        hint = (f"\n\n🪙 <b>{core.fa(prog['coins'])}</b> سکه دارید — "
                f"<b>{core.fa(prog['current_percent'])}٪ تخفیف</b> روی همین خرید.")
    elif prog["next"]:
        hint = (f"\n\n🪙 با <b>{core.fa(prog['next']['need'])}</b> سکه‌ی دیگر، "
                f"{core.fa(prog['next']['percent'])}٪ تخفیف باز می‌شود.")

    _reply(ctx, chat_id, message_id,
           "🛒 <b>خرید اشتراک</b>\n\n"
           "پلن مناسبتان را انتخاب کنید — جزئیات کامل و مبلغ را "
           f"در صفحه‌ی بعد می‌بینید.{hint}", kb(rows))


def show_plan_detail(ctx, user, chat_id, message_id, plan_id):
    p = ctx.db.get_plan(plan_id)
    if not p:
        return _reply(ctx, chat_id, message_id,
                      "این پلن دیگر در دسترس نیست.\n\n"
                      "از لیست، یکی از پلن‌های فعال را انتخاب کنید.",
                      back_kb("buy"))

    cs = ctx.s.get("coins")

    # کدِ در دست، هر بار از نو سنجیده می‌شود.
    #
    # ظرفیت ممکن است بین دیدنِ این صفحه و زدنِ دکمه تمام شده باشد؛
    # قیمتی که نشان می‌دهیم باید همان باشد که گرفته می‌شود.
    dcode = ctx.db.held_discount(user["tg_id"])
    dpct, dwhy, dbad = 0, None, ""
    if dcode:
        dwhy, dpct, _ = find_discount(ctx, dcode, plan_id)
        if not dpct:
            # بی‌صدا دور انداختنش یعنی قیمت بی‌توضیح به حالتِ اول
            # برمی‌گردد و مشتری فکر می‌کند کد را اشتباه زده.
            dbad, dcode = dcode, ""
            ctx.db.set_held_discount(user["tg_id"], None)

    pr = core.price_order(p["price"], coins=user["coins"], coin_cfg=cs,
                          use_coins=True, discount_percent=dpct)
    has_coin_discount = pr["coin_discount"] > 0

    # قیمتِ «بدون سکه ولی با کد» — پایه‌ی دکمه‌ی خریدِ ساده و سنجشِ
    # کفایتِ کیف پول. بدونش مشتری‌ای که کد زده هنوز قیمتِ کامل را
    # روی دکمه می‌بیند و کیف پولش «کافی نیست» اعلام می‌شود.
    plain = core.price_order(p["price"], discount_percent=dpct)

    ips = p["ip_limit"]
    days = p["days"]
    # هر سطر یک ایموجیِ نشانه دارد تا چشم بتواند اسکن کند. بدون
    # آن‌ها، سطرها در موبایل یک بلوک متن یکنواخت می‌شوند.
    lines = [
        F.title(p["name"], "📦"),
        "",
        f"💾 {core.fmt_gb(p['gb'])} ترافیک",
        (f"⏳ {core.fa(days)} روز اعتبار" if days else "⏳ بدون محدودیت زمانی"),
        (f"📱 {core.fa(ips)} دستگاه هم‌زمان" if ips else "📱 بدون محدودیت دستگاه"),
    ]
    if p.get("description"):
        lines += ["", F.i(p["description"])]

    if dwhy:
        lines += ["", F.quote(f"🎟 کدِ <code>{esc(dbad)}</code> اعمال نشد — "
                              f"{esc(dwhy)}")]

    rows = []
    if dpct:
        lines += ["", f"🎟 کد <code>{esc(dcode)}</code> — "
                      f"{core.fa(dpct)}٪ تخفیف"]
    if has_coin_discount:
        # قیمت قبلی خط‌خورده کنار قیمت جدید: مشتری خودش مقدار
        # صرفه‌جویی را می‌بیند، که از نوشتن «۲۰٪ تخفیف» قوی‌تر است.
        lines += ["", "💰 " + F.price(core.toman(pr["final"]),
                                     old=core.toman(p["price"]))]
        lines.append(F.i(f"🪙 {core.fa(pr['coins_used'])} سکه‌ی شما خرج می‌شود "
                         f"— {core.fa(pr['coin_percent'])}٪ تخفیف"))
        rows.append([(f"🪙 خرید با تخفیف — {core.toman(pr['final'])} تومان",
                      f"chk:{plan_id}:1")])
    else:
        lines += ["", "💰 " + F.price(
            core.toman(plain["final"]),
            old=(core.toman(p["price"]) if dpct else None))]

    rows.append([(f"💳 خرید — {core.toman(plain['final'])} تومان",
                  f"chk:{plan_id}:0")])

    # دکمه‌ی کد: یا برای واردکردنش، یا برای برداشتنش. هر دو حالت
    # دیده می‌شود — کدی که روی قیمت اثر دارد و یادِ کسی نیست، همان
    # مسیرِ خرابِ بی‌صداست.
    rows.append([("✖️ برداشتن کد تخفیف", f"dscx:{plan_id}")] if dcode
                else [("🎟 کد تخفیف دارم", f"dsc:{plan_id}")])

    if user["balance"] >= plain["final"]:
        lines.append("")
        lines.append(F.quote(
            "👛 موجودی کیف پولتان برای این خرید کافی است — با پرداخت از "
            "کیف پول، اشتراک " + F.b("بدون معطلی") + " تحویل می‌شود."))
        rows.append([("👛 پرداخت آنی از کیف پول", f"wpay:{plan_id}")])

    rows.append([("‹ بازگشت", "buy")])
    _reply(ctx, chat_id, message_id, "\n".join(lines), kb(rows))


def ask_discount(ctx, user, chat_id, message_id, plan_id):
    """پرسیدنِ کد. پاسخش در `handle_discount` می‌آید."""
    p = ctx.db.get_plan(plan_id)
    if not p:
        return _reply(ctx, chat_id, message_id,
                      "این پلن دیگر در دسترس نیست.\n\n"
                      "از لیست، یکی از پلن‌های فعال را انتخاب کنید.",
                      back_kb("buy"))
    ctx.db.set_state(user["tg_id"], "await_discount", {"plan": int(plan_id)})
    return _reply(ctx, chat_id, message_id,
                  "🎟 <b>کد تخفیف</b>\n\n"
                  "کدتان را همین‌جا بفرستید.\n\n"
                  "<blockquote>اگر کدی ندارید، برگردید و بدون آن "
                  "خرید کنید.</blockquote>",
                  kb([[("‹ بازگشت", f"plan:{plan_id}")]]))


def drop_discount(ctx, user, chat_id, message_id, plan_id):
    """برداشتنِ کد — و برگشت به همان صفحه با قیمتِ بی‌تخفیف."""
    ctx.db.set_held_discount(user["tg_id"], None)
    return show_plan_detail(ctx, user, chat_id, message_id, int(plan_id))


def handle_discount(ctx, msg, user, sdata):
    """
    کدی که مشتری فرستاده.

    سنجش همان‌جایی است که مینی‌اپ هم از آن رد می‌شود
    (`find_discount` → `core.validate_discount`) — نه نسخه‌ی دومی
    که روزی از اولی دور بیفتد.
    """
    chat_id = (msg.get("chat") or {}).get("id")
    code = (msg.get("text") or "").strip()
    pid = int(sdata.get("plan") or 0)

    if not code:
        return ctx.bot.send(chat_id, "کد را به‌صورت متن بفرستید.",
                            keyboard=kb([[("‹ بازگشت", f"plan:{pid}")]]))

    err, pct, _row = find_discount(ctx, code, pid or None)
    if not pct:
        # «ظرفیت تمام شده» و «منقضی شده» دو چیزِ متفاوتند و مشتری
        # باید بداند کدام — وگرنه کدِ درست را هم دوباره می‌زند.
        return ctx.bot.send(
            chat_id,
            f"❌ {esc(err or 'کد تخفیف معتبر نیست')}\n\n"
            "اگر کد دیگری دارید بفرستید، یا برگردید.",
            keyboard=kb([[("‹ بازگشت", f"plan:{pid}")]]))

    ctx.db.set_held_discount(user["tg_id"], code)
    ctx.db.clear_state(user["tg_id"])
    fresh = ctx.db.get_user(user["tg_id"]) or user
    ctx.bot.send(chat_id, f"✅ کد پذیرفته شد — <b>{core.fa(pct)}٪</b> تخفیف")
    return show_plan_detail(ctx, fresh, chat_id, None, pid)


def find_discount(ctx, code, plan_id=None):
    """
    کدِ تخفیفِ همین مستاجر. برمی‌گرداند (خطا, درصد, ردیف).

    **جست‌وجو همیشه با `tenant_id`.** بدونش مشتریِ یک نماینده کدِ
    نماینده‌ی دیگر را استفاده می‌کند و تخفیفش از جیبِ اشتباه می‌رود.

    خودِ سنجش در `core.validate_discount` است تا ربات و مینی‌اپ و
    پنل یک قاعده داشته باشند — نه سه نسخه که روزی از هم دور بیفتند.
    """
    if not str(code or "").strip():
        return "کد وارد نشده", 0, None
    row = ctx.db.get_discount(code)
    err, pct = core.validate_discount(dict(row) if row else None, plan_id)
    return err, pct, (dict(row) if row else None)


def card_order(ctx, user, plan_id, use_coins=False, renew_sub_id=None,
               discount_code=None):
    """
    ساختِ سفارشِ کارتی: قیمت، رزروِ سکه، و انتخابِ کارت.

    برمی‌گرداند (ok, data). وقتی ok است:
        {"order":…, "plan":…, "card":…, "price":…, "ttl":…}
    وقتی نیست، `data` یکی از:
        no_plan | no_card | {"why": "coins", "left":…, "need":…}

    چرا جدا از `checkout`: مینی‌اپ هم سفارشِ کارتی می‌سازد. نسخه‌ی
    اولِ مینی‌اپ همین را دوباره نوشته بود و **دو چیز را جا انداخت**:
    تخفیفِ سکه (`core.price_order`) و مهلتِ قابل‌تنظیم
    (`order_ttl_minutes`). یعنی مشتری‌ای که سکه داشت، از مینی‌اپ
    قیمتِ کامل می‌داد. تستِ «مینی‌اپ خودش پول جابه‌جا نمی‌کند» همین
    را گرفت.
    """
    p = ctx.db.get_plan(plan_id)
    if not p:
        return False, "no_plan"

    cs = ctx.s.get("coins")
    # کدِ تخفیف پیش از سکه اعمال می‌شود — ترتیبش در
    # `core.price_order` است و عوض نمی‌شود، وگرنه قیمت‌های امروز و
    # دیروز قابلِ مقایسه نیستند.
    derr, dpct, _drow = find_discount(ctx, discount_code, plan_id) \
        if discount_code else (None, 0, None)
    if derr:
        return False, {"why": "discount", "detail": derr}
    pr = core.price_order(p["price"], coins=user["coins"], coin_cfg=cs,
                          use_coins=bool(use_coins),
                          discount_percent=dpct)

    card = core.pick_card(ctx.s.get("cards"))
    if not card:
        return False, "no_card"

    ttl = int(ctx.s.get("order_ttl_minutes") or 30)
    order = ctx.db.create_order(
        user["id"], plan_id, p["price"], pr["final"],
        coins_used=pr["coins_used"], ttl_minutes=ttl,
        # کد روی خودِ سفارش می‌نشیند، نه با ارجاع: ماه‌ها بعد باید
        # بشود گفت این مبلغ چرا این بوده، حتی اگر کد حذف شده باشد
        discount_pct=dpct, discount_code=(discount_code or None) if dpct else None,
        # اگر تمدید است، مقصد از همین‌جا ثبت می‌شود — وگرنه provision
        # نمی‌داند کدام اشتراک را باید تمدید کند و کانفیگ تازه می‌سازد
        kind=("renew" if renew_sub_id else "new"),
        renew_sub_id=renew_sub_id,
    )

    # سکه همین حالا رزرو می‌شود، نه موقع تایید.
    #
    # اگر تا تایید صبر کنیم، مشتری می‌تواند چند سفارش با همان سکه‌ها
    # بسازد — چون هنوز کم نشده‌اند — و همه را تایید بگیرد.
    if pr["coins_used"]:
        took, left = ctx.db.spend_coins(
            user["id"], pr["coins_used"], "hold",
            f"رزرو برای سفارش #{order['id']}", order_id=order["id"])
        if not took:
            ctx.db.exec(
                "UPDATE orders SET status='expired' WHERE tenant_id=? AND id=?",
                (ctx.tid, order["id"]))
            return False, {"why": "coins", "left": left,
                           "need": pr["coins_used"]}

    ctx.db.exec(
        "UPDATE orders SET card_used=?, status='pending' WHERE tenant_id=? AND id=?",
        (card.get("number"), ctx.tid, order["id"]))

    return True, {"order": ctx.db.get_order(order["id"]), "plan": p,
                  "card": card, "price": pr, "ttl": ttl}


def checkout(ctx, user, chat_id, message_id, plan_id, use_coins,
             renew_sub_id=None):
    """ساخت سفارش و نمایش اطلاعات کارت — پوسته‌ی `card_order`."""
    # پوسته فقط کد را می‌برد؛ قیمت همان‌جایی حساب می‌شود که برای
    # مینی‌اپ هم حساب می‌شود.
    held = ctx.db.held_discount(user["tg_id"])
    ok, r = card_order(ctx, user, plan_id, use_coins=use_coins,
                       renew_sub_id=renew_sub_id, discount_code=held or None)
    if not ok:
        if r == "no_plan":
            return _reply(ctx, chat_id, message_id,
                          "این پلن دیگر در دسترس نیست.\n\n"
                          "از لیست، یکی از پلن‌های فعال را انتخاب کنید.",
                          back_kb("buy"))
        if r == "no_card":
            return _reply(ctx, chat_id, message_id,
                          "راه پرداخت هنوز فعال نشده است.\n\n"
                          "یک پیام به پشتیبانی بدهید تا دستی برایتان انجام دهیم.",
                          back_kb())
        return _reply(ctx, chat_id, message_id,
                      "سکه‌های شما برای این تخفیف کافی نیست.\n\n"
                      f"موجودی: <b>{core.fa(r['left'])}</b> سکه\n"
                      f"لازم: <b>{core.fa(r['need'])}</b> سکه\n\n"
                      "<blockquote>اگر همین الان سفارش دیگری ثبت "
                      "کرده‌اید، سکه‌هایتان آن‌جا رزرو شده‌اند."
                      "</blockquote>",
                      back_kb("buy"))

    order, p, card, pr, ttl = (r["order"], r["plan"], r["card"],
                               r["price"], r["ttl"])
    # کد داخلِ سفارش ثبت شد؛ ماندنش روی کاربر یعنی خریدِ بعدی هم
    # بی‌آنکه مشتری بخواهد تخفیف می‌گیرد.
    if held:
        ctx.db.set_held_discount(user["tg_id"], None)
    ctx.db.set_state(user["tg_id"], "await_receipt", {"order_id": order["id"]})

    holder = esc(card.get("holder") or "—")
    if card.get("bank"):
        holder += f" · {esc(card['bank'])}"

    lines = [
        "🧾 <b>سفارش شما</b>",
        "",
        f"📦 {esc(p['name'])}",
        f"<i>{core.fmt_gb(p['gb'])} · {core.fmt_days(p['days'])}</i>",
        "",
    ]
    if pr["code_discount"] or pr["coin_discount"]:
        lines.append(f"قیمت: <s>{core.toman(p['price'])}</s> تومان")
    if pr["code_discount"]:
        lines.append(f"🎟 کد تخفیف: {core.fa(pr['code_percent'])}٪ "
                     f"({core.toman(pr['code_discount'])} تومان)")
    if pr["coin_discount"]:
        lines.append(f"🪙 تخفیف سکه: {core.fa(pr['coin_percent'])}٪ "
                     f"({core.fa(pr['coins_used'])} سکه)")
    lines += [
        f"💰 قابل پرداخت: <b>{core.toman(pr['final'])} تومان</b>",
        "",
        "💳 <b>مبلغ را دقیقاً به همین کارت واریز کنید</b>",
        f"<code>{core.fmt_card(card['number'])}</code>",
        f"👤 {holder}",
        "",
        f"⏳ مهلت پرداخت: <b>{core.fa(ttl)} دقیقه</b>",
        "",
        "📸 بعد از واریز، <b>عکس رسید</b> یا <b>متن پیامک بانک</b> را "
        "همین‌جا بفرستید تا بررسی شود.",
        "",
        f"<i>کد پیگیری:</i> <code>#{order['id']}</code>",
    ]

    # شماره‌ی کارت بدون خط تیره کپی می‌شود — اپ بانک با خط تیره
    # معمولاً قبول نمی‌کند و مشتری باید دستی پاکشان کند
    digits = "".join(ch for ch in str(card["number"]) if ch.isdigit())
    _reply(ctx, chat_id, message_id, "\n".join(lines),
           kb([[("📋 کپی شماره کارت", digits, "copy")],
               [("📋 کپی مبلغ", str(pr["final"]), "copy")],
               [("✖️ لغو سفارش", f"cancel:{order['id']}")]]))


def wallet_purchase(ctx, user, plan_id, renew_sub_id=None,
                    discount_code=None):
    """
    خریدِ اشتراک از کیف پول — بدونِ هیچ پوسته‌ی تلگرامی.

    برمی‌گرداند یک دیکشنری با کلیدِ `ok`. وقتی `ok` است:
        {"ok": True, "order": <ردیف سفارش>, "plan": <پلن>,
         "user": <کاربرِ تازه>, "sub": <نتیجه‌ی provision>,
         "spent": <مبلغ>, "left": <موجودی بعد>}
    وقتی نیست:
        {"ok": False, "why": "<کلید>", "plan":…, "short":…, "left":…,
         "detail": "<متن خطای ساخت>"}

    چرا جدا از `wallet_pay`:
        مینی‌اپ هم باید دقیقاً همین را انجام بدهد. اگر آن‌جا دوباره
        نوشته شود، می‌شود مسیر چهارمِ پول در این مخزن — و سه مسیر
        قبلی (کارت، کیف پول، تمدید خودکار) هر کدام یک‌بار یک قاعده
        را فراموش کردند و سه بار جدا پیدا شدند: یکی `approved` را
        پیش از ساخت می‌نوشت، یکی بعدش هیچ‌وقت نمی‌نوشت، و یکی پاداشِ
        معرف را نمی‌داد.

        پس این‌جا یک نسخه هست و هر دو مسیر صدایش می‌زنند. تستِ
        `test_flow` با ast می‌سنجد که همین تابع هر دو پرداخت را
        بدهد.
    """
    p = ctx.db.get_plan(plan_id)
    if not p:
        return {"ok": False, "why": "no_plan"}

    # کدِ تخفیف — همان اعتبارسنجِ مسیرِ کارت، تا دو مسیر یک قاعده
    # داشته باشند. بدونِ این، کدی که در ربات کار می‌کرد از کیف پول
    # رد می‌شد و مشتری قیمتِ کامل می‌داد.
    dpct = 0
    if discount_code:
        derr, dpct, _drow = find_discount(ctx, discount_code, plan_id)
        if derr:
            return {"ok": False, "why": "discount", "detail": derr, "plan": p}
    pr = core.price_order(p["price"], discount_percent=dpct)
    price = pr["final"]

    fresh = ctx.db.get_user(user["tg_id"])
    if fresh["balance"] < price:
        return {"ok": False, "why": "low_balance", "plan": p,
                "short": price - fresh["balance"],
                "left": fresh["balance"]}

    # کسر اول، سفارش بعد. اگر ترتیب برعکس باشد و کسر نگیرد، یک
    # سفارش بی‌پرداخت می‌ماند که هیچ‌کس بعداً نمی‌فهمد چه بوده.
    # `base_amount` قیمتِ پلن می‌ماند و `amount` قیمتِ پرداختی —
    # تفاوتشان همان تخفیفی است که داده شده، و گزارش‌ها از رویش
    # حساب می‌کنند.
    order = ctx.db.create_order(fresh["id"], plan_id, p["price"], price,
                                paid_from="wallet",
                                kind=("renew" if renew_sub_id else "new"),
                                renew_sub_id=renew_sub_id,
                                discount_pct=dpct,
                                discount_code=(discount_code or None) if dpct else None)
    paid, left = ctx.db.spend_balance(fresh["id"], price, "spend",
                                      f"خرید {p['name']}", order["id"])
    if not paid:
        # بین خواندن موجودی و این لحظه، پول جای دیگری خرج شده —
        # مثلاً تمدید خودکار همین کاربر که در نخ دیگری می‌دود.
        ctx.db.close_order(order["id"], "rejected", "موجودی کیف پول کافی نبود")
        return {"ok": False, "why": "race", "plan": p, "left": left}

    ok, result = provision(ctx, order["id"])
    if not ok:
        # بستن و برگرداندن پول، با هم و یک بار.
        ctx.db.close_order(order["id"], "rejected", "خطا در ساخت کانفیگ")
        return {"ok": False, "why": "provision", "plan": p,
                "detail": str(result)}

    # حالا که کانفیگ ساخته شد، این یک فروشِ تمام‌شده است.
    #
    # بدون این خط سفارش pending می‌ماند و جاروکشِ سفارش‌های منقضی
    # نیم‌ساعت بعد «منقضی»‌اش می‌کرد — فروشی که انجام شده و در هیچ
    # آماری نیست.
    ctx.db.close_order(order["id"], "approved")

    # فروش با کیف پول هم فروش است — همکار باید سهمش را بگیرد
    _pay_commission(ctx, fresh, order["id"])

    # و پاداش معرف هم همین‌طور. ربات گفته «هر دوستی که با لینک شما
    # بیاید و خرید کند، N سکه به شما می‌رسد» — حرفی از روشِ پرداخت
    # نیست. این پاداش زمانی فقط از مسیر کارت می‌آمد.
    _reward_referrer(ctx, fresh, order["id"])

    # گروه مدیریت باید این فروش را ببیند. هر رویدادِ پولیِ دیگر خودش
    # را اعلام می‌کند؛ فقط خریدِ کیف‌پولی بی‌صدا بود.
    ctx.notify_group(
        f"👛 <b>خرید با کیف پول</b>\n"
        f"کاربر: {esc(fresh.get('first_name') or fresh['tg_id'])} "
        f"(<code>{fresh['tg_id']}</code>)\n"
        f"پلن: {esc(p['name'])}"
        + ("\nنوع: تمدید" if renew_sub_id else "")
        + f"\nمبلغ: {core.toman(p['price'])} تومان")

    return {"ok": True, "order": order, "plan": p, "user": fresh,
            "sub": result, "spent": p["price"], "left": left}


def wallet_pay(ctx, user, chat_id, message_id, plan_id,
               renew_sub_id=None):
    """
    پرداخت مستقیم از کیف پول — پوسته‌ی تلگرامیِ `wallet_purchase`.

    این‌جا فقط پیام ساخته می‌شود؛ هیچ پولی این‌جا جابه‌جا نمی‌شود.
    """
    held = ctx.db.held_discount(user["tg_id"])
    r = wallet_purchase(ctx, user, plan_id, renew_sub_id=renew_sub_id,
                        discount_code=held or None)

    if r["ok"]:
        # خرج شد — دیگر روی کاربر نمی‌ماند.
        if held:
            ctx.db.set_held_discount(user["tg_id"], None)
        _reply(ctx, chat_id, message_id,
               f"✅ <b>{core.toman(r['spent'])}</b> تومان از کیف پولتان کم شد.\n\n"
               "اشتراک آماده است — همین پایین برایتان فرستادیم.", None)
        return deliver(ctx, r["user"], r["sub"])

    why = r["why"]
    if why == "no_plan":
        return _reply(ctx, chat_id, message_id,
                      "این پلن دیگر در دسترس نیست.", back_kb("buy"))

    if why == "discount":
        # کد بین دیدنِ صفحه و زدنِ دکمه از کار افتاد. برش می‌داریم و
        # می‌گوییم چه شد — نه اینکه خرید بی‌توضیح نشود.
        ctx.db.set_held_discount(user["tg_id"], None)
        return _reply(ctx, chat_id, message_id,
                      f"🎟 {esc(r.get('detail') or 'کد تخفیف معتبر نیست')}\n\n"
                      "کد برداشته شد. دوباره امتحان کنید.",
                      kb([[("‹ بازگشت", f"plan:{plan_id}")]]))

    if why == "low_balance":
        return _reply(ctx, chat_id, message_id,
                      "موجودی کیف پولتان برای این پلن کافی نیست.\n\n"
                      f"موجودی: <b>{core.toman(r['left'])}</b> تومان\n"
                      f"کسری: <b>{core.toman(r['short'])}</b> تومان\n\n"
                      "می‌توانید کیف پول را شارژ کنید یا کارت‌به‌کارت بپردازید.",
                      back_kb("buy"))

    if why == "race":
        return _reply(ctx, chat_id, message_id,
                      "موجودی کیف پولتان کافی نیست.\n\n"
                      f"موجودی: <b>{core.toman(r['left'])}</b> تومان\n"
                      f"لازم: <b>{core.toman(r['plan']['price'])}</b> تومان\n\n"
                      "<blockquote>اگر همین الان خرید دیگری انجام داده‌اید یا "
                      "تمدید خودکارتان اجرا شده، ممکن است موجودی تغییر کرده "
                      "باشد.</blockquote>",
                      back_kb("buy"))

    return _reply(ctx, chat_id, message_id,
                  "ساخت اشتراک به مشکل خورد و <b>مبلغ کامل به کیف پولتان برگشت</b>.\n\n"
                  f"<i>{esc(r.get('detail') or '')}</i>\n\n"
                  "<blockquote>چند دقیقه دیگر دوباره امتحان کنید — اگر باز هم "
                  "نشد، پشتیبانی همین را می‌بیند و پیگیری می‌کند."
                  "</blockquote>",
                  back_kb())


def receipt_submit(ctx, user, order_id, rtype, rfile=None, rtext=None,
                   photo_bytes=None):
    """
    ثبتِ رسیدِ یک سفارشِ کارتی، و خبردادن به گروه مدیریت.

    برمی‌گرداند (ok, why). `why` یکی از:
        closed   سفارش دیگر باز نیست
        expired  مهلتش تمام شده
        race     درست همین لحظه منقضی شد

    چرا جدا از `handle_receipt`: مینی‌اپ هم باید دقیقاً همین را
    انجام بدهد — همان قاعده‌ی مهلت، همان ادعای اتمی، همان اعلان با
    دکمه‌های تایید و رد. اگر آن‌جا دوباره نوشته شود، دو مسیرِ رسید
    می‌شود و روزی یکی‌شان اعلان را جا می‌اندازد؛ آن‌وقت مشتری پول
    داده و هیچ‌کس خبر ندارد.

    `photo_bytes` برای جایی است که عکس از تلگرام نیامده (مینی‌اپ):
    همان‌جا به گروه آپلود می‌شود و `file_id`ش برمی‌گردد — پس پنل و
    پنل نماینده بدون هیچ تغییری همان رسید را نشان می‌دهند.
    """
    order = ctx.db.get_order(order_id)
    if not order or order["status"] != "pending":
        return False, "closed"

    if order.get("expires_at"):
        try:
            if datetime.fromisoformat(order["expires_at"]) < datetime.now():
                ctx.db.exec(
                    "UPDATE orders SET status='expired' WHERE tenant_id=? AND id=?",
                    (ctx.tid, order_id))
                _release_coins(ctx, order_id)
                return False, "expired"
        except ValueError:
            # مهلتِ ناخوانا یعنی قاعده‌ی مهلت اجرا نشد؛ رسید پذیرفته می‌شود،
            # ولی بی‌صدا نه
            log.warning("order %s has unreadable expires_at %r — deadline not enforced",
                        order_id, order.get("expires_at"))

    t = DB.get_tenant(ctx.tid)
    # گروه، یا پیویِ صاحبِ ربات — همان قاعده‌ی `notify_group`.
    gid, receipts_topic = ctx.staff_chat("receipts")

    # عکسی که از تلگرام نیامده باید اول آپلود شود تا `file_id` بگیرد.
    #
    # همین آپلود، خودش اعلانِ گروه هم هست — دو کار با یک درخواست. و
    # مهم‌تر: بعدش رسیدِ مینی‌اپ دقیقاً مثل رسیدِ ربات ذخیره می‌شود،
    # پس هیچ‌جای پایین‌دست لازم نیست بداند از کجا آمده.
    uploaded = None
    if photo_bytes and gid:
        try:
            r = ctx.bot.send_photo_bytes(
                gid, photo_bytes, filename=f"receipt-{order_id}.jpg",
                caption=_receipt_caption(ctx, user, order, rtext),
                topic_id=receipts_topic)
            ph = ((r or {}).get("result") or {}).get("photo") or []
            if ph:
                uploaded = ph[-1].get("file_id")
        except (TelegramError, KeyError, TypeError) as e:
            log.warning("آپلود رسید مینی‌اپ ناموفق: %s", e)

    # `rfile` اگر از قبل آمده، منبعِ اصلی است و جایش را نمی‌دهد.
    #
    # مینی‌اپ عکس را روی دیسکِ خودمان می‌گذارد و ارجاعِ `local:` را
    # می‌فرستد. اگر این‌جا با `file_id` تلگرام جایگزین شود، همان
    # وابستگی برمی‌گردد که باعث گم‌شدنِ رسید شده بود. `uploaded`
    # فقط برای پیامِ گروه است.
    if uploaded and not rfile:
        rfile = uploaded

    # شرطی، نه بی‌قید: بین بررسی مهلت بالا و همین لحظه، جاروکشِ
    # زمان‌بند می‌تواند سفارش را منقضی کرده و سکه‌ها را پس داده باشد.
    if not ctx.db.attach_receipt(order_id, rtype, rfile, rtext):
        return False, "race"

    # اگر عکس همین حالا آپلود شد، گروه خبردار شده — فقط دکمه‌ها را
    # جدا می‌فرستیم. وگرنه اعلانِ کامل.
    buttons = kb([[("✅ تایید", f"ap:{order_id}"), ("❌ رد", f"rj:{order_id}")]])
    info = _receipt_caption(ctx, user, order, rtext)

    if uploaded:
        ctx.notify_group(f"سفارش #{order_id} — تصمیم شما؟",
                         keyboard=buttons, topic="receipts")
        return True, None

    if gid and rtype == "photo" and rfile and not str(rfile).startswith("local:"):
        try:
            ctx.bot.send_photo(gid, rfile, caption=info, keyboard=buttons,
                               topic_id=receipts_topic)
            return True, None
        except TelegramError as e:
            log.warning("ارسال عکس رسید ناموفق: %s", e)

    ctx.notify_group(info, keyboard=buttons, topic="receipts")
    return True, None


def _receipt_caption(ctx, user, order, rtext):
    """متنِ اعلانِ رسید — یک شکل، از هر مسیری که آمده باشد."""
    plan = ctx.db.get_plan(order["plan_id"])
    who = esc(user.get("first_name") or "بدون نام")
    if user.get("username"):
        who += f" · @{esc(user['username'])}"
    info = (
        f"🧾 <b>رسید جدید — سفارش #{order['id']}</b>\n\n"
        f"{who}\n"
        f"<code>{user['tg_id']}</code>\n\n"
        f"{esc(plan['name']) if plan else '—'}\n"
        f"<b>{core.toman(order['amount'])}</b> تومان"
    )
    if order["coins_used"]:
        info += (f"\nبا {core.fa(order['coins_used'])} سکه · "
                 f"{core.fa(order['discount_pct'])}٪ تخفیف")
    if rtext:
        info += f"\n\n<i>{esc(rtext[:400])}</i>"
    return info


def handle_receipt(ctx, msg, user, state_data):
    """
    رسیدی که مشتری در گفتگوی ربات فرستاده.

    پوسته‌ی تلگرامیِ `receipt_submit` — این‌جا فقط پیام ساخته می‌شود.
    """
    order_id = state_data.get("order_id")

    rtype = rfile = rtext = None
    if msg.get("photo"):
        rtype = "photo"
        rfile = msg["photo"][-1]["file_id"]
        rtext = msg.get("caption")
    elif msg.get("text"):
        rtype = "text"
        rtext = msg["text"]
    else:
        return ctx.bot.send(user["tg_id"],
                            "برای ثبت پرداخت، <b>عکس رسید</b> یا "
                            "<b>متن پیامک بانک</b> را بفرستید.")

    ok, why = receipt_submit(ctx, user, order_id, rtype, rfile, rtext)
    ctx.db.clear_state(user["tg_id"])

    if ok:
        return ctx.bot.send(user["tg_id"], _waiting_text(ctx, order_id),
                            keyboard=_waiting_kb(ctx, order_id))

    if why == "closed":
        return ctx.bot.send(user["tg_id"],
                            "این سفارش دیگر باز نیست — شاید قبلاً بررسی "
                            "یا لغو شده باشد.\n\n"
                            "وضعیتش را از «سفارش‌های من» ببینید.",
                            keyboard=main_menu(ctx, user))

    if why == "expired":
        return ctx.bot.send(user["tg_id"],
                            "⌛️ مهلت این سفارش تمام شد.\n\n"
                            "اگر واریز کرده‌اید نگران نباشید — "
                            "به پشتیبانی پیام بدهید تا دستی ثبت شود.\n"
                            "وگرنه از «خرید اشتراک» یک سفارش تازه بسازید.",
                            keyboard=main_menu(ctx, user))

    return ctx.bot.send(
        user["tg_id"],
        "⌛️ درست همین لحظه مهلت این سفارش تمام شد.\n\n"
        "اگر واریز کرده‌اید نگران نباشید — رسیدتان را برای پشتیبانی "
        "بفرستید تا دستی ثبت شود.\n"
        "وگرنه از «خرید اشتراک» یک سفارش تازه بسازید.",
        keyboard=main_menu(ctx, user))


def _waiting_text(ctx, order_id):
    """
    پیام انتظار تایید.

    به‌جای برگرداندن کاربر به منوی اصلی (که گیج‌کننده است و انگار
    چیزی نشده)، وضعیت را روشن می‌گوییم و راه ارتباط می‌دهیم.
    """
    tpl = ctx.s.get("waiting_text")
    support = ctx.s.get("support_username") or ""
    if tpl:
        return (tpl.replace("{order_id}", str(order_id))
                   .replace("{support}", support))

    txt = (
        "✅ <b>رسیدتان رسید</b>\n\n"
        "⏳ الان در صف بررسی است — معمولاً کمتر از <b>۱۵ دقیقه</b>.\n"
        "📩 به‌محض تأیید، اشتراک همین‌جا برایتان می‌آید.\n\n"
        "<blockquote>لازم نیست منتظر بمانید؛ می‌توانید تلگرام را ببندید.</blockquote>\n\n"
        f"<i>کد پیگیری:</i> <code>#{order_id}</code>"
    )
    if support:
        txt += ("\n\n<i>اگر بیشتر از یک ساعت طول کشید، همین کد را "
                "برای پشتیبانی بفرستید.</i>")
    return txt


def _waiting_kb(ctx, order_id):
    support = ctx.s.get("support_username") or ""
    rows = [[("📊 وضعیت سفارش", f"ost:{order_id}")]]
    if support:
        rows.append([("🎧 پشتیبانی", f"https://t.me/{support.lstrip('@')}", "url")])
    rows.append([("‹ منوی اصلی", "menu")])
    return kb(rows)


def show_order_status(ctx, user, chat_id, message_id, order_id):
    """وضعیت لحظه‌ای یک سفارش برای مشتری."""
    o = ctx.db.get_order(order_id)
    if not o or o["user_id"] != user["id"]:
        return _reply(ctx, chat_id, message_id, "سفارش پیدا نشد.", back_kb())

    labels = {
        "awaiting": ("⏳", "در انتظار بررسی"),
        "review": ("🔍", "در حال بررسی"),
        "panel_approve": ("⚙️", "تایید شد — در حال ساخت کانفیگ"),
        "approved": ("✅", "تایید شد"),
        "rejected": ("❌", "تایید نشد"),
        "expired": ("⌛️", "منقضی شد"),
    }
    icon, label = labels.get(o["status"], ("•", o["status"]))
    p = ctx.db.get_plan(o["plan_id"]) if o.get("plan_id") else None

    txt = (
        f"{icon} <b>وضعیت سفارش: {label}</b>\n\n"
        f"{esc(p['name']) if p else '—'}\n"
        f"<b>{core.toman(o['amount'])}</b> تومان\n"
        f"ثبت شده در {core.fa_datetime(o.get('created_at'))}\n\n"
        f"<i>کد پیگیری:</i> <code>#{order_id}</code>"
    )
    if o["status"] == "rejected" and o.get("admin_note"):
        txt += f"\n\n<b>دلیل رد شدن:</b>\n{esc(o['admin_note'])}"

    return _reply(ctx, chat_id, message_id, txt, _waiting_kb(ctx, order_id))




def _free_email(ctx, user, prefix, limit=30):
    """
    شناسه‌ی کانفیگ تازه برای این مشتری — تضمین‌شده آزاد.

    قبلاً شماره از *تعداد* اشتراک‌های ثبت‌شده می‌آمد:

        seq = len(user_subs(...)) + 1

    تا وقتی جدول فقط رشد می‌کند این درست است. ولی شماره باید از
    بیشترین شماره‌ی موجود بیاید نه از تعداد، وگرنه هر شکافی در
    دنباله — یک ردیف که جا افتاده، یا دیتابیسی که از نسخه‌ی قدیمی‌تر
    بازگردانی شده — شماره را عقب می‌برد و روی کانفیگی می‌نشیند که
    در x-ui هنوز زنده است و مشتری دیگری دارد از آن استفاده می‌کند.

    پس دو محافظ: شماره از بیشینه، و بعد پرسیدن از خود پنل که آزاد
    است یا نه. یک درخواست اضافه در هر خرید، در برابر گرفتنِ کانفیگِ
    یک مشتریِ فعال.
    """
    subs = ctx.db.user_subs(user["id"], active_only=False)

    top = 0
    for sb in subs:
        tail = str(sb.get("client_email") or "").rsplit("_", 1)[-1]
        if tail.isdigit():
            top = max(top, int(tail))
    seq = max(top, len(subs)) + 1

    for _ in range(limit):
        email = core.make_email(prefix, user["tg_id"], seq)
        try:
            taken = ctx.xui.find_client(None, email=email)
        except Exception:
            # پنل جواب نداد — شماره‌ی محاسبه‌شده بهترین چیزی است که
            # داریم. متوقف‌کردن خرید به‌خاطر یک بررسی، بدتر است.
            return email
        if not taken:
            return email
        log.warning("شناسه‌ی %s در پنل گرفته است — شماره‌ی بعدی", email)
        seq += 1

    return core.make_email(prefix, user["tg_id"], seq)


#: پاسخ approve_order وقتی نخِ دیگری همین سفارش را برداشته.
#: صداکننده باید این را از «ساخت کانفیگ شکست خورد» تشخیص بدهد،
#: چون پاسخِ درست به این یکی صبر است نه تلاش دوباره.
ORDER_BUSY = "این سفارش همین حالا در حال پردازش است"


def _pay_commission(ctx, user, order_id):
    """
    ثبت پورسانت همکار فروش برای یک فروش موفق.

    همه‌ی مسیرهای فروش این را صدا می‌زنند — کارت، کیف پول، و تمدید
    خودکار. قبلاً فقط مسیر کارت صدایش می‌زد، و همکاری که مشتری آورده
    بود از خریدهای کیف‌پولی و تمدیدهای خودکارِ همان مشتری سهمی
    نمی‌گرفت.

    **مبلغ از خودِ سفارش خوانده می‌شود، نه از صداکننده.**

    سه صداکننده سه پایه می‌دادند: دو تا `plan["price"]` و یکی
    `order["amount"]`. تا وقتی تخفیفی در کار نبود هر سه یک عدد
    می‌شدند و تفاوت دیده نمی‌شد — ولی با کد تخفیف، آن دو روی پولی
    پورسانت می‌دهند که هرگز دریافت نشده.

    پورسانت سهمی از *درآمد* است. پس پایه‌اش `amount` است، یعنی
    آنچه مشتری واقعاً پرداخت کرده.

    ثبت دوباره ممکن نیست: جدول روی (مستاجر، سفارش) یکتاست، پس اگر
    تاییدی دو بار اجرا شود پورسانت دو بار حساب نمی‌شود.

    خطا این‌جا نباید تحویل کانفیگ را متوقف کند؛ فروش انجام شده و
    مشتری منتظر است.
    """
    row = ctx.db.get_order(order_id)
    amount = int((row or {}).get("amount") or 0)
    try:
        res = DB.record_commission(ctx.tid, user["id"], order_id, amount)
    except Exception:
        log.debug("ثبت پورسانت ناموفق", exc_info=True)
        return None
    if not res:
        return None

    aff = res["affiliate"]
    try:
        ctx.notify_group(
            f"💼 <b>پورسانت همکار</b>\n"
            f"همکار: {esc(aff['name'])}\n"
            f"سفارش #{order_id} — {core.toman(amount)} تومان\n"
            f"پورسانت: {core.toman(res['commission'])} تومان "
            f"({core.fa(aff['percent'])}٪)")
        if aff.get("tg_id"):
            ctx.bot.send(
                aff["tg_id"],
                F.lines(
                    F.header("یک فروش تازه از لینک شما", "💼"),
                    "",
                    F.row("مبلغ خرید", core.toman(amount) + " تومان", "🛒"),
                    F.row("پورسانت شما",
                          core.toman(res["commission"]) + " تومان", "💰"),
                    "",
                    F.quote("مانده‌ی کلتان را از «پنل همکاری در فروش» "
                            "ببینید.")))
    except Exception:
        log.debug("اطلاع پورسانت ناموفق", exc_info=True)
    return res


def approve_order(ctx, order_id, admin_tg_id):
    order = ctx.db.get_order(order_id)
    if not order:
        return False, "سفارش پیدا نشد"
    # سفارشی که تایید شده *و* کانفیگش ساخته شده، دوباره تایید نمی‌شود.
    #
    # ولی سفارشی که در نسخه‌های قبل approved شد و ساخت کانفیگش شکست
    # خورد، بدون sub_id مانده است. اگر آن را هم رد کنیم، برای همیشه
    # گیر می‌کند و مشتری پول داده و چیزی نگرفته. این‌ها باید بتوانند
    # دوباره تلاش کنند.
    if order["status"] == "approved" and order.get("sub_id"):
        return False, "این سفارش قبلاً تایید شده و کانفیگش ساخته شده"

    # ادعای اتمی، *قبل* از هر کاری.
    #
    # فقط یک نخ می‌تواند برنده شود؛ بقیه همین‌جا برمی‌گردند. بدون این،
    # دو تایید هم‌زمان هر دو نگهبان بالا را رد می‌کردند و مشتری با یک
    # پرداخت دو کانفیگ می‌گرفت.
    if not ctx.db.claim_order(order_id, admin_tg_id):
        return False, ORDER_BUSY

    def _unclaim(note):
        """ادعا را پس می‌دهیم تا تلاش دوباره ممکن بماند."""
        ctx.db.exec(
            "UPDATE orders SET status='awaiting', admin_note=? "
            "WHERE tenant_id=? AND id=? AND sub_id IS NULL",
            (note[:180], ctx.tid, order_id))

    # شارژ کیف پول کانفیگ ندارد — فقط موجودی اضافه می‌شود
    if order.get("kind") == "topup":
        u = ctx.db.get_user_by_id(order["user_id"])
        ctx.db.add_balance(u["id"], order["amount"], "topup",
                           "شارژ کیف پول", order_id)
        fresh = ctx.db.get_user_by_id(u["id"])
        ctx.bot.send(
            u["tg_id"],
            "✅ <b>کیف پولتان شارژ شد</b>\n\n"
            f"واریزی: {core.toman(order['amount'])} تومان\n"
            f"موجودی جدید: <b>{core.toman(fresh['balance'])}</b> تومان\n\n"
            "حالا می‌توانید بدون انتظارِ تأیید رسید خرید کنید.")
        ctx.notify_group(
            f"💳 <b>شارژ کیف پول</b>\n"
            f"کاربر: {esc(u.get('first_name') or u['tg_id'])}\n"
            f"مبلغ: {core.toman(order['amount'])} تومان")
        return True, "شارژ انجام شد"

    # ساخت کانفیگ *قبل* از تایید نهایی.
    #
    # قبلاً سفارش اول approved می‌شد و بعد کانفیگ ساخته می‌شد. اگر
    # ساخت شکست می‌خورد، سفارش برای همیشه در حالت «تایید شده ولی
    # بدون کانفیگ» گیر می‌کرد و تلاش دوباره هم با پیام «قبلاً تایید
    # شده» رد می‌شد. حالا تا کانفیگ ساخته نشود، سفارش در صف بررسی
    # می‌ماند و ادمین می‌تواند دوباره تایید بزند.
    # ساخت کانفیگ چند ثانیه طول می‌کشد؛ تا آن موقع کاربر «در حال
    # تایپ» می‌بیند و فکر نمی‌کند ربات قطع شده
    try:
        buyer = ctx.db.get_user_by_id(order["user_id"])
        if buyer:
            ctx.bot.action(buyer["tg_id"], "typing")
    except Exception:
        pass

    # ساخت کانفیگ چند ثانیه طول می‌کشد؛ بدون این، مشتری سکوت می‌بیند
    try:
        u0 = ctx.db.get_user_by_id(order["user_id"])
        if u0:
            ctx.bot.action(u0["tg_id"], "typing")
    except Exception:
        pass

    ok, result = provision(ctx, order_id)
    if not ok:
        # ادعا را پس می‌دهیم، وگرنه سفارشی که ساختش شکست خورده
        # approved می‌ماند و هیچ‌کس نمی‌تواند دوباره تلاش کند.
        _unclaim(f"خطای ساخت: {result}")
        return False, result

    user = ctx.db.get_user_by_id(order["user_id"])

    # پورسانت همکار فروش — بعد از ساخت موفق کانفیگ، چون تا وقتی
    # کانفیگ تحویل نشده فروشی اتفاق نیفتاده
    _pay_commission(ctx, user, order_id)

    # سکه هنگام ثبت سفارش رزرو شده — این‌جا فقط نوعش را ثبت می‌کنیم
    # که در تاریخچه «خرج‌شده» دیده شود، نه «رزرو».
    #
    # کم‌کردن دوباره‌ی آن، همان باگی بود که با دو سفارش هم‌زمان
    # موجودی را منفی می‌کرد.
    if order["coins_used"]:
        ctx.db.exec(
            "UPDATE coin_tx SET kind='spend', note=? "
            "WHERE tenant_id=? AND order_id=? AND kind='hold'",
            (f"تخفیف سفارش #{order_id}", ctx.tid, order_id))

    # پاداش معرف — فقط بعد از اولین خرید موفق
    _reward_referrer(ctx, user, order_id)

    # تحویل نباید بتواند جریان تایید را بشکند.
    #
    # قبلاً اگر ارسال پیام به مشتری خطا می‌داد، همان استثنا تا بالا
    # می‌رفت: پیام تایید به ادمین هم نمی‌رسید و دکمه‌های رسید سر جایشان
    # می‌ماندند، انگار تایید اصلاً ثبت نشده. کانفیگ ساخته شده بود ولی
    # هیچ‌کس خبر نداشت.
    # خبرِ تایید در صندوقِ مینی‌اپ — پیش از تحویل، چون تحویل ممکن
    # است شکست بخورد و آن‌وقت مشتری حتی نمی‌فهمد تایید شده.
    try:
        ctx.db.chat_add(order["user_id"], "system",
                        f"رسید سفارش #{order_id} تایید شد و اشتراکتان ساخته شد.",
                        order_id=order_id)
    except Exception:
        log.warning("ثبت خبرِ تایید در صندوق ناموفق", exc_info=True)

    try:
        deliver(ctx, user, result)
    except Exception as e:
        log.exception("ارسال کانفیگ به مشتری ناموفق")
        # فقط ثبت: پیامِ گروه همین پایین دست‌ساز است و راهنمای
        # عمل دارد، پس `record` نباید پیامِ دومی روی آن بفرستد.
        try:
            ctx.db.log("deliver_failed", order["user_id"],
                       {"order": order_id, "error": str(e)})
        except Exception:
            log.debug("ثبت رویداد ناموفق", exc_info=True)
        ctx.notify_group(
            f"⚠️ <b>کانفیگ ساخته شد ولی به مشتری نرسید</b>\n\n"
            f"سفارش <code>#{order_id}</code> · "
            f"{esc(user.get('first_name') or user['tg_id'])}\n"
            f"<code>{esc(str(e)[:200])}</code>\n\n"
            "اشتراک در پنل سالم است — لینک را دستی بفرستید.")
        return True, result

    return True, result


def _notify_referrer_joined(ctx, referrer_id, tg_user):
    """
    به معرف می‌گوید یک نفر با لینکش آمد.

    عمداً می‌گوید سکه *بعد از خرید* می‌آید، نه همین حالا — وگرنه
    معرف منتظر سکه‌ای می‌ماند که نمی‌آید و فکر می‌کند سیستم خراب است.
    """
    # get_user_by_id یک sqlite3.Row می‌دهد، نه dict — و Row متد get
    # ندارد. اولین نسخه‌ی این تابع .get() صدا می‌زد، استثنا می‌گرفت،
    # و dispatch بی‌صدا قورتش می‌داد: معرف هیچ‌وقت پیامی نمی‌گرفت و
    # هیچ ردی هم در لاگ نبود.
    ref = ctx.db.get_user_by_id(referrer_id)
    if not ref or not ref["tg_id"]:
        return

    cs = core.coin_settings(ctx.s.get("coins"))
    amount = int(cs.get("per_referral") or 0)

    total = ctx.db.q(
        "SELECT COUNT(*) AS c FROM users WHERE tenant_id=? AND referred_by=?",
        (ctx.tid, referrer_id), one=True
    )
    n = (total or {}).get("c", 0)

    name = esc(tg_user.get("first_name") or "یک نفر")
    text = (
        f"🎉 <b>{name} با لینک شما آمد</b>\n\n"
        f"تا حالا <b>{core.fa(n)}</b> نفر را دعوت کرده‌اید.\n\n"
    )
    if amount > 0:
        text += ("<blockquote>به‌محض اینکه اولین خریدش را انجام دهد، "
                 f"<b>{core.fa(amount)} سکه</b> به شما می‌رسد.</blockquote>")
    else:
        text += "<blockquote>دعوتتان ثبت شد.</blockquote>"

    try:
        ctx.bot.send(ref["tg_id"], text,
                     keyboard=kb([[("🎁 دعوت دوستان", "ref")],
                                  [("‹ منوی اصلی", "menu")]]))
    except TelegramError:
        pass



def _release_coins(ctx, order_id):
    """
    سکه‌های رزروشده‌ی یک سفارش را برمی‌گرداند.

    رزرو فقط وقتی معنا دارد که راه برگشتی هم داشته باشد. بدون این،
    سفارشی که منقضی یا لغو شود سکه‌ها را برای همیشه نگه می‌دارد و
    مشتری بدون اینکه چیزی گرفته باشد، آن‌ها را از دست می‌دهد.

    دو بار برگرداندن ممکن نیست: تراکنش رزرو بعد از بازگشت به
    «released» تغییر نام می‌دهد، پس دفعه‌ی بعد پیدا نمی‌شود.
    """
    return ctx.db.release_coins(order_id)


def _reward_referrer(ctx, user, order_id):
    """سکه به معرف، فقط یک‌بار و فقط بعد از اولین خرید تاییدشده."""
    if not user.get("referred_by"):
        return

    cs = core.coin_settings(ctx.s.get("coins"))
    amount = int(cs.get("per_referral") or 0)
    if amount <= 0:
        return

    ref = ctx.db.get_user_by_id(user["referred_by"])
    if not ref:
        return

    # یک پاداش برای هر دوست — نه «برای اولین سفارش». شرط و پرداخت یک
    # دستورند، پس دو تایید هم‌زمان نه دو بار پاداش می‌دهند نه هیچ.
    if not ctx.db.reward_referral(
            ref["id"], user["id"], amount,
            f"خرید زیرمجموعه {user.get('first_name') or user['tg_id']}",
            order_id=order_id):
        return

    prog = core.coin_progress(ref["coins"] + amount, ctx.s.get("coins"))
    text = (
        f"🎉 <b>{core.fa(amount)} سکه گرفتید</b>\n\n"
        "یکی از دوستانی که دعوت کرده بودید خرید کرد.\n\n"
        f"موجودی شما: <b>{core.fa(prog['coins'])} سکه</b>"
    )
    if prog["current_percent"]:
        text += (f" — <b>{core.fa(prog['current_percent'])}٪ تخفیف</b> "
                 "آماده‌ی استفاده")
    if prog["next"]:
        text += (f"\n\n<i>با {core.fa(prog['next']['need'])} سکه‌ی دیگر به "
                 f"{core.fa(prog['next']['percent'])}٪ می‌رسید.</i>")

    try:
        ctx.bot.send(ref["tg_id"], text)
    except TelegramError:
        pass


def provision(ctx, order_id):
    """
    ساخت یا تمدید کانفیگ در 3x-ui — و ثبتِ شکست، هر شکلی که باشد.

    چرا یک پوسته و نه `record()` کنارِ هر `return False`:
        بدنه پنج راهِ شکست دارد (پلنِ پیدانشده، اینباندِ نبود،
        تمدیدِ هم‌زمان، خطای پنل، خطای غیرمنتظره) و راهِ ششم روزی
        اضافه می‌شود. اولین نسخه فقط دو `except` را ثبت می‌کرد و
        probe نشان داد پنلِ خاموش از راهِ «اینباند پیدا نشد» بیرون
        می‌رود — یعنی سفارش شکست می‌خورد و هیچ رویدادی ثبت نمی‌شد.

        این‌جا نقطه‌ی خروج یکی است، پس راهِ ششم هم خودبه‌خود ثبت
        می‌شود.
    """
    ok, res = _provision(ctx, order_id)
    if not ok:
        try:
            order = ctx.db.get_order(order_id) or {}
            user = (ctx.db.get_user_by_id(order["user_id"])
                    if order.get("user_id") else None) or {}
        except Exception:
            order, user = {}, {}
        record(ctx, "provision_failed", order.get("user_id"),
               {"order": order_id, "error": res},
               who=user.get("first_name") or user.get("tg_id"))
    return ok, res


def _provision(ctx, order_id):
    """بدنه — هیچ‌کس جز پوسته‌ی بالا صدایش نمی‌زند."""
    order = ctx.db.get_order(order_id)
    plan = ctx.db.get_plan(order["plan_id"]) if order.get("plan_id") else None
    if not plan:
        return False, "پلن این سفارش پیدا نشد"

    user = ctx.db.get_user_by_id(order["user_id"])
    t = DB.get_tenant(ctx.tid)

    # ── فروشگاهِ نماینده ───────────────────────────────────────────
    #
    # سه چیز برای نماینده فرق می‌کند، و هر سه تا امروز جا مانده بودند:
    #
    #   گروه    تنها چیزی که می‌گوید این کانفیگ مالِ کیست. بدونش کانفیگ
    #           در پنلِ مالک ساخته می‌شد و در صورتحسابِ هیچ‌کس نمی‌آمد
    #           — مالک کانفیگ را داده و پولش را از کسی نمی‌گیرد.
    #   پیشوند  نامِ ردیفِ نماینده فارسی است («حسین دهلگی») و `isalnum`
    #           حرفِ فارسی را نگه می‌دارد؛ یعنی شناسه‌ی کانفیگ و لینکِ
    #           اشتراک فارسی می‌شد. پرتال از اول `portal_slug` را
    #           می‌گذاشت و صفحه‌ی اشتراک برند را از همان تشخیص می‌دهد.
    #   اعتبار  نماینده‌ی پیش‌پرداخت نباید بیشتر از آنچه داده بفروشد.
    #
    # شکستِ هر کدام **پیش از** ساختِ کانفیگ است، نه بعدش.
    reseller = bool(t.get("parent_id"))
    trial = bool(plan.get("is_trial"))
    group = None
    if reseller and trial:
        # تستِ نماینده رایگان است و هزینه‌اش با مالک (تصمیمِ مالک):
        # بی‌گروه ساخته می‌شود تا در صورتحسابِ نماینده نیاید. سقف همین‌جا
        # هم سنجیده می‌شود، نه فقط موقعِ ذخیره — اگر مالک تستِ خودش را
        # کوچک کرده باشد، تستِ قدیمیِ نماینده دیگر ساخته نمی‌شود.
        okc, why = core.trial_within_cap(plan, DB.trial_cap())
        if not okc:
            return False, f"تستِ این فروشگاه ساخته نشد: {why}"
    elif reseller:
        group = str(t.get("portal_group") or "").strip()
        if not group:
            return False, ("این فروشگاه هنوز گروهِ x-ui ندارد. کانفیگِ "
                           "بی‌گروه در صورتحسابِ کسی شمرده نمی‌شود، پس "
                           "ساخته نشد — مالک باید گروه را تعیین کند")

    inbound = plan.get("inbound_id") or t.get("default_inbound")
    if not inbound and reseller:
        # همان ترتیبِ `_portal_inbound` در پرتال: انتخابِ خودش، بعد
        # پیش‌فرضِ مالک. بدونِ این، کانفیگی که نماینده از ربات می‌فروشد
        # روی اینباندی می‌نشست که از پرتالش نمی‌نشست.
        try:
            own = json.loads(t.get("inbound_ids") or "[]") \
                if (t.get("inbound_mode") or "all") == "custom" else []
        except (json.JSONDecodeError, TypeError):
            own = []
        if own:
            inbound = own[0]
        else:
            inbound = (DB.root_tenant() or {}).get("default_inbound")
    if not inbound:
        # اینباند پیش‌فرض تنظیم نشده.
        #
        # شکست کامل اینجا از دید مشتری یعنی «پول دادم و کانفیگ
        # نگرفتم» — آن هم فقط به‌خاطر یک تنظیم که مدیر جا انداخته.
        # به‌جایش اولین اینباند فعال پنل را برمی‌داریم؛ در حالت
        # پیش‌فرض (all) کلاینت به‌هرحال به همه‌ی اینباندهای فعال
        # وصل می‌شود، پس این انتخاب فقط نقطه‌ی شروع است.
        try:
            active = [i for i in (ctx.xui.inbounds() or [])
                      if i.get("enable", True)]
        except Exception as e:
            log.warning("خواندن اینباندها برای انتخاب خودکار ناموفق: %s", e)
            active = []

        if not active:
            return False, ("اینباند پیش‌فرض تنظیم نشده و هیچ اینباند فعالی "
                           "هم در پنل پیدا نشد")

        inbound = active[0].get("id")
        log.warning("اینباند پیش‌فرض تنظیم نشده — به‌طور خودکار از #%s "
                    "استفاده شد", inbound)

    if reseller:
        prefix = t.get("portal_slug") or "nx"
    else:
        prefix = ctx.s.get("email_prefix") or (t.get("name") or "nx")
    sub_base = ctx.s.get("sub_base_url")
    if not sub_base and reseller:
        # همان ترتیبِ `_sub_base` در پرتال: خودش، بعد مالک، بعد خودِ پنل
        # (که `create_subscription` وقتی خالی باشد می‌پرسد).
        try:
            sub_base = (json.loads((DB.root_tenant() or {}).get("settings")
                                   or "{}") or {}).get("sub_base_url")
        except (json.JSONDecodeError, TypeError):
            sub_base = None

    # کفِ این پلن برای نماینده‌ی پیش‌پرداخت. بکند موقعِ ذخیره‌ی پلن
    # حسابش کرده (`plans.cost`)؛ این‌جا فقط خوانده می‌شود.
    charge = 0
    if reseller and not trial and DB.is_prepaid(t):
        charge = max(0, int(plan.get("cost") or 0))
        if not charge:
            # کف معلوم نیست — فروش را نمی‌ایستانیم چون مشتری پول داده؛
            # صورتحسابِ گروه به‌هرحال این کانفیگ را می‌شمارد. ولی
            # بی‌صدا هم نه.
            log.warning("پلن %s نماینده %s کف ندارد — از اعتبار چیزی کم "
                        "نشد، صورتحسابِ گروه می‌شماردش", plan.get("id"), ctx.tid)

    try:
        # تمدید اشتراک موجود یا ساخت جدید
        if order["kind"] == "renew":
            # مقصد را از خود سفارش می‌خوانیم.
            #
            # قبلاً subs[0] گرفته می‌شد — تازه‌ترین اشتراک، نه آن‌که
            # مشتری برای تمدیدش پول داده بود. کسی که سه اشتراک داشت،
            # اشتباهی یکی دیگر را تمدیدشده می‌دید و همان که می‌خواست
            # منقضی می‌شد.
            sub = None
            target = order.get("renew_sub_id")
            if target:
                sub = ctx.db.q(
                    "SELECT * FROM subscriptions WHERE tenant_id=? AND id=? "
                    "AND user_id=?", (ctx.tid, int(target), user["id"]), one=True)
            if not sub:
                subs = ctx.db.user_subs(user["id"])
                sub = subs[0] if subs else None
            if sub:
                # قفل کوتاه روی همین اشتراک.
                #
                # تاریخ تازه از تاریخ فعلی ساخته می‌شود، پس دو تمدید
                # هم‌زمان هر دو یک مبدأ می‌خوانند و هر دو همان یک ماه
                # را می‌نویسند — دو پرداخت، یک ماه. صداکننده با خطای
                # ما پول را برمی‌گرداند.
                if not ctx.db.claim_renewal(sub["id"]):
                    return False, "این اشتراک همین حالا در حال تمدید است"
                if charge:
                    okc, have = DB.charge_credit(
                        ctx.tid, charge, f"تمدید {sub.get('client_email')}")
                    if not okc:
                        ctx.db.release_renewal(sub["id"])
                        return False, (f"اعتبارِ فروشگاه کافی نیست — لازم "
                                       f"{charge:,}، موجودی {have:,} تومان")
                try:
                    # ایمیل را هم می‌دهیم: در 3x-ui نسخه‌ی ۳ شناسه‌ی
                    # اصلی کلاینت ایمیل است و جست‌وجو با آن مطمئن‌تر
                    # از uuid است
                    try:
                        ext = ctx.xui.extend_subscription(
                            sub["inbound_id"], sub["client_uuid"],
                            plan["days"], plan["gb"],
                            email=sub.get("client_email"))
                    except Exception:
                        if charge:
                            DB.refund_credit(
                                ctx.tid, charge,
                                "بازگشت — تمدید روی پنل انجام نشد")
                        raise
                    new_exp = _add_days_iso(sub["expires_at"], plan["days"])

                    # حجم را از همان چیزی می‌گیریم که روی پنل نشست.
                    #
                    # تمدید حجم را جمع می‌کند و شمارنده‌ی مصرف را صفر
                    # نمی‌کند. ربات ولی همان اندازه‌ی پلن را نگه
                    # می‌داشت، پس بعد از اولین تمدید مصرفِ تجمعی با
                    # سقفِ یک دوره سنجیده می‌شد: مشتری که ۴۵ از ۱۰۰
                    # گیگ خرج کرده بود «۹۰٪» می‌دید و هشدار اتمام حجم
                    # می‌گرفت، همان روز اولِ دوره‌ی تازه.
                    new_gb = sub.get("gb") or 0
                    if isinstance(ext, dict) and ext.get("total_bytes") is not None:
                        new_gb = int(round(ext["total_bytes"] / (1024 ** 3)))
                    ctx.db.exec(
                        """UPDATE subscriptions SET expires_at=?, gb=?,
                           is_active=1,
                           notified_7d=0, notified_3d=0, notified_1d=0,
                           notified_80p=0
                           WHERE tenant_id=? AND id=?""",
                        (new_exp, new_gb, ctx.tid, sub["id"])
                    )
                    ctx.db.exec(
                        "UPDATE orders SET sub_id=? WHERE tenant_id=? AND id=?",
                        (sub["id"], ctx.tid, order_id))
                finally:
                    ctx.db.release_renewal(sub["id"])
                return True, {**sub, "expires_at": new_exp, "gb": new_gb,
                              "renewed": True}

        email = _free_email(ctx, user, prefix)

        # اینباندهایی که کانفیگ روی آن‌ها ساخته می‌شود.
        #
        # اولویت: تنظیم پلن، بعد تنظیم سراسری. حالت all یعنی همه‌ی
        # اینباندهای فعال، که تصمیمش با خود کلاینت xui است.
        pl_inbounds = None
        t = ctx.tenant
        mode = t.get("inbound_mode") or "all"

        raw = plan.get("inbound_ids")
        if not raw and mode == "custom":
            raw = t.get("inbound_ids")
        elif not raw and mode == "default":
            raw = json.dumps([inbound]) if inbound else None

        if raw:
            try:
                pl_inbounds = json.loads(raw) if isinstance(raw, str) else raw
            except (json.JSONDecodeError, TypeError):
                pl_inbounds = [x.strip() for x in str(raw).split(",") if x.strip()]

        # یادداشت شناسه‌ی کانفیگ را دارد: `_portal_charge_for` موقعِ
        # حذف، برگشتی را از روی همین متن پیدا می‌کند.
        if charge:
            okc, have = DB.charge_credit(ctx.tid, charge, f"ساخت {email}")
            if not okc:
                return False, (f"اعتبارِ فروشگاه کافی نیست — لازم "
                               f"{charge:,}، موجودی {have:,} تومان")
        # گروه فقط برای نماینده فرستاده می‌شود؛ مسیرِ مالک همان است که بود.
        extra = {"group": group} if group else {}
        try:
            res = ctx.xui.create_subscription(
                inbound, email, plan["gb"], plan["days"],
                ip_limit=plan["ip_limit"], tg_id=user["tg_id"],
                sub_base_url=sub_base, inbound_ids=pl_inbounds, **extra,
            )
        except Exception:
            if charge:
                DB.refund_credit(ctx.tid, charge,
                                 "بازگشت — کار روی پنل انجام نشد")
            raise

        exp_iso = None
        if res["expiry_ms"]:
            exp_iso = datetime.fromtimestamp(res["expiry_ms"] / 1000).isoformat(timespec="seconds")

        sid = ctx.db.exec(
            """INSERT INTO subscriptions (tenant_id, user_id, order_id, plan_id,
                                          plan_name, client_email, client_uuid,
                                          sub_url, inbound_id, gb, expires_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            # نام پلن همین‌جا ثبت می‌شود، نه فقط شناسه‌اش. اگر مدیر
            # بعداً پلن را حذف یا عوض کند، مشتری همچنان نام چیزی را
            # می‌بیند که واقعاً خریده.
            (ctx.tid, user["id"], order_id, plan["id"], plan["name"], email,
             res["uuid"], res["sub_url"], inbound, plan["gb"], exp_iso)
        )
        ctx.db.exec("UPDATE orders SET sub_id=? WHERE tenant_id=? AND id=?",
                    (sid, ctx.tid, order_id))
        ctx.db.log("provision", user["id"], {"order": order_id, "sub": sid})

        return True, {"id": sid, "client_email": email, "sub_url": res["sub_url"],
                      "expires_at": exp_iso, "gb": plan["gb"],
                      "plan_name": plan["name"], "renewed": False,
                      # اگر لینک اشتراک ساخته نشد، دست‌کم خود کانفیگ‌ها
                      # را داریم تا مشتری دست‌خالی نماند
                      "configs": res.get("configs") or []}

    except XUIError as e:
        log.error("خطای ساخت کانفیگ: %s", e)
        return False, f"خطای پنل: {e}"
    except Exception as e:
        log.exception("خطای غیرمنتظره در provision")
        return False, f"خطای غیرمنتظره: {e}"


def _add_days_iso(iso, days):
    from datetime import timedelta
    base = datetime.now()
    if iso:
        try:
            cur = datetime.fromisoformat(iso)
            if cur > base:
                base = cur
        except ValueError:
            pass
    return (base + timedelta(days=days)).isoformat(timespec="seconds")


def _deliver_kb(ctx, url):
    """
    دکمه‌های پیام تحویل.

    دکمه‌ی «افزودن یک‌کلیک» با اسکیم اپلیکیشن (happ:// و امثالش)
    این‌جا ساخته نمی‌شود: تلگرام آن را نمی‌پذیرد و کل پیام را رد
    می‌کند. یک‌کلیک از روی صفحه‌ی اشتراک انجام می‌شود که با https
    باز می‌شود؛ اگر آدرس اشتراک http(s) باشد، همان را دکمه می‌کنیم.
    """
    rows = []
    if url:
        # دکمه‌ی کپی تلگرام — کاربر لازم نیست متن را دستی انتخاب کند
        rows.append([("📋 کپی لینک اشتراک", url, "copy")])
    if valid_button_url(url):
        rows.append([("📄 صفحه‌ی اشتراک من", url, "url")])
    rows.append([("📚 آموزش نصب", "help"), ("📊 اشتراک‌های من", "mysubs")])
    rows.append([("‹ منوی اصلی", "menu")])
    return kb(rows)


def deliver(ctx, user, sub):
    """ارسال کانفیگ به مشتری با دکمه‌های افزودن یک‌کلیک."""
    url = sub.get("sub_url")
    title = "تمدید شد" if sub.get("renewed") else "آماده است"

    # متن سفارشی ادمین، اگر تنظیم شده باشد
    tpl = ctx.s.get("delivered_text")
    if tpl:
        d0 = core.days_left(sub.get("expires_at"))
        custom = (tpl.replace("{plan}", esc(str(sub.get("plan_name") or "")))
                     .replace("{sub_url}", esc(url or ""))
                     .replace("{gb}", core.fmt_gb(sub.get("gb")))
                     .replace("{expires}", str(d0) if d0 is not None else "—"))
        _chat_copy(ctx, user, custom, sub)
        return ctx.bot.send(user["tg_id"], custom, keyboard=_deliver_kb(ctx, url))

    d = core.days_left(sub.get("expires_at"))

    lines = [
        # نام ثبت‌شده‌ی اشتراک زیر عنوان می‌آید: اگر مشتری چند اشتراک
        # داشته باشد باید همین‌جا بفهمد این کدام است.
        F.header(f"اشتراک شما {title}", "✅", F.b(ctx.sub_label(sub))),
        "",
        F.section("مشخصات", "📊"),
        F.row("حجم", core.fmt_gb(sub.get("gb")), "💾"),
    ]
    if d is not None:
        val = f"{core.fa(d)} روز"
        if sub.get("expires_at"):
            val += f" — تا {core.fa_date(sub['expires_at'])}"
        lines.append(F.row("اعتبار", val, "⏳"))
    if sub.get("client_email"):
        lines += ["", F.section("شناسه‌ی کانفیگ", "🏷"),
                  F.code(sub["client_email"])]

    if url:
        lines += [
            "",
            F.section("لینک اشتراک شما", "🔑"),
            F.code(url),
            "",
            F.quote_more(
                F.b("چطور وصل شوم؟"),
                "",
                "۱. دکمه‌ی «کپی لینک» پایین را بزنید.",
                "۲. برنامه‌ی VPN را باز کنید.",
                "۳. گزینه‌ی افزودن از کلیپ‌بورد را بزنید.",
                "۴. سرور را انتخاب کنید و وصل شوید.",
                "",
                "اگر برنامه ندارید، «آموزش نصب» لینک دانلود همه را دارد.",
            ),
        ]
    elif sub.get("configs"):
        # لینک اشتراک نداریم ولی خود کانفیگ‌ها را داریم — همان‌ها را
        # می‌دهیم تا مشتری دست‌خالی نماند و لازم نباشد پشتیبانی
        # را برای چیزی که در دسترس است درگیر کند.
        lines += ["", "🔗 <b>کانفیگ‌های شما</b>"]
        for cfg in sub["configs"][:5]:
            lines.append(f"<code>{esc(cfg)}</code>")
        lines.append("")
        lines.append("<i>هر کدام را که خواستید کپی کنید و در برنامه‌تان "
                     "وارد کنید — همه به یک حساب وصل‌اند.</i>")
    else:
        # بدون لینک، کاربر نمی‌داند چه کند — پس صریح می‌گوییم
        lines += [
            "",
            "⚠️ لینک اشتراک ساخته نشد، ولی <b>خریدتان ثبت شده است</b>.\n"
            "به پشتیبانی پیام بدهید تا همین حالا دستی برایتان بفرستیم.",
        ]

    lines += ["", "<blockquote>هر وقت خواستید، از «اشتراک‌های من» مصرف و "
              "روزهای باقی‌مانده را ببینید.</blockquote>"]

    text = "\n".join(lines)
    _chat_copy(ctx, user, text, sub)
    _send_delivery(ctx, user, text, url)


def _chat_copy(ctx, user, html, sub):
    """
    همان پیامِ تحویل، در صندوقِ مینی‌اپ.

    چرا کپیِ همان متن و نه متنی جدا:
        دو متنِ جدا یعنی روزی یکی‌شان اصلاح می‌شود و دیگری نه — و
        آن‌که فراموش می‌شود همانی است که مشتری می‌خواند. متنِ
        تلگرام از `F.*` ساخته شده، پس فقط تگ‌هایش برداشته می‌شود.

    چرا اصلاً لازم است:
        مشتری بعد از خرید مینی‌اپ را باز می‌کند، نه چتِ ربات را. و
        مشتری‌ای که ربات را بلاک کرده یا نوتیفیکیشن را بسته، پیامِ
        تلگرام را اصلاً نمی‌بیند — ولی پولش را داده.

    **هرگز تحویل را نمی‌شکند.** از داخلِ مسیرِ پول صدا زده می‌شود و
    یک خطای فرعی نباید جای کانفیگِ ساخته‌شده را بگیرد.
    """
    try:
        body = F.plain(html).strip()
        if not body:
            return
        ctx.db.chat_add(user["id"], "system", body,
                        order_id=(sub or {}).get("order_id"))
    except Exception:
        log.debug("کپیِ تحویل در صندوق ناموفق", exc_info=True)


def _chat_notice(ctx, srow, html):
    """
    یادآوری‌ها در صندوقِ مینی‌اپ.

    چرا: مشتری‌ای که ربات را بلاک کرده یا نوتیفیکیشن را بسته، هیچ
    یادآوری‌ای نمی‌بیند و اولین خبری که می‌گیرد قطع‌شدنِ اتصال است.
    صندوق همیشه هست.

    **همان متنِ تلگرام**، فقط بدونِ تگ — دو متنِ جدا یعنی روزی
    یکی‌شان اصلاح می‌شود و دیگری نه.

    `user_id` روی ردیفِ اشتراک هست؛ اگر نبود بی‌صدا رد می‌شویم، چون
    پیامِ بی‌صاحب در صندوقِ کسِ دیگری می‌نشیند.
    """
    try:
        uid = (srow or {}).get("user_id")
        if not uid:
            return
        body = F.plain(html).strip()
        if body:
            ctx.db.chat_add(uid, "system", body)
    except Exception:
        log.debug("یادآوری در صندوق ثبت نشد", exc_info=True)


def _send_delivery(ctx, user, text, url):
    """
    ارسال پیام تحویل با تضمین رسیدن.

    اگر تلگرام صفحه‌کلید را رد کند (مثلاً یک دکمه‌ی url نامعتبر)،
    کل پیام رد می‌شود و مشتری کانفیگش را نمی‌گیرد — در حالی که پول
    داده و کانفیگ در پنل ساخته شده. پس اگر ارسال با دکمه شکست خورد،
    بدون دکمه دوباره می‌فرستیم. متن مهم است، دکمه تزئین.
    """
    try:
        sent = ctx.bot.send(user["tg_id"], text,
                            keyboard=_deliver_kb(ctx, url))
    except TelegramError as e:
        log.warning("ارسال تحویل با صفحه‌کلید ناموفق (%s) — بدون دکمه "
                    "دوباره تلاش می‌شود", e)
        sent = ctx.bot.send(user["tg_id"], text)

    # کیوآر لینک — روی گوشی خیلی راحت‌تر از کپی‌کردن یک لینک بلند است،
    # مخصوصاً وقتی مشتری روی همان گوشی هم تلگرام دارد هم اپ VPN.
    # اگر ساخته نشد، تحویل که رسیده است؛ این فقط اضافه است.
    if url:
        try:
            png = qr.make(url)
            if png:
                ctx.bot.send_photo_bytes(
                    user["tg_id"], png, filename="nexora-sub.png",
                    caption="📷 <b>کیوآر همین لینک</b>\n\n"
                            "<blockquote>در اپ VPN گزینه‌ی افزودن با اسکن را "
                            "بزنید و این را نشان دوربین بدهید — نیازی به کپی "
                            "کردن لینک نیست.</blockquote>")
        except Exception as e:
            log.warning("ارسال کیوآر ناموفق: %s", e)

    return sent


# ═══════════════════════════════════════════════════════════
#  بخش‌های منو
# ═══════════════════════════════════════════════════════════

def show_subs(ctx, user, chat_id, message_id):
    subs = ctx.db.user_subs(user["id"])
    if not subs:
        return _reply(ctx, chat_id, message_id,
                      "📊 <b>اشتراک‌های شما</b>\n\n"
                      "هنوز اشتراکی اینجا نیست.\n\n"
                      "اولین اشتراکتان کمتر از یک دقیقه طول می‌کشد — "
                      "پلن را انتخاب می‌کنید، رسید می‌فرستید، تحویل می‌گیرید.",
                      kb([[("🛒 خرید اشتراک", "buy")], [("‹ بازگشت", "menu")]]))

    lines = ["📊 <b>اشتراک‌های شما</b>", ""]
    rows = []

    # مصرف واقعی از پنل — بدون این، کاربر نمی‌داند چقدر مانده و
    # وقتی حجمش تمام شود فکر می‌کند سرویس خراب است
    client = None
    try:
        client = ctx.xui
    except Exception:
        pass

    for s in subs:
        d = core.days_left(s.get("expires_at"))
        expired = d is not None and d <= 0

        used_gb = None
        if client and s.get("client_email"):
            try:
                t = client.client_traffic(s["client_email"])
                if t:
                    up = int(t.get("up") or 0)
                    down = int(t.get("down") or 0)
                    used_gb = round((up + down) / (1024 ** 3), 1)
            except Exception:
                pass

        total_gb = s.get("gb") or 0
        pct = None
        if total_gb and used_gb is not None:
            pct = min(100, round(used_gb * 100 / total_gb))

        if expired:
            status = "🔴"
        elif pct is not None and pct >= 90:
            status = "🟠"
        elif d is not None and d <= 3:
            status = "🟡"
        else:
            status = "🟢"

        # نام اشتراک = پلن + سرور. بدون نام سرور، سه اشتراک هم‌پلن
        # سه خط کاملاً یکسان می‌شوند و مشتری گم می‌شود.
        lines.append(f"{status} {F.b(ctx.sub_label(s))}")

        # نوار مصرف — سریع‌ترین راه فهمیدن وضعیت
        if pct is not None:
            filled = round(pct / 10)
            bar = "█" * filled + "░" * (10 - filled)
            left_gb = max(0, round(total_gb - used_gb, 1))
            lines.append(f"{F.code(bar)} {core.fa(pct)}٪")
            lines.append(f"💾 {F.b(f'{core.fa(left_gb)} گیگ')} باقی مانده "
                         f"{F.i(f'({core.fa(used_gb)} از {core.fmt_gb(total_gb)} مصرف شده)')}")
        elif used_gb is not None:
            lines.append(f"💾 {F.b(f'{core.fa(used_gb)} گیگ')} مصرف شده — حجم نامحدود")
        else:
            lines.append(f"💾 {core.fmt_gb(total_gb)} ترافیک")

        if d is None:
            lines.append("⏳ بدون محدودیت زمانی")
        elif expired:
            gone = core.days_past(s.get("expires_at"))
            lines.append(
                f"⛔ {F.b('امروز')} منقضی شد" if gone < 1 else
                f"⛔ {F.b(f'{core.fa(gone)} روز پیش')} منقضی شده")
        else:
            line = f"⏳ {F.b(f'{core.fa(d)} روز')} اعتبار"
            if s.get("expires_at"):
                line += f" — تا {core.fa_date(s['expires_at'])}"
            lines.append(line)

        if s.get("client_email"):
            lines.append(f"🏷 {F.code(s['client_email'])}")

        if s.get("sub_url"):
            lines.append(f"🔗 {F.code(s['sub_url'])}")

        lines.append("")

        # دکمه هم باید بگوید کدام اشتراک را تمدید می‌کند. «تمدید» تنها،
        # وقتی سه تا از آن زیر هم باشد، یعنی مشتری شانسی می‌زند.
        label = "🔄 تمدید" if not expired else "⚡ تمدید فوری"
        rows.append([(f"{label} · {ctx.sub_label(s)}", f"renew:{s['id']}")])

    lines.append(F.quote(
        "لینک را بزنید تا کپی شود، بعد در برنامه‌تان وارد کنید.",
        "اگر بلد نیستید، «آموزش نصب» را بزنید."))
    rows.append([("📚 آموزش نصب", "help")])

    rows.append([("‹ بازگشت", "menu")])
    _reply(ctx, chat_id, message_id, "\n".join(lines), kb(rows))


def show_renew(ctx, user, chat_id, message_id, sub_id):
    """
    تمدید یک اشتراک مشخص.

    نام پلن همه‌جا می‌آید: کسی که سه اشتراک دارد باید بداند دارد
    کدامش را تمدید می‌کند، وگرنه پول می‌دهد و اشتباه تمدید می‌شود.
    """
    sub = ctx.db.q(
        "SELECT * FROM subscriptions WHERE tenant_id=? AND id=? AND user_id=?",
        (ctx.tid, sub_id, user["id"]), one=True
    )
    if not sub:
        return _reply(ctx, chat_id, message_id,
                      "این اشتراک پیدا نشد.", back_kb("mysubs"))

    plan = ctx.db.get_plan(sub["plan_id"]) if sub.get("plan_id") else None
    left = core.days_left(sub.get("expires_at"))

    # تیتر خودش می‌گوید کدام اشتراک — نه «تمدید اشتراک» خشک و خالی.
    # نام پلن را صریح می‌دهیم چون این ردیف از SELECT خام آمده.
    label = ctx.sub_label(sub, plan_name=(plan or {}).get("name")
                          if plan else sub.get("plan_name"))
    lines = [F.header("تمدید اشتراک", "🔄", F.b(label)), ""]
    lines.append(F.section("وضعیت فعلی", "📊"))

    if plan:
        lines.append(F.row("پلن", core.fmt_gb(plan["gb"]) + " · "
                           + core.fmt_days(plan["days"]), "📦"))

    if left is None:
        lines.append(F.row("اعتبار", "بدون محدودیت زمانی", "⏳"))
    elif left <= 0:
        lines.append(F.row("اعتبار", "تمام شده", "⛔"))
    else:
        lines.append(F.row("باقی‌مانده", f"{core.fa(left)} روز", "⏳"))

    if sub.get("client_email"):
        lines += ["", F.section("شناسه‌ی کانفیگ", "🏷"),
                  F.code(sub["client_email"])]

    rows = []
    if plan:
        lines += ["", F.hr(),
                  F.row("مبلغ تمدید",
                        core.toman(plan["price"]) + " تومان", "💰"), ""]
        lines.append(F.quote(
            "بعد از تمدید، همین کانفیگ ادامه پیدا می‌کند — لازم نیست "
            "چیزی را در برنامه‌تان عوض کنید."))
        if user["balance"] >= plan["price"]:
            rows.append([("👛 تمدید آنی از کیف پول",
                          f"wpay:{plan['id']}:{sub['id']}")])
        rows.append([(f"💳 تمدید — {core.toman(plan['price'])} تومان",
                      f"chk:{plan['id']}:0:{sub['id']}")])
    else:
        lines += ["", "پلن این اشتراک دیگر موجود نیست — از فهرست پلن‌ها "
                  "یکی انتخاب کنید."]
        rows.append([("🛒 دیدن پلن‌ها", "buy")])

    rows.append([("‹ اشتراک‌های من", "mysubs")])
    return _reply(ctx, chat_id, message_id, "\n".join(lines), kb(rows))


def show_wallet(ctx, user, chat_id, message_id):
    u = ctx.db.get_user(user["tg_id"])
    txs = ctx.db.q(
        "SELECT * FROM wallet_tx WHERE tenant_id=? AND user_id=? ORDER BY id DESC LIMIT 5",
        (ctx.tid, u["id"])
    )
    lines = [
        "👛 <b>کیف پول</b>",
        "",
        f"💰 موجودی: <b>{core.toman(u['balance'])}</b> تومان",
    ]
    if txs:
        lines += ["", "📄 <b>آخرین تراکنش‌ها</b>"]
        for t in txs:
            sign = "+" if t["amount"] > 0 else "−"
            lines.append(f"{sign} {core.toman(abs(t['amount']))} · "
                         f"{esc(t.get('note') or t['kind'])}")

    lines += ["", "<i>با کیف پول شارژشده، خرید بعدی‌تان بدون انتظارِ تأیید "
              "رسید انجام می‌شود و تمدید خودکار هم فعال می‌ماند.</i>"]

    return _reply(ctx, chat_id, message_id, "\n".join(lines),
                  kb([[("💳 شارژ کیف پول", "topup")],
                      [("‹ منو", "menu")]]))


def wallet_topup(ctx, user, chat_id, message_id):
    """
    انتخاب مبلغ شارژ.

    همان جریان کارت‌به‌کارت خرید است — مبلغ انتخاب می‌شود، رسید
    می‌آید، شما تایید می‌کنید و موجودی اضافه می‌شود.
    """
    # کارت‌ها در تنظیمات مستاجر ذخیره می‌شوند، نه در جدول.
    #
    # این‌جا از جدولی به نام cards می‌خواند که هیچ‌وقت ساخته نشده —
    # پس هر بار که مشتری «شارژ کیف پول» را می‌زد، یک
    # OperationalError بالا می‌رفت و هیچ پاسخی نمی‌گرفت. مسیر خرید
    # از همان اول درست بود (core.pick_card روی ctx.s) و فقط شارژ
    # کیف پول جا مانده بود.
    cards = [c for c in (ctx.s.get("cards") or [])
             if isinstance(c, dict) and c.get("number")
             and c.get("active", True)]
    if not cards:
        return _reply(ctx, chat_id, message_id,
                      "شارژ کیف پول فعلاً در دسترس نیست.", back_kb("wallet"))

    amounts = [100000, 200000, 500000, 1000000]
    rows = [[(f"{core.toman(a)} تومان", f"topup:{a}")] for a in amounts]
    rows.append([("‹ بازگشت", "wallet")])

    return _reply(ctx, chat_id, message_id,
                  "💳 <b>شارژ کیف پول</b>\n\n"
                  "مبلغ را انتخاب کنید. بعد از واریز و فرستادن رسید، "
                  "موجودی‌تان اضافه می‌شود و خریدهای بعدی <b>بدون انتظار</b> "
                  "انجام می‌شوند.",
                  kb(rows))


#: کمینه و بیشینه‌ی شارژ — یک جا، چون هم ربات می‌سنجدش هم مینی‌اپ
TOPUP_MIN = 10_000
TOPUP_MAX = 50_000_000


def topup_order(ctx, user, amount):
    """
    هسته‌ی شارژ کیف پول: سفارشِ `topup` بساز و کارت را برگردان.

    چرا هسته شد: مینی‌اپ هم باید همین کار را بکند، و اگر آن‌جا
    دوباره نوشته شود می‌شود مسیرِ دومی که یک روز یکی از قاعده‌ها را
    فراموش می‌کند — دقیقاً همان چیزی که سه مسیرِ خرید سرش اتفاق
    افتاد.

    برمی‌گرداند `(order, card)`؛ روی ورودیِ بد `ValueError` با متنی
    که مستقیم قابل نشان‌دادن است.
    """
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        raise ValueError("این مبلغ خوانده نشد")

    if not (TOPUP_MIN <= amount <= TOPUP_MAX):
        raise ValueError("مبلغ باید بین ۱۰ هزار تا ۵۰ میلیون تومان باشد")

    u = ctx.db.get_user(user["tg_id"]) if user.get("tg_id") else user
    card = core.pick_card(ctx.s.get("cards"))
    if not card:
        raise ValueError("هنوز شماره کارتی ثبت نشده")

    # plan_id خالی یعنی این سفارش شارژ است نه خرید پلن
    order = ctx.db.create_order(u["id"], None, amount, amount, kind="topup")
    ctx.db.set_state(u["id"], "await_receipt", {"order_id": order["id"]})
    return order, card


def wallet_topup_amount(ctx, user, chat_id, message_id, amount):
    """پوسته‌ی تلگرامیِ `topup_order` — منطقش این‌جا نیست."""
    try:
        order, card = topup_order(ctx, user, amount)
    except ValueError as e:
        msg = str(e)
        if "کارتی" in msg:
            msg += ("\n\n<blockquote>از پنل، بخش «اتصال و تنظیمات»، کارت را "
                    "اضافه کنید.</blockquote>")
        return _reply(ctx, chat_id, message_id, msg, back_kb("wallet"))

    amount = int(order["amount"])

    return _reply(ctx, chat_id, message_id,
                  f"💳 <b>شارژ کیف پول</b>\n\n"
                  f"مبلغ: <b>{core.toman(amount)}</b> تومان\n\n"
                  f"این مبلغ را به کارت زیر واریز کنید:\n"
                  f"<code>{core.fmt_card(card['number'])}</code>\n"
                  f"به نام <b>{esc(card['holder'])}</b>\n\n"
                  f"بعد <b>عکس رسید</b> یا <b>متن پیامک بانک</b> را همین‌جا "
                  f"بفرستید تا موجودی‌تان اضافه شود.",
                  kb([[("📋 کپی شماره کارت",
                        "".join(c for c in str(card["number"]) if c.isdigit()),
                        "copy")],
                      [("📋 کپی مبلغ", str(amount), "copy")],
                      [("‹ انصراف", "wallet")]]))


def show_coins(ctx, user, chat_id, message_id):
    u = ctx.db.get_user(user["tg_id"])
    cs = core.coin_settings(ctx.s.get("coins"))
    prog = core.coin_progress(u["coins"], ctx.s.get("coins"))

    lines = [
        "🪙 <b>سکه‌های شما</b>",
        "",
        f"موجودی: <b>{core.fa(prog['coins'])} سکه</b>",
    ]
    if prog["current_percent"]:
        lines.append(f"همین حالا <b>{core.fa(prog['current_percent'])}٪ تخفیف</b> "
                     f"دارید <i>(با خرج {core.fa(prog['current_cost'])} سکه)</i>")
    if prog["next"]:
        lines.append(f"با <b>{core.fa(prog['next']['need'])} سکه</b> دیگر، "
                     f"تخفیف {core.fa(prog['next']['percent'])}٪ باز می‌شود")

    lines += ["", "<b>پله‌های تخفیف</b>"]
    for t in cs["tiers"]:
        mark = "✅" if u["coins"] >= t["coins"] else "▫️"
        lines.append(f"{mark} {core.fa(t['coins'])} سکه — "
                     f"{core.fa(t['percent'])}٪ تخفیف")

    lines += [
        "",
        f"هر دوستی که با لینک شما بیاید و <b>خرید کند</b>، "
        f"<b>{core.fa(cs['per_referral'])} سکه</b> به شما می‌رسد.",
        "",
        "<i>سکه‌ها تاریخ انقضا ندارند — می‌توانید جمعشان کنید تا "
        "به پله‌ی بالاتر برسید.</i>"
        if not cs.get("expire_days") else "",
    ]

    # فاصله‌های خالی عمدی‌اند (گروه‌بندی بصری) — فقط خط آخر که ممکن
    # است شرطی خالی بماند حذف می‌شود، نه همه‌ی خالی‌ها
    while lines and lines[-1] == "":
        lines.pop()

    _reply(ctx, chat_id, message_id, "\n".join(lines),
           kb([[("🎁 دعوت دوستان", "ref")], [("‹ بازگشت", "menu")]]))


def show_referral(ctx, user, chat_id, message_id):
    u = ctx.db.get_user(user["tg_id"])
    cs = core.coin_settings(ctx.s.get("coins"))
    t = DB.get_tenant(ctx.tid)
    bot_user = t.get("bot_username") or ""
    link = f"https://t.me/{bot_user}?start={u['ref_code']}" if bot_user else ""

    invited = ctx.db.q(
        "SELECT COUNT(*) AS c FROM users WHERE tenant_id=? AND referred_by=?",
        (ctx.tid, u["id"]), one=True
    )
    bought = ctx.db.q(
        """SELECT COUNT(DISTINCT o.user_id) AS c FROM orders o
           JOIN users us ON us.id = o.user_id
           WHERE o.tenant_id=? AND us.referred_by=? AND o.status='approved'""",
        (ctx.tid, u["id"]), one=True
    )

    lines = [
        "🎁 <b>دعوت دوستان</b>",
        "",
        f"هر دوستی که با لینک شما بیاید و خرید کند، "
        f"<b>{core.fa(cs['per_referral'])} سکه</b> به شما می‌رسد — "
        "و سکه یعنی تخفیف روی خرید بعدی‌تان.",
        "",
    ]
    if link:
        lines += [
            F.title("لینک اختصاصی شما", "🔗"),
            F.code(link),
        ]
    else:
        lines += [
            F.title("کد دعوت شما", "🔗"),
            F.code(u["ref_code"]),
            F.i("دوستتان بعد از /start این کد را بفرستد."),
        ]

    n_inv = (invited or {}).get("c", 0)
    n_buy = (bought or {}).get("c", 0)
    lines += [
        "",
        F.row("دعوت‌شده", f"{core.fa(n_inv)} نفر", "👥"),
        F.row("از این‌ها خرید کرده", f"{core.fa(n_buy)} نفر", "🛒"),
        F.row("سکه‌ی شما", core.fa(u["coins"]), "🪙"),
    ]

    # اگر هنوز کسی را نیاورده، مقدار جایزه را به‌شکل کنجکاوی‌برانگیز
    # نشان می‌دهیم — اسپویلر همان کاری را می‌کند که در تلگرام جواب
    # می‌دهد: کاربر برای دیدنش می‌زند، و همان زدن یعنی توجه.
    if not n_inv:
        nxt = core.next_tier(u["coins"], ctx.s.get("coins"))
        if nxt:
            lines += ["", "🎯 با " + F.spoiler(
                f"{core.fa(nxt['need'])} سکه‌ی دیگر، {core.fa(nxt['percent'])}٪ "
                "تخفیف") + " باز می‌شود."]

    rows = []
    # بدون یوزرنیم ربات لینکی وجود ندارد و دکمه‌ی اشتراک‌گذاری
    # به یک آدرس شکسته می‌رسید
    if link:
        share = (f"https://t.me/share/url?url={link}"
                 "&text=با این لینک ثبت‌نام کن و اینترنت پرسرعت بگیر")
        rows.append([("📤 ارسال به دوستان", share, "url")])
        # کپی مستقیم لینک — همه دوست ندارند از پنجره‌ی اشتراک‌گذاری
        # تلگرام برود؛ بعضی می‌خواهند لینک را جای دیگری بفرستند
        rows.append([("📋 کپی لینک دعوت", link, "copy")])
    rows.append([("🪙 سکه‌های من", "coins")])
    rows.append([("‹ بازگشت", "menu")])

    _reply(ctx, chat_id, message_id, "\n".join(lines), kb(rows))


def show_help(ctx, user, chat_id, message_id):
    # جزئیاتِ هر قدم داخل نقل‌قول جمع‌شونده می‌رود: کسی که بلد است سه
    # خط می‌بیند و رد می‌شود، کسی که نیست بازش می‌کند و کامل می‌خواند.
    txt = ctx.s.get("help_text") or F.join(
        F.title("آموزش نصب", "📚"),
        F.lines(
            "سه قدم، کمتر از دو دقیقه:",
            "",
            f"{F.b('۱.')} برنامه‌ی مناسب دستگاهتان را از دکمه‌های پایین نصب کنید",
            f"{F.b('۲.')} به «اشتراک‌های من» بروید و لینک اشتراک را کپی کنید",
            f"{F.b('۳.')} در برنامه، گزینه‌ی افزودن از لینک را بزنید و بچسبانید",
        ),
        F.quote_more(
            F.b("جزئیات هر قدم"),
            "",
            F.b("اندروید") + " — برنامه‌ی v2rayNG یا Happ را نصب کنید. بالا "
            "سمت راست علامت + را بزنید و «Import from clipboard» را انتخاب کنید.",
            "",
            F.b("آیفون") + " — برنامه‌ی Streisand یا Happ. روی + بزنید و "
            "«افزودن از کلیپ‌بورد» را انتخاب کنید.",
            "",
            F.b("ویندوز") + " — برنامه‌ی v2rayN. از منوی Servers گزینه‌ی "
            "«Import from clipboard» را بزنید.",
            "",
            "بعد از افزودن، سرور را انتخاب و دکمه‌ی اتصال را بزنید. اگر "
            "وصل نشد، یک سرور دیگر از همان لیست را امتحان کنید.",
        ),
        F.quote("اگر جایی گیر کردید، از پشتیبانی بپرسید. "
                "خجالت ندارد، همه اولین بار همین‌طورند."),
    )
    rows = []
    apps = ctx.s.get("apps") or []
    for a in apps[:6]:
        if a.get("url"):
            rows.append([(f"📥 {a.get('name')}", a["url"], "url")])
    rows.append([("‹ بازگشت", "menu")])
    _reply(ctx, chat_id, message_id, txt, kb(rows))


def start_support(ctx, user, chat_id, message_id):
    ctx.db.set_state(user["tg_id"], "await_ticket", {})
    _reply(ctx, chat_id, message_id,
           "💬 <b>پشتیبانی</b>\n\n"
           "مشکل یا سوالتان را در یک پیام بنویسید — هرچه دقیق‌تر، "
           "سریع‌تر حل می‌شود.\n\n"
           "<i>اگر درباره‌ی سفارش است، کد پیگیری‌اش را هم بنویسید.</i>",
           kb([[("✖️ انصراف", "menu")]]))


def handle_ticket(ctx, msg, user):
    text = msg.get("text") or msg.get("caption") or ""
    if not text.strip():
        return ctx.bot.send(user["tg_id"],
                            "پیامتان را به‌صورت متن بنویسید تا ثبت شود.")

    tid = ctx.db.exec(
        "INSERT INTO tickets (tenant_id, user_id, message) VALUES (?,?,?)",
        (ctx.tid, user["id"], text[:2000])
    )
    ctx.db.clear_state(user["tg_id"])
    ctx.bot.send(user["tg_id"],
                 "✅ <b>پیامتان ثبت شد</b>\n\n"
                 "پاسخ را همین‌جا در تلگرام می‌گیرید — لازم نیست منتظر بمانید.\n\n"
                 f"<i>شماره پیگیری:</i> <code>#{tid}</code>",
                 keyboard=main_menu(ctx, user))

    ctx.notify_group(
        f"🎫 <b>تیکت #{tid}</b>\n\n"
        f"👤 {esc(user.get('first_name'))} (<code>{user['tg_id']}</code>)\n\n"
        f"{esc(text[:800])}",
        keyboard=kb([[("✍️ پاسخ", f"tk:{tid}")]]),
        topic="tickets"
    )


def check_membership(ctx, u):
    """
    بررسی عضویت اجباری کانال.

    برمی‌گرداند: (مجاز, کیبورد_دعوت)
    اگر کانالی تنظیم نشده، همیشه مجاز است. اگر تلگرام خطا داد
    (مثلاً ربات در کانال ادمین نیست)، سخت‌گیری نمی‌کنیم — قفل‌شدن
    کل فروش بدتر از رد نشدن یک نفر است.
    """
    if not ctx.s.get("force_channel_on"):
        return True, None
    ch = ctx.s.get("force_channel")
    if not ch:
        return True, None
    try:
        st = ctx.bot.member_status(ch, u["tg_id"])
    except Exception:
        return True, None
    if st in ("member", "administrator", "creator"):
        return True, None

    link = ch if str(ch).startswith("http") else f"https://t.me/{str(ch).lstrip('@')}"
    return False, kb([
        [("📢 عضویت در کانال", link, "url")],
        [("✅ عضو شدم، بررسی کن", "menu")],
    ])


def require_membership(ctx, chat_id, message_id, u):
    """اگر عضو نبود پیام می‌دهد و True برمی‌گرداند (یعنی ادامه نده)."""
    allowed, invite = check_membership(ctx, u)
    if allowed:
        return False
    _reply(ctx, chat_id, message_id,
           "📢 <b>یک قدم مانده</b>\n\n"
           "برای ادامه، اول در کانال ما عضو شوید — اطلاع‌رسانی قطعی‌ها و "
           "تخفیف‌ها همان‌جا منتشر می‌شود.\n\n"
           "بعد از عضویت، دکمه‌ی «عضو شدم» را بزنید.", invite)
    return True


def affiliate_panel(ctx, user, chat_id, message_id):
    """
    پنل همکار فروش.

    چیزی که همکار می‌خواهد بداند: لینکش، چند نفر آورده، چقدر
    فروش شده، چقدر پورسانت گرفته و چقدر طلبکار است.
    """
    aff = DB.affiliate_by_tg(ctx.tid, user["tg_id"])
    if not aff:
        return _reply(ctx, chat_id, message_id,
                      "این بخش مخصوص همکاران فروش است.\n\n"
                      "اگر دوست دارید همکار شوید و از فروشتان پورسانت بگیرید، "
                      "به پشتیبانی پیام بدهید.",
                      back_kb())

    st = DB.affiliate_stats(ctx.tid, aff["id"])
    bot_user = ctx.s.get("bot_username") or ""
    link = (f"https://t.me/{bot_user}?start=aff_{aff['code']}"
            if bot_user else f"کد شما: {aff['code']}")

    lines = [
        "💼 <b>پنل همکاری در فروش</b>",
        "",
        f"سلام {esc(aff['name'])} 👋",
        f"پورسانت شما <b>{core.fa(aff['percent'])}٪</b> از هر خرید است.",
        "",
        "📊 <b>عملکرد</b>",
        f"کاربران معرفی‌شده   <b>{core.fa(st['users'])}</b>",
        f"خریدهای انجام‌شده   <b>{core.fa(st['orders'])}</b>",
        f"مجموع فروش   <b>{core.toman(st['sales'])}</b> تومان",
        "",
        "💰 <b>پورسانت</b>",
        f"کل پورسانت   <b>{core.toman(st['earned'])}</b> تومان",
        f"دریافت‌شده   {core.toman(st['payouts'])} تومان",
        f"<b>مانده   {core.toman(st['balance'])} تومان</b>",
        "",
        "🔗 <b>لینک اختصاصی شما</b>",
        f"<code>{esc(link)}</code>",
        "",
        "<i>هر کسی با این لینک وارد شود، از تمام خریدهایش — "
        "نه فقط خرید اول — به شما پورسانت می‌رسد.</i>",
    ]

    return _reply(ctx, chat_id, message_id, "\n".join(lines),
                  kb([[("📋 ریز فروش‌ها", "aff_list")],
                      [("‹ منو", "menu")]]))


def affiliate_list(ctx, user, chat_id, message_id):
    """ریز فروش‌های یک همکار."""
    aff = DB.affiliate_by_tg(ctx.tid, user["tg_id"])
    if not aff:
        return _reply(ctx, chat_id, message_id, "دسترسی ندارید.", back_kb())

    rows = ctx.db.q(
        """SELECT c.*, u.first_name, u.username
           FROM affiliate_commissions c
           LEFT JOIN users u ON u.id = c.user_id
           WHERE c.tenant_id=? AND c.affiliate_id=? AND c.status != 'cancelled'
           ORDER BY c.id DESC LIMIT 25""",
        (ctx.tid, aff["id"]))

    if not rows:
        return _reply(ctx, chat_id, message_id,
                      "📋 <b>ریز فروش‌ها</b>\n\n"
                      "هنوز فروشی ثبت نشده.\n\n"
                      "لینک اختصاصی‌تان را پخش کنید — از اولین خرید، "
                      "همه‌چیز همین‌جا می‌آید.",
                      kb([[("‹ بازگشت", "affiliate")]]))

    lines = ["📋 <b>ریز فروش‌ها</b>", ""]
    for r in rows:
        who = r.get("first_name") or r.get("username") or "کاربر"
        when = core.fa_date(r.get("created_at"), with_month_name=False)
        mark = "✅" if r["status"] == "paid" else "⏳"
        lines.append(f"{mark} {esc(who)} · {when}")
        lines.append(f"خرید {core.toman(r['order_amount'])} — "
                     f"پورسانت <b>{core.toman(r['commission'])}</b>")
        lines.append("")

    lines.append("<i>⏳ در انتظار پرداخت  ·  ✅ پرداخت‌شده</i>")

    return _reply(ctx, chat_id, message_id, "\n".join(lines),
                  kb([[("‹ بازگشت", "affiliate")]]))


def my_orders(ctx, user, chat_id, message_id):
    """
    تاریخچه‌ی سفارش‌های کاربر.

    هر سفارش با وضعیتش می‌آید — تا کاربر بداند رسیدش دیده شده یا
    نه، و اگر رد شده چرا. بدون این، تنها راهش پرسیدن از پشتیبانی است.
    """
    rows = ctx.db.q(
        """SELECT o.*, p.name AS plan_name, p.gb, p.days
           FROM orders o LEFT JOIN plans p ON p.id = o.plan_id
           WHERE o.tenant_id=? AND o.user_id=?
           ORDER BY o.id DESC LIMIT 15""",
        (ctx.tid, user["id"]))

    if not rows:
        return _reply(ctx, chat_id, message_id,
                      "🧾 <b>سفارش‌های من</b>\n\n"
                      "هنوز سفارشی اینجا نیست.\n\n"
                      "هر خریدی که بکنید، با وضعیتش همین‌جا ثبت می‌شود.",
                      kb([[("🛒 خرید اشتراک", "buy")], [("‹ منو", "menu")]]))

    label = {
        "pending": "⏳ در انتظار رسید",
        "awaiting": "⏳ در حال بررسی",
        "approved": "✅ تایید شده",
        "rejected": "❌ رد شده",
        "cancelled": "🚫 لغو شده",
        "expired": "⌛️ مهلتش تمام شد",
    }

    lines = ["🧾 <b>سفارش‌های من</b>", ""]
    for o in rows:
        st = label.get(o["status"], o["status"])
        when = core.fa_datetime(o.get("created_at"))
        name = o.get("plan_name") or "—"

        lines.append(f"{st} · {name}")

        # مبلغ نهایی در amount است، نه final_price/price که وجود ندارند
        price = o.get("amount") or 0
        if price:
            lines.append(f"<b>{core.toman(price)}</b> تومان · {when}")
        else:
            lines.append(f"رایگان · {when}")
        if o.get("coins_used"):
            lines.append(f"با {core.fa(o['coins_used'])} سکه")

        # دلیل رد — مهم‌ترین چیزی که کاربر می‌خواهد بداند
        if o["status"] == "rejected" and o.get("admin_note"):
            lines.append(f"<i>دلیل: {esc(o['admin_note'][:90])}</i>")

        lines.append(f"<i>کد پیگیری:</i> <code>#{o['id']}</code>")
        lines.append("")

    buttons = []
    pending = [o for o in rows if o["status"] in ("pending", "awaiting")]
    if pending:
        lines.append(f"<i>{core.fa(len(pending))} سفارش هنوز در جریان است.</i>")
    if any(o["status"] == "rejected" for o in rows):
        buttons.append([("🔄 خرید مجدد", "buy")])
    buttons.append([("‹ منو", "menu")])

    return _reply(ctx, chat_id, message_id, "\n".join(lines), kb(buttons))


def give_trial(ctx, user, chat_id, message_id):
    u = ctx.db.get_user(user["tg_id"])
    if u.get("trial_used"):
        return _reply(ctx, chat_id, message_id,
                      "اشتراک تست رایگان را قبلاً گرفته‌اید — "
                      "هر حساب فقط یک‌بار می‌تواند.\n\n"
                      "برای ادامه، یکی از پلن‌ها را انتخاب کنید.",
                      kb([[("🛒 دیدن پلن‌ها", "buy")], [("‹ بازگشت", "menu")]]))

    plan = ctx.db.trial_plan()
    if not plan:
        return _reply(ctx, chat_id, message_id,
                      "اشتراک تست فعلاً فعال نیست.", back_kb())

    if require_membership(ctx, chat_id, message_id, user):
        return

    # حقِ تست را *قبل* از ساخت می‌گیریم.
    #
    # بررسی بالا فقط یک خواندن است؛ بین آن و نوشتن پرچم، ساخت کانفیگ
    # چند ثانیه طول می‌کشد. دو بار زدنِ دکمه یعنی هر دو نخ پرچم را
    # صفر می‌دیدند و هر دو کانفیگ رایگان می‌ساختند.
    if not ctx.db.claim_trial(u["id"]):
        return _reply(ctx, chat_id, message_id,
                      "اشتراک تست رایگان را قبلاً گرفته‌اید — "
                      "هر حساب فقط یک‌بار می‌تواند.",
                      kb([[("🛒 دیدن پلن‌ها", "buy")], [("‹ بازگشت", "menu")]]))

    order = ctx.db.create_order(u["id"], plan["id"], 0, 0, kind="new")

    # سفارش این‌جا approved *نمی‌شود* — همان قاعده‌ی مسیر کارت و کیف
    # پول: تا کانفیگ ساخته نشود، فروشی اتفاق نیفتاده. قبلاً اول
    # approved می‌شد و اگر ساخت شکست می‌خورد، سفارشِ approved می‌ماند:
    # کاربری که هیچ‌وقت چیزی نگرفت، در قیف «خرید موفق» شمرده می‌شد.
    ok, result = provision(ctx, order["id"])
    if not ok:
        # پیام پایین می‌گوید تست محفوظ است — پس واقعاً پسش می‌دهیم
        ctx.db.release_trial(u["id"])
        ctx.db.close_order(order["id"], "rejected", "ساخت اشتراک تست ناموفق")
        return _reply(ctx, chat_id, message_id,
                      "ساخت اشتراک تست به مشکل خورد.\n\n"
                      f"<i>{esc(result)}</i>\n\n"
                      "چند دقیقه دیگر دوباره امتحان کنید — "
                      "تست رایگانتان هنوز محفوظ است.", back_kb())

    ctx.db.close_order(order["id"], "approved")

    _reply(ctx, chat_id, message_id,
           "🎉 <b>اشتراک تست رایگان شما فعال شد</b>\n\n"
           "همین پایین می‌فرستیمش — امتحانش کنید و اگر پسندیدید، "
           "پلن اصلی را بگیرید.", None)
    deliver(ctx, u, result)

    ctx.notify_group(
        f"🎉 اشتراک تست\n👤 {esc(u.get('first_name'))} (<code>{u['tg_id']}</code>)",
        topic="users"
    )


# ═══════════════════════════════════════════════════════════
#  کمکی
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
#  پنل مدیریت داخل ربات — فقط برای ادمین‌ها
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
#  دریافت شماره تلفن — اختیاری
#  اجباری نیست: کاربری که نمی‌خواهد شماره بدهد نباید از خرید
#  محروم شود. فقط یک‌بار پرسیده می‌شود.
# ═══════════════════════════════════════════════════════════

SKIP_PHONE = "فعلاً نه"


def ask_phone(ctx, user, chat_id):
    """اگر شماره نداریم و قبلاً نپرسیده‌ایم، یک‌بار می‌پرسیم."""
    if user.get("phone"):
        return False
    if not ctx.s.get("ask_phone", True):
        return False

    # اگر قبلاً پرسیده‌ایم، دوباره مزاحم نمی‌شویم
    if user.get("phone_asked"):
        return False

    ctx.db.exec("UPDATE users SET phone_asked=1 WHERE tenant_id=? AND tg_id=?",
                (ctx.tid, user["tg_id"]))
    ctx.db.set_state(user["tg_id"], "await_phone", {})
    txt = ctx.s.get("phone_prompt") or (
        "📱 <b>شماره تماس</b>\n\n"
        "اگر شماره‌تان را ثبت کنید، وقتی مشکلی پیش بیاید سریع‌تر پیدایتان "
        "می‌کنیم و اشتراکتان قابل بازیابی می‌ماند.\n\n"
        "<i>کاملاً اختیاری است — بدون آن هم می‌توانید خرید کنید.</i>"
    )
    ctx.bot.send(chat_id, txt,
                 keyboard=contact_kb("📱 ارسال شماره من", SKIP_PHONE))
    return True


def handle_phone(ctx, msg, user):
    """پردازش شماره — از دکمه‌ی تلگرام یا تایپ دستی."""
    chat_id = msg["chat"]["id"]
    contact = msg.get("contact")
    text = (msg.get("text") or "").strip()

    # کاربر رد کرد
    if text == SKIP_PHONE or text in ("رد", "بعدا", "بعداً"):
        ctx.db.clear_state(user["tg_id"])
        ctx.bot.send(chat_id, "باشه، بدون شماره ادامه می‌دهیم 👍",
                     keyboard=remove_kb())
        return cmd_start(ctx, msg)

    phone = None
    if contact:
        # فقط شماره‌ی خود کاربر را می‌پذیریم، نه مخاطب دیگری
        if contact.get("user_id") and int(contact["user_id"]) != int(user["tg_id"]):
            ctx.bot.send(chat_id,
                         "این شماره متعلق به شما نیست. لطفاً شماره‌ی خودتان را بفرستید.",
                         keyboard=contact_kb("📱 ارسال شماره من", SKIP_PHONE))
            return
        phone = contact.get("phone_number")
    elif text:
        digits = "".join(ch for ch in text if ch.isdigit() or ch == "+")
        if len(digits) >= 10:
            phone = digits

    if not phone:
        ctx.bot.send(chat_id,
                     "این شماره درست به نظر نمی‌رسد.\n\n"
                     "ساده‌ترین راه دکمه‌ی پایین است — یا شماره را به شکل "
                     "<code>09121234567</code> بنویسید.",
                     keyboard=contact_kb("📱 ارسال شماره من", SKIP_PHONE))
        return

    phone = core.normalize_phone(phone)
    ctx.db.exec("UPDATE users SET phone=? WHERE tenant_id=? AND tg_id=?",
                (phone, ctx.tid, user["tg_id"]))
    ctx.db.clear_state(user["tg_id"])

    ctx.bot.send(chat_id,
                 f"✅ شماره‌ی <code>{esc(core.pretty_phone(phone))}</code> ثبت شد.",
                 keyboard=remove_kb())
    user = ctx.db.get_user(user["tg_id"])
    return cmd_start(ctx, msg)


def show_admin(ctx, user, chat_id, message_id=None):
    """صفحه‌ی اصلی پنل مدیریت با آمار زنده."""
    if not ctx.is_admin(user["tg_id"]):
        return _reply(ctx, chat_id, message_id, "دسترسی ندارید.", back_kb())

    st = ctx.db.stats()
    pending = st.get("pending", 0)

    txt = (
        f"⚙️ <b>پنل مدیریت</b> · {esc(ctx.brand())}\n\n"
        f"👥 کاربران   <b>{core.fa(st.get('users', 0))}</b>\n"
        f"📦 اشتراک فعال   <b>{core.fa(st.get('active_subs', 0))}</b>\n"
        f"💳 رسید در انتظار   <b>{core.fa(pending)}</b>\n"
        f"🎫 تیکت باز   <b>{core.fa(st.get('open_tickets', 0))}</b>\n\n"
        f"💰 فروش کل   <b>{core.toman(st.get('revenue_total', 0))}</b> تومان"
    )
    if pending:
        txt += f"\n\n⏳ <b>{core.fa(pending)}</b> رسید منتظر بررسی شماست."

    rows = []
    rows.append([(f"💳 رسیدها ({pending})" if pending else "💳 رسیدها", "adm:orders")])
    rows += [
        [("👥 کاربران", "adm:users"), ("📦 پلن‌ها", "adm:plans")],
        [("📊 آمار", "adm:stats"), ("📢 پیام همگانی", "adm:bc")],
        [("‹ بازگشت", "menu")],
    ]
    return _reply(ctx, chat_id, message_id, txt, kb(rows))


def admin_orders(ctx, user, chat_id, message_id=None):
    """صف رسیدهای در انتظار."""
    if not ctx.is_admin(user["tg_id"]):
        return

    orders = ctx.db.pending_orders()
    if not orders:
        return _reply(ctx, chat_id, message_id,
                      "✅ صف رسیدها خالی است — همه بررسی شده‌اند.",
                      back_kb("admin"))

    rows = []
    for o in orders[:10]:
        nm = (o.get("first_name") or "بدون نام")[:15]
        rows.append([(f"#{o['id']} · {nm} · {core.toman(o['amount'])}", f"adm:o:{o['id']}")])
    rows.append([("‹ بازگشت", "admin")])

    return _reply(ctx, chat_id, message_id,
                  f"💳 <b>رسیدهای در انتظار</b> · {core.fa(len(orders))}\n\n"
                  "روی هرکدام بزنید تا جزئیات و رسیدش را ببینید.", kb(rows))


def admin_order_detail(ctx, user, chat_id, message_id, order_id):
    """جزئیات سفارش با دکمه تایید/رد."""
    if not ctx.is_admin(user["tg_id"]):
        return

    o = ctx.db.get_order(order_id)
    if not o:
        return _reply(ctx, chat_id, message_id, "سفارش پیدا نشد.", back_kb("adm:orders"))

    u = ctx.db.get_user_by_id(o["user_id"]) or {}
    p = ctx.db.get_plan(o["plan_id"]) if o.get("plan_id") else None

    txt = (
        f"🧾 <b>سفارش #{o['id']}</b>\n\n"
        f"{esc(u.get('first_name') or 'بدون نام')}"
        + (f" · @{esc(u['username'])}" if u.get("username") else "") + "\n"
        f"<code>{u.get('tg_id', '?')}</code>\n\n"
        f"{esc(p['name']) if p else 'نامشخص'}\n"
        f"<b>{core.toman(o['amount'])}</b> تومان\n"
    )
    if o.get("coins_used"):
        txt += (f"با {core.fa(o['coins_used'])} سکه · "
                f"{core.fa(o.get('discount_pct', 0))}٪ تخفیف\n")
    txt += f"{core.fa_datetime(o.get('created_at'))}"

    if o.get("receipt_text"):
        txt += f"\n\n📝 <i>{esc(str(o['receipt_text'])[:180])}</i>"

    rows = []
    if o["status"] in ("awaiting", "review"):
        rows = [
            [("✅ تایید و ساخت کانفیگ", f"ap:{o['id']}")],
            [("❌ رد", f"rj:{o['id']}"), ("💬 سوال از مشتری", f"adm:ask:{o['id']}")],
        ]
    else:
        txt += f"\n\nوضعیت: <b>{o['status']}</b>"
    rows.append([("‹ بازگشت", "adm:orders")])

    if o.get("receipt_type") == "photo" and o.get("receipt_file"):
        try:
            ctx.bot.send_photo(chat_id, o["receipt_file"], caption=txt, keyboard=kb(rows))
            return
        except TelegramError:
            pass

    return _reply(ctx, chat_id, message_id, txt, kb(rows))


def admin_users(ctx, user, chat_id, message_id=None):
    """آخرین کاربران."""
    if not ctx.is_admin(user["tg_id"]):
        return

    rows_db = ctx.db.q(
        "SELECT * FROM users WHERE tenant_id=? ORDER BY created_at DESC LIMIT 10",
        (ctx.tid,))
    if not rows_db:
        return _reply(ctx, chat_id, message_id,
                      "هنوز کاربری ثبت نشده است.", back_kb("admin"))

    lines = ["👥 <b>آخرین کاربران</b>", ""]
    rows = []
    for u in rows_db:
        nm = esc((u.get("first_name") or "بدون نام")[:16])
        un = f" @{esc(u['username'])}" if u.get("username") else ""
        lines.append(f"{nm}{un} — {core.fa(u.get('coins', 0))} سکه · "
                     f"{core.toman(u.get('balance', 0))} تومان")
        rows.append([(f"{nm} · {u['tg_id']}", f"adm:u:{u['tg_id']}")])

    rows.append([("🔎 جستجو", "adm:find")])
    rows.append([("‹ بازگشت", "admin")])
    return _reply(ctx, chat_id, message_id, "\n".join(lines), kb(rows))


def admin_user_detail(ctx, user, chat_id, message_id, target_id):
    """جزئیات و مدیریت یک کاربر."""
    if not ctx.is_admin(user["tg_id"]):
        return

    u = ctx.db.get_user(int(target_id))
    if not u:
        return _reply(ctx, chat_id, message_id, "کاربر پیدا نشد.", back_kb("adm:users"))

    subs = ctx.db.user_subs(u["id"], active_only=False)
    active = [s for s in subs if s.get("is_active")]

    txt = (
        f"👤 <b>{esc(u.get('first_name') or 'بدون نام')}</b>"
        + (f" · @{esc(u['username'])}" if u.get("username") else "") + "\n"
        f"<code>{u['tg_id']}</code>\n\n"
        f"🪙 سکه   <b>{core.fa(u.get('coins', 0))}</b>\n"
        f"👛 کیف پول   <b>{core.toman(u.get('balance', 0))}</b> تومان\n"
        f"📦 اشتراک فعال   <b>{core.fa(len(active))}</b>\n"
        f"📅 عضویت   {core.fa_date(u.get('created_at'))}\n\n"
        f"🔗 کد دعوت   <code>{u.get('ref_code', '—')}</code>"
    )
    if u.get("is_blocked"):
        txt += "\n\n🚫 <b>این کاربر مسدود است</b>"

    rows = [
        [("💎 سکه", f"adm:coin:{u['tg_id']}"), ("👛 کیف پول", f"adm:bal:{u['tg_id']}")],
        [("💬 ارسال پیام", f"adm:msg:{u['tg_id']}")],
        [("✅ رفع مسدودی" if u.get("is_blocked") else "🚫 مسدودسازی", f"adm:blk:{u['tg_id']}")],
        [("‹ بازگشت", "adm:users")],
    ]
    return _reply(ctx, chat_id, message_id, txt, kb(rows))


def admin_stats(ctx, user, chat_id, message_id=None):
    """آمار کامل."""
    if not ctx.is_admin(user["tg_id"]):
        return

    st = ctx.db.stats()
    txt = (
        f"📊 <b>آمار</b>\n\n"
        f"👥 کاربران   <b>{core.fa(st.get('users', 0))}</b>\n"
        f"📦 اشتراک فعال   <b>{core.fa(st.get('active_subs', 0))}</b>\n"
        f"💳 رسید در انتظار   <b>{core.fa(st.get('pending', 0))}</b>\n"
        f"🎫 تیکت باز   <b>{core.fa(st.get('open_tickets', 0))}</b>\n\n"
        f"💰 فروش کل   <b>{core.toman(st.get('revenue_total', 0))}</b> تومان"
    )
    return _reply(ctx, chat_id, message_id, txt,
                  kb([[("🔄 تازه‌سازی", "adm:stats")], [("‹ بازگشت", "admin")]]))


def admin_plans(ctx, user, chat_id, message_id=None):
    """لیست پلن‌ها."""
    if not ctx.is_admin(user["tg_id"]):
        return

    plans = ctx.db.plans(active_only=False, include_trial=True)
    if not plans:
        return _reply(ctx, chat_id, message_id,
                      "هنوز پلنی ساخته نشده.\n\n"
                      "<i>ساخت و ویرایش پلن‌ها از پنل وب انجام می‌شود.</i>",
                      back_kb("admin"))

    lines = ["📦 <b>پلن‌ها</b>", ""]
    for p in plans:
        mark = "🟢" if p.get("is_active") else "⚪️"
        trial = " 🎁" if p.get("is_trial") else ""
        lines.append(f"{mark} {esc(p['name'])}{trial} — {core.toman(p['price'])} · "
                     f"{core.fmt_gb(p.get('gb'))} · {core.fmt_days(p.get('days'))}")

    lines.append("\n<i>ویرایش پلن‌ها از پنل وب انجام می‌شود.</i>")
    return _reply(ctx, chat_id, message_id, "\n".join(lines), back_kb("admin"))


def admin_ask_input(ctx, user, chat_id, message_id, kind, target=None):
    """شروع ورودی چندمرحله‌ای ادمین."""
    if not ctx.is_admin(user["tg_id"]):
        return

    prompts = {
        "bc": "📢 <b>پیام همگانی</b>\n\n"
              "متن را بفرستید تا برای <b>همه‌ی کاربران</b> ارسال شود.\n\n"
              "<i>قبل از ارسال دوباره بخوانیدش — برگشتی ندارد.</i>",
        "coin": "🪙 <b>تغییر سکه</b>\n\n"
                "چند سکه اضافه شود؟\n\n"
                "<i>برای کسر، عدد را با منها بنویسید — مثلاً</i> <code>-10</code>",
        "bal": "👛 <b>تغییر موجودی</b>\n\n"
               "چه مبلغی (تومان) اضافه شود؟\n\n"
               "<i>برای کسر، عدد را با منها بنویسید — مثلاً</i> <code>-50000</code>",
        "msg": "💬 <b>پیام به کاربر</b>\n\n"
               "متن پیام را بفرستید تا مستقیم برایش ارسال شود.",
        "ask": "💬 سوالتان از این مشتری را بفرستید.",
        "find": "🔎 نام، یوزرنیم یا آیدی عددی کاربر را بفرستید.",
        "tkreply": "✍️ <b>پاسخ به تیکت</b>\n\n"
                   "متن پاسخ را بفرستید تا مستقیم برای مشتری ارسال شود.\n\n"
                   "<blockquote>مشتری فقط همین متن را می‌بیند — نه نام شما "
                   "و نه اینکه از گروه مدیریت فرستاده شده.</blockquote>",
    }
    ctx.db.set_state(user["tg_id"], f"adm_{kind}", {"t": target})
    return _reply(ctx, chat_id, message_id,
                  prompts.get(kind, "مقدار را بفرستید:"),
                  kb([[("انصراف", "admin")]]))


def admin_input(ctx, user, chat_id, text, state, data):
    """پردازش ورودی ادمین."""
    if not ctx.is_admin(user["tg_id"]):
        return

    kind = state.replace("adm_", "")
    target = (data or {}).get("t")
    ctx.db.clear_state(user["tg_id"])
    txt = (text or "").strip()

    if kind == "bc":
        ids = [r["tg_id"] for r in ctx.db.q(
            "SELECT tg_id FROM users WHERE tenant_id=? AND is_blocked=0", (ctx.tid,))]

        if not ids:
            return _reply(ctx, chat_id, None, "کاربری برای ارسال نیست.",
                          back_kb("admin"))

        # پیام پیشرفت، چون ارسال به صدها نفر طول می‌کشد و بدون آن
        # کاربر فکر می‌کند چیزی کار نمی‌کند
        progress = ctx.bot.send(
            chat_id, f"📢 در حال ارسال به {core.fa(len(ids))} کاربر…")
        pid = (progress or {}).get("message_id") if isinstance(progress, dict) else None

        sent = failed = blocked = 0
        for i, uid in enumerate(ids, 1):
            try:
                ctx.bot.send(uid, txt)
                sent += 1
            except TelegramError as e:
                msg = str(e).lower()
                if "blocked" in msg or "deactivated" in msg or "chat not found" in msg:
                    blocked += 1
                    # کاربری که ربات را بلاک کرده دیگر مشتری نیست
                    try:
                        ctx.db.exec(
                            "UPDATE users SET is_blocked=1 WHERE tenant_id=? AND tg_id=?",
                            (ctx.tid, uid))
                    except Exception as e:
                        log.warning("marking user %s blocked failed: %s", uid, e)
                else:
                    failed += 1
            except Exception:
                failed += 1

            # تلگرام حدود ۳۰ پیام در ثانیه اجازه می‌دهد
            if i % 25 == 0:
                time.sleep(1.2)
                if pid:
                    try:
                        ctx.bot.edit(chat_id, pid,
                                     f"📢 ارسال… {core.fa(i)} از {core.fa(len(ids))}")
                    except Exception:
                        pass

        report = [
            "📢 <b>پیام همگانی ارسال شد</b>", "",
            f"رسید به   <b>{core.fa(sent)}</b> نفر",
        ]
        if blocked:
            report.append(f"ربات را بلاک کرده‌اند   {core.fa(blocked)}")
            report.append("<i>این‌ها خودکار غیرفعال شدند تا دفعه‌ی بعد "
                          "وقت تلف نشود.</i>")
        if failed:
            report.append(f"ناموفق   {core.fa(failed)}")

        if pid:
            try:
                ctx.bot.edit(chat_id, pid, "\n".join(report),
                             keyboard=back_kb("admin"))
                return
            except Exception:
                pass
        return _reply(ctx, chat_id, None, "\n".join(report), back_kb("admin"))

    if kind == "find":
        like = f"%{txt}%"
        found = ctx.db.q(
            "SELECT * FROM users WHERE tenant_id=? AND (first_name LIKE ? OR username LIKE ? "
            "OR CAST(tg_id AS TEXT) LIKE ?) LIMIT 8", (ctx.tid, like, like, like))
        if not found:
            return _reply(ctx, chat_id, None,
                          "کسی با این مشخصات یافت نشد.\n\n"
                          "<i>با آیدی عددی مطمئن‌تر است.</i>",
                          back_kb("adm:users"))
        rows = [[(f"{(u.get('first_name') or '?')[:18]} · {u['tg_id']}", f"adm:u:{u['tg_id']}")]
                for u in found]
        rows.append([("‹ بازگشت", "adm:users")])
        return _reply(ctx, chat_id, None,
                      f"🔎 <b>{core.fa(len(found))}</b> نتیجه", kb(rows))

    if kind in ("coin", "bal") and target:
        try:
            amt = int(txt.replace(",", "").replace("،", ""))
        except ValueError:
            return _reply(ctx, chat_id, None,
                          "عدد معتبر نبود. فقط رقم بنویسید — "
                          "مثلاً <code>50</code> یا <code>-10</code>",
                          back_kb("admin"))

        u = ctx.db.get_user(int(target))
        if not u:
            return _reply(ctx, chat_id, None,
                          "این کاربر پیدا نشد.", back_kb("adm:users"))

        if kind == "coin":
            ctx.db.add_coins(u["id"], amt, "admin", "تنظیم دستی ادمین")
            fresh = ctx.db.get_user(u["tg_id"])
            note = (f"🪙 {core.fa(abs(amt))} سکه "
                    f"{'اضافه' if amt > 0 else 'کسر'} شد.")
            user_msg = (
                f"🪙 <b>{core.fa(abs(amt))} سکه</b> به حسابتان "
                f"{'اضافه شد' if amt > 0 else 'کم شد'}.\n\n"
                f"موجودی فعلی: <b>{core.fa(fresh.get('coins', 0))}</b> سکه")
        else:
            ctx.db.add_balance(u["id"], amt, "admin", "تنظیم دستی ادمین")
            fresh = ctx.db.get_user(u["tg_id"])
            note = (f"👛 {core.toman(abs(amt))} تومان "
                    f"{'اضافه' if amt > 0 else 'کسر'} شد.")
            user_msg = (
                f"👛 کیف پولتان <b>{core.toman(abs(amt))}</b> تومان "
                f"{'شارژ شد' if amt > 0 else 'کم شد'}.\n\n"
                f"موجودی فعلی: <b>{core.toman(fresh.get('balance', 0))}</b> تومان")

        try:
            ctx.bot.send(u["tg_id"], user_msg)
        except TelegramError:
            pass
        return _reply(ctx, chat_id, None, f"✅ {note}",
                      kb([[("‹ بازگشت", f"adm:u:{target}")]]))

    if kind == "msg" and target:
        u = ctx.db.get_user(int(target))
        if u:
            try:
                ctx.bot.send(u["tg_id"], f"💬 <b>پیام از پشتیبانی</b>\n\n{esc(txt)}")
                return _reply(ctx, chat_id, None, "✅ پیام رسید.",
                              kb([[("‹ بازگشت", f"adm:u:{target}")]]))
            except TelegramError:
                return _reply(ctx, chat_id, None,
                              "❌ نرسید — احتمالاً کاربر ربات را بلاک کرده.",
                              back_kb("adm:users"))

    if kind == "tkreply" and target:
        t = ctx.db.q("SELECT * FROM tickets WHERE tenant_id=? AND id=?",
                     (ctx.tid, int(target)), one=True)
        if not t:
            return _reply(ctx, chat_id, None, "این تیکت پیدا نشد.", back_kb())

        u = ctx.db.get_user_by_id(t["user_id"])
        if not u:
            return _reply(ctx, chat_id, None, "کاربر این تیکت پیدا نشد.", back_kb())

        try:
            ctx.bot.send(
                u["tg_id"],
                "💬 <b>پاسخ پشتیبانی</b>\n\n"
                f"{esc(txt)}\n\n"
                f"<blockquote>درباره‌ی پیامی که فرستاده بودید — "
                f"شماره پیگیری <code>#{t['id']}</code></blockquote>",
                keyboard=kb([[("💬 پاسخ دوباره", "support")],
                             [("‹ منوی اصلی", "menu")]]))
        except TelegramError:
            return _reply(ctx, chat_id, None,
                          "❌ نرسید — احتمالاً کاربر ربات را بلاک کرده.",
                          back_kb())

        # تیکت بسته می‌شود تا در فهرست «باز» نماند و دو بار جواب نگیرد
        try:
            ctx.db.exec(
                "UPDATE tickets SET status='answered', answer=?, "
                "answered_at=CURRENT_TIMESTAMP WHERE tenant_id=? AND id=?",
                (txt[:2000], ctx.tid, int(target)))
        except Exception as e:
            # پاسخ رفته، ولی تیکت «باز» می‌ماند و ممکن است دوباره جواب بگیرد
            log.warning("closing ticket %s after reply failed: %s", target, e)

        return _reply(ctx, chat_id, None,
                      f"✅ پاسخ تیکت <code>#{target}</code> برای مشتری رفت.",
                      kb([[("‹ منوی مدیریت", "admin")]]))

    if kind == "reject" and target:
        if not do_reject(ctx, int(target), user["tg_id"],
                         txt or "رسید تأیید نشد."):
            # رد حالا شرطی است: سفارشی که کانفیگ گرفته یا قبلاً رد
            # شده، رد نمی‌شود. گفتن «رد شد» در آن حالت دروغ است.
            return _reply(ctx, chat_id, None,
                          f"سفارش <code>#{target}</code> رد نشد — یا کانفیگش "
                          "ساخته شده، یا قبلاً رد شده بود.\n\n"
                          "وضعیتش را از فهرست سفارش‌ها ببینید.",
                          back_kb("adm:orders"))
        return _reply(ctx, chat_id, None,
                      f"❌ سفارش #{target} رد شد و دلیلش به مشتری رسید.",
                      back_kb("adm:orders"))

    if kind == "ask" and target:
        o = ctx.db.get_order(int(target))
        if o:
            u = ctx.db.get_user_by_id(o["user_id"])
            if u:
                try:
                    ctx.bot.send(u["tg_id"],
                                     f"💬 <b>درباره سفارش #{o['id']}</b>\n\n{esc(txt)}")
                    return _reply(ctx, chat_id, None, "✅ پیام رسید.",
                                  kb([[("‹ بازگشت", f"adm:o:{target}")]]))
                except TelegramError:
                    pass
        return _reply(ctx, chat_id, None,
                      "❌ نرسید — احتمالاً کاربر ربات را بلاک کرده.",
                      back_kb("adm:orders"))

    return _reply(ctx, chat_id, None,
                  "این ورودی شناخته نشد. از منو دوباره شروع کنید.",
                  back_kb("admin"))


def admin_toggle_block(ctx, user, chat_id, message_id, target_id):
    """مسدود/رفع مسدودی کاربر."""
    if not ctx.is_admin(user["tg_id"]):
        return
    u = ctx.db.get_user(int(target_id))
    if not u:
        return
    new = 0 if u.get("is_blocked") else 1
    ctx.db.exec("UPDATE users SET is_blocked=? WHERE tenant_id=? AND tg_id=?",
                (new, ctx.tid, int(target_id)))
    return admin_user_detail(ctx, user, chat_id, message_id, target_id)


def _reply(ctx, chat_id, message_id, text, keyboard):
    """اگر message_id باشد ویرایش می‌کند، وگرنه پیام جدید می‌فرستد."""
    if message_id:
        try:
            return ctx.bot.edit(chat_id, message_id, text, keyboard)
        except TelegramError:
            pass
    return ctx.bot.send(chat_id, text, keyboard=keyboard)


# ═══════════════════════════════════════════════════════════
#  مسیریاب — نقطه‌ی ورود همه‌ی آپدیت‌های تلگرام
# ═══════════════════════════════════════════════════════════

def dispatch(tenant, bot, update):
    """
    یک آپدیت تلگرام را به هندلر مناسب می‌رساند.

    این تنها نقطه‌ای است که run.py صدا می‌زند؛ بقیه‌ی توابع از این‌جا
    فراخوانی می‌شوند. خطاها این‌جا گرفته می‌شوند تا یک آپدیت خراب
    کل حلقه‌ی مستاجر را متوقف نکند.
    """
    ctx = Ctx(bot, tenant)

    # داکstring بالا این را وعده می‌داد ولی try واقعی وجود نداشت؛ هر
    # خطای یک آپدیت تا حلقه‌ی اصلی بالا می‌رفت.
    try:
        if "callback_query" in update:
            return _on_callback(ctx, update["callback_query"])
        if "message" in update:
            return _on_message(ctx, update["message"])
    except Exception as e:
        log.exception("خطای پردازش آپدیت %s", update.get("update_id"))
        try:
            ctx.notify_group(_error_alert(update, e), topic="alerts")
        except Exception:
            pass
    return None


def _error_alert(update, exc):
    """
    متن هشدار خطا برای گروه مدیریت.

    قبلاً فقط update_id و «جزئیات در لاگ سرور است» فرستاده می‌شد، که
    یعنی مدیر باید SSH بزند تا بفهمد کدام دکمه شکسته. حالا نوع خطا و
    دکمه‌ای که زده شده هم می‌آید — هیچ‌کدام حساس نیستند و معمولاً همان
    دو خط برای فهمیدن ماجرا کافی است.

    عمداً هیچ متن پیام کاربر این‌جا نمی‌آید؛ گروه مدیریت جای محتوای
    خصوصی مشتری نیست.
    """
    cb = (update.get("callback_query") or {})
    msg = update.get("message") or {}
    who = (cb.get("from") or msg.get("from") or {})

    lines = ["⚠️ <b>خطا در پردازش یک پیام</b>", ""]

    if cb.get("data"):
        lines.append(f"دکمه: <code>{esc(str(cb['data'])[:64])}</code>")
    elif msg.get("text", "").startswith("/"):
        lines.append(f"دستور: <code>{esc(msg['text'].split()[0][:32])}</code>")
    else:
        lines.append("رویداد: پیام معمولی")

    if who.get("id"):
        lines.append(f"کاربر: <code>{esc(str(who['id']))}</code>")

    lines += ["", f"<code>{esc(type(exc).__name__)}: "
                  f"{esc(str(exc)[:160])}</code>", ""]
    lines.append("<i>ردپای کامل در لاگ سرور — "
                 "<code>journalctl -u nexora-bot -n 50</code></i>")
    return "\n".join(lines)


def _get_or_create(ctx, tg_user, ref=None):
    u = ctx.db.get_user(tg_user["id"])
    if u:
        ctx.db.touch_user(tg_user["id"])
        return u

    # کاربر این‌جا ساخته می‌شود، پس همین‌جا هم باید تصمیم بگیریم
    # لینک از کدام نوع بوده. قبلاً پیشوند aff_ فقط در cmd_start
    # دیده می‌شد — که هیچ‌وقت به آن نمی‌رسید، چون تا آن لحظه کاربر
    # ساخته شده بود و شرط «کاربر جدید» رد می‌شد. نتیجه: هیچ لینک
    # همکاری هرگز به همکارش وصل نمی‌شد.
    referred_by = None
    affiliate = None
    arg = (ref or "").strip()
    if arg.startswith("aff_"):
        affiliate = DB.affiliate_by_code(ctx.tid, arg[4:])
        # همکار نمی‌تواند خودش را معرفی کند.
        #
        # مسیر «دعوت دوست» همین شرط را داشت و این یکی نداشت. همکاری
        # که هنوز با ربات کار نکرده، با بازکردن لینک خودش مشتریِ خودش
        # می‌شد و از هر خریدِ خودش پورسانت می‌گرفت — یعنی تخفیفی که
        # قرار نبود وجود داشته باشد.
        if affiliate and affiliate.get("tg_id") == tg_user["id"]:
            affiliate = None
    elif arg and arg not in DEEP_WORDS and not arg.startswith("renew_"):
        inviter = ctx.db.get_user_by_ref(arg)
        # کاربر نمی‌تواند خودش را دعوت کند
        if inviter and inviter["tg_id"] != tg_user["id"]:
            referred_by = inviter["id"]

    u = ctx.db.create_user(
        tg_user["id"],
        username=tg_user.get("username"),
        first_name=tg_user.get("first_name"),
        referred_by=referred_by,
    )
    if affiliate:
        ctx.db.exec("UPDATE users SET affiliate_id=? WHERE tenant_id=? AND id=?",
                    (affiliate["id"], ctx.tid, u["id"]))
        u["affiliate_id"] = affiliate["id"]

    # ── همه‌ی کارهای «کاربر تازه آمد» این‌جا انجام می‌شوند ──
    #
    # قبلاً در cmd_start بودند، و همان‌جا هم نمی‌رسیدند: تا وقتی
    # cmd_start صدا زده شود، کاربر توسط همین تابع ساخته شده بود و
    # شرط «کاربر جدید» رد می‌شد. اگر گیت شماره هم فعال باشد،
    # cmd_start اصلاً در اولین تماس اجرا نمی‌شود.
    #
    # نتیجه‌اش این بود: معرف هیچ خبری نمی‌گرفت، پاداش خوش‌آمد داده
    # نمی‌شد، و گروه مدیریت کاربر جدید را نمی‌دید.
    ctx.db.log("signup", u["id"], {"ref": bool(referred_by)})

    cs = core.coin_settings(ctx.s.get("coins"))
    if referred_by and cs.get("welcome_bonus"):
        ctx.db.add_coins(u["id"], int(cs["welcome_bonus"]),
                         "bonus", "هدیه ورود با لینک دعوت")

    uname = tg_user.get("username")
    ctx.notify_group(
        f"👤 <b>کاربر جدید</b>\n"
        f"نام: {esc(tg_user.get('first_name'))}\n"
        f"آیدی: <code>{tg_user['id']}</code>\n"
        f"یوزرنیم: @{esc(uname) if uname else '—'}"
        + ("\n📎 با لینک دعوت" if referred_by else ""),
        topic="users"
    )

    if referred_by:
        _notify_referrer_joined(ctx, referred_by, tg_user)

    return u


def _on_message(ctx, msg):
    frm = msg.get("from") or {}
    if frm.get("is_bot"):
        return None

    chat = msg.get("chat") or {}
    # پیام‌های گروه مدیریت جدا رسیدگی می‌شوند
    if chat.get("type") in ("group", "supergroup"):
        return None

    text = (msg.get("text") or "").strip()

    # /start با پارامتر کد معرف
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        ref = parts[1].strip() if len(parts) > 1 else None
        # وصل‌شدنِ صاحبِ فروشگاه — پیش از هر کارِ دیگر، چون این کد
        # کدِ معرف نیست و نباید به‌جای آن ثبت شود.
        if ref and ref.startswith("own_"):
            return claim_owner(ctx, msg, ref[4:])
        user = _get_or_create(ctx, frm, ref)
        if user.get("is_blocked"):
            return None
        if ask_phone(ctx, user, msg["chat"]["id"]):
            return None
        return cmd_start(ctx, msg, ref)

    user = ctx.db.get_user(frm["id"])
    if not user:
        user = _get_or_create(ctx, frm)
    if user.get("is_blocked"):
        return None

    # ادامه‌ی گفتگوی چندمرحله‌ای
    state = user.get("state")
    try:
        sdata = json.loads(user.get("state_data") or "{}")
    except (json.JSONDecodeError, TypeError):
        sdata = {}

    if state == "await_phone" or msg.get("contact"):
        return handle_phone(ctx, msg, user)

    # ورودی‌های پنل مدیریت
    if state and state.startswith("adm_"):
        return admin_input(ctx, user, chat.get("id"), text, state, sdata)

    if state == "await_receipt":
        return handle_receipt(ctx, msg, user, sdata)
    if state == "await_ticket":
        return handle_ticket(ctx, msg, user)
    if state == "await_discount":
        return handle_discount(ctx, msg, user, sdata)

    if text == "/menu":
        return ctx.bot.send(chat["id"], welcome_text(ctx, user),
                            keyboard=main_menu(ctx, user))

    # پیام آزاد → منو
    return ctx.bot.send(chat["id"], welcome_text(ctx, user),
                        keyboard=main_menu(ctx, user))


# نگاشت callback ساده → تابع
_SIMPLE = {
    "menu":    lambda ctx, u, c, m: _reply(ctx, c, m, welcome_text(ctx, u), main_menu(ctx, u)),
    "buy":     lambda ctx, u, c, m: show_plans(ctx, u, c, m),
    "mysubs":  lambda ctx, u, c, m: show_subs(ctx, u, c, m),
    "myorders": lambda ctx, u, c, m: my_orders(ctx, u, c, m),
    "affiliate": lambda ctx, u, c, m: affiliate_panel(ctx, u, c, m),
    "aff_list": lambda ctx, u, c, m: affiliate_list(ctx, u, c, m),
    "wallet":  lambda ctx, u, c, m: show_wallet(ctx, u, c, m),
    "topup":   lambda ctx, u, c, m: wallet_topup(ctx, u, c, m),
    "coins":   lambda ctx, u, c, m: show_coins(ctx, u, c, m),
    "ref":     lambda ctx, u, c, m: show_referral(ctx, u, c, m),
    "help":    lambda ctx, u, c, m: show_help(ctx, u, c, m),
    "support": lambda ctx, u, c, m: start_support(ctx, u, c, m),
    "trial":   lambda ctx, u, c, m: give_trial(ctx, u, c, m),
    "admin":   lambda ctx, u, c, m: show_admin(ctx, u, c, m),
}


def _on_callback(ctx, cq):
    frm = cq.get("from") or {}
    data = cq.get("data") or ""
    msg = cq.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    mid = msg.get("message_id")

    user = ctx.db.get_user(frm["id"]) or _get_or_create(ctx, frm)
    if user.get("is_blocked"):
        return ctx.bot.answer_cb(cq["id"], "دسترسی شما مسدود است", alert=True)

    try:
        ctx.bot.answer_cb(cq["id"])
    except TelegramError:
        pass

    if data in _SIMPLE:
        return _SIMPLE[data](ctx, user, chat_id, mid)

    if ":" not in data:
        return None
    action, _, arg = data.partition(":")

    try:
        if action == "plan":
            return show_plan_detail(ctx, user, chat_id, mid, int(arg))
        if action == "chk":
            # chk:<plan>:<coins>[:<sub>] — بخش سوم فقط در تمدید می‌آید
            parts = arg.split(":")
            pid = int(parts[0])
            use_coins = len(parts) > 1 and parts[1] == "1"
            rid = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
            return checkout(ctx, user, chat_id, mid, pid, use_coins,
                            renew_sub_id=rid)
        if action == "dsc":
            return ask_discount(ctx, user, chat_id, mid, int(arg))
        if action == "dscx":
            return drop_discount(ctx, user, chat_id, mid, int(arg))
        if action == "wpay":
            parts = arg.split(":")
            rid = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
            return wallet_pay(ctx, user, chat_id, mid, int(parts[0]),
                              renew_sub_id=rid)
        if action == "topup":
            return wallet_topup_amount(ctx, user, chat_id, mid, int(arg))
        if action == "cancel":
            ctx.db.exec("UPDATE orders SET status='expired' WHERE tenant_id=? AND id=?",
                        (ctx.tid, int(arg)))
            _release_coins(ctx, int(arg))
            ctx.db.clear_state(user["tg_id"])
            return _reply(ctx, chat_id, mid,
                          "سفارش لغو شد. هر وقت خواستید دوباره اقدام کنید 👍",
                          main_menu(ctx, user))

        # دکمه‌ی «پاسخ» روی تیکت در گروه مدیریت.
        #
        # این هم مثل دکمه‌ی تمدید هندلر نداشت: ادمین روی «پاسخ»
        # می‌زد و هیچ اتفاقی نمی‌افتاد، پس عملاً هیچ تیکتی از داخل
        # تلگرام جواب داده نمی‌شد.
        if action == "tk":
            if not ctx.is_admin(frm["id"]):
                return ctx.bot.answer_cb(cq["id"], "دسترسی ندارید", alert=True)
            return admin_ask_input(ctx, user, chat_id, mid, "tkreply", arg)

        # دکمه‌ی «تمدید» در اشتراک‌های من.
        #
        # این شاخه وجود نداشت: دکمه ساخته می‌شد، کاربر می‌زد و هیچ
        # اتفاقی نمی‌افتاد. هیچ خطایی هم در لاگ نبود چون callback
        # بی‌صدا به انتهای تابع می‌رسید و None برمی‌گرداند.
        if action == "renew":
            return show_renew(ctx, user, chat_id, mid, int(arg))

        if action == "ost":
            return show_order_status(ctx, user, chat_id, mid, int(arg))

        # ارسال مجدد رسید بعد از رد
        if action == "retry":
            o = ctx.db.get_order(int(arg))
            if not o or o["user_id"] != user["id"]:
                return ctx.bot.answer_cb(cq["id"], "سفارش پیدا نشد", alert=True)
            ctx.db.set_state(user["tg_id"], "await_receipt", {"order": int(arg)})
            return _reply(ctx, chat_id, mid,
                          "📤 رسید جدید را بفرستید — عکس یا متن پیامک بانک.",
                          kb([[("انصراف", "menu")]]))

        # ── پنل مدیریت داخل ربات ──
        if action == "adm":
            if not ctx.is_admin(frm["id"]):
                return ctx.bot.answer_cb(cq["id"], "دسترسی ندارید", alert=True)

            sub, _, param = arg.partition(":")
            routes = {
                "orders": lambda: admin_orders(ctx, user, chat_id, mid),
                "users":  lambda: admin_users(ctx, user, chat_id, mid),
                "stats":  lambda: admin_stats(ctx, user, chat_id, mid),
                "plans":  lambda: admin_plans(ctx, user, chat_id, mid),
            }
            if sub in routes:
                return routes[sub]()

            if sub == "o":
                return admin_order_detail(ctx, user, chat_id, mid, int(param))
            if sub == "u":
                return admin_user_detail(ctx, user, chat_id, mid, param)
            if sub == "blk":
                return admin_toggle_block(ctx, user, chat_id, mid, param)
            if sub in ("bc", "find"):
                return admin_ask_input(ctx, user, chat_id, mid, sub)
            if sub in ("coin", "bal", "msg", "ask"):
                return admin_ask_input(ctx, user, chat_id, mid, sub, param)
            return None

        # دکمه‌های ادمین در گروه مدیریت
        if action in ("ap", "rj"):
            if not ctx.is_admin(frm["id"]):
                return ctx.bot.answer_cb(cq["id"], "دسترسی ندارید", alert=True)
            if action == "ap":
                # نتیجه‌ی approve_order قبلاً دور ریخته می‌شد: نه
                # answer_cb زده می‌شد نه پیام گروه عوض می‌شد. یعنی
                # ادمین دکمه را می‌زد، هیچ اتفاقی نمی‌دید و همان رسید
                # با همان دکمه‌ها سر جایش می‌ماند — انگار تایید اصلاً
                # ثبت نشده. خطای واقعی پنل هم هیچ‌وقت دیده نمی‌شد.
                okp, res = approve_order(ctx, int(arg), frm["id"])
                # answer_cb بالای تابع یک‌بار مصرف شده، پس بازخورد را
                # با پیام واقعی می‌دهیم نه با پاسخ کال‌بک
                if okp:
                    try:
                        ctx.bot.edit_markup(chat_id, mid, keyboard=kb(
                            [[(f"✅ تایید شد — سفارش #{arg}", f"adm:o:{arg}")]]))
                    except TelegramError:
                        pass
                    ctx.bot.send(chat_id,
                                 f"✅ <b>سفارش #{arg} تایید شد</b>\n"
                                 "کانفیگ ساخته و برای مشتری ارسال شد.")
                elif res == ORDER_BUSY:
                    # نخ دیگری همین سفارش را برداشته. گفتن «ساخت
                    # ناموفق بود» ادمین را به تلاش دوباره تشویق
                    # می‌کند، درست وقتی که نباید.
                    ctx.bot.send(
                        chat_id,
                        f"⏳ سفارش #{arg} همین حالا از مسیر دیگری در حال "
                        "پردازش است — چند لحظه صبر کنید و وضعیتش را ببینید.")
                else:
                    ctx.bot.send(
                        chat_id,
                        f"❌ <b>ساخت کانفیگ سفارش #{arg} ناموفق بود</b>\n\n"
                        f"{esc(str(res))}\n\n"
                        "سفارش هنوز در صف بررسی است — بعد از رفع مشکل "
                        "دوباره تایید بزنید.")
                return None
            # از ادمین دلیل می‌پرسیم — رد بدون توضیح، مشتری را سردرگم
            # و عصبانی می‌کند و بار پشتیبانی را بالا می‌برد.
            ctx.db.set_state(frm["id"], "adm_reject", {"t": str(arg)})
            ctx.bot.send(
                chat_id,
                f"❌ <b>رد سفارش #{arg}</b>\n\n"
                "دلیل رد را بنویسید تا برای مشتری فرستاده شود.\n\n"
                "<i>یا یکی از دلیل‌های آماده را انتخاب کنید:</i>",
                keyboard=kb([
                    [("مبلغ نادرست", f"rjr:{arg}:amount")],
                    [("رسید ناخوانا", f"rjr:{arg}:unclear")],
                    [("رسید تکراری", f"rjr:{arg}:dup")],
                    [("رسید نامعتبر", f"rjr:{arg}:invalid")],
                    [("انصراف", f"adm:o:{arg}")],
                ]))
            return ctx.bot.answer_cb(cq["id"], "دلیل را انتخاب یا بنویسید")

        # دلیل آماده‌ی رد
        if action == "rjr":
            if not ctx.is_admin(frm["id"]):
                return ctx.bot.answer_cb(cq["id"], "دسترسی ندارید", alert=True)
            oid, _, code = arg.partition(":")
            reasons = {
                "amount": "مبلغ واریزی با مبلغ سفارش یکی نبود. "
                          "لطفاً دقیقاً همان مبلغ را واریز کنید.",
                "unclear": "تصویر رسید خوانا نبود. "
                           "یک عکس واضح‌تر یا متن پیامک بانک بفرستید.",
                "dup": "این رسید قبلاً برای سفارش دیگری استفاده شده است.",
                "invalid": "این رسید تأیید نشد. "
                           "اگر مطمئنید واریز کرده‌اید، به پشتیبانی پیام بدهید.",
            }
            ctx.db.clear_state(frm["id"])
            done = do_reject(ctx, int(oid), frm["id"],
                             reasons.get(code, "رسید تأیید نشد."))
            if not done:
                # دکمه‌ها را برمی‌داریم ولی ادمین باید بداند چرا
                # چیزی به مشتری نرفت
                ctx.bot.answer_cb(
                    cq["id"],
                    "رد نشد — یا کانفیگش ساخته شده یا قبلاً رد شده بود.",
                    alert=True)
            return ctx.bot.edit_markup(chat_id, mid, None)

    except (ValueError, TypeError):
        log.warning("callback نامعتبر: %s", data)
    return None


def do_reject(ctx, order_id, admin_tg_id, reason):
    """
    رد سفارش با دلیل مشخص و اطلاع‌رسانی به مشتری.

    مشتری باید بداند چرا رد شده و چه کاری بکند — وگرنه یا پیگیری
    نمی‌کند (فروش از دست می‌رود) یا با عصبانیت به پشتیبانی می‌زند.
    """
    # شرطی: سفارشی که کانفیگش ساخته شده رد نمی‌شود، و رد دوباره هم
    # پیام دوم به مشتری نمی‌فرستد.
    if not ctx.db.mark_rejected(order_id, admin_tg_id, reason):
        return False

    o = ctx.db.get_order(order_id)
    if not o:
        return False

    # سکه‌های رزروشده برمی‌گردند.
    #
    # قبلاً این‌جا بی‌قید add_coins صدا زده می‌شد، در حالی که سکه‌ای
    # کم نشده بود — یعنی هر سفارشی که رد می‌شد، به مشتری سکه‌ی
    # رایگان می‌داد. حالا فقط چیزی که واقعاً رزرو شده آزاد می‌شود.
    _release_coins(ctx, order_id)

    u = ctx.db.get_user_by_id(o["user_id"])
    if not u:
        return False

    support = ctx.s.get("support_username") or ""
    tpl = ctx.s.get("reject_text")
    if tpl:
        txt = (tpl.replace("{order_id}", str(order_id))
                  .replace("{reason}", reason)
                  .replace("{support}", support))
    else:
        txt = (
            "❌ <b>رسیدتان تأیید نشد</b>\n\n"
            f"<b>دلیل:</b>\n{esc(reason)}\n\n"
        )
        if o.get("coins_used"):
            txt += (f"🪙 <b>{core.fa(o['coins_used'])}</b> سکه‌ای که خرج شده بود "
                    "به حسابتان برگشت.\n\n")
        txt += ("نگران نباشید — رسید درست را دوباره بفرستید تا سریع بررسی شود.\n\n"
                f"<i>کد پیگیری:</i> <code>#{order_id}</code>")

    rows = [[("🔄 ارسال مجدد رسید", f"retry:{order_id}")]]
    if support:
        rows.append([("🎧 پشتیبانی", f"https://t.me/{support.lstrip('@')}", "url")])
    rows.append([("‹ منوی اصلی", "menu")])

    try:
        ctx.bot.send(u["tg_id"], txt, keyboard=kb(rows))
    except TelegramError:
        pass

    # و همان خبر در صندوقِ مینی‌اپ.
    #
    # مشتری که از مینی‌اپ خریده، ممکن است گفتگوی ربات را باز نکند.
    # بدون این، رسیدش رد می‌شود و *دلیلش را هیچ‌وقت نمی‌بیند* — و
    # بعد از پشتیبانی می‌پرسد چرا. متن همان متنی است که مالک نوشته.
    try:
        ctx.db.chat_add(
            o["user_id"], "system",
            f"رسید سفارش #{order_id} تایید نشد.\n\nدلیل: {reason}",
            order_id=order_id)
    except Exception:
        log.warning("ثبت خبرِ رد در صندوق ناموفق", exc_info=True)

    return True


# ═══════════════════════════════════════════════════════════
#  توابع زمان‌بند
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
#  کانال
#
#  برگه: docs/specs/2026-09-19-channel.md
# ═══════════════════════════════════════════════════════════

#: سقفِ تلگرام. پیامِ متنی ۴۰۹۶، ولی کپشنِ عکس فقط ۱۰۲۴ —
#: متنی که بدونِ عکس می‌رفت، با افزودنِ عکس رد می‌شود.
TG_TEXT_LIMIT = 4096
TG_CAPTION_LIMIT = 1024


def channel_target(ctx):
    """
    کجا پست شود.

    `channel_id` تنظیمِ خودش را دارد و `force_channel` فقط
    پیش‌فرضش است: کانالِ عضویتِ اجباری لزوماً همان کانالی نیست که
    محتوا در آن می‌رود.
    """
    ch = str(ctx.s.get("channel_id") or "").strip()
    if not ch:
        ch = str(ctx.s.get("force_channel") or "").strip()
    if not ch:
        return ""
    # کانالِ خصوصی یوزرنیم ندارد و با شناسه‌ی عددیِ منفی کار می‌کند
    if ch.lstrip("-").isdigit():
        return ch
    return ch if ch.startswith("@") else "@" + ch.lstrip("@")


def channel_limit(has_photo):
    return TG_CAPTION_LIMIT if has_photo else TG_TEXT_LIMIT


def channel_problems(body, has_photo=False):
    """
    هر چه مانعِ رفتنِ این پست است — پیش از فرستادنش.

    اعتبارسنجِ HTML همان `fmt.check` است که `tg.send` هم از آن رد
    می‌شود. نسخه‌ی دومی نوشته نمی‌شود: یک قاعده در دو جا، پرتکرارترین
    باگِ این مخزن.
    """
    out = []
    text = str(body or "")
    if not text.strip():
        out.append("متنِ پست خالی است")
    cap = channel_limit(has_photo)
    if len(text) > cap:
        out.append(f"متن {core.fa(len(text))} کاراکتر است؛ سقف "
                   f"{core.fa(cap)}" + (" (چون عکس دارد)" if has_photo else ""))
    try:
        from fmt import check as _fmt_check
        out += _fmt_check(text)
    except ImportError:
        pass
    return out


def channel_photo_save(blob, ext=".jpg"):
    """
    عکس را کنارِ دیتابیسِ ربات ذخیره می‌کند و نامش را برمی‌گرداند.

    نام تصادفی است، پس خودش کلیدِ دسترسی است — مثل عکسِ گفتگو.
    """
    import secrets as _sc
    d = core.channel_photo_dir()
    d.mkdir(parents=True, exist_ok=True)
    name = _sc.token_hex(16) + (ext if ext.startswith(".") else "." + ext)
    (d / name).write_bytes(blob)
    return name


def channel_photo_bytes(name):
    """
    بایت‌های عکسِ یک پست.

    نامِ آمده از بیرون هرگز مستقیم به مسیر نمی‌چسبد.
    """
    n = str(name or "").rsplit("/", 1)[-1]
    if not n or "\\" in n or ".." in n:
        return None
    p = core.channel_photo_dir() / n
    try:
        return p.read_bytes() if p.is_file() else None
    except OSError:
        return None


def channel_send(ctx, post, photo_bytes=None):
    """
    ارسالِ یک پست. برمی‌گرداند (ok, message_id یا دلیلِ خطا).

    تنها مسیرِ رفتنِ پست به کانال — پنل و زمان‌بند هر دو از همین
    می‌گذرند، پس ادعا و سنجش و پیامِ خطا یک جا می‌مانند.
    """
    where = channel_target(ctx)
    if not where:
        return False, "آدرس کانال تنظیم نشده است"

    body = str(post.get("body") or "")
    bad = channel_problems(body, has_photo=bool(photo_bytes))
    if bad:
        return False, " · ".join(bad[:3])

    try:
        if photo_bytes:
            r = ctx.bot.send_photo_bytes(where, photo_bytes, filename="post.jpg",
                                         caption=body)
        else:
            r = ctx.bot.send(where, body, preview=True)
        return True, int((r or {}).get("message_id") or 0)
    except Exception as e:
        # یک شاخه، و تشخیص از روی *متن* نه از روی کلاسِ استثنا.
        #
        # `handlers` با `from tg import TelegramError` برمی‌دارد و
        # `run.py` با `from bot.tg import …` — دو شیءِ کلاسِ جدا که
        # فقط اسمشان یکی است. با `except TelegramError` خطا از
        # شاخه‌ی مخصوصش رد می‌شد و مالک متنِ خامِ انگلیسی را می‌دید.
        return False, channel_error(e)


def channel_error(e):
    """
    خطای تلگرام به زبانی که مالک بتواند کاری با آن بکند.

    `Forbidden: bot is not a member of the channel chat` به کسی
    نمی‌گوید باید چه کند.
    """
    d = str(getattr(e, "description", "") or e)
    low = d.lower()
    if "not a member" in low or "chat not found" in low:
        return ("ربات در کانال نیست — اول اضافه‌اش کنید و ادمینش کنید، "
                "بعد دوباره بفرستید")
    if "not enough rights" in low or "need administrator" in low:
        return "ربات در کانال هست ولی اجازه‌ی ارسالِ پیام ندارد"
    if "chat_write_forbidden" in low:
        return "ارسال در این کانال برای ربات بسته است"
    if "too many requests" in low or "retry after" in low:
        return "تلگرام موقتاً محدودمان کرده — چند دقیقه دیگر دوباره بفرستید"
    if "message is too long" in low:
        return "متن برای تلگرام بلند است"
    return d[:200] or "ارسال ناموفق بود"


def send_expiry_notice(tenant, bot, sub, days_left):
    """یادآوری نزدیک‌شدن انقضا با دکمه‌ی تمدید."""
    ctx = Ctx(bot, tenant)
    if days_left <= 0:
        head = "⛔️ <b>اشتراکتان امروز تمام می‌شود</b>"
    elif days_left == 1:
        head = "⏰ <b>فقط یک روز تا پایان اشتراک</b>"
    else:
        head = f"⏰ <b>{core.fa(days_left)} روز تا پایان اشتراک</b>"

    # sub گاهی sqlite3.Row است و .get ندارد — با یک dict ساده کار
    # می‌کنیم تا sub_label بتواند مثل بقیه‌جا رفتارش را انجام دهد
    srow = {k: sub[k] for k in sub.keys()} if hasattr(sub, "keys") else dict(sub)
    label = ctx.sub_label(srow)

    # دکمه مستقیم همین اشتراک را تمدید می‌کند، نه «خرید» کلی —
    # وگرنه کاربر دوباره باید حدس بزند کدام را انتخاب کند.
    #
    # این یک خط قبلاً فقط در مسیرِ پیش‌فرض بود و مسیرِ متنِ سفارشی
    # `"buy"` می‌داد. یعنی هر مالکی که متن را عوض می‌کرد، بی‌آنکه
    # بداند دکمه‌ی هدفمند را هم از دست می‌داد.
    renew_cb = f"renew:{srow['id']}" if srow.get("id") else "mysubs"
    renew_kb = kb([[(f"🔄 تمدید · {label}", renew_cb)],
                   [("‹ منوی اصلی", "menu")]])

    tpl = ctx.s.get("expiry_text")
    if tpl:
        txt = (tpl.replace("{days}", str(max(days_left, 0)))
                  .replace("{plan}", esc(str(srow.get("plan_name") or "")))
                  .replace("{label}", esc(label)))
        _chat_notice(ctx, srow, txt)
        return ctx.bot.send(srow.get("tg_id"), txt, keyboard=renew_kb)

    txt = F.join(
        head,
        f"📦 {F.b(label)}",
        F.lines(
            "اگر تمدید نکنید، اتصالتان قطع می‌شود.",
            "تمدید یک دکمه است و کانفیگ فعلی‌تان " + F.b("همان می‌ماند") +
            " — لازم نیست چیزی را دوباره اضافه کنید.",
        ),
    )
    _chat_notice(ctx, srow, txt)
    try:
        bot.send(sub["tg_id"], txt, keyboard=renew_kb)
    except TelegramError as e:
        log.warning("یادآوری ارسال نشد (%s): %s", sub["tg_id"], e)


def send_traffic_notice(tenant, bot, sub, used_gb, total_gb):
    """
    هشدار «حجمت دارد تمام می‌شود».

    ستون notified_80p از ابتدا در جدول بود و دو جای کد صفرش می‌کردند،
    ولی هیچ‌جا پُرش نمی‌کرد — یعنی این هشدار هیچ‌وقت فرستاده نمی‌شد.
    مشتری حجمش تمام می‌شد، اتصالش می‌خوابید، و اولین خبری که می‌گرفت
    قطع‌شدن بود.

    برخلاف انقضا، حجم تاریخ ندارد: کسی ممکن است در یک شب تمامش کند.
    پس این هشدار روی درصد مصرف کار می‌کند، نه روی روز.
    """
    ctx = Ctx(bot, tenant)
    pct = min(100, int(used_gb * 100 / total_gb)) if total_gb else 0
    left_gb = max(0, round(total_gb - used_gb, 1))

    srow = {k: sub[k] for k in sub.keys()} if hasattr(sub, "keys") else dict(sub)
    label = ctx.sub_label(srow)

    # مثل `expiry_text` — همان سازوکار، تا مالک مجبور نشود یکی را
    # بتواند عوض کند و دیگری را نه.
    tpl = (ctx.s.get("reminders") or {}).get("traffic_text")
    if tpl:
        txt = (tpl.replace("{used}", core.fa(used_gb))
                  .replace("{total}", core.fmt_gb(total_gb))
                  .replace("{left}", core.fa(left_gb))
                  .replace("{pct}", core.fa(pct))
                  .replace("{plan}", esc(str(srow.get("plan_name") or "")))
                  .replace("{label}", esc(label)))
        renew_cb = f"renew:{srow['id']}" if srow.get("id") else "mysubs"
        _chat_notice(ctx, srow, txt)
        return bot.send(srow.get("tg_id"), txt,
                        keyboard=kb([[(f"🔄 تمدید · {label}", renew_cb)],
                                     [("‹ منوی اصلی", "menu")]]))

    txt = F.join(
        F.title(f"{core.fa(pct)}٪ از حجمتان مصرف شده", "📊"),
        f"📦 {F.b(label)}",
        F.lines(
            F.row("مصرف‌شده", f"{core.fa(used_gb)} از {core.fmt_gb(total_gb)}", "💾"),
            F.row("باقی‌مانده", f"{core.fa(left_gb)} گیگ", "🟢"),
        ),
        F.quote("وقتی حجم تمام شود اتصال قطع می‌شود — حتی اگر تاریخ "
                "اشتراکتان هنوز باقی باشد."),
    )
    renew_cb = f"renew:{srow['id']}" if srow.get("id") else "mysubs"
    _chat_notice(ctx, srow, txt)
    try:
        bot.send(sub["tg_id"], txt,
                 keyboard=kb([[(f"🔄 تمدید · {label}", renew_cb)],
                              [("‹ منوی اصلی", "menu")]]))
    except TelegramError as e:
        log.warning("هشدار حجم ارسال نشد (%s): %s", sub["tg_id"], e)


def _renew_gave_up(ctx, sub, why):
    """
    تمدید خودکاری که اصلاً نمی‌تواند اجرا شود.

    یک بار به مشتری و گروه گفته می‌شود، نه هر ساعت.
    """
    n = ctx.db.renew_failed(sub["id"], max_hours=24)
    if n != 1:
        return
    user = ctx.db.get_user_by_id(sub["user_id"])
    if not user:
        return
    try:
        ctx.bot.send(
            user["tg_id"],
            F.join(
                F.title("تمدید خودکار انجام نشد", "⚠️"),
                why + ".",
                F.quote("برای اینکه اشتراکتان قطع نشود، دستی تمدید کنید "
                        "یا به پشتیبانی پیام بدهید."),
            ),
            keyboard=kb([[("📊 اشتراک‌های من", "mysubs")]]))
    except TelegramError:
        pass
    ctx.notify_group(
        f"⚠️ تمدید خودکار ممکن نیست\n👤 <code>{user['tg_id']}</code>\n"
        f"{esc(why)}", topic="alerts")


def _tell_renew_stuck(ctx, user, sub, plan):
    """بعد از چند شکست پیاپی، مشتری باید خودش دست به کار شود."""
    try:
        srow = {k: sub[k] for k in sub.keys()} if hasattr(sub, "keys") else dict(sub)
        ctx.bot.send(
            user["tg_id"],
            F.join(
                F.title("تمدید خودکار چند بار ناموفق بود", "⚠️"),
                F.lines(f"📦 {F.b(ctx.sub_label(srow, plan_name=plan['name']))}"),
                "پولی از کیف پولتان کم نشده.",
                F.quote("برای اینکه اشتراکتان قطع نشود، دستی تمدید کنید "
                        "یا به پشتیبانی پیام بدهید."),
            ),
            keyboard=kb([[("🔁 تمدید دستی", f"renew:{sub['id']}")],
                         [("📊 اشتراک‌های من", "mysubs")]]))
    except TelegramError:
        pass


def auto_renew_subscription(tenant, bot, sub):
    """
    تمدید خودکار از کیف پول.

    اگر موجودی کافی نباشد، فقط اطلاع می‌دهیم — تمدید خودکار خاموش
    نمی‌شود تا اگر کاربر شارژ کرد، دفعه‌ی بعد انجام شود.
    """
    ctx = Ctx(bot, tenant)
    plan = ctx.db.get_plan(sub["plan_id"]) if sub["plan_id"] else None
    if not plan:
        # پلن حذف شده. قبلاً این‌جا بی‌صدا برمی‌گشت: تمدید خودکار
        # روشن می‌ماند، هیچ‌وقت اجرا نمی‌شد، و مشتری تا لحظه‌ی قطع‌شدن
        # فکر می‌کرد پوشش دارد.
        _renew_gave_up(ctx, sub, "پلن این اشتراک دیگر موجود نیست")
        return

    user = ctx.db.get_user_by_id(sub["user_id"])
    if not user:
        return

    if user["balance"] < plan["price"]:
        try:
            short = plan["price"] - user["balance"]
            # نام پلن باید بیاید: کاربری که چند اشتراک دارد وگرنه
            # نمی‌داند کدامشان تمدید نشده و دنبال کدام باید بگردد
            srow = {k: sub[k] for k in sub.keys()} if hasattr(sub, "keys") else dict(sub)
            bot.send(user["tg_id"],
                     F.join(
                         F.title("تمدید خودکار انجام نشد", "⚠️"),
                         F.lines(
                             f"📦 {F.b(ctx.sub_label(srow, plan_name=plan['name']))}",
                             F.i(f"{core.fmt_gb(plan['gb'])} · "
                                 f"{core.fmt_days(plan['days'])}"),
                         ),
                         "موجودی کیف پولتان کافی نبود.",
                         F.lines(
                             F.row("لازم", core.toman(plan["price"]) + " تومان", "💰"),
                             F.row("موجودی", core.toman(user["balance"]) + " تومان", "👛"),
                             F.row("کسری", core.toman(short) + " تومان", "➖"),
                         ),
                         F.quote("کیف پول را شارژ کنید تا دفعه‌ی بعد خودکار "
                                 "انجام شود — تمدید خودکارتان هنوز روشن است."),
                     ),
                     keyboard=kb([[("👛 شارژ کیف پول", "wallet")],
                                  [("📊 اشتراک‌های من", "mysubs")]]))
        except TelegramError:
            pass
        return

    order = ctx.db.create_order(user["id"], plan["id"], plan["price"], plan["price"],
                                kind="renew", paid_from="wallet")

    # اتمی: زمان‌بند تمدید خودکار در نخ جداگانه‌ای می‌دود و قفل هر چت
    # آن را پوشش نمی‌دهد. یعنی می‌تواند دقیقاً هم‌زمان با خریدِ خود
    # کاربر اجرا شود و دو بار از یک موجودی بردارد.
    paid, left = ctx.db.spend_balance(
        user["id"], plan["price"], "renew",
        f"تمدید خودکار اشتراک #{sub['id']}", order["id"])
    if not paid:
        ctx.db.close_order(order["id"], "rejected", "موجودی کیف پول کافی نبود")
        log.info("تمدید خودکار اشتراک %s: موجودی کافی نبود (%s تومان)",
                 sub["id"], left)
        return

    # سفارش این‌جا approved *نمی‌شود*.
    #
    # قبلاً می‌شد، و اگر ساخت شکست می‌خورد پول برمی‌گشت ولی سفارش
    # approved می‌ماند — یعنی پولِ برگشته در آمار «فروش» شمرده
    # می‌شد. و تمدیدِ ناموفق رها نمی‌شود؛ با فاصله دوباره تلاش
    # می‌کند. پس یک اشتراکِ گیرکرده هر روز چند فروشِ خیالی به آمار
    # اضافه می‌کرد.
    ok, result = provision(ctx, order["id"])
    if ok:
        ctx.db.close_order(order["id"], "approved")
        ctx.db.renew_succeeded(sub["id"])

        # تمدید خودکار هم فروش است — همکار باید سهمش را بگیرد.
        # قبلاً فقط مسیر کارت پورسانت ثبت می‌کرد، پس همکاری که مشتری
        # آورده بود از تمدیدهای خودکار او هیچ نمی‌گرفت.
        _pay_commission(ctx, user, order["id"])

        # همان استدلال برای پاداش معرف. چون «یک پاداش برای هر دوست»
        # است، اگر خرید اولش قبلاً پاداش داده باشد این‌جا بی‌اثر است —
        # ولی دوستی که پیش از این اصلاً پاداشی نگرفته بود (چون اولین
        # خریدش با کیف پول بود) بالاخره حسابش صاف می‌شود.
        _reward_referrer(ctx, user, order["id"])

        # پرچم‌های یادآوری برای دوره‌ی جدید صفر می‌شوند
        ctx.db.exec(
            """UPDATE subscriptions
               SET notified_7d=0, notified_3d=0, notified_1d=0, notified_80p=0
               WHERE tenant_id=? AND id=?""",
            (ctx.tid, sub["id"])
        )
        try:
            srow2 = {k: sub[k] for k in sub.keys()} if hasattr(sub, "keys") else dict(sub)
            bot.send(user["tg_id"],
                     F.join(
                         F.title("اشتراکتان خودکار تمدید شد", "✅"),
                         F.lines(
                             f"📦 {F.b(ctx.sub_label(srow2, plan_name=plan['name']))}",
                             F.i(f"{core.fmt_gb(plan['gb'])} · "
                                 f"{core.fmt_days(plan['days'])}"),
                         ),
                         f"💰 {F.b(core.toman(plan['price']) + ' تومان')} "
                         "از کیف پول کم شد.",
                         F.quote("کاری لازم نیست بکنید — کانفیگ فعلی‌تان "
                                 "همان است و وصل می‌ماند."),
                     ),
                     keyboard=kb([[("📊 اشتراک‌های من", "mysubs")]]))
        except TelegramError:
            pass
        ctx.notify_group(f"🔁 تمدید خودکار\n👤 <code>{user['tg_id']}</code>\n"
                         f"💰 {core.toman(plan['price'])} تومان", topic="renewals")
    else:
        # پول برمی‌گردد و سفارش بسته می‌شود — با هم، وگرنه یکی از آن
        # دو جا می‌ماند. برگشت هم به سفارش گره می‌خورد؛ قبلاً
        # order_id نمی‌گرفت و در دفتر پیدا نمی‌شد.
        ctx.db.close_order(order["id"], "rejected",
                           "بازگشت وجه — تمدید خودکار ناموفق")

        # همان خطا هر ساعت تکرار می‌شود. بدون شمردن، گروه مدیریت
        # شبانه‌روز یک پیام را می‌گیرد و هشدارِ واقعیِ بعدی گم می‌شود.
        n = ctx.db.renew_failed(sub["id"])
        if n == 1 or n % 6 == 0:
            ctx.notify_group(
                f"⚠️ تمدید خودکار ناموفق (بار {core.fa(n)})\n"
                f"👤 <code>{user['tg_id']}</code>\n"
                f"خطا: {esc(str(result))}", topic="alerts")
        else:
            log.warning("تمدید خودکار اشتراک %s بار %s ناموفق: %s",
                        sub["id"], n, result)
        if n == 3:
            _tell_renew_stuck(ctx, user, sub, plan)


def send_daily_report(tenant):
    """گزارش روزانه در تاپیک آمار."""
    bot = Bot(tenant["bot_token"])
    ctx = Ctx(bot, tenant)
    s = ctx.db.stats()

    today = ctx.db.q(
        """SELECT COUNT(*) c, COALESCE(SUM(amount),0) sum FROM orders
           WHERE tenant_id=? AND status='approved' AND date(created_at)=date('now')""",
        (ctx.tid,), one=True
    )
    new_users = ctx.db.q(
        "SELECT COUNT(*) c FROM users WHERE tenant_id=? AND date(created_at)=date('now')",
        (ctx.tid,), one=True
    )

    txt = (f"📊 <b>گزارش امروز</b>\n\n"
           f"فروش   <b>{core.fa(today['c'])}</b> سفارش\n"
           f"درآمد   <b>{core.toman(today['sum'])}</b> تومان\n"
           f"کاربر جدید   <b>{core.fa(new_users['c'])}</b>\n\n"
           f"<b>در مجموع</b>\n"
           f"کاربران   {core.fa(s.get('users', 0))}\n"
           f"اشتراک فعال   {core.fa(s.get('active_subs', 0))}")
    ctx.notify_group(txt, topic="stats")
