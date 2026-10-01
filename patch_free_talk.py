import struct
import sys
from pathlib import Path


FREE_TALK_PARENT_LAY2_NAME = "comment_in_out"
OVERLAY_LAY2_NAME = "comment_unused"
VISIBLE_WIDTH = 960
VISIBLE_HEIGHT = 544

# Slot order comes from the original comment_in_out LAY2 item order.
# Change only this table if a role image appears on the wrong free-talk item.
FREE_TALK_SLOT_TO_CODE = (
    "RAK", "CTG", "KSK", "SSR", "MRK", "RUR", "SYU", "OTM",
    "CLD", "RYU", "RAP", "CTP", "MRP", "HND", "KYK", None,
)
FREE_TALK_SLOT_TO_KEY = (0, 1, 2, 3, 4, 5, 6, 8, 7, 12, 10, 11, 15, 14, 9, 107)

FREE_TALK_ACTIVE_SLOT_KEYS = tuple(
    key for code, key in zip(FREE_TALK_SLOT_TO_CODE, FREE_TALK_SLOT_TO_KEY)
    if code
)

FREE_TALK_OVERLAY_CODES = tuple(code for code in FREE_TALK_SLOT_TO_CODE if code)
INVALID_CHILD_INDEX = 0xFF
OVERLAY_RESERVED_CHILD_COUNT = 4
FREE_TALK_KEY_TO_CHILD_INDEX = [INVALID_CHILD_INDEX] * 16
for _overlay_index, _slot_key in enumerate(FREE_TALK_ACTIVE_SLOT_KEYS):
    FREE_TALK_KEY_TO_CHILD_INDEX[_slot_key] = OVERLAY_RESERVED_CHILD_COUNT + _overlay_index
FREE_TALK_KEY_TO_CHILD_INDEX = tuple(FREE_TALK_KEY_TO_CHILD_INDEX)

LAY2_HEADER_SIZE = 0x30
LAY2_ITEM_SIZE = 0x30
TEX2_ENTRY_SIZE = 0x10
TXOS_ENTRY_SIZE = 0x40
CHUNK_HEADER_SIZE = 0x10

EBOOT_BASE_VA = 0x80FFFF20

CODE_CAVE_POINT = 0x002FDAA8
CODE_CAVE_SIZE = 0xA00
HIDE_FUNC_CAVE_OFFSET = 0x100
SHOW_FUNC_CAVE_OFFSET = 0x180
CHILD_INDEX_TABLE_CAVE_OFFSET = 0x780

FUNC_PREPARE_VISIBLE_VA = 0x810482B4
FUNC_SET_VISIBLE_VA = 0x81048914
FUNC_OBJECT_SET_VISIBLE_VA = 0x811942C0

# Free-talk object field for the original slot 16 parent handle: comment_unused.
COMMENT_UNUSED_PARENT_HANDLE_OFFSET = 0x1E8
FREE_TALK_PLAYING_FLAG_OFFSET = 0x204
FREE_TALK_STATE_OFFSET = 0x10
FREE_TALK_ROOT_SLOT_CACHE_OFFSET = 0x22C

HOOK_HIDE_ON_AUDIO_END = (0x0011D4F0, 0x8111D410, 0x8111D414)
HOOK_HIDE_ON_EXIT = (0x0011DA7C, 0x8111D99C, 0x8111D9A0)
HOOK_SHOW_ON_PLAY = (0x0011D1B8, 0x8111D0D8, 0x8111D134)
HOOK_HIDE_ON_STOP_A = (0x0011CDBC, 0x8111CCDC, 0x8111CCE0)
HOOK_HIDE_ON_STOP_B = (0x0011CE1C, 0x8111CD3C, 0x8111CD40)
HOOK_HIDE_ON_UPDATE = (0x0011DBA0, 0x8111DAC0, 0x8111DAC4)
HOOK_HIDE_ON_INIT = (0x0011CB2C, 0x8111CA4C, 0x8111CA50)

R0, R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, SP, _, PC = range(16)

PRESERVE_CALL_MASK = 0x5003  # r0, r1, r12, lr
PRESERVE_ALL_LR_MASK = 0x5FFF  # r0-r12, lr
PRESERVE_ALL_PC_MASK = 0x9FFF  # r0-r12, pc


def read_u32(data, point):
    return struct.unpack("<I", data[point:point + 4])[0]


def read_i32(data, point):
    return struct.unpack("<i", data[point:point + 4])[0]


def read_u64(data, point):
    return struct.unpack("<Q", data[point:point + 8])[0]


def write_u32(data, point, value):
    data[point:point + 4] = struct.pack("<I", value)


def align(value, unit):
    return (value + unit - 1) // unit * unit


def point_to_va(point):
    return EBOOT_BASE_VA + point


