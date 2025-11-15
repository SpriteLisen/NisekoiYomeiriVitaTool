import zlib
import copy
import struct
import os.path
import hashlib
import argparse
from typing import Final


def get_table_padding_count(current: int) -> int:
    if current % 16 == 0:
        return 0

    return 16 - (current % 16)


def get_table_end_padding_count(current: int) -> int:
    if current % 2048 == 0:
        return 0

    n = int(current / 2048)

    while True:
        block_size = (n * 2048)
        if current <= block_size:
            return block_size - current
        n += 1


# padding for single root file
def get_root_file_padding_cnt(size: int) -> int:
    if size % 512 == 0:
        return 0

    n = int(size / 512)

    while True:
        block_size = (n * 512)
        if size <= block_size:
            return block_size - size
        n += 1


# padding for all root files
def get_root_files_padding_count(size: int) -> int:
    if size % 2048 == 0:
        return 0

    n = int(size / 2048)

    while True:
        block_size = (n * 2048)
        if size <= block_size:
            return block_size - size
        n += 1


def get_archive_file_padding_cnt(size: int) -> int:
    if size % 16 == 0:
        return 0

    n = int(size / 16)

    while True:
        block_size = (n * 16)
        if size <= block_size:
            return block_size - size
        n += 1


def get_archive_padding_count(pad_type: int, size: int) -> int:
    if pad_type == 1:
        unit = 2048
    elif pad_type == 2:
        unit = 512
    else:
        unit = None

    if size % unit == 0:
        return 0

    n = int(size / unit)

    while True:
        block_size = (n * unit)
        if size <= block_size:
            return block_size - size
        n += 1


def get_changed_file_path(directory):
    result = []

    for dir_path, _, filenames in os.walk(directory):
        for name in filenames:
            full = str(os.path.join(dir_path, name))
            rel = os.path.relpath(full, directory).replace("\\", "/")
            result.append(rel)

    return result


def extract_directory(apk, entry_index: int, entry_count: int, path: str):
    for i in range(entry_index, entry_index + entry_count):
        toc_segment = apk.PACKTOC.TOC_SEGMENT_LIST[i]
        if int(toc_segment.IDENTIFIER) == 1:
            extract_directory(apk, int(toc_segment.ENTRY_INDEX), int(toc_segment.ENTRY_COUNT),
                              os.path.join(path, get_name_from_name_idx(apk, int(toc_segment.NAME_IDX))))
        else:
            file_path = os.path.join(path, get_name_from_name_idx(apk, int(toc_segment.NAME_IDX))).replace("\\", "/")
            TREE["ROOT"][file_path] = toc_segment


TREE: dict = dict()


def make_tree(apk) -> dict:
    TREE["ROOT"] = dict()
    TREE["ARCHIVE"] = dict()

    if len(apk.PACKTOC.TOC_SEGMENT_LIST) > 0:
        toc_segment = apk.PACKTOC.TOC_SEGMENT_LIST[0]
        if int(toc_segment.IDENTIFIER) == 1:  # If folders are present, they are expected to start with an empty string directory.
            extract_directory(apk, int(toc_segment.ENTRY_INDEX), int(toc_segment.ENTRY_COUNT), "")
        else:  # files for root directory, Only files are expected, without any folders.
            for toc_segment in apk.PACKTOC.TOC_SEGMENT_LIST:
                file_path = get_name_from_name_idx(apk, int(toc_segment.NAME_IDX)).replace("\\", "/")
                TREE["ROOT"][file_path] = toc_segment

    if int(apk.PACKFSLS.ARCHIVE_SEG_COUNT) > 0:
        ofs_name_map = dict()
        for archive_segment in apk.PACKFSLS.ARCHIVE_SEGMENT_LIST:
            archive_name = get_name_from_name_idx(apk, int(archive_segment.NAME_IDX))
            TREE["ARCHIVE"].setdefault(archive_name, {})
            ofs_name_map[int(archive_segment.ARCHIVE_OFFSET)] = archive_name

        for archive in apk.ARCHIVES.ARCHIVE_LIST:
            archive_name = ofs_name_map[archive.ARCHIVE_ofs]
            for file_segment in archive.PACKFSHD.FILE_SEGMENT_LIST:
                file_path = get_name_from_name_idx(archive, int(file_segment.NAME_IDX))
                TREE["ARCHIVE"][archive_name][file_path] = file_segment

    return TREE


class chararray:
    def __init__(self, size: int, value=None):
        if size < 1:
            raise CharArrayException(f"Size must be a positive integer.  size={size}")

        self.__size = size
        self.__value: list[str] = ["\0" for _ in range(size)]

        if value is not None:
            self.from_value(value)

    def __str__(self):
        return "".join(self.__value)

    def from_str(self, value: str):
        if self.__size < len(value):
            raise CharArrayException(f"The value is larger than the size. size={self.__size}  len(value)={len(value)}")
        if not all(ord(c) < 128 for c in value):
            raise CharArrayException(f"chararray supports only ASCII characters.")

        self.__value = list(value) + ["\0" for _ in range(self.__size - len(value))]

    def from_bytearray(self, value: bytearray):
        if self.__size < len(value):
            raise CharArrayException(f"The value is larger than the size. size={self.__size}  len(value)={len(value)}")
        if not all(c < 128 for c in value):
            raise CharArrayException(f"chararray supports only ASCII characters.")

        self.__value = list(value.decode("ascii")) + ["\0" for _ in range(self.__size - len(value))]

    def from_value(self, value):
        if isinstance(value, bytearray):
            self.from_bytearray(value)
        elif isinstance(value, str):
            self.from_str(value)
        else:
            raise CharArrayException(f"Value must be bytearray or str.  this={type(value)}")

    def to_str(self) -> str:
        return self.__str__()

    def to_bytearray(self) -> bytearray:
        return bytearray([ord(c) for c in self.__value])


class CharArrayException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class uint32:
    MIN_VALUE: Final[int] = 0
    MAX_VALUE: Final[int] = 4_294_967_295

    def __init__(self, value=None, endian: str = "<"):
        self.__value: int = 0

        if value is not None:
            self.from_value(value, endian)

    def __int__(self):
        return self.__value

    def from_int(self, value: int):
        if value < self.MIN_VALUE or value > self.MAX_VALUE:
            raise Uint32Exception(f"Value must be between {self.MIN_VALUE} and {self.MAX_VALUE}.")

        self.__value = value

    def from_bytearray(self, value: bytearray, endian: str = "<"):
        if len(value) != 4:
            raise Uint32Exception(f"Size must be a 4 bytes.  size={len(value)}")

        self.__value = struct.unpack(f"{endian}I", value)[0]

    def from_value(self, value, endian: str = "<"):
        if isinstance(value, bytearray):
            self.from_bytearray(value, endian)
        elif isinstance(value, int):
            self.from_int(value)
        else:
            raise Uint32Exception(f"Value must be bytearray or int.  this={type(value)}")

    def to_int(self) -> int:
        return self.__int__()

    def to_bytearray(self, endian: str = "<") -> bytearray:
        return bytearray(struct.pack(f"{endian}I", self.__value))


