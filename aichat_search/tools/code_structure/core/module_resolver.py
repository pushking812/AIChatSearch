# aichat_search/tools/code_structure/core/module_resolver.py

import logging
from typing import List, Optional, Tuple, Dict

from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier
from aichat_search.tools.code_structure.core.resolution_strategy import (
    ClassStrategy, MethodStrategy, FunctionStrategy, ImportStrategy
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


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
            logger.info(f"  Блок имеет ошибку или пустое дерево")
            return False, None, None

        for strategy in self.strategies:
            module = strategy.resolve(block_info, self.module_identifier)

            if module:
                logger.info(f"  -> НАЙДЕН ПО {strategy.__class__.__name__}: {module}")
                block_info.assignment_strategy = strategy.__class__.__name__
                return True, module, None

        logger.info(f"  -> НЕ ОПРЕДЕЛЕН")
        return False, None, None