#!/usr/bin/env python3
"""
تست فایروال.

چرا وجود دارد:
    این ماژول می‌تواند دسترسی SSH مدیر به سرور را قطع کند. اگر
    فایروال روشن شود و قاعده‌ای پورت ۲۲ را باز نگذاشته باشد، راه
    برگشتی جز کنسول ارائه‌دهنده نمی‌ماند. نگهبانِ همین حالت، و
    اعتبارسنجی ورودی‌ها، این‌جا تست می‌شوند.

اجرا:  python3 tools/test-firewall.py
"""
import os
import sys

G, R, D, X = "\033[38;5;42m", "\033[38;5;203m", "\033[38;5;245m", "\033[0m"
_ok = _fail = 0

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
import firewall as F   # noqa: E402


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


SAMPLE = """Status: active

     To                         Action      From
     --                         ------      ----
[ 1] 22/tcp                     ALLOW IN    Anywhere
[ 2] 443/tcp                    ALLOW IN    Anywhere
[ 3] 2053/tcp                   ALLOW IN    Anywhere
[ 4] Anywhere                   DENY IN     91.99.12.4
[ 5] 22/tcp (v6)                ALLOW IN    Anywhere (v6)
"""

head("خواندن قواعد")
rules = F._parse_status(SAMPLE)
check("همه‌ی قواعد خوانده شدند", len(rules) == 5, str(len(rules)))
check("شماره‌ی قاعده درست است", rules[0]["num"] == 1)
check("پورت و پروتکل جدا شدند",
      rules[0]["port"] == 22 and rules[0]["proto"] == "tcp",
      f"{rules[0]['port']}/{rules[0]['proto']}")
check("عمل درست خوانده شد", rules[3]["action"] == "DENY", rules[3]["action"])
check("مبدأ درست خوانده شد", rules[3]["source"] == "91.99.12.4",
      rules[3]["source"])
check("SSH حیاتی علامت خورد", rules[0]["critical"] is True)
check("پورت عادی حیاتی نیست", rules[1]["critical"] is False)
check("قاعده‌ی حیاتی توضیح دارد", "SSH" in rules[0]["note"], rules[0]["note"])

head("نگهبان SSH")
no_ssh = [r for r in rules if r["port"] != 22]
check("روشن‌کردن بدون قاعده‌ی SSH خطرناک است",
      F._ssh_would_break(no_ssh, False) is True)
check("با قاعده‌ی SSH خطری نیست",
      F._ssh_would_break(rules, False) is False)
check("فایروالِ از قبل روشن، دوباره بررسی نمی‌شود",
      F._ssh_would_break(no_ssh, True) is False)

limit_ssh = [{"port": 22, "action": "LIMIT"}]
check("قاعده‌ی LIMIT هم SSH را باز نگه می‌دارد",
      F._ssh_would_break(limit_ssh, False) is False)

deny_ssh = [{"port": 22, "action": "DENY"}]
check("قاعده‌ی DENY روی ۲۲ محافظت حساب نمی‌شود",
      F._ssh_would_break(deny_ssh, False) is True)

head("اعتبارسنجی ورودی")
cases = [
    ("پورت غیرعددی", F.add_rule("خراب"), "شماره پورت نامعتبر"),
    ("پورت خارج از بازه", F.add_rule(99999), "پورت باید"),
    ("پورت صفر", F.add_rule(0), "پورت باید"),
    ("عمل نامعتبر", F.add_rule(80, action="نابود کن"), "عمل نامعتبر"),
    ("پروتکل نامعتبر", F.add_rule(80, proto="sctp"), "پروتکل نامعتبر"),
    ("مبدأ نامعتبر", F.add_rule(80, source="; rm -rf /"), "آدرس مبدأ نامعتبر"),
]
for label, (ok, note), expect in cases:
    check(label + " رد می‌شود", (not ok) and expect in note, note[:44])

ok, note = F.block_ip("نه‌آی‌پی")
check("بستن آدرس نامعتبر رد می‌شود", (not ok) and "نامعتبر" in note, note[:40])

head("پیشنهاد قواعد")

_avail, _status = F.available, F.status
F.available = lambda: True
F.status = lambda: {"ready": True, "installed": True, "active": True,
                    "sshProtected": True,
                    "rules": [{"port": 443, "action": "ALLOW"}]}

PORTS = [
    {"port": 22, "proto": "tcp", "process": "sshd", "public": True, "known": "SSH"},
    {"port": 443, "proto": "tcp", "process": "nginx", "public": True, "known": "HTTPS"},
    {"port": 8443, "proto": "tcp", "process": "xray", "public": True, "known": "Xray"},
    {"port": 23, "proto": "tcp", "process": "telnetd", "public": True, "known": ""},
    {"port": 3306, "proto": "tcp", "process": "mysqld", "public": True, "known": ""},
    {"port": 5432, "proto": "tcp", "process": "postgres", "public": False, "known": ""},
]
s = F.suggest(PORTS)

keep_ports = {k["port"] for k in s["keep"]}
close_ports = {k["port"] for k in s["close"]}
already = {a["port"] for a in s["already"]}

check("SSH در فهرست باز ماندن است", 22 in keep_ports, str(sorted(keep_ports)))
check("Xray باز می‌ماند", 8443 in keep_ports)
check("telnet بسته پیشنهاد می‌شود", 23 in close_ports, str(sorted(close_ports)))
check("mysql بسته پیشنهاد می‌شود", 3306 in close_ports)
check("پورت فقط داخلی اصلاً پیشنهاد نمی‌شود",
      5432 not in keep_ports and 5432 not in close_ports)
check("پورتی که از قبل قاعده دارد دوباره پیشنهاد نمی‌شود",
      443 in already and 443 not in keep_ports and 443 not in close_ports)
check("هر پیشنهاد دلیل دارد",
      all(x.get("why") for x in s["keep"] + s["close"]))
check("SSH دلیلش را توضیح می‌دهد",
      any("SSH" in k["why"] for k in s["keep"] if k["port"] == 22))

ok, note, res = F.apply_plan(s["close"], confirm=False)
check("اعمال بدون تایید رد می‌شود", (not ok) and "confirm" in note, note[:44])

F.available, F.status = _avail, _status

head("رفتار بدون ufw")
_real = F.available
F.available = lambda: False
st = F.status()
check("بدون ufw خطا نمی‌دهد", st.get("ready") is False and "rules" in st)
check("راهنمای نصب می‌دهد", "ufw" in (st.get("hint") or ""), st.get("hint"))
ok, note = F.enable()
check("روشن‌کردن بدون ufw ناموفق و بی‌خطر است", not ok, note[:40])
F.available = _real

print(f"\n{D}{'─' * 46}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
