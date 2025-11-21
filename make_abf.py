import csv
from pathlib import Path
from fontTools.ttLib.ttFont import TTFont
from PIL import Image, ImageDraw, ImageFont


font_size = 24

def modify_font_preserve_structure(original_abf_path, original_png_path, char_list, output_abf_path, output_png_path,
                                   font_path):
    """
    修改原始 ABF 和 PNG 文件，保持原始文件结构不变
    """

    # 读取原始文件
    with open(original_abf_path, "rb") as f:
        original_abf = bytearray(f.read())

    original_image = Image.open(original_png_path).convert("RGBA")
    new_image = original_image.copy()
    draw = ImageDraw.Draw(new_image)

    # 获取图片尺寸
    img_width, img_height = new_image.size
    print(f"Image size: {img_width}x{img_height}")

    # 加载新字体
    new_font = ImageFont.truetype(font_path, font_size)

    # 找到 body 开始位置
    body_start_pos = 0
    pos = 0
    while pos < len(original_abf):
        try:
            header_str = original_abf[pos:pos + 8].decode("utf-8")
            if header_str == "BFNTCBLK":
                body_start_pos = pos + 16
                break
        except:
            pass
        pos += 1

    print(f"Body starts at: 0x{body_start_pos:X}")

    # 解析原始字符数据并按行列坐标排序
    char_data = []
    pos = body_start_pos

    while pos < len(original_abf):
        # 检查是否到达文件尾
        if pos + 8 <= len(original_abf):
            try:
                possible_end = original_abf[pos:pos + 8].decode("utf-8", errors='ignore')
                if "GENEEOF" in possible_end:
                    break
            except:
                pass

        # 读取字符段 (32字节)
        if pos + 32 > len(original_abf):
            break

        unicode_bytes = original_abf[pos:pos + 4]
        try:
            original_char = chr(int.from_bytes(unicode_bytes, 'big'))

            # 提取所有属性
            column = int.from_bytes(original_abf[pos + 4:pos + 6], 'big')
            row = int.from_bytes(original_abf[pos + 6:pos + 8], 'big')
            width = int.from_bytes(original_abf[pos + 8:pos + 10], 'big')
            height = int.from_bytes(original_abf[pos + 10:pos + 12], 'big')

            # 提取Left Margin和Text Space字段
            left_margin = int.from_bytes(original_abf[pos + 12:pos + 14], 'big')
            text_space = int.from_bytes(original_abf[pos + 16:pos + 18], 'big')

            # 检查边界：确保字符位置在图片范围内
            if (column >= 0 and row >= 0 and
                    column + width <= img_width and
                    row + height <= img_height):

                char_data.append({
                    'file_position': pos,
                    'original_char': original_char,
                    'column': column,
                    'row': row,
                    'width': width,
                    'height': height,
                    'left_margin': left_margin,
                    'text_space': text_space,
                    'segment_data': bytearray(original_abf[pos:pos + 32])
                })
            else:
                print(
                    f"Warning: Character '{original_char}' at position ({column}, {row}) with size {width}x{height} is out of bounds")

        except:
            # 跳过无效字符
            pass

        pos += 32

    print(f"Found {len(char_data)} valid characters in original ABF (after boundary check)")

    # 按行列坐标排序（先按行，再按列）
    char_data.sort(key=lambda x: (x['row'], x['column']))

    # 分析行分布，找到第一行和第二行的分界
    rows = sorted(set(char_info['row'] for char_info in char_data))
    print(f"Available rows: {rows}")

    # 直接跳过第一行，只使用第二行及以后的位置
    first_row = rows[0]
    second_row = rows[1]
    print(f"Skipping first row: {first_row}, Using rows from: {second_row}")

    # 只保留第二行及以后的字符
    usable_char_data = [char_info for char_info in char_data if char_info['row'] >= second_row]
    skipped_char_data = [char_info for char_info in char_data if char_info['row'] == first_row]

    print(f"Skipped first row characters: {len(skipped_char_data)}")
    print(f"Usable characters (from second row): {len(usable_char_data)}")

    # 创建新的ABF文件（完全复制原始文件，后面再修改）
    new_abf = bytearray(original_abf)

    # 用于记录已使用的 Unicode 码点，避免重复
    used_unicode_points = set()

    # 第一阶段：为每个新字符寻找合适的位置（只使用第二行及以后的位置）
    print(f"\nMatching {len(char_list)} characters to suitable slots (first row skipped)...")

    matched_slots = []
    used_slots = set()

    for new_char in char_list:
        # 获取新字符的预估尺寸
        try:
            bbox = new_font.getbbox(new_char)
            left, top, right, bottom = bbox
            estimated_width = right - left
            estimated_height = bottom - top
        except:
            estimated_width = font_size
            estimated_height = font_size

        # 寻找合适的位置（只在使用第二行及以后的位置中寻找）
        best_slot_index = -1

        for i, char_info in enumerate(usable_char_data):
            if i in used_slots:
                continue

            # 检查尺寸是否合适且不会超出边界
            char_width = char_info['width']
            char_height = char_info['height']
            column = char_info['column']
            row = char_info['row']

            # 计算实际绘制后的边界
            actual_right = column + char_info['left_margin'] + estimated_width - left
            actual_bottom = row + char_height

            if (char_width >= estimated_width + 2 and
                    char_height >= estimated_height + 2 and
                    actual_right <= img_width and
                    actual_bottom <= img_height):
                best_slot_index = i
                break

        # 如果没找到完全合适的，放宽条件
        if best_slot_index == -1:
            for i, char_info in enumerate(usable_char_data):
                if i in used_slots:
                    continue

                char_width = char_info['width']
                char_height = char_info['height']
                column = char_info['column']
                row = char_info['row']
                actual_right = column + char_info['left_margin'] + estimated_width - left
                actual_bottom = row + char_height

                if (char_width >= estimated_width and
                        char_height >= estimated_height and
                        actual_right <= img_width and
                        actual_bottom <= img_height):
                    best_slot_index = i
                    break

        # 如果还是没找到，使用第一个不会超界的可用位置
        if best_slot_index == -1:
            for i, char_info in enumerate(usable_char_data):
                if i in used_slots:
                    continue

                char_width = char_info['width']
                char_height = char_info['height']
                column = char_info['column']
                row = char_info['row']
                actual_right = column + char_info['left_margin'] + estimated_width - left
                actual_bottom = row + char_height

                if actual_right <= img_width and actual_bottom <= img_height:
                    best_slot_index = i
                    break

        if best_slot_index != -1:
            matched_slots.append((usable_char_data[best_slot_index], new_char))
            used_slots.add(best_slot_index)
            print(f"Matched '{new_char}' to slot {best_slot_index + 1}")
        else:
            print(f"Warning: No suitable slot found for character '{new_char}'")

    # 第二阶段：替换使用的字符
    print(f"\nReplacing {len(matched_slots)} characters with simple drawing method...")
    final_chars = []
    for char_info, new_char in matched_slots:
        final_chars.append(new_char)
        new_unicode = ord(new_char)

        print(f"Replacing '{char_info['original_char']}' with '{new_char}'")

        # 1. 修改ABF：只替换 Unicode 码点
        file_pos = char_info['file_position']
        new_unicode_bytes = new_unicode.to_bytes(4, 'big')
        new_abf[file_pos:file_pos + 4] = new_unicode_bytes
        used_unicode_points.add(new_unicode)

        # 2. 修改 PNG：在原始位置绘制新字符
        column = char_info['column']
        row = char_info['row']
        width = char_info['width']
        height = char_info['height']
        # left_margin = char_info['left_margin']

        # 彻底清除原始区域（扩大清理范围）
        clean_left = max(0, column - 1)
        clean_top = max(0, row - 1)
        clean_right = min(img_width, column + width + 1)
        clean_bottom = min(img_height, row + height + 1)
        draw.rectangle([clean_left, clean_top, clean_right, clean_bottom], fill=(0, 0, 0, 0))

        # 获取新字符的bbox
        bbox = new_font.getbbox(new_char)
        left, top, right, bottom = bbox
        char_width = right - left
        char_height_actual = bottom - top

        x_offset = column
        y_offset = row - 2

        # 最终边界检查
        if (x_offset + char_width <= img_width and
                y_offset + char_height_actual <= img_height and
                x_offset >= 0 and y_offset >= 0):

            # 直接绘制字符
            draw.text((x_offset, y_offset), new_char, fill=(255, 255, 255, 255), font=new_font)
            print(f"  Drawn at: x={x_offset}, y={y_offset}")
        else:
            print(f"  Warning: Character '{new_char}' would be drawn out of bounds at ({x_offset}, {y_offset})")

    print(f"final_chars: \n{final_chars}")

    # 第三阶段：处理未使用的字符位置（包括第一行和未使用的第二行及以后的位置）
    print(f"\nProcessing unused character slots...")

    # 处理未使用的第二行及以后的位置
    unused_usable_count = len(usable_char_data) - len(used_slots)
    print(f"Unused slots from second row: {unused_usable_count}")

    next_unicode = 0xE000
    for i, char_info in enumerate(usable_char_data):
        if i in used_slots:
            continue

        file_pos = char_info['file_position']
        while next_unicode in used_unicode_points:
            next_unicode += 1

        new_unicode_bytes = next_unicode.to_bytes(4, 'big')
        new_abf[file_pos:file_pos + 4] = new_unicode_bytes
        used_unicode_points.add(next_unicode)
        next_unicode += 1

        # 清除未使用的位置
        column = char_info['column']
        row = char_info['row']
        width = char_info['width']
        height = char_info['height']
        clean_left = max(0, column - 1)
        clean_top = max(0, row - 1)
        clean_right = min(img_width, column + width + 1)
        clean_bottom = min(img_height, row + height + 1)
        draw.rectangle([clean_left, clean_top, clean_right, clean_bottom], fill=(0, 0, 0, 0))

    # 第一行的字符全部清除并标记为未使用
    if len(rows) > 1:
        first_row = rows[0]
        first_row_chars = [char_info for char_info in char_data if char_info['row'] == first_row]
        print(f"Clearing first row: {len(first_row_chars)} characters")

        for char_info in first_row_chars:
            file_pos = char_info['file_position']
            while next_unicode in used_unicode_points:
                next_unicode += 1

            new_unicode_bytes = next_unicode.to_bytes(4, 'big')
            new_abf[file_pos:file_pos + 4] = new_unicode_bytes
            used_unicode_points.add(next_unicode)
            next_unicode += 1

            # 清除第一行的位置
            column = char_info['column']
            row = char_info['row']
            width = char_info['width']
            height = char_info['height']
            clean_left = max(0, column - 1)
            clean_top = max(0, row - 1)
            clean_right = min(img_width, column + width + 1)
            clean_bottom = min(img_height, row + height + 1)
            draw.rectangle([clean_left, clean_top, clean_right, clean_bottom], fill=(0, 0, 0, 0))

    # 验证文件大小不变
    if len(new_abf) != len(original_abf):
        print(f"Warning: File size changed! Original: {len(original_abf)}, New: {len(new_abf)}")
        if len(new_abf) > len(original_abf):
            new_abf = new_abf[:len(original_abf)]
        else:
            new_abf.extend(b'\x00' * (len(original_abf) - len(new_abf)))
    else:
        print(f"File size preserved: {len(new_abf)} bytes")

    # 保存文件
    with open(output_abf_path, "wb") as f:
        f.write(new_abf)

    Path(output_png_path.parent).mkdir(parents=True, exist_ok=True)
    new_image.save(output_png_path)

    print(f"\nSuccessfully created:")
    print(f"  ABF: {output_abf_path}")
    print(f"  PNG: {output_png_path}")
    print(f"Replaced {len(matched_slots)} characters, first row skipped and cleared")

    return True


