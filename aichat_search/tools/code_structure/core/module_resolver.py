# aichat_search/tools/code_structure/core/module_resolver.py

import logging
import re
from typing import Set, Dict, List, Optional, Tuple
from collections import defaultdict

from aichat_search.tools.code_structure.models.node import Node
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.core.signature_utils import (
    extract_function_signature, compare_signatures
)
from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier

logger = logging.getLogger(__name__)


class ModuleResolver:
    """
    Определитель модулей с чёткими приоритетами:
    1. По классам
    2. По методам (строго: ищем класс с методом того же имени и с self, сравниваем количество параметров)
       Если есть несколько кандидатов – неоднозначность, блок идёт в диалог.
    3. По функциям (без self)
    """

    def __init__(self, module_identifier: ModuleIdentifier):
        self.module_identifier = module_identifier
        self.auto_assign: Dict[str, str] = {}
        self.need_dialog: List[MessageBlockInfo] = []

    def resolve_block(self, block_info: MessageBlockInfo) -> Tuple[bool, Optional[str], None]:
        logger.info(f"=== resolve_block для {block_info.block_id} ===")

        if block_info.tree is None or block_info.syntax_error:
            logger.info(f"  Блок имеет ошибку или пустое дерево")
            return False, None, None

        # Извлекаем идентификаторы и сигнатуры
        classes, functions, methods = self._extract_identifiers(block_info.tree)
        func_sigs = self._get_signatures(block_info.tree, functions, 'function')
        method_sigs = self._get_signatures(block_info.tree, methods, 'method')

        # Отделяем функции с self (потенциальные методы)
        func_with_self = {name for name, sig in func_sigs.items() 
                          if sig[0] and sig[1] and sig[1][0] in ('self', 'cls')}
        func_without_self = functions - func_with_self

        logger.info(f"  Классы: {classes}")
        logger.info(f"  Методы: {methods}")
        logger.info(f"  Функции (с self): {func_with_self}")
        logger.info(f"  Функции (без self): {func_without_self}")

        # --- Приоритет 1: поиск по классам ---
        if classes:
            module = self._find_by_classes(classes)
            if module:
                logger.info(f"  -> НАЙДЕН ПО КЛАССУ: {module}")
                self.auto_assign[block_info.block_id] = module
                return True, module, None

        # --- Приоритет 2: поиск по методам (включая функции с self) ---
        method_names = methods | func_with_self
        if method_names:
            module, had_candidates = self._find_by_methods_strict(method_names, method_sigs, func_sigs, block_info.content)
            if had_candidates:
                if module:
                    logger.info(f"  -> НАЙДЕН ПО МЕТОДУ: {module}")
                    self.auto_assign[block_info.block_id] = module
                    return True, module, None
                else:
                    # Были кандидаты, но не один – неоднозначность
                    logger.info(f"  -> НЕОДНОЗНАЧНО ПО МЕТОДАМ, требуется диалог")
                    self.need_dialog.append(block_info)
                    return False, None, None
            # Если кандидатов не было, переходим к функциям

        # --- Приоритет 3: поиск по функциям (без self) ---
        if func_without_self:
            module = self._find_by_functions(func_without_self, func_sigs)
            if module:
                logger.info(f"  -> НАЙДЕН ПО ФУНКЦИИ: {module}")
                self.auto_assign[block_info.block_id] = module
                return True, module, None

        logger.info(f"  -> НЕ ОПРЕДЕЛЕН")
        self.need_dialog.append(block_info)
        return False, None, None

    def _extract_identifiers(self, node: Node):
        classes, functions, methods = set(), set(), set()
        for child in node.children:
            if child.node_type == "class":
                classes.add(child.name)
                for m in child.children:
                    if m.node_type == "method":
                        methods.add(m.name)
            elif child.node_type == "function":
                functions.add(child.name)
            elif child.node_type == "method":
                methods.add(child.name)
            else:
                c, f, m = self._extract_identifiers(child)
                classes.update(c)
                functions.update(f)
                methods.update(m)
        return classes, functions, methods

    def _get_signatures(self, tree: Node, names: Set[str], node_type: str) -> Dict[str, Tuple[bool, List[str]]]:
        signatures = {}
        for name in names:
            node = self._find_node(tree, name, node_type)
            if node:
                signatures[name] = extract_function_signature(node)
        return signatures

    def _find_node(self, node: Node, name: str, node_type: str) -> Optional[Node]:
        if node.name == name and node.node_type == node_type:
            return node
        for child in node.children:
            result = self._find_node(child, name, node_type)
            if result:
                return result
        return None

    def _find_by_classes(self, classes: Set[str]) -> Optional[str]:
        for class_name in classes:
            module = self.module_identifier.find_module_for_class(class_name)
            if module:
                logger.debug(f"    Класс {class_name} найден в {module}")
                return module
        return None

    def _extract_called_methods(self, content):
        called = set()
        called.update(re.findall(r'self\.(\w+)\s*\(', content))
        called.update(re.findall(r'cls\.(\w+)\s*\(', content))
        return called

    def _find_by_methods_strict(self, method_names, method_sigs, func_sigs, content):
        """
        Возвращает (модуль, были_ли_кандидаты)
        Если модуль не None – единственный кандидат.
        Если модуль None, но были_ли_кандидаты=True – несколько кандидатов (неоднозначность).
        Если были_ли_кандидаты=False – кандидатов нет.
        """
        candidate_modules = set()
        found_any = False

        for name in method_names:
            # Определяем сигнатуру искомого метода
            if name in method_sigs:
                target_sig = method_sigs[name]
            elif name in func_sigs:
                target_sig = func_sigs[name]
            else:
                continue

            # Проверяем, что это метод с self (иначе пропускаем)
            if not (target_sig[0] and target_sig[1] and target_sig[1][0] in ('self', 'cls')):
                continue

            target_count = len(target_sig[1]) - 1  # количество параметров без self
            logger.debug(f"Поиск метода '{name}' в модулях. Целевая сигнатура: {target_sig}, параметров без self: {target_count}")

            # Перебираем все модули и их классы через новый API
            for module_name in self.module_identifier.get_all_module_names():
                module = self.module_identifier.get_module_info(module_name)
                if not module:
                    continue
                for class_name, class_info in module.classes.items():
                    method_info = class_info.methods.get(name)
                    if not method_info:
                        continue
                    cand_sig = method_info.signature

                    # Проверяем, что метод в классе тоже имеет self
                    if not (cand_sig[0] and cand_sig[1] and cand_sig[1][0] in ('self', 'cls')):
                        continue

                    cand_count = len(cand_sig[1]) - 1
                    if target_count != cand_count:
                        continue

                    candidate_modules.add(module_name)
                    found_any = True

        if not found_any:
            return None, False
        if len(candidate_modules) == 1:
            return next(iter(candidate_modules)), True
        logger.info(f"Неоднозначность: найдено несколько модулей-кандидатов: {candidate_modules}")
        return None, True

    def _find_by_functions(self, func_names, func_sigs):
        # Сначала соберём все имена методов из классов (с self), чтобы исключить их из функций
        method_names_from_classes = set()
        for module_name in self.module_identifier.get_all_module_names():
            module = self.module_identifier.get_module_info(module_name)
            if not module:
                continue
            for class_info in module.classes.values():
                for method_info in class_info.methods.values():
                    if method_info.signature[0] and method_info.signature[1] and method_info.signature[1][0] in ('self', 'cls'):
                        method_names_from_classes.add(method_info.name)

        candidates = set()
        for name in func_names:
            # Если это имя уже есть как метод в каком-то классе – игнорируем как функцию
            if name in method_names_from_classes:
                logger.debug(f"Имя {name} есть как метод в классе, пропускаем при поиске функций")
                continue
            if name not in func_sigs:
                continue
            target_sig = func_sigs[name]
            target_params = target_sig[1]
            if target_sig[0] and target_params and target_params[0] in ('self', 'cls'):
                target_params = target_params[1:]

            for module_name in self.module_identifier.get_all_module_names():
                module = self.module_identifier.get_module_info(module_name)
                if not module:
                    continue
                func_info = module.functions.get(name)
                if not func_info:
                    continue
                cand_sig = func_info.signature
                cand_params = cand_sig[1]
                if cand_sig[0] and cand_params and cand_params[0] in ('self', 'cls'):
                    cand_params = cand_params[1:]
                if len(target_params) == len(cand_params):
                    candidates.add(module_name)

        if len(candidates) == 1:
            return next(iter(candidates))
        return None

    def get_auto_assignments(self):
        return self.auto_assign.copy()

    def get_need_dialog(self):
        return self.need_dialog.copy()

    def clear_temp_data(self):
        self.auto_assign.clear()
        self.need_dialog.clear()