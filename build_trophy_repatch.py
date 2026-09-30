from __future__ import annotations

import argparse
import hashlib
import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


TRP_MAGIC = 0xDCA24D00
TRP_VERSION = 2
HEADER_SIZE = 0x40
ENTRY_SIZE = 0x40
HASH_OFFSET = 0x1C
HASH_SIZE = 20

TITLE_NAME = "伪恋　出嫁！？"
TITLE_DETAIL = "这是《伪恋　出嫁！？》的奖杯数据。"

TROPHY_TEXT = {
    "000": ("全收集", "获得了全部奖杯。"),
    "001": ("序幕", "通关了序章事件。"),
    "002": ("后门", "通关了隐藏的序章事件。"),
    "003": ("恋人", "迎来了与千棘的幸福结局。"),
    "004": ("结婚", "迎来了与千棘的另一个结局。"),
    "005": ("女友", "迎来了与小咲的幸福结局。"),
    "006": ("监禁", "迎来了与小咲的另一个结局。"),
    "007": ("秘密", "迎来了与诚士郎的幸福结局。"),
    "008": ("互换", "迎来了与诚士郎的另一个结局。"),
    "009": ("逃亡", "迎来了与万里花的幸福结局。"),
    "010": ("偶像", "迎来了与万里花的另一个结局。"),
    "011": ("朋友", "迎来了与琉璃的平稳结局。"),
    "012": ("眼镜", "迎来了与琉璃的另一个结局。"),
    "013": ("觉醒", "迎来了真正的结局。"),
    "014": ("后宫", "迎来了安逸的结局。"),
    "015": ("真结局", "观看了全部真结局。"),
    "016": ("另一结局", "观看了全部另一结局。"),
    "017": ("重来", "被小玉的力量送回了第一天。"),
    "018": ("精疲力尽", "HP降到了零。"),
    "019": ("探病", "观看了所有女孩的探病事件。"),
    "020": ("道具", "使用了10次道具。"),
    "021": ("收藏", "获得了全部道具。"),
    "022": ("相册", "收集了全部事件CG。"),
    "023": ("真爱", "游玩了真爱模式＋。"),
    "024": ("出嫁", "在真爱模式＋中与四位女孩结缘。"),
    "025": ("蹑手", "通关了潜行游戏。"),
    "026": ("蹑脚", "在所有潜行游戏中刷新了纪录。"),
    "027": ("抽鬼牌", "在抽鬼牌中获得了第一名。"),
}


@dataclass(frozen=True)
class TrpEntry:
    name: str
    payload: bytes
    trailer: bytes


def align(value: int, boundary: int = 0x10) -> int:
    return (value + boundary - 1) & ~(boundary - 1)


def read_trp(path: Path) -> tuple[bytearray, list[TrpEntry]]:
    data = path.read_bytes()
    if len(data) < HEADER_SIZE:
        raise ValueError(f"TRP header is truncated: {path}")

    magic, version, total_size, entry_count, entry_size = struct.unpack_from(
        ">IIQII", data, 0
    )
    if magic != TRP_MAGIC or version != TRP_VERSION:
        raise ValueError(f"unsupported TRP header: magic=0x{magic:08X}, version={version}")
    if total_size != len(data):
        raise ValueError(f"TRP size mismatch: header={total_size}, actual={len(data)}")
    if entry_size != ENTRY_SIZE:
        raise ValueError(f"unsupported TRP entry size: 0x{entry_size:X}")
    if HEADER_SIZE + entry_count * entry_size > len(data):
        raise ValueError("TRP entry table is truncated")

    hash_image = bytearray(data)
    stored_hash = bytes(hash_image[HASH_OFFSET : HASH_OFFSET + HASH_SIZE])
    hash_image[HASH_OFFSET : HASH_OFFSET + HASH_SIZE] = b"\0" * HASH_SIZE
    if hashlib.sha1(hash_image).digest() != stored_hash:
        raise ValueError("source TRP SHA-1 does not match its header")

    entries = []
    for index in range(entry_count):
        position = HEADER_SIZE + index * entry_size
        row = data[position : position + entry_size]
        raw_name = row[:0x20].split(b"\0", 1)[0]
        name = raw_name.decode("ascii")
        offset, size = struct.unpack_from(">QQ", row, 0x20)
        if offset + size > len(data):
            raise ValueError(f"TRP entry exceeds archive: {name}")
        entries.append(TrpEntry(name, data[offset : offset + size], row[0x30:0x40]))

    return bytearray(data[:HEADER_SIZE]), entries


