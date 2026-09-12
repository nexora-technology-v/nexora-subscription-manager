#!/usr/bin/env python3
"""
ایجنت باید واقعاً کار کند، و توکنش قابل بازپخش نباشد.

چرا وجود دارد:
    مانیتورینگ سرورهای دیگر هیچ‌وقت نمی‌آمد و هیچ خطایی هم دیده
    نمی‌شد. سه علت پشت هم داشت:

      ۱. ایجنت نسخه‌اش را از روز اول «۱.۰.۰» گزارش می‌کرد و هرگز
         بالا نرفت، پس بررسی «قدیمی است» فعال نمی‌شد.
      ۲. دستور به‌روزرسانی یک آدرس نسبی می‌فرستاد که ایجنت آن را
         «خارج از پنل» رد می‌کرد — پس به‌روزرسانی هم ممکن نبود.
      ۳. و ریشه‌ی اصلی: ایجنت monitor.py را یک بار دانلود می‌کرد و
         تا ابد همان را نگه می‌داشت. وقتی پنل تابع snapshot را اضافه
         کرد، ایجنت هنوز نسخه‌ی قدیمی را داشت و می‌گفت «تابع نیست».

    هر سه این‌جا آزموده می‌شوند تا دوباره بی‌صدا برنگردند.

اجرا:  python3 tools/test-agent.py
"""
import hashlib
import hmac
import importlib.util
import io
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


AGENT = io.open(os.path.join(ROOT, "agent", "nexora-agent.py"),
                encoding="utf-8").read()
APP = io.open(os.path.join(ROOT, "backend", "app.py"), encoding="utf-8").read()


# ═══════════════════════════════════════════════════════════
head("نسخه")

m = re.search(r'^VERSION = "([\d.]+)"', AGENT, re.M)
check("ایجنت نسخه دارد", m is not None, m.group(1) if m else "")
ver = m.group(1) if m else "0"
check("نسخه دیگر ۱.۰.۰ نیست", ver != "1.0.0",
      "همان عددی که باعث شد «قدیمی است» هرگز فعال نشود")

panel_ver = io.open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read().strip()


def parts(v):
    return [int("".join(c for c in x if c.isdigit()) or 0)
            for x in str(v).split(".")][:3]


check("نسخه‌ی ایجنت از کف تشخیص جلوتر است", parts(ver) >= [1, 5, 0],
      f"ایجنت {ver} · پنل {panel_ver}")


# ═══════════════════════════════════════════════════════════
head("هر دستوری که پنل صف می‌کند، ایجنت می‌شناسد")

queued = set(re.findall(r'queue_job\([^,]+,\s*["\'](\w+)["\']', APP))
queued |= set(re.findall(r'kind not in \("(\w+)", "(\w+)"\)', APP)[0]
              if re.findall(r'kind not in \("(\w+)", "(\w+)"\)', APP) else [])

known = set(re.findall(r'if action (?:==|in) \(?["\'](\w+)["\']', AGENT))
for grp in re.findall(r'if action in \(([^)]*)\)', AGENT):
    known |= set(re.findall(r'["\'](\w+)["\']', grp))

missing = sorted(q for q in queued if q and q not in known)
check("هیچ دستور بی‌هندلری صف نمی‌شود", not missing,
      f"ناشناخته: {missing}" if missing else f"{len(queued)} دستور")

for must in ("sysmon", "firewall", "update_agent", "health"):
    check(f"دستور «{must}» پیاده‌سازی شده", must in known)


# ═══════════════════════════════════════════════════════════
head("کش ماژول کهنه نمی‌ماند")

check("نسخه‌ی پنل در پاسخ چک‌این می‌آید", '"panelVersion"' in APP)
check("ایجنت نسخه را به کارها می‌دهد", "panel_version" in AGENT)
check("کش با تغییر نسخه دور ریخته می‌شود", "stale = bool(want)" in AGENT,
      "همان چیزی که snapshot را برای همیشه ناموجود نگه می‌داشت")
check("نسخه‌ی کش‌شده ذخیره می‌شود", ".version" in AGENT)
check("وابستگی‌ها هم دانلود می‌شوند", "MODULE_DEPS" in AGENT)
check("netid همراه monitor می‌آید", '"monitor": ("netid",)' in AGENT)
check("پنل netid را سرو می‌کند", '/api/agent/netid.py' in APP)

for mod in ("monitor", "firewall", "netid", "health", "agent"):
    check(f"پنل {mod}.py را سرو می‌کند", f'/api/agent/{mod}.py' in APP)


# ═══════════════════════════════════════════════════════════
head("ماژول‌ها مستقل بارگذاری می‌شوند")

