import sys
import csv
import struct
from pathlib import Path

# The original pointer table can be restored by PSV/SCE relocation metadata at
# load time. Let the original memcpy copy the relocated table to the stack, then
# reorder that stack table before the title objects are created.
CODE_CAVE_POINT = 0x002E9A0C
CODE_CAVE_VA = 0x812E992C
FUN_8110C180_AFTER_MEMCPY_POINT = 0x0010C32C
FUN_8110C180_AFTER_MEMCPY_VA = 0x8110C24C
FUN_8110C180_LOOP_INIT_VA = 0x8110C250

TXOS_ATLAS_X_POINT = 0x1C
TXOS_ATLAS_Y_POINT = 0x20

LAY2_ITEM_TXOS_ID_POINT = 0x24
LAY2_KEYFRAME_SIZE = 0x34
LAY2_KEYFRAME_DRAW_OFFSET_X_POINT = 0x14
LAY2_KEYFRAME_DRAW_OFFSET_Y_POINT = 0x18
LAY2_KEYFRAME_MOTION_Y_POINT = 0x24
TITLE_GLYPH_BASELINE_X = 25
TITLE_GLYPH_BASELINE_Y = 8
TITLE_GLYPH_SPACING_X = 40


def encode_arm_branch(src_va, dst_va, link=False):
    delta = dst_va - (src_va + 8)
    if delta % 4 != 0:
        raise ValueError("ARM branch target must be 4-byte aligned")
    imm24 = (delta >> 2) & 0x00FFFFFF
    op = 0xEB000000 if link else 0xEA000000
    return struct.pack("<I", op | imm24)


def encode_arm_ldr_sp(rt, imm12):
    return struct.pack("<I", 0xE59D0000 | (rt << 12) | imm12)


def encode_arm_str_sp(rt, imm12):
    return struct.pack("<I", 0xE58D0000 | (rt << 12) | imm12)


def write_u32(data, point, value):
    data[point:point + 0x04] = struct.pack("<I", value)


def write_i32(data, point, value):
    data[point:point + 0x04] = struct.pack("<i", value)


def read_u32(data, point):
    return struct.unpack("<I", data[point:point + 0x04])[0]


def read_i32(data, point):
    return struct.unpack("<i", data[point:point + 0x04])[0]


def read_u64(data, point):
    return struct.unpack("<Q", data[point:point + 0x08])[0]


def collect_lay2_chunks(ark_data):
    cursor = 0x10
    arkf_size = read_u64(ark_data, cursor + 0x08)
    lay2_count = read_u32(ark_data, cursor + 0x14)
    cursor += 0x10 + arkf_size

    tex2_size = read_u64(ark_data, cursor + 0x08)
    cursor += 0x10 + tex2_size

    txos_size = read_u64(ark_data, cursor + 0x08)
    cursor += 0x10 + txos_size

    chunks = []
    for _ in range(lay2_count):
        if ark_data[cursor:cursor + 0x08] != b"ARK LAY2":
            raise ValueError(f"LAY2 chunk expected at 0x{cursor:X}")

        chunk_size = read_u64(ark_data, cursor + 0x08)
        total_end = cursor + 0x10 + chunk_size
        item_count = read_u32(ark_data, cursor + 0x24)
        item_start = cursor + 0x40
        item_end = item_start + item_count * 0x30
        chunks.append((item_start, item_end, total_end))
        cursor = total_end

    return chunks


def get_title_glyph_target_x(item_index, item_count):
    if item_count >= 9 and item_index >= 5:
        row_index = item_index - 5
    elif item_count == 8 and item_index >= 4:
        row_index = item_index - 4
    else:
        row_index = item_index
    return TITLE_GLYPH_BASELINE_X + row_index * TITLE_GLYPH_SPACING_X


def normalize_lay2_keyframe_draw_offset(ark_data, lay2_chunks, txos_id_point):
    item_point = txos_id_point - LAY2_ITEM_TXOS_ID_POINT

    for item_start, item_end, total_end in lay2_chunks:
        if not item_start <= item_point < item_end:
            continue

        item_index = (item_point - item_start) // 0x30
        item_count = (item_end - item_start) // 0x30
        block_point = item_end
        for block_index in range(item_index + 1):
            block_size = read_u32(ark_data, block_point)
            frame_count = read_u32(ark_data, block_point + 0x04)

            if block_size == 0 or block_point + block_size > total_end:
                raise ValueError(f"Invalid LAY2 animation block at 0x{block_point:X}")

            if block_index == item_index:
                frame_points = [
                    block_point + 0x08 + frame_index * LAY2_KEYFRAME_SIZE
                    for frame_index in range(frame_count)
                ]
                baseline_y = None
                for frame_point in frame_points:
                    motion_y = read_i32(ark_data, frame_point + LAY2_KEYFRAME_MOTION_Y_POINT)
                    if motion_y == 0:
                        baseline_y = read_i32(ark_data, frame_point + LAY2_KEYFRAME_DRAW_OFFSET_Y_POINT)
                        break

                if baseline_y is None:
                    baseline_y = read_i32(ark_data, frame_points[0] + LAY2_KEYFRAME_DRAW_OFFSET_Y_POINT)

                baseline_x = read_i32(ark_data, frame_points[0] + LAY2_KEYFRAME_DRAW_OFFSET_X_POINT)
                delta_x = get_title_glyph_target_x(item_index, item_count) - baseline_x
                delta_y = TITLE_GLYPH_BASELINE_Y - baseline_y
                for frame_point in frame_points:
                    draw_offset_x = read_i32(ark_data, frame_point + LAY2_KEYFRAME_DRAW_OFFSET_X_POINT)
                    draw_offset_y = read_i32(ark_data, frame_point + LAY2_KEYFRAME_DRAW_OFFSET_Y_POINT)
                    write_i32(ark_data, frame_point + LAY2_KEYFRAME_DRAW_OFFSET_X_POINT, draw_offset_x + delta_x)
                    write_i32(ark_data, frame_point + LAY2_KEYFRAME_DRAW_OFFSET_Y_POINT, draw_offset_y + delta_y)
                return

            block_point += block_size

    raise ValueError(f"LAY2 item not found for txos_id point 0x{txos_id_point:X}")


