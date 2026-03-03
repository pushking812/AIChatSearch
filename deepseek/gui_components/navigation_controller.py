# deepseek/gui_components/navigation_controller.py

"""Контроллер навигации по сообщениям в выбранных чатах."""

class NavigationController:
    """Управляет перемещением по парам внутри выбранных чатов."""

    def __init__(self, controller):
        """
        :param controller: ChatController (оригинальный)
        """
        self.controller = controller

    def set_chats(self, chats):
        """Установить список выбранных чатов (передаётся в ChatController)."""
        # ChatController уже содержит метод для установки текущих чатов?
        # В оригинале он хранит текущие чаты через set_chats при загрузке архива,
        # а выделенные чаты хранятся в current_selected_chats.
        # Мы будем использовать методы ChatController для навигации.
        # Возможно, стоит просто вызывать методы controller.prev_pair и т.д.
        pass

    def prev(self):
        """Перейти к предыдущему сообщению."""
        return self.controller.prev_pair()

    def next(self):
        """Перейти к следующему сообщению."""
        return self.controller.next_pair()

    def get_current(self):
        """Получить текущую пару (если есть)."""
        # В ChatController нет прямого метода, но можно использовать get_current_pair
        if hasattr(self.controller, 'get_current_pair'):
            return self.controller.get_current_pair()
        return getattr(self.controller, 'current_pair', None)

    def get_state(self):
        """Получить состояние кнопок (можно_prev, можно_next)."""
        return self.controller.get_nav_state()

    def get_position_info(self):
        """Получить информацию о позиции (заголовок чата, индекс, всего)."""
        return self.controller.get_position_info()
