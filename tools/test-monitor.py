#!/usr/bin/env python3
"""
تست منطق مانیتورینگ با داده‌ی شبیه‌سازی‌شده‌ی لینوکس.

چرا وجود دارد:
    آستانه‌ها همان چیزی هستند که به ادمین می‌گویند نگران باشد یا نه.
    یک آستانه‌ی اشتباه یعنی یا هشدار الکی (که بعد از چند بار نادیده
    گرفته می‌شود) یا سکوت در لحظه‌ی خطر. هر دو بدترند از نداشتن
    مانیتورینگ.

    ضمناً روی ویندوز /proc وجود ندارد، پس بدون شبیه‌سازی اصلاً
    نمی‌شود این کد را قبل از رفتن روی سرور سنجید.

اجرا:  python3 tools/test-monitor.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import monitor as M                                   # noqa: E402

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


# ═══ شبیه‌ساز ═══

class Fake:
    """یک سرور لینوکس ساختگی که می‌شود حالش را عوض کرد."""

    def __init__(self, mem_used_pct=40, disk_used_pct=30, load=0.5,
                 xray="active", updates=0, security=0, established=120,
                 firewall=True):
        self.firewall = firewall
        self.mem_used_pct = mem_used_pct
        self.disk_used_pct = disk_used_pct
        self.load = load
        self.xray = xray
        self.updates = updates
        self.security = security
        self.established = established

    # ── /proc ──
    def read(self, path, default=""):
        if path == "/proc/meminfo":
            total_kb = 4 * 1024 * 1024
            avail_kb = int(total_kb * (100 - self.mem_used_pct) / 100)
            return (f"MemTotal:       {total_kb} kB\n"
                    f"MemFree:        {avail_kb} kB\n"
                    f"MemAvailable:   {avail_kb} kB\n"
                    f"SwapTotal:      {2 * 1024 * 1024} kB\n"
                    f"SwapFree:       {2 * 1024 * 1024} kB\n")
        if path == "/proc/stat":
            return "cpu  100 0 100 800 0 0 0 0 0 0\n"
        if path == "/proc/net/dev":
            return ("Inter-|   Receive                    |  Transmit\n"
                    " face |bytes    packets errs drop fifo frame compressed multicast|"
                    "bytes    packets errs drop fifo colls carrier compressed\n"
                    "    lo: 100 1 0 0 0 0 0 0 100 1 0 0 0 0 0 0\n"
                    "  eth0: 1000000 10 0 0 0 0 0 0 2000000 20 0 0 0 0 0 0\n")
        if path == "/proc/uptime":
            return "86400.0 80000.0"
        return default

    # ── دستورها ──
    def run(self, cmd, timeout=8):
        c = " ".join(cmd)
        if cmd[0] == "df":
            total = 50 * 1024 ** 3
            used = int(total * self.disk_used_pct / 100)
            avail = total - used
            return True, ("Filesystem 1B-blocks Used Available Capacity Mounted on\n"
                          f"/dev/vda1 {total} {used} {avail} 1% /\n")
        if cmd[0] == "ps":
            return True, ("  PID COMMAND         %CPU %MEM ELAPSED\n"
                          " 1234 xray            42.5  8.1 100000\n"
                          " 2345 nginx            1.2  0.9  90000\n")
        if cmd[0] == "ss":
            if "established" in c:
                return True, "Netid State\n" + "\n".join(
                    ["tcp ESTAB"] * self.established)
            if "-tan" in c:
                return True, "ESTAB\n" * 10
            if "-tulpnH" in c:
                return True, (
                    'tcp LISTEN 0 128 0.0.0.0:22 0.0.0.0:* users:(("sshd",pid=1,fd=3))\n'
                    'tcp LISTEN 0 128 0.0.0.0:443 0.0.0.0:* users:(("xray",pid=2,fd=4))\n'
                    'tcp LISTEN 0 128 127.0.0.1:8100 0.0.0.0:* users:(("python3",pid=3,fd=5))\n'
                    'tcp LISTEN 0 128 0.0.0.0:9999 0.0.0.0:* users:(("weird",pid=4,fd=6))\n')
            return True, ""
        if cmd[0] == "systemctl" and cmd[1] == "is-active":
            return True, self.xray
        if cmd[0] == "systemctl" and cmd[1] == "show":
            name = cmd[2]
            state = self.xray if name == "xray" else "active"
            return True, (f"LoadState=loaded\nActiveState={state}\n"
                          f"SubState=running\nMainPID=10\n"
                          f"MemoryCurrent=52428800\nNRestarts=0\n")
        if cmd[0] == "journalctl":
            if "-u" in cmd and "xray" in cmd:
                return True, "-- No entries --"
            return True, ""
        if cmd[0] == "ufw":
            return True, ("Status: active\n" if self.firewall
                          else "Status: inactive\n")
        if cmd[0] == "fail2ban-client":
            return True, "Status\n|- Jail list:\tsshd\n"
        if cmd[0] == "apt-get":
            lines = []
            for i in range(self.updates):
                tag = "security" if i < self.security else "updates"
                lines.append(f"Inst pkg{i} [1.0] (1.1 Debian:12/{tag} [amd64])")
            return True, "\n".join(lines)
        return False, ""


def install(fake, *, has=lambda b: True, load=None):
    M._read = fake.read
    M._run = fake.run
    M._has = has
    os.getloadavg = lambda: (load if load is not None else fake.load,
                             fake.load, fake.load)
    M.SAMPLE = 0.01


def find(metrics, key):
    return next((m for m in metrics if m["key"] == key), None)


# ═══ سرور سالم ═══
head("سرور سالم")
install(Fake())
snap = M.snapshot()
check("سطح کلی سالم", snap["level"] == "ok",
      f"{snap['level']} · " + " / ".join(
          f"{m['key']}={m['value']}" for m in snap["metrics"] if m["level"] != "ok"))
check("همه‌ی بخش‌ها برگشتند",
      all(k in snap["sections"] for k in
          ("cpu", "memory", "disk", "network", "xray", "services", "ports")),
      str(list(snap["sections"])))
check("هر سنجه توضیح خطر دارد",
      all(m.get("why") for m in snap["metrics"] if m["level"] != "ok" or m["value"] is not None),
      str([m["key"] for m in snap["metrics"] if not m.get("why")]))

mem = find(snap["metrics"], "memory")
check("حافظه درصد درست", mem and abs(mem["value"] - 40) < 2, str(mem and mem["value"]))
check("حافظه سالم", mem and mem["level"] == "ok")

# ═══ حافظه‌ی پر ═══
head("حافظه‌ی پر")
install(Fake(mem_used_pct=97))
m = find(M.snapshot(include=["memory"])["metrics"], "memory")
check("۹۷٪ حافظه بحرانی است", m["level"] == "crit", str(m["value"]))
check("راهنمای عملی دارد", bool(m["hint"]))

install(Fake(mem_used_pct=88))
m = find(M.snapshot(include=["memory"])["metrics"], "memory")
check("۸۸٪ هشدار است نه بحران", m["level"] == "warn", str(m["value"]))

# ═══ دیسک ═══
head("دیسک")
install(Fake(disk_used_pct=95))
d = M.snapshot(include=["disk"])["metrics"][0]
check("۹۵٪ دیسک بحرانی", d["level"] == "crit", str(d["value"]))
check("دستور پاکسازی پیشنهاد می‌دهد", "journalctl" in d["hint"], d["hint"][:40])

install(Fake(disk_used_pct=50))
check("۵۰٪ دیسک سالم",
      M.snapshot(include=["disk"])["metrics"][0]["level"] == "ok")

# ═══ بار سیستم ═══
head("بار سیستم")
install(Fake(), load=0.4)
cores = os.cpu_count() or 1
lo = find(M.snapshot(include=["cpu"])["metrics"], "load")
check("بار کم سالم است", lo["level"] == "ok", str(lo["value"]))
check("توضیح، تعداد هسته را می‌گوید", M._fa(cores) in lo["why"], lo["why"][:60])
check("ارقام توضیح فارسی‌اند",
      not any(c.isdigit() and c.isascii() for c in lo["detail"]), lo["detail"])

install(Fake(), load=cores * 2.5)
lo = find(M.snapshot(include=["cpu"])["metrics"], "load")
check("بار ۲.۵ برابر هسته‌ها بحرانی", lo["level"] == "crit",
      f"{lo['value']} روی {cores} هسته")

# ═══ Xray ═══
head("Xray")
install(Fake(xray="active"))
x = find(M.snapshot(include=["xray"])["metrics"], "xray")
check("Xray روشن سالم", x["level"] == "ok", str(x["value"]))

install(Fake(xray="inactive"))
snap = M.snapshot(include=["xray"])
x = find(snap["metrics"], "xray")
check("Xray خاموش بحرانی است", x["level"] == "crit", str(x["value"]))
check("دستور ری‌استارت می‌دهد", "systemctl restart xray" in x["hint"], x["hint"])
check("سطح کلی بحرانی می‌شود", snap["level"] == "crit")
check("تیتر مشکل را نشان می‌دهد", bool(snap["headline"]), snap["headline"])

# ═══ به‌روزرسانی ═══
head("به‌روزرسانی و امنیت")
install(Fake(updates=0))
check("بدون به‌روزرسانی سالم",
      find(M.snapshot(include=["packages"])["metrics"], "updates")["level"] == "ok")

install(Fake(updates=40, security=0))
u = find(M.snapshot(include=["packages"])["metrics"], "updates")
check("۴۰ بسته‌ی عادی هشدار", u["level"] == "warn", str(u["value"]))

install(Fake(updates=5, security=2))
u = find(M.snapshot(include=["packages"])["metrics"], "updates")
check("حتی ۲ بسته‌ی امنیتی بحرانی است", u["level"] == "crit",
      f"{u['value']} بسته / {u['extra']['security']} امنیتی")
check("توضیحش دلیل فوریت را می‌گوید", "امنیت" in u["why"] or "حفره" in u["why"])

install(Fake(), has=lambda b: b != "fail2ban-client")
f2b = find(M.snapshot(include=["security"])["metrics"], "fail2ban")
check("نبود fail2ban هشدار می‌دهد", f2b["level"] == "warn", str(f2b["value"]))

install(Fake(firewall=False))
fw = find(M.snapshot(include=["security"])["metrics"], "firewall")
check("فایروال خاموش هشدار می‌دهد", fw["level"] == "warn", str(fw["value"]))
install(Fake(firewall=True))
fw = find(M.snapshot(include=["security"])["metrics"], "firewall")
check("فایروال روشن سالم است", fw["level"] == "ok", str(fw["value"]))

# ═══ پورت‌ها ═══
head("پورت‌های باز")
install(Fake())
ports = M.snapshot(include=["ports"])["sections"]["ports"]
by = {p["port"]: p for p in ports}
check("پورت‌ها خوانده شدند", len(ports) >= 3, str(sorted(by)))
check("SSH شناخته‌شده است", by[22]["known"] == "SSH")
check("۴۴۳ ریسک پایین", by[443]["risk"] == "low", by[443]["risk"])
check("پورت ناشناخته‌ی عمومی علامت می‌خورد", by[9999]["risk"] == "medium",
      by[9999]["risk"])
check("پورت لوکال عمومی حساب نمی‌شود", by[8100]["public"] is False)
check("نام پردازه استخراج شد", by[443]["process"] == "xray", by[443]["process"])
check("پرریسک‌ها اول فهرست‌اند", ports[0]["risk"] != "low")

# ═══ اتصال‌ها ═══
head("شبکه")
install(Fake(established=50))
c = find(M.snapshot(include=["network"])["metrics"], "connections")
check("۵۰ اتصال سالم", c["level"] == "ok", str(c["value"]))

install(Fake(established=9500))
c = find(M.snapshot(include=["network"])["metrics"], "connections")
check("۹۵۰۰ اتصال بحرانی", c["level"] == "crit", str(c["value"]))

# ═══ پردازه‌ها ═══
head("پردازه‌ها")
install(Fake())
procs = M.snapshot(include=["processes"])["sections"]["processes"]
check("سنگین‌ترین پردازه‌ها خوانده شد", len(procs) == 2, str(len(procs)))
check("مرتب بر اساس پردازنده", procs[0]["name"] == "xray", procs[0]["name"])
check("درصدها عددی‌اند", isinstance(procs[0]["cpu"], float))

# ═══ مقاومت ═══
head("مقاومت در برابر خرابی")


def boom(*a, **k):
    raise RuntimeError("خراب")


M._run = boom
snap = M.snapshot(include=["disk", "memory"])
check("خطای یک بخش کل خروجی را نمی‌شکند", "level" in snap and "metrics" in snap)
check("بخش خراب به‌عنوان هشدار می‌آید",
      any(m["level"] == "warn" for m in snap["metrics"]) or snap["level"] != "crit")

print(f"\n{D}{'─' * 46}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
