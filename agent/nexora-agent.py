#!/usr/bin/env python3
"""
Nexora Agent — روی سرور ایران نصب می‌شود.

این برنامه به پنل وصل می‌شود، نه برعکس. یعنی سرور ایران هیچ
پورتی باز نمی‌کند و رمزی جایی ذخیره نمی‌شود؛ فقط یک توکن دارد
که اگر لو رفت، از پنل باطل می‌شود.

Agent فقط دستورهای مشخصی را می‌شناسد. هر چیز دیگری رد می‌شود،
پس حتی اگر پنل نفوذ شود، نمی‌توان کد دلخواه اینجا اجرا کرد.

تنها وابستگی: کتابخانه‌ی استاندارد پایتون. هیچ pip install لازم
نیست — چون روی سرور کسی نصب می‌شود که ممکن است اینترنت محدود
داشته باشد.
"""

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

#: نسخه‌ی ایجنت. پنل از روی همین می‌فهمد که آیا این ایجنت دستورهای
#: تازه را می‌شناسد یا نه — پس با هر قابلیت جدید باید بالا برود،
#: وگرنه پنل فکر می‌کند ایجنت قدیمی است و بی‌دلیل به‌روزرسانی می‌خواهد.
VERSION = "1.6.0"

PANEL_URL = os.getenv("NEXORA_PANEL", "").rstrip("/")
TOKEN = os.getenv("NEXORA_TOKEN", "")
INTERVAL = int(os.getenv("NEXORA_INTERVAL", "30"))

BASE = Path("/opt/nexora-agent")
BIN = BASE / "bin"
CFG = BASE / "configs"

ENGINE_BINARIES = {
    "backhaul": "backhaul",
    "rathole": "rathole",
    "gost": "gost",
    "frp_server": "frps",
    "frp_client": "frpc",
}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run(cmd, timeout=90):
    """
    اجرای دستور.

    دستورها همیشه به‌صورت فهرست پاس می‌شوند نه رشته، تا هیچ‌جا
    shell دخالت نکند و تزریق دستور ممکن نباشد.
    """
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode == 0, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return False, "زمان اجرا تمام شد"
    except FileNotFoundError:
        return False, f"دستور پیدا نشد: {cmd[0]}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# ═══════════════════════════════════════════════════════════
#  ارتباط با پنل
# ═══════════════════════════════════════════════════════════

def sign(body: bytes, ts: str) -> str:
    """
    امضای HMAC-SHA256 روی بدنه‌ی درخواست و زمان آن.

    توکن به‌تنهایی کافی است تا پنل ما را بشناسد، ولی اگر یک بار لو
    برود — از لاگ، از پشتیبان، از هرجا — هر کسی می‌تواند خودش را
    جای این سرور جا بزند و تا وقتی باطل نشده کار کند.

    با امضا، توکن دیگر مستقیم روی سیم نمی‌رود: چیزی که فرستاده
    می‌شود امضای همان درخواست است، و چون زمان داخل امضاست، ضبط و
    بازپخشِ بعدی هم بی‌فایده است.

    توکن هنوز فرستاده می‌شود تا ایجنت‌های قدیمی از کار نیفتند؛ پنل
    هر دو را می‌پذیرد و امضا را وقتی هست بررسی می‌کند.
    """
    import hashlib
    import hmac
    msg = ts.encode() + b"." + (body or b"")
    return hmac.new(TOKEN.encode(), msg, hashlib.sha256).hexdigest()


def api(path, data=None, timeout=25):
    url = f"{PANEL_URL}/api/agent/{path}"
    body = json.dumps(data or {}).encode() if data is not None else None
    ts = str(int(time.time()))
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json",
                 "X-Agent-Token": TOKEN,
                 "X-Agent-Time": ts,
                 "X-Agent-Sign": sign(body or b"", ts),
                 "User-Agent": f"nexora-agent/{VERSION}"},
        method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode()).get("detail", "")
        except Exception:
            pass
        return {"error": f"HTTP {e.code} {detail}"[:200]}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:150]}"}