def encode_arm_branch(src_va, dst_va, link=False, cond=0xE):
    delta = dst_va - (src_va + 8)
    if delta % 4 != 0:
        raise ValueError("ARM branch target must be 4-byte aligned")
    imm24 = (delta >> 2) & 0x00FFFFFF
    op = (cond << 28) | (0x0B000000 if link else 0x0A000000)
    return struct.pack("<I", op | imm24)


def encode_movw(rd, imm16):
    return struct.pack("<I", 0xE3000000 | (((imm16 >> 12) & 0xF) << 16) | (rd << 12) | (imm16 & 0xFFF))


def encode_movt(rd, imm16):
    return struct.pack("<I", 0xE3400000 | (((imm16 >> 12) & 0xF) << 16) | (rd << 12) | (imm16 & 0xFFF))


def encode_load_u32(rd, value):
    return encode_movw(rd, value & 0xFFFF) + encode_movt(rd, (value >> 16) & 0xFFFF)


def encode_ldr(rd, rn, imm12=0):
    return struct.pack("<I", 0xE5900000 | (rn << 16) | (rd << 12) | imm12)


def encode_ldr_reg_scaled(rd, rn, rm, shift=0):
    return struct.pack("<I", 0xE7900000 | (rn << 16) | (rd << 12) | (shift << 7) | rm)


def encode_ldrb(rd, rn, imm12=0):
    return struct.pack("<I", 0xE5D00000 | (rn << 16) | (rd << 12) | imm12)


def encode_str(rd, rn, imm12=0):
    return struct.pack("<I", 0xE5800000 | (rn << 16) | (rd << 12) | imm12)


def encode_strb(rd, rn, imm12=0):
    return struct.pack("<I", 0xE5C00000 | (rn << 16) | (rd << 12) | imm12)


def encode_mov_imm(rd, imm12):
    return struct.pack("<I", 0xE3A00000 | (rd << 12) | imm12)


def encode_mov_reg(rd, rm):
    return struct.pack("<I", 0xE1A00000 | (rd << 12) | rm)


def encode_mov_reg_shift(rd, rm, shift_type, shift_imm):
    return struct.pack("<I", 0xE1A00000 | (rd << 12) | (shift_imm << 7) | (shift_type << 5) | rm)


def encode_add_reg(rd, rn, rm):
    return struct.pack("<I", 0xE0800000 | (rn << 16) | (rd << 12) | rm)


def encode_add_imm(rd, rn, imm12):
    return struct.pack("<I", 0xE2800000 | (rn << 16) | (rd << 12) | imm12)


def encode_cmp_imm(rn, imm12):
    return struct.pack("<I", 0xE3500000 | (rn << 16) | imm12)


def encode_cmp_reg(rn, rm):
    return struct.pack("<I", 0xE1500000 | (rn << 16) | rm)


def encode_push(mask):
    return struct.pack("<I", 0xE92D0000 | mask)


def encode_pop(mask):
    return struct.pack("<I", 0xE8BD0000 | mask)


def encode_load_pc_relative_address(rd, target_va, instruction_va):
    add_instruction_va = instruction_va + 8
    add_pc_va = add_instruction_va + 8
    delta = (target_va - add_pc_va) & 0xFFFFFFFF
    return encode_load_u32(rd, delta) + encode_add_reg(rd, PC, rd)


def append_skip_branch(code, skip_branches, cond=0x0, base_offset=0):
    skip_branches.append((base_offset + append_branch_placeholder(code), cond))


def append_branch_placeholder(code):
    point = len(code)
    code += b"\x00\x00\x00\x00"
    return point


def patch_skip_branches(code, func_va, skip_branches):
    cleanup_va = func_va + len(code)
    for branch_point, cond in skip_branches:
        code[branch_point:branch_point + 4] = encode_arm_branch(
            func_va + branch_point,
            cleanup_va,
            cond=cond,
        )


def parse_ark(data):
    if data[:0x10] != b"ENDILTLE\x00\x00\x00\x00\x00\x00\x00\x00":
        raise ValueError("Not an ARK file")

    cursor = 0x10
    if data[cursor:cursor + 8] != b"ARK ARKF":
        raise ValueError("ARKF chunk not found")
    arkf_pos = cursor
    cursor += CHUNK_HEADER_SIZE + read_u64(data, arkf_pos + 8)

    tex2_pos = cursor
    if data[tex2_pos:tex2_pos + 8] != b"ARK TEX2":
        raise ValueError("TEX2 chunk not found")
    cursor += CHUNK_HEADER_SIZE + read_u64(data, tex2_pos + 8)

    txos_pos = cursor
    if data[txos_pos:txos_pos + 8] != b"ARK TXOS":
        raise ValueError("TXOS chunk not found")
    cursor += CHUNK_HEADER_SIZE + read_u64(data, txos_pos + 8)

    lay2_count = read_u32(data, arkf_pos + 0x14)
    lay2_start = cursor
    for _ in range(lay2_count):
        if data[cursor:cursor + 8] != b"ARK LAY2":
            raise ValueError(f"LAY2 chunk not found at 0x{cursor:X}")
        cursor += CHUNK_HEADER_SIZE + read_u64(data, cursor + 8)
    lay2_end = cursor

    str_pos = cursor
    if data[str_pos:str_pos + 8] != b"GENESTRT":
        raise ValueError("GENESTRT chunk not found")
    str_end = str_pos + CHUNK_HEADER_SIZE + read_u64(data, str_pos + 8)

    return {
        "arkf_pos": arkf_pos,
        "tex2_pos": tex2_pos,
        "txos_pos": txos_pos,
        "lay2_start": lay2_start,
        "lay2_end": lay2_end,
        "str_pos": str_pos,
        "str_end": str_end,
    }


