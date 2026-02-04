import os
import re
import sys
import csv
import sys
import glob
import shutil
from pathlib import Path
from make_abf import font_config, choose_font, half_to_full

break_line_char = "@n"

need_holder_chars = font_config[choose_font]["holder_char"]

ignore_file = "talkanagram"


def is_alpha_underscore(text):
    """
    判断字符串是否只包含大小写字母和下划线
    """
    return bool(re.match(r'^[a-zA-Z_]+$', text))


def parse_gop_file(file_path):
    """
    解析GOP文件，提取字符串和文件结构信息
    """
    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        # 检查文件头
        if not data.startswith(b'GOP GFIN'):
            print(f"警告: {file_path} 不是有效的GOP文件")
            return None, None, None

        # 查找GENESTRT位置
        genestrt_pos = data.find(b'GENESTRT')
        if genestrt_pos == -1:
            print(f"警告: {file_path} 中未找到GENESTRT")
            return None, None, None

        # 查找GOP GDAT位置
        gop_gdat_pos = data.find(b'GOP GDAT')
        if gop_gdat_pos == -1:
            print(f"警告: {file_path} 中未找到GOP GDAT")
            return None, None, None

        # 字符串指针表 开始, 结束 offset
        table_start_point = genestrt_pos + 16
        table_end_point = table_start_point + int.from_bytes(
            data[table_start_point + 8:table_start_point + 12], "little"
        )
        # 字符传指针表数据
        string_points_table_data = data[table_start_point + 16:table_end_point]

        # 提取字符串区域
        extracted_data = data[table_end_point:gop_gdat_pos]

        # 从指针表提取字符串
        strings_with_offset = []
        for i in range(0, len(string_points_table_data), 4):
            chunk = string_points_table_data[i:i + 4]
            str_point = int.from_bytes(chunk, "little")
            if str_point != 0:
                end_pos = extracted_data.find(b'\x00', str_point)
                string_bytes = extracted_data[str_point:end_pos]
                string_data = string_bytes.decode('utf-8')
                if string_data:
                    # 记录字符串在指针表中的偏移量
                    table_offset = table_start_point + 16 + i
                    strings_with_offset.append((f"0x{table_offset:04X}", string_data))

        alignment_info = {
            'genestrt_pos': genestrt_pos,
            'gop_gdat_pos': gop_gdat_pos,
            'table_start_point': table_start_point,
            'table_end_point': table_end_point,
            'string_area_size1_offset': genestrt_pos + 8,
            'string_area_size2_offset': genestrt_pos + 28
        }

        return strings_with_offset, alignment_info, data

    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {e}")
        return None, None, None


def process_gop_files(folder_path, extract_path):
    """
    处理指定文件夹中的所有.gop文件，提取字符串到 CSV
    """
    gop_files = sorted(glob.glob(os.path.join(folder_path, "*.gop")))

    if not gop_files:
        print(f"在文件夹 {folder_path} 中未找到.gop文件")
        return

    print(f"找到 {len(gop_files)} 个.gop文件")
    print("=" * 80)

    target_path = Path(extract_path)
    target_path.mkdir(parents=True, exist_ok=True)

    for file_path in gop_files:
        filename = os.path.basename(file_path)

        if ignore_file in filename:
            continue

        strings_with_offset, alignment_info, _ = parse_gop_file(file_path)

        if strings_with_offset is not None and alignment_info is not None:
            string_count = len(strings_with_offset)

            # 创建对应的CSV文件路径
            csv_filename = Path(file_path).stem + ".csv"
            csv_path = target_path / csv_filename

            # 写入CSV文件
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['offset', 'string', "translate"])

                for offset, string in strings_with_offset:
                    writer.writerow([offset, string.replace("\n", break_line_char), ''])

            print(f"文件名: {filename}, 字符串数量: {string_count}")
            print(f"  已导出到: {csv_path}")

        else:
            print(f"无法解析文件: {filename}")

        print("-" * 80)


