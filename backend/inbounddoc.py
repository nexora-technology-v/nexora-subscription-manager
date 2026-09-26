"""
تحلیلِ اینباندهای 3x-ui: چرا این اینباند کار نمی‌کند یا کند است؟

برگه: docs/specs/2026-09-26-live-tunnel-and-inbound-doctor.md

دو بخش، عمداً جدا:
  · اندازه‌گیری (`probe_reality`، `cert_expiry`، پورت‌های در حالِ گوش‌دادن)
    — کاری که شبکه یا فایل لازم دارد؛
  · قاعده‌ها (`analyze`) — خالص، روی دادهٔ خوانده‌شده و نتیجه‌ی اندازه‌گیری.
    تست همه‌ی قاعده‌ها را با اینباندِ ساختگی می‌سنجد.

هیچ چیزی در x-ui.db نوشته نمی‌شود. پنل پیشنهاد می‌دهد؛ مالک در 3x-ui
اعمال می‌کند — و هر پیشنهاد می‌گوید لینکِ اشتراکِ مشتری‌ها عوض می‌شود یا
نه، چون عوض‌شدنش یعنی همه‌ی مشتری‌ها باید دوباره اشتراک بگیرند.
"""
import json
import socket
import ssl
import time
from concurrent.futures import ThreadPoolExecutor

#: ترانسپورت‌هایی که روی UDP‌اند — از تانلِ TCP رد نمی‌شوند
UDP_NETWORKS = ("kcp", "mkcp", "quic")

#: گواهی زیرِ این چند روز «رو به انقضا» است
CERT_WARN_DAYS = 7


