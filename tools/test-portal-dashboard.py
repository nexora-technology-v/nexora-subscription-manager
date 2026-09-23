#!/usr/bin/env python3
"""
داشبوردِ نماینده — و اینکه هر کس فقط مالِ خودش را ببیند.

برگه: docs/specs/2026-09-23-reseller-dashboard.md

تا وقتی فقط یک ربات بود، هیچ کوئریِ پنل شرطِ مستاجر نداشت و لازم هم
نبود. با آمدنِ رباتِ نماینده‌ها، کاربران و فروش و قیفِ پنلِ مالک همه‌ی
مستاجرها را با هم می‌شمردند. این تست روی اسکیمای **واقعیِ** ربات (نه
جدولِ دستی) می‌سنجد که:

  · مالک فقط کاربر و فروشِ خودش را می‌بیند
  · نماینده فقط مالِ خودش را — حتی وقتی یک نفر در هر دو ربات هست
  · تنظیماتِ ربات فهرستِ مجاز است
  · تستِ رایگانِ نماینده زیرِ سقفِ تستِ مالک است

اجرا:  python3 tools/test-portal-dashboard.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

TMP = tempfile.mkdtemp(prefix="portal_dash_")
os.environ.update(
    BOT_DB_PATH=os.path.join(TMP, "bot.db"), BOT_DB=os.path.join(TMP, "bot.db"),
    BILLING_DB=os.path.join(TMP, "billing.db"), NEXORA_ADMIN_PASSWORD="testpw",
    NEXORA_CONFIG=os.path.join(TMP, "config.json"))

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "bot"), str(ROOT / "backend")]

import db as DB                                          # noqa: E402
DB.DB_PATH = Path(os.environ["BOT_DB_PATH"])
DB.init_db()

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


def status_of(fn):
    """کدِ خطای HTTPException، یا ۲۰۰."""
    try:
        fn()
        return 200
    except Exception as e:          # noqa: BLE001
        return getattr(e, "status_code", 500)


# ── داده: مالک، دو نماینده، و یک نفر که در دو ربات هست ─────────────
OWNER = DB.create_tenant("owner", bot_token="1:root", panel_url="http://p",
                         settings={"brand": "Nexora"})
A = DB.create_tenant("shop-a", bot_token="2:a", parent_id=OWNER,
                     settings={"brand": "فروشگاه الف",
                               "cards": [{"number": "6037991122223333"}]})
B = DB.create_tenant("shop-b", bot_token="3:b", parent_id=OWNER, settings={})
with DB.conn() as c:
    c.execute("UPDATE tenants SET portal_slug='a', portal_group='ga', "
              "portal_enabled=1, bot_username='abot' WHERE id=?", (A,))
    c.execute("UPDATE tenants SET portal_slug='b', portal_group='gb', "
              "portal_enabled=1 WHERE id=?", (B,))

DO, DA, DBB = DB.TenantDB(OWNER), DB.TenantDB(A), DB.TenantDB(B)
o1 = DO.create_user(100, first_name="مشترک-مالک")     # همان آدم در دو ربات
o2 = DO.create_user(101, first_name="فقط-مالک")
a1 = DA.create_user(100, first_name="مشترک-الف")
a2 = DA.create_user(200, first_name="فقط-الف")
b1 = DBB.create_user(300, first_name="فقط-ب")

for d, tid, u, price in ((DO, OWNER, o1, 500000), (DA, A, a2, 70000)):
    d.exec("INSERT INTO plans (tenant_id,name,price,gb,days) VALUES (?,?,?,?,?)",
           (tid, "p", price, 10, 30))
    pid = d.plans()[0]["id"]
    oid = d.create_order(u["id"], pid, price, price)
    oid = oid["id"] if isinstance(oid, dict) else oid
    d.exec("UPDATE orders SET status='approved' WHERE tenant_id=? AND id=?", (tid, oid))

DO.chat_add(o1["id"], "user", "سلام مالک")
DA.chat_add(a2["id"], "user", "سلام الف")
DO.log("provision_failed", o1["id"], {"why": "x"})
DA.log("provision_failed", a2["id"], {"why": "y"})

import app as AP                                          # noqa: E402
AP.BOT_DB = Path(os.environ["BOT_DB_PATH"])

# تلگرامِ ساختگی: پاسخِ صندوق یک خبر در ربات هم می‌فرستد
_H = AP._bot_handlers()


class _FakeBot:
    def __init__(self, *a, **k):
        pass

    def send(self, *a, **k):
        return {"message_id": 1}


_H.Bot = _FakeBot
TA, TB = AP._tenant_row(A), AP._tenant_row(B)
# رمزِ داخلیِ خودِ بکند — این تست ورود را نمی‌سنجد
PW = AP._INTERNAL_PW

# ═══════════════════════════════════════════════════════════
head("پنلِ مالک فقط مالِ مالک")
# ═══════════════════════════════════════════════════════════
_u = AP.bot_users(x_admin_password=PW)
check("کاربرانِ مالک بدونِ مشتری‌های نماینده",
      sorted(x["tg_id"] for x in _u["users"]) == [100, 101],
      str(sorted(x["tg_id"] for x in _u["users"])))
check("و شمارشِ فیلترها هم", (_u.get("counts") or {}).get("all") == 2,
      str((_u.get("counts") or {}).get("all")))
_s = AP.bot_status(x_admin_password=PW)
check("وضعیت: کاربرانِ مالک", _s["stats"]["users"] == 2, _s["stats"]["users"])
check("وضعیت: فروشِ نماینده در فروشِ مالک نیست", _s["totalSales"] == 500000,
      _s["totalSales"])
_o = AP.bot_orders(status="all", x_admin_password=PW)
check("صفِ سفارش‌ها فقط مالِ مالک", len(_o["orders"]) == 1
      and _o["orders"][0]["tenant_id"] == OWNER)
_f = AP.bot_funnel(x_admin_password=PW)
check("قیفِ مالک", _f["started"] == 2, _f.get("started"))
_rep = AP.bot_users_report(days=30, x_admin_password=PW)
check("گزارش هم", (_rep.get("users") or {}).get("users") == 2
      and (_rep.get("orders") or {}).get("revenue") == 500000,
      f'{(_rep.get("users") or {}).get("users")} کاربر · '
      f'{(_rep.get("orders") or {}).get("revenue")} فروش')
_sd = AP.bot_subscriber_detail(100, x_admin_password=PW)
check("پرونده‌ی کسی که در دو ربات هست: ردیفِ مالک",
      _sd["user"]["tenant_id"] == OWNER and _sd["user"]["first_name"] == "مشترک-مالک")
_ib = AP.admin_inbox(x_admin_password=PW)
check("صندوقِ مالک", [t["tgId"] for t in _ib["threads"]] == [100])

# ═══════════════════════════════════════════════════════════
head("نماینده فقط مالِ خودش")
# ═══════════════════════════════════════════════════════════
_pu = AP.portal_users(t=TA)
check("کاربرانِ الف", sorted(x["tg_id"] for x in _pu["users"]) == [100, 200],
      str(sorted(x["tg_id"] for x in _pu["users"])))
check("کاربرانِ ب", [x["tg_id"] for x in AP.portal_users(t=TB)["users"]] == [300])
_ps = AP.portal_subscriber(100, t=TA)
check("پرونده‌ی همان آدم از پرتالِ الف: ردیفِ الف",
      _ps["user"]["tenant_id"] == A and _ps["user"]["first_name"] == "مشترک-الف")
check("مشتریِ مالک از پرتال دیده نمی‌شود",
      status_of(lambda: AP.portal_subscriber(101, t=TA)) == 404)
check("پیام به مشتریِ دیگران نمی‌رود",
      status_of(lambda: AP.portal_message(101, {"text": "x"}, t=TA)) == 404)
_pi = AP.portal_inbox(t=TA)
check("صندوقِ الف فقط گفتگوی خودش", [t["tgId"] for t in _pi["threads"]] == [200])
check("گفتگوی مشتریِ مالک از پرتال خالی است",
      AP.portal_inbox(user_id=o1["id"], t=TA)["messages"] == [])
check("پاسخ به مشتریِ دیگران رد می‌شود",
      status_of(lambda: AP.portal_inbox_send(
          {"userId": o1["id"], "body": "x"}, t=TA)) == 404)
_sent = AP.portal_inbox_send({"userId": a2["id"], "body": "جواب الف"}, t=TA)
check("پاسخ به مشتریِ خودش ثبت می‌شود", _sent.get("ok")
      and DA.chat_list(a2["id"])[-1]["body"] == "جواب الف")
check("و در صندوقِ مالک نمی‌آید",
      all(m["body"] != "جواب الف" for m in DO.chat_list(o1["id"])))
_pf = AP.portal_funnel(t=TA)
check("قیفِ الف", _pf["started"] == 2 and _pf["segments"]["paid"] == 1,
      f"{_pf.get('started')} / {_pf.get('segments')}")
_pe = AP.portal_events(t=TA)
check("رویدادهای الف فقط مالِ خودش",
      _pe["total"] == 1 and _pe["events"][0]["name"] == "فقط-الف",
      f"{_pe.get('total')}")

# ═══════════════════════════════════════════════════════════
head("تنظیماتِ ربات — فهرستِ مجاز")
# ═══════════════════════════════════════════════════════════
AP.portal_bot_settings_save({"settings": {
    "welcome_text": "سلام {name}", "order_ttl_minutes": 60,
    "reminders": {"enabled": True, "days": [5, 2, 1], "traffic_pct": 90},
    "coins": {"per_referral": 15, "tiers": [{"coins": 30, "percent": 15}]},
    # اینها مالِ نماینده نیستند
    "email_prefix": "hack", "miniapp_url": "https://evil.example",
    "sub_base_url": "https://evil.example", "cards": [], "brand": "دزد",
}}, t=TA)
_st = AP._tenant_settings(AP._tenant_row(A))
check("متن و مهلت ذخیره شد",
      _st.get("welcome_text") == "سلام {name}" and _st.get("order_ttl_minutes") == 60)
check("یادآوری و سکه با شکلِ درست",
      _st["reminders"]["days"] == [5, 2, 1] and _st["coins"]["per_referral"] == 15
      and _st["coins"]["tiers"] == [{"coins": 30, "percent": 15}])
check("کلیدِ خارج از فهرست ننشست",
      "email_prefix" not in _st and "miniapp_url" not in _st
      and "sub_base_url" not in _st)
check("و چیزی که بود پاک نشد", _st.get("cards")
      and _st.get("brand") == "فروشگاه الف", "ادغام، نه جایگزینی")
check("عددِ خارج از بازه رد می‌شود و بی‌صدا عوض نمی‌شود",
      status_of(lambda: AP.portal_bot_settings_save(
          {"settings": {"order_ttl_minutes": 2}}, t=TA)) == 400)
_g = AP.portal_bot_settings(t=TA)
check("خواندن فقط کلیدهای مجاز را می‌دهد",
      "cards" not in _g["settings"] and _g["settings"]["brand"] == "فروشگاه الف")

# ═══════════════════════════════════════════════════════════
head("تستِ رایگانِ نماینده — زیرِ سقفِ مالک")
# ═══════════════════════════════════════════════════════════


def save_trial(gb, days=1, ips=1, extra=()):
    rows = [{"name": "تست", "gb": gb, "days": days, "ip_limit": ips,
             "price": 99000, "is_trial": True}] + list(extra)
    return AP.portal_bot_plans_save({"plans": rows}, t=AP._tenant_row(A))


check("مالک تست ندارد: تستِ نماینده ذخیره نمی‌شود",
      status_of(lambda: save_trial(1)) == 400)
check("و پرتال همین را می‌گوید", AP.portal_bot_settings(t=TA)["trialCap"] is None
      and "مالک" in AP.portal_bot_settings(t=TA)["trialWhy"])

DO.exec("INSERT INTO plans (tenant_id,name,price,gb,days,ip_limit,is_trial,is_active) "
        "VALUES (?,?,?,?,?,?,1,1)", (OWNER, "تست مالک", 0, 2, 1, 1))
check("زیرِ سقف ذخیره می‌شود", status_of(lambda: save_trial(1)) == 200)
_tp = DA.q("SELECT * FROM plans WHERE tenant_id=? AND is_trial=1", (A,), one=True)
check("با قیمتِ صفر، هر چه فرستاده شده باشد", _tp and _tp["price"] == 0,
      _tp and _tp["price"])
check("بزرگ‌تر از سقف ذخیره نمی‌شود", status_of(lambda: save_trial(5)) == 400)
check("نامحدود وقتی سقف محدود است هم نه", status_of(lambda: save_trial(0)) == 400)
check("دو تست نه",
      status_of(lambda: save_trial(1, extra=[{"name": "تست۲", "gb": 1, "days": 1,
                                             "ip_limit": 1, "is_trial": True}])) == 400)
check("سقف در پاسخِ پلن‌ها هم هست",
      (AP.portal_bot_plans(t=TA).get("trialCap") or {}).get("gb") == 2)

# ═══════════════════════════════════════════════════════════
head("نسخه")
# ═══════════════════════════════════════════════════════════
_me = AP.portal_me(t=TA)
check("پرتال نسخه‌ی نصب‌شده را می‌گوید",
      _me.get("version") == (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
      _me.get("version"))

print(f"\n  {G if not _fail else R}{_ok} پاس{X}"
      + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
sys.exit(1 if _fail else 0)
