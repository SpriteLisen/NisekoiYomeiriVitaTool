import os
import glob


def parse_gop_file(file_path):
    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        # 检查文件头
        if not data.startswith(b'GOP GFIN'):
            print(f"警告: {file_path} 不是有效的GOP文件")
            return None, None

        # 查找GENESTRT位置
        genestrt_pos = data.find(b'GENESTRT')
        if genestrt_pos == -1:
            print(f"警告: {file_path} 中未找到GENESTRT")
            return None, None

        point_offset = genestrt_pos + 8
        # string_area_size (4 byte), 从 String count 开始一直到 GOP GDAT 开头
        string_area_size1 = int.from_bytes(data[point_offset:point_offset + 4], "little")

        point_offset = point_offset + 8
        table_start_point = point_offset

        # String count (4 byte)
        string_count_start_point = point_offset
        str_count = int.from_bytes(data[point_offset:point_offset + 4], "little")
        point_offset = point_offset + 4
        print(f"str_count: {str_count}")

        # unknown1 (4 byte), 这个区域好像一直都是 hex 10 ✅
        unknown1 = int.from_bytes(data[point_offset:point_offset + 4], "little")
        point_offset = point_offset + 4
        print(f'is unknown1 10: {unknown1 == 16}')

        # table_count_size (4 byte) ✅
        table_count_size = int.from_bytes(data[point_offset:point_offset + 4], "little")
        point_offset = point_offset + 4
        table_end_point = table_start_point + table_count_size
        real_table_data = len(data[table_start_point:table_end_point])
        print(f'is_table_byte_ok: {real_table_data == table_count_size}')

        # string_area_size (4 byte), 从 String count 开始一直到 GOP GDAT 开头
        string_area_size2 = int.from_bytes(data[point_offset:point_offset + 4], "little")
        point_offset = point_offset + 4

        print(f"is string_area_size same: {string_area_size1 == string_area_size2}")

        # string_start_content
        string_start_content = data[point_offset:point_offset + 12]
        point_offset = point_offset + 12
        # 永远是这几个字节开头 ✅
        is_target_content = string_start_content == b"\x00\x00\x00\x00\x01\x00\x00\x00\x08\x00\x00\x00"
        print(f'is_target_content: {is_target_content}')

        # 查找GOP GDAT位置
        gop_gdat_pos = data.find(b'GOP GDAT')
        if gop_gdat_pos == -1:
            print(f"警告: {file_path} 中未找到GOP GDAT")
            return None, None

        # 整个 GENESTRTP 区域的字节数会跟 string_area_size1, string_area_size2 两个值完全一致 ✅
        GENESTRTP_area_size = len(data[string_count_start_point:gop_gdat_pos])
        print(f"is GENESTRTP area ok: {GENESTRTP_area_size == string_area_size1 == string_area_size2}")

        # 截取数据：从GENESTRT开始到GOP GDAT前一个字节
        extracted_data = data[table_end_point:gop_gdat_pos]

        # 字符串记录指针的总 bytes
        mock_str_count = len(data[point_offset:table_end_point])

        strings = []
        current_pos = 0

        while current_pos < len(extracted_data):
            # 查找下一个null终止符
            null_pos = extracted_data.find(b'\x00', current_pos)
            if null_pos == -1:
                break

            # 提取字符串（从当前位置到null终止符前）
            string_bytes = extracted_data[current_pos:null_pos]

            # 尝试解码为字符串
            string_value = string_bytes.decode('utf-8')
            if string_value:  # 只添加非空字符串
                strings.append(string_value)

            # 移动到下一个字符串的开始位置（null终止符后）
            current_pos = null_pos + 1

        # 检查整个字符串内容区域是否 16 字节对齐 ✅
        is_16byte_aligned = (len(extracted_data) % 16 == 0)

        alignment_info = {
            'is_16byte_aligned': is_16byte_aligned,
        }

        print(f"mock count: {mock_str_count / 4}")
        print(f"is_equal_mock: {len(strings) == mock_str_count / 4}")

        # 从指针表里面把字符串提取出来
        string_points_table_data = data[table_start_point + 16:table_end_point]
        string_table_content = []
        for i in range(0, len(string_points_table_data), 4):
            chunk = string_points_table_data[i:i + 4]
            str_point = int.from_bytes(chunk, "little")
            if str_point != 0:
                end_pos = extracted_data.find(b'\x00', str_point)
                string_bytes = extracted_data[str_point:end_pos]

                # 尝试解码为字符串
                string_data = string_bytes.decode('utf-8')
                if string_data:  # 只添加非空字符串
                    string_table_content.append(string_data)

        # 从字符分区里面提取的字符串, 与从字符指针区域获取的字符完全一致 (达成这个才可以修改) ✅
        print(f"string_table_content len: {len(string_table_content)}")
        print(f"is same str len: {len(string_table_content) == len(strings)}")
        print(f"is same str list: {string_table_content == strings}")

        return strings, alignment_info

    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {e}")
        return None, None


def process_gop_files(folder_path):
    """
    处理指定文件夹中的所有.gop文件
    """
    # 查找所有.gop文件并按文件名排序
    gop_files = sorted(glob.glob(os.path.join(folder_path, "*.gop")))

    if not gop_files:
        print(f"在文件夹 {folder_path} 中未找到.gop文件")
        return

    print(f"找到 {len(gop_files)} 个.gop文件")
    print("=" * 80)

    for file_path in gop_files:
        filename = os.path.basename(file_path)

        strings, alignment_info = parse_gop_file(file_path)

        if strings is not None and alignment_info is not None:
            string_count = len(strings)

            if string_count > 0:
                first_string = strings[0]
                last_string = strings[-1]
            else:
                first_string = "无"
                last_string = "无"

            print(f"文件名: {filename}, 字符串数量: {string_count}, 第一个字符串: {first_string}, 最后一个字符串: {last_string}")

            # 输出对齐信息
            print(f"  16字节对齐: {'是' if alignment_info['is_16byte_aligned'] else '否'}")

        else:
            print(f"无法解析文件: {filename}")

        print("-" * 80)


def main():
    folder_path = "gop_data/origin"

    # 处理GOP文件
    process_gop_files(folder_path)


if __name__ == "__main__":
    main()
