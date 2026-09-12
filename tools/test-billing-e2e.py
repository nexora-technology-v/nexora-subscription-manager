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


print(f"\n{D}{'─' * 50}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
