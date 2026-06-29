## ark data format

### The ark (.ark) format consists of:

|  File layout   |
|:--------------:|
|  ENDILTLE      |
|  ARK ARKF      |
|  ARK TEX2      |
|  ARK TXOS      |
|  ARK LAY2...   |
|  GENESTRT      |

All integer values observed here are little-endian.

-------------------------

## ENDILTLE

### ENDILTLE Header

| Offset (h) | Size (h) | Example (h) | Value (conversion) | Notes |
|:----------:|:--------:|:-----------:|:------------------:|:------|
| 0x00 | 0x10 | 45 4E 44 49 4C 54 4C 45 00 00 00 00 00 00 00 00 | ENDILTLE | File magic. |

-------------------------

## ARK ARKF

### ARK ARKF Header

| Offset (h) | Size (h) | Example (h) | Value (conversion) | Notes |
|:----------:|:--------:|:-----------:|:------------------:|:------|
| 0x00 | 0x08 | 41 52 4B 20 41 52 4B 46 | ARK ARKF | Chunk magic. |
| 0x08 | 0x08 | 10 00 00 00 00 00 00 00 | 0x10 bytes | Chunk content size, starts from 0x10. |

### ARK ARKF Content

| Offset (h) | Size (h) | Example (h) | Value (conversion) | Notes |
|:----------:|:--------:|:-----------:|:------------------:|:------|
| 0x10 | 0x04 | - - - | - - - | Unknown. |
| 0x14 | 0x04 | 80 00 00 00 | 128 | LAY2 chunk count. |
| 0x18 | 0x08 | - - - | - - - | Unknown. |

-------------------------

## ARK TEX2

### ARK TEX2 Header

| Offset (h) | Size (h) | Example (h) | Value (conversion) | Notes |
|:----------:|:--------:|:-----------:|:------------------:|:------|
| 0x00 | 0x08 | 41 52 4B 20 54 45 58 32 | ARK TEX2 | Chunk magic. |
| 0x08 | 0x08 | 60 00 00 00 00 00 00 00 | 0x60 bytes | Chunk content size, starts from 0x10. |

### ARK TEX2 Content

The TEX2 chunk describes texture resources used by TXOS entries. In `gallery.ark`, it is a small table of 0x10-byte records. TXOS entry +0x10 stores the zero-based TEX2 record index, so adding a new GXT requires adding a TEX2 record and pointing the new TXOS entry to that record.

| Relative Offset (h) | Size (h) | Example (h) | Value (conversion) | Notes |
|:-------------------:|:--------:|:-----------:|:------------------:|:------|
| 0x00 | 0x04 | 05 00 00 00 | 5 | TEX2 record count. |
| 0x04 | 0x04 | 10 00 00 00 | 0x10 bytes | TEX2 record size. |
| 0x08 | 0x04 | 10 00 00 00 | 0x10 | First TEX2 record offset, relative to TEX2 content start. |
| 0x0C | 0x04 | 00 00 00 00 | 0 | Unknown or padding. |

### ARK TEX2 Record

Each TEX2 record is 0x10 bytes.

| Relative Offset (h) | Size (h) | Example (h) | Value (conversion) | Notes |
|:-------------------:|:--------:|:-----------:|:------------------:|:------|
| 0x00 | 0x04 | 00 00 00 00 | 0 | String ID, indexes GENESTRT. The string is a GXT path such as `gallery_tex.gxt`. |
| 0x04 | 0x04 | 00 00 00 00 | 0 | Unknown. |
| 0x08 | 0x04 | 00 00 00 00 | 0 | Unknown. |
| 0x0C | 0x04 | 00 00 00 00 | 0 | Unknown. |

For the current `gallery.ark`, the TEX2 table is:

| TEX2 Index | String |
|:----------:|:-------|
| 0 | `gallery_tex.gxt` |
| 1 | `gallery_pic.gxt` |
| 2 | `../oldmaid/oldmaid_result_chara_tex.gxt` |
| 3 | `gallery_music_pic.gxt` |
| 4 | `gallery_wall_tex.gxt` |

-------------------------

## ARK TXOS

### ARK TXOS Header

| Offset (h) | Size (h) | Example (h) | Value (conversion) | Notes |
|:----------:|:--------:|:-----------:|:------------------:|:------|
| 0x00 | 0x08 | 41 52 4B 20 54 58 4F 53 | ARK TXOS | Chunk magic. |
| 0x08 | 0x08 | 10 36 00 00 00 00 00 00 | 0x3610 bytes | Chunk content size, starts from 0x10. |

### ARK TXOS Sub Header

| Offset (h) | Size (h) | Example (h) | Value (conversion) | Notes |
|:----------:|:--------:|:-----------:|:------------------:|:------|
| 0x10 | 0x04 | D8 00 00 00 | 216 entries | TXOS entry count. |
| 0x14 | 0x04 | 40 00 00 00 | 0x40 bytes | TXOS entry size. |

### ARK TXOS Entry

Each TXOS entry is 0x40 bytes. Entry 0 starts at chunk offset 0x18.

