"""
لایه‌ی دیتابیس ماژول ربات.

نکته‌ی حیاتی امنیتی: هر جدولی که داده‌ی مستاجر دارد، ستون tenant_id دارد
و همه‌ی دسترسی‌ها از کلاس TenantDB می‌گذرد که خودکار فیلتر می‌کند.
این کار جلوی نشت داده بین مستاجرها را از سطح کد می‌گیرد، نه فقط با
یادآوری به برنامه‌نویس.
"""

import os
import json
import sqlite3
import secrets
import string
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import contextmanager

DB_PATH = Path(os.getenv("BOT_DB_PATH", "../data/bot.db"))

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ═══ مستاجرها (هر ربات یک مستاجر) ═══
CREATE TABLE IF NOT EXISTS tenants (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    bot_token         TEXT UNIQUE,
    bot_username      TEXT,
    owner_tg_id       INTEGER,
    parent_id         INTEGER REFERENCES tenants(id) ON DELETE SET NULL,
    is_active         INTEGER DEFAULT 1,
    -- اعتبار واسطه (تومان). برای مستاجر اصلی نامحدود = -1
    credit            INTEGER DEFAULT 0,
    credit_discount   INTEGER DEFAULT 0,      -- درصد تخفیف عمده واسطه
    -- اتصال به پنل 3x-ui
    panel_url         TEXT,
    panel_user        TEXT,
    panel_pass        TEXT,
    panel_token       TEXT,
    default_inbound   INTEGER,
    -- گروه مدیریت
    admin_group_id    INTEGER,
    topics            TEXT DEFAULT '{}',      -- JSON: نگاشت نام تاپیک به id
    settings          TEXT DEFAULT '{}',      -- JSON: برند، کارت‌ها، متن‌ها
    created_at        TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ═══ کاربران ═══
-- ═══════════════════════════════════════════════════════
--  همکاری در فروش
--
--  با «دعوت دوستان» فرق دارد: آن سکه می‌دهد به مشتری عادی،
--  این پورسانت نقدی می‌دهد به کسی که کارش فروش است.
-- ═══════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS affiliates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    code        TEXT NOT NULL,
    tg_id       INTEGER,
    percent     REAL NOT NULL DEFAULT 10,
    active      INTEGER DEFAULT 1,
    note        TEXT,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, code)
);

-- هر پورسانت به یک سفارش مشخص گره خورده، تا بعداً قابل ردیابی باشد
CREATE TABLE IF NOT EXISTS affiliate_commissions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id     INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    affiliate_id  INTEGER NOT NULL REFERENCES affiliates(id) ON DELETE CASCADE,
    order_id      INTEGER,
    user_id       INTEGER,
    order_amount  INTEGER NOT NULL DEFAULT 0,
    percent       REAL NOT NULL DEFAULT 0,
    commission    INTEGER NOT NULL DEFAULT 0,
    status        TEXT DEFAULT 'pending',      -- pending | paid | cancelled
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, order_id)
);

CREATE TABLE IF NOT EXISTS affiliate_payouts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id     INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    affiliate_id  INTEGER NOT NULL REFERENCES affiliates(id) ON DELETE CASCADE,
    amount        INTEGER NOT NULL,
    note          TEXT,
    paid_at       TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_aff_code ON affiliates(tenant_id, code);
CREATE INDEX IF NOT EXISTS idx_comm_aff ON affiliate_commissions(affiliate_id, status);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id     INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tg_id         INTEGER NOT NULL,
    username      TEXT,
    first_name    TEXT,
    phone         TEXT,
    balance       INTEGER DEFAULT 0,          -- کیف پول (تومان)
    coins         INTEGER DEFAULT 0,
    ref_code      TEXT UNIQUE,
    referred_by   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    is_blocked    INTEGER DEFAULT 0,
    trial_used    INTEGER DEFAULT 0,
    phone_asked   INTEGER DEFAULT 0,      -- یک‌بار پرسیده‌ایم؟
    lang          TEXT DEFAULT 'fa',
    state         TEXT,                       -- وضعیت مکالمه
    state_data    TEXT DEFAULT '{}',
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    last_seen     TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, tg_id)
);
CREATE INDEX IF NOT EXISTS ix_users_tenant ON users(tenant_id, tg_id);

