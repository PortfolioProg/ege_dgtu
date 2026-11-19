import pandas as pd

data = pd.read_csv("../ege_all.csv", sep=";", encoding="utf-8-sig")

print("1) score_change_competition заполнена только в:")
print(data.loc[data["score_change_competition"].notna(), "source_file"].value_counts())

print("\n2) Стоимость обучения, руб./год:")
print(data["tuition"].describe()[["min", "50%", "max"]])

print("\n3) Флаг вычета индивидуальных достижений:")
print(data["id_deducted"].value_counts(dropna=False))

print("\n4) Аномалии источника:")
bad_min = data[data["min_score"] > data["avg_score"]]
frac = data[data["enrolled"].notna() & (data["enrolled"] % 1 != 0)]
print("   min_score > avg_score:", len(bad_min))
print("   дробное число зачисленных:", len(frac))
if len(bad_min):
    print(bad_min["source_file"].value_counts().head())
if len(frac):
    print(frac["source_file"].value_counts().head())

print("\n5) Покрытие по годам (только вузы):")
v = data[data["category"] == "Данные по вузам"]
print(v.pivot_table(index="year", columns="admission_type",
                    values="university", aggfunc="count"))