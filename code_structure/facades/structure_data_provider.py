# code_structure/facades/structure_data_provider.py

import textwrap
from typing import List, Tuple, Optional, Dict, Any
import logging

from aichat_search.model import Chat, MessagePair
from code_structure.block_processing.services.block_service import BlockService
from code_structure.module_resolution.services.module_service import ModuleService
from code_structure.parsing.core.tree_builder import TreeBuilder
from code_structure.module_resolution.models.block_info import MessageBlockInfo
from code_structure.module_resolution.models.containers import Container
from code_structure.imports.services.import_service import ImportService
from code_structure.dialogs.dto import (
    TreeDisplayNode, FlatListItem, CodeStructureInitDTO, CodeStructureRefreshDTO
)
from code_structure.dialogs.dto_builder import DtoBuilder
from code_structure.utils.logger import get_logger

logger = get_logger(__name__)


class StructureDataProvider:
    def __init__(self, items: List[Tuple[Chat, MessagePair]]):
        self.items = items
        self.block_service = BlockService()
        self.module_service = ModuleService()
        self.import_service = ImportService()
        self.tree_builder = TreeBuilder()

        # Внутреннее состояние
        self._full_name_to_container: Dict[str, Container] = {}
        self._flat_items_raw: List[Dict[str, Any]] = []
        self._has_unknown_blocks: bool = False
        self._languages: List[str] = []
        self._current_local_only: bool = True

        # Новое для новых моделей
        self._use_new_models = True   # пока false, позже переключим
        self._versioned_roots: Dict[str, 'VersionedModule'] = {}
        self._versioned_nodes_by_full_name: Dict[str, 'VersionedNode'] = {}

    # ---------- Публичные методы ----------

    def load_blocks(self) -> None:
        """
        Загружает блоки из items, обрабатывает ошибки, строит начальную структуру.
        """
        # 1. Загружаем блоки через BlockService (старая и новая логика)
        self.block_service.load_from_items(self.items)

        error_blocks = self.block_service.get_error_blocks()
        if error_blocks:
            logger.warning(f"Найдены блоки с ошибками: {len(error_blocks)}")

        all_blocks = self.block_service.get_all_blocks()
        text_blocks_by_pair = self.block_service.get_text_blocks_by_pair()
        full_texts_by_pair = self.block_service.get_full_texts_by_pair()

        # 2. Старая логика разрешения модулей (использует MessageBlockInfo)
        containers, unknown_blocks = self.module_service.process_blocks(
            all_blocks,
            text_blocks_by_pair=text_blocks_by_pair,
            full_texts_by_pair=full_texts_by_pair
        )
        self.module_service.module_containers = containers
        self.module_service.unknown_blocks = unknown_blocks
        self._has_unknown_blocks = bool(unknown_blocks)

        # 3. Старое построение дерева и плоского списка
        self._build_tree_and_flat_items(self._current_local_only)

        # 4. Получаем языки (из старых блоков)
        self._languages = self.block_service.get_languages()

        # ---------------------------------------------
        # Построение нового дерева VersionedNode
        # ---------------------------------------------
        from code_structure.module_resolution.services.versioned_tree_builder import VersionedTreeBuilder
        builder = VersionedTreeBuilder()
        new_blocks = self.block_service.get_new_blocks()
        self._versioned_roots, unknown = builder.build_from_blocks(
            new_blocks,
            text_blocks_by_pair=text_blocks_by_pair,
            full_texts_by_pair=full_texts_by_pair
        )
        logger.info(f"[NEW] Построено модулей: {len(self._versioned_roots)}, неразрешённых блоков: {len(unknown)}")

        # 5. Построение DTO и словаря для быстрого доступа (для новых моделей)
        from code_structure.parsing.core.tree_builder_new import TreeBuilderNew
        _, _, path_map = TreeBuilderNew.build_display_tree(self._versioned_roots, self._current_local_only)
        self._versioned_nodes_by_full_name = path_map

    def get_initial_data(self) -> CodeStructureInitDTO:
        """Возвращает начальные DTO для отображения."""
        if self._use_new_models:
            from code_structure.parsing.core.tree_builder_new import TreeBuilderNew
            tree_root, flat_items, _ = TreeBuilderNew.build_display_tree(
                self._versioned_roots, self._current_local_only
            )
            return CodeStructureInitDTO(
                languages=self._languages,
                tree=tree_root,
                flat_items=flat_items,
                has_unknown_blocks=self._has_unknown_blocks
            )
        else:
            return CodeStructureInitDTO(
                languages=self._languages,
                tree=self._build_tree_dto(),
                flat_items=self._build_flat_dto(),
                has_unknown_blocks=self._has_unknown_blocks
            )

    def refresh(self, local_only: bool) -> CodeStructureRefreshDTO:
        """Перестраивает дерево и плоский список с учётом фильтра local_only."""
        self._current_local_only = local_only
        if self._use_new_models:
            from code_structure.parsing.core.tree_builder_new import TreeBuilderNew
            tree_root, flat_items, path_map = TreeBuilderNew.build_display_tree(
                self._versioned_roots, local_only
            )
            self._versioned_nodes_by_full_name = path_map
            return CodeStructureRefreshDTO(tree=tree_root, flat_items=flat_items)
        else:
            self._build_tree_and_flat_items(local_only)
            return CodeStructureRefreshDTO(
                tree=self._build_tree_dto(),
                flat_items=self._build_flat_dto()
            )

    def get_code_for_block(self, block_id: str) -> Optional[str]:
        """Возвращает код для блока по его ID."""
        if self._use_new_models:
            block = self.block_service.get_new_block(block_id)
            if block:
                return block.content
            return None
        else:
            block = next((b for b in self.block_service.get_all_blocks() if b.block_id == block_id), None)
            if block:
                return block.content
            return None

    def get_code_for_node(self, node_data: TreeDisplayNode) -> Optional[str]:
        """Возвращает код для узла дерева."""
        if self._use_new_models:
            # Для версий используем прямой доступ к блоку
            if node_data.type == 'version' and node_data.block_id:
                block = self.block_service.get_new_block(node_data.block_id)
                if block:
                    lines = block.content.splitlines()
                    if node_data.start_line and node_data.end_line:
                        fragment = '\n'.join(lines[node_data.start_line-1:node_data.end_line])
                    else:
                        fragment = block.content
                    return textwrap.dedent(fragment)

            # Для остальных узлов ищем VersionedNode по полному имени
            vnode = self._versioned_nodes_by_full_name.get(node_data.full_name)
            if vnode:
                return self._render_versioned_node_code(vnode)
            return None
        else:
            # Старый код
            container = self._full_name_to_container.get(node_data.full_name)
            if container:
                return self._render_code_from_container(container)
            return None

    def get_error_blocks(self) -> List[MessageBlockInfo]:
        """Возвращает список блоков с синтаксическими ошибками."""
        return self.block_service.get_error_blocks()

    def fix_error_block(self, block_id: str, new_code: str) -> None:
        """Исправляет блок с ошибкой и перестраивает структуру."""
        if self._use_new_models:
            # TODO: обновить новый блок и перестроить дерево
            pass
        else:
            block = next((b for b in self.block_service.get_all_blocks() if b.block_id == block_id), None)
            if block:
                self.block_service.fix_error_block(block, new_code)
                self.rebuild_structure()

    def rebuild_structure(self) -> None:
        """Перестраивает модульную структуру из текущих блоков."""
        if self._use_new_models:
            # TODO: перестроить новое дерево
            pass
        else:
            all_blocks = self.block_service.get_all_blocks()
            text_blocks_by_pair = self.block_service.get_text_blocks_by_pair()
            full_texts_by_pair = self.block_service.get_full_texts_by_pair()

            containers, unknown_blocks = self.module_service.process_blocks(
                all_blocks,
                text_blocks_by_pair=text_blocks_by_pair,
                full_texts_by_pair=full_texts_by_pair
            )
            self.module_service.module_containers = containers
            self.module_service.unknown_blocks = unknown_blocks
            self._has_unknown_blocks = bool(unknown_blocks)

            self._build_tree_and_flat_items(self._current_local_only)

    def has_unknown_blocks(self) -> bool:
        """Возвращает True, если есть неопределённые блоки."""
        return self._has_unknown_blocks

    # ---------- Внутренние методы (старая логика) ----------
    def _build_tree_and_flat_items(self, local_only: bool):
        """Строит дерево и плоский список, сохраняет сырые данные и словарь контейнеров."""
        root, flat_items = self.tree_builder.build_display_tree(
            self.module_service.module_containers,
            local_only=local_only
        )
        self._flat_items_raw = flat_items
        self._full_name_to_container.clear()
        if root:
            self._collect_containers_by_full_name(root, parent_path="")

    def _collect_containers_by_full_name(self, node_dict: Dict[str, Any], parent_path: str = ""):
        node_name = node_dict.get('text', '')
        current_path = f"{parent_path}.{node_name}" if parent_path else node_name
        container = node_dict.get('_container')
        if container:
            if hasattr(container, 'full_path') and container.full_path:
                self._full_name_to_container[container.full_path] = container
            else:
                self._full_name_to_container[current_path] = container
        for child in node_dict.get('children', []):
            self._collect_containers_by_full_name(child, current_path)

    def _build_tree_dto(self) -> TreeDisplayNode:
        """Преобразует текущее дерево в DTO (вызывается после _build_tree_and_flat_items)."""
        root, _ = self.tree_builder.build_display_tree(
            self.module_service.module_containers,
            local_only=self._current_local_only
        )
        return DtoBuilder.tree_dict_to_dto(root) if root else TreeDisplayNode(text="", type="root")

    def _build_flat_dto(self) -> List[FlatListItem]:
        """Преобразует сырой плоский список в DTO."""
        if not self._flat_items_raw:
            return []

        all_blocks = self.block_service.get_all_blocks()
        block_map = {b.block_id: b for b in all_blocks}
        enriched = []
        for item in self._flat_items_raw:
            block_id = item['block_id']
            block = block_map.get(block_id)
            if block:
                module = block.module_hint or ''
                strategy = block.assignment_strategy or ''
                enriched_item = item.copy()
                enriched_item['module'] = module
                enriched_item['strategy'] = strategy
                if item['node_type'] == 'method' and item['parent_path']:
                    enriched_item['class'] = item['parent_path'].split('.')[-1]
                else:
                    enriched_item['class'] = '-'
                enriched.append(enriched_item)
            else:
                enriched.append(item)

        return DtoBuilder.flat_items_to_dto(enriched)

    def _render_code_from_container(self, container: Container) -> str:
        logger.debug(f"_render_code_from_container: type={container.node_type}, name={container.name}, versions={len(container.versions)}")
        if container.node_type in ('method', 'function', 'code_block', 'import'):
            latest = container.get_latest_version()
            logger.debug(f"Latest version: {latest}")
            if latest and latest.sources:
                block_id, start, end, _ = latest.sources[0]
                logger.debug(f"Latest source: block={block_id}, lines={start}-{end}")
                block = next((b for b in self.block_service.get_all_blocks() if b.block_id == block_id), None)
                if block:
                    lines = block.content.splitlines()
                    fragment = '\n'.join(lines[start-1:end]) if start and end else block.content
                    code = textwrap.dedent(fragment)
                    logger.debug(f"Extracted code length: {len(code)}")
                    return code
                else:
                    logger.debug("Block not found")
            else:
                logger.debug("No latest version or sources")
            return ""
        elif container.node_type == 'class':
            class_lines = [f"class {container.name}:"]
            for child in container.children:
                child_code = self._render_code_from_container(child)
                if child_code:
                    class_lines.extend("    " + line for line in child_code.splitlines())
            return '\n'.join(class_lines)
        elif container.node_type == 'module':
            lines = []
            for child in container.children:
                child_code = self._render_code_from_container(child)
                if child_code:
                    lines.append(child_code)
            return '\n\n'.join(lines)
        elif container.node_type == 'package':
            return "# Пакет (не содержит кода)"
        return ""

    def _render_versioned_node_code(self, vnode) -> str:
        """Рекурсивно собирает код для узла."""
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