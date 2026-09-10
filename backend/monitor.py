"""
مانیتورینگ زنده‌ی سرور — مخصوص سروری که کارش VPN است.

فرق این با health.py:
    health.py یک عکس لحظه‌ای «سالم/ناسالم» می‌دهد. این ماژول عددها را
    هم می‌دهد: چقدر مصرف می‌شود، چه چیزی مصرف می‌کند، ترافیک در هر
    ثانیه چقدر است، چند نفر وصل‌اند، چه پورت‌هایی باز است.

    و مهم‌تر: هر عدد با «آستانه» و «چرا مهم است» می‌آید. عدد خام بدون
    مرجع بی‌فایده است — کسی که load=3 را می‌بیند نمی‌داند خوب است یا
    بد، مگر اینکه بداند سرور چند هسته دارد.

اصل کار:
    فقط دستورهای خواندنی از یک فهرست ثابت. هیچ ورودی کاربر به شل
    نمی‌رود.

اجرای مستقیم برای دیباگ:
    python3 backend/monitor.py
"""
import json
import os
import re
import shutil
import subprocess
import time

OK, WARN, CRIT = "ok", "warn", "crit"

#: فاصله‌ی دو نمونه برای محاسبه‌ی نرخ (ثانیه). کوتاه، چون کاربر
#: منتظر پاسخ صفحه است.
SAMPLE = 0.6


