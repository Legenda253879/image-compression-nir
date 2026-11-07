# -*- coding: utf-8 -*-
"""Иллюстрации для отчёта: тестовый набор и артефакты сжатия.

Кегль подписей подобран так, чтобы при вставке картинки на всю
ширину полосы набора (17 см) текст на рисунке совпадал с кеглем
основного текста отчёта, то есть 14,4 pt.
"""

import io
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
TEXTWIDTH_CM = 17.0
PT = 14.4


def font_px(image_width_px, part_of_textwidth=1.0):
    """Размер шрифта в пикселях, дающий кегль 14,4 pt в готовом PDF."""
    cm_per_px = TEXTWIDTH_CM * part_of_textwidth / image_width_px
    return round((PT / 72 * 2.54) / cm_per_px)


NAMES = [("photo", "а) фотография"), ("text", "б) текст"),
         ("graphics", "в) графика"), ("texture", "г) текстура")]

# --- Рисунок: тестовый набор ---
TH, GAP = 300, 18
W = TH * 4 + GAP * 3
FS = font_px(W)
f_cap = ImageFont.truetype(FONT_PATH, FS)
CAP = int(FS * 2.0)

sheet = Image.new("RGB", (W, TH + CAP), (255, 255, 255))
d = ImageDraw.Draw(sheet)
for i, (name, cap) in enumerate(NAMES):
    im = Image.open(f"images/{name}.png").convert("RGB").resize((TH, TH))
    x = i * (TH + GAP)
    sheet.paste(im, (x, 0))
    d.rectangle([x, 0, x + TH - 1, TH - 1], outline=(120, 120, 120))
    w = d.textlength(cap, font=f_cap)
    d.text((x + (TH - w) / 2, TH + FS * 0.35), cap, font=f_cap, fill=(0, 0, 0))
sheet.save("testset.png")
print(f"сохранено: testset.png  {sheet.size[0]}x{sheet.size[1]} px, кегль {FS} px")

# --- Рисунок: артефакты сжатия при низком качестве ---
BOX = (20, 60, 180, 160)
SCALE = 3
src = Image.open("images/text.png").convert("RGB")


def compress(fmt, **params):
    buf = io.BytesIO()
    src.save(buf, format=fmt, **params)
    size = buf.getbuffer().nbytes
    buf.seek(0)
    return Image.open(buf).convert("RGB"), size


variants = [("исходное изображение", src, None)]
for fmt, label, params in [("JPEG", "JPEG", {"quality": 10}),
                           ("WEBP", "WebP", {"quality": 10}),
                           ("AVIF", "AVIF", {"quality": 10})]:
    im, size = compress(fmt, **params)
    variants.append((f"{label}, q = 10, {size} байт", im, size))

cw = (BOX[2] - BOX[0]) * SCALE
ch = (BOX[3] - BOX[1]) * SCALE
W2 = cw * 2 + GAP
FS2 = font_px(W2)
f2 = ImageFont.truetype(FONT_PATH, FS2)
CAP2 = int(FS2 * 2.0)

out = Image.new("RGB", (W2, ch * 2 + CAP2 * 2 + GAP), (255, 255, 255))
dd = ImageDraw.Draw(out)
for i, (cap, im, _) in enumerate(variants):
    col, row = i % 2, i // 2
    x = col * (cw + GAP)
    y = row * (ch + CAP2 + GAP)
    crop = im.crop(BOX).resize((cw, ch), Image.NEAREST)
    out.paste(crop, (x, y))
    dd.rectangle([x, y, x + cw - 1, y + ch - 1], outline=(120, 120, 120))
    w = dd.textlength(cap, font=f2)
    dd.text((x + (cw - w) / 2, y + ch + FS2 * 0.35), cap, font=f2, fill=(0, 0, 0))
out.save("artifacts.png")
print(f"сохранено: artifacts.png  {out.size[0]}x{out.size[1]} px, кегль {FS2} px")
