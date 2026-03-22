# aichat_search/tools/code_structure/core/block_sorter.py

import re
from typing import List
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo


class BlockSorter:
    """Сортирует блоки внутри модуля по приоритету."""

    @staticmethod
    def get_priority(block: MessageBlockInfo) -> int:
        """
        Возвращает приоритет блока для сортировки внутри модуля.
        Чем меньше число, тем раньше должен обрабатываться блок.
        """
        if not block.tree or block.syntax_error:
            return 999  # ошибочные блоки в конец

        has_classes = BlockSorter._has_classes(block)
        has_imports = BlockSorter._has_imports(block.content)

        if has_classes:
            return 1  # классы - наивысший приоритет
        elif has_imports:
            return 2  # импорты - следующий приоритет
        elif block.module_hint:
            return 3  # module_hint без классов/импортов
        else:
            return 4  # всё остальное

    @staticmethod
    def _has_classes(block: MessageBlockInfo) -> bool:
        """Проверяет, содержит ли блок классы."""
        if not block.tree:
            return False
        for child in block.tree.children:
            if child.node_type == "class":
                return True
        return False

    @staticmethod
    def _has_imports(content: str) -> bool:
        """Проверяет, содержит ли код импорты."""
        import_patterns = [
            r'^import\s+\w+',
            r'^from\s+\w+\s+import',
        ]
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            for pattern in import_patterns:
                if re.match(pattern, line):
                    return True
        return False

    @staticmethod
    def sort_blocks(blocks: List[MessageBlockInfo]) -> List[MessageBlockInfo]:
        """
        Сортирует блоки по приоритету, а внутри одинакового приоритета - по global_index.
        Присваивает каждому блоку module_order в метаданных.
        """
        sorted_blocks = sorted(blocks,
                               key=lambda b: (BlockSorter.get_priority(b), b.global_index))

        for order, block in enumerate(sorted_blocks, 1):
            if block.metadata is None:
                block.metadata = {}
            block.metadata['module_order'] = order

        return sorted_blocks