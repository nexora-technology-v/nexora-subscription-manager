"""
کلاینت سبک Telegram Bot API.

عمداً از فریم‌ورک استفاده نشده تا وابستگی اضافه نصب نشود و
رفتار کاملاً قابل پیش‌بینی بماند. فقط requests لازم است.
"""

import json
import time
import logging

import requests

log = logging.getLogger("nexora.tg")

API = "https://api.telegram.org/bot{token}/{method}"


class TelegramError(Exception):
    def __init__(self, description, code=None):
        super().__init__(description)
        self.description = description
        self.code = code


class Bot:
    def __init__(self, token: str, timeout: int = 25):
        self.token = token
        self.timeout = timeout
        self._session = requests.Session()

    # ---------- هسته ----------
    def call(self, method: str, **params):
        """
        فراخوانی متد. خطاهای موقت شبکه سه بار تلاش مجدد می‌شوند،
        ولی خطاهای منطقی تلگرام (مثل chat not found) بلافاصله بالا می‌روند.
        """
        files = params.pop("_files", None)
        payload = {
            k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
            for k, v in params.items() if v is not None
        }

        last_err = None
        for attempt in range(3):
            try:
                r = self._session.post(
                    API.format(token=self.token, method=method),
                    data=payload, files=files, timeout=self.timeout
                )
                data = r.json()
                if data.get("ok"):
                    return data.get("result")

                desc = data.get("description", "خطای نامشخص")
                code = data.get("error_code")

                # محدودیت نرخ — صبر و تلاش مجدد
                if code == 429:
                    wait = (data.get("parameters") or {}).get("retry_after", 3)
                    time.sleep(min(wait, 30))
                    continue

                raise TelegramError(desc, code)

            except requests.RequestException as e:
                last_err = e
                time.sleep(1.5 * (attempt + 1))

        raise TelegramError(f"شبکه در دسترس نبود: {last_err}")

    # ---------- پیام ----------
    def send(self, chat_id, text, keyboard=None, parse_mode="HTML",
             preview=False, reply_to=None, topic_id=None):
        return self.call(
            "sendMessage",
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=keyboard,
            link_preview_options={"is_disabled": not preview},
            reply_to_message_id=reply_to,
            message_thread_id=topic_id,
        )

    def action(self, chat_id, action="typing"):
        """
        نشان‌دادن «در حال تایپ…».

        ساخت کانفیگ چند ثانیه طول می‌کشد و در آن فاصله کاربر فکر
        می‌کند ربات قطع شده. این کوچک است ولی حس زنده‌بودن می‌دهد.
        خطایش هم بی‌اهمیت است، پس بی‌صدا رد می‌شود.
        """
        try:
            return self.call("sendChatAction", chat_id=chat_id, action=action)
        except TelegramError:
            return None

    def edit(self, chat_id, message_id, text, keyboard=None, parse_mode="HTML"):
        try:
            return self.call(
                "editMessageText",
                chat_id=chat_id, message_id=message_id, text=text,
                parse_mode=parse_mode, reply_markup=keyboard,
                link_preview_options={"is_disabled": True},
            )
        except TelegramError as e:
            # ویرایش به همان محتوا خطا می‌دهد — بی‌ضرر است
            if "not modified" in e.description.lower():
                return None
            raise

    def edit_markup(self, chat_id, message_id, keyboard=None):
        try:
            return self.call("editMessageReplyMarkup", chat_id=chat_id,
                             message_id=message_id, reply_markup=keyboard)
        except TelegramError as e:
            if "not modified" in e.description.lower():
                return None
            raise

    def delete(self, chat_id, message_id):
        try:
            return self.call("deleteMessage", chat_id=chat_id, message_id=message_id)
        except TelegramError:
            return None

    def answer_cb(self, cb_id, text=None, alert=False):
        try:
            return self.call("answerCallbackQuery", callback_query_id=cb_id,
                             text=text, show_alert=alert)
        except TelegramError:
            return None

    def send_photo(self, chat_id, photo, caption=None, keyboard=None, topic_id=None):
        return self.call("sendPhoto", chat_id=chat_id, photo=photo,
                         caption=caption, parse_mode="HTML",
                         reply_markup=keyboard, message_thread_id=topic_id)

    def send_doc(self, chat_id, path, caption=None, topic_id=None):
        with open(path, "rb") as f:
            return self.call("sendDocument", chat_id=chat_id, caption=caption,
                             parse_mode="HTML", message_thread_id=topic_id,
                             _files={"document": f})

    def copy(self, chat_id, from_chat_id, message_id, caption=None,
             keyboard=None, topic_id=None):
        return self.call("copyMessage", chat_id=chat_id, from_chat_id=from_chat_id,
                         message_id=message_id, caption=caption, parse_mode="HTML",
                         reply_markup=keyboard, message_thread_id=topic_id)

    # ---------- گروه و تاپیک ----------
    def create_topic(self, chat_id, name, icon_color=None):
        return self.call("createForumTopic", chat_id=chat_id, name=name,
                         icon_color=icon_color)

    def get_chat(self, chat_id):
        return self.call("getChat", chat_id=chat_id)

    def member_status(self, chat_id, user_id):
        """وضعیت عضویت کاربر در کانال — برای عضویت اجباری."""
        try:
            m = self.call("getChatMember", chat_id=chat_id, user_id=user_id)
            return (m or {}).get("status")
        except TelegramError:
            return None

    # ---------- دریافت به‌روزرسانی ----------
    def me(self):
        return self.call("getMe")

    def updates(self, offset=None, timeout=25):
        return self.call("getUpdates", offset=offset, timeout=timeout,
                         allowed_updates=["message", "callback_query",
                                          "my_chat_member"]) or []

    def drop_webhook(self):
        try:
            return self.call("deleteWebhook", drop_pending_updates=False)
        except TelegramError:
            return None


