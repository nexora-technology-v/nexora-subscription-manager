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
        t = self.tenant
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

    def notify_group(self, text, keyboard=None, topic=None):
        """ارسال به گروه مدیریت در تاپیک مشخص."""
        t = DB.get_tenant(self.tid)
        gid = t.get("admin_group_id")
        if not gid:
            return None
        try:
            topics = json.loads(t.get("topics") or "{}")
        except json.JSONDecodeError:
            topics = {}
        try:
            return self.bot.send(gid, text, keyboard=keyboard,
                                 topic_id=topics.get(topic))
        except TelegramError as e:
            log.warning("ارسال به گروه ناموفق: %s", e)
            return None


# ═══════════════════════════════════════════════════════════
#  منوها
# ═══════════════════════════════════════════════════════════

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

    if ctx.s.get("trial_enabled") and not user.get("trial_used"):
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
    pr = core.price_order(p["price"], coins=user["coins"], coin_cfg=cs, use_coins=True)
    has_coin_discount = pr["coin_discount"] > 0

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

    rows = []
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
        lines += ["", "💰 " + F.price(core.toman(p["price"]))]

    rows.append([(f"💳 خرید — {core.toman(p['price'])} تومان", f"chk:{plan_id}:0")])

    if user["balance"] >= p["price"]:
        lines.append("")
        lines.append(F.quote(
            "👛 موجودی کیف پولتان برای این خرید کافی است — با پرداخت از "
            "کیف پول، اشتراک " + F.b("بدون معطلی") + " تحویل می‌شود."))
        rows.append([("👛 پرداخت آنی از کیف پول", f"wpay:{plan_id}")])

    rows.append([("‹ بازگشت", "buy")])
    _reply(ctx, chat_id, message_id, "\n".join(lines), kb(rows))


def checkout(ctx, user, chat_id, message_id, plan_id, use_coins,
             renew_sub_id=None):
    """ساخت سفارش و نمایش اطلاعات کارت."""
    p = ctx.db.get_plan(plan_id)
    if not p:
        return _reply(ctx, chat_id, message_id,
                      "این پلن دیگر در دسترس نیست.\n\n"
                      "از لیست، یکی از پلن‌های فعال را انتخاب کنید.",
                      back_kb("buy"))

    cs = ctx.s.get("coins")
    pr = core.price_order(p["price"], coins=user["coins"], coin_cfg=cs,
                          use_coins=bool(use_coins))

    card = core.pick_card(ctx.s.get("cards"))
    if not card:
        return _reply(ctx, chat_id, message_id,
                      "راه پرداخت هنوز فعال نشده است.\n\n"
                      "یک پیام به پشتیبانی بدهید تا دستی برایتان انجام دهیم.",
                      back_kb())

    ttl = int(ctx.s.get("order_ttl_minutes") or 30)
    order = ctx.db.create_order(
        user["id"], plan_id, p["price"], pr["final"],
        coins_used=pr["coins_used"], ttl_minutes=ttl,
        # اگر تمدید است، مقصد از همین‌جا ثبت می‌شود — وگرنه provision
        # نمی‌داند کدام اشتراک را باید تمدید کند و کانفیگ تازه می‌سازد
        kind=("renew" if renew_sub_id else "new"),
        renew_sub_id=renew_sub_id,
    )

    # سکه همین حالا رزرو می‌شود، نه موقع تایید.
    #
    # اگر تا تایید صبر کنیم، مشتری می‌تواند چند سفارش با همان سکه‌ها
    # بسازد — چون هنوز کم نشده‌اند — و همه را تایید بگیرد. رزروکردن
    # این را ناممکن می‌کند و مسیر بازگشت سکه در «رد شدن» را هم درست
    # می‌کند، که تا امروز سکه‌ی رایگان می‌داد.
    if pr["coins_used"]:
        took, left = ctx.db.spend_coins(
            user["id"], pr["coins_used"], "hold",
            f"رزرو برای سفارش #{order['id']}", order_id=order["id"])
        if not took:
            ctx.db.exec(
                "UPDATE orders SET status='expired' WHERE tenant_id=? AND id=?",
                (ctx.tid, order["id"]))
            return _reply(ctx, chat_id, message_id,
                          "سکه‌های شما برای این تخفیف کافی نیست.\n\n"
                          f"موجودی: <b>{core.fa(left)}</b> سکه\n"
                          f"لازم: <b>{core.fa(pr['coins_used'])}</b> سکه\n\n"
                          "<blockquote>اگر همین الان سفارش دیگری ثبت "
                          "کرده‌اید، سکه‌هایتان آن‌جا رزرو شده‌اند."
                          "</blockquote>",
                          back_kb("buy"))
    ctx.db.exec("UPDATE orders SET card_used=?, status='pending' WHERE tenant_id=? AND id=?",
                (card.get("number"), ctx.tid, order["id"]))
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
    if pr["coin_discount"]:
        lines += [
            f"قیمت: <s>{core.toman(p['price'])}</s> تومان",
            f"🪙 تخفیف سکه: {core.fa(pr['coin_percent'])}٪ "
            f"({core.fa(pr['coins_used'])} سکه)",
        ]
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


