# aichat_search/tools/code_structure/core/module_resolver.py

from typing import Set, Dict, Any, List, Optional, Tuple
import logging
import sys
from aichat_search.tools.code_structure.models.node import Node
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.core.signature_utils import compare_signatures, extract_function_signature
from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier

# Настройка логирования
logger = logging.getLogger(__name__)
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.DEBUG)
console.setFormatter(logging.Formatter('%(asctime)s - RESOLVER - %(levelname)s - %(message)s'))
logger.addHandler(console)
logger.setLevel(logging.DEBUG)


class ModuleResolver:
    """Определяет модули для блоков на основе идентификаторов и сигнатур."""

    def __init__(self, module_identifier: ModuleIdentifier):
        self.module_identifier = module_identifier
        self.auto_assign: Dict[str, str] = {}  # block_id -> module_name
        self.need_dialog: List[MessageBlockInfo] = []

    def resolve_block(self, block_info: MessageBlockInfo) -> Tuple[bool, Optional[str]]:
        """
        Пытается определить модуль для блока.
        Возвращает (определён, имя_модуля) или (False, None) если требуется диалог.
        """
        logger.info(f"=== resolve_block для {block_info.block_id} ===")

        if block_info.tree is None or block_info.syntax_error:
            logger.info(f"  Блок имеет ошибку или пустое дерево")
            return False, None

        # Анализируем содержимое блока
        block_classes, block_functions, block_methods = self._extract_block_identifiers(block_info.tree)

        logger.info(f"  Классы в блоке: {block_classes}")
        logger.info(f"  Функции в блоке: {block_functions}")
        logger.info(f"  Методы в блоке: {block_methods}")

        # Собираем сигнатуры
        func_sigs = self._collect_function_signatures(block_info.tree, block_functions)
        method_sigs = self._collect_method_signatures(block_info.tree, block_methods)

        for func_name, (has_self, params) in func_sigs.items():
            logger.info(f"  Сигнатура функции {func_name}: has_self={has_self}, params={params}")

        for method_name, (has_self, params) in method_sigs.items():
            logger.info(f"  Сигнатура метода {method_name}: has_self={has_self}, params={params}")

        # Находим возможные модули по имени и сигнатуре
        possible_modules = self._find_possible_modules(
            block_classes, func_sigs, method_sigs
        )

        logger.info(f"  Найдено возможных модулей: {possible_modules}")

        if len(possible_modules) == 1:
            module_name = possible_modules.pop()
            logger.info(f"  -> ОДНОЗНАЧНОЕ ОПРЕДЕЛЕНИЕ МОДУЛЯ: {module_name}")
            return True, module_name
        elif len(possible_modules) > 1:
            logger.info(f"  -> НЕСКОЛЬКО ВАРИАНТОВ: {possible_modules}")
            return False, None
        else:
            logger.info(f"  -> НЕТ ВАРИАНТОВ")
            return False, None

    def _extract_block_identifiers(self, node: Node) -> Tuple[Set[str], Set[str], Set[str]]:
        """Извлекает из блока множества классов, функций и методов."""
        classes = set()
        functions = set()
        methods = set()

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
                sub_classes, sub_functions, sub_methods = self._extract_block_identifiers(child)
                classes.update(sub_classes)
                functions.update(sub_functions)
                methods.update(sub_methods)

        return classes, functions, methods

    def _collect_function_signatures(self, tree: Node, func_names: Set[str]) -> Dict[str, Tuple[bool, List[str]]]:
        """Собирает сигнатуры для функций в блоке."""
        signatures = {}
        for func_name in func_names:
            func_node = self._find_node_by_name(tree, func_name, 'function')
            if func_node:
                signatures[func_name] = extract_function_signature(func_node)
        return signatures

    def _collect_method_signatures(self, tree: Node, method_names: Set[str]) -> Dict[str, Tuple[bool, List[str]]]:
        """Собирает сигнатуры для методов в блоке."""
        signatures = {}
        for method_name in method_names:
            method_node = self._find_node_by_name(tree, method_name, 'method')
            if method_node:
                signatures[method_name] = extract_function_signature(method_node)
        return signatures

    def _find_node_by_name(self, node: Node, name: str, node_type: str) -> Optional[Node]:
        """Ищет узел по имени и типу."""
        if node.name == name and node.node_type == node_type:
            return node
        for child in node.children:
            result = self._find_node_by_name(child, name, node_type)
            if result:
                return result
        return None

    def _find_possible_modules(self,
                               block_classes: Set[str],
                               block_func_sigs: Dict[str, Tuple[bool, List[str]]],
                               block_method_sigs: Dict[str, Tuple[bool, List[str]]]) -> Set[str]:
        """Находит возможные модули для блока."""
        possible_modules = set()

        logger.debug("Поиск возможных модулей:")

        # Поиск по классам
        for class_name in block_classes:
            module = self.module_identifier.find_module_for_class(class_name)
            if module:
                possible_modules.add(module)
                logger.debug(f"  Класс {class_name} найден в модуле {module}")

        # Поиск по методам (с учётом классов из этого же блока)
        for method_name, method_sig in block_method_sigs.items():
            # Сначала ищем методы в классах из этого же блока
            found = False
            for class_name in block_classes:
                module = self.module_identifier.find_module_for_method_with_class(
                    method_name, method_sig, class_name
                )
                if module:
                    possible_modules.add(module)
                    logger.debug(f"  Метод {method_name} из класса {class_name} найден в модуле {module}")
                    found = True
                    break

            if not found:
                # Если не нашли в конкретном классе, ищем среди всех методов
                module = self.module_identifier.find_module_for_method(method_name, method_sig)
                if module:
                    possible_modules.add(module)
                    logger.debug(f"  Метод {method_name} найден в модуле {module} (без учёта класса)")
                else:
                    # Если метод не найден, ищем среди функций
                    module = self.module_identifier.find_module_for_function(method_name, method_sig)
                    if module:
                        possible_modules.add(module)
                        logger.debug(f"  Метод {method_name} найден как функция в модуле {module}")

        # Поиск по функциям
        for func_name, func_sig in block_func_sigs.items():
            module = self.module_identifier.find_module_for_function(func_name, func_sig)
            if module:
                possible_modules.add(module)
                logger.debug(f"  Функция {func_name} найдена в модуле {module}")
            else:
                # Если функция не найдена, ищем среди методов
                module = self.module_identifier.find_module_for_method(func_name, func_sig)
                if module:
                    possible_modules.add(module)
                    logger.debug(f"  Функция {func_name} найдена как метод в модуле {module}")

        return possible_modules