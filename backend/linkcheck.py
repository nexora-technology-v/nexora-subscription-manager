"""
عیب‌یابیِ ارتباطِ ایران↔خارج — و شمارنده‌های ترافیک.

برگه: docs/specs/2026-09-26-link-diagnosis-and-traffic.md

این فایل دو جا اجرا می‌شود: خودِ پنل (سمتِ خارج) و ایجنتِ سرورِ ایران،
که آن را از `/api/agent/linkcheck.py` می‌گیرد — همان مسیرِ monitor و
health. نسخه‌ی دومی نوشته نشد: دو پیاده‌سازی یعنی دو جور عدد، و مدیری
که نمی‌فهمد چرا دو سمت با هم نمی‌خوانند.

فقط stdlib؛ ایجنت روی سرورهایی اجرا می‌شود که کسی قرار نیست رویشان
چیزی نصب کند.

چرا این همه مسیر: یک عدد نمی‌گوید اختلال کجاست. «تانل کند است» پنج
علتِ متفاوت دارد و هر کدام کارِ متفاوتی می‌خواهد — تنها با کنارِ هم
گذاشتنِ مسیرها معلوم می‌شود کدام است (جدولِ `diagnose`).
"""
import os
import re
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

#: مرجع‌های داخلی — اگر این‌ها هم از سرورِ ایران در دسترس نباشند، مشکل
#: از خودِ سرور یا دیتاسنترش است، نه از مرز
DOMESTIC = (("www.aparat.com", 443), ("www.digikala.com", 443), ("divar.ir", 443))

#: مرجع‌های بین‌المللی — سه شبکه‌ی جدا، تا خرابیِ یکی حکم را عوض نکند
INTL = (("1.1.1.1", 443), ("8.8.8.8", 443), ("9.9.9.9", 443))

#: پورت‌هایی که روی سرورِ خارج برای سنجشِ TCP امتحان می‌شوند
FOREIGN_PORTS = (443, 22)

#: مرزهای «کند» برای هر مسیر (میلی‌ثانیه). داخلی باید نزدیک باشد؛ مسیرِ
#: بین‌المللی از ایران به‌طورِ عادی چند صد میلی‌ثانیه است.
SLOW_MS = {"domestic": 150, "intl": 400, "between": 350}

#: از این پرت به بالا «قطع»، و از `LOSSY` به بالا «ناپایدار»
DOWN = 80
LOSSY = 10


# ═══════════════════════════════════════════════════════════
#  سنجش
# ═══════════════════════════════════════════════════════════

def tcp_probe(host, port, tries=4, timeout=3.0):
    """برقراریِ اتصالِ TCP — همان کاری که ترافیکِ واقعی می‌کند."""
    samples, fails = [], 0
    for _ in range(tries):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        t0 = time.perf_counter()
        try:
            s.connect((host, int(port)))
            samples.append((time.perf_counter() - t0) * 1000)
        except (OSError, ValueError):
            fails += 1
        finally:
            try:
                s.close()
            except OSError:
                pass
        time.sleep(0.1)
    out = {"loss": round(fails * 100 / tries), "tries": tries}
    if samples:
        out["avg"] = round(sum(samples) / len(samples), 1)
    return out


def icmp_probe(host, count=4):
    """ping — برای مقایسه با TCP. نبودنِ ping یعنی None، نه «قطع»."""
    if not re.match(r"^[A-Za-z0-9.\-:]{1,120}$", str(host)):
        return None
    try:
        p = subprocess.run(["ping", "-c", str(count), "-W", "2", str(host)],
                           capture_output=True, text=True, timeout=count * 3 + 4)
    except (OSError, subprocess.SubprocessError):
        return None
    out = p.stdout or ""
    m = re.search(r"(\d+(?:\.\d+)?)% packet loss", out)
    if not m:
        return None
    res = {"loss": round(float(m.group(1)))}
    m = re.search(r"=\s*[\d.]+/([\d.]+)/", out)
    if m:
        res["avg"] = round(float(m.group(1)), 1)
    return res


