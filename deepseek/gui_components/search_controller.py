"""Контроллер управления поиском и навигацией по результатам."""

class SearchController:
    """Обрабатывает поиск, хранение результатов и перемещение по ним."""

    def __init__(self, controller, on_result_change_callback):
        """
        :param controller: ChatController
        :param on_result_change_callback: вызывается при смене текущего результата
        """
        self.controller = controller
        self.on_result_change = on_result_change_callback
        self.results = []          # список (chat, pair, field, start, end)
        self.current_index = -1

    def search(self, query, field, chats):
        """Выполнить поиск по заданным чатам и полю."""
        self.results = []
        self.current_index = -1
        if not query or not chats:
            return self.results

        for chat in chats:
            results = self.controller.search_with_positions(chat, query, field)
            self.results.extend(results)

        if self.results:
            self.go_to(0)
        return self.results

    def next(self):
        """Перейти к следующему результату."""
        if self.results:
            self.go_to(self.current_index + 1)

    def prev(self):
        """Перейти к предыдущему результату."""
        if self.results:
            self.go_to(self.current_index - 1)

    def go_to(self, index):
        """Перейти к результату с указанным индексом (с зацикливанием)."""
        if not self.results:
            return None
        self.current_index = index % len(self.results)
        result = self.results[self.current_index]
        self.on_result_change(result, self.current_index, len(self.results))
        return result

    def get_current(self):
        """Вернуть текущий результат или None."""
        if 0 <= self.current_index < len(self.results):
            return self.results[self.current_index]
        return None

    def clear(self):
        """Очистить результаты поиска."""
        self.results = []
        self.current_index = -1
