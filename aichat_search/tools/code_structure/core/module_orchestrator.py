# aichat_search/tools/code_structure/core/module_orchestrator.py

import logging
import re
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict

from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.models.containers import (
    Container, MethodContainer, ClassContainer, ModuleContainer, FunctionContainer, PackageContainer, Version
)
from aichat_search.tools.code_structure.models.identifier_models import ModuleInfo, ClassInfo, MethodInfo, FunctionInfo, VersionInfo
from aichat_search.tools.code_structure.models.node import Node
from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier
from aichat_search.tools.code_structure.core.module_resolver import ModuleResolver
from aichat_search.tools.code_structure.models.import_models import ImportInfo
from aichat_search.tools.code_structure.core.signature_utils import extract_function_signature

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ModuleOrchestrator:
    def __init__(self):
        self.module_identifier = ModuleIdentifier()
        self.module_resolver = None
        self.text_blocks_by_pair: Dict[str, Dict[int, str]] = {}
        self.full_texts_by_pair: Dict[str, str] = {}
        self.module_containers: Dict[str, Container] = {}

    def process_blocks(
        self,
        blocks: List[MessageBlockInfo],
        imported_by_module: Optional[Dict[str, List[ImportInfo]]] = None,
        text_blocks_by_pair: Optional[Dict[str, Dict[int, str]]] = None,
        full_texts_by_pair: Optional[Dict[str, str]] = None
    ) -> Tuple[Dict[str, Container], List[MessageBlockInfo]]:
        logger.info("=== process_blocks: НАЧАЛО ===")
        self.text_blocks_by_pair = text_blocks_by_pair or {}
        self.full_texts_by_pair = full_texts_by_pair or {}
        valid_blocks, error_blocks = self._separate_error_blocks(blocks)
        logger.info(f"Блоков с ошибками: {len(error_blocks)}")

        self._add_blocks_with_hint(valid_blocks)

        if imported_by_module:
            self._add_imported_identifiers(imported_by_module)

        self._apply_text_hints(valid_blocks)

        unknown_blocks = self._resolve_modules_iteratively(valid_blocks)

        containers = self._build_unified_containers()
        self.module_containers = containers

        logger.info(f"Обработано блоков: {len(blocks)}, построено контейнеров: {len(containers)}")
        return containers, unknown_blocks + error_blocks

    def _separate_error_blocks(self, blocks):
        valid, errors = [], []
        for b in blocks:
            if b.syntax_error or b.tree is None:
                errors.append(b)
            else:
                valid.append(b)
        return valid, errors

    def _add_blocks_with_hint(self, blocks):
        for b in blocks:
            if b.module_hint and b.tree and not b.syntax_error:
                self.module_identifier.collect_from_tree(b.tree, b.module_hint, block_info=b)

    def _add_imported_identifiers(self, imported_by_module: Dict[str, List[ImportInfo]]):
        for module_name, imports in imported_by_module.items():
            for imp in imports:
                self.module_identifier.add_imported_item(module_name, imp)

    def _apply_text_hints(self, blocks: List[MessageBlockInfo]):
        import re
        for block in blocks:
            if block.module_hint:
                continue
            if not block.tree:
                continue
            if not self._block_has_methods_or_functions(block):
                continue
            pair_index = block.metadata.get('pair_index')
            if pair_index is None:
                continue
            text_blocks = self.text_blocks_by_pair.get(pair_index, {})
            prev_text_idx = None
            for idx in text_blocks:
                if idx < block.block_idx:
                    if prev_text_idx is None or idx > prev_text_idx:
                        prev_text_idx = idx
            if prev_text_idx is None:
                continue
            text = text_blocks[prev_text_idx]
            match = re.search(r'класс[аеуы]?\s+(?:`|\'|")?([A-Za-z_][A-Za-z0-9_]*)(?:`|\'|")?', text, re.IGNORECASE)
            if not match:
                continue
            class_name = match.group(1)
            module = self.module_identifier.find_module_for_class(class_name)
            if not module:
                module = self.module_identifier.find_imported_class(class_name)
            if module:
                logger.info(f"Текстовая подсказка: класс {class_name} -> модуль {module} для блока {block.block_id}")
                if block.tree:
                    self.module_identifier.collect_from_tree(block.tree, module, class_hint=class_name, block_info=block)
                block.module_hint = module
                if block.metadata is None:
                    block.metadata = {}
                block.metadata['class_hint'] = class_name

    def _resolve_modules_iteratively(self, blocks):
        for b in blocks:
            if b.module_hint and b.tree and not b.syntax_error:
                self.module_identifier.collect_from_tree(b.tree, b.module_hint, block_info=b)

        self.module_resolver = ModuleResolver(self.module_identifier)

        # Группировка (упрощённая)
        blocks_without_hint = [b for b in blocks if not b.module_hint]
        unknown = []
        for block in blocks_without_hint:
            resolved, module, _ = self.module_resolver.resolve_block(block)
            if resolved:
                block.module_hint = module
                self.module_identifier.collect_from_tree(block.tree, module, block_info=block)
            else:
                unknown.append(block)
        return unknown

    def _block_has_classes(self, block):
        if not block.tree:
            return False
        for child in block.tree.children:
            if child.node_type == "class":
                return True
        return False

    def _block_has_imports(self, content):
        import_patterns = [r'^import\s+\w+', r'^from\s+\w+\s+import']
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            for pattern in import_patterns:
                if re.match(pattern, line):
                    return True
        return False

    def _block_has_methods_or_functions(self, block: MessageBlockInfo) -> bool:
        if not block.tree:
            return False
        return self._node_has_methods_or_functions(block.tree)

    def _node_has_methods_or_functions(self, node) -> bool:
        for child in node.children:
            if child.node_type in ('method', 'function'):
                if child.node_type == 'function':
                    sig = extract_function_signature(child)
                    if sig[0]:
                        return True
                else:
                    return True
            if self._node_has_methods_or_functions(child):
                return True
        return False

    def _build_unified_containers(self) -> Dict[str, Container]:
        root_containers = {}
        for module_name, module_info in self.module_identifier._modules.items():
            parts = module_name.split('.')
            current = root_containers
            parent = None
            parent_path = ""
            for i, part in enumerate(parts):
                is_last = (i == len(parts) - 1)
                if part not in current:
                    if is_last:
                        container = ModuleContainer(part)
                    else:
                        container = PackageContainer(part)
                    current[part] = container
                    if parent_path:
                        container.full_path = f"{parent_path}.{part}"
                    else:
                        container.full_path = part
                else:
                    container = current[part]

                if parent is not None:
                    if container not in parent.children:
                        parent.add_child(container)

                parent = container
                parent_path = container.full_path
                if hasattr(container, 'children_dict'):
                    current = container.children_dict
                else:
                    container.children_dict = {c.name: c for c in container.children}
                    current = container.children_dict

                if is_last:
                    self._populate_container_with_module_info(container, module_info)

        return root_containers

    def _populate_container_with_module_info(self, module_container: ModuleContainer, module_info: ModuleInfo):
        """Заполняет контейнер модуля классами и функциями из ModuleInfo."""
        # 1. Создаём классы и их методы, добавляя версии из class_info
        for class_name, class_info in module_info.classes.items():
            class_container = module_container.find_child_container(class_name, "class")
            if not class_container:
                class_container = ClassContainer(class_name)
                module_container.add_child(class_container)
                class_container.full_path = f"{module_container.full_path}.{class_name}"
            # Добавляем методы класса с их версиями
            for method_name, method_info in class_info.methods.items():
                method_container = class_container.find_child_container(method_name, "method")
                if not method_container:
                    method_container = MethodContainer(method_name)
                    class_container.add_child(method_container)
                    method_container.full_path = f"{class_container.full_path}.{method_name}"
                # Добавляем все версии метода из method_info.sources
                for src in method_info.sources:
                    # Создаём фиктивный узел, чтобы удовлетворить конструктор Version
                    class DummyNode:
                        def __init__(self):
                            self.name = method_name
                            self.lineno_start = src.start
                            self.lineno_end = src.end
                            self.signature = ""
                    dummy_node = DummyNode()
                    version = Version(dummy_node, src.block_id, src.global_index, "", src.timestamp, src.block_idx)
                    method_container.add_version(version)

        # 2. Обрабатываем функции (не принадлежащие классам)
        # Собираем все имена методов из классов, чтобы исключить их
        method_names = set()
        for class_info in module_info.classes.values():
            method_names.update(class_info.methods.keys())

        for func_name, func_info in module_info.functions.items():
            if func_name in method_names:
                continue  # это метод, уже обработан
            func_container = module_container.find_child_container(func_name, "function")
            if not func_container:
                func_container = FunctionContainer(func_name)
                module_container.add_child(func_container)
                func_container.full_path = f"{module_container.full_path}.{func_name}"
            for src in func_info.sources:
                class DummyNode:
                    def __init__(self):
                        self.name = func_name
                        self.lineno_start = src.start
                        self.lineno_end = src.end
                        self.signature = ""
                dummy_node = DummyNode()
                version = Version(dummy_node, src.block_id, src.global_index, "", src.timestamp, src.block_idx)
                func_container.add_version(version)

    def _create_version_from_info(self, src: VersionInfo, name: str) -> Version:
        # Создаём фиктивный узел
        node = Node(name=name, node_type="code_block", lineno_start=src.start, lineno_end=src.end)
        return Version(node, src.block_id, src.global_index, src.block_content, src.timestamp, src.block_idx)