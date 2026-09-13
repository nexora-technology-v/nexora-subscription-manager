#!/usr/bin/env python3
"""
صف کارهای ایجنت — کاری که برداشته می‌شود ولی جواب نمی‌دهد.

چرا وجود دارد:
    وقتی ایجنت یک کار را برمی‌دارد، وضعیتش «taken» می‌شود. اگر بعدش
    نتیجه نرسد — ایجنت ری‌استارت شد، شبکه قطع شد، پردازه کشته شد —
    کار *برای همیشه* روی taken می‌ماند.

    پنل این را تشخیص می‌داد (هم nexora check، هم صفحه‌ی عیب‌یابی
    می‌گفتند «ایجنت کار را برداشته ولی نتیجه‌ای نفرستاده») ولی هیچ‌جا
    کاری برایش نمی‌کرد. مدیر دکمه را می‌زد، هیچ اتفاقی نمی‌افتاد، و
    تنها راه این بود که دوباره بزند و امیدوار باشد.

    همه‌ی دستورهای مجاز idempotent‌اند — apply و restart و sysmon را
    می‌شود دوباره اجرا کرد — پس تلاش دوباره امن است.

اجرا:  python3 tools/test-jobs.py
"""
import importlib.util
import io
import os
import sys
import tempfile
from datetime import datetime, timedelta

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


def _raises(fn):
    try:
        fn()
        return False
    except Exception:
        return True


def head(t):
    print(f"\n{D}── {t} ──{X}")


TMP = tempfile.mkdtemp()
os.environ["TUNNEL_DB_PATH"] = os.path.join(TMP, "tunnels.db")

spec = importlib.util.spec_from_file_location(
    "tunnels", os.path.join(ROOT, "backend", "tunnels.py"))
T = importlib.util.module_from_spec(spec)
sys.modules["tunnels"] = T
spec.loader.exec_module(T)

node = T.create_node("سرور ایران")
NID = node["id"]


def status_of(jid):
    c = T.conn()
    try:
        r = c.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
        return dict(r) if r else None
    finally:
        c.close()


def age_job(jid, minutes):
    """کار را چند دقیقه به عقب می‌بریم، مثل ایجنتی که جواب نداده."""
    c = T.conn()
    try:
        c.execute("UPDATE jobs SET taken_at=? WHERE id=?",
                  ((datetime.now() - timedelta(minutes=minutes))
                   .isoformat(timespec="seconds"), jid))
        c.commit()
    finally:
        c.close()


# ═══════════════════════════════════════════════════════════
head("چرخه‌ی عادی یک کار")

jid = T.queue_job(NID, "sysmon")
check("کار در صف می‌نشیند", status_of(jid)["status"] == "queued")

taken = T.take_jobs(NID)
check("ایجنت برش می‌دارد", len(taken) == 1 and taken[0]["id"] == jid)
check("وضعیتش taken می‌شود", status_of(jid)["status"] == "taken")

check("دوباره برداشته نمی‌شود", T.take_jobs(NID) == [],
      "وگرنه دو ایجنت یک کار را هم‌زمان اجرا می‌کنند")

T.finish_job(jid, True, "گزارش آماده است")
check("نتیجه ثبت می‌شود", status_of(jid)["status"] == "done")
check("متن نتیجه می‌ماند", "گزارش" in (status_of(jid)["result"] or ""))

head("کاری که برداشته شد و جواب نداد")

lost = T.queue_job(NID, "sysmon")
T.take_jobs(NID)
check("برداشته شد", status_of(lost)["status"] == "taken")

age_job(lost, 10)          # ده دقیقه بی‌جواب
again = T.take_jobs(NID)
check("بعد از مهلت دوباره به ایجنت داده می‌شود",
      any(j["id"] == lost for j in again),
      "قبلاً تا ابد روی taken می‌ماند و مدیر باید دستی دوباره می‌زد")
