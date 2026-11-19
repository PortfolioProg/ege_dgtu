import csv
import json
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path("data")
OUT = Path("structure_report.json")  # в корне проекта, не в data/

report = []
for f in sorted(DATA_DIR.glob("*.csv")):
    if f.name == "ege_all.csv":  # пропускаем итоговый файл, если он вдруг в data/
        continue
    # csv-модуль показывает шапку "как есть", без интерпретации pandas
    with open(f, encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh, delimiter=";")
        header = next(reader, [])
        sample = next(reader, None)

        n_rows = 0
        lengths = defaultdict(int)
        if sample is not None:
            n_rows += 1
            lengths[len(sample)] += 1
        for row in reader:
            n_rows += 1
            lengths[len(row)] += 1

    report.append({
        "file": f.name,
        "n_cols": len(header),
        "header": header,          # точная шапка файла
        "sample_row": sample,      # первая строка данных для проверки смысла
        "n_rows": n_rows,
        "row_lengths": dict(lengths),  # если тут >1 варианта — строки "рваные"
    })

OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

# Краткая сводка: сколько реально разных структур
groups = defaultdict(list)
for r in report:
    groups[tuple(r["header"])].append(r["file"])

print(f"Проверено файлов: {len(report)}")
print(f"Разных вариантов шапки: {len(groups)}\n")
for i, (h, files) in enumerate(groups.items(), 1):
    print(f"Вариант {i}: {len(files)} файл(ов), {len(h)} колонок")
    print("  файлы:", ", ".join(files[:6]) + (" ..." if len(files) > 6 else ""))
print(f"\nГотово — отправьте мне файл {OUT}")