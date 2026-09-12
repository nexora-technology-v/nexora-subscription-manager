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


def _auth_lines(hours=24):
    """
    خطوط لاگ احراز هویت در بازه‌ی خواسته‌شده.

    اول journald، بعد auth.log. اگر هیچ‌کدام نبود، رشته‌ی خالی —
    نبودِ لاگ نباید صفحه را از کار بیندازد.
    """
    if shutil.which("journalctl"):
        out = _run(f"journalctl -u ssh -u sshd --since '-{int(hours)} hours' "
                   "--no-pager -q 2>/dev/null")
        if out.strip():
            return out

    for path in ("/var/log/auth.log", "/var/log/secure"):
        out = _run(f"tail -n 20000 {path} 2>/dev/null")
        if out.strip():
            return out
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
        stamp = line[:15]

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
