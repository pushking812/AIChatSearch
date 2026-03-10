import tkinter as tk
from .chat_tree_panel import ChatListPanel
from .message_tree_panel import MessageTreePanel
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

        # Верхняя правая панель (дерево сообщений)
        app.top_frame = tk.Frame(app.right_paned)
        app.right_paned.add(app.top_frame, height=300, minsize=constants.MIN_TOP_HEIGHT)
        app.tree_panel = MessageTreePanel(app.top_frame, app.controller, app._on_tree_selected)

        # Нижняя правая панель (детали сообщения)
        app.bottom_frame = tk.Frame(app.right_paned)
        app.right_paned.add(app.bottom_frame, minsize=constants.MIN_BOTTOM_HEIGHT)
        app.detail_panel = MessageDetailPanel(app.bottom_frame)
        app.text_paned = app.detail_panel.text_paned

        # Навигационные кнопки (внизу)
        nav_frame = tk.Frame(app.bottom_frame)
        nav_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        app.prev_button = tk.Button(
            nav_frame,
            text="← Предыдущая",
            command=app.prev_pair,
            state=tk.DISABLED
        )
        app.prev_button.pack(side=tk.LEFT, padx=5)
        app.next_button = tk.Button(
            nav_frame,
            text="Следующая →",
            command=app.next_pair,
            state=tk.DISABLED
        )
        app.next_button.pack(side=tk.LEFT, padx=5)
        app.save_button = tk.Button(
            nav_frame,
            text="Сохранить изменения",
            command=app.save_current_pair
        )
        app.save_button.pack(side=tk.LEFT, padx=5)