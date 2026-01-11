from io import BytesIO
from collections import OrderedDict

order = "little"


def get4_bytes(data, start):
    return int.from_bytes(data[start: start + 0x04], order)


class Anagram:
    class CharText:
        def read4_int(self):
            return int.from_bytes(self.data.read(0x04), order)

        def __init__(self, data, str_table):
            self.data = data

            self.iPosX = self.read4_int()
            self.iPosY = self.read4_int()
            self.strTextIdx = self.read4_int()
            self.strText = '' if self.strTextIdx == 0 else str_table[str(self.strTextIdx)]

    def __init__(self, data, str_table):
        self.data = BytesIO(data)

        self.SelfId = self.read4_int()
        self.iQuestId = self.read4_int()
        self.iLimitMSec = self.read4_int()

        self.strTitleIdx = self.read4_int()
        self.strTitle = str_table[str(self.strTitleIdx)]

        self.strAnswerIdx = []
        self.strAnswer = []
        self.answerLength = 0
        for i in range(5):
            idx = self.read4_int()
            self.strAnswerIdx.append(idx)
            answer = '' if idx == 0 else str_table[str(idx)]
            self.answerLength = max(len(answer), self.answerLength)
            self.strAnswer.append(answer)

        self.charText = []
        for i in range(15):
            self.charText.append(Anagram.CharText(self.data, str_table))

    def read4_int(self):
        return int.from_bytes(self.data.read(0x04), order)

    def __str__(self):
        result = "[\n"
        result += f'SelfId: {self.SelfId}\n'
        result += f'iQuestId: {self.iQuestId}\n'
        result += f'iLimitMSec: {self.iLimitMSec}\n\n'
        result += f'strTitle: \n\t{self.strTitle}\n'

        result += f"\nAnswer: [{self.answerLength}]\n"
        for answer in self.strAnswer:
            if answer:
                result += f'\t{answer}\n'

        result += "\nChar:\n"
        for char in self.charText:
            if char.strText:
                result += f'\t{char.strText}\n'

        result += "]\n\n"

        return result


class RecordStructureArea:
    class StructureInfo:
        def __init__(self, type, offset, id):
            self.filed_name = ''
            self.type = type
            self.offset = offset
            self.id = id

            self.type_str = "Unknown"
            if self.type == 0x05:
                self.type_str = "int32"
            elif self.type == 0x0F:
                self.type_str = "string"
            elif self.type == 0x0E:
                self.type_str = "id string"

        def fill_name(self, name):
            self.filed_name = name

        def __str__(self):
            return "{\n" + f"\tid: {self.id}\n" + f"\toffset: {self.offset}\n" \
                   + (f"\tfiled_name: {self.filed_name}\n" if self.filed_name else "") \
                   + f"\ttype: {self.type_str}\n" # \
                   # + f"\ttype_value: {self.type}\n" + "}\n"

    def __init__(self, data):
        self.data = data
        self.content_size = get4_bytes(data, 0x08)
        self.entry_count = get4_bytes(data, 0x10)
        self.version = get4_bytes(data, 0x14)

        self.desc_data_bytes = self.data[0x14:0x14 + self.entry_count * 12]

        data = BytesIO(self.desc_data_bytes)
        self.structure = []
        for i in range(self.entry_count):
            type = int.from_bytes(data.read(0x04), order)
            offset = int.from_bytes(data.read(0x04), order)
            id = int.from_bytes(data.read(0x04), order)
            self.structure.append(RecordStructureArea.StructureInfo(type, offset, id))

    def fill_structure_name(self, names):
        for s in self.structure:
            s.fill_name(names[str(s.id)])

    def __str__(self):
        result = "[\n"
        result += f"content_size: {self.content_size}\n"
        result += f"entry_count: {self.entry_count}\n"
        result += f"version: {self.version}\n\n"

        for entry in self.structure:
            result += entry.__str__()

        return result


class StrArea:
    MAGIC = b"GENESTRT"

    def __init__(self, data):
        self.data = data
        self.content_size = get4_bytes(data, 0x08)
        self.flag = get4_bytes(data, 0x10)
        self.version = get4_bytes(data, 0x14)
        self.point_table_size = get4_bytes(data, 0x18)
        self.content_size2 = get4_bytes(data, 0x1C)
        self.str_table = {}
        self.str_table_title = {}
        self.str_table_tail = {}
        self.parse_index_and_str()

    def parse_index_and_str(self):
        # STR area parse
        point_area_end_offset = 0x20 + (self.point_table_size - 0x10)
        str_point_area_bytes = self.data[0x20:point_area_end_offset]

        str_content_area_bytes = self.data[point_area_end_offset:]

        # Parse strings with index
        buffer = BytesIO(str_point_area_bytes)
        idx = 0
        while True:
            chunk = buffer.read(4)
            if not chunk:
                break

            point_v = int.from_bytes(chunk, order)
            if point_v != 0:
                end_pos = str_content_area_bytes.find(b'\x00', point_v)
                string_bytes = str_content_area_bytes[point_v:end_pos]
                string_data = string_bytes.decode('utf-8')
                if string_data:
                    self.str_table[str(idx)] = string_data
            else:
                self.str_table['0'] = "0"

            idx += 1

        # Parse table title and tail desc (will hold it in rebuild)
        self.str_table_title = OrderedDict(list(self.str_table.items())[1:55])
        self.str_table_tail = OrderedDict(list(self.str_table.items())[-38:])


if __name__ == "__main__":
    with open("gop_data/origin/gop_talkanagram.gop", "rb") as file:
        gop_data = file.read()

        # GDAT area parse
        gdata_start_offset = gop_data.find(b"GOP GDAT")
        gdata_bytes = gop_data[gdata_start_offset:]

        magic_size = 0x10
        magic = gdata_bytes[0x00:0x08]
        print("magic: " + magic.decode())

        area_size = get4_bytes(gdata_bytes, 0x08)
        print(f"area_size: {area_size} bytes")

        record_size = get4_bytes(gdata_bytes, 0x10)
        print(f"record_size: {record_size} bytes")

        game_count = get4_bytes(gdata_bytes, 0x14)
        print(f"game_count: {game_count}")

        version = get4_bytes(gdata_bytes, 0x18)
        print(f"version: {version}")

        data_pos = get4_bytes(gdata_bytes, 0x1C)
        print(f"data_pos: {data_pos}")

        print()

        # REC area
        rec_area_data = gop_data[gop_data.find(b"GOP GREC"):gop_data.find(b"GENESTRT")]
        rec_area = RecordStructureArea(rec_area_data)

        # STR area
        str_area_data = gop_data[gop_data.find(b"GENESTRT"):gdata_start_offset]
        str_area = StrArea(str_area_data)

        rec_area.fill_structure_name(str_area.str_table)
        print(rec_area)

        game_anagram = []
        for i in range(game_count):
            start_pos = (data_pos + magic_size) + i * record_size
            end_pos = start_pos + record_size
            per_game_data = gdata_bytes[start_pos:end_pos]
            anagram = Anagram(per_game_data, str_area.str_table)
            game_anagram.append(anagram)
            print(anagram)

        print()
