#!/usr/bin/env python3
"""
کیف پول نباید منفی شود — حتی وقتی چند نخ هم‌زمان خرج می‌کنند.

چرا وجود دارد:
    الگوی قبلی «اول موجودی را بخوان، اگر کافی بود کم کن» بود:

        fresh = db.get_user(tg_id)
        if fresh["balance"] < price: return
        db.add_balance(user_id, -price, ...)

    بین آن دو خط هر اتفاقی می‌تواند بیفتد. و می‌افتد: ربات با هشت
    نخ کار می‌کند، و زمان‌بند تمدید خودکار در نخ جداگانه‌ای می‌دود که
    قفل هر چت پوششش نمی‌دهد. یعنی مشتری می‌تواند در حال خرید باشد و
    هم‌زمان تمدید خودکارش اجرا شود، و هر دو یک موجودی را ببینند.

    بدتر اینکه UPDATE هیچ شرطی نداشت، پس نتیجه یک موجودی منفی بود
    که در هیچ گزارشی به چشم نمی‌آمد.

    این تست پول واقعی را با نخ‌های واقعی خرج می‌کند.

اجرا:  python3 bot/test_wallet.py
"""
import io
import os
import sys
import tempfile
import threading
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

G, R, D, X = "\033[38;5;42m", "\033[38;5;203m", "\033[38;5;245m", "\033[0m"
_ok = _fail = 0


def check(name, cond, detail=""):
    global _ok, _fail
    if cond:
        _ok += 1
        print(f"  {G}✓{X} {name}" + (f" {D}— {detail}{X}" if detail else ""))
    else:
        _fail += 1
        print(f"  {R}✗{X} {name}" + (f" {D}— {detail}{X}" if detail else ""))


def head(t):
    print(f"\n{D}── {t} ──{X}")


