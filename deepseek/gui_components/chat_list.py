# deepseek/gui_components/chat_list.py

"""Панель списка чатов с фильтрацией и множественным выбором (Treeview)."""

import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Dict

from ..model import Chat


class ChatListPanel:
    """Управляет списком чатов, фильтром и кнопками выбора с использованием Treeview."""

    def __init__(self, parent, controller, on_select_callback):
        self.controller = controller
        self.on_select = on_select_callback
        self.filter_var = tk.StringVar()

        # Словарь для быстрого поиска чата по iid элемента дерева
        self._item_to_chat: Dict[str, Chat] = {}

        self._create_widgets(parent)

    def _create_widgets(self, parent):
        # Заголовок
        tk.Label(parent, text="Чаты", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=5)

        # Поле фильтра
        self.filter_entry = tk.Entry(parent, textvariable=self.filter_var)
        self.filter_entry.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.filter_entry.bind("<KeyRelease>", self._on_filter_changed)

        # Контейнер для дерева и скролла
        tree_container = tk.Frame(parent)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tree = ttk.Treeview(
            tree_container,
            columns=("source", "title"),
            show="tree headings",
            selectmode=tk.EXTENDED
        )
        self.tree.heading("source", text="Источник")
        self.tree.heading("title", text="Название чата")

        self.tree.column("#0", width=25, stretch=False, minwidth=20)
        self.tree.column("source", width=150, anchor="w")
        self.tree.column("title", width=250, anchor="w")

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

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

    def update_list(self, items: List[Tuple[Chat, str]]):
        """
        Обновляет отображение списка чатов с группировкой по источникам.
        items: список кортежей (chat, source_name)
        """
        # Очищаем дерево и словарь
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._item_to_chat.clear()

        # Группируем чаты по источнику
        groups: Dict[str, List[Chat]] = {}
        for chat, source_name in items:
            groups.setdefault(source_name, []).append(chat)

        # Создаём элементы дерева
        for source_name, chat_list in groups.items():
            # Создаём родительский элемент (группу)
            parent_id = self.tree.insert(
                "",
                "end",
                values=(source_name, ""),
                open=True
            )
            # Добавляем чаты как дочерние элементы
            for chat in chat_list:
                # Уникальный iid на основе имени источника и ID чата
                unique_iid = f"{source_name}_{chat.id}"
                # Добавляем количество сообщений к названию для наглядности
                display_title = f"{chat.title} ({len(chat.pairs)} сообщ.)"
                child_id = self.tree.insert(
                    parent_id,
                    "end",
                    values=(source_name, display_title),
                    iid=unique_iid
                )
                self._item_to_chat[unique_iid] = chat

    def get_selected_chats(self) -> List[Chat]:
        """Вернуть список выбранных объектов Chat (только чаты, не группы)."""
        selected_iids = self.tree.selection()
        result = []
        for iid in selected_iids:
            chat = self._item_to_chat.get(iid)
            if chat is not None:
                result.append(chat)
        return result

    def select_all(self):
        """Выбрать все чаты в списке (группы не выбираются)."""
        self.tree.selection_set(list(self._item_to_chat.keys()))
        self._on_select()

    def clear_selection(self):
        """Снять выделение со всех элементов."""
        self.tree.selection_set(())
        self._on_select()

    def _on_filter_changed(self, event=None):
        """Обработка изменения фильтра."""
        self.controller.filter_chats(self.filter_var.get())
        filtered = self.controller.get_filtered_chats()
        items = [(chat, self.controller.get_source_name(chat)) for chat in filtered]
        self.update_list(items)
        self.clear_selection()

    def _on_select(self, event=None):
        """Внутренний обработчик выбора – вызывает внешний callback."""
        self.on_select()