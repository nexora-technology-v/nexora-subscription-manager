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


print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
