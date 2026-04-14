import os
import csv
import sys
from pathlib import Path
from fontTools.ttLib.ttFont import TTFont
from PIL import Image, ImageDraw, ImageFont

font_size = 23

hold_chars = (
    ' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}'
    '~§¨®°±´¶×÷ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩαβγδεζηθικλμνξοπρστυφχψωЁАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгд'
    'ежзийклмнопрстуфхцчшщъыьэюяё‐―‘’“”†‡‥…‰′″※℃№℡™ÅⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ←↑→↓⇒⇔∀∂∃∇∈∋∑√∝∞∟∠∥∧∨∩∪∫∬∮∴∵∽≒≠≡'
    '≦≧≪≫⊂⊃⊆⊇⊥⊿⌒①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳─━│┃┌┏┐┓└┗┘┛├┝┠┣┤┥┨┫┬┯┰┳┴┷┸┻┼┿╂╋■□▲△▼▽◆◇○◎●◯★☆♀♂♥♪♭♯　、。〃'
    '々〆〇〈〉《》「」『』【】〒〓〔〕'
    '〝〟ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽ'
    'まみむめもゃやゅゆょよらりるれろゎわゐゑをん゛゜ゝゞァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅ'
    'テデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワヰヱヲンヴヵヶ・ーヽヾ'
    '㈱㈲㈹㊤㊥㊦㊧㊨㌃㌍㌔㌘㌢㌣㌦㌧㌫㌶㌻㍉㍊㍍㍑㍗㍻㍼㍽㍾㎎㎏㎜㎝㎞㎡㏄㏍'
    '！＃＄％＆（）＊＋，－．／０１２３４５６７８９：；＜＝＞？＠ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ［＼］＾＿｀'
    'ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ｛｜｝～￠￡￢￣￥\n'
)

redraw_chars = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ")

replace_char = {
    "ａ": "a", "ｂ": "b", "ｃ": "c", "ｄ": "d", "ｅ": "e", "ｆ": "f", "ｇ": "g", "ｈ": "h", "ｉ": "i", "ｊ": "j",
    "ｋ": "k", "ｌ": "l", "ｍ": "m", "ｎ": "n", "ｏ": "o", "ｐ": "p", "ｑ": "q", "ｒ": "r", "ｓ": "s", "ｔ": "t",
    "ｕ": "u", "ｖ": "v", "ｗ": "w", "ｘ": "x", "ｙ": "y", "ｚ": "z",

    "Ａ": "A", "Ｂ": "B", "Ｃ": "C", "Ｄ": "D", "Ｅ": "E", "Ｆ": "F", "Ｇ": "G", "Ｈ": "H", "Ｉ": "I", "Ｊ": "J",
    "Ｋ": "K", "Ｌ": "L", "Ｍ": "M", "Ｎ": "N", "Ｏ": "O", "Ｐ": "P", "Ｑ": "Q", "Ｒ": "R", "Ｓ": "S", "Ｔ": "T",
    "Ｕ": "U", "Ｖ": "V", "Ｗ": "W", "Ｘ": "X", "Ｙ": "Y", "Ｚ": "Z",
}


def half_to_full(text):
    result = []
    for char in text:
        code = ord(char)
        if char == '·':
            result.append('・')
        elif 33 <= code <= 126:
            result.append(chr(code + 65248))
        elif code == 32:
            result.append(chr(12288))
        else:
            result.append(char)
    return ''.join(result)


