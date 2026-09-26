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
check("سمتِ خارج نسنجیده → «آنچه سنجیده می‌شود سالم است» و می‌گوید چه چیزی سنجیده نشده",
      v["side"] == "partial" and "خارج ← ایران" in v["reason"], v["reason"])
check("هیچ داده‌ای → «هنوز سنجشی نرسیده»", LINK.diagnose(None, None)["side"] == "unknown")
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
_PW = "test-pass-123"
APP.check_auth = lambda pw: None      # مسیرها مستقیم صدا زده می‌شوند؛ احراز جای دیگری سنجیده می‌شود

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

# سمتِ خارج حالا همین‌جا اجرا می‌شود — در تست بی شبکه‌ی واقعی: یک تانلِ
# دستی (backpack) که ما به پورتِ 8443 ایران زنگ می‌زنیم
MANUAL = "203.0.113.50"
_PROBED = []


def _fake_probe(targets):
    _PROBED[:] = targets
    return [{"host": t["host"], "port": t.get("port"),
             "tcp": {"loss": 0, "avg": 90}} for t in targets]


def _fake_conns(peers=None, conns=None, listening=None):
    return {"ok": True, "peers": {MANUAL: {
        "engine": "backpack", "conns": 3, "in": 0, "out": 3, "listen": [8443],
        "rtt": 120.0, "minrtt": 95.0, "retrans": 1, "segs": 400, "retransPct": 0.25,
        "sent": 10_000, "recv": 50_000, "idle": 10}}}


APP.LINK.probe_all, APP.LINK.tunnel_conns = _fake_probe, _fake_conns
APP.LINK.tcp_check = lambda host, ports=None, tries=3, timeout=3.0: {
    "host": host, "icmp": {"loss": 0, "avg": 100.0}, "mtu": {"max": 1500},
    "ports": {"8443": {"loss": 0, "open": 2, "refused": 0, "timeout": 0, "avg": 101.0}}}
APP._manual_peers = lambda max_age=30: {MANUAL: "تانل (backpack)"}
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
head("تانلِ دستی — بی‌ایجنت، بیرون از پنل")
# ═══════════════════════════════════════════════════════════
_local = TUN.linkchecks(0, "foreign")
check("سمتِ خارج همین‌جا سنجیده و ذخیره شد (شناسه‌ی صفر)", len(_local) >= 1)
check("تانلِ دستی با پورتِ شنونده‌اش سنجیده شد (ما به 8443 زنگ می‌زنیم)",
      {"host": MANUAL, "port": 8443} in [{"host": t["host"], "port": t.get("port")} for t in _PROBED],
      str(_PROBED[:3]))
check("تانلی که ایجنتِ خارج دارد، این‌جا دوباره سنجیده نمی‌شود",
      not any(t["host"] == "198.51.100.7" for t in _PROBED))
_d = APP._link_diag_data()
_m = next((n for n in _d["nodes"] if n["kind"] == "manual"), None)
check("تانلِ دستی یک «ارتباط» در صفحه است", _m is not None and _m["ip"] == MANUAL, str(_m and _m["name"]))
check("با سلامتِ خودِ تانل از کرنل",
      _m and _m["tunnel"]["now"]["conns"] == 3 and _m["tunnel"]["state"] == "ok"
      and _m["engine"] == "backpack")
check("و حکمِ ناقص، نه «هنوز داده نیست»",
      _m and _m["verdict"]["side"] == "partial" and "ایجنت" in _m["verdict"]["fix"],
      _m and _m["verdict"]["title"])
check("مسیرِ «خارج ← ایران» تاریخچه دارد", _m and len(next(
    p for p in _m["paths"] if p["key"] == "foreign_iran")["history"]) >= 1)

# ایجنت روی همان آی‌پی نصب می‌شود → همان ارتباط، نه دو تا
M = TUN.create_node("iran-manual", role="iran")["id"]
TUN.touch_node(M, {"version": "1.6.0", "ip": MANUAL})
_d = APP._link_diag_data()
check("ایجنت روی آی‌پیِ تانلِ دستی → یک ارتباط، به نامِ نود",
      sum(1 for n in _d["nodes"] if n["ip"] == MANUAL) == 1
      and any(n["kind"] == "agent" and n["name"] == "iran-manual" for n in _d["nodes"]))

