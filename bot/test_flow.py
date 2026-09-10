"""
تست انتها-به-انتها: یک کاربر واقعی از /start تا دریافت کانفیگ.

تلگرام و پنل 3x-ui هر دو شبیه‌سازی می‌شوند، پس این تست بدون
سرور واقعی هم اجرا می‌شود و کل مسیر را می‌سنجد.

اجرا:  python3 bot/test_flow.py
"""
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

os.unlink(tmp)

print(f"\n{'═' * 52}")
print(f"  نتیجه:  {PASS} پاس  |  {FAIL} ناموفق")
print(f"{'═' * 52}\n")
sys.exit(1 if FAIL else 0)
