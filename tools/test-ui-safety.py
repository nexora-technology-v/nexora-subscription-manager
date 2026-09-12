#!/usr/bin/env python3
"""
سه باگی که کاربر دید و دیگر نباید برگردند.

۱. صفحه‌ی سیاه هنگام بستن آی‌پی
   FastAPI برای خطای اعتبارسنجی، detail را آرایه‌ای از آبجکت
   برمی‌گرداند. رندر مستقیم آن در JSX یعنی خطای React و از دست
   رفتن کل صفحه. هیچ detail خامی نباید به JSX برسد.

۲. «ناعدد» در حسابداری
   Number("متن").toLocaleString("fa-IR") در جاوااسکریپت رشته‌ی
   «ناعدد» می‌دهد. این کلمه هیچ معنایی برای کاربر ندارد.

۳. باکس‌های چسبیده
   فاصله فقط با کلاس دستی mb-4 می‌آمد و هرجا جا می‌افتاد،
   دو کارت به هم می‌چسبیدند.

اجرا:  python3 tools/test-ui-safety.py
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "frontend", "src")

G, R, Y, D, X = ("\033[38;5;42m", "\033[38;5;203m", "\033[38;5;221m",
                 "\033[38;5;245m", "\033[0m")
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


def sources():
    for dirpath, _d, files in os.walk(SRC):
        for f in sorted(files):
            if f.endswith((".jsx", ".js")):
                p = os.path.join(dirpath, f)
                key = os.path.relpath(p, SRC).replace(os.sep, "/")
                yield key, io.open(p, encoding="utf-8").read()


ALL = dict(sources())
FMT = ALL.get("lib/format.js", "")
UI = ALL.get("ui/index.jsx", "")
APP = ALL.get("App.jsx", "")
CSS = io.open(os.path.join(SRC, "index.css"), encoding="utf-8").read()


# ═══════════════════════════════════════════════════════════
head("۱ · صفحه‌ی سیاه هنگام خطای سرور")

check("errText تعریف شده", "export function errText" in FMT)
check("آرایه‌ی خطای FastAPI را مدیریت می‌کند", "Array.isArray(detail)" in FMT)
check("آبجکت تنها را هم مدیریت می‌کند", 'detail.msg || detail.message' in FMT)
check("loc را به نام فیلد تبدیل می‌کند", "d.loc" in FMT)

raw = []
for name, src in ALL.items():
    if name == "lib/format.js":
        continue
    for m in re.finditer(r'\b([a-z]\w*)\.detail\b', src):
        start = max(0, m.start() - 9)
        if "errText(" in src[start:m.start()]:
            continue
        # فیلدهای داده‌ای خودمان، نه پاسخ خطا
        line = src[src.rfind("\n", 0, m.start()) + 1:
                   src.find("\n", m.end())]
        if re.search(r'\bs\.detail\b', line) and "errText" not in line:
            continue
        raw.append(f"{name}: {line.strip()[:70]}")

check("هیچ detail خامی به JSX نمی‌رسد", not raw,
      f"{len(raw)} مورد" if raw else f"{len(ALL)} فایل بررسی شد")
for r in raw[:8]:
    print(f"      {Y}▸{X} {r}")

check("مرز خطا وجود دارد", "class ErrorBoundary" in UI)
check("getDerivedStateFromError دارد", "getDerivedStateFromError" in UI)
check("محتوای صفحه در مرز خطا پیچیده شده", "<ErrorBoundary" in APP)
check("با عوض‌شدن صفحه بازنشانی می‌شود", "ErrorBoundary key={active}" in APP,
      "وگرنه یک خطا تا رفرش روی همه‌ی صفحات می‌ماند")
check("مرز خطا راه بازگشت می‌دهد", "دوباره تلاش" in UI)
check("مرز خطا می‌گوید بقیه سالم است", "بقیه‌ی پنل سالم است" in UI)


head("۲ · «ناعدد»")

check("faNum مقدار خالی را خط تیره می‌کند",
      'n === null || n === undefined || n === ""' in FMT)
check("عدد نامتناهی هم خط تیره می‌شود", "Number.isFinite(n)" in FMT)
check("متن غیرعددی فقط رقم‌هایش فارسی می‌شود", "toFaDigits(s)" in FMT)
check("هیچ مسیری به toLocaleString روی NaN نمی‌رسد",
      "Number(n || 0).toLocaleString" not in FMT,
      "شکل قبلی که «ناعدد» می‌ساخت")

# کلمه نباید به‌عنوان متنِ نمایشی جایی بیاید. داخل توضیحِ کد
# اشکالی ندارد — همان‌جا دلیل وجود این تست نوشته شده.
def strip_comments(src):
    src = re.sub(r"/\*[\s\S]*?\*/", " ", src)
    return re.sub(r"^\s*//.*$", " ", src, flags=re.M)

hard = [n for n, s in ALL.items() if "ناعدد" in strip_comments(s)]
check("کلمه‌ی «ناعدد» به کاربر نشان داده نمی‌شود", not hard, str(hard))


head("۳ · فاصله‌ی باکس‌ها")

check("قاعده‌ی فاصله‌ی عمومی هست", ".fx-anim > * + *" in CSS,
      "هر دو عنصر هم‌سطح، نه فقط چند ترکیب مشخص")
check("از توکن فاصله استفاده می‌کند", "var(--space-4)" in CSS)
check("مقیاس فاصله تعریف شده",
      all(f"--space-{n}:" in CSS for n in (2, 3, 4, 6, 8)))
check("فقط فرزند مستقیم را می‌گیرد", ".fx-anim >" in CSS,
      "تا خانه‌های گرید که gap دارند دست‌نخورده بمانند")
check("دلیلش نوشته شده", "collapse" in CSS)


head("سلامت کلی رابط")

# هر فایلی که از یک کامپوننت استفاده می‌کند باید import کرده باشد
missing = []
for name, src in ALL.items():
    if not name.endswith(".jsx"):
        continue
    used = set(re.findall(r"<([A-Z]\w+)[\s/>]", src))
    declared = set(re.findall(r"(?:function|const|class)\s+([A-Z]\w+)", src))
    # <Icon /> که از پراپ یا destructure می‌آید: const { icon: Icon } = m
    declared |= set(re.findall(r"[:{]\s*([A-Z]\w+)\s*[,}=]", src))
    declared |= set(re.findall(r"const\s+([A-Z]\w+)\s*=", src))
    # destructure آرایه‌ای در map:  .map(([k, l, Ico, tag]) => ...)
    for m in re.finditer(r"\(\s*\[([^\]]*)\]\s*\)\s*=>", src):
        declared |= {x.strip() for x in m.group(1).split(",")
                     if re.fullmatch(r"[A-Z]\w*", x.strip())}
    imported = set()
    for m in re.finditer(r"import\s+\{([^}]*)\}\s+from", src):
        imported |= {x.strip().split(" as ")[-1] for x in m.group(1).split(",")}
    for m in re.finditer(r"import\s+(\w+)\s+from", src):
        imported.add(m.group(1))
    # React.Fragment و تگ‌های داخلی
    gap = used - declared - imported - {"React"}
    if gap:
        missing.append(f"{name}: {sorted(gap)}")

check("هر کامپوننتی که استفاده می‌شود import شده", not missing,
      f"{len(missing)} فایل" if missing else f"{len(ALL)} فایل")
for m in missing[:6]:
    print(f"      {Y}▸{X} {m}")

# هیچ فایلی نباید چیزی export کند که تعریف نکرده
broken = []
for name, src in ALL.items():
    for m in re.finditer(r"^export\s+(?:function|const|class)\s+(\w+)",
                         src, re.M):
        pass
    for m in re.finditer(r"import\s+\{([^}]*)\}\s+from\s+[\"'](\.[^\"']+)[\"']",
                         src):
        names = [x.strip().split(" as ")[0] for x in m.group(1).split(",")
                 if x.strip()]
        target = os.path.normpath(os.path.join(
            os.path.dirname(name), m.group(2)))
        cand = [target + ".jsx", target + ".js",
                os.path.join(target, "index.jsx")]
        tsrc = next((ALL[c.replace(os.sep, "/")] for c in cand
                     if c.replace(os.sep, "/") in ALL), None)
        if tsrc is None:
            broken.append(f"{name}: ماژول {m.group(2)} پیدا نشد")
            continue
        for n2 in names:
            if not re.search(r"export\s+(?:function|const|class|let|var)\s+"
                             + re.escape(n2) + r"\b", tsrc):
                broken.append(f"{name}: {n2} در {m.group(2)} export نشده")

check("هر import به یک export واقعی می‌رسد", not broken,
      f"{len(broken)} مورد" if broken else "")
for b in broken[:8]:
    print(f"      {Y}▸{X} {b}")

print(f"\n{D}{'─' * 46}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
