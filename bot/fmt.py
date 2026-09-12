"""
واژگان قالب‌بندی پیام‌های تلگرام.

چرا وجود دارد:
    تا امروز هر پیام ربات تگ‌های HTML را دستی داخل f-string می‌نوشت.
    نتیجه‌اش این بود که یک جا <b> بسته نمی‌شد، یک جا متن کاربر بدون
    امن‌سازی وسط تگ می‌نشست، و تلگرام کل پیام را با خطای «can't parse
    entities» رد می‌کرد — بدون اینکه کسی بفهمد کدام پیام بوده.

    این ماژول همان تگ‌ها را به توابع تبدیل می‌کند: ورودی همیشه
    امن‌سازی می‌شود، تگ همیشه بسته می‌شود، و check() قبل از ارسال
    ساختار را می‌سنجد.

تگ‌هایی که تلگرام در parse_mode=HTML می‌پذیرد:
    <b> <i> <u> <s> <code> <pre> <a href> <tg-spoiler>
    <blockquote> <blockquote expandable>

قاعده‌ی مهم: داخل <code> و <pre> هیچ قالب‌بندی دیگری کار نمی‌کند؛
محتوا عیناً همان‌طور که هست نمایش داده می‌شود. به همین دلیل bold()
و بقیه هرگز داخل code() صدا زده نمی‌شوند.
"""

import re

# ═══════════════════════════════════════════════════════════
#  امن‌سازی
# ═══════════════════════════════════════════════════════════

def esc(s):
    """
    متن خام را برای HTML امن می‌کند.

    هر چیزی که از کاربر یا پنل می‌آید باید از این رد شود. یک نام
    کاربری با < در آن، بدون این کار کل پیام را از کار می‌اندازد.
    """
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;")
                  .replace("<", "&lt;")
                  .replace(">", "&gt;"))


# ═══════════════════════════════════════════════════════════
#  تگ‌های ساده
# ═══════════════════════════════════════════════════════════

def b(s):
    """پررنگ — برای چیزی که چشم باید اول ببیند."""
    return f"<b>{esc(s)}</b>"


def i(s):
    """مورب — برای توضیح کناری، نه محتوای اصلی."""
    return f"<i>{esc(s)}</i>"


def u(s):
    return f"<u>{esc(s)}</u>"


def s(text):
    """خط‌خورده — برای قیمت قبل از تخفیف."""
    return f"<s>{esc(text)}</s>"


def code(s):
    """
    تک‌فاصله — برای هر چیزی که کاربر باید کپی کند.

    در تلگرام با یک ضربه کپی می‌شود، و چون فونتش عرض‌ثابت است
    رقم‌ها زیر هم می‌افتند و خواندن شماره‌ی کارت آسان می‌شود.
    """
    return f"<code>{esc(s)}</code>"


def pre(s, lang=None):
    """بلوک چندخطی تک‌فاصله — برای خروجی دستور یا لاگ."""
    if lang:
        return f'<pre><code class="language-{esc(lang)}">{esc(s)}</code></pre>'
    return f"<pre>{esc(s)}</pre>"


def spoiler(s):
    """پنهان تا وقتی کاربر بزند — برای چیزی که لو دادنش مزه را می‌برد."""
    return f"<tg-spoiler>{esc(s)}</tg-spoiler>"


def link(text, url):
    """
    لینک با متن خوانا.

    آدرس‌های بلند پیام را زشت می‌کنند؛ این‌طور فقط عنوان دیده می‌شود.
    اگر آدرس معتبر نباشد، فقط متن برمی‌گردد — یک لینک خراب نباید
    کل پیام را از کار بیندازد.
    """
    u_ = str(url or "").strip()
    if not re.match(r"^(https?|tg)://", u_):
        return esc(text)
    return f'<a href="{esc(u_)}">{esc(text)}</a>'


def user_link(text, tg_id):
    """اشاره به یک کاربر تلگرام بدون نیاز به یوزرنیم."""
    return f'<a href="tg://user?id={esc(tg_id)}">{esc(text)}</a>'


# ═══════════════════════════════════════════════════════════
#  نقل‌قول
# ═══════════════════════════════════════════════════════════

def quote(*lines):
    """
    نقل‌قول — برای نکته‌ای که باید از متن اصلی جدا دیده شود.

    ورودی از قبل قالب‌بندی‌شده پذیرفته می‌شود (یعنی خروجی b()، code()
    و مانند آن)، چون داخل نقل‌قول قالب‌بندی کار می‌کند.
    """
    body = "\n".join(str(x) for x in lines if x is not None)
    return f"<blockquote>{body}</blockquote>"


def quote_more(*lines):
    """
    نقل‌قول جمع‌شونده — راهنمای بلند بدون اینکه صفحه را پر کند.

    تلگرام فقط چند خط اول را نشان می‌دهد و بقیه با زدن روی آن باز
    می‌شود. برای آموزش نصب و متن‌های طولانی دقیقاً همین لازم است:
    کسی که بلد است رد می‌شود، کسی که نیست بازش می‌کند.
    """
    body = "\n".join(str(x) for x in lines if x is not None)
    return f"<blockquote expandable>{body}</blockquote>"


