# code_structure/module_resolution/services/versioned_tree_builder.py

import re
import logging
from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict

from code_structure.models.block import Block
from code_structure.models.code_node import CodeNode, ClassNode, FunctionNode, MethodNode, CodeBlockNode, ImportNode
from code_structure.models.versioned_node import (
    VersionedNode, VersionedModule, VersionedClass, VersionedFunction,
    VersionedMethod, VersionedCodeBlock, VersionedImport, SourceRef, VersionInfo
)
from code_structure.models.converters import code_node_to_old_node, block_to_old_block_info
from code_structure.models.registry import BlockRegistry
from code_structure.module_resolution.core.new_resolution_strategies import (
    ClassStrategy, MethodStrategy, FunctionStrategy, ImportStrategy
)
from code_structure.module_resolution.core.module_identifier import ModuleIdentifier
from code_structure.utils.helpers import extract_module_hint
from code_structure.utils.logger import get_logger

logger = get_logger(__name__)


class VersionedTreeBuilder:
    def __init__(self):
        self.module_identifier = ModuleIdentifier()
        self.strategies = [
            ClassStrategy(),
            MethodStrategy(),
            FunctionStrategy(),
            ImportStrategy()
        ]
        self.text_blocks_by_pair: Dict[str, Dict[int, str]] = {}
        self.full_texts_by_pair: Dict[str, str] = {}

    def build_from_blocks(
        self,
        blocks: List[Block],
        text_blocks_by_pair: Dict[str, Dict[int, str]] = None,
        full_texts_by_pair: Dict[str, str] = None
    ) -> Tuple[Dict[str, VersionedNode], List[Block]]:
        """Строит дерево версионированных модулей из блоков."""
        self.text_blocks_by_pair = text_blocks_by_pair or {}
        self.full_texts_by_pair = full_texts_by_pair or {}

        # 1. Назначение из комментариев
        self._assign_from_comments(blocks)

        # 2. Текстовые подсказки
        self._apply_text_hints(blocks)

        # 3. Итеративное разрешение
        unknown_blocks = self._resolve_iteratively(blocks)

        # 4. Построение дерева VersionedNode
        versioned_roots = self._build_versioned_from_identifier()

        return versioned_roots, unknown_blocks

    def _assign_from_comments(self, blocks: List[Block]):
        """Назначает module_hint блокам, у которых есть комментарий-подсказка."""
        for block in blocks:
            if block.module_hint is None:
                hint = extract_module_hint(block)
                if hint:
                    new_block = Block(
                        id=block.id,
                        chat=block.chat,
                        message_pair=block.message_pair,
                        language=block.language,
                        content=block.content,
                        block_idx=block.block_idx,
                        global_index=block.global_index,
                        code_tree=block.code_tree,
                        module_hint=hint
                    )
                    BlockRegistry().register(new_block)
                    # Заменяем в списке
                    idx = blocks.index(block)
                    blocks[idx] = new_block
                    if new_block.code_tree:
                        self._collect_from_code_node(new_block.code_tree, hint, new_block)
                        self._add_imports_from_block(new_block)
                    logger.debug(f"Блоку {new_block.id} назначен модуль {hint} по комментарию")

    def _apply_text_hints(self, blocks: List[Block]):
        """Применяет текстовые подсказки из предыдущих текстовых блоков."""
        if not self.text_blocks_by_pair:
            return
        for block in blocks:
            if block.module_hint is not None:
                continue
            if not block.code_tree:
                continue
            pair_index = block.pair_index
            if pair_index not in self.text_blocks_by_pair:
                continue
            text_blocks = self.text_blocks_by_pair[pair_index]
            # Ищем ближайший текстовый блок с меньшим индексом
            prev_text_idx = None
            for idx in text_blocks:
                if idx < block.block_idx:
                    if prev_text_idx is None or idx > prev_text_idx:
                        prev_text_idx = idx
            if prev_text_idx is None:
                continue
            text = text_blocks[prev_text_idx]
            class_match = re.search(
                r'(?:в\s+)?класс[еауы]?\s+(?:`|\'|")?([A-Za-z_][A-Za-z0-9_]*)(?:`|\'|")?',
                text, re.IGNORECASE
            )
            if not class_match:
                continue
            class_name = class_match.group(1)
            module = self.module_identifier.find_module_for_class(class_name)
            if not module:
                module = self.module_identifier.find_imported_class(class_name)
            if module:
                logger.debug(f"Текстовая подсказка: класс {class_name} -> модуль {module} для блока {block.id}")
                new_block = Block(
                    id=block.id,
                    chat=block.chat,
                    message_pair=block.message_pair,
                    language=block.language,
                    content=block.content,
                    block_idx=block.block_idx,
                    global_index=block.global_index,
                    code_tree=block.code_tree,
                    module_hint=module
                )
                BlockRegistry().register(new_block)
                idx = blocks.index(block)
                blocks[idx] = new_block
                if new_block.code_tree:
                    self._collect_from_code_node(new_block.code_tree, module, new_block)
                    self._add_imports_from_block(new_block)

    def _resolve_iteratively(self, blocks: List[Block]) -> List[Block]:
        """Итеративно разрешает модули для блоков, у которых ещё нет hint."""
        unknown = [b for b in blocks if b.module_hint is None]
        changed = True
        iteration = 0
        while changed and unknown:
            changed = False
            for block in unknown[:]:
                if block.module_hint is not None:
                    unknown.remove(block)
                    continue
                if block.code_tree is None:
                    continue
                module = self._resolve_block(block)
                if module:
                    new_block = Block(
                        id=block.id,
                        chat=block.chat,
                        message_pair=block.message_pair,
                        language=block.language,
                        content=block.content,
                        block_idx=block.block_idx,
                        global_index=block.global_index,
                        code_tree=block.code_tree,
                        module_hint=module
                    )
                    BlockRegistry().register(new_block)
                    unknown.remove(block)
                    unknown.append(new_block)
                    if new_block.code_tree:
                        self._collect_from_code_node(new_block.code_tree, module, new_block)
                        self._add_imports_from_block(new_block)
                    changed = True
                    logger.debug(f"Блок {block.id} разрешён как {module} на итерации {iteration}")
            unknown = [b for b in unknown if b.module_hint is None]
            iteration += 1
            if iteration > 20:
                break
        return unknown

    def _resolve_block(self, block: Block) -> Optional[str]:
        """Применяет стратегии для определения module_hint блока."""
        if not block.code_tree:
            return None
        context = {'identifier': self.module_identifier}
        for strategy in self.strategies:
            module = strategy.resolve(block.code_tree, context)
            if module:
                return module
        return None

    def _collect_from_code_node(self, code_node: CodeNode, module_name: str, block: Block):
        """Преобразует CodeNode в старый Node и добавляет в ModuleIdentifier."""
        if code_node is None:
            return
        old_node = code_node_to_old_node(code_node)
        old_block_info = block_to_old_block_info(block)
        self.module_identifier.collect_from_tree(old_node, module_name, block_info=old_block_info)

    def _add_imports_from_block(self, block: Block):
        """Извлекает импорты из блока и добавляет их в ModuleIdentifier."""
        if not block.code_tree or not block.module_hint:
            return
        from code_structure.imports.core.import_analyzer import extract_imports_from_block
        imports = extract_imports_from_block(block.content, block.module_hint)
        for imp in imports:
            self.module_identifier.add_imported_item(block.module_hint, imp)

    def _build_versioned_from_identifier(self) -> Dict[str, VersionedNode]:
        all_nodes = {}

        for mod_name in self.module_identifier.get_all_module_names():
            module_info = self.module_identifier.get_module_info(mod_name)
            if not module_info:
                continue

            parts = mod_name.split('.')
            parent = None
            current_path_parts = []
            for i, part in enumerate(parts):
                current_path = '.'.join(current_path_parts + [part])
                if current_path not in all_nodes:
                    if i == len(parts) - 1:
                        node = VersionedModule(part)
                        node.is_imported = module_info.is_imported
                    else:
                        node = VersionedNode(part, "package")
                    all_nodes[current_path] = node
                    if parent:
                        parent.add_child(node)
                        logger.debug(f"    {current_path} добавлен как ребёнок {parent.full_path}")
                parent = all_nodes[current_path]
                current_path_parts.append(part)

            module_node = all_nodes[mod_name]

            # Если узел ещё не является модулем, преобразуем его в модуль
            if not isinstance(module_node, VersionedModule):
                module_node.node_type = "module"
                # Добавляем атрибут is_imported (для совместимости с фильтром)
                module_node.is_imported = module_info.is_imported
                # Убеждаемся, что он остался тем же объектом – дети и родитель сохраняются
                logger.debug(f"    Преобразован {mod_name} в модуль (был пакетом)")

            # Классы
            for class_name, class_info in module_info.classes.items():
                class_full_name = f"{mod_name}.{class_name}"
                if class_full_name in all_nodes:
                    vclass = all_nodes[class_full_name]
                else:
                    vclass = VersionedClass(class_name)
                    all_nodes[class_full_name] = vclass
                    module_node.add_child(vclass)

                for method_name, method_info in class_info.methods.items():
                    method_full_name = f"{class_full_name}.{method_name}"
                    if method_full_name in all_nodes:
                        vmethod = all_nodes[method_full_name]
                    else:
                        vmethod = VersionedMethod(method_name)
                        all_nodes[method_full_name] = vmethod
                        vclass.add_child(vmethod)
                    for old_version in method_info.versions:
                        version_info = self._old_version_to_version_info(old_version)
                        if version_info:
                            vmethod.versions.append(version_info)

            # Функции
            for func_name, func_info in module_info.functions.items():
                func_full_name = f"{mod_name}.{func_name}"
                if func_full_name in all_nodes:
                    vfunc = all_nodes[func_full_name]
                else:
                    vfunc = VersionedFunction(func_name)
                    all_nodes[func_full_name] = vfunc
                    module_node.add_child(vfunc)
                for old_version in func_info.versions:
                    version_info = self._old_version_to_version_info(old_version)
                    if version_info:
                        vfunc.versions.append(version_info)

        # Отладочный вывод
        if 'deepseek' in all_nodes:
            node = all_nodes['deepseek']
            logger.debug(f"deepseek parent: {node.parent}")
            if node.parent:
                logger.debug(f"  родитель: {node.parent.full_path} (type={node.parent.node_type})")
        else:
            logger.debug("deepseek не найден в all_nodes")

        logger.debug(f"Все узлы: {list(all_nodes.keys())}")
        roots = {full_name: node for full_name, node in all_nodes.items() if node.parent is None}
        logger.debug(f"Корневые узлы: {list(roots.keys())}")
        return roots

    def _old_version_to_version_info(self, old_version) -> Optional[VersionInfo]:
        """Преобразует старый Version (из ModuleIdentifier) в VersionInfo."""
        if not old_version.sources:
            return None
        sources = []
        for src in old_version.sources:
            block_id, start, end, _ = src
            block = BlockRegistry().get(block_id)
            timestamp = block.timestamp if block else 0.0
            sources.append(SourceRef(block_id, start, end, timestamp))
        return VersionInfo(normalized_code=old_version.cleaned_content, sources=sources)