import asyncio
import io
import json
import logging
import os
import subprocess
import ctypes
import tempfile
import time

import cv2
import numpy as np
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

# Only these known applications can be launched. No arbitrary shell commands.
APP_COMMANDS = {
    "notepad": ("Блокнот", ["notepad.exe"]),
    "calculator": ("Калькулятор", ["calc.exe"]),
    "explorer": ("Проводник", ["explorer.exe"]),
    "paint": ("Paint", ["mspaint.exe"]),
}

# Windows multimedia virtual-key codes.
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
        [InlineKeyboardButton("🖱 Мышка", callback_data="page:mouse"),
         InlineKeyboardButton("⌨️ Клавиатура", callback_data="page:keyboard")],
        [InlineKeyboardButton("🔊 Громкость", callback_data="page:volume"),
         InlineKeyboardButton("🎵 Плеер", callback_data="page:media")],
        [InlineKeyboardButton("⚡ Комбинации", callback_data="page:shortcuts"),
         InlineKeyboardButton("📸 Медиа", callback_data="page:capture")],
        [InlineKeyboardButton("🗂 Приложения", callback_data="page:apps")],
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


def capture_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Сделать скриншот", callback_data="action:screenshot")],
        [InlineKeyboardButton("🎥 Записать 15 секунд", callback_data="action:record_video")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="page:home")],
    ])


def shortcuts_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Alt + F4 — закрыть окно", callback_data="shortcut:alt_f4")],
        [InlineKeyboardButton("Win + D — рабочий стол", callback_data="shortcut:win_d")],
        [InlineKeyboardButton("Win + I — параметры", callback_data="shortcut:win_i")],
        [InlineKeyboardButton("Ctrl + Shift + Esc — диспетчер задач", callback_data="shortcut:taskmgr")],
        [InlineKeyboardButton("Alt + Tab — сменить окно", callback_data="shortcut:alt_tab")],
        [InlineKeyboardButton("Win + E — проводник", callback_data="shortcut:win_e")],
        [InlineKeyboardButton("Win + R — выполнить", callback_data="shortcut:win_r")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="page:home")],
    ])


def record_screen_video(duration: int = 15) -> str:
    """Capture the desktop for a fixed period and return an MP4 file path."""
    screenshot = pyautogui.screenshot()
    width, height = screenshot.size
    scale = min(1.0, 1280 / width)
    out_width = max(2, int(width * scale) // 2 * 2)
    out_height = max(2, int(height * scale) // 2 * 2)
    fps = 8
    file_handle = tempfile.NamedTemporaryFile(prefix="couchcontrol-", suffix=".mp4", delete=False)
    video_path = file_handle.name
    file_handle.close()
    writer = cv2.VideoWriter(
        video_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (out_width, out_height)
    )
    if not writer.isOpened():
        writer.release()
        os.remove(video_path)
        raise RuntimeError("Не удалось создать MP4-видео.")

    try:
        deadline = time.monotonic() + duration
        interval = 1.0 / fps
        while time.monotonic() < deadline:
            frame_start = time.monotonic()
            frame = np.array(pyautogui.screenshot())
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            if (out_width, out_height) != (width, height):
                frame = cv2.resize(frame, (out_width, out_height), interpolation=cv2.INTER_AREA)
            writer.write(frame)
            remaining = interval - (time.monotonic() - frame_start)
            if remaining > 0:
                time.sleep(remaining)
    except Exception:
        writer.release()
        try:
            os.remove(video_path)
        except OSError:
            pass
        raise
    writer.release()
    return video_path


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Главное меню", callback_data="page:home")]])


def mouse_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↖", callback_data="mouse:ul"), InlineKeyboardButton("⬆️", callback_data="mouse:u"), InlineKeyboardButton("↗", callback_data="mouse:ur")],
        [InlineKeyboardButton("⬅️", callback_data="mouse:l"), InlineKeyboardButton("🖱 ЛКМ", callback_data="mouse:left"), InlineKeyboardButton("➡️", callback_data="mouse:r")],
        [InlineKeyboardButton("↙", callback_data="mouse:dl"), InlineKeyboardButton("⬇️", callback_data="mouse:d"), InlineKeyboardButton("↘", callback_data="mouse:dr")],
        [InlineKeyboardButton("ПКМ", callback_data="mouse:right"), InlineKeyboardButton("Колесо ↑", callback_data="mouse:su"), InlineKeyboardButton("Колесо ↓", callback_data="mouse:sd")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="page:home")],
    ])


