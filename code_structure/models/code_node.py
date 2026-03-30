# code_structure/models/code_node.py

"""
Модели узлов синтаксического дерева (CodeNode).
"""

from abc import ABC
from typing import Optional, List

# Циклический импорт избегаем, используем аннотацию типов
from .block import Block


class CodeNode(ABC):
    """Базовый узел дерева кода."""
    def __init__(self, name: str, node_type: str, block: Block,
                 start_line: int, end_line: int, parent: Optional['CodeNode'] = None):
        self.name = name
        self.node_type = node_type   # "module", "class", "function", "method", "code_block", "comment", "import"
        self.block = block
        self.start_line = start_line
        self.end_line = end_line
        self.parent = parent
        self.children: List['CodeNode'] = []

    def add_child(self, child: 'CodeNode'):
        child.parent = self
        self.children.append(child)

    @property
    def full_path(self) -> str:
        """Рекурсивно строит полный путь (например, 'mypkg.submod.ClassName.method_name')."""
        if self.parent is None or (self.parent.node_type == 'module' and self.parent.name == '<root>'):
            return self.name
        parent_path = self.parent.full_path
        return f"{parent_path}.{self.name}"

    def get_raw_code(self) -> str:
        """Извлекает фрагмент кода из блока по строкам."""
        lines = self.block.content.splitlines()
        return '\n'.join(lines[self.start_line - 1:self.end_line])

    def normalized_content(self) -> str:
        """Возвращает нормализованный код (без докстрингов, комментариев, лишних пробелов)."""
        from code_structure.utils.helpers import clean_code
        return clean_code(self.get_raw_code())

    def __repr__(self) -> str:
        return f"<{self.node_type.capitalize()}Node name={self.name} lines={self.start_line}-{self.end_line}>"


class ModuleNode(CodeNode):
    def __init__(self, name: str, block: Block, start_line: int, end_line: int, parent=None):
        super().__init__(name, "module", block, start_line, end_line, parent)


class ClassNode(CodeNode):
    def __init__(self, name: str, bases: str, block: Block, start_line: int, end_line: int, parent=None):
        super().__init__(name, "class", block, start_line, end_line, parent)
        self.bases = bases


class FunctionNode(CodeNode):
    def __init__(self, name: str, signature: str, block: Block, start_line: int, end_line: int, parent=None):
        super().__init__(name, "function", block, start_line, end_line, parent)
        self.signature = signature


class MethodNode(FunctionNode):
    def __init__(self, name: str, signature: str, block: Block, start_line: int, end_line: int, parent=None):
        super().__init__(name, signature, block, start_line, end_line, parent)
        self.node_type = "method"


class CodeBlockNode(CodeNode):
    def __init__(self, name: str, block: Block, start_line: int, end_line: int, parent=None):
        super().__init__(name, "code_block", block, start_line, end_line, parent)


class CommentNode(CodeNode):
    def __init__(self, text: str, block: Block, start_line: int, end_line: int, parent=None):
        super().__init__(f"comment_{start_line}", "comment", block, start_line, end_line, parent)
        self.text = text


class ImportNode(CodeNode):
    def __init__(self, statement: str, block: Block, start_line: int, end_line: int, parent=None):
        super().__init__(f"import_{start_line}", "import", block, start_line, end_line, parent)
        self.statement = statement