# aichat_search/gui_components/panels/top_panel.py

import tkinter as tk
from .message_tree_panel import MessageTreePanel

class TopPanel:
    """Панель, содержащая строку поиска и дерево сообщений."""
    
    def __init__(self, parent, controller, on_tree_select_callback):
        self.parent = parent
        self.controller = controller
        self.on_tree_select = on_tree_select_callback
        
        # Основной фрейм панели
        self.frame = tk.Frame(parent)
        self.frame.grid_rowconfigure(0, weight=0)  # строка поиска не растягивается
        self.frame.grid_rowconfigure(1, weight=1)  # строка дерева растягивается
        self.frame.grid_columnconfigure(0, weight=1)
        
        # Фрейм для поиска (будет заполнен менеджером поиска)
        self.search_frame = tk.Frame(self.frame)
        self.search_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 0))
        
        # Фрейм для дерева сообщений
        self.tree_frame = tk.Frame(self.frame)
        self.tree_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
        
        # Создаём дерево сообщений
        self.tree_panel = MessageTreePanel(self.tree_frame, controller, on_tree_select_callback)