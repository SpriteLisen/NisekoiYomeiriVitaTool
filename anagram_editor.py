import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk


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
        width = edit_window.winfo_width()
        height = edit_window.winfo_height()
        x = (edit_window.winfo_screenwidth() // 2) - (width // 2)
        y = (edit_window.winfo_screenheight() // 2) - (height // 2)
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

        # 列表标签
        list_label = tk.Label(
            left_frame, text=AnagramEditorApp.ANAGRAM_LIST_TITLE,
            font=(AnagramEditorApp.FONT_FAMILY, AnagramEditorApp.FUNCTION_FONT_SIZE),
            bg='#4a7a8c', fg='white', pady=5
        )
        list_label.pack(fill=tk.X)

        # 创建滚动条
        scrollbar = tk.Scrollbar(left_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 创建列表框
        self.list_box = tk.Listbox(
            left_frame, yscrollcommand=scrollbar.set,
            font=(AnagramEditorApp.FONT_FAMILY, 13),
            bg='white', fg='black', relief=tk.FLAT
        )
        self.list_box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 配置滚动条
        scrollbar.config(command=self.list_box.yview)

        # TODO 这里需要调整成读取出来的题目名称
        # 添加项目
        list_items = ["项目1", "项目2", "项目3", "项目4", "项目5"]
        for item in list_items:
            self.list_box.insert(tk.END, item)

        # 绑定点击事件
        self.list_box.bind('<<ListboxSelect>>', self.on_item_selected)

    def on_item_selected(self, event):
        if not self.list_box.curselection():
            return

        index = self.list_box.curselection()[0]
        item = self.list_box.get(index)

        # TODO 这里需要拿到 item index 然后获取全局的题目, 并更新 UI
        # self.status_label.config(text=f"选择: {item}")
        self.on_anagram_item_selected()


class ImageActionPanel:
    resource_dir = "resources/"
    bg_img_path = f"{resource_dir}bg.png"
    title_bg_img_path = f"{resource_dir}title_area_bg.png"

    def create_main_area(self):
        bg_img = Image.open(self.bg_img_path).convert("RGBA")
        title_bg_img = Image.open(self.title_bg_img_path).convert("RGBA")
        overlay = Image.new("RGBA", bg_img.size, (0, 0, 0, 0))
        overlay.paste(title_bg_img, (0, 15))
        main_img = Image.alpha_composite(bg_img, overlay)

        main_draw = ImageDraw.Draw(main_img)

        font = ImageFont.truetype(f"{self.resource_dir}WenQuanDengKuanWeiMiHei.ttf", 18)

        text_x = 30
        text_y = 44

        main_draw.text((text_x, text_y), self.title_text, fill='black', font=font, anchor='lm')

        self.main_img = ImageTk.PhotoImage(main_img)

    def redraw(self):
        self.create_main_area()
        self.image_label.config(image=self.main_img)
        self.image_label.image = self.main_img

    def __init__(self, root_window, main_frame):
        self.root_window = root_window
        self.main_frame = main_frame
        self.title_text = "点击编辑标题"

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

        self.image_label.bind('<Button-1>', self.on_main_img_click)

    def on_main_img_click(self, event):
        x, y = event.x, event.y

        # 点击标题区域
        if 0 <= x <= 400 and 18 <= y <= 68:
            self.show_title_edit_dialog()

    def show_title_edit_dialog(self):
        def on_text_changed(new_text):
            self.title_text = new_text

            self.redraw()

            print(f"标题已修改为: '{self.title_text}'")

        EditTextDialog(
            root_window=self.root_window,
            title="编辑标题",
            hint="编辑标题（最多16个字符）:",
            default_value=self.title_text,
            max_length=16,
            on_text_changed=on_text_changed
        )


class RightPanel:
    def __init__(self, root_window, main_frame):
        self.root_window = root_window
        self.main_frame = main_frame

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
        buttons = ["按钮1", "按钮2", "按钮3", "按钮4"]
        for text in buttons:
            btn = tk.Button(
                button_frame, text=text,
                font=(AnagramEditorApp.FONT_FAMILY, 13),
                bg='white', fg='black',
                borderwidth=0,
                highlightthickness=0,
                padx=10, pady=5,
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
            text="答案列表",
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
            height=8  # 显示8行
        )
        self.answer_listbox.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # TODO 这里需要动态从当前的题目答案进行构建填充
        # 示例答案数据
        sample_answers = [
            "答案1: 这是第一个答案",
            "答案2: 第二个测试答案",
            "答案3: 第三个示例答案",
            "答案4: 第四个可能答案",
            "答案5: 第五个备选答案",
            "答案6: 第六个正确答案",
            "答案7: 第七个候补答案",
            "答案8: 第八个最终答案",
            "答案9: 第九个额外答案",
            "答案10: 第十个补充答案"
        ]

        self.rebuild_data(sample_answers)

    def rebuild_data(self, data):
        # 清空列表并添加数据
        self.answer_listbox.delete(0, tk.END)
        for answer in data:
            self.answer_listbox.insert(tk.END, answer)

        # 绑定双击事件
        self.answer_listbox.bind('<Double-Button-1>', self.on_answer_double_click)

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
            # 删除原项目，插入新项目
            self.answer_listbox.delete(index)
            self.answer_listbox.insert(index, new_text)
            print(f"答案已修改为: '{new_text}'")

        EditTextDialog(
            root_window=self.root_window,
            title="编辑答案",
            hint="编辑答案（最多7个字符）:",
            max_length=7,
            default_value=original_text,
            on_text_changed=on_text_changed
        )


class AnagramEditorApp:
    TITLE = "字谜编辑器"

    ANAGRAM_LIST_TITLE = "字谜题集列表"
    EDIT_ACTION_TITLE = "编辑操作"

    FONT_FAMILY = "微软雅黑"

    FUNCTION_FONT_SIZE = 16

    PANEL_BG_COLOR = "#e8e8e8"

    IMAGE_WIDTH = 960
    IMAGE_HEIGHT = 540

    WINDOW_WIDTH = IMAGE_WIDTH + 460  # 960 + 200 + 260
    WINDOW_HEIGHT = IMAGE_HEIGHT + 40  # # 540 + 上下边距

    def __init__(self):
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
        self.image_action_panel = ImageActionPanel(self.root, self.main_frame)
        self.right_panel = RightPanel(self.root, self.main_frame)

        self.root.mainloop()

    def center_window(self, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def on_anagram_item_selected(self):
        pass


def main():
    AnagramEditorApp()


if __name__ == "__main__":
    main()
