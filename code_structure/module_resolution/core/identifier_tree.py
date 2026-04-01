# code_structure/module_resolution/core/identifier_tree.py

from typing import Dict, Optional


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

    def __repr__(self) -> str:
        def _format(node: IdentifierNode, indent: int = 0) -> str:
            lines = [f"{'  ' * indent}{node.name}"]
            for child in node.children.values():
                lines.append(_format(child, indent + 1))
            return '\n'.join(lines)
        return _format(self.root)