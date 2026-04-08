# code_structure/module_resolution/core/identifier_tree.py

from typing import Dict, List, Optional

import logging
from code_structure.utils.logger import get_logger
logger = get_logger(__name__, level=logging.DEBUG)

class IdentifierNode:
    """Узел иерархического дерева идентификаторов."""
    def __init__(self, name: str):
        self.name = name
        self.parent: Optional['IdentifierNode'] = None
        self.children: Dict[str, 'IdentifierNode'] = {}

    def __repr__(self) -> str:
        return f"IdentifierNode(name={self.name}, children={list(self.children.keys())})"


class IdentifierTree:
    """Дерево, представляющее иерархию имён (пакеты, модули, классы, функции)."""
    def __init__(self):
        self.root = IdentifierNode("")

    def add_path(self, path: str) -> IdentifierNode:
        """Добавляет цепочку узлов по пути и возвращает последний узел."""
        parts = path.split('.')
        current = self.root
        for part in parts:
            if part not in current.children:
                new_node = IdentifierNode(part)
                new_node.parent = current
                current.children[part] = new_node
            current = current.children[part]
        return current

    def get_node(self, path: str) -> Optional[IdentifierNode]:
        """Возвращает узел по полному пути или None, если путь не существует."""
        parts = path.split('.')
        current = self.root
        for part in parts:
            if part not in current.children:
                return None
            current = current.children[part]
        return current

    def get_full_path(self, node: IdentifierNode) -> str:
        """Возвращает полное имя узла, начиная от корня."""
        parts = []
        cur = node
        while cur and cur.name:
            parts.append(cur.name)
            cur = cur.parent
        return '.'.join(reversed(parts))

    def find_module_for_name(self, name: str) -> Optional[str]:
        nodes = self._find_nodes_by_name(self.root, name)
        logger.debug(f"find_module_for_name({name}) -> found {len(nodes)} nodes: {[self.get_full_path(n) for n in nodes]}")
        if len(nodes) == 1:
            parent = nodes[0].parent
            if parent is None:
                return None
            return self.get_full_path(parent)
        return None

    def _find_nodes_by_name(self, node: IdentifierNode, name: str) -> List[IdentifierNode]:
        """Рекурсивно находит все узлы с заданным именем."""
        result = []
        if node.name == name:
            result.append(node)
        for child in node.children.values():
            result.extend(self._find_nodes_by_name(child, name))
        return result

    def __repr__(self) -> str:
        def _format(node: IdentifierNode, indent: int = 0) -> str:
            lines = [f"{'  ' * indent}{node.name}"]
            for child in node.children.values():
                lines.append(_format(child, indent + 1))
            return '\n'.join(lines)
        return _format(self.root)