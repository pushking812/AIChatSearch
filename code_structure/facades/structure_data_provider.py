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

        # Внутреннее состояние
        self._versioned_roots: Dict[str, VersionedNode] = {}
        self._versioned_nodes_by_full_name: Dict[str, VersionedNode] = {}
        self._versioned_nodes_by_source: Dict[Tuple[str, int, int], VersionedNode] = {}
        self._all_code_blocks: List[Block] = []
        self._languages: List[str] = []
        self._current_local_only: bool = True
        self._flat_items: List[FlatListItem] = []

    # ------------------------------------------------------------------
    # Построение плоского списка из всех блоков (включая неопределённые и ошибки)
    # ------------------------------------------------------------------
    def _build_flat_items_from_all_blocks(self) -> List[FlatListItem]:
        """Строит плоский список из ВСЕХ блоков, включая неопределённые и с ошибками."""
        flat_items = []

        # 1. Блоки с синтаксическими ошибками (code_tree отсутствует)
        for block in self._error_blocks:
            flat_items.append(FlatListItem(
                block_id=block.id,
                block_name=block.display_name,
                node_path="[Синтаксическая ошибка]",
                parent_path="",
                lines="",
                module="",
                class_name="-",
                strategy="Синтаксическая ошибка"
            ))

        # 2. Все блоки, у которых есть code_tree (включая неопределённые)
        for block in self._all_code_blocks:
            if block.code_tree is None:
                continue
            # Начинаем обход с корневого узла, но сам корень не добавляем в список
            self._collect_flat_items_from_code_node(
                block.code_tree, block, flat_items, is_root=True
            )

        return flat_items

    def _collect_flat_items_from_code_node(
        self,
        node: CodeNode,
        block: Block,
        flat_items: List[FlatListItem],
        is_root: bool = False
    ):
        """
        Рекурсивно обходит CodeNode и добавляет FlatListItem для каждого узла.
        Если is_root=True, то сам узел не добавляется (пропускается корневой контейнер).
        """
        if not is_root:
            # Определяем отображаемое имя узла
            if isinstance(node, ImportNode):
                node_path = node.statement
            elif isinstance(node, CommentNode):
                node_path = node.text
            elif isinstance(node, CodeBlockNode):
                node_path = "блок кода"
            elif isinstance(node, (FunctionNode, MethodNode, ClassNode)):
                node_path = node.name if node.name else "?"
            else:
                node_path = node.name if node.name else "?"

            # Ищем VersionedNode по источнику (block_id, start_line, end_line)
            key = (block.id, node.start_line, node.end_line)
            vnode = self._versioned_nodes_by_source.get(key)

            # Логирование для отладки назначения класса
            self._log_node_class_assignment(node, block, key, vnode)

            if vnode:
                # Узел привязан к версионированному дереву – берём данные из него
                module = ""
                class_name = "-"
                # Ищем родительский модуль
                parent_module = vnode.parent
                while parent_module and parent_module.node_type not in ('module', 'package'):
                    parent_module = parent_module.parent
                if parent_module:
                    module = parent_module.full_path

                # Для методов и блоков кода внутри класса – ищем класс-родитель
                if vnode.node_type == 'method':
                    parent_class_node = vnode.parent
                    while parent_class_node and parent_class_node.node_type != 'class':
                        parent_class_node = parent_class_node.parent
                    if parent_class_node:
                        class_name = parent_class_node.name
                    else:
                        logger.debug(
                            f"Метод {node.name} (vnode {vnode.full_path}) не нашёл родительский класс. "
                            f"Родитель vnode: {vnode.parent} (тип={getattr(vnode.parent, 'node_type', None)})"
                        )
                elif vnode.node_type == 'code_block':
                    parent_class_node = vnode.parent
                    while parent_class_node and parent_class_node.node_type != 'class':
                        parent_class_node = parent_class_node.parent
                    if parent_class_node:
                        class_name = parent_class_node.name
                elif vnode.node_type == 'function':
                    # Функции не имеют класса
                    class_name = "-"
                else:
                    # Для классов, модулей и т.д.
                    class_name = "-"

                strategy = block.assignment_strategy or ""
            else:
                # Узел не привязан – используем информацию из блока и CodeNode
                module = block.module_hint or ""
                class_name = "-"
                # Если узел метод и внутри блока есть класс-родитель (из CodeNode)
                if isinstance(node, MethodNode) and node.parent and isinstance(node.parent, ClassNode):
                    class_name = node.parent.name if node.parent.name else "-"
                elif isinstance(node, CodeBlockNode) and node.parent and isinstance(node.parent, ClassNode):
                    class_name = node.parent.name if node.parent.name else "-"
                strategy = block.assignment_strategy or "Не назначен"

                logger.debug(
                    f"Узел {node_path} (тип {type(node).__name__}) не привязан к VersionedNode. "
                    f"module_hint={block.module_hint}, class_name={class_name}"
                )

            # Формируем строку "Родитель" (для колонки Parent)
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
                strategy=strategy
            ))

        # Рекурсивный обход детей (никогда не пропускаем детей, даже для корня)
        for child in node.children:
            self._collect_flat_items_from_code_node(child, block, flat_items, is_root=False)

    def _log_node_class_assignment(
        self,
        node: CodeNode,
        block: Block,
        key: Tuple[str, int, int],
        vnode: Optional[VersionedNode]
    ):
        """Логирует процесс определения класса для узла."""
        # Логируем только если узел является методом или блоком кода (потенциально внутри класса)
        if not isinstance(node, (MethodNode, CodeBlockNode)):
            return

        node_type_name = type(node).__name__
        node_name = getattr(node, 'name', '?')
        logger.debug(
            f"Обработка узла {node_name} (тип {node_type_name}) из блока {block.id} "
            f"строки {node.start_line}-{node.end_line}"
        )

        if vnode is None:
            logger.debug(
                f"  -> VersionedNode не найден по ключу {key}. "
                f"Будет использован CodeNode.parent (класс: {getattr(node.parent, 'name', None) if isinstance(node.parent, ClassNode) else 'нет'})"
            )
            return

        logger.debug(
            f"  -> Найден VersionedNode: {vnode.full_path}, тип={vnode.node_type}, "
            f"родитель={vnode.parent.full_path if vnode.parent else 'None'}"
        )

        # Проверяем, почему класс не определяется
        if vnode.node_type == 'method':
            parent_class = None
            temp = vnode.parent
            while temp:
                if temp.node_type == 'class':
                    parent_class = temp
                    break
                temp = temp.parent
            if parent_class:
                logger.debug(f"  -> Найден родительский класс для метода: {parent_class.name}")
            else:
                logger.warning(
                    f"  !!! Метод {node_name} (vnode {vnode.full_path}) НЕ имеет родительского класса в VersionedNode. "
                    f"Цепочка родителей: {self._get_parent_chain(vnode)}"
                )
        elif vnode.node_type == 'code_block':
            parent_class = None
            temp = vnode.parent
            while temp:
                if temp.node_type == 'class':
                    parent_class = temp
                    break
                temp = temp.parent
            if parent_class:
                logger.debug(f"  -> Найден родительский класс для блока кода: {parent_class.name}")
            else:
                logger.warning(
                    f"  !!! Блок кода (vnode {vnode.full_path}) НЕ имеет родительского класса. "
                    f"Цепочка родителей: {self._get_parent_chain(vnode)}"
                )
        else:
            logger.debug(f"  -> Узел типа {vnode.node_type} не является методом или блоком кода, класс не ищется")

    def _get_parent_chain(self, vnode: VersionedNode) -> str:
        """Возвращает строку с цепочкой родителей для отладки."""
        parts = []
        current = vnode
        while current:
            parts.append(f"{current.name} ({current.node_type})")
            current = current.parent
        return " -> ".join(parts)

    # ------------------------------------------------------------------
    # Основные методы загрузки и обновления структуры
    # ------------------------------------------------------------------
    def load_blocks(self) -> None:
        self.block_service.load_from_items(self.items)
        all_blocks = self.block_service.get_new_blocks()
        
        text_blocks_by_pair = self.block_service.get_text_blocks_by_pair()
        full_texts_by_pair = self.block_service.get_full_texts_by_pair()

        builder = VersionedTreeBuilder()
        self._versioned_roots, unknown = builder.build_from_blocks(
            all_blocks,
            text_blocks_by_pair=text_blocks_by_pair,
            full_texts_by_pair=full_texts_by_pair
        )
        self._unknown_blocks = unknown
        self._error_blocks = self.block_service.get_error_blocks()

        # После построения дерева обновляем список блоков (внутри builder могли создаваться новые блоки)
        all_blocks = self.block_service.get_new_blocks()
        self._all_code_blocks = [b for b in all_blocks if b.language in ('python', 'py')]
        self._languages = list(set(b.language for b in self._all_code_blocks))

        logger.info(f"Построено модулей: {len(self._versioned_roots)}, неразрешённых: {len(unknown)}, ошибок: {len(self._error_blocks)}")

        # Построение DTO и плоского списка
        _, _, path_map, source_map = self.tree_builder.build_display_tree(self._versioned_roots, self._current_local_only)
        self._versioned_nodes_by_full_name = path_map
        self._versioned_nodes_by_source = source_map
        self._flat_items = self._build_flat_items_from_all_blocks()

    def get_initial_data(self) -> CodeStructureInitDTO:
        tree_root, _, _, _ = self.tree_builder.build_display_tree(self._versioned_roots, self._current_local_only)
        return CodeStructureInitDTO(
            languages=self._languages,
            tree=tree_root,
            flat_items=self._flat_items,
            has_unknown_blocks=len(self._unknown_blocks) > 0
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
        # Перестраиваем карты для быстрого доступа
        _, _, path_map, source_map = self.tree_builder.build_display_tree(self._versioned_roots, self._current_local_only)
        self._versioned_nodes_by_full_name = path_map
        self._versioned_nodes_by_source = source_map
        self._flat_items = self._build_flat_items_from_all_blocks()
        
    def get_error_blocks(self):
        return self._error_blocks

    def has_unknown_blocks(self):
        return len(self._unknown_blocks) > 0

    def fix_error_block(self, block_id: str, new_code: str):
        block = self.block_service.get_new_block(block_id)
        if not block:
            return
        new_block = Block(
            id=block.id,
            chat=block.chat,
            message_pair=block.message_pair,
            language=block.language,
            content=new_code,
            block_idx=block.block_idx,
            global_index=block.global_index,
            code_tree=None,
            module_hint=block.module_hint
        )
        from code_structure.parsing.core.parser import PythonParser
        parser = PythonParser()
        try:
            tree = parser.parse(new_block)
            new_block = Block(
                chat=new_block.chat,
                message_pair=new_block.message_pair,
                language=new_block.language,
                content=new_block.content,
                block_idx=new_block.block_idx,
                global_index=new_block.global_index,
                code_tree=tree,
                module_hint=new_block.module_hint
            )
        except SyntaxError:
            logger.error(f"Исправленный блок {block_id} всё ещё содержит ошибку")
            return
        BlockRegistry().register(new_block)
        self.rebuild_structure()

    def rebuild_structure(self):
        self.load_blocks()