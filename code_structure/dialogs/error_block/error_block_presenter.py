# code_structure/dialogs/error_block/error_block_presenter.py

import logging
import textwrap
from typing import Optional

from code_structure.dialogs.dialog_interfaces import ErrorBlockView
from code_structure.dialogs.dto import ErrorBlockInput
from code_structure.parsing.core.parser import PythonParser
from code_structure.models.block import Block

from code_structure.utils.logger import get_logger

logger = get_logger(__name__, level=logging.WARNING)


class ErrorBlockPresenter:
    def __init__(self, view: ErrorBlockView):
        self.view = view
        self.input_data: Optional[ErrorBlockInput] = None
        self.modified = False
        self.result: Optional[str] = None
        self.parser = PythonParser()

    def initialize(self, input_data: ErrorBlockInput):
        self.input_data = input_data
        self.view.show_code(input_data.original_code)
        self.view.enable_apply_button(False)

    def on_text_changed(self, new_text: str):
        original = self.input_data.original_code.strip() if self.input_data else ""
        self.modified = (new_text.strip() != original)
        self.view.enable_apply_button(self.modified)

    def _validate_code(self, code: str) -> tuple[bool, str]:
        """Проверяет синтаксис кода. Возвращает (успех, сообщение об ошибке)."""
        if not code.strip():
            return False, "Код не может быть пустым"
        try:
            dummy_block = Block(
                chat=self.input_data.chat,
                message_pair=self.input_data.message_pair,
                language=self.input_data.language,
                content=code,
                block_idx=0,
                global_index=0
            )
            self.parser.parse(dummy_block)
            return True, ""
        except SyntaxError as e:
            return False, f"Синтаксическая ошибка: {e}"
        except Exception as e:
            return False, f"Ошибка парсинга: {e}"

    def on_apply(self):
        if not self.input_data:
            return
        new_code = self.view.get_modified_code()
        is_valid, error_msg = self._validate_code(new_code)
        if is_valid:
            # Очищаем отступы перед сохранением
            self.result = new_code
            self.view.close()
        else:
            self.view.show_error(error_msg)
            # Не закрываем диалог, остаёмся в режиме редактирования

    def on_skip(self):
        self.result = None
        self.view.close()