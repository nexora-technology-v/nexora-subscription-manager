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
  · تستِ رایگانِ نماینده عددهای مالک را می‌گیرد، نه عددهای خودش
  · کفِ حجمی: حجم × نرخِ هر گیگ
  · «ببند» مالک حتی با قیمتِ صفر می‌بندد

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
head("تستِ رایگانِ نماینده — عددها را مالک تعیین می‌کند")
# ═══════════════════════════════════════════════════════════


def save_trial(gb, days=1, ips=1, extra=()):
    rows = [{"name": "تست", "gb": gb, "days": days, "ip_limit": ips,
             "price": 99000, "is_trial": True}] + list(extra)
    return AP.portal_bot_plans_save({"plans": rows}, t=AP._tenant_row(A))


check("مالک تست ندارد: تستِ نماینده ذخیره نمی‌شود",
      status_of(lambda: save_trial(1)) == 400)
check("و پرتال همین را می‌گوید", AP.portal_bot_settings(t=TA)["trialCap"] is None
      and "مدیر" in AP.portal_bot_settings(t=TA)["trialWhy"])

DO.exec("INSERT INTO plans (tenant_id,name,price,gb,days,ip_limit,is_trial,is_active) "
        "VALUES (?,?,?,?,?,?,1,1)", (OWNER, "تست مالک", 0, 2, 1, 1))
check("تست ذخیره می‌شود", status_of(lambda: save_trial(1)) == 200)
_tp = DA.q("SELECT * FROM plans WHERE tenant_id=? AND is_trial=1", (A,), one=True)
check("با قیمتِ صفر، هر چه فرستاده شده باشد", _tp and _tp["price"] == 0,
      _tp and _tp["price"])
check("و با حجمِ مالک (۲)، نه عددِ نماینده (۱)", _tp and _tp["gb"] == 2, _tp and _tp["gb"])
check("۵۰ گیگ فرستاد: ۲ گیگ نشست (مالک: «ممکن است حجمِ زیاد بگذارد»)",
      status_of(lambda: save_trial(50, days=30, ips=5)) == 200
      and DA.q("SELECT gb, days, ip_limit FROM plans WHERE tenant_id=? AND is_trial=1",
               (A,), one=True) == {"gb": 2, "days": 1, "ip_limit": 1})
check("نامحدود فرستاد: باز هم ۲ گیگ",
      status_of(lambda: save_trial(0)) == 200
      and DA.q("SELECT gb FROM plans WHERE tenant_id=? AND is_trial=1", (A,), one=True)["gb"] == 2)
check("دو تست نه",
      status_of(lambda: save_trial(1, extra=[{"name": "تست۲", "gb": 1, "days": 1,
                                             "ip_limit": 1, "is_trial": True}])) == 400)
check("سقف در پاسخِ پلن‌ها هم هست",
      (AP.portal_bot_plans(t=TA).get("trialCap") or {}).get("gb") == 2)

# تنظیمِ جدای مالک برای نماینده‌ها — بر تستِ خودش مقدم، و همان لحظه روی ردیف‌ها
_g0 = AP.reseller_trial_get(x_admin_password=PW)
check("پیش از تنظیم: تستِ خودِ مالک ملاک است (source=own)",
      _g0["source"] == "own" and _g0["gb"] == 2, str(_g0))
check("حجمِ صفر (نامحدود) برای تست رد می‌شود",
      status_of(lambda: AP.reseller_trial_set(
          {"enabled": True, "gb": 0, "days": 1, "ip_limit": 1}, x_admin_password=PW)) == 400)
_s1 = AP.reseller_trial_set({"enabled": True, "gb": 3, "days": 2, "ip_limit": 1},
                            x_admin_password=PW)
check("ذخیره: روی ردیفِ تستِ نماینده‌ها نشست",
      _s1["synced"] >= 1 and DA.q("SELECT gb, days FROM plans WHERE tenant_id=? AND is_trial=1",
                                  (A,), one=True) == {"gb": 3, "days": 2}, str(_s1))
check("ردیفِ تستِ خودِ مالک دست نخورد",
      DO.q("SELECT gb FROM plans WHERE tenant_id=? AND is_trial=1", (OWNER,), one=True)["gb"] == 2)
check("پرتال عددِ تازه را می‌بیند",
      (AP.portal_bot_plans(t=AP._tenant_row(A)).get("trialCap") or {}).get("gb") == 3)
