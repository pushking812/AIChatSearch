# code_structure/facades/structure_data_provider.py

import textwrap
from typing import List, Tuple, Optional, Dict, Any

from aichat_search.model import Chat, MessagePair
from code_structure.block_processing.services.block_service import BlockService
from code_structure.imports.services.import_service import ImportService
from code_structure.dialogs.dto import (
    TreeDisplayNode, FlatListItem, CodeStructureInitDTO, CodeStructureRefreshDTO
)
from code_structure.parsing.core.tree_builder import TreeBuilderNew
from code_structure.module_resolution.services.versioned_tree_builder import VersionedTreeBuilder
from code_structure.models.versioned_node import VersionedNode
from code_structure.utils.logger import get_logger

logger = get_logger(__name__)


class StructureDataProvider:
    def __init__(self, items: List[Tuple[Chat, MessagePair]]):
        self.items = items
        self.block_service = BlockService()
        self.import_service = ImportService()
        self.tree_builder = TreeBuilderNew()
        self.module_service = None

        # Внутреннее состояние
        self._versioned_roots: Dict[str, VersionedNode] = {}
        self._versioned_nodes_by_full_name: Dict[str, VersionedNode] = {}
        self._versioned_nodes_by_source: Dict[Tuple[str, int, int], VersionedNode] = {}
        self._all_code_blocks: List['Block'] = []
        self._languages: List[str] = []
        self._current_local_only: bool = True

    def load_blocks(self) -> None:
        # Загружаем блоки через BlockService
        self.block_service.load_from_items(self.items)

        # Получаем все блоки
        all_blocks = self.block_service.get_new_blocks()
        self._all_code_blocks = [b for b in all_blocks if b.language in ('python', 'py')]
        self._languages = list(set(b.language for b in self._all_code_blocks))

        # Строим дерево
        builder = VersionedTreeBuilder()
        text_blocks_by_pair = self.block_service.get_text_blocks_by_pair()
        full_texts_by_pair = self.block_service.get_full_texts_by_pair()
        self._versioned_roots, unknown = builder.build_from_blocks(
            all_blocks,
            text_blocks_by_pair=text_blocks_by_pair,
            full_texts_by_pair=full_texts_by_pair
        )
        logger.info(f"Построено модулей: {len(self._versioned_roots)}, неразрешённых блоков: {len(unknown)}")

        # Построение DTO
        _, _, path_map, source_map = self.tree_builder.build_display_tree(self._versioned_roots, self._current_local_only)
        self._versioned_nodes_by_full_name = path_map
        self._versioned_nodes_by_source = source_map

    def get_initial_data(self) -> CodeStructureInitDTO:
        tree_root, flat_items, _, _ = self.tree_builder.build_display_tree(self._versioned_roots, self._current_local_only)
        return CodeStructureInitDTO(
            languages=self._languages,
            tree=tree_root,
            flat_items=flat_items,
            has_unknown_blocks=False
        )

    def refresh(self, local_only: bool) -> CodeStructureRefreshDTO:
        self._current_local_only = local_only
        tree_root, flat_items, _, _ = self.tree_builder.build_display_tree(self._versioned_roots, local_only)
        return CodeStructureRefreshDTO(tree=tree_root, flat_items=flat_items)

    def get_code_for_node(self, node_data: TreeDisplayNode) -> Optional[str]:
        if node_data.type == 'version' and node_data.block_id:
            block = self.block_service.get_new_block(node_data.block_id)
            if block:
                lines = block.content.splitlines()
                if node_data.start_line and node_data.end_line:
                    fragment = '\n'.join(lines[node_data.start_line-1:node_data.end_line])
                else:
                    fragment = block.content
                return textwrap.dedent(fragment)
        vnode = self._versioned_nodes_by_full_name.get(node_data.full_name)
        if vnode:
            return self._render_versioned_node_code(vnode)
        return None

    def _render_versioned_node_code(self, vnode) -> str:
        if vnode.node_type in ('function', 'method', 'code_block', 'import'):
            return vnode.get_latest_code()
        elif vnode.node_type == 'class':
            class_lines = [f"class {vnode.name}:"]
            for child in vnode.children:
                child_code = self._render_versioned_node_code(child)
                if child_code:
                    class_lines.extend("    " + line for line in child_code.splitlines())
            return '\n'.join(class_lines)
        elif vnode.node_type == 'module':
            lines = []
            for child in vnode.children:
                child_code = self._render_versioned_node_code(child)
                if child_code:
                    lines.append(child_code)
            return '\n\n'.join(lines)
        elif vnode.node_type == 'package':
            return "# Пакет (не содержит кода)"
        return ""

    # Методы для обратной совместимости (не используются, но оставлены)
    def get_error_blocks(self): return []
    def fix_error_block(self, block_id, new_code): pass
    def rebuild_structure(self): pass
    def has_unknown_blocks(self): return False
    
    def get_code_for_block(self, block_id: str) -> Optional[str]:
        """Возвращает код для блока по его ID."""
        block = self.block_service.get_new_block(block_id)
        if block:
            return block.content
        return None
        
    def get_versioned_roots(self) -> Dict[str, VersionedNode]:
        return self._versioned_roots

    def set_versioned_roots(self, roots: Dict[str, VersionedNode]):
        self._versioned_roots = roots
        from code_structure.parsing.core.tree_builder_new import TreeBuilderNew
        _, _, path_map, source_map = TreeBuilderNew.build_display_tree(self._versioned_roots, self._current_local_only)
        self._versioned_nodes_by_full_name = path_map
        self._versioned_nodes_by_source = source_map