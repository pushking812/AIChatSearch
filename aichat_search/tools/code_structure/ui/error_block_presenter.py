# aichat_search/tools/code_structure/ui/error_block_presenter.py

import logging
from typing import Optional

from aichat_search.tools.code_structure.ui.dialog_interfaces import ErrorBlockView
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo

logger = logging.getLogger(__name__)


class ErrorBlockPresenter:
    """Презентер для диалога исправления ошибок."""
    
    def __init__(self, view: ErrorBlockView):
        self.view = view
        self.block_info: Optional[MessageBlockInfo] = None
        self.modified = False
        self.result: Optional[str] = None
    
    def initialize(self, block_info: MessageBlockInfo):
        """Инициализация с блоком, содержащим ошибку."""
        self.block_info = block_info
        self.view.show_code(block_info.content)
        self.view.enable_apply_button(False)
    
    def on_text_changed(self, new_text: str):
        """Обработчик изменения текста."""
        original = self.block_info.content.strip() if self.block_info else ""
        self.modified = (new_text.strip() != original)
        self.view.enable_apply_button(self.modified)
    
    def on_apply(self):
        """Обработчик нажатия кнопки Apply."""
        self.result = self.view.get_modified_code()
        self.view.close()
    
    def on_skip(self):
        """Обработчик пропуска (отмена)."""
        self.result = None
        self.view.close()