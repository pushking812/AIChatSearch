from dataclasses import dataclass, field
from typing import List, Optional

from .block import Block
from .registry import BlockRegistry


@dataclass
class SourceRef:
    block_id: str
    start_line: int
    end_line: int
    timestamp: float

    def __repr__(self):
        return f"SourceRef({self.block_id}:{self.start_line}-{self.end_line})"


@dataclass
class VersionInfo:
    normalized_code: str
    sources: List[SourceRef] = field(default_factory=list)

    @property
    def max_timestamp(self) -> float:
        return max(s.timestamp for s in self.sources) if self.sources else 0.0

    def add_source(self, source: SourceRef):
        """Добавляет источник, если его ещё нет в списке."""
        for s in self.sources:
            if s.block_id == source.block_id and s.start_line == source.start_line and s.end_line == source.end_line:
                return
        self.sources.append(source)


class VersionedNode:
    def __init__(self, name: str, node_type: str):
        self.name = name or "?"
        self.node_type = node_type
        self.versions: List[VersionInfo] = []
        self.children: List['VersionedNode'] = []
        self.parent: Optional['VersionedNode'] = None
        self.is_imported: bool = False

    def add_version_info(self, version_info: VersionInfo):
        for v in self.versions:
            if v.normalized_code == version_info.normalized_code:
                for src in version_info.sources:
                    v.add_source(src)
                return
        self.versions.append(version_info)

    def get_latest_code(self) -> str:
        if not self.versions:
            return ""
        latest = self.versions[-1]
        src = latest.sources[-1]
        block = BlockRegistry().get(src.block_id)
        if not block:
            return ""
        lines = block.content.splitlines()
        return '\n'.join(lines[src.start_line - 1:src.end_line])

    @property
    def full_path(self) -> str:
        if self.parent is None:
            return self.name
        return f"{self.parent.full_path}.{self.name}"

    @property
    def local_path(self) -> str:
        parts = []
        node = self
        while node is not None and node.node_type not in ('module', 'package'):
            if node.name is not None:
                parts.append(node.name)
            node = node.parent
        return '.'.join(reversed(parts))

    def add_child(self, child: 'VersionedNode'):
        child.parent = self
        self.children.append(child)

    def __repr__(self):
        return f"<Versioned{self.node_type.capitalize()} name={self.name} versions={len(self.versions)}>"


class VersionedModule(VersionedNode):
    def __init__(self, name: str):
        super().__init__(name, "module")


class VersionedClass(VersionedNode):
    def __init__(self, name: str):
        super().__init__(name, "class")


class VersionedFunction(VersionedNode):
    def __init__(self, name: str):
        super().__init__(name, "function")


class VersionedMethod(VersionedNode):
    def __init__(self, name: str):
        super().__init__(name, "method")


class VersionedCodeBlock(VersionedNode):
    def __init__(self, name: str = "code_block"):
        super().__init__(name, "code_block")


class VersionedImport(VersionedNode):
    def __init__(self, name: str = "imports"):
        super().__init__(name, "import")