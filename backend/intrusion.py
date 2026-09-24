"""
تشخیص تلاش برای نفوذ — چه کسی دارد در می‌زند و از کجا.

چرا وجود دارد:
    هر سرور عمومی روی اینترنت، شبانه‌روز هدف اسکن و بروت‌فورس است.
    این عادی است و به‌خودی‌خود ترسناک نیست. چیزی که خطرناک است،
    ندیدنِ آن است: مدیر نمی‌داند کدام IP هزار بار رمز اشتباه زده،
    و مهم‌تر — نمی‌داند کدام‌یک از این IPها در واقع مشتری خودش است
    که رمزش را اشتباه می‌زند یا اسکریپتش خراب شده.

    بستن IP یک مشتری یعنی از دست دادن او. پس این ماژول هر IP را با
    فهرست IPهای متصلِ سرویس مقایسه می‌کند و صریح می‌گوید کدام «آشنا»
    است و کدام غریبه.

منابع:
    · journalctl -u ssh   (رایج‌ترین روی دبیان/اوبونتو)
    · /var/log/auth.log   (اگر journald نبود)
    · lastb               (ورودهای ناموفق ثبت‌شده در btmp)
"""

from datetime import datetime, timedelta
import re
import shutil
import subprocess
import time
from collections import defaultdict

#: بیش از این تعداد تلاش ناموفق یعنی بروت‌فورس، نه اشتباه تایپی
BRUTE_THRESHOLD = 10

#: بیش از این، دیگر «تلاش» نیست؛ حمله‌ی فعال است
HEAVY_THRESHOLD = 100

_FAIL_PATTERNS = [
    # Failed password for root from 1.2.3.4 port 55555 ssh2
    re.compile(r"Failed password for (?:invalid user )?(\S+) from "
               r"([0-9a-fA-F:.]+) port"),
    # Invalid user admin from 1.2.3.4 port 55555
    re.compile(r"Invalid user (\S+) from ([0-9a-fA-F:.]+) port"),
    # Connection closed by authenticating user root 1.2.3.4 port ...
    re.compile(r"Connection closed by authenticating user (\S+) "
               r"([0-9a-fA-F:.]+) port"),
]

_ACCEPT = re.compile(r"Accepted \S+ for (\S+) from ([0-9a-fA-F:.]+) port")


