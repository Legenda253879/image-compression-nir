# -*- coding: utf-8 -*-
"""Собственная реализация ядра кодера JPEG.

Реализованы все ступени стандарта, кроме формирования файлового
контейнера: переход в цветовое пространство YCbCr, субдискретизация
цветности по схеме 4:2:0, дискретное косинусное преобразование блоками
8x8, квантование по таблицам стандарта, зигзагообразный обход,
кодирование длин серий и код Хаффмана.

Объём результата вычисляется как длина энтропийно закодированного
потока. Дополнительно выполняется обратный ход, что позволяет измерить
качество восстановленного изображения.
"""

import heapq
from collections import Counter

import numpy as np

# --- Таблицы квантования стандарта (ISO/IEC 10918-1, приложение K) ---

QY = np.array([
    [16, 11, 10, 16,  24,  40,  51,  61],
    [12, 12, 14, 19,  26,  58,  60,  55],
    [14, 13, 16, 24,  40,  57,  69,  56],
    [14, 17, 22, 29,  51,  87,  80,  62],
    [18, 22, 37, 56,  68, 109, 103,  77],
    [24, 35, 55, 64,  81, 104, 113,  92],
    [49, 64, 78, 87, 103, 121, 120, 101],
    [72, 92, 95, 98, 112, 100, 103,  99],
], dtype=float)

QC = np.array([
    [17, 18, 24, 47, 99, 99, 99, 99],
    [18, 21, 26, 66, 99, 99, 99, 99],
    [24, 26, 56, 99, 99, 99, 99, 99],
    [47, 66, 99, 99, 99, 99, 99, 99],
    [99, 99, 99, 99, 99, 99, 99, 99],
    [99, 99, 99, 99, 99, 99, 99, 99],
    [99, 99, 99, 99, 99, 99, 99, 99],
    [99, 99, 99, 99, 99, 99, 99, 99],
], dtype=float)


def scale_table(base, quality):
    """Масштабирует таблицу квантования под заданное качество.

    Чем ниже качество, тем больше делители и тем больше коэффициентов
    обращается в нуль после округления.
    """
    quality = min(max(int(quality), 1), 100)
    scale = 5000.0 / quality if quality < 50 else 200.0 - quality * 2.0
    table = np.floor((base * scale + 50.0) / 100.0)
    return np.clip(table, 1, 255)


# --- Матрица дискретного косинусного преобразования ---

def dct_matrix():
    """Строит матрицу ДКП размера 8x8 по определению преобразования."""
    T = np.zeros((8, 8))
    for u in range(8):
        cu = np.sqrt(1.0 / 8.0) if u == 0 else np.sqrt(2.0 / 8.0)
        for x in range(8):
            T[u, x] = cu * np.cos((2 * x + 1) * u * np.pi / 16.0)
    return T


T8 = dct_matrix()


def dct2(block):
    """Прямое ДКП блока 8x8."""
    return T8 @ block @ T8.T


def idct2(coeffs):
    """Обратное ДКП блока 8x8."""
    return T8.T @ coeffs @ T8


# --- Зигзагообразный порядок обхода ---

def zigzag_order():
    """Порядок обхода коэффициентов от низких частот к высоким."""
    order = []
    for s in range(15):
        diag = [(r, s - r) for r in range(8) if 0 <= s - r < 8]
        if s % 2 == 0:
            diag.reverse()
        order.extend(diag)
    return [r * 8 + c for r, c in order]


ZIGZAG = zigzag_order()


# --- Цветовое преобразование ---

def rgb_to_ycbcr(img):
    """Переход от RGB к YCbCr по формулам стандарта."""
    a = img.astype(float)
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    Y = 0.299 * R + 0.587 * G + 0.114 * B
    Cb = 128.0 - 0.168736 * R - 0.331264 * G + 0.5 * B
    Cr = 128.0 + 0.5 * R - 0.418688 * G - 0.081312 * B
    return Y, Cb, Cr