# ═══════════════════════════════════════════════════════════
#  وضعیت سرور
# ═══════════════════════════════════════════════════════════

def metrics():
    m = {"version": VERSION}

    try:
        m["os"] = f"{platform.system()} {platform.release()}"
        rel = Path("/etc/os-release")
        if rel.exists():
            for line in rel.read_text().splitlines():
                if line.startswith("PRETTY_NAME="):
                    m["os"] = line.split("=", 1)[1].strip().strip('"')
                    break
    except Exception:
        pass

    # بار پردازنده از loadavg — بدون نیاز به psutil
    try:
        load = os.getloadavg()[0]
        cores = os.cpu_count() or 1
        m["cpu"] = round(min(100.0, load / cores * 100), 1)
    except Exception:
        pass

    try:
        info = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, _, v = line.partition(":")
            info[k] = int(v.strip().split()[0])
        total = info.get("MemTotal", 0)
        avail = info.get("MemAvailable", 0)
        if total:
            m["mem"] = round((total - avail) * 100.0 / total, 1)
    except Exception:
        pass

    try:
        st = os.statvfs("/")
        used = (st.f_blocks - st.f_bfree) * 100.0 / st.f_blocks
        m["disk"] = round(used, 1)
    except Exception:
        pass

    try:
        m["uptime"] = int(float(Path("/proc/uptime").read_text().split()[0]))
    except Exception:
        pass

    return m


# ═══════════════════════════════════════════════════════════
#  نصب موتورها
# ═══════════════════════════════════════════════════════════

def arch_tag():
    """نام معماری همان‌طور که در فایل‌های انتشار گیت‌هاب می‌آید."""
    m = platform.machine().lower()
    if m in ("x86_64", "amd64"):
        return "amd64"
    if m in ("aarch64", "arm64"):
        return "arm64"
    if m.startswith("armv7"):
        return "armv7"
    return "amd64"


