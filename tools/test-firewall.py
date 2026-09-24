#!/usr/bin/env python3
"""
تست فایروال.

چرا وجود دارد:
    این ماژول می‌تواند دسترسی SSH مدیر به سرور را قطع کند. اگر
    فایروال روشن شود و قاعده‌ای پورت ۲۲ را باز نگذاشته باشد، راه
    برگشتی جز کنسول ارائه‌دهنده نمی‌ماند. نگهبانِ همین حالت، و
    اعتبارسنجی ورودی‌ها، این‌جا تست می‌شوند.

اجرا:  python3 tools/test-firewall.py
"""
import io
import os
import sys

G, R, D, X = "\033[38;5;42m", "\033[38;5;203m", "\033[38;5;245m", "\033[0m"
_ok = _fail = 0

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
import firewall as F   # noqa: E402


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


SAMPLE = """Status: active

     To                         Action      From
     --                         ------      ----
[ 1] 22/tcp                     ALLOW IN    Anywhere
[ 2] 443/tcp                    ALLOW IN    Anywhere
[ 3] 2053/tcp                   ALLOW IN    Anywhere
[ 4] Anywhere                   DENY IN     91.99.12.4
[ 5] 22/tcp (v6)                ALLOW IN    Anywhere (v6)
"""

head("خواندن قواعد")
rules = F._parse_status(SAMPLE)
check("همه‌ی قواعد خوانده شدند", len(rules) == 5, str(len(rules)))
check("شماره‌ی قاعده درست است", rules[0]["num"] == 1)
check("پورت و پروتکل جدا شدند",
      rules[0]["port"] == 22 and rules[0]["proto"] == "tcp",
      f"{rules[0]['port']}/{rules[0]['proto']}")
check("عمل درست خوانده شد", rules[3]["action"] == "DENY", rules[3]["action"])
check("مبدأ درست خوانده شد", rules[3]["source"] == "91.99.12.4",
      rules[3]["source"])
check("SSH حیاتی علامت خورد", rules[0]["critical"] is True)
check("پورت عادی حیاتی نیست", rules[1]["critical"] is False)
check("قاعده‌ی حیاتی توضیح دارد", "SSH" in rules[0]["note"], rules[0]["note"])

head("نگهبان SSH")
no_ssh = [r for r in rules if r["port"] != 22]
check("روشن‌کردن بدون قاعده‌ی SSH خطرناک است",
      F._ssh_would_break(no_ssh, False) is True)
check("با قاعده‌ی SSH خطری نیست",
      F._ssh_would_break(rules, False) is False)
check("فایروالِ از قبل روشن، دوباره بررسی نمی‌شود",
      F._ssh_would_break(no_ssh, True) is False)

limit_ssh = [{"port": 22, "action": "LIMIT"}]
check("قاعده‌ی LIMIT هم SSH را باز نگه می‌دارد",
      F._ssh_would_break(limit_ssh, False) is False)

deny_ssh = [{"port": 22, "action": "DENY"}]
check("قاعده‌ی DENY روی ۲۲ محافظت حساب نمی‌شود",
      F._ssh_would_break(deny_ssh, False) is True)

head("اعتبارسنجی ورودی")
cases = [
    ("پورت غیرعددی", F.add_rule("خراب"), "شماره پورت نامعتبر"),
    ("پورت خارج از بازه", F.add_rule(99999), "پورت باید"),
    ("پورت صفر", F.add_rule(0), "پورت باید"),
    ("عمل نامعتبر", F.add_rule(80, action="نابود کن"), "عمل نامعتبر"),
    ("پروتکل نامعتبر", F.add_rule(80, proto="sctp"), "پروتکل نامعتبر"),
    ("مبدأ نامعتبر", F.add_rule(80, source="; rm -rf /"), "آدرس مبدأ نامعتبر"),
]
for label, (ok, note), expect in cases:
    check(label + " رد می‌شود", (not ok) and expect in note, note[:44])

ok, note = F.block_ip("نه‌آی‌پی")
check("بستن آدرس نامعتبر رد می‌شود", (not ok) and "نامعتبر" in note, note[:40])

head("پیشنهاد قواعد")

_avail, _status = F.available, F.status
F.available = lambda: True
F.status = lambda: {"ready": True, "installed": True, "active": True,
                    "sshProtected": True,
                    "rules": [{"port": 443, "action": "ALLOW"}]}

