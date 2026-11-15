# 🤖 Установка CouchControl — инструкция

CouchControl позволяет управлять своим компьютером Windows через Telegram-бота: мышкой, клавиатурой, громкостью и другими функциями.

## 1. Подготовка

1. Скачай и установи **Python 3.12**: https://www.python.org/downloads/release/python-31210/
2. При установке поставь галочку `Add Python to PATH`.
3. Получи ZIP-архив CouchControl от друга.
4. Распакуй архив в удобное место.

## 2. Создание Telegram-бота

1. Открой Telegram и найди [@BotFather](https://t.me/BotFather).
2. Отправь `/newbot`.
3. Придумай название бота.
4. Придумай username, заканчивающийся на `bot`.
5. Скопируй полученный токен. Никому его не показывай!

## 3. Установка CouchControl

1. Открой папку `couchcontrol_bot`.
2. Нажми на адресную строку папки, напиши `powershell` и нажми Enter.
3. Выполняй команды по очереди:

```powershell
py -3.12 -m venv .venv
```

Если появится ошибка при активации скриптов, выполни:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Подтверди клавишей `Y`, затем:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Настройка бота

1. Найди файл `.env.example`.
2. Скопируй его в ту же папку.
3. Переименуй копию в `.env`.
4. Открой `.env` через Блокнот.
5. В строке `BOT_TOKEN=` вставь свой токен от BotFather.
6. Оставь `ALLOWED_USER_ID=0`.
7. Сохрани файл.

## 5. Первый запуск

В PowerShell введи:

```powershell
python bot.py
```

Теперь открой своего бота в Telegram и отправь:

`/myid`

Бот пришлёт числовой Telegram ID.

1. Останови программу сочетанием Ctrl+C.
2. Открой `.env`.
3. Замени `ALLOWED_USER_ID=0` на свой числовой ID.
4. Сохрани файл.
5. Снова запусти:

```powershell
python bot.py
```

6. Открой бота и отправь `/start`.

Готово! Можно пользоваться CouchControl.

## 6. Автозапуск Windows

Чтобы бот запускался автоматически при включении компьютера:

1. Открой файл `install_startup.ps1` через Блокнот.
2. Если скрипт выдаёт ошибку, замени его содержимое исправленной версией от друга.
3. Сохрани файл.
4. В PowerShell выполни:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_startup.ps1
```

После успешной установки бот будет запускаться автоматически при входе в Windows без открытия консоли.

## 🔐 Важная информация

- У каждого пользователя должен быть собственный Telegram-бот и собственный токен.
- Не отправляй никому файл `.env`.
- Не публикуй токен.
- Не передавай посторонним свой Telegram ID вместе с токеном.
- Компьютер должен быть включён и не находиться в спящем режиме.

**Приятного использования CouchControl! 🚀**