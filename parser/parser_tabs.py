import io
import json
import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

DATA_DIR = Path("../data")
JSON_PATH = DATA_DIR / "ege_hse_tables.json"
SKIP_EXISTING = True  # не скачивать повторно уже сохранённые таблицы

# Короткие латинские имена для файлов (безопасны на любой ОС)
CATEGORY_SLUGS = {
    "Данные по вузам": "vuzy",
    "Данные по направлениям подготовки": "napravleniya",
}
TYPE_SLUGS = {
    "Бюджетный прием": "budget",
    "Платный прием": "paid",
}

# --- Читаем JSON и формируем список задач ---
with open(JSON_PATH, encoding="utf-8") as f:
    raw = json.load(f)

tasks = []  # (category, year, admission_type, url, путь к файлу)
for category, years in raw.items():
    category = category.strip()
    for year, types in years.items():
        year = int(year.strip())
        for admission_type, url in types.items():
            admission_type = admission_type.strip()
            url = url.strip()
            filename = (
                f"{CATEGORY_SLUGS.get(category, 'unknown')}_"
                f"{year}_{TYPE_SLUGS.get(admission_type, 'unknown')}.csv"
            )
            tasks.append((category, year, admission_type, url, DATA_DIR / filename))

print(f"Всего таблиц в файле: {len(tasks)}")
DATA_DIR.mkdir(exist_ok=True)

errors = []
saved = 0

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    for i, (category, year, admission_type, url, out_path) in enumerate(tasks, start=1):
        prefix = f"[{i}/{len(tasks)}] {out_path.name}"

        if SKIP_EXISTING and out_path.exists():
            print(f"{prefix}: уже есть, пропускаем")
            continue

        print(f"{prefix}: загружаем {url}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.locator("table tbody tr").first.wait_for(timeout=30000)
            time.sleep(2)  # пауза для дорисовки таблицы + вежливая задержка между запросами

            tables = pd.read_html(io.StringIO(page.content()))
            if not tables:
                raise RuntimeError("На странице не найдено ни одной таблицы")

            # Самая большая таблица на странице
            df = max(tables, key=lambda t: t.shape[0] * t.shape[1])
            df.columns = df.columns.str.replace(r"\s+", " ", regex=True).str.strip()

            # Метаданные — пригодятся при сборке всех файлов в одну таблицу
            df["category"] = category
            df["year"] = year
            df["admission_type"] = admission_type

            df.to_csv(out_path, index=False, encoding="utf-8-sig", sep=";")
            saved += 1
            print(f"{prefix}: ✅ сохранено {df.shape[0]} строк × {df.shape[1]} столбцов")

        except Exception as e:
            errors.append((out_path.name, url, str(e)))
            print(f"{prefix}: ❌ ошибка: {e}")

    browser.close()

print(f"\nГотово. Сохранено новых файлов: {saved}, ошибок: {len(errors)}")
if errors:
    print("\nНе скачались:")
    for name, url, err in errors:
        print(f"  {name}: {url}\n    {err}")
    print("\nЗапустите скрипт ещё раз — готовые файлы будут пропущены, "
          "а неудачные он попытается скачать заново.")