check("شمارنده‌ی تلاش بالا می‌رود",
      (status_of(lost).get("attempts") or 0) >= 1,
      str(status_of(lost).get("attempts")))

head("ولی بی‌نهایت تلاش نمی‌کند")

for _ in range(6):
    age_job(lost, 10)
    T.take_jobs(NID)

st = status_of(lost)
check("سرانجام شکست‌خورده علامت می‌خورد", st["status"] == "failed", st["status"])
check("و دلیلش نوشته می‌شود", "پاسخ" in (st["result"] or "")
      or "تلاش" in (st["result"] or ""), (st["result"] or "")[:60])
check("دیگر برداشته نمی‌شود",
      not any(j["id"] == lost for j in T.take_jobs(NID)),
      "وگرنه حلقه‌ی بی‌پایان می‌شود")

head("کار تازه دست‌نخورده می‌ماند")

fresh = T.queue_job(NID, "sysmon")
T.take_jobs(NID)
age_job(fresh, 1)          # فقط یک دقیقه — هنوز در حال اجراست
T.take_jobs(NID)
check("کاری که تازه برداشته شده دوباره صف نمی‌شود",
      status_of(fresh)["status"] == "taken",
      "sysmon روی سرور کند چند دقیقه طول می‌کشد")

head("کار نود دیگر قاطی نمی‌شود")

other = T.create_node("سرور دوم")
mine = T.queue_job(NID, "health")
theirs = T.queue_job(other["id"], "health")
got = [j["id"] for j in T.take_jobs(NID)]
check("فقط کار همان نود برداشته می‌شود",
      mine in got and theirs not in got,
      f"{got}")

age_job(theirs, 30)
T.take_jobs(NID)
check("کار گیرکرده‌ی نود دیگر هم دست نمی‌خورد",
      status_of(theirs)["status"] == "queued",
      "هر نود فقط مال خودش را جارو می‌کند")

head("دستور نامجاز اصلاً وارد صف نمی‌شود")

try:
    T.queue_job(NID, "rm -rf /")
    check("دستور ناشناخته رد می‌شود", False, "پذیرفته شد!")
except ValueError:
    check("دستور ناشناخته رد می‌شود", True, "ValueError")

check("همه‌ی دستورهای مجاز idempotent‌اند",
      T.ALLOWED_ACTIONS <= {"install", "apply", "start", "stop", "restart",
                            "remove", "status", "logs", "ping", "monitor",
                            "health", "sysmon", "firewall", "update_agent"},
      "تلاش دوباره فقط وقتی امن است که اجرای دوباره ضرری نداشته باشد")


head("پورت‌هایی که کنار گذاشته می‌شوند، بی‌صدا نمی‌روند")

# قبلاً هر ردیف نامعتبر با continue حذف می‌شد. مدیر سه پورت وارد
# می‌کرد، تانل با دوتا ساخته می‌شد، و هیچ‌جا نمی‌گفت سومی کجا رفت.
# بعداً که آن پورت کار نمی‌کرد، هیچ سرنخی نبود.

ok, dropped = T.validate_ports([443, 22, 80, "abc", 99999], report=True)
check("پورت‌های معتبر می‌مانند",
      [p["local"] for p in ok] == [443, 80],
      str([p["local"] for p in ok]))
check("SSH کنار گذاشته می‌شود و دلیلش می‌آید",
      any(v == "22" and "SSH" in why for v, why in dropped),
      str(dropped))
check("متنِ بی‌معنی هم گزارش می‌شود",
      any("عدد نیست" in why for _, why in dropped))
check("پورت خارج از بازه هم", any("۶۵۵۳۵" in why for _, why in dropped))
check("بدون report رفتار قبلی می‌ماند",
      T.validate_ports([443, 22]) == [{"local": 443, "remote": 443}],
      "کدی که این را صدا می‌زند نباید بشکند")

