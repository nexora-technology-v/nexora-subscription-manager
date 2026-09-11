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
import re
import shutil
import subprocess

#: پورت‌هایی که بستنشان یعنی قطع دسترسی خودِ مدیر یا خوابیدن سرویس.
#: این‌ها بدون تایید صریح حذف نمی‌شوند.
CRITICAL_PORTS = {22: "SSH — راه ورود شما به سرور"}


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


def _parse_status(text):
    """
    خروجی `ufw status numbered` را به قواعد ساختاریافته تبدیل می‌کند.

    نمونه‌ی خط:
      [ 1] 22/tcp                     ALLOW IN    Anywhere
      [ 2] 443                        ALLOW IN    Anywhere (v6)
    """
    rules = []
    for line in text.splitlines():
        m = re.match(r"\s*\[\s*(\d+)\]\s+(.+?)\s{2,}(ALLOW|DENY|REJECT|LIMIT)"
                     r"\s+(IN|OUT)?\s*(.*)$", line)
        if not m:
            continue
        num, target, act, direction, src = m.groups()
        port = None
        proto = ""
        pm = re.match(r"^(\d+)(?::(\d+))?(?:/(tcp|udp))?$", target.strip())
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
            "v6": "(v6)" in (src or ""),
            "critical": port in CRITICAL_PORTS if port else False,
            "note": CRITICAL_PORTS.get(port, "") if port else "",
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

    # قاعده‌های v6 تکراری‌اند و فقط فهرست را شلوغ می‌کنند
    seen, uniq = set(), []
    for r in rules:
        key = (r["target"], r["action"], r["source"].replace(" (v6)", ""))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)

    ssh_open = any(r["port"] == 22 and r["action"] in ("ALLOW", "LIMIT")
                   for r in rules)

    return {
        "ready": True, "installed": True, "active": active,
        "rules": uniq, "ruleCount": len(uniq),
        "sshProtected": ssh_open,
        "defaultIncoming": ("deny" if "deny (incoming)" in out
                            else ("allow" if "allow (incoming)" in out else "?")),
    }


def _ssh_would_break(rules, active):
    """
    آیا فعال‌کردن فایروال، SSH را می‌بندد؟

    اگر فایروال روشن شود و هیچ قاعده‌ای پورت ۲۲ را باز نگذاشته باشد،
    مدیر بلافاصله از سرور بیرون می‌افتد و راه برگشتی جز کنسول ارائه‌دهنده
    ندارد. این بدترین اتفاقی است که این ماژول می‌تواند رقم بزند.
    """
    if active:
        return False
    return not any(r["port"] == 22 and r["action"] in ("ALLOW", "LIMIT")
                   for r in rules)


def enable(confirm_ssh=False):
    """روشن‌کردن فایروال — با نگهبان SSH."""
    if not available():
        return False, "ufw نصب نیست"

    st = status()
    if st.get("active"):
        return True, "فایروال از قبل روشن است"

    if _ssh_would_break(st.get("rules") or [], st.get("active")) and not confirm_ssh:
        return False, ("هیچ قاعده‌ای پورت ۲۲ (SSH) را باز نگذاشته. با روشن‌کردن "
                       "فایروال دسترسی شما به سرور قطع می‌شود. اول قاعده‌ی SSH "
                       "را اضافه کنید.")

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

    ok, out = _run(["ufw", "--force", "delete", str(num)], timeout=20)
    return ok, (out.strip()[:200] or ("حذف شد" if ok else "ناموفق"))


def suggest(listening_ports=None):
    """
    پیشنهاد قواعد، بر اساس چیزی که واقعاً روی سرور گوش می‌دهد.

    مدیر نباید از حفظ بداند کدام پورت‌ها لازم‌اند. این تابع سرویس‌های
    در حال اجرا را می‌بیند و برای هر کدام می‌گوید باید باز بماند یا
    بسته شود — و *چرا*. تصمیم نهایی با مدیر است؛ این‌جا فقط پیشنهاد
    ساخته می‌شود، هیچ قاعده‌ای اعمال نمی‌شود.

    listening_ports: خروجی monitor.listening()؛ اگر داده نشود خودمان
    می‌خوانیم.
    """
    if listening_ports is None:
        listening_ports = _read_listening()

    st = status()
    existing = {}
    for r in st.get("rules") or []:
        if r.get("port"):
            existing[int(r["port"])] = r["action"]

    keep, close, already = [], [], []
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

        if port in existing:
            already.append({"port": port, "proto": p.get("proto") or "tcp",
                            "process": p.get("process") or "",
                            "action": existing[port], "why": known or "قاعده دارد"})
            continue

        if not public:
            # فقط روی لوپ‌بک گوش می‌دهد — از بیرون قابل دسترسی نیست
            continue

        if port in CRITICAL_PORTS:
            keep.append({"port": port, "proto": p.get("proto") or "tcp",
                         "process": p.get("process") or "",
                         "action": "allow",
                         "why": CRITICAL_PORTS[port]})
        elif known:
            keep.append({"port": port, "proto": p.get("proto") or "tcp",
                         "process": p.get("process") or "",
                         "action": "allow",
                         "why": f"{known} — سرویس شناخته‌شده‌ی این پنل"})
        elif any(s in proc for s in ("xray", "x-ui", "nginx", "sing-box",
                                     "hysteria", "wireguard")):
            keep.append({"port": port, "proto": p.get("proto") or "tcp",
                         "process": p.get("process") or "",
                         "action": "allow",
                         "why": f"پردازه‌ی {p.get('process')} — بخشی از سرویس شماست"})
        else:
            close.append({"port": port, "proto": p.get("proto") or "tcp",
                          "process": p.get("process") or "",
                          "action": "deny",
                          "why": ("رو به اینترنت باز است و به سرویس شما ربطی "
                                  "ندارد" + (f" — پردازه: {p.get('process')}"
                                             if p.get("process") else ""))})

    return {
        "ready": st.get("ready", False),
        "installed": st.get("installed", False),
        "active": st.get("active", False),
        "keep": keep,
        "close": close,
        "already": already,
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

    results = []
    for r in rules or []:
        port = r.get("port")
        action = r.get("action") or "allow"
        proto = r.get("proto") or "tcp"
        ok, note = add_rule(port, proto=proto, action=action,
                            comment="پیشنهاد پنل نکسورا")
        results.append({"port": port, "action": action, "ok": ok, "note": note})

    good = sum(1 for x in results if x["ok"])
    return True, f"{good} از {len(results)} قاعده اعمال شد", results


def block_ip(ip, comment=None):
    """بستن کامل یک آی‌پی — برای وقتی یک مبدأ دارد سرور را می‌خورد."""
    if not re.match(r"^[0-9a-fA-F:.]+(/\d{1,3})?$", str(ip or "")):
        return False, "آدرس نامعتبر"
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
