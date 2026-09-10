"""
پیش‌نمایش متن‌های ربات — همان‌طور که مشتری در تلگرام می‌بیند.

بعد از هر بازنویسی متن، این را اجرا کنید و خروجی را بخوانید.
تست نیست؛ ابزار چشمی است تا لحن و فاصله‌گذاری قبل از تحویل دیده شود.

اجرا:  python3 bot/preview_texts.py
"""
import html
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["BOT_DB_PATH"] = tempfile.mktemp(suffix=".db")

from bot import db                # noqa: E402
import bot.tg as tgmod            # noqa: E402
import bot.handlers as H          # noqa: E402

SENT = []


class FakeBot:
    def __init__(self, token=None):
        self.token = token

    def send(self, chat_id, text, keyboard=None, **kw):
        SENT.append({"text": text, "kb": keyboard})
        return {"message_id": len(SENT), "chat": {"id": chat_id}}

    def edit(self, chat_id, message_id, text, keyboard=None, **kw):
        SENT.append({"text": text, "kb": keyboard})
        return {"message_id": message_id}

    def edit_markup(self, *a, **k):
        return {}

    def answer_cb(self, *a, **k):
        return True

    def send_photo(self, chat_id, photo, caption=None, keyboard=None, **kw):
        SENT.append({"text": caption or "[عکس]", "kb": keyboard})
        return {"message_id": len(SENT)}

    def copy(self, *a, **k):
        return {"message_id": 1}

    def send_doc(self, *a, **k):
        return {"message_id": 1}

    def member_status(self, *a, **k):
        return "member"

    def me(self):
        return {"username": "NexoraBot"}


class FakeXUI:
    def __init__(self, *a, **kw):
        pass

    def create_subscription(self, inbound_id, email, gb, days, ip_limit=2,
                            tg_id=None, sub_base_url=None, inbound_ids=None):
        return {"email": email, "uuid": "u1", "sub_id": email,
                "sub_url": f"https://sub.nexora.ir/sub/{email}",
                "configs": [], "expiry_ms": 1800000000000, "gb": gb}

    def extend_subscription(self, *a, **k):
        return {"ok": True, "expiry_ms": 1800000000000}

    def client_traffic(self, email):
        # ۱۸.۴ گیگ از ۵۰ گیگ مصرف شده — تا نوار مصرف واقعی دیده شود
        return {"email": email, "up": 4 * 1024 ** 3,
                "down": int(14.4 * 1024 ** 3), "total": 0}

    def find_client(self, *a, **k):
        return {"id": "u1"}

    def ping(self):
        return True


tgmod.Bot = FakeBot
H.Bot = FakeBot
H.XUI = FakeXUI

db.init_db()

tid = db.create_tenant("Nexora", bot_token="1:T", owner_tg_id=999)
db.update_tenant(tid, panel_url="http://127.0.0.1:2053", panel_user="a",
                 panel_pass="a", admin_group_id=-100123,
                 topics=json.dumps({"receipts": 2, "users": 3, "stats": 4}))
db.save_tenant_settings(tid, {
    "brand": "نکسورا",
    "cards": [{"number": "6037997512345678", "holder": "علی قلعه‌دوز",
               "bank": "ملی", "active": True}],
    "trial_enabled": True,
    "coins": {"per_referral": 10},
    "inbound_id": 1,
    "support_username": "@nexora_support",
})

D = db.TenantDB(tid)
D.exec("""INSERT INTO plans (tenant_id,name,price,gb,days,ip_limit,inbound_id,
                             description,sort_order)
          VALUES (?,?,?,?,?,?,?,?,?)""",
       (tid, "یک‌ماهه پرسرعت", 190_000, 50, 30, 2, 1,
        "مناسب استفاده‌ی روزمره و تماشای ویدیو.", 1))
plan = D.plans()[0]

tenant = db.get_tenant(tid)
bot = FakeBot()

BOX = 62


