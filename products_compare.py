import os
from m_logger import *
from pathlib import Path

top_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if top_dir not in sys.path:
    sys.path.insert(0, top_dir)


def binary_equal(file1, file2):
    """逐字节比较两个文件是否完全一致"""
    with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
        offset = 0
        while True:
            b1 = f1.read(4096)
            b2 = f2.read(4096)

            min_len = min(len(b1), len(b2))
            for i in range(min_len):
                if b1[i] != b2[i]:
                    log_error(f"Difference at offset 0x{offset + i:08X} ({offset + i}):")
                    log_error(f"  {file1}: 0x{b1[i]:02X}")
                    log_error(f"  {file2}: 0x{b2[i]:02X}")
                    return False

            if len(b1) != len(b2):
                log_error(f"Files differ in length at offset 0x{offset + min_len:X} ({offset + min_len})")
                log_error(f"  {file1} length: {offset + len(b1)}")
                log_error(f"  {file2} length: {offset + len(b2)}")
                return False

            if not b1:  # both EOF
                return True

            offset += len(b1)


def compare_directories(dir1, dir2):
    dir1 = Path(dir1)
    dir2 = Path(dir2)

    files1 = {f.name: f for f in dir1.iterdir() if f.is_file()}
    files2 = {f.name: f for f in dir2.iterdir() if f.is_file()}

    common_files = files1.keys() & files2.keys()
    only_in_dir1 = files1.keys() - files2.keys()
    only_in_dir2 = files2.keys() - files1.keys()

    # 输出文件数量统计
    log_info("== File Statistics ==")
    log_info(f"Directory 1 ({dir1}): {len(files1)} files")
    log_info(f"Directory 2 ({dir2}): {len(files2)} files")
    log_info(f"Common files: {len(common_files)}")
    log_info(f"Files only in directory 1: {len(only_in_dir1)}")
    log_info(f"Files only in directory 2: {len(only_in_dir2)}")

    # 输出只在其中一个目录中存在的文件
    if only_in_dir1:
        log_warn("\n== Files only in directory 1 ==")
        for filename in sorted(only_in_dir1):
            log_warn(f"  {filename}")

    if only_in_dir2:
        log_warn("\n== Files only in directory 2 ==")
        for filename in sorted(only_in_dir2):
            log_warn(f"  {filename}")

    # 比较共同文件
    if common_files:
        log_info("\n== Comparing common files ==")
        compare_success = True

        for filename in sorted(common_files):
            f1 = files1[filename]
            f2 = files2[filename]
            if binary_equal(f1, f2):
                log_same(filename)
            else:
                log_diff(filename)
                compare_success = False

        if compare_success:
            log_succeed(f"Compared {len(common_files)} common files successfully.")
        else:
            log_error(f"Some files do not match in the {len(common_files)} common files.")
            return False
    else:
        log_warn("No common files to compare.")
        return False

    if only_in_dir1 or only_in_dir2:
        log_warn("Comparison completed with missing files in one directory.")
        return False

    return True


if __name__ == '__main__':
    if len(sys.argv) != 3:
        log_error("Usage: python products_compare_test.py <dir1> <dir2>")
        sys.exit(1)
    else:
        success = compare_directories(sys.argv[1], sys.argv[2])
        sys.exit(0 if success else 1)