import pandas as pd

# low_memory=False убирает DtypeWarning о смешанных типах
data = pd.read_csv("ege_all.csv", sep=";", encoding="utf-8-sig", low_memory=False)

# 1) Мусорная стоимость: реальная плата не бывает < 2 тыс. руб./год
susp = data[data["tuition"].notna() & (data["tuition"] < 2000)]
print(f"Подозрительная стоимость: {len(susp)} строк")
print(susp[["source_file", "university", "year", "tuition"]].head(20).to_string(index=False))
data.loc[data["tuition"] < 20000, "tuition"] = pd.NA

# 2) Два файла со съехавшими колонками: обнуляем недостоверные метрики,
#    остальное (avg_score, avg_score_budget) сохраняем + ставим пометку
BROKEN = ["vuzy_2012_paid.csv", "vuzy_2013_paid.csv"]
mask = data["source_file"].isin(BROKEN)
data.loc[mask, ["min_score", "enrolled"]] = pd.NA
data["qc_unreliable"] = mask

# 3) Флаг: из CSV приходит строками, приводим к булеву типу
data["id_deducted"] = (data["id_deducted"].astype(str).str.strip()
                       .map({"True": True, "False": False}).astype("boolean"))

# 4) Охват мониторинга: до 2018 — только госвузы, с 2018 — все
data["coverage"] = data["year"].map(
    lambda y: "state_only" if y <= 2017 else "all")

data.to_csv("ege_all_clean.csv", index=False, encoding="utf-8-sig", sep=";")
print(f"\n✅ ege_all_clean.csv: {len(data)} строк × {len(data.columns)} колонок")
print(f"Помечено как недостоверные: {int(mask.sum())} строк")
print(data.groupby("year")["tuition"].agg(["min", "median", "max", "count"]))