def clear_all_sources(self):
    """Полностью очищает все источники и сбрасывает состояние."""
    self.sources.clear()
    self.known_chat_ids.clear()
    self._chat_to_source.clear()
    self._current_filter_query = ""
    self._rebuild_filtered_chats()   # перестроит пустые списки и сбросит навигацию