def download(url, dest):
    """
    دانلود اتمی: اول به فایل موقت، بعد جابه‌جایی.

    قبلاً مستقیم روی مقصد نوشته می‌شد، پس قطع‌شدن اتصال وسط کپی یک
    فایل *ناقص* جا می‌گذاشت. برای ماژول‌های پنل این یعنی پایتونِ
    نصفه که تا نسخه‌ی بعدیِ پنل همان‌جا می‌ماند.
    """
    dest = Path(dest)
    tmp = dest.with_name(dest.name + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "nexora-agent"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        os.replace(tmp, dest)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def latest_release(repo):
    """آخرین نسخه‌ی منتشرشده و فایل‌هایش."""
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/releases/latest",
        headers={"User-Agent": "nexora-agent",
                 "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode())


def wanted_first(engine):
    """نام باینری اصلی هر موتور — برای وقتی آرشیو ساختار ندارد."""
    return {"backhaul": "backhaul", "rathole": "rathole", "gost": "gost",
            "frp": "frps", "chisel": "chisel"}.get(engine, engine)


def install_engine(engine):
    """
    نصب باینری یک موتور از انتشار رسمی گیت‌هاب.

    فایل انتخابی باید هم نام سیستم‌عامل و هم معماری را داشته
    باشد؛ وگرنه ممکن است باینری اشتباه دانلود شود و خطایش گیج‌کننده
    باشد.
    """
    repos = {
        "backhaul": "Musixal/Backhaul",
        "rathole": "rapiz1/rathole",
        "gost": "go-gost/gost",
        "frp": "fatedier/frp",
        "chisel": "jpillora/chisel",
    }
    repo = repos.get(engine)
    if not repo:
        return False, f"موتور ناشناخته: {engine}"

    BIN.mkdir(parents=True, exist_ok=True)
    arch = arch_tag()

    try:
        rel = latest_release(repo)
    except Exception as e:
        return False, f"خواندن نسخه‌ها ناموفق: {str(e)[:120]}"

    assets = rel.get("assets") or []
    pick = None
    for a in assets:
        n = a["name"].lower()
        if "linux" not in n:
            continue
        if arch not in n and not (arch == "amd64" and "x86_64" in n):
            continue
        # بعضی پروژه‌ها آرشیو می‌دهند و بعضی باینری فشرده‌ی تکی (مثل chisel)
        if n.endswith((".tar.gz", ".zip", ".tgz", ".gz")):
            pick = a
            break

    if not pick:
        names = ", ".join(a["name"] for a in assets[:5])
        return False, f"فایل مناسب linux/{arch} پیدا نشد. موجود: {names}"

    tmp = Path(tempfile.mkdtemp())
    try:
        archive = tmp / pick["name"]
        download(pick["browser_download_url"], archive)

        out = tmp / "x"
        out.mkdir()
        name_low = archive.name.lower()

        if name_low.endswith(".zip"):
            with zipfile.ZipFile(archive) as z:
                z.extractall(out)
        elif name_low.endswith((".tar.gz", ".tgz")):
            with tarfile.open(archive) as t:
                t.extractall(out)
        else:
            # باینری تکی فشرده‌شده با gzip — بدون ساختار آرشیو
            import gzip
            target = out / wanted_first(engine)
            with gzip.open(archive, "rb") as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            os.chmod(target, 0o755)

        wanted = {"backhaul": ["backhaul"], "rathole": ["rathole"],
                  "gost": ["gost"], "frp": ["frps", "frpc"],
                  "chisel": ["chisel"]}[engine]

        found = 0
        for name in wanted:
            for p in out.rglob(name):
                if p.is_file():
                    target = BIN / name
                    shutil.copy2(p, target)
                    os.chmod(target, 0o755)
                    found += 1
                    break

        if not found:
            return False, f"باینری در بسته پیدا نشد: {wanted}"

        return True, f"{engine} {rel.get('tag_name', '')} نصب شد ({found} فایل)"
    except Exception as e:
        return False, f"نصب ناموفق: {type(e).__name__}: {str(e)[:120]}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ═══════════════════════════════════════════════════════════
#  سرویس‌ها
# ═══════════════════════════════════════════════════════════

SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]{1,50}$")


def service_name(tunnel_id):
    return f"nexora-tunnel-{int(tunnel_id)}"


def write_service(tunnel_id, engine, config_text, side):
    """
    نوشتن کانفیگ و ساخت سرویس systemd.

    نام فایل‌ها فقط از شناسه‌ی عددی ساخته می‌شود، نه از ورودی
    کاربر — تا هیچ‌جا مسیر دستکاری نشود.
    """
    tid = int(tunnel_id)
    CFG.mkdir(parents=True, exist_ok=True)

    # Chisel فایل پیکربندی ندارد — آرگومان می‌گیرد
    if engine == "chisel":
        binary = BIN / "chisel"
        if not binary.exists():
            return False, "باینری chisel نصب نیست"
        # آرگومان‌ها را هم ذخیره می‌کنیم تا بعداً قابل بازبینی باشند
        cfg_path = CFG / f"tunnel-{tid}.args"
        cfg_path.write_text(config_text, encoding="utf-8")
        os.chmod(cfg_path, 0o600)
        return _make_unit(tid, engine, f"{binary} {config_text}", cfg_path)

    ext = {"backhaul": "toml", "rathole": "toml",
           "gost": "yaml", "frp": "toml"}.get(engine, "conf")
    cfg_path = CFG / f"tunnel-{tid}.{ext}"
    cfg_path.write_text(config_text, encoding="utf-8")
    os.chmod(cfg_path, 0o600)      # توکن داخلش هست

    if engine == "frp":
        binary = BIN / ("frps" if side == "iran" else "frpc")
        args = f"-c {cfg_path}"
    elif engine == "gost":
        binary = BIN / "gost"
        args = f"-C {cfg_path}"
    elif engine == "rathole":
        binary = BIN / "rathole"
        args = f"{'--server' if side == 'iran' else '--client'} {cfg_path}"
    else:
        binary = BIN / "backhaul"
        args = f"-c {cfg_path}"

    if not binary.exists():
        return False, f"باینری {binary.name} نصب نیست"

    return _make_unit(tid, engine, f"{binary} {args}", cfg_path)


def _make_unit(tid, engine, exec_line, cfg_path):
    """ساخت سرویس systemd و راه‌اندازی آن."""
    unit = f"""[Unit]
Description=Nexora Tunnel {tid} ({engine})
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={exec_line}
Restart=always
RestartSec=5
LimitNOFILE=1048576

# محدودیت‌های امنیتی — سرویس فقط به همان چیزی که لازم دارد دسترسی دارد
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths={CFG}
ProtectHome=true

[Install]
WantedBy=multi-user.target
"""
    svc = Path(f"/etc/systemd/system/{service_name(tid)}.service")
    svc.write_text(unit, encoding="utf-8")

    run(["systemctl", "daemon-reload"])
    ok, out = run(["systemctl", "enable", "--now", service_name(tid)])
    return ok, out or "service started"


def remove_service(tunnel_id):
    tid = int(tunnel_id)
    name = service_name(tid)
    run(["systemctl", "disable", "--now", name])
    for p in [Path(f"/etc/systemd/system/{name}.service")] + list(CFG.glob(f"tunnel-{tid}.*")):
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass
    run(["systemctl", "daemon-reload"])
    return True, "حذف شد"


def service_status(tunnel_id):
    name = service_name(tunnel_id)
    active, _ = run(["systemctl", "is-active", "--quiet", name])
    ok, out = run(["systemctl", "show", name,
                   "-p", "ActiveState,SubState,NRestarts,ExecMainStartTimestamp",
                   "--value"])
    parts = out.splitlines() if ok else []
    return {
        "running": active,
        "state": parts[0] if len(parts) > 0 else "unknown",
        "sub": parts[1] if len(parts) > 1 else "",
        "restarts": parts[2] if len(parts) > 2 else "0",
        "since": parts[3] if len(parts) > 3 else "",
    }


# ═══════════════════════════════════════════════════════════
#  اجرای کارها
# ═══════════════════════════════════════════════════════════

def tcp_latency(host, port, tries=5, timeout=4):
    """
    تاخیر واقعی برقراری اتصال TCP.

    این عدد از ping معمولی معنادارتر است: ping فقط ICMP را می‌سنجد
    که خیلی از مسیرها اولویت متفاوتی به آن می‌دهند، ولی این همان
    کاری را می‌کند که ترافیک واقعی می‌کند — یک اتصال کامل باز
    می‌کند و می‌بندد.
    """
    import socket
    samples, fails = [], 0

    for _ in range(tries):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        t0 = time.perf_counter()
        try:
            s.connect((host, int(port)))
            samples.append((time.perf_counter() - t0) * 1000)
        except Exception:
            fails += 1
        finally:
            try:
                s.close()
            except Exception:
                pass
        time.sleep(0.15)

    if not samples:
        return {"ok": False, "loss": 100, "tries": tries}

    samples.sort()
    n = len(samples)
    # jitter را از اختلاف نمونه‌های پیاپی می‌گیریم، نه از انحراف
    # معیار — چون آنچه کاربر حس می‌کند همین نوسان لحظه‌ای است
    jitter = 0.0
    if n > 1:
        jitter = sum(abs(samples[i] - samples[i - 1])
                     for i in range(1, n)) / (n - 1)

    return {
        "ok": True,
        "min": round(samples[0], 1),
        "avg": round(sum(samples) / n, 1),
        "max": round(samples[-1], 1),
        "median": round(samples[n // 2], 1),
        "jitter": round(jitter, 1),
        "loss": round(fails * 100.0 / tries),
        "tries": tries,
    }


def http_latency(url, tries=3, timeout=8):
    """
    زمان پاسخ HTTP — شامل TLS اگر https باشد.

    فرق مهمش با TCP این است که کل مسیر تا لایه‌ی برنامه را
    می‌سنجد، پس اگر تانل بالا باشد ولی سرویس پشتش کند باشد،
    اینجا معلوم می‌شود.
    """
    samples, codes, err = [], [], None

    for _ in range(tries):
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "nexora-agent/monitor"},
                method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                codes.append(r.status)
                samples.append((time.perf_counter() - t0) * 1000)
        except urllib.error.HTTPError as e:
            # پاسخ آمده، فقط کدش خطاست — از نظر شبکه موفق است
            codes.append(e.code)
            samples.append((time.perf_counter() - t0) * 1000)
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:70]}"
        time.sleep(0.2)

    if not samples:
        return {"ok": False, "error": err or "پاسخی نیامد"}

    return {
        "ok": True,
        "avg": round(sum(samples) / len(samples), 1),
        "min": round(min(samples), 1),
        "max": round(max(samples), 1),
        "codes": codes,
    }


