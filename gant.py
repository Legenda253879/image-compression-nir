# -*- coding: utf-8 -*-
"""Диаграмма Ганта календарного плана выполнения работы."""

from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

TEXTWIDTH_IN = 17.0 / 2.54
FONT = 14.4

plt.rcParams.update({
    "font.family": "DejaVu Serif",
    "font.size": FONT,
    "axes.edgecolor": "#9a9a95",
    "text.color": "#2b2b2b",
    "xtick.color": "#52514e",
    "ytick.color": "#2b2b2b",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

STAGES = [
    ("Постановка цели и задач",            date(2026, 10, 22), date(2026, 10, 24)),
    ("Обзор научной литературы",           date(2026, 10, 25), date(2026, 11,  3)),
    ("Растровое изображение и метрики",    date(2026, 11,  4), date(2026, 11,  7)),
    ("Методы сжатия без потерь",           date(2026, 11,  8), date(2026, 11, 11)),
    ("Стандарт JPEG",                      date(2026, 11, 12), date(2026, 11, 17)),
    ("JPEG 2000 и современные форматы",    date(2026, 11, 18), date(2026, 11, 21)),
    ("Тестовый набор и методика",          date(2026, 11, 22), date(2026, 11, 24)),
    ("Реализация ядра кодера JPEG",        date(2026, 11, 25), date(2026, 11, 30)),
    ("Эксперимент и анализ результатов",   date(2026, 12,  1), date(2026, 12,  4)),
    ("Оформление отчёта",                  date(2026, 12,  5), date(2026, 12, 11)),
    ("Презентация и доклад",               date(2026, 12, 12), date(2026, 12, 15)),
]

fig, ax = plt.subplots(figsize=(TEXTWIDTH_IN, 5.6))

for i, (name, start, end) in enumerate(STAGES):
    y = len(STAGES) - i - 1
    width = (end - start).days + 1
    ax.barh(y, width, left=start, height=0.58,
            color="#2a78d6", edgecolor="white", linewidth=1.0)
    ax.text(mdates.date2num(end) + 1.4, y, str(width),
            va="center", fontsize=FONT, color="black")

ax.set_yticks(range(len(STAGES)))
ax.set_yticklabels([str(len(STAGES) - i) for i in range(len(STAGES))])
ax.xaxis.set_major_locator(mdates.DayLocator(bymonthday=(1, 15)))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
ax.set_xlim(date(2026, 10, 19), date(2026, 12, 27))
ax.set_ylabel("Номер этапа")
ax.grid(True, axis="x", color="#e3e3df", linewidth=0.7)
ax.set_axisbelow(True)
for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
fig.tight_layout()
fig.savefig("gant.png", dpi=200)
print("сохранено: gant.png")