# ═══════════════════════════════════════════════════════════
head("سلامتِ اتصالِ تانل از کرنل (ss -ti)")
# ═══════════════════════════════════════════════════════════
SSI = ("0 0 198.51.100.2:443 203.0.113.9:51514 users:((\"backhaul\",pid=12,fd=7))\n"
       "\t cubic rtt:120.5/30.2 bytes_sent:1000 bytes_received:5000 segs_out:200 "
       "lastsnd:40 lastrcv:20 retrans:0/6 minrtt:98.1\n"
       "0 0 198.51.100.2:40000 203.0.113.9:3080\n"
       "\t cubic rtt:140.1/10 bytes_sent:300 bytes_received:700 segs_out:100 retrans:0/0\n"
       "0 0 127.0.0.1:2000 127.0.0.1:443\n")
_c = LINK.parse_ss_info(SSI)
check("هر اتصال با جزئیاتِ کرنلش", len(_c) == 3 and _c[0]["rtt"] == 120.5
      and _c[0]["retrans"] == 6 and _c[0]["proc"] == "backhaul", str(_c[0]))
_t = LINK.tunnel_conns(peers=["203.0.113.9", "192.0.2.5"], conns=_c, listening={443})["peers"]
_g = _t.get("203.0.113.9") or {}
check("جهت: یکی او به ما، یکی ما به پورتِ 3080 او",
      _g.get("in") == 1 and _g.get("out") == 1 and _g.get("listen") == [3080], str(_g))
check("درصدِ ارسالِ دوباره از کلِ بسته‌ها", _g.get("retransPct") == 2.0)
check("localhost تانل نیست", "127.0.0.1" not in _t)
check("تانلی که پنل می‌شناسد ولی اتصالی ندارد → صفر اتصال، نه غایب",
      _t.get("192.0.2.5", {}).get("conns") == 0)
check("بی اتصال → قطع", LINK.tunnel_state({"conns": 0}) == "down")
check("ارسالِ دوباره‌ی زیاد → ناپایدار", LINK.tunnel_state({"conns": 2, "retransPct": 5}) == "lossy")
check("بی داده → نامشخص", LINK.tunnel_state(None) == "unknown")

v = LINK.diagnose(None, foreign(), tunnel={"conns": 0})
check("تانلِ بی‌اتصال با مسیرِ سالم → «تانل وصل نیست» و «مشکل از سرویسِ تانل»",
      v["side"] == "tunnel" and "سرویسِ تانل" in v["reason"], v["reason"])
v = LINK.diagnose(None, foreign(iran_=DEAD), tunnel={"conns": 3, "retransPct": 9, "rtt": 400})
check("بی ایجنتِ ایران و مسیرِ بد → «بینِ دو سرور یا خودِ سرورِ ایران» با پیشنهادِ ایجنت",
      v["side"] == "between-or-iran" and "ایجنت" in v["fix"] and "ارسالِ دوباره" in v["reason"],
      v["title"])

# ═══════════════════════════════════════════════════════════
head("«پینگ می‌رود ولی TCP نه» — کدام علت؟")
# ═══════════════════════════════════════════════════════════
PING = {"loss": 0, "avg": 100.0}


def port(open_=0, refused=0, rst=None, tries=3):
    v = {"open": open_, "refused": refused, "timeout": tries - open_ - refused,
         "loss": round((tries - open_ - refused) * 100 / tries), "tries": tries}
    if rst is not None:
        v["rst_ms"] = rst
    return v


def chk(ports, icmp=PING, mtu=1500):
    return {"host": "h", "icmp": icmp, "mtu": {"max": mtu},
            "ports": {str(k): v for k, v in ports.items()}}


def fids(c, tun=None, tp=(3080,)):
    return [x["id"] for x in LINK.tcp_findings(c, tun, tp)]


check("پینگ می‌رود، پورتِ تانل و بقیه بی‌جواب → TCP به آی‌پی بسته است",
      fids(chk({3080: port(), 443: port(), 22: port()})) == ["tcp-blocked"])
