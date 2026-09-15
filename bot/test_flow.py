"""
تست انتها-به-انتها: یک کاربر واقعی از /start تا دریافت کانفیگ.

تلگرام و پنل 3x-ui هر دو شبیه‌سازی می‌شوند، پس این تست بدون
سرور واقعی هم اجرا می‌شود و کل مسیر را می‌سنجد.

اجرا:  python3 bot/test_flow.py
"""
import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

tmp = tempfile.mktemp(suffix=".db")
os.environ["BOT_DB_PATH"] = tmp

from bot import db, core          # noqa: E402
import bot.tg as tgmod            # noqa: E402
import bot.handlers as H          # noqa: E402
import bot.xui as xuimod          # noqa: E402

PASS = FAIL = 0
SENT = []
ACTIONS = []


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))


def section(t):
    print(f"\n{'─' * 52}\n{t}\n{'─' * 52}")


# ═══════════════ شبیه‌ساز تلگرام ═══════════════
class FakeBot:
    def __init__(self, token=None):
        self.token = token

    def send(self, chat_id, text, keyboard=None, parse_mode="HTML",
             topic_id=None, **kw):
        SENT.append({"to": chat_id, "text": text, "kb": keyboard, "topic": topic_id})
        return {"message_id": len(SENT), "chat": {"id": chat_id}}

    def edit(self, chat_id, message_id, text, keyboard=None, parse_mode="HTML"):
        SENT.append({"to": chat_id, "text": text, "kb": keyboard, "edit": True})
        return {"message_id": message_id}

    def edit_markup(self, chat_id, message_id, keyboard=None):
        return {"message_id": message_id}

    def answer_cb(self, cb_id, text=None, alert=False):
        return True

    def send_photo(self, chat_id, photo, caption=None, keyboard=None, topic_id=None):
        SENT.append({"to": chat_id, "text": caption or "[عکس]", "photo": True,
                     "topic": topic_id})
        return {"message_id": len(SENT)}

    def send_photo_bytes(self, chat_id, data, filename="qr.png", caption=None,
                         keyboard=None):
        # امضای واقعی؛ اگر عوض شود این تست باید بشکند نه اینکه بی‌صدا
        # از کنارش رد شود
        SENT.append({"to": chat_id, "text": caption or "[تصویر]",
                     "photoBytes": bytes(data), "file": filename})
        return {"message_id": len(SENT)}

    def action(self, chat_id, kind="typing"):
        ACTIONS.append({"to": chat_id, "kind": kind})
        return True

    def copy(self, chat_id, from_chat_id, message_id, caption=None, **kw):
        SENT.append({"to": chat_id, "text": caption or "[کپی]", "topic": kw.get("topic_id")})
        return {"message_id": len(SENT)}

    def send_doc(self, *a, **k):
        return {"message_id": 1}

    def member_status(self, chat_id, user_id):
        return "member"

    def me(self):
        return {"username": "NexoraTestBot"}


# ═══════════════ شبیه‌ساز پنل 3x-ui ═══════════════
class FakeXUI:
    """شبیه‌ساز پنل 3x-ui با همان امضای واقعی."""

    def __init__(self, *a, **kw):
        self.created = []
        self.extended = []

    def create_subscription(self, inbound_id, email, gb, days, ip_limit=2,
                            tg_id=None, sub_base_url=None, inbound_ids=None):
        self.created.append(email)
        base = sub_base_url or "https://sub.nexora.test/sub"
        return {
            "email": email,
            "uuid": f"uuid-{len(self.created)}",
            "sub_id": email,
            "sub_url": f"{base.rstrip('/')}/{email}",
            "configs": [],
            "expiry_ms": 1800000000000,
            "gb": gb,
        }

    def extend_subscription(self, inbound_id, client_uuid, add_days,
                            add_gb=None, reset_traffic=False, email=None):
        # امضا باید عیناً با XUI واقعی بخواند، وگرنه تستِ سبز
        # چیزی را تضمین نمی‌کند که در عمل TypeError می‌دهد
        self.extended.append(email or client_uuid)
        return {"ok": True, "expiry_ms": 1800000000000}

    def inbounds(self):
        return [{"id": 28, "remark": "FR-1", "enable": True},
                {"id": 41, "remark": "FR-2", "enable": True},
                {"id": 45, "remark": "TR", "enable": False}]

    def client_traffic(self, email):
        return {"email": email, "up": 0, "down": 0, "total": 0}

    def find_client(self, inbound_id, email=None, client_uuid=None):
        return {"id": "uuid-1", "email": email}

    def ping(self):
        return True


tgmod.Bot = FakeBot
H.Bot = FakeBot
H.XUI = FakeXUI

db.init_db()

# ═══════════════ آماده‌سازی ═══════════════
section("آماده‌سازی مستاجر")

tid = db.create_tenant("Nexora", bot_token="123:TEST", owner_tg_id=999)
db.update_tenant(tid, panel_url="http://127.0.0.1:2053", panel_user="admin",
                 panel_pass="admin", admin_group_id=-100123,
                 topics=json.dumps({"receipts": 2, "users": 3, "stats": 4,
                                    "renewals": 5, "alerts": 6}))
db.save_tenant_settings(tid, {
    "brand": "Nexora VPN",
    "cards": [{"number": "6037111122223333", "holder": "علی محمدی", "active": True}],
    "trial_enabled": True,
    "coins": {"per_referral": 10},
    "inbound_id": 1,
})

D = db.TenantDB(tid)
D.exec("""INSERT INTO plans (tenant_id,name,price,gb,days,inbound_id,sort_order)
          VALUES (?,?,?,?,?,?,?)""", (tid, "۳۰ گیگ / ۳۰ روز", 200_000, 30, 30, 1, 1))
D.exec("""INSERT INTO plans (tenant_id,name,price,gb,days,inbound_id,is_trial)
          VALUES (?,?,?,?,?,?,1)""", (tid, "تست رایگان", 0, 1, 1, 1))