-- ═══ پلن‌ها ═══
CREATE TABLE IF NOT EXISTS plans (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id     INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    description   TEXT DEFAULT '',
    gb            INTEGER NOT NULL,           -- 0 = نامحدود
    days          INTEGER NOT NULL,
    ip_limit      INTEGER DEFAULT 2,
    price         INTEGER NOT NULL,
    inbound_id    INTEGER,
    is_active     INTEGER DEFAULT 1,
    is_trial      INTEGER DEFAULT 0,
    sort_order    INTEGER DEFAULT 0,
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_plans_tenant ON plans(tenant_id);

-- ═══ سفارش‌ها ═══
CREATE TABLE IF NOT EXISTS orders (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id      INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id        INTEGER REFERENCES plans(id) ON DELETE SET NULL,
    kind           TEXT DEFAULT 'new',        -- new | renew | topup
    amount         INTEGER NOT NULL,          -- مبلغ نهایی
    base_amount    INTEGER NOT NULL,          -- قبل از تخفیف
    coins_used     INTEGER DEFAULT 0,
    discount_code  TEXT,
    discount_pct   INTEGER DEFAULT 0,
    paid_from      TEXT DEFAULT 'card',       -- card | wallet
    status         TEXT DEFAULT 'pending',    -- pending|awaiting|approved|rejected|expired
    receipt_type   TEXT,                      -- photo | text
    receipt_file   TEXT,
    receipt_text   TEXT,
    card_used      TEXT,
    admin_note     TEXT,
    reviewed_by    INTEGER,
    sub_id         INTEGER,
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
    expires_at     TEXT,
    reviewed_at    TEXT
);
CREATE INDEX IF NOT EXISTS ix_orders_tenant ON orders(tenant_id, status);
CREATE INDEX IF NOT EXISTS ix_orders_user ON orders(user_id);

-- ═══ اشتراک‌ها ═══
CREATE TABLE IF NOT EXISTS subscriptions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id     INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_id      INTEGER REFERENCES orders(id) ON DELETE SET NULL,
    plan_id       INTEGER REFERENCES plans(id) ON DELETE SET NULL,
    client_email  TEXT NOT NULL,              -- شناسه در 3x-ui
    client_uuid   TEXT,
    sub_url       TEXT,
    inbound_id    INTEGER,
    gb            INTEGER,
    expires_at    TEXT,
    auto_renew    INTEGER DEFAULT 0,
    is_active     INTEGER DEFAULT 1,
    notified_7d   INTEGER DEFAULT 0,
    notified_3d   INTEGER DEFAULT 0,
    notified_1d   INTEGER DEFAULT 0,
    notified_80p  INTEGER DEFAULT 0,
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_subs_tenant ON subscriptions(tenant_id, is_active);
CREATE INDEX IF NOT EXISTS ix_subs_user ON subscriptions(user_id);

-- ═══ تراکنش سکه ═══
CREATE TABLE IF NOT EXISTS coin_tx (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount      INTEGER NOT NULL,             -- مثبت = دریافت، منفی = مصرف
    kind        TEXT NOT NULL,                -- referral|spend|admin|bonus
    note        TEXT,
    ref_user_id INTEGER,
    order_id    INTEGER,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_cointx_user ON coin_tx(user_id);

-- ═══ تراکنش کیف پول ═══
CREATE TABLE IF NOT EXISTS wallet_tx (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount      INTEGER NOT NULL,
    kind        TEXT NOT NULL,                -- deposit|spend|refund|admin
    note        TEXT,
    order_id    INTEGER,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_wtx_user ON wallet_tx(user_id);

-- ═══ کد تخفیف ═══
CREATE TABLE IF NOT EXISTS discounts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code        TEXT NOT NULL,
    percent     INTEGER NOT NULL,
    max_uses    INTEGER DEFAULT 0,            -- 0 = نامحدود
    used_count  INTEGER DEFAULT 0,
    plan_id     INTEGER,
    expires_at  TEXT,
    is_active   INTEGER DEFAULT 1,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, code)
);

-- ═══ تیکت پشتیبانی ═══
CREATE TABLE IF NOT EXISTS tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message     TEXT NOT NULL,
    status      TEXT DEFAULT 'open',          -- open|answered|closed
    answer      TEXT,
    topic_msg   INTEGER,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    answered_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_tickets_tenant ON tickets(tenant_id, status);

-- ═══ لاگ رویدادها (برای آمار و عیب‌یابی) ═══
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   INTEGER,
    user_id     INTEGER,
    kind        TEXT NOT NULL,
    data        TEXT DEFAULT '{}',
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_events_tenant ON events(tenant_id, kind);
"""


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), timeout=20)
    con.row_factory = sqlite3.Row

    # WAL: خواندن و نوشتن هم‌زمان همدیگر را قفل نمی‌کنند.
    #
    # در حالت پیش‌فرض (journal=delete) هر نوشتن کل دیتابیس را قفل
    # می‌کند و هر خواننده‌ای باید منتظر بماند. تا وقتی آپدیت‌ها
    # یکی‌یکی پردازش می‌شدند این دیده نمی‌شد، ولی حالا که هشت نخ
    # هم‌زمان کار می‌کنند، دقیقاً همان‌جایی است که به گلوگاه می‌خورد.
    #
    # synchronous=NORMAL در کنار WAL امن است: در برق‌رفتن، آخرین
    # تراکنش‌های commit‌شده سالم می‌مانند.
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        con.execute("PRAGMA busy_timeout=20000")
    except sqlite3.Error:
        # روی فایل‌سیستم شبکه‌ای WAL پشتیبانی نمی‌شود — همان حالت
        # پیش‌فرض کار می‌کند، فقط کندتر
        pass

    return con


def _migrate(con):
    """ستون‌های جدید را به دیتابیس‌های موجود اضافه می‌کند."""
    adds = [
        ("users", "phone_asked", "INTEGER DEFAULT 0"),
        # کدام همکار فروش این کاربر را آورده — تا پورسانت هر خریدش
        # به همان نفر برسد، نه فقط خرید اول
        ("users", "affiliate_id", "INTEGER"),
        # اینباندهای هر پلن — خالی یعنی از تنظیم سراسری پیروی کن
        ("plans", "inbound_ids", "TEXT"),
        # حالت پیش‌فرض: all | default | custom
        ("tenants", "inbound_mode", "TEXT DEFAULT 'all'"),
        ("tenants", "inbound_ids", "TEXT"),
        # نام پلن، همان‌طور که لحظه‌ی خرید بود.
        #
        # plan_id با ON DELETE SET NULL وصل است، پس اگر مدیر پلنی را
        # حذف یا جایگزین کند، نام آن اشتراک از بین می‌رود و مشتری
        # به‌جای «یک‌ماهه پرسرعت» فقط نام اینباند را می‌بیند — چیزی
        # که هیچ‌وقت نخریده. این ستون همان نام را نگه می‌دارد.
        ("subscriptions", "plan_name", "TEXT"),
        # کدام اشتراک قرار است تمدید شود.
        #
        # sub_id موجود *بعد* از ساخت پر می‌شود و نتیجه را نگه می‌دارد؛
        # این یکی مقصد را از همان لحظه‌ی ثبت سفارش مشخص می‌کند.
        ("orders", "renew_sub_id", "INTEGER"),
    ]
    for table, col, spec in adds:
        try:
            cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
            if col not in cols:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {spec}")
        except sqlite3.Error:
            pass

    # نام پلن اشتراک‌های قدیمی را از جدول پلن‌ها پر می‌کنیم.
    #
    # تا وقتی پلن هنوز هست این کار شدنی است؛ بعد از حذفش دیگر هیچ
    # جایی آن نام را ندارد. پس همین یک بار، برای هرچه موجود است.
    try:
        con.execute(
            "UPDATE subscriptions SET plan_name = ("
            "  SELECT name FROM plans WHERE plans.id = subscriptions.plan_id) "
            "WHERE (plan_name IS NULL OR plan_name = '') "
            "  AND plan_id IS NOT NULL")
    except sqlite3.Error:
        pass


# ═══════════════════════════════════════════════════════════
#  همکاری در فروش
# ═══════════════════════════════════════════════════════════

def affiliate_by_code(tenant_id, code):
    """پیدا کردن همکار از روی کد — برای وقتی کاربر با لینکش می‌آید."""
    con = _connect()
    try:
        r = con.execute(
            "SELECT * FROM affiliates WHERE tenant_id=? AND code=? AND active=1",
            (tenant_id, (code or "").strip())).fetchone()
        return dict(r) if r else None
    finally:
        con.close()


def affiliate_by_tg(tenant_id, tg_id):
    con = _connect()
    try:
        r = con.execute(
            "SELECT * FROM affiliates WHERE tenant_id=? AND tg_id=? AND active=1",
            (tenant_id, tg_id)).fetchone()
        return dict(r) if r else None
    finally:
        con.close()


def record_commission(tenant_id, user_id, order_id, amount):
    """
    ثبت پورسانت یک سفارش.

    فقط وقتی ثبت می‌شود که کاربر همکاری داشته باشد و برای آن
    سفارش قبلاً ثبت نشده باشد — تا اگر تاییدی دوباره اجرا شد،
    پورسانت دو بار حساب نشود.
    """
    if not amount or amount <= 0:
        return None

    con = _connect()
    try:
        # هر دو جست‌وجو به مستاجر محدود می‌شوند.
        #
        # شناسه‌ها سراسری‌اند، پس بدون این هم نتیجه درست درمی‌آمد — تا
        # روزی که صداکننده‌ای user_id یک مستاجر را با tenant_id مستاجر
        # دیگر بدهد. آن‌وقت پورسانت به همکارِ فروشگاه دیگری می‌رسید و
        # هیچ‌جا خطایی هم نمی‌داد. شرط اضافه رایگان است.
        u = con.execute(
            "SELECT affiliate_id FROM users WHERE id=? AND tenant_id=?",
            (user_id, tenant_id)).fetchone()
        if not u or not u["affiliate_id"]:
            return None

        aff = con.execute(
            "SELECT * FROM affiliates WHERE id=? AND tenant_id=? AND active=1",
            (u["affiliate_id"], tenant_id)).fetchone()
        if not aff:
            return None

        commission = round(amount * float(aff["percent"]) / 100)
        if commission <= 0:
            return None

        try:
            con.execute(
                """INSERT INTO affiliate_commissions
                   (tenant_id, affiliate_id, order_id, user_id,
                    order_amount, percent, commission)
                   VALUES (?,?,?,?,?,?,?)""",
                (tenant_id, aff["id"], order_id, user_id,
                 amount, aff["percent"], commission))
            con.commit()
        except sqlite3.IntegrityError:
            # این سفارش قبلاً ثبت شده
            return None

        return {"affiliate": dict(aff), "commission": commission}
    finally:
        con.close()


def affiliate_stats(tenant_id, affiliate_id):
    """آمار یک همکار — فروش، پورسانت، پرداختی و مانده."""
    con = _connect()
    try:
        row = con.execute(
            """SELECT COUNT(*) AS orders,
                      COALESCE(SUM(order_amount),0) AS sales,
                      COALESCE(SUM(commission),0) AS earned,
                      COALESCE(SUM(CASE WHEN status='paid' THEN commission ELSE 0 END),0) AS paid
               FROM affiliate_commissions
               WHERE tenant_id=? AND affiliate_id=? AND status != 'cancelled'""",
            (tenant_id, affiliate_id)).fetchone()

        users = con.execute(
            "SELECT COUNT(*) AS c FROM users WHERE tenant_id=? AND affiliate_id=?",
            (tenant_id, affiliate_id)).fetchone()["c"]

        payouts = con.execute(
            """SELECT COALESCE(SUM(amount),0) AS s FROM affiliate_payouts
               WHERE tenant_id=? AND affiliate_id=?""",
            (tenant_id, affiliate_id)).fetchone()["s"]

        d = dict(row)
        d["users"] = users
        d["payouts"] = payouts
        d["balance"] = d["earned"] - payouts
        return d
    finally:
        con.close()


def init_db():
    """ساخت جداول. اجرای مکرر بی‌خطر است."""
    con = _connect()
    try:
        con.executescript(SCHEMA)
        _migrate(con)
        con.commit()
    finally:
        con.close()


@contextmanager
def conn():
    con = _connect()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def gen_ref_code(length=6):
    """کد معرف کوتاه و خوانا (بدون کاراکترهای گیج‌کننده مثل O و 0)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ═══════════════════════════════════════════════════════════
#  TenantDB — همه‌ی دسترسی‌ها از این‌جا می‌گذرند
#  هر متد خودکار tenant_id را اعمال می‌کند تا نشت داده ممکن نباشد
# ═══════════════════════════════════════════════════════════

class TenantDB:
    # جداولی که باید حتماً با tenant_id فیلتر شوند
    SCOPED = {"users", "plans", "orders", "subscriptions",
              "coin_tx", "wallet_tx", "discounts", "tickets", "events"}

    def __init__(self, tenant_id: int):
        if not isinstance(tenant_id, int) or tenant_id <= 0:
            raise ValueError("tenant_id نامعتبر است")
        self.tid = tenant_id

    # ---------- کمکی‌های عمومی ----------
    def q(self, sql: str, params=(), one=False):
        """
        اجرای کوئری. اگر جدولی از SCOPED در FROM باشد ولی tenant_id
        در WHERE نباشد، خطا می‌دهد — محافظ در برابر اشتباه انسانی.
        """
        low = sql.lower()
        if any(f" {t}" in low for t in self.SCOPED) and "tenant_id" not in low:
            raise RuntimeError(
                f"کوئری بدون فیلتر tenant_id روی جدول محافظت‌شده: {sql[:80]}"
            )
        with conn() as c:
            cur = c.execute(sql, params)
            rows = cur.fetchall()
        if one:
            return dict(rows[0]) if rows else None
        return [dict(r) for r in rows]

    def exec(self, sql: str, params=()):
        with conn() as c:
            cur = c.execute(sql, params)
            return cur.lastrowid

    # ---------- کاربران ----------
    def get_user(self, tg_id: int):
        return self.q(
            "SELECT * FROM users WHERE tenant_id=? AND tg_id=?",
            (self.tid, tg_id), one=True
        )

    def get_user_by_id(self, uid: int):
        return self.q(
            "SELECT * FROM users WHERE tenant_id=? AND id=?",
            (self.tid, uid), one=True
        )

    def get_user_by_ref(self, code: str):
        return self.q(
            "SELECT * FROM users WHERE tenant_id=? AND ref_code=?",
            (self.tid, code.upper()), one=True
        )

    def create_user(self, tg_id, username=None, first_name=None, referred_by=None):
        # کد معرف یکتا در کل سیستم (نه فقط مستاجر) تا لینک‌ها قابل تشخیص باشند
        for _ in range(12):
            code = gen_ref_code()
            try:
                uid = self.exec(
                    """INSERT INTO users (tenant_id, tg_id, username, first_name,
                                          ref_code, referred_by)
                       VALUES (?,?,?,?,?,?)""",
                    (self.tid, tg_id, username, first_name, code, referred_by)
                )
                return self.get_user_by_id(uid)
            except sqlite3.IntegrityError as e:
                if "ref_code" in str(e):
                    continue          # برخورد کد، دوباره تلاش
                if "tg_id" in str(e) or "UNIQUE" in str(e):
                    return self.get_user(tg_id)   # کاربر از قبل هست
                raise
        raise RuntimeError("ساخت کد معرف یکتا ناموفق بود")

    def touch_user(self, tg_id):
        self.exec(
            "UPDATE users SET last_seen=CURRENT_TIMESTAMP WHERE tenant_id=? AND tg_id=?",
            (self.tid, tg_id)
        )

    def set_state(self, tg_id, state, data=None):
        self.exec(
            "UPDATE users SET state=?, state_data=? WHERE tenant_id=? AND tg_id=?",
            (state, json.dumps(data or {}, ensure_ascii=False), self.tid, tg_id)
        )

    def clear_state(self, tg_id):
        self.set_state(tg_id, None, {})

    # ---------- سکه ----------
    def spend_coins(self, user_id, amount, kind, note=None, order_id=None):
        """
        خرج‌کردن سکه — اتمی. برمی‌گرداند: (موفق, موجودی تازه)

        چرا لازم است:
            سکه هنگام *تایید* سفارش کم می‌شد، نه هنگام ثبتش. بین آن
            دو، مشتری می‌توانست سفارش دومی با همان سکه‌ها بسازد —
            چون هنوز کم نشده بودند — و بعد هر دو تایید شوند و دو بار
            از یک موجودی برداشته شود.

            و از آن بدتر: مسیر «رد کردن سفارش» سکه را *برمی‌گرداند*،
            در حالی که اصلاً کم نشده بود. یعنی هر سفارشی که رد می‌شد
            به مشتری سکه‌ی رایگان می‌داد.

            حالا سکه همان لحظه‌ی ثبت سفارش رزرو می‌شود و فقط در رد،
            انقضا یا لغو برمی‌گردد — پس هر دو مشکل از ریشه می‌رود.
        """
        amount = abs(int(amount))
        with conn() as c:
            cur = c.execute(
                "UPDATE users SET coins = coins - ? "
                "WHERE tenant_id=? AND id=? AND coins >= ?",
                (amount, self.tid, user_id, amount)
            )
            if not cur.rowcount:
                row = c.execute(
                    "SELECT coins FROM users WHERE tenant_id=? AND id=?",
                    (self.tid, user_id)).fetchone()
                return False, (row["coins"] if row else 0)

            c.execute(
                """INSERT INTO coin_tx (tenant_id, user_id, amount, kind, note,
                                        ref_user_id, order_id)
                   VALUES (?,?,?,?,?,?,?)""",
                (self.tid, user_id, -amount, kind, note, None, order_id)
            )
            row = c.execute(
                "SELECT coins FROM users WHERE tenant_id=? AND id=?",
                (self.tid, user_id)).fetchone()
            return True, (row["coins"] if row else 0)

    def claim_trial(self, user_id):
        """
        گرفتن حقِ اشتراک تست، اتمی. برمی‌گرداند: گرفته شد یا نه.

        قبلاً پرچم trial_used *بعد از* ساخت کانفیگ نوشته می‌شد، و
        بینشان یک رفت‌وبرگشت کامل با x-ui فاصله بود. دو بار زدنِ
        دکمه‌ی «تست رایگان» یعنی هر دو نخ پرچم را صفر می‌دیدند و هر
        دو کانفیگ می‌ساختند — یعنی محصول رایگان، به تعداد دفعاتی که
        کسی دکمه را می‌زد.

        این شرط از ریشه می‌بندَدش: فقط اولین نفر می‌تواند پرچم را
        از صفر به یک ببرد.
        """
        with conn() as c:
            cur = c.execute(
                "UPDATE users SET trial_used=1 "
                "WHERE tenant_id=? AND id=? AND trial_used=0",
                (self.tid, user_id))
            return bool(cur.rowcount)

    def release_trial(self, user_id):
        """
        پس‌دادن حقِ تست، وقتی ساخت کانفیگ شکست خورد.

        پیام خطا به مشتری می‌گوید «تست رایگانتان هنوز محفوظ است» —
        و این تابع همان را راست نگه می‌دارد.
        """
        with conn() as c:
            c.execute("UPDATE users SET trial_used=0 WHERE tenant_id=? AND id=?",
                      (self.tid, user_id))

    def claim_order(self, order_id, admin_tg_id, stale_minutes=5):
        """
        ادعای انحصاری یک سفارش، پیش از ساخت کانفیگ. اتمی.

        چرا لازم است: تایید سفارش اول وضعیت را می‌خواند و *بعد از*
        ساخت موفق کانفیگ آن را approved می‌کرد. فاصله‌ی بین این دو یک
        رفت‌وبرگشت کامل با x-ui است — چند ثانیه.

        ربات هشت نخ دارد و دکمه‌ی تایید در گروه مدیریت است. دو بار
        زدن، دو ادمین، یا تایید از پنل هم‌زمان با دکمه‌ی تلگرام: هر
        دو نخ نگهبان را رد می‌کنند، هر دو کانفیگ می‌سازند، و مشتری با
        یک پرداخت دو کانفیگ می‌گیرد و معرفش دو بار سکه.

        شرط اتمی این را از ریشه می‌بندد: فقط یکی می‌تواند برنده شود.

        ادعای مانده هم دوباره قابل‌گرفتن است — اگر نخی وسط ساخت مرد،
        سفارش برای همیشه گیر نمی‌کند.
        """
        with conn() as c:
            cur = c.execute(
                """UPDATE orders
                      SET status='approved', reviewed_by=?,
                          reviewed_at=CURRENT_TIMESTAMP
                    WHERE tenant_id=? AND id=?
                      AND (status <> 'approved'
                           OR (sub_id IS NULL
                               AND (reviewed_at IS NULL
                                    OR reviewed_at <
                                       datetime('now', ?))))""",
                (admin_tg_id, self.tid, order_id,
                 f"-{int(stale_minutes)} minutes"))
            return bool(cur.rowcount)

    def release_coins(self, order_id):
        """
        سکه‌های رزروشده‌ی یک سفارش را برمی‌گرداند. تعدادِ رزروهای
        آزادشده را می‌دهد.

        این‌جا زندگی می‌کند، نه در handlers، چون جاروکشِ خودکارِ
        سفارش‌های منقضی هیچ رباتی در دست ندارد و نمی‌تواند Ctx بسازد.
        وقتی این منطق فقط در handlers بود، آن جاروکش یک UPDATE خام
        می‌زد و رزرو را باز می‌گذاشت — و چون جاروکش همیشه زودتر از
        مشتری به سفارش می‌رسد، عملاً *مسیر اصلیِ* انقضا همان بود.

        دو بار برگرداندن ممکن نیست: رزرو بعد از بازگشت به «released»
        تغییر نام می‌دهد، پس دفعه‌ی بعد پیدا نمی‌شود.
        """
        held = self.q(
            "SELECT * FROM coin_tx WHERE tenant_id=? AND order_id=? "
            "AND kind='hold'", (self.tid, order_id))
        for tx in held:
            self.add_coins(tx["user_id"], abs(int(tx["amount"])), "refund",
                           f"بازگشت سکه — سفارش #{order_id}",
                           order_id=order_id)
            self.exec("UPDATE coin_tx SET kind='released' "
                      "WHERE tenant_id=? AND id=?", (self.tid, tx["id"]))
        return len(held)

    def add_coins(self, user_id, amount, kind, note=None, ref_user_id=None, order_id=None):
        """
        تغییر موجودی سکه — برای پاداش، بازگشت و تنظیم دستی ادمین.

        برای *خرج‌کردن* از spend_coins استفاده کنید؛ این تابع شرطی
        ندارد و موجودی را منفی هم می‌کند.
        """
        with conn() as c:
            c.execute(
                "UPDATE users SET coins = coins + ? WHERE tenant_id=? AND id=?",
                (amount, self.tid, user_id)
            )
            c.execute(
                """INSERT INTO coin_tx (tenant_id, user_id, amount, kind, note,
                                        ref_user_id, order_id)
                   VALUES (?,?,?,?,?,?,?)""",
                (self.tid, user_id, amount, kind, note, ref_user_id, order_id)
            )

    # ---------- کیف پول ----------
    def add_balance(self, user_id, amount, kind, note=None, order_id=None):
        """
        تغییر موجودی — برای واریز، برگشت پول و تنظیم دستی ادمین.

        برای *خرج‌کردن* از spend_balance استفاده کنید، نه این. این
        تابع شرطی ندارد و موجودی را منفی هم می‌کند.
        """
        with conn() as c:
            c.execute(
                "UPDATE users SET balance = balance + ? WHERE tenant_id=? AND id=?",
                (amount, self.tid, user_id)
            )
            c.execute(
                """INSERT INTO wallet_tx (tenant_id, user_id, amount, kind, note, order_id)
                   VALUES (?,?,?,?,?,?)""",
                (self.tid, user_id, amount, kind, note, order_id)
            )

    def spend_balance(self, user_id, amount, kind, note=None, order_id=None):
        """
        خرج‌کردن از کیف پول — اتمی. برمی‌گرداند: (موفق, موجودی تازه)

        چرا جدا از add_balance:
            الگوی قبلی «اول موجودی را بخوان، اگر کافی بود کم کن» بود.
            بین این دو، هر چیز دیگری می‌تواند همان پول را خرج کند —
            و از وقتی ربات با هشت نخ کار می‌کند و زمان‌بند تمدید
            خودکار در نخ جداگانه‌ای می‌دود، این دیگر فرضی نیست:
            مشتری در حال خرید است و هم‌زمان تمدید خودکارش اجرا می‌شود.

            بدتر اینکه UPDATE هیچ شرطی نداشت، پس نتیجه‌ی هر لغزشی
            یک موجودی منفی بود که هیچ‌جا دیده نمی‌شد.

            این‌جا خود دیتابیس شرط را نگه می‌دارد: اگر موجودی کافی
            نباشد هیچ سطری به‌روز نمی‌شود و تراکنشی هم ثبت نمی‌شود.
        """
        amount = abs(int(amount))
        with conn() as c:
            cur = c.execute(
                "UPDATE users SET balance = balance - ? "
                "WHERE tenant_id=? AND id=? AND balance >= ?",
                (amount, self.tid, user_id, amount)
            )
            if not cur.rowcount:
                row = c.execute(
                    "SELECT balance FROM users WHERE tenant_id=? AND id=?",
                    (self.tid, user_id)).fetchone()
                return False, (row["balance"] if row else 0)

            c.execute(
                """INSERT INTO wallet_tx (tenant_id, user_id, amount, kind, note, order_id)
                   VALUES (?,?,?,?,?,?)""",
                (self.tid, user_id, -amount, kind, note, order_id)
            )
            row = c.execute(
                "SELECT balance FROM users WHERE tenant_id=? AND id=?",
                (self.tid, user_id)).fetchone()
            return True, (row["balance"] if row else 0)

    # ---------- پلن‌ها ----------
    def plans(self, active_only=True, include_trial=False):
        sql = "SELECT * FROM plans WHERE tenant_id=?"
        if active_only:
            sql += " AND is_active=1"
        if not include_trial:
            sql += " AND is_trial=0"
        sql += " ORDER BY sort_order, price"
        return self.q(sql, (self.tid,))

    def get_plan(self, pid):
        return self.q("SELECT * FROM plans WHERE tenant_id=? AND id=?",
                      (self.tid, pid), one=True)

    def trial_plan(self):
        return self.q(
            "SELECT * FROM plans WHERE tenant_id=? AND is_trial=1 AND is_active=1 LIMIT 1",
            (self.tid,), one=True
        )

    # ---------- سفارش ----------
    def create_order(self, user_id, plan_id, base_amount, amount,
                     coins_used=0, discount_pct=0, discount_code=None,
                     kind="new", paid_from="card", ttl_minutes=30,
                     renew_sub_id=None):
        exp = (datetime.now() + timedelta(minutes=ttl_minutes)).isoformat(timespec="seconds")
        oid = self.exec(
            """INSERT INTO orders (tenant_id, user_id, plan_id, kind, amount,
                                   base_amount, coins_used, discount_pct,
                                   discount_code, paid_from, expires_at,
                                   renew_sub_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (self.tid, user_id, plan_id, kind, amount, base_amount,
             coins_used, discount_pct, discount_code, paid_from, exp,
             renew_sub_id)
        )
        return self.get_order(oid)

    def get_order(self, oid):
        return self.q("SELECT * FROM orders WHERE tenant_id=? AND id=?",
                      (self.tid, oid), one=True)

    def pending_orders(self):
        return self.q(
            """SELECT o.*, u.tg_id, u.first_name, u.username, p.name AS plan_name
               FROM orders o
               JOIN users u ON u.id = o.user_id
               LEFT JOIN plans p ON p.id = o.plan_id
               WHERE o.tenant_id=? AND o.status='awaiting'
               ORDER BY o.created_at DESC""",
            (self.tid,)
        )

    # ---------- اشتراک ----------
    def user_subs(self, user_id, active_only=True):
        sql = """SELECT s.*, p.name AS plan_name FROM subscriptions s
                 LEFT JOIN plans p ON p.id = s.plan_id
                 WHERE s.tenant_id=? AND s.user_id=?"""
        if active_only:
            sql += " AND s.is_active=1"
        sql += " ORDER BY s.created_at DESC"
        return self.q(sql, (self.tid, user_id))

    # ---------- آمار ----------
    def stats(self):
        def one(sql, p=()):
            r = self.q(sql, p, one=True)
            return (list(r.values())[0] if r else 0) or 0

        today = datetime.now().strftime("%Y-%m-%d")
        return {
            "users": one("SELECT COUNT(*) FROM users WHERE tenant_id=?", (self.tid,)),
            "users_today": one(
                "SELECT COUNT(*) FROM users WHERE tenant_id=? AND date(created_at)=?",
                (self.tid, today)),
            "active_subs": one(
                "SELECT COUNT(*) FROM subscriptions WHERE tenant_id=? AND is_active=1",
                (self.tid,)),
            "pending": one(
                "SELECT COUNT(*) FROM orders WHERE tenant_id=? AND status='awaiting'",
                (self.tid,)),
            "revenue_today": one(
                """SELECT COALESCE(SUM(amount),0) FROM orders
                   WHERE tenant_id=? AND status='approved' AND date(reviewed_at)=?""",
                (self.tid, today)),
            "revenue_total": one(
                """SELECT COALESCE(SUM(amount),0) FROM orders
                   WHERE tenant_id=? AND status='approved'""",
                (self.tid,)),
            # پنل مدیریت ربات این را می‌خواند؛ نبودنش باعث می‌شد
            # «تیکت باز» همیشه صفر نشان داده شود
            "open_tickets": one(
                "SELECT COUNT(*) FROM tickets WHERE tenant_id=? AND status='open'",
                (self.tid,)),
        }

    def log(self, kind, user_id=None, data=None):
        self.exec(
            "INSERT INTO events (tenant_id, user_id, kind, data) VALUES (?,?,?,?)",
            (self.tid, user_id, kind, json.dumps(data or {}, ensure_ascii=False))
        )


# ═══════════════════════════════════════════════════════════
#  عملیات سطح سیستم (فراتر از یک مستاجر) — فقط برای مالک اصلی
# ═══════════════════════════════════════════════════════════

def all_tenants(active_only=True):
    sql = "SELECT * FROM tenants"
    if active_only:
        sql += " WHERE is_active=1"
    with conn() as c:
        return [dict(r) for r in c.execute(sql).fetchall()]


def get_tenant(tid):
    with conn() as c:
        r = c.execute("SELECT * FROM tenants WHERE id=?", (tid,)).fetchone()
    return dict(r) if r else None


def get_tenant_by_token(token):
    with conn() as c:
        r = c.execute("SELECT * FROM tenants WHERE bot_token=?", (token,)).fetchone()
    return dict(r) if r else None


def create_tenant(name, bot_token=None, owner_tg_id=None, parent_id=None, **kw):
    with conn() as c:
        cur = c.execute(
            """INSERT INTO tenants (name, bot_token, owner_tg_id, parent_id,
                                    panel_url, panel_user, panel_pass,
                                    default_inbound, credit, credit_discount, settings)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (name, bot_token, owner_tg_id, parent_id,
             kw.get("panel_url"), kw.get("panel_user"), kw.get("panel_pass"),
             kw.get("default_inbound"), kw.get("credit", 0),
             kw.get("credit_discount", 0),
             json.dumps(kw.get("settings", {}), ensure_ascii=False))
        )
        return cur.lastrowid


def update_tenant(tid, **fields):
    if not fields:
        return
    allowed = {"name", "bot_token", "bot_username", "owner_tg_id", "is_active",
               "credit", "credit_discount", "panel_url", "panel_user",
               "panel_pass", "panel_token", "default_inbound",
               "admin_group_id", "topics", "settings"}
    sets, vals = [], []
    for k, v in fields.items():
        if k in allowed:
            if k in ("topics", "settings") and isinstance(v, (dict, list)):
                v = json.dumps(v, ensure_ascii=False)
            sets.append(f"{k}=?")
            vals.append(v)
    if not sets:
        return
    vals.append(tid)
    with conn() as c:
        c.execute(f"UPDATE tenants SET {', '.join(sets)} WHERE id=?", vals)


def tenant_settings(tid):
    t = get_tenant(tid)
    if not t:
        return {}
    try:
        return json.loads(t.get("settings") or "{}")
    except json.JSONDecodeError:
        return {}


def save_tenant_settings(tid, settings: dict):
    update_tenant(tid, settings=settings)