def _j(v):
    if isinstance(v, dict):
        return v
    try:
        x = json.loads(v or "{}")
        return x if isinstance(x, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def stream_of(inb):
    """network و security و تنظیماتِ مرتبط، با نام‌های قدیم و جدید."""
    st = _j(inb.get("stream_settings"))
    net = (st.get("network") or "tcp").lower()
    sec = (st.get("security") or "none").lower()
    rs = st.get("realitySettings") or {}
    ts = st.get("tlsSettings") or {}
    # هر ترانسپورت کلیدِ تنظیماتِ خودش را دارد؛ acceptProxyProtocol در همان است
    per = {}
    for k in ("tcpSettings", "rawSettings", "wsSettings", "httpupgradeSettings",
              "xhttpSettings", "splithttpSettings", "grpcSettings"):
        if isinstance(st.get(k), dict):
            per.update(st[k])
    return {"network": "tcp" if net == "raw" else net, "security": sec,
            "reality": rs, "tls": ts, "per": per, "raw": st}


def reality_target(rs):
    """(host, port) dest — Xray جدید اسمش را target گذاشته."""
    d = str(rs.get("target") or rs.get("dest") or "").strip()
    if not d:
        return None, None
    if d.isdigit():
        return "127.0.0.1", int(d)
    host, _, port = d.rpartition(":")
    if not host:
        return d, 443
    return host.strip("[]"), int(port) if port.isdigit() else 443


# ═══════════════════════════════════════════════════════════
#  اندازه‌گیری
# ═══════════════════════════════════════════════════════════

def probe_reality(host, port, names, timeout=4.0):
    """
    آیا dest Reality از همین سرور، برای هر serverName، TLS 1.3 با گواهیِ
    معتبر می‌دهد؟ Reality دست‌دادن را از dest قرض می‌گیرد؛ dest ِ
    ناسالم یعنی مشتری وصل نمی‌شود — و از بیرون فقط «کار نمی‌کند» دیده می‌شود.
    """
    out = {"host": host, "port": port, "reachable": False, "names": {}}
    t0 = time.perf_counter()
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        out["reachable"] = True
        out["ms"] = round((time.perf_counter() - t0) * 1000, 1)
    except OSError as e:
        out["error"] = f"{type(e).__name__}: {e}"[:120]
        return out
    for name in (names or [host])[:3]:
        ctx = ssl.create_default_context()
        try:
            ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        except (AttributeError, ValueError):
            pass
        try:
            with socket.create_connection((host, port), timeout=timeout) as s:
                with ctx.wrap_socket(s, server_hostname=name) as t:
                    out["names"][name] = {"ok": True, "tls": t.version()}
        except ssl.SSLCertVerificationError as e:
            out["names"][name] = {"ok": False, "why": "cert",
                                  "error": str(getattr(e, "verify_message", e))[:120]}
        except ssl.SSLError as e:
            out["names"][name] = {"ok": False, "why": "tls",
                                  "error": f"{e.reason or e}"[:120]}
        except OSError as e:
            out["names"][name] = {"ok": False, "why": "net",
                                  "error": f"{type(e).__name__}: {e}"[:120]}
    return out


def probe_all_reality(targets, timeout=4.0):
    """{کلید: نتیجه} — هم‌زمان، تا ده اینباند ده برابر طول نکشد."""
    keys = list(targets)
    if not keys:
        return {}
    with ThreadPoolExecutor(max_workers=min(8, len(keys))) as ex:
        res = list(ex.map(lambda k: probe_reality(*targets[k], timeout=timeout), keys))
    return dict(zip(keys, res))


def cert_expiry(path):
    """تاریخِ انقضای گواهیِ یک فایل (ثانیه‌ی یونیکس) یا None."""
    try:
        info = ssl._ssl._test_decode_cert(str(path))       # noqa: SLF001
        return ssl.cert_time_to_seconds(info["notAfter"])
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════
#  قاعده‌ها
# ═══════════════════════════════════════════════════════════

#: سایت‌هایی که معمولاً dest خوبی‌اند (TLS 1.3 و h2) — پیشنهاد، نه قانون
DEST_EXAMPLES = ("www.microsoft.com:443", "www.speedtest.net:443", "www.cloudflare.com:443")


def _dest_examples(current):
    """همان dest ی که خراب است را دوباره پیشنهاد نده."""
    return [d for d in DEST_EXAMPLES if not d.startswith(f"{current}:")][:2]


def _f(level, fid, title, why, fix, sub=False):
    return {"level": level, "id": fid, "title": title, "why": why, "fix": fix, "sub": sub}


def client_state(inb, traffic_rows, now_ms):
    """(کل، فعال) — فعال یعنی روشن، منقضی‌نشده، و سهمیه‌اش باقی."""
    cl = _j(inb.get("settings")).get("clients") or []
    by_email = {r.get("email"): r for r in traffic_rows or []}
    active = 0
    for c in cl:
        if c.get("enable") is False:
            continue
        t = by_email.get(c.get("email")) or {}
        if t and not t.get("enable", 1):
            continue
        exp = int(t.get("expiry_time") if t.get("expiry_time") is not None else c.get("expiryTime") or 0)
        if exp > 0 and exp < now_ms:
            continue
        total = int(t.get("total") if t.get("total") is not None else c.get("totalGB") or 0)
        if total > 0 and int(t.get("up") or 0) + int(t.get("down") or 0) >= total:
            continue
        active += 1
    return len(cl), active


def analyze(inb, env):
    """
    یافته‌های یک اینباند. `env`:
      now_ms, listen_tcp, listen_udp (پورت‌هایی که الان کسی رویشان گوش می‌دهد),
      tunnel_ports (پورت‌هایی که موتورِ تانل گوش می‌دهد), tunnels (تانلی هست؟),
      dup_ports (پورت‌هایی که بیش از یک اینباندِ روشن دارند),
      traffic (ردیف‌های client_traffics همین اینباند),
      reality (نتیجه‌ی probe_reality برای همین اینباند یا None),
      cert_exp {مسیر: ثانیه}
    """
    now_ms = env.get("now_ms") or int(time.time() * 1000)
    s = stream_of(inb)
    proto = (inb.get("protocol") or "").lower()
    port = int(inb.get("port") or 0)
    out = []

    # ── خاموش، منقضی، بی‌سهمیه: Xray اصلاً ترافیکی قبول نمی‌کند ──
    if not inb.get("enable"):
        out.append(_f("bad", "disabled", "این اینباند خاموش است",
                      "Xray روی این پورت گوش نمی‌دهد؛ هیچ ترافیکی — از تانل یا مستقیم — نمی‌رسد.",
                      "در 3x-ui روشنش کنید."))
        return out
    exp = int(inb.get("expiry_time") or 0)
    if exp > 0 and exp < now_ms:
        out.append(_f("bad", "expired", "تاریخِ خودِ اینباند گذشته",
                      "جدا از کلاینت‌ها، خودِ اینباند تاریخِ انقضا دارد و گذشته — 3x-ui آن را از کار می‌اندازد.",
                      "در تنظیماتِ اینباند تاریخِ انقضا را بردارید (نه در کلاینت‌ها)."))
    total = int(inb.get("total") or 0)
    if total > 0 and int(inb.get("up") or 0) + int(inb.get("down") or 0) >= total:
        out.append(_f("bad", "quota", "سهمیه‌ی خودِ اینباند تمام شده",
                      "حجمِ کلِ اینباند پر شده و 3x-ui دیگر ترافیک رد نمی‌کند — برای همه‌ی کلاینت‌هایش.",
                      "حجمِ اینباند را صفر (نامحدود) کنید یا مصرفش را ریست کنید."))

    # ── گوش می‌دهد؟ — اندازه‌گیری، نه خواندنِ تنظیمات ──
    udp = s["network"] in UDP_NETWORKS
    live = env.get("listen_udp" if udp else "listen_tcp")
    if live is not None and port and port not in live:
        out.append(_f("bad", "not-listening", "هیچ‌کس روی این پورت گوش نمی‌دهد",
                      f"اینباند روشن است ولی روی این سرور کسی روی پورتِ {port} "
                      f"({'UDP' if udp else 'TCP'}) منتظر نیست. یعنی Xray پایین است، تنظیمات اعمال "
                      "نشده، یا پورت را برنامه‌ی دیگری گرفته.",
                      "در 3x-ui «ری‌استارتِ Xray» را بزنید و لاگِ Xray را ببینید."))
    if port and port in (env.get("tunnel_ports") or ()):
        out.append(_f("bad", "tunnel-port", "پورتِ اینباند همان پورتِ تانل است",
                      "موتورِ تانل و Xray نمی‌توانند هم‌زمان روی یک پورت گوش بدهند؛ یکی از آن دو کار نمی‌کند.",
                      "پورتِ اینباند یا پورتِ تانل را عوض کنید.", sub=True))
    if port and port in (env.get("dup_ports") or ()):
        out.append(_f("bad", "dup-port", "اینباندِ روشنِ دیگری همین پورت را دارد",
                      "دو اینباند روی یک پورت؛ Xray فقط یکی را بالا می‌آورد.",
                      "پورتِ یکی را عوض کنید.", sub=True))

    # ── کلاینت‌ها ──
    if proto in ("vless", "vmess", "trojan", "shadowsocks"):
        n, act = client_state(inb, env.get("traffic"), now_ms)
        if n and not act:
            out.append(_f("bad", "no-clients", "هیچ کلاینتِ فعالی ندارد",
                          f"هر {n} کلاینت یا خاموش‌اند، یا منقضی، یا حجمشان تمام شده.",
                          "کلاینت‌ها را تمدید یا روشن کنید."))

    # ── Reality ──
    if s["security"] == "reality":
        rs = s["reality"]
        if not rs.get("privateKey"):
            out.append(_f("bad", "reality-key", "کلیدِ خصوصیِ Reality خالی است",
                          "بدونِ privateKey هیچ دست‌دادنی کامل نمی‌شود.",
                          "در 3x-ui «Get New Cert» Reality را بزنید.", sub=True))
        bad_sid = [x for x in rs.get("shortIds") or []
                   if len(str(x)) % 2 or len(str(x)) > 16
                   or any(ch not in "0123456789abcdefABCDEF" for ch in str(x))]
        if bad_sid:
            out.append(_f("bad", "reality-sid", "shortId نامعتبر",
                          "shortId باید هگز با طولِ زوج و حداکثر ۱۶ نویسه باشد؛ Xray با آن بالا نمی‌آید.",
                          "shortIdها را دوباره بسازید.", sub=True))
        pr = env.get("reality")
        host, dport = reality_target(rs)
        if pr is not None:
            if not pr.get("reachable"):
                out.append(_f("bad", "reality-dest", "dest Reality از این سرور در دسترس نیست",
                              f"{host}:{dport} از همین سرور جواب نمی‌دهد ({pr.get('error') or '—'}). "
                              "Reality دست‌دادن را از dest قرض می‌گیرد؛ بدونِ آن مشتری وصل نمی‌شود.",
                              "dest را به سایتی عوض کنید که از این سرور باز است و TLS 1.3 دارد "
                              f"(مثلاً {' یا '.join(_dest_examples(host))}).", sub=True))
            else:
                bad_names = {k: v for k, v in (pr.get("names") or {}).items() if not v.get("ok")}
                for name, v in bad_names.items():
                    why = {"cert": f"گواهیِ {host} برای «{name}» معتبر نیست",
                           "tls": f"{host} با «{name}» TLS 1.3 نمی‌دهد",
                           "net": f"دست‌دادنِ TLS با {host} برای «{name}» قطع شد"}.get(v.get("why"), v.get("error"))
                    out.append(_f("bad", "reality-name", f"serverName «{name}» با dest نمی‌خواند",
                                  f"{why} ({v.get('error') or ''}). مشتری‌ای که با این SNI وصل می‌شود رد می‌شود.",
                                  "serverNames را دقیقاً نام‌هایی بگذارید که روی گواهیِ dest هست، "
                                  "یا dest را عوض کنید.", sub=True))
                if pr.get("ms") and pr["ms"] > 300:
                    out.append(_f("warn", "reality-slow", "dest Reality از این سرور کند است",
                                  f"اتصال به {host} {round(pr['ms'])} میلی‌ثانیه طول کشید. هر دست‌دادنِ "
                                  "مشتری همین را روی تاخیرش دارد.",
                                  "dest ی نزدیک به دیتاسنترِ سرورِ خارج انتخاب کنید.", sub=True))
        if host in ("127.0.0.1", "localhost") and dport == port:
            out.append(_f("bad", "reality-self", "dest به خودِ همین اینباند اشاره می‌کند",
                          "Reality دست‌دادن را به خودش پاس می‌دهد و حلقه می‌شود.",
                          "dest را یک سایتِ بیرونی بگذارید.", sub=True))

    # ── TLS: گواهی ──
    if s["security"] == "tls":
        for c in s["tls"].get("certificates") or []:
            path = c.get("certificateFile")
            if not path:
                continue
            exp_s = (env.get("cert_exp") or {}).get(path)
            if exp_s is None:
                continue
            days = (exp_s - now_ms / 1000) / 86400
            if days < 0:
                out.append(_f("bad", "cert-expired", "گواهیِ TLS منقضی شده",
                              f"گواهیِ {path} تاریخش گذشته؛ کلاینت‌ها دست‌دادن را رد می‌کنند.",
                              "گواهی را تمدید کنید (acme یا certbot) و Xray را ری‌استارت کنید."))
            elif days < CERT_WARN_DAYS:
                out.append(_f("warn", "cert-soon", f"گواهیِ TLS {int(days)} روزِ دیگر منقضی می‌شود",
                              f"گواهیِ {path} نزدیکِ انقضاست.",
                              "پیش از انقضا تمدیدش کنید."))

    # ── flow vision ──
    clients = _j(inb.get("settings")).get("clients") or []
    flows = {str(c.get("flow") or "") for c in clients}
    if proto == "vless" and "xtls-rprx-vision" in flows and s["network"] != "tcp":
        out.append(_f("bad", "vision-transport", "flow vision روی ترانسپورتِ غیر TCP",
                      f"xtls-rprx-vision فقط با TCP خام کار می‌کند؛ روی {s['network']} کلاینت وصل نمی‌شود.",
                      "flow کلاینت‌ها را خالی کنید، یا ترانسپورت را TCP کنید.", sub=True))
    if (proto == "vless" and s["network"] == "tcp" and s["security"] == "reality"
            and clients and "xtls-rprx-vision" not in flows):
        out.append(_f("tip", "vision-missing", "برای VLESS + Reality، flow vision پیشنهاد می‌شود",
                      "vision بسته‌های TLS داخلی را بی‌رمزگذاریِ دوباره رد می‌کند: CPU کمتر، "
                      "و الگوی ترافیک طبیعی‌تر.",
                      "flow کلاینت‌ها را xtls-rprx-vision بگذارید.", sub=True))

    # ── تانل ──
    if udp and env.get("tunnels"):
        out.append(_f("warn", "udp-behind-tunnel", "ترانسپورتِ UDP پشتِ تانل",
                      f"{s['network']} روی UDP است، ولی بیشترِ تانل‌ها (backhaul tcp، rathole، gost، …) "
                      "فقط TCP رد می‌کنند. اگر مشتری از راهِ تانل وصل می‌شود، ترافیکی نمی‌رسد.",
                      "برای مشتری‌های پشتِ تانل از ترانسپورتِ TCP (tcp، ws، httpupgrade، xhttp، grpc) "
                      "استفاده کنید.", sub=True))
    if s["per"].get("acceptProxyProtocol"):
        out.append(_f("warn", "proxy-protocol", "acceptProxyProtocol روشن است",
                      "Xray انتظار دارد هر اتصال با سرآیندِ PROXY شروع شود. اگر تانل یا nginx جلویش آن را "
                      "نفرستد، همه‌ی اتصال‌ها بی‌صدا رد می‌شوند.",
                      "اگر مطمئن نیستید چیزی PROXY protocol می‌فرستد، خاموشش کنید."))
    lst = str(inb.get("listen") or "")
    if lst in ("127.0.0.1", "localhost", "::1"):
        out.append(_f("tip", "loopback", "فقط از روی همین سرور در دسترس است",
                      "اینباند روی 127.0.0.1 گوش می‌دهد. درست است اگر موتورِ تانل روی همین سرور به آن "
                      "وصل می‌شود؛ ولی اگر تانل از سرورِ دیگری مستقیم به این پورت زنگ می‌زند، نمی‌رسد.",
                      "اگر تانلِ ایران مستقیم به این سرور وصل است، listen را خالی بگذارید."))

    # ── پیشنهادها ──
    sn = _j(inb.get("sniffing"))
    if proto in ("vless", "vmess", "trojan", "shadowsocks"):
        if not sn.get("enabled"):
            out.append(_f("tip", "sniffing-off", "sniffing خاموش است",
                          "بی sniffing، قانون‌های مسیریابی بر اساسِ دامنه (بستنِ تبلیغ، سایت‌های ایرانی "
                          "مستقیم، …) روی این اینباند کار نمی‌کنند.",
                          "sniffing را روشن کنید با http، tls و quic، و routeOnly را هم روشن کنید."))
        elif not sn.get("routeOnly"):
            out.append(_f("tip", "sniffing-routeonly", "routeOnly sniffing خاموش است",
                          "بی routeOnly، Xray مقصد را با دامنه‌ی تشخیص‌داده‌شده جایگزین و دوباره resolve "
                          "می‌کند — تاخیرِ بیشتر، و گاهی اتصال به آی‌پیِ اشتباه.",
                          "routeOnly را روشن کنید؛ مسیریابی همچنان از دامنه استفاده می‌کند."))
    if proto == "vmess":
        out.append(_f("tip", "vmess", "VMess به‌جای VLESS",
                      "VLESS سبک‌تر است (رمزگذاری را به TLS/Reality می‌سپارد) و در Xray جدید "
                      "بیشتر پشتیبانی می‌شود.",
                      "اینباندِ تازه‌ای با VLESS بسازید و مشتری‌ها را کم‌کم منتقل کنید.", sub=True))
    return out


LEVEL_ORDER = {"bad": 0, "warn": 1, "tip": 2}


def summary(findings):
    """بدترین سطح: bad | warn | tip | ok"""
    if not findings:
        return "ok"
    return min((f["level"] for f in findings), key=LEVEL_ORDER.get)