os.environ["BOT_DB_PATH"] = tempfile.mktemp(suffix=".db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import db as DB  # noqa: E402

DB.init_db()
tid = DB.create_tenant("تست کیف پول", bot_token="123:TEST", owner_tg_id=999)
d = DB.TenantDB(tid)


def new_user(balance):
    new_user.n += 1
    tg = 90000 + new_user.n
    d.create_user(tg, first_name="کاربر")
    u = d.get_user(tg)
    if balance:
        d.add_balance(u["id"], balance, "topup", "شارژ اولیه")
    return d.get_user(tg)


new_user.n = 0


def bal(uid):
    row = d.q("SELECT balance FROM users WHERE tenant_id=? AND id=?", (tid, uid))
    return row[0]["balance"] if row else None


# ═══════════════════════════════════════════════════════════
head("خرج ساده")

u = new_user(100000)
ok, left = d.spend_balance(u["id"], 30000, "spend", "خرید")
check("خرج در حد موجودی انجام می‌شود", ok)
check("موجودی درست کم شد", left == 70000, f"{left}")
check("در دیتابیس هم همان است", bal(u["id"]) == 70000, f"{bal(u['id'])}")

ok, left = d.spend_balance(u["id"], 70000, "spend", "خرید دوم")
check("خرج دقیقاً به اندازه‌ی موجودی انجام می‌شود", ok)
check("موجودی صفر شد", left == 0, f"{left}")

head("خرج بیش از موجودی")

u2 = new_user(50000)
ok, left = d.spend_balance(u2["id"], 80000, "spend", "گران")
check("خرج بیش از موجودی رد می‌شود", ok is False)
check("موجودی دست‌نخورده ماند", left == 50000, f"{left}")
check("در دیتابیس هم دست‌نخورده", bal(u2["id"]) == 50000)

txs = d.q("SELECT * FROM wallet_tx WHERE tenant_id=? AND user_id=?", (tid, u2["id"]))
check("تراکنش ناموفق ثبت نمی‌شود", len(txs) == 1,
      f"{len(txs)} تراکنش — فقط شارژ اولیه")

head("کیف پول خالی")

u3 = new_user(0)
ok, left = d.spend_balance(u3["id"], 1, "spend", "یک تومان")
check("از کیف خالی چیزی برداشته نمی‌شود", ok is False and left == 0)
check("موجودی منفی نشد", bal(u3["id"]) == 0)

head("هم‌زمانی — همان چیزی که در تولید اتفاق می‌افتد")

# ده نخ، هرکدام می‌خواهد ۱۰٬۰۰۰ خرج کند، ولی فقط ۵۰٬۰۰۰ پول هست.
# باید دقیقاً پنج‌تا موفق شوند و موجودی صفر بماند.
u4 = new_user(50000)
results = []
lock = threading.Lock()
start = threading.Barrier(10)


def worker():
    start.wait()
    ok_, left_ = d.spend_balance(u4["id"], 10000, "spend", "هم‌زمان")
    with lock:
        results.append(ok_)


threads = [threading.Thread(target=worker) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

wins = sum(1 for r in results if r)
final = bal(u4["id"])
check("دقیقاً پنج خرج موفق شد", wins == 5, f"{wins} از ۱۰")
check("موجودی صفر شد، نه منفی", final == 0, f"{final}")
check("هیچ‌وقت منفی نشد", final >= 0,
      "همان باگی که با add_balance ممکن بود")

spent = d.q("SELECT COALESCE(SUM(amount),0) s FROM wallet_tx "
            "WHERE tenant_id=? AND user_id=? AND kind='spend'", (tid, u4["id"]))
check("تراکنش‌ها با موجودی می‌خوانند", spent[0]["s"] == -50000,
      f"{spent[0]['s']}")

head("فشار بیشتر — بیست نخ روی مبلغ‌های نامساوی")

u5 = new_user(100000)
amounts = [7000, 13000, 21000, 5000, 9000] * 4
res2 = []


def worker2(amt):
    ok_, _ = d.spend_balance(u5["id"], amt, "spend", "فشار")
    with lock:
        res2.append((amt, ok_))


ts = [threading.Thread(target=worker2, args=(a,)) for a in amounts]
for t in ts:
    t.start()
for t in ts:
    t.join()

taken = sum(a for a, okk in res2 if okk)
final5 = bal(u5["id"])
check("مجموع برداشت‌ها از موجودی بیشتر نشد", taken <= 100000,
      f"برداشت {taken} از ۱۰۰۰۰۰")
check("موجودی نهایی منفی نیست", final5 >= 0, f"{final5}")
check("موجودی با برداشت‌ها می‌خواند", final5 == 100000 - taken,
      f"{final5} == {100000 - taken}")

head("برگشت پول هنوز کار می‌کند")

u6 = new_user(20000)
d.spend_balance(u6["id"], 20000, "spend", "خرید")
d.add_balance(u6["id"], 20000, "refund", "خطا در ساخت")
check("برگشت پول موجودی را برمی‌گرداند", bal(u6["id"]) == 20000)

head("ادمین هنوز می‌تواند دستی کم کند")

u7 = new_user(10000)
d.add_balance(u7["id"], -15000, "admin", "اصلاح دستی")
check("add_balance هنوز شرط ندارد", bal(u7["id"]) == -5000,
      "ادمین باید بتواند بدهی ثبت کند؛ فقط خرجِ مشتری شرط دارد")



# ═══════════════════════════════════════════════════════════
head("سکه — همان دسته، همان خطر")

def coins(uid):
    row = d.q("SELECT coins FROM users WHERE tenant_id=? AND id=?", (tid, uid))
    return row[0]["coins"] if row else None


c1 = new_user(0)
d.add_coins(c1["id"], 100, "admin", "شارژ تست")
check("سکه اضافه می‌شود", coins(c1["id"]) == 100)

okc, left = d.spend_coins(c1["id"], 40, "spend", "تخفیف")
check("خرج در حد موجودی", okc and left == 60, f"{left}")

okc, left = d.spend_coins(c1["id"], 80, "spend", "بیش از موجودی")
check("خرج بیش از موجودی رد می‌شود", okc is False)
check("موجودی دست‌نخورده", coins(c1["id"]) == 60, f"{coins(c1['id'])}")

txs = d.q("SELECT * FROM coin_tx WHERE tenant_id=? AND user_id=? AND amount<0",
          (tid, c1["id"]))
check("تراکنش ناموفق ثبت نمی‌شود", len(txs) == 1, f"{len(txs)}")

head("سکه — دو سفارش هم‌زمان با یک موجودی")

# همان اکسپلویت: دو سفارش، هرکدام ۵۰ سکه، ولی فقط ۵۰ سکه هست
c2 = new_user(0)
d.add_coins(c2["id"], 50, "admin", "شارژ")
a, _ = d.spend_coins(c2["id"], 50, "hold", "سفارش الف")
b, _ = d.spend_coins(c2["id"], 50, "hold", "سفارش ب")
check("فقط یکی از دو سفارش سکه می‌گیرد", a and not b,
      "قبلاً هر دو می‌گرفتند و موجودی منفی می‌شد")
check("موجودی صفر شد نه منفی", coins(c2["id"]) == 0, f"{coins(c2['id'])}")

head("سکه — فشار ده‌نخی")

c3 = new_user(0)
d.add_coins(c3["id"], 30, "admin", "شارژ")
res3 = []
start3 = threading.Barrier(10)


def w3():
    start3.wait()
    okk, _ = d.spend_coins(c3["id"], 10, "hold", "هم‌زمان")
    with lock:
        res3.append(okk)


t3 = [threading.Thread(target=w3) for _ in range(10)]
for t in t3:
    t.start()
for t in t3:
    t.join()

check("دقیقاً سه رزرو موفق شد", sum(1 for x in res3 if x) == 3,
      f"{sum(1 for x in res3 if x)} از ۱۰")
check("موجودی سکه منفی نشد", coins(c3["id"]) == 0, f"{coins(c3['id'])}")

head("سکه‌ی رایگان از راه رد شدن — دیگر ممکن نیست")

SRC = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "handlers.py"), encoding="utf-8").read()
check("سکه هنگام ثبت سفارش رزرو می‌شود",
      'spend_coins(' in SRC and '"hold"' in SRC,
      "نه هنگام تایید — وگرنه دو سفارش یک موجودی را می‌خورند")