AP.reseller_trial_set({"enabled": False, "gb": 3, "days": 2, "ip_limit": 1}, x_admin_password=PW)
check("خاموش: پرتال «ممکن نیست» می‌گوید", AP.portal_bot_plans(t=AP._tenant_row(A))["trialCap"] is None)
check("و ردیفِ تستِ نماینده غیرفعال شد، نه پاک",
      DA.q("SELECT is_active FROM plans WHERE tenant_id=? AND is_trial=1", (A,), one=True)
      == {"is_active": 0})
check("و ذخیره‌ی تستِ تازه رد می‌شود", status_of(lambda: save_trial(1)) == 400)
AP.reseller_trial_set({"enabled": True, "gb": 3, "days": 2, "ip_limit": 1}, x_admin_password=PW)
check("روشنِ دوباره: همان ردیف برمی‌گردد",
      DA.q("SELECT is_active, gb FROM plans WHERE tenant_id=? AND is_trial=1", (A,), one=True)
      == {"is_active": 1, "gb": 3})

# ═══════════════════════════════════════════════════════════
head("کفِ قیمت با نرخِ حجمی — حجم × نرخِ هر گیگ")
# ═══════════════════════════════════════════════════════════
# مالک: «اگر گیگی ۳ هزار است، ۳۰ گیگ کفش می‌شود ۹۰». تا ۱.۱۱۴ گروهی که فقط
# نرخِ حجمی داشت اصلاً کفی نداشت و هر قیمتی، حتی صفر، ذخیره می‌شد.
_bc = AP._billing_conn()
_bc.execute("INSERT OR REPLACE INTO group_config (group_key, label, billable, rates, per_gb) "
            "VALUES ('ga','الف',1,'[]',3000)")
_bc.commit()
_bc.close()
_TA3 = AP._tenant_row(A)
_fl = AP.portal_plan_cost({"rows": [{"gb": 30, "days": 30, "ip_limit": 2},
                                    {"gb": 30, "days": 90, "ip_limit": 4},
                                    {"gb": 0, "days": 30, "ip_limit": 1}]}, t=_TA3)["rows"]
check("۳۰ گیگ × ۳٬۰۰۰ = ۹۰٬۰۰۰", _fl[0].get("ready") and _fl[0]["cost"] == 90000, str(_fl[0]))
check("ماه و کاربر ضرب نمی‌شوند — حجم سقفِ کلِ دوره است",
      _fl[1].get("cost") == 90000, str(_fl[1]))
# مالک: «نامحدودی که ما تعریف می‌کنیم ۲۰۰ گیگ است»
check("نامحدود = ۲۰۰ گیگ → ۶۰۰٬۰۰۰",
      _fl[2].get("ready") and _fl[2]["cost"] == 600000 and _fl[2]["unlimited"], str(_fl[2]))
check("عددِ نامحدود را مالک عوض می‌کند (۱۰ گیگ کمتر از حد رد می‌شود)",
      status_of(lambda: AP.reseller_unlimited_set({"gb": 5}, x_admin_password=PW)) == 400)
AP.reseller_unlimited_set({"gb": 300}, x_admin_password=PW)
check("۳۰۰ گیگ → ۹۰۰٬۰۰۰",
      AP.portal_plan_cost({"rows": [{"gb": 0, "days": 30}]}, t=_TA3)["rows"][0]["cost"] == 900000)
AP.reseller_unlimited_set({"gb": 200}, x_admin_password=PW)


def _save_plan(price, gb=30):
    return AP.portal_bot_plans_save({"plans": [
        {"name": "سی", "gb": gb, "days": 30, "ip_limit": 2, "price": price}]}, t=_TA3)


check("۸۹٬۰۰۰ ذخیره نمی‌شود", status_of(lambda: _save_plan(89000)) == 400)
check("صفر هم نه", status_of(lambda: _save_plan(0)) == 400)
check("۹۰٬۰۰۰ ذخیره می‌شود", status_of(lambda: _save_plan(90000)) == 200)
check("و کف در plans.cost نشست (همان که از اعتبارِ پیش‌پرداخت کم می‌شود)",
      DA.q("SELECT cost FROM plans WHERE tenant_id=? AND gb=30", (A,), one=True)["cost"] == 90000)
_bc = AP._billing_conn()
_bc.execute("UPDATE group_config SET per_gb=4000 WHERE group_key='ga'")
_bc.commit()
_bc.close()
AP._refresh_plan_costs("ga")
check("نرخ عوض شد: کفِ ذخیره‌شده هم (۱۲۰٬۰۰۰)",
      DA.q("SELECT cost FROM plans WHERE tenant_id=? AND gb=30", (A,), one=True)["cost"] == 120000)