def modify_font_preserve_structure(
        original_abf_path, original_png_path,
        char_list, output_abf_path, output_png_path,
        font_path, x_off, y_off, holder_char
):
    """
    修改原始 ABF 和 PNG 文件，保持原始文件结构不变
    """

    with open(original_abf_path, "rb") as f:
        original_abf = bytearray(f.read())

    original_image = Image.open(original_png_path).convert("RGBA")
    new_image = original_image.copy()
    draw = ImageDraw.Draw(new_image)

    img_width, img_height = new_image.size
    print(f"Image size: {img_width}x{img_height}")

    new_font = ImageFont.truetype(font_path, font_size)

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

    char_data = []
    pos = body_start_pos

    min_char_data = []
    redraw_char_data = []

    while pos < len(original_abf):
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

            entry_info = {
                'file_position': pos,
                'original_char': original_char,
                'column': column,
                'row': row,
                'width': width,
                'height': height,
                'left_margin': left_margin,
                'text_space': text_space,
                'segment_data': bytearray(original_abf[pos:pos + 32])
            }

            if original_char in redraw_chars:
                pos += 32
                print(f"Redraw -> min width: {width} => {original_char}")
                redraw_char_data.append(entry_info)
                continue

            if holder_char and original_char in hold_chars:
                pos += 32
                continue

            if width < 23:
                pos += 32
                print(f"min width: {width} => {original_char}")
                min_char_data.append(entry_info)
                continue

            # 检查边界：确保字符位置在图片范围内
            if (column >= 0 and row >= 0 and
                    column + width <= img_width and
                    row + height <= img_height):

                char_data.append(entry_info)
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

    usable_char_data = char_data

    # 创建新的ABF文件（完全复制原始文件，后面再修改）
    new_abf = bytearray(original_abf)

    # 用于记录已使用的 Unicode 码点，避免重复
    used_unicode_points = []

    print(f"\nMatching {len(char_list)} characters to suitable slots (first row skipped)...")

    matched_slots = []
    used_slots = set()

    now_index = 0

    for new_char in char_list:
        used_slots.add(now_index)
        matched_slots.append((usable_char_data[now_index], new_char))
        use_char = usable_char_data[now_index]
        print(
            f"Matched '{new_char}' to slot {now_index + 1} => {use_char['original_char']} , width: {use_char['width']} , height: {use_char['height']}")
        now_index += 1

    def draw_char(char_info, draw_char, is_redraw=False):
        column = char_info['column']
        row = char_info['row']
        width = char_info['width']
        height = char_info['height']
        # left_margin = char_info['left_margin']

        # 彻底清除原始区域（扩大清理范围）
        clean_left = max(0, column)
        clean_top = max(0, row)
        clean_right = min(img_width, column + width)
        # if is_redraw:
        #     clean_right += 2
        clean_bottom = min(img_height, row + height + 1)
        draw.rectangle([clean_left, clean_top, clean_right, clean_bottom], fill=(0, 0, 0, 0))

        # 获取新字符的bbox
        # bbox = new_font.getbbox(new_char)
        # left, top, right, bottom = bbox
        # char_width = right - left
        # char_height_actual = bottom - top

        # x_offset = column - x_off
        # y_offset = row - y_off

        if is_redraw:
            draw_char = replace_char.get(draw_char, draw_char)

        center_x = column - x_off + width // 2
        if is_redraw:
            offset = 0

            if draw_char == "g" or draw_char == 'j':
                offset = 2
            elif draw_char == "Q":
                offset = 1

            center_x = column + offset + width // 2
        else:
            if choose_font == "ResourceHan":
                if draw_char == '不':
                    center_x -= 2
                elif draw_char == '下':
                    center_x -= 2

        center_y = row - y_off + height // 2
        if is_redraw:
            if choose_font == "ResourceHan":
                offset = 2
                if draw_char == "g" or draw_char == 'j':
                    offset = 4
                elif draw_char == "Q":
                    offset = 3
                center_y = row - offset + height // 2
            else:
                offset = 1
                if draw_char == "g" or draw_char == 'j':
                    offset = 3
                # elif draw_char == "Q":
                #     offset = 3
                center_y = row - offset + height // 2

        # 使用 anchor='mm' 让字符中心对齐到指定点
        draw.text((center_x, center_y), draw_char, fill=(255, 255, 255, 255),
                  font=new_font, anchor='mm')
        print(f"  Drawn at: x={center_x}, y={center_y}")

    # Replace chars
    print(f"\nReplacing {len(matched_slots)} characters with simple drawing method...")
    final_chars = []
    for char_info, new_char in matched_slots:
        final_chars.append(new_char)
        new_unicode = ord(new_char)

        print(f"Replacing '{char_info['original_char']}' with '{new_char}'")

        # 只替换 Unicode 码点
        file_pos = char_info['file_position']
        new_unicode_bytes = new_unicode.to_bytes(4, 'big')
        new_abf[file_pos:file_pos + 4] = new_unicode_bytes
        used_unicode_points.append(new_unicode)

        draw_char(char_info, new_char)

    # Redraw Chars
    for char_info in redraw_char_data:
        original_char = char_info['original_char']
        print(f"Redraw => {original_char}")
        draw_char(char_info, original_char, True)

    print(f"\nfinal_chars: \n{final_chars}")

    # Clear chars
    print(f"\nProcessing unused character slots...")

    next_unicode = 0xE000
    usable_char_data += min_char_data
    for i, char_info in enumerate(usable_char_data):
        if i in used_slots:
            continue

        file_pos = char_info['file_position']
        while next_unicode in used_unicode_points:
            next_unicode += 1

        new_unicode_bytes = next_unicode.to_bytes(4, 'big')
        new_abf[file_pos:file_pos + 4] = new_unicode_bytes
        used_unicode_points.append(next_unicode)
        next_unicode += 1

        column = char_info['column']
        row = char_info['row']
        width = char_info['width']
        height = char_info['height']
        clean_left = max(0, column - 2)
        clean_top = max(0, row - 2)
        clean_right = min(img_width, column + width - 1)
        clean_bottom = min(img_height, row + height + 1)
        draw.rectangle([clean_left, clean_top, clean_right, clean_bottom], fill=(0, 0, 0, 0))

    if len(new_abf) != len(original_abf):
        print(f"Warning: File size changed! Original: {len(original_abf)}, New: {len(new_abf)}")
        if len(new_abf) > len(original_abf):
            new_abf = new_abf[:len(original_abf)]
        else:
            new_abf.extend(b'\x00' * (len(original_abf) - len(new_abf)))
    else:
        print(f"File size preserved: {len(new_abf)} bytes")

    with open(output_abf_path, "wb") as f:
        f.write(new_abf)

    Path(output_png_path).parent.mkdir(parents=True, exist_ok=True)
    new_image.save(output_png_path)

    print(f"\nSuccessfully created:")
    print(f"  ABF: {output_abf_path}")
    print(f"  PNG: {output_png_path}")
    print(f"Replaced {len(matched_slots)} characters, first row skipped and cleared")

    return True


