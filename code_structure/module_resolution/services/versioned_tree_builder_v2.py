# code_structure/module_resolution/services/versioned_tree_builder_v2.py

import re
import logging
from typing import List, Dict, Optional, Tuple

from code_structure.models.block import Block
from code_structure.models.code_node import (
    CodeNode, ClassNode, FunctionNode, MethodNode, CodeBlockNode, ImportNode
)
from code_structure.models.versioned_node import (
    VersionedNode, VersionedModule, VersionedClass, VersionedFunction,
    VersionedMethod, VersionedCodeBlock, VersionedImport, SourceRef, VersionInfo
)
from code_structure.models.registry import BlockRegistry
from code_structure.module_resolution.core.identifier_tree import IdentifierTree
from code_structure.imports.models.import_models import ImportInfo
from code_structure.imports.core.import_analyzer import extract_imports_from_block
from code_structure.utils.helpers import extract_module_hint, clean_code
from code_structure.utils.logger import get_logger

logger = get_logger(__name__, level=logging.DEBUG)


class VersionedTreeBuilderV2:
    def __init__(self):
        self.identifier_tree = IdentifierTree()
        self._version_map: Dict[str, List[VersionInfo]] = {}
        self._node_type_map: Dict[str, str] = {}
        self.text_blocks_by_pair: Dict[str, Dict[int, str]] = {}
        self.full_texts_by_pair: Dict[str, str] = {}
        self._block_imports: Dict[str, List[ImportInfo]] = {}

    def build_from_blocks(
        self,
        blocks: List[Block],
        text_blocks_by_pair: Dict[str, Dict[int, str]] = None,
        full_texts_by_pair: Dict[str, str] = None
    ) -> Tuple[Dict[str, VersionedNode], List[Block]]:
        self.text_blocks_by_pair = text_blocks_by_pair or {}
        self.full_texts_by_pair = full_texts_by_pair or {}

        self._assign_from_comments(blocks)
        self._preprocess_classes(blocks)
        self._apply_text_hints(blocks)
        unknown_blocks = self._resolve_with_tree(blocks)

        # Финальный сбор всех блоков с module_hint (на случай, если какие-то ещё не были проиндексированы)
        self._collect_all_blocks(blocks)

        roots = self._build_versioned_from_identifier()
        return roots, unknown_blocks

    # ---------- Назначение из комментариев ----------
    def _assign_from_comments(self, blocks: List[Block]):
        for block in blocks:
            if block.module_hint is None:
                hint = extract_module_hint(block)
                if hint:
                    new_block = Block(
                        chat=block.chat,
                        message_pair=block.message_pair,
                        language=block.language,
                        content=block.content,
                        block_idx=block.block_idx,
                        global_index=block.global_index,
                        code_tree=block.code_tree,
                        module_hint=hint,
                        assignment_strategy="CommentHint"
                    )
                    BlockRegistry().register(new_block)
                    idx = blocks.index(block)
                    blocks[idx] = new_block
                    if new_block.code_tree:
                        self._collect_from_block(new_block)
                        self._process_imports_from_block(new_block)

    # ---------- Предобработка классов ----------
    def _preprocess_classes(self, blocks: List[Block]):
        for block in blocks:
            if block.module_hint is None:
                continue
            if not block.code_tree:
                continue
            classes = self._extract_class_names(block.code_tree)
            if classes:
                self._collect_from_block(block)

    # ---------- Текстовые подсказки ----------
    def _apply_text_hints(self, blocks: List[Block]):
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
            module = self.identifier_tree.find_module_for_name(class_name)
            if not module:
                module = self._find_imported_class(class_name)
            if module:
                logger.info(f"Текстовая подсказка: класс {class_name} -> модуль {module} для блока {block.display_name}")
                new_block = Block(
                    chat=block.chat,
                    message_pair=block.message_pair,
                    language=block.language,
                    content=block.content,
                    block_idx=block.block_idx,
                    global_index=block.global_index,
                    code_tree=block.code_tree,
                    module_hint=module,
                    assignment_strategy="TextHint"
                )
                BlockRegistry().register(new_block)
                idx = blocks.index(block)
                blocks[idx] = new_block
                if new_block.code_tree:
                    self._collect_from_block(new_block)
                    self._process_imports_from_block(new_block)

    # ---------- Разрешение через дерево ----------
    def _resolve_with_tree(self, blocks: List[Block]) -> List[Block]:
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
                module = self._resolve_block_with_tree(block)
                if module:
                    new_block = Block(
                        chat=block.chat,
                        message_pair=block.message_pair,
                        language=block.language,
                        content=block.content,
                        block_idx=block.block_idx,
                        global_index=block.global_index,
                        code_tree=block.code_tree,
                        module_hint=module,
                        assignment_strategy="TreeResolution"
                    )
                    BlockRegistry().register(new_block)
                    unknown.remove(block)
                    unknown.append(new_block)
                    if new_block.code_tree:
                        self._collect_from_block(new_block)
                        self._process_imports_from_block(new_block)
                        self._process_relative_imports_for_block(new_block)
                    changed = True
            unknown = [b for b in unknown if b.module_hint is None]
            iteration += 1
            if iteration > 20:
                break
        return unknown

    def _resolve_block_with_tree(self, block: Block) -> Optional[str]:
        if not block.code_tree:
            return None
        classes = self._extract_class_names(block.code_tree)
        functions = self._extract_function_names(block.code_tree)
        if not classes and not functions:
            return None
        candidates = set()
        for name in classes:
            module = self.identifier_tree.find_module_for_name(name)
            if module:
                candidates.add(module)
        for name in functions:
            module = self.identifier_tree.find_module_for_name(name)
            if module:
                candidates.add(module)
        if len(candidates) == 1:
            return next(iter(candidates))
        return None

    # ---------- Сбор данных из блока ----------
    def _collect_all_blocks(self, blocks: List[Block]):
        for block in blocks:
            if block.module_hint and block.code_tree:
                self._collect_from_block(block)
                self._process_imports_from_block(block)

    def _collect_from_block(self, block: Block):
        module_path = block.module_hint
        self.identifier_tree.add_path(module_path)
        self._collect_from_code_node(block.code_tree, module_path, block)

    # ---------- Сбор из CodeNode ----------
    def _collect_from_code_node(self, code_node: CodeNode, current_path: str, block: Block):
        for child in code_node.children:
            if isinstance(child, ClassNode):
                full_path = f"{current_path}.{child.name}"
                self.identifier_tree.add_path(full_path)
                self._node_type_map[full_path] = 'class'
                self._add_version(full_path, child, block)
                self._collect_from_code_node(child, full_path, block)
            elif isinstance(child, MethodNode):
                if child.parent and isinstance(child.parent, ClassNode):
                    full_path = f"{current_path}.{child.name}"
                    self.identifier_tree.add_path(full_path)
                    self._node_type_map[full_path] = 'method'
                    self._add_version(full_path, child, block)
            elif isinstance(child, FunctionNode) and not isinstance(child, MethodNode):
                full_path = f"{current_path}.{child.name}"
                self.identifier_tree.add_path(full_path)
                self._node_type_map[full_path] = 'function'
                self._add_version(full_path, child, block)
            elif isinstance(child, CodeBlockNode):
                full_path = f"{current_path}._code_block"
                self.identifier_tree.add_path(full_path)
                self._node_type_map[full_path] = 'code_block'
                self._add_version(full_path, child, block)
            elif isinstance(child, ImportNode):
                safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', child.statement[:50])
                full_path = f"{current_path}._import_{safe_name}"
                self._node_type_map[full_path] = 'import'
                self._add_version(full_path, child, block)
                # Импорт также добавляем в дерево идентификаторов (целевой путь)
                imports = extract_imports_from_block(child.statement, current_path)
                for imp in imports:
                    self.identifier_tree.add_path(imp.target_fullname)
            else:
                self._collect_from_code_node(child, current_path, block)

    def _add_version(self, path: str, code_node: CodeNode, block: Block):
        norm = clean_code(code_node.get_raw_code())
        src = SourceRef(block.id, code_node.start_line, code_node.end_line, block.timestamp)
        versions = self._version_map.setdefault(path, [])
        for ver in versions:
            if ver.normalized_code == norm:
                ver.add_source(src)
                return
        versions.append(VersionInfo(norm, [src]))

    # ---------- Обработка импортов ----------
    def _process_imports_from_block(self, block: Block):
        if not block.module_hint or not block.code_tree:
            return
        imports = extract_imports_from_block(block.content, block.module_hint)
        self._block_imports[block.id] = imports
        for imp in imports:
            self.identifier_tree.add_path(imp.target_fullname)

    def _process_relative_imports_for_block(self, block: Block):
        if block.id not in self._block_imports:
            return
        imports = self._block_imports[block.id]
        for imp in imports:
            if imp.is_relative:
                self.identifier_tree.add_path(imp.target_fullname)
                logger.debug(f"Добавлен относительный импорт в дерево: {imp.target_fullname}")

    def _find_imported_class(self, class_name: str) -> Optional[str]:
        return self.identifier_tree.find_module_for_name(class_name)

    # ---------- Построение дерева VersionedNode ----------
    def _build_versioned_from_identifier(self) -> Dict[str, VersionedNode]:
        all_nodes: Dict[str, VersionedNode] = {}
        self._build_nodes_recursive(self.identifier_tree.root, "", all_nodes)
        for path, versions in self._version_map.items():
            node = all_nodes.get(path)
            if node:
                node.versions = versions
            else:
                logger.warning(f"Версии для пути {path}, но узел не найден в дереве")
        roots = {path: node for path, node in all_nodes.items() if node.parent is None}
        return roots

    def _build_nodes_recursive(self, tree_node, current_path: str, all_nodes: Dict[str, VersionedNode]):
        if tree_node.name:
            if current_path:
                full_path = f"{current_path}.{tree_node.name}"
            else:
                full_path = tree_node.name

            node_type = self._node_type_map.get(full_path)
            if node_type is None:
                node_type = "package" if tree_node.children else "module"

            node = self._create_versioned_node(tree_node.name, node_type)
            all_nodes[full_path] = node
            if current_path and current_path in all_nodes:
                parent = all_nodes[current_path]
                parent.add_child(node)
        else:
            full_path = current_path

        for child in tree_node.children.values():
            self._build_nodes_recursive(child, full_path, all_nodes)

    def _create_versioned_node(self, name: str, node_type: str) -> VersionedNode:
        if node_type == 'class':
            return VersionedClass(name)
        elif node_type == 'function':
            return VersionedFunction(name)
        elif node_type == 'method':
            return VersionedMethod(name)
        elif node_type == 'code_block':
            return VersionedCodeBlock(name)
        elif node_type == 'import':
            return VersionedImport(name)
        elif node_type == 'module':
            return VersionedModule(name)
        else:
            return VersionedNode(name, node_type)

    # ---------- Вспомогательные ----------
    def _extract_class_names(self, code_node: CodeNode) -> set:
        classes = set()
        if isinstance(code_node, ClassNode):
            classes.add(code_node.name)
        for child in code_node.children:
            classes.update(self._extract_class_names(child))
        return classes

    def _extract_function_names(self, code_node: CodeNode) -> set:
        functions = set()
        if isinstance(code_node, FunctionNode) and not isinstance(code_node, MethodNode):
            functions.add(code_node.name)
        for child in code_node.children:
            functions.update(self._extract_function_names(child))
        return functions