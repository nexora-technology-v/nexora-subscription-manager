"""
مدیریت تانل — دیتابیس و منطق.

معماری: پنل روی سرور خارج است و سرور ایران فقط یک agent سبک دارد
که به پنل وصل می‌شود، نه برعکس. یعنی سرور ایران هیچ پورتی باز
نمی‌کند و رمزی جایی ذخیره نمی‌شود.

هر نود یک توکن یکتا دارد. اگر توکنی لو رفت، فقط همان نود را باطل
می‌کنیم — بقیه دست‌نخورده می‌مانند.
"""

import json
import os
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

# ═══════════════════════════════════════════════════════════
#  موتورهای تانل
#
#  هر کدام فایل پیکربندی و روش اجرای خودش را دارد. اینجا فقط
#  توصیفشان است؛ ساخت کانفیگ در _build_config.
# ═══════════════════════════════════════════════════════════

ENGINES = {
    "backhaul": {
        "name": "Backhaul",
        "desc": "سریع و پایدار برای شرایط ایران — پیشنهاد اول",
        "repo": "Musixal/Backhaul",
        "binary": "backhaul",
        "config": "toml",
        "transports": ["tcp", "tcpmux", "ws", "wss", "wsmux", "wssmux",
                       "utcpmux", "uwsmux"],
        "default_transport": "tcpmux",
        "recommended": True,
    },
    "rathole": {
        "name": "Rathole",
        "desc": "سبک و کم‌مصرف، نوشته‌شده با Rust",
        "repo": "rapiz1/rathole",
        "binary": "rathole",
        "config": "toml",
        "transports": ["tcp", "tls", "noise", "websocket"],
        "default_transport": "tcp",
        "recommended": False,
    },
    "gost": {
        "name": "GOST",
        "desc": "انعطاف‌پذیر با پروتکل‌های متنوع",
        "repo": "go-gost/gost",
        "binary": "gost",
        "config": "yaml",
        "transports": ["tcp", "ws", "wss", "mws", "mwss", "grpc", "quic"],
        "default_transport": "mws",
        "recommended": False,
    },
    "frp": {
        "name": "FRP",
        "desc": "پرکاربرد و باثبات، با پنل وضعیت داخلی",
        "repo": "fatedier/frp",
        "binary": "frps",
        "config": "toml",
        "transports": ["tcp", "kcp", "quic", "websocket"],
        "default_transport": "tcp",
        "recommended": False,
    },
    "chisel": {
        "name": "Chisel",
        "desc": "روی HTTP سوار می‌شود — وقتی بقیه بسته می‌شوند جواب می‌دهد",
        "repo": "jpillora/chisel",
        "binary": "chisel",
        # Chisel فایل پیکربندی ندارد و با آرگومان خط فرمان کار می‌کند
        "config": "args",
        "transports": ["http", "https"],
        "default_transport": "http",
        "recommended": True,
    },
}

def _db_path():
    """
    مسیر دیتابیس تانل.

    هر بار خوانده می‌شود، نه یک‌بار هنگام import — چون ترتیب
    بارگذاری ماژول‌ها زیر uvicorn تضمینی نیست و اگر متغیر محیطی
    آن لحظه هنوز تنظیم نشده باشد، مسیر اشتباه برای همیشه می‌ماند
    و نوشتن‌ها بی‌صدا به فایل دیگری می‌روند.
    """
    return Path(os.getenv("TUNNEL_DB_PATH", "/opt/nexora-panel/data/tunnels.db"))


# برای سازگاری با کدی که مستقیم به این نام اشاره می‌کند
TUNNEL_DB = _db_path()