check("زوجِ local/remote پشتیبانی می‌شود",
      T.validate_ports([{"local": 8080, "remote": 80}])
      == [{"local": 8080, "remote": 80}])
check("remote خالی یعنی همان local",
      T.validate_ports([{"local": 8080}]) == [{"local": 8080, "remote": 8080}])

tid = T.create_tunnel({
    "name": "تست پورت", "node_id": NID, "remote_host": "1.2.3.4",
    "ports": [443, 22, 80],
})
evs = [e["message"] for e in T.recent_events(20)]
check("تانل ساخته می‌شود", bool(tid))
check("و رویداد هشدار برای پورت حذف‌شده ثبت می‌شود",
      any("اضافه نشدند" in m and "22" in m for m in evs),
      next((m for m in evs if "اضافه نشدند" in m), "هیچ رویدادی"))

try:
    T.create_tunnel({"name": "همه خراب", "node_id": NID,
                     "remote_host": "1.2.3.4", "ports": [22, "abc"]})
    check("وقتی هیچ پورتی نماند، خطا می‌دهد", False, "ساخته شد!")
except ValueError as e:
    check("وقتی هیچ پورتی نماند، خطا می‌دهد", True, str(e)[:70])
    check("و خطا می‌گوید چرا", "SSH" in str(e) or "عدد نیست" in str(e),
          "نه فقط «حداقل یک پورت لازم است»")



head("هر موتور، پورت‌ها را در جهت درست می‌بندد")

# قاعده‌ای که خودِ backhaul در مستندش نوشته:
#
#     مشتری ──► سرور ایران ──[تانل]──► سرور خارج (3x-ui)
#
#     local  = پورتی که روی سرور ایران باز می‌شود؛ مشتری به این وصل است
#     remote = پورت سرویس واقعی روی سرور خارج
#
# «اشتباه گرفتن این دو یعنی تانل بالا می‌آید ولی هیچ ترافیکی رد
# نمی‌شود.» تا وقتی local و remote یکی‌اند — حالت پیش‌فرض پنل — هیچ‌کس
# متوجه نمی‌شود؛ اولین نگاشتِ نامتقارن ترافیک را به پورت اشتباه
# می‌فرستد.
#
# هر موتور نگاشت را جای دیگری اعلام می‌کند (backhaul سمت ایران،
# chisel سمت خارج) پس این‌جا خروجی دقیقِ هرکدام سنجیده می‌شود، نه یک
# قاعده‌ی کلی.

IRAN_PORT, FOREIGN_PORT = 8443, 8080

TPL = {
    "name": "تست", "secret": "s3cret",
    "remote_host": "203.0.113.9", "bridge_port": 3080,
    "ports": [{"local": IRAN_PORT, "remote": FOREIGN_PORT}],
    "options": {},
}


def cfg(eng, side):
    return T.build_config(
        dict(TPL, engine=eng,
             transport=T.ENGINES[eng]["default_transport"]), side)


# ── Backhaul: نگاشت را سمت ایران می‌نویسد ──
check("Backhaul: نگاشت «ایران=خارج» درست است",
      f'"{IRAN_PORT}={FOREIGN_PORT}"' in cfg("backhaul", "iran"),
      "برعکسش یعنی ایران روی پورت خارج گوش می‌دهد")
check("Backhaul: سمت ایران [server] است",
      "[server]" in cfg("backhaul", "iran"))
check("Backhaul: سمت خارج [client] است",
      "[client]" in cfg("backhaul", "foreign"))

# ── Chisel: نگاشت را سمت خارج می‌نویسد ──
check("Chisel: تانل معکوس درست است",
      f"R:0.0.0.0:{IRAN_PORT}:127.0.0.1:{FOREIGN_PORT}"
      in cfg("chisel", "foreign"),
      "R:<پورتی که ایران باز می‌کند>:<سرویس واقعی روی خارج>")
check("Chisel: سمت ایران server --reverse است",
      "--reverse" in cfg("chisel", "iran"))

