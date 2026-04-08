# code_structure/dialogs/dialog_factory.py

from abc import ABC, abstractmethod
from typing import Any, List
from code_structure.dialogs.dto import ErrorBlockInput, ModuleAssignmentInput, AmbiguityInfo

class DialogFactory(ABC):
    @abstractmethod
    def create_error_block_dialog(self, parent, input_data: ErrorBlockInput) -> Any:
        pass

    @abstractmethod
    def create_module_assignment_dialog(self, parent, input_data: ModuleAssignmentInput) -> Any:
        pass

    @abstractmethod
    def create_ambiguity_dialog(self, parent, ambiguities: List[AmbiguityInfo]) -> Any:
        pass