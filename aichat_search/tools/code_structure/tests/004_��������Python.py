def update_list(self, items):
    """
    Обновляет отображение списка чатов.
    items: список кортежей (chat, source_name)
    """
    self.listbox.delete(0, tk.END)
    for chat, source_name in items:
        display_text = f"[{source_name}] {chat.title}"
        self.listbox.insert(tk.END, display_text)

def _on_filter_changed(self, event=None):
    """Обработка изменения фильтра."""
    self.controller.filter_chats(self.filter_var.get())
    # Получаем отфильтрованные чаты и формируем кортежи с именами источников
    filtered = self.controller.get_filtered_chats()
    items = [(chat, self.controller.get_source_name(chat)) for chat in filtered]
    self.update_list(items)
    self.clear_selection()