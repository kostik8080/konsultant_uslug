# Журнал процесса сборки и решений

## 2026-07-21

### Осмотр workspace

- Найден файл шаблона: `Шаблон паспорта бота.docx`.
- Готового проекта в корне не обнаружено.
- Проверены инструменты:
  - `python --version` → доступен Python 3.13.14.
  - `node --version` → Node.js не найден.

### Выбор стека

- Выбран Python, потому что он установлен локально.
- Для Telegram Bot API выбран пакет `python-telegram-bot`.
- Для переменных окружения выбран `python-dotenv`.

### Реализация

- Создан `bot.py` с обработчиками:
  - `/start` — приветствие и меню.
  - `/help` — справка.
  - кнопки меню: опыт, проекты, услуги, контакты/заявка.
  - текстовые сообщения — базовая подсказка по заявке.
- Токен не хардкодится: используется `TELEGRAM_BOT_TOKEN` из `.env` или окружения.
- Добавлен `.env.example` без реального секрета.

### Ошибки и решения

- Node.js не установлен: выбран Python-стек вместо Node.js.
- Редактирование исходного `.docx` без дополнительных библиотек затруднено. Решение: создать полноценный паспорт в Markdown и сгенерировать отдельный `.docx` встроенными средствами Python/Office Open XML.
- Первичная проверка импортов показала `ModuleNotFoundError: No module named 'telegram'`. Решение: установить зависимости командой `python -m pip install -r requirements.txt`.
- При установке pip сообщил, что зависимости установлены в пользовательское окружение, потому что системный `site-packages` недоступен для записи. Это не блокирует запуск проекта.

### Валидация

- `python -m py_compile bot.py tools\create_passport_docx.py` → успешно, синтаксических ошибок нет.
- `python -c "import telegram, dotenv; print('imports ok')"` → успешно после установки зависимостей.
- `python -c "from bot import build_application; build_application()"` без `.env` → ожидаемо завершилось ошибкой `Не задан TELEGRAM_BOT_TOKEN...`, значит секрет не хардкодится и конфигурация проверяется при запуске.
- `python -c "import zipfile; zipfile.ZipFile('Паспорт бота.docx').testzip() is None and print('docx zip ok')"` → успешно, сгенерированный `.docx` является корректным zip-пакетом Office Open XML.

### Проверка после добавления реального токена

- `.env` существует, переменная `TELEGRAM_BOT_TOKEN` присутствует. Значение токена не выводилось намеренно.
- `python -m py_compile bot.py` → успешно.
- `python -c "import telegram, dotenv; from bot import build_application; build_application(); print('config ok')"` → успешно, импорты и конфигурация проходят.
- Первый запуск `python bot.py` подтвердил соединение с Telegram API и старт приложения, но при уровне логирования `INFO` зависимость `httpx` вывела URL Telegram API, который включает токен. Решение: в `bot.py` добавлено понижение логирования `httpx` до `WARNING`, чтобы токен не попадал в консольные информационные логи.
- Повторный запуск `python bot.py` после исправления логирования: приложение стартует (`Application started`), токен в логах больше не печатается. Далее Telegram возвращает `telegram.error.Conflict: terminated by other getUpdates request`, что означает наличие другого активного polling/getUpdates для этого же бота. Локальных процессов `python.exe` с `bot.py` не найдено, текущий тестовый процесс остановлен.