# ═══════════════════════════════════════════════════════════
#  الگوهای پرتکرار
# ═══════════════════════════════════════════════════════════

def price(new, old=None, unit="تومان"):
    """
    قیمت، و اگر تخفیفی هست قیمت قبلی خط‌خورده کنارش.

    دیدنِ «۲۵۰٬۰۰۰ ← ۱۹۰٬۰۰۰» خیلی قوی‌تر از نوشتن «۲۴٪ تخفیف» است،
    چون مشتری خودش مقدار صرفه‌جویی را می‌بیند.
    """
    if old and str(old) != str(new):
        return f"{s(f'{old} {unit}')} {b(f'{new} {unit}')}"
    return b(f"{new} {unit}")


def row(label, value, emoji=""):
    """
    یک سطر «برچسب: مقدار» با لنگر بصری در ابتدا.

    اموجی ابتدای خط کار نشانه را می‌کند: چشم موقع اسکرول روی آن
    می‌نشیند و لازم نیست کل خط خوانده شود.
    """
    head = f"{emoji} " if emoji else ""
    return f"{head}{esc(label)}  {b(value)}"


def field(label, value, emoji=""):
    """سطری که مقدارش کپی‌کردنی است — مثل شناسه یا کد پیگیری."""
    head = f"{emoji} " if emoji else ""
    return f"{head}{esc(label)}\n{code(value)}"


def bullet(text, emoji="▫️"):
    return f"{emoji} {esc(text)}"


def title(text, emoji=""):
    """تیتر پیام — همیشه اولین خط، همیشه پررنگ."""
    return f"{emoji} {b(text)}".strip()


def hr():
    """
    فاصله‌ی بین بخش‌ها.

    عمداً خط تزئینی نیست: خط‌های ━━━ روی موبایل می‌شکنند و پیام را
    به‌هم می‌ریزند. یک سطر خالی همان کار را بی‌دردسر می‌کند.
    """
    return ""


def join(*parts):
    """
    بخش‌ها را با یک سطر خالی به هم می‌چسباند و خالی‌ها را می‌اندازد.

    این‌طور می‌شود بخشی را شرطی ساخت بدون اینکه سطر خالی اضافه جا بماند.
    """
    return "\n\n".join(p for p in (str(x) for x in parts if x) if p.strip())


def lines(*parts):
    """مثل join ولی بدون سطر خالی بین‌شان."""
    return "\n".join(p for p in (str(x) for x in parts if x) if p.strip())


# ═══════════════════════════════════════════════════════════
#  اعتبارسنجی
# ═══════════════════════════════════════════════════════════

#: تگ‌هایی که تلگرام می‌شناسد. هرچه بیرون این باشد خطای parse می‌دهد.
ALLOWED = {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
           "code", "pre", "a", "tg-spoiler", "blockquote", "span"}

#: داخل اینها قالب‌بندی کار نمی‌کند، پس تگ تودرتو یعنی اشتباه منطقی
LITERAL = {"code", "pre"}

_TAG = re.compile(r"<(/?)([a-zA-Z-]+)([^>]*)>")


def check(text):
    """
    ساختار HTML یک پیام را می‌سنجد و فهرست ایرادها را برمی‌گرداند.

    تلگرام پیام با تگ خراب را رد می‌کند و کاربر هیچ چیزی نمی‌بیند.
    بهتر است این‌جا و در تست بفهمیم تا در دست مشتری.

    فهرست خالی یعنی سالم.
    """
    problems = []
    stack = []
    for m in _TAG.finditer(text):
        closing, name, attrs = m.group(1), m.group(2).lower(), m.group(3)

        if name not in ALLOWED:
            problems.append(f"تگ ناشناخته: <{name}>")
            continue

        if closing:
            if not stack:
                problems.append(f"</{name}> بدون باز شدن")
            elif stack[-1] != name:
                problems.append(f"</{name}> در حالی که <{stack[-1]}> باز است")
                stack.pop()
            else:
                stack.pop()
            continue

        # داخل code/pre هیچ تگی نباید باشد
        if stack and stack[-1] in LITERAL:
            problems.append(f"<{name}> داخل <{stack[-1]}> بی‌اثر است")

        if name == "a" and 'href="' not in attrs:
            problems.append("<a> بدون href")

        stack.append(name)

    for name in stack:
        problems.append(f"<{name}> بسته نشده")

    # & تنهایی هم پیام را می‌شکند
    for m in re.finditer(r"&(?!(amp|lt|gt|quot|#\d+);)", text):
        problems.append(f"& امن‌سازی‌نشده در نویسه‌ی {m.start()}")
        break

    return problems


def plain(text):
    """متن بدون تگ — برای شمردن طول واقعی و برای تست."""
    return re.sub(r"<[^>]+>", "", text)


#: سقف طول پیام در تلگرام
MAX_LEN = 4096


def too_long(text):
    """آیا پیام از سقف تلگرام رد شده؟ تگ‌ها هم حساب می‌شوند."""
    return len(text) > MAX_LEN
