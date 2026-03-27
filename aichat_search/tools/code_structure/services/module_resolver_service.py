# aichat_search/tools/code_structure/services/module_resolver_service.py

import logging
import re
from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict

from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.models.containers import (
    Container, ModuleContainer, PackageContainer, ClassContainer, MethodContainer, FunctionContainer
)
from aichat_search.tools.code_structure.models.identifier_models import ModuleInfo
from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier
from aichat_search.tools.code_structure.core.module_resolver import ModuleResolver
from aichat_search.tools.code_structure.services.import_service import ImportService
from aichat_search.tools.code_structure.core.signature_utils import extract_function_signature
from aichat_search.tools.code_structure.core.version_comparator import VersionComparator
from aichat_search.tools.code_structure.utils.helpers import extract_module_hint

logger = logging.getLogger(__name__)


class ModuleResolverService:
    def __init__(self, import_service: ImportService):
        self.import_service = import_service
        self.module_identifier = ModuleIdentifier()
        self.text_blocks_by_pair: Dict[str, Dict[int, str]] = {}
        self.full_texts_by_pair: Dict[str, str] = {}

    def resolve_blocks(
        self,
        blocks: List[MessageBlockInfo],
        text_blocks_by_pair: Dict[str, Dict[int, str]],
        full_texts_by_pair: Dict[str, str]
    ) -> Tuple[Dict[str, Container], List[MessageBlockInfo]]:
        """
        Определяет модули для блоков кода.

        Returns:
            tuple: (module_containers, unknown_blocks)
        """
        self.text_blocks_by_pair = text_blocks_by_pair
        self.full_texts_by_pair = full_texts_by_pair

        valid_blocks, error_blocks = self._separate_error_blocks(blocks)
        print(f"Блоков с ошибками: {len(error_blocks)}")

        # 1. Блоки с явным module_hint из комментариев
        self._add_blocks_with_hint(valid_blocks)

        # 2. Анализ комментариев и импортов для назначения модулей
        self._assign_from_comments_and_imports(valid_blocks)

        # 3. Собираем импорты (для идентификации импортированных объектов)
        imported_by_module = self.import_service.get_imported_items_by_module(valid_blocks)
        self._add_imported_identifiers(imported_by_module)

        # 4. Текстовые подсказки
        self._apply_text_hints(valid_blocks)

        # 5. Итеративное разрешение модулей для блоков без подсказок
        unknown_blocks = self._resolve_modules_iteratively(valid_blocks)

        # 6. Строим итоговые контейнеры
        containers = self._build_unified_containers()

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
            if not b.module_hint and b.content:
                hint = extract_module_hint(b)
                if hint:
                    b.module_hint = hint
            if b.module_hint and b.tree and not b.syntax_error:
                self.module_identifier.collect_from_tree(b.tree, b.module_hint, block_info=b)

    def _add_imported_identifiers(self, imported_by_module: Dict[str, List]):
        for module_name, imports in imported_by_module.items():
            for imp in imports:
                self.module_identifier.add_imported_item(module_name, imp)

    def _assign_from_comments_and_imports(self, blocks: List[MessageBlockInfo]):
        """
        Анализирует комментарии-подсказки и импорты для назначения module_hint блокам,
        содержащим классы или функции.
        """
        # Сбор информации: для каждого имени класса/функции собираем модули-источники
        module_for_def = defaultdict(lambda: defaultdict(set))  # {name: {type: set(modules)}}
        
        # 1. Сбор из комментариев-подсказок
        for block in blocks:
            if block.syntax_error or not block.content:
                continue
            hint = extract_module_hint(block)
            if hint:
                self._collect_definitions_from_block(block, hint, module_for_def)

        # 2. Сбор из импортов
        for block in blocks:
            if block.syntax_error or not block.content:
                continue
            current_module = block.module_hint
            if not current_module:
                continue
            imports = self.import_service.get_imported_items_by_module([block]).get(current_module, [])
            for imp in imports:
                target_module = imp.target_fullname.rsplit('.', 1)[0] if '.' in imp.target_fullname else imp.target_fullname
                name = imp.target_fullname.split('.')[-1]
                module_for_def[name][imp.target_type].add(target_module)

        # 3. Определение наиболее вероятного модуля для каждого имени
        resolved_def = {}  # {name: {type: module}}
        for name, types in module_for_def.items():
            resolved_def[name] = {}
            for def_type, modules in types.items():
                if len(modules) == 1:
                    resolved_def[name][def_type] = next(iter(modules))
                else:
                    # Несколько возможных модулей – конфликт, помечаем None
                    resolved_def[name][def_type] = None

        # 4. Назначение module_hint для блоков, содержащих классы или функции
        already_assigned = set()
        for block in blocks:
            if block.module_hint and block not in already_assigned:
                print(f"Блоку {block.block_id} назначен модуль {block.module_hint} из комментариев/импортов")
            if block.module_hint or block.syntax_error or not block.tree:
                continue
            if not self._block_has_classes_or_functions(block.tree):
                continue

            classes = self._extract_class_names(block.tree)
            functions = self._extract_function_names(block.tree)
            possible_modules = set()
            for cls in classes:
                mod = resolved_def.get(cls, {}).get('class')
                if mod:
                    possible_modules.add(mod)
            for func in functions:
                mod = resolved_def.get(func, {}).get('function')
                if mod:
                    possible_modules.add(mod)

            if len(possible_modules) == 1:
                module = next(iter(possible_modules))
                block.module_hint = module
                self.module_identifier.collect_from_tree(block.tree, module, block_info=block)
                print(f"[COMMENTS/IMPORTS] Блоку {block.block_id} назначен модуль {module}")
            elif len(possible_modules) > 1:
                logger.warning(f"[COMMENTS/IMPORTS] Блок {block.block_id} содержит определения из разных модулей: {possible_modules}")

    def _collect_definitions_from_block(self, block: MessageBlockInfo, module_name: str, module_for_def: dict):
        """Собирает имена классов и функций из дерева блока."""
        if not block.tree:
            return
        for child in block.tree.children:
            if child.node_type == "class":
                module_for_def[child.name]['class'].add(module_name)
                self._collect_definitions_from_node(child, module_name, module_for_def)
            elif child.node_type == "function":
                module_for_def[child.name]['function'].add(module_name)
            elif child.node_type == "method":
                pass
            else:
                self._collect_definitions_from_node(child, module_name, module_for_def)

    def _collect_definitions_from_node(self, node, module_name: str, module_for_def: dict):
        for child in node.children:
            if child.node_type == "class":
                module_for_def[child.name]['class'].add(module_name)
                self._collect_definitions_from_node(child, module_name, module_for_def)
            elif child.node_type == "function":
                module_for_def[child.name]['function'].add(module_name)
            elif child.node_type == "method":
                pass
            else:
                self._collect_definitions_from_node(child, module_name, module_for_def)

    def _block_has_classes_or_functions(self, node) -> bool:
        """Проверяет, содержит ли дерево узлов класс или функцию (не метод)."""
        for child in node.children:
            if child.node_type in ("class", "function"):
                return True
            if self._block_has_classes_or_functions(child):
                return True
        return False

    def _extract_class_names(self, node) -> Set[str]:
        classes = set()
        for child in node.children:
            if child.node_type == "class":
                classes.add(child.name)
            classes.update(self._extract_class_names(child))
        return classes

    def _extract_function_names(self, node) -> Set[str]:
        functions = set()
        for child in node.children:
            if child.node_type == "function":
                functions.add(child.name)
            elif child.node_type == "method":
                continue
            functions.update(self._extract_function_names(child))
        return functions

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
                print(f"Текстовая подсказка: класс {class_name} -> модуль {module} для блока {block.block_id}")
                if block.tree:
                    self.module_identifier.collect_from_tree(block.tree, module, class_hint=class_name, block_info=block)
                if block.metadata is None:
                    block.metadata = {}
                block.metadata['class_hint'] = class_name

    def _resolve_modules_iteratively(self, blocks):
        # 1. Обрабатываем уже назначенные (из комментариев/импортов)
        for b in blocks:
            if b.module_hint and b.tree and not b.syntax_error:
                self.module_identifier.collect_from_tree(b.tree, b.module_hint, block_info=b)

        # 2. Применяем текстовые подсказки, чтобы получить hint для оставшихся
        self._apply_text_hints(blocks)

        module_resolver = ModuleResolver(self.module_identifier)

        # 3. Формируем группы с учётом всех hint (включая полученные из текста)
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

        def process_group(group):
            unknown = group[:]
            while True:
                newly = []
                still = []
                for block in unknown:
                    # Если у блока уже есть hint, пропускаем (хотя он не должен сюда попадать)
                    if block.module_hint:
                        continue
                    resolved, module, _ = module_resolver.resolve_block(block)
                    if resolved:
                        block.module_hint = module
                        self.module_identifier.collect_from_tree(block.tree, module, block_info=block)
                        newly.append(block)
                    else:
                        still.append(block)
                if not newly:
                    break
                unknown = still
            return unknown

        unknown1 = process_group(group_classes_with_hint)
        unknown2 = process_group(group_imports_with_hint)
        unknown3 = process_group(group_classes_only)
        unknown4 = process_group(group_imports_only)
        unknown5 = process_group(group_neither)

        final_unknown = unknown2 + unknown4 + unknown5
        logger.info(f"Неопределено: {len(final_unknown)}")
        return final_unknown

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
        # 1. Создаём классы и их методы
        for class_name, class_info in module_info.classes.items():
            class_container = module_container.find_child_container(class_name, "class")
            if not class_container:
                class_container = ClassContainer(class_name)
                module_container.add_child(class_container)
                class_container.full_path = f"{module_container.full_path}.{class_name}"
            for v in class_info.versions:
                class_container.add_version(v)
            for method_name, method_info in class_info.methods.items():
                method_container = class_container.find_child_container(method_name, "method")
                if not method_container:
                    method_container = MethodContainer(method_name)
                    class_container.add_child(method_container)
                    method_container.full_path = f"{class_container.full_path}.{method_name}"
                for v in method_info.versions:
                    method_container.add_version(v)

        # 2. Собираем все имена методов для обработки функций
        method_names = set()
        for class_info in module_info.classes.values():
            method_names.update(class_info.methods.keys())

        # 3. Обрабатываем функции из module_info.functions
        for func_name, func_info in module_info.functions.items():
            if func_name in method_names:
                # Это метод класса – добавляем его версии в существующий метод
                for class_name, class_info in module_info.classes.items():
                    if func_name in class_info.methods:
                        class_container = module_container.find_child_container(class_name, "class")
                        if class_container:
                            method_container = class_container.find_child_container(func_name, "method")
                            if method_container:
                                for v in func_info.versions:
                                    existing = VersionComparator.find_existing(method_container.versions, v)
                                    if not existing:
                                        method_container.add_version(v)
            else:
                # Обычная функция – создаём контейнер и добавляем версии
                func_container = module_container.find_child_container(func_name, "function")
                if not func_container:
                    func_container = FunctionContainer(func_name)
                    module_container.add_child(func_container)
                    func_container.full_path = f"{module_container.full_path}.{func_name}"
                for v in func_info.versions:
                    func_container.add_version(v)