PORTS = [
    {"port": 22, "proto": "tcp", "process": "sshd", "public": True, "known": "SSH"},
    {"port": 443, "proto": "tcp", "process": "nginx", "public": True, "known": "HTTPS"},
    {"port": 8443, "proto": "tcp", "process": "xray", "public": True, "known": "Xray"},
    {"port": 23, "proto": "tcp", "process": "telnetd", "public": True, "known": ""},
    {"port": 3306, "proto": "tcp", "process": "mysqld", "public": True, "known": ""},
    {"port": 5432, "proto": "tcp", "process": "postgres", "public": False, "known": ""},
]
s = F.suggest(PORTS)

keep_ports = {k["port"] for k in s["keep"]}
close_ports = {k["port"] for k in s["close"]}
already = {a["port"] for a in s["already"]}

check("SSH در فهرست باز ماندن است", 22 in keep_ports, str(sorted(keep_ports)))
check("Xray باز می‌ماند", 8443 in keep_ports)
check("telnet بسته پیشنهاد می‌شود", 23 in close_ports, str(sorted(close_ports)))
check("mysql بسته پیشنهاد می‌شود", 3306 in close_ports)
check("پورت فقط داخلی اصلاً پیشنهاد نمی‌شود",
      5432 not in keep_ports and 5432 not in close_ports)
check("پورتی که از قبل قاعده دارد دوباره پیشنهاد نمی‌شود",
      443 in already and 443 not in keep_ports and 443 not in close_ports)
check("هر پیشنهاد دلیل دارد",
      all(x.get("why") for x in s["keep"] + s["close"]))
check("SSH دلیلش را توضیح می‌دهد",
      any("SSH" in k["why"] for k in s["keep"] if k["port"] == 22))

ok, note, res = F.apply_plan(s["close"], confirm=False)
check("اعمال بدون تایید رد می‌شود", (not ok) and "confirm" in note, note[:44])

F.available, F.status = _avail, _status

head("رفتار بدون ufw")
_real = F.available
F.available = lambda: False
st = F.status()
check("بدون ufw خطا نمی‌دهد", st.get("ready") is False and "rules" in st)
check("راهنمای نصب می‌دهد", "ufw" in (st.get("hint") or ""), st.get("hint"))
ok, note = F.enable()
check("روشن‌کردن بدون ufw ناموفق و بی‌خطر است", not ok, note[:40])
F.available = _real

# ═══════════════════════════════════════════════════════════
head("SSH همان‌جایی نیست که کد فکر می‌کرد")

# هر نگهبان این فایل عدد ۲۲ را ثابت در کد داشت. روی سروری که SSH
# را جابه‌جا کرده — کاری که هر راهنمای سخت‌سازی توصیه می‌کند — یک
# قاعده‌ی جامانده روی ۲۲ کافی بود تا sshProtected درست شود، هشدار
# رابط کاربری نیاید، و روشن‌کردن فایروال پورت واقعی SSH را ببندد.
# مسیر toggle ساعت‌شمار بازگشت هم ندارد.

CFG = os.path.join(os.environ.get("TEMP") or "/tmp", "nexora-sshd-test")
os.makedirs(CFG, exist_ok=True)
_cfg = os.path.join(CFG, "sshd_config")
io.open(_cfg, "w", encoding="utf-8").write(
    "# Port 22\n"
    "Port 2222\n"
    "ListenAddress 10.0.0.5:2022\n"
    "ListenAddress 0.0.0.0\n"
    "PermitRootLogin no\n")

_real_cfg, F.SSHD_CONFIG = F.SSHD_CONFIG, _cfg
_real_dir, F.SSHD_CONFIG_DIR = F.SSHD_CONFIG_DIR, os.path.join(CFG, "none.d")
F._SSH_CFG_CACHE["at"] = 0.0

ports = F.ssh_ports()
check("پورت جابه‌جاشده از پیکربندی خوانده شد", 2222 in ports, str(sorted(ports)))
check("ListenAddress با پورت هم حساب می‌شود", 2022 in ports)
check("خط کامنت‌شده شمرده نمی‌شود", 22 not in ports,
      "«# Port 22» یعنی ۲۲ دیگر باز نیست")
