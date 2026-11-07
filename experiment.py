# -*- coding: utf-8 -*-
"""Измерение характеристик алгоритмов сжатия изображений.

Для каждого исходного изображения выполняется сжатие несколькими
форматами. Для форматов с потерями параметр качества перебирается
по диапазону, что позволяет построить зависимость качества
восстановленного изображения от объёма файла.

Измеряемые величины:
    размер   - объём сжатых данных в байтах;
    bpp      - бит на пиксель, размер, нормированный к разрешению;
    K        - коэффициент сжатия относительно несжатого растра;
    PSNR     - пиковое отношение сигнала к шуму, дБ;
    SSIM     - индекс структурного сходства, от 0 до 1;
    время    - время кодирования, с.
"""

import io
import os
import csv
import math
import time
from collections import Counter

import numpy as np
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

from jpeg_core import jpeg_encode

IMAGES = ["photo", "text", "graphics", "texture"]

# Параметр качества для форматов с потерями.
QUALITY = [5, 10, 20, 30, 40, 50, 60, 70, 80, 85, 90, 95]
# Для JPEG 2000 задаётся не качество, а степень сжатия.
JP2_RATES = [4, 6, 8, 12, 16, 24, 32, 48, 64, 96]


def entropy(data):
    """Энтропия Шеннона в битах на байт."""
    freq = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


def row(name, label, q_label, size, dt, arr, rest, pixels):
    """Собирает строку результата по измеренным величинам."""
    raw = pixels * 3                      # несжатый растр, 3 байта на пиксель

    if np.array_equal(arr, rest):
        psnr, ssim = float("inf"), 1.0    # сжатие без потерь
    else:
        psnr = peak_signal_noise_ratio(arr, rest, data_range=255)
        ssim = structural_similarity(arr, rest, channel_axis=2, data_range=255)

    return {
        "изображение": name,
        "формат": label,
        "качество": q_label if q_label is not None else "",
        "размер": size,
        "bpp": round(size * 8 / pixels, 4),
        "K": round(raw / size, 3),
        "PSNR": "inf" if math.isinf(psnr) else round(psnr, 2),
        "SSIM": round(ssim, 5),
        "время": round(dt, 4),
    }


def measure(name, original, arr, fmt, label, q_label=None, **params):
    """Измерение для формата, поддерживаемого библиотекой Pillow."""
    buf = io.BytesIO()
    t0 = time.perf_counter()
    original.save(buf, format=fmt, **params)
    dt = time.perf_counter() - t0
    size = buf.getbuffer().nbytes
    buf.seek(0)
    rest = np.asarray(Image.open(buf).convert("RGB"))
    w, h = original.size
    return row(name, label, q_label, size, dt, arr, rest, w * h)


def measure_own(name, original, arr, quality):
    """Измерение для собственной реализации ядра кодера JPEG."""
    t0 = time.perf_counter()
    size, rest = jpeg_encode(arr, quality)
    dt = time.perf_counter() - t0
    w, h = original.size
    return row(name, "Своя реализация", quality, size, dt, arr, rest, w * h)


rows = []

for name in IMAGES:
    path = os.path.join("images", name + ".png")
    original = Image.open(path).convert("RGB")
    arr = np.asarray(original)
    w, h = original.size
    raw = w * h * 3

    print(f"\n=== {name}  {w}x{h}  несжатый растр {raw} байт ===")
    print(f"энтропия исходных байтов: {entropy(arr.tobytes()):.3f} бит/байт")

    # --- Сжатие без потерь ---
    rows.append(measure(name, original, arr, "PNG", "PNG", optimize=True))
    rows.append(measure(name, original, arr, "WEBP", "WebP lossless", lossless=True))

    # --- Сжатие с потерями ---
    for q in QUALITY:
        rows.append(measure(name, original, arr, "JPEG", "JPEG", q, quality=q))
        rows.append(measure(name, original, arr, "WEBP", "WebP", q, quality=q))
        rows.append(measure(name, original, arr, "AVIF", "AVIF", q, quality=q))
        rows.append(measure_own(name, original, arr, q))

    for r in JP2_RATES:
        rows.append(measure(name, original, arr, "JPEG2000", "JPEG 2000", r,
                            quality_mode="rates", quality_layers=[r],
                            irreversible=True))

    # Краткая сводка: без потерь и все форматы при качестве 80
    for r in rows:
        if r["изображение"] == name and r["качество"] in ("", 80):
            psnr = r["PSNR"]
            print(f"  {r['формат']:16s} q={str(r['качество']):>3s}"
                  f"  {r['размер']:>7d} байт  K={r['K']:>7.2f}"
                  f"  PSNR={psnr if psnr == 'inf' else f'{psnr:.2f}'}"
                  f"  SSIM={r['SSIM']}")

with open("results.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=";")
    writer.writeheader()
    writer.writerows(rows)

print(f"\nВсего измерений: {len(rows)}. Результаты записаны в results.csv")
