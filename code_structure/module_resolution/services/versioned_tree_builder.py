# code_structure/module_resolution/services/versioned_tree_builder.py

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
from code_structure.module_resolution.core.module_identifier import ModuleIdentifier
from code_structure.module_resolution.core.identifier_tree import IdentifierTree
from code_structure.imports.models.import_models import ImportInfo
from code_structure.parsing.core.signature_utils import extract_function_signature as extract_function_signature_from_code_node
from code_structure.utils.helpers import extract_module_hint
from code_structure.utils.logger import get_logger

logger = get_logger(__name__, level=logging.DEBUG)


class VersionedTreeBuilder:
    def __init__(self):
        self.module_identifier = ModuleIdentifier()
        self.text_blocks_by_pair: Dict[str, Dict[int, str]] = {}
        self.full_texts_by_pair: Dict[str, str] = {}
        self.identifier_tree = IdentifierTree()
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

        self._collect_absolute_imports_to_tree()

        versioned_roots = self._build_versioned_from_identifier()
        return versioned_roots, unknown_blocks

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
                        self._collect_from_code_node(new_block.code_tree, hint, new_block)
                        self._add_imports_from_block(new_block)
                        self._add_definitions_from_block(new_block)

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
            logger.debug(f"Text hint found: class {class_name}")
            module = self.module_identifier.find_module_for_class(class_name)
            if not module:
                module = self.module_identifier.find_imported_class(class_name)
                logger.debug(f"find_imported_class for {class_name} -> {module}")
            if not module:
                logger.warning(f"Class {class_name} not found in modules or imports for block {block.display_name}")
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
                    self._collect_from_code_node(new_block.code_tree, module, new_block, class_hint=class_name)
                    self._add_imports_from_block(new_block)
                    self._add_definitions_from_block(new_block)

    # ---------- Разрешение с помощью дерева ----------
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
                        self._collect_from_code_node(new_block.code_tree, module, new_block)
                        self._add_imports_from_block(new_block)
                        self._add_definitions_from_block(new_block)
                        self._process_relative_imports_for_block(new_block)
                    changed = True
            unknown = [b for b in unknown if b.module_hint is None]
            iteration += 1
            if iteration > 20:
                break
        return unknown

    def _resolve_block_with_tree(self, block: Block) -> Optional[str]:
        """Разрешает блок с помощью дерева идентификаторов. Возвращает модуль или None."""
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

    # ---------- Предобработка классов ----------
    def _preprocess_classes(self, blocks: List[Block]):
        for block in blocks:
            if block.module_hint is None:
                continue
            if not block.code_tree:
                continue
            classes = self._extract_class_names(block.code_tree)
            if classes:
                self._collect_from_code_node(block.code_tree, block.module_hint, block)

    # ---------- Добавление в ModuleIdentifier ----------
    def _collect_from_code_node(self, code_node: CodeNode, module_name: str, block: Block, class_hint: Optional[str] = None):
        if code_node is None:
            return

        if class_hint is None and isinstance(code_node, FunctionNode) and not isinstance(code_node, MethodNode):
            has_self, _ = extract_function_signature_from_code_node(code_node)
            if has_self:
                possible_class_name = module_name.split('.')[-1].capitalize()
                module_info = self.module_identifier.get_module_info(module_name)
                if module_info and possible_class_name in module_info.classes:
                    class_hint = possible_class_name

        self.module_identifier.collect_from_code_node(code_node, block, module_name, class_hint)
        if isinstance(code_node, ImportNode):
            version_info = self._create_version_info_from_code_node(code_node, block)
            if version_info:
                self.module_identifier.add_import_version(module_name, version_info)
        elif isinstance(code_node, CodeBlockNode):
            parent = code_node.parent
            if parent is None or parent.node_type in ('module', 'package'):
                version_info = self._create_version_info_from_code_node(code_node, block)
                if version_info:
                    self.module_identifier.add_code_block_version(module_name, version_info)
            elif isinstance(parent, ClassNode):
                version_info = self._create_version_info_from_code_node(code_node, block)
                if version_info:
                    self._add_code_block_to_class(module_name, parent.name, version_info)

        for child in code_node.children:
            self._collect_from_code_node(child, module_name, block, class_hint)

    def _create_version_info_from_code_node(self, code_node: CodeNode, block: Block) -> Optional[VersionInfo]:
        norm = code_node.normalized_content()
        src = SourceRef(block.id, code_node.start_line, code_node.end_line, block.timestamp)
        return VersionInfo(norm, [src])

    def _add_code_block_to_class(self, module_name: str, class_name: str, version_info: VersionInfo):
        module = self.module_identifier.get_module_info(module_name)
        if not module:
            return
        class_info = module.classes.get(class_name)
        if not class_info:
            return
        class_info.code_block_versions.append(version_info)

    def _add_imports_from_block(self, block: Block):
        if not block.code_tree or not block.module_hint:
            return
        from code_structure.imports.core.import_analyzer import extract_imports_from_block
        imports = extract_imports_from_block(block.content, block.module_hint)
        self._block_imports[block.id] = imports
        for imp in imports:
            self.module_identifier.add_imported_item(block.module_hint, imp)

    def _process_relative_imports_for_block(self, block: Block):
        if block.id not in self._block_imports:
            return
        imports = self._block_imports[block.id]
        for imp in imports:
            if imp.is_relative:
                self.identifier_tree.add_path(imp.target_fullname)
                logger.debug(f"Добавлен относительный импорт в дерево: {imp.target_fullname}")

    # ---------- Построение дерева VersionedNode ----------
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
                if part is None:
                    part = "?"
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
                parent = all_nodes[current_path]
                current_path_parts.append(part)

            module_node = all_nodes[mod_name]
            if not isinstance(module_node, VersionedModule):
                module_node.node_type = "module"
                module_node.is_imported = module_info.is_imported

            # 1. Импорты (один узел)
            if module_info.import_versions:
                vimports = VersionedImport("imports")
                for v in module_info.import_versions:
                    vimports.versions.append(v)
                module_node.add_child(vimports)

            # 2. Классы и методы
            method_names = set()
            for class_name, class_info in module_info.classes.items():
                if class_name is None:
                    continue
                class_full_name = f"{mod_name}.{class_name}"
                if class_full_name in all_nodes:
                    vclass = all_nodes[class_full_name]
                else:
                    vclass = VersionedClass(class_name)
                    all_nodes[class_full_name] = vclass
                    module_node.add_child(vclass)

                # Блоки кода внутри класса
                for v in class_info.code_block_versions:
                    vblock = VersionedCodeBlock("code_block")
                    vblock.versions.append(v)
                    vclass.add_child(vblock)

                # Методы
                for method_name, method_info in class_info.methods.items():
                    if method_name is None:
                        continue
                    method_names.add(method_name)
                    method_full_name = f"{class_full_name}.{method_name}"
                    if method_full_name in all_nodes:
                        vmethod = all_nodes[method_full_name]
                    else:
                        vmethod = VersionedMethod(method_name)
                        all_nodes[method_full_name] = vmethod
                        vclass.add_child(vmethod)
                    for v in method_info.versions:
                        vmethod.versions.append(v)

            # 3. Функции верхнего уровня (исключая методы)
            for func_name, func_info in module_info.functions.items():
                if func_name is None or func_name in method_names:
                    continue
                func_full_name = f"{mod_name}.{func_name}"
                if func_full_name in all_nodes:
                    vfunc = all_nodes[func_full_name]
                else:
                    vfunc = VersionedFunction(func_name)
                    all_nodes[func_full_name] = vfunc
                    module_node.add_child(vfunc)
                for v in func_info.versions:
                    vfunc.versions.append(v)

            # 4. Блоки кода верхнего уровня (модуль)
            if module_info.code_block_versions:
                vblock = VersionedCodeBlock("code_block")
                for v in module_info.code_block_versions:
                    vblock.versions.append(v)
                module_node.add_child(vblock)

        roots = {full_name: node for full_name, node in all_nodes.items() if node.parent is None}
        logger.debug(f"Roots: {list(roots.keys())}")
        return roots

    # ---------- Вспомогательные методы ----------
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

    # ---------- Сбор абсолютных импортов ----------
    def _collect_absolute_imports_to_tree(self):
        count = 0
        for mod_name, imports_dict in self.module_identifier._imported.items():
            for imp in imports_dict.values():
                if not imp.is_relative:
                    self.identifier_tree.add_path(imp.target_fullname)
                    count += 1
        logger.debug(f"Добавлено абсолютных импортов в дерево: {count}")

    # ---------- Добавление определений из блоков ----------
    def _add_definitions_from_block(self, block: Block):
        if not block.module_hint or not block.code_tree:
            return
        self.identifier_tree.add_path(block.module_hint)
        self._add_definitions_recursive(block.code_tree, block.module_hint)

    def _add_definitions_recursive(self, node: CodeNode, current_path: str):
        for child in node.children:
            if isinstance(child, (ClassNode, FunctionNode, MethodNode)):
                full_path = f"{current_path}.{child.name}"
                self.identifier_tree.add_path(full_path)
                logger.debug(f"Добавлен узел в дерево: {full_path} (тип: {child.node_type})")
                self._add_definitions_recursive(child, full_path)
            else:
                self._add_definitions_recursive(child, current_path)