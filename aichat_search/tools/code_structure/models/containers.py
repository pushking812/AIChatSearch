# aichat_search/tools/code_structure/models/containers.py

from typing import List, Optional, Tuple, Any
from .node import Node
from ..utils.helpers import clean_code

class Version:
    """
    Представляет конкретную реализацию функции, метода или блока кода.
    Хранит ссылку на исходный узел, очищенное содержимое и список источников.
    """
    def __init__(self, node: Node, block_id: str, global_index: int, block_content: str):
        self.node = node
        # Извлечение фрагмента кода, соответствующего узлу
        if node.lineno_start is not None and node.lineno_end is not None:
            lines = block_content.splitlines()
            start = max(0, node.lineno_start - 1)
            end = min(len(lines), node.lineno_end)
            code_fragment = '\n'.join(lines[start:end])
            self.cleaned_content = clean_code(code_fragment)
        else:
            self.cleaned_content = ""
        self.sources = [(block_id, node.lineno_start, node.lineno_end, global_index)]
        self.max_global_index = global_index

    def add_source(self, block_id: str, start: int, end: int, global_index: int):
        self.sources.append((block_id, start, end, global_index))
        if global_index > self.max_global_index:
            self.max_global_index = global_index


class Container:
    """
    Базовый класс для контейнеров, представляющих логические элементы структуры кода.
    """
    def __init__(self, name: str, node_type: str):
        self.name = name
        self.node_type = node_type   # "module", "class", "function", "method", "code_block"
        self.children: List['Container'] = []
        self.versions: List[Version] = []   # для function/method/code_block; у class/module versions пуст

    def add_child(self, child: 'Container'):
        self.children.append(child)

    def add_version(self, version: Version):
        self.versions.append(version)
        # Сортируем версии по убыванию максимального глобального индекса
        self.versions.sort(key=lambda v: v.max_global_index, reverse=True)

    def find_child_container(self, name: str, node_type: str) -> Optional['Container']:
        """Ищет дочерний контейнер по имени и типу."""
        for child in self.children:
            if child.name == name and child.node_type == node_type:
                return child
        return None

    def __repr__(self):
        return f"Container(name={self.name}, type={self.node_type}, children={len(self.children)}, versions={len(self.versions)})"


# Специализированные классы (опционально, можно использовать общий Container с проверкой типа)
class ModuleContainer(Container):
    def __init__(self, name: str):
        super().__init__(name, "module")


class ClassContainer(Container):
    def __init__(self, name: str):
        super().__init__(name, "class")


class FunctionContainer(Container):
    def __init__(self, name: str):
        super().__init__(name, "function")


class MethodContainer(Container):
    def __init__(self, name: str):
        super().__init__(name, "method")


class CodeBlockContainer(Container):
    def __init__(self, name: str):
        super().__init__(name, "code_block")