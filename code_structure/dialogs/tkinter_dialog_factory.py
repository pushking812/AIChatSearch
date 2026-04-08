# code_structure/dialogs/tkinter_dialog_factory.py

from code_structure.dialogs.error_blocks.error_blocks_dialog import ErrorBlocksDialog
from code_structure.dialogs.module_assignment.module_assignment_dialog import ModuleAssignmentDialog
from code_structure.dialogs.ambiguity.ambiguity_dialog import AmbiguityDialog
from code_structure.dialogs.dialog_factory import DialogFactory

class TkinterDialogFactory(DialogFactory):
    def create_error_blocks_dialog(self, parent, input_data):
        return ErrorBlocksDialog(parent, input_data)

    def create_module_assignment_dialog(self, parent, input_data):
        return ModuleAssignmentDialog(parent, input_data)

    def create_ambiguity_dialog(self, parent, ambiguities):
        return AmbiguityDialog(parent, ambiguities)