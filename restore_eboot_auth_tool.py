import sys


def eboot_bin_auth(eboot_file, key):
    fp_s = open(eboot_file, 'rb')
    data = bytearray(fp_s.read())
    fp_s.close()
    data[0x80:0x88] = key

    fp_s = open(eboot_file, 'wb')
    fp_s.write(data)
    fp_s.close()


if __name__ == "__main__":
    eboot_file_path = sys.argv[1]

    print(f"Start restore {eboot_file_path} auth.")

    eboot_bin_auth(
        eboot_file=eboot_file_path,
        key=bytearray([0x8D, 0x01, 0xCE, 0x1C, 0x10, 0x00, 0x00, 0x21])
    )

    print("Restore finished.")
