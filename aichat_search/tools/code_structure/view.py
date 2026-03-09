# aichat_search/tools/code_structure/view.py

import tkinter as tk
from tkinter import ttk


class CodeStructureWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Структура кода")
        self.geometry("700x500")
        self.transient(parent)
        self.grab_set()  # делаем окно модальным

        # Настраиваем сетку
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)  # колонка для кнопки не растягивается
        self.rowconfigure(2, weight=1)      # дерево должно расширяться

        # Метки (строка 0)
        ttk.Label(self, text="Тип блока:").grid(row=0, column=0, padx=5, pady=(10, 0), sticky="w")
        ttk.Label(self, text="Блок:").grid(row=0, column=1, padx=5, pady=(10, 0), sticky="w")

        # Комбобоксы и кнопка (строка 1)
        self.type_combo = ttk.Combobox(self, state="readonly", width=15)
        self.type_combo.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.block_combo = ttk.Combobox(self, state="readonly", width=50)
        self.block_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.show_button = ttk.Button(self, text="Показать структуру")
        self.show_button.grid(row=1, column=2, padx=5, pady=5, sticky="ew")

        # Дерево для структуры (строка 2, занимает все колонки)
        self.tree = ttk.Treeview(self, columns=("type", "name", "signature"), show="tree headings")
        self.tree.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")

        # Настройка заголовков и колонок
        self.tree.heading("type", text="Тип")
        self.tree.heading("name", text="Имя")
        self.tree.heading("signature", text="Сигнатура")

        self.tree.column("#0", width=0, stretch=False)  # скрываем стандартную колонку
        self.tree.column("type", width=100)
        self.tree.column("name", width=200)
        self.tree.column("signature", width=300)

        # Скролл для дерева
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=2, column=3, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)