def encode_stack_ptr_reorder_code():
    def table_off(index):
        return 0x10 + index * 4

    # Copy from the original Japanese title order after the loader has already
    # relocated the pointers. Order matters because writes also modify sources.
    moves = [
        (30, 27),  # word_ko -> 抽鬼牌 third char
        (31, 30),  # word_me -> 随谈 first char
        (23, 26),  # word_shi -> 抽鬼牌 second char
        (21, 25),  # word_ki -> 抽鬼牌 first char
        (20, 21),  # word_nu -> 潜行游戏 second char
        (17, 20),  # word_bi -> 潜行游戏 first char
        (16, 17),  # word_so -> 小游戏 third char
        (16, 23),  # word_so -> 潜行游戏 fourth char
        (13, 16),  # word_ku -> 小游戏 second char
        (13, 22),  # word_ku -> 潜行游戏 third char
        (12, 15),  # word_ga -> 小游戏 first char
        (10, 12),  # word_o -> 恋爱曲调 third char
        (11, 13),  # word_n -> 恋爱曲调 fourth char
        (5, 10),  # word_a -> 恋爱曲调 first char
        (6, 11),  # word_ru -> 恋爱曲调 second char
        (4, 18),  # long vowel/gap -> 小游戏 fourth char
        (4, 28),  # long vowel/gap -> 抽鬼牌 fourth char
        (4, 31),  # long vowel/gap -> 随谈 spacing
        (4, 32),  # long vowel/gap -> 随谈 spacing
    ]

    code = bytearray()
    for src, dst in moves:
        code.extend(encode_arm_ldr_sp(0, table_off(src)))
        code.extend(encode_arm_str_sp(0, table_off(dst)))
    code.extend(struct.pack("<I", 0xE3A08000))  # mov r8, #0
    code.extend(encode_arm_branch(CODE_CAVE_VA + len(code), FUN_8110C180_LOOP_INIT_VA))
    return code


def patch_eboot():
    print("Start patching EBOOT ...")
    output_dir = "eboot/modified"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    eboot_data = bytearray(Path("eboot/origin/eboot.elf").read_bytes())

    with open("eboot/code_config.csv", mode='r', encoding="utf-8") as config_f:
        config_reader = csv.DictReader(config_f)
        for row in config_reader:
            origin_char = row["char"]
            new_char = row["new_char"]

            origin_len = len(origin_char.encode("ascii"))
            new_byte = new_char.encode("ascii")
            final_byte = new_byte + ((origin_len - len(new_byte)) * b"\x00")

            point = int(row["data_point"], 16)
            eboot_data[point:point + origin_len] = final_byte

    code = encode_stack_ptr_reorder_code()
    eboot_data[CODE_CAVE_POINT:CODE_CAVE_POINT + len(code)] = code
    eboot_data[FUN_8110C180_AFTER_MEMCPY_POINT:FUN_8110C180_AFTER_MEMCPY_POINT + 4] = (
        encode_arm_branch(FUN_8110C180_AFTER_MEMCPY_VA, CODE_CAVE_VA, link=False)
    )

    Path(f"{output_dir}/eboot.elf").write_bytes(eboot_data)

    print("EBOOT patching finished.")


output_ark = "ark_data/new_gallery.ark"


def patch_ark():
    print("Start patching ark file ...")
    ark_data = bytearray(Path("ark_data/origin/gallery.ark").read_bytes())
    lay2_chunks = collect_lay2_chunks(ark_data)

    with open("ark_data/update_config.csv", mode='r', encoding="utf-8") as config_f:
        config_reader = csv.DictReader(config_f)
        for row in config_reader:
            # Override str data
            origin_char = row["origin_str"]
            new_char = row["new_str"]

            origin_len = len(origin_char.encode("ascii"))
            new_byte = new_char.encode("ascii")
            final_byte = new_byte + ((origin_len - len(new_byte)) * b"\x00")

            str_point = int(row["str_point"], 16)
            ark_data[str_point:str_point + origin_len] = final_byte

            # Override txos data
            txos_point = int(row["txos_point"], 16)
            x = int(row["x"])
            y = int(row["y"])
            write_u32(ark_data, txos_point + TXOS_ATLAS_X_POINT, x)
            write_u32(ark_data, txos_point + TXOS_ATLAS_Y_POINT, y)

            # Override lay2 data
            txos_id = int(row["txos_id"])
            lay2_ptrs = row["lay2_ptrs"].split(",")
            for lay2_ptr in lay2_ptrs:
                lay2_ptr = int(lay2_ptr, 16)
                write_u32(ark_data, lay2_ptr, txos_id)
                normalize_lay2_keyframe_draw_offset(ark_data, lay2_chunks, lay2_ptr)

        Path(output_ark).write_bytes(ark_data)

        print(f"Ark file patching finished. output: {output_ark}")


if __name__ == "__main__":
    try:
        output_ark = sys.argv[1]
    except Exception:
        pass

    patch_eboot()
    patch_ark()
