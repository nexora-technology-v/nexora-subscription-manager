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

# ═══════════════════════════════════════════════════════════
head("پورتی که به آی‌پی مشخص بسته شده هم دیده می‌شود")

import importlib.util as _iu  # noqa: E402
_sp = _iu.spec_from_file_location("mon", os.path.join(ROOT, "backend", "monitor.py"))
MON = _iu.module_from_spec(_sp)
_sp.loader.exec_module(MON)

# خروجی واقعی ss: سرویس‌ها همیشه به 0.0.0.0 بسته نمی‌شوند. تانل‌ها
# معمولاً به آی‌پی مشخص سرور بسته می‌شوند — و همان‌ها بودند که
# فایروال اصلاً نمی‌دیدشان.
SS = "\n".join([
    'tcp   LISTEN 0 4096  0.0.0.0:22    0.0.0.0:*  users:(("sshd",pid=1,fd=3))',
    'tcp   LISTEN 0 4096  65.108.213.175:7777 0.0.0.0:*  users:(("backpack",pid=9,fd=5))',
    'tcp   LISTEN 0 4096  127.0.0.1:9090 0.0.0.0:*  users:(("panel",pid=7,fd=4))',
    'udp   UNCONN 0 0     10.0.0.5:47995 0.0.0.0:*  users:(("backhaul",pid=8,fd=6))',
    'tcp   LISTEN 0 4096  [::]:443      [::]:*     users:(("xray",pid=5,fd=9))',
    'tcp   LISTEN 0 4096  [::1]:6010    [::]:*     users:(("sshd",pid=1,fd=11))',
])

MON._has = lambda b: True
MON._run = lambda cmd, timeout=8: (True, SS)
rows = {r["port"]: r for r in MON.listening()}

check("پورت روی همه‌ی رابط‌ها عمومی است", rows[22]["public"] is True)
check("پورت بسته‌شده به آی‌پی سرور هم عمومی است",
      rows[7777]["public"] is True,
      "همان تانلی که فایروال نمی‌دیدش")
check("پورت UDP روی آدرس خصوصی هم عمومی است",
      rows[47995]["public"] is True,
      "ufw آدرس خصوصی را هم فیلتر می‌کند")
check("IPv6 روی همه‌ی رابط‌ها عمومی است", rows[443]["public"] is True)
check("لوپ‌بک عمومی نیست", rows[9090]["public"] is False)
check("لوپ‌بک IPv6 هم عمومی نیست", rows[6010]["public"] is False)
check("آدرس اتصال گزارش می‌شود", rows[7777]["bind"] == "65.108.213.175",
      rows[7777].get("scope", ""))
check("نام پردازه خوانده می‌شود", rows[7777]["process"] == "backpack")

# و همین‌ها باید به دست فایروال برسند
FW.status = lambda: {"ready": True, "installed": True, "active": False,
                     "rules": [], "sshProtected": False}
FW.tunnel_ports_in_use = lambda: {7777: "backpack", 47995: "backhaul"}
res2 = FW.suggest(list(rows.values()))
seen_ports = ({r["port"] for r in res2["keep"]}
              | {r["port"] for r in res2["close"]}
              | {r["port"] for r in res2.get("unknown") or []})
check("تانلِ بسته‌شده به آی‌پی مشخص به فایروال می‌رسد", 7777 in seen_ports)
check("و در «باز بماند» است",
      7777 in {r["port"] for r in res2["keep"]})
check("لوپ‌بک به فایروال نمی‌رسد", 9090 not in seen_ports,
      "از بیرون در دسترس نیست، پس قاعده لازم ندارد")


# ═══════════════════════════════════════════════════════════
head("بستن آی‌پی بدون فایروال")

check("blackhole_add وجود دارد", hasattr(FW, "blackhole_add"))
check("blackhole_remove وجود دارد", hasattr(FW, "blackhole_remove"))
check("فهرست ماندگار نگه داشته می‌شود", "BLOCKLIST" in SRC,
      "مسیر روتینگ با ریبوت پاک می‌شود")
check("بعد از ریبوت بازگردانده می‌شود", hasattr(FW, "blackhole_restore"))

# آدرس نامعتبر باید قبل از رسیدن به هر دستوری رد شود
for bad in ("; rm -rf /", "not-an-ip", "", "1.2.3.4; ls"):
    okb, note = FW.blackhole_add(bad)
    check(f"«{bad[:18] or 'خالی'}» رد می‌شود", okb is False, note[:40])