def icmp_ping(host, count=5):
    """ping معمولی — برای مقایسه با تاخیر TCP."""
    if not re.match(r"^[A-Za-z0-9.\-:]{1,120}$", str(host)):
        return {"ok": False, "error": "آدرس نامعتبر"}

    ok, out = run(["ping", "-c", str(count), "-W", "3", str(host)], timeout=20)
    if not ok:
        return {"ok": False, "error": (out or "")[:120]}

    res = {"ok": True, "raw": out[-400:]}
    m = re.search(r"(\d+)% packet loss", out)
    if m:
        res["loss"] = int(m.group(1))
    m = re.search(r"=\s*([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)", out)
    if m:
        res.update(min=float(m.group(1)), avg=float(m.group(2)),
                   max=float(m.group(3)), mdev=float(m.group(4)))
    return res


def monitor(payload):
    """
    سنجش کیفیت یک تانل.

    سه معیار با هم، چون هرکدام چیز متفاوتی می‌گویند و تنها با
    مقایسه‌شان می‌شود فهمید مشکل کجاست:

      ICMP بالا، TCP بالا   → مسیر شبکه کند است
      ICMP خوب، TCP بالا    → تانل یا سرور مقصد کند است
      TCP خوب، HTTP بالا    → سرویس پشت تانل کند است
    """
    host = str(payload.get("host") or "127.0.0.1")
    ports = payload.get("ports") or []
    result = {"host": host, "at": time.strftime("%Y-%m-%d %H:%M:%S")}

    result["icmp"] = icmp_ping(host)

    # هر پورت جدا سنجیده می‌شود تا اگر یکی مشکل داشت معلوم شود
    result["tcp"] = {}
    for p in ports[:6]:
        try:
            port = int(p)
        except (TypeError, ValueError):
            continue
        result["tcp"][str(port)] = tcp_latency(host, port)

    url = payload.get("url")
    if url and str(url).startswith(("http://", "https://")):
        result["http"] = http_latency(str(url))

    return True, json.dumps(result, ensure_ascii=False)


