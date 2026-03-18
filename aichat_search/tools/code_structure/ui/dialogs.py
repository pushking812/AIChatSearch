# aichat_search/tools/code_structure/ui/dialogs.py

import re
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Optional, Any

from aichat_search.tools.code_structure.core.tree_builder import TreeBuilder


class ModuleAssignmentDialog(tk.Toplevel):
    """
    Диалог для ручного назначения модулей блокам без автоматической подсказки.
    """
    def __init__(
        self,
        parent,
        unknown_blocks: List[Dict[str, Any]],
        module_info: List[Dict[str, Any]],
        module_code_map: Optional[Dict[str, str]] = None,
        module_containers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(parent)
        self.title("Назначение модулей")
        self.geometry("1200x400")
        self.minsize(1200, 400)
        self.transient(parent)
        self.grab_set()

        self.unknown_blocks = unknown_blocks
        self.module_info = module_info
        self.known_modules = [info['name'] for info in module_info]
        self.has_modules = bool(self.known_modules)
        self.module_code_map = module_code_map or {}
        self.module_containers = module_containers or {}
        self.assignments: Dict[str, str] = {}
        self.changed = False
        self.result = None
        self.controller = None
        self.tree_builder = TreeBuilder()

        self.current_block_index = 0
        self.current_block_id = unknown_blocks[0]['id'] if unknown_blocks else None
        self.current_applied = ""
        self.current_assign_state = ""

        self._create_scrollable_area()
        self._create_widgets()
        self._update_display()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_scrollable_area(self):
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

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig("inner_frame", width=event.width)

    def _create_widgets(self):
        # Верхняя панель с выбором блока
        top_frame = ttk.Frame(self.scrollable_frame)
        top_frame.grid(row=0, column=0, sticky="ew", pady=5, padx=10)
        top_frame.columnconfigure(1, weight=1)

        ttk.Label(top_frame, text="Неопределённый блок:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.block_combo = ttk.Combobox(
            top_frame,
            values=[block['display_name'] for block in self.unknown_blocks],
            state="readonly",
            width=60
        )
        self.block_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.block_combo.bind("<<ComboboxSelected>>", self._on_block_selected)

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

        # Создаём дерево
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

        # Правая колонка - код и назначение
        right_frame = ttk.Frame(columns_frame)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)

        # Код выбранного блока (сверху)
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

        # Код выбранного модуля (снизу)
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

        # Панель назначения модуля
        assign_frame = ttk.Frame(self.scrollable_frame)
        assign_frame.grid(row=2, column=0, sticky="ew", pady=5, padx=10)
        assign_frame.columnconfigure(1, weight=1)

        ttk.Label(assign_frame, text="Назначить модулю:").grid(row=0, column=0, sticky=tk.W, padx=5)

        # Комбобокс с модулями из оркестратора
        module_display_names = []
        for info in self.module_info:
            if info['source']:
                module_display_names.append(f"{info['name']} (из {info['source']})")
            else:
                module_display_names.append(info['name'])

        self.module_combo = ttk.Combobox(
            assign_frame,
            values=module_display_names,
            state="readonly" if self.has_modules else "disabled",
            width=60
        )
        self.module_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.module_combo.bind("<<ComboboxSelected>>", self._on_module_selected)

        self.assigned_label = ttk.Label(assign_frame, text="", foreground="blue")
        self.assigned_label.grid(row=0, column=2, padx=10, sticky=tk.W)

        # Панель для ввода нового имени модуля
        new_module_frame = ttk.Frame(self.scrollable_frame)
        new_module_frame.grid(row=3, column=0, sticky="ew", pady=5, padx=10)
        new_module_frame.columnconfigure(1, weight=1)

        ttk.Label(new_module_frame, text="Имя нового модуля (с точками):").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.new_module_entry = ttk.Entry(new_module_frame)
        self.new_module_entry.grid(row=0, column=1, padx=5, sticky="ew")
        self.new_module_entry.config(state="disabled")
        self.new_module_entry.bind("<KeyRelease>", self._on_new_module_changed)

        # Панель с радиокнопками выбора действия
        action_frame = ttk.LabelFrame(self.scrollable_frame, text="Действие")
        action_frame.grid(row=4, column=0, sticky="ew", pady=10, padx=10)

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

        # Кнопки
        button_frame = ttk.Frame(self.scrollable_frame)
        button_frame.grid(row=5, column=0, sticky="ew", pady=10, padx=10)

        self.apply_button = ttk.Button(button_frame, text="Применить", command=self._apply, state="disabled")
        self.apply_button.pack(side=tk.LEFT, padx=5)

        self.ok_button = ttk.Button(button_frame, text="ОК", command=self._ok, state="disabled")
        self.ok_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Отмена", command=self._cancel).pack(side=tk.LEFT, padx=5)

        # Заполняем дерево модулей
        self._populate_module_tree()

    def _populate_module_tree(self):
        """Заполняет дерево структурой модулей до назначения."""
        for item in self.module_tree.get_children():
            self.module_tree.delete(item)

        if not self.module_containers:
            return

        # Строим корневое дерево
        root_node = self.tree_builder.build_display_tree(self.module_containers)
        self._add_tree_node("", root_node)

    def _add_tree_node(self, parent: str, node_data: Dict[str, Any]):
        """Рекурсивно добавляет узел дерева."""
        item = self.module_tree.insert(
            parent, tk.END,
            text=node_data['text'],
            values=(
                node_data.get('type', ''),
                node_data.get('signature', ''),
                node_data.get('version', '')
            )
        )
        # Сохраняем данные узла для последующего использования
        if not hasattr(self, '_tree_item_data'):
            self._tree_item_data = {}
        self._tree_item_data[item] = node_data

        for child in node_data.get('children', []):
            self._add_tree_node(item, child)

    def _on_tree_select(self, event):
        """Обработчик выбора элемента в дереве."""
        selected = self.module_tree.selection()
        if not selected:
            return

        item = selected[0]
        node_data = getattr(self, '_tree_item_data', {}).get(item)
        if not node_data:
            return

        # Если выбран узел-версия, показываем её код
        if node_data.get('type') == 'version':
            version = node_data.get('_version_data')
            if version and version.sources:
                block_id, start, end, _ = version.sources[0]
                # Ищем соответствующий блок в unknown_blocks или в module_code_map
                for block in self.unknown_blocks:
                    if block['id'] == block_id:
                        self.block_text.delete(1.0, tk.END)
                        self.block_text.insert(1.0, block['content'])
                        return
                # Если не нашли, возможно это код из module_code_map
                for module, code in self.module_code_map.items():
                    if module in block_id:  # грубое приближение
                        self.block_text.delete(1.0, tk.END)
                        self.block_text.insert(1.0, code)
                        return

    def _get_clean_module_name(self, display_name: str) -> str:
        if ' (из ' in display_name:
            return display_name.split(' (из ')[0]
        return display_name

    def _on_action_change(self):
        if self.action_var.get() == "create_new":
            self.module_combo.config(state="disabled")
            self.new_module_entry.config(state="normal")
        else:
            if self.has_modules:
                self.module_combo.config(state="readonly")
            else:
                self.module_combo.config(state="disabled")
            self.new_module_entry.config(state="disabled")
        self._check_changes()

    def _on_block_selected(self, event=None):
        index = self.block_combo.current()
        if 0 <= index < len(self.unknown_blocks):
            self.current_block_index = index
            self.current_block_id = self.unknown_blocks[index]['id']
            self._update_display()

    def _on_module_selected(self, event=None):
        selected_display = self.module_combo.get()
        selected = self._get_clean_module_name(selected_display)
        if selected in self.module_code_map:
            self.module_text.delete(1.0, tk.END)
            self.module_text.insert(1.0, self.module_code_map[selected])
        else:
            self.module_text.delete(1.0, tk.END)
        self._check_changes()

    def _on_new_module_changed(self, event=None):
        self._check_changes()

    def _check_changes(self):
        current_val = self._get_current_value()
        if current_val != self.current_applied:
            self.apply_button.config(state="normal")
        else:
            self.apply_button.config(state="disabled")

    def _get_current_value(self):
        if self.action_var.get() == "create_new":
            return self.new_module_entry.get().strip()
        else:
            selected_display = self.module_combo.get()
            return self._get_clean_module_name(selected_display)

    def _update_display(self):
        if not self.unknown_blocks:
            return
        block = self.unknown_blocks[self.current_block_index]
        self.block_text.delete(1.0, tk.END)
        self.block_text.insert(1.0, block['content'])

        if self.current_block_id in self.assignments:
            mod = self.assignments[self.current_block_id]
            if mod in self.module_code_map:
                self.module_text.delete(1.0, tk.END)
                self.module_text.insert(1.0, self.module_code_map[mod])
        else:
            selected_display = self.module_combo.get()
            selected = self._get_clean_module_name(selected_display) if selected_display else ""
            if selected and selected in self.module_code_map:
                self.module_text.delete(1.0, tk.END)
                self.module_text.insert(1.0, self.module_code_map[selected])
            else:
                self.module_text.delete(1.0, tk.END)

        if self.current_block_id in self.assignments:
            mod = self.assignments[self.current_block_id]
            display_mod = mod
            for item in self.module_combo['values']:
                if item.startswith(mod + ' (из ') or item == mod:
                    display_mod = item
                    break
            self.module_combo.set(display_mod)
            self.action_var.set("assign_existing")
            self._on_action_change()
            self.new_module_entry.delete(0, tk.END)
        else:
            if self.has_modules and self.module_combo['values']:
                self.module_combo.current(0)
                selected_display = self.module_combo.get()
                selected = self._get_clean_module_name(selected_display)
                if selected in self.module_code_map:
                    self.module_text.delete(1.0, tk.END)
                    self.module_text.insert(1.0, self.module_code_map[selected])
            else:
                self.module_combo.set("")
            self.new_module_entry.delete(0, tk.END)
            self.action_var.set("assign_existing")
            self._on_action_change()

        self.current_applied = self.assignments.get(self.current_block_id, "")
        self.current_assign_state = self.current_applied
        self._check_changes()
        self._update_assigned_label()

    def _update_assigned_label(self):
        assigned = self.assignments.get(self.current_block_id, "")
        if assigned:
            self.assigned_label.config(text=f"Назначен модуль: {assigned}")
        else:
            self.assigned_label.config(text="")

    def _apply(self):
        if not self.current_block_id:
            return

        action = self.action_var.get()
        if action == "create_new":
            new_name = self.new_module_entry.get().strip()
            if not new_name:
                messagebox.showerror("Ошибка", "Введите имя нового модуля")
                return
            if not re.match(r'^[a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)*$', new_name):
                messagebox.showerror(
                    "Ошибка",
                    "Некорректное имя модуля. Используйте буквы, цифры, подчёркивания и точки."
                )
                return
            if new_name in self.known_modules:
                messagebox.showerror(
                    "Ошибка",
                    f"Модуль '{new_name}' уже существует. Используйте действие 'Добавить в модуль'."
                )
                return
            self.known_modules.append(new_name)
            self.known_modules.sort()
            self.has_modules = True
            current_block = self.unknown_blocks[self.current_block_index]
            source_text = f"{current_block['id']} – {current_block['display_name'].split(' – ')[-1] if ' – ' in current_block['display_name'] else current_block['display_name']}"
            self.module_info.append({'name': new_name, 'source': source_text})
            module_display_names = []
            for info in self.module_info:
                if info['source']:
                    module_display_names.append(f"{info['name']} (из {info['source']})")
                else:
                    module_display_names.append(info['name'])
            self.module_combo['values'] = module_display_names
            self.module_code_map[new_name] = self.unknown_blocks[self.current_block_index]['content']
            self.assignments[self.current_block_id] = new_name
            self.changed = True

        else:
            selected_display = self.module_combo.get()
            selected_module = self._get_clean_module_name(selected_display)
            if not selected_module:
                messagebox.showerror("Ошибка", "Выберите существующий модуль из списка")
                return
            self.assignments[self.current_block_id] = selected_module
            self.changed = True

        self.current_applied = self.assignments[self.current_block_id]
        self.apply_button.config(state="disabled")
        self.ok_button.config(state="normal")
        self._update_assigned_label()

        if self.current_block_index + 1 < len(self.unknown_blocks):
            self.current_block_index += 1
            self.current_block_id = self.unknown_blocks[self.current_block_index]['id']
            self.block_combo.current(self.current_block_index)
            self._update_display()
        else:
            self._update_display()

    def _ok(self):
        self.result = self.assignments
        self.destroy()

    def _cancel(self):
        if self.changed:
            response = messagebox.askyesno(
                "Подтверждение",
                "Есть несохранённые изменения. Закрыть без сохранения?",
                parent=self
            )
            if not response:
                return
        self.result = None
        self.destroy()

    def _on_close(self):
        if self.changed:
            response = messagebox.askyesno(
                "Подтверждение",
                "Есть несохранённые изменения. Закрыть без сохранения?",
                parent=self
            )
            if not response:
                return
        self.result = None
        self.destroy()


