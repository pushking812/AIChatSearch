# deepseek/gui_components/message_tree.py

"""Панель дерева сообщений с отображением чатов и пар."""

import tkinter as tk
from tkinter import ttk

class MessageTreePanel:
    """Отвечает за отображение сообщений в виде дерева."""

    def __init__(self, parent, controller, on_select_callback):
        """
        :param parent: родительский виджет
        :param controller: ChatController
        :param on_select_callback: вызывается при выборе элемента
        """
        self.controller = controller
        self.on_select = on_select_callback
        self.tree_item_map = {}  # item_id -> (chat, pair)
        self._internal_update = False

        self._create_widgets(parent)

    def _create_widgets(self, parent):
        self.tree = ttk.Treeview(
            parent,
            columns=("idx", "request", "response"),
            show="tree headings",
        )
        self.tree.heading("idx", text="#")
        self.tree.heading("request", text="Запрос")
        self.tree.heading("response", text="Ответ")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)

        scrollbar = tk.Scrollbar(parent, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def display_chats(self, chats):
        """Отобразить все пары из выбранных чатов."""
        self._clear()
        for chat in chats:
            pairs = list(chat.get_pairs())
            if not pairs:
                continue
            parent_text = f"{chat.title} ({len(pairs)} msgs / 0 matches)"
            parent_id = self.tree.insert("", "end", text=parent_text)
            for pair in pairs:
                self._insert_pair(parent_id, chat, pair)

    def display_search_results(self, results):
        """
        Отобразить результаты поиска (группировка по чатам).
        results: список (chat, pair, field, start, end)
        """
        self._clear()
        grouped = {}
        for chat, pair, _, _, _ in results:
            if chat not in grouped:
                grouped[chat] = {'pairs': set(), 'matches': 0}
            grouped[chat]['pairs'].add(pair)
            grouped[chat]['matches'] += 1

        for chat, data in grouped.items():
            pairs = sorted(data['pairs'], key=lambda p: int(p.index))
            matches = data['matches']
            parent_text = f"{chat.title} ({len(pairs)} msgs / {matches} matches)"
            parent_id = self.tree.insert("", "end", text=parent_text)
            for pair in pairs:
                self._insert_pair(parent_id, chat, pair)

    def update_pair_item(self, pair):
        """Обновить отображение конкретной пары (после изменения)."""
        for item_id, (chat, p) in self.tree_item_map.items():
            if p is pair:
                idx_display = str(pair.index) + ('*' if pair.modified else '')
                self.tree.item(item_id, values=(
                    idx_display,
                    pair.request_text[:30],
                    pair.response_text[:30]
                ))
                break

    def get_selected_pair(self):
        """Вернуть (chat, pair) для выбранного элемента или None."""
        selection = self.tree.selection()
        if not selection:
            return None
        item_id = selection[0]
        return self.tree_item_map.get(item_id)

    def select_item_by_pair(self, chat, pair):
        """Выбрать элемент, соответствующий паре (если существует)."""
        for item_id, (c, p) in self.tree_item_map.items():
            if c == chat and p == pair:
                if item_id not in self.tree.selection():
                    self._internal_update = True
                    self.tree.selection_set(item_id)
                    self.tree.see(item_id)
                    self._internal_update = False
                return True
        return False

    def _clear(self):
        """Очистить дерево и карту."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree_item_map.clear()

    def _insert_pair(self, parent_id, chat, pair):
        """Вставить пару в дерево и сохранить в карту."""
        idx_display = str(pair.index) + ('*' if pair.modified else '')
        item_id = self.tree.insert(
            parent_id,
            "end",
            values=(
                idx_display,
                pair.request_text[:30],
                pair.response_text[:30],
            )
        )
        self.tree_item_map[item_id] = (chat, pair)

    def _on_tree_select(self, event=None):
        """Внутренний обработчик выбора – вызывает внешний callback."""
        if self._internal_update:
            return
        self.on_select()
