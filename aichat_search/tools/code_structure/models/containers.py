# aichat_search/tools/code_structure/models/containers.py

import logging
import textwrap
from typing import List, Optional
from .node import Node
from ..utils.helpers import clean_code

logger = logging.getLogger(__name__)

class Version:
    def __init__(self, node: Node, block_id: str, global_index: int, block_content: str):
        self.node = node
        self.sources = [(block_id, node.lineno_start, node.lineno_end, global_index)]
        self.max_global_index = global_index
        self.cleaned_content = ""

        if node.lineno_start is not None and node.lineno_end is not None:
            try:
                lines = block_content.splitlines()
                start = max(0, node.lineno_start - 1)
                end = min(len(lines), node.lineno_end)
                code_fragment = '\n'.join(lines[start:end])
                
                dedented = textwrap.dedent(code_fragment)
                
                self.cleaned_content = clean_code(dedented)
                    
                   
            except Exception as e:
                logger.error(f"Ошибка при создании версии для узла {node.name} (блок {block_id}): {e}", exc_info=True)
        else:
            logger.warning(f"Узел {node.name} (блок {block_id}) не имеет номеров строк")

    def add_source(self, block_id: str, start: int, end: int, global_index: int):
        self.sources.append((block_id, start, end, global_index))
        if global_index > self.max_global_index:
            self.max_global_index = global_index

    def __repr__(self):
        return f"Version(sources={len(self.sources)}, max_idx={self.max_global_index})"


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
        self.versions.sort(key=lambda v: v.max_global_index, reverse=True)

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