check("ولی بی پورتِ لازم، بی‌جوابیِ ۲۲ و ۴۴۳ (فایروال) هشدارِ دروغ نمی‌سازد",
      fids(chk({443: port(), 22: port()}), tp=()) == [])
check("نه پینگ نه TCP → آی‌پی در دسترس نیست",
      fids(chk({3080: port()}, icmp={"loss": 100})) == ["host-down"])
check("SYN ایران می‌رسد و دست‌دادن کامل نمی‌شود (SYN-RECV)",
      fids(chk({443: port()}), tun={"conns": 0, "synrecv": 3}, tp=()) == ["handshake-reverse"])
check("RST زودتر از رفت‌وبرگشتِ پینگ → جعلی",
      "rst-injected" in fids(chk({3080: port(refused=3, rst=6.0)})))
check("RST هم‌زمان با رفت‌وبرگشت → واقعی: سرویسِ تانل آن‌جا گوش نمی‌دهد",
      fids(chk({3080: port(refused=3, rst=98.0)})) == ["tunnel-port-closed"])
check("آی‌پی جواب می‌دهد ولی پورتِ تانل بی‌جواب → فیلترِ پورت",
      "tunnel-port-filtered" in fids(chk({3080: port(), 443: port(open_=3, tries=3)})))
check("MTU ۱۲۷۲ → قطع، با دستورِ محدودکردنِ MSS",
      any(x["id"] == "mtu" and x["level"] == "bad" and "--set-mss 1232" in x.get("cmd", "")
          for x in LINK.tcp_findings(chk({3080: port(open_=3)}, mtu=1272), None, (3080,))))
check("MTU ۱۳۷۲ → هشدار", any(x["id"] == "mtu" and x["level"] == "warn"
                              for x in LINK.tcp_findings(chk({3080: port(open_=3)}, mtu=1372), None, (3080,))))
check("SYN-SENT بی اتصال → دست‌دادن گیر کرده",
      "handshake-stuck" in fids(chk({3080: port(open_=3)}), tun={"conns": 0, "syn": 4}))
check("صفِ ارسالِ پر با backoff → داده گیر کرده",
      "data-stuck" in fids(chk({3080: port(open_=3)}), tun={"conns": 5, "stuck": 2}))
check("همه سالم → هیچ یافته‌ای", fids(chk({3080: port(open_=3), 443: port(open_=3)})) == [])

v = LINK.diagnose(None, foreign(), tunnel={"conns": 0, "syn": 2},
                  tcp=chk({3080: port(), 443: port()}), tunnel_ports=(3080,))
check("حکم: «پینگ می‌رود ولی TCP نه» بر «تانل وصل نیست» مقدم است",
      v["side"] == "tcp" and "TCP" in v["title"], v["title"])
v = LINK.diagnose(None, foreign(intl=DEAD), tcp=chk({3080: port()}), tunnel_ports=(3080,))
check("ولی اگر خودِ سرورِ خارج به بیرون نمی‌رسد، آن مقدم است", v["side"] == "foreign")

# tcp_probe: باز و «رد» روی همین ماشین، بی شبکه
import socket as _so           # noqa: E402
_srv = _so.socket()
_srv.bind(("127.0.0.1", 0))
_srv.listen(8)
_op = _srv.getsockname()[1]
_tmp = _so.socket()
_tmp.bind(("127.0.0.1", 0))
_closed = _tmp.getsockname()[1]
_tmp.close()
_r1 = LINK.tcp_probe("127.0.0.1", _op, tries=2, timeout=1)
_r2 = LINK.tcp_probe("127.0.0.1", _closed, tries=2, timeout=1)
_srv.close()
check("tcp_probe: باز", _r1["open"] == 2 and _r1["loss"] == 0, str(_r1))
check("tcp_probe: «رد» پرت نیست و زمانش ثبت می‌شود",
      _r2["refused"] + _r2["timeout"] == 2 and (_r2["refused"] == 0 or _r2["loss"] < 100)
      and (_r2["refused"] == 0 or "rst_ms" in _r2), str(_r2))

