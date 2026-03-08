# aichat_search/gui_components/message_tree.py

"""Панель дерева сообщений с отображением чатов и пар."""

import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Dict, Optional

from ..model import Chat, MessagePair
from . import constants


def _format_datetime(dt) -> str:
    """Форматирует datetime в строку 'ДД-ММ-ГГГГ ЧЧ:ММ' или возвращает пустую строку."""
    if dt:
        return dt.strftime("%d-%m-%Y %H:%M")
    return ""


def _escape_newlines(text: str) -> str:
    """Заменяет символы перевода строки на видимые последовательности '\n'."""
    if not text:
        return ""
    return text.replace('\n', '\\n')


def _get_context(text: str, start: int, end: int) -> str:
    """
    Возвращает фрагмент текста вокруг позиции совпадения.
    Выделяет до CONTEXT_CHARS символов слева и справа.
    """
    if not text:
        return ""
    context_chars = constants.CONTEXT_CHARS
    left = max(0, start - context_chars)
    right = min(len(text), end + context_chars)
    prefix = "..." if left > 0 else ""
    suffix = "..." if right < len(text) else ""
    fragment = text[left:right]
    fragment = _escape_newlines(fragment)
    return f"{prefix}{fragment}{suffix}"


class MessageTreePanel:
    """Отвечает за отображение сообщений в виде дерева с группировкой по чатам."""

    def __init__(self, parent, controller, on_select_callback):
        self.controller = controller
        self.on_select = on_select_callback
        # Карта: iid -> (chat, pair, field, start, end)
        self.tree_item_map: Dict[str, Tuple[Chat, MessagePair, Optional[str], Optional[int], Optional[int]]] = {}
        self._internal_update = False
        self._search_mode = False

        self._create_widgets(parent)

    def _create_widgets(self, parent):
        # Колонки: глобальный номер, источник, номер в чате, запрос, ответ/контекст, дата
        self.tree = ttk.Treeview(
            parent,
            columns=("global_idx", "source", "chat_idx", "request", "response", "date"),
            show="tree headings",
        )
        self.tree.heading("global_idx", text="№")
        self.tree.heading("source", text="Источник")
        self.tree.heading("chat_idx", text="В чате")
        self.tree.heading("request", text="Запрос")
        self.tree.heading("response", text="Ответ / Контекст")
        self.tree.heading("date", text="Дата")

        # Устанавливаем начальную ширину колонок
        self.tree.column("#0", width=20, stretch=False, minwidth=20)  # только стрелки
        self.tree.column("global_idx", width=50, anchor="center")
        self.tree.column("source", width=120, anchor="w")
        self.tree.column("chat_idx", width=60, anchor="center")
        self.tree.column("request", width=200, anchor="w")
        self.tree.column("response", width=300, anchor="w")
        self.tree.column("date", width=130, anchor="w")

        # Упаковываем дерево
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)

        scrollbar = tk.Scrollbar(parent, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=scrollbar.set)

        # Привязка событий
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind('<Double-1>', self._on_double_click_heading)

    def display_chats(self, chats: List[Chat]):
        """Отобразить все пары из выбранных чатов (обычный режим)."""
        self._clear()
        self._search_mode = False
        global_counter = 0
        preview_chars = constants.PREVIEW_CHARS

        for chat in chats:
            pairs = list(chat.get_pairs())
            try:
                pairs.sort(key=lambda p: int(p.index))
            except ValueError:
                pass

            if not pairs:
                continue
            parent_text = f"{chat.title} ({len(pairs)} сообщ.)"
            parent_id = self.tree.insert(
                "",
                "end",
                values=("", "", "", parent_text, "", ""),
                open=True
            )

            # Получаем имя источника для этого чата
            source_name, _ = self.controller.get_source_info(chat)

            for pair in pairs:
                global_counter += 1
                request_preview = _escape_newlines(pair.request_text[:preview_chars])
                if len(pair.request_text) > preview_chars:
                    request_preview += "..."
                response_preview = _escape_newlines(pair.response_text[:preview_chars])
                if len(pair.response_text) > preview_chars:
                    response_preview += "..."

                # Уникальный iid для каждой пары
                unique_iid = f"{id(chat)}_{pair.index}"
                self._insert_pair(
                    parent_id,
                    chat,
                    pair,
                    global_idx=global_counter,
                    source_name=source_name,
                    request_text=request_preview,
                    response_text=response_preview,
                    field=None,
                    start=None,
                    end=None,
                    iid=unique_iid
                )

    def display_search_results(self, results: List[Tuple[Chat, MessagePair, str, int, int]]):
        """Отобразить результаты поиска с контекстом."""
        self._clear()
        self._search_mode = True
        global_counter = 0
        preview_chars = constants.PREVIEW_CHARS

        grouped = {}
        for chat, pair, field, start, end in results:
            if chat not in grouped:
                grouped[chat] = {'pairs': [], 'matches': 0}
            grouped[chat]['pairs'].append((pair, field, start, end))
            grouped[chat]['matches'] += 1

        for chat, data in grouped.items():
            try:
                data['pairs'].sort(key=lambda x: int(x[0].index))
            except ValueError:
                pass

            parent_text = f"{chat.title} ({len(data['pairs'])} сообщ. / {data['matches']} совпад.)"
            parent_id = self.tree.insert(
                "",
                "end",
                values=("", "", "", parent_text, "", ""),
                open=True
            )

            # Получаем имя источника для этого чата
            source_name, _ = self.controller.get_source_info(chat)

            for pair, field, start, end in data['pairs']:
                global_counter += 1
                if field == "request":
                    full_text = pair.request_text
                else:
                    full_text = pair.response_text

                context = _get_context(full_text, start, end)

                request_preview = _escape_newlines(pair.request_text[:preview_chars])
                if len(pair.request_text) > preview_chars:
                    request_preview += "..."

                # Уникальный iid для каждой строки поиска
                unique_iid = f"{chat.id}_{pair.index}_{start}_{end}"
                self._insert_pair(
                    parent_id,
                    chat,
                    pair,
                    global_idx=global_counter,
                    source_name=source_name,
                    request_text=request_preview,
                    response_text=context,
                    field=field,
                    start=start,
                    end=end,
                    iid=unique_iid
                )

    def _insert_pair(self, parent_id, chat: Chat, pair: MessagePair,
                     global_idx: int, source_name: str, request_text: str, response_text: str,
                     field: Optional[str], start: Optional[int], end: Optional[int],
                     iid: str):
        """Вспомогательный метод для вставки одной пары в дерево."""
        idx_display = str(pair.index) + ('*' if pair.modified else '')
        date_str = _format_datetime(pair.request_time)

        item_id = self.tree.insert(
            parent_id,
            "end",
            values=(
                global_idx,
                source_name,
                idx_display,
                request_text,
                response_text,
                date_str
            ),
            iid=iid
        )
        self.tree_item_map[item_id] = (chat, pair, field, start, end)

    def update_pair_item(self, pair):
        """Обновить отображение конкретной пары (после изменения)."""
        preview_chars = constants.PREVIEW_CHARS
        for item_id, (chat, p, field, start, end) in self.tree_item_map.items():
            if p is pair:
                idx_display = str(pair.index) + ('*' if pair.modified else '')
                current_values = self.tree.item(item_id, 'values')
                if current_values:
                    request_preview = _escape_newlines(pair.request_text[:preview_chars])
                    if len(pair.request_text) > preview_chars:
                        request_preview += "..."
                    response_preview = _escape_newlines(pair.response_text[:preview_chars])
                    if len(pair.response_text) > preview_chars:
                        response_preview += "..."

                    # Сохраняем источник (второй элемент) без изменений
                    new_values = (
                        current_values[0],  # global_idx
                        current_values[1],  # source (без изменений)
                        idx_display,
                        request_preview,
                        response_preview,
                        current_values[5]   # date
                    )
                    self.tree.item(item_id, values=new_values)
                break

    def get_selected_item(self):
        """Вернуть (chat, pair, field, start, end) для выбранного элемента или None."""
        selection = self.tree.selection()
        if not selection:
            return None
        item_id = selection[0]
        return self.tree_item_map.get(item_id)

    def get_selected_pairs(self) -> List[Tuple[Chat, MessagePair]]:
        """Вернуть список (chat, pair) для всех выбранных элементов (только сообщения)."""
        selected_iids = self.tree.selection()
        result = []
        for iid in selected_iids:
            item = self.tree_item_map.get(iid)
            if item is not None:
                chat, pair, _, _, _ = item
                result.append((chat, pair))
        return result

    def _clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree_item_map.clear()

    def _on_tree_select(self, event=None):
        if self._internal_update:
            return
        self.on_select()

    def clear(self):
        self._clear()

    # ---------- Сворачивание/разворачивание всех ----------
    def _toggle_all_items(self):
        roots = self.tree.get_children('')
        if not roots:
            return
        all_open = all(self.tree.item(item, 'open') for item in roots)
        new_state = not all_open
        for item in roots:
            self.tree.item(item, open=new_state)

    def _on_double_click_heading(self, event):
        region = self.tree.identify_region(event.x, event.y)
        column = self.tree.identify_column(event.x)
        if region == "heading" and column == "#0":
            self._toggle_all_items()

    # ---------- Методы для сохранения ширины колонок ----------
    def get_column_widths(self) -> dict:
        widths = {}
        for col in ("global_idx", "source", "chat_idx", "request", "response", "date"):
            widths[col] = self.tree.column(col, 'width')
        return widths

    def set_column_widths(self, widths: dict):
        for col, width in widths.items():
            try:
                self.tree.column(col, width=width)
            except Exception:
                pass