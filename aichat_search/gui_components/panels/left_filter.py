# aichat_search/gui_components/panels/left_filter.py

import tkinter as tk

class LeftFilter(tk.Frame):
    """Строка поиска (фильтра) чатов."""
    def __init__(self, parent, on_filter_changed_callback, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.filter_var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.filter_var)
        self.entry.pack(fill=tk.X, expand=True)
        self.entry.bind('<KeyRelease>', on_filter_changed_callback)

    def get_filter_text(self):
        return self.filter_var.get()