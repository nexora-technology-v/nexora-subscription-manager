#!/usr/bin/env python3
"""
تست endpointهای مدیریت کاربران روی یک دیتابیس واقعی.

چرا وجود دارد:
    فیلترهای بخش کاربران SQL خام‌اند. یک شرط اشتباه، فهرست را بی‌صدا
    خالی یا اشتباه می‌کند و کسی متوجه نمی‌شود — چون خروجی همچنان
    «معتبر» به نظر می‌رسد.

اجرا:  python3 tools/test-admin-api.py
"""
import io
from datetime import datetime as _dt
import json
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
# ═══════════════════════════════════════════════════════════
head("حدس‌زدنِ پشت‌سرهمِ رمز باید متوقف شود")

# کل سامانه پشت یک رمز است: پنل، اطلاعات مشتری‌ها، رمز x-ui، توکن
# ربات. هیچ چیزی جلوی حدس‌زدن را نمی‌گرفت — نه در /api/login و نه در
# مسیرهای مدیریتی که همان رمز را در هدر می‌گیرند.

import importlib.util as _iu  # noqa: E402
_spec = _iu.spec_from_file_location(
    "nxauth", os.path.join(str(ROOT), "backend", "app.py"))
AP = _iu.module_from_spec(_spec)
sys.modules["nxauth"] = AP
_spec.loader.exec_module(AP)


def _try(pw):
    """(کد وضعیت, متن) — بدون بالا آوردن استثنا."""
    try:
        AP.check_auth(pw)
        return 200, ""
    except Exception as e:
        return getattr(e, "status_code", 0), str(getattr(e, "detail", e))


AP.load_password = lambda: "testpw"
AP._auth_fails.clear()
code, _ = _try("testpw")
check("رمز درست پذیرفته می‌شود", code == 200, str(code))

code, _ = _try("غلط")
check("رمز غلط رد می‌شود", code == 401, str(code))

# تا آستانه پیش می‌رویم
AP._auth_fails.clear()
codes = [_try("غلط")[0] for _ in range(AP.AUTH_MAX_FAILS)]
check("تا پیش از آستانه هنوز ۴۰۱ است",
      codes[:AP.AUTH_MAX_FAILS - 1] == [401] * (AP.AUTH_MAX_FAILS - 1),
      f"{AP.AUTH_MAX_FAILS - 1} تلاش")

code, detail = _try("غلط")
check("بعد از آستانه قفل می‌شود", code == 429, str(code))
check("و می‌گوید چقدر باید صبر کرد", "دقیقه" in detail, detail[:60])

code, _ = _try("testpw")
check("رمز درست هم در زمان قفل رد می‌شود", code == 429,
      "وگرنه قفل فقط یک مزاحمت است، نه سد")

# قفل که باز شود، رمز درست کار می‌کند و پرونده بسته می‌شود
AP._auth_fails["?"]["until"] = 0
code, _ = _try("testpw")
check("بعد از پایان قفل، ورود درست باز می‌شود", code == 200, str(code))
check("و شمارش صفر می‌شود", "?" not in AP._auth_fails,
      "وگرنه یک ورود موفق هم آدم را نزدیک قفل بعدی نگه می‌دارد")

AP._auth_fails.clear()
_try("غلط")
check("نزدیک آستانه هشدار نمی‌دهد",
      "تلاش دیگر" not in _try("غلط")[1],
      "هشدار زودهنگام فقط به حدس‌زننده می‌گوید کجاست")
for _ in range(AP.AUTH_MAX_FAILS - 4):
    _try("غلط")
check("ولی در سه تلاش آخر هشدار می‌دهد",
      "تلاش دیگر" in _try("غلط")[1],
      "مدیرِ فراموش‌کار باید بفهمد دارد به کجا می‌رود")

# ورود از /api/login هم باید از همین نگهبان رد شود
AP._auth_fails.clear()
try:
    AP.login({"password": "testpw"})
    _login_ok = True
except Exception:
    _login_ok = False
check("ورود با رمز درست کار می‌کند", _login_ok)
for _ in range(AP.AUTH_MAX_FAILS):
    try:
        AP.login({"password": "غلط"})
    except Exception:
        pass
try:
    AP.login({"password": "testpw"})
    _locked = False
except Exception as e:
    _locked = getattr(e, "status_code", 0) == 429
check("ورود هم قفل می‌شود", _locked,
      "بستن یک در و باز گذاشتن آن یکی فایده‌ای ندارد")

# آی‌پی واقعی
AP._auth_fails.clear()


class _Req:
    def __init__(self, peer, fwd=None):
        self.client = type("c", (), {"host": peer})()
        self.headers = {"x-forwarded-for": fwd} if fwd else {}


check("پشت nginx آی‌پی واقعی خوانده می‌شود",
      AP._client_ip(_Req("127.0.0.1", "5.6.7.8")) == "5.6.7.8",
      "وگرنه همه در یک سطل می‌افتند و یک مهاجم مدیر را بیرون می‌اندازد")
check("ولی از اینترنت این هدر باور نمی‌شود",
      AP._client_ip(_Req("5.6.7.8", "1.1.1.1")) == "5.6.7.8",
      "وگرنه با یک هدر جعلی می‌شود از قفل رد شد")
check("هدر بی‌معنا نادیده گرفته می‌شود",
      AP._client_ip(_Req("127.0.0.1", "not-an-ip")) == "127.0.0.1")

# رمز فارسی — همان چیزی که نزدیک بود کل پنل را با ۵۰۰ ببندد
AP._auth_fails.clear()
AP.load_password = lambda: "رمزفارسی۱۲۳"
check("رمز غیرانگلیسی کار می‌کند", _try("رمزفارسی۱۲۳")[0] == 200,
      "compare_digest روی رشته‌ی غیراسکی TypeError می‌دهد — باید بایت داد")
check("و رمز فارسیِ غلط فقط ۴۰۱ است", _try("رمزدیگر")[0] == 401,
      "نه ۵۰۰ — خطای سرور یعنی پنل برای خودِ مدیر هم بسته می‌شود")
AP.load_password = lambda: "testpw"
AP._auth_fails.clear()

SRC = io.open(os.path.join(str(ROOT), "backend", "app.py"),
              encoding="utf-8").read()
check("مقایسه‌ی رمز زمان‌ثابت است", "compare_digest" in SRC,
      "مقایسه‌ی معمولی روی اولین بایت متفاوت برمی‌گردد")


# ═══════════════════════════════════════════════════════════
head("ورود نماینده به پنل خودش")

# پنل مدیر ۱۱۴ مسیر دارد و همه فرض می‌کنند «تو صاحب سیستمی». دادنشان
# به نماینده یعنی هر کدام باید جداگانه محدود شود و کافی است یکی جا
# بیفتد. پس سطح نماینده جداست و فهرست مجاز دارد، نه فهرست ممنوع.

import sqlite3 as _sq3  # noqa: E402

_bd = _sq3.connect(str(AP.BOT_DB))
try:
    # دیتابیس تست جدول مستاجرها را ندارد — کمینه‌اش را می‌سازیم
    _bd.execute("""CREATE TABLE IF NOT EXISTS tenants (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        bot_token TEXT, bot_username TEXT, parent_id INTEGER,
        is_active INTEGER DEFAULT 1, credit INTEGER DEFAULT 0,
        credit_discount INTEGER DEFAULT 0, panel_pass TEXT)""")
    _cols = {r[1] for r in _bd.execute("PRAGMA table_info(tenants)")}
    for _c in ("portal_slug", "portal_pass", "portal_enabled"):
        if _c not in _cols:
            _bd.execute("ALTER TABLE tenants ADD COLUMN " + _c +
                        (" INTEGER DEFAULT 0" if _c == "portal_enabled" else " TEXT"))
    _bd.execute("DELETE FROM tenants WHERE name IN ('نماینده‌ی تست','دومی')")
    _bd.execute(
        "INSERT INTO tenants (name, is_active, portal_slug, portal_pass,"
        " portal_enabled, credit) VALUES (?,1,?,?,1,?)",
        ("نماینده‌ی تست", "hossein", "secret-pass-1", 500000))
    _rid = _bd.execute("SELECT id FROM tenants WHERE portal_slug='hossein'"
                       ).fetchone()[0]
    _bd.execute(
        "INSERT INTO tenants (name, is_active, portal_slug, portal_pass,"
        " portal_enabled, credit) VALUES (?,1,?,?,0,?)",
        ("دومی", "bastan", "secret-pass-2", 0))
    _bd.commit()
finally:
    _bd.close()


def _login(slug, pw):
    AP._auth_fails.clear()
    try:
        return 200, AP.portal_login(slug, {"password": pw}, None)
    except Exception as e:
        return getattr(e, "status_code", 0), str(getattr(e, "detail", e))


_code, _res = _login("hossein", "secret-pass-1")
check("ورود با رمز درست", _code == 200 and _res.get("token"), str(_code))
_tok = _res.get("token") if _code == 200 else ""

check("و نامش برمی‌گردد", _code == 200 and _res.get("name") == "نماینده‌ی تست")

_code, _d = _login("hossein", "غلط")
check("رمز غلط رد می‌شود", _code == 401, str(_code))

_code, _d = _login("ناموجود", "secret-pass-1")
check("نشانی ناموجود همان پیام را می‌دهد", _code == 401 and "نادرست" in _d,
      "وگرنه می‌شود فهمید کدام نشانی‌ها واقعی‌اند")

_code, _d = _login("bastan", "secret-pass-2")
check("نماینده‌ی خاموش اصلاً وارد نمی‌شود", _code == 401, str(_code))

# نشست
_me = AP.portal_tenant(_tok)
check("نشست به مستاجر خودش می‌رسد", _me["portal_slug"] == "hossein")
check("و اعتبارش را دارد", _me["credit"] == 500000)

_pub = AP.portal_me(_me)
check("مشخصات، توکن ربات را لو نمی‌دهد",
      "bot_token" not in _pub and "panel_pass" not in _pub,
      "نماینده هرگز نباید رمز پنل x-ui را ببیند")
check("ولی اعتبار و تخفیفش را می‌بیند",
      _pub["credit"] == 500000 and "discount" in _pub)

try:
    AP.portal_tenant("nxp_جعلی")
    _bad = False
except Exception as e:
    _bad = getattr(e, "status_code", 0) == 401
check("توکن جعلی رد می‌شود", _bad)

# بستن نماینده باید همان لحظه اثر کند
_bd = _sq3.connect(str(AP.BOT_DB))
try:
    _bd.execute("UPDATE tenants SET portal_enabled=0 WHERE id=?", (_rid,))
    _bd.commit()
finally:
    _bd.close()
try:
    AP.portal_tenant(_tok)
    _shut = False
except Exception as e:
    _shut = getattr(e, "status_code", 0) == 403
check("بستن نماینده نشستِ باز را همان لحظه می‌بندد", _shut,
      "نه اینکه تا انقضای نشست کار کند")
check("و توکنش هم پاک می‌شود", _tok not in AP._PORTAL_SESSIONS)


# ═══════════════════════════════════════════════════════════
head("نماینده فقط کانفیگ‌های گروه خودش را می‌بیند")

# همان چیزی که کل این کار برایش انجام شد: نماینده نباید کانفیگ
# نماینده‌ی دیگر یا مشتری مستقیم مدیر را ببیند. تا امروز پنل x-ui
# خودِ مدیر به او داده می‌شد، یعنی همه‌چیز را می‌دید.

_bd = _sq3.connect(str(AP.BOT_DB))
try:
    _bd.execute("UPDATE tenants SET portal_enabled=1, portal_group=? "
                "WHERE portal_slug='hossein'", ("goroh-a",))
    _bd.execute("UPDATE tenants SET portal_enabled=1, portal_group=? "
                "WHERE portal_slug='bastan'", ("goroh-b",))
    _bd.commit()
except Exception:
    # ستون در دیتابیس تست نیست — می‌سازیمش
    _bd.execute("ALTER TABLE tenants ADD COLUMN portal_group TEXT")
    _bd.execute("UPDATE tenants SET portal_enabled=1, portal_group=? "
                "WHERE portal_slug='hossein'", ("goroh-a",))
    _bd.execute("UPDATE tenants SET portal_enabled=1, portal_group=? "
                "WHERE portal_slug='bastan'", ("goroh-b",))
    _bd.commit()
finally:
    _bd.close()

# دنیای x-ui ساختگی: سه گروه
_ALL = [
    {"email": "a1", "group": "goroh-a", "totalGB": 50 * 1024 ** 3, "used": 0,
     "enable": True, "createdAt": "2026-07-01", "expiry": 1790000000000,
     "limitIp": 2, "subId": "s1"},
    {"email": "a2", "group": "goroh-a", "totalGB": 0, "used": 0,
     "enable": False, "createdAt": "2026-07-02", "expiry": 1790000000000,
     "limitIp": 0, "subId": "s2"},
    {"email": "b1", "group": "goroh-b", "totalGB": 50 * 1024 ** 3, "used": 0,
     "enable": True, "createdAt": "2026-07-03", "expiry": 1790000000000,
     "limitIp": 1, "subId": "s3"},
    {"email": "mine", "group": "مشتری مستقیم", "totalGB": 0, "used": 0,
     "enable": True, "createdAt": "2026-07-04", "expiry": 1790000000000,
     "limitIp": 0, "subId": "s4"},
]
AP._read_xui_clients = lambda *a, **k: (_ALL, [], None)

_t1 = AP._tenant_by_slug("hossein")
_out = AP.portal_configs(_t1)
_emails = sorted(c["email"] for c in _out["configs"])
check("فقط کانفیگ‌های گروه خودش", _emails == ["a1", "a2"], "، ".join(_emails))
check("کانفیگ نماینده‌ی دیگر نیست", "b1" not in _emails)
check("مشتری مستقیم مدیر هم نیست", "mine" not in _emails,
      "این بدترین نشتی ممکن بود")
check("شمارش فعال‌ها درست است", _out["active"] == 1, str(_out["active"]))

_t2 = AP._tenant_by_slug("bastan")
_out2 = AP.portal_configs(_t2)
check("نماینده‌ی دوم هم فقط مال خودش را می‌بیند",
      [c["email"] for c in _out2["configs"]] == ["b1"])

# نماینده‌ای که گروهش تعیین نشده نباید چیزی ببیند
_bd = _sq3.connect(str(AP.BOT_DB))
try:
    _bd.execute("UPDATE tenants SET portal_group=NULL WHERE portal_slug='hossein'")
    _bd.commit()
finally:
    _bd.close()
try:
    AP.portal_configs(AP._tenant_by_slug("hossein"))
    _blank = False
except Exception as e:
    _blank = getattr(e, "status_code", 0) == 409
check("نماینده‌ی بی‌گروه هیچ چیز نمی‌بیند", _blank,
      "نه اینکه «همه» را ببیند — آن بدترین حالت پیش‌فرض است")


# ═══════════════════════════════════════════════════════════
head("نوشتن نماینده در پنل — محافظ‌ها")

# از این‌جا به بعد نماینده در x-ui می‌نویسد، و x-ui همان جایی است که
# کانفیگ مشتری‌های واقعی زندگی می‌کند. سه قاعده که هیچ‌کدام قابل
# مذاکره نیست، و این بخش دقیقاً همان‌ها را می‌سنجد.

_bd = _sq3.connect(str(AP.BOT_DB))
try:
    _bd.execute("UPDATE tenants SET portal_group='goroh-a', portal_enabled=1,"
                " credit=300000 WHERE portal_slug='hossein'")
    for _pc in ("panel_url", "panel_user", "panel_pass", "panel_token"):
        try:
            _bd.execute(f"ALTER TABLE tenants ADD COLUMN {_pc} TEXT")
        except Exception:
            pass
    _bd.execute("UPDATE tenants SET panel_url='http://x', panel_user='u',"
                " panel_pass='p' WHERE parent_id IS NULL")
    _bd.commit()
finally:
    _bd.close()

_T = AP._tenant_by_slug("hossein")


class _FakeXUI:
    """پنل ساختگی — فقط برای دیدن اینکه چه چیزی به آن داده می‌شود."""
    calls = []

    def __init__(self, *a, **k):
        pass

    def find_client(self, inbound_id, email=None, client_uuid=None):
        if email in ("a1", "a2"):
            return {"id": "uuid-" + email, "inboundIds": [7], "email": email}
        if email == "b1":
            return {"id": "uuid-b1", "inboundIds": [9], "email": "b1"}
        return None

    def extend_subscription(self, ib, uuid, add_days=0, add_gb=None, email=None):
        _FakeXUI.calls.append(("extend", ib, uuid, add_days, add_gb, email))
        return {"expiry_ms": 1800000000000, "total_bytes": 0}

    def set_enabled(self, ib, uuid, enabled, email=None):
        _FakeXUI.calls.append(("enable", ib, uuid, enabled, email))
        return True


AP._portal_xui = lambda t: (_FakeXUI(), Exception)

