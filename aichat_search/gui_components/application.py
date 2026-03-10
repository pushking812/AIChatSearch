# aichat_search/gui_components/application.py

import os
from datetime import datetime
from tkinter import ttk
import tkinter as tk
from tkinter import filedialog, messagebox

from . import constants
from .panels.layout_builder import LayoutBuilder
from .panels.message_tree_panel import MessageTreePanel
from .managers.navigation_manager import NavigationManager
from .managers.archive_session_manager import ArchiveSessionManager
from .managers.search_bar_manager import SearchBarManager
from .search_controller import SearchController
from .window_state import WindowStateManager
from .group_handler import GroupHandler
from ..controller import ChatController
from ..services.export_manager import ExportManager
from ..tools.code_structure.controller import CodeStructureController

class Application(tk.Tk):
    def __init__(self):
        super().__init__()

        self.controller = ChatController()
        self.title("AI Chat Archive Search")
        self.geometry(f"{constants.DEFAULT_WIDTH}x{constants.DEFAULT_HEIGHT}")
        self.minsize(constants.MIN_LEFT_WIDTH + constants.MIN_RIGHT_WIDTH,
                     constants.MIN_TOP_HEIGHT + constants.MIN_BOTTOM_HEIGHT)

        self.grouping_var = tk.StringVar(value=self.controller.get_grouping_mode())

        # Построение интерфейса (панели создаются внутри)
        LayoutBuilder.build(self)

        # Создаём дерево сообщений и помещаем его в tree_frame
        self.tree_panel = MessageTreePanel(self.tree_frame, self.controller, self._on_tree_selected)

        # Контроллер поиска
        self.search_controller = SearchController(self.controller, self._on_search_result_change)

        # Менеджер поиска (размещает виджеты в search_frame)
        self.search_bar = SearchBarManager(
            parent=self.search_frame,
            app=self,
            search_controller=self.search_controller
        )

        # Менеджер навигации
        self.navigation = NavigationManager(
            controller=self.controller,
            detail_panel=self.detail_panel,
            prev_button=self.prev_button,
            next_button=self.next_button,
            position_label=self.detail_panel.position_label
        )
        self.prev_button.config(command=self.navigation.prev)
        self.next_button.config(command=self.navigation.next)

        # Менеджер архивов и сессии
        self.archive_manager = ArchiveSessionManager(
            controller=self.controller,
            tree_panel=self.tree_panel,
            detail_panel=self.detail_panel,
            on_update_callback=self._update_chat_list,
            on_clear_interface=self._clear_interface
        )
        self.save_button.config(command=self.archive_manager.save_current_pair)

        # Остальные менеджеры
        self.group_handler = GroupHandler(self, self.controller)
        self.export_manager = ExportManager(self.controller, self)
        self.state_manager = WindowStateManager(self)

        # Меню (будет вынесено позже)
        self._create_menu()

        # Загрузка сессии и обновление списка
        self.controller.load_session()
        self._update_chat_list()

        self.after_idle(self.state_manager.load_and_apply)

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    # ---------- Меню ----------
    def _create_menu(self):
        menubar = tk.Menu(self)

        # Меню Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Загрузить архив...", command=self.archive_manager.add_archive)
        file_menu.add_command(label="Новая сессия", command=self.archive_manager.new_session)
        menubar.add_cascade(label="Файл", menu=file_menu)

        # Меню Чат
        chat_menu = tk.Menu(menubar, tearoff=0)
        grouping_submenu = tk.Menu(chat_menu, tearoff=0)
        grouping_submenu.add_radiobutton(
            label="По источнику данных",
            variable=self.grouping_var,
            value="source",
            command=self._change_grouping_mode
        )
        grouping_submenu.add_radiobutton(
            label="По группе",
            variable=self.grouping_var,
            value="group",
            command=self._change_grouping_mode
        )
        grouping_submenu.add_radiobutton(
            label="По префиксу",
            variable=self.grouping_var,
            value="prefix",
            command=self._change_grouping_mode
        )
        chat_menu.add_cascade(label="Группировать", menu=grouping_submenu)
        chat_menu.add_separator()
        chat_menu.add_command(
            label="Создать/переименовать группу",
            command=lambda: self.group_handler.open_group_dialog(self._update_chat_list)
        )
        chat_menu.add_command(
            label="Добавить чат в группу",
            command=lambda: self.group_handler.assign_group_to_selected(
                self.chat_panel.get_selected_chats(),
                on_update_callback=self._update_chat_list
            )
        )
        menubar.add_cascade(label="Чат", menu=chat_menu)

        # Меню Сообщение
        self._create_message_menu(menubar)

        # Меню Инструменты
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Структура кода", command=self._open_code_structure)
        menubar.add_cascade(label="Инструменты", menu=tools_menu)

        self.config(menu=menubar)

    def _create_message_menu(self, menubar):
        message_menu = tk.Menu(menubar, tearoff=0)
        export_menu = tk.Menu(message_menu, tearoff=0)
        export_menu.add_command(
            label="В простой текст",
            command=lambda: self.export_manager.export_messages(self.tree_panel.get_selected_pairs(), 'txt')
        )
        export_menu.add_command(
            label="По блокам",
            command=lambda: self.export_manager.export_messages(self.tree_panel.get_selected_pairs(), 'blocks')
        )
        message_menu.add_cascade(label="Экспорт", menu=export_menu)
        menubar.add_cascade(label="Сообщение", menu=message_menu)

    # ---------- Обработчик изменения результата поиска ----------
    def _on_search_result_change(self, result, index, total, move_focus=True):
        chat, pair, field, start, end = result
        iid = f"{chat.id}_{pair.index}_{start}_{end}"
        if iid in self.tree_panel.tree_item_map:
            self.tree_panel.tree.selection_set(iid)
            self.tree_panel.tree.see(iid)
            self.controller.select_pair(chat, pair)
            self.detail_panel.display_pair(pair)
            self.navigation.update_position_label()
            self.navigation.update_buttons()
            self.detail_panel.highlight_search_match(field, start, end, move_focus=move_focus)
        else:
            self.controller.select_pair(chat, pair)
            self.detail_panel.display_pair(pair)
            self.navigation.update_position_label()
            self.navigation.update_buttons()
            self.detail_panel.highlight_search_match(field, start, end, move_focus=move_focus)
        self.search_bar.counter_label.config(text=f"{index + 1} / {total}")

    # ---------- Обработчики событий ----------
    def _on_chats_selected(self):
        selected = self.chat_panel.get_selected_chats()
        self.controller.reset_current_pair()
        self.tree_panel.display_chats(selected)
        self.detail_panel.clear()
        self.search_controller.clear()
        self.search_bar.counter_label.config(text="0 / 0")
        self.navigation.update_buttons()

    def _on_tree_selected(self):
        selected = self.tree_panel.get_selected_item()
        if not selected:
            return
        chat, pair, field, start, end = selected
        pair = self.controller.select_pair(chat, pair)
        if pair:
            self.detail_panel.display_pair(pair)
            self.navigation.update_position_label()
            self.navigation.update_buttons()

            if field is not None and self.search_controller.results:
                for idx, (s_chat, s_pair, s_field, s_start, s_end) in enumerate(self.search_controller.results):
                    if (s_chat is chat and s_pair is pair and 
                        s_field == field and s_start == start and s_end == end):
                        self.search_controller.current_index = idx
                        self.search_bar.counter_label.config(text=f"{idx + 1} / {len(self.search_controller.results)}")
                        self.detail_panel.highlight_search_match(field, start, end, move_focus=False)
                        break
                else:
                    self.detail_panel.highlight_search_match(field, start, end, move_focus=False)
            else:
                self.detail_panel.clear_highlight()
                if hasattr(self.search_controller, 'results') and self.search_controller.results:
                    self.search_bar.counter_label.config(text="0 / 0")

    # ---------- Группировка ----------
    def _change_grouping_mode(self):
        mode = self.grouping_var.get()
        self.controller.set_grouping_mode(mode)
        self.state_manager.save()
        self._update_chat_list()

    # ---------- Вспомогательные методы ----------
    def _update_chat_list(self):
        filtered = self.controller.get_filtered_chats()
        items = []
        for chat in filtered:
            source_name, source_time = self.controller.get_source_info(chat)
            items.append((chat, source_name, source_time))
        self.chat_panel.update_list(items)

    def _clear_interface(self):
        self.tree_panel.clear()
        self.detail_panel.clear()
        self.search_controller.clear()
        self.search_bar.counter_label.config(text="0 / 0")
        self.navigation.update_buttons()
        self.navigation.update_position_label()

    def _open_code_structure(self):
        pair = self.controller.get_current_pair()
        if pair is None:
            messagebox.showwarning("Структура кода", "Сначала выберите сообщение.")
            return
        CodeStructureController(self, pair)

    def _on_closing(self):
        self.controller.save_session()
        self.state_manager.save()
        self.destroy()