def _run(cmd, timeout=8):
    """اجرای دستور خواندنی. همیشه فهرست، نه رشته — تا shell دخالت نکند."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode == 0, (p.stdout or "") + (p.stderr or "")
    except Exception:
        return False, ""


def _read(path, default=""):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return default


def _has(binary):
    return shutil.which(binary) is not None


def _level(value, warn, crit):
    """سطح بر اساس دو آستانه. بالاتر یعنی بدتر."""
    if value is None:
        return OK
    if value >= crit:
        return CRIT
    if value >= warn:
        return WARN
    return OK


def _metric(key, title, value, unit="", level=OK, detail="", why="",
            hint="", pct=None, extra=None):
    """
    یک سنجه.

    why: چرا این عدد مهم است و از کجا به بعد خطرناک می‌شود. بدون این،
         ادمین عدد را می‌بیند و نمی‌داند باید نگران باشد یا نه — که
         دقیقاً همان چیزی است که آدم را از مانیتورینگ فراری می‌دهد.
    """
    return {"key": key, "title": title, "value": value, "unit": unit,
            "level": level, "detail": detail, "why": why, "hint": hint,
            "pct": pct, "extra": extra or {}}


_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa(v):
    """فارسی‌کردن ارقام. متن‌های این ماژول را ادمین می‌خواند، نه کپی می‌کند."""
    return str(v).translate(_FA)


def _hb(n):
    """بایت خوانا، با ارقام فارسی."""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    for u in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(n) < 1024 or u == "PB":
            return _fa(f"{n:.1f}") + f" {u}" if u != "B" else _fa(int(n)) + " B"
        n /= 1024
    return _fa(f"{n:.1f}") + " PB"


# ═══════════════════════════════════════════════════════════
#  پردازنده و بار
# ═══════════════════════════════════════════════════════════

def _cpu_times():
    line = _read("/proc/stat").split("\n")[0]
    parts = [float(x) for x in line.split()[1:] if x.replace(".", "").isdigit()]
    if len(parts) < 4:
        return None
    idle = parts[3] + (parts[4] if len(parts) > 4 else 0)
    return sum(parts), idle


def cpu():
    cores = os.cpu_count() or 1

    a = _cpu_times()
    time.sleep(SAMPLE)
    b = _cpu_times()
    usage = None
    if a and b:
        dt, di = b[0] - a[0], b[1] - a[1]
        if dt > 0:
            usage = round(max(0.0, min(100.0, (1 - di / dt) * 100)), 1)

    out = [_metric(
        "cpu", "مصرف پردازنده", usage, "٪",
        _level(usage, 75, 92), f"{_fa(usage)}٪ از {_fa(cores)} هسته" if usage is not None else "—",
        "بالای ۷۵٪ یعنی سرور دارد به سقف می‌رسد و تأخیر کاربران بالا می‌رود. "
        "بالای ۹۲٪ یعنی همین حالا کند شده.",
        "با «سنگین‌ترین پردازه‌ها» پایین ببینید چه چیزی مصرف می‌کند.",
        pct=usage, extra={"cores": cores})]

    try:
        l1, l5, l15 = os.getloadavg()
        per = round(l1 / cores, 2)
        out.append(_metric(
            "load", "بار سیستم", round(l1, 2), "",
            _level(per, 1.0, 2.0),
            _fa(f"{l1:.2f} · {l5:.2f} · {l15:.2f}") + "  (۱ و ۵ و ۱۵ دقیقه)",
            f"این عدد را باید بر تعداد هسته‌ها تقسیم کرد. سرور شما {_fa(cores)} هسته "
            f"دارد، پس بار {_fa(cores)} یعنی دقیقاً پر. الان {_fa(per)} برابر ظرفیت است.",
            "اگر بار بالاست ولی مصرف پردازنده پایین، معمولاً دیسک یا شبکه گلوگاه است.",
            pct=min(100, round(per * 100)), extra={"per_core": per,
                                                   "l5": round(l5, 2),
                                                   "l15": round(l15, 2)}))
    except Exception:
        pass

    return out


def top_processes(n=8):
    """سنگین‌ترین پردازه‌ها بر اساس پردازنده و حافظه."""
    ok, out = _run(["ps", "-eo", "pid,comm,%cpu,%mem,etimes", "--sort=-%cpu"])
    if not ok:
        return []
    rows = []
    for line in out.strip().split("\n")[1:n + 1]:
        p = line.split(None, 4)
        if len(p) < 5:
            continue
        try:
            rows.append({"pid": int(p[0]), "name": p[1],
                         "cpu": float(p[2]), "mem": float(p[3]),
                         "uptime": int(p[4])})
        except ValueError:
            continue
    return rows


# ═══════════════════════════════════════════════════════════
#  حافظه و دیسک
# ═══════════════════════════════════════════════════════════

def memory():
    info = {}
    for line in _read("/proc/meminfo").split("\n"):
        m = re.match(r"(\w+):\s+(\d+)", line)
        if m:
            info[m.group(1)] = int(m.group(2)) * 1024

    total = info.get("MemTotal", 0)
    avail = info.get("MemAvailable", info.get("MemFree", 0))
    used = total - avail
    pct = round(used * 100 / total, 1) if total else None

    out = [_metric(
        "memory", "حافظه", pct, "٪", _level(pct, 85, 95),
        f"{_hb(used)} از {_hb(total)} — {_hb(avail)} آزاد",
        "بالای ۸۵٪ یعنی فضای مانور کم شده. اگر پر شود، هسته پردازه‌ها را "
        "می‌کشد و Xray هم می‌تواند قربانی شود — یعنی قطعی سرویس.",
        "اگر همیشه بالاست، یا مصرف واقعی زیاد است یا نشتی حافظه دارید.",
        pct=pct, extra={"total": total, "used": used, "available": avail})]

    st, sf = info.get("SwapTotal", 0), info.get("SwapFree", 0)
    if st:
        su = st - sf
        spct = round(su * 100 / st, 1)
        out.append(_metric(
            "swap", "حافظه‌ی مجازی", spct, "٪", _level(spct, 40, 75),
            f"{_hb(su)} از {_hb(st)}",
            "استفاده‌ی زیاد از swap یعنی رم واقعی کم آمده. سرور کار می‌کند "
            "ولی کند — و برای VPN، کندی یعنی شکایت کاربر.",
            "اگر مدام بالاست، رم سرور را زیاد کنید."))
    return out


def disks():
    ok, out = _run(["df", "-PB1"])
    if not ok:
        return []
    rows = []
    for line in out.strip().split("\n")[1:]:
        p = line.split()
        if len(p) < 6 or not p[0].startswith("/"):
            continue
        try:
            total, used, avail = int(p[1]), int(p[2]), int(p[3])
        except ValueError:
            continue
        if total < 100 * 1024 ** 2:      # پارتیشن‌های ریز سیستمی
            continue
        pct = round(used * 100 / total, 1) if total else 0
        rows.append(_metric(
            f"disk:{p[5]}", f"دیسک {p[5]}", pct, "٪", _level(pct, 80, 92),
            f"{_hb(used)} از {_hb(total)} — {_hb(avail)} آزاد",
            "دیسک پر یعنی لاگ نوشته نمی‌شود، دیتابیس ربات خطا می‌دهد و "
            "بک‌آپ ساخته نمی‌شود. زیر ۸٪ آزاد وارد منطقه‌ی خطر می‌شوید.",
            "بزرگ‌ترین مصرف‌کننده معمولاً لاگ‌هاست: journalctl --vacuum-size=200M",
            pct=pct, extra={"mount": p[5], "total": total, "used": used}))
    return rows


# ═══════════════════════════════════════════════════════════
#  شبکه — مهم‌ترین بخش برای سرور VPN
# ═══════════════════════════════════════════════════════════

def _net_counters():
    res = {}
    for line in _read("/proc/net/dev").split("\n")[2:]:
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        name = name.strip()
        if name == "lo" or name.startswith(("veth", "docker", "br-")):
            continue
        f = rest.split()
        if len(f) >= 9:
            try:
                res[name] = (int(f[0]), int(f[8]))
            except ValueError:
                pass
    return res


def network():
    a = _net_counters()
    time.sleep(SAMPLE)
    b = _net_counters()

    rx = tx = 0
    per_if = []
    for name, (rx1, tx1) in b.items():
        rx0, tx0 = a.get(name, (rx1, tx1))
        r = max(0, int((rx1 - rx0) / SAMPLE))
        t = max(0, int((tx1 - tx0) / SAMPLE))
        rx += r
        tx += t
        per_if.append({"name": name, "rx": r, "tx": t,
                       "rxTotal": rx1, "txTotal": tx1})
    per_if.sort(key=lambda x: x["rx"] + x["tx"], reverse=True)

    total = rx + tx
    mbps = round(total * 8 / 1_000_000, 1)

    out = [_metric(
        "throughput", "ترافیک لحظه‌ای", mbps, "Mbps",
        _level(mbps, 700, 940),
        f"دریافت {_hb(rx)}/s · ارسال {_hb(tx)}/s",
        "این همان چیزی است که مشتری‌های شما دارند مصرف می‌کنند. اگر به سقف "
        "پورت سرور (معمولاً ۱ گیگابیت) نزدیک شود، سرعت همه افت می‌کند.",
        "اگر مدام نزدیک سقف است، یا کاربر را کم کنید یا پورت بالاتر بگیرید.",
        pct=min(100, round(mbps / 10)), extra={"rx": rx, "tx": tx,
                                               "interfaces": per_if[:5]})]

    # تعداد اتصال‌های برقرار — معیار مستقیم «چند نفر الان وصل‌اند»
    est = None
    if _has("ss"):
        ok, o = _run(["ss", "-tun", "state", "established"])
        if ok:
            est = max(0, len(o.strip().split("\n")) - 1)
    if est is not None:
        out.append(_metric(
            "connections", "اتصال‌های فعال", est, "",
            _level(est, 3000, 9000), f"{_fa(est)} اتصال برقرار",
            "هر کاربر VPN معمولاً چند اتصال هم‌زمان باز می‌کند. عدد خیلی بالا "
            "یا می‌گوید کاربر زیاد دارید، یا کسی دارد سوءاستفاده می‌کند.",
            "برای دیدن پرمصرف‌ترین IPها: ss -tn state established | awk '{print $5}'"))

    # نشست‌های TIME-WAIT — نشانه‌ی فشار یا حمله
    if _has("ss"):
        ok, o = _run(["ss", "-tan"])
        if ok:
            tw = o.count("TIME-WAIT")
            sw = o.count("SYN-RECV")
            if sw > 200:
                out.append(_metric(
                    "synflood", "اتصال‌های نیمه‌باز", sw, "",
                    _level(sw, 200, 800), f"{_fa(sw)} اتصال در حالت SYN-RECV",
                    "تعداد زیاد اتصال نیمه‌باز معمولاً یعنی حمله‌ی SYN flood — "
                    "کسی دارد سرور را با درخواست‌های ناتمام خسته می‌کند.",
                    "فعال‌کردن syncookies: sysctl -w net.ipv4.tcp_syncookies=1"))
            elif tw > 8000:
                out.append(_metric(
                    "timewait", "نشست‌های در حال بسته‌شدن", tw, "",
                    WARN, f"{_fa(tw)} نشست TIME-WAIT",
                    "عدد خیلی بالا یعنی اتصال‌ها سریع باز و بسته می‌شوند و "
                    "ممکن است پورت‌های سرور ته بکشد.",
                    "معمولاً با تنظیم tcp_tw_reuse حل می‌شود."))
    return out


def listening():
    """
    پورت‌های باز رو به اینترنت — سطح حمله‌ی شما.

    هر پورت باز یک در است. ادمینی که نمی‌داند چه درهایی باز است،
    نمی‌تواند بداند از کجا ضربه می‌خورد.
    """
    if not _has("ss"):
        return []
    ok, out = _run(["ss", "-tulpnH"])
    if not ok:
        return []

    #: پورت‌هایی که برای این سرویس طبیعی‌اند
    known = {22: "SSH", 80: "HTTP", 443: "HTTPS", 2053: "پنل/کلادفلر",
             2083: "کلادفلر", 2087: "کلادفلر", 2096: "اشتراک",
             8443: "Xray", 51820: "WireGuard"}

    rows = []
    seen = set()
    for line in out.strip().split("\n"):
        f = line.split()
        if len(f) < 5:
            continue
        proto, local = f[0], f[4]
        m = re.search(r":(\d+)$", local)
        if not m:
            continue
        port = int(m.group(1))
        host = local[:m.start()]
        public = host in ("0.0.0.0", "*", "[::]", "::")
        proc = ""
        pm = re.search(r'users:\(\("([^"]+)"', line)
        if pm:
            proc = pm.group(1)
        key = (port, proto, proc)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"port": port, "proto": proto, "process": proc,
                     "public": public, "known": known.get(port, ""),
                     "risk": "high" if (public and port not in known
                                        and port < 1024) else
                             ("medium" if public and port not in known else "low")})
    rows.sort(key=lambda r: (r["risk"] != "high", r["risk"] != "medium", r["port"]))
    return rows


# ═══════════════════════════════════════════════════════════
#  Xray و سرویس‌ها
# ═══════════════════════════════════════════════════════════

def _svc_state(name):
    ok, out = _run(["systemctl", "is-active", name])
    return out.strip() or ("active" if ok else "unknown")


def services(names=None):
    names = names or ["xray", "x-ui", "nginx", "nexora-bot", "nexora-api",
                      "fail2ban", "ssh", "sshd"]
    rows = []
    for n in names:
        ok, out = _run(["systemctl", "show", n,
                        "--property=LoadState,ActiveState,SubState,"
                        "MainPID,MemoryCurrent,NRestarts"])
        if not ok or "LoadState=not-found" in out:
            continue
        d = dict(x.split("=", 1) for x in out.strip().split("\n") if "=" in x)
        active = d.get("ActiveState", "")
        restarts = int(d.get("NRestarts", "0") or 0)
        mem = d.get("MemoryCurrent", "")
        mem = int(mem) if mem.isdigit() else None
        rows.append({
            "name": n,
            "active": active,
            "sub": d.get("SubState", ""),
            "pid": d.get("MainPID", ""),
            "memory": mem,
            "restarts": restarts,
            "level": OK if active == "active" else CRIT,
            # ری‌استارت مکرر یعنی سرویس بالا می‌آید و می‌افتد — از
            # «خاموش» بدتر است چون در نگاه اول سالم به نظر می‌رسد
            "flapping": restarts > 3,
        })
    return rows


def xray():
    """وضعیت اختصاصی Xray — قلب سرویس."""
    out = []
    state = _svc_state("xray")
    running = state == "active"
    out.append(_metric(
        "xray", "سرویس Xray", "روشن" if running else "خاموش", "",
        OK if running else CRIT,
        f"وضعیت systemd: {state}",
        "اگر Xray خاموش باشد هیچ کاربری وصل نمی‌شود، حتی اگر پنل و ربات "
        "سالم کار کنند.",
        "" if running else "systemctl restart xray"))

    # خطاهای اخیر — زودتر از شکایت مشتری خبر می‌دهد
    ok, log = _run(["journalctl", "-u", "xray", "--since", "-30min",
                    "-p", "warning", "--no-pager", "-n", "40"])
    if ok:
        lines = [x for x in log.strip().split("\n")
                 if x and "-- No entries" not in x]
        n = len(lines)
        out.append(_metric(
            "xray_errors", "خطاهای Xray (۳۰ دقیقه اخیر)", n, "",
            _level(n, 5, 30), f"{_fa(n)} خط هشدار یا خطا",
            "چند خطای پراکنده طبیعی است. انبوه خطا یعنی یا کانفیگ مشکل دارد "
            "یا سرور خارج در دسترس نیست.",
            "برای دیدن: journalctl -u xray -p warning --since -30min",
            extra={"lines": lines[-8:]}))
    return out


# ═══════════════════════════════════════════════════════════
#  بسته‌ها و امنیت
# ═══════════════════════════════════════════════════════════

def packages():
    """به‌روزرسانی‌های در انتظار — مخصوصاً امنیتی."""
    if not _has("apt-get"):
        return []
    ok, out = _run(["apt-get", "-s", "upgrade"], timeout=25)
    if not ok:
        return []
    lines = [x for x in out.split("\n") if x.startswith("Inst ")]
    total = len(lines)
    sec = len([x for x in lines if "security" in x.lower()])
    return [_metric(
        "updates", "به‌روزرسانی در انتظار", total, "بسته",
        CRIT if sec else _level(total, 25, 80),
        f"{_fa(total)} بسته — {_fa(sec)} مورد امنیتی",
        "به‌روزرسانی امنیتی یعنی حفره‌ای عمومی شده که کد سوءاستفاده‌اش هم "
        "معمولاً منتشر است. روی سروری که پورت باز به اینترنت دارد، این "
        "فوری‌ترین ریسک است.",
        "apt update && apt upgrade" if total else "",
        extra={"security": sec,
               "sample": [x.split()[1] for x in lines[:10] if len(x.split()) > 1]})]


def _re_status(text):
    """آیا خروجی ufw وضعیت active را گزارش می‌کند؟ (نه inactive)"""
    return re.search(r"^\s*status:\s*active\s*$", text or "",
                     re.IGNORECASE | re.MULTILINE)


def security():
    out = []

    # تلاش‌های ناموفق ورود SSH — نشانه‌ی حمله‌ی brute force
    ok, log = _run(["journalctl", "-u", "ssh", "-u", "sshd", "--since", "-24h",
                    "--no-pager", "-g", "Failed password"], timeout=15)
    if ok:
        n = len([x for x in log.split("\n") if "Failed password" in x])
        ips = re.findall(r"from ([\d.]+)", log)
        top = {}
        for ip in ips:
            top[ip] = top.get(ip, 0) + 1
        worst = sorted(top.items(), key=lambda kv: -kv[1])[:5]
        out.append(_metric(
            "ssh_failed", "ورود ناموفق SSH (۲۴ ساعت)", n, "",
            _level(n, 100, 1000), f"{_fa(n)} تلاش ناموفق از {_fa(len(top))} آدرس",
            "روی هر سرور عمومی چند صد تلاش خودکار در روز عادی است. عدد خیلی "
            "بالا از یک IP یعنی هدف‌گیری مشخص.",
            "ورود با رمز را ببندید و فقط کلید بگذارید؛ یا fail2ban نصب کنید.",
            extra={"topIps": [{"ip": i, "n": c} for i, c in worst]}))

    # fail2ban
    if _has("fail2ban-client"):
        ok, o = _run(["fail2ban-client", "status"])
        if ok:
            jails = re.search(r"Jail list:\s*(.*)", o)
            out.append(_metric(
                "fail2ban", "fail2ban", "فعال", "", OK,
                f"جیل‌ها: {jails.group(1).strip() if jails else '—'}",
                "fail2ban آدرس‌هایی را که مکرر شکست می‌خورند خودکار می‌بندد."))
    else:
        out.append(_metric(
            "fail2ban", "fail2ban", "نصب نیست", "", WARN,
            "روی این سرور پیدا نشد",
            "بدون آن، تلاش‌های brute force بی‌وقفه ادامه پیدا می‌کنند.",
            "apt install fail2ban"))

    # فایروال
    if _has("ufw"):
        ok, o = _run(["ufw", "status"])
        # دقت کنید: «inactive» خودش شامل «active» است. جست‌وجوی ساده‌ی
        # زیررشته، فایروالِ خاموش را روشن گزارش می‌کرد — یعنی دقیقاً
        # در لحظه‌ای که باید هشدار می‌داد، ساکت می‌ماند.
        act = bool(_re_status(o))
        out.append(_metric(
            "firewall", "فایروال", "روشن" if act else "خاموش", "",
            OK if act else WARN,
            o.strip().split("\n")[0] if o else "—",
            "فایروال خاموش یعنی هر پورتی که سهواً باز شود، مستقیم از اینترنت "
            "در دسترس است."))
    return out


# ═══════════════════════════════════════════════════════════
#  جمع‌بندی
# ═══════════════════════════════════════════════════════════

def _uptime():
    try:
        return int(float(_read("/proc/uptime", "0").split()[0]))
    except Exception:
        return 0


def snapshot(include=None):
    """
    یک عکس کامل.

    include: زیرمجموعه‌ی بخش‌ها، برای وقتی صفحه فقط بخشی را می‌خواهد.
    """
    want = set(include or ["cpu", "memory", "disk", "network", "xray",
                           "services", "ports", "packages", "security",
                           "processes"])
    metrics, sections = [], {}

    def add(name, fn, into_metrics=True):
        if name not in want:
            return
        try:
            r = fn()
            sections[name] = r
            if into_metrics and isinstance(r, list) and r and isinstance(r[0], dict) \
                    and "level" in r[0] and "key" in r[0]:
                metrics.extend(r)
        except Exception as e:
            sections[name] = []
            metrics.append(_metric(name, name, None, "", WARN,
                                   f"خواندن ناموفق: {type(e).__name__}"))

    add("cpu", cpu)
    add("memory", memory)
    add("disk", disks)
    add("network", network)
    add("xray", xray)
    add("packages", packages)
    add("security", security)
    add("services", services, into_metrics=False)
    add("ports", listening, into_metrics=False)
    add("processes", top_processes, into_metrics=False)

    for s in sections.get("services", []):
        if s["level"] == CRIT:
            metrics.append(_metric(
                f"svc:{s['name']}", f"سرویس {s['name']}", "خاموش", "", CRIT,
                f"وضعیت: {s['active']}",
                "این سرویس باید روشن باشد.",
                f"systemctl restart {s['name']}"))
        elif s.get("flapping"):
            metrics.append(_metric(
                f"svc:{s['name']}", f"سرویس {s['name']}", "ناپایدار", "", WARN,
                f"{_fa(s['restarts'])} بار ری‌استارت شده",
                "سرویسی که مدام بالا و پایین می‌شود از خاموش بدتر است، چون "
                "در نگاه اول سالم به نظر می‌رسد.",
                f"journalctl -u {s['name']} -n 50"))

    crit = [m for m in metrics if m["level"] == CRIT]
    warn = [m for m in metrics if m["level"] == WARN]
    level = CRIT if crit else (WARN if warn else OK)

    if crit:
        headline = crit[0]["title"]
        summary = f"{_fa(len(crit))} مشکل جدی" + (f" و {_fa(len(warn))} هشدار" if warn else "")
    elif warn:
        headline = warn[0]["title"]
        summary = f"{_fa(len(warn))} هشدار"
    else:
        headline = ""
        summary = "سرور سالم است"

    return {
        "level": level,
        "summary": summary,
        "headline": headline,
        "metrics": metrics,
        "sections": sections,
        "counts": {"ok": len(metrics) - len(crit) - len(warn),
                   "warn": len(warn), "crit": len(crit)},
        "host": {
            "uptime": _uptime(),
            "cores": os.cpu_count() or 1,
            "kernel": _read("/proc/sys/kernel/osrelease", "").strip(),
            "hostname": _read("/proc/sys/kernel/hostname", "").strip(),
        },
        "at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "took": None,
    }


if __name__ == "__main__":
    t0 = time.time()
    snap = snapshot()
    snap["took"] = round(time.time() - t0, 2)
    print(json.dumps(snap, ensure_ascii=False, indent=2))
