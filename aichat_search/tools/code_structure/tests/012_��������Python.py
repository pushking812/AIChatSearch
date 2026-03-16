def new_session(self):
    """Очищает все загруженные источники и сбрасывает интерфейс."""
    self.controller.clear_all_sources()
    self._update_chat_list()
    # Очищаем дерево сообщений и детали
    self.tree_panel.clear()
    self.detail_panel.clear()
    # Сбрасываем поиск
    self.search_var.set("")
    self.search_ctrl.clear()
    self.search_counter.config(text="0 / 0")
    # Обновляем навигацию
    self._update_nav_buttons()
    self._update_position_label()