# aichat_search/gui_components/application.py

"""Главный класс приложения, координирующий работу всех компонентов."""

import os
from datetime import datetime
from tkinter import ttk
import tkinter as tk
from tkinter import filedialog, messagebox

from . import constants
from .chat_list import ChatListPanel
from .message_tree import MessageTreePanel
from .message_detail import MessageDetailPanel
from .search_controller import SearchController
from .window_state import WindowStateManager
from .group_handler import GroupHandler  # новый импорт
from ..controller import ChatController
from ..services.export_manager import ExportManager
from ..tools.code_structure.controller import CodeStructureController


class Application(tk.Tk):
    """Основное окно приложения."""

    def __init__(self):
        super().__init__()

        self.controller = ChatController()
        self.title("AI Chat Archive Search")
        self.geometry(f"{constants.DEFAULT_WIDTH}x{constants.DEFAULT_HEIGHT}")
        self.minsize(constants.MIN_LEFT_WIDTH + constants.MIN_RIGHT_WIDTH,
                     constants.MIN_TOP_HEIGHT + constants.MIN_BOTTOM_HEIGHT)

        # Переменная для режима группировки
        self.grouping_var = tk.StringVar(value=self.controller.get_grouping_mode())

        # Инициализация компонентов
        self._create_menu()
        self._create_layout()
        self.search_ctrl = SearchController(self.controller, self._on_search_result_change)

        self.controller.load_session()
        self._update_chat_list()

        self.state_manager = WindowStateManager(self)
        self.after_idle(self.state_manager.load_and_apply)

        self.export_manager = ExportManager(self.controller, self)
        self.group_handler = GroupHandler(self, self.controller)  # создаём обработчик групп

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    # ---------- Инициализация ----------
    def _create_menu(self):
        menubar = tk.Menu(self)

        # Меню Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Загрузить архив...", command=self.add_archive)
        file_menu.add_command(label="Новая сессия", command=self.new_session)
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

        self.config(menu=menubar)
        
        # Меню Инструменты
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Структура кода", command=self._open_code_structure)
        menubar.add_cascade(label="Инструменты", menu=tools_menu)

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

    def _create_layout(self):
        self._create_main_paned()
        self._create_left_panel()
        self._create_right_paned()
        self._create_top_panel()
        self._create_bottom_panel()

        self.left_frame = self.left_frame
        self.top_frame = self.top_frame
        self.bottom_frame = self.bottom_frame
        self.request_container = self.detail_panel.request_text.master
        self.response_container = self.detail_panel.response_text.master

    def _create_main_paned(self):
        self.main_paned = tk.PanedWindow(
            self,
            orient=tk.HORIZONTAL,
            sashrelief=tk.RAISED,
            sashwidth=constants.SASH_WIDTH,
            bd=1,
            relief=tk.SUNKEN,
            showhandle=True,
        )
        self.main_paned.pack(fill=tk.BOTH, expand=True)

    def _create_left_panel(self):
        self.left_frame = tk.Frame(self.main_paned)
        self.main_paned.add(self.left_frame, width=300, minsize=constants.MIN_LEFT_WIDTH)
        self.chat_panel = ChatListPanel(self.left_frame, self.controller, self._on_chats_selected)

    def _create_right_paned(self):
        self.right_paned = tk.PanedWindow(
            self.main_paned,
            orient=tk.VERTICAL,
            sashrelief=tk.RAISED,
            sashwidth=constants.SASH_WIDTH,
            bd=1,
            relief=tk.SUNKEN,
            showhandle=True,
        )
        self.main_paned.add(self.right_paned, minsize=constants.MIN_RIGHT_WIDTH)

    def _create_top_panel(self):
        self.top_frame = tk.Frame(self.right_paned)
        self.right_paned.add(self.top_frame, height=300, minsize=constants.MIN_TOP_HEIGHT)
        self._create_search_bar(self.top_frame)
        self.tree_panel = MessageTreePanel(self.top_frame, self.controller, self._on_tree_selected)

    def _create_bottom_panel(self):
        self.bottom_frame = tk.Frame(self.right_paned)
        self.right_paned.add(self.bottom_frame, minsize=constants.MIN_BOTTOM_HEIGHT)
        self.detail_panel = MessageDetailPanel(self.bottom_frame)
        self.text_paned = self.detail_panel.text_paned

        nav_frame = tk.Frame(self.bottom_frame)
        nav_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.prev_button = tk.Button(nav_frame, text="← Предыдущая", command=self.prev_pair, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.next_button = tk.Button(nav_frame, text="Следующая →", command=self.next_pair, state=tk.DISABLED)
        self.next_button.pack(side=tk.LEFT, padx=5)

        self.save_button = tk.Button(nav_frame, text="Сохранить изменения", command=self.save_current_pair)
        self.save_button.pack(side=tk.LEFT, padx=5)

    def _create_search_bar(self, parent):
        search_frame = tk.Frame(parent)
        search_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.search_var = tk.StringVar()
        self.search_field_var = tk.StringVar(value="Запрос")
        self.live_search_var = tk.BooleanVar(value=True)

        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.bind('<KeyRelease>', lambda e: self._on_search_key(e))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.search_combobox = ttk.Combobox(
            search_frame,
            textvariable=self.search_field_var,
            values=["Запрос", "Ответ"],
            state="readonly",
            width=18
        )
        self.search_combobox.pack(side=tk.LEFT, padx=(0, 5))

        tk.Button(search_frame, text="Найти", command=self._perform_search).pack(side=tk.LEFT, padx=(0, 5))
        tk.Checkbutton(search_frame, text="Live", variable=self.live_search_var).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="<", width=2, command=self._prev_search_result).pack(side=tk.LEFT)
        tk.Button(search_frame, text=">", width=2, command=self._next_search_result).pack(side=tk.LEFT)
        self.search_counter = tk.Label(search_frame, text="0 / 0")
        self.search_counter.pack(side=tk.LEFT, padx=5)

    # ---------- Вспомогательные методы для обновления интерфейса ----------
    def _update_chat_list(self):
        filtered = self.controller.get_filtered_chats()
        items = []
        for chat in filtered:
            source_name, source_time = self.controller.get_source_info(chat)
            items.append((chat, source_name, source_time))
        self.chat_panel.update_list(items)

    # ---------- Обработчики событий ----------
    def _on_chats_selected(self):
        selected = self.chat_panel.get_selected_chats()
        self.tree_panel.display_chats(selected)
        self.detail_panel.clear()
        self.search_ctrl.clear()
        self.search_counter.config(text="0 / 0")
        self._update_nav_buttons()

    def _on_tree_selected(self):
        selected = self.tree_panel.get_selected_item()
        if not selected:
            return
        chat, pair, field, start, end = selected
        pair = self.controller.select_pair(chat, pair)
        if pair:
            self.detail_panel.display_pair(pair)
            self._update_position_label()
            self._update_nav_buttons()

            if field is not None and self.search_ctrl.results:
                for idx, (s_chat, s_pair, s_field, s_start, s_end) in enumerate(self.search_ctrl.results):
                    if (s_chat is chat and s_pair is pair and 
                        s_field == field and s_start == start and s_end == end):
                        self.search_ctrl.current_index = idx
                        self.search_counter.config(text=f"{idx + 1} / {len(self.search_ctrl.results)}")
                        self.detail_panel.highlight_search_match(field, start, end, move_focus=False)
                        break
                else:
                    self.detail_panel.highlight_search_match(field, start, end, move_focus=False)
            else:
                self.detail_panel.clear_highlight()
                if hasattr(self.search_ctrl, 'results') and self.search_ctrl.results:
                    self.search_counter.config(text="0 / 0")

    def _on_search_key(self, event):
        if self.live_search_var.get():
            self._perform_search()

    def _perform_search(self):
        query = self.search_var.get().strip()
        field = self.search_field_var.get()
        selected_chats = self.chat_panel.get_selected_chats()
        results = self.search_ctrl.search(query, field, selected_chats)
        if results:
            self.tree_panel.display_search_results(results)
        else:
            self.tree_panel.display_chats(selected_chats)
            self.search_counter.config(text="0 / 0")

    def _reset_search(self):
        self.search_var.set("")
        self._perform_search()

    def _prev_search_result(self):
        self.search_ctrl.prev()

    def _next_search_result(self):
        self.search_ctrl.next()

    def _on_search_result_change(self, result, index, total, move_focus=True):
        chat, pair, field, start, end = result
        iid = f"{chat.id}_{pair.index}_{start}_{end}"
        if iid in self.tree_panel.tree_item_map:
            self.tree_panel.tree.selection_set(iid)
            self.tree_panel.tree.see(iid)
            self.controller.select_pair(chat, pair)
            self.detail_panel.display_pair(pair)
            self._update_position_label()
            self._update_nav_buttons()
            self.detail_panel.highlight_search_match(field, start, end, move_focus=move_focus)
        else:
            self.controller.select_pair(chat, pair)
            self.detail_panel.display_pair(pair)
            self._update_position_label()
            self._update_nav_buttons()
            self.detail_panel.highlight_search_match(field, start, end, move_focus=move_focus)
        self.search_counter.config(text=f"{index + 1} / {total}")

    # ---------- Методы для работы с архивами и сессией ----------
    def add_archive(self):
        file_path = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")])
        if not file_path:
            return
        try:
            added, new_cnt, new_msg, upd_cnt, upd_msg = self.controller.add_source(file_path)
            if added:
                self._update_chat_list()
                parts = []
                if new_cnt:
                    parts.append(f"Добавлено чатов: {new_cnt} шт. ({new_msg} сообщ.)")
                if upd_cnt:
                    parts.append(f"Обновлено чатов: {upd_cnt} шт. ({upd_msg} сообщ.)")
                message = "\n".join(parts)
                messagebox.showinfo("Добавление архива", message)
                self.controller.save_session()
            else:
                messagebox.showinfo("Добавление архива",
                                    "Все чаты из этого архива уже загружены и не содержат новых сообщений.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить архив:\n{e}")

    def new_session(self):
        self.controller.clear_all_sources()
        self._update_chat_list()
        self.tree_panel.clear()
        self.detail_panel.clear()
        self.search_var.set("")
        self.search_ctrl.clear()
        self.search_counter.config(text="0 / 0")
        self._update_nav_buttons()
        self._update_position_label()

    def save_current_pair(self):
        current_pair = self.controller.get_current_pair()
        if current_pair is None:
            messagebox.showwarning("Предупреждение", "Нет выбранной пары для сохранения.")
            return

        new_request, new_response = self.detail_panel.get_current_texts()
        modified = False

        if new_request != current_pair.request_text:
            current_pair.request_text = new_request
            modified = True
        if new_response != current_pair.response_text:
            current_pair.response_text = new_response
            modified = True

        if modified:
            current_pair.modified = True
            self.tree_panel.update_pair_item(current_pair)
            messagebox.showinfo("Сохранение", "Изменения сохранены.")
            self.controller.save_session()
        else:
            messagebox.showinfo("Сохранение", "Нет изменений для сохранения.")

    def prev_pair(self):
        pair = self.controller.prev_pair()
        if pair:
            self.detail_panel.display_pair(pair)
            self._update_position_label()
            self._update_nav_buttons()

    def next_pair(self):
        pair = self.controller.next_pair()
        if pair:
            self.detail_panel.display_pair(pair)
            self._update_position_label()
            self._update_nav_buttons()

    def update_nav_buttons(self):
        self._update_nav_buttons()

    # ---------- Группировка ----------
    def _change_grouping_mode(self):
        mode = self.grouping_var.get()
        self.controller.set_grouping_mode(mode)
        self.state_manager.save()
        self._update_chat_list()

    # ---------- Внутренние вспомогательные методы ----------
    def _update_nav_buttons(self):
        can_prev, can_next = self.controller.get_nav_state()
        self.prev_button.config(state=tk.NORMAL if can_prev else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if can_next else tk.DISABLED)

    def _update_position_label(self):
        title, index, total = self.controller.get_position_info()
        if title is None:
            self.detail_panel.set_position_label("")
        else:
            self.detail_panel.set_position_label(f"Чат: {title} | Сообщение {index} из {total}")

    def _on_closing(self):
        self.controller.save_session()
        self.state_manager.save()
        self.destroy()
        
    def _open_code_structure(self):
        pair = self.controller.get_current_pair()
        if pair is None:
            messagebox.showwarning("Структура кода", "Сначала выберите сообщение.")
            return
        CodeStructureController(self, pair)  # передаём только pair