def conn():
    """اتصال به دیتابیس تانل. جداول در اولین تماس ساخته می‌شوند."""
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=10)
    con.row_factory = sqlite3.Row
    con.executescript("""
        -- سرورهایی که agent رویشان نصب است
        CREATE TABLE IF NOT EXISTS nodes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            token        TEXT NOT NULL UNIQUE,
            role         TEXT NOT NULL DEFAULT 'iran',   -- iran | foreign
            public_ip    TEXT,
            note         TEXT,
            last_seen    TEXT,
            agent_version TEXT,
            os_info      TEXT,
            cpu_percent  REAL,
            mem_percent  REAL,
            disk_percent REAL,
            uptime_sec   INTEGER,
    health       TEXT,
    health_at    TEXT,
            enabled      INTEGER DEFAULT 1,
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- تعریف هر تانل
        CREATE TABLE IF NOT EXISTS tunnels (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            engine       TEXT NOT NULL DEFAULT 'backhaul',
            transport    TEXT NOT NULL DEFAULT 'tcpmux',
            node_id      INTEGER NOT NULL,       -- سرور ایران
    foreign_node INTEGER,                -- سرور خارج، اگر agent دارد
            remote_host  TEXT NOT NULL,          -- آدرسی که طرف مقابل به آن وصل می‌شود
            bridge_port  INTEGER NOT NULL,       -- پورت ارتباط دو سرور
            ports        TEXT NOT NULL DEFAULT '[]',
            secret       TEXT NOT NULL,
            options      TEXT DEFAULT '{}',
            enabled      INTEGER DEFAULT 1,
            status       TEXT DEFAULT 'pending',
            last_error   TEXT,
            last_check   TEXT,
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at   TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
        );

        -- کارهایی که agent باید انجام دهد
        CREATE TABLE IF NOT EXISTS jobs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id    INTEGER NOT NULL,
            action     TEXT NOT NULL,
            payload    TEXT DEFAULT '{}',
            status     TEXT DEFAULT 'queued',    -- queued | taken | done | failed
            result     TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            taken_at   TEXT,
            done_at    TEXT
        );

        -- تاریخچه، برای دیدن اینکه چه اتفاقی افتاده
        CREATE TABLE IF NOT EXISTS events (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id    INTEGER,
            tunnel_id  INTEGER,
            level      TEXT DEFAULT 'info',      -- info | warn | error
            message    TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- تاریخچه‌ی سنجش، برای دیدن روند نه فقط لحظه
        CREATE TABLE IF NOT EXISTS metrics (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            tunnel_id  INTEGER NOT NULL,
            tcp_avg    REAL,
            tcp_min    REAL,
            tcp_max    REAL,
            jitter     REAL,
            loss       REAL,
            icmp_avg   REAL,
            http_avg   REAL,
            raw        TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_met_tun ON metrics(tunnel_id, id DESC);
        CREATE INDEX IF NOT EXISTS idx_jobs_node ON jobs(node_id, status);
        CREATE INDEX IF NOT EXISTS idx_tun_node ON tunnels(node_id);
        CREATE INDEX IF NOT EXISTS idx_ev_time  ON events(created_at DESC);
    """)
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(tunnels)")}
        if "foreign_node" not in cols:
            con.execute("ALTER TABLE tunnels ADD COLUMN foreign_node INTEGER")
        ncols = {r[1] for r in con.execute("PRAGMA table_info(nodes)")}
        for col in ("health", "health_at"):
            if col not in ncols:
                con.execute(f"ALTER TABLE nodes ADD COLUMN {col} TEXT")
    except Exception:
        pass

    con.commit()
    return con


def now():
    return datetime.now().isoformat(timespec="seconds")


def log(node_id=None, tunnel_id=None, level="info", message=""):
    """ثبت رویداد. خطای ثبت نباید کار اصلی را متوقف کند."""
    try:
        c = conn()
        c.execute(
            "INSERT INTO events (node_id, tunnel_id, level, message) VALUES (?,?,?,?)",
            (node_id, tunnel_id, level, message[:500]))
        # فقط ۵۰۰ رویداد آخر را نگه می‌داریم
        c.execute("""DELETE FROM events WHERE id NOT IN
                     (SELECT id FROM events ORDER BY id DESC LIMIT 500)""")
        c.commit()
        c.close()
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
#  نودها
# ═══════════════════════════════════════════════════════════

def new_token():
    """توکن نود — طولانی و تصادفی، چون تنها چیزی است که agent را می‌شناساند."""
    return "nxa_" + secrets.token_urlsafe(32)


def create_node(name, role="iran", note=""):
    c = conn()
    try:
        token = new_token()
        cur = c.execute(
            "INSERT INTO nodes (name, token, role, note) VALUES (?,?,?,?)",
            (name.strip()[:60], token, role, (note or "").strip()[:200]))
        c.commit()
        log(node_id=cur.lastrowid, message=f"نود «{name}» ساخته شد")
        return {"id": cur.lastrowid, "token": token}
    finally:
        c.close()


