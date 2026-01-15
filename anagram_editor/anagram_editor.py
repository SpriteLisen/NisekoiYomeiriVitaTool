import os
import csv
import json
import locale
import platform
import subprocess
import tkinter as tk
from io import BytesIO
from tkinter import ttk
from pathlib import Path
from collections import OrderedDict
from PIL import Image, ImageDraw, ImageFont, ImageTk

lang_table: dict = {}

lang_dir = "lang/"
lang = "en.json"

try:
    language, _ = locale.getdefaultlocale()
    # lang = "zh.json" if language is not None and language.lower().startswith('zh') else "en.json"

    with open(lang_dir + lang, 'r', encoding='utf-8') as f:
        lang_table = json.load(f)
except Exception as e:
    with open(lang_dir + "en.json", 'r', encoding='utf-8') as f:
        lang_table = json.load(f)

app_log = None

order = "little"

output_dir = "export/"

output_file_name = "gop_talkanagram.gop"
output_csv_name = "anagram.csv"
output_file = output_dir + output_file_name
output_csv_file = output_dir + output_csv_name

Path(output_dir).mkdir(parents=True, exist_ok=True)


def get4_bytes(data, start):
    return int.from_bytes(data[start: start + 0x04], order)


def align_to_16_bytes(data):
    remainder = len(data) % 16
    if remainder != 0:
        padding = 16 - remainder
        data.extend(b'\x00' * padding)
    return data


class Anagram:
    MAX_CHAR_SIZE = 15

    class CharText:
        DEFAULT_CHAR = lang_table["default_char_value"][:1]

        def read4_int(self):
            return int.from_bytes(self.data.read(0x04), order)

        def __init__(self, data=None, str_table=None):
            if not data and not str_table:
                self.iPosX = 0
                self.iPosY = 0
                self.strTextIdx = 0
                self.strText = ''
            else:
                self.data = data

                self.iPosX = self.read4_int()
                self.iPosY = self.read4_int()
                self.strTextIdx = self.read4_int()
                self.strText = '' if self.strTextIdx == 0 else str_table[str(self.strTextIdx)]

        def is_empty(self):
            return self.iPosX == 0 and self.iPosY == 0 and self.strText == ''

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

        self.charText: list[Anagram.CharText] = []
        for i in range(15):
            self.charText.append(Anagram.CharText(self.data, str_table))

    def read4_int(self):
        return int.from_bytes(self.data.read(0x04), order)


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


now_edit_index = 0

game_anagram: list[Anagram] = []

pre_data: bytearray = None
gdata_bytes: bytearray = None
str_area: StrArea = None


def parse_meta_info():
    with open("resources/anagram.gop", "rb") as file:
        gop_data = file.read()

        global pre_data
        pre_data = gop_data[:gop_data.find(b"GENESTRT")]

        # GDAT area parse
        gdata_start_offset = gop_data.find(b"GOP GDAT")
        global gdata_bytes
        gdata_bytes = gop_data[gdata_start_offset:]

        magic_size = 0x10

        record_size = get4_bytes(gdata_bytes, 0x10)

        game_count = get4_bytes(gdata_bytes, 0x14)
        app_log(lang_table["log_anagram_count"].format(game_count))

        data_pos = get4_bytes(gdata_bytes, 0x1C)

        # STR area
        str_area_data = gop_data[gop_data.find(b"GENESTRT"):gdata_start_offset]

        global str_area
        str_area = StrArea(str_area_data)

        for i in range(game_count):
            start_pos = (data_pos + magic_size) + i * record_size
            end_pos = start_pos + record_size
            per_game_data = gdata_bytes[start_pos:end_pos]
            anagram = Anagram(per_game_data, str_area.str_table)
            game_anagram.append(anagram)

        app_log(lang_table["log_decode_anagram_success"])

    if os.path.exists(output_csv_file):
        with open(output_csv_file, 'r', newline='', encoding='utf-8-sig') as csv_file:
            csv_reader = csv.DictReader(csv_file)

            for i, row in enumerate(csv_reader):
                anagram_entry = game_anagram[i]
                anagram_entry.SelfId = int(row['SelfId'])
                anagram_entry.iQuestId = int(row['iQuestId'])
                anagram_entry.iLimitMSec = int(row['iLimitMSec'])
                anagram_entry.strTitle = row['strTitle']
                if len(anagram_entry.strTitle) > 13:
                    print(anagram_entry.strTitle)

                for j in range(5):
                    anagram_entry.strAnswer[j] = row[f"strAnswer{j:02d}"]

                for j in range(15):
                    char_entry = anagram_entry.charText[j]
                    char_entry.iPosX = int(row[f"iPosX{j:02d}"])
                    char_entry.iPosY = int(row[f"iPosY{j:02d}"])
                    char_entry.strText = row[f"strText{j:02d}"]

        app_log(lang_table["log_restore_last_edit_success"])


