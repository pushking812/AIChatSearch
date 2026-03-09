# aichat_search/tools/code_structure/controller.py

from .view import CodeStructureWindow

class CodeStructureController:
    def __init__(self, parent, main_controller, current_pair):
        self.parent = parent
        self.main_controller = main_controller
        self.current_pair = current_pair

        # Создаем окно
        self.view = CodeStructureWindow(parent)
        # Пока никаких данных