# دستور ساخته‌شده باید دقیقاً همان چیزی باشد که انتظار داریم
cmds = []
FW._run = lambda cmd, timeout=15: (cmds.append(cmd) or (True, ""))
FW.blackhole_available = lambda: True
FW.blackhole_list = lambda: []
FW._blocklist_write = lambda ip, note, remove: None

FW.blackhole_add("91.99.12.4")
check("دستور درست ساخته می‌شود",
      cmds and cmds[-1] == ["ip", "route", "add", "blackhole", "91.99.12.4"],
      " ".join(cmds[-1]) if cmds else "")
check("هیچ رشته‌ای به شل نمی‌رود", all(isinstance(c, list) for c in cmds),
      "فهرست، نه رشته — پس تزریق دستور ممکن نیست")

cmds.clear()
FW.blackhole_remove("91.99.12.4")
check("بازکردن دستور درست دارد",
      cmds and cmds[-1] == ["ip", "route", "del", "blackhole", "91.99.12.4"])

cmds.clear()
okr, _ = FW.blackhole_add("91.99.12.0/24")
check("رنج هم پذیرفته می‌شود", okr and "91.99.12.0/24" in (cmds[-1] or []))

check("هر دو راه در یک فهرست می‌آیند", hasattr(FW, "blocked_overview"))


# ═══════════════════════════════════════════════════════════
head("بستن دسته‌ای، خروجی و تأیید")

check("bulk وجود دارد", hasattr(FW, "blackhole_bulk"))
check("export وجود دارد", hasattr(FW, "blackhole_export"))
check("verify وجود دارد", hasattr(FW, "blackhole_verify"))

calls2 = []
FW._run = lambda cmd, timeout=15: (calls2.append(cmd) or (True, ""))
FW.blackhole_available = lambda: True
FW.blackhole_list = lambda: []
FW._blocklist_write = lambda ip, note, remove: None

res = FW.blackhole_bulk(["91.99.12.4", "45.9.148.7", "  ", "# توضیح",
                         "91.99.12.4", "bad-ip"])
check("تکراری‌ها یک بار حساب می‌شوند",
      sum(1 for r in res["results"] if r["ip"] == "91.99.12.4") == 1)
check("خط خالی و کامنت رد می‌شوند",
      all(r["ip"] not in ("", "#") for r in res["results"]))
check("آدرس نامعتبر ناموفق می‌شود",
      any(not r["ok"] and r["ip"] == "bad-ip" for r in res["results"]))
check("آدرس‌های درست بسته می‌شوند", res["done"] == 2, str(res["done"]))
check("گزارش برای هر آدرس جدا می‌آید", len(res["results"]) == 3,
      f"{len(res['results'])} ردیف")

# قالب خروجی باید دوباره قابل ورود باشد
FW.blackhole_list = lambda: ["91.99.12.4", "45.9.148.7"]
txt = FW.blackhole_export()
back = FW.blackhole_bulk(txt.splitlines())
check("خروجی دوباره قابل ورود است", back["total"] == 2,
      f"{back['total']} آدرس از فایل خوانده شد")

# تأیید باید از کرنل بپرسد، نه از فایلی که خودمان نوشته‌ایم
FW._run = lambda cmd, timeout=10: (True, "blackhole 91.99.12.4 dev lo")
v = FW.blackhole_verify("91.99.12.4")
check("تأیید از کرنل می‌پرسد", v["blocked"] is True, v["why"][:40])

FW._run = lambda cmd, timeout=10: (True, "91.99.12.4 via 1.2.3.1 dev eth0")
FW.blackhole_list = lambda: []
v2 = FW.blackhole_verify("91.99.12.4")
check("مسیر عادی یعنی بسته نیست", v2["blocked"] is False, v2["why"][:40])



# ═══════════════════════════════════════════════════════════
head("سوکت‌های موقت xray قاعده‌ی فایروال نمی‌سازند")

# xray برای هر ترافیک خروجی (DNS، QUIC) یک سوکت UDP موقت باز می‌کند.
# در ss عیناً مثل یک سرویس در حال گوش‌دادن دیده می‌شوند — روی سرور
# واقعی حدود چهل‌تا. چون نام پردازه‌شان xray است، همه در دسته‌ی
# «باز بماند» می‌نشستند: فهرست فایروال با چهل ردیف بی‌معنی پر می‌شد،
# و اعمال پیشنهادها چهل قاعده‌ی ufw می‌ساخت برای پورت‌هایی که با
# اولین ری‌استارت xray عدد تازه می‌گیرند.