check("ListenAddress بی‌پورت چیزی اضافه نمی‌کند", ports == {2222, 2022},
      str(sorted(ports)))

check("سوکت واقعی sshd هم اضافه می‌شود",
      2200 in F.ssh_ports([{"port": 2200, "process": "sshd"}]),
      "اگر پیکربندی و چیزی که اجرا شده یکی نباشند، اجتماعشان امن‌تر است")
check("پردازه‌های دیگر اضافه نمی‌شوند",
      8443 not in F.ssh_ports([{"port": 8443, "process": "xray"}]))

# قاعده‌ای فقط روی ۲۲ — درست همان تله
LEFTOVER = [{"port": 22, "action": "ALLOW"}]
check("قاعده‌ی جامانده‌ی ۲۲ دیگر «محافظت‌شده» حساب نمی‌شود",
      F._ssh_would_break(LEFTOVER, active=False) is True,
      "پورت واقعی ۲۲۲۲ است و قاعده ندارد")
check("قاعده روی پورت واقعی کافی است",
      F._ssh_would_break([{"port": 2222, "action": "ALLOW"}],
                         active=False) is False)
check("LIMIT هم باز حساب می‌شود",
      F._ssh_would_break([{"port": 2222, "action": "LIMIT"}],
                         active=False) is False)

crit = F.critical_ports()
check("پورت واقعی SSH حیاتی علامت می‌خورد", crit.get(2222) == F.SSH_LABEL)
check("۲۲ هم حیاتی می‌ماند", 22 in crit,
      "هشدار اضافه بی‌ضرر است؛ هشدار جاافتاده نه")

added = F._parse_added("ufw allow 2222/tcp\nufw allow 443/tcp\n")
check("قاعده‌های ذخیره‌شده هم حیاتی علامت می‌خورند",
      added[0]["critical"] is True and added[1]["critical"] is False,
      "وقتی فایروال خاموش است، همین‌ها نمایش داده می‌شوند")

# بدون هیچ پیکربندی، رفتار قبلی می‌ماند
F.SSHD_CONFIG = os.path.join(CFG, "nope")
F._SSH_CFG_CACHE["at"] = 0.0
check("بدون پیکربندی، به ۲۲ برمی‌گردد", F.ssh_ports() == {22},
      "روی سرور بدون sshd_config رفتار عوض نمی‌شود")

F.SSHD_CONFIG, F.SSHD_CONFIG_DIR = _real_cfg, _real_dir
F._SSH_CFG_CACHE["at"] = 0.0

head("قاعده‌های v6")
# ufw هر قاعده را دو بار می‌سازد. پیش‌تر « (v6)» در مقصد جلوی خواندنِ پورت
# را می‌گرفت: SSHِ v6 «حیاتی» نبود و بی‌تأیید حذف می‌شد، و فهرست و
# شمارِ «درهای باز» دوبرابر می‌شد.
_v6 = rules[4]
check("پورتِ قاعده‌ی v6 خوانده می‌شود", _v6["port"] == 22 and _v6["proto"] == "tcp", str(_v6))
check("SSHِ v6 هم حیاتی است", _v6["critical"] is True)
check("پرچمِ v6 می‌خورد", _v6["v6"] is True and rules[0]["v6"] is False)

_calls = []
_state = {"out": SAMPLE}


def _fake_run(cmd, timeout=15):
    _calls.append(" ".join(cmd))
    if cmd[:2] == ["ufw", "status"]:
        return True, _state["out"]
    return True, "Rule deleted"


_real_run, _real_shutil = F._run, F.shutil
import types as _types  # noqa: E402
F._run = _fake_run
F.shutil = _types.SimpleNamespace(which=lambda n: "/usr/sbin/" + n)
F.UFW_DEFAULTS = os.path.join(CFG, "no-ufw-defaults")
_st = F.status()
check("فهرست جفتِ v6 را تکرار نمی‌کند", _st["ruleCount"] == 4,
      ", ".join(r["target"] for r in _st["rules"]))

_calls.clear()
_dok, _note = F.delete_rule(1, confirm_critical=True)
_dels = [c for c in _calls if "delete" in c]
check("حذفِ قاعده جفتِ v6 را هم برمی‌دارد، بزرگ‌تر اول",
      _dels == ["ufw --force delete 5", "ufw --force delete 1"], " | ".join(_dels))
