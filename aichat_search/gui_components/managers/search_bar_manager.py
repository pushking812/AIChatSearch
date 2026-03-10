# aichat_search/gui_components/managers/search_bar_manager.py

import tkinter as tk
from tkinter import ttk

class SearchBarManager:
    def __init__(self, parent, app, search_controller):
        """
        parent: родительский фрейм (search_frame), куда будут помещены виджеты поиска.
        app: ссылка на главное приложение (Application) для доступа к панелям и контроллеру.
        search_controller: экземпляр SearchController.
        """
        self.app = app
        self.search_controller = search_controller
        self.frame = tk.Frame(parent)
        self.frame.pack(fill=tk.X, padx=0, pady=0)

        self.search_var = tk.StringVar()
        self.search_field_var = tk.StringVar(value="Запрос")
        self.live_search_var = tk.BooleanVar(value=True)

        self._create_widgets()

    def _create_widgets(self):
        # Поле ввода
        self.entry = tk.Entry(self.frame, textvariable=self.search_var)
        self.entry.bind('<KeyRelease>', self._on_key)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Выбор поля поиска
        self.combobox = ttk.Combobox(
            self.frame,
            textvariable=self.search_field_var,
            values=["Запрос", "Ответ"],
            state="readonly",
            width=18
        )
        self.combobox.pack(side=tk.LEFT, padx=(0, 5))

        # Кнопка "Найти"
        self.search_button = tk.Button(self.frame, text="Найти", command=self.perform_search)
        self.search_button.pack(side=tk.LEFT, padx=(0, 5))

        # Чекбокс Live
        self.live_check = tk.Checkbutton(self.frame, text="Live", variable=self.live_search_var)
        self.live_check.pack(side=tk.LEFT, padx=5)

        # Кнопки навигации по результатам
        self.prev_button = tk.Button(self.frame, text="<", width=2, command=self.prev_result)
        self.prev_button.pack(side=tk.LEFT)
        self.next_button = tk.Button(self.frame, text=">", width=2, command=self.next_result)
        self.next_button.pack(side=tk.LEFT)

        # Счётчик результатов
        self.counter_label = tk.Label(self.frame, text="0 / 0")
        self.counter_label.pack(side=tk.LEFT, padx=5)

    def _on_key(self, event):
        if self.live_search_var.get():
            self.perform_search()

    def perform_search(self):
        query = self.search_var.get().strip()
        field = self.search_field_var.get()
        selected_chats = self.app.chat_panel.get_selected_chats()
        results = self.search_controller.search(query, field, selected_chats)
        if results:
            self.app.tree_panel.display_search_results(results)
        else:
            self.app.tree_panel.display_chats(selected_chats)
            self.counter_label.config(text="0 / 0")

    def prev_result(self):
        self.search_controller.prev()

    def next_result(self):
        self.search_controller.next()

    def clear(self):
        self.search_var.set("")
        self.perform_search()
        self.counter_label.config(text="0 / 0")