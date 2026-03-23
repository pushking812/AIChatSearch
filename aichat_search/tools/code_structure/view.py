# aichat_search/tools/code_structure/view.py

import tkinter as tk
from tkinter import ttk, messagebox
from chlorophyll import CodeView
import pygments.lexers
from typing import Dict, Any, Optional


class CodeStructureWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Структура кода")
        self.geometry("1400x750")
        self.transient(parent)
        self.grab_set()

        self.controller = None
        self._left_item_to_node = {}
        self._right_item_to_data = {}

        # Верхняя панель с элементами управления
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(top_frame, text="Тип блока:").grid(row=0, column=0, padx=5, sticky="w")
        self.type_combo = ttk.Combobox(top_frame, state="readonly", width=35)
        self.type_combo.grid(row=0, column=1, padx=5, sticky="w")
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_selected)

        ttk.Label(top_frame, text="Блок:").grid(row=0, column=2, padx=5, sticky="w")
        self.block_combo = ttk.Combobox(top_frame, state="readonly", width=113)
        self.block_combo.grid(row=0, column=3, padx=5, sticky="w")
        self.block_combo.bind("<<ComboboxSelected>>", self._on_block_selected)

        self.module_button = ttk.Button(top_frame, text="Назначить модули", command=self._on_module_button)
        self.module_button.grid(row=0, column=4, padx=5)

        # Панели управления раскрытием деревьев и кнопками
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=5, pady=2)

        # Левое дерево
        ttk.Label(control_frame, text="Левое дерево, уровень:").pack(side=tk.LEFT, padx=5)
        self.left_level_combo = ttk.Combobox(control_frame, values=[1,2,3,4,5], state="readonly", width=5)
        self.left_level_combo.pack(side=tk.LEFT, padx=5)
        self.left_level_combo.current(4)
        self.left_expand_button = ttk.Button(control_frame, text="+ / -", command=self._on_left_expand_level)
        self.left_expand_button.pack(side=tk.LEFT, padx=5)

        ttk.Label(control_frame, text="    Правое дерево, уровень:").pack(side=tk.LEFT, padx=5)
        self.right_level_combo = ttk.Combobox(control_frame, values=[1,2,3,4,5], state="readonly", width=5)
        self.right_level_combo.pack(side=tk.LEFT, padx=5)
        self.right_level_combo.current(4)
        self.right_expand_button = ttk.Button(control_frame, text="+ / -", command=self._on_right_expand_level)
        self.right_expand_button.pack(side=tk.LEFT, padx=5)

        # Кнопки для работы с проектом
        self.save_button = ttk.Button(control_frame, text="Сохранить структуру", command=self._on_save_structure)
        self.save_button.pack(side=tk.LEFT, padx=5)
        self.load_button = ttk.Button(control_frame, text="Загрузить структуру", command=self._on_load_structure)
        self.load_button.pack(side=tk.LEFT, padx=5)
        self.create_button = ttk.Button(control_frame, text="Создать проект", command=self._on_create_project)
        self.create_button.pack(side=tk.LEFT, padx=5)

        # Главный горизонтальный PanedWindow
        self.main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=6)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Левая вертикальная панель
        left_vertical = tk.PanedWindow(self.main_paned, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=6)
        self.main_paned.add(left_vertical, width=600, minsize=400)

        left_tree_frame = ttk.Frame(left_vertical)
        left_vertical.add(left_tree_frame, height=350, minsize=200)

        self.tree = ttk.Treeview(left_tree_frame, columns=("type", "signature"), show="tree headings")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree.heading("#0", text="Имя")
        self.tree.heading("type", text="Тип")
        self.tree.heading("signature", text="Сигнатура")
        self.tree.column("#0", width=250, minwidth=150, stretch=True)
        self.tree.column("type", width=80, minwidth=60, stretch=False)
        self.tree.column("signature", width=250, minwidth=150, stretch=True)

        tree_scroll = ttk.Scrollbar(left_tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_left_tree_select)

        left_code_frame = ttk.Frame(left_vertical)
        left_vertical.add(left_code_frame, height=300, minsize=150)
        left_code_frame.grid_rowconfigure(0, weight=1)
        left_code_frame.grid_columnconfigure(0, weight=1)

        self.code_text = CodeView(
            left_code_frame,
            lexer=pygments.lexers.PythonLexer,
            color_scheme=None,
            font=("Courier New", 10),
            wrap=tk.NONE,
            autohide_scrollbar=False,
            linenums_border=1,
            default_context_menu=True,
            tab_width=4
        )
        self.code_text.grid(row=0, column=0, sticky="nsew")

        # Правая вертикальная панель
        right_vertical = tk.PanedWindow(self.main_paned, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=6)
        self.main_paned.add(right_vertical, width=700, minsize=400)

        right_tree_frame = ttk.Frame(right_vertical)
        right_vertical.add(right_tree_frame, height=350, minsize=200)

        self.merged_tree = ttk.Treeview(
            right_tree_frame,
            columns=("type", "signature", "version", "sources"),
            show="tree headings"
        )
        self.merged_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.merged_tree.heading("#0", text="Имя")
        self.merged_tree.heading("type", text="Тип")
        self.merged_tree.heading("signature", text="Сигнатура")
        self.merged_tree.heading("version", text="Версия")
        self.merged_tree.heading("sources", text="Последнее упоминание")

        self.merged_tree.column("#0", width=250, minwidth=150, stretch=True)
        self.merged_tree.column("type", width=80, minwidth=60, stretch=False)
        self.merged_tree.column("signature", width=200, minwidth=120, stretch=True)
        self.merged_tree.column("version", width=80, minwidth=60, stretch=False)
        self.merged_tree.column("sources", width=200, minwidth=120, stretch=True)

        merged_tree_scroll = ttk.Scrollbar(right_tree_frame, orient=tk.VERTICAL, command=self.merged_tree.yview)
        merged_tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.merged_tree.configure(yscrollcommand=merged_tree_scroll.set)
        self.merged_tree.bind("<<TreeviewSelect>>", self._on_right_tree_select)

        right_code_frame = ttk.Frame(right_vertical)
        right_vertical.add(right_code_frame, height=300, minsize=150)
        right_code_frame.grid_rowconfigure(0, weight=1)
        right_code_frame.grid_columnconfigure(0, weight=1)

        self.merged_code = CodeView(
            right_code_frame,
            lexer=pygments.lexers.PythonLexer,
            color_scheme=None,
            font=("Courier New", 10),
            wrap=tk.NONE,
            autohide_scrollbar=False,
            linenums_border=1,
            default_context_menu=True,
            tab_width=4
        )
        self.merged_code.grid(row=0, column=0, sticky="nsew")

        self.update_idletasks()
        min_width = (self.type_combo.winfo_reqwidth() +
                     self.block_combo.winfo_reqwidth() +
                     self.module_button.winfo_reqwidth() +
                     self.left_level_combo.winfo_reqwidth() +
                     self.left_expand_button.winfo_reqwidth() +
                     self.right_level_combo.winfo_reqwidth() +
                     self.right_expand_button.winfo_reqwidth() +
                     self.save_button.winfo_reqwidth() +
                     self.load_button.winfo_reqwidth() +
                     self.create_button.winfo_reqwidth() +
                     200)
        self.minsize(min_width, 550)

    # ---- Обработчики для автоматического показа структуры ----
    def _on_block_selected(self, event):
        if self.controller:
            self.controller.on_block_selected(event)

    # ---- Методы для управления левым деревом ----
    def _on_left_expand_level(self):
        try:
            level = int(self.left_level_combo.get())
        except (ValueError, TypeError):
            level = 5
        self._collapse_all_left('')
        self._expand_to_level_left('', 1, level)

    def _collapse_all_left(self, parent):
        for child in self.tree.get_children(parent):
            self.tree.item(child, open=False)
            self._collapse_all_left(child)

    def _expand_to_level_left(self, parent, current_level, target_level):
        if current_level >= target_level:
            return
        for child in self.tree.get_children(parent):
            self.tree.item(child, open=True)
            self._expand_to_level_left(child, current_level + 1, target_level)

    # ---- Методы для управления правым деревом ----
    def _on_right_expand_level(self):
        try:
            level = int(self.right_level_combo.get())
        except (ValueError, TypeError):
            level = 5
        self._collapse_all_right('')
        self._expand_to_level_right('', 1, level)

    def _collapse_all_right(self, parent):
        for child in self.merged_tree.get_children(parent):
            self.merged_tree.item(child, open=False)
            self._collapse_all_right(child)

    def _expand_to_level_right(self, parent, current_level, target_level):
        if current_level >= target_level:
            return
        for child in self.merged_tree.get_children(parent):
            self.merged_tree.item(child, open=True)
            self._expand_to_level_right(child, current_level + 1, target_level)

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

    def _on_module_button(self):
        if self.controller:
            self.controller._reset_module_assignments()

    # ---- Методы для работы с проектом (вызывают контроллер) ----
    def _on_save_structure(self):
        if self.controller:
            self.controller._save_structure()

    def _on_load_structure(self):
        if self.controller:
            self.controller._load_structure()

    def _on_create_project(self):
        if self.controller:
            self.controller._create_project()

    # ---- Методы для левого дерева ----
    def clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._left_item_to_node.clear()

    def display_structure(self, root_node):
        self.clear_tree()
        self._add_left_node("", root_node)
        if self.tree.get_children():
            first_item = self.tree.get_children()[0]
            self.tree.selection_set(first_item)
            self.tree.focus(first_item)
        self._expand_all_left("")

    def _add_left_node(self, parent, node):
        item = self.tree.insert(parent, tk.END, text=node.name, values=(node.node_type, node.signature))
        self._left_item_to_node[item] = node
        for child in node.children:
            self._add_left_node(item, child)

    def get_node_by_item(self, item):
        return self._left_item_to_node.get(item)

    def _expand_all_left(self, parent):
        for child in self.tree.get_children(parent):
            self.tree.item(child, open=True)
            self._expand_all_left(child)

    def _on_left_tree_select(self, event):
        if self.controller:
            self.controller.on_node_selected()

    # ---- Методы для правого дерева ----
    def clear_merged_tree(self):
        for item in self.merged_tree.get_children():
            self.merged_tree.delete(item)
        self._right_item_to_data.clear()

    def display_merged_tree(self, root_node: Dict[str, Any]):
        self.clear_merged_tree()
        self._add_merged_node("", root_node)
        if self.merged_tree.get_children():
            first_item = self.merged_tree.get_children()[0]
            self.merged_tree.selection_set(first_item)
            self.merged_tree.focus(first_item)

    def _add_merged_node(self, parent: str, node_data: Dict[str, Any]):
        item = self.merged_tree.insert(
            parent, tk.END,
            text=node_data['text'],
            values=(
                node_data.get('type', ''),
                node_data.get('signature', ''),
                node_data.get('version', ''),
                node_data.get('sources', '')
            )
        )
        self._right_item_to_data[item] = node_data
        for child in node_data.get('children', []):
            self._add_merged_node(item, child)

    def get_merged_data_by_item(self, item) -> Optional[Dict[str, Any]]:
        return self._right_item_to_data.get(item)

    def _on_right_tree_select(self, event):
        selected = self.merged_tree.selection()
        if not selected:
            return
        item = selected[0]
        data = self.get_merged_data_by_item(item)
        if data and self.controller:
            self.controller.on_merged_node_selected(data)

    # ---- Методы для отображения кода ----
    def display_code(self, code: str, language: str = "python"):
        self.code_text.delete(1.0, tk.END)
        if not code.strip():
            return
        if language.lower() == "python":
            self.code_text.lexer = pygments.lexers.PythonLexer
        else:
            try:
                self.code_text.lexer = pygments.lexers.get_lexer_by_name(language.lower())
            except:
                pass
        self.code_text.insert(1.0, code)

    def display_merged_code(self, code: str, language: str = "python"):
        self.merged_code.delete(1.0, tk.END)
        if not code.strip():
            return
        if language.lower() == "python":
            self.merged_code.lexer = pygments.lexers.PythonLexer
        else:
            try:
                self.merged_code.lexer = pygments.lexers.get_lexer_by_name(language.lower())
            except:
                pass
        self.merged_code.insert(1.0, code)

    # ---- Вспомогательные методы ----
    def show_error(self, message):
        messagebox.showerror("Ошибка", message, parent=self)