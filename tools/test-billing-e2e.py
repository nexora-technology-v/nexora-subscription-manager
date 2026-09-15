#!/usr/bin/env python3
"""
حسابداری سرتاسر — با یک دیتابیس x-ui واقعی که همین‌جا ساخته می‌شود.

چرا وجود دارد:
    test-billing.py فقط محاسبه‌ی نرخ را می‌آزماید. نمای کلی — جایی که
    x-ui خوانده می‌شود، گروه‌ها ساخته می‌شوند، ماه‌ها شمرده می‌شوند و
    در client_seen نوشته می‌شود — هیچ تستی نداشت.

    و همان‌جا بود که شکست: تنظیم دسته‌ای تاریخ شروع، وسط یک اتصال
    باز، دوباره نمای کلی را صدا می‌زد. نمای کلی خودش اتصال دومی باز
    می‌کند و می‌نویسد، و SQLite قفل می‌کرد — کل صفحه‌ی حسابداری با
    «database is locked» می‌ایستاد.

اجرا:  python3 tools/test-billing-e2e.py
"""
import importlib.util
import io
import os
import sqlite3
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


# ═══════════ یک x-ui ساختگی، با همان اسکیمای نسخه‌ی ۳ ═══════════
TMP = tempfile.mkdtemp()
XUI = os.path.join(TMP, "x-ui.db")
NOW_MS = int(time.time() * 1000)
YEAR = 365 * 86400000

con = sqlite3.connect(XUI)
con.executescript("""
CREATE TABLE clients (
    id INTEGER PRIMARY KEY, email TEXT, group_name TEXT,
    total_gb INTEGER, expiry_time INTEGER, enable INTEGER,
    created_at TEXT, limit_ip INTEGER DEFAULT 0
);
CREATE TABLE client_traffics (
    id INTEGER PRIMARY KEY, email TEXT, up INTEGER, down INTEGER,
    expiry_time INTEGER, enable INTEGER
);
""")

GB = 1024 ** 3
ROWS = [
    # (ایمیل, گروه, حجم, انقضا, فعال, ساخت)
    ("ali_1", "ali", 50, NOW_MS + 30 * 86400000, 1, None),
    ("ali_2", "ali", 50, NOW_MS + 30 * 86400000, 1, None),
    # این یکی دو سال کار کرده و دیروز منقضی شده
    ("old_1", "unlimited", 0, NOW_MS - 86400000, 1, None),
    ("unl_1", "unlimited", 0, NOW_MS + 60 * 86400000, 1, None),
    ("naji_1", "Hossein naji", 100, NOW_MS + 30 * 86400000, 0, None),
    ("solo_1", "", 30, NOW_MS + 30 * 86400000, 1, None),
]
for i, (em, grp, gb, exp, en, created) in enumerate(ROWS, 1):
    con.execute("INSERT INTO clients (id,email,group_name,total_gb,expiry_time,"
                "enable,created_at) VALUES (?,?,?,?,?,?,?)",
                (i, em, grp, gb, exp, en, created))
    con.execute("INSERT INTO client_traffics (id,email,up,down,expiry_time,enable)"
                " VALUES (?,?,?,?,?,?)",
                (i, em, 3 * GB, 7 * GB, exp, en))
con.commit()
con.close()

os.environ["XUI_DB_PATH"] = XUI
os.environ["NEXORA_DATA_DIR"] = TMP

spec = importlib.util.spec_from_file_location(
    "nxapp", os.path.join(ROOT, "backend", "app.py"))
APP = importlib.util.module_from_spec(spec)
sys.modules["nxapp"] = APP
spec.loader.exec_module(APP)

from pathlib import Path  # noqa: E402
APP.BILLING_DB = Path(TMP) / "billing.db"
APP.check_auth = lambda pw: True
try:
    APP._xui_db_path = lambda: Path(XUI)
except Exception:
    pass


# ═══════════════════════════════════════════════════════════
head("نمای کلی خوانده می‌شود")

ov = APP._billing_overview_impl()
check("نمای کلی آماده است", ov.get("ready") is True,
      ov.get("error", "")[:70])
check("همه‌ی کلاینت‌ها شمرده شدند", ov.get("totalClients") == len(ROWS),
      f"{ov.get('totalClients')} از {len(ROWS)}")

groups = {g["key"]: g for g in ov.get("groups") or []}
check("گروه‌ها از group_name ساخته می‌شوند", "ali" in groups,
      ", ".join(sorted(groups)[:5]))
check("کلاینت بدون گروه هم جایی دارد",
      any(k in groups for k in ("بدون گروه", "")),
      ", ".join(sorted(groups)))
check("تعداد کانفیگ هر گروه درست است",
      groups.get("ali", {}).get("configs") == 2,
      str(groups.get("ali", {}).get("configs")))
check("کلاینت غیرفعال در active شمرده نمی‌شود",
      groups.get("Hossein naji", {}).get("active") == 0)


head("منبع شمارش ماه گزارش می‌شود")

check("هر گروه sources دارد", all("sources" in g for g in groups.values()))
srcs = set()
for g in groups.values():
    srcs |= set(g["sources"])
check("منبع‌ها نام‌گذاری شده‌اند", srcs, ", ".join(sorted(srcs)))
check("بدون تاریخ ساخت، پیش‌فرض یا اولین‌دید می‌شود",
      srcs & {"پیش‌فرض", "اولین‌دید"},
      "x-ui این نسخه created_at خالی دارد")


head("اولین دیدن ثبت می‌شود")

bcon = APP._billing_conn()
try:
    seen = {r["email"]: r["first_seen"] for r in
            bcon.execute("SELECT email, first_seen FROM client_seen")}
finally:
    bcon.close()
check("همه‌ی کلاینت‌ها ثبت شدند", len(seen) == len(ROWS),
      f"{len(seen)} از {len(ROWS)}")
check("تاریخ معتبر است",
      all(len(v or "") == 10 for v in seen.values()),
      next(iter(seen.values()), ""))

# بار دوم نباید تاریخ را عوض کند
APP._billing_overview_impl()
bcon = APP._billing_conn()
try:
    seen2 = {r["email"]: r["first_seen"] for r in
             bcon.execute("SELECT email, first_seen FROM client_seen")}
finally:
    bcon.close()
check("اجرای دوباره اولین‌دید را عوض نمی‌کند", seen == seen2,
      "وگرنه هر بار صفحه باز شود، تاریخ شروع عقب می‌رود")


head("تنظیم دسته‌ای تاریخ شروع")

# فقط گروه‌های قابل صورت‌حساب تاریخ شروع لازم دارند
bcon = APP._billing_conn()
try:
    for g in ("ali", "unlimited", "Hossein naji"):
        bcon.execute("INSERT INTO group_config (group_key, billable) "
                     "VALUES (?,1) ON CONFLICT(group_key) DO UPDATE "
                     "SET billable=1", (g,))
    bcon.commit()
finally:
    bcon.close()

ov = APP._billing_overview_impl()
need = ov.get("needStart")
check("گروه‌های بی‌تاریخ فهرست می‌شوند", isinstance(need, list),
      f"{len(need or [])} گروه")

# این همان جایی بود که دیتابیس قفل می‌کرد
try:
    res = APP.billing_bulk_start({"start": "2024-09-01"}, x_admin_password="x")
    locked = False
except Exception as e:
    res, locked = {}, f"{type(e).__name__}: {str(e)[:70]}"
check("تنظیم دسته‌ای بدون قفل‌شدن انجام می‌شود", locked is False,
      locked or res.get("note", "")[:60])

if not locked:
    check("گزارش می‌گوید چند گروه عوض شد", "changed" in res,
          str(len(res.get("changed") or [])))

    ov2 = APP._billing_overview_impl()
    g2 = {g["key"]: g for g in ov2["groups"]}
    touched = [k for k in (res.get("changed") or []) if k in g2]
    check("تاریخ شروع واقعاً ذخیره شد",
          all(g2[k]["periodStart"] == "2024-09-01" for k in touched),
          f"{len(touched)} گروه")
    check("ماه‌ها بعد از تاریخ شروع بیشتر از یک شد",
          any(g2[k]["months"] > g2[k]["configs"] for k in touched)
          if touched else True,
          "هر کانفیگ باید بیش از یک ماه بشود")


head("تاریخ نامعتبر رد می‌شود")

for bad in ("۱۴۰۳-۰۶-۱۰", "2024/09/01", "hello", ""):
    try:
        APP.billing_bulk_start({"start": bad}, x_admin_password="x")
        okbad = False
    except Exception:
        okbad = True
    check(f"«{bad or 'خالی'}» رد می‌شود", okbad)


head("گروهی که تاریخ دارد بازنویسی نمی‌شود")

APP.billing_bulk_start({"start": "2023-01-01", "groups": ["ali"]},
                       x_admin_password="x")
r2 = APP.billing_bulk_start({"start": "2020-01-01", "groups": ["ali"]},
                            x_admin_password="x")
check("بدون overwrite دست‌نخورده می‌ماند", "ali" in (r2.get("skipped") or []),
      "تاریخی که مدیر گذاشته نباید خودکار عوض شود")

r3 = APP.billing_bulk_start({"start": "2020-01-01", "groups": ["ali"],
                             "overwrite": True}, x_admin_password="x")
check("با overwrite عوض می‌شود", "ali" in (r3.get("changed") or []))


# ═══════════════════════════════════════════════════════════
head("کدام کانفیگ نرخ می‌گیرد")

# قاعده‌ای که مالک خواست: فقط کانفیگ‌های در استفاده — ولی «منقضی شد»
# نباید راه فرار از پرداخت باشد، چون منقضی‌شدن یعنی دوره‌اش را کار
# کرده. ۳x-ui کانفیگ منقضی را خودش خاموش می‌کند، پس نگاه‌کردن فقط به
# enable یعنی هر کانفیگی با تمام‌شدن دوره‌اش از صورت‌حساب بیرون بیفتد.
GB2 = 1024 ** 3
CASES = [
    ("فعال، بدون مصرف", {"enable": 1, "used": 0,
                          "expiry": NOW_MS + 30 * 86400000}, True),
    ("فعال، با مصرف", {"enable": 1, "used": 5 * GB2,
                        "expiry": NOW_MS + 30 * 86400000}, True),
    ("غیرفعال ولی مصرف داشته", {"enable": 0, "used": 12 * GB2,
                                 "expiry": NOW_MS + 30 * 86400000}, True),
    ("منقضی — x-ui خاموشش کرده", {"enable": 0, "used": 0,
                                   "expiry": NOW_MS - 5 * 86400000}, True),
    ("ساخته شد و هرگز به کار نیفتاد", {"enable": 0, "used": 0,
                                        "expiry": NOW_MS + 30 * 86400000}, False),
    ("غیرفعال، بدون تاریخ انقضا", {"enable": 0, "used": 0,
                                    "expiry": 0}, False),
]

