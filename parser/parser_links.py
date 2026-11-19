import json
import re
import html
import urllib.request
from urllib.parse import urljoin, urlsplit

# Любая страница рейтинга содержит полное левое меню
MENU_PAGE = "https://ege.hse.ru/ege/rating/2025/102338950/all/"

def get_html(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")

def collect():
    page = get_html(MENU_PAGE)
    menu = page[page.find("navigation_dpo"):]  # вырезаем левое меню

    # Токены меню в порядке следования: заголовок блока, год, ссылка
    token = re.compile(
        r'<span class="first_level">(?P<header>[^<]+)</span>'
        r'|<a href="(?P<href>[^"]*rating[^"]*)"[^>]*>(?P<kind>[^<]+)</a>'
    )

    result, original = {}, {}
    block = year = None
    for t in token.finditer(menu):
        if t.group("header"):                      # заголовок блока или год
            text = html.unescape(t.group("header")).strip()
            if text.isdigit():
                year = text
            else:
                block, year = text, None
        else:                                      # ссылка "Бюджетный/Платный прием"
            kind = html.unescape(t.group("kind")).strip()
            url = urljoin("https://ege.hse.ru/", html.unescape(t.group("href")))
            y, table_id = re.search(r"/rating/(\d{4})/(\d+)/", urlsplit(url).path).groups()

            # 2018+ приводим к формату /ege/rating/ГОД/ID/all/ (без фильтров),
            # 2011-2017 оставляем формат меню сайта /rating/ГОД/ID/gos/
            if int(y) >= 2018:
                clean = f"https://ege.hse.ru/ege/rating/{y}/{table_id}/all/"
            else:
                clean = f"https://ege.hse.ru/rating/{y}/{table_id}/gos/"

            result.setdefault(block, {}).setdefault(year, {})[kind] = clean
            original.setdefault(block, {}).setdefault(year, {})[kind] = url

    # годы по возрастанию: 2011 -> 2025
    result = {b: {y: result[b][y] for y in sorted(result[b], key=int)} for b in result}
    original = {b: {y: original[b][y] for y in sorted(original[b], key=int)} for b in original}
    return result, original

data, menu_original = collect()
n = sum(len(v) for b in data.values() for v in b.values())
assert n == 60, f"Ожидалось 60 ссылок, получено {n}"

with open("data/ege_hse_tables.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# запасной файл: ссылки ровно в том виде, в каком они стоят в меню сайта (с фильтрами)
with open("data/ege_hse_tables_menu_original.json", "w", encoding="utf-8") as f:
    json.dump(menu_original, f, ensure_ascii=False, indent=2)

print(f"Готово: {n} ссылок сохранены в ege_hse_tables.json")