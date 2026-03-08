# aichat_search/gui_components/chat_list.py

"""Панель списка чатов с фильтрацией и множественным выбором (Treeview)."""

import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Dict, Optional
from datetime import datetime

from ..model import Chat


def _format_datetime(dt) -> str:
    """Форматирует datetime в строку 'ДД-ММ-ГГГГ ЧЧ:ММ'."""
    if dt:
        return dt.strftime("%d-%m-%Y %H:%M")
    return ""


class ChatListPanel:
    """Управляет списком чатов, фильтром и кнопками выбора."""

    def __init__(self, parent, controller, on_select_callback):
        self.controller = controller
        self.on_select = on_select_callback
        self.filter_var = tk.StringVar()
        self._item_to_chat: Dict[str, Chat] = {}
        self._create_widgets(parent)

    def _create_widgets(self, parent):
        tk.Label(parent, text="Чаты", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=5)

        self.filter_entry = tk.Entry(parent, textvariable=self.filter_var)
        self.filter_entry.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.filter_entry.bind("<KeyRelease>", self._on_filter_changed)

        tree_container = tk.Frame(parent)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Колонки: название, группа, кол-во сообщений, дата создания
        self.tree = ttk.Treeview(
            tree_container,
            columns=("name", "group", "msg_count", "created"),
            show="tree headings",
            selectmode=tk.EXTENDED
        )
        self.tree.heading("name", text="Название")
        self.tree.heading("group", text="Группа")
        self.tree.heading("msg_count", text="Сообщ.")
        self.tree.heading("created", text="Создан")

        self.tree.column("#0", width=25, stretch=False, minwidth=20)
        self.tree.column("name", width=250, anchor="w")
        self.tree.column("group", width=120, anchor="w")
        self.tree.column("msg_count", width=80, anchor="center")
        self.tree.column("created", width=140, anchor="w")

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind('<Double-1>', self._on_double_click_heading)

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

    # ---------- Построение дерева ----------
    def update_list(self, items: List[Tuple[Chat, str, Optional[str]]]):
        """Очищает и перестраивает дерево согласно текущему режиму группировки."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._item_to_chat.clear()

        mode = self.controller.get_grouping_mode()
        if mode == "source":
            self._build_source_tree(items)
        elif mode == "group":
            self._build_group_tree(items)
        elif mode == "prefix":
            self._build_prefix_tree(items)

    def _build_source_tree(self, items):
        """Группировка по источнику (исходное поведение)."""
        groups: Dict[str, dict] = {}
        for chat, source_name, source_time in items:
            if source_name not in groups:
                groups[source_name] = {'chats': [], 'time': source_time}
            groups[source_name]['chats'].append(chat)

        for source_name, group in groups.items():
            group['chats'].sort(key=lambda c: c.created_at or datetime.min, reverse=True)
            parent_id = self.tree.insert("", "end", values=(source_name, "", "", group['time']),
                                         open=True, tags=('group',))
            for chat in group['chats']:
                unique_iid = f"{source_name}_{chat.id}"
                created_str = _format_datetime(chat.created_at)
                child_id = self.tree.insert(
                    parent_id, "end",
                    values=(chat.title, chat.group or "", len(chat.pairs), created_str),
                    iid=unique_iid, tags=('chat',)
                )
                self._item_to_chat[unique_iid] = chat

    def _build_group_tree(self, items):
        """Группировка по пользовательским группам."""
        groups: Dict[str, List[Tuple[Chat, str, Optional[str]]]] = {}
        for chat, source_name, source_time in items:
            group_name = chat.group if chat.group else "Без группы"
            groups.setdefault(group_name, []).append((chat, source_name, source_time))

        for group_name in sorted(groups.keys()):
            parent_id = self.tree.insert("", "end", values=(group_name, "", "", ""),
                                         open=True, tags=('group',))
            for chat, source_name, source_time in groups[group_name]:
                unique_iid = f"{source_name}_{chat.id}"
                created_str = _format_datetime(chat.created_at)
                child_id = self.tree.insert(
                    parent_id, "end",
                    values=(chat.title, chat.group or "", len(chat.pairs), created_str),
                    iid=unique_iid, tags=('chat',)
                )
                self._item_to_chat[unique_iid] = chat

    def _build_prefix_tree(self, items):
        """Группировка по префиксу названия чата (до первого ':')."""
        groups: Dict[str, List[Tuple[Chat, str, Optional[str]]]] = {}
        for chat, source_name, source_time in items:
            title = chat.title
            if ':' in title:
                prefix = title.split(':', 1)[0].strip().upper() + ":"
            else:
                prefix = "БЕЗ ПРЕФИКСА"
            groups.setdefault(prefix, []).append((chat, source_name, source_time))

        for prefix in sorted(groups.keys()):
            parent_id = self.tree.insert("", "end", values=(prefix, "", "", ""),
                                         open=True, tags=('group',))
            for chat, source_name, source_time in groups[prefix]:
                unique_iid = f"{source_name}_{chat.id}"
                created_str = _format_datetime(chat.created_at)
                child_id = self.tree.insert(
                    parent_id, "end",
                    values=(chat.title, chat.group or "", len(chat.pairs), created_str),
                    iid=unique_iid, tags=('chat',)
                )
                self._item_to_chat[unique_iid] = chat

    # ---------- Получение выбранных чатов ----------
    def get_selected_chats(self) -> List[Chat]:
        """Возвращает список уникальных чатов, выбранных в дереве.

        Правила отбора:
        - Явно выделенные чаты всегда включаются.
        - Если выделена группа (источник, группа по префиксу, пользовательская группа)
          и при этом не выделен ни один из её дочерних чатов, то включаются все чаты этой группы.
        - Если выделена группа и одновременно выделены какие-то из её дочерних чатов,
          то группа игнорируется, включаются только явно выделенные чаты.
        - Дубликаты исключаются.
        """
        selected_iids = self.tree.selection()
        selected_chat_iids = set()
        selected_group_iids = set()

        # Разделяем выделенные элементы на чаты и группы
        for iid in selected_iids:
            if iid in self._item_to_chat:
                selected_chat_iids.add(iid)
            else:
                selected_group_iids.add(iid)

        result_set = set()

        # Добавляем все явно выделенные чаты
        for iid in selected_chat_iids:
            result_set.add(self._item_to_chat[iid])

        # Обрабатываем группы
        for group_iid in selected_group_iids:
            child_iids = self.tree.get_children(group_iid)
            # Проверяем, есть ли среди выделенных чатов дети этой группы
            if not any(child_iid in selected_chat_iids for child_iid in child_iids):
                # Если ни один ребёнок не выделен, добавляем всех детей группы
                for child_iid in child_iids:
                    if child_iid in self._item_to_chat:
                        result_set.add(self._item_to_chat[child_iid])

        return list(result_set)

    # ---------- Кнопки ----------
    def select_all(self):
        self.tree.selection_set(list(self._item_to_chat.keys()))
        self._on_select()

    def clear_selection(self):
        self.tree.selection_set(())
        self._on_select()

    # ---------- Обработчики ----------
    def _on_filter_changed(self, event=None):
        self.controller.filter_chats(self.filter_var.get())
        filtered = self.controller.get_filtered_chats()
        items = []
        for chat in filtered:
            source_name, source_time = self.controller.get_source_info(chat)
            items.append((chat, source_name, source_time))
        self.update_list(items)
        self.clear_selection()

    def _on_select(self, event=None):
        self.on_select()

    # ---------- Методы для сохранения ширины колонок ----------
    def get_column_widths(self) -> dict:
        widths = {}
        for col in ("name", "group", "msg_count", "created"):
            widths[col] = self.tree.column(col, 'width')
        return widths

    def set_column_widths(self, widths: dict):
        for col, width in widths.items():
            try:
                self.tree.column(col, width=width)
            except Exception:
                pass
                
    def _toggle_all_items(self):
        """Переключает состояние всех корневых элементов дерева: если все открыты – закрывает, иначе открывает."""
        roots = self.tree.get_children('')
        if not roots:
            return
        # Проверяем, все ли открыты
        all_open = all(self.tree.item(item, 'open') for item in roots)
        new_state = not all_open
        for item in roots:
            self.tree.item(item, open=new_state)

    def _on_double_click_heading(self, event):
        """Обрабатывает двойной щелчок мыши по заголовку колонки #0."""
        # Определяем регион и колонку под курсором
        region = self.tree.identify_region(event.x, event.y)
        column = self.tree.identify_column(event.x)
        if region == "heading" and column == "#0":
            self._toggle_all_items()            
           