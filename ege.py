import io
import time
import pandas as pd
from playwright.sync_api import sync_playwright

urls = {
    2023: "https://ege.hse.ru/rating/2023/95405408/all/",
    2024: "https://ege.hse.ru/rating/2024/98607722/all/",
    2025: "https://ege.hse.ru/rating/2025/102338950/all/",
}

frames = []

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--disable-blink-features=AutomationControlled']
    )

    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    for year, url in urls.items():
        print(f"Начинаем обработку {year} года: {url}")
        try:
            # domcontentloaded надежнее, чем networkidle
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Ждем появления хотя бы одной строки в таблице
            page.locator("table tbody tr").first.wait_for(timeout=30000)

            # Небольшая пауза для гарантированного завершения рендеринга JS
            time.sleep(2)

            html_content = page.content()

            # ИСПРАВЛЕНИЕ: Оборачиваем HTML в io.StringIO, чтобы pandas читал его как поток данных, а не как путь к файлу
            tables = pd.read_html(io.StringIO(html_content))

            if not tables:
                print(f"⚠️ Предупреждение: Таблицы не найдены на странице за {year} год.")
                continue

            # Выбираем самую большую таблицу (по количеству ячеек)
            df = max(tables, key=lambda table: table.shape[0] * table.shape[1])
            print(f"✅ {year}: найдена таблица размером {df.shape}")

            df["year"] = year
            frames.append(df)

        except Exception as e:
            print(f"❌ Ошибка при обработке {year} года: {e}")

    browser.close()

# Сохраняем результат, только если данные были успешно собраны
if frames:
    data = pd.concat(frames, ignore_index=True)

    # Очищаем названия колонок от возможных переносов строк и лишних пробелов
    data.columns = data.columns.str.replace(r'\s+', ' ', regex=True).str.strip()

    data.to_csv("ege_monitoring.csv", index=False, encoding="utf-8-sig", sep=";")
    print(f"\n🎉 Успешно! Файл 'ege_monitoring.csv' создан. Всего строк: {len(data)}")
else:
    print("\n❌ Не удалось собрать данные. Файл не создан. Проверьте ошибки выше.")