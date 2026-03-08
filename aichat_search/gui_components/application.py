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
from ..controller import ChatController
from ..services.exporter_factory import ExporterFactory
from ..services.exporters.base import Exporter
from ..services.exporters.block_exporter import BlockExporter   # для экспорта по блокам


class Application(tk.Tk):
    """Основное окно приложения."""

    def __init__(self):
        super().__init__()

        self.controller = ChatController()
        self.title("DeepSeek Chat Archive Navigator")
        self.geometry(f"{constants.DEFAULT_WIDTH}x{constants.DEFAULT_HEIGHT}")
        self.minsize(constants.MIN_LEFT_WIDTH + constants.MIN_RIGHT_WIDTH,
                     constants.MIN_TOP_HEIGHT + constants.MIN_BOTTOM_HEIGHT)

        # Инициализация компонентов
        self._create_menu()
        self._create_layout()
        self._init_controllers()

        self.controller.load_session()
        self._update_chat_list()

        self.state_manager = WindowStateManager(self)
        self.after_idle(self.state_manager.load_and_apply)

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    # ---------- Инициализация ----------
    def _create_menu(self):
        menubar = tk.Menu(self)

        # Меню Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Загрузить архив...", command=self.add_archive)
        file_menu.add_command(label="Новая сессия", command=self.new_session)
        menubar.add_cascade(label="Файл", menu=file_menu)

        # Меню Сообщение
        self._create_message_menu(menubar)

        self.config(menu=menubar)

    def _create_message_menu(self, menubar):
        message_menu = tk.Menu(menubar, tearoff=0)
        export_menu = tk.Menu(message_menu, tearoff=0)
        export_menu.add_command(label="В простой текст", command=self._export_selected_messages)
        export_menu.add_command(label="По блокам", command=self._export_selected_blocks)
        message_menu.add_cascade(label="Экспорт", menu=export_menu)
        menubar.add_cascade(label="Сообщение", menu=message_menu)

    def _create_layout(self):
        # Основная горизонтальная панель
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

        # Левая панель (чаты)
        left_frame = tk.Frame(self.main_paned)
        self.main_paned.add(left_frame, width=300, minsize=constants.MIN_LEFT_WIDTH)
        self.chat_panel = ChatListPanel(left_frame, self.controller, self._on_chats_selected)

        # Правая вертикальная панель
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

        # Верхняя часть (дерево сообщений)
        top_frame = tk.Frame(self.right_paned)
        self.right_paned.add(top_frame, height=300, minsize=constants.MIN_TOP_HEIGHT)
        self._create_search_bar(top_frame)
        self.tree_panel = MessageTreePanel(top_frame, self.controller, self._on_tree_selected)

        # Нижняя часть (детали сообщения)
        bottom_frame = tk.Frame(self.right_paned)
        self.right_paned.add(bottom_frame, minsize=constants.MIN_BOTTOM_HEIGHT)
        self.detail_panel = MessageDetailPanel(bottom_frame)
        self.text_paned = self.detail_panel.text_paned

        # Кнопки навигации и сохранения (добавляем в нижнюю часть)
        nav_frame = tk.Frame(bottom_frame)
        nav_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.prev_button = tk.Button(nav_frame, text="← Предыдущая", command=self.prev_pair, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.next_button = tk.Button(nav_frame, text="Следующая →", command=self.next_pair, state=tk.DISABLED)
        self.next_button.pack(side=tk.LEFT, padx=5)

        self.save_button = tk.Button(nav_frame, text="Сохранить изменения", command=self.save_current_pair)
        self.save_button.pack(side=tk.LEFT, padx=5)

        # Сохраняем ссылки на панели для восстановления геометрии
        self.left_frame = left_frame
        self.top_frame = top_frame
        self.bottom_frame = bottom_frame
        self.request_container = self.detail_panel.request_text.master  # родительский Frame
        self.response_container = self.detail_panel.response_text.master

    def _create_search_bar(self, parent):
        """Создаёт строку поиска над деревом."""
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
            values=["Название чата", "Запрос", "Ответ"],
            state="readonly",
            width=18
        )
        self.search_combobox.pack(side=tk.LEFT, padx=(0, 5))

        tk.Button(search_frame, text="Найти", command=self._perform_search).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(search_frame, text="Сбросить", command=self._reset_search).pack(side=tk.LEFT)
        tk.Checkbutton(search_frame, text="Live", variable=self.live_search_var).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="<", width=2, command=self._prev_search_result).pack(side=tk.LEFT)
        tk.Button(search_frame, text=">", width=2, command=self._next_search_result).pack(side=tk.LEFT)
        self.search_counter = tk.Label(search_frame, text="0 / 0")
        self.search_counter.pack(side=tk.LEFT, padx=5)

    def _init_controllers(self):
        """Создание вспомогательных контроллеров."""
        self.search_ctrl = SearchController(self.controller, self._on_search_result_change)

    # ---------- Вспомогательные методы для обновления интерфейса ----------
    def _update_chat_list(self):
        """Обновляет список чатов в панели, формируя кортежи (chat, source_name, source_time)."""
        filtered = self.controller.get_filtered_chats()
        items = []
        for chat in filtered:
            source_name, source_time = self.controller.get_source_info(chat)
            items.append((chat, source_name, source_time))
        self.chat_panel.update_list(items)

    # ---------- Обработчики событий ----------
    def _on_chats_selected(self):
        """Вызывается при изменении выбора в списке чатов."""
        selected = self.chat_panel.get_selected_chats()
        self.tree_panel.display_chats(selected)
        self.detail_panel.clear()
        self.search_ctrl.clear()
        self.search_counter.config(text="0 / 0")
        self._update_nav_buttons()

    def _on_tree_selected(self):
        selected = self.tree_panel.get_selected_pair()
        if not selected:
            return
        chat, pair = selected
        pair = self.controller.select_pair(chat, pair)
        if pair:
            self.detail_panel.display_pair(pair)
            self._update_position_label()
            self._update_nav_buttons()

            if hasattr(self.search_ctrl, 'results') and self.search_ctrl.results:
                results = self.search_ctrl.results
                for idx, (s_chat, s_pair, field, start, end) in enumerate(results):
                    if s_chat is chat and s_pair is pair:
                        if hasattr(self.search_ctrl, 'current_index'):
                            self.search_ctrl.current_index = idx
                        self.search_counter.config(text=f"{idx + 1} / {len(results)}")
                        self.detail_panel.highlight_search_match(field, start, end, move_focus=False)
                        break
                else:
                    self.detail_panel.clear_highlight()

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
        if self.tree_panel.select_item_by_pair(chat, pair):
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

    # ---------- Экспорт в простой текст ----------
    def _export_selected_messages(self):
        """Экспортировать каждое выбранное сообщение в отдельный текстовый файл."""
        selected = self.tree_panel.get_selected_pairs()
        if not selected:
            messagebox.showwarning("Экспорт", "Нет выбранных сообщений для экспорта.")
            return

        exporter = ExporterFactory.get_exporter('txt')

        exported_count = 0
        for chat, pair in selected:
            try:
                message_index = chat.pairs.index(pair) + 1
            except ValueError:
                message_index = 0

            data = Exporter.prepare_data(
                chat_title=chat.title,
                chat_created_at=chat.created_at,
                pair=pair,
                message_index=message_index
            )

            source_name_full, _ = self.controller.get_source_info(chat)
            source_name_base = os.path.splitext(source_name_full)[0] if source_name_full != "Imported" else "Imported"

            safe_chat_title = "".join(c for c in chat.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = constants.EXPORT_FILENAME_TEMPLATE.format(
                source_name=source_name_base,
                chat_title=safe_chat_title,
                message_index=message_index
            )

            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=filename,
                title=f"Сохранить сообщение {message_index} из чата '{chat.title}'"
            )
            if not file_path:
                answer = messagebox.askyesno("Экспорт", "Продолжить экспорт остальных сообщений?")
                if not answer:
                    break
                continue

            try:
                exporter.export(data, file_path)
                exported_count += 1
            except Exception as e:
                messagebox.showerror("Ошибка экспорта", f"Не удалось сохранить файл:\n{e}")
                answer = messagebox.askyesno("Экспорт", "Продолжить экспорт остальных сообщений?")
                if not answer:
                    break

        if exported_count:
            messagebox.showinfo("Экспорт", f"Успешно экспортировано {exported_count} сообщений.")
        else:
            messagebox.showinfo("Экспорт", "Ни одно сообщение не было экспортировано.")

    # ---------- Экспорт по блокам ----------
    def _export_selected_blocks(self):
        """Экспортировать каждое выбранное сообщение в отдельную папку с блоками."""
        selected = self.tree_panel.get_selected_pairs()
        if not selected:
            messagebox.showwarning("Экспорт", "Нет выбранных сообщений для экспорта.")
            return

        root_dir = filedialog.askdirectory(title="Выберите корневую папку для сохранения блоков")
        if not root_dir:
            return

        exporter = ExporterFactory.get_exporter('blocks')
        exported_count = 0

        for chat, pair in selected:
            try:
                message_index = chat.pairs.index(pair) + 1
            except ValueError:
                message_index = 0

            data = BlockExporter.prepare_data(
                chat_title=chat.title,
                chat_created_at=chat.created_at,
                pair=pair,
                message_index=message_index
            )

            source_name_full, _ = self.controller.get_source_info(chat)
            source_name_base = os.path.splitext(source_name_full)[0] if source_name_full != "Imported" else "Imported"

            safe_chat_title = "".join(c for c in chat.title if c.isalnum() or c in (' ', '-', '_')).rstrip()

            folder_name = constants.EXPORT_FILENAME_TEMPLATE.format(
                source_name=source_name_base,
                chat_title=safe_chat_title,
                message_index=message_index
            ).replace('.txt', '')

            folder_path = os.path.join(root_dir, folder_name)

            try:
                exporter.export(data, folder_path)
                exported_count += 1
            except Exception as e:
                messagebox.showerror("Ошибка экспорта", f"Не удалось сохранить блоки для сообщения {message_index}:\n{e}")
                answer = messagebox.askyesno("Экспорт", "Продолжить экспорт остальных сообщений?")
                if not answer:
                    break

        if exported_count:
            messagebox.showinfo("Экспорт", f"Успешно экспортировано {exported_count} сообщений по блокам в папку:\n{root_dir}")
        else:
            messagebox.showinfo("Экспорт", "Ни одно сообщение не было экспортировано.")

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