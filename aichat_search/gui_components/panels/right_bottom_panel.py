# aichat_search/gui_components/panels/right_bottom_panel.py

import tkinter as tk
from .message_details_panel import MessageDetailPanel

class RightBottomPanel:
    """Нижняя правая панель: детали сообщения + кнопки навигации и метка позиции."""
    def __init__(self, parent):
        self.frame = tk.Frame(parent)
        # grid: строка 0 (детали) растягивается, строка 1 (кнопки + метка) фиксирована
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_rowconfigure(1, weight=0)
        self.frame.grid_columnconfigure(0, weight=1)

        # Панель деталей сообщения (теперь с вкладками)
        self.detail_panel = MessageDetailPanel(self.frame)
        self.detail_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Горизонтальный фрейм для кнопок и метки
        bottom_bar = tk.Frame(self.frame)
        bottom_bar.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))

        # Кнопки навигации (слева)
        self.prev_button = tk.Button(bottom_bar, text="← Предыдущая", state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.next_button = tk.Button(bottom_bar, text="Следующая →", state=tk.DISABLED)
        self.next_button.pack(side=tk.LEFT, padx=5)

        self.save_button = tk.Button(bottom_bar, text="Сохранить изменения")
        self.save_button.pack(side=tk.LEFT, padx=5)

        # Метка позиции (справа)
        self.position_label = tk.Label(bottom_bar, text="", font=("Arial", 10, "italic"))
        self.position_label.pack(side=tk.RIGHT, padx=5)