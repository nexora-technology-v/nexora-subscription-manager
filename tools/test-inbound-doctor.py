"""
تحلیلِ اینباندهای 3x-ui — هر قاعده با اینباندِ ساختگی، و مسیرِ پنل روی
یک x-ui.db ساختگی.

برگه: docs/specs/2026-09-26-live-tunnel-and-inbound-doctor.md

اجرا:  PYTHONIOENCODING=utf-8 python tools/test-inbound-doctor.py
"""
import hashlib
import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = tempfile.mkdtemp()
XDB = os.path.join(TMP, "x-ui.db")
os.environ["XUI_DB_PATH"] = XDB
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


spec = importlib.util.spec_from_file_location("inbounddoc_t", os.path.join(ROOT, "backend", "inbounddoc.py"))
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)

NOW = int(time.time() * 1000)


def inb(**kw):
    base = {"id": 1, "enable": 1, "port": 443, "protocol": "vless", "listen": "",
            "up": 0, "down": 0, "total": 0, "expiry_time": 0,
            "settings": {"clients": [{"email": "a", "enable": True, "flow": ""}]},
            "stream_settings": {"network": "tcp", "security": "none"},
            "sniffing": {"enabled": True, "routeOnly": True, "destOverride": ["http", "tls"]}}
    base.update(kw)
    for k in ("settings", "stream_settings", "sniffing"):
        if isinstance(base[k], dict):
            base[k] = json.dumps(base[k])
    return base


def env(**kw):
    e = {"now_ms": NOW, "listen_tcp": {443, 8443, 2053}, "listen_udp": {5000},
         "tunnel_ports": {3080}, "tunnels": True, "dup_ports": set(),
         "traffic": [{"email": "a", "enable": 1, "up": 0, "down": 0, "total": 0, "expiry_time": 0}],
         "reality": None, "cert_exp": {}}
    e.update(kw)
    return e


def ids(i, e=None):
    return [f["id"] for f in D.analyze(i, e or env())]


REAL = {"network": "tcp", "security": "reality",
        "realitySettings": {"dest": "www.example.com:443", "serverNames": ["www.example.com"],
                            "privateKey": "k", "shortIds": ["ab12", ""]}}

head("اینباندِ سالم")
check("VLESS + TCP سالم هیچ یافته‌ای ندارد", ids(inb()) == [], str(ids(inb())))

head("قطع")
check("خاموش", ids(inb(enable=0)) == ["disabled"])
check("تاریخِ خودِ اینباند گذشته", "expired" in ids(inb(expiry_time=NOW - 1000)))
check("سهمیه‌ی خودِ اینباند تمام", "quota" in ids(inb(total=100, up=60, down=40)))
check("اندازه‌گیری: هیچ‌کس روی پورت گوش نمی‌دهد", "not-listening" in ids(inb(port=9999)))
check("ولی وقتی ss نبود، ادعا نمی‌کنیم", "not-listening" not in ids(inb(port=9999), env(listen_tcp=None)))
check("UDP روی فهرستِ UDP سنجیده می‌شود",
      "not-listening" not in ids(inb(port=5000, stream_settings={"network": "kcp"})))
check("پورتِ تانل", "tunnel-port" in ids(inb(port=3080), env(listen_tcp={3080})))
check("پورتِ تکراری", "dup-port" in ids(inb(), env(dup_ports={443})))
check("هیچ کلاینتِ فعالی",
      "no-clients" in ids(inb(), env(traffic=[{"email": "a", "enable": 1, "up": 5, "down": 5,
                                               "total": 10, "expiry_time": 0}])))
check("کلاینتِ منقضی هم فعال نیست",
      "no-clients" in ids(inb(), env(traffic=[{"email": "a", "enable": 1, "up": 0, "down": 0,
                                               "total": 0, "expiry_time": NOW - 5}])))
check("vision روی ws", "vision-transport" in ids(inb(
    settings={"clients": [{"email": "a", "flow": "xtls-rprx-vision"}]},
    stream_settings={"network": "ws", "security": "none"})))

head("Reality — با نتیجه‌ی سنجشِ dest")
check("کلید خالی", "reality-key" in ids(inb(stream_settings={
    **REAL, "realitySettings": {**REAL["realitySettings"], "privateKey": ""}})))
check("shortId نامعتبر", "reality-sid" in ids(inb(stream_settings={
    **REAL, "realitySettings": {**REAL["realitySettings"], "shortIds": ["xyz"]}})))
_f = D.analyze(inb(stream_settings=REAL), env(reality={"reachable": False, "error": "timed out"}))
check("dest در دسترس نیست → قطع، با «لینک عوض می‌شود»",
      any(f["id"] == "reality-dest" and f["level"] == "bad" and f["sub"] for f in _f))
