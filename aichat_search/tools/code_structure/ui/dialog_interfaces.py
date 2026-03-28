# aichat_search/tools/code_structure/ui/dialog_interfaces.py

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from aichat_search.tools.code_structure.ui.dto import UnknownBlockInfo, KnownModuleInfo, TreeDisplayNode, ErrorBlockInput, FlatListItem


class ErrorBlockView(ABC):
    """Интерфейс для представления диалога исправления ошибок."""

    @abstractmethod
    def show_code(self, code: str):
        """Показывает код для редактирования."""
        pass

    @abstractmethod
    def get_modified_code(self) -> str:
        """Возвращает изменённый код."""
        pass

    @abstractmethod
    def enable_apply_button(self, enabled: bool):
        """Включает/отключает кнопку Apply."""
        pass

    @abstractmethod
    def close(self):
        """Закрывает диалог."""
        pass


class ModuleAssignmentView(ABC):
    """Интерфейс для представления диалога назначения модулей."""

    @abstractmethod
    def set_blocks(self, blocks: List[UnknownBlockInfo]):
        """Устанавливает список неопределённых блоков."""
        pass

    @abstractmethod
    def set_modules(self, modules: List[KnownModuleInfo]):
        """Устанавливает список известных модулей."""
        pass

    @abstractmethod
    def set_tree_data(self, tree_data: TreeDisplayNode):
        """Устанавливает данные для дерева модулей."""
        pass

    @abstractmethod
    def show_block_code(self, code: str):
        """Показывает код текущего блока."""
        pass

    @abstractmethod
    def show_module_code(self, code: str):
        """Показывает код выбранного модуля."""
        pass

    @abstractmethod
    def update_assignment_label(self, module_name: str):
        """Обновляет метку с назначенным модулем."""
        pass

    @abstractmethod
    def enable_apply_button(self, enabled: bool):
        """Включает/отключает кнопку Apply."""
        pass

    @abstractmethod
    def enable_ok_button(self, enabled: bool):
        """Включает/отключает кнопку OK."""
        pass

    @abstractmethod
    def set_action_mode(self, mode: str):
        """Устанавливает режим действия (create_new/assign_existing)."""
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
        """Возвращает имя нового модуля."""
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
        

class CodeStructureView(ABC):
    """Интерфейс для представления основного окна структуры кода."""

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
        """Отображает код в правом окне."""
        pass

    @abstractmethod
    def set_module_button_state(self, enabled: bool):
        """Включает/отключает кнопку 'Назначить модули'."""
        pass

    @abstractmethod
    def set_type_combo_values(self, values: List[str]):
        """Устанавливает значения в комбобокс языков."""
        pass

    @abstractmethod
    def set_type_combo_state(self, enabled: bool):
        """Включает/отключает комбобокс языков."""
        pass

    @abstractmethod
    def show_error(self, message: str):
        """Показывает сообщение об ошибке."""
        pass

    @abstractmethod
    def display_code(self, code: str, language: str = "python"):
        """Отображает код в левом окне."""
        pass

    @abstractmethod
    def get_local_only(self) -> bool:
        """Возвращает значение флага 'Только локальные импорты'."""
        pass

    @abstractmethod
    def set_presenter(self, presenter):
        """Устанавливает презентер."""
        pass

    @abstractmethod
    def wait_window(self, window):
        """Ожидает закрытия окна (для диалогов)."""
        pass

    @abstractmethod
    def destroy(self):
        """Закрывает окно."""
        pass