SSQ = ("0 12800 198.51.100.2:40000 203.0.113.9:3080 users:((\"backhaul\",pid=1,fd=3))\n"
       "\t cubic rtt:300/50 backoff:3 bytes_sent:100 segs_out:10 retrans:2/9\n")
_g = LINK.tunnel_conns(peers=["203.0.113.9"], conns=LINK.parse_ss_info(SSQ), listening=set(),
                       syn={})["peers"]["203.0.113.9"]
check("صفِ ارسالِ پر + backoff از کرنل خوانده می‌شود", _g["stuck"] == 1, str(_g))
_g = LINK.tunnel_conns(peers=["203.0.113.9"], conns=[], listening=set(),
                       syn={"203.0.113.9": 2})["peers"]["203.0.113.9"]
check("SYN-SENT بی اتصالِ برقرار", _g["syn"] == 2 and _g["conns"] == 0)

# ═══════════════════════════════════════════════════════════
head("فهرستِ موتورهای تانل با netid یکی است")
# ═══════════════════════════════════════════════════════════
NET = load("netid_t", "backend/netid.py")
check("نسخه‌ی پشتیبانِ ایجنت همان netid.TUNNEL_PROCS است",
      tuple(LINK._TUNNEL_PROCS_FALLBACK) == tuple(NET.TUNNEL_PROCS))

# ═══════════════════════════════════════════════════════════
head("آی‌پیِ واقعی پشتِ nginx")
# ═══════════════════════════════════════════════════════════


class _Req:
    def __init__(self, peer, headers):
        self.client = type("C", (), {"host": peer})()
        self.headers = headers


check("nginx فقط X-Real-IP می‌فرستد — همان خوانده می‌شود",
      APP._client_ip(_Req("127.0.0.1", {"x-real-ip": "203.0.113.77"})) == "203.0.113.77")
check("ولی از اینترنت باور نمی‌شود",
      APP._client_ip(_Req("100.64.0.9", {"x-real-ip": "203.0.113.77"})) == "100.64.0.9")

# ═══════════════════════════════════════════════════════════
head("نرخِ زنده")
# ═══════════════════════════════════════════════════════════
_seq = iter([{"rx": 1000, "tx": 2000}, {"rx": 4000, "tx": 2600}])
APP.LINK.net_counters = lambda text=None: next(_seq)
_calls = iter([10_000, 40_000])


def _live_conns(peers=None, conns=None, listening=None):
    r = _fake_conns()
    r["peers"][MANUAL]["recv"] = next(_calls)
    return r


APP.LINK.tunnel_conns = _live_conns
APP._LIVE.update(t=None, net=None, peers={})
APP.link_live(x_admin_password=_PW)
import time as _time           # noqa: E402
APP._LIVE["t"] -= 2.0          # دو ثانیه گذشت
_l = APP.link_live(x_admin_password=_PW)
check("نرخِ کارتِ شبکه از تفاضل با فراخوانیِ قبلی",
      _l["net"] and 1400 <= _l["net"]["rx"] <= 1600, str(_l["net"]))
check("نرخِ هر تانل هم", _l["peers"][MANUAL]["rate"]["rx"] >= 14000, str(_l["peers"][MANUAL]))

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

# ═══════════════════════════════════════════════════════════
head("کسره‌ی جدا به صفحه نمی‌رسد")
# ═══════════════════════════════════════════════════════════
# «flow ِ vision» روی صفحه «flow_vision» دیده می‌شد: کسره‌ی بعد از فاصله روی
# خودِ فاصله می‌نشیند و شبیهِ زیرخط است. دو بار در همین کار رخ داد.
import glob as _glob            # noqa: E402
_kas = []
for _p in (_glob.glob(os.path.join(ROOT, "backend", "*.py"))
           + _glob.glob(os.path.join(ROOT, "frontend", "src", "**", "*.js*"), recursive=True)):
    if " \u0650 " in io.open(_p, encoding="utf-8").read():
        _kas.append(os.path.relpath(_p, ROOT))
check("هیچ متنی کسره‌ی جدا ندارد", not _kas, "، ".join(_kas))

print(f"\n  {PASS} پاس · {FAIL} شکست")
sys.exit(1 if FAIL else 0)
