import json
import struct

txos_per_data = bytearray([
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x80, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x3B, 0x01, 0x00, 0x00,
    0x2B, 0x00, 0x00, 0x00, 0x26, 0x00, 0x00, 0x00,
    0x28, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00,
    0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x78, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
])

with open("ark_data/texture_data_test.json", mode="r", encoding="utf-8") as texture_data_file:
    texture_data = json.load(texture_data_file)

global_str_idx = 931
extend_str_list = []


def pad_to_16_byte(ba):
    remainder = len(ba) % 16
    if remainder == 0:
        return

    padding_len = 16 - remainder
    ba.extend([0] * padding_len)


def extend_txos(txos_data: bytearray):
    global global_str_idx
    for idx, texture in enumerate(texture_data):
        extend_str_list.append(texture["str_area"])
        # extend_str_list.append(f"CHAR_{idx:04d}")
        txos_per_data[0x14:0x18] = struct.pack("<I", texture["point_x"])
        txos_per_data[0x18:0x1C] = struct.pack("<I", texture["point_y"])
        txos_per_data[0x34:0x38] = struct.pack("<I", global_str_idx)

        print(
            struct.unpack(
                "<I", txos_per_data[0x34:0x38]
            )[0]
        )

        global_str_idx += 1

        txos_data.extend(txos_per_data)

    pad_to_16_byte(txos_data)

    # Update header
    txos_data[0x08:0x0C] = struct.pack("<I", len(txos_data) - 0x10)
    txos_data[0x10:0x14] = struct.pack("<I", 216 + len(texture_data))


def update_lay2(lay2_data: bytearray):
    global global_str_idx
    start_offset = 0x36C0

    idx = 0
    for texture in texture_data:
        points = texture["lay2_point"].split(",")
        for point in points:
            lay2_point = int(point, 16)
            # lay2_data[lay2_point - start_offset:(lay2_point + 4) - start_offset] = struct.pack("<I", global_str_idx)
            lay2_data[lay2_point - start_offset:(lay2_point + 4) - start_offset] = struct.pack("<I", 243)
            # extend_str_list.append(f"OBJ_ANIM_{idx:04d}")

            txos_id_offset = lay2_point - start_offset + 0x14
            # lay2_data[txos_id_offset:txos_id_offset + 4] = struct.pack("<I", texture["texture_id"])
            # lay2_data[txos_id_offset:txos_id_offset + 4] = struct.pack("<I", 143)
            # global_str_idx += 1
            idx += 1


def extend_str(str_header_data: bytearray, str_content_data: bytearray):
    global global_str_idx
    str_header_data[0x10:0x14] = struct.pack("<I", global_str_idx)

    for idx, ex_str in enumerate(extend_str_list):
        if idx != 0:
            str_header_data.extend(struct.pack("<I", len(str_content_data)))
        str_content_data.extend(ex_str.encode("utf-8"))
        str_content_data.extend(b'\x00')

    # End mark
    str_header_data.extend(struct.pack("<I", len(str_content_data)))

    pad_to_16_byte(str_header_data)
    pad_to_16_byte(str_content_data)

    str_header_data[0x18:0x1C] = struct.pack("<I", len(str_header_data) - 0x10)
    str_area_size = len(str_header_data) + len(str_content_data) - 0x10
    str_header_data[0x08:0x0C] = struct.pack("<I", str_area_size)
    str_header_data[0x1C:0x20] = struct.pack("<I", str_area_size)


def process():
    with open("ark_data/origin/gallery.ark", 'rb') as f:
        ark_data = f.read()

        pre_data = bytearray(ark_data[0x00:0xA0])

        pre_data[0x2C:0x30] = struct.pack("<I", 216 + len(texture_data))

        txos_data = bytearray(ark_data[0xA0:0x36B8])
        pad_to_16_byte(txos_data)
        # extend_txos(txos_data)

        lay2_data = bytearray(ark_data[0x36C0:0x1E100])
        update_lay2(lay2_data)

        str_header_data = bytearray(ark_data[0x1E100:0x1EFB0])
        str_content_data = bytearray(ark_data[0x1EFB0:0x22816])
        # extend_str(str_header_data, str_content_data)
        pad_to_16_byte(str_header_data)
        pad_to_16_byte(str_content_data)

        suffix_data = bytearray(ark_data[0x22820:])

        with open("ark_data/new_gallery.ark", mode="wb") as new_ark_f:
            new_ark_f.write(pre_data)
            new_ark_f.write(txos_data)
            new_ark_f.write(lay2_data)
            new_ark_f.write(str_header_data)
            new_ark_f.write(str_content_data)
            new_ark_f.write(suffix_data)


if __name__ == "__main__":
    process()