def list_nodes():
    """نودها با شمار تانل و وضعیت زنده بودن."""
    c = conn()
    try:
        rows = c.execute("""
            SELECT n.*,
                   (SELECT COUNT(*) FROM tunnels t WHERE t.node_id = n.id) AS tunnel_count,
                   (SELECT COUNT(*) FROM tunnels t
                     WHERE t.node_id = n.id AND t.status = 'running') AS running_count
            FROM nodes n ORDER BY n.id
        """).fetchall()

        out = []
        for r in rows:
            d = dict(r)
            d["token"] = d["token"][:12] + "…"   # هرگز کامل نمایش داده نمی‌شود
            d["online"] = _is_online(d.get("last_seen"))
            out.append(d)
        return out
    finally:
        c.close()


def _is_online(last_seen, window=90):
    """
    نود زنده است اگر در ۹۰ ثانیه‌ی اخیر خبر داده باشد.

    agent هر ۳۰ ثانیه ping می‌زند، پس سه بار فرصت دارد قبل از
    اینکه آفلاین اعلام شود — تا یک قطعی لحظه‌ای هشدار کاذب ندهد.
    """
    if not last_seen:
        return False
    try:
        delta = (datetime.now() - datetime.fromisoformat(last_seen)).total_seconds()
        return delta < window
    except Exception:
        return False


def node_by_token(token):
    c = conn()
    try:
        r = c.execute("SELECT * FROM nodes WHERE token = ? AND enabled = 1",
                      (token,)).fetchone()
        return dict(r) if r else None
    finally:
        c.close()


def touch_node(node_id, metrics=None):
    """agent خبر داده که زنده است، همراه با وضعیت سرور."""
    m = metrics or {}
    c = conn()
    try:
        c.execute("""UPDATE nodes SET last_seen = ?, agent_version = ?, os_info = ?,
                     cpu_percent = ?, mem_percent = ?, disk_percent = ?, uptime_sec = ?,
                     public_ip = COALESCE(?, public_ip)
                     WHERE id = ?""",
                  (now(), m.get("version"), m.get("os"),
                   m.get("cpu"), m.get("mem"), m.get("disk"), m.get("uptime"),
                   m.get("ip"), node_id))
        c.commit()
    finally:
        c.close()


def delete_node(node_id):
    c = conn()
    try:
        c.execute("DELETE FROM tunnels WHERE node_id = ?", (node_id,))
        c.execute("DELETE FROM jobs WHERE node_id = ?", (node_id,))
        c.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        c.commit()
    finally:
        c.close()


def rotate_token(node_id):
    """توکن جدید — اگر قبلی لو رفته باشد."""
    c = conn()
    try:
        token = new_token()
        c.execute("UPDATE nodes SET token = ? WHERE id = ?", (token, node_id))
        c.commit()
        log(node_id=node_id, level="warn", message="توکن نود عوض شد")
        return token
    finally:
        c.close()


# ═══════════════════════════════════════════════════════════
#  تانل‌ها
# ═══════════════════════════════════════════════════════════

def validate_ports(ports):
    """
    بررسی فهرست پورت‌ها.

    هر ردیف: {"local": 443, "remote": 443} یا فقط عدد که یعنی
    هر دو طرف یکی باشند.
    """
    out = []
    for p in (ports or []):
        try:
            if isinstance(p, (int, str)):
                n = int(p)
                item = {"local": n, "remote": n}
            else:
                item = {"local": int(p.get("local")),
                        "remote": int(p.get("remote") or p.get("local"))}
        except (TypeError, ValueError):
            continue

        if not (1 <= item["local"] <= 65535 and 1 <= item["remote"] <= 65535):
            continue
        # پورت‌های سیستمی حساس را رد می‌کنیم تا کسی سهواً SSH را نبندد
        if item["local"] in (22,):
            continue
        out.append(item)
    return out


