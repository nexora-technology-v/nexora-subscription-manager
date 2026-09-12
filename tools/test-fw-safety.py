#!/usr/bin/env python3
"""
فایروال نباید سرویس خودش را قطع کند.

چرا وجود دارد:
    پنل روی یک سرور واقعی پیشنهاد داد پورت ۷۷۷۷ بسته شود، با این
    توضیح که «به سرویس شما ربطی ندارد — پردازه: backpack». ولی
    backpack خودِ تانل بود: بستن آن یعنی قطع‌شدن تمام مشتری‌هایی
    که ترافیکشان از ایران رد می‌شود.

    یک پیشنهاد اشتباه در فایروال، از یک باگ معمولی بدتر است: کاربر
    به آن اعتماد می‌کند، تیک می‌زند، و سرویسش می‌خوابد.

اجرا:  python3 tools/test-fw-safety.py
"""
import importlib.util
import io
import os
import sys

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


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


NETID = load("netid", "backend/netid.py")
FW = load("firewall", "backend/firewall.py")
SRC = io.open(os.path.join(ROOT, "backend", "firewall.py"),
              encoding="utf-8").read()


# ═══════════════════════════════════════════════════════════
head("پیشنهاد هرگز پورت تانل را برای بستن نمی‌دهد")

#: همان چیزی که روی سرور واقعی دیده شد
LISTENING = [
    {"port": 7777, "proto": "tcp", "process": "backpack", "public": True},
    {"port": 8460, "proto": "tcp", "process": "backhaul", "public": True},
    {"port": 22, "proto": "tcp", "process": "sshd", "public": True},
    {"port": 2053, "proto": "tcp", "process": "x-ui", "public": True},
    {"port": 443, "proto": "tcp", "process": "xray-linux-amd64", "public": True},
    {"port": 47995, "proto": "udp", "process": "", "public": True},
    {"port": 9999, "proto": "tcp", "process": "weirdthing", "public": True},
    {"port": 5432, "proto": "tcp", "process": "postgres", "public": False},
]

FW.status = lambda: {"ready": True, "installed": True, "active": False,
                     "rules": [], "sshProtected": False}
FW.tunnel_ports_in_use = lambda: {7777: "backpack", 8460: "backhaul"}

res = FW.suggest(LISTENING)
close_ports = {r["port"] for r in res["close"]}
keep_ports = {r["port"] for r in res["keep"]}
unknown_ports = {r["port"] for r in res.get("unknown") or []}

check("پورت backpack پیشنهاد بستن نمی‌شود", 7777 not in close_ports,
      "همان باگی که تانل را قطع می‌کرد")
check("پورت backpack در «باز بماند» است", 7777 in keep_ports)
check("پورت backhaul هم همین‌طور", 8460 in keep_ports and 8460 not in close_ports)
check("SSH پیشنهاد بستن نمی‌شود", 22 not in close_ports)
check("پورت x-ui باز می‌ماند", 2053 in keep_ports)
check("پورت Xray باز می‌ماند", 443 in keep_ports)

tun_rows = [r for r in res["keep"] if r.get("tunnel")]
check("تانل‌ها برچسب مخصوص دارند", len(tun_rows) == 2,
      f"{len(tun_rows)} مورد")
check("دلیلشان توضیح می‌دهد چه اتفاقی می‌افتد",
      all("قطع می‌شوند" in r["why"] for r in tun_rows))

head("پورت بی‌نام حدس زده نمی‌شود")

check("پورت UDP بدون پردازه در «نامشخص» است", 47995 in unknown_ports,
      "ممکن است تانل باشد؛ حدس‌زدن خطرناک است")
check("در «ببند» نیست", 47995 not in close_ports)
check("راه فهمیدنش را می‌گوید",
      any("ss -tulpn" in r["why"] for r in res.get("unknown") or []))

head("چیزی که واقعاً ناشناس است پیشنهاد بستن می‌شود")

check("پردازه‌ی ناشناس پیشنهاد بستن دارد", 9999 in close_ports)
check("پورت غیرعمومی اصلاً نمی‌آید",
      5432 not in close_ports | keep_ports | unknown_ports,
      "فقط روی لوپ‌بک گوش می‌دهد")

head("اعمال دسته‌ای هم محافظت دارد")

calls = []
FW.add_rule = lambda p, proto="tcp", action="allow", comment=None: (
    calls.append((p, action)) or (True, "ok"))
