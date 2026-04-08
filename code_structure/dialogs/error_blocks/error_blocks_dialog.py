# code_structure/dialogs/error_blocks/error_blocks_dialog.py

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional

from code_structure.dialogs.dialog_interfaces import ErrorBlocksView
from code_structure.dialogs.error_blocks.error_blocks_presenter import ErrorBlocksPresenter
from code_structure.dialogs.dto import ErrorBlockInfo, ErrorBlocksInput, ErrorBlocksOutput


class ErrorBlocksDialog(tk.Toplevel, ErrorBlocksView):
    def __init__(self, parent, input_data: ErrorBlocksInput):
        super().__init__(parent)
        self.title("Исправление синтаксических ошибок")
        self.geometry("1000x600")
        self.minsize(800, 400)
        self.transient(parent)
        self.grab_set()

        self.presenter = ErrorBlocksPresenter(self)
        self._create_widgets()
        self.presenter.initialize(input_data)

        self.result = None

    def _create_widgets(self):
        default_font = ("Segoe UI", 9)
        self.option_add("*Font", default_font)
        
        style = ttk.Style()
        style.configure(".", font=("Segoe UI", 9))   # глобально для всех ttk виджетов
        style.configure("TLabel", font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 9))
        style.configure("TCombobox", font=("Segoe UI", 9))

        main_frame = ttk.Frame(self, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)

        paned = tk.PanedWindow(main_frame, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=6, bd=0)
        paned.pack(fill=tk.BOTH, expand=True)

        # Левая панель: список блоков
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, width=300, minsize=200)
        left_frame.pack_propagate(False)
        left_frame.rowconfigure(1, weight=1)
        left_frame.columnconfigure(0, weight=1)

        ttk.Label(left_frame, text="Блоки с синтаксическими ошибками:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        self.listbox = tk.Listbox(left_frame)
        self.listbox.grid(row=1, column=0, sticky="nsew")
        self.listbox.bind("<<ListboxSelect>>", self._on_block_selected)

        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.listbox.config(yscrollcommand=scrollbar.set)

        # Правая панель: текстовый редактор
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, width=600, minsize=400)
        right_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)

        ttk.Label(right_frame, text="Код выбранного блока (можно редактировать):").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        self.text = tk.Text(right_frame, wrap=tk.NONE)
        self.text.grid(row=1, column=0, sticky="nsew")
        self.text.bind("<KeyRelease>", self._on_text_changed)

        # Кнопки
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        self.apply_button = ttk.Button(btn_frame, text="Применить", command=self._apply, state=tk.DISABLED)
        self.apply_button.pack(side=tk.LEFT, padx=5)

        self.delete_button = ttk.Button(btn_frame, text="Удалить", command=self._delete, state=tk.DISABLED)
        self.delete_button.pack(side=tk.LEFT, padx=5)

        self.ok_button = ttk.Button(btn_frame, text="ОК", command=self._ok)
        self.ok_button.pack(side=tk.RIGHT, padx=5)

        self.cancel_button = ttk.Button(btn_frame, text="Отмена", command=self._cancel)
        self.cancel_button.pack(side=tk.RIGHT, padx=5)

        self._block_ids = []

    def set_blocks(self, blocks: List[ErrorBlockInfo]):
        self.listbox.delete(0, tk.END)
        self._block_ids = []
        for block in blocks:
            display_name = f"{block.block_id} – {block.language}"
            self.listbox.insert(tk.END, display_name)
            self._block_ids.append(block.block_id)

        if blocks:
            self.listbox.selection_set(0)
            self._on_block_selected()
        else:
            self.delete_button.config(state=tk.DISABLED)
            self.apply_button.config(state=tk.DISABLED)

    def get_selected_block_id(self) -> Optional[str]:
        selection = self.listbox.curselection()
        if not selection:
            return None
        idx = selection[0]
        if 0 <= idx < len(self._block_ids):
            return self._block_ids[idx]
        return None

    def show_block_code(self, code: str):
        self.text.delete(1.0, tk.END)
        self.text.insert(1.0, code)

    def get_modified_code(self) -> str:
        return self.text.get(1.0, tk.END).strip()

    def enable_apply_button(self, enabled: bool):
        self.apply_button.config(state=tk.NORMAL if enabled else tk.DISABLED)

    def show_error(self, message: str):
        messagebox.showerror("Ошибка", message, parent=self)

    def close(self, result: Optional[ErrorBlocksOutput]):
        self.result = result
        self.destroy()

    def _on_block_selected(self, event=None):
        block_id = self.get_selected_block_id()
        if block_id:
            self.delete_button.config(state=tk.NORMAL)
            self.presenter.on_block_selected(block_id)
        else:
            self.delete_button.config(state=tk.DISABLED)

    def _on_text_changed(self, event):
        self.presenter.on_text_changed(self.get_modified_code())

    def _apply(self):
        self.presenter.on_apply()

    def _delete(self):
        self.presenter.on_delete()
        if not self.listbox.curselection():
            self.delete_button.config(state=tk.DISABLED)

    def _ok(self):
        self.presenter.on_ok()

    def _cancel(self):
        self.presenter.on_cancel()