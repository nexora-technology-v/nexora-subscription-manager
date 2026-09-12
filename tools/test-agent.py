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
      'url = (url or "").strip() or f"{PANEL_URL}' in AGENT,
      "پنل پشت nginx آدرس بیرونی‌اش را نمی‌داند")
check("فقط از پنل خودش می‌گیرد", "خارج از پنل مجاز نیست" in AGENT)
check("فایل دریافتی بررسی می‌شود", "معتبر نیست" in AGENT)
check("نسخه‌ی قبلی پشتیبان گرفته می‌شود", '".bak"' in AGENT)
check("پنل آدرس مطلق می‌سازد", "request.base_url" in APP)
check("ایجنت بدون نسخه قدیمی حساب می‌شود", 'stale_agent = "نامشخص"' in APP)


print(f"\n{D}{'─' * 50}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
