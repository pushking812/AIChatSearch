# code_structure/facades/structure_data_provider.py

import textwrap
from typing import List, Tuple, Optional, Dict, Any

from aichat_search.model import Chat, MessagePair
from code_structure.block_processing.services.block_service import BlockService
from code_structure.imports.services.import_service import ImportService
from code_structure.dialogs.dto import (
    TreeDisplayNode, FlatListItem, CodeStructureInitDTO, CodeStructureRefreshDTO, AmbiguityInfo
)
from code_structure.parsing.core.tree_builder import TreeBuilderNew
from code_structure.module_resolution.services.versioned_tree_builder import VersionedTreeBuilder
from code_structure.models.versioned_node import VersionedNode
from code_structure.models.block import Block
from code_structure.models.registry import BlockRegistry
from code_structure.models.code_node import (
    CodeNode, ClassNode, FunctionNode, MethodNode,
    CodeBlockNode, ImportNode, CommentNode
)

import logging
from code_structure.utils.logger import get_logger
logger = get_logger(__name__, level=logging.WARNING)


class StructureDataProvider:
    def __init__(self, items: List[Tuple[Chat, MessagePair]]):
        self.items = items
        self.block_service = BlockService()
        self.import_service = ImportService()
        self.tree_builder = TreeBuilderNew()
        self._unknown_blocks: List[Block] = []
        self._error_blocks: List[Block] = []
        self._deleted_blocks: List[Block] = []

        self._versioned_roots: Dict[str, VersionedNode] = {}
        self._versioned_nodes_by_full_name: Dict[str, VersionedNode] = {}
        self._versioned_nodes_by_source: Dict[Tuple[str, int, int], VersionedNode] = {}
        self._all_code_blocks: List[Block] = []
        self._languages: List[str] = []
        self._current_local_only: bool = True
        self._flat_items: List[FlatListItem] = []

        self._tree_builder_instance: Optional[VersionedTreeBuilder] = None
        self._initial_blocks: List[Block] = []   # для сохранения состояния при повторных вызовах

    # ------------------------------------------------------------------
    # Построение плоского списка из всех блоков (включая неопределённые и ошибки)
    # ------------------------------------------------------------------
    def _build_flat_items_from_all_blocks(self) -> List[FlatListItem]:
        flat_items = []

        # 1. Блоки с синтаксическими ошибками (включая удалённые)
        for block in self._error_blocks:
            is_deleted = block in self._deleted_blocks
            strategy = "Удалён" if is_deleted else "Синтаксическая ошибка"
            flat_items.append(FlatListItem(
                block_id=block.id,
                block_name=block.display_name,
                node_path="[Синтаксическая ошибка]",
                parent_path="",
                lines="",
                module="",
                class_name="-",
                strategy=strategy,
                language=block.language
            ))

        # 2. Все блоки с code_tree (включая удалённые)
        sorted_blocks = sorted(self._all_code_blocks, key=lambda b: b.global_index)
        for block in sorted_blocks:
            if block.code_tree is None:
                continue
            is_deleted = block in self._deleted_blocks
            self._collect_flat_items_from_code_node(
                block.code_tree, block, flat_items, is_root=True, is_deleted=is_deleted
            )
        return flat_items

    def _collect_flat_items_from_code_node(
        self,
        node: CodeNode,
        block: Block,
        flat_items: List[FlatListItem],
        is_root: bool = False,
        is_deleted: bool = False
    ):
        if isinstance(node, ClassNode):
            for child in node.children:
                self._collect_flat_items_from_code_node(child, block, flat_items, is_root=False, is_deleted=is_deleted)
            return

        if not is_root:
            if isinstance(node, ImportNode):
                node_path = node.statement
            elif isinstance(node, CommentNode):
                node_path = node.text
            elif isinstance(node, CodeBlockNode):
                node_path = "блок кода"
            elif isinstance(node, (FunctionNode, MethodNode)):
                node_path = node.name if node.name else "?"
            else:
                node_path = node.name if node.name else "?"

            key = (block.id, node.start_line, node.end_line)
            vnode = self._versioned_nodes_by_source.get(key)

            module = ""
            class_name = "-"

            if is_deleted:
                strategy = "Удалён"
            else:
                if block.module_hint is None:
                    if block.assignment_strategy == "AmbiguousMethod":
                        strategy = "Неоднозначный метод"
                    else:
                        strategy = "Не назначен"
                else:
                    strategy = block.assignment_strategy or "Назначен"

            if vnode:
                parent_module = vnode.parent
                while parent_module and parent_module.node_type not in ('module', 'package'):
                    parent_module = parent_module.parent
                if parent_module:
                    module = parent_module.full_path

                parent_class_node = None
                temp = vnode.parent
                while temp:
                    if temp.node_type == 'class':
                        parent_class_node = temp
                        break
                    temp = temp.parent
                if parent_class_node:
                    class_name = parent_class_node.name
            else:
                module = block.module_hint or ""
                class_name = "-"
                if isinstance(node, MethodNode) and node.parent and isinstance(node.parent, ClassNode):
                    class_name = node.parent.name if node.parent.name else "-"
                elif isinstance(node, CodeBlockNode) and node.parent and isinstance(node.parent, ClassNode):
                    class_name = node.parent.name if node.parent.name else "-"

            parent_path = ""
            if isinstance(node, MethodNode) and node.parent and isinstance(node.parent, ClassNode):
                parent_path = node.parent.name or ""
            elif isinstance(node, CodeBlockNode) and node.parent and isinstance(node.parent, ClassNode):
                parent_path = node.parent.name or ""

            flat_items.append(FlatListItem(
                block_id=block.id,
                block_name=block.display_name,
                node_path=node_path,
                parent_path=parent_path,
                lines=f"{node.start_line}-{node.end_line}",
                module=module,
                class_name=class_name,
                strategy=strategy,
                language=block.language
            ))

        for child in node.children:
            self._collect_flat_items_from_code_node(child, block, flat_items, is_root=False, is_deleted=is_deleted)

    # ------------------------------------------------------------------
    # Основные методы загрузки и обновления
    # ------------------------------------------------------------------
    def load_blocks(self, resolved_ambiguities: Optional[Dict[str, str]] = None) -> List[AmbiguityInfo]:
        """
        Загружает блоки. Если есть неоднозначности и resolved_ambiguities=None, возвращает их список.
        При повторном вызове с resolved_ambiguities использует уже загруженные блоки, не перечитывая исходные данные.
        """
        # При первом вызове загружаем блоки из items и сохраняем их
        if not self._initial_blocks:
            BlockRegistry().clear()
            self.block_service.load_from_items(self.items)
            self._initial_blocks = self.block_service.get_new_blocks()
        else:
            # Восстанавливаем реестр из сохранённых блоков (чтобы не терять назначенные module_hint)
            BlockRegistry().clear()
            for block in self._initial_blocks:
                BlockRegistry().register(block)

        # Получаем актуальные блоки (после восстановления реестра)
        all_blocks = self.block_service.get_new_blocks()
        text_blocks_by_pair = self.block_service.get_text_blocks_by_pair()
        full_texts_by_pair = self.block_service.get_full_texts_by_pair()

        builder = VersionedTreeBuilder()
        self._tree_builder_instance = builder

        roots, unknown, candidates = builder.build_from_blocks(
            all_blocks,
            text_blocks_by_pair=text_blocks_by_pair,
            full_texts_by_pair=full_texts_by_pair,
            resolved_ambiguities=resolved_ambiguities
        )
        if candidates:
            return candidates

        # После успешного построения обновляем сохранённые блоки (они могли измениться в процессе)
        updated_blocks = self.block_service.get_new_blocks()
        self._initial_blocks = updated_blocks

        self._versioned_roots = roots
        # Убираем фильтрацию чистых классов – все unknown блоки попадают в диалог
        self._unknown_blocks = unknown
        self._error_blocks = self.block_service.get_error_blocks()
        self._all_code_blocks = [b for b in updated_blocks if b.language in ('python', 'py')]
        self._languages = list(set(b.language for b in self._all_code_blocks))

        logger.info(f"Построено модулей: {len(self._versioned_roots)}, неразрешённых: {len(self._unknown_blocks)}, ошибок: {len(self._error_blocks)}")

        _, _, path_map, source_map = self.tree_builder.build_display_tree(self._versioned_roots, self._current_local_only)
        self._versioned_nodes_by_full_name = path_map
        self._versioned_nodes_by_source = source_map
        self._flat_items = self._build_flat_items_from_all_blocks()
        return []

    def update_block_assignment(self, block_id: str, module_name: Optional[str], strategy: str = "ManualAssignment") -> None:
        block = self.block_service.get_new_block(block_id)
        if not block:
            logger.error(f"Блок {block_id} не найден при обновлении назначения")
            return

        new_block = Block(
            chat=block.chat,
            message_pair=block.message_pair,
            language=block.language,
            content=block.content,
            block_idx=block.block_idx,
            global_index=block.global_index,
            code_tree=block.code_tree,
            module_hint=module_name,
            assignment_strategy=strategy if module_name is not None else None
        )
        BlockRegistry().register(new_block)

        logger.info(f"update_block_assignment: block_id={block_id}, module_name={module_name}, strategy={strategy}, has_code_tree={new_block.code_tree is not None}")

        if self._tree_builder_instance and new_block.code_tree:
            logger.info(f"  Инкрементальное добавление блока в дерево")
            effective_module = module_name if module_name is not None else f"_temp_{block_id}"
            self._tree_builder_instance._collect_from_code_node(
                new_block.code_tree, effective_module, new_block
            )
            self._tree_builder_instance._add_imports_from_block(new_block)
            self._versioned_roots = self._tree_builder_instance._build_versioned_from_identifier()
        else:
            logger.warning(f"  Не удалось инкрементально обновить блок {block_id}, выполняем полную перестройку")
            self.rebuild_structure()
            return

        _, _, path_map, source_map = self.tree_builder.build_display_tree(self._versioned_roots, self._current_local_only)
        self._versioned_nodes_by_full_name = path_map
        self._versioned_nodes_by_source = source_map
        self._flat_items = self._build_flat_items_from_all_blocks()

        self._unknown_blocks = [b for b in self._unknown_blocks if b.id != block_id]
        self._error_blocks = [b for b in self._error_blocks if b.id != block_id]
        self._all_code_blocks = [b for b in self._all_code_blocks if b.id != block_id]

        if new_block.code_tree is not None:
            self._all_code_blocks.append(new_block)
            if new_block.module_hint is None:
                # Всегда добавляем в unknown (без фильтрации чистых классов)
                self._unknown_blocks.append(new_block)
                logger.info(f"  Блок {block_id} добавлен в _unknown_blocks (module_hint=None)")
            else:
                logger.info(f"  Блок {block_id} имеет module_hint={new_block.module_hint}")
        else:
            self._error_blocks.append(new_block)
            logger.info(f"  Блок {block_id} добавлен в _error_blocks (нет code_tree)")

        logger.info(f"  Итого: _unknown_blocks={len(self._unknown_blocks)}, _error_blocks={len(self._error_blocks)}, _all_code_blocks={len(self._all_code_blocks)}")

    def fix_error_block(self, block_id: str, new_code: str):
        block = self.block_service.get_new_block(block_id)
        if not block:
            logger.error(f"Блок {block_id} не найден при исправлении ошибки")
            return

        dedented_code = textwrap.dedent(new_code)

        from code_structure.parsing.core.parser import PythonParser
        parser = PythonParser()
        try:
            temp_block = Block(
                chat=block.chat,
                message_pair=block.message_pair,
                language=block.language,
                content=dedented_code,
                block_idx=block.block_idx,
                global_index=block.global_index,
                code_tree=None,
                module_hint=block.module_hint
            )
            tree = parser.parse(temp_block)
            new_block = Block(
                chat=temp_block.chat,
                message_pair=temp_block.message_pair,
                language=temp_block.language,
                content=temp_block.content,
                block_idx=temp_block.block_idx,
                global_index=temp_block.global_index,
                code_tree=tree,
                module_hint=temp_block.module_hint
            )
        except SyntaxError as e:
            logger.error(f"Исправленный блок {block_id} всё ещё содержит синтаксическую ошибку: {e}")
            return
        except Exception as e:
            logger.error(f"Неожиданная ошибка при парсинге исправленного блока {block_id}: {e}")
            return

        BlockRegistry().register(new_block)
        self.update_block_assignment(block_id, new_block.module_hint, strategy="FixedError")

    def get_initial_data(self) -> CodeStructureInitDTO:
        tree_root, _, _, _ = self.tree_builder.build_display_tree(self._versioned_roots, self._current_local_only)
        active_error_blocks = [b for b in self._error_blocks if b not in self._deleted_blocks]
        has_error_blocks = len(active_error_blocks) > 0
        return CodeStructureInitDTO(
            languages=self._languages,
            tree=tree_root,
            flat_items=self._flat_items,
            has_unknown_blocks=len(self._unknown_blocks) > 0,
            has_error_blocks=has_error_blocks
        )

    def refresh(self, local_only: bool) -> CodeStructureRefreshDTO:
        self._current_local_only = local_only
        tree_root, _, _, _ = self.tree_builder.build_display_tree(self._versioned_roots, local_only)
        self._flat_items = self._build_flat_items_from_all_blocks()
        return CodeStructureRefreshDTO(tree=tree_root, flat_items=self._flat_items)

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

    def _render_versioned_node_code(self, vnode: VersionedNode) -> str:
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

    def get_code_for_block(self, block_id: str) -> Optional[str]:
        block = self.block_service.get_new_block(block_id)
        if block:
            return block.content
        return None

    def get_versioned_roots(self) -> Dict[str, VersionedNode]:
        return self._versioned_roots

    def set_versioned_roots(self, roots: Dict[str, VersionedNode]):
        self._versioned_roots = roots
        _, _, path_map, source_map = self.tree_builder.build_display_tree(self._versioned_roots, self._current_local_only)
        self._versioned_nodes_by_full_name = path_map
        self._versioned_nodes_by_source = source_map
        self._flat_items = self._build_flat_items_from_all_blocks()

    def get_error_blocks(self):
        return [b for b in self._error_blocks if b not in self._deleted_blocks]

    def has_unknown_blocks(self):
        return len(self._unknown_blocks) > 0

    def rebuild_structure(self):
        self.load_blocks()

    def get_unknown_blocks(self) -> List[Block]:
        return self._unknown_blocks.copy()

    def mark_block_as_deleted(self, block_id: str) -> bool:
        block = self.block_service.get_new_block(block_id)
        if not block:
            return False

        self._unknown_blocks = [b for b in self._unknown_blocks if b.id != block_id]
        self._error_blocks = [b for b in self._error_blocks if b.id != block_id]

        if block not in self._deleted_blocks:
            self._deleted_blocks.append(block)

        self._flat_items = self._build_flat_items_from_all_blocks()
        return True