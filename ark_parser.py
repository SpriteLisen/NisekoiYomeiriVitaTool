import struct
from dataclasses import dataclass
from typing import List, Optional

char_mapping = {
    "word_ru": "ル",
    "word_mu": "ム",
    "word_a": "ア",
    "word_ba": "バ",
    "word_bi": "ビ",
    "word_ga": "ガ",
    "word_gi": "ギ",
    "word_i": "ー",
    "word_ki": "キ",
    "word_ko": "コ",
    "word_ku": "ク",
    "word_me": "メ",
    "word_n": "ン",
    "word_nu": "ヌ",
    "word_o": "オ",
    "word_ra": "ラ",
    "word_ri": "リ",
    "word_shi": "シ",
    "word_so": "ソ",
    "word_to": "ト",
    "word_ya": "ヤ",

    # Extend char
    "TEXTURE0045": "ア",
    "TEXTURE0015": "バ",
    "TEXTURE0024": "ア",
    "TEXTURE0006": "ン",
}


class TXOSChunk:
    def __init__(self, data, id):
        self.data = data

        self.id = id
        self.type = struct.unpack("<I", data[0x00:0x04])[0]
        self.point_x = struct.unpack("<I", data[0x14:0x18])[0]
        self.point_y = struct.unpack("<I", data[0x18:0x1C])[0]
        self.width = struct.unpack("<I", data[0x1C:0x20])[0]
        self.height = struct.unpack("<I", data[0x20:0x24])[0]
        self.str_id = struct.unpack("<I", data[0x34:0x38])[0]
        self.str = ""

    def fill_str(self, value):
        self.str = char_mapping.get(value, value)

    def __str__(self):
        return f"""
            [
                type: {self.type},
                id: {self.id},
                point_x: {self.point_x},
                point_y: {self.point_y},
                width: {self.width},
                height: {self.height},
                str_id: {self.str_id},
                str: {self.str},
            ]
        """


@dataclass
class LAY2Header:
    magic: bytes
    file_size: int
    str_id: int
    unk14: int
    unk18: int
    unk1C: int
    unk20: int
    item_count: int
    canvas_width: int
    canvas_height: int
    pre_header_size: int
    header_size: int
    unk38: int
    unk3C: int

    str = ""

    def __repr__(self):
        return (f"LAY2Header(str_id={self.str_id}, str={self.str}, "
                f"unk14={self.unk14}, unk18={self.unk18}, unk1C={self.unk1C}, unk20={self.unk20}, "
                f"canvas_width={self.canvas_width}, canvas_height={self.canvas_height})")


@dataclass
class LAY2Item:
    tag: int  # 固定 0x30
    instance_id: int  # 实例 ID
    base_x: int  # X 坐标
    base_y: int  # Y 坐标
    item_id: int  # 引用字符串的 idx
    canvas_width: int  # 画布宽度
    canvas_height: int  # 画布高度
    unk1C: int  # 未知
    unk20: int  # 未知
    txos_id: int  # TXOS 资源 ID
    unk28: int  # 未知
    unk2C: int  # 未知

    txos = None

    str_content = ''

    def __repr__(self):
        return (f"LAY2Item(tag=0x{self.tag:02X}, instance_id={self.instance_id}, "
                f"pos=({self.base_x},{self.base_y}), size={self.canvas_width}x{self.canvas_height}, "
                f"unk1C={self.unk20}, unk20={self.unk20}, "
                f"unk28={self.unk28}, unk2C={self.unk2C}, "
                f"str_id={self.item_id}, str={self.str_content}, "
                f"txos_id={self.txos_id}, txos_str={self.txos.str if self.txos else ''})")


