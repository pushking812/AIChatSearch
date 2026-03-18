# aichat_search/tools/code_structure/core/module_resolver.py

import logging
from typing import List, Optional, Tuple, Dict

from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier
from aichat_search.tools.code_structure.core.resolution_strategy import (
    ClassStrategy, MethodStrategy, FunctionStrategy
)

logger = logging.getLogger(__name__)


class ModuleResolver:
    """
    Определитель модулей с использованием стратегий.
    Последовательно применяет стратегии: классы, методы, функции.
    """

    def __init__(self, module_identifier: ModuleIdentifier):
        self.module_identifier = module_identifier
        self.strategies = [
            ClassStrategy(),
            MethodStrategy(),
            FunctionStrategy()
        ]
        self.auto_assign: Dict[str, str] = {}
        self.need_dialog: List[MessageBlockInfo] = []

    def resolve_block(self, block_info: MessageBlockInfo) -> Tuple[bool, Optional[str], None]:
        logger.info(f"=== resolve_block для {block_info.block_id} ===")

        if block_info.tree is None or block_info.syntax_error:
            logger.info(f"  Блок имеет ошибку или пустое дерево")
            return False, None, None

        for strategy in self.strategies:
            # Сбрасываем флаг неоднозначности перед использованием
            strategy.ambiguous = False
            module = strategy.resolve(block_info, self.module_identifier)

            if strategy.ambiguous:
                logger.info(f"  -> НЕОДНОЗНАЧНО ПО {strategy.__class__.__name__}, требуется диалог")
                self.need_dialog.append(block_info)
                return False, None, None

            if module:
                logger.info(f"  -> НАЙДЕН ПО {strategy.__class__.__name__}: {module}")
                self.auto_assign[block_info.block_id] = module
                return True, module, None

        logger.info(f"  -> НЕ ОПРЕДЕЛЕН")
        self.need_dialog.append(block_info)
        return False, None, None

    def get_auto_assignments(self):
        return self.auto_assign.copy()

    def get_need_dialog(self):
        return self.need_dialog.copy()

    def clear_temp_data(self):
        self.auto_assign.clear()
        self.need_dialog.clear()