def _run(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return p.stdout or ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def _ran_ok(cmd, timeout=20):
    """مثل _run، ولی می‌گوید دستور موفق بود یا نه: (موفق, خروجی)"""
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return p.returncode == 0, (p.stdout or "")
    except (subprocess.TimeoutExpired, OSError):
        return False, ""


def _within(line, cutoff):
    """
    آیا این خط لاگ از cutoff به بعد است؟

    دو قالب: syslog («Sep 12 16:18:20» بدون سال) و ISO.

    syslog سال ندارد، پس باید حدسش زد. حدسِ درست، *تازه‌ترین* سالی
    است که این تاریخ را در آینده نمی‌اندازد — نه سالِ cutoff.

    قبلاً سالِ cutoff فرض می‌شد و فقط حالتِ «در آینده افتاد» یک سال
    عقب برده می‌شد. آن یک طرفِ ماجرا را می‌گرفت و طرف دیگر را نه:

        حالا: ۱ ژانویه‌ی ۲۰۲۶، ساعت ۰۰:۳۰
        cutoff: ۳۱ دسامبر ۲۰۲۵، ساعت ۰۰:۳۰
        خط لاگ: «Jan  1 00:10» — یعنی بیست دقیقه پیش

        با سالِ cutoff می‌شد ۱ ژانویه‌ی ۲۰۲۵، یعنی تقریباً یک سال
        *پیش از* cutoff — و خط دور انداخته می‌شد.

    یعنی در بیست‌وچهار ساعتِ اول هر سال، حمله‌های همان روز اصلاً
    گزارش نمی‌شدند. برای صفحه‌ای که کارش دیدنِ حمله است، بدترین
    زمانِ ممکن برای کور بودن.

    خطی که تاریخش خوانده نشود نگه داشته می‌شود: انداختنش یعنی
    بی‌صدا داده از دست دادن، و این‌جا همان چیزی است که می‌خواهیم
    از آن دور بمانیم.
    """
    when = _line_time(line, cutoff)
    return True if when is None else when >= cutoff


def _line_time(line, cutoff=None):
    """
    زمانِ یک خطِ لاگ، یا None — همان قاعده‌ای که _within با آن فیلتر
    می‌کند، تا زمانِ نمایش‌داده‌شده و زمانِ فیلتر یکی باشند.
    """
    cutoff = cutoff or (datetime.now() - timedelta(days=1))
    head = line[:32]
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})", head)
    if m:
        try:
            return datetime(*(int(g) for g in m.groups()))
        except ValueError:
            return None

    m = re.match(r"([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})",
                  head)
    if not m:
        return None
    try:
        mon = _MONTHS.index(m.group(1)) + 1
    except ValueError:
        return None
    # یک روز ارفاق برای اختلاف ساعتِ سرور و منطقه‌ی زمانی لاگ
    limit = datetime.now() + timedelta(days=1)
    when = None
    for year in (cutoff.year + 1, cutoff.year, cutoff.year - 1):
        try:
            cand = datetime(year, mon, int(m.group(2)), int(m.group(3)),
                            int(m.group(4)), int(m.group(5)))
        except ValueError:
            continue        # ۲۹ فوریه در سالی که کبیسه نیست
        if cand > limit:
            continue
        # تازه‌ترین سالی که این تاریخ را در آینده نمی‌اندازد
        if when is None or cand > when:
            when = cand
    return when


_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _auth_lines(hours=24):
    """
    خطوط لاگ احراز هویت در بازه‌ی خواسته‌شده.

    اول journald، بعد auth.log. اگر هیچ‌کدام نبود، رشته‌ی خالی —
    نبودِ لاگ نباید صفحه را از کار بیندازد.
    """
    if shutil.which("journalctl"):
        ok, out = _ran_ok(
            f"journalctl -u ssh -u sshd --since '-{int(hours)} hours' "
            "--no-pager -q")
        if ok:
            # موفق ولی خالی یعنی در این بازه چیزی نبوده — یک روز آرام.
            # قبلاً این حالت هم به فایل می‌افتاد و تاریخچه‌ی کهنه را
            # به‌جای «هیچ» نشان می‌داد.
            return out

    # فایل، با همان بازه. tail تنها اندازه را محدود می‌کند نه زمان را،
    # پس بدون این فیلتر صفحه می‌گفت «۲۴ ساعت گذشته» و تلاش‌های چند
    # هفته پیش را نشان می‌داد — با شمارش‌های بادکرده.
    cutoff = datetime.now() - timedelta(hours=int(hours))
    for path in ("/var/log/auth.log", "/var/log/secure"):
        out = _run(f"tail -n 20000 {path} 2>/dev/null")
        if out.strip():
            kept = [ln for ln in out.splitlines() if _within(ln, cutoff)]
            return "\n".join(kept) + ("\n" if kept else "")
    return ""


def _is_private(ip):
    """IPهای شبکه‌ی داخلی — هرگز به‌عنوان مهاجم گزارش نمی‌شوند."""
    if ip.startswith(("10.", "127.", "192.168.", "::1", "fe80:", "fc", "fd")):
        return True
    if ip.startswith("172."):
        try:
            return 16 <= int(ip.split(".")[1]) <= 31
        except (IndexError, ValueError):
            return False
    return False


