# aichat_search/gui_components/panels/message_details_panel.py

import tkinter as tk
import tkinter.font as tkfont
from .. import constants

class MessageDetailPanel(tk.Frame):
    """Содержит текстовые поля запроса и ответа."""
    def __init__(self, parent, include_position_label=True, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.text_font = tkfont.Font(size=constants.FONT_SIZE)
        self.current_pair = None
        self.include_position_label = include_position_label
        self._create_widgets()

    def _create_widgets(self):
        # Метка позиции (только если включена)
        if self.include_position_label:
            self.position_label = tk.Label(self, text="", font=("Arial", 10, "italic"))
            self.position_label.pack(anchor="w", padx=5, pady=(5, 0))

        # Панель с текстами (вертикальная)
        self.text_paned = tk.PanedWindow(
            self,
            orient=tk.VERTICAL,
            sashrelief=tk.RAISED,
            sashwidth=constants.SASH_WIDTH,
            bd=1,
            relief=tk.SUNKEN,
            showhandle=True,
        )
        self.text_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Контейнер запроса
        request_container = tk.Frame(self.text_paned)
        tk.Label(request_container, text="Запрос", font=("Arial", 11, "bold")).pack(anchor="w", padx=5)
        self.request_text = tk.Text(request_container, height=10, font=self.text_font)
        self.request_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Контейнер ответа
        response_container = tk.Frame(self.text_paned)
        tk.Label(response_container, text="Ответ", font=("Arial", 11, "bold")).pack(anchor="w", padx=5)
        self.response_text = tk.Text(response_container, height=10, font=self.text_font)
        self.response_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.text_paned.add(request_container, minsize=constants.MIN_REQUEST_HEIGHT)
        self.text_paned.add(response_container, minsize=constants.MIN_RESPONSE_HEIGHT)

        # Настройка тегов для подсветки поиска
        self.request_text.tag_configure("search_match", background=constants.SEARCH_HIGHLIGHT_COLOR)
        self.response_text.tag_configure("search_match", background=constants.SEARCH_HIGHLIGHT_COLOR)

    def display_pair(self, pair):
        self.current_pair = pair
        self.request_text.delete("1.0", tk.END)
        self.response_text.delete("1.0", tk.END)
        self.request_text.insert(tk.END, pair.request_text)
        self.response_text.insert(tk.END, pair.response_text)

    def clear(self):
        self.current_pair = None
        self.request_text.delete("1.0", tk.END)
        self.response_text.delete("1.0", tk.END)

    def set_position_label(self, text):
        if hasattr(self, 'position_label'):
            self.position_label.config(text=text)

    def highlight_search_match(self, field, start, end, move_focus=True):
        widget = self.request_text if field == "request" else self.response_text
        if move_focus:
            widget.focus_set()
        widget.tag_remove("search_match", "1.0", tk.END)
        widget.tag_add("search_match", f"1.0 + {start} chars", f"1.0 + {end} chars")
        widget.see(f"1.0 + {start} chars")

    def get_current_texts(self):
        return (
            self.request_text.get("1.0", "end-1c"),
            self.response_text.get("1.0", "end-1c")
        )

    def clear_highlight(self):
        self.request_text.tag_remove("search_match", "1.0", tk.END)
        self.response_text.tag_remove("search_match", "1.0", tk.END)