# نرخ گروه
_bc = AP._billing_conn()
try:
    _bc.execute("DELETE FROM group_config WHERE group_key='goroh-a'")
    _bc.execute(
        "INSERT INTO group_config (group_key,label,billable,rates) VALUES (?,?,?,?)",
        ("goroh-a", "گروه الف", 1,
         json.dumps([{"gb": 50, "price": 100000, "perDevice": 20000}])))
    _bc.execute("DELETE FROM renewals")
    _bc.commit()
finally:
    _bc.close()

# ── قاعده ۲: کانفیگ نماینده‌ی دیگر دست‌نیافتنی است ──
_FakeXUI.calls = []
try:
    AP.portal_renew({"email": "b1", "months": 1}, _T)
    _blocked = False
except Exception as e:
    _blocked = getattr(e, "status_code", 0) == 404
check("تمدید کانفیگ نماینده‌ی دیگر رد می‌شود", _blocked,
      "ایمیل فرستادن هیچ چیزی را ثابت نمی‌کند")
check("و اصلاً به پنل نمی‌رسد", not _FakeXUI.calls,
      "رد باید قبل از هر نوشتنی اتفاق بیفتد")

try:
    AP.portal_toggle({"email": "b1", "enable": False}, _T)
    _blocked2 = False
except Exception as e:
    _blocked2 = getattr(e, "status_code", 0) == 404
check("خاموش‌کردن کانفیگ نماینده‌ی دیگر هم رد می‌شود", _blocked2)

# ── تمدید درست ──
_FakeXUI.calls = []
_before = _sq3.connect(str(AP.BOT_DB))
_c0 = _before.execute("SELECT credit FROM tenants WHERE portal_slug='hossein'"
                      ).fetchone()[0]
_before.close()

_res = AP.portal_renew({"email": "a1", "months": 2}, _T)
check("تمدید انجام شد", _res["ok"] and _res["months"] == 2)
check("و به پنل با uuid و اینباند درست رفت",
      _FakeXUI.calls and _FakeXUI.calls[0][1] == 7
      and _FakeXUI.calls[0][2] == "uuid-a1",
      str(_FakeXUI.calls[:1]))
check("روزها دو برابر شد", _FakeXUI.calls[0][3] == 60, str(_FakeXUI.calls[0][3]))

# ── قاعده ۳: اعتبار اتمی کم شد ──
_after = _sq3.connect(str(AP.BOT_DB))
_c1 = _after.execute("SELECT credit FROM tenants WHERE portal_slug='hossein'"
                     ).fetchone()[0]
_after.close()
# ۵۰ گیگ = ۱۰۰٬۰۰۰ پایه، ۲ دستگاه یعنی ۱ کاربر اضافه = ۲۰٬۰۰۰، دو ماه
check("اعتبار به اندازه‌ی درست کم شد", _c0 - _c1 == 240000,
      f"{_c0} → {_c1} · انتظار ۲۴۰٬۰۰۰")
check("و همان مبلغ گزارش شد", _res["charged"] == 240000, str(_res["charged"]))

# ── و این تمام دلیل وجود این پنل: ثبت دقیق ──
_bc = AP._billing_conn()
try:
    _rn = [dict(r) for r in _bc.execute("SELECT * FROM renewals")]
finally:
    _bc.close()
check("تمدید دقیق ثبت شد", len(_rn) == 1 and _rn[0]["months"] == 2,
      "دیگر لازم نیست از فاصله‌ی ساخت تا انقضا حدس زده شود")
check("به نام همان کانفیگ و گروه",
      _rn and _rn[0]["email"] == "a1" and _rn[0]["group_key"] == "goroh-a")

# ── اعتبار که کم بیاید ──
_bd = _sq3.connect(str(AP.BOT_DB))
try:
    _bd.execute("UPDATE tenants SET credit=1000 WHERE portal_slug='hossein'")
    _bd.commit()
finally:
    _bd.close()
_FakeXUI.calls = []
try:
    AP.portal_renew({"email": "a1", "months": 1}, AP._tenant_by_slug("hossein"))
    _poor = False
except Exception as e:
    _poor = getattr(e, "status_code", 0) == 402
check("اعتبار ناکافی جلوی تمدید را می‌گیرد", _poor)
check("و هیچ چیزی روی پنل عوض نمی‌شود", not _FakeXUI.calls,
      "کسر قبل از کار است، پس شکستش یعنی کار اصلاً شروع نمی‌شود")

# ── ماه نامعتبر ──
try:
    AP.portal_renew({"email": "a1", "months": 99}, _T)
    _bad = False
except Exception as e:
    _bad = getattr(e, "status_code", 0) == 400
check("تعداد ماه بی‌معنا رد می‌شود", _bad)

APP_SRC = io.open(os.path.join(str(ROOT), "backend", "app.py"),
                  encoding="utf-8").read()
check("کسر اعتبار اتمی است",
      "WHERE id=? AND credit >= ?" in APP_SRC,
      "بخوان-بعد-کم‌کن بین آن دو جا برای درخواست دیگر باز می‌گذارد")
check("و اگر پنل شکست خورد پول برمی‌گردد", "_portal_refund" in APP_SRC)


# ═══════════════════════════════════════════════════════════
head("ساخت کانفیگ از پنل نماینده")

# ساخت حساس‌تر از تمدید است: کانفیگ تازه باید *حتماً* در گروه خودش
# بنشیند و نامش نباید با الگوی گروه دیگری بخواند — چون صفحه‌ی اشتراک
# برند را از پیشوند ایمیل تشخیص می‌دهد.

_bd = _sq3.connect(str(AP.BOT_DB))
try:
    try:
        _bd.execute("ALTER TABLE tenants ADD COLUMN default_inbound INTEGER")
    except Exception:
        pass
    _bd.execute("UPDATE tenants SET credit=1000000, default_inbound=7 "
                "WHERE portal_slug='hossein'")
    _bd.commit()
finally:
    _bd.close()
_T2 = AP._tenant_by_slug("hossein")


def _topup(amount=1000000):
    """اعتبار را برمی‌گرداند سر جایش.

    هر ساختی واقعاً پول کم می‌کند، پس چند بلوکِ پشت سر هم اعتبار را
    تمام می‌کنند و تستِ بعدی به جای چیزی که می‌سنجد، ۴۰۲ می‌گیرد.
    """
    _c = _sq3.connect(str(AP.BOT_DB))
    try:
        _c.execute("UPDATE tenants SET credit=? WHERE portal_slug='hossein'",
                   (amount,))
        _c.commit()
    finally:
        _c.close()


class _MakeXUI(_FakeXUI):
    made = []

    def add_client(self, inbound_id, email, gb=0, days=0, ip_limit=0,
                   client_uuid=None, tg_id=None, sub_id=None, flow=None,
                   group=None, inbound_ids=None, start_on_use=False):
        _MakeXUI.made.append({"inbound": inbound_id, "email": email, "gb": gb,
                              "days": days, "ip": ip_limit, "group": group,
                              "start_on_use": start_on_use})
        return {"id": "new-uuid", "email": email, "subId": email}


AP._portal_xui = lambda t: (_MakeXUI(), Exception)
AP._read_xui_clients = lambda *a, **k: (_ALL, [], None)

_MakeXUI.made = []
_res = AP.portal_create({"gb": 50, "months": 2, "devices": 3}, _T2)
check("کانفیگ ساخته شد", _res["ok"])

_m = _MakeXUI.made[0] if _MakeXUI.made else {}
check("گروهش از ردیف مستاجر آمد", _m.get("group") == "goroh-a",
      "نه از درخواست — این تنها چیزی است که تعیین می‌کند مال کیست")
check("روی اینباند پیش‌فرض ساخته شد", _m.get("inbound") == 7, str(_m.get("inbound")))
check("حجم و روز درست رفت", _m.get("gb") == 50 and _m.get("days") == 60,
      f"{_m.get('gb')} گیگ · {_m.get('days')} روز")
check("تعداد کاربر هم", _m.get("ip") == 3)

check("نامش با نشانی خودِ نماینده شروع می‌شود",
      str(_m.get("email", "")).startswith("hossein_"),
      "نماینده نام را نمی‌فرستد — می‌ساختیمش، وگرنه می‌توانست نام گروه دیگری بسازد")
check("و تکراری نیست", _m.get("email") not in {c["email"] for c in _ALL})

# قیمت: ۵۰ گیگ = ۱۰۰٬۰۰۰، دو کاربر اضافه × ۲۰٬۰۰۰، دو ماه
check("مبلغ درست کسر شد", _res["charged"] == (100000 + 40000) * 2,
      str(_res["charged"]))


# ═══════════════════════════════════════════════════════════
head("ساخت کانفیگ · روز، نه فقط ماه")

# نماینده می‌خواهد «۴۵ روز» بدهد، نه اینکه بین ۱ و ۲ و ۳ ماه گیر
# کند. ولی مبلغ باید با همان تابعی حساب شود که کلِ حسابداری از آن
# می‌خواند — وگرنه سطح تازه‌ای می‌شود که عدد خودش را می‌سازد.

_topup()
_MakeXUI.made = []
_r45 = AP.portal_create({"gb": 50, "days": 45, "devices": 1}, _T2)
_m45 = _MakeXUI.made[0] if _MakeXUI.made else {}
check("روز همان‌طور که خواسته شده به پنل می‌رود",
      _m45.get("days") == 45, str(_m45.get("days")))
check("و مبلغ با گردکردنِ خودِ حسابداری حساب می‌شود",
      _r45["months"] == 2 and _r45["charged"] == 100000 * 2,
      f"{_r45['months']} ماه · {_r45['charged']} تومان — ۴۵ روز یعنی ۲ ماه")

_MakeXUI.made = []
_r10 = AP.portal_create({"gb": 50, "days": 10, "devices": 1}, _T2)
check("ده روز هم می‌شود، و یک ماه حساب می‌شود",
      _MakeXUI.made[0].get("days") == 10 and _r10["months"] == 1,
      f"{_r10['months']} ماه")

# ماه هنوز پذیرفته می‌شود تا فراخوانی قدیمی نشکند
_MakeXUI.made = []
_rm = AP.portal_create({"gb": 50, "months": 3, "devices": 1}, _T2)
check("«ماه» هنوز کار می‌کند و به روز تبدیل می‌شود",
      _MakeXUI.made[0].get("days") == 90 and _rm["months"] == 3,
      f"{_MakeXUI.made[0].get('days')} روز")

# همان قاعده، دو جا — پس تستِ برابری می‌خواهد.
#
# پنل نماینده مبلغ را *پیش از* فرستادن نشان می‌دهد، پس مجبور است
# خودش هم روز را به ماه تبدیل کند. اگر این دو از هم جدا بیفتند،
# عددی که نماینده می‌بیند با عددی که از اعتبارش کم می‌شود فرق
# می‌کند — و او تازه بعد از کسر می‌فهمد.
_PSRC = io.open(os.path.join(str(ROOT), "frontend", "src", "portal",
                             "index.jsx"), encoding="utf-8").read()
check("پنل همان فرمول گردکردن را دارد",
      "const billMonths = Math.max(1, Math.round(days / 30));" in _PSRC,
      "اگر شکلش عوض شد، برابریِ زیر را دوباره بسنج")

import math as _math                                        # noqa: E402
_drift = [d for d in range(1, 367)
          # Math.round در جاوااسکریپت نیم را به بالا می‌برد
          if max(1, _math.floor(d / 30.0 + 0.5)) != AP._months_from_days(d)]
check("و برای هر روزی از ۱ تا ۳۶۶ همان عدد را می‌دهد",
      not _drift, "اختلاف در: %s" % (_drift[:6] or "هیچ روزی"))


for _bad, _why in (({"gb": 50, "days": 0, "devices": 1}, "روز صفر"),
                   ({"gb": 50, "days": 400, "devices": 1}, "روز ۴۰۰")):
    try:
        AP.portal_create(_bad, _T2)
        _ok_day = False
    except Exception as e:
        _ok_day = getattr(e, "status_code", 0) == 400
    check("%s رد می‌شود" % _why, _ok_day)


# ═══════════════════════════════════════════════════════════
head("ساخت کانفیگ · شمارش از اولین اتصال")

# قرارداد خودِ ۳x-ui: expiryTime منفی یعنی «این‌قدر مدت، از لحظه‌ای
# که وصل شد». پنل از قبل این حالت را «شروع‌نشده» می‌شناسد.
#
# چرا مهم است: مشتری امروز می‌خرد و شاید هفته‌ی دیگر وصل شود. بدون
# این، آن هفته از سهمش کم می‌شود.

_topup()
_MakeXUI.made = []
_ru = AP.portal_create({"gb": 50, "days": 30, "devices": 1,
                        "startOnFirstUse": True}, _T2)
check("گزینه به پاسخ برمی‌گردد", _ru.get("startOnFirstUse") is True)
check("و به پنل هم پاس داده می‌شود",
      _MakeXUI.made[0].get("start_on_use") is True,
      "وگرنه گزینه هست و هیچ کاری نمی‌کند")

# و خودِ xui باید expiry را منفی بسازد
import importlib.util as _iu3                            # noqa: E402
_xspec = _iu3.spec_from_file_location(
    "_xui_days", os.path.join(str(ROOT), "bot", "xui.py"))
_xsrc = io.open(os.path.join(str(ROOT), "bot", "xui.py"),
                encoding="utf-8").read()
check("add_client حالت شروع‌از-اتصال را می‌شناسد",
      "start_on_use" in _xsrc and "-int(days * 86400 * 1000)" in _xsrc,
      "expiry منفی، قرارداد خودِ ۳x-ui")

_neg = _xsrc[_xsrc.find("def add_client("):]
_neg = _neg[:_neg.find(chr(10) + "    def ", 10)]
check("و بدون آن، انقضا از همین حالا حساب می‌شود",
      "timedelta(days=days)" in _neg,
      "حالت پیش‌فرض نباید عوض شده باشد")


# ═══════════════════════════════════════════════════════════
head("ساخت کانفیگ · گروه باید واقعاً بنشیند")

# گروه تنها چیزی است که می‌گوید این کانفیگ مالِ کدام نماینده است —
# هم برای صورتحساب، هم برای اینکه خودش ببیندش. اگر ننشیند، کانفیگ
# ساخته می‌شود، پولش کم می‌شود، و بعد در فهرست پیدا نمی‌شود. و
# نسخه‌های قدیمی‌تر ۳x-ui اصلاً گروه ندارند و بی‌صدا دورش می‌ریزند.

_topup()
_MakeXUI.made = []
_rg = AP.portal_create({"gb": 50, "days": 30, "devices": 1}, _T2)
check("گروه به پنل فرستاده می‌شود", _MakeXUI.made[0].get("group") == "goroh-a",
      str(_MakeXUI.made[0].get("group")))
check("و وقتی درست نشسته، هشداری نیست",
      "groupWarning" not in _rg,
      "هشدار فقط برای وقتی است که واقعاً جا نیفتاده")

# حالا پنلی که گروه را دور می‌ریزد
_saved_read = AP._read_xui_clients
AP._read_xui_clients = lambda *a, **k: ([
    {"email": _MakeXUI.made[-1].get("email") if _MakeXUI.made else "x",
     "group": "بدون گروه", "used": 0, "enable": True,
     "totalGB": 0, "expiry": 0, "limitIp": 0}], [], None)
_MakeXUI.made = []
_rw = AP.portal_create({"gb": 50, "days": 30, "devices": 1}, _T2)
AP._read_xui_clients = _saved_read
check("ولی اگر گروه جا نیفتد، بی‌صدا نمی‌ماند",
      "groupWarning" in _rw and "بدون گروه" in _rw["groupWarning"],
      (_rw.get("groupWarning") or "(هیچ هشداری)")[:58])

# ── حجمی که نرخ ندارد ──
_MakeXUI.made = []
try:
    AP.portal_create({"gb": 999, "months": 1, "devices": 1}, _T2)
    _bad = False
except Exception as e:
    _bad = getattr(e, "status_code", 0) == 400
check("حجمی که در نرخ‌ها نیست رد می‌شود", _bad,
      "وگرنه ردیفی ساخته می‌شود که سر ماه «بدون نرخ» می‌ماند")
check("و چیزی روی پنل ساخته نمی‌شود", not _MakeXUI.made)

# ── ورودی بی‌معنا ──
for _bad_in, _why in ((({"gb": 50, "months": 0, "devices": 1}), "ماه صفر"),
                      (({"gb": 50, "months": 99, "devices": 1}), "ماه ۹۹"),
                      (({"gb": 50, "months": 1, "devices": 999}), "کاربر ۹۹۹")):
    # نامش `_ok` نیست: آن، شمارنده‌ی خودِ check است و بازنویسی‌اش
    # شمارش را از این‌جا به بعد صفر می‌کرد. عدد پایانِ این سوییت
    # مدتی کمتر از واقع گزارش می‌شد.
    try:
        AP.portal_create(_bad_in, _T2)
        _rejected = False
    except Exception as e:
        _rejected = getattr(e, "status_code", 0) == 400
    check(f"{_why} رد می‌شود", _rejected)

