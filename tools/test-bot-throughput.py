#!/usr/bin/env python3
"""
تست هم‌زمانی حلقه‌ی ربات.

چرا وجود دارد:
    گزارش شد «ربات کند است و با کاربر زیاد به مشکل می‌خورد». علتش
    این بود که آپدیت‌ها یکی‌یکی پردازش می‌شدند: ساخت کانفیگ چند ثانیه
    طول می‌کشد و در تمام آن مدت هیچ پیام دیگری جلو نمی‌رفت.

    این تست دو چیز را می‌سنجد که هر دو باید هم‌زمان درست باشند:
      ۱. کاربرهای مختلف موازی پیش بروند (سرعت)
      ۲. پیام‌های یک کاربر به‌ترتیب بمانند (درستی)

    دومی مهم‌تر است: موازی‌سازی‌ای که ترتیب گفت‌وگوی یک نفر را به هم
    بزند، از کندی بدتر است.

اجرا:  python3 tools/test-bot-throughput.py
"""
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

G, R, D, X = "\033[38;5;42m", "\033[38;5;203m", "\033[38;5;245m", "\033[0m"
_ok = _fail = 0

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


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


# ═══════════ بازسازی منطق حلقه ═══════════
# همان ساختار run.py، بدون تلگرام و دیتابیس، تا فقط رفتار
# هم‌زمانی سنجیده شود.

POOL_SIZE = 8
WORK = 0.25          # هر آپدیت چقدر طول می‌کشد (شبیه ساخت کانفیگ)


def make_runner(pool_size):
    chat_locks = {}
    guard = threading.Lock()
    done = []
    done_lock = threading.Lock()

    def chat_lock(cid):
        with guard:
            lk = chat_locks.get(cid)
            if lk is None:
                lk = chat_locks[cid] = threading.Lock()
        return lk

    def handle(cid, seq):
        with chat_lock(cid):
            time.sleep(WORK)
            with done_lock:
                done.append((cid, seq))

    return ThreadPoolExecutor(max_workers=pool_size), handle, done


head("سرعت با چند کاربر هم‌زمان")

N_USERS = 8
pool, handle, done = make_runner(POOL_SIZE)
t0 = time.time()
for uid in range(N_USERS):
    pool.submit(handle, uid, 0)
pool.shutdown(wait=True)
parallel = time.time() - t0

serial = N_USERS * WORK
check(f"{N_USERS} کاربر هم‌زمان پردازش شدند", len(done) == N_USERS, str(len(done)))
check("موازی از سریالی سریع‌تر است",
      parallel < serial * 0.5,
      f"موازی {parallel:.2f}s در برابر سریالی {serial:.2f}s")
check("همه در حدود یک نوبت تمام شدند",
      parallel < WORK * 2.5, f"{parallel:.2f}s")

head("ترتیب پیام‌های یک کاربر")

pool2, handle2, done2 = make_runner(POOL_SIZE)
SEQ = 6
for i in range(SEQ):
    pool2.submit(handle2, 999, i)
pool2.shutdown(wait=True)

order = [s for c, s in done2 if c == 999]
check("همه‌ی پیام‌های کاربر پردازش شدند", len(order) == SEQ, str(len(order)))
check("ترتیب حفظ شد", order == sorted(order), str(order))

head("کاربر کند، بقیه را بلوکه نمی‌کند")

pool3, _, done3 = make_runner(POOL_SIZE)
locks3 = {}
g3 = threading.Lock()
res3 = []
r3lock = threading.Lock()


def slow_or_fast(cid, delay):
    time.sleep(delay)
    with r3lock:
        res3.append(cid)


pool3.submit(slow_or_fast, "کند", 1.2)
time.sleep(0.05)
for i in range(5):
    pool3.submit(slow_or_fast, f"سریع{i}", 0.05)
pool3.shutdown(wait=True)

fast_done = [c for c in res3 if c.startswith("سریع")]
check("کاربران سریع زودتر از کاربر کند تمام شدند",
      res3.index("کند") == len(res3) - 1,
      " ← ".join(res3[:3]) + " ... ")
check("هیچ کاربری گم نشد", len(res3) == 6, str(len(res3)))

head("کش تنظیمات در Ctx")

import tempfile   # noqa: E402
os.environ["BOT_DB_PATH"] = tempfile.mktemp(suffix=".db")
sys.path.insert(0, os.path.join(ROOT, "bot"))

from bot import db as _db          # noqa: E402
import bot.tg as _tg               # noqa: E402
import bot.handlers as _H          # noqa: E402


class _FakeBot:
    def __init__(self, token=None):
        self.token = token

    def __getattr__(self, n):
        return lambda *a, **k: {"message_id": 1, "chat": {"id": 1}}


_tg.Bot = _FakeBot
_H.Bot = _FakeBot
_db.init_db()
_tid = _db.create_tenant("T", bot_token="1:X", owner_tg_id=9)
_db.save_tenant_settings(_tid, {"brand": "Nexora", "coins": {"per_referral": 10}})
_tenant = _db.get_tenant(_tid)

_reads = {"n": 0}
_orig = _db.tenant_settings


def _counting(tid):
    _reads["n"] += 1
    return _orig(tid)


_db.tenant_settings = _counting
_H.DB.tenant_settings = _counting

_ctx = _H.Ctx(_FakeBot(), _tenant)
_reads["n"] = 0
for _ in range(30):
    _ctx.s
check("۳۰ دسترسی به ctx.s فقط یک بار دیسک می‌خورد",
      _reads["n"] == 1, f"{_reads['n']} بار خواندن")

# تغییر تنظیمات از پنل باید بعد از TTL دیده شود
_H.Ctx.CACHE_TTL = 0.05
_ctx2 = _H.Ctx(_FakeBot(), _tenant)
_ = _ctx2.s
_db.save_tenant_settings(_tid, {"brand": "عوض‌شده"})
time.sleep(0.12)
check("تغییر تنظیمات پنل بعد از TTL دیده می‌شود",
      _ctx2.s.get("brand") == "عوض‌شده", str(_ctx2.s.get("brand")))

_ctx3 = _H.Ctx(_FakeBot(), _tenant)
_ = _ctx3.s
_ctx3.invalidate()
_reads["n"] = 0
_ = _ctx3.s
check("invalidate کش را دور می‌ریزد", _reads["n"] == 1, f"{_reads['n']} بار")

_db.tenant_settings = _orig
_H.DB.tenant_settings = _orig
_H.Ctx.CACHE_TTL = 2

head("تنظیمات واقعی run.py")

import importlib.util   # noqa: E402
spec = importlib.util.spec_from_file_location(
    "_run_probe", os.path.join(ROOT, "bot", "run.py"))
src = open(os.path.join(ROOT, "bot", "run.py"), encoding="utf-8").read()

check("استخر نخ در حلقه هست", "ThreadPoolExecutor" in src)
check("قفل هر چت هست", "chat_lock" in src)
check("Bot بیرون حلقه ساخته می‌شود",
      "if tg is None or tg.token" in src)
check("اندازه‌ی استخر قابل تنظیم است", "BOT_POOL_SIZE" in src)
check("dispatch مستقیم در حلقه صدا زده نمی‌شود",
      "pool.submit(handle" in src and
      "\n                    handlers.dispatch(tenant, tg, up)" not in src)

print(f"\n{D}{'─' * 46}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
