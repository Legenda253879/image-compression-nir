# -*- coding: utf-8 -*-
"""Готовит числа для таблиц отчёта по результатам собственного запуска.

Печатает готовые строки LaTeX для таблиц 2.1, 2.2, 2.3 и 2.4,
а также время кодирования для раздела 2.6. Запускать после
experiment.py, в той же папке.
"""

import io
import csv
import math
import os
from collections import Counter

import numpy as np
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio as psnr

from jpeg_core import jpeg_encode

IMAGES = ["photo", "text", "graphics", "texture"]
CONTENT = {"photo": "фотография", "text": "страница с текстом",
           "graphics": "диаграмма", "texture": "текстура"}


def num(x, digits=2):
    """Число с запятой в качестве десятичного разделителя."""
    return f"{x:.{digits}f}".replace(".", ",")


def size(n):
    """Целое с неразрывным пробелом между разрядами, как требует ГОСТ."""
    s = f"{int(n):,}".replace(",", "\\,")
    return s


def entropy(data):
    freq = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


# --- Читаем результаты эксперимента ---
rows = {}
with open("results.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f, delimiter=";"):
        rows[(r["изображение"], r["формат"], r["качество"])] = r


def val(img, fmt, q, field):
    return rows[(img, fmt, q)][field]


print("=" * 70)
print("ТАБЛИЦА 2.1 — характеристики тестового набора")
print("=" * 70)
for name in IMAGES:
    img = Image.open(os.path.join("images", name + ".png")).convert("RGB")
    w, h = img.size
    e = entropy(np.asarray(img).tobytes())
    print(f"        {name:8s} & {CONTENT[name]:18s} & ${w}\\times{h}$ "
          f"& {size(w * h * 3)} & {num(e, 3)} \\\\")

print()
print("=" * 70)
print("ТАБЛИЦА 2.2 — сравнение собственной реализации с libjpeg")
print("=" * 70)
for name in IMAGES:
    img = Image.open(os.path.join("images", name + ".png")).convert("RGB")
    arr = np.asarray(img)
    print(f"        \\multirow{{2}}{{*}}{{{name}}}")
    for i, q in enumerate((50, 80)):
        my_size, rec = jpeg_encode(arr, q)
        my_psnr = psnr(arr, rec, data_range=255)

        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True)
        data = buf.getvalue()
        sos = data.find(b"\xff\xda")
        header = sos + 2 + int.from_bytes(data[sos + 2:sos + 4], "big")
        ref_size = len(data) - header
        ref = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"))
        ref_psnr = psnr(arr, ref, data_range=255)

        dev = 100.0 * (my_size / ref_size - 1.0)
        print(f"          & {q} & {size(my_size)} & {num(my_psnr)} "
              f"& {size(ref_size)} & {num(ref_psnr)} "
              f"& ${num(dev, 1)}\\,\\%$ \\\\")
    print("        \\hline")

print()
print("=" * 70)
print("ТАБЛИЦА 2.3 — сжатие без потерь")
print("=" * 70)
for name in IMAGES:
    png_s = val(name, "PNG", "", "размер")
    png_k = float(val(name, "PNG", "", "K"))
    wl_s = val(name, "WebP lossless", "", "размер")
    wl_k = float(val(name, "WebP lossless", "", "K"))
    print(f"        {name:8s} & {size(png_s)} & {num(png_k)} "
          f"& {size(wl_s)} & {num(wl_k)} \\\\")

print()
print("=" * 70)
print("ТАБЛИЦА 2.4 — сжатие с потерями")
print("=" * 70)
PLAN = [("JPEG", "80", "$q=80$"), ("WebP", "80", "$q=80$"),
        ("AVIF", "80", "$q=80$"), ("JPEG 2000", "16", "16"),
        ("Своя реализация", "80", "$q=80$")]
for name in IMAGES:
    print(f"        \\multirow{{5}}{{*}}{{{name}}}")
    for fmt, q, param in PLAN:
        r = rows[(name, fmt, q)]
        label = "Своя реализация" if fmt == "Своя реализация" else fmt
        print(f"          & {label:16s} & {param:7s} & {size(r['размер'])} "
              f"& {num(float(r['K']))} & {num(float(r['PSNR']))} "
              f"& {num(float(r['SSIM']), 3)} \\\\")
    print("        \\hline")

print()
print("=" * 70)
print("ВРЕМЯ КОДИРОВАНИЯ для раздела 2.6 (фотография, качество 80)")
print("=" * 70)
for fmt in ["JPEG", "WebP", "AVIF"]:
    t = float(val("photo", fmt, "80", "время")) * 1000
    print(f"        {fmt:6s} {num(t, 1):>8s} мс")
jpeg_t = float(val("photo", "JPEG", "80", "время"))
avif_t = float(val("photo", "AVIF", "80", "время"))
print(f"\n        AVIF медленнее JPEG в {avif_t / jpeg_t:.0f} раз")