# دقیقاً همان کاری که remote_module می‌کند: فایل تنها، بدون بقیه‌ی پروژه
for name, func in (("monitor", "snapshot"), ("firewall", "status")):
    path = os.path.join(ROOT, "backend", f"{name}.py")
    try:
        spec = importlib.util.spec_from_file_location(f"solo_{name}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = getattr(mod, func, None)
        check(f"{name}.py تنها بارگذاری می‌شود", fn is not None,
              f"تابع {func}" if fn else f"{func} پیدا نشد")
        if fn:
            out = fn()
            check(f"{name}.{func}() خروجی می‌دهد", isinstance(out, dict),
                  f"{len(out)} کلید" if isinstance(out, dict) else type(out).__name__)
    except Exception as e:
        check(f"{name}.py تنها بارگذاری می‌شود", False,
              f"{type(e).__name__}: {str(e)[:60]}")


# ═══════════════════════════════════════════════════════════
head("امضای درخواست")

check("ایجنت امضا می‌سازد", "def sign(" in AGENT)
check("HMAC-SHA256 استفاده می‌شود", "hashlib.sha256" in AGENT)
check("زمان داخل امضاست", 'ts.encode() + b"." +' in AGENT,
      "بدون زمان، ضبط و بازپخش ممکن است")
check("هدرهای امضا فرستاده می‌شوند",
      '"X-Agent-Time"' in AGENT and '"X-Agent-Sign"' in AGENT)
check("پنل امضا را بررسی می‌کند", "hmac.compare_digest" in APP)
check("مقایسه در زمان ثابت است", "compare_digest" in APP,
      "مقایسه‌ی معمولی رشته، طول امضا را لو می‌دهد")
check("اختلاف ساعت محدود است", "AGENT_CLOCK_SKEW" in APP)
check("ایجنت بدون امضا هنوز کار می‌کند", "if sign:" in APP,
      "تا نسخه‌های قدیمی یک‌شبه از کار نیفتند")

# امضا واقعاً باید بخواند
TOKEN = "tok_test_123"
body = b'{"metrics":{"cpu":12.5}}'
ts = str(int(time.time()))
want = hmac.new(TOKEN.encode(), ts.encode() + b"." + body,
                hashlib.sha256).hexdigest()

sys.path.insert(0, os.path.join(ROOT, "agent"))
spec = importlib.util.spec_from_file_location(
    "nxagent", os.path.join(ROOT, "agent", "nexora-agent.py"))
ag = importlib.util.module_from_spec(spec)
ag.__dict__["__name__"] = "nxagent"
try:
    spec.loader.exec_module(ag)
    ag.TOKEN = TOKEN
    got = ag.sign(body, ts)
    check("امضای ایجنت با محاسبه‌ی پنل یکی است", got == want,
          f"{got[:16]}… == {want[:16]}…")
    check("بدنه‌ی متفاوت امضای متفاوت می‌دهد",
          ag.sign(b'{"metrics":{"cpu":99}}', ts) != want)
    check("زمان متفاوت امضای متفاوت می‌دهد",
          ag.sign(body, str(int(ts) + 1)) != want)
except Exception as e:
    check("ایجنت بارگذاری می‌شود", False, f"{type(e).__name__}: {str(e)[:70]}")


# ═══════════════════════════════════════════════════════════
head("به‌روزرسانی خود ایجنت")

check("آدرس خالی را خودش می‌سازد",
      'own = f"{PANEL_URL}/api/agent/agent.py"' in AGENT,
      "پنل پشت nginx آدرس بیرونی‌اش را نمی‌داند")
check("فقط از پنل خودش می‌گیرد",
      'if not url or not url.startswith(PANEL_URL):' in AGENT,
      "هر آدرس دیگری نادیده گرفته می‌شود و آدرس خودمان جایش می‌نشیند")
check("فایل دریافتی بررسی می‌شود", "معتبر نیست" in AGENT)
check("نسخه‌ی قبلی پشتیبان گرفته می‌شود", '".bak"' in AGENT)
check("پنل آدرس مطلق می‌سازد", "request.base_url" in APP)
check("ایجنت بدون نسخه قدیمی حساب می‌شود", 'stale_agent = "نامشخص"' in APP)


# ═══════════════════════════════════════════════════════════
head("تشخیص: چرا گزارشی نمی‌آید")

check("مسیر تشخیص وجود دارد", "/diagnose" in APP)
check("چک‌این ایجنت بررسی می‌شود", "چک‌این ایجنت" in APP)
check("نسخه‌ی ایجنت بررسی می‌شود", "نسخه‌ی ایجنت" in APP)
check("برداشتن کار بررسی می‌شود", "برداشتن کار" in APP)
check("اجرای کار بررسی می‌شود", "اجرای کار" in APP)
check("گزارش ذخیره‌شده بررسی می‌شود", "گزارش ذخیره‌شده" in APP)
check("برای هر مرحله راه‌حل می‌دهد", APP.count('"fix"') >= 5,
      f"{APP.count(chr(34) + 'fix' + chr(34))} راه‌حل")
check("تاریخچه‌ی کارها برمی‌گردد", '"jobs": jobs' in APP)
check("کار مانده در صف تشخیص داده می‌شود", 'st == "queued"' in APP)
check("کار برداشته‌شده ولی بی‌نتیجه هم", 'st == "taken"' in APP)
check("کار شکست‌خورده متن خطا را نشان می‌دهد", 'st == "failed"' in APP)
check("رابط تشخیص را نشان می‌دهد",
      "NodeDiagnose" in io.open(
          os.path.join(ROOT, "frontend", "src", "sections",
                       "nodes-monitor.jsx"), encoding="utf-8").read())


# ═══════════════════════════════════════════════════════════
head("مانیتورینگ خودکار ثبت می‌شود، نه فقط دستی")

# در لاگ یک سرور واقعی ۲۳ کار health پشت هم دیده شد و حتی یک sysmon —
# چون sysmon فقط با کلیک مدیر ثبت می‌شد. یعنی صفحه تا اولین کلیک خالی
# بود و بعدش هم بلافاصله کهنه می‌شد.
check("زمان‌بند sysmon را هم ثبت می‌کند",
      'TUN.queue_job(nid, "sysmon", {})' in APP,
      "کنار health، در همان حلقه")
check("قبلش تازگی بررسی می‌شود", "_sysmon_fresh(nid)" in APP,
      "تا صف بی‌دلیل شلوغ نشود")
check("آستانه‌ی تازگی تعریف شده", "SYSMON_MAX_AGE" in APP)
check("هر دو کار در یک حلقه‌اند",
      0 < (APP.index('TUN.queue_job(nid, "sysmon"')
           - APP.index('TUN.queue_job(nid, "health"')) < 900,
      "پس اگر health می‌رسد، sysmon هم می‌رسد")

_sp2 = importlib.util.spec_from_file_location(
    "nxapp2", os.path.join(ROOT, "backend", "app.py"))
A2 = importlib.util.module_from_spec(_sp2)
try:
    _sp2.loader.exec_module(A2)
    from datetime import datetime as _dt, timedelta as _td

    def _stub(at):
        return type("T", (), {"get_sysmon": staticmethod(lambda nid: at)})

    A2.TUN = _stub({"at": (_dt.now() - _td(seconds=30)).isoformat()})
    check("گزارش سی‌ثانیه‌ای تازه حساب می‌شود", A2._sysmon_fresh(1) is True)

    A2.TUN = _stub({"at": (_dt.now() - _td(seconds=900)).isoformat()})
    check("گزارش پانزده‌دقیقه‌ای کهنه است", A2._sysmon_fresh(1) is False)

    A2.TUN = _stub(None)
    check("نبود گزارش یعنی کهنه", A2._sysmon_fresh(1) is False)

    A2.TUN = _stub({"at": "خراب"})
    check("تاریخ خراب خطا نمی‌دهد", A2._sysmon_fresh(1) is False)
except Exception as e:
    check("app.py بارگذاری می‌شود", False, f"{type(e).__name__}: {str(e)[:60]}")



# ═══════════════════════════════════════════════════════════
head("ایجنت قبل از ری‌استارت نتیجه را می‌فرستد")

# کار ۱۸۴۰ روی «taken» مانده بود: systemctl restart همین پردازه را
# می‌کشد، و چون نتیجه بعد از return فرستاده می‌شد، هیچ‌وقت نمی‌رسید.
check("ری‌استارت داخل update_self انجام نمی‌شود",
      "RESTART_AFTER.append" in AGENT,
      "وگرنه کار تا ابد روی taken می‌ماند")
check("پرچم ری‌استارت وجود دارد", "RESTART_AFTER = []" in AGENT)
check("حلقه بعد از فرستادن نتیجه ری‌استارت می‌کند",
      AGENT.index('api("job-result"') < AGENT.index("if RESTART_AFTER:"),
      "ترتیب مهم است")
check("بعد از ری‌استارت حلقه تمام می‌شود",
      "RESTART_AFTER.clear()" in AGENT)

head("نام معکوس صفحه را معطل نمی‌کند")

NET = io.open(os.path.join(ROOT, "backend", "netid.py"),
              encoding="utf-8").read()
check("نسخه‌ی کش‌خوان وجود دارد", "def rdns_cached" in NET,
      "صفحه فقط از کش می‌خواند")
check("پرکردن کش در پس‌زمینه است", "def rdns_warm" in NET)
check("نخ پس‌زمینه daemon است", "daemon=True" in NET,
      "تا بستن سرویس را معطل نکند")
check("نسخه‌ی موازی سقف زمانی دارد", "budget=" in NET)
check("صفحه دیگر مستقیم owner صدا نمی‌زند",
      "NETID.rdns_cached(top)" in APP,
      "شصت آدرس × ۱.۵ ثانیه یعنی نود ثانیه انتظار")

head("ابزار تشخیص سرور")

DOC = os.path.join(ROOT, "nexora-doctor.sh")
check("فایل تشخیص وجود دارد", os.path.exists(DOC))
if os.path.exists(DOC):
    D2 = io.open(DOC, encoding="utf-8").read()
    for what, needle in (
        ("نسخه‌ی روی دیسک و نسخه‌ی در حال اجرا", "panel code is newer"),
        ("کار گیرکرده روی taken", "taken by the agent with no answer"),
        ("کار مانده در صف", "waiting with no agent"),
        ("دید فایروال به پورت‌ها", "listening ports and their owners"),
        ("پردازه‌های تانل", "tunnel process"),
        ("خواندن x-ui", "x-ui database"),
        ("گروه بدون تاریخ شروع", "have no start date"),
        ("موجودی منفی", "negative balance"),
        ("رزرو سکه‌ی آزادنشده", "coin hold"),
    ):
        check("بررسی می‌کند: " + what, needle in D2)

    persian_out = re.findall(r'^\s*(?:echo|info|warn|bad|ok|fix)\s+.*[؀-ۿ]',
                             D2, re.M)
    check("خروجی انگلیسی است", not persian_out,
          "متن فارسی در شل با جهت‌دهی ترمینال تداخل می‌کند")
    check("به CLI وصل شده",
          "check|diagnose" in io.open(
              os.path.join(ROOT, "nexora-cli.sh"), encoding="utf-8").read())



# ═══════════════════════════════════════════════════════════
head("به‌روزرسانی ایجنت با حدسِ آدرسِ پنل شکست نمی‌خورد")

# سه کار پشت سر هم روی سرور واقعی با «آدرس به‌روزرسانی خارج از پنل
# مجاز نیست» رد شده بود. علتش این بود که پنل آدرس بیرونی خودش را از
# هدرهای nginx حدس می‌زد (manage.example.ir) در حالی که ایجنت موقع
# نصب با آی‌پی و پورت تنظیم شده بود. نگهبانِ ایجنت درست کار می‌کرد؛
# چیزی که غلط بود، حدس‌زدنِ پنل بود.

APPSRC = io.open(os.path.join(ROOT, "backend/app.py"),
                 encoding="utf-8").read()

check("پنل دیگر آدرس نمی‌فرستد",
      'TUN.queue_job(node_id, "update_agent", {"url": ""})' in APPSRC,
      "ایجنت از PANEL_URL خودش می‌سازد — همان که با آن چک‌این می‌کند")
check("و از هدرها برای این کار استفاده نمی‌کند",
      '_external_base(request)\n    url = f"{base}/api/agent/agent.py"' not in APPSRC)

AGSRC = io.open(os.path.join(ROOT, "agent/nexora-agent.py"),
                encoding="utf-8").read()
check("ایجنت در صورت عدم تطابق خطا نمی‌دهد",
      'url = own' in AGSRC and
      'if not url or not url.startswith(PANEL_URL):' in AGSRC,
      "آدرس خودش را دارد، پس دلیلی برای شکست نیست")
check("ولی آدرس بیرونی را هم قبول نمی‌کند",
      'own = f"{PANEL_URL}/api/agent/agent.py"' in AGSRC,
      "نگهبان سر جایش می‌ماند — فایل اجرایی فقط از پنل خودش")
check("نسخه‌ی ایجنت بالا رفت",
      'VERSION = "1.5.1"' in AGSRC)


def _update_url(given, panel):
    """همان منطق update_self، جدا شده تا بشود مستقیم امتحانش کرد."""
    own = f"{panel}/api/agent/agent.py"
    u = (given or "").strip()
    if not u or not u.startswith(panel):
        u = own
    return u


PANEL = "http://10.0.0.5:8100"
check("آدرس خالی → آدرس خودِ ایجنت",
      _update_url("", PANEL) == f"{PANEL}/api/agent/agent.py")
check("دامنه‌ی متفاوت → آدرس خودِ ایجنت، نه خطا",
      _update_url("https://manage.example.ir/api/agent/agent.py", PANEL)
      == f"{PANEL}/api/agent/agent.py",
      "همان حالتی که سه بار شکست خورده بود")
check("آدرس درست دست‌نخورده می‌ماند",
      _update_url(f"{PANEL}/api/agent/agent.py", PANEL)
      == f"{PANEL}/api/agent/agent.py")
check("سایت ناشناس هیچ‌وقت دانلود نمی‌شود",
      _update_url("https://evil.example/agent.py", PANEL).startswith(PANEL),
      "به آدرس خودِ پنل برمی‌گردد، نه به آن‌که فرستاده شده")



print(f"\n{D}{'─' * 50}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
