#!/usr/bin/env python3
import os, math, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

# Дефолтные настройки
INPUT_DIR = './input'
OUTPUT_DIR = './output'
GRID_SIZE = 5
TILE_SIZE = 600
GAP = 10

def natural_sort_key(path):
    """Естественная сортировка: 1, 2, 10 вместо 1, 10, 2"""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', os.path.basename(path))]

def normalize_caption(filename):
    """Убрать расширение и всё после дефиса: '40-2.jpg' -> '40'"""
    name = os.path.splitext(os.path.basename(filename))[0]
    if '-' in name:
        name = name.split('-')[0]
    if name.isdigit():
        name = str(int(name))  # Убрать ведущие нули
    return name

def list_images(folder):
    exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}
    files = [os.path.join(folder, f) for f in os.listdir(folder)
             if os.path.splitext(f)[1].lower() in exts]
    return sorted(files, key=natural_sort_key)

def has_b_suffix(filename):
    """Проверить есть ли буква 'b' после цифры: 01b.jpg, 01b-2.jpg -> True"""
    name = os.path.splitext(os.path.basename(filename))[0]
    # Убрать всё после дефиса если есть
    if '-' in name:
        name = name.split('-')[0]
    # Проверить заканчивается ли на 'b' или 'B'
    return name.lower().endswith('b')

def remove_duplicates(files):
    """Удалить дубли: если после нормализации имена совпадают, оставить файл с максимальным размером.
    Исключить все файлы с буквой 'b' после цифры (01b, 01b-2 и т.п.)"""
    groups = {}

    # Сгруппировать файлы по нормализованному имени
    for filepath in files:
        normalized = normalize_caption(filepath)
        if normalized not in groups:
            groups[normalized] = []
        groups[normalized].append(filepath)

    # Для каждой группы выбрать файл с максимальным размером
    result = []
    duplicates_removed = 0
    b_files_removed = 0

    for normalized_name, file_list in groups.items():
        # Отфильтровать файлы с буквой 'b'
        files_without_b = [f for f in file_list if not has_b_suffix(f)]
        files_with_b = [f for f in file_list if has_b_suffix(f)]

        if files_with_b:
            b_files_removed += len(files_with_b)

        # Если нет файлов без 'b' - пропустить всю группу
        if not files_without_b:
            if files_with_b:
                print(f"  ⚠️  Группа '{normalized_name}': все файлы с 'b', исключены:")
                for f in files_with_b:
                    size_kb = os.path.getsize(f) / 1024
                    print(f"    ✗ {os.path.basename(f)} ({size_kb:.1f} KB)")
            continue

        # Работать только с файлами без 'b'
        if len(files_without_b) > 1:
            # Есть дубли - выбрать самый большой файл без 'b'
            best_file = max(files_without_b, key=lambda f: os.path.getsize(f))
            result.append(best_file)
            duplicates_removed += len(files_without_b) - 1

            # Вывести информацию о дублях
            print(f"  Дубли для '{normalized_name}':")
            for f in sorted(files_without_b, key=lambda x: os.path.getsize(x), reverse=True):
                size_kb = os.path.getsize(f) / 1024
                marker = "✓" if f == best_file else "✗"
                print(f"    {marker} {os.path.basename(f)} ({size_kb:.1f} KB)")

            # Показать исключённые файлы с 'b'
            if files_with_b:
                for f in files_with_b:
                    size_kb = os.path.getsize(f) / 1024
                    print(f"    ✗ {os.path.basename(f)} ({size_kb:.1f} KB) [содержит 'b']")
        else:
            # Уникальный файл без 'b'
            result.append(files_without_b[0])

            # Если есть версии с 'b' - показать что они исключены
            if files_with_b:
                print(f"  Файл '{normalized_name}':")
                size_kb = os.path.getsize(files_without_b[0]) / 1024
                print(f"    ✓ {os.path.basename(files_without_b[0])} ({size_kb:.1f} KB)")
                for f in files_with_b:
                    size_kb = os.path.getsize(f) / 1024
                    print(f"    ✗ {os.path.basename(f)} ({size_kb:.1f} KB) [содержит 'b']")
                b_files_removed += len(files_with_b)

    if b_files_removed > 0:
        print(f"\n⚠️  Исключено {b_files_removed} файл(ов) с буквой 'b'")
    if duplicates_removed > 0:
        print(f"⚠️  Удалено {duplicates_removed} дубл(ей)\n")

    return sorted(result, key=natural_sort_key)

