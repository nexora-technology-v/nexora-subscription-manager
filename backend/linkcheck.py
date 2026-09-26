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
    """
    برقراریِ اتصالِ TCP — همان کاری که ترافیکِ واقعی می‌کند.

    سه نتیجه‌ی جدا، چون هر کدام خبرِ دیگری است:
      open     دست‌دادن کامل شد
      refused  جوابِ «رد» (RST) آمد — کسی آن طرف جواب داد؛ `rst_ms` زمانش.
               RST ای که زودتر از رفت‌وبرگشتِ پینگ برسد از خودِ سرور نیامده
               (tcp_findings)
      timeout  هیچ جوابی — بسته‌ها بینِ راه دور ریخته می‌شوند

    `loss` فقط بی‌جواب‌ها را می‌شمارد: RST واقعی یعنی مسیرِ TCP باز است و
    فقط آن پورت بسته. پیش‌تر هر «رد» پرت حساب می‌شد و مسیرِ سالم به سرورِ
    ایرانی که ۲۲ و ۴۴۳ اش بسته بود «قطع» نشان داده می‌شد.
    """
    samples, rst, timeouts, other = [], [], 0, 0
    for _ in range(tries):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        t0 = time.perf_counter()
        try:
            s.connect((host, int(port)))
            samples.append((time.perf_counter() - t0) * 1000)
        except ConnectionRefusedError:
            rst.append((time.perf_counter() - t0) * 1000)
        except (socket.timeout, TimeoutError):
            timeouts += 1
        except (OSError, ValueError):
            other += 1
        finally:
            try:
                s.close()
            except OSError:
                pass
        time.sleep(0.1)
    out = {"loss": round((timeouts + other) * 100 / tries), "tries": tries,
           "open": len(samples), "refused": len(rst), "timeout": timeouts + other}
    if samples:
        out["avg"] = round(sum(samples) / len(samples), 1)
    if rst:
        out["rst_ms"] = round(sorted(rst)[len(rst) // 2], 1)
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
    """
    TCP اگر هست (همان که ترافیک استفاده می‌کند)، وگرنه ICMP. `loss` TCP فقط
    بی‌جواب‌هاست (tcp_probe)؛ پورتِ بسته‌ای که «رد» گفت، مسیرِ TCP را باز نشان می‌دهد.
    """
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
#  «پینگ می‌رود ولی TCP نه» — آزمونِ TCP
# ═══════════════════════════════════════════════════════════

#: اندازه‌ی payload پینگ با DF؛ MTU = اندازه + ۲۸
MTU_STEPS = (1472, 1432, 1400, 1372, 1332, 1272, 1172, 972, 548)

#: پورت‌هایی که در آزمونِ TCP کنارِ پورتِ تانل امتحان می‌شوند
TCP_TEST_PORTS = (443, 80, 22, 8080, 2053)


def _ping_df(host, size, timeout=2):
    """پینگِ بی‌تکه (DF) با payload مشخص. True/False، یا None اگر ping این سرور DF ندارد."""
    try:
        p = subprocess.run(["ping", "-M", "do", "-c", "2", "-W", str(timeout),
                            "-s", str(size), str(host)],
                           capture_output=True, text=True, timeout=timeout * 3 + 3)
    except (OSError, subprocess.SubprocessError):
        return None
    txt = (p.stdout or "") + (p.stderr or "")
    if "invalid" in txt.lower() or "usage" in txt.lower():
        return None
    m = re.search(r"(\d+) received", txt)
    return bool(m and int(m.group(1)) > 0)


def mtu_probe(host):
    """
    بزرگ‌ترین بسته‌ای که بی‌تکه‌شدن تا مقصد می‌رسد.

    پینگِ معمولی ۸۴ بایت است و از هر مسیری رد می‌شود. اگر مسیری بسته‌ی
    بزرگ را بی‌صدا دور بریزد، TCP دست می‌دهد (بسته‌های دست‌دادن کوچک‌اند)
    ولی داده‌ی واقعی گیر می‌کند — دقیقاً «وصل است ولی کار نمی‌کند».
    """
    if not re.match(r"^[A-Za-z0-9.\-:]{1,120}$", str(host)):
        return None
    with ThreadPoolExecutor(max_workers=len(MTU_STEPS)) as ex:
        res = dict(zip(MTU_STEPS, ex.map(lambda n: _ping_df(host, n), MTU_STEPS)))
    if all(v is None for v in res.values()):
        return None
    ok = [n for n, v in res.items() if v]
    return {"max": (max(ok) + 28) if ok else None, "steps": {str(k): v for k, v in res.items()}}


def tcp_check(host, ports=None, tries=3, timeout=3.0):
    """
    آزمونِ TCP یک آی‌پی: پینگ، چند پورت (باز / رد / بی‌جواب، و زمانِ RST)،
    و MTU مسیر — هم‌زمان، چند ثانیه.
    """
    want = []
    for p in list(ports or []) + list(TCP_TEST_PORTS):
        try:
            p = int(p)
        except (TypeError, ValueError):
            continue
        if 0 < p < 65536 and p not in want:
            want.append(p)
    want = want[:8]
    with ThreadPoolExecutor(max_workers=len(want) + 2) as ex:
        f_icmp = ex.submit(icmp_probe, host, 4)
        f_mtu = ex.submit(mtu_probe, host)
        f_ports = {p: ex.submit(tcp_probe, host, p, tries, timeout) for p in want}
        return {"host": host, "icmp": f_icmp.result(), "mtu": f_mtu.result(),
                "ports": {str(p): f.result() for p, f in f_ports.items()}}


def tcp_findings(check, tunnel=None, tunnel_ports=()):
    """
    «پینگ می‌رود ولی TCP نه» — کدام‌یک از علت‌های شناخته‌شده؟

    هر یافته: {level, id, title, why, fix}. ترتیب مهم است: اگر TCP به کلِ
    آی‌پی بسته است، گفتنِ «MTU کوچک است» گمراه‌کننده است.
    """
    out = []
    if not check:
        return out
    icmp = check.get("icmp") or {}
    rtt = icmp.get("avg")
    ports = {int(k): v for k, v in (check.get("ports") or {}).items() if v}
    ping_ok = icmp and icmp.get("loss", 100) < 50
    answered = [p for p, v in ports.items() if v.get("open") or v.get("refused")]
    silent = [p for p, v in ports.items() if not v.get("open") and not v.get("refused")]
    tport = [p for p in ports if p in set(int(x) for x in tunnel_ports or ())]
    t = tunnel or {}

    def f(level, fid, title, why, fix, cmd=None):
        # دستور جدا از متن: لاتین وسطِ جمله‌ی فارسی به‌هم می‌ریخت و قابلِ کپی نبود
        out.append({"level": level, "id": fid, "title": title, "why": why, "fix": fix,
                    **({"cmd": cmd} if cmd else {})})

    # «TCP بسته است» فقط روی پورتی که باید باز باشد. فایروالِ سرورِ ایران
    # (ufw با deny پیش‌فرض) پورت‌های بسته را بی‌صدا دور می‌ریزد؛ بی‌جوابیِ
    # ۲۲ و ۴۴۳ به‌تنهایی چیزی نمی‌گوید — مخصوصاً وقتی تانل از ایران به ما
    # زنگ می‌زند و هیچ پورتی آن‌جا لازم نیست باز باشد.
    must = tport or []
    if t.get("synrecv") and not t.get("conns"):
        f("bad", "handshake-reverse", "SYN سرورِ ایران می‌رسد ولی دست‌دادن کامل نمی‌شود",
          f"{t['synrecv']} اتصال از سرورِ ایران در حالِ SYN-RECV مانده‌اند: درخواستش به این‌جا می‌رسد، "
          "ولی جوابِ ما (SYN-ACK) به او نمی‌رسد یا تأییدش برنمی‌گردد. TCP در یک جهت بسته است — "
          "حتی اگر پینگ برود.",
          "آی‌پیِ یکی از دو سرور را عوض کنید. اگر UDP باز است، تانلی روی UDP راهِ موقتی است.")
        return out
    if ports and not answered and not ping_ok:
        f("bad", "host-down", "نه پینگ، نه TCP — آی‌پی از این سمت در دسترس نیست",
          "هیچ بسته‌ای به این آی‌پی نمی‌رسد؛ یا سرور خاموش است یا کلِ آی‌پی بسته شده.",
          "سرور را از کنسولِ دیتاسنتر چک کنید؛ اگر روشن است، آی‌پی را عوض کنید.")
        return out
    if must and all(p in silent for p in must) and not answered:
        if ping_ok:
            f("bad", "tcp-blocked", "پینگ رد می‌شود ولی TCP نه — TCP به این آی‌پی بسته است",
              f"پینگ می‌رسد، ولی پورتِ تانل ({'، '.join(str(p) for p in must)}) و هیچ پورتِ دیگری حتی جوابِ "
              "«رد» هم نداد؛ بسته‌های TCP بینِ راه دور ریخته می‌شوند. این الگوی فیلترِ آی‌پی است: "
              "ICMP آزاد، TCP بسته.",
              "آی‌پیِ یکی از دو سرور را عوض کنید (معمولاً آی‌پیِ تازه برای سرورِ خارج ساده‌تر است). اگر "
              "UDP باز است، تانلی روی UDP (hysteria، wireguard، یا ترانسپورتِ udp backhaul) هم راهِ موقتی است.")
        return out

    fast = [p for p, v in ports.items()
            if v.get("refused") and v.get("rst_ms") is not None and rtt and rtt > 20
            and v["rst_ms"] < rtt * 0.5]
    if fast:
        v = ports[fast[0]]
        f("bad", "rst-injected", "اتصال را وسطِ راه با RST جعلی می‌بندند",
          f"جوابِ «رد» روی پورتِ {fast[0]} در {round(v['rst_ms'])} میلی‌ثانیه رسید، ولی رفت‌وبرگشتِ پینگ "
          f"{round(rtt)} میلی‌ثانیه است — پس از خودِ سرور نیامده. یک دستگاهِ میانی (DPI) اتصال را قطع می‌کند.",
          "ترانسپورتِ تانل را رمزدار و شبیه‌سازی‌شده کنید (مثلاً wss یا wssmux با TLS روی پورتِ 443)، "
          "یا پورتِ تانل را عوض کنید.")

    if must and answered and any(p in silent for p in must):
        f("bad", "tunnel-port-filtered", "پورتِ تانل بینِ راه بسته است",
          "آی‌پی به TCP جواب می‌دهد (" + "، ".join(str(p) for p in answered) + ") ولی پورتِ تانل ("
          + "، ".join(str(p) for p in must if p in silent) + ") هیچ جوابی نمی‌دهد — فیلترِ پورت، یا "
          "فایروالِ سرورِ ایران این پورت را بسته.",
          "اول فایروالِ سرورِ ایران (ufw status) را ببینید؛ اگر باز است، پورتِ تانل را روی یکی از "
          "پورت‌های جواب‌دار بگذارید.")
    elif silent and answered and len(answered) < len(ports):
        f("tip", "port-filter", "بعضی پورت‌ها بی‌جواب‌اند",
          "بی‌جواب: " + "، ".join(str(p) for p in silent) + " — جواب‌دار: "
          + "، ".join(str(p) for p in answered) + ". آی‌پی باز است ولی این پورت‌ها بینِ راه فیلتر می‌شوند.",
          "پورتِ تانل را روی یکی از پورت‌های جواب‌دار بگذارید.")
    for p in tport:
        v = ports[p]
        if v.get("refused") and not v.get("open") and p not in fast:
            f("bad", "tunnel-port-closed", f"پورتِ تانل ({p}) باز است ولی کسی گوش نمی‌دهد",
              "سرورِ ایران جواب می‌دهد، ولی روی پورتِ تانل «رد» می‌گوید — سرویسِ تانل آن‌جا بالا نیست "
              "یا روی پورتِ دیگری گوش می‌دهد.",
              "سرویسِ تانل را روی سرورِ ایران ری‌استارت کنید و پورتِ bind را با پورتِ این سمت مقایسه کنید.")

    mtu = (check.get("mtu") or {}).get("max")
    if mtu and mtu < 1400:
        f("bad" if mtu < 1300 else "warn", "mtu",
          f"بسته‌های بزرگ رد نمی‌شوند — MTU مسیر {mtu} بایت است",
          f"پینگِ کوچک می‌رسد ولی بسته‌ی بزرگ‌تر از {mtu} بایت (بی‌تکه) گم می‌شود. TCP دست می‌دهد "
          "(بسته‌های دست‌دادن کوچک‌اند) ولی وقتِ فرستادنِ داده گیر می‌کند.",
          f"روی هر دو سرور MSS را محدود کنید (دستورِ زیر)، یا MTU تانل را {mtu} بگذارید.",
          cmd=f"iptables -t mangle -A POSTROUTING -p tcp --tcp-flags SYN,RST SYN "
              f"-j TCPMSS --set-mss {mtu - 40}")

    if t.get("syn") and not t.get("conns"):
        f("bad", "handshake-stuck", "اتصالِ تانل در دست‌دادن گیر کرده",
          f"{t['syn']} اتصال در حالِ SYN-SENT اند و هیچ‌کدام برقرار نمی‌شود — SYN می‌رود و جوابی برنمی‌گردد.",
          "همان راه‌حلِ «TCP بسته است»: آی‌پی یا پورتِ تانل را عوض کنید.")
    if t.get("stuck"):
        f("warn", "data-stuck", "داده روی اتصالِ تانل گیر کرده",
          f"{t['stuck']} اتصال صفِ ارسالِ پر دارند و کرنل دارد دوباره می‌فرستد (backoff) — داده می‌رود ولی "
          "تأیید برنمی‌گردد. معمولاً MTU یا DPI است.",
          "MSS را محدود کنید (بالا)، یا ترانسپورتِ تانل را عوض کنید.")
    return out


# ═══════════════════════════════════════════════════════════
#  سلامتِ خودِ اتصال‌های تانل — از کرنل، نه سنجشِ مصنوعی
# ═══════════════════════════════════════════════════════════

#: موتورهای تانل. منبع netid.TUNNEL_PROCS است؛ روی ایجنت netid ممکن است
#: نباشد، پس نسخه‌ی پشتیبان این‌جاست و test-linkcheck برابری‌شان را می‌سنجد.
_TUNNEL_PROCS_FALLBACK = (
    "backhaul", "backpack", "chisel", "rathole", "gost", "frpc", "frps",
    "wireguard", "wg-quick", "wstunnel", "hysteria", "tuic", "udp2raw",
    "iodine", "socat", "haproxy", "stunnel", "openvpn",
)
try:
    from netid import TUNNEL_PROCS
except Exception:
    TUNNEL_PROCS = _TUNNEL_PROCS_FALLBACK


def _ss(args, timeout=8):
    try:
        p = subprocess.run(["ss"] + args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout if p.returncode == 0 else None


def _split_addr(a):
    host, _, port = a.rpartition(":")
    host = host.strip("[]")
    if host.startswith("::ffff:"):
        host = host[7:]
    return host, int(port) if port.isdigit() else None


def parse_ss_info(text):
    """
    خروجیِ `ss -tinpH state established`: هر اتصال یک خط، و خطِ تورفته‌ی
    بعدی جزئیاتِ TCP کرنل (rtt، ارسالِ دوباره، بایت‌ها).
    """
    conns = []
    for line in (text or "").splitlines():
        if not line.strip():
            continue
        if line[:1] in (" ", "\t") and conns:
            c = conns[-1]
            for m in re.finditer(r"(\w+):([\d./]+)", line):
                k, v = m.group(1), m.group(2)
                try:
                    if k == "rtt":
                        c["rtt"] = float(v.split("/")[0])
                    elif k == "minrtt":
                        c["minrtt"] = float(v)
                    elif k == "retrans":
                        c["retrans"] = int(v.split("/")[-1])
                    elif k in ("segs_out", "bytes_sent", "bytes_received", "bytes_acked",
                               "lastrcv", "lastsnd", "lastack", "backoff", "unacked", "lost"):
                        c[k] = int(float(v))
                except ValueError:
                    continue
            continue
        f = line.split()
        if len(f) < 4:
            continue
        lh, lp = _split_addr(f[2])
        ph, pp = _split_addr(f[3])
        m = re.search(r'users:\(\("([^"]+)"', line)
        try:
            sendq = int(f[1])
        except ValueError:
            sendq = 0
        conns.append({"local": lh, "lport": lp, "peer": ph, "pport": pp, "sendq": sendq,
                      "proc": m.group(1).lower() if m else ""})
    return conns


def _is_local(ip):
    return (not ip or ip.startswith(("127.", "10.", "192.168.", "169.254."))
            or ip in ("::1", "0.0.0.0", "*")
            or (ip.startswith("172.") and ip.split(".")[1].isdigit()
                and 16 <= int(ip.split(".")[1]) <= 31))


def syn_sent(peers=None, text=None, state="syn-sent"):
    """
    {آی‌پی: تعداد} اتصال‌هایی که در دست‌دادن مانده‌اند.
    syn-sent: ما SYN فرستادیم و جوابی نیامد. syn-recv: SYN او رسید و
    دست‌دادن کامل نشد — TCP در جهتِ برگشت بسته است.
    """
    if text is None:
        text = _ss(["-tnpH", "state", state])
        if text is None:
            return {}
    want = set(peers or [])
    out = {}
    for line in text.splitlines():
        f = line.split()
        if len(f) < 4:
            continue
        ip, _p = _split_addr(f[3])
        eng = any(e in line.lower() for e in TUNNEL_PROCS)
        if ip and not _is_local(ip) and (eng or ip in want):
            out[ip] = out.get(ip, 0) + 1
    return out


def tunnel_conns(peers=None, conns=None, listening=None, syn=None):
    """
    اتصال‌های تانلِ این سرور، به تفکیکِ آی‌پیِ طرفِ مقابل.

    اتصالِ تانل = پردازه‌اش یکی از موتورهای تانل است، یا طرفِ مقابلش در
    `peers` (آی‌پی‌هایی که پنل تانل می‌داند — `ss` بی‌دسترسیِ root نامِ
    پردازه را نمی‌دهد).

    برای هر آی‌پی: تعدادِ اتصال، RTTِ کرنل (میانه)، درصدِ ارسالِ دوباره
    (نشانه‌ی پرتِ واقعی روی همان مسیرِ تانل)، بایت‌ها، و جهت: «in» یعنی
    طرفِ مقابل به ما زنگ زده، «out» یعنی ما به پورتِ شنونده‌ی او — که
    همان پورت برای سنجش از این سمت برگردانده می‌شود.
    """
    if conns is None:
        text = _ss(["-tinpH", "state", "established"], timeout=10)
        if text is None:
            return {"ok": False, "peers": {}}
        conns = parse_ss_info(text)
    if listening is None:
        text = _ss(["-tlnH"]) or ""
        listening = set()
        for line in text.splitlines():
            f = line.split()
            if len(f) >= 4:
                _h, lp = _split_addr(f[3])
                if lp:
                    listening.add(lp)
    want = set(peers or [])
    out = {}
    for c in conns:
        ip = c["peer"]
        if _is_local(ip):
            continue
        eng = next((e for e in TUNNEL_PROCS if e in c["proc"]), None) if c["proc"] else None
        if not eng and ip not in want:
            continue
        g = out.setdefault(ip, {"engine": eng, "conns": 0, "in": 0, "out": 0,
                                "listen": [], "rtts": [], "minrtt": None,
                                "retrans": 0, "segs": 0, "sent": 0, "recv": 0,
                                "idle": None, "stuck": 0})
        g["engine"] = g["engine"] or eng
        g["conns"] += 1
        if c.get("lport") in listening:
            g["in"] += 1
        else:
            g["out"] += 1
            if c.get("pport") and c["pport"] not in g["listen"]:
                g["listen"].append(c["pport"])
        if c.get("rtt") is not None:
            g["rtts"].append(c["rtt"])
        if c.get("minrtt") is not None:
            g["minrtt"] = c["minrtt"] if g["minrtt"] is None else min(g["minrtt"], c["minrtt"])
        g["retrans"] += c.get("retrans", 0)
        # داده در صفِ ارسال و کرنل در حالِ عقب‌نشینی: رفته ولی تأیید نیامده
        if c.get("sendq", 0) > 0 and c.get("backoff", 0) > 0:
            g["stuck"] += 1
        g["segs"] += c.get("segs_out", 0)
        g["sent"] += c.get("bytes_sent", 0)
        g["recv"] += c.get("bytes_received", 0)
        last = min(c.get("lastrcv", 10 ** 9), c.get("lastsnd", 10 ** 9))
        g["idle"] = last if g["idle"] is None else min(g["idle"], last)
    for ip, g in out.items():
        r = sorted(g.pop("rtts"))
        g["rtt"] = round(r[len(r) // 2], 1) if r else None
        g["retransPct"] = round(g["retrans"] * 100 / g["segs"], 2) if g["segs"] else 0.0
        g["listen"] = g["listen"][:4]
    for ip in want:
        # تانلی که پنل می‌شناسد ولی هیچ اتصالی ندارد — خودش خبر است
        out.setdefault(ip, {"engine": None, "conns": 0, "in": 0, "out": 0, "listen": [],
                            "minrtt": None, "retrans": 0, "segs": 0, "sent": 0,
                            "recv": 0, "idle": None, "rtt": None, "retransPct": 0.0,
                            "stuck": 0})
    try:
        syn = syn_sent(peers=want) if syn is None else syn
    except Exception:
        syn = {}
    try:
        synr = syn_sent(peers=want, state="syn-recv")
    except Exception:
        synr = {}
    blank = {"engine": None, "conns": 0, "in": 0, "out": 0, "listen": [], "minrtt": None,
             "retrans": 0, "segs": 0, "sent": 0, "recv": 0, "idle": None, "rtt": None,
             "retransPct": 0.0, "stuck": 0}
    for key, src in (("syn", syn), ("synrecv", synr)):
        for ip, n in src.items():
            out.setdefault(ip, dict(blank))[key] = n
    return {"ok": True, "peers": out}


def tunnel_state(t):
    """وضعیتِ اتصالِ تانل به یک آی‌پی: ok | slow | lossy | down | unknown."""
    if not t:
        return "unknown"
    if not t.get("conns"):
        return "down"          # شاملِ دست‌دادنِ گیرکرده (syn/synrecv بی اتصالِ برقرار)
    if (t.get("retransPct") or 0) >= LOSSY / 3:
        return "lossy"
    if t.get("rtt") is not None and t["rtt"] > SLOW_MS["between"]:
        return "slow"
    return "ok"


# ═══════════════════════════════════════════════════════════
#  یک دورِ کامل — همان تابعی که ایجنت و پنل صدا می‌زنند
# ═══════════════════════════════════════════════════════════

#: وقتی پورتِ شنونده‌ی طرفِ ایران را نمی‌دانیم (تانلی که او به ما زنگ
#: می‌زند)، این‌ها امتحان می‌شوند و بهترینش می‌ماند
PROBE_FALLBACK_PORTS = (22, 443, 80)


def _best_per_host(results):
    """برای هر آی‌پی بهترین پورت: پورتِ بسته «قطع» نیست."""
    best = {}
    for r in results:
        m = _metric(r)
        cur = best.get(r["host"])
        if cur is None or (m and m["loss"] < (_metric(cur) or {"loss": 101})["loss"]):
            best[r["host"]] = r
    return list(best.values())


def run(side="iran", bridge_ports=None, iran_hosts=None, peers=None, **_):
    """
    side="iran":    از سرورِ ایران — داخل، بین‌الملل، و سرورِ خارج
    side="foreign": از سرورِ خارج — ایران، و بین‌الملل

    `iran_hosts`: [{host, port?}] — بی‌پورت یعنی تانلی که ایران به ما زنگ
    می‌زند؛ آن‌وقت پینگ و چند پورتِ رایج، بهترینش.
    `peers`: آی‌پی‌هایی که تانل‌اند، برای سلامتِ اتصال‌ها وقتی `ss` نامِ
    پردازه را نمی‌دهد.

    `**_` تا ایجنت هر پارامترِ اضافه‌ای (panelVersion، …) را بی‌خطا رد کند.
    """
    t0 = time.time()
    out = {"side": side, "at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "counters": net_counters()}

    if side == "iran":
        found = peer_ips(bridge_ports)
        if not found:
            # تانلِ دستی: پنل پورتش را نمی‌داند؛ پردازه‌ی تانل خودش می‌گوید
            # به کدام آی‌پی وصل است
            try:
                found = [ip for ip, g in (tunnel_conns(peers=peers).get("peers") or {}).items()
                         if g.get("conns")][:3]
            except Exception:
                found = []
        peers_found = found
        groups = {
            "domestic": [{"host": h, "port": p} for h, p in DOMESTIC],
            "intl": [{"host": h, "port": p} for h, p in INTL],
            "foreign": [{"host": ip, "port": port, "icmp": port == FOREIGN_PORTS[0]}
                        for ip in peers_found for port in FOREIGN_PORTS],
        }
        out["peers"] = peers_found
    else:
        hosts = [h for h in iran_hosts or [] if h.get("host")][:12]
        iran_t = []
        for h in hosts:
            if h.get("port"):
                iran_t.append({"host": h["host"], "port": int(h["port"])})
            else:
                iran_t += [{"host": h["host"], "port": pt, "icmp": pt == PROBE_FALLBACK_PORTS[0]}
                           for pt in PROBE_FALLBACK_PORTS]
        groups = {"iran": iran_t, "intl": [{"host": h, "port": p} for h, p in INTL]}

    flat = [(g, t) for g, ts in groups.items() for t in ts]
    results = probe_all([t for _g, t in flat])
    paths = {g: [] for g in groups}
    for (g, _t), r in zip(flat, results):
        paths[g].append(r)

    # سرورِ مقابل لازم نیست همه‌ی پورت‌های امتحانی را باز داشته باشد
    if side == "iran" and paths.get("foreign"):
        paths["foreign"] = _best_per_host(paths["foreign"])
    if side != "iran" and paths.get("iran"):
        paths["iran"] = _best_per_host(paths["iran"])

    out["paths"] = paths
    # آزمونِ TCP برای هر آی‌پیِ طرفِ مقابل — «پینگ می‌رود ولی TCP نه»
    tcp_hosts = {}
    if side == "iran":
        for ip in out.get("peers") or []:
            tcp_hosts[ip] = []
    else:
        for h in iran_hosts or []:
            if h.get("host"):
                tcp_hosts.setdefault(h["host"], [])
                if h.get("port"):
                    tcp_hosts[h["host"]].append(int(h["port"]))
    if tcp_hosts:
        with ThreadPoolExecutor(max_workers=min(4, len(tcp_hosts))) as ex:
            res = ex.map(lambda kv: tcp_check(kv[0], kv[1], tries=2), list(tcp_hosts.items())[:6])
            out["tcp"] = {c["host"]: c for c in res}
    try:
        out["tunnel"] = tunnel_conns(peers=peers)
    except Exception as e:          # سلامتِ اتصال‌ها تزئینِ حکم است، نه شرطِ آن
        out["tunnel"] = {"ok": False, "peers": {}, "error": f"{type(e).__name__}: {e}"[:160]}
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


def _tunnel_phrase(t):
    if not t:
        return ""
    if not t.get("conns"):
        return " هیچ اتصالِ تانلی به این آی‌پی برقرار نیست."
    bits = [f"{t['conns']} اتصالِ تانل"]
    if t.get("rtt") is not None:
        bits.append(f"RTTِ کرنل {round(t['rtt'])} ms")
    if t.get("retransPct"):
        bits.append(f"{t['retransPct']}٪ ارسالِ دوباره")
    return " روی خودِ تانل: " + "، ".join(bits) + "."


def diagnose(iran, foreign, tunnel=None, tcp=None, tunnel_ports=()):
    """
    یک حکم به زبانِ ساده: اختلال از کدام سمت است و چه باید کرد.

    ترتیبِ بررسی مهم است: اگر خودِ سرورِ ایران به داخل هم نمی‌رسد، بقیه‌ی
    مسیرها طبیعتاً بدند و گفتنِ «آی‌پیِ خارج محدود شده» گمراه‌کننده است.

    `tunnel`: سلامتِ اتصال‌های تانل به همین سرورِ ایران (`tunnel_conns`)،
    دیده‌شده از سمتِ خارج. داده‌ی ناقص حکم را «نامشخص» نمی‌کند: تانلِ دستیِ
    بی‌ایجنت هرگز سمتِ ایران ندارد، و «هنوز داده نیست»ِ همیشگی بی‌فایده بود.
    """
    s = path_states(iran, foreign)
    s["tunnel"] = tunnel_state(tunnel)
    tf = tcp_findings(tcp, tunnel, tunnel_ports) if tcp else []
    iran_known = s["iran_intl"] != "unknown" or s["iran_domestic"] != "unknown"
    between = _worst(s["iran_foreign"], s["foreign_iran"], s["tunnel"])
    tp = _tunnel_phrase(tunnel)

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
    # «پینگ می‌رود ولی TCP نه» مشخص‌ترین حکم است — وقتی سرورِ خارج خودش سالم است
    bad_tcp = next((x for x in tf if x["level"] == "bad"), None)
    if bad_tcp and s["foreign_intl"] not in _BAD:
        return {"side": "tcp", "level": "bad", "title": bad_tcp["title"], "id": bad_tcp["id"],
                "reason": bad_tcp["why"] + tp, "fix": bad_tcp["fix"], "paths": s, "tcp": tf}
    if s["foreign_intl"] in _BAD + _WARN:
        return verdict(
            "foreign", s["foreign_intl"],
            "مشکل از سرورِ خارج است",
            f"سرورِ خارج به اینترنتِ بین‌المللی {_STATE_FA[s['foreign_intl']]} وصل می‌شود.",
            "وضعیتِ دیتاسنترِ خارج و مصرفِ همان سرور را ببینید.")
    if s["tunnel"] == "down" and tunnel is not None:
        return verdict(
            "tunnel", "down",
            "تانل وصل نیست",
            "هیچ اتصالی بینِ این سرور و سرورِ ایران برقرار نیست — ترافیکی رد نمی‌شود."
            + ("" if s["foreign_iran"] in _BAD else " خودِ مسیر جواب می‌دهد، پس مشکل از سرویسِ تانل است."),
            "سرویسِ تانل را روی هر دو سرور ری‌استارت کنید و لاگش را ببینید؛ "
            "پورت و توکنِ دو طرف یکی باشد.")
    if between in _BAD + _WARN:
        if iran_known:
            return verdict(
                "between", between,
                "مسیرِ بینِ این دو سرور مشکل دارد",
                "هر دو سرور به اینترنت سالم وصل‌اند، ولی بینِ خودشان "
                f"{_STATE_FA[between]}. معمولاً یعنی آی‌پیِ یکی از دو سرور محدود شده." + tp,
                "آی‌پیِ سرورِ خارج (یا ایران) را عوض کنید، یا دیتاسنترِ دیگری امتحان کنید.")
        return verdict(
            "between-or-iran", between,
            "مشکل بینِ این سرور و سرورِ ایران است — یا خودِ سرورِ ایران",
            f"سرورِ خارج به اینترنت سالم وصل است، ولی تا سرورِ ایران {_STATE_FA[between]}." + tp,
            "برای جداکردنِ «مسیر» از «سرورِ ایران»، ایجنت را روی سرورِ ایران نصب کنید "
            "(تانل ← سرورها). تا آن موقع: ترنسپورتِ تانل یا آی‌پیِ یکی از دو سرور را عوض کنید.")

    missing = [k for k in _PATH_FA if s[k] == "unknown"]
    if len(missing) == len(_PATH_FA) and s["tunnel"] == "unknown":
        return {"side": "unknown", "level": "unknown", "paths": s,
                "title": "هنوز سنجشی نرسیده",
                "reason": "هیچ مسیری سنجیده نشده.",
                "fix": "«همین حالا بسنج» را بزنید؛ اگر ایجنت قدیمی است به‌روزش کنید."}
    if missing:
        return {"side": "partial", "level": "ok", "paths": s,
                "title": "آنچه سنجیده می‌شود سالم است",
                "reason": "سنجیده نشده: " + "، ".join(_PATH_FA[k] for k in missing) + "." + tp,
                "fix": ("اگر مشتری‌ها هنوز کندی دارند، ایجنت را روی سرورِ ایران نصب کنید تا "
                        "سمتِ ایران هم دیده شود؛ و «اینباندها» را ببینید.")}
    return {"side": "none", "level": "ok", "paths": s,
            "title": "همه‌ی مسیرها سالم‌اند",
            "reason": "اگر مشتری‌ها هنوز کندی دارند، مشکل از خودِ تانل یا اینباند است، نه شبکه." + tp,
            "fix": "«تانل ← اینباندها» را ببینید، یا ترنسپورتِ تانل را عوض کنید."}