class LAY2Parser:
    def __init__(self, data: bytes, area_start_cursor):
        self._data = data
        self.area_start_cursor = area_start_cursor
        self.header: Optional[LAY2Header] = None
        self.items: List[LAY2Item] = []

    def parse(self):
        if len(self._data) < 0x40:
            raise ValueError("数据太短，无法解析文件头")

        self._parse_header()
        # print(f"Item 数量: {self.header.item_count}")
        # print(f"Item 区域总大小: 0x{self.header.items_total_size:X} ({self.header.items_total_size} 字节)")

        # Item 数据从 0x40 开始
        ptr = 0x40
        for i in range(self.header.item_count):
            if ptr + 0x30 > len(self._data):
                print(f"警告：数据不足，只解析了 {i} 个 Item")
                break
            item = self._parse_item(ptr)
            self.items.append(item)
            # print(f"Item {i + 1}: {item}")
            ptr += 0x30

        # ptr 现在指向 Item 区域结束，后续是变换层数据（暂不解析）
        # print(f"Item 区域结束于 0x{ptr:X}")

    def _parse_header(self):
        magic = self._data[0:8]
        if magic != b'ARK LAY2':
            raise ValueError(f"无效魔数: {magic}")

        file_size = struct.unpack("<Q", self._data[0x08:0x10])[0] # ✅
        str_id = struct.unpack("<I", self._data[0x10:0x14])[0] # ✅

        unk14 = struct.unpack("<I", self._data[0x14:0x18])[0]
        unk18 = struct.unpack("<I", self._data[0x18:0x1C])[0]
        unk1C = struct.unpack("<I", self._data[0x1C:0x20])[0]
        unk20 = struct.unpack("<I", self._data[0x20:0x24])[0]

        item_count = struct.unpack("<I", self._data[0x24:0x28])[0] # ✅
        canvas_width = struct.unpack("<I", self._data[0x28:0x2C])[0]  # ✅
        canvas_height = struct.unpack("<I", self._data[0x2C:0x30])[0]  # ✅

        # Always 0x30
        pre_header_size = struct.unpack("<I", self._data[0x30:0x34])[0] # ✅
        header_size = struct.unpack("<I", self._data[0x34:0x38])[0] # ✅

        # Always 0x00, ignore
        unk38 = struct.unpack("<I", self._data[0x38:0x3C])[0] # ✅
        unk3C = struct.unpack("<I", self._data[0x3C:0x40])[0] # ✅

        self.header = LAY2Header(
            magic=magic,
            file_size=file_size,
            str_id=str_id,
            unk14=unk14,
            unk18=unk18,
            unk1C=unk1C,
            unk20=unk20,
            item_count=item_count,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            pre_header_size=pre_header_size,
            header_size=header_size,
            unk38=unk38,
            unk3C=unk3C
        )

    def _parse_item(self, ptr: int) -> LAY2Item:
        """解析单个 Item，固定 0x30 字节"""
        tag = struct.unpack("<I", self._data[ptr:ptr + 4])[0]
        if tag != 0x30:
            print(f"警告：Item 标记异常，期望 0x30，实际 0x{tag:08X} at 0x{ptr:X}")

        instance_id = struct.unpack("<I", self._data[ptr + 0x04:ptr + 0x08])[0]
        base_x = struct.unpack("<I", self._data[ptr + 0x08:ptr + 0x0C])[0]
        base_y = struct.unpack("<I", self._data[ptr + 0x0C:ptr + 0x10])[0]
        item_id = struct.unpack("<I", self._data[ptr + 0x10:ptr + 0x14])[0]
        canvas_width = struct.unpack("<I", self._data[ptr + 0x14:ptr + 0x18])[0]
        canvas_height = struct.unpack("<I", self._data[ptr + 0x18:ptr + 0x1C])[0]
        unk1C = struct.unpack("<I", self._data[ptr + 0x1C:ptr + 0x20])[0]
        unk20 = struct.unpack("<I", self._data[ptr + 0x20:ptr + 0x24])[0]
        txos_id = struct.unpack("<I", self._data[ptr + 0x24:ptr + 0x28])[0]
        unk28 = struct.unpack("<I", self._data[ptr + 0x28:ptr + 0x2C])[0]
        unk2C = struct.unpack("<I", self._data[ptr + 0x2C:ptr + 0x30])[0]

        return LAY2Item(
            tag=tag,
            instance_id=instance_id,
            base_x=base_x,
            base_y=base_y,
            item_id=item_id,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            unk1C=unk1C,
            unk20=unk20,
            txos_id=txos_id,
            unk28=unk28,
            unk2C=unk2C
        )