class Uint32Exception(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class uint64:
    MIN_VALUE: Final[int] = 0
    MAX_VALUE: Final[int] = 18_446_744_073_709_551_615

    def __init__(self, value, endian: str = "<"):
        self.__value: int = 0

        if value is not None:
            self.from_value(value, endian)

    def __int__(self):
        return self.__value

    def from_int(self, value: int):
        if value < self.MIN_VALUE or value > self.MAX_VALUE:
            raise Uint64Exception(f"Value must be between {self.MIN_VALUE} and {self.MAX_VALUE}.")

        self.__value = value

    def from_bytearray(self, value: bytearray, endian: str = "<"):
        if len(value) != 8:
            raise Uint64Exception(f"Size must be a 8 bytes.  size={len(value)}")

        self.__value = struct.unpack(f"{endian}Q", value)[0]

    def from_value(self, value, endian: str = "<"):
        if isinstance(value, bytearray):
            self.from_bytearray(value, endian)
        elif isinstance(value, int):
            self.from_int(value)
        else:
            raise Uint64Exception(f"Value must be bytearray or int.  this={type(value)}")

    def to_int(self) -> int:
        return self.__int__()

    def to_bytearray(self, endian: str = "<") -> bytearray:
        return bytearray(struct.pack(f"{endian}Q", self.__value))


class Uint64Exception(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class BinaryReader:
    def __init__(self, data: bytearray):
        if type(data) is not bytearray:
            raise BinaryManagerException(f"BinaryReader only accepts type bytearray")

        self.__RAW: bytearray = copy.deepcopy(data)
        self.__OFFSET: int = -1

    def __getitem__(self, index: int):
        return self.__RAW[index]

    def clear(self):
        self.__RAW.clear()
        self.__OFFSET = -1

    def skip(self, n):
        self.__OFFSET += n

    def size(self) -> int:
        return len(self.__RAW)

    def seek(self, offset: int):
        self.__OFFSET = offset

    def tell(self) -> int:
        return self.__OFFSET

    def EOF(self) -> bool:
        return self.__OFFSET + 1 >= self.size()

    def get_raw(self) -> bytearray:
        return copy.deepcopy(self.__RAW)

    def get_byte(self) -> int:
        if self.__OFFSET < self.size():
            result = self.__RAW[self.__OFFSET]
            self.__OFFSET += 1
            return result
        else:
            raise BinaryManagerException(f"get_byte() OutOfRange.")

    def get_bytes(self, size: int) -> bytearray:
        if self.__OFFSET + size <= self.size():
            result = self.__RAW[self.__OFFSET:self.__OFFSET + size]
            self.__OFFSET += size
            return result
        else:
            raise BinaryManagerException(f"get_bytes() OutOfRange.")

    def read_ascii_string(self) -> str:
        tmp: bytearray = bytearray()

        while self.tell() < self.size():
            b: int = self.__RAW[self.tell()]
            if b == 0:
                tmp.append(0)
                self.__OFFSET += 1
                break
            tmp.append(b)
            self.__OFFSET += 1

        return tmp.decode("ascii")


class BinaryManagerException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class APK:

    def __init__(self):
        self.ENDIANNESS = self._ENDIANNESS()
        self.PACKHEDR = self._PACKHEDR()
        self.PACKTOC = self._PACKTOC()
        self.PACKFSLS = self._PACKFSLS()
        self.GENESTRT = self._GENESTRT()
        self.GENEEOF = self._GENEEOF()
        self.ROOT_FILES = self._ROOT_FILES()
        self.ARCHIVES = self._ARCHIVES()

    def to_bytearray(self) -> bytearray:
        return (
                self.ENDIANNESS.to_bytearray() +
                self.PACKHEDR.to_bytearray() +
                self.PACKTOC.to_bytearray() +
                self.PACKFSLS.to_bytearray() +
                self.GENESTRT.to_bytearray() +
                self.GENEEOF.to_bytearray() +
                self.ROOT_FILES.to_bytearray() +
                self.ARCHIVES.to_bytearray()
        )

    class _ENDIANNESS:
        def __init__(self):
            self.SIGNATURE: chararray = chararray(size=8)
            self.TABLE_SIZE: uint64 = uint64(0)

            self.SIGNATURE_ofs: int = 0
            self.TABLE_SIZE_ofs: int = 0

        def from_bytearray(self, ofs: int, src: bytearray):
            if len(src) != 16:
                raise TableException(self, f"The table size must be 16.  this={len(src)}")

            self.SIGNATURE.from_bytearray(src[:8])
            self.SIGNATURE_ofs = ofs
            if str(self.SIGNATURE) != "ENDILTLE":
                raise TableException(self, f"SIGNATURE must be 'ENDILTLE'.  this={str(self.SIGNATURE)}")

            self.TABLE_SIZE.from_bytearray(src[8:])
            self.TABLE_SIZE_ofs = ofs + 8
            if int(self.TABLE_SIZE) != 0:
                raise TableException(self, f"TABLE_SIZE must be 0.  this={int(self.TABLE_SIZE)}")

        def to_bytearray(self) -> bytearray:
            return self.SIGNATURE.to_bytearray() + self.TABLE_SIZE.to_bytearray()

    class _PACKHEDR:
        def __init__(self):
            self.SIGNATURE: chararray = chararray(size=8)
            self.TABLE_SIZE: uint64 = uint64(0)
            self.unknown_1: bytearray = bytearray()
            self.NAME_IDX: uint32 = uint32()
            self.FILE_LIST_OFFSET: uint32 = uint32(0)
            self.ARCHIVE_PADDING_TYPE: uint32 = uint32(0)
            self.HASH: bytearray = bytearray()

            self.SIGNATURE_ofs: int = 0
            self.TABLE_SIZE_ofs: int = 0
            self.unknown_1_ofs: int = 0
            self.NAME_IDX_ofs: int = 0
            self.FILE_LIST_OFFSET_ofs: int = 0
            self.ARCHIVE_PADDING_TYPE_ofs: int = 0
            self.HASH_ofs: int = 0

        def from_bytearray(self, ofs: int, src: bytearray):
            self.SIGNATURE.from_bytearray(src[:8])
            self.SIGNATURE_ofs = ofs
            if str(self.SIGNATURE) != "PACKHEDR":
                raise TableException(self, f"SIGNATURE must be 'PACKHEDR'.  this={str(self.SIGNATURE)}")

            self.TABLE_SIZE.from_bytearray(src[8:16])
            self.TABLE_SIZE_ofs = ofs + 8

            if len(src) != int(self.TABLE_SIZE) + 16:
                raise TableException(self,
                                     f"The table size mismatch.  this={len(src)} expected={int(self.TABLE_SIZE) + 16}")

            self.unknown_1 = src[16:20]
            self.unknown_1_ofs = ofs + 16

            self.NAME_IDX = uint32(src[20:24])
            self.NAME_IDX_ofs = ofs + 20

            self.FILE_LIST_OFFSET.from_bytearray(src[24:28])
            self.FILE_LIST_OFFSET_ofs = ofs + 24

            self.ARCHIVE_PADDING_TYPE.from_bytearray(src[28:32])
            self.ARCHIVE_PADDING_TYPE_ofs = ofs + 28
            if int(self.ARCHIVE_PADDING_TYPE) not in [1, 2]:
                raise TableException(self,
                                     f"The ARCHIVE PADDING TYPE must be 1 or 2.  this={int(self.ARCHIVE_PADDING_TYPE)}")

            self.HASH = src[32:]
            self.HASH_ofs = ofs + 32

        def to_bytearray(self) -> bytearray:
            return (
                    self.SIGNATURE.to_bytearray() +
                    self.TABLE_SIZE.to_bytearray() +
                    self.unknown_1 +
                    self.NAME_IDX.to_bytearray() +
                    self.FILE_LIST_OFFSET.to_bytearray() +
                    self.ARCHIVE_PADDING_TYPE.to_bytearray() +
                    self.HASH
            )

    class _PACKTOC:
        def __init__(self):
            self.SIGNATURE: chararray = chararray(size=8)
            self.TABLE_SIZE: uint64 = uint64(0)
            self.TOC_SEG_SIZE: uint32 = uint32(0)
            self.TOC_SEG_COUNT: uint32 = uint32(0)
            self.unknown_1: bytearray = bytearray()
            self.TOC_SEGMENT_LIST: list[APK._PACKTOC._TOC_SEGMENT] = []
            self.PADDING: bytearray = bytearray()

            self.SIGNATURE_ofs: int = 0
            self.TABLE_SIZE_ofs: int = 0
            self.TOC_SEG_SIZE_ofs: int = 0
            self.TOC_SEG_COUNT_ofs: int = 0
            self.unknown_1_ofs: int = 0
            self.TOC_SEGMENT_LIST_ofs: int = 0
            self.PADDING_ofs: int = 0

        def from_bytearray(self, ofs: int, src: bytearray):
            self.SIGNATURE.from_bytearray(src[:8])
            self.SIGNATURE_ofs = ofs
            if str(self.SIGNATURE) != "PACKTOC ":
                raise TableException(self, f"SIGNATURE must be 'PACKTOC '.  this='{str(self.SIGNATURE)}'")

            self.TABLE_SIZE.from_bytearray(src[8:16])
            self.TABLE_SIZE_ofs = ofs + 8
            if len(src) != int(self.TABLE_SIZE) + 16:
                raise TableException(self,
                                     f"The table size mismatch.  this={len(src)} expected={int(self.TABLE_SIZE) + 16}")

            self.TOC_SEG_SIZE.from_bytearray(src[16:20])
            self.TOC_SEG_SIZE_ofs = ofs + 16
            if int(self.TOC_SEG_SIZE) != 40:
                raise TableException(self, f"The TOC_SEG_SIZE mismatch.  this={int(self.TOC_SEG_SIZE)}, expected=40")

            self.TOC_SEG_COUNT.from_bytearray(src[20:24])
            self.TOC_SEG_COUNT_ofs = ofs + 20

            self.unknown_1 = src[24:32]
            self.unknown_1_ofs = ofs + 24

            seg_ofs = 32
            self.TOC_SEGMENT_LIST_ofs = ofs + 32
            for i in range(int(self.TOC_SEG_COUNT)):
                seg = self._TOC_SEGMENT()
                seg.from_bytearray(ofs=ofs + seg_ofs, src=src[seg_ofs:seg_ofs + int(self.TOC_SEG_SIZE)])
                self.TOC_SEGMENT_LIST.append(seg)
                seg_ofs += int(self.TOC_SEG_SIZE)

            self.PADDING = src[seg_ofs:seg_ofs + get_table_padding_count(seg_ofs)]
            self.PADDING_ofs = ofs + seg_ofs

        def to_bytearray(self) -> bytearray:
            part_A: bytearray = (
                    self.SIGNATURE.to_bytearray() +
                    self.TABLE_SIZE.to_bytearray() +
                    self.TOC_SEG_SIZE.to_bytearray() +
                    self.TOC_SEG_COUNT.to_bytearray() +
                    self.unknown_1
            )

            part_B = bytearray()
            for seg in self.TOC_SEGMENT_LIST:
                part_B += seg.to_bytearray()

            part_C: bytearray = self.PADDING

            return part_A + part_B + part_C

        class _TOC_SEGMENT:
            def __init__(self):
                self.IDENTIFIER: uint32 = uint32(0)
                self.NAME_IDX: uint32 = uint32(0)
                self.ZERO: bytearray = bytearray()
                self.FILE_OFFSET: uint64 = uint64(0)  # for file
                self.ENTRY_INDEX: uint32 = uint32(0)  # for directory
                self.ENTRY_COUNT: uint32 = uint32(0)  # for directory
                self.FILE_SIZE: uint64 = uint64(0)
                self.FILE_ZSIZE: uint64 = uint64(0)

                self.IDENTIFIER_ofs: int = 0
                self.NAME_IDX_ofs: int = 0
                self.ZERO_ofs: int = 0
                self.FILE_OFFSET_ofs: int = 0
                self.ENTRY_INDEX_ofs: int = 0
                self.ENTRY_COUNT_ofs: int = 0
                self.FILE_SIZE_ofs: int = 0
                self.FILE_ZSIZE_ofs: int = 0

                self.file_index: int = -1

            def from_bytearray(self, ofs: int, src: bytearray):
                self.IDENTIFIER.from_bytearray(src[:4])
                self.IDENTIFIER_ofs = ofs
                if int(self.IDENTIFIER) not in [0, 1, 512]:
                    raise TableException(self, f"IDENTIFIER must be 0 or 1 or 512    this={int(self.IDENTIFIER)}")

                self.NAME_IDX.from_bytearray(src[4:8])
                self.NAME_IDX_ofs = ofs + 4

                self.ZERO = src[8:16]
                self.ZERO_ofs = ofs + 8

                if int(self.IDENTIFIER) == 1:  # if directory
                    self.ENTRY_INDEX.from_bytearray(src[16:20])
                    self.ENTRY_INDEX_ofs = ofs + 16
                    self.ENTRY_COUNT.from_bytearray(src[20:24])
                    self.ENTRY_COUNT_ofs = ofs + 20
                else:  # if file
                    self.FILE_OFFSET.from_bytearray(src[16:24])
                    self.FILE_OFFSET_ofs = ofs + 16

                self.FILE_SIZE.from_bytearray(src[24:32])
                self.FILE_SIZE_ofs = ofs + 24

                self.FILE_ZSIZE.from_bytearray(src[32:40])
                self.FILE_ZSIZE_ofs = ofs + 32

            def to_bytearray(self) -> bytearray:
                if int(self.IDENTIFIER) == 1:  # if directory
                    return (
                            self.IDENTIFIER.to_bytearray() +
                            self.NAME_IDX.to_bytearray() +
                            self.ZERO +
                            self.ENTRY_INDEX.to_bytearray() +
                            self.ENTRY_COUNT.to_bytearray() +
                            self.FILE_SIZE.to_bytearray() +
                            self.FILE_ZSIZE.to_bytearray()
                    )
                else:
                    return (
                            self.IDENTIFIER.to_bytearray() +
                            self.NAME_IDX.to_bytearray() +
                            self.ZERO +
                            self.FILE_OFFSET.to_bytearray() +
                            self.FILE_SIZE.to_bytearray() +
                            self.FILE_ZSIZE.to_bytearray()
                    )

    class _PACKFSLS:
        def __init__(self):
            self.SIGNATURE: chararray = chararray(size=8)
            self.TABLE_SIZE: uint64 = uint64(0)
            self.ARCHIVE_SEG_COUNT: uint32 = uint32(0)
            self.ARCHIVE_SEG_SIZE: uint32 = uint32(0)
            self.unknown_1: bytearray = bytearray()
            self.ARCHIVE_SEGMENT_LIST: list[APK._PACKFSLS._ARCHIVE_SEGMENT] = list()
            self.PADDING: bytearray = bytearray()

            self.SIGNATURE_ofs: int = 0
            self.TABLE_SIZE_ofs: int = 0
            self.ARCHIVE_SEG_COUNT_ofs: int = 0
            self.ARCHIVE_SEG_SIZE_ofs: int = 0
            self.unknown_1_ofs: int = 0
            self.ARCHIVE_SEGMENT_LIST_ofs: int = 0
            self.PADDING_ofs: int = 0

            self.temp_name_idx_list = []
            self.NAME_ARCHIVE_MAP = dict()

        def from_bytearray(self, ofs: int, src: bytearray):
            self.SIGNATURE.from_bytearray(src[:8])
            self.SIGNATURE_ofs = ofs
            if str(self.SIGNATURE) != "PACKFSLS":
                raise TableException(self, f"SIGNATURE must be 'PACKFSLS'.  this='{str(self.SIGNATURE)}'")

            self.TABLE_SIZE.from_bytearray(src[8:16])
            self.TABLE_SIZE_ofs = ofs + 8
            if len(src) != int(self.TABLE_SIZE) + 16:
                raise TableException(self,
                                     f"The table size mismatch.  this={len(src)} expected={int(self.TABLE_SIZE) + 16}")

            self.ARCHIVE_SEG_COUNT.from_bytearray(src[16:20])
            self.ARCHIVE_SEG_COUNT_ofs = ofs + 16

            self.ARCHIVE_SEG_SIZE.from_bytearray(src[20:24])
            self.ARCHIVE_SEG_SIZE_ofs = ofs + 20
            if int(self.ARCHIVE_SEG_SIZE) != 40:
                raise TableException(self,
                                     f"The ARCHIVE_SEG_SIZE mismatch.  this={int(self.ARCHIVE_SEG_SIZE)}, expected=40")

            self.unknown_1 = src[24:32]
            self.unknown_1_ofs = ofs + 24

            seg_ofs = 32
            self.ARCHIVE_SEGMENT_LIST_ofs = ofs + 32
            for i in range(int(self.ARCHIVE_SEG_COUNT)):
                seg = self._ARCHIVE_SEGMENT()
                seg.from_bytearray(ofs=ofs + seg_ofs, src=src[seg_ofs:seg_ofs + int(self.ARCHIVE_SEG_SIZE)])
                self.ARCHIVE_SEGMENT_LIST.append(seg)
                seg_ofs += int(self.ARCHIVE_SEG_SIZE)

                self.temp_name_idx_list.append(int(seg.NAME_IDX))

            self.PADDING = src[seg_ofs:seg_ofs + get_table_padding_count(seg_ofs)]
            self.PADDING_ofs = ofs + seg_ofs

        def to_bytearray(self) -> bytearray:
            part_A: bytearray = (
                    self.SIGNATURE.to_bytearray() +
                    self.TABLE_SIZE.to_bytearray() +
                    self.ARCHIVE_SEG_COUNT.to_bytearray() +
                    self.ARCHIVE_SEG_SIZE.to_bytearray() +
                    self.unknown_1
            )

            part_B = bytearray()
            for seg in self.ARCHIVE_SEGMENT_LIST:
                part_B += seg.to_bytearray()

            part_C: bytearray = self.PADDING

            return part_A + part_B + part_C

        class _ARCHIVE_SEGMENT:
            def __init__(self):
                self.NAME_IDX: uint32 = uint32(0)
                self.ZERO: uint32 = uint32()
                self.ARCHIVE_OFFSET: uint64 = uint64(0)
                self.ARCHIVE_SIZE: uint64 = uint64(0)
                self.HASH: bytearray = bytearray()

                self.NAME_IDX_ofs: int = 0
                self.ZERO_ofs: int = 0
                self.ARCHIVE_OFFSET_ofs: int = 0
                self.ARCHIVE_SIZE_ofs: int = 0
                self.HASH_ofs: int = 0

            def from_bytearray(self, ofs: int, src: bytearray):
                self.NAME_IDX.from_bytearray(src[:4])
                self.NAME_IDX_ofs = ofs

                self.ZERO = uint32(src[4:8])
                self.ZERO_ofs = ofs + 4

                self.ARCHIVE_OFFSET.from_bytearray(src[8:16])
                self.ARCHIVE_OFFSET_ofs = ofs + 8

                self.ARCHIVE_SIZE.from_bytearray(src[16:24])
                self.ARCHIVE_SIZE_ofs = ofs + 16

                self.HASH = src[24:40]
                self.HASH_ofs = ofs + 24

            def to_bytearray(self) -> bytearray:
                return (
                        self.NAME_IDX.to_bytearray() +
                        self.ZERO.to_bytearray() +
                        self.ARCHIVE_OFFSET.to_bytearray() +
                        self.ARCHIVE_SIZE.to_bytearray() +
                        self.HASH
                )

    class _GENESTRT:
        def __init__(self):
            self.SIGNATURE: chararray = chararray(size=8)
            self.TABLE_SIZE_1: uint64 = uint64(0)
            self.FILENAME_COUNT: uint32 = uint32(0)
            self.unknown_1: bytearray = bytearray()
            self.FILE_NAMES_OFFSET: uint32 = uint32(0)
            self.TABLE_SIZE_2: uint32 = uint32(0)
            self.FILENAME_OFFSET_LIST: list[uint32] = list()
            self.FILENAME_OFFSET_LIST_PADDING: bytearray = bytearray()
            self.FILE_NAMES: list[str] = list()
            self.PADDING: bytearray = bytearray()

            self.SIGNATURE_ofs: int = 0
            self.TABLE_SIZE_1_ofs: int = 0
            self.FILENAME_COUNT_ofs: int = 0
            self.unknown_1_ofs: int = 0
            self.FILE_NAMES_OFFSET_ofs: int = 0
            self.TABLE_SIZE_2_ofs: int = 0
            self.FILENAME_OFFSET_LIST_ofs: int = 0
            self.FILENAME_OFFSET_LIST_PADDING_ofs: int = 0
            self.FILE_NAMES_ofs: int = 0
            self.PADDING_ofs: int = 0

            self.FILE_NAMES_SIZE: int = 0

        def from_bytearray(self, ofs: int, src: bytearray):
            self.SIGNATURE.from_bytearray(src[:8])
            self.SIGNATURE_ofs = ofs
            if str(self.SIGNATURE) != "GENESTRT":
                raise TableException(self, f"SIGNATURE must be 'GENESTRT'.  this={str(self.SIGNATURE)}")

            self.TABLE_SIZE_1.from_bytearray(src[8:16])
            self.TABLE_SIZE_1_ofs = ofs + 8
            if len(src) != int(self.TABLE_SIZE_1) + 16:
                raise TableException(self,
                                     f"The table size mismatch.  this={len(src)} expected={int(self.TABLE_SIZE_1) + 16}")

            self.FILENAME_COUNT.from_bytearray(src[16:20])
            self.FILENAME_COUNT_ofs = ofs + 16

            self.unknown_1 = src[20:24]
            self.unknown_1_ofs = ofs + 20

            self.FILE_NAMES_OFFSET.from_bytearray(src[24:28])
            self.FILE_NAMES_OFFSET_ofs = ofs + 24

            self.TABLE_SIZE_2.from_bytearray(src[28:32])
            self.TABLE_SIZE_2_ofs = ofs + 28
            if int(self.TABLE_SIZE_1) != int(self.TABLE_SIZE_2):
                raise TableException(self,
                                     f"The TABLE_SIZE_2 mismatch.  this={int(self.TABLE_SIZE_2)} expected={int(self.TABLE_SIZE_1)}")

            seg_ofs = 32
            self.FILENAME_OFFSET_LIST_ofs = ofs + 32
            for i in range(int(self.FILENAME_COUNT)):
                self.FILENAME_OFFSET_LIST.append(uint32(src[seg_ofs:seg_ofs + 4]))
                seg_ofs += 4

            self.FILENAME_OFFSET_LIST_PADDING = src[seg_ofs:seg_ofs + get_table_padding_count(seg_ofs)]
            self.FILENAME_OFFSET_LIST_PADDING_ofs = ofs + seg_ofs

            seg_ofs += len(self.FILENAME_OFFSET_LIST_PADDING)
            self.FILE_NAMES_ofs = ofs + seg_ofs
            for i in range(int(self.FILENAME_COUNT)):
                filename: bytearray = bytearray()
                while True:
                    filename += src[seg_ofs:seg_ofs + 1]
                    self.FILE_NAMES_SIZE += len(filename)
                    seg_ofs += 1
                    if filename[-1] == 0:
                        break
                self.FILE_NAMES.append(filename.decode("ascii"))

            self.PADDING = src[seg_ofs:seg_ofs + get_table_padding_count(seg_ofs)]
            self.PADDING_ofs = ofs + seg_ofs

        def to_bytearray(self) -> bytearray:
            partA = (
                    self.SIGNATURE.to_bytearray() +
                    self.TABLE_SIZE_1.to_bytearray() +
                    self.FILENAME_COUNT.to_bytearray() +
                    self.unknown_1 +
                    self.FILE_NAMES_OFFSET.to_bytearray() +
                    self.TABLE_SIZE_2.to_bytearray()
            )

            partB = bytearray()
            for o in self.FILENAME_OFFSET_LIST:
                partB += o.to_bytearray()

            partC = self.FILENAME_OFFSET_LIST_PADDING

            partD = bytearray()
            for s in self.FILE_NAMES:
                partD += bytearray(s.encode("ascii"))

            partE = self.PADDING

            return partA + partB + partC + partD + partE

    class _GENEEOF:
        def __init__(self):
            self.SIGNATURE: chararray = chararray(size=8)
            self.TABLE_SIZE: uint64 = uint64(0)
            self.TABLE_END_PADDING: bytearray = bytearray()

            self.SIGNATURE_ofs: int = 0
            self.TABLE_SIZE_ofs: int = 0
            self.TABLE_END_PADDING_ofs: int = 0

        def from_bytearray(self, ofs: int, src: bytearray):
            self.SIGNATURE.from_bytearray(src[:8])
            self.SIGNATURE_ofs = ofs
            if str(self.SIGNATURE) != "GENEEOF ":
                raise TableException(self, f"SIGNATURE must be 'GENEEOF '.  this={str(self.SIGNATURE)}")

            self.TABLE_SIZE.from_bytearray(src[8:16])
            self.TABLE_SIZE_ofs = ofs + 8
            if int(self.TABLE_SIZE) != 0:
                raise TableException(self, f"TABLE_SIZE must be 0.  this={int(self.TABLE_SIZE)}")

            self.TABLE_END_PADDING = src[16:]
            self.TABLE_END_PADDING_ofs = ofs + 16

        def to_bytearray(self) -> bytearray:
            return (
                    self.SIGNATURE.to_bytearray() +
                    self.TABLE_SIZE.to_bytearray() +
                    self.TABLE_END_PADDING
            )

    class _FILE:
        def __init__(self):
            self.DATA: bytearray = bytearray()
            self.PADDING: bytearray = bytearray()

            self.DATA_ofs: int = 0
            self.PADDING_ofs: int = 0

        def from_bytearray(self, ofs: int, size: int, src: bytearray):
            self.DATA = src[:size]
            self.DATA_ofs = ofs

            self.PADDING = src[size:]
            self.PADDING_ofs = ofs + size

        def to_bytearray(self) -> bytearray:
            return self.DATA + self.PADDING

    class _ROOT_FILES:
        def __init__(self):
            self.FILE_LIST: list[APK._FILE] = list()
            self.PADDING: bytearray = bytearray()

            self.PADDING_ofs: int = 0

        def add_from_bytearray(self, ofs: int, size: int, src: bytearray):
            file = APK._FILE()
            file.from_bytearray(ofs, size, src)
            self.FILE_LIST.append(file)

        def to_bytearray(self) -> bytearray:
            result = bytearray()

            for file in self.FILE_LIST:
                result += file.to_bytearray()

            result += self.PADDING

            return result

        def sort(self):
            self.FILE_LIST.sort(key=lambda x: x.DATA_ofs)

    class _ARCHIVE_FILES:
        def __init__(self):
            self.FILE_LIST: list[APK._FILE] = list()
            self.PADDING: bytearray = bytearray()

            self.PADDING_ofs: int = 0

        def add_from_bytearray(self, ofs: int, size: int, src: bytearray, seg):
            file = APK._FILE()
            file.from_bytearray(ofs, size, src)
            self.FILE_LIST.append(file)

        def to_bytearray(self) -> bytearray:
            result = bytearray()

            for file in self.FILE_LIST:
                result += file.to_bytearray()

            return result

        def sort(self):
            self.FILE_LIST.sort(key=lambda x: x.DATA_ofs)

    class _PACKFSHD:
        def __init__(self):
            self.SIGNATURE: chararray = chararray(size=8)
            self.TABLE_SIZE: uint64 = uint64(0)
            self.unknown_1: bytearray = bytearray()
            self.FILE_SEG_SIZE_1: uint32 = uint32(0)
            self.FILE_SEG_COUNT: uint32 = uint32(0)
            self.FILE_SEG_SIZE_2: uint32 = uint32(0)
            self.unknown_2: bytearray = bytearray()
            self.unknown_3: bytearray = bytearray()
            self.FILE_SEGMENT_LIST: list[APK._PACKFSHD.ARCHIVE_FILE_SEGMENT] = []
            self.PADDING: bytearray = bytearray()

            self.SIGNATURE_ofs: int = 0
            self.TABLE_SIZE_ofs: int = 0
            self.unknown_1_ofs: int = 0
            self.FILE_SEG_SIZE_1_ofs: int = 0
            self.FILE_SEG_COUNT_ofs: int = 0
            self.FILE_SEG_SIZE_2_ofs: int = 0
            self.unknown_2_ofs: int = 0
            self.unknown_3_ofs: int = 0
            self.FILE_SEGMENT_LIST_ofs: int = 0
            self.PADDING_ofs: int = 0

        def from_bytearray(self, ofs: int, src: bytearray):
            self.SIGNATURE.from_bytearray(src[:8])
            self.SIGNATURE_ofs = ofs
            if str(self.SIGNATURE) != "PACKFSHD":
                raise TableException(self, f"SIGNATURE must be 'PACKFSHD'.  this='{str(self.SIGNATURE)}'")

            self.TABLE_SIZE.from_bytearray(src[8:16])
            self.TABLE_SIZE_ofs = ofs + 8
            if len(src) != int(self.TABLE_SIZE) + 16:
                raise TableException(self,
                                     f"The table size mismatch.  this={len(src)} expected={int(self.TABLE_SIZE) + 16}")

            self.unknown_1 = src[16:20]
            self.unknown_1_ofs = ofs + 16

            self.FILE_SEG_SIZE_1.from_bytearray(src[20:24])
            self.FILE_SEG_SIZE_1_ofs = ofs + 20
            if int(self.FILE_SEG_SIZE_1) != 32:
                raise TableException(self,
                                     f"The FILE_SEG_SIZE_1 mismatch.  this={int(self.FILE_SEG_SIZE_1)}, expected=32")

            self.FILE_SEG_COUNT.from_bytearray(src[24:28])
            self.FILE_SEG_COUNT_ofs = ofs + 24

            self.FILE_SEG_SIZE_2.from_bytearray(src[28:32])
            self.FILE_SEG_SIZE_2_ofs = ofs + 28
            if int(self.FILE_SEG_SIZE_1) != int(self.FILE_SEG_SIZE_2):
                raise TableException(self,
                                     f"The FILE_SEG_SIZE_2 mismatch with FILE_SEG_SIZE_1.  this={int(self.FILE_SEG_SIZE_2)}, expected={int(self.FILE_SEG_SIZE_1)}")

            self.unknown_2 = src[32:36]
            self.unknown_2_ofs = ofs + 32

            self.unknown_3 = src[36:48]
            self.unknown_3_ofs = ofs + 36

            seg_ofs = 48
            self.FILE_SEGMENT_LIST_ofs = ofs + 48
            for i in range(int(self.FILE_SEG_COUNT)):
                seg = self.ARCHIVE_FILE_SEGMENT()
                seg.from_bytearray(ofs=ofs + seg_ofs, src=src[seg_ofs:seg_ofs + int(self.FILE_SEG_SIZE_1)])
                self.FILE_SEGMENT_LIST.append(seg)
                seg_ofs += int(self.FILE_SEG_SIZE_1)

            self.PADDING = src[seg_ofs:seg_ofs + get_table_padding_count(seg_ofs)]
            self.PADDING_ofs = ofs + seg_ofs

        def to_bytearray(self) -> bytearray:
            part_A: bytearray = (
                    self.SIGNATURE.to_bytearray() +
                    self.TABLE_SIZE.to_bytearray() +
                    self.unknown_1 +
                    self.FILE_SEG_SIZE_1.to_bytearray() +
                    self.FILE_SEG_COUNT.to_bytearray() +
                    self.FILE_SEG_SIZE_2.to_bytearray() +
                    self.unknown_2 +
                    self.unknown_3
            )

            part_B = bytearray()
            for seg in self.FILE_SEGMENT_LIST:
                part_B += seg.to_bytearray()

            part_C: bytearray = self.PADDING

            return part_A + part_B + part_C

        class ARCHIVE_FILE_SEGMENT:
            def __init__(self):
                self.NAME_IDX: uint32 = uint32(0)
                self.ZIP: uint32 = uint32(0)
                self.FILE_OFFSET: uint64 = uint64(0)  # for file
                self.FILE_SIZE: uint64 = uint64(0)
                self.FILE_ZSIZE: uint64 = uint64(0)

                self.NAME_IDX_ofs: int = 0
                self.ZIP_ofs: int = 0
                self.FILE_OFFSET_ofs: int = 0
                self.FILE_SIZE_ofs: int = 0
                self.FILE_ZSIZE_ofs: int = 0

                self.file_index = -1

            def from_bytearray(self, ofs: int, src: bytearray):
                self.NAME_IDX.from_bytearray(src[:4])
                self.NAME_IDX_ofs = ofs

                self.ZIP.from_bytearray(src[4:8])
                self.ZIP_ofs = ofs + 4

                self.FILE_OFFSET.from_bytearray(src[8:16])
                self.FILE_OFFSET_ofs = ofs + 8

                self.FILE_SIZE.from_bytearray(src[16:24])
                self.FILE_SIZE_ofs = ofs + 16

                self.FILE_ZSIZE.from_bytearray(src[24:32])
                self.FILE_ZSIZE_ofs = ofs + 24

            def to_bytearray(self) -> bytearray:
                return (
                        self.NAME_IDX.to_bytearray() +
                        self.ZIP.to_bytearray() +
                        self.FILE_OFFSET.to_bytearray() +
                        self.FILE_SIZE.to_bytearray() +
                        self.FILE_ZSIZE.to_bytearray()
                )

    class ARCHIVE:
        def __init__(self):
            self.ENDIANNESS = APK._ENDIANNESS()
            self.PACKFSHD = APK._PACKFSHD()
            self.GENESTRT = APK._GENESTRT()
            self.GENEEOF = APK._GENEEOF()
            self.FILES = APK._ARCHIVE_FILES()
            self.PADDING: bytearray = bytearray()

            self.ARCHIVE_ofs: int = 0
            self.PADDING_ofs: int = 0

            self.name_idx: int = -1

        def to_bytearray(self) -> bytearray:
            return (
                    self.ENDIANNESS.to_bytearray() +
                    self.PACKFSHD.to_bytearray() +
                    self.GENESTRT.to_bytearray() +
                    self.GENEEOF.to_bytearray() +
                    self.FILES.to_bytearray() +
                    self.PADDING
            )

    class _ARCHIVES:
        def __init__(self):
            self.ARCHIVE_LIST: list[APK.ARCHIVE] = list()
            self.PADDING: bytearray = bytearray()

            self.PADDING_ofs: int = 0

        def add_from_object(self, archive: object):
            if not isinstance(archive, APK.ARCHIVE):
                raise TableException(self,
                                     f"parameter archive must be instance of APK._ARCHIVE.  this={archive.__class__.__name__}")

            self.ARCHIVE_LIST.append(archive)

        def to_bytearray(self) -> bytearray:
            result = bytearray()

            for archive in self.ARCHIVE_LIST:
                result += archive.to_bytearray()

            return result

        def sort(self):
            self.ARCHIVE_LIST.sort(key=lambda x: x.ARCHIVE_ofs)


class APKReader:
    def __init__(self, INPUT_APK_PATH: str):
        self.__INPUT_APK_PATH = INPUT_APK_PATH
        self.__APK = APK()
        self.__original_md5 = None

    def read(self):
        with open(self.__INPUT_APK_PATH, "rb") as f:
            reader = BinaryReader(bytearray(f.read()))
            reader.seek(0)

        self.__original_md5 = hashlib.md5(reader.get_raw()).hexdigest()

        print("Reading ENDIANNESS table...")
        self.__APK.ENDIANNESS.from_bytearray(ofs=reader.tell(), src=reader.get_bytes(size=16))

        print("Reading PACKHEDR table...")
        self.__APK.PACKHEDR.from_bytearray(ofs=reader.tell(), src=reader.get_bytes(size=48))

        print("Reading PACKTOC table...")
        tmp = reader.tell()
        reader.skip(8)
        size = int(uint64(reader.get_bytes(8))) + 16
        reader.seek(tmp)
        self.__APK.PACKTOC.from_bytearray(ofs=reader.tell(), src=reader.get_bytes(size=size))

        print("Reading PACKFSLS table...")
        tmp = reader.tell()
        reader.skip(8)
        size = int(uint64(reader.get_bytes(8))) + 16
        reader.seek(tmp)
        self.__APK.PACKFSLS.from_bytearray(ofs=reader.tell(), src=reader.get_bytes(size=size))

        print("Reading GENESTRT table...")
        tmp = reader.tell()
        reader.skip(8)
        size = int(uint64(reader.get_bytes(8))) + 16
        reader.seek(tmp)
        self.__APK.GENESTRT.from_bytearray(ofs=reader.tell(), src=reader.get_bytes(size=size))

        print("Reading GENEEOF table...")
        size = get_table_end_padding_count(reader.tell() + 16) + 16
        self.__APK.GENEEOF.from_bytearray(ofs=reader.tell(), src=reader.get_bytes(size=size))

        print("Reading ROOT files...")
        tmp = reader.tell()
        root_files_size = 0
        if len(self.__APK.PACKTOC.TOC_SEGMENT_LIST) > 0:
            for seg in self.__APK.PACKTOC.TOC_SEGMENT_LIST:
                if int(seg.IDENTIFIER) == 1:
                    continue
                reader.seek(int(seg.FILE_OFFSET))
                if int(seg.IDENTIFIER) == 0:  # raw file
                    filesize = int(seg.FILE_SIZE)
                elif int(seg.IDENTIFIER) == 512:  # zlib compressed file
                    filesize = int(seg.FILE_ZSIZE)
                else:
                    filesize = None
                block_size = filesize + get_root_file_padding_cnt(filesize)
                root_files_size += block_size

                self.__APK.ROOT_FILES.add_from_bytearray(ofs=int(seg.FILE_OFFSET), size=filesize,
                                                         src=reader.get_bytes(block_size))

            self.__APK.ROOT_FILES.sort()

            ofs_list = [int(x.DATA_ofs) for x in self.__APK.ROOT_FILES.FILE_LIST]

            for seg in self.__APK.PACKTOC.TOC_SEGMENT_LIST:
                if int(seg.IDENTIFIER) == 1:
                    continue
                seg.file_index = ofs_list.index(int(seg.FILE_OFFSET))

        reader.seek(tmp + root_files_size)
        if reader.EOF():
            return

        self.__APK.ROOT_FILES.PADDING_ofs = reader.tell()
        self.__APK.ROOT_FILES.PADDING = reader.get_bytes(get_root_files_padding_count(root_files_size))

        if reader.EOF():
            raise TableException(self, f"If ROOT_FILES_PADDING exists, EOF cannot appear")

        for idx, seg in enumerate(self.__APK.PACKFSLS.ARCHIVE_SEGMENT_LIST):
            print(f"Reading archive {idx + 1}/{len(self.__APK.PACKFSLS.ARCHIVE_SEGMENT_LIST)}...")
            archive = self.__APK.ARCHIVE()
            archive.name_idx = int(seg.NAME_IDX)
            ARCHIVE_OFFSET = int(seg.ARCHIVE_OFFSET)
            ARCHIVE_SIZE = int(seg.ARCHIVE_SIZE)

            archive.ARCHIVE_ofs = int(seg.ARCHIVE_OFFSET)

            reader.seek(ARCHIVE_OFFSET)

            print(f"    Reading ENDIANNESS table...")
            archive.ENDIANNESS.from_bytearray(ofs=reader.tell(), src=reader.get_bytes(size=16))

            print(f"    Reading PACKFSHD table...")
            tmp = reader.tell()
            reader.skip(8)
            size = int(uint64(reader.get_bytes(8))) + 16
            reader.seek(tmp)
            archive.PACKFSHD.from_bytearray(ofs=reader.tell(), src=reader.get_bytes(size=size))

            print(f"    Reading GENESTRT table...")
            tmp = reader.tell()
            reader.skip(8)
            size = int(uint64(reader.get_bytes(8))) + 16
            reader.seek(tmp)
            archive.GENESTRT.from_bytearray(ofs=reader.tell(), src=reader.get_bytes(size=size))

            print(f"    Reading GENEEOF table...")
            archive.GENEEOF.from_bytearray(ofs=reader.tell(), src=reader.get_bytes(size=16))

            print(f"    Reading files...")
            tmp = reader.tell()
            archive_files_size = 0
            if len(archive.PACKFSHD.FILE_SEGMENT_LIST) > 0:
                for file_seg in archive.PACKFSHD.FILE_SEGMENT_LIST:
                    real_file_offset = ARCHIVE_OFFSET + int(file_seg.FILE_OFFSET)
                    reader.seek(real_file_offset)

                    if int(file_seg.ZIP) == 0:  # raw file
                        filesize = int(file_seg.FILE_SIZE)
                    elif int(file_seg.ZIP) == 2:  # zlib compressed file
                        filesize = int(file_seg.FILE_ZSIZE)
                    else:
                        filesize = None

                    block_size = filesize + get_archive_file_padding_cnt(filesize)
                    archive_files_size += block_size

                    archive.FILES.add_from_bytearray(ofs=real_file_offset, size=filesize,
                                                     src=reader.get_bytes(block_size), seg=file_seg)

                archive.FILES.sort()

                ofs_list = [int(x.DATA_ofs) for x in archive.FILES.FILE_LIST]

                for fseg in archive.PACKFSHD.FILE_SEGMENT_LIST:
                    fseg.file_index = ofs_list.index(int(fseg.FILE_OFFSET) + ARCHIVE_OFFSET)

            reader.seek(tmp + archive_files_size)

            if not reader.EOF():
                size = get_archive_padding_count(int(self.__APK.PACKHEDR.ARCHIVE_PADDING_TYPE), ARCHIVE_SIZE)
                archive.PADDING_ofs = reader.tell()
                archive.PADDING = reader.get_bytes(size=size)

            self.__APK.ARCHIVES.add_from_object(archive)

        self.__APK.ARCHIVES.sort()

        for name_idx in self.__APK.PACKFSLS.temp_name_idx_list:
            archive_name = self.__APK.GENESTRT.FILE_NAMES[int(name_idx)][:-1]

            archive = None
            for x in self.__APK.ARCHIVES.ARCHIVE_LIST:
                if x.name_idx == name_idx:
                    archive = x
                    break

            if archive is None:
                raise Exception("archive not found")

            self.__APK.PACKFSLS.NAME_ARCHIVE_MAP[archive_name] = archive

    def get_apk(self) -> APK:
        return self.__APK

    def get_original_md5(self) -> str:
        return self.__original_md5

    def update_offsets(self):
        NEW_OFFSET: int = -1

        if len(self.__APK.PACKTOC.TOC_SEGMENT_LIST) > 0:
            toc_seg_list = sorted(
                [seg for seg in self.__APK.PACKTOC.TOC_SEGMENT_LIST if int(seg.IDENTIFIER) != 1],
                key=lambda seg: int(seg.FILE_OFFSET)
            )

            if len(toc_seg_list) > 0:
                NEW_OFFSET = int(toc_seg_list[0].FILE_OFFSET)

                tmp_seg = toc_seg_list[0]
                file_index = tmp_seg.file_index
                NEW_OFFSET += len(self.__APK.ROOT_FILES.FILE_LIST[file_index].DATA)
                NEW_OFFSET += len(self.__APK.ROOT_FILES.FILE_LIST[file_index].PADDING)

                for seg in toc_seg_list[1:]:  # offset of first file is never change
                    file_index = seg.file_index
                    seg.FILE_OFFSET = uint64(NEW_OFFSET)
                    NEW_OFFSET += len(self.__APK.ROOT_FILES.FILE_LIST[file_index].DATA)
                    NEW_OFFSET += len(self.__APK.ROOT_FILES.FILE_LIST[file_index].PADDING)

        if len(self.__APK.ARCHIVES.ARCHIVE_LIST) > 0:
            for i, archive in enumerate(self.__APK.ARCHIVES.ARCHIVE_LIST):
                print("=======================")
                old_offset = int(archive.ARCHIVE_ofs)
                if NEW_OFFSET == -1:
                    NEW_OFFSET = int(archive.ARCHIVE_ofs)

                archive_seg = \
                    [x for x in self.__APK.PACKFSLS.ARCHIVE_SEGMENT_LIST if int(x.ARCHIVE_OFFSET) == old_offset][0]
                archive_seg.ARCHIVE_OFFSET = uint64(NEW_OFFSET)

                seg_list = sorted(
                    [seg for seg in archive.PACKFSHD.FILE_SEGMENT_LIST],
                    key=lambda seg: int(seg.FILE_OFFSET)
                )

                NEW_FILE_OFFSET: int = int(seg_list[0].FILE_OFFSET)

                tmp_seg = seg_list[0]
                file_index = tmp_seg.file_index
                NEW_FILE_OFFSET += len(archive.FILES.FILE_LIST[file_index].DATA)
                NEW_FILE_OFFSET += len(archive.FILES.FILE_LIST[file_index].PADDING)
                print(NEW_FILE_OFFSET)

                for seg in seg_list[1:]:
                    file_index = seg.file_index
                    seg.FILE_OFFSET = uint64(NEW_FILE_OFFSET)
                    NEW_FILE_OFFSET += len(archive.FILES.FILE_LIST[file_index].DATA)
                    NEW_FILE_OFFSET += len(archive.FILES.FILE_LIST[file_index].PADDING)

                if i + 1 < len(self.__APK.ARCHIVES.ARCHIVE_LIST):  # make padding without last archive
                    archive.PADDING = bytearray(0)
                    new_archive_size = len(archive.to_bytearray())
                    archive_seg.ARCHIVE_SIZE = uint64(new_archive_size)

                    new_padding_cnt = get_archive_padding_count(int(self.__APK.PACKHEDR.ARCHIVE_PADDING_TYPE),
                                                                int(archive_seg.ARCHIVE_SIZE))
                    archive.PADDING = bytearray(new_padding_cnt)
                    NEW_OFFSET += new_archive_size + new_padding_cnt


class TableException(Exception):
    def __init__(self, table: object, message: str):
        table_name = table.__class__.__name__
        self.message = f"table {table_name}: {message}"
        super().__init__(self.message)


def get_name_from_name_idx(apk, name_idx: int) -> str:
    return apk.GENESTRT.FILE_NAMES[name_idx][:-1]  # remove null


class UnpackApk:
    def __init__(self, i: str, o: str, e: str):
        self.INPUT_APK_PATH: str = i
        self.OUTPUT_DUMP_PATH: str = o
        self.IS_OVERWRITE: bool = True if e == "overwrite" else False
        self.APK = None

        self.__ROOT_FILE_OFFSET_INDEX = dict()  # k: root file offset    v: root files index
        self.__ARCHIVE_FILE_OFFSET_INDEX = dict()
        self.__original_md5 = None
        self.__dumped_md5 = None

    def extract(self):
        apk_reader = APKReader(self.INPUT_APK_PATH)
        apk_reader.read()
        self.APK = apk_reader.get_apk()

        for idx, file in enumerate(self.APK.ROOT_FILES.FILE_LIST):
            self.__ROOT_FILE_OFFSET_INDEX[int(file.DATA_ofs)] = idx

        self.__original_md5 = apk_reader.get_original_md5()
        self.__dumped_md5 = hashlib.md5(self.APK.to_bytearray()).hexdigest()

        if self.__original_md5 != self.__dumped_md5:
            print("Warning! The original file and the dumped file do not match. The extract results may be inaccurate.")
            print(f"{self.__original_md5} != {self.__dumped_md5}")

        if len(self.APK.PACKTOC.TOC_SEGMENT_LIST) > 0:
            toc_segment = self.APK.PACKTOC.TOC_SEGMENT_LIST[0]
            if int(toc_segment.IDENTIFIER) == 1:  # If folders are present, they are expected to start with an empty string directory.
                self.extract_directory(int(toc_segment.ENTRY_INDEX), int(toc_segment.ENTRY_COUNT), "")
            else:  # files for root directory, Only files are expected, without any folders.
                for toc_segment in self.APK.PACKTOC.TOC_SEGMENT_LIST:
                    self.extract_root_file(toc_segment, get_name_from_name_idx(self.APK, int(toc_segment.NAME_IDX)))

        if int(self.APK.PACKFSLS.ARCHIVE_SEG_COUNT) > 0:
            os.makedirs(os.path.join(self.OUTPUT_DUMP_PATH, "__ARCHIVE__"), exist_ok=True)

            archive_offset_index = dict()
            for archive_segment in self.APK.PACKFSLS.ARCHIVE_SEGMENT_LIST:
                archive_name = get_name_from_name_idx(self.APK, int(archive_segment.NAME_IDX))
                archive_dir_path = os.path.join(self.OUTPUT_DUMP_PATH, "__ARCHIVE__", archive_name)
                os.makedirs(archive_dir_path, exist_ok=True)
                archive_offset_index[int(archive_segment.ARCHIVE_OFFSET)] = archive_dir_path

            for archive in self.APK.ARCHIVES.ARCHIVE_LIST:
                archive_dir_path = archive_offset_index[int(archive.ARCHIVE_ofs)]

                self.__ARCHIVE_FILE_OFFSET_INDEX.clear()
                for idx, file in enumerate(archive.FILES.FILE_LIST):
                    self.__ARCHIVE_FILE_OFFSET_INDEX[int(file.DATA_ofs)] = idx

                for file_segment in archive.PACKFSHD.FILE_SEGMENT_LIST:
                    self.extract_archive_file(archive, file_segment, archive_dir_path,
                                              get_name_from_name_idx(archive, int(file_segment.NAME_IDX)))

    def extract_directory(self, entry_index: int, entry_count: int, path: str):
        os.makedirs(os.path.join(self.OUTPUT_DUMP_PATH, path), exist_ok=True)

        for i in range(entry_index, entry_index + entry_count):
            toc_segment = self.APK.PACKTOC.TOC_SEGMENT_LIST[i]
            if int(toc_segment.IDENTIFIER) == 1:
                self.extract_directory(int(toc_segment.ENTRY_INDEX), int(toc_segment.ENTRY_COUNT),
                                       os.path.join(path, get_name_from_name_idx(self.APK, int(toc_segment.NAME_IDX))))
            else:
                file_path = os.path.join(path, get_name_from_name_idx(self.APK, int(toc_segment.NAME_IDX)))
                self.extract_root_file(toc_segment, file_path)

    def extract_root_file(self, toc_segment, path: str):
        file_path = os.path.join(self.OUTPUT_DUMP_PATH, path)

        if os.path.isfile(file_path) and not self.IS_OVERWRITE:
            return

        file_idx = self.__ROOT_FILE_OFFSET_INDEX[int(toc_segment.FILE_OFFSET)]
        file = self.APK.ROOT_FILES.FILE_LIST[file_idx]
        with open(file_path, "wb") as f:
            if int(toc_segment.IDENTIFIER) == 512:  # zlib file
                f.write(zlib.decompress(file.DATA))
            else:
                f.write(file.DATA)

    def extract_archive_file(self, archive, file_seg, archive_dir_path: str, path: str):
        parents_path = "/".join(path.split("/")[:-1])
        file_path = os.path.join(archive_dir_path, path)
        os.makedirs(os.path.join(archive_dir_path, parents_path), exist_ok=True)

        if os.path.isfile(file_path) and not self.IS_OVERWRITE:
            return

        file_idx = self.__ARCHIVE_FILE_OFFSET_INDEX[archive.ARCHIVE_ofs + int(file_seg.FILE_OFFSET)]
        file = archive.FILES.FILE_LIST[file_idx]
        with open(file_path, "wb") as f:
            if int(file_seg.ZIP) == 2:  # zlib file
                f.write(zlib.decompress(file.DATA))
            else:
                f.write(file.DATA)


class PatchApk:
    def __init__(self, i: list, o: str):
        self.INPUT_APK_PATH: str = i[0]
        self.INPUT_DIR_PATH: str = i[1]
        self.OUTPUT_PATCHED_PATH: str = o
        self.APK = None
        self.TREE: dict = dict()

        self.__original_md5 = None
        self.__dumped_md5 = None

    def patch(self):
        print(f"Reading apk file {self.INPUT_APK_PATH}")
        apk_reader = APKReader(self.INPUT_APK_PATH)
        apk_reader.read()
        self.APK = apk_reader.get_apk()
        self.TREE = make_tree(self.APK)

        self.__original_md5 = apk_reader.get_original_md5()
        self.__dumped_md5 = hashlib.md5(self.APK.to_bytearray()).hexdigest()

        if self.__original_md5 != self.__dumped_md5:
            print("Warning! The original file and the dumped file do not match. The dump result may be inaccurate.")
            print(f"{self.__original_md5} != {self.__dumped_md5}")

        print(f"Get changed file list...")
        changed_files = get_changed_file_path(self.INPUT_DIR_PATH)
        print(f"{len(changed_files)} changed files.")

        for idx, changed_file in enumerate(changed_files):
            print(f"\r\033[KPatching...[{idx + 1}/{len(changed_files)}] {changed_file}", end="")
            with open(os.path.join(self.INPUT_DIR_PATH, changed_file), 'rb') as f:
                data = f.read()

                if changed_file.startswith("__ARCHIVE__"):
                    archive_name = changed_file.split("/")[1]
                    file_path = "/".join(changed_file.split("/")[2:])
                    seg = self.TREE["ARCHIVE"][archive_name][file_path]
                    _zip = int(seg.ZIP)

                    if _zip == 0:
                        seg.FILE_SIZE = uint64(len(data))
                        seg.FILE_ZSIZE = uint64(0)
                    elif _zip == 2:
                        seg.FILE_SIZE = uint64(len(data))
                        data = zlib.compress(data, level=9)
                        seg.FILE_ZSIZE = uint64(len(data))
                    else:
                        raise Exception(f"unknown ZIP {_zip}")

                    file = self.APK.PACKFSLS.NAME_ARCHIVE_MAP[archive_name].FILES.FILE_LIST[seg.file_index]
                    file.DATA = copy.deepcopy(data)
                    padding_cnt = get_archive_file_padding_cnt(len(file.DATA))
                    file.PADDING = copy.deepcopy(bytearray(padding_cnt))
                else:
                    seg = self.TREE["ROOT"][changed_file]
                    identifier = int(seg.IDENTIFIER)

                    if identifier == 0:
                        seg.FILE_SIZE = uint64(len(data))
                        seg.FILE_ZSIZE = uint64(0)
                    elif identifier == 512:
                        seg.FILE_SIZE = uint64(len(data))
                        data = zlib.compress(data, level=9)
                        seg.FILE_ZSIZE = uint64(len(data))
                    else:
                        raise Exception(f"unknown identifier {identifier}")

                    file = self.APK.ROOT_FILES.FILE_LIST[seg.file_index]
                    file.DATA = copy.deepcopy(data)
                    padding_cnt = get_root_file_padding_cnt(len(file.DATA))
                    file.PADDING = copy.deepcopy(bytearray(padding_cnt))

        print()

        print("Update offsets...")
        apk_reader.update_offsets()
        self.APK = apk_reader.get_apk()

        print("Write patched apk file...")
        with open(self.OUTPUT_PATCHED_PATH, "wb") as f:
            f.write(self.APK.to_bytearray())

        print("Validating patched apk...")
        temp = APKReader(self.OUTPUT_PATCHED_PATH)
        temp.read()

        print("OK.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="This is a tool for APK found in certain games.",
                                     add_help=False)

    subparser = parser.add_subparsers(dest="script")

    parser_unpack_apk = subparser.add_parser("unpack", add_help=False)
    parser_unpack_apk.add_argument("-i", type=str, required=True)
    parser_unpack_apk.add_argument("-o", type=str, required=True)
    parser_unpack_apk.add_argument("-e", type=str, choices=["overwrite", "skip"], default="overwrite")

    parser_patch_apk = subparser.add_parser("pack", add_help=False)
    parser_patch_apk.add_argument("-i", type=str, required=True, nargs=2)
    parser_patch_apk.add_argument("-o", type=str, required=True)

    args = parser.parse_args()

    if args.script == "unpack":
        UnpackApk(args.i, args.o, args.e).extract()
    elif args.script == "pack":
        PatchApk(args.i, args.o).patch()
    else:
        raise RuntimeError("Unsupported params")