import sqlite3 as _sq
import tempfile as _tf

XDB = _tf.mktemp(suffix=".db")
_c = _sq.connect(XDB)
_c.execute("CREATE TABLE inbounds (id INTEGER PRIMARY KEY, port INTEGER,"
           " remark TEXT, enable INTEGER)")
_c.executemany("INSERT INTO inbounds (port, remark, enable) VALUES (?,?,1)",
               [(8443, "آلمان"), (2096, "اشتراک"), (36112, "هیستریا UDP")])
_c.commit()
_c.close()
os.environ["XUI_DB_PATH"] = XDB

ports = FW.xray_service_ports()
check("اینباندها از x-ui خوانده می‌شوند", ports == {8443, 2096, 36112},
      str(sorted(ports or [])))

REAL = [
    {"port": 22, "proto": "tcp", "process": "sshd", "public": True,
     "known": "SSH"},
    {"port": 443, "proto": "tcp", "process": "nginx", "public": True,
     "known": "HTTPS"},
    {"port": 8443, "proto": "tcp", "process": "xray-linux-amd6",
     "public": True, "known": "Xray"},
    {"port": 36112, "proto": "udp", "process": "xray-linux-amd6",
     "public": True, "known": ""},
    {"port": 7777, "proto": "tcp", "process": "backpack", "public": True,
     "known": ""},
]
EPH = [{"port": p, "proto": "udp", "process": "xray-linux-amd6",
        "public": True, "known": ""}
       for p in (25289, 45772, 29394, 49882, 29411, 33512, 21242)]

FW.status = lambda: {"ready": True, "installed": True, "active": False,
                     "rules": [], "sshProtected": False}
FW.tunnel_ports_in_use = lambda: {7777: "backpack"}

r = FW.suggest(listening_ports=REAL + EPH)
kept = {x["port"] for x in r["keep"]}
eph = {x["port"] for x in r["ephemeral"]}

check("سوکت‌های موقت کنار گذاشته می‌شوند", eph == {p["port"] for p in EPH},
      f"{len(eph)} سوکت")
check("و در هیچ دسته‌ی دیگری نیستند",
      not (eph & (kept | {x["port"] for x in r["close"]}
                  | {x["port"] for x in r["unknown"]})),
      "وگرنه باز هم قاعده می‌سازند")

check("اینباند واقعی xray باز می‌ماند", 8443 in kept)
check("اینباند UDP واقعی هم باز می‌ماند", 36112 in kept,
      "هیستریا روی پورت بالای UDP کار می‌کند — نباید با موقت‌ها اشتباه شود")
check("SSH دست‌نخورده می‌ماند", 22 in kept)
check("تانل دست‌نخورده می‌ماند", 7777 in kept)
check("nginx دست‌نخورده می‌ماند", 443 in kept)
check("فهرست پیشنهاد کوتاه و خواندنی می‌شود", len(r["keep"]) == 5,
      f"{len(r['keep'])} ردیف به‌جای {len(REAL) + len(EPH)}")

head("وقتی مطمئن نیستیم، چیزی را کنار نمی‌گذاریم")

os.environ["XUI_DB_PATH"] = "/nowhere/x-ui.db"
check("بدون دیتابیس x-ui، پاسخ None است — نه مجموعه‌ی خالی",
      FW.xray_service_ports() is None,
      "مجموعه‌ی خالی یعنی «هیچ اینباندی نیست» و همه چیز را موقت می‌دید")

r2 = FW.suggest(listening_ports=REAL + EPH)
check("و هیچ پورتی کنار گذاشته نمی‌شود", not r2["ephemeral"])
check("رفتار قبلی دست‌نخورده می‌ماند",
      len(r2["keep"]) == len(REAL) + len(EPH),
      "حدس‌نزدن بهتر از حدسِ اشتباه است")

os.environ["XUI_DB_PATH"] = XDB

head("پورت محافظت‌شده هیچ‌وقت موقت حساب نمی‌شود")

r3 = FW.suggest(listening_ports=[
    {"port": 22, "proto": "tcp", "process": "xray-linux-amd6",
     "public": True, "known": ""},
    {"port": 7777, "proto": "udp", "process": "xray-linux-amd6",
     "public": True, "known": ""},
])
check("SSH حتی با نام پردازه‌ی xray کنار گذاشته نمی‌شود",
      22 in {x["port"] for x in r3["keep"]},
      "یک اشتباه این‌جا یعنی قفل‌شدن بیرون سرور")
