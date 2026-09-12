#!/usr/bin/env python3
"""
بررسی‌های سلامت سرور — همان فهرستی که در صفحه‌ی مانیتورینگ می‌بینید.

چرا وجود دارد:
    این‌ها خروجی دستورهای سیستمی را تجزیه می‌کنند، و تجزیه‌ی متن
    شکننده است. یک بار check_time خروجی timedatectl را به ترتیبِ
    خواسته‌شده فرض کرده بود — systemd به ترتیب خودش چاپ می‌کند — و
    نتیجه این بود که *همیشه* هشدار می‌داد و دستور پیشنهادی‌اش هم
    هیچ اثری نداشت، چون از اول چیزی خراب نبود.

    بررسی گواهی SSL بدتر بود: اصلاً اجرا نمی‌شد.

اجرا:  python3 tools/test-health.py
"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

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


spec = importlib.util.spec_from_file_location(
    "health", os.path.join(ROOT, "backend", "health.py"))
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)

TMP = Path(tempfile.mkdtemp())


def fake_openssl(enddate):
    def _run(cmd, **k):
        if cmd and cmd[0] == "openssl":
            return True, f"notAfter={enddate}\n"
        return False, ""
    return _run


from datetime import datetime, timedelta, timezone  # noqa: E402


def in_days(n):
    """تاریخ انقضا به همان قالبی که openssl می‌دهد."""
    d = datetime.now(timezone.utc) + timedelta(days=n)
    # openssl برای روزهای تک‌رقمی دو فاصله می‌گذارد
    return f"{d:%b} {d.day:>2} {d:%H:%M:%S} {d:%Y} GMT"


# ═══════════════════════════════════════════════════════════
head("گواهی SSL بدون اینکه دامنه را دستی بدهیم پیدا می‌شود")

live = TMP / "letsencrypt" / "live" / "panel.example.ir"
live.mkdir(parents=True)
(live / "fullchain.pem").write_text("x")
H.CERT_DIRS = (TMP / "letsencrypt" / "live", TMP / "nexora-ssl")

H._run = fake_openssl(in_days(40))
r = H.check_cert()
check("بدون دامنه هم بررسی انجام می‌شود", r is not None,
      "قبلاً بدون panelDomain هیچ‌وقت اجرا نمی‌شد — و panelDomain "
      "هیچ‌جا تنظیم نمی‌شد")
check("سالم گزارش می‌شود", r and r["level"] == "ok", r and r["detail"])
check("نام دامنه در گزارش هست", r and "panel.example.ir" in r["detail"],
      r and r["detail"])

H._run = fake_openssl(in_days(6))
r = H.check_cert()
check("نزدیک انقضا هشدار می‌دهد", r and r["level"] == "warn", r and r["detail"])
check("و راه‌حل می‌دهد", r and "certbot" in (r["hint"] or ""))

H._run = fake_openssl(in_days(-2))
r = H.check_cert()
check("منقضی‌شده بحرانی است", r and r["level"] == "crit", r and r["detail"])

head("روزهای تک‌رقمی و دو فاصله‌ی openssl")

d = datetime.now(timezone.utc) + timedelta(days=30)
H._run = fake_openssl(f"{d:%b}  {d.day} {d:%H:%M:%S} {d:%Y} GMT"
                      if d.day < 10 else in_days(30))
r = H.check_cert()
check("قالب دو فاصله‌ای هم خوانده می‌شود", r is not None and r["level"] == "ok",
      r and r["detail"])

head("وقتی چیزی برای بررسی نیست")

H.CERT_DIRS = (TMP / "nowhere",)
check("بدون گواهی، بررسی حذف می‌شود — نه هشدار الکی",
      H.check_cert() is None,
      "سروری که فقط HTTP دارد نباید هشدار بگیرد")

head("گواهی هست ولی خوانده نمی‌شود")

H.CERT_DIRS = (TMP / "letsencrypt" / "live",)
H._run = lambda cmd, **k: (False, "openssl: not found")
r = H.check_cert()
check("سکوت نمی‌کند", r is not None,
      "گواهی وجود دارد و نمی‌دانیم کی منقضی می‌شود — این خودش خبر است")
check("و هشدار است نه «سالم»", r and r["level"] == "warn", r and r["level"])

H._run = fake_openssl("این تاریخ نیست")
r = H.check_cert()
check("تاریخ نامفهوم هم هشدار می‌شود", r and r["level"] == "warn",
      r and r["detail"])

head("چند گواهی — نزدیک‌ترین انقضا برنده است")

live2 = TMP / "letsencrypt" / "live" / "sub.example.ir"
live2.mkdir(parents=True, exist_ok=True)
(live2 / "fullchain.pem").write_text("x")

seq = {}


def two_certs(cmd, **k):
    p = str(cmd[-1])
    days = 60 if "panel.example.ir" in p else 4
    seq[p] = days
    return True, f"notAfter={in_days(days)}\n"


H._run = two_certs
r = H.check_cert()
check("هر دو گواهی خوانده می‌شوند", len(seq) == 2, str(len(seq)))
check("نزدیک‌ترین انقضا گزارش می‌شود",
      r and r["level"] == "warn" and "sub.example.ir" in r["detail"],
      r and r["detail"])

head("بررسی‌های دیگر که خروجی دستور را تجزیه می‌کنند")

H._run = lambda cmd, **k: (True, """Timezone=UTC
LocalRTC=no
CanNTP=yes
NTP=yes
NTPSynchronized=yes""")
r = H.check_time()
check("همگام‌سازی زمان بدون توجه به ترتیب خوانده می‌شود",
      r and r["level"] == "ok", r and r["detail"])

H._run = lambda cmd, **k: (True, "Timezone=UTC\nNTPSynchronized=no")
check("و ناهمگام را هشدار می‌دهد",
      H.check_time()["level"] == "warn")

H._run = lambda cmd, **k: (True, "Timezone=UTC")
check("اگر systemd این ویژگی را ندهد، حدس نمی‌زند",
      H.check_time() is None,
      "هشدارِ بی‌پایه بدتر از نگفتن است")

head("دیسک و حافظه")

d = H.check_disk()
check("دیسک خوانده می‌شود", d and d["level"] in ("ok", "warn", "crit"),
      d and d["detail"])
m = H.check_memory()
check("حافظه خوانده می‌شود یا صادقانه می‌گوید نشد",
      m and m["level"] in ("ok", "warn", "crit"), m and m["detail"])


print(f"\n{D}{'─' * 50}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
