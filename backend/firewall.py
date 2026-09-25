"""
مدیریت فایروال سرور.

از ufw استفاده می‌کند چون روی اوبونتو/دبیان — که سرورهای این پنل
رویشان است — پیش‌فرض موجود است و قواعدش خوانا هستند. اگر ufw نبود،
به iptables فقط برای *خواندن* برمی‌گردیم؛ نوشتن قواعد iptables خام
بدون ufw کار خطرناکی است و بی‌سروصدا انجامش نمی‌دهیم.

قاعده‌ی طلایی این فایل: هیچ عملیاتی نباید بتواند دسترسی SSH مدیر را
قطع کند. هر مسیری که به فعال‌کردن فایروال یا حذف قاعده می‌رسد، اول
از این نگهبان رد می‌شود.
"""
import glob
import ipaddress
import os
import re
import shutil
import subprocess
import time
from datetime import datetime

#: پورت‌هایی که بستنشان یعنی قطع دسترسی خودِ مدیر یا خوابیدن سرویس.
#: این‌ها بدون تایید صریح حذف نمی‌شوند. پایه است، نه همه‌ی فهرست:
#: پورت واقعی SSH از روی سرور خوانده می‌شود و به این اضافه می‌شود.
CRITICAL_PORTS = {22: "SSH — راه ورود شما به سرور"}

SSH_LABEL = CRITICAL_PORTS[22]
SSHD_CONFIG = "/etc/ssh/sshd_config"
SSHD_CONFIG_DIR = "/etc/ssh/sshd_config.d"

_SSH_CFG_CACHE = {"at": 0.0, "ports": frozenset()}
_SSH_CFG_TTL = 60.0

#: Port 2222 — و شکل‌های دیگرش: با «=»، با فاصله‌ی اضافه، حروف بزرگ
_RE_SSH_PORT = re.compile(r"^\s*port\s*=?\s*(\d{1,5})\s*$", re.I)
#: ListenAddress 1.2.3.4:2222 یا [::1]:2222
_RE_SSH_LISTEN = re.compile(r"^\s*listenaddress\s*=?\s*(\S+)", re.I)


def _sshd_config_ports():
    """
    پورت‌های SSH از روی پیکربندی sshd.

    خواندن فایل ارزان است و به هیچ پردازه‌ای نیاز ندارد، پس این منبعِ
    پیش‌فرض است. نتیجه یک دقیقه نگه داشته می‌شود چون مسیر وضعیت
    فایروال مدام از رابط کاربری خوانده می‌شود.
    """
    now = time.time()
    if now - _SSH_CFG_CACHE["at"] < _SSH_CFG_TTL:
        return _SSH_CFG_CACHE["ports"]

    ports = set()
    files = [SSHD_CONFIG]
    try:
        files += sorted(glob.glob(os.path.join(SSHD_CONFIG_DIR, "*.conf")))
    except Exception:
        pass

    for path in files:
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except Exception:
            continue
        for line in text.splitlines():
            line = line.split("#", 1)[0]
            m = _RE_SSH_PORT.match(line)
            if m:
                p = int(m.group(1))
                if 1 <= p <= 65535:
                    ports.add(p)
                continue
            m = _RE_SSH_LISTEN.match(line)
            if m:
                addr = m.group(1)
                # [::1]:2222 یا 1.2.3.4:2222 — ولی نه «::» خالی و نه
                # آدرس آی‌پی‌ششِ بی‌پورت، که دو نقطه‌اش پورت نیست.
                tail = addr.rsplit("]:", 1)[-1] if "]" in addr else (
                    addr.rsplit(":", 1)[-1] if addr.count(":") == 1 else "")
                if tail.isdigit() and 1 <= int(tail) <= 65535:
                    ports.add(int(tail))

    _SSH_CFG_CACHE["at"] = now
    _SSH_CFG_CACHE["ports"] = frozenset(ports)
    return _SSH_CFG_CACHE["ports"]


def ssh_ports(listening=None):
    """
    پورت‌هایی که SSH واقعاً روی آن‌هاست.

    تمام نگهبان‌های این فایل تا امروز عدد ۲۲ را ثابت در کد داشتند.
    روی سروری که SSH را جابه‌جا کرده — کاری که هر راهنمای سخت‌سازی
    توصیه می‌کند — این یعنی بدترین حالت ممکن: یک قاعده‌ی جامانده روی
    ۲۲ کافی بود تا sshProtected درست شود، هشدار رابط کاربری نیاید، و
    روشن‌کردن فایروال پورت واقعی SSH را ببندد. آن مسیر ساعت‌شمار
    بازگشت هم ندارد، پس راه برگشتی جز کنسول ارائه‌دهنده نمی‌ماند.

    listening=None یعنی فقط پیکربندی خوانده شود — ارزان، برای مسیرهایی
    که رابط کاربری مدام صدایشان می‌زند. مسیرهایی که فهرست سوکت‌ها را
    از قبل دارند آن را می‌دهند تا سوکت‌های واقعی sshd هم اضافه شوند:
    اگر پیکربندی و چیزی که اجرا شده یکی نباشند، اجتماعشان امن‌ترین
    پاسخ است — پورت اضافه فقط یک هشدار بیشتر است، ولی پورت جاافتاده
    یعنی قفل‌شدن بیرونِ سرور.
    """
    found = set(_sshd_config_ports())
    for p in listening or []:
        proc = (p.get("process") or "").lower()
        if proc.startswith("sshd") or proc == "ssh":
            try:
                found.add(int(p.get("port")))
            except (TypeError, ValueError):
                continue
    return found or set(CRITICAL_PORTS)


def critical_ports(listening=None):
    """نقشه‌ی پورت‌های حیاتی، با SSH هرجا که واقعاً هست."""
    out = dict(CRITICAL_PORTS)
    for p in ssh_ports(listening):
        out.setdefault(p, SSH_LABEL)
    return out


def _run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout or "") + (r.stderr or "")
    except FileNotFoundError:
        return False, "دستور پیدا نشد"
    except subprocess.TimeoutExpired:
        return False, "زمان اجرا تمام شد"
    except Exception as e:
        return False, str(e)


def available():
    """آیا ufw روی این سرور هست؟"""
    return shutil.which("ufw") is not None