_bc = AP._billing_conn()
_bc.execute("DELETE FROM group_config WHERE group_key='ga'")
_bc.commit()
_bc.close()

# ═══════════════════════════════════════════════════════════
head("قابلیت‌ها: «ببند» مالک حتی با قیمتِ صفر")
# ═══════════════════════════════════════════════════════════
# مالک: «دکمه‌های باز و بسته‌اش اصلاً کار نمی‌کند». با قیمتِ صفر فقط تاریخ
# پاک می‌شد و تاریخ آن‌جا خوانده نمی‌شد.
_st0 = AP._tenant_settings(AP._tenant_row(OWNER))
_st0["store_addon"] = {"price": 0, "days": 30}
AP._save_tenant_settings(OWNER, _st0)
check("قیمتِ صفر: باز", AP._addon_open(AP._tenant_row(A), "store"))
AP.store_addon_grant({"tenant": A, "days": 0}, x_admin_password=PW)
check("ببند: بسته شد، با وجودِ قیمتِ صفر", not AP._addon_open(AP._tenant_row(A), "store"))
_rows = {r["id"]: r for r in AP.store_addon_get(x_admin_password=PW)["resellers"]}
check("فهرست «بسته به‌دستِ مالک» را جدا می‌گوید", _rows[A]["blocked"] and not _rows[A]["open"])
check("فروشگاهِ دیگر دست نخورد", _rows[B]["open"] and not _rows[B]["blocked"])
check("ربات هم نمی‌فروشد (همان core.addon_open)",
      _H.store_gate(type("C", (), {"tenant": AP._tenant_row(A),
                                    "s": AP._tenant_settings(AP._tenant_row(A))})()) is not None)
_st0["store_addon"] = {"price": 100000, "days": 30}
AP._save_tenant_settings(OWNER, _st0)
check("نماینده‌ی بسته با پولِ خودش بازش نمی‌کند (۴۰۳)",
      status_of(lambda: AP.portal_store_buy(t=AP._tenant_row(A))) == 403)
_st0["store_addon"] = {"price": 0, "days": 30}
AP._save_tenant_settings(OWNER, _st0)
AP.store_addon_grant({"tenant": A, "days": 30}, x_admin_password=PW)
check("باز کن: دوباره باز", AP._addon_open(AP._tenant_row(A), "store")
      and not AP._addon_blocked(AP._tenant_row(A), "store"))
check("و با قیمتِ صفر تاریخِ گمراه‌کننده نمی‌گذارد", AP._addon_until(AP._tenant_row(A), "store") == "")

# ═══════════════════════════════════════════════════════════
head("استودیوی پوسته — قالب × پالت × سبکِ لوگو")
# ═══════════════════════════════════════════════════════════
# برگه: docs/specs/2026-09-23-mini-theme-studio.md

def _owner_addon(price):
    st = AP._tenant_settings(AP._tenant_row(OWNER))
    st["portal_addon"] = {"price": price, "days": 30}
    AP._save_tenant_settings(OWNER, st)


_owner_addon(250000)                         # پولی، و نماینده نخریده
check("بدونِ اشتراک، ذخیره‌ی پوسته قفل است (در بکند)",
      status_of(lambda: AP.portal_theme_set({"tpl": "bold"}, t=AP._tenant_row(A))) == 402)
check("و مینی‌اپ پیش‌فرض را نشان می‌دهد",
      AP._mini_theme(AP._tenant_row(A))["tpl"] == "aurora")

_owner_addon(0)                              # رایگان برای همه
TA2 = AP._tenant_row(A)
check("قالبِ ناشناخته رد می‌شود",
      status_of(lambda: AP.portal_theme_set({"tpl": "hacker"}, t=TA2)) == 400)
check("پالتِ ناشناخته رد می‌شود",
      status_of(lambda: AP.portal_theme_set({"palette": "neon-green"}, t=TA2)) == 400)
check("رنگِ دلخواه بدونِ رنگ رد می‌شود",
      status_of(lambda: AP.portal_theme_set({"palette": "custom"}, t=TA2)) == 400)

AP.portal_theme_set({"tpl": "bold", "palette": "sunset",
                     "logo_style": {"shape": "circle", "bg": "evil", "pad": 99}}, t=TA2)