def parse_strings(str_content):
    count = read_u32(str_content, 0)
    idx_size = read_u32(str_content, 8)
    str_data = str_content[idx_size:]
    strings = []
    for index in range(count):
        offset = read_u32(str_content, 0x10 + index * 4)
        end = str_data.index(b"\x00", offset)
        strings.append(str_data[offset:end].decode("utf-8"))
    return strings


def rebuild_strings(strings):
    offsets = bytearray()
    str_data = bytearray()
    for text in strings:
        offsets += struct.pack("<I", len(str_data))
        str_data += text.encode("utf-8") + b"\x00"

    idx_size = 0x10 + len(offsets)
    total_unaligned_size = idx_size + len(str_data)
    padding = bytearray(align(total_unaligned_size, 0x10) - total_unaligned_size)
    return (
        struct.pack("<IIII", len(strings), 0x10, idx_size, total_unaligned_size + len(padding)) +
        offsets +
        str_data +
        padding
    )


def get_or_add_string(strings, value):
    try:
        return strings.index(value)
    except ValueError:
        strings.append(value)
        return len(strings) - 1


def get_string(strings, index):
    return strings[index] if index < len(strings) else ""


def overlay_texture_name(code):
    return f"FRE_{code}_cmt.gxt"


def overlay_txos_name(code):
    return f"FRE_{code}_cmt"


def overlay_item_name(code):
    return f"free_talk_cmt_{code.lower()}"


def iter_lay2_chunks(lay2_region):
    cursor = 0
    index = 0
    while cursor < len(lay2_region):
        if lay2_region[cursor:cursor + 8] != b"ARK LAY2":
            raise ValueError(f"LAY2 chunk not found at region offset 0x{cursor:X}")
        chunk_size = read_u64(lay2_region, cursor + 8)
        content_start = cursor + CHUNK_HEADER_SIZE
        content_end = content_start + chunk_size
        yield index, cursor, chunk_size, lay2_region[content_start:content_end]
        index += 1
        cursor = content_end


def find_lay2_index(lay2_region, strings, lay2_name):
    for index, _, _, content in iter_lay2_chunks(lay2_region):
        if get_string(strings, read_u32(content, 0)) == lay2_name:
            return index
    raise ValueError(f"LAY2 not found: {lay2_name}")


def find_lay2_item_index(content, strings, item_name):
    item_count = read_u32(content, 0x14)
    item_start = LAY2_HEADER_SIZE
    item_end = item_start + item_count * LAY2_ITEM_SIZE
    if item_end > len(content):
        raise ValueError("LAY2 item table exceeds chunk size")

    for item_index in range(item_count):
        item_point = item_start + item_index * LAY2_ITEM_SIZE
        item_name_id = read_u32(content, item_point + 0x10)
        if get_string(strings, item_name_id) == item_name:
            return item_index

    raise ValueError(f"LAY2 item not found: {item_name}")


def build_lay2_item(inst, name_id, width, height, ref_or_txos_id):
    return struct.pack(
        "<IIIIIIIIIIII",
        LAY2_ITEM_SIZE,
        inst,
        0,
        0,
        name_id,
        width,
        height,
        width // 2,
        height // 2,
        ref_or_txos_id,
        0,
        0,
    )


def build_static_anim_block(draw_x=0, draw_y=0):
    keyframe = struct.pack(
        "<IIIIiiiIIIIII",
        0x00140034,
        0x1F,
        0,
        0,
        0,
        draw_x,
        draw_y,
        0xFFFFFFFF,
        0,
        0,
        0,
        100,
        100,
    )
    return struct.pack("<II", 0x3C, 1) + keyframe


def split_lay2_content(content):
    item_count = read_u32(content, 0x14)
    item_table_end = LAY2_HEADER_SIZE + item_count * LAY2_ITEM_SIZE
    if item_table_end > len(content):
        raise ValueError("LAY2 item table exceeds chunk size")

    anim_blocks = []
    cursor = item_table_end
    for block_index in range(item_count):
        if cursor + 8 > len(content):
            raise ValueError(f"Missing LAY2 animation block {block_index}")
        block_size = read_u32(content, cursor)
        if block_size < 8 or cursor + block_size > len(content):
            raise ValueError(f"Invalid LAY2 animation block at 0x{cursor:X}")
        anim_blocks.append(content[cursor:cursor + block_size])
        cursor += block_size
    if cursor != len(content):
        raise ValueError("Unexpected trailing bytes in LAY2 content")

    return (
        bytearray(content[:LAY2_HEADER_SIZE]),
        bytearray(content[LAY2_HEADER_SIZE:item_table_end]),
        anim_blocks,
    )


