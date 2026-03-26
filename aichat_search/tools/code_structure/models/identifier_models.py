# aichat_search/tools/code_structure/models/identifier_models.py

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

# Тип сигнатуры: (has_self: bool, params: List[str])
Signature = Tuple[bool, List[str]]


@dataclass
class MethodInfo:
    name: str
    signature: Signature
    class_name: str


@dataclass
class FunctionInfo:
    name: str
    signature: Signature


@dataclass
class ClassInfo:
    name: str
    methods: Dict[str, MethodInfo] = field(default_factory=dict)


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
    is_imported: bool = False