def translate_trop_sfm(payload: bytes) -> bytes:
    text = payload.decode("utf-8")
    root_start = text.find("<trophyconf")
    if root_start < 0:
        raise ValueError("TROP.SFM does not contain a trophyconf root")

    prefix = text[:root_start]
    root = ET.fromstring(text[root_start:])
    title_name = root.find("title-name")
    title_detail = root.find("title-detail")
    if title_name is None or title_detail is None:
        raise ValueError("TROP.SFM is missing title metadata")
    title_name.text = TITLE_NAME
    title_detail.text = TITLE_DETAIL

    seen = set()
    for trophy in root.findall("trophy"):
        trophy_id = trophy.get("id")
        if trophy_id not in TROPHY_TEXT:
            raise ValueError(f"unexpected trophy id in TROP.SFM: {trophy_id}")
        name = trophy.find("name")
        detail = trophy.find("detail")
        if name is None or detail is None:
            raise ValueError(f"trophy {trophy_id} is missing name or detail")
        name.text, detail.text = TROPHY_TEXT[trophy_id]
        seen.add(trophy_id)

    missing = sorted(set(TROPHY_TEXT) - seen)
    if missing:
        raise ValueError(f"TROP.SFM is missing trophy ids: {', '.join(missing)}")

    ET.indent(root, space=" ")
    translated = prefix + ET.tostring(root, encoding="unicode") + "\n"
    return translated.encode("utf-8")


def pack_trp(header: bytearray, entries: list[TrpEntry]) -> bytes:
    if len(header) != HEADER_SIZE:
        raise ValueError("invalid preserved TRP header size")

    table_end = HEADER_SIZE + len(entries) * ENTRY_SIZE
    offset = align(table_end)
    rows = []
    bodies = []
    for entry in entries:
        encoded_name = entry.name.encode("ascii")
        if len(encoded_name) > 0x1F:
            raise ValueError(f"TRP entry name is too long: {entry.name}")
        offset = align(offset)
        row = encoded_name.ljust(0x20, b"\0")
        row += struct.pack(">QQ", offset, len(entry.payload))
        row += entry.trailer
        if len(row) != ENTRY_SIZE:
            raise ValueError(f"invalid rebuilt table row: {entry.name}")
        rows.append(row)
        bodies.append((offset, entry.payload))
        offset += len(entry.payload)

    total_size = align(offset)
    image = bytearray(total_size)
    image[:HEADER_SIZE] = header
    struct.pack_into(">QII", image, 0x08, total_size, len(entries), ENTRY_SIZE)
    image[HASH_OFFSET : HASH_OFFSET + HASH_SIZE] = b"\0" * HASH_SIZE
    image[HEADER_SIZE:table_end] = b"".join(rows)
    for position, payload in bodies:
        image[position : position + len(payload)] = payload

    image[HASH_OFFSET : HASH_OFFSET + HASH_SIZE] = hashlib.sha1(image).digest()
    return bytes(image)


def build(source: Path, output: Path) -> None:
    header, source_entries = read_trp(source)
    translated_entries = []
    found_trop_sfm = False
    for entry in source_entries:
        payload = entry.payload
        if entry.name == "TROP.SFM":
            payload = translate_trop_sfm(payload)
            found_trop_sfm = True
        translated_entries.append(TrpEntry(entry.name, payload, entry.trailer))
    if not found_trop_sfm:
        raise ValueError("source TRP does not contain TROP.SFM")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(pack_trp(header, translated_entries))

    _, built_entries = read_trp(output)
    source_by_name = {entry.name: entry for entry in source_entries}
    built_by_name = {entry.name: entry for entry in built_entries}
    if source_by_name.keys() != built_by_name.keys():
        raise ValueError("rebuilt TRP entry list changed")
    for name, source_entry in source_by_name.items():
        if name != "TROP.SFM" and source_entry.payload != built_by_name[name].payload:
            raise ValueError(f"rebuilt TRP changed an unrelated entry: {name}")

    translated_text = built_by_name["TROP.SFM"].payload.decode("utf-8")
    translated_root_start = translated_text.find("<trophyconf")
    translated_xml = ET.fromstring(translated_text[translated_root_start:])
    if translated_xml.findtext("title-name") != TITLE_NAME:
        raise ValueError("translated title failed round-trip verification")
    for trophy in translated_xml.findall("trophy"):
        expected = TROPHY_TEXT[trophy.get("id")]
        actual = (trophy.findtext("name"), trophy.findtext("detail"))
        if actual != expected:
            raise ValueError(f"translated trophy failed verification: {trophy.get('id')}")

    print(f"Wrote {output}")
    print(f"Entries: {len(built_entries)}; trophies: {len(TROPHY_TEXT)}")
    print(f"Size: {output.stat().st_size} bytes")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Chinese Nisekoi Vita trophy rePatch")
    parser.add_argument("source", type=Path, help="original TROPHY.TRP")
    parser.add_argument("output", type=Path, help="translated TROPHY.TRP")
    args = parser.parse_args()
    build(args.source, args.output)


if __name__ == "__main__":
    main()
