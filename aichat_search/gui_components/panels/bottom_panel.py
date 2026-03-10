# aichat_search/gui_components/panels/bottom_panel.py

import tkinter as tk
from .message_details_panel import MessageDetailPanel

class BottomPanel:
    """Панель, содержащая детали сообщения и кнопки навигации."""
    
    def __init__(self, parent):
        self.parent = parent
        
        # Основной фрейм панели
        self.frame = tk.Frame(parent)
        self.frame.grid_rowconfigure(0, weight=1)  # строка текстовых полей растягивается
        self.frame.grid_rowconfigure(1, weight=0)  # строка кнопок не растягивается
        self.frame.grid_columnconfigure(0, weight=1)
        
        # Панель деталей сообщения (теперь это наследник Frame)
        self.detail_panel = MessageDetailPanel(self.frame)
        self.detail_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Фрейм с кнопками навигации
        nav_frame = tk.Frame(self.frame)
        nav_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        
        # Создаём кнопки (команды будут назначены позже в application.py)
        self.prev_button = tk.Button(
            nav_frame,
            text="← Предыдущая",
            state=tk.DISABLED
        )
        self.prev_button.pack(side=tk.LEFT, padx=5)
        
        self.next_button = tk.Button(
            nav_frame,
            text="Следующая →",
            state=tk.DISABLED
        )
        self.next_button.pack(side=tk.LEFT, padx=5)
        
        self.save_button = tk.Button(
            nav_frame,
            text="Сохранить изменения"
        )
        self.save_button.pack(side=tk.LEFT, padx=5)