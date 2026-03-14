# aichat_search/tools/code_structure/core/module_identifier.py

from typing import Dict, Any, Set, Tuple, Optional
from collections import defaultdict
from aichat_search.tools.code_structure.models.node import Node
from aichat_search.tools.code_structure.core.signature_utils import extract_function_signature

class ModuleIdentifier:
    """Собирает и хранит идентификаторы модулей с сигнатурами."""
    
    def __init__(self):
        self.module_ids: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'classes': {},
            'functions': {},
            'methods': {}
        })
    
    def collect_from_tree(self, node: Node, module_name: str):
        """Рекурсивно собирает идентификаторы из дерева узлов."""
        for child in node.children:
            if child.node_type == "class":
                self._add_class(child, module_name)
                for method in child.children:
                    if method.node_type == "method":
                        self._add_method(method, module_name, child.name)
            elif child.node_type == "function":
                self._add_function(child, module_name)
            else:
                self.collect_from_tree(child, module_name)
    
    def _add_class(self, class_node: Node, module_name: str):
        if 'classes' not in self.module_ids[module_name]:
            self.module_ids[module_name]['classes'] = {}
        self.module_ids[module_name]['classes'][class_node.name] = {'signatures': {}}
    
    def _add_method(self, method_node: Node, module_name: str, class_name: str):
        if 'methods' not in self.module_ids[module_name]:
            self.module_ids[module_name]['methods'] = {}
        sig = extract_function_signature(method_node)
        if method_node.name not in self.module_ids[module_name]['methods']:
            self.module_ids[module_name]['methods'][method_node.name] = []
        self.module_ids[module_name]['methods'][method_node.name].append({
            'class': class_name,
            'signature': sig
        })
    
    def _add_function(self, func_node: Node, module_name: str):
        if 'functions' not in self.module_ids[module_name]:
            self.module_ids[module_name]['functions'] = {}
        sig = extract_function_signature(func_node)
        if func_node.name not in self.module_ids[module_name]['functions']:
            self.module_ids[module_name]['functions'][func_node.name] = []
        self.module_ids[module_name]['functions'][func_node.name].append({
            'signature': sig
        })
    
    def get_module_ids(self) -> Dict[str, Dict[str, Any]]:
        return dict(self.module_ids)
    
    def get_known_modules(self) -> Set[str]:
        return set(self.module_ids.keys())