# ── اعتبار ناکافی ──
_bd = _sq3.connect(str(AP.BOT_DB))
try:
    _bd.execute("UPDATE tenants SET credit=5000 WHERE portal_slug='hossein'")
    _bd.commit()
finally:
    _bd.close()
_MakeXUI.made = []
try:
    AP.portal_create({"gb": 50, "months": 1, "devices": 1},
                     AP._tenant_by_slug("hossein"))
    _poor = False
except Exception as e:
    _poor = getattr(e, "status_code", 0) == 402
check("اعتبار ناکافی جلوی ساخت را می‌گیرد", _poor)
check("و کانفیگی ساخته نمی‌شود", not _MakeXUI.made,
      "کسر قبل از کار است")

APP_SRC2 = io.open(os.path.join(str(ROOT), "backend", "app.py"),
                   encoding="utf-8").read()
# به «group=group» بند است، نه به پرانتزِ بعدش: افزودن یک آرگومانِ
# تازه به همان فراخوانی نباید تستی را قرمز کند که درباره‌ی گروه است.
check("گروه در ساخت از _portal_group می‌آید",
      "group=group" in APP_SRC2 and "group = _portal_group(t)" in APP_SRC2)


# ═══════════════════════════════════════════════════════════
head("ربات شخصی نماینده")

# زیرساختش از قبل بود: run.py برای هر مستاجرِ فعالی که توکن دارد یک
# نخ جدا می‌سازد. پس کارِ این‌جا فقط ثبت توکن است — و مهم‌ترین بخشش
# این است که توکن غلط *قبل از ذخیره* رد شود، وگرنه رباتی بالا می‌آید
# که هیچ‌وقت جواب نمی‌دهد و نماینده نمی‌فهمد چرا.

_bd = _sq3.connect(str(AP.BOT_DB))
try:
    for _c in ("bot_token", "bot_username", "settings"):
        try:
            _bd.execute(f"ALTER TABLE tenants ADD COLUMN {_c} TEXT")
        except Exception:
            pass
    _bd.execute("UPDATE tenants SET bot_token=NULL, bot_username=NULL,"
                " settings='{}' WHERE portal_slug='hossein'")
    _bd.execute("UPDATE tenants SET bot_token='999888777:BBHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw' "
                "WHERE portal_slug='bastan'")
    _bd.commit()
finally:
    _bd.close()

_TB = AP._tenant_by_slug("hossein")

# تلگرام ساختگی
_asked = []


def _fake_me(tok, timeout=10):
    _asked.append(tok)
    if tok.startswith("111222333:"):
        return True, "hossein_vpn_bot"
    return False, "تلگرام این توکن را نمی‌شناسد"


AP._tg_get_me = _fake_me

# ── شکل غلط، بدون اینکه اصلاً از تلگرام پرسیده شود ──
_asked.clear()
for _bad, _why in (("", "توکن خالی"), ("abc", "بدون دونقطه"),
                   ("1:2", "خیلی کوتاه")):
    try:
        AP.portal_bot_set({"token": _bad}, _TB)
        _rejected = False
    except Exception as e:
        _rejected = getattr(e, "status_code", 0) == 400
    check(f"{_why} رد می‌شود", _rejected)
check("و برای هیچ‌کدام تلگرام صدا زده نشد", not _asked,
      "بررسی شکل قبل از شبکه است")

# ── توکنی که مال حساب دیگری است ──
try:
    AP.portal_bot_set({"token": "999888777:BBHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"}, _TB)
    _dup = False
except Exception as e:
    _dup = getattr(e, "status_code", 0) == 409
check("توکن تکراری رد می‌شود", _dup)
_dup_msg = ""
try:
    AP.portal_bot_set({"token": "999888777:BBHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"}, _TB)
except Exception as e:
    _dup_msg = str(getattr(e, "detail", ""))
check("و نام صاحبش را نمی‌گوید", "دومی" not in _dup_msg,
      "نماینده نباید بفهمد چه کسانی در سیستم هستند")

# ── توکنی که تلگرام قبولش ندارد ──
try:
    AP.portal_bot_set({"token": "222333444:CCHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"}, _TB)
    _rej = False
except Exception as e:
    _rej = getattr(e, "status_code", 0) == 400
check("توکنی که تلگرام نمی‌شناسد ذخیره نمی‌شود", _rej)

_row = _sq3.connect(str(AP.BOT_DB))
_tok_now = _row.execute("SELECT bot_token FROM tenants WHERE portal_slug='hossein'"
                        ).fetchone()[0]
_row.close()
check("و چیزی در دیتابیس ننشست", not _tok_now,
      "وگرنه رباتی بالا می‌آمد که هیچ‌وقت جواب نمی‌دهد")

# ── توکن درست ──
_res = AP.portal_bot_set({"token": "111222333:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"}, _TB)
check("توکن درست ثبت می‌شود", _res["ok"] and _res["username"] == "hossein_vpn_bot")

_row = _sq3.connect(str(AP.BOT_DB))
_r = _row.execute("SELECT bot_token, bot_username FROM tenants "
                  "WHERE portal_slug='hossein'").fetchone()
_row.close()
check("و در ردیف خودش نشست", _r[0] == "111222333:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw" and _r[1] == "hossein_vpn_bot")

# ── توکن هرگز برنمی‌گردد ──
_st = AP.portal_bot_get(AP._tenant_by_slug("hossein"))
check("وضعیت می‌گوید ربات هست", _st["hasBot"] and _st["username"] == "hossein_vpn_bot")
check("ولی توکن را برنمی‌گرداند",
      "token" not in _st and "111222333:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw" not in str(_st),
      "حتی به صاحب خودش هم دوباره نشان داده نمی‌شود")

# ── برند: فهرست مجاز ──
AP.portal_brand({"brand": "وی‌پی‌ان حسین", "support_username": "hsupport",
                 "panel_pass": "نفوذ", "credit": 99999999},
                AP._tenant_by_slug("hossein"))
_row = _sq3.connect(str(AP.BOT_DB))
_s2 = _row.execute("SELECT settings, credit FROM tenants "
                   "WHERE portal_slug='hossein'").fetchone()
_row.close()
_js = json.loads(_s2[0] or "{}")
check("برند ذخیره شد", _js.get("brand") == "وی‌پی‌ان حسین")
check("پشتیبانی هم", _js.get("support_username") == "hsupport")
check("ولی کلید خارج از فهرست مجاز ننشست", "panel_pass" not in _js,
      "settings کلیدهای حساس هم دارد — باز گذاشتنش یعنی نماینده چیزی "
      "را عوض کند که مال او نیست")

# ── جداکردن ──
AP.portal_bot_del(AP._tenant_by_slug("hossein"))
_row = _sq3.connect(str(AP.BOT_DB))
_gone = _row.execute("SELECT bot_token FROM tenants WHERE portal_slug='hossein'"
                     ).fetchone()[0]
_row.close()
check("جداکردن توکن را پاک می‌کند", not _gone)


# ═══════════════════════════════════════════════════════════
head("نماینده باید لینک اشتراک مشتری‌اش را ببیند")

# نماینده لینک را فقط موقع ساخت یک بار می‌دید. مشتری‌ای که لینکش را
# گم می‌کرد، نماینده هم نمی‌توانست کمکش کند.

_bd = _sq3.connect(str(AP.BOT_DB))
try:
    # یک مستاجر ریشه‌ی واقعی لازم است: نماینده‌ها باید parent داشته
    # باشند وگرنه جست‌وجوی «ریشه» به خودشان می‌رسد.
    _bd.execute("DELETE FROM tenants WHERE name='مالک'")
    _bd.execute("INSERT INTO tenants (name, parent_id, is_active, settings) "
                "VALUES ('مالک', NULL, 1, ?)",
                (json.dumps({"sub_base_url": "https://sub.example.ir/sub"}),))
    _root = _bd.execute("SELECT id FROM tenants WHERE name='مالک'").fetchone()[0]
    _bd.execute("UPDATE tenants SET parent_id=? WHERE name<>'مالک'", (_root,))
    _bd.execute("UPDATE tenants SET portal_group='goroh-a', portal_enabled=1,"
                " settings='{}' WHERE portal_slug='hossein'")
    _bd.commit()
finally:
    _bd.close()

AP._read_xui_clients = lambda *a, **k: (_ALL, [], None)
_cfgs = AP.portal_configs(AP._tenant_by_slug("hossein"))
_first = _cfgs["configs"][0] if _cfgs["configs"] else {}
check("هر ردیف لینک اشتراک دارد", bool(_first.get("subUrl")),
      str(_first.get("subUrl")))
check("و لینک با شناسه‌ی همان کانفیگ ساخته شده",
      str(_first.get("subUrl", "")).endswith(_first.get("subId")
                                             or _first.get("email", "")),
      _first.get("subUrl", ""))
check("پایه از تنظیمات مالک آمد",
      "sub.example.ir" in str(_first.get("subUrl")),
      "نماینده تنظیم خودش را نداشت، پس تنظیم مالک")


# ═══════════════════════════════════════════════════════════
head("پلن‌های مالک با پلن‌های نماینده قاطی نمی‌شوند")

# تا وقتی یک ربات بود فرقی نمی‌کرد. از وقتی نماینده ربات خودش را
# دارد، پلن‌هایش در فهرست پلن‌های مالک ظاهر می‌شدند — و چون ذخیره
# به مستاجر اصلی محدود است، حذفشان از آن فهرست «ok» می‌داد و هیچ
# کاری نمی‌کرد.

APSRC = io.open(os.path.join(str(ROOT), "backend", "app.py"),
                encoding="utf-8").read()
check("خواندن پلن‌ها به مستاجر محدود است",
      "SELECT * FROM plans WHERE tenant_id=? ORDER BY sort_order" in APSRC,
      "نوشتنش از اول محدود بود، خواندنش نه")
check("و نوشتنش هم هنوز محدود است",
      "WHERE id=? AND tenant_id=?" in APSRC
      and "DELETE FROM plans WHERE tenant_id=?" in APSRC)


# ═══════════════════════════════════════════════════════════
head("راه‌اندازی نماینده از پنل مدیر")

# چیزی که مدیر واقعاً دید: نماینده را ساخت، رمز گرفت، لینک را باز
# کرد، و پنل گفت «نشانی یا رمز نادرست است». رمز درست بود.
#
# دو علت داشت، هر دو در همین مسیر:
#   • group بی‌صدا دور ریخته می‌شد
#   • هیچ دکمه‌ای portal_enabled را یک نمی‌کرد، و ورود برای پنلِ
#     بسته همان پیام رمز غلط را می‌دهد

AP.load_password = lambda: "testpw"
AP._auth_fails.clear()

_bd = _sq3.connect(str(AP.BOT_DB))
try:
    _bd.execute("DELETE FROM tenants WHERE name='تازه‌وارد'")
    # نماینده همیشه فرزندِ ریشه است — همان کاری که tenant_create
    # می‌کند. بدون والد، در حسابداری «مالک» شمرده می‌شود و فهرست
    # نماینده‌ها هم درست نشانش نمی‌دهد.
    _proot = _bd.execute("SELECT id FROM tenants WHERE parent_id IS NULL "
                         "ORDER BY id LIMIT 1").fetchone()
    _bd.execute("INSERT INTO tenants (name, parent_id, is_active, credit) "
                "VALUES (?,?,1,?)",
                ("تازه‌وارد", _proot[0] if _proot else None, 0))
    _nid = _bd.execute("SELECT id FROM tenants WHERE name='تازه‌وارد'"
                       ).fetchone()[0]
    _bd.commit()
finally:
    _bd.close()

# همان چیزی که دکمه‌ی «ثبت» می‌فرستد
_r1 = AP.tenant_portal_set(_nid, {"slug": "tazevared", "group": "goroh-a"},
                           x_admin_password="testpw")
check("نشانی و گروه ثبت شد", _r1["ok"])

_row = _sq3.connect(str(AP.BOT_DB))
_g = _row.execute("SELECT portal_group FROM tenants WHERE id=?",
                  (_nid,)).fetchone()[0]
_row.close()
check("گروه واقعاً نشست", _g == "goroh-a",
      "قبلاً بی‌صدا دور ریخته می‌شد و نماینده هیچ کانفیگی نمی‌دید")

# هنوز رمز ندارد، پس نباید باز شده باشد
check("بدون رمز پنل باز نمی‌شود", not _r1.get("opened"),
      "باز کردنِ پنلی که رمز ندارد یعنی در باز بی‌قفل")

_bad = None
try:
    AP.portal_login("tazevared", {"password": "hich"}, None)
except Exception as e:
    _bad = getattr(e, "status_code", 0)
check("و ورود هم ممکن نیست", _bad == 401)

# همان چیزی که دکمه‌ی «رمز تازه بساز» می‌فرستد
_r2 = AP.tenant_portal_set(_nid, {"password": "rooz-e-khoob-1"},
                           x_admin_password="testpw")
check("رمز ثبت شد", _r2["ok"])
check("و حالا پنل خودش باز شد", _r2.get("opened") is True,
      "این همان چیزی بود که جا افتاده بود")

# و حالا باید بتواند وارد شود — همان کاری که مدیر کرد
AP._auth_fails.clear()
_in = AP.portal_login("tazevared", {"password": "rooz-e-khoob-1"}, None)
check("ورود با رمزی که پنل ساخت کار می‌کند", bool(_in.get("token")),
      "دقیقاً همان چیزی که کار نمی‌کرد")

# بستنِ صریح نباید با ویرایش بعدی خودبه‌خود باز شود
AP.tenant_portal_set(_nid, {"enabled": False}, x_admin_password="testpw")
_r3 = AP.tenant_portal_set(_nid, {"slug": "tazevared2"}, x_admin_password="testpw")
check("بستنِ صریح با ویرایش بعدی باز نمی‌شود", not _r3.get("opened"),
      "وگرنه بستنِ یک نماینده هیچ معنایی ندارد")

_row = _sq3.connect(str(AP.BOT_DB))
_e = _row.execute("SELECT COALESCE(portal_enabled,0) FROM tenants WHERE id=?",
                  (_nid,)).fetchone()[0]
_row.close()
check("و بسته می‌ماند", str(_e) in ("0", "", "None"), str(_e))

# فهرست باید بگوید رمز دارد یا نه، بدون اینکه رمز را بدهد
_lst = AP.tenant_portal_list(x_admin_password="testpw")
_me = [x for x in _lst["tenants"] if x["id"] == _nid]
check("فهرست می‌گوید رمز دارد", _me and _me[0]["hasPass"] is True)
check("ولی خودِ رمز را نمی‌دهد", "rooz-e-khoob-1" not in str(_lst),
      "پنل فقط باید بداند هست یا نه")


# ═══════════════════════════════════════════════════════════
head("شارژ اعتبار نماینده")

# بدون این، مدل پیش‌پرداخت فقط روی کاغذ کار می‌کرد: هیچ راهی برای
# شارژکردن نبود جز دست‌زدن به دیتابیس.

AP.load_password = lambda: "testpw"
AP._auth_fails.clear()
_bd = _sq3.connect(str(AP.BOT_DB))
try:
    _bd.execute("UPDATE tenants SET credit=0 WHERE portal_slug='hossein'")
    _bd.execute("DELETE FROM credit_tx")
    _bd.commit()
except Exception:
    pass
finally:
    _bd.close()

_cid = AP._tenant_by_slug("hossein")["id"]

_c = AP.tenant_credit(_cid, {"amount": 500000, "note": "شارژ اول"},
                      x_admin_password="testpw")
check("شارژ انجام شد", _c["credit"] == 500000, str(_c["credit"]))

_c = AP.tenant_credit(_cid, {"amount": -200000}, x_admin_password="testpw")
check("برداشت هم کار می‌کند", _c["credit"] == 300000, str(_c["credit"]))

try:
    AP.tenant_credit(_cid, {"amount": -999999}, x_admin_password="testpw")
    _neg = False
except Exception as e:
    _neg = getattr(e, "status_code", 0) == 400
check("اعتبار منفی نمی‌شود", _neg,
      "منفی در این سیستم معنای دیگری دارد: بدون سقف")

try:
    AP.tenant_credit(_cid, {"amount": 0}, x_admin_password="testpw")
    _z = False
except Exception as e:
    _z = getattr(e, "status_code", 0) == 400
check("مبلغ صفر رد می‌شود", _z)

_c = AP.tenant_credit(_cid, {"unlimited": True}, x_admin_password="testpw")
check("بدون سقف کردن کار می‌کند", _c["credit"] == -1 and _c["mode"] == "بدهکاری")

_c = AP.tenant_credit(_cid, {"amount": 100000}, x_admin_password="testpw")
check("و برگشت به پیش‌پرداخت از صفر شروع می‌شود", _c["credit"] == 100000,
      f"{_c['credit']} — نه از منفی یک")

# دفتر
_lg = AP.tenant_credit_log(_cid, x_admin_password="testpw")
# چهار تغییرِ واقعی: شارژ، برداشت، بدون‌سقف، شارژ دوباره.
# آن دو تای ردشده عمداً ثبت نمی‌شوند — دفتر باید کاری را نشان بدهد
# که انجام شده، نه تلاشی را که نشده.
check("هر تغییرِ انجام‌شده در دفتر ثبت شده", len(_lg["rows"]) == 4,
      f"{len(_lg['rows'])} سطر")