for label, cl, want in CASES:
    got, why = APP._billable_config(cl)
    check(f"{label} → {'نرخ می‌گیرد' if want else 'نرخ نمی‌گیرد'}",
          got is want, why)

check("منقضی‌شدن راه فرار نیست",
      APP._billable_config({"enable": 0, "used": 0,
                            "expiry": NOW_MS - 86400000})[0] is True,
      "کانفیگی که دوره‌اش تمام شده، آن دوره را کار کرده")

head("گروه، کنارگذاشته‌ها را گزارش می‌کند")

# یک کانفیگ بی‌استفاده به گروه ali اضافه می‌کنیم
xc = sqlite3.connect(XUI)
xc.execute("INSERT INTO clients (id,email,group_name,total_gb,expiry_time,"
           "enable,created_at) VALUES (99,'never_used','ali',50,?,0,NULL)",
           (NOW_MS + 30 * 86400000,))
xc.execute("INSERT INTO client_traffics (id,email,up,down,expiry_time,enable)"
           " VALUES (99,'never_used',0,0,?,0)", (NOW_MS + 30 * 86400000,))
xc.commit()
xc.close()

ov3 = APP._billing_overview_impl()
g3 = {g["key"]: g for g in ov3["groups"]}["ali"]
check("کانفیگ بی‌استفاده شمرده می‌شود", g3["configs"] >= 3,
      f"{g3['configs']} کانفیگ")
check("ولی از صورت‌حساب کنار گذاشته می‌شود", g3["skipped"] >= 1,
      f"{g3['skipped']} کنار گذاشته شد")
check("دلیلش گزارش می‌شود", bool(g3.get("skippedWhy")),
      "، ".join(g3.get("skippedWhy") or {}))
check("ماه‌ها فقط برای حساب‌شده‌ها جمع می‌شود",
      g3["months"] < g3["configs"] * 60,
      f"{g3['months']} ماه برای {g3['configs']} کانفیگ")



# ═══════════════════════════════════════════════════════════
head("تاریخ متنی — همان چیزی که x-ui واقعاً ذخیره می‌کند")

# _to_jalali فقط عدد می‌پذیرفت، ولی x-ui در بیشتر نسخه‌ها created_at
# را متنی نگه می‌دارد. صفحه‌ی «صورتحساب دوره» همان مقدار خام را
# می‌فرستاد، پس روی آن نصب‌ها با TypeError می‌افتاد.

check("متن ISO خوانده می‌شود",
      APP._epoch_ms("2024-03-11 09:22:00") is not None)
check("عدد میلی‌ثانیه دست‌نخورده می‌ماند",
      APP._epoch_ms(NOW_MS) == float(NOW_MS))
