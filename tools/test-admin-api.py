#!/usr/bin/env python3
"""
تست endpointهای مدیریت کاربران روی یک دیتابیس واقعی.

چرا وجود دارد:
    فیلترهای بخش کاربران SQL خام‌اند. یک شرط اشتباه، فهرست را بی‌صدا
    خالی یا اشتباه می‌کند و کسی متوجه نمی‌شود — چون خروجی همچنان
    «معتبر» به نظر می‌رسد.

اجرا:  python3 tools/test-admin-api.py
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bot"))
sys.path.insert(0, str(ROOT / "backend"))

TMP = tempfile.mktemp(suffix=".db")
os.environ["BOT_DB_PATH"] = TMP
os.environ["NEXORA_ADMIN_PASSWORD"] = "testpw"

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


# ── ساخت دیتابیس نمونه ──
os.environ["BOT_DB_PATH"] = TMP
import db as botdb                                    # noqa: E402

botdb.DB_PATH = Path(TMP)
botdb.init_db()
tid = botdb.create_tenant("Test", bot_token="123:TEST", owner_tg_id=1)
D_ = botdb.TenantDB(tid)

# کاربر ۱: خریدار فعال، شماره دارد
u1 = D_.create_user(1001, "ali", "علی")
D_.exec("UPDATE users SET phone='989120000001', balance=50000, coins=12 "
        "WHERE id=?", (u1["id"],))
D_.exec("INSERT INTO plans (tenant_id,name,price,gb,days) VALUES (?,?,?,?,?)",
        (tid, "پلن", 100000, 30, 30))
pid = D_.plans()[0]["id"]
o1 = D_.create_order(u1["id"], pid, 100000, 100000)
D_.exec("UPDATE orders SET status='approved' WHERE id=?", (o1["id"],))
D_.exec("INSERT INTO subscriptions (tenant_id,user_id,plan_id,client_email,"
        "is_active,expires_at) VALUES (?,?,?,?,1,datetime('now','+10 day'))",
        (tid, u1["id"], pid, "e1"))

# کاربر ۲: اشتراکش تمام شده، بدون شماره
u2 = D_.create_user(1002, None, "رضا")
D_.exec("INSERT INTO subscriptions (tenant_id,user_id,plan_id,client_email,"
        "is_active,expires_at) VALUES (?,?,?,?,0,datetime('now','-3 day'))",
        (tid, u2["id"], pid, "e2"))

# کاربر ۳: هیچ‌وقت خرید نکرده، مسدود
u3 = D_.create_user(1003, "sara", "سارا")
D_.exec("UPDATE users SET is_blocked=1 WHERE id=?", (u3["id"],))

# کاربر ۴: با لینک دعوت آمده
D_.create_user(1004, None, "مهدی", referred_by=u1["id"])

import app                                            # noqa: E402

app.BOT_DB = Path(TMP)
# رمز واقعی سرور را نمی‌خوانیم؛ برای تست جایگزینش می‌کنیم
PW = "testpw"
app.load_password = lambda: PW

head("فیلترهای کاربران")


def users(**kw):
    kw.setdefault("x_admin_password", PW)
    return app.bot_users(**kw)


allu = users()
check("دیتابیس خوانده شد", allu.get("dbReady"), str(allu.get("error") or ""))
check("همه‌ی کاربران", allu["total"] == 4, str(allu.get("total")))
check("آمار هر فیلتر برمی‌گردد", "counts" in allu and allu["counts"]["all"] == 4,
      str(allu.get("counts", {}).get("all")))

cases = [
    ("active", 1, "اشتراک فعال"),
    ("expired", 1, "اشتراک تمام‌شده"),
    ("never", 2, "هیچ اشتراکی نداشته"),
    ("buyers", 1, "خرید موفق داشته"),
    ("blocked", 1, "مسدود"),
    ("withPhone", 1, "شماره دارد"),
    ("noPhone", 3, "بدون شماره"),
    ("withBalance", 1, "کیف پول پر"),
    ("withCoins", 1, "سکه دارد"),
    ("referred", 1, "با لینک دعوت"),
]
for key, want, label in cases:
    got = users(filter=key)["total"]
    check(label, got == want, f"{got} (انتظار {want})")

head("آمار هر کاربر")
row = next(u for u in users(filter="buyers")["users"] if u["tg_id"] == 1001)
check("تعداد سفارش موفق", row["ordersCount"] == 1, str(row["ordersCount"]))
check("مجموع خرید", row["spent"] == 100000, str(row["spent"]))
check("اشتراک فعال", row["activeSubs"] == 1, str(row["activeSubs"]))
check("شماره برمی‌گردد", row["phone"] == "989120000001", str(row["phone"]))

head("جستجو")
check("با نام", users(q="علی")["total"] == 1)
check("با یوزرنیم", users(q="sara")["total"] == 1)
check("با شناسه تلگرام", users(q="1002")["total"] == 1)
check("با شماره تماس", users(q="98912")["total"] == 1)
check("جستجوی بی‌نتیجه", users(q="هیچ‌کس")["total"] == 0)
check("جستجو با فیلتر ترکیب می‌شود",
      users(q="علی", filter="blocked")["total"] == 0)

head("مرتب‌سازی و صفحه‌بندی")
check("بیشترین خرید اول", users(sort="spent")["users"][0]["tg_id"] == 1001)
check("قدیمی‌ترین اول", users(sort="old")["users"][0]["tg_id"] == 1001)
p1 = users(limit=2, offset=0)
p2 = users(limit=2, offset=2)
check("صفحه‌بندی", len(p1["users"]) == 2 and len(p2["users"]) == 2)
check("صفحه‌ها هم‌پوشانی ندارند",
      not ({u["tg_id"] for u in p1["users"]} & {u["tg_id"] for u in p2["users"]}))
check("total مستقل از صفحه است", p2["total"] == 4, str(p2["total"]))

head("پیام به کاربر")
try:
    app.bot_message_user(1001, {"text": ""}, x_admin_password=PW)
    check("متن خالی رد می‌شود", False)
except app.HTTPException as e:
    check("متن خالی رد می‌شود", e.status_code == 400, e.detail)

try:
    app.bot_message_user(9999, {"text": "سلام"}, x_admin_password=PW)
    check("کاربر ناموجود رد می‌شود", False)
except app.HTTPException as e:
    check("کاربر ناموجود رد می‌شود", e.status_code == 404, e.detail)

try:
    app.bot_message_user(1001, {"text": "x" * 4000}, x_admin_password=PW)
    check("متن خیلی بلند رد می‌شود", False)
except app.HTTPException as e:
    check("متن خیلی بلند رد می‌شود", e.status_code == 400, e.detail)

try:
    os.unlink(TMP)
except OSError:
    pass

# ═══════════════════════════════════════════════════════════
head("شناسه‌ی نسخه به شل نمی‌رسد")

# نقطه‌ی پایانی بازگردانی، شناسه‌ی نسخه را از بدنه‌ی درخواست می‌گرفت
# و مستقیم داخل یک رشته‌ی شل می‌گذاشت:
#
#     cmd = f"setsid {cli} rollback {snap} --yes ..."
#     subprocess.Popen(["bash", "-lc", cmd])
#
# و اعتبارسنجی‌اش فهرستِ «این کاراکترها را رد کن» بود: / و ..
#
# این‌جا هم همان شکلِ اشتباه است. فهرستِ ممنوع هر چیزی را که در آن
# فکر نکرده‌ایم عبور می‌دهد؛ فهرستِ مجاز فقط چیزی را که می‌شناسیم.
# نام نسخه‌ها را خودِ اسکریپت با date می‌سازد و همیشه یک قالب دارد.

import shutil as _sh
import tempfile as _tf
from pathlib import Path as _P

SNAPS = _P(_tf.mkdtemp())
app.SNAP_DIR = SNAPS

LAUNCHED = []
app.subprocess_popen_calls = LAUNCHED


class _FakePopen:
    def __init__(self, argv, **kw):
        LAUNCHED.append((argv, kw))
        self.pid = 4242


import subprocess as _sp  # noqa: E402
_real_popen = _sp.Popen
_sp.Popen = _FakePopen

# نسخه‌ای با نام معتبر
(SNAPS / "20260101-120000").mkdir()
# و یکی با نامی که اگر به شل برسد دستور اجرا می‌کند
EVIL = "20260101-120000; touch /tmp/nexora-pwned"
(SNAPS / EVIL.replace("/", "_")).mkdir(exist_ok=True)


def _roll(snap_id):
    try:
        return app.run_rollback({"id": snap_id}, x_admin_password="testpw"), None
    except Exception as e:
        return None, e


ok_res, ok_err = _roll("20260101-120000")
check("نسخه‌ی معتبر اجرا می‌شود", ok_res and ok_res.get("ok") is True,
      str(ok_err)[:70] if ok_err else "")

bad_res, bad_err = _roll(EVIL.replace("/", "_"))
code = getattr(bad_err, "status_code", None)
check("نامی با کاراکتر شل رد می‌شود", bad_res is None and code == 400,
      f"status={code}")

for weird in ("20260101-120000 && ls", "$(whoami)", "a`id`b", "", "..",
              "../../etc", "20260101_120000"):
    r, e = _roll(weird)
    check(f"«{weird[:22] or 'خالی'}» رد می‌شود",
          r is None and getattr(e, "status_code", None) in (400, 404),
          f"status={getattr(e, 'status_code', None)}")

head("و اصلاً شلی در کار نیست")

check("دستور به‌صورت فهرست اجرا می‌شود",
      LAUNCHED and isinstance(LAUNCHED[0][0], list),
      str(type(LAUNCHED[0][0]).__name__) if LAUNCHED else "هیچ اجرایی نشد")
check("bash -lc استفاده نمی‌شود",
      LAUNCHED and "-lc" not in LAUNCHED[0][0],
      " ".join(str(x) for x in (LAUNCHED[0][0] if LAUNCHED else []))[:70])
check("shell=True نیست",
      LAUNCHED and not LAUNCHED[0][1].get("shell"),
      str(LAUNCHED[0][1].get("shell")) if LAUNCHED else "")
check("شناسه‌ی نسخه به‌عنوان یک آرگومان جدا می‌رود",
      LAUNCHED and "20260101-120000" in LAUNCHED[0][0],
      str(LAUNCHED[0][0])[:80] if LAUNCHED else "")
check("در نشست جدا اجرا می‌شود",
      LAUNCHED and LAUNCHED[0][1].get("start_new_session") is True,
      "تا بستن پنل وسط بازگردانی آن را نکشد")

_sp.Popen = _real_popen
_sh.rmtree(SNAPS, ignore_errors=True)



print(f"\n{D}{'─' * 46}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
