import struct


class TXOSChunk:
    def __init__(self, data, id):
        self.data = data

        self.id = id
        self.type = struct.unpack("<I", data[0x00:0x04])[0]
        self.flags = struct.unpack("<I", data[0x04:0x08])[0]
        self.matrix_a = struct.unpack("<I", data[0x08:0x0C])[0]
        self.matrix_b = struct.unpack("<I", data[0x0C:0x10])[0]
        self.screen_x = struct.unpack("<I", data[0x10:0x14])[0]
        self.point_x = struct.unpack("<I", data[0x14:0x18])[0]
        self.point_y = struct.unpack("<I", data[0x18:0x1C])[0]
        self.width = struct.unpack("<I", data[0x1C:0x20])[0]
        self.height = struct.unpack("<I", data[0x20:0x24])[0]
        self.src_y = struct.unpack("<I", data[0x24:0x28])[0]
        self.dst_x = struct.unpack("<I", data[0x28:0x2C])[0]
        self.dst_y = struct.unpack("<I", data[0x2C:0x30])[0]
        self.blend_mode = struct.unpack("<I", data[0x30:0x34])[0]
        self.str_id = struct.unpack("<I", data[0x34:0x38])[0]
        self.color = struct.unpack("<I", data[0x38:0x3C])[0]
        self.child_count = struct.unpack("<I", data[0x3C:0x40])[0]
        self.str = ""

    def fill_str(self, value):
        self.str = value

    def __str__(self):
        return f"""
            [
                id: {self.id},
                point_x: {self.point_x},
                point_y: {self.point_y},
                width: {self.width},
                height: {self.height},
                str_id: {self.str_id},
                str: {self.str},
                
                type: {self.type},
                flags: {self.flags},
                matrix_a: {self.matrix_a},
                matrix_b: {self.matrix_b},
                screen_x: {self.screen_x},
                src_y: {self.src_y},
                dst_x: {self.dst_x},
                dst_y: {self.dst_y},
                blend_mode: {self.blend_mode},
                color: {self.color},
                child_count: {self.child_count},
            ]
        """


class LAY2Item:
    """代表 LAY2 中的一个显示项，关联 TXOS 资源"""

    def __init__(self, txos_id, x, y, width_or_x2, height_or_y2, priority, ref_w, ref_h):
        self.txos_id = txos_id  # 关联 TXOS 的 Item ID

        # 基础布局属性
        self.base_x = x
        self.base_y = y
        # 这两个字段在全屏元素下代表坐标(960, 544)，在普通元素下代表宽高
        self.layout_w = width_or_x2
        self.layout_h = height_or_y2

        # 修正后的关键字段
        self.priority = priority  # 优先级/层级，或者是某些情况下的参考宽
        self.ref_w = ref_w  # 参考画布宽度 (通常为 960)
        self.ref_h = ref_h  # 参考画布高度 (通常为 544)

        # 变换属性（由后续的 0x34 块提供修正）
        self.offset_x = 0
        self.offset_y = 0
        self.scale_x = 100
        self.scale_y = 100
        self.rgba = 0xFFFFFFFF
        self.txos_ref = None  # 用于后续关联 TXOS 对象

    def apply_transform(self, offset_x, offset_y, rgba, scale_x, scale_y):
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.rgba = rgba
        self.scale_x = scale_x
        self.scale_y = scale_y

    def __repr__(self):
        color_hex = f"{self.rgba:08X}"
        # 逻辑计算：最终坐标 = 基础坐标 + 偏移
        final_x = self.base_x + self.offset_x
        final_y = self.base_y + self.offset_y
        return (f"<Item TXOS:{self.txos_id} Pos:({final_x}, {final_y}) "
                f"Layout:({self.layout_w}x{self.layout_h}) Pri:{self.priority} "
                f"Canvas:{self.ref_w}x{self.ref_h} Color:#{color_hex}>")