def get_item_final_draw_offset(content, item_index):
    _, _, anim_blocks = split_lay2_content(content)
    block = anim_blocks[item_index]
    frame_count = read_u32(block, 0x04)
    if frame_count == 0:
        raise ValueError("LAY2 animation block has no keyframes")
    frame_point = 0x08 + (frame_count - 1) * 0x34
    return read_i32(block, frame_point + 0x14), read_i32(block, frame_point + 0x18)


def build_overlay_lay2_content(original_content, overlay_items, overlay_draw_offset):
    header, original_items, original_anim_blocks = split_lay2_content(original_content)
    original_count = len(original_anim_blocks)
    if original_count != OVERLAY_RESERVED_CHILD_COUNT:
        raise ValueError(f"Unexpected {OVERLAY_LAY2_NAME} child count: {original_count}")

    item_count = original_count + len(overlay_items)
    item_table_end = LAY2_HEADER_SIZE + item_count * LAY2_ITEM_SIZE
    write_u32(header, 0x14, item_count)
    write_u32(header, 0x20, LAY2_ITEM_SIZE)
    write_u32(header, 0x24, item_table_end)

    content = bytearray(header)
    content += original_items
    for item_str_id, txos_id in overlay_items:
        content += build_lay2_item(5, item_str_id, VISIBLE_WIDTH, VISIBLE_HEIGHT, txos_id)
    for block in original_anim_blocks:
        content += block
    for _ in overlay_items:
        content += build_static_anim_block(*overlay_draw_offset)
    return content


def get_comment_unused_local_draw_offset(content, strings, overlay_lay2_index):
    item_index = find_lay2_item_index(content, strings, OVERLAY_LAY2_NAME)
    item_point = LAY2_HEADER_SIZE + item_index * LAY2_ITEM_SIZE
    item_type = read_u32(content, item_point + 0x04)
    item_ref = read_u32(content, item_point + 0x24)
    if item_type != 4 or item_ref != overlay_lay2_index:
        raise ValueError(f"Unexpected {OVERLAY_LAY2_NAME} parent item: type={item_type}, ref={item_ref}")
    parent_x, parent_y = get_item_final_draw_offset(content, item_index)
    parent_x += read_i32(content, item_point + 0x08)
    parent_y += read_i32(content, item_point + 0x0C)
    return -parent_x, -parent_y


def get_overlay_draw_offset(lay2_region, strings):
    overlay_lay2_index = find_lay2_index(lay2_region, strings, OVERLAY_LAY2_NAME)
    for _, _, _, content in iter_lay2_chunks(lay2_region):
        lay2_name = get_string(strings, read_u32(content, 0))
        if lay2_name == FREE_TALK_PARENT_LAY2_NAME:
            return get_comment_unused_local_draw_offset(content, strings, overlay_lay2_index)
    raise ValueError(f"LAY2 not found: {FREE_TALK_PARENT_LAY2_NAME}")


def patch_lay2_region(lay2_region, strings, overlay_items):
    overlay_draw_offset = get_overlay_draw_offset(lay2_region, strings)
    result = bytearray()
    patched_overlay = False

    for _, _, _, content in iter_lay2_chunks(lay2_region):
        lay2_name = get_string(strings, read_u32(content, 0))
        if lay2_name == OVERLAY_LAY2_NAME:
            content = build_overlay_lay2_content(content, overlay_items, overlay_draw_offset)
            patched_overlay = True

        result += b"ARK LAY2" + struct.pack("<Q", len(content)) + content

    if not patched_overlay:
        raise ValueError(f"LAY2 not found: {OVERLAY_LAY2_NAME}")

    return result


def append_tex2_entry(tex2_content, gxt_str_id):
    tex2_count = read_u32(tex2_content, 0)
    if read_u32(tex2_content, 4) != TEX2_ENTRY_SIZE or read_u32(tex2_content, 8) != 0x10:
        raise ValueError("Unexpected TEX2 layout")
    patched = bytearray(tex2_content)
    patched += struct.pack("<IIII", gxt_str_id, 0, 0, 0)
    write_u32(patched, 0, tex2_count + 1)
    return patched, tex2_count


def append_txos_entry(txos_content, txos_str_id, tex2_id):
    txos_count = read_u32(txos_content, 0)
    if read_u32(txos_content, 4) != TXOS_ENTRY_SIZE:
        raise ValueError("Unexpected TXOS layout")

    txos_entry = struct.pack(
        "<IIIIIIIIIIIIIIII",
        0,
        0,
        0x80000000,
        0,
        tex2_id,
        0,
        0,
        VISIBLE_WIDTH,
        VISIBLE_HEIGHT,
        0x00010001,
        0x00010001,
        0,
        0,
        txos_str_id,
        0,
        0,
    )
    table_end = 8 + txos_count * TXOS_ENTRY_SIZE
    patched = bytearray(txos_content[:table_end] + txos_entry + txos_content[table_end:])
    write_u32(patched, 0, txos_count + 1)
    return patched, txos_count


