# aichat_search/tools/code_structure/models/node.py

from ..utils.helpers import clean_code


class Node:
    """Базовый узел дерева структуры кода."""
    def __init__(self, name: str, node_type: str, signature: str = "", lineno_start=None, lineno_end=None):
        self.name = name
        self.node_type = node_type
        self.signature = signature
        self.children = []
        self.lineno_start = lineno_start   # номер первой строки (в коде блока)
        self.lineno_end = lineno_end       # номер последней строки
        
        self.source_info = None  # поле для хранения информации об источнике

    def add_child(self, child: 'Node'):
        self.children.append(child)

    # Заглушка для будущего использования
    def get_cleaned_content(self) -> str:
        """Возвращает очищенное содержимое узла (для функций/методов/блоков)."""
        return ""

    def count_nodes(self) -> int:
        """Возвращает общее количество узлов в поддереве, включая текущий."""
        total = 1  # считаем себя
        for child in self.children:
            total += child.count_nodes()
        return total


class ModuleNode(Node):
    def __init__(self, name: str = "Модуль", lineno_start=None, lineno_end=None):
        super().__init__(name, "module", "", lineno_start, lineno_end)


class ClassNode(Node):
    def __init__(self, name: str, bases: str = "", lineno_start=None, lineno_end=None):
        signature = f"({bases})" if bases else ""
        super().__init__(name, "class", signature, lineno_start, lineno_end)


class FunctionNode(Node):
    def __init__(self, name: str, args: str = "", lineno_start=None, lineno_end=None):
        signature = f"({args})"
        super().__init__(name, "function", signature, lineno_start, lineno_end)

    def get_cleaned_content(self) -> str:
        if hasattr(self, '_cached_cleaned'):
            return self._cached_cleaned
        return ""


class MethodNode(Node):
    def __init__(self, name: str, args: str = "", lineno_start=None, lineno_end=None):
        signature = f"({args})"
        super().__init__(name, "method", signature, lineno_start, lineno_end)


class CodeBlockNode(Node):
    def __init__(self, name: str = "Блок кода", line_range: str = "", lineno_start=None, lineno_end=None):
        signature = line_range
        super().__init__(name, "code_block", signature, lineno_start, lineno_end)