_f = D.analyze(inb(stream_settings=REAL), env(reality={
    "reachable": True, "ms": 40,
    "names": {"www.example.com": {"ok": False, "why": "cert", "error": "hostname mismatch"}}}))
check("serverName با گواهیِ dest نمی‌خواند", any(f["id"] == "reality-name" for f in _f))
_f = D.analyze(inb(stream_settings=REAL), env(reality={
    "reachable": True, "ms": 450, "names": {"www.example.com": {"ok": True, "tls": "TLSv1.3"}}}))
check("dest کند → هشدار", [f["id"] for f in _f] == ["reality-slow", "vision-missing"],
      str([f["id"] for f in _f]))
check("dest Xray جدید (target) هم خوانده می‌شود",
      D.reality_target({"target": "a.example:8443"}) == ("a.example", 8443))
check("همان dest خراب دوباره پیشنهاد نمی‌شود",
      not any(x.startswith("www.speedtest.net:") for x in D._dest_examples("www.speedtest.net")))
check("dest به خودِ اینباند", "reality-self" in ids(inb(stream_settings={
    **REAL, "realitySettings": {**REAL["realitySettings"], "dest": "443"}})))

head("TLS")
_tls = {"network": "tcp", "security": "tls",
        "tlsSettings": {"certificates": [{"certificateFile": "/c.pem"}]}}
check("گواهیِ منقضی", "cert-expired" in ids(inb(stream_settings=_tls),
                                           env(cert_exp={"/c.pem": NOW / 1000 - 10})))
check("گواهیِ رو به انقضا", "cert-soon" in ids(inb(stream_settings=_tls),
                                             env(cert_exp={"/c.pem": NOW / 1000 + 86400 * 3})))
check("گواهیِ نخواندنی ادعایی نمی‌سازد", ids(inb(stream_settings=_tls)) == [])

head("تانل و پیشنهادها")
check("UDP پشتِ تانل", "udp-behind-tunnel" in ids(inb(port=5000, stream_settings={"network": "kcp"})))
check("بی تانل، UDP مشکلی نیست",
      "udp-behind-tunnel" not in ids(inb(port=5000, stream_settings={"network": "kcp"}), env(tunnels=False)))
check("acceptProxyProtocol", "proxy-protocol" in ids(inb(stream_settings={
    "network": "tcp", "tcpSettings": {"acceptProxyProtocol": True}})))
check("فقط روی 127.0.0.1", "loopback" in ids(inb(listen="127.0.0.1")))
check("sniffing خاموش", "sniffing-off" in ids(inb(sniffing={"enabled": False})))
check("routeOnly خاموش", "sniffing-routeonly" in ids(inb(sniffing={"enabled": True})))
check("VMess → پیشنهادِ VLESS با «لینک عوض می‌شود»",
      any(f["id"] == "vmess" and f["sub"] for f in D.analyze(inb(protocol="vmess"), env())))
check("بدترین سطح", D.summary([{"level": "tip"}, {"level": "bad"}]) == "bad" and D.summary([]) == "ok")

# ═══════════════════════════════════════════════════════════
head("مسیرِ پنل روی x-ui.db ساختگی — و هیچ نوشتنی")
# ═══════════════════════════════════════════════════════════
con = sqlite3.connect(XDB)
con.executescript("""
CREATE TABLE inbounds (id INTEGER PRIMARY KEY, user_id INTEGER, up INTEGER, down INTEGER,
  total INTEGER, remark TEXT, enable INTEGER, expiry_time INTEGER, listen TEXT, port INTEGER,
  protocol TEXT, settings TEXT, stream_settings TEXT, tag TEXT, sniffing TEXT);
CREATE TABLE client_traffics (id INTEGER PRIMARY KEY, inbound_id INTEGER, enable INTEGER,
  email TEXT, up INTEGER, down INTEGER, expiry_time INTEGER, total INTEGER);
""")
for i in (inb(id=1, remark="اصلی", port=443), inb(id=2, remark="خاموش", port=8443, enable=0)):
    con.execute("INSERT INTO inbounds (id, up, down, total, remark, enable, expiry_time, listen, "
                "port, protocol, settings, stream_settings, sniffing) VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (i["id"], 1000, 2000, 0, i.get("remark"), i["enable"], 0, "", i["port"],
                 i["protocol"], i["settings"], i["stream_settings"], i["sniffing"]))
con.execute("INSERT INTO client_traffics (inbound_id, enable, email, up, down, expiry_time, total) "
            "VALUES (1, 1, 'a', 0, 0, 0, 0)")
