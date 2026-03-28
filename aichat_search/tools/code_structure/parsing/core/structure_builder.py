# aichat_search/tools/code_structure/core/structure_builder.py

import logging
from typing import List

from aichat_search.tools.code_structure.parsing.models.node import Node
from aichat_search.tools.code_structure.module_resolution.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.module_resolution.models.containers import (
    ModuleContainer, Container
)
from aichat_search.tools.code_structure.parsing.core.node_processor import (
    InitialBuildProcessor, MergeProcessor
)
from aichat_search.tools.code_structure.utils.logger import get_logger

from aichat_search.tools.code_structure.utils.logger import get_logger
logger = get_logger(__name__, level = logging.WARNING)


class StructureBuilder:
    """
    Построитель структуры модулей из AST-узлов.
    Использует процессоры для начального построения и последующего слияния блоков.
    """

    def __init__(self):
        self._block_order = {}
        self._operation_logger = StructureBuilderLogger("StructureBuilder")
        self.initial_processor = InitialBuildProcessor(self)
        self.merge_processor = MergeProcessor(self)

    def build_initial_structure(self, module_name: str, base_block: MessageBlockInfo, all_blocks: List[MessageBlockInfo] = None) -> ModuleContainer:
        """
        Строит начальную структуру модуля на основе базового блока.

        Args:
            module_name: имя модуля
            base_block: базовый блок (обычно самый полный)
            all_blocks: список всех блоков модуля (для сохранения порядка обработки)

        Returns:
            ModuleContainer с построенной структурой
        """
        self._operation_logger.start_operation("build_initial_structure", {
            'module_name': module_name,
            'base_block': base_block.block_id,
            'has_all_blocks': all_blocks is not None
        })

        logger.info(f"=== build_initial_structure для модуля {module_name} ===")
        module_container = ModuleContainer(module_name)

        if all_blocks:
            self._block_order = {block.block_id: block.metadata.get('module_order', idx)
                                for idx, block in enumerate(all_blocks)}
            self._operation_logger.log_decision(
                "set_block_order",
                {'module': module_name, 'blocks_count': len(all_blocks)},
                "Сохранен порядок блоков для последующего слияния"
            )

        if base_block.tree is None:
            self._operation_logger.log_decision(
                "skip_empty_tree",
                {'block': base_block.block_id},
                "Пропуск блока без дерева"
            )
            self._operation_logger.end_operation("build_initial_structure", "empty")
            return module_container

        self.initial_processor.process(base_block.tree, module_container, base_block, "root")

        self._operation_logger.log_decision(
            "structure_built",
            {
                'module': module_name,
                'containers_count': len(module_container.children),
                'block_order_size': len(self._block_order)
            },
            "Начальная структура построена"
        )

        self._operation_logger.end_operation("build_initial_structure", f"containers: {len(module_container.children)}")
        return module_container

    def merge_node_into_container(self, node: Node, container: Container, block_info: MessageBlockInfo, path: str = ""):
        """
        Сливает узел из дополнительного блока в существующий контейнер.

        Args:
            node: узел AST
            container: целевой контейнер
            block_info: информация о блоке, из которого получен узел
            path: путь для логирования
        """
        self._operation_logger.start_operation("merge_node_into_container", {
            'node_type': node.node_type,
            'node_name': getattr(node, 'name', 'unknown'),
            'container': container.name,
            'block': block_info.block_id
        })

        self.merge_processor.process(node, container, block_info, path)

        self._operation_logger.end_operation("merge_node_into_container", f"merged {node.node_type}")

    def _get_block_order(self, block: MessageBlockInfo) -> int:
        """
        Возвращает порядковый номер блока для логирования.
        Если номер не задан, возвращает 0.
        """
        order = 0
        if hasattr(self, '_block_order') and block.block_id in self._block_order:
            order = self._block_order[block.block_id]
        else:
            order = getattr(block, 'module_order', 0)

        self._operation_logger.log_decision(
            "get_block_order",
            {'block': block.block_id, 'order': order},
            "Получен порядковый номер блока"
        )
        return order