import tkinter as tk
from tkinter import filedialog, messagebox

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
        self.current_chat = None
        self.current_pairs = []
        self.current_pair = None
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

        self.chat_listbox = tk.Listbox(left_frame)
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
        selection = self.chat_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        self.current_chat = self.chats[index]
        self.current_pairs = self.current_chat.get_pairs()

        self._update_pair_list()

    def _update_pair_list(self):
        self.pair_listbox.delete(0, tk.END)

        for pair in self.current_pairs:
            preview_request = pair.request_text[:50].replace("\n", " ")
            preview_response = pair.response_text[:50].replace("\n", " ")

            line = f"#{pair.index}: {preview_request}... → {preview_response}"
            self.pair_listbox.insert(tk.END, line)

    def on_pair_select(self, event):
        selection = self.pair_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        self.current_pair = self.current_pairs[index]

        self._display_pair(self.current_pair)

    def _display_pair(self, pair):
        self.request_text.delete("1.0", tk.END)
        self.response_text.delete("1.0", tk.END)

        self.request_text.insert(tk.END, pair.request_text)
        self.response_text.insert(tk.END, pair.response_text)