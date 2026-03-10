# aichat_search/gui_components/panels/layout_builder.py

import tkinter as tk
from .left_filter import LeftFilter
from .left_chat_tree import LeftChatTree
from .left_buttons import LeftButtons
from .right_top_panel import RightTopPanel
from .right_bottom_panel import RightBottomPanel
from .. import constants

class LayoutBuilder:
    @staticmethod
    def build(app):
        # Главная горизонтальная панель
        app.main_paned = tk.PanedWindow(
            app,
            orient=tk.HORIZONTAL,
            sashrelief=tk.RAISED,
            sashwidth=constants.SASH_WIDTH,
            bd=1,
            relief=tk.SUNKEN,
            showhandle=True,
        )
        app.main_paned.pack(fill=tk.BOTH, expand=True)

        # === Левая панель ===
        app.left_frame = tk.Frame(app.main_paned)
        app.main_paned.add(app.left_frame, width=300, minsize=constants.MIN_LEFT_WIDTH)
        # Левая панель использует grid: три строки
        app.left_frame.grid_rowconfigure(0, weight=0)  # фильтр
        app.left_frame.grid_rowconfigure(1, weight=1)  # дерево чатов
        app.left_frame.grid_rowconfigure(2, weight=0)  # кнопки
        app.left_frame.grid_columnconfigure(0, weight=1)

        # Фильтр
        app.left_filter = LeftFilter(app.left_frame, app._on_filter_changed)
        app.left_filter.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Дерево чатов
        app.left_tree = LeftChatTree(app.left_frame, app.controller, app._on_chats_selected)
        app.left_tree.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Кнопки
        app.left_buttons = LeftButtons(app.left_frame, app._select_all_chats, app._clear_chat_selection)
        app.left_buttons.grid(row=2, column=0, sticky="ew", padx=5, pady=5)

        # === Правая вертикальная панель ===
        app.right_paned = tk.PanedWindow(
            app.main_paned,
            orient=tk.VERTICAL,
            sashrelief=tk.RAISED,
            sashwidth=constants.SASH_WIDTH,
            bd=1,
            relief=tk.SUNKEN,
            showhandle=True,
        )
        app.main_paned.add(app.right_paned, minsize=constants.MIN_RIGHT_WIDTH)

        # Верхняя правая панель
        app.right_top_panel = RightTopPanel(app.right_paned, app.controller, app._on_tree_selected)
        app.right_paned.add(app.right_top_panel.frame, height=300, minsize=constants.MIN_TOP_HEIGHT)
        # Извлекаем атрибуты для совместимости
        app.search_frame = app.right_top_panel.search_frame
        app.tree_frame = app.right_top_panel.tree_frame
        app.tree_panel = app.right_top_panel.tree_panel

        # Нижняя правая панель
        app.right_bottom_panel = RightBottomPanel(app.right_paned)
        app.right_paned.add(app.right_bottom_panel.frame, minsize=constants.MIN_BOTTOM_HEIGHT)
        app.detail_panel = app.right_bottom_panel.detail_panel
        app.position_label = app.right_bottom_panel.position_label
        app.prev_button = app.right_bottom_panel.prev_button
        app.next_button = app.right_bottom_panel.next_button
        app.save_button = app.right_bottom_panel.save_button
        app.text_paned = app.detail_panel.text_paned