check("تایید دیگر دوباره کم نمی‌کند",
      'add_coins(user["id"], -order["coins_used"]' not in SRC)
check("رد شدن فقط رزرو را آزاد می‌کند",
      "_release_coins(ctx, order_id)" in SRC,
      "قبلاً بی‌قید add_coins مثبت می‌زد — سکه‌ی رایگان")
check("انقضا هم آزاد می‌کند", SRC.count("_release_coins(") >= 3,
      f"{SRC.count('_release_coins(')} جا")
DBSRC = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "db.py"), encoding="utf-8").read()
check("منطق آزادسازی یک جا بیشتر نیست",
      "def release_coins(" in DBSRC
      and "return ctx.db.release_coins(order_id)" in SRC,
      "جاروکش خودکار ربات ندارد و نمی‌تواند Ctx بسازد")
check("آزادسازی دو بار انجام نمی‌شود", "kind='released'" in DBSRC,
      "تراکنش بعد از بازگشت نام عوض می‌کند")


# ═══════════════════════════════════════════════════════════
head("تمدید همان اشتراکی را تمدید می‌کند که انتخاب شده")

# دو باگ با هم:
#
#   ۱. دکمه‌های «تمدید» همان chk و wpay خرید جدید بودند و create_order
#      پیش‌فرض kind="new" دارد — پس مشتری پول تمدید می‌داد و کانفیگ
#      *دوم* می‌گرفت، در حالی که اولی همچنان منقضی می‌شد.
#
#   ۲. تمدید خودکار kind="renew" می‌ساخت ولی provision با subs[0] کار
#      می‌کرد — تازه‌ترین اشتراک، نه آن‌که پول برایش داده شده بود.

