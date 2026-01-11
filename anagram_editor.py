import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


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

        # 左侧：List列表区域
        self.create_left_panel()

        # 中间：图片展示区域
        self.create_image_panel()

        # 右侧：按钮面板
        self.create_right_panel()

        self.root.mainloop()

    def center_window(self, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def create_left_panel(self):
        # 左侧框架
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

        # 添加项目
        list_items = ["项目1", "项目2", "项目3", "项目4", "项目5"]
        for item in list_items:
            self.list_box.insert(tk.END, item)

        # 绑定点击事件
        self.list_box.bind('<<ListboxSelect>>', self.on_list_select)

    def create_image_panel(self):
        # 图片展示框架
        image_frame = tk.Frame(self.main_frame, width=self.IMAGE_WIDTH,
                               height=self.IMAGE_HEIGHT, bg='white',
                               relief=tk.SUNKEN, borderwidth=2)
        image_frame.pack(side=tk.LEFT, padx=(0, 10))

        # Add bg img
        self.image_label = tk.Label(image_frame, bg='white')
        self.image_label.pack(fill=tk.BOTH, expand=True)
        self.bg_img = tk.PhotoImage(file="resources/bg.png")
        self.image_label.config(
            image=self.bg_img,
            text=""
        )

        self.create_title_edit_area(image_frame)

    def create_title_edit_area(self, parent_frame):
        """创建左上角的纯色图片和文本输入框"""
        top_img = Image.new('RGB', (406, 52), color='white')

        self.top_photo = ImageTk.PhotoImage(top_img)

        # 2. 在Canvas上显示这张图片
        self.top_canvas = tk.Canvas(
            parent_frame,
            width=406,
            height=52,
            highlightthickness=0,
            bg='white'
        )
        # 定位：距离左边0，距离顶部14
        self.top_canvas.place(x=0, y=15)

        self.top_canvas.create_image(0, 0, anchor=tk.NW, image=self.top_photo)

        # 在图片的水平居中位置，距离左侧30，创建文本输入框
        # 计算文本框的位置
        text_x = 30  # 距离左侧30
        text_y = 26  # 垂直居中（52/2）

        # self.create_title_textbox(text_x, text_y)

        # 如果还没有保存的文本，使用默认值
        if not hasattr(self, 'saved_text'):
            self.saved_text = "双击编辑文本"

        # 创建显示文本的Label（非编辑状态）
        self.text_display = tk.Label(
            self.top_canvas,
            text=self.saved_text,  # 显示已保存的文本
            font=(AnagramEditorApp.FONT_FAMILY, 14),
            bg='white',
            fg='black',
            padx=10,
            cursor='xterm'
        )

        # 将Label放置在Canvas上
        self.top_canvas.create_window(text_x, text_y, anchor=tk.W, window=self.text_display)

        # 绑定双击事件
        self.text_display.bind('<Double-Button-1>', self.on_title_text_double_click)

    def create_title_textbox(self, x, y):
        """创建自定义文本框（双击编辑，回车保存）"""
        # 如果还没有保存的文本，使用默认值
        if not hasattr(self, 'saved_text'):
            self.saved_text = "双击编辑文本"

        # 创建显示文本的Label（非编辑状态）
        self.text_display = tk.Label(
            self.top_canvas,
            text=self.saved_text,  # 显示已保存的文本
            font=('微软雅黑', 14),
            bg='white',
            fg='black',
            padx=10,
            cursor='xterm'
        )

        # 将Label放置在Canvas上
        self.top_canvas.create_window(x, y, anchor=tk.W, window=self.text_display)

        # 绑定双击事件
        self.text_display.bind('<Double-Button-1>', self.on_title_text_double_click)

    def on_title_text_double_click(self, event):
        """双击文本进入编辑模式"""
        # 销毁Label
        self.text_display.destroy()

        # 创建Entry控件用于编辑
        self.text_entry = tk.Entry(
            self.top_canvas,
            font=(AnagramEditorApp.FONT_FAMILY, 14),
            bg='white',
            fg='black',
            insertbackground='black',
            width=16,
            justify='left',
            relief='flat',
            highlightthickness=1,
            highlightcolor='#3498db',
            highlightbackground='#bdc3c7'
        )

        # 设置文本为已保存的文本
        self.text_entry.insert(0, self.saved_text)

        # 将Entry放置在Canvas上
        self.top_canvas.create_window(30, 26, anchor=tk.W, window=self.text_entry)

        # 设置焦点并全选文本
        self.text_entry.focus_set()
        self.text_entry.select_range(0, tk.END)

        # 绑定回车键事件（保存）
        self.text_entry.bind('<Return>', self.on_title_text_save)

        # 绑定失去焦点事件（也保存）
        self.text_entry.bind('<FocusOut>', self.on_title_text_save)

        # 绑定ESC键（取消编辑）
        self.text_entry.bind('<Escape>', self.on_title_text_cancel)

    def on_title_text_save(self, event):
        """保存文本并退出编辑模式"""
        new_text = self.text_entry.get().strip()

        # 如果输入为空，走取消逻辑（恢复原文本）
        if not new_text:
            self.on_title_text_cancel(event)
            return

        # 限制最多16个字符
        if len(new_text) > 16:
            new_text = new_text[:16]

        # 更新已保存的文本
        self.saved_text = new_text

        # 打印修改后的值
        print(f"文本已保存为: '{self.saved_text}'")

        # 销毁Entry
        self.text_entry.destroy()

        # 重新创建显示Label，显示新保存的文本
        self.create_title_textbox(30, 26)

    def on_title_text_cancel(self, event):
        """取消编辑，恢复到上一次保存的文本"""
        # 销毁Entry
        self.text_entry.destroy()

        # 重新创建显示Label，显示上一次保存的文本（saved_text）
        self.create_title_textbox(30, 26)

    def create_right_panel(self):
        # 右侧框架
        right_frame = tk.Frame(
            self.main_frame, width=260,
            bg=AnagramEditorApp.PANEL_BG_COLOR,
            relief=tk.RAISED, borderwidth=1
        )
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        right_frame.pack_propagate(False)

        # 按钮面板标签
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
        """创建答案列表区域"""
        # 创建分隔线
        separator = ttk.Separator(parent_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=(10, 5))

        # 答案列表标题
        answer_title = tk.Label(
            parent_frame,
            text="答案列表",
            font=(AnagramEditorApp.FONT_FAMILY, 12, 'bold'),
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

        # 创建答案列表框
        self.answer_listbox = tk.Listbox(
            answer_container,
            # yscrollcommand=answer_scrollbar.set,
            font=(AnagramEditorApp.FONT_FAMILY, 14),
            bg='white',
            fg='black',
            relief=tk.FLAT,
            height=8  # 显示8行
        )
        self.answer_listbox.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

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

        # 清空列表并添加数据
        self.answer_listbox.delete(0, tk.END)
        for answer in sample_answers:
            self.answer_listbox.insert(tk.END, answer)

        # 绑定双击事件
        self.answer_listbox.bind('<Double-Button-1>', self.on_answer_double_click)

    def on_answer_double_click(self, event):
        """答案列表双击事件 - 弹出编辑窗口"""
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
        # 创建顶层窗口
        edit_window = tk.Toplevel(self.root)
        edit_window.title("编辑答案")
        edit_window.geometry("300x120")
        edit_window.resizable(False, False)
        edit_window.transient(self.root)  # 设置为主窗口的子窗口
        edit_window.grab_set()  # 模态窗口

        # 居中显示
        edit_window.update_idletasks()
        width = edit_window.winfo_width()
        height = edit_window.winfo_height()
        x = (edit_window.winfo_screenwidth() // 2) - (width // 2)
        y = (edit_window.winfo_screenheight() // 2) - (height // 2)
        edit_window.geometry(f'{width}x{height}+{x}+{y}')

        # 创建编辑框和提示标签
        tk.Label(edit_window, text="编辑答案（最多7个字符）:",
                 font=(AnagramEditorApp.FONT_FAMILY, 11)).pack(pady=2)

        # 创建Entry控件
        entry_var = tk.StringVar(value=original_text)

        # 文本变化回调函数
        def on_text_change(*args):
            text = entry_var.get()
            if len(text) > 7:
                # 如果超过7个字符，截断并更新
                entry_var.set(text[:7])

        # 绑定文本变化事件
        entry_var.trace('w', on_text_change)

        entry = tk.Entry(
            edit_window,
            textvariable=entry_var,
            font=(AnagramEditorApp.FONT_FAMILY, 12),
            width=20  # 减小宽度以适应7个字符
        )
        entry.pack(pady=5)
        entry.focus_set()
        entry.select_range(0, tk.END)

        # 按钮框架
        button_frame = tk.Frame(edit_window)
        button_frame.pack(pady=10)

        def save_edit():
            """保存编辑"""
            new_text = entry_var.get().strip()

            # 如果没有输入任何内容，保持原样（不修改）
            if not new_text:
                edit_window.destroy()
                return

            # 如果有输入内容，检查是否和原文本相同
            if new_text == original_text:
                print("文本未更改")
                edit_window.destroy()
                return

            # 确保不超过7个字符（再次检查）
            if len(new_text) > 7:
                new_text = new_text[:7]
                print(f"文本超过7个字符，已截断为: '{new_text}'")

            # 删除原项目，插入新项目
            self.answer_listbox.delete(index)
            self.answer_listbox.insert(index, new_text)
            print(f"答案已修改为: '{new_text}'")

            edit_window.destroy()

        def cancel_edit():
            """取消编辑"""
            edit_window.destroy()

        # 保存按钮
        save_btn = tk.Button(
            button_frame,
            text="保存",
            command=save_edit,
            width=10
        )
        save_btn.pack(side=tk.LEFT, padx=5)

        # 取消按钮
        cancel_btn = tk.Button(
            button_frame,
            text="取消",
            command=cancel_edit,
            width=10
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)

        # 绑定回车键
        entry.bind('<Return>', lambda e: save_edit())
        entry.bind('<Escape>', lambda e: cancel_edit())

        # 初始时调用一次
        on_text_change()

    def on_list_select(self, event):
        if not self.list_box.curselection():
            return

        index = self.list_box.curselection()[0]
        item = self.list_box.get(index)
        # self.status_label.config(text=f"选择: {item}")


def main():
    AnagramEditorApp()


if __name__ == "__main__":
    main()
