def add_archive(self):
    """Загружает новый ZIP-архив и добавляет его чаты к существующим."""
    file_path = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")])
    if not file_path:
        return
    try:
        added = self.controller.add_source(file_path)
        if added:
            self._update_chat_list()
            # Можно показать сообщение о количестве добавленных чатов
            messagebox.showinfo("Добавление архива", f"Добавлено {len(added)} новых чатов.")
        else:
            messagebox.showinfo("Добавление архива", "Все чаты из этого архива уже загружены.")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось загрузить архив:\n{e}")