u = new_user(0)

pid = d.exec(
    "INSERT INTO plans (tenant_id, name, gb, days, price) VALUES (?,?,?,?,?)",
    (tid, "یک‌ماهه", 50, 30, 190000))

sub_ids = []
for n in ("aaa", "bbb", "ccc"):
    sub_ids.append(d.exec(
        "INSERT INTO subscriptions (tenant_id, user_id, plan_id, client_email,"
        " gb, expires_at) VALUES (?,?,?,?,?,?)",
        (tid, u["id"], pid, f"e_{n}", 50, "2026-12-01T00:00:00")))

o = d.create_order(u["id"], pid, 190000, 190000,
                   kind="renew", renew_sub_id=sub_ids[1])
check("سفارش تمدید مقصد را نگه می‌دارد",
      o.get("renew_sub_id") == sub_ids[1],
      f"{o.get('renew_sub_id')} در برابر {sub_ids[1]}")

o2 = d.create_order(u["id"], pid, 190000, 190000)
check("سفارش عادی مقصد ندارد", not o2.get("renew_sub_id"))
check("و نوعش new می‌ماند", o2["kind"] == "new", o2["kind"])

SRC = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "handlers.py"), encoding="utf-8").read()

check("دکمه‌ی تمدید شناسه‌ی اشتراک را حمل می‌کند",
      'f"chk:{plan[\'id\']}:0:{sub[\'id\']}"' in SRC,
      "وگرنه دقیقاً مثل خرید جدید عمل می‌کند")
check("دکمه‌ی کیف پول هم همین‌طور",
      'f"wpay:{plan[\'id\']}:{sub[\'id\']}"' in SRC)
check("مسیریاب بخش سوم را می‌خواند", "renew_sub_id=rid" in SRC)
check("سفارش با مقصد، نوعش renew می‌شود",
      'kind=("renew" if renew_sub_id else "new")' in SRC)
check("provision مقصد را از سفارش می‌خواند",
      'order.get("renew_sub_id")' in SRC,
      "نه subs[0] که تازه‌ترین است")
check("مقصد به همان کاربر محدود است", 'AND user_id=?' in SRC,
      "تا کسی اشتراک دیگری را تمدید نکند")

# مقصدِ متعلق به کاربر دیگر نباید پیدا شود
other = new_user(0)
osid = d.exec(
    "INSERT INTO subscriptions (tenant_id, user_id, plan_id, client_email,"
    " gb, expires_at) VALUES (?,?,?,?,?,?)",
    (tid, other["id"], pid, "e_other", 50, "2026-12-01T00:00:00"))
found = d.q("SELECT * FROM subscriptions WHERE tenant_id=? AND id=? AND user_id=?",
            (tid, osid, u["id"]), one=True)
check("اشتراک کاربر دیگر پیدا نمی‌شود", found is None,
      "همان شرطی که جلوی تمدید اشتراک دیگران را می‌گیرد")



# ═══════════════════════════════════════════════════════════
head("پورسانت همکار — روی هر فروش، نه فقط کارتی")

# باگ: record_commission فقط در approve_order صدا زده می‌شد. خرید با
# کیف پول و تمدید خودکار هر دو کانفیگ می‌ساختند و تحویل می‌دادند ولی
# هیچ پورسانتی ثبت نمی‌کردند — همکار بی‌صدا سهمش را از دست می‌داد.

aid = d.exec(
    "INSERT INTO affiliates (tenant_id, name, code, percent, active)"
    " VALUES (?,?,?,?,1)", (tid, "همکار تست", "AFF1", 10))

