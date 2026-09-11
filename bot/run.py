"""
نقطه‌ی شروع ماژول ربات Nexora.

این فایل دو کار می‌کند:
  ۱. برای هر مستاجر فعال، یک حلقه‌ی polling تلگرام اجرا می‌کند
  ۲. یک زمان‌بند برای کارهای دوره‌ای (یادآوری، تمدید خودکار، بک‌آپ)

اجرا:
    python3 -m bot.run

متغیرهای محیطی:
    BOT_DB_PATH   مسیر دیتابیس (پیش‌فرض ../data/bot.db)
    BOT_LOG_LEVEL INFO | DEBUG
"""
import logging
import os
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import db, core, handlers
from bot.tg import Bot, TelegramError

log = logging.getLogger("nexora.bot")

_stop = threading.Event()
_workers = {}          # tenant_id → Thread
_lock = threading.Lock()

#: چند آپدیت هم‌زمان برای هر مستاجر.
#: هشت یعنی هشت کاربر می‌توانند هم‌زمان کانفیگ بگیرند بدون
#: اینکه منتظر هم بمانند؛ بالاتر از این، محدودیت نرخ تلگرام
#: و پنل 3x-ui گلوگاه می‌شوند نه ما.
POOL_SIZE = int(os.getenv("BOT_POOL_SIZE", "8"))


# ═══════════════════════════════════════════════════════════
#  حلقه‌ی هر مستاجر
# ═══════════════════════════════════════════════════════════

def tenant_loop(tenant_id: int):
    """
    حلقه‌ی polling یک مستاجر.

    اگر توکن نامعتبر شود یا مستاجر غیرفعال شود، حلقه تمیز خارج می‌شود.
    خطاهای موقت شبکه باعث توقف نمی‌شوند — با backoff دوباره تلاش می‌کند.
    """
    offset = 0
    backoff = 1
    tg = None
    name = f"tenant-{tenant_id}"

    # ── چرا اینجا استخر نخ داریم ──
    #
    # قبلاً آپدیت‌ها یکی‌یکی و پشت‌سرهم پردازش می‌شدند. ساخت کانفیگ
    # در 3x-ui چند ثانیه طول می‌کشد (لاگین، افزودن کلاینت، بازخوانی،
    # گرفتن لینک) و در تمام آن مدت *هیچ* پیام دیگری پردازش نمی‌شد.
    # با ده کاربر هم‌زمان، نفر دهم ده‌ها ثانیه منتظر می‌ماند.
    #
    # حالا هر آپدیت به استخر می‌رود، ولی پیام‌های یک کاربر با قفلِ
    # همان چت سریالی می‌مانند — وگرنه دو پیام پشت‌سرهم یک نفر
    # می‌توانستند جابه‌جا اجرا شوند و وضعیت گفت‌وگو خراب شود.
    pool = ThreadPoolExecutor(max_workers=POOL_SIZE,
                              thread_name_prefix=f"{name}-w")
    chat_locks = {}
    locks_guard = threading.Lock()

    def chat_lock(update):
        msg = (update.get("message") or update.get("callback_query", {})
               .get("message") or {})
        cid = (msg.get("chat") or {}).get("id")
        if cid is None:
            cid = ((update.get("callback_query") or {}).get("from")
                   or {}).get("id", 0)
        with locks_guard:
            lk = chat_locks.get(cid)
            if lk is None:
                lk = chat_locks[cid] = threading.Lock()
            # جلوگیری از رشد بی‌پایان در ربات پرترافیک
            if len(chat_locks) > 5000:
                for k in [k for k, v in list(chat_locks.items())
                          if k != cid and not v.locked()][:2500]:
                    chat_locks.pop(k, None)
        return lk

    def handle(tenant_snapshot, bot, update):
        try:
            with chat_lock(update):
                handlers.dispatch(tenant_snapshot, bot, update)
        except Exception:
            log.exception("%s: خطا در پردازش آپدیت %s",
                          name, update.get("update_id"))

    while not _stop.is_set():
        try:
            tenant = db.get_tenant(tenant_id)
            if not tenant or not tenant["is_active"] or not tenant["bot_token"]:
                log.info("%s: غیرفعال یا بدون توکن — خروج", name)
                return

            # Bot را یک‌بار می‌سازیم و نگه می‌داریم.
            #
            # قبلاً در هر دور حلقه یکی نو ساخته می‌شد، یعنی نشست
            # requests و اتصال باز TLS هر بار دور ریخته می‌شد و
            # فراخوانی بعدی از صفر دست می‌داد. روی مسیر ایران به
            # تلگرام، همین تنهایی چند صد میلی‌ثانیه به هر پیام
            # اضافه می‌کرد.
            if tg is None or tg.token != tenant["bot_token"]:
                tg = Bot(tenant["bot_token"])

            updates = tg.updates(offset=offset, timeout=25)
            backoff = 1

            for up in updates:
                offset = up["update_id"] + 1
                if _stop.is_set():
                    break
                pool.submit(handle, tenant, tg, up)

        except TelegramError as e:
            msg = str(e)
            if "401" in msg or "Unauthorized" in msg:
                log.error("%s: توکن نامعتبر است — غیرفعال شد", name)
                db.update_tenant(tenant_id, is_active=0)
                return
            log.warning("%s: خطای تلگرام: %s", name, msg)
            _stop.wait(min(backoff, 60))
            backoff = min(backoff * 2, 60)

        except Exception:
            log.exception("%s: خطای غیرمنتظره", name)
            _stop.wait(min(backoff, 60))
            backoff = min(backoff * 2, 60)