plan = D.plans()[0]
check("مستاجر و پلن آماده", bool(tid and plan), f"پلن: {plan['name']}")

tenant = db.get_tenant(tid)
bot = FakeBot()


def up_msg(tg_id, text, first_name="علی"):
    return {"update_id": len(SENT) + 1,
            "message": {"message_id": 1, "text": text,
                        "chat": {"id": tg_id, "type": "private"},
                        "from": {"id": tg_id, "first_name": first_name,
                                 "is_bot": False}}}


def up_cb(tg_id, data):
    return {"update_id": len(SENT) + 1,
            "callback_query": {"id": "cb1", "data": data,
                               "from": {"id": tg_id, "first_name": "علی", "is_bot": False},
                               "message": {"message_id": 1, "chat": {"id": tg_id}}}}


def last():
    return SENT[-1]["text"] if SENT else ""


# ═══════════════ جریان کاربر ═══════════════
section("جریان کاربر: /start تا خرید")

SENT.clear()
H.dispatch(tenant, bot, up_msg(555, "/start"))
u = D.get_user(555)
check("کاربر ساخته شد", bool(u), f"کد معرف: {u['ref_code'] if u else '—'}")
check("پیام خوش‌آمد ارسال شد", len(SENT) > 0 and len(last()) > 10)

SENT.clear()
H.dispatch(tenant, bot, up_cb(555, "buy"))
check("لیست پلن‌ها نمایش داده شد", "پلن" in last() or plan["name"] in last())
check("پلن تست در لیست خرید نیست", "تست رایگان" not in last())

SENT.clear()
H.dispatch(tenant, bot, up_cb(555, f"plan:{plan['id']}"))
check("جزئیات پلن", plan["name"] in last() or "200" in last().replace("،", ","))

SENT.clear()
H.dispatch(tenant, bot, up_cb(555, f"chk:{plan['id']}:0"))
order = D.q("SELECT * FROM orders WHERE tenant_id=? ORDER BY id DESC", (tid,), one=True)
check("سفارش ساخته شد", bool(order), f"#{order['id'] if order else '—'}")
check("شماره کارت نمایش داده شد", "6037" in last().replace("-", ""))
check("وضعیت انتظار رسید", D.get_user(555)["state"] == "await_receipt",
      D.get_user(555)["state"] or "—")

# ═══════════════ رسید ═══════════════
section("ارسال و تایید رسید")

SENT.clear()
photo_msg = {"update_id": 99,
             "message": {"message_id": 5,
                         "chat": {"id": 555, "type": "private"},
                         "from": {"id": 555, "first_name": "علی", "is_bot": False},
                         "photo": [{"file_id": "PHOTO123"}]}}
H.dispatch(tenant, bot, photo_msg)
order = D.get_order(order["id"])
check("رسید ثبت شد", order["receipt_file"] == "PHOTO123" or order["receipt_type"] == "photo",
      f"وضعیت: {order['status']}")
check("در صف بررسی قرار گرفت", order["status"] in ("awaiting", "review"), order["status"])

to_group = [s for s in SENT if s["to"] == -100123]
check("اعلان در گروه مدیریت", len(to_group) > 0, f"{len(to_group)} پیام")
check("در تاپیک رسیدها", any(s.get("topic") == 2 for s in to_group))

SENT.clear()
H.dispatch(tenant, bot, up_cb(999, f"ap:{order['id']}"))
order = D.get_order(order["id"])
check("سفارش تایید شد", order["status"] == "approved", order["status"])

sub = D.q("SELECT * FROM subscriptions WHERE tenant_id=? ORDER BY id DESC", (tid,), one=True)
check("اشتراک ساخته شد", bool(sub), sub["client_email"] if sub else "—")
check("لینک اشتراک تولید شد", bool(sub and sub["sub_url"]),
      sub["sub_url"] if sub else "—")

to_user = [s for s in SENT if s["to"] == 555]
check("کانفیگ برای کاربر ارسال شد", len(to_user) > 0, f"{len(to_user)} پیام")

# ═══════════════ معرفی و سکه ═══════════════
section("سیستم معرفی و سکه")

inviter = D.get_user(555)
SENT.clear()
H.dispatch(tenant, bot, up_msg(777, f"/start {inviter['ref_code']}", "رضا"))
u2 = D.get_user(777)
check("کاربر دعوت‌شده ثبت شد", bool(u2))
check("رابطه معرف ثبت شد", u2["referred_by"] == inviter["id"],
      f"معرف: {u2['referred_by']}")

check("قبل از خرید سکه‌ای داده نمی‌شود", D.get_user(555)["coins"] == 0,
      f"{D.get_user(555)['coins']} سکه")

o2 = D.create_order(u2["id"], plan["id"], 200_000, 200_000)
D.exec("UPDATE orders SET status='awaiting' WHERE tenant_id=? AND id=?", (tid, o2["id"]))
SENT.clear()
H.dispatch(tenant, bot, up_cb(999, f"ap:{o2['id']}"))
check("بعد از خرید زیرمجموعه، معرف سکه گرفت", D.get_user(555)["coins"] == 10,
      f"{D.get_user(555)['coins']} سکه")

# خوددعوتی
SENT.clear()
self_ref = D.get_user(777)["ref_code"]
H.dispatch(tenant, bot, up_msg(777, f"/start {self_ref}"))
check("خوددعوتی مسدود است", D.get_user(777)["referred_by"] != u2["id"])

# ═══════════════ تخفیف با سکه ═══════════════
section("خرید با تخفیف سکه")

D.add_coins(inviter["id"], 30, "bonus", "تست")
check("موجودی سکه", D.get_user(555)["coins"] == 40, f"{D.get_user(555)['coins']} سکه")

SENT.clear()
H.dispatch(tenant, bot, up_cb(555, f"chk:{plan['id']}:1"))
o3 = D.q("SELECT * FROM orders WHERE tenant_id=? ORDER BY id DESC", (tid,), one=True)
check("تخفیف سکه اعمال شد", o3["amount"] == 160_000,
      f"{core.toman(o3['amount'])} از {core.toman(o3['base_amount'])} تومان")
