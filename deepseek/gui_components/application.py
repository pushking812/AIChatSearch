# deepseek/gui_components/application.py

"""Главный класс приложения, координирующий работу всех компонентов."""

from tkinter import ttk
import tkinter as tk
from tkinter import filedialog, messagebox
from . import constants
from .chat_list import ChatListPanel
from .message_tree import MessageTreePanel
from .message_detail import MessageDetailPanel
from .search_controller import SearchController
from .navigation_controller import NavigationController
from .window_state import WindowStateManager
from ..controller import ChatController
from .. import model

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

        # Восстановление состояния окна
        self.state_manager = WindowStateManager(self)
        self.after_idle(self.state_manager.load_and_apply)

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    # ---------- Инициализация ----------
    def _create_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Открыть архив...", command=self.open_archive)
        menubar.add_cascade(label="Файл", menu=file_menu)
        self.config(menu=menubar)

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
        self.nav_ctrl = NavigationController(self.controller)

    # ---------- Обработчики событий ----------
    def _on_chats_selected(self):
        """Вызывается при изменении выбора в списке чатов."""
        selected = self.chat_panel.get_selected_chats()
        # Обновляем дерево
        self.tree_panel.display_chats(selected)
        # Очищаем детали
        self.detail_panel.clear()
        # Сбрасываем поиск
        self.search_ctrl.clear()
        self.search_counter.config(text="0 / 0")
        # Обновляем навигацию
        self._update_nav_buttons()

    def _on_tree_selected(self):
        """Вызывается при выборе элемента в дереве."""
        selected = self.tree_panel.get_selected_pair()
        if not selected:
            return
        chat, pair = selected
        pair = self.controller.select_pair(chat, pair)
        if pair:
            self.detail_panel.display_pair(pair)
            self._update_position_label()
            self._update_nav_buttons()
            # Если есть активный поиск, подсветить результат
            current = self.search_ctrl.get_current()
            if current:
                s_chat, s_pair, field, start, end = current
                if s_chat == chat and s_pair == pair:
                    self.detail_panel.highlight_search_match(field, start, end, move_focus=False)

    def _on_search_key(self, event):
        """Обработка ввода в поле поиска при live-режиме."""
        if self.live_search_var.get():
            self._perform_search()

    def _perform_search(self):
        """Выполнить поиск."""
        query = self.search_var.get().strip()
        field = self.search_field_var.get()
        selected_chats = self.chat_panel.get_selected_chats()
        results = self.search_ctrl.search(query, field, selected_chats)
        if results:
            self.tree_panel.display_search_results(results)
        else:
            # Если результатов нет, показываем все сообщения выбранных чатов
            self.tree_panel.display_chats(selected_chats)
            self.search_counter.config(text="0 / 0")

    def _reset_search(self):
        """Сбросить поиск."""
        self.search_var.set("")
        self._perform_search()

    def _prev_search_result(self):
        """Предыдущий результат поиска."""
        self.search_ctrl.prev()

    def _next_search_result(self):
        """Следующий результат поиска."""
        self.search_ctrl.next()

    def _on_search_result_change(self, result, index, total):
        """Обработчик смены текущего результата поиска."""
        chat, pair, field, start, end = result
        # Выделяем пару в дереве
        if self.tree_panel.select_item_by_pair(chat, pair):
            # Обновляем детали (уже будет вызвано через _on_tree_selected, но для надёжности)
            self.controller.select_pair(chat, pair)
            self.detail_panel.display_pair(pair)
            self._update_position_label()
            self._update_nav_buttons()
            self.detail_panel.highlight_search_match(field, start, end, move_focus=True)
        self.search_counter.config(text=f"{index + 1} / {total}")

    # ---------- Публичные методы (для обратной совместимости) ----------
    def open_archive(self):
        """Открыть ZIP-архив с чатами."""
        file_path = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")])
        if not file_path:
            return
        try:
            chats = model.load_from_zip(file_path)
            self.controller.set_chats(chats)
            self.chat_panel.update_list()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть архив:\n{e}")

    def save_current_pair(self):
        """Сохранить изменения текущей пары."""
        current_pair = self.nav_ctrl.get_current()
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
        else:
            messagebox.showinfo("Сохранение", "Нет изменений для сохранения.")

    def prev_pair(self):
        """Перейти к предыдущей паре."""
        pair = self.nav_ctrl.prev()
        if pair:
            self.detail_panel.display_pair(pair)
            self._update_position_label()
            self._update_nav_buttons()

    def next_pair(self):
        """Перейти к следующей паре."""
        pair = self.nav_ctrl.next()
        if pair:
            self.detail_panel.display_pair(pair)
            self._update_position_label()
            self._update_nav_buttons()

    def update_nav_buttons(self):
        """Обновить состояние кнопок навигации (вызывается извне)."""
        self._update_nav_buttons()

    # ---------- Внутренние вспомогательные методы ----------
    def _update_nav_buttons(self):
        can_prev, can_next = self.nav_ctrl.get_state()
        self.prev_button.config(state=tk.NORMAL if can_prev else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if can_next else tk.DISABLED)

    def _update_position_label(self):
        title, index, total = self.nav_ctrl.get_position_info()
        if title is None:
            self.detail_panel.set_position_label("")
        else:
            self.detail_panel.set_position_label(f"Чат: {title} | Сообщение {index} из {total}")

    def _on_closing(self):
        """Обработчик закрытия окна."""
        self.state_manager.save()
        self.destroy()
