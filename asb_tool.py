import re
import sys
import csv
from pathlib import Path
from make_abf import font_config, choose_font, half_to_full

default_encode = "utf-8"
break_line_char = "@n"

need_holder_chars = font_config[choose_font]["holder_char"]

say_title_prefix = "@say "

say_title_map = {
    'rak': "【一条 乐】",
    'ctg': "【桐崎 千棘】",
    'ksk': "【小野寺 小咲】",
    'ssr': "【鸫 诚士郎】",
    'mrk': "【橘 万里花】",
    'rur': "【宫本 琉璃】",
    'syu': "【舞子 集】",
    'cld': "【克劳德】",
    'otm': "【小玉】",
    'kyk': "【教子老师】",
    'rap': "【乐的父亲】",
    'ctp': "【千棘的父亲】",
    'ryu': "【龙】",
    'ksm': "【小咲的母亲】",
    'hnd': "【本田】",
    'mrp': "【万里花的父亲】",
    'mtg': "【桐崎 美棘】",
    'ss1': "【诚士郎（乐）】",
    'ra1': "【乐（诚士郎）】",
    'ot1': "【小玉（琉璃）】",
    'bab': "【鬼牌】",
    'snk': "【蛇】",
    'ask': "【海狮】",
    'ign': "【鬣蜥】",
    'ibr': "【伊比利亚猪】",
    'trt': "【龟】",
    'crw': "【乌鸦】",
    'niw': "【鸡】",
    'mnt': "【山魈】",
    'agt': "【鳄鱼】",
    'dog': "【狗】",
    'ktn': "【小猫】",
    'crn': "【鹤】",
    'cat': "【猫】",
    'sdg': "【野狗】",
    'ham': "【仓鼠】",
    'ugr': "【牛蛙】",
    'wow': "【猴子】",
    'wst': "【女学生】",
    'wsa': "【女学生A】",
    'wsb': "【女学生B】",
    'wsc': "【女学生C】",
    'wsd': "【女学生D】",
    'wvb': "【女子排球社员】",
    'wkd': "【女子剑道社员】",
    'wtk': "【女子田径社员】",
    'bik': "【美化委员】",
    'mst': "【男学生】",
    'msa': "【男学生A】",
    'msb': "【男学生B】",
    'msc': "【男学生C】",
    'msd': "【男学生D】",
    'mse': "【男学生E】",
    'mta': "【田径社员A】",
    'mtb': "【田径社员B】",
    'jka': "【学长A】",
    'jkb': "【学长B】",
    'jkc': "【学长C】",
    'stk': "【学生会干部】",
    'cpa': "【小混混A】",
    'cpb': "【小混混B】",
    'sea': "【年轻手下A】",
    'seb': "【年轻手下B】",
    'sec': "【年轻手下C】",
    'sed': "【年轻手下D】",
    'gna': "【黑帮分子A】",
    'gnb': "【黑帮分子B】",
    'gnc': "【黑帮分子C】",
    'gnd': "【黑帮分子D】",
    'pla': "【机动队员A】",
    'plb': "【机动队员B】",
    'plc': "【机动队员C】",
    'cpu': "【ＣＰＵ】",
    'evs': "【活动工作人员】",
    'gca': "【游戏中心顾客A】",
    'gcb': "【游戏中心顾客B】",
    'gcs': "【游戏中心店员】",
    'stm': "【系统】",
    'tak': "【章鱼烧摊大叔】",
    'ana': "【播音员】",
    'pro': "【制作人】",
    'fna': "【粉丝A】",
    'fnb': "【粉丝B】",
    'fnc': "【粉丝C】",
    'fnd': "【粉丝D】",
    'fne': "【粉丝E】",
    'fnf': "【粉丝F】",
    'mas': "【媒体】",
    'pcp': "【男性参加者】",
    'chm': "【主持人】",
    'chd': "【小孩】",
    'owr': "【饲主】",
    'mdl': "【人体模型】",
    'tlp': "【电话自动应答】",
    'nza': "【谜之声A】",
    'nzb': "【谜之声B】",
    'nzc': "【谜之声C】",
    'nzd': "【谜之声D】",
    'nze': "【谜之声E】",
    'mtr': "【母亲】",
    'lvr': "【恋爱中的少女】",
    'dlc_ctg': "【DLC 千棘】",
    'dlc_ksk': "【DLC 小咲】",
    'dlc_ssr': "【DLC 诚士郎】",
    'dlc_mrk': "【DLC 万里花】",
    'dlc_rur': "【DLC 琉璃】",
    'ano': "【？？？】",
    'rak_syu': "【乐＆集】",
    'rak_ctg': "【乐＆千棘】",
    'rak_ksk': "【乐＆小咲】",
    'rak_ssr': "【乐＆诚士郎】",
    'rak_mrk': "【乐＆万里花】",
    'rak_mtg': "【乐＆美棘】",
    'ctg_mrk': "【千棘＆万里花】",
    'ctg_mtg': "【千棘＆美棘】",
    'ctg_ksk': "【千棘＆小咲】",
    'ksk_mrk': "【小咲＆万里花】",
    'syu_rur': "【集＆琉璃】",
    'syu_seg': "【集＆年轻手下们】",
    'cld_ryu': "【克劳德＆龙】",
    'all': "【大家】",
    'raks': "【乐等人】",
    'ctgs': "【千棘等人】",
    'ksks': "【小咲等人】",
    'mrks': "【万里花等人】",
    'mss': "【男学生们】",
    'pls': "【机动队员们】",
    'st_all': "【全体学生】",
    'w_spts': "【女社员们】",
}


