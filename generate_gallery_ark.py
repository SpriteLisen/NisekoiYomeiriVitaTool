import csv
import struct
from pathlib import Path


def patch_eboot():
    print("Start patching EBOOT ...")
    output_dir = "eboot/modified"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    eboot_file = open("eboot/origin/eboot.elf", mode='rb')
    eboot_data = bytearray(eboot_file.read())
    eboot_file.close()

    # Load & modify char bytes
    with open("eboot/code_config.csv", mode='r', encoding="utf-8") as config_f:
        point_map = {}
        config_reader = csv.DictReader(config_f)
        for row in config_reader:
            origin_char = row["char"]
            new_char = row["new_char"]

            point_map[row["ch"]] = row["code_point"]

            origin_len = len(origin_char.encode("ascii"))
            new_byte = new_char.encode("ascii")
            final_byte = new_byte + ((origin_len - len(new_byte)) * b"\x00")

            point = int(row["data_point"], 16)
            eboot_data[point:point + origin_len] = final_byte

        # Update ptr table
        with open("eboot/ptr_config.csv", mode='r', encoding="utf-8") as ptr_f:
            ptr_reader = csv.DictReader(ptr_f)
            for row in ptr_reader:
                update_point = int(row["point"], 16)
                point_value = int(point_map[row["new_char"][1:2]], 16)
                eboot_data[update_point:update_point + 4] = struct.pack("<I", point_value)

        # Write new elf
        with open(f"{output_dir}/eboot.elf", mode="wb") as out_eboot_f:
            out_eboot_f.write(eboot_data)

        print("EBOOT patching finished.")


def patch_ark():
    print("Start patching ark file ...")
    ark_file = open("ark_data/origin/gallery.ark", mode='rb')
    ark_data = bytearray(ark_file.read())
    ark_file.close()

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
            ark_data[txos_point + 0x1C:txos_point + 0x1C + 0x04] = struct.pack("<I", x)
            ark_data[txos_point + 0x20:txos_point + 0x20 + 0x04] = struct.pack("<I", y)

            # Override lay2 data
            txos_id = int(row["txos_id"])
            lay2_ptrs = row["lay2_ptrs"].split(",")
            for lay2_ptr in lay2_ptrs:
                lay2_ptr = int(lay2_ptr, 16)
                ark_data[lay2_ptr:lay2_ptr + 0x04] = struct.pack("<I", txos_id)

        # Write new elf
        with open(f"ark_data/new_gallery.ark", mode="wb") as out_ark_f:
            out_ark_f.write(ark_data)

        print("Ark file patching finished.")


if __name__ == "__main__":
    patch_eboot()
    patch_ark()
