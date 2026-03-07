# aichat_search/gui_components/search_controller.py

"""Контроллер управления поиском и навигацией по результатам."""

class SearchController:
    def __init__(self, controller, on_result_change_callback):
        self.controller = controller
        self.on_result_change = on_result_change_callback
        self.results = []
        self.current_index = -1

    def search(self, query, field, chats):
        self.results = []
        self.current_index = -1
        if not query or not chats:
            return self.results
        for chat in chats:
            results = self.controller.search_with_positions(chat, query, field)
            self.results.extend(results)
        if self.results:
            self.go_to(0, move_focus=False)   # <-- добавляем move_focus=False
        return self.results

    def go_to(self, index, move_focus=True):
        if not self.results:
            return None
        self.current_index = index % len(self.results)
        result = self.results[self.current_index]
        self.on_result_change(result, self.current_index, len(self.results), move_focus)
        return result

    def next(self, move_focus=True):
        if self.results:
            self.go_to(self.current_index + 1, move_focus)

    def prev(self, move_focus=True):
        if self.results:
            self.go_to(self.current_index - 1, move_focus)

    def get_current(self):
        if 0 <= self.current_index < len(self.results):
            return self.results[self.current_index]
        return None

    def clear(self):
        self.results = []
        self.current_index = -1
        
###        
        
    def has_results(self) -> bool:
        """Возвращает True, если есть результаты поиска."""
        return bool(self.results)

    def get_total(self) -> int:
        """Возвращает общее количество результатов."""
        return len(self.results)

    def get_current_index(self) -> int:
        """Возвращает текущий индекс."""
        return self.current_index

    def set_current_index(self, idx: int, move_focus: bool = False):
        """
        Устанавливает текущий результат по индексу и вызывает колбэк.
        Если индекс выходит за пределы, ничего не делает.
        """
        if 0 <= idx < len(self.results):
            self.current_index = idx
            self._callback(self.results[idx], idx, len(self.results), move_focus)

    def find_first_index_for_pair(self, chat, pair) -> int:
        """
        Возвращает индекс первого результата, принадлежащего указанной паре (чат, сообщение).
        Если не найдено, возвращает -1.
        """
        for i, (c, p, field, start, end) in enumerate(self.results):
            if c is chat and p is pair:
                return i
        return -1
