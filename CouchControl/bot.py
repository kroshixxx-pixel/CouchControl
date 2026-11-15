import asyncio
import io
import json
import logging
import os
import subprocess
import ctypes
from ctypes import wintypes

import pyautogui
import pyperclip
from dotenv import load_dotenv
from web_server import start_web_server, stop_web_server
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://kroshixxx-pixel.github.io/CouchControl/").strip()
try:
    ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0").strip() or "0")
except ValueError:
    ALLOWED_USER_ID = 0

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("couchcontrol")
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.04

# Можно запускать только перечисленные приложения. Произвольные команды оболочки не выполняются.
APP_COMMANDS = {
    "notepad": ("Блокнот", ["notepad.exe"]),
    "calculator": ("Калькулятор", ["calc.exe"]),
    "explorer": ("Проводник", ["explorer.exe"]),
    "paint": ("Paint", ["mspaint.exe"]),
}

# Виртуальные коды клавиш мультимедиа Windows.
VK = {
    "volume_up": 0xAF,
    "volume_down": 0xAE,
    "volume_mute": 0xAD,
    "media_play_pause": 0xB3,
    "media_next": 0xB0,
    "media_previous": 0xB1,
}


def authorized(update: Update) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    return bool(
        user and chat and chat.type == "private"
        and ALLOWED_USER_ID and user.id == ALLOWED_USER_ID
    )


def main_keyboard() -> InlineKeyboardMarkup:
    rows = []
    rows.extend([
        [InlineKeyboardButton("🖱 Мышь", callback_data="page:mouse"),
         InlineKeyboardButton("⌨️ Клавиатура", callback_data="page:keyboard")],
        [InlineKeyboardButton("🔊 Громкость", callback_data="page:volume"),
         InlineKeyboardButton("🎵 Мультимедиа", callback_data="page:media")],
        [InlineKeyboardButton("📸 Скриншот", callback_data="action:screenshot"),
         InlineKeyboardButton("🗂 Приложения", callback_data="page:apps")],
        [InlineKeyboardButton("⏻ Питание", callback_data="page:power"),
         InlineKeyboardButton("ℹ️ Статус", callback_data="action:status")],
    ])
    return InlineKeyboardMarkup(rows)


def webapp_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Открыть CouchControl", web_app=WebAppInfo(url=WEB_APP_URL))]],
        resize_keyboard=True,
        is_persistent=True,
    )


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Главное меню", callback_data="page:home")]])


def mouse_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↖", callback_data="mouse:ul"), InlineKeyboardButton("⬆️", callback_data="mouse:u"), InlineKeyboardButton("↗", callback_data="mouse:ur")],
        [InlineKeyboardButton("⬅️", callback_data="mouse:l"), InlineKeyboardButton("🖱 Левый клик", callback_data="mouse:left"), InlineKeyboardButton("➡️", callback_data="mouse:r")],
        [InlineKeyboardButton("↙", callback_data="mouse:dl"), InlineKeyboardButton("⬇️", callback_data="mouse:d"), InlineKeyboardButton("↘", callback_data="mouse:dr")],
        [InlineKeyboardButton("Правый клик", callback_data="mouse:right"), InlineKeyboardButton("Прокрутка вверх", callback_data="mouse:su"), InlineKeyboardButton("Прокрутка вниз", callback_data="mouse:sd")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="page:home")],
    ])


def keyboard_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Ввести текст", callback_data="keyboard:type")],
        [InlineKeyboardButton("Enter", callback_data="key:enter"), InlineKeyboardButton("Esc", callback_data="key:esc"), InlineKeyboardButton("Tab", callback_data="key:tab")],
        [InlineKeyboardButton("Ctrl+C", callback_data="key:copy"), InlineKeyboardButton("Ctrl+V", callback_data="key:paste"), InlineKeyboardButton("Alt+Tab", callback_data="key:alt_tab")],
        [InlineKeyboardButton("Space", callback_data="key:space"), InlineKeyboardButton("Backspace", callback_data="key:backspace")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="page:home")],
    ])


def volume_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔉 −", callback_data="volume:down"), InlineKeyboardButton("🔊 +", callback_data="volume:up")],
        [InlineKeyboardButton("🔇 Mute / unmute", callback_data="volume:mute")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="page:home")],
    ])


def media_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏮ Предыдущий", callback_data="media:previous"), InlineKeyboardButton("⏯ Пуск / пауза", callback_data="media:play_pause"), InlineKeyboardButton("⏭ Следующий", callback_data="media:next")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="page:home")],
    ])


