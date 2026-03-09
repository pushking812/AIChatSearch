# aichat_search/tools/code_structure/model.py

class Node:
    """Базовый узел дерева структуры кода."""
    def __init__(self, name: str, node_type: str, signature: str = "", lineno_start=None, lineno_end=None):
        self.name = name
        self.node_type = node_type
        self.signature = signature
        self.children = []
        self.lineno_start = lineno_start   # номер первой строки (в коде блока)
        self.lineno_end = lineno_end       # номер последней строки

    def add_child(self, child: 'Node'):
        self.children.append(child)


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


class MethodNode(Node):
    def __init__(self, name: str, args: str = "", lineno_start=None, lineno_end=None):
        signature = f"({args})"
        super().__init__(name, "method", signature, lineno_start, lineno_end)


class CodeBlockNode(Node):
    def __init__(self, name: str = "Блок кода", line_range: str = "", lineno_start=None, lineno_end=None):
        signature = line_range
        super().__init__(name, "code_block", signature, lineno_start, lineno_end)