def ssh_attempts(hours=24, known_ips=None):
    """
    تلاش‌های ناموفق ورود SSH، گروه‌شده بر اساس IP.

    known_ips مجموعه‌ای از IPهایی است که همین حالا به سرویس وصل‌اند —
    یعنی به‌احتمال زیاد مشتری‌اند. هر IP که در آن باشد با پرچم
    «آشنا» برمی‌گردد تا مدیر تصادفی مشتری خودش را نبندد.
    """
    known = set(known_ips or ())
    text = _auth_lines(hours)

    if not text.strip():
        return {"available": False,
                "note": "لاگ SSH خوانده نشد — ممکن است دسترسی root لازم باشد",
                "attempts": [], "total": 0, "accepted": []}

    by_ip = defaultdict(lambda: {"count": 0, "users": defaultdict(int),
                                 "first": None, "last": None})
    accepted = []

    for line in text.splitlines():
        # ISO، نه ۱۵ نویسه‌ی اولِ خط: روی لاگِ RFC 3339 (اوبونتو ۲۴)
        # «۲۰۲۶-۰۹-۲۴T۱۲:۰» بریده می‌شد، و قالبِ syslog سال نداشت و در
        # رابط میلادی و خام دیده می‌شد
        _t = _line_time(line)
        stamp = _t.isoformat(timespec="seconds") if _t else line[:15]

        for pat in _FAIL_PATTERNS:
            m = pat.search(line)
            if not m:
                continue
            user, ip = m.group(1), m.group(2)
            if _is_private(ip):
                break
            rec = by_ip[ip]
            rec["count"] += 1
            rec["users"][user] += 1
            rec["first"] = rec["first"] or stamp
            rec["last"] = stamp
            break

        ok = _ACCEPT.search(line)
        if ok and not _is_private(ok.group(2)):
            accepted.append({"user": ok.group(1), "ip": ok.group(2),
                             "at": stamp})

    out = []
    for ip, rec in by_ip.items():
        users = sorted(rec["users"].items(), key=lambda kv: -kv[1])
        out.append({
            "ip": ip,
            "count": rec["count"],
            "users": [u for u, _ in users[:5]],
            "top_user": users[0][0] if users else "",
            "first": rec["first"],
            "last": rec["last"],
            "known": ip in known,
            "severity": ("heavy" if rec["count"] >= HEAVY_THRESHOLD
                         else "brute" if rec["count"] >= BRUTE_THRESHOLD
                         else "noise"),
        })

    out.sort(key=lambda r: -r["count"])

    return {
        "available": True,
        "hours": hours,
        "attempts": out,
        "total": sum(r["count"] for r in out),
        "attackers": sum(1 for r in out if r["severity"] != "noise"),
        "customers": [r for r in out if r["known"]],
        # ورودهای موفق هم مهم‌اند: اگر IP ناآشنایی موفق شده باشد،
        # این دیگر تلاش نیست — نفوذ است.
        "accepted": accepted[-10:],
    }


