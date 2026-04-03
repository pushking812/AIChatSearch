# code_structure/dialogs/error_block/error_block_presenter.py

import logging
from typing import Optional

from code_structure.dialogs.dialog_interfaces import ErrorBlockView
from code_structure.dialogs.dto import ErrorBlockInput

from code_structure.utils.logger import get_logger

logger = get_logger(__name__, level = logging.WARNING)

class ErrorBlockPresenter:
    def __init__(self, view: ErrorBlockView):
        self.view = view
        self.input_data: Optional[ErrorBlockInput] = None
        self.modified = False
        self.result: Optional[str] = None

    def initialize(self, input_data: ErrorBlockInput):
        self.input_data = input_data
        self.view.show_code(input_data.original_code)
        self.view.enable_apply_button(False)

    def on_text_changed(self, new_text: str):
        original = self.input_data.original_code.strip() if self.input_data else ""
        self.modified = (new_text.strip() != original)
        self.view.enable_apply_button(self.modified)

    def on_apply(self):
        self.result = self.view.get_modified_code()
        self.view.close()

    def on_skip(self):
        self.result = None
        self.view.close()