def _parse_added(out):
    """
    قاعده‌های ذخیره‌شده را از خروجی `ufw show added` می‌خواند.

    این خروجی شکل دیگری دارد: هر خط یک دستور کامل ufw است، نه یک
    سطر جدول. مثال:

        ufw deny from 203.0.113.4 to any
        ufw allow 22/tcp

    شماره‌ی قاعده ندارد چون هنوز فعال نشده؛ برای حذف هم همان دستور
    با delete لازم است، نه شماره. پس num را None می‌گذاریم و رابط
    می‌داند که هنوز اعمال نشده.
    """
    crit = critical_ports()
    rules = []
    for line in (out or "").splitlines():
        line = line.strip()
        if not line.startswith("ufw "):
            continue
        body = line[4:].strip()

        action = "ALLOW"
        for word, label in (("deny", "DENY"), ("reject", "REJECT"),
                            ("limit", "LIMIT"), ("allow", "ALLOW")):
            if body.startswith(word + " "):
                action = label
                body = body[len(word) + 1:].strip()
                break

        source = "Anywhere"
        m = re.search(r"from\s+(\S+)", body)
        if m:
            source = m.group(1)

        target, port, proto = "Anywhere", None, None
        m = re.search(r"(?:to\s+any\s+)?port\s+(\d+)", body)
        if not m:
            m = re.match(r"^(\d+)(?:/(tcp|udp))?", body)
        if m:
            try:
                port = int(m.group(1))
                target = str(port)
            except (TypeError, ValueError):
                port = None
        pm = re.search(r"/(tcp|udp)", body)
        if pm:
            proto = pm.group(1)
            if port:
                target = f"{port}/{proto}"

        rules.append({
            "num": None, "target": target, "action": action,
            "source": source, "port": port, "proto": proto,
            "pending": True, "raw": line,
            "critical": port in crit if port else False,
            "note": crit.get(port, "") if port else "",
        })
    return rules


def _parse_status(text):
    """
    خروجی `ufw status numbered` را به قواعد ساختاریافته تبدیل می‌کند.

    نمونه‌ی خط:
      [ 1] 22/tcp                     ALLOW IN    Anywhere
      [ 2] 443                        ALLOW IN    Anywhere (v6)
    """
    crit = critical_ports()
    rules = []
    for line in text.splitlines():
        m = re.match(r"\s*\[\s*(\d+)\]\s+(.+?)\s{2,}(ALLOW|DENY|REJECT|LIMIT)"
                     r"\s+(IN|OUT)?\s*(.*)$", line)
        if not m:
            continue
        num, target, act, direction, src = m.groups()
        port = None
        proto = ""
        # ufw هر قاعده را برای v6 هم می‌سازد و به مقصدش « (v6)» می‌چسباند.
        # پیش‌تر این پسوند جلوی خواندنِ پورت را می‌گرفت: نسخه‌ی v6ِ قاعده‌ی
        # SSH «حیاتی» شناخته نمی‌شد و بی‌تأیید حذف می‌شد.
        target = re.sub(r"\s*\(v6\)\s*$", "", target.strip())
        pm = re.match(r"^(\d+)(?::(\d+))?(?:/(tcp|udp))?$", target)
        if pm:
            port = int(pm.group(1))
            proto = pm.group(3) or "any"
        rules.append({
            "num": int(num),
            "target": target.strip(),
            "port": port,
            "proto": proto,
            "action": act,
            "direction": direction or "IN",
            "source": (src or "Anywhere").strip(),
            "v6": "(v6)" in (src or "") or "(v6)" in line.split(act)[0],
            "critical": port in crit if port else False,
            "note": crit.get(port, "") if port else "",
        })
    return rules


def status():
    """وضعیت فایروال و قواعدش."""
    if not available():
        return {"ready": False, "installed": False,
                "error": "ufw روی این سرور نصب نیست",
                "hint": "apt install ufw", "rules": []}

    ok, out = _run(["ufw", "status", "numbered"])
    if not ok:
        return {"ready": False, "installed": True,
                "error": f"خواندن وضعیت ناموفق: {out[:160]}", "rules": []}

    active = "Status: active" in out
    rules = _parse_status(out)

    # وقتی ufw خاموش است، `ufw status` هیچ قاعده‌ای چاپ نمی‌کند — ولی
    # قاعده‌ها واقعاً ذخیره شده‌اند و به‌محض روشن‌شدن اعمال می‌شوند.
    #
    # بدون این، کاربر یک آی‌پی را می‌بست، پیام موفقیت می‌گرفت، و بعد
    # فهرست «بسته‌شده‌ها» را خالی می‌دید — انگار هیچ اتفاقی نیفتاده.
    if not active:
        rules = _parse_added(_run(["ufw", "show", "added"])[1]) or rules

    # قاعده‌های v6 تکراری‌اند و فقط فهرست را شلوغ می‌کنند
    seen, uniq = {}, []
    for r in rules:
        key = (r["target"], r["action"], r["source"].replace(" (v6)", ""))
        if key in seen:
            # رابط می‌گوید قاعده هر دو نسخه را می‌گیرد — و حذف هر دو را برمی‌دارد
            seen[key]["both"] = True
            continue
        r["both"] = False
        seen[key] = r
        uniq.append(r)

    ssh = ssh_ports()
    ssh_open = any(r["port"] in ssh and r["action"] in ("ALLOW", "LIMIT")
                   for r in rules)

    return {
        "ready": True, "installed": True, "active": active,
        "rules": uniq, "ruleCount": len(uniq),
        "sshProtected": ssh_open,
        "sshPorts": sorted(ssh),
        "defaultIncoming": _default_incoming(out),
    }


def _default_incoming(out=""):
    """
    سیاستِ پیش‌فرضِ ورودی: deny | allow | ?

    پیش‌تر فقط در خروجیِ `ufw status numbered` دنبالِ «deny (incoming)»
    می‌گشت — ولی آن خط فقط در `status verbose` چاپ می‌شود. پس همیشه «?»
    برمی‌گشت و یادداشتِ «سیاستِ پیش‌فرض» در رابط هیچ‌وقت دیده نشد.
    فایلِ پیکربندیِ ufw هم وقتی خاموش است هم وقتی روشن جواب می‌دهد.
    """
    text = out or ""
    if "deny (incoming)" in text or "reject (incoming)" in text:
        return "deny"
    if "allow (incoming)" in text:
        return "allow"
    try:
        with open(UFW_DEFAULTS, encoding="utf-8") as f:
            m = re.search(r'^\s*DEFAULT_INPUT_POLICY\s*=\s*"?(\w+)"?', f.read(), re.M)
        if m:
            v = m.group(1).upper()
            return "deny" if v in ("DROP", "REJECT") else ("allow" if v == "ACCEPT" else "?")
    except OSError:
        pass
    ok, verbose = _run(["ufw", "status", "verbose"])
    if ok and ("deny (incoming)" in verbose or "reject (incoming)" in verbose):
        return "deny"
    if ok and "allow (incoming)" in verbose:
        return "allow"
    return "?"


