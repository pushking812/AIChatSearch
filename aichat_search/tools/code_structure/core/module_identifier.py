# aichat_search/tools/code_structure/core/module_identifier.py

from typing import Dict, Any, Set, Tuple, Optional, List
from collections import defaultdict
from aichat_search.tools.code_structure.models.node import Node
from aichat_search.tools.code_structure.core.signature_utils import extract_function_signature

class ModuleIdentifier:
    """Собирает и хранит идентификаторы модулей с сигнатурами."""

    def __init__(self):
        self.module_ids: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'classes': {},      # имя класса -> информация о классе и его методах
            'functions': {},     # имя функции -> список сигнатур
            'methods': {}        # имя метода -> список {'class': имя_класса, 'signature': сигнатура}
        })

    def collect_from_tree(self, node: Node, module_name: str):
        """Рекурсивно собирает все идентификаторы из дерева узлов."""
        for child in node.children:
            if child.node_type == "class":
                self._add_class(child, module_name)
                # Собираем методы внутри класса
                for method in child.children:
                    if method.node_type == "method":
                        self._add_method(method, module_name, child.name)
            elif child.node_type == "function":
                self._add_function(child, module_name)
            elif child.node_type == "method":
                # Собираем методы, даже если они не в классе
                self._add_method(child, module_name, "unknown_class")
            else:
                self.collect_from_tree(child, module_name)

    def _add_class(self, class_node: Node, module_name: str):
        """Добавляет класс и собирает все его методы."""
        class_info = {
            'name': class_node.name,
            'methods': []
        }

        # Собираем все методы класса
        for method in class_node.children:
            if method.node_type == "method":
                sig = extract_function_signature(method)
                class_info['methods'].append({
                    'name': method.name,
                    'signature': sig
                })
                # Также добавляем метод в общий список методов
                self._add_method(method, module_name, class_node.name)

        self.module_ids[module_name]['classes'][class_node.name] = class_info

    def _add_method(self, method_node: Node, module_name: str, class_name: str):
        """Добавляет метод в общий список методов."""
        if 'methods' not in self.module_ids[module_name]:
            self.module_ids[module_name]['methods'] = {}

        sig = extract_function_signature(method_node)
        method_key = f"{class_name}.{method_node.name}" if class_name != "unknown_class" else method_node.name

        if method_key not in self.module_ids[module_name]['methods']:
            self.module_ids[module_name]['methods'][method_key] = []

        self.module_ids[module_name]['methods'][method_key].append({
            'class': class_name,
            'name': method_node.name,
            'signature': sig
        })

    def _add_function(self, func_node: Node, module_name: str):
        """Добавляет функцию верхнего уровня."""
        if 'functions' not in self.module_ids[module_name]:
            self.module_ids[module_name]['functions'] = {}

        sig = extract_function_signature(func_node)
        if func_node.name not in self.module_ids[module_name]['functions']:
            self.module_ids[module_name]['functions'][func_node.name] = []

        self.module_ids[module_name]['functions'][func_node.name].append({
            'signature': sig
        })

    def find_module_for_method(self, method_name: str, signature: Tuple[bool, List[str]]) -> Optional[str]:
        """Ищет модуль, содержащий метод с указанным именем и сигнатурой."""
        for module, ids in self.module_ids.items():
            # Ищем во всех методах (включая методы классов)
            for method_key, methods in ids.get('methods', {}).items():
                for method_info in methods:
                    if method_info['name'] == method_name:
                        if (method_info['signature'][0] == signature[0] and
                            method_info['signature'][1] == signature[1]):
                            return module
        return None

    def find_module_for_method_with_class(self, method_name: str, signature: Tuple[bool, List[str]], class_name: Optional[str] = None) -> Optional[str]:
        """Ищет модуль, содержащий метод с указанным именем и сигнатурой, optionally в указанном классе."""
        for module, ids in self.module_ids.items():
            # Ищем во всех методах
            for method_key, methods in ids.get('methods', {}).items():
                for method_info in methods:
                    if method_info['name'] == method_name:
                        # Если указан класс, проверяем соответствие
                        if class_name and method_info['class'] != class_name:
                            continue
                        if (method_info['signature'][0] == signature[0] and
                            method_info['signature'][1] == signature[1]):
                            return module
        return None

    def find_module_for_function(self, func_name: str, signature: Tuple[bool, List[str]]) -> Optional[str]:
        """Ищет модуль, содержащий функцию с указанным именем и сигнатурой."""
        for module, ids in self.module_ids.items():
            if func_name in ids.get('functions', {}):
                for func_info in ids['functions'][func_name]:
                    if (func_info['signature'][0] == signature[0] and
                        func_info['signature'][1] == signature[1]):
                        return module
        return None

    def find_module_for_class(self, class_name: str) -> Optional[str]:
        """Ищет модуль, содержащий класс с указанным именем."""
        for module, ids in self.module_ids.items():
            if class_name in ids.get('classes', {}):
                return module
        return None

    def get_module_ids(self) -> Dict[str, Dict[str, Any]]:
        return dict(self.module_ids)

    def get_known_modules(self) -> Set[str]:
        return set(self.module_ids.keys())
        
    def remove_temp_modules(self):
        """Удаляет все временные модули (с префиксом temp_)."""
        to_remove = [m for m in self.module_ids.keys() if m.startswith('temp_')]
        for m in to_remove:
            del self.module_ids[m]
        if to_remove:
            logger.info(f"Удалены временные модули: {to_remove}")