buyer = new_user(0)
d.exec("UPDATE users SET affiliate_id=? WHERE tenant_id=? AND id=?",
       (aid, tid, buyer["id"]))

r1 = DB.record_commission(tid, buyer["id"], 5001, 200000)
check("پورسانت ثبت می‌شود", r1 is not None)
check("درصد درست حساب می‌شود", r1 and r1["commission"] == 20000,
      str(r1 and r1["commission"]))

r2 = DB.record_commission(tid, buyer["id"], 5001, 200000)
check("همان سفارش دوبار پورسانت نمی‌گیرد", r2 is None,
      "جدول روی (مستاجر، سفارش) یکتاست")

r3 = DB.record_commission(tid, buyer["id"], 5002, 0)
check("فروش صفر پورسانت ندارد", r3 is None)

# کاربر بدون همکار
plain = new_user(0)
r4 = DB.record_commission(tid, plain["id"], 5003, 200000)
check("کاربر بدون همکار پورسانت نمی‌سازد", r4 is None)

# همکار غیرفعال
d.exec("UPDATE affiliates SET active=0 WHERE id=?", (aid,))
r5 = DB.record_commission(tid, buyer["id"], 5004, 200000)
check("همکار غیرفعال پورسانت نمی‌گیرد", r5 is None)
d.exec("UPDATE affiliates SET active=1 WHERE id=?", (aid,))

head("هر سه مسیر فروش پورسانت می‌دهند")

check("تابع مشترک وجود دارد", "def _pay_commission(" in SRC)
check("مسیر کارت صدایش می‌زند",
      SRC.count("_pay_commission(ctx, user, order_id") >= 1)
check("خرید با کیف پول صدایش می‌زند",
      "_pay_commission(ctx, fresh, order[\"id\"]" in SRC,
      "قبلاً هیچ پورسانتی نمی‌داد")
check("تمدید خودکار صدایش می‌زند",
      "_pay_commission(ctx, user, order[\"id\"], plan[\"price\"])" in SRC,
      "قبلاً هیچ پورسانتی نمی‌داد")
check("هر سه مسیر پوشش داده شدند",
      SRC.count("_pay_commission(") >= 4,
      f"{SRC.count('_pay_commission(')} ارجاع — یک تعریف و سه صدازدن")
check("خطای پورسانت تحویل را متوقف نمی‌کند",
      "log.debug(\"ثبت پورسانت ناموفق\"" in SRC,
      "فروش انجام شده و مشتری منتظر است")



# ═══════════════════════════════════════════════════════════
head("سفارشی که خودکار منقضی می‌شود، سکه‌ها را پس می‌دهد")

# سکه هنگام ثبت سفارش رزرو می‌شود. مستند spend_coins می‌گوید «فقط در
# رد، انقضا یا لغو برمی‌گردد» — و سه مسیر دستی (دکمه‌ی لغو، بازکردن
# سفارشِ گذشته، رد توسط ادمین) واقعاً برش می‌گردانند.
#
# ولی جاروکشِ خودکار، همانی که هر دو دقیقه می‌دود و عملاً *همیشه*
# زودتر از مشتری به سفارش می‌رسد، یک UPDATE خام می‌زد:
#
#     UPDATE orders SET status='expired' WHERE ...
#
# بدون آزادکردن رزرو. یعنی هر مشتری که سکه‌هایش را روی سفارشی خرج
# کند و سر وقت پول نریزد، سکه‌ها را برای همیشه از دست می‌دهد — بی‌صدا،
# بدون خطا، بدون اینکه چیزی گرفته باشد.

from bot import run as RUN2   # noqa: E402

pid_c = d.exec(
    "INSERT INTO plans (tenant_id, name, gb, days, price) VALUES (?,?,?,?,?)",
    (tid, "پلن سکه", 50, 30, 200000))


