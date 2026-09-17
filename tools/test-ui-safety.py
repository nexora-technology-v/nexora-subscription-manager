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
        # خودِ مسیر هم یک گزینه است: وقتی import پسوند را صریح
        # نوشته باشد (`./lib/route.js`)، چسباندنِ پسوند دوباره
        # دنبال `route.js.js` می‌گشت و ماژولِ سالم را «پیدا نشد»
        # گزارش می‌کرد — یعنی یک هشدار دروغ که هشدارهای واقعی را
        # بی‌ارزش می‌کند.
        cand = [target, target + ".jsx", target + ".js",
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



# ═══════════════════════════════════════════════════════════
head("CSS · دو قاعده نباید بی‌صدا همدیگر را پاک کنند")

# `.fx-card` و `.fx-kpi` روی یک عنصر با هم می‌آیند. اگر هر دو
# `::before` بسازند، هرکدام دیرتر در فایل بیاید دیگری را پاک
# می‌کند — بدون هیچ خطایی، فقط یک افکت که ناپدید می‌شود.
_PAIRS = [("fx-card", "fx-kpi"), ("fx-card", "fx-sk")]
_clash = []
for _a, _b in _PAIRS:
    for _pseudo in ("::before", "::after"):
        _ra = re.search(r"^\.%s%s\s*\{" % (_a, _pseudo), CSS, re.M)
        _rb = re.search(r"^\.%s%s\s*\{" % (_b, _pseudo), CSS, re.M)
        if _ra and _rb:
            _clash.append("%s + %s هر دو %s" % (_a, _b, _pseudo))
check("کلاس‌هایی که با هم می‌آیند، یک شبه‌عنصر را دو بار نمی‌سازند",
      not _clash, "، ".join(_clash) if _clash
      else "کارت از ::before، شاخص از ::after")

# و هر عنصری که شبه‌عنصرِ مطلق دارد باید خودش جایگاه داشته باشد،
# وگرنه آن شبه‌عنصر روی نزدیک‌ترین والدِ جایگاه‌دار می‌نشیند و کلِ
# صفحه را می‌گیرد
for _cls in ("fx-card", "fx-kpi"):
    _blk = re.search(r"^\.%s\s*\{([^}]*)\}" % _cls, CSS, re.M)
    _all = "".join(m.group(1) for m in
                   re.finditer(r"^\.%s\s*\{([^}]*)\}" % _cls, CSS, re.M))
    check("%s جایگاه دارد" % _cls,
          "position: relative" in _all or "position:relative" in _all,
          "شبه‌عنصرِ absolute بدون آن، از کارت بیرون می‌زند")



# ═══════════════════════════════════════════════════════════
head("حالت خالی · یک قاعده، یک جا")

# بیست جا همان شکل را دستی ساخته بودند — کارتِ نقطه‌چین، آیکونِ
# کم‌رنگ، یک جمله. یعنی بهترکردنِ کامپوننت مشترک هیچ‌کدامشان را عوض
# نمی‌کرد. همان باگی که این مخزن هشت بار دیده: یک قاعده، چند جا.
_hand = []
for _n, _s in ALL.items():
    if _n.endswith("ui/index.jsx"):
        continue
    for _m in re.finditer(r'className="fx-card p-\d+ text-center"[^>]*'
                          r'borderStyle: "dashed"', _s):
        _hand.append(f"{_n}:{_s[:_m.start()].count(chr(10)) + 1}")

check("هیچ حالت خالیِ دست‌سازی نمانده", not _hand,
      "، ".join(_hand[:4]) if _hand else "همه از EmptyState یا کلاس مشترک")

check("کامپوننت حالت خالی وجود دارد", "export function EmptyState" in UI)
check("و آیکونش داخل یک مربع می‌نشیند", "fx-empty-ico" in UI and ".fx-empty-ico" in CSS,
      "آیکونِ تنهای کم‌رنگ شبیه «چیزی بارگذاری نشد» بود")
check("و نبودنِ آیکون چیزی را نمی‌شکند", "Icon ? <Icon" in UI,
      "وگرنه «Element type is invalid» و سقوط همان بخش")

_users = [n for n, s in ALL.items() if "<EmptyState" in s]
check("و واقعاً همه‌جا استفاده می‌شود", len(_users) >= 14, f"{len(_users)} فایل")


head("چیدمان · کارتِ کوتاه تمام‌عرض نمی‌شود")

# سه صفحه یک ستون از کارت‌های ۹۷۰ پیکسلی بودند که هرکدام یک کادر
# سه‌خطی داشتند. اندازه‌گیری‌شده: متن‌های ربات ۲۳۲۴ پیکسل بلند.
check("گریدِ دوستونیِ مساوی تعریف شده", ".fx-g2-even" in CSS)
check("و روی موبایل یک‌ستونه می‌شود",
      re.search(r"@media \(max-width: 900px\)[^}]*\{[^}]*\.fx-g2-even", CSS, re.S) is not None
      or ".fx-g2-even { grid-template-columns: 1fr; }" in CSS)
check("متن‌های ربات دو ستونه است", "fx-g2-even" in ALL.get("sections/bot/texts.jsx", ""))
check("سوالات متداول هم", "fx-g2-even" in ALL.get("sections/subpage.jsx", ""))
check("و سرورهای تانل گرید گرفته‌اند",
      "minmax(300px,1fr)" in ALL.get("sections/tunnel.jsx", ""))

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


# ═══════════════════════════════════════════════════════════
head("جهت و قلم · فارسی داخل ظرفِ چپ‌به‌راست یا مونو")

# سه چیز اندازه‌گیری‌شده، نه حدس:
#
#   • dir="ltr" جای عدد و واحدش را عوض می‌کند. «۸۳ روز» روی صفحه
#     «روز ۸۳» خوانده می‌شود.
#   • JetBrains Mono هیچ گلیف فارسی ندارد، پس حرف‌های فارسی به مونوی
#     سیستم می‌افتند: «اعتبار» ۷۱٪ پهن‌تر از قلمِ خودِ پنل، «تومان»
#     ۳۱٪ — درست وسط یک عدد.
#   • و ارقام فارسی باید در مونو بمانند، چون ستون‌های جدول با آن
#     هم‌تراز می‌شوند (در مونو همه ۲۴٫۰۱ پیکسل، در قلم اصلی ۱۴٫۵ تا
#     ۲۷٫۱). پس راه‌حل «فارسی را به زنجیره‌ی مونو اضافه کن» رد شد.
#
# این باگ در دو صفحه‌ی جدا پیدا شد — داشبورد حسابداری و «واسطه‌ها و
# نرخ» — با یک متنِ تقریباً یکسان. همان الگویی که این مخزن هفت بار
# دیده: یک قاعده، دو جا، اصلاح در یکی.
#
# راه فرار: کلاس fx-fa-sub (جهت و قلم را برمی‌گرداند) یا <bdi>.
#
# چیزی که این تست *نمی‌تواند* بگیرد: فارسیِ داده‌ای. `{g.name}` وقتی
# نامِ گروه «بدون گروه» باشد همان مشکل را دارد، ولی در فایل هیچ حرف
# فارسی‌ای دیده نمی‌شود. برای آن‌ها قرارداد این است که هر شناسه‌ای که
# کاربر می‌نویسد (نام گروه، ایمیل کانفیگ) داخل <bdi> و با monoIf()
# بنشیند — و همین تست، اگر کسی <bdi> را بردارد و کنارش متن فارسی
# باشد، قرمز می‌شود.

_FA_LETTER = re.compile(r"[\u0620-\u064A\u066E-\u06D3\u06EE\u06EF"
                        r"\u06FA-\u06FF]")
#: راه‌های اعلامِ «این‌جا حواسم بود»
#  fx-fa-sub  → جهت و قلم را برمی‌گرداند
#  <bdi       → متنِ دوجهته را جدا نگه می‌دارد
#  monoIf(    → مونو را فقط به شناسه‌ی لاتین می‌دهد
#  fx-ltr-ok  → چپ‌به‌راست عمدی است (نمودار جریان)
_ESCAPE = ("fx-fa-sub", "<bdi", "monoIf(")
_TAG_ESCAPE = ("fx-ltr-ok",)

def _walk_jsx(src):
    """
    پشته‌ی تگ‌ها را می‌پیماید و هر متنِ فارسی را با ظرفش گزارش می‌کند.

    چرا پشته و نه regex روی بدنه: دو <span> تودرتو هم‌نام‌اند، پس
    «تا اولین </span>» بدنه را وسط می‌برد. و وقتی راه فرار را
    «هرجای بدنه» گرفتم، شکستنِ عمدی نشان داد یک <bdi> در گوشه‌ی
    بدنه، فارسیِ بیرونِ خودش را هم معاف می‌کند.

    برمی‌گرداند: (شماره‌ی خط, توضیح ظرف) برای هر تخلف.
    """
    out, stack, i, n = [], [], 0, len(src)
    while i < n:
        lt = src.find("<", i)
        if lt < 0:
            lt = n
        text = src[i:lt]
        if text and _FA_LETTER.search(text):
            # عمیق‌ترین ظرفی که جهت یا قلم را تحمیل می‌کند
            hard = max((k for k, f in enumerate(stack) if f["hard"]),
                       default=None)
            safe = max((k for k, f in enumerate(stack) if f["safe"]),
                       default=None)
            if hard is not None and (safe is None or safe < hard):
                out.append((src[:i].count(chr(10)) + 1, stack[hard]["desc"]))
        i = lt
        if i >= n:
            break
        if src.startswith("</", i):
            gt = src.find(">", i)
            if gt < 0:
                break
            if stack:
                stack.pop()
            i = gt + 1
            continue
        m = re.match(r"<([A-Za-z][\w.]*)", src[i:])
        if not m:
            i += 1
            continue
        # تا بستنِ تگِ باز، با شمردن آکولاد — صفت‌ها {{…}} دارند
        j, depth = i + m.end(), 0
        while j < n:
            c = src[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            elif c == ">" and depth == 0:
                break
            j += 1
        attrs = src[i + m.end():j]
        self_close = attrs.rstrip().endswith("/")
        tag = m.group(1)
        hard = ('dir="ltr"' in attrs or "var(--mono)" in attrs) \
            and not any(e in attrs for e in _TAG_ESCAPE)
        safe = (tag == "bdi" or "fx-fa-sub" in attrs or "monoIf(" in attrs)
        if not self_close:
            stack.append({
                "hard": hard, "safe": safe,
                "desc": "<%s%s>" % (tag, re.sub(r"\s+", " ", attrs)[:44]),
            })
        i = j + 1
    return out


_bidi = []
for _name, _src in ALL.items():
    if not _name.endswith(".jsx"):
        continue
    # کامنت‌ها با تعداد خطِ برابر جایگزین می‌شوند، وگرنه شماره‌ی خطی
    # که گزارش می‌شود با فایل نمی‌خواند و آدم را به جای اشتباه می‌برد
    _flat = re.sub(r"\{/\*.*?\*/\}",
                   lambda m: "\n" * m.group(0).count("\n"), _src, flags=re.S)
    for _line, _desc in _walk_jsx(_flat):
        _bidi.append("%s:%d %s" % (_name, _line, _desc))

check("حرف فارسی داخل dir=ltr یا مونو نمانده", not _bidi,
      "، ".join(_bidi[:6]) if _bidi
      else "هر کدام یا fx-fa-sub دارند یا داخل bdi نشسته‌اند")

# و خودِ راه فرار باید وجود داشته باشد، وگرنه تست بالا با حذف کلاس
# هم سبز می‌ماند
_css = ALL.get("index.css") or io.open(
    os.path.join(SRC, "index.css"), encoding="utf-8").read()
check("کلاس fx-fa-sub تعریف شده", ".fx-fa-sub" in _css
      and "--sans" in _css, "جهت rtl و قلم اصلی را برمی‌گرداند")


# ═══════════════════════════════════════════════════════════
head("دکمه‌ی آیکونی · هر دکمه‌ای باید بگوید چه می‌کند")

# دکمه‌ی بی‌متن و بی‌tooltip کاربر را به حدس‌زدن وامی‌دارد، و ۱۲ تا از
# اینها دکمه‌ی «حذف» بودند. پنل ۳۳ دکمه را از قبل همین‌طور برچسب زده
# بود؛ بقیه جا مانده بودند.

_ICON = re.compile(r"<([A-Z][A-Za-z0-9]*)\s+size=")
_nolabel = []
for _name, _src in ALL.items():
    if not _name.endswith(".jsx"):
        continue
    for _m in re.finditer(r"<button\b", _src):
        _i, _depth = _m.end(), 0
        while _i < len(_src):
            _ch = _src[_i]
            if _ch == "{":
                _depth += 1
            elif _ch == "}":
                _depth -= 1
            elif _ch == ">" and _depth == 0:
                break
            _i += 1
        _open_tag = _src[_m.start():_i + 1]
        _close = _src.find("</button>", _i)
        _body = _src[_i + 1:_close] if _close > 0 else ""
        _inner = re.sub(r"<[^>]*>", "", _body)
        # متنِ ثابت
        _txt = re.sub(r"\{[^{}]*\}", "", _inner).strip()
        # و متنِ پویا: `{copied ? "کپی شد" : "کپی لینک"}` یا `{label}`
        # هم برچسب‌اند و کاربر می‌بیندشان. بدون این، هر دکمه‌ای که
        # متنش شرطی باشد «فقط‌آیکون» شمرده می‌شد — دو مورد در مینی‌اپ
        # همین‌طور بی‌دلیل قرمز شدند.
        if not _txt:
            for _e in re.findall(r"\{([^{}]*)\}", _inner):
                if re.search(r'"[^"]*[^\W\d_][^"]*"', _e) or \
                        re.fullmatch(r"\s*[a-z]\w*\s*", _e):
                    _txt = "(پویا)"
                    break
        if _txt or not _ICON.search(_body):
            continue
        if "title=" in _open_tag or "aria-label" in _open_tag:
            continue
        _nolabel.append("%s:%d" % (_name, _src[:_m.start()].count(chr(10)) + 1))

check("هر دکمه‌ی فقط‌آیکون برچسب دارد", not _nolabel,
      "، ".join(_nolabel[:6]) if _nolabel
      else "title یا aria-label روی همه هست")


# ═══════════════════════════════════════════════════════════
head("زبان · واحدِ انگلیسی در رابطی که فارسی است")

# دو خط در دو صفحه‌ی جدا این شکلی بودند:
#
#     {g.name} · {g.configs} config · {g.months} months
#
# در حالی که سرستونِ همان جدول «ماه» می‌نوشت و جای دیگرِ همان فایل
# «{faNum(it.months)} ماه». یعنی واژه‌ها فارسیِ خودشان را داشتند و
# فقط این دو خط جا مانده بودند.
#
# فقط متنِ رندرشده شمرده می‌شود، نه کد: «config» ۱۲۶ بار در مخزن هست
# و تقریباً همه‌اش نام متغیر یا مسیر API است.

#: واژه‌هایی که معادل فارسی‌شان همین حالا جای دیگرِ پنل به کار می‌رود
_EN_UNITS = re.compile(r"\b(configs?|months?|days?|used|renewals?)\b", re.I)

_en = []
for _name, _src in ALL.items():
    if not _name.endswith(".jsx"):
        continue
    _flat = re.sub(r"\{/\*.*?\*/\}",
                   lambda m: "\n" * m.group(0).count("\n"), _src, flags=re.S)
    # متنِ بینِ تگ‌ها، بدونِ عبارت‌های {…}
    for _m in re.finditer(r">([^<>]{1,200})<", _flat):
        _txt = _m.group(1)
        # آکولادهای تودرتو را لایه‌لایه برمی‌داریم؛ یک regex ساده
        # `\{[^{}]*\}` از پسِ {a && (b ? c : d)} برنمی‌آید و تکه‌ای از
        # کد را به‌عنوان «متن» تحویل می‌دهد
        for _ in range(6):
            _new = re.sub(r"\{[^{}]*\}", "", _txt)
            if _new == _txt:
                break
            _txt = _new
        # اگر هنوز نشانه‌ی کد دارد، این «متنِ نمایشی» نبوده
        if re.search(r"[{}();=]|&&|=>", _txt):
            continue
        if not _EN_UNITS.search(_txt):
            continue
        _en.append("%s:%d — %s" % (
            _name, _flat[:_m.start()].count(chr(10)) + 1,
            re.sub(r"\s+", " ", _txt).strip()[:44]))

check("واحدِ انگلیسی در متنِ نمایشی نمانده", not _en,
      "، ".join(_en[:5]) if _en
      else "«کانفیگ» و «ماه» و «مصرف» همه‌جا فارسی‌اند")


# ═══════════════════════════════════════════════════════════
head("اندازه‌ی قلم · کلاسی که نوشته می‌شود باید اثر کند")

# `.fx-stat-num` در index.css اندازه و وزن را می‌گذاشت و دیرتر از
# کلاس‌های تیلویند می‌آمد، پس با ویژگیِ برابر برنده می‌شد. نتیجه: سه
# جا `fx-stat-num text-[21px] font-extrabold` نوشته شده بود و هیچ‌کدام
# کار نمی‌کرد — ۳۲ پیکسل (و در موبایل ۲۸) رندر می‌شد و عددِ میلیونی از
# کارت بیرون می‌زد. با :where ویژگی صفر می‌شود و هر اندازه‌ی صریحی در
# JSX برنده است.
check("اندازه‌ی fx-stat-num با :where قابل بازنویسی است",
      ":where(.fx-stat-num)" in _css,
      "وگرنه text-[..] کنارش بی‌اثر می‌شود")

# قاعده‌ی واقعی: هیچ‌جا `.fx-stat-num` بدونِ :where نباید font-size
# بگذارد — نه در قاعده‌ی اصلی، نه داخل مدیاکوئری. شمردنِ همه‌شان از
# خواندنِ یک مدیاکوئریِ مشخص مطمئن‌تر است، چون فردا مدیاکوئریِ دیگری
# اضافه می‌شود و تستِ نقطه‌ای آن را نمی‌بیند.
_bare_size = []
for _m in re.finditer(r"(:where\()?\.fx-stat-num\)?\s*\{([^}]*)\}", _css):
    if "font-size" in _m.group(2) and not _m.group(1):
        _bare_size.append(re.sub(r"\s+", " ", _m.group(2)).strip()[:40])
check("هیچ قاعده‌ی fx-stat-num بدون :where اندازه نمی‌گذارد",
      not _bare_size, "، ".join(_bare_size) if _bare_size
      else "پیش‌فرض‌ها صفر-ویژگی‌اند و text-[..] بر آن‌ها غلبه می‌کند")



# ═══════════════════════════════════════════════════════════
head("فیلد عددی · کاربر فارسی باید بتواند رقم بزند")

# `<input type="number">` هر چیزی جز رقمِ لاتین را **بی‌صدا دور
# می‌ریزد**. در مرورگر اندازه گرفته شد:
#
#     تایپ «۱۲۳»    →  value === ""
#     تایپ «۱۲٬۳۴۵» →  value === ""
#     تایپ «1,234»  →  value === ""
#
# یعنی کاربر فارسی رقم می‌زند و هیچ چیزی در فیلد ظاهر نمی‌شود؛ نه
# خطایی، نه پیامی. و فلش‌های بالا/پایینش هم در چیدمان راست‌به‌چپ سر
# جای درستی نمی‌نشستند.
#
# جایگزین NumberInput است: type=text با inputMode عددی، و
# نرمال‌سازی در همان مرز. چیزی که به onChange و بعد به بکند می‌رسد
# همان رشته‌ی لاتینِ قبلی است — قرارداد عوض نشده، فقط دیگر خالی
# نمی‌ماند.

_num_inputs = []
for _name, _src in ALL.items():
    if not _name.endswith(".jsx"):
        continue
    for _m in re.finditer(r"<input\b", _src):
        _i, _d = _m.end(), 0
        while _i < len(_src):
            _c = _src[_i]
            if _c == "{":
                _d += 1
            elif _c == "}":
                _d -= 1
            elif _c == ">" and _d == 0:
                break
            _i += 1
        if 'type="number"' in _src[_m.start():_i + 1]:
            _num_inputs.append("%s:%d"
                               % (_name, _src[:_m.start()].count(chr(10)) + 1))

check("هیچ <input type=\"number\"> نمانده", not _num_inputs,
      "، ".join(_num_inputs[:6]) if _num_inputs
      else "همه NumberInput شده‌اند")

_ui = ALL.get("ui/index.jsx", "")
check("NumberInput وجود دارد و type=text است",
      "export function NumberInput" in _ui and 'type="text"' in _ui,
      "با inputMode عددی، تا صفحه‌کلید موبایل هم عددی بماند")
check("و ورودی را پیش از onChange نرمال می‌کند",
      "normalizeNumeric(e.target.value" in _ui,
      "وگرنه رقم فارسی دست‌نخورده به بکند می‌رسد")
check("نرمال‌ساز ارقام فارسی و عربی را می‌شناسد",
      "\u06F0" in _ui or "۰-۹" in _ui,
      "هر دو مجموعه‌ی رقم در یونیکد جدا هستند")


# ═══════════════════════════════════════════════════════════
head("جدول پرتال · روی گوشی نباید پهلو بکشد")

# جدولِ کانفیگ‌ها هفت ستون دارد. روی ۳۷۵ پیکسل یعنی اسکرول افقی، و
# اسکرول افقی یعنی نماینده برای رسیدن به دکمه‌ی تمدید باید جدول را
# بکشد. زیر ۷۲۰ پیکسل هر ردیف یک کارت می‌شود و عنوانِ هر خانه از
# data-label می‌آید — پس یک نشانه‌گذاری می‌ماند، نه دو نسخه‌ی جدا که
# روزی از هم دور بیفتند.
_PI = ALL.get("portal/index.jsx", "")

check("جدول کانفیگ‌ها کلاسِ کارت‌شونده دارد",
      "fx-table-cards" in _PI and ".fx-table-cards" in _css,
      "بدون کلاس، قاعده‌ی موبایل به هیچ جدولی نمی‌خورد")

_labelled = re.findall(r'<td data-label="([^"]+)"', _PI)
check("خانه‌های داده عنوان دارند", len(_labelled) >= 5,
      "، ".join(_labelled) if _labelled else "هیچ‌کدام")

check("و قاعده‌ی موبایل عنوان را نشان می‌دهد",
      "td[data-label]::before" in _css and "attr(data-label)" in _css,
      "وگرنه روی گوشی ستون‌ها بی‌نام می‌شوند")

# نوار مصرف: عدد تنها خوانده نمی‌شود، نوار فقط دیده می‌شود
# خودِ قاعده، نه هر رشته‌ای که نامش را دارد: `.fx-usebar > i` هم
# همین زیررشته را دارد، پس شکستنِ عمدی نشان داد حذفِ قاعده‌ی اصلی
# گرفته نمی‌شود
check("نوار مصرف تعریف شده",
      re.search(r"^\.fx-usebar\s*\{", _css, re.M) is not None
      and re.search(r"^\.fx-usebar\s*>\s*i\s*\{", _css, re.M) is not None
      and "fx-usebar" in _PI,
      "هم خودِ نوار و هم پُرشدگی‌اش")
check("و رنگش از روی درصد می‌آید",
      "usagePct >= 90" in _PI and "usagePct >= 75" in _PI,
      "قرمز بالای ۹۰، زرد بالای ۷۵ — تا نگاه سریع کافی باشد")

TW = io.open(os.path.join(ROOT, "frontend", "tailwind.config.js"),
             encoding="utf-8").read()


# ═══════════════════════════════════════════════════════════
head("بارگذاری · اسکلتون، نه چرخنده‌ی وسطِ صفحه")

# چرخنده فقط می‌گوید «صبر کن» و وقتی داده رسید کل چیدمان می‌پرد.
# اسکلتون جای محتوا را از قبل نگه می‌دارد.
#
# چرخنده‌ی داخلِ دکمه درست است و باید بماند: آن‌جا واقعاً یعنی
# «این دکمه مشغول است» و جای چیزی را نگرفته.
_page_spin = []
for _n, _s in ALL.items():
    for _m in re.finditer(
            r'<div className="flex (?:justify-center|items-center justify-center)'
            r'[^"]*"[^>]*>\\s*<Loader2[^/]*/>\\s*</div>', _s):
        _page_spin.append(f"{_n}:{_s[:_m.start()].count(chr(10)) + 1}")

check("هیچ چرخنده‌ی تمام‌صفحه‌ای نمانده", not _page_spin,
      "، ".join(_page_spin[:4]) if _page_spin else "همه اسکلتون شده‌اند")

check("اسکلتونِ صفحه وجود دارد", "export function PageSkeleton" in UI)
check("و به صفحه‌خوان هم می‌گوید مشغول است", 'aria-busy="true"' in UI,
      "وگرنه کسی که صفحه را نمی‌بیند نمی‌فهمد چیزی در راه است")

_sk_users = [n for n, s in ALL.items()
             if "<PageSkeleton" in s or "<Skeleton" in s or "<SkeletonTable" in s]
check("و واقعاً در صفحه‌ها استفاده شده", len(_sk_users) >= 18,
      f"{len(_sk_users)} فایل")


# ═══════════════════════════════════════════════════════════
head("مودال · نباید تله‌ی کیبورد باشد")

# با Tab می‌شد از داخل مودال به صفحه‌ی زیرش رفت و روی دکمه‌ای زد که
# اصلاً دیده نمی‌شود. برای کسی که با کیبورد کار می‌کند، مودال عملاً
# یک تله بود.
check("حبس تمرکز نوشته شده", "export function useFocusTrap" in UI)
check("و تمرکز را سر جای اولش برمی‌گرداند", "prev.focus" in UI,
      "بعد از بستن، کاربر باید همان‌جا باشد که بود")
check("و با Escape بسته می‌شود", 'e.key === "Escape"' in UI)

for _name in ("Modal", "ConfirmModal"):
    _fn = UI[UI.find(f"export function {_name}("):]
    _fn = _fn[:_fn.find(chr(10) + "export ", 10)]
    check(f"{_name} از حبس تمرکز استفاده می‌کند", "useFocusTrap(box" in _fn)
    check(f"{_name} به صفحه‌خوان می‌گوید مودال است",
          'role="dialog"' in _fn and 'aria-modal="true"' in _fn)

_toast = UI[UI.find("export function Toast("):]
_toast = _toast[:_toast.find(chr(10) + "export ", 10)]
check("توست اعلام می‌شود", 'role="status"' in _toast and 'aria-live' in _toast,
      "بدون این، «ذخیره شد» برای صفحه‌خوان اتفاق نیفتاده است")


# ═══════════════════════════════════════════════════════════
head("موشن · یک زبان، نه سلیقه‌ی هر کامپوننت")

_css_all = CSS
for _tok in ("--m-fast", "--m-base", "--m-slow",
             "--sp-snappy", "--sp-soft", "--sp-inout"):
    check(f"توکن {_tok} تعریف شده", _tok + ":" in _css_all)

check("تیلویند توکن‌ها را می‌شناسد",
      "theme: { extend: {} }" not in TW
      and 'accent: "var(--accent)"' in TW
      and "transitionTimingFunction" in TW,
      "وگرنه هر کامپوننت باید style درون‌خطی بنویسد")
check("و رنگ‌ها را از همان متغیرهای CSS می‌خواند",
      TW.count("var(--") >= 14, f"{TW.count('var(--')} ارجاع")

# انیمیشن روی width/height/top/left یعنی مرورگر باید چیدمان را
# دوباره حساب کند — روی موبایل همان‌جا می‌لنگد
_bad_anim = []
for _m in re.finditer(r"transition:\\s*([^;]+);", _css_all):
    _t = _m.group(1)
    for _prop in ("width", "height", "top", "left", "right", "bottom", "margin"):
        # «width» داخل «stroke-width» و «max-width» نباید شمرده شود
        if re.search(r"(?:^|[\\s,])" + _prop + r"(?:\\s|,|$)", _t):
            _bad_anim.append(_t.strip()[:60])
check("هیچ transition روی خصوصیت‌های چیدمانی نیست", not _bad_anim,
      "، ".join(sorted(set(_bad_anim))[:3]) if _bad_anim
      else "فقط transform و opacity و رنگ — یعنی روی GPU")

check("حرکت را می‌شود کم کرد", "body.fx-calm" in _css_all)
check("و تنظیمِ خودِ سیستم هم محترم است",
      "prefers-reduced-motion" in _css_all)


# ═══════════════════════════════════════════════════════════
head("پالت فرمان · ۴۵ صفحه با یک تایپ")

_APPJ = ALL.get("App.jsx", "")
check("پالت فرمان وجود دارد", "export function CommandPalette" in UI)
check("و با Ctrl+K باز می‌شود",
      'e.key.toLowerCase() === "k"' in _APPJ and "ctrlKey" in _APPJ)
check("همه‌ی فضاهای کاری را می‌گردد، نه فقط یکی",
      "workspaces={WORKSPACES}" in _APPJ,
      "جستجوی سایدبار فقط همان فضای کاری را فیلتر می‌کرد")
check("و انتخاب، فضای کاری را هم عوض می‌کند",
      "setWorkspace(ws)" in _APPJ,
      "وگرنه به صفحه‌ای می‌رفت که در فهرست جاری نیست و پرت می‌شد")
check("صفحه‌های نیامده در پالت نمی‌آیند", "if (it.badge) return;" in UI,
      "دکمه‌ی بی‌جواب از نبودِ دکمه بدتر است")
check("با کیبورد کامل کار می‌کند",
      '"ArrowDown"' in UI and '"ArrowUp"' in UI and '"Enter"' in UI)


# ═══════════════════════════════════════════════════════════
head("سه اپ نباید در یک فایل باشند")

# مشتریِ مینی‌اپ کلِ پنل مدیر را هم دانلود می‌کرد — و همان مشتری،
# همان کسی است که اینترنتش محدود است.
_MAIN = ALL.get("main.jsx", "")
# سه import پویا و *یک* lazy: تکه‌ها جدا می‌مانند و فقط یکی دانلود
# می‌شود. شکلِ قبلی سه تا `lazy(() => import(...))` بود؛ حالا دانلود
# پیش از رندر شروع می‌شود تا کفِ زمانیِ صفحه‌ی ورود با آن هم‌زمان
# بدود، نه پشت سرش.
check("اپ‌ها با import پویا جدا می‌مانند",
      _MAIN.count("() => import(") >= 3, "پنل مدیر، پنل نماینده، مینی‌اپ")
# کامنت‌ها اول برداشته می‌شوند — این‌جا هم `lazy(` در توضیحِ خودِ
# کد پیدا می‌شد و شمارش را دو برابر می‌کرد. سومین بار در این مخزن.
_main_code = "\n".join(l for l in _MAIN.split("\n")
                       if not l.strip().startswith("//"))
check("و فقط یکی از آن‌ها بار می‌شود",
      "PICK[WHICH]()" in _main_code and _main_code.count("lazy(") == 1,
      "اگر هر سه صدا زده شوند، مشتریِ مینی‌اپ کلِ پنل مدیر را هم می‌گیرد")
check("و شرطِ مسیر از ماژولِ بی‌وابستگی می‌آید",
      'from "./lib/route.js"' in _MAIN,
      "وگرنه خودِ تصمیم، هر سه اپ را بار می‌کند")
_ROUTE = ALL.get("lib/route.js", "")
check("و آن ماژول واقعاً هیچ وابستگی‌ای ندارد",
      "import " not in _ROUTE, "یک import کافی است تا همه‌چیز دوباره به هم بچسبد")
check("تا رسیدنِ تکه، صفحه سفید نمی‌ماند", "Suspense" in _MAIN and "fallback" in _MAIN)


# ═══════════════════════════════════════════════════════════
head("مینی‌اپ · باید شبیه خودِ تلگرام باشد")

_MINI = ALL.get("mini/index.jsx", "")
check("رنگ‌ها را از تلگرام می‌گیرد", "themeParams" in _MINI,
      "وگرنه روی تلگرامِ روشن، یک جعبه‌ی تیره‌ی غریبه است")
check("و وقتی کاربر پوسته را عوض کند، دنبالش می‌رود",
      '"themeChanged"' in _MINI)
check("نوار بالای تلگرام هم هم‌رنگ می‌شود", "setHeaderColor" in _MINI)
check("هیچ متنِ سفیدِ ثابتی نمانده", "text-white" not in _MINI,
      "روی پوسته‌ی روشن، سفید روی سفید نامرئی است")
check("لرزشِ بازخورد دارد", "HapticFeedback" in _MINI)

# ── ناحیه‌ی امن ──
#
# `env(safe-area-inset-*)` را مرورگر از سیستم‌عامل می‌گیرد، ولی داخل
# WebViewِ تلگرام معمولاً صفر برمی‌گردد و اصلاً چیزی از نوارِ خودِ
# تلگرام نمی‌داند. پس عددها باید از خودِ تلگرام بیایند.
check("ناحیه‌ی امن را از تلگرام می‌خواند",
      "safeAreaInset" in _MINI and "contentSafeAreaInset" in _MINI,
      "env() داخل تلگرام صفر است و نوار خودش را هم نمی‌شناسد")
# دنبالِ *اشتراک* بگرد، نه نامِ رویداد: همان رشته در خطِ لغوِ
# اشتراک (`offEvent`) هم هست، پس با شرطِ ساده، برداشتنِ خودِ
# `onEvent` سبز می‌ماند.
check("و وقتی عوض شود دنبالش می‌رود",
      'onEvent?.("safeAreaChanged"' in _MINI
      and 'onEvent?.("contentSafeAreaChanged"' in _MINI,
      "چرخاندن گوشی و بازشدن صفحه‌کلید عوضش می‌کنند")
check("نوارهای بالا و پایین از همان متغیر استفاده می‌کنند",
      "var(--mn-sa-top)" in CSS and "var(--mn-sa-bottom)" in CSS)

# `* 0` یک‌بار واقعاً در این فایل بود: خطی که شبیه رعایتِ ناحیه‌ی امن
# است ولی حاصلش همیشه صفر — بدترین نوعِ مسیر خرابِ بی‌صدا، چون
# *به نظر می‌رسد* کار شده.
check("هیچ حسابِ ناحیه‌ی امنی در صفر ضرب نشده",
      "safe-area-inset-top, 0px) * 0" not in CSS,
      "خطی که شبیه رعایتِ ناحیه‌ی امن است ولی همیشه صفر می‌دهد")
check("ولی نبودنش چیزی را نمی‌شکند",
      "catch { /* بی‌صدا — لرزش اختیاری است */ }" in _MINI)
check("و هنوز هیچ پولی این‌جا حساب نمی‌شود",
      "price *" not in _MINI and "* months" not in _MINI,
      "خرید در خودِ ربات می‌ماند — قرار خودِ مالک")

import re as _re

# ═══════════════════════════════════════════════════════════
head("رنگ · یک نام، یک مقدار")

# چهار وضعیت پنل در ۳۲۸ جای JSX دستی نوشته شده بودند — رنگ هشدار
# به‌تنهایی ۶۳ بار با ۱۷ آلفای متفاوت. `.05` و `.06` و `.07` و `.08`
# را هیچ طراحی عمداً انتخاب نمی‌کند؛ ردِ پای کپی‌کردن‌اند. نتیجه این
# بود که هیچ دو چیپِ «هشدار» دقیقاً یک رنگ نبودند.
_RGBA = _re.compile(r"rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,")

# این دو صفحه انتخابگرِ رنگ‌اند: آن‌جا مقدارِ واقعی *خودِ داده* است،
# نه استایل. عمداً بیرون‌اند.
_PICKERS = ("sections/bot/themes.jsx", "sections/subpage.jsx")

_raw = []
for _name, _src in ALL.items():
    if _name.endswith(_PICKERS) or not _name.endswith(".jsx"):
        continue
    _n = len(_RGBA.findall(_src))
    if _n:
        _raw.append(f"{_name}:{_n}")

check("هیچ rgba خامی در JSX نمانده", not _raw,
      ", ".join(_raw[:4]) if _raw else "همه از توکن می‌آیند")

# و خودِ توکن‌ها باید واقعاً تعریف شده باشند — var(--nope) بی‌صدا
# شفاف می‌شود، که همان مسیر خرابِ بی‌صداست
_CSS = io.open(os.path.join(ROOT, "frontend", "src", "index.css"),
               encoding="utf-8").read()
_defined = set(_re.findall(r"^\s*(--[a-z0-9-]+)\s*:", _CSS, _re.M))
_used = set()
for _name, _src in ALL.items():
    if _name.endswith(".jsx"):
        _used |= set(_re.findall(r"var\(\s*(--[a-z0-9-]+)\s*\)", _src))
# توکن‌هایی که خودِ کامپوننت در لحظه می‌سازد (مثل --ring روی Avatar)
_runtime = {"--ring", "--pct", "--w"}
_ghost = sorted(_used - _defined - _runtime)
check("هر var() که JSX می‌نویسد تعریف شده", not _ghost,
      ", ".join(_ghost[:5]) if _ghost else f"{len(_used)} توکن")

check("پله‌های معنایی کامل‌اند",
      all(f"--{c}-{t}:" in _CSS
          for c in ("ok", "warn", "danger")
          for t in ("wash", "soft", "fill", "line", "edge")),
      "wash · soft · fill · line · edge")


# ═══════════════════════════════════════════════════════════
head("چهره‌ی کاربر · یک قاعده، دو جا")

# `AVATAR_HUES` در پنل (React) و `NEXORA_AVATAR_HUES` در صفحه‌ی
# اشتراک (HTML تک‌فایلی) عمداً تکراری‌اند: صفحه‌ی اشتراک را سرورِ
# 3x-ui سرو می‌کند و به باندلِ ما دسترسی ندارد. پس طبق قاعده‌ی
# مخزن، تستِ برابری می‌خواهد — وگرنه دقیقاً وقتی از هم جدا می‌شوند
# که کسی یکی را عوض کند و همان مشتری در دو جا دو رنگ بگیرد.

_UI = ALL.get("ui/index.jsx", "")
_SUBP = io.open(os.path.join(ROOT, "sub-page-index.html"),
                encoding="utf-8").read()


def _hues(text, name):
    m = _re.search(name + r"\s*=\s*\[(.*?)\];", text, _re.S)
    return _re.findall(r"#[0-9A-Fa-f]{6}", m.group(1)) if m else []


_a = _hues(_UI, "AVATAR_HUES")
_b = _hues(_SUBP, "NEXORA_AVATAR_HUES")
check("پنل رنگ‌های چهره را دارد", len(_a) == 16, f"{len(_a)} رنگ")
check("صفحه‌ی اشتراک هم همان‌ها را دارد", len(_b) == 16, f"{len(_b)} رنگ")
check("و دو فهرست دقیقاً یکی‌اند", _a == _b,
      "یک مشتری نباید در پنل بنفش باشد و در صفحه‌ی اشتراک سبز")

# هشِ رنگ هم باید یکی باشد، نه فقط فهرست
check("هشِ هر دو یک فرمول است",
      "h = (h * 31 + key.charCodeAt(i)) >>> 0" in _UI
      and "h = (h * 31 + label.charCodeAt(i)) >>> 0" in _SUBP,
      "رنگ باید از نام بیاید، همیشه همان")

# دنبالِ *صداشدن* بگرد، نه تعریفِ تابع: با `paintAvatar(` تنها،
# برداشتنِ خطِ صدازدن هم سبز می‌ماند — یعنی دروازه‌ای که به اتاقِ
# خالی نگاه می‌کند.
# چهره باید دایره بماند، نه بیضی. قابِ ۴۶ پیکسلی داخل یک ستونِ
# فلکسِ ۵۴ پیکسلی بود و کنارش خطِ «آفلاین» هم می‌نشست، پس از ۴۶ به
# ۳۸ فشرده می‌شد — و `border-radius: 50%` روی ۴۶×۳۸ یعنی بیضی.
# jsdom چیدمان ندارد، پس این را از روی خودِ قاعده می‌سنجیم.
check("قابِ چهره در صفحه‌ی اشتراک فشرده نمی‌شود",
      "flex: none;" in _SUBP.split(".profile-img {")[1].split("}")[0]
      if ".profile-img {" in _SUBP else False,
      "بدون flex:none، ستونِ فلکس ارتفاعش را می‌خورد و دایره بیضی می‌شود")

# صفحه‌ی اشتراک باید همان زبانِ طراحیِ پنل را داشته باشد، نه فقط
# همان رنگِ اکسنت. سه چیزِ مشترک: سریِ دومِ فیروزه‌ای، خطِ مو روی
# لبه‌ی بالای کارت‌ها، و نورِ محیطی.
# دو کارت که یک چیز را دو بار می‌گفتند، یکی شدند. برگشتشان یعنی
# دوباره ۲۶۲ پیکسل برای شش قلم داده.
check("آمار صفحه‌ی اشتراک دو بار تکرار نمی‌شود",
      'id="sec-details"' not in _SUBP and "stat-cell" in _SUBP,
      "«مصرف کل» و «باقی‌مانده» هر کدام در دو کارت جدا بودند")

# `getElementById(x).innerText` بدون نگهبان یعنی هر جابه‌جاییِ چیدمان
# صفحه را سفید می‌کند.
check("نوشتن روی شناسه نگهبان دارد", "function setText(id, v)" in _SUBP,
      "یک عنصرِ جابه‌جاشده نباید کل رندر را بیندازد")

check("صفحه‌ی اشتراک سری دوم برند را دارد", "--cy:" in _SUBP,
      "پنل دو رنگ دارد؛ این صفحه فقط آبی داشت")
check("و خطِ مو روی لبه‌ی کارت‌ها", "--hair-3" in _SUBP and "::after" in _SUBP,
      "بدون آن، کارت یک مستطیلِ تخت است")
check("و نورِ محیطی زیر همه چیز", "nx-amb" in _SUBP)
# `::after` عمداً است نه `::before`: چند کلاس از قبل `::before`
# دارند (سه‌نقطه‌ی قالب کنسول) و گرفتنش یعنی خراب‌کردنشان.
check("خط مو از ::after می‌آید، نه ::before",
      ".stats-card::after" in _SUBP and ".stats-card::before" not in _SUBP,
      "همان برخوردی که یک‌بار روی کارت KPI پنل رخ داد")

check("صفحه‌ی اشتراک شبحِ خاکستری را کنار می‌گذارد",
      "profile-initial" in _SUBP and "paintAvatar(username)" in _SUBP,
      "آیکونِ یکسان برای همه، هیچ نمی‌گوید")


print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
