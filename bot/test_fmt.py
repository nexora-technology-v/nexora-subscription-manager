#!/usr/bin/env python3
"""
واژگان قالب‌بندی و سلامت HTML همه‌ی پیام‌های ربات.

چرا وجود دارد:
    تلگرام پیامی را که HTML خرابی داشته باشد رد می‌کند — کاربر هیچ
    چیزی نمی‌بیند و در لاگ فقط یک ۴۰۰ می‌ماند. یک <b> بسته‌نشده کافی
    است تا صفحه‌ای کامل از کار بیفتد.

    این تست دو کار می‌کند: خود توابع fmt را می‌سنجد، و بعد همه‌ی
    صحنه‌هایی که preview_texts می‌سازد را از اعتبارسنج رد می‌کند.

اجرا:  python3 bot/test_fmt.py
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fmt as F  # noqa: E402

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
head("امن‌سازی")

check("< و > امن می‌شوند", F.esc("<b>x</b>") == "&lt;b&gt;x&lt;/b&gt;")
check("& امن می‌شود", F.esc("a & b") == "a &amp; b")
check("None خالی می‌شود", F.esc(None) == "")
check("عدد هم قبول است", F.esc(42) == "42")
check("امن‌سازی دوباره نمی‌شکند",
      F.esc(F.esc("&")) == "&amp;amp;", "esc دوبار = دوبار کدگذاری")

head("تگ‌های پایه")

check("پررنگ", F.b("سلام") == "<b>سلام</b>")
check("خط‌خورده", F.s("۱۰۰") == "<s>۱۰۰</s>")
check("تک‌فاصله", F.code("nexora_1") == "<code>nexora_1</code>")
check("اسپویلر", F.spoiler("۱۰٪") == "<tg-spoiler>۱۰٪</tg-spoiler>")
check("ورودی خطرناک داخل تگ امن می‌شود",
      F.b("<script>") == "<b>&lt;script&gt;</b>")
check("pre با زبان",
      'class="language-bash"' in F.pre("ls", lang="bash"))

head("لینک")

check("لینک سالم", F.link("اینجا", "https://x.ir")
      == '<a href="https://x.ir">اینجا</a>')
check("لینک tg:// قبول می‌شود", 'href="tg://' in F.user_link("x", 5))
check("آدرس نامعتبر فقط متن می‌شود",
      F.link("متن", "javascript:alert(1)") == "متن",
      "نباید تگ بسازد")
check("آدرس خالی فقط متن می‌شود", F.link("متن", None) == "متن")
check("آدرس با نویسه‌ی خطرناک امن می‌شود",
      "&amp;" in F.link("x", "https://a.ir/?a=1&b=2"))

head("نقل‌قول")

check("نقل‌قول ساده", F.quote("خط") == "<blockquote>خط</blockquote>")
check("نقل‌قول چندخطی", "\n" in F.quote("یک", "دو"))
check("نقل‌قول جمع‌شونده", F.quote_more("متن")
      == "<blockquote expandable>متن</blockquote>")
check("قالب‌بندی داخل نقل‌قول می‌ماند",
      "<b>" in F.quote(F.b("مهم")), "نقل‌قول ورودی آماده را دست نمی‌زند")
check("None داخل نقل‌قول انداخته می‌شود",
      F.quote("یک", None, "دو") == "<blockquote>یک\nدو</blockquote>")

head("قیمت")

check("قیمت بدون تخفیف", F.price("۱۹۰") == "<b>۱۹۰ تومان</b>")
check("قیمت با تخفیف خط‌خورده دارد", "<s>" in F.price("۱۹۰", old="۲۵۰"))
check("قیمت با تخفیف جدید را پررنگ می‌کند",
      "<b>۱۹۰ تومان</b>" in F.price("۱۹۰", old="۲۵۰"))
check("قیمت یکسان خط‌خورده نمی‌گیرد",
      "<s>" not in F.price("۱۹۰", old="۱۹۰"))

head("چیدمان")

check("join خالی‌ها را می‌اندازد",
      F.join("یک", "", None, "دو") == "یک\n\nدو")
check("lines بدون سطر خالی", F.lines("یک", "دو") == "یک\nدو")
check("title پررنگ است", F.title("سلام", "👋") == "👋 <b>سلام</b>")
check("title بدون اموجی فاصله‌ی اضافه ندارد",
      F.title("سلام") == "<b>سلام</b>")
check("field مقدار را کپی‌کردنی می‌کند", "<code>" in F.field("کد", "AB12"))

head("اعتبارسنج")

check("متن سالم ایراد ندارد", F.check(F.b("x") + F.code("y")) == [])
check("تگ بسته‌نشده گرفته می‌شود",
      any("بسته نشده" in p for p in F.check("<b>سلام")))
check("تگ ناشناخته گرفته می‌شود",
      any("ناشناخته" in p for p in F.check("<marquee>x</marquee>")))
check("ترتیب غلط گرفته می‌شود",
      F.check("<b><i>x</b></i>") != [])
check("تگ داخل code گرفته می‌شود",
      any("بی‌اثر" in p for p in F.check("<code><b>x</b></code>")))
check("a بدون href گرفته می‌شود",
      any("href" in p for p in F.check("<a>x</a>")))
check("& تنها گرفته می‌شود",
      any("امن‌سازی‌نشده" in p for p in F.check("a & b")))
check("&amp; مشکلی ندارد", F.check("a &amp; b") == [])
check("بستن بدون باز شدن گرفته می‌شود",
      any("بدون باز شدن" in p for p in F.check("</b>")))
check("blockquote expandable معتبر است",
      F.check(F.quote_more("x")) == [])

check("plain تگ‌ها را برمی‌دارد", F.plain("<b>سلام</b>") == "سلام")
check("سقف طول شناسایی می‌شود", F.too_long("x" * 4097))
check("پیام معمولی بلند نیست", not F.too_long("x" * 100))


# ═══════════════════════════════════════════════════════════
head("همه‌ی صحنه‌های ربات")

# preview_texts هر صفحه‌ی ربات را می‌سازد. اگر HTML هر کدام خراب باشد،
# این‌جا لو می‌رود — نه در دست مشتری.
import subprocess  # noqa: E402

env = dict(os.environ, PYTHONIOENCODING="utf-8", NEXORA_PREVIEW_RAW="1")
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
proc = subprocess.run([sys.executable, os.path.join("bot", "preview_texts.py")],
                      cwd=root, env=env, capture_output=True, text=True,
                      encoding="utf-8", errors="replace", timeout=300)

check("پیش‌نمایش بدون خطا اجرا شد",
      proc.returncode == 0 and "Traceback" not in (proc.stdout + proc.stderr),
      (proc.stderr or "").strip().splitlines()[-1][:60] if proc.returncode else "")

raw = os.path.join(root, "bot", ".preview-raw.txt")
if os.path.exists(raw):
    blocks = io.open(raw, encoding="utf-8").read().split("\x00")
    blocks = [b for b in blocks if b.strip()]
    check("صحنه‌ها استخراج شدند", len(blocks) > 30, f"{len(blocks)} پیام")

    bad = []
    for blk in blocks:
        name, _, body = blk.partition("\x01")
        for p in F.check(body):
            bad.append(f"{name.strip()}: {p}")
    check("HTML همه‌ی پیام‌ها سالم است", not bad,
          f"{len(bad)} ایراد" if bad else f"{len(blocks)} پیام بررسی شد")
    for line in bad[:10]:
        print(f"      {R}▸{X} {line}")

    long_ = [b.partition("\x01")[0].strip() for b in blocks
             if F.too_long(b.partition("\x01")[2])]
    check("هیچ پیامی از سقف تلگرام رد نشده", not long_, ", ".join(long_[:3]))

    os.remove(raw)
else:
    check("فایل خام پیش‌نمایش ساخته شد", False, ".preview-raw.txt نبود")


print(f"\n{D}{'─' * 46}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
