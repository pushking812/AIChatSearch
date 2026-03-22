# aichat_search/tools/code_structure/services/module_service.py

from typing import List, Dict, Optional, Tuple
import logging

from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.models.containers import Container
from aichat_search.tools.code_structure.core.module_orchestrator import ModuleOrchestrator
from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier
from aichat_search.tools.code_structure.models.import_models import ImportInfo

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ModuleService:
    """Сервис для работы с модулями и их структурой."""

    def __init__(self):
        self.orchestrator = ModuleOrchestrator()
        self.module_containers: Dict[str, Container] = {}
        self.unknown_blocks: List[MessageBlockInfo] = []

    @property
    def identifier(self) -> ModuleIdentifier:
        return self.orchestrator.module_identifier

    def process_blocks(
        self,
        blocks: List[MessageBlockInfo],
        imported_by_module: Optional[Dict[str, List[ImportInfo]]] = None
    ) -> Tuple[Dict[str, Container], List[MessageBlockInfo]]:
        containers, unknown = self.orchestrator.process_blocks(blocks, imported_by_module)
        self.module_containers = containers
        self.unknown_blocks = unknown
        logger.info(f"Обработано блоков: {len(blocks)}, определено модулей: {len(containers)}")
        return containers, unknown

    def get_known_modules(self) -> List[str]:
        return sorted(self.identifier.get_known_modules())

    def get_module_source(self, module_name: str, blocks: List[MessageBlockInfo]) -> Optional[str]:
        for block in blocks:
            if block.module_hint == module_name and block.tree:
                return f"{block.block_id} – ..."
        return None

    def get_module_code(self, module_name: str, blocks: List[MessageBlockInfo]) -> Optional[str]:
        for block in blocks:
            if block.module_hint == module_name and block.content:
                return block.content
        return None

    def assign_module_to_block(self, block: MessageBlockInfo, module_name: str):
        old_hint = block.module_hint
        block.module_hint = module_name
        logger.info(f"Блок {block.block_id}: {old_hint} -> {module_name}")
        if block.tree and not block.syntax_error:
            self.identifier.collect_from_tree(block.tree, module_name)

    def reset_assignments(self, blocks: List[MessageBlockInfo]):
        for block in blocks:
            block.module_hint = None

    def remove_temp_modules(self):
        self.identifier.remove_temp_modules()

    def rebuild_after_dialog(self, blocks: List[MessageBlockInfo]):
        self.orchestrator.module_identifier.remove_temp_modules()
        self.orchestrator.module_groups = self.orchestrator._group_blocks_by_module(blocks)
        self.orchestrator._select_base_blocks()
        self.orchestrator.module_containers = {}
        self.orchestrator._build_initial_structures()
        self.orchestrator._merge_remaining_blocks()
        self.orchestrator._merge_temp_modules()
        self.module_containers = self.orchestrator.module_containers