| Relative Offset (h) | Size (h) | Example (h) | Value (conversion) | Notes |
|:-------------------:|:--------:|:-----------:|:------------------:|:------|
| 0x00 | 0x04 | 00 00 00 00 | 0 | Type or flags. |
| 0x04 | 0x04 | 00 00 00 00 | 0 | Unknown. |
| 0x08 | 0x04 | 00 00 00 80 | 0x80000000 | Unknown flag. |
| 0x0C | 0x04 | 00 00 00 00 | 0 | Unknown. |
| 0x10 | 0x04 | 00 00 00 00 | 0 | TEX2 texture index. This selects which GXT file owns the atlas coordinates below. |
| 0x14 | 0x04 | 39 00 00 00 | 57 | Texture atlas X coordinate. |
| 0x18 | 0x04 | 02 00 00 00 | 2 | Texture atlas Y coordinate. |
| 0x1C | 0x04 | 26 00 00 00 | 38 | Source width. |
| 0x20 | 0x04 | 28 00 00 00 | 40 | Source height. |
| 0x24 | 0x04 | 01 00 01 00 | 0x00010001 | Unknown, often constant. |
| 0x28 | 0x04 | 01 00 01 00 | 0x00010001 | Unknown, often constant. |
| 0x2C | 0x04 | 00 00 00 00 | 0 | Unknown. |
| 0x30 | 0x04 | 00 00 00 00 | 0 | Unknown. |
| 0x34 | 0x04 | 85 00 00 00 | 133 | String ID, indexes GENESTRT. |
| 0x38 | 0x04 | 00 00 00 00 | 0 | Unknown. |
| 0x3C | 0x04 | 00 00 00 00 | 0 | Unknown. |

Important note for `ark_data/update_config.csv`: its `txos_point` value points 8 bytes before the actual TXOS entry data used by `ark_parser.py`. Therefore:

```text
CSV txos_point + 0x1C == TXOS entry + 0x14 == atlas X
CSV txos_point + 0x20 == TXOS entry + 0x18 == atlas Y
```

-------------------------

## ARK LAY2

LAY2 chunks define layout objects and animation/keyframe data. There are multiple ARK LAY2 chunks; the chunk count is stored in ARK ARKF.

### ARK LAY2 Header

| Offset (h) | Size (h) | Example (h) | Value (conversion) | Notes |
|:----------:|:--------:|:-----------:|:------------------:|:------|
| 0x00 | 0x08 | 41 52 4B 20 4C 41 59 32 | ARK LAY2 | Chunk magic. |
| 0x08 | 0x08 | - - - | - - - | Chunk content size, starts from 0x10. |
| 0x10 | 0x04 | - - - | - - - | String ID for this layout name. |
| 0x14 | 0x04 | - - - | - - - | Unknown. |
| 0x18 | 0x04 | - - - | - - - | Unknown. |
| 0x1C | 0x04 | - - - | - - - | Unknown. |
| 0x20 | 0x04 | - - - | - - - | Unknown. |
| 0x24 | 0x04 | 09 00 00 00 | 9 items | LAY2 item count. |
| 0x28 | 0x04 | C0 03 00 00 | 960 | Canvas width. |
| 0x2C | 0x04 | 20 02 00 00 | 544 | Canvas height. |
| 0x30 | 0x04 | 30 00 00 00 | 0x30 | Pre-header size, usually 0x30. |
| 0x34 | 0x04 | E0 01 00 00 | 0x1E0 | Item/transform header size or related block size. |
| 0x38 | 0x04 | 00 00 00 00 | 0 | Unknown. |
| 0x3C | 0x04 | 00 00 00 00 | 0 | Unknown. |

### ARK LAY2 Item

Item data starts at LAY2 chunk offset 0x40. Each item is 0x30 bytes.

| Relative Offset (h) | Size (h) | Example (h) | Value (conversion) | Notes |
|:-------------------:|:--------:|:-----------:|:------------------:|:------|
| 0x00 | 0x04 | 30 00 00 00 | 0x30 | Item tag, usually 0x30. |
| 0x04 | 0x04 | 05 00 00 00 | 5 | Instance ID or item type. |
| 0x08 | 0x04 | 00 00 00 00 | 0 | Base X. |
| 0x0C | 0x04 | 00 00 00 00 | 0 | Base Y. |
| 0x10 | 0x04 | - - - | - - - | String ID for item name. |
| 0x14 | 0x04 | 26 00 00 00 | 38 | Canvas/item width. |
| 0x18 | 0x04 | 28 00 00 00 | 40 | Canvas/item height. |
| 0x1C | 0x04 | 13 00 00 00 | 19 | Unknown; observed as pivot/animation center X for title glyphs. Do not zero blindly. |
| 0x20 | 0x04 | 14 00 00 00 | 20 | Unknown; observed as pivot/animation center Y for title glyphs. Do not zero blindly. |
| 0x24 | 0x04 | - - - | - - - | TXOS ID, references ARK TXOS entry. |
| 0x28 | 0x04 | 00 00 00 00 | 0 | Unknown. |
| 0x2C | 0x04 | 00 00 00 00 | 0 | Unknown. |

