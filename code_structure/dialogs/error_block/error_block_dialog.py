# code_structure/dialogs/error_block/error_block_dialog.py

import tkinter as tk
from tkinter import messagebox
import textwrap

from code_structure.dialogs.dialog_interfaces import ErrorBlockView
from code_structure.dialogs.error_block.error_block_presenter import ErrorBlockPresenter
from code_structure.dialogs.dto import ErrorBlockInput


class ErrorBlockDialog(tk.Toplevel, ErrorBlockView):
    def __init__(self, parent, input_data: ErrorBlockInput):
        super().__init__(parent)
        self.title(f"Ошибка парсинга: {input_data.block_id}")
        self.geometry("800x600")
        self.transient(parent)
        self.grab_set()

        self.presenter = ErrorBlockPresenter(self)
        self._create_widgets()
        
        self.presenter.initialize(input_data)
        
        # Показываем сообщение об ошибке при открытии
        self._show_initial_error(input_data)

        self.result = None

    def _show_initial_error(self, input_data: ErrorBlockInput):
        """Показывает сообщение об ошибке при открытии диалога."""
        from code_structure.parsing.core.parser import PythonParser
        parser = PythonParser()
        try:
            from code_structure.models.block import Block
            temp_block = Block(
                chat=input_data.chat,
                message_pair=input_data.message_pair,
                language=input_data.language,
                content=input_data.original_code,
                block_idx=0,
                global_index=0
            )
            parser.parse(temp_block)
        except SyntaxError as e:
            messagebox.showerror("Синтаксическая ошибка", str(e), parent=self)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def _create_widgets(self):
        # Текстовое поле
        self.text = tk.Text(self, wrap=tk.NONE, font=("Courier New", 10))
        self.text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.text.bind("<KeyRelease>", self._on_text_changed)

        # Кнопки
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        self.apply_button = tk.Button(btn_frame, text="Внести изменения", command=self._apply, state=tk.DISABLED)
        self.apply_button.pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Отмена", command=self._skip).pack(side=tk.LEFT, padx=5)

    def show_code(self, code: str):
        self.text.delete(1.0, tk.END)
        self.text.insert(1.0, code)

    def get_modified_code(self) -> str:
        return self.text.get(1.0, tk.END).strip()

    def enable_apply_button(self, enabled: bool):
        self.apply_button.config(state=tk.NORMAL if enabled else tk.DISABLED)

    def show_error(self, message: str):
        messagebox.showerror("Ошибка", message, parent=self)

    def close(self):
        self.result = self.presenter.result
        self.destroy()

    def _on_text_changed(self, event=None):
        self.presenter.on_text_changed(self.get_modified_code())

    def _apply(self):
        self.presenter.on_apply()

    def _skip(self):
        self.presenter.on_skip()
        self.result = None