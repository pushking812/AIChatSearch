# code_structure/ui/code_structure/main_window_view.py

import tkinter as tk
from tkinter import ttk, messagebox
from chlorophyll import CodeView
import pygments.lexers
from pygments.util import ClassNotFound
from typing import List, Optional

from code_structure.dialogs.dialog_interfaces import CodeStructureView
from code_structure.dialogs.dto import TreeDisplayNode, FlatListItem


class CodeStructureView(tk.Toplevel, CodeStructureView):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Структура кода")
        self.geometry("1400x750")
        self.transient(parent)
        self.grab_set()

        self.presenter = None
        self._right_item_to_data = {}
        self._all_flat_items: List[FlatListItem] = []
        self._current_filter_column = "Узел"
        self._current_filter_text = ""

        # --- Верхняя панель с элементами управления ---
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(top_frame, text="Тип блока:").grid(row=0, column=0, padx=5, sticky="w")
        self.type_combo = ttk.Combobox(top_frame, state="readonly", width=35)
        self.type_combo.grid(row=0, column=1, padx=5, sticky="w")
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_selected)

        self.local_only_var = tk.BooleanVar(value=True)
        self.local_only_check = ttk.Checkbutton(
            top_frame,
            text="Только локальные импорты",
            variable=self.local_only_var,
            command=self._on_local_only_toggled
        )
        self.local_only_check.grid(row=0, column=2, padx=5, sticky="w")

        self.module_button = ttk.Button(top_frame, text="Назначить модули", command=self._on_module_button)
        self.module_button.grid(row=0, column=3, padx=5)

        # Панель управления правым деревом и кнопками
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(control_frame, text="Правое дерево, уровень:").pack(side=tk.LEFT, padx=5)
        self.right_level_combo = ttk.Combobox(control_frame, values=[1,2,3,4,5], state="readonly", width=5)
        self.right_level_combo.pack(side=tk.LEFT, padx=5)
        self.right_level_combo.current(4)
        self.right_expand_button = ttk.Button(control_frame, text="+ / -", command=self._on_right_expand_level)
        self.right_expand_button.pack(side=tk.LEFT, padx=5)

        self.save_button = ttk.Button(control_frame, text="Сохранить структуру", command=self._on_save_structure)
        self.save_button.pack(side=tk.LEFT, padx=5)
        self.load_button = ttk.Button(control_frame, text="Загрузить структуру", command=self._on_load_structure)
        self.load_button.pack(side=tk.LEFT, padx=5)
        self.create_button = ttk.Button(control_frame, text="Создать проект", command=self._on_create_project)
        self.create_button.pack(side=tk.LEFT, padx=5)

        # Панель фильтрации плоского списка
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(filter_frame, text="Фильтр плоского списка:").pack(side=tk.LEFT, padx=5)
        self.filter_column_combo = ttk.Combobox(
            filter_frame,
            values=["Узел", "Модуль", "Класс", "Стратегия"],
            state="readonly",
            width=15
        )
        self.filter_column_combo.current(0)
        self.filter_column_combo.pack(side=tk.LEFT, padx=5)
        self.filter_column_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

        self.filter_entry = ttk.Entry(filter_frame, width=20)
        self.filter_entry.pack(side=tk.LEFT, padx=5)
        self.filter_entry.bind("<KeyRelease>", self._on_filter_changed)

        self.clear_filter_button = ttk.Button(filter_frame, text="X", width=3, command=self._clear_filter)
        self.clear_filter_button.pack(side=tk.LEFT, padx=5)

        # --- Главный горизонтальный PanedWindow ---
        self.main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=6)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Левая вертикальная панель (плоский список + код) ---
        left_vertical = tk.PanedWindow(self.main_paned, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=6)
        self.main_paned.add(left_vertical, width=600, minsize=400)

        # Контейнер для плоского списка
        flat_container = ttk.Frame(left_vertical)
        left_vertical.add(flat_container, height=350, minsize=200)
        flat_container.grid_rowconfigure(0, weight=1)
        flat_container.grid_columnconfigure(0, weight=1)

        self.flat_tree = ttk.Treeview(
            flat_container,
            columns=("block_name", "node_path", "parent_path", "lines", "module", "class", "strategy"),
            show="tree headings"
        )
        flat_v_scroll = ttk.Scrollbar(flat_container, orient=tk.VERTICAL, command=self.flat_tree.yview)
        flat_h_scroll = ttk.Scrollbar(flat_container, orient=tk.HORIZONTAL, command=self.flat_tree.xview)
        self.flat_tree.configure(yscrollcommand=flat_v_scroll.set, xscrollcommand=flat_h_scroll.set)

        self.flat_tree.grid(row=0, column=0, sticky="nsew")
        flat_v_scroll.grid(row=0, column=1, sticky="ns")
        flat_h_scroll.grid(row=1, column=0, sticky="ew")

        # Настройка колонок: разрешаем изменение ширины, задаём минимальную ширину
        self.flat_tree.heading("#0", text="ID")
        self.flat_tree.column("#0", width=0, stretch=False)  # ID не нужен

        self.flat_tree.heading("block_name", text="Блок")
        self.flat_tree.column("block_name", minwidth=50, stretch=True)

        self.flat_tree.heading("node_path", text="Узел")
        self.flat_tree.column("node_path", minwidth=50, stretch=True)

        self.flat_tree.heading("parent_path", text="Родитель")
        self.flat_tree.column("parent_path", minwidth=50, stretch=True)

        self.flat_tree.heading("lines", text="Строки")
        self.flat_tree.column("lines", minwidth=50, stretch=True)

        self.flat_tree.heading("module", text="Модуль")
        self.flat_tree.column("module", minwidth=50, stretch=True)

        self.flat_tree.heading("class", text="Класс")
        self.flat_tree.column("class", minwidth=50, stretch=True)

        self.flat_tree.heading("strategy", text="Стратегия")
        self.flat_tree.column("strategy", minwidth=50, stretch=True)

        self.flat_tree.bind("<<TreeviewSelect>>", self._on_flat_tree_select)

        # Текстовое поле для кода (левое)
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

        # --- Правая вертикальная панель (сводное дерево + код) ---
        right_vertical = tk.PanedWindow(self.main_paned, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=6)
        self.main_paned.add(right_vertical, width=700, minsize=400)

        # Контейнер для сводного дерева
        merged_container = ttk.Frame(right_vertical)
        right_vertical.add(merged_container, height=350, minsize=200)
        merged_container.grid_rowconfigure(0, weight=1)
        merged_container.grid_columnconfigure(0, weight=1)

        self.merged_tree = ttk.Treeview(
            merged_container,
            columns=("type", "signature", "version", "sources", "full_name"),
            show="tree headings"
        )
        merged_v_scroll = ttk.Scrollbar(merged_container, orient=tk.VERTICAL, command=self.merged_tree.yview)
        merged_h_scroll = ttk.Scrollbar(merged_container, orient=tk.HORIZONTAL, command=self.merged_tree.xview)
        self.merged_tree.configure(yscrollcommand=merged_v_scroll.set, xscrollcommand=merged_h_scroll.set)

        self.merged_tree.grid(row=0, column=0, sticky="nsew")
        merged_v_scroll.grid(row=0, column=1, sticky="ns")
        merged_h_scroll.grid(row=1, column=0, sticky="ew")

        # Настройка колонок сводного дерева
        self.merged_tree.heading("#0", text="Имя")
        self.merged_tree.column("#0", minwidth=50, stretch=True)

        self.merged_tree.heading("type", text="Тип")
        self.merged_tree.column("type", minwidth=50, stretch=True)

        self.merged_tree.heading("signature", text="Сигнатура")
        self.merged_tree.column("signature", minwidth=50, stretch=True)

        self.merged_tree.heading("version", text="Версия")
        self.merged_tree.column("version", minwidth=50, stretch=True)

        self.merged_tree.heading("sources", text="Последнее упоминание")
        self.merged_tree.column("sources", minwidth=50, stretch=True)

        self.merged_tree.heading("full_name", text="Полное имя")
        self.merged_tree.column("full_name", width=0, stretch=False)  # скрытая колонка

        self.merged_tree.bind("<<TreeviewSelect>>", self._on_right_tree_select)

        # Текстовое поле для кода (правое)
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

        # Минимальная ширина окна
        self.update_idletasks()
        control_width = sum(w.winfo_reqwidth() for w in control_frame.winfo_children()) + 50
        filter_width = sum(w.winfo_reqwidth() for w in filter_frame.winfo_children()) + 50
        min_width = max(control_width, filter_width, 800)
        self.minsize(min_width, 550)

    # ------------------------------------------------------------------
    # Все остальные методы (фильтрация, обработчики) остаются без изменений
    # ------------------------------------------------------------------
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

    def clear_merged_tree(self):
        if not self.merged_tree.winfo_exists():
            return
        for item in self.merged_tree.get_children():
            self.merged_tree.delete(item)
        self._right_item_to_data.clear()

    def display_merged_tree(self, root_node: TreeDisplayNode):
        self.clear_merged_tree()
        self._add_merged_node("", root_node)
        if self.merged_tree.get_children():
            first_item = self.merged_tree.get_children()[0]
            self.merged_tree.selection_set(first_item)
            self.merged_tree.focus(first_item)

    def _add_merged_node(self, parent: str, node: TreeDisplayNode):
        item = self.merged_tree.insert(
            parent, tk.END,
            text=node.text,
            values=(
                node.type,
                node.signature,
                node.version,
                node.sources,
                node.full_name
            )
        )
        self._right_item_to_data[item] = node
        for child in node.children:
            self._add_merged_node(item, child)

    def set_flat_list(self, items: List[FlatListItem]):
        self._all_flat_items = items
        self._apply_flat_filter()

    def _apply_flat_filter(self):
        for item in self.flat_tree.get_children():
            self.flat_tree.delete(item)

        filtered = self._all_flat_items
        if self._current_filter_text.strip():
            col_map = {
                "Узел": "node_path",
                "Модуль": "module",
                "Класс": "class_name",
                "Стратегия": "strategy"
            }
            attr = col_map.get(self._current_filter_column, "node_path")
            text_lower = self._current_filter_text.lower()
            filtered = [
                item for item in self._all_flat_items
                if text_lower in getattr(item, attr, "").lower()
            ]

        for i, data in enumerate(filtered):
            self.flat_tree.insert(
                "", tk.END,
                text=str(i),
                values=(
                    data.block_name,
                    data.node_path,
                    data.parent_path,
                    data.lines,
                    data.module,
                    data.class_name,
                    data.strategy
                ),
                tags=(data.block_id,)
            )

    def _on_filter_changed(self, event=None):
        self._current_filter_column = self.filter_column_combo.get()
        self._current_filter_text = self.filter_entry.get()
        self._apply_flat_filter()

    def _clear_filter(self):
        self.filter_entry.delete(0, tk.END)
        self.filter_column_combo.current(0)
        self._current_filter_column = "Узел"
        self._current_filter_text = ""
        self._apply_flat_filter()

    def set_flat_filter(self, column: str, value: str):
        if column in ["Узел", "Модуль", "Класс", "Стратегия"]:
            self.filter_column_combo.set(column)
            self.filter_entry.delete(0, tk.END)
            self.filter_entry.insert(0, value)
            self._current_filter_column = column
            self._current_filter_text = value
            self._apply_flat_filter()

    def clear_flat_filter(self):
        self._clear_filter()

    def set_type_combo_values(self, values):
        self.type_combo['values'] = values
        if values:
            self.type_combo.current(0)

    def set_type_combo_state(self, enabled: bool):
        state = 'readonly' if enabled else 'disabled'
        self.type_combo.config(state=state)

    def get_local_only(self) -> bool:
        return self.local_only_var.get()

    def set_presenter(self, presenter):
        self.presenter = presenter

    def set_controller(self, controller):
        self.set_presenter(controller)

    def set_module_button_state(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.module_button.config(state=state)

    def show_error(self, message: str):
        messagebox.showerror("Ошибка", message, parent=self)

    def display_code(self, code: str, language: str = "python", start_line: Optional[int] = None, end_line: Optional[int] = None):
        self.code_text.delete(1.0, tk.END)
        if not code.strip():
            return
        if language.lower() == "python":
            self.code_text.lexer = pygments.lexers.PythonLexer
        else:
            try:
                self.code_text.lexer = pygments.lexers.get_lexer_by_name(language.lower())
            except ClassNotFound:
                pass
        self.code_text.insert(1.0, code)
        if start_line is not None:
            line_start = f"{start_line}.0"
            self.code_text.see(line_start)
            self.code_text.mark_set("insert", line_start)
            self.code_text.focus_set()

    def display_merged_code(self, code: str, language: str = "python"):
        self.merged_code.delete(1.0, tk.END)
        if not code.strip():
            return
        if language.lower() == "python":
            self.merged_code.lexer = pygments.lexers.PythonLexer
        else:
            try:
                self.merged_code.lexer = pygments.lexers.get_lexer_by_name(language.lower())
            except ClassNotFound:
                pass
        self.merged_code.insert(1.0, code)

    def _on_type_selected(self, event):
        if self.presenter:
            self.presenter.on_type_selected(event)

    def _on_module_button(self):
        if self.presenter:
            self.presenter.on_reset_module_assignments()

    def _on_save_structure(self):
        if self.presenter:
            self.presenter.on_save_structure()

    def _on_load_structure(self):
        if self.presenter:
            self.presenter.on_load_structure()

    def _on_create_project(self):
        if self.presenter:
            self.presenter.on_create_project()

    def _on_local_only_toggled(self):
        if self.presenter:
            self.presenter.on_local_only_toggled(self.local_only_var.get())

    def _on_flat_tree_select(self, event):
        selected = self.flat_tree.selection()
        if not selected:
            return
        item = selected[0]
        tags = self.flat_tree.item(item, 'tags')
        if tags:
            block_id = tags[0]
            values = self.flat_tree.item(item, 'values')
            lines_str = values[3] if len(values) > 3 else ""
            if self.presenter:
                self.presenter.on_flat_node_selected(block_id, lines_str)

    def _on_right_tree_select(self, event):
        selected = self.merged_tree.selection()
        if not selected:
            return
        item = selected[0]
        node_data = self._right_item_to_data.get(item)
        if node_data and self.presenter:
            self.presenter.on_merged_node_selected(node_data, self._right_item_to_data)