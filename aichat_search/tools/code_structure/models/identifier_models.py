# aichat_search/tools/code_structure/models/identifier_models.py

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

# Тип сигнатуры: (has_self: bool, params: List[str])
Signature = Tuple[bool, List[str]]


@dataclass
class MethodInfo:
    """Информация о методе класса."""
    name: str
    signature: Signature
    class_name: str


@dataclass
class FunctionInfo:
    """Информация о функции верхнего уровня."""
    name: str
    signature: Signature


@dataclass
class ClassInfo:
    """Информация о классе."""
    name: str
    methods: Dict[str, MethodInfo] = field(default_factory=dict)


@dataclass
class ModuleInfo:
    """Информация о модуле."""
    name: str
    classes: Dict[str, ClassInfo] = field(default_factory=dict)
    functions: Dict[str, FunctionInfo] = field(default_factory=dict)