class ErrorBlockDialog(tk.Toplevel):
    """Диалог для исправления блока с синтаксической ошибкой."""
    def __init__(self, parent, block_info):
        super().__init__(parent)
        self.title(f"Ошибка парсинга: {block_info.block_id}")
        self.geometry("800x600")
        self.transient(parent)
        self.grab_set()

        self.block_info = block_info
        self.result = None
        self.modified = False

        # Текстовое поле с исходным кодом
        self.text = tk.Text(self, wrap=tk.NONE, font=("Courier New", 10))
        self.text.insert(1.0, block_info.content)
        self.text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.text.bind("<KeyRelease>", self._on_text_changed)

        # Кнопки
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        self.apply_button = tk.Button(btn_frame, text="Внести изменения", command=self.apply, state=tk.DISABLED)
        self.apply_button.pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Отмена", command=self.skip).pack(side=tk.LEFT, padx=5)

    def _on_text_changed(self, event=None):
        """Активирует кнопку при изменении текста."""
        current_text = self.text.get(1.0, tk.END).strip()
        original_text = self.block_info.content.strip()
        self.modified = (current_text != original_text)
        if self.modified:
            self.apply_button.config(state=tk.NORMAL)
        else:
            self.apply_button.config(state=tk.DISABLED)

    def apply(self):
        new_code = self.text.get(1.0, tk.END).strip()
        self.result = new_code
        self.destroy()

    def skip(self):
        self.result = None
        self.destroy()