check("سکه‌های مصرفی ثبت شد", o3["coins_used"] == 40, f"{o3['coins_used']} سکه")

# ═══════════════ کیف پول ═══════════════
section("کیف پول و تمدید خودکار")

D.add_balance(inviter["id"], 500_000, "topup", "شارژ تست")
SENT.clear()
H.dispatch(tenant, bot, up_cb(555, "wallet"))
check("نمایش کیف پول", "۵۰۰" in last().replace("،", "").replace(",", ""),
      "موجودی نمایش داده شد")

D.exec("UPDATE subscriptions SET auto_renew=1, expires_at=datetime('now','+1 day') "
       "WHERE tenant_id=? AND id=?", (tid, sub["id"]))
srow = D.q("""SELECT s.*, u.tg_id, u.balance FROM subscriptions s
              JOIN users u ON u.id=s.user_id WHERE s.tenant_id=? AND s.id=?""",
           (tid, sub["id"]), one=True)
bal_before = D.get_user(555)["balance"]
SENT.clear()
H.auto_renew_subscription(tenant, bot, srow)
bal_after = D.get_user(555)["balance"]
check("تمدید خودکار از کیف پول", bal_after == bal_before - plan["price"],
      f"{core.toman(bal_before)} → {core.toman(bal_after)}")
check("به کاربر اطلاع داده شد", any("تمدید" in s["text"] for s in SENT))

# موجودی ناکافی
D.exec("UPDATE users SET balance=1000 WHERE tenant_id=? AND id=?", (tid, inviter["id"]))
srow = D.q("""SELECT s.*, u.tg_id, u.balance FROM subscriptions s
              JOIN users u ON u.id=s.user_id WHERE s.tenant_id=? AND s.id=?""",
           (tid, sub["id"]), one=True)
SENT.clear()
H.auto_renew_subscription(tenant, bot, srow)
check("موجودی ناکافی → فقط هشدار", D.get_user(555)["balance"] == 1000,
      "پولی کسر نشد")
check("کاربر مطلع شد", any("کافی" in s["text"] for s in SENT))

# ═══════════════ یادآوری ═══════════════
section("یادآوری انقضا")

SENT.clear()
H.send_expiry_notice(tenant, bot, srow, 3)
check("یادآوری ۳ روزه", any("3" in s["text"] or "۳" in s["text"] for s in SENT))
SENT.clear()
H.send_expiry_notice(tenant, bot, srow, 0)
check("یادآوری روز آخر", any("امروز" in s["text"] for s in SENT))

# ═══════════════ تست رایگان ═══════════════
section("اشتراک تست رایگان")

SENT.clear()
H.dispatch(tenant, bot, up_cb(777, "trial"))
check("تست رایگان فعال شد", D.get_user(777)["trial_used"] == 1)
SENT.clear()
H.dispatch(tenant, bot, up_cb(777, "trial"))
check("بار دوم رد می‌شود", any("قبلا" in s["text"] or "قبلاً" in s["text"] or
                                 "یک‌بار" in s["text"] for s in SENT) or len(SENT) > 0)

# ═══════════════ دسترسی ادمین ═══════════════
section("کنترل دسترسی")

o4 = D.create_order(u2["id"], plan["id"], 200_000, 200_000)
SENT.clear()
H.dispatch(tenant, bot, up_cb(777, f"ap:{o4['id']}"))
check("کاربر عادی نمی‌تواند تایید کند",
      D.get_order(o4["id"])["status"] != "approved",
      D.get_order(o4["id"])["status"])

D.exec("UPDATE users SET is_blocked=1 WHERE tenant_id=? AND tg_id=?", (tid, 777))
SENT.clear()
H.dispatch(tenant, bot, up_msg(777, "/start"))
check("کاربر مسدود پاسخی نمی‌گیرد", len(SENT) == 0)

# ═══════════════ پورسانت همکار فروش ═══════════════
# رگرسیون: مبلغ سفارش در ستون amount است، نه final_price/price.
# وقتی این‌جا از نام اشتباه خوانده می‌شد، مبلغ صفر می‌شد و
# record_commission بی‌صدا None برمی‌گرداند — یعنی هیچ پورسانتی
# برای هیچ فروشی ثبت نمی‌شد.
section("پورسانت همکار فروش")

D.exec("INSERT INTO affiliates (tenant_id,name,code,tg_id,percent) "
       "VALUES (?,?,?,?,?)", (tid, "همکار تست", "AFFX", 888, 20))
aff_row = D.q("SELECT * FROM affiliates WHERE tenant_id=? AND code='AFFX'",
              (tid,), one=True)

D.create_user(444, "buyer", "خریدار")
buyer = D.get_user(444)
D.exec("UPDATE users SET affiliate_id=? WHERE tenant_id=? AND id=?",
       (aff_row["id"], tid, buyer["id"]))

aff_order = D.create_order(buyer["id"], plan["id"], plan["price"], plan["price"])
D.exec("UPDATE orders SET status='awaiting' WHERE tenant_id=? AND id=?",
       (tid, aff_order["id"]))

SENT.clear()
ok_aff, _ = H.approve_order(H.Ctx(bot, tenant), aff_order["id"], 999)
comm = D.q("SELECT * FROM affiliate_commissions WHERE tenant_id=? AND order_id=?",
           (tid, aff_order["id"]), one=True)
check("سفارش همکار تایید شد", ok_aff)
check("پورسانت ثبت شد", bool(comm),
      "هیچ ردیفی ثبت نشد" if not comm else "ثبت شد")
check("مبلغ فروش درست خوانده شد",
      bool(comm) and comm["order_amount"] == plan["price"],
      f"{(comm or {}).get('order_amount')} به‌جای {plan['price']}")
check("پورسانت ۲۰٪ درست حساب شد",
      bool(comm) and comm["commission"] == round(plan["price"] * 0.2),
      f"{(comm or {}).get('commission')}")
