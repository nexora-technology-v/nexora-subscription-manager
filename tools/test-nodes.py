#!/usr/bin/env python3
"""
مانیتورینگ سرورهای دیگر — زنجیره‌ی کامل از agent تا پنل.

چرا وجود دارد:
    این قابلیت از پنج قطعه ساخته شده که هرکدام در فایل دیگری‌اند:
    عمل مجاز در tunnels، دستور در agent، سرو کردن ماژول در app،
    ذخیره‌ی نتیجه، و خواندنش. اگر یکی از این پنج‌تا جا بماند،
    دکمه فشرده می‌شود و هیچ اتفاقی نمی‌افتد — بدون هیچ خطایی.

    این تست هر پنج حلقه را می‌سنجد.

اجرا:  python3 tools/test-nodes.py
"""
import importlib.util
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def rd(path):
    return io.open(os.path.join(ROOT, path), encoding="utf-8").read()


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


AGENT = rd("agent/nexora-agent.py")
APP = rd("backend/app.py")
TUN = rd("backend/tunnels.py")
UI = rd("frontend/src/sections/nodes-monitor.jsx")

# ═══════════════════════════════════════════════════════════
head("حلقه ۱ · عمل در فهرست مجاز")

check("sysmon مجاز است", '"sysmon"' in TUN)
check("firewall مجاز است", '"firewall",     #' in TUN or '"firewall"' in TUN)
check("queue_job عمل غیرمجاز را رد می‌کند",
      "دستور مجاز نیست" in TUN)

head("حلقه ۲ · agent دستور را می‌شناسد")

check("agent شاخه‌ی sysmon دارد", 'action == "sysmon"' in AGENT)
check("agent شاخه‌ی firewall دارد", 'action == "firewall"' in AGENT)
check("هر دو از remote_module استفاده می‌کنند",
      AGENT.count("remote_module(") >= 3, "تعریف + دو صدازدن")
check("sysmon تابع snapshot را صدا می‌زند",
      'remote_module("monitor", "snapshot"' in AGENT)
check("firewall تابع status را صدا می‌زند",
      'remote_module("firewall", "status"' in AGENT)
check("دستور ناشناخته هنوز رد می‌شود", "دستور ناشناخته" in AGENT)

head("حلقه ۳ · پنل ماژول را سرو می‌کند")

check("مسیر monitor.py هست", '"/api/agent/monitor.py"' in APP)
check("مسیر firewall.py هست", '"/api/agent/firewall.py"' in APP)
check("هر دو فایل واقعاً وجود دارند",
      os.path.exists(os.path.join(ROOT, "backend", "monitor.py"))
      and os.path.exists(os.path.join(ROOT, "backend", "firewall.py")))

MON = load("monitor", "backend/monitor.py")
FW = load("firewall", "backend/firewall.py")
check("monitor.snapshot وجود دارد", callable(getattr(MON, "snapshot", None)),
      "agent دقیقاً همین نام را صدا می‌زند")
check("firewall.status وجود دارد", callable(getattr(FW, "status", None)))

head("حلقه ۴ · نتیجه ذخیره می‌شود")

check("save_sysmon تعریف شده", "def save_sysmon" in TUN)
check("get_sysmon تعریف شده", "def get_sysmon" in TUN)
check("ستون در صورت نبود ساخته می‌شود",
      "ALTER TABLE nodes ADD COLUMN sysmon" in TUN,
      "نصب‌های قدیمی بدون مهاجرت دستی")
check("app نتیجه‌ی sysmon را ذخیره می‌کند",
      'p.get("action") in ("sysmon", "firewall")' in APP)

head("حلقه ۵ · پنل می‌خواند")

check("مسیر درخواست هست", '/api/admin/tunnel/node/{node_id}/sysmon' in APP)
check("درخواست و خواندن هر دو تعریف شده‌اند",
      APP.count('tunnel/node/{node_id}/sysmon') == 2, "POST و GET")
check("نوع نامعتبر رد می‌شود", 'نوع درخواست نامعتبر' in APP)
check("نبودِ گزارش خطا نیست",
      '"ready": False' in APP and "هنوز گزارشی" in APP)

head("رابط کاربری")

check("صفحه ساخته شده", "NodesMonitor" in UI)
check("فهرست سرورها از overview می‌آید",
      "/api/admin/tunnel/overview" in UI,
      "مسیر /tunnel/nodes وجود ندارد")
check("مسیر درخواست درست است",
      "/api/admin/tunnel/node/${sel}/sysmon?kind=" in UI)
check("بعد از درخواست منتظر می‌ماند", "tries >= 10" in UI,
      "کار در صف می‌نشیند، پس جواب فوری نیست")
check("حلقه‌ی انتظار بی‌پایان نیست", "setTimeout(poll, 3000)" in UI)
check("تایمر پاک می‌شود", "clearTimeout(timer.current)" in UI,
      "وگرنه بعد از ترک صفحه هم ادامه می‌دهد")

# امضای کامپوننت‌ها باید با تعریفشان بخواند — همان دسته اشتباهی
# که build نمی‌گیرد و فقط در مرورگر سفید می‌شود
MONUI = rd("frontend/src/sections/monitoring.jsx")
check("PortsCard با پراپ ports صدا زده می‌شود",
      "export function PortsCard({ ports })" in MONUI
      and "<PortsCard ports=" in UI)
check("ConnectionsCard با پراپ conn صدا زده می‌شود",
      "export function ConnectionsCard({ conn" in MONUI
      and "<ConnectionsCard conn=" in UI)
check("MetricCard با پراپ m صدا زده می‌شود",
      "export function MetricCard({ m })" in MONUI
      and "<MetricCard key={m.key} m={m} />" in UI)

head("شکل داده")

snap = MON.snapshot(include=["cpu"])
check("snapshot کلید metrics دارد", "metrics" in snap)
check("snapshot کلید sections دارد", "sections" in snap,
      "رابط از همین می‌خواند")
check("هر سنجه key دارد",
      all("key" in m for m in snap.get("metrics", [])) or not snap.get("metrics"))

st = FW.status()
check("firewall.status کلید installed دارد", "installed" in st)
check("firewall.status کلید rules دارد", "rules" in st)

check("رابط از sections می‌خواند", "d.sections" in UI)
check("رابط نوع گزارش را تفکیک می‌کند",
      'snap.kind === "sysmon"' in UI and 'snap.kind === "firewall"' in UI)

head("در منو دیده می‌شود")

NAV = rd("frontend/src/lib/constants.js")
APPJSX = rd("frontend/src/App.jsx")
check("آیتم منو اضافه شده", '"nodes-monitor"' in NAV)
check("به کامپوننت وصل شده", 'active === "nodes-monitor"' in APPJSX)
check("import شده", 'from "./sections/nodes-monitor"' in APPJSX)

print(f"\n{D}{'─' * 46}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