# ── Rathole: هر دو طرف ──
check("Rathole: ایران پورت مشتری را باز می‌کند",
      f'bind_addr = "0.0.0.0:{IRAN_PORT}"' in cfg("rathole", "iran"),
      "قبلاً پورت سرویسِ خارج را باز می‌کرد")
check("Rathole: خارج به سرویس واقعی وصل می‌شود",
      f'local_addr = "127.0.0.1:{FOREIGN_PORT}"' in cfg("rathole", "foreign"),
      "قبلاً به پورت ایران وصل می‌شد — یعنی به هیچ‌جا")
check("Rathole: نام سرویس دو طرف یکی است",
      set(l for l in cfg("rathole", "iran").split("\n") if l.startswith("[server.services."))
      and cfg("rathole", "iran").count(".services.p") ==
          cfg("rathole", "foreign").count(".services.p"),
      "اگر نام‌ها یکی نباشند rathole جفتشان نمی‌کند")

# ── FRP ──
frpc = cfg("frp", "foreign")
check("FRP: سرویس واقعی روی پورت خارج است",
      f"localPort = {FOREIGN_PORT}" in frpc,
      "localPort یعنی پورت روی همان ماشینِ frpc — یعنی سرور خارج")
check("FRP: پورت منتشرشده روی ایران، پورت مشتری است",
      f"remotePort = {IRAN_PORT}" in frpc,
      "remotePort یعنی پورتی که frps (ایران) باز می‌کند")
check("FRP: سمت ایران فقط bindPort دارد",
      f"bindPort = {TPL['bridge_port']}" in cfg("frp", "iran"))

# ── GOST ──
gforeign = cfg("gost", "foreign")
check("GOST: از rtcp استفاده می‌کند",
      "rtcp" in gforeign,
      "با handler: tcp فقط یک پراکسی رو به جلو بود — ایران هیچ پورتی باز نمی‌کرد")
check("GOST: پورتی که ایران باز می‌کند اعلام می‌شود",
      f"addr: :{IRAN_PORT}" in gforeign)
check("GOST: مقصد، سرویس واقعی روی خارج است",
      f"127.0.0.1:{FOREIGN_PORT}" in gforeign,
      "بدون forwarder، ترافیک به هیچ‌جا نمی‌رفت")
check("GOST: سمت ایران relay را می‌پذیرد",
      "type: relay" in cfg("gost", "iran"))

head("کانفیگ تولیدشده واقعاً قابل‌خواندن است")

# یک کانفیگ خراب روی سرور یعنی سرویسی که بالا نمی‌آید و خطایش هم
# فقط در journalctl آن ماشین دیده می‌شود. این‌جا قبل از فرستادن
# می‌سنجیمش.
try:
    import yaml as _yaml
except ImportError:
    _yaml = None

if _yaml:
    for side in ("iran", "foreign"):
        try:
            doc = _yaml.safe_load(cfg("gost", side))
            good = isinstance(doc, dict) and "services" in doc
        except Exception as e:
            doc, good = None, False
            print(f"       {D}{e}{X}")
        check(f"GOST ({side}): YAML معتبر است", good)
    fdoc = _yaml.safe_load(cfg("gost", "foreign"))
    check("GOST: مقصد forwarder واقعاً ثبت شده",
          fdoc["services"][0]["forwarder"]["nodes"][0]["addr"]
          == f"127.0.0.1:{FOREIGN_PORT}",
          str(fdoc["services"][0].get("forwarder")))
else:
    check("YAML نصب نیست — این بررسی رد شد", True, "pip install pyyaml")

try:
    import tomllib as _toml
except ImportError:
    try:
        import tomli as _toml
    except ImportError:
        _toml = None

