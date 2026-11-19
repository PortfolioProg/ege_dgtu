import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path("../data")
OUT_ALL = Path("../ege_all.csv")          # вне data/
REVIEW = Path("column_mapping_review.csv")

META = ["category", "year", "admission_type"]

CANONICAL_ORDER = [
    "category", "year", "admission_type",
    "university", "field_group", "region", "profile",
    "avg_score", "score_change", "min_score",
    "avg_score_competition", "score_change_competition", "avg_score_no_id", "avg_score_budget",
    "enrolled", "enrolled_competition", "enrolled_bvi", "enrolled_quota",
    "enrolled_target", "enrolled_crimea", "enrolled_budget", "n_known_scores",
    "tuition", "id_deducted", "source_file",
]
NUMERIC = {
    "avg_score", "score_change", "min_score",
    "avg_score_competition", "score_change_competition",
    "avg_score_no_id", "avg_score_budget",
    "enrolled", "enrolled_competition", "enrolled_bvi", "enrolled_quota",
    "enrolled_target", "enrolled_crimea", "enrolled_budget", "n_known_scores",
    "tuition",
}
TEXT = {"university", "field_group", "region", "profile"}
NA_MARKERS = {"", "нет данных", "нет информации", "-", "—", "н/д"}


def norm(s):
    s = str(s).lower().replace("ё", "е")
    return re.sub(r"\s+", " ", s).strip()


# (regex, каноническое имя, только для этого вида приёма или None)
# ПОРЯДОК ВАЖЕН: специфичные правила раньше общих.
RULES = [
    (r"известна сумма", "n_known_scores", None),
    (r"рассчитан с вычетом", "id_deducted", None),
    (r"без вычета", "avg_score_no_id", None),
    (r"слабого|min\s*балл", "min_score", None),
    (r"(разность|насколько изменился).*по конкурсу", "score_change_competition", None),
    (r"разность|насколько изменился|рост\s*/\s*падени", "score_change", None),
    (r"стоимост", "tuition", None),
    (r"^регион", "region", None),
    (r"^профиль", "profile", None),
    (r"укрупн", "field_group", None),
    (r"^вуз", "university", None),
    (r"(балл|качество приема).*по конкурсу", "avg_score_competition", None),
    (r"(балл|качество приема).*(на бюджет|по результатам егэ)", "avg_score_budget", "Платный прием"),
    (r"балл|качество приема", "avg_score", None),
    (r"по конкурсу", "enrolled_competition", None),
    (r"олимпиад|без экзаменов|бви", "enrolled_bvi", None),
    (r"льгот|квот", "enrolled_quota", None),
    (r"целев", "enrolled_target", None),
    (r"крым", "enrolled_crimea", None),
    (r"на бюджет|по результатам егэ|кол-во зачисленных", "enrolled_budget", "Платный прием"),
    (r"зачислен|принято|количество студентов|сколько человек", "enrolled", None),
]


def map_columns(columns, admission_type):
    mapping, used, issues = {}, set(), []
    for col in columns:
        if col in META:
            continue
        low = norm(col)
        target = next(
            (name for pat, name, cond in RULES
             if (cond is None or cond == admission_type) and re.search(pat, low)),
            None,
        )
        if target is None:
            mapping[col] = re.sub(r"\s+", " ", str(col)).strip()
            issues.append(f"не распознана колонка: {col!r}")
            continue
        if target in used:
            issues.append(f"дубликат метрики {target!r} для колонки {col!r} -> {target}_2")
            target += "_2"
        used.add(target)
        mapping[col] = target
    return mapping, issues


frames, review, problems = [], [], []
files = sorted(p for p in DATA_DIR.glob("*.csv") if p.name != OUT_ALL.name)

for f in files:
    try:
        df = pd.read_csv(f, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)
    except Exception as e:
        problems.append(f"{f.name}: ошибка чтения: {e}")
        continue

    adm = df["admission_type"].iloc[0].strip()
    mapping, issues = map_columns(df.columns, adm)
    problems.extend(f"{f.name}: {msg}" for msg in issues)
    review.extend({"file": f.name, "original_column": o, "mapped_to": n}
                  for o, n in mapping.items())
    df = df.rename(columns=mapping)

    # --- чистка значений ---
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
        df.loc[df[c].str.lower().isin(NA_MARKERS), c] = pd.NA
    for c in TEXT & set(df.columns):
        df[c] = df[c].str.replace(r"\s+", " ", regex=True)
    for c in NUMERIC & set(df.columns):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if "id_deducted" in df.columns:
        df["id_deducted"] = (df["id_deducted"].str.lower()
                             .map({"да": True, "нет": False}).astype("boolean"))
    if "tuition" in df.columns:
        # значения < 10000 — это тыс. рублей (2011–2020 и направления), приводим к рублям
        t = df["tuition"]
        df["tuition"] = t.where(t >= 10000, t * 1000).round()

    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["source_file"] = f.name

    if not {"university", "avg_score", "enrolled"} <= set(df.columns):
        problems.append(f"{f.name}: нет обязательных колонок, файл пропущен")
        continue
    frames.append(df)

data = pd.concat(frames, ignore_index=True)
order = [c for c in CANONICAL_ORDER if c in data.columns]
order += sorted(c for c in data.columns if c not in order)
data = data[order]

data.to_csv(OUT_ALL, index=False, encoding="utf-8-sig", sep=";")
data[data.category == "Данные по вузам"].to_csv(
    "vuzy_all.csv", index=False, encoding="utf-8-sig", sep=";")
data[data.category == "Данные по направлениям подготовки"].to_csv(
    "napravleniya_all.csv", index=False, encoding="utf-8-sig", sep=";")
pd.DataFrame(review).to_csv(REVIEW, index=False, encoding="utf-8-sig", sep=";")

print(f"✅ {OUT_ALL}: {len(data)} строк × {len(data.columns)} колонок из {len(frames)} файлов")
print(data.groupby(["category", "admission_type"]).size())
if problems:
    print("\n⚠️ Требуют внимания:")
    for p in problems:
        print(" ", p)
print(f"\nПолная карта переименований: {REVIEW}")