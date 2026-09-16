#!/usr/bin/env python3
"""
بررسی هماهنگی فرانت‌اند و بک‌اند.

ناهماهنگی نام آدرس یا نام فیلد بی‌صدا شکست می‌خورد — نه خطایی،
نه لاگی، فقط یک صفحه‌ی خالی یا دکمه‌ای که کار نمی‌کند. پس قبل از
هر انتشار این اجرا شود:

    python3 tools/check-api-contract.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
backend = (ROOT / "backend" / "app.py").read_text(encoding="utf-8")

# ALL of frontend/src, not just App.jsx.
#
# This checker read App.jsx alone. When the panel was split into
# sections/, the API calls went with them — so it was auditing 2 URLs
# while the real frontend called dozens, and every one of those was
# unchecked. A gate that passes because it is looking at an empty room
# is worse than no gate: it is a green light nobody earned.
SRC = ROOT / "frontend" / "src"
_files = sorted(p for p in SRC.rglob("*")
                if p.suffix in (".jsx", ".js") and p.is_file())
frontend = "\n".join(p.read_text(encoding="utf-8") for p in _files)

G = "\033[38;5;42m"
R = "\033[38;5;203m"
D = "\033[38;5;245m"
X = "\033[0m"

problems = 0

# ═══════════════════════════════════════════════
#  ۱. هر آدرسی که فرانت‌اند صدا می‌زند، مسیر دارد؟
# ═══════════════════════════════════════════════

routes = set()
for m in re.finditer(r'@app\.(\w+)\("(/api[^"]+)"', backend):
    routes.add(re.sub(r"\{[^}]+\}", "*", m.group(2)))

called = set()
# Two shapes, because the panel uses both:
#
#   fetch(`${API_URL}/api/admin/stats`)      ← literal template
#   useJson("/api/admin/billing/ledger")     ← path handed to a helper
#
# Only the first was matched. Every section that went through call() or
# useJson() — firewall rules, the ledger, the whole reseller portal and
# the mini app — was invisible to this check. Those are most of them.
#
# Interpolations collapse to * first: `${encodeURIComponent(slug)}` has a
# paren in it, so cutting the path at the first odd character left the
# fragment `/api/portal/${encodeURIComponent` and reported a route that
# does not exist. A checker that cries wolf gets switched off.
# `${API_URL}` itself survives: it is the prefix the first pattern keys on.
_flat = re.sub(r"\$\{(?!API_URL\})[^{}]*\}", "*", frontend)
for pat in (r"\$\{API_URL\}(/api/[^`\"']*)",
            r"[\"'`](/api/[a-zA-Z0-9_\-/*.]*)"):
    for m in re.finditer(pat, _flat):
        p = m.group(1).split("?")[0].rstrip("/")
        if p and p != "/api":
            called.add(p)

print(f"\n{D}Checking {len(called)} URLs against {len(routes)} routes{X}\n")

# A floor, so this cannot quietly go blind again.
#
# For years it read App.jsx only and audited 2 URLs while the panel
# called dozens — and it reported "API contract is sound" every time.
# If a refactor moves the calls somewhere this scanner cannot see, that
# has to be a failure, not a green tick on an empty room.
_FLOOR = 90
if len(called) < _FLOOR:
    print(f"  {R}✗{X} only {len(called)} URLs found, expected at least {_FLOOR}")
    print(f"      {D}the scanner has stopped seeing the frontend's calls —{X}")
    print(f"      {D}fix the extractor before trusting this result{X}\n")
    sys.exit(1)


def matches(path, route):
    if path == route:
        return True
    if route.endswith("*") and path.startswith(route[:-1]):
        return True
    if path.endswith("*") and route.startswith(path[:-1]):
        return True
    return False


missing = [p for p in sorted(called)
           if not any(matches(p, r) for r in routes)]

if missing:
    for p in missing:
        problems += 1
        print(f"  {R}✗{X} URL with no route: {p}")
else:
    print(f"  {G}✓{X} every URL has a route")

# ═══════════════════════════════════════════════
#  ۲. نام فیلدهایی که هر دو طرف باید بشناسند
# ═══════════════════════════════════════════════

print()

CONTRACTS = [
    ("billing_group_put", ["billed", "billable"]),
    ("billing_payment_add", ["group", "group_key"]),
]

for fn, names in CONTRACTS:
    m = re.search(rf"def {fn}\(.*?(?=\n@app\.|\ndef |\Z)", backend, re.S)
    if not m:
        problems += 1
        print(f"  {R}✗{X} function {fn} not found")
        continue
    src = m.group(0)
    unknown = [n for n in names if f'"{n}"' not in src]
    if unknown:
        problems += 1
        print(f"  {R}✗{X} {fn} does not accept: {unknown}")
    else:
        print(f"  {G}✓{X} {fn} accepts both names")

# ═══════════════════════════════════════════════
#  ۳. فیلدهایی که فرانت‌اند از پاسخ می‌خواند
# ═══════════════════════════════════════════════

print()

# نام‌های مترادفی که بک‌اند باید بفرستد
ALIASES = ["name", "billed", "amount", "uncertain", "items", "group_name"]
sent = [a for a in ALIASES if f'"{a}"' in backend]
absent = set(ALIASES) - set(sent)

if absent:
    problems += 1
    print(f"  {R}✗{X} backend does not send these aliases: {sorted(absent)}")
else:
    print(f"  {G}✓{X} all aliases are sent")

# ═══════════════════════════════════════════════
#  ۴. سلامت CSS
#
#  اگر @tailwind حذف شود، کل ظاهر پنل از بین می‌رود
#  ولی build بدون خطا تمام می‌شود — پس باید صریح بررسی شود.
# ═══════════════════════════════════════════════

print()

css_path = ROOT / "frontend" / "src" / "index.css"
if css_path.exists():
    css = css_path.read_text(encoding="utf-8")

    tw = [d for d in ("@tailwind base", "@tailwind components", "@tailwind utilities")
          if d not in css]
    if tw:
        problems += 1
        print(f"  {R}✗{X} Tailwind directives are missing: {tw}")
        print(f"      without them the panel has no styling at all")
    else:
        print(f"  {G}✓{X} Tailwind directives present")

    # قانون فونت عناصر فرم نباید چیز دیگری داشته باشد.
    # یک‌بار خصوصیات body داخلش افتاد و همه‌ی دکمه‌ها پس‌زمینه‌ی
    # صفحه گرفتند — ظاهرشان کاملاً به هم ریخت.
    m = re.search(r'input[^{]*button[^{]*\{([^}]*)\}', css)
    if m:
        body_rule = m.group(1)
        extras = [p.split(":")[0].strip() for p in body_rule.split(";")
                  if p.strip() and "font-family" not in p]
        if extras:
            problems += 1
            print(f"  {R}✗{X} قانون فونت فرم‌ها خصوصیات اضافه دارد: {extras}")
            print(f"      این‌ها ظاهر دکمه‌ها را بازنویسی می‌کنند")
        else:
            print(f"  {G}✓{X} قانون فونت فرم‌ها فقط فونت دارد")

    # body باید رنگ و پس‌زمینه داشته باشد
    if not re.search(r'body\s*\{[^}]*background', css):
        problems += 1
        print(f"  {R}✗{X} body پس‌زمینه ندارد — صفحه بی‌رنگ می‌شود")
    else:
        print(f"  {G}✓{X} body پس‌زمینه دارد")

    # فونت باید هم تعریف و هم اعمال شود
    has_face = "@font-face" in css
    # فونت باید روی body یا html اعمال شده باشد — هر شکلی که نوشته شده
    applied = bool(re.search(r'(html|body|#root)[^{]*\{[^}]*font-family', css))
    if has_face and not applied:
        problems += 1
        print(f"  {R}✗{X} font declared but never applied to body")
    elif has_face:
        print(f"  {G}✓{X} font declared and applied")
else:
    problems += 1
    print(f"  {R}✗{X} index.css not found")

print()
if problems:
    print(f"{R}{problems} mismatches found{X}\n")
    sys.exit(1)

print(f"{G}API contract is sound{X}\n")
