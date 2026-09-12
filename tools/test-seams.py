#!/usr/bin/env python3
"""
درزها را می‌آزماید — جاهایی که دو نیمه‌ی کد باید با هم بخوانند.

چرا وجود دارد:
    هر باگی که در این پروژه به دست مشتری رسید، باگ منطق نبود؛ باگ
    اتصال بود. یک طرف چیزی را اعلام کرده بود و طرف دیگر خبر نداشت:

      · دکمه‌ی «تمدید» ساخته می‌شد، dispatch شاخه نداشت
      · «شارژ کیف پول» از جدول cards می‌خواند، جدولی وجود نداشت
      · firewall/suggest در بک‌اند بود، هیچ‌جای پنل صدایش نمی‌زد
      · tg.py متد action را دو بار تعریف کرده بود

    هیچ‌کدام را تست‌های معمولی نگرفتند، چون تست یک *تابع* را می‌آزماید
    و درز تابع نیست. این فایل به‌جای آزمودن رفتار، دو سمت هر درز را
    می‌شمارد و تفاضل می‌گیرد.

اجرا:  python3 tools/test-seams.py
"""
import ast
import io
import os
import re
import sys

G, R, Y, D, X = ("\033[38;5;42m", "\033[38;5;203m", "\033[38;5;221m",
                 "\033[38;5;245m", "\033[0m")
_ok = _fail = 0

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rd(*parts):
    return io.open(os.path.join(ROOT, *parts), encoding="utf-8").read()


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


def bullets(items, limit=12):
    """فهرست خطاها را زیر تست چاپ می‌کند تا لازم نباشد کسی بگردد."""
    for x in sorted(items)[:limit]:
        print(f"      {Y}▸{X} {x}")
    if len(items) > limit:
        print(f"      {D}… و {len(items) - limit} مورد دیگر{X}")


APP_PY = rd("backend", "app.py")
HANDLERS = rd("bot", "handlers.py")
DB_PY = rd("bot", "db.py")


def _frontend_src():
    """
    همه‌ی سورس فرانت‌اند، به هم چسبیده.

    تا وقتی پنل یک فایل ۱۱۴۰۰ خطی بود، خواندن App.jsx کافی بود. حالا
    که به ماژول شکسته شده، باید کل درخت را بخوانیم وگرنه این تست فکر
    می‌کند نصف پنل ناپدید شده.
    """
    base = os.path.join(ROOT, "frontend", "src")
    parts = []
    for dirpath, _dirs, files in os.walk(base):
        for f in sorted(files):
            if f.endswith((".jsx", ".js")):
                parts.append(io.open(os.path.join(dirpath, f),
                                     encoding="utf-8").read())
    return "\n".join(parts)


APP_JSX = _frontend_src()

print(f"\n{D}{'═' * 54}{X}")
print("  تست درزها — دو سمت هر اتصال باید با هم بخوانند")
print(f"{D}{'═' * 54}{X}")


# ═══════════════════════════════════════════════════════════
#  درز ۱ — مسیرهای بک‌اند ↔ صداکننده‌های فرانت‌اند
# ═══════════════════════════════════════════════════════════
head("درز ۱ · بک‌اند ↔ فرانت‌اند")


def _collapse(p):
    """
    ${...} را حذف می‌کند — با شمردن آکولاد، چون درون‌شان خودشان
    آکولاد و پرانتز دارند: ${encodeURIComponent(sel.name)}
    """
    out, i = [], 0
    while i < len(p):
        if p.startswith("${", i):
            depth, i = 1, i + 2
            while i < len(p) and depth:
                depth += (p[i] == "{") - (p[i] == "}")
                i += 1
            out.append(":p")
        else:
            out.append(p[i])
            i += 1
    return "".join(out)


def normalize(p):
    """
    /api/x/{id} و /api/x/${n} را به یک شکل درمی‌آورد تا قابل مقایسه شوند،
    و رشته‌ی پرس‌وجو را دور می‌ریزد چون بخشی از مسیر نیست.
    """
    p = _collapse(p).split("?")[0].rstrip("/")
    p = re.sub(r"\{[^}]*\}", ":p", p)       # {palette_id} → :p
    p = re.sub(r"(?::p){2,}", ":p", p)      # `${id}${q}` یک پارامتر است، نه دو
    return p


routes = {normalize(m.group(2))
          for m in re.finditer(r'@app\.(get|post|put|delete|patch)\(\s*"([^"]+)"',
                               APP_PY)}

# فرانت‌اند از دو شکل استفاده می‌کند: تمپلیت مستقیم، و helper به نام call.
# کل بک‌تیک را برمی‌داریم، نه تا اولین پرانتز — چون ${encodeURIComponent(x)}
# داخل خودش پرانتز دارد و برش زودهنگام مسیر را ناقص می‌کند.
called = set()
for lit in re.findall(r'`([^`]*)`', APP_JSX):
    m = re.search(r'\$\{API_URL\}(/api[^\s]*)', lit)
    if m:
        called.add(normalize(m.group(1)))
