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

        self.chats = []
        self.filtered_chats = []
        self.tree_item_map = {}

        self.chat_filter_var = tk.StringVar()

        self.archive_path = None
        self.raw_data = None

        self._create_menu()
        self._create_layout()

    def _create_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Открыть архив...", command=self.open_archive)
        menubar.add_cascade(label="Файл", menu=file_menu)
        self.config(menu=menubar)

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

        self.chat_listbox.bind("<<ListboxSelect>>", self.on_chat_select)

        right_paned = tk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(right_paned)

        top_frame = tk.Frame(right_paned)
        right_paned.add(top_frame, height=300)

        tk.Label(top_frame, text="Сообщения", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=5)

        self.tree = ttk.Treeview(
            top_frame,
            columns=("chat", "idx", "request", "response"),
            show="headings",
        )
        self.tree.heading("chat", text="Чат")
        self.tree.heading("idx", text="#")
        self.tree.heading("request", text="Запрос")
        self.tree.heading("response", text="Ответ")
        self.tree.column("chat", width=180)
        self.tree.column("idx", width=50, anchor="center")
        self.tree.column("request", width=300)
        self.tree.column("response", width=300)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)

        tree_scroll = tk.Scrollbar(top_frame, command=self.tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=tree_scroll.set)

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        bottom_frame = tk.Frame(right_paned)
        right_paned.add(bottom_frame)

        tk.Label(bottom_frame, text="Запрос", font=("Arial", 11, "bold")).pack(anchor="w", padx=5, pady=(5, 0))
        self.request_text = tk.Text(bottom_frame, height=10)
        self.request_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(bottom_frame, text="Ответ", font=("Arial", 11, "bold")).pack(anchor="w", padx=5, pady=(5, 0))
        self.response_text = tk.Text(bottom_frame, height=10)
        self.response_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        nav_frame = tk.Frame(bottom_frame)
        nav_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.prev_button = tk.Button(nav_frame, text="← Предыдущая", command=self.prev_pair, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.next_button = tk.Button(nav_frame, text="Следующая →", command=self.next_pair, state=tk.DISABLED)
        self.next_button.pack(side=tk.LEFT, padx=5)

    def open_archive(self):
        file_path = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")])
        if not file_path:
            return

        try:
            self.chats = model.load_from_zip(file_path)
            self.filtered_chats = self.chats[:]
            self.controller.set_chats(self.chats)
            self._update_chat_list()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть архив:\n{e}")

    def _update_chat_list(self):
        self.chat_listbox.delete(0, tk.END)
        for chat in self.filtered_chats:
            self.chat_listbox.insert(tk.END, chat.title)

    def on_chat_select(self, event=None):
        indices = self.chat_listbox.curselection()
        selected = [
            self.filtered_chats[i]
            for i in indices
            if i < len(self.filtered_chats)
        ]
        self.controller.select_chats(selected)
        self.display_visible_pairs()
        self.update_nav_buttons()

    def display_visible_pairs(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.tree_item_map = {}

        for index, (chat, pair) in enumerate(self.controller.get_visible_pairs()):
            item_id = self.tree.insert(
                "",
                "end",
                values=(chat.title, pair.index, pair.request_text[:30], pair.response_text[:30]),
            )
            self.tree_item_map[item_id] = index

    def on_tree_select(self, event=None):
        selection = self.tree.selection()
        if not selection:
            return

        item_id = selection[0]
        index = self.tree_item_map.get(item_id)
        if index is None:
            return

        pair = self.controller.select_pair_by_index(index)
        if pair:
            self._display_pair(pair)
            self.update_nav_buttons()

    def _display_pair(self, pair):
        self.request_text.delete("1.0", tk.END)
        self.response_text.delete("1.0", tk.END)
        self.request_text.insert(tk.END, pair.request_text)
        self.response_text.insert(tk.END, pair.response_text)

    def _sync_tree_selection(self):
        index = self.controller.current_pair_index
        if index is None:
            return

        for item_id, item_index in self.tree_item_map.items():
            if item_index == index:
                self.tree.selection_remove(self.tree.selection())
                self.tree.selection_set(item_id)
                self.tree.focus(item_id)
                self.tree.see(item_id)
                break

    def prev_pair(self):
        pair = self.controller.prev_pair()
        if pair:
            self._display_pair(pair)
            self._sync_tree_selection()
            self.update_nav_buttons()

    def next_pair(self):
        pair = self.controller.next_pair()
        if pair:
            self._display_pair(pair)
            self._sync_tree_selection()
            self.update_nav_buttons()

    def update_nav_buttons(self):
        can_prev, can_next = self.controller.get_nav_state()
        self.prev_button.config(state=tk.NORMAL if can_prev else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if can_next else tk.DISABLED)

    def filter_chats(self, event=None):
        query = self.chat_filter_var.get().lower().strip()
        if not query:
            self.filtered_chats = self.chats[:]
        else:
            self.filtered_chats = [
                chat for chat in self.chats
                if query in chat.title.lower()
            ]
        self._update_chat_list()
