# aichat_search/tools/code_structure/view.py

import tkinter as tk
from tkinter import ttk, messagebox


class CodeStructureWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Структура кода")
        self.geometry("800x600")
        self.transient(parent)
        self.grab_set()

        # Настраиваем сетку
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)
        self.rowconfigure(3, weight=1)  # строка 3 для дерева

        # Метки
        ttk.Label(self, text="Тип блока:").grid(row=0, column=0, padx=5, pady=(10,0), sticky="w")
        ttk.Label(self, text="Блок:").grid(row=0, column=1, padx=5, pady=(10,0), sticky="w")

        # Комбобоксы
        self.type_combo = ttk.Combobox(self, state="readonly", width=15)
        self.type_combo.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.block_combo = ttk.Combobox(self, state="readonly", width=50)
        self.block_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Кнопка "Показать структуру"
        self.show_button = ttk.Button(self, text="Показать структуру")
        self.show_button.grid(row=1, column=2, padx=5, pady=5, sticky="ew")

        # Панель управления раскрытием
        expand_frame = ttk.Frame(self)
        expand_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        ttk.Label(expand_frame, text="Уровень раскрытия:").pack(side=tk.LEFT, padx=(0,5))
        self.level_combo = ttk.Combobox(expand_frame, values=[str(i) for i in range(1,6)], width=5, state="readonly")
        self.level_combo.pack(side=tk.LEFT, padx=5)
        self.level_combo.current(0)  # по умолчанию уровень 1

        self.expand_button = ttk.Button(expand_frame, text="Развернуть до уровня", command=self._on_expand_to_level)
        self.expand_button.pack(side=tk.LEFT, padx=5)

        # Дерево
        self.tree = ttk.Treeview(self, columns=("type", "signature"), show="tree headings")
        self.tree.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")

        self.tree.heading("#0", text="Имя")
        self.tree.heading("type", text="Тип")
        self.tree.heading("signature", text="Сигнатура")

        self.tree.column("#0", width=300, minwidth=200, stretch=True)
        self.tree.column("type", width=100, minwidth=80, stretch=False)
        self.tree.column("signature", width=400, minwidth=200, stretch=True)

        # Скролл
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=3, column=3, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

    # ---------- Методы для комбобоксов ----------
    def set_type_combo_values(self, values):
        self.type_combo['values'] = values
        if values:
            self.type_combo.current(0)

    def set_block_combo_values(self, values):
        self.block_combo['values'] = values

    def set_current_block_index(self, index):
        if 0 <= index < len(self.block_combo['values']):
            self.block_combo.current(index)

    def get_selected_block_index(self):
        return self.block_combo.current()

    # ---------- Методы для дерева ----------
    def clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def display_structure(self, root_node):
        self.clear_tree()
        self._add_node("", root_node)
        self._expand_all("")  # по умолчанию раскрываем всё

    def _add_node(self, parent, node):
        item = self.tree.insert(parent, tk.END, text=node.name, values=(node.node_type, node.signature))
        for child in node.children:
            self._add_node(item, child)

    def _expand_all(self, parent):
        for child in self.tree.get_children(parent):
            self.tree.item(child, open=True)
            self._expand_all(child)

    def _expand_to_level(self, level, parent=""):
        """Раскрывает узлы до заданной глубины (1 – только корневые)."""
        for child in self.tree.get_children(parent):
            if level > 1:
                self.tree.item(child, open=True)
                self._expand_to_level(level-1, child)
            else:
                self.tree.item(child, open=False)

    def _on_expand_to_level(self):
        """Обработчик кнопки раскрытия до уровня."""
        try:
            level = int(self.level_combo.get())
            self._expand_to_level(level)
        except ValueError:
            pass

    def show_error(self, message):
        messagebox.showerror("Ошибка", message, parent=self)