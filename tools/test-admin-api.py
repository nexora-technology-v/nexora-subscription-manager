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


class _MakeXUI(_FakeXUI):
    made = []

    def add_client(self, inbound_id, email, gb=0, days=0, ip_limit=0,
                   client_uuid=None, tg_id=None, sub_id=None, flow=None,
                   group=None, inbound_ids=None):
        _MakeXUI.made.append({"inbound": inbound_id, "email": email, "gb": gb,
                              "days": days, "ip": ip_limit, "group": group})
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
    try:
        AP.portal_create(_bad_in, _T2)
        _ok = False
    except Exception as e:
        _ok = getattr(e, "status_code", 0) == 400
    check(f"{_why} رد می‌شود", _ok)

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
check("گروه در ساخت از _portal_group می‌آید",
      "group=group)" in APP_SRC2 and "group = _portal_group(t)" in APP_SRC2)


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
        _ok = False
    except Exception as e:
        _ok = getattr(e, "status_code", 0) == 400
    check(f"{_why} رد می‌شود", _ok)
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
    _bd.execute("INSERT INTO tenants (name, is_active, credit) VALUES (?,1,?)",
                ("تازه‌وارد", 0))
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


print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