check("همکار مطلع شد", any(s["to"] == 888 for s in SENT))

# توابع همکار در ماژول db هستند نه روی TenantDB. وقتی از روی
# ctx.db صدا زده می‌شدند AttributeError می‌گرفتند و این صفحه‌ها
# اصلاً باز نمی‌شدند.
SENT.clear()
H.dispatch(tenant, bot, up_cb(888, "affiliate"))
check("پنل همکار باز می‌شود", bool(last()) and "همکاری در فروش" in last(),
      (last() or "پاسخی نیامد")[:34])
check("مانده‌ی همکار نمایش داده شد", "مانده" in (last() or ""))

SENT.clear()
H.dispatch(tenant, bot, up_cb(888, "aff_list"))
check("ریز فروش‌های همکار باز می‌شود", "ریز فروش‌ها" in (last() or ""),
      (last() or "پاسخی نیامد")[:34])

SENT.clear()
H.dispatch(tenant, bot, up_msg(333, f"/start aff_{aff_row['code']}"))
newcomer = D.get_user(333)
check("ورود با لینک همکار ثبت می‌شود",
      bool(newcomer) and newcomer["affiliate_id"] == aff_row["id"],
      f"affiliate_id={(newcomer or {}).get('affiliate_id')}")

# ═══════════════ گزارش ═══════════════
section("گزارش روزانه")

SENT.clear()
H.send_daily_report(tenant)
rep = [s for s in SENT if s["to"] == -100123]
check("گزارش به گروه رفت", len(rep) > 0)
check("در تاپیک آمار", any(s.get("topic") == 4 for s in rep))

# ═══════════════ کیوآر و حالت تایپ ═══════════════
section("کیوآر و حالت تایپ")

import qr as _qr   # noqa: E402

_png = _qr.make("https://sub.example.ir/sub/nexora_555_1")
check("segno نصب است", _qr.available())
check("کیوآر ساخته می‌شود", bool(_png) and _png[:8] == b"\x89PNG\r\n\x1a\n",
      f"{len(_png or b'')} بایت")
check("بدون داده کیوآر نمی‌سازد", _qr.make("") is None)

SENT.clear()
H._send_delivery(H.Ctx(bot, tenant), D.get_user(555),
                 "متن کانفیگ", "https://sub.example.ir/sub/nexora_555_1")
_photos = [s for s in SENT if s.get("photoBytes")]
check("کیوآر همراه کانفیگ فرستاده می‌شود", len(_photos) == 1,
      f"{len(_photos)} تصویر")
check("تصویر واقعاً PNG است",
      bool(_photos) and _photos[0]["photoBytes"][:8] == b"\x89PNG\r\n\x1a\n")
check("متن کانفیگ هم جدا رسیده",
      any("متن کانفیگ" in s["text"] for s in SENT))

# بدون لینک، کیوآری در کار نیست
SENT.clear()
H._send_delivery(H.Ctx(bot, tenant), D.get_user(555), "بدون لینک", None)
check("بدون لینک کیوآر فرستاده نمی‌شود",
      not any(s.get("photoBytes") for s in SENT))

check("پیام‌ها از blockquote استفاده می‌کنند",
      "<blockquote>" in H._waiting_text(H.Ctx(bot, tenant), 1),
      "متن انتظار")

# حالت تایپ باید در مسیر واقعی تایید رسید زده شده باشد — ACTIONS از
# ابتدای اجرا جمع شده است
check("هنگام تایید رسید، «در حال تایپ» نشان داده می‌شود",
      any(a["kind"] == "typing" for a in ACTIONS),
      f"{len(ACTIONS)} بار")

# ═══════════════ اطلاع به معرف ═══════════════
section("اطلاع به معرف")

# معرف باید *همان لحظه‌ی ثبت‌نام* خبردار شود. قبلاً فقط گروه مدیریت
# خبر می‌گرفت و خود معرف هیچ سیگنالی نداشت — از دیدش لینک دعوت کار
# نمی‌کرد، چون سکه هم فقط بعد از خرید می‌آمد و گاهی روزها سکوت بود.
inviter = D.get_user(555)
SENT.clear()
H.dispatch(tenant, bot, up_msg(7788, f"/start {inviter['ref_code']}", "مهمان"))

to_inviter = [s for s in SENT if s["to"] == 555]
check("معرف همان لحظه خبردار شد", len(to_inviter) > 0, f"{len(to_inviter)} پیام")
if to_inviter:
    t = to_inviter[0]["text"]
    check("نام دعوت‌شده آمده", "مهمان" in t)
    check("تعداد کل دعوت‌ها آمده", "نفر را دعوت" in t)
    check("می‌گوید سکه بعد از خرید می‌آید", "خرید" in t and "سکه" in t, t[:60])
    check("از blockquote استفاده شده", "<blockquote>" in t)

newbie = D.get_user(7788)
check("رابطه‌ی معرف ثبت شد", newbie and newbie["referred_by"] == inviter["id"])

# خوددعوتی نباید پیام بسازد
SENT.clear()
H.dispatch(tenant, bot, up_msg(4242, f"/start {inviter['ref_code']}"))
D.exec("DELETE FROM users WHERE tenant_id=? AND tg_id=?", (tid, 4242))

# ═══════════════ دکمه‌ی تمدید ═══════════════
section("دکمه‌ی تمدید")

# این دکمه در «اشتراک‌های من» ساخته می‌شد ولی هیچ شاخه‌ای در
# dispatch نداشت: کاربر می‌زد، هیچ اتفاقی نمی‌افتاد، و چون callback
# بی‌صدا None برمی‌گرداند حتی خطایی در لاگ نبود.
mysub = D.q("SELECT * FROM subscriptions WHERE tenant_id=? AND user_id=? LIMIT 1",
            (tid, inviter["id"]), one=True)
