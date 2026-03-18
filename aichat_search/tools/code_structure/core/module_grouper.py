# aichat_search/tools/code_structure/core/module_grouper.py

from collections import defaultdict
from typing import Dict, List
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo


class ModuleGrouper:
    """Группирует блоки по модулям на основе module_hint."""

    @staticmethod
    def group_blocks(blocks: List[MessageBlockInfo]) -> Dict[str, List[MessageBlockInfo]]:
        """
        Группирует блоки по module_hint.
        Блоки без module_hint не включаются в результат.
        """
        groups = defaultdict(list)
        for block in blocks:
            if block.module_hint:
                groups[block.module_hint].append(block)
        return dict(groups)