#: جدا تا تست بتواند مسیرش را عوض کند
UFW_DEFAULTS = "/etc/default/ufw"


def _ssh_would_break(rules, active):
    """
    آیا فعال‌کردن فایروال، SSH را می‌بندد؟

    اگر فایروال روشن شود و هیچ قاعده‌ای پورت ۲۲ را باز نگذاشته باشد،
    مدیر بلافاصله از سرور بیرون می‌افتد و راه برگشتی جز کنسول ارائه‌دهنده
    ندارد. این بدترین اتفاقی است که این ماژول می‌تواند رقم بزند.
    """
    if active:
        return False
    # فهرست سوکت‌ها را هم می‌خوانیم: این تنها جایی است که اشتباه‌کردن
    # یعنی قطع‌شدن دسترسی، و این مسیر ساعت‌شمار بازگشت ندارد.
    ssh = ssh_ports(_read_listening())
    return not any(r["port"] in ssh and r["action"] in ("ALLOW", "LIMIT")
                   for r in rules)


def enable(confirm_ssh=False):
    """روشن‌کردن فایروال — با نگهبان SSH."""
    if not available():
        return False, "ufw نصب نیست"

    st = status()
    if st.get("active"):
        return True, "فایروال از قبل روشن است"

    if _ssh_would_break(st.get("rules") or [], st.get("active")) and not confirm_ssh:
        pl = "، ".join(str(p) for p in sorted(ssh_ports(_read_listening())))
        return False, (f"هیچ قاعده‌ای پورت SSH ({pl}) را باز نگذاشته. با "
                       "روشن‌کردن فایروال دسترسی شما به سرور قطع می‌شود. "
                       "اول قاعده‌ی SSH را اضافه کنید.")

    ok, out = _run(["ufw", "--force", "enable"], timeout=25)
    return ok, (out.strip()[:200] or ("روشن شد" if ok else "ناموفق"))


def disable():
    if not available():
        return False, "ufw نصب نیست"
    ok, out = _run(["ufw", "disable"], timeout=25)
    return ok, (out.strip()[:200] or ("خاموش شد" if ok else "ناموفق"))


def add_rule(port, proto="tcp", action="allow", source=None, comment=None):
    """
    افزودن قاعده.

    source خالی یعنی از همه‌جا. اگر آی‌پی داده شود، قاعده فقط برای
    همان مبدأ ساخته می‌شود — همان چیزی که برای بستن دسترسی یک آی‌پی
    پرمصرف لازم است.
    """
    # اعتبارسنجی قبل از بررسی ufw: پیام خطا باید بگوید *چه چیزی* غلط
    # است، نه اینکه همیشه «ufw نصب نیست» برگرداند
    try:
        port = int(port)
    except (TypeError, ValueError):
        return False, "شماره پورت نامعتبر"
    if not (1 <= port <= 65535):
        return False, "پورت باید بین ۱ تا ۶۵۵۳۵ باشد"
    if action not in ("allow", "deny", "reject", "limit"):
        return False, "عمل نامعتبر"
    if proto not in ("tcp", "udp", "any"):
        return False, "پروتکل نامعتبر"
    if source and not re.match(r"^[0-9a-fA-F:.]+(/\d{1,3})?$", str(source)):
        return False, "آدرس مبدأ نامعتبر"

    if not available():
        return False, "ufw نصب نیست"

    cmd = ["ufw", action]
    if source:
        cmd += ["from", str(source), "to", "any", "port", str(port)]
        if proto != "any":
            cmd += ["proto", proto]
    else:
        cmd.append(f"{port}/{proto}" if proto != "any" else str(port))

    if comment:
        cmd += ["comment", str(comment)[:60]]

    ok, out = _run(cmd, timeout=20)
    return ok, (out.strip()[:200] or ("اضافه شد" if ok else "ناموفق"))


def delete_rule(num, confirm_critical=False):
    """
    حذف قاعده بر اساس شماره‌اش.

    شماره‌ها بعد از هر حذف عوض می‌شوند، پس قبل از حذف دوباره وضعیت
    را می‌خوانیم و مطمئن می‌شویم همان قاعده‌ای را می‌بندیم که مدیر
    دیده — نه چیزی که جایش نشسته.
    """
    if not available():
        return False, "ufw نصب نیست"

    try:
        num = int(num)
    except (TypeError, ValueError):
        return False, "شماره قاعده نامعتبر"

    st = status()
    target = next((r for r in (st.get("rules") or []) if r["num"] == num), None)
    if not target:
        return False, "این قاعده دیگر وجود ندارد — صفحه را تازه کنید"

    if target.get("critical") and not confirm_critical:
        return False, (f"این قاعده {target.get('note') or 'حیاتی'} است. "
                       "حذفش می‌تواند دسترسی شما را قطع کند.")

    # فهرستِ رابط جفتِ v6 را پنهان می‌کند (تکراری است)، پس حذف باید
    # هر دو را بردارد — وگرنه «حذف شد» می‌آمد و پورت روی IPv6 باز می‌ماند.
    # بزرگ‌تر اول: بعد از هر حذف، شماره‌های بعدی یکی کم می‌شوند.
    raw = _parse_status(_run(["ufw", "status", "numbered"])[1] or "")
    twins = [r["num"] for r in raw
             if r["num"] != num and r["target"] == target["target"]
             and r["action"] == target["action"]
             and r["source"].replace(" (v6)", "") == target["source"].replace(" (v6)", "")]
    notes = []
    for n in sorted([num] + twins, reverse=True):
        ok, out = _run(["ufw", "--force", "delete", str(n)], timeout=20)
        if not ok:
            return False, (out.strip()[:200] or f"حذفِ قاعده‌ی {n} ناموفق بود")
        notes.append(out.strip())
    return True, ("حذف شد" + (" (همراهِ نسخه‌ی IPv6)" if twins else ""))


def _tunnel_procs():
    """
    نام پردازه‌های تانل — از netid، با جایگزین محلی.

    firewall.py گاهی بدون بقیه‌ی پروژه اجرا می‌شود (تست، اسکریپت)،
    پس نبودن netid نباید بشکندش.
    """
    try:
        import netid
        return tuple(netid.TUNNEL_PROCS)
    except Exception:
        pass
    try:
        import importlib.util
        import pathlib
        p = pathlib.Path(__file__).resolve().parent / "netid.py"
        if p.exists():
            spec = importlib.util.spec_from_file_location("netid", p)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            return tuple(m.TUNNEL_PROCS)
    except Exception:
        pass
    return ("backhaul", "backpack", "chisel", "rathole", "gost", "frpc",
            "frps", "wireguard", "wg-quick", "wstunnel", "hysteria", "tuic",
            "udp2raw", "iodine", "socat", "haproxy", "stunnel", "openvpn")


