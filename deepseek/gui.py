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

        # Данные
        self.chats = []
        self.filtered_chats = []
        self.selected_chats = []
        self.chat_filter_var = tk.StringVar()
        self.current_chat = None
        self.current_pairs = []
        self.multi_mode = False
        self.multi_pairs = []
        self.current_pair = None
        self.current_pair_index = None
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
        # Главный горизонтальный разделитель
        main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # -------- Левая панель --------
        left_frame = tk.Frame(main_paned)
        main_paned.add(left_frame, width=300)

        left_label = tk.Label(left_frame, text="Чаты", font=("Arial", 12, "bold"))
        left_label.pack(anchor="w", padx=5, pady=5)

        # --- Chat Filter Entry ---
        self.chat_filter_entry = tk.Entry(left_frame, textvariable=self.chat_filter_var)
        self.chat_filter_entry.pack(fill=tk.X, padx=5, pady=(0,5))
        self.chat_filter_entry.bind("<KeyRelease>", self.filter_chats)


        self.chat_listbox = tk.Listbox(left_frame, selectmode=tk.EXTENDED)
        self.chat_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)

        chat_scrollbar = tk.Scrollbar(left_frame, command=self.chat_listbox.yview)
        chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        self.chat_listbox.config(yscrollcommand=chat_scrollbar.set)
        self.chat_listbox.bind("<<ListboxSelect>>", self.on_chat_select)

        # -------- Правая панель --------
        right_paned = tk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(right_paned)

        # Верхняя часть (список сообщений)
        top_frame = tk.Frame(right_paned)
        right_paned.add(top_frame, height=300)

        top_label = tk.Label(top_frame, text="Сообщения", font=("Arial", 12, "bold"))
        top_label.pack(anchor="w", padx=5, pady=5)

        # --- Search Frame ---
        search_frame = tk.Frame(top_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.search_var = tk.StringVar()
        self.search_field_var = tk.StringVar(value="Запрос")

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

        self.search_button = tk.Button(
            search_frame,
            text="Найти",
            command=self.search_current_chat
        )
        self.search_button.pack(side=tk.LEFT, padx=(0, 5))

        self.reset_button = tk.Button(
            search_frame,
            text="Сбросить",
            command=self.reset_search
        )
        self.reset_button.pack(side=tk.LEFT)


        self.pair_listbox = tk.Listbox(top_frame)
        self.pair_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)

        pair_scrollbar = tk.Scrollbar(top_frame, command=self.pair_listbox.yview)
        pair_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        self.pair_listbox.config(yscrollcommand=pair_scrollbar.set)
        self.pair_listbox.bind("<<ListboxSelect>>", self.on_pair_select)

        # Нижняя часть (тексты запроса и ответа)
        bottom_frame = tk.Frame(right_paned)
        right_paned.add(bottom_frame)

        # Запрос
        request_label = tk.Label(bottom_frame, text="Запрос", font=("Arial", 11, "bold"))
        request_label.pack(anchor="w", padx=5, pady=(5, 0))

        request_frame = tk.Frame(bottom_frame)
        request_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.request_text = tk.Text(request_frame, height=10)
        self.request_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        request_scrollbar = tk.Scrollbar(request_frame, command=self.request_text.yview)
        request_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.request_text.config(yscrollcommand=request_scrollbar.set)

        # Ответ
        response_label = tk.Label(bottom_frame, text="Ответ", font=("Arial", 11, "bold"))
        response_label.pack(anchor="w", padx=5, pady=(5, 0))

        response_frame = tk.Frame(bottom_frame)
        response_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.response_text = tk.Text(response_frame, height=10)
        self.response_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        response_scrollbar = tk.Scrollbar(response_frame, command=self.response_text.yview)
        response_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.response_text.config(yscrollcommand=response_scrollbar.set)

        # --- Navigation controls ---
        nav_frame = tk.Frame(bottom_frame)
        nav_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.prev_button = tk.Button(
            nav_frame, text="← Предыдущая", command=self.prev_pair, state=tk.DISABLED
        )
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.next_button = tk.Button(
            nav_frame, text="Следующая →", command=self.next_pair, state=tk.DISABLED
        )
        self.next_button.pack(side=tk.LEFT, padx=5)


    # ---------------- LOGIC ----------------

    def open_archive(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("ZIP files", "*.zip")]
        )

        if not file_path:
            return

        try:
            chats = model.load_from_zip(file_path)
            self.chats = chats
            self.filtered_chats = self.chats[:]
            self.archive_path = file_path

            # raw_data хранится в model (если реализовано глобально)
            if hasattr(model, "raw_data"):
                self.raw_data = model.raw_data

            self._update_chat_list()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть архив:\n{e}")

    def _update_chat_list(self):
        self.chat_listbox.delete(0, tk.END)

        for chat in self.chats:
            self.chat_listbox.insert(tk.END, chat.title)

    def on_chat_select(self, event):
        self.update_selected_chats()
        
        if not self.selected_chats:
            return
        
        if len(self.selected_chats) == 1:
            self.multi_mode = False
            self.current_chat = self.selected_chats[0]
            self.current_pairs = self.current_chat.get_pairs()
        else:
            self.multi_mode = True
            self.current_chat = None
            self.multi_pairs = []
            for chat in self.selected_chats:
                for pair in chat.get_pairs():
                    self.multi_pairs.append((chat, pair))
        
        self.current_pair_index = None
        self._update_pair_list()
        self.update_nav_buttons()
    def _update_pair_list(self):
        self.pair_listbox.delete(0, tk.END)
        
        if self.multi_mode:
            for chat, pair in self.multi_pairs:
                display_text = (
                    f"{chat.title} [#{pair.index}]: "
                    f"{pair.request_text[:30]}... → "
                    f"{pair.response_text[:30]}..."
                )
                self.pair_listbox.insert(tk.END, display_text)
        else:
            for pair in self.current_pairs:
                display_text = (
                    f"#{pair.index}: "
                    f"{pair.request_text[:30]}... → "
                    f"{pair.response_text[:30]}..."
                )
                self.pair_listbox.insert(tk.END, display_text)
    def on_pair_select(self, event):
        selection = self.pair_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        self.current_pair_index = index
        
        if self.multi_mode:
            chat, pair = self.multi_pairs[index]
        else:
            pair = self.current_pairs[index]
        
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
        if not self.current_chat:
            return

        query = self.search_var.get().strip().lower()
        field = self.search_field_var.get()

        if not query:
            self.reset_search()
            return

        if field == "Название чата":
            if query in self.current_chat.title.lower():
                self.current_pairs = self.current_chat.get_pairs()
            else:
                self.current_pairs = []
        else:
            filtered = []
            for pair in self.current_chat.get_pairs():
                if field == "Запрос":
                    if query in pair.request_text.lower():
                        filtered.append(pair)
                elif field == "Ответ":
                    if query in pair.response_text.lower():
                        filtered.append(pair)

            self.current_pairs = filtered

        self.current_pair_index = None
        self._update_pair_list()
        self.update_nav_buttons()

    def reset_search(self):
        if not self.current_chat:
            return

        self.search_var.set("")
        self.current_pairs = self.current_chat.get_pairs()
        self.current_pair_index = None
        self._update_pair_list()
        self.update_nav_buttons()

    # ---------------- NAVIGATION ----------------
        if not self.current_pairs or self.current_pair_index is None:
            self.prev_button.config(state=tk.DISABLED)
            self.next_button.config(state=tk.DISABLED)
            return

        if self.current_pair_index <= 0:
            self.prev_button.config(state=tk.DISABLED)
        else:
            self.prev_button.config(state=tk.NORMAL)

        if self.current_pair_index >= len(self.current_pairs) - 1:
            self.next_button.config(state=tk.DISABLED)
        else:
            self.next_button.config(state=tk.NORMAL)




    # ---------------- SEARCH ----------------

    def search_current_chat(self):
        if not self.current_chat:
            return

        query = self.search_var.get().strip().lower()
        field = self.search_field_var.get()

        if not query:
            self.reset_search()
            return

        if field == "Название чата":
            if query in self.current_chat.title.lower():
                self.current_pairs = self.current_chat.get_pairs()
            else:
                self.current_pairs = []
        else:
            filtered = []
            for pair in self.current_chat.get_pairs():
                if field == "Запрос":
                    if query in pair.request_text.lower():
                        filtered.append(pair)
                elif field == "Ответ":
                    if query in pair.response_text.lower():
                        filtered.append(pair)

            self.current_pairs = filtered

        self.current_pair_index = None
        self._update_pair_list()
        self.update_nav_buttons()

    def reset_search(self):
        if not self.current_chat:
            return

        self.search_var.set("")
        self.current_pairs = self.current_chat.get_pairs()
        self.current_pair_index = None
        self._update_pair_list()
        self.update_nav_buttons()

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
        if self.current_pair_index < len(self.current_pairs) - 1:
            self.current_pair_index += 1
            self._select_pair(self.current_pair_index)

    def _select_pair(self, index):
        self.pair_listbox.selection_clear(0, tk.END)
        self.pair_listbox.selection_set(index)
        self.pair_listbox.activate(index)

        self.current_pair = self.current_pairs[index]
        self._display_pair(self.current_pair)
        self.update_nav_buttons()

    def update_nav_buttons(self):
        if not self.current_pairs or self.current_pair_index is None:
            self.prev_button.config(state=tk.DISABLED)
            self.next_button.config(state=tk.DISABLED)
            return

        if self.current_pair_index <= 0:
            self.prev_button.config(state=tk.DISABLED)
        else:
            self.prev_button.config(state=tk.NORMAL)

        if self.current_pair_index >= len(self.current_pairs) - 1:
            self.next_button.config(state=tk.DISABLED)
        else:
            self.next_button.config(state=tk.NORMAL)


    # ---------------- CHAT FILTER ----------------

    def filter_chats(self, event=None):
        query = self.chat_filter_var.get().lower().strip()
        self.chat_listbox.delete(0, tk.END)

        if not query:
            self.filtered_chats = self.chats[:]
        else:
            self.filtered_chats = [
                chat for chat in self.chats
                if query in chat.title.lower()
            ]

        for chat in self.filtered_chats:
            self.chat_listbox.insert(tk.END, chat.title)


    def select_all_chats(self):
        self.chat_listbox.select_set(0, tk.END)
        self.update_selected_chats()

    def clear_chat_selection(self):
        self.chat_listbox.selection_clear(0, tk.END)
        self.selected_chats = []

    def update_selected_chats(self):
        indices = self.chat_listbox.curselection()
        self.selected_chats = [
            self.filtered_chats[i] for i in indices
            if i < len(self.filtered_chats)
        ]