if __name__ == "__main__":
    cursor_idx = 0
    # with (open("ark_data/origin/gallery.ark", 'rb') as f):
    with (open("ark_data/new_gallery.ark", 'rb') as f):
        data = f.read()

        # --------------------------------------------------------------------------
        # File Magic (size: 0x10)
        magic_size = 0x10
        magic_data = data[0:magic_size]
        cursor_idx += magic_size

        if magic_data != b'ENDILTLE\x00\x00\x00\x00\x00\x00\x00\x00':
            raise Exception("Not ark file!")

        # --------------------------------------------------------------------------
        # ARKF Area
        arkf_title_size = 0x08
        arkf_title_data = data[cursor_idx:cursor_idx + arkf_title_size]
        cursor_idx += arkf_title_size
        if arkf_title_data != b'ARK ARKF':
            raise Exception("ARKF area error")

        arkf_area_len_size = 0x08
        # 0x10
        arkf_area_data = struct.unpack(
            '<Q', data[cursor_idx:cursor_idx + arkf_area_len_size]
        )[0]
        cursor_idx += arkf_area_len_size

        arkf_content = data[cursor_idx:cursor_idx + arkf_area_data]
        cursor_idx += arkf_area_data

        # Lay2 chunk size = 0x80
        lay2_chunk_size = struct.unpack(
            "<I", arkf_content[0x04:0x08]
        )[0]
        print(f"lay2 chunk size: {lay2_chunk_size}")

        # --------------------------------------------------------------------------
        # TEX2 Area
        # 贴图资源块：定义使用的贴图文件索引（如 gallery_tex）
        tex2_size = 0x08
        tex2_data = data[cursor_idx:cursor_idx + tex2_size]
        cursor_idx += tex2_size
        if tex2_data != b'ARK TEX2':
            raise Exception("TEX2 area error")

        tex2_area_len_size = 0x08
        # 0x60
        tex2_area_data = struct.unpack(
            '<Q', data[cursor_idx:cursor_idx + tex2_area_len_size]
        )[0]
        cursor_idx += tex2_area_len_size

        tex2_content = data[cursor_idx:cursor_idx + tex2_area_data]
        cursor_idx += tex2_area_data

        # --------------------------------------------------------------------------
        # TXOS Area
        # 渲染条目块 (核心)：存放所有原子视觉单位（Item）的数据
        # TODO 应该要扩这部分
        txos_size = 0x08
        txos_data = data[cursor_idx:cursor_idx + txos_size]
        cursor_idx += txos_size
        if txos_data != b'ARK TXOS':
            raise Exception("TXOS area error")

        txos_area_len_size = 0x08
        # 0x3610
        txos_area_data = struct.unpack(
            '<Q', data[cursor_idx:cursor_idx + txos_area_len_size]
        )[0]
        cursor_idx += txos_area_len_size

        txos_content = data[cursor_idx:cursor_idx + txos_area_data]
        cursor_idx += txos_area_data

        # 0xD8 = 216
        txos_chunk_count = struct.unpack(
            "<I", txos_content[0x00:0x04]
        )[0]
        # 0x40 = 64
        txos_chunk_size = struct.unpack(
            "<I", txos_content[0x04:0x08]
        )[0]

        print(f"TXOS chunk count: {txos_chunk_count}")
        print(f"TXOS chunk size: {txos_chunk_size}")

        # Chunk data = 216 * 64 = 0x3600
        # Part aligned with 16 byte
        txos_chunk_data = txos_content[0x08:]
        txos_chunks = []
        txos_chunk_idx = 0
        txos_item_id = 0
        while True:
            if txos_chunk_idx + 64 >= len(txos_chunk_data) - 1:
                break

            txos_chunks.append(
                TXOSChunk(txos_chunk_data[txos_chunk_idx:txos_chunk_idx + 64], txos_item_id)
            )
            txos_chunk_idx += 64
            txos_item_id += 1

        # --------------------------------------------------------------------------
        # Lay2 items
        # 布局逻辑块：定义 Item 如何组合成“词组”或“页面”
        lay2_items_list = []

        for i in range(lay2_chunk_size):
            area_start_cursor = cursor_idx

            lay2_title_size = 0x08
            lay2_title_data = data[cursor_idx:cursor_idx + lay2_title_size]
            cursor_idx += lay2_title_size
            if lay2_title_data != b'ARK LAY2':
                raise Exception("LAY2 area error")

            lay2_area_len_size = 0x08
            lay2_area_byte = data[cursor_idx:cursor_idx + lay2_area_len_size]
            lay2_area_data = struct.unpack(
                '<Q', lay2_area_byte
            )[0]
            cursor_idx += lay2_area_len_size

            lay2_content = data[cursor_idx:cursor_idx + lay2_area_data]
            cursor_idx += lay2_area_data

            total_bytes = bytearray()
            total_bytes.extend(lay2_title_data)
            total_bytes.extend(lay2_area_byte)
            total_bytes.extend(lay2_content)
            parser = LAY2Parser(total_bytes, area_start_cursor)
            parser.parse()
            lay2_items_list.append(parser)

            # for item in parser.items:
            #     print(f"TXOS ID: {item.txos_id}, Pos: ({item.base_x},{item.base_y})")

        print(f"Lay2 items size: {len(lay2_items_list)}")

        # --------------------------------------------------------------------------
        # STR Area
        # 字符串区域
        str_area_title_size = 0x08
        str_title_area_data = data[cursor_idx:cursor_idx + str_area_title_size]
        cursor_idx += str_area_title_size
        if str_title_area_data != b'GENESTRT':
            raise Exception("STR area error")

        str_area_len_size = 0x08
        str_area_data = struct.unpack(
            '<Q', data[cursor_idx:cursor_idx + str_area_len_size]
        )[0]
        cursor_idx += str_area_len_size

        str_area_content = data[cursor_idx:cursor_idx + str_area_data]
        cursor_idx += str_area_data

        str_idx_table_size = struct.unpack("<I", str_area_content[0x08:0x0C])[0]
        str_idx_table_data = str_area_content[0x10:str_idx_table_size]
        str_content_data = str_area_content[str_idx_table_size:]


        def parse_str(start_cursor):
            idx = start_cursor
            str_data = bytearray()
            while True:
                byte_data = str_content_data[idx:idx + 1]
                if byte_data != b'\x00':
                    str_data.extend(byte_data)
                    idx += 1
                else:
                    return str_data.decode("utf-8")


        str_list = []
        idx_table_idx = 0
        while True:
            if idx_table_idx + 4 >= len(str_idx_table_data) - 1:
                break

            start_idx = struct.unpack(
                "<I", str_idx_table_data[idx_table_idx:idx_table_idx + 4]
            )[0]

            if idx_table_idx != 0 and start_idx == 0:
                idx_table_idx += 4
                continue

            str_part = parse_str(start_idx)
            str_list.append(str_part)
            idx_table_idx += 4

        # print(f"str_items: {len(str_list)}")
        print(str_list)

        for chunk in txos_chunks:
            chunk.fill_str(str_list[chunk.str_id])
            # print(chunk)
            # if str_list[chunk.str_id].startswith("word"):
            #     print(chunk)

        for lay in lay2_items_list:
            print()
            print(f"Area point: {lay.area_start_cursor}")

            lay.header.str = str_list[lay.header.str_id]
            print(lay.header)
            for lay2_item in lay.items:
                lay2_item.str_content = str_list[lay2_item.item_id]
                for chunk in txos_chunks:
                    if chunk.id == lay2_item.txos_id:
                        lay2_item.txos = chunk
                        print(lay2_item)
