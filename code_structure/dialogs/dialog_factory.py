# code_structure/dialogs/dialog_factory.py

from abc import ABC, abstractmethod
from typing import Any, List
from code_structure.dialogs.dto import ErrorBlocksInput, ModuleAssignmentInput, AmbiguityInfo


class DialogFactory(ABC):
    @abstractmethod
    def create_error_blocks_dialog(self, parent, input_data: ErrorBlocksInput) -> Any:
        pass

    @abstractmethod
    def create_module_assignment_dialog(self, parent, input_data: ModuleAssignmentInput) -> Any:
        pass

    @abstractmethod
    def create_ambiguity_dialog(self, parent, ambiguities: List[AmbiguityInfo]) -> Any:
        pass