_mt = AP._mini_theme(AP._tenant_row(A))
check("قالب و پالت ذخیره شدند", _mt["tpl"] == "bold" and _mt["palette"] == "sunset", str(_mt))
check("سبکِ لوگو پاک‌سازی شد (زمینه‌ی ناشناخته → پیش‌فرض، فاصله ≤ ۲۴)",
      _mt["logoStyle"] == {"shape": "circle", "bg": "none", "pad": 24}, str(_mt["logoStyle"]))

AP.portal_theme_set({"accent": "#e84393"}, t=AP._tenant_row(A))
_mt2 = AP._mini_theme(AP._tenant_row(A))
check("ذخیره‌ی جزئی بقیه را پاک نمی‌کند",
      _mt2["tpl"] == "bold" and _mt2["palette"] == "sunset"
      and _mt2["logoStyle"]["shape"] == "circle", str(_mt2))
AP.portal_theme_set({"palette": "custom"}, t=AP._tenant_row(A))
check("رنگِ دلخواه با رنگِ ذخیره‌شده پذیرفته می‌شود",
      AP._mini_theme(AP._tenant_row(A))["palette"] == "custom")

_g2 = AP.portal_theme_get(t=AP._tenant_row(A))
check("پرتال همان را برمی‌گرداند", _g2["tpl"] == "bold" and _g2["palette"] == "custom"
      and _g2["logoStyle"]["shape"] == "circle")

_owner_addon(250000)                         # اشتراک تمام شد
_mt3 = AP._mini_theme(AP._tenant_row(A))
check("اشتراک که تمام شد مینی‌اپ پیش‌فرض می‌شود — بی‌آنکه پاک شود",
      _mt3["tpl"] == "aurora" and _mt3["palette"] == ""
      and AP.portal_theme_get(t=AP._tenant_row(A))["tpl"] == "bold")
_owner_addon(0)

# برابری با رابط — شناسه‌ای که یک طرف نمی‌شناسد، بی‌صدا پیش‌فرض می‌شود
_JS = (ROOT / "frontend" / "src" / "lib" / "mini-themes.js").read_text(encoding="utf-8")
import re as _re                                         # noqa: E402
_js_tpls = _re.findall(r'\{ id: "([a-z]+)", fa:', _JS.split("export const MINI_PALETTES")[0])
_js_pals = _re.findall(r'\{ id: "([a-z]+)", fa:[^}]*accent:', _JS)
check("قالب‌های بکند و رابط یکی‌اند", tuple(_js_tpls) == AP.MINI_TEMPLATES,
      f"{_js_tpls} / {AP.MINI_TEMPLATES}")
check("پالت‌های بکند و رابط یکی‌اند", tuple(_js_pals) + ("custom",) == AP.MINI_PALETTES,
      f"{_js_pals}")
_SL = (ROOT / "frontend" / "src" / "lib" / "shoplogo.jsx").read_text(encoding="utf-8")
check("شکل‌ها و زمینه‌های لوگو یکی‌اند",
      tuple(_re.findall(r'\{ id: "([a-z]+)", fa: "[^"]+" \}', _SL.split("LOGO_BGS")[0])) == AP.LOGO_SHAPES
      and tuple(_re.findall(r'\{ id: "([a-z]+)", fa: "[^"]+" \}', _SL.split("LOGO_BGS")[1].split("];")[0])) == AP.LOGO_BGS)

# سبکِ صفحه‌ی ورود: سه فهرست — بکند، mini-themes.js، و mark.jsx (که عمداً
# به هیچ ماژولی وابسته نیست و فهرستِ خودش را دارد). شناسه‌ای که یکی
# نشناسد، بی‌صدا «نوار» می‌شد و انتخابِ نماینده دیده نمی‌شد.
_js_spl = _re.findall(r'\{ id: "([a-z]+)", fa:',
                      _JS.split("export const MINI_SPLASHES")[1].split("];")[0])
_MK = (ROOT / "frontend" / "src" / "lib" / "mark.jsx").read_text(encoding="utf-8")
_mk_spl = _re.findall(r'"([a-z]+)"', _MK.split("const SPLASH_IDS = [")[1].split("]")[0])
check("سبک‌های صفحه‌ی ورود در بکند، رابط و اسپلش یکی‌اند",
      tuple(_js_spl) == AP.MINI_SPLASHES == tuple(_mk_spl),
      f"{_js_spl} / {_mk_spl} / {AP.MINI_SPLASHES}")