def parse_use_chars(holder_chars):
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

                        if not holder_chars:
                            text = half_to_full(text)
                            trans_text = half_to_full(trans_text)

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

                        if not holder_chars:
                            text = half_to_full(text)
                            trans_text = half_to_full(trans_text)

                        if trans_text:
                            text = trans_text

                        if text:
                            all_chars.extend(list(text.replace('@n', '\n')))
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")

    return all_chars


font_config = {
    "WenQuan": {
        "ttf": "font/ttf/WenQuanDengKuanWeiMiHei.ttf",
        "x_offset": 0,
        "y_offset": 2,
        "holder_char": False
    },

    "ResourceHan": {
        "ttf": "font/ttf/ResourceHanRoundedCN-Normal.ttf",
        "x_offset": 0,
        "y_offset": 2,
        "holder_char": True
    }
}

choose_font = "ResourceHan"

if __name__ == "__main__":
    try:
        output_dir = sys.argv[1]
    except Exception:
        output_dir = "images/modified/font/font_j24x24"

    ORIGINAL_ABF = "font/origin/font_j24x24.abf"
    ORIGINAL_PNG = "font/origin/font_j24x24_0.png"
    font_info = font_config[choose_font]
    NEW_FONT = font_info["ttf"]
    OUTPUT_ABF = os.path.join(output_dir, "font_j24x24.abf")
    OUTPUT_PNG = "images/modified/font/font_j24x24/font_j24x24_0.png"

    need_holder_char = font_info["holder_char"]

    all_chars = parse_use_chars(need_holder_char)

    char_list = sorted(set(all_chars) - set(hold_chars if need_holder_char else []))
    print(f"Characters: {char_list}")
    print(f"Characters to replace: {len(char_list)}")

    # 检查字体支持
    font = TTFont(NEW_FONT)
    support_chars = set(ch for ch, _ in font["cmap"].getBestCmap().items())
    supported_chars = [char for char in char_list if ord(char) in support_chars]
    print(f"Supported characters: {len(supported_chars)}")

    modify_font_preserve_structure(
        ORIGINAL_ABF,
        ORIGINAL_PNG,
        supported_chars,
        OUTPUT_ABF,
        OUTPUT_PNG,
        NEW_FONT,
        font_info["x_offset"],
        font_info["y_offset"],
        need_holder_char
    )