def create_tunnel(data):
    name = (data.get("name") or "").strip()[:60]
    if not name:
        raise ValueError("نام تانل لازم است")

    engine = data.get("engine") or "backhaul"
    if engine not in ENGINES:
        raise ValueError(f"موتور ناشناخته: {engine}")

    transport = data.get("transport") or ENGINES[engine]["default_transport"]
    if transport not in ENGINES[engine]["transports"]:
        raise ValueError(f"{ENGINES[engine]['name']} از {transport} پشتیبانی نمی‌کند")

    try:
        node_id = int(data.get("node_id"))
    except (TypeError, ValueError):
        raise ValueError("نود مشخص نشده است")

    remote = (data.get("remote_host") or "").strip()
    if not remote:
        raise ValueError("آدرس سرور خارج لازم است")

    try:
        bridge = int(data.get("bridge_port") or 3080)
    except (TypeError, ValueError):
        raise ValueError("پورت ارتباط نامعتبر است")
    if not (1024 <= bridge <= 65535):
        raise ValueError("پورت ارتباط باید بین ۱۰۲۴ تا ۶۵۵۳۵ باشد")

    ports = validate_ports(data.get("ports"))
    if not ports:
        raise ValueError("حداقل یک پورت معتبر لازم است")

    secret = (data.get("secret") or "").strip() or secrets.token_urlsafe(24)

    c = conn()
    try:
        try:
            foreign_node = int(data.get("foreign_node") or 0) or None
        except (TypeError, ValueError):
            foreign_node = None

        cur = c.execute("""INSERT INTO tunnels
            (name, engine, transport, node_id, foreign_node, remote_host,
             bridge_port, ports, secret, options)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (name, engine, transport, node_id, foreign_node, remote, bridge,
             json.dumps(ports), secret,
             json.dumps(data.get("options") or {}, ensure_ascii=False)))
        c.commit()
        tid = cur.lastrowid
        log(node_id=node_id, tunnel_id=tid,
            message=f"تانل «{name}» با {ENGINES[engine]['name']} ساخته شد")
        return tid
    finally:
        c.close()


def list_tunnels(node_id=None):
    c = conn()
    try:
        sql = """SELECT t.*, n.name AS node_name, n.last_seen AS node_seen,
                        n.public_ip AS node_ip
                 FROM tunnels t LEFT JOIN nodes n ON n.id = t.node_id"""
        params = ()
        if node_id:
            sql += " WHERE t.node_id = ?"
            params = (node_id,)
        sql += " ORDER BY t.id DESC"

        out = []
        for r in c.execute(sql, params):
            d = dict(r)
            try:
                d["ports"] = json.loads(d.get("ports") or "[]")
            except (json.JSONDecodeError, TypeError):
                d["ports"] = []
            try:
                d["options"] = json.loads(d.get("options") or "{}")
            except (json.JSONDecodeError, TypeError):
                d["options"] = {}
            d["secret"] = "••••••"        # در فهرست نمایش داده نمی‌شود
            d["engineName"] = ENGINES.get(d["engine"], {}).get("name", d["engine"])
            d["nodeOnline"] = _is_online(d.get("node_seen"))
            out.append(d)
        return out
    finally:
        c.close()


def get_tunnel(tid, with_secret=False):
    c = conn()
    try:
        r = c.execute("SELECT * FROM tunnels WHERE id = ?", (tid,)).fetchone()
        if not r:
            return None
        d = dict(r)
        try:
            d["ports"] = json.loads(d.get("ports") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["ports"] = []
        try:
            d["options"] = json.loads(d.get("options") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["options"] = {}
        if not with_secret:
            d["secret"] = "••••••"
        return d
    finally:
        c.close()


def update_tunnel(tid, data):
    cur = get_tunnel(tid, with_secret=True)
    if not cur:
        raise ValueError("تانل پیدا نشد")

    fields, params = [], []
    for key, col in (("name", "name"), ("remote_host", "remote_host"),
                     ("transport", "transport")):
        if key in data:
            fields.append(f"{col} = ?")
            params.append(str(data[key]).strip()[:120])

    if "bridge_port" in data:
        fields.append("bridge_port = ?")
        params.append(int(data["bridge_port"]))

    if "ports" in data:
        ports = validate_ports(data["ports"])
        if not ports:
            raise ValueError("حداقل یک پورت معتبر لازم است")
        fields.append("ports = ?")
        params.append(json.dumps(ports))

    if "enabled" in data:
        fields.append("enabled = ?")
        params.append(1 if data["enabled"] else 0)

    if "options" in data:
        fields.append("options = ?")
        params.append(json.dumps(data["options"] or {}, ensure_ascii=False))

    if not fields:
        return False

    fields.append("updated_at = ?")
    params.append(now())
    params.append(tid)

    c = conn()
    try:
        c.execute(f"UPDATE tunnels SET {', '.join(fields)} WHERE id = ?", params)
        c.commit()
        return True
    finally:
        c.close()


def delete_tunnel(tid):
    t = get_tunnel(tid)
    c = conn()
    try:
        c.execute("DELETE FROM tunnels WHERE id = ?", (tid,))
        c.commit()
    finally:
        c.close()
    if t:
        log(node_id=t["node_id"], message=f"تانل «{t['name']}» حذف شد")


def set_status(tid, status, error=None):
    c = conn()
    try:
        c.execute("""UPDATE tunnels SET status = ?, last_error = ?, last_check = ?
                     WHERE id = ?""", (status, error, now(), tid))
        c.commit()
    finally:
        c.close()


# ═══════════════════════════════════════════════════════════
#  ساخت پیکربندی موتورها
#
#  هر موتور فرمت خودش را دارد. اینجا از روی تعریف تانل، فایل
#  پیکربندی سمت ایران (client) و سمت خارج (server) ساخته می‌شود.
# ═══════════════════════════════════════════════════════════

def build_config(tunnel, side):
    """
    پیکربندی یک طرف تانل.

    side: "iran" (کلاینت، به سرور خارج وصل می‌شود) یا
          "foreign" (سرور، منتظر اتصال می‌ماند)
    """
    engine = tunnel["engine"]
    builder = {
        "backhaul": _cfg_backhaul,
        "rathole": _cfg_rathole,
        "gost": _cfg_gost,
        "frp": _cfg_frp,
        "chisel": _cfg_chisel,
    }.get(engine)

    if not builder:
        raise ValueError(f"موتور {engine} پشتیبانی نمی‌شود")
    return builder(tunnel, side)


def _cfg_backhaul(t, side):
    """
    Backhaul با فرمت TOML.

    جهت ترافیک در این سناریو:

        مشتری ──► سرور ایران ──[تانل]──► سرور خارج (3x-ui)

    پس سرور ایران باید پورت‌ها را باز کند و ترافیک را به خارج
    بفرستد. در Backhaul، طرفی که پورت باز می‌کند [server] است و
    طرفی که سرویس واقعی دارد [client]. یعنی برعکس چیزی که از نام
    «ایران/خارج» به ذهن می‌رسد:

        سرور ایران   → [server]  پورت باز می‌کند، منتظر مشتری
        سرور خارج    → [client]  به ایران وصل می‌شود، سرویس دارد

    اشتباه گرفتن این دو یعنی تانل بالا می‌آید ولی هیچ ترافیکی رد
    نمی‌شود.
    """
    opt = t.get("options") or {}
    common = [
        f'token = "{t["secret"]}"',
        f'transport = "{t["transport"]}"',
        f'keepalive_period = {opt.get("keepalive", 75)}',
        f'nodelay = {"true" if opt.get("nodelay", True) else "false"}',
        f'log_level = "{opt.get("log_level", "info")}"',
    ]

    if side == "iran":
        # پورت‌ها اینجا باز می‌شوند چون مشتری به همین سرور وصل می‌شود
        lines = ["[server]", f'bind_addr = ":{t["bridge_port"]}"'] + common
        if opt.get("heartbeat"):
            lines.append(f'heartbeat = {int(opt["heartbeat"])}')
        if t["transport"].endswith("mux"):
            lines.append(f'mux_con = {opt.get("mux_con", 8)}')
        lines.append("")
        lines.append("ports = [")
        for p in t["ports"]:
            # "پورتی که باز می‌شود=پورتی که در سمت خارج هست"
            lines.append(f'    "{p["local"]}={p["remote"]}",')
        lines.append("]")
        return "\n".join(lines) + "\n"

    # سمت خارج به ایران وصل می‌شود و سرویس واقعی را دارد
    lines = ["[client]",
             f'remote_addr = "{t["remote_host"]}:{t["bridge_port"]}"'] + common
    if opt.get("retry_interval"):
        lines.append(f'retry_interval = {int(opt["retry_interval"])}')
    if t["transport"].endswith("mux"):
        lines.append(f'mux_version = {opt.get("mux_version", 1)}')
    return "\n".join(lines) + "\n"


def _cfg_rathole(t, side):
    """
    Rathole — همان جهت Backhaul.

    سرور ایران [server] است و پورت‌ها را باز می‌کند؛ سرور خارج
    [client] است و سرویس واقعی را دارد.
    """
    if side == "iran":
        lines = ["[server]",
                 f'bind_addr = "0.0.0.0:{t["bridge_port"]}"',
                 f'default_token = "{t["secret"]}"', ""]
        for p in t["ports"]:
            lines += [f'[server.services.p{p["remote"]}]',
                      f'bind_addr = "0.0.0.0:{p["remote"]}"', ""]
        return "\n".join(lines)

    lines = ["[client]",
             f'remote_addr = "{t["remote_host"]}:{t["bridge_port"]}"',
             f'default_token = "{t["secret"]}"', ""]
    for p in t["ports"]:
        lines += [f'[client.services.p{p["remote"]}]',
                  f'local_addr = "127.0.0.1:{p["local"]}"', ""]
    return "\n".join(lines)


def _cfg_gost(t, side):
    """
    GOST با YAML.

    سرور ایران هم relay را می‌پذیرد و هم پورت‌ها را باز می‌کند،
    پس هر دو بخش در یک فایل می‌آید.
    """
    tr = t["transport"]
    if side == "iran":
        svc = [f"""  - name: bridge
    addr: ":{t['bridge_port']}"
    handler:
      type: relay
      auth:
        username: nexora
        password: {t['secret']}
    listener:
      type: {tr}"""]
        return "services:\n" + "\n".join(svc) + "\n"

    svc = []
    for i, p in enumerate(t["ports"]):
        svc.append(f"""  - name: fwd{i}
    addr: ":{p['local']}"
    handler:
      type: tcp
      chain: c0
    listener:
      type: tcp""")
    chain = f"""chains:
  - name: c0
    hops:
      - name: h0
        nodes:
          - name: n0
            addr: {t['remote_host']}:{t['bridge_port']}
            connector:
              type: relay
              auth:
                username: nexora
                password: {t['secret']}
            dialer:
              type: {tr}"""
    return "services:\n" + "\n".join(svc) + "\n" + chain + "\n"


def _cfg_chisel(t, side):
    """
    Chisel — با آرگومان خط فرمان، نه فایل پیکربندی.

    خروجی این تابع رشته‌ی آرگومان‌هاست که agent مستقیم به باینری
    می‌دهد. چون ترافیک داخل HTTP معمولی می‌رود، جایی که بقیه‌ی
    پروتکل‌ها فیلتر می‌شوند این معمولاً باز می‌ماند.

    جهت مثل بقیه: سرور ایران --server است و پورت باز می‌کند،
    سرور خارج --client و سرویس واقعی را دارد.
    """
    opt = t.get("options") or {}
    auth = f"nexora:{t['secret']}"

    if side == "iran":
        args = ["server",
                f"--port {t['bridge_port']}",
                f"--auth {auth}",
                "--reverse"]
        if opt.get("keepalive"):
            args.append(f"--keepalive {int(opt['keepalive'])}s")
        else:
            args.append("--keepalive 25s")
        if t["transport"] == "https" and opt.get("tls_domain"):
            args.append(f"--tls-domain {opt['tls_domain']}")
        return " ".join(args)

    scheme = "https" if t["transport"] == "https" else "http"
    args = ["client",
            f"--auth {auth}",
            "--keepalive 25s",
            f"--max-retry-interval 30s",
            f"{scheme}://{t['remote_host']}:{t['bridge_port']}"]
    # R: یعنی تانل معکوس — پورت روی سمت server باز می‌شود
    for p in t["ports"]:
        args.append(f"R:0.0.0.0:{p['local']}:127.0.0.1:{p['remote']}")
    return " ".join(args)


def _cfg_frp(t, side):
    """
    FRP با TOML.

    سرور ایران frps است (پورت باز می‌کند)، سرور خارج frpc.
    """
    if side == "iran":
        return (f'bindPort = {t["bridge_port"]}\n'
                f'auth.method = "token"\n'
                f'auth.token = "{t["secret"]}"\n')

    lines = [f'serverAddr = "{t["remote_host"]}"',
             f'serverPort = {t["bridge_port"]}',
             'auth.method = "token"',
             f'auth.token = "{t["secret"]}"', ""]
    for p in t["ports"]:
        lines += ["[[proxies]]",
                  f'name = "p{p["remote"]}"',
                  'type = "tcp"',
                  'localIP = "127.0.0.1"',
                  f'localPort = {p["local"]}',
                  f'remotePort = {p["remote"]}', ""]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
#  صف کارها
#
#  agent فقط این دستورهای مشخص را می‌شناسد. هر چیز دیگری رد
#  می‌شود — پس حتی اگر پنل هک شود، نمی‌شود کد دلخواه روی سرور
#  ایران اجرا کرد.
# ═══════════════════════════════════════════════════════════

ALLOWED_ACTIONS = {
    "install",      # نصب باینری موتور
    "apply",        # نوشتن کانفیگ و راه‌اندازی سرویس
    "start",
    "stop",
    "restart",
    "remove",       # حذف سرویس و کانفیگ
    "status",       # گزارش وضعیت
    "logs",         # آخرین خطوط لاگ
    "ping",         # تست شبکه به سرور خارج
    "monitor",      # سنجش کیفیت تانل
    "health",       # بررسی سلامت سیستم
    "sysmon",       # مانیتورینگ کامل سرور: CPU، رم، دیسک، پورت، اتصال
    "firewall",     # خواندن وضعیت فایروال آن سرور
    "update_agent",
}


def queue_job(node_id, action, payload=None):
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"دستور مجاز نیست: {action}")

    c = conn()
    try:
        cur = c.execute(
            "INSERT INTO jobs (node_id, action, payload) VALUES (?,?,?)",
            (node_id, action, json.dumps(payload or {}, ensure_ascii=False)))
        c.commit()
        return cur.lastrowid
    finally:
        c.close()


def take_jobs(node_id, limit=5):
    """کارهای در انتظار را به agent می‌دهد و علامت می‌زند."""
    c = conn()
    try:
        rows = c.execute(
            """SELECT * FROM jobs WHERE node_id = ? AND status = 'queued'
               ORDER BY id LIMIT ?""", (node_id, limit)).fetchall()
        out = []
        for r in rows:
            c.execute("UPDATE jobs SET status = 'taken', taken_at = ? WHERE id = ?",
                      (now(), r["id"]))
            d = dict(r)
            try:
                d["payload"] = json.loads(d.get("payload") or "{}")
            except (json.JSONDecodeError, TypeError):
                d["payload"] = {}
            out.append(d)
        c.commit()
        return out
    finally:
        c.close()


def finish_job(job_id, ok, result=""):
    c = conn()
    try:
        c.execute("""UPDATE jobs SET status = ?, result = ?, done_at = ?
                     WHERE id = ?""",
                  ("done" if ok else "failed", str(result)[:2000], now(), job_id))
        c.commit()
    finally:
        c.close()


def save_metrics(tunnel_id, data):
    """
    ثبت یک سنجش.

    فقط ۱۰۰ نمونه‌ی آخر هر تانل نگه داشته می‌شود — بیشتر از این
    برای دیدن روند لازم نیست و دیتابیس را بی‌دلیل بزرگ می‌کند.
    """
    tcp = {}
    for v in (data.get("tcp") or {}).values():
        if v.get("ok"):
            tcp = v
            break

    icmp = data.get("icmp") or {}
    http = data.get("http") or {}

    c = conn()
    try:
        c.execute("""INSERT INTO metrics
                     (tunnel_id, tcp_avg, tcp_min, tcp_max, jitter, loss,
                      icmp_avg, http_avg, raw)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (tunnel_id, tcp.get("avg"), tcp.get("min"), tcp.get("max"),
                   tcp.get("jitter"), tcp.get("loss"),
                   icmp.get("avg"), http.get("avg"),
                   json.dumps(data, ensure_ascii=False)[:4000]))
        c.execute("""DELETE FROM metrics WHERE tunnel_id = ? AND id NOT IN
                     (SELECT id FROM metrics WHERE tunnel_id = ?
                      ORDER BY id DESC LIMIT 100)""", (tunnel_id, tunnel_id))
        c.commit()
    finally:
        c.close()


