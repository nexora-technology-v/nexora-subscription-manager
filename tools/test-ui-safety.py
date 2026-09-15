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
# ═══════════════════════════════════════════════════════════
head("فهرست بلند باید صفحه‌بندی شود، نه اینکه همه‌اش ریخته شود")

# سرور ایران نزدیک هشتصد سوکت باز دارد. کارت «پورت‌های باز» دو راه
# داشت که هر دو کل فهرست را یک‌جا می‌ریختند: با فیلتر فعال هیچ سقفی
# نبود، و دکمه‌ی «نمایش همه‌ی N پورت» هم همه را باز می‌کرد. نتیجه یک
# جدول هشتصد ردیفی در یک کارت بود.
#
# LongList صفحه‌بندی عددی دارد — همان چیزی که لازم است — ولی این
# کارت از آن استفاده نمی‌کرد.

MON = io.open(os.path.join(ROOT, "frontend", "src", "sections",
                           "monitoring.jsx"), encoding="utf-8").read()
_ports = MON[MON.index("export function PortsCard"):]
_ports = _ports[:_ports.index("\nexport function")]

check("کارت پورت‌ها صفحه‌بندی دارد", "<LongList" in _ports,
      "همان کامپوننتی که بقیه‌ی فهرست‌های بلند استفاده می‌کنند")
# دنبال خودِ دکمه می‌گردیم، نه متن — وگرنه توضیحِ همین اصلاح هم
# به‌عنوان دکمه شمرده می‌شود
check("و دکمه‌ی «نمایش همه» ندارد",
      "faNum(ports.length)} پورت" not in _ports,
      "«نمایش بیشتر» فهرست را بلندتر می‌کند — دقیقاً همان مشکل")
check("کارت مشتری‌ها هم صفحه‌بندی شد",
      "نمایش همه‌ی ${faNum(d.clients.length)} مشتری" not in MON
      and "items={list} initial={6}" in MON,
      "فهرست مشتری‌ها با رشد کسب‌وکار بلندتر می‌شد")
check("و حالتِ all جایی نمانده", "const [all, setAll]" not in MON,
      "وضعیتی که دیگر خوانده نمی‌شود فقط گمراه‌کننده است")
check("و حالتِ بی‌سقف هم ندارد",
      "setAll" not in _ports and "const [all," not in _ports)
check("پرخطرها هنوز اول می‌آیند",
      "[...risky, ...low]" in _ports,
      "صفحه‌ی اول باید همان چیزی باشد که باید به آن رسیدگی شود")

UI = io.open(os.path.join(ROOT, "frontend", "src", "ui", "index.jsx"),
             encoding="utf-8").read()
check("LongList می‌تواند ظرف دلخواه بگیرد", "container" in UI,
      "ردیف جدول باید داخل tbody بنشیند، نه داخل div")
check("و صفحه‌بندی‌اش عددی است", "Pager page={cur}" in UI)

# هر فهرستی که از داده‌ی سرور می‌آید و مستقیم map می‌شود، بالقوه
# بی‌سقف است. این‌ها را می‌شماریم تا کارت تازه‌ای همان اشتباه را
# تکرار نکند.
_unbounded = []
for _name in ("sec.processes", "sec.services", "conn.byIp"):
    if f"{_name}.map(" in MON:
        _unbounded.append(_name)
FW = io.open(os.path.join(ROOT, "frontend", "src", "sections",
                          "firewall.jsx"), encoding="utf-8").read()
check("جدول قاعده‌های فایروال هم صفحه‌بندی شد",
      "items={rules} initial={12}" in FW and "rules.map(" not in FW,
      "روی سروری با ده‌ها قاعده، جدول تا ته صفحه می‌رفت")

INT = io.open(os.path.join(ROOT, "frontend", "src", "sections",
                           "intrusion.jsx"), encoding="utf-8").read()
check("جدول تلاش‌های نفوذ صفحه‌بندی دارد", "usePager(shown, 15)" in INT)

check("فهرست‌های بلندِ دیگر هم مستقیم map نمی‌شوند", not _unbounded,
      "، ".join(_unbounded) if _unbounded else "همه از LongList رد می‌شوند")

