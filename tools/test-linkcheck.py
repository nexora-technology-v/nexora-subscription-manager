"""
عیب‌یابیِ ارتباطِ ایران↔خارج و حجمِ ترافیک.

برگه: docs/specs/2026-09-26-link-diagnosis-and-traffic.md

هر ادعا با رفتار سنجیده می‌شود: حکمِ هر ردیفِ جدولِ برگه، تفاضلِ
شمارنده با ری‌استارت، و اینکه نتیجه‌ی یک نود روی نودِ دیگری نوشته نشود.

اجرا:  PYTHONIOENCODING=utf-8 python tools/test-linkcheck.py
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = tempfile.mkdtemp()
os.environ["TUNNEL_DB_PATH"] = os.path.join(TMP, "tunnels.db")
os.environ.setdefault("BILLING_DB", os.path.join(TMP, "billing.db"))
os.environ.setdefault("BOT_DB", os.path.join(TMP, "bot.db"))
sys.path.insert(0, os.path.join(ROOT, "backend"))

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  ✗ {name}" + (f" — {detail}" if detail else ""))


def head(t):
    print(f"\n── {t} ──")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


LINK = load("linkcheck", "backend/linkcheck.py")
MON = load("monitor_t", "backend/monitor.py")
import tunnels as TUN          # noqa: E402

# ═══════════════════════════════════════════════════════════
head("خلاصه‌ی مسیر و وضعیت")
# ═══════════════════════════════════════════════════════════


def tgt(loss, avg=None, kind="tcp"):
    m = {"loss": loss}
    if avg is not None:
        m["avg"] = avg
    return {"host": "h", kind: m}


s = LINK.summarize([tgt(0, 20), tgt(100), tgt(0, 40)])
check("مقصدِ مرده ۱۰۰ حساب می‌شود و تاخیر از زنده‌ها",
      s["loss"] == 33 and s["avg"] == 40 and s["up"] == 2, str(s))
check("بیش از نیمی قطع → کلِ مسیر قطع",
      LINK.state(LINK.summarize([tgt(100), tgt(100), tgt(0, 20)]), "intl") == "down")
check("پرتِ ۱۰٪ → ناپایدار", LINK.state(LINK.summarize([tgt(10, 50)]), "intl") == "lossy")
check("کند بر اساسِ مرزِ همان مسیر",
      LINK.state(LINK.summarize([tgt(0, 200)]), "domestic") == "slow"
      and LINK.state(LINK.summarize([tgt(0, 200)]), "intl") == "ok")
check("بی‌داده «نامشخص» است، نه «قطع»", LINK.state(None, "intl") == "unknown")
check("ICMP وقتی TCP نیست", LINK.summarize([tgt(0, 30, "icmp")])["avg"] == 30)

# ═══════════════════════════════════════════════════════════
head("حکم — هر ردیفِ جدولِ برگه")
# ═══════════════════════════════════════════════════════════
OK = [tgt(0, 30)]
DEAD = [tgt(100)]


def iran(domestic=OK, intl=OK, foreign=OK):
    return {"paths": {"domestic": domestic, "intl": intl, "foreign": foreign}}


def foreign(iran_=OK, intl=OK):
    return {"paths": {"iran": iran_, "intl": intl}}


CASES = [
    ("ایران به داخل هم نمی‌رسد → سرورِ ایران", iran(domestic=DEAD, intl=DEAD, foreign=DEAD),
     foreign(iran_=DEAD), "iran"),
    ("داخل خوب، بین‌الملل قطع → سراسری", iran(intl=DEAD, foreign=DEAD), foreign(iran_=DEAD),
     "iran-intl"),
    ("سرورِ خارج به بیرون نمی‌رسد → سرورِ خارج", iran(foreign=DEAD), foreign(iran_=DEAD, intl=DEAD),
     "foreign"),
    ("هر دو به بیرون سالم، بینِ خودشان قطع → مسیرِ بینِ دو سرور", iran(foreign=DEAD),
     foreign(iran_=DEAD), "between"),
    ("فقط یک جهتِ بینِ دو سرور بد → باز هم بینِ دو سرور", iran(), foreign(iran_=DEAD), "between"),
    ("همه سالم", iran(), foreign(), "none"),
]
for name, i, f, want in CASES:
    v = LINK.diagnose(i, f)
    check(name, v["side"] == want, f"{v['side']} · {v['title']}")
v = LINK.diagnose(iran(), None)
check("سمتِ خارج هنوز نسنجیده → «هنوز داده نیست»، نه «سالم»",
      v["side"] == "unknown" and "خارج ← ایران" in v["reason"], v["reason"])
check("سرورِ ایرانِ قطع بر «آی‌پیِ خارج محدود شده» مقدم است",
      LINK.diagnose(iran(domestic=DEAD, intl=DEAD, foreign=DEAD), foreign(iran_=DEAD))["side"] == "iran")

# ═══════════════════════════════════════════════════════════
head("شمارنده‌ها — همان فیلترِ monitor")
# ═══════════════════════════════════════════════════════════
DEV = """Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo: 9999 1 0 0 0 0 0 0 9999 1 0 0 0 0 0 0
  eth0: 1000 10 0 0 0 0 0 0 2000 20 0 0 0 0 0 0
  ens3: 500 5 0 0 0 0 0 0 700 7 0 0 0 0 0 0