FW.available = lambda: True

ok, note, results = FW.apply_plan([
    {"port": 7777, "proto": "tcp", "action": "deny"},
    {"port": 22, "proto": "tcp", "action": "deny"},
    {"port": 9999, "proto": "tcp", "action": "deny"},
], confirm=True)

applied = {p for p, a in calls}
check("بستن پورت تانل انجام نمی‌شود حتی اگر خواسته شود",
      7777 not in applied)
check("بستن SSH هم انجام نمی‌شود", 22 not in applied)
check("پورت واقعاً ناشناس بسته می‌شود", 9999 in applied)
check("گزارش می‌گوید چرا انجام نشد",
      any(r.get("blocked") for r in results))
check("پیام نهایی تعداد جلوگیری‌شده را می‌گوید", "محافظت" in note, note[:60])

head("قاعده‌های ثبت‌شده با فایروال خاموش")

added = """Added user rules (see 'ufw status' for running firewall):
ufw deny from 91.99.12.4 to any
ufw allow 22/tcp
"""
rows = FW._parse_added(added)
check("قاعده‌ها خوانده می‌شوند", len(rows) == 2, f"{len(rows)} قاعده")
check("آدرس بسته‌شده پیدا می‌شود",
      any(r["source"] == "91.99.12.4" and r["action"] == "DENY" for r in rows))
check("به‌عنوان «در انتظار» علامت می‌خورند",
      all(r["pending"] for r in rows),
      "تا کاربر بداند هنوز اعمال نشده")
check("status وقتی خاموش است از show added می‌خواند",
      "ufw\", \"show\", \"added\"" in SRC or '"show", "added"' in SRC)

head("روشن‌کردن امن")

check("preflight وجود دارد", hasattr(FW, "preflight"))
check("safe_enable وجود دارد", hasattr(FW, "safe_enable"))
check("بدون confirm روشن نمی‌شود",
      FW.safe_enable(confirm=False)[0] is False)

FW._read_listening = lambda: LISTENING
FW.status = lambda: {"ready": True, "installed": True, "active": False,
                     "rules": [], "sshProtected": False}
pre = FW.preflight()
check("preflight سرویس‌های در خطر را می‌شمارد", len(pre["atRisk"]) > 0,
      f"{len(pre['atRisk'])} مورد")
check("SSH و تانل به‌عنوان مانع علامت می‌خورند",
      {b["port"] for b in pre["blockers"]} >= {22, 7777, 8460},
      str(sorted(b["port"] for b in pre["blockers"])))
check("با وجود مانع، safe نیست", pre["safe"] is False)

ok2, note2, _ = FW.safe_enable(confirm=True)
check("با وجود مانع روشن نمی‌شود", ok2 is False)
check("می‌گوید کدام‌ها مانع‌اند", "قاعده ندارند" in note2, note2[:70])

# حالا با قاعده‌های لازم
FW.status = lambda: {
    "ready": True, "installed": True, "active": False, "sshProtected": True,
    "rules": [{"port": p, "action": "ALLOW", "target": str(p),
               "source": "Anywhere", "proto": "tcp"}
              for p in (22, 7777, 8460, 2053, 443, 47995, 9999)]}
pre2 = FW.preflight()
check("وقتی همه قاعده دارند، مانعی نیست", not pre2["blockers"])
check("و امن اعلام می‌شود", pre2["safe"] is True)

head("بازگشت خودکار")

check("زمان‌بندی بازگشت وجود دارد", hasattr(FW, "_schedule_rollback"))
check("تایید دستی وجود دارد", hasattr(FW, "confirm_enabled"))
check("وضعیت بازگشت قابل خواندن است", hasattr(FW, "rollback_state"))
check("مهلت کمینه دو دقیقه است", "max(2, min(" in SRC,
      "کمتر از این برای تایید کافی نیست")
check("مهلت بیشینه یک ساعت است", "60)" in SRC)
check("بدون ساعت‌شمار روشن نمی‌کند مگر force",
      "خطرناک است" in SRC)
check("systemd اول امتحان می‌شود", "systemd-run" in SRC)
check("جایگزین پس‌زمینه هم هست", "start_new_session=True" in SRC)

print(f"\n{D}{'─' * 50}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
if not _fail:
    print(f"  {D}فایروال سرویس خودش را قطع نمی‌کند{X}")
print()
sys.exit(1 if _fail else 0)