if _toml:
    for eng in ("backhaul", "rathole", "frp"):
        for side in ("iran", "foreign"):
            try:
                _toml.loads(cfg(eng, side))
                good = True
            except Exception as e:
                good = False
                print(f"       {D}{e}{X}")
            check(f"{T.ENGINES[eng]['name']} ({side}): TOML معتبر است", good)
else:
    check("TOML نصب نیست — این بررسی رد شد", True)


head("چیزهایی که در هر پنج موتور باید باشد")

for eng in sorted(T.ENGINES):
    iran, foreign = cfg(eng, "iran"), cfg(eng, "foreign")
    check(f"{T.ENGINES[eng]['name']}: راز در هر دو طرف",
          "s3cret" in iran and "s3cret" in foreign)
    check(f"{T.ENGINES[eng]['name']}: خارج آدرس ایران را دارد",
          "203.0.113.9" in foreign,
          "بدون آن نمی‌داند به کجا وصل شود")
    check(f"{T.ENGINES[eng]['name']}: پورت ارتباط در هر دو طرف",
          "3080" in iran and "3080" in foreign)

check("موتور ناشناخته رد می‌شود",
      _raises(lambda: T.build_config(dict(TPL, engine="هیچ"), "iran")))


# ═══════════════════════════════════════════════════════════
head("تانلی که قطع است نباید «نامشخص» گزارش شود")

# ایجنت برای پورت مرده {"ok": False, "loss": 100} می‌فرستد — یعنی
# دقیقاً می‌داند صد درصد قطع است. ثبت‌کننده اولین پورتِ *سالم* را
# برمی‌داشت و بقیه را دور می‌ریخت، پس وقتی هیچ پورتی سالم نبود هیچ
# عددی ثبت نمی‌شد و کیفیت «نامشخص» می‌ماند — برای تانلی که کار
# نمی‌کرد. و وقتی نصف پورت‌ها مرده بودند، «عالی» گزارش می‌شد.

TUN_ID = T.create_tunnel({
    "name": "سنجش", "engine": "backhaul", "node_id": NID,
    "remote_host": "1.2.3.4", "ports": [443, 8443],
})

DEAD = {"tcp": {"443": {"ok": False, "loss": 100, "tries": 5},
                "8443": {"ok": False, "loss": 100, "tries": 5}}}
HALF = {"tcp": {"443": {"ok": True, "avg": 40.0, "min": 38.0, "max": 44.0,
                        "jitter": 2.0, "loss": 0},
                "8443": {"ok": False, "loss": 100, "tries": 5}}}
GOOD = {"tcp": {"443": {"ok": True, "avg": 40.0, "min": 38.0, "max": 44.0,
                        "jitter": 2.0, "loss": 0},
                "8443": {"ok": True, "avg": 50.0, "min": 46.0, "max": 55.0,
                         "jitter": 3.0, "loss": 0}}}

d = T._tcp_summary(DEAD["tcp"])
check("قطعِ کامل صد درصد پرت ثبت می‌کند", d.get("loss") == 100, str(d.get("loss")))
check("و تاخیری ادعا نمی‌کند", d.get("avg") is None)
check("و می‌گوید چند پورت از چند تا بالاست",
      d.get("up") == 0 and d.get("ports") == 2)

h = T._tcp_summary(HALF["tcp"])
check("یک پورت مرده از دو تا یعنی ۵۰ درصد پرت", h.get("loss") == 50,
      f"قبلاً ۰ ثبت می‌شد — «عالی» برای تانلی که نصفش مرده بود")
check("تاخیر فقط از پورت‌های سالم می‌آید", h.get("avg") == 40.0, str(h.get("avg")))

g = T._tcp_summary(GOOD["tcp"])
check("سالم: میانگین هر دو پورت", g.get("avg") == 45.0, str(g.get("avg")))
check("کمینه و بیشینه از کل پورت‌ها",
      g.get("min") == 38.0 and g.get("max") == 55.0)
check("فهرست خالی چیزی ثبت نمی‌کند", T._tcp_summary({}) == {})
check("ردیف بی‌شکل نمی‌شکندش", T._tcp_summary({"443": "خراب"}) == {})

