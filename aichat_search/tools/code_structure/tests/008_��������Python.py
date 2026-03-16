def _update_chat_list(self):
    """Обновляет список чатов в панели, формируя кортежи (chat, source_name)."""
    filtered = self.controller.get_filtered_chats()
    items = [(chat, self.controller.get_source_name(chat)) for chat in filtered]
    self.chat_panel.update_list(items)