def sync_workers():
    """
    مستاجرهای فعال را با نخ‌های در حال اجرا هماهنگ می‌کند.
    مستاجر جدید → نخ جدید. مستاجر حذف/غیرفعال → نخ خودش خارج می‌شود.
    """
    with _lock:
        active = {t["id"] for t in db.all_tenants(active_only=True) if t["bot_token"]}

        # حذف نخ‌های تمام‌شده
        for tid in list(_workers):
            if not _workers[tid].is_alive():
                _workers.pop(tid, None)

        for tid in active:
            if tid not in _workers:
                th = threading.Thread(target=tenant_loop, args=(tid,),
                                      name=f"tenant-{tid}", daemon=True)
                th.start()
                _workers[tid] = th
                log.info("ربات مستاجر %s راه‌اندازی شد", tid)


# ═══════════════════════════════════════════════════════════
#  کارهای دوره‌ای
# ═══════════════════════════════════════════════════════════

def expire_stale_orders():
    """سفارش‌هایی که مهلت پرداختشان گذشته را منقضی می‌کند."""
    n = 0
    for t in db.all_tenants():
        d = db.TenantDB(t["id"])
        rows = d.q(
            """SELECT id FROM orders
               WHERE tenant_id=? AND status='pending'
                 AND expires_at IS NOT NULL AND expires_at < ?""",
            (t["id"], datetime.now().isoformat())
        )
        for r in rows:
            d.exec("UPDATE orders SET status='expired' WHERE tenant_id=? AND id=?",
                   (t["id"], r["id"]))
            n += 1
    if n:
        log.info("%s سفارش منقضی شد", n)


def send_expiry_reminders():
    """
    یادآوری انقضا در ۷، ۳ و ۱ روز مانده.

    هر یادآوری فقط یک‌بار ارسال می‌شود (پرچم notified_*) تا کاربر
    با پیام تکراری آزار نبیند.
    """
    now = datetime.now(timezone.utc)
    for t in db.all_tenants(active_only=True):
        if not t["bot_token"]:
            continue
        d = db.TenantDB(t["id"])
        cfg = db.tenant_settings(t["id"])
        if cfg.get("reminders", {}).get("enabled") is False:
            continue

        tg = Bot(t["bot_token"])
        subs = d.q(
            """SELECT s.*, u.tg_id FROM subscriptions s
               JOIN users u ON u.id = s.user_id
               WHERE s.tenant_id=? AND s.is_active=1 AND s.expires_at IS NOT NULL""",
            (t["id"],)
        )

        for s in subs:
            left = core.days_left(s["expires_at"])
            if left is None or left < 0:
                continue

            for day, flag in ((7, "notified_7d"), (3, "notified_3d"), (1, "notified_1d")):
                if left <= day and not s[flag]:
                    try:
                        handlers.send_expiry_notice(t, tg, s, left)
                        d.exec(
                            f"UPDATE subscriptions SET {flag}=1 WHERE tenant_id=? AND id=?",
                            (t["id"], s["id"])
                        )
                        log.info("یادآوری %s روز برای اشتراک %s", day, s["id"])
                    except Exception:
                        log.exception("ارسال یادآوری ناموفق (اشتراک %s)", s["id"])
                    break


def run_auto_renew():
    """
    تمدید خودکار از کیف پول برای اشتراک‌هایی که auto_renew دارند.

    فقط وقتی انجام می‌شود که موجودی کافی باشد؛ در غیر این‌صورت به کاربر
    اطلاع داده می‌شود تا خودش شارژ کند.
    """
    for t in db.all_tenants(active_only=True):
        if not t["bot_token"]:
            continue
        d = db.TenantDB(t["id"])
        tg = Bot(t["bot_token"])

        subs = d.q(
            """SELECT s.*, u.tg_id, u.balance FROM subscriptions s
               JOIN users u ON u.id = s.user_id
               WHERE s.tenant_id=? AND s.is_active=1 AND s.auto_renew=1""",
            (t["id"],)
        )

        for s in subs:
            left = core.days_left(s["expires_at"])
            if left is None or left > 1:
                continue
            try:
                handlers.auto_renew_subscription(t, tg, s)
            except Exception:
                log.exception("تمدید خودکار ناموفق (اشتراک %s)", s["id"])


def daily_report():
    """گزارش روزانه در گروه مدیریت هر مستاجر."""
    for t in db.all_tenants(active_only=True):
        if not t["bot_token"]:
            continue
        try:
            handlers.send_daily_report(t)
        except Exception:
            log.exception("گزارش روزانه ناموفق (مستاجر %s)", t["id"])


