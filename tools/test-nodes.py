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
      'action in ("sysmon", "firewall")' in APP)
_jr = APP[APP.index("def agent_job_result"):]
_jr = _jr[:_jr.index(chr(10) + "@app.")]
check("و دستور را از ردیفِ خودِ کار می‌خواند",
      'p.get("action")' not in _jr,
      "وگرنه فرستنده تعیین می‌کند نتیجه‌اش کجا نوشته شود")

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

# ═══════════════════════════════════════════════════════════
#  رفتاری — روی دیتابیسِ موقت و خودِ app، نه روی متن
# ═══════════════════════════════════════════════════════════
import tempfile  # noqa: E402

_tmp = tempfile.mkdtemp(prefix="nx-nodes-")
for _k, _v in (("CONFIG_PATH", "config.json"), ("BOT_DB_PATH", "bot.db"),
               ("BILLING_DB_PATH", "billing.db"), ("TUNNEL_DB_PATH", "tunnels.db"),
               ("HISTORY_PATH", "history.json")):
    os.environ[_k] = os.path.join(_tmp, _v)
os.environ.setdefault("NEXORA_ADMIN_PASSWORD", "testpw")
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "bot"))
import app as _A  # noqa: E402

_T = _A.TUN
_nd = _T.create_node("ایران-۱", role="iran")
_nid, _tok = _nd["id"], _nd["token"]

head("overview گزارش‌های کامل را نمی‌فرستد")
_T.save_sysmon(_nid, {"kind": "sysmon", "data": {"blob": "x" * 20000}})
_T.save_health(_nid, {"level": "ok", "checks": []})
_row = [n for n in _T.list_nodes() if n["id"] == _nid][0]
check("sysmon در فهرستِ نودها نیست", "sysmon" not in _row,
      f"{len(json.dumps(_row, ensure_ascii=False))} بایت برای یک نود")
check("health در فهرستِ نودها نیست", "health" not in _row)
check("زمانِ گزارش می‌ماند", _row.get("sysmon_at") and _row.get("health_at"))
check("گزارش از مسیرِ خودش هنوز خوانده می‌شود",
      (_T.get_sysmon(_nid) or {}).get("data", {}).get("data", {}).get("blob", "")[:1] == "x")

head("نتیجه‌ی خراب بی‌صدا گم نمی‌شود")


def _events():
    c = _T.conn()
    try:
        return [dict(r)["message"] for r in c.execute(
            "SELECT message FROM events WHERE node_id = ? ORDER BY id", (_nid,))]
    finally:
        c.close()


for _act, _label in (("sysmon", "مانیتورینگ"), ("health", "گزارشِ سلامت")):
    _jid = _T.queue_job(_nid, _act, {})
    _before = len(_events())
    _r = _A.agent_job_result({"job_id": _jid, "ok": True, "result": "{not json"}, x_agent_token=_tok)
    _new = _events()[_before:]
    check(f"{_act}: JSONِ خراب رویداد می‌سازد", any(_label in m and "ذخیره نشد" in m for m in _new),
          " | ".join(_new)[:120] or "هیچ رویدادی")
    check(f"{_act}: پاسخ به ایجنت همچنان ok است", _r == {"ok": True})

head("وضعیتِ تانل از نتیجه‌ی کار می‌آید")
# پیش از این هیچ مسیری وضعیت را از deploying جلوتر نمی‌برد — داشبورد
# هرگز «در حال کار» نشان نمی‌داد و تانلِ خراب هم «در حال اعمال» بود.
_fn = _T.create_node("آلمان-۱", role="foreign")
_fid, _ftok = _fn["id"], _fn["token"]
_tid = _T.create_tunnel({"name": "ت۱", "engine": "backhaul", "node_id": _nid, "foreign_node": _fid,
                         "remote_host": "10.0.0.2", "bridge_port": 3080, "ports": [443]})


def _tstatus():
    t = _T.get_tunnel(_tid)
    return t["status"], t.get("last_error")


def _run(node_id, tok, action, ok, result, payload=None):
    jid = _T.queue_job(node_id, action, payload or {"tunnel_id": _tid})
    _A.agent_job_result({"job_id": jid, "ok": ok, "result": result}, x_agent_token=tok)
    return jid


_run(_nid, _tok, "apply", True, "service started")
check("اعمالِ موفقِ ایران ← در حال کار", _tstatus()[0] == "running", str(_tstatus()))
_run(_fid, _ftok, "apply", False, "binary missing")
_st = _tstatus()
check("شکستِ سمتِ خارج ← خطا، با برچسبِ «سمت خارج»", _st[0] == "failed" and "سمت خارج" in (_st[1] or ""), str(_st))
_run(_nid, _tok, "start", False, "iran side broke")
_run(_fid, _ftok, "apply", True, "ok")
check("موفقیتِ دیرترِ خارج خطای ایران را پاک نمی‌کند (صاحبِ وضعیت ایران است)",
      _tstatus() == ("failed", "iran side broke"), str(_tstatus()))
