CouchControl — проект Windows-установщика

СБОРКА
1. Установите Inno Setup 6: https://jrsoftware.org/isinfo.php
2. Откройте CouchControl\CouchControl.iss в Inno Setup Compiler.
3. Нажмите Build -> Compile (Ctrl+F9).
4. EXE появится в CouchControl\Output\CouchControl-Setup.exe.

УСТАНОВКА
- Установщик предназначен для Windows 10/11 x64.
- Во время установки нужен интернет: официальный Python 3.12.10 загружается с python.org.
- Пользователь вводит Telegram Bot Token и числовой Telegram User ID.
- Python устанавливается локально в папку приложения, затем создаётся .venv и ставятся зависимости.
- Отдельная галочка автозапуска есть на странице дополнительных задач и по умолчанию выключена.
- Токен сохраняется локально в .env. Не публикуйте этот файл и не отправляйте его другим людям.

ДИАГНОСТИКА
При ошибке см.:
%TEMP%\CouchControl-install-diagnostic.log
%TEMP%\CouchControl-Python-install.log (если сам установщик Python создал этот файл)

ВАЖНО
Этот архив содержит исходники Inno Setup, а не готовый EXE. После сборки протестируйте установщик на отдельной чистой Windows 10/11 x64 машине. Среда подготовки не является Windows, поэтому фактическую установку здесь выполнить нельзя.