def parse_use_chars():
    all_chars = []
    folder = Path("scripts/extract")
    for csv_file in folder.glob("*.csv"):
        try:
            with open(csv_file, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 3:
                        text = row[1].strip()
                        trans_text = row[2].strip()
                        if trans_text:
                            text = trans_text

                        if text:
                            all_chars.extend(list(text.replace('@n', '\n')))
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")

    folder = Path("gop_data/extract")
    for csv_file in folder.glob("*.csv"):
        try:
            with open(csv_file, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 3:
                        text = row[1].strip()
                        trans_text = row[2].strip()
                        if trans_text:
                            text = trans_text

                        if text:
                            all_chars.extend(list(text.replace('@n', '\n')))
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")

    return all_chars


if __name__ == "__main__":
    # 配置参数
    ORIGINAL_ABF = "font/origin/font_j24x24.abf"
    ORIGINAL_PNG = "font/origin/font_j24x24_0.png"
    NEW_FONT = "font/ttf/WenQuanDengKuanWeiMiHei.ttf"
    OUTPUT_ABF = "font_j24x24.abf"
    OUTPUT_PNG = "images/modified/font/font_j24x24/font_j24x24_0.png"

    all_chars = parse_use_chars()

    # 去重并排序
    char_list = sorted(set(all_chars))
    print(f"Characters: {char_list}")
    print(f"Characters to replace: {len(char_list)}")

    # 检查字体支持
    font = TTFont(NEW_FONT)
    support_chars = set(ch for ch, _ in font["cmap"].getBestCmap().items())
    supported_chars = [char for char in char_list if ord(char) in support_chars]
    print(f"Supported characters: {len(supported_chars)}")

    # 执行修改
    modify_font_preserve_structure(
        ORIGINAL_ABF,
        ORIGINAL_PNG,
        supported_chars,
        OUTPUT_ABF,
        OUTPUT_PNG,
        NEW_FONT
    )