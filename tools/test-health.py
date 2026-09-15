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


head("بررسی DNS خودش هنگ نمی‌کند")

# این بررسی اصلاً برای تشخیص DNSِ کند نوشته شده. ولی gethostbyname
# مهلت نمی‌پذیرد — از resolver سیستم می‌رود و مهلت خودش را دارد که
# می‌تواند ده‌ها ثانیه باشد. یعنی دقیقاً وقتی باید هشدار می‌داد،
# خودش کل گزارش سلامت را نگه می‌داشت: هم در پنل، هم روی نود ایران.

import socket as _sk
import threading as _thr
import time as _tm

_HANG = _thr.Event()
_real_ghn = _sk.gethostbyname


def _never(host):
    _HANG.wait(30)
    return "1.2.3.4"


_sk.gethostbyname = _never
H.DNS_DEADLINE = 1.0

_t0 = _tm.time()
r = H.check_dns()
_took = _tm.time() - _t0

check("با resolverِ بی‌جواب هم سر وقت برمی‌گردد", _took < 3.0,
      f"{_took:.1f} ثانیه با مهلت ۱ ثانیه")
check("و آن را بحرانی گزارش می‌کند", r and r["level"] == "crit",
      r and r["detail"])
check("دلیلش را می‌گوید", r and "جواب نداد" in r["detail"], r and r["detail"])

_HANG.set()
_tm.sleep(0.2)

_sk.gethostbyname = lambda h: "1.2.3.4"
H.DNS_DEADLINE = 4.0
r2 = H.check_dns()
check("resolverِ سالم سالم گزارش می‌شود", r2 and r2["level"] in ("ok", "warn"),
      r2 and r2["detail"])


def _boom(host):
    raise OSError("نام حل نشد")


_sk.gethostbyname = _boom
r3 = H.check_dns()
check("خطای واقعی resolve هم بحرانی است", r3 and r3["level"] == "crit")
check("و با «بی‌جواب» اشتباه نمی‌شود",
      r3 and "OSError" in r3["detail"], r3 and r3["detail"])

_sk.gethostbyname = _real_ghn



# ═══════════════════════════════════════════════════════════
head("هشدار سلامت — به چه کسی، و چه وقت")

# این تنها راهی است که مالک می‌فهمد سرورش مشکل دارد. دو ایراد داشت و
# هر دو به سکوت یا به آدرس اشتباه ختم می‌شدند.

import json as _json          # noqa: E402
import sqlite3 as _sq         # noqa: E402
import urllib.request as _ur  # noqa: E402

_APPTMP = tempfile.mkdtemp()
_spec = importlib.util.spec_from_file_location(
    "nxapp_alert", os.path.join(ROOT, "backend", "app.py"))
_AP = importlib.util.module_from_spec(_spec)
sys.modules["nxapp_alert"] = _AP
_spec.loader.exec_module(_AP)
_AP.BOT_DB = Path(_APPTMP) / "bot.db"

_sent = []


def _fake_urlopen(req, timeout=None):
    _sent.append({"url": req.full_url,
                  "body": _json.loads(req.data.decode("utf-8"))})

    class _R:
        def read(self_):
            return b"{}"

        def __enter__(self_):
            return self_

        def __exit__(self_, *a):
            return False
    return _R()


_ur.urlopen = _fake_urlopen


def _tenants(rows):
    """بازسازی جدول مستاجرها با ردیف‌های داده‌شده."""
    c = _sq.connect(str(_AP.BOT_DB))
    c.execute("DROP TABLE IF EXISTS tenants")
    c.execute("""CREATE TABLE tenants (id INTEGER PRIMARY KEY, name TEXT,
                 parent_id INTEGER, bot_token TEXT, admin_id INTEGER,
                 group_id INTEGER)""")
    c.executemany("INSERT INTO tenants VALUES (?,?,?,?,?,?)", rows)
    c.commit()
    c.close()


def _fire(key, level):
    _AP._health_alert("سرور تست", {"level": level, "summary": "خلاصه",
                                   "checks": []}, key=key)


# ── سروری که از همان ابتدا خراب است ──
#
# وضعیت در حافظه‌ی همین پردازه است، پس هر ری‌استارت پاکش می‌کند — و
# `nexora update` هر بار ری‌استارت می‌کند. قبلاً اولین مشاهده ساکت
# بود و بقیه هم چون سطح عوض نشده بود ساکت می‌ماندند: دیسک تا ابد پر
# و هیچ پیامی.
_tenants([(1, "owner", None, "OWNER", 111, -100)])
_AP._health_state.clear()
_sent.clear()
for _ in range(3):
    _fire("boot", "crit")
check("سرورِ خراب از لحظه‌ی بالا آمدن خبر می‌دهد", len(_sent) == 1,
      f"{len(_sent)} پیام — یکی، نه صفر و نه سه تا")

# ── سرور سالم هیچ پیامی نمی‌سازد ──
_AP._health_state.clear()
_sent.clear()
_fire("quiet", "ok")
_fire("quiet", "ok")
check("ری‌استارتِ سرور سالم پیام نمی‌سازد", not _sent,
      f"{len(_sent)} پیام")

# ── گذارها ──
_AP._health_state.clear()
_sent.clear()
for _lvl in ("ok", "warn", "warn", "crit", "ok"):
    _fire("flow", _lvl)
check("فقط گذارها خبر می‌شوند", len(_sent) == 3,
      "ok→warn، warn→crit، crit→ok")
check("و پیام بازگشت هم می‌آید",
      any("برطرف" in m["body"]["text"] for m in _sent))

# ── با کدام ربات، و به کدام گروه ──
#
# اگر ردیف مالک یک‌بار پاک و دوباره ساخته شود — که با اجرای دوباره‌ی
# نصب اتفاق می‌افتد — شناسه‌اش از شناسه‌ی نماینده بزرگ‌تر می‌شود.
# بدون شرط parent_id، هشدارِ سرورِ مالک با رباتِ نماینده و به گروهِ
# نماینده می‌رفت.
_tenants([(2, "reseller", 1, "RESELLER", 222, -200),
          (9, "owner", None, "OWNER", 111, -100)])
_AP._health_state.clear()
_sent.clear()
_fire("who", "crit")
check("هشدار با رباتِ مالک فرستاده می‌شود",
      len(_sent) == 1 and "OWNER" in _sent[0]["url"],
      _sent[0]["url"].split("/bot")[-1].split("/")[0] if _sent else "هیچ")
check("و به گروهِ مالک، نه نماینده",
      len(_sent) == 1 and _sent[0]["body"]["chat_id"] == -100,
      str(_sent[0]["body"]["chat_id"]) if _sent else "هیچ")

# ── گروه که نباشد، به خودِ مدیر ──
_tenants([(1, "owner", None, "OWNER", 111, None)])
_AP._health_state.clear()
_sent.clear()
_fire("dm", "warn")
check("بدون گروه، پیام به شناسه‌ی مدیر می‌رود",
      len(_sent) == 1 and _sent[0]["body"]["chat_id"] == 111,
      str(_sent[0]["body"]["chat_id"]) if _sent else "هیچ")

# ── بدون توکن، بی‌صدا رد می‌شود و نمی‌ترکد ──
_tenants([(1, "owner", None, None, 111, -100)])
_AP._health_state.clear()
_sent.clear()
try:
    _fire("notoken", "crit")
    _crashed = False
except Exception as _e:
    _crashed = str(_e)
check("نبودِ توکن ربات خطا نمی‌دهد", not _crashed and not _sent,
      _crashed or "بدون پیام، بدون خطا")


print(f"\n{D}{'─' * 50}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