def render(title, text, kb=None):
    """نمایش پیام همان‌طور که در تلگرام دیده می‌شود."""
    print(f"\n\033[38;5;245m{'─' * BOX}\033[0m")
    print(f"\033[38;5;117m{title}\033[0m")
    print(f"\033[38;5;245m{'─' * BOX}\033[0m")

    t = text or "(خالی)"
    # تگ‌های تلگرام را به شکل خوانا در ترمینال درمی‌آوریم
    t = re.sub(r"</?b>", "\033[1m" if True else "", t)
    t = t.replace("\033[1m", "\033[1m", 1)
    t = re.sub(r"<b>", "\033[1m", text or "")
    t = re.sub(r"</b>", "\033[0m", t)
    t = re.sub(r"<i>", "\033[3;38;5;245m", t)
    t = re.sub(r"</i>", "\033[0m", t)
    t = re.sub(r"<code>", "\033[38;5;222m", t)
    t = re.sub(r"</code>", "\033[0m", t)
    t = re.sub(r"</?s>", "", t)
    print(html.unescape(t))

    if kb:
        try:
            rows = json.loads(kb).get("inline_keyboard", [])
        except (TypeError, ValueError, AttributeError):
            rows = kb if isinstance(kb, list) else []
        for row in rows:
            labels = " | ".join(b.get("text", "") for b in row)
            print(f"\033[38;5;108m[ {labels} ]\033[0m")


def up_msg(tg_id, text):
    return {"message": {"message_id": 1, "text": text,
                        "chat": {"id": tg_id, "type": "private"},
                        "from": {"id": tg_id, "first_name": "علی",
                                 "is_bot": False}}}


def up_cb(tg_id, data):
    return {"callback_query": {"id": "c", "data": data,
                               "from": {"id": tg_id, "first_name": "علی",
                                        "is_bot": False},
                               "message": {"message_id": 1,
                                           "chat": {"id": tg_id}}}}


def shot(title, update):
    SENT.clear()
    H.dispatch(tenant, bot, update)
    for m in SENT:
        if m["text"]:
            render(title, m["text"], m.get("kb"))
            title = title + " (ادامه)"


print("\n\033[1m پیش‌نمایش متن‌های ربات نکسورا \033[0m")

shot("۱. خوش‌آمد / منوی اصلی", up_msg(555, "/start"))
D.exec("UPDATE users SET phone='989120000000' WHERE tenant_id=? AND tg_id=?",
       (tid, 555))
shot("۱. خوش‌آمد / منوی اصلی", up_msg(555, "/start"))
shot("۲. لیست پلن‌ها", up_cb(555, "buy"))
shot("۳. جزئیات پلن", up_cb(555, f"plan:{plan['id']}"))
shot("۴. سفارش و کارت‌به‌کارت", up_cb(555, f"chk:{plan['id']}:0"))
shot("۵. بعد از فرستادن رسید", up_msg(555, "واریز شد، ۱۹۰ هزار تومان"))

order = D.q("SELECT * FROM orders WHERE tenant_id=? ORDER BY id DESC LIMIT 1",
            (tid,), one=True)
ctx = H.Ctx(bot, tenant)
SENT.clear()
H.approve_order(ctx, order["id"], 999)
for m in SENT:
    if m["text"] and "تحویل" not in str(m["text"]):
        render("۶. تحویل اشتراک", m["text"], m.get("kb"))
        break

shot("۷. اشتراک‌های من", up_cb(555, "mysubs"))
shot("۸. کیف پول", up_cb(555, "wallet"))
shot("۹. سکه‌ها", up_cb(555, "coins"))
shot("۱۰. دعوت دوستان", up_cb(555, "ref"))
shot("۱۱. سفارش‌های من", up_cb(555, "myorders"))
shot("۱۲. آموزش نصب", up_cb(555, "help"))
shot("۱۳. پشتیبانی", up_cb(555, "support"))

SENT.clear()
H.do_reject(ctx, order["id"], 999, "تصویر رسید خوانا نبود. "
            "یک عکس واضح‌تر یا متن پیامک بانک بفرستید.")
for m in SENT:
    render("۱۴. رد شدن رسید", m["text"], m.get("kb"))
    break

sub = D.q("SELECT s.*, p.name AS plan_name, u.tg_id FROM subscriptions s "
          "LEFT JOIN plans p ON p.id=s.plan_id "
          "LEFT JOIN users u ON u.id=s.user_id "
          "WHERE s.tenant_id=? LIMIT 1", (tid,), one=True)
if sub:
    SENT.clear()
    H.send_expiry_notice(tenant, bot, sub, 3)
    for m in SENT:
        render("۱۵. یادآوری انقضا", m["text"], m.get("kb"))
        break

shot("۱۶. پنل مدیریت", up_cb(999, "admin"))

print(f"\n\033[38;5;245m{'─' * BOX}\033[0m")
print("پایان پیش‌نمایش.\n")