_run(_nid, _tok, "start", True, "")
_run(_nid, _tok, "stop", True, "")
check("توقف ← متوقف", _tstatus()[0] == "stopped")
_run(_nid, _tok, "status", True, json.dumps({"running": False, "state": "failed", "sub": "failed"}))
check("status: سرویسِ failed ← خطا", _tstatus()[0] == "failed", str(_tstatus()))
_run(_nid, _tok, "status", True, json.dumps({"running": True, "state": "active"}))
check("status: در حال اجرا ← در حال کار", _tstatus()[0] == "running")
_before_ev = len(_events())
_run(_nid, _tok, "status", True, "not json")
check("status نامفهوم وضعیت را دست نمی‌زند و رویداد می‌سازد",
      _tstatus()[0] == "running" and any("وضعیتِ تانل" in m for m in _events()[_before_ev:]))
_run(_nid, _tok, "restart", False, "Job for nexora-tunnel failed")
check("شکستِ ری‌استارت ← خطا با پیامِ سرور", _tstatus() == ("failed", "Job for nexora-tunnel failed"),
      str(_tstatus()))
_run(_nid, _tok, "logs", True, "some log line")
check("لاگ وضعیت را عوض نمی‌کند", _tstatus()[0] == "failed")
check("مقدارِ «error» هیچ‌جا نوشته نمی‌شود (رابط فقط failed را خطا می‌شناسد)",
      "\"error\"" not in _T.status_from_result.__doc__ and
      all((_T.status_from_result(a, ok, r) or ("",))[0] != "error"
          for a in _T.STATUS_ACTIONS for ok in (True, False) for r in ("", "{}", "x")))

head("کارهای تانل خوانده می‌شوند (دکمه‌ی لاگ)")
_jobs = _T.tunnel_jobs(_tid, 30)
check("لاگ با نتیجه‌اش برمی‌گردد", any(j["action"] == "logs" and j["result"] == "some log line" for j in _jobs))
check("payload (کانفیگ و راز) برنمی‌گردد", all("payload" not in j for j in _jobs))
_other = _T.create_tunnel({"name": "ت۱۲", "engine": "backhaul", "node_id": _nid, "remote_host": "10.0.0.3",
                           "bridge_port": 3081, "ports": [8443]})
_T.queue_job(_nid, "logs", {"tunnel_id": _other})
# شناسه‌ای که با شناسه‌ی این تانل *شروع* می‌شود (۳ و ۳۲) — LIKE هر دو را می‌گیرد
_T.queue_job(_nid, "restart", {"tunnel_id": int(f"{_tid}2")})
_mine = _T.tunnel_jobs(_tid, 30)
check("کارِ تانلِ دیگر قاطی نمی‌شود (حتی با شناسه‌ی هم‌پیشوند)",
      all(j["action"] != "logs" or j["result"] for j in _mine)
      and not any(j["action"] == "restart" and j["status"] == "queued" for j in _mine),
      f"tid={_tid}")
check("مسیرِ /jobs ثبت شده", any(getattr(r, "path", "") == "/api/admin/tunnel/{tid}/jobs" for r in _A.app.routes))

head("حذفِ نود")
_res = _T.delete_node(_fid)
check("تانلی که این نود سمتِ خارجش بود جدا می‌شود، نه یتیم", _T.get_tunnel(_tid)["foreign_node"] is None
      and _res.get("detached") == 1, str(_res))
check("شمارِ تانل‌های حذف‌شده گزارش می‌شود", _res.get("tunnels") == 0)
check("نودِ ناموجود ← None", _T.get_node(_fid) is None)

head("مرزهای تأخیر — برابریِ بکند و نمودار")
import re as _re  # noqa: E402
_TUNUI = rd("frontend/src/sections/tunnel.jsx")
_mm = _re.search(r"LATENCY_STEPS\s*=\s*\[([^\]]+)\]", _TUNUI)
_js = tuple(int(x) for x in _mm.group(1).split(",")) if _mm else None
check("LATENCY_STEPS در رابط همان بکند است", _js == tuple(_T.LATENCY_STEPS), f"ui={_js} backend={_T.LATENCY_STEPS}")
check("نمودار از latencyColor رنگ می‌گیرد، نه عددِ دستی",
      "latencyColor(v)" in _TUNUI and "v > 150 ?" not in _TUNUI and "s.latest > 60" not in _TUNUI)

print(f"\n{D}{'─' * 46}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
