# code_structure/dialogs/dto.py

"""
Data Transfer Objects (DTO) для обмена данными между UI-слоем и бизнес-логикой.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple

# ----------------------------------------------------------------------
# DTO для ModuleAssignmentDialog
# ----------------------------------------------------------------------
@dataclass
class UnknownBlockInfo:
    id: str
    display_name: str
    content: str
    candidates: List[str] = field(default_factory=list)

@dataclass
class KnownModuleInfo:
    name: str
    source: Optional[str]
    code: str

@dataclass
class TreeDisplayNode:
    text: str
    type: str
    signature: str = ""
    version: str = ""
    sources: str = ""
    full_name: str = ""
    block_id: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    children: List['TreeDisplayNode'] = field(default_factory=list)

@dataclass
class ModuleAssignmentInput:
    unknown_blocks: List[UnknownBlockInfo]
    known_modules: List[KnownModuleInfo]
    module_tree: TreeDisplayNode

@dataclass
class ModuleAssignmentOutput:
    assignments: Dict[str, str]
    updated_module_tree: TreeDisplayNode
    deleted_block_ids: List[str] = field(default_factory=list)

# ----------------------------------------------------------------------
# DTO для главного окна
# ----------------------------------------------------------------------
@dataclass
class FlatListItem:
    block_id: str
    block_name: str
    node_path: str
    parent_path: str
    lines: str
    module: str
    class_name: str
    strategy: str
    language: str = "python"

@dataclass
class CodeStructureInitDTO:
    languages: List[str]
    tree: TreeDisplayNode
    flat_items: List[FlatListItem]
    has_unknown_blocks: bool
    has_error_blocks: bool = False

@dataclass
class CodeStructureRefreshDTO:
    tree: TreeDisplayNode
    flat_items: List[FlatListItem]

# ----------------------------------------------------------------------
# DTO для диалога разрешения неоднозначностей
# ----------------------------------------------------------------------
@dataclass
class AmbiguityInfo:
    name: str
    candidates: List[str]
    context: Optional[str] = None

# ----------------------------------------------------------------------
# DTO для единого диалога исправления ошибок
# ----------------------------------------------------------------------
@dataclass
class ErrorBlockInfo:
    block_id: str
    original_code: str
    language: str
    chat: Any = None
    message_pair: Any = None

@dataclass
class ErrorBlocksInput:
    blocks: List[ErrorBlockInfo]

@dataclass
class ErrorBlocksOutput:
    fixed_blocks: List[Tuple[str, str]]   # (block_id, new_code)
    deleted_block_ids: List[str]