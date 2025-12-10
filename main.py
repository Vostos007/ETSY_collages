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
# Название коллекции (если пусто — попытаемся определить из имён файлов)
YARN_NAME = "DROPS Nepal"
# Доп. маркировка: цвета с низким остатком (оставьте пустым множеством, если не нужно)
LOW_STOCK_CODES = set()
LOW_STOCK_BADGE_TEXT = "For Contrast color only"

def parse_file_info(path):
    """Извлечь из имени: коллекцию, номер для подписи, ключ группировки.

    Пример: 'Kremke-Babyalpaka-10114.jpg' ->
      collection='Kremke Babyalpaka', number='10114', caption='10114'
    """
    stem = os.path.splitext(os.path.basename(path))[0]
    stem = stem[:-2] if stem.endswith('-2') else stem
    parts = re.split(r'[-_]+', stem)
    ident = None
    # выбрать последнюю чисто цифровую часть, иначе последнее звено
    for p in reversed(parts):
        if p.isdigit():
            ident = p
            break
    if ident is None and parts:
        ident = parts[-1]
    # коллекция — всё до идентификатора, если он последний элемент
    if ident and parts and parts[-1] == ident:
        coll_parts = parts[:-1]
    else:
        coll_parts = [p for p in parts if p != ident] if ident else parts
    collection = ' '.join(coll_parts).strip() or stem
    if ident and ident.isdigit():
        caption = ident.lstrip('0') or ident
    else:
        caption = ident or stem
    group_key = (collection.lower(), caption.lower())
    return {
        "collection": collection or stem,
        "number": ident,
        "caption": caption,
        "group_key": group_key,
    }


def derive_yarn_name(files):
    """Определить имя коллекции по самым частым префиксам."""
    from collections import Counter
    coll = [parse_file_info(p)["collection"] for p in files if parse_file_info(p)["collection"]]
    if not coll:
        return ""
    return Counter(coll).most_common(1)[0][0]

def natural_sort_key(path):
    """Естественная сортировка: 1, 2, 10 вместо 1, 10, 2"""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', os.path.basename(path))]

def normalize_caption(filename):
    """Извлечь короткую подпись: последняя числовая группа или stem."""
    return parse_file_info(filename)["caption"]

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
    """Удалить дубли: группируем по (collection, number) чтобы разные серии не смешивались."""
    groups = {}
    for filepath in files:
        key = parse_file_info(filepath)["group_key"]
        groups.setdefault(key, []).append(filepath)

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
    """Подбирать читаемый шрифт: пробуем полужирные варианты, fallback — DejaVuSans."""
    candidates = [
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSText.ttf",
        "Arial.ttf",
        "DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

def draw_label(draw, x, y, w, h, text):
    pad = max(3, int(round(min(w, h) * 0.025)))
    size = max(18, int(round(min(w, h) * 0.16)))
    font = load_font(size)
    def textbbox_size(s):
        try:
            b = draw.textbbox((0, 0), s, font=font)
            return b[2] - b[0], b[3] - b[1]
        except:
            return draw.textsize(s, font=font)
    maxw = w - 2*pad
    tw, th = textbbox_size(text)
    while tw > maxw and size > 12:
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

    # Полупрозрачная светло-серая подложка, чтобы не перекрывать фото
    bg_h = th + pad*2
    try:
        from PIL import Image
        overlay = Image.new('RGBA', (w, bg_h), (245, 245, 245, 140))
        draw.im.paste(overlay, (x, y + h - bg_h), overlay)
    except Exception:
        # fallback: тонкая линия без заливки
        draw.rectangle([x, y + h - bg_h, x + w, y + h], outline=(220,220,220))

    tx = x + (w - tw)//2
    ty = y + h - th - pad - 6  # ~2 мм при 72-96 dpi
    draw.text((tx, ty), text, font=font, fill=(20,20,20),
              stroke_width=max(1, size//14), stroke_fill=(245,245,245))

def create_collage(files, cols, tile, gap, yarn_name=""):
    """Создать один коллаж из списка файлов"""
    n = len(files)
    rows = math.ceil(n / cols)
    header_h = 0
    if yarn_name:
        header_h = max(40, int(tile * 0.15))

    W = cols * tile + (cols-1) * gap
    H = header_h + rows * tile + (rows-1) * gap
    canvas = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(canvas)

    if header_h:
        bar_color = (245, 245, 245)
        draw.rectangle([0, 0, W, header_h], fill=bar_color)
        font = load_font(max(24, header_h // 2))
        text = yarn_name
        # совместимость разных версий Pillow
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            try:
                tw, th = draw.textsize(text, font=font)
            except Exception:
                tw, th = font.getsize(text)
        tx = (W - tw) // 2
        ty = (header_h - th) // 2
        draw.text((tx, ty), text, font=font, fill=(0, 0, 0))

    for idx, path in enumerate(files):
        r, c = divmod(idx, cols)
        x = c * (tile + gap)
        y = header_h + r * (tile + gap)
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            im = ImageOps.fit(im, (tile, tile), method=Image.LANCZOS)
        canvas.paste(im, (x, y))
        caption = normalize_caption(path)
        draw_label(draw, x, y, tile, tile, caption)

        # Низкий остаток — добавить бейдж
        if caption in LOW_STOCK_CODES:
            badge_h = max(30, tile // 8)
            badge_w = min(tile, int(tile * 0.9))
            bx = x + (tile - badge_w) // 2
            by = y + tile - badge_h - bg_offset if (bg_offset := 0) else y + tile - badge_h
            try:
                badge = Image.new('RGBA', (badge_w, badge_h), (230, 230, 230, 180))
                draw.im.paste(badge, (bx, by), badge)
            except Exception:
                draw.rectangle([bx, by, bx + badge_w, by + badge_h], fill=(230,230,230), outline=None)

            bfont = load_font(max(14, badge_h // 2))
            btext = LOW_STOCK_BADGE_TEXT
            try:
                bbox = draw.textbbox((0, 0), btext, font=bfont)
                btw, bth = bbox[2] - bbox[0], bbox[3] - bbox[1]
            except Exception:
                btw, bth = draw.textsize(btext, font=bfont)
            btx = bx + (badge_w - btw)//2
            bty = by + (badge_h - bth)//2
            draw.text((btx, bty), btext, font=bfont, fill=(20,20,20))

    return canvas

def main():
    # Создать output директорию
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    # Найти все фото
    files = list_images(INPUT_DIR)
    if not files:
        print(f"❌ В папке {INPUT_DIR} нет изображений")
        return

    yarn_name = YARN_NAME or derive_yarn_name(files)

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
        canvas = create_collage(batch, cols, TILE_SIZE, GAP, yarn_name)

        # Сохранить
        output_file = f"{OUTPUT_DIR}/collage_{i+1}.jpg"
        canvas.save(output_file, quality=95)
        print(f"  ✓ {output_file}\n")

    print(f"✅ Готово! Создано {total_collages} коллаж(а) в {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()