def process_panel_approvals():
    """
    سفارش‌هایی که از پنل مدیریت تایید شده‌اند را تحویل می‌دهد.

    پنل به 3x-ui و تلگرام دسترسی ندارد، پس فقط وضعیت را روی
    panel_approve می‌گذارد؛ ربات اینجا کار را تمام می‌کند:
    ساخت کانفیگ، ارسال به مشتری، اعطای سکه معرف.
    """
    try:
        with db.conn() as cx:
            rows = cx.execute(
                "SELECT id, tenant_id, status, admin_note FROM orders "
                "WHERE status IN ('panel_approve','panel_reject') LIMIT 20"
            ).fetchall()
    except Exception as e:
        log.warning("خواندن سفارش‌های پنل ناموفق: %s", e)
        return

    for r in rows:
        oid, tid = r["id"], r["tenant_id"]
        try:
            tenant = db.get_tenant(tid)
            if not tenant or not tenant.get("bot_token"):
                continue

            tg = Bot(tenant["bot_token"])
            ctx = handlers.Ctx(tg, tenant)

            if r["status"] == "panel_reject":
                handlers.do_reject(ctx, oid, 0,
                                   r["admin_note"] or "رسید تایید نشد.")
                log.info("سفارش %s از پنل رد شد", oid)
                continue

            ok, note = handlers.approve_order(ctx, oid, admin_tg_id=0)

            if ok:
                log.info("سفارش %s از پنل تحویل شد", oid)
            else:
                log.warning("تحویل سفارش %s ناموفق: %s", oid, note)
                with db.conn() as cx:
                    cx.execute(
                        "UPDATE orders SET status='awaiting', admin_note=? WHERE id=?",
                        (f"تحویل ناموفق: {str(note)[:120]}", oid))
        except Exception as e:
            log.error("خطا در تحویل سفارش %s: %s", oid, e)
            try:
                with db.conn() as cx:
                    cx.execute(
                        "UPDATE orders SET status='awaiting', admin_note=? WHERE id=?",
                        (f"خطای تحویل: {str(e)[:120]}", oid))
            except Exception:
                pass


def scheduler_loop():
    """
    زمان‌بند ساده و بدون وابستگی خارجی.

    از APScheduler استفاده نمی‌کنیم تا نصب سبک بماند؛ این حلقه
    برای بازه‌های چنددقیقه‌ای کاملاً کافی است.
    """
    last = {"orders": 0, "panel": 0, "reminders": 0, "renew": 0, "report_day": None}

    while not _stop.is_set():
        now = time.time()
        try:
            if now - last["orders"] > 120:
                expire_stale_orders()
                last["orders"] = now

            # تاییدهای پنل را سریع‌تر بررسی می‌کنیم — مشتری منتظر است
            if now - last.get("panel", 0) > 20:
                process_panel_approvals()
                last["panel"] = now

            if now - last["reminders"] > 3600:
                send_expiry_reminders()
                last["reminders"] = now

            if now - last["renew"] > 3600:
                run_auto_renew()
                last["renew"] = now

            today = datetime.now().date()
            if datetime.now().hour == 23 and last["report_day"] != today:
                daily_report()
                last["report_day"] = today

            # اگر پنل اعلام کرده تنظیمات عوض شده، نخ‌ها را همگام می‌کنیم.
            # این باعث قطعی نمی‌شود؛ فقط مستاجرهای جدید/غیرفعال را می‌گیرد.
            try:
                with db.conn() as cx:
                    row = cx.execute(
                        "SELECT value FROM bot_flags WHERE key='reload'").fetchone()
                    if row and row["value"] != last.get("reload_seen"):
                        last["reload_seen"] = row["value"]
                        log.info("پنل تغییر تنظیمات را اعلام کرد — همگام‌سازی")
            except Exception:
                pass

            sync_workers()

        except Exception:
            log.exception("خطا در زمان‌بند")

        _stop.wait(30)


# ═══════════════════════════════════════════════════════════
#  اجرا
# ═══════════════════════════════════════════════════════════

def shutdown(signum, frame):
    log.info("سیگنال %s — در حال خاموش شدن...", signum)
    _stop.set()


def main():
    logging.basicConfig(
        level=os.getenv("BOT_LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    db.init_db()
    log.info("دیتابیس آماده: %s", db.DB_PATH)

    tenants = [t for t in db.all_tenants(active_only=True) if t["bot_token"]]
    if not tenants:
        log.warning("هیچ مستاجر فعالی با توکن ربات پیدا نشد — منتظر پیکربندی از پنل")
    else:
        log.info("%s مستاجر فعال", len(tenants))

    sync_workers()

    sch = threading.Thread(target=scheduler_loop, name="scheduler", daemon=True)
    sch.start()
    log.info("زمان‌بند فعال شد")

    try:
        while not _stop.is_set():
            _stop.wait(1)
    except KeyboardInterrupt:
        _stop.set()

    log.info("خاموش شد")


if __name__ == "__main__":
    main()
