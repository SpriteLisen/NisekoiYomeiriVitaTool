import os
import sys
import argparse
import subprocess
from pathlib import Path

GAME_ID = "PCSG00397"
GAME_FILES_DIR = "pack"
all_apk_file = "all.apk"
fs_apk_file = "fs.apk"
idx_file = "pack.idx"

base_ci_dir = "CI"
original_dir = os.path.join(base_ci_dir, "Original")
extract_dir = os.path.join(base_ci_dir, "Extract")
product_dir = os.path.join(base_ci_dir, "Product")

all_extract_dir = "extract_all"
fs_extract_dir = "extract_fs"

Path(original_dir).mkdir(parents=True, exist_ok=True)
Path(extract_dir).mkdir(parents=True, exist_ok=True)
Path(
    os.path.join(
        product_dir, GAME_ID, GAME_FILES_DIR
    )
).mkdir(parents=True, exist_ok=True)
Path(product_dir).mkdir(parents=True, exist_ok=True)

output_eboot_file = os.path.join(product_dir, GAME_ID, "eboot.bin")

extract_commands = [
    (
        f"Extract {all_apk_file}...",
        [
            sys.executable, "apk_extractor.py", "unpack",
            "-i", os.path.join(original_dir, all_apk_file),
            "-o", os.path.join(extract_dir, all_extract_dir)
        ]
    ),
    (
        f"Extract {fs_extract_dir}...",
        [
            sys.executable, "apk_extractor.py", "unpack",
            "-i", os.path.join(original_dir, fs_apk_file),
            "-o", os.path.join(extract_dir, fs_extract_dir)
        ]
    ),
]

repack_commands = [
    (
        f"Rebuild fnt ...",
        [
            sys.executable, "make_abf.py", os.path.join(extract_dir, all_extract_dir, "font", "font_j24x24")
        ]
    ),
    (
        f"Rebuild image resources ...",
        [
            sys.executable, "repack_png_resources.py", os.path.join(extract_dir, all_extract_dir)
        ]
    ),
    (
        f"Rebuild script files ...",
        [
            sys.executable, "asb_tool.py", "repack",
            os.path.join("scripts", "origin"),
            os.path.join("scripts", "extract"),
            os.path.join(extract_dir, fs_extract_dir, "__ARCHIVE__", "eventscript", "scripts")
        ]
    ),
    (
        f"Rebuild gop file ...",
        [
            sys.executable, "gop_tool.py", "repack", os.path.join(extract_dir, all_extract_dir, "gop")
        ]
    ),
    (
        f"Rebuild all.apk file ...",
        [
            sys.executable, "apk_extractor.py", "pack",
            "-i", os.path.join(original_dir, all_apk_file), os.path.join(extract_dir, all_extract_dir),
            "-o", os.path.join(product_dir, GAME_ID, GAME_FILES_DIR, all_apk_file)
        ]
    ),
    (
        f"Rebuild fs.apk file ...",
        [
            sys.executable, "apk_extractor.py", "pack",
            "-i", os.path.join(original_dir, fs_apk_file), os.path.join(extract_dir, fs_extract_dir),
            "-o", os.path.join(product_dir, GAME_ID, GAME_FILES_DIR, fs_apk_file)
        ]
    ),
    (
        f"Rebuild idx file ...",
        [
            sys.executable, "rebuild_idx.py",
            "-i", os.path.join(product_dir, GAME_ID, GAME_FILES_DIR, all_apk_file),
            os.path.join(product_dir, GAME_ID, GAME_FILES_DIR, fs_apk_file),
            "-o", os.path.join(product_dir, GAME_ID, GAME_FILES_DIR, "pack.idx"),
            "-d", "pack"
        ]
    ),
    (
        f"Rebuild eboot ...",
        [
            "tools/vitasdk/vita-make-fself.exe", "-c", "eboot/modified/eboot.elf", output_eboot_file
        ]
    ),
]


def main():
    parser = argparse.ArgumentParser(
        description='Project CI tool, can auto extract files to resources, or repack all resource to rePatch files')
    subparsers = parser.add_subparsers(dest='command', help='commands', required=True)

    # extract
    extract_parser = subparsers.add_parser('extract', help='extract *.cpk to directory')

    # repack
    replace_parser = subparsers.add_parser('repack', help='repack the target dir all file to a cpk pack')

    args = parser.parse_args()

    if args.command == 'extract':
        for k, v in extract_commands:
            print(k)

            try:
                result = subprocess.run(
                    v,
                    check=True,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                )

                if result.returncode != 0:
                    print("Execute command error =>" + result.returncode)
                    return -1
            except Exception as e:
                print(f"Error: {e}")
                return -1
    elif args.command == 'repack':
        for k, v in repack_commands:
            print(k)

            try:
                result = subprocess.run(
                    v,
                    check=True,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                )

                if result.returncode != 0:
                    print("Execute command error =>" + result.returncode)
                    return -1
            except Exception as e:
                print(f"Error: {e}")
                return -1

    return -1


if __name__ == "__main__":
    main()
