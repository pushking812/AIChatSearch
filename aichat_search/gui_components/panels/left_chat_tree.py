# aichat_search/gui_components/panels/left_chat_tree.py

import tkinter as tk
from tkinter import ttk
from typing import List, Dict
from datetime import datetime

from ..utils import format_datetime
from ...model import Chat

class LeftChatTree(tk.Frame):
    """Дерево чатов."""
    def __init__(self, parent, controller, on_select_callback, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.controller = controller
        self.on_select = on_select_callback
        self._item_to_chat: Dict[str, Chat] = {}

        self.tree = ttk.Treeview(
            self,
            columns=("name", "group", "msg_count", "updated"),
            show="tree headings",
            selectmode=tk.EXTENDED
        )
        self.tree.heading("name", text="Название")
        self.tree.heading("group", text="Группа")
        self.tree.heading("msg_count", text="Сообщ.")
        self.tree.heading("updated", text="Обновлён")

        self.tree.column("#0", width=25, stretch=False, minwidth=20)
        self.tree.column("name", width=250, anchor="w")
        self.tree.column("group", width=120, anchor="w")
        self.tree.column("msg_count", width=80, anchor="center")
        self.tree.column("updated", width=140, anchor="w")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind('<Double-1>', self._on_double_click_heading)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_select(self, event=None):
        self.on_select()

    def _on_double_click_heading(self, event):
        region = self.tree.identify_region(event.x, event.y)
        column = self.tree.identify_column(event.x)
        if region == "heading" and column == "#0":
            self._toggle_all_items()

    def _toggle_all_items(self):
        roots = self.tree.get_children('')
        if not roots:
            return
        all_open = all(self.tree.item(item, 'open') for item in roots)
        new_state = not all_open
        for item in roots:
            self.tree.item(item, open=new_state)

    def update_list(self, items: List):
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
        groups = {}
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
                display_date = format_datetime(chat.updated_at or chat.created_at)
                child_id = self.tree.insert( # child_id не используется, проверить # noqa
                    parent_id, "end",
                    values=(chat.title, chat.group or "", len(chat.pairs), display_date),
                    iid=unique_iid, tags=('chat',)
                )
                self._item_to_chat[unique_iid] = chat

    def _build_group_tree(self, items):
        groups = {}
        for chat, source_name, source_time in items:
            group_name = chat.group if chat.group else "Без группы"
            groups.setdefault(group_name, []).append((chat, source_name, source_time))

        for group_name in sorted(groups.keys()):
            parent_id = self.tree.insert("", "end", values=(group_name, "", "", ""),
                                         open=True, tags=('group',))
            for chat, source_name, source_time in groups[group_name]:
                unique_iid = f"{source_name}_{chat.id}"
                display_date = format_datetime(chat.updated_at or chat.created_at)
                child_id = self.tree.insert( # child_id не используется, проверить # noqa
                    parent_id, "end",
                    values=(chat.title, chat.group or "", len(chat.pairs), display_date),
                    iid=unique_iid, tags=('chat',)
                )
                self._item_to_chat[unique_iid] = chat

    def _build_prefix_tree(self, items):
        groups = {}
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
                display_date = format_datetime(chat.updated_at or chat.created_at)
                child_id = self.tree.insert( # child_id не используется, проверить # noqa
                    parent_id, "end",
                    values=(chat.title, chat.group or "", len(chat.pairs), display_date),
                    iid=unique_iid, tags=('chat',)
                )
                self._item_to_chat[unique_iid] = chat

    def get_selected_chats(self):
        selected_iids = self.tree.selection()
        selected_chat_iids = set()
        selected_group_iids = set()

        for iid in selected_iids:
            if iid in self._item_to_chat:
                selected_chat_iids.add(iid)
            else:
                selected_group_iids.add(iid)

        result_set = set()
        for iid in selected_chat_iids:
            result_set.add(self._item_to_chat[iid])

        for group_iid in selected_group_iids:
            child_iids = self.tree.get_children(group_iid)
            if not any(child_iid in selected_chat_iids for child_iid in child_iids):
                for child_iid in child_iids:
                    if child_iid in self._item_to_chat:
                        result_set.add(self._item_to_chat[child_iid])

        return list(result_set)

    def get_column_widths(self):
        widths = {}
        for col in ("name", "group", "msg_count", "updated"):
            widths[col] = self.tree.column(col, 'width')
        return widths

    def set_column_widths(self, widths):
        for col, width in widths.items():
            try:
                self.tree.column(col, width=width)
            except Exception:
                pass