def patch_ark(ark_path):
    ark_path = Path(ark_path)
    data = bytearray(ark_path.read_bytes())
    parts = parse_ark(data)

    str_content = data[parts["str_pos"] + CHUNK_HEADER_SIZE:parts["str_end"]]
    strings = parse_strings(str_content)

    original_lay2_count = read_u32(data, parts["arkf_pos"] + 0x14)

    tex2_content = bytearray(data[parts["tex2_pos"] + CHUNK_HEADER_SIZE:parts["txos_pos"]])
    txos_content = bytearray(data[parts["txos_pos"] + CHUNK_HEADER_SIZE:parts["lay2_start"]])
    overlay_items = []
    for code in FREE_TALK_OVERLAY_CODES:
        gxt_str_id = get_or_add_string(strings, overlay_texture_name(code))
        txos_str_id = get_or_add_string(strings, overlay_txos_name(code))
        overlay_item_str_id = get_or_add_string(strings, overlay_item_name(code))

        tex2_content, new_tex2_id = append_tex2_entry(tex2_content, gxt_str_id)
        txos_content, new_txos_id = append_txos_entry(txos_content, txos_str_id, new_tex2_id)
        overlay_items.append((overlay_item_str_id, new_txos_id))

    lay2_region = patch_lay2_region(
        data[parts["lay2_start"]:parts["lay2_end"]],
        strings,
        overlay_items,
    )
    str_content = rebuild_strings(strings)

    arkf_chunk = bytearray(data[parts["arkf_pos"]:parts["tex2_pos"]])
    write_u32(arkf_chunk, 0x14, original_lay2_count)
    write_u32(arkf_chunk, 0x18, read_u32(tex2_content, 0))
    write_u32(arkf_chunk, 0x1C, read_u32(txos_content, 0))

    result = bytearray()
    result += data[:parts["arkf_pos"]]
    result += arkf_chunk
    result += b"ARK TEX2" + struct.pack("<Q", len(tex2_content)) + tex2_content
    result += b"ARK TXOS" + struct.pack("<Q", len(txos_content)) + txos_content
    result += lay2_region
    result += b"GENESTRT" + struct.pack("<Q", len(str_content)) + str_content
    result += data[parts["str_end"]:]

    ark_path.write_bytes(result)
    print(f"Free talk ARK patch finished: {ark_path}")


def encode_preserved_call_with_this_reg(call_va, this_reg, target_func_va):
    code = bytearray()
    code += encode_push(PRESERVE_CALL_MASK)
    code += encode_mov_reg(R0, this_reg)
    code += encode_arm_branch(call_va + len(code), target_func_va, link=True)
    code += encode_pop(PRESERVE_CALL_MASK)
    return code


def encode_overlay_handle_load(code, skip_branches):
    code += encode_ldr(R0, R5, FREE_TALK_ROOT_SLOT_CACHE_OFFSET)
    code += encode_cmp_imm(R0, 0)
    append_skip_branch(code, skip_branches)

    code += encode_ldr(R4, R0, 0x18)
    code += encode_cmp_imm(R4, 0)
    append_skip_branch(code, skip_branches)

    code += encode_ldr(R6, R5, COMMENT_UNUSED_PARENT_HANDLE_OFFSET)
    code += encode_cmp_imm(R6, 0)
    append_skip_branch(code, skip_branches)
    return code


def encode_set_visible_for_handle_reg(func_va, handle_reg, visible, recursive=1):
    code = bytearray()
    code += encode_mov_reg(R0, R4)
    code += encode_mov_reg(R1, handle_reg)
    code += encode_mov_imm(R2, visible)
    code += encode_mov_imm(R3, recursive)
    code += encode_arm_branch(func_va + len(code), FUNC_SET_VISIBLE_VA, link=True)
    return code


def encode_prepare_visible_for_handle_reg(func_va, handle_reg, visible):
    code = bytearray()
    code += encode_mov_reg(R0, R4)
    code += encode_mov_reg(R1, handle_reg)
    code += encode_mov_imm(R2, visible)
    code += encode_arm_branch(func_va + len(code), FUNC_PREPARE_VISIBLE_VA, link=True)
    return code


