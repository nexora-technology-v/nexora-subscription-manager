#!/usr/bin/env python3
"""
عکس‌برداری پیش از به‌روزرسانی و پیش از بازگردانی.

چرا وجود دارد:
    nexora-cli دو جا از وضعیت فعلی نسخه می‌گرفت — یکی پیش از update،
    یکی پیش از rollback — و هر کدام فهرست جدای خودش را داشت.

    فهرستِ rollback هشت مورد کم داشت، از جمله bot.db.

    یعنی اگر بعد از rollback به «بازگردانی تنظیمات» جواب بله می‌دادید،
    دیتابیس زنده‌ی ربات با نسخه‌ی قدیمی بازنویسی می‌شد و نسخه‌ی زنده
    هیچ‌جا ذخیره نشده بود. هر کاربر، سفارش، اشتراک و موجودی کیف پولی
    که از آخرین به‌روزرسانی به بعد ساخته شده بود، بی‌بازگشت.

    این تست تابع را واقعاً *اجرا* می‌کند روی یک نصبِ ساختگی، نه اینکه
    فقط متن اسکریپت را بخواند.

اجرا:  python3 tools/test-snapshot.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
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


CLI = (ROOT / "nexora-cli.sh").read_text(encoding="utf-8")


def _bash():
    """
    مفسر bash واقعی.

    روی ویندوز، «bash» در PATH معمولاً به WSL می‌رسد که توزیعی نصب
    ندارد و با پیام خودش شکست می‌خورد. Git Bash همان‌جاست و درست کار
    می‌کند. روی لینوکس — یعنی CI — همان bash معمولی.
    """
    for c in ("C:/Program Files/Git/bin/bash.exe",
              "C:/Program Files/Git/usr/bin/bash.exe"):
        if os.path.exists(c):
            return c
    return shutil.which("bash") or "bash"


BASH = _bash()

# ═══════════════════════════════════════════════════════════
head("یک تابع، نه دو فهرست")

check("تابع مشترک تعریف شده", "snapshot_to() {" in CLI)
calls = len(re.findall(r"^\s*snapshot_to\s+\"\$", CLI, re.M))
check("هر دو مسیر از همان استفاده می‌کنند", calls == 2,
      f"{calls} صدازدن — update و rollback")
check("هیچ فهرست دستیِ دومی نمانده",
      '"$PRE/"' not in CLI.replace('snapshot_to "$PRE"', ""),
      "وگرنه دوباره از هم فاصله می‌گیرند")

# ═══════════════════════════════════════════════════════════
head("اجرای واقعی روی یک نصب ساختگی")

TMP = Path(tempfile.mkdtemp())
INST = TMP / "nexora"
(INST / "data").mkdir(parents=True)
(INST / "backend" / "venv").mkdir(parents=True)
(INST / "backend" / "__pycache__").mkdir(parents=True)
(INST / "bot" / "__pycache__").mkdir(parents=True)
(INST / "frontend" / "src" / "sections").mkdir(parents=True)

FILES = {
    "data/config.json": '{"brand":"nexora"}',
    "data/auth.json": '{"password":"x"}',
    "data/bot.db": "BOT-DATA",
    "data/billing.db": "BILL-DATA",
    "data/tunnels.db": "TUN-DATA",
    "sub-page-index.html": "<html></html>",
    "VERSION": "1.2.3",
    ".github": "GITHUB_REPO=x/y",
    "nexora-cli.sh": "#!/bin/bash",
    "backend/app.py": "print(1)",
    "backend/requirements.txt": "fastapi",
    "backend/venv/pyvenv.cfg": "junk",
    "backend/__pycache__/app.pyc": "junk",
    "bot/handlers.py": "print(2)",
    "bot/__pycache__/x.pyc": "junk",
    "frontend/package.json": '{"name":"p"}',
    "frontend/.env": "VITE_API_URL=http://x",
    "frontend/src/App.jsx": "export default 1",
    "frontend/src/sections/billing.jsx": "export const a = 1",
}
for rel, body in FILES.items():
    (INST / rel).write_text(body, encoding="utf-8")

SNAP = TMP / "snap"
harness = TMP / "run.sh"
# فقط همان تابع را بیرون می‌کشیم و اجرا می‌کنیم — بقیه‌ی اسکریپت
# منتظر آرگومان و systemd است
body = CLI[CLI.index("snapshot_to() {"):]
body = body[:body.index("\n}\n") + 3]
harness.write_text(
    'set -e\nINSTALL_DIR="%s"\nVER="1.2.3"\n%s\nsnapshot_to "%s"\n'
    % (INST.as_posix(), body, SNAP.as_posix()), encoding="utf-8")

r = subprocess.run([BASH, str(harness)], capture_output=True, text=True)
check("تابع بدون خطا اجرا می‌شود", r.returncode == 0,
      (r.stderr or "")[:100])

MUST = ["config.json", "auth.json", "bot.db", "billing.db", "tunnels.db",
        "sub-page-index.html", "VERSION", ".github", "nexora-cli.sh",
        "FROM_VERSION", "backend/app.py", "backend/requirements.txt",
        "bot/handlers.py", "frontend/package.json", "frontend/.env",
        "frontend/src/App.jsx", "frontend/src/sections/billing.jsx"]

missing = [f for f in MUST if not (SNAP / f).exists()]
check("هر چیزی که لازم است در نسخه هست", not missing,
      "جامانده: " + "، ".join(missing) if missing else f"{len(MUST)} مورد")

check("دیتابیس ربات واقعاً کپی شده — نه فقط فایل خالی",
      (SNAP / "bot.db").exists()
      and (SNAP / "bot.db").read_text(encoding="utf-8") == "BOT-DATA",
      "همان چیزی که rollback می‌تواند بازنویسی‌اش کند")
check("نسخه‌ی مبدا نوشته شده",
      (SNAP / "FROM_VERSION").read_text(encoding="utf-8").strip() == "1.2.3")

head("زباله‌ها کپی نمی‌شوند")

check("venv کپی نمی‌شود", not (SNAP / "backend" / "venv").exists(),
      "صدها مگابایت بی‌فایده در هر نسخه")
check("__pycache__ بک‌اند کپی نمی‌شود",
      not (SNAP / "backend" / "__pycache__").exists())
check("__pycache__ ربات هم نه",
      not (SNAP / "bot" / "__pycache__").exists(),
      "فایل pyc قدیمی بعد از بازگردانی کد تازه را سایه می‌اندازد")

head("نصب ناقص، اسکریپت را نمی‌شکند")

INST2 = TMP / "minimal"
(INST2 / "data").mkdir(parents=True)
(INST2 / "backend").mkdir(parents=True)
(INST2 / "backend" / "app.py").write_text("x", encoding="utf-8")
SNAP2 = TMP / "snap2"
h2 = TMP / "run2.sh"
h2.write_text('INSTALL_DIR="%s"\nVER="9.9.9"\n%s\nsnapshot_to "%s"\n'
              % (INST2.as_posix(), body, SNAP2.as_posix()), encoding="utf-8")
r2 = subprocess.run([BASH, str(h2)], capture_output=True, text=True)
check("نصبِ بدون ربات و بدون دیتابیس هم کار می‌کند", r2.returncode == 0,
      (r2.stderr or "")[:100])
check("و آن‌چه هست را برمی‌دارد", (SNAP2 / "backend" / "app.py").exists())
check("برای آن‌چه نیست فایل خالی نمی‌سازد",
      not (SNAP2 / "bot.db").exists(),
      "فایل صفر بایت بدتر از نبودن است — موقع بازگردانی داده را پاک می‌کند")

shutil.rmtree(TMP, ignore_errors=True)

print(f"\n{D}{'─' * 50}{X}")
color = G if not _fail else R
print(f"  {color}{_ok} پاس{X}" + (f" · {R}{_fail} ناموفق{X}" if _fail else ""))
print()
sys.exit(1 if _fail else 0)
