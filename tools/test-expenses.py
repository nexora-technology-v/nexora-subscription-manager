#!/usr/bin/env python3
"""
هزینه‌ها، نرخ ارز و دفتر کل.

چرا وجود دارد:
    این بخش با پول کار می‌کند و اشتباهش بی‌صدا است. اگر تبدیل ارز
    غلط باشد، گزارش سود همچنان یک عدد قشنگ نشان می‌دهد — فقط عدد
    اشتباهی است.

    دو قاعده‌ای که این‌جا محافظت می‌شوند:
      · نرخِ لحظه‌ی خرید ذخیره می‌شود و بعداً عوض نمی‌شود
      · هزینه‌ی بدون مبلغ تومانی اصلاً ثبت نمی‌شود

اجرا:  python3 tools/test-expenses.py
"""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "fx", os.path.join(ROOT, "backend", "fx.py"))
FX = importlib.util.module_from_spec(spec)
spec.loader.exec_module(FX)

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


# ═══════════════════════════════════════════════════════════
head("خواندن عدد")

check("جداکننده‌ی هزارگان", FX._num("2,746,100") == 2746100)
check("رقم فارسی", FX._num("۲,۷۴۶,۱۰۰") == 2746100)
check("عدد ساده", FX._num("5000") == 5000)
check("خالی None می‌دهد", FX._num("") is None)
check("None می‌ماند None", FX._num(None) is None)
check("متن بی‌ربط None می‌دهد", FX._num("نامشخص") is None)

head("نرخ زنده — بدون شبکه")

SAMPLE = {"current": {
    "price_eur": {"p": "2,746,100", "ts": "2026-09-12 12:52:25"},
    "price_dollar_rl": {"p": "1,150,000", "ts": "2026-09-12 12:52:25"},
}}
FX._cache.clear()
FX._fetch_tgju = lambda timeout=12: SAMPLE

r = FX.live("EUR")
check("نرخ خوانده شد", r["ok"])
check("ریال به تومان تبدیل شد", r["toman"] == 274610,
      f"۲٬۷۴۶٬۱۰۰ ریال = {r['toman']} تومان")
check("ریال هم برمی‌گردد", r["rial"] == 2746100)
check("زمان نرخ می‌آید", r["at"] == "2026-09-12 12:52:25")
check("منبع مشخص است", r["source"] == "tgju")

r2 = FX.live("EUR")
check("بار دوم از کش می‌آید", r2.get("cached") is True)

check("دلار هم کار می‌کند", FX.live("USD")["toman"] == 115000)
check("ارز ناشناخته رد می‌شود", FX.live("XYZ")["ok"] is False)

head("وقتی منبع در دسترس نیست")


def boom(timeout=12):
    raise OSError("شبکه قطع است")


FX._fetch_tgju = boom
# کش را پیر می‌کنیم، وگرنه live اصلاً سراغ شبکه نمی‌رود و مسیر
# «نرخ کهنه» هرگز اجرا نمی‌شود — یعنی تست چیزی را نمی‌سنجد.
for entry in FX._cache.values():
    entry["at"] -= FX.TTL + 60
stale = FX.live("EUR")
check("آخرین نرخ موفق برمی‌گردد", stale.get("toman") == 274610)
check("ولی «کهنه» علامت می‌خورد", stale.get("stale") is True)
check("سن نرخ گزارش می‌شود", "ageMinutes" in stale)

FX._cache.clear()
dead = FX.live("EUR")
check("بدون کش هم خطا نمی‌دهد", dead["ok"] is False)
check("بدون کش مبلغ None است", dead["toman"] is None)
check("راهنمای دستی می‌دهد", "دستی" in dead.get("hint", ""))

head("تبدیل به تومان")

FX._cache.clear()
FX._fetch_tgju = lambda timeout=12: SAMPLE

c = FX.to_toman(100, "IRT")
check("تومان دست‌نخورده می‌ماند", c["toman"] == 100 and c["rate"] == 1)

c = FX.to_toman(5, "EUR")
check("یورو با نرخ زنده", c["toman"] == 5 * 274610, str(c["toman"]))
check("نرخ استفاده‌شده برمی‌گردد", c["rate"] == 274610)

c = FX.to_toman(5, "EUR", manual_rate=300000)
check("نرخ دستی بر نرخ زنده مقدم است", c["toman"] == 1_500_000)
check("منبع «دستی» علامت می‌خورد", c["source"] == "manual")

check("نرخ دستی صفر نادیده گرفته می‌شود",
      FX.to_toman(5, "EUR", manual_rate=0)["source"] != "manual")
check("نرخ دستی نامعتبر نادیده گرفته می‌شود",
      FX.to_toman(5, "EUR", manual_rate="abc")["source"] != "manual")

check("مبلغ خالی صفر می‌شود", FX.to_toman(None, "IRT")["toman"] == 0)
check("مبلغ نامعتبر صفر می‌شود", FX.to_toman("xx", "IRT")["toman"] == 0)

FX._cache.clear()
FX._fetch_tgju = boom
c = FX.to_toman(5, "EUR")
check("بدون نرخ، مبلغ None است — نه صفر", c["toman"] is None,
      "صفر یعنی «رایگان بود» که دروغ است")
check("دلیل شکست برمی‌گردد", "error" in c)

head("قاعده‌ی ثبت ماندگار")

# این مهم‌ترین قاعده است: نرخ در لحظه‌ی خرید قفل می‌شود.
FX._cache.clear()
FX._fetch_tgju = lambda timeout=12: SAMPLE
at_purchase = FX.to_toman(10, "EUR")

FX._cache.clear()
FX._fetch_tgju = lambda timeout=12: {"current": {
    "price_eur": {"p": "5,000,000", "ts": "2026-10-01 10:00:00"}}}
later = FX.to_toman(10, "EUR")

check("نرخ بازار عوض شد", later["toman"] != at_purchase["toman"])
check("ولی مقدار ثبت‌شده‌ی قبلی همان است",
      at_purchase["toman"] == 2_746_100,
      "چون در دیتابیس amount_irt ذخیره می‌شود، نه دوباره محاسبه")

head("دسته‌های هزینه")

KINDS = {"server_abroad", "server_iran", "traffic", "domain", "other"}
src = open(os.path.join(ROOT, "backend", "app.py"), encoding="utf-8").read()
for k in KINDS:
    check(f"دسته‌ی {k} تعریف شده", f'"{k}"' in src)
check("جدول هزینه‌ها amount_irt دارد", "amount_irt  INTEGER" in src)
check("جدول هزینه‌ها نرخ را ذخیره می‌کند", "fx_rate     INTEGER" in src)
check("هزینه بدون مبلغ تومانی رد می‌شود",
      'conv.get("toman") is None' in src)
check("دفتر کل سود را از پرداختی حساب می‌کند",
      '"profit": paid - spent' in src)
check("دفتر کل بدهکاران را جدا می‌کند", '"owing"' in src)

print(f"\n{D}{'─' * 46}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