def wallet_pay(ctx, user, chat_id, message_id, plan_id,
               renew_sub_id=None):
    """پرداخت مستقیم از کیف پول — بدون نیاز به تایید ادمین."""
    p = ctx.db.get_plan(plan_id)
    if not p:
        return _reply(ctx, chat_id, message_id,
                      "این پلن دیگر در دسترس نیست.", back_kb("buy"))

    fresh = ctx.db.get_user(user["tg_id"])
    if fresh["balance"] < p["price"]:
        short = p["price"] - fresh["balance"]
        return _reply(ctx, chat_id, message_id,
                      "موجودی کیف پولتان برای این پلن کافی نیست.\n\n"
                      f"موجودی: <b>{core.toman(fresh['balance'])}</b> تومان\n"
                      f"کسری: <b>{core.toman(short)}</b> تومان\n\n"
                      "می‌توانید کیف پول را شارژ کنید یا کارت‌به‌کارت بپردازید.",
                      back_kb("buy"))

    # کسر اول، سفارش بعد. اگر ترتیب برعکس باشد و کسر نگیرد، یک
    # سفارش بی‌پرداخت می‌ماند که هیچ‌کس بعداً نمی‌فهمد چه بوده.
    order = ctx.db.create_order(fresh["id"], plan_id, p["price"], p["price"],
                                paid_from="wallet",
                                kind=("renew" if renew_sub_id else "new"),
                                renew_sub_id=renew_sub_id)
    paid, left = ctx.db.spend_balance(fresh["id"], p["price"], "spend",
                                      f"خرید {p['name']}", order["id"])
    if not paid:
        # بین خواندن موجودی و این لحظه، پول جای دیگری خرج شده —
        # مثلاً تمدید خودکار همین کاربر که در نخ دیگری می‌دود.
        ctx.db.exec(
            "UPDATE orders SET status='rejected', "
            "reject_reason='موجودی کیف پول کافی نبود' "
            "WHERE tenant_id=? AND id=?", (ctx.tid, order["id"]))
        return _reply(ctx, chat_id, message_id,
                      "موجودی کیف پولتان کافی نیست.\n\n"
                      f"موجودی: <b>{core.toman(left)}</b> تومان\n"
                      f"لازم: <b>{core.toman(p['price'])}</b> تومان\n\n"
                      "<blockquote>اگر همین الان خرید دیگری انجام داده‌اید یا "
                      "تمدید خودکارتان اجرا شده، ممکن است موجودی تغییر کرده "
                      "باشد.</blockquote>",
                      back_kb("buy"))

    ok, result = provision(ctx, order["id"])
    if ok:
        # فروش با کیف پول هم فروش است — همکار باید سهمش را بگیرد
        _pay_commission(ctx, fresh, order["id"], p["price"])
        _reply(ctx, chat_id, message_id,
               f"✅ <b>{core.toman(p['price'])}</b> تومان از کیف پولتان کم شد.\n\n"
               "اشتراک آماده است — همین پایین برایتان فرستادیم.", None)
        deliver(ctx, fresh, result)
    else:
        # برگرداندن پول در صورت خطا
        ctx.db.add_balance(fresh["id"], p["price"], "refund",
                           "خطا در ساخت کانفیگ", order["id"])
        _reply(ctx, chat_id, message_id,
               "ساخت اشتراک به مشکل خورد و <b>مبلغ کامل به کیف پولتان برگشت</b>.\n\n"
               f"<i>{esc(result)}</i>\n\n"
               "<blockquote>چند دقیقه دیگر دوباره امتحان کنید — اگر باز هم "
               "نشد، پشتیبانی همین را می‌بیند و پیگیری می‌کند."
               "</blockquote>",
               back_kb())


