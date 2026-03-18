# aichat_search/tools/code_structure/ui/error_block_dialog.py

import tkinter as tk
from tkinter import ttk

from aichat_search.tools.code_structure.ui.dialog_interfaces import ErrorBlockView
from aichat_search.tools.code_structure.ui.error_block_presenter import ErrorBlockPresenter


class ErrorBlockDialog(tk.Toplevel, ErrorBlockView):
    """Диалог для исправления блока с синтаксической ошибкой."""
    
    def __init__(self, parent, block_info):
        super().__init__(parent)
        self.title(f"Ошибка парсинга: {block_info.block_id}")
        self.geometry("800x600")
        self.transient(parent)
        self.grab_set()

        # Создаём презентер
        self.presenter = ErrorBlockPresenter(self)
        
        # Создаём UI
        self._create_widgets()
        
        # Инициализация
        self.presenter.initialize(block_info)
        
        self.result = None

    def _create_widgets(self):
        """Создаёт виджеты."""
        # Текстовое поле с исходным кодом
        self.text = tk.Text(self, wrap=tk.NONE, font=("Courier New", 10))
        self.text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.text.bind("<KeyRelease>", self._on_text_changed)

        # Кнопки
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        self.apply_button = tk.Button(btn_frame, text="Внести изменения", command=self._apply, state=tk.DISABLED)
        self.apply_button.pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Отмена", command=self._skip).pack(side=tk.LEFT, padx=5)

    # === Реализация интерфейса ErrorBlockView ===
    
    def show_code(self, code: str):
        """Показывает код для редактирования."""
        self.text.delete(1.0, tk.END)
        self.text.insert(1.0, code)
    
    def get_modified_code(self) -> str:
        """Возвращает изменённый код."""
        return self.text.get(1.0, tk.END).strip()
    
    def enable_apply_button(self, enabled: bool):
        """Включает/отключает кнопку Apply."""
        self.apply_button.config(state=tk.NORMAL if enabled else tk.DISABLED)
    
    def close(self):
        """Закрывает диалог."""
        self.destroy()
    
    # === Обработчики событий ===
    
    def _on_text_changed(self, event=None):
        self.presenter.on_text_changed(self.get_modified_code())
    
    def _apply(self):
        self.presenter.on_apply()
        self.result = self.presenter.result
    
    def _skip(self):
        self.presenter.on_skip()
        self.result = None