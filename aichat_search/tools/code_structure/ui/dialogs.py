# aichat_search/tools/code_structure/ui/dialogs.py

import re
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Optional, Any


class ModuleAssignmentDialog(tk.Toplevel):
    """
    Диалог для ручного назначения модулей блокам без автоматической подсказки.
    """

    def __init__(
        self,
        parent,
        unknown_blocks: List[Dict[str, Any]],  # каждый элемент: {'id': str, 'display_name': str, 'content': str}
        known_modules: List[str],
        module_code_map: Optional[Dict[str, str]] = None  # имя модуля -> пример кода для отображения
    ):
        super().__init__(parent)
        self.title("Назначение модулей")
        self.geometry("1100x750")
        self.minsize(1100, 750)
        self.transient(parent)
        self.grab_set()

        self.unknown_blocks = unknown_blocks
        self.known_modules = sorted(known_modules)
        self.has_modules = bool(self.known_modules)
        self.module_code_map = module_code_map or {}
        self.assignments: Dict[str, str] = {}
        self.changed = False
        self.result = None

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

        # Привязываем внутренний фрейм к canvas и задаём тег
        self.canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw",
            tags=("inner_frame",)
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # При изменении размера canvas обновляем ширину внутреннего фрейма
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_canvas_configure(self, event):
        """Обновляет ширину внутреннего фрейма при изменении размера canvas."""
        self.canvas.itemconfig("inner_frame", width=event.width)

    def _create_widgets(self):
        # Верхняя панель: выбор блока и модуля
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

        ttk.Label(top_frame, text="Назначить модулю:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.module_combo = ttk.Combobox(
            top_frame,
            values=self.known_modules,
            state="readonly" if self.has_modules else "disabled",
            width=40
        )
        self.module_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        self.module_combo.bind("<<ComboboxSelected>>", self._on_module_selected)

        self.assigned_label = ttk.Label(top_frame, text="", foreground="blue")
        self.assigned_label.grid(row=1, column=2, padx=10, sticky=tk.W)

        # Панель с двумя текстовыми полями
        text_frame = ttk.Frame(self.scrollable_frame)
        text_frame.grid(row=2, column=0, sticky="nsew", pady=10, padx=10)
        text_frame.columnconfigure(0, weight=1)
        text_frame.columnconfigure(1, weight=1)
        text_frame.rowconfigure(0, weight=1)

        # Левое поле (код выбранного блока)
        left_frame = ttk.LabelFrame(text_frame, text="Код выбранного блока")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5)
        left_frame.rowconfigure(0, weight=1)
        left_frame.columnconfigure(0, weight=1)

        self.block_text = tk.Text(left_frame, wrap=tk.NONE, font=("Courier New", 10))
        block_scroll_y = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.block_text.yview)
        block_scroll_x = ttk.Scrollbar(left_frame, orient=tk.HORIZONTAL, command=self.block_text.xview)
        self.block_text.configure(yscrollcommand=block_scroll_y.set, xscrollcommand=block_scroll_x.set)

        self.block_text.grid(row=0, column=0, sticky="nsew")
        block_scroll_y.grid(row=0, column=1, sticky="ns")
        block_scroll_x.grid(row=1, column=0, sticky="ew")

        # Правое поле (код выбранного модуля)
        right_frame = ttk.LabelFrame(text_frame, text="Код выбранного модуля (пример)")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5)
        right_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)

        self.module_text = tk.Text(right_frame, wrap=tk.NONE, font=("Courier New", 10))
        module_scroll_y = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.module_text.yview)
        module_scroll_x = ttk.Scrollbar(right_frame, orient=tk.HORIZONTAL, command=self.module_text.xview)
        self.module_text.configure(yscrollcommand=module_scroll_y.set, xscrollcommand=module_scroll_x.set)

        self.module_text.grid(row=0, column=0, sticky="nsew")
        module_scroll_y.grid(row=0, column=1, sticky="ns")
        module_scroll_x.grid(row=1, column=0, sticky="ew")

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
        selected = self.module_combo.get()
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
            return self.module_combo.get()

    def _update_display(self):
        if not self.unknown_blocks:
            return
        block = self.unknown_blocks[self.current_block_index]
        self.block_text.delete(1.0, tk.END)
        self.block_text.insert(1.0, block['content'])

        # Если есть ранее назначенный модуль, показываем его код
        if self.current_block_id in self.assignments:
            mod = self.assignments[self.current_block_id]
            if mod in self.module_code_map:
                self.module_text.delete(1.0, tk.END)
                self.module_text.insert(1.0, self.module_code_map[mod])
        else:
            # Если модуль не назначен, пытаемся показать код выбранного в комбобоксе
            selected_mod = self.module_combo.get()
            if selected_mod and selected_mod in self.module_code_map:
                self.module_text.delete(1.0, tk.END)
                self.module_text.insert(1.0, self.module_code_map[selected_mod])
            else:
                self.module_text.delete(1.0, tk.END)

        # Восстанавливаем ранее назначенный модуль, если есть
        if self.current_block_id in self.assignments:
            mod = self.assignments[self.current_block_id]
            if mod in self.known_modules:
                self.module_combo.set(mod)
                self.action_var.set("assign_existing")
                self._on_action_change()
                self.new_module_entry.delete(0, tk.END)
            else:
                self.module_combo.set("")
                self.new_module_entry.delete(0, tk.END)
                self.new_module_entry.insert(0, mod)
                self.action_var.set("create_new")
                self._on_action_change()
        else:
            if self.has_modules:
                self.module_combo.current(0)
                selected_mod = self.module_combo.get()
                if selected_mod in self.module_code_map:
                    self.module_text.delete(1.0, tk.END)
                    self.module_text.insert(1.0, self.module_code_map[selected_mod])
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
            self.module_combo['values'] = self.known_modules
            self.assignments[self.current_block_id] = new_name
            self.changed = True

        else:
            selected_module = self.module_combo.get()
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