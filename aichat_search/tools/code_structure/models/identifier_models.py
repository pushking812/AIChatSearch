# aichat_search/tools/code_structure/models/identifier_models.py

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

# Тип сигнатуры: (has_self: bool, params: List[str])
Signature = Tuple[bool, List[str]]


@dataclass
class VersionInfo:
    """Информация о версии (источнике) кода."""
    block_id: str
    start: int
    end: int
    global_index: int
    timestamp: float
    block_idx: int
    block_content: str = ""

@dataclass
class MethodInfo:
    name: str
    signature: Signature
    class_name: str
    sources: List[VersionInfo] = field(default_factory=list)


@dataclass
class FunctionInfo:
    name: str
    signature: Signature
    sources: List[VersionInfo] = field(default_factory=list)


@dataclass
class ClassInfo:
    name: str
    methods: Dict[str, MethodInfo] = field(default_factory=dict)
    sources: List[VersionInfo] = field(default_factory=list)


@dataclass
class ImportedInfo:
    fullname: str
    target_type: str  # 'module', 'class', 'function'
    alias: Optional[str] = None


@dataclass
class ModuleInfo:
    name: str
    classes: Dict[str, ClassInfo] = field(default_factory=dict)
    functions: Dict[str, FunctionInfo] = field(default_factory=dict)
    imports: Dict[str, ImportedInfo] = field(default_factory=dict)
    sources: List[VersionInfo] = field(default_factory=list)
    is_imported: bool = False