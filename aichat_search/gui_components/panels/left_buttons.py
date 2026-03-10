# aichat_search/gui_components/panels/left_buttons.py

import tkinter as tk

class LeftButtons(tk.Frame):
    """Кнопки выделения всех чатов и снятия выделения."""
    def __init__(self, parent, select_all_callback, clear_selection_callback, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.btn_select_all = tk.Button(self, text="☑", width=3, command=select_all_callback)
        self.btn_select_all.pack(side=tk.LEFT, padx=2)
        self.btn_clear = tk.Button(self, text="[ ]", width=3, command=clear_selection_callback)
        self.btn_clear.pack(side=tk.LEFT, padx=2)