def order_with_coins(coins, ttl=30):
    """مشتری با سکه سفارش می‌دهد — دقیقاً مثل مسیر واقعی خرید."""
    u = new_user(0)
    d.add_coins(u["id"], coins, "bonus", "برای تست")
    o = d.create_order(u["id"], pid_c, 200000, 200000 - coins * 1000,
                       coins_used=coins, ttl_minutes=ttl)
    ok, _ = d.spend_coins(u["id"], coins, "hold", "رزرو سفارش",
                          order_id=o["id"])
    return u, o, ok


def coins_of(uid):
    return d.q("SELECT coins FROM users WHERE tenant_id=? AND id=?",
               (tid, uid), one=True)["coins"]


def expire_now(oid):
    """مهلت پرداخت را به گذشته می‌بریم، مثل مشتری‌ای که پول نریخته."""
    d.exec("UPDATE orders SET expires_at=? WHERE tenant_id=? AND id=?",
           ((datetime.now() - timedelta(minutes=5)).isoformat(), tid, oid))


u1, o1, held = order_with_coins(12)
check("سکه هنگام ثبت سفارش رزرو می‌شود", held and coins_of(u1["id"]) == 0,
      f"{coins_of(u1['id'])} سکه")

expire_now(o1["id"])
RUN2.expire_stale_orders()

st = d.get_order(o1["id"])["status"]
check("جاروکش سفارش را منقضی می‌کند", st == "expired", st)
check("و سکه‌ها برمی‌گردند", coins_of(u1["id"]) == 12,
      f"{coins_of(u1['id'])} از ۱۲ سکه")

rel = d.q("SELECT kind FROM coin_tx WHERE tenant_id=? AND order_id=?"
          " AND kind='hold'", (tid, o1["id"]))
check("رزرو دیگر باز نیست", not rel,
      "وگرنه دفعه‌ی بعد دوباره برمی‌گرداند")

head("بازگشت سکه دوبار انجام نمی‌شود")

RUN2.expire_stale_orders()
RUN2.expire_stale_orders()
check("جاروکش‌های بعدی سکه‌ی اضافه نمی‌دهند", coins_of(u1["id"]) == 12,
      f"{coins_of(u1['id'])} سکه — باید ۱۲ بماند")

head("سفارش‌هایی که نباید دست بخورند")

u2, o2, _ = order_with_coins(7)
RUN2.expire_stale_orders()
check("سفارشی که مهلتش نگذشته منقضی نمی‌شود",
      d.get_order(o2["id"])["status"] == "pending")
check("و سکه‌هایش همچنان رزرو است", coins_of(u2["id"]) == 0,
      f"{coins_of(u2['id'])} سکه")

u3, o3, _ = order_with_coins(5)
d.exec("UPDATE orders SET status='approved' WHERE tenant_id=? AND id=?",
       (tid, o3["id"]))
expire_now(o3["id"])
RUN2.expire_stale_orders()
check("سفارش تاییدشده با گذشتن مهلت منقضی نمی‌شود",
      d.get_order(o3["id"])["status"] == "approved",
      "مشتری پولش را داده و کانفیگش را گرفته")
check("و سکه‌های خرج‌شده‌اش برنمی‌گردند", coins_of(u3["id"]) == 0,
      f"{coins_of(u3['id'])} سکه — فروش انجام شده")

head("سفارش بدون سکه هم سالم منقضی می‌شود")

u4 = new_user(0)
o4 = d.create_order(u4["id"], pid_c, 200000, 200000)
expire_now(o4["id"])
RUN2.expire_stale_orders()
check("بدون رزرو هم خطا نمی‌دهد",
      d.get_order(o4["id"])["status"] == "expired")
check("و سکه‌ی بی‌دلیل نمی‌سازد", coins_of(u4["id"]) == 0,
      f"{coins_of(u4['id'])} سکه")



print(f"\n{D}{'─' * 50}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