class ASBStringTool:
    @staticmethod
    def get_null_terminated_string_at(data: bytearray, position: int) -> str:
        string_data = bytearray()
        if len(data) <= position:
            return ""
        i = 0
        while True:
            if position + i >= len(data):
                break
            b = data[position + i]
            i += 1
            if b == 0:
                break
            string_data.append(b)
        return string_data.decode(errors="ignore").replace("\n", break_line_char)

    @staticmethod
    def get32(data: bytearray, pos: int) -> int:
        if pos + 3 >= len(data):
            return 0
        return int.from_bytes(data[pos:pos + 4], "little")

    @staticmethod
    def get16(data: bytearray, pos: int) -> int:
        if pos + 1 >= len(data):
            return 0
        return int.from_bytes(data[pos:pos + 2], "little")

    @staticmethod
    def get8(data: bytearray, pos: int) -> int:
        if pos >= len(data):
            return 0
        return data[pos]

    @staticmethod
    def get_op_names_and_arguments(opcode: int):
        if opcode == 0:
            return ["show_text", ['s', 'i']]
        if opcode == 906:
            return ["show_text_noindex", ['s']]
        if opcode == 926:
            return ["show_text_noindex", ['s']]
        if opcode == 331:
            return ["play_voice_line", ['i', 'i', 's']]
        if opcode == 1:
            return ["display_choices", ['s'] * 6]
        if opcode == 2:
            return ["display_choices", ['s'] * 6]
        if opcode == 930:
            return ["display_choices", ['s'] * 6]
        if opcode == 931:
            return ["display_choices", ['i', 'i'] + ['s'] * 5]
        return []

    @staticmethod
    def should_ignore_string(s: str) -> bool:
        if not s:
            return True
        if s.startswith("@"):
            return True
        if s == "__main":
            return True
        # 以三个字母+/ 开头的都筛掉, 这个是标注人名的, 应该是用来做引用人名的变量
        # if s[:4] in ("CTG/", "RAK/", "MRK/", "SSR/", "SYU/", "RUR/", "KSK/"):
        # if len(s) >= 4 and s[:3].isalpha() and s[3] == '/':
        #     return True
        return False

    @staticmethod
    def is_say_style(s: str):
        pattern = r'^([a-zA-Z][a-zA-Z_]*[a-zA-Z])/([a-zA-Z0-9]+)$'
        return re.match(pattern, s)

    @staticmethod
    def replace_say_title(s: str) -> str:
        match = ASBStringTool.is_say_style(s)
        if match:
            return f'{say_title_prefix}{say_title_map[match.group(1).lower()]}'
        else:
            return s

    def extract_single(self, infile: str, csv_out: str):
        data = bytearray(open(infile, "rb").read())
        if len(data) < 14:
            print(f"Invalid file: {infile}")
            return

        get32 = self.get32
        get8 = self.get8
        get_str = self.get_null_terminated_string_at

        number_of_sections = get32(data, 0x28)

        string_sections = []
        for i in range(3):
            start = get32(data, 0x2C + i * 8)
            length = get32(data, 0x30 + i * 8)
            string_sections.append([start, length])

        indices_of_string_indices = {}

        def add_string_offset(position: int, index: int):
            key = str(index)
            if key not in indices_of_string_indices:
                indices_of_string_indices[key] = []
            indices_of_string_indices[key].append(position)

        sections = []
        sec_it = 0
        for i in range(number_of_sections):
            func_name_offset = get32(data, 0x44 + sec_it)
            add_string_offset(0x44 + sec_it, func_name_offset)
            script_start = get32(data, 0x50 + sec_it)
            script_len = get32(data, 0x54 + sec_it)
            sections.append([script_start, script_len])
            sec_it += 0x14

        indexed_strings = {}
        str_start = string_sections[1][0]
        idx = 0
        while str_start + idx < len(data):
            s = get_str(data, str_start + idx)
            indexed_strings[str(idx)] = s
            idx += len(s.replace(break_line_char, "\n").encode(default_encode)) + 1

        function_args = []
        function_arg_pos = []

        for sec_start, sec_len in sections:
            start_at = sec_start + string_sections[0][0]
            end_at = start_at + sec_len
            cur = start_at
            opcode = get8(data, cur)
            while opcode != 0x2b and cur < end_at:
                if opcode in (0x01, 0x03, 0x04, 0x08):
                    function_arg_pos.append(cur + 1)
                    function_args.append(self.get32(data, cur + 1))
                    cur += 5
                elif opcode == 0x16:
                    function_arg_pos.append(cur + 1)
                    function_args.append(self.get16(data, cur + 1))
                    cur += 3
                elif opcode == 0x0a:
                    function_arg_pos.append(cur + 1)
                    function_args.append(self.get32(data, cur + 1))
                    cur += 6
                elif opcode == 0x02 or opcode == 0x07:
                    function_arg_pos.append(cur + 1)
                    function_args.append(self.get8(data, cur + 1))
                    cur += 2
                elif opcode == 0x26:
                    add_string_offset(cur + 5, self.get32(data, cur + 5))
                    cur += 9
                elif opcode == 0x29:
                    cmd = self.get32(data, cur + 1)
                    arg_n = self.get8(data, cur + 5)
                    op_info = self.get_op_names_and_arguments(cmd)
                    if op_info and len(op_info) > 1:
                        types = op_info[1]
                        for i in range(arg_n):
                            pos = function_arg_pos[len(function_args) - arg_n + i]
                            val = function_args[len(function_args) - arg_n + i]
                            if i < len(types) and types[i] == 's':
                                add_string_offset(pos, val)
                    cur += 6
                else:
                    cur += 1
                opcode = get8(data, cur)

        Path(csv_out).parent.mkdir(parents=True, exist_ok=True)
        with open(csv_out, "w", encoding='utf-8-sig', newline="") as fw:
            writer = csv.writer(fw)
            writer.writerow(["offset", "string", "translate"])
            for idx, positions in indices_of_string_indices.items():
                # s = indexed_strings.get(idx, "<unknown>")
                # if self.should_ignore_string(s):
                #     continue
                s = indexed_strings.get(idx)
                if s is None or self.should_ignore_string(s):
                    continue

                for p in positions:
                    writer.writerow([hex(p), self.replace_say_title(s), ''])
        print(f"Extract finished → {csv_out}")

    def extract_folder(self, input_folder: str, output_folder: str):
        input_path = Path(input_folder)
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)
        for asb_file in input_path.glob("*.asb"):
            csv_out = output_path / (asb_file.stem + ".csv")
            self.extract_single(str(asb_file), str(csv_out))

    def repack_single(self, original_asb: str, csv_file: str, out_asb: str):
        data = bytearray(open(original_asb, "rb").read())

        string_section_start = self.get32(data, 0x2C + 1 * 8)
        original_string_len = self.get32(data, 0x30 + 1 * 8)

        # 读取尾部 offset 0x3C~0x3D
        tail_offset = self.get16(data, 0x3C)
        if tail_offset < len(data) - 1:
            tail_data = data[tail_offset:]  # 尾部数据
            data = data[:tail_offset]  # 截断原始尾部
        else:
            tail_data = bytearray()  # 没有尾部数据

        rows = []
        with open(csv_file, "r", encoding='utf-8-sig') as fr:
            reader = csv.reader(fr)
            next(reader, None)
            for row in reader:
                if not row:
                    continue
                try:
                    pointer_pos = int(row[0], 16)
                except:
                    continue

                # 忽略带说话人姓名的, 此为提示行, 不需要往回插入
                if row[1].startswith(say_title_prefix) or ASBStringTool.is_say_style(row[1]):
                    continue

                rows.append(
                    (
                        pointer_pos,
                        row[1] if need_holder_chars else half_to_full(row[1]),
                        row[2] if need_holder_chars else half_to_full(row[2]),
                    )
                )

        # 追加数据从原始字符串区尾部开始
        write_cursor = string_section_start + original_string_len
        for pointer_pos, s, trans_str in rows:
            new_bytes = s.replace(break_line_char, "\n").replace("＠ｎ", "\n").encode(default_encode) + b"\x00"

            # 有翻译就应用翻译到最终文件
            if trans_str:
                new_bytes = trans_str.replace(break_line_char, "\n").replace("＠ｎ", "\n").encode(default_encode) + b"\x00"

            data.extend(new_bytes)
            new_offset = write_cursor - string_section_start  # 字符串区内相对偏移
            data[pointer_pos:pointer_pos + 4] = new_offset.to_bytes(4, "little")
            write_cursor += len(new_bytes)

        # 更新字符串区长度
        new_string_len = write_cursor - string_section_start
        data[0x30 + 1 * 8:0x30 + 1 * 8 + 4] = new_string_len.to_bytes(4, "little")

        # 尾部数据追加
        new_tail_offset = len(data)
        data.extend(tail_data)
        if not tail_data:
            new_tail_offset -= 1

        try:
            # data[0x3C:0x3C + 2] = new_tail_offset.to_bytes(2, "little")
            data[0x3C:0x3C + 4] = new_tail_offset.to_bytes(4, "little")
        except Exception as e:
            pass

        Path(out_asb).parent.mkdir(parents=True, exist_ok=True)
        with open(out_asb, "wb") as fw:
            fw.write(data)
        print(f"Repack finished → {out_asb}")

    def repack_folder(self, asb_folder: str, csv_folder: str, out_folder: str):
        asb_path = Path(asb_folder)
        csv_path = Path(csv_folder)
        out_path = Path(out_folder)
        out_path.mkdir(parents=True, exist_ok=True)
        for asb_file in asb_path.glob("*.asb"):
            csv_file = csv_path / (asb_file.stem + ".csv")
            out_asb_file = out_path / asb_file.name
            if csv_file.exists():
                self.repack_single(str(asb_file), str(csv_file), str(out_asb_file))
            else:
                print(f"CSV file missing for {asb_file}, skipping...")


def usage():
    print("Usage:")
    print("  Extract folder -> python asb_tool.py extract input_asb_folder output_csv_folder")
    print("  Repack folder  -> python asb_tool.py repack input_asb_folder input_csv_folder output_asb_folder")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    mode = sys.argv[1].lower()
    tool = ASBStringTool()

    if mode == "extract":
        if len(sys.argv) < 4:
            usage()
            sys.exit(1)
        tool.extract_folder(sys.argv[2], sys.argv[3])
    elif mode == "repack":
        if len(sys.argv) < 5:
            usage()
            sys.exit(1)
        tool.repack_folder(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        usage()
