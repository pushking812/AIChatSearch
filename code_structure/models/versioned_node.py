# code_structure/models/versioned_node.py

"""
Модели версионированных узлов (VersionedNode).
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .code_node import CodeNode
from .block import Block
from .registry import BlockRegistry  # будет создан позже, но пока используем forward ref


@dataclass
class SourceRef:
    """Ссылка на источник кода (блок и строки)."""
    block_id: str
    start_line: int
    end_line: int
    timestamp: float   # для сортировки

    def __repr__(self) -> str:
        return f"SourceRef({self.block_id}:{self.start_line}-{self.end_line})"


@dataclass
class VersionInfo:
    """Информация об одной версии."""
    normalized_code: str
    sources: List[SourceRef] = field(default_factory=list)

    @property
    def max_timestamp(self) -> float:
        return max(s.timestamp for s in self.sources) if self.sources else 0.0


class VersionedNode:
    """Базовый класс для версионированных узлов."""
    def __init__(self, name: str, node_type: str):
        self.name = name
        self.node_type = node_type   # "module", "class", "function", "method", "code_block", "import"
        self.versions: List[VersionInfo] = []
        self.children: List['VersionedNode'] = []
        self.parent: Optional['VersionedNode'] = None

    def add_version(self, code_node: CodeNode):
        """Добавляет версию из CodeNode, если нормализованный код уникален."""
        norm = code_node.normalized_content()
        src = SourceRef(
            block_id=code_node.block.id,
            start_line=code_node.start_line,
            end_line=code_node.end_line,
            timestamp=code_node.block.timestamp
        )
        # Поиск существующей версии с таким же нормализованным кодом
        for v in self.versions:
            if v.normalized_code == norm:
                v.sources.append(src)
                self._sort_versions()
                return
        # Новая версия
        self.versions.append(VersionInfo(norm, [src]))
        self._sort_versions()

    def _sort_versions(self):
        """Сортирует версии по возрастанию max_timestamp."""
        self.versions.sort(key=lambda v: v.max_timestamp)

    def get_latest_code(self) -> str:
        """Возвращает исходный код последней версии (не нормализованный)."""
        if not self.versions:
            return ""
        latest = self.versions[-1]
        # Берём источник с максимальным timestamp (последний добавленный)
        src = latest.sources[-1]
        block = BlockRegistry().get(src.block_id)
        if block is None:
            return ""
        lines = block.content.splitlines()
        return '\n'.join(lines[src.start_line - 1:src.end_line])

    @property
    def full_path(self) -> str:
        if self.parent is None:
            return self.name
        return f"{self.parent.full_path}.{self.name}"

    def add_child(self, child: 'VersionedNode'):
        child.parent = self
        self.children.append(child)

    def __repr__(self) -> str:
        return f"<Versioned{self.node_type.capitalize()} name={self.name} versions={len(self.versions)}>"


class VersionedModule(VersionedNode):
    def __init__(self, name: str):
        super().__init__(name, "module")


class VersionedClass(VersionedNode):
    def __init__(self, name: str):
        super().__init__(name, "class")
        # Классы не имеют версий, но могут содержать методы
        self.versions = []   # явно обнуляем, чтобы не было версий


class VersionedFunction(VersionedNode):
    def __init__(self, name: str):
        super().__init__(name, "function")


class VersionedMethod(VersionedNode):
    def __init__(self, name: str):
        super().__init__(name, "method")


class VersionedCodeBlock(VersionedNode):
    def __init__(self, name: str):
        super().__init__(name, "code_block")


class VersionedImport(VersionedNode):
    def __init__(self, name: str = "imports"):
        super().__init__(name, "import")