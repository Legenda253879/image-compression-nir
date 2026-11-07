# -*- coding: utf-8 -*-
"""Рисунок: работа ДКП и квантования на реальном блоке 8x8.

Показывает четыре состояния одного и того же блока изображения:
исходные значения яркости, коэффициенты ДКП, таблицу квантования
и результат квантования, в котором большинство коэффициентов
обращается в нуль.

Размер картинки подобран под ширину полосы набора отчёта (17 см),
кегль совпадает с кеглем основного текста.
"""

import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from jpeg_core import dct2, scale_table, QY, rgb_to_ycbcr

TEXTWIDTH_IN = 17.0 / 2.54
FONT = 14.4

plt.rcParams.update({
    "font.family": "DejaVu Serif",
    "font.size": FONT,
    "figure.facecolor": "white",
    "text.color": "black",
})

QUALITY = 50
BY, BX = 24, 56           # координаты блока в единицах блоков 8x8

img = np.asarray(Image.open("images/photo.png").convert("RGB"))
Y, _, _ = rgb_to_ycbcr(img)
block = Y[BY * 8:BY * 8 + 8, BX * 8:BX * 8 + 8]

coeffs = dct2(block - 128.0)
Q = scale_table(QY, QUALITY)
quant = np.round(coeffs / Q)

PANELS = [
    (block,  "а) значения яркости",    "#2a78d6"),
    (coeffs, "б) коэффициенты ДКП",    "#2a78d6"),
    (Q,      "в) таблица квантования", "#52514e"),
    (quant,  "г) после квантования",   "#2a78d6"),
]

fig, axes = plt.subplots(2, 2, figsize=(TEXTWIDTH_IN, 7.3))

for ax, (data, title, hue) in zip(axes.ravel(), PANELS):
    weight = np.abs(data)
    weight = weight / weight.max() if weight.max() else weight
    for r in range(8):
        for c in range(8):
            v = data[r, c]
            v = 0.0 if abs(v) < 0.5 else v
            shade = 0.10 + 0.50 * weight[r, c] ** 0.45 if v != 0 else 0.0
            ax.add_patch(plt.Rectangle((c, -r - 1), 1, 1,
                                       facecolor=hue, alpha=shade,
                                       edgecolor="#b8b8b8", linewidth=0.6))
            ax.text(c + 0.5, -r - 0.5, f"{v:.0f}", ha="center", va="center",
                    fontsize=FONT,
                    color="#8a8a8a" if v == 0 else "black")
    ax.set_xlim(0, 8)
    ax.set_ylim(-8, 0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=FONT, pad=6)

zeros = int((quant == 0).sum())
fig.subplots_adjust(left=0.0, right=1.0, top=0.95, bottom=0.02,
                    wspace=0.035, hspace=0.10)
fig.savefig("dct_demo.png", dpi=200)
print(f"сохранено: dct_demo.png | нулей после квантования: {zeros} из 64")
print(f"наибольший по модулю коэффициент ДКП: {coeffs[np.unravel_index(np.abs(coeffs).argmax(), coeffs.shape)]:.0f}")
print(f"яркость в блоке: от {block.min():.0f} до {block.max():.0f}")
print(f"F(0,0) = {coeffs[0,0]:.0f}, Q(0,0) = {Q[0,0]:.0f} -> {quant[0,0]:.0f}")
