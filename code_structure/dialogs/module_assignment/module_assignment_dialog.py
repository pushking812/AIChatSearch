# code_structure/ui/module_assignment/module_assignment_dialog.py

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional

from code_structure.dialogs.dialog_interfaces import ModuleAssignmentView
from code_structure.dialogs.module_assignment.module_assignment_presenter import ModuleAssignmentPresenter
from code_structure.dialogs.dto import (
    UnknownBlockInfo, KnownModuleInfo, TreeDisplayNode, ModuleAssignmentInput
)


class ModuleAssignmentDialog(tk.Toplevel, ModuleAssignmentView):
    def __init__(self, parent, input_data: ModuleAssignmentInput):
        super().__init__(parent)
        self.title("Назначение модулей")
        self.geometry("1200x800")
        self.minsize(1200, 800)
        self.transient(parent)
        self.grab_set()
        
        self._tree_item_data = {}

        self.presenter = ModuleAssignmentPresenter(self)
        self._create_widgets()
        self.presenter.initialize(input_data)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.result = None

    def _create_widgets(self):
        # Создаём canvas для прокрутки
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.columnconfigure(0, weight=1)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", tags=("inner_frame",))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._create_content_widgets()

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig("inner_frame", width=event.width)

    def _create_content_widgets(self):
        # Верхняя панель
        top_frame = ttk.Frame(self.scrollable_frame)
        top_frame.grid(row=0, column=0, sticky="ew", pady=5, padx=10)
        top_frame.columnconfigure(1, weight=1)
        top_frame.columnconfigure(3, weight=1)

        ttk.Label(top_frame, text="Неопределённый блок:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.block_combo = ttk.Combobox(top_frame, state="readonly", width=60)
        self.block_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.block_combo.bind("<<ComboboxSelected>>", self._on_block_selected)

        ttk.Label(top_frame, text="Назначить модулю:").grid(row=0, column=2, sticky=tk.W, padx=(20, 5))
        self.module_combo = ttk.Combobox(top_frame, state="readonly", width=60)
        self.module_combo.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        self.assigned_label = ttk.Label(top_frame, text="", foreground="blue")
        self.assigned_label.grid(row=0, column=4, padx=10, sticky=tk.W)

        # Панель с двумя колонками
        columns_frame = ttk.Frame(self.scrollable_frame)
        columns_frame.grid(row=1, column=0, sticky="nsew", pady=10, padx=10)
        columns_frame.columnconfigure(0, weight=1)
        columns_frame.columnconfigure(1, weight=1)
        columns_frame.rowconfigure(0, weight=1)

        # Левая колонка - дерево модулей
        left_frame = ttk.LabelFrame(columns_frame, text="Структура модулей (до назначения)")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5)
        left_frame.rowconfigure(0, weight=1)
        left_frame.columnconfigure(0, weight=1)

        self.module_tree = ttk.Treeview(
            left_frame,
            columns=("type", "signature", "version"),
            show="tree headings"
        )
        self.module_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.module_tree.heading("#0", text="Имя")
        self.module_tree.heading("type", text="Тип")
        self.module_tree.heading("signature", text="Сигнатура")
        self.module_tree.heading("version", text="Версия")

        self.module_tree.column("#0", width=200, minwidth=150, stretch=True)
        self.module_tree.column("type", width=80, minwidth=60, stretch=False)
        self.module_tree.column("signature", width=150, minwidth=100, stretch=True)
        self.module_tree.column("version", width=60, minwidth=40, stretch=False)

        tree_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.module_tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.module_tree.configure(yscrollcommand=tree_scroll.set)
        self.module_tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Правая колонка - код
        right_frame = ttk.Frame(columns_frame)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)

        block_frame = ttk.LabelFrame(right_frame, text="Код выбранного блока")
        block_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        block_frame.rowconfigure(0, weight=1)
        block_frame.columnconfigure(0, weight=1)

        self.block_text = tk.Text(block_frame, wrap=tk.NONE, font=("Courier New", 10))
        block_scroll_y = ttk.Scrollbar(block_frame, orient=tk.VERTICAL, command=self.block_text.yview)
        block_scroll_x = ttk.Scrollbar(block_frame, orient=tk.HORIZONTAL, command=self.block_text.xview)
        self.block_text.configure(yscrollcommand=block_scroll_y.set, xscrollcommand=block_scroll_x.set)
        self.block_text.grid(row=0, column=0, sticky="nsew")
        block_scroll_y.grid(row=0, column=1, sticky="ns")
        block_scroll_x.grid(row=1, column=0, sticky="ew")

        module_frame = ttk.LabelFrame(right_frame, text="Код выбранного модуля (пример)")
        module_frame.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
        module_frame.rowconfigure(0, weight=1)
        module_frame.columnconfigure(0, weight=1)

        self.module_text = tk.Text(module_frame, wrap=tk.NONE, font=("Courier New", 10))
        module_scroll_y = ttk.Scrollbar(module_frame, orient=tk.VERTICAL, command=self.module_text.yview)
        module_scroll_x = ttk.Scrollbar(module_frame, orient=tk.HORIZONTAL, command=self.module_text.xview)
        self.module_text.configure(yscrollcommand=module_scroll_y.set, xscrollcommand=module_scroll_x.set)
        self.module_text.grid(row=0, column=0, sticky="nsew")
        module_scroll_y.grid(row=0, column=1, sticky="ns")
        module_scroll_x.grid(row=1, column=0, sticky="ew")

        # Панель с радиокнопками
        action_frame = ttk.LabelFrame(self.scrollable_frame, text="Действие")
        action_frame.grid(row=2, column=0, sticky="w", pady=10, padx=10)

        self.action_var = tk.StringVar(value="assign_existing")
        ttk.Radiobutton(
            action_frame,
            text="Создать новый модуль с указанным именем",
            variable=self.action_var,
            value="create_new",
            command=self._on_action_change
        ).pack(anchor=tk.W, padx=20, pady=2)
        ttk.Radiobutton(
            action_frame,
            text="Добавить блок в выбранный модуль",
            variable=self.action_var,
            value="assign_existing",
            command=self._on_action_change
        ).pack(anchor=tk.W, padx=20, pady=2)

        # Поле для ввода нового имени модуля
        new_module_frame = ttk.Frame(self.scrollable_frame)
        new_module_frame.grid(row=2, column=0, sticky="e", pady=10, padx=10)

        ttk.Label(new_module_frame, text="Имя нового модуля (с точками):").pack(anchor=tk.W, padx=5)
        self.new_module_entry = ttk.Entry(new_module_frame, width=40)
        self.new_module_entry.pack(anchor=tk.W, padx=5, pady=(0, 5))
        self.new_module_entry.config(state="disabled")
        self.new_module_entry.bind("<KeyRelease>", self._on_new_module_changed)

        # Кнопки
        button_frame = ttk.Frame(self.scrollable_frame)
        button_frame.grid(row=3, column=0, sticky="ew", pady=10, padx=10)

        self.apply_button = ttk.Button(button_frame, text="Применить", command=self._apply, state="disabled")
        self.apply_button.pack(side=tk.LEFT, padx=5)

        self.ok_button = ttk.Button(button_frame, text="ОК", command=self._ok, state="disabled")
        self.ok_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Отмена", command=self._cancel).pack(side=tk.LEFT, padx=5)

    def show_error(self, message: str):
        messagebox.showerror("Ошибка", message, parent=self)

    def set_blocks(self, blocks: List[UnknownBlockInfo]):
        self.block_combo['values'] = [b.display_name for b in blocks]
        if blocks:
            self.block_combo.current(0)

    def set_modules(self, modules: List[KnownModuleInfo]):
        module_display_names = []
        for info in modules:
            if info.source:
                module_display_names.append(f"{info.name} (из {info.source})")
            else:
                module_display_names.append(info.name)
        self.module_combo['values'] = module_display_names
        if module_display_names:
            self.module_combo.current(0)

    def set_tree_data(self, tree_data: TreeDisplayNode):
        for item in self.module_tree.get_children():
            self.module_tree.delete(item)
        self._tree_item_data.clear()
        self._add_tree_node("", tree_data)

    def _add_tree_node(self, parent: str, node: TreeDisplayNode):
        text = node.text
        item = self.module_tree.insert(
            parent, tk.END,
            text=text,
            values=(
                node.type,
                node.signature,
                node.version,
                node.sources
            )
        )
        self._tree_item_data[item] = node
        for child in node.children:
            self._add_tree_node(item, child)

    def show_block_code(self, code: str):
        self.block_text.delete(1.0, tk.END)
        self.block_text.insert(1.0, code)

    def show_module_code(self, code: str):
        self.module_text.delete(1.0, tk.END)
        if code:
            self.module_text.insert(1.0, code)

    def update_assignment_label(self, module_name: str):
        if module_name:
            self.assigned_label.config(text=f"Назначен модуль: {module_name}")
        else:
            self.assigned_label.config(text="")

    def enable_apply_button(self, enabled: bool):
        self.apply_button.config(state="normal" if enabled else "disabled")

    def enable_ok_button(self, enabled: bool):
        self.ok_button.config(state="normal" if enabled else "disabled")

    def set_action_mode(self, mode: str):
        if mode == "create_new":
            self.module_combo.config(state="disabled")
            self.new_module_entry.config(state="normal")
        else:
            self.module_combo.config(state="readonly")
            self.new_module_entry.config(state="disabled")

    def get_selected_block_id(self) -> Optional[str]:
        """Возвращает ID выбранного блока."""
        if not self.presenter.input:
            return None
        selected_idx = self.block_combo.current()
        if 0 <= selected_idx < len(self.presenter.input.unknown_blocks):
            return self.presenter.input.unknown_blocks[selected_idx].id
        return None

    def get_selected_module(self) -> str:
        return self.module_combo.get()

    def get_new_module_name(self) -> str:
        return self.new_module_entry.get()

    def get_action_mode(self) -> str:
        return self.action_var.get()

    def close(self):
        self.destroy()

    def _on_block_selected(self, event=None):
        block_id = self.get_selected_block_id()
        if block_id:
            self.presenter.on_block_selected(block_id)

    def _on_tree_select(self, event):
        selected = self.module_tree.selection()
        if not selected:
            return
        item = selected[0]
        node_data = self._tree_item_data.get(item)
        if node_data and node_data.type in ('module', 'class', 'function', 'method'):
            full_name = node_data.full_name
            # Ищем модуль по полному имени
            for mod in self.presenter.input.known_modules:
                if mod.name == full_name:
                    self.show_module_code(mod.code)
                    break

    def _on_action_change(self):
        self.presenter.on_action_changed(self.get_action_mode())

    def _on_new_module_changed(self, event=None):
        self.presenter.on_new_module_name_changed(self.get_new_module_name())

    def _apply(self):
        self.presenter.on_apply()

    def _ok(self):
        self.result = self.presenter.on_ok()
        self.destroy()

    def _cancel(self):
        if self.presenter.on_cancel() is None:
            self.result = None
            self.destroy()

    def _on_close(self):
        if self.presenter.on_close():
            response = messagebox.askyesno(
                "Подтверждение",
                "Есть несохранённые изменения. Закрыть без сохранения?",
                parent=self
            )
            if not response:
                return
        self.result = None
        self.destroy()