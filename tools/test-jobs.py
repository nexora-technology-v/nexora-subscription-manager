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



print(f"\n{D}{'─' * 50}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