check("و تلاش‌های ردشده ثبت نشده‌اند",
      not any(r["amount"] == -999999 for r in _lg["rows"]))
check("و مانده‌ی بعد از هر تغییر هم هست",
      _lg["rows"][0]["balance"] == 100000, str(_lg["rows"][0]["balance"]))
check("و یادداشتش", "شارژ اول" in str(_lg["rows"]),
      "عددِ credit به‌تنهایی تاریخچه ندارد")

# خرجِ خودِ نماینده هم باید در همین دفتر بیفتد
_spent = AP._portal_charge(AP._tenant_by_slug("hossein"), 30000, "تست خرج")
check("کسر از سمت نماینده هم ثبت می‌شود", _spent[0])
_lg2 = AP.tenant_credit_log(_cid, x_admin_password="testpw")
check("و در دفتر با علامت منفی می‌نشیند",
      any(r["amount"] == -30000 for r in _lg2["rows"]),
      "وگرنه معلوم نیست اعتبار کجا رفت")


# ═══════════════════════════════════════════════════════════
head("پلن‌های ربات نماینده")

# رباتش بالا می‌آمد ولی مغازه‌اش خالی بود: plans به مستاجر محدود است
# و نماینده هیچ راهی برای ساختن پلن نداشت.

_T3 = AP._tenant_by_slug("hossein")
_other = AP._tenant_by_slug("bastan")

_bd = _sq3.connect(str(AP.BOT_DB))
try:
    _bd.execute("""CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id INTEGER,
        name TEXT, description TEXT, gb INTEGER, days INTEGER,
        ip_limit INTEGER, price INTEGER, inbound_id INTEGER,
        is_active INTEGER, is_trial INTEGER, sort_order INTEGER)""")
    _bd.execute("DELETE FROM plans")
    _bd.execute("INSERT INTO plans (tenant_id,name,gb,days,price,is_active,"
                "sort_order) VALUES (?,?,?,?,?,1,0)",
                (_other["id"], "مال نماینده‌ی دیگر", 10, 30, 50000))
    _oid = _bd.execute("SELECT id FROM plans").fetchone()[0]
    _bd.commit()
finally:
    _bd.close()

_r = AP.portal_bot_plans_save(
    {"plans": [{"name": "ماهانه ۵۰", "gb": 50, "days": 30,
                "ip_limit": 2, "price": 250000}]}, _T3)
check("پلن ساخته شد", _r["ok"] and _r["count"] == 1)

_mine = AP.portal_bot_plans(_T3)
check("و فقط مال خودش را می‌بیند",
      len(_mine["plans"]) == 1 and _mine["plans"][0]["name"] == "ماهانه ۵۰")

_theirs = AP.portal_bot_plans(_other)
check("پلن نماینده‌ی دیگر دست‌نخورده ماند",
      len(_theirs["plans"]) == 1
      and _theirs["plans"][0]["name"] == "مال نماینده‌ی دیگر",
      "ذخیره‌ی یکی نباید پلن‌های دیگری را پاک کند")

# فرستادن شناسه‌ی پلن نماینده‌ی دیگر نباید کاری بکند
AP.portal_bot_plans_save(
    {"plans": [{"id": _oid, "name": "دزدیده", "gb": 1, "days": 1,
                "price": 1}]}, _T3)
_theirs2 = AP.portal_bot_plans(_other)
check("شناسه‌ی پلن دیگری هم کاری نمی‌کند",
      _theirs2["plans"] and _theirs2["plans"][0]["name"] == "مال نماینده‌ی دیگر",
      "به‌روزرسانی با WHERE id=? AND tenant_id=? محدود است")

try:
    AP.portal_bot_plans_save({"plans": [{"name": "", "gb": 1}]}, _T3)
    _noname = False
except Exception as e:
    _noname = getattr(e, "status_code", 0) == 400
check("پلن بی‌نام رد می‌شود", _noname)

_r2 = AP.portal_bot_plans_save({"plans": []}, _T3)
check("فهرست خالی همه‌ی پلن‌های خودش را پاک می‌کند", _r2["count"] == 0)
check("ولی باز هم مال دیگری سر جایش است",
      len(AP.portal_bot_plans(_other)["plans"]) == 1)

APS = io.open(os.path.join(str(ROOT), "backend", "app.py"),
              encoding="utf-8").read()
check("پلن آزمایشی دست نماینده نیست", '"is_trial": 0,' in APS,
      "کانفیگ رایگان روی سرور مالک ساخته می‌شود — تصمیمش با اوست")


# ═══════════════════════════════════════════════════════════
head("لینک اشتراک باید پیدا شود، حتی وقتی کسی تنظیمش نکرده")

# این همان چیزی بود که نماینده می‌دید: کانفیگ ساخته می‌شد ولی هیچ
# لینکی برای تحویل نبود، و هیچ‌جا نمی‌گفت چرا. علتش این بود که همه‌چیز
# به sub_base_url دستی وابسته بود.

_bd = _sq3.connect(str(AP.BOT_DB))
try:
    _bd.execute("UPDATE tenants SET settings='{}'")
    _bd.commit()
finally:
    _bd.close()
AP._SUB_BASE_CACHE.clear()


class _SubXUI:
    def panel_sub_base(self):
        return "https://sub.panel.ir:2096/sub"


AP._portal_xui = lambda t: (_SubXUI(), Exception)
_tt = AP._tenant_by_slug("hossein")
check("وقتی کسی تنظیم نکرده، از خود پنل خوانده می‌شود",
      AP._sub_base(_tt) == "https://sub.panel.ir:2096/sub",
      "پنل خودش این را می‌داند — ربات از روز اول همین کار را می‌کرد")

AP._SUB_BASE_CACHE.clear()
_bd = _sq3.connect(str(AP.BOT_DB))
try:
    _bd.execute("UPDATE tenants SET settings=? WHERE parent_id IS NULL",
                (json.dumps({"sub_base_url": "https://owner.ir/sub"}),))
    _bd.commit()
finally:
    _bd.close()
check("ولی تنظیم مالک بر آن مقدم است",
      AP._sub_base(AP._tenant_by_slug("hossein")) == "https://owner.ir/sub")

AP._SUB_BASE_CACHE.clear()
_bd = _sq3.connect(str(AP.BOT_DB))
try:
    _bd.execute("UPDATE tenants SET settings=? WHERE portal_slug='hossein'",
                (json.dumps({"sub_base_url": "https://mine.ir/sub/"}),))
    _bd.commit()
finally:
    _bd.close()
check("و تنظیم خودِ نماینده بر همه",
      AP._sub_base(AP._tenant_by_slug("hossein")) == "https://mine.ir/sub",
      "اسلش آخر هم برداشته می‌شود تا لینک دوتا اسلش نگیرد")


# ═══════════════════════════════════════════════════════════
head("آمار نماینده باید کاربردی باشد، نه شمارش خشک")

# «۹۴ کانفیگ» به نماینده نمی‌گوید کدام مشتری دارد از دست می‌رود.
# چیزی که می‌شود رویش کاری کرد این است: چند تا دارند تمام می‌شوند،
# چند تا حجمشان پر شده.

import time as _tm  # noqa: E402
_now = int(_tm.time() * 1000)
_STAT = [
    # فعال، جای زیادی مانده
    {"email": "s1", "group": "goroh-a", "totalGB": 100 * 1024**3,
     "used": 10 * 1024**3, "enable": True, "createdAt": "2026-01-01",
     "expiry": _now + 40 * 86400000, "limitIp": 2, "subId": "s1"},
    # تا سه روز دیگر تمام می‌شود
    {"email": "s2", "group": "goroh-a", "totalGB": 50 * 1024**3,
     "used": 5 * 1024**3, "enable": True, "createdAt": "2026-01-01",
     "expiry": _now + 3 * 86400000, "limitIp": 1, "subId": "s2"},
    # منقضی
    {"email": "s3", "group": "goroh-a", "totalGB": 50 * 1024**3,
     "used": 5 * 1024**3, "enable": False, "createdAt": "2026-01-01",
     "expiry": _now - 5 * 86400000, "limitIp": 1, "subId": "s3"},
    # حجمش تمام شده
    {"email": "s4", "group": "goroh-a", "totalGB": 10 * 1024**3,
     "used": 10 * 1024**3, "enable": True, "createdAt": "2026-01-01",
     "expiry": _now + 20 * 86400000, "limitIp": 1, "subId": "s4"},
    # نزدیک سقف
    {"email": "s5", "group": "goroh-a", "totalGB": 10 * 1024**3,
     "used": 9 * 1024**3, "enable": True, "createdAt": "2026-01-01",
     "expiry": _now + 20 * 86400000, "limitIp": 1, "subId": "s5"},
    # نامحدود و بدون انقضا
    {"email": "s6", "group": "goroh-a", "totalGB": 0, "used": 1 * 1024**3,
     "enable": True, "createdAt": "2026-01-01", "expiry": 0,
     "limitIp": 0, "subId": "s6"},
    # مالِ نماینده‌ی دیگر — نباید شمرده شود
    {"email": "x1", "group": "goroh-b", "totalGB": 0, "used": 99 * 1024**3,
     "enable": True, "createdAt": "2026-01-01", "expiry": 0,
     "limitIp": 0, "subId": "x1"},
]
AP._read_xui_clients = lambda *a, **k: (_STAT, [], None)

_bd = _sq3.connect(str(AP.BOT_DB))
try:
    _bd.execute("UPDATE tenants SET portal_group='goroh-a', portal_enabled=1 "
                "WHERE portal_slug='hossein'")
    _bd.commit()
finally:
    _bd.close()

_st = AP.portal_stats(t=AP._tenant_by_slug("hossein"))
check("فقط کاربران خودش شمرده می‌شوند", _st["total"] == 6, str(_st["total"]))
check("رو به اتمام درست است", _st["expiringSoon"] == 1, str(_st["expiringSoon"]))
check("منقضی‌ها جدا شمرده می‌شوند", _st["expired"] == 1, str(_st["expired"]))
check("حجم‌تمام‌شده جدا از نزدیک‌به‌سقف",
      _st["overQuota"] == 1 and _st["nearQuota"] == 1,
      f"تمام‌شده {_st['overQuota']} · نزدیک {_st['nearQuota']}")
check("نامحدودها در سقف حساب نمی‌شوند", _st["unlimitedQuota"] == 1,
      "درصدی از بی‌نهایت معنا ندارد")
# «فعال» یعنی روشن و منقضی‌نشده. کانفیگی که حجمش تمام شده هنوز
# فعال است و جداگانه در overQuota شمرده می‌شود — دو چیز متفاوت‌اند
# و نماینده باید هر دو را ببیند.
check("فعال یعنی روشن و منقضی‌نشده", _st["active"] == 5, str(_st["active"]))
check("و غیرفعال‌ها بقیه‌اند", _st["inactive"] == 1, str(_st["inactive"]))
check("و «نیاز به پیگیری» جمعشان است",
      _st["needsAttention"] == 1 + 1 + 1,
      f"{_st['needsAttention']} — رو به اتمام + منقضی + حجم تمام")
check("مصرف نماینده‌ی دیگر داخلش نیست", _st["usedGB"] < 99,
      f"{_st['usedGB']} GB")


# ═══════════════════════════════════════════════════════════
head("رسید و تایید سفارش در پنل نماینده")

# مشتریِ نماینده از رباتِ او سفارش می‌دهد و رسید می‌فرستد. تا امروز
# تنها جای تاییدش گروه تلگرام بود؛ نماینده‌ای که گروه نداشت، سفارشش
# برای همیشه در انتظار می‌ماند.

_bd = _sq3.connect(str(AP.BOT_DB))
try:
    _bd.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id INTEGER,
        user_id INTEGER, plan_id INTEGER, kind TEXT, amount INTEGER,
        base_amount INTEGER, coins_used INTEGER, paid_from TEXT,
        status TEXT, receipt_type TEXT, receipt_file TEXT,
        receipt_text TEXT, admin_note TEXT, sub_id INTEGER,
        created_at TEXT)""")
    _bd.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id INTEGER,
        tg_id INTEGER, first_name TEXT, username TEXT)""")
    _bd.execute("DELETE FROM orders")
    _bd.execute("DELETE FROM users WHERE tg_id IN (7001, 7002)")

    _h = AP._tenant_by_slug("hossein")
    _b = AP._tenant_by_slug("bastan")
    _bd.execute("INSERT INTO users (tenant_id,tg_id,first_name) VALUES (?,?,?)",
                (_h["id"], 7001, "مشتریِ حسین"))
    _u1 = _bd.execute("SELECT id FROM users WHERE tg_id=7001").fetchone()[0]
    _bd.execute("INSERT INTO users (tenant_id,tg_id,first_name) VALUES (?,?,?)",
                (_b["id"], 7002, "مشتریِ دیگری"))
    _u2 = _bd.execute("SELECT id FROM users WHERE tg_id=7002").fetchone()[0]

    _bd.execute("INSERT INTO orders (tenant_id,user_id,kind,amount,base_amount,"
                "paid_from,status,receipt_file,created_at) "
                "VALUES (?,?,'new',250000,250000,'card','awaiting','file-1',"
                "'2026-09-15')", (_h["id"], _u1))
    _mine = _bd.execute("SELECT id FROM orders WHERE user_id=?", (_u1,)).fetchone()[0]
    _bd.execute("INSERT INTO orders (tenant_id,user_id,kind,amount,base_amount,"
                "paid_from,status,created_at) "
                "VALUES (?,?,'new',99000,99000,'card','awaiting','2026-09-15')",
                (_b["id"], _u2))
    _theirs = _bd.execute("SELECT id FROM orders WHERE user_id=?", (_u2,)).fetchone()[0]
    _bd.commit()
finally:
    _bd.close()

_T4 = AP._tenant_by_slug("hossein")

_lst = AP.portal_orders(t=_T4)
_ids = [o["id"] for o in _lst["orders"]]
check("فقط سفارش‌های مشتری‌های خودش", _ids == [_mine], str(_ids))
check("سفارش نماینده‌ی دیگر نیست", _theirs not in _ids,
      "همان محدودسازی‌ای که همه‌جای این پنل هست")
check("و می‌گوید رسید دارد", _lst["orders"][0]["hasReceipt"] is True)
check("مبلغ و نام مشتری می‌آید",
      _lst["orders"][0]["amount"] == 250000
      and _lst["orders"][0]["customer"] == "مشتریِ حسین")

# دست‌درازی به سفارش دیگری
for _fn, _nm in ((AP.portal_order_approve, "تایید"),
                 (AP.portal_receipt, "دیدن رسید")):
    try:
        _fn(_theirs, t=_T4)
        _blocked = False
    except Exception as e:
        _blocked = getattr(e, "status_code", 0) == 404
    check(f"{_nm} سفارش نماینده‌ی دیگر رد می‌شود", _blocked,
          "پیامش همان «پیدا نشد» است — وگرنه می‌شود شناسه‌ها را کشف کرد")

try:
    AP.portal_order_reject(_theirs, {"reason": "چون"}, t=_T4)
    _rb = False
except Exception as e:
    _rb = getattr(e, "status_code", 0) == 404
check("رد سفارش نماینده‌ی دیگر هم", _rb)

# بدون ربات نمی‌شود تایید کرد
_bd = _sq3.connect(str(AP.BOT_DB))
try:
    _bd.execute("UPDATE tenants SET bot_token=NULL WHERE portal_slug='hossein'")
    _bd.commit()
finally:
    _bd.close()
try:
    AP.portal_order_approve(_mine, t=AP._tenant_by_slug("hossein"))
    _nobot = False
except Exception as e:
    _nobot = getattr(e, "status_code", 0) == 409
check("بدون ربات، تایید ممکن نیست", _nobot,
      "تاییدِ بی‌خبر یعنی مشتری پولش را داده و هیچ‌چیز نمی‌بیند")

# دلیل رد اجباری است
try:
    AP.portal_order_reject(_mine, {"reason": "  "}, t=AP._tenant_by_slug("hossein"))
    _nore = False
except Exception as e:
    _nore = getattr(e, "status_code", 0) == 400
check("رد بدون دلیل ممکن نیست", _nore, "مشتری همان دلیل را می‌بیند")

APO = io.open(os.path.join(str(ROOT), "backend", "app.py"),
              encoding="utf-8").read()
check("تایید همان کد ربات را صدا می‌زند",
      "h.approve_order(ctx, oid" in APO,
      "مسیر پول دو پیاده‌سازی برنمی‌دارد")
check("رد هم همین‌طور", "h.do_reject(ctx, oid" in APO)
check("و «همین حالا در حال پردازش» را هم می‌فهمد",
      "ORDER_BUSY" in APO,
      "وگرنه نماینده دوباره تایید می‌زند، درست وقتی که نباید")
