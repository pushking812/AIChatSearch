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
        self.chat_filter_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.search_field_var = tk.StringVar(value="Запрос")

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

        # --- SEARCH BLOCK RESTORED ---
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

    # Remaining logic from 433 remains unchanged... (chat selection, navigation, etc.)

