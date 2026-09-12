#!/usr/bin/env python3
"""
شناسایی آی‌پی: لوپ‌بک، تانل، و «این مشتری من است؟»

چرا وجود دارد:
    هر باگی که این‌جا می‌سنجیم یک بار روی سرور واقعی دیده شده:

    · ::ffff:127.0.0.1 از صافی رد می‌شد و ۲۶٪ کل اتصال‌ها را
      به‌عنوان «پرمصرف‌ترین آی‌پی» بالای فهرست می‌نشاند
    · backpack و backhaul تانل‌اند ولی شناخته نمی‌شدند
    · تابع _connected_ips کلید "top" را می‌خواند در حالی که
      connections() کلید "byIp" برمی‌گرداند — یعنی تشخیص مشتری
      عملاً هیچ‌وقت کار نکرده بود

اجرا:  python3 tools/test-netid.py
"""
import importlib.util
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


N = load("netid", "backend/netid.py")

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


# ═══════════════════════════════════════════════════════════
head("یکسان‌سازی آدرس")

check("::ffff:127.0.0.1 همان 127.0.0.1 است",
      N.normalize("::ffff:127.0.0.1") == "127.0.0.1",
      "روی سرور واقعی ۷۵۱ اتصال بود که مشتری حساب می‌شد")
check("آدرس با براکت پاک می‌شود",
      N.normalize("[2a11:6c7:f39:6b::2]") == "2a11:6c7:f39:6b::2")
check("آی‌پی‌وی۶ فشرده می‌شود",
      N.normalize("2A11:06C7:0F39:006B:0:0:0:2") == "2a11:6c7:f39:6b::2")
check("آدرس ساده دست‌نخورده", N.normalize("95.38.38.14") == "95.38.38.14")
check("ورودی خالی خالی می‌ماند", N.normalize("") == "")
check("متن بی‌ربط نمی‌شکند", N.normalize("سلام") == "سلام")

head("داخلی یا بیرونی")

for ip, want, why in [
    ("::ffff:127.0.0.1", True, "لوپ‌بک نگاشته‌شده — همان باگ سرور"),
    ("127.0.0.1", True, ""),
    ("::1", True, ""),
    ("10.0.0.5", True, "شبکه‌ی خصوصی"),
    ("192.168.1.7", True, ""),
    ("172.16.0.1", True, ""),
    ("169.254.1.1", True, "link-local"),
    ("0.0.0.0", True, ""),
    ("*", True, ""),
    ("95.38.38.14", False, "آی‌پی ایران — مشتری واقعی"),
    ("2a11:6c7:f39:6b::2", False, "آی‌پی‌وی۶ عمومی"),
    ("172.32.0.1", False, "خارج از محدوده‌ی خصوصی"),
]:
    check(f"{ip} {'داخلی' if want else 'عمومی'} است",
          N.is_local(ip) is want, why)

head("موتورهای تانل")

for eng in ("backhaul", "backpack", "chisel", "rathole", "gost",
            "wireguard", "hysteria", "wstunnel"):
    check(f"{eng} شناخته می‌شود", eng in N.TUNNEL_PROCS)
check("فهرست کوتاه نیست", len(N.TUNNEL_PROCS) >= 15,
      f"{len(N.TUNNEL_PROCS)} موتور")

head("دسته‌بندی یک آدرس")

TUN = {"95.38.38.14": "تانل (backhaul)"}
CL = {"5.200.10.20": ["ali_1", "ali_2"], "185.5.5.5": []}

r = N.identify("::ffff:127.0.0.1", tunnels=TUN, clients=CL)
check("لوپ‌بک دسته‌ی local می‌گیرد", r["kind"] == "local")
check("لوپ‌بک نرمال‌شده برمی‌گردد", r["ip"] == "127.0.0.1")

r = N.identify("95.38.38.14", tunnels=TUN, clients=CL)
check("تانل شناخته می‌شود", r["kind"] == "tunnel")
check("نام موتور تانل می‌آید", "backhaul" in r["why"])

r = N.identify("5.200.10.20", tunnels=TUN, clients=CL)
check("مشتری شناخته می‌شود", r["kind"] == "customer")
check("نام کلاینت‌ها برمی‌گردد", r.get("clients") == ["ali_1", "ali_2"])
check("توضیح شامل نام کلاینت است", "ali_1" in r["why"])

r = N.identify("185.5.5.5", tunnels=TUN, clients=CL)
check("کلاینت بی‌نام هم مشتری است", r["kind"] == "customer",
      "آی‌پی در فهرست هست حتی اگر نامش را ندانیم")

r = N.identify("45.9.148.7", tunnels=TUN, clients=CL)
check("آدرس ناشناس ناشناس می‌ماند", r["kind"] == "unknown")
check("دلیل ناشناس‌بودن نوشته می‌شود", "هیچ کلاینت" in r["why"])

head("صداقت درباره‌ی VPN")

note = N.explain_vpn()
check("صریح می‌گوید آدرس پشت VPN قابل کشف نیست",
      "قابل کشف" in note and "نیست" in note,
      "ادعای بیشتر از این، دروغ است")
check("سؤال درست را جای آن می‌گذارد", "مشتری‌ام را" in note)
check("راه‌حل واقعی را توضیح می‌دهد", "کلاینت‌های خودتان" in note)

head("باگ کلید byIp در app.py")

APP = io.open(os.path.join(ROOT, "backend", "app.py"), encoding="utf-8").read()
check("_connected_ips کلید درست را می‌خواند",
      '"byIp", "heavy", "tunnels"' in APP,
      "قبلاً \"top\" بود که connections() هرگز برنمی‌گرداند")
check("از netid برای آی‌پی مشتری استفاده می‌کند",
      "NETID.client_ips()" in APP)
check("آی‌پی تانل هم آشنا حساب می‌شود",
      "NETID.tunnel_peers()" in APP)
check("دسته‌بندی به خروجی اضافه می‌شود",
      'a["kind"] = info.get("kind")' in APP)
check("تانل و مشتری هر دو known می‌شوند",
      '("tunnel", "customer", "local")' in APP)

head("monitor از netid استفاده می‌کند")

MON = io.open(os.path.join(ROOT, "backend", "monitor.py"), encoding="utf-8").read()
check("لوپ‌بک با is_local کنار می‌رود", "_NET.is_local(ip)" in MON)
check("آدرس نرمال می‌شود", "_NET.normalize(" in MON)
check("فهرست ثابت آدرس‌ها حذف شده",
      '("127.0.0.1", "::1", "*", "0.0.0.0")' not in MON)
check("تانل‌ها از netid می‌آیند", "_NET.tunnel_peers(" in MON)
check("بدون netid هم کار می‌کند", "_Fallback" in MON,
      "agent این فایل را تنها اجرا می‌کند")

M = load("monitor", "backend/monitor.py")
check("monitor واقعاً بارگذاری می‌شود", hasattr(M, "snapshot"))
check("backpack در TUNNEL_ENGINES هست", "backpack" in M.TUNNEL_ENGINES)

print(f"\n{D}{'─' * 46}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
