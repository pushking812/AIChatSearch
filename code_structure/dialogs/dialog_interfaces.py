# code_structure/dialogs/dialog_interfaces.py

"""
Интерфейсы для представлений (View) в архитектуре MVP.

Каждый диалог и главное окно реализуют свой интерфейс, описывающий методы,
которые презентер может вызывать для обновления UI. Это позволяет тестировать
презентеры без реального GUI (с использованием моков).
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .dto import (
    UnknownBlockInfo, KnownModuleInfo, TreeDisplayNode,
    FlatListItem
)

# ----------------------------------------------------------------------
# Интерфейс для ErrorBlockDialog
# ----------------------------------------------------------------------
class ErrorBlockView(ABC):
    """Интерфейс диалога исправления синтаксической ошибки."""

    @abstractmethod
    def show_code(self, code: str):
        """Отображает код для редактирования."""
        pass

    @abstractmethod
    def get_modified_code(self) -> str:
        """Возвращает изменённый пользователем код."""
        pass

    @abstractmethod
    def enable_apply_button(self, enabled: bool):
        """Включает/отключает кнопку «Применить» в зависимости от наличия изменений."""
        pass

    @abstractmethod
    def close(self):
        """Закрывает диалог."""
        pass

# ----------------------------------------------------------------------
# Интерфейс для ModuleAssignmentDialog
# ----------------------------------------------------------------------
class ModuleAssignmentView(ABC):
    """Интерфейс диалога назначения модулей."""

    @abstractmethod
    def set_blocks(self, blocks: List[UnknownBlockInfo]):
        """Устанавливает список неопределённых блоков в комбобокс."""
        pass

    @abstractmethod
    def set_modules(self, modules: List[KnownModuleInfo]):
        """Устанавливает список известных модулей в комбобокс."""
        pass

    @abstractmethod
    def set_tree_data(self, tree_data: TreeDisplayNode):
        """Отображает дерево модулей."""
        pass

    @abstractmethod
    def show_block_code(self, code: str):
        """Показывает код выбранного блока."""
        pass

    @abstractmethod
    def show_module_code(self, code: str):
        """Показывает пример кода выбранного модуля."""
        pass

    @abstractmethod
    def update_assignment_label(self, module_name: str):
        """Обновляет метку с назначенным модулем."""
        pass

    @abstractmethod
    def enable_apply_button(self, enabled: bool):
        """Включает/отключает кнопку «Применить»."""
        pass

    @abstractmethod
    def enable_ok_button(self, enabled: bool):
        """Включает/отключает кнопку «OK»."""
        pass

    @abstractmethod
    def set_action_mode(self, mode: str):
        """Устанавливает режим действия ('create_new' или 'assign_existing')."""
        pass

    @abstractmethod
    def get_selected_block_id(self) -> Optional[str]:
        """Возвращает ID выбранного блока."""
        pass

    @abstractmethod
    def get_selected_module(self) -> str:
        """Возвращает имя выбранного модуля."""
        pass

    @abstractmethod
    def get_new_module_name(self) -> str:
        """Возвращает имя нового модуля, введённое пользователем."""
        pass

    @abstractmethod
    def get_action_mode(self) -> str:
        """Возвращает текущий режим действия."""
        pass

    @abstractmethod
    def close(self):
        """Закрывает диалог."""
        pass

    @abstractmethod
    def show_error(self, message: str):
        """Показывает сообщение об ошибке."""
        pass

# ----------------------------------------------------------------------
# Интерфейс для главного окна
# ----------------------------------------------------------------------
class CodeStructureView(ABC):
    """Интерфейс главного окна структуры кода."""

    @abstractmethod
    def display_merged_tree(self, root_node: TreeDisplayNode):
        """Отображает дерево модулей."""
        pass

    @abstractmethod
    def set_flat_list(self, items: List[FlatListItem]):
        """Устанавливает плоский список элементов."""
        pass

    @abstractmethod
    def display_merged_code(self, code: str, language: str = "python"):
        """Отображает код в правой панели (дерево)."""
        pass

    @abstractmethod
    def set_module_button_state(self, enabled: bool):
        """Включает/отключает кнопку «Назначить модули»."""
        pass

    @abstractmethod
    def set_type_combo_values(self, values: List[str]):
        """Устанавливает значения в комбобокс выбора языка."""
        pass

    @abstractmethod
    def set_type_combo_state(self, enabled: bool):
        """Включает/отключает комбобокс выбора языка."""
        pass

    @abstractmethod
    def show_error(self, message: str):
        """Показывает сообщение об ошибке."""
        pass

    @abstractmethod
    def display_code(self, code: str, language: str = "python"):
        """Отображает код в левой панели (плоский список)."""
        pass

    @abstractmethod
    def get_local_only(self) -> bool:
        """Возвращает текущее состояние чекбокса «Только локальные импорты»."""
        pass

    @abstractmethod
    def set_presenter(self, presenter):
        """Устанавливает презентер для обработки событий."""
        pass

    @abstractmethod
    def wait_window(self, window):
        """Ожидает закрытия переданного дочернего окна (для диалогов)."""
        pass

    @abstractmethod
    def destroy(self):
        """Закрывает главное окно."""
        pass

    # ---------- Дополнительные методы для фильтрации плоского списка ----------
    @abstractmethod
    def set_flat_filter(self, column: str, value: str):
        """
        Устанавливает фильтр для плоского списка.
        column: название колонки ("Узел", "Модуль", "Класс", "Стратегия")
        value: значение для фильтрации (подстрока)
        """
        pass

    @abstractmethod
    def clear_flat_filter(self):
        """Сбрасывает фильтр плоского списка."""
        pass