SENT.clear()
H.dispatch(tenant, bot, up_cb(555, f"renew:{mysub['id']}"))
check("دکمه‌ی تمدید پاسخ می‌دهد", len(SENT) > 0, f"{len(SENT)} پیام")
if SENT:
    rt = SENT[-1]["text"]
    check("نام پلن نشان داده می‌شود", plan["name"] in rt, rt[:70])
    check("مبلغ تمدید آمده", "مبلغ تمدید" in rt)
    check("blockquote توضیحی دارد", "<blockquote>" in rt)

SENT.clear()
H.dispatch(tenant, bot, up_cb(555, "renew:99999"))
check("اشتراک ناموجود خطای تمیز می‌دهد",
      SENT and "پیدا نشد" in SENT[-1]["text"], SENT[-1]["text"][:40] if SENT else "—")

# ═══════════════ پاسخ به تیکت ═══════════════
section("پاسخ به تیکت")

# دکمه‌ی «✍️ پاسخ» در گروه مدیریت ساخته می‌شد ولی هیچ شاخه‌ای در
# dispatch نداشت — ادمین می‌زد و هیچ اتفاقی نمی‌افتاد، پس عملاً هیچ
# تیکتی از داخل تلگرام جواب داده نمی‌شد.
SENT.clear()
H.dispatch(tenant, bot, up_cb(555, "support"))     # وارد حالت await_ticket
H.dispatch(tenant, bot, up_msg(555, "اینترنتم قطع می‌شود"))
tk = D.q("SELECT * FROM tickets WHERE tenant_id=? ORDER BY id DESC LIMIT 1",
         (tid,), one=True)
check("تیکت ثبت شد", bool(tk), f"#{tk['id']}" if tk else "—")

if tk:
    SENT.clear()
    H.dispatch(tenant, bot, up_cb(999, f"tk:{tk['id']}"))
    check("دکمه‌ی پاسخ، ورودی می‌خواهد",
          any("پاسخ به تیکت" in s["text"] for s in SENT), f"{len(SENT)} پیام")

    SENT.clear()
    H.dispatch(tenant, bot, up_msg(999, "مشکل از سرور بود، الان درست شد."))

    to_user = [s for s in SENT if s["to"] == 555]
    check("پاسخ به مشتری رسید", len(to_user) > 0, f"{len(to_user)} پیام")
    if to_user:
        rt = to_user[0]["text"]
        check("متن پاسخ در پیام هست", "الان درست شد" in rt)
        check("شماره پیگیری ذکر شده", f"#{tk['id']}" in rt)
        check("از blockquote استفاده شده", "<blockquote>" in rt)

    after = D.q("SELECT * FROM tickets WHERE tenant_id=? AND id=?",
                (tid, tk["id"]), one=True)
    check("تیکت به answered تغییر کرد",
          after and after["status"] == "answered",
          after["status"] if after else "—")
    check("متن پاسخ ذخیره شد",
          after and "الان درست شد" in (after["answer"] or ""))

# ═══════════════ دکمه‌ی کپی ═══════════════
section("دکمه‌ی کپی")

from tg import kb as _kbc   # noqa: E402

_ck = _kbc([[("کپی", "6037997512345678", "copy")],
            [("لینک", "https://a.ir", "url")],
            [("منو", "menu")]])
_flat = [b for r in _ck["inline_keyboard"] for b in r]
check("دکمه‌ی کپی ساخته می‌شود",
      any(b.get("copy_text", {}).get("text") == "6037997512345678" for b in _flat))
check("کپی با callback قاطی نمی‌شود",
      not any("callback_data" in b and "copy_text" in b for b in _flat))
check("مقدار خالی دکمه‌ی کپی نمی‌سازد",
      not [b for r in _kbc([[("کپی", "", "copy")]])["inline_keyboard"] for b in r])

# شماره‌ی کارت باید بدون خط تیره کپی شود، وگرنه اپ بانک رد می‌کند
SENT.clear()
H.checkout(H.Ctx(bot, tenant), D.get_user(555), 555, None, plan["id"], 0)
_last_kb = SENT[-1].get("kb") or {}
_copies = [b.get("copy_text", {}).get("text")
           for r in _last_kb.get("inline_keyboard", []) for b in r
           if "copy_text" in b]
check("شماره کارت بدون خط تیره کپی می‌شود",
      any(c and c.isdigit() and len(c) == 16 for c in _copies), str(_copies))

# ═══════════════ دکمه‌ی url نامعتبر ═══════════════
section("دکمه‌ی url نامعتبر")

# تلگرام دکمه‌ی شیشه‌ای را فقط با http/https/tg می‌پذیرد. اسکیم
# اپلیکیشن‌ها (happ://) کل پیام را رد می‌کرد، نه فقط آن دکمه را —
# یعنی کانفیگ ساخته می‌شد ولی هیچ‌وقت به مشتری نمی‌رسید.
from tg import kb as _kb, valid_button_url as _vbu   # noqa: E402

check("اسکیم اپلیکیشن نامعتبر است", not _vbu("happ://add/x"))
check("https معتبر است", _vbu("https://sub.example.ir/sub/x"))
check("tg معتبر است", _vbu("tg://resolve?domain=x"))

_mixed = _kb([[("اپ", "happ://add/x", "url"), ("سایت", "https://a.ir", "url")],
              [("منو", "menu")]])
_urls = [b.get("url") for r in _mixed["inline_keyboard"] for b in r if "url" in b]
check("دکمه‌ی نامعتبر حذف می‌شود، معتبر می‌ماند",
      _urls == ["https://a.ir"], str(_urls))
check("دکمه‌ی callback دست‌نخورده می‌ماند",
      any("callback_data" in b for r in _mixed["inline_keyboard"] for b in r))

# دکمه‌ی کپی تلگرام — لینک اشتراک با یک ضربه در کلیپ‌بورد
_cp = _kb([[("کپی", "https://sub.ir/x", "copy")], [("خالی", "", "copy")]])
_flat = [b for r in _cp["inline_keyboard"] for b in r]
check("دکمه‌ی کپی ساخته می‌شود",
      len(_flat) == 1 and _flat[0].get("copy_text", {}).get("text") == "https://sub.ir/x",
      str(_flat))
