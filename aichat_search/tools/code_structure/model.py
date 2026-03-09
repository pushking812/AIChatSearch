# aichat_search/tools/code_structure/model.py

class Node:
    """Базовый узел дерева структуры кода."""
    def __init__(self, name: str, node_type: str, signature: str = ""):
        self.name = name
        self.node_type = node_type  # "module", "class", "function", "method", "code_block"
        self.signature = signature
        self.children = []

    def add_child(self, child: 'Node'):
        self.children.append(child)


class ModuleNode(Node):
    def __init__(self, name: str = "Модуль"):
        super().__init__(name, "module")


class ClassNode(Node):
    def __init__(self, name: str, bases: str = ""):
        signature = f"({bases})" if bases else ""
        super().__init__(name, "class", signature)


class FunctionNode(Node):
    def __init__(self, name: str, args: str = ""):
        signature = f"({args})"
        super().__init__(name, "function", signature)


class MethodNode(Node):
    def __init__(self, name: str, args: str = ""):
        signature = f"({args})"
        super().__init__(name, "method", signature)


class CodeBlockNode(Node):
    def __init__(self, name: str = "Блок кода", line_range: str = ""):
        signature = line_range
        super().__init__(name, "code_block", signature)