# ═══════════════════════════════════════════════════════════
#  دریافت رسید
# ═══════════════════════════════════════════════════════════

def handle_receipt(ctx, msg, user, state_data):
    order_id = state_data.get("order_id")
    order = ctx.db.get_order(order_id)

    if not order or order["status"] not in ("pending",):
        ctx.db.clear_state(user["tg_id"])
        return ctx.bot.send(user["tg_id"],
                            "این سفارش دیگر باز نیست — شاید قبلاً بررسی "
                            "یا لغو شده باشد.\n\n"
                            "وضعیتش را از «سفارش‌های من» ببینید.",
                            keyboard=main_menu(ctx, user))

    # بررسی مهلت
    if order.get("expires_at"):
        try:
            if datetime.fromisoformat(order["expires_at"]) < datetime.now():
                ctx.db.exec("UPDATE orders SET status='expired' WHERE tenant_id=? AND id=?",
                            (ctx.tid, order_id))
                _release_coins(ctx, order_id)
                ctx.db.clear_state(user["tg_id"])
                return ctx.bot.send(user["tg_id"],
                                    "⌛️ مهلت این سفارش تمام شد.\n\n"
                                    "اگر واریز کرده‌اید نگران نباشید — "
                                    "به پشتیبانی پیام بدهید تا دستی ثبت شود.\n"
                                    "وگرنه از «خرید اشتراک» یک سفارش تازه بسازید.",
                                    keyboard=main_menu(ctx, user))
        except ValueError:
            pass

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

    ctx.db.exec(
        """UPDATE orders SET status='awaiting', receipt_type=?, receipt_file=?,
                             receipt_text=? WHERE tenant_id=? AND id=?""",
        (rtype, rfile, rtext, ctx.tid, order_id)
    )
    ctx.db.clear_state(user["tg_id"])

    plan = ctx.db.get_plan(order["plan_id"])
    ctx.bot.send(
        user["tg_id"],
        _waiting_text(ctx, order_id),
        keyboard=_waiting_kb(ctx, order_id)
    )

    # اعلان به گروه مدیریت
    who = esc(user.get("first_name") or "بدون نام")
    if user.get("username"):
        who += f" · @{esc(user['username'])}"

    info = (
        f"🧾 <b>رسید جدید — سفارش #{order_id}</b>\n\n"
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

    buttons = kb([
        [("✅ تایید", f"ap:{order_id}"), ("❌ رد", f"rj:{order_id}")]
    ])

    t = DB.get_tenant(ctx.tid)
    gid = t.get("admin_group_id")
    if gid and rtype == "photo":
        try:
            topics = json.loads(t.get("topics") or "{}")
            ctx.bot.send_photo(gid, rfile, caption=info, keyboard=buttons,
                               topic_id=topics.get("receipts"))
            return
        except TelegramError as e:
            log.warning("ارسال عکس رسید ناموفق: %s", e)
    ctx.notify_group(info, keyboard=buttons, topic="receipts")


# ═══════════════════════════════════════════════════════════
#  تایید/رد سفارش و تحویل
# ═══════════════════════════════════════════════════════════

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


def _pay_commission(ctx, user, order_id, amount):
    """
    ثبت پورسانت همکار فروش برای یک فروش موفق.

    همه‌ی مسیرهای فروش این را صدا می‌زنند — کارت، کیف پول، و تمدید
    خودکار. قبلاً فقط مسیر کارت صدایش می‌زد، و همکاری که مشتری آورده
    بود از خریدهای کیف‌پولی و تمدیدهای خودکارِ همان مشتری سهمی
    نمی‌گرفت.

    ثبت دوباره ممکن نیست: جدول روی (مستاجر، سفارش) یکتاست، پس اگر
    تاییدی دو بار اجرا شود پورسانت دو بار حساب نمی‌شود.

    خطا این‌جا نباید تحویل کانفیگ را متوقف کند؛ فروش انجام شده و
    مشتری منتظر است.
    """
    try:
        res = DB.record_commission(ctx.tid, user["id"], order_id, amount or 0)
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

    def _mark_approved():
        ctx.db.exec(
            """UPDATE orders SET status='approved', reviewed_by=?,
                                 reviewed_at=CURRENT_TIMESTAMP
               WHERE tenant_id=? AND id=?""",
            (admin_tg_id, ctx.tid, order_id)
        )

    # شارژ کیف پول کانفیگ ندارد — فقط موجودی اضافه می‌شود
    if order.get("kind") == "topup":
        _mark_approved()
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
        ctx.db.exec("UPDATE orders SET admin_note=? WHERE tenant_id=? AND id=?",
                    (f"خطای ساخت: {result}", ctx.tid, order_id))
        return False, result

    _mark_approved()
    user = ctx.db.get_user_by_id(order["user_id"])

    # پورسانت همکار فروش — بعد از ساخت موفق کانفیگ، چون تا وقتی
    # کانفیگ تحویل نشده فروشی اتفاق نیفتاده
    _pay_commission(ctx, user, order_id, order["amount"] or 0)

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
    try:
        deliver(ctx, user, result)
    except Exception as e:
        log.exception("ارسال کانفیگ به مشتری ناموفق")
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

    prev = ctx.db.q(
        """SELECT COUNT(*) AS c FROM orders
           WHERE tenant_id=? AND user_id=? AND status='approved' AND id<>?""",
        (ctx.tid, user["id"], order_id), one=True
    )
    if (prev or {}).get("c", 0) > 0:
        return  # خرید اولش نبوده

    cs = core.coin_settings(ctx.s.get("coins"))
    amount = int(cs.get("per_referral") or 0)
    if amount <= 0:
        return

    ref = ctx.db.get_user_by_id(user["referred_by"])
    if not ref:
        return

    ctx.db.add_coins(ref["id"], amount, "referral",
                     f"خرید زیرمجموعه {user.get('first_name') or user['tg_id']}",
                     ref_user_id=user["id"], order_id=order_id)

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
    """ساخت یا تمدید کانفیگ در 3x-ui."""
    order = ctx.db.get_order(order_id)
    plan = ctx.db.get_plan(order["plan_id"]) if order.get("plan_id") else None
    if not plan:
        return False, "پلن این سفارش پیدا نشد"

    user = ctx.db.get_user_by_id(order["user_id"])
    t = DB.get_tenant(ctx.tid)
    inbound = plan.get("inbound_id") or t.get("default_inbound")
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

    prefix = ctx.s.get("email_prefix") or (t.get("name") or "nx")
    sub_base = ctx.s.get("sub_base_url")

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
                # ایمیل را هم می‌دهیم: در 3x-ui نسخه‌ی ۳ شناسه‌ی اصلی
                # کلاینت ایمیل است و جست‌وجو با آن مطمئن‌تر از uuid است
                ctx.xui.extend_subscription(sub["inbound_id"], sub["client_uuid"],
                                            plan["days"], plan["gb"],
                                            email=sub.get("client_email"))
                new_exp = _add_days_iso(sub["expires_at"], plan["days"])
                ctx.db.exec(
                    """UPDATE subscriptions SET expires_at=?, is_active=1,
                       notified_7d=0, notified_3d=0, notified_1d=0, notified_80p=0
                       WHERE tenant_id=? AND id=?""",
                    (new_exp, ctx.tid, sub["id"])
                )
                ctx.db.exec("UPDATE orders SET sub_id=? WHERE tenant_id=? AND id=?",
                            (sub["id"], ctx.tid, order_id))
                return True, {**sub, "expires_at": new_exp, "renewed": True}

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

        res = ctx.xui.create_subscription(
            inbound, email, plan["gb"], plan["days"],
            ip_limit=plan["ip_limit"], tg_id=user["tg_id"],
            sub_base_url=sub_base, inbound_ids=pl_inbounds
        )

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

    _send_delivery(ctx, user, "\n".join(lines), url)


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
            lines.append(f"⛔ {F.b(f'{core.fa(abs(d))} روز پیش')} منقضی شده")
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


def wallet_topup_amount(ctx, user, chat_id, message_id, amount):
    """ساخت سفارش شارژ و نمایش کارت."""
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return _reply(ctx, chat_id, message_id,
                      "این مبلغ خوانده نشد. یکی از مبلغ‌های آماده را انتخاب کنید.",
                      back_kb("wallet"))

    if not (10000 <= amount <= 50000000):
        return _reply(ctx, chat_id, message_id,
                      "مبلغ باید بین ۱۰ هزار تا ۵۰ میلیون تومان باشد.",
                      back_kb("wallet"))

    u = ctx.db.get_user(user["tg_id"])
    card = core.pick_card(ctx.s.get("cards"))
    if not card:
        return _reply(ctx, chat_id, message_id,
                      "هنوز شماره کارتی ثبت نشده.\n\n"
                      "<blockquote>از پنل، بخش «اتصال و تنظیمات»، کارت را "
                      "اضافه کنید.</blockquote>",
                      back_kb("wallet"))

    # plan_id خالی یعنی این سفارش شارژ است نه خرید پلن
    order = ctx.db.create_order(u["id"], None, amount, amount, kind="topup")

    ctx.db.set_state(u["id"], "await_receipt", {"order_id": order["id"]})

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

    order = ctx.db.create_order(u["id"], plan["id"], 0, 0, kind="new")
    ctx.db.exec("UPDATE orders SET status='approved', reviewed_at=CURRENT_TIMESTAMP "
                "WHERE tenant_id=? AND id=?", (ctx.tid, order["id"]))

    ok, result = provision(ctx, order["id"])
    if not ok:
        return _reply(ctx, chat_id, message_id,
                      "ساخت اشتراک تست به مشکل خورد.\n\n"
                      f"<i>{esc(result)}</i>\n\n"
                      "چند دقیقه دیگر دوباره امتحان کنید — "
                      "تست رایگانتان هنوز محفوظ است.", back_kb())

    ctx.db.exec("UPDATE users SET trial_used=1 WHERE tenant_id=? AND id=?",
                (ctx.tid, u["id"]))
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
                    except Exception:
                        pass
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
        except Exception:
            pass

        return _reply(ctx, chat_id, None,
                      f"✅ پاسخ تیکت <code>#{target}</code> برای مشتری رفت.",
                      kb([[("‹ منوی مدیریت", "admin")]]))

    if kind == "reject" and target:
        do_reject(ctx, int(target), user["tg_id"], txt or "رسید تأیید نشد.")
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
    elif arg:
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
            do_reject(ctx, int(oid), frm["id"],
                      reasons.get(code, "رسید تأیید نشد."))
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
    ctx.db.exec(
        "UPDATE orders SET status='rejected', reviewed_by=?, admin_note=?, "
        "reviewed_at=CURRENT_TIMESTAMP WHERE tenant_id=? AND id=?",
        (admin_tg_id, reason, ctx.tid, order_id))

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
    return True


# ═══════════════════════════════════════════════════════════
#  توابع زمان‌بند
# ═══════════════════════════════════════════════════════════

def send_expiry_notice(tenant, bot, sub, days_left):
    """یادآوری نزدیک‌شدن انقضا با دکمه‌ی تمدید."""
    ctx = Ctx(bot, tenant)
    if days_left <= 0:
        head = "⛔️ <b>اشتراکتان امروز تمام می‌شود</b>"
    elif days_left == 1:
        head = "⏰ <b>فقط یک روز تا پایان اشتراک</b>"
    else:
        head = f"⏰ <b>{core.fa(days_left)} روز تا پایان اشتراک</b>"

    tpl = ctx.s.get("expiry_text")
    if tpl:
        txt = (tpl.replace("{days}", str(max(days_left, 0)))
                  .replace("{plan}", esc(str(sub.get("plan_name") or ""))))
        return ctx.bot.send(
            sub["tg_id"] if "tg_id" in sub.keys() else sub.get("tg_id"),
            txt, keyboard=kb([[("♻️ تمدید اشتراک", "buy")], [("‹ منو", "menu")]]))

    # sub گاهی sqlite3.Row است و .get ندارد — با یک dict ساده کار
    # می‌کنیم تا sub_label بتواند مثل بقیه‌جا رفتارش را انجام دهد
    srow = {k: sub[k] for k in sub.keys()} if hasattr(sub, "keys") else dict(sub)
    label = ctx.sub_label(srow)

    txt = F.join(
        head,
        f"📦 {F.b(label)}",
        F.lines(
            "اگر تمدید نکنید، اتصالتان قطع می‌شود.",
            "تمدید یک دکمه است و کانفیگ فعلی‌تان " + F.b("همان می‌ماند") +
            " — لازم نیست چیزی را دوباره اضافه کنید.",
        ),
    )
    # دکمه مستقیم همین اشتراک را تمدید می‌کند، نه «خرید» کلی —
    # وگرنه کاربر دوباره باید حدس بزند کدام را انتخاب کند.
    renew_cb = f"renew:{srow['id']}" if srow.get("id") else "mysubs"
    try:
        bot.send(sub["tg_id"], txt,
                 keyboard=kb([[(f"🔄 تمدید · {label}", renew_cb)],
                              [("‹ منوی اصلی", "menu")]]))
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
    try:
        bot.send(sub["tg_id"], txt,
                 keyboard=kb([[(f"🔄 تمدید · {label}", renew_cb)],
                              [("‹ منوی اصلی", "menu")]]))
    except TelegramError as e:
        log.warning("هشدار حجم ارسال نشد (%s): %s", sub["tg_id"], e)


def auto_renew_subscription(tenant, bot, sub):
    """
    تمدید خودکار از کیف پول.

    اگر موجودی کافی نباشد، فقط اطلاع می‌دهیم — تمدید خودکار خاموش
    نمی‌شود تا اگر کاربر شارژ کرد، دفعه‌ی بعد انجام شود.
    """
    ctx = Ctx(bot, tenant)
    plan = ctx.db.get_plan(sub["plan_id"]) if sub["plan_id"] else None
    if not plan:
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
        ctx.db.exec(
            "UPDATE orders SET status='rejected', "
            "reject_reason='موجودی کیف پول کافی نبود' "
            "WHERE tenant_id=? AND id=?", (ctx.tid, order["id"]))
        log.info("تمدید خودکار اشتراک %s: موجودی کافی نبود (%s تومان)",
                 sub["id"], left)
        return
    ctx.db.exec("UPDATE orders SET status='approved' WHERE tenant_id=? AND id=?",
                (ctx.tid, order["id"]))

    ok, result = provision(ctx, order["id"])
    if ok:
        # تمدید خودکار هم فروش است — همکار باید سهمش را بگیرد.
        # قبلاً فقط مسیر کارت پورسانت ثبت می‌کرد، پس همکاری که مشتری
        # آورده بود از تمدیدهای خودکار او هیچ نمی‌گرفت.
        _pay_commission(ctx, user, order["id"], plan["price"])

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
        # پول برمی‌گردد تا کاربر ضرر نکند
        ctx.db.add_balance(user["id"], plan["price"], "refund",
                           "بازگشت وجه — تمدید خودکار ناموفق")
        ctx.notify_group(f"⚠️ تمدید خودکار ناموفق\n👤 <code>{user['tg_id']}</code>\n"
                         f"خطا: {esc(str(result))}", topic="alerts")


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
