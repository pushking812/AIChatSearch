# aichat_search/gui_components/panels/message_details_panel.py

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from .. import constants

class MessageDetailPanel(tk.Frame):
    """Содержит текстовые поля запроса и ответа на вкладках."""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.text_font = tkfont.Font(size=constants.FONT_SIZE)
        self.current_pair = None
        self._create_widgets()

    def _create_widgets(self):
        # Notebook для вкладок
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Вкладка запроса
        self.request_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.request_tab, text="Запрос")
        self.request_text = tk.Text(self.request_tab, wrap=tk.WORD, font=self.text_font)
        self.request_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Вкладка ответа
        self.response_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.response_tab, text="Ответ")
        self.response_text = tk.Text(self.response_tab, wrap=tk.WORD, font=self.text_font)
        self.response_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Настройка тегов для подсветки поиска
        self.request_text.tag_configure("search_match", background=constants.SEARCH_HIGHLIGHT_COLOR)
        self.response_text.tag_configure("search_match", background=constants.SEARCH_HIGHLIGHT_COLOR)

    def display_pair(self, pair):
        """Отобразить текст пары в полях."""
        self.current_pair = pair
        self.request_text.delete("1.0", tk.END)
        self.response_text.delete("1.0", tk.END)
        self.request_text.insert(tk.END, pair.request_text)
        self.response_text.insert(tk.END, pair.response_text)

    def clear(self):
        """Очистить текстовые поля и сбросить текущую пару."""
        self.current_pair = None
        self.request_text.delete("1.0", tk.END)
        self.response_text.delete("1.0", tk.END)

    def highlight_search_match(self, field, start, end, move_focus=True):
        """Подсветить совпадение и переключить вкладку."""
        if field == "request":
            widget = self.request_text
            self.notebook.select(self.request_tab)
        else:
            widget = self.response_text
            self.notebook.select(self.response_tab)

        if move_focus:
            widget.focus_set()

        # Удаляем предыдущую подсветку
        widget.tag_remove("search_match", "1.0", tk.END)
        # Добавляем подсветку
        widget.tag_add("search_match", f"1.0 + {start} chars", f"1.0 + {end} chars")
        widget.see(f"1.0 + {start} chars")

    def get_current_texts(self):
        """Вернуть (текст запроса, текст ответа) из полей ввода."""
        return (
            self.request_text.get("1.0", "end-1c"),
            self.response_text.get("1.0", "end-1c")
        )

    def clear_highlight(self):
        """Убирает подсветку поиска в обоих текстовых полях."""
        self.request_text.tag_remove("search_match", "1.0", tk.END)
        self.response_text.tag_remove("search_match", "1.0", tk.END)