# code_structure/dialogs/ambiguity/ambiguity_dialog.py

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Optional

from code_structure.dialogs.dialog_interfaces import AmbiguityView
from code_structure.dialogs.ambiguity.ambiguity_presenter import AmbiguityPresenter
from code_structure.dialogs.dto import AmbiguityInfo


class AmbiguityDialog(tk.Toplevel, AmbiguityView):
    def __init__(self, parent, ambiguities: List[AmbiguityInfo]):
        super().__init__(parent)
        self.title("Проверка и корректировка путей модулей")
        self.geometry("850x500")
        self.transient(parent)
        self.grab_set()

        self.presenter = AmbiguityPresenter(self, ambiguities)
        self._create_widgets()
        self.presenter.initialize()

        self.result = None

    def _create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Для следующих идентификаторов найдены пути к модулям.\n"
                                   "Двойной клик по строке для изменения пути. Вы можете выбрать из списка или ввести свой вариант.").pack(anchor=tk.W, pady=5)

        # Таблица
        self.tree = ttk.Treeview(main_frame, columns=("candidates", "selected"), show="tree headings")
        self.tree.heading("#0", text="Имя")
        self.tree.heading("candidates", text="Возможные пути (через запятую)")
        self.tree.heading("selected", text="Выбранный путь")
        self.tree.column("#0", width=150)
        self.tree.column("candidates", width=400)
        self.tree.column("selected", width=250)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=5)

        # Кнопки
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        self.ok_button = ttk.Button(btn_frame, text="OK", command=self._ok)
        self.ok_button.pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Отмена", command=self._cancel).pack(side=tk.RIGHT, padx=5)

        self.tree.bind("<Double-1>", self._on_double_click)

    def set_ambiguities(self, ambiguities: List[AmbiguityInfo]):
        for amb in ambiguities:
            candidates_str = ", ".join(amb.candidates)
            # По умолчанию выбираем первый кандидат
            default_selected = amb.candidates[0] if amb.candidates else ""
            node = self.tree.insert("", tk.END, text=amb.name, values=(candidates_str, default_selected))
            self.tree.set(node, "candidates", candidates_str)
            self.tree.set(node, "selected", default_selected)

    def get_selected_path(self, name: str) -> Optional[str]:
        for item in self.tree.get_children():
            if self.tree.item(item, "text") == name:
                selected = self.tree.set(item, "selected")
                return selected if selected else None
        return None

    def _on_double_click(self, event):
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            name = self.tree.item(item, "text")
            candidates_str = self.tree.set(item, "candidates")
            candidates = [c.strip() for c in candidates_str.split(",")] if candidates_str else []
            current_selected = self.tree.set(item, "selected")

            # Диалог выбора/ввода
            dialog = tk.Toplevel(self)
            dialog.title(f"Редактирование пути для '{name}'")
            dialog.geometry("500x200")
            dialog.transient(self)
            dialog.grab_set()

            tk.Label(dialog, text=f"Путь для '{name}':").pack(pady=10)
            combo = ttk.Combobox(dialog, values=candidates, width=60)
            combo.pack(pady=5)
            if current_selected:
                combo.set(current_selected)
            elif candidates:
                combo.set(candidates[0])
            combo.focus_set()

            result = [None]

            def on_ok():
                val = combo.get().strip()
                if val:
                    result[0] = val
                dialog.destroy()

            def on_cancel():
                dialog.destroy()

            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(pady=15)
            ttk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=20)
            ttk.Button(btn_frame, text="Отмена", command=on_cancel).pack(side=tk.RIGHT, padx=20)

            self.wait_window(dialog)
            if result[0]:
                self.tree.set(item, "selected", result[0])

    def close(self, result: Optional[Dict[str, str]]):
        self.result = result
        self.destroy()

    def show_error(self, message: str):
        messagebox.showerror("Ошибка", message, parent=self)

    def _ok(self):
        self.presenter.on_ok()

    def _cancel(self):
        self.presenter.on_cancel()