#: سرویس‌هایی که خودِ محصول است و باید باز بماند
SERVICE_PROCS = ("xray", "x-ui", "nginx", "sing-box", "caddy", "apache")


#: جاهایی که x-ui دیتابیسش را می‌گذارد.
XUI_DB_PATHS = ("/etc/x-ui/x-ui.db", "/usr/local/x-ui/x-ui.db",
                "/opt/x-ui/x-ui.db", "/etc/x-ui/db/x-ui.db")


def xray_service_ports():
    """
    پورت‌هایی که واقعاً در x-ui تعریف شده‌اند — یعنی اینباندها.

    چرا لازم است: xray علاوه بر اینباندهایش، برای هر ترافیک خروجی
    (DNS، QUIC) هم یک سوکت UDP موقت باز می‌کند. این سوکت‌ها در ss
    عیناً مثل یک سرویس در حال گوش‌دادن دیده می‌شوند — روی سرور شما
    حدود چهل‌تا از آن‌ها هست.

    نتیجه‌اش دو چیز بود: فهرست فایروال با چهل ردیف بی‌معنی پر می‌شد،
    و اگر مدیر پیشنهادها را اعمال می‌کرد، چهل قاعده‌ی ufw برای
    پورت‌هایی ساخته می‌شد که با اولین ری‌استارت xray عدد تازه
    می‌گیرند — یعنی چهل قاعده‌ی زباله که هیچ‌وقت هم پاک نمی‌شوند.

    تنها منبع درست، خودِ x-ui است. برمی‌گردانیم:
      مجموعه‌ای از پورت‌ها  — می‌دانیم اینباندها کدام‌اند
      None                  — دیتابیس خوانده نشد، پس حدس نمی‌زنیم
    """
    import sqlite3
    env = os.getenv("XUI_DB_PATH", "").strip()
    for p in ((env,) if env else ()) + XUI_DB_PATHS:
        if not p or not os.path.exists(p):
            continue
        try:
            cx = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=3)
            try:
                rows = cx.execute("SELECT port FROM inbounds").fetchall()
            finally:
                cx.close()
        except Exception:
            continue
        ports = set()
        for r in rows:
            try:
                ports.add(int(r[0]))
            except (TypeError, ValueError):
                continue
        if ports:
            return ports
    return None


def tunnel_ports_in_use():
    """
    پورت‌هایی که همین حالا یک پردازه‌ی تانل صاحبشان است.

    بستن این‌ها یعنی قطع‌شدن کامل تانل — و چون تمام ترافیک مشتری‌های
    ایران از همین‌جا رد می‌شود، یعنی قطع‌شدن سرویس. پس این‌ها مثل SSH
    محافظت‌شده‌اند، نه فقط «پیشنهاد نمی‌شوند».
    """
    ports = {}
    procs = _tunnel_procs()
    ok, out = _run(["ss", "-tunlp"], timeout=12)
    if not ok:
        return ports
    for line in out.splitlines():
        low = line.lower()
        eng = next((e for e in procs if e in low), None)
        if not eng:
            continue
        m = re.search(r"[:.](\d+)\s", line)
        if m:
            try:
                ports[int(m.group(1))] = eng
            except ValueError:
                pass
    return ports


def _is_ephemeral(port, proc, xports, tun, crit):
    """
    سوکتِ موقتِ xray — نه سرویس است، نه قاعده می‌خواهد. فقط وقتی مطمئنیم
    کنارش می‌گذاریم: یعنی وقتی فهرستِ اینباندها را از خودِ x-ui خوانده‌ایم
    و این پورت در آن نیست.

    یک تابع برای suggest و preflight: پیش‌تر فقط suggest این را داشت و
    preflight همان چهل سوکت را «بی‌قاعده — با روشن‌شدن بسته می‌شود»
    فهرست می‌کرد.
    """
    proc = (proc or "").lower()
    return (xports is not None and port not in xports
            and ("xray" in proc or "sing-box" in proc)
            and port not in tun and port not in crit)


def suggest(listening_ports=None):
    """
    پیشنهاد قواعد، بر اساس چیزی که واقعاً روی سرور گوش می‌دهد.

    مدیر نباید از حفظ بداند کدام پورت‌ها لازم‌اند. این تابع سرویس‌های
    در حال اجرا را می‌بیند و برای هر کدام می‌گوید باید باز بماند یا
    بسته شود — و *چرا*. تصمیم نهایی با مدیر است.

    سه دسته، نه دو تا:
      keep     مطمئنیم باید باز بماند — سرویس، تانل، SSH
      close    مطمئنیم به سرویس ربطی ندارد
      unknown  نام پردازه در دسترس نیست، پس نمی‌دانیم

    دسته‌ی سوم به این دلیل اضافه شد که یک پورت UDP بی‌نام به‌عنوان
    «ببند» پیشنهاد می‌شد، در حالی که می‌توانست همان تانل باشد. حدس
    را به‌جای مدیر زدن، خطرناک‌تر از نگفتن است.
    """
    if listening_ports is None:
        listening_ports = _read_listening()

    st = status()
    existing = {}
    for r in st.get("rules") or []:
        if r.get("port"):
            existing[int(r["port"])] = r["action"]

    tun = tunnel_ports_in_use()
    tprocs = _tunnel_procs()
    xports = xray_service_ports()
    crit = critical_ports(listening_ports)

    keep, close, unknown, already = [], [], [], []
    ephemeral = []
    seen = set()

    for p in listening_ports or []:
        try:
            port = int(p.get("port"))
        except (TypeError, ValueError):
            continue
        if port in seen:
            continue
        seen.add(port)

        proc = (p.get("process") or "").lower()
        known = p.get("known") or ""
        public = bool(p.get("public"))

        if _is_ephemeral(port, proc, xports, tun, crit):
            ephemeral.append({"port": port, "proto": p.get("proto") or "udp",
                              "process": p.get("process") or ""})
            continue
        row = {"port": port, "proto": p.get("proto") or "tcp",
               "process": p.get("process") or ""}

        if port in existing:
            already.append({**row, "action": existing[port],
                            "why": known or "قاعده دارد"})
            continue

        if not public:
            # فقط روی لوپ‌بک گوش می‌دهد — از بیرون قابل دسترسی نیست
            continue

        # ── تانل: قبل از هر چیز دیگری ──
        eng = tun.get(port) or next((e for e in tprocs if e in proc), None)
        if eng:
            keep.append({**row, "action": "allow", "tunnel": True,
                         "why": f"تانل {eng} روی این پورت کار می‌کند. "
                                "اگر ببندیدش، تانل و همه‌ی مشتری‌هایی که "
                                "از آن رد می‌شوند قطع می‌شوند."})
            continue

        if port in crit:
            keep.append({**row, "action": "allow", "critical": True,
                         "why": crit[port]})
        elif known:
            keep.append({**row, "action": "allow",
                         "why": f"{known} — سرویس شناخته‌شده‌ی این پنل"})
        elif any(s in proc for s in SERVICE_PROCS):
            keep.append({**row, "action": "allow",
                         "why": f"پردازه‌ی {p.get('process')} — بخشی از "
                                "سرویس شماست"})
        elif not proc:
            # بدون نام پردازه نمی‌شود گفت این چیست. ممکن است تانل باشد،
            # ممکن است چیزی که فراموش شده. پیشنهاد نمی‌دهیم.
            unknown.append({**row, "action": "deny",
                            "why": "نام پردازه در دسترس نیست، پس نمی‌دانیم "
                                   "این پورت مال چیست. اگر تانل یا سرویسی "
                                   "دارید که روی این پورت کار می‌کند، "
                                   "نبندیدش. برای دیدن نامش روی سرور: "
                                   f"ss -tulpn | grep {port}"})
        else:
            close.append({**row, "action": "deny",
                          "why": "رو به اینترنت باز است و به سرویس شما ربطی "
                                 f"ندارد — پردازه: {p.get('process')}"})

    return {
        "ready": st.get("ready", False),
        "installed": st.get("installed", False),
        "active": st.get("active", False),
        "keep": keep,
        "close": close,
        "unknown": unknown,
        "already": already,
        "ephemeral": ephemeral,
        "tunnelPorts": sorted(tun),
        "sshCovered": st.get("sshProtected", False),
    }