for m in re.finditer(r'call\(\s*[`"\']([^`"\']*(?:\$\{[^}]*\}[^`"\']*)*)',
                     APP_JSX):
    if m.group(1).startswith("/api"):
        called.add(normalize(m.group(1)))

check("مسیرهای بک‌اند استخراج شدند", len(routes) > 50, f"{len(routes)} مسیر")
check("صداکننده‌های فرانت‌اند استخراج شدند", len(called) > 40,
      f"{len(called)} صدازدن")

# فرانت‌اند مسیری را صدا بزند که وجود ندارد = ۴۰۴ در دست مشتری
ghost = called - routes - {"/api"}
check("هر صدازدن فرانت‌اند مسیر واقعی دارد", not ghost,
      f"{len(ghost)} مسیر ناموجود" if ghost else "")
if ghost:
    bullets(ghost)

# مسیری که هیچ‌کس صدا نمی‌زند = کد مرده (باگ «پیشنهاد قواعد فایروال»)
# مسیرهای عمومی و مسیرهای ایجنت را مستثنا می‌کنیم: صداکننده‌شان مرورگر،
# صفحه‌ی اشتراک، یا اسکریپت ایجنت روی سرور دیگر است — نه App.jsx.
PUBLIC = ("/api/public", "/api/sub", "/api/health", "/api/docs",
          "/api/openapi", "/api/agent")

#: مسیرهایی که می‌دانیم صداکننده ندارند و دلیلش را نوشته‌ایم.
#: این فهرست عمداً کوتاه است — هر ورودی یک بدهی است، نه یک استثنا.
#: مسیر تازه‌ای که این‌جا نباشد، تست را قرمز می‌کند.
KNOWN_ORPHANS = {
    "/api/admin/reset-defaults":
        "کل تنظیمات را بدون تأیید به پیش‌فرض برمی‌گرداند — بهتر است حذف شود",
    "/api/admin/billing/overview":
        "داکstring می‌گوید پایه‌ی صفحات حسابداری است ولی پنل صدایش نمی‌زند",
    "/api/admin/billing/payments/:p":
        "پنل پرداخت ثبت می‌کند ولی دکمه‌ی حذف ندارد",
    "/api/admin/health/local":
        "سلامت سرور خود پنل — پنل فقط سرورهای دیگر را نشان می‌دهد",
}

orphan = {r for r in routes - called if not r.startswith(PUBLIC)}
new_orphans = orphan - set(KNOWN_ORPHANS)
check("مسیر بی‌صداکننده‌ی تازه‌ای اضافه نشده", not new_orphans,
      f"{len(new_orphans)} مسیر تازه" if new_orphans
      else f"{len(orphan)} بدهی شناخته‌شده")
if new_orphans:
    bullets(new_orphans)

# بدهی‌های شناخته‌شده هشدارند، نه شکست — ولی دیده می‌شوند
still = orphan & set(KNOWN_ORPHANS)
if still:
    print(f"    {D}بدهی‌های باز:{X}")
    for r in sorted(still):
        print(f"      {Y}▸{X} {r} {D}— {KNOWN_ORPHANS[r]}{X}")

# اگر بدهی‌ای وصل شد، باید از فهرست پاک شود وگرنه فهرست بی‌معنا می‌شود
stale = set(KNOWN_ORPHANS) - orphan
check("فهرست بدهی‌ها به‌روز است", not stale,
      f"{len(stale)} مورد دیگر بدهی نیست" if stale else "")
if stale:
    bullets(stale)


# ═══════════════════════════════════════════════════════════
#  درز ۲ — جدول‌هایی که ربات کوئری می‌زند ↔ اسکیمای واقعی
# ═══════════════════════════════════════════════════════════
head("درز ۲ · کوئری‌های ربات ↔ اسکیمای دیتابیس")

BOT_DIR = os.path.join(ROOT, "bot")
bot_sources = {f: rd("bot", f) for f in sorted(os.listdir(BOT_DIR))
               if f.endswith(".py") and not f.startswith("test_")}

