def _create_menu(self):
    menubar = tk.Menu(self)
    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(label="Загрузить архив...", command=self.add_archive)
    file_menu.add_command(label="Новая сессия", command=self.new_session)
    menubar.add_cascade(label="Файл", menu=file_menu)
    self.config(menu=menubar)