# aichat_search/tools/code_structure/core/module_resolver.py

from typing import Set, Dict, Any, List, Optional, Tuple
import logging
from aichat_search.tools.code_structure.models.node import Node
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.core.signature_utils import compare_signatures, extract_function_signature
from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier

logger = logging.getLogger(__name__)

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
        logger.debug(f"resolve_block для {block_info.block_id}")
        
        if block_info.tree is None or block_info.syntax_error:
            logger.debug(f"  Блок имеет ошибку или пустое дерево")
            return False, None
        
        # Анализируем содержимое блока
        block_classes, block_functions, block_methods = self._extract_block_identifiers(block_info.tree)
        
        logger.debug(f"  Классы в блоке: {block_classes}")
        logger.debug(f"  Функции в блоке: {block_functions}")
        logger.debug(f"  Методы в блоке: {block_methods}")
        
        # Собираем сигнатуры
        func_sigs = self._collect_function_signatures(block_info.tree, block_functions)
        method_sigs = self._collect_method_signatures(block_info.tree, block_methods)
        
        for func_name, (has_self, params) in func_sigs.items():
            logger.debug(f"  Сигнатура функции {func_name}: has_self={has_self}, params={params}")
        
        for method_name, (has_self, params) in method_sigs.items():
            logger.debug(f"  Сигнатура метода {method_name}: has_self={has_self}, params={params}")
        
        # Находим возможные модули по имени и сигнатуре (НЕ по содержимому)
        possible_modules = self._find_possible_modules(
            block_classes, func_sigs, method_sigs
        )
        
        logger.debug(f"  Найдено возможных модулей: {possible_modules}")
        
        if len(possible_modules) == 1:
            module_name = possible_modules.pop()
            logger.info(f"  -> ОДНОЗНАЧНОЕ ОПРЕДЕЛЕНИЕ МОДУЛЯ: {module_name} (по имени и сигнатуре)")
            return True, module_name
        elif len(possible_modules) > 1:
            logger.debug(f"  -> НЕСКОЛЬКО ВАРИАНТОВ: {possible_modules}")
            return False, None
        else:
            logger.debug(f"  -> НЕТ ВАРИАНТОВ")
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
        module_ids = self.module_identifier.get_module_ids()
        
        # Проверка классов
        for class_name in block_classes:
            for module, ids in module_ids.items():
                if class_name in ids['classes']:
                    possible_modules.add(module)
        
        # Проверка функций (включая методы без класса) - ПО ИМЕНИ И СИГНАТУРЕ
        for func_name, func_sig in block_func_sigs.items():
            for module, ids in module_ids.items():
                # Ищем среди функций верхнего уровня
                if func_name in ids['functions']:
                    # ДЛЯ ОПРЕДЕЛЕНИЯ МОДУЛЯ ДОСТАТОЧНО СОВПАДЕНИЯ ИМЕНИ И СИГНАТУРЫ
                    for func_info in ids['functions'][func_name]:
                        # Сравниваем только имя и сигнатуру (has_self и параметры)
                        if func_sig[0] == func_info['signature'][0]:  # одинаковое наличие self
                            if func_sig[1] == func_info['signature'][1]:  # одинаковые параметры
                                possible_modules.add(module)
                                logger.debug(f"      Функция {func_name}: найдено совпадение по сигнатуре в модуле {module}")
                                break
                
                # Ищем среди методов классов
                if func_name in ids['methods']:
                    for method_info in ids['methods'][func_name]:
                        # Сравниваем только имя и сигнатуру
                        if func_sig[0] == method_info['signature'][0]:
                            if func_sig[1] == method_info['signature'][1]:
                                possible_modules.add(module)
                                logger.debug(f"      Функция {func_name}: найдено совпадение с методом в модуле {module}")
                                break
        
        # Проверка методов
        for method_name, method_sig in block_method_sigs.items():
            for module, ids in module_ids.items():
                if method_name in ids['methods']:
                    for method_info in ids['methods'][method_name]:
                        if method_sig[0] == method_info['signature'][0]:
                            if method_sig[1] == method_info['signature'][1]:
                                possible_modules.add(module)
                                logger.debug(f"      Метод {method_name}: найдено совпадение по сигнатуре в модуле {module}")
                                break
                if method_name in ids['functions']:
                    for func_info in ids['functions'][method_name]:
                        if method_sig[0] == func_info['signature'][0]:
                            if method_sig[1] == func_info['signature'][1]:
                                possible_modules.add(module)
                                logger.debug(f"      Метод {method_name}: найдено совпадение с функцией в модуле {module}")
                                break
        
        return possible_modules