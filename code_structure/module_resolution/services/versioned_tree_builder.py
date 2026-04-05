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
from code_structure.module_resolution.core.identifier_tree import IdentifierTree
from code_structure.imports.models.import_models import ImportInfo
from code_structure.imports.core.import_analyzer import extract_imports_from_block
from code_structure.utils.helpers import extract_module_hint, clean_code
from code_structure.utils.logger import get_logger

logger = get_logger(__name__, level=logging.DEBUG)


class VersionedTreeBuilder:
    def __init__(self):
        self.identifier_tree = IdentifierTree()
        self._version_map: Dict[str, List[VersionInfo]] = {}
        self._node_type_map: Dict[str, str] = {}
        self._imported_paths: set = set()
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

    # ---------- Текстовые подсказки (улучшенные) ----------
    def _extract_module_path_from_text(self, text: str) -> Optional[str]:
        """
        Ищет в тексте подстроку, похожую на путь к Python-модулю.
        Возвращает полное имя модуля (с точками), если такой модуль уже есть в дереве.
        """
        patterns = [
            r'([\w./]+\.py)',          # file.py или path/file.py
            r'([\w.]+\.\w+)',          # module.submodule (без .py)
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Нормализуем: заменяем '/' на '.', убираем .py
                module_path = match.replace('/', '.').replace('\\', '.')
                if module_path.endswith('.py'):
                    module_path = module_path[:-3]
                # Проверяем, существует ли такой модуль в дереве
                if self.identifier_tree.get_node(module_path):
                    logger.info(f"Text hint: found module path '{module_path}' in text")
                    return module_path
        return None

    def _apply_text_hints(self, blocks: List[Block]):
        if not self.text_blocks_by_pair:
            return

        for block in blocks:
            if block.module_hint is not None:
                logger.debug(f"Text hint skip: block {block.id} already has module_hint={block.module_hint}")
                continue
            if not block.code_tree:
                logger.debug(f"Text hint skip: block {block.id} has no code_tree")
                continue
            pair_index = block.pair_index
            if pair_index not in self.text_blocks_by_pair:
                logger.debug(f"Text hint skip: block {block.id} pair_index {pair_index} not in text_blocks_by_pair")
                continue
            text_blocks = self.text_blocks_by_pair[pair_index]
            prev_text_idx = None
            for idx in text_blocks:
                if idx < block.block_idx:
                    if prev_text_idx is None or idx > prev_text_idx:
                        prev_text_idx = idx
            if prev_text_idx is None:
                logger.debug(f"Text hint skip: block {block.id} no previous text block")
                continue
            text = text_blocks[prev_text_idx]
            logger.info(f"Text hint processing block {block.id}, prev text block index {prev_text_idx}, text: {text[:200]}...")

            # 1. Сначала ищем имя класса (старая логика)
            class_match = re.search(
                r'(?:в\s+)?класс[еауы]?\s+(?:`|\'|")?([A-Za-z_][A-Za-z0-9_]*)(?:`|\'|")?',
                text, re.IGNORECASE
            )
            module = None
            class_name = None
            if class_match:
                class_name = class_match.group(1)
                module = self.identifier_tree.find_module_for_name(class_name)
                if not module:
                    module = self._find_imported_class(class_name)
                if module:
                    logger.info(f"Text hint: resolved module '{module}' for class '{class_name}'")
            # 2. Если не нашли, ищем путь к модулю
            if not module:
                module = self._extract_module_path_from_text(text)
                if module:
                    class_name = None  # путь модуля не даёт имя класса
                    logger.info(f"Text hint: resolved module by path '{module}'")

            if module:
                logger.info(f"Text hint: assigning module '{module}' to block {block.id}")
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
            else:
                logger.debug(f"Text hint: no module found for block {block.id}")

    # ---------- Разрешение с помощью дерева ----------
    def _resolve_with_tree(self, blocks: List[Block]) -> List[Block]:
        unknown = [b for b in blocks if b.module_hint is None]
        logger.info(f"Resolve with tree: initial unknown blocks count={len(unknown)}")
        changed = True
        iteration = 0
        while changed and unknown:
            changed = False
            for block in unknown[:]:
                if block.module_hint is not None:
                    unknown.remove(block)
                    continue
                if block.code_tree is None:
                    logger.debug(f"Resolve: block {block.id} has no code_tree, skipping")
                    continue
                module = self._resolve_block_with_tree(block)
                if module:
                    logger.info(f"Resolve: block {block.id} resolved to module '{module}'")
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
                    changed = True
                else:
                    logger.debug(f"Resolve: block {block.id} could not be resolved")
            unknown = [b for b in unknown if b.module_hint is None]
            iteration += 1
            if iteration > 20:
                logger.warning("Resolve iteration limit reached")
                break
        logger.info(f"Resolve finished: unknown blocks left={len(unknown)}")
        return unknown

    def _resolve_block_with_tree(self, block: Block) -> Optional[str]:
        if not block.code_tree:
            return None
        classes = self._extract_class_names(block.code_tree)
        functions = self._extract_function_names(block.code_tree)
        logger.debug(f"Resolve block {block.id}: classes={classes}, functions={functions}")
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
        logger.debug(f"Resolve block {block.id}: candidates={candidates}")
        if len(candidates) == 1:
            return next(iter(candidates))
        return None

    def _collect_from_code_node(self, code_node: CodeNode, module_name: str, block: Block, class_hint: Optional[str] = None):
        """
        Рекурсивно обходит дерево CodeNode и строит идентификаторы в identifier_tree.
        Порядок обработки: сначала ClassNode, потом MethodNode, потом FunctionNode.
        Для MethodNode без class_hint выполняется поиск существующего класса по имени метода.
        """
        if code_node is None:
            return

        logger.info(f"COLLECT: block={block.id}, module_name={module_name}, class_hint={class_hint}, node={code_node.name} type={type(code_node).__name__}")
        
        # Сортируем детей по категориям
        class_children = []
        method_children = []
        function_children = []
        other_children = []
        
        for child in code_node.children:
            if isinstance(child, ClassNode):
                class_children.append(child)
            elif isinstance(child, MethodNode):
                method_children.append(child)
            elif isinstance(child, FunctionNode) and not isinstance(child, MethodNode):
                function_children.append(child)
            else:
                other_children.append(child)
        
        # 1. ClassNode
        for child in class_children:
            logger.info(f"  Processing ClassNode: {child.name}")
            class_path = f"{module_name}.{child.name}"
            self.identifier_tree.add_path(class_path)
            self._node_type_map[class_path] = 'class'
            logger.info(f"  ClassNode: added {class_path} as class")
            self._collect_from_code_node(child, class_path, block, child.name)
        
        # 2. MethodNode
        for child in method_children:
            logger.info(f"  Processing MethodNode: {child.name}, class_hint={class_hint}")
            if class_hint:
                # Определяем путь к классу: избегаем дублирования
                if module_name.endswith(f".{class_hint}") or module_name == class_hint:
                    class_path = module_name
                else:
                    class_path = f"{module_name}.{class_hint}"
                if class_path not in self._node_type_map:
                    self.identifier_tree.add_path(class_path)
                    self._node_type_map[class_path] = 'class'
                    logger.info(f"    Created class {class_path} for method {child.name}")
                method_path = f"{class_path}.{child.name}"
                self.identifier_tree.add_path(method_path)
                self._node_type_map[method_path] = 'method'
                self._add_version(method_path, child, block)
                logger.info(f"    Added method {method_path} (class_hint) from {block.id}")
            else:
                # Пытаемся найти существующий класс, который уже имеет метод с таким именем
                existing_class = None
                for path, node_type in self._node_type_map.items():
                    if node_type == 'class':
                        candidate_method_path = f"{path}.{child.name}"
                        if candidate_method_path in self._node_type_map and self._node_type_map[candidate_method_path] == 'method':
                            existing_class = path
                            break
                if existing_class:
                    class_path = existing_class
                    method_path = f"{class_path}.{child.name}"
                    if method_path not in self._node_type_map:
                        self.identifier_tree.add_path(method_path)
                        self._node_type_map[method_path] = 'method'
                    self._add_version(method_path, child, block)
                    logger.info(f"    Added method {method_path} (found existing class) from {block.id}")
                    continue
                
                # Если не нашли, пытаемся извлечь класс из module_name
                parts = module_name.split('.')
                if len(parts) >= 1 and parts[-1] and parts[-1][0].isupper():
                    class_path = module_name
                    if class_path not in self._node_type_map:
                        self.identifier_tree.add_path(class_path)
                        self._node_type_map[class_path] = 'class'
                        logger.info(f"    Auto-created class {class_path} for method {child.name}")
                    method_path = f"{class_path}.{child.name}"
                    if method_path in self._node_type_map and self._node_type_map[method_path] == 'method':
                        logger.info(f"    Method {method_path} already exists, adding version")
                        self._add_version(method_path, child, block)
                    else:
                        self.identifier_tree.add_path(method_path)
                        self._node_type_map[method_path] = 'method'
                        self._add_version(method_path, child, block)
                        logger.info(f"    Added method {method_path} (auto-detected class) from {block.id}")
                else:
                    method_path = f"{module_name}.{child.name}"
                    self.identifier_tree.add_path(method_path)
                    self._node_type_map[method_path] = 'method'
                    self._add_version(method_path, child, block)
                    logger.info(f"    Added method {method_path} (no class detected) from {block.id}")
        
        # 3. FunctionNode
        for child in function_children:
            logger.info(f"  Processing FunctionNode: {child.name}, class_hint={class_hint}")
            if class_hint:
                if module_name.endswith(f".{class_hint}") or module_name == class_hint:
                    class_path = module_name
                else:
                    class_path = f"{module_name}.{class_hint}"
                if class_path not in self._node_type_map:
                    self.identifier_tree.add_path(class_path)
                    self._node_type_map[class_path] = 'class'
                    logger.info(f"    Created class {class_path} for function {child.name}")
                method_path = f"{class_path}.{child.name}"
                self.identifier_tree.add_path(method_path)
                self._node_type_map[method_path] = 'method'
                self._add_version(method_path, child, block)
                logger.info(f"    Function converted to method {method_path} (class_hint)")
            else:
                if self._has_self_parameter(child):
                    # Сначала ищем существующий класс
                    existing_class = None
                    for path, node_type in self._node_type_map.items():
                        if node_type == 'class':
                            candidate_method_path = f"{path}.{child.name}"
                            if candidate_method_path in self._node_type_map and self._node_type_map[candidate_method_path] == 'method':
                                existing_class = path
                                break
                    if existing_class:
                        class_path = existing_class
                        method_path = f"{class_path}.{child.name}"
                        if method_path not in self._node_type_map:
                            self.identifier_tree.add_path(method_path)
                            self._node_type_map[method_path] = 'method'
                        self._add_version(method_path, child, block)
                        logger.info(f"    Function with self added as method {method_path} (found existing class)")
                        continue
                    
                    parts = module_name.split('.')
                    if len(parts) >= 1 and parts[-1] and parts[-1][0].isupper():
                        class_path = module_name
                        if class_path not in self._node_type_map:
                            self.identifier_tree.add_path(class_path)
                            self._node_type_map[class_path] = 'class'
                            logger.info(f"    Auto-created class {class_path} for function with self")
                        method_path = f"{class_path}.{child.name}"
                        if method_path in self._node_type_map and self._node_type_map[method_path] == 'method':
                            logger.info(f"    Method {method_path} already exists, adding version")
                            self._add_version(method_path, child, block)
                        else:
                            self.identifier_tree.add_path(method_path)
                            self._node_type_map[method_path] = 'method'
                            self._add_version(method_path, child, block)
                            logger.info(f"    Function with self converted to method {method_path}")
                    else:
                        func_path = f"{module_name}.{child.name}"
                        if func_path in self._node_type_map and self._node_type_map[func_path] == 'method':
                            logger.info(f"    Path {func_path} already method, adding version")
                            self._add_version(func_path, child, block)
                        else:
                            self.identifier_tree.add_path(func_path)
                            self._node_type_map[func_path] = 'function'
                            self._add_version(func_path, child, block)
                            logger.info(f"    Added function {func_path} (no class detected)")
                else:
                    func_path = f"{module_name}.{child.name}"
                    if func_path in self._node_type_map and self._node_type_map[func_path] == 'method':
                        logger.info(f"    Path {func_path} already method, adding version")
                        self._add_version(func_path, child, block)
                    else:
                        self.identifier_tree.add_path(func_path)
                        self._node_type_map[func_path] = 'function'
                        self._add_version(func_path, child, block)
                        logger.info(f"    Added function {func_path}")
        
        # 4. Остальные узлы
        for child in other_children:
            if isinstance(child, CodeBlockNode):
                block_path = f"{module_name}._code_block"
                self.identifier_tree.add_path(block_path)
                self._node_type_map[block_path] = 'code_block'
                self._add_version(block_path, child, block)
                logger.info(f"  CodeBlockNode: added {block_path}")
            elif isinstance(child, ImportNode):
                self._process_import_statement(child.statement, module_name, block)
            else:
                self._collect_from_code_node(child, module_name, block, class_hint)

    def _has_self_parameter(self, func_node: FunctionNode) -> bool:
        signature = getattr(func_node, 'signature', '')
        if not signature:
            return False
        match = re.match(r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:[=:,]|$)', signature)
        if match:
            first_param = match.group(1)
            return first_param == 'self'
        return False

    def _add_version(self, path: str, code_node: CodeNode, block: Block):
        import difflib
        raw_code = code_node.get_raw_code()
        norm = clean_code(raw_code)
        src = SourceRef(block.id, code_node.start_line, code_node.end_line, block.timestamp)
        versions = self._version_map.setdefault(path, [])
        logger.debug(f"Adding version for {path} from block {block.id}")
        for i, ver in enumerate(versions):
            if ver.normalized_code == norm:
                ver.add_source(src)
                logger.debug(f"  Matched existing version {i+1}, sources now {len(ver.sources)}")
                return
        versions.append(VersionInfo(norm, [src]))
        logger.debug(f"  Created NEW version (total {len(versions)})")

    # ---------- Импорты ----------
    def _add_imports_from_block(self, block: Block):
        if not block.module_hint:
            return
        imports = extract_imports_from_block(block.content, block.module_hint)
        self._block_imports[block.id] = imports
        for imp in imports:
            self.identifier_tree.add_path(imp.target_fullname)
            self._imported_paths.add(imp.target_fullname)

    def _collect_absolute_imports_to_tree(self):
        pass

    def _process_import_statement(self, statement: str, current_module: str, block: Block):
        imports = extract_imports_from_block(statement, current_module)
        for imp in imports:
            self.identifier_tree.add_path(imp.target_fullname)
            self._imported_paths.add(imp.target_fullname)
            self._block_imports.setdefault(block.id, []).append(imp)

    # ---------- Вычисление локальных узлов ----------
    def _compute_local_nodes(self, all_nodes: Dict[str, VersionedNode]):
        local_nodes = set()
        for path, node in all_nodes.items():
            if node.versions:
                local_nodes.add(node)
                parent = node.parent
                while parent:
                    local_nodes.add(parent)
                    parent = parent.parent
        for node in local_nodes:
            node.is_local = True

    # ---------- Построение VersionedNode из identifier_tree ----------
    def _build_versioned_from_identifier(self) -> Dict[str, VersionedNode]:
        all_nodes: Dict[str, VersionedNode] = {}
        self._build_nodes_recursive(self.identifier_tree.root, "", all_nodes)
        for path, versions in self._version_map.items():
            node = all_nodes.get(path)
            if node:
                node.versions = versions
                logger.info(f"Assigned versions to node {path} (type {node.node_type})")
                if node.node_type == 'function' and '.' in path:
                    parent_path = '.'.join(path.split('.')[:-1])
                    parent_node = all_nodes.get(parent_path)
                    if parent_node and parent_node.node_type == 'class':
                        logger.warning(f"Node {path} is function but parent {parent_path} is class - should be method")
            else:
                logger.warning(f"Versions for path {path} but node not found in tree")
        self._mark_imported_nodes(all_nodes)
        self._compute_local_nodes(all_nodes)
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

            logger.info(f"Creating node {full_path} with type {node_type} (map: {self._node_type_map.get(full_path, 'missing')})")

            node = self._create_versioned_node(tree_node.name, node_type)
            all_nodes[full_path] = node
            if current_path and current_path in all_nodes:
                parent = all_nodes[current_path]
                parent.add_child(node)
                logger.info(f"  Attached as child to {current_path}")
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

    def _mark_imported_nodes(self, all_nodes: Dict[str, VersionedNode]):
        for path in self._imported_paths:
            node = all_nodes.get(path)
            if node:
                node.is_imported = True
                parent = node.parent
                while parent:
                    parent.is_imported = True
                    parent = parent.parent
            else:
                parts = path.split('.')
                for i in range(len(parts), 0, -1):
                    parent_path = '.'.join(parts[:i])
                    if parent_path in all_nodes:
                        all_nodes[parent_path].is_imported = True
                        break

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
        # Включаем и MethodNode, потому что они тоже могут быть кандидатами для разрешения
        if isinstance(code_node, (FunctionNode, MethodNode)):
            functions.add(code_node.name)
        for child in code_node.children:
            functions.update(self._extract_function_names(child))
        return functions

    def _find_imported_class(self, class_name: str) -> Optional[str]:
        return self.identifier_tree.find_module_for_name(class_name)