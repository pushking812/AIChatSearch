# deepseek/gui_components/chat_list.py

"""Панель списка чатов с фильтрацией и множественным выбором (Treeview)."""

import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Dict, Optional

from ..model import Chat


def _format_datetime(dt) -> str:
    """Форматирует datetime в строку 'YYYY-MM-DD HH:MM' или возвращает пустую строку."""
    if dt:
        return dt.strftime("%Y-%m-%d %H:%M")
    return ""


class ChatListPanel:
    """Управляет списком чатов, фильтром и кнопками выбора с использованием Treeview."""

    def __init__(self, parent, controller, on_select_callback):
        self.controller = controller
        self.on_select = on_select_callback
        self.filter_var = tk.StringVar()

        # Словарь для быстрого поиска чата по iid элемента дерева (только для листьев)
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

        # Колонки: источник, название чата, кол-во сообщений, дата создания
        self.tree = ttk.Treeview(
            tree_container,
            columns=("source", "chat", "msg_count", "created"),
            show="tree headings",
            selectmode=tk.EXTENDED
        )
        self.tree.heading("source", text="Источник")
        self.tree.heading("chat", text="Чат")
        self.tree.heading("msg_count", text="Сообщений")
        self.tree.heading("created", text="Создан")

        # Настройка ширины колонок
        self.tree.column("#0", width=25, stretch=False, minwidth=20)   # стрелки
        self.tree.column("source", width=150, anchor="w")
        self.tree.column("chat", width=250, anchor="w")
        self.tree.column("msg_count", width=80, anchor="center")
        self.tree.column("created", width=140, anchor="w")

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Скроллбар
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

    def update_list(self, items: List[Tuple[Chat, str, Optional[str]]]):
        """
        Обновляет отображение списка чатов с группировкой по источникам.
        items: список кортежей (chat, source_name, source_time)
               source_time – строка с датой/временем файла источника.
        """
        # Очищаем дерево и словарь
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._item_to_chat.clear()

        # Группируем чаты по источнику, сохраняя время файла (берём из первого чата группы)
        groups: Dict[str, dict] = {}
        for chat, source_name, source_time in items:
            if source_name not in groups:
                groups[source_name] = {
                    'chats': [],
                    'time': source_time
                }
            groups[source_name]['chats'].append(chat)

        # Создаём элементы дерева
        for source_name, group in groups.items():
            # Родительский элемент (группа-источник)
            parent_id = self.tree.insert(
                "",
                "end",
                values=(source_name, "", "", group['time']),
                open=True,
                tags=('group',)
            )
            # Дочерние элементы (чаты)
            for chat in group['chats']:
                # Уникальный iid на основе имени источника и ID чата
                unique_iid = f"{source_name}_{chat.id}"
                # Форматируем дату создания чата
                created_str = _format_datetime(chat.created_at)
                child_id = self.tree.insert(
                    parent_id,
                    "end",
                    values=("", chat.title, len(chat.pairs), created_str),
                    iid=unique_iid,
                    tags=('chat',)
                )
                self._item_to_chat[unique_iid] = chat

    def get_selected_chats(self) -> List[Chat]:
        """
        Возвращает список объектов Chat, соответствующих выбранным элементам.
        Если выбран элемент группы, включаются все чаты этой группы.
        """
        selected_iids = self.tree.selection()
        result = []
        for iid in selected_iids:
            # Проверяем, является ли элемент чатом (присутствует в _item_to_chat)
            chat = self._item_to_chat.get(iid)
            if chat is not None:
                result.append(chat)
            else:
                # Это группа – собираем все дочерние чаты
                children = self.tree.get_children(iid)
                for child_iid in children:
                    child_chat = self._item_to_chat.get(child_iid)
                    if child_chat is not None:
                        result.append(child_chat)
        return result

    def select_all(self):
        """Выбрать все чаты во всех группах."""
        all_chat_iids = list(self._item_to_chat.keys())
        self.tree.selection_set(all_chat_iids)
        self._on_select()

    def clear_selection(self):
        """Снять выделение со всех элементов."""
        self.tree.selection_set(())
        self._on_select()

    def _on_filter_changed(self, event=None):
        """Обработка изменения фильтра."""
        self.controller.filter_chats(self.filter_var.get())
        filtered = self.controller.get_filtered_chats()
        items = []
        for chat in filtered:
            source_name, source_time = self.controller.get_source_info(chat)
            items.append((chat, source_name, source_time))
        self.update_list(items)
        self.clear_selection()

    def _on_select(self, event=None):
        """Внутренний обработчик выбора – вызывает внешний callback."""
        self.on_select()