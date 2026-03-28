# aichat_search/tools/code_structure/models/containers.py

import logging
import textwrap
from typing import List, Optional, Tuple, Dict

from aichat_search.tools.code_structure.utils.helpers import clean_code

from aichat_search.tools.code_structure.utils.logger import get_logger
logger = get_logger(__name__, level = logging.WARNING)


class Version:
    def __init__(self, node, block_id: str, global_index: int, block_content: str, timestamp: float = None, block_idx: int = 0):
        self.node = node
        self.sources = [(block_id, node.lineno_start, node.lineno_end, global_index)]
        self.source_set = {(block_id, node.lineno_start, node.lineno_end, global_index)}
        self.min_global_index = global_index
        self.max_global_index = global_index
        self.max_timestamp = timestamp if timestamp is not None else global_index
        self.max_block_idx = block_idx
        self.cleaned_content = ""

        if node.lineno_start is not None and node.lineno_end is not None:
            try:
                lines = block_content.splitlines()
                start = max(0, node.lineno_start - 1)
                end = min(len(lines), node.lineno_end)
                fragment_lines = lines[start:end]

                while fragment_lines and not fragment_lines[0].strip():
                    fragment_lines.pop(0)
                while fragment_lines and not fragment_lines[-1].strip():
                    fragment_lines.pop()

                if fragment_lines:
                    code_fragment = '\n'.join(fragment_lines)
                    dedented = textwrap.dedent(code_fragment)
                    code_fragment = dedented
                else:
                    code_fragment = ''

                self.cleaned_content = clean_code(code_fragment)

            except Exception as e:
                logger.error(f"Ошибка при создании версии для узла {node.name} (блок {block_id}): {e}", exc_info=True)
        else:
            logger.warning(f"Узел {node.name} (блок {block_id}) не имеет номеров строк")

    def add_source(self, block_id: str, start: int, end: int, global_index: int, timestamp: float = None, block_idx: int = 0):
        key = (block_id, start, end, global_index)
        if key in self.source_set:
            return  # уже есть
        self.sources.append(key)
        self.source_set.add(key)
        if global_index < self.min_global_index:
            self.min_global_index = global_index
        if global_index > self.max_global_index:
            self.max_global_index = global_index
        if timestamp is not None and timestamp > self.max_timestamp:
            self.max_timestamp = timestamp
        if block_idx > self.max_block_idx:
            self.max_block_idx = block_idx

    def get_last_source(self):
        if not self.sources:
            return None
        return max(self.sources, key=lambda s: s[3])

    def __repr__(self):
        return f"Version(sources={len(self.sources)}, min={self.min_global_index}, max={self.max_global_index}, timestamp={self.max_timestamp}, block_idx={self.max_block_idx})"


class Container:
    def __init__(self, name: str, node_type: str):
        self.name = name
        self.node_type = node_type
        self.children: List['Container'] = []
        self.versions: List[Version] = []
        self.is_placeholder = False
        self.children_dict: Dict[str, 'Container'] = {}
        self.full_path = name

    def add_child(self, child: 'Container'):
        self.children.append(child)
        self.children_dict[child.name] = child

    def add_version(self, version: Version):
        self.versions.append(version)
        self.versions.sort(key=lambda v: (v.max_timestamp, v.max_global_index, v.max_block_idx))

    def get_latest_version(self) -> Optional[Version]:
        if not self.versions:
            return None
        return max(self.versions, key=lambda v: (v.max_timestamp, v.max_global_index, v.max_block_idx))

    def find_child_container(self, name: str, node_type: str) -> Optional['Container']:
        return self.children_dict.get(name)

    def set_placeholder(self, value: bool = True):
        self.is_placeholder = value

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


class ImportContainer(Container):
    def __init__(self, name: str = "imports"):
        super().__init__(name, "import")


class PackageContainer(Container):
    def __init__(self, name: str):
        super().__init__(name, "package")