### ARK LAY2 Animation Block

After the item array, there is animation/keyframe data. Observed title LAY2 chunks store one animation block per item, in the same order as the item array.

```text
LAY2 item array:
  item[0]
  item[1]
  ...

Animation block area:
  block for item[0]
  block for item[1]
  ...
```

### ARK LAY2 Animation Block Header

| Relative Offset (h) | Size (h) | Example (h) | Value (conversion) | Notes |
|:-------------------:|:--------:|:-----------:|:------------------:|:------|
| 0x00 | 0x04 | D8 00 00 00 | 0xD8 bytes | Block size. |
| 0x04 | 0x04 | 04 00 00 00 | 4 frames | Keyframe count. |

Block size follows this formula in observed title chunks:

```text
block_size = 0x08 + keyframe_count * 0x34
```

### ARK LAY2 Keyframe

Each keyframe is 0x34 bytes.

| Relative Offset (h) | Size (h) | Example (h) | Value (conversion) | Notes |
|:-------------------:|:--------:|:-----------:|:------------------:|:------|
| 0x00 | 0x04 | 34 00 14 00 | packed 0x00140034 | Unknown packed data. Low word is often 0x34, high word is often 0x14. |
| 0x04 | 0x04 | 1F 00 00 00 | 31 | Unknown. |
| 0x08 | 0x04 | 00 00 00 00 | frame/time | Keyframe time or sequence value. |
| 0x0C | 0x04 | 05 00 00 00 | 5 | Unknown, often item type or interpolation group. |
| 0x10 | 0x04 | 00 00 00 00 | 0 | Unknown. |
| 0x14 | 0x04 | 19 00 00 00 | 25 | Draw offset X / glyph baseline X. |
| 0x18 | 0x04 | 0B 00 00 00 | 11 | Draw offset Y / glyph baseline Y. |
| 0x1C | 0x04 | FF FF FF FF | -1 | Unknown signed value. |
| 0x20 | 0x04 | 00 00 00 00 | 0 | Unknown. |
| 0x24 | 0x04 | 5A 00 00 00 | 90 | Motion Y or transition offset. Observed 0 for static/baseline frames, 90 or -90 for vertical transition frames. |
| 0x28 | 0x04 | 00 00 00 00 | 0 | Unknown. |
| 0x2C | 0x04 | 64 00 00 00 | 100 | Scale/alpha-like value, often 100. |
| 0x30 | 0x04 | 64 00 00 00 | 100 | Scale/alpha-like value, often 100. |

For gallery header glyphs:

- Keyframe +0x14 is used to normalize X spacing between glyphs.
- Keyframe +0x18 is used to normalize Y baseline.
- Keyframe +0x24 should not be zeroed when preserving the vertical in/out animation.
- LAY2 item +0x1C/+0x20 should not be zeroed blindly, because doing so can remove or break the original vertical transition behavior.

-------------------------

## GENESTRT

### GENESTRT Header

| Offset (h) | Size (h) | Example (h) | Value (conversion) | Notes |
|:----------:|:--------:|:-----------:|:------------------:|:------|
| 0x00 | 0x08 | 47 45 4E 45 53 54 52 54 | GENESTRT | Chunk magic. |
| 0x08 | 0x08 | - - - | - - - | Chunk content size, starts from 0x10. |

### GENESTRT Sub Header

| Offset (h) | Size (h) | Example (h) | Value (conversion) | Notes |
|:----------:|:--------:|:-----------:|:------------------:|:------|
| 0x10 | 0x04 | - - - | - - - | Unknown. |
| 0x14 | 0x04 | - - - | - - - | Unknown. |
| 0x18 | 0x04 | - - - | - - - | Index table size, relative to GENESTRT content start. |
| 0x1C | 0x04 | - - - | - - - | Content size or end offset. |

### GENESTRT Index Table

The index table starts at GENESTRT content offset 0x10 and ends at the offset stored at content +0x08. Each entry is 4 bytes and stores an offset into the string area.

Entries with value 0 can appear after the first entry and are skipped by the current parser.

### GENESTRT String Area

The string area starts at:

```text
GENESTRT content start + index_table_size
```

Each string is a null-terminated UTF-8 string. TXOS entries and LAY2 headers/items reference strings by string ID.

-------------------------

## Notes for gallery title patching

Important fields used by `generate_gallery_ark.py`:

| Field | Meaning |
|:------|:--------|
| TXOS entry +0x14 | Texture atlas X. In `update_config.csv`, use `txos_point + 0x1C`. |
| TXOS entry +0x18 | Texture atlas Y. In `update_config.csv`, use `txos_point + 0x20`. |
| LAY2 item +0x24 | TXOS ID. `update_config.csv` `lay2_ptrs` point here. |
| LAY2 keyframe +0x14 | Draw offset X / visible glyph X baseline. |
| LAY2 keyframe +0x18 | Draw offset Y / visible glyph Y baseline. |
| LAY2 keyframe +0x24 | Vertical transition offset. Preserve relative values to keep in/out animation. |
