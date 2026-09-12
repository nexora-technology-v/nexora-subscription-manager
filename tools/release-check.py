#!/usr/bin/env python3
"""
دروازه‌ی ریلیز — قبل از تگ‌زدن همه‌چیز را می‌سنجد.

چرا وجود دارد:
    چک‌لیست ریلیز تا امروز در حافظه‌ی آدم‌ها بود: تست‌ها را بگیر، نسخه
    را بالا ببر، CHANGELOG بنویس، بعد تگ بزن. حافظه گاهی خطا می‌کند و
    نتیجه‌اش ریلیزی است که یک نیمه‌اش جا مانده.

    این فایل همان چک‌لیست است، ولی اجرایی. اگر چیزی جا مانده باشد
    خروجی غیرصفر می‌دهد و اجازه‌ی ادامه نمی‌دهد.

اجرا:
    python3 tools/release-check.py              # کامل، قبل از تگ‌زدن
    python3 tools/release-check.py --tag v1.3.0 # فقط هماهنگی نسخه (CI)
    python3 tools/release-check.py --fast       # بدون تست‌های کند
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

G, R, Y, D, X = ("\033[38;5;42m", "\033[38;5;203m", "\033[38;5;221m",
                 "\033[38;5;245m", "\033[0m")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_fail = []


def rd(*p):
    return io.open(os.path.join(ROOT, *p), encoding="utf-8").read()


def ok(name, detail=""):
    print(f"  {G}✓{X} {name}" + (f" {D}— {detail}{X}" if detail else ""))


def bad(name, detail=""):
    _fail.append(name)
    print(f"  {R}✗{X} {name}" + (f" {D}— {detail}{X}" if detail else ""))


def check(name, cond, detail=""):
    (ok if cond else bad)(name, detail)
    return cond


def head(t):
    print(f"\n{D}── {t} ──{X}")


def run(cmd, cwd=None):
    """خروجی را نگه می‌دارد تا فقط وقتی شکست خورد چاپ شود."""
    try:
        p = subprocess.run(cmd, cwd=cwd or ROOT, shell=isinstance(cmd, str),
                           capture_output=True, text=True, timeout=600,
                           encoding="utf-8", errors="replace")
        return p.returncode == 0, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return False, "زمان اجرا تمام شد"
    except FileNotFoundError as e:
        return False, str(e)


# ═══════════════════════════════════════════════════════════
def version_checks(tag):
    head("هماهنگی نسخه")

    ver = rd("VERSION").strip()
    check("VERSION خوانده شد", re.fullmatch(r"\d+\.\d+\.\d+", ver), ver)

    pkg = json.loads(rd("frontend", "package.json")).get("version", "")
    check("package.json با VERSION یکی است", pkg == ver,
          f"VERSION={ver} · package.json={pkg}")

    changelog = rd("CHANGELOG.md")
    check(f"CHANGELOG برای {ver} بخش دارد", f"[{ver}]" in changelog,
          "بخش «## [{}]» پیدا نشد".format(ver) if f"[{ver}]" not in changelog
          else "")

    # بخش باید محتوا داشته باشد، نه فقط تیتر
    m = re.search(r"##\s*\[" + re.escape(ver) + r"\](.*?)(?=\n##\s*\[|\Z)",
                  changelog, re.S)
    body = (m.group(1).strip() if m else "")
    check("بخش CHANGELOG خالی نیست", len(body) > 80,
          f"{len(body)} کاراکتر")

    if tag:
        want = tag.lstrip("v")
        check(f"تگ {tag} با VERSION می‌خواند", want == ver,
              f"تگ={want} · VERSION={ver}")
    else:
        # بدون این، دروازه می‌گوید «آماده‌ی ریلیز ۱.۳.۰» در حالی که
        # ۱.۳.۰ قبلاً منتشر شده و تگ‌زدن دوباره‌اش شکست می‌خورد.
        okt, out = run(["git", "tag", "--list", f"v{ver}"])
        check(f"نسخه‌ی {ver} هنوز تگ نخورده", not (okt and out.strip()),
              f"v{ver} از قبل وجود دارد — اول VERSION را بالا ببرید"
              if okt and out.strip() else "")
    return ver


def git_checks():
    head("وضعیت مخزن")

    okc, out = run(["git", "status", "--porcelain"])
    if not okc:
        bad("git در دسترس است", out.strip()[:60])
        return
    dirty = [l for l in out.splitlines() if l.strip()]
    check("چیزی کامیت‌نشده نمانده", not dirty,
          f"{len(dirty)} فایل تغییرکرده" if dirty else "")
    for l in dirty[:8]:
        print(f"      {Y}▸{X} {l.strip()}")

    okb, branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    check("روی شاخه‌ی main هستیم", okb and branch.strip() == "main",
          branch.strip())


def test_checks(fast):
    head("تست‌ها")

    suites = [
        ("ربات", ["bot/test_bot.py", "bot/test_flow.py",
                  "bot/test_admin.py", "bot/test_xui.py",
                  "bot/test_fmt.py"]),
        ("پنل و ابزارها", ["tools/test-admin-api.py", "tools/test-billing.py",
                           "tools/test-monitor.py", "tools/test-firewall.py",
                           "tools/test-maintenance.py", "tools/test-serve.py",
                           "tools/test-intrusion.py"]),
        ("اتصال‌ها", ["tools/test-bot-buttons.py", "tools/test-seams.py",
                      "tools/check-api-contract.py"]),
    ]
    if not fast:
        suites.append(("توان عملیاتی", ["tools/test-bot-throughput.py"]))

    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for label, files in suites:
        broken = []
        for f in files:
            try:
                p = subprocess.run([sys.executable, f], cwd=ROOT, env=env,
                                   capture_output=True, text=True, timeout=400,
                                   encoding="utf-8", errors="replace")
                if p.returncode != 0:
                    broken.append((f, (p.stdout or p.stderr or "")[-400:]))
            except Exception as e:
                broken.append((f, str(e)))
        check(f"تست‌های {label}", not broken,
              f"{len(files)} سوییت" if not broken else f"{len(broken)} شکست")
        for f, detail in broken:
            print(f"      {Y}▸{X} {f}")
            for line in detail.strip().splitlines()[-4:]:
                print(f"        {D}{line}{X}")

    # پیش‌نمایش متن‌ها: اگر صفحه‌ای بشکند این‌جا traceback می‌دهد
    okp, out = run([sys.executable, "bot/preview_texts.py"])
    check("پیش‌نمایش همه‌ی صفحات ربات رندر می‌شود",
          okp and "Traceback" not in out,
          "" if okp else out.strip().splitlines()[-1][:70] if out else "")


def frontend_checks(fast):
    head("فرانت‌اند")

    nm = os.path.join(ROOT, "frontend", "node_modules")
    if not os.path.isdir(nm):
        bad("node_modules نصب است", "اول در frontend دستور npm install را بزنید")
        return

    if not fast:
        okb, out = run("npm run build", cwd=os.path.join(ROOT, "frontend"))
        check("پنل ساخته می‌شود", okb,
              "" if okb else out.strip().splitlines()[-1][:70])

    env = dict(os.environ, NODE_PATH=nm)
    for f, label in [("tools/test-render.cjs", "ظاهر پنل"),
                     ("test-panel-runtime.js", "اجرای پنل"),
                     ("test-subpage.js", "صفحه‌ی اشتراک")]:
        try:
            p = subprocess.run(["node", f], cwd=ROOT, env=env, timeout=400,
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            check(f"تست {label}", p.returncode == 0,
                  "" if p.returncode == 0
                  else (p.stdout or p.stderr or "").strip()[-70:])
        except Exception as e:
            bad(f"تست {label}", str(e)[:60])


# ═══════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", help="تگی که قرار است ساخته شود، مثل v1.3.0")
    ap.add_argument("--fast", action="store_true",
                    help="بدون build و تست‌های کند")
    args = ap.parse_args()

    print(f"\n{D}{'═' * 54}{X}")
    print("  دروازه‌ی ریلیز نکسورا")
    print(f"{D}{'═' * 54}{X}")

    ver = version_checks(args.tag)

    # در CI مخزن همیشه تمیز است و تست‌ها جداگانه اجرا شده‌اند؛
    # آن‌جا فقط هماهنگی نسخه مهم است.
    if not args.tag:
        git_checks()
        test_checks(args.fast)
        frontend_checks(args.fast)

    print(f"\n{D}{'─' * 54}{X}")
    if _fail:
        print(f"  {R}ریلیز نسازید — {len(_fail)} مورد باقی است:{X}")
        for f in _fail:
            print(f"    {R}▸{X} {f}")
        print()
        return 1

    print(f"  {G}آماده‌ی ریلیز {ver}{X}")
    if not args.tag:
        print(f"  {D}git tag -a v{ver} -m \"Nexora {ver}\" "
              f"&& git push newgh v{ver}{X}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