def keyboard_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Ввести текст", callback_data="keyboard:type")],
        [InlineKeyboardButton("Enter", callback_data="key:enter"), InlineKeyboardButton("Esc", callback_data="key:esc"), InlineKeyboardButton("Tab", callback_data="key:tab")],
        [InlineKeyboardButton("Ctrl+C", callback_data="key:copy"), InlineKeyboardButton("Ctrl+V", callback_data="key:paste"), InlineKeyboardButton("Alt+Tab", callback_data="key:alt_tab")],
        [InlineKeyboardButton("Пробел", callback_data="key:space"), InlineKeyboardButton("Backspace", callback_data="key:backspace")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="page:home")],
    ])


def volume_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔉 −", callback_data="volume:down"), InlineKeyboardButton("🔊 +", callback_data="volume:up")],
        [InlineKeyboardButton("🔇 Вкл./выкл. звук", callback_data="volume:mute")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="page:home")],
    ])


def media_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏮ Назад", callback_data="media:previous"), InlineKeyboardButton("⏯ Пауза/старт", callback_data="media:play_pause"), InlineKeyboardButton("⏭ Далее", callback_data="media:next")],
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
            "Доступ пока не настроен. Для первичной настройки отправь /myid, "
            "впиши свой ID в ALLOWED_USER_ID в файле .env и перезапусти бота."
        )
        return
    context.user_data["awaiting_text"] = False
    await update.effective_message.reply_text(
        "🛋 CouchControl\nВыбери, чем управлять:", reply_markup=main_keyboard()
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
            caption="📸 Скриншот экрана компьютера из CouchControl",
        )
    except Exception:
        log.exception("Mini App screenshot failed")
        await update.effective_message.reply_text("Не удалось сделать скриншот экрана ПК.")


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if user and chat and chat.type == "private":
        await update.effective_message.reply_text(f"Твой Telegram user ID: {user.id}\nДобавь это число в ALLOWED_USER_ID в файле .env.")
    elif update.effective_message:
        await update.effective_message.reply_text("Открой бота в личном чате и отправь /myid.")


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
        await update.effective_message.reply_text("Слишком длинный текст. Максимум — 2000 символов.")
        return
    try:
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        context.user_data["awaiting_text"] = False
        await update.effective_message.reply_text("✅ Текст вставлен в активное окно ПК.", reply_markup=keyboard_keyboard())
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
        await query.answer("Нет доступа", show_alert=True)
        return
    await query.answer()
    data = query.data or ""

    pages = {
        "home": ("🛋 CouchControl\nВыбери, чем управлять:", main_keyboard),
        "mouse": ("🖱 Управление мышью\nНажимай стрелки для перемещения курсора.", mouse_keyboard),
        "keyboard": ("⌨️ Клавиатура\nНажми «Ввести текст», затем отправь сообщение. Текст будет вставлен в активное окно ПК.", keyboard_keyboard),
        "volume": ("🔊 Управление громкостью", volume_keyboard),
        "media": ("🎵 Управление плеером", media_keyboard),
        "capture": ("📸 Медиа\nВыбери скриншот или запись экрана.", capture_keyboard),
        "shortcuts": ("⚡ Быстрые комбинации клавиш", shortcuts_keyboard),
        "apps": ("🗂 Запуск приложений", apps_keyboard),
        "power": ("⏻ Питание компьютера", power_keyboard),
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
        return

    if data == "keyboard:type":
        context.user_data["awaiting_text"] = True
        await query.message.reply_text("✍️ Отправь следующим сообщением текст, который нужно вставить на ПК. Для отмены — /cancel.")
        return

    if data.startswith("shortcut:"):
        shortcuts = {
            "alt_f4": ("alt", "f4"),
            "win_d": ("win", "d"),
            "win_i": ("win", "i"),
            "taskmgr": ("ctrl", "shift", "esc"),
            "alt_tab": ("alt", "tab"),
            "win_e": ("win", "e"),
            "win_r": ("win", "r"),
        }
        keys = shortcuts.get(data.split(":", 1)[1])
        if keys:
            pyautogui.hotkey(*keys)
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
            await query.message.reply_photo(photo=buffer, caption="📸 Текущий экран компьютера")
        except Exception:
            log.exception("Screenshot failed")
            await query.message.reply_text("Не удалось сделать скриншот.")
        return

    if data == "action:record_video":
        status_message = await query.message.reply_text(
            "🎥 Записываю экран 15 секунд. После записи пришлю MP4 сюда."
        )
        video_path = None
        try:
            video_path = await asyncio.to_thread(record_screen_video, 15)
            with open(video_path, "rb") as video_file:
                await query.message.reply_video(
                    video=video_file,
                    caption="🎥 Запись экрана — 15 секунд",
                    supports_streaming=True,
                )
            await status_message.edit_text("✅ Видео отправлено.")
        except Exception:
            log.exception("Screen recording failed")
            await status_message.edit_text(
                "Не удалось записать или отправить видео. Проверь свободное место и повтори попытку."
            )
        finally:
            if video_path and os.path.exists(video_path):
                try:
                    os.remove(video_path)
                except OSError:
                    log.warning("Could not remove temporary video: %s", video_path)
        return

    if data == "action:status":
        await query.message.reply_text("🟢 CouchControl работает. Компьютер доступен через Telegram.")
        return

    if data in {"power:ask_shutdown", "power:ask_restart"}:
        action = "shutdown" if data.endswith("shutdown") else "restart"
        label = "выключить" if action == "shutdown" else "перезагрузить"
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Подтвердить: {label}", callback_data=f"power:confirm_{action}")],
            [InlineKeyboardButton("Отмена", callback_data="page:power")],
        ])
        await query.message.reply_text(
            f"⚠️ Точно {label} компьютер? Команда будет запланирована на 30 секунд, чтобы её можно было отменить.",
            reply_markup=markup,
        )
        return

    if data.startswith("power:confirm_"):
        action = data.rsplit("_", 1)[1]
        flag = "/s" if action == "shutdown" else "/r"
        subprocess.Popen(["shutdown", flag, "/t", "30"], shell=False)
        await query.message.reply_text(
            "⏳ Команда запланирована на 30 секунд. Если передумал, нажми отмену:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Отменить выключение/перезагрузку", callback_data="power:abort")]])
        )
        return

    if data == "power:abort":
        subprocess.Popen(["shutdown", "/a"], shell=False)
        await query.message.reply_text("✅ Запланированная команда отменена.", reply_markup=power_keyboard())
        return

    if data == "power:lock":
        ctypes.windll.user32.LockWorkStation()
        await query.message.reply_text("🔒 Компьютер заблокирован.")
        return


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("Unhandled bot error", exc_info=context.error)


def main() -> None:
    if not TOKEN:
        raise SystemExit("Не найден BOT_TOKEN. Заполни файл .env по образцу .env.example")
    if os.name != "nt":
        raise SystemExit("CouchControl Agent рассчитан на Windows 10/11.")

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
    log.info("CouchControl запущен. Разрешённый Telegram user ID: %s", ALLOWED_USER_ID or "не настроен")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