check("عدد ثانیه به میلی‌ثانیه تبدیل می‌شود",
      APP._epoch_ms(NOW_MS // 1000) == float(NOW_MS // 1000) * 1000,
      "x-ui هر دو شکل را می‌دهد")
check("متنِ عددی هم کار می‌کند",
      APP._epoch_ms(str(NOW_MS)) == float(NOW_MS))
check("خالی و بی‌معنی None می‌شود",
      all(APP._epoch_ms(v) is None
          for v in (None, "", 0, -5, "چیزی نیست", True)))

cj, cg = APP._to_jalali("2024-03-11 09:22:00")
check("تاریخ متنی به شمسی تبدیل می‌شود", bool(cg), f"{cj} / {cg}")
check("و با عدد همان نتیجه را می‌دهد",
      APP._to_jalali(APP._epoch_ms("2024-03-11 09:22:00"))[1] == cg)

head("تمدیدها با تاریخ متنی شمرده می‌شوند")

# _renewal_dates روی float(created) بود و با متن ValueError می‌داد،
# پس فهرست خالی برمی‌گشت: کانفیگی که دو سال تمدید شده بود، در
# صورتحساب *صفر* تمدید داشت و تقریباً کل مبلغ از قلم می‌افتاد.
TXT = {"email": "txt_1",
       "createdAt": "2024-09-12 10:00:00",
       "expiry": NOW_MS + 25 * 86400000}
rd = APP._renewal_dates(TXT, [])
check("تمدیدها از تاریخ متنی استنتاج می‌شوند", len(rd) > 20,
      f"{len(rd)} تمدید برای دو سال")
check("هر تمدید تاریخ میلادی معتبر دارد",
      all(len(d) == 10 and d[4] == "-" for d, _ in rd),
      rd[0][0] if rd else "")
check("و تخمینی علامت می‌خورد", all(k == "تخمینی" for _, k in rd))

NUM = {"email": "num_1",
       "createdAt": APP._epoch_ms("2024-09-12 10:00:00"),
       "expiry": NOW_MS + 25 * 86400000}
check("عدد و متن به یک نتیجه می‌رسند",
      len(APP._renewal_dates(NUM, [])) == len(rd),
      "وگرنه صورتحساب به شکل ذخیره‌سازی x-ui وابسته است")

head("_date_ms جای strftime(%s)")

from datetime import date as _date
check("نیمه‌شب تاریخ به میلی‌ثانیه",
      APP._date_ms(_date(2026, 1, 1)) == 1767225600000,
      str(APP._date_ms(_date(2026, 1, 1))))
check("و روی هر سیستمی یکسان است",
      APP._to_jalali(APP._date_ms(_date(2026, 1, 1)))[1] == "2026-01-01",
      "strftime('%s') افزونه‌ی glibc است و روی ویندوز خطا می‌دهد")



# ═══════════════════════════════════════════════════════════
head("صورتحساب «از ابتدا» در برابر دوره‌ی جاری")

# شکایت مالک: «حسابداری از قبل انجام نمیشه و جدیدها رو حساب می‌کنه».
# درست بود — دوره‌ی پیش‌فرض سی روز است، پس برای واسطه‌ای که دو سال
# کار کرده فقط کانفیگ‌های همین ماه دیده می‌شدند.

import json as _json
from datetime import datetime as _dtm, timedelta as _tdl

_c = sqlite3.connect(XUI)
for n, age in enumerate((730, 600, 400, 200, 15), start=200):
    _cr = (_dtm.now() - _tdl(days=age)).isoformat(sep=" ", timespec="seconds")
    _ex = NOW_MS + 25 * 86400000
    _c.execute("INSERT INTO clients (id,email,group_name,total_gb,expiry_time,"
               "enable,created_at) VALUES (?,?,?,?,?,1,?)",
               (n, f"vet_{n}", "قدیمی", 50, _ex, _cr))
    _c.execute("INSERT INTO client_traffics (id,email,up,down,expiry_time,enable)"
               " VALUES (?,?,?,?,?,1)", (n, f"vet_{n}", 3 * GB, 7 * GB, _ex))
_c.commit()
_c.close()

_b = sqlite3.connect(str(APP.BILLING_DB))
_b.execute("INSERT OR REPLACE INTO group_config (group_key,label,billable,"
           "rates,period_days) VALUES ('قدیمی','قدیمی',1,?,30)",
           (_json.dumps([{"gb": 50, "price": 150000}]),))
_b.commit()
_b.close()

cur = APP.billing_period("قدیمی", x_admin_password="x")
allt = APP.billing_period("قدیمی", full=1, x_admin_password="x")

check("دوره‌ی جاری فقط تازه‌ها را می‌بیند",
      cur["totals"]["newCount"] == 1,
      f"{cur['totals']['newCount']} کانفیگ از ۵")
check("«از ابتدا» همه را می‌بیند",
      allt["totals"]["newCount"] == 5,
      f"{allt['totals']['newCount']} کانفیگ")
check("و مبلغش بیشتر است",
      allt["totals"]["due"] > cur["totals"]["due"],
      f"{allt['totals']['due']} در برابر {cur['totals']['due']}")
check("تمدیدها صفر نیستند",
      allt["totals"]["renewalCount"] > 50,
      f"{allt['totals']['renewalCount']} تمدید — قبلاً صفر بود")
check("بازه از قدیمی‌ترین کانفیگ شروع می‌شود",
      allt["period"]["start"] < cur["period"]["start"],
      allt["period"]["start"])
check("پاسخ می‌گوید حالت «از ابتدا» است",
      allt["period"].get("full") is True,
      "تا صفحه بتواند برچسبش را درست بزند")
check("دوره‌ی جاری این نشانه را ندارد",
      not cur["period"].get("full"))
check("تاریخ شمسی هر دو سر بازه ساخته می‌شود",
      bool(allt["period"]["startJalali"]) and bool(allt["period"]["endJalali"]),
      f"{allt['period']['startJalali']} تا {allt['period']['endJalali']}")

head("تسویه‌شده‌ها حتی در «از ابتدا» برنمی‌گردند")

_b = sqlite3.connect(str(APP.BILLING_DB))
_b.execute("UPDATE group_config SET settled_until=? WHERE group_key='قدیمی'",
           ((_dtm.now() - _tdl(days=300)).date().isoformat(),))
_b.commit()
_b.close()

after = APP.billing_period("قدیمی", full=1, x_admin_password="x")
check("کانفیگ‌های تسویه‌شده کنار می‌روند",
      after["totals"]["newCount"] < allt["totals"]["newCount"],
      f"{after['totals']['newCount']} از {allt['totals']['newCount']}")
check("و شروع بازه جلو می‌آید",
      after["period"]["start"] > allt["period"]["start"],
      after["period"]["start"])
check("تعدادشان گزارش می‌شود", after["skippedSettled"] > 0,
      f"{after['skippedSettled']} تسویه‌شده")

_b = sqlite3.connect(str(APP.BILLING_DB))
_b.execute("UPDATE group_config SET settled_until=NULL WHERE group_key='قدیمی'")
_b.commit()
_b.close()



# ═══════════════════════════════════════════════════════════
head("مدت اشتراک با هر شکلی از تاریخ")

# _duration_days هم روی float(created) بود. با تاریخ متنی None
# برمی‌گرداند، پس ستون «مدت» در صورتحساب گروه و در فهرست کاربران
# برای *همه‌ی* کلاینت‌ها خالی می‌ماند.

_START_TXT = "2024-09-12 10:00:00"
_START_MS = APP._epoch_ms(_START_TXT)
_END_MS = _START_MS + 90 * 86400000

check("تاریخ متنی مدت می‌دهد",
      APP._duration_days(_START_TXT, _END_MS) == 90.0,
      str(APP._duration_days(_START_TXT, _END_MS)))
check("عدد هم همان را می‌دهد",
      APP._duration_days(_START_MS, _END_MS) == 90.0)
check("ثانیه و میلی‌ثانیه یکسان‌اند",
      APP._duration_days(_START_MS / 1000, _END_MS) == 90.0,
      "x-ui هر دو شکل را می‌دهد")
check("بدون تاریخ ساخت، None — نه صفر",
      APP._duration_days(None, _END_MS) is None,
      "صفر یعنی «مدت صفر» و با «نمی‌دانیم» فرق دارد")
check("بدون انقضا هم None", APP._duration_days(_START_TXT, 0) is None)
check("مدت منفی None می‌شود",
      APP._duration_days(_END_MS, _START_MS) is None,
      "انقضا قبل از ساخت یعنی داده خراب است")
check("متن بی‌معنی خطا نمی‌دهد",
      APP._duration_days("چیزی نیست", _END_MS) is None)



# ═══════════════════════════════════════════════════════════
head("گرد کردن ماه — نیم‌ماه همیشه به بالا")

# پایتون «گرد کردن بانکی» می‌کند: round(9.5)==10 ولی round(10.5)==10.
# یعنی دو کانفیگ که هر دو دقیقاً نیم‌ماه اضافه دارند، بسته به زوج یا
# فرد بودنِ عدد ماه، دو جور حساب می‌شدند.
check("۹.۵ ماه → ۱۰", APP._months_from_days(285) == 10,
      str(APP._months_from_days(285)))
check("۱۰.۵ ماه → ۱۱ (نه ۱۰)", APP._months_from_days(315) == 11,
      f"{APP._months_from_days(315)} — round(10.5) در پایتون ۱۰ می‌دهد")
check("۱۱.۵ ماه → ۱۲", APP._months_from_days(345) == 12)
check("زیر نیم پایین می‌رود", APP._months_from_days(284) == 9,
      str(APP._months_from_days(284)))
check("یک ماه کف است", APP._months_from_days(1) == 1)
check("صفر و منفی هم یک ماه", APP._months_from_days(0) == 1
      and APP._months_from_days(-10) == 1,
      "کانفیگی که وجود دارد دست‌کم یک دوره کار کرده")

check("یک ثانیه اختلاف، ماه را عوض نمی‌کند",
      APP._months_from_days(285) == APP._months_from_days(285 - 1 / 86400.0)
      == APP._months_from_days(285 + 1 / 86400.0),
      "مرزِ دقیق نیم‌ماه نباید به کسری از ثانیه حساس باشد")
check("ورودی بی‌معنی یک ماه می‌دهد",
      APP._months_from_days(None) == 1 and APP._months_from_days("x") == 1)


head("عدد صورتحساب نباید به شکل ذخیره‌سازی x-ui وابسته باشد")

# این بلوک برای همین کلاس از باگ نوشته شده: کدی که فرض می‌کند
# created_at عدد است، روی نصب‌هایی که متن ذخیره می‌کنند بی‌صدا
# عددهای غلط می‌دهد. دو دیتابیس یکسان می‌سازیم — یکی متنی، یکی
# عددی — و انتظار داریم *همه‌ی* عددها یکی دربیایند.

from datetime import datetime as _d2, timedelta as _t2
import shutil as _sh

_AGES = (700, 430, 260, 95, 40)


def _build(as_text):
    d = tempfile.mkdtemp()
    x = os.path.join(d, "x-ui.db")
    c = sqlite3.connect(x)
    c.executescript("""
    CREATE TABLE clients (id INTEGER PRIMARY KEY, email TEXT, group_name TEXT,
     total_gb INTEGER, expiry_time INTEGER, enable INTEGER, created_at,
     limit_ip INTEGER DEFAULT 0);
    CREATE TABLE client_traffics (id INTEGER PRIMARY KEY, email TEXT, up INTEGER,
     down INTEGER, expiry_time INTEGER, enable INTEGER);
    """)
    for n, age in enumerate(_AGES, start=1):
        # ثانیه‌ی گرد: متنِ x-ui دقت ثانیه دارد، پس اگر عددی را با
        # میلی‌ثانیه بسازیم دو ورودیِ واقعاً متفاوت مقایسه می‌کنیم.
        born = (_d2.now() - _t2(days=age)).replace(microsecond=0)
        created = (born.isoformat(sep=" ", timespec="seconds") if as_text
                   else int(born.timestamp() * 1000))
        exp = NOW_MS + 25 * 86400000
        c.execute("INSERT INTO clients (id,email,group_name,total_gb,"
                  "expiry_time,enable,created_at) VALUES (?,?,?,?,?,1,?)",
                  (n, f"cmp_{n}", "مقایسه", 50, exp, created))
        c.execute("INSERT INTO client_traffics (id,email,up,down,expiry_time,"
                  "enable) VALUES (?,?,?,?,?,1)", (n, f"cmp_{n}", GB, GB, exp))
    c.commit()
    c.close()

    b = os.path.join(d, "billing.db")
    return x, b


def _numbers(xpath, bpath):
    """همان عددهایی که مدیر روی صفحه می‌بیند."""
    APP._xui_db_path = lambda: Path(xpath)
    APP.BILLING_DB = Path(bpath)
    con2 = sqlite3.connect(bpath)
    APP._billing_conn().close()          # جدول‌ها ساخته شوند
    con2.close()
    b = sqlite3.connect(bpath)
    b.execute("INSERT OR REPLACE INTO group_config (group_key,label,billable,"
              "rates,period_days) VALUES ('مقایسه','مقایسه',1,?,30)",
              ('[{"gb": 50, "price": 100000}]',))
    b.commit()
    b.close()

    ov = APP._billing_overview_impl()
    g = {x["key"]: x for x in ov["groups"]}.get("مقایسه", {})
    inv = APP.billing_period("مقایسه", full=1, x_admin_password="x")
    return {
        "configs": g.get("configs"),
        "months": g.get("months"),
        "due": g.get("due"),
        "newCount": inv["totals"]["newCount"],
        "renewalCount": inv["totals"]["renewalCount"],
        "invoiceDue": inv["totals"]["due"],
        "start": inv["period"]["start"],
    }


_xt, _bt = _build(as_text=True)
_xn, _bn = _build(as_text=False)
_saved_x, _saved_b = APP._xui_db_path, APP.BILLING_DB

txt = _numbers(_xt, _bt)
num = _numbers(_xn, _bn)

check("تعداد کانفیگ یکی است",
      txt["configs"] == num["configs"] == len(_AGES),
      f"متنی {txt['configs']} · عددی {num['configs']}")
check("ماه‌ها یکی است", txt["months"] == num["months"],
      f"متنی {txt['months']} · عددی {num['months']}")
check("بدهی نمای کلی یکی است", txt["due"] == num["due"],
      f"متنی {txt['due']} · عددی {num['due']}")
check("کانفیگ‌های جدیدِ صورتحساب یکی است",
      txt["newCount"] == num["newCount"],
      f"متنی {txt['newCount']} · عددی {num['newCount']}")
check("تمدیدها یکی است — و صفر نیست",
      txt["renewalCount"] == num["renewalCount"] > 0,
      f"متنی {txt['renewalCount']} · عددی {num['renewalCount']}")
check("مبلغ صورتحساب یکی است",
      txt["invoiceDue"] == num["invoiceDue"],
      f"متنی {txt['invoiceDue']} · عددی {num['invoiceDue']}")
check("شروع بازه‌ی «از ابتدا» یکی است",
      txt["start"] == num["start"],
      f"متنی {txt['start']} · عددی {num['start']}")
check("و مبلغ واقعاً محاسبه شده، نه صفر",
      (txt["invoiceDue"] or 0) > 0, str(txt["invoiceDue"]))

APP._xui_db_path, APP.BILLING_DB = _saved_x, _saved_b



print(f"\n{D}{'─' * 50}{X}")
color = G if not _fail else R
# ═══════════════════════════════════════════════════════════
head("هزینه‌ی سالانه هم بار ماهانه است")

# کارت «هزینه‌ی ثابت ماهانه» می‌گوید «این مبلغ را هر ماه باید
# دربیاورید». هزینه‌ی سالانه — دامنه، لایسنس — کلاً کنار گذاشته
# می‌شد و صفر حساب می‌آمد. یعنی همان خطایی که این بخش برای
# جلوگیری از آن ساخته شده: اشتباه، و همیشه به نفع خودِ مدیر.

_bc = APP._billing_conn()
try:
    _bc.execute("DELETE FROM expenses")
    for _kind, _label, _irt, _rec in (
            ("server_abroad", "هتزنر", 3_000_000, "monthly"),
            ("domain", "دامنه‌ی ir", 1_200_000, "yearly"),
            ("other", "یک‌بار", 500_000, "once")):
        _bc.execute(
            "INSERT INTO expenses (kind,label,amount,currency,amount_irt,"
            "recurring,spent_at) VALUES (?,?,?,?,?,?,?)",
            (_kind, _label, _irt, "IRT", _irt, _rec, "2025-01-01"))
    _bc.commit()
finally:
    _bc.close()

_ex = APP.expenses_list(months=120, x_admin_password="x")

check("سهم ماهانه‌ی هزینه‌ی سالانه شمرده می‌شود",
      _ex["monthlyFromYearly"] == 100_000,
      f"۱٬۲۰۰٬۰۰۰ ÷ ۱۲ = {_ex['monthlyFromYearly']:,}")
check("و در بار ماهانه جمع می‌شود",
      _ex["monthlyRecurring"] == 3_100_000,
      f"{_ex['monthlyRecurring']:,} — قبلاً ۳٬۰۰۰٬۰۰۰ بود")
check("هزینه‌ی یک‌بار در بار ماهانه نمی‌آید",
      _ex["monthlyRecurring"] < 3_500_000,
      "«یک‌بار» یعنی یک‌بار")
check("جمع سالانه جدا هم گزارش می‌شود",
      _ex["yearlyTotal"] == 1_200_000)
check("جمع کل هر سه را دارد", _ex["allTimeTotal"] == 4_700_000,
      f"{_ex['allTimeTotal']:,}")

_bc = APP._billing_conn()
try:
    _bc.execute("DELETE FROM expenses WHERE recurring='yearly'")
    _bc.commit()
finally:
    _bc.close()
_ex2 = APP.expenses_list(months=120, x_admin_password="x")
check("بدون هزینه‌ی سالانه، عدد همان قبلی است",
      _ex2["monthlyRecurring"] == 3_000_000
      and _ex2["monthlyFromYearly"] == 0,
      "رفتار قبلی برای کسی که هزینه‌ی سالانه ندارد عوض نمی‌شود")

JSX = io.open(os.path.join(ROOT, "frontend", "src", "sections",
                           "expenses.jsx"), encoding="utf-8").read()
check("کارت می‌گوید این عدد از کجا آمده",
      "monthlyFromYearly" in JSX and "هزینه‌های سالانه" in JSX,
      "عددی که بی‌توضیح بالا برود، مدیر فکر می‌کند اشتباه است")


# ═══════════════════════════════════════════════════════════
head("تمدیدی که واسطه مستقیم در پنل زده باید دیده شود")

# پنل دست واسطه است. او کانفیگ را همان‌جا در x-ui تمدید می‌کند و
# هیچ‌جا ثبت نمی‌شود — نه در ربات، نه در x-ui که تاریخچه ندارد. مدیر
# نمی‌فهمد کدام مشتری تمدید کرده و چند بار؛ فقط می‌بیند واسطه چند
# کانفیگ دارد.
#
# جدول renewals از روز اول وجود داشت، با توضیحی که می‌گفت «از امروز
# خودمان ثبت می‌کنیم» — ولی هیچ‌جای کد چیزی در آن نمی‌نوشت.

import time as _t  # noqa: E402

_DAY = 86400000
_now = int(_t.time() * 1000)


def _cl(email, exp_ms, gb=50):
    return {"email": email, "group": "g1", "expiry": exp_ms,
            "totalGB": gb * 1024 ** 3, "used": 0, "enable": True,
            "createdAt": _now - 60 * _DAY, "limitIp": 0}


_bc = APP._billing_conn()
try:
    _bc.execute("DELETE FROM client_seen")
    _bc.execute("DELETE FROM renewals")
    _bc.commit()

    # اولین خواندن: هنوز چیزی نمی‌دانیم، پس تمدیدی ثبت نمی‌شود
    APP._record_seen(_bc, [_cl("a@x", _now + 10 * _DAY)])
    _n = _bc.execute("SELECT COUNT(*) c FROM renewals").fetchone()["c"]
    check("اولین دیدن تمدید حساب نمی‌شود", _n == 0,
          "هیچ مبنایی برای مقایسه نیست")

    _seen = _bc.execute(
        "SELECT last_expiry FROM client_seen WHERE email='a@x'").fetchone()
    check("ولی انقضا به خاطر سپرده می‌شود",
          _seen and _seen["last_expiry"] == _now + 10 * _DAY,
          "بدون این، دفعه‌ی بعد هم چیزی فهمیده نمی‌شود")

    # واسطه یک ماه تمدید می‌کند
    APP._record_seen(_bc, [_cl("a@x", _now + 40 * _DAY)])
    _r = [dict(r) for r in _bc.execute("SELECT * FROM renewals")]
    check("تمدید یک‌ماهه دیده شد", len(_r) == 1, f"{len(_r)} ردیف")
    check("و یک ماه حساب شد", _r and _r[0]["months"] == 1,
          str(_r[0]["months"]) if _r else "-")
    check("و به نام همان کانفیگ", _r and _r[0]["email"] == "a@x")

    # خواندن دوباره بدون تغییر — نباید دو بار ثبت شود
    APP._record_seen(_bc, [_cl("a@x", _now + 40 * _DAY)])
    _n = _bc.execute("SELECT COUNT(*) c FROM renewals").fetchone()["c"]
    check("خواندن دوباره تمدید تکراری نمی‌سازد", _n == 1, f"{_n} ردیف")

    # تغییر چندروزه اصلاح دستی است، نه فروش
    APP._record_seen(_bc, [_cl("a@x", _now + 45 * _DAY)])
    _n = _bc.execute("SELECT COUNT(*) c FROM renewals").fetchone()["c"]
    check("جابه‌جایی چندروزه تمدید حساب نمی‌شود", _n == 1,
          "کمتر از ۲۰ روز معمولاً اصلاح دستی است")

    # تمدید سه‌ماهه
    APP._record_seen(_bc, [_cl("a@x", _now + 135 * _DAY)])
    _r = [dict(r) for r in _bc.execute(
        "SELECT * FROM renewals ORDER BY id DESC LIMIT 1")]
    check("تمدید سه‌ماهه هم درست شمرده می‌شود",
          _r and _r[0]["months"] == 3, str(_r[0]["months"]) if _r else "-")

    # انقضایی که عقب کشیده شده تمدید نیست
    APP._record_seen(_bc, [_cl("a@x", _now + 5 * _DAY)])
    _n = _bc.execute("SELECT COUNT(*) c FROM renewals").fetchone()["c"]
    check("عقب‌رفتن انقضا تمدید نیست", _n == 2, f"{_n} ردیف")
finally:
    _bc.close()

# ── ثبت‌شده باید کف باشد، نه سقف ──
#
# ثبت از روزی شروع می‌شود که نکسورا نصب شده. کانفیگی که دو سال سابقه
# دارد و یک تمدیدِ ثبت‌شده، نباید «۲ ماه» بشود.
_old = {"email": "b@x", "group": "g1", "expiry": _now + 30 * _DAY,
        "totalGB": 50 * 1024 ** 3, "used": 0, "enable": True,
        "createdAt": _now - 720 * _DAY, "limitIp": 0}
_m, _k, _d = APP._months_for(_old, {"b@x": 1})
check("سابقه‌ی قدیمی با یک تمدیدِ ثبت‌شده کوچک نمی‌شود", _m >= 24,
      f"{_m} ماه — تخمینِ فاصله‌ی ساخت تا انقضا برنده می‌شود")

# و برعکس: وقتی تخمین کم می‌آورد، ثبت‌شده نجاتش می‌دهد
_short = {"email": "c@x", "group": "g1", "expiry": _now + 30 * _DAY,
          "totalGB": 50 * 1024 ** 3, "used": 0, "enable": True,
          "createdAt": _now - 10 * _DAY, "limitIp": 0}
_m2, _k2, _d2 = APP._months_for(_short, {"c@x": 5})
check("تمدید با «تاریخ تازه» دیگر گم نمی‌شود", _m2 == 6,
      f"{_m2} ماه — تخمین ۱ می‌داد، ثبت‌شده ۶ می‌گوید")
check("و منبعش صریح گفته می‌شود", _k2 == "ثبت‌شده", _k2)


# ═══════════════════════════════════════════════════════════
head("شماره‌ی صفحه‌ی فاکتور PDF")

# فوتر اولِ هر صفحه کشیده می‌شد، یعنی صفحه‌ی اول قبل از اینکه تعداد
# کل حساب شود. نتیجه: فاکتور ۹۴ کانفیگی شش صفحه بود و پایین صفحه‌ی
# اولش می‌نوشت «صفحه ۱ از ۱» — مدیر فکر می‌کرد تمام شده و بقیه‌ی
# کانفیگ‌ها از قلم افتاده‌اند.
#
# تعداد کل هم پیش‌بینی می‌شد و همیشه یک صفحه‌ی اضافه برای توضیحات
# فرض می‌کرد، پس حتی وقتی درست کشیده می‌شد عددش غلط بود.

try:
    import reportlab  # noqa: F401
    _have_pdf = True
except ImportError:
    _have_pdf = False

if not _have_pdf:
    check("reportlab نصب نیست — این بخش رد شد", True, "روی سرور نصب است")
else:
    from reportlab.pdfgen import canvas as _pc
    import unicodedata as _ud

    def _mk_lines(n):
        out = []
        for i in range(n):
            ren = 2 if i % 6 == 0 else (1 if i % 3 == 0 else 0)
            out.append({
                "email": "user%03d" % i, "gb": 200, "gbLabel": "200",
                "usedGB": 98.2, "usagePct": (49 if i else None),
                "limitIp": (0 if i == 12 else 2),
                "createdJalali": "1405/04/30", "createdGregorian": "2026-07-21",
                "expiryJalali": ("" if i == 12 else "1405/07/20"),
                "expiryGregorian": "2026-10-12",
                "days": (0 if i == 12 else 83.1),
                "months": 1 + ren, "renewals": ren, "kind": "تخمینی",
                "drift": 0, "price": 190000, "priceWhy": None,
                "amount": 190000 * (1 + ren), "active": True,
                "status": "فعال", "expiry": 1790000000000,
            })
        return out

    def _footers_for(n):
        """(تعداد فوتر, تعداد کلی که در فوترها نوشته شده)"""
        lines = _mk_lines(n)
        totals = {"configs": n, "months": 110, "renewals": 16,
                  "renewalRate": 17.0, "quotaGB": 17680, "usedGB": 3885,
                  "usagePct": 22.0, "due": 20900000, "paid": 0,
                  "balance": 20900000, "unpriced": 0, "estimated": 16,
                  "active": 73, "inactive": 17, "notStarted": 0, "noExpiry": 1}
        real = APP.billing_invoice
        APP.billing_invoice = lambda g, start="", x_admin_password=None: {
            "label": "g", "lines": lines, "totals": totals,
            "unpricedVolumes": [], "unpricedWhy": [], "payments": [],
            "paid": 0, "balance": 20900000, "totalAmount": 20900000,
            "generatedAt": "1405/06/23", "review": []}
        seen = []
        orig = _pc.Canvas.drawCentredString

        def spy(self, x, y, text, *a, **k):
            if y < 30:
                seen.append(text)
            return orig(self, x, y, text, *a, **k)

        _pc.Canvas.drawCentredString = spy
        try:
            APP.billing_invoice_pdf("g", x_admin_password="x")
        finally:
            _pc.Canvas.drawCentredString = orig
            APP.billing_invoice = real

        totals_written = set()
        for t in seen:
            d = "".join(ch for ch in _ud.normalize("NFKC", t) if ch.isdigit())
            # بعد از bidi، اول تعداد کل می‌آید بعد شماره‌ی صفحه
            totals_written.add(d[:len(str(len(seen)))])
        return len(seen), totals_written

    for _n in (1, 15, 94, 200):
        _pages, _written = _footers_for(_n)
        check("هر صفحه یک فوتر دارد (%d کانفیگ)" % _n, _pages >= 1,
              "%d صفحه" % _pages)
        check("و تعداد کل درست نوشته شده (%d کانفیگ)" % _n,
              _written == {str(_pages)},
              "نوشته: %s · واقعی: %d" % (sorted(_written), _pages))

    check("جای خالی با خط تیره‌ی ساده پر می‌شود",
          'DASH = "-"' in io.open(os.path.join(ROOT, "backend", "app.py"),
                                  encoding="utf-8").read(),
          "خط تیره‌ی بلند در فونت فارسیِ سرور گلیف ندارد و مربع می‌شود")


# ═══════════════════════════════════════════════════════════
head("گروه‌هایی که هیچ درآمدی از آن‌ها شمرده نمی‌شود")

# روی سرور واقعی ۹۴ کانفیگ در هفت گروه بودند که در صورتحساب
# نمی‌آمدند، و هیچ‌جای پنل این را یکجا نمی‌گفت. مدیر فقط می‌دید عدد
# کل کمتر از انتظارش است.

APP_SRC_NS = io.open(os.path.join(ROOT, "backend", "app.py"),
                     encoding="utf-8").read()
check("نمای کلی فهرست «نیاز به تنظیم» می‌دهد",
      '"needsSetup": needs' in APP_SRC_NS)
check("و جمع کانفیگ‌هایش را هم", '"needsSetupConfigs"' in APP_SRC_NS)
check("گروه خاموش شناسایی می‌شود",
      'if not g["billable"]' in APP_SRC_NS and "خاموش است" in APP_SRC_NS)
check("گروه بدون نرخ هم", "هیچ نرخی تعریف نشده" in APP_SRC_NS)
check("و گروهی که بعضی حجم‌هایش نرخ ندارند",
      'elif g["unpriced"]' in APP_SRC_NS)
check("گروه بی‌کانفیگ در فهرست نمی‌آید",
      'if g["configs"] <= 0:' in APP_SRC_NS,
      "گروه خالی چیزی برای تنظیم ندارد")

BJ = io.open(os.path.join(ROOT, "frontend", "src", "sections", "billing.jsx"),
             encoding="utf-8").read()
check("پنل هم نشانش می‌دهد", "نیاز به تنظیم" in BJ)
check("با دکمه‌ای که همان گروه را باز می‌کند", "setOpen(n.key)" in BJ)


# ═══════════════════════════════════════════════════════════
head("صورتحساب از یک تاریخ به بعد — نه از اول دنیا")

# شکایت مالک: «تمدیدی‌ها هم باید از اون تاریخی که می‌خوام فاکتور
# بگیرم یا همون شروع همکاری حساب کنه … تمدیدی‌های قبل رو حساب نکنه».
#
# درست بود. billing_invoice — که PDF هم از آن ساخته می‌شود — هیچ
# تاریخی نمی‌دید و کل عمر هر کانفیگ را می‌شمرد. «تسویه‌شده تا» در
# پایگاه داده بود و فقط صفحه‌ی دوره‌ای رعایتش می‌کرد.

_DAY = 86400000
_SINCE = (_dtm.now() - _tdl(days=90)).date().isoformat()

_c = sqlite3.connect(XUI)
#            ایمیل      روز از ساخت   انقضا (روز از حالا)  فعال
for _id, _em, _age, _exp_in, _en in (
        (300, "per_old", 400, +25, 1),     # عمرش ۱۴ ماه، ۳ ماهش در بازه
        (301, "per_new", 10, +20, 1),      # تازه — همه‌اش در بازه
        (302, "per_done", 400, -300, 0)):  # عمرش ۳ ماه، همه‌اش پیش از بازه
    _cr = (_dtm.now() - _tdl(days=_age)).isoformat(sep=" ", timespec="seconds")
    _ex = NOW_MS + _exp_in * _DAY
    _c.execute("INSERT INTO clients (id,email,group_name,total_gb,expiry_time,"
               "enable,created_at) VALUES (?,?,?,0,?,?,?)",
               (_id, _em, "بازه", _ex, _en, _cr))
    _c.execute("INSERT INTO client_traffics (id,email,up,down,expiry_time,enable)"
               " VALUES (?,?,?,?,?,?)", (_id, _em, 1 * GB, 4 * GB, _ex, _en))
_c.commit()
_c.close()

_b = sqlite3.connect(str(APP.BILLING_DB))
_b.execute("INSERT OR REPLACE INTO group_config (group_key,label,billable,"
           "rates,period_days,settled_until) VALUES ('بازه','بازه',1,?,30,?)",
           (_json.dumps([{"gb": 0, "price": 200000}]), _SINCE))
# یکی پیش از تسویه، یکی بعدش
_b.execute("DELETE FROM payments WHERE group_key='بازه'")
for _amt, _ago in ((1_000_000, 200), (300_000, 30)):
    _b.execute("INSERT INTO payments (group_key,amount,paid_at) VALUES (?,?,?)",
               ("بازه", _amt,
                (_dtm.now() - _tdl(days=_ago)).date().isoformat()))
_b.commit()
_b.close()

_inv = APP.billing_invoice("بازه", x_admin_password="x")
_t = _inv["totals"]
_by = {l["email"]: l for l in _inv["lines"]}

check("مبدأ از «تسویه‌شده تا» برداشته می‌شود",
      _inv["since"] == _SINCE and _inv["sinceWhy"] == "تسویه‌شده تا",
      f"{_inv['since']} · {_inv['sinceWhy']}")
check("و شمسی‌اش هم برای فاکتور آماده است",
      bool(_inv.get("sinceJalali")), str(_inv.get("sinceJalali")))

check("کانفیگی که همه‌ی ماه‌هایش پیش از مبدأ بوده، اصلاً نمی‌آید",
      "per_done" not in _by, ", ".join(sorted(_by)))
check("ولی بی‌صدا گم نمی‌شود — شمرده می‌شود",
      _t["before"] == 1 and _t["beforeMonths"] == 3,
      f"{_t['before']} کانفیگ · {_t['beforeMonths']} ماه")

check("از کانفیگ قدیمی فقط تمدیدهای داخل بازه حساب می‌شود",
      _by["per_old"]["months"] == 3, str(_by["per_old"]["months"]))
check("و عمر کاملش جدا گزارش می‌شود",
      _by["per_old"]["totalMonths"] == 14,
      f"{_by['per_old']['totalMonths']} ماه در کل — قبلاً همین روی فاکتور بود")
check("ماه اولش دوباره فروخته نمی‌شود",
      _by["per_old"]["newInPeriod"] is False,
      "ساختش ۴۰۰ روز پیش بوده، نه در این بازه")
check("و هر سه ماهش تمدید است، نه دو تا",
      _by["per_old"]["renewals"] == 3,
      "وقتی ساخت بیرون بازه است، renewals = months نه months-1")

check("کانفیگ تازه کامل حساب می‌شود",
      _by["per_new"]["months"] == 1 and _by["per_new"]["newInPeriod"] is True)

check("مبلغ فقط بابت همین بازه است",
      _t["due"] == 4 * 200_000, f"{_t['due']:,}")
check("پرداختیِ پیش از تسویه دوباره اعتبار نمی‌شود",
      _t["paid"] == 300_000, f"{_t['paid']:,}")
check("پس مانده همان چیزی است که واقعاً طلب است",
      _t["balance"] == 500_000, f"{_t['balance']:,}")


head("و همان فاکتور بدون مبدأ، کل عمر را می‌شمارد")

_b = sqlite3.connect(str(APP.BILLING_DB))
_b.execute("UPDATE group_config SET settled_until=NULL, period_start=NULL "
           "WHERE group_key='بازه'")
_b.commit()
_b.close()

_all = APP.billing_invoice("بازه", x_admin_password="x")
check("بدون هیچ تاریخی، رفتار قبلی دست‌نخورده است",
      _all["since"] is None and _all["totals"]["months"] == 14 + 1 + 3,
      f"{_all['totals']['months']} ماه")
check("و مبلغش خیلی بیشتر است",
      _all["totals"]["due"] == 18 * 200_000,
      f"{_all['totals']['due']:,} در برابر {_t['due']:,}")
check("پرداختیِ کل هم برمی‌گردد",
      _all["totals"]["paid"] == 1_300_000, f"{_all['totals']['paid']:,}")
check("این تفاوت دقیقاً همان دوباره‌حساب‌کردنی است که گزارش شد",
      _all["totals"]["due"] > _t["due"] * 4,
      "۱۴ ماه به‌جای ۳ ماه، بابت کانفیگی که ماه پیش تسویه شده بود")


head("تاریخ انتخابیِ مدیر بر همه چیز مقدم است")

_pick = (_dtm.now() - _tdl(days=45)).date().isoformat()
_sel = APP.billing_invoice("بازه", start=_pick, x_admin_password="x")
check("همان تاریخ به کار می‌رود", _sel["since"] == _pick,
      f"{_sel['since']} · {_sel['sinceWhy']}")
check("و بازه‌ی کوتاه‌تر، ماه کمتری می‌دهد",
      _sel["totals"]["months"] < _t["months"],
      f"{_sel['totals']['months']} در برابر {_t['months']}")

_b = sqlite3.connect(str(APP.BILLING_DB))
_b.execute("UPDATE group_config SET period_start=? WHERE group_key='بازه'",
           (_SINCE,))
_b.commit()
_b.close()
_ps = APP.billing_invoice("بازه", x_admin_password="x")
check("نبودِ «تسویه‌شده تا»، «شروع همکاری» را جانشین می‌کند",
      _ps["since"] == _SINCE and _ps["sinceWhy"] == "شروع همکاری",
      f"{_ps['since']} · {_ps['sinceWhy']}")
check("تاریخ خراب نادیده گرفته می‌شود، نه اینکه فاکتور بترکد",
      APP.billing_invoice("بازه", start="۱۴۰۴/۰۱/۰۱",
                          x_admin_password="x")["sinceWhy"] == "شروع همکاری",
      "برمی‌گردد به پیش‌فرض گروه")


head("شمارش تمدید یک منبع دارد، نه دو تا")

# _renewal_dates اگر حتی یک تمدیدِ ثبت‌شده می‌دید، بقیه را دور
# می‌ریخت. کانفیگی با دو سال سابقه و یک تمدید ثبت‌شده، در صورتحساب
# ۲۵ ماه بود و در صفحه‌ی دوره‌ای یک تمدید.
_cl = {"email": "mix_1",
       "createdAt": (_dtm.now() - _tdl(days=740)).isoformat(sep=" ",
                                                            timespec="seconds"),
       "expiry": NOW_MS + 20 * _DAY}
_rows = [{"email": "mix_1", "months": 1,
          "created_at": (_dtm.now() - _tdl(days=20)).date().isoformat()}]
_m, _k, _d = APP._months_for(_cl, {"mix_1": 1})
_rd = APP._renewal_dates(_cl, _rows, _m)
check("تعداد تاریخ‌ها با تعداد ماه‌ها می‌خواند", len(_rd) == _m - 1,
      f"{len(_rd)} تاریخ برای {_m} ماه")
check("تمدیدِ ثبت‌شده هنوز قطعی علامت می‌خورد",
      sum(1 for _, k in _rd if k == "قطعی") == 1)
check("و بقیه تخمینی", sum(1 for _, k in _rd if k == "تخمینی") == _m - 2)
check("تاریخ‌ها مرتب و معتبرند",
      _rd == sorted(_rd) and all(len(d) == 10 for d, _ in _rd),
      _rd[0][0] if _rd else "")

# تمدید سه‌ماهه سه ماه صورتحساب است، نه یکی
_cl2 = {"email": "three_1",
        "createdAt": (_dtm.now() - _tdl(days=120)).isoformat(sep=" ",
                                                             timespec="seconds"),
        "expiry": NOW_MS + 10 * _DAY}
_rows2 = [{"email": "three_1", "months": 3,
           "created_at": (_dtm.now() - _tdl(days=15)).date().isoformat()}]
_m2, _, _ = APP._months_for(_cl2, {"three_1": 3})
_rd2 = APP._renewal_dates(_cl2, _rows2, _m2)
check("ردیفِ تمدید سه‌ماهه سه تاریخ می‌دهد",
      sum(1 for _, k in _rd2 if k == "قطعی") == 3,
      "قبلاً یک تمدید حساب می‌شد و دو ماهش از فاکتور می‌افتاد")


# ═══════════════════════════════════════════════════════════
head("هشدار «حجم بدون نرخ» واقعاً چیزی برای نشان‌دادن دارد")

# unpricedVolumes یک *عدد* برمی‌گشت، و رابط کاربری روی همان .length و
# .map صدا می‌زد — یعنی هشدار هرگز رندر نمی‌شد.
_b = sqlite3.connect(str(APP.BILLING_DB))
_b.execute("UPDATE group_config SET rates='[]', settled_until=NULL, "
           "period_start=NULL WHERE group_key='بازه'")
_b.commit()
_b.close()
_np = APP.billing_invoice("بازه", x_admin_password="x")
check("فهرست است، نه عدد", isinstance(_np["unpricedVolumes"], list),
      str(type(_np["unpricedVolumes"]).__name__))
check("و واقعاً حجم‌های بی‌نرخ را می‌شمارد",
      len(_np["unpricedVolumes"]) >= 1,
      str(_np["unpricedVolumes"]))


# ═══════════════════════════════════════════════════════════
head("داشبورد و فاکتور باید یک عدد بدهند")

# دو صفحه، دو حساب جدا — و آن‌که برچسب «کل بدهی دوره» داشت، عدد کلِ
# عمر را نشان می‌داد.
#
# دو اختلاف واقعی بود:
#   ۱. نمای کلی «تسویه‌شده تا» را اصلاً نمی‌دید
#   ۲. صورتحساب قاعده‌ی «قابل صورتحساب» را به کار نمی‌برد، پس بابت
#      کانفیگی که هرگز روشن نشده پول می‌گرفت — روی همان کاغذی که
#      دست واسطه می‌رسد

_ALIGN = (_dtm.now() - _tdl(days=90)).date().isoformat()

_c = sqlite3.connect(XUI)
#            ایمیل        روز از ساخت  انقضا   فعال  مصرف
for _id, _em, _age, _exp_in, _en, _used in (
        (400, "algn_old", 400, +25, 1, 6 * GB),    # ۱۴ ماه عمر، ۳ ماه در بازه
        (401, "algn_new", 10, +20, 1, 2 * GB),     # تازه — کامل در بازه
        (402, "algn_dead", 400, -300, 0, 9 * GB),  # ۳ ماه، همه پیش از بازه
        (403, "algn_never", 5, +25, 0, 0)):        # ساخته شد، هرگز روشن نشد
    _cr = (_dtm.now() - _tdl(days=_age)).isoformat(sep=" ", timespec="seconds")
    _ex = NOW_MS + _exp_in * 86400000
    _c.execute("INSERT INTO clients (id,email,group_name,total_gb,expiry_time,"
               "enable,created_at,limit_ip) VALUES (?,?,'همسو',0,?,?,?,1)",
               (_id, _em, _ex, _en, _cr))
    _c.execute("INSERT INTO client_traffics (id,email,up,down,expiry_time,enable)"
               " VALUES (?,?,0,?,?,?)", (_id, _em, _used, _ex, _en))
_c.commit()
_c.close()

_b = sqlite3.connect(str(APP.BILLING_DB))
_b.execute("INSERT OR REPLACE INTO group_config (group_key,label,billable,"
           "rates,period_days,settled_until) VALUES ('همسو','همسو',1,?,30,?)",
           (_json.dumps([{"gb": 0, "price": 100000}]), _ALIGN))
_b.execute("DELETE FROM payments WHERE group_key='همسو'")
for _amt, _ago in ((500_000, 200), (200_000, 30)):
    _b.execute("INSERT INTO payments (group_key,amount,paid_at) VALUES (?,?,?)",
               ("همسو", _amt, (_dtm.now() - _tdl(days=_ago)).date().isoformat()))
_b.commit()
_b.close()

_ov = {x["key"]: x for x in APP._billing_overview_impl()["groups"]}["همسو"]
_iv = APP.billing_invoice("همسو", x_admin_password="x")
_it = _iv["totals"]

check("مبلغ دو صفحه یکی است", _ov["due"] == _it["due"],
      f"داشبورد {_ov['due']:,} · فاکتور {_it['due']:,}")
check("تعداد ماه هم", _ov["months"] == _it["months"],
      f"{_ov['months']} · {_it['months']}")
check("تعداد تمدید هم", _ov["renewals"] == _it["renewals"],
      f"{_ov['renewals']} · {_it['renewals']}")
check("پرداختی هم", _ov["paid"] == _it["paid"],
      f"{_ov['paid']:,} · {_it['paid']:,}")
check("و مانده هم", _ov["balance"] == _it["balance"],
      f"{_ov['balance']:,} · {_it['balance']:,}")

check("مبلغ همان چیزی است که دستی هم درمی‌آید",
      _it["due"] == 4 * 100_000,
      "۳ تمدیدِ کانفیگ قدیمی + ۱ ماه کانفیگ تازه")
check("پرداختیِ پیش از تسویه در داشبورد هم شمرده نمی‌شود",
      _ov["paid"] == 200_000, f"{_ov['paid']:,} — نه ۷۰۰٬۰۰۰")

head("کانفیگی که هرگز روشن نشد، روی هیچ‌کدام پول نمی‌گیرد")

_rows = {l["email"] for l in _iv["lines"]}
check("روی فاکتور ردیفی ندارد", "algn_never" not in _rows,
      "، ".join(sorted(_rows)))
check("و فاکتور می‌گوید چند تا و چرا",
      _it["unused"] == 1 and "هرگز به کار نیفتاده" in "".join(_it["unusedWhy"]),
      f"{_it['unused']} — {list(_it['unusedWhy'])}")
check("داشبورد از قبل همین را می‌گفت",
      _ov["skipped"] >= 1, f"{_ov['skipped']} کنار گذاشته شد")
check("کانفیگ تسویه‌شده جدا شمرده می‌شود، نه قاطیِ بی‌استفاده‌ها",
      _it["before"] == 1 and _it["beforeMonths"] == 3,
      f"{_it['before']} کانفیگ · {_it['beforeMonths']} ماه")
check("و داشبورد هم کنارش می‌گذارد",
      _ov.get("settledSkipped") == 1, str(_ov.get("settledSkipped")))

head("بدون تاریخِ تسویه، هر دو به کل عمر برمی‌گردند")

_b = sqlite3.connect(str(APP.BILLING_DB))
_b.execute("UPDATE group_config SET settled_until=NULL, period_start=NULL "
           "WHERE group_key='همسو'")
_b.commit()
_b.close()
_ov2 = {x["key"]: x for x in APP._billing_overview_impl()["groups"]}["همسو"]
_iv2 = APP.billing_invoice("همسو", x_admin_password="x")
check("و باز هم با هم می‌خوانند",
      _ov2["due"] == _iv2["totals"]["due"]
      and _ov2["paid"] == _iv2["totals"]["paid"],
      f"{_ov2['due']:,} · {_iv2['totals']['due']:,}")
check("عدد بزرگ‌تر شد، چون دیگر چیزی بریده نمی‌شود",
      _iv2["totals"]["due"] > _it["due"],
      f"{_iv2['totals']['due']:,} در برابر {_it['due']:,}")
check("پرداختیِ قدیمی هم برگشت",
      _ov2["paid"] == 700_000, f"{_ov2['paid']:,}")

check("هر دو صفحه از یک تابع حساب می‌کنند",
      "def _period_share(" in APP_SRC_NS
      and APP_SRC_NS.count("_period_share(") >= 3,
      "وگرنه دوباره از هم جدا می‌افتند")


# ═══════════════════════════════════════════════════════════
head("فهرست مرجع کاربران هم باید همان عدد را بدهد")

# داکstring این endpoint می‌گوید «نمای مرجع است … چقدر بدهکار است».
# سه جا با صورتحساب فرق داشت، و بدترینش این بود که مبلغ را
# months × price حساب می‌کرد — یعنی نرخ کاربر اضافه را کامل نادیده
# می‌گرفت. کانفیگ چهارکاربره روی این فهرست ۲۰۰٬۰۰۰ بود و روی فاکتور
# ۴۴۰٬۰۰۰.

_c = sqlite3.connect(XUI)
#            ایمیل       دستگاه فعال مصرف
for _id, _em, _ips, _en, _used in ((500, "dev_four", 4, 1, 5 * GB),
                                   (501, "dev_one", 1, 1, 5 * GB),
                                   (502, "dev_never", 1, 0, 0)):
    _cr = (_dtm.now() - _tdl(days=20)).isoformat(sep=" ", timespec="seconds")
    _ex = NOW_MS + 25 * 86400000
    _c.execute("INSERT INTO clients (id,email,group_name,total_gb,expiry_time,"
               "enable,created_at,limit_ip) VALUES (?,?,'دستگاه',0,?,?,?,?)",
               (_id, _em, _ex, _en, _cr, _ips))
    _c.execute("INSERT INTO client_traffics (id,email,up,down,expiry_time,enable)"
               " VALUES (?,?,0,?,?,?)", (_id, _em, _used, _ex, _en))
_c.commit()
_c.close()

_b = sqlite3.connect(str(APP.BILLING_DB))
_b.execute("INSERT OR REPLACE INTO group_config (group_key,label,billable,"
           "rates,period_days) VALUES ('دستگاه','دستگاه',1,?,30)",
           (_json.dumps([{"gb": 0, "price": 100000, "perDevice": 40000}]),))
_b.commit()
_b.close()
APP._billing_overview_impl()

_lst = {c["email"]: c for c in APP.billing_clients(x_admin_password="x")["clients"]}
_inv = APP.billing_invoice("دستگاه", x_admin_password="x")
_ovd = {x["key"]: x for x in APP._billing_overview_impl()["groups"]}["دستگاه"]

check("کانفیگ چهارکاربره نرخ کاربر اضافه را می‌گیرد",
      _lst["dev_four"]["amount"] == (100_000 + 40_000 * 3) * 2,
      f"{_lst['dev_four']['amount']:,} — قبلاً ۲۰۰٬۰۰۰ بود")
check("و ریزش هم گزارش می‌شود",
      _lst["dev_four"]["extraDevices"] == 3
      and _lst["dev_four"]["deviceAmount"] == 40_000 * 3 * 2,
      f"{_lst['dev_four']['extraDevices']} کاربر · "
      f"{_lst['dev_four']['deviceAmount']:,}")
check("تک‌کاربره دست‌نخورده می‌ماند",
      _lst["dev_one"]["amount"] == 200_000, f"{_lst['dev_one']['amount']:,}")
check("کانفیگی که هرگز روشن نشد صفر است",
      _lst["dev_never"]["amount"] == 0)
check("و می‌گوید چرا صفر است",
      "هرگز به کار نیفتاده" in (_lst["dev_never"]["amountWhy"] or ""),
      _lst["dev_never"]["amountWhy"])
check("ولی نرخش هنوز گزارش می‌شود",
      _lst["dev_never"]["price"] == 100_000,
      "فیلتر «بدون نرخ» نباید پر شود از ردیف‌هایی که نرخشان سالم است")

_sum = sum(c["amount"] for c in _lst.values() if c["group"] == "دستگاه")
check("جمع فهرست با فاکتور یکی است",
      _sum == _inv["totals"]["due"],
      f"فهرست {_sum:,} · فاکتور {_inv['totals']['due']:,}")
check("و با داشبورد هم", _ovd["due"] == _inv["totals"]["due"],
      f"داشبورد {_ovd['due']:,}")

head("«تمدید کرده؟» سوالِ نگه‌داشت است، نه سوالِ دوره")

# وقتی مبلغ دوره‌ای شد، اگر این فیلتر هم دوره‌ای می‌شد، مشتریِ دوساله
# روی گروهی با تاریخ تسویه‌ی نزدیک «هرگز تمدید نکرده» می‌شد.
# کانفیگی که همه‌ی تمدیدهایش در گذشته افتاده‌اند.
#
# ۷۵ روز عمر یعنی ۳ ماه: تمدیدها روی «ساخت + ۳۰» و «ساخت + ۶۰»
# می‌نشینند که هر دو پیش از امروزند. کانفیگی که عمرش به آینده کشیده،
# ماه‌های آینده‌اش هم همین حالا فروخته شده‌اند و درست است که حساب
# شوند — پس برای این آزمون به کار نمی‌آید.
_c = sqlite3.connect(XUI)
_cr = (_dtm.now() - _tdl(days=70)).isoformat(sep=" ", timespec="seconds")
_ex = NOW_MS + 5 * 86400000
_c.execute("INSERT INTO clients (id,email,group_name,total_gb,expiry_time,"
           "enable,created_at,limit_ip) VALUES (503,'dev_old','دستگاه',0,?,1,?,1)",
           (_ex, _cr))
_c.execute("INSERT INTO client_traffics (id,email,up,down,expiry_time,enable)"
           " VALUES (503,'dev_old',0,?,?,1)", (5 * GB, _ex))
_c.commit()
_c.close()
APP._billing_overview_impl()

_b = sqlite3.connect(str(APP.BILLING_DB))
_b.execute("UPDATE group_config SET settled_until=? WHERE group_key='دستگاه'",
           (_dtm.now().date().isoformat(),))
_b.commit()
_b.close()

_yes = APP.billing_clients(group="دستگاه", renewed="yes", x_admin_password="x")
_names = {c["email"] for c in _yes["clients"]}
check("مشتری با سابقه‌ی تمدید هنوز «تمدید کرده» است",
      "dev_old" in _names, "، ".join(sorted(_names)) or "هیچ‌کدام")

_all = {c["email"]: c
        for c in APP.billing_clients(group="دستگاه", x_admin_password="x")["clients"]}
check("ولی سهم دوره‌اش صفر است", _all["dev_old"]["renewals"] == 0,
      f"{_all['dev_old']['renewals']} در دوره · "
      f"{_all['dev_old']['totalRenewals']} در کل")
check("و مبلغش هم صفر، با دلیل",
      _all["dev_old"]["amount"] == 0
      and "تسویه" in (_all["dev_old"]["amountWhy"] or ""),
      _all["dev_old"]["amountWhy"])
check("ماه‌های آینده‌ی یک کانفیگ همین حالا فروخته شده‌اند",
      _all["dev_four"]["renewals"] == 1,
      "ساخته‌شده ۲۰ روز پیش با ۴۵ روز عمر — ماه دومش حساب می‌شود")

_b = sqlite3.connect(str(APP.BILLING_DB))
_b.execute("UPDATE group_config SET settled_until=NULL WHERE group_key='دستگاه'")
_b.commit()
_b.close()

check("هر سه صفحه از یک تابع حساب می‌کنند",
      APP_SRC_NS.count("_period_share(") >= 4
      and "months * price" not in APP_SRC_NS,
      "months × price نرخ کاربر اضافه را نادیده می‌گرفت")


# ═══════════════════════════════════════════════════════════
head("تمدید نماینده نباید دو بار شمرده شود")

# دو سازوکار موازی تمدید ثبت می‌کنند: پنل نمایندگی همان لحظه، و
# _detect_renewals که انقضا را به خاطر می‌سپارد و جلورفتنش را تمدید
# حساب می‌کند. ناظر برای تمدیدهایی است که مستقیم در x-ui زده می‌شوند
# — ولی تمدیدِ پنل هم انقضا را جلو می‌برد، پس هر دو همان یکی را ثبت
# می‌کردند: یک تمدید، دو ردیف، صورتحساب ۵۰٪ بیشتر.

_c = sqlite3.connect(XUI)
_cr = (_dtm.now() - _tdl(days=30)).isoformat(sep=" ", timespec="seconds")
_ex = NOW_MS + 5 * 86400000
_c.execute("INSERT INTO clients (id,email,group_name,total_gb,expiry_time,"
           "enable,created_at,limit_ip) VALUES (600,'dbl_1','دوبار',0,?,1,?,1)",
           (_ex, _cr))
_c.execute("INSERT INTO client_traffics (id,email,up,down,expiry_time,enable)"
           " VALUES (600,'dbl_1',0,?,?,1)", (3 * GB, _ex))
_c.commit()
_c.close()

_b = sqlite3.connect(str(APP.BILLING_DB))
_b.execute("INSERT OR REPLACE INTO group_config (group_key,label,billable,"
           "rates,period_days) VALUES ('دوبار','دوبار',1,?,30)",
           (_json.dumps([{"gb": 0, "price": 100000}]),))
_b.commit()
_b.close()


def _ren_rows(email):
    _q = sqlite3.connect(str(APP.BILLING_DB))
    try:
        return _q.execute("SELECT COUNT(*) FROM renewals WHERE email=?",
                          (email,)).fetchone()[0]
    finally:
        _q.close()


APP._billing_overview_impl()          # اولین دیدن: انقضا به خاطر سپرده می‌شود
check("در اولین دیدن تمدیدی ثبت نمی‌شود", _ren_rows("dbl_1") == 0)

# نماینده از پنل تمدید می‌کند: ثبت می‌شود و انقضای پنل جلو می‌رود
_NEW_EX = _ex + 30 * 86400000
APP._portal_log_renewal({"portal_group": "دوبار"}, "dbl_1", 1,
                        new_expiry_ms=_NEW_EX)
_c = sqlite3.connect(XUI)
_c.execute("UPDATE clients SET expiry_time=? WHERE email='dbl_1'", (_NEW_EX,))
_c.execute("UPDATE client_traffics SET expiry_time=? WHERE email='dbl_1'",
           (_NEW_EX,))
_c.commit()
_c.close()
check("پنل نمایندگی تمدید را ثبت می‌کند", _ren_rows("dbl_1") == 1)

APP._billing_overview_impl()          # ناظر حالا انقضای جلورفته را می‌بیند
check("و ناظرِ انقضا دوباره ثبتش نمی‌کند", _ren_rows("dbl_1") == 1,
      f"{_ren_rows('dbl_1')} ردیف برای یک تمدید")

_inv = APP.billing_invoice("دوبار", x_admin_password="x")
check("پس صورتحساب دو ماه است، نه سه",
      _inv["totals"]["months"] == 2 and _inv["totals"]["due"] == 200_000,
      f"{_inv['totals']['months']} ماه · {_inv['totals']['due']:,}")

head("و اگر ناظر زودتر رسیده باشد، پنل دوباره ثبت نمی‌کند")

# مسابقه‌ی باریک: نمای کلی درست بین تمدیدِ پنل و ثبتِ آن خوانده شود.
_c = sqlite3.connect(XUI)
_EX2 = _NEW_EX + 30 * 86400000
_c.execute("UPDATE clients SET expiry_time=? WHERE email='dbl_1'", (_EX2,))
_c.execute("UPDATE client_traffics SET expiry_time=? WHERE email='dbl_1'", (_EX2,))
_c.commit()
_c.close()
APP._billing_overview_impl()          # ناظر اول رسید
check("ناظر تمدید مستقیمِ x-ui را می‌گیرد", _ren_rows("dbl_1") == 2)

APP._portal_log_renewal({"portal_group": "دوبار"}, "dbl_1", 1,
                        new_expiry_ms=_EX2)
check("و ثبتِ دیرهنگامِ پنل ردیف تکراری نمی‌سازد",
      _ren_rows("dbl_1") == 2, f"{_ren_rows('dbl_1')} ردیف")

check("انقضای تازه به ثبت پاس داده می‌شود",
      "new_expiry_ms=new_exp" in APP_SRC_NS,
      "بدون این عدد، مبنای ناظر جلو نمی‌رود")


# ═══════════════════════════════════════════════════════════
head("سود از روز اول حساب می‌شود، نه از تاریخ تسویه")

# دفتر کل صریح می‌گوید «از روز اول»، و هزینه‌ها هم بدون هیچ برشی
# جمع می‌شوند. وقتی نمای کلی دوره‌ای شد، این صفحه هنوز همان کلیدها را
# می‌خواند: درآمدِ سه ماه در برابر هزینه‌ی دو سال.
#
# روی داده‌ی آزمایشی، «سود واقعی تا امروز» از +۵٬۰۰۰٬۰۰۰ به
# −۵٬۰۰۰٬۰۰۰ می‌پرید — فقط با ثبت یک تاریخ تسویه.

_c = sqlite3.connect(XUI)
for _i in range(700, 710):
    _cr = (_dtm.now() - _tdl(days=400)).isoformat(sep=" ", timespec="seconds")
    _ex = NOW_MS + 25 * 86400000
    _c.execute("INSERT INTO clients (id,email,group_name,total_gb,expiry_time,"
               "enable,created_at,limit_ip) VALUES (?,?,'سود',0,?,1,?,1)",
               (_i, "prof_%d" % _i, _ex, _cr))
    _c.execute("INSERT INTO client_traffics (id,email,up,down,expiry_time,enable)"
               " VALUES (?,?,0,?,?,1)", (_i, "prof_%d" % _i, 4 * GB, _ex))
_c.commit()
_c.close()

_b = sqlite3.connect(str(APP.BILLING_DB))
_b.execute("INSERT OR REPLACE INTO group_config (group_key,label,billable,"
           "rates,period_days) VALUES ('سود','سود',1,?,30)",
           (_json.dumps([{"gb": 0, "price": 100000}]),))
_b.execute("DELETE FROM payments WHERE group_key='سود'")
for _m in range(1, 14):
    _b.execute("INSERT INTO payments (group_key,amount,paid_at) VALUES ('سود',?,?)",
               (1_000_000,
                (_dtm.now() - _tdl(days=_m * 30)).date().isoformat()))
_b.commit()
_b.close()

_before = APP.billing_ledger(x_admin_password="x")
check("پولی که واقعاً گرفته شده، کامل شمرده می‌شود",
      _before["paid"] >= 13_000_000, f"{_before['paid']:,}")
_p0 = _before["profit"]

_b = sqlite3.connect(str(APP.BILLING_DB))
_b.execute("UPDATE group_config SET settled_until=? WHERE group_key='سود'",
           ((_dtm.now() - _tdl(days=90)).date().isoformat(),))
_b.commit()
_b.close()

_after = APP.billing_ledger(x_admin_password="x")
check("ثبت تاریخ تسویه سود را عوض نمی‌کند",
      _after["profit"] == _p0, f"{_p0:,} → {_after['profit']:,}")
check("و درآمدِ گرفته‌شده هم همان می‌ماند",
      _after["paid"] == _before["paid"],
      f"{_before['paid']:,} → {_after['paid']:,}")
check("و کل مبلغ صورتحساب‌شده هم",
      _after["billed"] == _before["billed"],
      f"{_before['billed']:,} → {_after['billed']:,}")
check("سود منفیِ ساختگی نمی‌شود", _after["profit"] > 0,
      f"{_after['profit']:,}")

# ولی «چه کسی الان بدهکار است» باید دوره‌ای باشد
_dbt = {d["key"]: d for d in _after["debtors"]}["سود"]
check("طلبِ امروز از دوره حساب می‌شود، نه از تاریخ",
      _dbt["due"] < _dbt["dueAll"],
      f"دوره {_dbt['due']:,} · کل {_dbt['dueAll']:,}")
check("و مانده‌ی صفحه‌ی بدهکاران با داشبورد یکی است",
      _after["outstanding"] == sum(
          d["balance"] for d in _after["debtors"]),
      f"{_after['outstanding']:,}")

check("چهار کارت بالای دفتر کل با هم جور درمی‌آیند",
      (_after["billed"] - _after["paid"]) - _after["outstanding"]
      == _after["settledGap"],
      f"اختلاف {_after['settledGap']:,} — همان دوره‌های تسویه‌شده")
check("و اختلاف صفر نیست، پس باید توضیح داده شود",
      _after["settledGap"] > 0,
      "بدون این خط، صفحه شبیه خرابی به نظر می‌رسد")
check("«اگر همه تسویه کنند» از طلبِ امروز حساب می‌شود",
      _after["profitIfAllPaid"]
      == _after["paid"] + _after["outstanding"] - _after["spent"],
      f"{_after['profitIfAllPaid']:,}")

check("نمای کلی هر دو عدد را می‌دهد",
      '"dueAll"' in APP_SRC_NS and '"paidAll"' in APP_SRC_NS,
      "یک پیمایش، دو جواب — نه دو بار خواندن x-ui")


# ═══════════════════════════════════════════════════════════
head("پول نماینده‌ی پیش‌پرداخت هم باید به حسابداری برسد")

# دو سیستم پول موازی بود و با هم حرف نمی‌زدند.
#
# نماینده‌ی بدهکاری آخر ماه پرداخت می‌کند و در `payments` می‌نشیند.
# نماینده‌ی پیش‌پرداخت *جلوتر* پول می‌دهد و آن پول فقط در `credit_tx`
# ثبت می‌شد — که هیچ صفحه‌ی حسابداری‌ای نمی‌خواندش.
#
# یعنی پولی که واقعاً گرفته شده در «دریافت‌شده» و «سود واقعی تا امروز»
# اصلاً نمی‌آمد، و نماینده‌ای که از قبل پولش را داده بود روی داشبورد
# بدهکار نشان داده می‌شد.

_c = sqlite3.connect(XUI)
for _i in range(800, 804):
    _cr = (_dtm.now() - _tdl(days=10)).isoformat(sep=" ", timespec="seconds")
    _ex = NOW_MS + 25 * 86400000
    _c.execute("INSERT INTO clients (id,email,group_name,total_gb,expiry_time,"
               "enable,created_at,limit_ip) VALUES (?,?,'پیش',0,?,1,?,1)",
               (_i, "pre_%d" % _i, _ex, _cr))
    _c.execute("INSERT INTO client_traffics (id,email,up,down,expiry_time,enable)"
               " VALUES (?,?,0,?,?,1)", (_i, "pre_%d" % _i, 3 * GB, _ex))
_c.commit()
_c.close()

_b = sqlite3.connect(str(APP.BILLING_DB))
_b.execute("INSERT OR REPLACE INTO group_config (group_key,label,billable,"
           "rates,period_days) VALUES ('پیش','پیش',1,?,30)",
           (_json.dumps([{"gb": 0, "price": 250000}]),))
_b.commit()
_b.close()

_tcon = APP._bot_rw()
try:
    _tcon.execute("CREATE TABLE IF NOT EXISTS tenants (id INTEGER PRIMARY KEY,"
                  " name TEXT, credit INTEGER DEFAULT 0, portal_group TEXT)")
    _tcon.execute("INSERT OR REPLACE INTO tenants (id,name,credit,portal_group)"
                  " VALUES (77,'رضا',0,'پیش')")
    _tcon.commit()
finally:
    _tcon.close()


def _paid_of(group):
    _q = sqlite3.connect(str(APP.BILLING_DB))
    try:
        return _q.execute("SELECT COALESCE(SUM(amount),0) FROM payments "
                          "WHERE group_key=?", (group,)).fetchone()[0]
    finally:
        _q.close()


check("پیش از شارژ، پرداختی ثبت نشده", _paid_of("پیش") == 0)

_res = APP.tenant_credit(77, {"amount": 2_000_000, "note": "کارت به کارت"},
                         x_admin_password="x")
check("شارژ اعتبار به‌عنوان پرداخت ثبت می‌شود",
      _paid_of("پیش") == 2_000_000, f"{_paid_of('پیش'):,}")
check("و پاسخ می‌گوید ثبت شده", _res.get("recorded") is True)

_ovp = {x["key"]: x for x in APP._billing_overview_impl()["groups"]}["پیش"]
check("داشبورد پول رسیده را می‌بیند", _ovp["paid"] == 2_000_000,
      f"{_ovp['paid']:,}")
check("و نماینده‌ای که جلوتر پول داده بدهکار نیست",
      _ovp["balance"] < 0,
      f"مانده {_ovp['balance']:,} — یعنی اعتبار، نه بدهی")

_lg = APP.billing_ledger(x_admin_password="x")
check("و سود، پولِ پیش‌پرداخت را هم می‌شمارد",
      _lg["paid"] >= 2_000_000, f"{_lg['paid']:,}")

head("مصرفِ اعتبار پولِ تازه نیست")

# شارژ لحظه‌ی رسیدن پول است؛ کسر بعدی فقط جابه‌جایی همان پول است.
_before = _paid_of("پیش")
APP._portal_charge({"id": 77, "credit": 2_000_000}, 250_000, "ساخت آزمایشی")
check("کسر از اعتبار پرداختِ تازه نمی‌سازد",
      _paid_of("پیش") == _before, f"{_paid_of('پیش'):,}")

head("نماینده‌ی بدون گروه، بی‌صدا رد نمی‌شود")

_tcon = APP._bot_rw()
try:
    _tcon.execute("INSERT OR REPLACE INTO tenants (id,name,credit,portal_group)"
                  " VALUES (78,'بی‌گروه',0,'')")
    _tcon.commit()
finally:
    _tcon.close()
_r2 = APP.tenant_credit(78, {"amount": 500_000}, x_admin_password="x")
check("پاسخ می‌گوید در حسابداری ثبت نشد", _r2.get("recorded") is False,
      "بدون گروه نمی‌شود فهمید پول بابت کدام واسطه است")


color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
