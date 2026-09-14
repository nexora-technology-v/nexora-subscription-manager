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

# هر رشته‌ای که با /api/ شروع شود یک صدازدن است — فرقی نمی‌کند
# مستقیم در fetch باشد یا به یک helper مثل call() یا useJson() برود.
# الگوی قبلی فقط call() را می‌شناخت و وقتی useJson اضافه شد، مسیرهای
# تازه بی‌صداکننده به نظر رسیدند.
for m in re.finditer(r'[`"\'](/api/[^`"\'\s]*)', APP_JSX):
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
# الگو باید *شکل* SQL را ببیند، نه فقط یک کلمه‌ی کلیدی. یک داک‌استرینگ
# فارسی که در توضیحش می‌نویسد «UPDATE هیچ شرطی نداشت» وگرنه SQL حساب
# می‌شد و «هیچ» را به‌عنوان نام جدول گزارش می‌کرد.
SQL_START = re.compile(
    r'\bSELECT\b[\s\S]*\bFROM\b'
    r'|\bINSERT\s+(?:OR\s+\w+\s+)?INTO\b'
    r'|\bUPDATE\s+\w+\s+SET\b'
    r'|\bDELETE\s+FROM\b'
    r'|\bREPLACE\s+INTO\b', re.I)
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
#  درز ۶ — آیکون استفاده‌شده ولی import‌نشده
# ═══════════════════════════════════════════════════════════
head("درز ۶ · آیکون بدون import")

# این دو بار اتفاق افتاد و هر دو بار فقط موقع اجرای واقعی پیدا شد:
# «Activity is not defined» و بعد «Power is not defined». باندل بدون
# خطا ساخته می‌شود چون esbuild نام آزاد را خطا نمی‌گیرد؛ فقط مرورگر
# موقع اجرا می‌افتد — و کل پنل سفید می‌شود.
FRONT = os.path.join(ROOT, "frontend", "src")
icon_problems = []

for dirpath, _dirs, files in os.walk(FRONT):
    for fname in files:
        if not fname.endswith((".jsx", ".js")):
            continue
        path = os.path.join(dirpath, fname)
        src = io.open(path, encoding="utf-8").read()

        imported = set()
        for im in re.finditer(r'import \{([^}]*)\} from', src):
            for chunk in im.group(1).split(","):
                chunk = chunk.strip()
                if chunk:
                    imported.add(chunk.split()[-1])
        imported |= set(re.findall(r'^import (\w+)', src, re.M))

        # هر چیزی که در همین فایل تعریف شده
        local = set(re.findall(
            r'^(?:export\s+)?(?:default\s+)?'
            r'(?:function|const|let|var|class)\s+(\w+)', src, re.M))
        # کامپوننت‌های تعریف‌شده داخل بدنه‌ی یک کامپوننت دیگر
        local |= set(re.findall(r'\bconst\s+([A-Z]\w*)\s*=', src))

        # نام‌هایی که از destructuring پارامتر می‌آیند: ({ icon: Icon })
        # اینها متغیر محلی‌اند، نه نام آزاد. بدون این، هر کامپوننتی که
        # آیکون را به‌عنوان prop می‌گیرد اشتباهاً «import‌نشده» اعلام
        # می‌شد — و تست به‌خاطر خودش قرمز می‌ماند.
        for params in re.findall(r'(?:function\s+\w+|=>|\()\s*\(?\{([^}]*)\}',
                                 src):
            local |= set(re.findall(r'\w+\s*:\s*([A-Z]\w*)', params))

        # و از destructuring آرایه‌ای: .map(([k, l, Ico, tag]) => …)
        for params in re.findall(r'\(\s*\[([^\]]*)\]\s*\)\s*=>', src):
            local |= set(re.findall(r'\b([A-Z]\w*)\b', params))

        used = set(re.findall(r'<([A-Z][A-Za-z0-9]+)[\s/>]', src))
        used |= set(re.findall(r'icon:\s*([A-Z][A-Za-z0-9]+)', src))

        for name in sorted(used):
            if name in imported or name in local:
                continue
            if name in ("React", "Fragment"):
                continue
            icon_problems.append(f"{os.path.relpath(path, ROOT)}: {name}")

