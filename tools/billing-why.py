#!/usr/bin/env python3
"""
چرا این کانفیگ «بدون نرخ» است؟

روی خودِ سرور اجرا می‌شود و سه چیزی را که تصمیم می‌گیرند یک ردیف نرخ
می‌گیرد یا نه، کنار هم می‌گذارد:

  ۱. نرخ‌هایی که برای هر گروه ثبت شده‌اند
  ۲. نام گروه‌ها در x-ui، و اینکه با کلیدهای ثبت‌شده می‌خوانند یا نه
  ۳. حجم واقعی کانفیگ‌های هر گروه، و اینکه با کدام نرخ جور در می‌آید

هیچ رمز، توکن، شماره تلفن یا نام مشتری چاپ نمی‌شود — فقط نام گروه،
حجم، و عدد. خروجی را می‌شود مستقیم فرستاد.

اجرا:  python3 tools/billing-why.py
"""
import glob
import json
import os
import sqlite3
import sys

G, R, Y, D, X = ("\033[38;5;42m", "\033[38;5;203m", "\033[38;5;221m",
                 "\033[38;5;245m", "\033[0m")

BILLING_PATHS = [
    "/opt/nexora/data/billing.db",
    "/root/nexora/data/billing.db",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "data", "billing.db"),
]
XUI_PATHS = ["/etc/x-ui/x-ui.db", "/usr/local/x-ui/x-ui.db",
             "/usr/local/x-ui/bin/x-ui.db", "/etc/x-ui/db/x-ui.db"]


def _find(paths, extra_glob=None):
    for p in paths:
        if os.path.exists(p):
            return p
    if extra_glob:
        hits = glob.glob(extra_glob)
        if hits:
            return hits[0]
    return None


def _open(path):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def _gb_of(total):
    """همان تبدیلی که حسابداری می‌کند."""
    try:
        total = int(total or 0)
    except (TypeError, ValueError):
        return 0
    return total // (1024 ** 3) if total > 1024 else total


def _price_for(gb, rates):
    """کپی ساده‌ی منطق قیمت‌گذاری — تا بشود دقیقاً همان نتیجه را دید."""
    valid = []
    for r in rates or []:
        try:
            valid.append((int(r.get("gb", -1)), int(r.get("price", 0))))
        except (TypeError, ValueError, AttributeError):
            continue
    if not valid:
        return None, "نرخی خوانده نشد"
    for g, price in valid:
        if g == gb:
            return price, None
    if gb > 0:
        higher = sorted((v for v in valid if v[0] > gb), key=lambda v: v[0])
        if higher:
            return higher[0][1], None
        vol = [v for v in valid if v[0] > 0]
        if vol:
            return max(vol, key=lambda v: v[0])[1], None
        return None, "حجمی است، ولی فقط نرخ نامحدود تعریف شده"
    return None, "نامحدود است، ولی نرخ نامحدود تعریف نشده"


def main():
    bpath = _find(BILLING_PATHS, "/opt/*/data/billing.db")
    xpath = _find(XUI_PATHS)

    if not bpath:
        print(f"{R}billing.db پیدا نشد{X}")
        sys.exit(1)
    if not xpath:
        print(f"{R}x-ui.db پیدا نشد{X}")
        sys.exit(1)

    print(f"{D}billing: {bpath}{X}")
    print(f"{D}x-ui:    {xpath}{X}\n")

    # ── ۱) نرخ‌های ثبت‌شده ──
    con = _open(bpath)
    conf = {}
    try:
        for r in con.execute("SELECT * FROM group_config"):
            d = dict(r)
            try:
                d["_rates"] = json.loads(d.get("rates") or "[]")
            except Exception:
                d["_rates"] = []
            conf[d["group_key"]] = d
    finally:
        con.close()

    print(f"{Y}── گروه‌هایی که در حسابداری ثبت شده‌اند ──{X}")
    if not conf:
        print(f"  {R}هیچ گروهی ثبت نشده{X}")
    for k, d in sorted(conf.items()):
        rates = d["_rates"]
        rt = "، ".join(
            ("نامحدود" if int(r.get("gb", 0) or 0) == 0 else f"{r.get('gb')}گیگ")
            + f"={r.get('price')}"
            for r in rates) or f"{R}هیچ نرخی{X}"
        print(f"  «{k}»  محاسبه={'بله' if d.get('billable') else 'خیر'}  "
              f"نرخ‌ها: {rt}")
        if d.get("per_gb"):
            print(f"      {D}نرخ حجمی: {d['per_gb']} — نرخ‌های بالا نادیده "
                  f"گرفته می‌شوند{X}")
        if d.get("settled_until"):
            print(f"      {D}تسویه تا: {d['settled_until']} — قبلش شمرده "
                  f"نمی‌شود{X}")
        if d.get("period_start"):
            print(f"      {D}شروع دوره: {d['period_start']}{X}")

    # ── ۲) گروه‌های واقعی در x-ui ──
    con = _open(xpath)
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(clients)")}
        if "group_name" not in cols:
            print(f"\n{R}جدول clients ستون group_name ندارد — این پنل "
                  f"نسخه‌ی قدیمی است{X}")
            sys.exit(1)
        # نام ستون حجم بین نسخه‌های x-ui فرق می‌کند. مثل بک‌اند، از
        # روی اسکیما انتخابش می‌کنیم نه از روی حدس.
        qcol = next((c for c in ("total_gb", "total", "totalGB") if c in cols),
                    None)
        if not qcol:
            print(f"\n{R}ستون حجم در جدول clients پیدا نشد — ستون‌ها: "
                  + "، ".join(sorted(cols)) + X)
            sys.exit(1)
        rows = [{"group_name": r[0], "total": r[1], "enable": r[2]}
                for r in con.execute(
                    "SELECT group_name, " + qcol + ", enable FROM clients")]
    finally:
        con.close()

    groups = {}
    for r in rows:
        g = r.get("group_name") or ""
        groups.setdefault(g, []).append(r)

    print(f"\n{Y}── گروه‌های واقعی در x-ui ──{X}")
    for g, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        shown = g if g else "(بدون گروه)"
        known = g in conf
        mark = f"{G}✓ ثبت شده{X}" if known else f"{R}✗ در حسابداری نیست{X}"
        print(f"  «{shown}» — {len(items)} کانفیگ  {mark}")

        if not known:
            near = [k for k in conf if k.strip().lower() == g.strip().lower()]
            if near:
                print(f"      {R}ولی «{near[0]}» ثبت شده — فقط فاصله یا "
                      f"حروف بزرگ و کوچک فرق دارد{X}")
            continue

        d = conf[g]
        if not d.get("billable"):
            print(f"      {D}محاسبه خاموش است — این گروه اصلاً صورتحساب "
                  f"نمی‌شود{X}")
            continue
        if d.get("per_gb"):
            continue

        # هر حجم، چند تا، و چه می‌شود
        buckets = {}
        for it in items:
            buckets.setdefault(_gb_of(it.get("total")), 0)
            buckets[_gb_of(it.get("total"))] += 1
        for gb, n in sorted(buckets.items()):
            price, why = _price_for(gb, d["_rates"])
            label = "نامحدود" if gb == 0 else f"{gb} گیگ"
            if price is None:
                print(f"      {R}✗ {n} کانفیگِ {label}: {why}{X}")
            else:
                print(f"      {G}✓ {n} کانفیگِ {label} → {price}{X}")

    print(f"\n{D}هیچ نام مشتری، شماره یا رمزی در این خروجی نیست.{X}")


if __name__ == "__main__":
    main()