def encode_resolve_handle_object(base_offset, manager_reg, handle_reg, object_reg, index_reg, generation_reg, temp_reg, skip_branches):
    code = bytearray()
    code += encode_cmp_imm(handle_reg, 0)
    append_skip_branch(code, skip_branches, base_offset=base_offset)

    code += encode_ldr(temp_reg, manager_reg, 0x78)
    code += encode_cmp_imm(temp_reg, 0)
    mode_direct_branch_point = append_branch_placeholder(code)
    append_skip_branch(code, skip_branches, cond=0xB, base_offset=base_offset)  # blt

    code += encode_mov_reg_shift(index_reg, handle_reg, 0, 16)  # index = handle & 0xFFFF
    code += encode_mov_reg_shift(index_reg, index_reg, 1, 16)
    code += encode_mov_reg_shift(generation_reg, handle_reg, 1, 16)
    code += encode_ldr(temp_reg, manager_reg, 0x5C)
    code += encode_ldr_reg_scaled(temp_reg, temp_reg, index_reg, 2)
    code += encode_cmp_reg(temp_reg, generation_reg)
    append_skip_branch(code, skip_branches, cond=0x1, base_offset=base_offset)

    code += encode_ldr(object_reg, manager_reg, 0x4C)
    code += encode_ldr_reg_scaled(object_reg, object_reg, index_reg, 2)
    code += encode_cmp_imm(object_reg, 0)
    append_skip_branch(code, skip_branches, base_offset=base_offset)

    mode_zero_done_branch_point = append_branch_placeholder(code)

    mode_direct_point = len(code)
    code[mode_direct_branch_point:mode_direct_branch_point + 4] = encode_arm_branch(
        base_offset + mode_direct_branch_point,
        base_offset + mode_direct_point,
        cond=0xC,  # bgt
    )
    code += encode_cmp_imm(temp_reg, 1)
    append_skip_branch(code, skip_branches, cond=0xC, base_offset=base_offset)  # bgt
    code += encode_mov_reg(object_reg, handle_reg)
    code += encode_cmp_imm(object_reg, 0)
    append_skip_branch(code, skip_branches, base_offset=base_offset)

    done_point = len(code)
    code[mode_zero_done_branch_point:mode_zero_done_branch_point + 4] = encode_arm_branch(
        base_offset + mode_zero_done_branch_point,
        base_offset + done_point,
    )
    return code


def encode_set_child_object_visible(func_va, child_reg, visible_reg, recursive=1):
    code = bytearray()
    code += encode_mov_reg(R0, child_reg)
    code += encode_mov_reg(R1, visible_reg)
    code += encode_mov_imm(R2, recursive)
    code += encode_arm_branch(func_va + len(code), FUNC_OBJECT_SET_VISIBLE_VA, link=True)
    return code


def encode_show_selected_overlay_func(func_va, child_index_table_va):
    code = bytearray()
    skip_branches = []
    code += encode_push(PRESERVE_ALL_LR_MASK)
    code += encode_mov_reg(R5, R0)
    code += encode_mov_reg(R7, R1)
    code += encode_cmp_imm(R5, 0)
    append_skip_branch(code, skip_branches)

    code = encode_overlay_handle_load(code, skip_branches)

    code += encode_cmp_imm(R7, len(FREE_TALK_KEY_TO_CHILD_INDEX))
    append_skip_branch(code, skip_branches, cond=0x2)  # bhs

    code += encode_load_pc_relative_address(R8, child_index_table_va, func_va + len(code))
    code += encode_ldr_reg_scaled(R9, R8, R7, 2)
    code += encode_cmp_imm(R9, INVALID_CHILD_INDEX)
    append_skip_branch(code, skip_branches)

    code += encode_ldr(R10, R4, 4)
    code += encode_resolve_handle_object(
        len(code),
        manager_reg=R10,
        handle_reg=R6,
        object_reg=R8,
        index_reg=R7,
        generation_reg=R11,
        temp_reg=R12,
        skip_branches=skip_branches,
    )
    code += encode_ldr(R12, R8, 0x5C)
    code += encode_cmp_imm(R12, 4)
    append_skip_branch(code, skip_branches, cond=0x1)

    code += encode_ldr(R10, R8, 0xDC)
    code += encode_cmp_imm(R10, 0)
    append_skip_branch(code, skip_branches)
    code += encode_ldr(R11, R10, 0x30)
    code += encode_cmp_imm(R11, 0)
    append_skip_branch(code, skip_branches)
    code += encode_cmp_reg(R9, R11)
    append_skip_branch(code, skip_branches, cond=0x2)  # bhs
    code += encode_ldr(R10, R8, 0xE0)
    code += encode_cmp_imm(R10, 0)
    append_skip_branch(code, skip_branches)

    code += encode_prepare_visible_for_handle_reg(func_va + len(code), R6, 1)
    code += encode_set_visible_for_handle_reg(func_va + len(code), R6, 1, recursive=0)

    code += encode_mov_imm(R7, 0)
    loop_point = len(code)
    code += encode_cmp_reg(R7, R11)
    loop_done_branch_point = append_branch_placeholder(code)
    code += encode_ldr_reg_scaled(R6, R10, R7, 2)
    code += encode_cmp_imm(R6, 0)
    skip_child_branch_point = append_branch_placeholder(code)
    code += encode_mov_imm(R1, 0)
    code += encode_cmp_reg(R7, R9)
    keep_hidden_branch_point = append_branch_placeholder(code)
    code += encode_mov_imm(R1, 1)
    visible_arg_done = len(code)
    code[keep_hidden_branch_point:keep_hidden_branch_point + 4] = encode_arm_branch(
        func_va + keep_hidden_branch_point,
        func_va + visible_arg_done,
        cond=0x1,
    )
    code += encode_set_child_object_visible(func_va + len(code), R6, R1, recursive=1)
    next_child_point = len(code)
    code[skip_child_branch_point:skip_child_branch_point + 4] = encode_arm_branch(
        func_va + skip_child_branch_point,
        func_va + next_child_point,
        cond=0x0,
    )
    code += encode_add_imm(R7, R7, 1)
    code += encode_arm_branch(func_va + len(code), func_va + loop_point)
    loop_done_point = len(code)
    code[loop_done_branch_point:loop_done_branch_point + 4] = encode_arm_branch(
        func_va + loop_done_branch_point,
        func_va + loop_done_point,
        cond=0x2,
    )

    patch_skip_branches(code, func_va, skip_branches)
    code += encode_pop(PRESERVE_ALL_PC_MASK)
    return code