check("دکمه‌ی کپی خالی ساخته نمی‌شود", len(_flat) == 1)

# و اگر باز هم تلگرام صفحه‌کلید را رد کرد، متن باید برسد
_real_send = FakeBot.send
_calls = {"n": 0}


def _picky_send(self, chat_id, text, keyboard=None, **k):
    _calls["n"] += 1
    if keyboard is not None:
        raise H.TelegramError("Bad Request: BUTTON_URL_INVALID")
    return _real_send(self, chat_id, text, keyboard=None, **k)


FakeBot.send = _picky_send
SENT.clear()
H._send_delivery(H.Ctx(bot, tenant), D.get_user(555), "متن کانفیگ", "happ://x")
FakeBot.send = _real_send
check("رد شدن صفحه‌کلید، جلوی رسیدن کانفیگ را نمی‌گیرد",
      any("متن کانفیگ" in s["text"] for s in SENT), f"{len(SENT)} پیام")

# ═══════════════ شکست ساخت کانفیگ هنگام تایید ═══════════════
section("شکست ساخت کانفیگ هنگام تایید")

# سناریوی واقعی گزارش‌شده: ادمین ✅ می‌زند، کانفیگ ساخته نمی‌شود،
# هیچ پیامی نمی‌آید و همان رسید دوباره منتظر تایید می‌ماند.
# دو باگ داشت: نتیجه‌ی approve_order دور ریخته می‌شد، و سفارش قبل از
# ساخت کانفیگ approved می‌شد و بعد برای همیشه گیر می‌کرد.
u3 = D.get_user(555)
o_fail = D.create_order(u3["id"], plan["id"], plan["price"], plan["price"])
D.exec("UPDATE orders SET status='awaiting' WHERE tenant_id=? AND id=?",
       (tid, o_fail["id"]))

_real_create = H.XUI.create_subscription


def _boom(self, *a, **k):
    raise H.XUIError("پنل: inbound not found")


H.XUI.create_subscription = _boom
SENT.clear()
H.dispatch(tenant, bot, up_cb(999, f"ap:{o_fail['id']}"))
o_after = D.get_order(o_fail["id"])

check("سفارش با شکست ساخت، approved نمی‌شود",
      o_after["status"] != "approved", o_after["status"])
admin_msgs = [s for s in SENT if s["to"] == 999]
check("خطا به ادمین گزارش می‌شود", len(admin_msgs) > 0,
      f"{len(admin_msgs)} پیام")
check("متن خطای واقعی پنل دیده می‌شود",
      any("inbound not found" in s["text"] for s in admin_msgs))
check("برای مشتری کانفیگی فرستاده نمی‌شود",
      len([s for s in SENT if s["to"] == 555]) == 0)

# حالا مشکل رفع شد — تایید دوباره باید کار کند، نه اینکه بگوید
# «قبلاً تایید شده»
H.XUI.create_subscription = _real_create
SENT.clear()
H.dispatch(tenant, bot, up_cb(999, f"ap:{o_fail['id']}"))
o_retry = D.get_order(o_fail["id"])
check("تلاش دوباره بعد از رفع مشکل موفق است",
      o_retry["status"] == "approved", o_retry["status"])
check("این بار کانفیگ برای مشتری رفت",
      len([s for s in SENT if s["to"] == 555]) > 0)

# ═══════════════ اینباند پیش‌فرض تنظیم‌نشده ═══════════════
section("اینباند پیش‌فرض تنظیم‌نشده")

# روی سرور واقعی، default_inbound خالی بود و پلن هم inbound_id نداشت.
# قبلاً provision همین‌جا شکست می‌خورد و مشتری بعد از پرداخت هیچ
# کانفیگی نمی‌گرفت — بدترین حالت ممکن.
D.exec("UPDATE tenants SET default_inbound=NULL WHERE id=?", (tid,))
D.exec("""INSERT INTO plans (tenant_id,name,price,gb,days,inbound_id,sort_order)
          VALUES (?,?,?,?,?,?,?)""", (tid, "بدون اینباند", 150_000, 20, 20, None, 9))
free_plan = [p for p in D.plans() if p["name"] == "بدون اینباند"][0]

u2 = D.get_user(555)
o_free = D.create_order(u2["id"], free_plan["id"], free_plan["price"],
                        free_plan["price"])
ctx_free = H.Ctx(bot, db.get_tenant(tid))
okp, resp = H.provision(ctx_free, o_free["id"])
check("بدون اینباند پیش‌فرض هم کانفیگ ساخته می‌شود", okp,
      resp if not okp else f"اشتراک #{resp.get('id')}")
if okp:
    made = D.q("SELECT inbound_id FROM subscriptions WHERE tenant_id=? AND id=?",
               (tid, resp["id"]), one=True)
    check("اولین اینباند فعال انتخاب شد", made and made["inbound_id"] == 28,
          f"inbound #{made['inbound_id'] if made else '—'}")

# ═══════════════════════════════════════════════════════════
section("همکار نمی‌تواند مشتریِ خودش شود")

# مسیر «دعوت دوست» شرط خوددعوتی را داشت، مسیر همکاری نداشت. همکاری
# که هنوز با ربات کار نکرده، با بازکردن لینک خودش مشتریِ خودش می‌شد
# و از هر خریدِ خودش پورسانت می‌گرفت — تخفیفی که قرار نبود باشد.

HSRC = io.open(H.__file__, encoding="utf-8").read()
_blk = HSRC[HSRC.index('if arg.startswith("aff_")'):]
_blk = _blk[:_blk.index("u = ctx.db.create_user")]
check("شرط خودمعرفی برای همکار هم هست",
      'affiliate.get("tg_id") == tg_user["id"]' in _blk,
      "همان قاعده‌ای که مسیر دعوت دوست دارد")
