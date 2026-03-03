import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import json
import os

from . import model
from .controller import ChatController


def run_gui():
    app = Application()
    app.mainloop()


class Application(tk.Tk):
    def __init__(self):
        super().__init__()

        self.controller = ChatController()

        self.title("DeepSeek Chat Archive Navigator")
        self.geometry("1200x800")

        # Set minimum window size based on panel minimums
        min_width = 150 + 400
        min_height = 150 + 250
        self.minsize(min_width, min_height)

        self.tree_item_map = {}
        self.current_selected_chats = []

        self.chat_filter_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.search_field_var = tk.StringVar(value="Запрос")
        self.search_results = []
        self.current_result_index = -1
        self.live_search_var = tk.BooleanVar(value=True)
        self._internal_tree_update = False

        # Path to configuration file
        self.config_dir = os.path.join(os.path.dirname(__file__), 'config')
        self.config_path = os.path.join(self.config_dir, 'config.json')

        self._create_menu()
        self._create_layout()

        # Restore window state after UI is fully created
        self.after_idle(self.load_window_state)
        # Handle window close event
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ---------------- MENU ----------------

    def _create_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Открыть архив...", command=self.open_archive)
        menubar.add_cascade(label="Файл", menu=file_menu)
        self.config(menu=menubar)

    # ---------------- LAYOUT ----------------

    def _create_layout(self):
        # Main horizontal paned window
        self.main_paned = tk.PanedWindow(
            self,
            orient=tk.HORIZONTAL,
            sashrelief=tk.RAISED,
            sashwidth=6,
            bd=1,
            relief=tk.SUNKEN,
            showhandle=True,
        )
        self.main_paned.pack(fill=tk.BOTH, expand=True)

        # Left frame (chat list)
        left_frame = tk.Frame(self.main_paned)
        self.main_paned.add(left_frame, width=300, minsize=150)

        tk.Label(left_frame, text="Чаты", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=5)

        self.chat_filter_entry = tk.Entry(left_frame, textvariable=self.chat_filter_var)
        self.chat_filter_entry.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.chat_filter_entry.bind("<KeyRelease>", self.filter_chats)

        list_container = tk.Frame(left_frame)
        list_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.chat_listbox = tk.Listbox(
            list_container,
            selectmode=tk.EXTENDED,
            exportselection=False
        )
        self.chat_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_container, command=self.chat_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_listbox.config(yscrollcommand=scrollbar.set)
        self.chat_listbox.bind("<ButtonRelease-1>", self.on_chat_select)
        self.chat_listbox.bind("<Shift-ButtonRelease-1>", self.on_chat_select)
        self.chat_listbox.bind("<Control-ButtonRelease-1>", self.on_chat_select)

        buttons_frame = tk.Frame(left_frame)
        buttons_frame.pack(pady=(0, 5))

        self.btn_select_all = tk.Button(
            buttons_frame,
            text="☑",
            width=3,
            height=1,
            command=self.select_all_chats
        )
        self.btn_select_all.pack(side=tk.LEFT, padx=2)

        self.btn_clear_selection = tk.Button(
            buttons_frame,
            text="[ ]",
            width=3,
            height=1,
            command=self.clear_chat_selection
        )
        self.btn_clear_selection.pack(side=tk.LEFT, padx=2)

        # Right vertical paned window
        self.right_paned = tk.PanedWindow(
            self.main_paned,
            orient=tk.VERTICAL,
            sashrelief=tk.RAISED,
            sashwidth=6,
            bd=1,
            relief=tk.SUNKEN,
            showhandle=True,
        )
        self.main_paned.add(self.right_paned, minsize=400)

        # Top frame (messages tree)
        top_frame = tk.Frame(self.right_paned)
        self.right_paned.add(top_frame, height=300, minsize=150)

        tk.Label(top_frame, text="Сообщения", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=5)

        search_frame = tk.Frame(top_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.bind('<KeyRelease>', lambda e: self.perform_search() if self.live_search_var.get() else None)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.search_combobox = ttk.Combobox(
            search_frame,
            textvariable=self.search_field_var,
            values=["Название чата", "Запрос", "Ответ"],
            state="readonly",
            width=18
        )
        self.search_combobox.pack(side=tk.LEFT, padx=(0, 5))

        tk.Button(search_frame, text="Найти", command=self.perform_search).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(search_frame, text="Сбросить", command=self.reset_search).pack(side=tk.LEFT)
        tk.Checkbutton(search_frame, text="Live", variable=self.live_search_var).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="<", width=2, command=self.prev_search_result).pack(side=tk.LEFT)
        tk.Button(search_frame, text=">", width=2, command=self.next_search_result).pack(side=tk.LEFT)
        self.search_counter = tk.Label(search_frame, text="0 / 0")
        self.search_counter.pack(side=tk.LEFT, padx=5)

        self.tree = ttk.Treeview(
            top_frame,
            columns=("idx", "request", "response"),
            show="tree headings",
        )
        self.tree.heading("idx", text="#")
        self.tree.heading("request", text="Запрос")
        self.tree.heading("response", text="Ответ")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)

        tree_scroll = tk.Scrollbar(top_frame, command=self.tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=tree_scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Bottom frame (message details)
        bottom_frame = tk.Frame(self.right_paned)
        self.right_paned.add(bottom_frame, minsize=250)

        self.position_label = tk.Label(bottom_frame, text="", font=("Arial", 10, "italic"))
        self.position_label.pack(anchor="w", padx=5, pady=(5, 0))

        # Vertical paned window inside bottom frame for request/response
        self.text_paned = tk.PanedWindow(
            bottom_frame,
            orient=tk.VERTICAL,
            sashrelief=tk.RAISED,
            sashwidth=6,
            bd=1,
            relief=tk.SUNKEN,
            showhandle=True,
        )
        self.text_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        request_container = tk.Frame(self.text_paned)
        tk.Label(request_container, text="Запрос", font=("Arial", 11, "bold")).pack(anchor="w", padx=5)
        self.request_text = tk.Text(request_container, height=10)
        self.request_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        response_container = tk.Frame(self.text_paned)
        tk.Label(response_container, text="Ответ", font=("Arial", 11, "bold")).pack(anchor="w", padx=5)
        self.response_text = tk.Text(response_container, height=10)
        self.response_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.text_paned.add(request_container, minsize=110)
        self.text_paned.add(response_container, minsize=130)

        self.request_text.tag_configure("search_match", background="yellow")
        self.response_text.tag_configure("search_match", background="yellow")

        nav_frame = tk.Frame(bottom_frame)
        nav_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.prev_button = tk.Button(nav_frame, text="← Предыдущая", command=self.prev_pair, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.next_button = tk.Button(nav_frame, text="Следующая →", command=self.next_pair, state=tk.DISABLED)
        self.next_button.pack(side=tk.LEFT, padx=5)

        # Save button
        self.save_button = tk.Button(bottom_frame, text="Сохранить изменения", command=self.save_current_pair)
        self.save_button.pack(pady=5)

        # Keep references for state saving/restoring
        self.left_frame = left_frame
        self.top_frame = top_frame
        self.bottom_frame = bottom_frame
        self.request_container = request_container
        self.response_container = response_container

    # ---------------- DATA ----------------

    def open_archive(self):
        file_path = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")])
        if not file_path:
            return

        try:
            chats = model.load_from_zip(file_path)
            self.controller.set_chats(chats)
            self._update_chat_list()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть архив:\n{e}")

    def _update_chat_list(self):
        self.chat_listbox.delete(0, tk.END)
        for chat in self.controller.get_filtered_chats():
            self.chat_listbox.insert(tk.END, chat.title)

    def filter_chats(self, event=None):
        self.controller.filter_chats(self.chat_filter_var.get())
        self._update_chat_list()

    # ---------------- TREE ----------------

    def on_chat_select(self, event=None):
        indices = self.chat_listbox.curselection()
    
        if not indices:
            return
    
        filtered = self.controller.get_filtered_chats()
    
        self.current_selected_chats = [
            filtered[i]
            for i in indices
            if i < len(filtered)
        ]
    
        for item in self.tree.get_children():
            self.tree.delete(item)
    
        self.tree_item_map = {}
    
        for chat in self.current_selected_chats:
            pairs = list(chat.get_pairs())
            if not pairs:
                continue
    
            parent_text = f"{chat.title} ({len(pairs)} msgs / 0 matches)"
            parent_id = self.tree.insert("", "end", text=parent_text)
    
            for pair in pairs:
                idx_display = str(pair.index) + ('*' if pair.modified else '')
                item_id = self.tree.insert(
                    parent_id,
                    "end",
                    values=(
                        idx_display,
                        pair.request_text[:30],
                        pair.response_text[:30],
                    ),
                )
                self.tree_item_map[item_id] = (chat, pair)
    
        self.position_label.config(text="")
        self.update_nav_buttons()

    def on_tree_select(self, event=None):
        if self._internal_tree_update:
            return

        selection = self.tree.selection()
        if not selection:
            return

        item_id = selection[0]
        chat_pair = self.tree_item_map.get(item_id)
        if not chat_pair:
            return

        chat, pair = chat_pair

        pair = self.controller.select_pair(chat, pair)
        if pair:
            self._display_pair(pair)
            self._update_position_label()
            self.update_nav_buttons()

        # If search is active, jump to first found occurrence of this message
        if self.search_results:
            for idx, (s_chat, s_pair, field, start_pos, end_pos) in enumerate(self.search_results):
                if s_chat == chat and s_pair == pair:
                    self.current_result_index = idx
                    self.search_counter.config(
                        text=f"{idx + 1} / {len(self.search_results)}"
                    )
                    self._apply_search_highlight(field, start_pos, end_pos, move_focus=False)
                    break

    def _display_pair(self, pair):
        self.request_text.delete("1.0", tk.END)
        self.response_text.delete("1.0", tk.END)
        self.request_text.insert(tk.END, pair.request_text)
        self.response_text.insert(tk.END, pair.response_text)

    def select_all_chats(self):
        self.chat_listbox.selection_set(0, tk.END)
        self.on_chat_select()

    def clear_chat_selection(self):
        self.chat_listbox.selection_clear(0, tk.END)
        self.current_selected_chats = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree_item_map = {}
        self.position_label.config(text="")
        self.update_nav_buttons()

    # ---------------- SEARCH ----------------
    def reset_search(self):
        self.search_var.set("")
        self.on_chat_select()

    def perform_search(self):
        self.search_results = []
        self.current_result_index = -1
        query = self.search_var.get().strip()

        if not self.current_selected_chats:
            self.search_counter.config(text="0 / 0")
            return

        query = self.search_var.get().strip()
        field = self.search_field_var.get()

        for chat in self.current_selected_chats:
            results = self.controller.search_with_positions(chat, query, field)
            self.search_results.extend(results)

        print('DEBUG search_results count:', len(self.search_results))
        # Rebuild TreeView with found pairs only
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree_item_map = {}

        unique_pairs = []

        for chat, pair, _, _, _ in self.search_results:
            if (chat, pair) not in unique_pairs:
                unique_pairs.append((chat, pair))

        grouped = {}
        for chat, pair, _, _, _ in self.search_results:
            if chat not in grouped:
                grouped[chat] = {'pairs': set(), 'matches': 0}
            grouped[chat]['pairs'].add(pair)
            grouped[chat]['matches'] += 1

        for chat, data in grouped.items():
            pairs = sorted(data['pairs'], key=lambda p: int(p.index))
            matches = data['matches']
            parent_text = f"{chat.title} ({len(pairs)} msgs / {matches} matches)"
            parent_id = self.tree.insert("", "end", text=parent_text)
            for pair in pairs:
                idx_display = str(pair.index) + ('*' if pair.modified else '')
                item_id = self.tree.insert(
                    parent_id,
                    "end",
                    values=(
                        idx_display,
                        pair.request_text[:30],
                        pair.response_text[:30],
                    ),
                )
                self.tree_item_map[item_id] = (chat, pair)
        if not self.search_results:
            self.search_counter.config(text="0 / 0")
            return

        self.go_to_search_result(0, move_focus=False)

    def go_to_search_result(self, index, move_focus=True):
        total = len(self.search_results)
        if total == 0:
            return

        self.current_result_index = index % total
        chat, pair, field, start, end = self.search_results[self.current_result_index]

        item_id = None
        for iid, value in self.tree_item_map.items():
            if value == (chat, pair):
                item_id = iid
                break

        if item_id:
            if item_id not in self.tree.selection():
                self._internal_tree_update = True
                self.tree.selection_set(item_id)
                self.tree.see(item_id)
                self._internal_tree_update = False
            else:
                # Message already selected – ensure text is displayed
                self._display_pair(pair)

        self.controller.select_pair(chat, pair)

        # Defer highlight until after Treeview selection event completes
        self.after_idle(
            lambda f=field, s=start, e=end, mf=move_focus: 
                self._apply_search_highlight(f, s, e, mf)
        )

        self.search_counter.config(
            text=f"{self.current_result_index + 1} / {total}"
        )

    def next_search_result(self):
        if self.search_results:
            self.go_to_search_result(self.current_result_index + 1, move_focus=True)

    def prev_search_result(self):
        if self.search_results:
            self.go_to_search_result(self.current_result_index - 1, move_focus=True)

    def _apply_search_highlight(self, field, start, end, move_focus):
        widget = self.request_text if field == "request" else self.response_text

        if move_focus:
            widget.focus_set()

        widget.tag_remove("search_match", "1.0", tk.END)
        widget.tag_add("search_match", f"1.0 + {start} chars", f"1.0 + {end} chars")
        widget.see(f"1.0 + {start} chars")

    # ---------------- NAVIGATION ----------------

    def prev_pair(self):
        pair = self.controller.prev_pair()
        if pair:
            self._display_pair(pair)
            self._update_position_label()
            self.update_nav_buttons()

    def next_pair(self):
        pair = self.controller.next_pair()
        if pair:
            self._display_pair(pair)
            self._update_position_label()
            self.update_nav_buttons()

    def update_nav_buttons(self):
        can_prev, can_next = self.controller.get_nav_state()
        self.prev_button.config(state=tk.NORMAL if can_prev else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if can_next else tk.DISABLED)

    def _update_position_label(self):
        title, index, total = self.controller.get_position_info()
        if title is None:
            self.position_label.config(text="")
        else:
            self.position_label.config(
                text=f"Чат: {title} | Сообщение {index} из {total}"
            )

    # ---------- СОХРАНЕНИЕ/ВОССТАНОВЛЕНИЕ С ПРОПОРЦИЯМИ ----------
    def save_window_state(self):
        """Сохраняет геометрию окна и пропорции разделителей в config.json."""
        os.makedirs(self.config_dir, exist_ok=True)

        win_width = self.winfo_width()
        win_height = self.winfo_height()

        # Вычисляем пропорции для каждой панели
        try:
            left_width = self.main_paned.sash_coord(0)[0]
            main_total = self.main_paned.winfo_width()
            main_sash = self.main_paned.cget('sashwidth')
            left_prop = left_width / (main_total - main_sash) if main_total > main_sash else 0.25
        except:
            left_prop = 0.25

        try:
            top_height = self.right_paned.sash_coord(0)[1]
            right_total = self.right_paned.winfo_height()
            right_sash = self.right_paned.cget('sashwidth')
            top_prop = top_height / (right_total - right_sash) if right_total > right_sash else 0.5
        except:
            top_prop = 0.5

        try:
            req_height = self.text_paned.sash_coord(0)[1]
            text_total = self.text_paned.winfo_height()
            text_sash = self.text_paned.cget('sashwidth')
            req_prop = req_height / (text_total - text_sash) if text_total > text_sash else 0.5
        except:
            req_prop = 0.5

        config = {
            "window_size": {"width": win_width, "height": win_height},
            "proportions": {
                "main_horizontal": left_prop,
                "right_vertical": top_prop,
                "text_vertical": req_prop
            }
        }

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"Сохранено: {config}")
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

    def load_window_state(self):
        """Восстанавливает геометрию окна и пропорции разделителей."""
        if not os.path.exists(self.config_path):
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"Загружено: {config}")
        except Exception as e:
            print(f"Ошибка загрузки: {e}")
            return

        # Восстанавливаем размер окна
        win_size = config.get("window_size", {})
        width = win_size.get("width", 1200)
        height = win_size.get("height", 800)
        self.geometry(f"{width}x{height}")

        self.update_idletasks()

        # Восстанавливаем пропорции
        props = config.get("proportions", {})
        if props:
            self.after(50, self._apply_proportions, props)

    def _apply_proportions(self, props):
        """Применяет сохранённые пропорции к панелям с учётом minsize."""
        # Главная горизонтальная панель
        left_prop = props.get("main_horizontal")
        if left_prop is not None:
            total_width = self.main_paned.winfo_width()
            sash_width = self.main_paned.cget('sashwidth')
            available = total_width - sash_width
            desired = int(left_prop * available)
            # Минимальные размеры (заданы при создании)
            left_minsize = 150
            right_minsize = 400
            if desired < left_minsize:
                desired = left_minsize
            if available - desired < right_minsize:
                desired = available - right_minsize
            if 0 < desired < total_width - sash_width:
                try:
                    self.main_paned.sash_place(0, desired, 0)
                except Exception as e:
                    print(f"Ошибка main_horizontal: {e}")

        # Вертикальная панель справа
        top_prop = props.get("right_vertical")
        if top_prop is not None:
            total_height = self.right_paned.winfo_height()
            sash_width = self.right_paned.cget('sashwidth')
            available = total_height - sash_width
            desired = int(top_prop * available)
            top_minsize = 150
            bottom_minsize = 250
            if desired < top_minsize:
                desired = top_minsize
            if available - desired < bottom_minsize:
                desired = available - bottom_minsize
            if 0 < desired < total_height - sash_width:
                try:
                    self.right_paned.sash_place(0, 0, desired)
                except Exception as e:
                    print(f"Ошибка right_vertical: {e}")

        # Текстовая панель
        req_prop = props.get("text_vertical")
        if req_prop is not None:
            total_height = self.text_paned.winfo_height()
            sash_width = self.text_paned.cget('sashwidth')
            available = total_height - sash_width
            desired = int(req_prop * available)
            req_minsize = 110
            resp_minsize = 130
            if desired < req_minsize:
                desired = req_minsize
            if available - desired < resp_minsize:
                desired = available - resp_minsize
            if 0 < desired < total_height - sash_width:
                try:
                    self.text_paned.sash_place(0, 0, desired)
                except Exception as e:
                    print(f"Ошибка text_vertical: {e}")

    def on_closing(self):
        """Обработчик закрытия окна: сохраняем состояние и завершаем работу."""
        self.save_window_state()
        self.destroy()

    # ---------- СОХРАНЕНИЕ ТЕКУЩЕЙ ПАРЫ ----------
    def save_current_pair(self):
        """Сохраняет изменения текущей пары сообщений."""
        # Получаем текущую пару из контроллера (предполагается наличие метода get_current_pair)
        current_pair = self.controller.get_current_pair() if hasattr(self.controller, 'get_current_pair') else None
        if current_pair is None:
            # Если метод отсутствует, пробуем получить через атрибут (на свой страх и риск)
            current_pair = getattr(self.controller, 'current_pair', None)
        if current_pair is None:
            messagebox.showwarning("Предупреждение", "Нет выбранной пары для сохранения.")
            return

        modified = False

        # Получаем текст из виджетов
        new_request = self.request_text.get("1.0", "end-1c")
        new_response = self.response_text.get("1.0", "end-1c")

        # Сравниваем и обновляем
        if new_request != current_pair.request_text:
            current_pair.request_text = new_request
            modified = True
        if new_response != current_pair.response_text:
            current_pair.response_text = new_response
            modified = True

        if modified:
            current_pair.modified = True
            # Обновляем отображение в дереве (добавляем * к номеру)
            self._update_tree_item_for_pair(current_pair)
            messagebox.showinfo("Сохранение", "Изменения сохранены.")
        else:
            messagebox.showinfo("Сохранение", "Нет изменений для сохранения.")

    # ---------- ВСПОМОГАТЕЛЬНЫЙ МЕТОД: Обновление строки дерева ----------
    def _update_tree_item_for_pair(self, target_pair):
        """Находит элемент дерева, соответствующий паре, и обновляет его отображение."""
        for item_id, (chat, pair) in self.tree_item_map.items():
            if pair is target_pair:
                # Формируем отображаемый номер со звёздочкой, если изменено
                idx_display = str(pair.index) + ('*' if pair.modified else '')
                # Обновляем значения в дереве
                self.tree.item(item_id, values=(
                    chat.title,
                    idx_display,
                    pair.request_text[:30],
                    pair.response_text[:30],
                ))
                break