def encode_hide_overlay_func(func_va):
    code = bytearray()
    skip_branches = []
    code += encode_push(PRESERVE_ALL_LR_MASK)
    code += encode_mov_reg(R5, R0)
    code += encode_cmp_imm(R5, 0)
    append_skip_branch(code, skip_branches)

    code = encode_overlay_handle_load(code, skip_branches)
    code += encode_set_visible_for_handle_reg(func_va + len(code), R6, 0, recursive=1)

    patch_skip_branches(code, func_va, skip_branches)
    code += encode_pop(PRESERVE_ALL_PC_MASK)
    return code


def encode_store_then_hide_hook(hook_va, store_encoder, this_reg, hide_func_va, return_va):
    code = bytearray()
    code += store_encoder()
    code += encode_preserved_call_with_this_reg(hook_va + len(code), this_reg, hide_func_va)
    code += encode_arm_branch(hook_va + len(code), return_va)
    return code


def encode_show_on_play_hook(hook_va, show_func_va, return_va):
    code = bytearray()
    code += encode_push(PRESERVE_CALL_MASK)
    code += encode_mov_reg(R0, R10)
    # r6 is the selected free-talk key computed by the original play path.
    code += encode_mov_reg(R1, R6)
    code += encode_arm_branch(hook_va + len(code), show_func_va, link=True)
    code += encode_pop(PRESERVE_CALL_MASK)
    code += encode_arm_branch(hook_va + len(code), return_va)
    return code


def encode_update_guard_hook(hook_va, hide_func_va, return_va):
    code = bytearray()
    code += encode_push(PRESERVE_ALL_LR_MASK)
    code += encode_ldrb(R0, R10, FREE_TALK_PLAYING_FLAG_OFFSET)
    code += encode_cmp_imm(R0, 0)
    play_flag_zero_branch_point = append_branch_placeholder(code)

    code += encode_ldr(R0, R10, FREE_TALK_STATE_OFFSET)
    code += encode_cmp_imm(R0, 2)
    skip_hide_branch_point = append_branch_placeholder(code)

    call_hide_point = len(code)
    code += encode_mov_reg(R0, R10)
    code += encode_arm_branch(hook_va + len(code), hide_func_va, link=True)
    skip_hide_point = len(code)

    code += encode_pop(PRESERVE_ALL_LR_MASK)
    code += encode_ldr(R1, SP, 4)
    code += encode_arm_branch(hook_va + len(code), return_va)

    code[play_flag_zero_branch_point:play_flag_zero_branch_point + 4] = encode_arm_branch(
        hook_va + play_flag_zero_branch_point,
        hook_va + call_hide_point,
        cond=0x0,
    )
    code[skip_hide_branch_point:skip_hide_branch_point + 4] = encode_arm_branch(
        hook_va + skip_hide_branch_point,
        hook_va + skip_hide_point,
        cond=0x1,
    )
    return code


def encode_init_hide_hook(hook_va, hide_func_va, return_va):
    code = bytearray()
    code += encode_push(PRESERVE_CALL_MASK)
    code += encode_ldr(R0, SP, 0x9C)
    code += encode_cmp_imm(R0, 0)
    skip_store_branch_point = append_branch_placeholder(code)
    # r8 holds the relocated gallery root slot in this init path. Cache it on
    # the free-talk object itself; the code cave is RX on real Vita hardware.
    code += encode_str(R8, R0, FREE_TALK_ROOT_SLOT_CACHE_OFFSET)
    store_done_point = len(code)
    code[skip_store_branch_point:skip_store_branch_point + 4] = encode_arm_branch(
        hook_va + skip_store_branch_point,
        hook_va + store_done_point,
        cond=0x0,
    )
    code += encode_arm_branch(hook_va + len(code), hide_func_va, link=True)
    code += encode_pop(PRESERVE_CALL_MASK)
    code += encode_add_imm(SP, SP, 0x9C)
    code += encode_arm_branch(hook_va + len(code), return_va)
    return code


