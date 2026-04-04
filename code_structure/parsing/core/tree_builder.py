# code_structure/parsing/core/tree_builder.py

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

import logging
logger = get_logger(__name__, level=logging.WARNING)


class TreeBuilderNew:
    @staticmethod
    def build_display_tree(
        versioned_roots: Dict[str, VersionedNode],
        local_only: bool
    ) -> Tuple[TreeDisplayNode, List[FlatListItem], Dict[str, VersionedNode], Dict[Tuple[str, int, int], VersionedNode]]:
        if not versioned_roots:
            return TreeBuilderNew._empty_tree(), [], {}, {}

        flat_items = []
        children = []
        path_map = {}
        source_map = {}

        for name, vnode in versioned_roots.items():
            if local_only and not TreeBuilderNew._is_local(vnode):
                continue
            node, path_map, source_map = TreeBuilderNew._versioned_to_node(vnode, local_only, flat_items, path_map, source_map)
            if node:
                children.append(node)

        logger.debug(f"Root has {len(children)} children")
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
        return getattr(vnode, 'is_local', False)

    @staticmethod
    def _versioned_to_node(
        vnode: VersionedNode,
        local_only: bool,
        flat_items: List[FlatListItem],
        path_map: Dict[str, VersionedNode],
        source_map: Dict[Tuple[str, int, int], VersionedNode],
        parent_path: str = ""
    ) -> Tuple[Optional[TreeDisplayNode], Dict[str, VersionedNode], Dict[Tuple[str, int, int], VersionedNode]]:
        logger.debug(f"Rendering node {vnode.name} type={vnode.node_type} with {len(vnode.children)} children")

        name = vnode.name if vnode.name is not None else "?"
        full_name = vnode.full_path if vnode.full_path is not None else name

        path_map[full_name] = vnode

        for version in vnode.versions:
            for src in version.sources:
                key = (src.block_id, src.start_line, src.end_line)
                if key not in source_map:
                    source_map[key] = vnode

        node = TreeDisplayNode(
            text=name,
            type=vnode.node_type,
            signature="",
            version=f"v{len(vnode.versions)}" if vnode.versions else "",
            sources="",
            children=[],
            full_name=full_name
        )

        if vnode.node_type in ('function', 'method', 'code_block', 'import'):
            for i, version in enumerate(vnode.versions, 1):
                version_node = TreeBuilderNew._version_to_node(version, i, vnode)
                node.children.append(version_node)

            # Не добавляем плоские записи здесь, чтобы избежать дублирования.
            # Все записи будут добавлены через build_flat_list_from_blocks.

        if vnode.node_type in ('module', 'class', 'package'):
            current_path = f"{parent_path}.{name}" if parent_path else name
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
            node_path = node.name if node.name is not None else "?"
        else:
            node_path = node.name if node.name is not None else "?"

        # Родительский узел для отображения в колонке "Родитель"
        source_parent = ""
        if isinstance(node, MethodNode) and node.parent and isinstance(node.parent, ClassNode):
            source_parent = node.parent.name if node.parent.name is not None else ""
        elif isinstance(node, CodeBlockNode) and node.parent and isinstance(node.parent, ClassNode):
            source_parent = node.parent.name if node.parent.name is not None else ""

        key = (block.id, node.start_line, node.end_line)
        vnode = source_map.get(key)

        module = ""
        class_name = "-"
        strategy = ""

        if vnode:
            # Получаем родительский класс (если есть)
            parent_class = None
            temp = vnode.parent
            while temp:
                if temp.node_type == 'class':
                    parent_class = temp
                    break
                temp = temp.parent

            # Получаем родительский модуль (верхний уровень)
            parent_module = None
            temp_mod = vnode.parent
            while temp_mod:
                if temp_mod.node_type in ('module', 'package'):
                    parent_module = temp_mod
                    break
                temp_mod = temp_mod.parent

            if vnode.node_type == 'method':
                # Для метода: module = полный путь родительского модуля, class_name = имя класса
                if parent_module:
                    module = parent_module.full_path
                else:
                    module = block.module_hint or ''
                if parent_class:
                    class_name = parent_class.name
                else:
                    class_name = '-'
            elif vnode.node_type == 'code_block':
                # Для блока кода внутри класса: аналогично методу
                if parent_module:
                    module = parent_module.full_path
                else:
                    module = block.module_hint or ''
                if parent_class:
                    class_name = parent_class.name
                else:
                    class_name = '-'
            elif vnode.node_type == 'function':
                # Для функции: module = полный путь родительского модуля (без класса)
                if parent_module:
                    module = parent_module.full_path
                else:
                    module = block.module_hint or ''
                class_name = '-'
            else:
                # Для остальных (import, class, module) – module = полный путь узла
                module = vnode.full_path
                class_name = '-'
            strategy = block.assignment_strategy or ""
        else:
            # Нет версионированного узла – используем подсказки из блока
            if block.module_hint:
                module = block.module_hint
                strategy = block.assignment_strategy or ""
                # Определяем класс, если узел является методом или блоком кода внутри класса
                if isinstance(node, MethodNode) and node.parent and isinstance(node.parent, ClassNode):
                    class_name = node.parent.name if node.parent.name else "-"
                elif isinstance(node, CodeBlockNode) and node.parent and isinstance(node.parent, ClassNode):
                    class_name = node.parent.name if node.parent.name else "-"
                else:
                    class_name = '-'
            else:
                strategy = "Неназначенный блок"
                module = ""
                class_name = '-'

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

        current_path = f"{parent_path}.{node.name}" if parent_path else node.name
        for child in node.children:
            TreeBuilderNew._collect_flat_items_from_node(child, block, source_map, flat_items, current_path)