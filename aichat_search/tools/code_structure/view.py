# aichat_search/tools/code_structure/view.py

import tkinter as tk
from tkinter import ttk, messagebox
from chlorophyll import CodeView
import pygments.lexers


class CodeStructureWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Структура кода")
        self.geometry("1200x700")
        self.transient(parent)
        self.grab_set()

        # Контроллер для обратных вызовов
        self.controller = None

        # Словарь для маппинга элементов дерева в узлы
        self._item_to_node = {}

        # Настраиваем сетку: 4 строки
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)
        self.columnconfigure(3, weight=0)
        self.rowconfigure(3, weight=1)

        # ---- Строка 0: метки ----
        ttk.Label(self, text="Тип блока:").grid(row=0, column=0, padx=5, pady=(10,0), sticky="w")
        ttk.Label(self, text="Блок:").grid(row=0, column=1, padx=5, pady=(10,0), sticky="w")

        # ---- Строка 1: комбобоксы и кнопка ----
        self.type_combo = ttk.Combobox(self, state="readonly", width=15)
        self.type_combo.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_selected)

        self.block_combo = ttk.Combobox(self, state="readonly", width=50)
        self.block_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.show_button = ttk.Button(self, text="Показать структуру")
        self.show_button.grid(row=1, column=2, padx=5, pady=5, sticky="ew")

        # ---- Строка 2: панель управления развёртыванием ----
        level_frame = ttk.Frame(self)
        level_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        level_frame.columnconfigure(2, weight=1)

        ttk.Label(level_frame, text="Уровень раскрытия:").grid(row=0, column=0, padx=5, sticky="w")
        self.level_combo = ttk.Combobox(level_frame, values=[1,2,3,4,5], state="readonly", width=5)
        self.level_combo.grid(row=0, column=1, padx=5, sticky="w")
        self.level_combo.current(4)

        self.expand_button = ttk.Button(level_frame, text="+ / -", command=self._on_expand_level)
        self.expand_button.grid(row=0, column=2, padx=5, sticky="w")

        # ---- Строка 3: горизонтальная панель с сашем ----
        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=6)
        self.paned.grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")

        # Левая панель (дерево)
        left_frame = ttk.Frame(self.paned)
        self.paned.add(left_frame, width=500, minsize=300)

        self.tree = ttk.Treeview(left_frame, columns=("type", "signature"), show="tree headings")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree.heading("#0", text="Имя")
        self.tree.heading("type", text="Тип")
        self.tree.heading("signature", text="Сигнатура")

        self.tree.column("#0", width=300, minwidth=200, stretch=True)
        self.tree.column("type", width=100, minwidth=80, stretch=False)
        self.tree.column("signature", width=400, minwidth=200, stretch=True)

        tree_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        # Правая панель (текст) – используем CodeView
        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, width=500, minsize=300)
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        # Исправлено: убираем color_scheme или передаём None, чтобы использовать схему по умолчанию
        self.code_text = CodeView(
            right_frame,
            lexer=pygments.lexers.PythonLexer,
            color_scheme=None,   # или просто опустить этот параметр
            font=("Courier New", 10),
            wrap=tk.NONE,
            autohide_scrollbar=False,
            linenums_border=1,
            default_context_menu=True,
            tab_width=4
        )
        self.code_text.grid(row=0, column=0, sticky="nsew")

        # Привязка событий дерева
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    # ---- Методы для работы с комбобоксами ----
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

    def set_controller(self, controller):
        self.controller = controller

    def _on_type_selected(self, event):
        if self.controller:
            self.controller.on_type_selected(event)

    # ---- Методы для дерева ----
    def clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._item_to_node.clear()

    def display_structure(self, root_node):
        self.clear_tree()
        self._add_node("", root_node)
        self._expand_all("")

    def _add_node(self, parent, node):
        item = self.tree.insert(parent, tk.END, text=node.name, values=(node.node_type, node.signature))
        self._item_to_node[item] = node
        for child in node.children:
            self._add_node(item, child)

    def get_node_by_item(self, item):
        return self._item_to_node.get(item)

    def _expand_all(self, parent):
        for child in self.tree.get_children(parent):
            self.tree.item(child, open=True)
            self._expand_all(child)

    def _collapse_all(self, parent):
        for child in self.tree.get_children(parent):
            self.tree.item(child, open=False)
            self._collapse_all(child)

    def _expand_to_level(self, parent, current_level, target_level):
        if current_level >= target_level:
            return
        for child in self.tree.get_children(parent):
            self.tree.item(child, open=True)
            self._expand_to_level(child, current_level + 1, target_level)

    def _on_expand_level(self):
        try:
            level = int(self.level_combo.get())
        except (ValueError, TypeError):
            level = 5
        self._collapse_all('')
        self._expand_to_level('', 1, level)

    def _on_tree_select(self, event):
        if self.controller:
            self.controller.on_node_selected()

    # ---- Метод для отображения кода с подсветкой ----
    def display_code(self, code: str, language: str = "python"):
        self.code_text.delete(1.0, tk.END)
        if not code.strip():
            return

        # Устанавливаем лексер в зависимости от языка
        if language.lower() == "python":
            self.code_text.lexer = pygments.lexers.PythonLexer
        else:
            try:
                self.code_text.lexer = pygments.lexers.get_lexer_by_name(language.lower())
            except:
                pass  # оставляем текущий лексер

        self.code_text.insert(1.0, code)

    # ---- Вспомогательные методы ----
    def show_error(self, message):
        messagebox.showerror("Ошибка", message, parent=self)