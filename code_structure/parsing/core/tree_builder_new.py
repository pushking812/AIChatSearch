# code_structure/parsing/core/tree_builder_new.py

import re
from typing import List, Dict, Any, Optional, Tuple

from code_structure.models.versioned_node import (
    VersionedNode, VersionedModule, VersionedClass, VersionedFunction,
    VersionedMethod, VersionedCodeBlock, VersionedImport
)
from code_structure.models.registry import BlockRegistry
from code_structure.models.code_node import (
    CodeNode, ModuleNode, ClassNode, FunctionNode, MethodNode,
    CodeBlockNode, ImportNode, CommentNode
)
from code_structure.dialogs.dto import TreeDisplayNode, FlatListItem
from code_structure.utils.logger import get_logger

logger = get_logger(__name__)


class TreeBuilderNew:
    """
    Строит DTO для отображения из дерева VersionedNode и из исходных CodeNode.
    """

    @staticmethod
    def build_display_tree(
        versioned_roots: Dict[str, VersionedNode],
        local_only: bool
    ) -> Tuple[TreeDisplayNode, List[FlatListItem], Dict[str, VersionedNode], Dict[Tuple[str, int, int], VersionedNode]]:
        """
        Строит корневой узел дерева, плоский список и словари для быстрого поиска.
        """
        if not versioned_roots:
            return TreeBuilderNew._empty_tree(), [], {}, {}

        flat_items = []
        children = []
        path_map = {}  # full_name -> VersionedNode
        source_map = {}  # (block_id, start, end) -> VersionedNode

        for name, vnode in versioned_roots.items():
            if local_only and not TreeBuilderNew._is_local(vnode):
                continue
            node, path_map, source_map = TreeBuilderNew._versioned_to_node(vnode, local_only, flat_items, path_map, source_map)
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
        return root, flat_items, path_map, source_map

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
        if isinstance(vnode, VersionedModule):
            return not getattr(vnode, 'is_imported', False)
        if vnode.parent:
            return TreeBuilderNew._is_local(vnode.parent)
        return True

    @staticmethod
    def _versioned_to_node(
        vnode: VersionedNode,
        local_only: bool,
        flat_items: List[FlatListItem],
        path_map: Dict[str, VersionedNode],
        source_map: Dict[Tuple[str, int, int], VersionedNode],
        parent_path: str = ""
    ) -> Tuple[Optional[TreeDisplayNode], Dict[str, VersionedNode], Dict[Tuple[str, int, int], VersionedNode]]:
        """Рекурсивно преобразует VersionedNode в TreeDisplayNode и заполняет source_map."""
        path_map[vnode.full_path] = vnode

        # Сохраняем все источники в source_map
        for version in vnode.versions:
            for src in version.sources:
                key = (src.block_id, src.start_line, src.end_line)
                if key not in source_map:
                    source_map[key] = vnode

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

                # Определяем имя класса в сводном дереве (если узел метод и его родитель класс)
                class_name = '-'
                if vnode.node_type == 'method':
                    if vnode.parent and vnode.parent.node_type == 'class':
                        class_name = vnode.parent.name

                item = FlatListItem(
                    block_id=src.block_id,
                    block_name=block_name,
                    node_path=vnode.local_path if hasattr(vnode, 'local_path') else vnode.name,
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
                child_node, path_map, source_map = TreeBuilderNew._versioned_to_node(
                    child, local_only, flat_items, path_map, source_map, current_path
                )
                if child_node:
                    node.children.append(child_node)

        return node, path_map, source_map

    @staticmethod
    def _version_to_node(version_info, index: int, parent_vnode: VersionedNode) -> TreeDisplayNode:
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

    @staticmethod
    def build_flat_list_from_blocks(
        blocks: List['Block'],
        source_map: Dict[Tuple[str, int, int], 'VersionedNode']
    ) -> List[FlatListItem]:
        """
        Строит плоский список из всех CodeNode всех блоков.
        Для каждого узла пытается найти соответствующий VersionedNode в source_map.
        """
        flat_items = []
        for block in blocks:
            if not block.code_tree:
                continue
            TreeBuilderNew._collect_flat_items_from_node(
                block.code_tree, block, source_map, flat_items, ""
            )
        return flat_items

    @staticmethod
    def _collect_flat_items_from_node(
        node: CodeNode,
        block: 'Block',
        source_map: Dict[Tuple[str, int, int], 'VersionedNode'],
        flat_items: List[FlatListItem],
        parent_path: str
    ):
        """
        Рекурсивно собирает плоский список, добавляя запись для каждого узла.
        Пропускает корневой ModuleNode (пустое имя).
        """
        # Пропускаем корневой ModuleNode (пустое имя или тип module и отсутствие имени)
        if isinstance(node, ModuleNode) and (not node.name or node.name == ""):
            for child in node.children:
                TreeBuilderNew._collect_flat_items_from_node(child, block, source_map, flat_items, parent_path)
            return

        # Определяем строку для колонки "Узел"
        if isinstance(node, ImportNode):
            node_path = node.statement
        elif isinstance(node, CommentNode):
            node_path = node.text
        elif isinstance(node, CodeBlockNode):
            node_path = "блок кода"
        elif isinstance(node, (FunctionNode, MethodNode, ClassNode)):
            node_path = node.name
        else:
            node_path = node.name or "?"

        # Определяем родителя в исходном коде (класс, если метод внутри класса)
        source_parent = ""
        if isinstance(node, MethodNode) and node.parent and isinstance(node.parent, ClassNode):
            source_parent = node.parent.name

        # Ищем соответствие в source_map
        key = (block.id, node.start_line, node.end_line)
        vnode = source_map.get(key)

        module = ""
        class_name = "-"
        strategy = ""

        if vnode:
            # Назначенный узел
            if vnode.node_type in ('function', 'method', 'code_block', 'import'):
                module = vnode.full_path.rsplit('.', 1)[0] if '.' in vnode.full_path else ''
            else:
                module = vnode.full_path
            if vnode.node_type == 'method' and vnode.parent and vnode.parent.node_type == 'class':
                class_name = vnode.parent.name
            # Стратегию берём из блока (если есть)
            strategy = block.assignment_strategy or ""
        else:
            # Узел не найден, возможно, блок назначен целиком
            if block.module_hint:
                module = block.module_hint
                strategy = block.assignment_strategy or ""
                class_name = '-'
            else:
                strategy = "Неназначенный блок"

        # Создаём запись в плоском списке
        flat_item = FlatListItem(
            block_id=block.id,
            block_name=block.display_name,
            node_path=node_path,
            parent_path=source_parent,
            lines=f"{node.start_line}-{node.end_line}",
            module=module,
            class_name=class_name,
            strategy=strategy
        )
        flat_items.append(flat_item)

        # Рекурсивно обрабатываем детей
        current_path = f"{parent_path}.{node.name}" if parent_path else node.name
        for child in node.children:
            TreeBuilderNew._collect_flat_items_from_node(child, block, source_map, flat_items, current_path)