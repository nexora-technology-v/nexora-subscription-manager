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
import os
import sys
import tempfile
import threading

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

print(f"\n{D}{'─' * 50}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