check("پیام می‌گوید v6 هم رفت", _dok and "IPv6" in _note, _note)
_calls.clear()
F.delete_rule(2)
check("قاعده‌ی بی‌جفت فقط خودش حذف می‌شود",
      [c for c in _calls if "delete" in c] == ["ufw --force delete 2"])
# SSHِ v6ِ تنها — جفتِ v4اش با نسخه‌ی قبلی حذف شده بود و این یکی جا مانده
_state["out"] = SAMPLE.replace("[ 1] 22/tcp                     ALLOW IN    Anywhere\n", "")
_ok2, _n2 = F.delete_rule(5)
check("SSHِ v6ِ تنها بی‌تأیید حذف نمی‌شود", _ok2 is False and "SSH" in _n2, _n2)
_state["out"] = SAMPLE

head("سیاستِ پیش‌فرضِ ورودی")
# پیش‌تر فقط در خروجیِ `status numbered` می‌گشت که خطِ Default ندارد — پس
# همیشه «?» بود و یادداشتِ رابط هرگز دیده نشد
with open(os.path.join(CFG, "ufw-defaults"), "w", encoding="utf-8") as _f:
    _f.write('IPV6=yes\nDEFAULT_INPUT_POLICY="DROP"\nDEFAULT_OUTPUT_POLICY="ACCEPT"\n')
F.UFW_DEFAULTS = os.path.join(CFG, "ufw-defaults")
check("از /etc/default/ufw: DROP ← deny", F.status()["defaultIncoming"] == "deny")
with open(F.UFW_DEFAULTS, "w", encoding="utf-8") as _f:
    _f.write('DEFAULT_INPUT_POLICY="ACCEPT"\n')
check("ACCEPT ← allow", F.status()["defaultIncoming"] == "allow")
F.UFW_DEFAULTS = os.path.join(CFG, "missing")
_state["out"] = SAMPLE
F._run = lambda cmd, timeout=15: (True, SAMPLE + ("Default: deny (incoming), allow (outgoing)\n"
                                                   if "verbose" in cmd else ""))
check("بی‌فایل، از status verbose", F.status()["defaultIncoming"] == "deny")

head("سوکتِ موقتِ xray — یک قاعده برای پیشنهاد و پیش‌بررسی")
_L = [{"port": 443, "proto": "tcp", "process": "xray", "public": True, "known": "Xray"},
      {"port": 41877, "proto": "udp", "process": "xray", "public": True, "known": ""},
      {"port": 6379, "proto": "tcp", "process": "redis-server", "public": True, "known": ""}]
_real_x, _real_rl, _real_tp = F.xray_service_ports, F._read_listening, F.tunnel_ports_in_use
F.xray_service_ports = lambda: {443}
F._read_listening = lambda: _L
F.tunnel_ports_in_use = lambda: {}
_pf = F.preflight()
_sg = F.suggest(_L)
_pf_ports = {r["port"] for r in _pf["atRisk"] + _pf["covered"]}
check("پیش‌بررسی سوکتِ موقت را «بی‌قاعده» نمی‌شمارد", 41877 not in _pf_ports, str(sorted(_pf_ports)))
check("پیشنهاد هم کنارش می‌گذارد", any(e["port"] == 41877 for e in _sg["ephemeral"]))
check("پورتِ واقعیِ بی‌قاعده هنوز فهرست می‌شود", 6379 in _pf_ports)
F.xray_service_ports, F._read_listening, F.tunnel_ports_in_use = _real_x, _real_rl, _real_tp
F._run, F.shutil = _real_run, _real_shutil


# شمارنده نباید بازنویسی شده باشد — همان اشتباهی که test-admin-api یک‌بار
# داشت، این‌جا هم رخ داد: `_ok, _note = F.delete_rule(...)` شمارنده را صفر
# کرد و سوییتِ ۵۶تایی «۸ پاس» گزارش داد
_calls = io.open(__file__, encoding="utf-8").read().count("\ncheck(")
if _ok + _fail < _calls * 0.95:
    print(f"  {R}✗ شمارنده بازنویسی شده — {_ok + _fail} شمرده شد، ولی {_calls} فراخوانی در فایل هست{X}")
    _fail += 1

print(f"\n{D}{'─' * 46}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