# پنل نماینده اپلیکیشن جداست و از این اسکن بیرون می‌ماند — و دقیقاً
# به همین دلیل، جدول کانفیگ‌هایش تا امروز همه‌ی ردیف‌ها را یک‌جا
# می‌ریخت. نماینده‌ای با صدها کانفیگ صفحه‌ای می‌دید که ته نداشت.
PORTAL = ALL.get("portal/index.jsx", "")
check("پنل نماینده هم خوانده شد", len(PORTAL) > 1000, f"{len(PORTAL)} نویسه")
# ادعا روی همان جدول، نه روی هر map در فایل: فهرست پلن‌های ربات
# کوتاه و کران‌دار است و صفحه‌بندی‌اش بی‌معنی.
_dash = PORTAL[PORTAL.index("function Dashboard("):] if "function Dashboard(" in PORTAL else ""
check("جدول کانفیگ‌های نماینده صفحه‌بندی دارد",
      "usePager(rows, 15)" in _dash and "{pageRows.map(" in _dash
      and "{rows.map(" not in _dash,
      "باید برشِ صفحه را map کند، نه کل فهرست را")
check("و کنترل صفحه‌بندی هم رندر می‌شود", "{pager}" in PORTAL)
check("فهرست سفارش‌های نماینده هم صفحه‌بندی دارد",
      "usePager(rows || [], 12)" in PORTAL and "{ordersPager}" in PORTAL,
      "سفارش‌ها با گذر زمان بی‌سقف می‌شوند")
check("و بریده‌شدنِ فهرست بی‌صدا نمی‌ماند", "truncated" in PORTAL,
      "نماینده نباید فکر کند همین‌ها همه‌ی سفارش‌هایش است")
check("فیلتر وضعیت هم دارد", "const FILTERS" in PORTAL and "passes(c)" in PORTAL,
      "جست‌وجوی نام به‌تنهایی «کدام‌ها رو به اتمام‌اند» را جواب نمی‌دهد")


# ═══════════════════════════════════════════════════════════
head("جعبه‌ی راهنما نباید به چیزِ زیرش بچسبد")

# InfoBox فقط mt-4 داشت و هیچ فاصله‌ای از پایین. اندازه‌گیری روی
# صفحه‌ی زنده: صفر پیکسل تا عنصر بعدی. و این کامپوننت بیش از صد بار
# در نوزده صفحه به کار رفته، پس همه‌جا همین‌طور بود.
#
# last:mb-0 برای وقتی است که آخرین عنصرِ یک کارت باشد — آن‌جا فاصله‌ی
# پایین فقط فضای خالیِ اضافه می‌سازد، که خودش ایراد دیگری است.
_ib = UI[UI.index("export function InfoBox("):]
_ib = _ib[:_ib.index("export function", 10)]
check("InfoBox از بالا و پایین فاصله دارد", "my-4" in _ib,
      "با mt-4 تنها، هر چیزی که زیرش بیاید چسبیده است")
check("و وقتی آخرین عنصر است فاصله‌ی اضافه نمی‌گذارد",
      "last:mb-0" in _ib, "وگرنه ته کارت فضای خالی می‌ماند")


# ═══════════════════════════════════════════════════════════
head("فرمِ باز‌شونده نباید داخل ردیفِ دکمه‌ها بنشیند")

# فرمِ «نماینده‌ی جدید» داخل یک ردیفِ flex justify-between رندر
# می‌شد که برای دکمه‌هاست. نتیجه: فرم فقط یک ستون از عرض را
# می‌گرفت و کنارش یک ستونِ خالیِ بزرگ می‌ماند.
_pa2 = ALL.get("sections/portal-admin.jsx", "")
_btn_row = _pa2[_pa2.index('className="flex justify-between items-center gap-2 mb-3 flex-wrap"'):]
_btn_row = _btn_row[:_btn_row.index("</div>")]
check("فرم داخل ردیفِ دکمه‌ها نیست", "<NewReseller" not in _btn_row,
      "ردیفِ flex عرض را می‌شکند و کنارش خالی می‌ماند")
