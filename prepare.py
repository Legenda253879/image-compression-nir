# -*- coding: utf-8 -*-
"""Подготовка тестового набора изображений.

Четыре изображения разных типов. Все приводятся к режиму RGB,
8 бит на канал, и сохраняются в PNG без потерь - это исходники,
с которыми дальше сравнивается результат сжатия.
"""

import os
from PIL import Image, ImageDraw, ImageFont
from skimage import data

os.makedirs("images", exist_ok=True)


def save(array_or_image, name):
    """Приводит изображение к RGB и сохраняет в PNG без потерь."""
    if isinstance(array_or_image, Image.Image):
        img = array_or_image
    else:
        img = Image.fromarray(array_or_image)
    img = img.convert("RGB")
    path = os.path.join("images", name + ".png")
    img.save(path, "PNG", optimize=True)
    w, h = img.size
    print(f"{name:12s} {w}x{h}  {os.path.getsize(path)} байт")


# 1. Фотография - плавные переходы яркости, много полутонов.
#    Снимок NASA, стандартное тестовое изображение.
save(data.astronaut(), "photo")

# 2. Текст - резкие границы, мало цветов, тонкие штрихи.
#    Имитация скриншота документа.
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
txt = Image.new("RGB", (512, 512), (255, 255, 255))
d = ImageDraw.Draw(txt)
f_head = ImageFont.truetype(FONT, 22)
f_body = ImageFont.truetype(FONT, 15)
d.text((24, 24), "Алгоритмы сжатия изображений", font=f_head, fill=(20, 20, 20))
lines = [
    "Избыточность изображения проявляется в трёх",
    "формах. Пространственная избыточность связана",
    "с тем, что соседние элементы растра принимают",
    "близкие значения яркости. Спектральная",
    "избыточность возникает из-за корреляции между",
    "цветовыми каналами. Психовизуальная",
    "избыточность обусловлена ограничениями",
    "зрительной системы человека, которая менее",
    "чувствительна к высокочастотным деталям",
    "цветовой составляющей, чем к яркостной.",
]
y = 72
for line in lines:
    d.text((24, y), line, font=f_body, fill=(30, 30, 30))
    y += 26
d.rectangle([24, y + 14, 488, y + 16], fill=(60, 90, 160))
for i, line in enumerate(["Пространственная", "Спектральная", "Психовизуальная"]):
    d.rectangle([24, y + 36 + i * 34, 40, y + 52 + i * 34], fill=(60, 90, 160))
    d.text((52, y + 34 + i * 34), line, font=f_body, fill=(30, 30, 30))
save(txt, "text")

# 3. Графика - плоские заливки, ограниченная палитра, чёткие края.
#    Имитация диаграммы из отчёта.
gr = Image.new("RGB", (512, 512), (255, 255, 255))
g = ImageDraw.Draw(gr)
f_t = ImageFont.truetype(FONT, 20)
f_s = ImageFont.truetype(FONT, 13)
g.text((24, 22), "Коэффициент сжатия", font=f_t, fill=(25, 25, 25))
COLORS = [(62, 110, 180), (224, 148, 48), (86, 160, 94), (190, 76, 76), (128, 100, 176)]
VALUES = [0.95, 0.62, 0.78, 0.45, 0.88]
LABELS = ["JPEG", "WebP", "AVIF", "PNG", "JP2"]
base_y, max_h = 400, 280
for i, (v, c, lb) in enumerate(zip(VALUES, COLORS, LABELS)):
    x = 60 + i * 84
    h = int(max_h * v)
    g.rectangle([x, base_y - h, x + 56, base_y], fill=c)
    g.text((x + 8, base_y + 10), lb, font=f_s, fill=(40, 40, 40))
g.line([44, base_y, 480, base_y], fill=(40, 40, 40), width=2)
g.line([44, 100, 44, base_y], fill=(40, 40, 40), width=2)
for i in range(5):
    yy = base_y - i * 70
    g.line([38, yy, 44, yy], fill=(40, 40, 40), width=2)
g.ellipse([360, 440, 380, 460], fill=(62, 110, 180))
g.text((392, 442), "с потерями", font=f_s, fill=(40, 40, 40))
save(gr, "graphics")

# 4. Текстура - высокочастотный шумоподобный сигнал, худший случай.
save(data.gravel(), "texture")

print("\nИсходники готовы: папка images/")
