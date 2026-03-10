# aichat_search/gui_components/panels/layout_builder.py

import tkinter as tk
from .chat_tree_panel import ChatListPanel
from .message_details_panel import MessageDetailPanel
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

        # Левая панель (список чатов)
        app.left_frame = tk.Frame(app.main_paned)
        app.main_paned.add(app.left_frame, width=300, minsize=constants.MIN_LEFT_WIDTH)
        app.chat_panel = ChatListPanel(app.left_frame, app.controller, app._on_chats_selected)

        # Правая вертикальная панель
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

        # Верхняя правая панель (поиск + дерево сообщений)
        app.top_frame = tk.Frame(app.right_paned)
        app.right_paned.add(app.top_frame, height=300, minsize=constants.MIN_TOP_HEIGHT)

        # Фрейм для строки поиска
        app.search_frame = tk.Frame(app.top_frame)
        app.search_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(5, 0))

        # Фрейм для дерева сообщений
        app.tree_frame = tk.Frame(app.top_frame)
        app.tree_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        # Нижняя правая панель (детали сообщения)
        app.bottom_frame = tk.Frame(app.right_paned)
        app.right_paned.add(app.bottom_frame, minsize=constants.MIN_BOTTOM_HEIGHT)
        app.detail_panel = MessageDetailPanel(app.bottom_frame)
        app.text_paned = app.detail_panel.text_paned

        # Навигационные кнопки (внизу) - команды будут назначены позже
        nav_frame = tk.Frame(app.bottom_frame)
        nav_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        app.prev_button = tk.Button(
            nav_frame,
            text="← Предыдущая",
            state=tk.DISABLED
        )
        app.prev_button.pack(side=tk.LEFT, padx=5)
        app.next_button = tk.Button(
            nav_frame,
            text="Следующая →",
            state=tk.DISABLED
        )
        app.next_button.pack(side=tk.LEFT, padx=5)
        app.save_button = tk.Button(
            nav_frame,
            text="Сохранить изменения"
        )
        app.save_button.pack(side=tk.LEFT, padx=5)