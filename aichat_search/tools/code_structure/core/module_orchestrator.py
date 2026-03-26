# aichat_search/tools/code_structure/core/module_orchestrator.py

import logging
import re
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict

from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.models.containers import (
    Container, MethodContainer, ClassContainer, ModuleContainer, FunctionContainer, PackageContainer
)
from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier
from aichat_search.tools.code_structure.core.module_resolver import ModuleResolver
from aichat_search.tools.code_structure.core.structure_builder import StructureBuilder
from aichat_search.tools.code_structure.models.import_models import ImportInfo
from aichat_search.tools.code_structure.core.signature_utils import extract_function_signature

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ModuleOrchestrator:
    def __init__(self):
        self.module_identifier = ModuleIdentifier()
        self.module_resolver = None
        self.structure_builder = StructureBuilder()
        self.module_groups: Dict[str, List[MessageBlockInfo]] = {}
        self.module_base_blocks: Dict[str, MessageBlockInfo] = {}
        self.module_containers: Dict[str, Container] = {}
        self.assignment_stats: Dict[str, Tuple[str, None]] = {}
        self.temp_modules: List[str] = []
        self.error_blocks: List[MessageBlockInfo] = []
        self.text_blocks_by_pair: Dict[str, Dict[int, str]] = {}
        self.full_texts_by_pair: Dict[str, str] = {}

    def process_blocks(
        self,
        blocks: List[MessageBlockInfo],
        imported_by_module: Optional[Dict[str, List[ImportInfo]]] = None,
        text_blocks_by_pair: Optional[Dict[str, Dict[int, str]]] = None,
        full_texts_by_pair: Optional[Dict[str, str]] = None
    ) -> Tuple[Dict[str, Container], List[MessageBlockInfo]]:
        logger.info("=== process_blocks: НАЧАЛО ===")
        self._reset_state()
        self.text_blocks_by_pair = text_blocks_by_pair or {}
        self.full_texts_by_pair = full_texts_by_pair or {}
        valid_blocks, error_blocks = self._separate_error_blocks(blocks)
        self.error_blocks = error_blocks
        logger.info(f"Блоков с ошибками: {len(error_blocks)}")

        self._collect_initial_identifiers(valid_blocks)

        if imported_by_module:
            self._add_imported_identifiers(imported_by_module)

        self._apply_text_hints(valid_blocks)

        unknown_blocks = self._resolve_modules_iteratively(valid_blocks)
        self.module_groups = self._group_blocks_by_module(valid_blocks)
        self._select_base_blocks()
        self._create_placeholder_containers()
        self._build_initial_structures()
        self._merge_remaining_blocks()
        self._merge_temp_modules()

        self._build_unified_containers()

        self.unknown_blocks = unknown_blocks
        self.log_analysis_result()

        return self.module_containers, unknown_blocks + error_blocks

    def _reset_state(self):
        self.module_groups.clear()
        self.module_base_blocks.clear()
        self.module_containers.clear()
        self.assignment_stats.clear()
        self.temp_modules.clear()
        self.error_blocks.clear()

    def _separate_error_blocks(self, blocks):
        valid, errors = [], []
        for b in blocks:
            if b.syntax_error or b.tree is None:
                errors.append(b)
            else:
                valid.append(b)
        return valid, errors

    def _collect_initial_identifiers(self, blocks):
        for b in blocks:
            if b.module_hint and b.tree and not b.syntax_error:
                self.module_identifier.collect_from_tree(b.tree, b.module_hint)

    def _add_imported_identifiers(self, imported_by_module: Dict[str, List[ImportInfo]]):
        for module_name, imports in imported_by_module.items():
            for imp in imports:
                self.module_identifier.add_imported_item(module_name, imp)

    def _block_has_imports(self, content):
        import_patterns = [r'^import\s+\w+', r'^from\s+\w+\s+import']
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            for pattern in import_patterns:
                if re.match(pattern, line):
                    return True
        return False

    def _get_block_priority(self, block: MessageBlockInfo) -> int:
        if not block.tree or block.syntax_error:
            return 999
        has_classes = self._block_has_classes(block)
        has_imports = self._block_has_imports(block.content)
        if has_classes:
            return 1
        elif has_imports:
            return 2
        elif block.module_hint:
            return 3
        else:
            return 4

    def _sort_blocks_for_module(self, blocks: List[MessageBlockInfo]) -> List[MessageBlockInfo]:
        sorted_blocks = sorted(blocks, key=lambda b: (self._get_block_priority(b), b.global_index))
        for order, block in enumerate(sorted_blocks, 1):
            if block.metadata is None:
                block.metadata = {}
            block.metadata['module_order'] = order
        return sorted_blocks

    def _resolve_modules_iteratively(self, blocks):
        for b in blocks:
            if b.module_hint and b.tree and not b.syntax_error:
                self.module_identifier.collect_from_tree(b.tree, b.module_hint)

        self.module_resolver = ModuleResolver(self.module_identifier)

        group_classes_with_hint = []
        group_imports_with_hint = []
        group_classes_only = []
        group_imports_only = []
        group_neither = []

        for b in blocks:
            if not b.tree or b.syntax_error:
                continue
            has_classes = self._block_has_classes(b)
            has_imports = self._block_has_imports(b.content)

            if has_classes and b.module_hint:
                group_classes_with_hint.append(b)
            elif not has_classes and has_imports and b.module_hint:
                group_imports_with_hint.append(b)
            elif has_classes and not b.module_hint:
                group_classes_only.append(b)
            elif not has_classes and has_imports and not b.module_hint:
                group_imports_only.append(b)
            else:
                group_neither.append(b)

        self.assignment_stats.clear()
        self.temp_modules.clear()

        def process_group(group):
            unknown = group[:]
            while True:
                newly = []
                still = []
                for block in unknown:
                    resolved, module, _ = self.module_resolver.resolve_block(block)
                    if resolved:
                        block.module_hint = module
                        self.module_identifier.collect_from_tree(block.tree, module)
                        newly.append(block)
                        self.assignment_stats[block.block_id] = (module, None)
                    else:
                        still.append(block)
                if not newly:
                    break
                unknown = still
            return unknown

        unknown1 = process_group(group_classes_with_hint)
        unknown2 = process_group(group_imports_with_hint)
        unknown3 = process_group(group_classes_only)

        for block in unknown1 + unknown3:
            if self._block_has_classes(block):
                temp = f"temp_{block.block_id}"
                block.module_hint = temp
                self.module_identifier.collect_from_tree(block.tree, temp)
                self.temp_modules.append(temp)

        unknown4 = process_group(group_imports_only)
        unknown5 = process_group(group_neither)

        final_unknown = unknown2 + unknown4 + unknown5

        logger.info(f"Определено модулей: {len(self.assignment_stats)}")
        logger.info(f"Временных модулей: {len(self.temp_modules)}")
        logger.info(f"Неопределено: {len(final_unknown)}")
        return final_unknown

    def _block_has_classes(self, block):
        if not block.tree:
            return False
        for child in block.tree.children:
            if child.node_type == "class":
                return True
        return False

    def _group_blocks_by_module(self, blocks):
        groups = defaultdict(list)
        for b in blocks:
            if b.module_hint:
                groups[b.module_hint].append(b)
        return dict(groups)

    def _select_most_complete_block(self, blocks: List[MessageBlockInfo]) -> Optional[MessageBlockInfo]:
        if not blocks:
            return None
        best = None
        best_cnt = -1
        best_idx = float('inf')
        for block in blocks:
            if block.tree is None or block.syntax_error:
                continue
            count = block.tree.count_nodes()
            if count > best_cnt or (count == best_cnt and block.global_index < best_idx):
                best_cnt = count
                best_idx = block.global_index
                best = block
        return best

    def _select_base_blocks(self):
        self.module_base_blocks = {}
        for module, blocks in self.module_groups.items():
            base = self._select_most_complete_block(blocks)
            if base:
                self.module_base_blocks[module] = base
                logger.debug(f"Базовый блок для {module}: {base.block_id}")

    def _create_placeholder_containers(self):
        for module_name, module_info in self.module_identifier._modules.items():
            if module_name not in self.module_containers:
                self.module_containers[module_name] = ModuleContainer(module_name)
            container = self.module_containers[module_name]
            for class_name in module_info.classes.keys():
                if not any(child.name == class_name and child.node_type == "class" for child in container.children):
                    class_container = ClassContainer(class_name)
                    container.add_child(class_container)
                    logger.debug(f"Добавлен плейсхолдер класса {class_name} в модуль {module_name}")

    def _build_initial_structures(self):
        for module_name, base_block in self.module_base_blocks.items():
            container = self.module_containers.get(module_name)
            if container is None:
                container = ModuleContainer(module_name)
                self.module_containers[module_name] = container
            if base_block.tree and not base_block.syntax_error:
                self.structure_builder.merge_node_into_container(base_block.tree, container, base_block)

    def _merge_remaining_blocks(self):
        for module_name, container in self.module_containers.items():
            base = self.module_base_blocks.get(module_name)
            if not base:
                continue

            all_blocks = self.module_groups.get(module_name, [])
            sorted_blocks = self._sort_blocks_for_module(all_blocks)
            others = [b for b in sorted_blocks if b is not base]

            for block in others:
                if block.tree and not block.syntax_error:
                    class_hint = block.metadata.get('class_hint') if block.metadata else None
                    if class_hint:
                        if not any(child.name == class_hint and child.node_type == "class" for child in container.children):
                            class_container = ClassContainer(class_hint)
                            container.add_child(class_container)
                            logger.debug(f"Создан класс {class_hint} в модуле {module_name} во время слияния")
                    try:
                        self.structure_builder.merge_node_into_container(
                            block.tree, container, block
                        )
                    except Exception as e:
                        logger.error(f"Ошибка при слиянии блока {block.block_id} в модуль {module_name}: {e}", exc_info=True)

    def _merge_temp_modules(self):
        logger.info("=== Объединение temp-модулей ===")
        temp_modules = self.module_identifier.get_temp_modules()
        if not temp_modules:
            return

        for temp in temp_modules:
            try:
                temp_info = self.module_identifier.get_module_info(temp)
                if not temp_info:
                    continue

                temp_classes = set(temp_info.classes.keys())
                target = None
                for mod_name in self.module_identifier.get_all_module_names():
                    if mod_name.startswith('temp_'):
                        continue
                    mod_info = self.module_identifier.get_module_info(mod_name)
                    if not mod_info:
                        continue
                    real_classes = set(mod_info.classes.keys())
                    if temp_classes & real_classes:
                        target = mod_name
                        break

                if target:
                    self.module_identifier.merge_temp_module(temp, target)
                else:
                    logger.warning(f"Не найден целевой модуль для временного {temp}, пропускаем")
            except Exception as e:
                logger.error(f"Ошибка при объединении {temp}: {e}")

    def _build_unified_containers(self):
        """Строит полную иерархию контейнеров, включая пакеты и импортированные модули."""
        # 1. Собираем все имена модулей
        all_module_names = set()
        all_module_names.update(self.module_containers.keys())
        all_module_names.update(self.module_identifier.get_all_module_names())
        for module_name, imports in self.module_identifier._imported.items():
            for imp in imports.values():
                if '.' in imp.target_fullname:
                    module = imp.target_fullname.rsplit('.', 1)[0]
                else:
                    module = imp.target_fullname
                all_module_names.add(module)

        # 2. Строим иерархию
        root_containers = {}
        for full_name in sorted(all_module_names):
            parts = full_name.split('.')
            current = root_containers
            parent = None
            for i, part in enumerate(parts):
                is_last = (i == len(parts) - 1)

                if is_last and full_name in self.module_containers:
                    container = self.module_containers[full_name]
                    container.name = part
                else:
                    if part not in current:
                        if is_last:
                            container = ModuleContainer(part)
                            container.set_placeholder(True)
                        else:
                            container = PackageContainer(part)
                        current[part] = container
                    else:
                        container = current[part]

                if parent is not None:
                    if container not in parent.children:
                        parent.add_child(container)

                parent = container
                if hasattr(container, 'children_dict'):
                    current = container.children_dict
                else:
                    container.children_dict = {c.name: c for c in container.children}
                    current = container.children_dict

            # После построения иерархии для последнего уровня заполняем контейнер
            if is_last:
                self._populate_placeholder_container(parent, full_name)

        self.module_containers = root_containers

    def _populate_placeholder_container(self, container: ModuleContainer, full_name: str):
        """Заполняет контейнер классами и функциями из module_identifier (включая импортированные)."""
        module_info = self.module_identifier.get_module_info(full_name)
        if not module_info:
            return

        # Добавляем классы
        for class_name, class_info in module_info.classes.items():
            existing = container.find_child_container(class_name, "class")
            if not existing:
                class_container = ClassContainer(class_name)
                class_container.set_placeholder(True)
                container.add_child(class_container)
            else:
                class_container = existing
                # Если класс уже существует (реальный код), не меняем его тип

            # Добавляем методы класса
            for method_name, method_info in class_info.methods.items():
                if not class_container.find_child_container(method_name, "method"):
                    method_container = MethodContainer(method_name)
                    method_container.set_placeholder(True)
                    class_container.add_child(method_container)

        # Добавляем функции
        for func_name, func_info in module_info.functions.items():
            if not container.find_child_container(func_name, "function"):
                func_container = FunctionContainer(func_name)
                func_container.set_placeholder(True)
                container.add_child(func_container)

    def _log_module_tree(self, module_name: str, container: Container, level: int = 0, order: int = 0):
        indent = "  " * level
        version_info = f" (версий: {len(container.versions)})" if container.versions else ""
        sources_info = ""
        if container.versions and container.versions[0].sources:
            sources = ", ".join([f"{src[0]}:{src[1]}-{src[2]}" for src in container.versions[0].sources[:2]])
            if len(container.versions[0].sources) > 2:
                sources += f" и ещё {len(container.versions[0].sources)-2}"
            sources_info = f" [{sources}]"
        order_info = f"[#{order}]" if order else ""
        logger.info(f"{indent}• {container.name} {order_info}({container.node_type}){version_info}{sources_info}")
        for i, child in enumerate(container.children, 1):
            self._log_module_tree(module_name, child, level + 1, i)

    def log_analysis_result(self):
        logger.info("=" * 60)
        logger.info("ИТОГОВАЯ СТРУКТУРА МОДУЛЕЙ (с порядком обработки)")
        logger.info("=" * 60)
        for module_name, container in self.module_containers.items():
            logger.info(f"\n📦 {module_name}")
            blocks = self.module_groups.get(module_name, [])
            logger.info(f"   Блоков: {len(blocks)}")
            self._log_module_tree(module_name, container, 1, 1)
        if self.temp_modules:
            logger.info(f"\n⚠️ Временные модули: {', '.join(self.temp_modules)}")
        total_blocks = len(self.assignment_stats) + sum(len(g) for g in self.module_groups.values())
        logger.info("=" * 60)
        logger.info(f"Всего модулей: {len(self.module_containers)}")
        logger.info(f"Всего блоков: {total_blocks}")
        logger.info(f"Неопределено: {len(getattr(self, 'unknown_blocks', []))}")
        logger.info("=" * 60)

    def get_blocks_for_module(self, module_name: str) -> List[MessageBlockInfo]:
        return self.module_groups.get(module_name, [])

    def get_module_containers(self) -> Dict[str, Container]:
        return self.module_containers.copy()

    def get_temp_modules(self) -> List[str]:
        return self.temp_modules.copy()

    def get_error_blocks(self) -> List[MessageBlockInfo]:
        return self.error_blocks.copy()

    def clear_temp_data(self):
        self.temp_modules.clear()
        self.assignment_stats.clear()
        self.module_identifier.remove_temp_modules()

    def _apply_text_hints(self, blocks: List[MessageBlockInfo]):
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
                self.module_identifier.add_class_placeholder(module, class_name)
                block.module_hint = module
                if block.metadata is None:
                    block.metadata = {}
                block.metadata['class_hint'] = class_name
                if block.tree:
                    self.module_identifier.collect_from_tree(block.tree, module, class_name)

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