#!/usr/bin/env python3
"""
تست ریاضیات حسابداری.

چرا وجود دارد:
    گزارش شد «با اینکه نرخ تعیین کرده‌ام، بعضی ردیف‌ها بدون نرخ
    می‌آیند». علتش این بود که وقتی حجم کانفیگ از همه‌ی نرخ‌های
    تعریف‌شده بزرگ‌تر بود، هیچ نرخی انتخاب نمی‌شد و آن ردیف *صفر*
    حساب می‌شد — یعنی پول از دست رفته، بی‌سروصدا.

اجرا:  python3 tools/test-billing.py
"""
import io
import os
import re
import sys

G, R, D, X = "\033[38;5;42m", "\033[38;5;203m", "\033[38;5;245m", "\033[0m"
_ok = _fail = 0

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = io.open(os.path.join(ROOT, "backend", "app.py"), encoding="utf-8").read()

# فقط همین تابع را برمی‌داریم تا کل app.py با وابستگی‌هایش لازم نشود
_m = re.search(r"def _price_for.*?\n(?=\n\n@|\n\ndef )", SRC, re.S)
if not _m:
    print(f"{R}تابع _price_for در backend/app.py پیدا نشد{X}")
    sys.exit(1)
_ns = {}
exec(_m.group(0), _ns)
price_for = _ns["_price_for"]


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


RATES = [{"gb": 30, "price": 90_000},
         {"gb": 50, "price": 120_000},
         {"gb": 100, "price": 190_000}]

head("انتخاب نرخ")
check("تطابق دقیق حجم", price_for(50, RATES) == 120_000,
      str(price_for(50, RATES)))
check("حجم بین دو نرخ، بالاتر را می‌گیرد", price_for(40, RATES) == 120_000,
      str(price_for(40, RATES)))
check("حجم کمتر از همه، کوچک‌ترین نرخ", price_for(10, RATES) == 90_000,
      str(price_for(10, RATES)))

# باگ اصلی: قبلاً None برمی‌گشت و ردیف صفر حساب می‌شد
check("حجم بزرگ‌تر از همه‌ی نرخ‌ها، بالاترین نرخ را می‌گیرد",
      price_for(200, RATES) == 190_000, str(price_for(200, RATES)))
check("حجم خیلی بزرگ هم صفر نمی‌شود",
      price_for(5000, RATES) is not None, str(price_for(5000, RATES)))

head("نامحدود")
check("نامحدود بدون نرخ نامحدود، بدون نرخ می‌ماند",
      price_for(0, RATES) is None, str(price_for(0, RATES)))
check("نرخ حجمی به نامحدود تعمیم داده نمی‌شود",
      price_for(0, RATES) != 190_000)

UNL = RATES + [{"gb": 0, "price": 250_000}]
check("نامحدود با نرخ نامحدود", price_for(0, UNL) == 250_000,
      str(price_for(0, UNL)))
check("وجود نرخ نامحدود، انتخاب حجمی را خراب نمی‌کند",
      price_for(50, UNL) == 120_000, str(price_for(50, UNL)))

head("ورودی خراب")
check("لیست خالی", price_for(50, []) is None)
check("None", price_for(50, None) is None)
check("نرخ با مقدار غیرعددی نادیده گرفته می‌شود",
      price_for(50, [{"gb": "خراب", "price": "x"}, {"gb": 50, "price": 120_000}])
      == 120_000)
check("همه‌ی نرخ‌ها خراب", price_for(50, [{"gb": "x", "price": "y"}]) is None)

print(f"\n{D}{'─' * 46}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