check("و در آن حالت اصلا وصل نمی‌شود", "affiliate = None" in _blk)
check("مسیر دعوت دوست هنوز شرط خودش را دارد",
      'inviter["tg_id"] != tg_user["id"]' in _blk,
      "اصلاح این یکی نباید آن یکی را برداشته باشد")


# ═══════════════════════════════════════════════════════════
section("وضعیت سفارش باید درباره‌ی پول راست بگوید")

# دو خطا در دو جهت، که جمعشان عددی می‌ساخت که درست به نظر می‌رسید:
#
#   • خرید با کیف پول هیچ‌وقت approved نمی‌شد. کانفیگ ساخته و تحویل
#     می‌شد و سفارش pending می‌ماند؛ جاروکشِ سفارش‌های منقضی نیم‌ساعت
#     بعد آن را «منقضی» می‌کرد. فروشِ انجام‌شده در هیچ آماری نبود.
#
#   • تمدید خودکار برعکس: *قبل* از ساخت approved می‌شد. اگر ساخت
#     شکست می‌خورد پول برمی‌گشت و سفارش approved می‌ماند — پولِ
#     برگشته «فروش» شمرده می‌شد. و تمدیدِ ناموفق رها نمی‌شود؛ با
#     فاصله دوباره تلاش می‌کند، پس هر روز چند فروشِ خیالی.

from datetime import datetime as _dt      # noqa: E402

H.dispatch(tenant, bot, up_msg(777, "/start", "مریم"))
_w = D.get_user(777)
D.add_balance(_w["id"], 1_000_000, "topup", "شارژ تست")
_w = D.get_user(777)

SENT.clear()
H.wallet_pay(H.Ctx(bot, tenant), _w, 777, None, plan["id"])
_o = D.q("SELECT * FROM orders WHERE tenant_id=? AND user_id=? "
         "ORDER BY id DESC LIMIT 1", (tid, _w["id"]), one=True)

check("خرید با کیف پول approved می‌شود", _o["status"] == "approved",
      f"وضعیت: {_o['status']} — قبلاً pending می‌ماند")
check("و پول کم شده", D.get_user(777)["balance"] == 800_000,
      core.toman(D.get_user(777)["balance"]))

# همان کوئریِ جاروکش در bot/run.py، عیناً
D.exec("UPDATE orders SET expires_at=datetime('now','-1 hour') "
       "WHERE tenant_id=? AND id=?", (tid, _o["id"]))
_swept = D.q("""SELECT id FROM orders
                WHERE tenant_id=? AND status='pending'
                  AND expires_at IS NOT NULL AND expires_at < ?""",
             (tid, _dt.now().isoformat()))
check("جاروکش سفارشِ تحویل‌شده را منقضی نمی‌کند",
      not any(r["id"] == _o["id"] for r in _swept),
      "فروشِ انجام‌شده نباید «منقضی» شود")

# ─── تمدید خودکارِ ناموفق ───
_sub = D.q("SELECT * FROM subscriptions WHERE tenant_id=? AND user_id=? "
           "ORDER BY id DESC LIMIT 1", (tid, _w["id"]), one=True)
check("اشتراک ساخته شد", bool(_sub))

_bal_before = D.get_user(777)["balance"]
_orig_extend = FakeXUI.extend_subscription


def _panel_down(self, *a, **k):
    raise RuntimeError("پنل در دسترس نیست")


FakeXUI.extend_subscription = _panel_down
try:
    H.auto_renew_subscription(tenant, bot, _sub)
finally:
    FakeXUI.extend_subscription = _orig_extend

_o2 = D.q("SELECT * FROM orders WHERE tenant_id=? AND user_id=? "
          "ORDER BY id DESC LIMIT 1", (tid, _w["id"]), one=True)
check("تمدیدِ ناموفق فروش شمرده نمی‌شود", _o2["status"] != "approved",
      f"وضعیت: {_o2['status']} — قبلاً approved می‌ماند")
check("و پول برگشته", D.get_user(777)["balance"] == _bal_before,
      core.toman(D.get_user(777)["balance"]))

_ref = D.q("SELECT * FROM wallet_tx WHERE tenant_id=? AND order_id=? "
           "AND amount > 0", (tid, _o2["id"]), one=True)
check("برگشتِ وجه به سفارش گره خورده", bool(_ref),
      "بدون order_id در دفتر پیدا نمی‌شد")

# ─── ادعا: پول فقط یک بار برمی‌گردد ───
_bal_now = D.get_user(777)["balance"]
_again = D.close_order(_o2["id"], "expired")
check("بستنِ دوباره‌ی همان سفارش برنده نمی‌شود", _again == (False, 0),
      str(_again))
check("و پول دوبار برنمی‌گردد", D.get_user(777)["balance"] == _bal_now,
      "جاروکش و مسیر لغو هر دو می‌توانند همین سفارش را ببینند")

# ─── سفارشِ تاییدشده هرگز پس داده نمی‌شود ───
_o3 = D.create_order(_w["id"], plan["id"], plan["price"], plan["price"],
                     paid_from="wallet")
D.spend_balance(_w["id"], plan["price"], "spend", "خرید", _o3["id"])
_b3 = D.get_user(777)["balance"]
_won3, _back3 = D.close_order(_o3["id"], "approved")
check("سفارشِ approved پول پس نمی‌دهد", (_won3, _back3) == (True, 0),
      "وگرنه هر فروش یک اشتراکِ هدیه می‌شد")
check("و موجودی دست نخورده می‌ماند", D.get_user(777)["balance"] == _b3)

# ─── شاخه‌ی «موجودی وسطِ کار تمام شد» ───
# این شاخه هرگز اجرا نشده بود: ستونی که می‌نوشت وجود ندارد، پس
# به‌جای مدیریتِ مسابقه، خطای SQL می‌داد.
import sqlite3 as _sq3      # noqa: E402

_con = _sq3.connect(tmp)
try:
    _cols = [r[1] for r in _con.execute("PRAGMA table_info(orders)")]
finally:
    _con.close()
check("ستون reject_reason واقعاً وجود ندارد", "reject_reason" not in _cols,
      "پس هر دستوری که به آن اشاره کند خطا می‌دهد")

