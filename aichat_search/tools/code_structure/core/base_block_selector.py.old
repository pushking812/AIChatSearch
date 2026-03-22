# aichat_search/tools/code_structure/core/base_block_selector.py

from typing import List, Optional
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo


class BaseBlockSelector:
    """Выбирает базовый (наиболее полный) блок для модуля."""

    @staticmethod
    def select_base_block(blocks: List[MessageBlockInfo]) -> Optional[MessageBlockInfo]:
        """
        Выбирает блок с наибольшим количеством узлов.
        При равенстве выбирает блок с меньшим global_index.
        """
        if not blocks:
            return None

        best = None
        best_cnt = -1
        best_idx = float('inf')

        for block in blocks:
            if block.tree is None or block.syntax_error:
                continue
            count = block.tree.count_nodes()
            if count > best_cnt or (count == best_cnt and block.global_index < best_idx):
                best_cnt = count
                best_idx = block.global_index
                best = block

        return best