def repack_gop_files(gop_folder, csv_folder, output_folder):
    """
    重新封包GOP文件
    """
    gop_files = sorted(glob.glob(os.path.join(gop_folder, "*.gop")))

    if not gop_files:
        print(f"在文件夹 {gop_folder} 中未找到.gop文件")
        return

    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"开始重新封包 {len(gop_files)} 个.gop文件")
    print("=" * 80)

    for gop_file in gop_files:
        filename = Path(gop_file).name

        if ignore_file in filename:
            continue

        csv_file = Path(csv_folder) / (Path(gop_file).stem + ".csv")

        if not csv_file.exists():
            print(f"警告: 找不到对应的CSV文件 {csv_file}")
            continue

        print(f"处理文件: {filename}")

        # 解析原始文件
        strings_with_offset, alignment_info, original_data = parse_gop_file(gop_file)
        if not all([strings_with_offset, alignment_info, original_data]):
            print(f"  无法解析原始文件，跳过")
            continue

        # 读取CSV文件
        csv_strings = []
        csv_translate = []
        csv_offsets = []
        with open(csv_file, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                csv_offsets.append(int(row['offset'], 16))
                csv_strings.append(row['string'].replace(break_line_char, "\n").replace("＠ｎ", "\n"))
                csv_translate.append(row['translate'].replace(break_line_char, "\n").replace("＠ｎ", "\n"))

        if len(csv_strings) != len(strings_with_offset):
            print(f"  警告: CSV字符串数量({len(csv_strings)})与原始文件({len(strings_with_offset)})不匹配")

        # 构建新的字符串区域
        new_string_data = b""
        string_offsets = []

        # 构建字符串内容
        for idx, string in enumerate(csv_strings):
            is_text_command = is_alpha_underscore(string)

            # 如果是SelfId，在前面添加00字节
            if string == "SelfId":
                new_string_data += b'\x00'
                string_offsets.append(1)

            # 添加字符串内容和 null 终止符
            trans_text = csv_translate[idx]

            if not need_holder_chars:
                # string = half_to_full(string)
                trans_text = half_to_full(trans_text)

            if trans_text:
                is_trans_command = is_alpha_underscore(trans_text)

                if is_text_command and not is_trans_command:
                    raise RuntimeError(f'不符合翻译规则: {string}')

                new_string_data += trans_text.encode('utf-8') + b'\x00'
            else:
                new_string_data += string.encode('utf-8') + b'\x00'

            # 记录当前字符串的偏移量
            string_offsets.append(len(new_string_data))

        # 对齐到16字节
        padding_size = (16 - (len(new_string_data) % 16)) % 16
        if padding_size > 0:
            new_string_data += b'\x00' * padding_size

        print(f"  新字符串区域大小: {len(new_string_data)} 字节")
        print(f"  对齐填充: {padding_size} 字节")
        print(f"  16字节对齐: {len(new_string_data) % 16 == 0}")

        # 构建新的文件数据
        new_file_data = bytearray()

        # 1. 保留原始文件从0到table_end_point的所有数据
        new_file_data.extend(original_data[:alignment_info['table_end_point']])

        # 2. 更新指针表中的字符串偏移量
        # 遍历CSV中的每个偏移量位置，写入新的字符串偏移量
        for i, (csv_offset, new_offset) in enumerate(zip(csv_offsets, string_offsets)):
            # 在原始指针位置写入新的偏移量
            new_file_data[csv_offset:csv_offset + 4] = new_offset.to_bytes(4, 'little')
            print(f"  更新指针 {i}: 位置 0x{csv_offset:04X} -> 偏移量 0x{new_offset:04X}")

        # 3. 计算新的字符串区域总大小
        # 字符串区域总大小 = (table_end_point到字符串区域开始) + 新字符串数据大小
        # 但实际上就是指针表大小 + 字符串数据大小
        pointer_table_size = alignment_info['table_end_point'] - alignment_info['table_start_point']
        new_string_area_size = pointer_table_size + len(new_string_data)

        # 4. 更新string_area_size1和string_area_size2
        # 更新string_area_size1 (在GENESTRT区域)
        size1_offset = alignment_info['string_area_size1_offset']
        new_file_data[size1_offset:size1_offset + 4] = new_string_area_size.to_bytes(4, 'little')

        # 更新string_area_size2 (在表头区域)
        size2_offset = alignment_info['string_area_size2_offset']
        new_file_data[size2_offset:size2_offset + 4] = new_string_area_size.to_bytes(4, 'little')

        print(f"  更新区域大小: {new_string_area_size} 字节")
        print(f"  大小字段位置: 0x{size1_offset:04X}, 0x{size2_offset:04X}")

        # 5. 添加新的字符串数据
        new_file_data.extend(new_string_data)

        # 6. 添加GOP GDAT及之后的数据
        new_file_data.extend(original_data[alignment_info['gop_gdat_pos']:])

        # 7. 写入新文件
        output_file = output_path / filename
        with open(output_file, 'wb') as f:
            f.write(new_file_data)

        print(f"  成功生成: {output_file}")
        print(f"  新文件大小: {len(new_file_data)} 字节")
        print("-" * 80)

    # Copy TalkAnagram
    shutil.copy(
        os.path.join("anagram_editor", "export", "gop_talkanagram.gop"),
        os.path.join(output_folder, "gop_talkanagram.gop")
    )


def usage():
    print("Usage:")
    print("  Extract *.gop -> python gop_tool.py extract")
    print("  Repack *.gop  -> python gop_tool.py repack")


def main():
    # 配置路径
    origin_folder = "gop_data/origin"
    extract_folder = "gop_data/extract"
    output_folder = sys.argv[2] if sys.argv[2] else "gop_data/rebuild"

    # 创建必要的文件夹
    for folder in [origin_folder, extract_folder, output_folder]:
        Path(folder).mkdir(parents=True, exist_ok=True)

    mode = sys.argv[1].lower()

    if mode == "extract":
        process_gop_files(origin_folder, extract_folder)
    elif mode == "repack":
        repack_gop_files(origin_folder, extract_folder, output_folder)
    else:
        usage()


if __name__ == "__main__":
    main()
