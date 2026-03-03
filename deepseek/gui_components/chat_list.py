# deepseek/gui_components/chat_list.py

"""Панель списка чатов с фильтрацией и множественным выбором."""

import tkinter as tk
from tkinter import messagebox

class ChatListPanel:
    """Управляет списком чатов, фильтром и кнопками выбора."""

    def __init__(self, parent, controller, on_select_callback):
        """
        :param parent: родительский виджет (Frame)
        :param controller: экземпляр ChatController
        :param on_select_callback: вызывается при изменении выбора
        """
        self.controller = controller
        self.on_select = on_select_callback
        self.filter_var = tk.StringVar()

        self._create_widgets(parent)

    def _create_widgets(self, parent):
        # Заголовок
        tk.Label(parent, text="Чаты", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=5)

        # Поле фильтра
        self.filter_entry = tk.Entry(parent, textvariable=self.filter_var)
        self.filter_entry.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.filter_entry.bind("<KeyRelease>", self._on_filter_changed)

        # Контейнер для списка и скролла
        list_container = tk.Frame(parent)
        list_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.listbox = tk.Listbox(
            list_container,
            selectmode=tk.EXTENDED,
            exportselection=False
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_container, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

        # Привязка событий выбора
        self.listbox.bind("<ButtonRelease-1>", self._on_select)
        self.listbox.bind("<Shift-ButtonRelease-1>", self._on_select)
        self.listbox.bind("<Control-ButtonRelease-1>", self._on_select)

        # Кнопки выбора
        buttons_frame = tk.Frame(parent)
        buttons_frame.pack(pady=(0, 5))

        self.btn_select_all = tk.Button(
            buttons_frame,
            text="☑",
            width=3,
            command=self.select_all
        )
        self.btn_select_all.pack(side=tk.LEFT, padx=2)

        self.btn_clear = tk.Button(
            buttons_frame,
            text="[ ]",
            width=3,
            command=self.clear_selection
        )
        self.btn_clear.pack(side=tk.LEFT, padx=2)

    def update_list(self, chats=None):
        """Обновить отображение списка чатов."""
        if chats is None:
            chats = self.controller.get_filtered_chats()
        self.listbox.delete(0, tk.END)
        for chat in chats:
            self.listbox.insert(tk.END, chat.title)

    def get_selected_chats(self):
        """Вернуть список выбранных объектов Chat."""
        indices = self.listbox.curselection()
        if not indices:
            return []
        filtered = self.controller.get_filtered_chats()
        return [filtered[i] for i in indices if i < len(filtered)]

    def select_all(self):
        """Выбрать все чаты в списке."""
        self.listbox.selection_set(0, tk.END)
        self._on_select()

    def clear_selection(self):
        """Снять выделение со всех чатов."""
        self.listbox.selection_clear(0, tk.END)
        self._on_select()

    def _on_filter_changed(self, event=None):
        """Обработка изменения фильтра."""
        self.controller.filter_chats(self.filter_var.get())
        self.update_list()
        # Сброс выделения? Пользователь ожидает, что список обновится, а выделение останется.
        # Но лучше сбросить, чтобы избежать несоответствий.
        self.clear_selection()

    def _on_select(self, event=None):
        """Внутренний обработчик выбора – вызывает внешний callback."""
        self.on_select()