_owner_addon(0)
AP.portal_theme_set({"splash": "pulse"}, t=AP._tenant_row(A))
check("سبکِ صفحه‌ی ورود ذخیره و به مینی‌اپ داده می‌شود",
      AP._mini_theme(AP._tenant_row(A))["splash"] == "pulse"
      and AP.portal_theme_get(t=AP._tenant_row(A))["splash"] == "pulse")
check("سبکِ ناشناخته ۴۰۰ است، نه «نوار»ِ بی‌صدا",
      status_of(lambda: AP.portal_theme_set({"splash": "fireworks"}, t=AP._tenant_row(A))) == 400)
_owner_addon(250000)
check("پوسته که قفل شد، صفحه‌ی ورود هم پیش‌فرض می‌شود",
      AP._mini_theme(AP._tenant_row(A))["splash"] == "bar")
_owner_addon(0)

# ═══════════════════════════════════════════════════════════
head("اشتراکِ فروشگاه — ربات و مینی‌اپِ نماینده")
# ═══════════════════════════════════════════════════════════
# برگه: docs/specs/2026-09-26-reseller-store-subscription.md
# خودِ دروازه‌ی فروش را bot/test_reseller می‌سنجد؛ این‌جا خرید و وضعیت.


def _store_price(price):
    st = AP._tenant_settings(AP._tenant_row(OWNER))
    st["store_addon"] = {"price": price, "days": 30}
    AP._save_tenant_settings(OWNER, st)


_store_price(0)
check("قیمتِ صفر: همه باز — آپدیت فروشِ کسی را نمی‌بندد",
      AP.portal_store_get(t=AP._tenant_row(A))["open"] is True)
check("قیمتِ صفر: خرید معنی ندارد (۴۰۰)",
      status_of(lambda: AP.portal_store_buy(t=AP._tenant_row(A))) == 400)
check("قیمتِ پوسته روی فروشگاه اثر ندارد (دو افزونه‌ی جدا)",
      (_owner_addon(999000) or True) and AP._addon_open(AP._tenant_row(A), "store"))
_owner_addon(0)

_store_price(300000)
with DB.conn() as c:
    c.execute("UPDATE tenants SET credit=? WHERE id=?", (1000000, A))
_sa = AP.portal_store_get(t=AP._tenant_row(A))
check("قیمت گذاشته شد: بسته", _sa["open"] is False and _sa["price"] == 300000, str(_sa))
check("مینی‌اپ هم می‌داند", AP.mini_me(tu=(AP._tenant_row(A), {"id": 1, "tg_id": 1}))
      .get("storeOpen") is False if hasattr(AP, "mini_me") else True)
_bought = AP.portal_store_buy(t=AP._tenant_row(A))
check("خرید: اعتبار کم شد و باز شد",
      int(AP._tenant_row(A)["credit"]) == 700000
      and AP.portal_store_get(t=AP._tenant_row(A))["open"] is True, str(_bought))
_u1 = AP._addon_until(AP._tenant_row(A), "store")
AP.portal_store_buy(t=AP._tenant_row(A))
_u2 = AP._addon_until(AP._tenant_row(A), "store")
from datetime import datetime as _dtt                    # noqa: E402
check("تمدیدِ زودهنگام روزهای مانده را نمی‌سوزاند",
      (_dtt.fromisoformat(_u2) - _dtt.fromisoformat(_u1)).days == 30, f"{_u1} → {_u2}")

with DB.conn() as c:
    c.execute("UPDATE tenants SET credit=? WHERE id=?", (1000, A))
check("اعتبارِ ناکافی: ۴۰۲ و تاریخ عوض نمی‌شود",
      status_of(lambda: AP.portal_store_buy(t=AP._tenant_row(A))) == 402
      and AP._addon_until(AP._tenant_row(A), "store") == _u2)

check("فروشگاهِ مالک هرگز بسته نیست",
      AP._addon_open(AP._tenant_row(OWNER), "store") is True)

AP._addon_admin_grant("store", {"tenant": B, "days": 10})
check("بازکردنِ دستیِ مالک", AP._addon_open(AP._tenant_row(B), "store") is True)
AP._addon_admin_grant("store", {"tenant": B, "days": 0})
check("و بستنش", AP._addon_open(AP._tenant_row(B), "store") is False)
check("مالک را نمی‌شود «باز کرد» — ردیفِ خودش است",
      status_of(lambda: AP._addon_admin_grant("store", {"tenant": OWNER, "days": 5})) == 400)
_store_price(0)

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