def _read_listening():
    """پورت‌های در حال گوش‌دادن، از ماژول مانیتورینگ."""
    try:
        import importlib.util
        import pathlib
        p = pathlib.Path(__file__).resolve().parent / "monitor.py"
        spec = importlib.util.spec_from_file_location("_fw_monitor", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m.listening() or []
    except Exception:
        return []


def apply_plan(rules, confirm=False):
    """
    اعمال دسته‌ای قواعد پیشنهادی — فقط با تایید صریح.

    خروجی می‌گوید هرکدام چه شد، چون اعمال نیمه‌کاره بدتر از اعمال
    نشدن است: مدیر باید بداند کدام قاعده ننشست.
    """
    if not confirm:
        return False, "برای اعمال قواعد باید confirm بفرستید", []
    if not available():
        return False, "ufw نصب نیست", []

    # بستن پورت تانل یعنی قطع‌شدن همه‌ی مشتری‌هایی که از آن رد
    # می‌شوند. مثل SSH، این را بدون تایید جداگانه انجام نمی‌دهیم —
    # حتی اگر خودِ پیشنهاد از همین‌جا آمده باشد.
    tun = tunnel_ports_in_use()
    crit = critical_ports(_read_listening())
    results = []
    for r in rules or []:
        port = r.get("port")
        action = r.get("action") or "allow"
        proto = r.get("proto") or "tcp"

        try:
            pnum = int(port)
        except (TypeError, ValueError):
            results.append({"port": port, "action": action, "ok": False,
                            "note": "پورت نامعتبر"})
            continue

        if action == "deny" and pnum in tun and not r.get("confirmTunnel"):
            results.append({
                "port": pnum, "action": action, "ok": False, "blocked": True,
                "note": f"پورت {pnum} را تانل {tun[pnum]} استفاده می‌کند. "
                        "بستنش تانل را قطع می‌کند، پس انجام نشد."})
            continue

        if action == "deny" and pnum in crit and not r.get("confirmCritical"):
            results.append({
                "port": pnum, "action": action, "ok": False, "blocked": True,
                "note": f"{crit[pnum]} — بسته نشد"})
            continue

        ok, note = add_rule(pnum, proto=proto, action=action,
                            comment="پیشنهاد پنل نکسورا")
        results.append({"port": pnum, "action": action, "ok": ok, "note": note})

    good = sum(1 for x in results if x["ok"])
    stopped = sum(1 for x in results if x.get("blocked"))
    msg = f"{good} از {len(results)} قاعده اعمال شد"
    if stopped:
        msg += f" — {stopped} مورد برای محافظت از تانل یا SSH انجام نشد"
    return True, msg, results


#: کم‌ترین طول پیشوندی که می‌پذیریم — کوتاه‌تر از این یعنی نصف
#: اینترنت. بستن یک /8 برای مسدودکردن یک کشور معنا دارد؛ /0 تا /7 نه.
MIN_PREFIX_V4 = 8
MIN_PREFIX_V6 = 16


def block_refusal(ip, protect=None):
    """
    چرا این آدرس را نباید بست — یا None اگر اشکالی ندارد.

    قاعده‌ی طلایی این فایل می‌گوید هیچ عملیاتی نباید دسترسی SSH مدیر
    را قطع کند، ولی بستن آی‌پی از این نگهبان رد نمی‌شد. آی‌پی خودِ
    مدیر هم می‌تواند در فهرست تلاش‌های ناموفق بنشیند — چند بار اشتباه
    زدن رمز کافی است — و بعد یک کلیک روی «بستن مهاجم‌ها» قاعده را
    *در جایگاه اول* می‌نشاند، جلوتر از قاعده‌ی مجازِ SSH. این مسیر
    ساعت‌شمار بازگشت هم ندارد.

    protect آدرسی است که همین درخواست از آن آمده. هر چیز دیگری هم
    که بستنش یعنی قطع‌کردن خودمان این‌جا رد می‌شود: لوپ‌بک، آدرس
    داخلی، و رنجی که آن‌قدر بزرگ است که معنایش «همه».
    """
    raw = str(ip or "").strip()
    if not _ip_ok(raw):
        return "آدرس نامعتبر"

    try:
        net = ipaddress.ip_network(raw, strict=False)
    except ValueError:
        return "آدرس نامعتبر"

    if protect:
        try:
            if ipaddress.ip_address(str(protect).strip()) in net:
                return ("این همان آدرسی است که خودتان از آن وصل‌اید — "
                        "بستنش یعنی قطع‌شدن دسترسی خودتان")
        except ValueError:
            pass

    if net.is_loopback:
        return "لوپ‌بک است — بستنش فقط خود سرور را می‌شکند"
    if net.is_unspecified:
        return "این یعنی «همه‌ی آدرس‌ها»"
    if net.is_private or net.is_link_local:
        return "آدرس داخلی است، نه مهاجم از بیرون"

    floor = MIN_PREFIX_V4 if net.version == 4 else MIN_PREFIX_V6
    if net.prefixlen < floor:
        return (f"این رنج بیش از حد بزرگ است (/{net.prefixlen}) — "
                f"دست‌کم /{floor} لازم است")
    return None


def block_ip(ip, comment=None, protect=None):
    """بستن کامل یک آی‌پی — برای وقتی یک مبدأ دارد سرور را می‌خورد."""
    why = block_refusal(ip, protect)
    if why:
        return False, why
    if not available():
        return False, "ufw نصب نیست"

    cmd = ["ufw", "insert", "1", "deny", "from", str(ip), "to", "any"]
    if comment:
        cmd += ["comment", str(comment)[:60]]
    ok, out = _run(cmd, timeout=20)
    return ok, (out.strip()[:200] or ("بسته شد" if ok else "ناموفق"))


def unblock_ip(ip):
    if not available():
        return False, "ufw نصب نیست"
    ok, out = _run(["ufw", "delete", "deny", "from", str(ip), "to", "any"],
                   timeout=20)
    return ok, (out.strip()[:200] or ("باز شد" if ok else "ناموفق"))


# ═══════════════════════════════════════════════════════════
#  روشن‌کردن امن، با بازگشت خودکار
# ═══════════════════════════════════════════════════════════

#: جایی که نشانه‌ی «تایید شد» گذاشته می‌شود
_ARM_FLAG = "/run/nexora-fw-armed"
_ARM_LOG = "/var/log/nexora-firewall-rollback.log"


def preflight():
    """
    قبل از روشن‌کردن، هر چیزی که ممکن است قطع شود را فهرست می‌کند.

    ترس از روشن‌کردن فایروال بی‌دلیل نیست: یک قاعده‌ی جاافتاده یعنی
    قطع‌شدن SSH، یا تانل، یا خود پنل — و بعدش راهی برای برگشتن نیست
    مگر از کنسول ارائه‌دهنده.

    این تابع به‌جای «امیدوارم درست باشد»، فهرست می‌دهد: چه چیزی الان
    گوش می‌دهد، کدامشان قاعده دارد، و کدام‌ها با روشن‌شدن قطع می‌شوند.
    """
    st = status()
    if not st.get("installed"):
        return {"ready": False, "error": "ufw نصب نیست"}

    allowed = set()
    for r in st.get("rules") or []:
        if r.get("port") and r.get("action") in ("ALLOW", "LIMIT"):
            allowed.add(int(r["port"]))

    listening = _read_listening() or []
    tun = tunnel_ports_in_use()
    crit = critical_ports(listening)
    xports = xray_service_ports()

    at_risk, covered = [], []
    for p in listening:
        try:
            port = int(p.get("port"))
        except (TypeError, ValueError):
            continue
        if not p.get("public"):
            continue
        if _is_ephemeral(port, p.get("process"), xports, tun, crit):
            continue

        why = ""
        critical = False
        if port in crit:
            why, critical = crit[port], True
        elif port in tun:
            why = f"تانل {tun[port]} — تمام مشتری‌های ایران از این رد می‌شوند"
            critical = True
        elif p.get("known"):
            why = p["known"]
        elif p.get("process"):
            why = f"پردازه‌ی {p['process']}"

        row = {"port": port, "proto": p.get("proto") or "tcp",
               "process": p.get("process") or "", "why": why,
               "critical": critical}
        (covered if port in allowed else at_risk).append(row)

    blockers = [r for r in at_risk if r["critical"]]

    return {
        "ready": True,
        "active": st.get("active", False),
        "atRisk": at_risk,
        "covered": covered,
        "blockers": blockers,
        "safe": not blockers,
        "note": ("همه‌چیز پوشش دارد" if not at_risk else
                 f"{len(at_risk)} سرویس قاعده ندارد و با روشن‌شدن قطع می‌شود"),
    }


def _schedule_rollback(minutes):
    """
    یک ساعت‌شمار می‌گذارد که اگر تایید نیاید، فایروال را خاموش کند.

    این همان چیزی است که روشن‌کردن فایروال از راه دور را بی‌خطر
    می‌کند: اگر قاعده‌ای جا افتاده باشد و ارتباطتان قطع شود، لازم
    نیست به کنسول ارائه‌دهنده بروید — چند دقیقه صبر می‌کنید و سرور
    خودش برمی‌گردد به حالت قبل.

    اول systemd-run را امتحان می‌کنیم چون مستقل از پردازه‌ی پنل
    زندگی می‌کند؛ اگر نبود، یک پردازه‌ی جداشده با nohup.
    """
    secs = max(60, int(minutes) * 60)
    script = (
        f"sleep {secs}; "
        f"if [ ! -f {_ARM_FLAG} ]; then "
        f"  ufw --force disable >> {_ARM_LOG} 2>&1; "
        f"  echo \"$(date -Is) فایروال به‌دلیل نیامدن تایید خاموش شد\" "
        f">> {_ARM_LOG}; "
        f"fi; rm -f {_ARM_FLAG}"
    )

    if shutil.which("systemd-run"):
        ok, out = _run(["systemd-run", "--quiet", "--collect",
                        "--unit", "nexora-fw-rollback",
                        "/bin/sh", "-c", script], timeout=15)
        if ok:
            return True, "systemd"

    try:
        subprocess.Popen(["/bin/sh", "-c", script],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return True, "background"
    except Exception as e:
        return False, str(e)[:120]


def safe_enable(confirm=False, rollback_minutes=5, force=False):
    """
    روشن‌کردن فایروال با تور نجات.

    مراحل:
      ۱. بررسی می‌کند چه چیزی قطع می‌شود
      ۲. اگر چیز حیاتی‌ای (SSH یا تانل) قاعده ندارد، رد می‌کند
      ۳. یک ساعت‌شمار بازگشت می‌گذارد
      ۴. فایروال را روشن می‌کند

    بعد از این، مدیر باید ظرف مهلت تعیین‌شده confirm_enabled() را
    صدا بزند. اگر نزند — یعنی اگر ارتباطش قطع شده باشد — فایروال
    خودش خاموش می‌شود.

    force: رد کردن هشدارها. فقط وقتی مدیر صریحاً بداند چه می‌کند.
    """
    if not confirm:
        return False, "برای روشن‌کردن فایروال باید confirm بفرستید", {}

    pre = preflight()
    if not pre.get("ready"):
        return False, pre.get("error") or "بررسی اولیه ناموفق", pre

    if pre["blockers"] and not force:
        names = "، ".join(
            f"{b['port']} ({b['why']})" for b in pre["blockers"][:4])
        return False, (f"روشن نشد — این‌ها قاعده ندارند و قطع می‌شوند: "
                       f"{names}. اول برایشان قاعده‌ی allow بسازید."), pre

    minutes = max(2, min(int(rollback_minutes or 5), 60))

    # نشانه‌ی قبلی را پاک می‌کنیم تا ساعت‌شمار تازه معتبر باشد
    try:
        if os.path.exists(_ARM_FLAG):
            os.remove(_ARM_FLAG)
    except Exception:
        pass

    sched_ok, how = _schedule_rollback(minutes)
    if not sched_ok and not force:
        return False, (f"ساعت‌شمار بازگشت گذاشته نشد ({how}) — بدون آن "
                       "روشن‌کردن از راه دور خطرناک است"), pre

    ok, out = _run(["ufw", "--force", "enable"], timeout=30)
    if not ok:
        # ساعت‌شمار را بی‌اثر می‌کنیم چون اصلاً روشن نشد
        _touch_flag()
        return False, f"روشن نشد: {out.strip()[:160]}", pre

    return True, (f"فایروال روشن شد. اگر تا {minutes} دقیقه‌ی دیگر تایید "
                  "نکنید، خودش خاموش می‌شود — پس اگر ارتباطتان قطع شد، "
                  "فقط صبر کنید."), {
        **pre, "rollbackMinutes": minutes, "scheduler": how, "armed": True}


def _touch_flag():
    try:
        d = os.path.dirname(_ARM_FLAG)
        if not os.path.isdir(d):
            d = "/tmp"
        path = os.path.join(d, os.path.basename(_ARM_FLAG))
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(int(time.time())))
        return True
    except Exception:
        return False


def confirm_enabled():
    """
    «همه‌چیز کار می‌کند» — ساعت‌شمار بازگشت لغو می‌شود.

    اینکه این درخواست اصلاً به پنل رسیده، خودش ثابت می‌کند ارتباط
    برقرار است. به همین دلیل تاییدِ دستی کافی و درست است.
    """
    if not _touch_flag():
        return False, "ثبت تایید ناموفق بود"
    if shutil.which("systemctl"):
        _run(["systemctl", "stop", "nexora-fw-rollback.service"], timeout=10)
    return True, "تایید شد — فایروال روشن می‌ماند"


def rollback_state():
    """وضعیت ساعت‌شمار بازگشت، برای نمایش در پنل."""
    armed = False
    if shutil.which("systemctl"):
        ok, out = _run(["systemctl", "is-active",
                        "nexora-fw-rollback.service"], timeout=8)
        armed = (out or "").strip() == "active"
    confirmed = os.path.exists(_ARM_FLAG) or os.path.exists(
        os.path.join("/tmp", os.path.basename(_ARM_FLAG)))
    return {"armed": armed and not confirmed, "confirmed": confirmed}


# ═══════════════════════════════════════════════════════════
#  بستن آی‌پی بدون فایروال
# ═══════════════════════════════════════════════════════════

#: جایی که آدرس‌های بسته‌شده نگه داشته می‌شوند تا بعد از ریبوت
#: دوباره اعمال شوند. مسیر روتینگ در حافظه است و با ریستارت می‌رود.
BLOCKLIST = "/etc/nexora/blocked-ips.txt"


def _ip_ok(ip):
    """آدرس یا رنج معتبر — همان صافی‌ای که block_ip دارد."""
    return bool(re.match(r"^[0-9a-fA-F:.]+(/\d{1,3})?$", str(ip or "").strip()))


def blackhole_available():
    """آیا دستور ip هست. تقریباً روی هر لینوکسی هست، ولی فرض نمی‌کنیم."""
    return shutil.which("ip") is not None


def blackhole_list():
    """
    آدرس‌هایی که همین حالا سیاه‌چاله شده‌اند.

    از خود کرنل می‌خوانیم، نه از فایل — فایل فقط برای بازگرداندن
    بعد از ریبوت است و ممکن است با واقعیت یکی نباشد.
    """
    out_set = []
    ok, out = _run(["ip", "route", "show", "type", "blackhole"], timeout=10)
    if ok:
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "blackhole":
                out_set.append(parts[1])
    return out_set


def blackhole_add(ip, note=None, protect=None):
    """
    بستن یک آدرس بدون فایروال.

    چرا این روش:
        روشن‌کردن ufw روی سرور راه دور ریسک دارد و خیلی‌ها — به‌درستی —
        حاضر نیستند بپذیرندش. ولی «این آدرس دارد سرور را می‌خورد و
        می‌خواهم همین حالا قطعش کنم» یک نیاز فوری است که نباید منتظر
        آن تصمیم بماند.

        مسیر blackhole کاری با فایروال ندارد: کرنل هر بسته‌ای را که
        *به* آن آدرس برود دور می‌اندازد. یعنی دست‌دادن TCP هیچ‌وقت
        کامل نمی‌شود و اتصال از همان اول می‌میرد.

        فوری است، هیچ سرویسی را لمس نمی‌کند، و برگشتش یک دستور است.

    محدودیتش را هم صریح بگوییم: این ترافیک ورودی را «فیلتر» نمی‌کند،
    فقط جواب را قطع می‌کند. برای اسکنر و حدس‌زن رمز کافی است؛ برای
    حمله‌ی حجمی، فایروال لازم است.
    """
    ip = str(ip or "").strip()
    why = block_refusal(ip, protect)
    if why:
        return False, why
    if not blackhole_available():
        return False, "دستور ip روی این سرور نیست"

    if ip in blackhole_list():
        return True, "از قبل بسته بود"

    ok, out = _run(["ip", "route", "add", "blackhole", ip], timeout=15)
    if not ok and "File exists" not in out:
        return False, out.strip()[:180] or "ناموفق"

    _blocklist_write(ip, note, remove=False)
    return True, f"{ip} بسته شد — بدون نیاز به فایروال"


def blackhole_remove(ip):
    """بازکردن یک آدرس سیاه‌چاله‌شده."""
    ip = str(ip or "").strip()
    if not _ip_ok(ip):
        return False, "آدرس نامعتبر"
    if not blackhole_available():
        return False, "دستور ip روی این سرور نیست"

    ok, out = _run(["ip", "route", "del", "blackhole", ip], timeout=15)
    _blocklist_write(ip, None, remove=True)
    if not ok and "No such process" not in out:
        return False, out.strip()[:180] or "ناموفق"
    return True, f"{ip} باز شد"


def _blocklist_write(ip, note, remove):
    """
    فهرست ماندگار را به‌روز می‌کند.

    مسیر روتینگ در حافظه است و با ریبوت پاک می‌شود. بدون این فایل،
    آدرسی که مدیر بسته، بعد از اولین ریستارت بی‌سروصدا باز می‌شود —
    و او فکر می‌کند هنوز بسته است.
    """
    try:
        d = os.path.dirname(BLOCKLIST)
        os.makedirs(d, exist_ok=True)
        rows = []
        if os.path.exists(BLOCKLIST):
            with open(BLOCKLIST, "r", encoding="utf-8") as f:
                rows = [l.rstrip("\n") for l in f if l.strip()]
        rows = [r for r in rows if r.split("|")[0].strip() != ip]
        if not remove:
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            rows.append(f"{ip} | {stamp} | {(note or '').replace('|', ' ')[:60]}")
        with open(BLOCKLIST, "w", encoding="utf-8") as f:
            f.write("\n".join(rows) + ("\n" if rows else ""))
    except Exception:
        # نوشتن فایل نباید مانع بستن آدرس شود
        pass


def blackhole_restore():
    """
    بعد از ریبوت، آدرس‌های ذخیره‌شده را دوباره می‌بندد.

    پنل این را موقع بالا آمدن صدا می‌زند.
    """
    if not blackhole_available() or not os.path.exists(BLOCKLIST):
        return 0
    done = 0
    live = set(blackhole_list())
    try:
        with open(BLOCKLIST, "r", encoding="utf-8") as f:
            for line in f:
                ip = line.split("|")[0].strip()
                if not ip or ip in live or not _ip_ok(ip):
                    continue
                ok, _ = _run(["ip", "route", "add", "blackhole", ip], timeout=10)
                if ok:
                    done += 1
    except Exception:
        pass
    return done


def blocked_overview():
    """
    همه‌ی آدرس‌های بسته — از هر دو راه.

    مدیر نباید دو جای جدا را نگاه کند تا بفهمد یک آدرس بسته هست یا
    نه. این‌جا هر دو کنار هم می‌آیند، با ذکر اینکه هرکدام از کدام
    راه بسته شده.
    """
    rows = []

    for ip in blackhole_list():
        rows.append({"ip": ip, "via": "blackhole", "active": True,
                     "how": "مسیر سیاه‌چاله‌ی کرنل — بدون فایروال کار می‌کند"})

    st = status()
    for r in st.get("rules") or []:
        src = (r.get("source") or "").strip()
        if r.get("action") == "DENY" and src and src != "Anywhere":
            rows.append({
                "ip": src, "via": "ufw",
                "active": bool(st.get("active")),
                "pending": bool(r.get("pending")),
                "num": r.get("num"),
                "how": ("قاعده‌ی فایروال" if st.get("active")
                        else "قاعده‌ی فایروال — تا روشن‌شدن ufw اثری ندارد"),
            })

    return {"blocked": rows,
            "firewallActive": bool(st.get("active")),
            "blackholeAvailable": blackhole_available()}


def blackhole_verify(ip):
    """
    واقعاً بسته شده؟

    «پیام موفقیت دیدم» با «بسته شده» یکی نیست. این تابع از خود کرنل
    می‌پرسد، نه از فایلی که خودمان نوشته‌ایم — تنها جواب قابل اتکا.
    """
    n = str(ip or "").strip()
    if not _ip_ok(n):
        return {"ip": n, "blocked": False, "why": "آدرس نامعتبر"}
    if not blackhole_available():
        return {"ip": n, "blocked": False, "why": "دستور ip در دسترس نیست"}

    ok, out = _run(["ip", "route", "get", n.split("/")[0]], timeout=10)
    if ok and "blackhole" in (out or "").lower():
        return {"ip": n, "blocked": True,
                "why": "کرنل تأیید می‌کند: مسیر این آدرس سیاه‌چاله است"}

    if n in blackhole_list():
        return {"ip": n, "blocked": True,
                "why": "در جدول مسیرهای سیاه‌چاله هست"}

    return {"ip": n, "blocked": False,
            "why": "کرنل مسیر عادی برایش دارد — بسته نیست"}


def blackhole_bulk(ips, note=None, remove=False, protect=None):
    """
    بستن یا بازکردن دسته‌ای.

    وقتی یک اسکن با صد آدرس می‌آید، واردکردن دستی صدتا نه شدنی است
    نه بی‌خطا. خروجی برای هر آدرس جدا می‌گوید چه شد، چون «۹۷ تا از
    ۱۰۰ تا» بدون فهرست آن سه‌تا بی‌فایده است.
    """
    seen, rows = set(), []
    for raw in (ips or []):
        ip = str(raw or "").strip()
        if not ip or ip.startswith("#"):
            continue
        # فایل‌های صادرشده ممکن است ستون‌های دیگری هم داشته باشند
        ip = ip.split("|")[0].split(",")[0].split()[0].strip()
        if not ip or ip in seen:
            continue
        seen.add(ip)

        if remove:
            ok, msg = blackhole_remove(ip)
        else:
            ok, msg = blackhole_add(ip, note=note, protect=protect)
        rows.append({"ip": ip, "ok": ok, "note": msg})

    good = sum(1 for r in rows if r["ok"])
    verb = "باز شد" if remove else "بسته شد"
    return {
        "ok": True,
        "total": len(rows),
        "done": good,
        "failed": len(rows) - good,
        "results": rows,
        "note": f"{good} از {len(rows)} آدرس {verb}",
    }


def blackhole_export():
    """
    فهرست آدرس‌های بسته، به‌شکل متنی قابل ذخیره.

    همان قالبی که bulk می‌خواند، پس خروجی یک سرور مستقیم روی سرور
    دیگر قابل واردکردن است.
    """
    rows = blackhole_list()
    lines = [
        "# آدرس‌های بسته‌شده — نکسورا",
        f"# {datetime.now():%Y-%m-%d %H:%M}",
        f"# {len(rows)} آدرس",
        "",
    ]
    lines.extend(rows)
    return "\n".join(lines) + "\n"
