# aichat_search/tools/code_structure/services/module_service.py

from typing import List, Dict, Optional, Tuple
import logging
import sys

from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.models.containers import Container
from aichat_search.tools.code_structure.services.module_resolver_service import ModuleResolverService
from aichat_search.tools.code_structure.services.import_service import ImportService
from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier
from aichat_search.tools.code_structure.models.import_models import ImportInfo

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class ModuleService:
    def __init__(self):
        self.import_service = ImportService()
        self.resolver_service = ModuleResolverService(self.import_service)
        self.module_containers: Dict[str, Container] = {}
        self.unknown_blocks: List[MessageBlockInfo] = []

    @property
    def identifier(self) -> ModuleIdentifier:
        return self.resolver_service.module_identifier

    def process_blocks(
        self,
        blocks: List[MessageBlockInfo],
        imported_by_module: Optional[Dict[str, List[ImportInfo]]] = None,
        text_blocks_by_pair: Optional[Dict[str, Dict[int, str]]] = None,
        full_texts_by_pair: Optional[Dict[str, str]] = None
    ) -> Tuple[Dict[str, Container], List[MessageBlockInfo]]:
        containers, unknown = self.resolver_service.resolve_blocks(
            blocks,
            text_blocks_by_pair or {},
            full_texts_by_pair or {}
        )
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
            self.identifier.collect_from_tree(block.tree, module_name, block_info=block)
        # После изменения нужно перестроить контейнеры
        self.module_containers = self.resolver_service._build_unified_containers()

    def reset_assignments(self, blocks: List[MessageBlockInfo]):
        for block in blocks:
            block.module_hint = None
        self.module_containers = self.resolver_service._build_unified_containers()

    def remove_temp_modules(self):
        self.identifier.remove_temp_modules()
        self.module_containers = self.resolver_service._build_unified_containers()

    def rebuild_after_dialog(self, blocks: List[MessageBlockInfo]):
        self.module_containers = self.resolver_service._build_unified_containers()
        logger.info(f"Контейнеры перестроены, модулей: {len(self.module_containers)}")