def export_product(root_window):
    csv_file = open(output_csv_file, 'w', newline='', encoding='utf-8-sig')
    csv_writer = csv.writer(csv_file)

    offset_data = []
    string_data = b""

    string_data += b'\x00'
    offset_data.append(0)

    # encode table header
    csv_writer.writerow(str_area.str_table_title.values())
    for v in str_area.str_table_title.values():
        offset_data.append(len(string_data))
        string_data += v.encode('utf-8') + b'\x00'

    entry_bytes = bytearray()

    # encode anagram data
    for i in range(len(game_anagram)):
        anagram_data_list = []

        offset_data.append(len(string_data))
        string_data += f"R_TalkAnagram{i:03d}".encode('utf-8') + b'\x00'

        anagram_entry = game_anagram[i]

        # SelfId, iQuestId, iLimitMSec
        anagram_data_list.append(anagram_entry.SelfId)
        anagram_data_list.append(anagram_entry.iQuestId)
        anagram_data_list.append(anagram_entry.iLimitMSec)
        entry_bytes.extend(anagram_entry.SelfId.to_bytes(4, order))
        entry_bytes.extend(anagram_entry.iQuestId.to_bytes(4, order))
        entry_bytes.extend(anagram_entry.iLimitMSec.to_bytes(4, order))

        # Title
        anagram_entry.strTitleIdx = len(offset_data)
        entry_bytes.extend(anagram_entry.strTitleIdx.to_bytes(4, order))
        offset_data.append(len(string_data))
        string_data += anagram_entry.strTitle.encode('utf-8') + b'\x00'
        anagram_data_list.append(anagram_entry.strTitle)

        # 5 answer
        for j in range(5):
            answer_str = anagram_entry.strAnswer[j]
            anagram_data_list.append(answer_str)
            if answer_str:
                anagram_entry.strAnswerIdx[j] = len(offset_data)
                entry_bytes.extend(anagram_entry.strAnswerIdx[j].to_bytes(4, order))
                offset_data.append(len(string_data))
                string_data += answer_str.encode('utf-8') + b'\x00'
            else:
                entry_bytes.extend(int("0").to_bytes(4, order))

        # 15 char entry
        for j in range(15):
            char_entry = anagram_entry.charText[j]
            anagram_data_list.append(char_entry.iPosX)
            anagram_data_list.append(char_entry.iPosY)
            anagram_data_list.append(char_entry.strText)
            if not char_entry.is_empty():
                char_entry.strTextIdx = len(offset_data)
                offset_data.append(len(string_data))
                string_data += char_entry.strText.encode('utf-8') + b'\x00'
                entry_bytes.extend(char_entry.iPosX.to_bytes(4, order))
                entry_bytes.extend(char_entry.iPosY.to_bytes(4, order))
                entry_bytes.extend(char_entry.strTextIdx.to_bytes(4, order))
            else:
                entry_bytes.extend(int("0").to_bytes(4, order))
                entry_bytes.extend(int("0").to_bytes(4, order))
                entry_bytes.extend(int("0").to_bytes(4, order))

        csv_writer.writerow(anagram_data_list)

    # encode table tail
    for v in str_area.str_table_tail.values():
        offset_data.append(len(string_data))
        string_data += v.encode('utf-8') + b'\x00'

    str_index_bytes = bytearray()
    for offset in offset_data:
        str_index_bytes.extend(offset.to_bytes(4, order))
    str_index_bytes = align_to_16_bytes(str_index_bytes)

    string_data = align_to_16_bytes(bytearray(string_data))

    # Build str area data
    string_area_bytes = bytearray()
    string_area_bytes.extend(b"GENESTRT")
    content_data_size = len(str_index_bytes) + len(string_data) + 0x10
    string_area_bytes.extend(content_data_size.to_bytes(8, order))
    string_area_bytes.extend((len(offset_data) - 1).to_bytes(4, order))
    string_area_bytes.extend(0x10.to_bytes(4, order))
    string_area_bytes.extend((len(str_index_bytes) + 0x10).to_bytes(4, order))
    string_area_bytes.extend(content_data_size.to_bytes(4, order))

    string_area_bytes.extend(str_index_bytes)
    string_area_bytes.extend(string_data)

    # Override gdata
    new_gdata_bytes = bytearray(gdata_bytes)
    new_gdata_bytes[0x90:0x15A8] = entry_bytes

    with open(output_file, "wb") as f:
        f.write(pre_data)
        f.write(string_area_bytes)
        f.write(new_gdata_bytes)

    csv_file.close()

    hint = lang_table["export_product_success_hint"].format(output_file_name)
    app_log(hint)
    AlertDialog(
        root_window, hint
    )


