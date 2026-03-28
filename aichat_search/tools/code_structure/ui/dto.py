# aichat_search/tools/code_structure/ui/dto.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

# --- DTO для ErrorBlockDialog ---
@dataclass
class ErrorBlockInput:
    block_id: str
    original_code: str
    language: str

@dataclass
class ErrorBlockOutput:
    fixed_code: Optional[str] = None

# --- DTO для ModuleAssignmentDialog ---
@dataclass
class UnknownBlockInfo:
    id: str
    display_name: str
    content: str

@dataclass
class KnownModuleInfo:
    name: str
    source: Optional[str]      # откуда получен модуль (например, "из блока abc")
    code: str                  # пример кода для предпросмотра

@dataclass
class TreeDisplayNode:
    text: str
    type: str
    signature: str = ""
    version: str = ""
    sources: str = ""
    children: List['TreeDisplayNode'] = field(default_factory=list)

@dataclass
class ModuleAssignmentInput:
    unknown_blocks: List[UnknownBlockInfo]
    known_modules: List[KnownModuleInfo]
    module_tree: TreeDisplayNode

@dataclass
class ModuleAssignmentOutput:
    assignments: Dict[str, str]          # block_id -> module_name
    updated_module_tree: TreeDisplayNode