def apps_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(label, callback_data=f"app:{key}")] for key, (label, _cmd) in APP_COMMANDS.items()]
    rows.append([InlineKeyboardButton("⬅️ Главное меню", callback_data="page:home")])
    return InlineKeyboardMarkup(rows)


def power_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔒 Заблокировать ПК", callback_data="power:lock")],
        [InlineKeyboardButton("⏻ Выключить…", callback_data="power:ask_shutdown"), InlineKeyboardButton("🔄 Перезагрузить…", callback_data="power:ask_restart")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="page:home")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        await update.effective_message.reply_text(
            "Доступ ещё не настроен. Для настройки отправьте /myid, "
            "укажите свой ID в ALLOWED_USER_ID в файле .env и перезапустите бота."
        )
        return
    context.user_data["awaiting_text"] = False
    await update.effective_message.reply_text(
        "🛋 CouchControl\nВыберите, чем хотите управлять:", reply_markup=main_keyboard()
    )
    if WEB_APP_URL.startswith("https://"):
        await update.effective_message.reply_text(
            "Нажмите кнопку ниже, чтобы открыть Mini App и запросить снимки экрана.",
            reply_markup=webapp_reply_keyboard(),
        )


async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update) or not update.effective_message or not update.effective_message.web_app_data:
        return
    try:
        payload = json.loads(update.effective_message.web_app_data.data)
    except (ValueError, TypeError):
        return
    if payload.get("action") != "screenshot":
        return
    try:
        image = pyautogui.screenshot()
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=75, optimize=True)
        buffer.seek(0)
        await update.effective_message.reply_photo(
            photo=buffer,
            caption="📸 Снимок экрана ПК через CouchControl",
        )
    except Exception:
        log.exception("Mini App screenshot failed")
        await update.effective_message.reply_text("Не удалось сделать снимок экрана ПК.")


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if user and chat and chat.type == "private":
        await update.effective_message.reply_text(f"Ваш Telegram ID: {user.id}\nДобавьте это число в ALLOWED_USER_ID в файле .env.")
    elif update.effective_message:
        await update.effective_message.reply_text("Откройте бота в личном чате и отправьте команду /myid.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting_text"] = False
    if authorized(update):
        await update.effective_message.reply_text("Ввод текста отменён.", reply_markup=main_keyboard())


async def text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        return
    if not context.user_data.get("awaiting_text"):
        return
    text = update.effective_message.text or ""
    if not text:
        return
    if len(text) > 2000:
        await update.effective_message.reply_text("Текст слишком длинный. Максимальная длина — 2 000 символов.")
        return
    try:
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        context.user_data["awaiting_text"] = False
        await update.effective_message.reply_text("✅ Текст вставлен в активное окно на ПК.", reply_markup=keyboard_keyboard())
    except Exception as exc:
        log.exception("Text paste failed")
        await update.effective_message.reply_text(f"Не удалось вставить текст: {exc}")


