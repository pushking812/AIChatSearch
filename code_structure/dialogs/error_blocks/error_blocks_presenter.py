# code_structure/dialogs/error_blocks/error_blocks_presenter.py

import logging
from typing import List, Optional, Tuple, Dict

from code_structure.dialogs.dialog_interfaces import ErrorBlocksView
from code_structure.dialogs.dto import ErrorBlockInfo, ErrorBlocksInput, ErrorBlocksOutput
from code_structure.parsing.core.parser import PythonParser
from code_structure.models.block import Block

logger = logging.getLogger(__name__)


class ErrorBlocksPresenter:
    def __init__(self, view: ErrorBlocksView):
        self.view = view
        self.blocks: List[ErrorBlockInfo] = []
        self.fixed: Dict[str, str] = {}      # block_id -> new_code
        self.deleted: List[str] = []
        self.current_block_id: Optional[str] = None
        self.parser = PythonParser()

    def initialize(self, input_data: ErrorBlocksInput):
        self.blocks = input_data.blocks
        self.view.set_blocks(self.blocks)
        if self.blocks:
            self._select_block(self.blocks[0].block_id)

    def _select_block(self, block_id: str):
        self.current_block_id = block_id
        for b in self.blocks:
            if b.block_id == block_id:
                self.view.show_block_code(b.original_code)
                self.view.enable_apply_button(False)
                break

    def on_block_selected(self, block_id: str):
        self._select_block(block_id)

    def on_text_changed(self, new_code: str):
        if not self.current_block_id:
            return
        # Найти оригинальный код
        original = ""
        for b in self.blocks:
            if b.block_id == self.current_block_id:
                original = b.original_code
                break
        modified = (new_code.strip() != original.strip())
        self.view.enable_apply_button(modified)

    def _validate_code(self, code: str, block: ErrorBlockInfo) -> Tuple[bool, str]:
        if not code.strip():
            return False, "Код не может быть пустым"
        try:
            dummy_block = Block(
                chat=block.chat,
                message_pair=block.message_pair,
                language=block.language,
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
        if not self.current_block_id:
            return
        new_code = self.view.get_modified_code()
        # Найти блок
        block = None
        for b in self.blocks:
            if b.block_id == self.current_block_id:
                block = b
                break
        if not block:
            return
        is_valid, error_msg = self._validate_code(new_code, block)
        if not is_valid:
            self.view.show_error(error_msg)
            return
        self.fixed[self.current_block_id] = new_code
        self.view.enable_apply_button(False)
        # Обновить оригинальный код в списке для дальнейших сравнений
        block.original_code = new_code

    def on_delete(self):
        if not self.current_block_id:
            return
        self.deleted.append(self.current_block_id)
        # Удалить из списка
        self.blocks = [b for b in self.blocks if b.block_id != self.current_block_id]
        self.view.set_blocks(self.blocks)
        if self.blocks:
            self._select_block(self.blocks[0].block_id)
        else:
            self.current_block_id = None
            self.view.show_block_code("")
            self.view.enable_apply_button(False)

    def on_ok(self):
        output = ErrorBlocksOutput(
            fixed_blocks=[(bid, code) for bid, code in self.fixed.items()],
            deleted_block_ids=self.deleted
        )
        self.view.close(output)

    def on_cancel(self):
        self.view.close(None)