#: ماژول‌هایی که هر ماژول پنل ممکن است لازم داشته باشد
MODULE_DEPS = {
    "monitor": ("netid",),
    "firewall": ("netid",),
}


def remote_module(name, func, payload, **kwargs):
    """
    یک ماژول پنل را روی این سرور اجرا می‌کند.

    پنل خودش monitor.py و firewall.py را دارد. به‌جای نوشتن نسخه‌ی
    دومِ همان کد داخل agent — که بلافاصله از پنل عقب می‌افتد و
    خروجی متفاوت می‌دهد — همان فایل را از پنل می‌گیریم و اجرا
    می‌کنیم. این‌طور سرور ایران دقیقاً همان اعدادی را گزارش می‌دهد
    که سرور اصلی می‌دهد، با همان آستانه‌ها و همان نام‌ها.

    فایل کنار agent کش می‌شود؛ با refresh=1 دوباره گرفته می‌شود.
    """
    try:
        import importlib.util
        mod_path = BASE / f"{name}.py"
        stamp = BASE / f".{name}.version"

        # کش را وقتی پنل نسخه عوض می‌کند دور می‌ریزیم.
        #
        # قبلاً فقط «اگر فایل نبود» دانلود می‌شد. یعنی ایجنتی که یک بار
        # monitor.py را گرفته بود، تا ابد همان را نگه می‌داشت — حتی
        # وقتی پنل به‌روز می‌شد و تابع تازه‌ای مثل snapshot اضافه
        # می‌شد. نتیجه‌اش «تابع snapshot در monitor نیست» بود و
        # مانیتورینگ هیچ‌وقت نمی‌آمد، بدون اینکه معلوم باشد چرا.
        want = str(payload.get("panelVersion") or "").strip()
        have = ""
        try:
            if stamp.exists():
                have = stamp.read_text(encoding="utf-8").strip()
        except Exception:
            have = ""

        stale = bool(want) and want != have
        if not mod_path.exists() or payload.get("refresh") or stale:
            download(f"{PANEL_URL}/api/agent/{name}.py", mod_path)
            # وابستگی‌های اختیاری: اگر پنل نداشته باشدشان، ماژول
            # خودش جایگزین داخلی دارد و نبودشان مشکلی نیست.
            for dep in MODULE_DEPS.get(name, ()):
                try:
                    download(f"{PANEL_URL}/api/agent/{dep}.py", BASE / f"{dep}.py")
                except Exception:
                    pass
            if want:
                try:
                    stamp.write_text(want, encoding="utf-8")
                except Exception:
                    pass

        # تا ماژول بتواند وابستگی‌اش را import کند
        if str(BASE) not in sys.path:
            sys.path.insert(0, str(BASE))
        def _load():
            spec = importlib.util.spec_from_file_location(f"nx_{name}", mod_path)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            return m

        try:
            m = _load()
        except Exception:
            # ماژولِ کش‌شده بارگذاری نمی‌شود — نحوش خراب است یا از
            # دانلودی نیمه‌کاره مانده. دور می‌ریزیمش و یک‌بار دوباره
            # می‌گیریم؛ وگرنه همین خطا تا نسخه‌ی بعدیِ پنل هر بار
            # تکرار می‌شود و مانیتورینگ آن نود خاموش می‌ماند.
            for p in (mod_path, stamp):
                try:
                    p.unlink()
                except OSError:
                    pass
            download(f"{PANEL_URL}/api/agent/{name}.py", mod_path)
            if want:
                try:
                    stamp.write_text(want, encoding="utf-8")
                except Exception:
                    pass
            m = _load()

        fn = getattr(m, func, None)
        if not fn:
            return False, f"تابع {func} در {name} نیست"
        return True, json.dumps(fn(**kwargs), ensure_ascii=False)
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:150]}"



