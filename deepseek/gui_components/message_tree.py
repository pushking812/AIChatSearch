# deepseek/gui_components/message_tree.py

"""Панель дерева сообщений с отображением чатов и пар."""

import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Dict, Optional

from ..model import Chat, MessagePair


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


def _get_context(text: str, start: int, end: int, context_chars: int = 30) -> str:
    """
    Возвращает фрагмент текста вокруг позиции совпадения.
    Выделяет до context_chars символов слева и справа.
    """
    if not text:
        return ""
    left = max(0, start - context_chars)
    right = min(len(text), end + context_chars)
    prefix = "..." if left > 0 else ""
    suffix = "..." if right < len(text) else ""
    fragment = text[left:right]
    # Экранируем переносы строк
    fragment = _escape_newlines(fragment)
    return f"{prefix}{fragment}{suffix}"


class MessageTreePanel:
    """Отвечает за отображение сообщений в виде дерева с группировкой по чатам."""

    def __init__(self, parent, controller, on_select_callback):
        """
        :param parent: родительский виджет
        :param controller: ChatController
        :param on_select_callback: вызывается при выборе элемента
        """
        self.controller = controller
        self.on_select = on_select_callback
        self.tree_item_map: Dict[str, Tuple[Chat, MessagePair]] = {}  # item_id -> (chat, pair)
        self._internal_update = False
        self._search_mode = False  # флаг, показываем ли результаты поиска

        self._create_widgets(parent)

    def _create_widgets(self, parent):
        # Колонки: глобальный номер, номер в чате, запрос, ответ/контекст, дата
        self.tree = ttk.Treeview(
            parent,
            columns=("global_idx", "chat_idx", "request", "response", "date"),
            show="tree headings",
        )
        self.tree.heading("global_idx", text="№")
        self.tree.heading("chat_idx", text="В чате")
        self.tree.heading("request", text="Запрос")
        self.tree.heading("response", text="Ответ / Контекст")
        self.tree.heading("date", text="Дата")

        # Устанавливаем начальную ширину колонок (можно будет регулировать)
        self.tree.column("#0", width=25, stretch=False, minwidth=20)  # стрелки
        self.tree.column("global_idx", width=50, anchor="center")
        self.tree.column("chat_idx", width=60, anchor="center")
        self.tree.column("request", width=200, anchor="w")
        self.tree.column("response", width=300, anchor="w")
        self.tree.column("date", width=130, anchor="w")

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)

        scrollbar = tk.Scrollbar(parent, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def display_chats(self, chats: List[Chat]):
        """Отобразить все пары из выбранных чатов (обычный режим)."""
        self._clear()
        self._search_mode = False
        global_counter = 0

        for chat in chats:
            pairs = list(chat.get_pairs())
            # Сортируем пары по их индексу (по умолчанию они уже должны быть в порядке возрастания)
            # Можно явно отсортировать по числовому значению, если индекс – строка, содержащая число.
            # В модели index хранится как строка, но мы можем сортировать по int(index)
            try:
                pairs.sort(key=lambda p: int(p.index))
            except ValueError:
                # Если не число, оставляем как есть
                pass

            if not pairs:
                continue
            parent_text = f"{chat.title} ({len(pairs)} сообщ.)"
            parent_id = self.tree.insert("", "end", text=parent_text, open=True)

            for pair in pairs:
                global_counter += 1
                request_preview = _escape_newlines(pair.request_text[:50])
                if len(pair.request_text) > 50:
                    request_preview += "..."
                response_preview = _escape_newlines(pair.response_text[:50])
                if len(pair.response_text) > 50:
                    response_preview += "..."

                self._insert_pair(
                    parent_id,
                    chat,
                    pair,
                    global_idx=global_counter,
                    request_text=request_preview,
                    response_text=response_preview
                )

    def display_search_results(self, results: List[Tuple[Chat, MessagePair, str, int, int]]):
        """
        Отобразить результаты поиска с контекстом.
        results: список (chat, pair, field, start, end)
        """
        self._clear()
        self._search_mode = True
        global_counter = 0

        # Группируем по чатам для создания заголовков
        grouped = {}
        for chat, pair, field, start, end in results:
            if chat not in grouped:
                grouped[chat] = {'pairs': [], 'matches': 0}
            grouped[chat]['pairs'].append((pair, field, start, end))
            grouped[chat]['matches'] += 1

        for chat, data in grouped.items():
            # Сортируем пары по индексу
            try:
                data['pairs'].sort(key=lambda x: int(x[0].index))
            except ValueError:
                pass

            parent_text = f"{chat.title} ({len(data['pairs'])} сообщ. / {data['matches']} совпад.)"
            parent_id = self.tree.insert("", "end", text=parent_text, open=True)

            for pair, field, start, end in data['pairs']:
                global_counter += 1
                # Формируем контекст в зависимости от поля
                if field == "request":
                    full_text = pair.request_text
                else:  # field == "response" или любое другое (поиск по всему)
                    full_text = pair.response_text

                context = _get_context(full_text, start, end, context_chars=30)

                # Запрос показываем как обычно (первые 50 символов)
                request_preview = _escape_newlines(pair.request_text[:50])
                if len(pair.request_text) > 50:
                    request_preview += "..."

                self._insert_pair(
                    parent_id,
                    chat,
                    pair,
                    global_idx=global_counter,
                    request_text=request_preview,
                    response_text=context
                )

    def _insert_pair(self, parent_id, chat: Chat, pair: MessagePair,
                     global_idx: int, request_text: str, response_text: str):
        """Вспомогательный метод для вставки одной пары в дерево."""
        idx_display = str(pair.index) + ('*' if pair.modified else '')

        # Формируем дату (используем request_time)
        date_str = _format_datetime(pair.request_time)

        item_id = self.tree.insert(
            parent_id,
            "end",
            values=(
                global_idx,
                idx_display,
                request_text,
                response_text,
                date_str
            )
        )
        self.tree_item_map[item_id] = (chat, pair)

    def update_pair_item(self, pair):
        """Обновить отображение конкретной пары (после изменения)."""
        for item_id, (chat, p) in self.tree_item_map.items():
            if p is pair:
                idx_display = str(pair.index) + ('*' if pair.modified else '')
                current_values = self.tree.item(item_id, 'values')
                if current_values:
                    # Обновляем только вторую колонку (индекс в чате) и тексты запроса/ответа
                    request_preview = _escape_newlines(pair.request_text[:50])
                    if len(pair.request_text) > 50:
                        request_preview += "..."
                    response_preview = _escape_newlines(pair.response_text[:50])
                    if len(pair.response_text) > 50:
                        response_preview += "..."

                    new_values = (
                        current_values[0],  # global_idx не меняем
                        idx_display,
                        request_preview,
                        response_preview,
                        current_values[4]  # дату не меняем
                    )
                    self.tree.item(item_id, values=new_values)
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

    def _on_tree_select(self, event=None):
        """Внутренний обработчик выбора – вызывает внешний callback."""
        if self._internal_update:
            return
        self.on_select()

    def clear(self):
        """Удаляет все элементы из дерева."""
        self._clear()

    # ---------- Методы для сохранения ширины колонок ----------
    def get_column_widths(self) -> dict:
        """Возвращает словарь {имя_колонки: ширина} для всех колонок, кроме #0."""
        widths = {}
        for col in ("global_idx", "chat_idx", "request", "response", "date"):
            widths[col] = self.tree.column(col, 'width')
        return widths

    def set_column_widths(self, widths: dict):
        """Устанавливает ширину колонок из словаря."""
        for col, width in widths.items():
            try:
                self.tree.column(col, width=width)
            except Exception:
                pass