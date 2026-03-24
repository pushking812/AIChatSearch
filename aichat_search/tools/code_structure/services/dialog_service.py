# aichat_search/tools/code_structure/services/dialog_service.py

from typing import List, Dict, Optional
import logging

from aichat_search.tools.code_structure.ui import ErrorBlockDialog, ModuleAssignmentDialog
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.models.containers import Container

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class DialogService:
    """Сервис для управления диалогами."""
    
    def __init__(self, parent):
        self.parent = parent
    
    def show_error_dialog(self, block: MessageBlockInfo, block_description: str) -> Optional[str]:
        """
        Показывает диалог исправления ошибки.
        Возвращает исправленный код или None.
        """
        dialog = ErrorBlockDialog(self.parent, block)
        self.parent.wait_window(dialog)
        return dialog.result
    
    def show_module_assignment_dialog(
        self,
        unknown_blocks: List[MessageBlockInfo],
        block_descriptions: Dict[str, str],
        known_modules: List[str],
        module_sources: Dict[str, Optional[str]],
        module_code_map: Dict[str, str],
        module_containers: Dict[str, Container]
    ) -> Optional[Dict[str, str]]:
        """
        Показывает диалог назначения модулей.
        Возвращает словарь {block_id: module_name} или None.
        """
        # Подготавливаем данные для диалога
        dialog_data = []
        for block in unknown_blocks:
            display_name = f"{block.block_id} – {block_descriptions.get(block.block_id, 'блок_кода')}"
            dialog_data.append({
                'id': block.block_id,
                'display_name': display_name,
                'content': block.content
            })
        
        module_info = []
        for module in sorted(known_modules):
            module_info.append({
                'name': module,
                'source': module_sources.get(module)
            })
        
        dialog = ModuleAssignmentDialog(
            self.parent,
            dialog_data,
            module_info,
            module_code_map,
            module_containers
        )
        
        self.parent.wait_window(dialog)
        return dialog.result