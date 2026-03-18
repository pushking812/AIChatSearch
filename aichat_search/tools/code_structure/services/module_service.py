# aichat_search/tools/code_structure/services/module_service.py

from typing import List, Dict, Optional, Tuple
import logging

from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.models.containers import Container
from aichat_search.tools.code_structure.core.module_orchestrator import ModuleOrchestrator
from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier

logger = logging.getLogger(__name__)


class ModuleService:
    """Сервис для работы с модулями и их структурой."""
    
    def __init__(self):
        self.orchestrator = ModuleOrchestrator()
        self.module_containers: Dict[str, Container] = {}
        self.unknown_blocks: List[MessageBlockInfo] = []
    
    @property
    def identifier(self) -> ModuleIdentifier:
        """Возвращает идентификатор модулей из оркестратора."""
        return self.orchestrator.module_identifier
    
    def process_blocks(self, blocks: List[MessageBlockInfo]) -> Tuple[Dict[str, Container], List[MessageBlockInfo]]:
        """
        Обрабатывает блоки, определяет модули и строит структуру.
        Возвращает (контейнеры модулей, неопределённые блоки).
        """
        containers, unknown = self.orchestrator.process_blocks(blocks)
        self.module_containers = containers
        self.unknown_blocks = unknown
        logger.info(f"Обработано блоков: {len(blocks)}, определено модулей: {len(containers)}")
        return containers, unknown
    
    def get_known_modules(self) -> List[str]:
        """Возвращает список известных модулей."""
        return sorted(self.identifier.get_known_modules())
    
    def get_module_source(self, module_name: str, blocks: List[MessageBlockInfo]) -> Optional[str]:
        """
        Возвращает описание источника для модуля (блок, из которого он получен).
        """
        for block in blocks:
            if block.module_hint == module_name and block.tree:
                return f"{block.block_id} – ..."  # описание будет добавлено через BlockService
        return None
    
    def get_module_code(self, module_name: str, blocks: List[MessageBlockInfo]) -> Optional[str]:
        """Возвращает код первого блока, назначенного модулю."""
        for block in blocks:
            if block.module_hint == module_name and block.content:
                return block.content
        return None
    
    def assign_module_to_block(self, block: MessageBlockInfo, module_name: str):
        """Назначает модуль блоку и обновляет идентификатор."""
        old_hint = block.module_hint
        block.module_hint = module_name
        logger.info(f"Блок {block.block_id}: {old_hint} -> {module_name}")
        if block.tree and not block.syntax_error:
            self.identifier.collect_from_tree(block.tree, module_name)
    
    def reset_assignments(self, blocks: List[MessageBlockInfo]):
        """Сбрасывает назначения всех блоков."""
        for block in blocks:
            block.module_hint = None
    
    def remove_temp_modules(self):
        """Удаляет временные модули."""
        self.identifier.remove_temp_modules()
    
    def rebuild_after_dialog(self, blocks: List[MessageBlockInfo]):
        """Перестраивает структуру после диалога."""
        self.orchestrator.module_identifier.remove_temp_modules()
        self.orchestrator.module_groups = self.orchestrator._group_blocks_by_module(blocks)
        self.orchestrator._select_base_blocks()
        self.orchestrator.module_containers = {}
        self.orchestrator._build_initial_structures()
        self.orchestrator._merge_remaining_blocks()
        self.orchestrator._merge_temp_modules()
        self.module_containers = self.orchestrator.module_containers