check("رسید با توکن ربات پاس داده می‌شود نه آدرسش",
      "api.telegram.org/file/bot" in APO and "Response(content=blob" in APO,
      "آن آدرس توکن ربات را در خودش دارد")


# ═══════════════════════════════════════════════════════════
head("پرچمِ باز/بسته یک جواب دارد، نه سه تا")

# سه جا portal_enabled را می‌خواندند و هر کدام جور دیگری:
#
#   ورود        CAST(... AS INTEGER)=1   — فقط عددِ یک
#   بررسی نشست  not in ("0","","None")   — هرچه ناشناخته، باز
#   فهرست مدیر  همان فهرست ممنوع
#
# روی ۰ و ۱ هر سه یکی‌اند. روی هر مقدار دیگری ورود می‌بست و نشستِ
# باز، باز می‌ماند — یعنی بستنِ یک نماینده، نشستِ فعلی‌اش را نمی‌بست،
# درست برعکسِ چیزی که بالای همان کد نوشته شده بود.

_VALUES = [1, 0, "1", "0", None, 2, "true", "yes", "", "01", 1.0,
           True, False, " 1 ", "-1", "1.0"]

# ورود و بررسی نشست باید روی *هر* مقداری یک جواب بدهند. این را با
# خودِ دو مسیر می‌سنجیم، نه با بازنویسی شرطشان در تست — تستی که
# قاعده را دوباره پیاده کند، فقط بازنویسی خودش را می‌آزماید.
_drift = []
_fb = _sq3.connect(str(AP.BOT_DB))
try:
    for _v in _VALUES:
        _fb.execute("UPDATE tenants SET portal_enabled=? "
                    "WHERE portal_slug='hossein'", (_v,))
        _fb.commit()
        # مقدارِ *ذخیره‌شده* را می‌خوانیم، نه آنچه فرستادیم: ستون
        # affinity عددی دارد و SQLite رشته‌ی '1.0' را همان موقع به ۱
        # تبدیل می‌کند. مقایسه با مقدار خام یعنی سنجیدن چیزی که
        # هیچ‌وقت در دیتابیس ننشسته.
        _stored = _fb.execute("SELECT portal_enabled FROM tenants "
                              "WHERE portal_slug='hossein'").fetchone()[0]
        _login_ok = AP._tenant_by_slug("hossein") is not None
        _sess_ok = AP._portal_open(_stored)
        if _login_ok != _sess_ok:
            _drift.append(f"{_v!r}→{_stored!r}: ورود {_login_ok} · "
                          f"نشست {_sess_ok}")
    # برگرداندن به حالت باز، تا بقیه‌ی تست‌ها به هم نریزند
    _fb.execute("UPDATE tenants SET portal_enabled=1 "
                "WHERE portal_slug='hossein'")
    _fb.commit()
finally:
    _fb.close()

check("ورود و بررسی نشست یک جواب می‌دهند", not _drift,
      "، ".join(_drift) if _drift
      else f"{len(_VALUES)} مقدار سنجیده شد")

check("فقط یک، باز است",
      AP._portal_open(1) and AP._portal_open("1") and AP._portal_open(True))
check("صفر و خالی و None بسته‌اند",
      not any(AP._portal_open(v) for v in (0, "0", "", None, False)))
check("مقدار ناشناخته باز نیست — فهرست مجاز، نه ممنوع",
      not any(AP._portal_open(v) for v in (2, "true", "yes", "-1")),
      "همین‌ها بودند که نشست را باز نگه می‌داشتند")

_src_ap = io.open(str(ROOT / "backend" / "app.py"),
                  encoding="utf-8").read()
check("هیچ‌جا فهرست ممنوعِ قدیمی نمانده",
      'in ("0", "", "None")' not in _src_ap,
      "هر سه جا باید از _portal_open بگیرند")
check("و شرط در SQL دوباره پیاده نشده",
      "CAST(COALESCE(portal_enabled,0) AS INTEGER)" not in _src_ap,
      "دو پیاده‌سازی از یک قاعده، دیر یا زود از هم جدا می‌شوند")
check("بررسی نشست از همان تابع می‌گیرد",
      "not _portal_open(\n            t.get(\"portal_enabled\"))" in _src_ap
      or "_portal_open(t.get(\"portal_enabled\"))" in _src_ap)


# ═══════════════════════════════════════════════════════════
head("بدهی به همکاران نباید بدهی نماینده‌ها را هم بشمارد")

# صفحه‌ی همکاری «مجموع بدهی به همکاران» را نشان می‌دهد و دفتر کل
# همان عدد را از `_affiliate_money_out` می‌گیرد. دفتر کل فقط
# مستاجرهای ریشه را می‌شمارد — چون پورسانتِ همکارِ یک نماینده،
# هزینه‌ی همان نماینده است. صفحه هیچ شرطی نداشت و هر دو را با هم
# جمع می‌کرد، پس دو صفحه به یک سؤال دو جواب می‌دادند.

# تست بازگردانی، بالاتر در همین فایل، دیتابیس را با یک نسخه‌ی
# پشتیبانِ کوچک جایگزین می‌کند و جدول‌های همکاری در آن نیستند.
# init_db همان اسکیمای واقعی را دوباره می‌سازد (IF NOT EXISTS)، پس
# تست به جای کپی‌کردن تعریفِ جدول‌ها، خودِ منبع را صدا می‌زند.
botdb.init_db()

# مستاجرهای خودمان را می‌سازیم و به آنچه تست‌های قبلی گذاشته‌اند
# تکیه نمی‌کنیم: در این دیتابیس مستاجر ۱ خودش فرزندِ ۳ است.
_ab = _sq3.connect(str(AP.BOT_DB))
_ab.executescript("""
INSERT OR REPLACE INTO tenants (id, name, parent_id)
  VALUES (9000, 'مالک تستی', NULL);
INSERT OR REPLACE INTO tenants (id, name, parent_id)
  VALUES (9001, 'نماینده‌ی تستی', 9000);

INSERT INTO affiliates (id, tenant_id, name, code, percent, active)
  VALUES (9101, 9000, 'همکار خودم', 'MINE', 10, 1);
INSERT INTO affiliate_commissions
  (tenant_id, affiliate_id, order_id, order_amount, percent, commission, status)
  VALUES (9000, 9101, 91011, 3000000, 10, 300000, 'pending');
INSERT INTO affiliate_payouts (tenant_id, affiliate_id, amount)
  VALUES (9000, 9101, 100000);

INSERT INTO affiliates (id, tenant_id, name, code, percent, active)
  VALUES (9102, 9001, 'همکار نماینده', 'THEIRS', 10, 1);
INSERT INTO affiliate_commissions
  (tenant_id, affiliate_id, order_id, order_amount, percent, commission, status)
  VALUES (9001, 9102, 91021, 5000000, 10, 500000, 'pending');
""")
_ab.commit()
_ab.close()

_aff = app.bot_affiliates(x_admin_password=PW)
_rows = {r["id"]: r for r in _aff.get("affiliates", [])}

check("هر دو همکار در فهرست می‌آیند", 9101 in _rows and 9102 in _rows,
      "همکارِ نماینده نباید ناپدید شود — پنل نماینده اصلا این بخش را ندارد")
check("همکار خودم «مالِ خودم» علامت می‌خورد",
      _rows.get(9101, {}).get("isOwn") is True)
check("همکار نماینده نه", _rows.get(9102, {}).get("isOwn") is False,
      "وگرنه از همکارِ خودتان قابل تشخیص نیست")
check("و نامِ نماینده‌اش می‌آید",
      _rows.get(9102, {}).get("tenantName") == "نماینده‌ی تستی",
      _rows.get(9102, {}).get("tenantName") or "—")

check("مانده‌ی همکار خودم درست است",
      _rows.get(9101, {}).get("balance") == 200_000,
      str(_rows.get(9101, {}).get("balance")))

# همان چیزی که دفتر کل می‌گوید
_lpaid, _lowed = AP._affiliate_money_out()
check("«مجموع بدهی» با دفتر کل یکی است",
      _aff.get("totalOwed") == _lowed,
      f"صفحه {_aff.get('totalOwed')} · دفتر کل {_lowed}")
check("و این برابری با «هر دو صفر» بی‌معنی نشده",
      _lowed >= 200_000, f"دفتر کل: {_lowed}")
check("و بدهیِ نماینده‌ها جدا شمرده می‌شود",
      _aff.get("resellerOwed") == 500_000,
      str(_aff.get("resellerOwed")))
_all_bal = sum(r["balance"] for r in _aff.get("affiliates", []))
check("تفکیک کامل است و چیزی گم نمی‌شود",
      _aff.get("totalOwed", 0) + _aff.get("resellerOwed", 0) == _all_bal
      and _aff.get("totalOwed") != _all_bal,
      f"کل {_all_bal} = خودم {_aff.get('totalOwed')} + "
      f"نماینده {_aff.get('resellerOwed')}")

# و همان شرط، نه یک بازنویسیِ موازی
_apsrc = io.open(os.path.join(str(ROOT), "backend", "app.py"),
                 encoding="utf-8").read()
_blk = _apsrc[_apsrc.index("def bot_affiliates("):]
_blk = _blk[:_blk.index("@app.post")]
check("شرط ریشه‌بودن همان عبارت دفتر کل است",
      "parent_id IS NULL" in _blk,
      "دو پیاده‌سازی از یک قاعده، دیر یا زود از هم جدا می‌شوند")


# ═══════════════════════════════════════════════════════════
head("قیف تبدیل باید خریدار را از کسی که فقط تست گرفته جدا کند")

# گرفتنِ تست رایگان خودش یک سفارشِ approved می‌سازد (مبلغ صفر). پس
# با شرطِ ساده‌ی status='approved':
#
#   • هر کسی که دکمه‌ی تست را زده «خرید موفق» شمرده می‌شد
#   • و بخشِ «فقط تست گرفتند» هیچ‌وقت نمی‌توانست چیزی جز صفر باشد،
#     چون همان تست برایش یک سفارشِ approved ثبت کرده بود
#
# قیف دقیقاً برای جداکردنِ همین دو گروه ساخته شده.
#
# روی یک دیتابیس تازه سنجیده می‌شود تا عددها دقیق باشند، نه وابسته
# به آنچه تست‌های قبلی در این فایل جا گذاشته‌اند.

_fdb = _tf.mktemp(suffix=".db")
_old_botdb_path = botdb.DB_PATH
_old_app_db = app.BOT_DB
botdb.DB_PATH = Path(_fdb)
try:
    botdb.init_db()
    _ftid = botdb.create_tenant("قیف", bot_token="1:F", owner_tg_id=1)
    _fc = _sq3.connect(_fdb)
    _fc.executescript(f"""
    INSERT INTO plans (id, tenant_id, name, price, gb, days, is_trial)
      VALUES (8001, {_ftid}, 'تست رایگان', 0, 1, 1, 1);
    INSERT INTO plans (id, tenant_id, name, price, gb, days, is_trial)
      VALUES (8002, {_ftid}, '۳۰ گیگ', 200000, 30, 30, 0);

    -- الف: تستش گرفت، هیچ‌وقت نخرید
    INSERT INTO users (id, tenant_id, tg_id, trial_used) VALUES (1, {_ftid}, 101, 1);
    INSERT INTO orders (tenant_id, user_id, plan_id, amount, base_amount, status)
      VALUES ({_ftid}, 1, 8001, 0, 0, 'approved');

    -- ب: تست گرفت و بعد خرید
    INSERT INTO users (id, tenant_id, tg_id, trial_used) VALUES (2, {_ftid}, 102, 1);
    INSERT INTO orders (tenant_id, user_id, plan_id, amount, base_amount, status)
      VALUES ({_ftid}, 2, 8001, 0, 0, 'approved');
    INSERT INTO orders (tenant_id, user_id, plan_id, amount, base_amount, status)
      VALUES ({_ftid}, 2, 8002, 200000, 200000, 'approved');

    -- ج: بدون تست، مستقیم خرید
    INSERT INTO users (id, tenant_id, tg_id, trial_used) VALUES (3, {_ftid}, 103, 0);
    INSERT INTO orders (tenant_id, user_id, plan_id, amount, base_amount, status)
      VALUES ({_ftid}, 3, 8002, 200000, 200000, 'approved');

    -- د: تستش شکست خورد ولی سفارشش approved مانده بود (باگ قدیمی)
    INSERT INTO users (id, tenant_id, tg_id, trial_used) VALUES (4, {_ftid}, 104, 0);
    INSERT INTO orders (tenant_id, user_id, plan_id, amount, base_amount, status)
      VALUES ({_ftid}, 4, 8001, 0, 0, 'approved');

    -- ه: هیچ کاری نکرد
    INSERT INTO users (id, tenant_id, tg_id, trial_used) VALUES (5, {_ftid}, 105, 0);
    """)
    _fc.commit()
    _fc.close()

    app.BOT_DB = Path(_fdb)
    _fun = app.bot_funnel(x_admin_password=PW)
finally:
    app.BOT_DB = _old_app_db
    botdb.DB_PATH = _old_botdb_path

check("قیف خوانده شد", _fun.get("ready") is True)

_seg = _fun.get("segments") or {}
_steps = {st["label"]: st["n"] for st in (_fun.get("steps") or [])}

check("پنج کاربر دیده می‌شوند", _fun.get("started") == 5,
      str(_fun.get("started")))
check("«خرید موفق» فقط دو نفرند", _seg.get("paid") == 2,
      f"{_seg.get('paid')} — فقط ب و ج واقعا خریدند")
check("و کسی که تستش شکست خورد جزوشان نیست", _seg.get("paid") != 4,
      "قبلا هر چهار نفر «خرید موفق» بودند")
check("«فقط تست گرفتند» یک نفر است", _seg.get("trialOnly") == 1,
      f"{_seg.get('trialOnly')} — الف")
check("و این عدد دیگر همیشه صفر نیست", _seg.get("trialOnly") > 0,
      "قبلا ساختارا نمی‌توانست چیزی جز صفر باشد")
check("«تست گرفتند» هر دو نفرند", _seg.get("trial") == 2,
      str(_seg.get("trial")))
check("«سفارش ثبت کردند» یعنی از مسیر خرید رد شدند",
      _steps.get("سفارش ثبت کردند") == 2, str(_steps))
check("و گام «خرید موفق» با بخشش می‌خواند",
      _steps.get("خرید موفق") == _seg.get("paid"),
      f"{_steps.get('خرید موفق')} در برابر {_seg.get('paid')}")

# یک عبارت، نه دو تا — وگرنه دو شمارش از یک قاعده از هم جدا می‌شوند
_fsrc = io.open(os.path.join(str(ROOT), "backend", "app.py"),
                encoding="utf-8").read()
_fblk = _fsrc[_fsrc.index("def bot_funnel("):]
_fblk = _fblk[:_fblk.index("SNAP_DIR")]
check("قاعده‌ی «خرید واقعی» یک بار نوشته شده",
      _fblk.count("REAL_BUY") >= 3 and _fblk.count("is_trial") <= 2,
      "یک تعریف و دو استفاده")


# ═══════════════════════════════════════════════════════════
head("اینباندِ هر نماینده مالِ خودش است")

# این دستور `WHERE` نداشت:
#
#     UPDATE tenants SET inbound_mode=?, inbound_ids=?
#
# یعنی هر بار که مالک اینباندهای خودش را ذخیره می‌کرد، همان تنظیم
# بی‌صدا روی تک‌تک نماینده‌ها هم می‌نشست و انتخابِ خودشان پاک می‌شد.
# و خواندنش همیشه از مستاجر ریشه بود، پس تنظیمِ نماینده نه دیده
# می‌شد و نه قابل تغییر.

botdb.init_db()
_rb = _sq3.connect(str(AP.BOT_DB))
_rb.executescript("""
INSERT OR REPLACE INTO tenants (id, name, parent_id, inbound_mode, inbound_ids)
  VALUES (7000, 'مالک تستی', NULL, 'all', NULL);
INSERT OR REPLACE INTO tenants (id, name, parent_id, inbound_mode, inbound_ids)
  VALUES (7001, 'نماینده الف', 7000, 'all', NULL);
INSERT OR REPLACE INTO tenants (id, name, parent_id, inbound_mode, inbound_ids)
  VALUES (7002, 'نماینده ب', 7000, 'all', NULL);
""")
_rb.commit()
_rb.close()


def _inb(tid):
    c = _sq3.connect(str(AP.BOT_DB))
    try:
        r = c.execute("SELECT inbound_mode, inbound_ids FROM tenants "
                      "WHERE id=?", (tid,)).fetchone()
        return (r[0], r[1]) if r else (None, None)
    finally:
        c.close()


app.bot_inbounds_set({"mode": "custom", "ids": [41], "tenant": 7001},
                     x_admin_password=PW)
check("تنظیم نماینده‌ی الف نوشته شد", _inb(7001) == ("custom", "[41]"),
      str(_inb(7001)))
check("نماینده‌ی ب دست نخورد", _inb(7002)[0] == "all",
      f"{_inb(7002)} — قبلا این هم عوض می‌شد")
