# -*- coding: utf-8 -*-
"""Построение графиков по результатам эксперимента.

Строятся три рисунка:
    rd_psnr.png   - зависимость PSNR от битовой скорости (bpp);
    rd_ssim.png   - зависимость SSIM от битовой скорости;
    lossless.png  - коэффициент сжатия без потерь по типам изображений.

Размер картинки подобран под ширину полосы набора отчёта (17 см).
Изображение вставляется командой width=\\hsize без масштабирования,
поэтому кегль внутри рисунка совпадает с кеглем основного текста.
"""

import csv
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ширина полосы набора: 21 - 3 - 1 = 17 см
TEXTWIDTH_IN = 17.0 / 2.54
FONT = 14.4

plt.rcParams.update({
    "font.family": "DejaVu Serif",
    "font.size": FONT,
    "axes.titlesize": FONT,
    "axes.labelsize": FONT,
    "xtick.labelsize": FONT,
    "ytick.labelsize": FONT,
    "legend.fontsize": FONT,
    "axes.edgecolor": "#444444",
    "axes.labelcolor": "black",
    "text.color": "black",
    "xtick.color": "black",
    "ytick.color": "black",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "lines.linewidth": 1.8,
})

STYLE = {
    "JPEG":            {"color": "#2a78d6", "marker": "o", "ls": "-"},
    "WebP":            {"color": "#eb6834", "marker": "s", "ls": "--"},
    "AVIF":            {"color": "#1baf7a", "marker": "^", "ls": "-."},
    "JPEG 2000":       {"color": "#eda100", "marker": "D", "ls": ":"},
    "Своя реализация": {"color": "#e87ba4", "marker": "v", "ls": (0, (4, 1, 1, 1))},
}
LOSSY = list(STYLE)

TITLES = {"photo": "Фотография", "text": "Текст",
          "graphics": "Графика", "texture": "Текстура"}
ORDER = ["photo", "text", "graphics", "texture"]

rows = []
with open("results.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f, delimiter=";"):
        rows.append(r)

data = defaultdict(lambda: defaultdict(list))
for r in rows:
    data[r["изображение"]][r["формат"]].append(
        (float(r["bpp"]),
         None if r["PSNR"] == "inf" else float(r["PSNR"]),
         float(r["SSIM"]))
    )
for img in data:
    for fmt in data[img]:
        data[img][fmt].sort()


def rate_distortion(metric_index, ylabel, filename, ylim=None):
    """Кривые «качество - объём» для всех изображений, 2x2."""
    fig, axes = plt.subplots(2, 2, figsize=(TEXTWIDTH_IN, 8.4))

    for ax, img in zip(axes.ravel(), ORDER):
        for fmt in LOSSY:
            pts = [(b, m) for b, p, s in data[img][fmt]
                   for m in [p if metric_index == 1 else s] if m is not None]
            if not pts:
                continue
            st = STYLE[fmt]
            ax.plot([p[0] for p in pts], [p[1] for p in pts],
                    color=st["color"], linestyle=st["ls"], marker=st["marker"],
                    markersize=5.5, markeredgecolor="white",
                    markeredgewidth=0.7, label=fmt)

        ax.set_xscale("log")
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
            lambda v, _: f"{v:g}".replace(".", ",")))
        ax.set_title(TITLES[img], pad=6)
        ax.set_xlabel("Бит на пиксель")
        ax.set_ylabel(ylabel)
        ax.grid(True, which="both", color="#d8d8d8", linewidth=0.7)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        if ylim:
            ax.set_ylim(*ylim)

    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3,
               frameon=False, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig(filename, dpi=200)
    plt.close(fig)
    print("сохранено:", filename)


rate_distortion(1, "PSNR, дБ", "rd_psnr.png", ylim=(18, 52))
rate_distortion(2, "SSIM", "rd_ssim.png", ylim=(0.4, 1.01))

# --- Сжатие без потерь ---
fig, ax = plt.subplots(figsize=(TEXTWIDTH_IN, 4.6))
LL = ["PNG", "WebP lossless"]
LL_COLOR = {"PNG": "#2a78d6", "WebP lossless": "#eb6834"}
width = 0.36
for i, fmt in enumerate(LL):
    vals = []
    for img in ORDER:
        row = next(r for r in rows
                   if r["изображение"] == img and r["формат"] == fmt)
        vals.append(float(row["K"]))
    pos = [j + (i - 0.5) * (width + 0.02) for j in range(len(ORDER))]
    bars = ax.bar(pos, vals, width, color=LL_COLOR[fmt], label=fmt,
                  edgecolor="white", linewidth=1.2)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.08,
                f"{v:.2f}".replace(".", ","), ha="center", fontsize=FONT)

ax.set_xticks(range(len(ORDER)))
ax.set_xticklabels([TITLES[i] for i in ORDER])
ax.set_yscale("log")
ax.set_ylim(1, 900)
ax.set_ylabel("Коэффициент сжатия")
ax.grid(True, axis="y", which="major", color="#d8d8d8", linewidth=0.7)
ax.set_axisbelow(True)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
ax.legend(frameon=False, loc="upper left")
fig.tight_layout()
fig.savefig("lossless.png", dpi=200)
plt.close(fig)
print("сохранено: lossless.png")
