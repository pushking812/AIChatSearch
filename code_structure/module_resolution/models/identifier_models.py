# code_structure/module_resolution/models/identifier_models.py

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

# Тип сигнатуры: (has_self: bool, params: List[str])
Signature = Tuple[bool, List[str]]


@dataclass
class MethodInfo:
    name: str
    signature: Signature
    class_name: str
    versions: List['Version'] = field(default_factory=list)


@dataclass
class FunctionInfo:
    name: str
    signature: Signature
    versions: List['Version'] = field(default_factory=list)


@dataclass
class ClassInfo:
    name: str
    methods: Dict[str, MethodInfo] = field(default_factory=dict)
    versions: List['Version'] = field(default_factory=list)


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
    versions: List['Version'] = field(default_factory=list)
    is_imported: bool = False
    # новые поля для импортов и блоков кода
    import_versions: List['Version'] = field(default_factory=list)
    code_block_versions: List['Version'] = field(default_factory=list)