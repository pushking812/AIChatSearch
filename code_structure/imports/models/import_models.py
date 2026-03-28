# code_structure/imports/models/import_models.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class ImportInfo:
    """Информация об импорте, извлечённая из блока кода."""
    source_module: str
    target_fullname: str
    target_type: str
    is_relative: bool
    original_statement: str
    alias: Optional[str] = None