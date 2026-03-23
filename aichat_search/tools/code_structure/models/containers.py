# aichat_search/tools/code_structure/models/containers.py

import logging
import textwrap
from typing import List, Optional, Tuple
from .node import Node
from ..utils.helpers import clean_code

logger = logging.getLogger(__name__)

class Version:
    def __init__(self, node: Node, block_id: str, global_index: int, block_content: str):
        self.node = node
        self.sources = [(block_id, node.lineno_start, node.lineno_end, global_index)]
        self.min_global_index = global_index   # самый ранний источник
        self.max_global_index = global_index   # самый поздний источник
        self.cleaned_content = ""

        if node.lineno_start is not None and node.lineno_end is not None:
            try:
                lines = block_content.splitlines()
                start = max(0, node.lineno_start - 1)
                end = min(len(lines), node.lineno_end)
                fragment_lines = lines[start:end]

                # Удаляем пустые строки в начале и конце, чтобы dedent работал корректно
                while fragment_lines and not fragment_lines[0].strip():
                    fragment_lines.pop(0)
                while fragment_lines and not fragment_lines[-1].strip():
                    fragment_lines.pop()

                if not fragment_lines:
                    code_fragment = ''
                else:
                    code_fragment = '\n'.join(fragment_lines)
                    dedented = textwrap.dedent(code_fragment)
                    code_fragment = dedented

                self.cleaned_content = clean_code(code_fragment)

            except Exception as e:
                logger.error(f"Ошибка при создании версии для узла {node.name} (блок {block_id}): {e}", exc_info=True)
        else:
            logger.warning(f"Узел {node.name} (блок {block_id}) не имеет номеров строк")

    def add_source(self, block_id: str, start: int, end: int, global_index: int):
        self.sources.append((block_id, start, end, global_index))
        if global_index < self.min_global_index:
            self.min_global_index = global_index
        if global_index > self.max_global_index:
            self.max_global_index = global_index

    def get_last_source(self):
        """Возвращает наиболее актуальный источник (последнее упоминание)."""
        if not self.sources:
            return None
        # sources хранятся в порядке добавления, но последний по max_global_index – не обязательно последний добавленный
        last = max(self.sources, key=lambda s: s[3])  # s[3] = global_index
        return last

    def __repr__(self):
        return f"Version(sources={len(self.sources)}, min={self.min_global_index}, max={self.max_global_index})"


class Container:
    def __init__(self, name: str, node_type: str):
        self.name = name
        self.node_type = node_type
        self.children: List['Container'] = []
        self.versions: List[Version] = []

    def add_child(self, child: 'Container'):
        self.children.append(child)

    def add_version(self, version: Version):
        self.versions.append(version)
        # Сортировка по самому раннему источнику (старые версии в начале)
        self.versions.sort(key=lambda v: v.min_global_index)

    def find_child_container(self, name: str, node_type: str) -> Optional['Container']:
        for child in self.children:
            if child.name == name and child.node_type == node_type:
                return child
        return None

    def __repr__(self):
        return f"Container(name={self.name}, type={self.node_type}, children={len(self.children)}, versions={len(self.versions)})"


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