docker0: 77777 1 0 0 0 0 0 0 77777 1 0 0 0 0 0 0
vethabc: 88888 1 0 0 0 0 0 0 88888 1 0 0 0 0 0 0
br-1234: 55555 1 0 0 0 0 0 0 55555 1 0 0 0 0 0 0
"""
c = LINK.net_counters(DEV)
check("جمعِ کارت‌های واقعی", c == {"rx": 1500, "tx": 2700}, str(c))
MON._read = lambda path, default="": DEV
mc = MON._net_counters()
check("برابر با monitor._net_counters (همان کارت‌ها)",
      sum(v[0] for v in mc.values()) == c["rx"] and sum(v[1] for v in mc.values()) == c["tx"],
      f"{mc}")
check("بی کارت → None، نه صفر", LINK.net_counters("a\nb\n") is None)

# ═══════════════════════════════════════════════════════════
head("آی‌پیِ طرفِ مقابلِ تانل")
# ═══════════════════════════════════════════════════════════
SS = ("0 0 198.51.100.7:3080 203.0.113.9:51514\n"
      "0 0 198.51.100.7:3080 203.0.113.9:51515\n"
      "0 0 198.51.100.7:443 192.0.2.44:6000\n"
      "0 0 127.0.0.1:3080 127.0.0.1:4000\n")
_real_run = subprocess.run
LINK.subprocess.run = lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=SS, stderr="")
check("فقط اتصال‌های پورتِ تانل، یکتا، بی localhost",
      LINK.peer_ips([3080]) == ["203.0.113.9"], str(LINK.peer_ips([3080])))
LINK.subprocess.run = _real_run

# ═══════════════════════════════════════════════════════════
head("حجمِ ترافیک")
# ═══════════════════════════════════════════════════════════
check("سنجشِ اول فقط مبدأ است", TUN.traffic_delta(None, 5000) == 0)
check("تفاضلِ عادی", TUN.traffic_delta(1000, 1600) == 600)
check("ری‌استارت: کلِ عددِ تازه، نه منفی و نه صفر", TUN.traffic_delta(9000, 300) == 300)

TUN.conn().close()
TUN.record_traffic(7, {"rx": 1000, "tx": 5000}, at="2026-09-26T10:00:00")
TUN.record_traffic(7, {"rx": 1600, "tx": 5900}, at="2026-09-26T10:05:00")
TUN.record_traffic(7, {"rx": 200, "tx": 100}, at="2026-09-26T11:02:00")     # ری‌استارت
TUN.record_traffic(7, {"rx": 1200, "tx": 600}, at="2026-09-27T09:00:00")
sm = TUN.traffic_summary(7, at="2026-09-27T09:30:00")
check("امروز فقط امروز", sm["today"] == {"rx": 1000, "tx": 500}, str(sm["today"]))
check("هفت روز همه را دارد (با ری‌استارت)",
      sm["week"] == {"rx": 600 + 200 + 1000, "tx": 900 + 100 + 500}, str(sm["week"]))
check("۲۴ سطلِ ساعتی و ۳۰ روز", len(sm["hours"]) == 24 and len(sm["days"]) == 30)
check("ساعتِ ری‌استارت در سطلِ خودش",
      next(d for d in sm["days"] if d["day"] == "2026-09-26") == {"day": "2026-09-26", "rx": 800, "tx": 1000})
check("شمارنده‌ی ناقص چیزی ثبت نمی‌کند", TUN.record_traffic(7, {"rx": 5}) == (0, 0))

# ═══════════════════════════════════════════════════════════
head("نتیجه‌ی ایجنت — فقط برای نودِ خودش")
# ═══════════════════════════════════════════════════════════
import app as APP              # noqa: E402

A = TUN.create_node("iran-a", role="iran")["id"]
B = TUN.create_node("iran-b", role="iran")["id"]
F = TUN.create_node("foreign-f", role="foreign")["id"]
con = TUN.conn()
con.execute("INSERT INTO tunnels (name, node_id, foreign_node, remote_host, bridge_port, "
            "ports, secret) VALUES ('t', ?, ?, '198.51.100.7', 3080, '[]', 's')", (A, F))
con.commit()
con.close()

RES = json.dumps({"side": "iran", "counters": {"rx": 10, "tx": 20},
                  "paths": {"domestic": OK, "intl": OK, "foreign": OK}})
jid = TUN.queue_job(A, "pathcheck", {"side": "iran"})
APP._pathcheck_result(TUN.get_node(A), jid, RES)
check("سمتِ ایران روی نودِ خودش", len(TUN.linkchecks(A, "iran")) == 1)

jid = TUN.queue_job(F, "pathcheck", {"side": "foreign", "for_node": A})
APP._pathcheck_result(TUN.get_node(F), jid, RES)
check("سرورِ خارجِ همان تانل می‌تواند برای نود بنویسد", len(TUN.linkchecks(A, "foreign")) == 1)

jid = TUN.queue_job(F, "pathcheck", {"side": "foreign", "for_node": B})
APP._pathcheck_result(TUN.get_node(F), jid, RES)
check("ولی برای نودی که تانلی با آن ندارد نه", len(TUN.linkchecks(B, "foreign")) == 0)

APP._pathcheck_result(TUN.get_node(A), jid, "{not json")
check("نتیجه‌ی خراب بی‌صدا گم نمی‌شود — رویداد ثبت می‌شود",
      any("عیب‌یابی" in (e.get("message") or "") for e in TUN.recent_events(10)))

# ═══════════════════════════════════════════════════════════
head("حلقه‌ی پنج‌دقیقه‌ای")
# ═══════════════════════════════════════════════════════════
# همین مسیر بود که `pathcheck` را در فهرستِ مجازِ کارها نداشت و هر دور
# با خطا می‌ایستاد — تستِ تابع‌ها آن را نمی‌دید، فقط اجرای خودِ حلقه.
TUN.touch_node(A, {"version": "1.6.0"})
TUN.touch_node(B, {"version": "1.5.2"})
TUN.touch_node(F, {"version": "1.6.0"})


def open_jobs(nid):
    c2 = TUN.conn()
    try:
        return [dict(r) for r in c2.execute(
            "SELECT action, payload FROM jobs WHERE node_id = ? AND action = 'pathcheck' "
            "AND status IN ('queued','taken')", (nid,))]
    finally:
        c2.close()


c2 = TUN.conn()
c2.execute("UPDATE jobs SET status = 'done' WHERE action = 'pathcheck'")
c2.commit()
c2.close()
APP._linkcheck_tick()
_ja = open_jobs(A)
check("ایجنتِ ۱.۶.۰ سنجش می‌گیرد، با پورتِ تانل",
      len(_ja) == 1 and json.loads(_ja[0]["payload"])["bridge_ports"] == [3080], str(_ja))
check("ایجنتِ قدیمی کاری نمی‌گیرد که نمی‌شناسد", open_jobs(B) == [])
_jf = open_jobs(F)
check("سرورِ خارجِ تانل، سمتِ خارج را برای همان نود می‌سنجد",
      len(_jf) == 1 and json.loads(_jf[0]["payload"]) == {
          "side": "foreign", "for_node": A,
          "iran_hosts": [{"host": "198.51.100.7", "port": 3080}]}, str(_jf))
APP._linkcheck_tick()
check("نودِ قطع: سنجش‌های کهنه پشتِ هم جمع نمی‌شوند", len(open_jobs(A)) == 1)
APP._linkcheck_tick(force=True)
check("«همین حالا بسنج» یکی تازه می‌گذارد", len(open_jobs(A)) == 2)
check("شمارنده‌ی خودِ سرورِ پنل هم ثبت شد (شناسه‌ی صفر)",
      TUN.traffic_summary(0)["lastSample"] is not None or LINK.net_counters() is None)

# ═══════════════════════════════════════════════════════════
head("یک دورِ کامل — سرهم‌کردنِ نتیجه")
# ═══════════════════════════════════════════════════════════
_real_probe, _real_peers, _real_cnt = LINK.probe_all, LINK.peer_ips, LINK.net_counters


def fake_probe(targets):
    out = []
    for t in targets:
        # روی سرورِ خارج ۲۲ بسته است و ۴۴۳ باز
        dead = t.get("port") == 22
        out.append({"host": t["host"], "port": t.get("port"),
                    "tcp": {"loss": 100} if dead else {"loss": 0, "avg": 90}})
    return out


LINK.probe_all, LINK.peer_ips = fake_probe, (lambda ports: ["203.0.113.9"])
LINK.net_counters = lambda text=None: {"rx": 1, "tx": 2}
r = LINK.run("iran", bridge_ports=[3080], panelVersion="x")
check("پارامترِ اضافه‌ی ایجنت (panelVersion) خطا نمی‌دهد", r["side"] == "iran")
check("برای هر آی‌پیِ خارج بهترین پورت — پورتِ بسته «قطع» نیست",
      len(r["paths"]["foreign"]) == 1 and r["paths"]["foreign"][0]["port"] == 443,
      str(r["paths"]["foreign"]))
check("سه مسیرِ سمتِ ایران و شمارنده", set(r["paths"]) == {"domestic", "intl", "foreign"}
      and r["counters"] == {"rx": 1, "tx": 2} and r["peers"] == ["203.0.113.9"])
r = LINK.run("foreign", iran_hosts=[{"host": "198.51.100.7", "port": 3080}, {"host": ""}])
check("سمتِ خارج: مقصدِ بی‌آدرس کنار می‌رود",
      set(r["paths"]) == {"iran", "intl"} and len(r["paths"]["iran"]) == 1)
LINK.probe_all, LINK.peer_ips, LINK.net_counters = _real_probe, _real_peers, _real_cnt

# ═══════════════════════════════════════════════════════════
head("ایجنت و پنل یک نسخه را می‌شناسند")
# ═══════════════════════════════════════════════════════════
AG = io.open(os.path.join(ROOT, "agent", "nexora-agent.py"), encoding="utf-8").read()
import re                       # noqa: E402
_av = re.search(r'^VERSION = "([\d.]+)"', AG, re.M).group(1)
check("ایجنتِ همین مخزن دستورِ pathcheck را دارد و نسخه‌اش کافی است",
      'action == "pathcheck"' in AG and not APP._older_than(_av, APP.AGENT_PATHCHECK),
      f"agent {_av} / need {APP.AGENT_PATHCHECK}")
check("ایجنت همان تابعِ linkcheck.run را صدا می‌زند",
      'remote_module(\n            "linkcheck", "run"' in AG)
check("پنل ماژول را به ایجنت می‌دهد", '"/api/agent/linkcheck.py"' in io.open(
    os.path.join(ROOT, "backend", "app.py"), encoding="utf-8").read())

print(f"\n  {PASS} پاس · {FAIL} شکست")
sys.exit(1 if FAIL else 0)
