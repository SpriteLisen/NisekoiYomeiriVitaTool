from io import BytesIO

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
        for i in range(5):
            idx = self.read4_int()
            self.strAnswerIdx.append(idx)
            self.strAnswer.append('' if idx == 0 else str_table[str(idx)])

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

        result += "\nAnswer:\n"
        for answer in self.strAnswer:
            if answer:
                result += f'\t{answer}\n'

        result += "\nChar:\n"
        for char in self.charText:
            if char.strText:
                result += f'\t{char.strText}\n'

        result += "]\n\n"

        return result


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

        cols = get4_bytes(gdata_bytes, 0x18)
        print(f"cols: {cols}")

        data_pos = get4_bytes(gdata_bytes, 0x1C)
        print(f"data_pos: {data_pos}")

        print()

        # STR area parse
        str_area_start_offset = gop_data.find(b"GENESTRT") + 0x20
        str_content_start_offset = gop_data.find(b"SelfId") - 1

        str_point_area_bytes = gop_data[str_area_start_offset:str_content_start_offset]
        str_content_area_bytes = gop_data[str_content_start_offset:gdata_start_offset]
        str_table = {}

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
                    str_table[str(idx)] = string_data

            idx += 1

        game_anagram = []
        for i in range(game_count):
            start_pos = (data_pos + magic_size) + i * record_size
            end_pos = start_pos + record_size
            per_game_data = gdata_bytes[start_pos:end_pos]
            anagram = Anagram(per_game_data, str_table)
            game_anagram.append(anagram)
            print(anagram)

        print()
