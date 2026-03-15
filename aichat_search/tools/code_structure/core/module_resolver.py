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
    Определитель модулей с учётом контекста и сигнатур.
    При неоднозначности возвращает None.
    """

    def __init__(self, module_identifier: ModuleIdentifier):
        self.module_identifier = module_identifier
        self.auto_assign: Dict[str, str] = {}
        self.need_dialog: List[MessageBlockInfo] = []

    def resolve_block(self, block_info: MessageBlockInfo) -> Tuple[bool, Optional[str]]:
        logger.info(f"=== resolve_block для {block_info.block_id} ===")

        if block_info.tree is None or block_info.syntax_error:
            logger.info(f"  Блок имеет ошибку или пустое дерево")
            return False, None

        classes, functions, methods = self._extract_identifiers(block_info.tree)
        func_sigs = self._get_signatures(block_info.tree, functions, 'function')
        method_sigs = self._get_signatures(block_info.tree, methods, 'method')

        logger.info(f"  Классы: {classes}")
        logger.info(f"  Функции: {functions}")
        logger.info(f"  Методы: {methods}")

        # 1. Поиск по классам
        if classes:
            module = self._find_by_classes(classes)
            if module:
                logger.info(f"  -> НАЙДЕН ПО КЛАССУ: {module}")
                self.auto_assign[block_info.block_id] = module
                return True, module

        # 2. Поиск по методам
        if methods:
            module = self._find_by_methods(methods, method_sigs, block_info.content)
            if module:
                logger.info(f"  -> НАЙДЕН ПО МЕТОДУ: {module}")
                self.auto_assign[block_info.block_id] = module
                return True, module

        # 3. Поиск по функциям
        if functions:
            module = self._find_by_functions(functions, func_sigs, block_info.content)
            if module:
                logger.info(f"  -> НАЙДЕН ПО ФУНКЦИИ: {module}")
                self.auto_assign[block_info.block_id] = module
                return True, module

        logger.info(f"  -> НЕ ОПРЕДЕЛЕН")
        self.need_dialog.append(block_info)
        return False, None

    def _extract_identifiers(self, node: Node) -> Tuple[Set[str], Set[str], Set[str]]:
        classes, functions, methods = set(), set(), set()
        for child in node.children:
            if child.node_type == "class":
                classes.add(child.name)
                for method in child.children:
                    if method.node_type == "method":
                        methods.add(method.name)
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

    def _extract_called_methods(self, content: str) -> Set[str]:
        called = set()
        matches = re.findall(r'self\.(\w+)\s*\(', content)
        called.update(matches)
        matches = re.findall(r'cls\.(\w+)\s*\(', content)
        called.update(matches)
        return called

    def _find_by_methods(self, methods: Set[str], method_sigs: Dict[str, Tuple[bool, List[str]]], content: str) -> Optional[str]:
        has_self = 'self.' in content or 'cls.' in content
        called_methods = self._extract_called_methods(content) if has_self else set()

        candidates = []  # (module_name, score)

        for method_name in methods:
            if method_name not in method_sigs:
                continue
            target_sig = method_sigs[method_name]
            target_params = target_sig[1]
            if target_sig[0] and target_params and target_params[0] in ('self', 'cls'):
                target_params = target_params[1:]

            for module, ids in self.module_identifier.get_module_ids().items():
                # Поиск в классах
                for class_name, class_info in ids.get('classes', {}).items():
                    for method_info in class_info.get('methods', []):
                        if method_info['name'] != method_name:
                            continue
                        cand_sig = method_info['signature']
                        cand_params = cand_sig[1]
                        if cand_sig[0] and cand_params and cand_params[0] in ('self', 'cls'):
                            cand_params = cand_params[1:]
                        # Подсчёт совпадающих параметров
                        matches = sum(1 for a, b in zip(target_params, cand_params) if a == b)
                        # Учитываем бонус за вызываемые методы (те, что есть в этом классе)
                        bonus = 0
                        if called_methods:
                            class_methods = {m['name'] for m in class_info.get('methods', [])}
                            bonus = len(called_methods & class_methods) * 2
                        total = matches + bonus
                        candidates.append((module, total))

                # Поиск в общем списке methods (если нужно)
                for method_key, mlist in ids.get('methods', {}).items():
                    for method_info in mlist:
                        if method_info['name'] != method_name:
                            continue
                        cand_sig = method_info['signature']
                        cand_params = cand_sig[1]
                        if cand_sig[0] and cand_params and cand_params[0] in ('self', 'cls'):
                            cand_params = cand_params[1:]
                        matches = sum(1 for a, b in zip(target_params, cand_params) if a == b)
                        # Для методов без класса бонус не считаем
                        candidates.append((module, matches))

        if not candidates:
            return None

        # Группируем по модулю и суммируем баллы
        module_scores = defaultdict(int)
        for module, score in candidates:
            module_scores[module] += score

        # Находим максимальный балл
        max_score = max(module_scores.values())
        best_modules = [m for m, s in module_scores.items() if s == max_score]

        if len(best_modules) == 1:
            logger.debug(f"    Лучший кандидат по методу: {best_modules[0]} (score: {max_score})")
            return best_modules[0]
        else:
            logger.debug(f"    Неоднозначно: несколько модулей с одинаковым score {max_score}: {best_modules}")
            return None

    def _find_by_functions(self, functions: Set[str], func_sigs: Dict[str, Tuple[bool, List[str]]], content: str) -> Optional[str]:
        has_self = 'self.' in content or 'cls.' in content
        candidates = []

        for func_name in functions:
            if func_name not in func_sigs:
                continue
            target_sig = func_sigs[func_name]
            target_params = target_sig[1]
            if target_sig[0] and target_params and target_params[0] in ('self', 'cls'):
                target_params = target_params[1:]

            # Если есть self в теле, ищем только как метод (игнорируем функции)
            if has_self:
                # Поиск как метод
                for module, ids in self.module_identifier.get_module_ids().items():
                    for method_key, mlist in ids.get('methods', {}).items():
                        for method_info in mlist:
                            if method_info['name'] == func_name:
                                cand_sig = method_info['signature']
                                cand_params = cand_sig[1]
                                if cand_sig[0] and cand_params and cand_params[0] in ('self', 'cls'):
                                    cand_params = cand_params[1:]
                                matches = sum(1 for a, b in zip(target_params, cand_params) if a == b)
                                candidates.append((module, matches))
            else:
                # Ищем как функцию
                for module, ids in self.module_identifier.get_module_ids().items():
                    if func_name in ids.get('functions', {}):
                        for func_info in ids['functions'][func_name]:
                            cand_sig = func_info['signature']
                            cand_params = cand_sig[1]
                            if cand_sig[0] and cand_params and cand_params[0] in ('self', 'cls'):
                                cand_params = cand_params[1:]
                            matches = sum(1 for a, b in zip(target_params, cand_params) if a == b)
                            candidates.append((module, matches))

        if not candidates:
            return None

        module_scores = defaultdict(int)
        for module, score in candidates:
            module_scores[module] += score

        max_score = max(module_scores.values())
        best_modules = [m for m, s in module_scores.items() if s == max_score]

        if len(best_modules) == 1:
            logger.debug(f"    Лучший кандидат по функции: {best_modules[0]} (score: {max_score})")
            return best_modules[0]
        else:
            logger.debug(f"    Неоднозначно: несколько модулей с одинаковым score {max_score}: {best_modules}")
            return None

    def get_auto_assignments(self) -> Dict[str, str]:
        return self.auto_assign.copy()

    def get_need_dialog(self) -> List[MessageBlockInfo]:
        return self.need_dialog.copy()

    def clear_temp_data(self):
        self.auto_assign.clear()
        self.need_dialog.clear()