class AlertDialog:
    def __init__(
            self, root_window, hint: str, title: str = "提示",
            confirm_btn_text="知道了",
            width=320  # 只传宽度，高度自动计算
    ):
        alert_window = tk.Toplevel(root_window)
        alert_window.title(title)

        # 不要设置固定高度，让窗口自动调整
        alert_window.geometry(f"{width}x1")  # 初始高度设为1，后面会自动调整

        alert_window.resizable(False, True)  # 宽度固定，高度可调整（为了自动计算）
        alert_window.transient(root_window)
        alert_window.grab_set()

        # 主容器，用于添加间距
        main_frame = tk.Frame(alert_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)  # 四周留白

        # 文本标签，设置自动换行
        text_label = tk.Label(
            main_frame,
            text=hint,
            font=(AnagramEditorApp.FONT_FAMILY, 11),
            wraplength=width - 50,  # 设置换行长度，比窗口宽度小一些
            justify=tk.LEFT,  # 左对齐
            anchor="w"  # 文本左对齐
        )
        text_label.pack(fill=tk.X, pady=(0, 15))  # 下方留白

        # 按钮框架
        button_frame = tk.Frame(main_frame)
        button_frame.pack()

        save_btn = tk.Button(
            button_frame,
            text=confirm_btn_text,
            command=alert_window.destroy,
            width=10
        )
        save_btn.pack()

        # 更新窗口，让tkinter计算实际需要的尺寸
        alert_window.update_idletasks()

        # 获取实际需要的高度
        req_height = main_frame.winfo_reqheight() + 40  # 加上窗口边框和标题栏的高度

        # 居中显示
        parent_x = root_window.winfo_rootx()
        parent_y = root_window.winfo_rooty()
        parent_width = root_window.winfo_width()
        parent_height = root_window.winfo_height()

        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - req_height) // 2

        # 设置最终尺寸
        alert_window.geometry(f"{width}x{req_height}+{x}+{y}")

        # 禁止调整高度（现在高度已经计算好了）
        alert_window.resizable(False, False)

        # 设置焦点
        alert_window.focus_force()
        save_btn.focus_set()


class EditTextDialog:
    def __init__(
            self, root_window, title: str, hint: str,
            default_value: str, max_length: int,
            on_text_changed,
            save_btn_text="保存", cancel_btn_text="取消",
            size="320x140"
    ):
        edit_window = tk.Toplevel(root_window)
        edit_window.title(title)
        edit_window.geometry(size)
        edit_window.resizable(False, False)

        edit_window.transient(root_window)
        edit_window.grab_set()
        edit_window.attributes('-topmost', True)
        edit_window.bind('<Escape>', lambda e: edit_window.destroy())

        edit_window.update_idletasks()

        parent_x = root_window.winfo_rootx()
        parent_y = root_window.winfo_rooty()
        parent_width = root_window.winfo_width()
        parent_height = root_window.winfo_height()

        width = edit_window.winfo_width()
        height = edit_window.winfo_height()

        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2

        edit_window.geometry(f'{width}x{height}+{x}+{y}')

        edit_window.focus_force()

        tk.Label(
            edit_window, text=hint,
            font=(AnagramEditorApp.FONT_FAMILY, 11)
        ).pack(pady=10)

        entry_var = tk.StringVar(value=default_value)

        def on_text_change(*args):
            text = entry_var.get()
            if len(text) > max_length:
                entry_var.set(text[:max_length])

        entry_var.trace('w', on_text_change)

        entry = tk.Entry(
            edit_window,
            textvariable=entry_var,
            font=(AnagramEditorApp.FONT_FAMILY, 14),
            width=25
        )
        entry.pack(pady=5)

        entry.focus_set()
        entry.select_range(0, tk.END)

        button_frame = tk.Frame(edit_window)
        button_frame.pack(pady=10)

        def save_action():
            new_text = entry_var.get().strip()

            if not new_text:
                edit_window.destroy()
                return

            if new_text == default_value:
                edit_window.destroy()
                return

            on_text_changed(new_text)

            edit_window.destroy()

        def cancel_edit():
            edit_window.destroy()

        save_btn = tk.Button(
            button_frame,
            text=save_btn_text,
            command=save_action,
            width=10
        )
        save_btn.pack(side=tk.LEFT, padx=5)

        cancel_btn = tk.Button(
            button_frame,
            text=cancel_btn_text,
            command=cancel_edit,
            width=10
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)

        entry.bind('<Return>', lambda e: save_action())
        edit_window.bind('<Escape>', lambda e: cancel_edit())

        on_text_change()


