# aichat_search/tools/code_structure/core/resolution_strategy.py

from abc import ABC, abstractmethod
from typing import Optional, Set, Dict, List, Tuple
import logging

from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.models.node import Node
from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier
from aichat_search.tools.code_structure.core.signature_utils import extract_function_signature

logger = logging.getLogger(__name__)


class ResolutionStrategy(ABC):
    """Базовый класс для стратегий разрешения модуля."""

    def __init__(self):
        self.ambiguous = False

    @abstractmethod
    def resolve(self, block: MessageBlockInfo, identifier: ModuleIdentifier) -> Optional[str]:
        """
        Пытается определить модуль для блока.
        Возвращает имя модуля или None.
        В случае неоднозначности устанавливает self.ambiguous = True и возвращает None.
        """
        pass

    def get_signatures(self, tree: Node, names: Set[str], node_type: str) -> Dict[str, Tuple[bool, List[str]]]:
        """Вспомогательный метод для извлечения сигнатур."""
        sigs = {}
        for name in names:
            node = self._find_node(tree, name, node_type)
            if node:
                sigs[name] = extract_function_signature(node)
        return sigs

    def _find_node(self, node: Node, name: str, node_type: str) -> Optional[Node]:
        if node.name == name and node.node_type == node_type:
            return node
        for child in node.children:
            result = self._find_node(child, name, node_type)
            if result:
                return result
        return None


class ClassStrategy(ResolutionStrategy):
    """Стратегия поиска по именам классов."""

    def resolve(self, block: MessageBlockInfo, identifier: ModuleIdentifier) -> Optional[str]:
        self.ambiguous = False
        classes = self._extract_classes(block.tree)
        if not classes:
            return None

        for class_name in classes:
            module = identifier.find_module_for_class(class_name)
            if module:
                logger.debug(f"ClassStrategy: класс {class_name} найден в {module}")
                return module
        return None

    def _extract_classes(self, node: Node) -> Set[str]:
        classes = set()
        for child in node.children:
            if child.node_type == "class":
                classes.add(child.name)
            else:
                classes.update(self._extract_classes(child))
        return classes


class MethodStrategy(ResolutionStrategy):
    """Стратегия поиска по методам (включая функции с self)."""

    def resolve(self, block: MessageBlockInfo, identifier: ModuleIdentifier) -> Optional[str]:
        self.ambiguous = False
        methods, funcs_with_self = self._extract_methods_and_funcs_with_self(block.tree)

        if not methods and not funcs_with_self:
            return None

        method_sigs = self.get_signatures(block.tree, methods, 'method')
        func_sigs = self.get_signatures(block.tree, funcs_with_self, 'function')

        # Единый модуль-кандидат, если все имена указывают на один и тот же модуль
        common_module = None

        for name in methods | funcs_with_self:
            if name in method_sigs:
                target_sig = method_sigs[name]
            else:
                target_sig = func_sigs[name]

            if not (target_sig[0] and target_sig[1] and target_sig[1][0] in ('self', 'cls')):
                continue

            target_params_count = len(target_sig[1]) - 1
            candidates_for_name = set()

            for mod_name in identifier.get_all_module_names():
                module = identifier.get_module_info(mod_name)
                if not module:
                    continue
                for class_info in module.classes.values():
                    method_info = class_info.methods.get(name)
                    if not method_info:
                        continue
                    cand_sig = method_info.signature
                    if not (cand_sig[0] and cand_sig[1] and cand_sig[1][0] in ('self', 'cls')):
                        continue
                    cand_params_count = len(cand_sig[1]) - 1
                    if target_params_count == cand_params_count:
                        candidates_for_name.add(mod_name)

            # Если для текущего имени нет кандидатов, пропускаем
            if not candidates_for_name:
                continue

            # Если несколько кандидатов для одного имени – неоднозначность
            if len(candidates_for_name) > 1:
                self.ambiguous = True
                logger.info(f"MethodStrategy: несколько кандидатов для {name}: {candidates_for_name}")
                return None

            # Получаем единственный модуль для этого имени
            module_for_name = next(iter(candidates_for_name))

            # Если это первое имя с кандидатом, запоминаем
            if common_module is None:
                common_module = module_for_name
            # Если модуль для текущего имени отличается от предыдущего – неоднозначность
            elif common_module != module_for_name:
                self.ambiguous = True
                logger.info(f"MethodStrategy: имена указывают на разные модули: {common_module} и {module_for_name}")
                return None

        # Если ни одного имени не дало кандидатов
        if common_module is None:
            return None

        return common_module

    def _extract_methods_and_funcs_with_self(self, node: Node):
        methods = set()
        funcs_with_self = set()
        for child in node.children:
            if child.node_type == "class":
                for m in child.children:
                    if m.node_type == "method":
                        methods.add(m.name)
            elif child.node_type == "function":
                funcs_with_self.add(child.name)
            elif child.node_type == "method":
                methods.add(child.name)
            else:
                m, f = self._extract_methods_and_funcs_with_self(child)
                methods.update(m)
                funcs_with_self.update(f)
        return methods, funcs_with_self


class FunctionStrategy(ResolutionStrategy):
    """Стратегия поиска по функциям (без self)."""

    def resolve(self, block: MessageBlockInfo, identifier: ModuleIdentifier) -> Optional[str]:
        self.ambiguous = False
        func_names = self._extract_functions(block.tree)
        if not func_names:
            return None

        func_sigs = self.get_signatures(block.tree, func_names, 'function')

        # Собираем имена методов из классов, чтобы исключить их
        method_names_from_classes = set()
        for mod_name in identifier.get_all_module_names():
            module = identifier.get_module_info(mod_name)
            if not module:
                continue
            for class_info in module.classes.values():
                for method_info in class_info.methods.values():
                    if method_info.signature[0] and method_info.signature[1] and method_info.signature[1][0] in ('self', 'cls'):
                        method_names_from_classes.add(method_info.name)

        candidates = set()
        for name in func_names:
            if name in method_names_from_classes:
                logger.debug(f"FunctionStrategy: имя {name} есть как метод, пропускаем")
                continue
            if name not in func_sigs:
                continue
            target_sig = func_sigs[name]
            target_params = target_sig[1]
            if target_sig[0] and target_params and target_params[0] in ('self', 'cls'):
                target_params = target_params[1:]

            for mod_name in identifier.get_all_module_names():
                module = identifier.get_module_info(mod_name)
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
                    candidates.add(mod_name)

        if len(candidates) == 1:
            return next(iter(candidates))
        elif len(candidates) > 1:
            self.ambiguous = True
            logger.info(f"FunctionStrategy: несколько кандидатов для функций: {candidates}")
        return None

    def _extract_functions(self, node: Node) -> Set[str]:
        funcs = set()
        for child in node.children:
            if child.node_type == "function":
                funcs.add(child.name)
            else:
                funcs.update(self._extract_functions(child))
        return funcs