T.save_metrics(TUN_ID, DEAD)
m = T.get_metrics(TUN_ID)
check("کیفیتِ تانلِ قطع «قطع» است", m["summary"]["quality"] == "قطع",
      m["summary"]["quality"])
check("و میانگین پرتش صد است", m["summary"]["lossAvg"] == 100)

TUN2 = T.create_tunnel({
    "name": "سنجش ۲", "engine": "backhaul", "node_id": NID,
    "remote_host": "1.2.3.4", "ports": [443],
})
T.save_metrics(TUN2, GOOD)
m2 = T.get_metrics(TUN2)
check("تانل سالم هنوز «عالی» است", m2["summary"]["quality"] == "عالی",
      m2["summary"]["quality"])

TUN3 = T.create_tunnel({
    "name": "سنجش ۳", "engine": "backhaul", "node_id": NID,
    "remote_host": "1.2.3.4", "ports": [443],
})
T.save_metrics(TUN3, {"tcp": {}})
m3 = T.get_metrics(TUN3)
check("سنجشِ بی‌داده هنوز «نامشخص» است", m3["summary"]["quality"] == "نامشخص",
      "نبودِ خبر با خبرِ بد فرق دارد")

JSX = io.open(os.path.join(ROOT, "frontend", "src", "sections", "tunnel.jsx"),
              encoding="utf-8").read()
check("پنل برای «قطع» رنگ دارد", '"قطع": "var(--danger)"' in JSX,
      "کلید ناشناخته خاکستری می‌شد — رنگِ «نمی‌دانم»")


print(f"\n{D}{'─' * 50}{X}")
color = G if not _fail else R
# ═══════════════════════════════════════════════════════════
head("ویرایش تانل باید همان‌قدر سخت‌گیر باشد که ساختش")

# ساخت تانل پروتکل و پورت ارتباط و آدرس را بررسی می‌کرد، ویرایش
# هیچ‌کدام را. همان مقداری که موقع ساخت رد می‌شد با یک PUT می‌نشست،
# بی‌هیچ خطایی — و تنها نشانه‌اش این بود که تانل کار نمی‌کرد.

EDIT_ID = T.create_tunnel({
    "name": "ویرایش", "engine": "backhaul", "node_id": NID,
    "remote_host": "1.2.3.4", "ports": [443],
})

check("پروتکلی که موتور نمی‌شناسد رد می‌شود",
      _raises(lambda: T.update_tunnel(EDIT_ID, {"transport": "کبوتر"})))
check("پروتکل درست پذیرفته می‌شود",
      T.update_tunnel(EDIT_ID, {"transport": "ws"}) is True,
      "backhaul ws را می‌شناسد")
check("پورت ارتباط زیر ۱۰۲۴ رد می‌شود",
      _raises(lambda: T.update_tunnel(EDIT_ID, {"bridge_port": 80})))
check("پورت ارتباط خالی هم رد می‌شود — نه خطای انگلیسی int()",
      _raises(lambda: T.update_tunnel(EDIT_ID, {"bridge_port": ""})))
check("آدرس سرور خارجِ خالی رد می‌شود",
      _raises(lambda: T.update_tunnel(EDIT_ID, {"remote_host": "   "})))
check("نام خالی رد می‌شود",
      _raises(lambda: T.update_tunnel(EDIT_ID, {"name": ""})))
check("ویرایش معتبر هنوز می‌نشیند",
      T.update_tunnel(EDIT_ID, {"bridge_port": 3090,
                                "remote_host": "5.6.7.8"}) is True)
_e = T.get_tunnel(EDIT_ID)
check("و واقعاً ذخیره شد",
      _e["bridge_port"] == 3090 and _e["remote_host"] == "5.6.7.8",
      f"{_e['bridge_port']} / {_e['remote_host']}")


print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