class LeftPanel:
    def __init__(self, root_window, main_frame, on_anagram_item_selected):
        self.root_window = root_window
        self.main_frame = main_frame
        self.on_anagram_item_selected = on_anagram_item_selected

        left_frame = tk.Frame(
            self.main_frame, width=200, bg=AnagramEditorApp.PANEL_BG_COLOR,
            relief=tk.RAISED, borderwidth=1
        )
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        left_frame.pack_propagate(False)

        # 列表标签
        list_label = tk.Label(
            left_frame, text=AnagramEditorApp.ANAGRAM_LIST_TITLE,
            font=(AnagramEditorApp.FONT_FAMILY, AnagramEditorApp.FUNCTION_FONT_SIZE),
            bg='#4a7a8c', fg='white', pady=5
        )
        list_label.pack(fill=tk.X)

        # 创建主内容框架（上面是列表，下面是日志）
        content_frame = tk.Frame(left_frame, bg='white')
        content_frame.pack(fill=tk.BOTH, expand=True)

        # 上部：列表区域（占60%高度）
        list_container = tk.Frame(content_frame, bg='white')
        list_container.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # 创建滚动条
        scrollbar = tk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 创建列表框
        self.list_box = tk.Listbox(
            list_container, yscrollcommand=scrollbar.set,
            font=(AnagramEditorApp.FONT_FAMILY, 13),
            bg='white', fg='black', relief=tk.FLAT,
            exportselection=False  # 失去焦点时保持选择
        )
        self.list_box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 配置滚动条
        scrollbar.config(command=self.list_box.yview)

        # 绑定点击事件
        self.list_box.bind('<<ListboxSelect>>', self.on_item_selected)

        # 分隔线
        separator = tk.Frame(content_frame, height=2, bg='#cccccc')
        separator.pack(fill=tk.X, pady=5)

        # 下部：日志区域（占40%高度）
        log_container = tk.Frame(content_frame, bg='white')
        log_container.pack(fill=tk.BOTH, expand=True)

        # 日志标题
        log_label = tk.Label(
            log_container, text=lang_table["log_title"],
            font=(AnagramEditorApp.FONT_FAMILY, 11, 'bold'),
            bg='#4a7a8c', fg='white', pady=3
        )
        log_label.pack(fill=tk.X)

        # 创建日志文本框
        log_frame = tk.Frame(log_container, bg='white')
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 日志滚动条
        log_scrollbar = tk.Scrollbar(log_frame)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 日志文本框
        self.log_text = tk.Text(
            log_frame,
            height=8,  # 固定高度
            font=(AnagramEditorApp.FONT_FAMILY, 10),
            bg='#f5f5f5',
            fg='#333333',
            relief=tk.FLAT,
            wrap=tk.WORD,  # 自动换行
            yscrollcommand=log_scrollbar.set,
            state='disabled'  # 初始为只读
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 配置滚动条
        log_scrollbar.config(command=self.log_text.yview)

    def fill_list_data(self):
        for item in range(len(game_anagram)):
            self.list_box.insert(tk.END, f'字谜 {item + 1:02d}')

        # 默认选中第0项
        self.list_box.selection_set(0)
        self.list_box.activate(0)  # 激活第0项
        self.last_selected_index = 0

    def on_item_selected(self, event):
        selection = self.list_box.curselection()
        current_index = selection[0]
        if not selection or current_index == self.last_selected_index:
            return

        self.last_selected_index = current_index
        index = self.list_box.curselection()[0]
        item = self.list_box.get(index)

        self.on_anagram_item_selected(index, item)

    def log(self, message):
        """添加日志消息"""
        import datetime

        # 获取当前时间
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        # 启用编辑，添加消息，然后禁用
        self.log_text.config(state='normal')

        # 插入带时间戳的消息
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")

        # 自动滚动到最后
        self.log_text.see(tk.END)

        # 恢复只读状态
        self.log_text.config(state='disabled')

        # 确保界面更新
        self.log_text.update_idletasks()


class ImageActionPanel:
    resource_dir = "resources/"
    bg_img_path = f"{resource_dir}bg.png"
    title_bg_img_path = f"{resource_dir}title_area_bg.png"
    char_bg_img_path = f"{resource_dir}char_bg.png"

    char_bg_half_width = 45

    min_x = 45
    min_y = 100
    max_x = 915
    max_y = 495

    class BubbleEntry:
        def __init__(self, x, y):
            self.min_x = x
            self.max_x = x + ImageActionPanel.char_bg_half_width * 2
            self.min_y = y
            self.max_y = y + ImageActionPanel.char_bg_half_width * 2

        def is_hit(self, x, y):
            return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y

    def create_main_area(self):
        bg_img = Image.open(self.bg_img_path).convert("RGBA")

        main_img = Image.new("RGBA", bg_img.size, (0, 0, 0, 0))

        main_img.paste(bg_img, (0, 0))

        title_bg_img = Image.open(self.title_bg_img_path).convert("RGBA")
        main_img.paste(title_bg_img, (0, 15), title_bg_img)

        main_draw = ImageDraw.Draw(main_img)

        font = ImageFont.truetype(f"{self.resource_dir}WenQuanDengKuanWeiMiHei.ttf", 18)
        text_x = 30
        text_y = 44
        main_draw.text((text_x, text_y), self.title_text, fill='black', font=font, anchor='lm')

        char_bg_img = Image.open(self.char_bg_img_path).convert("RGBA")
        self.bubble_entry = []

        if game_anagram:
            char_font = ImageFont.truetype(f"{self.resource_dir}WenQuanDengKuanWeiMiHei.ttf", 38)

            for char_entry in game_anagram[now_edit_index].charText:
                if not char_entry.is_empty():
                    show_x = char_entry.iPosX - self.char_bg_half_width
                    show_y = char_entry.iPosY - self.char_bg_half_width

                    self.bubble_entry.append(
                        ImageActionPanel.BubbleEntry(show_x, show_y)
                    )

                    main_img.paste(
                        char_bg_img,
                        (show_x, show_y),
                        char_bg_img
                    )

                    char_x = char_entry.iPosX
                    char_y = char_entry.iPosY
                    main_draw.text(
                        (char_x, char_y), char_entry.strText,
                        fill='#555555', font=char_font, anchor='mm'
                    )

        self.main_img = ImageTk.PhotoImage(main_img)

    def redraw(self):
        self.create_main_area()
        self.image_label.config(image=self.main_img)
        self.image_label.image = self.main_img

    def __init__(self, root_window, main_frame, on_title_changed):
        self.root_window = root_window
        self.main_frame = main_frame
        self.title_text = ""
        self.on_title_changed = on_title_changed

        self.image_frame = tk.Frame(
            main_frame, width=AnagramEditorApp.IMAGE_WIDTH,
            height=AnagramEditorApp.IMAGE_HEIGHT, bg='white',
            relief=tk.SUNKEN, borderwidth=2
        )
        self.image_frame.pack(side=tk.LEFT, padx=(0, 10))

        self.create_main_area()

        # Add main img
        self.image_label = tk.Label(self.image_frame, image=self.main_img, bg='white')
        self.image_label.pack(fill=tk.BOTH, expand=True)

        self.delete_char_menu = tk.Menu(self.root_window, tearoff=0)
        self.delete_char_menu.add_command(
            label="删除该字",
            command=self.on_delete_char
        )

        self.add_char_menu = tk.Menu(self.root_window, tearoff=0)
        self.add_char_menu.add_command(
            label="增加字符",
            command=self.on_add_char
        )

        self.image_label.bind('<Button-1>', self.on_main_img_click)
        self.image_label.bind('<B1-Motion>', self.on_mouse_drag)
        self.image_label.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.image_label.bind('<Button-3>', self.on_right_click)
        self.image_label.bind('<Button-2>', self.on_right_click)  # macOS mouse right click use Magic Trackpad
        self.image_label.bind('<Double-Button-1>', self.on_double_click)

    def refresh_now_anagram_ui(self):
        self.title_text = game_anagram[now_edit_index].strTitle

        self.redraw()

    def on_main_img_click(self, event):
        x, y = event.x, event.y

        # 点击标题区域
        if 0 <= x <= 400 and 18 <= y <= 68:
            self.show_title_edit_dialog()
        else:
            for i in range(len(self.bubble_entry)):
                if self.bubble_entry[i].is_hit(x, y):
                    self.dragging = True
                    self.dragging_index = i
                    self.dragging_entry = self.bubble_entry[i]
                    self.drag_start_x = x
                    self.drag_start_y = y

    def on_mouse_drag(self, event):
        if self.dragging and self.dragging_entry:
            offset_x = self.drag_start_x - event.x
            offset_y = self.drag_start_y - event.y

            dragging_item = game_anagram[now_edit_index].charText[self.dragging_index]

            new_x = dragging_item.iPosX - offset_x
            new_y = dragging_item.iPosY - offset_y

            new_x = max(ImageActionPanel.min_x, min(new_x, ImageActionPanel.max_x))
            new_y = max(ImageActionPanel.min_y, min(new_y, ImageActionPanel.max_y))

            dragging_item.iPosX = new_x
            dragging_item.iPosY = new_y

            self.drag_start_x = dragging_item.iPosX
            self.drag_start_y = dragging_item.iPosY

            self.redraw()

    def on_mouse_up(self, event):
        self.dragging = False
        self.dragging_index = None
        self.dragging_entry = None
        self.drag_start_x = None
        self.drag_start_y = None

    def on_right_click(self, event):
        x, y = event.x, event.y

        hit_index = -1
        for i in range(len(self.bubble_entry)):
            if self.bubble_entry[i].is_hit(x, y):
                hit_index = i
                break

        if hit_index >= 0:
            self.right_click_index = hit_index
            self.delete_char_menu.post(event.x_root, event.y_root)
        else:
            self.right_click_index = -1

            if (ImageActionPanel.min_x - ImageActionPanel.char_bg_half_width <= x
                    <= ImageActionPanel.max_x + ImageActionPanel.char_bg_half_width
                    and ImageActionPanel.min_y - ImageActionPanel.char_bg_half_width <= y
                    <= ImageActionPanel.max_y + ImageActionPanel.char_bg_half_width):
                self.right_click_x = x + ImageActionPanel.char_bg_half_width
                self.right_click_y = y + ImageActionPanel.char_bg_half_width
                self.add_char_menu.post(event.x_root, event.y_root)

    def on_delete_char(self):
        if self.right_click_index >= 0:
            answer_length = len(game_anagram[now_edit_index].strAnswer[0])

            answer_count = 0
            for answer in game_anagram[now_edit_index].strAnswer:
                if answer:
                    answer_count += 1

            char_count = 0
            for char in game_anagram[now_edit_index].charText:
                if not char.is_empty():
                    char_count += 1

            if char_count <= answer_count:
                hint = lang_table["delete_char_less_answer_count_hint"]
                app_log(hint)
                AlertDialog(
                    self.root_window,
                    hint=hint
                )
                return

            if char_count <= answer_length:
                hint = lang_table["delete_char_less_answer_length_hint"]
                app_log(hint)
                AlertDialog(
                    self.root_window,
                    hint=hint
                )
                return

            # 移除该字符, 将后面的字符前移
            remove_char = game_anagram[now_edit_index].charText[self.right_click_index].strText
            char_list = game_anagram[now_edit_index].charText
            original_length = len(char_list)

            for i in range(self.right_click_index, original_length - 1):
                char_list[i] = char_list[i + 1]

            char_list[original_length - 1] = Anagram.CharText()

            app_log(
                lang_table["log_delete_char_success"].format(f"{now_edit_index + 1:02d}", remove_char)
            )

            self.redraw()

            self.right_click_index = -1

    def on_add_char(self):
        char_count = 0
        for char in game_anagram[now_edit_index].charText:
            if not char.is_empty():
                char_count += 1

        if char_count >= Anagram.MAX_CHAR_SIZE:
            hint = lang_table["add_char_to_more_hint"]
            app_log(hint)
            AlertDialog(
                self.root_window,
                hint=hint
            )
            return

        char_entry = game_anagram[now_edit_index].charText[char_count]
        char_entry.iPosX = self.right_click_x
        char_entry.iPosY = self.right_click_y
        char_entry.strText = Anagram.CharText.DEFAULT_CHAR

        app_log(
            lang_table["log_add_char_success"].format(f"{now_edit_index + 1:02d}", Anagram.CharText.DEFAULT_CHAR)
        )

        self.redraw()

    def show_title_edit_dialog(self):
        def on_text_changed(new_text):
            self.title_text = new_text

            self.on_title_changed(self.title_text)
            self.redraw()

        EditTextDialog(
            root_window=self.root_window,
            title="编辑标题",
            hint="编辑标题（最多16个字符）:",
            default_value=self.title_text,
            max_length=16,
            on_text_changed=on_text_changed
        )

    def on_double_click(self, event):
        x, y = event.x, event.y

        for i in range(len(self.bubble_entry)):
            if self.bubble_entry[i].is_hit(x, y):
                self.show_char_edit_dialog(
                    game_anagram[now_edit_index].charText[i]
                )

    def show_char_edit_dialog(self, bubble):
        def on_text_changed(new_text):
            app_log(
                lang_table["log_change_char_success"].format(f"{now_edit_index + 1:02d}", bubble.strText, new_text)
            )
            bubble.strText = new_text
            self.redraw()

        EditTextDialog(
            root_window=self.root_window,
            title="编辑字符",
            hint="编辑字符（最多1个字符）:",
            default_value=bubble.strText,
            max_length=1,
            on_text_changed=on_text_changed
        )


class RightPanel:
    def __init__(self, root_window, main_frame, on_answer_changed):
        self.root_window = root_window
        self.main_frame = main_frame
        self.on_answer_changed = on_answer_changed

        right_frame = tk.Frame(
            self.main_frame, width=260,
            bg=AnagramEditorApp.PANEL_BG_COLOR,
            relief=tk.RAISED, borderwidth=1
        )
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        right_frame.pack_propagate(False)

        # 按钮面板
        panel_label = tk.Label(
            right_frame, text=AnagramEditorApp.EDIT_ACTION_TITLE,
            font=(AnagramEditorApp.FONT_FAMILY, AnagramEditorApp.FUNCTION_FONT_SIZE),
            bg='#8a4a7a', fg='white', pady=5
        )
        panel_label.pack(fill=tk.X)

        # 按钮框架
        button_frame = tk.Frame(right_frame, bg='white')
        button_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 创建按钮
        buttons = [
            (lang_table["save_change_button"], self.on_click_save),
            (lang_table["open_product_button"], self.on_click_open_product),
            (lang_table["about_program_button"], self.on_click_open_product)
        ]
        for text, command in buttons:
            btn = tk.Button(
                button_frame, text=text,
                font=(AnagramEditorApp.FONT_FAMILY, 13),
                bg='white', fg='black',
                borderwidth=0,
                highlightthickness=0,
                highlightbackground="white",
                padx=10, pady=5,
                command=command
            )
            btn.pack(fill=tk.X, pady=5)

        # 添加答案列表区域（在下半区）
        self.create_answer_list_section(right_frame)

    def create_answer_list_section(self, parent_frame):
        # 分隔线
        separator = ttk.Separator(parent_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=(10, 5))

        # 答案列表标题
        answer_title = tk.Label(
            parent_frame,
            text=lang_table["answer_list_title"],
            font=(AnagramEditorApp.FONT_FAMILY, 15, 'bold'),
            bg=AnagramEditorApp.PANEL_BG_COLOR,
            fg='#2c3e50',
            pady=5
        )
        answer_title.pack(fill=tk.X)

        # 答案列表容器框架
        answer_container = tk.Frame(
            parent_frame,
            bg='white',
            relief=tk.SUNKEN,
            borderwidth=1
        )
        answer_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # 答案列表框
        self.answer_listbox = tk.Listbox(
            answer_container,
            # yscrollcommand=answer_scrollbar.set,
            font=(AnagramEditorApp.FONT_FAMILY, 13),
            bg='white',
            fg='black',
            relief=tk.FLAT,
        )
        self.answer_listbox.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    def rebuild_data(self, data):
        # 清空列表并添加数据
        self.answer_listbox.delete(0, tk.END)
        for answer in data:
            if answer:
                self.answer_listbox.insert(tk.END, answer)

        # 绑定双击事件
        self.answer_listbox.bind('<Double-Button-1>', self.on_answer_double_click)

    def refresh_now_anagram_ui(self):
        self.rebuild_data(game_anagram[now_edit_index].strAnswer)

    def on_answer_double_click(self, event):
        # 获取点击的索引
        index = self.answer_listbox.nearest(event.y)
        if index < 0:
            return

        # 获取原始文本
        original_text = self.answer_listbox.get(index)

        # 创建编辑窗口
        self.show_answer_edit_dialog(index, original_text)

    def show_answer_edit_dialog(self, index, original_text):
        """显示答案编辑对话框"""

        def on_text_changed(new_text):
            if self.on_answer_changed(index, new_text):
                # 删除原项目，插入新项目
                self.answer_listbox.delete(index)
                self.answer_listbox.insert(index, new_text)

        EditTextDialog(
            root_window=self.root_window,
            title=lang_table["edit_answer_dialog_title"],
            hint=lang_table["edit_answer_dialog_hint"],
            max_length=7,
            default_value=original_text,
            on_text_changed=on_text_changed
        )

    def on_click_save(self):
        export_product(self.root_window)

    def on_click_open_product(self):
        system_platform = platform.system()

        if system_platform == "Windows":
            os.startfile(Path(output_dir).resolve())
        elif system_platform == "Darwin":
            subprocess.run(["open", output_dir], check=True)
        else:
            subprocess.run(["xdg-open", output_dir], check=True)

        app_log(lang_table["log_open_product_success"])

    def on_click_about(self):
        pass


class AnagramEditorApp:
    TITLE = lang_table["window_title"]

    ANAGRAM_LIST_TITLE = lang_table["anagram_list_title"]
    EDIT_ACTION_TITLE = lang_table["button_title"]

    FONT_FAMILY = "微软雅黑"

    FUNCTION_FONT_SIZE = 16

    PANEL_BG_COLOR = "#e8e8e8"

    IMAGE_WIDTH = 960
    IMAGE_HEIGHT = 540

    WINDOW_WIDTH = IMAGE_WIDTH + 460  # 960 + 200 + 260
    WINDOW_HEIGHT = IMAGE_HEIGHT + 40  # # 540 + 上下边距

    def __init__(self):
        self.is_changed = False
        self.root = tk.Tk()
        self.root.title(self.TITLE)

        self.root.resizable(False, False)

        self.center_window(
            AnagramEditorApp.WINDOW_WIDTH,
            AnagramEditorApp.WINDOW_HEIGHT
        )

        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.left_panel = LeftPanel(
            root_window=self.root,
            main_frame=self.main_frame,
            on_anagram_item_selected=self.on_anagram_item_selected
        )
        self.image_action_panel = ImageActionPanel(self.root, self.main_frame, self.on_title_changed)
        self.right_panel = RightPanel(self.root, self.main_frame, self.on_answer_changed)

        global app_log
        app_log = self.log

        app_log(lang_table["log_app_start"])

        parse_meta_info()

        self.left_panel.fill_list_data()

        app_log(
            lang_table["log_load_default_data_success"].format(f"{now_edit_index + 1:02d}")
        )
        self.refresh_now_anagram_ui()

        self.root.mainloop()

    def refresh_now_anagram_ui(self):
        self.image_action_panel.refresh_now_anagram_ui()
        self.right_panel.refresh_now_anagram_ui()

    def center_window(self, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def on_anagram_item_selected(self, index, item):
        app_log(lang_table["log_change_anagram_item"].format(f"{index + 1:02d}"))

        global now_edit_index
        now_edit_index = index

        self.refresh_now_anagram_ui()

    def on_title_changed(self, text):
        game_anagram[now_edit_index].strTitle = text
        app_log(
            lang_table["log_anagram_title_changed"].format(f"{now_edit_index + 1:02d}", text)
        )

        self.is_changed = True

    def on_answer_changed(self, index, text):
        def modify_answer():
            game_anagram[now_edit_index].strAnswer[index] = text
            app_log(
                lang_table["log_anagram_answer_changed"].format(f"{now_edit_index + 1:02d}", f"{index + 1}", text)
            )

            self.is_changed = True

        if index == 0:
            is_modified_other = False
            for i in range(len(game_anagram[now_edit_index].strAnswer)):
                if i != 0:
                    if len(game_anagram[now_edit_index].strAnswer[i]) > len(text):
                        game_anagram[now_edit_index].strAnswer[i] = game_anagram[now_edit_index] \
                                                                        .strAnswer[i][:len(text)]
                        is_modified_other = True

            if not is_modified_other:
                modify_answer()
            else:
                modify_answer()
                self.right_panel.refresh_now_anagram_ui()

                hint = lang_table["other_answer_length_less_first_answer_hint"]

                app_log(hint)

                AlertDialog(
                    root_window=self.root,
                    hint=hint
                )
            return True
        else:
            max_length = len(game_anagram[now_edit_index].strAnswer[0])
            if len(text) > max_length:
                hint = lang_table["reject_other_answer_length_over_first_answer_hint"].format(max_length)
                app_log(hint)

                AlertDialog(self.root, hint=hint)
                return False
            else:
                modify_answer()
                return True

    def log(self, msg):
        self.left_panel.log(msg)


def main():
    AnagramEditorApp()


if __name__ == "__main__":
    main()