class LAY2Node:
    def __init__(self, data, node_id=0):
        self.data = data
        self.items = []  # 解析出的所有 Item
        self._parse()

    def _parse(self):
        ptr = 0
        data_len = len(self.data)
        item_list = []

        while ptr + 4 <= data_len:
            # 预读前 4 字节
            tag = struct.unpack("<I", self.data[ptr:ptr + 4])[0]

            tx_id = 0
            # --- 情况 3: 修正后的 0x30 块解析 ---
            if tag == 0x30:
                tx_id = struct.unpack("<I", self.data[ptr + 0x24: ptr + 0x28])[0]

            # --- 情况 1: 组容器 Header (D8 或 3C) ---
            # 这种块只有 8 字节，表示一个容器的开始
            if tag == 0xD8 or tag == 0x3C:
                child_count = struct.unpack("<I", self.data[ptr + 4:ptr + 8])[0]
                # print(f"发现容器: Type={hex(tag)}, 子项目数={child_count}")
                ptr += 8  # 仅跳过 Header，继续解析后面的内容

            # --- 情况 2: 变换属性块 (34 00 14 00) ---
            # 这种块通常是 0x34 (52) 字节
            elif tag == 0x00140034:
                # 这里可以解析颜色、缩放等变换
                # ... 解析逻辑 ...
                ptr += 0x34

            # --- 情况 3: 真正的显示项 (0x30 块) ---
            # 我们通过检查 0x2C 偏移处是否为 0x30 来确认
            elif ptr + 0x30 <= data_len and struct.unpack("<I", self.data[ptr + 0x2C:ptr + 0x30])[0] == 0x30:
                # 按上面修正的表格解析
                inst_id = struct.unpack("<I", self.data[ptr:ptr + 4])[0]
                # tx_id = struct.unpack("<I", self.data[ptr + 4:ptr + 8])[0]
                x = struct.unpack("<I", self.data[ptr + 8:ptr + 12])[0]
                y = struct.unpack("<I", self.data[ptr + 12:ptr + 16])[0]
                w = struct.unpack("<I", self.data[ptr + 16:ptr + 20])[0]
                h = struct.unpack("<I", self.data[ptr + 20:ptr + 24])[0]
                cw = struct.unpack("<I", self.data[ptr + 24:ptr + 28])[0]
                ch = struct.unpack("<I", self.data[ptr + 28:ptr + 32])[0]

                new_item = LAY2Item(tx_id, x, y, w, h, inst_id, cw, ch)
                item_list.append(new_item)
                ptr += 0x30

            # --- 情况 4: 空白或对齐填充 ---
            elif tag == 0:
                ptr += 4
            else:
                # 遇到未知数据，按 4 字节步进尝试重新找回同步
                ptr += 4

        self.items = item_list

    def link_txos(self, txos_chunks):
        for item in self.items:
            for chunk in txos_chunks:
                # 假定的, 不一定准确
                if chunk.id + chunk.str_id == item.base_y:
                    item.txos_ref = chunk


if __name__ == "__main__":
    cursor_idx = 0
    with (open("ark_data/origin/gallery.ark", 'rb') as f):
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

        # print(f"txos_chunks: {txos_chunks}")
        # ss = [obj.parent_texture_id for obj in txos_chunks]

        # --------------------------------------------------------------------------
        # Lay2 items
        # 布局逻辑块：定义 Item 如何组合成“词组”或“页面”
        lay2_items_list = []

        for i in range(lay2_chunk_size):
            lay2_title_size = 0x08
            lay2_title_data = data[cursor_idx:cursor_idx + lay2_title_size]
            cursor_idx += lay2_title_size
            if lay2_title_data != b'ARK LAY2':
                raise Exception("LAY2 area error")

            lay2_area_len_size = 0x08
            lay2_area_data = struct.unpack(
                '<Q', data[cursor_idx:cursor_idx + lay2_area_len_size]
            )[0]
            cursor_idx += lay2_area_len_size

            lay2_content = data[cursor_idx:cursor_idx + lay2_area_data]
            cursor_idx += lay2_area_data

            lay2_node = LAY2Node(lay2_content)
            lay2_node.link_txos(txos_chunks)  # 关键：在这里建立引用关系

            for item in lay2_node.items:
                print(f"LAY2元素引用了 TXOS ID: {item.txos_id}")
                if item.txos_ref:
                    print(f"  -> 对应贴图实际尺寸: {item.txos_ref.width}x{item.txos_ref.height}")
                    print(f"  -> 对应字符串说明: {item.txos_ref.str}")

            pass

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
            str_part = parse_str(start_idx)
            str_list.append(str_part)
            idx_table_idx += 4

        # print(f"str_items: {len(str_list)}")
        print(str_list)

        for chunk in txos_chunks:
            chunk.fill_str(str_list[chunk.str_id])
            if chunk.str.startswith("word"):
                print(chunk)

        # for lay in lay2_items_list:
        #     lay.fill_str(str_list)
        #     print(lay)