check("هر آیکون/کامپوننت استفاده‌شده import شده", not icon_problems,
      f"{len(icon_problems)} مورد" if icon_problems
      else "همان باگی که دو بار پنل را سفید کرد")
if icon_problems:
    bullets(icon_problems, limit=15)


# ═══════════════════════════════════════════════════════════
#  درز ۷ — ماژولی که استفاده شده ولی import نشده (پایتون)
# ═══════════════════════════════════════════════════════════
head("درز ۷ · نام ناموجود در پایتون")

# app.py ماژول re را با نام _re وارد می‌کند. دو تابع تازه `re.match`
# نوشتند — کامپایل بی‌صدا رد می‌شود، چون پایتون نام آزاد را فقط موقع
# اجرا حل می‌کند. NameError وقتی رخ می‌داد که کاربر دکمه را می‌زد.
py_problems = []
STDLIB = ("re", "os", "sys", "json", "time", "math", "random", "socket",
          "sqlite3", "shutil", "subprocess", "hashlib", "hmac", "base64",
          "ipaddress", "tempfile", "logging", "secrets", "string", "uuid")

for rel in ("backend/app.py", "backend/monitor.py", "backend/firewall.py",
            "backend/netid.py", "backend/tunnels.py", "bot/handlers.py",
            "bot/db.py", "bot/core.py", "bot/xui.py", "bot/tg.py",
            "bot/run.py", "agent/nexora-agent.py"):
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        continue
    src = io.open(path, encoding="utf-8").read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        continue

    bound = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                bound.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                bound.add(a.asname or a.name)

    for mod in STDLIB:
        if mod in bound:
            continue
        hit = re.search(r"(?<![\w.])" + mod + r"\.[a-z_]+\(", src)
        if not hit:
            continue
        # ممکن است داخل خود تابع import شده باشد
        if re.search(r"^\s+import " + mod + r"\b", src, re.M):
            continue
        line = src[:hit.start()].count("\n") + 1
        py_problems.append(f"{rel}:{line} — {mod}. بدون import")

check("هر ماژولی که استفاده می‌شود import شده", not py_problems,
      f"{len(py_problems)} مورد" if py_problems
      else "همان NameError که فقط موقع کلیک کاربر رخ می‌داد")
if py_problems:
    bullets(py_problems)


# ═══════════════════════════════════════════════════════════
#  درز — هر مسیر مدیریتی باید احراز هویت کند
# ═══════════════════════════════════════════════════════════
head("درز · احراز هویت مسیرها")

# یک نقطه‌ی پایانی مدیریتی که check_auth را جا انداخته باشد، درِ باز
# است — و از بیرون هیچ تفاوتی با بقیه ندارد. با ۱۱۴ مسیر، چشم‌چرانی
# جواب نمی‌دهد؛ این بررسی درخت نحوی را می‌خواند.

import ast as _ast