def get_metrics(tunnel_id, limit=40):
    """آخرین سنجش‌ها به‌همراه خلاصه‌ی روند."""
    c = conn()
    try:
        rows = [dict(r) for r in c.execute(
            """SELECT * FROM metrics WHERE tunnel_id = ?
               ORDER BY id DESC LIMIT ?""", (tunnel_id, limit))]
    finally:
        c.close()

    if not rows:
        return {"samples": [], "summary": None}

    latest = rows[0]
    try:
        latest["detail"] = json.loads(latest.get("raw") or "{}")
    except (json.JSONDecodeError, TypeError):
        latest["detail"] = {}

    vals = [r["tcp_avg"] for r in rows if r["tcp_avg"] is not None]
    losses = [r["loss"] for r in rows if r["loss"] is not None]

    summary = {
        "count": len(rows),
        "latest": latest.get("tcp_avg"),
        "best": min(vals) if vals else None,
        "worst": max(vals) if vals else None,
        "average": round(sum(vals) / len(vals), 1) if vals else None,
        "lossAvg": round(sum(losses) / len(losses), 1) if losses else None,
        "since": rows[-1].get("created_at"),
    }

    # کیفیت — همان چیزی که کاربر می‌خواهد بداند
    a = summary["average"]
    l = summary["lossAvg"] or 0
    if a is None:
        summary["quality"] = "نامشخص"
    elif l > 5 or a > 300:
        summary["quality"] = "ضعیف"
    elif l > 1 or a > 150:
        summary["quality"] = "متوسط"
    elif a > 60:
        summary["quality"] = "خوب"
    else:
        summary["quality"] = "عالی"

    return {"samples": list(reversed(rows)), "summary": summary,
            "latest": latest}