def _probe_target(t):
    host, port = t["host"], t.get("port")
    r = {"host": host, "port": port}
    if port:
        r["tcp"] = tcp_probe(host, port)
    if t.get("icmp", True):
        r["icmp"] = icmp_probe(host)
    return r


def probe_all(targets):
    """همه هم‌زمان: سرورِ قطع نباید ایجنت را چند دقیقه معطل کند."""
    if not targets:
        return []
    with ThreadPoolExecutor(max_workers=min(12, len(targets))) as ex:
        return list(ex.map(_probe_target, targets))


def _metric(r):
    """TCP اگر هست (همان که ترافیک استفاده می‌کند)، وگرنه ICMP."""
    return r.get("tcp") or r.get("icmp")


def summarize(results):
    """
    خلاصه‌ی یک مسیر از چند مقصد.

    برمی‌گرداند {"loss", "avg", "up", "targets"} یا None اگر هیچ عددی نیست.
    پرت میانگینِ همه‌ی مقصدهاست (مقصدِ مرده ۱۰۰)، تاخیر میانه‌ی آن‌هایی
    که جواب داده‌اند — همان منطقِ `_tcp_summary` تانل.
    """
    ms = [m for m in (_metric(r) for r in results or []) if m]
    if not ms:
        return None
    avgs = sorted(m["avg"] for m in ms if isinstance(m.get("avg"), (int, float)))
    return {
        "loss": round(sum(m["loss"] for m in ms) / len(ms)),
        "avg": avgs[len(avgs) // 2] if avgs else None,
        "up": sum(1 for m in ms if m["loss"] < DOWN),
        "targets": len(ms),
    }


def state(summary, kind):
    """ok | slow | lossy | down | unknown — برای یک مسیر."""
    if not summary:
        return "unknown"
    # بیش از نیمی از مقصدها قطع → مسیر قطع است، نه «میانگینِ ۵۰٪ پرت»
    if summary["up"] * 2 < summary["targets"] or summary["loss"] >= DOWN:
        return "down"
    if summary["loss"] >= LOSSY:
        return "lossy"
    if summary["avg"] is not None and summary["avg"] > SLOW_MS[kind]:
        return "slow"
    return "ok"


# ═══════════════════════════════════════════════════════════
#  شمارنده‌های ترافیک
# ═══════════════════════════════════════════════════════════

def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def net_counters(text=None):
    """
    جمعِ بایت‌های دریافت و ارسالِ کارت‌های واقعی از `/proc/net/dev`.

    همان فیلترِ `monitor._net_counters` (بی lo، veth، docker، br-) —
    test-linkcheck برابری‌شان را می‌سنجد. اگر یکی کارتی را بشمارد و
    دیگری نه، «ترافیکِ لحظه‌ای» و «حجمِ امروز» با هم نمی‌خوانند.
    """
    text = _read("/proc/net/dev") if text is None else text
    rx = tx = 0
    found = False
    for line in text.split("\n")[2:]:
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        name = name.strip()
        if name == "lo" or name.startswith(("veth", "docker", "br-")):
            continue
        f = rest.split()
        if len(f) >= 9:
            try:
                rx += int(f[0])
                tx += int(f[8])
                found = True
            except ValueError:
                continue
    return {"rx": rx, "tx": tx} if found else None


# ═══════════════════════════════════════════════════════════
#  آی‌پیِ طرفِ مقابلِ تانل
# ═══════════════════════════════════════════════════════════

def peer_ips(ports):
    """
    آی‌پی‌هایی که الان به پورتِ تانلِ این سرور وصل‌اند — یعنی سرورِ خارج.

    پنل آی‌پیِ سرورِ خارج را جایی ذخیره نمی‌کند (`remote_host` آدرسِ
    ایران است: همه‌ی موتورها از خارج به ایران زنگ می‌زنند). اتصالِ
    برقرار خودش می‌گوید طرفِ مقابل کیست.
    """
    want = {str(int(p)) for p in ports or [] if str(p).isdigit()}
    if not want:
        return []
    try:
        p = subprocess.run(["ss", "-Htn", "state", "established"],
                           capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.SubprocessError):
        return []
    seen = []
    for line in (p.stdout or "").splitlines():
        f = line.split()
        if len(f) < 4:
            continue
        local, peer = f[-2], f[-1]
        lp = local.rsplit(":", 1)[-1]
        ip = peer.rsplit(":", 1)[0].strip("[]")
        if lp in want and not ip.startswith(("127.", "::1")) and ip not in seen:
            seen.append(ip)
    return seen[:3]


# ═══════════════════════════════════════════════════════════
#  یک دورِ کامل — همان تابعی که ایجنت و پنل صدا می‌زنند
# ═══════════════════════════════════════════════════════════

def run(side="iran", bridge_ports=None, iran_hosts=None, **_):
    """
    side="iran":    از سرورِ ایران — داخل، بین‌الملل، و سرورِ خارج
    side="foreign": از سرورِ خارج — ایران (پورتِ تانل)، و بین‌الملل

    `**_` تا ایجنت هر پارامترِ اضافه‌ای (panelVersion، …) را بی‌خطا رد کند.
    """
    t0 = time.time()
    out = {"side": side, "at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "counters": net_counters()}

    if side == "iran":
        peers = peer_ips(bridge_ports)
        groups = {
            "domestic": [{"host": h, "port": p} for h, p in DOMESTIC],
            "intl": [{"host": h, "port": p} for h, p in INTL],
            "foreign": [{"host": ip, "port": port, "icmp": port == FOREIGN_PORTS[0]}
                        for ip in peers for port in FOREIGN_PORTS],
        }
        out["peers"] = peers
    else:
        hosts = [h for h in iran_hosts or [] if h.get("host") and h.get("port")][:6]
        groups = {
            "iran": [{"host": h["host"], "port": int(h["port"])} for h in hosts],
            "intl": [{"host": h, "port": p} for h, p in INTL],
        }

    flat = [(g, t) for g, ts in groups.items() for t in ts]
    results = probe_all([t for _g, t in flat])
    paths = {g: [] for g in groups}
    for (g, _t), r in zip(flat, results):
        paths[g].append(r)

    if side == "iran" and paths.get("foreign"):
        # برای هر آی‌پی بهترین پورت: سرورِ خارج لازم نیست ۲۲ و ۴۴۳ را
        # هر دو باز داشته باشد، و پورتِ بسته «قطع» نیست
        best = {}
        for r in paths["foreign"]:
            m = _metric(r)
            cur = best.get(r["host"])
            if cur is None or (m and m["loss"] < (_metric(cur) or {"loss": 101})["loss"]):
                best[r["host"]] = r
        paths["foreign"] = list(best.values())

    out["paths"] = paths
    out["took"] = round(time.time() - t0, 1)
    return out


# ═══════════════════════════════════════════════════════════
#  حکم
# ═══════════════════════════════════════════════════════════

_BAD = ("down",)
_WARN = ("lossy", "slow")

_PATH_FA = {"iran_domestic": "ایران ← داخل", "iran_intl": "ایران ← بین‌الملل",
            "iran_foreign": "ایران ← خارج", "foreign_iran": "خارج ← ایران",
            "foreign_intl": "خارج ← بین‌الملل"}

_STATE_FA = {"ok": "سالم", "slow": "کند", "lossy": "ناپایدار", "down": "قطع",
             "unknown": "بی‌داده"}


def path_states(iran, foreign):
    """وضعیتِ هر پنج مسیر از روی آخرین سنجشِ دو سمت."""
    ip = (iran or {}).get("paths") or {}
    fp = (foreign or {}).get("paths") or {}
    return {
        "iran_domestic": state(summarize(ip.get("domestic")), "domestic"),
        "iran_intl": state(summarize(ip.get("intl")), "intl"),
        "iran_foreign": state(summarize(ip.get("foreign")), "between"),
        "foreign_iran": state(summarize(fp.get("iran")), "between"),
        "foreign_intl": state(summarize(fp.get("intl")), "intl"),
    }


def _worst(*xs):
    order = ["down", "lossy", "slow", "ok", "unknown"]
    known = [x for x in xs if x != "unknown"]
    return min(known, key=order.index) if known else "unknown"


def diagnose(iran, foreign):
    """
    یک حکم به زبانِ ساده: اختلال از کدام سمت است و چه باید کرد.

    ترتیبِ بررسی مهم است: اگر خودِ سرورِ ایران به داخل هم نمی‌رسد، بقیه‌ی
    مسیرها طبیعتاً بدند و گفتنِ «آی‌پیِ خارج محدود شده» گمراه‌کننده است.
    """
    s = path_states(iran, foreign)
    between = _worst(s["iran_foreign"], s["foreign_iran"])

    def verdict(side, st, title, detail, fix):
        return {"side": side, "level": "bad" if st in _BAD else "warn",
                "title": title, "reason": detail, "fix": fix, "paths": s}

    if s["iran_domestic"] in _BAD + _WARN:
        return verdict(
            "iran", s["iran_domestic"],
            "مشکل از خودِ سرورِ ایران یا دیتاسنترش است",
            f"سرورِ ایران حتی به سایت‌های داخلی هم {_STATE_FA[s['iran_domestic']]} وصل می‌شود.",
            "با پشتیبانیِ دیتاسنترِ ایران تماس بگیرید؛ مصرفِ CPU و پهنای باندِ همان سرور را هم ببینید.")
    if s["iran_intl"] in _BAD + _WARN:
        return verdict(
            "iran-intl", s["iran_intl"],
            "اختلالِ خروجیِ بین‌المللِ ایران",
            "سرورِ ایران به داخل سالم وصل است ولی به اینترنتِ بین‌المللی "
            f"{_STATE_FA[s['iran_intl']]}. این معمولاً سراسری است و از دستِ ما خارج.",
            "صبر، یا امتحانِ ترنسپورتِ دیگر برای تانل. عوض‌کردنِ سرورِ خارج کمکی نمی‌کند.")
    if s["foreign_intl"] in _BAD + _WARN:
        return verdict(
            "foreign", s["foreign_intl"],
            "مشکل از سرورِ خارج است",
            f"سرورِ خارج به اینترنتِ بین‌المللی {_STATE_FA[s['foreign_intl']]} وصل می‌شود.",
            "وضعیتِ دیتاسنترِ خارج و مصرفِ همان سرور را ببینید.")
    if between in _BAD + _WARN:
        return verdict(
            "between", between,
            "مسیرِ بینِ این دو سرور مشکل دارد",
            "هر دو سرور به اینترنت سالم وصل‌اند، ولی بینِ خودشان "
            f"{_STATE_FA[between]}. معمولاً یعنی آی‌پیِ یکی از دو سرور محدود شده.",
            "آی‌پیِ سرورِ خارج (یا ایران) را عوض کنید، یا دیتاسنترِ دیگری امتحان کنید.")
    if "unknown" in s.values():
        missing = [k for k, v in s.items() if v == "unknown"]
        return {"side": "unknown", "level": "unknown", "paths": s,
                "title": "هنوز برای همه‌ی مسیرها داده نیست",
                "reason": "مسیرهای بی‌داده: " + "، ".join(_PATH_FA[k] for k in missing),
                "fix": "اگر ایجنت قدیمی است به‌روزش کنید؛ وگرنه چند دقیقه صبر کنید."}
    return {"side": "none", "level": "ok", "paths": s,
            "title": "همه‌ی مسیرها سالم‌اند",
            "reason": "اگر مشتری‌ها هنوز کندی دارند، مشکل از خودِ تانل یا موتور است، نه شبکه.",
            "fix": "لاگِ تانل را ببینید، یا ترنسپورتِ دیگری امتحان کنید."}