def ycbcr_to_rgb(Y, Cb, Cr):
    """Обратный переход от YCbCr к RGB."""
    R = Y + 1.402 * (Cr - 128.0)
    G = Y - 0.344136 * (Cb - 128.0) - 0.714136 * (Cr - 128.0)
    B = Y + 1.772 * (Cb - 128.0)
    out = np.stack([R, G, B], axis=2)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def subsample(ch):
    """Прореживание канала цветности по схеме 4:2:0 усреднением 2x2."""
    h, w = ch.shape
    ch = ch[:h - h % 2, :w - w % 2]
    return ch.reshape(ch.shape[0] // 2, 2, ch.shape[1] // 2, 2).mean(axis=(1, 3))


def upsample(ch, shape):
    """Восстановление разрешения канала цветности повторением отсчётов."""
    big = np.repeat(np.repeat(ch, 2, axis=0), 2, axis=1)
    return big[:shape[0], :shape[1]]


# --- Разбиение на блоки ---

def to_blocks(ch):
    """Дополняет канал до кратного восьми размера и режет на блоки 8x8."""
    h, w = ch.shape
    ph, pw = (-h) % 8, (-w) % 8
    if ph or pw:
        ch = np.pad(ch, ((0, ph), (0, pw)), mode="edge")
    H, W = ch.shape
    blocks = ch.reshape(H // 8, 8, W // 8, 8).transpose(0, 2, 1, 3)
    return blocks, (H, W)


def from_blocks(blocks, padded, shape):
    """Собирает канал обратно из блоков и убирает дополнение."""
    H, W = padded
    ch = blocks.transpose(0, 2, 1, 3).reshape(H, W)
    return ch[:shape[0], :shape[1]]


# --- Энтропийное кодирование ---

def category(value):
    """Число бит, необходимое для записи значения (категория по стандарту)."""
    return int(value).bit_length() if value else 0


def code_lengths(freq):
    """Длины кодовых слов Хаффмана по частотам символов.

    Используется тот же подход, что и в предыдущей работе: очередь
    с приоритетом, на каждом шаге объединяются два самых редких узла.
    """
    if not freq:
        return {}
    if len(freq) == 1:
        return {next(iter(freq)): 1}

    heap = [(w, i, (s,)) for i, (s, w) in enumerate(freq.items())]
    heapq.heapify(heap)
    counter = len(heap)
    lengths = Counter()
    while len(heap) > 1:
        w1, _, g1 = heapq.heappop(heap)
        w2, _, g2 = heapq.heappop(heap)
        for s in g1 + g2:
            lengths[s] += 1
        heapq.heappush(heap, (w1 + w2, counter, g1 + g2))
        counter += 1
    return lengths


def scan_blocks(blocks, Q):
    """Квантует блоки и превращает их в поток символов.

    Возвращает символы постоянной составляющей, символы переменной
    составляющей, число дополнительных бит и квантованные блоки.
    """
    nby, nbx = blocks.shape[:2]
    dc_symbols, ac_symbols = [], []
    extra_bits = 0
    quant = np.empty_like(blocks)
    prev_dc = 0

    for by in range(nby):
        for bx in range(nbx):
            block = blocks[by, bx] - 128.0          # сдвиг уровня
            coeffs = np.round(dct2(block) / Q)       # ДКП и квантование
            quant[by, bx] = coeffs
            flat = coeffs.reshape(-1)[ZIGZAG]        # зигзаг-обход

            # Постоянная составляющая кодируется разностью с предыдущей
            dc = int(flat[0])
            diff = dc - prev_dc
            prev_dc = dc
            cat = category(diff)
            dc_symbols.append(cat)
            extra_bits += cat

            # Переменная составляющая: пары "длина серии нулей -- категория"
            ac = flat[1:].astype(int)
            last = np.nonzero(ac)[0]
            last = last[-1] if len(last) else -1
            run = 0
            for k in range(last + 1):
                if ac[k] == 0:
                    run += 1
                    continue
                while run > 15:
                    ac_symbols.append((15, 0))       # серия из 16 нулей
                    run -= 16
                cat = category(ac[k])
                ac_symbols.append((run, cat))
                extra_bits += cat
                run = 0
            if last < 62:
                ac_symbols.append((0, 0))            # конец блока

    return dc_symbols, ac_symbols, extra_bits, quant


def stream_bits(dc_symbols, ac_symbols, extra_bits):
    """Считает объём потока при оптимальных кодах Хаффмана."""
    total = extra_bits
    for symbols in (dc_symbols, ac_symbols):
        lengths = code_lengths(Counter(symbols))
        total += sum(lengths[s] for s in symbols)
    return total


def reconstruct(quant, Q, padded, shape):
    """Обратный ход: деквантование, обратное ДКП, сборка канала."""
    nby, nbx = quant.shape[:2]
    out = np.empty_like(quant)
    for by in range(nby):
        for bx in range(nbx):
            out[by, bx] = idct2(quant[by, bx] * Q) + 128.0
    return from_blocks(out, padded, shape)


def jpeg_encode(img, quality=80):
    """Кодирует изображение и восстанавливает его обратно.

    Возвращает объём закодированного потока в байтах и восстановленное
    изображение в виде массива RGB.
    """
    qy = scale_table(QY, quality)
    qc = scale_table(QC, quality)

    Y, Cb, Cr = rgb_to_ycbcr(img)
    shape = Y.shape
    Cb_s, Cr_s = subsample(Cb), subsample(Cr)

    total_bits = 0
    planes = []
    for channel, Q in ((Y, qy), (Cb_s, qc), (Cr_s, qc)):
        blocks, padded = to_blocks(channel)
        dc, ac, extra, quant = scan_blocks(blocks, Q)
        total_bits += stream_bits(dc, ac, extra)
        planes.append((quant, Q, padded, channel.shape))

    size = (total_bits + 7) // 8

    Y_r = reconstruct(*planes[0])
    Cb_r = upsample(reconstruct(*planes[1]), shape)
    Cr_r = upsample(reconstruct(*planes[2]), shape)
    return size, ycbcr_to_rgb(Y_r, Cb_r, Cr_r)
