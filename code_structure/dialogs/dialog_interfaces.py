# code_structure/dialogs/dialog_interfaces.py

"""
Интерфейсы для представлений (View) в архитектуре MVP.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict

from .dto import (
    UnknownBlockInfo, KnownModuleInfo, TreeDisplayNode,
    FlatListItem, AmbiguityInfo, ErrorBlockInfo, ErrorBlocksInput, ErrorBlocksOutput
)

# ----------------------------------------------------------------------
# Интерфейс для ModuleAssignmentDialog
# ----------------------------------------------------------------------
class ModuleAssignmentView(ABC):
    @abstractmethod
    def set_blocks(self, blocks: List[UnknownBlockInfo]):
        pass

    @abstractmethod
    def set_modules(self, modules: List[KnownModuleInfo]):
        pass

    @abstractmethod
    def set_tree_data(self, tree_data: TreeDisplayNode):
        pass

    @abstractmethod
    def show_block_code(self, code: str):
        pass

    @abstractmethod
    def show_module_code(self, code: str):
        pass

    @abstractmethod
    def update_assignment_label(self, module_name: str):
        pass

    @abstractmethod
    def enable_apply_button(self, enabled: bool):
        pass

    @abstractmethod
    def enable_ok_button(self, enabled: bool):
        pass

    @abstractmethod
    def set_action_mode(self, mode: str):
        pass

    @abstractmethod
    def get_selected_block_id(self) -> Optional[str]:
        pass

    @abstractmethod
    def get_selected_module(self) -> str:
        pass

    @abstractmethod
    def get_new_module_name(self) -> str:
        pass

    @abstractmethod
    def get_action_mode(self) -> str:
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def show_error(self, message: str):
        pass

# ----------------------------------------------------------------------
# Интерфейс для главного окна
# ----------------------------------------------------------------------
class CodeStructureView(ABC):
    @abstractmethod
    def display_merged_tree(self, root_node: TreeDisplayNode):
        pass

    @abstractmethod
    def set_flat_list(self, items: List[FlatListItem]):
        pass

    @abstractmethod
    def display_merged_code(self, code: str, language: str = "python"):
        pass

    @abstractmethod
    def set_module_button_state(self, enabled: bool):
        pass

    @abstractmethod
    def set_fix_errors_button_state(self, enabled: bool):
        pass

    @abstractmethod
    def set_type_combo_values(self, values: List[str]):
        pass

    @abstractmethod
    def set_type_combo_state(self, enabled: bool):
        pass

    @abstractmethod
    def show_error(self, message: str):
        pass

    @abstractmethod
    def display_code(self, code: str, language: str, start_line: Optional[int], end_line: Optional[int]):
        pass

    @abstractmethod
    def get_local_only(self) -> bool:
        pass

    @abstractmethod
    def set_presenter(self, presenter):
        pass

    @abstractmethod
    def wait_window(self, window):
        pass

    @abstractmethod
    def destroy(self):
        pass

    @abstractmethod
    def set_flat_filter(self, column: str, value: str):
        pass

    @abstractmethod
    def clear_flat_filter(self):
        pass

# ----------------------------------------------------------------------
# Интерфейс для диалога разрешения неоднозначностей
# ----------------------------------------------------------------------
class AmbiguityView(ABC):
    @abstractmethod
    def set_ambiguities(self, ambiguities: List[AmbiguityInfo]):
        pass

    @abstractmethod
    def get_selected_path(self, name: str) -> Optional[str]:
        pass

    @abstractmethod
    def close(self, result: Optional[Dict[str, str]]):
        pass

    @abstractmethod
    def show_error(self, message: str):
        pass

# ----------------------------------------------------------------------
# Интерфейс для единого диалога исправления ошибок
# ----------------------------------------------------------------------
class ErrorBlocksView(ABC):
    @abstractmethod
    def set_blocks(self, blocks: List[ErrorBlockInfo]):
        pass

    @abstractmethod
    def get_selected_block_id(self) -> Optional[str]:
        pass

    @abstractmethod
    def show_block_code(self, code: str):
        pass

    @abstractmethod
    def get_modified_code(self) -> str:
        pass

    @abstractmethod
    def enable_apply_button(self, enabled: bool):
        pass

    @abstractmethod
    def close(self, result: Optional[ErrorBlocksOutput]):
        pass

    @abstractmethod
    def show_error(self, message: str):
        pass