check("و مالک هم دست نخورد", _inb(7000)[0] == "all", str(_inb(7000)))

# و حالا مالک تنظیم خودش را ذخیره می‌کند.
#
# «ریشه» همان چیزی است که خودِ کد برمی‌دارد — کوچک‌ترین شناسه‌ای که
# parent_id ندارد. این دیتابیسِ تست چند ریشه دارد چون بخش‌های قبلی
# ساخته‌اند؛ روی نصبِ واقعی فقط یکی هست.
_rc = _sq3.connect(str(AP.BOT_DB))
_root_id = _rc.execute("SELECT id FROM tenants WHERE parent_id IS NULL "
                       "ORDER BY id LIMIT 1").fetchone()[0]
_rc.close()
_res = app.bot_inbounds_set({"mode": "custom", "ids": [28]},
                            x_admin_password=PW)
check("بدون tenant، تنظیم روی مستاجر ریشه می‌نشیند",
      _res.get("tenant") == _root_id, f"{_res.get('tenant')} در برابر {_root_id}")
_root_now = _inb(_root_id)
check("و واقعا نوشته شد",
      _root_now[0] == "custom" and "28" in (_root_now[1] or ""),
      str(_root_now))
check("و انتخابِ نماینده‌ی الف را پاک نمی‌کند",
      _inb(7001) == ("custom", "[41]"), str(_inb(7001)))
check("و نماینده‌ی ب را هم نه", _inb(7002)[0] == "all", str(_inb(7002)))

_bad = None
try:
    app.bot_inbounds_set({"mode": "all", "tenant": 999999},
                         x_admin_password=PW)
except Exception as e:      # noqa: BLE001
    _bad = getattr(e, "status_code", 0)
check("نماینده‌ی ناموجود ۴۰۴ می‌گیرد", _bad == 404, str(_bad))

_srcmod = io.open(os.path.join(str(ROOT), "backend", "app.py"),
                  encoding="utf-8").read()
_wblk = _srcmod[_srcmod.index("def bot_inbounds_set("):]
_wblk = _wblk[:_wblk.index("\n@app.")]
_wcode = "\n".join(l for l in _wblk.split("\n")
                   if not l.strip().startswith("#"))
check("دستور نوشتن بدون WHERE نمانده",
      "UPDATE tenants SET inbound_mode=?, inbound_ids=? WHERE" in _wcode,
      "بدون WHERE روی همه‌ی مستاجرها می‌نویسد")

# ═══════════════════════════════════════════════════════════
head("ساخت نماینده — که تا امروز اصلا ممکن نبود")

_made = app.tenant_create(
    {"name": "نماینده تازه", "slug": "TazeH-1", "password": "abcd1234efgh",
     "group": "g-taze", "credit": 0}, x_admin_password=PW)
check("ساخته شد", _made.get("ok") and _made.get("id"), str(_made)[:70])

_row = _sq3.connect(str(AP.BOT_DB)).execute(
    "SELECT name, parent_id, portal_slug, portal_pass, portal_group, "
    "portal_enabled, credit FROM tenants WHERE id=?",
    (_made["id"],)).fetchone()
check("فرزندِ مستاجر ریشه است", _row[1] is not None,
      "وگرنه در حسابداری «مالک» شمرده می‌شود و درآمدش با شما قاطی می‌شود")
check("نشانی پاک‌سازی و کوچک شد", _row[2] == "tazeh-1", _row[2])
check("رمزش ثبت شد", _row[3] == "abcd1234efgh")
check("گروهش ثبت شد", _row[4] == "g-taze")
check("و پنلش بسته ساخته می‌شود", _row[5] == 0,
      "تا گروه و رمز ثبت نشده، بازکردنش فقط صفحه‌ی ورودِ بی‌فایده است")
check("پیش‌پرداخت بودنش ثبت شد", _row[6] == 0, str(_row[6]))

# نشانی تکراری یعنی دو نماینده به یک لینک می‌رسند
_dup = None
try:
    app.tenant_create({"name": "دیگری", "slug": "tazeh-1",
                       "password": "abcd1234efgh"}, x_admin_password=PW)
except Exception as e:      # noqa: BLE001
    _dup = getattr(e, "status_code", 0)
check("نشانی تکراری رد می‌شود", _dup == 400, str(_dup))

for _bad_payload, _why in (
        ({"slug": "x1", "password": "abcd1234efgh"}, "بدون نام"),
        ({"name": "ب", "password": "abcd1234efgh"}, "بدون نشانی"),
        ({"name": "ب", "slug": "x2", "password": "123"}, "رمز کوتاه")):
    _e = None
    try:
        app.tenant_create(_bad_payload, x_admin_password=PW)
    except Exception as ex:      # noqa: BLE001
        _e = getattr(ex, "status_code", 0)
    check(f"{_why} رد می‌شود", _e == 400, str(_e))

# و نماینده‌ی تازه واقعا در فهرست پنل نمایندگی می‌آید
_lst = app.tenant_portal_list(x_admin_password=PW)
check("در فهرست پنل نمایندگی دیده می‌شود",
      any(t["id"] == _made["id"] for t in _lst.get("tenants", [])),
      "وگرنه ساخته شده ولی هیچ‌جا نیست")


# ═══════════════════════════════════════════════════════════
head("آمار فروشِ پنل نماینده")

# نماینده ربات خودش را دارد ولی هیچ عددی از فروشش نمی‌دید. دو
# قاعده‌ای که این‌جا هم باید اجرا شوند:
#
#   • تست رایگان خرید نیست — خودش یک سفارشِ approved با مبلغ صفر
#     می‌سازد و اگر کنار گذاشته نشود، «تعداد فروش» را باد می‌کند.
#   • «فروش» با «درآمد» یکی نیست — خرید از کیف پول فروش هست ولی پول
#     تازه‌ای نیامده؛ آن پول موقع شارژ رسیده.

botdb.init_db()
_sb = _sq3.connect(str(AP.BOT_DB))
_sb.executescript("""
INSERT OR REPLACE INTO tenants (id, name, parent_id) VALUES (7100, 'نماینده فروش', 1);
INSERT OR REPLACE INTO tenants (id, name, parent_id) VALUES (7101, 'نماینده دیگر', 1);

INSERT OR REPLACE INTO plans (id, tenant_id, name, price, gb, days, is_trial)
  VALUES (7110, 7100, 'پلن', 200000, 30, 30, 0);
INSERT OR REPLACE INTO plans (id, tenant_id, name, price, gb, days, is_trial)
  VALUES (7111, 7100, 'تست', 0, 1, 1, 1);

INSERT OR REPLACE INTO users (id, tenant_id, tg_id) VALUES (7120, 7100, 71);
INSERT OR REPLACE INTO users (id, tenant_id, tg_id) VALUES (7121, 7101, 72);
""")
# دو فروش کارتی، یک فروش کیف‌پولی، یک تست، یک ردشده، یک در انتظار
for _amt, _plan, _st, _pf in (
        (200000, 7110, 'approved', 'card'),
        (300000, 7110, 'approved', 'card'),
        (150000, 7110, 'approved', 'wallet'),
        (0,      7111, 'approved', 'card'),
        (500000, 7110, 'rejected', 'card'),
        (400000, 7110, 'awaiting', 'card')):
    _sb.execute("INSERT INTO orders (tenant_id,user_id,plan_id,amount,"
                "base_amount,status,paid_from,created_at) "
                "VALUES (7100,7120,?,?,?,?,?,datetime('now'))",
                (_plan, _amt, _amt, _st, _pf))
# و یک فروش برای نماینده‌ی دیگر که نباید قاطی شود
_sb.execute("INSERT INTO orders (tenant_id,user_id,plan_id,amount,base_amount,"
            "status,paid_from,created_at) "
            "VALUES (7101,7121,NULL,900000,900000,'approved','card',datetime('now'))")
_sb.commit()
_sb.close()

_first = _dt.now().replace(day=1).strftime("%Y-%m-%d")
_sales = AP._portal_sales(7100, _first)

check("ربات دارد", _sales["hasBot"] is True)
check("تعداد فروش، تست را نمی‌شمارد", _sales["orders"] == 3,
      f"{_sales['orders']} — دو کارتی و یک کیف‌پولی، نه تستِ رایگان")
check("مبلغ فروش هم همین‌طور", _sales["sold"] == 650000,
      f"{_sales['sold']} — ۲۰۰ + ۳۰۰ + ۱۵۰ هزار")
check("«دریافتی» فقط کارت را می‌شمارد", _sales["received"] == 500000,
      f"{_sales['received']} — خرید کیف‌پولی پول تازه نیست")
check("سفارشِ ردشده در فروش نیست", _sales["sold"] != 1150000)
check("در انتظار بررسی جدا شمرده می‌شود", _sales["pending"] == 1,
      str(_sales["pending"]))
check("فروش این ماه هم درست است", _sales["monthSold"] == 650000,
      str(_sales["monthSold"]))

_other = AP._portal_sales(7101, _first)
check("فروش نماینده‌ها با هم قاطی نمی‌شود", _other["sold"] == 900000,
      f"{_other['sold']} — فقط مالِ خودش")
check("و برعکسش هم", _sales["sold"] == 650000)

_none = AP._portal_sales(999999, _first)
check("نماینده‌ی بدون ربات صفر می‌گیرد، نه خطا",
      _none["hasBot"] is False and _none["orders"] == 0, str(_none)[:60])


# ═══════════════════════════════════════════════════════════
head("پنل نماینده و ربات باید یک اینباند را انتخاب کنند")

# انتخابِ اینباندِ هر نماینده اضافه شد و ربات آن را می‌خواند — ولی
# پنلِ خودِ نماینده نه. یعنی مالک می‌گفت «کانفیگ‌های این نماینده روی
# اینباند ۴۱ و ۴۵»، نماینده از پنل خودش کانفیگ می‌ساخت، و روی
# اینباند پیش‌فرض می‌نشست. بی‌صدا و بدون هیچ خطایی.
#
# دو پیاده‌سازی‌اند چون دو پردازه‌ی جدا هستند. این تست برابری‌شان را
# اجرا می‌کند.


def _bot_rule(t, inbound):
    """همان منطقِ bot/handlers.py، برای مقایسه."""
    import json as _j
    mode = t.get("inbound_mode") or "all"
    raw = None
    if mode == "custom":
        raw = t.get("inbound_ids")
    elif mode == "default":
        raw = _j.dumps([inbound]) if inbound else None
    if not raw:
        return None
    try:
        ids = _j.loads(raw) if isinstance(raw, str) else raw
    except Exception:      # noqa: BLE001
        ids = [x.strip() for x in str(raw).split(",") if x.strip()]
    out = []
    for x in (ids or []):
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    return out or None


_CASES = [
    ({"inbound_mode": "all", "inbound_ids": None}, 28),
    ({"inbound_mode": "all", "inbound_ids": "[41]"}, 28),
    ({"inbound_mode": "default", "inbound_ids": None}, 28),
    ({"inbound_mode": "default", "inbound_ids": "[41,45]"}, 28),
    ({"inbound_mode": "custom", "inbound_ids": "[41,45]"}, 28),
    ({"inbound_mode": "custom", "inbound_ids": "[]"}, 28),
    ({"inbound_mode": "custom", "inbound_ids": None}, 28),
    ({"inbound_mode": "custom", "inbound_ids": "چرند"}, 28),
    ({"inbound_mode": None, "inbound_ids": "[41]"}, 28),
    ({"inbound_mode": "default", "inbound_ids": None}, 0),
]

_diff = []
for _t, _inb in _CASES:
    _a = AP._portal_inbound_ids(_t, _inb)
    _b = _bot_rule(_t, _inb)
    if _a != _b:
        _diff.append(f"{_t['inbound_mode']}/{_t['inbound_ids']} → "
                     f"پنل {_a} در برابر ربات {_b}")

check("هر ده حالت در هر دو یکی جواب می‌دهد", not _diff,
      "، ".join(_diff) if _diff else f"{len(_CASES)} حالت سنجیده شد")

# و چند نتیجه‌ی مشخص، تا برابریِ «هر دو غلط» بی‌معنی سبز نشود
check("حالت all یعنی همه‌ی اینباندهای فعال",
      AP._portal_inbound_ids({"inbound_mode": "all"}, 28) is None,
      "None یعنی تصمیم با خود x-ui")
check("حالت custom همان‌هایی را می‌دهد که انتخاب شده",
      AP._portal_inbound_ids(
          {"inbound_mode": "custom", "inbound_ids": "[41,45]"}, 28) == [41, 45])
check("حالت default فقط اینباند پیش‌فرض",
      AP._portal_inbound_ids({"inbound_mode": "default"}, 28) == [28])
check("و custom با فهرست خالی به all برمی‌گردد، نه فهرست تهی",
      AP._portal_inbound_ids(
          {"inbound_mode": "custom", "inbound_ids": "[]"}, 28) is None,
      "فهرست تهی به x-ui یعنی هیچ اینباندی — کانفیگ به هیچ‌جا وصل نمی‌شود")

# و واقعا به x-ui پاس داده می‌شود
_apsrc2 = io.open(os.path.join(str(ROOT), "backend", "app.py"),
                  encoding="utf-8").read()
check("و موقع ساخت کانفیگ به پنل x-ui داده می‌شود",
      "inbound_ids=_portal_inbound_ids(t, inbound)" in _apsrc2,
      "حساب‌کردنش بدون پاس‌دادنش بی‌فایده است")


# ═══════════════════════════════════════════════════════════
head("اینباندِ نماینده · انتخابش باید دیده شود")

# مالک برای نماینده اینباند ۴۱ و ۴۵ را تعریف می‌کرد و پنلِ خودِ
# نماینده باز هم می‌گفت «اینباند پیش‌فرض تنظیم نشده» — چون
# _portal_inbound فقط ستون default_inbound را نگاه می‌کرد و
# inbound_mode/inbound_ids را اصلاً نمی‌دید.
#
# یعنی پیامِ خطا دقیقاً چیزی را انکار می‌کرد که تعریف شده بود، و
# نماینده هیچ راهی نداشت بفهمد چه کم است.


class _FakeXui:
    """x-ui با دو اینباند فعال — نصبِ معمولی."""

    def __init__(self, ids=(41, 45)):
        self._ids = ids

    def inbounds(self):
        return [{"id": i, "enable": True} for i in self._ids]


def _inb(t, xui=_FakeXui()):
    try:
        return AP._portal_inbound(t, xui)
    except Exception as e:
        return "خطا:" + str(getattr(e, "detail", e))[:20]


# x-ui عمداً اینباندِ دیگری می‌دهد (۷۷ و ۸۸)، وگرنه «از انتخابِ
# نماینده خواند» و «به x-ui افتاد» هر دو ۴۱ می‌دادند و تست نمی‌توانست
# فرقشان را بگذارد — شکستنِ عمدی همین را نشان داد.
check("نماینده‌ای که اینباند دارد ولی پیش‌فرض ندارد، کار می‌کند",
      _inb({"inbound_mode": "custom", "inbound_ids": "[41,45]",
            "default_inbound": None}, _FakeXui(ids=(77, 88))) == 41,
      "قبلاً همین حالت ۵۰۳ می‌گرفت — و ۴۱ فقط از انتخابِ خودش می‌آید")

check("پیش‌فرضِ خودِ نماینده بر انتخابِ نداشته مقدم است",
      _inb({"inbound_mode": "all", "inbound_ids": None,
            "default_inbound": 45}, _FakeXui(ids=(77, 88))) == 45,
      "۴۵ فقط می‌تواند از ستون خودش آمده باشد")

check("و وقتی هیچ‌کدام نیست، اولین اینباند فعال — مثل ربات",
      _inb({"inbound_mode": "all", "inbound_ids": None,
            "default_inbound": None}) == 41,
      "ربات از قبل همین کار را می‌کرد؛ پرتال خطا می‌داد")

check("اینباند غیرفعال انتخاب نمی‌شود",
      AP._portal_inbound(
          {"inbound_mode": "all", "default_inbound": None},
          type("X", (), {"inbounds": lambda s: [
              {"id": 7, "enable": False}, {"id": 9, "enable": True}]})()) == 9)

_no_xui = None
try:
    AP._portal_inbound({"inbound_mode": "all", "inbound_ids": None,
                        "default_inbound": None}, _FakeXui(ids=()))
    _no_xui = "بدون خطا رد شد"
except Exception as e:
    _no_xui = str(getattr(e, "detail", e))
check("وقتی واقعاً هیچ اینباندی نیست، خطا می‌دهد و می‌گوید چرا",
      "هیچ اینباند فعالی" in str(_no_xui),
      str(_no_xui)[:54])


# ═══════════════════════════════════════════════════════════
head("پول نباید پیش از چیزی که ممکن است شکست بخورد کم شود")

# _portal_charge اعتبار را واقعاً کم می‌کند. اگر بعد از آن چیزی
# خطا بدهد و آن مسیر برگشت نداشته باشد، نماینده پول داده و کانفیگ
# نگرفته.
#
# قبلاً ترتیب این بود:  charge → _portal_inbound → _portal_xui → add_client
# و فقط شکستِ add_client برگشت داشت. یعنی همان نماینده‌ای که
# اینباندش تنظیم نبود، اعتبارش هم می‌رفت.