#: سقف اندازه‌ی نتیجه‌ای که به پنل فرستاده می‌شود.
#:
#: قبلاً ۴۰۰۰ بود، و گزارش کامل مانیتورینگ از آن بزرگ‌تر است. نتیجه
#: این بود که JSON وسط راه بریده می‌شد، پنل نمی‌توانست بخواندش، و
#: خطا هم بی‌صدا بلعیده می‌شد — کار «موفق» ثبت می‌شد ولی هیچ داده‌ای
#: ذخیره نمی‌شد. مانیتورینگ سرورهای دیگر دقیقاً به همین دلیل همیشه
#: خالی بود.
RESULT_MAX = 200000


def _result_text(out):
    """
    نتیجه را برای فرستادن آماده می‌کند.

    اگر JSON معتبر باشد دست‌نخورده می‌رود — بریدنش یعنی نابودکردنش.
    فقط متن آزادِ خیلی بلند (مثل خروجی journalctl) کوتاه می‌شود.
    """
    text = str(out)
    if len(text) <= RESULT_MAX:
        return text
    stripped = text.lstrip()
    if stripped[:1] in ("{", "["):
        # JSON بریده‌شده بی‌فایده است؛ به‌جای نصفه‌فرستادن، صریح
        # می‌گوییم چه شد تا در پنل دیده شود
        return json.dumps({
            "error": "گزارش از سقف اندازه بزرگ‌تر بود",
            "size": len(text),
            "limit": RESULT_MAX,
        }, ensure_ascii=False)
    return text[:RESULT_MAX]