def press_vk(code: int) -> None:
    ctypes.windll.user32.keybd_event(code, 0, 0, 0)
    ctypes.windll.user32.keybd_event(code, 0, 2, 0)


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    if not authorized(update):
        await query.answer("Доступ запрещён", show_alert=True)
        return
    await query.answer()
    data = query.data or ""

    pages = {
        "home": ("🛋 CouchControl\nВыберите, чем хотите управлять:", main_keyboard),
        "mouse": ("🖱 Управление мышью\nИспользуйте стрелки, чтобы перемещать курсор.", mouse_keyboard),
        "keyboard": ("⌨️ Клавиатура\nНажмите «Ввести текст», затем отправьте сообщение. Текст будет вставлен в активное окно на ПК.", keyboard_keyboard),
        "volume": ("🔊 Управление громкостью", volume_keyboard),
        "media": ("🎵 Управление мультимедиа", media_keyboard),
        "apps": ("🗂 Запуск приложений", apps_keyboard),
        "power": ("⏻ Питание ПК", power_keyboard),
    }
    if data.startswith("page:"):
        page = data.split(":", 1)[1]
        text, markup_fn = pages.get(page, pages["home"])
        context.user_data["awaiting_text"] = False
        await query.edit_message_text(text, reply_markup=markup_fn())
        return

    if data.startswith("mouse:"):
        action = data.split(":", 1)[1]
        step = 55
        moves = {
            "ul": (-step, -step), "u": (0, -step), "ur": (step, -step),
            "l": (-step, 0), "r": (step, 0),
            "dl": (-step, step), "d": (0, step), "dr": (step, step),
        }
        if action in moves:
            pyautogui.moveRel(*moves[action], duration=0.05)
        elif action == "left":
            pyautogui.click(button="left")
        elif action == "right":
            pyautogui.click(button="right")
        elif action == "su":
            pyautogui.scroll(3)
        elif action == "sd":
            pyautogui.scroll(-3)
        return

    if data.startswith("key:"):
        action = data.split(":", 1)[1]
        if action == "copy": pyautogui.hotkey("ctrl", "c")
        elif action == "paste": pyautogui.hotkey("ctrl", "v")
        elif action == "alt_tab": pyautogui.hotkey("alt", "tab")
        elif action in {"enter", "esc", "tab", "space", "backspace"}:
            pyautogui.press({"esc": "esc"}.get(action, action))
        await query.answer("Клавиша нажата")
        return

    if data == "keyboard:type":
        context.user_data["awaiting_text"] = True
        await query.message.reply_text("✍️ Отправьте следующим сообщением текст, который нужно вставить на ПК. Для отмены отправьте /cancel.")
        return

    if data.startswith("volume:"):
        action = data.split(":", 1)[1]
        press_vk({"up": VK["volume_up"], "down": VK["volume_down"], "mute": VK["volume_mute"]}[action])
        return

    if data.startswith("media:"):
        action = data.split(":", 1)[1]
        press_vk(VK[action])
        return

    if data.startswith("app:"):
        key = data.split(":", 1)[1]
        if key not in APP_COMMANDS:
            return
        label, command = APP_COMMANDS[key]
        try:
            subprocess.Popen(command, shell=False)
            await query.message.reply_text(f"✅ Запускаю: {label}")
        except Exception:
            log.exception("App launch failed")
            await query.message.reply_text(f"Не удалось запустить: {label}")
        return

    if data == "action:screenshot":
        try:
            image = pyautogui.screenshot()
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=75)
            buffer.seek(0)
            await query.message.reply_photo(photo=buffer, caption="📸 Текущий экран ПК")
        except Exception:
            log.exception("Screenshot failed")
            await query.message.reply_text("Could not take a screenshot.")
        return

    if data == "action:status":
        await query.message.reply_text("🟢 CouchControl запущен. ПК доступен через Telegram.")
        return

    if data in {"power:ask_shutdown", "power:ask_restart"}:
        action = "shutdown" if data.endswith("shutdown") else "restart"
        label = "выключить" if action == "shutdown" else "перезагрузить"
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Подтвердить: {label}", callback_data=f"power:confirm_{action}")],
            [InlineKeyboardButton("Отмена", callback_data="page:power")],
        ])
        await query.message.reply_text(
            f"⚠️ Вы уверены, что хотите {label} ПК? Действие будет запланировано через 30 секунд — до этого его можно отменить.",
            reply_markup=markup,
        )
        return

    if data.startswith("power:confirm_"):
        action = data.rsplit("_", 1)[1]
        flag = "/s" if action == "shutdown" else "/r"
        subprocess.Popen(["shutdown", flag, "/t", "30"], shell=False)
        await query.message.reply_text(
            "⏳ Действие запланировано на 30 секунд. Если передумаете, нажмите «Отменить»:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Отменить выключение / перезагрузку", callback_data="power:abort")]])
        )
        return

    if data == "power:abort":
        subprocess.Popen(["shutdown", "/a"], shell=False)
        await query.message.reply_text("✅ Запланированное действие отменено.", reply_markup=power_keyboard())
        return

    if data == "power:lock":
        ctypes.windll.user32.LockWorkStation()
        await query.message.reply_text("🔒 ПК заблокирован.")
        return


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("Необработанная ошибка бота", exc_info=context.error)


def main() -> None:
    if not TOKEN:
        raise SystemExit("Не найден BOT_TOKEN. Создайте файл .env по образцу .env.example.")
    if os.name != "nt":
        raise SystemExit("CouchControl Agent предназначен для Windows 10/11.")

    app = (Application.builder().token(TOKEN)
           .post_init(start_web_server)
           .post_shutdown(stop_web_server)
           .build())
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_input))
    app.add_error_handler(error_handler)
    log.info("CouchControl запущен. Разрешённый Telegram ID: %s", ALLOWED_USER_ID or "not configured")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