_ordering = []
for _fn in ("portal_create", "portal_renew"):
    _i = _apsrc2.find("def %s(" % _fn)
    if _i < 0:
        _ordering.append("%s پیدا نشد" % _fn)
        continue
    _body = _apsrc2[_i:_i + 4000]
    _c = _body.find("_portal_charge(")
    _x = _body.find("_portal_xui(")
    if _c < 0:
        continue
    if 0 <= _c < _x:
        _ordering.append("%s: اتصال بعد از کسر اعتبار" % _fn)
    _ib = _body.find("_portal_inbound(")
    if _ib >= 0 and _c < _ib:
        _ordering.append("%s: اینباند بعد از کسر اعتبار" % _fn)

check("اتصال و اینباند پیش از کسر اعتبار حل می‌شوند", not _ordering,
      "، ".join(_ordering) if _ordering
      else "هر دو فقط می‌خوانند، پس جایشان پیش از پول است")


# ═══════════════════════════════════════════════════════════
head("تسویه · پول و بستنِ دوره باید یک کار باشند")

# مالک پرداخت را ثبت می‌کرد و `settled_until` دست‌نخورده می‌ماند، پس
# فاکتور ماه بعد همان کاربران و همان دوره را دوباره می‌آورد — و او
# بر اساس همان فاکتور دوباره پول گرفت.
#
# همان شکلِ آشنا: پول یک جا ثبت می‌شود، وضعیت جای دیگر.

_bc = AP._billing_conn()
_bc.execute("INSERT OR REPLACE INTO group_config (group_key,label,billable) "
            "VALUES ('tasvieh','tasvieh',1)")
_bc.execute("DELETE FROM payments WHERE group_key='tasvieh'")
_bc.commit()
_bc.close()

_st = AP.billing_settle({"group": "tasvieh", "amount": 750000,
                         "until": "2026-03-01"}, x_admin_password="testpw")
check("تسویه ثبت شد", _st.get("ok") and _st["settledUntil"] == "2026-03-01",
      str(_st.get("settledUntil")))

_bc = AP._billing_conn()
_row = _bc.execute("SELECT settled_until FROM group_config "
                   "WHERE group_key='tasvieh'").fetchone()
_pay = _bc.execute("SELECT amount, paid_at FROM payments "
                   "WHERE group_key='tasvieh'").fetchall()
_bc.close()

check("و دوره را هم بست", (_row["settled_until"] or "") == "2026-03-01",
      "ثبت پرداخت بدون این، فاکتور بعدی را دوباره پر می‌کند")
check("و پول هم ثبت شد", len(_pay) == 1 and _pay[0]["amount"] == 750000,
      f"{len(_pay)} ردیف")
check("تاریخ پرداخت همان تاریخ تسویه است",
      (_pay[0]["paid_at"] or "")[:10] == "2026-03-01",
      "وگرنه پرداخت بیرون از دوره‌ای می‌افتد که بسته شده")

_back = None
try:
    AP.billing_settle({"group": "tasvieh", "amount": 1,
                       "until": "2026-01-01"}, x_admin_password="testpw")
    _back = "بدون خطا پذیرفته شد"
except Exception as e:
    _back = str(getattr(e, "detail", e))
check("عقب‌بردن تاریخ تسویه رد می‌شود", "تسویه شده" in str(_back),
      str(_back)[:58])

_st2 = AP.billing_settle({"group": "tasvieh", "amount": 0,
                          "until": "2026-04-01"}, x_admin_password="testpw")
_bc = AP._billing_conn()
_n = _bc.execute("SELECT COUNT(*) c FROM payments "
                 "WHERE group_key='tasvieh'").fetchone()["c"]
_bc.close()
check("تسویه‌ی بدون مبلغ فقط دوره را می‌بندد",
      _st2["settledUntil"] == "2026-04-01" and _n == 1,
      f"{_n} پرداخت — صفر نباید ردیف بسازد")


# ═══════════════════════════════════════════════════════════
head("حذف کانفیگ · پولِ مشتریِ پشیمان باید برگردد")

# موردی که مالک گفت: نماینده کانفیگ را می‌سازد، مشتری همان لحظه
# پشیمان می‌شود. اگر اعتبار برنگردد، نماینده بابت چیزی پول داده که
# هیچ‌کس استفاده‌اش نکرد.
#
# ولی کانفیگی که مصرف داشته دوره‌اش را کار کرده — همان قاعده‌ای که
# مالک برای انقضا گذاشت: راه فرار از پرداخت نیست.


class _DelXUI:
    deleted = []

    def find_client(self, _ib, email=None):
        return {"id": "uuid-" + str(email), "inboundId": 7}

    def delete_client(self, ib, uuid, email=None):
        _DelXUI.deleted.append(email)


_T3 = AP._tenant_by_slug("hossein")
_before_credit = int(_T3.get("credit") or 0)

# کانفیگی که ساخته و پولش کم شده، ولی یک بایت هم مصرف نکرده
AP._portal_charge(_T3, 30000, "ساخت hossein_fresh")
_T3 = AP._tenant_by_slug("hossein")
_after_charge = int(_T3.get("credit") or 0)
check("اعتبار موقع ساخت کم شد", _after_charge == _before_credit - 30000,
      f"{_before_credit} → {_after_charge}")

_FRESH = {"email": "hossein_fresh", "group": "goroh-a", "used": 0,
          "enable": True, "totalGB": 50 * 1024 ** 3, "expiry": 0, "limitIp": 1}
_USEDC = {"email": "hossein_used", "group": "goroh-a", "used": 9 * 1024 ** 3,
          "enable": True, "totalGB": 50 * 1024 ** 3, "expiry": 0, "limitIp": 1}
AP._read_xui_clients = lambda *a, **k: ([_FRESH, _USEDC], [], None)
AP._portal_xui = lambda t: (_DelXUI(), Exception)

_d1 = AP.portal_config_delete("hossein_fresh", _T3)
_T3 = AP._tenant_by_slug("hossein")
check("کانفیگ بی‌مصرف حذف شد", _d1["ok"] and "hossein_fresh" in _DelXUI.deleted)
check("و اعتبارش برگشت", _d1["refunded"] == 30000,
      f"برگشت {_d1['refunded']} — از دفتر اعتبار، نه از نرخ امروز")
check("اعتبار مستاجر هم واقعاً برگشت",
      int(_T3.get("credit") or 0) == _before_credit,
      f"{_T3.get('credit')} در برابر {_before_credit}")

_d2 = AP.portal_config_delete("hossein_used", _T3)
check("کانفیگ با مصرف هم حذف می‌شود", _d2["ok"])
check("ولی اعتباری برنمی‌گردد", _d2["refunded"] == 0,
      "دوره‌اش را کار کرده — حذف راه فرار از پرداخت نیست")

_bc = AP._billing_conn()
_delrow = _bc.execute(
    "SELECT email, amount FROM deleted_clients "
    "WHERE email='hossein_used'").fetchone()
_bc.close()
check("و بیرون‌رفتنش از فاکتور بی‌صدا نمی‌ماند", _delrow is not None,
      "ردیفی در deleted_clients، تا مالک ببیند چه چیزی از فاکتور رفت")


# ═══════════════════════════════════════════════════════════
head("فهرست کانفیگ‌ها · مصرف باید خام هم برود")

# تصمیمِ «برگشت اعتبار» با used <= 0 گرفته می‌شود. اگر رابط با
# usedGB قضاوت کند، مصرفِ چند مگابایتی به ۰٫۰ گرد می‌شود و دیالوگ
# وعده‌ی برگشتی می‌دهد که بک‌اند انجامش نمی‌دهد.
_TINY = {"email": "hossein_tiny", "group": "goroh-a", "used": 40 * 1024 ** 2,
         "enable": True, "totalGB": 50 * 1024 ** 3, "expiry": 0, "limitIp": 1}
AP._read_xui_clients = lambda *a, **k: ([_TINY], [], None)
_lst = AP.portal_configs(_T3)
_one = (_lst.get("configs") or [_lst])[0] if _lst.get("configs") else None
check("مصرف خام در پاسخ هست", _one is not None and "used" in _one,
      "کلیدهای موجود: " + "، ".join(sorted((_one or {}).keys()))[:60])
check("و مصرفِ کوچک به صفر گرد نمی‌شود",
      _one and _one["used"] > 0 and _one["usedGB"] == 0.0,
      f"used={(_one or {}).get('used')} · usedGB={(_one or {}).get('usedGB')}")


# ═══════════════════════════════════════════════════════════
head("مینی‌اپ · امضا تنها دیواری است که بین مشتری‌هاست")

# initData رشته‌ای است که تلگرام امضا کرده. اگر امضا سنجیده نشود، هر
# کسی می‌تواند user={"id":...} بفرستد و اشتراک‌های هر مشتری‌ای را
# ببیند. این تنها چیزی است که جلویش را می‌گیرد.

import hashlib as _hl
import hmac as _hm
import re as _re
import time as _tm
import json as _json
from urllib.parse import urlencode as _ue

_APSRC = io.open(os.path.join(str(ROOT), "backend", "app.py"),
                 encoding="utf-8").read()

_BOT = "8100001:AA-token-for-the-signature-test"


def _sign(token, user_id=555, age=0, extra=None):
    """یک initData معتبر می‌سازد — همان‌طور که تلگرام می‌سازد."""
    pairs = {
        "auth_date": str(int(_tm.time()) - age),
        "query_id": "AAH",
        "user": _json.dumps({"id": user_id, "first_name": "آزمون"},
                            ensure_ascii=False),
    }
    pairs.update(extra or {})
    check = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret = _hm.new(b"WebAppData", token.encode(), _hl.sha256).digest()
    pairs["hash"] = _hm.new(secret, check.encode(), _hl.sha256).hexdigest()
    return _ue(pairs)


_sok, _d = AP._mini_check(_sign(_BOT), _BOT)
check("امضای درست پذیرفته می‌شود", _sok and _d["user"]["id"] == 555, str(_d)[:60])

_sok2, _w2 = AP._mini_check(_sign(_BOT), "8100002:AA-a-different-bots-token")
check("امضای یک ربات با توکن ربات دیگر رد می‌شود", not _sok2, str(_w2)[:52])

_forged = _sign(_BOT).replace("hash=", "hash=0")
check("امضای دستکاری‌شده رد می‌شود",
      not AP._mini_check(_forged, _BOT)[0])

_noHash = _ue({"auth_date": str(int(_tm.time())),
               "user": _json.dumps({"id": 555})})
check("بدون امضا اصلاً رد می‌شود", not AP._mini_check(_noHash, _BOT)[0],
      "وگرنه فرستادن شناسه کافی بود تا حساب دیگری دیده شود")

_old = _sign(_BOT, age=25 * 3600)
_sok3, _w3 = AP._mini_check(_old, _BOT)
check("امضای کهنه‌تر از ۲۴ ساعت رد می‌شود", not _sok3, str(_w3)[:46])

_fresh = _sign(_BOT, age=23 * 3600)
check("ولی امضای ۲۳ ساعته هنوز قبول است",
      AP._mini_check(_fresh, _BOT)[0],
      "سقف نباید آن‌قدر تنگ باشد که نشست وسط کار بیفتد")

_future = _sign(_BOT, age=-3600)
check("امضای با تاریخِ آینده رد می‌شود",
      not AP._mini_check(_future, _BOT)[0])

_noUser = _sign(_BOT, extra={"user": "{}"})
check("امضای بدون شناسه‌ی کاربر رد می‌شود",
      not AP._mini_check(_noUser, _BOT)[0])

# داخل خودِ تابع، نه هرجای فایل: compare_digest شش جای دیگر app.py
# هم هست و شکستنِ عمدی نشان داد جایگزینی‌اش با == گرفته نمی‌شود
_chk_fn = _APSRC[_APSRC.find("def _mini_check("):]
_chk_fn = _chk_fn[:_chk_fn.find(chr(10) + "def ", 10)]
check("مقایسه‌ی امضا با compare_digest است",
      "compare_digest" in _chk_fn and "want != got" not in _chk_fn,
      "مقایسه‌ی معمولی از روی زمانش لو می‌دهد")


# ═══════════════════════════════════════════════════════════
head("مینی‌اپ · مرزها")

_mini_routes = _re.findall(r'@app\.(?:get|post|put|delete)\("(/api/mini/[^"]*)"\)',
                           _APSRC)
check("مسیرهای مینی‌اپ پیدا شدند", len(_mini_routes) >= 3,
      "، ".join(_mini_routes))

# هر مسیر باید از mini_user رد شود — مثل همان قاعده‌ای که برای
# /api/portal/* هست
_unguarded = []
for _r in _mini_routes:
    _i = _APSRC.find('"%s"' % _r)
    _seg = _APSRC[_i:_i + 400]
    if "Depends(mini_user)" not in _seg:
        _unguarded.append(_r)
check("هر مسیر مینی‌اپ از احراز هویت رد می‌شود", not _unguarded,
      "، ".join(_unguarded) if _unguarded else "%d مسیر" % len(_mini_routes))

# و هیچ‌کدام نباید به حسابداری دست بزنند — مالک گفت جداست
_MONEY = ("_billing_conn", "_line_amount", "_period_share", "_portal_charge",
          "_bill_since", "billing.db", "group_config")
_i0 = _APSRC.find("#  مینی‌اپ تلگرام")
_i1 = _APSRC.find('@app.post("/api/admin/tenant/{tid}/credit")', _i0)
_block = _APSRC[_i0:_i1] if _i0 >= 0 and _i1 > _i0 else ""
_touched = [w for w in _MONEY if w in _block]
check("مینی‌اپ به حسابداری دست نمی‌زند", _block and not _touched,
      "، ".join(_touched) if _touched
      else "نه نرخ حساب می‌کند، نه اعتبار کم می‌کند")

check("و هیچ سفارشی را approved نمی‌کند",
      "approved" not in _block,
      "خرید در خودِ ربات می‌ماند")


# ═══════════════════════════════════════════════════════════
head("مینی‌اپ · ربات باید مسیر مستقل بماند")

# مشتری‌های ما همان کسانی‌اند که اینترنتشان محدود است. اگر دامنه بالا
# نیاید، مینی‌اپ صفحه‌ی سفید می‌شود و تلگرام چیزی نمی‌گوید. پس هر
# کاری که از مینی‌اپ می‌شود کرد باید از منوی ربات هم بشود.
_H = io.open(os.path.join(str(ROOT), "bot", "handlers.py"),
             encoding="utf-8").read()

# داخل خودِ main_menu، نه هرجای فایل: همین متن‌ها در حالت‌های خالی
# هم به کار رفته‌اند و شکستنِ عمدی نشان داد حذفشان از منو گرفته
# نمی‌شود
_menu = _H[_H.find("def main_menu("):]
_menu = _menu[:_menu.find(chr(10) + "def ", 10)]
for _must in ("🛒 خرید اشتراک", "📊 اشتراک‌های من", "👛 کیف پول"):
    check("دکمه‌ی «%s» هنوز در منوی ربات هست" % _must.split(" ", 1)[-1],
          _must in _menu, "مینی‌اپ اضافه است، نه جایگزین")

# آدرس مینی‌اپ باید خودش پیدا شود، نه اینکه منتظر بماند کسی پرش کند.
#
# تنظیمی که باید آدم انجامش بدهد، انجام نمی‌شود — و آن‌وقت قابلیتی
# داریم که ساخته شده و هیچ‌کس نمی‌بیندش. همان چیزی که سر پنل
# نمایندگی افتاد و سر اینباند پیش‌فرض.
#
# راهش این است: اولین باری که مدیر پنل را روی https باز می‌کند،
# بک‌اند دامنه‌ی خودش را از هدر Host می‌بیند و آدرس را ثبت می‌کند.


class _Req:
    def __init__(self, **h):
        self.headers = h


def _stored_mini():
    _c = _sq3.connect(str(AP.BOT_DB))
    _c.row_factory = _sq3.Row
    _r = _c.execute("SELECT settings FROM tenants WHERE parent_id IS NULL "
                    "ORDER BY id LIMIT 1").fetchone()
    _c.close()
    try:
        return json.loads(_r["settings"] or "{}").get("miniapp_url") or ""
    except Exception:
        return ""


def _clear_mini():
    _c = _sq3.connect(str(AP.BOT_DB))
    _c.row_factory = _sq3.Row
    _r = _c.execute("SELECT id, settings FROM tenants WHERE parent_id IS NULL "
                    "ORDER BY id LIMIT 1").fetchone()
    _st = json.loads(_r["settings"] or "{}")
    _st.pop("miniapp_url", None)
    _c.execute("UPDATE tenants SET settings=? WHERE id=?",
               (json.dumps(_st, ensure_ascii=False), _r["id"]))
    _c.commit()
    _c.close()


_clear_mini()
AP._learn_panel_origin(_Req(host="panel.example.com",
                            **{"x-forwarded-proto": "https"}))