def patch_original_branch(eboot_data, hook_site, target_va):
    hook_point, hook_va, _ = hook_site
    eboot_data[hook_point:hook_point + 4] = encode_arm_branch(hook_va, target_va)


def write_child_index_table(eboot_data):
    table_point = CODE_CAVE_POINT + CHILD_INDEX_TABLE_CAVE_OFFSET
    for key, child_index in enumerate(FREE_TALK_KEY_TO_CHILD_INDEX):
        write_u32(eboot_data, table_point + key * 4, child_index)
    return point_to_va(table_point)


def patch_eboot(eboot_path):
    eboot_path = Path(eboot_path)
    if not eboot_path.exists():
        raise FileNotFoundError(f"Patched EBOOT not found: {eboot_path}")

    eboot_data = bytearray(eboot_path.read_bytes())
    eboot_data[CODE_CAVE_POINT:CODE_CAVE_POINT + CODE_CAVE_SIZE] = b"\x00" * CODE_CAVE_SIZE

    child_index_table_va = write_child_index_table(eboot_data)

    show_func_point = CODE_CAVE_POINT + SHOW_FUNC_CAVE_OFFSET
    hide_func_point = CODE_CAVE_POINT + HIDE_FUNC_CAVE_OFFSET
    show_func_va = point_to_va(show_func_point)
    hide_func_va = point_to_va(hide_func_point)

    cursor = CODE_CAVE_POINT
    hook_targets = []

    def write_hook(hook_site, hook_builder):
        nonlocal cursor
        hook_va = point_to_va(cursor)
        code = hook_builder(hook_va)
        eboot_data[cursor:cursor + len(code)] = code
        cursor += align(len(code), 4)
        hook_targets.append((hook_site, hook_va))

    def write_store_hide_hook(hook_site, store_encoder, this_reg):
        write_hook(
            hook_site,
            lambda hook_va: encode_store_then_hide_hook(
                hook_va,
                store_encoder,
                this_reg,
                hide_func_va,
                hook_site[2],
            ),
        )

    write_store_hide_hook(HOOK_HIDE_ON_AUDIO_END, lambda: encode_strb(R0, R10, FREE_TALK_PLAYING_FLAG_OFFSET), R10)
    write_store_hide_hook(HOOK_HIDE_ON_EXIT, lambda: encode_str(R0, R10, FREE_TALK_STATE_OFFSET), R10)
    write_hook(HOOK_SHOW_ON_PLAY, lambda hook_va: encode_show_on_play_hook(hook_va, show_func_va, HOOK_SHOW_ON_PLAY[2]))
    write_store_hide_hook(HOOK_HIDE_ON_STOP_A, lambda: encode_strb(R0, R4, FREE_TALK_PLAYING_FLAG_OFFSET), R4)
    write_store_hide_hook(HOOK_HIDE_ON_STOP_B, lambda: encode_strb(R0, R4, FREE_TALK_PLAYING_FLAG_OFFSET), R4)
    write_hook(HOOK_HIDE_ON_UPDATE, lambda hook_va: encode_update_guard_hook(hook_va, hide_func_va, HOOK_HIDE_ON_UPDATE[2]))
    write_hook(HOOK_HIDE_ON_INIT, lambda hook_va: encode_init_hide_hook(hook_va, hide_func_va, HOOK_HIDE_ON_INIT[2]))
    if cursor > hide_func_point:
        raise ValueError("Free-talk inline hooks overlap hide function")

    show_func = encode_show_selected_overlay_func(show_func_va, child_index_table_va)
    hide_func = encode_hide_overlay_func(hide_func_va)
    if show_func_point + len(show_func) > CODE_CAVE_POINT + CHILD_INDEX_TABLE_CAVE_OFFSET:
        raise ValueError("Free-talk show function overlaps child index table")
    if hide_func_point + len(hide_func) > show_func_point:
        raise ValueError("Free-talk hide function overlaps show function")
    eboot_data[show_func_point:show_func_point + len(show_func)] = show_func
    eboot_data[hide_func_point:hide_func_point + len(hide_func)] = hide_func

    for hook_site, target_va in hook_targets:
        patch_original_branch(eboot_data, hook_site, target_va)

    eboot_path.write_bytes(eboot_data)
    print(f"Free talk EBOOT patch finished: {eboot_path}")


def patch_free_talk(ark_path, eboot_path):
    patch_ark(ark_path)
    patch_eboot(eboot_path)


def main(argv=None):
    argv = sys.argv if argv is None else argv
    if len(argv) != 3:
        raise SystemExit(f"Usage: {Path(argv[0]).name} <gallery.ark> <eboot.elf>")
    patch_free_talk(argv[1], argv[2])


if __name__ == "__main__":
    main()