con.commit()
con.close()
_before = hashlib.sha256(open(XDB, "rb").read()).hexdigest()

import app as APP              # noqa: E402
APP.check_auth = lambda pw: None


def _fake_reality(targets, timeout=4.0):
    # بی شبکه: apple سریع، microsoft کند، github بی h2، yahoo گواهیِ نامعتبر
    ms = {"www.apple.com": 40, "www.microsoft.com": 180, "github.com": 30, "www.yahoo.com": 20}
    out = {}
    for k, (h, _p, names) in targets.items():
        ok = h in ms
        out[k] = {"reachable": ok, "ms": ms.get(h), "names": {h: {
            "ok": ok and h != "www.yahoo.com", "h2": h != "github.com", "ms": ms.get(h)}}}
    return out


APP.INBDOC.probe_all_reality = _fake_reality
APP._listen_ports = lambda udp=False: None if udp else {443}
APP._inbound_conns = lambda ports, ips: {443: {"tunnel": 4, "direct": 1}}
r = APP.inbounds_doctor(fresh=0, x_admin_password="x")
rows = {x["id"]: x for x in r["inbounds"]}
check("هر دو اینباند برگشت", set(rows) == {1, 2})
check("خاموش «قطع» است", rows[2]["level"] == "bad" and rows[2]["findings"][0]["id"] == "disabled")
check("اتصال‌ها جدا: از تانل / مستقیم", rows[1]["conns"] == {"tunnel": 4, "direct": 1})
check("کلاینت‌ها شمرده شدند", rows[1]["clients"] == 1 and rows[1]["active"] == 1)

con = sqlite3.connect(XDB)
con.execute("UPDATE inbounds SET up = up + 30000 WHERE id = 1")
con.commit()
con.close()
APP._LIVE["inb"]["t"] -= 3.0
r = APP.inbounds_doctor(fresh=0, x_admin_password="x")
rate = {x["id"]: x for x in r["inbounds"]}[1]["rate"]
check("مصرفِ لحظه‌ای از تفاضل با بارِ قبلی", rate and 9000 <= rate["rx"] <= 11000, str(rate))
_before2 = hashlib.sha256(open(XDB, "rb").read()).hexdigest()
APP.inbounds_doctor(fresh=0, x_admin_password="x")
check("پنل هیچ چیزی در x-ui.db نمی‌نویسد",
      hashlib.sha256(open(XDB, "rb").read()).hexdigest() == _before2)

# ═══════════════════════════════════════════════════════════
head("پیشنهادها — «این را بسازید»، نه فقط «این خراب است»")
# ═══════════════════════════════════════════════════════════
_rk = D.rank_candidates(_fake_reality({h: (h, 443, [h]) for h in D.REALITY_CANDIDATES}))
check("دامنه‌های Reality: فقط سالم‌ها (TLS 1.3، گواهیِ درست، h2)، سریع‌ترین اول",
      [x["host"] for x in _rk] == ["www.apple.com", "www.microsoft.com"], str(_rk))
_rec = {x["id"]: x for x in r["recommend"]}
check("پنل پیشنهادِ دامنه را برمی‌گرداند",
      (_rec.get("reality-dest") or {}).get("domains", [{}])[0].get("host") == "www.apple.com",
      str(r["recommend"])[:120])
check("اینباندِ مستقیم با dest سریع‌ترین دامنه",
      ["dest", "www.apple.com:443"] in (_rec.get("direct-inbound") or {}).get("settings", []))
_i = [inb(id=1, remark="t", stream_settings={"network": "tcp", "security": "none"})]
_r2 = {x["id"]: x for x in D.recommend(_i, True, _rk)}
check("پشتِ تانل: اگر اینباندِ VLESS+TCP هست، همان را نام می‌برد نه «بسازید»",
      _r2["tunnel-inbound"]["have"] == "t" and _r2["tunnel-inbound"]["new"] is False)
check("بی تانل، پیشنهادِ اینباندِ پشتِ تانل نمی‌آید",
      "tunnel-inbound" not in {x["id"] for x in D.recommend(_i, False, _rk)})
_ir = [inb(id=2, stream_settings=REAL)]
check("Reality سالم هست → پیشنهادِ اینباندِ مستقیم نمی‌آید",
      "direct-inbound" not in {x["id"] for x in D.recommend(_ir, False, _rk, reality_ok=True)})
check("Reality خراب هست → پیشنهادِ اینباندِ مستقیم می‌آید",
      "direct-inbound" in {x["id"] for x in D.recommend(_ir, False, _rk, reality_ok=False)})

print(f"\n  {PASS} پاس · {FAIL} شکست")
sys.exit(1 if FAIL else 0)
