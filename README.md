# Converter

Веб-сервис конвертации файлов на Flask: загружаешь документ — получаешь сконвертированный.

- **DOCX → PDF** (через `pdfkit` / `wkhtmltopdf`)
- **CSV → XLSX** (через `pandas` / `openpyxl`)

Файлы складываются в пользовательскую сессию (`uploads/session_<uuid>/`), фоновый планировщик периодически чистит старые.

> ⚠️ Это учебный намеренно уязвимый сервис. Запускайте только в изолированной среде, не выставляйте в интернет.

## Стек

- Python 3.12, Flask 3, Gunicorn
- pdfkit + wkhtmltopdf (конвертация в PDF)
- pandas + openpyxl (конвертация в XLSX)
- APScheduler (очистка старых файлов)

## Запуск в Docker

```bash
docker compose up -d --build
```

Приложение: http://localhost:8000

Остановить:

```bash
docker compose down
```

> `wkhtmltopdf` в репозиториях Debian больше нет, поэтому в образ он ставится из официального пакета `wkhtmltox` (patched Qt, headless). Путь к бинарю приложение определяет само (переменная `WKHTMLTOPDF_PATH` или поиск в `PATH`).

## Локальный запуск без Docker

Нужен установленный `wkhtmltopdf` в системе.

```bash
python3 -m venv .venv && source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

```bash
gunicorn --bind 0.0.0.0:8000 wsgi:app
```

Или для разработки: `python app.py` (поднимется на порту 5000).

## Структура

```
app.py              маршруты и логика конвертации
wsgi.py             точка входа для gunicorn
requirements.txt    зависимости
templates/          index, myfiles, 404, 500
static/images/      логотип и картинки ошибок
uploads/            файлы пользователей (создаётся автоматически, в .gitignore)
```
