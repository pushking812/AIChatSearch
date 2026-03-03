
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

from . import model


def run_gui():
    app = Application()
    app.mainloop()


class Application(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("DeepSeek Chat Archive Navigator")
        self.geometry("1200x800")

        # Data
        self.chats = []
        self.filtered_chats = []
        self.selected_chats = []
        self.visible_pairs = []
        self.tree_item_map = {}

        self.current_pair = None
        self.current_pair_index = None

        self.chat_filter_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.search_field_var = tk.StringVar(value="Запрос")

        self.archive_path = None
        self.raw_data = None

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

        # LEFT
        left_frame = tk.Frame(main_paned)
        main_paned.add(left_frame, width=300)

        tk.Label(left_frame, text="Чаты", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=5)

        self.chat_filter_entry = tk.Entry(left_frame, textvariable=self.chat_filter_var)
        self.chat_filter_entry.pack(fill=tk.X, padx=5, pady=(0,5))
        self.chat_filter_entry.bind("<KeyRelease>", self.filter_chats)

        self.chat_listbox = tk.Listbox(left_frame, selectmode=tk.EXTENDED)
        self.chat_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)

        scrollbar = tk.Scrollbar(left_frame, command=self.chat_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_listbox.config(yscrollcommand=scrollbar.set)

        self.chat_listbox.bind("<<ListboxSelect>>", self.on_chat_select)

        # RIGHT
        right_paned = tk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(right_paned)

        # Top
        top_frame = tk.Frame(right_paned)
        right_paned.add(top_frame, height=300)

        tk.Label(top_frame, text="Сообщения", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=5)

        search_frame = tk.Frame(top_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=(0,5))

        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))

        self.search_combobox = ttk.Combobox(
            search_frame,
            textvariable=self.search_field_var,
            values=["Название чата", "Запрос", "Ответ"],
            state="readonly",
            width=18
        )
        self.search_combobox.pack(side=tk.LEFT, padx=(0,5))

        tk.Button(search_frame, text="Найти", command=self.search_current_chat).pack(side=tk.LEFT, padx=(0,5))
        tk.Button(search_frame, text="Сбросить", command=self.reset_search).pack(side=tk.LEFT)

        # --- Treeview instead of Listbox ---
        self.tree = ttk.Treeview(top_frame, columns=('chat','idx','request','response'), show='headings')
        self.tree.heading('chat', text='Чат')
        self.tree.heading('idx', text='#')
        self.tree.heading('request', text='Запрос')
        self.tree.heading('response', text='Ответ')
        self.tree.column('chat', width=180)
        self.tree.column('idx', width=50, anchor='center')
        self.tree.column('request', width=300)
        self.tree.column('response', width=300)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0), pady=5)

        tree_scroll = tk.Scrollbar(top_frame, command=self.tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=tree_scroll.set)

        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

        # Bottom
        bottom_frame = tk.Frame(right_paned)
        right_paned.add(bottom_frame)

        tk.Label(bottom_frame, text="Запрос", font=("Arial", 11, "bold")).pack(anchor="w", padx=5, pady=(5,0))
        self.request_text = tk.Text(bottom_frame, height=10)
        self.request_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(bottom_frame, text="Ответ", font=("Arial", 11, "bold")).pack(anchor="w", padx=5, pady=(5,0))
        self.response_text = tk.Text(bottom_frame, height=10)
        self.response_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        nav_frame = tk.Frame(bottom_frame)
        nav_frame.pack(fill=tk.X, padx=5, pady=(0,5))

        self.prev_button = tk.Button(nav_frame, text="← Предыдущая", command=self.prev_pair, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.next_button = tk.Button(nav_frame, text="Следующая →", command=self.next_pair, state=tk.DISABLED)
        self.next_button.pack(side=tk.LEFT, padx=5)

    # ---------------- DATA LOADING ----------------

    def open_archive(self):
        file_path = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")])
        if not file_path:
            return

        try:
            self.chats = model.load_from_zip(file_path)
            self.filtered_chats = self.chats[:]
            self.archive_path = file_path
            if hasattr(model, "raw_data"):
                self.raw_data = model.raw_data
            self._update_chat_list()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть архив:\n{e}")

    def _update_chat_list(self):
        self.chat_listbox.delete(0, tk.END)
        for chat in self.filtered_chats:
            self.chat_listbox.insert(tk.END, chat.title)

    # ---------------- CHAT SELECTION ----------------

    def on_chat_select(self, event=None):
        indices = self.chat_listbox.curselection()

        # Ignore false deselection event caused by focus change
        if not indices and self.selected_chats:
            return

        self.selected_chats = [
            self.filtered_chats[i] for i in indices
            if i < len(self.filtered_chats)
        ]

        self._rebuild_visible_pairs()
    def _rebuild_visible_pairs(self):
        self.visible_pairs = []
        self.tree_item_map = {}
        for chat in self.selected_chats:
            for pair in chat.get_pairs():
                self.visible_pairs.append((chat, pair))
        self.current_pair_index = None
        self.display_visible_pairs()
        self.update_nav_buttons()

    # ---------------- PAIR LIST ----------------

    def display_visible_pairs(self):
        print(f"[DEBUG] display_visible_pairs called, visible_pairs={len(self.visible_pairs)}")
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree_item_map = {}

        for chat, pair in self.visible_pairs:
            item_id = self.tree.insert(
                '',
                'end',
                values=(chat.title, pair.index, pair.request_text[:30], pair.response_text[:30])
            )
            self.tree_item_map[item_id] = (chat, pair)

    def on_tree_select(self, event=None):
        print(f"[DEBUG] on_tree_select ENTER | current_pair_index(before)={self.current_pair_index}")
        selection = self.tree.selection()
        print(f"[DEBUG] on_tree_select selection={selection}")
        if not selection:
            return

        item_id = selection[0]
        chat_pair = self.tree_item_map.get(item_id)
        if not chat_pair:
            print("[DEBUG] No mapping found for selected item")
            return

        chat, pair = chat_pair

        # Synchronize index with visible_pairs
        found_index = None
        for i, (c, p) in enumerate(self.visible_pairs):
            if p is pair:
                found_index = i
                break

        if found_index is None:
            print("[DEBUG] Pair not found in visible_pairs")
            return

        self.current_pair_index = found_index
        print(f"[DEBUG] current_pair_index set to {self.current_pair_index}")

        self.current_pair = pair
        self._display_pair(pair)
        self.update_nav_buttons()

    def on_pair_select(self, event=None):
        if not selection:
            return

        index = selection[0]
        if index >= len(self.visible_pairs):
            return

        self.current_pair_index = index
        _, pair = self.visible_pairs[index]
        self.current_pair = pair
        self._display_pair(pair)
        self.update_nav_buttons()

    def _display_pair(self, pair):
        self.request_text.delete("1.0", tk.END)
        self.response_text.delete("1.0", tk.END)
        self.request_text.insert(tk.END, pair.request_text)
        self.response_text.insert(tk.END, pair.response_text)

    # ---------------- SEARCH ----------------

    def search_current_chat(self):
        query = self.search_var.get().strip().lower()
        field = self.search_field_var.get()

        if not query:
            self.reset_search()
            return

        result = []

        for chat in self.selected_chats:
            if field == "Название чата":
                if query in chat.title.lower():
                    for pair in chat.get_pairs():
                        result.append((chat, pair))
            else:
                for pair in chat.get_pairs():
                    if field == "Запрос" and query in pair.request_text.lower():
                        result.append((chat, pair))
                    if field == "Ответ" and query in pair.response_text.lower():
                        result.append((chat, pair))

        self.visible_pairs = result
        self.current_pair_index = None
        self.display_visible_pairs()
        self.update_nav_buttons()

    def reset_search(self):
        self.search_var.set("")
        self._rebuild_visible_pairs()

    # ---------------- NAVIGATION ----------------

    def prev_pair(self):
        if self.current_pair_index is None:
            return
        if self.current_pair_index > 0:
            self.current_pair_index -= 1
            self._select_pair(self.current_pair_index)

    def next_pair(self):
        if self.current_pair_index is None:
            return
        if self.current_pair_index < len(self.visible_pairs) - 1:
            self.current_pair_index += 1
            self._select_pair(self.current_pair_index)

    def _select_pair(self, index):
        print(f"[DEBUG] _select_pair called | index={index} | visible_pairs={len(self.visible_pairs)}")

        if index < 0 or index >= len(self.visible_pairs):
            print("[DEBUG] _select_pair index out of range")
            return

        self.current_pair_index = index
        chat, pair = self.visible_pairs[index]

        # Find corresponding Treeview item
        for item_id, (c, p) in self.tree_item_map.items():
            if p is pair:
                # Clear previous selection
                self.tree.selection_remove(self.tree.selection())
                self.tree.selection_set(item_id)
                self.tree.focus(item_id)
                self.tree.see(item_id)
                print(f"[DEBUG] Treeview selection moved to item {item_id}")
                break

        self.current_pair = pair
        self._display_pair(pair)
        self.update_nav_buttons()

    def update_nav_buttons(self):
        print(f"[DEBUG] update_nav_buttons | visible_pairs={len(self.visible_pairs)} | current_pair_index={self.current_pair_index}")
        if not self.visible_pairs or self.current_pair_index is None:
            self.prev_button.config(state=tk.DISABLED)
            self.next_button.config(state=tk.DISABLED)
            return

        self.prev_button.config(state=tk.NORMAL if self.current_pair_index > 0 else tk.DISABLED)
        self.next_button.config(
            state=tk.NORMAL if self.current_pair_index < len(self.visible_pairs) - 1 else tk.DISABLED
        )

    # ---------------- FILTER ----------------

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

        # Reset selections after filtering
        self.selected_chats = []
        self.visible_pairs = []
        self.tree_item_map = {}
        self.current_pair_index = None
        self.update_nav_buttons()