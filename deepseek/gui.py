import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

from . import model
from .controller import ChatController


def run_gui():
    app = Application()
    app.mainloop()


class Application(tk.Tk):
    def __init__(self):
        super().__init__()

        self.controller = ChatController()

        self.title("DeepSeek Chat Archive Navigator")
        self.geometry("1200x800")

        self.tree_item_map = {}
        self.current_selected_chats = []

        self.chat_filter_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.search_field_var = tk.StringVar(value="Запрос")

        self._create_menu()
        self._create_layout()

    # ---------------- MENU ----------------

    def _create_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Открыть архив...", command=self.open_archive)
        menubar.add_cascade(label="Файл", menu=file_menu)
        self.config(menu=menubar)

    # ---------------- LAYOUT ----------------

    def _create_layout(self):
        main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(main_paned)
        main_paned.add(left_frame, width=300)

        tk.Label(left_frame, text="Чаты", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=5)

        self.chat_filter_entry = tk.Entry(left_frame, textvariable=self.chat_filter_var)
        self.chat_filter_entry.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.chat_filter_entry.bind("<KeyRelease>", self.filter_chats)

        self.chat_listbox = tk.Listbox(left_frame, selectmode=tk.EXTENDED)
        self.chat_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)

        scrollbar = tk.Scrollbar(left_frame, command=self.chat_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_listbox.config(yscrollcommand=scrollbar.set)
        self.chat_listbox.bind("<ButtonRelease-1>", self.on_chat_select)
        self.chat_listbox.bind("<Shift-ButtonRelease-1>", self.on_chat_select)
        self.chat_listbox.bind("<Control-ButtonRelease-1>", self.on_chat_select)

        right_paned = tk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(right_paned)

        top_frame = tk.Frame(right_paned)
        right_paned.add(top_frame, height=300)

        tk.Label(top_frame, text="Сообщения", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=5)

        search_frame = tk.Frame(top_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.search_combobox = ttk.Combobox(
            search_frame,
            textvariable=self.search_field_var,
            values=["Название чата", "Запрос", "Ответ"],
            state="readonly",
            width=18
        )
        self.search_combobox.pack(side=tk.LEFT, padx=(0, 5))

        tk.Button(search_frame, text="Найти", command=self.search_current_chat).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(search_frame, text="Сбросить", command=self.reset_search).pack(side=tk.LEFT)

        self.tree = ttk.Treeview(
            top_frame,
            columns=("chat", "idx", "request", "response"),
            show="headings",
        )
        self.tree.heading("chat", text="Чат")
        self.tree.heading("idx", text="#")
        self.tree.heading("request", text="Запрос")
        self.tree.heading("response", text="Ответ")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)

        tree_scroll = tk.Scrollbar(top_frame, command=self.tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=tree_scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        bottom_frame = tk.Frame(right_paned)
        right_paned.add(bottom_frame)

        self.position_label = tk.Label(bottom_frame, text="", font=("Arial", 10, "italic"))
        self.position_label.pack(anchor="w", padx=5, pady=(5, 0))

        tk.Label(bottom_frame, text="Запрос", font=("Arial", 11, "bold")).pack(anchor="w", padx=5)
        self.request_text = tk.Text(bottom_frame, height=10)
        self.request_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(bottom_frame, text="Ответ", font=("Arial", 11, "bold")).pack(anchor="w", padx=5)
        self.response_text = tk.Text(bottom_frame, height=10)
        self.response_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        nav_frame = tk.Frame(bottom_frame)
        nav_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.prev_button = tk.Button(nav_frame, text="← Предыдущая", command=self.prev_pair, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.next_button = tk.Button(nav_frame, text="Следующая →", command=self.next_pair, state=tk.DISABLED)
        self.next_button.pack(side=tk.LEFT, padx=5)

    # ---------------- DATA ----------------

    def open_archive(self):
        file_path = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")])
        if not file_path:
            return

        try:
            chats = model.load_from_zip(file_path)
            self.controller.set_chats(chats)
            self._update_chat_list()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть архив:\n{e}")

    def _update_chat_list(self):
        self.chat_listbox.delete(0, tk.END)
        for chat in self.controller.get_filtered_chats():
            self.chat_listbox.insert(tk.END, chat.title)

    def filter_chats(self, event=None):
        self.controller.filter_chats(self.chat_filter_var.get())
        self._update_chat_list()

    # ---------------- TREE ----------------

    def on_chat_select(self, event=None):
        indices = self.chat_listbox.curselection()

        if not indices:
            return

        filtered = self.controller.get_filtered_chats()

        self.current_selected_chats = [
            filtered[i]
            for i in indices
            if i < len(filtered)
        ]

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.tree_item_map = {}

        for chat in self.current_selected_chats:
            for pair in chat.get_pairs():
                item_id = self.tree.insert(
                    "",
                    "end",
                    values=(
                        chat.title,
                        pair.index,
                        pair.request_text[:30],
                        pair.response_text[:30],
                    ),
                )
                self.tree_item_map[item_id] = (chat, pair)

        self.position_label.config(text="")
        self.update_nav_buttons()

    def on_tree_select(self, event=None):
        selection = self.tree.selection()
        if not selection:
            return

        item_id = selection[0]
        chat_pair = self.tree_item_map.get(item_id)
        if not chat_pair:
            return

        chat, pair = chat_pair

        pair = self.controller.select_pair(chat, pair)
        if pair:
            self._display_pair(pair)
            self._update_position_label()
            self.update_nav_buttons()

    def _display_pair(self, pair):
        self.request_text.delete("1.0", tk.END)
        self.response_text.delete("1.0", tk.END)
        self.request_text.insert(tk.END, pair.request_text)
        self.response_text.insert(tk.END, pair.response_text)

    # ---------------- SEARCH ----------------

    def search_current_chat(self):
        if not self.current_selected_chats:
            return

        chat = self.current_selected_chats[0]
        pairs = self.controller.search(chat, self.search_var.get(), self.search_field_var.get())

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.tree_item_map = {}

        for pair in pairs:
            item_id = self.tree.insert(
                "",
                "end",
                values=(
                    chat.title,
                    pair.index,
                    pair.request_text[:30],
                    pair.response_text[:30],
                ),
            )
            self.tree_item_map[item_id] = (chat, pair)

    def reset_search(self):
        self.search_var.set("")
        self.on_chat_select()

    # ---------------- NAVIGATION ----------------

    def prev_pair(self):
        pair = self.controller.prev_pair()
        if pair:
            self._display_pair(pair)
            self._update_position_label()
            self.update_nav_buttons()

    def next_pair(self):
        pair = self.controller.next_pair()
        if pair:
            self._display_pair(pair)
            self._update_position_label()
            self.update_nav_buttons()

    def update_nav_buttons(self):
        can_prev, can_next = self.controller.get_nav_state()
        self.prev_button.config(state=tk.NORMAL if can_prev else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if can_next else tk.DISABLED)

    def _update_position_label(self):
        title, index, total = self.controller.get_position_info()
        if title is None:
            self.position_label.config(text="")
        else:
            self.position_label.config(
                text=f"Чат: {title} | Сообщение {index} из {total}"
            )