# ---------- کمکی‌های صفحه‌کلید ----------

def contact_kb(button_text="ارسال شماره من", skip_text=None):
    """
    کیبورد پایین صفحه با دکمه‌ی درخواست شماره.

    تلگرام فقط از طریق ReplyKeyboard با request_contact شماره می‌دهد —
    دکمه‌های شیشه‌ای این قابلیت را ندارند.
    """
    rows = [[{"text": button_text, "request_contact": True}]]
    if skip_text:
        rows.append([{"text": skip_text}])
    return {
        "keyboard": rows,
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def remove_kb():
    """برداشتن کیبورد پایین صفحه."""
    return {"remove_keyboard": True}


#: تنها اسکیم‌هایی که تلگرام در دکمه‌ی شیشه‌ای می‌پذیرد.
#
# اسکیم اپلیکیشن‌ها (happ://، v2rayng://، v2box://) را رد می‌کند و
# خطای BUTTON_URL_INVALID می‌دهد — و این خطا *کل پیام* را از بین
# می‌برد، نه فقط آن دکمه را. یعنی کانفیگ ساخته می‌شد ولی هیچ‌وقت
# به دست مشتری نمی‌رسید.
_OK_SCHEMES = ("http://", "https://", "tg://")


def valid_button_url(url):
    """آیا تلگرام این آدرس را در دکمه می‌پذیرد؟"""
    return isinstance(url, str) and url.lower().startswith(_OK_SCHEMES)


def kb(rows):
    """
    صفحه‌کلید شیشه‌ای. هر ردیف لیستی از (متن، داده) یا (متن، داده, 'url').

    دکمه‌ی url با اسکیم غیرمجاز حذف می‌شود — یک دکمه‌ی نمایش‌داده‌نشده
    خیلی بهتر از پیامی است که اصلاً ارسال نمی‌شود.
    """
    out = []
    for row in rows:
        line = []
        for item in row:
            if item is None:
                continue
            text, data = item[0], item[1]
            kind = item[2] if len(item) > 2 else None
            if kind == "url":
                if not valid_button_url(data):
                    continue
                line.append({"text": text, "url": data})
            elif kind == "copy":
                # دکمه‌ی کپی تلگرام: با یک ضربه متن در کلیپ‌بورد
                # می‌نشیند. برای لینک اشتراک بهترین حالت است — کاربر
                # لازم نیست متن را انتخاب کند و اشتباه ببرد.
                if not data:
                    continue
                line.append({"text": text, "copy_text": {"text": str(data)[:256]}})
            else:
                line.append({"text": text, "callback_data": data})
        if line:
            out.append(line)
    return {"inline_keyboard": out}


def esc(s):
    """امن‌سازی متن برای parse_mode=HTML."""
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
