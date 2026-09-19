"""بک‌اند پنل مدیریت صفحه‌ی اشتراک Nexora"""

import os
import json
import re as _re
import secrets
import threading as _threading
import time
import logging
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import (FastAPI, HTTPException, Header, Request, Response,
                     Depends)
from fastapi.middleware.cors import CORSMiddleware
import contextvars as _contextvars
import hmac as _hmac
import secrets as _secrets
import ipaddress as _ipaddress
import time as _time
from fastapi.responses import HTMLResponse

log = logging.getLogger("nexora.panel")

CONFIG_PATH = Path(os.getenv("CONFIG_PATH", "../data/config.json"))
AUTH_PATH = Path(os.getenv("AUTH_PATH", str(CONFIG_PATH.parent / "auth.json")))
ADMIN_PASSWORD = os.getenv("NEXORA_SUBPAGE_ADMIN_PASSWORD", "change-me")
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")


#: رمز به‌شکل هَش ذخیره می‌شود، نه متنِ ساده.
#
#  چرا: تا امروز `auth.json` خودِ رمز را داشت. هر کسی که آن فایل را
#  می‌خواند — پشتیبانِ لو رفته، اسنپ‌شاتِ جابه‌جاشده، یک خطای مسیر —
#  مستقیم به پنل، رمز x-ui، توکن ربات و داده‌ی همه‌ی مشتری‌ها
#  می‌رسید. هَش این را به یک حدس‌زدنِ گران تبدیل می‌کند.
#
#  چرا PBKDF2 و نه یک هَشِ ساده: SHA سریع است و سرعت دقیقاً همان
#  چیزی است که حدس‌زننده می‌خواهد.
PW_SCHEME = "pbkdf2_sha256"
PW_ITERS = 200_000


def _pw_hash(pw: str, salt: bytes = None, iters: int = PW_ITERS) -> str:
    import hashlib
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", str(pw).encode("utf-8"), salt, iters)
    return f"{PW_SCHEME}${iters}${salt.hex()}${dk.hex()}"


def _pw_is_hash(v: str) -> bool:
    return isinstance(v, str) and v.startswith(PW_SCHEME + "$")


def _pw_check(given: str, stored: str) -> bool:
    """
    مقایسه‌ی زمان‌ثابت — چه ذخیره‌شده هَش باشد چه متنِ ساده.

    متنِ ساده هنوز پذیرفته می‌شود چون نصب‌های قبلی همان را دارند و
    ردکردنش یعنی قفل‌شدنِ مالک پشتِ پنلِ خودش. اولین ورودِ موفق
    خودش ارتقا می‌دهد.
    """
    import hashlib
    g = str(given or "")
    st = str(stored or "")
    if not st:
        return False
    if _pw_is_hash(st):
        try:
            _, it, salt_hex, want = st.split("$", 3)
            dk = hashlib.pbkdf2_hmac("sha256", g.encode("utf-8"),
                                     bytes.fromhex(salt_hex), int(it))
        except (ValueError, TypeError):
            log.error("قالبِ رمزِ ذخیره‌شده خوانده نشد")
            return False
        return _hmac.compare_digest(dk.hex(), want)
    # بایت مقایسه می‌شود، نه رشته: compare_digest روی رشته‌ی غیراسکی
    # TypeError می‌دهد — یک رمز فارسی کل پنل را با ۵۰۰ می‌بست.
    return _hmac.compare_digest(g.encode("utf-8"), st.encode("utf-8"))


def _stored_password():
    """مقدارِ خام (هَش یا متن) — فقط برای سنجیدن، نه برای پاس‌دادن."""
    if AUTH_PATH.exists():
        try:
            with open(AUTH_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                pw = data.get("password")
                if pw:
                    return pw
        except (json.JSONDecodeError, OSError):
            log.warning("auth.json خوانده نشد؛ از متغیر محیطی", exc_info=True)
    return ADMIN_PASSWORD


def verify_password(given: str) -> bool:
    """
    آیا این رمز درست است؟

    و اگر ذخیره‌شده هنوز متنِ ساده بود، همین‌جا ارتقا می‌دهد — تا
    مهاجرت بدون اینکه کسی کاری کند انجام شود.
    """
    stored = _stored_password()
    if not _pw_check(given, stored):
        return False
    if not _pw_is_hash(stored):
        try:
            save_password(given)
            log.info("رمز پنل به شکل هَش ذخیره شد")
        except Exception:
            # ارتقا نشد؛ ولی ورود درست بود و نباید بشکند
            log.warning("ارتقای رمز به هَش ناموفق", exc_info=True)
    return True


#: نشانه‌ی فراخوانِ درونی.
#
#  یک مسیرِ نماینده، تابعِ صورتحسابِ مدیر را مستقیم صدا می‌زند و آن
#  تابع `check_auth` دارد. تا امروز رمزِ ذخیره‌شده را پاس می‌داد —
#  که با هَش‌شدن دیگر جواب نمی‌دهد. مقدارِ تصادفیِ هر اجرا یعنی
#  حدس‌زدنی هم نیست، و چون از بیرون هیچ‌وقت برابرش نمی‌شود، راهِ
#  دور زدن باز نمی‌کند.
_INTERNAL_PW = "internal:" + secrets.token_urlsafe(32)


def load_password():
    """
    مقدارِ ذخیره‌شده.

    **برای مقایسه از `verify_password` استفاده کن، نه از این.** این
    ممکن است هَش برگرداند و مقایسه‌ی مستقیم با آن همیشه غلط است.
    """
    return _stored_password()


def save_password(new_password: str):
    AUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUTH_PATH, "w", encoding="utf-8") as f:
        json.dump({"password": _pw_hash(new_password)}, f,
                  ensure_ascii=False, indent=2)
    # محدود کردن دسترسی فایل به مالک (فقط روی سیستم‌های یونیکسی)
    try:
        os.chmod(AUTH_PATH, 0o600)
    except OSError:
        pass

DEFAULT_CONFIG = {
    "downloadApps": {
        "android": [
            {"id": "happ", "name": "Happ", "url": "https://github.com/Happ-proxy/happ-android/releases/download/3.26.3/Happ.apk", "recommended": True, "icon": "bolt", "scheme": "happ"},
            {"id": "v2rayng", "name": "v2rayNG", "url": "https://github.com/2dust/v2rayNG/releases/download/2.2.6/v2rayNG_2.2.6_arm64-v8a.apk", "recommended": False, "icon": "paper-plane", "scheme": "v2rayng"}
        ],
        "ios": [
            {"id": "happ", "name": "Happ", "url": "https://apps.apple.com/us/app/happ-proxy-utility/id6504287215", "recommended": True, "icon": "bolt", "scheme": "happ"},
            {"id": "v2box", "name": "V2Box", "url": "https://apps.apple.com/us/app/v2box-v2ray-client/id6446814690", "recommended": False, "icon": "shield-halved", "scheme": "v2box"}
        ],
        "desktop": [
            {"id": "happ", "name": "Happ (Windows)", "url": "https://github.com/Happ-proxy/happ-desktop/releases/download/3.3.6/setup-Happ.x64.exe", "recommended": True, "icon": "bolt", "scheme": "happ"},
            {"id": "v2rayn", "name": "v2rayN (Windows)", "url": "https://github.com/2dust/v2rayN/releases/download/7.24.1/v2rayN-windows-arm64.zip", "recommended": False, "icon": "box-open", "scheme": "none"}
        ]
    },
    "faq": {
        "fa": [
            {"q": "چرا نمی‌توانم وصل شوم؟", "a": "اول مطمئن شوید آخرین نسخه‌ی اپ پیشنهادی (Happ) را نصب کرده‌اید و کانفیگ را درست وارد کرده‌اید."},
            {"q": "چطور اشتراکم را تمدید کنم؟", "a": "روی دکمه‌ی «تمدید ساب» در داشبورد بزنید یا مستقیم به پشتیبانی پیام دهید."}
        ],
        "en": [{"q": "Why can't I connect?", "a": "Make sure you've installed the latest version of our recommended app (Happ)."}],
        "tr": [], "ar": []
    },
    "banners": {
        "enabled": True,
        "lowQuotaDaysThreshold": 3,
        "lowQuotaPercentThreshold": 15,
        "disabledTitle": "",
        "disabledDesc": "",
        "disabledButtonText": "",
        "lowQuotaTitle": "",
        "lowQuotaDescDays": "",
        "lowQuotaDescVolume": "",
        "lowQuotaButtonText": "",
        "lowQuotaButtonUrl": ""
    },
    "referral": {"enabled": True},
    "links": {"supportUsername": "crm_nexoravpn", "channelUsername": "yanexoravpn"},
    "videoTutorialUrl": None,
    "videos": [],
    "advanced": {
        "brandName": "NEXORA",
        "pageTitle": "Nexora | مدیریت اشتراک",
        "accentColor": "#2B7FD6",
        "accentColor2": "#5AA9E6",
        "defaultLanguage": "fa",
        "defaultTheme": "dark",
        "showNotificationPopup": True,
        "notificationDelaySeconds": 10,
        "showBrandStrip": True,
        "showReferralCard": True,
        "showFaqSection": True,
        "customCss": "",
        "customFooterText": "",
        "allowThemeToggle": True,
        "allowLanguageToggle": True,
        "hideConfigsList": False
    },
    "popup": {
        "enabled": True,
        "delaySeconds": 10,
        "icon": "🔔",
        "title": "آیا مشکلی در اتصال کانفیگ دارید؟",
        "description": "پیشنهاد می‌کنیم از برنامه‌ی Happ استفاده کنید؛ در غیر این صورت به پشتیبانی پیام بدهید",
        "primaryButtonText": "پشتیبانی",
        "primaryButtonUrl": "",
        "dismissButtonText": "خیر",
        "autoCloseSeconds": 15
    },
    "bot": {
        "enabled": False,
        "token": "",
        "adminChatId": "",
        "welcomeMessage": "سلام! به ربات Nexora خوش آمدید 👋",
        "notifyOnPurchase": True,
        "notifyOnExpiry": True,
        "expiryReminderDays": 3
    },
    "resellers": [],
    "template": "classic",
    "palette": "ocean",
    "customPalettes": []
}


# ---------------------------------------------------------------
# قالب‌های داخلی صفحه‌ی اشتراک
# ---------------------------------------------------------------
# هر قالب فقط ظاهر را عوض می‌کند؛ داده و منطق یکسان می‌ماند.
# layout مشخص می‌کند کدام چیدمان استفاده شود:
#   standard = حلقه پیشرفت + کارت‌ها
#   compact  = نوار افقی فشرده
#   glass    = کارت‌های شیشه‌ای با عدد درشت
# ═══════════════════════════════════════════════════════════
#  سیستم قالب: ساختار (template) × طیف رنگی (palette)
#  جدا نگه داشتن این دو یعنی با ۴ ساختار و ۸ پالت،
#  ۳۲ ترکیب در اختیار کاربر است — و افزودن یک پالت جدید
#  خودکار ۴ ترکیب تازه می‌سازد.
# ═══════════════════════════════════════════════════════════

TEMPLATES = [
    {"id": "classic", "name": "Classic", "fa": "کلاسیک",
     "desc": "ظاهر پیش‌فرض — ساده و آشنا"},
    {"id": "analytics", "name": "Analytics", "fa": "تحلیلی",
     "desc": "کارت‌های آماری برجسته با حاشیه‌های رنگی"},
    {"id": "wallet", "name": "Wallet", "fa": "کیف پول",
     "desc": "کارت اصلی گرادینتی + دکمه‌های گرد"},
    {"id": "console", "name": "Console", "fa": "کنسول",
     "desc": "حس ترمینال — مونواسپیس و گوشه‌های تیز"},
]

PALETTES = [
    {"id": "ocean", "name": "Ocean", "fa": "اقیانوس", "builtin": True, "vars": {
        "accent": "#2B7FD6", "accent2": "#5AA9E6", "bg": "#06090F",
        "surface": "#0D1420", "surfaceAlt": "#0A0E17",
        "border": "rgba(255,255,255,0.06)", "text": "#E8EEF7", "textMuted": "#5A6880"}},
    {"id": "violet", "name": "Violet", "fa": "بنفش", "builtin": True, "vars": {
        "accent": "#8B5CF6", "accent2": "#C084FC", "bg": "#0A0713",
        "surface": "#150F26", "surfaceAlt": "#0F0A1C",
        "border": "rgba(255,255,255,0.07)", "text": "#EDE9F7", "textMuted": "#6B6188"}},
    {"id": "ember", "name": "Ember", "fa": "آتشین", "builtin": True, "vars": {
        "accent": "#F97316", "accent2": "#FB923C", "bg": "#0C0906",
        "surface": "#181109", "surfaceAlt": "#120C07",
        "border": "rgba(255,255,255,0.07)", "text": "#FBEDE6", "textMuted": "#8F7365"}},
    {"id": "forest", "name": "Forest", "fa": "جنگل", "builtin": True, "vars": {
        "accent": "#10B981", "accent2": "#34D399", "bg": "#04100C",
        "surface": "#0A1D16", "surfaceAlt": "#071711",
        "border": "rgba(255,255,255,0.06)", "text": "#E4F7EF", "textMuted": "#5A806F"}},
    {"id": "rose", "name": "Rose", "fa": "رز", "builtin": True, "vars": {
        "accent": "#EC4899", "accent2": "#F472B6", "bg": "#0E060B",
        "surface": "#1B0D16", "surfaceAlt": "#150A11",
        "border": "rgba(255,255,255,0.07)", "text": "#FDF2FA", "textMuted": "#8B6F80"}},
    {"id": "gold", "name": "Gold", "fa": "طلایی", "builtin": True, "vars": {
        "accent": "#D4AF37", "accent2": "#E8C766", "bg": "#0C0A07",
        "surface": "#171310", "surfaceAlt": "#110E0B",
        "border": "rgba(212,175,55,0.16)", "text": "#F5EFE2", "textMuted": "#8F8371"}},
    {"id": "cyan", "name": "Cyan", "fa": "فیروزه‌ای", "builtin": True, "vars": {
        "accent": "#06B6D4", "accent2": "#22D3EE", "bg": "#04121A",
        "surface": "#0A2029", "surfaceAlt": "#071821",
        "border": "rgba(255,255,255,0.07)", "text": "#E0F5FA", "textMuted": "#6E96A3"}},
    {"id": "slate", "name": "Slate", "fa": "خاکستری", "builtin": True, "vars": {
        "accent": "#94A3B8", "accent2": "#CBD5E1", "bg": "#0B0C0F",
        "surface": "#14161B", "surfaceAlt": "#101216",
        "border": "rgba(255,255,255,0.09)", "text": "#F1F5F9", "textMuted": "#6B7480"}},
]


def get_template(tpl_id=None):
    for t in TEMPLATES:
        if t["id"] == tpl_id:
            return t
    return TEMPLATES[0]


def get_palette(cfg, pal_id=None):
    for p in PALETTES:
        if p["id"] == pal_id:
            return p
    for p in cfg.get("customPalettes", []):
        if p.get("id") == pal_id:
            return p
    return PALETTES[0]


def resolve_theme(cfg, template_id=None, palette_id=None):
    """ترکیب ساختار و رنگ — چیزی که صفحه‌ی اشتراک برای رندر لازم دارد."""
    tpl = get_template(template_id or cfg.get("template"))
    pal = get_palette(cfg, palette_id or cfg.get("palette"))
    return {
        "template": tpl["id"], "templateName": tpl["name"],
        "palette": pal["id"], "paletteName": pal["name"],
        "vars": pal.get("vars", {}),
    }


def deep_merge(base: dict, override: dict) -> dict:
    """ادغام عمیق: مقادیر override روی base می‌نشینند، بقیه دست‌نخورده می‌مانند."""
    result = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def find_reseller(cfg: dict, email: str = None, host: str = None):
    """
    واسطه‌ی مربوطه را پیدا می‌کند. اولویت با دامنه است (دقیق‌تر)،
    بعد پیشوند ایمیل. اگر هیچ‌کدام نخورد، None برمی‌گرداند
    (یعنی برند اصلی خودتان نمایش داده می‌شود).
    """
    resellers = [r for r in cfg.get("resellers", []) if r.get("enabled", True)]

    # ۱. تطبیق دامنه (دقیق‌تر، اولویت بالاتر)
    if host:
        clean_host = host.split(":")[0].lower().strip()
        # حذف www. برای تطبیق راحت‌تر
        if clean_host.startswith("www."):
            clean_host = clean_host[4:]
        for r in resellers:
            for d in (r.get("domains") or []):
                d_clean = d.lower().strip().replace("https://", "").replace("http://", "").split("/")[0]
                if d_clean.startswith("www."):
                    d_clean = d_clean[4:]
                if d_clean and (clean_host == d_clean or clean_host.endswith("." + d_clean)):
                    return r

    # ۲. تطبیق پیشوند ایمیل
    if email:
        e = email.lower().strip()
        for r in resellers:
            prefix = (r.get("emailPrefix") or "").lower().strip()
            if prefix and (e.startswith(prefix + "_") or e.startswith(prefix + "-") or e.startswith(prefix + ".")):
                return r

    return None

app = FastAPI(title="Nexora Sub Page Config API")
# `expose_headers` لازم است: هدرِ سفارشی در حالت cross-origin
# برای جاوااسکریپت نامرئی است مگر این‌جا نامش بیاید — و پنل
# روی همان مبدأ صفحه‌ی اشتراک نیست. بدون این، نسخه‌ی تنظیمات
# همیشه null می‌شد و محافظِ «دو تبِ باز» بی‌صدا از کار می‌افتاد.
app.add_middleware(CORSMiddleware, allow_origins=[ALLOWED_ORIGIN],
                   allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"], expose_headers=["X-Config-Version"])


#: تنظیماتِ پنل روی دیتابیس می‌نشیند، نه فایل JSON.
#
#  چرا عوض شد — سه چیز، هر سه واقعی:
#
#  ۱. نوشتن اتمی نبود. `open(w)` اول فایل را خالی می‌کرد بعد
#     می‌نوشت؛ برق برود یا دیسک پر شود، فایل نصفه می‌ماند.
#  ۲. و خرابی بی‌صدا بود: JSONِ خراب یعنی برگشت به `DEFAULT_CONFIG`،
#     یعنی برند و پالت و لینک‌ها و فهرست نماینده‌ها پاک می‌شدند و
#     هیچ‌جا نمی‌گفت چرا. مالک فکر می‌کرد خودش خرابش کرده.
#  ۳. آخرین ذخیره همه‌چیز را می‌برد. دو تبِ باز یعنی یکی بی‌صدا
#     کارِ دیگری را پاک می‌کند.
#
#  چرا داخل `bot.db` و نه فایلِ سوم: یک فایل برای پشتیبان‌گرفتن و
#  برگرداندن، همان چیزی که مالک خواست.
CONFIG_HISTORY_KEEP = 50

#: جدول‌ها یک‌بار ساخته می‌شوند، نه در هر اتصال
_CFG_READY = False
_CFG_LOCAL = _threading.local()


def _cfg_con():
    """
    اتصال به دیتابیسِ تنظیمات، با ساختِ جدول‌ها اگر نبودند.

    `CHECK (id = 1)` عمدی است: یک ردیف، ساختاری تضمین‌شده. این همان
    دامِ «FROM … LIMIT 1 بدون شرط» است که در این مخزن پنج بار پیدا
    شد — این‌جا از اول ممکنش نمی‌کنیم.
    """
    import sqlite3
    # اتصال به‌ازای هر نخ نگه داشته می‌شود و بسته نمی‌شود.
    #
    # اندازه‌گیری: با بازکردنِ اتصالِ تازه در هر خواندن، هر
    # `load_config()` حدود یک میلی‌ثانیه طول می‌کشید — کندتر از
    # خواندنِ همان فایل JSON. هزینه‌اش خودِ باز کردن بود، نه کوئری.
    #
    # اتصالِ SQLite فقط در نخِ خودش امن است، و FastAPI مسیرهای
    # همگام را در یک استخرِ نخ اجرا می‌کند که نخ‌هایش بازاستفاده
    # می‌شوند — پس تعدادِ اتصال‌ها کران‌دار است.
    have = getattr(_CFG_LOCAL, "con", None)
    if have is not None:
        return have
    BOT_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(BOT_DB), timeout=15)
    con.row_factory = sqlite3.Row
    # پیش‌فرضِ پایتون تراکنشِ deferred است؛ برای ادعا کردن پیش از
    # نوشتن، خودمان BEGIN IMMEDIATE می‌زنیم
    con.isolation_level = None
    # ساختِ جدول فقط یک‌بار در عمرِ پردازه.
    #
    # اندازه‌گیری: با اجرای این دو دستور در هر اتصال، خواندنِ
    # تنظیمات ۱٫۱۷ میلی‌ثانیه شد — کندتر از خواندنِ همان فایل JSON،
    # یعنی دقیقاً برعکسِ چیزی که می‌خواستیم.
    if not _CFG_READY:
        con.execute("""CREATE TABLE IF NOT EXISTS panel_config (
            id         INTEGER PRIMARY KEY CHECK (id = 1),
            body       TEXT NOT NULL,
            version    INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        con.execute("""CREATE TABLE IF NOT EXISTS panel_config_history (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL,
            body    TEXT NOT NULL,
            note    TEXT,
            at      TEXT DEFAULT CURRENT_TIMESTAMP)""")
        globals()["_CFG_READY"] = True
    _CFG_LOCAL.con = con
    return con


#: کَشِ درون‌پردازه‌ای. نرمال‌سازی (ادغام با پیش‌فرض و اصلاح نوع‌ها)
#  گران‌ترین بخشِ خواندن است و در هر درخواست تکرار می‌شد.
_CFG_CACHE = {"version": None, "json": None}


def _cfg_migrate(con):
    """
    یک‌بار، از `config.json` به جدول.

    فایل **پاک نمی‌شود** — به‌عنوان پشتیبان می‌ماند. اگر جدول پر
    باشد، فایل اصلاً خوانده نمی‌شود.
    """
    stored = None
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                stored = json.load(f)
        except (json.JSONDecodeError, OSError):
            log.warning("config.json خوانده نشد؛ از پیش‌فرض شروع می‌کنیم",
                        exc_info=True)
    if not isinstance(stored, dict):
        stored = json.loads(json.dumps(DEFAULT_CONFIG))
    con.execute("INSERT OR REPLACE INTO panel_config (id, body, version) "
                "VALUES (1, ?, 1)",
                (json.dumps(stored, ensure_ascii=False),))
    log.info("تنظیمات از config.json به دیتابیس منتقل شد")
    return stored


def _cfg_raw():
    """بدنه‌ی خام و نسخه‌اش — بدون نرمال‌سازی."""
    con = _cfg_con()
    try:
        row = con.execute(
            "SELECT body, version FROM panel_config WHERE id = 1").fetchone()
        if row is None:
            con.execute("BEGIN IMMEDIATE")
            try:
                # ممکن است بین SELECT و این‌جا کسِ دیگری ساخته باشد
                again = con.execute(
                    "SELECT body, version FROM panel_config WHERE id = 1").fetchone()
                if again is not None:
                    con.execute("COMMIT")
                    return again["body"], int(again["version"])
                stored = _cfg_migrate(con)
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise
            return json.dumps(stored, ensure_ascii=False), 1

        body, ver = row["body"], int(row["version"])
        try:
            json.loads(body)
        except json.JSONDecodeError:
            # خرابی — ولی این‌بار بی‌صدا به پیش‌فرض برنمی‌گردیم.
            # تاریخچه دقیقاً برای همین هست: آخرین نسخه‌ی سالم.
            log.error("بدنه‌ی تنظیمات (نسخه %s) خراب است — "
                      "برمی‌گردیم به آخرین نسخه‌ی سالم", ver)
            for h in con.execute(
                    "SELECT body, version FROM panel_config_history "
                    "ORDER BY id DESC LIMIT 20"):
                try:
                    json.loads(h["body"])
                except json.JSONDecodeError:
                    continue
                log.error("نسخه‌ی %s از تاریخچه استفاده شد", h["version"])
                return h["body"], ver
            log.error("هیچ نسخه‌ی سالمی در تاریخچه نبود — پیش‌فرض")
            return json.dumps(DEFAULT_CONFIG, ensure_ascii=False), ver
        return body, ver
    finally:
        pass


def config_version():
    """نسخه‌ی فعلی — پنل همین را موقع ذخیره پس می‌فرستد."""
    con = _cfg_con()
    row = con.execute(
        "SELECT version FROM panel_config WHERE id = 1").fetchone()
    return int(row["version"]) if row else 0


def _normalize_config(stored):
    """
    ساختارِ کامل از روی چیزی که ذخیره شده.

    اگر فایلِ ذخیره‌شده از نسخه‌ی قدیمی‌تر باشد و فیلدهای جدید را
    نداشته باشد، از پیش‌فرض پر می‌شوند — بدون این، پنل هنگام
    دسترسی به فیلدِ ناموجود کرش می‌کند.
    """
    if not isinstance(stored, dict):
        stored = {}
    # ادغام: مقادیر ذخیره‌شده روی پیش‌فرض می‌نشینند،
    # ولی هر فیلدی که در ذخیره‌شده نباشد از پیش‌فرض می‌آید
    merged = deep_merge(json.loads(json.dumps(DEFAULT_CONFIG)), stored)

    # تضمین اینکه کلیدهای زبان FAQ همیشه وجود دارند
    faq = merged.setdefault("faq", {})
    # اگر faq خودش دیکشنری نباشد (فایل دستی خراب شده)، بازش می‌سازیم.
    # setdefault فقط وقتی کلید نباشد کمک می‌کند — نه وقتی مقدارش نوع اشتباه دارد.
    if not isinstance(faq, dict):
        faq = merged["faq"] = {}
    for lang in ("fa", "en", "tr", "ar"):
        if not isinstance(faq.get(lang), list):
            faq[lang] = []

    # تضمین اینکه کلیدهای پلتفرم اپ‌ها همیشه وجود دارند
    apps = merged.setdefault("downloadApps", {})
    if not isinstance(apps, dict):
        apps = merged["downloadApps"] = {}
    for os_key in ("android", "ios", "desktop"):
        if not isinstance(apps.get(os_key), list):
            apps[os_key] = []

    for key in ("videos", "resellers", "customPalettes"):
        if not isinstance(merged.get(key), list):
            merged[key] = []

    # دیکشنری‌های تودرتو — اگر نوعشان خراب باشد، فرانت‌اند روی
    # خواندن فیلدهایشان کرش می‌کند
    for key in ("advanced", "links", "banners", "popup", "referral", "bot"):
        if not isinstance(merged.get(key), dict):
            merged[key] = dict(DEFAULT_CONFIG.get(key) or {})

    # مهاجرت از سیستم قدیمی (theme واحد) به سیستم ترکیبی.
    # نکته: چون DEFAULT_CONFIG خودش template دارد، باید بررسی کنیم که
    # کاربر در فایل ذخیره‌شده‌اش template نداشته — نه در نسخه‌ی ادغام‌شده.
    if stored.get("theme") and not stored.get("template"):
        old_map = {
            "aurora": ("classic", "ocean"), "midnight": ("classic", "violet"),
            "emerald": ("classic", "forest"), "sunset": ("wallet", "ember"),
            "carbon": ("console", "slate"), "neon": ("console", "rose"),
            "ocean": ("analytics", "cyan"), "royal": ("wallet", "gold"),
            "minimal": ("classic", "slate"),
        }
        tpl, pal = old_map.get(stored.get("theme"), ("classic", "ocean"))
        merged["template"] = tpl
        merged["palette"] = pal
    merged.setdefault("template", "classic")
    merged.setdefault("palette", "ocean")
    return merged


def load_config():
    """تنظیمات، همیشه با ساختارِ کامل."""
    # اول فقط نسخه را بپرس. بدنه ممکن است چند کیلوبایت باشد و
    # کشیدن و پارس‌کردنش وقتی چیزی عوض نشده، دور ریختنِ کار است.
    ver = config_version()
    if ver and _CFG_CACHE["version"] == ver and _CFG_CACHE["json"] is not None:
        # کپیِ تازه می‌دهیم: فراخوان‌ها مقدار را دست‌کاری می‌کنند و
        # بعد ذخیره — اگر همان شیء برگردد، کشِ مشترک آلوده می‌شود
        return json.loads(_CFG_CACHE["json"])
    body, ver = _cfg_raw()
    merged = _normalize_config(json.loads(body))
    _CFG_CACHE["version"] = ver
    _CFG_CACHE["json"] = json.dumps(merged, ensure_ascii=False)
    return merged


def save_config(data, expected_version=None):
    """
    ذخیره‌ی اتمی، با تاریخچه.

    `expected_version` اگر داده شود و با نسخه‌ی فعلی نخواند، ذخیره
    رد می‌شود — این همان چیزی است که جلوی «دو تبِ باز، یکی کارِ
    دیگری را پاک می‌کند» را می‌گیرد. فراخوان‌های داخلی ندهند؛
    آن‌ها خودشان همین حالا خوانده‌اند.

    `BEGIN IMMEDIATE` عمدی است: نسخه را باید *پیش از* نوشتن ادعا
    کرد، وگرنه دو نویسنده هر دو نسخه‌ی N را می‌خوانند و هر دو
    N+1 می‌نویسند.
    """
    body = json.dumps(data, ensure_ascii=False)
    con = _cfg_con()
    con.execute("BEGIN IMMEDIATE")
    try:
        row = con.execute(
            "SELECT body, version FROM panel_config WHERE id = 1").fetchone()
        cur_ver = int(row["version"]) if row else 0
        if expected_version is not None and int(expected_version) != cur_ver:
            raise HTTPException(
                status_code=409,
                detail="این تنظیمات را جای دیگری عوض کرده‌اید — "
                       "صفحه را تازه کنید تا تغییراتِ آن‌جا از بین نرود")
        new_ver = cur_ver + 1
        if row is not None:
            # نسخه‌ی *قبلی* در تاریخچه می‌نشیند، چون برگشت یعنی
            # برگشت به همان
            con.execute(
                "INSERT INTO panel_config_history (version, body) VALUES (?,?)",
                (cur_ver, row["body"]))
            con.execute(
                "DELETE FROM panel_config_history WHERE id NOT IN "
                "(SELECT id FROM panel_config_history ORDER BY id DESC LIMIT ?)",
                (CONFIG_HISTORY_KEEP,))
        con.execute(
            "INSERT INTO panel_config (id, body, version, updated_at) "
            "VALUES (1, ?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(id) DO UPDATE SET body=excluded.body, "
            "version=excluded.version, updated_at=CURRENT_TIMESTAMP",
            (body, new_ver))
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    _CFG_CACHE["version"] = None      # دفعه‌ی بعد دوباره بخوان
    return new_ver


def config_history(limit=20):
    """نسخه‌های قبلی — برای دیدن و برگشتن."""
    con = _cfg_con()
    rows = con.execute(
        "SELECT version, at, LENGTH(body) n FROM panel_config_history "
        "ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
    return [{"version": int(r["version"]), "at": r["at"], "size": int(r["n"])}
            for r in rows]


def config_rollback(version):
    """
    برگشت به یک نسخه‌ی قبلی.

    خودِ برگشت هم یک ذخیره‌ی تازه است، نه پاک‌کردنِ تاریخچه — پس
    اگر اشتباه بود، از همان راه برمی‌گردد.
    """
    con = _cfg_con()
    row = con.execute(
        "SELECT body FROM panel_config_history WHERE version = ? "
        "ORDER BY id DESC LIMIT 1", (int(version),)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="این نسخه در تاریخچه نیست")
    try:
        data = json.loads(row["body"])
    except json.JSONDecodeError:
        raise HTTPException(status_code=422,
                            detail="این نسخه خوانا نیست و برگرداندنی نیست")
    save_config(data)
    return _normalize_config(data)


# ═══════════════════════════════════════════════════════════
#  سدّ حدس‌زدن رمز
#
#  کل این سامانه پشت یک رمز است: پنل، اطلاعات مشتری‌ها، رمز x-ui،
#  توکن ربات. تا امروز هیچ چیزی جلوی حدس‌زدنِ پشت‌سرهم را نمی‌گرفت —
#  نه در /api/login و نه در هیچ‌کدام از مسیرهای مدیریتی، که همان رمز
#  را در هدر می‌گیرند و به همان اندازه برای حدس‌زدن در دسترس‌اند.
#
#  ماژول intrusion حمله‌ی SSH را می‌بیند و گزارش می‌دهد؛ درِ خودِ پنل
#  هیچ نگهبانی نداشت.
# ═══════════════════════════════════════════════════════════

#: چند تلاش ناموفق، در چه بازه‌ای، و چقدر قفل
AUTH_MAX_FAILS = 10
AUTH_WINDOW = 300        # ثانیه
AUTH_LOCK = 900          # ثانیه
#: سقف آی‌پی‌های زیر نظر — تا کسی با آی‌پی جعلی حافظه را پر نکند
AUTH_TRACK_MAX = 2048

_auth_fails = {}
_auth_ip = _contextvars.ContextVar("nexora_client_ip", default="?")


def _client_ip(request):
    """
    آی‌پی واقعی درخواست‌دهنده.

    پشت nginx همه‌ی درخواست‌ها از 127.0.0.1 می‌آیند، پس بدون
    X-Forwarded-For همه در یک سطل می‌افتند و یک مهاجم می‌تواند مدیر
    را بیرون بیندازد. ولی این هدر را فقط وقتی باور می‌کنیم که خودِ
    همسایه لوپ‌بک یا شبکه‌ی خصوصی باشد — یعنی nginx خودمان. از
    اینترنت هر کسی می‌تواند هر چیزی در آن بنویسد.
    """
    peer = ""
    try:
        peer = (request.client.host or "") if request.client else ""
    except Exception:
        peer = ""

    trusted = False
    try:
        ip = _ipaddress.ip_address(peer)
        trusted = ip.is_loopback or ip.is_private
    except ValueError:
        trusted = False

    if trusted:
        fwd = request.headers.get("x-forwarded-for") or ""
        first = fwd.split(",")[0].strip()
        if first:
            try:
                _ipaddress.ip_address(first)
                return first
            except ValueError:
                pass
    return peer or "?"


@app.middleware("http")
async def _remember_client_ip(request: Request, call_next):
    """
    آی‌پی را برای همین درخواست کنار می‌گذارد.

    check_auth از ۱۱۴ جا با همان یک آرگومان صدا زده می‌شود؛ عوض‌کردن
    امضایش یعنی دست‌زدن به همه‌ی آن‌ها. این‌طور نگهبان بدون تغییر
    هیچ صداکننده‌ای به آی‌پی می‌رسد.
    """
    token = _auth_ip.set(_client_ip(request))
    try:
        return await call_next(request)
    finally:
        _auth_ip.reset(token)


def _auth_locked(ip):
    """اگر قفل است، چند ثانیه‌ی دیگر باز می‌شود؛ وگرنه صفر."""
    rec = _auth_fails.get(ip)
    if not rec:
        return 0
    if rec.get("until", 0) > _time.time():
        return int(rec["until"] - _time.time()) + 1
    return 0


def _auth_failed(ip):
    now = _time.time()
    rec = _auth_fails.get(ip)
    if not rec or now - rec.get("first", now) > AUTH_WINDOW:
        rec = {"first": now, "n": 0, "until": 0}
    rec["n"] += 1
    if rec["n"] >= AUTH_MAX_FAILS:
        rec["until"] = now + AUTH_LOCK
    if len(_auth_fails) >= AUTH_TRACK_MAX and ip not in _auth_fails:
        # قدیمی‌ترین را بیرون می‌اندازیم تا فهرست بی‌مرز رشد نکند
        try:
            oldest = min(_auth_fails, key=lambda k: _auth_fails[k].get("first", 0))
            _auth_fails.pop(oldest, None)
        except ValueError:
            pass
    _auth_fails[ip] = rec
    return rec


def _auth_ok(ip):
    """ورود درست یعنی پرونده بسته می‌شود."""
    _auth_fails.pop(ip, None)


def check_auth(x_admin_password: str = Header(...)):
    ip = _auth_ip.get()

    wait = _auth_locked(ip)
    if wait:
        raise HTTPException(
            status_code=429,
            detail=f"تلاش‌های ناموفق زیاد بود. {wait // 60 + 1} دقیقه‌ی دیگر "
                   "دوباره امتحان کنید.",
            headers={"Retry-After": str(wait)})

    # مقایسه‌ی زمان‌ثابت: مقایسه‌ی معمولی روی اولین بایتِ متفاوت
    # برمی‌گردد و همان اختلاف، هرچند کوچک، رمز را بایت‌به‌بایت لو
    # می‌دهد.
    # بایت مقایسه می‌کنیم، نه رشته: compare_digest روی رشته‌ی غیر
    # اسکی TypeError می‌دهد — یعنی یک رمز فارسی کل پنل را با خطای
    # ۵۰۰ می‌بست، نه فقط ورود را.
    if x_admin_password == _INTERNAL_PW:
        return True
    if not verify_password(x_admin_password):
        rec = _auth_failed(ip)
        left = AUTH_MAX_FAILS - rec["n"]
        detail = "رمز عبور نادرست است"
        if 0 < left <= 3:
            detail += f" — {left} تلاش دیگر تا قفل‌شدن موقت"
        raise HTTPException(status_code=401, detail=detail)

    _auth_ok(ip)


#: کلیدهایی که به مرورگر مشتری فرستاده می‌شوند.
#
#  این عمداً فهرستِ «مجاز» است، نه فهرستِ «حذف کن».
#
#  قبلاً برعکس بود: هر چیزی جز resellers و bot عمومی می‌شد. یعنی هر
#  کلیدِ تازه‌ای که به تنظیمات اضافه می‌شد، خودبه‌خود روی صفحه‌ی
#  عمومی می‌نشست — maintenance (ساعت ری‌استارت سرور، آستانه‌ی شلوغی،
#  آخرین خطا) دقیقاً همین‌طور بیرون می‌رفت.
#
#  با فهرست مجاز، جهتِ اشتباه بی‌خطر است: فراموش‌کردن یک کلید یعنی
#  قابلیتی نمایش داده نمی‌شود، نه اینکه چیزی درز کند. اگر قابلیت
#  تازه‌ای لازم دارد روی صفحه دیده شود، همین‌جا اضافه‌اش کنید.
PUBLIC_CONFIG_KEYS = {
    "downloadApps", "faq", "banners", "referral", "links",
    "videoTutorialUrl", "videos", "advanced", "popup",
    "template", "palette", "customPalettes",
}


@app.get("/api/public/config")
def get_public_config(request: Request, response: Response, email: str = None, host: str = None):
    """
    تنظیمات را برمی‌گرداند. اگر مشتری متعلق به یک واسطه باشد،
    تنظیمات همان واسطه (ادغام‌شده روی تنظیمات پایه) برگردانده می‌شود.

    تشخیص واسطه:
      - پارامتر host یا هدر Origin/Referer (تطبیق دامنه)
      - پارامتر email (تطبیق پیشوند ایمیل کلاینت)
    """
    # جلوگیری از کش شدن توسط مرورگر، کلودفلر یا هر CDN دیگری.
    # بدون این، مشتری ممکن است ساعت‌ها تنظیمات قدیمی را ببیند.
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    cfg = load_config()

    # اگر host به‌صراحت داده نشده، از Origin یا Referer استخراج می‌کنیم
    if not host:
        origin = request.headers.get("origin") or request.headers.get("referer") or ""
        if origin:
            host = origin.replace("https://", "").replace("http://", "").split("/")[0]

    reseller = find_reseller(cfg, email=email, host=host)

    # فقط چیزهایی که صفحه‌ی اشتراک واقعاً لازم دارد.
    public_cfg = {k: v for k, v in cfg.items() if k in PUBLIC_CONFIG_KEYS}

    if reseller:
        # overrides هم از همان صافی رد می‌شود. این‌ها را مدیر می‌نویسد
        # نه مهاجم، ولی یک کلیدِ اشتباهی در overrides نباید بتواند
        # چیزی را که بالا حذف شده دوباره برگرداند.
        merged = deep_merge(public_cfg, reseller.get("overrides", {}))
        public_cfg = {k: v for k, v in merged.items()
                      if k in PUBLIC_CONFIG_KEYS}
        public_cfg["_resellerId"] = reseller.get("id")

    # قالب فعال را به‌صورت کامل ضمیمه می‌کنیم تا صفحه‌ی اشتراک
    # بتواند مستقیم متغیرهای رنگ و چیدمان را اعمال کند.
    # واسطه می‌تواند قالب متفاوتی داشته باشد (theme در overrides).
    # ترکیب ساختار و رنگ — واسطه می‌تواند هر دو را متفاوت داشته باشد
    public_cfg["_theme"] = resolve_theme(
        cfg, public_cfg.get("template"), public_cfg.get("palette")
    )

    return public_cfg


@app.get("/api/admin/themes")
def list_themes(x_admin_password: str = Header(...)):
    """ساختارها و پالت‌ها برای انتخاب در پنل."""
    check_auth(x_admin_password)
    cfg = load_config()
    return {
        "currentTemplate": cfg.get("template", "classic"),
        "currentPalette": cfg.get("palette", "ocean"),
        "templates": TEMPLATES,
        "palettes": PALETTES,
        "customPalettes": cfg.get("customPalettes", []),
    }


@app.post("/api/admin/palettes")
def add_custom_palette(payload: dict, x_admin_password: str = Header(...)):
    """افزودن پالت رنگی سفارشی."""
    check_auth(x_admin_password)
    cfg = load_config()

    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="نام پالت الزامی است")

    customs = cfg.setdefault("customPalettes", [])
    if len(customs) >= 20:
        raise HTTPException(status_code=400, detail="حداکثر ۲۰ پالت سفارشی مجاز است")

    pal_id = payload.get("id") or f"pal-{int(datetime.now().timestamp())}"
    if any(p.get("id") == pal_id for p in customs) or any(p["id"] == pal_id for p in PALETTES):
        raise HTTPException(status_code=400, detail="پالتی با این شناسه وجود دارد")

    allowed = {"accent", "accent2", "bg", "surface", "surfaceAlt", "border", "text", "textMuted"}
    raw = payload.get("vars") or {}
    pal = {
        "id": pal_id,
        "name": name,
        "fa": (payload.get("fa") or name).strip(),
        "builtin": False,
        "vars": {k: str(v)[:60] for k, v in raw.items() if k in allowed},
    }

    customs.append(pal)
    save_config(cfg)
    return {"ok": True, "palette": pal}


@app.delete("/api/admin/palettes/{palette_id}")
def delete_custom_palette(palette_id: str, x_admin_password: str = Header(...)):
    """حذف پالت سفارشی. پالت‌های داخلی حذف نمی‌شوند."""
    check_auth(x_admin_password)
    cfg = load_config()

    customs = cfg.get("customPalettes", [])
    if not any(p.get("id") == palette_id for p in customs):
        raise HTTPException(status_code=404, detail="پالت پیدا نشد")

    cfg["customPalettes"] = [p for p in customs if p.get("id") != palette_id]

    if cfg.get("palette") == palette_id:
        cfg["palette"] = "ocean"
    for r in cfg.get("resellers", []):
        if r.get("overrides", {}).get("palette") == palette_id:
            r["overrides"].pop("palette", None)

    save_config(cfg)
    return {"ok": True}


@app.post("/api/login")
def login(payload: dict):
    # همان نگهبان — وگرنه بستن یک در و باز گذاشتن آن یکی.
    check_auth((payload or {}).get("password") or "")
    return {"ok": True}


def _panel_host(request):
    """
    دامنه‌ی پنل، فقط وقتی مطمئن باشیم روی https باز شده. وگرنه "" .

    چرا دو منبع و نه فقط هدر `X-Forwarded-Proto`:

    نسخه‌ی اول فقط آن هدر را می‌خواند، و روی نصب‌های واقعی **هیچ‌وقت
    درست نشد** — چون بلوک nginx خودمان آن را جلو نمی‌فرستاد. TLS روی
    nginx تمام می‌شد و درخواست به uvicorn به شکل http می‌رسید، پس
    شرط همیشه رد می‌شد و آدرس مینی‌اپ هرگز ثبت نمی‌شد. یعنی قابلیتی
    که «بدون تنظیم کار می‌کند» اعلام شده بود، روی سرور کار نمی‌کرد و
    هیچ‌جا هم نمی‌گفت چرا. (بلوک nginx هم در همین نسخه اصلاح شد، ولی
    نصب‌های موجود فایل قدیمی را دارند.)

    `Referer` را خودِ مرورگر می‌گذارد و نوار آدرسِ همان پنل است — یعنی
    دقیقاً همان چیزی که می‌خواهیم بدانیم، بدون وابستگی به تنظیم nginx.
    این مسیر رمز مدیر می‌خواهد، پس فقط مرورگرِ خودِ مالک به این‌جا
    می‌رسد و سطح اعتماد همان قبلی است.
    """
    def _clean(h):
        h = (h or "").split(",")[0].strip()
        return "" if (not h or any(c in h for c in " /\\?#@")) else h

    # ۱) نوار آدرسِ خودِ مرورگر
    for key in ("referer", "origin"):
        raw = (request.headers.get(key) or "").strip()
        if not raw.lower().startswith("https://"):
            continue
        host = _clean(raw[len("https://"):].split("/")[0])
        if host:
            return host

    # ۲) هدر پروکسی — برای نصب‌هایی که تنظیمش دارند
    if (request.headers.get("x-forwarded-proto") or "").strip().lower() == "https":
        return _clean(request.headers.get("host"))

    # بدون https آدرسی نمی‌سازیم: تلگرام خودش ردش می‌کند و
    # ثبت‌کردنش فقط یک مقدارِ مرده به جا می‌گذارد
    return ""


def _learn_panel_origin(request):
    """
    دامنه‌ی خودِ پنل را یک‌بار یاد می‌گیرد و آدرس مینی‌اپ را می‌سازد.

    چرا این‌جا: مینی‌اپ از همان `frontend/dist` سرو می‌شود که پنل، و
    nginx هم `try_files` دارد — پس `https://<دامنه‌ی پنل>/app` بدون
    هیچ تنظیم تازه‌ای بالا می‌آید. تنها چیزی که کم بود، خودِ دامنه
    بود؛ و این‌جا در هدر Host نشسته است.

    چرا از مسیر مدیر و نه مسیر عمومی: هدر Host را فرستنده تعیین
    می‌کند. روی یک مسیر عمومی، هر کسی می‌توانست دامنه‌ی دلخواهش را
    ثبت کند و مینی‌اپِ مشتری‌ها را به صفحه‌ی خودش ببرد. این مسیر رمز
    مدیر می‌خواهد، پس فقط مرورگرِ خودِ مالک به این‌جا می‌رسد.

    یک‌بار نوشته می‌شود و بعد دست نمی‌خورد — تا اگر مالک آدرس دیگری
    گذاشت، بازکردنِ دوباره‌ی پنل رویش ننویسد.
    """
    try:
        host = _panel_host(request)
        if not host:
            return

        con = _bot_rw()
        try:
            row = con.execute(
                "SELECT id, settings FROM tenants WHERE parent_id IS NULL "
                "ORDER BY id LIMIT 1").fetchone()
            if not row:
                return
            try:
                st = json.loads(row["settings"] or "{}")
            except (json.JSONDecodeError, TypeError):
                st = {}
            if str(st.get("miniapp_url") or "").strip():
                return                      # مالک خودش گذاشته — دست نمی‌زنیم
            st["miniapp_url"] = f"https://{host}/app"
            con.execute("UPDATE tenants SET settings=? WHERE id=?",
                        (json.dumps(st, ensure_ascii=False), row["id"]))
            con.commit()
            log.info("آدرس مینی‌اپ ثبت شد: %s", st["miniapp_url"])
        finally:
            con.close()
    except Exception:
        # یادگرفتنِ دامنه راحتی است، نه شرطِ بازشدنِ پنل
        log.debug("ثبت خودکار آدرس مینی‌اپ ناموفق", exc_info=True)


@app.get("/api/admin/config")
def get_admin_config(request: Request, response: Response,
                     x_admin_password: str = Header(...)):
    """
    تنظیمات، به‌علاوه‌ی نسخه‌اش در هدر.

    چرا در هدر و نه داخل خودِ سند: پنل همین سند را می‌گیرد، دست‌کاری
    می‌کند و عیناً پس می‌فرستد. هر کلیدی که این‌جا اضافه شود، آن‌جا
    ذخیره می‌شود و برای همیشه در تنظیمات می‌ماند.
    """
    check_auth(x_admin_password)
    _learn_panel_origin(request)
    cfg = load_config()
    response.headers["X-Config-Version"] = str(config_version())
    return cfg


@app.put("/api/admin/config")
def update_config(payload: dict, x_admin_password: str = Header(...),
                  x_config_version: str = Header(None)):
    """
    ذخیره — و اگر جای دیگری عوض شده باشد، رد.

    بدون این، دو تبِ باز یعنی هر کدام که دیرتر ذخیره کند کارِ
    دیگری را بی‌صدا پاک می‌کند. پنل نسخه‌ای را که گرفته پس
    می‌فرستد؛ اگر نخواند، خطای روشن می‌گیرد نه پاک‌شدنِ خاموش.
    """
    check_auth(x_admin_password)
    want = None
    if x_config_version not in (None, ""):
        try:
            want = int(x_config_version)
        except ValueError:
            want = None
    ver = save_config(payload, expected_version=want)
    return {"ok": True, "version": ver}


@app.get("/api/admin/config/history")
def get_config_history(x_admin_password: str = Header(...)):
    """نسخه‌های قبلیِ تنظیمات."""
    check_auth(x_admin_password)
    return {"current": config_version(), "versions": config_history()}


@app.post("/api/admin/config/rollback/{version}")
def post_config_rollback(version: int, x_admin_password: str = Header(...)):
    """برگشت به یک نسخه‌ی قبلی."""
    check_auth(x_admin_password)
    cfg = config_rollback(version)
    return {"ok": True, "version": config_version(), "config": cfg}


@app.post("/api/admin/reset-defaults")
def reset_defaults(x_admin_password: str = Header(...)):
    check_auth(x_admin_password)
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG


@app.get("/api/admin/stats")
def get_stats(x_admin_password: str = Header(...)):
    """آمار خلاصه برای نمایش در داشبورد."""
    check_auth(x_admin_password)
    cfg = load_config()

    apps = cfg.get("downloadApps", {})
    faq = cfg.get("faq", {})
    videos = cfg.get("videos", [])
    advanced = cfg.get("advanced", {})

    apps_count = sum(len(v or []) for v in apps.values())
    faq_count = sum(len(v or []) for v in faq.values())

    # شمارش اپ‌های پیشنهادی تعیین‌شده
    recommended = {}
    for os_key, lst in apps.items():
        rec = next((a for a in (lst or []) if a.get("recommended")), None)
        recommended[os_key] = rec.get("name") if rec else None

    active_features = {
        "banners": cfg.get("banners", {}).get("enabled", False),
        "referral": cfg.get("referral", {}).get("enabled", False),
        "faqSection": advanced.get("showFaqSection", True),
        "notificationPopup": advanced.get("showNotificationPopup", True),
        "brandStrip": advanced.get("showBrandStrip", True),
    }

    return {
        "appsCount": apps_count,
        "faqCount": faq_count,
        "videosCount": len(videos),
        "appsPerPlatform": {k: len(v or []) for k, v in apps.items()},
        "faqPerLanguage": {k: len(v or []) for k, v in faq.items()},
        "recommendedApps": recommended,
        "activeFeatures": active_features,
        "activeFeaturesCount": sum(1 for v in active_features.values() if v),
    }


def render_preview_html(raw: str) -> str:
    """
    فایل قالب را برای پیش‌نمایش آماده می‌کند.

    چون فایل یک قالب Go template است (که فقط پنل 3x-ui می‌تواند رندرش کند)،
    برای نمایش در پنل مدیریت، متغیرهای {{ .xxx }} را با داده‌ی نمونه
    جایگزین می‌کنیم — دقیقاً همان کاری که پنل واقعی با داده‌ی واقعی می‌کند.
    """

    now = int(datetime.now().timestamp())
    sample = {
        "sId": "preview-sample-id",
        "enabled": "true",
        "expire": str(now + 15 * 86400),
        "downloadByte": "3221225472",
        "uploadByte": "536870912",
        "totalByte": "32212254720",
        "subUrl": "https://example.com/sub/preview-sample",
        "subJsonUrl": "https://example.com/json/preview-sample",
        "subClashUrl": "https://example.com/clash/preview-sample",
        "subTitle": "NexoraVpn",
        "subSupportUrl": "https://t.me/crm_nexoravpn",
        "datepicker": "gregorian",
        "lastOnline": str((now - 300) * 1000),
        "download": "3.0 GB",
        "upload": "512 MB",
        "total": "30 GB",
        "used": "3.5 GB",
        "remained": "26.5 GB",
    }

    out = raw

    # ۱. حلقه‌ی emails
    # نکته: از lambda استفاده می‌کنیم چون رشته‌ی جایگزین ممکن است شامل
    # کاراکترهایی مثل \u باشد که re.sub آن‌ها را به‌عنوان escape تفسیر می‌کند.
    out = _re.sub(
        r"\[\s*\{\{\s*range\s+\$i,\s*\$e\s*:=\s*\.emails\s*\}\}.*?\{\{\s*end\s*\}\}\s*\]",
        lambda m: '["preview@nexora"]',
        out, flags=_re.DOTALL,
    )

    # ۲. حلقه‌ی links
    sample_links = (
        '["vless://11111111-2222-3333-4444-555555555555@example.com:443'
        '?type=ws&security=tls&path=%2Fpreview#FR-Nexora-Sample-1",'
        '"vless://11111111-2222-3333-4444-555555555555@example.com:2053'
        '?type=ws&security=tls&path=%2Fpreview#TR-Nexora-Sample-2"]'
    )
    out = _re.sub(
        r"\[\s*\{\{\s*range\s+\$i,\s*\$l\s*:=\s*\.links\s*\}\}.*?\{\{\s*end\s*\}\}\s*\]",
        lambda m: sample_links,
        out, flags=_re.DOTALL,
    )

    # ۳. متغیرهای ساده
    for key, val in sample.items():
        out = _re.sub(r"\{\{\s*\." + key + r"\s*\}\}", lambda m, v=val: v, out)

    # ۴. هر متغیر باقی‌مانده‌ی ناشناخته → رشته‌ی خالی (تا JS نشکند)
    out = _re.sub(r"\{\{[^}]*\}\}", lambda m: "", out)

    return out


@app.get("/api/preview", response_class=HTMLResponse)
def preview_subpage():
    """صفحه‌ی اشتراک را با داده‌ی نمونه برای مشاهده در پنل مدیریت سرو می‌کند."""
    html_path = Path(os.getenv("SUBPAGE_HTML_PATH", "../sub-page-index.html"))
    if not html_path.exists():
        return HTMLResponse(
            "<div style='font-family:sans-serif;padding:40px;text-align:center;"
            "color:#888;background:#06090f;height:100vh'>فایل قالب پیدا نشد.<br>"
            f"مسیر مورد انتظار: {html_path.resolve()}</div>",
            status_code=404,
        )

    raw = html_path.read_text(encoding="utf-8")
    return HTMLResponse(render_preview_html(raw))


@app.post("/api/admin/change-password")
def change_password(payload: dict, x_admin_password: str = Header(...)):
    """
    تغییر رمز عبور مدیریت.
    نیازمند رمز فعلی است تا اگر کسی به مرورگر باز شما دسترسی پیدا کرد،
    نتواند بدون دانستن رمز فعلی آن را عوض کند.
    """
    check_auth(x_admin_password)

    current = payload.get("currentPassword", "")
    new = payload.get("newPassword", "")

    # `!=` روی مقدارِ ذخیره‌شده کار نمی‌کند وقتی هَش است
    if not _pw_check(current, _stored_password()):
        raise HTTPException(status_code=400, detail="رمز عبور فعلی نادرست است")

    if len(new) < 8:
        raise HTTPException(status_code=400, detail="رمز جدید باید حداقل ۸ کاراکتر باشد")

    if new == current:
        raise HTTPException(status_code=400, detail="رمز جدید نباید با رمز فعلی یکسان باشد")

    save_password(new)
    return {"ok": True, "message": "رمز عبور با موفقیت تغییر کرد"}


@app.get("/api/admin/export")
def export_config(x_admin_password: str = Header(...)):
    """خروجی کامل تنظیمات برای پشتیبان‌گیری (بدون رمز عبور)."""
    check_auth(x_admin_password)
    cfg = load_config()
    return {
        "_exportedAt": datetime.now().isoformat(),
        "_version": "1.0",
        "config": cfg,
    }


@app.post("/api/admin/import")
def import_config(payload: dict, x_admin_password: str = Header(...)):
    """بازیابی تنظیمات از فایل پشتیبان."""
    check_auth(x_admin_password)

    cfg = payload.get("config") or payload
    if not isinstance(cfg, dict) or "downloadApps" not in cfg:
        raise HTTPException(status_code=400, detail="فایل پشتیبان معتبر نیست")

    # پشتیبان از نسخه‌ی فعلی قبل از بازنویسی (برای بازگشت در صورت اشتباه)
    try:
        backup_path = CONFIG_PATH.parent / f"config.backup.{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as src, open(backup_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())
    except OSError:
        pass

    save_config(cfg)
    return {"ok": True, "message": "تنظیمات با موفقیت بازیابی شد"}


def _frontend_build_info():
    """
    وضعیت بیلد فرانت‌اند.

    اگر بیلد قدیمی‌تر از کد باشد، یعنی آخرین به‌روزرسانی بیلد نشده و
    کاربر دارد نسخه‌ی قبلی پنل را می‌بیند — دقیقاً همان حالتی که
    گیج‌کننده است چون VERSION جدید نشان می‌دهد.
    """
    root = _root_dir()
    dist = root / "frontend" / "dist" / "index.html"
    src = root / "frontend" / "src" / "App.jsx"

    if not dist.exists():
        return {"built": False, "stale": True,
                "note": "پنل هنوز ساخته نشده — nexora rebuild را اجرا کنید"}

    try:
        d_time = dist.stat().st_mtime
        s_time = src.stat().st_mtime if src.exists() else 0
        stale = s_time > d_time + 5
        return {
            "built": True,
            "stale": stale,
            "builtAt": datetime.fromtimestamp(d_time).isoformat(timespec="seconds"),
            "note": ("کد جدیدتر از بیلد است — nexora rebuild را اجرا کنید"
                     if stale else None),
        }
    except OSError:
        return {"built": True, "stale": False}


@app.get("/api/admin/system")
def system_info(x_admin_password: str = Header(...)):
    """اطلاعات نسخه و وضعیت سیستم برای نمایش در پنل."""
    check_auth(x_admin_password)

    version = "unknown"
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    if version_file.exists():
        try:
            version = version_file.read_text(encoding="utf-8").strip()
        except OSError:
            pass

    html_path = Path(os.getenv("SUBPAGE_HTML_PATH", "../sub-page-index.html"))
    template_ok = html_path.exists()
    template_size = html_path.stat().st_size if template_ok else 0

    # آدرس API تنظیم‌شده داخل قالب
    api_url = None
    if template_ok:
        try:
            content = html_path.read_text(encoding="utf-8")
            m = _re.search(r'const SUBPAGE_CONFIG_API = "([^"]*)"', content)
            if m:
                api_url = m.group(1)
        except OSError:
            pass

    cfg = load_config()
    return {
        "build": _frontend_build_info(),
        "version": version,
        "template": {
            "path": str(html_path),
            "exists": template_ok,
            "size": template_size,
            "apiUrl": api_url,
        },
        "counts": {
            "apps": sum(len(v or []) for v in cfg.get("downloadApps", {}).values()),
            "faq": sum(len(v or []) for v in cfg.get("faq", {}).values()),
            "videos": len(cfg.get("videos", [])),
            "resellers": len(cfg.get("resellers", [])),
        },
        "configPath": str(CONFIG_PATH),
        "configExists": CONFIG_PATH.exists(),
    }


@app.get("/api/admin/check-update")
def check_update(x_admin_password: str = Header(...)):
    """
    بررسی وجود نسخه‌ی جدید در گیت‌هاب.
    فقط چک می‌کند — چیزی نصب نمی‌کند.
    """
    check_auth(x_admin_password)

    root = Path(__file__).resolve().parent.parent
    current = "unknown"
    vf = root / "VERSION"
    if vf.exists():
        try:
            current = vf.read_text(encoding="utf-8").strip()
        except OSError:
            pass

    # خواندن مخزن از فایل .github (اگر نصب‌کننده آن را ساخته باشد)
    repo, token = None, None
    gh = root / ".github"
    if gh.exists():
        try:
            for line in gh.read_text(encoding="utf-8").splitlines():
                if line.startswith("GITHUB_REPO="):
                    repo = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("GITHUB_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
        except OSError:
            pass

    if not repo:
        return {
            "currentVersion": current,
            "latestVersion": None,
            "updateAvailable": False,
            "configured": False,
            "message": "به‌روزرسانی خودکار تنظیم نشده است",
        }

    try:
        import urllib.request

        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/releases/latest",
            headers={"Accept": "application/vnd.github+json", "User-Agent": "nexora-panel"},
        )
        if token:
            req.add_header("Authorization", f"token {token}")

        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.load(resp)

        latest = (data.get("tag_name") or "").lstrip("v")
        notes = data.get("body") or ""
        published = data.get("published_at")

        def parse(v):
            try:
                return tuple(int(x) for x in v.split("."))
            except (ValueError, AttributeError):
                return (0,)

        available = bool(latest) and parse(latest) > parse(current)

        return {
            "currentVersion": current,
            "latestVersion": latest,
            "updateAvailable": available,
            "configured": True,
            "releaseNotes": notes[:2000],
            "publishedAt": published,
            "repo": repo,
        }
    except Exception as e:
        return {
            "currentVersion": current,
            "latestVersion": None,
            "updateAvailable": False,
            "configured": True,
            "error": str(e)[:200],
            "message": "ارتباط با گیت‌هاب برقرار نشد",
        }


@app.post("/api/admin/run-update")
def run_update(x_admin_password: str = Header(...)):
    """
    اجرای به‌روزرسانی در پس‌زمینه.

    نکته: این عملیات سرویس را ری‌استارت می‌کند، پس نمی‌توانیم منتظر
    نتیجه‌اش بمانیم. اسکریپت جدا (detached) اجرا می‌شود تا بعد از
    قطع شدن این پروسه هم ادامه پیدا کند.
    """
    check_auth(x_admin_password)

    root = Path(__file__).resolve().parent.parent
    if not (root / ".github").exists():
        raise HTTPException(status_code=400, detail="به‌روزرسانی خودکار تنظیم نشده است")

    cli = Path("/usr/local/bin/nexora")
    if not cli.exists():
        cli = root / "nexora-cli.sh"
    if not cli.exists():
        raise HTTPException(status_code=400, detail="اسکریپت به‌روزرسانی پیدا نشد")

    log_path = "/tmp/nexora-update.log"
    try:
        import subprocess

        subprocess.Popen(
            f"nohup bash {cli} update > {log_path} 2>&1 &",
            shell=True,
            start_new_session=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"اجرای به‌روزرسانی ناموفق بود: {e}")

    return {
        "ok": True,
        "message": "به‌روزرسانی شروع شد. حدود ۲ تا ۵ دقیقه طول می‌کشد.",
        "logPath": log_path,
    }


@app.get("/api/admin/update-log")
def update_log(x_admin_password: str = Header(...)):
    """خواندن لاگ آخرین به‌روزرسانی."""
    check_auth(x_admin_password)
    p = Path("/tmp/nexora-update.log")
    if not p.exists():
        return {"exists": False, "lines": []}
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        # حذف کدهای رنگ ترمینال برای نمایش تمیز در مرورگر
        clean = [_re.sub(r"\x1b\[[0-9;]*m", "", ln) for ln in lines[-60:]]
        # نشانه‌های پایان کار — چند حالت مختلف را پوشش می‌دهیم چون
        # اسکریپت ممکن است با پیام‌های متفاوتی تمام شود
        end_markers = ("UPDATE COMPLETE", "Already on the latest",
                       "Version did not change", "ROLLBACK COMPLETE")
        done = any(any(m in ln for m in end_markers) for ln in clean)
        failed = any(ln.strip().startswith("✗") for ln in clean)
        return {"exists": True, "lines": clean, "finished": done, "failed": failed}
    except OSError as e:
        return {"exists": False, "lines": [], "error": str(e)}


# ═══════════════════════════════════════════════════════════
#  مدیریت ربات — ماژول جدا (bot/)
#  پنل فقط به دیتابیس ربات نگاه می‌کند؛ اگر ربات نصب نباشد،
#  این endpointها پاسخ خالی می‌دهند و پنل مثل قبل کار می‌کند.
# ═══════════════════════════════════════════════════════════

BOT_DB = Path(os.getenv("BOT_DB_PATH", str(CONFIG_PATH.parent / "bot.db")))


def _row_get(row, key, default=None):
    """
    یک ستون از ردیف، وقتی ممکن است اصلاً نباشد.

    `sqlite3.Row` برای کلیدِ ناموجود IndexError می‌دهد، نه None. و
    ترتیبِ به‌روزرسانی روی سرور همیشه مرتب نیست: پنل تازه می‌شود و
    ربات هنوز ری‌استارت نشده، پس ستونی که مهاجرتِ ربات می‌سازد
    هنوز وجود ندارد. بدون این، کلِ صندوق ۵۰۳ می‌شد به‌جای اینکه
    فقط یک عکس نیاید.
    """
    try:
        v = row[key]
    except (IndexError, KeyError, TypeError):
        return default
    return default if v is None else v


def _bot_conn():
    """اتصال فقط‌خواندنی به دیتابیس ربات. اگر نبود، None."""
    if not BOT_DB.exists():
        return None
    try:
        import sqlite3
        con = sqlite3.connect(f"file:{BOT_DB}?mode=ro", uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        return con
    except Exception:
        return None


#: «خرید واقعی» — یک تعریف، برای هر جایی که می‌پرسد چند نفر خریدند.
#
#  گرفتن تست رایگان خودش یک سفارشِ `approved` با مبلغ صفر می‌سازد. هر
#  شمارشی که این را کنار نگذارد، کسانی را که فقط دکمه‌ی تست را زده‌اند
#  «خریدار» حساب می‌کند.
#
#  قیف تبدیل در ۱.۳۷.۰ درست شد ولی گزارش فروش تعریف خودش را داشت، پس
#  پنل دو نرخ تبدیل نشان می‌داد: ۸۰٪ و ۲۰٪ روی همان داده. حالا هر سه
#  جا — قیف، گزارش فروش، و آمار پنل نماینده — از همین می‌خوانند.
SQL_PLAN_JOIN = "LEFT JOIN plans p ON p.id = o.plan_id"
SQL_REAL_BUY = "o.status='approved' AND COALESCE(p.is_trial,0)=0"


@app.get("/api/admin/bot/inbounds")
def bot_inbounds(tenant: int = None, x_admin_password: str = Header(...)):
    """
    اینباندهای پنل با نام و مشخصات.

    تا مدیر با نام انتخاب کند نه با شماره — کسی شماره‌ی اینباند
    را حفظ نیست، ولی نامش را می‌شناسد.
    """
    check_auth(x_admin_password)
    ok, err = _ensure_bot_db()
    if not ok:
        return {"ready": False, "error": err, "inbounds": []}

    con = _bot_conn()
    if not con:
        return {"ready": False, "error": "دیتابیس ربات در دسترس نیست",
                "inbounds": []}
    try:
        # اعتبارنامه‌ی پنل x-ui همیشه مالِ مالک است — ردیف نماینده
        # معمولاً خالی است و صفحه بدون هیچ توضیحی «اینباندی نیست»
        # نشان می‌داد.
        root = con.execute(
            "SELECT panel_url, panel_user, panel_pass, panel_token, "
            "default_inbound, inbound_mode, inbound_ids "
            "FROM tenants WHERE parent_id IS NULL "
            "ORDER BY id LIMIT 1").fetchone()
        t = dict(root) if root else {}

        # ولی *انتخابِ* اینباند مالِ همان مستاجری است که پرسیده شده.
        # قبلاً همیشه ریشه خوانده می‌شد، پس تنظیم هر نماینده نه دیده
        # می‌شد و نه قابل تغییر بود.
        if tenant:
            own = con.execute(
                "SELECT default_inbound, inbound_mode, inbound_ids "
                "FROM tenants WHERE id=?", (int(tenant),)).fetchone()
            if not own:
                return {"ready": False, "error": "نماینده پیدا نشد",
                        "inbounds": []}
            t.update({k: own[k] for k in
                      ("default_inbound", "inbound_mode", "inbound_ids")})
    except Exception as e:
        return {"ready": False, "error": str(e)[:150], "inbounds": []}
    finally:
        con.close()

    if not t.get("panel_url"):
        return {"ready": False, "error": "اتصال پنل تنظیم نشده", "inbounds": []}

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_nx_xui", _bot_dir() / "xui.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        cl = m.XUI(t["panel_url"], t.get("panel_user"),
                   t.get("panel_pass"), t.get("panel_token"))
        raw = cl.inbounds()
    except Exception as e:
        return {"ready": False, "error": f"خواندن اینباندها ناموفق: {str(e)[:120]}",
                "inbounds": []}

    out = []
    for i in raw:
        out.append({
            "id": i.get("id"),
            "remark": i.get("remark") or f"اینباند {i.get('id')}",
            "protocol": i.get("protocol") or "",
            "port": i.get("port"),
            "enable": bool(i.get("enable", True)),
        })

    try:
        selected = json.loads(t.get("inbound_ids") or "[]")
    except (json.JSONDecodeError, TypeError):
        selected = []

    return {
        "ready": True,
        "inbounds": out,
        "mode": t.get("inbound_mode") or "all",
        "selected": selected,
        "default": t.get("default_inbound"),
        "tenant": int(tenant) if tenant else None,
    }


@app.put("/api/admin/bot/inbounds")
def bot_inbounds_set(payload: dict, x_admin_password: str = Header(...)):
    """
    تعیین اینباندهایی که کانفیگ روی آن‌ها ساخته شود.

    mode:
      all     → همه‌ی اینباندهای فعال
      default → فقط اینباند پیش‌فرض
      custom  → همان‌هایی که انتخاب شده

    `tenant` در بدنه یعنی «برای همین نماینده». بدون آن، مستاجر ریشه —
    یعنی خودِ مالک.

    قبلاً این دستور `WHERE` نداشت و روی *همه‌ی* مستاجرها می‌نوشت. یعنی
    هر بار که مالک اینباندهای خودش را تنظیم می‌کرد، همان تنظیم بی‌صدا
    روی تک‌تک نماینده‌ها هم می‌نشست و انتخابِ خودشان را پاک می‌کرد.
    """
    check_auth(x_admin_password)
    mode = (payload or {}).get("mode") or "all"
    if mode not in ("all", "default", "custom"):
        raise HTTPException(status_code=400, detail="حالت نامعتبر")

    ids = payload.get("ids") or []
    clean = []
    for x in ids:
        try:
            clean.append(int(x))
        except (TypeError, ValueError):
            continue

    if mode == "custom" and not clean:
        raise HTTPException(status_code=400,
                            detail="در حالت انتخابی، حداقل یک اینباند لازم است")

    con = _bot_rw()
    try:
        tid = (payload or {}).get("tenant")
        if tid:
            row = con.execute("SELECT id FROM tenants WHERE id=?",
                              (int(tid),)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="نماینده پیدا نشد")
            target = int(tid)
        else:
            row = con.execute("SELECT id FROM tenants WHERE parent_id IS NULL "
                              "ORDER BY id LIMIT 1").fetchone()
            if not row:
                raise HTTPException(status_code=400,
                                    detail="مستاجر ریشه پیدا نشد")
            target = int(row["id"])

        cur = con.execute(
            "UPDATE tenants SET inbound_mode=?, inbound_ids=? WHERE id=?",
            (mode, json.dumps(clean), target))
        con.commit()
        if not cur.rowcount:
            raise HTTPException(status_code=404, detail="چیزی تغییر نکرد")
        return {"ok": True, "mode": mode, "ids": clean, "tenant": target}
    finally:
        con.close()


@app.get("/api/admin/bot/affiliates")
def bot_affiliates(x_admin_password: str = Header(...)):
    """همکاران فروش با آمار و مانده‌ی هرکدام."""
    check_auth(x_admin_password)
    ok, err = _ensure_bot_db()
    if not ok:
        return {"ready": False, "error": err, "affiliates": []}

    con = _bot_conn()
    if not con:
        return {"ready": False, "error": "دیتابیس ربات در دسترس نیست",
                "affiliates": []}
    try:
        # «مالِ خودم» دقیقاً با همان شرطی سنجیده می‌شود که دفتر کل
        # به کار می‌برد (`_affiliate_money_out`). این عمدی است: تا
        # وقتی هر دو یک عبارت را می‌خوانند، نمی‌توانند دو عدد متفاوت
        # بدهند. قبلاً این‌جا هیچ شرطی نبود و «مجموع بدهی به همکاران»
        # بدهیِ نماینده‌ها را هم به حساب مالک می‌گذاشت.
        rows = [dict(r) for r in con.execute("""
            SELECT a.*,
              t.name AS tenantName,
              (a.tenant_id IN (SELECT id FROM tenants
                                WHERE parent_id IS NULL)) AS isOwn,
              (SELECT COUNT(*) FROM users u WHERE u.affiliate_id = a.id) AS users,
              (SELECT COUNT(*) FROM affiliate_commissions c
                WHERE c.affiliate_id = a.id AND c.status != 'cancelled') AS orders,
              (SELECT COALESCE(SUM(order_amount),0) FROM affiliate_commissions c
                WHERE c.affiliate_id = a.id AND c.status != 'cancelled') AS sales,
              (SELECT COALESCE(SUM(commission),0) FROM affiliate_commissions c
                WHERE c.affiliate_id = a.id AND c.status != 'cancelled') AS earned,
              (SELECT COALESCE(SUM(amount),0) FROM affiliate_payouts p
                WHERE p.affiliate_id = a.id) AS payouts
            FROM affiliates a
            LEFT JOIN tenants t ON t.id = a.tenant_id
            ORDER BY a.id DESC""")]
        for r in rows:
            r["balance"] = r["earned"] - r["payouts"]
            r["isOwn"] = bool(r["isOwn"])

        # همکارهای نماینده‌ها پاک نمی‌شوند — هیچ صفحه‌ی دیگری آنها را
        # نشان نمی‌دهد و پنل نماینده اصلاً بخش همکاری ندارد. فقط جدا
        # شمرده می‌شوند: پورسانتِ همکارِ یک نماینده، هزینه‌ی همان
        # نماینده است، نه بدهیِ مالک.
        return {"ready": True, "affiliates": rows,
                "totalOwed": sum(r["balance"] for r in rows if r["isOwn"]),
                "resellerOwed": sum(r["balance"] for r in rows
                                    if not r["isOwn"])}
    except Exception as e:
        return {"ready": False, "error": str(e)[:160], "affiliates": []}
    finally:
        con.close()


@app.post("/api/admin/bot/affiliate")
def bot_affiliate_add(payload: dict, x_admin_password: str = Header(...)):
    check_auth(x_admin_password)
    _ensure_bot_db()

    name = (payload or {}).get("name", "").strip()[:60]
    if not name:
        raise HTTPException(status_code=400, detail="نام همکار لازم است")

    try:
        percent = float(payload.get("percent") or 10)
    except (TypeError, ValueError):
        percent = 10
    if not (0 < percent <= 100):
        raise HTTPException(status_code=400, detail="درصد باید بین ۰ تا ۱۰۰ باشد")

    code = (payload.get("code") or "").strip()
    if not code:
        code = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8]
    code = "".join(ch for ch in code if ch.isalnum())[:20]

    try:
        tg_id = int(payload.get("tg_id") or 0) or None
    except (TypeError, ValueError):
        tg_id = None

    import sqlite3 as sq
    con = sq.connect(str(BOT_DB), timeout=10)
    try:
        # همکارِ تازه باید زیر مستاجر ریشه ساخته شود.
        #
        # بدون این شرط به هر ردیفی که اول بیاید می‌چسبید. اگر آن ردیف
        # نماینده می‌بود، همکار در فهرست مالک اصلاً دیده نمی‌شد و
        # پورسانتش هم از دفتر کل مالک بیرون می‌ماند — چون آن‌جا فقط
        # مستاجرهای ریشه شمرده می‌شوند.
        tid = con.execute("SELECT id FROM tenants WHERE parent_id IS NULL "
                          "ORDER BY id LIMIT 1").fetchone()
        tid = tid[0] if tid else 1
        cur = con.execute(
            """INSERT INTO affiliates (tenant_id, name, code, tg_id, percent, note)
               VALUES (?,?,?,?,?,?)""",
            (tid, name, code, tg_id, percent,
             (payload.get("note") or "").strip()[:200]))
        con.commit()
        return {"ok": True, "id": cur.lastrowid, "code": code}
    except sq.IntegrityError:
        raise HTTPException(status_code=400, detail="این کد قبلاً استفاده شده")
    finally:
        con.close()


@app.put("/api/admin/bot/affiliate/{aid}")
def bot_affiliate_edit(aid: int, payload: dict,
                       x_admin_password: str = Header(...)):
    check_auth(x_admin_password)
    import sqlite3 as sq
    con = sq.connect(str(BOT_DB), timeout=10)
    try:
        fields, params = [], []
        for key in ("name", "note"):
            if key in payload:
                fields.append(f"{key} = ?")
                params.append(str(payload[key]).strip()[:200])
        if "percent" in payload:
            fields.append("percent = ?")
            params.append(max(0.1, min(100.0, float(payload["percent"]))))
        if "tg_id" in payload:
            fields.append("tg_id = ?")
            params.append(int(payload["tg_id"] or 0) or None)
        if "active" in payload:
            fields.append("active = ?")
            params.append(1 if payload["active"] else 0)
        if not fields:
            return {"ok": True}
        params.append(aid)
        con.execute(f"UPDATE affiliates SET {', '.join(fields)} WHERE id = ?", params)
        con.commit()
        return {"ok": True}
    finally:
        con.close()


@app.delete("/api/admin/bot/affiliate/{aid}")
def bot_affiliate_del(aid: int, x_admin_password: str = Header(...)):
    check_auth(x_admin_password)
    import sqlite3 as sq
    con = sq.connect(str(BOT_DB), timeout=10)
    try:
        # کاربران معرفی‌شده حفظ می‌شوند، فقط پیوندشان قطع می‌شود
        con.execute("UPDATE users SET affiliate_id = NULL WHERE affiliate_id = ?", (aid,))
        con.execute("DELETE FROM affiliates WHERE id = ?", (aid,))
        con.commit()
        return {"ok": True}
    finally:
        con.close()


def _affiliate_balance(con, aid):
    """
    مانده‌ی همکار: هر چه درآورده، منهای هر چه گرفته.

    دفترِ پرداخت‌ها حقیقت است، نه ستونِ `status`. چون پرداخت می‌تواند
    جزئی باشد (۶۰ هزار بابتِ ۸۰ هزار بدهی) و با علامت‌زدنِ
    سفارش‌به‌سفارش اصلاً قابل بیان نیست.
    """
    earned = con.execute(
        "SELECT COALESCE(SUM(commission),0) FROM affiliate_commissions "
        "WHERE affiliate_id=? AND status != 'cancelled'", (aid,)).fetchone()[0]
    paid = con.execute(
        "SELECT COALESCE(SUM(amount),0) FROM affiliate_payouts "
        "WHERE affiliate_id=?", (aid,)).fetchone()[0]
    return int(earned or 0) - int(paid or 0)


def _settle_commissions(con, aid):
    """
    وضعیتِ هر پورسانت را از روی دفترِ پرداخت‌ها دوباره بساز.

    چرا دوباره‌سازی و نه علامت‌زدنِ تدریجی: نسخه‌ی قبلی از مبلغِ
    همین پرداخت کم می‌کرد و وقتی به پورسانتی می‌رسید که از باقی‌مانده
    بزرگ‌تر بود، `break` می‌زد و **باقی‌مانده را دور می‌ریخت**. یعنی
    پرداختِ ۶۰ هزار بابتِ پورسانت‌های ۵۰ و ۳۰ هزار، آن ۱۰ هزارِ
    اضافه را هیچ‌جا حساب نمی‌کرد و وضعیت‌ها با واقعیت جور درنمی‌آمد.

    این نسخه از مجموعِ کلِ پرداخت‌ها شروع می‌کند، پس چند بار اجرا
    شدنش هم همان جواب را می‌دهد.

    و `cancelled` دست نمی‌خورد: آن یعنی «این پورسانت اصلاً بدهی
    نیست»، نه «پرداخت نشده».
    """
    paid_total = int(con.execute(
        "SELECT COALESCE(SUM(amount),0) FROM affiliate_payouts "
        "WHERE affiliate_id=?", (aid,)).fetchone()[0] or 0)

    running = 0
    for cid, amt in con.execute(
            "SELECT id, commission FROM affiliate_commissions "
            "WHERE affiliate_id=? AND status != 'cancelled' ORDER BY id",
            (aid,)).fetchall():
        running += int(amt or 0)
        want = "paid" if running <= paid_total else "pending"
        con.execute("UPDATE affiliate_commissions SET status=? "
                    "WHERE id=? AND status != ?", (want, cid, want))


@app.post("/api/admin/bot/affiliate/{aid}/payout")
def bot_affiliate_payout(aid: int, payload: dict,
                         x_admin_password: str = Header(...)):
    """
    ثبت پرداخت به همکار.

    پرداخت نقدی بیرون از ربات انجام می‌شود، پس فقط ثبتش می‌کنیم
    تا مانده درست بماند.
    """
    check_auth(x_admin_password)
    try:
        amount = int((payload or {}).get("amount") or 0)
    except (TypeError, ValueError):
        amount = 0
    if amount <= 0:
        raise HTTPException(status_code=400, detail="مبلغ نامعتبر است")

    import sqlite3 as sq
    con = sq.connect(str(BOT_DB), timeout=10)
    try:
        tid = con.execute("SELECT tenant_id FROM affiliates WHERE id=?",
                          (aid,)).fetchone()
        if not tid:
            raise HTTPException(status_code=404, detail="همکار پیدا نشد")
        con.execute(
            "INSERT INTO affiliate_payouts (tenant_id, affiliate_id, amount, note) "
            "VALUES (?,?,?,?)",
            (tid[0], aid, amount, (payload.get("note") or "").strip()[:200]))
        _settle_commissions(con, aid)
        con.commit()
        return {"ok": True, "balance": _affiliate_balance(con, aid)}
    finally:
        con.close()


# ═══════════════════════════════════════════════════════════
#  پنل همکار فروش
#
#  برگه‌اش: docs/specs/2026-09-17-affiliate-portal.md
#
#  همکار هیچ چیزی را عوض نمی‌کند — نه پرداخت ثبت می‌کند، نه درصد.
#  فقط می‌خواند. و هر عددی که می‌بیند از همان عبارتی می‌آید که پنلِ
#  مالک به کار می‌برد؛ دو نسخه یعنی روزی دو عدد و یک بحث.
# ═══════════════════════════════════════════════════════════

#: نشست‌های همکار — مثل نشست نماینده، در حافظه
_AFF_SESSIONS = {}
AFF_SESSION_HOURS = 12


@app.post("/api/aff/login")
def aff_login(payload: dict, request: Request):
    """ورود همکار با کد و رمز."""
    p = payload or {}
    code = str(p.get("code") or "").strip().upper()[:40]
    pw = str(p.get("password") or "")
    ip = _client_ip(request)

    # همان سدِ حدس‌زدنِ پنل — بدون آن، کد و رمزِ همکار را می‌شود
    # پشت‌سرهم امتحان کرد
    wait = _auth_locked(ip)
    if wait:
        raise HTTPException(
            status_code=429,
            detail=f"تلاش‌های ناموفق زیاد بود. {max(1, wait // 60)} دقیقه‌ی دیگر دوباره امتحان کنید")

    con = _bot_conn()
    if not con:
        raise HTTPException(status_code=503, detail="دیتابیس ربات در دسترس نیست")
    try:
        row = con.execute(
            "SELECT * FROM affiliates WHERE UPPER(code)=?", (code,)).fetchone()
        aff = dict(row) if row else None
    finally:
        con.close()

    # پیامِ یکسان برای «کد نیست» و «رمز غلط».
    # اگر فرق کند، می‌شود با امتحان‌کردن فهمید چه کدهایی وجود دارند.
    bad = HTTPException(status_code=401, detail="کد یا رمز نادرست است")
    if not aff:
        _auth_failed(ip)
        raise bad
    if not aff.get("active"):
        raise HTTPException(status_code=403, detail="دسترسی شما بسته شده است")
    if not aff.get("password"):
        raise HTTPException(
            status_code=409,
            detail="هنوز رمزی برای شما تعریف نشده — با پشتیبانی تماس بگیرید")
    if not _pw_check(pw, aff["password"]):
        _auth_failed(ip)
        raise bad

    _auth_ok(ip)
    tok = secrets.token_urlsafe(32)
    _AFF_SESSIONS[tok] = (int(aff["id"]), _time.time() + AFF_SESSION_HOURS * 3600)
    return {"token": tok, "name": aff.get("name") or "",
            "code": aff.get("code") or "", "percent": float(aff.get("percent") or 0)}


def aff_session(x_aff_token: str = Header(None)):
    """همکارِ نشستِ جاری. هر مسیر `/api/aff/*` از این رد می‌شود."""
    rec = _AFF_SESSIONS.get(str(x_aff_token or ""))
    if not rec or rec[1] < _time.time():
        _AFF_SESSIONS.pop(str(x_aff_token or ""), None)
        raise HTTPException(status_code=401, detail="نشست منقضی شده — دوباره وارد شوید")

    con = _bot_conn()
    try:
        row = con.execute("SELECT * FROM affiliates WHERE id=?",
                          (rec[0],)).fetchone() if con else None
    finally:
        if con:
            con.close()
    if not row:
        _AFF_SESSIONS.pop(str(x_aff_token or ""), None)
        raise HTTPException(status_code=404, detail="این همکار دیگر وجود ندارد")
    aff = dict(row)
    if not aff.get("active"):
        # دسترسی همان لحظه بسته می‌شود، نه سرِ انقضای نشست
        _AFF_SESSIONS.pop(str(x_aff_token or ""), None)
        raise HTTPException(status_code=403, detail="دسترسی شما بسته شده است")
    return aff


@app.post("/api/aff/logout")
def aff_logout(x_aff_token: str = Header(None)):
    _AFF_SESSIONS.pop(str(x_aff_token or ""), None)
    return {"ok": True}


@app.get("/api/aff/summary")
def aff_summary(aff: dict = Depends(aff_session)):
    """
    همه‌ی چیزی که همکار می‌بیند، در یک درخواست.

    مانده از `_affiliate_balance` می‌آید — همان تابعی که پنلِ مالک
    هم صدا می‌زند. اگر این‌جا دوباره حساب می‌شد، روزی دو عدد
    می‌دادند.
    """
    aid = int(aff["id"])
    con = _bot_conn()
    if not con:
        raise HTTPException(status_code=503, detail="دیتابیس ربات در دسترس نیست")
    try:
        earned = con.execute(
            "SELECT COALESCE(SUM(commission),0) FROM affiliate_commissions "
            "WHERE affiliate_id=? AND status != 'cancelled'", (aid,)).fetchone()[0]
        paid = con.execute(
            "SELECT COALESCE(SUM(amount),0) FROM affiliate_payouts "
            "WHERE affiliate_id=?", (aid,)).fetchone()[0]
        balance = _affiliate_balance(con, aid)

        # مشتری‌هایی که این همکار آورده — با مجموعِ خریدشان
        users = [dict(r) for r in con.execute("""
            SELECT u.id, u.first_name, u.username, u.tg_id, u.created_at,
                   (SELECT COUNT(*) FROM orders o
                     WHERE o.user_id = u.id AND o.status='approved') AS orders,
                   (SELECT COALESCE(SUM(o.amount),0) FROM orders o
                     WHERE o.user_id = u.id AND o.status='approved') AS spent
              FROM users u WHERE u.affiliate_id = ?
             ORDER BY u.id DESC LIMIT 200""", (aid,))]

        comms = [dict(r) for r in con.execute("""
            SELECT c.id, c.order_id, c.order_amount, c.percent, c.commission,
                   c.status, c.created_at, u.first_name, u.username
              FROM affiliate_commissions c
              LEFT JOIN users u ON u.id = c.user_id
             WHERE c.affiliate_id = ? AND c.status != 'cancelled'
             ORDER BY c.id DESC LIMIT 200""", (aid,))]

        pays = [dict(r) for r in con.execute(
            "SELECT id, amount, note, paid_at FROM affiliate_payouts "
            "WHERE affiliate_id=? ORDER BY id DESC LIMIT 100", (aid,))]
    except Exception as e:
        log.exception("خلاصه‌ی همکار خوانده نشد")
        raise HTTPException(status_code=502, detail=f"خوانده نشد: {str(e)[:120]}")
    finally:
        con.close()

    return {
        "name": aff.get("name") or "", "code": aff.get("code") or "",
        "percent": float(aff.get("percent") or 0),
        "earned": int(earned or 0), "paid": int(paid or 0), "balance": int(balance),
        "users": users, "commissions": comms, "payouts": pays,
    }


@app.post("/api/admin/bot/affiliate/{aid}/password")
def bot_affiliate_password(aid: int, payload: dict,
                           x_admin_password: str = Header(...)):
    """
    رمزِ ورودِ همکار را مالک تعیین می‌کند.

    خالی‌فرستادن یعنی «دسترسی را ببند» — رمز پاک می‌شود و همکار
    دیگر وارد نمی‌شود. نشستِ بازش هم همان لحظه باطل می‌شود، وگرنه
    تا دوازده ساعت هنوز می‌دید.
    """
    check_auth(x_admin_password)
    pw = str((payload or {}).get("password") or "")
    if pw and len(pw) < 6:
        raise HTTPException(status_code=400, detail="رمز باید حداقل ۶ کاراکتر باشد")

    con = _bot_rw()
    try:
        row = con.execute("SELECT id FROM affiliates WHERE id=?", (aid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="همکار پیدا نشد")
        con.execute("UPDATE affiliates SET password=? WHERE id=?",
                    (_pw_hash(pw) if pw else None, aid))
        con.commit()
    finally:
        con.close()

    for tok, rec in list(_AFF_SESSIONS.items()):
        if rec[0] == aid:
            _AFF_SESSIONS.pop(tok, None)
    return {"ok": True, "hasPassword": bool(pw)}


@app.post("/api/admin/bot/xui-trace")
def bot_xui_trace(x_admin_password: str = Header(...)):
    """
    تشخیص کامل ساخت کانفیگ — همان چیزی که xui-trace.py می‌کند،
    ولی از داخل پنل تا نیازی به SSH نباشد.

    هر مرحله جدا گزارش می‌شود، و اگر جایی شکست بخورد پیام خام
    پنل ۳x-ui بدون تفسیر نمایش داده می‌شود — چون همان پیام است
    که می‌گوید چه چیزی کم است.
    """
    check_auth(x_admin_password)
    steps = []

    def step(title, ok, detail="", hint=""):
        steps.append({"title": title, "ok": ok, "detail": detail, "hint": hint})
        return ok

    con = _bot_conn()
    if not con:
        step("خواندن تنظیمات", False, "دیتابیس ربات در دسترس نیست")
        return {"ok": False, "steps": steps}

    try:
        # همان قاعده‌ی بالا: صفحه‌ی عیب‌یابی هم باید تنظیمات مالک را
        # بخواند، وگرنه «پنل تنظیم نشده» گزارش می‌کند در حالی که شده.
        r = con.execute(
            "SELECT panel_url, panel_user, panel_pass, panel_token, "
            "default_inbound FROM tenants WHERE parent_id IS NULL "
            "ORDER BY id LIMIT 1").fetchone()
        t = dict(r) if r else {}
    finally:
        con.close()

    if not t.get("panel_url"):
        step("آدرس پنل", False, "تنظیم نشده",
             "بخش اتصال و تنظیمات را پر کنید")
        return {"ok": False, "steps": steps}

    step("آدرس پنل", True, t["panel_url"])
    step("روش احراز هویت", True,
         "توکن API" if t.get("panel_token") else f"نام کاربری ({t.get('panel_user')})")

    # app.py ماژول sys را با نام _sys وارد می‌کند؛ «sys» خالی این‌جا
    # یعنی NameError درست وقتی ادمین دکمه‌ی ردیابی را می‌زند.
    import sys as _sys
    _sys.path.insert(0, str(_bot_dir()))
    try:
        from xui import XUI, XUIError
    except Exception as e:
        step("بارگذاری کلاینت", False, str(e)[:120])
        return {"ok": False, "steps": steps}

    client = XUI(t["panel_url"], t.get("panel_user"),
                 t.get("panel_pass"), t.get("panel_token"))

    try:
        client.login()
        step("ورود به پنل", True, "موفق")
    except Exception as e:
        step("ورود به پنل", False, str(e)[:160],
             "رمز یا توکن را بررسی کنید")
        return {"ok": False, "steps": steps}

    try:
        inbounds = client.inbounds()
        step("خواندن inboundها", True,
             " · ".join(f"#{i.get('id')} {i.get('remark','')}"
                        for i in inbounds[:5]))
    except Exception as e:
        step("خواندن inboundها", False, str(e)[:160])
        return {"ok": False, "steps": steps}

    if not inbounds:
        step("inbound موجود", False, "هیچ inboundی نیست",
             "در ۳x-ui حداقل یک inbound بسازید")
        return {"ok": False, "steps": steps}

    try:
        routes = client.discover()
    except Exception:
        routes = {}

    if routes:
        client_routes = [p for p in routes if "client" in p.lower()]
        step("مسیرهای API", True,
             f"{len(routes)} مسیر · " +
             (", ".join(sorted(client_routes)[:3]) if client_routes
              else "بدون مسیر کلاینت"))
    else:
        step("مسیرهای API", True, "پنل مشخصات OpenAPI ندارد",
             "مسیرها با آزمون‌وخطا پیدا می‌شوند")

    schema = None
    try:
        schema = client.request_schema("/panel/api/clients", "post")
    except Exception:
        pass

    if schema:
        props = list((schema.get("properties") or {}).keys())
        req = schema.get("required") or []
        step("فیلدهایی که پنل می‌خواهد", True,
             f"{', '.join(props[:10])}" +
             (f" · اجباری: {', '.join(req)}" if req else ""))
    else:
        step("فیلدهایی که پنل می‌خواهد", True,
             "اعلام نشده — شکل‌های شناخته‌شده امتحان می‌شوند")

    target = t.get("default_inbound") or inbounds[0].get("id")
    email = f"nexora_test_{secrets.token_hex(3)}"

    created = None
    try:
        created = client.add_client(int(target), email, gb=1, days=1)
        step("ساخت کانفیگ آزمایشی", True, f"{email} روی inbound #{target}")
    except Exception as e:
        step("ساخت کانفیگ آزمایشی", False, str(e)[:300],
             "پیام بالا مستقیم از پنل ۳x-ui است. اگر نام فیلدی را "
             "می‌گوید، همان فیلد در این نسخه جای دیگری است.")
        return {"ok": False, "steps": steps}

    try:
        found = client.find_client(int(target), email=email)
        step("بازخوانی از پنل", bool(found),
             "پیدا شد" if found else "ساخته شد ولی پیدا نشد",
             "" if found else "احتمالاً به inbound وصل نشده — "
             "کلاینت هست ولی هیچ‌جا فعال نیست")
    except Exception as e:
        step("بازخوانی از پنل", False, str(e)[:160])

    try:
        if created and created.get("id"):
            client.delete_client(int(target), created["id"], email=email)
            step("پاکسازی", True, "کانفیگ آزمایشی حذف شد")
    except Exception as e:
        step("پاکسازی", False, f"{str(e)[:120]} — {email} را دستی حذف کنید")

    return {"ok": all(s["ok"] for s in steps), "steps": steps}


@app.get("/api/admin/bot/status")
def bot_status(x_admin_password: str = Header(...)):
    """وضعیت کلی ربات — نصب شده؟ فعال است؟ چند کاربر؟"""
    check_auth(x_admin_password)

    module_exists = (_bot_dir() / "run.py").exists()
    okdb, err = _ensure_bot_db()
    con = _bot_conn()
    if not con:
        return {
            "installed": module_exists,
            "dbReady": False,
            "running": _svc_active(),
            "message": err or ("ربات هنوز راه‌اندازی نشده است" if module_exists
                               else "ماژول ربات روی سرور نیست — nexora update را اجرا کنید"),
            "botDir": str(_bot_dir()),
            "dbPath": str(BOT_DB),
        }

    try:
        stats = {}
        for key, sql in [
            ("users", "SELECT COUNT(*) c FROM users"),
            ("plans", "SELECT COUNT(*) c FROM plans WHERE is_active=1"),
            ("pendingOrders", "SELECT COUNT(*) c FROM orders WHERE status IN ('awaiting','review')"),
            ("activeSubs", "SELECT COUNT(*) c FROM subscriptions WHERE is_active=1"),
            ("openTickets", "SELECT COUNT(*) c FROM tickets WHERE status='open'"),
            ("tenants", "SELECT COUNT(*) c FROM tenants"),
        ]:
            try:
                stats[key] = con.execute(sql).fetchone()["c"]
            except Exception:
                stats[key] = 0

        # «فروش» و «درآمد» یکی نیستند: سفارشی که از کیف پول پرداخت
        # شده فروش هست ولی پول تازه‌ای با آن نرسیده. این عدد بی‌برچسب
        # بالای صفحه می‌نشست و خواننده آن را درآمد می‌خواند.
        try:
            sales = con.execute(
                "SELECT COALESCE(SUM(amount),0) s FROM orders "
                "WHERE status='approved'").fetchone()["s"]
        except Exception:
            sales = 0

        return {
            "installed": True,
            "dbReady": True,
            "running": _svc_active(),
            "stats": stats,
            "totalSales": sales,
            "totalReceived": _bot_money_in(),
            # نام قدیمی، تا اگر جایی هنوز می‌خواندش خالی نماند
            "totalRevenue": sales,
        }
    finally:
        con.close()


@app.get("/api/admin/bot/orders")
def bot_orders(status: str = "awaiting", limit: int = 50,
               x_admin_password: str = Header(...)):
    """صف سفارش‌ها — برای تایید رسید از داخل پنل."""
    check_auth(x_admin_password)
    con = _bot_conn()
    if not con:
        return {"orders": [], "dbReady": False}

    try:
        allowed = {"awaiting", "review", "approved", "rejected", "all"}
        if status not in allowed:
            status = "awaiting"

        if status == "all":
            rows = con.execute(
                "SELECT o.*, u.first_name, u.username, u.tg_id FROM orders o "
                "LEFT JOIN users u ON u.id=o.user_id "
                "ORDER BY o.created_at DESC LIMIT ?", (min(limit, 200),)
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT o.*, u.first_name, u.username, u.tg_id FROM orders o "
                "LEFT JOIN users u ON u.id=o.user_id "
                "WHERE o.status=? ORDER BY o.created_at DESC LIMIT ?",
                (status, min(limit, 200))
            ).fetchall()

        return {"orders": [dict(r) for r in rows], "dbReady": True}
    except Exception as e:
        return {"orders": [], "dbReady": True, "error": str(e)[:200]}
    finally:
        con.close()


#: فیلترهای بخش کاربران — شرط SQL هرکدام.
#
# فهرست ساده‌ی «۵۰ کاربر آخر» وقتی چند صد کاربر دارید بی‌فایده است؛
# ادمین معمولاً دنبال یک دسته‌ی مشخص می‌گردد: چه کسی خرید کرده، چه
# کسی شماره داده، چه کسی اشتراکش تمام شده.
_USER_FILTERS = {
    "all": "1=1",
    "active": "EXISTS (SELECT 1 FROM subscriptions s WHERE s.user_id=u.id "
              "AND s.is_active=1 AND (s.expires_at IS NULL "
              "OR s.expires_at > CURRENT_TIMESTAMP))",
    "expired": "EXISTS (SELECT 1 FROM subscriptions s WHERE s.user_id=u.id) "
               "AND NOT EXISTS (SELECT 1 FROM subscriptions s WHERE s.user_id=u.id "
               "AND s.is_active=1 AND (s.expires_at IS NULL "
               "OR s.expires_at > CURRENT_TIMESTAMP))",
    "never": "NOT EXISTS (SELECT 1 FROM subscriptions s WHERE s.user_id=u.id)",
    "buyers": "EXISTS (SELECT 1 FROM orders o WHERE o.user_id=u.id "
              "AND o.status='approved')",
    "blocked": "u.is_blocked=1",
    "withPhone": "u.phone IS NOT NULL AND u.phone<>''",
    "noPhone": "(u.phone IS NULL OR u.phone='')",
    "withBalance": "COALESCE(u.balance,0) > 0",
    "withCoins": "COALESCE(u.coins,0) > 0",
    "referred": "u.referred_by IS NOT NULL",
}

_USER_SORTS = {
    "new": "u.created_at DESC",
    "old": "u.created_at ASC",
    "spent": "spent DESC",
    "balance": "COALESCE(u.balance,0) DESC",
    "coins": "COALESCE(u.coins,0) DESC",
    "lastSeen": "COALESCE(u.last_seen, u.created_at) DESC",
}


@app.get("/api/admin/bot/users")
def bot_users(q: str = "", limit: int = 50, offset: int = 0,
              filter: str = "all", sort: str = "new", counts: int = 1,
              x_admin_password: str = Header(...)):
    """
    کاربران ربات با فیلتر، مرتب‌سازی و آمار هر کاربر.

    برای هر کاربر تعداد سفارش موفق، مجموع خرید و وضعیت اشتراک هم
    برمی‌گردد — بدون این‌ها ادمین باید روی تک‌تک کاربران کلیک می‌کرد
    تا بفهمد کدام مشتری واقعی است.
    """
    check_auth(x_admin_password)
    con = _bot_conn()
    if not con:
        return {"users": [], "dbReady": False}

    where = [_USER_FILTERS.get(filter, "1=1")]
    params = []
    if q:
        like = f"%{q}%"
        where.append("(u.first_name LIKE ? OR u.username LIKE ? "
                     "OR CAST(u.tg_id AS TEXT) LIKE ? OR u.phone LIKE ?)")
        params += [like, like, like, like]

    where_sql = " AND ".join(f"({w})" for w in where)
    order_sql = _USER_SORTS.get(sort, _USER_SORTS["new"])
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    base = f"""
        SELECT u.*,
          (SELECT COUNT(*) FROM orders o
            WHERE o.user_id=u.id AND o.status='approved') AS ordersCount,
          (SELECT COALESCE(SUM(o.amount),0) FROM orders o
            WHERE o.user_id=u.id AND o.status='approved') AS spent,
          (SELECT COUNT(*) FROM subscriptions s WHERE s.user_id=u.id) AS subsCount,
          (SELECT COUNT(*) FROM subscriptions s WHERE s.user_id=u.id
            AND s.is_active=1 AND (s.expires_at IS NULL
            OR s.expires_at > CURRENT_TIMESTAMP)) AS activeSubs
        FROM users u
        WHERE {where_sql}
    """

    try:
        total = con.execute(
            f"SELECT COUNT(*) AS n FROM users u WHERE {where_sql}",
            params).fetchone()["n"]
        rows = con.execute(f"{base} ORDER BY {order_sql} LIMIT ? OFFSET ?",
                           params + [limit, offset]).fetchall()

        # شمارش هر فیلتر، تا ادمین بدون کلیک‌کردن بداند هرکدام چندتاست.
        #
        # یک اسکن، نه یازده‌تا — ولی شرط‌ها از همان `_USER_FILTERS`
        # ساخته می‌شوند، نه یک نسخه‌ی دوم. اگر این‌جا دستی نوشته
        # می‌شد، همان باگِ همیشگیِ این مخزن بود: یک قاعده، دو جا،
        # اصلاح در یکی.
        #
        # اندازه‌گیری روی ۲۵ هزار کاربر: ۶۱ میلی‌ثانیه → ۳۵.
        n_counts = {}
        if counts:
            try:
                sel = ", ".join(
                    f'SUM(CASE WHEN ({cond}) THEN 1 ELSE 0 END) AS "{key}"'
                    for key, cond in _USER_FILTERS.items())
                row = con.execute(f"SELECT {sel} FROM users u").fetchone()
                n_counts = {k: int(row[k] or 0) for k in _USER_FILTERS}
            except Exception:
                log.debug("شمارش فیلترها ناموفق", exc_info=True)
                n_counts = {}

        out = {"users": [dict(r) for r in rows], "dbReady": True,
               "total": total, "offset": offset, "limit": limit}
        # وقتی خواسته نشده، کلید اصلاً نمی‌آید — فرانت عددهای قبلی
        # را نگه می‌دارد. `{}` می‌فرستادیم، همه‌ی چیپ‌ها صفر می‌شدند.
        if counts:
            out["counts"] = n_counts
        return out
    except Exception as e:
        return {"users": [], "dbReady": True, "error": str(e)[:200]}
    finally:
        con.close()


@app.get("/api/admin/bot/users/report")
def bot_users_report(days: int = 30, x_admin_password: str = Header(...)):
    """
    گزارش دوره‌ای کاربران ربات — معادل صورتحساب حسابداری، ولی برای
    سمت فروش.

    حسابداری می‌گوید از هر واسطه چقدر طلب دارید. این می‌گوید در این
    دوره چند نفر آمدند، چند نفر خریدند، چقدر فروش رفت و چه کسانی
    بیشترین سهم را داشتند — چیزی که تا حالا فقط با نگاه‌کردن به
    فهرست کاربران قابل حدس‌زدن بود.
    """
    check_auth(x_admin_password)
    con = _bot_conn()
    if not con:
        return {"ready": False, "error": "دیتابیس ربات در دسترس نیست"}

    days = max(1, min(int(days or 30), 365))
    since = f"-{days} days"

    def one(sql, args=()):
        try:
            r = con.execute(sql, args).fetchone()
            return dict(r) if r else {}
        except Exception:
            return {}

    def many(sql, args=()):
        try:
            return [dict(r) for r in con.execute(sql, args)]
        except Exception:
            return []

    try:
        totals = one("""
            SELECT
              (SELECT COUNT(*) FROM users) AS users,
              (SELECT COUNT(*) FROM users
                WHERE created_at >= datetime('now', ?)) AS newUsers,
              (SELECT COUNT(*) FROM users WHERE is_blocked=1) AS blocked,
              (SELECT COUNT(*) FROM users WHERE phone IS NOT NULL
                AND phone != '') AS withPhone
        """, (since,))

        # تست رایگان سفارش هست ولی خرید نیست — بدون این، هم تعداد
        # باد می‌کند و هم «میانگین سفارش» با سفارش‌های صفرتومانی
        # پایین کشیده می‌شود.
        orders = one(f"""
            SELECT COUNT(*) AS n, COALESCE(SUM(o.amount),0) AS sum
            FROM orders o {SQL_PLAN_JOIN}
            WHERE {SQL_REAL_BUY} AND o.created_at >= datetime('now', ?)
        """, (since,))

        rejected = one("""
            SELECT COUNT(*) AS n FROM orders
            WHERE status='rejected' AND created_at >= datetime('now', ?)
        """, (since,))

        pending = one("SELECT COUNT(*) AS n FROM orders WHERE status='awaiting'")

        subs = one("""
            SELECT
              (SELECT COUNT(*) FROM subscriptions) AS total,
              (SELECT COUNT(*) FROM subscriptions WHERE is_active=1
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP))
                AS active,
              (SELECT COUNT(*) FROM subscriptions
                WHERE expires_at IS NOT NULL
                AND expires_at <= datetime('now', '+3 days')
                AND expires_at > CURRENT_TIMESTAMP) AS expiringSoon
        """)

        # خریدارها — همان چیزی که تصمیم فروش رویش گرفته می‌شود
        buyers = many(f"""
            SELECT u.tg_id, u.first_name, u.username, u.phone,
                   COUNT(o.id) AS orders,
                   COALESCE(SUM(o.amount),0) AS spent,
                   MAX(o.created_at) AS lastBuy
            FROM users u JOIN orders o ON o.user_id = u.id {SQL_PLAN_JOIN}
            WHERE {SQL_REAL_BUY} AND o.created_at >= datetime('now', ?)
            GROUP BY u.id
            ORDER BY spent DESC
            LIMIT 20
        """, (since,))

        # فروش روزانه، برای دیدن روند
        daily = many(f"""
            SELECT date(o.created_at) AS day, COUNT(*) AS n,
                   COALESCE(SUM(o.amount),0) AS sum
            FROM orders o {SQL_PLAN_JOIN}
            WHERE {SQL_REAL_BUY} AND o.created_at >= datetime('now', ?)
            GROUP BY date(o.created_at)
            ORDER BY day
        """, (since,))

        n_orders = int(orders.get("n") or 0)
        n_new = int(totals.get("newUsers") or 0)
        n_buyers = len(many(f"""
            SELECT DISTINCT o.user_id FROM orders o {SQL_PLAN_JOIN}
            WHERE {SQL_REAL_BUY} AND o.created_at >= datetime('now', ?)
        """, (since,)))

        return {
            "ready": True,
            "days": days,
            "users": totals,
            "orders": {
                "approved": n_orders,
                "rejected": int(rejected.get("n") or 0),
                "pending": int(pending.get("n") or 0),
                "revenue": int(orders.get("sum") or 0),
                "avg": int((orders.get("sum") or 0) / n_orders) if n_orders else 0,
            },
            "subs": subs,
            "buyers": buyers,
            "buyerCount": n_buyers,
            # نرخ تبدیل: از کسانی که این دوره آمدند، چند درصد خریدند
            "conversion": (round(n_buyers * 100.0 / n_new, 1)
                           if n_new else None),
            "daily": daily,
        }
    finally:
        con.close()


@app.get("/api/admin/bot/users/export")
def bot_users_export(q: str = "", filter: str = "all", sort: str = "new",
                     x_admin_password: str = Header(...)):
    """
    خروجی CSV کاربران ربات — با همان فیلتری که در صفحه اعمال شده.

    شماره تماس هم می‌آید، چون همان چیزی است که برای پیگیری فروش
    بیرون از تلگرام لازم می‌شود.
    """
    check_auth(x_admin_password)

    data = bot_users(q=q, filter=filter, sort=sort, limit=100000, offset=0,
                     x_admin_password=x_admin_password)
    if not data.get("dbReady"):
        raise HTTPException(status_code=400, detail="دیتابیس ربات در دسترس نیست")

    import csv
    import io as _io
    buf = _io.StringIO()
    buf.write("﻿")   # BOM تا اکسل فارسی را درست بخواند
    w = csv.writer(buf)
    w.writerow(["شناسه تلگرام", "نام", "یوزرنیم", "شماره تماس",
                "سفارش موفق", "مجموع خرید (تومان)", "اشتراک", "اشتراک فعال",
                "سکه", "کیف پول", "کد دعوت", "مسدود", "تاریخ عضویت"])

    for u in data.get("users") or []:
        w.writerow([
            u.get("tg_id", ""), u.get("first_name") or "",
            u.get("username") or "", u.get("phone") or "",
            u.get("ordersCount", 0), u.get("spent", 0),
            u.get("subsCount", 0), u.get("activeSubs", 0),
            u.get("coins", 0), u.get("balance", 0),
            u.get("ref_code") or "",
            "بله" if u.get("is_blocked") else "خیر",
            str(u.get("created_at") or "")[:19],
        ])

    from fastapi.responses import Response as _Resp
    return _Resp(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition":
                 'attachment; filename="nexora-bot-users.csv"'})


def _sqlite_copy(src, dest):
    """
    کپی سازگار از یک دیتابیس SQLite.

    کپی ساده‌ی فایل برای دیتابیسی که WAL دارد کافی نیست: هر چیزی که
    هنوز به فایل اصلی منتقل نشده در «‎-wal» نشسته و در کپی نمی‌آید.
    یعنی نسخه‌ای که «قبل از بازگردانی» گرفته می‌شد می‌توانست ساعت‌ها
    سفارش و پرداخت کم داشته باشد — دقیقاً همان چیزی که قرار بود از
    آن محافظت کند.

    بدتر از کم‌داشتن: اگر همان فایلِ تنها بعداً کنار یک ‎-wal دیگر
    گذاشته شود، SQLite ممکن است آن WAL را رویش اعمال کند.

    backup() خودِ SQLite همه‌ی این‌ها را یک‌جا و سازگار می‌نویسد.
    """
    import sqlite3
    s = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=15)
    try:
        d = sqlite3.connect(str(dest), timeout=15)
        try:
            s.backup(d)
        finally:
            d.close()
    finally:
        s.close()


def _bot_rw():
    """اتصال نوشتنی به دیتابیس ربات (برای تنظیمات از پنل)."""
    import sqlite3
    BOT_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(BOT_DB), timeout=10)
    con.row_factory = sqlite3.Row
    return con


#: لوگوی برند — مالک و هر نماینده یکی دارد.
#
#  چرا روی دیسک و نه در دیتابیس: این فایل را مرورگرِ مشتری مستقیم
#  می‌خواهد (مینی‌اپ و صفحه‌ی اشتراک)، و ریختنِ چند صد کیلوبایت باینری
#  در هر `SELECT * FROM tenants` یعنی کند‌کردنِ هر چیزی که مستاجر
#  می‌خواند.
LOGO_DIR = Path(os.getenv("LOGO_DIR", str(CONFIG_PATH.parent / "logos")))

#: سقفِ حجم. بدون Pillow نمی‌شود تصویر را کوچک کرد، پس همین سقف تنها
#  چیزی است که جلوی یک فایلِ ۲۰ مگابایتی را می‌گیرد.
LOGO_MAX_BYTES = 512 * 1024

#: رسید از دوربینِ گوشی می‌آید و بزرگ‌تر است؛ ولی بی‌سقف هم نه.
RECEIPT_MAX_BYTES = 3 * 1024 * 1024

#: فرمت‌های مجاز، با **بایت‌های اولِ فایل** — نه پسوند و نه
#  `Content-Type`، که هر دو را فرستنده می‌نویسد.
#
#  SVG عمداً نیست: می‌تواند `<script>` داشته باشد و این فایل از
#  دامنه‌ی خودِ ما سرو می‌شود، یعنی XSS روی پنل.
def _logo_kind(blob: bytes):
    """پسوند و نوعِ محتوا، یا (None, None) اگر تصویرِ مجاز نباشد."""
    if blob[:8] == b"\x89PNG\r\n\x1a\n":
        return "png", "image/png"
    if blob[:3] == b"\xff\xd8\xff":
        return "jpg", "image/jpeg"
    if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        return "webp", "image/webp"
    return None, None


def _logo_path(tid: int):
    """فایلِ لوگوی این مستاجر، اگر باشد."""
    for ext in ("png", "jpg", "webp"):
        p = LOGO_DIR / f"{int(tid)}.{ext}"
        if p.exists():
            return p
    return None


def _logo_url(tid) -> str:
    """نشانیِ عمومیِ لوگو، یا رشته‌ی خالی. رابط از همین تصمیم می‌گیرد."""
    try:
        return f"/api/public/logo/{int(tid)}" if _logo_path(tid) else ""
    except (TypeError, ValueError):
        return ""


def _logo_save(tid: int, payload: dict):
    """
    ذخیره‌ی لوگو از بدنه‌ی JSON با base64.

    چرا base64 و نه multipart: `python-multipart` نصب نیست و افزودنِ
    وابستگی به سروری که با `nexora-cli` به‌روز می‌شود ریسکِ بی‌دلیل
    دارد. برای نیم‌مگابایت، base64 کاملاً بس است.
    """
    import base64
    raw = str((payload or {}).get("data") or "")
    if "," in raw[:80] and raw.lstrip().startswith("data:"):
        raw = raw.split(",", 1)[1]          # data:image/png;base64,....
    raw = raw.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="فایلی فرستاده نشد")

    # سقف را *قبل* از دیکد بسنج: رشته‌ی base64 حدود ۴/۳ برابرِ خودِ
    # فایل است، پس بدونِ این شرط یک رشته‌ی چند مگابایتی دیکد می‌شود و
    # تازه بعدش رد می‌شود.
    if len(raw) > (LOGO_MAX_BYTES * 4) // 3 + 1024:
        raise HTTPException(status_code=413,
                            detail="حجم فایل بیشتر از ۵۱۲ کیلوبایت است")
    try:
        blob = base64.b64decode(raw, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="فایل خوانده نشد")

    if len(blob) > LOGO_MAX_BYTES:
        raise HTTPException(status_code=413,
                            detail="حجم فایل بیشتر از ۵۱۲ کیلوبایت است")

    ext, _ctype = _logo_kind(blob)
    if not ext:
        raise HTTPException(status_code=400,
                            detail="فقط PNG، JPEG یا WebP — و فایل باید سالم باشد")

    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    # پسوندِ قبلی ممکن است فرق کند، پس همه را پاک کن وگرنه دو فایل
    # می‌مانند و `_logo_path` قدیمی را برمی‌دارد
    _logo_clear(tid)
    (LOGO_DIR / f"{int(tid)}.{ext}").write_bytes(blob)
    return {"ok": True, "url": _logo_url(tid), "bytes": len(blob)}


def _logo_clear(tid: int):
    for ext in ("png", "jpg", "webp"):
        p = LOGO_DIR / f"{int(tid)}.{ext}"
        if p.exists():
            try:
                p.unlink()
            except OSError:
                log.debug("پاک‌کردن لوگو ناموفق", exc_info=True)


def _root_tenant_row():
    """
    مستاجرِ ریشه — همان مالک.

    **هیچ‌وقت `LIMIT 1` بدون شرط.** اگر ردیفِ مالک یک‌بار پاک و
    دوباره ساخته شود (نصبِ دوباره)، شناسه‌اش از نماینده بزرگ‌تر
    می‌شود و بی‌صدا به ردیفِ اشتباه می‌رسیم. قاعده‌ی مخزن است و تستِ
    درز اجرایش می‌کند.
    """
    con = _bot_conn()
    if not con:
        raise HTTPException(status_code=503, detail="دیتابیس ربات در دسترس نیست")
    try:
        r = con.execute(
            "SELECT * FROM tenants WHERE parent_id IS NULL "
            "ORDER BY id LIMIT 1").fetchone()
    finally:
        con.close()
    if not r:
        raise HTTPException(status_code=404, detail="مستاجر ریشه پیدا نشد")
    return dict(r)


def _bot_db_rw(t):
    """
    `TenantDB` نوشتنی برای این مستاجر.

    `_bot_conn` فقط‌خواندنی است و صندوق پیام باید بنویسد. از همان
    کلاسِ ربات استفاده می‌کنیم، نه SQL دستی — وگرنه قاعده‌ی
    خوانده‌نشده دو جا نوشته می‌شود و روزی از هم دور می‌افتند.
    """
    h = _bot_handlers()
    return h.DB.TenantDB(t["id"])


@app.get("/api/admin/bot/inbox")
def admin_inbox(user_id: int = None, x_admin_password: str = Header(...)):
    """
    گفتگوها برای مالک — فهرست، یا یک گفتگوی مشخص.
    """
    check_auth(x_admin_password)
    t = _root_tenant_row()
    try:
        db = _bot_db_rw(t)
        if user_id:
            rows = db.chat_list(int(user_id))
            return {"messages": [{
                "id": r["id"], "from": r["sender"], "body": r["body"],
                "photo": _row_get(r, "photo") or "",
                "orderId": r["order_id"], "at": r["created_at"],
                "read": bool(r["read_at"]),
            } for r in rows]}
        threads = db.chat_threads()
        return {"threads": [{
            "userId": r["user_id"], "tgId": r["tg_id"],
            "name": r["first_name"] or "", "username": r["username"] or "",
            "avatar": _avatar_url(t["id"], r["user_id"]),
            "unread": int(r["unread"] or 0),
            # پیامی که فقط عکس است متنِ خالی دارد؛ بدون این، ردیفِ
            # گفتگو در فهرست خالی می‌ماند و به نظر می‌رسد چیزی نیامده
            "lastBody": ((r["last_body"] or "")[:120]
                         or ("📷 عکس" if _row_get(r, "last_photo") else "")),
            "lastAt": r["last_at"] or "",
        } for r in threads],
            "unread": db.chat_unread_for_admin()}
    except Exception as e:
        log.exception("خواندن صندوق پنل ناموفق")
        raise HTTPException(status_code=503, detail=f"صندوق خوانده نشد: {str(e)[:120]}")


@app.post("/api/admin/bot/inbox/send")
def admin_inbox_send(payload: dict, x_admin_password: str = Header(...)):
    """پاسخ مالک به یک مشتری — هم در صندوق، هم در خودِ ربات."""
    check_auth(x_admin_password)
    p = payload or {}
    try:
        uid = int(p.get("userId"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="مشتری مشخص نشده")
    body = str(p.get("body") or "").strip()
    raw = p.get("photo")
    if not body and not raw:
        raise HTTPException(status_code=400, detail="پیام خالی است")

    t = _root_tenant_row()
    # عکس *قبل* از ثبتِ پیام ذخیره می‌شود: اگر فایل ننشیند، پیامی
    # هم ثبت نشده. برعکسش یعنی ردیفی در گفتگو که به عکسی اشاره
    # می‌کند که وجود ندارد — و آن، قابِ شکسته‌ی همیشگی است.
    photo = _chat_photo_save(t["id"], uid, raw) if raw else None
    try:
        db = _bot_db_rw(t)
        db.chat_add(uid, "admin", body[:2000], photo=photo)
        db.chat_mark_read(uid, "admin")
        u = db.get_user_by_id(uid)
    except Exception as e:
        log.exception("ثبت پاسخ ناموفق")
        raise HTTPException(status_code=502, detail=f"فرستاده نشد: {str(e)[:120]}")

    # و در خودِ تلگرام هم برسد: مشتری ممکن است مینی‌اپ را باز نکند.
    if u:
        try:
            h, ctx = _mini_ctx(t)
            cap = f"💬 <b>پاسخ پشتیبانی</b>\n\n{h.esc(body[:900])}" if body \
                else "💬 <b>پاسخ پشتیبانی</b>"
            blob = _chat_photo_bytes(photo) if photo else None
            if blob:
                ctx.bot.send_photo_bytes(u["tg_id"], blob, filename="photo.jpg",
                                         caption=cap)
            else:
                ctx.bot.send(u["tg_id"], cap)
        except Exception:
            log.debug("ارسال پاسخ در تلگرام ناموفق", exc_info=True)

    return {"ok": True, "photo": photo or ""}


@app.get("/api/admin/bot/alerts")
def admin_alerts(x_admin_password: str = Header(...)):
    """
    چیزهایی که همین حالا کارِ مالک را می‌خواهند — با نام و ساعت.

    چرا فقط شمار کافی نبود: «۲ رسید» می‌گفت چند تا، ولی نمی‌گفت
    *کی* فرستاده و *چقدر* منتظر مانده. مالک باید صفحه‌ی سفارش‌ها را
    باز می‌کرد تا بفهمد کدامش دو ساعت است که معطل است. و همان دو
    ساعت، همان چیزی است که مشتری از آن ناراضی می‌شود.

    ترتیب از قدیمی‌ترین است، نه تازه‌ترین: چیزی که بیشتر منتظر
    مانده بالاتر می‌آید، چون همان است که دارد دیر می‌شود.

    و فیلترِ مستاجر: تا امروز نبود، پس رسیدِ مشتریِ *نماینده* هم به
    مالک هشدار می‌داد — کاری که اصلاً مالِ او نیست و نماینده خودش
    باید جوابش را بدهد.
    """
    check_auth(x_admin_password)
    con = _bot_conn()
    empty = {"receipts": 0, "messages": 0, "items": [], "oldestMin": 0,
             "ready": False}
    if not con:
        return empty
    try:
        root = _root_tenant_row()
        tid = root["id"] if root else None
        if tid is None:
            return empty

        # «چند دقیقه منتظر» را خودِ اسکیوال حساب کند — تبدیلِ رشته‌ی
        # زمان در پایتون یعنی یک جای دیگر که منطقه‌ی زمانی را اشتباه
        # بفهمد
        rc = con.execute(
            "SELECT o.id, o.amount, o.created_at, o.receipt_type, "
            "       u.id uid, u.first_name, u.username, u.tg_id, "
            "       p.name plan, "
            "       CAST((julianday('now') - julianday(o.created_at)) * 1440 AS INTEGER) mins "
            "  FROM orders o "
            "  JOIN users u ON u.id = o.user_id "
            "  LEFT JOIN plans p ON p.id = o.plan_id "
            " WHERE o.tenant_id = ? AND o.status = 'awaiting' "
            " ORDER BY o.created_at ASC LIMIT 30", (tid,)).fetchall()

        ms = con.execute(
            "SELECT m.user_id uid, u.first_name, u.username, u.tg_id, "
            "       MIN(m.created_at) at, COUNT(*) n, "
            "       CAST((julianday('now') - julianday(MIN(m.created_at))) * 1440 AS INTEGER) mins "
            "  FROM chat_messages m "
            "  JOIN users u ON u.id = m.user_id "
            " WHERE m.tenant_id = ? AND m.sender = 'user' AND m.read_at IS NULL "
            " GROUP BY m.user_id ORDER BY at ASC LIMIT 30", (tid,)).fetchall()

        # آخرین متنِ هر گفتگو، تا مالک بدون بازکردن بداند موضوع چیست
        last = {}
        for r in ms:
            row = con.execute(
                "SELECT body FROM chat_messages WHERE tenant_id=? AND user_id=? "
                "AND sender='user' ORDER BY id DESC LIMIT 1",
                (tid, r["uid"])).fetchone()
            last[r["uid"]] = (row["body"] if row else "") or ""
    except Exception:
        log.debug("خواندن هشدارها ناموفق", exc_info=True)
        return empty
    finally:
        con.close()

    def who(r):
        return (r["first_name"] or "").strip() or \
               ("@" + r["username"] if r["username"] else "") or \
               f"#{r['tg_id']}"

    items = []
    for r in rc:
        items.append({
            "kind": "receipt", "id": int(r["id"]), "userId": int(r["uid"]),
            "name": who(r), "amount": int(r["amount"] or 0),
            "plan": r["plan"] or "", "at": r["created_at"],
            "waitedMin": max(0, int(r["mins"] or 0)),
            "hasPhoto": (r["receipt_type"] or "") == "photo",
        })
    for r in ms:
        items.append({
            "kind": "message", "id": int(r["uid"]), "userId": int(r["uid"]),
            "name": who(r), "count": int(r["n"] or 0),
            "body": (last.get(r["uid"], "") or "")[:90],
            "at": r["at"], "waitedMin": max(0, int(r["mins"] or 0)),
        })

    items.sort(key=lambda x: -x["waitedMin"])
    return {
        "receipts": len(rc), "messages": sum(int(r["n"] or 0) for r in ms),
        "items": items,
        "oldestMin": items[0]["waitedMin"] if items else 0,
        "ready": True,
    }


@app.get("/api/admin/brand/logo")
def brand_logo_get(x_admin_password: str = Header(...)):
    """
    لوگوی خودِ مالک — شناسه‌اش و اینکه هست یا نه.

    چرا مسیرِ جدا: فهرستِ نماینده‌ها `WHERE parent_id IS NOT NULL`
    است، یعنی خودِ مالک هیچ‌وقت در آن نیست. پس تا امروز هیچ جایی
    برای آپلودِ لوگوی خودش وجود نداشت — قابلیتی که ساخته شده بود ولی
    صاحبِ پنل به آن نمی‌رسید.
    """
    check_auth(x_admin_password)
    con = _bot_conn()
    if not con:
        raise HTTPException(status_code=503, detail="دیتابیس ربات در دسترس نیست")
    try:
        # هیچ‌وقت `LIMIT 1` بدون شرط: ردیفِ مالک اگر یک‌بار پاک و
        # دوباره ساخته شود، شناسه‌اش از نماینده بزرگ‌تر می‌شود.
        r = con.execute(
            "SELECT id, name FROM tenants "
            "WHERE parent_id IS NULL ORDER BY id LIMIT 1").fetchone()
    finally:
        con.close()
    if not r:
        raise HTTPException(status_code=404, detail="مستاجر ریشه پیدا نشد")
    return {"id": r["id"], "name": r["name"] or "",
            "logo": _logo_url(r["id"])}


#: رسیدِ تصویری روی دیسکِ خودمان.
#
#  چرا: نسخه‌ی اول عکس را فقط به گروه مدیریت تلگرام آپلود می‌کرد و
#  `file_id`ش را نگه می‌داشت. اگر گروه تنظیم نشده بود — یا آپلود
#  شکست می‌خورد — `receipt_file` خالی می‌ماند در حالی که
#  `receipt_type` هنوز "photo" بود. نتیجه: پنل ۴۰۴ می‌داد و
#  **عکسِ رسید برای همیشه گم می‌شد**. مشتری پول داده و مدرکش نیست.
#
#  حالا دیسک منبعِ اصلی است و تلگرام فقط راهِ *دیدنِ سریع* در گروه.
RECEIPT_DIR = Path(os.getenv("RECEIPT_DIR", str(CONFIG_PATH.parent / "receipts")))

#: پیشوندی که می‌گوید این رسید روی دیسکِ ماست، نه در تلگرام.
LOCAL_RECEIPT = "local:"


def _receipt_save(order_id: int, blob: bytes):
    """بایت‌های رسید را ذخیره کن و مقدارِ `receipt_file` را برگردان."""
    ext, _ctype = _logo_kind(blob)
    if not ext:
        return None
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{int(order_id)}.{ext}"
    (RECEIPT_DIR / name).write_bytes(blob)
    return LOCAL_RECEIPT + name


def _receipt_local(ref):
    """اگر این ارجاع محلی است، فایلش را بده — وگرنه None."""
    ref = str(ref or "")
    if not ref.startswith(LOCAL_RECEIPT):
        return None
    name = ref[len(LOCAL_RECEIPT):]
    # هیچ‌وقت مسیرِ آمده از بیرون را مستقیم به هم نچسبان
    if "/" in name or "\\" in name or ".." in name:
        return None
    p = RECEIPT_DIR / name
    return p if p.exists() else None


#: عکسِ پروفایلِ مشتری.
#
#  نامِ فایل تصادفی است، نه `<مستاجر>_<کاربر>.png`. چرا: این مسیر
#  عمومی است (تگِ <img> نمی‌تواند هدرِ احراز هویت بفرستد)، و نامِ
#  قابل‌حدس یعنی هر کسی می‌تواند عکسِ هر مشتری را با شمردنِ شناسه‌ها
#  بردارد. نامِ تصادفی همان «آدرس، خودش کلید است».
AVATAR_DIR = Path(os.getenv("AVATAR_DIR", str(CONFIG_PATH.parent / "avatars")))
AVATAR_MAX_BYTES = 512 * 1024


def _avatar_find(tid, uid):
    """فایلِ عکسِ این کاربر، اگر باشد."""
    if not AVATAR_DIR.exists():
        return None
    for p in AVATAR_DIR.glob(f"{int(tid)}_{int(uid)}_*"):
        if p.is_file():
            return p
    return None


def _avatar_url(tid, uid):
    p = _avatar_find(tid, uid)
    return f"/api/public/avatar/{p.name}" if p else ""


def _avatar_clear(tid, uid):
    while True:
        p = _avatar_find(tid, uid)
        if not p:
            return
        try:
            p.unlink()
        except OSError:
            return


def _avatar_save(tid, uid, raw):
    """base64 → فایل. برمی‌گرداند نشانی، یا خطا می‌دهد."""
    import base64
    import secrets as _s
    raw = str(raw or "")
    if raw.lstrip().startswith("data:") and "," in raw[:80]:
        raw = raw.split(",", 1)[1]
    raw = raw.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="عکسی فرستاده نشد")
    if len(raw) > (AVATAR_MAX_BYTES * 4) // 3 + 1024:
        raise HTTPException(status_code=413, detail="حجم عکس بیشتر از ۵۱۲ کیلوبایت است")
    try:
        blob = base64.b64decode(raw, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="عکس خوانده نشد")
    if len(blob) > AVATAR_MAX_BYTES:
        raise HTTPException(status_code=413, detail="حجم عکس بیشتر از ۵۱۲ کیلوبایت است")
    ext, _c = _logo_kind(blob)
    if not ext:
        raise HTTPException(status_code=400, detail="فقط PNG، JPEG یا WebP")

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    _avatar_clear(tid, uid)
    name = f"{int(tid)}_{int(uid)}_{_s.token_hex(8)}.{ext}"
    (AVATAR_DIR / name).write_bytes(blob)
    return f"/api/public/avatar/{name}"


@app.get("/api/public/avatar/{name}")
def public_avatar(name: str):
    """
    عکسِ پروفایل. نامِ فایل تصادفی است، پس خودش کلیدِ دسترسی است.
    """
    # نامِ آمده از بیرون هرگز مستقیم به مسیر نمی‌چسبد
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status_code=404, detail="پیدا نشد")
    p = AVATAR_DIR / name
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="پیدا نشد")
    blob = p.read_bytes()
    _e, ctype = _logo_kind(blob)
    if not ctype:
        raise HTTPException(status_code=404, detail="پیدا نشد")
    return Response(content=blob, media_type=ctype,
                    headers={"Cache-Control": "public, max-age=600"})


#: عکسِ داخل گفتگو.
#
#  همان قاعده‌ی عکسِ پروفایل: نامِ فایل تصادفی است و خودش کلیدِ
#  دسترسی، چون تگِ <img> نمی‌تواند هدرِ احراز هویت بفرستد. نامِ
#  قابل‌حدس یعنی هر کسی با شمردنِ شناسه‌ها عکس‌های پشتیبانیِ بقیه را
#  برمی‌دارد.
#
#  و حدِ حجم بالاتر از پروفایل است: عکسِ صفحه‌ی گوشی معمولاً از یک
#  آواتار بزرگ‌تر است و ۵۱۲ کیلوبایت بیشترشان را رد می‌کرد.
CHAT_DIR = Path(os.getenv("CHAT_DIR", str(CONFIG_PATH.parent / "chat")))
CHAT_MAX_BYTES = 3 * 1024 * 1024


def _chat_photo_save(tid, uid, raw):
    """base64 → فایل. برمی‌گرداند نشانی، یا خطا می‌دهد."""
    import base64
    import secrets as _s
    raw = str(raw or "")
    if raw.lstrip().startswith("data:") and "," in raw[:80]:
        raw = raw.split(",", 1)[1]
    raw = raw.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="عکسی فرستاده نشد")
    if len(raw) > (CHAT_MAX_BYTES * 4) // 3 + 1024:
        raise HTTPException(status_code=413, detail="حجم عکس بیشتر از ۳ مگابایت است")
    try:
        blob = base64.b64decode(raw, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="عکس خوانده نشد")
    if len(blob) > CHAT_MAX_BYTES:
        raise HTTPException(status_code=413, detail="حجم عکس بیشتر از ۳ مگابایت است")
    ext, _c = _logo_kind(blob)
    if not ext:
        raise HTTPException(status_code=400, detail="فقط PNG، JPEG یا WebP")

    CHAT_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{int(tid)}_{int(uid)}_{_s.token_hex(12)}.{ext}"
    (CHAT_DIR / name).write_bytes(blob)
    return f"/api/public/chat-photo/{name}"


def _chat_photo_bytes(url):
    """بایت‌های عکسِ یک پیام، برای فرستادنش در تلگرام."""
    name = str(url or "").rsplit("/", 1)[-1]
    if not name or "\\" in name or ".." in name:
        return None
    p = CHAT_DIR / name
    try:
        return p.read_bytes() if p.is_file() else None
    except OSError:
        return None


@app.get("/api/public/chat-photo/{name}")
def public_chat_photo(name: str):
    """عکسِ گفتگو. نامِ فایل تصادفی است، پس خودش کلیدِ دسترسی است."""
    # نامِ آمده از بیرون هرگز مستقیم به مسیر نمی‌چسبد
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status_code=404, detail="پیدا نشد")
    p = CHAT_DIR / name
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="پیدا نشد")
    blob = p.read_bytes()
    _e, ctype = _logo_kind(blob)
    if not ctype:
        raise HTTPException(status_code=404, detail="پیدا نشد")
    return Response(content=blob, media_type=ctype,
                    headers={"Cache-Control": "public, max-age=3600"})


@app.get("/api/public/logo/{tid}")
def public_logo(tid: int):
    """
    لوگوی یک مستاجر — عمومی، چون مینی‌اپ و صفحه‌ی اشتراک بدون احراز
    هویت بازش می‌کنند. چیزی جز بایت‌های تصویر در پاسخ نیست.
    """
    p = _logo_path(tid)
    if not p:
        raise HTTPException(status_code=404, detail="لوگویی ثبت نشده")
    blob = p.read_bytes()
    _ext, ctype = _logo_kind(blob)
    if not ctype:
        # فایلِ روی دیسک دیگر تصویر نیست — سرو نکن
        raise HTTPException(status_code=404, detail="لوگویی ثبت نشده")
    return Response(content=blob, media_type=ctype,
                    headers={"Cache-Control": "public, max-age=300"})


def _bot_dir():
    return Path(__file__).resolve().parent.parent / "bot"


def _ensure_bot_db():
    """
    اگر دیتابیس ربات نبود، می‌سازدش.

    برمی‌گرداند: (موفق, پیام خطا)
    پیام خطا دقیق است تا کاربر بداند چه کاری کند — نه یک «نصب نشده» مبهم.
    """
    # وجود فایل کافی نیست — ممکن است ساخته شده ولی جدول‌ها نباشند
    # (نصب نیمه‌کاره، یا فایلی که دستی کپی شده). این حالت خطای
    # «no such table» می‌دهد که برای کاربر بی‌معناست.
    if BOT_DB.exists():
        try:
            import sqlite3
            con = sqlite3.connect(f"file:{BOT_DB}?mode=ro", uri=True, timeout=5)
            has = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tenants'"
            ).fetchone()
            con.close()
            if has:
                return True, None
        except Exception:
            pass
        # فایل هست ولی ناقص — از نو می‌سازیم

    bd = _bot_dir()
    if not (bd / "db.py").exists():
        return False, (
            f"پوشه‌ی ربات پیدا نشد ({bd}). "
            "احتمالاً به‌روزرسانی ناقص بوده — روی سرور اجرا کنید: nexora update"
        )

    # اول تلاش مستقیم (سریع‌تر و خطای واضح‌تر می‌دهد)
    try:
        import importlib.util
        BOT_DB.parent.mkdir(parents=True, exist_ok=True)
        os.environ["BOT_DB_PATH"] = str(BOT_DB)

        spec = importlib.util.spec_from_file_location("_nexora_botdb", bd / "db.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.init_db()

        if BOT_DB.exists():
            return True, None
    except Exception as e:
        direct_err = str(e)[:200]
    else:
        direct_err = "ساخته نشد"

    # تلاش دوم: پروسه‌ی جدا
    try:
        import subprocess
        import sys as _sys
        code = (
            "import os, sys\n"
            f"os.environ['BOT_DB_PATH'] = r'{BOT_DB}'\n"
            f"sys.path.insert(0, r'{bd}')\n"
            "import db\n"
            "db.init_db()\n"
        )
        p = subprocess.run([_sys.executable, "-c", code],
                           timeout=30, capture_output=True, text=True)
        if BOT_DB.exists():
            return True, None
        err = (p.stderr or "").strip()[-250:] or direct_err
        return False, f"ساخت دیتابیس ربات ناموفق بود: {err}"
    except Exception as e:
        return False, f"ساخت دیتابیس ربات ناموفق بود: {str(e)[:200]}"


@app.get("/api/admin/bot/settings")
def bot_settings_get(x_admin_password: str = Header(...)):
    """
    تنظیمات ربات اصلی — توکن، پنل، گروه، کارت‌ها، سکه.

    این endpoint هرگز نباید ۵۰۰ بدهد: اگر داده‌ی دیتابیس خراب باشد،
    یک پاسخ خالی برمی‌گرداند تا پنل باز شود و کاربر بتواند از نو
    تنظیم کند — نه اینکه با صفحه‌ی سفید روبه‌رو شود.
    """
    check_auth(x_admin_password)
    okdb, err = _ensure_bot_db()

    con = _bot_conn()
    if not con:
        return {"ready": False, "tenant": None, "error": err,
                "botDir": str(_bot_dir()), "dbPath": str(BOT_DB)}
    try:
        try:
            row = con.execute(
                "SELECT * FROM tenants WHERE parent_id IS NULL ORDER BY id LIMIT 1"
            ).fetchone()
        except Exception as e:
            # جدول ناقص یا اسکیمای قدیمی — پنل باید باز شود
            return {"ready": False, "tenant": None,
                    "error": f"خواندن تنظیمات ناموفق: {str(e)[:150]}"}
        if not row:
            return {"ready": True, "tenant": None}

        t = dict(row)
        # توکن‌ها را ماسک می‌کنیم — در پاسخ کامل نمی‌فرستیم
        for k in ("bot_token", "panel_pass", "panel_token"):
            if t.get(k):
                t[k + "_set"] = True
                t[k] = t[k][:6] + "…" if len(str(t[k])) > 8 else "…"
            else:
                t[k + "_set"] = False
        # settings و topics باید همیشه دیکشنری باشند.
        # اگر مقدارشان "null" یا "[]" باشد، json.loads چیزی برمی‌گرداند
        # که دیکشنری نیست و فرانت‌اند روی آن کرش می‌کند.
        for k in ("topics", "settings"):
            try:
                parsed = json.loads(t.get(k) or "{}")
            except (json.JSONDecodeError, TypeError, ValueError):
                parsed = {}
            t[k] = parsed if isinstance(parsed, dict) else {}

        # فیلدهای متنی نباید None باشند — فرانت‌اند روی input می‌گذاردشان
        for k in ("name", "bot_username", "panel_url", "panel_user",
                  "owner_tg_id", "admin_group_id", "default_inbound"):
            if t.get(k) is None:
                t[k] = ""

        return {"ready": True, "tenant": t}
    except Exception as e:
        return {"ready": False, "tenant": None,
                "error": f"خطای غیرمنتظره: {str(e)[:150]}"}
    finally:
        con.close()


@app.put("/api/admin/bot/settings")
def bot_settings_put(payload: dict, x_admin_password: str = Header(...)):
    """ذخیره تنظیمات ربات اصلی."""
    check_auth(x_admin_password)
    okdb, err = _ensure_bot_db()
    if not okdb:
        raise HTTPException(status_code=400, detail=err or "ماژول ربات در دسترس نیست")

    con = _bot_rw()
    try:
        row = con.execute(
            "SELECT id FROM tenants WHERE parent_id IS NULL ORDER BY id LIMIT 1"
        ).fetchone()

        name = (payload.get("name") or "Nexora").strip()
        if not row:
            cur = con.execute(
                "INSERT INTO tenants (name, is_active, credit) VALUES (?,1,-1)", (name,)
            )
            tid = cur.lastrowid
        else:
            tid = row["id"]

        # فیلدهای ساده — فقط اگر مقدار داده شده باشد به‌روز می‌شوند
        simple = ["name", "bot_username", "owner_tg_id", "panel_url", "panel_user",
                  "default_inbound", "admin_group_id", "is_active"]
        for k in simple:
            if k in payload:
                con.execute(f"UPDATE tenants SET {k}=? WHERE id=?", (payload[k], tid))

        # فیلدهای حساس — فقط وقتی مقدار جدید و غیرخالی بیاید
        for k in ("bot_token", "panel_pass", "panel_token"):
            v = payload.get(k)
            if v and not str(v).endswith("…"):
                con.execute(f"UPDATE tenants SET {k}=? WHERE id=?", (v, tid))

        for k in ("topics", "settings"):
            if k in payload and isinstance(payload[k], (dict, list)):
                con.execute(f"UPDATE tenants SET {k}=? WHERE id=?",
                            (json.dumps(payload[k], ensure_ascii=False), tid))

        con.commit()
        return {"ok": True, "tenantId": tid}
    finally:
        con.close()


@app.get("/api/admin/bot/plans")
def bot_plans_get(x_admin_password: str = Header(...)):
    """لیست پلن‌های فروش."""
    check_auth(x_admin_password)
    con = _bot_conn()
    if not con:
        return {"plans": [], "ready": False}
    try:
        # به مستاجر اصلی محدود، مثل مسیر ذخیره.
        #
        # قبلاً بی‌قید بود. تا وقتی فقط یک ربات وجود داشت فرقی
        # نمی‌کرد، ولی از وقتی نماینده می‌تواند ربات خودش را داشته
        # باشد، پلن‌های او در فهرست پلن‌های مالک ظاهر می‌شدند — و
        # چون *ذخیره* به مستاجر اصلی محدود است، حذفشان از آن فهرست
        # پاسخ «ok» می‌داد و هیچ کاری نمی‌کرد.
        root = con.execute(
            "SELECT id FROM tenants WHERE parent_id IS NULL "
            "ORDER BY id LIMIT 1").fetchone()
        if root:
            rows = con.execute(
                "SELECT * FROM plans WHERE tenant_id=? ORDER BY sort_order, id",
                (root["id"],)).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM plans ORDER BY sort_order, id").fetchall()
        return {"plans": [dict(r) for r in rows], "ready": True}
    except Exception:
        return {"plans": [], "ready": True}
    finally:
        con.close()


@app.put("/api/admin/bot/plans")
def bot_plans_put(payload: dict, x_admin_password: str = Header(...)):
    """ذخیره کامل لیست پلن‌ها (جایگزینی)."""
    check_auth(x_admin_password)
    okdb, err = _ensure_bot_db()
    if not okdb:
        raise HTTPException(status_code=400, detail=err or "ماژول ربات در دسترس نیست")

    plans = payload.get("plans")
    if not isinstance(plans, list):
        raise HTTPException(status_code=400, detail="فهرست پلن‌ها نامعتبر است")

    con = _bot_rw()
    try:
        row = con.execute(
            "SELECT id FROM tenants WHERE parent_id IS NULL ORDER BY id LIMIT 1"
        ).fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="ابتدا تنظیمات ربات را ذخیره کنید")
        tid = row["id"]

        keep = [p.get("id") for p in plans if p.get("id")]
        if keep:
            ph = ",".join("?" * len(keep))
            con.execute(
                f"DELETE FROM plans WHERE tenant_id=? AND id NOT IN ({ph})",
                [tid] + keep)
        else:
            con.execute("DELETE FROM plans WHERE tenant_id=?", (tid,))

        for i, p in enumerate(plans):
            vals = (
                p.get("name", "پلن"), p.get("description", ""),
                int(p.get("gb") or 0), int(p.get("days") or 0),
                int(p.get("ip_limit") or 0), int(p.get("price") or 0),
                p.get("inbound_id"), 1 if p.get("is_active", True) else 0,
                1 if p.get("is_trial") else 0, i,
            )
            if p.get("id"):
                con.execute(
                    "UPDATE plans SET name=?,description=?,gb=?,days=?,ip_limit=?,"
                    "price=?,inbound_id=?,is_active=?,is_trial=?,sort_order=? "
                    "WHERE id=? AND tenant_id=?", vals + (p["id"], tid))
            else:
                con.execute(
                    "INSERT INTO plans (name,description,gb,days,ip_limit,price,"
                    "inbound_id,is_active,is_trial,sort_order,tenant_id) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)", vals + (tid,))

        con.commit()
        return {"ok": True, "count": len(plans)}
    finally:
        con.close()


@app.post("/api/admin/bot/orders/{order_id}/reject-with-reason")
def bot_reject_reason(order_id: int, payload: dict,
                      x_admin_password: str = Header(...)):
    """
    رد سفارش با دلیل مشخص.

    دلیل در admin_note ذخیره می‌شود و ربات آن را برای مشتری می‌فرستد
    و سکه‌های خرج‌شده را برمی‌گرداند.
    """
    check_auth(x_admin_password)
    reason = (payload or {}).get("reason", "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="دلیل رد را بنویسید")

    if not BOT_DB.exists():
        raise HTTPException(status_code=400, detail="دیتابیس ربات موجود نیست")

    con = _bot_rw()
    try:
        row = con.execute("SELECT status FROM orders WHERE id=?", (order_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="سفارش پیدا نشد")
        if row["status"] not in ("awaiting", "review"):
            raise HTTPException(status_code=400, detail="این سفارش قبلاً بررسی شده است")

        # ربات این وضعیت را می‌بیند، به مشتری خبر می‌دهد و سکه را برمی‌گرداند
        con.execute(
            "UPDATE orders SET status='panel_reject', admin_note=?, "
            "reviewed_at=CURRENT_TIMESTAMP WHERE id=?",
            (reason[:400], order_id))
        con.commit()
        return {"ok": True}
    finally:
        con.close()


@app.post("/api/admin/bot/orders/{order_id}/{action}")
def bot_order_action(order_id: int, action: str, x_admin_password: str = Header(...)):
    """
    تایید یا رد سفارش از داخل پنل.

    نکته: ساخت کانفیگ و اطلاع به مشتری کار ربات است. پنل فقط وضعیت را
    علامت‌گذاری می‌کند و ربات در چرخه‌ی بعدی‌اش آن را می‌بیند و انجام می‌دهد.
    """
    check_auth(x_admin_password)
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="عملیات نامعتبر")
    if not BOT_DB.exists():
        raise HTTPException(status_code=400, detail="دیتابیس ربات موجود نیست")

    con = _bot_rw()
    try:
        row = con.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="سفارش پیدا نشد")
        if row["status"] not in ("awaiting", "review"):
            raise HTTPException(status_code=400, detail="این سفارش قبلاً بررسی شده است")

        new_status = "panel_approve" if action == "approve" else "rejected"
        con.execute(
            "UPDATE orders SET status=?, reviewed_at=CURRENT_TIMESTAMP, admin_note=? "
            "WHERE id=?",
            (new_status, "از پنل مدیریت", order_id))
        con.commit()
        return {"ok": True, "status": new_status}
    finally:
        con.close()


# ═══════════════════════════════════════════════════════════
#  خودترمیمی هنگام راه‌اندازی
#
#  بک‌اند تنها جزئی است که بعد از هر به‌روزرسانی حتماً ری‌استارت
#  می‌شود. پس هر کاری که ممکن است در به‌روزرسانی جا بماند را
#  اینجا انجام می‌دهیم — تا کاربر هیچ‌وقت مجبور به کار دستی نشود.
# ═══════════════════════════════════════════════════════════

def _root_dir():
    return Path(__file__).resolve().parent.parent


def _selfheal_cli():
    """دستور nexora را با نسخه‌ی نصب‌شده همگام می‌کند."""
    src = _root_dir() / "nexora-cli.sh"
    dst = Path("/usr/local/bin/nexora")
    if not src.exists() or not dst.parent.exists():
        return None

    data = src.read_bytes()
    if dst.exists() and dst.read_bytes() == data:
        return None

    tmp = dst.with_suffix(".new")
    tmp.write_bytes(data)
    os.chmod(tmp, 0o755)
    os.replace(tmp, dst)   # اتمی — اگر همان لحظه اجرا شود، نصفه نمی‌ماند
    return "CLI به‌روز شد"


def _selfheal_scripts():
    """دسترسی اجرایی اسکریپت‌ها را برمی‌گرداند."""
    fixed = 0
    for p in _root_dir().glob("*.sh"):
        try:
            if not os.access(p, os.X_OK):
                os.chmod(p, 0o755)
                fixed += 1
        except OSError:
            pass
    return f"{fixed} اسکریپت اجرایی شد" if fixed else None


def _selfheal_bot_deps():
    """وابستگی‌های ربات را در صورت نبود نصب می‌کند."""
    root = _root_dir()
    req = root / "bot" / "requirements.txt"
    if not req.exists():
        return None

    try:
        import importlib
        importlib.import_module("requests")
        return None          # قبلاً هست
    except ImportError:
        pass

    pip = root / "backend" / "venv" / "bin" / "pip"
    if not pip.exists():
        return None

    try:
        import subprocess
        subprocess.run([str(pip), "install", "-r", str(req), "-q"],
                       timeout=180, capture_output=True)
        return "وابستگی‌های ربات نصب شد"
    except Exception:
        return None


def _selfheal_bot_service():
    """اگر ماژول ربات هست ولی سرویسش نیست، می‌سازدش."""
    root = _root_dir()
    if not (root / "bot" / "run.py").exists():
        return None

    svc = Path("/etc/systemd/system/nexora-bot.service")
    if svc.exists() or not svc.parent.exists():
        return None

    python = root / "backend" / "venv" / "bin" / "python"
    if not python.exists():
        return None

    try:
        svc.write_text(f"""[Unit]
Description=Nexora Telegram Bot
After=network.target nexora-panel.service

[Service]
Type=simple
WorkingDirectory={root}/bot
Environment="BOT_DB_PATH={root}/data/bot.db"
Environment="PANEL_CONFIG={root}/data/config.json"
ExecStart={python} run.py
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
""", encoding="utf-8")
        os.chmod(svc, 0o600)

        import subprocess
        subprocess.run(["systemctl", "daemon-reload"], timeout=20, capture_output=True)
        return "سرویس ربات ساخته شد"
    except Exception:
        return None


def _selfheal_backup_cron():
    """بک‌آپ روزانه را در صورت نبود تنظیم می‌کند."""
    root = _root_dir()
    cfg = root / "data" / "config.json"
    if not cfg.exists():
        return None

    try:
        import subprocess
        cur = subprocess.run(["crontab", "-l"], capture_output=True,
                             text=True, timeout=15).stdout or ""
        if "nexora" in cur and "config.json" in cur:
            return None

        line = (f"0 3 * * * cp {cfg} /root/backups/config-$(date +\\%Y\\%m\\%d).json 2>/dev/null")
        Path("/root/backups").mkdir(parents=True, exist_ok=True)
        new_tab = (cur.rstrip("\n") + "\n" + line + "\n").lstrip("\n")
        subprocess.run(["crontab", "-"], input=new_tab, text=True,
                       timeout=15, capture_output=True)
        return "بک‌آپ روزانه تنظیم شد"
    except Exception:
        return None


HISTORY_PATH = Path(os.getenv("HISTORY_PATH",
                              str(CONFIG_PATH.parent / "usage-history.json")))

#: چند نمونه نگه داریم. هر ۵ دقیقه یک نمونه یعنی ۵۷۶ نمونه = دو روز.
#: بیشتر از این، فایل بزرگ می‌شود بدون اینکه به تصمیم کمکی کند.
HISTORY_MAX = 576


def _history_load():
    try:
        with open(HISTORY_PATH, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except Exception:
        return []


def _history_sample():
    """
    یک نمونه از وضعیت سرور.

    بدون تاریخچه، «پیک سرور کی است؟» جواب ندارد و زمان‌بندی نگهداری
    فقط حدس است. نمونه‌ها همراه همان حلقه‌ی پنج‌دقیقه‌ای گرفته می‌شوند
    تا بار اضافه‌ای به سرور تحمیل نشود.
    """
    if not MONITOR:
        return
    try:
        snap = MONITOR.snapshot(include=["cpu", "memory", "connections"])
    except Exception:
        return

    def _val(key):
        for m in snap.get("metrics") or []:
            if m.get("key") == key and isinstance(m.get("value"), (int, float)):
                return round(float(m["value"]), 1)
        return None

    conn = (snap.get("sections") or {}).get("connections") or {}
    row = {
        "t": datetime.now().isoformat(timespec="minutes"),
        "cpu": _val("cpu"),
        "mem": _val("memory"),
        "conn": int(conn.get("total") or 0),
        "ips": int(conn.get("uniqueIps") or 0),
    }

    rows = _history_load()
    rows.append(row)
    rows = rows[-HISTORY_MAX:]
    try:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False)
    except Exception:
        pass


@app.get("/api/admin/usage-history")
def usage_history(hours: int = 24, x_admin_password: str = Header(...)):
    """تاریخچه‌ی مصرف سرور و ساعت پیک."""
    check_auth(x_admin_password)
    from datetime import timedelta

    rows = _history_load()
    if hours and hours > 0:
        cut = (datetime.now() - timedelta(hours=int(hours))).isoformat(
            timespec="minutes")
        rows = [r for r in rows if str(r.get("t") or "") >= cut]

    # میانگین هر ساعت شبانه‌روز — همان چیزی که ساعت کم‌مصرف را نشان
    # می‌دهد و زمان‌بندی نگهداری باید رویش بنشیند
    buckets = {}
    for r in _history_load():
        try:
            h = int(str(r["t"])[11:13])
        except (ValueError, KeyError, IndexError):
            continue
        b = buckets.setdefault(h, {"conn": 0, "cpu": 0.0, "n": 0})
        b["conn"] += int(r.get("conn") or 0)
        b["cpu"] += float(r.get("cpu") or 0)
        b["n"] += 1

    hourly = [{"hour": h,
               "conn": round(b["conn"] / b["n"], 1),
               "cpu": round(b["cpu"] / b["n"], 1)}
              for h, b in sorted(buckets.items()) if b["n"]]

    quietest = min(hourly, key=lambda x: x["conn"])["hour"] if hourly else None
    busiest = max(hourly, key=lambda x: x["conn"])["hour"] if hourly else None

    return {"samples": rows, "hourly": hourly, "count": len(rows),
            "quietestHour": quietest, "busiestHour": busiest,
            "maxSamples": HISTORY_MAX}


@app.get("/api/admin/top-clients")
def top_clients(limit: int = 10, x_admin_password: str = Header(...)):
    """
    پرمصرف‌ترین مشتری‌ها بر اساس ترافیک واقعی پنل.

    شمارش اتصال فقط IP می‌دهد؛ این می‌گوید کدام *مشتری* — با نام
    کانفیگ، حجم مصرفی و سهمش از کل — بیشترین بار را می‌برد.
    """
    check_auth(x_admin_password)

    clients, _groups, err = _read_xui_clients()
    if clients is None:
        return {"ready": False, "error": err or "دیتابیس پنل در دسترس نیست",
                "clients": []}

    out = []
    for c in clients:
        email = c.get("email")
        if not email:
            continue
        used = int(c.get("used") or 0)
        quota = int(c.get("totalGB") or 0)
        out.append({
            "email": email,
            "group": c.get("group") or "بدون گروه",
            "usedBytes": used,
            "usedGB": round(used / (1024 ** 3), 2),
            "quotaGB": round(quota / (1024 ** 3), 1) if quota else 0,
            "pctOfQuota": (round(used * 100.0 / quota, 1) if quota else None),
            "enable": bool(c.get("enable", True)),
            "expiryTime": c.get("expiry_time") or c.get("expiryTime") or 0,
        })

    total = sum(x["usedBytes"] for x in out) or 1
    for x in out:
        x["pctOfAll"] = round(x["usedBytes"] * 100.0 / total, 1)

    out.sort(key=lambda x: x["usedBytes"], reverse=True)
    return {"ready": True, "clients": out[:max(1, min(limit, 100))],
            "totalClients": len(out),
            "totalUsedGB": round(total / (1024 ** 3), 1)}


try:
    import firewall as FIREWALL
except Exception:
    try:
        import importlib.util as _ifw
        _fs = _ifw.spec_from_file_location(
            "firewall", Path(__file__).resolve().parent / "firewall.py")
        FIREWALL = _ifw.module_from_spec(_fs)
        _fs.loader.exec_module(FIREWALL)
    except Exception:
        FIREWALL = None


try:
    import intrusion as INTRUSION
except Exception:
    try:
        import importlib.util as _iin
        _is = _iin.spec_from_file_location(
            "intrusion", Path(__file__).resolve().parent / "intrusion.py")
        INTRUSION = _iin.module_from_spec(_is)
        _is.loader.exec_module(INTRUSION)
    except Exception:
        INTRUSION = None


def _fw_or_die():
    if not FIREWALL:
        raise HTTPException(status_code=500, detail="ماژول فایروال بارگذاری نشد")
    return FIREWALL


try:
    import netid as NETID
except Exception:
    try:
        import importlib.util as _ind
        _ns = _ind.spec_from_file_location(
            "netid", Path(__file__).resolve().parent / "netid.py")
        NETID = _ind.module_from_spec(_ns)
        _ns.loader.exec_module(NETID)
    except Exception:
        NETID = None


def _connected_ips(status=None):
    """
    آی‌پی‌هایی که «آشنا»یند — تانل خودمان یا مشتری.

    این تنها چیزی است که «مهاجم» را از «مشتریِ من که رمز را اشتباه
    می‌زند» جدا می‌کند. بدون آن، مدیر ممکن است آی‌پی مشتری خودش را
    ببندد و تازه وقتی شکایت آمد بفهمد.

    نکته‌ی مهم: خیلی از این آدرس‌ها خودشان VPN‌اند. آدرس واقعیِ پشت
    یک VPN از بیرون قابل کشف نیست — ولی لازم هم نیست. اگر همان آدرس
    را کلاینت‌های خودمان استفاده می‌کنند، پشتش مشتری نشسته و بستنش
    یعنی قطع‌کردن او.

    `status` اگر دیکشنری بگیرد، پر می‌شود با اینکه چند منبع واقعاً
    جواب دادند و کدام‌ها نه.

    چرا لازم است:
        هر سه منبع داخل try بودند و شکستشان فقط در لاگ debug می‌نشست.
        اگر همه‌شان می‌افتادند — یا ماژول‌ها اصلاً بارگذاری نشده
        بودند — این تابع یک مجموعه‌ی *خالی* برمی‌گرداند.

        و مجموعه‌ی خالی از «هیچ‌کدام مشتری نیستند» قابل تشخیص نبود.
        بستنِ دسته‌ای آن را «پس همه را ببند» می‌خواند و در پاسخ
        می‌نوشت «۰ آی‌پی چون به سرویس وصل بودند رد شد» — یعنی
        اطمینان می‌داد که بررسی شده، در حالی که اصلاً نشده بود.

        روی خطرناک‌ترین دکمه‌ی این پنل.
    """
    ips = set()
    answered = 0
    failed = []

    if NETID:
        for _fn, _label in ((NETID.client_ips, "آی‌پی کلاینت‌ها"),
                            (NETID.tunnel_peers, "آی‌پی تانل‌ها")):
            try:
                ips |= set(_fn().keys())
                answered += 1
            except Exception as e:
                failed.append(f"{_label}: {type(e).__name__}")
                log.debug("خواندن %s ناموفق", _label, exc_info=True)
    else:
        failed.append("ماژول شناسایی آی‌پی بارگذاری نشده")

    if MONITOR:
        try:
            data = MONITOR.connections(top=200) or {}
            for key in ("byIp", "heavy", "tunnels"):
                for row in (data.get(key) or []):
                    ip = (row or {}).get("ip")
                    if ip:
                        ips.add(ip)
            answered += 1
        except Exception as e:
            failed.append(f"اتصال‌های جاری: {type(e).__name__}")
            log.debug("خواندن اتصال‌ها ناموفق", exc_info=True)
    else:
        failed.append("ماژول مانیتورینگ بارگذاری نشده")

    if status is not None:
        status["answered"] = answered
        status["failed"] = failed

    return ips


@app.get("/api/admin/firewall/intrusion")
def firewall_intrusion(hours: int = 24, x_admin_password: str = Header(...)):
    """
    چه کسی دارد به سرور در می‌زند — و کدامشان مشتری خودتان است.

    ساعت را محدود می‌کنیم تا خواندن لاگ روی سرور شلوغ طول نکشد.
    """
    check_auth(x_admin_password)
    if not INTRUSION:
        raise HTTPException(status_code=500, detail="ماژول تشخیص نفوذ بارگذاری نشد")
    hours = max(1, min(int(hours or 24), 168))

    res = INTRUSION.summary(known_ips=_connected_ips(), hours=hours)

    # هر آدرس را دسته‌بندی می‌کنیم: داخلی، تانل خودمان، مشتری، یا ناشناس.
    # بدون این، مدیر فقط یک عدد می‌بیند و نمی‌داند بستنش چه هزینه‌ای دارد.
    if NETID:
        try:
            tun = NETID.tunnel_peers()
            cl = NETID.client_ips()
            # نام معکوس فقط از کش خوانده می‌شود.
            #
            # نسخه‌ی قبلی برای هر آدرس یک جست‌وجوی DNS می‌زد و صفحه‌ی
            # «تلاش برای نفوذ» تا یک دقیقه‌ونیم باز نمی‌شد. حالا صفحه
            # فوری می‌آید و نام‌ها در پس‌زمینه پر می‌شوند — دفعه‌ی بعد
            # که صفحه باز شود، از کش می‌آیند.
            attempts = (res.get("ssh") or {}).get("attempts") or []
            top = [a.get("ip") for a in attempts[:60] if a.get("ip")]

            cached = NETID.rdns_cached(top)
            for a in attempts[:60]:
                ptr = cached.get(NETID.normalize(a.get("ip")))
                if ptr is None:
                    continue          # هنوز پرسیده نشده
                own = NETID.owner(a.get("ip"), ptr=ptr)
                a["owner"] = own.get("label") or ""
                a["ownerKind"] = own.get("kind")
                a["ptr"] = own.get("ptr") or ""
                a["ownerWhy"] = own.get("why") or ""

            # آنچه در کش نبود، در پس‌زمینه پرسیده می‌شود
            missing = [i for i in top
                       if NETID.normalize(i) not in cached]
            if missing:
                NETID.rdns_warm(missing)
                res["lookupPending"] = len(missing)
            for a in attempts:
                info = NETID.identify(a.get("ip"), tunnels=tun, clients=cl)
                a["kind"] = info.get("kind")
                a["why"] = info.get("why")
                if info.get("clients"):
                    a["clients"] = info["clients"]
                # «آشنا» یعنی تانل یا مشتری — هر دو نباید بسته شوند
                if info.get("kind") in ("tunnel", "customer", "local"):
                    a["known"] = True
            res["vpnNote"] = NETID.explain_vpn()
        except Exception:
            log.debug("دسته‌بندی آی‌پی‌ها ناموفق", exc_info=True)

    # customers را دوباره می‌سازیم چون known بالا ممکن است عوض شده باشد
    att = (res.get("ssh") or {}).get("attempts") or []
    res.setdefault("ssh", {})["customers"] = [a for a in att if a.get("known")]
    return res


@app.post("/api/admin/firewall/block-attackers")
def firewall_block_attackers(payload: dict, x_admin_password: str = Header(...)):
    """
    بستن دسته‌ای آی‌پی‌های مهاجم، با تایید صریح.

    آی‌پی‌هایی که به سرویس وصل‌اند عمداً رد می‌شوند مگر مدیر صریحاً
    اسمشان را بیاورد — بستن مشتری بدترین نتیجه‌ی ممکن این صفحه است.
    """
    check_auth(x_admin_password)
    fw = _fw_or_die()
    p = payload or {}
    if not p.get("confirm"):
        raise HTTPException(status_code=400, detail="بستن آی‌پی نیاز به تایید دارد")

    wanted = [str(x).strip() for x in (p.get("ips") or []) if str(x).strip()]
    if not wanted:
        raise HTTPException(status_code=400, detail="فهرست آی‌پی خالی است")
    if len(wanted) > 100:
        raise HTTPException(status_code=400, detail="حداکثر ۱۰۰ آی‌پی در هر بار")

    _st = {}
    connected = _connected_ips(status=_st)
    force = bool(p.get("includeConnected"))

    # هیچ منبعی جواب نداد یعنی *نمی‌دانیم* کدام مشتری است — نه اینکه
    # هیچ‌کدام نیست. ادامه‌دادن یعنی بستنِ کورکورانه، و پیامِ
    # «۰ آی‌پی رد شد» هم دروغِ اطمینان‌بخشی می‌شود.
    if not _st.get("answered") and not force:
        raise HTTPException(
            status_code=503,
            detail=("نمی‌توان تشخیص داد کدام آدرس مشتری شماست ("
                    + "، ".join(_st.get("failed") or ["منبعی در دسترس نیست"])
                    + "). اگر با این حال مطمئنید، دوباره با گزینه‌ی "
                      "«شامل آدرس‌های وصل» بفرستید."))
    done, skipped, failed = [], [], []
    for ip in wanted:
        if ip in connected and not force:
            skipped.append(ip)
            continue
        try:
            ok, note = fw.block_ip(ip, comment="nexora: brute-force",
                                   protect=_auth_ip.get())
            (done if ok else failed).append({"ip": ip, "note": note})
        except Exception as e:
            failed.append({"ip": ip, "note": str(e)})

    note = f"{len(done)} آی‌پی بسته شد"
    if skipped:
        note += f" · {len(skipped)} آی‌پی چون به سرویس وصل بودند رد شد"
    # اگر بعضی منابع افتاده‌اند، «۰ رد شد» معنای کامل ندارد
    if _st.get("failed"):
        note += (" · بخشی از تشخیص در دسترس نبود: "
                 + "، ".join(_st["failed"]))
    if failed:
        note += f" · {len(failed)} ناموفق"
    return {"ok": True, "note": note, "blocked": done,
            "skipped": skipped, "failed": failed}


@app.get("/api/admin/firewall")
def firewall_status(x_admin_password: str = Header(...)):
    """وضعیت فایروال و قواعدش."""
    check_auth(x_admin_password)
    return _fw_or_die().status()


@app.post("/api/admin/firewall/toggle")
def firewall_toggle(payload: dict = None, x_admin_password: str = Header(...)):
    """
    روشن/خاموش کردن فایروال.

    روشن‌کردن بدون قاعده‌ی SSH یعنی قطع دسترسی مدیر به سرور — پس
    تا وقتی confirmSsh صریحاً فرستاده نشود، رد می‌شود.
    """
    check_auth(x_admin_password)
    fw = _fw_or_die()
    p = payload or {}
    want = bool(p.get("enable"))

    if want:
        ok, note = fw.enable(confirm_ssh=bool(p.get("confirmSsh")))
    else:
        ok, note = fw.disable()

    if not ok:
        raise HTTPException(status_code=400, detail=note)
    return {"ok": True, "note": note, **fw.status()}


@app.post("/api/admin/firewall/rule")
def firewall_add_rule(payload: dict, x_admin_password: str = Header(...)):
    """افزودن قاعده."""
    check_auth(x_admin_password)
    fw = _fw_or_die()
    p = payload or {}
    ok, note = fw.add_rule(
        port=p.get("port"), proto=p.get("proto") or "tcp",
        action=p.get("action") or "allow",
        source=p.get("source") or None, comment=p.get("comment") or None)
    if not ok:
        raise HTTPException(status_code=400, detail=note)
    return {"ok": True, "note": note, **fw.status()}


@app.delete("/api/admin/firewall/rule/{num}")
def firewall_delete_rule(num: int, confirm: int = 0,
                         x_admin_password: str = Header(...)):
    """حذف قاعده. قواعد حیاتی مثل SSH تایید جدا می‌خواهند."""
    check_auth(x_admin_password)
    fw = _fw_or_die()
    ok, note = fw.delete_rule(num, confirm_critical=bool(confirm))
    if not ok:
        raise HTTPException(status_code=400, detail=note)
    return {"ok": True, "note": note, **fw.status()}


@app.get("/api/admin/firewall/suggest")
def firewall_suggest(x_admin_password: str = Header(...)):
    """
    پیشنهاد قواعد بر اساس سرویس‌هایی که واقعاً روی سرور اجرا می‌شوند.

    هیچ‌چیز اعمال نمی‌شود — فقط می‌گوید چه چیزی باید باز بماند و چه
    چیزی مشکوک است، با دلیل هرکدام.
    """
    check_auth(x_admin_password)
    fw = _fw_or_die()
    ports = MONITOR.listening() if MONITOR else []
    return fw.suggest(ports)


@app.post("/api/admin/firewall/apply-plan")
def firewall_apply_plan(payload: dict, x_admin_password: str = Header(...)):
    """اعمال دسته‌ای قواعد پیشنهادی، با تایید صریح مدیر."""
    check_auth(x_admin_password)
    fw = _fw_or_die()
    p = payload or {}
    ok, note, results = fw.apply_plan(p.get("rules") or [],
                                      confirm=bool(p.get("confirm")))
    if not ok:
        raise HTTPException(status_code=400, detail=note)
    return {"ok": True, "note": note, "results": results, **fw.status()}


@app.post("/api/admin/firewall/block-ip")
def firewall_block_ip(payload: dict, x_admin_password: str = Header(...)):
    """
    بستن یا بازکردن یک آی‌پی.

    این همان دکمه‌ای است که از صفحه‌ی مانیتورینگ، وقتی یک آی‌پی سهم
    غیرعادی گرفته، به آن وصل می‌شود.
    """
    check_auth(x_admin_password)
    fw = _fw_or_die()
    p = payload or {}
    ip = str(p.get("ip") or "").strip()

    if p.get("unblock"):
        ok, note = fw.unblock_ip(ip)
    else:
        ok, note = fw.block_ip(ip, comment=p.get("comment") or "از پنل نکسورا",
                               protect=_auth_ip.get())

    if not ok:
        raise HTTPException(status_code=400, detail=note)
    return {"ok": True, "note": note}


#: پیش‌فرض زمان‌بندی نگهداری.
#
# ۰۵:۰۰ به وقت سرور انتخاب شده چون کم‌ترین مصرف VPN ایرانی همان‌جاست:
# شب‌روها خوابیده‌اند و صبح‌کارها هنوز بیدار نشده‌اند. عمل پیش‌فرض هم
# ری‌استارت Xray است نه ریبوت سرور — یکی حدود یک ثانیه قطعی دارد،
# دیگری یک تا دو دقیقه.
MAINT_DEFAULT = {
    "enabled": False,
    "action": "xray",          # xray | reboot
    "hour": 5,
    "minute": 0,
    "days": [],                # خالی یعنی هر روز
    "skipIfBusy": True,
    "busyThreshold": 20,
    "confirmedReboot": False,  # ریبوت تا تایید صریح مدیر اجرا نمی‌شود
    "lastRun": None,
    "lastResult": None,
}


def _maint_conf():
    cfg = load_config()
    m = dict(MAINT_DEFAULT)
    got = cfg.get("maintenance")
    if isinstance(got, dict):
        m.update({k: v for k, v in got.items() if k in MAINT_DEFAULT})
    return m


def _maint_save(m):
    cfg = load_config()
    cfg["maintenance"] = m
    save_config(cfg)


def _maint_busy():
    """آیا سرور الان شلوغ است؟ برای اینکه وسط پیک ری‌استارت نکنیم."""
    if not MONITOR:
        return False, 0
    try:
        c = MONITOR.connections() or {}
        n = int(c.get("total") or 0)
        return n, n
    except Exception:
        return 0, 0


def _maint_run(action):
    """اجرای واقعی نگهداری. خروجی: (موفق، توضیح)"""
    import subprocess
    if action == "reboot":
        try:
            subprocess.Popen(["shutdown", "-r", "+1"],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            return True, "ریبوت سرور تا یک دقیقه‌ی دیگر"
        except Exception as e:
            return False, f"ریبوت ناموفق: {e}"

    for svc in ("x-ui", "xray"):
        try:
            r = subprocess.run(["systemctl", "restart", svc],
                               capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                return True, f"سرویس {svc} ری‌استارت شد"
        except Exception:
            continue
    return False, "هیچ‌کدام از سرویس‌های x-ui/xray ری‌استارت نشدند"


def _maint_tick():
    """
    یک‌بار بررسی پنجره‌ی نگهداری. از حلقه‌ی سلامت (هر ۵ دقیقه) صدا زده
    می‌شود، پس پنجره را ۵ دقیقه‌ای می‌گیریم تا جا نیفتد.
    """
    m = _maint_conf()
    if not m.get("enabled"):
        return
    if m.get("action") == "reboot" and not m.get("confirmedReboot"):
        return

    now = datetime.now()
    if m.get("days") and now.weekday() not in [int(d) for d in m["days"]]:
        return

    target = now.replace(hour=int(m.get("hour", 5)),
                         minute=int(m.get("minute", 0)),
                         second=0, microsecond=0)
    delta = (now - target).total_seconds()
    if not (0 <= delta < 300):
        return

    today = now.strftime("%Y-%m-%d")
    if str(m.get("lastRun") or "")[:10] == today:
        return

    if m.get("skipIfBusy"):
        busy, n = _maint_busy()
        if busy and n >= int(m.get("busyThreshold") or 20):
            m["lastRun"] = now.isoformat(timespec="seconds")
            m["lastResult"] = f"رد شد — {n} اتصال فعال بود"
            _maint_save(m)
            return

    ok, note = _maint_run(m.get("action") or "xray")
    m["lastRun"] = now.isoformat(timespec="seconds")
    m["lastResult"] = ("انجام شد — " if ok else "ناموفق — ") + note
    _maint_save(m)


@app.get("/api/admin/maintenance")
def maintenance_get(x_admin_password: str = Header(...)):
    """زمان‌بندی نگهداری خودکار."""
    check_auth(x_admin_password)
    m = _maint_conf()

    from datetime import timedelta

    nxt = None
    if m.get("enabled"):
        now = datetime.now()
        cand = now.replace(hour=int(m["hour"]), minute=int(m["minute"]),
                           second=0, microsecond=0)
        if cand <= now:
            cand += timedelta(days=1)
        for _ in range(8):
            if not m.get("days") or cand.weekday() in [int(d) for d in m["days"]]:
                break
            cand += timedelta(days=1)
        nxt = cand.isoformat(timespec="minutes")

    busy, n = _maint_busy()
    m["nextRun"] = nxt
    m["activeConnections"] = n
    return m


@app.put("/api/admin/maintenance")
def maintenance_set(payload: dict, x_admin_password: str = Header(...)):
    """
    تنظیم زمان‌بندی.

    ریبوت سرور عمداً سخت‌تر از ری‌استارت سرویس است: تا وقتی
    confirmedReboot صریحاً true نشود، اجرا نمی‌شود. یک تیک اشتباهی
    نباید بتواند سرور فروش را وسط شب بخواباند.
    """
    check_auth(x_admin_password)
    m = _maint_conf()

    action = (payload or {}).get("action") or m["action"]
    if action not in ("xray", "reboot"):
        raise HTTPException(status_code=400, detail="عمل نامعتبر")

    try:
        hour = int(payload.get("hour", m["hour"]))
        minute = int(payload.get("minute", m["minute"]))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="ساعت نامعتبر")
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise HTTPException(status_code=400, detail="ساعت باید بین ۰ تا ۲۳ باشد")

    days = payload.get("days", m["days"]) or []
    days = [int(d) for d in days if str(d).isdigit() and 0 <= int(d) <= 6]

    confirmed = bool(payload.get("confirmedReboot", m["confirmedReboot"]))
    enabled = bool(payload.get("enabled", m["enabled"]))
    if enabled and action == "reboot" and not confirmed:
        raise HTTPException(
            status_code=400,
            detail="ریبوت خودکار سرور نیاز به تایید صریح دارد")

    m.update({
        "enabled": enabled,
        "action": action,
        "hour": hour,
        "minute": minute,
        "days": days,
        "skipIfBusy": bool(payload.get("skipIfBusy", m["skipIfBusy"])),
        "busyThreshold": max(1, int(payload.get("busyThreshold",
                                                m["busyThreshold"]) or 20)),
        "confirmedReboot": confirmed,
    })
    _maint_save(m)
    return {"ok": True, **m}


@app.post("/api/admin/maintenance/run-now")
def maintenance_run_now(payload: dict = None, x_admin_password: str = Header(...)):
    """اجرای دستی — برای وقتی مدیر همین حالا می‌خواهد."""
    check_auth(x_admin_password)
    action = ((payload or {}).get("action") or "xray")
    if action not in ("xray", "reboot"):
        raise HTTPException(status_code=400, detail="عمل نامعتبر")
    if action == "reboot" and not (payload or {}).get("confirm"):
        raise HTTPException(status_code=400,
                            detail="برای ریبوت باید confirm بفرستید")

    ok, note = _maint_run(action)
    m = _maint_conf()
    m["lastRun"] = datetime.now().isoformat(timespec="seconds")
    m["lastResult"] = ("دستی — " if ok else "دستی، ناموفق — ") + note
    _maint_save(m)
    return {"ok": ok, "note": note}


def _start_health_loop():
    """
    بررسی خودکار سلامت هر ۵ دقیقه.

    نخ پس‌زمینه، نه cron — چون باید همراه سرویس بالا و پایین برود
    و اگر پنل خاموش شد، بررسی هم متوقف شود.
    """
    import threading

    def loop():
        time.sleep(60)          # فرصت بالا آمدن کامل سرویس
        while True:
            try:
                if HEALTH:
                    data = HEALTH.run_all(ports=_health_ports(),
                                          domain=_health_domain())
                    _health_alert("سرور پنل", data, key="local")

                # نودها هم بررسی می‌شوند تا اختلال سمت ایران دیده شود
                if TUNNELS_OK:
                    try:
                        con = TUN.conn()
                        ids = [r[0] for r in con.execute(
                            "SELECT id FROM nodes WHERE enabled=1")]
                        con.close()
                        for nid in ids:
                            TUN.queue_job(nid, "health", {})
                            # مانیتورینگ هم خودکار، نه فقط دستی.
                            #
                            # تا امروز sysmon فقط وقتی ثبت می‌شد که مدیر
                            # دکمه‌ای را بزند. یعنی صفحه‌ی مانیتورینگ
                            # سرورهای دیگر تا اولین کلیک خالی بود، و بعد
                            # از آن هم بلافاصله کهنه می‌شد. در لاگ سرور
                            # واقعی بیست‌وسه کار health پشت هم دیده شد و
                            # حتی یک sysmon — چون هیچ‌وقت خواسته نشده بود.
                            if not _sysmon_fresh(nid):
                                TUN.queue_job(nid, "sysmon", {})
                    except Exception:
                        pass
            except Exception:
                pass

            # پنجره‌ی نگهداری هم همین‌جا بررسی می‌شود — نخ جدا لازم
            # ندارد و هر دو با سرویس بالا و پایین می‌روند
            try:
                _history_sample()
            except Exception:
                pass

            try:
                _maint_tick()
            except Exception:
                pass

            time.sleep(300)

    try:
        threading.Thread(target=loop, daemon=True).start()
    except Exception:
        pass


@app.on_event("startup")
def _selfheal():
    """
    همه‌ی ترمیم‌ها را اجرا می‌کند.

    هر مرحله جدا محافظت شده: اگر یکی شکست بخورد، بقیه ادامه می‌دهند
    و سرویس در هر حالت بالا می‌آید. اینها بهبودند، نه ضرورت.
    """
    _start_health_loop()

    steps = [
        ("cli", _selfheal_cli),
        ("scripts", _selfheal_scripts),
        ("bot-deps", _selfheal_bot_deps),
        ("bot-service", _selfheal_bot_service),
        ("cron", _selfheal_backup_cron),
    ]
    done = []
    for name, fn in steps:
        try:
            r = fn()
            if r:
                done.append(r)
        except Exception:
            pass

    if done:
        try:
            import logging
            logging.getLogger("uvicorn").info(
                "خودترمیمی: %s", " · ".join(done))
        except Exception:
            pass


def _svc(action, unit="nexora-bot"):
    """اجرای امن systemctl. برمی‌گرداند (موفق, پیام)."""
    import subprocess
    try:
        r = subprocess.run(["systemctl", action, unit],
                           capture_output=True, text=True, timeout=25)
        if r.returncode == 0:
            return True, ""
        return False, (r.stderr or r.stdout or "").strip()[:200]
    except FileNotFoundError:
        return False, "systemctl در دسترس نیست"
    except Exception as e:
        return False, str(e)[:200]


def _svc_active(unit="nexora-bot"):
    import subprocess
    try:
        r = subprocess.run(["systemctl", "is-active", "--quiet", unit],
                           timeout=10)
        return r.returncode == 0
    except Exception:
        return False


@app.post("/api/admin/bot/service/{action}")
def bot_service(action: str, x_admin_password: str = Header(...)):
    """کنترل سرویس ربات از پنل — بدون نیاز به ورود به سرور."""
    check_auth(x_admin_password)
    if action not in ("start", "stop", "restart"):
        raise HTTPException(status_code=400, detail="عملیات نامعتبر")

    if action in ("start", "restart"):
        if not (_bot_dir() / "run.py").exists():
            raise HTTPException(status_code=400,
                                detail="ماژول ربات روی سرور نیست — nexora update را اجرا کنید")
        # اگر سرویس نبود، بساز
        if not Path("/etc/systemd/system/nexora-bot.service").exists():
            try:
                _selfheal_bot_service()
            except Exception:
                pass

    ok, err = _svc(action)
    if not ok:
        raise HTTPException(status_code=500, detail=err or "اجرای دستور ناموفق بود")

    if action in ("start", "restart"):
        _svc("enable")

    import time
    time.sleep(2.5)
    return {"ok": True, "running": _svc_active()}


#: جدول‌هایی که پشتیبان نمی‌خواهند.
#
#  sqlite_sequence را خودِ SQLite نگه می‌دارد، و bot_flags یک پرچم
#  لحظه‌ای بین پنل و ربات است نه داده‌ی کاربر.
_BACKUP_SKIP = {"sqlite_sequence", "bot_flags"}

#: ترتیب دلخواه — والدها اول. جدول‌های کشف‌شده‌ای که این‌جا نیستند
#: بعد از این‌ها می‌آیند، پس فراموش‌شدنشان ممکن نیست.
_BOT_TABLE_ORDER = [
    "tenants", "users", "plans", "orders", "subscriptions",
    "affiliates", "affiliate_commissions", "affiliate_payouts",
    "coin_tx", "wallet_tx", "discounts", "tickets", "events",
]


def _tables_of(con, order=()):
    """
    فهرست جدول‌های واقعیِ یک دیتابیس، به ترتیب دلخواه.

    چرا از اسکیما خوانده می‌شود و دستی نوشته نمی‌شود: فهرست دستی با
    هر قابلیت تازه عقب می‌ماند و هیچ خطایی هم نمی‌دهد. پشتیبان با
    «ok» دانلود می‌شد و جدول‌های تازه اصلاً در آن نبودند — همکاران
    فروش، پورسانتشان، و کل بخش هزینه‌ها همین‌طور جا افتاده بودند.
    """
    try:
        found = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    except Exception:
        return list(order)
    found -= _BACKUP_SKIP
    known = [t for t in order if t in found]
    return known + sorted(found - set(known))


@app.get("/api/admin/bot/backup")
def bot_backup(x_admin_password: str = Header(...)):
    """دانلود بک‌آپ کامل ربات (JSON)."""
    check_auth(x_admin_password)
    con = _bot_conn()
    if not con:
        raise HTTPException(status_code=400, detail="دیتابیس ربات موجود نیست")

    try:
        tables = _tables_of(con, _BOT_TABLE_ORDER)
        dump = {}
        for t in tables:
            try:
                dump[t] = [dict(r) for r in con.execute(f"SELECT * FROM {t}")]
            except Exception:
                dump[t] = []

        return {
            "version": 1,
            "createdAt": datetime.now().isoformat(timespec="seconds"),
            "panelVersion": (Path(__file__).resolve().parent.parent / "VERSION")
                            .read_text().strip() if (Path(__file__).resolve().parent.parent / "VERSION").exists() else "?",
            "counts": {k: len(v) for k, v in dump.items()},
            "data": dump,
        }
    finally:
        con.close()


@app.post("/api/admin/bot/restore")
def bot_restore(payload: dict, x_admin_password: str = Header(...)):
    """
    بازیابی بک‌آپ ربات.

    قبل از هر کاری از وضعیت فعلی یک نسخه‌ی امن می‌گیریم — اگر بازیابی
    اشتباه بود، داده‌ی فعلی از دست نرفته باشد.
    """
    check_auth(x_admin_password)
    data = (payload or {}).get("data")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="فایل بک‌آپ نامعتبر است")

    okdb, err = _ensure_bot_db()
    if not okdb:
        raise HTTPException(status_code=400, detail=err or "دیتابیس ربات در دسترس نیست")

    # نسخه‌ی امن قبل از بازیابی
    try:
        safety = BOT_DB.with_name(
            f"bot-before-restore-{datetime.now():%Y%m%d-%H%M%S}.db")
        _sqlite_copy(BOT_DB, safety)
    except Exception:
        log.warning("نسخه‌ی امنِ پیش از بازگردانی گرفته نشد", exc_info=True)
        safety = None

    con = _bot_rw()
    try:
        con.execute("PRAGMA foreign_keys=OFF")
        # همه‌ی جدول‌ها اول خالی می‌شوند و بعد پر. اگر وسط کار چیزی
        # بشکند، بدون تراکنشِ صریح نیمی از داده رفته است و نیمی
        # برنگشته — و آن نسخه‌ی امن هم تازه همان‌جا لازم می‌شود.
        con.execute("BEGIN IMMEDIATE")
        # فقط جدول‌هایی که هم در پشتیبان‌اند و هم در این دیتابیس
        # وجود دارند. این‌طور پشتیبانِ نسخه‌ی قدیمی‌تر هم بازمی‌گردد،
        # بدون اینکه جدولی که در آن نبوده خالی شود.
        present = _tables_of(con, _BOT_TABLE_ORDER)
        order = [t for t in present if t in data]
        restored, skipped = {}, {}

        for t in reversed(order):
            try:
                con.execute(f"DELETE FROM {t}")
            except Exception:
                pass

        for t in order:
            rows = data.get(t) or []
            if not rows:
                restored[t] = 0
                continue
            cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
            usable = [c for c in cols if any(c in r for r in rows)]
            if not usable:
                restored[t] = 0
                continue
            ph = ",".join("?" * len(usable))
            sql = f"INSERT OR REPLACE INTO {t} ({','.join(usable)}) VALUES ({ph})"
            n = 0
            for r in rows:
                try:
                    con.execute(sql, [r.get(c) for c in usable])
                    n += 1
                except Exception:
                    pass
            restored[t] = n
            # ردیفی که درج نشد باید دیده شود. قبلاً بی‌صدا رد می‌شد و
            # جوابْ «ok» بود — یعنی بازگردانیِ نصفه، بدون هیچ نشانه‌ای.
            if n < len(rows):
                skipped[t] = len(rows) - n

        missing = sorted(set(data) - set(order))
        con.commit()
        out = {"ok": True, "restored": restored,
               "safetyCopy": str(safety) if safety else None}
        if skipped:
            out["skipped"] = skipped
            out["warning"] = ("بعضی ردیف‌ها بازنگشتند: "
                              + "، ".join(f"{k} ({v})"
                                          for k, v in skipped.items()))
        if missing:
            out["unknownTables"] = missing
        return out
    except Exception as e:
        try:
            con.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"بازیابی ناموفق: {str(e)[:200]}")
    finally:
        con.close()


@app.get("/api/admin/bot/funnel")
def bot_funnel(x_admin_password: str = Header(...)):
    """آمار قیف تبدیل — از استارت تا خرید."""
    check_auth(x_admin_password)
    con = _bot_conn()
    if not con:
        return {"ready": False}

    def one(sql):
        try:
            return con.execute(sql).fetchone()[0] or 0
        except Exception:
            return 0

    # «خرید» یعنی سفارشی که پلنش تست رایگان نبوده.
    #
    #  گرفتنِ تست رایگان خودش یک سفارشِ approved می‌سازد (با مبلغ صفر).
    #  پس با شرطِ ساده‌ی status='approved'، هر کسی که دکمه‌ی تست را زده
    #  «خرید موفق» شمرده می‌شد — و بخشِ «فقط تست گرفتند» هیچ‌وقت
    #  نمی‌توانست چیزی جز صفر باشد، چون همان تست یک سفارشِ approved
    #  برایش ثبت کرده بود.
    #
    #  قیف دقیقاً برای جداکردنِ همین دو گروه ساخته شده. یک عبارت،
    #  نه دو تا: هر جا «خرید واقعی» لازم است از همین خوانده می‌شود.
    REAL_BUY = (f"SELECT 1 FROM orders o {SQL_PLAN_JOIN} "
                f" WHERE o.user_id = u.id AND {SQL_REAL_BUY}")

    try:
        started = one("SELECT COUNT(*) FROM users")
        with_phone = one("SELECT COUNT(*) FROM users WHERE phone IS NOT NULL AND phone<>''")
        # «سفارش ثبت کردند» هم یعنی از مسیر خرید رد شده‌اند، نه اینکه
        # دکمه‌ی تست رایگان را زده باشند
        ordered = one(
            "SELECT COUNT(*) FROM users u WHERE EXISTS ("
            f"  SELECT 1 FROM orders o {SQL_PLAN_JOIN}"
            "   WHERE o.user_id = u.id AND COALESCE(p.is_trial, 0) = 0)")
        paid = one("SELECT COUNT(*) FROM users u WHERE EXISTS (" + REAL_BUY + ")")
        trial = one("SELECT COUNT(*) FROM users WHERE trial_used=1")
        trial_only = one("SELECT COUNT(*) FROM users u WHERE u.trial_used=1 "
                         "AND NOT EXISTS (" + REAL_BUY + ")")
        idle = one(
            "SELECT COUNT(*) FROM users u WHERE NOT EXISTS "
            "(SELECT 1 FROM orders o WHERE o.user_id=u.id) AND u.trial_used=0")

        pct = lambda n: round(n * 100 / started, 1) if started else 0
        return {
            "ready": True,
            "started": started,
            "steps": [
                {"label": "ربات را باز کردند", "n": started, "pct": 100},
                {"label": "شماره ثبت کردند", "n": with_phone, "pct": pct(with_phone)},
                {"label": "سفارش ثبت کردند", "n": ordered, "pct": pct(ordered)},
                {"label": "خرید موفق", "n": paid, "pct": pct(paid)},
            ],
            "segments": {
                "paid": paid,
                "trialOnly": trial_only,
                "trial": trial,
                "idle": idle,
            },
        }
    finally:
        con.close()


SNAP_DIR = Path("/root/nexora-snapshots")


@app.get("/api/admin/snapshots")
def list_snapshots(x_admin_password: str = Header(...)):
    """نسخه‌های ذخیره‌شده برای بازگشت — بدون نیاز به ترمینال."""
    check_auth(x_admin_password)
    if not SNAP_DIR.exists():
        return {"snapshots": []}

    out = []
    for d in sorted(SNAP_DIR.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        ver = "?"
        vf = d / "VERSION"
        if vf.exists():
            try:
                ver = vf.read_text().strip()
            except OSError:
                pass

        size = 0
        try:
            size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        except OSError:
            pass

        out.append({
            "id": d.name,
            "version": ver,
            "createdAt": datetime.fromtimestamp(d.stat().st_mtime).isoformat(timespec="seconds"),
            "sizeMb": round(size / 1048576, 1),
            "hasSettings": (d / "config.json").exists(),
            "hasBot": (d / "bot").exists() or (d / "bot.db").exists(),
        })
    return {"snapshots": out[:20]}


#: لاگ مشترک به‌روزرسانی و بازگردانی — رابط کاربری همین را دنبال می‌کند.
UPDATE_LOG = os.getenv("NEXORA_UPDATE_LOG", "/tmp/nexora-update.log")


@app.post("/api/admin/rollback")
def run_rollback(payload: dict, x_admin_password: str = Header(...)):
    """
    بازگشت به یک نسخه‌ی قبلی از داخل پنل.

    مثل به‌روزرسانی، در پس‌زمینه اجرا می‌شود و لاگش در همان فایل
    نوشته می‌شود تا رابط کاربری بتواند دنبالش کند.
    """
    check_auth(x_admin_password)
    # قالبِ مجاز، نه فهرستِ کاراکترهای ممنوع.
    #
    # نام نسخه‌ها را خودِ اسکریپت با «date +%Y%m%d-%H%M%S» می‌سازد، پس
    # همیشه همین شکل است. فهرستِ ممنوع (قبلاً فقط / و ..) هر چیزی را
    # که در آن فکر نکرده بودیم عبور می‌داد — از جمله کاراکترهای شل.
    snap = str((payload or {}).get("id", "") or "").strip()
    if not _re.fullmatch(r"\d{8}-\d{6}", snap):
        raise HTTPException(status_code=400, detail="شناسه نسخه نامعتبر است")

    target = SNAP_DIR / snap
    if not target.is_dir():
        raise HTTPException(status_code=404, detail="این نسخه پیدا نشد")

    keep = "yes" if (payload or {}).get("keepSettings", True) else "no"

    # مسیر کامل دستور — نه فقط نام.
    #
    # سرویس systemd متغیر PATH محدودی دارد و ممکن است
    # /usr/local/bin در آن نباشد، پس «nexora» پیدا نمی‌شود و
    # دستور بی‌صدا شکست می‌خورد.
    import shutil
    exe = shutil.which("nexora") or "/usr/local/bin/nexora"
    if Path(exe).exists():
        cli_argv = [exe]
    else:
        local = _root_dir() / "nexora-cli.sh"
        if local.exists():
            cli_argv = ["bash", str(local)]
        else:
            raise HTTPException(
                status_code=500,
                detail="دستور nexora پیدا نشد. روی سرور اجرا کنید: nexora doctor")

    log = UPDATE_LOG
    try:
        import subprocess
        # لاگ را پاک می‌کنیم تا رابط کاربری فقط این اجرا را ببیند
        try:
            Path(log).write_text(
                f"[{datetime.now():%H:%M:%S}] بازگشت به نسخه {snap} آغاز شد\n",
                encoding="utf-8")
        except Exception:
            pass

        # بدون شل. آرگومان‌ها فهرست‌اند، پس هیچ مقداری تفسیر نمی‌شود.
        # start_new_session همان کاری را می‌کند که setsid می‌کرد:
        # بستن پنل وسط کار، بازگردانی را نمی‌کشد.
        argv = cli_argv + ["rollback", snap, "--yes", f"--settings={keep}"]

        # نبودِ فایل لاگ نباید جلوی بازگردانی را بگیرد. لاگ برای دیدن
        # است؛ بازگردانی کاری است که باید انجام شود.
        try:
            logf = open(log, "ab")
        except OSError:
            logf = None
        try:
            subprocess.Popen(argv,
                             start_new_session=True,
                             stdin=subprocess.DEVNULL,
                             stdout=logf or subprocess.DEVNULL,
                             stderr=subprocess.STDOUT)
        finally:
            if logf:
                try:
                    logf.close()
                except OSError:
                    pass
        return {"ok": True, "started": snap, "log": log}
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"اجرای بازگشت ناموفق: {str(e)[:200]}")


@app.get("/api/admin/bot/receipt/{order_id}")
def bot_receipt(order_id: int, pw: str = "",
                x_admin_password: str = Header(None)):
    """
    تصویر رسید.

    رمز از هدر یا از پارامتر می‌آید — چون تگ <img> در مرورگر
    نمی‌تواند هدر بفرستد و بدون این، تصویر هرگز نمایش داده نمی‌شود.
    """
    """
    تصویر رسید یک سفارش.

    تلگرام فایل‌ها را با file_id نگه می‌دارد. اینجا آن را به لینک
    موقت تبدیل می‌کنیم، محتوا را می‌گیریم و به‌صورت تصویر برمی‌گردانیم
    تا پنل بتواند نمایش و بزرگ‌نمایی کند.
    """
    check_auth(x_admin_password or pw)
    con = _bot_conn()
    if not con:
        raise HTTPException(status_code=404, detail="دیتابیس ربات موجود نیست")

    try:
        row = con.execute(
            "SELECT o.receipt_type, o.receipt_file, o.receipt_text, o.tenant_id "
            "FROM orders o WHERE o.id=?", (order_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="سفارش پیدا نشد")

        if row["receipt_type"] != "photo" or not row["receipt_file"]:
            raise HTTPException(status_code=404, detail="این سفارش رسید تصویری ندارد")

        # رسیدی که خودمان نگه داشته‌ایم — بدون رفتن به تلگرام.
        # یک قاعده‌ی نمایش، دو منبع: دیسک برای رسیدهای مینی‌اپ،
        # تلگرام برای رسیدهایی که در خودِ گفتگو آمده‌اند.
        _lp = _receipt_local(row["receipt_file"])
        if _lp:
            _blob = _lp.read_bytes()
            _e, _ct = _logo_kind(_blob)
            if _ct:
                return Response(content=_blob, media_type=_ct,
                                headers={"Cache-Control": "private, max-age=60"})
            raise HTTPException(status_code=404, detail="فایل رسید سالم نیست")

        t = con.execute("SELECT bot_token FROM tenants WHERE id=?",
                        (row["tenant_id"],)).fetchone()
        token = t["bot_token"] if t else None
        if not token:
            raise HTTPException(status_code=400, detail="توکن ربات تنظیم نشده است")
    finally:
        con.close()

    try:
        import requests
        from fastapi.responses import Response as FastResponse

        r = requests.get(f"https://api.telegram.org/bot{token}/getFile",
                         params={"file_id": row["receipt_file"]}, timeout=15)
        d = r.json()
        if not d.get("ok"):
            raise HTTPException(status_code=502,
                                detail="تلگرام فایل را برنگرداند")

        path = d["result"]["file_path"]
        img = requests.get(f"https://api.telegram.org/file/bot{token}/{path}",
                           timeout=25)
        if img.status_code != 200:
            raise HTTPException(status_code=502, detail="دریافت تصویر ناموفق بود")

        ext = path.rsplit(".", 1)[-1].lower() if "." in path else "jpg"
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")

        return FastResponse(content=img.content, media_type=mime,
                            headers={"Cache-Control": "private, max-age=600"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"خطا در دریافت رسید: {str(e)[:150]}")


@app.get("/api/admin/bot/subscriber/{tg_id}")
def bot_subscriber_detail(tg_id: int, x_admin_password: str = Header(...)):
    """
    پرونده‌ی کامل یک مشتری: اطلاعات ربات + مصرف زنده از 3x-ui.

    ترافیک از خود پنل خوانده می‌شود نه از کش، چون عددی که به ادمین
    نشان می‌دهیم باید همان چیزی باشد که مشتری می‌بیند.
    """
    check_auth(x_admin_password)

    con = _bot_conn()
    if not con:
        raise HTTPException(status_code=404, detail="دیتابیس ربات موجود نیست")

    try:
        u = con.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        if not u:
            raise HTTPException(status_code=404, detail="کاربر پیدا نشد")
        user = dict(u)

        subs = [dict(r) for r in con.execute(
            "SELECT s.*, p.name AS plan_name FROM subscriptions s "
            "LEFT JOIN plans p ON p.id = s.plan_id "
            "WHERE s.user_id = ? ORDER BY s.created_at DESC", (user["id"],))]

        orders = [dict(r) for r in con.execute(
            "SELECT o.*, p.name AS plan_name FROM orders o "
            "LEFT JOIN plans p ON p.id = o.plan_id "
            "WHERE o.user_id = ? ORDER BY o.created_at DESC LIMIT 20", (user["id"],))]

        coins = [dict(r) for r in con.execute(
            "SELECT * FROM coin_tx WHERE user_id=? ORDER BY created_at DESC LIMIT 15",
            (user["id"],))]

        tenant = con.execute(
            "SELECT panel_url, panel_user, panel_pass, panel_token "
            "FROM tenants WHERE id=?", (user["tenant_id"],)).fetchone()
    finally:
        con.close()

    # ترافیک زنده برای هر اشتراک فعال
    live = {}
    if tenant and tenant["panel_url"]:
        try:
            import sys as _sys
            bd = str(_bot_dir())
            if bd not in _sys.path:
                _sys.path.insert(0, bd)
            from xui import XUI  # noqa: E402

            client = XUI(tenant["panel_url"], tenant["panel_user"],
                         tenant["panel_pass"], tenant["panel_token"])
            for s in subs:
                email = s.get("client_email")
                if not email:
                    continue
                try:
                    t = client.client_traffic(email)
                    if t:
                        if isinstance(t, list):
                            t = t[0] if t else None
                        if t:
                            live[email] = {
                                "up": t.get("up", 0),
                                "down": t.get("down", 0),
                                "total": t.get("total", 0),
                                "expiryTime": t.get("expiryTime", 0),
                                "enable": t.get("enable", True),
                                "inboundId": t.get("inboundId"),
                            }
                except Exception:
                    pass
        except Exception:
            pass

    return {
        "user": user,
        "subscriptions": subs,
        "orders": orders,
        "coinHistory": coins,
        "live": live,
        "liveAvailable": bool(live),
    }


@app.post("/api/admin/bot/message/{tg_id}")
def bot_message_user(tg_id: int, payload: dict,
                     x_admin_password: str = Header(...)):
    """
    پیام مستقیم ادمین به یک کاربر، از طریق ربات.

    بدون این، ادمین برای هر تماسی باید از پنل بیرون می‌رفت و در تلگرام
    دنبال کاربر می‌گشت — و اگر کاربر یوزرنیم نداشت، اصلاً راهی نبود.
    """
    check_auth(x_admin_password)

    text = (payload or {}).get("text") or ""
    text = str(text).strip()
    if not text:
        raise HTTPException(status_code=400, detail="متن پیام خالی است")
    if len(text) > 3500:
        raise HTTPException(status_code=400,
                            detail="متن پیام از ۳۵۰۰ کاراکتر بیشتر است")

    con = _bot_conn()
    if not con:
        raise HTTPException(status_code=404, detail="دیتابیس ربات موجود نیست")
    try:
        u = con.execute("SELECT id, tenant_id, first_name, is_blocked "
                        "FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        if not u:
            raise HTTPException(status_code=404, detail="کاربر پیدا نشد")
        t = con.execute("SELECT bot_token FROM tenants WHERE id=?",
                        (u["tenant_id"],)).fetchone()
    finally:
        con.close()

    token = t["bot_token"] if t else None
    if not token:
        raise HTTPException(status_code=400, detail="توکن ربات تنظیم نشده است")

    # امضای «پیام از پشتیبانی» تا کاربر نداند این پیام خودکار است یا انسان
    body = json.dumps({
        "chat_id": tg_id,
        "text": f"💬 <b>پیام از پشتیبانی</b>\n\n{text}",
        "parse_mode": "HTML",
    }).encode()

    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            res = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode("utf-8")).get("description", "")
        except Exception:
            err = str(e)
        # پرتکرارترین حالت: کاربر ربات را بلاک کرده — این خطای ما نیست
        if "blocked" in err.lower() or "deactivated" in err.lower():
            raise HTTPException(status_code=409,
                                detail="کاربر ربات را بلاک کرده یا حسابش حذف شده")
        raise HTTPException(status_code=400, detail=f"تلگرام: {err[:200]}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ارسال ناموفق: {str(e)[:160]}")

    if not res.get("ok"):
        raise HTTPException(status_code=400,
                            detail=res.get("description") or "ارسال ناموفق")

    return {"ok": True, "sentTo": tg_id}


@app.post("/api/admin/bot/reload")
def bot_reload(x_admin_password: str = Header(...)):
    """
    اعلام به ربات که تنظیمات عوض شده.

    ربات تنظیمات را در هر درخواست تازه می‌خواند، پس تغییرات معمولاً
    فوری اعمال می‌شوند. این endpoint برای مواردی است که ربات چیزی را
    در حافظه نگه داشته — مثل نخِ یک مستاجر که توکنش عوض شده.

    یک فلگ در دیتابیس می‌گذاریم؛ ربات در چرخه‌ی بعدی می‌بیندش و
    خودش را همگام می‌کند. بدون قطعی سرویس.
    """
    check_auth(x_admin_password)
    if not BOT_DB.exists():
        raise HTTPException(status_code=400, detail="دیتابیس ربات موجود نیست")

    con = _bot_rw()
    try:
        con.execute(
            "CREATE TABLE IF NOT EXISTS bot_flags ("
            "  key TEXT PRIMARY KEY,"
            "  value TEXT,"
            "  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        con.execute(
            "INSERT INTO bot_flags (key, value, updated_at) VALUES ('reload', ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
            (str(int(datetime.now().timestamp())),))
        con.commit()
        return {"ok": True, "running": _svc_active()}
    finally:
        con.close()


@app.post("/api/admin/bot/test-connection")
def bot_test_connection(payload: dict, x_admin_password: str = Header(...)):
    """
    تست کامل اتصال به 3x-ui — مرحله به مرحله.

    فقط «وصل شد» کافی نیست. کاربر باید مطمئن شود که ربات واقعاً
    می‌تواند کانفیگ بسازد. پس یک کلاینت آزمایشی می‌سازیم، بررسی
    می‌کنیم، و بلافاصله پاکش می‌کنیم.
    """
    check_auth(x_admin_password)

    bot_dir = _bot_dir()
    if not (bot_dir / "xui.py").exists():
        raise HTTPException(status_code=400, detail="ماژول ربات روی سرور نیست")

    # اطلاعات از payload یا از تنظیمات ذخیره‌شده
    url = (payload or {}).get("panel_url")
    user = (payload or {}).get("panel_user")
    pw = (payload or {}).get("panel_pass")
    token = (payload or {}).get("panel_token")
    inbound = (payload or {}).get("default_inbound")

    if not url or (token and str(token).endswith("…")) or (pw and str(pw).endswith("…")):
        con = _bot_conn()
        if con:
            try:
                row = con.execute(
                    "SELECT * FROM tenants WHERE parent_id IS NULL ORDER BY id LIMIT 1"
                ).fetchone()
                if row:
                    r = dict(row)
                    url = url or r.get("panel_url")
                    user = user or r.get("panel_user")
                    if not pw or str(pw).endswith("…"):
                        pw = r.get("panel_pass")
                    if not token or str(token).endswith("…"):
                        token = r.get("panel_token")
                    inbound = inbound or r.get("default_inbound")
            finally:
                con.close()

    if not url:
        raise HTTPException(status_code=400, detail="آدرس پنل وارد نشده است")

    steps = []

    def step(key, title, ok, detail="", hint=""):
        steps.append({"key": key, "title": title, "ok": ok,
                      "detail": detail, "hint": hint})
        return ok

    import sys as _sys
    if str(bot_dir) not in _sys.path:
        _sys.path.insert(0, str(bot_dir))

    try:
        import importlib
        xmod = importlib.import_module("xui")
        importlib.reload(xmod)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"بارگذاری ماژول ناموفق: {str(e)[:150]}")

    client = xmod.XUI(url, user, pw, token)

    # ۱ — احراز هویت
    try:
        client.login()
        method = "توکن API" if token else "نام کاربری و رمز"
        step("auth", "احراز هویت", True, f"با {method} وارد شد")
    except Exception as e:
        step("auth", "احراز هویت", False, str(e)[:180],
             "آدرس پنل، توکن یا نام کاربری و رمز را بررسی کنید. "
             "آدرس باید شامل پورت و مسیر باشد.")
        return {"ok": False, "steps": steps}

    # ۲ — خواندن inboundها
    inbounds = []
    try:
        inbounds = client.inbounds() or []
        names = [f"#{i.get('id')} {i.get('remark') or i.get('protocol','')}"
                 for i in inbounds[:6]]
        step("inbounds", "خواندن inboundها", bool(inbounds),
             f"{len(inbounds)} inbound: " + " · ".join(names) if inbounds
             else "هیچ inbound فعالی پیدا نشد",
             "" if inbounds else "ابتدا در پنل 3x-ui یک inbound بسازید.")
        if not inbounds:
            return {"ok": False, "steps": steps}
    except Exception as e:
        step("inbounds", "خواندن inboundها", False, str(e)[:180],
             "کاربر پنل باید دسترسی خواندن داشته باشد.")
        return {"ok": False, "steps": steps}

    # ۳ — معماری پنل
    #
    # از نسخه‌ی ۳ به بعد پنل مشخصات OpenAPI خودش را سرو می‌کند.
    # اگر بتوانیم بخوانیمش، دیگر حدس نمی‌زنیم کدام مسیر را صدا بزنیم.
    try:
        routes = client.discover()
    except Exception:
        routes = {}

    if routes:
        modern = any(p.startswith("/panel/api/clients") for p in routes)
        step("api", "مسیرهای API", True,
             f"{len(routes)} مسیر از خود پنل خوانده شد — "
             + ("معماری کلاینت مستقل" if modern else "معماری کلاسیک"))
    else:
        try:
            mode = client.detect_api()
            step("api", "تشخیص نسخه پنل", True,
                 "معماری جدید (۳.۴ به بعد)" if mode == "modern" else "معماری کلاسیک",
                 "مشخصات OpenAPI خوانده نشد — مسیرها با آزمون‌وخطا پیدا می‌شوند")
        except Exception:
            step("api", "تشخیص نسخه پنل", True, "کلاسیک (پیش‌فرض)")

    # ۴ — inbound انتخاب‌شده
    target = None
    if inbound:
        try:
            target = int(inbound)
        except (TypeError, ValueError):
            target = None
    if target is None:
        target = inbounds[0].get("id")
        step("inbound", "inbound پیش‌فرض", True,
             f"#{target} (اولین inbound — در تنظیمات مشخص نشده بود)",
             "بهتر است inbound دلخواهتان را در تنظیمات مشخص کنید.")
    else:
        found = any(int(i.get("id", -1)) == target for i in inbounds)
        if not step("inbound", "inbound پیش‌فرض", found,
                    f"#{target}" if found else f"#{target} در پنل وجود ندارد",
                    "" if found else "شماره‌ی درست را از لیست بالا انتخاب کنید."):
            return {"ok": False, "steps": steps}

    # ۵ — ساخت کلاینت آزمایشی
    import uuid as _uuid
    probe = f"nexora_test_{_uuid.uuid4().hex[:8]}"
    created = False
    try:
        client.add_client(target, probe, gb=1, days=1, ip_limit=1)
        created = True
        step("create", "ساخت کانفیگ آزمایشی", True, f"کلاینت {probe} ساخته شد")
    except Exception as e:
        step("create", "ساخت کانفیگ آزمایشی", False, str(e)[:180],
             "کاربر پنل باید دسترسی نوشتن داشته باشد. "
             "اگر از توکن استفاده می‌کنید، مطمئن شوید توکن محدود نشده باشد.")
        return {"ok": False, "steps": steps}

    # ۶ — خواندن کلاینت ساخته‌شده
    try:
        # آرگومان اول inbound است نه ایمیل — قبلاً ایمیل به‌جای
        # inbound می‌رفت و این مرحله همیشه «خوانده نشد» می‌داد،
        # حتی وقتی کلاینت درست ساخته شده بود.
        found = client.find_client(target, email=probe)
        step("verify", "بازخوانی کانفیگ", bool(found),
             "کلاینت در پنل پیدا شد" if found else "ساخته شد ولی خوانده نشد",
             "" if found else "ممکن است پنل هنوز همگام نشده باشد.")
    except Exception as e:
        step("verify", "بازخوانی کانفیگ", False, str(e)[:180])

    # ۷ — پاکسازی (مهم: نباید کلاینت آشغال بماند)
    if created:
        try:
            # در نسخه‌ی ۳ حذف با ایمیل انجام می‌شود؛ اگر ایمیل را
            # به‌جای uuid بفرستیم مسیرهای درست اصلاً امتحان نمی‌شوند
            # و کلاینت آزمایشی در پنل باقی می‌ماند.
            client.delete_client(target, None, email=probe)
            step("cleanup", "پاکسازی", True, "کلاینت آزمایشی حذف شد")
        except Exception as e:
            step("cleanup", "پاکسازی", False, str(e)[:180],
                 f"کلاینت «{probe}» را دستی از پنل حذف کنید.")

    all_ok = all(s["ok"] for s in steps)
    return {
        "ok": all_ok,
        "steps": steps,
        "inbounds": [{"id": i.get("id"),
                      "remark": i.get("remark") or "",
                      "protocol": i.get("protocol") or "",
                      "port": i.get("port")}
                     for i in inbounds],
    }


@app.get("/api/admin/github")
def github_get(x_admin_password: str = Header(...)):
    """تنظیمات مخزن گیت‌هاب برای به‌روزرسانی."""
    check_auth(x_admin_password)
    f = _root_dir() / ".github"
    repo = ""
    if f.exists():
        try:
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.startswith("GITHUB_REPO="):
                    repo = line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return {"repo": repo, "configured": bool(repo)}


@app.put("/api/admin/github")
def github_put(payload: dict, x_admin_password: str = Header(...)):
    """
    ذخیره‌ی مخزن گیت‌هاب.

    قبل از ذخیره، وجود مخزن و داشتن Release بررسی می‌شود — تا کاربر
    یک آدرس اشتباه ذخیره نکند و بعد در به‌روزرسانی گیر کند.
    """
    check_auth(x_admin_password)
    repo = (payload or {}).get("repo", "").strip()

    # نرمال‌سازی: از URL کامل هم قبول می‌کنیم
    repo = repo.replace("https://github.com/", "").replace("http://github.com/", "")
    repo = repo.rstrip("/").removesuffix(".git")

    if not repo:
        f = _root_dir() / ".github"
        try:
            f.unlink(missing_ok=True)
        except Exception:
            pass
        return {"ok": True, "repo": "", "configured": False}

    if repo.count("/") != 1 or not all(repo.split("/")):
        raise HTTPException(status_code=400,
                            detail="قالب درست: username/repository")

    # بررسی واقعی
    try:
        import urllib.request
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/releases/latest",
            headers={"Accept": "application/vnd.github+json",
                     "User-Agent": "nexora-panel"})
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode())
        tag = data.get("tag_name", "")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise HTTPException(
                status_code=400,
                detail=f"مخزن «{repo}» پیدا نشد یا هیچ Release ندارد. "
                       "مطمئن شوید عمومی است و حداقل یک Release ساخته‌اید.")
        raise HTTPException(status_code=400, detail=f"گیت‌هاب پاسخ نداد: {e.code}")
    except Exception as e:
        raise HTTPException(status_code=400,
                            detail=f"بررسی مخزن ناموفق: {str(e)[:120]}")

    f = _root_dir() / ".github"
    f.write_text(f'GITHUB_REPO="{repo}"\n', encoding="utf-8")
    try:
        os.chmod(f, 0o600)
    except Exception:
        pass

    return {"ok": True, "repo": repo, "configured": True, "latestTag": tag}


# ═══════════════════════════════════════════════════════════
#  حسابداری واسطه‌ها
#
#  گروه‌ها و مصرف واقعی از x-ui.db خوانده می‌شوند (فقط‌خواندنی).
#  نرخ‌ها، پرداخت‌ها و لاگ تمدید در دیتابیس خودمان ذخیره می‌شوند.
# ═══════════════════════════════════════════════════════════

# مسیر دیتابیس x-ui.
#
# اولویت: تنظیمات پنل ← متغیر محیطی ← مسیرهای رایج.
# اگر فقط به متغیر محیطی تکیه کنیم، نصب‌های قدیمی که آن را ندارند
# حسابداری‌شان کار نمی‌کند و کاربر هم راهی برای اصلاحش ندارد.
XUI_CANDIDATES = [
    "/etc/x-ui/x-ui.db",
    "/usr/local/x-ui/x-ui.db",
    "/opt/x-ui/x-ui.db",
    "/etc/x-ui/db/x-ui.db",
]


def _xui_db_path():
    """مسیر فعلی دیتابیس x-ui را برمی‌گرداند."""
    # ۱. تنظیم دستی در پنل.
    #
    # اگر مسیر دستی وجود نداشته باشد (غلط تایپی، فاصله‌ی اضافه،
    # جابه‌جایی فایل) نباید همان‌جا شکست بخوریم — بقیه‌ی راه‌ها را
    # امتحان می‌کنیم. وگرنه یک اشتباه کوچک، حسابداری را برای همیشه
    # از کار می‌اندازد.
    try:
        cfg = load_config()
        manual = ((cfg.get("advanced") or {}).get("xuiDbPath") or "").strip()
        # کاراکترهای نامرئی که هنگام کپی‌پیست می‌آیند
        manual = manual.strip("\u200c\u200e\u200f\ufeff'\" ")
        if manual and Path(manual).exists():
            return Path(manual)
    except Exception:
        manual = ""

    # ۲. متغیر محیطی
    env = os.getenv("XUI_DB_PATH", "").strip()
    if env and Path(env).exists():
        return Path(env)

    # ۳. مسیرهای رایج — تازه‌ترین، نه اولینِ فهرست.
    #
    # چرا این‌طور شد: نصب‌های واقعی بیش از یک `x-ui.db` دارند. نصبِ
    # دوباره، مهاجرت از یک مسیر به مسیر دیگر، یا بک‌آپی که کنارش
    # مانده — و فهرستِ بالا اولینِ موجود را برمی‌داشت.
    #
    # نتیجه‌اش بی‌صدا بود و از بیرون شبیهِ خرابیِ حسابداری: پنل عددِ
    # یک فایلِ مرده را می‌خواند که هیچ‌وقت عوض نمی‌شد، و مالک
    # می‌دید مصرف «آپدیت نمی‌شود» و با پنلِ خودِ x-ui هم نمی‌خواند.
    #
    # x-ui هر چند ثانیه روی فایلِ زنده می‌نویسد، پس تازه‌ترین
    # `mtime` همان فایلِ زنده است. این حدس نیست؛ قابلِ سنجش است.
    found = []
    for p in XUI_CANDIDATES:
        pp = Path(p)
        try:
            if pp.exists():
                found.append((pp.stat().st_mtime, pp))
        except OSError:
            continue
    if found:
        found.sort(key=lambda x: x[0], reverse=True)
        return found[0][1]

    # هیچ‌کدام پیدا نشد — مسیری که کاربر انتظار دارد را برمی‌گردانیم
    # تا پیام خطا به همان اشاره کند، نه به یک مسیر پیش‌فرض گیج‌کننده.
    if manual:
        return Path(manual)
    if env:
        return Path(env)
    return Path(XUI_CANDIDATES[0])
def _xui_db_candidates():
    """
    همه‌ی فایل‌های `x-ui.db` که پیدا می‌شوند، با زمانِ آخرین نوشتن.

    برای تشخیص هم هست و هم برای هشدار: وقتی بیش از یکی هست، یعنی
    ممکن است پنل به فایلِ اشتباه نگاه کند — و آن خرابی بی‌صداست.
    """
    out = []
    seen = set()
    for p in XUI_CANDIDATES:
        pp = Path(p)
        try:
            if not pp.exists():
                continue
            key = str(pp.resolve())
            if key in seen:
                continue
            seen.add(key)
            st = pp.stat()
            out.append({"path": str(pp), "mtime": st.st_mtime,
                        "size": st.st_size})
        except OSError:
            continue
    out.sort(key=lambda d: d["mtime"], reverse=True)
    return out


BILLING_DB = Path(os.getenv("BILLING_DB_PATH", str(CONFIG_PATH.parent / "billing.db")))


def _xui_conn():
    """
    اتصال فقط‌خواندنی به دیتابیس x-ui.

    برمی‌گرداند: (اتصال, پیام‌خطا)
    خطای واقعی برگردانده می‌شود نه None خالی — چون «پیدا نشد» و
    «مجوز ندارد» و «قفل است» سه مشکل کاملاً متفاوت‌اند و کاربر باید
    بداند کدام است تا بتواند رفعش کند.
    """
    xdb = _xui_db_path()

    if not xdb.exists():
        parent = xdb.parent
        if not parent.exists():
            return None, (f"پوشه‌ی {parent} وجود ندارد. "
                          "مطمئن شوید ۳x-ui روی همین سرور نصب است.")
        return None, f"فایل {xdb.name} در {parent} پیدا نشد"

    if not os.access(xdb, os.R_OK):
        try:
            st = xdb.stat()
            perm = oct(st.st_mode)[-3:]
        except Exception:
            perm = "?"
        return None, (f"فایل هست ولی پنل اجازه‌ی خواندنش را ندارد "
                      f"(مجوز فعلی: {perm}). روی سرور اجرا کنید: "
                      f"chmod +r {xdb}")

    import sqlite3

    def _try_open(uri):
        con = sqlite3.connect(uri, uri=True, timeout=8)
        con.row_factory = sqlite3.Row
        # SQLite تنبل است: تا به جدول‌ها دست نزنی، فایل خراب را هم
        # بی‌صدا قبول می‌کند. پس فهرست جدول‌ها را می‌خوانیم.
        con.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
        return con

    # فایل‌های جانبی WAL هم باید خواندنی باشند، وگرنه SQLite کل
    # دیتابیس را باز نمی‌کند. این را قبل از تلاش بررسی می‌کنیم چون
    # پیام خطای خودش گمراه‌کننده است.
    for suffix in ("-wal", "-shm"):
        side = xdb.with_name(xdb.name + suffix)
        if side.exists() and not os.access(side, os.R_OK):
            return None, (f"فایل {side.name} خواندنی نیست. ۳x-ui در حالت WAL است و "
                          f"این فایل هم لازم است. اجرا کنید: "
                          f"chmod +r {xdb.parent}/{xdb.name}*")

    try:
        # حالت اول: فقط‌خواندنی معمولی
        return _try_open(f"file:{xdb}?mode=ro"), None
    except sqlite3.OperationalError as first:
        # اگر دیتابیس در حالت WAL باشد، mode=ro به فایل‌های جانبی
        # (-wal و -shm) هم نیاز دارد و اگر آن‌ها خواندنی نباشند
        # شکست می‌خورد. immutable=1 این وابستگی را دور می‌زند.
        #
        # امن است چون x-ui در حال نوشتن است ولی ما فقط می‌خوانیم؛
        # بدترین حالت این است که چند ثانیه داده‌ی قدیمی‌تر ببینیم.
        # immutable فقط وقتی درست است که فایل -wal وجود نداشته باشد،
        # وگرنه داده‌های اخیر دیده نمی‌شوند و جدول‌ها خالی به نظر می‌رسند.
        if not xdb.with_name(xdb.name + "-wal").exists():
            try:
                return _try_open(f"file:{xdb}?immutable=1"), None
            except Exception:
                pass

        msg = str(first)
        low = msg.lower()
        if "locked" in low:
            return None, "دیتابیس ۳x-ui قفل است. چند لحظه بعد دوباره امتحان کنید."
        if "unable to open" in low:
            wal = xdb.with_name(xdb.name + "-wal")
            hint = ""
            if wal.exists() and not os.access(wal, os.R_OK):
                hint = f" فایل {wal.name} هم باید خواندنی باشد: chmod +r {wal}"
            return None, (f"باز کردن دیتابیس ممکن نشد. معمولاً یعنی پنل به پوشه‌ی "
                          f"{xdb.parent} دسترسی ندارد: chmod o+x {xdb.parent}" + hint)
        if "not a database" in low:
            return None, f"فایل {xdb.name} یک دیتابیس SQLite معتبر نیست"
        return None, f"باز کردن دیتابیس ناموفق: {msg[:120]}"
    except sqlite3.OperationalError as e:
        msg = str(e)
        if "locked" in msg.lower():
            return None, "دیتابیس ۳x-ui قفل است. چند لحظه بعد دوباره امتحان کنید."
        if "not a database" in msg.lower():
            return None, f"فایل {xdb} یک دیتابیس SQLite معتبر نیست"
        return None, f"باز کردن دیتابیس ناموفق: {msg[:120]}"
    except sqlite3.DatabaseError as e:
        if "not a database" in str(e).lower():
            return None, f"فایل {xdb.name} یک دیتابیس SQLite معتبر نیست"
        return None, f"خواندن دیتابیس ناموفق: {str(e)[:110]}"
    except Exception as e:
        return None, f"خطای غیرمنتظره: {type(e).__name__}: {str(e)[:110]}"


def _billing_conn():
    """
    دیتابیس حسابداری — جدا از x-ui تا هرگز به آن دست نزنیم.

    اگر فایل خراب باشد (قطع برق وسط نوشتن، کپی ناقص) کنارش
    می‌گذاریم و از نو می‌سازیم. از دست رفتن نرخ‌ها بد است، ولی
    از کار افتادن کل بخش حسابداری بدتر.
    """
    import sqlite3
    BILLING_DB.parent.mkdir(parents=True, exist_ok=True)

    def _open():
        con = sqlite3.connect(str(BILLING_DB), timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
        return con

    try:
        con = _open()
    except sqlite3.DatabaseError:
        # فایل سالم نیست — کنار می‌گذاریم تا قابل بازیابی دستی بماند
        try:
            broken = BILLING_DB.with_name(
                f"{BILLING_DB.stem}-corrupt-{datetime.now():%Y%m%d-%H%M%S}.db")
            BILLING_DB.replace(broken)
        except Exception:
            try:
                BILLING_DB.unlink(missing_ok=True)
            except Exception:
                pass
        con = _open()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS group_config (
            group_key   TEXT PRIMARY KEY,
            label       TEXT,
            billable    INTEGER DEFAULT 0,
            rates         TEXT DEFAULT '[]',
            per_gb        INTEGER DEFAULT 0,
            period_days   INTEGER DEFAULT 30,
            period_start  TEXT,
            settled_until TEXT,
            note          TEXT,
            updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS payments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            group_key   TEXT NOT NULL,
            amount      INTEGER NOT NULL,
            paid_at     TEXT NOT NULL,
            note        TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );
        -- اولین باری که پنل هر کلاینت را دید.
        --
        -- نسخه‌های قدیمی x-ui تاریخ ساخت کلاینت را نگه نمی‌دارند، و آن
        -- اطلاعات جای دیگری هم وجود ندارد — پس هر کانفیگ «یک ماهه»
        -- حساب می‌شد و واسطه‌ای که دو سال کار کرده، یک ماه صورت‌حساب
        -- می‌گرفت.
        --
        -- گذشته را نمی‌شود ساخت، ولی از امروز به بعد می‌شود ثبت کرد.
        -- این کف مطمئنی می‌دهد: «دست‌کم از این تاریخ می‌شناسیمش».
        CREATE TABLE IF NOT EXISTS client_seen (
            email      TEXT PRIMARY KEY,
            group_key  TEXT,
            first_seen TEXT NOT NULL,
            last_seen  TEXT,
            -- آخرین انقضایی که از این کلاینت دیدیم.
            --
            -- بدون این، تمدید اصلاً قابل تشخیص نیست: پنل دست واسطه
            -- است، او مستقیم در x-ui تمدید می‌کند، و x-ui هیچ
            -- تاریخچه‌ای نگه نمی‌دارد. تنها راه فهمیدنش این است که
            -- خودمان انقضا را به خاطر بسپاریم و دفعه‌ی بعد مقایسه
            -- کنیم — اگر جلو رفته باشد، تمدید شده.
            last_expiry INTEGER,

            -- مصرف، و همان قاعده برای ترافیک.
            --
            -- x-ui با ریست‌شدنِ ترافیک `up` و `down` را صفر می‌کند و
            -- عددِ قبلی برای همیشه می‌رود. اندازه‌گیری‌شده: کانفیگِ
            -- ۵۰۰ گیگی که ۵۰۰ مصرف کرد، ریست خورد، و ۴۵۰ دیگر مصرف
            -- کرد — پنل ۴۵۰ نشان می‌داد و ۵۰۰ گیگ بی‌صدا گم شده بود.
            --
            -- روی صورتحساب یعنی واسطه‌ای که با ریست‌زدن دو برابر حجم
            -- فروخته، یک‌بار پول می‌دهد.
            --
            -- `used_before` جمعِ دوره‌های ریست‌شده است و `last_used`
            -- مبنای مقایسه. افتادنِ عدد یعنی ریست.
            last_used   INTEGER,
            used_before INTEGER DEFAULT 0
        );

        -- لاگ تمدید: x-ui تاریخچه ندارد، پس از امروز خودمان ثبت می‌کنیم
        CREATE TABLE IF NOT EXISTS renewals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT NOT NULL,
            group_key   TEXT,
            months      INTEGER DEFAULT 1,
            gb          INTEGER,
            source      TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );
        -- هزینه‌ها: سرور خارج، سرور ایران، خرید حجم، دامنه و بقیه.
        -- بدون این، «درآمد» عدد بی‌معنایی است؛ سود آن چیزی است که
        -- بعد از کم‌کردن اینها می‌ماند.
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            kind        TEXT NOT NULL,      -- server_abroad | server_iran | traffic | domain | other
            label       TEXT NOT NULL,
            amount      REAL NOT NULL,      -- به واحد currency
            currency    TEXT DEFAULT 'IRT', -- IRT | EUR | USD
            -- مبلغ تومانیِ *لحظه‌ی خرید*. عمداً ذخیره می‌شود و دوباره
            -- محاسبه نمی‌شود: اگر هر بار با نرخ روز حساب کنیم، هزینه‌ی
            -- ماه پیش با تکان‌خوردن بازار عوض می‌شود.
            amount_irt  INTEGER,
            fx_rate     INTEGER,
            fx_source   TEXT,
            gb          INTEGER,            -- برای خرید حجم
            recurring   TEXT DEFAULT 'once',-- once | monthly | yearly
            spent_at    TEXT NOT NULL,
            note        TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );
        -- کانفیگ‌هایی که پاک شدند در حالی که بدهی داشتند.
        --
        -- صورتحساب از فهرستِ *زنده‌ی* x-ui خوانده می‌شود، پس ردیفی که
        -- پاک شود کاملاً از فاکتور غیب می‌شود — چه نماینده پاکش کند
        -- چه خودِ مالک. این یعنی «حذف» می‌تواند راه فرار از پرداخت
        -- باشد، درست همان چیزی که مالک درباره‌ی انقضا هشدار داد.
        --
        -- ردیف‌های این جدول عدد را عوض نمی‌کنند؛ فقط می‌گویند چه چیزی
        -- و با چه مبلغی از فاکتور بیرون رفت، تا تصمیمش با مالک باشد
        -- نه با سکوت.
        CREATE TABLE IF NOT EXISTS deleted_clients (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT NOT NULL,
            group_key   TEXT,
            deleted_at  TEXT NOT NULL,
            months      REAL DEFAULT 0,
            amount      INTEGER DEFAULT 0,
            gb          INTEGER,
            used        INTEGER,
            by_whom     TEXT,
            note        TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_delcl_group
            ON deleted_clients(group_key, deleted_at);

        CREATE INDEX IF NOT EXISTS idx_pay_group ON payments(group_key);
        CREATE INDEX IF NOT EXISTS idx_ren_email ON renewals(email);
        CREATE INDEX IF NOT EXISTS idx_exp_date ON expenses(spent_at);
        CREATE INDEX IF NOT EXISTS idx_exp_kind ON expenses(kind);
    """)
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(group_config)")}
        for col, decl in (("per_gb", "INTEGER DEFAULT 0"),
                          ("period_days", "INTEGER DEFAULT 30"),
                          ("period_start", "TEXT"),
                          ("settled_until", "TEXT")):
            if col not in cols:
                con.execute(f"ALTER TABLE group_config ADD COLUMN {col} {decl}")
    except Exception:
        pass

    con.commit()
    return con


def _read_xui_clients():
    """
    همه‌ی کانفیگ‌ها با گروه و مصرف واقعی.

    نسخه‌ی ۳.۵ ساختار تمیزی دارد:
      clients.group_name  ← نام گروه، مستقیم روی خود کلاینت
      client_groups       ← فهرست گروه‌ها (برای نمایش گروه‌های خالی)
      client_traffics     ← مصرف واقعی

    نسخه‌های قدیمی‌تر گروه ندارند و کلاینت داخل JSON اینباند است؛
    آن حالت هم پشتیبانی می‌شود تا پنل روی هر نسخه‌ای کار کند.
    """
    con, cerr = _xui_conn()
    if not con:
        return None, None, cerr or f"دیتابیس x-ui در {_xui_db_path()} در دسترس نیست"

    try:
        tables = {r["name"] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}

        # مصرف واقعی — تنها جایی که عدد درست دارد
        traffic = {}
        if "client_traffics" in tables:
            try:
                for r in con.execute(
                    "SELECT email, up, down, expiry_time, enable FROM client_traffics"
                ):
                    traffic[r["email"]] = dict(r)
            except Exception as e:
                return None, None, f"خواندن client_traffics ناموفق: {str(e)[:110]}"

        # فهرست گروه‌ها — حتی آن‌هایی که هنوز کاربری ندارند
        known_groups = []
        if "client_groups" in tables:
            try:
                known_groups = [r["name"] for r in con.execute(
                    "SELECT name FROM client_groups ORDER BY id")]
            except Exception:
                pass

        rows = []

        # ── نسخه‌ی ۳.۵: جدول مستقل clients ──
        if "clients" in tables:
            cols = {r[1] for r in con.execute("PRAGMA table_info(clients)")}
            sel = ["email", "total_gb", "expiry_time", "enable", "created_at"]
            for extra in ("limit_ip", "sub_id", "tg_id", "updated_at", "reset"):
                if extra in cols:
                    sel.append(extra)
            if "group_name" in cols:
                sel.append("group_name")
            if "comment" in cols:
                sel.append("comment")
            try:
                for r in con.execute(f"SELECT {','.join(sel)} FROM clients"):
                    d = dict(r)
                    rows.append({
                        "email": d.get("email"),
                        "group": (d.get("group_name") or "").strip() or "بدون گروه",
                        "totalGB": int(d.get("total_gb") or 0),
                        "expiry": int(d.get("expiry_time") or 0),
                        "enable": bool(d.get("enable")),
                        "createdAt": d.get("created_at"),
                        "limitIp": int(d.get("limit_ip") or 0),
                        "subId": d.get("sub_id") or "",
                        "tgId": d.get("tg_id") or 0,
                        "updatedAt": d.get("updated_at"),
                        "resetCount": int(d.get("reset") or 0),
                        "comment": d.get("comment") or "",
                    })
            except Exception as e:
                return None, None, f"خواندن clients ناموفق: {str(e)[:110]}"

        # ── نسخه‌ی کلاسیک: کلاینت داخل JSON اینباند ──
        elif "inbounds" in tables:
            try:
                for r in con.execute("SELECT id, remark, settings FROM inbounds"):
                    try:
                        st = json.loads(r["settings"] or "{}")
                    except (json.JSONDecodeError, TypeError):
                        continue
                    for cl in st.get("clients", []):
                        rows.append({
                            "email": cl.get("email"),
                            "group": (r["remark"] or "").strip() or "بدون گروه",
                            "totalGB": int(cl.get("totalGB") or 0),
                            "expiry": int(cl.get("expiryTime") or 0),
                            "enable": bool(cl.get("enable", True)),
                            "createdAt": None,
                            "limitIp": int(cl.get("limitIp") or 0),
                            "comment": "",
                        })
            except Exception as e:
                return None, None, f"خواندن اینباندها ناموفق: {str(e)[:110]}"
        else:
            return None, None, "جدول کلاینت‌ها پیدا نشد — نسخه‌ی x-ui پشتیبانی نمی‌شود"

        # مصرف را می‌چسبانیم
        out = []
        for r in rows:
            em = r.get("email")
            if not em:
                continue
            t = traffic.get(em, {})
            r["used"] = int((t.get("up") or 0) + (t.get("down") or 0))
            # مصرفِ جمع‌شده‌ی همه‌ی دوره‌ها. این‌جا فقط پایه‌اش گذاشته
            # می‌شود (برابرِ دوره‌ی جاری)؛ `_attach_total_usage` مقدارِ
            # دوره‌های ریست‌شده را رویش می‌گذارد.
            #
            # چرا همیشه ست می‌شود: تا هیچ صداکننده‌ای مجبور نباشد
            # `.get()` بنویسد و هیچ‌کدام بی‌صدا به `used` برنگردند.
            r["usedTotal"] = r["used"]
            if not r.get("expiry"):
                r["expiry"] = int(t.get("expiry_time") or 0)
            out.append(r)

        return out, known_groups, None
    finally:
        con.close()


# ═══════════════════════════════════════════════════════════
#  محاسبات حسابداری
#
#  هر عددی که اینجا حساب می‌شود روی فاکتور واسطه می‌رود، پس
#  گرد کردن و حالت‌های لبه باید صریح و قابل توضیح باشند.
# ═══════════════════════════════════════════════════════════

TEHRAN_OFFSET = 3.5 * 3600      # UTC+3:30


def _epoch_ms(v):
    """
    هر شکلی از تاریخ را به میلی‌ثانیه‌ی epoch تبدیل می‌کند، یا None.

    لازم است چون x-ui در نسخه‌های مختلف created_at را جور دیگری
    نگه می‌دارد: گاهی عدد ثانیه، گاهی عدد میلی‌ثانیه، و گاهی متنِ
    «۲۰۲۴-۰۳-۱۱ ۰۹:۲۲:۰۰». هر کد که فرض کند فقط یکی از این‌هاست،
    روی نصف نصب‌ها می‌شکند.
    """
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        f = float(v)
        if f <= 0:
            return None
        # زیر ۱e11 یعنی ثانیه است، نه میلی‌ثانیه
        return f * (1000 if f < 1e11 else 1)
    try:
        txt = str(v).strip().replace("Z", "+00:00")
        if txt.isdigit():
            return _epoch_ms(int(txt))
        from datetime import datetime as _dt
        return _dt.fromisoformat(txt[:19]).timestamp() * 1000
    except (ValueError, TypeError):
        return None


def _months_from_days(days):
    """
    تعداد ماه‌های صورتحساب از تعداد روز. نیم‌ماه به بالا.

    چرا round() ساده کافی نبود:

        round(9.5)  == 10
        round(10.5) == 10      ← همین
        round(11.5) == 12

    پایتون «گرد کردن بانکی» می‌کند و نیم را به نزدیک‌ترین عدد زوج
    می‌برد. یعنی دو کانفیگ که هر دو دقیقاً نیم‌ماه اضافه دارند،
    بسته به اینکه عدد ماهشان زوج است یا فرد، دو جور حساب می‌شوند.
    برای صورتحساب این قابل دفاع نیست.

    اپسیلون هم لازم است: مرزِ دقیق نیم‌ماه با اختلاف کسری از ثانیه
    این‌ور و آن‌ور می‌شود (۲۸۵ روز = دقیقاً ۹.۵ ماه)، و بدون آن یک
    ثانیه فرقِ بی‌اهمیت در تاریخ ساخت، یک ماه کم یا زیاد می‌کرد.
    """
    import math
    if days is None:
        return 1
    try:
        return max(1, int(math.floor(float(days) / 30.0 + 0.5 + 1e-6)))
    except (TypeError, ValueError):
        return 1


def _date_ms(d):
    """
    نیمه‌شبِ یک تاریخ به میلی‌ثانیه — بدون وابستگی به منطقه‌ی زمانی ماشین.

    جایگزین strftime("%s") که افزونه‌ی glibc است: روی ویندوز و
    هر libc دیگری ValueError می‌دهد و تست‌ها هم آن را نمی‌گرفتند،
    چون تا پیش از این هیچ‌وقت به آن خط نمی‌رسیدیم.
    """
    from datetime import datetime as _dt, timezone as _tz
    return int(_dt(d.year, d.month, d.day, tzinfo=_tz.utc).timestamp() * 1000)


def _to_jalali(epoch_ms):
    """
    تاریخ به شمسی، به وقت تهران.

    ورودی می‌تواند عدد یا متن باشد — قبلاً فقط عدد را می‌پذیرفت و
    با متن TypeError می‌داد. صفحه‌ی «صورتحساب دوره» دقیقاً همین
    مقدار را خام می‌فرستاد، پس روی هر x-ui که created_at را متنی
    ذخیره می‌کند، آن صفحه با خطای ۵۰۰ می‌افتاد.

    برمی‌گرداند: (شمسی, میلادی) یا (None, None) اگر مقدار معنادار نباشد.
    """
    epoch_ms = _epoch_ms(epoch_ms)
    if not epoch_ms or epoch_ms <= 0:
        return None, None
    try:
        from datetime import datetime as _dt, timezone as _tz, timedelta as _td
        d = _dt.fromtimestamp(epoch_ms / 1000, _tz.utc) + _td(seconds=TEHRAN_OFFSET)
        try:
            import jdatetime
            j = jdatetime.date.fromgregorian(date=d.date())
            return f"{j.year:04d}/{j.month:02d}/{j.day:02d}", d.strftime("%Y-%m-%d")
        except ImportError:
            return None, d.strftime("%Y-%m-%d")
    except Exception:
        return None, None


def _duration_days(created, expiry):
    """
    مدت اشتراک به روز.

    اگر یکی از دو تاریخ نباشد، None برمی‌گردد — نه صفر، چون صفر
    یعنی «مدت صفر» و این با «نمی‌دانیم» فرق دارد.

    هر دو ورودی از _epoch_ms رد می‌شوند: created در x-ui معمولاً متن
    است و float("2024-09-12 10:00:00") خطا می‌داد، پس این تابع برای
    *همه‌ی* کلاینت‌ها None برمی‌گرداند و ستون «مدت» در صورتحساب
    گروه همیشه خالی بود.
    """
    c0 = _epoch_ms(created)
    e0 = _epoch_ms(expiry)
    if not c0 or not e0:
        return None
    days = (e0 - c0) / 86400000.0
    return round(days, 1) if days > 0 else None


def _usage_percent(used_bytes, quota_raw):
    """
    درصد مصرف. برای پلن نامحدود None برمی‌گردد چون درصدی از
    بی‌نهایت معنا ندارد.

    `quota_raw` همان چیزی است که x-ui می‌دهد — و x-ui گاهی بایت
    می‌دهد و گاهی خودِ عددِ گیگ. پس از `_gb_of` رد می‌شود، همان
    هسته‌ای که بقیه‌ی حسابداری هم از آن می‌گذرد.

    چرا این‌جا و نه در صداکننده‌ها: هر چهار صداکننده مقدارِ خامِ
    x-ui را می‌دادند انگار بایت است. روی نصبی که `total_gb` عددِ
    گیگ نگه می‌دارد، نتیجه‌اش این بود:

        used=450GB، quota=500  →  ۹۶٬۶۳۶٬۷۶۴٬۱۶۰٪

    و در مینی‌اپ، `gb` و `usagePct` دو خط فاصله داشتند و همان یک
    مقدار در یکی از `_gb_of` رد می‌شد و در دیگری نه.
    """
    gb = _gb_of(quota_raw)
    if gb <= 0:
        return None
    return round(used_bytes * 100.0 / (gb * (1024 ** 3)))


def _start_ms(cl, since=None, first_seen=None):
    """
    مبدأ زمانی یک کانفیگ، و اینکه از کجا آمده.

    شمارش ماه و تاریخ‌گذاری تمدیدها باید از *یک* مبدأ حساب کنند.
    وقتی هر کدام مبدأ خودش را داشت، صورتحساب کلی و صورتحساب دوره‌ای
    دو عدد متفاوت می‌دادند و معلوم نبود کدام درست است.

    برمی‌گرداند: (میلی‌ثانیه یا None, نام منبع)
    """
    ms = _epoch_ms(cl.get("createdAt"))
    if ms is not None:
        return ms, "ساخت"
    ms = _epoch_ms(since)
    if ms is not None:
        return ms, "شروع گروه"
    ms = _epoch_ms(first_seen)
    if ms is not None:
        return ms, "اولین‌دید"
    return None, "پیش‌فرض"


def _renewal_dates(cl, logged_rows, months=None, since=None, first_seen=None):
    """
    تاریخِ هر تمدید — دقیقاً به تعدادی که _months_for شمرده است.

    دو منبع داریم و هیچ‌کدام تنهایی کافی نیست:

      ثبت‌شده  تمدیدهایی که خودِ نکسورا دیده. تاریخ واقعی دارند،
               ولی فقط از روزی که نصب شده به بعد.
      تخمینی   بقیه — از فاصله‌ی ساخت تا انقضا. فرض این است که هر
               تمدید سر ماه انجام شده: ایجاد + ۳۰ روز، + ۶۰ روز، …

    چرا شمارش دیگر این‌جا انجام نمی‌شود:
        این تابع اگر حتی *یک* تمدیدِ ثبت‌شده می‌دید، بقیه را دور
        می‌ریخت و فقط همان را برمی‌گرداند. کانفیگی با دو سال سابقه و
        یک تمدید ثبت‌شده، در صورتحساب کلی ۲۵ ماه بود و در صورتحساب
        دوره‌ای یک تمدید — دو عدد از یک واقعیت.

        حالا تعداد از _months_for می‌آید و این‌جا فقط *تاریخ* گذاشته
        می‌شود. ماه‌هایی که ردی از آن‌ها نداریم مالِ گذشته‌اند: ثبت از
        روز نصب شروع شده، پس ثبت‌شده‌ها تازه‌ترین‌ها هستند و تخمین‌ها
        جای ماه‌های اول را می‌گیرند.

    و چرا هر ردیفِ ثبت‌شده به اندازه‌ی months خودش باز می‌شود:
        تمدید سه‌ماهه سه ماه صورتحساب است، نه یکی. قبلاً هر ردیف یک
        تمدید حساب می‌شد.
    """
    email = cl.get("email")
    real = []
    for r in (logged_rows or []):
        if r.get("email") != email:
            continue
        d = (r.get("created_at") or "")[:10]
        if not d:
            continue
        try:
            n = max(1, int(r.get("months") or 1))
        except (TypeError, ValueError):
            n = 1
        real.extend([(d, "قطعی")] * n)
    real.sort()

    # created ممکن است متن باشد. قبلاً float(created) بود و با متن
    # ValueError می‌داد، پس این تابع خالی برمی‌گشت — یعنی کانفیگی که
    # دو سال تمدید شده، در صورتحساب *صفر* تمدید داشت و تقریباً کل
    # مبلغ از قلم می‌افتاد.
    c0, _src = _start_ms(cl, since, first_seen)
    e0 = _epoch_ms(cl.get("expiry") or 0)

    if months is None:
        if c0 is None or not e0 or e0 <= 0:
            return real
        months = max(1 + len(real),
                     _months_from_days((e0 - c0) / 86400000.0))

    need = max(0, int(months) - 1)
    if len(real) >= need:
        return real[len(real) - need:]
    if c0 is None:
        return real

    out = []
    for i in range(1, need - len(real) + 1):
        _j, g = _to_jalali(int(c0 + i * 30 * 86400000))
        if g:
            out.append((g, "تخمینی"))
    return out + real


def _rows_by_email(logged_rows):
    """
    ردیف‌های تمدید، گروه‌شده بر اساس ایمیل.

    بدون این، هر کلاینت کل جدول تمدیدها را می‌پیمود — روی ۲۵۷ کانفیگ
    یعنی ۲۵۷ پیمایش کامل، در تابعی که هر بار باز کردن صفحه صدا زده
    می‌شود.
    """
    out = {}
    for r in (logged_rows or []):
        out.setdefault(r.get("email"), []).append(r)
    return out


def _period_share(cl, logged, rows, since, group_start=None, first_seen=None):
    """
    از عمر این کانفیگ، چند ماهش روی صورتحسابِ *این دوره* می‌آید.

    برمی‌گرداند:
        (ماهِ این دوره, ماهِ کل, تمدیدِ این دوره, در دوره ساخته شده؟,
         منبع, انحراف)

    چرا یک تابع مشترک:
        صورتحساب و نمای کلی هر کدام جدا حساب می‌کردند. وقتی صورتحساب
        «تسویه‌شده تا» را رعایت کرد و نمای کلی نکرد، داشبورد زیر تیتر
        «کل بدهی دوره» عدد کلِ عمر را نشان می‌داد و فاکتور عدد دوره را
        — دو رقم برای یک واقعیت، و آن‌که برچسبِ «دوره» داشت غلط بود.

        هر جای تازه‌ای هم که بدهی حساب می‌کند باید از همین‌جا بگیرد.
    """
    months, kind, drift = _months_for(cl, logged, since=group_start,
                                      first_seen=first_seen)
    if not since:
        return months, months, months - 1, True, kind, drift

    today = datetime.now().strftime("%Y-%m-%d")
    _cj, created_g = _to_jalali(cl.get("createdAt"))
    base_g = created_g or (first_seen or "")[:10]
    is_new = bool(base_g) and since <= base_g <= today

    dates = _renewal_dates(cl, rows, months,
                           since=group_start, first_seen=first_seen)

    # هر ماه یک‌بار، در همان دوره‌ای که **سپری شده**.
    #
    # شرط قبلاً فقط `d >= since` بود، بدون سقف. `_renewal_dates` برای
    # کانفیگی که تا ۱۴۰۶ اعتبار دارد، مرزهای ماهانه را تا همان‌جا جلو
    # می‌برد — و آن تاریخ‌ها همیشه از «تسویه‌شده تا» جلوترند. پس هر
    # دوره دوباره شمرده می‌شدند.
    #
    # اندازه‌گیری‌شده روی یک گروه واقعی: ۵۸ ماه در دوره‌ی اول، ۴۱ ماه
    # در دوره‌ی دوم که **هر ۴۱ تایش قبلاً هم شمرده شده بود**، و ۳۰ ماه
    # که در هر سه دوره آمدند. مالک بر اساس همین فاکتورها دو بار پول
    # گرفت.
    #
    # چرا «سپری‌شده» و نه «فروخته‌شده»:
    #     مدل «کلِ دوره را موقع فروش حساب کن» هم درست است، ولی برای
    #     تکرارنشدن باید به خاطر بسپارد کدام ماه‌های آینده قبلاً روی
    #     فاکتور رفته‌اند — و «تسویه‌شده تا» که یک تاریخ است نمی‌تواند
    #     این را نگه دارد. با شمردنِ ماهِ سپری‌شده، جمعِ کلِ عمرِ
    #     کانفیگ همان عدد است، فقط درست پخش می‌شود و هیچ ماهی دو بار
    #     نمی‌آید.
    ren_in = sum(1 for d, _k in dates if since <= d <= today)
    return (1 if is_new else 0) + ren_in, months, ren_in, is_new, kind, drift


def _period_bounds(conf, ref=None):
    """
    ابتدا و انتهای دوره‌ی جاری یک واسطه.

    دوره از تاریخ شروعی که مدیر تعیین کرده جلو می‌رود، به طول
    period_days. اگر شروعی تعریف نشده باشد، از اول ماه میلادی
    جاری حساب می‌شود.
    """
    from datetime import date, timedelta

    today = ref or date.today()
    length = max(1, int(conf.get("period_days") or 30))

    start_str = (conf.get("period_start") or "").strip()
    if start_str:
        try:
            anchor = date.fromisoformat(start_str[:10])
        except ValueError:
            anchor = None
    else:
        anchor = None

    if anchor is None:
        # بدون لنگر، دوره باید شامل امروز باشد و به عقب برسد —
        # نه از اول ماه میلادی. وگرنه در روزهای اول ماه، کانفیگ‌های
        # چند روز پیش بیرون می‌مانند و صورتحساب خالی درمی‌آید.
        anchor = today - timedelta(days=length - 1)

    if anchor > today:
        return anchor, anchor + timedelta(days=length)

    # چند دوره از لنگر گذشته؟
    elapsed = (today - anchor).days
    n = elapsed // length
    start = anchor + timedelta(days=n * length)
    return start, start + timedelta(days=length)


def _months_for(cl, logged, since=None, first_seen=None):
    """
    یک کانفیگ چند ماه صورت‌حساب دارد، و این عدد از کجا آمده.

    برمی‌گرداند: (تعداد ماه, منبع, خطای تخمین به روز)

    منبع‌ها به ترتیب اعتبار:

      ثبت‌شده   تمدیدهایی که خودِ نکسورا ثبت کرده — قطعی
      ساخت      تاریخ ساخت کلاینت در x-ui — قطعی، ولی نسخه‌های
                قدیمی این ستون را ندارند
      شروع گروه مدیر تاریخ شروع همکاری با واسطه را گفته
      اولین‌دید  پنل از این تاریخ کلاینت را می‌شناسد — کف مطمئن،
                نه تاریخ واقعی شروع
      پیش‌فرض   هیچ‌کدام نبود؛ یک ماه

    چرا منبع برمی‌گردد: قبلاً همه‌ی این حالت‌ها یک عدد خشک می‌دادند و
    مدیر نمی‌فهمید چرا واسطه‌ای که دو سال کار کرده «یک ماه» صورت‌حساب
    گرفته. حالا پنل می‌تواند دقیقاً بگوید عدد از کجا آمده و چه چیزی
    لازم است تا درست شود.
    """
    from datetime import datetime as _dt

    # تمدیدهای ثبت‌شده یک *کف* هستند، نه جایگزین تخمین.
    #
    # قبلاً همین‌جا return می‌شد. ولی ثبت از روزی شروع می‌شود که
    # نکسورا نصب شده؛ کانفیگی که دو سال سابقه دارد و یک تمدیدِ
    # ثبت‌شده، «۲ ماه» می‌شد به‌جای ۲۵ ماه — یعنی ثبت‌کردن تمدیدها
    # صورتحساب را *بدتر* می‌کرد.
    #
    # پایین هر دو حساب می‌شوند و بزرگ‌ترشان برمی‌گردد.
    floor = 1 + logged.get(cl["email"], 0) if cl["email"] in logged else 0

    exp = cl.get("expiry")

    _ms = _epoch_ms

    created, source = _start_ms(cl, since, first_seen)

    if not exp or exp <= 0 or created is None:
        return (floor, "ثبت‌شده", 0) if floor > 1 else (1, "پیش‌فرض", 0)

    exp_ms = _ms(exp)
    if exp_ms is None:
        return (floor, "ثبت‌شده", 0) if floor > 1 else (1, "پیش‌فرض", 0)

    days = (exp_ms - created) / 86400000.0
    if days <= 0:
        # منقضی شده: از شروع تا امروز حساب می‌کنیم، نه تا انقضا —
        # وگرنه کانفیگی که سه سال کار کرده و دیروز تمام شده،
        # «یک ماه» حساب می‌شد.
        days = (_dt.now().timestamp() * 1000 - created) / 86400000.0
        if days <= 0:
            return (floor, "ثبت‌شده", 0) if floor > 1 else (1, "منقضی", 0)
        months = _months_from_days(days)
        if floor > months:
            return floor, "ثبت‌شده", 0
        return months, source + " (منقضی)", 0

    months = _months_from_days(days)

    # تمدیدی که دیده‌ایم از تخمین بیشتر است — یعنی انقضا یک جایی عقب
    # کشیده شده (تمدید با «تاریخ تازه» به‌جای «افزودن روز»). آن‌وقت
    # فاصله‌ی ساخت تا انقضا کوتاه‌تر از واقعیت است و تخمین کم می‌آورد.
    if floor > months:
        return floor, "ثبت‌شده", 0

    drift = abs(days - months * 30)
    if source == "ساخت" and drift <= 2:
        return months, "قطعی", 0
    return months, source, round(drift)


def _bill_since(conf, explicit=""):
    """
    صورتحساب از چه تاریخی به بعد حساب شود، و چرا.

    ترتیب:
      ۱. تاریخی که مدیر همین حالا انتخاب کرده
      ۲. «تسویه‌شده تا» — هرچه پیش از آن بوده، پولش گرفته شده
      ۳. «شروع همکاری» — پیش از آن اصلاً همکاری‌ای نبوده
      ۴. هیچ‌کدام — از ابتدای عمر هر کانفیگ

    چرا لازم شد:
        صورتحساب *همه‌ی* عمر هر کانفیگ را حساب می‌کرد و هیچ تاریخی
        را نمی‌دید. واسطه‌ای که ماه پیش تسویه کرده بود، این ماه
        دوباره همان تمدیدها را روی فاکتورش می‌دید.

        «تسویه‌شده تا» از قبل در پایگاه داده بود و صفحه‌ی دوره‌ای هم
        رعایتش می‌کرد — ولی صورتحساب و PDF، یعنی همان چیزی که دست
        واسطه می‌رسد، اصلاً نگاهش نمی‌کردند.

    برمی‌گرداند: (YYYY-MM-DD یا "", برچسب منبع)
    """
    from datetime import date as _date

    def ok(v):
        v = (v or "").strip()[:10]
        if not v:
            return ""
        try:
            _date.fromisoformat(v)
        except ValueError:
            return ""
        return v

    for value, why in ((explicit, "تاریخ انتخابی"),
                       ((conf or {}).get("settled_until"), "تسویه‌شده تا"),
                       ((conf or {}).get("period_start"), "شروع همکاری")):
        v = ok(value)
        if v:
            return v, why
    return "", ""


def _price_per_gb(conf):
    """
    نرخ حجمی — وقتی با واسطه به‌جای پلن، روی هر گیگابایت توافق شده.

    برمی‌گرداند: عدد تومان بر گیگابایت، یا None اگر تعریف نشده.
    """
    try:
        v = int(conf.get("per_gb") or 0)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def _price_for(gb, rates):
    """
    قیمت یک کانفیگ. نرخ نامحدود با gb=0 مشخص می‌شود.

    ترتیب انتخاب:
      ۱. نرخ دقیقاً همان حجم
      ۲. نزدیک‌ترین نرخ بالاتر
      ۳. بالاترین نرخ تعریف‌شده — وقتی حجم کانفیگ از همه‌ی نرخ‌ها
         بزرگ‌تر است

    مرحله‌ی سوم قبلاً نبود: اگر واسطه‌ای نرخ ۳۰ و ۵۰ و ۱۰۰ گیگ تعریف
    کرده بود و مشتری کانفیگ ۲۰۰ گیگی داشت، هیچ نرخی پیدا نمی‌شد و آن
    ردیف *صفر* حساب می‌شد — با اینکه نرخ تعریف شده بود. صفر گرفتن از
    یک کانفیگ واقعی بدتر از تقریب زدن است.

    نرخی که مدیر تعریف کرده باید استفاده شود — حتی اگر دقیقاً روی این
    کانفیگ ننشیند.

    قبلاً این‌طور نبود و دو حالت بی‌صدا صفر می‌شدند:

      • گروهی که فقط نرخ نامحدود داشت، ولی کانفیگ‌هایش حجم داشتند.
        روی سرور واقعی این یعنی ۱۰۰ کانفیگ از ۲۵۷ تا هیچ قیمتی
        نمی‌گرفتند — گروهی به اسم «unlimited» با یک نرخ ۱۹۰٬۰۰۰ و
        ۸۸ کانفیگِ ۲۰۰ گیگی داخلش.

      • گروهی که فقط نرخ حجمی داشت، ولی کانفیگی نامحدود در آن بود.

    وقتی مدیر برای یک گروه نرخ گذاشته، منظورش این است که این گروه
    قیمت دارد. «چون دقیقاً جور در نمی‌آید پس صفر» جوابِ غلطی است به
    سوالی که اصلاً پرسیده نشده بود.
    """
    price, _ = _price_with_reason(gb, rates)
    return price


def _device_rate(gb, rates):
    """
    نرخ هر کاربرِ اضافه برای همین حجم — یا صفر اگر تعریف نشده.

    از همان ردیفی خوانده می‌شود که قیمت پایه از آن آمده، پس هر پله
    می‌تواند نرخ کاربر خودش را داشته باشد.
    """
    chosen = _match_rate(gb, rates)
    if not chosen:
        return 0
    try:
        return max(0, int(chosen.get("perDevice", 0) or 0))
    except (TypeError, ValueError):
        return 0


def _line_amount(gb, rates, months, limit_ip):
    """
    مبلغ یک ردیف فاکتور: (نرخ پایه + کاربرهای اضافه) × ماه.

    کانفیگ چهارکاربره همان نرخ کانفیگ تک‌کاربره را می‌گرفت، در حالی
    که سه کاربر بیشتر روی سرور می‌نشیند. حالا هر ردیف نرخ، نرخ کاربر
    خودش را دارد.

    «کاربرِ اضافه» یعنی از دومی به بعد — نرخ پایه شامل کاربر اول است،
    پس کانفیگ تک‌کاربره و فاکتورهای قبلی دست‌نخورده می‌مانند.

    محدودیت نامحدود (صفر) قابل شمردن نیست، پس فقط نرخ پایه می‌گیرد و
    ردیف علامت می‌خورد تا در فهرست «نیاز به بررسی» دیده شود.

    برمی‌گرداند: (مبلغ, نرخ پایه, نرخ هر کاربر, تعداد کاربر اضافه)
    """
    base, _why = _price_with_reason(gb, rates)
    if base is None:
        return 0, None, 0, 0
    per = _device_rate(gb, rates)
    try:
        ips = int(limit_ip or 0)
    except (TypeError, ValueError):
        ips = 0
    extra = max(0, ips - 1) if ips > 0 else 0
    return (base + per * extra) * months, base, per, extra


def _match_rate(gb, rates):
    """همان ردیفی که _price_with_reason قیمتش را برمی‌دارد."""
    valid = []
    for r in rates or []:
        try:
            valid.append((int(r.get("gb", -1)), r))
        except (TypeError, ValueError, AttributeError):
            continue
    if not valid:
        return None
    for g, r in valid:
        if g == gb:
            return r
    if gb > 0:
        higher = sorted((v for v in valid if v[0] > gb), key=lambda v: v[0])
        if higher:
            return higher[0][1]
        vol = [v for v in valid if v[0] > 0]
        if vol:
            return max(vol, key=lambda v: v[0])[1]
        flat = [v for v in valid if v[0] == 0]
        if flat:
            return flat[0][1]
        return None
    vol = [v for v in valid if v[0] > 0]
    return max(vol, key=lambda v: v[0])[1] if vol else None


def _price_with_reason(gb, rates):
    """
    قیمت، به‌همراه دلیلِ نبودنش. برمی‌گرداند: (قیمت یا None, دلیل یا None)

    چرا دلیل لازم است: «بدون نرخ» پنج علت مختلف دارد و هیچ‌کدامشان
    از خودِ عبارت پیدا نیست. مدیری که نرخ تعریف کرده و باز هم «بدون
    نرخ» می‌بیند، هیچ راهی ندارد بفهمد کدام‌یک است — و همین چند بار
    به‌عنوان «حسابداری کار نمی‌کند» برگشته.
    """
    if not rates:
        return None, "برای این گروه هیچ نرخی تعریف نشده"

    valid, broken = [], 0
    for r in rates:
        try:
            valid.append((int(r.get("gb", -1)), int(r.get("price", 0))))
        except (TypeError, ValueError):
            broken += 1
            continue
    if not valid:
        return None, "نرخ‌های این گروه خوانده نشدند — دوباره ثبتشان کنید"

    for g, price in valid:
        if g == gb:
            return price, None

    if gb > 0:
        higher = sorted((v for v in valid if v[0] > gb), key=lambda v: v[0])
        if higher:
            return higher[0][1], None
        # از همه‌ی نرخ‌ها بزرگ‌تر است — بالاترین نرخ حجمی را می‌گیرد
        volume_rates = [v for v in valid if v[0] > 0]
        if volume_rates:
            return max(volume_rates, key=lambda v: v[0])[1], None
        # هیچ نرخ حجمی نیست، ولی نرخ نامحدود هست: همان تنها نرخِ
        # گروه است، پس نرخِ ثابتِ گروه حساب می‌شود.
        flat = [v for v in valid if v[0] == 0]
        if flat:
            return flat[0][1], None
        return None, (f"این کانفیگ {gb} گیگ است و هیچ نرخی برای این "
                      "گروه جور در نمی‌آید")

    # gb == 0 یعنی نامحدود. نرخ نامحدود در حلقه‌ی تطابق دقیق بالا
    # گرفته می‌شد؛ اگر به این‌جا رسیدیم یعنی فقط نرخ حجمی هست.
    #
    # گران‌ترین پله را می‌گیرد: نامحدود دست‌کم به اندازه‌ی بزرگ‌ترین
    # حجمی است که برایش نرخ گذاشته‌اید — همان قاعده‌ای که برای کانفیگِ
    # بزرگ‌تر از همه‌ی پله‌ها هم به کار می‌رود.
    vol = [v for v in valid if v[0] > 0]
    if vol:
        return max(vol, key=lambda v: v[0])[1], None

    return None, "برای این گروه هیچ نرخ قابل‌استفاده‌ای نیست"


@app.get("/api/admin/billing/groups")
@app.get("/api/admin/billing/overview")
def billing_overview(x_admin_password: str = Header(...)):
    """گروه‌ها با محاسبه‌ی کامل — پایه‌ی همه‌ی صفحات حسابداری."""
    check_auth(x_admin_password)

    try:
        return _billing_overview_impl()
    except HTTPException:
        raise
    except Exception as e:
        # هرگز ۵۰۰ نمی‌دهیم: فرانت‌اند وقتی پاسخ JSON بدون error بگیرد،
        # متن پیش‌فرض گمراه‌کننده نشان می‌دهد و کاربر فکر می‌کند مشکل
        # از مسیر دیتابیس است.
        return {"ready": False, "groups": [],
                "xuiPath": str(_xui_db_path()),
                "error": f"محاسبه ناموفق: {type(e).__name__}: {str(e)[:150]}"}


def _bot_sold_emails():
    """
    شناسه‌ی کلاینت‌هایی که ربات فروخته.

    حسابداری برای واسطه‌هاست. کلاینت‌های ربات مشتری مستقیم خودتان‌اند
    و صورت‌حسابی برایشان صادر نمی‌شود — اگر در همان جدول بنشینند،
    عدد بدهی واسطه‌ها اشتباه می‌شود و مدیر از کسی طلب می‌کند که
    بدهکار نیست.

    از خود دیتابیس ربات خوانده می‌شود، نه از روی الگوی نام — الگو
    با عوض‌شدن پیشوند می‌شکند و بی‌صدا اشتباه می‌کند.
    """
    con = _bot_conn()
    if not con:
        return set()
    try:
        return {r["client_email"] for r in con.execute(
            "SELECT client_email FROM subscriptions "
            "WHERE client_email IS NOT NULL") if r["client_email"]}
    except Exception:
        return set()
    finally:
        con.close()



#: انقضا باید دست‌کم این‌قدر جلو برود تا «تمدید» حساب شود.
#
#  کمتر از این معمولاً اصلاح دستی چند روزه است، نه فروش.
RENEWAL_MIN_DAYS = 20


def _detect_renewals(bcon, clients, known, today):
    """
    تمدیدهایی که واسطه مستقیم در x-ui انجام داده را پیدا و ثبت می‌کند.

    پنل دست واسطه است. او کانفیگ را همان‌جا تمدید می‌کند و هیچ‌کجا
    ثبت نمی‌شود — نه در ربات، نه در x-ui که اصلاً تاریخچه ندارد. پس
    مدیر نمی‌فهمد کدام مشتری تمدید کرده و چند بار؛ فقط می‌بیند واسطه
    چند کانفیگ دارد. برای حساب‌وکتاب کافی نیست.

    تنها راهش این است: هر بار که فهرست کلاینت‌ها را می‌خوانیم، انقضای
    هر کدام را به خاطر بسپاریم. دفعه‌ی بعد اگر انقضا *جلو* رفته باشد،
    بین این دو خواندن تمدید شده.

    محدودیتش را صریح بگوییم: تاریخِ ثبت، تاریخِ *دیدن* است نه تاریخ
    واقعی تمدید. اگر ماهی یک بار صفحه‌ی حسابداری باز شود، تمدید ثبت
    می‌شود ولی تا یک ماه دیرتر. تعدادش درست است، تاریخش تقریبی.
    """
    rows = []
    upd = []
    for c in clients:
        em = c.get("email")
        if not em:
            continue
        exp = _epoch_ms(c.get("expiry"))
        if not exp or exp <= 0:
            continue
        prev = known.get(em)
        upd.append((exp, em))
        if not prev or prev <= 0:
            continue
        gained = (exp - int(prev)) / 86400000.0
        if gained < RENEWAL_MIN_DAYS:
            continue
        months = max(1, _months_from_days(gained))
        rows.append((em, c.get("group") or "", months, today))

    try:
        if rows:
            bcon.executemany(
                "INSERT INTO renewals (email, group_key, months, created_at) "
                "VALUES (?,?,?,?)", rows)
        if upd:
            bcon.executemany(
                "UPDATE client_seen SET last_expiry=?, last_seen=date('now') "
                "WHERE email=?", upd)
        if rows or upd:
            bcon.commit()
        if rows:
            log.info("تمدید تازه ثبت شد: %s کانفیگ", len(rows))
    except Exception:
        log.debug("ثبت تمدید ناموفق", exc_info=True)


def _record_seen(bcon, clients):
    """
    اولین و آخرین باری که هر کلاینت دیده شده را ثبت می‌کند.

    برمی‌گرداند: {ایمیل: تاریخ اولین دیدن}

    این تنها منبع قابل اتکایی است که خودمان می‌سازیم. x-ui در
    نسخه‌های قدیمی تاریخ ساخت ندارد، و هیچ‌جای دیگری هم این را
    نگه نمی‌دارد — پس اگر خودمان ثبت نکنیم، برای همیشه نداریمش.
    """
    now = datetime.now().strftime("%Y-%m-%d")
    out = {}
    known = {}
    #: ایمیل → (آخرین مصرفی که دیدیم، جمعِ دوره‌های ریست‌شده)
    seen_used = {}
    try:
        # ستون در نصب‌های قدیمی نیست — بی‌سروصدا اضافه‌اش می‌کنیم.
        cols = {r[1] for r in bcon.execute("PRAGMA table_info(client_seen)")}
        for _c, _t in (("last_expiry", "INTEGER"),
                       ("last_used", "INTEGER"),
                       ("used_before", "INTEGER DEFAULT 0")):
            if _c not in cols:
                bcon.execute(f"ALTER TABLE client_seen ADD COLUMN {_c} {_t}")
        bcon.commit()
        for r in bcon.execute(
                "SELECT email, first_seen, last_expiry, last_used, used_before "
                "FROM client_seen"):
            out[r["email"]] = r["first_seen"]
            known[r["email"]] = r["last_expiry"]
            seen_used[r["email"]] = (r["last_used"], r["used_before"] or 0)
    except Exception:
        return out

    # کلاینت تازه *قبل* از تشخیص درج می‌شود، و با انقضای همین لحظه.
    #
    # اگر بعدش درج شود، آن UPDATE به هیچ سطری نمی‌خورد و ردیف با
    # last_expiry خالی ساخته می‌شود — یعنی مبنای مقایسه یک دور دیرتر
    # جا می‌افتد و اولین تمدیدِ هر کانفیگ برای همیشه از دست می‌رود.
    fresh = [(c["email"], c.get("group") or "", now, now,
              _epoch_ms(c.get("expiry")), int(c.get("used") or 0))
             for c in clients if c.get("email") and c["email"] not in out]
    if fresh:
        try:
            bcon.executemany(
                "INSERT OR IGNORE INTO client_seen "
                "(email, group_key, first_seen, last_seen, last_expiry, "
                " last_used, used_before) "
                "VALUES (?,?,?,?,?,?,0)", fresh)
            bcon.commit()
            for em, _g, fs, _l, exp, us in fresh:
                out[em] = fs
                known[em] = exp
                seen_used[em] = (us, 0)
        except Exception:
            log.debug("ثبت اولین دیدن ناموفق", exc_info=True)

    _detect_renewals(bcon, clients, known, now)
    _track_usage(bcon, clients, seen_used)

    try:
        bcon.executemany(
            "UPDATE client_seen SET last_seen=? WHERE email=?",
            [(now, c["email"]) for c in clients if c.get("email")])
        bcon.commit()
    except Exception:
        pass
    return out


def _track_usage(bcon, clients, seen_used):
    """
    مصرفِ جمع‌شده را نگه می‌دارد — حتی وقتی ترافیک ریست می‌شود.

    همان قاعده‌ی تشخیصِ تمدید، برای ترافیک: x-ui تاریخچه ندارد، پس
    خودمان عددِ قبلی را به خاطر می‌سپاریم و مقایسه می‌کنیم. اگر
    مصرف **پایین** آمده باشد، یعنی ریست شده و عددِ قبلی باید به
    جمع اضافه شود، وگرنه برای همیشه می‌رود.

    اندازه‌گیری‌شده: کانفیگِ ۵۰۰ گیگی که ۵۰۰ مصرف کرد، ریست خورد،
    و ۴۵۰ دیگر مصرف کرد — پنل ۴۵۰ می‌گفت. ۵۰۰ گیگ بی‌صدا گم شده
    بود، و روی صورتحساب یعنی واسطه یک‌بار پول داده برای دو دوره.

    یک نکته: «پایین آمدن» را با حاشیه نمی‌سنجیم. مصرف هیچ‌وقت خودش
    کم نمی‌شود، پس هر کاهشی ریست است. ولی *مساوی* ریست نیست —
    وگرنه کانفیگی که بی‌استفاده مانده هر بار دوباره جمع می‌شد.
    """
    ups = []
    for c in clients:
        em = c.get("email")
        if not em:
            continue
        now_used = int(c.get("used") or 0)
        prev, before = seen_used.get(em, (None, 0))
        if prev is None:
            ups.append((now_used, before, em))
            continue
        if now_used < prev:
            # ریست: آنچه تا پیش از ریست مصرف شده بود را نگه دار
            before = int(before or 0) + int(prev)
        ups.append((now_used, before, em))

    if not ups:
        return
    try:
        bcon.executemany(
            "UPDATE client_seen SET last_used=?, used_before=? WHERE email=?", ups)
        bcon.commit()
    except Exception:
        log.debug("ثبت مصرف جمع‌شده ناموفق", exc_info=True)



def _gb_of(total):
    """
    حجمِ کانفیگ به گیگابایت.

    ۳x-ui گاهی بایت می‌دهد و گاهی خودِ عدد گیگ — پس شرطِ «بزرگ‌تر از
    ۱۰۲۴» تصمیم می‌گیرد کدام است. صفر یعنی نامحدود.

    این یک خط تا امروز شش بار درون‌خطی تکرار شده بود و یک‌بار هم در
    `tools/billing-why.py`. هفت کپی از یک قاعده‌ی پول، که هر کدامشان
    جای تازه‌ای برای جدا افتادن بود.
    """
    try:
        total = int(total or 0)
    except (TypeError, ValueError):
        return 0
    return total // (1024 ** 3) if total > 1024 else total


def _attach_total_usage(bcon, clients):
    """
    مصرفِ دوره‌های ریست‌شده را روی کلاینت‌ها می‌گذارد.

    x-ui با ریستِ ترافیک عدد را صفر می‌کند و تاریخچه‌ای ندارد، پس
    `client_seen.used_before` تنها جایی است که آن مصرف باقی مانده.

    **این تنها راهِ رسیدن به مصرفِ واقعی است.** نسخه‌ی قبل این جمع را
    فقط در `billing_clients` حساب می‌کرد و بقیه‌ی صفحه‌های حسابداری —
    از جمله بدهیِ نرخِ حجمی — همان عددِ پس‌از‌ریست را برمی‌داشتند.
    یعنی همان «یک قاعده، دو جا، اصلاح در یکی».
    """
    if not clients:
        return
    before = {}
    try:
        before = {r["email"]: int(r["used_before"] or 0) for r in bcon.execute(
            "SELECT email, used_before FROM client_seen")}
    except Exception:
        # ستون هنوز ساخته نشده (نصبِ تازه، پیش از اولین ثبت).
        # این‌جا *برنمی‌گردیم*: قرارِ این تابع این است که بعد از
        # اجرایش هر کلاینت `usedTotal` داشته باشد. برگشتنِ زودهنگام
        # یعنی صداکننده روی کلیدِ نبوده KeyError می‌گیرد — و آن،
        # یک صفحه‌ی خالی است به‌جای یک عددِ بدونِ جمع.
        log.debug("خواندن مصرف پیشین ناموفق", exc_info=True)
    for cl in clients:
        cl["usedTotal"] = int(cl.get("used") or 0) + before.get(cl.get("email"), 0)


def _with_total_usage(clients):
    """
    `_attach_total_usage`، ولی خودش اتصالِ حسابداری را باز و بسته
    می‌کند.

    برای مسیرهایی که اتصالِ باز ندارند (پنلِ نماینده). شکستِ باز‌کردن
    بی‌صداست: `usedTotal` از پیش برابرِ `used` است، پس بدترین حالت
    همان رفتارِ قبلی است، نه کرش.
    """
    if not clients:
        return clients
    try:
        bcon = _billing_conn()
    except Exception:
        log.debug("اتصال حسابداری برای جمعِ مصرف باز نشد", exc_info=True)
        return clients
    try:
        _attach_total_usage(bcon, clients)
    finally:
        bcon.close()
    return clients


def _billable_config(cl):
    """
    آیا این کانفیگ باید نرخ بگیرد؟ برمی‌گرداند: (بله/خیر, دلیل)

    قاعده‌ای که مالک خواست: فقط کانفیگ‌های در استفاده حساب شوند — ولی
    «منقضی شد» نباید راه فرار از پرداخت باشد.

    این دو با هم می‌خوانند، چون منقضی‌شدن یعنی کانفیگ *دوره‌اش را کار
    کرده*. مشتری آن ماه را استفاده کرده و واسطه باید بابتش بدهد. آنچه
    نباید حساب شود، کانفیگی است که ساخته شده و اصلاً به کار نیفتاده:
    غیرفعال، بدون یک بایت ترافیک.

    ۳x-ui کانفیگ منقضی را خودش غیرفعال می‌کند، پس اگر فقط به enable
    نگاه می‌کردیم، هر کانفیگی با تمام‌شدن دوره‌اش از صورت‌حساب بیرون
    می‌افتاد — دقیقاً همان چیزی که مالک هشدار داد.
    """
    # جمعِ همه‌ی دوره‌ها، نه دوره‌ی جاری.
    #
    # وگرنه کانفیگی که مصرف داشته و بعد ریست خورده، «ساخته شده ولی
    # هرگز به کار نیفتاده» شمرده می‌شد و کاملاً از صورتحساب بیرون
    # می‌افتاد. یعنی ریست‌زدن راهِ نپرداختن می‌شد — و ریست دستِ خودِ
    # نماینده است.
    used = int(cl.get("usedTotal") or cl.get("used") or 0)
    enabled = bool(cl.get("enable"))

    if enabled:
        return True, "فعال"
    if used > 0:
        return True, "غیرفعال ولی مصرف داشته"

    exp = cl.get("expiry")
    try:
        expired = bool(exp) and int(exp) > 0 and int(exp) < _now_ms()
    except (TypeError, ValueError):
        expired = False
    if expired:
        return True, "دوره‌اش تمام شده — کار کرده و باید حساب شود"

    return False, "ساخته شده ولی هرگز به کار نیفتاده"


def _now_ms():
    return int(datetime.now().timestamp() * 1000)


def _billing_overview_impl():
    clients, known_groups, err = _read_xui_clients()
    if clients is None:
        return {"ready": False, "error": err, "xuiPath": str(_xui_db_path()), "groups": []}

    bot_emails = _bot_sold_emails()

    bcon = _billing_conn()
    try:
        cfg = {r["group_key"]: dict(r) for r in bcon.execute("SELECT * FROM group_config")}

        # مبدأ هر گروه یک‌بار حساب می‌شود و هم ماه‌ها و هم پرداختی‌ها
        # را می‌برد. پیش از این پرداختی‌ها با یک GROUP BY ساده جمع
        # می‌شدند — یعنی پولِ دوره‌ی تسویه‌شده هم داخل «دریافت‌شده»
        # می‌آمد، در حالی که بدهی‌اش دیگر شمرده نمی‌شود.
        since_of = {k: _bill_since(v)[0] for k, v in cfg.items()}
        pays, pays_all = {}, {}
        for r in bcon.execute(
            "SELECT group_key, amount, COALESCE(paid_at,'') d FROM payments"
        ):
            amt = r["amount"] or 0
            k = r["group_key"]
            # هر دو نگه داشته می‌شوند: «چقدر الان طلبکارم» دوره‌ای
            # است، «از روز اول چقدر گرفته‌ام» نیست. دفتر کل دومی را
            # می‌خواهد و هزینه‌ها هم از روز اول جمع می‌شوند.
            pays_all[k] = pays_all.get(k, 0) + amt
            cut = since_of.get(k) or ""
            if cut and r["d"][:10] < cut:
                continue
            pays[k] = pays.get(k, 0) + amt
        logged = {}
        for r in bcon.execute(
            "SELECT email, COALESCE(SUM(months),0) m FROM renewals GROUP BY email"
        ):
            logged[r["email"]] = r["m"]
        rows_by = _rows_by_email([dict(r) for r in bcon.execute(
            "SELECT email, months, created_at FROM renewals")])

        # هر بار که نمای کلی خوانده می‌شود، دیدن کلاینت‌ها ثبت می‌شود.
        # این‌طور از امروز به بعد یک کف واقعی برای «از کی می‌شناسیمش»
        # داریم، بدون اینکه مدیر کاری بکند.
        seen = _record_seen(bcon, clients)
        # و مصرفِ دوره‌های ریست‌شده را روی همین کلاینت‌ها بگذار.
        # *بعد* از `_record_seen` است، چون همان تابع است که ریستِ
        # همین لحظه را تشخیص می‌دهد و `used_before` را به‌روز می‌کند.
        _attach_total_usage(bcon, clients)
    finally:
        bcon.close()

    groups = {}
    for cl in clients:
        g = cl["group"]
        conf = cfg.get(g, {})
        try:
            rates = json.loads(conf.get("rates") or "[]")
        except (json.JSONDecodeError, TypeError):
            rates = []

        if g not in groups:
            groups[g] = {
                "key": g,
                "label": conf.get("label") or g,
                "billable": bool(conf.get("billable", 0)),
                "rates": rates if isinstance(rates, list) else [],
                "perGb": _price_per_gb(conf),
                "periodDays": conf.get("period_days") or 30,
                "periodStart": conf.get("period_start"),
                "settledUntil": conf.get("settled_until"),
                # پول گرفته شده ولی هیچ دوره‌ای بسته نشده.
                #
                # این همان حالتی است که به مالک ضرر زد: پرداخت ثبت
                # می‌شد، `settled_until` دست‌نخورده می‌ماند، و فاکتور
                # ماه بعد همان کاربران و همان دوره را دوباره می‌آورد —
                # و بر اساس همان فاکتور، پول دوباره گرفته شد.
                #
                # هیچ‌جا هم نمی‌گفت. حالا می‌گوید.
                "unsettledPayments": 0,
                # از چه تاریخی حساب شده — همان که صورتحساب به کار
                # می‌برد، تا دو صفحه یک عدد بدهند
                "since": since_of.get(g) or None,
                "settledSkipped": 0,
                # از کجا معلوم شد چند ماه — تا مدیر بفهمد چرا عدد
                # این است و چه چیزی لازم است تا دقیق‌تر شود
                "sources": {},
                "configs": 0, "active": 0, "months": 0, "renewals": 0,
                "used": 0, "quota": 0, "due": 0,
                # عمرِ کامل، برای دفتر کل — جایی که هزینه‌ها هم از روز
                # اول جمع می‌شوند و درآمدِ دوره‌ای کنارشان بی‌معناست
                "monthsAll": 0, "dueAll": 0,
                "paid": pays.get(g, 0), "paidAll": pays_all.get(g, 0),
                "unpriced": 0, "unpricedWhy": {},
                "estimated": 0,
                # کانفیگ‌هایی که ساخته شدند ولی هرگز به کار نیفتادند —
                # اینها نرخ نمی‌گیرند و این‌جا شمرده می‌شوند تا مدیر
                # ببیند چند تا و چرا کنار گذاشته شده‌اند
                "skipped": 0, "skippedWhy": {},
                # کلاینت‌هایی که ربات فروخته — مشتری مستقیم، نه واسطه
                "botOwned": 0,
            }

        G = groups[g]
        G["configs"] += 1
        if cl["email"] in bot_emails:
            G["botOwned"] += 1
        if cl["enable"]:
            G["active"] += 1
        # جمعِ همه‌ی دوره‌ها، نه فقط دوره‌ی جاری.
        #
        # با `cl["used"]`، گروهی که کانفیگ‌هایش ریست خورده‌اند
        # «کم‌مصرف» به نظر می‌رسید — و همان عددی است که مالک روی
        # کارتِ بدهی می‌بیند.
        G["used"] += cl["usedTotal"]
        G["quota"] += cl["totalGB"]

        bill_it, why = _billable_config(cl)
        if not bill_it:
            G["skipped"] += 1
            G["skippedWhy"][why] = G["skippedWhy"].get(why, 0) + 1
            continue

        months, all_months, ren_in, _new, kind, _drift = _period_share(
            cl, logged, rows_by.get(cl["email"], []), since_of.get(g),
            group_start=conf.get("period_start"),
            first_seen=seen.get(cl["email"]))
        G["monthsAll"] += all_months
        if G["billable"] and cl["email"] not in bot_emails and not G.get("perGb"):
            gb_all = (_gb_of(cl["totalGB"]))
            G["dueAll"] += _line_amount(gb_all, G["rates"], all_months,
                                        cl.get("limitIp"))[0]
        if months <= 0:
            # کاملاً پیش از مبدأ — تسویه‌شده و دیگر بدهیِ *امروز* نیست
            G["settledSkipped"] = G.get("settledSkipped", 0) + 1
            continue
        G["months"] += months
        G["renewals"] += ren_in
        G["sources"][kind] = G["sources"].get(kind, 0) + 1
        # «تخمینی» یعنی هر چیزی جز دو منبع قطعی. بدون این، گروهی که
        # همه‌ی کانفیگ‌هایش روی پیش‌فرض یک ماه افتاده‌اند، با اطمینان
        # کامل نمایش داده می‌شد.
        if kind not in ("قطعی", "ثبت‌شده"):
            G["estimated"] += 1

        # کلاینت ربات هرگز به واسطه صورت‌حساب نمی‌شود، حتی اگر
        # تصادفی در گروهی نشسته باشد.
        if G["billable"] and cl["email"] not in bot_emails:
            gb = _gb_of(cl["totalGB"])

            if G.get("perGb"):
                # نرخ حجمی: بر اساس مصرف واقعی، نه پلن.
                # چون در این مدل واسطه بابت چیزی که مصرف شده پول می‌دهد،
                # نه بابت سقفی که خریده.
                #
                # و «مصرف واقعی» یعنی جمعِ همه‌ی دوره‌ها. با عددِ
                # پس‌از‌ریست، واسطه‌ای که ریست می‌زند بابتِ نصفِ چیزی
                # که فروخته پول می‌داد — و ریست دستِ خودش است.
                used_gb = cl["usedTotal"] / (1024 ** 3)
                G["due"] += round(used_gb * G["perGb"])
            else:
                amount, price, per_dev, extra = _line_amount(
                    gb, G["rates"], months, cl.get("limitIp"))
                why = None
                if price is None:
                    _, why = _price_with_reason(gb, G["rates"])
                    G["unpriced"] += 1
                    # چرایش را هم نگه می‌داریم. «۷ کانفیگ بدون نرخ»
                    # بدون دلیل، مدیر را به همان‌جایی می‌برد که نرخ
                    # را از قبل تعریف کرده و فکر می‌کند پنل خراب است.
                    if why:
                        G["unpricedWhy"][why] = G["unpricedWhy"].get(why, 0) + 1
                else:
                    G["due"] += amount
                    G["deviceExtra"] = G.get("deviceExtra", 0) + per_dev * extra * months

    # گروه‌هایی که در پنل ساخته شده‌اند ولی هنوز کاربری ندارند هم
    # باید دیده شوند — وگرنه ادمین فکر می‌کند گروهش گم شده.
    for gname in (known_groups or []):
        if gname not in groups:
            conf = cfg.get(gname, {})
            try:
                rates = json.loads(conf.get("rates") or "[]")
            except (json.JSONDecodeError, TypeError):
                rates = []
            groups[gname] = {
                "key": gname,
                "label": conf.get("label") or gname,
                "billable": bool(conf.get("billable", 0)),
                "rates": rates if isinstance(rates, list) else [],
                "perGb": _price_per_gb(conf),
                "configs": 0, "active": 0, "months": 0, "renewals": 0,
                "used": 0, "quota": 0, "due": 0,
                "monthsAll": 0, "dueAll": 0,
                "paid": pays.get(gname, 0), "paidAll": pays_all.get(gname, 0),
                "unpriced": 0, "unpricedWhy": {},
                "estimated": 0,
                "botOwned": 0,
            }

    out = sorted(groups.values(), key=lambda g: (-g["billable"], -g["configs"]))
    # داشبورد این را می‌خواند. تا امروز فقط endpoint دیگری آن را
    # برمی‌گرداند و این‌جا undefined می‌شد: «undefined کانفیگ در ۱۱ گروه».
    total_clients = sum(g["configs"] for g in out)
    for g in out:
        g["balance"] = g["due"] - g["paid"]
        g["balanceAll"] = g.get("dueAll", 0) - g.get("paidAll", 0)
        # پول گرفته‌شده‌ای که هیچ دوره‌ای پشتش بسته نشده — همان حالتی
        # که فاکتور را وادار می‌کند دوره‌ی قبل را دوباره بیاورد
        if not (g.get("settledUntil") or "").strip():
            g["unsettledPayments"] = int(g.get("paidAll") or 0)
        g["usedGB"] = round(g["used"] / (1024 ** 3), 1)
        g["quotaGB"] = round(g["quota"] / (1024 ** 3), 1) if g["quota"] > 1024 else g["quota"]

        # نام‌های مترادف.
        #
        # رابط کاربری در جاهایی name/billed/amount/uncertain می‌خواند و در
        # جاهایی key/billable/due/estimated. هر دو را می‌فرستیم تا هیچ
        # بخشی خالی نماند — ارزان‌تر از این است که یک اسم فراموش شود و
        # کل صفحه بی‌صدا خالی بماند.
        g["name"] = g["key"]
        g["billed"] = g["billable"]
        g["amount"] = g["due"]
        g["uncertain"] = g["estimated"]

    billed = [g for g in out if g["billable"]]

    # ── گروه‌هایی که هیچ درآمدی از آن‌ها شمرده نمی‌شود ──
    #
    # روی سرور واقعی ۹۴ کانفیگ در هفت گروه بودند که هیچ‌کدام در
    # صورتحساب نمی‌آمدند، و هیچ‌جای پنل این را یکجا نمی‌گفت. مدیر
    # فقط می‌دید که عدد کل کمتر از انتظارش است و دلیلش را نمی‌فهمید.
    #
    # هر ردیف می‌گوید *چه چیزی* کم است، نه فقط اینکه مشکلی هست.
    needs = []
    for g in out:
        if g["configs"] <= 0:
            continue
        if not g["billable"]:
            needs.append({
                "key": g["key"], "configs": g["configs"],
                "why": "محاسبه برای این گروه خاموش است",
                "fix": "billable",
            })
        elif not g["rates"] and not g.get("perGb"):
            needs.append({
                "key": g["key"], "configs": g["configs"],
                "why": "هیچ نرخی تعریف نشده",
                "fix": "rates",
            })
        elif g["unpriced"]:
            needs.append({
                "key": g["key"], "configs": g["unpriced"],
                "why": (list(g.get("unpricedWhy") or {})
                        or ["نرخ این حجم‌ها تعریف نشده"])[0],
                "fix": "rates",
            })
    needs.sort(key=lambda x: -x["configs"])

    return {
        "ready": True,
        "groups": out,
        "needsSetup": needs,
        "needsSetupConfigs": sum(x["configs"] for x in needs),
        "totalClients": total_clients,
        "botClients": sum(g.get("botOwned", 0) for g in out),

        # گروه‌هایی که تاریخ شروع ندارند و به همین دلیل ماه‌هایشان
        # حدسی است.
        #
        # «اولین‌دید» هم این‌جا می‌آید: آن تاریخِ شروعِ همکاری نیست،
        # فقط روزی است که پنل کلاینت را دید. اگر حسابش نکنیم، بنر
        # بعد از اولین اجرا برای همیشه ناپدید می‌شود در حالی که
        # صورت‌حساب هنوز از امروز حساب می‌شود.
        "needStart": [
            g["key"] for g in out
            if g["billable"] and not g["periodStart"]
            and (g["sources"].get("پیش‌فرض", 0)
                 + sum(n for k, n in g["sources"].items()
                       if k.startswith("اولین‌دید"))) > 0
        ],

        "totals": {
            "due": sum(g["due"] for g in billed),
            "paid": sum(g["paid"] for g in billed),
            "balance": sum(g["balance"] for g in billed),
            "resellers": len(billed),
            "configs": sum(g["configs"] for g in billed),
        },
    }


@app.put("/api/admin/billing/group/{group_key}")
def billing_group_put(group_key: str, payload: dict, x_admin_password: str = Header(...)):
    """ذخیره‌ی نرخ و وضعیت یک گروه."""
    check_auth(x_admin_password)

    payload = payload or {}

    # رابط کاربری در جاهایی billed می‌فرستد و در جاهایی billable.
    # هر دو را می‌پذیریم — وگرنه کلید روشن/خاموش بی‌صدا ذخیره نمی‌شود
    # و کاربر فکر می‌کند دکمه کار نمی‌کند.
    billable = payload.get("billable")
    if billable is None:
        billable = payload.get("billed")

    rates = payload.get("rates", [])
    if not isinstance(rates, list):
        raise HTTPException(status_code=400, detail="فهرست نرخ نامعتبر است")

    # ردیفی که خوانده نشود باید خطا بدهد، نه اینکه بی‌صدا بیفتد.
    #
    # قبلاً continue بود: پاسخ «ok» می‌آمد و نرخی که مدیر تازه نوشته
    # بود اصلاً ذخیره نمی‌شد. بعد در حسابداری «بدون نرخ» می‌دید و
    # مطمئن بود که نرخ را تعریف کرده — چون کرده بود.
    clean = []
    for i, r in enumerate(rates, 1):
        try:
            clean.append({"gb": max(0, int(r.get("gb", 0))),
                          "price": max(0, int(r.get("price", 0))),
                          # نرخ هر کاربرِ اضافه، مخصوص همین ردیف
                          "perDevice": max(0, int(r.get("perDevice", 0) or 0))})
        except (TypeError, ValueError, AttributeError):
            raise HTTPException(
                status_code=400,
                detail=f"ردیف نرخ شماره {i} خوانده نشد — حجم و قیمت باید عدد باشند")

    try:
        per_gb = int(payload.get("per_gb") or payload.get("perGb") or 0)
    except (TypeError, ValueError):
        per_gb = 0

    try:
        period_days = int(payload.get("period_days") or payload.get("periodDays") or 30)
    except (TypeError, ValueError):
        period_days = 30
    period_days = max(1, min(period_days, 365))

    period_start = (payload.get("period_start")
                    or payload.get("periodStart") or "").strip()[:10]
    settled_until = (payload.get("settled_until")
                     or payload.get("settledUntil") or "").strip()[:10]

    con = _billing_conn()
    try:
        con.execute(
            "INSERT INTO group_config "
            "(group_key,label,billable,rates,per_gb,period_days,period_start,"
            " settled_until,note,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP) "
            "ON CONFLICT(group_key) DO UPDATE SET "
            "label=excluded.label, billable=excluded.billable, "
            "rates=excluded.rates, per_gb=excluded.per_gb, "
            "period_days=excluded.period_days, period_start=excluded.period_start, "
            "settled_until=excluded.settled_until, "
            "note=excluded.note, updated_at=CURRENT_TIMESTAMP",
            (group_key,
             (payload.get("label") or group_key).strip(),
             1 if billable else 0,
             json.dumps(clean, ensure_ascii=False),
             per_gb, period_days, period_start or None, settled_until or None,
             (payload.get("note") or "").strip()))
        con.commit()
        return {"ok": True, "rates": clean, "per_gb": per_gb, "perGb": per_gb,
                "periodDays": period_days, "periodStart": period_start,
                "settledUntil": settled_until,
                "billable": bool(billable), "billed": bool(billable),
                "label": (payload.get("label") or group_key).strip()}
    finally:
        con.close()


try:
    import fx as FX
except Exception:
    try:
        import importlib.util as _ifx
        _xs = _ifx.spec_from_file_location(
            "fx", Path(__file__).resolve().parent / "fx.py")
        FX = _ifx.module_from_spec(_xs)
        _xs.loader.exec_module(FX)
    except Exception:
        FX = None


#: دسته‌های هزینه، با نامی که مدیر می‌فهمد
EXPENSE_KINDS = {
    "server_abroad": "سرور خارج",
    "server_iran": "سرور ایران",
    "traffic": "خرید حجم و ترافیک",
    "domain": "دامنه و گواهی",
    "other": "متفرقه",
}


@app.get("/api/admin/billing/fx")
def billing_fx(currency: str = "EUR", x_admin_password: str = Header(...)):
    """نرخ روز ارز — برای تبدیل هزینه‌ی سرور خارج به تومان."""
    check_auth(x_admin_password)
    if not FX:
        raise HTTPException(status_code=500, detail="ماژول نرخ ارز بارگذاری نشد")
    return FX.live((currency or "EUR").upper())


@app.get("/api/admin/billing/expenses")
def expenses_list(months: int = 12, x_admin_password: str = Header(...)):
    """
    هزینه‌ها به‌همراه جمع هر دسته.

    بازه را محدود می‌کنیم تا بعد از چند سال، صفحه کند نشود؛ ولی
    جمع کل از ابتدا هم جدا برمی‌گردد چون مدیر همان را می‌خواهد.
    """
    check_auth(x_admin_password)
    months = max(1, min(int(months or 12), 120))
    since = (datetime.now() - timedelta(days=31 * months)).strftime("%Y-%m-%d")

    con = _billing_conn()
    try:
        rows = [dict(r) for r in con.execute(
            "SELECT * FROM expenses WHERE spent_at >= ? "
            "ORDER BY spent_at DESC, id DESC", (since,))]
        by_kind = {r["kind"]: r["s"] for r in con.execute(
            "SELECT kind, COALESCE(SUM(amount_irt),0) s FROM expenses "
            "WHERE spent_at >= ? GROUP BY kind", (since,))}
        all_time = con.execute(
            "SELECT COALESCE(SUM(amount_irt),0) s, COUNT(*) n FROM expenses"
        ).fetchone()
        gb_total = con.execute(
            "SELECT COALESCE(SUM(gb),0) g FROM expenses WHERE kind='traffic'"
        ).fetchone()
        # هزینه‌ی ماهانه‌ی تکرارشونده — عددی که مدیر باید هر ماه دربیاورد
        #
        # هزینه‌ی سالانه هم هست، فقط تقسیم بر دوازده. قبلاً کلاً کنار
        # گذاشته می‌شد: دامنه و لایسنسی که سالی یک‌بار پرداخت می‌شوند
        # در عددی که می‌گوید «این را هر ماه باید دربیاورید» صفر حساب
        # می‌شدند. یعنی همان خطایی که این بخش برای جلوگیری از آن
        # ساخته شده — اشتباه، و همیشه به نفع خودِ مدیر.
        monthly = con.execute(
            "SELECT COALESCE(SUM(amount_irt),0) s FROM expenses "
            "WHERE recurring='monthly'"
        ).fetchone()
        yearly = con.execute(
            "SELECT COALESCE(SUM(amount_irt),0) s FROM expenses "
            "WHERE recurring='yearly'"
        ).fetchone()
    finally:
        con.close()

    return {
        "ready": True,
        "months": months,
        "expenses": rows,
        "kinds": EXPENSE_KINDS,
        "byKind": {k: by_kind.get(k, 0) for k in EXPENSE_KINDS},
        "total": sum(by_kind.values()),
        "allTimeTotal": all_time["s"] if all_time else 0,
        "allTimeCount": all_time["n"] if all_time else 0,
        "trafficGB": gb_total["g"] if gb_total else 0,
        "monthlyRecurring": (
            (monthly["s"] if monthly else 0)
            + round((yearly["s"] if yearly else 0) / 12)),
        # جدا هم می‌آید تا کارت بتواند بگوید این عدد از کجا آمده
        "monthlyFromYearly": round((yearly["s"] if yearly else 0) / 12),
        "yearlyTotal": yearly["s"] if yearly else 0,
    }


@app.post("/api/admin/billing/expenses")
def expenses_add(payload: dict, x_admin_password: str = Header(...)):
    """
    ثبت یک هزینه.

    تبدیل ارز همین‌جا و یک‌بار انجام می‌شود و نتیجه ذخیره می‌ماند —
    نه در زمان نمایش. اگر نرخ در دسترس نباشد و مدیر هم نرخ دستی
    نداده باشد، ثبت را رد می‌کنیم: هزینه‌ی بدون مبلغ تومانی، یعنی
    گزارش سودی که بی‌صدا غلط است.
    """
    check_auth(x_admin_password)
    p = payload or {}

    kind = str(p.get("kind") or "other")
    if kind not in EXPENSE_KINDS:
        raise HTTPException(status_code=400, detail="دسته‌ی هزینه نامعتبر است")

    label = str(p.get("label") or "").strip()
    if not label:
        raise HTTPException(status_code=400, detail="عنوان هزینه لازم است")

    try:
        amount = float(p.get("amount") or 0)
    except (TypeError, ValueError):
        amount = 0.0
    if amount <= 0:
        raise HTTPException(status_code=400, detail="مبلغ باید بزرگ‌تر از صفر باشد")

    currency = str(p.get("currency") or "IRT").upper()
    if currency not in ("IRT", "EUR", "USD"):
        raise HTTPException(status_code=400, detail="ارز پشتیبانی نمی‌شود")

    if not FX:
        raise HTTPException(status_code=500, detail="ماژول نرخ ارز بارگذاری نشد")
    conv = FX.to_toman(amount, currency, manual_rate=p.get("rate"))
    if conv.get("toman") is None:
        raise HTTPException(
            status_code=400,
            detail=(conv.get("error") or "نرخ ارز در دسترس نیست") +
                   " — نرخ را دستی وارد کنید")

    spent_at = str(p.get("spentAt") or "").strip()[:10] \
        or datetime.now().strftime("%Y-%m-%d")
    recurring = str(p.get("recurring") or "once")
    if recurring not in ("once", "monthly", "yearly"):
        recurring = "once"

    gb = p.get("gb")
    try:
        gb = int(gb) if gb not in (None, "") else None
    except (TypeError, ValueError):
        gb = None

    con = _billing_conn()
    try:
        cur = con.execute(
            """INSERT INTO expenses (kind, label, amount, currency, amount_irt,
                                     fx_rate, fx_source, gb, recurring,
                                     spent_at, note)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (kind, label[:120], amount, currency, conv["toman"],
             conv.get("rate"), conv.get("source"), gb, recurring,
             spent_at, str(p.get("note") or "")[:300]))
        con.commit()
        new_id = cur.lastrowid
    finally:
        con.close()

    out = {"ok": True, "id": new_id, "toman": conv["toman"],
           "rate": conv.get("rate"), "source": conv.get("source"),
           "note": f"{label} ثبت شد"}
    # نرخ کهنه رد نمی‌شود — ممکن است سایت چند دقیقه پایین باشد و مدیر
    # منتظر است. ولی باید بداند با چه نرخی ثبت شد، وگرنه بعداً عددی
    # می‌بیند که با هیچ چیزی جور در نمی‌آید.
    if conv.get("stale"):
        age = conv.get("ageMinutes") or 0
        out["stale"] = True
        out["warning"] = (
            f"نرخ ارز از {_re.sub(r'.0$', '', str(round(age / 60, 1)))} ساعت "
            "پیش استفاده شد — سایت نرخ در دسترس نبود. اگر مهم است، "
            "هزینه را حذف کنید و با نرخ دستی دوباره ثبت کنید.")
    return out


@app.delete("/api/admin/billing/expenses/{exp_id}")
def expenses_del(exp_id: int, x_admin_password: str = Header(...)):
    """حذف یک هزینه — مثلاً وقتی اشتباه ثبت شده."""
    check_auth(x_admin_password)
    con = _billing_conn()
    try:
        con.execute("DELETE FROM expenses WHERE id=?", (exp_id,))
        con.commit()
    finally:
        con.close()
    return {"ok": True, "note": "هزینه حذف شد"}


def _bot_money_in():
    """
    پولی که از راه ربات واقعاً به دست مالک رسیده.

    دو تله این‌جا هست و هر دو در جهت *بیشتر نشان‌دادن* خطا می‌کنند:

      • سفارشی که از کیف پول پرداخت شده پول تازه نیست. همان پول
        یک‌بار موقع شارژ کیف رسیده و یک‌بار موقع خرید شمرده می‌شود.
        مشتری‌ای که ۵۰۰٬۰۰۰ شارژ کند و همان را خرج کند، ۱٬۰۰۰٬۰۰۰
        درآمد نشان می‌دهد.

      • سفارش‌های رباتِ *نماینده* درآمد نماینده است، نه مالک. بدون
        فیلتر مستاجر، فروش آن‌ها در سود مالک می‌نشیند.

    پس فقط سفارش‌های تاییدشده‌ی مستاجر اصلی که با کارت پرداخت
    شده‌اند — شارژ کیف پول با کارت هم همین‌جاست، چون آن لحظه‌ی
    رسیدن پول است.
    """
    con = _bot_conn()
    if not con:
        return 0
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(orders)")}
        # نصب‌های قدیمی ستون paid_from ندارند؛ آن‌جا همه‌ی سفارش‌ها
        # کارتی بوده‌اند چون کیف پول هنوز نبوده.
        card = (" AND COALESCE(paid_from,'card')='card'"
                if "paid_from" in cols else "")
        # «مستاجرِ ریشه» یعنی هرکسی که نماینده‌ی کس دیگری نیست. با
        # ORDER BY id LIMIT 1 یک ردیف دلخواه انتخاب می‌شد و اگر
        # مستاجر دیگری زودتر ساخته شده بود، درآمد واقعی صفر
        # گزارش می‌شد — بی‌صدا.
        r = con.execute(
            "SELECT COALESCE(SUM(amount),0) s FROM orders "
            "WHERE status='approved'" + card +
            " AND tenant_id IN (SELECT id FROM tenants WHERE parent_id IS NULL)"
        ).fetchone()
        return int((r["s"] if r else 0) or 0)
    except Exception:
        log.debug("خواندن درآمد ربات ناموفق", exc_info=True)
        return 0
    finally:
        con.close()


def _affiliate_money_out():
    """
    پورسانتی که به معرف‌ها پرداخت شده، و آنچه هنوز طلبشان است.

    برمی‌گرداند: (پرداخت‌شده, باقی‌مانده)

    هر دو پول واقعی‌اند و هیچ‌کدام در دفتر کل دیده نمی‌شدند: پرداختی
    از سود کم نمی‌شد و بدهیِ باقی‌مانده هیچ‌جا به‌عنوان تعهد نمی‌آمد.
    سودی که هزینه‌ی فروش را نبیند، همیشه بیشتر از واقعیت است.

    مثل درآمد ربات، فقط مستاجرهای ریشه: پورسانتِ معرف‌های یک
    نماینده، هزینه‌ی همان نماینده است.
    """
    con = _bot_conn()
    if not con:
        return 0, 0
    try:
        roots = "(SELECT id FROM tenants WHERE parent_id IS NULL)"
        paid = con.execute(
            f"SELECT COALESCE(SUM(amount),0) s FROM affiliate_payouts "
            f"WHERE tenant_id IN {roots}").fetchone()
        earned = con.execute(
            f"SELECT COALESCE(SUM(commission),0) s FROM affiliate_commissions "
            f"WHERE status != 'cancelled' AND tenant_id IN {roots}").fetchone()
        p = int((paid["s"] if paid else 0) or 0)
        e = int((earned["s"] if earned else 0) or 0)
        return p, max(0, e - p)
    except Exception:
        log.debug("خواندن پورسانت معرف‌ها ناموفق", exc_info=True)
        return 0, 0
    finally:
        con.close()


@app.get("/api/admin/billing/ledger")
def billing_ledger(x_admin_password: str = Header(...)):
    """
    دفتر کل از روز اول: چه کسی چقدر بدهکار است و سود واقعی چقدر بوده.

    «درآمد» بدون کم‌کردن هزینه‌ها عددی است که آدم را خوشحال و
    ورشکسته می‌کند. این‌جا هر دو طرف با هم می‌آیند.
    """
    check_auth(x_admin_password)

    overview = _billing_overview_impl()
    groups = overview.get("groups") or []

    # این صفحه «از روز اول» است و هزینه‌ها هم بدون هیچ برشی جمع
    # می‌شوند. وقتی نمای کلی دوره‌ای شد، این‌جا هنوز همان کلیدها را
    # می‌خواند — یعنی درآمدِ سه ماه در برابر هزینه‌ی دو سال، و
    # «سود واقعی تا امروز» از مثبت به منفی می‌پرید به‌محض اینکه
    # مدیر یک تاریخ تسویه ثبت می‌کرد.
    billed = sum(g.get("dueAll", g.get("due", 0)) for g in groups
                 if g.get("billable"))
    paid = sum(g.get("paidAll", g.get("paid", 0)) for g in groups
               if g.get("billable"))

    con = _billing_conn()
    try:
        spent = con.execute(
            "SELECT COALESCE(SUM(amount_irt),0) s FROM expenses").fetchone()["s"]
        by_kind = {r["kind"]: r["s"] for r in con.execute(
            "SELECT kind, COALESCE(SUM(amount_irt),0) s FROM expenses "
            "GROUP BY kind")}
        first_pay = con.execute(
            "SELECT MIN(paid_at) d FROM payments").fetchone()["d"]
        first_exp = con.execute(
            "SELECT MIN(spent_at) d FROM expenses").fetchone()["d"]
    finally:
        con.close()

    # فروش مستقیم ربات هم درآمد است و همین سرورها را خرج می‌کند.
    # بدون آن، «سود واقعی» فقط نیمی از کسب‌وکار را می‌بیند.
    bot_in = _bot_money_in()
    aff_paid, aff_owed = _affiliate_money_out()

    # «چه کسی بدهکار است» سوالِ امروز است، نه سوالِ تاریخ: بدهیِ
    # دوره‌ی تسویه‌شده دیگر طلب نیست.
    outstanding = sum(g.get("balance", 0) for g in groups if g.get("billable"))

    debtors = sorted(
        [{"key": g["key"], "label": g.get("label") or g["key"],
          "due": g.get("due", 0), "paid": g.get("paid", 0),
          "dueAll": g.get("dueAll", 0), "paidAll": g.get("paidAll", 0),
          "balance": g.get("balance", 0),
          "configs": g.get("configs", 0),
          "unpriced": g.get("unpriced", 0)}
         for g in groups if g.get("billable")],
        key=lambda g: -g["balance"])

    return {
        "ready": overview.get("ready", True),
        "error": overview.get("error"),
        # از ابتدای تاریخ، نه فقط دوره‌ی جاری
        # قدیمی‌ترین رویداد ثبت‌شده — یعنی «از کی» این اعداد را می‌شمریم
        "since": min([d for d in (first_pay, first_exp) if d], default=None),
        "billed": billed,
        "paid": paid,
        # طلبِ امروز، نه اختلاف تاریخی
        "outstanding": outstanding,
        "spent": spent,
        "spentByKind": {k: by_kind.get(k, 0) for k in EXPENSE_KINDS},
        "botReceived": bot_in,
        "affiliatePaid": aff_paid,
        # هنوز پرداخت نشده، پس از سود کم نمی‌شود — ولی تعهدی است که
        # باید دیده شود، وگرنه سودِ امروز فردا آب می‌رود.
        "affiliateOwed": aff_owed,
        "profit": paid + bot_in - spent - aff_paid,
        # «اگر همه تسویه کنند» یعنی آنچه گرفته‌ام + آنچه هنوز طلب دارم،
        # منهای هزینه. قبلاً billed - spent بود، یعنی کلِ تاریخِ
        # صورتحساب — که اگر دوره‌ای با تخفیف یا گِردکردن بسته شده
        # باشد، آن اختلاف را دوباره طلب حساب می‌کرد.
        "profitIfAllPaid": (paid + bot_in + outstanding
                            - spent - aff_paid - aff_owed),
        # اختلاف «صورت‌حساب‌شده منهای دریافت‌شده» با «طلب شما»: همان
        # دوره‌هایی که تسویه‌شده اعلام شده‌اند. بدون این عدد، چهار
        # کارتِ بالای صفحه با هم جور درنمی‌آیند و صفحه شبیه خرابی
        # به نظر می‌رسد.
        "settledGap": (billed - paid) - outstanding,
        "debtors": debtors,
        "owing": [d for d in debtors if d["balance"] > 0],
        "credit": [d for d in debtors if d["balance"] < 0],
    }


@app.get("/api/admin/billing/payments")
def billing_payments_get(group: str = "", x_admin_password: str = Header(...)):
    """فهرست پرداخت‌ها."""
    check_auth(x_admin_password)
    try:
        con = _billing_conn()
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"دیتابیس حسابداری باز نشد: {str(e)[:120]}")
    try:
        if group:
            rows = con.execute(
                "SELECT * FROM payments WHERE group_key=? ORDER BY paid_at DESC, id DESC",
                (group,)).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM payments ORDER BY paid_at DESC, id DESC LIMIT 200").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["group_name"] = d.get("group_key")   # نام مترادف
            out.append(d)
        return {"payments": out}
    finally:
        con.close()


@app.post("/api/admin/billing/payment")
@app.post("/api/admin/billing/payments")
def billing_payment_add(payload: dict, x_admin_password: str = Header(...)):
    """ثبت یک پرداخت."""
    check_auth(x_admin_password)
    payload = payload or {}

    # نام‌های مترادف — رابط کاربری group/date می‌فرستد،
    # اسکریپت‌ها و API از group_key/paid_at استفاده می‌کنند
    g = (payload.get("group_key") or payload.get("group") or "").strip()
    if not g:
        raise HTTPException(status_code=400, detail="واسطه مشخص نشده است")
    try:
        amount = int(payload.get("amount", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="مبلغ نامعتبر است")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="مبلغ باید بیشتر از صفر باشد")

    con = _billing_conn()
    try:
        cur = con.execute(
            "INSERT INTO payments (group_key,amount,paid_at,note) VALUES (?,?,?,?)",
            (g, amount,
             (payload.get("paid_at") or payload.get("date")
              or datetime.now().strftime("%Y-%m-%d")),
             (payload.get("note") or "").strip()))
        con.commit()
        return {"ok": True, "id": cur.lastrowid}
    finally:
        con.close()


@app.post("/api/admin/billing/settle")
def billing_settle(payload: dict, x_admin_password: str = Header(...)):
    """
    تسویه‌ی یک واسطه: پول را ثبت می‌کند **و** دوره را می‌بندد.

    چرا یک تابع، نه دو تا:
        تا امروز «پرداخت گرفتم» و «این دوره بسته شد» دو کارِ جدا در
        دو صفحه‌ی جدا بودند. مالک پول را ثبت می‌کرد و تمام — ولی
        `settled_until` دست‌نخورده می‌ماند و فاکتور ماه بعد **همان
        کاربران و همان دوره را دوباره می‌آورد**.

        این واقعاً اتفاق افتاد: مالک بر اساس همان فاکتور، پولِ دوره‌ی
        قبل را دوباره از واسطه گرفت.

        همان شکلِ آشنای این مخزن — پول یک جا ثبت می‌شود، وضعیت جای
        دیگر، و از هم دور می‌افتند. پس مثل `close_order` یکی شدند.

    عقب‌بردن تاریخ ممنوع است: اگر دوره‌ای یک‌بار بسته شده، بازکردنش
    یعنی دوباره‌حساب‌کردنِ چیزی که پولش گرفته شده. برای آن حالت باید
    آگاهانه از صفحه‌ی «واسطه‌ها و نرخ» دست برد.
    """
    check_auth(x_admin_password)
    p = payload or {}

    g = (p.get("group_key") or p.get("group") or "").strip()
    if not g:
        raise HTTPException(status_code=400, detail="واسطه مشخص نشده است")

    try:
        amount = int(p.get("amount") or 0)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="مبلغ نامعتبر است")
    if amount < 0:
        raise HTTPException(status_code=400, detail="مبلغ منفی معنا ندارد")

    until = (p.get("until") or p.get("settled_until")
             or p.get("settledUntil") or "").strip()[:10]
    if not until:
        until = datetime.now().strftime("%Y-%m-%d")
    from datetime import date as _date
    try:
        _date.fromisoformat(until)
    except ValueError:
        raise HTTPException(status_code=400, detail="تاریخ تسویه نامعتبر است")

    con = _billing_conn()
    try:
        row = con.execute(
            "SELECT settled_until, label FROM group_config WHERE group_key=?",
            (g,)).fetchone()
        prev = ((row["settled_until"] if row else "") or "").strip()[:10]

        if prev and until < prev:
            raise HTTPException(
                status_code=409,
                detail=(f"این گروه تا {prev} تسویه شده و تاریخ تازه عقب‌تر "
                        "است. عقب‌بردنش یعنی دوباره‌حساب‌کردنِ چیزی که "
                        "پولش گرفته شده."))

        if amount > 0:
            con.execute(
                "INSERT INTO payments (group_key,amount,paid_at,note) "
                "VALUES (?,?,?,?)",
                (g, amount, until, (p.get("note") or "تسویه").strip()))

        # گروه ممکن است هنوز ردیفی در group_config نداشته باشد
        con.execute(
            "INSERT INTO group_config (group_key,label,settled_until) "
            "VALUES (?,?,?) ON CONFLICT(group_key) DO UPDATE SET "
            "settled_until=excluded.settled_until, "
            "updated_at=CURRENT_TIMESTAMP",
            (g, g, until))
        con.commit()
    finally:
        con.close()

    return {"ok": True, "group": g, "settledUntil": until,
            "previousSettledUntil": prev or None, "amount": amount,
            "note": f"تا {until} تسویه شد — فاکتور بعدی از همین تاریخ "
                    "به بعد را حساب می‌کند"}


@app.delete("/api/admin/billing/payment/{pid}")
@app.delete("/api/admin/billing/payments/{pid}")
def billing_payment_del(pid: int, x_admin_password: str = Header(...)):
    """حذف یک پرداخت."""
    check_auth(x_admin_password)
    con = _billing_conn()
    try:
        con.execute("DELETE FROM payments WHERE id=?", (pid,))
        con.commit()
        return {"ok": True}
    finally:
        con.close()


@app.get("/api/admin/billing/invoice/{group_key}")
def billing_invoice(group_key: str, start: str = "",
                    x_admin_password: str = Header(...)):
    """
    جزئیات کامل یک واسطه — برای صورتحساب.

    `start` اختیاری است؛ اگر ندهید خودِ تنظیمات گروه تصمیم می‌گیرد
    («تسویه‌شده تا» و بعد «شروع همکاری»). هرچه پیش از آن تاریخ بوده —
    چه ساختِ کانفیگ و چه تمدید — روی این فاکتور نمی‌آید.

    تا پیش از این، این تابع هیچ تاریخی نمی‌دید و کل عمر هر کانفیگ را
    حساب می‌کرد؛ یعنی واسطه‌ای که ماه پیش تسویه کرده بود، این ماه
    دوباره همان تمدیدها را روی فاکتورش می‌دید.
    """
    check_auth(x_admin_password)

    clients, _known, err = _read_xui_clients()
    if clients is None:
        raise HTTPException(status_code=400, detail=err)

    bcon = _billing_conn()
    try:
        # مصرفِ دوره‌های ریست‌شده. بدونِ این، همان عددِ پس‌از‌ریست
        # روی فاکتور می‌رود.
        _attach_total_usage(bcon, clients)
        row = bcon.execute("SELECT * FROM group_config WHERE group_key=?",
                           (group_key,)).fetchone()
        conf = dict(row) if row else {}
        try:
            rates = json.loads(conf.get("rates") or "[]")
        except (json.JSONDecodeError, TypeError):
            rates = []
        logged = {r["email"]: r["m"] for r in bcon.execute(
            "SELECT email, COALESCE(SUM(months),0) m FROM renewals GROUP BY email")}
        rows_by = _rows_by_email([dict(r) for r in bcon.execute(
            "SELECT email, months, created_at FROM renewals")])
        # «از کی می‌شناسیمش» — برای کانفیگ‌هایی که x-ui تاریخ ساختشان
        # را ندارد. بدون این، به‌محض فعال‌شدن بازه هیچ‌کدامشان
        # دوره‌بندی نمی‌شدند و بی‌صدا از فاکتور می‌افتادند.
        try:
            seen = {r["email"]: r["first_seen"] for r in bcon.execute(
                "SELECT email, first_seen FROM client_seen")}
        except Exception:
            seen = {}
        since, since_why = _bill_since(conf, start)
        if since:
            # پرداختی هم باید با همان تاریخ بریده شود. وگرنه فاکتورِ
            # دوره‌ی تازه، پول دوره‌ی تسویه‌شده را هم اعتبار حساب
            # می‌کند و مانده منفیِ ساختگی درمی‌آید.
            paid = bcon.execute(
                "SELECT COALESCE(SUM(amount),0) s FROM payments "
                "WHERE group_key=? AND COALESCE(paid_at,'') >= ?",
                (group_key, since)).fetchone()["s"]
        else:
            paid = bcon.execute(
                "SELECT COALESCE(SUM(amount),0) s FROM payments WHERE group_key=?",
                (group_key,)).fetchone()["s"]
    finally:
        bcon.close()

    lines, due = [], 0
    before_configs = before_months = 0
    unused_configs, unused_why = 0, {}
    for cl in clients:
        if cl["group"] != group_key:
            continue

        # همان قاعده‌ای که نمای کلی به کار می‌برد.
        #
        # تا پیش از این فقط نمای کلی این را می‌دید: کانفیگی که ساخته
        # شده و هرگز به کار نیفتاده، روی داشبورد کنار گذاشته می‌شد و
        # دلیلش هم نوشته می‌شد — ولی روی *فاکتور* پول می‌گرفت. یعنی
        # واسطه بابت چیزی صورتحساب می‌گرفت که قاعده‌ی خودِ مالک
        # می‌گفت نباید حساب شود، و آن فاکتور همان چیزی است که دستش
        # می‌رسد.
        bill_it, why = _billable_config(cl)
        if not bill_it:
            unused_configs += 1
            unused_why[why] = unused_why.get(why, 0) + 1
            continue

        fseen = seen.get(cl["email"])
        created_j, created_g = _to_jalali(cl.get("createdAt"))

        # ── چه تکه‌ای از عمر این کانفیگ روی *این* فاکتور می‌آید ──
        billed, months, ren_in, is_new, kind, drift = _period_share(
            cl, logged, rows_by.get(cl["email"], []), since,
            group_start=conf.get("period_start"), first_seen=fseen)

        if billed <= 0:
            # کاملاً پیش از مبدأ — تسویه‌شده. از جدول بیرون می‌ماند
            # ولی شمرده می‌شود، تا فاکتورِ کوتاه خودش توضیح بدهد چرا
            # کوتاه است.
            before_configs += 1
            before_months += months
            continue

        gb = _gb_of(cl["totalGB"])
        amount, price, per_dev, extra_dev = _line_amount(
            gb, rates, billed, cl.get("limitIp"))
        price_why = None
        if price is None:
            _, price_why = _price_with_reason(gb, rates)
        due += amount
        expiry_j, expiry_g = _to_jalali(cl.get("expiry"))
        days = _duration_days(cl.get("createdAt"), cl.get("expiry"))
        # درصد روی *دوره‌ی جاری* می‌ماند: «۱۹۰٪ از سهمیه» عددِ
        # بی‌معنایی است. ولی گیگابایتِ نمایشی جمعِ همه‌ی دوره‌هاست،
        # چون همان است که مشتری واقعاً مصرف کرده.
        pct = _usage_percent(cl["used"], cl["totalGB"])

        # وضعیت هر ردیف — برای بخش «نیازمند بررسی دستی»
        if not cl.get("expiry"):
            status = "بدون انقضا"
        elif cl.get("expiry", 0) < 0:
            status = "شروع‌نشده"
        elif not cl["enable"]:
            status = "غیرفعال"
        else:
            status = "فعال"

        lines.append({
            "email": cl["email"],
            "gb": gb,
            "gbLabel": "∞" if gb == 0 else str(gb),
            "usedGB": round(cl["usedTotal"] / (1024 ** 3), 1),
            "usagePct": pct,
            "limitIp": cl.get("limitIp") or 0,
            "createdJalali": created_j,
            "createdGregorian": created_g,
            "expiryJalali": expiry_j,
            "expiryGregorian": expiry_g,
            "days": days,
            "months": billed,
            "renewals": ren_in,
            "newInPeriod": is_new,
            # عمر کامل، برای وقتی که مدیر می‌خواهد بداند این کانفیگ
            # در کل چقدر بوده — نه فقط سهم این دوره
            "totalMonths": months,
            "totalRenewals": months - 1,
            "kind": kind,
            "drift": drift,
            "price": price,
            "priceWhy": price_why,
            "perDevice": per_dev,
            "extraDevices": extra_dev,
            "deviceAmount": per_dev * extra_dev * billed,
            "amount": amount,
            "active": cl["enable"],
            "status": status,
            "expiry": cl["expiry"],
        })

    # ترتیب: بر اساس تاریخ ایجاد، مثل فاکتور دستی — چون واسطه
    # می‌خواهد ترتیب زمانی فروش را ببیند، نه ترتیب مبلغ
    lines.sort(key=lambda x: (x.get("createdGregorian") or "9999", x["email"]))

    quota_gb = sum(l["gb"] for l in lines)
    used_gb = round(sum(l["usedGB"] for l in lines), 1)
    configs = len(lines)
    renewals = sum(l["renewals"] for l in lines)

    totals = {
        "configs": configs,
        "months": sum(l["months"] for l in lines),
        "renewals": renewals,
        "renewalRate": round(renewals * 100.0 / configs, 1) if configs else 0,
        "quotaGB": quota_gb,
        "usedGB": used_gb,
        "usagePct": round(used_gb * 100.0 / quota_gb, 1) if quota_gb else 0,
        "due": due,
        "paid": paid,
        "balance": due - paid,
        "unpriced": sum(1 for l in lines if l["price"] is None),
        "estimated": sum(1 for l in lines if l["kind"] == "تخمینی"),
        "active": sum(1 for l in lines if l["status"] == "فعال"),
        "inactive": sum(1 for l in lines if l["status"] == "غیرفعال"),
        "notStarted": sum(1 for l in lines if l["status"] == "شروع‌نشده"),
        "noExpiry": sum(1 for l in lines if l["status"] == "بدون انقضا"),
        # کانفیگ‌هایی که کاملاً پیش از مبدأ بوده‌اند
        "before": before_configs,
        "beforeMonths": before_months,
        # ساخته شده ولی هرگز به کار نیفتاده — با دلیل، نه فقط عدد
        "unused": unused_configs,
        "unusedWhy": unused_why,
    }

    # ردیف‌هایی که حسابدار باید خودش نگاهشان کند
    review = []
    for l in lines:
        reason = None
        if l["kind"] == "تخمینی" and l.get("drift", 0) >= 5:
            reason = f"مدت {l['days']} روز — انحراف {l['drift']} روز از مضرب ۳۰"
        elif l["status"] in ("بدون انقضا", "شروع‌نشده"):
            reason = "بدون تاریخ انقضا"
        elif l["price"] is None:
            # تفکیک دو حالت، چون راه‌حلشان فرق دارد: یکی نرخ نامحدود
            # می‌خواهد، دیگری اصلاً هیچ نرخی برای گروه تعریف نشده.
            if not l.get("gb"):
                reason = "کانفیگ نامحدود است و نرخ نامحدود تعریف نشده"
            else:
                reason = f"حجم {l['gbLabel']} GB نرخ ندارد"
        if reason:
            review.append({"email": l["email"], "status": l["status"],
                           "reason": reason,
                           "accuracy": "نامشخص" if l["status"] in ("بدون انقضا", "شروع‌نشده")
                                       else "پایین"})

    return {
        "group": group_key,
        "name": group_key,
        "label": conf.get("label") or group_key,
        "rates": rates,
        "lines": lines,
        # نام‌های مترادف برای بخش‌هایی از رابط که اسم دیگری می‌خوانند
        "items": lines,
        "totalAmount": totals["due"],
        "paid": totals["paid"],
        "balance": totals["balance"],
        # از چه تاریخی حساب شده و چرا — بدون این، فاکتورِ کوتاه
        # مثل فاکتورِ خراب به نظر می‌رسد
        "since": since or None,
        "sinceWhy": since_why or None,
        "sinceJalali": (_to_jalali(_epoch_ms(since))[0]
                        if since else None),
        # فهرست حجم‌های بی‌نرخ، نه تعدادشان.
        #
        # این‌جا totals["unpriced"] گذاشته شده بود که یک عدد است، و
        # رابط کاربری روی همان .length و .map صدا می‌زد — یعنی هشدارِ
        # «حجم بدون نرخ» هرگز نمایش داده نمی‌شد.
        "unpricedVolumes": sorted({l["gb"] for l in lines
                                   if l["price"] is None}),
        # دلیل‌ها، نه فقط شمارش — همان چیزی که مدیر برای درست‌کردنش
        # لازم دارد
        "unpricedWhy": sorted({l["priceWhy"] for l in lines
                               if l["price"] is None and l.get("priceWhy")}),
        "totals": totals,
        "review": review,
        "generatedAt": _to_jalali(int(datetime.now().timestamp() * 1000))[0],
    }


@app.get("/api/admin/billing/backup")
def billing_backup(x_admin_password: str = Header(...)):
    """بک‌آپ کامل حسابداری — نرخ‌ها، پرداخت‌ها و لاگ تمدید."""
    check_auth(x_admin_password)
    try:
        con = _billing_conn()
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"دیتابیس حسابداری باز نشد: {str(e)[:120]}")
    try:
        dump = {}
        for t in _tables_of(con, ("group_config", "payments", "renewals",
                                  "expenses", "client_seen")):
            try:
                dump[t] = [dict(r) for r in con.execute(f"SELECT * FROM {t}")]
            except Exception:
                dump[t] = []
        return {
            "version": 1,
            "createdAt": datetime.now().isoformat(timespec="seconds"),
            "counts": {k: len(v) for k, v in dump.items()},
            "data": dump,
        }
    finally:
        con.close()


@app.post("/api/admin/billing/restore")
def billing_restore(payload: dict, x_admin_password: str = Header(...)):
    """
    بازیابی بک‌آپ حسابداری.

    قبل از هر کاری یک نسخه‌ی امن از وضعیت فعلی گرفته می‌شود، چون
    نرخ‌ها و پرداخت‌ها داده‌ی مالی‌اند و از دست رفتنشان گران است.
    """
    check_auth(x_admin_password)
    data = (payload or {}).get("data")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="فایل بک‌آپ نامعتبر است")

    safety = None
    try:
        import shutil
        if BILLING_DB.exists():
            safety = BILLING_DB.with_name(
                f"billing-before-restore-{datetime.now():%Y%m%d-%H%M%S}.db")
            shutil.copy2(BILLING_DB, safety)
    except Exception:
        pass

    con = _billing_conn()
    try:
        restored, skipped = {}, {}
        # فقط جدول‌هایی که هم در فایل‌اند و هم در این دیتابیس. قبلاً
        # سه جدولِ ثابت بی‌قید خالی می‌شدند — یعنی بازگردانیِ یک
        # پشتیبانِ قدیمی، داده‌ی جدول‌هایی را که در آن نبود پاک می‌کرد.
        for t in [x for x in _tables_of(con, ("group_config", "payments",
                                              "renewals", "expenses",
                                              "client_seen"))
                  if x in data]:
            rows = data.get(t) or []
            try:
                con.execute(f"DELETE FROM {t}")
            except Exception:
                pass
            if not rows:
                restored[t] = 0
                continue
            cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
            usable = [x for x in cols if any(x in r for r in rows)]
            if not usable:
                restored[t] = 0
                continue
            ph = ",".join("?" * len(usable))
            sql = f"INSERT OR REPLACE INTO {t} ({','.join(usable)}) VALUES ({ph})"
            n = 0
            for r in rows:
                try:
                    con.execute(sql, [r.get(x) for x in usable])
                    n += 1
                except Exception:
                    pass
            restored[t] = n
            if n < len(rows):
                skipped[t] = len(rows) - n
        con.commit()
        out = {"ok": True, "restored": restored,
               "safetyCopy": str(safety) if safety else None}
        if skipped:
            out["skipped"] = skipped
            out["warning"] = ("بعضی ردیف‌ها بازنگشتند: "
                              + "، ".join(f"{k} ({v})"
                                          for k, v in skipped.items()))
        return out
    finally:
        con.close()


@app.get("/api/admin/billing/xui-path")
def billing_xui_path(x_admin_password: str = Header(...)):
    """
    وضعیت مسیر دیتابیس x-ui — برای بخش تنظیمات.

    مسیرهای رایج را هم بررسی می‌کند تا اگر جای دیگری نصب شده،
    کاربر مجبور نباشد حدس بزند.
    """
    check_auth(x_admin_password)
    cur = _xui_db_path()

    found = []
    for p in XUI_CANDIDATES:
        pp = Path(p)
        if pp.exists():
            found.append({"path": p, "readable": os.access(pp, os.R_OK),
                          "size": pp.stat().st_size})

    # تست واقعی اتصال — نه فقط بررسی وجود فایل
    con, err = _xui_conn()
    tables = []
    if con:
        try:
            tables = [r["name"] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        except Exception:
            pass
        finally:
            con.close()

    return {
        "current": str(cur),
        "exists": cur.exists(),
        "readable": cur.exists() and os.access(cur, os.R_OK),
        "connected": con is not None or err is None,
        "error": err,
        "tables": tables[:30],
        "hasClients": "clients" in tables or "client_traffics" in tables,
        "hasGroups": "client_groups" in tables,
        "found": found,
        "envVar": os.getenv("XUI_DB_PATH", ""),
    }


def _fa(text):
    """
    آماده‌سازی متن فارسی برای PDF.

    reportlab حروف را نمی‌چسباند و راست‌به‌چپ نمی‌کند، پس قبلش
    خودمان شکل‌دهی و ترتیب را درست می‌کنیم. اگر کتابخانه‌ها نبودند،
    متن خام برمی‌گردد تا حداقل چیزی چاپ شود.
    """
    s = str(text or "")
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(s))
    except Exception:
        return s


def _pdf_font(bold=False):
    """
    فونت فارسی برای PDF.

    اول ایران‌سنس همراه پروژه، بعد فونت‌های سیستم. هر فونت با یک
    نمونه‌ی واقعی آزمایش می‌شود چون خیلی‌ها حروف پایه را دارند ولی
    گلیف‌های اتصالی را نه، و نتیجه مربع خالی می‌شود.
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    key = "NexoraFA-Bold" if bold else "NexoraFA"
    if key in pdfmetrics.getRegisteredFontNames():
        return key

    try:
        import arabic_reshaper
        probe = arabic_reshaper.reshape("صورتحساب مبلغ باقی‌مانده")
    except Exception:
        probe = "\ufebb\ufeee\ufead\ufe97\ufea4\ufeb4"

    def covers(path):
        try:
            from fontTools.ttLib import TTFont as FT
            ft = FT(path, fontNumber=0, lazy=True)
            cmap = set(ft.getBestCmap().keys())
            ft.close()
            return {ord(ch) for ch in probe if ch.strip()}.issubset(cmap)
        except Exception:
            return False

    import glob
    fonts_dir = _root_dir() / "assets" / "fonts"
    want = "Bold" if bold else "Regular"

    candidates = []
    # فونت همراه پروژه، با وزن درست
    candidates += sorted(glob.glob(str(fonts_dir / f"*{want}*.ttf")))
    candidates += sorted(glob.glob(str(fonts_dir / "*.ttf")))
    candidates += sorted(glob.glob(str(_root_dir() / "assets" / "*.ttf")))

    system = glob.glob("/usr/share/fonts/**/*.ttf", recursive=True)
    prefer = ("iransans", "vazir", "sahel", "shabnam", "naskh", "arabic")
    candidates += [f for f in system
                   if any(p in f.lower() for p in prefer)
                   and (want.lower() in f.lower() or not bold)]
    candidates += [f for f in system
                   if "bold" not in f.lower() and "italic" not in f.lower()]

    for path in candidates:
        if covers(path):
            try:
                pdfmetrics.registerFont(TTFont(key, path))
                return key
            except Exception:
                continue

    return "Helvetica-Bold" if bold else "Helvetica"


@app.get("/api/admin/bot/users/report/pdf")
def bot_users_report_pdf(days: int = 30, x_admin_password: str = Header(...)):
    """
    گزارش فروش ربات به‌صورت PDF — با همان قالب و رنگ صورتحساب واسطه.

    چیزی که فقط روی صفحه است را نمی‌شود بایگانی کرد یا برای شریک
    فرستاد؛ به همین دلیل نسخه‌ی چاپی لازم است. و چون کنار صورتحساب
    حسابداری بایگانی می‌شود، باید همان شکل را داشته باشد نه یک جدول
    ساده‌ی بی‌قواره.
    """
    check_auth(x_admin_password)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas as pdfcanvas
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="reportlab نصب نیست: pip install reportlab arabic-reshaper python-bidi")

    rep = bot_users_report(days=days, x_admin_password=x_admin_password)
    if not rep.get("ready"):
        raise HTTPException(status_code=400,
                            detail=rep.get("error") or "گزارش در دسترس نیست")

    F = _pdf_font()
    FB = _pdf_font(bold=True)

    import io as _io
    buf = _io.BytesIO()
    W, H = A4
    c = pdfcanvas.Canvas(buf, pagesize=A4)

    # همان پالت صورتحساب — روشن و چاپ‌پذیر
    NAVY = colors.HexColor("#1F3864")
    INK = colors.HexColor("#1A1A1A")
    GREY = colors.HexColor("#555555")
    MUTE = colors.HexColor("#8A92A0")
    LINE = colors.HexColor("#CFD6E4")
    SOFT = colors.HexColor("#F6F8FC")
    CARD = colors.HexColor("#FAFBFD")
    HEAD = colors.HexColor("#E8EDF6")
    GOOD = colors.HexColor("#14683C")

    def money(n):
        return f"{int(n or 0):,}"

    stamp = datetime.now()
    doc_no = f"NX-R-{stamp:%Y%m%d}-{days}"

    ML, MR = 14 * mm, 14 * mm
    CW = W - ML - MR
    page = [0]

    def footer():
        c.setFont(F, 7)
        c.setFillColor(MUTE)
        c.drawCentredString(W / 2, 8 * mm,
                            _fa(f"گزارش نکسورا — صفحه {page[0]}"))

    def header():
        c.setFillColor(colors.white)
        c.rect(0, 0, W, H, fill=1, stroke=0)

        y0 = H - 14 * mm
        c.setFont(FB, 19)
        c.setFillColor(NAVY)
        c.drawString(ML, y0 - 4 * mm, "NEXORA")
        c.setFont(F, 8)
        c.setFillColor(GREY)
        c.drawString(ML, y0 - 9.5 * mm, _fa("گزارش فروش ربات تلگرام"))

        c.setFont(F, 8)
        meta = [
            (_fa("شماره گزارش") + ": ", doc_no),
            (_fa("تاریخ صدور") + ": ", stamp.strftime("%Y-%m-%d")),
            (_fa("بازه") + ": ", _fa(f"{days} روز گذشته")),
        ]
        yy = y0 - 3 * mm
        for label, val in meta:
            c.setFillColor(GREY)
            tw = c.stringWidth(val, F, 8)
            c.drawRightString(W - MR, yy, val)
            c.setFillColor(MUTE)
            c.drawRightString(W - MR - tw - 1 * mm, yy, label)
            yy -= 4.5 * mm

        c.setStrokeColor(NAVY)
        c.setLineWidth(1.8)
        c.line(ML, H - 28 * mm, W - MR, H - 28 * mm)
        footer()
        return H - 38 * mm

    y = header()

    o = rep.get("orders") or {}
    u = rep.get("users") or {}
    subs = rep.get("subs") or {}

    # ── کارت‌های خلاصه ──
    cards = [
        ("کاربر جدید", f"{int(u.get('newUsers') or 0):,}", NAVY),
        ("خریدار", f"{int(rep.get('buyerCount') or 0):,}", NAVY),
        ("سفارش موفق", f"{int(o.get('approved') or 0):,}", GOOD),
        # «فروش»، نه «درآمد»: سفارشی که از کیف پول پرداخت شده در این
        # عدد هست، ولی پول تازه‌ای با آن نرسیده.
        ("فروش (تومان)", money(o.get("revenue")), GOOD),
    ]
    cw = CW / len(cards)
    for idx, (label, val, col) in enumerate(cards):
        x = ML + idx * cw
        c.setFillColor(CARD)
        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        c.roundRect(x + 1.2 * mm, y - 17 * mm, cw - 2.4 * mm, 17 * mm,
                    2 * mm, fill=1, stroke=1)
        c.setFont(F, 7.5)
        c.setFillColor(MUTE)
        c.drawCentredString(x + cw / 2, y - 5.5 * mm, _fa(label))
        c.setFont(FB, 13)
        c.setFillColor(col)
        c.drawCentredString(x + cw / 2, y - 13 * mm, val)
    y -= 26 * mm

    # ── خلاصه‌ی دوره ──
    detail = [
        ("نرخ تبدیل بازدید به خرید", f"{rep.get('conversion') or 0}%"),
        ("میانگین هر سفارش", money(o.get("avg")) + " " + _fa("تومان")),
        ("سفارش رد شده", f"{int(o.get('rejected') or 0):,}"),
        ("سفارش در انتظار", f"{int(o.get('pending') or 0):,}"),
        ("اشتراک فعال", f"{int(subs.get('active') or 0):,}"),
    ]
    c.setFont(FB, 9.5)
    c.setFillColor(NAVY)
    c.drawRightString(W - MR, y, _fa("خلاصه‌ی دوره"))
    y -= 6 * mm

    for idx, (label, val) in enumerate(detail):
        if idx % 2 == 0:
            c.setFillColor(SOFT)
            c.rect(ML, y - 2.2 * mm, CW, 6.8 * mm, fill=1, stroke=0)
        c.setFont(F, 8.5)
        c.setFillColor(MUTE)
        c.drawRightString(W - MR - 2 * mm, y, _fa(label))
        c.setFillColor(INK)
        c.drawString(ML + 2 * mm, y, val)
        y -= 6.8 * mm

    y -= 8 * mm

    # ── بیشترین خریداران ──
    c.setFont(FB, 9.5)
    c.setFillColor(NAVY)
    c.drawRightString(W - MR, y, _fa("بیشترین خریداران"))
    y -= 7 * mm

    COL_AMOUNT = ML + 2 * mm
    COL_ORDERS = ML + 42 * mm

    def table_head(yy):
        c.setFillColor(HEAD)
        c.rect(ML, yy - 2.4 * mm, CW, 7.5 * mm, fill=1, stroke=0)
        c.setFont(FB, 8)
        c.setFillColor(NAVY)
        c.drawString(COL_AMOUNT, yy, _fa("مبلغ (تومان)"))
        c.drawString(COL_ORDERS, yy, _fa("سفارش"))
        c.drawRightString(W - MR - 2 * mm, yy, _fa("مشتری"))
        return yy - 8.5 * mm

    y = table_head(y)

    buyers = rep.get("buyers") or []
    if not buyers:
        c.setFont(F, 8.5)
        c.setFillColor(MUTE)
        c.drawCentredString(W / 2, y, _fa("در این بازه خریدی ثبت نشده است"))
        y -= 8 * mm
    else:
        for idx, b in enumerate(buyers[:30]):
            if y < 28 * mm:
                c.showPage()
                y = table_head(header())
            if idx % 2 == 0:
                c.setFillColor(SOFT)
                c.rect(ML, y - 2.2 * mm, CW, 6.8 * mm, fill=1, stroke=0)
            name = (b.get("first_name") or b.get("username")
                    or str(b.get("tg_id") or ""))
            c.setFont(F, 8.5)
            c.setFillColor(INK)
            c.drawString(COL_AMOUNT, y, money(b.get("spent")))
            c.setFillColor(GREY)
            c.drawString(COL_ORDERS, y, f"{int(b.get('orders') or 0):,}")
            c.setFillColor(INK)
            c.drawRightString(W - MR - 2 * mm, y, _fa(str(name)[:38]))
            y -= 6.8 * mm

        total = sum(int(b.get("spent") or 0) for b in buyers)
        c.setStrokeColor(NAVY)
        c.setLineWidth(0.9)
        c.line(ML, y - 0.5 * mm, W - MR, y - 0.5 * mm)
        y -= 6.5 * mm
        c.setFont(FB, 9)
        c.setFillColor(NAVY)
        c.drawString(COL_AMOUNT, y, money(total))
        c.drawRightString(W - MR - 2 * mm, y, _fa("جمع کل"))
        y -= 9 * mm

    # ── روند روزانه ──
    #
    # نمودار میله‌ای ساده و بدون کتابخانه: روند فروش را در یک نگاه
    # نشان می‌دهد، که از یک ستون عدد خیلی گویاتر است.
    daily = rep.get("daily") or []
    if daily and y > 55 * mm:
        c.setFont(FB, 9.5)
        c.setFillColor(NAVY)
        c.drawRightString(W - MR, y, _fa("روند فروش روزانه"))
        y -= 8 * mm

        peak = max([int(x.get("sum") or 0) for x in daily] + [1])
        bar_h = 22 * mm
        n = min(len(daily), 30)
        shown = daily[-n:]
        bw = CW / n
        base = y - bar_h

        c.setStrokeColor(LINE)
        c.setLineWidth(0.5)
        c.line(ML, base, W - MR, base)

        for idx, x in enumerate(shown):
            v = int(x.get("sum") or 0)
            h = (v / peak) * bar_h if peak else 0
            bx = ML + idx * bw
            c.setFillColor(NAVY if v else LINE)
            c.rect(bx + bw * 0.22, base, bw * 0.56, max(h, 0.4),
                   fill=1, stroke=0)

        c.setFont(F, 6.5)
        c.setFillColor(MUTE)
        c.drawString(ML, base - 4 * mm, _fa(str(shown[0].get("d") or "")))
        c.drawRightString(W - MR, base - 4 * mm,
                          _fa(str(shown[-1].get("d") or "")))
        c.drawCentredString(W / 2, base - 4 * mm,
                            _fa("بیشترین روز: ") + money(peak))

    c.showPage()
    c.save()
    buf.seek(0)
    return Response(
        content=buf.read(),
        media_type="application/pdf",
        headers={"Content-Disposition":
                 "attachment; filename=nexora-bot-report-" + str(days) + "d.pdf"})


@app.get("/api/admin/billing/invoice/{group_key}/pdf")
def billing_invoice_pdf(group_key: str, start: str = "",
                        x_admin_password: str = Header(...)):
    """
    صورتحساب PDF برای ارسال به واسطه.

    زمینه‌ی روشن و چاپ‌پذیر — چون این فایل ممکن است چاپ شود یا در
    مکاتبات بماند، نه فقط روی صفحه دیده شود.
    """
    check_auth(x_admin_password)

    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.pdfgen import canvas as pdfcanvas
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="reportlab نصب نیست: pip install reportlab arabic-reshaper python-bidi")

    inv = billing_invoice(group_key, start=start,
                          x_admin_password=x_admin_password)
    lines, t = inv["lines"], inv["totals"]
    F = _pdf_font()
    FB = _pdf_font(bold=True)

    import io
    buf = io.BytesIO()
    W, H = landscape(A4)
    class _Numbered(pdfcanvas.Canvas):
        """
        بومی که «صفحه x از y» را درست می‌نویسد.

        قبلاً تعداد کل از روی ارتفاع ردیف‌ها *پیش‌بینی* می‌شد، و
        پیش‌بینی همیشه یک صفحه‌ی اضافه برای توضیحات فرض می‌کرد. روی
        فاکتور ۹۴ کانفیگی، شش صفحه ساخته می‌شد و پایینشان می‌نوشت
        «از ۷».

        بدتر از آن: فوتر اولِ هر صفحه کشیده می‌شد، یعنی صفحه‌ی اول
        قبل از محاسبه‌ی تعداد کل — پس همیشه «صفحه ۱ از ۱» بود و
        فاکتور شش صفحه‌ای تمام‌شده به نظر می‌رسید.

        این‌جا هیچ چیزی پیش‌بینی نمی‌شود: صفحه‌ها کنار گذاشته
        می‌شوند و فوترها آخر کار، وقتی تعدادشان قطعی است، کشیده
        می‌شوند.
        """

        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self._pages = []

        def showPage(self):
            self._pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            # صفحه‌ی جاری هنوز بسته نشده — بدون این، آخرین صفحه‌ی
            # فاکتور (جمع‌ها و توضیحات) اصلاً در خروجی نمی‌آمد.
            self._pages.append(dict(self.__dict__))
            total = len(self._pages)
            for i, state in enumerate(self._pages, 1):
                self.__dict__.update(state)
                self._draw_footer(i, total)
                super().showPage()
            super().save()

        def _draw_footer(self, num, total):
            pass        # پایین‌تر، وقتی فونت و رنگ ساخته شدند، جا می‌افتد

    c = _Numbered(buf, pagesize=landscape(A4))

    # پالت روشن — برای چاپ
    NAVY = colors.HexColor("#1F3864")
    INK = colors.HexColor("#1A1A1A")
    GREY = colors.HexColor("#555555")
    MUTE = colors.HexColor("#8A92A0")
    LINE = colors.HexColor("#CFD6E4")
    SOFT = colors.HexColor("#F6F8FC")
    CARD = colors.HexColor("#FAFBFD")
    HEAD = colors.HexColor("#E8EDF6")
    REN = colors.HexColor("#DCE9FA")
    RENT = colors.HexColor("#14508C")
    WARNBG = colors.HexColor("#FDF6F0")
    WARNBD = colors.HexColor("#E4C9B4")
    WARNT = colors.HexColor("#9A4B12")

    def money(n):
        return f"{int(n or 0):,}"

    stamp = datetime.now()
    jnow = inv.get("generatedAt") or stamp.strftime("%Y/%m/%d")
    #: جای خالی در جدول.
    #
    #  خط تیره‌ی بلند (—) نبود: فونت فارسیِ سرور آن گلیف را ندارد و
    #  به‌جایش مربع خالی چاپ می‌شد. آزمایشِ فونت فقط حروف فارسی را
    #  می‌سنجد، نه علائمی که خودِ جدول می‌کشد. خط تیره‌ی ساده در هر
    #  فونتی هست.
    DASH = "-"
    inv_no = f"NX-{jnow.replace('/', '')}-1G"

    dates = [l.get("createdJalali") for l in lines if l.get("createdJalali")]
    span = f"{min(dates)} تا {max(dates)}" if dates else DASH

    # وقتی فاکتور از تاریخی به بعد حساب شده، *همان* باید بالای صفحه
    # بنشیند. واسطه‌ای که فاکتور کوتاه می‌گیرد باید در نگاه اول ببیند
    # که این فاکتورِ یک دوره است، نه فاکتور ناقصِ کل همکاری.
    since_j = inv.get("sinceJalali")
    if since_j:
        span_label = _fa("بازه صورتحساب") + ": "
        span_value = _fa(f"از {since_j} تا {jnow}")
    else:
        span_label = _fa("بازه کانفیگ‌ها") + ": "
        span_value = _fa(span)

    ML, MR = 10 * mm, 10 * mm
    CW = W - ML - MR
    page = [0]
    def _footer(self, num, total):
        self.setFont(F, 7)
        self.setFillColor(MUTE)
        self.drawCentredString(W / 2, 7 * mm,
                               _fa(f"صفحه {num} از {total}"))

    _Numbered._draw_footer = _footer

    def header():
        # شمارش صفحه کار بوم است، نه این‌جا.
        c.setFillColor(colors.white)
        c.rect(0, 0, W, H, fill=1, stroke=0)

        y = H - 12 * mm
        c.setFont(FB, 19)
        c.setFillColor(NAVY)
        c.drawString(ML, y - 4 * mm, "NEXORA")
        c.setFont(F, 8)
        c.setFillColor(GREY)
        c.drawString(ML, y - 9.5 * mm,
                     _fa("صورتحساب واسطه — گزارش کانفیگ‌های فروخته‌شده"))

        c.setFont(F, 8)
        c.setFillColor(GREY)
        rows_meta = [
            (_fa("شماره صورتحساب") + ": ", inv_no),
            (_fa("تاریخ صدور") + ": ", f"{jnow} ({stamp:%Y-%m-%d})"),
            (span_label, span_value),
        ]
        yy = y - 3 * mm
        for label, val in rows_meta:
            c.setFillColor(GREY)
            tw = c.stringWidth(val, F, 8)
            c.drawRightString(W - MR, yy, val)
            c.setFillColor(MUTE)
            c.drawRightString(W - MR - tw - 1 * mm, yy, label)
            yy -= 4.5 * mm

        c.setStrokeColor(NAVY)
        c.setLineWidth(1.8)
        c.line(ML, H - 26 * mm, W - MR, H - 26 * mm)
        return H - 34 * mm

    def end_page():
        """صفحه را می‌بندد. فوتر را خودِ بوم آخر کار می‌کشد."""
        c.showPage()

    # ─────────── صفحه‌ی اول ───────────
    y = header()

    # کادرهای خلاصه
    gap = 2.5 * mm
    hero_w = CW * 0.26
    small_w = (CW - hero_w - 4 * gap) / 4
    box_h = 19 * mm

    c.setFillColor(NAVY)
    c.roundRect(W - MR - hero_w, y - box_h, hero_w, box_h, 2 * mm, fill=1, stroke=0)
    c.setFont(F, 7.5)
    c.setFillColor(colors.HexColor("#B9C6DE"))
    # تیتر باید همان چیزی باشد که واسطه *باید بدهد*، نه کل فروش.
    #
    # قبلاً همیشه due چاپ می‌شد و پرداختی فقط در یک پانوشت ریز پایین
    # صفحه می‌آمد. واسطه‌ای که نصف حسابش را داده بود، بالای فاکتور
    # همان عدد اول را می‌دید و فکر می‌کرد پرداختش اصلاً ثبت نشده.
    _paid = int(t.get("paid") or 0)
    _bal = int(t.get("balance", t["due"]) or 0)
    c.drawRightString(W - MR - 3 * mm, y - 6 * mm,
                      _fa("مانده‌ی قابل پرداخت" if _paid else "مبلغ قابل پرداخت"))
    c.setFont(FB, 17)
    c.setFillColor(colors.white)
    c.drawRightString(W - MR - 3 * mm, y - 13 * mm,
                      money(_bal if _paid else t["due"]) + " " + _fa("تومان"))
    c.setFont(F, 6.5)
    c.setFillColor(colors.HexColor("#9FB0CD"))
    # این خط باید همان مبلغ بالا را توضیح بدهد.
    #
    # قبلاً «۱۱۰ ماه × ۱۹۰٬۰۰۰» بود — یعنی فقط نرخ پایه‌ی اولین پله.
    # از وقتی نرخ کاربر اضافه شد، آن ضرب دیگر با مبلغ نمی‌خواند:
    # فاکتور بالایش ۲۵٬۳۰۰٬۰۰۰ می‌نوشت و زیرش ضربی که ۲۰٬۹۰۰٬۰۰۰
    # می‌شد. فاکتوری که خودش را نقض کند، هیچ عددش قابل اعتماد نیست.
    dev_total = sum(l.get("deviceAmount") or 0 for l in lines)
    base_total = t["due"] - dev_total
    if _paid:
        # وقتی پرداختی هست، مهم‌ترین چیزی که باید زیر عدد بیاید همین
        # است: کل چقدر بود و چقدرش داده شده.
        note = (_fa("کل") + f" {money(t['due'])} − "
                + _fa("پرداخت‌شده") + f" {money(_paid)}")
    elif dev_total:
        note = (_fa("پایه") + f" {money(base_total)} + "
                + _fa("کاربر اضافه") + f" {money(dev_total)}")
    else:
        note = f"{t['months']} " + _fa("ماه") + _fa(" اشتراک")
    c.drawRightString(W - MR - 3 * mm, y - 17 * mm, note)

    cards = [
        (_fa("تعداد کانفیگ"), str(t["configs"]),
         _fa(f"{t['active']} فعال · {t['inactive']} غیرفعال")),
        (_fa("مجموع ماه"), str(t["months"]),
         _fa("در این بازه" if since_j else "دوره اول + تمدیدها")),
        (_fa("تعداد تمدید"), str(t["renewals"]),
         _fa("نرخ تمدید") + f" {t['renewalRate']}٪"),
        (_fa("ترافیک مصرفی"), f"{t['usedGB']:,.0f} GB",
         _fa("از") + f" {t['quotaGB']:,} GB ({t['usagePct']}٪)"),
    ]
    x = W - MR - hero_w - gap
    for label, val, sub in cards:
        x -= small_w
        c.setFillColor(CARD)
        c.setStrokeColor(colors.HexColor("#D6DCE8"))
        c.setLineWidth(0.5)
        c.roundRect(x, y - box_h, small_w, box_h, 2 * mm, fill=1, stroke=1)
        c.setFont(F, 7)
        c.setFillColor(MUTE)
        c.drawRightString(x + small_w - 2.5 * mm, y - 5.5 * mm, label)
        c.setFont(FB, 12)
        c.setFillColor(NAVY)
        c.drawRightString(x + small_w - 2.5 * mm, y - 12 * mm, val)
        c.setFont(F, 6)
        c.setFillColor(MUTE)
        c.drawRightString(x + small_w - 2.5 * mm, y - 16.5 * mm, sub)
        x -= gap

    y -= box_h + 7 * mm

    # ─────────── جدول ───────────
    cols = [
        ("ردیف", 11 * mm, "c"),
        ("نام کاربر", 52 * mm, "r"),
        ("تاریخ ایجاد", 25 * mm, "c"),
        ("تاریخ انقضا", 25 * mm, "c"),
        ("مدت (روز)", 19 * mm, "c"),
        ("ماه", 12 * mm, "c"),
        ("تمدید", 15 * mm, "c"),
        ("حجم (GB)", 20 * mm, "c"),
        ("مصرفی (GB)", 22 * mm, "c"),
        ("درصد", 15 * mm, "c"),
        ("دستگاه", 16 * mm, "c"),
        ("مبلغ (تومان)", 29 * mm, "c"),
    ]
    tw = sum(w for _, w, _ in cols)
    x0 = W - MR - tw
    ROW = 7.9 * mm

    def draw_thead(yy):
        c.setFillColor(NAVY)
        c.rect(x0, yy - 2 * mm, tw, 8 * mm, fill=1, stroke=0)
        c.setFont(FB, 8)
        c.setFillColor(colors.white)
        x = x0 + tw
        for label, w, _a in cols:
            x -= w
            c.drawCentredString(x + w / 2, yy + 0.6 * mm, _fa(label))
        return yy - 8 * mm

    # سربرگ گروه
    c.setFillColor(HEAD)
    c.rect(x0, y - 1.5 * mm, tw, 6.5 * mm, fill=1, stroke=0)
    c.setStrokeColor(NAVY)
    c.setLineWidth(1)
    c.line(x0, y + 5 * mm, x0 + tw, y + 5 * mm)
    c.setFont(F, 8)
    c.setFillColor(NAVY)
    c.drawRightString(x0 + tw - 2.5 * mm, y + 0.6 * mm,
                      _fa("گروه") + f"  {inv['label']}  ·  {t['configs']} " +
                      _fa("کانفیگ") + f"  ·  {t['months']} " + _fa("ماه") +
                      f"  ·  {t['renewals']} " + _fa("تمدید") +
                      f"  ·  {money(t['due'])} " + _fa("تومان"))
    y -= 6.5 * mm
    y = draw_thead(y)

    # ظرفیت هر صفحه.
    #
    # صفحه‌ی اول کمتر جا دارد چون کادرهای خلاصه بالایش هستند. و
    # صفحه‌ای که جمع‌ها رویش می‌آیند، به اندازه‌ی سه ردیف فضای
    # اضافه لازم دارد. بدون این حساب، یا ته صفحه خالی می‌ماند یا
    # جمع‌ها به صفحه‌ی بعد می‌افتند.
    # فوتر روی ۷ میلی‌متری است و حدود ۳ میلی‌متر ارتفاع دارد. ردیفی
    # که پایه‌اش زیر این خط بیفتد، کفش روی فوتر می‌نشیند.
    BOTTOM = 11.5 * mm
    TOTALS_H = 20 * mm          # جمع گروه + جمع کل


    idx = 0
    for ln in lines:
        if y < BOTTOM:
            end_page()
            y = header()
            y = draw_thead(y)

        idx += 1
        if idx % 2 == 0:
            c.setFillColor(SOFT)
            c.rect(x0, y - 1.2 * mm, tw, ROW, fill=1, stroke=0)

        vals = [
            str(idx),
            ln["email"][:30],
            ln.get("createdJalali") or DASH,
            ln.get("expiryJalali") or DASH,
            str(ln["days"]) if ln["days"] else DASH,
            str(ln["months"]),
            str(ln["renewals"]) if ln["renewals"] else DASH,
            ln["gbLabel"],
            f"{ln['usedGB']}",
            DASH if ln.get("usagePct") is None else f"{ln['usagePct']}٪",
            ("∞" if not ln["limitIp"]
             else (str(ln["limitIp"]) + "+" + money(ln["perDevice"])
                   if ln.get("perDevice") and ln.get("extraDevices")
                   else str(ln["limitIp"]))),
            money(ln["amount"]),
        ]

        x = x0 + tw
        for i, ((label, w, align), v) in enumerate(zip(cols, vals)):
            x -= w
            # نشانه‌ی تمدید: قرصِ کوچک دور عدد.
            #
            # قبلاً کل سلول رنگ می‌شد — به بلندای ROW و به عرض ستون.
            # ردیف‌های پشت‌سرهم که تمدید داشتند به هم می‌چسبیدند و یک
            # نوار آبیِ یکپارچه می‌ساختند که از سرستون شروع می‌شد؛
            # نه عددها خوانده می‌شدند نه معلوم بود مال کدام ردیف است.
            if label == "تمدید" and ln["renewals"]:
                pw, ph = 7 * mm, 4.6 * mm
                c.setFillColor(REN)
                c.roundRect(x + (w - pw) / 2, y - 0.9 * mm, pw, ph,
                            1.6 * mm, fill=1, stroke=0)
                c.setFillColor(RENT)
                c.setFont(FB, 8.2)
            elif label in ("ماه", "مبلغ (تومان)"):
                c.setFillColor(INK)
                c.setFont(FB, 8.2)
            elif label == "نام کاربر":
                c.setFillColor(INK if ln["active"] else MUTE)
                c.setFont(F, 8.2)
            else:
                c.setFillColor(GREY)
                c.setFont(F, 8.2)

            txt = _fa(v) if any("\u0600" <= ch <= "\u06FF" for ch in v) else v
            if align == "r":
                c.drawRightString(x + w - 2 * mm, y + 0.5 * mm, txt)
            else:
                c.drawCentredString(x + w / 2, y + 0.5 * mm, txt)

        # خط جداکننده
        c.setStrokeColor(LINE)
        c.setLineWidth(0.3)
        c.line(x0, y - 1.2 * mm, x0 + tw, y - 1.2 * mm)
        y -= ROW

    # جمع گروه — اگر جا نیست، صفحه‌ی جدید
    if y < BOTTOM + TOTALS_H:
        end_page()
        y = header()
        y = draw_thead(y)

    y -= 1 * mm
    c.setFillColor(colors.HexColor("#EEF1F7"))
    c.rect(x0, y - 1.2 * mm, tw, 6.5 * mm, fill=1, stroke=0)
    c.setFont(FB, 7.2)
    c.setFillColor(INK)
    c.drawRightString(x0 + tw - 2.5 * mm, y + 0.8 * mm,
                      _fa("جمع گروه") + f" {inv['label']}")
    # ستون‌های عددی جمع
    xs = x0 + tw
    for label, w, _a in cols:
        xs -= w
        v = None
        if label == "ماه":
            v = str(t["months"])
        elif label == "تمدید":
            v = str(t["renewals"])
        elif label == "حجم (GB)":
            v = f"{t['quotaGB']:,}"
        elif label == "مصرفی (GB)":
            v = f"{t['usedGB']:,}"
        elif label == "مبلغ (تومان)":
            v = money(t["due"])
        if v:
            c.drawCentredString(xs + w / 2, y + 0.8 * mm, v)
    y -= 8 * mm

    # جمع کل
    c.setFillColor(NAVY)
    c.rect(x0, y - 1.5 * mm, tw, 7.5 * mm, fill=1, stroke=0)
    c.setFont(FB, 8.5)
    c.setFillColor(colors.white)
    c.drawRightString(x0 + tw - 2.5 * mm, y + 1 * mm,
                      _fa("جمع کل") + f" ({t['configs']} " + _fa("کانفیگ") + ")")
    xs = x0 + tw
    for label, w, _a in cols:
        xs -= w
        if label == "مبلغ (تومان)":
            c.drawCentredString(xs + w / 2, y + 1 * mm,
                                money(t["due"]) )
    y -= 12 * mm

    # ─────────── توضیحات ───────────
    #
    # اگر در همین صفحه جا هست، ادامه می‌دهیم. صفحه‌ی خالی فقط
    # برای چند خط توضیح، فاکتور را بی‌دقت نشان می‌دهد.
    review = inv.get("review") or []
    need = 42 * mm + (min(len(review), 18) * 4.5 * mm + 14 * mm if review else 0)

    if y - need < 18 * mm:
        end_page()
        y = header()
    else:
        y -= 6 * mm

    c.setStrokeColor(NAVY)
    c.setLineWidth(2)
    c.line(W - MR, y, W - MR, y - 30 * mm)

    c.setFont(FB, 9)
    c.setFillColor(NAVY)
    c.drawRightString(W - MR - 4 * mm, y - 4 * mm, _fa("روش محاسبه"))
    c.setFont(F, 7.8)
    y -= 10 * mm
    _how = [
        "پنل ۳x-ui تاریخچه‌ی تمدید نگه نمی‌دارد. تنها اثر تمدید این است که تاریخ انقضا",
        "جلو می‌رود در حالی که تاریخ ایجاد ثابت می‌ماند. بنابراین:",
        "مدت اشتراک = تاریخ انقضا منهای تاریخ ایجاد",
        "تعداد ماه = گِردشده‌ی مدت تقسیم بر ۳۰، حداقل ۱",
        "تعداد تمدید = تعداد ماه منهای یک",
        "مبلغ هر کانفیگ = تعداد ماه ضربدر نرخ حجم آن پلن",
    ]
    if since_j:
        # بدون این خط، واسطه فقط می‌بیند که عددها از فاکتور قبلی
        # کمترند و دلیلش را نمی‌داند.
        _how += [
            f"این فاکتور فقط از {since_j} به بعد را حساب کرده"
            f" ({inv.get('sinceWhy') or 'بازه انتخابی'}).",
        ]
        if t.get("before"):
            _how += [
                f"{t['before']} کانفیگ که تمام ماه‌هایشان پیش از این تاریخ بوده"
                f" ({t.get('beforeMonths', 0)} ماه) روی این فاکتور نیامده‌اند.",
            ]
    # این یکی به بازه ربطی ندارد و همیشه باید گفته شود.
    if t.get("unused"):
        _how += [
            f"{t['unused']} کانفیگ ساخته شده ولی هرگز به کار نیفتاده و"
            " حساب نشده است.",
        ]
    for m in _how:
        c.setFillColor(GREY)
        c.drawRightString(W - MR - 4 * mm, y, _fa(m))
        y -= 5 * mm

    y -= 3 * mm
    c.setFont(F, 7.5)
    for m in [
        "مصرف ترافیک از جدول client_traffics پنل خوانده شده و داده‌ی واقعی است.",
        "حجم ∞ یعنی پلن نامحدود · دستگاه ∞ یعنی بدون محدودیت اتصال همزمان.",
        f"پرداخت ثبت‌شده: {money(t['paid'])} تومان · مانده: {money(t['balance'])} تومان.",
    ]:
        c.setFillColor(MUTE)
        c.drawRightString(W - MR - 4 * mm, y, _fa(m))
        y -= 5 * mm

    # موارد بررسی
    if review:
        y -= 6 * mm
        box_h2 = min(len(review), 18) * 4.5 * mm + 12 * mm
        c.setFillColor(WARNBG)
        c.setStrokeColor(WARNBD)
        c.setLineWidth(0.6)
        c.roundRect(ML, y - box_h2, CW, box_h2, 2 * mm, fill=1, stroke=1)

        c.setFont(FB, 8.5)
        c.setFillColor(WARNT)
        c.drawRightString(W - MR - 4 * mm, y - 6 * mm,
                          _fa(f"موارد نیازمند بررسی دستی ({len(review)} مورد)"))
        yy = y - 12 * mm
        c.setFont(F, 7.2)
        for r in review[:18]:
            c.setFillColor(GREY)
            c.drawRightString(W - MR - 4 * mm, yy,
                              f"{r['email']} — " + _fa(r["status"]) + " · " +
                              _fa(r["reason"]) + " · " + _fa("دقت") + ": " +
                              _fa(r["accuracy"]))
            yy -= 4.5 * mm
        if len(review) > 18:
            c.setFillColor(MUTE)
            c.drawRightString(W - MR - 4 * mm, yy,
                              _fa(f"و {len(review) - 18} مورد دیگر"))

    # پاورقی
    c.setStrokeColor(colors.HexColor("#CCD3E0"))
    c.setLineWidth(0.5)
    c.line(ML, 13 * mm, W - MR, 13 * mm)
    c.setFont(F, 6.8)
    c.setFillColor(MUTE)
    c.drawRightString(W - MR, 9.5 * mm,
                      _fa("گزارش تولیدشده از دیتابیس پنل ۳x-ui") + "  ·  NEXORA  ·  @yanexoravpn")
    c.drawString(ML, 9.5 * mm, f"{inv_no}  ·  {jnow}")

    c.save()
    buf.seek(0)

    safe = "".join(ch for ch in group_key if ch.isalnum() or ch in "-_") or "invoice"
    return Response(
        content=buf.read(),
        media_type="application/pdf",
        headers={"Content-Disposition":
                 f'attachment; filename="nexora-{safe}-{stamp:%Y%m%d}.pdf"'})


@app.get("/api/admin/billing/period/{group_key}")
def billing_period(group_key: str, start: str = "", end: str = "",
                   full: int = 0,
                   x_admin_password: str = Header(...)):
    """
    صورتحساب یک دوره — نه کل بدهی تا امروز.

    این همان چیزی است که برای پرداخت دوره‌ای لازم است: در این
    هفته یا ماه، چند کانفیگ ساخته شده و چند تمدید انجام شده، و
    بابتش چقدر باید گرفت. هر کانفیگ فقط یک‌بار در دوره‌ای که
    ساخته شده حساب می‌شود، نه هر بار که گزارش گرفته می‌شود.
    """
    check_auth(x_admin_password)

    clients, _known, err = _read_xui_clients()
    if clients is None:
        return {"ready": False, "error": err}

    bcon = _billing_conn()
    try:
        _attach_total_usage(bcon, clients)
        row = bcon.execute("SELECT * FROM group_config WHERE group_key=?",
                           (group_key,)).fetchone()
        conf = dict(row) if row else {}
        try:
            rates = json.loads(conf.get("rates") or "[]")
        except (json.JSONDecodeError, TypeError):
            rates = []
        logged_rows = [dict(r) for r in bcon.execute(
            "SELECT email, months, created_at FROM renewals")]
        logged = {r["email"]: r["m"] for r in bcon.execute(
            "SELECT email, COALESCE(SUM(months),0) m FROM renewals GROUP BY email")}
        try:
            seen = {r["email"]: r["first_seen"] for r in bcon.execute(
                "SELECT email, first_seen FROM client_seen")}
        except Exception:
            seen = {}
        pays = [dict(r) for r in bcon.execute(
            "SELECT * FROM payments WHERE group_key=? ORDER BY paid_at", (group_key,))]
    finally:
        bcon.close()

    settled = (conf.get("settled_until") or "").strip()[:10]

    from datetime import date, timedelta as _td
    if full:
        # از ابتدا تا امروز.
        #
        # دوره‌ی پیش‌فرض سی روز است، و برای واسطه‌ای که دو سال با شما
        # کار کرده یعنی صورتحسابی که فقط کانفیگ‌های همین ماه را نشان
        # می‌دهد — انگار حسابداری از قبل اصلاً وجود نداشته. این حالت
        # از تاریخ ساخت قدیمی‌ترین کانفیگ همان گروه شروع می‌کند.
        firsts = [ (_to_jalali(c.get("createdAt"))[1] or "")
                   for c in clients if c["group"] == group_key ]
        firsts = sorted(x for x in firsts if x)
        p_start = date.fromisoformat(firsts[0]) if firsts else date(2000, 1, 1)
        # تسویه‌شده‌ها بیرون می‌مانند، پس شروع را جلو می‌بریم
        if settled:
            try:
                p_start = max(p_start, date.fromisoformat(settled))
            except ValueError:
                pass
        p_end = date.today() + _td(days=1)
    elif start and end:
        try:
            p_start = date.fromisoformat(start[:10])
            p_end = date.fromisoformat(end[:10])
        except ValueError:
            raise HTTPException(status_code=400, detail="تاریخ نامعتبر")
    else:
        p_start, p_end = _period_bounds(conf)

    per_gb = _price_per_gb(conf)

    def in_period(d):
        return d and p_start.isoformat() <= d < p_end.isoformat()

    new_configs, renewals, skipped = [], [], 0
    unused, unused_why = 0, {}

    for cl in clients:
        if cl["group"] != group_key:
            continue

        # چهارمین صفحه‌ای که این قاعده را نداشت.
        #
        # کانفیگی که ساخته شده و هرگز روشن نشده، روی این صفحه یک
        # «فروش تازه» در همان هفته حساب می‌شد — با مبلغ. داشبورد و
        # صورتحساب کنارش می‌گذارند، این نه.
        bill_it, why = _billable_config(cl)
        if not bill_it:
            unused += 1
            unused_why[why] = unused_why.get(why, 0) + 1
            continue

        gb = _gb_of(cl["totalGB"])
        _amt1, price, _pd, _ex = _line_amount(gb, rates, 1, cl.get("limitIp"))
        price_why = None
        if price is None:
            _, price_why = _price_with_reason(gb, rates)
        # قیمتِ یک ماه، با کاربرهای اضافه
        price = _amt1 if price is not None else None
        _cj, created_g = _to_jalali(cl.get("createdAt"))
        created_j, _ = _to_jalali(cl.get("createdAt"))

        # کانفیگ‌های تسویه‌شده اصلاً وارد محاسبه نمی‌شوند
        if settled and created_g and created_g < settled:
            skipped += 1
        elif in_period(created_g):
            new_configs.append({
                "email": cl["email"], "gb": gb,
                "gbLabel": "نامحدود" if gb == 0 else f"{gb} GB",
                "date": created_g, "dateJalali": created_j,
                "price": price, "priceWhy": price_why,
                "amount": price or 0,
                "usedGB": round(cl["usedTotal"] / (1024 ** 3), 1),
            })

        # تعداد از همان جایی می‌آید که صورتحساب کلی می‌شمارد.
        #
        # وقتی این‌جا مستقل شمرده می‌شد، کانفیگی با سابقه‌ی طولانی و
        # یک تمدیدِ ثبت‌شده در صفحه‌ی دوره یک تمدید داشت و در
        # صورتحساب بیست‌وچند ماه — دو عدد از یک واقعیت.
        _months, _kind, _drift = _months_for(
            cl, logged, since=conf.get("period_start"),
            first_seen=seen.get(cl["email"]))
        for rdate, kind in _renewal_dates(
                cl, logged_rows, _months, since=conf.get("period_start"),
                first_seen=seen.get(cl["email"])):
            if settled and rdate < settled:
                continue
            if in_period(rdate):
                rj, _ = _to_jalali(_date_ms(date.fromisoformat(rdate)))
                renewals.append({
                    "email": cl["email"], "gb": gb,
                    "gbLabel": "نامحدود" if gb == 0 else f"{gb} GB",
                    "date": rdate, "dateJalali": rj, "kind": kind,
                    "price": price, "priceWhy": price_why,
                    "amount": price or 0,
                })

    new_total = sum(x["amount"] for x in new_configs)
    ren_total = sum(x["amount"] for x in renewals)

    # نرخ حجمی: بر اساس مصرف کل گروه در دوره
    gb_total = 0
    if per_gb:
        used = sum(c["usedTotal"] for c in clients if c["group"] == group_key)
        gb_total = round(used / (1024 ** 3) * per_gb)

    due = gb_total if per_gb else (new_total + ren_total)

    paid_in_period = sum(p["amount"] for p in pays
                         if in_period((p.get("paid_at") or "")[:10]))

    return {
        "ready": True,
        "group": group_key,
        "label": conf.get("label") or group_key,
        "period": {
            "start": p_start.isoformat(),
            "end": p_end.isoformat(),
            "startJalali": _to_jalali(_date_ms(p_start))[0],
            "endJalali": _to_jalali(_date_ms(p_end))[0],
            "days": (p_end - p_start).days,
            "full": bool(full),
        },
        "settledUntil": settled or None,
        "skippedSettled": skipped,
        "perGb": per_gb,
        "newConfigs": sorted(new_configs, key=lambda x: x["date"] or ""),
        "renewals": sorted(renewals, key=lambda x: x["date"] or ""),
        "totals": {
            "newCount": len(new_configs),
            "newAmount": new_total,
            "renewalCount": len(renewals),
            "renewalAmount": ren_total,
            "gbAmount": gb_total,
            "due": due,
            "paid": paid_in_period,
            "balance": due - paid_in_period,
            "unused": unused,
            "unusedWhy": unused_why,
            "estimated": sum(1 for r in renewals if r["kind"] == "تخمینی"),
            "unpriced": sum(1 for x in new_configs + renewals if x["price"] is None),
            # همان دلیل‌ها، جمع‌شده — تا صفحه بتواند یک جمله‌ی روشن
            # بگوید به‌جای یک عدد
            "unpricedWhy": sorted({x["priceWhy"] for x in new_configs + renewals
                                   if x["price"] is None and x.get("priceWhy")}),
        },
        "payments": [p for p in pays if in_period((p.get("paid_at") or "")[:10])],
    }


@app.get("/api/admin/billing/clients")
def billing_clients(
    q: str = "",
    group: str = "",
    status: str = "",
    renewed: str = "",
    created_from: str = "",
    created_to: str = "",
    age: str = "",
    priced: str = "",
    sort: str = "created",
    order: str = "desc",
    limit: int = 500,
    offset: int = 0,
    x_admin_password: str = Header(...),
):
    """
    فهرست کامل همه‌ی کاربران — از هر گروه، و آن‌هایی که گروه ندارند.

    این نمای مرجع است: هر سوالی درباره‌ی یک کاربر پیش بیاید،
    جوابش اینجاست. چه کسی تمدید کرده، چه کسی نکرده، چند روز مانده،
    چقدر مصرف کرده و چقدر بدهکار است.
    """
    check_auth(x_admin_password)

    clients, known_groups, err = _read_xui_clients()
    if clients is None:
        return {"ready": False, "error": err, "clients": [], "groups": []}

    bcon = _billing_conn()
    try:
        cfg = {r["group_key"]: dict(r) for r in bcon.execute("SELECT * FROM group_config")}
        logged = {r["email"]: r["m"] for r in bcon.execute(
            "SELECT email, COALESCE(SUM(months),0) m FROM renewals GROUP BY email")}
        rows_by = _rows_by_email([dict(r) for r in bcon.execute(
            "SELECT email, months, created_at FROM renewals")])
        # این صفحه هم باید ثبت کند، نه فقط نمای کلی.
        #
        # تا امروز فقط `billing/overview` صدایش می‌زد. ولی مصرفِ
        # جمع‌شده از *مشاهده* ساخته می‌شود: اگر بین دو نگاه ریست
        # بیفتد، عددِ قبلی دیده نشده و برای همیشه می‌رود. «همه
        # کاربران» جایی است که مالک به مصرف نگاه می‌کند، پس همین‌جا
        # هم باید چشم باز باشد.
        #
        # دوباره‌اجرا بی‌خطر است: هم تشخیص تمدید و هم شمارش مصرف با
        # مقایسه‌ی مقدارِ قبلی کار می‌کنند، نه با افزودنِ کور.
        try:
            seen = _record_seen(bcon, clients)
        except Exception:
            log.debug("ثبت دیدن در فهرست مرجع ناموفق", exc_info=True)
            seen = {}
        # مصرفِ دوره‌های ریست‌شده — از همان هسته‌ای که بقیه‌ی
        # صفحه‌های حسابداری هم از آن می‌گذرند. نسخه‌ی قبل این‌جا
        # دیکشنریِ خودش را می‌ساخت و بقیه هیچ، که شد «یک قاعده، دو
        # جا، اصلاح در یکی» — همان باگی که این مخزن اسم دارد رویش.
        _attach_total_usage(bcon, clients)
        since_of = {k: _bill_since(v)[0] for k, v in cfg.items()}
    finally:
        bcon.close()

    now_ms = int(datetime.now().timestamp() * 1000)
    out = []

    for cl in clients:
        g = cl["group"]
        conf = cfg.get(g, {})
        try:
            rates = json.loads(conf.get("rates") or "[]")
        except (json.JSONDecodeError, TypeError):
            rates = []
        if not isinstance(rates, list):
            rates = []

        # این فهرست «نمای مرجع» است و مبلغش باید همان چیزی باشد که
        # روی فاکتور می‌آید. سه جا با صورتحساب فرق داشت:
        #
        #   ۱. _months_for بدون since و first_seen صدا زده می‌شد، پس
        #      کانفیگِ بدون تاریخ ساخت این‌جا «یک ماه» بود و آن‌جا
        #      چیز دیگری
        #   ۲. بازه‌ی «تسویه‌شده تا» اصلاً دیده نمی‌شد
        #   ۳. مبلغ months × price بود، یعنی نرخ کاربر اضافه را کامل
        #      نادیده می‌گرفت — کانفیگ چهارکاربره روی این فهرست
        #      ۲۰۰٬۰۰۰ بود و روی فاکتور ۴۴۰٬۰۰۰
        billed, months, ren_in, _new, kind, drift = _period_share(
            cl, logged, rows_by.get(cl["email"], []), since_of.get(g),
            group_start=conf.get("period_start"),
            first_seen=seen.get(cl["email"]))
        gb = _gb_of(cl["totalGB"])

        # نرخ و مبلغ دو چیز جدا هستند و باید جدا بمانند.
        #
        # `price` یعنی «نرخی که به این حجم می‌خورد» و فیلترِ «بدون
        # نرخ» روی همین کار می‌کند — مدیر با آن دنبال گروه‌هایی
        # می‌گردد که باید برایشان نرخ تعریف کند. اگر price را برای
        # کانفیگِ تسویه‌شده یا بی‌استفاده هم None کنیم، آن فیلتر پر
        # می‌شود از ردیف‌هایی که نرخشان هیچ مشکلی ندارد.
        #
        # `amount` یعنی «چقدر بابتش گرفته می‌شود» — که می‌تواند صفر
        # باشد در حالی که نرخ کاملاً تعریف شده است.
        bill_it, bill_why = _billable_config(cl)
        price_why = None
        if conf.get("billable"):
            full, price, per_dev, extra_dev = _line_amount(
                gb, rates, max(0, billed), cl.get("limitIp"))
            if price is None:
                _p, price_why = _price_with_reason(gb, rates)
        else:
            full, price, per_dev, extra_dev = 0, None, 0, 0

        amount, amount_why = 0, None
        if not conf.get("billable"):
            amount_why = "محاسبه برای این گروه خاموش است"
        elif not bill_it:
            amount_why = bill_why
        elif billed <= 0:
            amount_why = "پیش از تاریخ تسویه"
        elif price is None:
            amount_why = price_why
        else:
            amount = full

        created_j, created_g = _to_jalali(cl.get("createdAt"))
        expiry_j, expiry_g = _to_jalali(cl.get("expiry"))
        updated_j, _ = _to_jalali(cl.get("updatedAt"))
        days = _duration_days(cl.get("createdAt"), cl.get("expiry"))

        # روزهای باقی‌مانده — عدد منفی یعنی چند روز از انقضا گذشته
        remaining = None
        exp = cl.get("expiry") or 0
        if exp > 0:
            remaining = round((exp - now_ms) / 86400000.0, 1)

        used = cl["used"]
        # `used` مصرفِ دوره‌ی جاری است و `usedTotal` جمعِ همه‌ی
        # دوره‌ها. درصد روی دوره‌ی جاری می‌ماند — «۱۹۰٪ از سهمیه»
        # عدد بی‌معنایی است — ولی جمع باید دیده شود، چون همان است
        # که مشتری واقعاً مصرف کرده.
        used_total = cl["usedTotal"]
        reset_before = used_total - used
        pct = _usage_percent(used, cl["totalGB"])

        if not exp:
            st = "بدون انقضا"
        elif exp < 0:
            st = "شروع‌نشده"
        elif not cl["enable"]:
            st = "غیرفعال"
        elif remaining is not None and remaining < 0:
            st = "منقضی"
        elif remaining is not None and remaining <= 3:
            st = "رو به انقضا"
        else:
            st = "فعال"

        renewals = ren_in

        out.append({
            "email": cl["email"],
            "group": g,
            "groupLabel": conf.get("label") or g,
            "billable": bool(conf.get("billable", 0)),
            "gb": gb,
            "gbLabel": "نامحدود" if gb == 0 else f"{gb} GB",
            "usedBytes": used,
            "usedGB": round(used / (1024 ** 3), 2),
            "usedTotalGB": round(used_total / (1024 ** 3), 2),
            # چقدر از مصرف مالِ دوره‌های ریست‌شده است — رابط فقط
            # وقتی نشانش می‌دهد که صفر نباشد
            "usedBeforeGB": round(reset_before / (1024 ** 3), 2),
            "usagePct": pct,
            "limitIp": cl.get("limitIp") or 0,
            "subId": cl.get("subId") or "",
            "tgId": cl.get("tgId") or 0,
            "comment": cl.get("comment") or "",
            "resetCount": cl.get("resetCount") or 0,
            "createdJalali": created_j,
            "createdGregorian": created_g,
            "expiryJalali": expiry_j,
            "expiryGregorian": expiry_g,
            "updatedJalali": updated_j,
            "days": days,
            "remainingDays": remaining,
            "months": billed,
            "totalMonths": months,
            "renewals": renewals,
            "totalRenewals": months - 1,
            "renewalKind": kind,
            "drift": drift,
            "loggedRenewals": logged.get(cl["email"], 0),
            "price": price,
            "perDevice": per_dev,
            "extraDevices": extra_dev,
            "deviceAmount": per_dev * extra_dev * billed,
            "amount": amount,
            # چرا صفر است — وگرنه ردیفِ صفر شبیه خرابی به نظر می‌رسد
            "amountWhy": amount_why,
            "enable": cl["enable"],
            "status": st,
        })

    # ── فیلترها ──
    if q:
        needle = q.strip().lower()
        out = [x for x in out
               if needle in x["email"].lower()
               or needle in x["group"].lower()
               or needle in (x["comment"] or "").lower()]

    if group:
        out = [x for x in out if x["group"] == group]

    if status:
        out = [x for x in out if x["status"] == status]

    if renewed == "yes":
        # سوالِ این فیلتر «این مشتری تا حالا تمدید کرده؟» است، نه
        # «در این دوره تمدید کرده؟». وقتی مبلغ دوره‌ای شد، اگر این هم
        # دوره‌ای می‌شد، مشتریِ دوساله روی گروهی با تاریخ تسویه‌ی
        # نزدیک «هرگز تمدید نکرده» نشان داده می‌شد.
        out = [x for x in out if x["totalRenewals"] > 0]
    elif renewed == "no":
        out = [x for x in out if x["totalRenewals"] == 0]

    # بازه‌ی تاریخ ایجاد — برای اینکه بدانید در یک بازه چه کسانی
    # اضافه شده‌اند و بابتشان چقدر باید گرفت
    if created_from:
        out = [x for x in out
               if (x.get("createdGregorian") or "") >= created_from[:10]]
    if created_to:
        out = [x for x in out
               if (x.get("createdGregorian") or "") <= created_to[:10]]

    # تازه یا قدیمی — مرز ۳۰ روز، چون دوره‌ی معمول همین است
    if age in ("new", "old"):
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        if age == "new":
            out = [x for x in out
                   if (x.get("createdGregorian") or "") >= cutoff]
        else:
            out = [x for x in out
                   if (x.get("createdGregorian") or "9999") < cutoff]

    # بدون نرخ — حجم‌هایی که در نرخ‌های گروه تعریف نشده‌اند.
    # اینها پول از دست رفته‌اند چون در صورتحساب صفر می‌آیند.
    if priced == "no":
        out = [x for x in out if x["billable"] and x["price"] is None]
    elif priced == "yes":
        out = [x for x in out if x["price"] is not None]

    # ── مرتب‌سازی ──
    keys = {
        "email": lambda x: x["email"].lower(),
        "group": lambda x: (x["group"].lower(), x["email"].lower()),
        "created": lambda x: x.get("createdGregorian") or "",
        "expiry": lambda x: x.get("expiryGregorian") or "",
        "remaining": lambda x: (x["remainingDays"] is None, x["remainingDays"] or 0),
        "used": lambda x: x["usedBytes"],
        "usage": lambda x: (x["usagePct"] is None, x["usagePct"] or 0),
        "renewals": lambda x: x["renewals"],
        "months": lambda x: x["months"],
        "amount": lambda x: x["amount"],
    }
    out.sort(key=keys.get(sort, keys["created"]), reverse=(order != "asc"))

    total = len(out)

    # ── آمار کلی، قبل از صفحه‌بندی ──
    stats = {
        "total": total,
        # نرخ نگه‌داشت هم از کل سابقه حساب می‌شود، نه از دوره
        "renewed": sum(1 for x in out if x["totalRenewals"] > 0),
        "notRenewed": sum(1 for x in out if x["totalRenewals"] == 0),
        "totalRenewals": sum(x["totalRenewals"] for x in out),
        # و این یکی سهم همین دوره است — همان که روی فاکتور می‌آید
        "periodRenewals": sum(x["renewals"] for x in out),
        "active": sum(1 for x in out if x["status"] == "فعال"),
        "expiringSoon": sum(1 for x in out if x["status"] == "رو به انقضا"),
        "expired": sum(1 for x in out if x["status"] == "منقضی"),
        "disabled": sum(1 for x in out if x["status"] == "غیرفعال"),
        "noGroup": sum(1 for x in out if x["group"] == "بدون گروه"),
        "usedGB": round(sum(x["usedBytes"] for x in out) / (1024 ** 3), 1),
        "amount": sum(x["amount"] for x in out),
    }
    stats["renewalRate"] = (round(stats["renewed"] * 100.0 / total, 1)
                            if total else 0)

    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    stats["newLast30"] = sum(1 for x in out
                             if (x.get("createdGregorian") or "") >= cutoff)
    stats["olderThan30"] = total - stats["newLast30"]
    stats["unpriced"] = sum(1 for x in out
                            if x["billable"] and x["price"] is None)

    # همه‌ی گروه‌ها برای فیلتر، حتی خالی‌ها
    all_groups = sorted({c["group"] for c in clients} | set(known_groups or []))

    return {
        "ready": True,
        "clients": out[offset:offset + max(1, min(limit, 2000))],
        "total": total,
        "offset": offset,
        "limit": limit,
        "stats": stats,
        "groups": all_groups,
        "statuses": ["فعال", "رو به انقضا", "منقضی", "غیرفعال",
                     "بدون انقضا", "شروع‌نشده"],
    }


@app.get("/api/admin/billing/clients/export")
def billing_clients_export(
    q: str = "",
    group: str = "",
    status: str = "",
    renewed: str = "",
    created_from: str = "",
    created_to: str = "",
    age: str = "",
    priced: str = "",
    sort: str = "created",
    order: str = "desc",
    x_admin_password: str = Header(...),
):
    """
    خروجی CSV — با همان فیلترهایی که در صفحه اعمال کرده‌اید.

    اگر خروجی همیشه کامل بود، بعد از فیلتر کردن باید دوباره در
    اکسل همان کار را تکرار می‌کردید.
    """
    check_auth(x_admin_password)

    data = billing_clients(
        q=q, group=group, status=status, renewed=renewed,
        created_from=created_from, created_to=created_to,
        age=age, priced=priced, sort=sort, order=order,
        limit=100000, x_admin_password=x_admin_password)
    if not data.get("ready"):
        raise HTTPException(status_code=400, detail=data.get("error") or "خواندن ناموفق")

    import io, csv
    buf = io.StringIO()
    buf.write("\ufeff")   # BOM تا اکسل فارسی را درست بخواند

    w = csv.writer(buf)
    w.writerow(["ایمیل", "گروه", "وضعیت", "حجم", "مصرف (GB)", "درصد مصرف",
                "تاریخ ایجاد", "تاریخ انقضا", "روز مانده", "مدت (روز)",
                "ماه", "تمدید", "نوع تشخیص", "دستگاه", "نرخ",
                "کاربر اضافه", "مبلغ", "چرا صفر", "توضیح"])
    for x in data["clients"]:
        w.writerow([
            x["email"], x["group"], x["status"], x["gbLabel"],
            x["usedGB"], "" if x["usagePct"] is None else x["usagePct"],
            x["createdJalali"] or "", x["expiryJalali"] or "",
            "" if x["remainingDays"] is None else x["remainingDays"],
            x["days"] or "", x["months"], x["renewals"], x["renewalKind"],
            x["limitIp"] or "نامحدود",
            x["price"] or "", x.get("extraDevices") or "",
            x["amount"] or "",
            # مبلغ صفر بدون دلیل، در یک فایل که آفلاین خوانده می‌شود،
            # هیچ راهی برای فهمیدن باقی نمی‌گذارد
            x.get("amountWhy") or "", x["comment"],
        ])

    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition":
                 f'attachment; filename="nexora-clients-{datetime.now():%Y%m%d}.csv"'})


@app.get("/api/admin/billing/diagnose")
def billing_diagnose(x_admin_password: str = Header(...)):
    """
    تشخیص کامل مشکل اتصال — هر مرحله جدا گزارش می‌شود.

    وقتی حسابداری کار نمی‌کند، این می‌گوید دقیقاً کدام مرحله شکست
    خورده: مسیر، مجوز، باز کردن، ساختار، یا محاسبه.
    """
    check_auth(x_admin_password)
    steps = []

    def step(title, ok, detail="", hint=""):
        steps.append({"title": title, "ok": ok, "detail": detail, "hint": hint})
        return ok

    manual = env = ""
    try:
        cfg = load_config()
        manual = ((cfg.get("advanced") or {}).get("xuiDbPath") or "").strip()
    except Exception:
        pass
    env = os.getenv("XUI_DB_PATH", "").strip()
    path = _xui_db_path()

    source = ("تنظیمات پنل" if manual and str(path) == manual
              else "متغیر سرویس" if env and str(path) == env
              else "جستجوی خودکار")
    step("مسیر انتخابی", True, f"{path}  (از {source})")

    # ── بیش از یک x-ui.db روی سرور ──
    #
    # این خرابیِ بی‌صداست و از بیرون شبیهِ «حسابداری آپدیت نمی‌شود»
    # دیده می‌شود: پنل عددِ یک فایلِ مرده را می‌خواند که هیچ‌وقت
    # عوض نمی‌شود، و مالک می‌بیند مصرف با پنلِ خودِ x-ui نمی‌خواند.
    #
    # نصبِ دوباره، مهاجرت از مسیری به مسیرِ دیگر، یا بک‌آپی که کنارش
    # مانده — هر سه این حالت را می‌سازند.
    cands = _xui_db_candidates()
    if len(cands) > 1:
        import time as _t
        now = _t.time()
        lines = []
        for c in cands:
            age = now - c["mtime"]
            if age < 120:
                when = "همین حالا"
            elif age < 3600:
                when = f"{int(age // 60)} دقیقه پیش"
            elif age < 86400:
                when = f"{int(age // 3600)} ساعت پیش"
            else:
                when = f"{int(age // 86400)} روز پیش"
            mark = " ← انتخاب‌شده" if c["path"] == str(path) else ""
            lines.append(f"{c['path']} (آخرین نوشتن: {when}){mark}")
        # تازه‌ترین فایل همان است که x-ui رویش می‌نویسد
        live_is_chosen = cands[0]["path"] == str(path)
        step("چند فایل x-ui پیدا شد", live_is_chosen,
             " · ".join(lines),
             "" if live_is_chosen else
             "فایلِ انتخاب‌شده تازه‌ترین نیست. مسیر درست را در «تنظیمات و "
             "بک‌آپ» دستی بگذارید، یا فایل‌های اضافه را کنار ببرید.")

    # ── فایلِ انتخاب‌شده اصلاً تازه است؟ ──
    #
    # x-ui هر چند ثانیه ترافیک را می‌نویسد. فایلی که ساعت‌هاست
    # دست‌نخورده مانده یعنی x-ui رویش نمی‌نویسد — چه بک‌آپ باشد، چه
    # نصبی که دیگر اجرا نمی‌شود.
    try:
        import time as _t2
        age2 = _t2.time() - path.stat().st_mtime
        fresh = age2 < 6 * 3600
        step("فایل تازه نوشته شده", fresh,
             (f"{int(age2 // 60)} دقیقه پیش" if age2 < 3600
              else f"{int(age2 // 3600)} ساعت پیش"),
             "" if fresh else
             "x-ui روی این فایل نمی‌نویسد. احتمالاً فایلِ درست جای دیگری "
             "است — روی سرور بزنید: nexora usage-why")
    except OSError:
        pass

    if manual and not Path(manual).exists():
        step("مسیر دستی", False, f"{manual} وجود ندارد",
             "در بخش تنظیمات و بک‌آپ اصلاحش کنید یا خالی بگذارید")

    if not step("فایل موجود است", path.exists(), str(path),
                "" if path.exists() else "روی سرور اجرا کنید: nexora fix-xui"):
        return {"ok": False, "steps": steps}

    perms, blocked = [], []
    for suffix in ("", "-wal", "-shm"):
        f = path.with_name(path.name + suffix) if suffix else path
        if not f.exists():
            continue
        try:
            mode = oct(f.stat().st_mode)[-3:]
        except Exception:
            mode = "?"
        readable = os.access(f, os.R_OK)
        perms.append(f"{f.name}: {mode}{'' if readable else ' (خوانا نیست)'}")
        if not readable:
            blocked.append(f.name)

    step("مجوزها", not blocked, " · ".join(perms),
         f"chmod +r {path.parent}/{path.name}*" if blocked else "")

    try:
        import pwd
        me = pwd.getpwuid(os.geteuid()).pw_name
    except Exception:
        me = str(os.geteuid())
    step("کاربر پنل", True, me)

    con, err = _xui_conn()
    if not step("باز کردن دیتابیس", con is not None, err or "موفق",
                "" if con else "پیام بالا را دنبال کنید"):
        return {"ok": False, "steps": steps}

    try:
        tables = [r["name"] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        has_new = "clients" in tables
        has_old = "inbounds" in tables
        step("ساختار دیتابیس", has_new or has_old,
             f"{len(tables)} جدول — " +
             ("نسخه ۳.۵ به بالا" if has_new else "نسخه کلاسیک" if has_old else "ناشناخته"))

        if has_new:
            n = con.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
            step("خواندن کلاینت‌ها", True, f"{n} کانفیگ")
            try:
                g = [r[0] for r in con.execute("SELECT name FROM client_groups")]
                step("خواندن گروه‌ها", True,
                     f"{len(g)} گروه: " + "، ".join(g[:8]) + ("..." if len(g) > 8 else ""))
            except Exception as e:
                step("خواندن گروه‌ها", False, str(e)[:90])
    except Exception as e:
        step("خواندن جدول‌ها", False, str(e)[:110])
    finally:
        con.close()

    # دیتابیس حسابداری خودمان — جایی که یک‌بار مشکل ساخت
    try:
        bcon = _billing_conn()
        bt = [r[0] for r in bcon.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")]
        bcon.close()
        step("دیتابیس حسابداری", True, f"{len(bt)} جدول")
    except Exception as e:
        step("دیتابیس حسابداری", False, f"{type(e).__name__}: {str(e)[:90]}",
             f"فایل را کنار بگذارید: mv {BILLING_DB} {BILLING_DB}.broken")

    clients, groups, rerr = _read_xui_clients()
    step("پردازش نهایی", clients is not None,
         f"{len(clients)} کانفیگ، {len(groups or [])} گروه" if clients else (rerr or "ناموفق"))

    return {"ok": all(s["ok"] for s in steps), "steps": steps}


# ═══════════════════════════════════════════════════════════
#  تانل — نودها و اتصال بین سرورها
#
#  agent روی سرور ایران به این endpointها وصل می‌شود. احراز
#  هویتش با توکن نود است، نه رمز پنل — تا اگر توکنی لو رفت فقط
#  همان نود باطل شود.
# ═══════════════════════════════════════════════════════════

try:
    import tunnels as TUN
    TUNNELS_OK = True
except Exception as _tun_err:
    TUNNELS_OK = False
    TUN = None


def _need_tunnels():
    if not TUNNELS_OK:
        raise HTTPException(status_code=500,
                            detail="ماژول تانل بارگذاری نشد — nexora update را اجرا کنید")


#: چقدر اختلاف ساعت بین پنل و سرور راه دور تحمل می‌شود.
#: پنج دقیقه هم برای ساعت‌های ناهماهنگ جا دارد و هم پنجره‌ی بازپخش
#: را به‌قدر کافی کوتاه نگه می‌دارد.
AGENT_CLOCK_SKEW = 300


def _agent_node(token: str, *, body: bytes = b"",
                ts: str = "", sign: str = ""):
    """
    نود را از روی توکن پیدا می‌کند، و اگر امضا آمده باشد بررسی‌اش می‌کند.

    امضا اختیاری است تا ایجنت‌های قدیمی از کار نیفتند — ولی وقتی
    بیاید، باید درست باشد. امضای غلط یعنی یا توکن جای دیگری استفاده
    شده یا کسی درخواست را دستکاری کرده؛ هیچ‌کدام را رد نکردن اشتباه
    است.
    """
    _need_tunnels()
    if not token:
        raise HTTPException(status_code=401, detail="توکن ارسال نشده")
    node = TUN.node_by_token(token.strip())
    if not node:
        raise HTTPException(status_code=401, detail="توکن نامعتبر یا نود غیرفعال")

    if sign:
        import hashlib
        import hmac
        try:
            drift = abs(int(time.time()) - int(ts))
        except (TypeError, ValueError):
            raise HTTPException(status_code=401, detail="زمان درخواست نامعتبر")
        if drift > AGENT_CLOCK_SKEW:
            raise HTTPException(
                status_code=401,
                detail=f"اختلاف ساعت {drift} ثانیه — ساعت سرور را هماهنگ کنید")

        want = hmac.new(token.strip().encode(),
                        ts.encode() + b"." + (body or b""),
                        hashlib.sha256).hexdigest()
        if not hmac.compare_digest(want, sign.strip()):
            raise HTTPException(status_code=401, detail="امضای درخواست نادرست")

    return node


@app.post("/api/agent/checkin")
async def agent_checkin(request: Request, payload: dict = None,
                        x_agent_token: str = Header(None),
                        x_agent_time: str = Header(None),
                        x_agent_sign: str = Header(None)):
    """
    agent هر ۳۰ ثانیه اینجا خبر می‌دهد و کارهایش را می‌گیرد.

    این تنها راه ارتباط است؛ پنل هرگز به سرور ایران وصل نمی‌شود.
    """
    raw = await request.body()
    node = _agent_node(x_agent_token, body=raw,
                       ts=x_agent_time or "", sign=x_agent_sign or "")
    TUN.touch_node(node["id"], (payload or {}).get("metrics"))
    jobs = TUN.take_jobs(node["id"])

    # نسخه‌ی پنل را می‌فرستیم تا ایجنت بفهمد ماژول‌های کش‌شده‌اش
    # کهنه‌اند. بدون این، ایجنتی که یک بار monitor.py را گرفته، تا
    # ابد همان نسخه را نگه می‌دارد و قابلیت‌های تازه هرگز نمی‌رسند.
    try:
        pv = (Path(__file__).resolve().parent.parent / "VERSION"
              ).read_text(encoding="utf-8").strip()
    except Exception:
        pv = ""

    return {"ok": True, "node": node["name"], "jobs": jobs,
            "interval": 30, "panelVersion": pv}


@app.post("/api/agent/job-result")
def agent_job_result(payload: dict, x_agent_token: str = Header(None)):
    """نتیجه‌ی یک کار."""
    node = _agent_node(x_agent_token)
    p = payload or {}
    try:
        jid = int(p.get("job_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="شناسه کار نامعتبر")

    ok = bool(p.get("ok"))

    # نتیجه‌ی کامل برای تحلیل می‌ماند؛ فقط چیزی که در جدول کارها
    # ذخیره می‌شود کوتاه می‌شود.
    #
    # قبلاً همین‌جا به ۴۰۰۰ کاراکتر بریده می‌شد و بعد همان بریده
    # json.loads می‌شد. گزارش مانیتورینگ از ۴۰۰۰ بزرگ‌تر است، پس
    # JSON ناقص می‌شد، تجزیه می‌افتاد، و خطا در except بی‌صدا گم
    # می‌شد — کار «موفق» ثبت می‌شد و هیچ داده‌ای ذخیره نمی‌شد.
    full = str(p.get("result") or "")

    # فقط صاحبِ کار می‌تواند ببنددش، و دستور را از روی ردیفِ خودِ کار
    # می‌خوانیم نه از چیزی که در پاسخ نوشته شده.
    action = TUN.finish_job(jid, ok, full[:4000], node_id=node["id"])
    if action is None:
        TUN.log(node_id=node["id"], level="warn",
                message=f"نتیجه‌ی کار {jid} رد شد — این کار برای این نود نیست")
        raise HTTPException(status_code=404,
                            detail="این کار برای این نود نیست")
    result = full

    # نتیجه‌ی سنجش را جدا نگه می‌داریم تا روند قابل دیدن باشد
    if ok and action == "monitor" and p.get("tunnel_id"):
        try:
            _tid = int(p["tunnel_id"])
        except (TypeError, ValueError):
            _tid = None
        # شناسه‌ی تانل از خودِ پاسخ می‌آید؛ بدون این بررسی هر نودی
        # می‌توانست سنجش جعلی روی تاریخچه‌ی تانلِ نود دیگری بنویسد.
        if _tid is not None and TUN.tunnel_on_node(_tid, node["id"]):
            try:
                TUN.save_metrics(_tid, json.loads(result))
            except Exception:
                pass
        elif _tid is not None:
            TUN.log(node_id=node["id"], level="warn",
                    message=f"سنجشِ تانل {_tid} رد شد — روی این نود نیست")

    if ok and action == "health":
        try:
            data = json.loads(result)
            TUN.save_health(node["id"], data)
            _health_alert(node["name"], data, key=f"node:{node['id']}")
        except Exception:
            pass

    if ok and action in ("sysmon", "firewall"):
        try:
            TUN.save_sysmon(node["id"], {
                "kind": action,
                "data": json.loads(result),
            })
        except Exception:
            log.debug("ذخیره‌ی مانیتورینگ نود ناموفق", exc_info=True)

    if not ok:
        TUN.log(node_id=node["id"], level="error",
                message=f"کار {jid} ناموفق: {result[:150]}")
    return {"ok": True}


@app.get("/api/agent/install.sh")
def agent_installer(token: str = "", panel: str = ""):
    """
    اسکریپت نصب agent — بدون احراز هویت، چون خودش توکن را در
    خط فرمان دارد و کاری جز نصب انجام نمی‌دهد.
    """
    _need_tunnels()
    safe_token = "".join(ch for ch in token if ch.isalnum() or ch in "_-")[:80]
    safe_panel = "".join(ch for ch in panel
                         if ch.isalnum() or ch in ".:/-_")[:120]

    script = f"""#!/usr/bin/env bash
#
# Nexora agent installer.
#
# Output is English on purpose: Persian renders as boxes on most server
# terminals, and an error you cannot read is an error you will not notice.

set -u

PANEL="{safe_panel}"
TOKEN="{safe_token}"

G=$'\\033[38;5;42m'; R=$'\\033[38;5;203m'; D=$'\\033[38;5;245m'; X=$'\\033[0m'
ok(){{ echo "  ${{G}}OK${{X}}    $1"; }}
bad(){{ echo "  ${{R}}FAIL${{X}}  $1"; }}
info(){{ echo "  ${{D}}$1${{X}}"; }}

echo
echo "Nexora agent installer"
echo

[ "$(id -u)" -eq 0 ] || {{ bad "Run with sudo"; exit 1; }}

if ! command -v python3 >/dev/null 2>&1; then
  info "Installing python3..."
  apt-get update -qq >/dev/null 2>&1
  apt-get install -y python3 >/dev/null 2>&1 || {{ bad "Could not install python3"; exit 1; }}
fi
ok "python3 $(python3 -V 2>&1 | cut -d' ' -f2)"

# Reachability is checked before anything is installed, because it is the
# most common reason a node never shows up online.
CODE=$(curl -s -o /dev/null -w "%{{http_code}}" --max-time 15 "$PANEL/api/health" 2>/dev/null || echo 000)
if [ "$CODE" = "200" ]; then
  ok "Panel reachable"
else
  bad "Cannot reach the panel (HTTP $CODE)"
  info "Tried: $PANEL/api/health"
  info "Check DNS, firewall, and that the panel is running."
  exit 1
fi

mkdir -p /opt/nexora-agent/bin /opt/nexora-agent/configs
if ! curl -fsSL --max-time 60 "$PANEL/api/agent/agent.py" -o /opt/nexora-agent/nexora-agent.py; then
  bad "Download failed"
  exit 1
fi

SIZE=$(wc -c < /opt/nexora-agent/nexora-agent.py)
if [ "$SIZE" -lt 5000 ]; then
  bad "Downloaded file is too small ($SIZE bytes)"
  head -3 /opt/nexora-agent/nexora-agent.py | sed 's/^/    /'
  exit 1
fi
chmod +x /opt/nexora-agent/nexora-agent.py
ok "Agent downloaded ($SIZE bytes)"

if ! python3 -m py_compile /opt/nexora-agent/nexora-agent.py 2>/dev/null; then
  bad "Downloaded file is not valid Python"
  exit 1
fi
ok "Agent file is valid"

# One manual check-in before the service is installed. If this fails the
# service would fail too, and finding out now beats reading journald later.
OUT=$(NEXORA_PANEL="$PANEL" NEXORA_TOKEN="$TOKEN" timeout 25 python3 -c '
import sys, importlib.util
spec = importlib.util.spec_from_file_location("ag", "/opt/nexora-agent/nexora-agent.py")
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
r = a.api("checkin", {{"metrics": a.metrics()}})
if r.get("error"):
    print("ERROR " + str(r["error"])); sys.exit(1)
print("NODE " + str(r.get("node", "?")))
' 2>&1)

if echo "$OUT" | grep -q "^NODE "; then
  ok "Check-in succeeded - node: $(echo "$OUT" | sed 's/^NODE //')"
else
  bad "Check-in failed"
  echo "$OUT" | sed 's/^/    /'
  info "The token may be wrong, or the node was removed from the panel."
  exit 1
fi

cat > /etc/systemd/system/nexora-agent.service <<UNIT
[Unit]
Description=Nexora Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Environment="NEXORA_PANEL=$PANEL"
Environment="NEXORA_TOKEN=$TOKEN"
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/usr/bin/python3 /opt/nexora-agent/nexora-agent.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable nexora-agent >/dev/null 2>&1
systemctl restart nexora-agent
sleep 4

if systemctl is-active --quiet nexora-agent; then
  ok "Service is running"
  echo
  info "Recent log:"
  journalctl -u nexora-agent -n 5 --no-pager -o cat 2>/dev/null | sed 's/^/    /'
  echo
  echo "  ${{G}}Done.${{X}} The node should show as online within 30 seconds."
else
  bad "Service failed to start"
  echo
  journalctl -u nexora-agent -n 25 --no-pager 2>/dev/null | sed 's/^/    /'
  exit 1
fi
echo
"""
    return Response(content=script, media_type="text/x-shellscript")


@app.get("/api/agent/health.py")
def agent_health_module():
    """ماژول سلامت — agent از اینجا می‌گیرد تا نسخه‌ها یکی بماند."""
    p = _root_dir() / "backend" / "health.py"
    if not p.exists():
        raise HTTPException(status_code=404, detail="ماژول سلامت پیدا نشد")
    return Response(content=p.read_text(encoding="utf-8"),
                    media_type="text/x-python")


@app.get("/api/agent/monitor.py")
def agent_monitor_module():
    """
    ماژول مانیتورینگ برای سرورهای دیگر.

    همان فایلی که پنل خودش استفاده می‌کند. نسخه‌ی دوم نوشتن یعنی دو
    مجموعه آستانه و دو جور خروجی — و مدیری که نمی‌فهمد چرا سرور
    ایران عدد دیگری می‌گوید.
    """
    p = _root_dir() / "backend" / "monitor.py"
    if not p.exists():
        raise HTTPException(status_code=404, detail="ماژول مانیتورینگ پیدا نشد")
    return Response(content=p.read_text(encoding="utf-8"),
                    media_type="text/x-python")


@app.get("/api/agent/firewall.py")
def agent_firewall_module():
    """ماژول فایروال برای سرورهای دیگر."""
    p = _root_dir() / "backend" / "firewall.py"
    if not p.exists():
        raise HTTPException(status_code=404, detail="ماژول فایروال پیدا نشد")
    return Response(content=p.read_text(encoding="utf-8"),
                    media_type="text/x-python")


@app.get("/api/agent/agent.py")
def agent_source():
    """کد agent — از خود پنل سرو می‌شود تا نسخه‌ها همگام بمانند."""
    p = _root_dir() / "agent" / "nexora-agent.py"
    if not p.exists():
        raise HTTPException(status_code=404, detail="فایل agent پیدا نشد")
    return Response(content=p.read_text(encoding="utf-8"),
                    media_type="text/x-python")


# ── مدیریت از پنل ──

@app.get("/api/admin/tunnel/node/{node_id}/check")
def tunnel_node_check(node_id: int, x_admin_password: str = Header(...)):
    """
    چرا نود آفلاین است.

    وقتی agent نصب شده ولی پنل آفلاین نشانش می‌دهد، مشکل معمولاً
    یکی از چند چیز مشخص است. به‌جای اینکه کاربر حدس بزند، اینجا
    می‌گوییم کدام.
    """
    check_auth(x_admin_password)
    _need_tunnels()

    con = TUN.conn()
    try:
        r = con.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="نود پیدا نشد")
        node = dict(r)
    finally:
        con.close()

    steps = []

    def step(title, ok, detail="", hint=""):
        steps.append({"title": title, "ok": ok, "detail": detail, "hint": hint})

    never = not node.get("last_seen")
    online = TUN._is_online(node.get("last_seen"))

    step("نود در پنل ثبت است", True, node["name"])

    if never:
        step("agent تا حالا تماس گرفته", False, "هیچ تماسی ثبت نشده",
             "یعنی یا agent نصب نشده، یا نصب شده و اجرا نمی‌شود، "
             "یا اجرا می‌شود ولی به پنل نمی‌رسد")
    else:
        step("آخرین تماس", True, node["last_seen"])
        step("زنده است", online,
             "کمتر از ۹۰ ثانیه پیش" if online else "بیش از ۹۰ ثانیه سکوت",
             "" if online else "روی سرور ایران: systemctl status nexora-agent")

    # آیا خود پنل از بیرون در دسترس است؟
    reachable = None
    try:
        cfg = load_config()
        domain = ((cfg.get("advanced") or {}).get("panelDomain") or "").strip()
    except Exception:
        domain = ""

    step("دستور نصب", True,
         "از دکمه‌ی «توکن جدید» دوباره بگیرید اگر لازم شد")

    return {
        "ok": online,
        "node": node["name"],
        "online": online,
        "neverSeen": never,
        "steps": steps,
        "commands": [
            {"label": "وضعیت agent", "cmd": "systemctl status nexora-agent"},
            {"label": "لاگ زنده", "cmd": "journalctl -u nexora-agent -n 40 --no-pager"},
            {"label": "تست دسترسی به پنل",
             "cmd": "curl -sI https://YOUR-PANEL/api/health"},
            {"label": "ری‌استارت", "cmd": "systemctl restart nexora-agent"},
        ],
    }


@app.post("/api/admin/tunnel/{tid}/monitor")
def tunnel_monitor(tid: int, x_admin_password: str = Header(...)):
    """سنجش کیفیت — در صف agent قرار می‌گیرد."""
    check_auth(x_admin_password)
    _need_tunnels()

    t = TUN.get_tunnel(tid)
    if not t:
        raise HTTPException(status_code=404, detail="تانل پیدا نشد")

    ports = [p["local"] for p in (t.get("ports") or [])][:6]
    payload = {"tunnel_id": tid, "host": "127.0.0.1", "ports": ports}

    # اگر پورت وب دارد، پاسخ HTTP را هم می‌سنجیم
    for p in ports:
        if p in (80, 443, 8443, 2053, 2087, 8080):
            scheme = "http" if p in (80, 8080) else "https"
            payload["url"] = f"{scheme}://127.0.0.1:{p}/"
            break

    TUN.queue_job(t["node_id"], "monitor", payload)
    return {"ok": True, "queued": True, "ports": ports}


@app.get("/api/admin/tunnel/{tid}/metrics")
def tunnel_metrics(tid: int, x_admin_password: str = Header(...)):
    """تاریخچه و خلاصه‌ی سنجش."""
    check_auth(x_admin_password)
    _need_tunnels()
    return TUN.get_metrics(tid)


@app.get("/api/admin/tunnel/overview")
def tunnel_overview(x_admin_password: str = Header(...)):
    """نمای کلی: نودها، تانل‌ها، رویدادها."""
    check_auth(x_admin_password)
    _need_tunnels()

    nodes = TUN.list_nodes()
    tuns = TUN.list_tunnels()

    return {
        "ready": True,
        "nodes": nodes,
        "tunnels": tuns,
        "events": TUN.recent_events(40),
        "engines": [{"key": k, **v} for k, v in TUN.ENGINES.items()],
        "stats": {
            "nodes": len(nodes),
            "online": sum(1 for n in nodes if n["online"]),
            "tunnels": len(tuns),
            "running": sum(1 for t in tuns if t["status"] == "running"),
        },
    }


@app.post("/api/admin/tunnel/node/{node_id}/sysmon")
def node_sysmon_request(node_id: int, kind: str = "sysmon",
                        x_admin_password: str = Header(...)):
    """
    درخواست مانیتورینگ از یک سرور دیگر.

    کار در صف می‌نشیند و agent در چک‌این بعدی‌اش برش می‌دارد — پس
    این فوری جواب نمی‌دهد و نباید هم بدهد. پنل بعد از چند ثانیه
    نتیجه را از مسیر GET می‌خواند.
    """
    check_auth(x_admin_password)
    _need_tunnels()
    if kind not in ("sysmon", "firewall"):
        raise HTTPException(status_code=400, detail="نوع درخواست نامعتبر است")
    jid = TUN.queue_job(node_id, kind, {})
    return {"ok": True, "jobId": jid,
            "note": "درخواست ثبت شد — نتیجه تا چند ثانیه‌ی دیگر می‌رسد"}


@app.get("/api/admin/tunnel/node/{node_id}/sysmon")
def node_sysmon_get(node_id: int, x_admin_password: str = Header(...)):
    """
    آخرین مانیتورینگ ثبت‌شده‌ی یک سرور.

    اگر هنوز چیزی نرسیده، خالی برمی‌گردد و پنل خودش می‌گوید منتظر
    بماند — نه اینکه خطا نشان دهد و مدیر فکر کند چیزی خراب است.
    """
    check_auth(x_admin_password)
    _need_tunnels()

    # نسخه‌ی ایجنت مهم است: دستور sysmon از ۱.۴.۰ اضافه شده. اگر
    # ایجنتِ روی سرور قدیمی باشد، کار در صف می‌ماند و هیچ‌وقت جواب
    # نمی‌آید — و کاربر فقط یک صفحه‌ی خالی می‌بیند بدون هیچ توضیحی.
    stale_agent = None
    last_error = None
    try:
        c = TUN.conn()
        try:
            row = c.execute(
                "SELECT agent_version, last_seen FROM nodes WHERE id = ?",
                (node_id,)).fetchone()
            if row:
                ver = (row["agent_version"] or "").strip()
                # ایجنت‌های قبل از ۱.۵.۰ نسخه‌ی ۱.۰.۰ گزارش می‌کردند
                # و هیچ‌وقت بالا نرفت. پس هر چیزی زیر ۱.۵.۰ — و هر
                # ایجنتی که اصلاً نسخه نمی‌دهد — قدیمی است.
                if not ver:
                    stale_agent = "نامشخص"
                elif _older_than(ver, "1.5.0"):
                    stale_agent = ver
            bad = c.execute(
                """SELECT result FROM jobs
                   WHERE node_id = ? AND action IN ('sysmon','firewall')
                     AND status = 'failed'
                   ORDER BY id DESC LIMIT 1""", (node_id,)).fetchone()
            if bad and bad["result"]:
                last_error = str(bad["result"])[:200]
        finally:
            c.close()
    except Exception:
        log.debug("خواندن نسخه‌ی ایجنت ناموفق", exc_info=True)

    saved = TUN.get_sysmon(node_id)
    if not saved:
        note = "هنوز گزارشی از این سرور نرسیده است"
        if stale_agent:
            note = (f"ایجنت این سرور نسخه‌ی {stale_agent} است و دستور "
                    "مانیتورینگ را نمی‌شناسد — باید به‌روز شود")
        elif last_error:
            note = f"آخرین تلاش ناموفق بود: {last_error}"
        return {"ready": False, "note": note,
                "staleAgent": stale_agent, "lastError": last_error}

    return {"ready": True, "at": saved.get("at"),
            "kind": (saved.get("data") or {}).get("kind"),
            "data": (saved.get("data") or {}).get("data"),
            "staleAgent": stale_agent, "lastError": last_error}


def _older_than(ver, floor):
    """
    مقایسه‌ی نسخه‌های x.y.z.

    نسخه‌ی نامفهوم «قدیمی» حساب نمی‌شود: ادعای نادرست بدتر از
    نگفتن است — کاربر را دنبال به‌روزرسانیِ بی‌دلیل می‌فرستد.
    """
    if not _re.match(r"^\s*\d+(\.\d+)*", str(ver or "")):
        return False

    def parts(v):
        out = []
        for chunk in str(v).strip().split("."):
            digits = "".join(ch for ch in chunk if ch.isdigit())
            out.append(int(digits) if digits else 0)
        return (out + [0, 0, 0])[:3]

    try:
        return parts(ver) < parts(floor)
    except Exception:
        return False



def _external_base(request):
    """
    آدرس بیرونی پنل — همان چیزی که ایجنت با آن وصل می‌شود.

    چرا به این سادگی نیست:
        پنل پشت nginx اجرا می‌شود، پس request.base_url چیزی مثل
        http://127.0.0.1:8100 می‌دهد — آدرس داخلی، نه دامنه‌ای که
        ایجنت می‌شناسد.

        ایجنت هر آدرسی را که با PANEL_URL خودش شروع نشود رد می‌کند،
        و درست هم می‌کند: نباید فایل اجرایی‌اش را از هر جایی بگیرد.
        نتیجه این بود که به‌روزرسانی ایجنت همیشه با «آدرس خارج از
        پنل مجاز نیست» رد می‌شد — و چون ایجنت قدیمی بود، خودش هم
        نمی‌توانست این را درست کند.

        هدرهایی که nginx می‌گذارد آدرس واقعی را دارند.
    """
    env = os.getenv("NEXORA_PANEL_URL", "").strip().rstrip("/")
    if env:
        return env

    try:
        h = request.headers
        host = (h.get("x-forwarded-host") or h.get("host") or "").split(",")[0]
        host = host.strip()
        proto = (h.get("x-forwarded-proto") or "").split(",")[0].strip()
        if host:
            if not proto:
                proto = "https" if not host.startswith(("127.", "localhost")) else "http"
            return f"{proto}://{host}"
    except Exception:
        pass

    try:
        return str(request.base_url).rstrip("/")
    except Exception:
        return ""


@app.post("/api/admin/tunnel/node/{node_id}/update-agent")
def node_update_agent(node_id: int, request: Request,
                      x_admin_password: str = Header(...)):
    """
    به‌روزرسانی ایجنت یک سرور از روی همین پنل.

    بدون این، مدیر باید دستی SSH بزند و اسکریپت نصب را دوباره اجرا
    کند — کاری که بیشتر آدم‌ها انجام نمی‌دهند و در نتیجه سرورهایشان
    برای همیشه روی نسخه‌ی قدیمی می‌ماند.
    """
    check_auth(x_admin_password)
    _need_tunnels()
    # آدرس را عمداً نمی‌فرستیم.
    #
    # ایجنت هر آدرسی را که با PANEL_URL خودش شروع نشود رد می‌کند، و
    # درست هم می‌کند — نباید فایل اجرایی‌اش را از هر جایی بگیرد. ولی
    # PANEL_URL چیزی است که موقع نصب به ایجنت داده شده، و پنل آن را
    # نمی‌داند: هدرهای nginx دامنه را می‌دهند در حالی که ایجنت ممکن
    # است با آی‌پی و پورت وصل شده باشد. نتیجه، سه کار پشت سر هم با
    # «آدرس به‌روزرسانی خارج از پنل مجاز نیست» بود.
    #
    # وقتی آدرس خالی باشد، ایجنت خودش از PANEL_URL خودش می‌سازدش —
    # همان آدرسی که همین حالا با آن چک‌این می‌کند، پس قطعاً درست
    # است. پنل حدس نمی‌زند، و نگهبانِ ایجنت هم سر جایش می‌ماند.
    jid = TUN.queue_job(node_id, "update_agent", {"url": ""})
    return {"ok": True, "jobId": jid,
            "note": "به‌روزرسانی در صف قرار گرفت — ایجنت بعد از "
                    "چک‌این بعدی خودش را به‌روز و ری‌استارت می‌کند"}


@app.post("/api/admin/tunnel/node")
def tunnel_node_add(payload: dict, x_admin_password: str = Header(...)):
    check_auth(x_admin_password)
    _need_tunnels()
    name = (payload or {}).get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="نام سرور لازم است")
    res = TUN.create_node(name, (payload.get("role") or "iran"),
                          payload.get("note") or "")
    return {"ok": True, **res}


@app.delete("/api/admin/tunnel/node/{node_id}")
def tunnel_node_del(node_id: int, x_admin_password: str = Header(...)):
    check_auth(x_admin_password)
    _need_tunnels()
    TUN.delete_node(node_id)
    return {"ok": True}


@app.post("/api/admin/tunnel/node/{node_id}/rotate")
def tunnel_node_rotate(node_id: int, x_admin_password: str = Header(...)):
    check_auth(x_admin_password)
    _need_tunnels()
    return {"ok": True, "token": TUN.rotate_token(node_id)}


@app.post("/api/admin/tunnel")
def tunnel_add(payload: dict, x_admin_password: str = Header(...)):
    check_auth(x_admin_password)
    _need_tunnels()
    try:
        tid = TUN.create_tunnel(payload or {})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "id": tid}


@app.put("/api/admin/tunnel/{tid}")
def tunnel_edit(tid: int, payload: dict, x_admin_password: str = Header(...)):
    check_auth(x_admin_password)
    _need_tunnels()
    try:
        TUN.update_tunnel(tid, payload or {})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@app.delete("/api/admin/tunnel/{tid}")
def tunnel_del(tid: int, x_admin_password: str = Header(...)):
    check_auth(x_admin_password)
    _need_tunnels()
    t = TUN.get_tunnel(tid)
    if t:
        TUN.queue_job(t["node_id"], "remove", {"tunnel_id": tid})
    TUN.delete_tunnel(tid)
    return {"ok": True}


@app.post("/api/admin/tunnel/{tid}/deploy")
def tunnel_deploy(tid: int, x_admin_password: str = Header(...)):
    """
    اعمال تانل روی سرور ایران.

    دو کار در صف می‌رود: نصب باینری و نوشتن کانفیگ. اگر باینری
    از قبل باشد، نصب سریع رد می‌شود.
    """
    check_auth(x_admin_password)
    _need_tunnels()

    t = TUN.get_tunnel(tid, with_secret=True)
    if not t:
        raise HTTPException(status_code=404, detail="تانل پیدا نشد")

    try:
        cfg = TUN.build_config(t, "iran")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    TUN.queue_job(t["node_id"], "install", {"engine": t["engine"]})
    TUN.queue_job(t["node_id"], "apply",
                  {"tunnel_id": tid, "engine": t["engine"],
                   "config": cfg, "side": "iran"})

    # اگر سرور خارج هم agent دارد، همان‌جا هم راه‌اندازی می‌شود.
    # بدون این، هر تانل یک نصب دستی روی خارج می‌خواهد — که کل
    # هدف این بخش را از بین می‌برد.
    sides = ["ایران"]
    if t.get("foreign_node"):
        try:
            cfg_f = TUN.build_config(t, "foreign")
            TUN.queue_job(t["foreign_node"], "install", {"engine": t["engine"]})
            TUN.queue_job(t["foreign_node"], "apply",
                          {"tunnel_id": tid, "engine": t["engine"],
                           "config": cfg_f, "side": "foreign"})
            sides.append("خارج")
        except Exception:
            pass

    TUN.set_status(tid, "deploying")
    TUN.log(node_id=t["node_id"], tunnel_id=tid,
            message=f"اعمال تانل «{t['name']}» — سمت " + " و ".join(sides))
    return {"ok": True, "sides": sides,
            "manual": "خارج" not in sides}


@app.post("/api/admin/tunnel/{tid}/action/{what}")
def tunnel_action(tid: int, what: str, x_admin_password: str = Header(...)):
    check_auth(x_admin_password)
    _need_tunnels()
    if what not in ("start", "stop", "restart", "status", "logs"):
        raise HTTPException(status_code=400, detail="دستور نامعتبر")

    t = TUN.get_tunnel(tid)
    if not t:
        raise HTTPException(status_code=404, detail="تانل پیدا نشد")

    TUN.queue_job(t["node_id"], what, {"tunnel_id": tid})
    return {"ok": True, "queued": what}


@app.get("/api/admin/tunnel/{tid}/config")
def tunnel_config(tid: int, side: str = "foreign",
                  x_admin_password: str = Header(...)):
    """
    کانفیگ سمت خارج — که مدیر باید دستی روی سرور خارجش بگذارد،
    چون آنجا agent نصب نیست.
    """
    check_auth(x_admin_password)
    _need_tunnels()

    t = TUN.get_tunnel(tid, with_secret=True)
    if not t:
        raise HTTPException(status_code=404, detail="تانل پیدا نشد")
    if side not in ("iran", "foreign"):
        raise HTTPException(status_code=400, detail="سمت نامعتبر")

    try:
        cfg = TUN.build_config(t, side)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"config": cfg, "engine": t["engine"], "side": side,
            "filename": f"tunnel-{tid}.{'yaml' if t['engine'] == 'gost' else 'toml'}"}


# ═══════════════════════════════════════════════════════════
#  سلامت سیستم
# ═══════════════════════════════════════════════════════════

try:
    import health as HEALTH
except Exception:
    HEALTH = None

# آخرین وضعیت هر سرور، تا فقط وقتی چیزی عوض شد هشدار بدهیم
_health_state = {}


def _health_ports():
    """پورت‌هایی که باید شنونده داشته باشند — از inboundهای ۳x-ui."""
    ports = set()
    try:
        con, _ = _xui_conn()
        if con:
            try:
                for r in con.execute("SELECT port FROM inbounds WHERE enable=1"):
                    if r[0]:
                        ports.add(int(r[0]))
            except Exception:
                pass
            con.close()
    except Exception:
        pass
    return sorted(ports)[:12]


def _health_domain():
    try:
        cfg = load_config()
        return ((cfg.get("advanced") or {}).get("panelDomain") or "").strip() or None
    except Exception:
        return None



#: هر چند ثانیه یک بار گزارش کامل سرور تازه شود.
#: پنج دقیقه: هم‌قدم با چرخه‌ی سلامت، و به‌قدر کافی کوتاه که وقتی
#: مدیر صفحه را باز می‌کند عدد کهنه نبیند.
SYSMON_MAX_AGE = 300


def _sysmon_fresh(node_id):
    """
    آیا گزارش این نود به‌قدر کافی تازه است.

    بدون این بررسی، هر چرخه یک کار تازه ثبت می‌شد حتی وقتی گزارش
    چند ثانیه پیش رسیده بود — صف بی‌دلیل شلوغ می‌شد.
    """
    try:
        saved = TUN.get_sysmon(node_id)
        if not saved or not saved.get("at"):
            return False
        at = datetime.fromisoformat(str(saved["at"]))
        return (datetime.now() - at).total_seconds() < SYSMON_MAX_AGE
    except Exception:
        return False


def _health_alert(server, data, key):
    """
    هشدار تلگرام — وقتی وضعیت عوض شود، و اولین باری که خراب است.

    اگر هر بار پیام بدهیم، بعد از چند ساعت کسی نگاهشان نمی‌کند. پس
    تکرارِ همان سطح خبر نمی‌شود.

    ولی «اولین مشاهده» را هم ساکت گذاشتن یک سوراخ واقعی می‌ساخت:
    وضعیت در حافظه‌ی همین پردازه نگه داشته می‌شود، پس هر ری‌استارت
    پنل آن را پاک می‌کند — و `nexora update` هر بار ری‌استارت می‌کند.

    اگر سروری با دیسک پر بالا می‌آمد، اجرای اول فقط ثبت می‌کرد و
    ساکت می‌ماند؛ اجراهای بعدی هم چون سطح عوض نشده بود ساکت
    می‌ماندند. دیسک تا ابد پر و هیچ پیامی. برای سامانه‌ای که تنها
    کارش خبردادن است، بدترین حالت ممکن.

    حالا اولین مشاهده هم خبر می‌شود، ولی فقط وقتی «ok» نباشد — پس
    ری‌استارتِ سرورِ سالم هیچ پیامی نمی‌سازد.
    """
    level = data.get("level", "ok")
    prev = _health_state.get(key)
    _health_state[key] = level

    if prev == level:
        return
    if prev is None and level == "ok":
        return

    crit = [c for c in data.get("checks", []) if c.get("level") == "crit"]
    warn = [c for c in data.get("checks", []) if c.get("level") == "warn"]

    if level == "ok":
        text = f"✅ <b>{server}</b>\n\nمشکلات برطرف شد."
    else:
        icon = "🔴" if level == "crit" else "🟡"
        lines = [f"{icon} <b>{server}</b>", "", data.get("summary", ""), ""]
        for c in (crit + warn)[:6]:
            mark = "❌" if c["level"] == "crit" else "⚠️"
            lines.append(f"{mark} <b>{c['title']}</b> — {c['detail']}")
            if c.get("hint"):
                lines.append(f"   <i>{c['hint'][:110]}</i>")
        text = "\n".join(lines)

    try:
        import sqlite3 as sq
        con = sq.connect(f"file:{BOT_DB}?mode=ro", uri=True, timeout=5)
        con.row_factory = sq.Row
        # مستاجر ریشه، نه هر ردیفی که اول بیاید.
        #
        # بدون این شرط، اگر ردیف مالک یک‌بار پاک و دوباره ساخته شود —
        # که با اجرای دوباره‌ی نصب اتفاق می‌افتد — شناسه‌اش بزرگ‌تر از
        # شناسه‌ی نماینده می‌شود و LIMIT 1 نماینده را برمی‌دارد.
        #
        # آن‌وقت هشدارِ سرورِ مالک با رباتِ نماینده و به گروهِ نماینده
        # فرستاده می‌شود: دیسک پر، سرویس خاموش، انقضای گواهی و نام
        # میزبان‌ها می‌رود دست شخص سوم، و مالک هیچ خبری نمی‌گیرد.
        r = con.execute(
            "SELECT bot_token, admin_id, group_id FROM tenants "
            "WHERE parent_id IS NULL ORDER BY id LIMIT 1").fetchone()
        con.close()
        if not r or not r["bot_token"]:
            return
        target = r["group_id"] or r["admin_id"]
        if not target:
            return
        import urllib.request
        body = json.dumps({"chat_id": target, "text": text,
                           "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{r['bot_token']}/sendMessage",
            data=body, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=12)
    except Exception:
        pass


try:
    import monitor as MONITOR
except Exception:
    try:
        import importlib.util as _ilu
        _ms = _ilu.spec_from_file_location(
            "monitor", Path(__file__).resolve().parent / "monitor.py")
        MONITOR = _ilu.module_from_spec(_ms)
        _ms.loader.exec_module(MONITOR)
    except Exception:
        MONITOR = None


@app.get("/api/admin/monitor")
def monitor_snapshot(sections: str = "", x_admin_password: str = Header(...)):
    """
    وضعیت زنده‌ی سرور.

    sections: فهرست کاما-جدا برای گرفتن فقط بخشی از داده‌ها — صفحه‌ای
    که هر ۵ ثانیه تازه می‌شود نباید هر بار apt را هم صدا بزند.
    """
    check_auth(x_admin_password)
    if not MONITOR:
        raise HTTPException(status_code=500, detail="ماژول مانیتورینگ بارگذاری نشد")

    want = [s.strip() for s in sections.split(",") if s.strip()] or None
    t0 = time.time()
    snap = MONITOR.snapshot(include=want)
    snap["took"] = round(time.time() - t0, 2)
    return snap


@app.get("/api/admin/health/local")
def health_local(x_admin_password: str = Header(...)):
    """سلامت همین سرور — جایی که پنل نصب است."""
    check_auth(x_admin_password)
    if not HEALTH:
        raise HTTPException(status_code=500, detail="ماژول سلامت بارگذاری نشد")

    res = HEALTH.run_all(ports=_health_ports(), domain=_health_domain())
    res["server"] = "سرور پنل"
    return res


@app.get("/api/admin/health/all")
def health_all(x_admin_password: str = Header(...)):
    """
    سلامت همه‌ی سرورها.

    سرور پنل مستقیم بررسی می‌شود؛ نودها آخرین گزارششان را
    برمی‌گردانند — چون بررسی آنجا از طریق agent انجام می‌شود و
    نتیجه‌اش با تاخیر می‌رسد.
    """
    check_auth(x_admin_password)
    servers = []

    if HEALTH:
        try:
            local = HEALTH.run_all(ports=_health_ports(), domain=_health_domain())
            local["server"] = "سرور پنل"
            local["nodeId"] = None
            servers.append(local)
        except Exception as e:
            servers.append({"server": "سرور پنل", "level": "warn",
                            "summary": f"بررسی ناموفق: {str(e)[:80]}",
                            "checks": [], "nodeId": None})

    if TUNNELS_OK:
        try:
            con = TUN.conn()
            rows = [dict(r) for r in con.execute(
                "SELECT id, name, health, health_at FROM nodes WHERE enabled=1")]
            con.close()
            for n in rows:
                if n.get("health"):
                    try:
                        d = json.loads(n["health"])
                        d["server"] = n["name"]
                        d["nodeId"] = n["id"]
                        servers.append(d)
                        continue
                    except Exception:
                        pass
                servers.append({"server": n["name"], "nodeId": n["id"],
                                "level": "unknown", "summary": "هنوز گزارشی نرسیده",
                                "checks": []})
        except Exception:
            pass

    worst = "ok"
    for s in servers:
        if s.get("level") == "crit":
            worst = "crit"
            break
        if s.get("level") == "warn":
            worst = "warn"

    return {"ready": True, "level": worst, "servers": servers,
            "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


@app.post("/api/admin/health/check/{node_id}")
def health_check_node(node_id: int, x_admin_password: str = Header(...)):
    """درخواست بررسی از یک نود."""
    check_auth(x_admin_password)
    _need_tunnels()
    TUN.queue_job(node_id, "health", {})
    return {"ok": True, "queued": True}



# ═══════════════════════════════════════════════════════════
#  پنل نماینده
#
#  چرا یک سطح API جداگانه، و نه استفاده از مسیرهای مدیریتی:
#
#  پنل مدیر ۱۱۴ مسیر دارد و همه‌شان فرض می‌کنند «تو صاحب سیستمی».
#  دادنشان به نماینده یعنی هر کدام باید جداگانه به مستاجر خودش
#  محدود شود — و کافی است یکی جا بیفتد تا نماینده داده‌ی بقیه را
#  ببیند. همین کلاس اشتباه امروز در مسیرهای ایجنت پیدا شد: نودی که
#  احراز هویت شده بود ولی محدود نشده بود، می‌توانست کار نود دیگر را
#  ببندد.
#
#  پس فهرست مجاز، نه فهرست ممنوع: هر چیزی که این‌جا نوشته نشده،
#  برای نماینده اصلاً وجود ندارد. اضافه‌کردن یک قابلیت تازه یک
#  تصمیم آگاهانه است، نه چیزی که خودبه‌خود ارث برسد.
# ═══════════════════════════════════════════════════════════

def _tenant_row(tid):
    """یک مستاجر از دیتابیس ربات — فقط خواندن."""
    con = _bot_conn()
    if not con:
        return None
    try:
        r = con.execute("SELECT * FROM tenants WHERE id=?", (tid,)).fetchone()
        return dict(r) if r else None
    except Exception:
        return None
    finally:
        con.close()


def _tenant_by_slug(slug):
    """
    نماینده از روی نشانیِ لینکش.

    فقط فعال‌ها و آن‌هایی که پنلشان روشن است. بستن یک نماینده باید
    همان لحظه اثر کند، نه اینکه فقط از فهرست پنهانش کند.
    """
    con = _bot_conn()
    if not con or not slug:
        return None
    try:
        r = con.execute(
            # CAST چون روی نصبی که این ستون قبلاً TEXT ساخته شده،
            # مقدارش '1' است و '1' = 1 در SQLite غلط است.
            "SELECT * FROM tenants WHERE portal_slug=? AND is_active=1",
            (str(slug).strip().lower(),)).fetchone()
        # باز یا بسته بودن در پایتون تصمیم گرفته می‌شود، نه در SQL.
        #
        # قبلاً این‌جا CAST(... AS INTEGER)=1 بود و بررسی نشست یک
        # قاعده‌ی دیگر داشت. دو پیاده‌سازی از یک قاعده، دیر یا زود
        # از هم جدا می‌شوند — و شدند: روی '1.0' این یکی باز می‌گفت و
        # آن یکی بسته. حالا یک تابع بیشتر وجود ندارد.
        if not r or not _portal_open(dict(r).get("portal_enabled")):
            return None
        return dict(r)
    except Exception:
        return None
    finally:
        con.close()


#: نشست‌های باز نماینده — توکن به (شناسه‌ی مستاجر، زمان انقضا)
def _portal_open(value):
    """
    آیا پورتالِ این نماینده باز است؟

    فهرست مجاز، نه فهرست ممنوع. سه جا این پرچم را می‌خواندند و هر
    کدام جور دیگری:

      ورود         CAST(... AS INTEGER)=1   — فقط عددِ یک
      بررسی نشست   not in ("0","","None")   — هرچه ناشناخته، باز
      فهرست مدیر   همان فهرست ممنوع

    روی ۰ و ۱ هر سه یک جواب می‌دهند، ولی روی هر مقدار دیگری — ۲،
    "true"، "yes" — ورود می‌بست و نشست باز می‌ماند. یعنی دقیقاً
    برعکسِ چیزی که بالای همان کد نوشته شده بود: «دسترسی همان لحظه
    بسته می‌شود».

    ستون یک‌بار به‌اشتباه TEXT ساخته شده بود و همان یک‌بار کافی بود
    تا هیچ نماینده‌ای نتواند وارد شود. پرچمی که سه جور خوانده شود،
    دیر یا زود همان اتفاق را دوباره می‌سازد.
    """
    if value is None or isinstance(value, bool):
        return value is True
    if isinstance(value, (int, float)):
        return int(value) == 1
    try:
        return int(str(value).strip() or "0") == 1
    except (TypeError, ValueError):
        return False


_PORTAL_SESSIONS = {}
PORTAL_TTL = 12 * 3600
PORTAL_MAX = 2000


def _portal_prune():
    now = _time.time()
    for k in [k for k, v in _PORTAL_SESSIONS.items() if v[1] < now]:
        _PORTAL_SESSIONS.pop(k, None)
    # سقف، تا نشست‌های رهاشده حافظه را نخورند
    if len(_PORTAL_SESSIONS) > PORTAL_MAX:
        for k in sorted(_PORTAL_SESSIONS, key=lambda k: _PORTAL_SESSIONS[k][1])[:500]:
            _PORTAL_SESSIONS.pop(k, None)


@app.post("/api/portal/{slug}/login")
def portal_login(slug: str, payload: dict, request: Request):
    """
    ورود نماینده. همان سدّ حدس‌زدنِ رمز مدیر این‌جا هم هست.
    """
    ip = _auth_ip.get()
    wait = _auth_locked(ip)
    if wait:
        raise HTTPException(
            status_code=429,
            detail=f"تلاش‌های ناموفق زیاد بود. {wait // 60 + 1} دقیقه‌ی دیگر "
                   "دوباره امتحان کنید.",
            headers={"Retry-After": str(wait)})

    t = _tenant_by_slug(slug)
    given = str((payload or {}).get("password") or "")

    # نماینده‌ی ناموجود و رمز غلط یک پیام می‌گیرند: وگرنه می‌شود
    # فهمید کدام نشانی‌ها واقعی‌اند.
    ok = bool(t and t.get("portal_pass") and _hmac.compare_digest(
        given.encode("utf-8"), str(t["portal_pass"]).encode("utf-8")))
    if not ok:
        rec = _auth_failed(ip)
        left = AUTH_MAX_FAILS - rec["n"]
        detail = "نشانی یا رمز نادرست است"
        if 0 < left <= 3:
            detail += f" — {left} تلاش دیگر تا قفل‌شدن موقت"
        raise HTTPException(status_code=401, detail=detail)

    _auth_ok(ip)
    _portal_prune()
    token = "nxp_" + _secrets.token_urlsafe(32)
    _PORTAL_SESSIONS[token] = (int(t["id"]), _time.time() + PORTAL_TTL)
    return {"ok": True, "token": token, "name": t["name"],
            "expiresIn": PORTAL_TTL}


def portal_tenant(x_portal_token: str = Header(None)):
    """
    مستاجرِ نشستِ جاری. هر مسیر نماینده از این رد می‌شود.

    برمی‌گرداند: ردیف کامل مستاجر — تا صداکننده مجبور نباشد شناسه را
    از جای دیگری بگیرد و اشتباهی مستاجر دیگری را بخواند.
    """
    rec = _PORTAL_SESSIONS.get(str(x_portal_token or ""))
    if not rec or rec[1] < _time.time():
        _PORTAL_SESSIONS.pop(str(x_portal_token or ""), None)
        raise HTTPException(status_code=401, detail="نشست منقضی شده — دوباره وارد شوید")

    t = _tenant_row(rec[0])
    if not t or not t.get("is_active") or not _portal_open(
            t.get("portal_enabled")):
        # دسترسی همان لحظه بسته می‌شود، نه سر انقضای نشست.
        _PORTAL_SESSIONS.pop(str(x_portal_token or ""), None)
        raise HTTPException(status_code=403, detail="دسترسی این نماینده بسته شده")
    return t


# ═══════════════════════════════════════════════════════════
#  مینی‌اپ تلگرام
#
#  برگه‌اش: docs/specs/2026-09-16-miniapp.md
#
#  این‌جا هیچ پولی جابه‌جا نمی‌شود و هیچ نرخی حساب نمی‌شود. مینی‌اپ
#  فقط نشان می‌دهد؛ خرید و رسید در خودِ ربات می‌مانند. مالک صریح گفت
#  حسابداری از این بحث جداست.
# ═══════════════════════════════════════════════════════════

#: initData کهنه پذیرفته نمی‌شود.
#
#  بدون این، یک رشته‌ی امضاشده که یک‌بار از دست کسی در رفته، تا ابد
#  کلیدِ حساب آن مشتری می‌ماند.
MINI_MAX_AGE = 24 * 3600


def _mini_check(init_data: str, token: str):
    """
    امضای تلگرام را می‌سنجد. برمی‌گرداند: (درست؟, داده یا پیام خطا)

    الگوریتم خودِ تلگرام:
        secret = HMAC-SHA256(key="WebAppData", msg=<توکن ربات>)
        hash   = HMAC-SHA256(key=secret, msg=<رشته‌ی بررسی>)

    رشته‌ی بررسی، همه‌ی کلیدها جز `hash` است که مرتب شده و با خط تازه
    به هم چسبیده‌اند.

    چرا سخت‌گیرانه: اگر امضا سنجیده نشود، هر کسی می‌تواند
    `user={"id":...}` بفرستد و اشتراک‌های هر مشتری‌ای را ببیند. این
    تنها چیزی است که بین مشتری‌ها دیوار می‌کشد.
    """
    import hashlib
    from urllib.parse import parse_qsl

    if not init_data or not token:
        return False, "دسترسی بدون امضا ممکن نیست"

    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return False, "امضا خوانده نشد"

    got = pairs.pop("hash", "")
    if not got:
        return False, "امضا نیامده"

    check = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret = _hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    want = _hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()

    # compare_digest، نه == : مقایسه‌ی معمولی به‌محض اولین اختلاف
    # برمی‌گردد و از روی زمانش می‌شود امضا را حدس زد
    if not _hmac.compare_digest(want, got):
        return False, "امضا معتبر نیست"

    try:
        age = _time.time() - int(pairs.get("auth_date") or 0)
    except (TypeError, ValueError):
        return False, "تاریخ امضا خوانده نشد"
    if age > MINI_MAX_AGE:
        return False, "این نشست کهنه شده — مینی‌اپ را دوباره باز کنید"
    if age < -300:
        # ساعتِ جلوترِ سرور یا امضای ساختگی
        return False, "تاریخ امضا از آینده است"

    try:
        user = json.loads(pairs.get("user") or "{}")
    except (json.JSONDecodeError, TypeError):
        return False, "اطلاعات کاربر خوانده نشد"
    if not user.get("id"):
        return False, "شناسه‌ی کاربر نیامده"

    return True, {"user": user, "auth_date": pairs.get("auth_date")}


def _mini_tenants():
    """
    رباتی که مینی‌اپ ممکن است از آن باز شده باشد.

    فعلاً فقط مستاجر ریشه — تصمیم مالک. ولی فهرست برمی‌گرداند نه یک
    ردیف، چون قدم بعدی دادنِ همین به نماینده‌هاست و آن‌وقت باید امضا
    با توکنِ هر کدام جدا سنجیده شود.

    `initData` نمی‌گوید از کدام ربات آمده، پس تنها راه امتحان‌کردن
    توکن‌هاست. تعدادشان کم و کراندار است.
    """
    con = _bot_conn()
    if not con:
        return []
    try:
        rows = con.execute(
            "SELECT * FROM tenants WHERE parent_id IS NULL AND is_active=1 "
            "AND bot_token IS NOT NULL ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    except Exception:
        log.debug("خواندن مستاجرها برای مینی‌اپ ناموفق", exc_info=True)
        return []
    finally:
        con.close()


def mini_user(x_telegram_init_data: str = Header(None)):
    """
    کاربرِ مینی‌اپ. هر مسیر `/api/mini/*` از این رد می‌شود.

    برمی‌گرداند: (ردیف مستاجر, ردیف کاربر)

    شناسه از **امضا** برداشته می‌شود، نه از بدنه‌ی درخواست. اگر از
    بدنه خوانده شود، فرستادن شناسه‌ی دیگری کافی است تا کسی حساب
    دیگری را ببیند.
    """
    tenants = _mini_tenants()
    if not tenants:
        raise HTTPException(
            status_code=503,
            detail="رباتی تنظیم نشده — از بخش «ربات تلگرام» توکن را ثبت کنید")

    why = "امضا معتبر نیست"
    for t in tenants:
        ok, data = _mini_check(x_telegram_init_data or "", t.get("bot_token"))
        if ok:
            tg_id = int(data["user"]["id"])
            con = _bot_conn()
            try:
                row = con.execute(
                    "SELECT * FROM users WHERE tenant_id=? AND tg_id=?",
                    (t["id"], tg_id)).fetchone() if con else None
            finally:
                if con:
                    con.close()
            if not row:
                # کاربری که هنوز /start نزده. ساختنش کارِ ربات است،
                # نه این‌جا — وگرنه دو جا کاربر ساخته می‌شود.
                raise HTTPException(
                    status_code=404,
                    detail="هنوز وارد ربات نشده‌اید — یک‌بار /start را بزنید")
            return t, dict(row)
        why = data if isinstance(data, str) else why

    raise HTTPException(status_code=401, detail=why)


def _bot_username(t):
    """
    نام کاربری ربات — و اگر نبود، یک‌بار از تلگرام بپرس و نگه دار.

    چرا لازم شد: همه‌ی دکمه‌های «برو به ربات» در مینی‌اپ (شارژ کیف
    پول، تمدید، پشتیبانی) لینکِ `t.me/<username>` می‌سازند. این ستون
    فقط وقتی پر می‌شود که توکن از خودِ پنل ثبت شده باشد؛ اگر با
    نصب‌کننده یا CLI تنظیم شده باشد خالی می‌ماند و همه‌ی آن دکمه‌ها
    بی‌صدا بن‌بست می‌شوند — کاربر می‌زند و هیچ اتفاقی نمی‌افتد.

    یک‌بار می‌پرسیم و در همان ستون می‌نشیند، پس دفعه‌ی بعد رایگان
    است.
    """
    u = (t.get("bot_username") or "").strip().lstrip("@")
    if u:
        return u
    tok = t.get("bot_token")
    if not tok:
        return ""
    try:
        ok, who = _tg_get_me(tok)
    except Exception:
        log.warning("getMe برای پرکردن bot_username نشد", exc_info=True)
        return ""
    if not ok or not who:
        return ""
    who = str(who).lstrip("@")
    try:
        con = _bot_rw()
        try:
            con.execute("UPDATE tenants SET bot_username=? WHERE id=?", (who, t["id"]))
            con.commit()
        finally:
            con.close()
    except Exception:
        # نتوانستیم نگه داریم؛ ولی همین حالا جواب را داریم
        log.warning("ذخیره‌ی bot_username نشد", exc_info=True)
    return who


def _ref_count(tid, uid):
    """چند نفر با کدِ این کاربر وارد شده‌اند."""
    con = _bot_conn()
    if not con:
        return 0
    try:
        row = con.execute(
            "SELECT COUNT(*) n FROM users WHERE tenant_id=? AND referred_by=?",
            (tid, uid)).fetchone()
        return int(row["n"] or 0) if row else 0
    except Exception:
        log.debug("شمارشِ دعوت‌ها ناموفق", exc_info=True)
        return 0
    finally:
        con.close()


@app.get("/api/mini/me")
def mini_me(tu: tuple = Depends(mini_user)):
    """کیستم، چقدر پول و سکه دارم، و برندِ این ربات چیست."""
    t, u = tu
    try:
        st = json.loads(t.get("settings") or "{}")
    except (json.JSONDecodeError, TypeError):
        st = {}
    return {
        "name": u.get("first_name") or "",
        # شناسه‌ی تلگرام روی کارتِ موجودی نشان داده می‌شود — همان
        # چیزی که مشتری موقع پشتیبانی باید بگوید، پس باید جایی
        # باشد که بتواند بخواند و کپی کند.
        "tgId": int(u.get("tg_id") or 0),
        "username": u.get("username") or "",
        "balance": int(u.get("balance") or 0),
        "coins": int(u.get("coins") or 0),
        "brand": st.get("brand") or t.get("name") or "",
        "support": st.get("support_username") or st.get("support") or "",
        "botUsername": _bot_username(t),
        "trialUsed": bool(u.get("trial_used")),
        # لوگوی همین فروشگاه. خالی یعنی «نشان نکسورا» — رابط خودش
        # تصمیم می‌گیرد، این‌جا حدس نمی‌زنیم.
        "logo": _logo_url(t["id"]),
        "avatar": _avatar_url(t["id"], u["id"]),
        "phone": u.get("phone") or "",
        # دعوتِ دوست — کدِ خودِ کاربر و اینکه چند نفر با آن آمده‌اند.
        # داده‌اش از قبل بود و فقط راهی برای دیدنش نداشت؛ مشتری
        # مجبور بود از منوی ربات پیدایش کند.
        "refCode": u.get("ref_code") or "",
        "refCount": _ref_count(t["id"], u["id"]),
    }


@app.get("/api/mini/rewards")
def mini_rewards(tu: tuple = Depends(mini_user)):
    """
    سکه و دعوت — هر چیزی که صفحه‌ی پاداش نشان می‌دهد.

    **هیچ عددی این‌جا حساب نمی‌شود.** پله‌ی فعلی و پله‌ی بعدی از
    `core.coin_progress` می‌آیند — همان تابعی که لحظه‌ی خرید قیمت
    را کم می‌کند. اگر مینی‌اپ نردبان را خودش می‌ساخت، روزی به کاربر
    «۳۰٪ تخفیف» نشان می‌داد و صندوق ۲۰٪ کم می‌کرد؛ و حق با صندوق
    بود، چون پول آن‌جا جابه‌جا می‌شود.

    همین باگ یک‌بار در همین مخزن رخ داد: قیمتِ مینی‌اپ تخفیفِ سکه را
    نمی‌دید، چون نسخه‌ی دومی از قیمت‌گذاری نوشته شده بود.
    """
    t, u = tu
    h = _bot_handlers()
    core = h.core
    try:
        st = json.loads(t.get("settings") or "{}")
    except (json.JSONDecodeError, TypeError):
        st = {}
    # عیناً همان دسترسی‌ای که ربات دارد (`ctx.s.get("coins")`).
    # هر شکلِ دیگری این‌جا یعنی مینی‌اپ و ربات یک روز دو نردبانِ
    # متفاوت نشان می‌دهند.
    raw = st.get("coins")
    cs = core.coin_settings(raw)
    coins = int(u.get("coins") or 0)
    prog = core.coin_progress(coins, raw)

    bot = _bot_username(t)
    code = u.get("ref_code") or ""
    return {
        "enabled": bool(cs["enabled"]),
        "coins": coins,
        "percent": prog["current_percent"],
        "cost": prog["current_cost"],
        "next": prog["next"],
        "maxPercent": int(cs["max_percent"]),
        # کلِ نردبان، تا کاربر ببیند کجای راه است — نه فقط پله‌ی بعد
        "tiers": [{"coins": int(x["coins"]),
                   "percent": min(int(x["percent"]), int(cs["max_percent"]))}
                  for x in cs["tiers"]],
        "perReferral": int(cs["per_referral"]),
        "welcomeBonus": int(cs["welcome_bonus"]),
        "expireDays": int(cs["expire_days"]),
        "refCode": code,
        "refCount": _ref_count(t["id"], u["id"]),
        "botUsername": bot,
        "link": f"https://t.me/{bot}?start={code}" if bot and code else "",
    }


@app.get("/api/mini/subs")
def mini_subs(tu: tuple = Depends(mini_user)):
    """
    اشتراک‌های همین کاربر، با مصرف واقعی.

    مصرف از x-ui می‌آید؛ بدون آن کاربر نمی‌داند چقدر مانده و وقتی
    حجمش تمام شود فکر می‌کند سرویس خراب است.
    """
    t, u = tu
    con = _bot_conn()
    if not con:
        return {"subs": []}
    try:
        rows = [dict(r) for r in con.execute(
            "SELECT s.*, p.name AS plan_name FROM subscriptions s "
            "LEFT JOIN plans p ON p.id = s.plan_id "
            "WHERE s.tenant_id=? AND s.user_id=? ORDER BY s.id DESC",
            (t["id"], u["id"]))]
    except Exception:
        log.debug("خواندن اشتراک‌های مینی‌اپ ناموفق", exc_info=True)
        rows = []
    finally:
        con.close()

    clients, _k, _e = _read_xui_clients()
    by_email = {c.get("email"): c for c in (clients or [])}

    out = []
    for s in rows:
        cl = by_email.get(s.get("client_email")) or {}
        total = int(cl.get("totalGB") or 0)
        used = int(cl.get("used") or 0)
        left = None
        exp = (s.get("expires_at") or "")[:19]
        if exp:
            try:
                left = (datetime.fromisoformat(exp) - datetime.now()).days
            except ValueError:
                left = None
        out.append({
            "id": s.get("id"),
            "plan": s.get("plan_name") or "",
            "email": s.get("client_email") or "",
            "subUrl": s.get("sub_url") or "",
            "gb": _gb_of(total),
            "usedGB": round(used / (1024 ** 3), 1) if used else 0,
            "usagePct": _usage_percent(used, total),
            "expiryJalali": _to_jalali(_epoch_ms(exp))[0] if exp else None,
            "daysLeft": left,
            "active": bool(s.get("is_active")) and (left is None or left > 0),
            # صفحه‌ی جزئیات این‌ها را می‌خواهد. بایت خام می‌رود و
            # واحدش سمت مشتری انتخاب می‌شود: ۵۰ مگابایت نباید
            # «۰٫۰ گیگ» نوشته شود.
            "usedBytes": int(used or 0),
            "totalBytes": int(total or 0),
            "remainBytes": max(0, int(total or 0) - int(used or 0)) if total else None,
            "isTrial": bool(s.get("is_trial")),
            "months": int(s.get("months") or 0) or None,
        })
    return {"subs": out}


@app.get("/api/mini/plans")
def mini_plans(tu: tuple = Depends(mini_user)):
    """
    پلن‌های فروش — همان‌هایی که ربات نشان می‌دهد.

    قیمت از جدول `plans` می‌آید، همان جایی که ربات می‌خواند. این‌جا
    هیچ محاسبه‌ای انجام نمی‌شود؛ اگر می‌شد، همان باگِ «یک قاعده، دو
    جا» برمی‌گشت.
    """
    t, _u = tu
    con = _bot_conn()
    if not con:
        return {"plans": []}
    try:
        rows = [dict(r) for r in con.execute(
            "SELECT id, name, description, gb, days, ip_limit, price, is_trial "
            "FROM plans WHERE tenant_id=? AND is_active=1 "
            "ORDER BY sort_order, id", (t["id"],))]
    except Exception:
        log.debug("خواندن پلن‌های مینی‌اپ ناموفق", exc_info=True)
        rows = []
    finally:
        con.close()
    return {"plans": [{
        "id": r["id"], "name": r["name"], "desc": r.get("description") or "",
        "gb": r["gb"], "days": r["days"], "devices": r.get("ip_limit") or 0,
        "price": r["price"], "isTrial": bool(r.get("is_trial")),
    } for r in rows]}


def _mini_ctx(t):
    """
    زمینه‌ی ربات این مستاجر — برای خرید از داخل مینی‌اپ.

    همان چیزی که `_portal_bot_ctx` برای نماینده می‌سازد. بدون توکن
    ربات نمی‌شود کانفیگ ساخت و به مشتری داد.
    """
    h = _bot_handlers()
    row = _tenant_row(t["id"]) or t
    if not row.get("bot_token"):
        raise HTTPException(status_code=409,
                            detail="ربات این فروشگاه تنظیم نشده")
    return h, h.Ctx(h.Bot(row["bot_token"]), row)


@app.post("/api/mini/buy")
def mini_buy(payload: dict, tu: tuple = Depends(mini_user)):
    """
    خرید اشتراک از داخل مینی‌اپ، با کیف پول.

    **هیچ منطق پولی این‌جا نیست.** این تابع فقط ورودی را می‌سنجد و
    `handlers.wallet_purchase` را صدا می‌زند — همان هسته‌ای که خرید
    از داخل ربات هم از آن رد می‌شود.

    چرا این‌قدر صریح: این مسیرِ چهارمِ پول در این مخزن است. سه مسیر
    قبلی (کارت، کیف پول، تمدید خودکار) هر کدام یک‌بار یک قاعده را
    فراموش کردند و سه بار جدا پیدا شدند — یکی `approved` را پیش از
    ساخت کانفیگ می‌نوشت، یکی بعدش هیچ‌وقت نمی‌نوشت، و یکی پاداشِ
    معرف را نمی‌داد. اگر این‌جا دوباره نوشته شود، چهارمی هم همان
    راه را می‌رود.
    """
    t, u = tu
    pid = (payload or {}).get("planId")
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="پلن انتخاب نشده")

    # پلن باید مالِ همین مستاجر و فعال باشد. بدون این شرط، فرستادنِ
    # شناسه‌ی پلنِ نماینده‌ی دیگر کافی است تا با قیمتِ او خرید شود.
    con = _bot_conn()
    if not con:
        raise HTTPException(status_code=503, detail="دیتابیس ربات در دسترس نیست")
    try:
        pl = con.execute(
            "SELECT id, name, price, is_trial FROM plans "
            "WHERE id=? AND tenant_id=? AND is_active=1", (pid, t["id"])).fetchone()
    finally:
        con.close()
    if not pl:
        raise HTTPException(status_code=404, detail="این پلن دیگر در دسترس نیست")

    # تستِ رایگان مسیر خودش را دارد (یک‌بار برای هر کاربر، با پرچمِ
    # `trial_used`). از این‌جا که بیاید، آن قاعده دور زده می‌شود.
    if pl["is_trial"]:
        raise HTTPException(
            status_code=409,
            detail="تست رایگان از خودِ ربات گرفته می‌شود")

    h, ctx = _mini_ctx(t)
    try:
        r = h.wallet_purchase(ctx, u, pid)
    except Exception as e:
        log.exception("خرید مینی‌اپ ناموفق")
        raise HTTPException(status_code=502, detail=f"خرید ناموفق: {str(e)[:140]}")

    if r.get("ok"):
        return {"ok": True, "spent": int(r["spent"]), "left": int(r["left"]),
                "plan": pl["name"]}

    why = r.get("why")
    if why == "low_balance":
        raise HTTPException(
            status_code=402,
            detail=f"موجودی کافی نیست — {int(r['short']):,} تومان کم دارید")
    if why == "race":
        raise HTTPException(
            status_code=409,
            detail="موجودی همین حالا تغییر کرد — دوباره امتحان کنید")
    if why == "provision":
        raise HTTPException(
            status_code=502,
            detail="ساخت اشتراک نشد و مبلغ کامل به کیف پولتان برگشت")
    raise HTTPException(status_code=404, detail="این پلن دیگر در دسترس نیست")


def _mini_plan(t, payload):
    """پلنِ همین مستاجر، فعال، و غیرِ تست — یا خطا."""
    pid = (payload or {}).get("planId")
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="پلن انتخاب نشده")
    con = _bot_conn()
    if not con:
        raise HTTPException(status_code=503, detail="دیتابیس ربات در دسترس نیست")
    try:
        pl = con.execute(
            "SELECT id, name, price, gb, days, is_trial FROM plans "
            "WHERE id=? AND tenant_id=? AND is_active=1",
            (pid, t["id"])).fetchone()
    finally:
        con.close()
    if not pl:
        raise HTTPException(status_code=404, detail="این پلن دیگر در دسترس نیست")
    if pl["is_trial"]:
        # تست یک‌بار برای هر کاربر است و پرچمِ `trial_used` دارد.
        # از این مسیر که بیاید، آن قاعده دور زده می‌شود.
        raise HTTPException(status_code=409,
                            detail="تست رایگان از خودِ ربات گرفته می‌شود")
    return dict(pl)


@app.get("/api/mini/inbox")
def mini_inbox(tu: tuple = Depends(mini_user)):
    """گفتگوی همین مشتری، و شمارِ نخوانده‌ها."""
    t, u = tu
    try:
        db = _bot_db_rw(t)
        rows = db.chat_list(u["id"])
        unread = db.chat_unread_for_user(u["id"])
    except Exception as e:
        log.exception("خواندن صندوق مینی‌اپ ناموفق")
        raise HTTPException(status_code=503, detail=f"صندوق خوانده نشد: {str(e)[:120]}")
    return {
        "unread": unread,
        "messages": [{
            "id": r["id"], "from": r["sender"], "body": r["body"],
            "photo": _row_get(r, "photo") or "",
            "orderId": r["order_id"], "at": r["created_at"],
            "read": bool(r["read_at"]),
        } for r in rows],
    }


@app.get("/api/mini/ping")
def mini_ping(tu: tuple = Depends(mini_user)):
    """
    فقط شمارنده‌ها — سبک، برای پرسیدنِ مکرر.

    مینی‌اپ هر بیست ثانیه همین را می‌پرسد و وقتی عددی عوض شد،
    داده‌ی کامل را می‌گیرد. بدون این، کاربر باید خودش تازه‌سازی کند
    و تا وقتی نکند، تاییدِ رسیدش را نمی‌بیند.
    """
    t, u = tu
    con = _bot_conn()
    if not con:
        return {"unread": 0, "openOrders": 0, "subs": 0}
    try:
        unread = con.execute(
            "SELECT COUNT(*) n FROM chat_messages WHERE tenant_id=? AND user_id=? "
            "AND sender<>'user' AND read_at IS NULL",
            (t["id"], u["id"])).fetchone()["n"]
        opened = con.execute(
            "SELECT COUNT(*) n FROM orders WHERE tenant_id=? AND user_id=? "
            "AND status IN ('pending','awaiting')",
            (t["id"], u["id"])).fetchone()["n"]
        subs = con.execute(
            "SELECT COUNT(*) n FROM subscriptions WHERE tenant_id=? AND user_id=?",
            (t["id"], u["id"])).fetchone()["n"]
    except Exception:
        log.debug("پینگ مینی‌اپ ناموفق", exc_info=True)
        return {"unread": 0, "openOrders": 0, "subs": 0}
    finally:
        con.close()
    return {"unread": int(unread or 0), "openOrders": int(opened or 0),
            "subs": int(subs or 0)}


@app.post("/api/mini/topup")
def mini_topup(payload: dict, tu: tuple = Depends(mini_user)):
    """
    شارژ کیف پول از داخل مینی‌اپ.

    **هیچ منطقی این‌جا نیست** — `handlers.topup_order` همان هسته‌ای
    است که ربات هم از آن رد می‌شود. اگر این‌جا دوباره نوشته شود،
    می‌شود مسیرِ دومی که یک روز کمینه‌ی مبلغ یا انتخابِ کارت را
    فراموش می‌کند.

    رسیدش از همان `/api/mini/order/{oid}/receipt` می‌رود؛ سفارشِ
    شارژ و سفارشِ خرید هر دو یک شکل‌اند.
    """
    t, u = tu
    h, ctx = _mini_ctx(t)
    try:
        order, card = h.topup_order(ctx, u, (payload or {}).get("amount"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        log.exception("ساخت سفارش شارژ ناموفق")
        raise HTTPException(status_code=502, detail=f"ثبت نشد: {str(e)[:120]}")

    st = {}
    try:
        st = json.loads(t.get("settings") or "{}")
    except (json.JSONDecodeError, TypeError):
        st = {}

    return {
        "orderId": int(order["id"]),
        "amount": int(order["amount"]),
        "card": {"number": str(card.get("number") or ""),
                 "holder": str(card.get("holder") or "")},
        "ttlMinutes": int(st.get("order_ttl_minutes") or 0),
    }


@app.post("/api/mini/profile")
def mini_profile_save(payload: dict, tu: tuple = Depends(mini_user)):
    """
    نام و شماره‌ی خودِ مشتری.

    چرا مشتری خودش بنویسد: `first_name` از تلگرام می‌آید و ممکن است
    «😎» باشد یا اصلاً نباشد؛ و شماره را ربات فقط وقتی می‌گیرد که
    کاربر دکمه‌اش را بزند. بدون این دو، پشتیبانی نمی‌داند با که حرف
    می‌زند.
    """
    t, u = tu
    p = payload or {}
    name = str(p.get("name") or "").strip()[:60]
    phone = str(p.get("phone") or "").strip()[:24]

    # شماره اگر آمد باید شبیه شماره باشد — وگرنه ستونی پر می‌شود که
    # بعداً هیچ‌کس نمی‌تواند رویش حساب کند
    if phone and not _re.fullmatch(r"[0-9+\-\s()]{6,24}", phone):
        raise HTTPException(status_code=400, detail="شماره معتبر نیست")

    con = _bot_rw()
    try:
        con.execute(
            "UPDATE users SET first_name=COALESCE(NULLIF(?,''), first_name), "
            "phone=COALESCE(NULLIF(?,''), phone) WHERE tenant_id=? AND id=?",
            (name, phone, t["id"], u["id"]))
        con.commit()
    except Exception as e:
        log.exception("ذخیره‌ی پروفایل ناموفق")
        raise HTTPException(status_code=502, detail=f"ذخیره نشد: {str(e)[:120]}")
    finally:
        con.close()
    return {"ok": True, "name": name or u.get("first_name") or "",
            "phone": phone or u.get("phone") or ""}


@app.post("/api/mini/profile/avatar")
def mini_avatar_set(payload: dict, tu: tuple = Depends(mini_user)):
    """عکسِ پروفایلِ خودِ مشتری."""
    t, u = tu
    return {"ok": True, "avatar": _avatar_save(t["id"], u["id"],
                                               (payload or {}).get("data"))}


@app.delete("/api/mini/profile/avatar")
def mini_avatar_clear(tu: tuple = Depends(mini_user)):
    t, u = tu
    _avatar_clear(t["id"], u["id"])
    return {"ok": True, "avatar": ""}


@app.post("/api/mini/inbox/send")
def mini_inbox_send(payload: dict, tu: tuple = Depends(mini_user)):
    """پیام مشتری به پشتیبانی."""
    t, u = tu
    p = payload or {}
    body = str(p.get("body") or "").strip()
    raw = p.get("photo")
    if not body and not raw:
        raise HTTPException(status_code=400, detail="پیام خالی است")
    if len(body) > 2000:
        raise HTTPException(status_code=400, detail="پیام خیلی بلند است")

    # اول فایل، بعد ردیف — وگرنه پیامی می‌ماند که به عکسِ ناموجود
    # اشاره می‌کند
    photo = _chat_photo_save(t["id"], u["id"], raw) if raw else None
    try:
        db = _bot_db_rw(t)
        db.chat_add(u["id"], "user", body, photo=photo)
    except Exception as e:
        log.exception("ثبت پیام مینی‌اپ ناموفق")
        raise HTTPException(status_code=502, detail=f"فرستاده نشد: {str(e)[:120]}")

    # مالک باید بفهمد — وگرنه پیام می‌ماند تا کسی اتفاقی پنل را باز کند
    try:
        h, ctx = _mini_ctx(t)
        who = u.get("first_name") or str(u.get("tg_id") or "")
        head = f"💬 <b>پیام تازه از {h.esc(who)}</b>"
        cap = f"{head}\n\n{h.esc(body[:400])}" if body else f"{head}\n\n📷 عکس"
        blob = _chat_photo_bytes(photo) if photo else None
        if blob:
            # عکس را خودِ گروه ببیند؛ «عکس فرستاد» بدونِ عکس یعنی
            # مالک باید پنل را باز کند تا بفهمد موضوع چیست
            ctx.notify_group(cap, topic="tickets", photo=blob)
        else:
            ctx.notify_group(cap, topic="tickets")
    except Exception:
        log.debug("اعلان پیام به گروه ناموفق", exc_info=True)

    return {"ok": True, "photo": photo or ""}


@app.post("/api/mini/inbox/read")
def mini_inbox_read(tu: tuple = Depends(mini_user)):
    """مشتری صندوقش را باز کرد."""
    t, u = tu
    try:
        _bot_db_rw(t).chat_mark_read(u["id"], "user")
    except Exception:
        log.debug("علامت خواندن ناموفق", exc_info=True)
    return {"ok": True}


@app.post("/api/mini/order")
def mini_order(payload: dict, tu: tuple = Depends(mini_user)):
    """
    سفارشِ کارت‌به‌کارت از داخل مینی‌اپ.

    **هیچ منطقی این‌جا نیست**: `handlers.card_order` صدا زده می‌شود،
    همان هسته‌ای که سفارشِ کارتیِ ربات هم از آن رد می‌شود — قیمت با
    تخفیفِ سکه، رزروِ سکه، مهلتِ قابل‌تنظیم، و انتخابِ کارت.

    نسخه‌ی اول این را دوباره نوشته بود و دو چیز را جا انداخت: تخفیفِ
    سکه و `order_ttl_minutes`. یعنی مشتری‌ای که سکه داشت از مینی‌اپ
    قیمتِ کامل می‌داد. تست همین را گرفت.
    """
    t, u = tu
    pl = _mini_plan(t, payload)
    h, ctx = _mini_ctx(t)

    try:
        ok, r = h.card_order(ctx, u, pl["id"],
                             use_coins=bool((payload or {}).get("useCoins")))
    except Exception as e:
        log.exception("ساخت سفارش مینی‌اپ ناموفق")
        raise HTTPException(status_code=502, detail=f"ساخت سفارش نشد: {str(e)[:140]}")

    if not ok:
        if r == "no_card":
            raise HTTPException(
                status_code=409,
                detail="کارتی برای واریز تنظیم نشده — به پشتیبانی پیام بدهید")
        if r == "no_plan":
            raise HTTPException(status_code=404, detail="این پلن دیگر در دسترس نیست")
        raise HTTPException(
            status_code=409,
            detail=f"سکه کافی نیست — {int(r.get('need') or 0)} سکه لازم است")

    o, card, pr = r["order"], r["card"], r["price"]
    return {
        "ok": True,
        "orderId": o["id"],
        "amount": int(o["amount"] or 0),
        "basePrice": int(o["base_amount"] or 0),
        "coinsUsed": int(o["coins_used"] or 0),
        "discountPct": int(pr.get("coin_discount") or 0),
        "expiresAt": o.get("expires_at") or "",
        "ttlMinutes": int(r["ttl"]),
        "card": {"number": card.get("number") or "",
                 "holder": card.get("holder") or card.get("name") or "",
                 "bank": card.get("bank") or ""},
        "plan": r["plan"]["name"],
    }


@app.post("/api/mini/order/{oid}/receipt")
def mini_receipt(oid: int, payload: dict, tu: tuple = Depends(mini_user)):
    """
    رسیدِ یک سفارشِ کارتی — عکس یا متنِ پیامک بانک.

    **هیچ منطقی این‌جا نیست**: `handlers.receipt_submit` صدا زده
    می‌شود، همان هسته‌ای که رسیدِ داخلِ ربات هم از آن رد می‌شود —
    همان قاعده‌ی مهلت، همان ادعای اتمی، همان اعلان با دکمه‌های تایید
    و رد. دو مسیرِ رسید یعنی روزی یکی‌شان اعلان را جا می‌اندازد و
    مشتری پول داده بدون اینکه کسی خبر داشته باشد.

    عکس همین‌جا به گروه مدیریت آپلود می‌شود و `file_id`ش ذخیره —
    پس پنل و پنل نماینده بدون هیچ تغییری همان رسید را نشان می‌دهند.
    """
    t, u = tu
    o = _mini_own_order(t, u, oid)
    if o["status"] != "pending":
        raise HTTPException(status_code=409,
                            detail="این سفارش دیگر منتظر رسید نیست")

    p = payload or {}
    text = str(p.get("text") or "").strip()[:2000]
    blob = None
    raw = str(p.get("data") or "")
    if raw:
        import base64
        if raw.lstrip().startswith("data:") and "," in raw[:80]:
            raw = raw.split(",", 1)[1]
        raw = raw.strip()
        if len(raw) > (RECEIPT_MAX_BYTES * 4) // 3 + 1024:
            raise HTTPException(status_code=413,
                                detail="حجم تصویر بیشتر از ۳ مگابایت است")
        try:
            blob = base64.b64decode(raw, validate=True)
        except Exception:
            raise HTTPException(status_code=400, detail="تصویر خوانده نشد")
        if len(blob) > RECEIPT_MAX_BYTES:
            raise HTTPException(status_code=413,
                                detail="حجم تصویر بیشتر از ۳ مگابایت است")
        if not _logo_kind(blob)[0]:
            raise HTTPException(status_code=400,
                                detail="فقط تصویر PNG، JPEG یا WebP")

    if not blob and not text:
        raise HTTPException(status_code=400,
                            detail="عکس رسید یا متن پیامک بانک را بفرستید")

    # **اول روی دیسک.**
    #
    # اگر این کار به تلگرام سپرده شود و گروه مدیریت تنظیم نشده باشد،
    # `receipt_file` خالی می‌ماند و عکس برای همیشه گم می‌شود — مشتری
    # پول داده و مدرکش نیست. تلگرام فقط راهِ دیدنِ سریع در گروه است.
    local_ref = _receipt_save(oid, blob) if blob else None

    h, ctx = _mini_ctx(t)
    try:
        ok, why = h.receipt_submit(
            ctx, u, oid,
            "photo" if blob else "text",
            rfile=local_ref,
            rtext=text or None, photo_bytes=blob)
    except Exception as e:
        log.exception("ثبت رسید مینی‌اپ ناموفق")
        raise HTTPException(status_code=502, detail=f"ثبت نشد: {str(e)[:140]}")

    if ok:
        return {"ok": True, "status": "awaiting"}
    if why == "expired" or why == "race":
        raise HTTPException(
            status_code=410,
            detail="مهلت این سفارش تمام شد — اگر واریز کرده‌اید به پشتیبانی "
                   "پیام بدهید")
    raise HTTPException(status_code=409, detail="این سفارش دیگر باز نیست")


def _mini_own_order(t, u, oid):
    """سفارشی که مالِ همین کاربرِ همین مستاجر است — یا ۴۰۴."""
    con = _bot_conn()
    if not con:
        raise HTTPException(status_code=503, detail="دیتابیس ربات در دسترس نیست")
    try:
        r = con.execute(
            "SELECT * FROM orders WHERE id=? AND tenant_id=? AND user_id=?",
            (int(oid), t["id"], u["id"])).fetchone()
    finally:
        con.close()
    if not r:
        # همان «پیدا نشد» برای سفارشِ کسِ دیگر: وگرنه می‌شود فهمید چه
        # شناسه‌هایی وجود دارند.
        raise HTTPException(status_code=404, detail="سفارش پیدا نشد")
    return dict(r)


@app.get("/api/mini/orders")
def mini_orders(tu: tuple = Depends(mini_user)):
    """
    سفارش‌های خودِ کاربر — تا بداند رسیدش به کجا رسید.

    بدون این، مشتری رسید می‌فرستد و بعد هیچ نمی‌بیند؛ همان مسیرِ
    خرابِ بی‌صدا.
    """
    t, u = tu
    con = _bot_conn()
    if not con:
        return {"orders": []}
    try:
        rows = [dict(r) for r in con.execute(
            """SELECT o.id, o.status, o.amount, o.created_at, o.expires_at,
                      o.paid_from, o.admin_note, p.name AS plan_name
                 FROM orders o
            LEFT JOIN plans p ON p.id = o.plan_id
                WHERE o.tenant_id=? AND o.user_id=?
             ORDER BY o.id DESC LIMIT 20""", (t["id"], u["id"]))]
    except Exception:
        log.debug("خواندن سفارش‌های مینی‌اپ ناموفق", exc_info=True)
        rows = []
    finally:
        con.close()
    return {"orders": [{
        "id": r["id"], "status": r["status"],
        "amount": int(r["amount"] or 0),
        "plan": r.get("plan_name") or "",
        "paidFrom": r.get("paid_from") or "",
        "createdAt": r.get("created_at") or "",
        "expiresAt": r.get("expires_at") or "",
        "note": r.get("admin_note") or "",
    } for r in rows]}


@app.post("/api/admin/tenant/{tid}/logo")
def tenant_logo_set(tid: int, payload: dict, x_admin_password: str = Header(...)):
    """
    لوگوی یک مستاجر — مالک برای خودش یا برای هر نماینده.

    مستاجر باید وجود داشته باشد، وگرنه فایل‌هایی روی دیسک می‌مانند که
    هیچ‌کس صاحبشان نیست.
    """
    check_auth(x_admin_password)
    if not _tenant_row(tid):
        raise HTTPException(status_code=404, detail="این مستاجر پیدا نشد")
    return _logo_save(tid, payload)


@app.delete("/api/admin/tenant/{tid}/logo")
def tenant_logo_clear(tid: int, x_admin_password: str = Header(...)):
    """برداشتن لوگو — بعدش نشان نکسورا برمی‌گردد، نه قابِ خالی."""
    check_auth(x_admin_password)
    _logo_clear(tid)
    return {"ok": True}


@app.post("/api/admin/tenant/{tid}/credit")
def tenant_credit(tid: int, payload: dict, x_admin_password: str = Header(...)):
    """
    شارژ یا اصلاح اعتبار یک نماینده.

    amount مثبت یعنی شارژ، منفی یعنی برداشت. unlimited=true یعنی
    نماینده بدون سقف کار کند و آخر ماه صورتحساب بگیرد.

    هر تغییری در دفتر ثبت می‌شود — عددِ credit به‌تنهایی تاریخچه
    ندارد و با هر ساخت و تمدید عوض می‌شود.
    """
    check_auth(x_admin_password)
    p = payload or {}
    note = str(p.get("note") or "").strip()[:200]

    con = _bot_rw()
    try:
        row = con.execute(
            "SELECT name, credit, portal_group FROM tenants WHERE id=?",
            (tid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="نماینده پیدا نشد")
        group_key = (row["portal_group"] or "").strip()

        if p.get("unlimited"):
            con.execute("UPDATE tenants SET credit=-1 WHERE id=?", (tid,))
            _credit_log(con, tid, 0, -1, note or "بدون سقف — صورتحساب ماهانه")
            con.commit()
            return {"ok": True, "credit": -1, "mode": "بدهکاری"}

        try:
            amount = int(p.get("amount"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="مبلغ نامعتبر است")
        if amount == 0:
            raise HTTPException(status_code=400, detail="مبلغ صفر است")

        cur_credit = int(row["credit"] or 0)
        if cur_credit < 0:
            # از بدهکاری به پیش‌پرداخت: از صفر شروع می‌شود، نه از -۱
            base = 0
        else:
            base = cur_credit
        new = base + amount
        if new < 0:
            raise HTTPException(
                status_code=400,
                detail=f"اعتبار منفی می‌شود — موجودی فعلی {base:,} تومان")

        con.execute("UPDATE tenants SET credit=? WHERE id=?", (new, tid))
        _credit_log(con, tid, amount, new,
                    note or ("شارژ از پنل" if amount > 0 else "برداشت از پنل"))
        con.commit()
    finally:
        con.close()

    # بعد از commit، و در دیتابیسِ دیگری: اگر این یکی بیفتد، اعتبار
    # درست مانده و فقط ثبتِ حسابداری جا افتاده — که قابل جبران است.
    # ترتیب برعکس یعنی پرداختی ثبت شود که اعتباری پشتش نیست.
    _record_topup(group_key, amount,
                  ("شارژ اعتبار — " + (note or "پنل نمایندگی"))[:200])
    if not group_key:
        log.warning("نماینده %s گروه ندارد — شارژ در حسابداری ثبت نشد", tid)

    log.info("اعتبار نماینده %s تغییر کرد: %s → %s", tid, base, new)
    return {"ok": True, "credit": new, "mode": "پیش‌پرداخت",
            "recorded": bool(group_key)}


def _record_topup(group_key, amount, note):
    """
    شارژ اعتبار نماینده را به‌عنوان پرداخت ثبت می‌کند.

    چرا لازم است:
        دو سیستم پول موازی وجود داشت و با هم حرف نمی‌زدند. نماینده‌ی
        بدهکاری آخر ماه پرداخت می‌کند و در جدول `payments` ثبت
        می‌شود. نماینده‌ی پیش‌پرداخت *جلوتر* پول می‌دهد و آن پول فقط
        در `credit_tx` می‌نشست — که هیچ صفحه‌ی حسابداری‌ای نمی‌خواندش.

        نتیجه‌اش دو چیز بود:

          • پولی که واقعاً گرفته شده در «دریافت‌شده» و «سود واقعی تا
            امروز» اصلاً نمی‌آمد
          • و نماینده‌ای که از قبل پولش را داده بود، روی داشبورد
            بدهکار نشان داده می‌شد

        شارژ، لحظه‌ی واقعیِ رسیدن پول است — پس همان‌جا ثبت می‌شود.
        مصرفِ بعدیِ اعتبار پول تازه‌ای نیست و ثبت نمی‌شود.
    """
    if not group_key or not amount:
        return
    try:
        con = _billing_conn()
    except Exception:
        log.warning("ثبت شارژ در پرداخت‌ها ناموفق — دیتابیس باز نشد")
        return
    try:
        con.execute(
            "INSERT INTO payments (group_key,amount,paid_at,note) "
            "VALUES (?,?,?,?)",
            (group_key, int(amount), datetime.now().strftime("%Y-%m-%d"),
             note))
        con.commit()
    except Exception:
        log.warning("ثبت شارژ در پرداخت‌ها ناموفق", exc_info=True)
    finally:
        con.close()


@app.get("/api/admin/tenant/{tid}/credit-log")
def tenant_credit_log(tid: int, limit: int = 40,
                      x_admin_password: str = Header(...)):
    """تاریخچه‌ی اعتبار یک نماینده — شارژها و برداشت‌ها."""
    check_auth(x_admin_password)
    con = _bot_conn()
    if not con:
        return {"ready": False, "rows": []}
    try:
        rows = [dict(r) for r in con.execute(
            "SELECT amount, balance, note, created_at FROM credit_tx "
            "WHERE tenant_id=? ORDER BY id DESC LIMIT ?",
            (tid, max(1, min(int(limit or 40), 200))))]
        return {"ready": True, "rows": rows}
    except Exception as e:
        return {"ready": False, "error": str(e)[:120], "rows": []}
    finally:
        con.close()


@app.post("/api/admin/tenant")
def tenant_create(payload: dict, x_admin_password: str = Header(...)):
    """
    ساخت یک نماینده‌ی تازه.

    تا امروز هیچ راهی برایش نبود. صفحه‌ی پنل نمایندگی می‌گفت «از بخش
    ربات، مستاجر بسازید» ولی چنین جایی وجود نداشت — `create_tenant` در
    کل مخزن فقط از تست‌ها صدا زده می‌شد. یعنی مالک عملاً به همان یک
    مستاجرِ ریشه محدود بود.

    نکته‌های عمدی:

      • مستاجر تازه همیشه فرزندِ ریشه است. بدون `parent_id`، در
        حسابداری «مالک» شمرده می‌شود و درآمد و بدهی‌اش با مالِ شما
        قاطی می‌شود — همان قاعده‌ای که دفتر کل و صفحه‌ی همکاری اجرا
        می‌کنند.

      • پنلش **بسته** ساخته می‌شود. تا گروه و رمز ثبت نشده، بازکردنش
        فقط یک صفحه‌ی ورود می‌دهد که هیچ‌وقت چیزی نشان نمی‌دهد.

      • اتصال x-ui از ریشه به ارث می‌رسد و کپی نمی‌شود؛ نماینده رمز
        پنل شما را نه می‌بیند و نه لازم دارد.
    """
    check_auth(x_admin_password)
    p = payload or {}

    name = str(p.get("name") or "").strip()[:60]
    if not name:
        raise HTTPException(status_code=400, detail="نام نماینده لازم است")

    slug = "".join(ch for ch in str(p.get("slug") or "").strip().lower()
                   if ch.isalnum() or ch in "-_")[:32]
    if not slug:
        raise HTTPException(status_code=400, detail="نشانی لینک لازم است")

    pw = str(p.get("password") or "")
    if len(pw) < 8:
        raise HTTPException(status_code=400,
                            detail="رمز باید دست‌کم ۸ نویسه باشد")

    group = str(p.get("group") or "").strip()[:80]

    # credit منفی یعنی بدون سقف — آخر ماه صورتحساب می‌گیرد.
    try:
        credit = int(p.get("credit"))
    except (TypeError, ValueError):
        credit = -1

    con = _bot_rw()
    try:
        taken = con.execute("SELECT id FROM tenants WHERE portal_slug=?",
                            (slug,)).fetchone()
        if taken:
            raise HTTPException(
                status_code=400, detail="این نشانی برای نماینده‌ی دیگری ثبت شده")

        root = con.execute("SELECT id FROM tenants WHERE parent_id IS NULL "
                           "ORDER BY id LIMIT 1").fetchone()
        if not root:
            raise HTTPException(status_code=400,
                                detail="مستاجر ریشه پیدا نشد — اول پنل را راه بیندازید")

        cur = con.execute(
            """INSERT INTO tenants (name, parent_id, credit, portal_slug,
                                    portal_pass, portal_group, portal_enabled,
                                    inbound_mode, is_active)
               VALUES (?,?,?,?,?,?,0,'all',1)""",
            (name, int(root["id"]), credit, slug, pw, group))
        con.commit()
        tid = cur.lastrowid
        log.info("نماینده‌ی تازه ساخته شد: %s (#%s)", name, tid)
        return {"ok": True, "id": tid, "name": name, "slug": slug,
                "enabled": False,
                "next": "گروه x-ui را انتخاب کنید و بعد پنلش را باز کنید"}
    finally:
        con.close()


@app.get("/api/admin/tenant/portal-list")
def tenant_portal_list(x_admin_password: str = Header(...)):
    """
    نماینده‌ها و وضعیت پنلشان، به‌همراه گروه‌های واقعی x-ui.

    گروه‌ها را هم می‌دهیم تا مدیر از فهرست انتخاب کند نه اینکه نام را
    دستی بنویسد — یک فاصله یا حرف بزرگ و کوچکِ متفاوت یعنی نماینده
    هیچ کانفیگی نمی‌بیند و دلیلش هم معلوم نیست.
    """
    check_auth(x_admin_password)
    out = []
    con = _bot_conn()
    try:
        if con:
            cols = {r[1] for r in con.execute("PRAGMA table_info(tenants)")}
            pick = ["id", "name"]
            for c in ("portal_slug", "portal_group", "portal_enabled",
                      "portal_pass", "credit", "is_active"):
                if c in cols:
                    pick.append(c)
            # فقط نماینده‌ها، نه خودِ مالک.
            #
            #  بدون این شرط، مستاجرِ ریشه هم در فهرست می‌آمد: با فرم
            #  «نشانی لینک»، «گروه x-ui»، دکمه‌ی «بازکردن پنل» و
            #  حتی هشدارِ «برای اینکه بتواند وارد شود…» — برای خودِ
            #  صاحب پنل. و بدتر، می‌شد ناخواسته برایش پنل نمایندگی
            #  باز کرد.
            for r in con.execute(
                    f"SELECT {','.join(pick)} FROM tenants "
                    "WHERE parent_id IS NOT NULL ORDER BY id"):
                d = dict(r)
                out.append({
                    "id": d["id"], "name": d.get("name") or "",
                    "portalSlug": d.get("portal_slug") or "",
                    "portalGroup": d.get("portal_group") or "",
                    "portalEnabled": _portal_open(d.get("portal_enabled")),
                    # خودِ رمز هرگز برنمی‌گردد — فقط اینکه هست یا نه،
                    # تا پنل بتواند بگوید چه چیزی مانده.
                    "hasPass": bool(d.get("portal_pass")),
                    "credit": d.get("credit"),
                    "active": bool(d.get("is_active", 1)),
                    # خالی یعنی «هنوز لوگو نگذاشته» — رابط خودش نشانِ
                    # نکسورا را می‌گذارد
                    "logo": _logo_url(d["id"]),
                })
    except Exception as e:
        return {"ready": False, "error": str(e)[:140], "tenants": [],
                "groups": []}
    finally:
        if con:
            con.close()

    # خطای خواندنِ گروه‌ها دور ریخته می‌شد و فهرست بی‌صدا خالی
    # می‌ماند. نتیجه‌اش این بود که وقتی x-ui در دسترس نبود، *همه‌ی*
    # نماینده‌ها بدون گروه به نظر می‌رسیدند — بدون هیچ توضیحی.
    groups, groups_error = [], ""
    try:
        clients, known, err = _read_xui_clients()
        if clients is None and err:
            groups_error = str(err)[:140]
        seen = {c.get("group") for c in (clients or []) if c.get("group")}
        groups = sorted(seen | set(known or []))
    except Exception as e:
        groups_error = f"{type(e).__name__}: {str(e)[:120]}"

    return {"ready": True, "tenants": out, "groups": groups,
            "groupsError": groups_error}


@app.post("/api/admin/tenant/{tid}/portal")
def tenant_portal_set(tid: int, payload: dict,
                      x_admin_password: str = Header(...)):
    """
    تنظیم دسترسی پنل یک نماینده — از سمت مدیر.

    نشانی یکتاست چون آدرس است؛ تکراری بودنش یعنی دو نماینده به یک
    لینک می‌رسند.
    """
    check_auth(x_admin_password)
    p = payload or {}
    sets, vals = [], []

    if "slug" in p:
        clean = "".join(ch for ch in str(p.get("slug") or "").strip().lower()
                        if ch.isalnum() or ch in "-_")[:32]
        if not clean:
            raise HTTPException(status_code=400, detail="نشانی لینک نامعتبر است")
        con = _bot_conn()
        taken = None
        if con:
            try:
                taken = con.execute(
                    "SELECT id FROM tenants WHERE portal_slug=? AND id<>?",
                    (clean, tid)).fetchone()
            finally:
                con.close()
        if taken:
            raise HTTPException(
                status_code=400, detail="این نشانی برای نماینده‌ی دیگری ثبت شده")
        sets.append("portal_slug=?")
        vals.append(clean)

    if "group" in p:
        # گروه بی‌صدا دور ریخته می‌شد: پنل می‌فرستادش و این مسیر
        # نمی‌خواندش. نماینده وارد می‌شد و هیچ کانفیگی نمی‌دید.
        sets.append("portal_group=?")
        vals.append(str(p.get("group") or "").strip())

    if p.get("password"):
        pw = str(p["password"])
        if len(pw) < 8:
            raise HTTPException(status_code=400,
                                detail="رمز باید دست‌کم ۸ نویسه باشد")
        sets.append("portal_pass=?")
        vals.append(pw)

    if "enabled" in p:
        sets.append("portal_enabled=?")
        vals.append(1 if p["enabled"] else 0)
        if not p["enabled"]:
            # بستن باید همان لحظه اثر کند، نه سر انقضای نشست.
            for k in [k for k, v in _PORTAL_SESSIONS.items() if v[0] == tid]:
                _PORTAL_SESSIONS.pop(k, None)

    if not sets:
        raise HTTPException(status_code=400, detail="چیزی برای تغییر نیست")

    con = _bot_rw()
    try:
        # آیا از قبل رمز داشت؟ تصمیمِ «خودش باز شود» به همین بند است.
        try:
            _prev = con.execute("SELECT portal_pass FROM tenants WHERE id=?",
                                (tid,)).fetchone()
            had_pass = bool(_prev and _prev["portal_pass"])
        except Exception:
            had_pass = False

        cols = {r[1] for r in con.execute("PRAGMA table_info(tenants)")}
        # نوعِ هر ستون مهم است.
        #
        # اگر portal_enabled را TEXT بسازیم، عدد ۱ به رشته‌ی '1'
        # تبدیل می‌شود و در SQLite مقایسه‌ی '1' = 1 هیچ‌وقت درست
        # نیست — یعنی هیچ نماینده‌ای نمی‌تواند وارد شود، بی‌آنکه
        # هیچ خطایی جایی ثبت شود.
        for col, typ in (("portal_slug", "TEXT"), ("portal_pass", "TEXT"),
                         ("portal_group", "TEXT"),
                         ("portal_enabled", "INTEGER DEFAULT 0")):
            if col not in cols:
                con.execute(f"ALTER TABLE tenants ADD COLUMN {col} {typ}")
        vals.append(tid)
        cur = con.execute(
            f"UPDATE tenants SET {', '.join(sets)} WHERE id=?", vals)
        if not cur.rowcount:
            raise HTTPException(status_code=404, detail="نماینده پیدا نشد")

        # تنظیم‌کردن یعنی باز کردن.
        #
        # قبلاً نبود و هیچ‌کدام از دکمه‌های پنل enabled نمی‌فرستادند،
        # پس portal_enabled صفر می‌ماند. ورودِ نماینده آن‌وقت «نشانی
        # یا رمز نادرست است» می‌گرفت — که از رمز غلط قابل تشخیص
        # نیست. مدیر رمز را درست زده بود و پنل می‌گفت غلط است.
        #
        # فقط وقتی که مدیر صریحاً enabled نفرستاده باشد، و ردیف
        # حالا هر سه چیزِ لازم را داشته باشد. بستنِ صریح دست‌نخورده
        # می‌ماند.
        opened = False
        if "enabled" not in p and p.get("password") and not had_pass:
            # فقط همان *بار اولی* که رمز ساخته می‌شود.
            #
            # «هر بار که تنظیم شد باز کن» ساده‌تر بود ولی غلط: مدیری
            # که نماینده‌ای را عمداً بسته، با ویرایش بعدیِ نشانی‌اش
            # دوباره بازش می‌کرد — یعنی بستن هیچ معنایی نداشت.
            row = con.execute(
                "SELECT portal_slug, portal_group FROM tenants WHERE id=?",
                (tid,)).fetchone()
            if row and row["portal_slug"] and row["portal_group"]:
                con.execute("UPDATE tenants SET portal_enabled=1 WHERE id=?",
                            (tid,))
                opened = True
        con.commit()
    finally:
        con.close()
    return {"ok": True, "opened": opened}


def _days_left(expiry):
    """
    چند روز تا انقضا. None یعنی بی‌پایان، منفی یعنی گذشته.

    x-ui برای کلاینتی که هنوز وصل نشده عدد منفی نگه می‌دارد (یعنی
    «از اولین اتصال شروع شود») — آن هم بی‌پایان حساب می‌شود، نه
    منقضی‌شده‌ی خیلی قدیمی.
    """
    ms = _epoch_ms(expiry)
    if not ms or ms <= 0:
        return None
    return int((ms - _epoch_ms(datetime.now())) / 86400000.0)


#: پایه‌ی لینک اشتراک — گران است (یک تماس با پنل)، پس کوتاه کش می‌شود.
_SUB_BASE_CACHE = {}
_SUB_BASE_TTL = 300.0


def _sub_base(t):
    """
    پایه‌ی لینک اشتراک. سه منبع، به ترتیب اعتبار.

      ۱. تنظیم خودِ نماینده
      ۲. تنظیم مالک
      ۳. خودِ پنل x-ui

    سومی تازه اضافه شده و مهم است: تا پیش از آن، اگر هیچ‌کس
    sub_base_url را دستی ننوشته بود، *همه‌ی* لینک‌ها خالی می‌ماندند.
    نماینده کانفیگ می‌ساخت و هیچ چیزی برای تحویل به مشتری نداشت، و
    هیچ‌جا هم نمی‌گفت چرا.

    پنل خودش این را می‌داند — سرویس اشتراک روی پورت و مسیر جدا اجرا
    می‌شود و تنظیماتش همان‌جاست. ربات از روز اول همین کار را می‌کرد.
    """
    def _read(row):
        try:
            st = json.loads((row or {}).get("settings") or "{}")
        except (json.JSONDecodeError, TypeError):
            return ""
        return (st.get("sub_base_url") or "").strip() if isinstance(st, dict) else ""

    own = _read(t)
    if own:
        return own.rstrip("/")

    con = _bot_conn()
    try:
        r = con.execute("SELECT settings FROM tenants WHERE parent_id IS NULL "
                        "ORDER BY id LIMIT 1").fetchone() if con else None
        owner = _read(dict(r) if r else {})
    except Exception:
        owner = ""
    finally:
        if con:
            con.close()
    if owner:
        return owner.rstrip("/")

    # ── از خود پنل ──
    key = t.get("id")
    hit = _SUB_BASE_CACHE.get(key)
    if hit and _time.time() - hit[0] < _SUB_BASE_TTL:
        return hit[1]
    found = ""
    try:
        xui, _E = _portal_xui(t)
        found = (xui.panel_sub_base() or "").rstrip("/")
    except Exception:
        log.debug("خواندن آدرس اشتراک از پنل ناموفق", exc_info=True)
        found = ""
    _SUB_BASE_CACHE[key] = (_time.time(), found)
    return found


def _portal_group(t):
    """
    گروه x-ui این نماینده. اگر تعریف نشده باشد، هیچ چیزی نشان نمی‌دهیم.

    برگرداندن «همه» وقتی گروه تنظیم نشده، بدترین حالت ممکن است: یک
    نماینده‌ی نیمه‌ساخته کل مشتری‌های سیستم را می‌دید.
    """
    g = (t.get("portal_group") or "").strip()
    if not g:
        raise HTTPException(
            status_code=409,
            detail="گروه این نماینده هنوز تعیین نشده — با پشتیبانی تماس بگیرید")
    return g


@app.get("/api/portal/configs")
def portal_configs(t: dict = Depends(portal_tenant)):
    """
    کانفیگ‌های همین نماینده — و فقط همین نماینده.

    فیلتر روی گروه، نه روی چیزی که کاربر فرستاده: هیچ پارامتری از
    درخواست در انتخاب ردیف‌ها دخالت ندارد.
    """
    group = _portal_group(t)
    clients, _known, err = _read_xui_clients()
    if clients is None:
        raise HTTPException(status_code=400, detail=err)
    # مصرفِ دوره‌های ریست‌شده. این‌جا هم لازم است، وگرنه نماینده
    # عددی می‌بیند که با صورتحسابش نمی‌خواند — و سرِ همان عدد بحث
    # می‌شود.
    _with_total_usage(clients)

    # لینک اشتراک هر کانفیگ.
    #
    # نماینده موقع ساخت یک بار می‌دیدش و بعد هیچ راهی برای پیدا
    # کردنش نداشت — یعنی مشتری‌ای که لینکش را گم می‌کرد، نماینده
    # هم نمی‌توانست کمکش کند.
    base = _sub_base(t)
    out = []
    for cl in clients:
        if (cl.get("group") or "") != group:
            continue
        cj, cg = _to_jalali(cl.get("createdAt"))
        ej, eg = _to_jalali(cl.get("expiry"))
        gb = _gb_of(cl["totalGB"])
        out.append({
            "email": cl["email"],
            "gb": gb,
            "gbLabel": "نامحدود" if gb == 0 else f"{gb} GB",
            # نماینده همان عددی را ببیند که روی صورتحسابش می‌آید،
            # وگرنه سرِ همین عدد بحث می‌شود. درصد روی دوره‌ی جاری
            # می‌ماند، چون آن نسبتِ سهمیه است نه مصرفِ تاریخی.
            "usedGB": round(cl["usedTotal"] / (1024 ** 3), 1),
            # بایتِ خام هم می‌رود، نه فقط گیگِ گردشده.
            #
            # تصمیمِ «برگشت اعتبار هنگام حذف» با used <= 0 گرفته
            # می‌شود. اگر رابط با usedGB قضاوت کند، مصرفِ چند
            # مگابایتی به ۰٫۰ گرد می‌شود و دیالوگ وعده‌ی برگشتی
            # می‌دهد که بک‌اند انجامش نمی‌دهد — دو جا، دو جواب.
            "used": int(cl["usedTotal"] or 0),
            "usagePct": _usage_percent(cl["used"], cl["totalGB"]),
            "devices": cl.get("limitIp") or 0,
            "createdJalali": cj, "createdGregorian": cg,
            "expiryJalali": ej, "expiryGregorian": eg,
            "daysLeft": _days_left(cl.get("expiry")),
            "active": bool(cl["enable"]),
            "subId": cl.get("subId") or "",
            "subUrl": (f"{base}/{cl.get('subId') or cl['email']}"
                       if base else ""),
        })

    out.sort(key=lambda x: (x.get("createdGregorian") or "9999", x["email"]))
    return {
        "group": group,
        "configs": out,
        "total": len(out),
        "active": sum(1 for x in out if x["active"]),
        "expiringSoon": sum(1 for x in out
                            if x["daysLeft"] is not None and 0 <= x["daysLeft"] <= 7),
    }


@app.get("/api/portal/summary")
def portal_summary(t: dict = Depends(portal_tenant)):
    """
    خلاصه‌ی وضعیت نماینده: چند کانفیگ، چقدر بدهکار، چقدر اعتبار.

    همان محاسبه‌ای که صورتحساب مدیر می‌کند — تا دو طرف یک عدد ببینند
    و سر آن بحث نشود.
    """
    group = _portal_group(t)
    try:
        # فراخوانِ درونی: این‌جا نماینده از `portal_tenant` رد شده و
        # دسترسی‌اش سنجیده شده. پاس‌دادنِ مقدارِ ذخیره‌شده تا امروز
        # کار می‌کرد چون متنِ ساده بود؛ حالا که هَش است، مقایسه‌ی
        # آن با خودش همیشه غلط می‌شود. پس نشانه‌ی درونی می‌دهیم.
        inv = billing_invoice(group, x_admin_password=_INTERNAL_PW)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"محاسبه ناموفق: {str(e)[:120]}")

    tot = inv.get("totals") or {}
    credit = t.get("credit")
    return {
        "group": group,
        "label": inv.get("label") or group,
        "configs": tot.get("configs", 0),
        "months": tot.get("months", 0),
        "renewals": tot.get("renewals", 0),
        "usedGB": tot.get("usedGB", 0),
        "due": tot.get("due", 0),
        "paid": tot.get("paid", 0),
        "balance": tot.get("balance", 0),
        # -1 یعنی نامحدود (مستاجر اصلی)
        "credit": credit,
        "prepaid": credit is not None and int(credit or 0) >= 0,
        "unpriced": tot.get("unpriced", 0),
    }



# ═══════════════════════════════════════════════════════════
#  پنل نماینده — نوشتن
#
#  تا این‌جا نماینده فقط می‌خواند. از این‌جا به بعد در x-ui می‌نویسد،
#  و x-ui همان جایی است که کانفیگ مشتری‌های واقعی زندگی می‌کند. پس
#  سه قاعده که هیچ‌کدام قابل مذاکره نیست:
#
#    ۱. گروه هرگز از درخواست خوانده نمی‌شود. همیشه از ردیف مستاجر.
#    ۲. هر کانفیگی که قرار است تغییر کند، اول از پنل خوانده می‌شود و
#       گروهش سنجیده می‌شود. اینکه نماینده ایمیلش را فرستاده هیچ
#       چیزی را ثابت نمی‌کند.
#    ۳. کسر اعتبار اتمی است و *قبل* از کار انجام می‌شود؛ اگر کار
#       شکست خورد برمی‌گردد.
# ═══════════════════════════════════════════════════════════

def _portal_xui(t):
    """
    اتصال x-ui برای این نماینده.

    اگر خودش پنل جدا دارد، همان. وگرنه پنل مالک — چون در نصب معمول
    یک x-ui هست و گروه‌ها داخلش از هم جدا می‌شوند.
    """
    import importlib.util as _iu
    _p = Path(__file__).resolve().parent.parent / "bot" / "xui.py"
    _sp = _iu.spec_from_file_location("_portal_xui_mod", _p)
    _m = _iu.module_from_spec(_sp)
    _sp.loader.exec_module(_m)

    row = t if t.get("panel_url") else None
    if row is None:
        con = _bot_conn()
        try:
            r = con.execute(
                "SELECT * FROM tenants WHERE parent_id IS NULL "
                "ORDER BY id LIMIT 1").fetchone() if con else None
            row = dict(r) if r else None
        finally:
            if con:
                con.close()
    if not row or not row.get("panel_url"):
        raise HTTPException(status_code=503,
                            detail="اتصال به پنل تنظیم نشده — با پشتیبانی تماس بگیرید")
    return _m.XUI(row.get("panel_url"), row.get("panel_user"),
                  row.get("panel_pass"), row.get("panel_token")), _m.XUIError


def _portal_find(t, email):
    """
    یک کانفیگ از گروهِ همین نماینده — یا خطا.

    گروه از *پنل* خوانده می‌شود، نه از درخواست. اینکه نماینده ایمیلی
    فرستاده هیچ چیزی را ثابت نمی‌کند؛ ممکن است ایمیل مشتری نماینده‌ی
    دیگری باشد.
    """
    group = _portal_group(t)
    clients, _k, err = _read_xui_clients()
    if clients is None:
        raise HTTPException(status_code=400, detail=err)
    for cl in clients:
        if cl.get("email") == email:
            if (cl.get("group") or "") != group:
                # پیام همان «پیدا نشد» است: وگرنه می‌شود فهمید کدام
                # ایمیل‌ها در گروه‌های دیگر وجود دارند.
                raise HTTPException(status_code=404, detail="کانفیگ پیدا نشد")
            return cl
    raise HTTPException(status_code=404, detail="کانفیگ پیدا نشد")


def _portal_live(t, email):
    """
    نسخه‌ی زنده‌ی یک کانفیگ از خودِ پنل — بعد از اینکه گروهش تایید شد.

    دو مرحله عمدی است:

      اول _portal_find که از عکسِ دیتابیس می‌خواند و گروه را می‌سنجد.
      این‌جا تصمیم دسترسی گرفته می‌شود و ارزان است.

      بعد پرسیدن از خودِ پنل، چون شناسه‌ی یکتا و اینباند در آن عکس
      نیستند و نوشتن باید روی چیزی انجام شود که *همین حالا* روی پنل
      است، نه آنچه آخرین بار خوانده‌ایم.

    برمی‌گرداند: (ردیف عکس, ردیف زنده, uuid, inbound_id)
    """
    snap = _portal_find(t, email)        # گروه این‌جا سنجیده می‌شود
    xui, _E = _portal_xui(t)
    try:
        live = xui.find_client(0, email=email)
    except Exception as e:
        raise HTTPException(status_code=502,
                            detail=f"پنل پاسخ نداد: {str(e)[:140]}")
    if not live:
        raise HTTPException(status_code=404, detail="کانفیگ روی پنل پیدا نشد")

    uuid = live.get("id") or live.get("uuid") or live.get("client_uuid")
    ib = live.get("inboundId") or live.get("inbound_id")
    if not ib:
        ids = live.get("inboundIds") or []
        if isinstance(ids, list) and ids:
            ib = ids[0]
    try:
        ib = int(ib or 0)
    except (TypeError, ValueError):
        ib = 0
    return snap, live, uuid, ib


def _portal_rates(t):
    """نرخ‌های گروه این نماینده، از تنظیمات حسابداری."""
    group = _portal_group(t)
    con = _billing_conn()
    try:
        r = con.execute("SELECT * FROM group_config WHERE group_key=?",
                        (group,)).fetchone()
        conf = dict(r) if r else {}
    finally:
        con.close()
    try:
        rates = json.loads(conf.get("rates") or "[]")
    except (json.JSONDecodeError, TypeError):
        rates = []
    return conf, (rates if isinstance(rates, list) else [])


def _portal_gb_policy(t):
    """
    نماینده چه حجم‌هایی می‌تواند برای ربات خودش بفروشد؟

    برمی‌گرداند: (mode, allowed, per_gb)
        mode = "volume" | "tiers" | "open"

    سه حالت، و هر سه از همان `group_config` می‌آیند که حسابداری از
    رویش می‌خواند — هیچ نرخِ تازه‌ای این‌جا ساخته نمی‌شود:

      volume  مالک نرخ حجمی گذاشته و به‌ازای مصرف حساب می‌کند، پس
              پله معنا ندارد و هر حجمی مجاز است.
      tiers   مالک پله تعریف کرده؛ فقط همان‌ها.
      open    مالک هنوز هیچ نرخی نگذاشته. عمداً باز است — بستنش
              یعنی نماینده‌ای که نرخش تعریف نشده اصلاً نتواند کار
              کند. ولی رابط باید *بگوید* چرا باز است، وگرنه همان
              مسیر خرابِ بی‌صداست.
    """
    conf, rates = _portal_rates(t)
    per_gb = _price_per_gb(conf) or 0
    if per_gb > 0:
        return "volume", [], per_gb

    allowed = []
    for r in rates:
        try:
            allowed.append(max(0, int(r.get("gb", 0) or 0)))
        except (TypeError, ValueError):
            continue
    allowed = sorted(set(allowed))
    if allowed:
        return "tiers", allowed, 0
    return "open", [], 0


def _credit_log(con, tid, amount, balance, note):
    """
    یک سطر در دفتر اعتبار. شکستش نباید کار اصلی را متوقف کند.

    روی همان اتصالی می‌نویسد که تغییر اعتبار را انجام داده، تا اگر
    آن تراکنش برنگردد این هم برنگردد.
    """
    try:
        con.execute("""CREATE TABLE IF NOT EXISTS credit_tx (
            id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id INTEGER NOT NULL,
            amount INTEGER NOT NULL, balance INTEGER, note TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        con.execute(
            "INSERT INTO credit_tx (tenant_id, amount, balance, note) "
            "VALUES (?,?,?,?)", (tid, int(amount), balance, str(note or "")[:200]))
    except Exception:
        log.debug("ثبت دفتر اعتبار ناموفق", exc_info=True)


def _portal_charge(t, amount, note):
    """
    کسر اعتبار — اتمی، و فقط وقتی نماینده پیش‌پرداخت است.

    برمی‌گرداند: (اجازه هست؟, پیام)

    شرط داخل خودِ UPDATE است. الگوی «اول بخوان، اگر کافی بود کم کن»
    بین آن دو جا برای یک درخواست دیگر باز می‌گذارد — همان مسابقه‌ای
    که امروز در کیف پول ربات بسته شد.
    """
    credit = t.get("credit")
    if credit is None or int(credit) < 0:
        return True, "بدهکاری"          # نامحدود: آخر ماه صورتحساب
    amount = max(0, int(amount or 0))
    if amount <= 0:
        return True, "رایگان"

    con = _bot_rw()
    try:
        cur = con.execute(
            "UPDATE tenants SET credit = credit - ? WHERE id=? AND credit >= ?",
            (amount, t["id"], amount))
        if not cur.rowcount:
            row = con.execute("SELECT credit FROM tenants WHERE id=?",
                              (t["id"],)).fetchone()
            have = int((row["credit"] if row else 0) or 0)
            return False, (f"اعتبار کافی نیست — لازم {amount:,} تومان، "
                           f"موجودی {have:,} تومان")
        left = con.execute("SELECT credit FROM tenants WHERE id=?",
                           (t["id"],)).fetchone()
        _credit_log(con, t["id"], -amount,
                    int((left["credit"] if left else 0) or 0), note)
        con.commit()
    finally:
        con.close()
    log.info("اعتبار نماینده %s کم شد: %s (%s)", t["id"], amount, note)
    return True, "کسر شد"


def _portal_refund(t, amount):
    """برگرداندن اعتبار وقتی کار روی پنل شکست خورد."""
    credit = t.get("credit")
    if credit is None or int(credit) < 0 or not amount:
        return
    con = _bot_rw()
    try:
        con.execute("UPDATE tenants SET credit = credit + ? WHERE id=?",
                    (int(amount), t["id"]))
        row = con.execute("SELECT credit FROM tenants WHERE id=?",
                          (t["id"],)).fetchone()
        _credit_log(con, t["id"], int(amount),
                    int((row["credit"] if row else 0) or 0),
                    "بازگشت — کار روی پنل انجام نشد")
        con.commit()
    finally:
        con.close()


def _portal_due_so_far(t, cl):
    """
    بدهیِ این کانفیگ تا همین لحظه. برمی‌گرداند: (ماه, مبلغ)

    از همان دو تابعی می‌خواند که کلِ حسابداری از آن‌ها می‌خواند —
    `_period_share` برای ماه و `_line_amount` برای مبلغ. حساب‌کردنِ
    دستی این‌جا یعنی سطح پنجمی که عدد خودش را می‌سازد، و مالک چهار
    تای قبلی را دیده که چهار عدد متفاوت می‌دادند.
    """
    conf, rates = _portal_rates(t)
    if not rates and not _price_per_gb(conf):
        return 0, 0

    since, _why = _bill_since(conf)
    bcon = _billing_conn()
    try:
        first = {r["email"]: r["first_seen"] for r in bcon.execute(
            "SELECT email, first_seen FROM client_seen")}
        logged = {r["email"]: r["m"] for r in bcon.execute(
            "SELECT email, COALESCE(SUM(months),0) m FROM renewals "
            "GROUP BY email")}
        rows = _rows_by_email([dict(r) for r in bcon.execute(
            "SELECT email, months, created_at FROM renewals")])
    except Exception:
        log.debug("خواندن سابقه برای بدهیِ حذف ناموفق", exc_info=True)
        return 0, 0
    finally:
        bcon.close()

    try:
        months, _all, _ren, _new, _kind, _drift = _period_share(
            cl, logged, rows, since,
            group_start=(conf or {}).get("period_start"),
            first_seen=first.get(cl.get("email")))
        gb = _gb_of(cl.get("totalGB"))
        amount, _base, _per, _extra = _line_amount(
            gb, rates, months, cl.get("limitIp"))
    except Exception:
        log.debug("محاسبه‌ی بدهیِ حذف ناموفق", exc_info=True)
        return 0, 0
    return months, int(amount or 0)


def _portal_charge_for(t, email):
    """
    مبلغی که موقع ساختِ همین کانفیگ از اعتبار کم شد.

    از دفتر اعتبار خوانده می‌شود، نه از نرخِ امروز — نرخ ممکن است در
    این فاصله عوض شده باشد و آن‌وقت برگشتی می‌دادیم که با گرفته‌شده
    نمی‌خواند.

    صفر برمی‌گرداند اگر پیدا نشود یا قبلاً برگشته باشد، چون برگرداندنِ
    دوباره یعنی هدیه‌دادنِ اعتبار.
    """
    credit = t.get("credit")
    if credit is None or int(credit) < 0:
        return 0                      # بدهکار: اصلاً اعتباری کم نشده
    con = _bot_conn()
    if not con:
        return 0
    try:
        rows = con.execute(
            "SELECT amount, note FROM credit_tx WHERE tenant_id=? "
            "AND note LIKE ? ORDER BY id",
            (t["id"], "%" + email + "%")).fetchall()
    except Exception:
        log.debug("خواندن دفتر اعتبار ناموفق", exc_info=True)
        return 0
    finally:
        con.close()

    spent = sum(-int(r["amount"]) for r in rows if int(r["amount"] or 0) < 0)
    back = sum(int(r["amount"]) for r in rows if int(r["amount"] or 0) > 0)
    return max(0, spent - back)


def _bill_record_deleted(email, group, months, amount, gb, used, by_whom,
                         note=""):
    """
    ثبت اینکه چه کانفیگی با چه بدهی‌ای از فاکتور بیرون رفت.

    عدد فاکتور را عوض نمی‌کند — فقط جلوی بی‌صدا رفتنش را می‌گیرد.
    شکستِ این ثبت نباید حذف را متوقف کند، ولی باید در لاگ دیده شود.
    """
    try:
        con = _billing_conn()
    except Exception:
        log.warning("ثبت کانفیگ حذف‌شده ناموفق — دیتابیس حسابداری باز نشد")
        return
    try:
        con.execute(
            "INSERT INTO deleted_clients (email,group_key,deleted_at,months,"
            "amount,gb,used,by_whom,note) VALUES (?,?,?,?,?,?,?,?,?)",
            (email, group, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             float(months or 0), int(amount or 0),
             int(gb or 0), int(used or 0), by_whom, note))
        con.commit()
    except Exception:
        log.warning("ثبت کانفیگ حذف‌شده ناموفق", exc_info=True)
    finally:
        con.close()


def _portal_log_renewal(t, email, months, new_expiry_ms=None):
    """
    تمدید را همان لحظه و دقیق ثبت می‌کند، و مبنای ناظرِ انقضا را جلو
    می‌برد.

    این تمام دلیلِ وجود این پنل است. وقتی نماینده در x-ui کار می‌کرد
    هیچ ردی نمی‌ماند و صورتحساب مجبور بود از فاصله‌ی ساخت تا انقضا
    حدس بزند. این‌جا تاریخ و تعداد ماه *واقعی* است، نه تخمینی.

    چرا new_expiry_ms لازم است:
        دو سازوکار موازی تمدید را ثبت می‌کنند. این یکی، و
        _detect_renewals که انقضای هر کلاینت را به خاطر می‌سپارد و
        دفعه‌ی بعد اگر جلو رفته باشد «تمدید» ثبت می‌کند.

        ناظرِ انقضا برای تمدیدهایی است که نماینده *مستقیم در x-ui*
        می‌زند و هیچ ردی نمی‌گذارند. ولی تمدیدی که از همین پنل آمده
        هم انقضا را جلو می‌برد — پس ناظر هم همان را دوباره ثبت
        می‌کرد. یک تمدید، دو ردیف، و صورتحساب ۵۰٪ بیشتر: سه ماه
        به‌جای دو.

        با جلوبردن مبنا، ناظر چیزی برای دیدن ندارد.
    """
    con = _billing_conn()
    try:
        if new_expiry_ms:
            row = con.execute(
                "SELECT last_expiry FROM client_seen WHERE email=?",
                (email,)).fetchone()
            prev = int((row["last_expiry"] if row else 0) or 0)
            # اگر ناظر زودتر رسیده باشد — نمای کلی درست بین تمدید و
            # این ثبت خوانده شده باشد — مبنا از قبل جلو رفته و همین
            # تمدید ثبت شده. دوباره ثبتش نمی‌کنیم.
            if prev and prev >= int(new_expiry_ms):
                log.info("تمدید %s را ناظرِ انقضا زودتر ثبت کرده بود", email)
                return
        con.execute(
            "INSERT INTO renewals (email, group_key, months, created_at) "
            "VALUES (?,?,?,?)",
            (email, t.get("portal_group") or "", int(months),
             datetime.now().strftime("%Y-%m-%d")))
        if new_expiry_ms:
            con.execute("UPDATE client_seen SET last_expiry=? WHERE email=?",
                        (int(new_expiry_ms), email))
        con.commit()
    except Exception:
        log.warning("ثبت تمدید نماینده ناموفق", exc_info=True)
    finally:
        con.close()


@app.get("/api/portal/plans")
def portal_plans(t: dict = Depends(portal_tenant)):
    """
    چیزهایی که این نماینده می‌تواند بسازد — از روی نرخ‌های گروه خودش.

    نرخ همان چیزی است که مالک تعریف کرده؛ نماینده نمی‌تواند عددی
    بفرستد که قیمت را عوض کند.
    """
    conf, rates = _portal_rates(t)
    out = []
    for r in rates:
        try:
            gb = max(0, int(r.get("gb", 0) or 0))
            price = max(0, int(r.get("price", 0) or 0))
            per = max(0, int(r.get("perDevice", 0) or 0))
        except (TypeError, ValueError):
            continue
        out.append({"gb": gb, "price": price, "perDevice": per,
                    "label": "نامحدود" if gb == 0 else f"{gb} گیگ"})
    credit = t.get("credit")
    return {"plans": out,
            "prepaid": credit is not None and int(credit or 0) >= 0,
            "credit": credit,
            "perGb": _price_per_gb(conf) or 0}


@app.post("/api/portal/renew")
def portal_renew(payload: dict, t: dict = Depends(portal_tenant)):
    """
    تمدید یک کانفیگ — و ثبت دقیقش.
    """
    p = payload or {}
    email = str(p.get("email") or "").strip()
    _mv = p.get("months")
    try:
        months = 1 if _mv is None or _mv == "" else int(_mv)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="تعداد ماه نامعتبر است")
    if not 1 <= months <= 12:
        raise HTTPException(status_code=400, detail="تعداد ماه باید بین ۱ تا ۱۲ باشد")

    cl, _live, uuid, ib = _portal_live(t, email)
    _conf, rates = _portal_rates(t)
    gb = _gb_of(cl["totalGB"])
    amount, base, _per, _extra = _line_amount(gb, rates, months,
                                              cl.get("limitIp"))
    if base is None:
        raise HTTPException(
            status_code=409,
            detail="برای این حجم نرخی تعریف نشده — با پشتیبانی تماس بگیرید")

    # اتصال پیش از کسر اعتبار — مثل مسیر ساخت. اگر _portal_xui
    # بیفتد (ماژول خوانده نشود، ردیف مالک پیدا نشود) خطا بالا می‌رود
    # و هیچ‌جا پول را برنمی‌گرداند؛ فقط شکستِ خودِ تمدید برگشت دارد.
    xui, _XUIError = _portal_xui(t)

    ok, why = _portal_charge(t, amount, f"تمدید {email}")
    if not ok:
        raise HTTPException(status_code=402, detail=why)

    try:
        # حجم هم به همان اندازه‌ی ماه‌ها اضافه می‌شود — همان کاری که
        # تمدید از مسیر ربات می‌کند، پس مصرف و سقف با هم بالا می‌روند
        # و درصدها معنا می‌دهند.
        res = xui.extend_subscription(
            ib, uuid,
            add_days=months * 30,
            add_gb=(gb * months) if gb else 0,
            email=email)
    except Exception as e:
        _portal_refund(t, amount)
        raise HTTPException(status_code=502,
                            detail=f"پنل تمدید را انجام نداد: {str(e)[:140]}")

    # اگر پنل انقضای تازه را برنگرداند، از روی انقضای قبلی حسابش
    # می‌کنیم. بدون عدد، مبنای ناظر جلو نمی‌رود و تمدید دو بار ثبت
    # می‌شود — که دقیقاً همان چیزی است که این عدد برای جلوگیری از آن
    # پاس داده می‌شود.
    new_exp = (res or {}).get("expiry_ms")
    if not new_exp:
        old = _epoch_ms(cl.get("expiry")) or 0
        new_exp = int(old + months * 30 * 86400000) if old else None
    _portal_log_renewal(t, email, months, new_expiry_ms=new_exp)
    return {"ok": True, "email": email, "months": months,
            "charged": amount,
            "expiryMs": new_exp}



def _portal_new_email(t, taken, label=""):
    """
    نام کانفیگ تازه.

    **پیشوند** ساختِ ماست، نه فرستاده‌ی نماینده — و این عمدی است:
    `find_reseller` برندِ صفحه‌ی اشتراک را از همان تکه‌ی پیش از اولین
    `_` تشخیص می‌دهد. اگر نماینده پیشوند را انتخاب می‌کرد، می‌توانست
    نامی بسازد که با الگوی گروه دیگری بخواند — یعنی مشتریِ او برندِ
    نماینده‌ی دیگری را ببیند، و حسابداری هم ممکن بود ردیف را جای
    دیگری بشمارد.

    **بخشِ دوم** ولی مالِ خودِ نماینده است. تا امروز هشت نویسه‌ی
    تصادفی بود (`ali_3f2a9b1c`) و نماینده هیچ راهی نداشت بفهمد کدام
    کانفیگ مالِ کدام مشتری است. حالا می‌تواند نام بدهد و
    `ali_hossein` بگیرد.

    برچسب سخت‌گیرانه پاک می‌شود: فقط حرف و رقم لاتین و خط تیره. نه
    برای زیبایی — این رشته در URLِ اشتراک و در جدول‌های x-ui می‌نشیند
    و فاصله و حرف فارسی هر دو جا دردسر می‌سازند.
    """
    slug = "".join(ch for ch in str(t.get("portal_slug") or "nx")
                   if ch.isalnum())[:12].lower() or "nx"

    clean = _re.sub(r"[^A-Za-z0-9-]+", "-", str(label or "")).strip("-")[:24]
    clean = _re.sub(r"-{2,}", "-", clean).lower()

    if clean:
        name = f"{slug}_{clean}"
        if name not in taken:
            return name
        # نام تکراری: عددِ کوچک می‌گیرد، نه هشت نویسه‌ی تصادفی —
        # «hossein-2» هنوز برای نماینده معنا دارد
        for n in range(2, 60):
            cand = f"{slug}_{clean}-{n}"
            if cand not in taken:
                return cand

    for _ in range(40):
        name = f"{slug}_{_secrets.token_hex(4)}"
        if name not in taken:
            return name
    raise HTTPException(status_code=500, detail="ساخت نام یکتا ممکن نشد")


def _portal_inbound_ids(t, inbound):
    """
    اینباندهایی که کانفیگِ این نماینده باید رویشان بنشیند.

    برمی‌گرداند: فهرست، یا None یعنی «همه‌ی اینباندهای فعال» — که
    تصمیمش با خود کلاینت x-ui است.

    این دقیقاً همان قاعده‌ای است که ربات اجرا می‌کند
    (`bot/handlers.py`، جایی که `inbound_mode` خوانده می‌شود). دو
    پیاده‌سازی‌اند چون دو پردازه‌ی جدا هستند، پس تست برابری‌شان را
    اجرا می‌کند.

    چرا لازم شد: انتخابِ اینباندِ هر نماینده اضافه شد و ربات آن را
    می‌خواند — ولی پنلِ خودِ نماینده نه. یعنی مالک می‌گفت «کانفیگ‌های
    این نماینده روی اینباند ۴۱ و ۴۵»، نماینده از پنل خودش کانفیگ
    می‌ساخت، و روی اینباند پیش‌فرض می‌نشست. بی‌صدا و بدون هیچ خطایی.
    """
    mode = (t.get("inbound_mode") or "all").strip().lower()

    if mode == "custom":
        raw = t.get("inbound_ids")
    elif mode == "default":
        raw = json.dumps([inbound]) if inbound else None
    else:
        return None

    if not raw:
        return None
    try:
        ids = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        ids = [x.strip() for x in str(raw).split(",") if x.strip()]

    out = []
    for x in (ids or []):
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    return out or None


def _portal_inbound(t, xui=None):
    """
    اینباندی که کانفیگ روی آن ساخته می‌شود.

    ترتیب — و هر پله دلیلی دارد:

      ۱. انتخابِ خودِ نماینده (`inbound_mode` / `inbound_ids`).
         این پله اصلاً وجود نداشت. مالک برای نماینده اینباند ۴۱ و ۴۵
         را تعریف می‌کرد و پنلِ نماینده باز هم می‌گفت «اینباند پیش‌فرض
         تنظیم نشده» — چون فقط `default_inbound` را نگاه می‌کرد و آن
         ستون خالی بود. یعنی پیامِ خطا دقیقاً چیزی را انکار می‌کرد که
         تعریف شده بود.

      ۲. پیش‌فرضِ خودِ نماینده، بعد پیش‌فرضِ مالک.

      ۳. اولین اینباندِ فعالِ پنل.
         این همان کاری است که ربات از قبل می‌کرد
         (`bot/handlers.py`، جایی که default_inbound خالی است) و
         کامنتش دلیلش را نوشته: شکستِ کامل از دید مشتری یعنی «پول
         دادم و کانفیگ نگرفتم». پرتالِ نماینده عکسش را می‌کرد.

    فقط وقتی خطا می‌دهد که هیچ اینباند فعالی هم پیدا نشود — یعنی
    واقعاً جایی برای ساختن نیست.
    """
    # ۱. انتخابِ خودِ نماینده
    ids = _portal_inbound_ids(t, t.get("default_inbound"))
    if ids:
        return ids[0]

    # ۲. پیش‌فرضِ خودش، بعد پیش‌فرضِ مالک
    ib = t.get("default_inbound")
    if not ib:
        con = _bot_conn()
        try:
            r = con.execute(
                "SELECT default_inbound FROM tenants WHERE parent_id IS NULL "
                "ORDER BY id LIMIT 1").fetchone() if con else None
            ib = (r["default_inbound"] if r else None)
        except Exception:
            ib = None
        finally:
            if con:
                con.close()
    try:
        ib = int(ib or 0)
    except (TypeError, ValueError):
        ib = 0
    if ib > 0:
        return ib

    # ۳. اولین اینباند فعال — مثل ربات
    if xui is not None:
        try:
            active = [i for i in (xui.inbounds() or []) if i.get("enable", True)]
        except Exception as e:
            log.warning("خواندن اینباندها برای انتخاب خودکار ناموفق: %s", e)
            active = []
        for i in active:
            try:
                n = int(i.get("id") or 0)
            except (TypeError, ValueError):
                continue
            if n > 0:
                log.info("اینباند پیش‌فرض تنظیم نشده بود؛ اینباند %s استفاده شد", n)
                return n

    raise HTTPException(
        status_code=503,
        detail="هیچ اینباند فعالی در پنل پیدا نشد — با پشتیبانی تماس بگیرید")


@app.post("/api/portal/config")
def portal_create(payload: dict, t: dict = Depends(portal_tenant)):
    """
    ساخت کانفیگ تازه در گروهِ همین نماینده.

    حجم باید یکی از پله‌هایی باشد که مالک برای این گروه تعریف کرده.
    نماینده نمی‌تواند حجمی بسازد که نرخ ندارد — وگرنه ردیفی ساخته
    می‌شود که سر ماه «بدون نرخ» می‌ماند و کسی پولش را نمی‌دهد.
    """
    p = payload or {}
    group = _portal_group(t)
    _conf, rates = _portal_rates(t)
    if not rates:
        raise HTTPException(status_code=409,
                            detail="برای این گروه نرخی تعریف نشده")

    # «نیامده» و «صفر آمده» یکی نیستند.
    #
    # int(p.get("months") or 1) صفر را بی‌صدا به یک تبدیل می‌کرد —
    # یعنی کسی که صفر ماه خواسته، یک ماه می‌گرفت و پولش را می‌داد.
    # وقتی پول در میان است، عوض‌کردن بی‌صدای خواسته‌ی کاربر غلط است.
    def _num(key, default):
        v = p.get(key)
        if v is None or v == "":
            return default
        return int(v)

    try:
        gb = max(0, _num("gb", 0))
        devices = _num("devices", 1)
        # روز، نه فقط ماه.
        #
        # نماینده می‌خواهد «۴۵ روز» یا «۱۰ روز» بدهد، نه اینکه بین
        # ۱ و ۲ و ۳ ماه گیر کند. ماه هنوز پذیرفته می‌شود تا هر
        # فراخوانیِ قدیمی بشکند نشود.
        days = _num("days", 0)
        months_in = _num("months", 0)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="ورودی نامعتبر است")

    # «نفرستاده» با «صفر فرستاده» یکی نیست: اگر هیچ‌کدام نیامده باشد
    # یک ماه پیش‌فرض است، ولی روزِ صفر یک ورودیِ غلط است و باید
    # گفته شود — نه اینکه بی‌صدا یک ماه شود.
    if p.get("days") is None and p.get("months") is None:
        months_in = 1
    if months_in and not days:
        days = months_in * 30

    if not 1 <= days <= 366:
        raise HTTPException(status_code=400,
                            detail="تعداد روز باید بین ۱ تا ۳۶۶ باشد")
    if not 0 <= devices <= 20:
        raise HTTPException(status_code=400, detail="تعداد کاربر باید بین ۰ تا ۲۰ باشد")

    # مبلغ همچنان بر حسب ماه حساب می‌شود، با همان تابعی که کلِ
    # حسابداری از آن می‌خواند. اگر این‌جا روز را جدا قیمت‌گذاری
    # می‌کردیم، سطح تازه‌ای می‌شد که عدد خودش را می‌سازد — همان
    # چیزی که چهار بار قبلاً چهار عدد متفاوت داد.
    months = _months_from_days(days)

    # شروع از اولین اتصال — همان کاری که خود پنل ۳x-ui می‌کند:
    # expiryTime منفی یعنی «این‌قدر مدت، از لحظه‌ای که وصل شد».
    # پنل از قبل این حالت را می‌شناسد و «شروع‌نشده» نشانش می‌دهد.
    on_use = bool(p.get("startOnFirstUse") or p.get("start_on_use"))

    # حجم باید دقیقاً یکی از پله‌های تعریف‌شده باشد
    tiers = set()
    for r in rates:
        try:
            tiers.add(max(0, int(r.get("gb", 0) or 0)))
        except (TypeError, ValueError):
            continue
    if gb not in tiers:
        raise HTTPException(
            status_code=400,
            detail="این حجم در نرخ‌های گروه شما نیست")

    amount, base, _per, _extra = _line_amount(gb, rates, months, devices)
    if base is None:
        raise HTTPException(status_code=409, detail="نرخ این حجم پیدا نشد")

    clients, _k, err = _read_xui_clients()
    if clients is None:
        raise HTTPException(status_code=400, detail=err)
    taken = {c.get("email") for c in clients}
    email = _portal_new_email(t, taken, p.get("label") or p.get("name") or "")

    # اتصال و اینباند *پیش* از کسر اعتبار حل می‌شوند.
    #
    # قبلاً اول پول کم می‌شد و بعد این دو. هر کدامشان که شکست
    # می‌خورد، خطا بالا می‌رفت و هیچ‌جا پول را برنمی‌گرداند —
    # فقط شکستِ خودِ add_client برگشت داشت. یعنی نماینده‌ای که
    # اینباندش تنظیم نبود، اعتبارش کم می‌شد و کانفیگی نمی‌گرفت.
    # هر دو فقط می‌خوانند، پس جابه‌جا کردنشان بی‌خطر است.
    xui, _E = _portal_xui(t)
    inbound = _portal_inbound(t, xui)

    ok, why = _portal_charge(t, amount, f"ساخت {email}")
    if not ok:
        raise HTTPException(status_code=402, detail=why)

    try:
        # گروه از ردیف مستاجر می‌آید، نه از درخواست. این تنها جایی
        # است که تعیین می‌کند کانفیگ تازه مال کیست.
        client = xui.add_client(inbound, email, gb=gb, days=days,
                                ip_limit=devices, group=group,
                                start_on_use=on_use,
                                inbound_ids=_portal_inbound_ids(t, inbound))
    except Exception as e:
        _portal_refund(t, amount)
        raise HTTPException(status_code=502,
                            detail=f"پنل کانفیگ را نساخت: {str(e)[:140]}")

    # ساخت هم مثل تمدید ثبت می‌شود: دوره‌ی اول هم فروش است.
    #
    # کلاینت تازه هنوز در client_seen نیست، پس ناظر اولین بار با
    # همین انقضا ثبتش می‌کند و چیزی دو بار شمرده نمی‌شود.
    if months > 1:
        _portal_log_renewal(t, email, months - 1)

    _b = _sub_base(t)
    sub_url = (f"{_b}/{(client or {}).get('subId') or email}") if _b else None

    # گروه واقعاً نشست؟
    #
    # گروه تنها چیزی است که می‌گوید این کانفیگ مالِ کدام نماینده
    # است — هم برای صورتحساب، هم برای اینکه خودِ نماینده ببیندش.
    # اگر ننشیند، کانفیگ ساخته می‌شود، پولش هم کم می‌شود، و بعد در
    # فهرستِ نماینده پیدا نمی‌شود. هیچ خطایی هم نمی‌آید.
    #
    # نسخه‌های قدیمی‌تر ۳x-ui اصلاً گروه ندارند و `groupName` را
    # بی‌صدا دور می‌ریزند، پس این را نمی‌شود فرض گرفت — باید خواند.
    group_ok, group_got = True, group
    try:
        fresh, _k, _e = _read_xui_clients()
        for c in (fresh or []):
            if c.get("email") == email:
                group_got = (c.get("group") or "").strip()
                group_ok = (group_got == group)
                break
    except Exception:
        log.debug("بازخوانی گروهِ کانفیگ تازه ناموفق", exc_info=True)

    out = {"ok": True, "email": email, "gb": gb, "months": months,
           "days": days, "startOnFirstUse": on_use,
           "devices": devices, "charged": amount,
           "uuid": (client or {}).get("id"), "subUrl": sub_url}
    if not group_ok:
        log.warning("کانفیگ %s ساخته شد ولی گروهش «%s» شد نه «%s»",
                    email, group_got, group)
        out["groupWarning"] = (
            f"کانفیگ ساخته شد ولی در گروه «{group_got or 'بدون گروه'}» "
            f"نشست، نه «{group}». تا وقتی گروهش درست نشود، در فهرست "
            "شما و در صورتحساب دیده نمی‌شود — به پشتیبانی بگویید.")
    return out


@app.post("/api/portal/toggle")
def portal_toggle(payload: dict, t: dict = Depends(portal_tenant)):
    """فعال یا غیرفعال کردن یک کانفیگ — فقط از گروه خودش."""
    p = payload or {}
    email = str(p.get("email") or "").strip()
    want = bool(p.get("enable"))
    _cl, _live, uuid, ib = _portal_live(t, email)

    xui, _E = _portal_xui(t)
    try:
        xui.set_enabled(ib, uuid, want, email=email)
    except Exception as e:
        raise HTTPException(status_code=502,
                            detail=f"پنل تغییر را انجام نداد: {str(e)[:140]}")
    return {"ok": True, "email": email, "enabled": want}


@app.delete("/api/portal/config/{email}")
def portal_config_delete(email: str, t: dict = Depends(portal_tenant)):
    """
    حذف کانفیگ — فقط از گروه خودش.

    دو حالتِ کاملاً متفاوت که یک دکمه‌اند:

      • **کانفیگی که هنوز کار نکرده.** مشتری همان لحظه پشیمان شده.
        اعتبارِ نماینده باید برگردد، وگرنه بابت چیزی پول داده که
        هیچ‌کس استفاده‌اش نکرد. مبلغ از همان `credit_tx`ی خوانده
        می‌شود که موقع ساخت نوشته شد — نه از نرخِ امروز، چون ممکن
        است نرخ در این فاصله عوض شده باشد.

      • **کانفیگی که مصرف داشته.** دوره‌اش را کار کرده، پس بدهی‌اش
        می‌ماند. این همان قاعده‌ای است که مالک برای انقضا گذاشت:
        «منقضی شد» راه فرار از پرداخت نیست — و حذف راهِ فرارِ
        بزرگ‌تری است، چون صورتحساب از فهرستِ زنده‌ی x-ui خوانده
        می‌شود و ردیفِ حذف‌شده کاملاً از فاکتور غیب می‌شود.

        پس پیش از پاک‌کردن، سهمِ همین دوره در `renewals` قفل می‌شود
        تا فاکتور فراموشش نکند.
    """
    email = str(email or "").strip()
    cl, _live, uuid, ib = _portal_live(t, email)

    # «هیچ مصرفی نشده» یعنی **هیچ‌وقت**، نه از آخرین ریست.
    #
    # بدونِ این، نماینده می‌توانست ترافیک را ریست کند و بعد کانفیگ
    # را پاک کند تا پولِ ساختش کامل برگردد — در حالی که مشتری حجمش
    # را مصرف کرده بود و ریست هم دستِ خودِ نماینده است.
    _with_total_usage([cl] if cl else [])
    used = int((cl or {}).get("usedTotal") or 0)
    billable, why = _billable_config(cl or {})

    # مبلغی که موقع ساخت گرفته شد — اگر هنوز چیزی مصرف نشده،
    # همان برمی‌گردد
    refund = 0
    if used <= 0:
        refund = _portal_charge_for(t, email)

    # سهمی که تا همین لحظه روی فاکتور آمده بود — پیش از پاک‌کردن
    # حساب می‌شود، چون بعدش دیگر ردیفی نیست
    owed_months, owed_amount = 0, 0
    if billable:
        owed_months, owed_amount = _portal_due_so_far(t, cl)

    xui, _E = _portal_xui(t)
    try:
        xui.delete_client(ib, uuid, email=email)
    except Exception as e:
        raise HTTPException(status_code=502,
                            detail=f"پنل کانفیگ را پاک نکرد: {str(e)[:140]}")

    if refund:
        _portal_refund(t, refund)

    if billable and owed_amount > 0:
        _bill_record_deleted(
            email, _portal_group(t), owed_months, owed_amount,
            (cl or {}).get("totalGB"), used,
            f"نماینده #{t.get('id')}", why or "")

    log.info("نماینده %s کانفیگ %s را حذف کرد (مصرف %s، برگشت %s، بدهی %s)",
             t.get("id"), email, used, refund, owed_amount)

    return {
        "ok": True, "email": email,
        "refunded": refund,
        "owedAmount": owed_amount,
        "note": ("کانفیگ حذف شد و اعتبارش برگشت — چیزی مصرف نشده بود"
                 if refund else "کانفیگ حذف شد"),
    }



# ═══════════════════════════════════════════════════════════
#  ربات شخصی نماینده
#
#  زیرساختش از قبل هست: run.py برای هر مستاجرِ فعال که توکن دارد یک
#  نخ polling جدا می‌سازد، با برند و پنل و مشتری‌های خودش. هر سی
#  ثانیه هم sync_workers نگاه می‌کند چه چیزی تازه اضافه شده.
#
#  پس تنها کاری که این‌جا می‌ماند ثبت توکن است — و مهم‌ترین بخشش
#  این است که توکنِ غلط قبل از ذخیره‌شدن رد شود. توکنی که تایپش
#  اشتباه باشد، رباتی می‌سازد که بالا می‌آید و هیچ‌وقت جواب نمی‌دهد،
#  و نماینده هیچ راهی ندارد بفهمد چرا.
# ═══════════════════════════════════════════════════════════

#: کلیدهایی که نماینده می‌تواند از برندش عوض کند.
#
#  فهرست مجاز، نه ممنوع: settings کلیدهای حساس هم دارد (اتصال پنل،
#  شناسه‌ی گروه مدیریت) و باز گذاشتنش یعنی نماینده می‌تواند چیزهایی
#  را عوض کند که مال او نیست.
PORTAL_BRAND_KEYS = {"brand", "support_username", "channel_username"}


def _tg_get_me(token, timeout=10):
    """
    توکن را از خودِ تلگرام می‌پرسد. برمی‌گرداند: (درست؟, نام کاربری یا پیام)
    """
    import urllib.request
    import urllib.error
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "تلگرام این توکن را نمی‌شناسد"
        return False, f"تلگرام پاسخ نداد (HTTP {e.code})"
    except Exception as e:
        return False, f"تلگرام در دسترس نبود: {type(e).__name__}"
    if not data.get("ok"):
        return False, "تلگرام این توکن را نپذیرفت"
    return True, (data.get("result") or {}).get("username") or ""


@app.get("/api/portal/bot")
def portal_bot_get(t: dict = Depends(portal_tenant)):
    """
    وضعیت ربات نماینده. توکن هرگز برنمی‌گردد — فقط اینکه هست یا نه.
    """
    try:
        st = json.loads(t.get("settings") or "{}")
    except (json.JSONDecodeError, TypeError):
        st = {}
    return {
        "hasBot": bool(t.get("bot_token")),
        "username": t.get("bot_username") or "",
        "brand": st.get("brand") or t.get("name") or "",
        "supportUsername": st.get("support_username") or "",
        "channelUsername": st.get("channel_username") or "",
    }


@app.post("/api/portal/bot")
def portal_bot_set(payload: dict, t: dict = Depends(portal_tenant)):
    """
    ثبت یا جایگزینی توکن ربات نماینده.

    توکن اول از تلگرام پرسیده می‌شود و تا وقتی تایید نشود ذخیره
    نمی‌شود. ربات خودش تا حداکثر نیم دقیقه بعد بالا می‌آید.
    """
    token = str((payload or {}).get("token") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="توکن وارد نشده")
    if ":" not in token or len(token) < 20:
        raise HTTPException(status_code=400, detail="شکل توکن درست نیست")

    con = _bot_conn()
    try:
        used = con.execute(
            "SELECT name FROM tenants WHERE bot_token=? AND id<>?",
            (token, t["id"])).fetchone() if con else None
    finally:
        if con:
            con.close()
    if used:
        # نام مالکش را نمی‌گوییم — نماینده نباید بفهمد چه کسانی
        # در سیستم هستند.
        raise HTTPException(status_code=409,
                            detail="این ربات قبلاً برای حساب دیگری ثبت شده")

    ok, who = _tg_get_me(token)
    if not ok:
        raise HTTPException(status_code=400, detail=who)

    con = _bot_rw()
    try:
        con.execute("UPDATE tenants SET bot_token=?, bot_username=? WHERE id=?",
                    (token, who, t["id"]))
        con.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ذخیره نشد: {str(e)[:120]}")
    finally:
        con.close()

    log.info("نماینده %s ربات خودش را وصل کرد: @%s", t["id"], who)
    return {"ok": True, "username": who,
            "note": "ربات تا نیم دقیقه‌ی دیگر خودش بالا می‌آید"}


@app.delete("/api/portal/bot")
def portal_bot_del(t: dict = Depends(portal_tenant)):
    """جداکردن ربات. نخِ در حال اجرا خودش تمیز خارج می‌شود."""
    con = _bot_rw()
    try:
        con.execute("UPDATE tenants SET bot_token=NULL, bot_username=NULL "
                    "WHERE id=?", (t["id"],))
        con.commit()
    finally:
        con.close()
    return {"ok": True}


@app.post("/api/portal/brand")
def portal_brand(payload: dict, t: dict = Depends(portal_tenant)):
    """
    برند رباتِ نماینده — فقط همان چند کلیدی که مال اوست.
    """
    p = payload or {}
    try:
        st = json.loads(t.get("settings") or "{}")
    except (json.JSONDecodeError, TypeError):
        st = {}
    if not isinstance(st, dict):
        st = {}

    touched = []
    for k in PORTAL_BRAND_KEYS:
        if k in p:
            st[k] = str(p[k] or "").strip()[:80]
            touched.append(k)
    if not touched:
        raise HTTPException(status_code=400, detail="چیزی برای تغییر نیست")

    con = _bot_rw()
    try:
        con.execute("UPDATE tenants SET settings=? WHERE id=?",
                    (json.dumps(st, ensure_ascii=False), t["id"]))
        con.commit()
    finally:
        con.close()
    return {"ok": True}



# ═══════════════════════════════════════════════════════════
#  پلن‌های رباتِ نماینده
#
#  رباتش بالا می‌آمد ولی مغازه‌اش خالی بود: جدول plans به مستاجر
#  محدود است و نماینده هیچ راهی برای ساختن پلن نداشت.
#
#  این‌جا قیمتی که او به *مشتری خودش* می‌فروشد تعیین می‌شود. قیمتی
#  که خودش به مالک می‌دهد چیز دیگری است و از نرخ‌های گروهش می‌آید —
#  آن یکی دست او نیست و نباید باشد.
# ═══════════════════════════════════════════════════════════

@app.get("/api/portal/bot-plans")
def portal_bot_plans(t: dict = Depends(portal_tenant)):
    """
    پلن‌هایی که ربات این نماینده می‌فروشد — و اینکه چه حجم‌هایی
    اجازه دارد.

    `gbCost` هزینه‌ی هر پله برای خودِ نماینده است. بدون آن، نماینده
    نمی‌داند دارد زیر قیمت می‌فروشد یا نه — و این چیزی است که
    فقط یک‌بار، آخر ماه، روی صورتحساب معلوم می‌شود.
    """
    mode, allowed, per_gb = _portal_gb_policy(t)
    _conf, _rates = _portal_rates(t)
    cost = {}
    for r in _rates:
        try:
            cost[str(int(r.get("gb", 0) or 0))] = int(r.get("price", 0) or 0)
        except (TypeError, ValueError):
            continue

    policy = {"gbMode": mode, "gbAllowed": allowed,
              "perGb": per_gb, "gbCost": cost}

    con = _bot_conn()
    if not con:
        return dict({"ready": False, "plans": []}, **policy)
    try:
        rows = [dict(r) for r in con.execute(
            "SELECT id, name, description, gb, days, ip_limit, price, "
            "is_active, is_trial, sort_order FROM plans "
            "WHERE tenant_id=? ORDER BY sort_order, id", (t["id"],))]
        return dict({"ready": True, "plans": rows,
                     "hasBot": bool(t.get("bot_token"))}, **policy)
    except Exception as e:
        return dict({"ready": False, "error": str(e)[:120], "plans": []},
                    **policy)
    finally:
        con.close()


@app.put("/api/portal/bot-plans")
def portal_bot_plans_save(payload: dict, t: dict = Depends(portal_tenant)):
    """
    ذخیره‌ی پلن‌های ربات نماینده.

    همه‌چیز به مستاجر خودش محدود است: به‌روزرسانی با
    `WHERE id=? AND tenant_id=?`، حذفِ آن‌هایی که در فهرست نیامده‌اند
    هم فقط داخل همین مستاجر. یعنی حتی اگر نماینده شناسه‌ی پلن
    نماینده‌ی دیگری را بفرستد، هیچ اتفاقی نمی‌افتد.
    """
    plans = (payload or {}).get("plans")
    if not isinstance(plans, list):
        raise HTTPException(status_code=400, detail="فهرست پلن نامعتبر است")
    if len(plans) > 40:
        raise HTTPException(status_code=400, detail="حداکثر ۴۰ پلن")

    # حجمِ مجاز از نرخ‌های مالک می‌آید، نه از دلخواهِ نماینده.
    #
    # این اعتبارسنجی **در بکند** است، نه فقط در رابط: رابط فقط
    # راحتی است و کسی می‌تواند درخواست را مستقیم بفرستد.
    mode, allowed, _per_gb = _portal_gb_policy(t)

    clean = []
    for i, p in enumerate(plans):
        if not isinstance(p, dict):
            continue
        name = str(p.get("name") or "").strip()[:60]
        if not name:
            raise HTTPException(status_code=400,
                                detail=f"پلن شماره {i + 1} نام ندارد")
        try:
            gb = max(0, int(p.get("gb") or 0))
            days = max(0, int(p.get("days") or 0))
            ip_limit = max(0, int(p.get("ip_limit") or 0))
            price = max(0, int(p.get("price") or 0))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400,
                                detail=f"عددهای پلن «{name}» نامعتبرند")

        if mode == "tiers" and gb not in allowed:
            # پله‌ها را *بگو*. «نامعتبر» بدون گفتنِ اینکه چه چیزی
            # معتبر است، یعنی حدس‌زدن.
            opts = "، ".join(("نامحدود" if g == 0 else str(g)) for g in allowed)
            raise HTTPException(
                status_code=400,
                detail=f"حجم {gb} گیگ در نرخ‌های شما نیست — "
                       f"یکی از این‌ها را بردارید: {opts}")

        clean.append({
            "id": p.get("id"), "name": name,
            "description": str(p.get("description") or "").strip()[:200],
            "gb": gb, "days": days, "ip_limit": ip_limit, "price": price,
            "is_active": 1 if p.get("is_active", True) else 0,
            # آزمایشی فقط دست مالک است: پلن رایگان یعنی کانفیگی که
            # کسی پولش را نمی‌دهد ولی روی سرور او ساخته می‌شود.
            "is_trial": 0,
            "sort": i,
        })

    con = _bot_rw()
    try:
        keep = [int(p["id"]) for p in clean if p.get("id")]
        if keep:
            ph = ",".join("?" * len(keep))
            con.execute(
                f"DELETE FROM plans WHERE tenant_id=? AND id NOT IN ({ph})",
                [t["id"]] + keep)
        else:
            con.execute("DELETE FROM plans WHERE tenant_id=?", (t["id"],))

        for p in clean:
            vals = (p["name"], p["description"], p["gb"], p["days"],
                    p["ip_limit"], p["price"], p["is_active"], p["is_trial"],
                    p["sort"])
            if p.get("id"):
                con.execute(
                    "UPDATE plans SET name=?,description=?,gb=?,days=?,"
                    "ip_limit=?,price=?,is_active=?,is_trial=?,sort_order=? "
                    "WHERE id=? AND tenant_id=?", vals + (p["id"], t["id"]))
            else:
                con.execute(
                    "INSERT INTO plans (name,description,gb,days,ip_limit,"
                    "price,is_active,is_trial,sort_order,tenant_id) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)", vals + (t["id"],))
        con.commit()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ذخیره نشد: {str(e)[:120]}")
    finally:
        con.close()
    return {"ok": True, "count": len(clean)}



# ═══════════════════════════════════════════════════════════
#  سفارش‌های نماینده — رسید و تایید
#
#  مشتریِ نماینده از رباتِ *او* سفارش می‌دهد و رسید می‌فرستد. تا
#  امروز تنها جایی که می‌شد تاییدش کرد گروه مدیریت تلگرام بود؛ اگر
#  نماینده گروه نداشت، سفارش برای همیشه در انتظار می‌ماند.
#
#  تاییدکردن یعنی: پول گرفته شده، کانفیگ ساخته شود، مشتری خبردار
#  شود. همان کاری که ربات می‌کند — و عمداً *همان کد* را صدا می‌زنیم،
#  نه یک نسخه‌ی دوم. مسیر پول دو پیاده‌سازی برنمی‌دارد؛ هر اصلاحی که
#  به یکی برسد و به دیگری نه، یک باگ بی‌صداست.
# ═══════════════════════════════════════════════════════════

_BOT_MODS = {}


def _bot_handlers():
    """
    ماژول handlers ربات، با bot/ روی مسیر.

    handlers با نام‌های مسطح import می‌کند (core، db، tg)، پس تا وقتی
    آن پوشه روی sys.path نباشد بارگذاری نمی‌شود.
    """
    if "handlers" in _BOT_MODS:
        return _BOT_MODS["handlers"]
    import sys as _sys
    bot_dir = str(Path(__file__).resolve().parent.parent / "bot")
    if bot_dir not in _sys.path:
        _sys.path.insert(0, bot_dir)
    try:
        import handlers as _h          # noqa: E402
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"منطق ربات بارگذاری نشد: {type(e).__name__}")
    _BOT_MODS["handlers"] = _h
    return _h


def _portal_bot_ctx(t):
    """
    زمینه‌ی ربات این نماینده — برای پیام‌دادن به مشتری و ساخت کانفیگ.

    بدون توکن ربات نمی‌شود به مشتری خبر داد، و تاییدِ بی‌خبر یعنی
    مشتری پولش را داده و هیچ‌چیز نمی‌بیند.
    """
    h = _bot_handlers()
    if not t.get("bot_token"):
        raise HTTPException(
            status_code=409,
            detail="برای تایید سفارش باید ربات خودتان را وصل کنید — "
                   "وگرنه مشتری خبردار نمی‌شود")
    row = _tenant_row(t["id"]) or t
    return h, h.Ctx(h.Bot(row["bot_token"]), row)


def _portal_order(t, oid):
    """سفارشی از مستاجر خودش — یا خطا."""
    con = _bot_conn()
    if not con:
        raise HTTPException(status_code=503, detail="دیتابیس ربات در دسترس نیست")
    try:
        r = con.execute(
            "SELECT * FROM orders WHERE id=? AND tenant_id=?",
            (oid, t["id"])).fetchone()
    finally:
        con.close()
    if not r:
        # همان پیام «پیدا نشد» برای سفارش نماینده‌ی دیگر: وگرنه
        # می‌شود از این‌جا فهمید چه شناسه‌هایی وجود دارند.
        raise HTTPException(status_code=404, detail="سفارش پیدا نشد")
    return dict(r)


@app.get("/api/portal/orders")
def portal_orders(status: str = "open", limit: int = 200,
                  t: dict = Depends(portal_tenant)):
    """
    سفارش‌های مشتری‌های این نماینده.

    پیش‌فرض فقط آن‌هایی که کاری می‌خواهند: رسید آمده و منتظر تایید
    است، یا هنوز رسیدی نیامده.

    `truncated` می‌گوید که سقف خورده — قبلاً فهرست بی‌صدا سر ۵۰ تا
    بریده می‌شد و نماینده فکر می‌کرد همین‌ها همه‌ی سفارش‌هایش است.
    """
    con = _bot_conn()
    if not con:
        return {"ready": False, "orders": []}
    want = {"open": ("pending", "awaiting"),
            "approved": ("approved",), "rejected": ("rejected", "expired")}
    picked = want.get(status, want["open"])
    ph = ",".join("?" * len(picked))
    cap = max(1, min(int(limit or 200), 500))
    try:
        rows = [dict(r) for r in con.execute(
            f"""SELECT o.*, u.tg_id, u.first_name, u.username,
                       p.name AS plan_name, p.gb, p.days
                  FROM orders o
                  JOIN users u ON u.id = o.user_id
             LEFT JOIN plans p ON p.id = o.plan_id
                 WHERE o.tenant_id=? AND o.status IN ({ph})
              ORDER BY o.id DESC LIMIT ?""",
            [t["id"]] + list(picked) + [cap])]
    except Exception as e:
        return {"ready": False, "error": str(e)[:120], "orders": []}
    finally:
        con.close()

    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "customer": r.get("first_name") or r.get("username") or "مشتری",
            "tgId": r.get("tg_id"),
            "kind": r.get("kind") or "new",
            "amount": r.get("amount") or 0,
            "planName": r.get("plan_name") or "—",
            "gb": r.get("gb"), "days": r.get("days"),
            "status": r.get("status"),
            "paidFrom": r.get("paid_from") or "card",
            "hasReceipt": bool(r.get("receipt_file")),
            "receiptText": r.get("receipt_text") or "",
            "createdAt": r.get("created_at"),
            "note": r.get("admin_note") or "",
        })
    return {"ready": True, "truncated": len(out) >= cap, "orders": out,
            "openCount": sum(1 for x in out if x["status"] == "awaiting")}


@app.get("/api/portal/order/{oid}/receipt")
def portal_receipt(oid: int, t: dict = Depends(portal_tenant)):
    """
    عکس رسید، از تلگرام و از راه رباتِ خودِ نماینده.

    فایل مستقیم پاس داده می‌شود نه آدرسش: آن آدرس توکن ربات را در
    خودش دارد و دادنش به مرورگر یعنی لو دادن توکن.
    """
    o = _portal_order(t, oid)
    _lp = _receipt_local(o.get("receipt_file"))
    if _lp:
        _blob = _lp.read_bytes()
        _e, _ct = _logo_kind(_blob)
        if _ct:
            return Response(content=_blob, media_type=_ct,
                            headers={"Cache-Control": "private, max-age=60"})

    if not o.get("receipt_file"):
        raise HTTPException(status_code=404, detail="این سفارش رسید عکسی ندارد")
    if not t.get("bot_token"):
        raise HTTPException(status_code=409, detail="ربات وصل نیست")

    import urllib.request
    tok = t["bot_token"]
    try:
        with urllib.request.urlopen(
                f"https://api.telegram.org/bot{tok}/getFile"
                f"?file_id={o['receipt_file']}", timeout=15) as r:
            info = json.loads(r.read().decode("utf-8", "replace"))
        path = ((info.get("result") or {}).get("file_path") or "")
        if not path:
            raise HTTPException(status_code=404, detail="تلگرام فایل را نداد")
        with urllib.request.urlopen(
                f"https://api.telegram.org/file/bot{tok}/{path}",
                timeout=30) as r:
            blob = r.read()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502,
                            detail=f"رسید گرفته نشد: {type(e).__name__}")

    kind = "image/jpeg"
    if path.lower().endswith(".png"):
        kind = "image/png"
    elif path.lower().endswith(".pdf"):
        kind = "application/pdf"
    return Response(content=blob, media_type=kind,
                    headers={"Cache-Control": "private, max-age=300"})


@app.post("/api/portal/order/{oid}/approve")
def portal_order_approve(oid: int, t: dict = Depends(portal_tenant)):
    """
    تایید سفارش — همان مسیری که ربات می‌رود.

    ادعای اتمی، ساخت کانفیگ، خبردادن به مشتری، پورسانت. هیچ‌کدام
    این‌جا دوباره نوشته نشده.
    """
    o = _portal_order(t, oid)
    if o.get("status") == "approved" and o.get("sub_id"):
        raise HTTPException(status_code=409,
                            detail="این سفارش قبلاً تایید شده و کانفیگش ساخته شده")

    h, ctx = _portal_bot_ctx(t)
    try:
        ok, note = h.approve_order(ctx, oid, admin_tg_id=0)
    except Exception as e:
        log.exception("تایید سفارش نماینده ناموفق")
        raise HTTPException(status_code=502, detail=f"تایید ناموفق: {str(e)[:140]}")

    if not ok:
        if note == getattr(h, "ORDER_BUSY", None):
            raise HTTPException(
                status_code=409,
                detail="این سفارش همین حالا از مسیر دیگری در حال پردازش است")
        raise HTTPException(status_code=400, detail=str(note)[:200])
    return {"ok": True, "id": oid}


@app.post("/api/portal/order/{oid}/reject")
def portal_order_reject(oid: int, payload: dict = None,
                        t: dict = Depends(portal_tenant)):
    """رد سفارش با دلیل — مشتری همان دلیل را می‌بیند."""
    o = _portal_order(t, oid)
    reason = str((payload or {}).get("reason") or "").strip()[:200]
    if not reason:
        raise HTTPException(status_code=400,
                            detail="دلیل رد را بنویسید — مشتری همین را می‌بیند")

    h, ctx = _portal_bot_ctx(t)
    try:
        done = h.do_reject(ctx, oid, 0, reason)
    except Exception as e:
        log.exception("رد سفارش نماینده ناموفق")
        raise HTTPException(status_code=502, detail=f"رد ناموفق: {str(e)[:140]}")
    if not done:
        raise HTTPException(status_code=409,
                            detail="رد نشد — کانفیگ این سفارش ساخته شده")
    return {"ok": True, "id": oid}



@app.get("/api/portal/config/{email}/qr")
def portal_qr(email: str, t: dict = Depends(portal_tenant)):
    """
    کیوآر لینک اشتراک — برای تحویل به مشتری.

    محلی ساخته می‌شود و هیچ‌جا نمی‌رود: لینک اشتراک عملاً رمز مشتری
    است و فرستادنش به یک کیوآرسازِ آنلاین یعنی دادن دسترسی کامل
    سرویس به آن سایت.
    """
    _portal_find(t, email)          # گروه سنجیده می‌شود
    base = _sub_base(t)
    if not base:
        raise HTTPException(status_code=409,
                            detail="آدرس پایه‌ی اشتراک تنظیم نشده")

    import sys as _sys
    bot_dir = str(Path(__file__).resolve().parent.parent / "bot")
    if bot_dir not in _sys.path:
        _sys.path.insert(0, bot_dir)
    try:
        import qr as _qr
    except Exception:
        raise HTTPException(status_code=503, detail="ساخت کیوآر در دسترس نیست")
    if not _qr.available():
        raise HTTPException(
            status_code=503,
            detail="کتابخانه‌ی segno نصب نیست — pip install segno")

    clients, _k, _e = _read_xui_clients()
    sub_id = email
    for cl in (clients or []):
        if cl.get("email") == email:
            sub_id = cl.get("subId") or email
            break

    png = _qr.make(f"{base}/{sub_id}")
    if not png:
        raise HTTPException(status_code=503, detail="کیوآر ساخته نشد")
    return Response(content=png, media_type="image/png",
                    headers={"Cache-Control": "private, max-age=600"})


def _portal_sales(tid, since):
    """
    فروشِ ربات همین نماینده. همیشه دیکشنری برمی‌گرداند، حتی اگر
    رباتی نداشته باشد.

    دو قاعده‌ای که جای دیگر هم اجرا می‌شوند و این‌جا هم باید:

      • تست رایگان خرید نیست. گرفتن تست خودش یک سفارشِ approved با
        مبلغ صفر می‌سازد؛ اگر کنار گذاشته نشود، «تعداد فروش» هر کسی
        را که دکمه‌ی تست را زده می‌شمارد.

      • «فروش» با «درآمد» یکی نیست. خریدی که از کیف پول پرداخت شده
        فروش هست ولی پول تازه‌ای با آن نرسیده — آن پول موقع شارژ
        رسیده. پس «دریافتی» فقط کارت را می‌شمارد.
    """
    empty = {"hasBot": False, "orders": 0, "sold": 0, "received": 0,
             "monthOrders": 0, "monthSold": 0, "pending": 0}
    con = _bot_conn()
    if not con:
        return empty
    try:
        real = (f"FROM orders o {SQL_PLAN_JOIN} "
                f"WHERE o.tenant_id=? AND {SQL_REAL_BUY}")

        tot = con.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(o.amount),0) s " + real,
            (tid,)).fetchone()
        mon = con.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(o.amount),0) s " + real
            + " AND o.created_at >= ?", (tid, since)).fetchone()
        rec = con.execute(
            "SELECT COALESCE(SUM(o.amount),0) s " + real
            + " AND o.paid_from='card'", (tid,)).fetchone()
        pend = con.execute(
            "SELECT COUNT(*) n FROM orders WHERE tenant_id=? "
            "AND status IN ('awaiting','review')", (tid,)).fetchone()
        any_row = con.execute(
            "SELECT 1 FROM orders WHERE tenant_id=? LIMIT 1", (tid,)).fetchone()

        return {
            "hasBot": bool(any_row),
            "orders": int(tot["n"] or 0),
            "sold": int(tot["s"] or 0),
            "received": int(rec["s"] or 0),
            "monthOrders": int(mon["n"] or 0),
            "monthSold": int(mon["s"] or 0),
            "pending": int(pend["n"] or 0),
        }
    except Exception:
        log.debug("خواندن فروش نماینده ناموفق", exc_info=True)
        return empty
    finally:
        con.close()


@app.get("/api/portal/stats")
def portal_stats(t: dict = Depends(portal_tenant)):
    """
    آمار واقعیِ کارِ نماینده.

    تا امروز فقط شمارش خشک بود: چند کانفیگ، چند تمدید. آن‌ها نمی‌گویند
    کدام مشتری دارد از دست می‌رود یا کدام حجمش تمام شده — که تنها
    چیزهایی‌اند که نماینده می‌تواند رویشان کاری بکند.
    """
    group = _portal_group(t)
    clients, _known, err = _read_xui_clients()
    if clients is None:
        raise HTTPException(status_code=400, detail=err)

    mine = [c for c in clients if (c.get("group") or "") == group]
    # نماینده همان مصرفی را ببیند که روی صورتحسابش می‌آید
    _with_total_usage(mine)
    now_ms = _epoch_ms(datetime.now())

    active = expired = soon = nearq = overq = never = 0
    used_b = quota_b = 0
    unlimited_q = 0
    for c in mine:
        used_b += c.get("usedTotal") or 0
        q = c.get("totalGB") or 0
        if q > 0:
            quota_b += q
            # درصد روی دوره‌ی جاری: «رو به اتمام» یعنی سهمیه‌ی همین
            # دوره دارد تمام می‌شود، نه اینکه تاریخاً چقدر مصرف شده
            pct = (c.get("used") or 0) * 100.0 / q
            if pct >= 100:
                overq += 1
            elif pct >= 80:
                nearq += 1
        else:
            unlimited_q += 1

        exp = _epoch_ms(c.get("expiry"))
        if not exp or exp <= 0:
            never += 1
            if c.get("enable"):
                active += 1
            continue
        days = (exp - now_ms) / 86400000.0
        if days < 0:
            expired += 1
        else:
            if c.get("enable"):
                active += 1
            if days <= 7:
                soon += 1

    # کارِ همین ماه — از دفترِ تمدیدها که حالا واقعی است
    first = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    renewals_m = 0
    bcon = _billing_conn()
    try:
        r = bcon.execute(
            "SELECT COALESCE(SUM(months),0) m FROM renewals "
            "WHERE group_key=? AND created_at >= ?", (group, first)).fetchone()
        renewals_m = int((r["m"] if r else 0) or 0)
    except Exception:
        renewals_m = 0
    finally:
        bcon.close()

    new_m = sum(1 for c in mine
                if str(c.get("createdAt") or "")[:10] >= first)

    # سریِ چهارده‌روزه — کارت‌های آمار پنل نماینده تا امروز فقط یک عدد
    # خشک بودند، در حالی که همان کامپوننتِ مشترک نمودارِ کوچک هم
    # می‌گیرد. عدد می‌گوید «۸۴»، نمودار می‌گوید «داشت بالا می‌رفت».
    days = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(13, -1, -1)]
    idx = {d: i for i, d in enumerate(days)}
    new_series = [0] * 14
    for c in mine:
        i = idx.get(str(c.get("createdAt") or "")[:10])
        if i is not None:
            new_series[i] += 1
    renew_series = [0] * 14
    bcon = _billing_conn()
    try:
        for row in bcon.execute(
                "SELECT substr(created_at,1,10) d, COUNT(*) n FROM renewals "
                "WHERE group_key=? AND substr(created_at,1,10) >= ? "
                "GROUP BY d", (group, days[0])).fetchall():
            i = idx.get(row["d"])
            if i is not None:
                renew_series[i] = int(row["n"] or 0)
    except Exception:
        # سریِ نمودار تزئینی است؛ نبودش نباید کل صفحه‌ی آمار را
        # بیندازد
        renew_series = [0] * 14
    finally:
        bcon.close()

    return {
        "series": {"new": new_series, "renew": renew_series},
        "total": len(mine),
        "active": active,
        "inactive": len(mine) - active,
        "expired": expired,
        "expiringSoon": soon,
        "neverExpires": never,
        "nearQuota": nearq,
        "overQuota": overq,
        "unlimitedQuota": unlimited_q,
        "usedGB": round(used_b / (1024 ** 3), 1),
        "quotaGB": round(quota_b / (1024 ** 3), 1),
        "usagePct": (round(used_b * 100.0 / quota_b, 1) if quota_b else None),
        "thisMonth": {"new": new_m, "renewals": renewals_m},
        # چیزهایی که همین حالا کاری می‌خواهند
        "needsAttention": soon + expired + overq,
        # فروشِ ربات خودش — تا امروز نماینده هیچ عددی از فروشش
        # نمی‌دید، با اینکه ربات و سفارش و رسید داشت.
        "sales": _portal_sales(t["id"], first),
    }


@app.post("/api/portal/logo")
def portal_logo_set(payload: dict, t: dict = Depends(portal_tenant)):
    """
    لوگوی خودِ نماینده.

    شناسه از نشستِ احراز‌شده می‌آید، نه از بدنه — وگرنه فرستادنِ
    شناسه‌ی نماینده‌ی دیگر کافی بود تا لوگوی او عوض شود.
    """
    return _logo_save(t["id"], payload)


@app.delete("/api/portal/logo")
def portal_logo_clear(t: dict = Depends(portal_tenant)):
    _logo_clear(t["id"])
    return {"ok": True}


@app.post("/api/portal/logout")
def portal_logout(x_portal_token: str = Header(None)):
    _PORTAL_SESSIONS.pop(str(x_portal_token or ""), None)
    return {"ok": True}


@app.get("/api/portal/me")
def portal_me(t: dict = Depends(portal_tenant)):
    """
    نماینده‌ی وارد‌شده. عمداً کم: نه توکن ربات، نه رمز پنل x-ui.
    """
    return {
        "id": t["id"],
        "name": t["name"],
        "slug": t.get("portal_slug"),
        "credit": t.get("credit"),
        "discount": t.get("credit_discount") or 0,
        "hasBot": bool(t.get("bot_token")),
        "botUsername": t.get("bot_username") or "",
        "logo": _logo_url(t["id"]),
    }


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/admin/firewall/preflight")
def firewall_preflight(x_admin_password: str = Header(...)):
    """
    قبل از روشن‌کردن فایروال: چه چیزی قطع می‌شود؟

    ترس از روشن‌کردن فایروال روی سرور راه دور کاملاً بجاست — یک
    قاعده‌ی جاافتاده یعنی قطع‌شدن SSH یا تانل، و بعد راهی برای
    برگشتن نیست مگر کنسول ارائه‌دهنده. این‌جا فهرست می‌شود.
    """
    check_auth(x_admin_password)
    fw = _fw_or_die()
    return fw.preflight()


@app.post("/api/admin/firewall/safe-enable")
def firewall_safe_enable(payload: dict, x_admin_password: str = Header(...)):
    """
    روشن‌کردن فایروال با بازگشت خودکار.

    اگر مدیر ظرف مهلت تعیین‌شده تایید نکند — یعنی اگر ارتباطش قطع
    شده باشد — فایروال خودش خاموش می‌شود.
    """
    check_auth(x_admin_password)
    fw = _fw_or_die()
    p = payload or {}
    ok, note, data = fw.safe_enable(
        confirm=bool(p.get("confirm")),
        rollback_minutes=int(p.get("rollbackMinutes") or 5),
        force=bool(p.get("force")))
    if not ok:
        raise HTTPException(status_code=400,
                            detail=note, headers={"X-Preflight": "1"})
    return {"ok": True, "note": note, **(data or {})}


@app.post("/api/admin/firewall/confirm-enabled")
def firewall_confirm_enabled(x_admin_password: str = Header(...)):
    """
    «هنوز وصلم» — ساعت‌شمار بازگشت لغو می‌شود.

    اینکه این درخواست اصلاً رسیده، خودش ثابت می‌کند ارتباط برقرار
    است؛ پس همین تایید کافی است.
    """
    check_auth(x_admin_password)
    fw = _fw_or_die()
    ok, note = fw.confirm_enabled()
    if not ok:
        raise HTTPException(status_code=400, detail=note)
    return {"ok": True, "note": note}


@app.get("/api/admin/firewall/rollback-state")
def firewall_rollback_state(x_admin_password: str = Header(...)):
    """آیا ساعت‌شمار بازگشت هنوز فعال است؟"""
    check_auth(x_admin_password)
    fw = _fw_or_die()
    return fw.rollback_state()


@app.post("/api/admin/billing/bulk-start")
def billing_bulk_start(payload: dict, x_admin_password: str = Header(...)):
    """
    تاریخ شروع را یک‌جا برای چند گروه تنظیم می‌کند.

    بدون این، مدیری که یازده گروه دارد باید یازده بار وارد تنظیمات
    هر گروه شود — و عملاً نمی‌شود، پس همه روی «یک ماه» می‌مانند و
    صورت‌حساب‌ها غلط درمی‌آیند.

    گروه‌هایی که از قبل تاریخ دارند دست‌نخورده می‌مانند، مگر
    overwrite خواسته شود؛ بازنویسی ناخواسته‌ی تاریخی که مدیر خودش
    گذاشته، بدتر از نداشتنش است.
    """
    check_auth(x_admin_password)
    p = payload or {}
    start = str(p.get("start") or "").strip()[:10]
    # [0-9] و نه \d — در پایتون \d رقم فارسی و عربی را هم می‌گیرد، پس
    # «۱۴۰۳-۰۶-۱۰» از این صافی رد می‌شد و به‌عنوان تاریخ میلادی ذخیره
    # می‌شد؛ بعدش هر محاسبه‌ای روی آن بی‌معنا بود.
    if not _re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$", start):
        raise HTTPException(status_code=400,
                            detail="تاریخ باید به شکل ۲۰۲۴-۰۹-۰۱ باشد")

    keys = p.get("groups")
    overwrite = bool(p.get("overwrite"))

    # نمای کلی خودش یک اتصال باز می‌کند و در client_seen می‌نویسد.
    # اگر وسط یک اتصال بازِ دیگر صدایش بزنیم، SQLite قفل می‌کند و کل
    # صفحه‌ی حسابداری با «database is locked» می‌ایستد. پس قبل از
    # بازکردن اتصال نوشتن حسابش می‌کنیم.
    if not keys:
        keys = (_billing_overview_impl().get("needStart") or [])

    con = _billing_conn()
    try:
        have = {r["group_key"]: r["period_start"] for r in
                con.execute("SELECT group_key, period_start FROM group_config")}

        changed, skipped = [], []
        for k in keys:
            if have.get(k) and not overwrite:
                skipped.append(k)
                continue
            con.execute(
                "INSERT INTO group_config (group_key, period_start) VALUES (?,?) "
                "ON CONFLICT(group_key) DO UPDATE SET period_start=excluded.period_start",
                (k, start))
            changed.append(k)
        con.commit()
    finally:
        con.close()

    note = f"تاریخ شروع {len(changed)} گروه روی {start} تنظیم شد"
    if skipped:
        note += f" — {len(skipped)} گروه که از قبل تاریخ داشتند دست‌نخورده ماند"
    return {"ok": True, "note": note, "changed": changed, "skipped": skipped}


@app.get("/api/agent/netid.py")
def agent_netid_module():
    """
    ماژول شناسایی آی‌پی برای سرورهای دیگر.

    monitor.py و firewall.py بدون این هم کار می‌کنند — جایگزین
    داخلی دارند — ولی تشخیص تانل و لوپ‌بکِ نگاشته بدون آن ناقص
    است. پس همراهشان فرستاده می‌شود.
    """
    p = _root_dir() / "backend" / "netid.py"
    if not p.exists():
        raise HTTPException(status_code=404, detail="ماژول netid پیدا نشد")
    return Response(content=p.read_text(encoding="utf-8"),
                    media_type="text/x-python")


@app.get("/api/admin/firewall/blocked")
def firewall_blocked_all(x_admin_password: str = Header(...)):
    """
    همه‌ی آدرس‌های بسته — از هر دو راه، در یک فهرست.

    مدیر نباید دو جای جدا نگاه کند تا بفهمد آدرسی بسته هست یا نه.
    """
    check_auth(x_admin_password)
    fw = _fw_or_die()
    return fw.blocked_overview()


@app.post("/api/admin/firewall/blackhole")
def firewall_blackhole(payload: dict, x_admin_password: str = Header(...)):
    """
    بستن یک آدرس بدون روشن‌کردن فایروال.

    روشن‌کردن ufw روی سرور راه دور تصمیم بزرگی است و خیلی‌ها —
    به‌درستی — با احتیاط با آن برخورد می‌کنند. ولی «این آدرس دارد
    سرور را می‌خورد و می‌خواهم همین حالا قطعش کنم» نباید منتظر آن
    تصمیم بماند.

    مسیر blackhole کاری با فایروال ندارد و فوری اثر می‌کند.
    """
    check_auth(x_admin_password)
    fw = _fw_or_die()
    p = payload or {}
    ip = str(p.get("ip") or "").strip()

    if p.get("unblock"):
        ok, note = fw.blackhole_remove(ip)
    else:
        ok, note = fw.blackhole_add(ip, note=p.get("note") or "از پنل نکسورا",
                                    protect=_auth_ip.get())

    if not ok:
        raise HTTPException(status_code=400, detail=note)
    return {"ok": True, "note": note}


@app.get("/api/admin/tunnel/node/{node_id}/diagnose")
def node_diagnose(node_id: int, x_admin_password: str = Header(...)):
    """
    چرا از این سرور گزارشی نمی‌آید.

    چرا این وجود دارد:
        دو بار برای همین مشکل حدس زدم و هر دو بار اشتباه بود، چون
        هیچ‌جا دیده نمی‌شد کار کجا می‌ایستد. صف کار چهار مرحله دارد —
        ثبت، برداشتن، اجرا، نتیجه — و هر کدام می‌تواند جای گیرکردن
        باشد.

        این‌جا هر چهار مرحله با زمان و متن خطا نشان داده می‌شود، پس
        دفعه‌ی بعد به‌جای حدس، جواب هست.
    """
    check_auth(x_admin_password)
    _need_tunnels()

    c = TUN.conn()
    try:
        node = c.execute("SELECT * FROM nodes WHERE id = ?",
                         (node_id,)).fetchone()
        if not node:
            raise HTTPException(status_code=404, detail="نود پیدا نشد")
        node = dict(node)

        jobs = [dict(r) for r in c.execute(
            """SELECT id, action, status, created_at, taken_at, done_at, result
               FROM jobs WHERE node_id = ? ORDER BY id DESC LIMIT 15""",
            (node_id,))]
    finally:
        c.close()

    last_seen = node.get("last_seen")
    age = None
    if last_seen:
        try:
            age = int((datetime.now()
                       - datetime.fromisoformat(str(last_seen))).total_seconds())
        except Exception:
            age = None

    ver = (node.get("agent_version") or "").strip()

    steps = []

    # ۱) ایجنت اصلاً خبر می‌دهد؟
    if age is None:
        steps.append({"step": "چک‌این ایجنت", "ok": False,
                      "note": "این نود هرگز به پنل وصل نشده",
                      "fix": "اسکریپت نصب ایجنت را روی آن سرور اجرا کنید"})
    elif age > 180:
        steps.append({"step": "چک‌این ایجنت", "ok": False,
                      "note": f"آخرین خبر {age // 60} دقیقه پیش بود",
                      "fix": "روی آن سرور: systemctl status nexora-agent"})
    else:
        steps.append({"step": "چک‌این ایجنت", "ok": True,
                      "note": f"{age} ثانیه پیش"})

    # ۲) نسخه‌ی ایجنت
    if not ver:
        steps.append({"step": "نسخه‌ی ایجنت", "ok": False,
                      "note": "ایجنت نسخه‌اش را گزارش نمی‌کند — یعنی خیلی قدیمی است",
                      "fix": "دکمه‌ی «به‌روزرسانی ایجنت» را بزنید"})
    elif _older_than(ver, "1.5.0"):
        steps.append({"step": "نسخه‌ی ایجنت", "ok": False,
                      "note": f"نسخه‌ی {ver} دستور مانیتورینگ را نمی‌شناسد",
                      "fix": "دکمه‌ی «به‌روزرسانی ایجنت» را بزنید"})
    else:
        steps.append({"step": "نسخه‌ی ایجنت", "ok": True, "note": ver})

    # ۳) کار مانیتورینگ به کجا رسید
    mon = [j for j in jobs if j["action"] in ("sysmon", "firewall")]
    if not mon:
        steps.append({"step": "درخواست مانیتورینگ", "ok": False,
                      "note": "هیچ درخواستی برای این نود ثبت نشده",
                      "fix": "دکمه‌ی «گزارش تازه» را بزنید"})
    else:
        last = mon[0]
        st = last["status"]
        if st == "queued":
            steps.append({"step": "برداشتن کار", "ok": False,
                          "note": "کار در صف مانده و ایجنت برش نداشته",
                          "fix": "یعنی ایجنت وصل نیست — مرحله‌ی اول را ببینید"})
        elif st == "taken":
            steps.append({"step": "اجرای کار", "ok": False,
                          "note": "ایجنت کار را برداشته ولی نتیجه‌ای نفرستاده",
                          "fix": "روی آن سرور: journalctl -u nexora-agent -n 50"})
        elif st == "failed":
            steps.append({"step": "اجرای کار", "ok": False,
                          "note": str(last.get("result") or "")[:300],
                          "fix": "اگر می‌گوید تابعی پیدا نشد، ایجنت را به‌روز کنید"})
        else:
            steps.append({"step": "اجرای کار", "ok": True,
                          "note": f"کار #{last['id']} انجام شد"})

    # ۴) گزارش ذخیره‌شده
    saved = TUN.get_sysmon(node_id)
    if not saved:
        steps.append({"step": "گزارش ذخیره‌شده", "ok": False,
                      "note": "هیچ گزارشی ذخیره نشده"})
    else:
        steps.append({"step": "گزارش ذخیره‌شده", "ok": True,
                      "note": f"آخرین گزارش: {saved.get('at')}"})

    return {
        "node": {"id": node["id"], "name": node.get("name"),
                 "host": node.get("host"), "version": ver or None,
                 "lastSeen": last_seen, "ageSeconds": age},
        "steps": steps,
        "healthy": all(s["ok"] for s in steps),
        "jobs": jobs,
    }


@app.post("/api/admin/firewall/blackhole/bulk")
def firewall_blackhole_bulk(payload: dict, x_admin_password: str = Header(...)):
    """
    بستن یا بازکردن دسته‌ای آدرس‌ها.

    وقتی یک اسکن با صد آدرس می‌آید، واردکردن دستی صدتا نه شدنی است
    نه بی‌خطا.
    """
    check_auth(x_admin_password)
    fw = _fw_or_die()
    p = payload or {}

    raw = p.get("ips")
    if isinstance(raw, str):
        raw = [ln for ln in raw.replace(",", "\n").splitlines()]
    if not isinstance(raw, list) or not raw:
        raise HTTPException(status_code=400, detail="فهرستی از آدرس‌ها بفرستید")
    if len(raw) > 2000:
        raise HTTPException(status_code=400,
                            detail="حداکثر ۲۰۰۰ آدرس در هر بار")

    return fw.blackhole_bulk(raw, protect=_auth_ip.get(),
                             note=p.get("note") or "ورودی دسته‌ای",
                             remove=bool(p.get("unblock")))


@app.get("/api/admin/firewall/blackhole/export")
def firewall_blackhole_export(x_admin_password: str = Header(...)):
    """فهرست بسته‌شده‌ها به‌شکل فایل متنی."""
    check_auth(x_admin_password)
    fw = _fw_or_die()
    return Response(
        content=fw.blackhole_export(),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition":
                 "attachment; filename=nexora-blocked-ips.txt"})


@app.get("/api/admin/firewall/blackhole/verify")
def firewall_blackhole_verify(ip: str, x_admin_password: str = Header(...)):
    """
    واقعاً بسته شده؟

    از خود کرنل می‌پرسد، نه از فایلی که خودمان نوشته‌ایم — «پیام
    موفقیت دیدم» با «بسته شده» یکی نیست.
    """
    check_auth(x_admin_password)
    fw = _fw_or_die()
    return fw.blackhole_verify(ip)