def load_font(size):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except:
            return ImageFont.load_default()

def draw_label(draw, x, y, w, h, text):
    pad = max(2, int(round(min(w, h) * 0.02)))
    size = max(12, int(round(min(w, h) * 0.10)))
    font = load_font(size)
    def textbbox_size(s):
        try:
            b = draw.textbbox((0, 0), s, font=font)
            return b[2] - b[0], b[3] - b[1]
        except:
            return draw.textsize(s, font=font)
    maxw = w - 2*pad
    tw, th = textbbox_size(text)
    while tw > maxw and size > 10:
        size -= 1
        font = load_font(size)
        tw, th = textbbox_size(text)
    if tw > maxw:
        ell = '…'
        for i in range(len(text), 0, -1):
            t = text[:i] + ell
            tw, th = textbbox_size(t)
            if tw <= maxw:
                text = t; break
        else:
            text = ell; tw, th = textbbox_size(text)
    tx = x + (w - tw)//2
    ty = y + h - th - pad
    draw.text((tx, ty), text, font=font, fill=(255,255,255),
              stroke_width=max(1, size//12), stroke_fill=(0,0,0))

def create_collage(files, cols, tile, gap):
    """Создать один коллаж из списка файлов"""
    n = len(files)
    rows = math.ceil(n / cols)
    W = cols * tile + (cols-1) * gap
    H = rows * tile + (rows-1) * gap
    canvas = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(canvas)

    for idx, path in enumerate(files):
        r, c = divmod(idx, cols)
        x = c * (tile + gap)
        y = r * (tile + gap)
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            im = ImageOps.fit(im, (tile, tile), method=Image.LANCZOS)
        canvas.paste(im, (x, y))
        caption = normalize_caption(path)
        draw_label(draw, x, y, tile, tile, caption)

    return canvas

def main():
    # Создать output директорию
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    # Найти все фото
    files = list_images(INPUT_DIR)
    if not files:
        print(f"❌ В папке {INPUT_DIR} нет изображений")
        return

    print(f"Найдено {len(files)} фото")

    # Удалить дубли (оставить файлы с большим размером)
    files = remove_duplicates(files)

    print(f"Осталось {len(files)} уникальных фото для обработки")

    # Разбить на батчи по GRID_SIZE x GRID_SIZE
    images_per_collage = GRID_SIZE * GRID_SIZE
    total_collages = math.ceil(len(files) / images_per_collage)

    print(f"Создаём {total_collages} коллаж(а) по {GRID_SIZE}x{GRID_SIZE}...\n")

    for i in range(total_collages):
        start = i * images_per_collage
        end = min(start + images_per_collage, len(files))
        batch = files[start:end]

        # Выбрать оптимальное количество колонок
        if len(batch) == images_per_collage:
            # Полный коллаж - используем GRID_SIZE
            cols = GRID_SIZE
        elif len(batch) <= 4:
            # Для малого количества фото - квадратная или линейная сетка
            cols = min(len(batch), 2)
        else:
            # Для остальных - используем GRID_SIZE для консистентности
            cols = GRID_SIZE

        print(f"Коллаж {i+1}/{total_collages}: {len(batch)} фото → {cols}x{math.ceil(len(batch)/cols)}")

        # Создать коллаж
        canvas = create_collage(batch, cols, TILE_SIZE, GAP)

        # Сохранить
        output_file = f"{OUTPUT_DIR}/collage_{i+1}.jpg"
        canvas.save(output_file, quality=95)
        print(f"  ✓ {output_file}\n")

    print(f"✅ Готово! Создано {total_collages} коллаж(а) в {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()
