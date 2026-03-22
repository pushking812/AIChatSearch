# aichat_search/tools/code_structure/core/project_tree_builder.py

import logging
from typing import List, Dict, Optional, Set
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.core.import_analyzer import build_imported_items_by_module
from aichat_search.tools.code_structure.utils.helpers import extract_module_hint
from aichat_search.tools.code_structure.models.project_models import ProjectInfo, ProjectModuleInfo
from aichat_search.tools.code_structure.models.node import ClassNode, FunctionNode, MethodNode

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ProjectTreeBuilder:
    """
    Строит дерево модулей проекта на основе комментариев и импортов из блоков.
    """

    def __init__(self):
        self.project_info = ProjectInfo()

    def process_blocks(self, blocks: List[MessageBlockInfo]) -> ProjectInfo:
        """Основной метод: собирает информацию из всех блоков."""
        self._collect_comments(blocks)
        self._collect_imports(blocks)
        self._build_module_tree()
        self._resolve_conflicts()
        return self.project_info

    def _collect_comments(self, blocks: List[MessageBlockInfo]):
        """Извлекает комментарии-подсказки и добавляет модули в проект."""
        for block in blocks:
            if block.syntax_error or not block.content:
                continue
            hint = extract_module_hint(block)
            if hint:
                self._add_module(hint, from_comment=True, block_id=block.block_id)
                if block.tree:
                    self._collect_definitions(block.tree, hint, block.block_id)

    def _collect_definitions(self, node, module_name: str, block_id: str):
        """Обходит дерево и собирает определения классов и функций."""
        for child in node.children:
            if isinstance(child, ClassNode):
                self._add_definition(child.name, 'class', module_name, block_id)
                self._collect_definitions(child, module_name, block_id)
            elif isinstance(child, FunctionNode):
                self._add_definition(child.name, 'function', module_name, block_id)
            elif isinstance(child, MethodNode):
                # Методы не добавляем как отдельные определения, они принадлежат классам
                pass
            else:
                self._collect_definitions(child, module_name, block_id)

    def _add_definition(self, name: str, def_type: str, module_name: str, block_id: str):
        """Сохраняет определение в проект."""
        if name not in self.project_info.definitions:
            self.project_info.definitions[name] = {}
        if def_type not in self.project_info.definitions[name]:
            self.project_info.definitions[name][def_type] = set()
        self.project_info.definitions[name][def_type].add(module_name)

        module = self._get_or_create_module(module_name)
        if def_type not in module.definitions:
            module.definitions[def_type] = set()
        module.definitions[def_type].add(name)

    def _collect_imports(self, blocks: List[MessageBlockInfo]):
        """Извлекает импорты и добавляет информацию о модулях."""
        imports_by_module = build_imported_items_by_module(blocks)
        for source_module, imports in imports_by_module.items():
            for imp in imports:
                if '.' in imp.target_fullname:
                    target_module = imp.target_fullname.rsplit('.', 1)[0]
                    self._add_module(target_module, from_import=True, block_id=source_module)
                else:
                    target_module = imp.target_fullname
                    self._add_module(target_module, from_import=True, block_id=source_module)

                if imp.target_type in ('class', 'function'):
                    name = imp.target_fullname.split('.')[-1]
                    self._add_definition(name, imp.target_type, target_module, source_module)

    def _add_module(self, module_name: str, from_comment: bool = False, from_import: bool = False, block_id: str = ''):
        """Добавляет модуль в проект, если его ещё нет."""
        module = self._get_or_create_module(module_name)
        if from_comment:
            module.from_comments.add(block_id)
        if from_import:
            module.from_imports.add(block_id)

    def _get_or_create_module(self, module_name: str) -> ProjectModuleInfo:
        """Возвращает модуль по имени, создавая его при необходимости."""
        if module_name not in self.project_info.modules:
            self.project_info.modules[module_name] = ProjectModuleInfo(name=module_name)
        return self.project_info.modules[module_name]

    def _build_module_tree(self):
        """Строит иерархическое дерево модулей из плоского словаря."""
        for name, module in self.project_info.modules.items():
            parts = name.split('.')
            if len(parts) > 1:
                parent_name = '.'.join(parts[:-1])
                parent = self._get_or_create_module(parent_name)
                parent.children[parts[-1]] = module

    def _resolve_conflicts(self):
        """Выявляет конфликты: если одно имя класса/функции определено в нескольких модулях."""
        for name, types in self.project_info.definitions.items():
            for def_type, modules in types.items():
                if len(modules) > 1:
                    logger.warning(f"Конфликт для {def_type} '{name}': определён в {modules}")

    def resolve_module_for_definitions(self) -> Dict[str, Dict[str, Optional[str]]]:
        """
        Для каждого имени определения (класса/функции) вычисляет наиболее вероятный модуль.
        Возвращает словарь: {имя: {тип: модуль}}.
        Приоритет: если есть комментарий, берём его; если нет, берём модуль из импортов,
        если несколько – конфликт, помечаем как None.
        """
        result = {}
        for name, types in self.project_info.definitions.items():
            result[name] = {}
            for def_type, modules in types.items():
                # Сначала ищем, есть ли модуль, который имеет комментарий с определением
                candidate = None
                for mod in modules:
                    module_obj = self.project_info.modules.get(mod)
                    if module_obj and name in module_obj.definitions.get(def_type, set()):
                        if module_obj.from_comments:
                            candidate = mod
                            break
                if candidate:
                    result[name][def_type] = candidate
                    continue
                if len(modules) == 1:
                    result[name][def_type] = next(iter(modules))
                else:
                    # Несколько возможных модулей – конфликт
                    logger.warning(f"Конфликт для {def_type} '{name}': возможные модули {modules}")
                    result[name][def_type] = None
        return result

    def _extract_class_names(self, node) -> Set[str]:
        """Рекурсивно извлекает имена классов из дерева."""
        classes = set()
        for child in node.children:
            if isinstance(child, ClassNode):
                classes.add(child.name)
            classes.update(self._extract_class_names(child))
        return classes

    def _extract_function_names(self, node) -> Set[str]:
        """Рекурсивно извлекает имена функций из дерева (не методы)."""
        functions = set()
        for child in node.children:
            if isinstance(child, FunctionNode):
                functions.add(child.name)
            elif isinstance(child, MethodNode):
                continue
            functions.update(self._extract_function_names(child))
        return functions

    def _block_has_class_or_function(self, node) -> bool:
        """Проверяет, содержит ли дерево узлов класс или функцию (не метод)."""
        for child in node.children:
            if isinstance(child, ClassNode) or isinstance(child, FunctionNode):
                return True
            if self._block_has_class_or_function(child):
                return True
        return False

    def assign_blocks_to_modules(self, blocks: List[MessageBlockInfo]) -> List[MessageBlockInfo]:
        """
        Присваивает module_hint только блокам, содержащим классы или функции (не методы).
        Возвращает список блоков, для которых не удалось определить модуль (конфликт или неопределённость).
        """
        module_for_def = self.resolve_module_for_definitions()
        need_dialog = []

        for block in blocks:
            if block.syntax_error or not block.tree:
                continue
            # Если у блока уже есть module_hint из комментария, не переопределяем
            if block.module_hint:
                continue

            # Обрабатываем только блоки с классами или функциями (не методами)
            if not self._block_has_class_or_function(block.tree):
                continue

            classes = self._extract_class_names(block.tree)
            functions = self._extract_function_names(block.tree)
            possible_modules = set()
            for cls in classes:
                mod = module_for_def.get(cls, {}).get('class')
                if mod:
                    possible_modules.add(mod)
            for func in functions:
                mod = module_for_def.get(func, {}).get('function')
                if mod:
                    possible_modules.add(mod)

            if len(possible_modules) == 1:
                block.module_hint = next(iter(possible_modules))
            elif len(possible_modules) > 1:
                logger.warning(f"Блок {block.block_id} содержит определения из разных модулей: {possible_modules}")
                need_dialog.append(block)
            else:
                # Нет определений или не удалось определить модуль
                pass

        return need_dialog