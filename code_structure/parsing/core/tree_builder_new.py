# code_structure/parsing/core/tree_builder_new.py

"""
Построитель DTO для UI из дерева VersionedNode.
"""

import re
from typing import List, Dict, Any, Optional, Tuple

from code_structure.models.versioned_node import (
    VersionedNode, VersionedModule, VersionedClass, VersionedFunction,
    VersionedMethod, VersionedCodeBlock, VersionedImport
)
from code_structure.models.registry import BlockRegistry
from code_structure.dialogs.dto import TreeDisplayNode, FlatListItem

from code_structure.utils.logger import get_logger

logger = get_logger(__name__)


class TreeBuilderNew:
    """
    Строит DTO для отображения из дерева VersionedNode.
    """

    @staticmethod
    def build_display_tree(
        versioned_roots: Dict[str, VersionedModule],
        local_only: bool
    ) -> Tuple[TreeDisplayNode, List[FlatListItem], Dict[str, VersionedNode]]:
        """
        Строит корневой узел дерева, плоский список и словарь для быстрого поиска.

        Args:
            versioned_roots: словарь {имя_модуля: VersionedModule}
            local_only: фильтр "только локальные импорты"

        Returns:
            tuple: (корневой_узел, плоский_список, словарь {full_name: VersionedNode})
        """
        if not versioned_roots:
            return TreeBuilderNew._empty_tree(), [], {}

        flat_items = []
        children = []
        path_map = {}  # full_name -> VersionedNode

        for name, vmodule in versioned_roots.items():
            # Фильтрация локальности
            if local_only and not TreeBuilderNew._is_local(vmodule):
                continue
            node, path_map = TreeBuilderNew._versioned_to_node(vmodule, local_only, flat_items, path_map)
            if node:
                children.append(node)

        max_version = max((node.version for node in children if node.version), default='')
        root = TreeDisplayNode(
            text="Все модули",
            type="root",
            signature="",
            version=f"v{max_version}" if max_version else "",
            sources="",
            children=children
        )
        return root, flat_items, path_map

    @staticmethod
    def _empty_tree() -> TreeDisplayNode:
        return TreeDisplayNode(
            text="Все модули",
            type="root",
            signature="",
            version="",
            sources="",
            children=[]
        )

    @staticmethod
    def _is_local(vnode: VersionedNode) -> bool:
        """Определяет, является ли узел локальным (не импортированным)."""
        # Для модуля: если у него есть флаг is_imported, иначе считаем локальным
        if isinstance(vnode, VersionedModule):
            return not getattr(vnode, 'is_imported', False)
        # Для остальных: локальность определяется родителем
        if vnode.parent:
            return TreeBuilderNew._is_local(vnode.parent)
        return True

    @staticmethod
    def _versioned_to_node(
        vnode: VersionedNode,
        local_only: bool,
        flat_items: List[FlatListItem],
        path_map: Dict[str, VersionedNode],
        parent_path: str = ""
    ) -> Tuple[Optional[TreeDisplayNode], Dict[str, VersionedNode]]:
        """Рекурсивно преобразует VersionedNode в TreeDisplayNode."""
        # Сохраняем в словарь для быстрого поиска
        path_map[vnode.full_path] = vnode

        # Базовый узел
        node = TreeDisplayNode(
            text=vnode.name,
            type=vnode.node_type,
            signature="",
            version=f"v{len(vnode.versions)}" if vnode.versions else "",
            sources="",
            children=[],
            full_name=vnode.full_path
        )

        # Для узлов, которые могут иметь версии (функции, методы, блоки, импорты)
        if vnode.node_type in ('function', 'method', 'code_block', 'import'):
            # Добавляем версии как детей
            for i, version in enumerate(vnode.versions, 1):
                version_node = TreeBuilderNew._version_to_node(version, i, vnode)
                node.children.append(version_node)

            # Добавляем запись в плоский список для последней версии (если есть)
            if vnode.versions:
                latest = vnode.versions[-1]
                src = latest.sources[-1]
                block = BlockRegistry().get(src.block_id)
                if block:
                    block_name = block.display_name
                else:
                    block_name = src.block_id

                # Определяем имя класса (если узел метод)
                class_name = '-'
                if vnode.node_type == 'method':
                    if vnode.parent and vnode.parent.node_type == 'class':
                        class_name = vnode.parent.name

                item = FlatListItem(
                    block_id=src.block_id,
                    block_name=block_name,
                    node_path=vnode.local_path,
                    parent_path=parent_path,
                    lines=f"{src.start_line}-{src.end_line}",
                    module=vnode.full_path.rsplit('.', 1)[0] if '.' in vnode.full_path else '',
                    class_name=class_name,
                    strategy=''
                )
                flat_items.append(item)

        # Для составных узлов (модуль, класс, пакет) – рекурсивно обрабатываем детей
        if vnode.node_type in ('module', 'class', 'package'):
            current_path = f"{parent_path}.{vnode.name}" if parent_path else vnode.name
            for child in vnode.children:
                child_node, path_map = TreeBuilderNew._versioned_to_node(
                    child, local_only, flat_items, path_map, current_path
                )
                if child_node:
                    node.children.append(child_node)

        return node, path_map

    @staticmethod
    def _version_to_node(version_info, index: int, parent_vnode: VersionedNode) -> TreeDisplayNode:
        """Создаёт узел для версии."""
        src = version_info.sources[-1]
        block_id = src.block_id
        start = src.start_line
        end = src.end_line
        sources = f"{block_id}:{start}-{end}"
        if len(version_info.sources) > 1:
            sources += f" ({len(version_info.sources)})"
        return TreeDisplayNode(
            text=parent_vnode.name,
            type="version",
            signature="",
            version=f"v{index}",
            sources=sources,
            children=[],
            full_name=f"{parent_vnode.full_path}_v{index}",
            block_id=block_id,
            start_line=start,
            end_line=end
        )