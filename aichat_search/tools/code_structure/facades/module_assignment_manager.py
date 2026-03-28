# aichat_search/tools/code_structure/facades/module_assignment_manager.py

import logging
from typing import Dict, List

from aichat_search.tools.code_structure.block_processing.services.block_service import BlockService
from aichat_search.tools.code_structure.module_resolution.services.module_service import ModuleService
from aichat_search.tools.code_structure.parsing.core.tree_builder import TreeBuilder
from aichat_search.tools.code_structure.ui.dto import (
    ModuleAssignmentInput, UnknownBlockInfo, KnownModuleInfo, ModuleAssignmentOutput
)
from aichat_search.tools.code_structure.ui.dto_builder import DtoBuilder
from aichat_search.tools.code_structure.utils.logger import get_logger

logger = get_logger(__name__)


class ModuleAssignmentManager:
    def __init__(self, block_service: BlockService, module_service: ModuleService, tree_builder: TreeBuilder):
        self.block_service = block_service
        self.module_service = module_service
        self.tree_builder = tree_builder

    def get_module_assignment_input(self, local_only: bool) -> ModuleAssignmentInput:
        """Подготавливает DTO для диалога назначения модулей."""
        unknown_blocks_info = []
        for block in self.module_service.unknown_blocks:
            display_name = f"{block.block_id} – {self.block_service.get_block_description(block)}"
            unknown_blocks_info.append(UnknownBlockInfo(
                id=block.block_id,
                display_name=display_name,
                content=block.content
            ))

        known_modules_info = []
        for module_name in sorted(self.module_service.get_known_modules()):
            source = self.module_service.get_module_source(module_name, self.block_service.get_all_blocks())
            code = self.module_service.get_module_code(module_name, self.block_service.get_all_blocks()) or ""
            known_modules_info.append(KnownModuleInfo(
                name=module_name,
                source=source,
                code=code
            ))

        root_dict, _ = self.tree_builder.build_display_tree(
            self.module_service.module_containers,
            local_only=local_only
        )
        module_tree = DtoBuilder.tree_dict_to_dto(root_dict)

        return ModuleAssignmentInput(
            unknown_blocks=unknown_blocks_info,
            known_modules=known_modules_info,
            module_tree=module_tree
        )

    def apply_assignments(self, assignments: Dict[str, str]) -> None:
        """Применяет назначения модулей к блокам и перестраивает структуру."""
        all_blocks = self.block_service.get_all_blocks()
        for block in all_blocks:
            if block.block_id in assignments:
                block.module_hint = assignments[block.block_id]
                if block.tree and not block.syntax_error:
                    self.module_service.identifier.collect_from_tree(
                        block.tree, block.module_hint, block_info=block
                    )

        # Перестраиваем контейнеры
        text_blocks_by_pair = self.block_service.get_text_blocks_by_pair()
        full_texts_by_pair = self.block_service.get_full_texts_by_pair()
        containers, unknown_blocks = self.module_service.process_blocks(
            all_blocks,
            text_blocks_by_pair=text_blocks_by_pair,
            full_texts_by_pair=full_texts_by_pair
        )
        self.module_service.module_containers = containers
        self.module_service.unknown_blocks = unknown_blocks

    def reset_assignments(self) -> None:
        """Сбрасывает все назначения модулей (без перестроения структуры)."""
        all_blocks = self.block_service.get_all_blocks()
        self.module_service.reset_assignments(all_blocks)
        # Перестраиваем контейнеры заново
        text_blocks_by_pair = self.block_service.get_text_blocks_by_pair()
        full_texts_by_pair = self.block_service.get_full_texts_by_pair()
        containers, unknown_blocks = self.module_service.process_blocks(
            all_blocks,
            text_blocks_by_pair=text_blocks_by_pair,
            full_texts_by_pair=full_texts_by_pair
        )
        self.module_service.module_containers = containers
        self.module_service.unknown_blocks = unknown_blocks