_tree = _ast.parse(APP_PY)
_routes = []
for _n in _tree.body:
    if not isinstance(_n, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
        continue
    for _d in _n.decorator_list:
        if (isinstance(_d, _ast.Call) and _d.args
                and isinstance(_d.args[0], _ast.Constant)
                and re.fullmatch(r"app\.(get|post|put|delete|patch)",
                                 _ast.unparse(_d.func))):
            _routes.append((_d.args[0].value, _n))

check("مسیرها از درخت نحوی خوانده شدند", len(_routes) > 100,
      f"{len(_routes)} مسیر")

_admin = [(p, n) for p, n in _routes if p.startswith("/api/admin")]
_naked = [(p, n.name, n.lineno) for p, n in _admin
          if "check_auth" not in _ast.unparse(n)]
check("هر مسیر مدیریتی احراز هویت می‌کند", not _naked,
      ("، ".join(f"{p} (خط {ln})" for p, _f, ln in _naked)
       if _naked else f"{len(_admin)} مسیر"))
if _naked:
    bullets([f"{p} — {f}() خط {ln}" for p, f, ln in _naked])

# مسیرهای ایجنت با رمز مدیریت کار نمی‌کنند؛ با توکن و امضای نود.
_agent = [(p, n) for p, n in _routes if p.startswith("/api/agent")]
#: مسیرهایی که عمداً توکن نمی‌خواهند، و دلیلش.
#
#  این پنج‌تا فقط *کد* می‌دهند — منطق مانیتورینگ و فایروال و خودِ
#  ایجنت — نه داده و نه اعتبارنامه. بستنشان ممکن است، ولی download
#  در ایجنت توکن نمی‌فرستد، پس هر ایجنتی که همین حالا روی سرورها
#  نصب است دیگر نمی‌تواند خودش را به‌روز کند و برای همیشه عقب
#  می‌ماند. راهش این است که اول ایجنت توکن بفرستد و بعد این‌جا
#  اجباری شود — نه برعکس.
OPEN_AGENT_ROUTES = {
    "/api/agent/agent.py", "/api/agent/monitor.py",
    "/api/agent/firewall.py", "/api/agent/health.py",
    "/api/agent/netid.py",
}

_unsigned = [(p, n.name) for p, n in _agent
             if p not in OPEN_AGENT_ROUTES
             and "_agent_node" not in _ast.unparse(n)
             and "token" not in _ast.unparse(n.args).lower()]
check("هر مسیر ایجنتِ داده‌ای توکن می‌خواهد", not _unsigned,
      ("، ".join(p for p, _f in _unsigned) if _unsigned
       else f"{len(_agent) - len(OPEN_AGENT_ROUTES)} مسیر"))

_gone = [p for p in OPEN_AGENT_ROUTES
         if p not in {x for x, _n in _agent}]
check("فهرست استثناها کهنه نشده", not _gone,
      "، ".join(_gone) if _gone else "هر پنج‌تا هنوز هستند")

# و مسیرهای عمومی عمداً بازند — ولی باید کم و شناخته‌شده باشند
_public = sorted(p for p, _n in _routes
                 if not p.startswith(("/api/admin", "/api/agent")))
KNOWN_PUBLIC = {
    "/api/public/config", "/api/preview", "/api/health", "/api/sub/{sub_id}",
    "/", "/api", "/api/docs", "/api/openapi.json",
    # ورود خودش نمی‌تواند رمز بخواهد
    "/api/login",
    # ── پنل نماینده ──
    #
    # این‌ها check_auth ندارند چون رمز مدیر را نمی‌گیرند — از
    # portal_tenant رد می‌شوند که نشست نماینده را می‌سنجد و ردیف
    # مستاجر خودش را برمی‌گرداند. عمداً یک سطح جداست: مسیرهای مدیر
    # همه فرض می‌کنند «تو صاحب سیستمی» و هیچ‌کدامشان نباید دست
    # نماینده بیفتد.
    "/api/portal/{slug}/login",     # ورود، مثل /api/login رمز نمی‌خواهد
    "/api/portal/logout",           # فقط نشست خودش را پاک می‌کند
}

# بقیه‌ی مسیرهای نماینده یک دسته‌اند و تستِ اختصاصیِ پایین تضمین
# می‌کند همه‌شان از portal_tenant رد می‌شوند — که سختگیرانه‌تر از
# فهرست‌کردن تک‌تکشان این‌جاست.
KNOWN_PUBLIC |= {p for p, _n in _routes if p.startswith("/api/portal/")}

# ── هر مسیر نماینده باید به مستاجر خودش محدود باشد ──
#
# همان کاری که بالاتر برای check_auth روی مسیرهای مدیر انجام شد.
# مسیر نماینده‌ای که portal_tenant نداشته باشد یعنی یا احراز هویت
# ندارد یا — بدتر — احراز هویت دارد و محدود نیست، که دقیقاً همان
# باگی است که در مسیرهای ایجنت پیدا شد.
_portal = [(p, n) for p, n in _routes if p.startswith("/api/portal")]
_unguarded = [p for p, n in _portal
              if not p.endswith(("/login", "/logout"))
              and "portal_tenant" not in _ast.unparse(n)]
check("هر مسیر نماینده به مستاجر خودش محدود است", not _unguarded,
      "، ".join(_unguarded) if _unguarded
      else f"{len(_portal)} مسیر، همه پشت portal_tenant")
_new_public = [p for p in _public if p not in KNOWN_PUBLIC]
check("مسیر عمومی تازه‌ای بی‌خبر اضافه نشده", not _new_public,
      ("، ".join(_new_public) if _new_public
       else f"{len(_public)} مسیر عمومی شناخته‌شده"))
if _new_public:
    bullets(_new_public)



# ═══════════════════════════════════════════════════════════
#  درز — هر کوئری باید به مستاجر محدود باشد
# ═══════════════════════════════════════════════════════════
head("درز · محدودشدن به مستاجر")

# ربات چندمستاجری است: هر فروشگاه جدول‌های مشترک دارد و فقط ستون
# tenant_id آن‌ها را از هم جدا می‌کند. یک کوئری که آن شرط را جا
# بیندازد، داده‌ی یک فروشگاه را در ربات دیگری نشان می‌دهد — و هیچ
# خطایی هم نمی‌دهد، چون نتیجه «معتبر» به نظر می‌رسد.

TENANT_TABLES = {
    "users", "plans", "orders", "subscriptions", "coin_tx", "wallet_tx",
    "discounts", "tickets", "affiliates", "affiliate_commissions",
    "affiliate_payouts", "events",
}

#: کوئری‌هایی که عمداً به مستاجر محدود نیستند، و دلیلشان.
#: هر ورودی یک تصمیم است، نه یک استثنا.
TENANT_FREE = {
    "UPDATE subscriptions SET plan_name":
        "مهاجرت یک‌باره — عمداً روی همه‌ی مستاجرها، و روی plan_id که "
        "سراسری یکتاست",
}


def _sql_literals(tree):
    """رشته‌های SQL، با چسباندن رشته‌های مجاور."""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append((node.lineno, node.value))
        elif isinstance(node, ast.JoinedStr):
            parts = [v.value for v in node.values
                     if isinstance(v, ast.Constant) and isinstance(v.value, str)]
            out.append((node.lineno, " ".join(parts)))
    return out


_leaks, _checked = [], 0
for _path, _src in (("bot/db.py", DB_PY), ("bot/handlers.py", HANDLERS)):
    for _ln, _q in _sql_literals(ast.parse(_src)):
        if not re.search(r"\b(SELECT|INSERT INTO|UPDATE|DELETE FROM)\b",
                         _q, re.I):
            continue
        _tables = {t.lower() for t in re.findall(
            r"(?:FROM|INTO|UPDATE|JOIN)\s+([a-z_]+)", _q, re.I)}
        if not (_tables & TENANT_TABLES):
            continue
        _checked += 1
        if "tenant_id" in _q:
            continue
        _flat = " ".join(_q.split())
        if any(_flat.startswith(k) for k in TENANT_FREE):
            continue
        _leaks.append(f"{_path}:{_ln} — {_flat[:70]}")

check("کوئری‌های مستاجری پیدا شدند", _checked > 60, f"{_checked} کوئری")
check("همه به مستاجر محدودند", not _leaks,
      f"{len(_leaks)} بدون شرط" if _leaks else f"{_checked} کوئری")
if _leaks:
    bullets(_leaks)



# ═══════════════════════════════════════════════════════════
#  درز — SQL ساخته‌شده با درج رشته
# ═══════════════════════════════════════════════════════════
head("درز · درجِ رشته در SQL")

# مقدارها همیشه با ? پارامتر می‌شوند، ولی *نام* جدول و ستون را
# نمی‌شود پارامتر کرد — پس چند جا با f-string ساخته می‌شوند.
#
# تا وقتی آن نام‌ها از خود کد بیایند (فهرست ثابت، فهرست سفید، یا
# اسکیمای دیتابیس) هیچ مشکلی نیست. خطر جایی است که چیزی از بدنه‌ی
# درخواست مستقیم داخل کوئری بنشیند.

#: نام‌هایی که یعنی «این از بیرون آمده».
REQUEST_ISH = ("payload", "request", "body", "form", "params",
               "user_input", "raw_input")

SQL_KW = re.compile(
    r"\b(SELECT|INSERT INTO|UPDATE|DELETE FROM|ALTER TABLE|PRAGMA)\b", re.I)

_interp, _risky = 0, []
for _path in ("backend/app.py", "bot/db.py", "bot/handlers.py",
              "backend/tunnels.py"):
    _src = io.open(os.path.join(ROOT, _path), encoding="utf-8").read()
    for _n in ast.walk(ast.parse(_src)):
        if not isinstance(_n, ast.JoinedStr):
            continue
        _lit = " ".join(v.value for v in _n.values
                        if isinstance(v, ast.Constant)
                        and isinstance(v.value, str))
        if not SQL_KW.search(_lit):
            continue
        _interp += 1
        for _v in _n.values:
            if not isinstance(_v, ast.FormattedValue):
                continue
            _expr = ast.unparse(_v.value)
            if any(r in _expr.lower() for r in REQUEST_ISH):
                _risky.append(f"{_path}:{_n.lineno} — {{{_expr}}}")

check("کوئری‌های درج‌شده پیدا شدند", _interp > 15, f"{_interp} کوئری")
check("هیچ‌کدام مقدارِ درخواست را داخل SQL نمی‌گذارند", not _risky,
      f"{len(_risky)} مورد" if _risky else f"{_interp} کوئری بررسی شد")
if _risky:
    bullets(_risky)



# ═══════════════════════════════════════════════════════════
#  درز — مسیر فایل‌ها در نصب، کد، و CLI
# ═══════════════════════════════════════════════════════════
head("درز · مسیر داده‌ها")

# سه جا باید درباره‌ی محل فایل‌ها یک حرف بزنند: install.sh که متغیرها
# را در سرویس systemd می‌نویسد، کدی که پیش‌فرض‌ها را دارد، و
# nexora-cli که موقع نسخه‌برداری همان‌جا را می‌گردد.
#
# اگر از هم فاصله بگیرند، پنل جایی می‌نویسد که نسخه‌بردار نگاه
# نمی‌کند — و روزی که به پشتیبان نیاز باشد، خالی است.

INSTALL_SH = rd("install.sh")
CLI_SH = rd("nexora-cli.sh")

# متغیرهایی که کد می‌خواند
_read_env = set(re.findall(r'getenv\("([A-Z_]+)"', APP_PY + rd("bot/db.py")
                           + rd("backend/tunnels.py")))
check("متغیرهای محیطی کد پیدا شدند", len(_read_env) > 8,
      f"{len(_read_env)} متغیر")

# آن‌هایی که *باید* در نصب تنظیم شوند، چون پیش‌فرضشان نسبی است
MUST_SET = {"CONFIG_PATH", "AUTH_PATH", "SUBPAGE_HTML_PATH",
            "TUNNEL_DB_PATH", "BOT_DB_PATH"}
_unset = [v for v in MUST_SET if f'{v}=' not in INSTALL_SH]
check("نصب همه‌ی مسیرهای لازم را تنظیم می‌کند", not _unset,
      "، ".join(_unset) if _unset else f"{len(MUST_SET)} متغیر")

# دیتابیس‌ها باید کنار هم در data/ باشند — همان‌جا که CLI می‌گردد
for _db in ("bot.db", "billing.db", "tunnels.db"):
    check(f"«{_db}» در نسخه‌برداری هست", f"{_db}" in CLI_SH,
          "وگرنه پشتیبان بدون آن ساخته می‌شود")

check("نصب، داده را در data/ کنار نصب می‌گذارد",
      "CONFIG_PATH=$INSTALL_DIR/data/config.json" in INSTALL_SH,
      "پیش‌فرض billing.db و bot.db از کنار همین ساخته می‌شود")
check("و CLI هم همان‌جا را می‌گردد",
      '"$INSTALL_DIR/data/$db"' in CLI_SH
      or '$INSTALL_DIR/data/bot.db' in CLI_SH,
      "سه جا باید یک حرف بزنند")



# ═══════════════════════════════════════════════════════════
#  درز — متغیری که هیچ‌جا مقدار نگرفته
# ═══════════════════════════════════════════════════════════
head("درز · متغیر بی‌مقدار در تابع")

# همان خانواده‌ی بالا، ولی یک پله نزدیک‌تر: نه ماژول جاافتاده، بلکه
# متغیری که *در تابعِ دیگری* مقدار می‌گیرد و این‌جا بی‌مقدار خوانده
# می‌شود. پایتون تا لحظه‌ی اجرا چیزی نمی‌گوید، و چون این خط معمولاً
# پشت یک شرط است — «اگر ادمین رد کرد»، «اگر پورت حیاتی بود» — تست‌های
# معمولی هم از کنارش رد می‌شوند.
#
# سه بار همین اتفاق افتاد: یک‌بار در مسیر تایید سفارش از گروه ادمین،
# دوبار وقتی یک مقدار مشترک را به چند تابع بردم و در یکی‌شان تعریفش
# را جا انداختم. هر سه فقط وقتی خودشان را نشان می‌دادند که کاربر
# دقیقاً همان دکمه را می‌زد.

PYFILES = [
    "backend/app.py", "backend/monitor.py", "backend/firewall.py",
    "backend/netid.py", "backend/tunnels.py", "backend/health.py",
    "backend/intrusion.py", "backend/fx.py", "bot/handlers.py",
    "bot/db.py", "bot/core.py", "bot/xui.py", "bot/tg.py", "bot/run.py",
    "bot/fmt.py", "bot/qr.py", "agent/nexora-agent.py",
]

import builtins as _bi
_BUILTIN = set(dir(_bi)) | {"__file__", "__name__", "__doc__", "__spec__"}


def _bound_in(node):
    """هر نامی که در این زیردرخت مقدار می‌گیرد — سخاوتمندانه."""
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            out.add(n.id)
        elif isinstance(n, ast.Import):
            for a in n.names:
                out.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                out.add(a.asname or a.name)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                            ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            out.update(n.names)
        elif isinstance(n, (ast.arg,)):
            out.add(n.arg)
    return out


unbound = []
for rel in PYFILES:
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        continue
    try:
        tree = ast.parse(io.open(path, encoding="utf-8").read())
    except SyntaxError:
        continue

    # نام‌های سطح ماژول: هر چیزی که بیرون توابع مقدار می‌گیرد
    modscope = set(_BUILTIN)
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            modscope.add(n.name)
        else:
            modscope |= _bound_in(n)

    # فقط توابع سطح بالا و متدها — تابع تودرتو داخل همین زیردرخت است
    funcs = [n for n in tree.body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        funcs += [n for n in cls.body
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

    for fn in funcs:
        bound = modscope | _bound_in(fn)
        for stmt in fn.body:
            for n in ast.walk(stmt):
                if (isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
                        and n.id not in bound):
                    unbound.append(f"{rel}:{n.lineno} — {n.id} در {fn.name}()")

check("هر متغیری که خوانده می‌شود جایی مقدار گرفته", not unbound,
      f"{len(unbound)} مورد" if unbound
      else f"{len(PYFILES)} فایل — NameError پشت شرط پنهان نمانده")
if unbound:
    bullets(unbound)


# ═══════════════════════════════════════════════════════════
print(f"\n{D}{'─' * 54}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
if not _fail:
    print(f"  {D}هر دو سمت همه‌ی درزها با هم می‌خوانند{X}")
print()
sys.exit(1 if _fail else 0)
