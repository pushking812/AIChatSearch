# code_structure/module_resolution/services/identifier_tree_builder.py

import logging
from typing import Dict
from code_structure.module_resolution.core.identifier_tree import IdentifierTree
from .tree_utils import infer_node_type
from code_structure.utils.logger import get_logger

logger = get_logger(__name__, level=logging.DEBUG)

class IdentifierTreeBuilder:
    def __init__(self):
        self.identifier_tree = IdentifierTree()
        self.node_type_map: Dict[str, str] = {}

    def build_from_resolved(self, resolved_paths: Dict[str, str]):
        self.identifier_tree = IdentifierTree()
        self.node_type_map.clear()
        for identifier, full_path in resolved_paths.items():
            node = self.identifier_tree.add_path(full_path)
            node_type = infer_node_type(identifier, full_path)
            self.node_type_map[full_path] = node_type
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("  === identifier_tree после разрешения ===")
            self._log_tree(self.identifier_tree.root, 0)

    def _log_tree(self, node, indent=0):
        if node.name:
            try:
                full_path = self.identifier_tree.get_full_path(node)
                node_type = self.node_type_map.get(full_path, '?')
                logger.debug("  " * indent + f"- {node.name} [{node_type}] -> {full_path}")
            except Exception as e:
                logger.debug("  " * indent + f"- {node.name} [ошибка: {e}]")
        for child in node.children.values():
            self._log_tree(child, indent + 1)