check("پورت تانل هم همین‌طور", 7777 in {x["port"] for x in r3["keep"]})

try:
    os.unlink(XDB)
except OSError:
    pass
os.environ.pop("XUI_DB_PATH", None)



print(f"\n{D}{'─' * 50}{X}")
color = G if not _fail else R
# ═══════════════════════════════════════════════════════════
head("بستن آی‌پی نباید خودِ مدیر را ببندد")

# قاعده‌ی طلایی این فایل می‌گوید هیچ عملیاتی نباید دسترسی SSH مدیر را
# قطع کند — ولی بستن آی‌پی از این نگهبان رد نمی‌شد. آی‌پی خودِ مدیر
# می‌تواند در فهرست تلاش‌های ناموفق بنشیند (چند بار اشتباه زدن رمز
# کافی است) و بعد یک کلیک روی «بستن مهاجم‌ها» قاعده را در جایگاه
# *اول* می‌نشاند، جلوتر از قاعده‌ی مجازِ SSH. و این مسیر ساعت‌شمار
# بازگشت ندارد.

check("آدرس خودِ درخواست‌دهنده بسته نمی‌شود",
      "وصل‌اید" in (FW.block_refusal("5.6.7.8", protect="5.6.7.8") or ""),
      FW.block_refusal("5.6.7.8", protect="5.6.7.8"))
check("رنجی که آدرس خودش را در بر می‌گیرد هم",
      FW.block_refusal("5.6.0.0/16", protect="5.6.7.8") is not None,
      "بستن رنج هم همان نتیجه را دارد")
check("ولی آدرس واقعاً غریبه پذیرفته می‌شود",
      FW.block_refusal("91.99.12.4", protect="5.6.7.8") is None)

check("لوپ‌بک رد می‌شود", FW.block_refusal("127.0.0.1") is not None)
check("آدرس داخلی رد می‌شود", FW.block_refusal("192.168.1.5") is not None,
      "مهاجمِ بیرونی آدرس داخلی ندارد")
check("۱۰.x هم", FW.block_refusal("10.0.0.7") is not None)
check("«همه‌ی آدرس‌ها» رد می‌شود", FW.block_refusal("0.0.0.0") is not None,
      "در جایگاه اول یعنی قطع کامل سرور")

check("رنج بیش از حد بزرگ رد می‌شود",
      FW.block_refusal("1.0.0.0/4") is not None,
      "/4 یعنی یک‌شانزدهم اینترنت")
check("ولی یک /8 برای بستن یک کشور مجاز است",
      FW.block_refusal("5.0.0.0/8") is None,
      "کاربرد واقعی دارد، پس ردش نمی‌کنیم")
check("آدرس بی‌معنا رد می‌شود", FW.block_refusal("سلام") is not None)
check("خالی هم", FW.block_refusal("") is not None)
# 2001:db8:: رنج مستندات است و پایتون هم خصوصی حسابش می‌کند — آدرس
# جهانی واقعی لازم است
check("آی‌پی‌شش جهانی پذیرفته می‌شود",
      FW.block_refusal("2606:4700:4700::1111") is None,
      str(FW.block_refusal("2606:4700:4700::1111")))
check("ولی رنج مستندات آی‌پی‌شش رد می‌شود",
      FW.block_refusal("2001:db8::1") is not None)

# بدون ufw هم باید *قبل* از «ufw نصب نیست» رد شود — یعنی پیام درست
# را بدهد، نه پیامی که مدیر را دنبال نخود سیاه بفرستد
_real = FW.available
FW.available = lambda: False
# نام _ok نه: همان شمارنده‌ی پاسِ این فایل است
_bok, _bnote = FW.block_ip("127.0.0.1")
check("پیام خطا دلیل واقعی را می‌گوید",
      not _bok and "لوپ‌بک" in _bnote, _bnote)
FW.available = _real

APP = io.open(os.path.join(ROOT, "backend", "app.py"), encoding="utf-8").read()
check("هر سه مسیرِ بستن آدرسِ خودی را می‌فرستند",
      APP.count("protect=_auth_ip.get()") >= 3,
      "تک‌تک، دسته‌ای، و بلک‌هول")
check("مسیر دسته‌ای بلک‌هول هم",
      "blackhole_bulk(raw, protect=" in APP)


print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
if not _fail:
    print(f"  {D}فایروال سرویس خودش را قطع نمی‌کند{X}")
print()
sys.exit(1 if _fail else 0)
