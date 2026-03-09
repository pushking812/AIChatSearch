# aichat_search/gui_components/group_handler.py

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Callable

from .group_dialog import GroupDialog
from ..model import Chat


class GroupHandler:
    """Обрабатывает операции с группами на уровне GUI: открытие диалогов управления и назначения."""

    def __init__(self, parent, controller):
        """
        :param parent: родительское окно (tk.Tk или tk.Toplevel)
        :param controller: экземпляр ChatController для доступа к данным групп
        """
        self.parent = parent
        self.controller = controller

    def open_group_dialog(self, on_update_callback: Optional[Callable] = None):
        """Открывает диалог управления группами (создание, переименование, удаление)."""
        GroupDialog(self.parent, self.controller, on_update_callback or self._dummy_callback)

    def assign_group_to_selected(self, selected_chats: List[Chat], on_update_callback: Optional[Callable] = None):
        """Открывает диалог выбора группы для назначения выбранным чатам."""
        if not selected_chats:
            messagebox.showwarning("Назначение группы", "Нет выбранных чатов.", parent=self.parent)
            return

        groups = self.controller.get_all_groups()
        dialog = tk.Toplevel(self.parent)
        dialog.title("Выберите группу")
        dialog.geometry("300x200")
        dialog.transient(self.parent)
        dialog.grab_set()

        tk.Label(dialog, text="Группа:").pack(pady=5)
        var = tk.StringVar()
        combobox = ttk.Combobox(dialog, textvariable=var, values=[""] + groups, state="readonly")
        combobox.pack(pady=5)

        def on_ok():
            group = var.get().strip()
            if group == "":
                group = None
            self.controller.assign_group_to_chats(selected_chats, group)
            if on_update_callback:
                on_update_callback()
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Отмена", command=on_cancel).pack(side=tk.LEFT, padx=5)

    def _dummy_callback(self):
        """Пустой колбэк по умолчанию."""
        pass