def handle(job, panel_version=""):
    action = job.get("action")
    p = job.get("payload") or {}
    if panel_version:
        p.setdefault("panelVersion", panel_version)

    if action == "install":
        return install_engine(p.get("engine", "backhaul"))

    if action == "apply":
        return write_service(p["tunnel_id"], p["engine"],
                             p["config"], p.get("side", "iran"))

    if action in ("start", "stop", "restart"):
        return run(["systemctl", action, service_name(p["tunnel_id"])])

    if action == "remove":
        return remove_service(p["tunnel_id"])

    if action == "status":
        return True, json.dumps(service_status(p["tunnel_id"]))

    if action == "logs":
        n = max(10, min(int(p.get("lines", 60)), 400))
        return run(["journalctl", "-u", service_name(p["tunnel_id"]),
                    "-n", str(n), "--no-pager", "-o", "short-iso"])

    if action == "ping":
        host = str(p.get("host", ""))
        # فقط نام میزبان یا IP — تا چیزی به دستور تزریق نشود
        if not re.match(r"^[A-Za-z0-9.\-:]{1,120}$", host):
            return False, "آدرس نامعتبر"
        return run(["ping", "-c", "4", "-W", "3", host], timeout=25)

    if action == "monitor":
        return monitor(p)

    if action == "health":
        # از همان مسیری که monitor و firewall می‌روند.
        #
        # قبلاً نسخه‌ی دومِ همان منطق این‌جا نوشته شده بود، و همان
        # اشکالی را داشت که remote_module برای رفعش ساخته شد: فقط
        # «اگر فایل نبود» دانلود می‌کرد. ایجنتی که یک‌بار health.py
        # را گرفته بود تا ابد همان را نگه می‌داشت.
        #
        # و این نظری نیست: run_all بعداً پارامتر services گرفت. هر
        # ایجنتی با نسخه‌ی قدیمیِ کش‌شده، از آن به بعد TypeError
        # می‌گیرد و سلامت آن نود دیگر هرگز به‌روز نمی‌شود — بدون
        # اینکه چیزی فایل را تازه کند.
        return remote_module(
            "health", "run_all", p,
            ports=p.get("ports"), domain=p.get("domain"),
            services=p.get("services") or ["nexora-agent", "nginx"])

    if action == "sysmon":
        return remote_module("monitor", "snapshot", p)

    if action == "firewall":
        return remote_module("firewall", "status", p)

    if action == "pathcheck":
        # عیب‌یابیِ ارتباط و شمارنده‌های ترافیک — از ۱.۶.۰. منطق در
        # linkcheck.py ِ پنل است، همان که پنل برای سمتِ خودش اجرا می‌کند.
        return remote_module(
            "linkcheck", "run", p, side=p.get("side", "iran"),
            bridge_ports=p.get("bridge_ports") or [],
            iran_hosts=p.get("iran_hosts") or [])

    if action == "update_agent":
        return update_self(p.get("url", ""))

    return False, f"دستور ناشناخته: {action}"


#: اگر چیزی این‌جا گذاشته شود، حلقه‌ی اصلی بعد از فرستادن نتیجه
#: خودش را ری‌استارت می‌کند.
RESTART_AFTER = []