def ssh_hardening():
    """
    وضعیت سفت‌بودن تنظیمات SSH و کاری که باید کرد.

    هر مورد یک راه‌حل صریح دارد، نه توصیه‌ی کلی. مدیری که وسط
    اختلال است نباید مجبور شود دنبال دستور بگردد.
    """
    cfg = _run("cat /etc/ssh/sshd_config 2>/dev/null "
               "/etc/ssh/sshd_config.d/*.conf 2>/dev/null")
    checks = []

    def val(key, default):
        m = re.findall(rf"^\s*{key}\s+(\S+)", cfg, re.M | re.I)
        return m[-1].lower() if m else default

    root_login = val("PermitRootLogin", "prohibit-password")
    checks.append({
        "key": "root_login",
        "title": "ورود مستقیم با کاربر root",
        "ok": root_login in ("no", "prohibit-password", "without-password"),
        "value": root_login,
        "why": "بیشترِ بروت‌فورس‌ها فقط root را امتحان می‌کنند. بستن آن "
               "به‌تنهایی اغلب حجم تلاش‌ها را چند برابر کم می‌کند.",
        "fix": "sed -i 's/^#\\?PermitRootLogin.*/PermitRootLogin "
               "prohibit-password/' /etc/ssh/sshd_config && systemctl "
               "reload ssh",
    })

    pw_auth = val("PasswordAuthentication", "yes")
    checks.append({
        "key": "password_auth",
        "title": "ورود با رمز عبور",
        "ok": pw_auth == "no",
        "value": pw_auth,
        "why": "تا وقتی رمز قبول می‌شود، بروت‌فورس معنی دارد. با کلید "
               "SSH، حدس‌زدن رمز بی‌فایده می‌شود.",
        "fix": "اول کلید SSH خودتان را اضافه کنید، بعد: "
               "sed -i 's/^#\\?PasswordAuthentication.*/"
               "PasswordAuthentication no/' /etc/ssh/sshd_config && "
               "systemctl reload ssh",
        "danger": "اگر کلید SSH نگذاشته باشید، بعد از این دیگر نمی‌توانید "
                  "وارد سرور شوید.",
    })

    port = val("Port", "22")
    checks.append({
        "key": "port",
        "title": "پورت SSH",
        "ok": port != "22",
        "value": port,
        "why": "عوض‌کردن پورت جلوی حمله‌ی هدفمند را نمی‌گیرد، ولی اسکنرهای "
               "خودکار که فقط ۲۲ را می‌زنند کنار می‌روند و لاگ تمیز می‌شود.",
        "fix": "در /etc/ssh/sshd_config پورت را عوض کنید، در فایروال باز "
               "کنید، و تا وقتی با پورت جدید وارد نشده‌اید نشست فعلی را نبندید.",
    })

    f2b = bool(shutil.which("fail2ban-client"))
    banned = 0
    if f2b:
        out = _run("fail2ban-client status sshd 2>/dev/null")
        m = re.search(r"Currently banned:\s*(\d+)", out)
        banned = int(m.group(1)) if m else 0
    checks.append({
        "key": "fail2ban",
        "title": "fail2ban",
        "ok": f2b,
        "value": (f"نصب است — {banned} IP مسدود" if f2b else "نصب نیست"),
        "why": "IPهایی که پشت سر هم رمز اشتباه می‌زنند را خودکار و موقت "
               "می‌بندد. بهترین نسبت اثر به زحمت در این فهرست همین است.",
        "fix": "apt-get install -y fail2ban && systemctl enable --now fail2ban",
    })

    return {"checks": checks,
            "score": sum(1 for c in checks if c["ok"]),
            "total": len(checks)}


def summary(known_ips=None, hours=24):
    """همه‌چیز در یک فراخوانی — برای صفحه‌ی فایروال پنل."""
    att = ssh_attempts(hours=hours, known_ips=known_ips)
    hard = ssh_hardening()

    advice = []
    if att.get("available"):
        heavy = [a for a in att["attempts"] if a["severity"] == "heavy"]
        if heavy:
            advice.append({
                "level": "crit",
                "text": f"{len(heavy)} آی‌پی بیش از {HEAVY_THRESHOLD} بار "
                        "رمز اشتباه زده‌اند. اینها اسکنر خودکارند و با "
                        "بستنشان هیچ مشتری‌ای را از دست نمی‌دهید.",
                "action": "block_heavy",
            })
        if att.get("customers"):
            advice.append({
                "level": "warn",
                "text": f"{len(att['customers'])} از این آی‌پی‌ها همین حالا "
                        "به سرویس شما وصل‌اند — یعنی احتمالاً مشتری خودتان "
                        "است که رمز اشتباه می‌زند. اینها را نبندید.",
                "action": None,
            })
    for c in hard["checks"]:
        if not c["ok"]:
            advice.append({"level": "warn", "text": c["why"],
                           "fix": c["fix"], "title": c["title"],
                           "danger": c.get("danger"), "action": None})

    return {"ssh": att, "hardening": hard, "advice": advice,
            "checked_at": int(time.time())}