def save_health(node_id, data):
    """ثبت آخرین گزارش سلامت یک نود."""
    c = conn()
    try:
        c.execute("UPDATE nodes SET health = ?, health_at = ? WHERE id = ?",
                  (json.dumps(data, ensure_ascii=False)[:8000], now(), node_id))
        c.commit()
    finally:
        c.close()


def save_sysmon(node_id, data):
    """
    ثبت آخرین مانیتورینگ کامل یک سرور.

    ستون را در صورت نبود می‌سازیم تا نصب‌های قدیمی هم بدون مهاجرت
    دستی کار کنند — این ماژول روی سرورهایی اجرا می‌شود که کسی
    قرار نیست دستی به دیتابیسشان دست بزند.
    """
    c = conn()
    try:
        cols = {r[1] for r in c.execute("PRAGMA table_info(nodes)")}
        if "sysmon" not in cols:
            c.execute("ALTER TABLE nodes ADD COLUMN sysmon TEXT")
        if "sysmon_at" not in cols:
            c.execute("ALTER TABLE nodes ADD COLUMN sysmon_at TEXT")
        c.execute("UPDATE nodes SET sysmon = ?, sysmon_at = ? WHERE id = ?",
                  (json.dumps(data, ensure_ascii=False)[:60000], now(), node_id))
        c.commit()
    finally:
        c.close()


def get_sysmon(node_id):
    """آخرین مانیتورینگ ثبت‌شده‌ی یک سرور، یا None."""
    c = conn()
    try:
        cols = {r[1] for r in c.execute("PRAGMA table_info(nodes)")}
        if "sysmon" not in cols:
            return None
        r = c.execute("SELECT sysmon, sysmon_at FROM nodes WHERE id = ?",
                      (node_id,)).fetchone()
        if not r or not r["sysmon"]:
            return None
        try:
            return {"data": json.loads(r["sysmon"]), "at": r["sysmon_at"]}
        except (json.JSONDecodeError, TypeError):
            return None
    finally:
        c.close()


def recent_events(limit=60):
    c = conn()
    try:
        rows = c.execute("""
            SELECT e.*, n.name AS node_name, t.name AS tunnel_name
            FROM events e
            LEFT JOIN nodes n ON n.id = e.node_id
            LEFT JOIN tunnels t ON t.id = e.tunnel_id
            ORDER BY e.id DESC LIMIT ?""", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        c.close()
