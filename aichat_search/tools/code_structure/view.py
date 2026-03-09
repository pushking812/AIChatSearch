# aichat_search/tools/code_structure/view.py

import tkinter as tk
from tkinter import ttk, messagebox


class CodeStructureWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Структура кода")
        self.geometry("700x500")
        self.transient(parent)
        self.grab_set()

        # Настраиваем сетку
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)
        self.rowconfigure(2, weight=1)

        # Метки
        ttk.Label(self, text="Тип блока:").grid(row=0, column=0, padx=5, pady=(10, 0), sticky="w")
        ttk.Label(self, text="Блок:").grid(row=0, column=1, padx=5, pady=(10, 0), sticky="w")

        # Комбобоксы
        self.type_combo = ttk.Combobox(self, state="readonly", width=15)
        self.type_combo.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.block_combo = ttk.Combobox(self, state="readonly", width=50)
        self.block_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Кнопка
        self.show_button = ttk.Button(self, text="Показать структуру")
        self.show_button.grid(row=1, column=2, padx=5, pady=5, sticky="ew")

        # Дерево
        self.tree = ttk.Treeview(self, columns=("type", "name", "signature"), show="tree headings")
        self.tree.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")

        self.tree.heading("type", text="Тип")
        self.tree.heading("name", text="Имя")
        self.tree.heading("signature", text="Сигнатура")

        self.tree.column("#0", width=0, stretch=False)
        self.tree.column("type", width=100)
        self.tree.column("name", width=200)
        self.tree.column("signature", width=300)

        # Скролл для дерева
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=2, column=3, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

    def set_type_combo_values(self, values):
        """Устанавливает значения для первого комбобокса."""
        self.type_combo['values'] = values
        if values:
            self.type_combo.current(0)

    def set_block_combo_values(self, values):
        """Устанавливает значения для второго комбобокса."""
        self.block_combo['values'] = values

    def set_current_block_index(self, index):
        """Выбирает элемент во втором комбобоксе по индексу."""
        if 0 <= index < len(self.block_combo['values']):
            self.block_combo.current(index)

    def show_error(self, message):
        """Показывает сообщение об ошибке."""
        messagebox.showerror("Ошибка", message, parent=self)
        
    def clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def display_structure(self, root_node):
        self.clear_tree()
        self._add_node("", root_node)

    def _add_node(self, parent, node):
        item = self.tree.insert(parent, tk.END,
                                values=(node.node_type, node.name, node.signature))
        for child in node.children:
            self._add_node(item, child)
            
    def get_selected_block_index(self):
        return self.block_combo.current()