check("و بیرون از آن، تمام‌عرض رندر می‌شود",
      "{adding && (" in _pa2 and "<NewReseller" in _pa2)


# ═══════════════════════════════════════════════════════════
head("مقدارِ ثبت‌شده نباید از منوی انتخاب غیب شود")

# فهرست گروه‌ها از x-ui می‌آید. اگر گروهِ ثبت‌شده‌ی یک نماینده در آن
# فهرست نباشد — پنل در دسترس نباشد، یا گروه در x-ui عوض شده باشد —
# select مقدارِ بی‌گزینه را نشان نمی‌دهد و روی «انتخاب کنید»
# می‌افتد. یعنی نماینده‌ای که گروه دارد «بدون گروه» دیده می‌شود، و
# کافی است پنل یک لحظه قطع باشد تا همه‌ی نماینده‌ها همین‌طور شوند.
PADM = ALL.get("sections/portal-admin.jsx", "")
check("صفحه‌ی نمایندگی خوانده شد", len(PADM) > 1000, f"{len(PADM)} نویسه")
check("گروهِ ثبت‌شده حتی بیرون از فهرست هم گزینه می‌شود",
      "!(groups || []).includes(group)" in PADM
      and "<option value={group}>" in PADM,
      "وگرنه select روی «انتخاب کنید» می‌افتد و صفحه دروغ می‌گوید")


# ═══════════════════════════════════════════════════════════
head("یک بخش نباید دو بار رندر شود")

# اسکریپتِ وصله روی ("App.jsx", "app.jsx") حلقه زد. ویندوز به بزرگی
# و کوچکی حروف حساس نیست، پس هر دو یک فایل بودند و خطِ مسیر دو بار
# اضافه شد — صفحه‌ی اینباند نماینده‌ها دو بار پشت سر هم رندر می‌شد.
_routes = re.findall(r'\{active === "([a-z0-9-]+)" &&', APP)
_dupe = sorted({k for k in _routes if _routes.count(k) > 1})
check("هیچ مسیری دو بار وصل نشده", not _dupe,
      "، ".join(_dupe) if _dupe else f"{len(_routes)} مسیر، همه یکتا")


# ═══════════════════════════════════════════════════════════
head("متن فارسی داخل فیلدِ چپ‌به‌راست دیده نمی‌شود")

# روی input، جهت از *مقدار* گرفته می‌شود نه placeholder — پس فیلدی
# که dir="ltr" دارد، placeholder فارسی‌اش را چپ‌به‌راست می‌چیند. و
# فونت mono هم حرف فارسی ندارد.
#
# قاعده‌ی خودِ مخزن در بیشتر جاها رعایت شده: فارسی در label و hint،
# و placeholder یک نمونه‌ی خنثی.
_FA = re.compile(r"[\u0600-\u06ff]")
_bad_ph = []
for _name, _src in ALL.items():
    if not _name.endswith((".jsx", ".js")):
        continue
    for _m in re.finditer(r'placeholder="([^"]*)"', _src):
        _txt = _m.group(1)
        # فقط حروف فارسی مهم است؛ رقم فارسی جهت‌پذیر نیست
        if not re.search(r"[\u0620-\u064a\u067e\u0686\u0698\u06af\u06cc]",
                         _txt):
            continue
        # از نزدیک‌ترین «<» عقب‌تر تا خودِ placeholder — داخلِ یک تگ
        # می‌ماند، چون تگ نمی‌تواند «<» داشته باشد
        _open = _src.rfind("<", 0, _m.start())
        _tag = _src[_open:_m.start()]
        if 'dir="ltr"' in _tag or "var(--mono)" in _tag:
            _bad_ph.append(f"{_name}:{_src[:_m.start()].count(chr(10)) + 1}")

check("placeholder فارسی روی فیلد چپ‌به‌راست نمانده", not _bad_ph,
      "، ".join(_bad_ph) if _bad_ph
      else "فارسی در label می‌نشیند، نه در placeholder")


print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
