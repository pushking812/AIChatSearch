# aichat_search/gui_components/application.py

import tkinter as tk
from tkinter import messagebox

from aichat_search.gui_components import constants
from aichat_search.gui_components.panels.layout_builder import LayoutBuilder
from aichat_search.gui_components.managers.navigation_manager import NavigationManager
from aichat_search.gui_components.managers.archive_session_manager import ArchiveSessionManager
from aichat_search.gui_components.managers.search_bar_manager import SearchBarManager
from aichat_search.gui_components.managers.menu_manager import MenuManager
from aichat_search.gui_components.managers.window_state_manager import WindowStateManager
from aichat_search.gui_components.controllers.search_controller import SearchController
from aichat_search.gui_components.group_management.group_handler import GroupHandler
from aichat_search.controller import ChatController
from aichat_search.services.export_manager import ExportManager
from code_structure.controller import CodeStructureController

class Application(tk.Tk):
    def __init__(self):
        super().__init__()

        self.controller = ChatController()
        self.title("AI Chat Archive Search")
        self.geometry(f"{constants.DEFAULT_WIDTH}x{constants.DEFAULT_HEIGHT}")
        self.minsize(constants.MIN_LEFT_WIDTH + constants.MIN_RIGHT_WIDTH,
                     constants.MIN_TOP_HEIGHT + constants.MIN_BOTTOM_HEIGHT)

        self.grouping_var = tk.StringVar(value=self.controller.get_grouping_mode())

        # Построение интерфейса
        LayoutBuilder.build(self)

        # Привязка команд к левым кнопкам
        self.left_buttons.btn_select_all.config(command=self._select_all_chats)
        self.left_buttons.btn_clear.config(command=self._clear_chat_selection)

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
            position_label=self.position_label   # метка из нижней панели
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

        # Менеджер меню
        self.menu_manager = MenuManager(
            archive_manager=self.archive_manager,
            group_handler=self.group_handler,
            export_manager=self.export_manager,
            grouping_var=self.grouping_var,
            on_grouping_change=self._change_grouping_mode,
            open_code_structure=self._open_code_structure,
            get_selected_chats_callback=lambda: self.left_tree.get_selected_chats(),
            get_selected_pairs_callback=lambda: self.tree_panel.get_selected_pairs(),
            on_update_callback=self._update_chat_list
        )
        menubar = tk.Menu(self)
        self.menu_manager.build_menu(menubar)
        self.config(menu=menubar)

        # Загрузка сессии и обновление списка
        self.controller.load_session()
        self._update_chat_list()

        self.after_idle(self.state_manager.load_and_apply)

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    # ---------- Обработчики левой панели ----------
    def _on_filter_changed(self, event=None):
        query = self.left_filter.get_filter_text()
        self.controller.filter_chats(query)
        self._update_chat_list()
        self._clear_chat_selection()

    def _select_all_chats(self):
        self.left_tree.tree.selection_set(list(self.left_tree._item_to_chat.keys()))
        self._on_chats_selected()

    def _clear_chat_selection(self):
        self.left_tree.tree.selection_set(())
        self._on_chats_selected()

    def _on_chats_selected(self):
        selected = self.left_tree.get_selected_chats()
        self.controller.reset_current_pair()
        self.tree_panel.display_chats(selected)
        self.detail_panel.clear()
        self.search_controller.clear()
        self.search_bar.counter_label.config(text="0 / 0")
        self.navigation.update_buttons()

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
        self.left_tree.update_list(items)

    def _clear_interface(self):
        self.tree_panel.clear()
        self.detail_panel.clear()
        self.search_controller.clear()
        self.search_bar.counter_label.config(text="0 / 0")
        self.navigation.update_buttons()
        self.navigation.update_position_label()

    def _open_code_structure(self):
        """Открывает окно структуры кода для выделенных пар сообщений."""
        selected_pairs = self.tree_panel.get_selected_pairs()
        if not selected_pairs:
            messagebox.showwarning(
                "Структура кода",
                "Сначала выберите одно или несколько сообщений в правой панели."
            )
            return

        items = []
        for item in selected_pairs:
            # item = (chat, pair, field, start, end) — как возвращает get_selected_pairs
            if isinstance(item, (tuple, list)) and len(item) >= 2:
                chat, pair = item[0], item[1]
                if hasattr(pair, 'response_text'):
                    items.append((chat, pair))

        if items:
            CodeStructureController(self, items)
        else:
            messagebox.showwarning(
                "Структура кода",
                "Не удалось извлечь данные из выбранных элементов."
            )

    def _on_closing(self):
        self.controller.save_session()
        self.state_manager.save()
        self.destroy()