def update_self(url):
    """
    به‌روزرسانی خود agent — فقط از همان پنلی که به آن وصل است.

    اگر پنل آدرسی ندهد، خودمان از PANEL_URL می‌سازیم. پنل همیشه
    آدرس بیرونی خودش را نمی‌داند (پشت nginx، دامنه‌ی متفاوت)، و اگر
    آدرس ناقص بفرستد این تابع ردش می‌کرد و به‌روزرسانی هیچ‌وقت
    انجام نمی‌شد — بدون اینکه کسی بفهمد چرا.
    """
    own = f"{PANEL_URL}/api/agent/agent.py"
    url = (url or "").strip()
    if not url or not url.startswith(PANEL_URL):
        # آدرسی که پنل داده با پنلی که ما می‌شناسیم یکی نیست. قبلاً
        # این‌جا خطا می‌دادیم و به‌روزرسانی هیچ‌وقت انجام نمی‌شد؛ ولی
        # آدرس پنل را خودمان داریم، پس دلیلی برای شکست نیست — از
        # همان‌جایی می‌گیریم که هر دقیقه با آن چک‌این می‌کنیم.
        url = own
    try:
        tmp = Path(tempfile.mktemp(suffix=".py"))
        download(url, tmp)
        text = tmp.read_text(encoding="utf-8")
        if "NEXORA_TOKEN" not in text or len(text) < 2000:
            return False, "فایل دریافتی معتبر نیست"
        target = Path(__file__).resolve()
        shutil.copy2(target, str(target) + ".bak")
        shutil.move(str(tmp), target)
        os.chmod(target, 0o755)

        # ری‌استارت این‌جا انجام *نمی‌شود*.
        #
        # systemctl restart همین پردازه را می‌کشد، و چون نتیجه‌ی کار
        # بعد از return فرستاده می‌شود، آن پیام هیچ‌وقت نمی‌رسد: کار
        # تا ابد روی «taken» می‌ماند و پنل فکر می‌کند ایجنت جواب نداده.
        #
        # حلقه‌ی اصلی اول نتیجه را می‌فرستد، بعد ری‌استارت می‌کند.
        RESTART_AFTER.append(True)
        return True, "به‌روزرسانی شد — ایجنت در حال ری‌استارت"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:120]}"


# ═══════════════════════════════════════════════════════════
#  حلقه‌ی اصلی
# ═══════════════════════════════════════════════════════════

def main():
    if not PANEL_URL or not TOKEN:
        print("Error: NEXORA_PANEL and NEXORA_TOKEN are not set", file=sys.stderr)
        sys.exit(1)

    BASE.mkdir(parents=True, exist_ok=True)
    log(f"Nexora Agent {VERSION} - panel: {PANEL_URL}")

    fails = 0
    while True:
        try:
            res = api("checkin", {"metrics": metrics()})

            if res.get("error"):
                fails += 1
                log(f"Connection failed ({fails}): {res['error']}")
                # عقب‌نشینی تدریجی تا پنل خاموش را بمباران نکنیم
                time.sleep(min(INTERVAL * min(fails, 6), 300))
                continue

            if fails:
                log("Connected")
                fails = 0

            for job in res.get("jobs", []):
                jid, action = job.get("id"), job.get("action")
                log(f"Job {jid}: {action}")
                try:
                    ok, out = handle(job, res.get("panelVersion", ""))
                except Exception as e:
                    ok, out = False, f"{type(e).__name__}: {str(e)[:200]}"
                log(f"  {'✓' if ok else '✗'} {str(out)[:110]}")
                api("job-result", {"job_id": jid, "ok": ok, "action": action,
                                   "tunnel_id": (job.get("payload") or {}).get("tunnel_id"),
                                   "result": _result_text(out)})

                # حالا که نتیجه رسیده، اگر به‌روزرسانی شده بود
                # می‌شود خودمان را ری‌استارت کرد
                if RESTART_AFTER:
                    RESTART_AFTER.clear()
                    log("Restarting after update")
                    run(["systemctl", "restart", "nexora-agent"], timeout=20)
                    return

        except KeyboardInterrupt:
            log("Exiting")
            return
        except Exception as e:
            log(f"Unexpected error: {type(e).__name__}: {str(e)[:120]}")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
