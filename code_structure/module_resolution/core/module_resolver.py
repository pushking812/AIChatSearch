# code_structure/module_resolution/core/module_resolver.py

import logging
from typing import Optional, Tuple

from code_structure.module_resolution.models.block_info import MessageBlockInfo
from code_structure.module_resolution.core.module_identifier import ModuleIdentifier
from code_structure.module_resolution.core.resolution_strategy import (
    ClassStrategy, MethodStrategy, FunctionStrategy, ImportStrategy
)

from code_structure.utils.logger import get_logger
logger = get_logger(__name__, level = logging.WARNING)


class ModuleResolver:
    def __init__(self, module_identifier: ModuleIdentifier):
        self.module_identifier = module_identifier
        self.strategies = [
            ClassStrategy(),
            MethodStrategy(),
            FunctionStrategy(),
            ImportStrategy()
        ]

    def resolve_block(self, block_info: MessageBlockInfo) -> Tuple[bool, Optional[str], None]:
        logger.info(f"=== resolve_block для {block_info.block_id} ===")

        if block_info.tree is None or block_info.syntax_error:
            logger.info("  Блок имеет ошибку или пустое дерево")
            return False, None, None

        for strategy in self.strategies:
            module = strategy.resolve(block_info, self.module_identifier)

            if module:
                logger.info(f"  -> НАЙДЕН ПО {strategy.__class__.__name__}: {module}")
                block_info.assignment_strategy = strategy.__class__.__name__
                return True, module, None

        logger.info("  -> НЕ ОПРЕДЕЛЕН")
        return False, None, None