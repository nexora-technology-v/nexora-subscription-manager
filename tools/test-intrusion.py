#!/usr/bin/env python3
"""
تشخیص بروت‌فورس SSH و جداکردن مشتری از مهاجم.

چرا وجود دارد:
    خطرناک‌ترین اشتباه این صفحه بستنِ آی‌پی مشتری خودمان است. یک
    مشتری که رمز SSH ندارد و اشتباهی وصل می‌شود، در لاگ دقیقاً شبیه
    مهاجم است. تنها تفاوتش این است که همین حالا به سرویس وصل است.

    این تست مطمئن می‌شود آن تفاوت هرگز گم نشود.

اجرا:  python3 tools/test-intrusion.py
"""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "intrusion", os.path.join(ROOT, "backend", "intrusion.py"))
IN = importlib.util.module_from_spec(spec)
spec.loader.exec_module(IN)

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


# لاگ نمونه — شکل واقعی خطوط sshd روی دبیان
SAMPLE = "\n".join(
    # یک آی‌پی با ۱۲۰ تلاش — باید «حمله‌ی سنگین» شناخته شود
    [f"Sep 12 03:1{i % 10}:22 srv sshd[1]: Failed password for root "
     f"from 45.9.148.7 port 5000{i} ssh2" for i in range(120)]
    + [f"Sep 12 04:00:0{i} srv sshd[2]: Invalid user admin from "
       f"185.220.101.5 port 600{i}" for i in range(15)]
    + ["Sep 12 05:00:00 srv sshd[3]: Failed password for ubuntu "
       "from 5.200.10.20 port 7000 ssh2"] * 12
    + ["Sep 12 05:10:00 srv sshd[4]: Failed password for root "
       "from 192.168.1.50 port 7100 ssh2"] * 30
    + ["Sep 12 06:00:00 srv sshd[5]: Accepted publickey for root "
       "from 91.99.12.4 port 7200 ssh2"]
    + ["Sep 12 06:05:00 srv sshd[6]: Failed password for git "
       "from 2001:db8::1 port 7300 ssh2"] * 3
)

IN._auth_lines = lambda hours=24: SAMPLE

head("گروه‌بندی تلاش‌ها")

res = IN.ssh_attempts(hours=24)
check("لاگ خوانده شد", res["available"])
by = {a["ip"]: a for a in res["attempts"]}

check("آی‌پی‌ها گروه شدند", len(res["attempts"]) >= 4,
      f"{len(res['attempts'])} آی‌پی")
check("۱۸۵.۲۲۰.۱۰۱.۵ شمرده شد", by.get("185.220.101.5", {}).get("count") == 15)
check("۵.۲۰۰.۱۰.۲۰ شمرده شد", by.get("5.200.10.20", {}).get("count") == 12)
check("آی‌پی شبکه‌ی داخلی نادیده گرفته شد", "192.168.1.50" not in by,
      "۳۰ تلاش داخلی نباید مهاجم حساب شود")
check("آی‌پی نسخه ۶ هم پشتیبانی می‌شود", "2001:db8::1" in by)
check("مرتب‌سازی نزولی است",
      res["attempts"][0]["count"] >= res["attempts"][-1]["count"])

head("شدت")

check("بالای ۱۰۰ تلاش = حمله‌ی سنگین",
      any(a["severity"] == "heavy" for a in res["attempts"]))
check("۱۵ تلاش = بروت‌فورس",
      by["185.220.101.5"]["severity"] == "brute")
check("۳ تلاش = نویز", by["2001:db8::1"]["severity"] == "noise")
check("کاربر هدف ثبت می‌شود",
      by["185.220.101.5"]["top_user"] == "admin")
check("ورود موفق جدا گزارش می‌شود", len(res["accepted"]) == 1)
check("ورود موفق آی‌پی دارد", res["accepted"][0]["ip"] == "91.99.12.4")

head("جداکردن مشتری از مهاجم — مهم‌ترین بخش")

res2 = IN.ssh_attempts(hours=24, known_ips={"5.200.10.20"})
by2 = {a["ip"]: a for a in res2["attempts"]}

check("آی‌پی متصل «آشنا» علامت می‌خورد", by2["5.200.10.20"]["known"] is True)
check("آی‌پی ناشناس آشنا علامت نمی‌خورد",
      by2["185.220.101.5"]["known"] is False)
check("فهرست مشتری‌ها جدا برمی‌گردد",
      [c["ip"] for c in res2["customers"]] == ["5.200.10.20"])
check("بدون فهرست متصل‌ها، هیچ‌کس آشنا نیست",
      not any(a["known"] for a in res["attempts"]))

head("توصیه‌ها")

s = IN.summary(known_ips={"5.200.10.20"})
texts = " ".join(a["text"] for a in s["advice"])
check("درباره‌ی حمله‌ی سنگین هشدار می‌دهد", "اسکنر خودکار" in texts)
check("درباره‌ی مشتری هشدار می‌دهد", "مشتری خودتان" in texts)
check("توصیه‌ی مسدودسازی دسته‌ای دارد",
      any(a.get("action") == "block_heavy" for a in s["advice"]))
check("خروجی هر دو بخش را دارد", "ssh" in s and "hardening" in s)

head("سفت‌کردن SSH")

h = IN.ssh_hardening()
keys = {c["key"] for c in h["checks"]}
check("چهار بررسی دارد", keys == {"root_login", "password_auth", "port",
                                  "fail2ban"}, str(sorted(keys)))
check("هر بررسی راه‌حل صریح دارد",
      all(c.get("fix") for c in h["checks"]))
check("هر بررسی دلیل دارد", all(c.get("why") for c in h["checks"]))
check("بستن رمز عبور هشدار خطر دارد",
      any(c.get("danger") for c in h["checks"] if c["key"] == "password_auth"),
      "بدون کلید SSH، قفل‌شدن بیرون سرور")
check("امتیاز شمرده می‌شود", isinstance(h["score"], int)
      and 0 <= h["score"] <= h["total"])

head("نبود لاگ")

IN._auth_lines = lambda hours=24: ""
empty = IN.ssh_attempts()
check("بدون لاگ خطا نمی‌دهد", empty["available"] is False)
check("بدون لاگ توضیح می‌دهد", "لاگ" in empty["note"])
check("بدون لاگ فهرست خالی است", empty["attempts"] == [])

head("شبکه‌ی داخلی")

for ip in ("10.0.0.1", "127.0.0.1", "192.168.1.1", "172.16.0.1", "::1"):
    check(f"{ip} داخلی شناخته می‌شود", IN._is_private(ip))
for ip in ("8.8.8.8", "45.9.148.1", "172.32.0.1"):
    check(f"{ip} داخلی نیست", not IN._is_private(ip))

print(f"\n{D}{'─' * 46}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