# پنل هم در دیتابیس ربات جدول می‌سازد (مثلاً bot_flags برای فرمان reload)،
# پس اسکیمای واقعی مجموع هر دو فایل است، نه فقط db.py
_CREATE = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?["\']?(\w+)'
schema = {m.lower() for m in re.findall(_CREATE, DB_PY, re.I)}
schema |= {m.lower() for m in re.findall(_CREATE, APP_PY, re.I)}
check("اسکیما خوانده شد", len(schema) > 3, f"{len(schema)} جدول")

# فقط داخل رشته‌هایی که واقعاً SQL هستند می‌گردیم. اگر مستقیم روی
# متن فایل regex بزنیم، «from datetime import ...» هم جدول حساب می‌شود.
SQL_START = re.compile(r'\b(SELECT|INSERT|UPDATE|DELETE|REPLACE)\b', re.I)
queried = {}
for fname, src in bot_sources.items():
    try:
        tree = ast.parse(src)
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        sql = node.value
        if not SQL_START.search(sql):
            continue
        for m in re.finditer(r'\b(?:FROM|JOIN|INTO|UPDATE)\s+["\']?(\w+)',
                             sql, re.I):
            t = m.group(1).lower()
            if t in ("select", "set", "where", "values"):
                continue
            queried.setdefault(t, set()).add(fname)

# جدول‌های موقتی/سیستمی SQLite را نادیده می‌گیریم
SYSTEM = {"sqlite_master", "sqlite_sequence", "pragma"}
missing = {t: f for t, f in queried.items()
           if t not in schema and t not in SYSTEM}

check("هر جدولی که ربات کوئری می‌زند در اسکیما هست", not missing,
      f"{len(missing)} جدول ناموجود" if missing else
      f"{len(queried)} جدول بررسی شد")
if missing:
    bullets([f"{t}  ({', '.join(sorted(f))})" for t, f in missing.items()])


# ═══════════════════════════════════════════════════════════
#  درز ۳ — کلیدهای تنظیمات: ربات می‌خواند ↔ پنل می‌نویسد
# ═══════════════════════════════════════════════════════════
head("درز ۳ · تنظیمات ربات ↔ فرم پنل")

# فقط ctx.s و self.s — نه هر s.get دیگری، چون s نام رایج ردیف اشتراک هم هست
read_keys = set()
for src in bot_sources.values():
    read_keys |= set(re.findall(r'(?:ctx|self)\.s\.get\(\s*"([a-z_]+)"', src))
    read_keys |= set(re.findall(r'(?:ctx|self)\.s\[\s*"([a-z_]+)"\s*\]', src))

check("کلیدهای تنظیمات استخراج شدند", len(read_keys) > 10,
      f"{len(read_keys)} کلید")

# کلیدی که ربات می‌خواند ولی هیچ‌جای پنل نیست، یعنی مدیر هرگز
# نمی‌تواند مقدارش را بدهد — همیشه خالی می‌ماند و بی‌صدا از کار می‌افتد.
unreachable = {k for k in read_keys if f'"{k}"' not in APP_JSX
               and f"'{k}'" not in APP_JSX and f".{k}" not in APP_JSX}
check("هر تنظیمی که ربات می‌خواند در پنل قابل تنظیم است", not unreachable,
      f"{len(unreachable)} کلید بی‌راه" if unreachable else "")
if unreachable:
    bullets(unreachable)


# ═══════════════════════════════════════════════════════════
#  درز ۴ — تعریف تکراری: دو متد هم‌نام، یکی بی‌صدا برنده
# ═══════════════════════════════════════════════════════════
head("درز ۴ · تعریف تکراری")

dupes = []
for fname, src in bot_sources.items():
    try:
        tree = ast.parse(src)
    except SyntaxError:
        continue
    # سطح ماژول و سطح کلاس، جدا از هم
    scopes = [("", tree.body)]
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            scopes.append((node.name + ".", node.body))
    for prefix, body in scopes:
        seen = {}
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in seen:
                    dupes.append(f"{fname}: {prefix}{node.name}() "
                                 f"خط {seen[node.name]} و {node.lineno}")
                seen[node.name] = node.lineno

check("هیچ تابعی دو بار تعریف نشده", not dupes,
      f"{len(dupes)} تعریف تکراری" if dupes else
      f"{len(bot_sources)} فایل بررسی شد")
if dupes:
    bullets(dupes)


# ═══════════════════════════════════════════════════════════
#  درز ۵ — هر هندلری که ثبت شده باید وجود داشته باشد
# ═══════════════════════════════════════════════════════════
head("درز ۵ · ارجاع به توابع ناموجود")

tree = ast.parse(HANDLERS)
defined = {n.name for n in ast.walk(tree)
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
imported = set(re.findall(r'^(?:from|import)\s+(\w+)', HANDLERS, re.M))

referenced = set(re.findall(r'\breturn\s+(show_\w+|admin_\w+|cmd_\w+)\(',
                            HANDLERS))
dangling = sorted(f for f in referenced if f not in defined)
check("هر تابعی که صدا زده می‌شود تعریف شده", not dangling, str(dangling))

check("ماژول‌های لازم import شده‌اند",
      {"core", "db"} <= imported | defined,
      f"{sorted(imported)[:4]}")


# ═══════════════════════════════════════════════════════════
print(f"\n{D}{'─' * 54}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
if not _fail:
    print(f"  {D}هر دو سمت همه‌ی درزها با هم می‌خوانند{X}")
print()
sys.exit(1 if _fail else 0)