check("بازکردن پنل، آدرس مینی‌اپ را خودش ثبت می‌کند",
      _stored_mini() == "https://panel.example.com/app",
      _stored_mini() or "(هیچ) — قابلیتی که کسی نمی‌بیندش")

_clear_mini()
AP._learn_panel_origin(_Req(host="panel.example.com:8443",
                            **{"x-forwarded-proto": "https"}))
check("پورت هم نگه داشته می‌شود",
      _stored_mini() == "https://panel.example.com:8443/app", _stored_mini())

# هدر Host را فرستنده تعیین می‌کند. اگر بی‌شرط ثبتش کنیم، کسی
# می‌تواند مینی‌اپِ مشتری‌ها را به صفحه‌ی خودش ببرد.
for _h, _why in ((("http"), "بدون https"), ((""), "بدون هدر proto")):
    _clear_mini()
    AP._learn_panel_origin(_Req(host="panel.example.com",
                                **({"x-forwarded-proto": _h} if _h else {})))
    check("%s چیزی ثبت نمی‌کند" % _why, _stored_mini() == "",
          "تلگرام هم http را رد می‌کند؛ ثبتش فقط مقدار مرده می‌سازد")

# و بدون آن هدر هم باید کار کند.
#
# نسخه‌ی اول فقط x-forwarded-proto را می‌خواند و روی نصب‌های واقعی
# هیچ‌وقت ثبت نشد: بلوک nginx خودمان آن هدر را جلو نمی‌فرستاد، پس
# درخواست به شکل http می‌رسید و شرط همیشه رد می‌شد. مالک آخرین نسخه
# را نصب کرد و هیچ دکمه‌ای ندید.
_clear_mini()
AP._learn_panel_origin(_Req(host="panel.example.com",
                            referer="https://panel.example.com/"))
check("بدون هدر پروکسی هم، از نوار آدرسِ مرورگر یاد می‌گیرد",
      _stored_mini() == "https://panel.example.com/app",
      _stored_mini() or "(هیچ) — همان چیزی که روی سرور واقعی افتاد")

_clear_mini()
AP._learn_panel_origin(_Req(host="10.0.0.5:8100",
                            referer="https://panel.example.com:8443/#/x"))
check("و دامنه را از خودِ Referer می‌گیرد، نه از Host",
      _stored_mini() == "https://panel.example.com:8443/app", _stored_mini())

_clear_mini()
AP._learn_panel_origin(_Req(host="panel.example.com",
                            origin="https://panel.example.com"))
check("هدر Origin هم پذیرفته است",
      _stored_mini() == "https://panel.example.com/app", _stored_mini())

# ولی http در هیچ شکلی قبول نیست — تلگرام خودِ پیام را رد می‌کند
_clear_mini()
AP._learn_panel_origin(_Req(host="panel.example.com",
                            referer="http://panel.example.com/"))
check("Refererِ http چیزی ثبت نمی‌کند", _stored_mini() == "",
      "وگرنه دکمه‌ای می‌ساخت که کل منوی ربات را از کار می‌اندازد")

_clear_mini()
AP._learn_panel_origin(_Req(host="panel.example.com",
                            referer="https://good.ir@evil.com/x"))
check("Refererِ آلوده هم رد می‌شود", _stored_mini() == "",
      "@ در آدرس یعنی هاستِ واقعی چیز دیگری است")

# و همان قاعده در nginx هم باید نوشته باشد، وگرنه نصب تازه دوباره
# همان‌جا می‌ماند
_INST = io.open(os.path.join(str(ROOT), "install.sh"), encoding="utf-8").read()
check("nginx هم هدر پروتکل را جلو می‌فرستد",
      _INST.count("X-Forwarded-Proto") >= 3,
      "%d بلوک — ریشه‌ی خودِ باگ" % _INST.count("X-Forwarded-Proto"))

_clear_mini()
AP._learn_panel_origin(_Req(host="evil.com/x?a=b",
                            **{"x-forwarded-proto": "https"}))
check("هاستِ آلوده ثبت نمی‌شود", _stored_mini() == "",
      "وگرنه مینی‌اپِ مشتری به صفحه‌ی دیگری می‌رفت")

_clear_mini()
_c9 = _sq3.connect(str(AP.BOT_DB))
_c9.row_factory = _sq3.Row
_r9 = _c9.execute("SELECT id, settings FROM tenants WHERE parent_id IS NULL "
                  "ORDER BY id LIMIT 1").fetchone()
_s9 = json.loads(_r9["settings"] or "{}")
_s9["miniapp_url"] = "https://my.own.example.com/app"
_c9.execute("UPDATE tenants SET settings=? WHERE id=?",
            (json.dumps(_s9, ensure_ascii=False), _r9["id"]))
_c9.commit()
_c9.close()
AP._learn_panel_origin(_Req(host="panel.example.com",
                            **{"x-forwarded-proto": "https"}))
check("و انتخابِ خودِ مالک را بازنویسی نمی‌کند",
      _stored_mini() == "https://my.own.example.com/app", _stored_mini())

# و واقعاً از مسیر API صدا زده می‌شود.
#
# تست‌های بالا تابع را مستقیم صدا می‌زنند، پس اگر فراخوانی از خودِ
# نقطه‌ی API برداشته شود همه‌شان سبز می‌مانند — شکستنِ عمدی همین را
# نشان داد.
_cfg_fn = _APSRC[_APSRC.find("def get_admin_config("):]
_cfg_fn = _cfg_fn[:_cfg_fn.find(chr(10) + "@app", 10)]
check("و بازکردن پنل واقعاً صدایش می‌زند",
      "_learn_panel_origin(request)" in _cfg_fn,
      "وگرنه آدرس هیچ‌وقت ثبت نمی‌شود و دکمه ظاهر نمی‌شود")

import bot.handlers as _BH                               # noqa: E402
check("ربات همان تنظیم را می‌خواند",
      _BH.miniapp_url(type("C", (), {"s": {"miniapp_url": "https://a.ir/app"}})())
      == "https://a.ir/app")
check("و آدرس http را رد می‌کند",
      _BH.miniapp_url(type("C", (), {"s": {"miniapp_url": "http://a.ir"}})()) == "",
      "تلگرام با http خودِ پیام را رد می‌کند، نه فقط دکمه را")

_RUN = io.open(os.path.join(str(ROOT), "bot", "run.py"), encoding="utf-8").read()
check("ربات خودش دکمه‌ی کنار کادر تایپ را تنظیم می‌کند",
      _re.search(r'setChatMenuButton"[^)]*"type":\s*"web_app"', _RUN, _re.S)
      is not None and "_sync_menu_button" in _RUN,
      "وگرنه مالک باید دستی به BotFather برود")
check("و وقتی آدرسی نیست، دکمه‌ی قبلی را برمی‌دارد",
      '"type": "commands"' in _RUN,
      "وگرنه به صفحه‌ای اشاره می‌کند که دیگر بالا نمی‌آید")

_TG = io.open(os.path.join(str(ROOT), "bot", "tg.py"), encoding="utf-8").read()
check("و کیبورد هم آدرس نامعتبر را حذف می‌کند نه می‌فرستد",
      'kind == "web_app"' in _TG and "startswith(\"https://\")" in _TG,
      "یک آدرس غلط کل منو را از کار می‌اندازد")


# ═══════════════════════════════════════════════════════════
head("گزارش فروش و قیف باید یک نرخ تبدیل بدهند")

# قیف در ۱.۳۷.۰ درست شد، ولی گزارش فروش تعریفِ خودش را داشت. روی
# همان داده، یکی می‌گفت ۸۰٪ و دیگری ۲۰٪.
#
# و «میانگین سفارش» هم با سفارش‌های صفرتومانیِ تست پایین کشیده
# می‌شد: ۶۲٬۵۰۰ به‌جای ۲۵۰٬۰۰۰.
#
# روی دیتابیس تازه سنجیده می‌شود تا عددها دقیق باشند.

_rdb = _tf.mktemp(suffix=".db")
_old_bp, _old_ap = botdb.DB_PATH, app.BOT_DB
botdb.DB_PATH = Path(_rdb)
try:
    botdb.init_db()
    _rtid = botdb.create_tenant("گزارش", bot_token="1:R", owner_tg_id=1)
    _rc = _sq3.connect(_rdb)
    _rc.executescript(f"""
    INSERT INTO plans (id, tenant_id, name, price, gb, days, is_trial)
      VALUES (6001, {_rtid}, 'تست', 0, 1, 1, 1);
    INSERT INTO plans (id, tenant_id, name, price, gb, days, is_trial)
      VALUES (6002, {_rtid}, '۳۰ گیگ', 200000, 30, 30, 0);
    """)
    # ده نفر آمدند؛ شش نفر فقط تست گرفتند، دو نفر واقعا خریدند
    for _u in range(1, 11):
        _rc.execute("INSERT INTO users (id,tenant_id,tg_id,created_at) "
                    "VALUES (?,?,?,datetime('now'))",
                    (_u, _rtid, 600 + _u))
    for _u in range(1, 7):
        _rc.execute("INSERT INTO orders (tenant_id,user_id,plan_id,amount,"
                    "base_amount,status,created_at) "
                    "VALUES (?,?,6001,0,0,'approved',datetime('now'))",
                    (_rtid, _u))
    for _u, _amt in ((7, 200000), (8, 300000)):
        _rc.execute("INSERT INTO orders (tenant_id,user_id,plan_id,amount,"
                    "base_amount,status,created_at) "
                    "VALUES (?,?,6002,?,?,'approved',datetime('now'))",
                    (_rtid, _u, _amt, _amt))
    _rc.commit()
    _rc.close()

    app.BOT_DB = Path(_rdb)
    _rep = app.bot_users_report(days=30, x_admin_password=PW)
    _fun2 = app.bot_funnel(x_admin_password=PW)
finally:
    app.BOT_DB = _old_ap
    botdb.DB_PATH = _old_bp

check("گزارش خوانده شد", _rep.get("ready") is True)

_o = _rep.get("orders") or {}
check("تعداد سفارش، تست رایگان را نمی‌شمارد", _o.get("approved") == 2,
      f"{_o.get('approved')} — شش تستِ رایگان نباید سفارش باشند")
check("درآمد درست است", _o.get("revenue") == 500000, str(_o.get("revenue")))
check("میانگین سفارش با سفارش‌های صفرتومانی پایین کشیده نمی‌شود",
      _o.get("avg") == 250000,
      f"{_o.get('avg')} — قبلا ۶۲٬۵۰۰ می‌شد")

check("شمارش خریدارها هم", _rep.get("buyerCount") == 2,
      f"{_rep.get('buyerCount')} — قبلا هشت نفر")
check("نرخ تبدیل درست است", _rep.get("conversion") == 20.0,
      f"{_rep.get('conversion')} — قبلا ۸۰٪")

_seg2 = _fun2.get("segments") or {}
check("و با قیف یکی است", _rep.get("buyerCount") == _seg2.get("paid"),
      f"گزارش {_rep.get('buyerCount')} · قیف {_seg2.get('paid')}")
check("و این برابری با «هر دو صفر» بی‌معنی نشده",
      _seg2.get("paid") == 2, str(_seg2.get("paid")))

_bl = _rep.get("buyers") or []
check("فهرست خریدارها فقط خریدارهای واقعی است", len(_bl) == 2,
      f"{len(_bl)} — کسی که فقط تست گرفته خریدار نیست")
check("و هیچ‌کدام صفرتومانی نیستند",
      all((b.get("spent") or 0) > 0 for b in _bl),
      str([b.get("spent") for b in _bl]))

_dl = _rep.get("daily") or []
check("نمودار روزانه هم تست را نمی‌شمارد",
      sum(int(d.get("n") or 0) for d in _dl) == 2,
      str([(d.get("day"), d.get("n")) for d in _dl]))

# و قاعده یک بار نوشته شده، نه سه بار
_rsrc = io.open(os.path.join(str(ROOT), "backend", "app.py"),
                encoding="utf-8").read()
check("قاعده‌ی «خرید واقعی» یک تعریف دارد",
      _rsrc.count("SQL_REAL_BUY = ") == 1, "یک تعریف")
check("و هر سه جا از همان می‌خوانند",
      _rsrc.count("SQL_REAL_BUY") >= 6,
      f"{_rsrc.count('SQL_REAL_BUY')} اشاره — قیف، گزارش، پنل نماینده")
check("و کپیِ دستیِ شرط نمانده",
      _rsrc.count("COALESCE(p.is_trial,0)=0") == 1,
      "هر کپی یک جای تازه برای جدا افتادن است")


# ═══════════════════════════════════════════════════════════
head("فهرست نماینده‌ها نباید خودِ مالک را نشان بدهد")

# مستاجرِ ریشه هم در فهرست می‌آمد: با فرم «نشانی لینک»، «گروه
# x-ui»، دکمه‌ی «بازکردن پنل» و حتی هشدارِ «برای اینکه بتواند وارد
# شود…» — برای خودِ صاحب پنل. و می‌شد ناخواسته برایش پنل نمایندگی
# باز کرد.

_pl = app.tenant_portal_list(x_admin_password=PW)
_ids = {t["id"] for t in _pl.get("tenants", [])}

_pc = _sq3.connect(str(AP.BOT_DB))
_roots = {r[0] for r in _pc.execute(
    "SELECT id FROM tenants WHERE parent_id IS NULL")}
_kids = {r[0] for r in _pc.execute(
    "SELECT id FROM tenants WHERE parent_id IS NOT NULL")}
_pc.close()

check("مستاجر ریشه پیدا شد", bool(_roots), str(sorted(_roots)))
check("هیچ مستاجرِ ریشه‌ای در فهرست نیست", not (_ids & _roots),
      f"در فهرست: {sorted(_ids & _roots)}")
check("ولی نماینده‌ها همه هستند", _kids <= _ids,
      f"جاافتاده: {sorted(_kids - _ids)}")
check("و این خالی‌بودنِ فهرست نیست", len(_ids) >= 1, f"{len(_ids)} نماینده")

# ─── نخواندنِ گروه‌ها باید گفته شود ───
#
# خطای _read_xui_clients دور ریخته می‌شد و فهرست بی‌صدا خالی می‌ماند.
# نتیجه: وقتی x-ui در دسترس نبود، *همه‌ی* نماینده‌ها بدون گروه به
# نظر می‌رسیدند، بدون هیچ توضیحی.
check("کلید groupsError در پاسخ هست", "groupsError" in _pl,
      "بدون آن، رابط نمی‌تواند بگوید چرا فهرست خالی است")

# روی همان ماژولی وصله می‌زنیم که صدایش می‌زنیم: AP و app دو شیء
# جدا هستند و وصله‌ی یکی روی دیگری اثر ندارد.
_orig_read = app._read_xui_clients
app._read_xui_clients = lambda *a, **k: (None, [], "پنل در دسترس نیست")
try:
    _pl2 = app.tenant_portal_list(x_admin_password=PW)
finally:
    app._read_xui_clients = _orig_read

check("وقتی x-ui جواب نمی‌دهد، دلیلش گزارش می‌شود",
      bool(_pl2.get("groupsError")), repr(_pl2.get("groupsError")))
check("و فهرست نماینده‌ها همچنان می‌آید",
      _pl2.get("ready") is True and isinstance(_pl2.get("tenants"), list),
      "نخواندنِ گروه‌ها نباید کلِ صفحه را از کار بیندازد")


# شمارنده نباید جای دیگری بازنویسی شده باشد.
#
# `_ok` دو جا به‌عنوان متغیر معمولی به کار رفته بود و هر بار شمارش را
# از صفر شروع می‌کرد — سوییت ۳۱۳ بررسی را اجرا می‌کرد و ۱۸۲ گزارش
# می‌داد. خود تست‌ها درست کار می‌کردند و شکست‌ها هم شمرده می‌شدند، ولی
# عددِ پایانی دروغ می‌گفت و هیچ راهی نبود بفهمی بخشی از سوییت اصلاً
# اجرا نشده.
# آستانه: هر فراخوانیِ ایستا دست‌کم یک‌بار اجرا می‌شود و بعضی‌ها داخل
# حلقه‌اند، پس شمرده‌شده باید **بیشتر** از تعداد ایستا باشد. کمتر بودن
# یعنی یا شمارنده بازنویسی شده یا بخشی از سوییت اصلاً نرسیده.
#
# چند بررسی داخل شرط‌اند و ممکن است اجرا نشوند، پس کمی ارفاق —
# ولی نه آن‌قدر که بازنویسی از زیرش در برود: با آستانه‌ی ۰٫۶ یک
# بازنویسی که ۲۰۶ از ۲۷۹ را شمرد، بی‌صدا رد شد.
_calls = io.open(__file__, encoding="utf-8").read().count("\ncheck(")
_counted = _ok + _fail
if _counted < _calls * 0.95:
    print(f"  {R}✗ شمارنده بازنویسی شده — {_counted} شمرده شد، "
          f"ولی {_calls} فراخوانی در فایل هست{X}")
    _fail += 1

print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
