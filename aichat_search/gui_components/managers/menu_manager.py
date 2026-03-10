# aichat_search/gui_components/managers/menu_manager.py

import tkinter as tk

class MenuManager:
    def __init__(self, archive_manager, group_handler, export_manager,
                 grouping_var, on_grouping_change, open_code_structure):
        """
        archive_manager: экземпляр ArchiveSessionManager
        group_handler: экземпляр GroupHandler
        export_manager: экземпляр ExportManager
        grouping_var: tk.StringVar для режима группировки
        on_grouping_change: колбэк при изменении группировки
        open_code_structure: колбэк для открытия окна структуры кода
        """
        self.archive_manager = archive_manager
        self.group_handler = group_handler
        self.export_manager = export_manager
        self.grouping_var = grouping_var
        self.on_grouping_change = on_grouping_change
        self.open_code_structure = open_code_structure

    def build_menu(self, menubar):
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
            command=self.on_grouping_change
        )
        grouping_submenu.add_radiobutton(
            label="По группе",
            variable=self.grouping_var,
            value="group",
            command=self.on_grouping_change
        )
        grouping_submenu.add_radiobutton(
            label="По префиксу",
            variable=self.grouping_var,
            value="prefix",
            command=self.on_grouping_change
        )
        chat_menu.add_cascade(label="Группировать", menu=grouping_submenu)
        chat_menu.add_separator()
        chat_menu.add_command(
            label="Создать/переименовать группу",
            command=lambda: self.group_handler.open_group_dialog(self.on_grouping_change)
        )
        chat_menu.add_command(
            label="Добавить чат в группу",
            command=lambda: self.group_handler.assign_group_to_selected(
                # Здесь нужно будет передать выбранные чаты, но это будет сделано через app
                # В текущей реализации group_handler сам обращается к app.chat_panel
                # Поэтому оставляем как есть
            )
        )
        menubar.add_cascade(label="Чат", menu=chat_menu)

        # Меню Сообщение
        message_menu = tk.Menu(menubar, tearoff=0)
        export_menu = tk.Menu(message_menu, tearoff=0)
        export_menu.add_command(
            label="В простой текст",
            command=lambda: self.export_manager.export_messages(
                # аналогично, export_manager использует app.tree_panel
            )
        )
        export_menu.add_command(
            label="По блокам",
            command=lambda: self.export_manager.export_messages(
                # аналогично
            )
        )
        message_menu.add_cascade(label="Экспорт", menu=export_menu)
        menubar.add_cascade(label="Сообщение", menu=message_menu)

        # Меню Инструменты
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Структура кода", command=self.open_code_structure)
        menubar.add_cascade(label="Инструменты", menu=tools_menu)

        return menubar