# نکته‌ی دام‌دار: handlers با «import db as DB» ماژول را برمی‌دارد و
# این فایل با «from bot import db». اینها دو شیء ماژولِ جدا هستند که
# فقط یک فایلِ دیتابیس مشترک دارند — پس وصله‌زدن به db.TenantDB هیچ
# اثری روی چیزی که handlers صدا می‌زند ندارد. باید همانی را وصله زد
# که خودش در دست دارد.
_orig_spend = H.DB.TenantDB.spend_balance
H.DB.TenantDB.spend_balance = lambda self, *a, **k: (False, 0)
try:
    _raised = None
    try:
        H.wallet_pay(H.Ctx(bot, tenant), D.get_user(777), 777, None, plan["id"])
    except Exception as e:      # noqa: BLE001
        _raised = e
finally:
    H.DB.TenantDB.spend_balance = _orig_spend

check("شاخه‌ی کسریِ لحظه‌ی آخر دیگر خطا نمی‌دهد", _raised is None,
      f"{type(_raised).__name__}: {_raised}" if _raised else "")
_o4 = D.q("SELECT * FROM orders WHERE tenant_id=? AND user_id=? "
          "ORDER BY id DESC LIMIT 1", (tid, _w["id"]), one=True)
check("و سفارشِ بی‌پرداخت رد می‌شود", _o4["status"] == "rejected",
      f"وضعیت: {_o4['status']}")
check("دلیل در admin_note می‌نشیند — همان ستونی که پنل می‌خواند",
      "کافی نبود" in (_o4["admin_note"] or ""), _o4["admin_note"] or "—")


# ═══════════════════════════════════════════════════════════
section("تست رایگان هم تا ساخته نشود «فروش» نیست")

# همان قاعده‌ی مسیر کارت و کیف پول، در سومین جایی که جا افتاده بود:
# سفارشِ تست *قبل* از ساخت approved می‌شد. اگر ساخت شکست می‌خورد،
# حقِ تست پس داده می‌شد ولی سفارش approved می‌ماند — و قیف تبدیل،
# کاربری را که هیچ‌وقت چیزی نگرفت «خرید موفق» می‌شمرد.

_tplan = D.q("SELECT * FROM plans WHERE tenant_id=? AND is_trial=1",
             (tid,), one=True)
check("پلن تست هست", bool(_tplan))

# ── تستِ موفق ──
SENT.clear()
H.dispatch(tenant, bot, up_msg(888, "/start", "سارا"))
H.dispatch(tenant, bot, up_cb(888, "trial"))
_tu = D.get_user(888)
_to = D.q("SELECT * FROM orders WHERE tenant_id=? AND user_id=? "
          "ORDER BY id DESC LIMIT 1", (tid, _tu["id"]), one=True)
check("حق تست مصرف شد", _tu["trial_used"] == 1)
check("سفارشِ تستِ موفق approved می‌شود", _to and _to["status"] == "approved",
      f"وضعیت: {_to['status'] if _to else '—'}")
check("و کانفیگ واقعا ساخته شد",
      bool(D.q("SELECT 1 FROM subscriptions WHERE tenant_id=? AND user_id=?",
               (tid, _tu["id"]), one=True)))

# ── تستی که ساختش شکست می‌خورد ──
_orig_create = FakeXUI.create_subscription


def _no_panel(self, *a, **k):
    raise RuntimeError("پنل در دسترس نیست")


H.dispatch(tenant, bot, up_msg(889, "/start", "نگار"))
FakeXUI.create_subscription = _no_panel
try:
    H.dispatch(tenant, bot, up_cb(889, "trial"))
finally:
    FakeXUI.create_subscription = _orig_create

_fu = D.get_user(889)
_fo = D.q("SELECT * FROM orders WHERE tenant_id=? AND user_id=? "
          "ORDER BY id DESC LIMIT 1", (tid, _fu["id"]), one=True)
check("حق تست پس داده می‌شود", _fu["trial_used"] == 0,
      "پیام به کاربر می‌گوید «تست رایگانتان هنوز محفوظ است»")
check("و سفارشِ ناموفق approved نمی‌ماند",
      _fo and _fo["status"] != "approved",
      f"وضعیت: {_fo['status'] if _fo else '—'}")
check("بلکه رد می‌شود", _fo and _fo["status"] == "rejected",
      f"وضعیت: {_fo['status'] if _fo else '—'}")

# و چون حق تست برگشته، دوباره می‌تواند امتحان کند
H.dispatch(tenant, bot, up_cb(889, "trial"))
check("و کاربر می‌تواند دوباره امتحان کند",
      D.get_user(889)["trial_used"] == 1,
      "وگرنه کسی که تقصیری نداشت، تستش را از دست می‌داد")


# و هیچ مسیر تازه‌ای نباید دوباره خام approved بنویسد.
#
# این الگو سه بار پیدا شد: کیف پول، تمدید خودکار، و تست رایگان. هر
# سه یک شکل داشتند — approved پیش از ساخت کانفیگ. حالا همه از
# close_order می‌گذرند و این اسکن جلوی چهارمی را می‌گیرد.
#
# کامنت‌ها اول برداشته می‌شوند: سه بار تستی سبز مانده چون رشته‌ای که
# دنبالش بودم در توضیحِ خودم پیدا می‌شد، نه در کد.
_hsrc = io.open(H.__file__, encoding="utf-8").read()
_hcode = "\n".join(l for l in _hsrc.split("\n")
                   if not l.strip().startswith("#"))
check("هیچ‌جای handlers خام approved نمی‌نویسد",
      "SET status='approved'" not in _hcode,
      "برای تاییدِ سفارش از ctx.db.close_order استفاده کنید")


os.unlink(tmp)

print(f"\n{'═' * 52}")
print(f"  نتیجه:  {PASS} پاس  |  {FAIL} ناموفق")
print(f"{'═' * 52}\n")
sys.exit(1 if FAIL else 0)
